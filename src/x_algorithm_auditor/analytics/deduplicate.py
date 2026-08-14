"""Non-additive reconciliation of potentially cumulative Analytics exports."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit

import pandas as pd

from x_algorithm_auditor.analytics.schema import CANONICAL_FIELDS, COUNT_FIELDS


def _normal_text(value: object) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    return re.sub(r"\s+", " ", text)


def _canonical_url(value: object) -> str | None:
    """Return a conservative URL identity without tracking query/fragment data.

    URL identity is deliberately separate from a status ID.  This lets exports
    that provide a stable non-status permalink deduplicate even if post text
    changes between export windows, while status URLs still converge with an
    explicit ``post_id`` through the higher-priority ID key.
    """

    if value is None or value is pd.NA or pd.isna(value):
        return None
    raw = unicodedata.normalize("NFKC", str(value)).strip()
    if not raw:
        return None
    if raw.startswith("//"):
        raw = "https:" + raw
    elif "://" not in raw:
        raw = "https://" + raw
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    if not host:
        return None
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    tracking_keys = {"campaign", "cxt", "ref", "s", "src", "t"}
    query = [
        (key, query_value)
        for key, query_value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in tracking_keys and not key.casefold().startswith("utm_")
    ]
    normalized_query = urlencode(sorted(query))
    return f"{host}{path}" + (f"?{normalized_query}" if normalized_query else "")


def _post_id_from_url(value: object) -> str | None:
    canonical_url = _canonical_url(value)
    if canonical_url is None:
        return None
    match = re.search(r"/(?:status|statuses)/(\d+)(?:/|$)", canonical_url, re.IGNORECASE)
    return match.group(1) if match else None


def _identity(row: pd.Series, row_order: int) -> tuple[str, str]:
    """Choose only a strong cluster key; weak identities remain unique rows.

    A fallback hash that omits a stable upstream identity would turn unrelated
    blank or short-text rows into duplicates.  For that reason the final
    fallback is intentionally an auditable per-input-row token rather than a
    cross-row merge key.
    """

    post_id = _normal_text(row.get("post_id"))
    if post_id:
        return "id", f"id:{post_id}"
    url_id = _post_id_from_url(row.get("canonical_url"))
    if url_id:
        return "url_status_id", f"id:{url_id}"
    canonical_url = _canonical_url(row.get("canonical_url"))
    if canonical_url:
        return "canonical_url", f"url:{canonical_url}"
    text = _normal_text(row.get("text"))
    timestamp = _normal_text(row.get("created_at"))
    if text and timestamp:
        return "text_timestamp", f"text_timestamp:{text}|{timestamp}"
    payload = "|".join(
        (
            _normal_text(row.get("source_file")),
            _normal_text(row.get("source_row")),
            str(row_order),
            text,
            timestamp,
            _normal_text(row.get("post_type")),
        )
    )
    return (
        "insufficient_identity",
        "insufficient_identity:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24],
    )


def _observed_count(row: pd.Series) -> int:
    return sum(
        not pd.isna(row.get(column))
        for column in CANONICAL_FIELDS
        if column not in {"source_file", "source_row"}
    )


def _date_order(row: pd.Series) -> str:
    for column in ("export_date", "date_range_end"):
        value = row.get(column)
        if value is not None and value is not pd.NA and not pd.isna(value):
            return str(value)
    return ""


@dataclass
class DeduplicationSummary:
    """Auditable reconciliation diagnostics, with no arithmetic merging."""

    input_rows: int
    output_posts: int
    deduplicated_rows: int
    conflict_count: int
    identity_methods: Counter[str] = field(default_factory=Counter)
    insufficient_identity_rows: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "input_rows": self.input_rows,
            "output_posts": self.output_posts,
            "deduplicated_rows": self.deduplicated_rows,
            "conflict_count": self.conflict_count,
            "identity_methods": dict(sorted(self.identity_methods.items())),
            "insufficient_identity_rows": self.insufficient_identity_rows,
        }


@dataclass
class DeduplicatedAnalytics:
    data: pd.DataFrame
    summary: DeduplicationSummary


def deduplicate_posts(data: pd.DataFrame) -> DeduplicatedAnalytics:
    """Choose a single documented anchor per duplicate cluster; never sum counts."""

    if data.empty:
        return DeduplicatedAnalytics(
            data=data.copy(),
            summary=DeduplicationSummary(0, 0, 0, 0),
        )
    clusters: dict[str, list[tuple[int, pd.Series, str]]] = {}
    insufficient_identity_rows = 0
    for order, (_, row) in enumerate(data.iterrows()):
        method, key = _identity(row, order)
        if method == "insufficient_identity":
            insufficient_identity_rows += 1
        clusters.setdefault(key, []).append((order, row.copy(), method))

    resolved: list[pd.Series] = []
    method_counts: Counter[str] = Counter()
    conflicts = 0
    for rows in clusters.values():
        rows.sort(
            key=lambda item: (
                _observed_count(item[1]),
                _date_order(item[1]),
                float(item[1].get("impressions"))
                if not pd.isna(item[1].get("impressions"))
                else -1.0,
                item[0],
            ),
            reverse=True,
        )
        _, anchor, method = rows[0]
        method_counts[method] += 1
        anchor["dedup_identity_method"] = method
        if method == "insufficient_identity":
            anchor["dedup_identity_warning"] = (
                "insufficient stable identity; row preserved without weak-identity merging"
            )
        else:
            anchor["dedup_identity_warning"] = pd.NA
        for _, duplicate, _ in rows[1:]:
            for column in CANONICAL_FIELDS:
                if column in {"source_file", "source_row"}:
                    continue
                anchor_value = anchor.get(column)
                duplicate_value = duplicate.get(column)
                anchor_missing = pd.isna(anchor_value)
                duplicate_missing = pd.isna(duplicate_value)
                if anchor_missing and not duplicate_missing:
                    anchor[column] = duplicate_value
                elif (
                    not anchor_missing
                    and not duplicate_missing
                    and str(anchor_value) != str(duplicate_value)
                ):
                    conflicts += 1
        resolved.append(anchor)

    result = pd.DataFrame(resolved).reset_index(drop=True)
    for column in COUNT_FIELDS:
        if column in result:
            result[column] = result[column].astype("Float64")
    return DeduplicatedAnalytics(
        data=result,
        summary=DeduplicationSummary(
            input_rows=len(data),
            output_posts=len(result),
            deduplicated_rows=len(data) - len(result),
            conflict_count=conflicts,
            identity_methods=method_counts,
            insufficient_identity_rows=insufficient_identity_rows,
        ),
    )

"""CSV/XLSX Analytics loading with nullable semantics and quality diagnostics."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from x_algorithm_auditor.analytics.schema import (
    ALIASES,
    CANONICAL_FIELDS,
    COUNT_FIELDS,
    AnalyticsSchemaError,
    HeaderMapping,
    load_alias_overrides,
    map_headers,
    normalize_header,
)

CROSS_EXPORT_WARNING = (
    "Account overview and per-post analytics may use different coverage or attribution "
    "semantics and must not be automatically summed or merged."
)


@dataclass
class DataQualitySummary:
    """Machine-readable validation and source coverage diagnostics."""

    input_rows: int = 0
    events: Counter[str] = field(default_factory=Counter)
    source_columns: dict[str, bool] = field(default_factory=dict)
    unknown_headers: list[str] = field(default_factory=list)
    mapped_headers: dict[str, str] = field(default_factory=dict)
    date_range_values: list[str] = field(default_factory=list)

    def add(self, event: str, amount: int = 1) -> None:
        if amount > 0:
            self.events[event] += amount

    def category_counts(self) -> dict[str, int]:
        """Group event evidence without collapsing missing into observed zero."""

        def count_prefixes(*prefixes: str) -> int:
            return sum(
                amount
                for event, amount in self.events.items()
                if any(event.startswith(prefix) for prefix in prefixes)
            )

        return {
            "absent_columns": count_prefixes("absent_column:"),
            "missing_cells": count_prefixes("missing_cell:"),
            "malformed_values": count_prefixes(
                "malformed_numeric:", "malformed_timestamp:", "percentage_for_count:"
            ),
            "negative_values": count_prefixes("negative_count:"),
            "rate_unavailable_zero_impressions": count_prefixes(
                "rate_unavailable:zero_impressions"
            ),
            "rate_unavailable_missing_or_invalid_impressions": count_prefixes(
                "rate_unavailable:missing_or_invalid_impressions"
            ),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_rows": self.input_rows,
            "events": dict(sorted(self.events.items())),
            "source_columns": self.source_columns,
            "unknown_headers": self.unknown_headers,
            "mapped_headers": self.mapped_headers,
            "date_range_values": self.date_range_values,
            "category_counts": self.category_counts(),
        }


@dataclass
class LoadedAnalytics:
    """Canonical nullable table and its read/validation evidence."""

    data: pd.DataFrame
    quality: DataQualitySummary
    mapping: HeaderMapping


class AnalyticsLoadError(ValueError):
    """Input cannot be read or violates minimum safe schema requirements."""


def _read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            return pd.read_csv(path, dtype=object, encoding=encoding)
        except UnicodeError as error:
            last_error = error
    raise AnalyticsLoadError(f"unable to decode CSV {path}: {last_error}")


def _read_source(path: Path) -> pd.DataFrame:
    suffix = path.suffix.casefold()
    try:
        if suffix == ".csv":
            return _read_csv(path)
        if suffix == ".xlsx":
            return pd.read_excel(path, dtype=object, sheet_name=0)
    except (OSError, ValueError, ImportError) as error:
        raise AnalyticsLoadError(f"unable to read {path}: {error}") from error
    display_suffix = suffix if suffix else "(no extension)"
    raise AnalyticsLoadError(
        f"unsupported input format {display_suffix!r}; only .csv and .xlsx are supported"
    )


def _blank(value: object) -> bool:
    if value is None or value is pd.NA:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def _parse_count(value: object, field_name: str, quality: DataQualitySummary) -> object:
    if _blank(value):
        quality.add(f"missing_cell:{field_name}")
        return pd.NA
    if isinstance(value, bool):
        quality.add(f"malformed_numeric:{field_name}")
        return pd.NA
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text.endswith("%"):
            quality.add(f"percentage_for_count:{field_name}")
            return pd.NA
        value = text
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        quality.add(f"malformed_numeric:{field_name}")
        return pd.NA
    if not math.isfinite(numeric):
        quality.add(f"malformed_numeric:{field_name}")
        return pd.NA
    if numeric < 0:
        quality.add(f"negative_count:{field_name}")
        return pd.NA
    return numeric


def _parse_datetime(value: object, field_name: str, quality: DataQualitySummary) -> object:
    if _blank(value):
        quality.add(f"missing_cell:{field_name}")
        return pd.NA
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        quality.add(f"malformed_timestamp:{field_name}")
        return pd.NA
    return parsed.isoformat().replace("+00:00", "Z")


def _parse_text(value: object, field_name: str, quality: DataQualitySummary) -> object:
    if _blank(value):
        quality.add(f"missing_cell:{field_name}")
        return pd.NA
    return str(value).strip()


def load_analytics(path: Path, alias_map_path: Path | None = None) -> LoadedAnalytics:
    """Read one Analytics export into all nullable canonical columns.

    This function does not infer a missing metric from aggregate engagements or
    coerce malformed/missing values to zero.
    """

    if not path.exists() or not path.is_file():
        raise AnalyticsLoadError(f"input file does not exist: {path}")
    raw = _read_source(path)
    normalized_headers = {normalize_header(column) for column in raw.columns}
    identity_aliases = {
        normalize_header(alias)
        for field in ("post_id", "canonical_url", "text")
        for alias in (*ALIASES[field], field)
    }
    if normalized_headers & {"create post", "unfollows"} and not (
        normalized_headers & identity_aliases
    ):
        raise AnalyticsLoadError(
            "account overview export detected. "
            + CROSS_EXPORT_WARNING
            + " Provide a per-post Analytics export for auditing."
        )
    try:
        overrides = load_alias_overrides(alias_map_path)
        mapping = map_headers(list(raw.columns), overrides)
    except AnalyticsSchemaError as error:
        raise AnalyticsLoadError(str(error)) from error

    if "impressions" not in mapping.canonical_to_source:
        raise AnalyticsLoadError("required exposure field missing: impressions")
    identity_fields = {"post_id", "canonical_url", "text"}
    if not (identity_fields & set(mapping.canonical_to_source)):
        raise AnalyticsLoadError(
            "at least one identity field is required: post_id, canonical_url, or text"
        )

    quality = DataQualitySummary(
        input_rows=len(raw),
        source_columns={field: field in mapping.canonical_to_source for field in CANONICAL_FIELDS},
        unknown_headers=mapping.unknown_headers,
        mapped_headers=mapping.source_to_canonical,
    )
    result = pd.DataFrame(index=raw.index)
    for canonical in CANONICAL_FIELDS:
        source = mapping.canonical_to_source.get(canonical)
        if source is None:
            result[canonical] = pd.Series(pd.NA, index=raw.index, dtype="object")
            # These two fields are provenance generated by the local loader,
            # not fields an upstream export is expected to contain.
            if canonical not in {"source_file", "source_row"}:
                quality.add(f"absent_column:{canonical}")
            continue
        values = raw[source]
        if canonical in COUNT_FIELDS:
            result[canonical] = values.map(
                lambda value, field_name=canonical: _parse_count(value, field_name, quality)
            ).astype("Float64")
        elif canonical in {"created_at", "export_date", "date_range_start", "date_range_end"}:
            result[canonical] = values.map(
                lambda value, field_name=canonical: _parse_datetime(value, field_name, quality)
            ).astype("string")
        else:
            result[canonical] = values.map(
                lambda value, field_name=canonical: _parse_text(value, field_name, quality)
            ).astype("string")

    result["source_file"] = str(path)
    result["source_row"] = pd.Series(range(2, len(result) + 2), index=result.index, dtype="Int64")
    impressions = result["impressions"]
    quality.add("rate_unavailable:zero_impressions", int(impressions.eq(0).sum()))
    quality.add("rate_unavailable:missing_or_invalid_impressions", int(impressions.isna().sum()))
    ranges = (
        result[["date_range_start", "date_range_end"]]
        .dropna(how="all")
        .astype("string")
        .fillna("")
        .apply(lambda row: f"{row['date_range_start']}..{row['date_range_end']}", axis=1)
        .unique()
        .tolist()
    )
    quality.date_range_values = sorted(str(value) for value in ranges)
    if len(quality.date_range_values) > 1:
        quality.add("multiple_date_ranges")
    return LoadedAnalytics(data=result.reset_index(drop=True), quality=quality, mapping=mapping)

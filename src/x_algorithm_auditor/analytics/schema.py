"""Canonical nullable Analytics schema and versioned header aliases."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ALIAS_SCHEMA_VERSION = "analytics-aliases-v1"

METADATA_FIELDS: tuple[str, ...] = (
    "post_id",
    "canonical_url",
    "text",
    "created_at",
    "post_type",
    "source_file",
    "source_row",
    "export_date",
    "date_range_start",
    "date_range_end",
)
COUNT_FIELDS: tuple[str, ...] = (
    "impressions",
    "engagements",
    "likes",
    "replies",
    "reposts",
    "quotes",
    "shares",
    "shares_via_dm",
    "shares_via_copy_link",
    "bookmarks",
    "profile_visits",
    "follows",
    "link_clicks",
    "detail_expands",
    "media_views",
    "not_interested",
    "blocks",
    "mutes",
    "reports",
)
CANONICAL_FIELDS = METADATA_FIELDS + COUNT_FIELDS


def normalize_header(value: object) -> str:
    """Normalize safe header variations without altering semantic word content."""

    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    text = re.sub(r"[\s_\-/.()\[\]:]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Alias data remains compact, explicit, and versioned. An unknown header is not
# guessed from similarity; callers can pass an explicit override YAML file.
ALIASES: dict[str, tuple[str, ...]] = {
    "post_id": ("post id", "tweet id", "x post id", "id", "status id"),
    "canonical_url": (
        "post link",
        "post url",
        "tweet link",
        "tweet url",
        "status link",
        "status url",
        "x url",
        "canonical url",
        "permalink",
    ),
    "text": ("post text", "tweet text", "text", "content", "full text", "body"),
    "created_at": ("created at", "post date", "tweet date", "date", "time", "posted at"),
    "post_type": ("post type", "tweet type", "type", "format"),
    "export_date": ("export date", "exported at"),
    "date_range_start": ("date range start", "range start", "start date"),
    "date_range_end": ("date range end", "range end", "end date"),
    "impressions": ("impressions", "impression", "views", "view count"),
    "engagements": ("engagements", "total engagements", "engagement count"),
    "likes": ("likes", "like", "favorites", "favourites"),
    "replies": ("replies", "reply", "comments"),
    "reposts": ("reposts", "reposts", "retweets", "retweet", "reposts count"),
    "quotes": ("quotes", "quote posts", "quote tweets", "quote"),
    "shares": ("shares", "share"),
    "shares_via_dm": ("shares via dm", "dm shares", "share via dm"),
    "shares_via_copy_link": (
        "shares via copy link",
        "copy link shares",
        "share via copy link",
    ),
    "bookmarks": ("bookmarks", "bookmark"),
    "profile_visits": ("profile visits", "profile visit", "profile clicks"),
    "follows": ("follows", "new follows", "followers gained", "follow"),
    "link_clicks": ("link clicks", "url clicks", "link click"),
    "detail_expands": ("detail expands", "detail expand", "detail clicks"),
    "media_views": ("media views", "video views", "media view"),
    "not_interested": ("not interested", "not interested feedback"),
    "blocks": ("blocks", "block author", "block"),
    "mutes": ("mutes", "mute author", "mute"),
    "reports": ("reports", "report", "reported"),
}


class AnalyticsSchemaError(ValueError):
    """Input headers cannot be safely normalized into the canonical schema."""


@dataclass(frozen=True)
class HeaderMapping:
    """Result of a deterministic source-header mapping pass."""

    source_to_canonical: dict[str, str]
    canonical_to_source: dict[str, str]
    unknown_headers: list[str]


def _normalized_override(override: dict[str, Any] | None) -> dict[str, str]:
    if not override:
        return {}
    normalized: dict[str, str] = {}
    for source, canonical in override.items():
        if canonical not in CANONICAL_FIELDS:
            raise AnalyticsSchemaError(
                f"alias override maps {source!r} to unknown canonical field {canonical!r}"
            )
        normalized[normalize_header(source)] = canonical
    return normalized


def map_headers(headers: list[object], overrides: dict[str, Any] | None = None) -> HeaderMapping:
    """Map aliases without silently accepting ambiguous duplicate canonical fields."""

    override_map = _normalized_override(overrides)
    alias_to_canonical: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in (*aliases, canonical):
            normalized = normalize_header(alias)
            existing = alias_to_canonical.get(normalized)
            if existing and existing != canonical:
                raise RuntimeError(
                    f"built-in alias collision: {normalized}: {existing} / {canonical}"
                )
            alias_to_canonical[normalized] = canonical

    source_to_canonical: dict[str, str] = {}
    canonical_to_source: dict[str, str] = {}
    unknown: list[str] = []
    for original in headers:
        source = str(original)
        normalized = normalize_header(source)
        canonical = override_map.get(normalized) or alias_to_canonical.get(normalized)
        if canonical is None:
            unknown.append(source)
            continue
        if canonical in canonical_to_source:
            prior = canonical_to_source[canonical]
            raise AnalyticsSchemaError(
                f"ambiguous mapping: source columns {prior!r} and {source!r} both map to {canonical!r}; "
                "provide a safe explicit alias map or remove one column"
            )
        source_to_canonical[source] = canonical
        canonical_to_source[canonical] = source
    return HeaderMapping(source_to_canonical, canonical_to_source, unknown)


def load_alias_overrides(path: Path | None) -> dict[str, Any] | None:
    """Load a simple YAML mapping of source header to canonical field."""

    if path is None:
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise AnalyticsSchemaError(f"unable to read alias map {path}: {error}") from error
    except yaml.YAMLError as error:
        raise AnalyticsSchemaError(f"invalid alias map YAML {path}: {error}") from error
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise AnalyticsSchemaError(
            "alias map must be a mapping of source header to canonical field"
        )
    return payload

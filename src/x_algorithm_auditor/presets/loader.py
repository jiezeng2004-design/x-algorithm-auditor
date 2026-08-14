"""Explicit, versioned optional preset loading with no scoring-policy override."""

from __future__ import annotations

from math import isfinite
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

PRESET_SCHEMA_VERSION = "preset-v1"

# These are generic classifier labels, not creator-specific strategy claims.
SUPPORTED_CONTENT_TYPES = frozenset(
    {
        "Tool Hands-on",
        "AI News",
        "Tutorial",
        "Comparison",
        "Builder / Project",
        "Social",
        "Reply",
        "Quote",
        "Thread",
        "Other",
    }
)


class PresetLoadError(ValueError):
    """An actionable local-preset validation failure."""


class AuditPreset(BaseModel):
    """A local context and classifier-extension preset, never an audit policy.

    Scores, exposure gates, official snapshot provenance, missing-state
    semantics, detectors, and recommendations remain governed by the generic
    methodology. Historical values are retained only as a comparison prior for
    a human reader; current supplied Analytics remains the scored evidence.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[PRESET_SCHEMA_VERSION]
    creator_goal: str | None = Field(default=None, max_length=240)
    niche: str | None = Field(default=None, max_length=160)
    content_taxonomy_keywords: dict[str, list[str]] = Field(default_factory=dict)
    historical_baseline: dict[str, float] = Field(default_factory=dict)
    preferred_metrics: list[str] = Field(default_factory=list)

    @field_validator("creator_goal", "niche")
    @classmethod
    def nonblank_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must be a non-empty string when supplied")
        return value.strip() if value is not None else None

    @field_validator("content_taxonomy_keywords")
    @classmethod
    def validate_keyword_extensions(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        normalized: dict[str, list[str]] = {}
        for content_type, keywords in value.items():
            if content_type not in SUPPORTED_CONTENT_TYPES:
                choices = ", ".join(sorted(SUPPORTED_CONTENT_TYPES))
                raise ValueError(
                    f"unsupported content type {content_type!r}; choose one of: {choices}"
                )
            if not keywords:
                raise ValueError(f"content taxonomy keywords for {content_type!r} cannot be empty")
            cleaned: list[str] = []
            seen: set[str] = set()
            for keyword in keywords:
                compact = keyword.strip()
                if not compact:
                    raise ValueError(
                        f"content taxonomy keywords for {content_type!r} cannot contain blanks"
                    )
                key = compact.casefold()
                if key in seen:
                    raise ValueError(
                        f"content taxonomy keywords for {content_type!r} cannot contain duplicates"
                    )
                seen.add(key)
                cleaned.append(compact)
            normalized[content_type] = cleaned
        return normalized

    @field_validator("historical_baseline")
    @classmethod
    def validate_historical_baseline(cls, value: dict[str, float]) -> dict[str, float]:
        for metric, observed in value.items():
            if not metric.strip():
                raise ValueError("historical baseline metric names cannot be blank")
            if not isfinite(observed):
                raise ValueError(f"historical baseline {metric!r} must be finite")
        return value

    @field_validator("preferred_metrics")
    @classmethod
    def validate_preferred_metrics(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for metric in value:
            compact = metric.strip()
            if not compact:
                raise ValueError("preferred metrics cannot contain blanks")
            key = compact.casefold()
            if key in seen:
                raise ValueError("preferred metrics cannot contain duplicates")
            seen.add(key)
            cleaned.append(compact)
        return cleaned


def _validation_summary(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )


def load_preset(path: Path) -> AuditPreset:
    """Read one user-selected YAML preset with concise remediation guidance."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PresetLoadError(f"unable to read preset {path}: {error}") from error
    except yaml.YAMLError as error:
        raise PresetLoadError(f"invalid YAML in preset {path}: {error}") from error
    if not isinstance(payload, dict):
        raise PresetLoadError(
            f"preset {path} must be a YAML mapping beginning with "
            f"schema_version: {PRESET_SCHEMA_VERSION}"
        )
    try:
        return AuditPreset.model_validate(payload)
    except ValidationError as error:
        raise PresetLoadError(
            f"invalid preset {path}: {_validation_summary(error)}. "
            f"Use schema_version: {PRESET_SCHEMA_VERSION} and only documented fields."
        ) from error

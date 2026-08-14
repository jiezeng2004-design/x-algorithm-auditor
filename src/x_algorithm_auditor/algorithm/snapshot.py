"""Immutable, validated Algorithm Snapshot models, cache, and diff support."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

# v2 fixes the recorded default for positional string parameters such as
# ValueModelMode.  Cache validation rejects v1 rather than letting a stale parse
# masquerade as a current compatible snapshot after a parser-schema upgrade.
SNAPSHOT_SCHEMA_VERSION = "algorithm-snapshot-v2"


def utc_now() -> str:
    """Return an ISO 8601 UTC timestamp with a stable Z suffix."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def source_sha256(source: str) -> str:
    """Hash source bytes exactly as decoded and persisted by this application."""

    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class ParsedParam(BaseModel):
    """A parsed Rust ``param!`` invocation or a structured parser diagnostic."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    rust_type: str | None = None
    config_key: str | None = None
    literal: str | None = None
    numeric_value: float | None = None
    raw_macro: str


class ExtractedSignal(BaseModel):
    """One relevant public parameter paired with its source-relation metadata."""

    model_config = ConfigDict(extra="forbid")

    parameter: str
    canonical_field: str
    relation: str
    numeric_value: float | None = None
    sign: Literal["positive", "negative", "zero", "unknown"] = "unknown"
    active_scorer_reference: bool | None = None
    source: str = "home-mixer/params/param.rs"


class SnapshotDiff(BaseModel):
    """Structured difference from the prior validated snapshot."""

    model_config = ConfigDict(extra="forbid")

    previous_commit: str | None = None
    commit_changed: bool = False
    source_changed: bool = False
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)
    mode_changed: bool = False
    identical: bool = False


class AlgorithmSnapshot(BaseModel):
    """Self-validating serialized public-source snapshot.

    ``parameter_source_content`` is retained so a cache can validate the stored
    hash without network access. It is public upstream source, never user
    Analytics or credentials.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SNAPSHOT_SCHEMA_VERSION
    repository: str = "xai-org/x-algorithm"
    branch: str = "main"
    commit_sha: str
    fetched_at_utc: str
    parameter_source_path: str = "home-mixer/params/param.rs"
    ranking_source_path: str = "home-mixer/scorers/ranking_scorer.rs"
    parameter_sync_date: str | None = None
    source_sha256: str
    ranking_source_sha256: str | None = None
    source_mode: Literal["live", "cached"] = "live"
    value_model_mode: str | None = None
    extracted_signals: list[ExtractedSignal] = Field(default_factory=list)
    parsed_params: list[ParsedParam] = Field(default_factory=list)
    expected_missing: list[str] = Field(default_factory=list)
    unsupported_params: list[str] = Field(default_factory=list)
    unparsed_params: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    active_scorer_coverage: float | None = None
    change_from_previous: SnapshotDiff = Field(default_factory=SnapshotDiff)
    parameter_source_content: str
    ranking_source_content: str | None = None

    @field_validator("commit_sha")
    @classmethod
    def full_sha(cls, value: str) -> str:
        if len(value) != 40 or any(char not in "0123456789abcdef" for char in value.lower()):
            raise ValueError("commit_sha must be a full 40-character hexadecimal SHA")
        return value.lower()

    @field_validator("schema_version")
    @classmethod
    def supported_schema(cls, value: str) -> str:
        if value != SNAPSHOT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported snapshot schema {value!r}; expected {SNAPSHOT_SCHEMA_VERSION!r}"
            )
        return value

    def validate_source_hashes(self) -> None:
        """Raise when a persisted cache has been corrupted or mismatched."""

        if source_sha256(self.parameter_source_content) != self.source_sha256:
            raise ValueError("parameter source SHA-256 does not match snapshot metadata")
        if self.ranking_source_content is not None and self.ranking_source_sha256 is not None:
            if source_sha256(self.ranking_source_content) != self.ranking_source_sha256:
                raise ValueError("ranking source SHA-256 does not match snapshot metadata")

    def with_cached_mode(self, warning: str) -> AlgorithmSnapshot:
        """Create an in-memory cache-use view without overwriting immutable source evidence."""

        warnings = [*self.warnings, warning]
        return self.model_copy(update={"source_mode": "cached", "warnings": warnings})


def snapshot_filename(snapshot: AlgorithmSnapshot) -> str:
    """Choose a deterministic immutable cache name from the full commit."""

    return f"snapshot-{snapshot.schema_version}-{snapshot.commit_sha}.json"


def write_snapshot(snapshot: AlgorithmSnapshot, directory: Path) -> Path:
    """Persist one validated snapshot without replacing an existing file."""

    snapshot.validate_source_hashes()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / snapshot_filename(snapshot)
    if path.exists():
        existing = load_snapshot(path)
        if existing.source_sha256 != snapshot.source_sha256:
            raise ValueError(f"immutable snapshot collision at {path}")
        return path
    payload = snapshot.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def load_snapshot(path: Path) -> AlgorithmSnapshot:
    """Load and validate an on-disk snapshot, including its embedded source hash."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshot = AlgorithmSnapshot.model_validate(payload)
        snapshot.validate_source_hashes()
        return snapshot
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as error:
        raise ValueError(f"invalid algorithm snapshot {path}: {error}") from error


def latest_valid_snapshot(directory: Path) -> tuple[AlgorithmSnapshot, Path] | None:
    """Return the newest valid cache entry, skipping invalid/corrupt candidates."""

    if not directory.exists():
        return None
    candidates = sorted(
        directory.glob("snapshot-*.json"), key=lambda item: item.stat().st_mtime, reverse=True
    )
    for path in candidates:
        try:
            return load_snapshot(path), path
        except ValueError:
            continue
    return None


def diff_snapshots(previous: AlgorithmSnapshot | None, current: AlgorithmSnapshot) -> SnapshotDiff:
    """Compare commit, source, parsed parameters, and selected value-model mode."""

    if previous is None:
        return SnapshotDiff()
    old = {param.symbol: param for param in previous.parsed_params}
    new = {param.symbol: param for param in current.parsed_params}
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(
        name
        for name in set(old) & set(new)
        if (
            old[name].literal != new[name].literal
            or old[name].numeric_value != new[name].numeric_value
            or old[name].config_key != new[name].config_key
            or old[name].rust_type != new[name].rust_type
        )
    )
    commit_changed = previous.commit_sha != current.commit_sha
    source_changed = previous.source_sha256 != current.source_sha256
    mode_changed = previous.value_model_mode != current.value_model_mode
    return SnapshotDiff(
        previous_commit=previous.commit_sha,
        commit_changed=commit_changed,
        source_changed=source_changed,
        added=added,
        removed=removed,
        changed=changed,
        mode_changed=mode_changed,
        identical=not (
            commit_changed or source_changed or added or removed or changed or mode_changed
        ),
    )

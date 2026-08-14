from __future__ import annotations

from pathlib import Path

import pytest

from x_algorithm_auditor.algorithm.fetcher import AlgorithmSourceError, SnapshotProvider
from x_algorithm_auditor.algorithm.parser import build_snapshot, parse_param_source
from x_algorithm_auditor.algorithm.registry import EXPECTED_SIGNAL_PARAMETERS, SIGNAL_RELATIONS
from x_algorithm_auditor.algorithm.snapshot import (
    diff_snapshots,
    latest_valid_snapshot,
    write_snapshot,
)

from .conftest import RUNTIME, representative_param_source, representative_ranking_source


def test_multiline_param_parser_extracts_known_positive_and_negative_weights() -> None:
    result = parse_param_source(representative_param_source())
    values = {param.symbol: param.numeric_value for param in result.params}
    assert values["FavoriteWeight"] == 0.5
    assert values["ReplyWeight"] == 5.0
    assert values["ReportWeight"] == -234.0
    assert values["ValueModelMode"] is None


def test_positional_string_default_is_not_mistaken_for_its_rust_type() -> None:
    source = 'param!(ValueModelMode, String, "rust_home_mixer_value_model_mode", "weighted")'
    snapshot = build_snapshot(
        parameter_source=source,
        ranking_source="ValueModelMode",
        commit_sha="0" * 40,
    )
    assert snapshot.value_model_mode == "weighted"
    assert not any("compatibility is reduced" in warning for warning in snapshot.warnings)


def test_missing_malformed_and_renamed_weights_are_diagnostics_not_a_crash() -> None:
    source = """
    param!( FavoriteWeight: f64 = 0.5, "favorite_weight" );
    param!( RenamedWeight: f64 = unknown_symbol, "renamed_weight" );
    """
    snapshot = build_snapshot(
        parameter_source=source,
        ranking_source="FavoriteWeight RenamedWeight",
        commit_sha="b" * 40,
    )
    assert "ReplyWeight" in snapshot.expected_missing
    assert "RenamedWeight" in snapshot.unsupported_params
    assert any(item.get("parameter") == "RenamedWeight" for item in snapshot.unparsed_params)
    assert any("possible renamed" in warning for warning in snapshot.warnings)
    assert snapshot.extracted_signals


def test_snapshot_cache_validates_hash_and_marks_cached(cached_snapshot_dir: Path) -> None:
    provider = SnapshotProvider()
    result = provider.acquire(cached_snapshot_dir, offline=True)
    assert result.used_cache is True
    assert result.snapshot.source_mode == "cached"
    assert result.snapshot.commit_sha == "a" * 40
    assert latest_valid_snapshot(cached_snapshot_dir) is not None


def test_invalid_cache_does_not_satisfy_offline_source_requirement() -> None:
    invalid = RUNTIME / "invalid-cache"
    invalid.mkdir(exist_ok=True)
    (invalid / "snapshot-bad.json").write_text("{}", encoding="utf-8")
    with pytest.raises(AlgorithmSourceError, match="no valid cached snapshot"):
        SnapshotProvider().acquire(invalid, offline=True)


def test_snapshot_diff_covers_identical_commit_only_changed_param_and_mode() -> None:
    first = build_snapshot(
        parameter_source=representative_param_source(),
        ranking_source=representative_ranking_source(),
        commit_sha="c" * 40,
    )
    identical = build_snapshot(
        parameter_source=representative_param_source(),
        ranking_source=representative_ranking_source(),
        commit_sha="c" * 40,
    )
    assert diff_snapshots(first, identical).identical
    commit_only = identical.model_copy(update={"commit_sha": "d" * 40})
    assert diff_snapshots(first, commit_only).commit_changed
    removed_source = representative_param_source().replace(
        'param!(\n    FutureWeight: f64 = 0.42,\n    "futureweight"\n);\n', ""
    )
    removed = build_snapshot(
        parameter_source=removed_source,
        ranking_source=representative_ranking_source(),
        commit_sha="9" * 40,
    )
    assert "FutureWeight" in diff_snapshots(first, removed).removed
    added = build_snapshot(
        parameter_source=representative_param_source()
        + '\nparam!(AddedWeight, f64, "added", 1.0);',
        ranking_source=representative_ranking_source(),
        commit_sha="8" * 40,
    )
    assert "AddedWeight" in diff_snapshots(first, added).added
    changed_source = representative_param_source().replace(
        "ReplyWeight: f64 = 5.0", "ReplyWeight: f64 = 6.0"
    )
    changed = build_snapshot(
        parameter_source=changed_source,
        ranking_source=representative_ranking_source(),
        commit_sha="e" * 40,
    )
    assert "ReplyWeight" in diff_snapshots(first, changed).changed
    altered_mode = build_snapshot(
        parameter_source=representative_param_source("gated_dwell_regret"),
        ranking_source=representative_ranking_source(),
        commit_sha="f" * 40,
    )
    assert diff_snapshots(first, altered_mode).mode_changed
    assert any("compatibility" in warning for warning in altered_mode.warnings)


def test_active_scorer_coverage_is_reduced_when_source_is_missing() -> None:
    snapshot = build_snapshot(
        parameter_source=representative_param_source(),
        ranking_source=None,
        commit_sha="1" * 40,
    )
    assert snapshot.active_scorer_coverage is None
    assert any("coverage reduced" in warning for warning in snapshot.warnings)


def test_bookmarks_have_no_invented_public_parameter() -> None:
    bookmarks = next(
        relation for relation in SIGNAL_RELATIONS if relation.canonical_field == "bookmarks"
    )
    assert bookmarks.parameter is None
    assert "BookmarkWeight" not in EXPECTED_SIGNAL_PARAMETERS


def test_immutable_snapshot_write_rejects_hash_collision(snapshot) -> None:
    directory = RUNTIME / "snapshot-collision"
    directory.mkdir(exist_ok=True)
    path = write_snapshot(snapshot, directory)
    assert path.exists()
    changed = snapshot.model_copy(update={"source_sha256": "0" * 64})
    with pytest.raises(ValueError, match="SHA-256"):
        write_snapshot(changed, directory)

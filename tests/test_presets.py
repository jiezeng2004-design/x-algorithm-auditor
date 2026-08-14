from __future__ import annotations

from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from x_algorithm_auditor.analytics.loader import load_analytics
from x_algorithm_auditor.cli import app
from x_algorithm_auditor.presets.loader import PresetLoadError, load_preset
from x_algorithm_auditor.scoring.common import load_scoring_config
from x_algorithm_auditor.scoring.pipeline import score_posts


def _valid_preset_text() -> str:
    return """schema_version: preset-v1
creator_goal: Turn qualified interest into repeatable account assets
niche: Synthetic creator examples
content_taxonomy_keywords:
  Comparison: [orbit-signal]
historical_baseline:
  follows_per_1k_impressions: 2.5
preferred_metrics: [Creator Conversion, follows_per_1k_impressions]
"""


def test_valid_preset_is_explicit_and_only_extends_local_classifier_context(
    tmp_path, snapshot, synthetic_csv
) -> None:
    preset_path = tmp_path / "preset.yaml"
    preset_path.write_text(_valid_preset_text(), encoding="utf-8")
    preset = load_preset(preset_path)
    assert preset.schema_version == "preset-v1"
    assert preset.content_taxonomy_keywords == {"Comparison": ["orbit-signal"]}

    data = load_analytics(synthetic_csv).data.copy()
    data.loc[data["post_id"] == "p0", "text"] = "orbit-signal field note"
    config = load_scoring_config()
    generic, _ = score_posts(data, snapshot, config)
    configured, _ = score_posts(data, snapshot, config, preset=preset)

    generic_row = generic.loc[generic["post_id"] == "p0"].iloc[0]
    configured_row = configured.loc[configured["post_id"] == "p0"].iloc[0]
    assert generic_row["content_type"] == "Other"
    assert configured_row["content_type"] == "Comparison"
    assert configured_row["content_classifier_version"] == "content-taxonomy-v1+preset-keywords"
    for column in (
        "alignment_score",
        "distribution_score",
        "conversion_score",
        "efficiency_score",
        "score_eligible",
        "cheap_exposure",
        "under_distributed_winner",
        "repackage_queue",
    ):
        assert configured_row[column] == generic_row[column]


def test_invalid_preset_has_actionable_schema_errors(tmp_path) -> None:
    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text(
        """schema_version: preset-v1
content_taxonomy_keywords:
  Private Rule: [secret conclusion]
scoring_weights:
  follows: 1.0
""",
        encoding="utf-8",
    )
    try:
        load_preset(invalid_path)
    except PresetLoadError as error:
        message = str(error)
    else:  # pragma: no cover - assertion keeps the raised error readable
        raise AssertionError("invalid preset unexpectedly loaded")
    assert "unsupported content type" in message
    assert "scoring_weights" in message
    assert "documented fields" in message


def test_generic_and_preset_cli_audits_are_isolated(
    tmp_path, cached_snapshot_dir: Path, synthetic_csv: Path
) -> None:
    preset_path = tmp_path / "preset.yaml"
    preset_path.write_text(_valid_preset_text(), encoding="utf-8")
    runner = CliRunner()

    generic_output = tmp_path / "generic"
    generic_result = runner.invoke(
        app,
        [
            "audit",
            str(synthetic_csv),
            "--offline",
            "--snapshot-dir",
            str(cached_snapshot_dir),
            "--output",
            str(generic_output),
        ],
    )
    assert generic_result.exit_code == 0, generic_result.output
    generic_report = next(generic_output.glob("audit-*.md")).read_text(encoding="utf-8")
    assert "Optional preset: none (generic core only)." in generic_report

    preset_output = tmp_path / "preset-output"
    preset_result = runner.invoke(
        app,
        [
            "audit",
            str(synthetic_csv),
            "--offline",
            "--snapshot-dir",
            str(cached_snapshot_dir),
            "--output",
            str(preset_output),
            "--preset",
            str(preset_path),
        ],
    )
    assert preset_result.exit_code == 0, preset_result.output
    preset_report = next(preset_output.glob("audit-*.md")).read_text(encoding="utf-8")
    assert "Optional preset: active (`preset-v1`)." in preset_report
    assert "comparison prior only" in preset_report
    assert "cannot override snapshot provenance" in preset_report

    generic_csv = pd.read_csv(generic_output / "scored-posts.csv")
    preset_csv = pd.read_csv(preset_output / "scored-posts.csv")
    stable_columns = [
        "post_id",
        "alignment_score",
        "distribution_score",
        "conversion_score",
        "efficiency_score",
        "score_eligible",
        "cheap_exposure",
        "under_distributed_winner",
        "repackage_queue",
    ]
    pd.testing.assert_frame_equal(
        generic_csv.loc[:, stable_columns], preset_csv.loc[:, stable_columns], check_dtype=False
    )

    invalid_path = tmp_path / "bad.yaml"
    invalid_path.write_text("schema_version: wrong-version\n", encoding="utf-8")
    failure = runner.invoke(
        app,
        [
            "audit",
            str(synthetic_csv),
            "--offline",
            "--snapshot-dir",
            str(cached_snapshot_dir),
            "--output",
            str(tmp_path / "bad-output"),
            "--preset",
            str(invalid_path),
        ],
    )
    assert failure.exit_code == 4
    assert "invalid preset" in failure.output
    assert "schema_version" in failure.output

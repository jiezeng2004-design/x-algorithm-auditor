from __future__ import annotations

from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from x_algorithm_auditor.algorithm.parser import build_snapshot
from x_algorithm_auditor.analytics.deduplicate import deduplicate_posts
from x_algorithm_auditor.analytics.loader import CROSS_EXPORT_WARNING, load_analytics
from x_algorithm_auditor.cli import app
from x_algorithm_auditor.reports.csv_export import build_csv_frame
from x_algorithm_auditor.reports.markdown import PROXY_DISCLAIMER, render_markdown
from x_algorithm_auditor.scoring.common import load_scoring_config
from x_algorithm_auditor.scoring.pipeline import score_posts

from .conftest import RUNTIME, representative_param_source


def test_markdown_has_required_sections_disclaimer_cached_provenance_and_unavailable(
    snapshot, synthetic_csv: Path
) -> None:
    loaded = load_analytics(synthetic_csv)
    deduped = deduplicate_posts(loaded.data)
    scored, summary = score_posts(
        deduped.data, snapshot.with_cached_mode("test cache"), load_scoring_config()
    )
    report = render_markdown(
        data=scored,
        snapshot=snapshot.with_cached_mode("test cache"),
        quality=loaded.quality,
        deduplication=deduped.summary,
        scoring=summary,
    )
    for section in (
        "Executive Summary",
        "Data Coverage",
        "Algorithm Snapshot",
        "Observable Signals",
        "Unobservable Signals",
        "Core Winners",
        "Cheap Exposure",
        "Under-distributed Winners",
        "Traffic Without Asset",
        "Content Type Analysis",
        "Operating Recommendations",
        "Methodology Notes",
        "Limitations",
    ):
        assert section in report
    assert PROXY_DISCLAIMER in report
    assert "Algorithm source: **cached**" in report
    assert "Phase 2 not enabled" not in report
    assert "Core Winner is a stricter badge" in report
    assert "Classifier: deterministic local heuristic" in report
    assert "**Experimental.** Current content classification is heuristic" in report
    assert CROSS_EXPORT_WARNING in report
    assert "unavailable" in report
    assert "Absent source columns" in report
    assert "Missing source cells" in report
    assert "Rates unavailable: zero impressions" in report
    assert "none — contextual only" in report
    assert "BookmarkWeight" not in report


def test_markdown_marks_unverified_active_scorer_source(synthetic_csv: Path) -> None:
    unverified = build_snapshot(
        parameter_source=representative_param_source(),
        ranking_source=None,
        commit_sha="5" * 40,
    )
    loaded = load_analytics(synthetic_csv)
    deduped = deduplicate_posts(loaded.data)
    scored, summary = score_posts(deduped.data, unverified, load_scoring_config())
    report = render_markdown(
        data=scored,
        snapshot=unverified,
        quality=loaded.quality,
        deduplication=deduped.summary,
        scoring=summary,
    )
    assert "Active scorer verification: **unverified**" in report
    assert "not claimed as active-verified" in report


def test_csv_keeps_observed_zero_numeric_and_missing_empty(snapshot, synthetic_csv: Path) -> None:
    loaded = load_analytics(synthetic_csv)
    scored, _ = score_posts(loaded.data, snapshot, load_scoring_config())
    export = build_csv_frame(scored, "cached", snapshot.commit_sha)
    zero_row = export.loc[export["post_id"] == "zero-impressions"].iloc[0]
    assert zero_row["impressions"] == 0
    assert pd.isna(zero_row["reply_rate"])
    assert pd.isna(zero_row["alignment_score"])
    assert "observable_signal_count" in export.columns
    assert "cheap_exposure" in export.columns


def test_cli_help_and_offline_csv_xlsx_audits(
    cached_snapshot_dir: Path, synthetic_csv: Path, synthetic_xlsx: Path
) -> None:
    runner = CliRunner()
    assert runner.invoke(app, ["--help"]).exit_code == 0
    assert runner.invoke(app, ["audit", "--help"]).exit_code == 0
    csv_output = RUNTIME / "csv-report"
    csv_result = runner.invoke(
        app,
        [
            "audit",
            str(synthetic_csv),
            "--offline",
            "--snapshot-dir",
            str(cached_snapshot_dir),
            "--output",
            str(csv_output),
        ],
    )
    assert csv_result.exit_code == 0, csv_result.output
    assert (csv_output / "scored-posts.csv").exists()
    assert list(csv_output.glob("audit-*.md"))
    xlsx_output = RUNTIME / "xlsx-report"
    xlsx_result = runner.invoke(
        app,
        [
            "audit",
            str(synthetic_xlsx),
            "--offline",
            "--snapshot-dir",
            str(cached_snapshot_dir),
            "--output",
            str(xlsx_output),
        ],
    )
    assert xlsx_result.exit_code == 0, xlsx_result.output
    assert (xlsx_output / "scored-posts.csv").exists()


def test_cli_detector_rich_csv_and_xlsx_prove_phase_two_flags(
    cached_snapshot_dir: Path, detector_rich_csv: Path, detector_rich_xlsx: Path
) -> None:
    runner = CliRunner()
    for input_path, label in ((detector_rich_csv, "csv"), (detector_rich_xlsx, "xlsx")):
        output = RUNTIME / f"detector-rich-{label}-report"
        result = runner.invoke(
            app,
            [
                "audit",
                str(input_path),
                "--offline",
                "--snapshot-dir",
                str(cached_snapshot_dir),
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0, result.output
        scored_path = max(output.glob("scored-posts*.csv"), key=lambda path: path.stat().st_mtime)
        scored = pd.read_csv(scored_path)
        cheap = scored.loc[scored["post_id"] == "cheap-exposure"].iloc[0]
        under = scored.loc[scored["post_id"] == "under-winner"].iloc[0]
        tiny = scored.loc[scored["post_id"] == "tiny"].iloc[0]
        assert cheap["cheap_exposure"]
        assert under["under_distributed_winner"]
        assert under["repackage_queue"]
        assert not tiny["cheap_exposure"]
        assert not tiny["under_distributed_winner"]
        report_path = max(output.glob("audit-*.md"), key=lambda path: path.stat().st_mtime)
        report = report_path.read_text(encoding="utf-8")
        assert "Repackage Queue" in report
        assert "Phase 2 not enabled" not in report


def test_cli_failure_codes_distinguish_bad_input_and_missing_offline_snapshot() -> None:
    runner = CliRunner()
    missing_input = runner.invoke(app, ["audit", str(RUNTIME / "nope.csv"), "--offline"])
    assert missing_input.exit_code == 2
    input_path = RUNTIME / "input.csv"
    pd.DataFrame({"Post ID": ["x"], "Impressions": [1]}).to_csv(input_path, index=False)
    source_failure = runner.invoke(
        app,
        [
            "audit",
            str(input_path),
            "--offline",
            "--snapshot-dir",
            str(RUNTIME / "missing-snapshots"),
        ],
    )
    assert source_failure.exit_code == 3

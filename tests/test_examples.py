from __future__ import annotations

from pathlib import Path

import pandas as pd

from x_algorithm_auditor.analytics.deduplicate import deduplicate_posts
from x_algorithm_auditor.analytics.loader import load_analytics
from x_algorithm_auditor.scoring.common import load_scoring_config
from x_algorithm_auditor.scoring.pipeline import score_posts

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CSV = PROJECT_ROOT / "examples" / "analytics-example.csv"
EXAMPLE_XLSX = PROJECT_ROOT / "examples" / "analytics-example.xlsx"


def test_synthetic_csv_and_artifact_tool_xlsx_examples_normalize_and_score_equivalently(
    snapshot,
) -> None:
    """Keep the published synthetic formats interchangeable for the CLI path."""

    csv_loaded = load_analytics(EXAMPLE_CSV)
    xlsx_loaded = load_analytics(EXAMPLE_XLSX)
    pd.testing.assert_frame_equal(
        csv_loaded.data.drop(columns=["source_file"]),
        xlsx_loaded.data.drop(columns=["source_file"]),
    )
    assert csv_loaded.quality.as_dict() == xlsx_loaded.quality.as_dict()

    csv_deduped = deduplicate_posts(csv_loaded.data)
    xlsx_deduped = deduplicate_posts(xlsx_loaded.data)
    assert (csv_deduped.summary.input_rows, csv_deduped.summary.output_posts) == (16, 15)
    assert csv_deduped.summary.as_dict() == xlsx_deduped.summary.as_dict()

    config = load_scoring_config()
    csv_scored, _ = score_posts(csv_deduped.data, snapshot, config)
    xlsx_scored, _ = score_posts(xlsx_deduped.data, snapshot, config)
    comparison_columns = [
        "post_id",
        "impressions",
        "alignment_score",
        "distribution_score",
        "conversion_score",
        "efficiency_score",
        "score_eligible",
        "cheap_exposure",
        "under_distributed_winner",
        "repackage_queue",
        "content_type",
    ]
    pd.testing.assert_frame_equal(
        csv_scored.loc[:, comparison_columns],
        xlsx_scored.loc[:, comparison_columns],
        check_dtype=False,
    )
    tiny = csv_scored.loc[csv_scored["post_id"] == "tiny"].iloc[0]
    assert pd.isna(tiny["alignment_score"])
    assert not tiny["cheap_exposure"]
    assert not tiny["under_distributed_winner"]

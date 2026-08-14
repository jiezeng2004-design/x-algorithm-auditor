"""Stable machine-readable post-level CSV export."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from x_algorithm_auditor.analytics.normalize import RATE_FIELD_NAMES

CSV_COLUMNS: tuple[str, ...] = (
    "post_id",
    "canonical_url",
    "created_at",
    "text",
    "post_type",
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
    *RATE_FIELD_NAMES.values(),
    *(f"stabilized_{rate_name}" for rate_name in RATE_FIELD_NAMES.values()),
    *(f"score_{rate_name}" for rate_name in RATE_FIELD_NAMES.values()),
    "follows_per_1k_impressions",
    "reliability",
    "sample_confidence",
    "score_eligible",
    "alignment_score",
    "distribution_score",
    "conversion_score",
    "efficiency_score",
    "alignment_raw",
    "alignment_coverage_adjusted",
    "alignment_weighted_coverage",
    "alignment_used_signal_count",
    "alignment_reason",
    "conversion_weight_coverage",
    "conversion_reason",
    "efficiency_weight_coverage",
    "efficiency_reason",
    "alignment_signal_details",
    "quadrant",
    "core_winner",
    "core_winner_reason",
    "cheap_exposure",
    "cheap_exposure_reason",
    "cheap_exposure_trigger_metrics",
    "under_distributed_winner",
    "under_distributed_winner_reason",
    "under_distributed_winner_trigger_metrics",
    "repackage_queue",
    "repackage_queue_reason",
    "detector_eligible_cohort_size",
    "content_type",
    "content_type_confidence",
    "content_type_reason",
    "content_classifier_version",
    "dedup_identity_method",
    "dedup_identity_warning",
    "observable_signal_count",
    "algorithm_source_mode",
    "algorithm_snapshot_commit",
)


def build_csv_frame(data: pd.DataFrame, source_mode: str, snapshot_commit: str) -> pd.DataFrame:
    """Create the documented stable field order, keeping missing values null."""

    output = data.copy()
    output["observable_signal_count"] = output.get(
        "alignment_used_signal_count", pd.Series(0, index=output.index, dtype="Int64")
    )
    output["algorithm_source_mode"] = source_mode
    output["algorithm_snapshot_commit"] = snapshot_commit
    for column in CSV_COLUMNS:
        if column not in output:
            output[column] = pd.NA
    return output.loc[:, list(CSV_COLUMNS)]


def write_scored_csv(
    data: pd.DataFrame,
    path: Path,
    *,
    source_mode: str,
    snapshot_commit: str,
) -> Path:
    """Write stable UTF-8 CSV with blank nullable values and numeric observed zeroes."""

    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    build_csv_frame(data, source_mode, snapshot_commit).to_csv(path, index=False, encoding="utf-8")
    return path

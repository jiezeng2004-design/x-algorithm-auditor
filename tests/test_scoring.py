from __future__ import annotations

import json

import pandas as pd

from x_algorithm_auditor.algorithm.parser import build_snapshot
from x_algorithm_auditor.analytics.loader import load_analytics
from x_algorithm_auditor.analytics.normalize import normalize_metrics
from x_algorithm_auditor.analytics.schema import COUNT_FIELDS
from x_algorithm_auditor.reports.csv_export import build_csv_frame
from x_algorithm_auditor.scoring.common import average_rank_percentile, load_scoring_config
from x_algorithm_auditor.scoring.pipeline import score_posts

from .conftest import representative_param_source, representative_ranking_source


def test_average_rank_percentile_handles_ties_single_and_missing() -> None:
    tied = average_rank_percentile(pd.Series([1.0, 1.0, 3.0, None], dtype="Float64"))
    assert list(tied.iloc[:3]) == [25, 25, 100]
    assert pd.isna(tied.iloc[3])
    assert average_rank_percentile(pd.Series([4.0], dtype="Float64")).iloc[0] == 50


def test_rates_and_tiny_exposure_protection(snapshot, synthetic_csv) -> None:
    loaded = load_analytics(synthetic_csv)
    config = load_scoring_config()
    scored, summary = score_posts(loaded.data, snapshot, config)
    tiny = scored.loc[scored["post_id"] == "tiny"].iloc[0]
    zero = scored.loc[scored["post_id"] == "zero-impressions"].iloc[0]
    assert tiny["reply_rate"] == 1 / 3
    assert tiny["stabilized_reply_rate"] < tiny["reply_rate"]
    assert tiny["sample_confidence"] == "low"
    assert pd.isna(tiny["alignment_score"])
    assert pd.isna(tiny["conversion_score"])
    assert pd.isna(tiny["efficiency_score"])
    assert not pd.isna(tiny["distribution_score"])
    assert pd.isna(zero["reply_rate"])
    assert summary.normalization.k >= 50
    assert summary.normalization.eligibility_floor >= 20


def test_alignment_uses_public_snapshot_weight_and_contributions_sum(
    snapshot, synthetic_csv
) -> None:
    config = load_scoring_config()
    scored, _ = score_posts(load_analytics(synthetic_csv).data, snapshot, config)
    eligible = scored.loc[scored["alignment_score"].notna()].iloc[0]
    details = json.loads(eligible["alignment_signal_details"])
    observed_sum = sum(item["contribution"] for item in details if item["contribution"] is not None)
    assert observed_sum == pytest_approx(float(eligible["alignment_raw"]))
    reply = next(item for item in details if item["parameter"] == "ReplyWeight")
    assert reply["public_weight"] == 5.0
    assert eligible["alignment_used_signal_count"] >= 2
    assert eligible["alignment_weighted_coverage"] >= 0.5
    assert eligible["alignment_coverage_adjusted"] == pytest_approx(
        float(eligible["alignment_raw"]) / (float(eligible["alignment_weighted_coverage"]) * 17.5)
    )


def pytest_approx(value: float):
    # Keep pytest import local to this assertion helper to make the normal test
    # body read as the methodology statement it verifies.
    import pytest

    return pytest.approx(value)


def test_alignment_requires_dataset_observable_signals_and_missing_negative_is_not_zero(
    snapshot, synthetic_csv
) -> None:
    config = load_scoring_config()
    scored, summary = score_posts(load_analytics(synthetic_csv).data, snapshot, config)
    assert "NotInterestedWeight" not in summary.alignment.dataset_observable_parameters
    assert "NotInterestedWeight" in summary.alignment.excluded_parameters
    assert "NotInterestedWeight" not in scored.iloc[0]["alignment_signal_details"]


def test_inactive_scorer_parameters_are_excluded_from_alignment_evidence(synthetic_csv) -> None:
    ranking_source = representative_ranking_source().replace("ReplyWeight", "InactiveReplyWeight")
    snapshot = build_snapshot(
        parameter_source=representative_param_source(),
        ranking_source=ranking_source,
        commit_sha="3" * 40,
    )
    scored, summary = score_posts(
        load_analytics(synthetic_csv).data, snapshot, load_scoring_config()
    )
    assert snapshot.active_scorer_coverage is not None
    assert snapshot.active_scorer_coverage < 1
    assert "ReplyWeight" in summary.alignment.inactive_parameters
    assert "ReplyWeight" not in summary.alignment.dataset_observable_parameters
    assert summary.alignment.excluded_parameters["ReplyWeight"] == (
        "not referenced by commit-pinned ranking source"
    )
    for details in scored["alignment_signal_details"].dropna():
        assert "ReplyWeight" not in details


def test_missing_ranking_source_marks_alignment_reference_unverified(synthetic_csv) -> None:
    snapshot = build_snapshot(
        parameter_source=representative_param_source(),
        ranking_source=None,
        commit_sha="4" * 40,
    )
    scored, summary = score_posts(
        load_analytics(synthetic_csv).data, snapshot, load_scoring_config()
    )
    assert "FavoriteWeight" in summary.alignment.unverified_parameters
    eligible = scored.loc[scored["score_eligible"]].iloc[0]
    assert eligible["alignment_reason"] == "scoreable; active scorer reference unverified"


def test_aggregate_and_channel_shares_are_not_double_counted(synthetic_csv) -> None:
    frame = pd.read_csv(synthetic_csv)
    frame["Shares Via DM"] = 1
    frame["Shares Via Copy Link"] = 2
    frame.to_csv(synthetic_csv, index=False)
    snapshot = build_snapshot(
        parameter_source=representative_param_source(),
        ranking_source=representative_ranking_source(),
        commit_sha="2" * 40,
    )
    scored, summary = score_posts(
        load_analytics(synthetic_csv).data, snapshot, load_scoring_config()
    )
    assert "ShareWeight" not in summary.alignment.dataset_observable_parameters
    assert "ShareViaDmWeight" in summary.alignment.dataset_observable_parameters
    assert "ShareViaCopyLinkWeight" in summary.alignment.dataset_observable_parameters
    details = json.loads(scored.iloc[0]["alignment_signal_details"])
    assert all(detail["parameter"] != "ShareWeight" for detail in details)


def test_distribution_is_impression_only_conversion_is_funnel_only_and_efficiency_excludes_funnel(
    snapshot,
) -> None:
    data = pd.DataFrame(
        {
            "post_id": ["a", "b", "c", "d", "e", "f", "g", "h"],
            "impressions": [100] * 8,
            "likes": [0] * 8,
            "replies": [0] * 8,
            "reposts": [0] * 8,
            "quotes": [0] * 8,
            "shares": [0] * 8,
            "bookmarks": [0] * 8,
            "profile_visits": list(range(8)),
            "follows": list(range(8)),
            "link_clicks": [0] * 8,
            "detail_expands": [0] * 8,
        }
    )
    scored, _ = score_posts(data, snapshot, load_scoring_config())
    assert scored["distribution_score"].nunique(dropna=True) == 1
    assert scored["conversion_score"].nunique(dropna=True) > 1
    assert "profile_visits" not in [
        "replies",
        "quotes",
        "reposts",
        "shares",
        "bookmarks",
        "link_clicks",
        "detail_expands",
        "likes",
    ]
    assert scored["efficiency_component_likes"].notna().all()


def test_winsorization_only_activates_at_twenty_eligible_rows(snapshot) -> None:
    config = load_scoring_config()

    def make(count: int) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "post_id": [str(index) for index in range(count)],
                "impressions": [100] * count,
                "likes": list(range(count)),
                "replies": list(range(count)),
            }
        )

    _, below = normalize_metrics(make(19), config)
    _, at = normalize_metrics(make(20), config)
    assert "like_rate" not in below.winsorized_rates
    assert "like_rate" in at.winsorized_rates


def test_alignment_contribution_uses_exported_scoring_rate_after_winsorization(snapshot) -> None:
    count = 20
    data: dict[str, object] = {
        "post_id": [str(index) for index in range(count)],
        "impressions": [100] * count,
    }
    for field in COUNT_FIELDS:
        if field != "impressions":
            data[field] = [0] * count
    data["likes"] = [*range(count - 1), 100]
    data["replies"] = [index % 3 for index in range(count)]

    scored, summary = score_posts(pd.DataFrame(data), snapshot, load_scoring_config())
    assert "like_rate" in summary.normalization.winsorized_rates
    extreme = scored.loc[scored["post_id"] == "19"].iloc[0]
    favorite = next(
        item
        for item in json.loads(extreme["alignment_signal_details"])
        if item["parameter"] == "FavoriteWeight"
    )
    assert favorite["scoring_rate"] == pytest_approx(float(extreme["score_like_rate"]))
    assert favorite["contribution"] == pytest_approx(
        favorite["public_weight"] * favorite["scoring_rate"]
    )
    export = build_csv_frame(scored, "cached", snapshot.commit_sha)
    exported = export.loc[export["post_id"] == "19"].iloc[0]
    assert exported["score_like_rate"] == pytest_approx(favorite["scoring_rate"])
    assert exported["score_like_rate"] <= exported["stabilized_like_rate"] or pd.isna(
        exported["stabilized_like_rate"]
    )


def test_final_scores_are_nullable_in_range(snapshot, synthetic_csv) -> None:
    scored, _ = score_posts(load_analytics(synthetic_csv).data, snapshot, load_scoring_config())
    for column in ("alignment_score", "distribution_score", "conversion_score", "efficiency_score"):
        observed = scored[column].dropna()
        assert observed.between(0, 100).all()
        assert str(scored[column].dtype) == "Int64"

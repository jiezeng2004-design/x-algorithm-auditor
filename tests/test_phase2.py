from __future__ import annotations

import pandas as pd

from x_algorithm_auditor.analytics.deduplicate import deduplicate_posts
from x_algorithm_auditor.analytics.loader import load_analytics
from x_algorithm_auditor.content.analysis import (
    ContentAnalysisSummary,
    ContentTypeAggregate,
    aggregate_content_types,
)
from x_algorithm_auditor.content.classifier import (
    ContentClassification,
    DeterministicContentClassifier,
    classify_posts,
)
from x_algorithm_auditor.detection.detectors import apply_detectors
from x_algorithm_auditor.detection.quadrants import (
    INSUFFICIENT_DATA,
    QUADRANT_A,
    QUADRANT_B,
    QUADRANT_C,
    QUADRANT_D,
    classify_quadrants,
)
from x_algorithm_auditor.recommendations.engine import generate_recommendations
from x_algorithm_auditor.reports.csv_export import build_csv_frame
from x_algorithm_auditor.reports.markdown import render_markdown
from x_algorithm_auditor.scoring.common import load_scoring_config
from x_algorithm_auditor.scoring.pipeline import score_posts


def test_quadrants_are_exhaustive_at_boundary_and_core_badge_is_stricter() -> None:
    frame = pd.DataFrame(
        {
            "score_eligible": [True, True, True, True, True, True, False],
            "alignment_score": [50, 50, 49, 49, pd.NA, 75, 100],
            "conversion_score": [50, 49, 50, 49, 100, 75, 100],
            "alignment_weighted_coverage": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1.0],
        }
    )
    scored, summary = classify_quadrants(frame, load_scoring_config())
    assert list(scored["quadrant"]) == [
        QUADRANT_A,
        QUADRANT_B,
        QUADRANT_C,
        QUADRANT_D,
        INSUFFICIENT_DATA,
        QUADRANT_A,
        INSUFFICIENT_DATA,
    ]
    assert list(scored["core_winner"]) == [False, False, False, False, False, True, False]
    assert scored.loc[5, "core_winner_reason"] == "qualified core winner badge"
    assert summary.core_winner_count == 1


def test_detectors_require_every_condition_boundary_cohort_and_observed_scores() -> None:
    frame = pd.DataFrame(
        {
            "score_eligible": [True, True, True, True, True, True, True, True, False, True],
            "distribution_score": [75, 40, 74, 75, 75, 41, 40, 40, 100, 75],
            "conversion_score": [25, 75, 25, 26, 25, 75, 74, 75, 0, pd.NA],
            "efficiency_score": [25, 75, 25, 25, 26, 75, 75, 74, 0, 25],
        }
    )
    scored, summary = apply_detectors(frame, load_scoring_config())
    assert summary.eligible_cohort_size == 8
    assert scored.loc[0, "cheap_exposure"]
    assert scored.loc[1, "under_distributed_winner"]
    assert scored.loc[1, "repackage_queue"]
    assert not scored.loc[2, "cheap_exposure"]
    assert not scored.loc[3, "cheap_exposure"]
    assert not scored.loc[4, "cheap_exposure"]
    assert not scored.loc[5, "under_distributed_winner"]
    assert not scored.loc[6, "under_distributed_winner"]
    assert not scored.loc[7, "under_distributed_winner"]
    assert not scored.loc[8, "cheap_exposure"]
    assert not scored.loc[9, "cheap_exposure"]
    assert "required Distribution" in scored.loc[9, "cheap_exposure_reason"]
    assert '"eligible_detector_cohort": 8' in scored.loc[0, "cheap_exposure_trigger_metrics"]

    too_small, small_summary = apply_detectors(frame.iloc[:7], load_scoring_config())
    assert small_summary.eligible_cohort_size == 7
    assert not too_small["cheap_exposure"].any()
    assert not too_small["under_distributed_winner"].any()
    assert "below 8" in too_small.loc[0, "cheap_exposure_reason"]


def test_classifier_metadata_precedence_determinism_version_reason_and_replacement() -> None:
    classifier = DeterministicContentClassifier()
    reply = classifier.classify(text="AI news tool tutorial", post_type="Reply")
    quote = classifier.classify(text="tool notes", post_type="Quote")
    thread = classifier.classify(text="tool notes", post_type="Thread")
    assert (reply.content_type, reply.confidence) == ("Reply", "high")
    assert quote.content_type == "Quote"
    assert thread.content_type == "Thread"
    assert "metadata" in reply.reason
    assert reply.version == "content-taxonomy-v1"
    assert classifier.classify(text="AI 新闻发布", post_type="Post").content_type == "AI News"
    assert classifier.classify(text="如何完成这个步骤", post_type="Post").content_type == "Tutorial"
    assert classifier.classify(text="A versus B", post_type="Post").content_type == "Comparison"
    assert (
        classifier.classify(text="开源项目构建记录", post_type="Post").content_type
        == "Builder / Project"
    )
    assert classifier.classify(text="感谢社区", post_type="Post").content_type == "Social"

    input_frame = pd.DataFrame(
        {"text": ["How to use this tool", "plain note"], "post_type": ["Post", "Post"]}
    )
    first = classify_posts(input_frame, classifier)
    second = classify_posts(input_frame, classifier)
    pd.testing.assert_frame_equal(first, second)
    assert first.loc[0, "content_type"] == "Tool Hands-on"
    assert first.loc[1, "content_type"] == "Other"

    class StubClassifier:
        version = "stub-v1"

        def classify(self, *, text: object, post_type: object) -> ContentClassification:
            return ContentClassification("Custom", "high", "test replacement", self.version)

    replaced = classify_posts(input_frame, StubClassifier())
    assert set(replaced["content_type"]) == {"Custom"}
    assert set(replaced["content_classifier_version"]) == {"stub-v1"}


def test_content_type_aggregates_mark_low_samples_insufficient() -> None:
    frame = pd.DataFrame(
        {
            "content_type": ["Tool Hands-on"] * 3 + ["AI News"] * 2,
            "score_eligible": [True, True, True, True, True],
            "impressions": [100, 200, 300, 400, 500],
            "alignment_score": [70, 80, 90, 20, 30],
            "distribution_score": [20, 40, 60, 80, 100],
            "conversion_score": [70, 80, 90, 20, 30],
            "efficiency_score": [60, 70, 80, 20, 30],
            "profile_visit_rate": [0.01, 0.02, 0.03, 0.001, 0.002],
            "follows_per_1k_impressions": [10, 20, 30, 1, 2],
            "cheap_exposure": [False, False, False, True, False],
            "under_distributed_winner": [False, True, False, False, False],
        }
    )
    summary = aggregate_content_types(frame, load_scoring_config())
    tool = summary.by_type("Tool Hands-on")
    news = summary.by_type("AI News")
    assert tool is not None and news is not None
    assert tool.sample_sufficient and tool.eligible_post_count == 3
    assert tool.median_follows_per_1k_impressions == 20
    assert tool.under_distributed_winner_ratio == 1 / 3
    assert not news.sample_sufficient and news.eligible_post_count == 2
    assert news.cheap_exposure_ratio == 0.5


def _aggregate(
    content_type: str,
    *,
    eligible: int,
    follows_per_1k: float | None,
    cheap_ratio: float | None,
) -> ContentTypeAggregate:
    return ContentTypeAggregate(
        content_type=content_type,
        post_count=eligible,
        eligible_post_count=eligible,
        sample_sufficient=eligible >= 3,
        median_impressions=100.0,
        median_alignment_score=75.0,
        median_distribution_score=50.0,
        median_conversion_score=75.0,
        median_efficiency_score=75.0,
        median_profile_visit_rate=0.01,
        median_follows_per_1k_impressions=follows_per_1k,
        cheap_exposure_ratio=cheap_ratio,
        under_distributed_winner_ratio=0.0,
    )


def test_recommendations_keep_evidence_baseline_sample_and_zero_baseline_guard() -> None:
    content = ContentAnalysisSummary(
        aggregates=(
            _aggregate("Tool Hands-on", eligible=3, follows_per_1k=2.0, cheap_ratio=0.0),
            _aggregate("AI News", eligible=3, follows_per_1k=0.5, cheap_ratio=0.5),
        ),
        account_baselines={
            "median_follows_per_1k_impressions": 1.0,
            "cheap_exposure_ratio": 0.0,
        },
        minimum_eligible_sample=3,
    )
    recommendations = generate_recommendations(
        pd.DataFrame({"repackage_queue": [False]}), content
    ).recommendations
    follow = next(item for item in recommendations if item.category == "content_type_candidate")
    cheap = next(
        item for item in recommendations if item.category == "traffic_without_asset_review"
    )
    assert follow.sample_n == 3
    assert follow.supporting_metric == "median follows per 1k impressions"
    assert follow.comparison_kind == "ratio"
    assert cheap.comparison_kind == "absolute_difference"
    assert "ratio" not in cheap.comparison_kind
    assert cheap.baseline == "account eligible ratio 0.0000"

    insufficient = ContentAnalysisSummary(
        aggregates=(_aggregate("Other", eligible=2, follows_per_1k=9.0, cheap_ratio=1.0),),
        account_baselines={
            "median_follows_per_1k_impressions": 1.0,
            "cheap_exposure_ratio": 0.0,
        },
        minimum_eligible_sample=3,
    )
    no_evidence = generate_recommendations(
        pd.DataFrame({"repackage_queue": [False]}), insufficient
    ).recommendations
    assert len(no_evidence) == 1
    assert no_evidence[0].category == "insufficient_evidence"
    assert no_evidence[0].title == "Insufficient evidence"


def test_detector_rich_pipeline_report_and_csv_keep_phase_two_evidence(
    snapshot, detector_rich_csv
) -> None:
    loaded = load_analytics(detector_rich_csv)
    scored, summary = score_posts(loaded.data, snapshot, load_scoring_config())
    cheap = scored.loc[scored["post_id"] == "cheap-exposure"].iloc[0]
    under = scored.loc[scored["post_id"] == "under-winner"].iloc[0]
    tiny = scored.loc[scored["post_id"] == "tiny"].iloc[0]
    assert cheap["cheap_exposure"]
    assert under["under_distributed_winner"]
    assert under["repackage_queue"]
    assert not tiny["cheap_exposure"]
    assert not tiny["under_distributed_winner"]
    assert summary.detection.eligible_cohort_size >= 8
    assert scored.loc[scored["repackage_queue"], "under_distributed_winner"].all()
    report = render_markdown(
        data=scored,
        snapshot=snapshot,
        quality=loaded.quality,
        deduplication=deduplicate_posts(loaded.data).summary,
        scoring=summary,
    )
    assert "Phase 2 not enabled" not in report
    assert "Repackage Queue" in report
    assert "cheap-exposure" in report
    assert "under-winner" in report
    assert "qualified conjunctive cheap exposure rule" in report
    assert "qualified conjunctive under-distributed winner rule" in report
    assert "Operating Recommendations" in report
    export = build_csv_frame(scored, "cached", snapshot.commit_sha)
    required = {
        "core_winner",
        "cheap_exposure_reason",
        "cheap_exposure_trigger_metrics",
        "under_distributed_winner_reason",
        "under_distributed_winner_trigger_metrics",
        "repackage_queue",
        "content_type_confidence",
        "content_type_reason",
        "content_classifier_version",
    }
    assert required.issubset(export.columns)

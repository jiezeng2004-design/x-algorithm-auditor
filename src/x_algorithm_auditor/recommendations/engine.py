"""Conservative recommendations derived only from this audit's retained evidence."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from x_algorithm_auditor.content.analysis import ContentAnalysisSummary, ContentTypeAggregate


@dataclass(frozen=True)
class Recommendation:
    """Structured evidence supporting one noncausal operating suggestion."""

    recommendation_id: str
    category: str
    title: str
    action: str
    supporting_metric: str
    observed_value: str
    baseline: str
    sample_n: int
    comparison_kind: str
    comparison_value: str
    uncertainty: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RecommendationSummary:
    """Ordered recommendations, including an explicit no-evidence outcome."""

    recommendations: tuple[Recommendation, ...]


def _observed(value: object) -> bool:
    return value is not None and value is not pd.NA and not pd.isna(value)


def _comparison(observed: float, baseline: float) -> tuple[str, str]:
    """Use no ratio where an account baseline is zero."""

    if baseline == 0:
        return "absolute_difference", f"{observed - baseline:.4f}"
    return "ratio", f"{observed / baseline:.2f}x"


def _best_above_baseline(
    aggregates: tuple[ContentTypeAggregate, ...], *, metric: str, baseline: float | None
) -> ContentTypeAggregate | None:
    if baseline is None:
        return None
    candidates = [
        aggregate
        for aggregate in aggregates
        if aggregate.sample_sufficient
        and _observed(getattr(aggregate, metric))
        and float(getattr(aggregate, metric)) > baseline
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda aggregate: float(getattr(aggregate, metric)))


def _post_label(row: pd.Series, index: object) -> str:
    post_id = row.get("post_id")
    if _observed(post_id):
        return str(post_id)
    return f"row-{index}"


def generate_recommendations(
    frame: pd.DataFrame, content: ContentAnalysisSummary
) -> RecommendationSummary:
    """Produce only evidence-anchored suggestions or an explicit insufficiency result."""

    recommendations: list[Recommendation] = []
    if "repackage_queue" in frame:
        queued = frame.loc[frame["repackage_queue"].fillna(False).astype(bool)]
        for index, row in queued.iterrows():
            label = _post_label(row, index)
            recommendations.append(
                Recommendation(
                    recommendation_id=f"repackage:{label}",
                    category="repackage_queue",
                    title=f"Repackage Queue: {label}",
                    action=(
                        "Test a packaging variation for this post in a future audit cycle; "
                        "the observed scores do not establish why distribution was lower."
                    ),
                    supporting_metric="Distribution / Conversion / Efficiency detector metrics",
                    observed_value=(
                        f"Distribution={row.get('distribution_score')}; "
                        f"Conversion={row.get('conversion_score')}; "
                        f"Efficiency={row.get('efficiency_score')}"
                    ),
                    baseline="Under-distributed Winner policy: Distribution <= 40, Conversion >= 75, Efficiency >= 75",
                    sample_n=int(row.get("detector_eligible_cohort_size", 0) or 0),
                    comparison_kind="policy_threshold",
                    comparison_value="qualified",
                    uncertainty=(
                        "Account-relative observational detector; it does not infer a distribution cause "
                        "or predict a repackage outcome."
                    ),
                )
            )

    follow_baseline = content.account_baselines.get("median_follows_per_1k_impressions")
    best_follow = _best_above_baseline(
        content.aggregates,
        metric="median_follows_per_1k_impressions",
        baseline=follow_baseline,
    )
    if best_follow is not None and follow_baseline is not None:
        observed = float(best_follow.median_follows_per_1k_impressions)
        comparison_kind, comparison_value = _comparison(observed, float(follow_baseline))
        recommendations.append(
            Recommendation(
                recommendation_id=f"type-follow:{best_follow.content_type}",
                category="content_type_candidate",
                title=f"{best_follow.content_type}: account-asset test candidate",
                action=(
                    f"Test one additional {best_follow.content_type} post and compare future "
                    "account-relative follows-per-1k and Conversion results."
                ),
                supporting_metric="median follows per 1k impressions",
                observed_value=f"{observed:.4f}",
                baseline=f"account eligible median {float(follow_baseline):.4f}",
                sample_n=best_follow.eligible_post_count,
                comparison_kind=comparison_kind,
                comparison_value=comparison_value,
                uncertainty=(
                    "Eligible-sample descriptive comparison only; content type does not prove the "
                    "observed conversion difference caused follows."
                ),
            )
        )

    cheap_baseline = content.account_baselines.get("cheap_exposure_ratio")
    best_cheap = _best_above_baseline(
        content.aggregates,
        metric="cheap_exposure_ratio",
        baseline=cheap_baseline,
    )
    if best_cheap is not None and cheap_baseline is not None:
        observed = float(best_cheap.cheap_exposure_ratio)
        comparison_kind, comparison_value = _comparison(observed, float(cheap_baseline))
        recommendations.append(
            Recommendation(
                recommendation_id=f"type-cheap:{best_cheap.content_type}",
                category="traffic_without_asset_review",
                title=f"{best_cheap.content_type}: traffic-without-asset review candidate",
                action=(
                    "Review this content type before expanding it; keep future audits focused on "
                    "whether its observed account-asset outcomes change."
                ),
                supporting_metric="Cheap Exposure ratio among eligible posts",
                observed_value=f"{observed:.4f}",
                baseline=f"account eligible ratio {float(cheap_baseline):.4f}",
                sample_n=best_cheap.eligible_post_count,
                comparison_kind=comparison_kind,
                comparison_value=comparison_value,
                uncertainty=(
                    "The detector is account-relative and descriptive; it does not identify a "
                    "causal conversion mechanism."
                ),
            )
        )

    if not recommendations:
        recommendations.append(
            Recommendation(
                recommendation_id="insufficient-evidence",
                category="insufficient_evidence",
                title="Insufficient evidence",
                action=(
                    "Insufficient evidence: no content type met the eligible-sample and comparative "
                    "evidence rules in this audit."
                ),
                supporting_metric="none",
                observed_value="unavailable",
                baseline="unavailable",
                sample_n=0,
                comparison_kind="none",
                comparison_value="unavailable",
                uncertainty=(
                    "No generalized content advice is emitted when the retained account-relative "
                    "evidence is insufficient."
                ),
            )
        )
    return RecommendationSummary(recommendations=tuple(recommendations))

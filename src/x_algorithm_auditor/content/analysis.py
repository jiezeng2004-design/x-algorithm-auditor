"""Account-relative content-type aggregates with explicit sample sufficiency."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from x_algorithm_auditor.scoring.common import ScoringConfig


def _observed_median(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(values.median()) if not values.empty else None


def _flag_ratio(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame or frame.empty:
        return None
    values = frame[column].dropna()
    return float(values.astype(bool).mean()) if not values.empty else None


def _eligible_mask(frame: pd.DataFrame) -> pd.Series:
    if "score_eligible" not in frame:
        return pd.Series(False, index=frame.index, dtype="boolean")
    return frame["score_eligible"].fillna(False).astype(bool)


@dataclass(frozen=True)
class ContentTypeAggregate:
    """One type's descriptive metrics and its recommendation evidence guard."""

    content_type: str
    post_count: int
    eligible_post_count: int
    sample_sufficient: bool
    median_impressions: float | None
    median_alignment_score: float | None
    median_distribution_score: float | None
    median_conversion_score: float | None
    median_efficiency_score: float | None
    median_profile_visit_rate: float | None
    median_follows_per_1k_impressions: float | None
    cheap_exposure_ratio: float | None
    under_distributed_winner_ratio: float | None

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ContentAnalysisSummary:
    """All type aggregates and comparable account-level eligible baselines."""

    aggregates: tuple[ContentTypeAggregate, ...]
    account_baselines: dict[str, float | None]
    minimum_eligible_sample: int

    def by_type(self, content_type: str) -> ContentTypeAggregate | None:
        return next(
            (aggregate for aggregate in self.aggregates if aggregate.content_type == content_type),
            None,
        )


def _aggregate_type(
    content_type: str, frame: pd.DataFrame, config: ScoringConfig
) -> ContentTypeAggregate:
    eligible = frame.loc[_eligible_mask(frame)]
    eligible_count = len(eligible)
    return ContentTypeAggregate(
        content_type=content_type,
        post_count=len(frame),
        eligible_post_count=eligible_count,
        sample_sufficient=eligible_count >= config.content_minimum_eligible_sample,
        median_impressions=_observed_median(frame, "impressions"),
        median_alignment_score=_observed_median(eligible, "alignment_score"),
        median_distribution_score=_observed_median(eligible, "distribution_score"),
        median_conversion_score=_observed_median(eligible, "conversion_score"),
        median_efficiency_score=_observed_median(eligible, "efficiency_score"),
        median_profile_visit_rate=_observed_median(eligible, "profile_visit_rate"),
        median_follows_per_1k_impressions=_observed_median(eligible, "follows_per_1k_impressions"),
        cheap_exposure_ratio=_flag_ratio(eligible, "cheap_exposure"),
        under_distributed_winner_ratio=_flag_ratio(eligible, "under_distributed_winner"),
    )


def aggregate_content_types(frame: pd.DataFrame, config: ScoringConfig) -> ContentAnalysisSummary:
    """Aggregate classifier output; low samples remain descriptive, not decisive."""

    output = frame.copy()
    if "content_type" not in output:
        output["content_type"] = pd.Series("Other", index=output.index, dtype="string")
    output["content_type"] = output["content_type"].fillna("Other").astype("string")
    aggregates: Iterable[ContentTypeAggregate] = (
        _aggregate_type(str(content_type), group.copy(), config)
        for content_type, group in output.groupby("content_type", dropna=False, sort=True)
    )
    aggregate_tuple = tuple(
        sorted(aggregates, key=lambda item: (-item.eligible_post_count, item.content_type))
    )
    eligible = output.loc[_eligible_mask(output)]
    baselines = {
        "median_profile_visit_rate": _observed_median(eligible, "profile_visit_rate"),
        "median_follows_per_1k_impressions": _observed_median(
            eligible, "follows_per_1k_impressions"
        ),
        "cheap_exposure_ratio": _flag_ratio(eligible, "cheap_exposure"),
        "median_distribution_score": _observed_median(eligible, "distribution_score"),
        "median_conversion_score": _observed_median(eligible, "conversion_score"),
        "median_efficiency_score": _observed_median(eligible, "efficiency_score"),
    }
    return ContentAnalysisSummary(
        aggregates=aggregate_tuple,
        account_baselines=baselines,
        minimum_eligible_sample=config.content_minimum_eligible_sample,
    )

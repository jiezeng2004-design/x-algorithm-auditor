"""Rate calculation, empirical shrinkage, eligibility, and winsorization."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from x_algorithm_auditor.scoring.common import ScoringConfig

RATE_FIELD_NAMES: dict[str, str] = {
    "likes": "like_rate",
    "replies": "reply_rate",
    "reposts": "repost_rate",
    "quotes": "quote_rate",
    "shares": "share_rate",
    "shares_via_dm": "share_via_dm_rate",
    "shares_via_copy_link": "share_via_copy_link_rate",
    "bookmarks": "bookmark_rate",
    "profile_visits": "profile_visit_rate",
    "follows": "follow_rate",
    "link_clicks": "link_click_rate",
    "detail_expands": "detail_expand_rate",
    "media_views": "media_view_rate",
    "engagements": "engagement_rate",
    "not_interested": "not_interested_rate",
    "blocks": "block_rate",
    "mutes": "mute_rate",
    "reports": "report_rate",
}


@dataclass(frozen=True)
class NormalizationSummary:
    """Audit-level statistics required to reconstruct methodology-v1 inputs."""

    k: float
    eligibility_floor: float
    positive_impression_posts: int
    very_small_cohort: bool
    baselines: dict[str, float]
    winsorized_rates: list[str]


def _nullable_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Float64")


def normalize_metrics(
    data: pd.DataFrame, config: ScoringConfig
) -> tuple[pd.DataFrame, NormalizationSummary]:
    """Add raw/stabilized/winsorized rates without inventing unavailable values."""

    frame = data.copy()
    impressions = _nullable_float(frame["impressions"])
    frame["impressions"] = impressions
    positive = impressions[impressions > 0]
    positive_count = len(positive)
    very_small = positive_count < 5
    if very_small:
        k = config.very_small_cohort_k
    else:
        k = float(positive.median())
        k = min(config.k_max, max(config.k_min, k))
    if positive_count:
        floor = float(positive.quantile(0.25))
        floor = min(config.floor_max, max(config.floor_min, floor))
    else:
        floor = config.floor_min

    confidence = pd.Series("unavailable", index=frame.index, dtype="string")
    confidence.loc[impressions.gt(0) & impressions.lt(floor)] = "low"
    confidence.loc[impressions.ge(floor) & impressions.lt(config.high_multiple * floor)] = "medium"
    confidence.loc[impressions.ge(config.high_multiple * floor)] = "high"
    frame["sample_confidence"] = confidence
    frame["score_eligible"] = confidence.isin(["medium", "high"])
    frame["reliability"] = pd.Series(pd.NA, index=frame.index, dtype="Float64")
    valid_impressions = impressions.gt(0)
    frame.loc[valid_impressions, "reliability"] = (
        impressions.loc[valid_impressions] / (impressions.loc[valid_impressions] + k)
    ).astype("Float64")

    baselines: dict[str, float] = {}
    for field, rate_name in RATE_FIELD_NAMES.items():
        if field not in frame.columns:
            continue
        action = _nullable_float(frame[field])
        frame[field] = action
        valid = valid_impressions & action.notna()
        raw = pd.Series(pd.NA, index=frame.index, dtype="Float64")
        raw.loc[valid] = (action.loc[valid] / impressions.loc[valid]).astype("Float64")
        frame[rate_name] = raw
        if valid.any():
            denominator = float(impressions.loc[valid].sum())
            baseline = float(action.loc[valid].sum() / denominator) if denominator else 0.0
            baselines[rate_name] = baseline
            stabilized = pd.Series(pd.NA, index=frame.index, dtype="Float64")
            stabilized.loc[valid] = (
                (action.loc[valid] + k * baseline) / (impressions.loc[valid] + k)
            ).astype("Float64")
            frame[f"stabilized_{rate_name}"] = stabilized
        else:
            frame[f"stabilized_{rate_name}"] = pd.Series(pd.NA, index=frame.index, dtype="Float64")
        frame[f"score_{rate_name}"] = frame[f"stabilized_{rate_name}"].copy()

    frame["follows_per_1k_impressions"] = (
        frame.get("follow_rate", pd.Series(pd.NA, index=frame.index, dtype="Float64")) * 1000
    ).astype("Float64")

    winsorized: list[str] = []
    eligible = frame["score_eligible"]
    for _, rate_name in RATE_FIELD_NAMES.items():
        stabilized_name = f"stabilized_{rate_name}"
        score_name = f"score_{rate_name}"
        if stabilized_name not in frame:
            continue
        candidates = frame.loc[eligible, stabilized_name].dropna()
        if len(candidates) >= config.winsor_minimum_observations:
            lower = candidates.quantile(config.winsor_lower_quantile)
            upper = candidates.quantile(config.winsor_upper_quantile)
            frame.loc[eligible, score_name] = frame.loc[eligible, stabilized_name].clip(
                lower, upper
            )
            winsorized.append(rate_name)
    return frame, NormalizationSummary(
        k=k,
        eligibility_floor=floor,
        positive_impression_posts=positive_count,
        very_small_cohort=very_small,
        baselines=baselines,
        winsorized_rates=winsorized,
    )

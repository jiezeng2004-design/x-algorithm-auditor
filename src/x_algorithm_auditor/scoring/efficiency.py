"""Content Efficiency: valuable per-impression actions, separate from conversion."""

from __future__ import annotations

import pandas as pd

from x_algorithm_auditor.scoring.common import ScoringConfig, average_rank_percentile
from x_algorithm_auditor.scoring.conversion import ComponentSummary

EFFICIENCY_RATE_NAMES = {
    "replies": "reply_rate",
    "quotes": "quote_rate",
    "reposts": "repost_rate",
    "shares": "share_rate",
    "bookmarks": "bookmark_rate",
    "link_clicks": "link_click_rate",
    "detail_expands": "detail_expand_rate",
    "likes": "like_rate",
}


def score_efficiency(
    frame: pd.DataFrame, config: ScoringConfig
) -> tuple[pd.DataFrame, ComponentSummary]:
    """Score only policy-weighted efficiency components, with guarded fallback."""

    output = frame.copy()
    eligible = output["score_eligible"].astype(bool)
    eligible_count = int(eligible.sum())
    included: list[str] = []
    excluded: dict[str, str] = {}
    for name, rate_name in EFFICIENCY_RATE_NAMES.items():
        score_rate = f"score_{rate_name}"
        coverage = float(output.loc[eligible, score_rate].notna().mean()) if eligible_count else 0.0
        if score_rate in output and coverage >= config.dataset_observable_threshold:
            included.append(name)
            output[f"efficiency_component_{name}"] = average_rank_percentile(
                output.loc[eligible, score_rate]
            )
        else:
            excluded[name] = f"dataset-observable coverage {coverage:.3f} below threshold"
            output[f"efficiency_component_{name}"] = pd.Series(
                pd.NA, index=output.index, dtype="Int64"
            )

    fallback_used = False
    weights: dict[str, float] = {name: config.efficiency_weights[name] for name in included}
    if not included:
        fallback_rate = "score_engagement_rate"
        coverage = (
            float(output.loc[eligible, fallback_rate].notna().mean())
            if fallback_rate in output and eligible_count
            else 0.0
        )
        if fallback_rate in output and coverage >= config.dataset_observable_threshold:
            fallback_used = True
            included = ["engagements_fallback"]
            weights = {"engagements_fallback": 1.0}
            output["efficiency_component_engagements_fallback"] = average_rank_percentile(
                output.loc[eligible, fallback_rate]
            )
        else:
            excluded["engagements_fallback"] = (
                f"dataset-observable coverage {coverage:.3f} below threshold"
            )

    original_weight_total = sum(weights.values())
    output["efficiency_raw"] = pd.Series(pd.NA, index=output.index, dtype="Float64")
    output["efficiency_weight_coverage"] = pd.Series(pd.NA, index=output.index, dtype="Float64")
    output["efficiency_reason"] = pd.Series(
        "insufficient coverage", index=output.index, dtype="string"
    )
    for index, row in output.iterrows():
        available_weight = 0.0
        numerator = 0.0
        for name in included:
            component = row.get(f"efficiency_component_{name}")
            weight = weights[name]
            if not pd.isna(component):
                available_weight += weight
                numerator += weight * float(component)
        coverage = available_weight / original_weight_total if original_weight_total else 0.0
        if available_weight:
            output.loc[index, "efficiency_raw"] = numerator / available_weight
            output.loc[index, "efficiency_weight_coverage"] = coverage
        if not bool(row["score_eligible"]):
            output.loc[index, "efficiency_reason"] = "low or unavailable exposure confidence"
        elif not included:
            output.loc[index, "efficiency_reason"] = "no dataset-observable efficiency component"
        elif coverage < config.minimum_weight_coverage:
            output.loc[index, "efficiency_reason"] = "component coverage below 0.50"
        else:
            output.loc[index, "efficiency_reason"] = "scoreable"
    scoreable = eligible & (output["efficiency_reason"] == "scoreable")
    score = average_rank_percentile(output.loc[scoreable, "efficiency_raw"])
    output["efficiency_score"] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    output.loc[score.index, "efficiency_score"] = score
    return output, ComponentSummary(
        included=included, excluded=excluded, fallback_used=fallback_used
    )

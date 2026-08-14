"""Creator Conversion: only the profile-visit/follow funnel."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from x_algorithm_auditor.scoring.common import ScoringConfig, average_rank_percentile


@dataclass(frozen=True)
class ComponentSummary:
    included: list[str]
    excluded: dict[str, str]
    fallback_used: bool = False


def _component_score(frame: pd.DataFrame, rate_name: str) -> pd.Series:
    return average_rank_percentile(frame.loc[frame["score_eligible"], f"score_{rate_name}"])


def score_conversion(
    frame: pd.DataFrame, config: ScoringConfig
) -> tuple[pd.DataFrame, ComponentSummary]:
    """Score account-asset conversion without likes or other efficiency metrics."""

    output = frame.copy()
    eligible = output["score_eligible"].astype(bool)
    eligible_count = int(eligible.sum())
    candidates = {"follows": "follow_rate", "profile_visits": "profile_visit_rate"}
    included: list[str] = []
    excluded: dict[str, str] = {}
    for name, rate_name in candidates.items():
        score_rate = f"score_{rate_name}"
        coverage = float(output.loc[eligible, score_rate].notna().mean()) if eligible_count else 0.0
        if score_rate in output and coverage >= config.dataset_observable_threshold:
            included.append(name)
            output[f"conversion_component_{name}"] = _component_score(output, rate_name)
        else:
            excluded[name] = f"dataset-observable coverage {coverage:.3f} below threshold"
            output[f"conversion_component_{name}"] = pd.Series(
                pd.NA, index=output.index, dtype="Int64"
            )

    original_weight_total = sum(config.conversion_weights[name] for name in included)
    output["conversion_raw"] = pd.Series(pd.NA, index=output.index, dtype="Float64")
    output["conversion_weight_coverage"] = pd.Series(pd.NA, index=output.index, dtype="Float64")
    output["conversion_reason"] = pd.Series(
        "insufficient coverage", index=output.index, dtype="string"
    )
    for index, row in output.iterrows():
        available_weight = 0.0
        numerator = 0.0
        for name in included:
            component = row.get(f"conversion_component_{name}")
            weight = config.conversion_weights[name]
            if not pd.isna(component):
                available_weight += weight
                numerator += weight * float(component)
        coverage = available_weight / original_weight_total if original_weight_total else 0.0
        if available_weight:
            output.loc[index, "conversion_raw"] = numerator / available_weight
            output.loc[index, "conversion_weight_coverage"] = coverage
        if not bool(row["score_eligible"]):
            output.loc[index, "conversion_reason"] = "low or unavailable exposure confidence"
        elif not included:
            output.loc[index, "conversion_reason"] = "no dataset-observable funnel component"
        elif coverage < config.minimum_weight_coverage:
            output.loc[index, "conversion_reason"] = "component coverage below 0.50"
        else:
            output.loc[index, "conversion_reason"] = "scoreable"
    scoreable = eligible & (output["conversion_reason"] == "scoreable")
    score = average_rank_percentile(output.loc[scoreable, "conversion_raw"])
    output["conversion_score"] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    output.loc[score.index, "conversion_score"] = score
    return output, ComponentSummary(included=included, excluded=excluded)

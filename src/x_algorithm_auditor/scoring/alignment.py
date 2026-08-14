"""Observed Algorithm Alignment Proxy scoring using parsed public weights only."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from x_algorithm_auditor.algorithm.registry import SIGNAL_RELATIONS
from x_algorithm_auditor.algorithm.snapshot import AlgorithmSnapshot
from x_algorithm_auditor.analytics.normalize import RATE_FIELD_NAMES
from x_algorithm_auditor.scoring.common import ScoringConfig, average_rank_percentile


@dataclass(frozen=True)
class AlignmentSummary:
    """Dataset-level signal availability and mapping-policy evidence."""

    dataset_observable_parameters: list[str]
    excluded_parameters: dict[str, str]
    weighted_signal_denominator: float
    inactive_parameters: list[str]
    unverified_parameters: list[str]


def _param_values(snapshot: AlgorithmSnapshot) -> dict[str, float]:
    return {
        param.symbol: param.numeric_value
        for param in snapshot.parsed_params
        if param.numeric_value is not None
    }


def _source_column_observed(frame: pd.DataFrame, field: str) -> bool:
    return field in frame and frame[field].notna().any()


def _active_reference_by_parameter(snapshot: AlgorithmSnapshot) -> dict[str, bool | None]:
    """Return the conservative source-reference state for every extracted parameter."""

    references: dict[str, set[bool | None]] = {}
    for signal in snapshot.extracted_signals:
        references.setdefault(signal.parameter, set()).add(signal.active_scorer_reference)
    # A false reference wins over a true/unknown duplicate: using a parameter
    # known not to occur in the pinned scorer would overstate source coverage.
    return {
        parameter: False if False in states else True if states == {True} else None
        for parameter, states in references.items()
    }


def score_alignment(
    frame: pd.DataFrame, snapshot: AlgorithmSnapshot, config: ScoringConfig
) -> tuple[pd.DataFrame, AlignmentSummary]:
    """Calculate the account-relative weighted observed proxy.

    Public weight values come exclusively from ``snapshot``. The function never
    calls observed rates Phoenix probabilities and never makes missing fields
    numeric zero.
    """

    output = frame.copy()
    parameter_values = _param_values(snapshot)
    eligible = output["score_eligible"].astype(bool)
    eligible_count = int(eligible.sum())
    dataset_parameters: list[tuple[str, str, float, str]] = []
    excluded: dict[str, str] = {}
    inactive_parameters: list[str] = []
    unverified_parameters: list[str] = []
    active_references = _active_reference_by_parameter(snapshot)

    channels_observed = _source_column_observed(output, "shares_via_dm") or _source_column_observed(
        output, "shares_via_copy_link"
    )
    for relation in SIGNAL_RELATIONS:
        parameter = relation.parameter
        exclusion_label = parameter or f"{relation.canonical_field} (no direct parameter)"
        weight = parameter_values.get(parameter)
        if relation.relation == "unobservable":
            excluded[exclusion_label] = "unobservable relation; contextual only"
            continue
        if relation.relation in {"approximate", "outcome"}:
            excluded[exclusion_label] = f"{relation.relation} relation"
            continue
        if parameter is None:
            excluded[exclusion_label] = "no direct parameter"
            continue
        active_reference = active_references.get(parameter)
        if active_reference is False:
            excluded[parameter] = "not referenced by commit-pinned ranking source"
            inactive_parameters.append(parameter)
            continue
        if active_reference is None:
            unverified_parameters.append(parameter)
        if weight is None:
            excluded[parameter] = "parameter unavailable or nonnumeric"
            continue
        if weight == 0:
            excluded[parameter] = "public parameter is zero-weight"
            continue
        if relation.canonical_field not in RATE_FIELD_NAMES:
            excluded[parameter] = "canonical field has no rate adapter"
            continue
        if relation.relation == "conditional":
            # The generic adapter uses aggregate shares only when channel-specific
            # columns are absent, preventing any overlap/double-counting claim.
            if channels_observed:
                excluded[parameter] = "aggregate shares overlap with channel fields"
                continue
            relation_status = "conditional_aggregate_only"
        else:
            relation_status = relation.relation
        rate_name = RATE_FIELD_NAMES[relation.canonical_field]
        score_rate = f"score_{rate_name}"
        if score_rate not in output:
            excluded[parameter] = "rate unavailable in data"
            continue
        if eligible_count == 0:
            coverage = 0.0
        else:
            coverage = float(output.loc[eligible, score_rate].notna().mean())
        if coverage < config.dataset_observable_threshold:
            excluded[parameter] = f"dataset-observable coverage {coverage:.3f} below threshold"
            continue
        dataset_parameters.append(
            (parameter, relation.canonical_field, float(weight), relation_status)
        )

    total_abs_weight = sum(abs(weight) for _, _, weight, _ in dataset_parameters)
    output["alignment_raw"] = pd.Series(pd.NA, index=output.index, dtype="Float64")
    output["alignment_coverage_adjusted"] = pd.Series(pd.NA, index=output.index, dtype="Float64")
    output["alignment_weighted_coverage"] = pd.Series(pd.NA, index=output.index, dtype="Float64")
    output["alignment_used_signal_count"] = pd.Series(0, index=output.index, dtype="Int64")
    output["alignment_signal_details"] = pd.Series(pd.NA, index=output.index, dtype="string")
    output["alignment_reason"] = pd.Series(
        "insufficient coverage", index=output.index, dtype="string"
    )

    for index, row in output.iterrows():
        details: list[dict[str, object]] = []
        numerator = 0.0
        used_weight = 0.0
        used = 0
        for parameter, field, weight, relation_status in dataset_parameters:
            rate_name = RATE_FIELD_NAMES[field]
            raw_rate = row.get(rate_name)
            stabilized = row.get(f"stabilized_{rate_name}")
            score_rate = row.get(f"score_{rate_name}")
            observed = not pd.isna(score_rate)
            contribution = float(weight * score_rate) if observed else None
            details.append(
                {
                    "signal": field,
                    "parameter": parameter,
                    "relation": relation_status,
                    "observed_rate": None if pd.isna(raw_rate) else float(raw_rate),
                    "stabilized_rate": None if pd.isna(stabilized) else float(stabilized),
                    "scoring_rate": None if pd.isna(score_rate) else float(score_rate),
                    "scoring_rate_definition": (
                        "stabilized rate after conditional eligible-only winsorization"
                    ),
                    "public_weight": weight,
                    "contribution": contribution,
                    "state": "observed" if observed else "unavailable",
                    "active_scorer_reference": active_references.get(parameter),
                }
            )
            if observed:
                numerator += float(contribution)
                used_weight += abs(weight)
                used += 1
        coverage = used_weight / total_abs_weight if total_abs_weight else 0.0
        output.loc[index, "alignment_signal_details"] = json.dumps(
            details, ensure_ascii=False, sort_keys=True
        )
        output.loc[index, "alignment_used_signal_count"] = used
        if used:
            output.loc[index, "alignment_raw"] = numerator
            output.loc[index, "alignment_weighted_coverage"] = coverage
            if coverage:
                output.loc[index, "alignment_coverage_adjusted"] = numerator / used_weight
        if not bool(row["score_eligible"]):
            output.loc[index, "alignment_reason"] = "low or unavailable exposure confidence"
        elif not dataset_parameters:
            output.loc[index, "alignment_reason"] = "no dataset-observable mapped signal"
        elif used < config.minimum_alignment_signals:
            output.loc[index, "alignment_reason"] = "fewer than two observed mapped signals"
        elif coverage < config.minimum_weight_coverage:
            output.loc[index, "alignment_reason"] = "weighted coverage below 0.50"
        else:
            output.loc[index, "alignment_reason"] = (
                "scoreable; active scorer reference unverified"
                if unverified_parameters
                else "scoreable"
            )

    scoreable = eligible & output["alignment_reason"].str.startswith("scoreable", na=False)
    composite = output.loc[scoreable, "alignment_coverage_adjusted"]
    score = average_rank_percentile(composite)
    output["alignment_score"] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    output.loc[score.index, "alignment_score"] = score
    return output, AlignmentSummary(
        dataset_observable_parameters=[parameter for parameter, _, _, _ in dataset_parameters],
        excluded_parameters=excluded,
        weighted_signal_denominator=total_abs_weight,
        inactive_parameters=sorted(set(inactive_parameters)),
        unverified_parameters=sorted(set(unverified_parameters)),
    )

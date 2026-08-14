"""Conjunctive, account-relative Phase 2 overlay detectors."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from x_algorithm_auditor.scoring.common import ScoringConfig


@dataclass(frozen=True)
class DetectionSummary:
    """Run-level detector evidence retained for reports and recommendations."""

    eligible_cohort_size: int
    minimum_eligible_cohort: int
    cheap_exposure_count: int
    under_distributed_winner_count: int


def _observed(value: object) -> bool:
    return value is not None and value is not pd.NA and not pd.isna(value)


def _eligible(value: object) -> bool:
    return _observed(value) and bool(value)


def _metric_value(value: object) -> float | None:
    return float(value) if _observed(value) else None


def _metrics_payload(
    row: pd.Series, *, cohort_size: int, config: ScoringConfig, detector: str
) -> str:
    if detector == "cheap_exposure":
        thresholds = {
            "distribution_score_gte": config.cheap_exposure_minimum_distribution_score,
            "conversion_score_lte": config.cheap_exposure_maximum_conversion_score,
            "efficiency_score_lte": config.cheap_exposure_maximum_efficiency_score,
        }
    else:
        thresholds = {
            "distribution_score_lte": config.under_distributed_maximum_distribution_score,
            "conversion_score_gte": config.under_distributed_minimum_conversion_score,
            "efficiency_score_gte": config.under_distributed_minimum_efficiency_score,
        }
    return json.dumps(
        {
            "policy_version": config.phase2_policy_version,
            "eligible_detector_cohort": cohort_size,
            "minimum_eligible_detector_cohort": config.detector_minimum_eligible_cohort,
            "distribution_score": _metric_value(row.get("distribution_score")),
            "conversion_score": _metric_value(row.get("conversion_score")),
            "efficiency_score": _metric_value(row.get("efficiency_score")),
            "thresholds": thresholds,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _base_reason(row: pd.Series, cohort_size: int, config: ScoringConfig) -> str | None:
    if cohort_size < config.detector_minimum_eligible_cohort:
        return (
            "detector cohort below "
            f"{config.detector_minimum_eligible_cohort} observed eligible posts"
        )
    if not _eligible(row.get("score_eligible")):
        return "low or unavailable exposure confidence"
    required = ("distribution_score", "conversion_score", "efficiency_score")
    if any(not _observed(row.get(column)) for column in required):
        return "required Distribution, Conversion, or Efficiency score unavailable"
    return None


def apply_detectors(
    frame: pd.DataFrame, config: ScoringConfig
) -> tuple[pd.DataFrame, DetectionSummary]:
    """Apply detector conjunctions and retain row-level non-trigger reasons."""

    output = frame.copy()
    observed_detector_rows = output.apply(
        lambda row: (
            _eligible(row.get("score_eligible"))
            and all(
                _observed(row.get(column))
                for column in ("distribution_score", "conversion_score", "efficiency_score")
            )
        ),
        axis=1,
    )
    cohort_size = int(observed_detector_rows.sum())
    cheap_flags = pd.Series(False, index=output.index, dtype="boolean")
    under_flags = pd.Series(False, index=output.index, dtype="boolean")
    cheap_reasons = pd.Series("not evaluated", index=output.index, dtype="string")
    under_reasons = pd.Series("not evaluated", index=output.index, dtype="string")
    cheap_metrics = pd.Series(pd.NA, index=output.index, dtype="string")
    under_metrics = pd.Series(pd.NA, index=output.index, dtype="string")

    for index, row in output.iterrows():
        base_reason = _base_reason(row, cohort_size, config)
        cheap_metrics.loc[index] = _metrics_payload(
            row, cohort_size=cohort_size, config=config, detector="cheap_exposure"
        )
        under_metrics.loc[index] = _metrics_payload(
            row, cohort_size=cohort_size, config=config, detector="under_distributed_winner"
        )
        if base_reason is not None:
            cheap_reasons.loc[index] = base_reason
            under_reasons.loc[index] = base_reason
            continue

        distribution = float(row["distribution_score"])
        conversion = float(row["conversion_score"])
        efficiency = float(row["efficiency_score"])

        cheap_failures: list[str] = []
        if distribution < config.cheap_exposure_minimum_distribution_score:
            cheap_failures.append(
                f"distribution below {config.cheap_exposure_minimum_distribution_score}"
            )
        if conversion > config.cheap_exposure_maximum_conversion_score:
            cheap_failures.append(
                f"conversion above {config.cheap_exposure_maximum_conversion_score}"
            )
        if efficiency > config.cheap_exposure_maximum_efficiency_score:
            cheap_failures.append(
                f"efficiency above {config.cheap_exposure_maximum_efficiency_score}"
            )
        if not cheap_failures:
            cheap_flags.loc[index] = True
            cheap_reasons.loc[index] = "qualified conjunctive cheap exposure rule"
        else:
            cheap_reasons.loc[index] = "; ".join(cheap_failures)

        under_failures: list[str] = []
        if distribution > config.under_distributed_maximum_distribution_score:
            under_failures.append(
                f"distribution above {config.under_distributed_maximum_distribution_score}"
            )
        if conversion < config.under_distributed_minimum_conversion_score:
            under_failures.append(
                f"conversion below {config.under_distributed_minimum_conversion_score}"
            )
        if efficiency < config.under_distributed_minimum_efficiency_score:
            under_failures.append(
                f"efficiency below {config.under_distributed_minimum_efficiency_score}"
            )
        if not under_failures:
            under_flags.loc[index] = True
            under_reasons.loc[index] = "qualified conjunctive under-distributed winner rule"
        else:
            under_reasons.loc[index] = "; ".join(under_failures)

    output["cheap_exposure"] = cheap_flags
    output["cheap_exposure_reason"] = cheap_reasons
    output["cheap_exposure_trigger_metrics"] = cheap_metrics
    output["under_distributed_winner"] = under_flags
    output["under_distributed_winner_reason"] = under_reasons
    output["under_distributed_winner_trigger_metrics"] = under_metrics
    output["repackage_queue"] = under_flags.copy()
    output["repackage_queue_reason"] = pd.Series(
        [
            "qualified under-distributed winner" if bool(flag) else "not qualified"
            for flag in under_flags
        ],
        index=output.index,
        dtype="string",
    )
    output["detector_eligible_cohort_size"] = pd.Series(
        cohort_size, index=output.index, dtype="Int64"
    )
    return output, DetectionSummary(
        eligible_cohort_size=cohort_size,
        minimum_eligible_cohort=config.detector_minimum_eligible_cohort,
        cheap_exposure_count=int(cheap_flags.sum()),
        under_distributed_winner_count=int(under_flags.sum()),
    )

"""Shared scoring primitives for methodology-v1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from x_algorithm_auditor._config_resources import default_config_label, read_default_config


@dataclass(frozen=True)
class ScoringConfig:
    """Versioned auditor policy, distinct from public X parameter values."""

    schema_version: str
    dataset_observable_threshold: float
    minimum_alignment_signals: int
    minimum_weight_coverage: float
    k_min: float
    k_max: float
    very_small_cohort_k: float
    floor_min: float
    floor_max: float
    high_multiple: float
    winsor_minimum_observations: int
    winsor_lower_quantile: float
    winsor_upper_quantile: float
    conversion_weights: dict[str, float]
    efficiency_weights: dict[str, float]
    phase2_policy_version: str
    quadrant_median_cutoff: int
    core_winner_cutoff: int
    detector_minimum_eligible_cohort: int
    cheap_exposure_minimum_distribution_score: int
    cheap_exposure_maximum_conversion_score: int
    cheap_exposure_maximum_efficiency_score: int
    under_distributed_maximum_distribution_score: int
    under_distributed_minimum_conversion_score: int
    under_distributed_minimum_efficiency_score: int
    content_minimum_eligible_sample: int


def load_scoring_config(path: Path | None = None) -> ScoringConfig:
    """Load validated scoring policy YAML; no X source parameter lives here."""

    try:
        if path is None:
            content, selected = read_default_config("scoring.yaml")
        else:
            selected = str(path)
            content = path.read_text(encoding="utf-8")
        payload: dict[str, Any] = yaml.safe_load(content)
    except (OSError, yaml.YAMLError, ValueError) as error:
        label = str(path) if path is not None else default_config_label("scoring.yaml")
        raise ValueError(f"unable to read scoring config {label}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("scoring config must be a YAML mapping")
    try:
        shrinkage = payload["shrinkage"]
        eligibility = payload["eligibility"]
        winsor = payload["winsorization"]
        phase2 = payload["phase2_policy"]
        quadrants = phase2["quadrants"]
        detectors = phase2["detectors"]
        cheap = detectors["cheap_exposure"]
        under_distributed = detectors["under_distributed_winner"]
        content_analysis = phase2["content_analysis"]
        config = ScoringConfig(
            schema_version=str(payload["schema_version"]),
            dataset_observable_threshold=float(payload["dataset_observable_threshold"]),
            minimum_alignment_signals=int(payload["minimum_alignment_signals"]),
            minimum_weight_coverage=float(payload["minimum_weight_coverage"]),
            k_min=float(shrinkage["k_min"]),
            k_max=float(shrinkage["k_max"]),
            very_small_cohort_k=float(shrinkage["very_small_cohort_k"]),
            floor_min=float(eligibility["floor_min"]),
            floor_max=float(eligibility["floor_max"]),
            high_multiple=float(eligibility["high_multiple"]),
            winsor_minimum_observations=int(winsor["minimum_observations"]),
            winsor_lower_quantile=float(winsor["lower_quantile"]),
            winsor_upper_quantile=float(winsor["upper_quantile"]),
            conversion_weights={
                key: float(value) for key, value in payload["conversion_weights"].items()
            },
            efficiency_weights={
                key: float(value) for key, value in payload["efficiency_weights"].items()
            },
            phase2_policy_version=str(phase2["version"]),
            quadrant_median_cutoff=int(quadrants["median_cutoff"]),
            core_winner_cutoff=int(quadrants["core_winner_cutoff"]),
            detector_minimum_eligible_cohort=int(detectors["minimum_eligible_cohort"]),
            cheap_exposure_minimum_distribution_score=int(cheap["minimum_distribution_score"]),
            cheap_exposure_maximum_conversion_score=int(cheap["maximum_conversion_score"]),
            cheap_exposure_maximum_efficiency_score=int(cheap["maximum_efficiency_score"]),
            under_distributed_maximum_distribution_score=int(
                under_distributed["maximum_distribution_score"]
            ),
            under_distributed_minimum_conversion_score=int(
                under_distributed["minimum_conversion_score"]
            ),
            under_distributed_minimum_efficiency_score=int(
                under_distributed["minimum_efficiency_score"]
            ),
            content_minimum_eligible_sample=int(content_analysis["minimum_eligible_sample"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid scoring config {selected}: {error}") from error
    if config.schema_version != "methodology-v1":
        raise ValueError(f"unsupported scoring schema version: {config.schema_version}")
    if not 0 < config.dataset_observable_threshold <= 1:
        raise ValueError("dataset_observable_threshold must be in (0, 1]")
    if not 0 <= config.quadrant_median_cutoff <= 100:
        raise ValueError("quadrant_median_cutoff must be in [0, 100]")
    if not 0 <= config.core_winner_cutoff <= 100:
        raise ValueError("core_winner_cutoff must be in [0, 100]")
    if config.detector_minimum_eligible_cohort < 1:
        raise ValueError("detector_minimum_eligible_cohort must be positive")
    if config.content_minimum_eligible_sample < 1:
        raise ValueError("content_minimum_eligible_sample must be positive")
    return config


def average_rank_percentile(values: pd.Series) -> pd.Series:
    """Return nullable 0–100 average-rank percentiles, including tie behavior."""

    numeric = pd.to_numeric(values, errors="coerce").astype("Float64")
    result = pd.Series(pd.NA, index=numeric.index, dtype="Int64")
    observed = numeric.dropna()
    count = len(observed)
    if count == 0:
        return result
    if count == 1:
        result.loc[observed.index] = 50
        return result
    ranks = observed.rank(method="average")
    score = (100 * (ranks - 1) / (count - 1)).round().astype("Int64")
    result.loc[score.index] = score
    return result


def nullable_score(series: pd.Series) -> pd.Series:
    """Coerce a score series to bounded nullable integer output."""

    numeric = pd.to_numeric(series, errors="coerce").clip(0, 100)
    return numeric.round().astype("Int64")

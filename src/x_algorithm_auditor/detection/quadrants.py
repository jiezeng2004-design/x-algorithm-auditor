"""Exhaustive Alignment × Conversion quadrants and the stricter Core Winner badge."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from x_algorithm_auditor.scoring.common import ScoringConfig

QUADRANT_A = "A — Core Winner zone"
QUADRANT_B = "B — Traffic Without Asset"
QUADRANT_C = "C — Conversion-led candidate"
QUADRANT_D = "D — Low Priority"
INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class QuadrantSummary:
    """Counts for descriptive quadrants and the stronger qualifying badge."""

    counts: dict[str, int]
    core_winner_count: int


def _observed(value: object) -> bool:
    return value is not None and value is not pd.NA and not pd.isna(value)


def _eligible(value: object) -> bool:
    return _observed(value) and bool(value)


def classify_quadrants(
    frame: pd.DataFrame, config: ScoringConfig
) -> tuple[pd.DataFrame, QuadrantSummary]:
    """Classify score-eligible posts without treating missing scores as low scores."""

    output = frame.copy()
    quadrants = pd.Series(INSUFFICIENT_DATA, index=output.index, dtype="string")
    core_winner = pd.Series(False, index=output.index, dtype="boolean")
    reasons = pd.Series("insufficient data", index=output.index, dtype="string")

    for index, row in output.iterrows():
        alignment = row.get("alignment_score")
        conversion = row.get("conversion_score")
        coverage = row.get("alignment_weighted_coverage")
        if not _eligible(row.get("score_eligible")):
            reasons.loc[index] = "low or unavailable exposure confidence"
            continue
        if not _observed(alignment) or not _observed(conversion):
            reasons.loc[index] = "alignment or conversion score unavailable"
            continue

        alignment_value = float(alignment)
        conversion_value = float(conversion)
        if alignment_value >= config.quadrant_median_cutoff:
            quadrants.loc[index] = (
                QUADRANT_A if conversion_value >= config.quadrant_median_cutoff else QUADRANT_B
            )
        else:
            quadrants.loc[index] = (
                QUADRANT_C if conversion_value >= config.quadrant_median_cutoff else QUADRANT_D
            )

        if not _observed(coverage) or float(coverage) < config.minimum_weight_coverage:
            reasons.loc[index] = "alignment coverage below required threshold"
        elif alignment_value < config.core_winner_cutoff:
            reasons.loc[index] = f"alignment below {config.core_winner_cutoff}"
        elif conversion_value < config.core_winner_cutoff:
            reasons.loc[index] = f"conversion below {config.core_winner_cutoff}"
        else:
            core_winner.loc[index] = True
            reasons.loc[index] = "qualified core winner badge"

    output["quadrant"] = quadrants
    output["core_winner"] = core_winner
    output["core_winner_reason"] = reasons
    counts = Counter(str(value) for value in quadrants)
    return output, QuadrantSummary(
        counts=dict(sorted(counts.items())), core_winner_count=int(core_winner.sum())
    )

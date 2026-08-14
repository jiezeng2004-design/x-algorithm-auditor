"""Distribution is observed impression percentile only."""

from __future__ import annotations

import pandas as pd

from x_algorithm_auditor.scoring.common import average_rank_percentile


def score_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    """Add a relative impression score without engagement/conversion inputs."""

    output = frame.copy()
    output["distribution_score"] = average_rank_percentile(output["impressions"])
    return output

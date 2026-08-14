"""One deterministic Phase 1/2 scoring orchestration seam."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from x_algorithm_auditor.algorithm.snapshot import AlgorithmSnapshot
from x_algorithm_auditor.analytics.normalize import NormalizationSummary, normalize_metrics
from x_algorithm_auditor.content.analysis import ContentAnalysisSummary, aggregate_content_types
from x_algorithm_auditor.content.classifier import (
    DeterministicContentClassifier,
    classify_posts,
    extend_taxonomy_keywords,
    load_content_taxonomy,
)
from x_algorithm_auditor.detection.detectors import DetectionSummary, apply_detectors
from x_algorithm_auditor.detection.quadrants import QuadrantSummary, classify_quadrants
from x_algorithm_auditor.presets.loader import AuditPreset
from x_algorithm_auditor.recommendations.engine import (
    RecommendationSummary,
    generate_recommendations,
)
from x_algorithm_auditor.scoring.alignment import AlignmentSummary, score_alignment
from x_algorithm_auditor.scoring.common import ScoringConfig
from x_algorithm_auditor.scoring.conversion import ComponentSummary, score_conversion
from x_algorithm_auditor.scoring.distribution import score_distribution
from x_algorithm_auditor.scoring.efficiency import score_efficiency


@dataclass(frozen=True)
class ScoringSummary:
    normalization: NormalizationSummary
    alignment: AlignmentSummary
    conversion: ComponentSummary
    efficiency: ComponentSummary
    quadrants: QuadrantSummary
    detection: DetectionSummary
    content: ContentAnalysisSummary
    recommendations: RecommendationSummary


def score_posts(
    data: pd.DataFrame,
    snapshot: AlgorithmSnapshot,
    config: ScoringConfig,
    preset: AuditPreset | None = None,
) -> tuple[pd.DataFrame, ScoringSummary]:
    """Produce generic scores; a preset can extend classifier keywords only."""

    normalized, normalization = normalize_metrics(data, config)
    aligned, alignment = score_alignment(normalized, snapshot, config)
    distributed = score_distribution(aligned)
    converted, conversion = score_conversion(distributed, config)
    efficient, efficiency = score_efficiency(converted, config)
    quadranted, quadrants = classify_quadrants(efficient, config)
    detected, detection = apply_detectors(quadranted, config)
    taxonomy = load_content_taxonomy()
    if preset is not None:
        taxonomy = extend_taxonomy_keywords(taxonomy, preset.content_taxonomy_keywords)
    classified = classify_posts(detected, DeterministicContentClassifier(taxonomy))
    content = aggregate_content_types(classified, config)
    recommendations = generate_recommendations(classified, content)
    return classified, ScoringSummary(
        normalization=normalization,
        alignment=alignment,
        conversion=conversion,
        efficiency=efficiency,
        quadrants=quadrants,
        detection=detection,
        content=content,
        recommendations=recommendations,
    )

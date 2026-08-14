"""Human-readable Markdown audit report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from x_algorithm_auditor.algorithm.registry import SIGNAL_RELATIONS
from x_algorithm_auditor.algorithm.snapshot import AlgorithmSnapshot
from x_algorithm_auditor.analytics.deduplicate import DeduplicationSummary
from x_algorithm_auditor.analytics.loader import CROSS_EXPORT_WARNING, DataQualitySummary
from x_algorithm_auditor.presets.loader import AuditPreset
from x_algorithm_auditor.scoring.pipeline import ScoringSummary

PROXY_DISCLAIMER = (
    "Algorithm Alignment is an account-relative observed proxy based on public weights and "
    "historical Analytics rates. It is not X's official ranking score and does not contain "
    "Phoenix viewer-post probabilities."
)


def _value(value: object, digits: int = 4) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _bullet_map(values: dict[str, Any]) -> list[str]:
    if not values:
        return ["- none"]
    return [f"- `{key}`: {_value(value)}" for key, value in values.items()]


def _table(rows: list[list[str]], headers: list[str]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _sample_posts(data: pd.DataFrame) -> list[list[str]]:
    columns = [
        "post_id",
        "impressions",
        "alignment_score",
        "distribution_score",
        "conversion_score",
        "efficiency_score",
    ]
    sample = data.sort_values("distribution_score", ascending=False, na_position="last").head(10)
    return [[_value(row.get(column)) for column in columns] for _, row in sample.iterrows()]


def _quality_state_rows(quality: DataQualitySummary) -> list[list[str]]:
    labels = {
        "absent_columns": "Absent source columns",
        "missing_cells": "Missing source cells",
        "malformed_values": "Malformed values",
        "negative_values": "Negative count values",
        "rate_unavailable_zero_impressions": "Rates unavailable: zero impressions",
        "rate_unavailable_missing_or_invalid_impressions": (
            "Rates unavailable: missing/invalid impressions"
        ),
    }
    return [[labels[key], str(value)] for key, value in quality.category_counts().items()]


def _rows_for_posts(data: pd.DataFrame, mask: pd.Series) -> list[list[str]]:
    columns = [
        "post_id",
        "impressions",
        "alignment_score",
        "distribution_score",
        "conversion_score",
        "efficiency_score",
    ]
    selected = data.loc[mask].sort_values("distribution_score", ascending=False, na_position="last")
    return [[_value(row.get(column)) for column in columns] for _, row in selected.iterrows()]


def _phase_two_post_table(data: pd.DataFrame, mask: pd.Series, empty_message: str) -> list[str]:
    rows = _rows_for_posts(data, mask)
    if not rows:
        return [empty_message]
    return _table(
        rows,
        ["post_id", "impressions", "Alignment", "Distribution", "Conversion", "Efficiency"],
    )


def _detector_post_table(
    data: pd.DataFrame, mask: pd.Series, reason_column: str, empty_message: str
) -> list[str]:
    selected = data.loc[mask].sort_values("distribution_score", ascending=False, na_position="last")
    if selected.empty:
        return [empty_message]
    rows = [
        [
            _value(row.get("post_id")),
            _value(row.get("distribution_score")),
            _value(row.get("conversion_score")),
            _value(row.get("efficiency_score")),
            _value(row.get(reason_column)),
        ]
        for _, row in selected.iterrows()
    ]
    return _table(rows, ["post_id", "Distribution", "Conversion", "Efficiency", "Trigger reason"])


def _content_type_rows(scoring: ScoringSummary) -> list[list[str]]:
    return [
        [
            aggregate.content_type,
            str(aggregate.post_count),
            str(aggregate.eligible_post_count),
            "sufficient" if aggregate.sample_sufficient else "insufficient sample",
            _value(aggregate.median_impressions),
            _value(aggregate.median_alignment_score),
            _value(aggregate.median_distribution_score),
            _value(aggregate.median_conversion_score),
            _value(aggregate.median_efficiency_score),
            _value(aggregate.median_profile_visit_rate),
            _value(aggregate.median_follows_per_1k_impressions),
            _value(aggregate.cheap_exposure_ratio),
        ]
        for aggregate in scoring.content.aggregates
    ]


def _recommendation_rows(scoring: ScoringSummary) -> list[list[str]]:
    return [
        [
            recommendation.title,
            recommendation.supporting_metric,
            recommendation.observed_value,
            recommendation.baseline,
            str(recommendation.sample_n),
            f"{recommendation.comparison_kind}: {recommendation.comparison_value}",
            recommendation.uncertainty,
        ]
        for recommendation in scoring.recommendations.recommendations
    ]


def _preset_context_lines(preset: AuditPreset | None) -> list[str]:
    """Render optional local context without treating it as scoring evidence."""

    if preset is None:
        return ["- Optional preset: none (generic core only)."]
    lines = [
        f"- Optional preset: active (`{preset.schema_version}`).",
        "- Scope: classifier keyword extensions and human-readable comparison context only; "
        "it cannot override snapshot provenance, Missing != Zero, scoring policy, eligibility, "
        "detectors, or recommendations.",
    ]
    if preset.creator_goal:
        lines.append(f"- Creator goal: {preset.creator_goal}")
    if preset.niche:
        lines.append(f"- Niche: {preset.niche}")
    if preset.preferred_metrics:
        lines.append(
            "- Preferred metrics (display context): " + ", ".join(preset.preferred_metrics)
        )
    if preset.historical_baseline:
        baseline = ", ".join(
            f"{metric}={value:g}" for metric, value in sorted(preset.historical_baseline.items())
        )
        lines.append(
            "- Historical baseline (comparison prior only; current Analytics remains the scored "
            f"evidence): {baseline}"
        )
    return lines


def render_markdown(
    *,
    data: pd.DataFrame,
    snapshot: AlgorithmSnapshot,
    quality: DataQualitySummary,
    deduplication: DeduplicationSummary,
    scoring: ScoringSummary,
    preset: AuditPreset | None = None,
) -> str:
    """Render all thirteen required sections with guarded audit evidence."""

    lines: list[str] = ["# X Algorithm Auditor Audit", "", "> " + PROXY_DISCLAIMER, ""]
    lines.extend(["## 1. Executive Summary", ""])
    lines.append(f"- Algorithm source: **{snapshot.source_mode}**")
    lines.append(f"- Snapshot commit: `{snapshot.commit_sha}`")
    lines.append(f"- Deduplicated posts analyzed: **{len(data)}**")
    if snapshot.source_mode == "cached":
        lines.append(
            "- Warning: this run used a validated cached public-source snapshot, not a live fetch."
        )
    if scoring.normalization.very_small_cohort:
        lines.append(
            "- Warning: very small positive-impression cohort; rate-derived results have limited resolution."
        )
    lines.append(
        "- Detector cohort: "
        f"{scoring.detection.eligible_cohort_size} observed eligible posts "
        f"(minimum {scoring.detection.minimum_eligible_cohort})"
    )
    lines.extend(_preset_context_lines(preset))
    lines.extend(["", "## 2. Data Coverage", ""])
    lines.extend(
        [
            f"- Input rows: {deduplication.input_rows}",
            f"- Output posts: {deduplication.output_posts}",
            f"- Deduplicated rows: {deduplication.deduplicated_rows}",
            f"- Duplicate conflicts retained as diagnostics: {deduplication.conflict_count}",
            (
                "- Rows with insufficient stable identity preserved without weak-identity merging: "
                f"{deduplication.insufficient_identity_rows}"
            ),
            f"- Shrinkage k: {_value(scoring.normalization.k)}",
            f"- Eligibility floor: {_value(scoring.normalization.eligibility_floor)} impressions",
            "- Low-confidence posts retain diagnostics but have unavailable Alignment, Conversion, and Efficiency final scores.",
            f"- Warning: {CROSS_EXPORT_WARNING}",
        ]
    )
    lines.extend(["", "### Validation diagnostics", ""])
    lines.extend(_table(_quality_state_rows(quality), ["Data quality state", "Count"]))
    lines.append("")
    lines.extend(_bullet_map(dict(sorted(quality.events.items()))))
    if quality.date_range_values:
        lines.append("- Date range observations: " + "; ".join(quality.date_range_values))
    lines.extend(["", "### Score sample", ""])
    lines.extend(
        _table(
            _sample_posts(data),
            ["post_id", "impressions", "Alignment", "Distribution", "Conversion", "Efficiency"],
        )
    )

    lines.extend(["", "## 3. Algorithm Snapshot", ""])
    lines.extend(
        [
            f"- Repository: `{snapshot.repository}`",
            f"- Branch resolved: `{snapshot.branch}`",
            f"- Commit: `{snapshot.commit_sha}`",
            f"- Source mode: **{snapshot.source_mode}**",
            f"- Fetched at (UTC): `{snapshot.fetched_at_utc}`",
            f"- Parameter source: `{snapshot.parameter_source_path}`",
            f"- Parameter sync date: `{_value(snapshot.parameter_sync_date)}`",
            f"- Parameter source SHA-256: `{snapshot.source_sha256}`",
            f"- ValueModelMode: `{_value(snapshot.value_model_mode)}`",
        ]
    )
    if snapshot.active_scorer_coverage is None:
        verification_reason = (
            "ranking scorer source was unavailable"
            if snapshot.ranking_source_content is None
            else "no parsed registered parameter could be source-verified"
        )
        lines.append(
            "- Active scorer verification: **unverified** ("
            + verification_reason
            + "; mappings are not active-verified)."
        )
    else:
        lines.append(f"- Active scorer coverage: `{_value(snapshot.active_scorer_coverage)}`")
    if snapshot.change_from_previous.previous_commit:
        change = snapshot.change_from_previous
        lines.append(
            "- Change from previous: "
            f"commit_changed={change.commit_changed}, source_changed={change.source_changed}, "
            f"added={len(change.added)}, removed={len(change.removed)}, changed={len(change.changed)}"
        )
    if snapshot.warnings:
        lines.extend(["", "### Snapshot warnings", ""])
        lines.extend(f"- {warning}" for warning in snapshot.warnings)

    lines.extend(["", "## 4. Observable Signals", ""])
    observed_rows = [
        [
            signal.canonical_field,
            signal.parameter,
            signal.relation,
            _value(signal.numeric_value),
            _value(signal.active_scorer_reference),
        ]
        for signal in snapshot.extracted_signals
        if signal.parameter in scoring.alignment.dataset_observable_parameters
    ]
    if observed_rows:
        lines.extend(
            _table(
                observed_rows,
                ["Analytics field", "Public param", "Relation", "Weight", "Active source"],
            )
        )
    else:
        lines.append(
            "No mapped signal met the dataset-observable gate; Alignment is unavailable where evidence is insufficient."
        )
    if scoring.alignment.unverified_parameters:
        lines.append(
            "- Active scorer source-reference verification is **unverified** for: `"
            + "`, `".join(scoring.alignment.unverified_parameters)
            + "`. These mappings are not claimed as active-verified."
        )

    lines.extend(["", "## 5. Unobservable Signals", ""])
    excluded_rows = [
        [
            relation.canonical_field,
            relation.parameter or "none — contextual only",
            relation.description,
        ]
        for relation in SIGNAL_RELATIONS
        if relation.relation in {"approximate", "outcome", "unobservable"}
    ]
    lines.extend(
        _table(
            excluded_rows,
            ["Analytics concept", "Public parameter", "Why excluded from Alignment"],
        )
    )
    if scoring.alignment.excluded_parameters:
        lines.append("")
        lines.append("Additional run-specific exclusions:")
        lines.extend(_bullet_map(scoring.alignment.excluded_parameters))

    lines.extend(["", "## 6. Core Winners", ""])
    lines.append(
        "Core Winner is a stricter badge than Quadrant A: Alignment and Conversion must both be "
        "at least 75 with score-eligible exposure and adequate Alignment coverage."
    )
    lines.append("")
    core_mask = data["core_winner"].fillna(False).astype(bool)
    lines.extend(
        _phase_two_post_table(data, core_mask, "No post qualified for the Core Winner badge.")
    )

    lines.extend(["", "## 7. Cheap Exposure", ""])
    lines.append(
        "Flag requires account-relative Distribution >= 75 plus Conversion <= 25 and Efficiency <= 25; "
        "it is not an impressions-only label."
    )
    lines.append("")
    cheap_mask = data["cheap_exposure"].fillna(False).astype(bool)
    lines.extend(
        _detector_post_table(
            data,
            cheap_mask,
            "cheap_exposure_reason",
            "No post met the conjunctive Cheap Exposure rule.",
        )
    )

    lines.extend(["", "## 8. Under-distributed Winners", ""])
    lines.append(
        "Flag requires Distribution <= 40 plus Conversion >= 75 and Efficiency >= 75; it is a "
        "descriptive repackage-review priority, not a claim about why distribution was lower."
    )
    lines.append("")
    under_mask = data["under_distributed_winner"].fillna(False).astype(bool)
    lines.extend(
        _detector_post_table(
            data,
            under_mask,
            "under_distributed_winner_reason",
            "No post met the conjunctive Under-distributed Winner rule.",
        )
    )
    lines.extend(["", "### Repackage Queue", ""])
    repackage_mask = data["repackage_queue"].fillna(False).astype(bool)
    lines.extend(
        _phase_two_post_table(
            data,
            repackage_mask,
            "No post entered the Repackage Queue; only qualified Under-distributed Winners can enter.",
        )
    )

    lines.extend(["", "## 9. Traffic Without Asset", ""])
    lines.append(
        "This is the descriptive Quadrant B zone (Alignment >= 50, Conversion < 50), distinct from "
        "the stricter Cheap Exposure detector."
    )
    lines.append("")
    traffic_mask = data["quadrant"].eq("B — Traffic Without Asset")
    lines.extend(
        _phase_two_post_table(data, traffic_mask, "No score-eligible post fell in Quadrant B.")
    )

    lines.extend(["", "## 10. Content Type Analysis", ""])
    lines.append(
        "**Experimental.** Current content classification is heuristic and should be treated "
        "as descriptive rather than authoritative."
    )
    lines.append("")
    classifier_versions = sorted(
        str(value)
        for value in data.get("content_classifier_version", pd.Series(dtype="string"))
        .dropna()
        .unique()
    )
    lines.append(
        "Classifier: deterministic local heuristic"
        + (f" (`{', '.join(classifier_versions)}`)" if classifier_versions else "")
        + ". Metadata Reply/Quote/Thread labels take precedence over text rules."
    )
    lines.append(
        "Types with fewer than "
        f"{scoring.content.minimum_eligible_sample} eligible posts are explicitly insufficient samples "
        "and cannot drive type recommendations."
    )
    lines.append("")
    content_rows = _content_type_rows(scoring)
    if content_rows:
        lines.extend(
            _table(
                content_rows,
                [
                    "Content type",
                    "Posts",
                    "Eligible",
                    "Evidence",
                    "Median impressions",
                    "Median Alignment",
                    "Median Distribution",
                    "Median Conversion",
                    "Median Efficiency",
                    "Median profile visit rate",
                    "Median follows/1k",
                    "Cheap Exposure ratio",
                ],
            )
        )
    else:
        lines.append("No content-type data was available.")

    lines.extend(["", "## 11. Operating Recommendations", ""])
    lines.append(
        "Every recommendation below is traceable to retained audit metrics and is observational, not causal."
    )
    lines.append("")
    lines.extend(
        _table(
            _recommendation_rows(scoring),
            [
                "Recommendation",
                "Supporting metric",
                "Observed value",
                "Baseline",
                "Eligible n",
                "Comparison",
                "Uncertainty",
            ],
        )
    )

    lines.extend(["", "## 12. Methodology Notes", ""])
    lines.extend(
        [
            "- Rates are action counts divided by positive impressions; zero impressions makes rates unavailable.",
            "- Stabilized rates use the account baseline and the report's shrinkage k before rate-derived scoring.",
            "- Per-signal Alignment contributions use the exported scoring rate (the stabilized rate after conditional eligible-only winsorization), multiplied by the public parameter weight.",
            "- All displayed 0–100 scores are account-relative average-rank percentiles, not probabilities or cross-account benchmarks.",
            "- Conversion/Efficiency component weights are versioned auditor policy, not X parameters.",
            "- Quadrant cutoffs, badges, and detector thresholds are versioned account-relative auditor policy, not X thresholds or predictions.",
            "- Missing values render as `unavailable`; an observed numeric zero remains zero.",
        ]
    )
    lines.extend(["", "## 13. Limitations", ""])
    lines.extend(
        [
            "- Public repository defaults may differ from experiments or runtime production configuration.",
            "- Aggregate Analytics cannot reveal viewer-post Phoenix predictions, candidate context, filters, or reranking state.",
            "- This report cannot detect shadowbans, visibility enforcement, or guarantee distribution or growth.",
            "- Duplicate reconciliation avoids cumulative summing but cannot recover undocumented export-window semantics.",
            "- Rows without a stable ID, canonical URL, or text-plus-timestamp are preserved rather than weakly merged; they may remain duplicated across exports.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown(report: str, path: Path) -> Path:
    """Write an audit report without silently overwriting an existing file."""

    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path


def parse_alignment_details(value: object) -> list[dict[str, Any]]:
    """A small public seam for integrations that need per-signal explanations."""

    if value is None or value is pd.NA or pd.isna(value):
        return []
    return json.loads(str(value))

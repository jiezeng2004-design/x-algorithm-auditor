"""Typer command line interface for the local audit workflow."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from x_algorithm_auditor.algorithm.fetcher import AlgorithmSourceError, SnapshotProvider
from x_algorithm_auditor.analytics.deduplicate import deduplicate_posts
from x_algorithm_auditor.analytics.loader import AnalyticsLoadError, load_analytics
from x_algorithm_auditor.presets.loader import PresetLoadError, load_preset
from x_algorithm_auditor.reports.csv_export import write_scored_csv
from x_algorithm_auditor.reports.markdown import render_markdown, write_markdown
from x_algorithm_auditor.scoring.common import load_scoring_config
from x_algorithm_auditor.scoring.pipeline import score_posts

app = typer.Typer(
    name="xalgo",
    help=(
        "Audit X Analytics locally using a commit-pinned public Algorithm Snapshot. "
        "Algorithm Alignment is an observed account-relative proxy, not X's official score."
    ),
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Keep ``audit`` as an explicit subcommand instead of flattening a one-command CLI."""


def _output_paths(directory: Path) -> tuple[Path, Path]:
    """Generate paired report names without silently replacing existing output."""

    stem = f"audit-{date.today().isoformat()}"
    candidate = 0
    while True:
        suffix = "" if candidate == 0 else f"-{candidate}"
        markdown = directory / f"{stem}{suffix}.md"
        csv = directory / f"scored-posts{suffix}.csv"
        if not markdown.exists() and not csv.exists():
            return markdown, csv
        candidate += 1


@app.command()
def audit(
    input_path: Annotated[
        Path, typer.Argument(help="CSV or XLSX X Analytics export to read locally.")
    ],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory.")] = Path(
        "reports"
    ),
    snapshot_dir: Annotated[
        Path,
        typer.Option("--snapshot-dir", help="Directory holding validated Algorithm Snapshots."),
    ] = Path("snapshots"),
    offline: Annotated[
        bool,
        typer.Option("--offline", help="Use only the latest validated local snapshot cache."),
    ] = False,
    alias_map: Annotated[
        Path | None,
        typer.Option("--alias-map", help="YAML mapping of source headers to canonical names."),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Methodology-v1 scoring policy YAML."),
    ] = None,
    preset: Annotated[
        Path | None,
        typer.Option(
            "--preset",
            help=(
                "Optional preset YAML: classifier keywords and report context only; "
                "it cannot override scoring policy or source provenance."
            ),
        ),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Fail if malformed/negative input diagnostics were found."),
    ] = False,
) -> None:
    """Run one CSV/XLSX audit and generate Markdown plus stable scored CSV."""

    try:
        loaded = load_analytics(input_path, alias_map)
        if strict and any(
            count
            for event, count in loaded.quality.events.items()
            if event.startswith(("malformed_", "negative_", "percentage_"))
        ):
            raise AnalyticsLoadError(
                "strict validation rejected malformed, negative, or percentage-for-count values"
            )
        deduplicated = deduplicate_posts(loaded.data)
        provider = SnapshotProvider()
        acquisition = provider.acquire(snapshot_dir, offline=offline)
        score_config = load_scoring_config(config)
        selected_preset = load_preset(preset) if preset is not None else None
        scored, scoring = score_posts(
            deduplicated.data, acquisition.snapshot, score_config, preset=selected_preset
        )
        markdown = render_markdown(
            data=scored,
            snapshot=acquisition.snapshot,
            quality=loaded.quality,
            deduplication=deduplicated.summary,
            scoring=scoring,
            preset=selected_preset,
        )
        markdown_path, csv_path = _output_paths(output)
        # Check both names before creating either output, avoiding a misleading
        # partial success if an external process creates one path concurrently.
        if markdown_path.exists() or csv_path.exists():
            raise FileExistsError("report output path became occupied; rerun the audit")
        write_markdown(markdown, markdown_path)
        try:
            write_scored_csv(
                scored,
                csv_path,
                source_mode=acquisition.snapshot.source_mode,
                snapshot_commit=acquisition.snapshot.commit_sha,
            )
        except Exception:
            # The report is safe but incomplete; make the failure explicit rather
            # than claiming a completed paired output.
            raise
    except AnalyticsLoadError as error:
        typer.echo(f"Input validation failed: {error}", err=True)
        raise typer.Exit(code=2) from error
    except AlgorithmSourceError as error:
        typer.echo(f"Algorithm source failure: {error}", err=True)
        raise typer.Exit(code=3) from error
    except (PresetLoadError, ValueError, OSError, FileExistsError) as error:
        typer.echo(f"Audit failed: {error}", err=True)
        raise typer.Exit(code=4) from error

    typer.echo("Audit completed with local output:")
    typer.echo(f"  Markdown: {markdown_path}")
    typer.echo(f"  CSV: {csv_path}")
    typer.echo(f"  Algorithm source: {acquisition.snapshot.source_mode}")
    typer.echo(f"  Snapshot commit: {acquisition.snapshot.commit_sha}")
    if acquisition.snapshot.warnings:
        typer.echo(f"  Warnings: {len(acquisition.snapshot.warnings)}")


if __name__ == "__main__":  # pragma: no cover - console entry point exercises app
    app()

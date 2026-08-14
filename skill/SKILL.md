---
name: x-algorithm-auditor
description: Audit user-supplied X Analytics CSV/XLSX with commit-pinned X algorithm snapshots, an account-relative four-score proxy, Cheap Exposure and Under-distributed Winner detection, and explainable Markdown/CSV reports. Use when a creator asks to validate, score, explain, or recommend actions from a local X Analytics export.
---

# X Algorithm Auditor

Run a local, explainable audit of one creator's exported X Analytics. Treat all account-level conclusions as relative to the supplied audit cohort.

## Workflow

Follow this order: **Validate → Snapshot → Normalize → Score → Detect → Explain → Recommend**.

1. Validate the input before drawing conclusions.

   - Accept only a user-supplied `.csv` or `.xlsx` export. Reject `.xls` and
     `.xlsm` with the CLI's actionable unsupported-format error; do not add a
     legacy spreadsheet dependency merely to guess at their semantics.
   - Run the audit locally; do not request X credentials, cookies, OAuth, scraping, browser automation, or paid-model access.
   - Preserve `unavailable` distinctly from an observed numeric `0`. Missing, malformed, negative, or zero-denominator values are not zero.
   - Treat very low-exposure rows as diagnostics only. They cannot receive rate-derived final scores, quadrants, detector flags, or strong recommendations.

2. Acquire an Algorithm Snapshot.

   ```bash
   xalgo audit "PATH/TO/analytics.csv" --output reports
   ```

   - Prefer a live commit-pinned public snapshot when available.
   - If the run reports `Algorithm source: cached`, name the exact snapshot commit in the explanation. Never imply the values are current/live when the report says cached.

3. Normalize and score the export.

   - Explain that **Algorithm Alignment** is an observed, account-relative proxy based on public weights and historical action rates.
   - State that observed rates are not Phoenix viewer-post probabilities and are not X's official ranking score.
   - Keep Alignment, Distribution, Creator Conversion, and Content Efficiency separate.
   - Use raw/stabilized/scoring rates and signal coverage to answer why a row received its result.

4. Detect and classify with evidence gates.

   - Interpret Cheap Exposure only when the report shows high account-relative Distribution plus low observed Conversion and Efficiency in a sufficient eligible cohort.
   - Interpret Under-distributed Winner only when low account-relative Distribution coincides with high observed Conversion and Efficiency; place only qualified rows in the Repackage Queue.
   - Treat deterministic content types as transparent heuristics. Metadata Reply, Quote, and Thread take precedence over keyword guesses.

5. Explain the output.

   - Deliver the generated Markdown report and scored CSV paths.
   - Cite source mode and commit, data-quality diagnostics, sample-confidence/coverage, detector trigger metrics, and classifier reason/version.
   - Say `insufficient evidence` when type-level eligible samples are too small instead of inventing broad content advice.

6. Recommend conservatively.

   - Base each suggestion on the report's supporting metric, account baseline, eligible sample count, comparison value, and uncertainty.
   - Treat historical preset baselines only as comparison priors. Prioritize new Analytics observations and never force an old conclusion onto a new export.
   - Use an optional preset only for classifier keywords, report context, or comparison display:

   ```bash
   xalgo audit "PATH/TO/analytics.xlsx" --preset "PATH/TO/preset.yaml" --output reports
   ```

   - Do not allow a preset to override algorithm provenance, missing-value semantics, scoring formula, eligibility gates, or detector thresholds.

## Offline / reproducible run

Use a validated local snapshot explicitly when network access is unavailable:

```bash
xalgo audit "PATH/TO/analytics.xlsx" --offline --snapshot-dir snapshots --output reports
```

Report the cached mode and full commit. Do not substitute bundled values or call the snapshot live.

## Boundaries

Do not claim that this tool calculates X's real ranking score, predicts future impressions, detects shadowbans, reveals visibility filtering decisions, guarantees follows, or guarantees recommendation. Public repository defaults can differ from runtime experiments and per-viewer ranking context.

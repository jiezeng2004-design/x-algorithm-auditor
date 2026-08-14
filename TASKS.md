# X Algorithm Auditor Task Plan

Owner model policy: Lead designs and reviews gates; Worker implements coherent
phase-sized packages and performs its own test/fix/retest loop.

## Stage A — Lead architecture baseline

- [x] Inspect workspace and Git baseline.
- [x] Compare the official repository and three existing creator projects at
  pinned revisions before finalizing product architecture.
- [x] Define a no-copy differentiation and release-worthiness gate.
- [x] Read current official README, params, scorer, filters, and visibility
  rules at a pinned commit.
- [x] Define architecture boundaries.
- [x] Define normative scoring methodology and small-sample protection.
- [x] Define limitations and source-honesty rules.
- [x] Define phase tasks and acceptance gates.
- [x] Complete the ten-question Lead self-check.

Stage A files are normative for Worker implementation:

- `docs/architecture.md`
- `docs/methodology.md`
- `docs/limitations.md`
- `docs/competitive-analysis.md`
- `TASKS.md`
- `ACCEPTANCE.md`

## Phase 1 — Worker implementation package

Worker receives this as one package and should implement, test, fix, retest,
and lint before returning.

Status: **[x] Complete — Gate #1 passed after the required data-integrity,
active-scorer, explainability, and data-quality repairs.**

### P1.1 Project foundation

- Create Python 3.11+ `src` package and `xalgo` Typer entry point.
- Use a lightweight stack: pandas, pydantic, PyYAML, openpyxl, Typer, pytest,
  Ruff; standard library networking is preferred.
- Add versioned config and alias data.
- Add `.gitignore`; do not add generated reports, caches, environments, or real
  Analytics.
- Do not choose a public license in Phase 1.

### P1.2 Algorithm subsystem

- Resolve official branch SHA and fetch `param.rs` pinned to that SHA.
- Parse multiline Rust `param!` macros without line-number assumptions.
- Extract relevant params, supported positive/negative signals, contextual
  scoring mode, and structured unknown/unparsed diagnostics.
- Keep source parsing, Analytics availability, and mapping confidence separate;
  only direct or adapter-proven conditional relations enter Alignment.
- Validate registered scorer use against commit-pinned ranking source when
  available; do not treat every `*Weight` name as active by assumption.
- Persist validated immutable snapshot JSON with SHA-256 and sync date.
- Load latest valid cache on live failure and clearly mark `cached`.
- Diff commit/source/parsed params against previous snapshot.
- Warn on missing, renamed-looking, unknown, malformed, and nonliteral params.
- Never use hidden hardcoded weights as if they were live.

### P1.3 Analytics ingestion subsystem

- Load CSV and XLSX with deterministic encoding/worksheet behavior.
- Map versioned aliases to canonical fields; allow explicit overrides.
- Preserve nullable counts and missing-state diagnostics.
- Validate negatives, malformed numbers/timestamps, zero impressions,
  percentage strings, date windows, and ambiguous mappings.
- Deduplicate using the normative identity and anchor hierarchy; never sum
  cumulative duplicates.
- Emit a structured data-quality summary.

### P1.4 Normalization and four score families

- Calculate raw rates only with positive impressions.
- Implement account baseline, `k`, shrinkage, eligibility, confidence labels,
  and conditional winsorization exactly as methodology-v1.
- Keep rate-derived final scores unavailable below the exposure eligibility
  floor while retaining the underlying diagnostics and Distribution.
- Implement Alignment contributions and coverage using parsed snapshot weights.
- Implement impression-percentile Distribution.
- Implement funnel-only Creator Conversion.
- Implement valuable-action Content Efficiency with no double counting.
- Preserve raw inputs and intermediates needed to explain each result.

### P1.5 Reports and CLI

- `xalgo audit INPUT` accepts CSV and XLSX.
- Support explicit output, snapshot, config, alias-map, and offline/cache options
  where needed for deterministic tests.
- Write `audit-YYYY-MM-DD.md` and `scored-posts.csv` without silently
  overwriting unrelated data.
- Markdown contains Phase 1 sections even when later sections say `Phase 2 not
  enabled`.
- CSV contains the required post/rate/score/coverage columns.
- Both outputs preserve `unavailable` versus observed zero.
- Exit codes and messages distinguish input failure, source/cache failure,
  validation failure, and successful audit with warnings.

### P1.6 Verification owned by Worker

- Add focused unit and integration tests listed in `ACCEPTANCE.md`.
- Use only synthetic fixtures.
- Run `pytest` until green.
- Run `ruff check .` and `ruff format --check .` until green.
- Run CLI help.
- Run an offline deterministic synthetic audit.
- If public network is available, run one live snapshot; otherwise show tested
  cached fallback without claiming live proof.
- Return one complete phase summary with exact commands/results and blockers.
- Demonstrate a material executable capability beyond the three projects in
  `docs/competitive-analysis.md`; do not copy their prompts, prose, formulas,
  presets, branding, or unsupported claims.

## Gate #1 — Lead review

Lead reviews only after the complete Phase 1 return:

- architecture and methodology compliance;
- source provenance and mode honesty;
- missing-state and dedup semantics;
- small-sample and percentile correctness;
- four-score separation and explanation data;
- test assertion strength, CLI behavior, sample report, and full task-owned
  tree/diff.

Lead output categories:

```text
PASS

or

BLOCKING ISSUES
HIGH PRIORITY
MEDIUM
LOW
```

Only Blocking and High are returned for mandatory repair.

## Phase 1 repair — Worker

- Fix Gate #1 Blocking and High findings only.
- Add regression tests.
- Run pytest, Ruff check, Ruff format check, CLI smoke, and synthetic audit.
- Return exact evidence once, not file-by-file updates.

## Phase 2 — Worker implementation package

Status: **[x] Complete — Gate #2 passed with no Blocking/High findings.**

- [x] Implement exhaustive quadrants and stronger Core Winner badge.
- [x] Implement Cheap Exposure and Under-distributed Winner overlay detectors.
- [x] Add Repackage Queue.
- [x] Implement replaceable deterministic content classifier and reasons.
- [x] Aggregate content-type metrics with sample sufficiency.
- [x] Implement evidence-backed, noncausal recommendation rules.
- [x] Add report sections, CSV fields, config, fixtures, and tests.
- [x] Run the complete verification loop before returning.

## Gate #2 — Lead review

Lead checks overfitting, fake precision, proxy wording, detector conjunctions,
data provenance in recommendations, small-sample behavior, percentile logic,
and real sample outputs. Only Blocking and High are mandatory repairs.

## Phase 3 — Worker implementation package

Status: **[x] Complete — worker verification and the Lead Final Audit are
recorded in `ACCEPTANCE.md`.**

- [x] Create `skill/SKILL.md` for the generic local audit workflow.
- [x] Add optional, explicit preset loading with schema validation.
- [x] Prove generic core runs with no preset.
- [x] Add synthetic example CSV/XLSX and generated example report/CSV.
- [x] Polish README with installation, CLI, methodology, privacy, and limitation
  language.
- [x] Add publication hygiene checks; leave license choice explicit if not supplied.
- [x] Run full verification.

## Final Audit — Lead

Status: **[x] PASS — completed 2026-08-14 with no Blocking or High issue.**

- [x] Inspect current branch/HEAD/status and task-owned changes.
- [x] Install the final wheel in a project-external clean environment.
- [x] Run tests, lint, format check, CLI help, synthetic audits, and inspect the
  sample report.
- [x] Fetch and save a current live official snapshot.
- [x] Review README, Skill, preset isolation, examples, report language, and
  limitations.
- [x] Issue the exact final report structure requested by the project owner.

## Deferred beyond Phase 3

- UI or hosted service.
- X API, authentication, scraping, or browser automation.
- Paid/hosted LLM classification.
- Cross-account benchmarking.
- Production deployment or publishing.
- Integration with X Under the Hood transparency data.

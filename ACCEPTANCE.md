# X Algorithm Auditor Acceptance Criteria

Version: Current acceptance record, 2026-08-14

## 1. Global invariants

Every phase must preserve all of these:

1. The primary metric is an **Observed Algorithm Alignment Proxy**.
2. No code, help, report, README, Skill, or example calls it X's official
   ranking score or a Phoenix prediction.
3. Unavailable is nullable and never serialized or rendered as numeric zero.
4. Analytics rates are not named or typed as prediction probabilities.
5. Input files are read-only and no X credentials are requested.
6. Scores are account-relative; cross-account comparability is disclaimed.
7. Low-exposure posts have unavailable rate-derived final scores and cannot
   enter rankings, quadrants, winner lists, detectors, or strong
   recommendations.
8. Cached source use is prominent and includes its exact commit.
9. Nonobservable algorithm mechanisms remain context, not invented score terms.
10. Generated tests/examples contain only synthetic data.
11. Official-source parsing, mapping confidence, and per-row observation state
    are distinct; a similar field name alone cannot authorize scoring.
12. No copied competitor prompt, prose, arbitrary formula, private preset, or
    unsupported quantitative claim appears in the generic core.
13. Conversion/Efficiency weights and detector cutoffs are labelled versioned
    auditor policy, never X parameters or universal targets.

Any invariant violation is Blocking.

## 2. Stage A acceptance

- [x] Required five documents plus the competitive-analysis research record
  exist.
- [x] Four repositories were compared at pinned revisions before formal design.
- [x] The project has an explicit stop/release-worthiness gate and no-copy
  boundary.
- [x] Architecture cites a current official commit and source paths.
- [x] Methodology defines Missing != Zero end-to-end.
- [x] Methodology defines exact rate, shrinkage, percentile, and four-score
  formulas.
- [x] Tiny-exposure eligibility and confidence are explicit.
- [x] Cheap Exposure requires high Distribution plus low Conversion and low
  Efficiency.
- [x] Under-distributed Winner requires below-baseline Distribution plus high
  Conversion and Efficiency.
- [x] Algorithm source drift and alternate scoring mode behavior are specified.
- [x] Ten Lead self-check questions have explicit PASS answers.

## 3. Phase 1 functional acceptance

### 3.1 Algorithm snapshot

- [x] Live mode resolves a full 40-character commit SHA before fetching source.
- [x] Source bytes are fetched by commit, not a moving branch URL.
- [x] Snapshot records repository, branch, commit, UTC fetch time, path, source
  hash, parameter sync date, signals, unsupported/unparsed params, and mode.
- [x] Parser handles one-line and multiline `param!` forms.
- [x] Known positive and negative weights parse from representative current
  source.
- [x] Relation registry distinguishes direct, conditional, approximate,
  outcome, and unobservable mappings.
- [x] Link clicks/open link, detail expands/click, media views/media heads, and
  profile visits/profile click are not silently treated as exact mappings.
- [x] Registered active-scorer verification is commit-pinned when available and
  honestly reports reduced coverage otherwise.
- [x] A parameter explicitly absent from the pinned ranking scorer contributes
  nothing; unavailable ranking-source verification is labelled unverified.
- [x] Missing expected weights warn without crashing when other signals remain.
- [x] Renamed-looking/unknown `*Weight` params appear in diagnostics.
- [x] Malformed numeric defaults appear as unparsed and are not coerced to zero.
- [x] Cache fallback validates schema/hash, sets `cached`, and exposes commit.
- [x] No live source plus no valid cache exits nonzero with an actionable error.
- [x] Change detection covers added, removed, changed, mode, commit-only, and
  identical snapshots.

### 3.2 Analytics ingestion

- [x] CSV and XLSX containing equivalent synthetic data normalize equivalently.
- [x] Common alias/case/spacing variations map correctly.
- [x] Explicit aliases can resolve a safe unknown header.
- [x] Ambiguous mappings fail rather than guess.
- [x] Required minimum identity/exposure failures are actionable.
- [x] Missing columns and missing cells remain unavailable.
- [x] A supplied zero remains observed zero.
- [x] Negative and malformed values become unavailable plus diagnostics.
- [x] Zero impressions makes rates unavailable without division warnings.
- [x] Percentage strings obey field semantics and do not become fake counts.
- [x] Malformed timestamps do not crash and reduce identity quality visibly.
- [x] Multiple date ranges are detected and reported.
- [x] Duplicate post IDs, status IDs, canonical URLs, and text/timestamps have
  focused tests; weak/blank identities receive unique provenance fingerprints
  and are preserved with diagnostics rather than merged.
- [x] Duplicate cumulative rows are never summed.
- [x] Deduplicated-row and conflict counts are reported.

### 3.3 Normalization and scoring

- [x] Raw rate tests cover positive denominator, observed zero, missing action,
  missing impressions, and zero impressions.
- [x] Account baselines, clipped `k`, reliability, stabilized rates,
  eligibility floor, and confidence labels match methodology-v1 examples.
- [x] Conditional winsorization is tested above and below the 20-row boundary.
- [x] Average-rank percentile handles ties, one row, and missing values.
- [x] A `3 impressions / 1 reply` fixture is strongly shrunk, has unavailable
  Alignment/Conversion/Efficiency final scores, and cannot rank or enter any
  quadrant, top label, detector, or strong recommendation.
- [x] Alignment uses parsed snapshot weights and only observed mapped signals.
- [x] A mapped signal must meet the 80% eligible-row dataset-observable rule
  before defining a cross-post composite.
- [x] Alignment requires at least two used signals and 0.50 weighted coverage;
  Conversion/Efficiency require 0.50 component coverage.
- [x] Aggregate and channel-specific shares are not double-counted.
- [x] Negative feedback contributes only when actually observed.
- [x] Per-signal contributions sum to the stored raw alignment numerator.
- [x] Each contribution is reconstructable as public weight times the exported
  post-signal scoring rate after any winsorization.
- [x] Alignment score is unavailable when no mapped signal is observed.
- [x] Distribution is the impression percentile and does not include engagement.
- [x] Conversion uses only follow/profile funnel components by default.
- [x] Efficiency excludes impressions, follows, and profile visits and caps the
  default influence of likes at 0.05 before renormalization.
- [x] Aggregate engagement fallback is not combined with child metrics.
- [x] Final scores are nullable integers in `[0, 100]`.

### 3.4 CLI and outputs

- [x] `xalgo --help` and `xalgo audit --help` exit zero.
- [x] `xalgo audit sample.csv` completes with a deterministic offline snapshot.
- [x] Equivalent XLSX audit completes.
- [x] Default output names are `audit-YYYY-MM-DD.md` and `scored-posts.csv`.
- [x] Existing unrelated output is not silently overwritten.
- [x] Markdown includes:
  1. Executive Summary
  2. Data Coverage
  3. Algorithm Snapshot
  4. Observable Signals
  5. Unobservable Signals
  6. Core Winners
  7. Cheap Exposure
  8. Under-distributed Winners
  9. Traffic Without Asset
  10. Content Type Analysis
  11. Operating Recommendations
  12. Methodology Notes
  13. Limitations
- [x] Phase 2 sections were honestly marked not enabled before implementation;
  after Phase 2 they render actual evidence rather than placeholders.
- [x] Markdown always contains the proxy/Phoenix disclaimer.
- [x] Markdown identifies live/cached source and full commit.
- [x] Markdown renders missing metrics as `unavailable`.
- [x] CSV contains identifiers, text, dates/types, impressions, relevant rates,
  four scores, quadrants, detector evidence, content type/classifier evidence,
  observable count, coverage, and confidence.
- [x] CSV missing fields are empty/null and observed zeros are numeric zero.

## 4. Phase 1 test matrix

At minimum, focused tests cover:

```text
Algorithm: known, missing, malformed/renamed, snapshot, cache, change diff
Analytics: CSV, XLSX, aliases, missing, duplicates, zero, malformed, ranges
Scoring: rates, null semantics, shrinkage, winsor, percentile, four scores
Reports: Markdown sections/disclaimers/cache/missing, CSV schema/null/zero
CLI: help, successful offline audit, source failure, invalid input
```

Test count is not an acceptance metric; assertion strength and behavior coverage
are. Tests must exercise public seams as well as small pure functions.

## 5. Phase 1 verification evidence

Worker and Lead must report actual, current results for:

```text
installation or environment sync
pytest
ruff check .
ruff format --check .
xalgo --help
xalgo audit --help
synthetic CSV audit
synthetic XLSX audit
sample Markdown inspection
sample CSV inspection
```

A passing build or unit test is not described as a live GitHub snapshot. A live
snapshot is separately evidenced with source mode, commit, and saved snapshot.

## 6. Gate #1 severity

### Blocking

- Global invariant violation.
- Data corruption, cumulative duplicate summing, missing-to-zero coercion.
- Official-score/Phoenix misrepresentation.
- Source provenance mismatch or unlabelled hardcoded fallback.
- CLI cannot complete a deterministic offline audit.
- Core scoring formula materially differs from methodology without Lead change.

### High

- Tiny samples can enter strong outputs.
- One of four scores conflates a prohibited dimension.
- Parser drift/malformed handling loses evidence silently.
- Required format unsupported or report/CSV semantics materially wrong.
- Tests pass while not asserting the promised behavior.

### Medium / Low

Nonblocking robustness, ergonomics, documentation, or maintainability issues
that do not falsify core results. Only Blocking and High must return to Worker
before Phase 2.

## 7. Phase 2 acceptance

- [x] Quadrants are exhaustive only when Alignment and Conversion are present;
  otherwise `insufficient_data`.
- [x] Core Winner badge requires both scores >= 75 plus eligibility/coverage.
- [x] Cheap Exposure implements all conjunctive conditions and minimum cohort.
- [x] Under-distributed Winner implements all conjunctive conditions and
  minimum cohort.
- [x] Boundary, missing-metric, small-cohort, and tiny-exposure detector tests
  exist.
- [x] Repackage Queue contains only qualified under-distributed winners.
- [x] Classifier is deterministic, replaceable, and reports reason/version.
- [x] Metadata Reply/Quote/Thread takes precedence over text heuristics.
- [x] Content-type summaries include sample sufficiency and required metrics.
- [x] Recommendations cite real metrics, baseline, and sample count.
- [x] No strong recommendation is generated below evidence thresholds.
- [x] Full Phase 1 verification remains green.

## 8. Gate #2 acceptance

Lead must find no Blocking/High issue in:

- overfitting or private conclusions in generic core;
- false precision or proxy-as-official wording;
- detector logic and missing handling;
- recommendation evidence provenance;
- low-sample eligibility;
- percentile thresholds and tied cohorts;
- sample report claims.

## 9. Phase 3 acceptance

- [x] `skill/SKILL.md` implements Validate -> Snapshot -> Normalize -> Score ->
  Detect -> Explain -> Recommend and repeats all global invariants.
- [x] Generic workflow succeeds without any preset.
- [x] Presets are optional, explicit, schema-validated, and cannot override
  source provenance or Missing != Zero.
- [x] Historical baselines are comparison priors, never forced conclusions.
- [x] Synthetic example CSV and XLSX are documented and contain edge cases.
- [x] Example report/CSV are generated by the current CLI, not hand-authored.
- [x] README documents install, use, outputs, methodology, privacy, limitations,
  cached/live evidence, and license status.
- [x] Publication hygiene excludes real Analytics, credentials, cache secrets,
  environments, and generated local noise.

### Recorded worker verification — 2026-08-14

- [x] `uv sync --all-groups --offline` completed against the local project.
- [x] `python -m pytest -q -p no:cacheprovider --basetemp ...` completed:
  `46 passed`.
- [x] `ruff check .` and `ruff format --check .` completed cleanly.
- [x] `xalgo --help` and `xalgo audit --help` completed cleanly.
- [x] Offline generic CSV, XLSX, and optional-preset audits completed against
  the synthetic examples, using validated cached commit
  `a389166f6cf5da70a286b568c87695d4dcdce3a1`.
- [x] `quick_validate.py skill` completed with UTF-8 mode; the validator's
  scope is the required `skill/` directory, and `agents/openai.yaml` was also
  structurally checked.
- [x] Current wheel and sdist built successfully; the wheel contains bundled
  runtime YAML. A fresh project-external venv installed that wheel and ran
  `xalgo --help` plus a cached synthetic audit from outside the source tree.
- [x] No Phase 3 live fetch is claimed. Cached evidence remains explicitly
  labelled as cached with its full snapshot commit.

### Recorded Lead Final Audit — 2026-08-14

- [x] `pytest tests -q -p no:cacheprovider --ignore=tests/runtime --basetemp
  ...` completed outside the managed sandbox after its temporary-directory ACL
  blocked the sandboxed run: `46 passed in 7.24s`.
- [x] `ruff check .` passed and `ruff format --check .` reported `51 files
  already formatted`.
- [x] `quick_validate.py skill` reported `Skill is valid!`; `xalgo --help` and
  `xalgo audit --help` both exited zero.
- [x] Current-source offline CSV and XLSX audits both produced 15 scored rows
  from the equivalent synthetic input and byte-identical scored CSV output.
- [x] A live official fetch completed and saved commit
  `a389166f6cf5da70a286b568c87695d4dcdce3a1` with source mode `live`, 16
  extracted signals, 10 unsupported parameters, zero unparsed parameters, and
  full registered-scorer coverage.
- [x] The current wheel and sdist rebuilt successfully. The wheel contains both
  runtime YAML resources and the CSV/XLSX-only loader contract.
- [x] A newly created project-external Python 3.12 venv installed the final
  wheel and completed `xalgo --help` plus a cached synthetic audit from outside
  the source tree.
- [x] Publication hygiene found no credential-named files or secret-like token
  values in the intended source/example tree. At the time of this Final Audit,
  no license, commit, push, publication, or deployment was performed.
- [x] Final Gate result: **PASS**, with no Blocking or High issue remaining.

## 10. Final acceptance

Final status may be PASS only when all required phases and current verification
commands pass, a sample audit exists, and no Blocking/High issue remains.

`Ready for Real Analytics? YES` means the local tool is ready to ingest a first
private export for validation. It does not mean every export variation is
supported or that production behavior has been verified.

The final report must explicitly separate:

- static/source inspection;
- unit/integration test results;
- installed CLI execution;
- synthetic audit execution;
- live official source acquisition, if actually performed;
- real private Analytics validation, which is not performed without user data.

## 11. v0.1.0 minimal release preparation — 2026-08-14

- [x] Golden Validation completed against 321 real posts with verdict `PASS
  WITH MINOR ISSUES`; private inputs and reports remain ignored and untracked.
- [x] Explicit canonical URL aliases cover Post/Tweet/Status Link and URL
  headers; generic `URL` is not guessed and ambiguity rejection remains active.
- [x] Account overview inputs are rejected with the cross-export coverage and
  attribution warning; reports and README carry the same boundary.
- [x] Content Type Analysis is labelled Experimental and descriptive rather
  than authoritative.
- [x] MIT License and a minimal Python 3.12 GitHub Actions workflow are present.
- [x] Final release regression: `55 passed in 6.83s`; Ruff check passed; 51
  Python files were already formatted; wheel/sdist, CLI help, cached synthetic
  audit, and live snapshot audit passed.
- [x] `git add --dry-run --verbose .` identified 66 first-commit candidates,
  zero private-data/report matches, left the index empty, and did not leave an
  index lock.
- [x] No commit, push, tag, GitHub Release, PyPI publication, or deployment was
  performed.

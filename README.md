# X Algorithm Auditor

X Algorithm Auditor is a local CLI that connects the official public
[`xai-org/x-algorithm`](https://github.com/xai-org/x-algorithm) source to a
creator's exported X Analytics. It calculates an account-relative **Observed
Algorithm Alignment Proxy**, finds **Cheap Exposure** and **Under-distributed
Winner** review candidates, and produces explainable Markdown plus
machine-readable CSV.

- Runs locally on CSV/XLSX exports.
- Requires no X API, OAuth, account login, scraping, browser automation, GPU,
  or paid model.
- Uses commit-pinned public algorithm source with explicit live/cached
  provenance.

> [!IMPORTANT]
> This is **NOT an official X ranking score**. It does not know Phoenix
> `viewer × post` probabilities, predict future impressions, detect shadowbans,
> or access private X production configuration.

## Why this exists

The project is intentionally not another static algorithm explainer, draft
grader, reply scraper, or generic content-advice prompt. Its useful boundary
is a reproducible audit chain:

```text
commit-pinned public source
  -> dynamic Algorithm Snapshot and change evidence
  -> nullable CSV/XLSX ingestion and non-additive deduplication
  -> small-sample-protected, account-relative four-score audit
  -> Cheap Exposure and Under-distributed Winner review queues
  -> evidence-bearing Markdown and stable scored CSV
```

The [competitive analysis](docs/competitive-analysis.md) records the research
against the official repository and the three related open-source projects,
including why their older source conclusions are not copied into this tool.

## Install

Python 3.11+ is required. The tool is CPU-only and has no X API, login,
browser automation, scraping, GPU, or paid-model dependency.

With `uv` from a source checkout:

```bash
uv sync --all-groups
uv run xalgo --help
```

With `pip` from a source checkout or built wheel:

```bash
python -m pip install .
xalgo --help
```

The wheel bundles the default methodology and generic content-taxonomy YAML
files. An installed command therefore does not rely on the original checkout
or its current working directory.

## Audit an Analytics export

```bash
xalgo audit analytics.csv
xalgo audit analytics.xlsx --output reports
```

The input remains local. The loader supports only CSV and XLSX; it maps known
header aliases into a canonical nullable schema and reports unknown, missing,
malformed, negative, and zero-denominator conditions rather than turning them
into zeros.

Account overview and per-post analytics may use different coverage or
attribution semantics and must not be automatically summed or merged. The
auditor requires a per-post export; an account overview may be reviewed as
separate context, but it is not a scoring input or reconciliation source.

For a reproducible offline run, use a previously validated snapshot cache:

```bash
xalgo audit analytics.csv --offline --snapshot-dir snapshots --output reports
```

Each report identifies `live` or `cached` source mode and the full commit SHA.
`cached` means a local validated snapshot was used; it is never evidence of a
live fetch. A successful live fetch is likewise evidence only of the public
source at that commit, not of X production experiments or per-viewer settings.

Useful options:

```bash
xalgo audit analytics.xlsx \
  --alias-map aliases.yaml \
  --config scoring-policy.yaml \
  --preset creator-context.yaml \
  --strict \
  --output reports
```

`--strict` rejects malformed, negative, and percentage-for-count diagnostics.
`--alias-map` is an explicit source-header-to-canonical-field mapping, not a
fuzzy guess. `--config` selects a methodology-v1 policy file.

## Four separate account-relative lenses

Every final score is a 0–100 average-rank percentile within the supplied,
deduplicated account cohort. Scores are not calibrated probabilities and are
not cross-account benchmarks.

| Lens | Question it answers | What it deliberately does not mean |
| --- | --- | --- |
| Algorithm Alignment | Does the post's **observed** action-rate structure align relatively well with available public weighted signals? | X's real ranking score or Phoenix probability |
| Distribution | How much observed exposure did the post receive relative to this account history? | Content quality or causation |
| Creator Conversion | Did exposure become profile visits and follows? | A proxy for likes or a universal growth target |
| Content Efficiency | How much valuable observed behavior occurred per exposure? | Distribution volume or a prediction |

Rates use only positive-impression denominators. Raw rates are retained, while
score inputs use transparent account-baseline shrinkage and eligible-only
winsorization. A `3 impressions / 1 reply` row remains inspectable, but its
Alignment, Conversion, and Efficiency final scores are unavailable; it cannot
enter quadrants, badges, detectors, or strong recommendations. Distribution
remains separately observable.

`unavailable` is never numeric `0`: an observed numeric zero remains zero,
while an absent column, blank/malformed value, or zero denominator is nullable.

## Detectors and recommendations

The detector thresholds are versioned account-relative operating policy, not X
thresholds or guarantees.

- **Cheap Exposure** requires Distribution >= 75, Conversion <= 25, and
  Efficiency <= 25, with all metrics observed, score-eligible exposure, and a
  detector cohort of at least eight eligible posts. It is not merely a
  high-impressions label.
- **Under-distributed Winner** requires Distribution <= 40, Conversion >= 75,
  and Efficiency >= 75 under the same evidence gates. Only qualified rows enter
  the Repackage Queue; the flag does not prove why distribution was lower or
  that repackaging will work.
- **Core Winner** is stricter than the high/high quadrant: Alignment and
  Conversion must both be at least 75 with exposure eligibility and adequate
  Alignment coverage.

## Content Type Analysis — Experimental

Current content classification is heuristic and should be treated as
descriptive rather than authoritative. The local classifier is deterministic
and replaceable; metadata Reply, Quote, and Thread labels take precedence over
keyword rules. Type-level recommendations require sufficient eligible
observations and include the supporting metric, account baseline, sample count,
comparison, and uncertainty. When evidence is insufficient, the tool says so
instead of emitting generic advice.

## Outputs

An audit writes a paired report without silently overwriting an existing pair:

```text
reports/audit-YYYY-MM-DD.md
reports/scored-posts.csv
```

The Markdown report has thirteen sections: Executive Summary, Data Coverage,
Algorithm Snapshot, Observable Signals, Unobservable Signals, Core Winners,
Cheap Exposure, Under-distributed Winners, Traffic Without Asset, Content Type
Analysis, Operating Recommendations, Methodology Notes, and Limitations.

The CSV preserves post identifiers, observed metrics, raw/stabilized/scoring
rates, four score families, coverage/confidence, per-signal Alignment detail,
deduplication provenance, classifier evidence, detector reasons/metrics,
quadrants, and cached/live snapshot provenance. Empty values are unavailable;
numeric zero is retained as `0`.

## Optional personal preset

Presets are local YAML files selected explicitly with `--preset`. They use
`schema_version: preset-v1` and may contain `creator_goal`, `niche`,
`content_taxonomy_keywords`, `historical_baseline`, and `preferred_metrics`.

```yaml
schema_version: preset-v1
creator_goal: Improve repeatable account-asset outcomes
niche: Example niche
content_taxonomy_keywords:
  Comparison: ["tool-a vs tool-b"]
historical_baseline:
  follows_per_1k_impressions: 2.5
preferred_metrics: [Creator Conversion, follows_per_1k_impressions]
```

The schema rejects unknown fields, invalid labels, invalid types, blanks, and
non-finite historical values with actionable errors. A preset can extend local
classifier keywords and add report context/comparison display only. It cannot
override the Algorithm Snapshot, Missing != Zero, generic score formulas,
small-sample gates, detector policy, or current-data conclusions. Historical
values are comparison priors; the new Analytics export remains the scored
evidence. Running without a preset is the fully supported generic core.

## Generic Codex Skill

[skill/SKILL.md](skill/SKILL.md) defines the reusable local workflow:

```text
Validate -> Snapshot -> Normalize -> Score -> Detect -> Explain -> Recommend
```

It repeats the proxy, missing-data, cached-source, low-sample, and no-prediction
boundaries so the tool can be applied to another creator without importing a
private conclusion or personal voice profile.

## Synthetic examples

The repository contains only synthetic sample data:

- [analytics-example.csv](examples/analytics-example.csv)
- [analytics-example.xlsx](examples/analytics-example.xlsx)
- [generated audit report](examples/output/audit-example.md)
- [generated scored CSV](examples/output/scored-posts-example.csv)

The input includes a duplicate export row, missing cell, zero-impression row,
low-exposure row, multiple content types, and detector-rich rows. The generated
report/CSV come from the current CLI with a validated cached snapshot; inspect
the report for the exact commit and source mode. Do not replace these examples
with real Analytics.

## Privacy and limitations

The tool performs local file processing and does not request credentials. Audit
reports can contain post text and account performance, so users are responsible
for secure storage, sharing, and redaction.

This tool cannot:

- calculate an official X ranking score or Phoenix prediction;
- predict future impressions, follows, revenue, or growth;
- detect a shadowban, hidden enforcement state, or visibility-filtering result;
- bypass filters or recommendation systems; or
- guarantee distribution, recommendations, or follower growth.

Public repository defaults can differ from runtime experiments, model modes,
filters, candidate retrieval, reranking, and per-viewer context. Aggregate
Analytics cannot recover those inputs. See the detailed
[methodology](docs/methodology.md), [architecture](docs/architecture.md), and
[limitations](docs/limitations.md).

## License

X Algorithm Auditor is available under the [MIT License](LICENSE).

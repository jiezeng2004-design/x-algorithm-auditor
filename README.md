# X Algorithm Auditor

> **把你的 X Analytics 导出表，变成一份“哪些内容值得继续放大、哪些只是拿了曝光”的本地审计报告。**
>
> No X API. No login. No scraping. No paid model. Your analytics file stays local.

X Algorithm Auditor connects two things you can actually inspect:

1. the public [`xai-org/x-algorithm`](https://github.com/xai-org/x-algorithm) source at a pinned commit;
2. your own exported X Analytics CSV / XLSX.

It then produces account-relative, explainable review signals such as:

- **Observed Algorithm Alignment Proxy**;
- **Cheap Exposure** candidates;
- **Under-distributed Winner** candidates;
- content-efficiency / conversion / distribution comparisons;
- a Markdown report plus scored CSV for follow-up analysis.

> [!IMPORTANT]
> **This is not an official X ranking score.** It does not know private production weights, Phoenix viewer × post probabilities, live experiments, shadowban state or future impressions.

## Why this exists

Most “X algorithm” advice has one of two problems:

- it explains public source code but never connects that source to your own content history;
- or it scores posts with opaque rules that cannot be traced back to observable data.

X Algorithm Auditor is designed around a reproducible chain instead:

```text
public X algorithm source @ pinned commit
                ↓
observable signal snapshot
                ↓
your local Analytics export
                ↓
account-relative scoring
                ↓
review queues + evidence-bearing report
```

The goal is not to claim “this is how X ranks you.”

The goal is:

> **Use public algorithm evidence + your own observed outcomes to decide which posts deserve closer review.**

## Quick start

Requirements:

- Python 3.11+
- a per-post X Analytics export in CSV or XLSX

Install from source with `uv`:

```bash
uv sync --all-groups
uv run xalgo --help
```

Or with pip:

```bash
python -m pip install .
xalgo --help
```

Audit a file:

```bash
xalgo audit analytics.csv
```

Or XLSX with an output directory:

```bash
xalgo audit analytics.xlsx --output reports
```

The input stays local.

## What you get

Typical output:

```text
reports/audit-YYYY-MM-DD.md
reports/scored-posts.csv
```

The Markdown report summarizes:

- data coverage and quality;
- public algorithm snapshot provenance;
- observable vs unobservable signals;
- core winners;
- Cheap Exposure candidates;
- Under-distributed Winners;
- traffic-without-asset patterns;
- content-type observations;
- operating recommendations;
- methodology and limitations.

The CSV keeps the underlying post-level metrics, scores, eligibility, detector reasons and provenance so the result stays inspectable.

## The four lenses

Every final score is **relative to the supplied account cohort**, not a global benchmark.

| Lens | Question it answers | What it does NOT mean |
| --- | --- | --- |
| **Algorithm Alignment** | Does observed action-rate structure align relatively well with available public weighted signals? | X's real ranking score |
| **Distribution** | How much exposure did this post receive relative to this account history? | Content quality |
| **Creator Conversion** | Did exposure become profile visits / follows where observed? | Universal growth quality |
| **Content Efficiency** | How much valuable observed behavior occurred per exposure? | Future distribution prediction |

The tool keeps `unavailable` separate from numeric `0` and applies evidence / sample-size gates before strong classifications.

## The two most useful review queues

### Cheap Exposure

A post may receive strong distribution but weak downstream conversion / efficiency relative to your own history.

That does **not** mean “bad post.” It means:

> This post got attention, but the observed downstream value was weak enough to deserve review.

The detector uses versioned account-relative thresholds and evidence gates instead of a raw “high impressions = Cheap Exposure” shortcut.

### Under-distributed Winner

A post may show relatively strong conversion + efficiency while receiving weak distribution.

That does **not** prove X under-ranked it or that reposting will work.

It means:

> The observed response quality was strong relative to your account history, so the content may deserve repackaging or another look.

Qualified rows can enter the Repackage Queue.

## Reproducible source provenance

The auditor pins the public algorithm source to a commit and records whether the run used:

- `live` source retrieval; or
- a previously validated `cached` snapshot.

Offline run:

```bash
xalgo audit analytics.csv \
  --offline \
  --snapshot-dir snapshots \
  --output reports
```

A cached run proves only which validated public-source snapshot was used. A live run proves only which public commit was fetched. Neither reveals X private production configuration.

## Input discipline matters

The loader supports CSV / XLSX and keeps missing / malformed values nullable instead of silently converting them to zero.

It also distinguishes per-post analytics from account-overview data.

Do **not** automatically sum or merge account-overview metrics into per-post scoring: coverage and attribution semantics may differ.

Useful options:

```bash
xalgo audit analytics.xlsx \
  --alias-map aliases.yaml \
  --config scoring-policy.yaml \
  --preset creator-context.yaml \
  --strict \
  --output reports
```

`--strict` rejects problematic numeric conditions instead of letting them quietly pass through.

## Experimental content-type analysis

Content classification is heuristic and should be treated as descriptive, not authoritative.

The local classifier is deterministic and replaceable. Recommendations require enough eligible observations; when evidence is insufficient, the tool should say so instead of inventing generic advice.

## Optional personal preset

Presets are local YAML files selected explicitly with `--preset`.

They can describe things like:

- creator goal;
- niche;
- content taxonomy keywords;
- historical baseline;
- preferred metrics.

Presets influence local analysis context. They do not give the tool access to private X ranking systems.

## Privacy

- CSV / XLSX input stays local;
- no X API required;
- no OAuth required;
- no account login;
- no browser automation;
- no scraping;
- no paid model;
- CPU-only workflow.

## What this tool cannot tell you

It cannot reliably answer:

- “What is my real X ranking score?”
- “Am I shadowbanned?”
- “Why did Phoenix rank this specific viewer/post pair?”
- “What will my next post's impressions be?”
- “Which private production weights is X using today?”

If a report appears to imply those claims, treat that as a bug in interpretation.

## Methodology principle

The project deliberately prefers:

```text
observable evidence
> transparent uncertainty
> reproducible heuristics
> confident-sounding guesses
```

That makes the output useful as an **audit and review aid**, not an oracle.

## Documentation

See the repository docs for methodology, competitive analysis and implementation notes, including:

- [competitive analysis](docs/competitive-analysis.md)

## License

MIT. See [LICENSE](LICENSE).

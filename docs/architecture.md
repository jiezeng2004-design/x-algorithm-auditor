# X Algorithm Auditor Architecture

Status: Stage A architecture baseline  
Date: 2026-08-14  
Target runtime: Python 3.11+, Windows and Linux, CPU-only

## 1. Purpose and boundary

X Algorithm Auditor connects two evidence sources:

1. public source code from `xai-org/x-algorithm`; and
2. a creator's own exported X Analytics CSV or XLSX data.

It produces an account-relative, explainable **Observed Algorithm Alignment
Proxy** plus separate distribution, creator-conversion, and content-efficiency
scores. It does not reproduce X's online ranking system.

The product is local-first. Phase 1 has no X API, OAuth, cookies, browser
automation, scraping, paid model, GPU, account login, or UI.

## 2. Current official-source basis

Stage A was checked against the official repository rather than older Twitter
algorithm articles:

- Repository: <https://github.com/xai-org/x-algorithm>
- Default branch: `main`
- Reviewed HEAD: [`a389166f6cf5da70a286b568c87695d4dcdce3a1`](https://github.com/xai-org/x-algorithm/commit/a389166f6cf5da70a286b568c87695d4dcdce3a1)
- Parameter source: [`home-mixer/params/param.rs`](https://github.com/xai-org/x-algorithm/blob/main/home-mixer/params/param.rs)
- Ranking source: [`home-mixer/scorers/ranking_scorer.rs`](https://github.com/xai-org/x-algorithm/blob/main/home-mixer/scorers/ranking_scorer.rs)
- Filters: [`home-mixer/filters/`](https://github.com/xai-org/x-algorithm/tree/main/home-mixer/filters)
- Visibility rules: [`visibility-filtering/rules/registry.rs`](https://github.com/xai-org/x-algorithm/blob/main/visibility-filtering/rules/registry.rs)
- `param.rs` source comment at the reviewed commit: `last sync
  2026-08-12T04:09:22Z`.

The source currently documents a weighted action-value scorer and exposes a
default `ValueModelMode` of `weighted`. The scorer also contains
`dwell_regret_sigmoid` and gated dwell-regret paths. The auditor therefore
does not claim that the weighted proxy captures every experiment or scoring
mode. A non-`weighted` parsed default is a compatibility warning, not a reason
to silently pretend the proxy is the official final score.

## 3. Architectural principles

1. **Evidence provenance first.** Every report identifies the exact algorithm
   commit or explicitly says that a cached snapshot was used.
2. **Missing is a state.** Nullable values remain nullable through ingestion,
   normalization, scoring, export, and report rendering.
3. **No online-score simulation.** Analytics action rates never enter a type or
   field named Phoenix probability or official ranking score.
4. **Account-relative scores.** Available 0–100 scores compare posts only within
   the supplied, deduplicated account dataset; insufficient exposure or field
   coverage yields unavailable rather than fake precision.
5. **Separation of concerns.** Distribution, conversion, and efficiency are not
   folded into the alignment proxy.
6. **Replaceable policy.** Alias maps, content classifiers, scoring settings,
   and presets are adapters around a generic core.
7. **Graceful source drift.** Unknown, renamed, or malformed upstream params
   create structured warnings and snapshot diffs instead of crashing an audit.
8. **Determinism.** Given the same input bytes, config, and algorithm snapshot,
   scoring and report ordering are deterministic.
9. **Source relation is explicit.** An upstream parameter being parseable does
   not prove that an Analytics column has the same semantics. Parsing,
   observation availability, and mapping confidence are separate states.
10. **Executable differentiation.** The generic Skill is a thin interface to a
    tested CLI/report core. It must not become a second, independent source of
    static algorithm claims or handcrafted draft scores.

The competitive research and release-worthiness gate are documented in
[`competitive-analysis.md`](competitive-analysis.md). In particular, the
project deliberately does not reproduce a static creator knowledge Skill or a
single-post heuristic analyzer.

## 4. System context

```text
Official GitHub source                  Local Analytics export(s)
        |                                         |
        v                                         v
Commit resolver -> source fetcher       CSV/XLSX loader -> alias mapper
        |                                         |
        v                                         v
Parameter parser -> immutable snapshot  canonical nullable rows
        |                                         |
        +-------------------+---------------------+
                            v
                  validation + deduplication
                            v
                  rates + sample stabilization
                            v
            four independent relative score families
                            v
               Phase 2 detectors and classifier
                            v
                 Markdown report + scored CSV
```

## 5. Package boundaries

```text
src/x_algorithm_auditor/
  cli.py                    orchestration and user-facing exit behavior
  algorithm/
    fetcher.py              commit resolution and commit-pinned source fetch
    parser.py               Rust param macro extraction and diagnostics
    snapshot.py             snapshot model, persistence, cache, and diff
  analytics/
    schema.py               canonical columns, nullable contracts, aliases
    loader.py               CSV/XLSX decoding and source diagnostics
    deduplicate.py          identity hierarchy and non-additive resolution
    normalize.py            numeric parsing, rates, priors, reliability
  scoring/
    common.py               percentile and coverage primitives
    alignment.py            public-weight observed proxy only
    distribution.py         impression percentile only
    conversion.py           profile-visit/follow funnel only
    efficiency.py           valuable-action efficiency only
  detection/                Phase 2 account-relative overlay detectors
  content/                  Phase 2 replaceable heuristic classifier
  recommendations/          Phase 2 evidence-backed recommendation rules
  reports/
    markdown.py             human-readable audit
    csv_export.py           stable machine-readable export
```

The exact file split may be simplified when two modules would be trivial, but
the ownership boundaries above must remain visible in code and tests.

## 6. Algorithm snapshot contract

An immutable JSON snapshot contains at least:

```text
schema_version
repository
branch
commit_sha
fetched_at_utc
parameter_source_path
parameter_sync_date
source_sha256
source_mode              live | cached
value_model_mode
extracted_signals[]      name, config key, numeric value, sign, source
parsed_params[]          all parseable params needed for change diagnostics
expected_missing[]
unsupported_params[]
unparsed_params[]
warnings[]
change_from_previous     previous commit, added, removed, changed
```

Live acquisition resolves the branch commit first and then fetches
`param.rs` by that SHA. This prevents metadata from one commit being paired
with source bytes from another. A snapshot is written only after schema and
hash validation.

If live acquisition fails, the snapshot provider may load the latest valid
local snapshot. The caller receives `source_mode=cached`, the cached commit,
and a warning. If neither live source nor a valid cache exists, the audit fails
with an actionable error; it must not inject unlabelled constants.

Change detection compares both the source SHA-256 and structured parameter
sets. A commit change with no relevant weight change is still recorded. A
weight addition, removal, rename-like missing/unknown pair, type change,
malformed value, `ValueModelMode` change, or source-path failure is surfaced.

## 7. Parameter parser contract

The parser recognizes Rust `param!(...)` macro invocations across one or many
lines and extracts the symbol, Rust type, config key, and literal default. It
does not depend on fixed line numbers.

The parser records the complete relevant param set; a separate versioned signal
registry decides which parsed params can be related to canonical Analytics
actions. The first registry includes:

- positive: `FavoriteWeight`, `ReplyWeight`, `RetweetWeight`, `QuoteWeight`,
  `ShareWeight`, `ShareViaDmWeight`, `ShareViaCopyLinkWeight`, and
  `FollowAuthorWeight`;
- negative: `NotInterestedWeight`, `BlockAuthorWeight`, `MuteAuthorWeight`, and
  `ReportWeight`.

Other current scorer weights and gates are retained as unsupported context,
not silently discarded. Nonliteral or malformed values become unparsed
records. Expected signal loss produces warnings but does not make the parser
throw unless no usable scoring signal remains.

The registry assigns one of `direct`, `conditional`, `approximate`, `outcome`,
or `unobservable` to every considered relation. Only `direct`, plus
`conditional` relations whose adapter proves the required semantics, may enter
Alignment. For example, generic shares are conditional on overlap semantics;
link clicks versus `OpenLinkWeight`, detail expands versus `ClickWeight`, and
media views versus media-specific heads remain approximate by default.

Snapshot validation also checks whether registered params are referenced by
the reviewed scorer source. A name ending in `Weight` is not sufficient proof
that the active scorer consumes it. Source fetch failure for this validation is
reported as reduced source coverage rather than silently marked verified.

## 8. Canonical analytics contract

Canonical identifiers and metadata:

```text
post_id, canonical_url, text, created_at, post_type,
source_file, source_row, export_date, date_range_start, date_range_end
```

Canonical exposure and observable action counts:

```text
impressions, engagements, likes, replies, reposts, quotes, shares,
shares_via_dm, shares_via_copy_link, bookmarks, profile_visits, follows,
link_clicks, detail_expands, media_views, not_interested, blocks, mutes,
reports
```

Counts use pandas nullable numeric dtypes (or an equivalent explicit option
type). A missing source column or blank/malformed cell is not converted to
zero. Validation diagnostics distinguish absent column, missing cell,
malformed value, invalid negative count, and rate unavailable because
impressions are zero.

Alias mapping is versioned data, not scattered conditionals. Matching is
case-insensitive after Unicode normalization, whitespace collapse, and safe
punctuation normalization. Ambiguous collisions fail with a clear request for
an explicit mapping rather than guessing.

## 9. Deduplication contract

Possible duplicate identities are matched in this order:

1. normalized `post_id`;
2. post ID extracted from a canonical X URL;
3. normalized canonical URL;
4. normalized text plus normalized timestamp;
5. a documented provenance fingerprint that keeps an insufficient-identity
   row unique rather than weakly merging it.

The last item is deliberately non-merging. A repeated short text without a
timestamp is not enough evidence that two cumulative-export rows are the same
post. Such rows remain visible with an `insufficient_identity` warning; a
future adapter may supply a stronger ID, but the generic core prefers a
possible duplicate over silent data loss.

Duplicate exports are cumulative observations, so metrics are never summed.
Within a duplicate cluster, one anchor row is chosen by completeness, newest
known export/range end, greatest nonnegative impressions, then stable input
order. Missing anchor cells may be filled from a compatible duplicate, but
conflicting observed values are recorded and not arithmetically combined.
Reports include input rows, output posts, deduplicated rows, conflict count,
and identity method counts.

## 10. Scoring boundary

The scoring subsystem consumes only a validated snapshot and a deduplicated
canonical table. It emits nullable scores and diagnostics. It must not fetch
network data, mutate input files, classify content, or write reports.

Each post emits enough evidence for reconstruction:

```text
raw rates
stabilized rates
signal weights
per-signal contributions
observable and unavailable signal lists
coverage count
sample-confidence label
raw composite values
final account-relative scores
```

Detailed formulas and thresholds live in `docs/methodology.md`; configurable
defaults live in `config/scoring.yaml` and carry a schema version.

## 11. Report contract

Markdown is the explanatory source of truth and contains the exact sections
listed in `ACCEPTANCE.md`. CSV is a stable post-level export. Both must say:

> Algorithm Alignment is an account-relative observed proxy based on public
> weights and historical Analytics rates. It is not X's official ranking
> score and does not contain Phoenix viewer-post probabilities.

Unavailable metrics render as `unavailable` in Markdown and empty/null in CSV,
never as numeric zero. Cached algorithm provenance is prominent in the
executive summary and snapshot section.

## 12. CLI and filesystem behavior

Primary command:

```bash
xalgo audit analytics.csv
xalgo audit analytics.xlsx
```

Phase 1 may add explicit options for output directory, config, alias map,
snapshot directory, offline/cache-only mode, and strict validation. Defaults
must be local and cross-platform. Existing output files are not silently
overwritten: deterministic names may receive a timestamp suffix or require an
explicit overwrite flag.

Input files are read-only. Network access is limited to public official source
acquisition. Logs contain paths and counts but not full post text by default.

## 13. Extension points

- `AnalyticsAdapter`: alternate export layouts without changing scoring.
- `ContentClassifier`: Phase 2 heuristic implementation, later replaceable.
- `Preset`: optional goals, taxonomy, keywords, and comparison baselines. The
  generic core never imports a personal preset implicitly.
- `SnapshotSource`: live GitHub, local checked-out source, or validated cache.
- `ReportRenderer`: Markdown first; other formats later.

## 14. Phase boundaries

- **Stage A:** architecture, methodology, limitations, tasks, acceptance.
- **Stage A research gate:** pinned comparison with the official repository and
  three existing creator projects, including a no-copy differentiation gate.
- **Phase 1:** source-to-report CLI loop and four score families; no detectors,
  taxonomy, recommendations, presets, or Skill implementation.
- **Phase 2:** quadrants, detectors, replaceable content taxonomy, type
  aggregates, and evidence-backed recommendations.
- **Phase 3:** generic Skill, optional preset loading, synthetic example data,
  example report, and publication-ready README.

No UI is in these phases.

## 15. Security, privacy, and publication posture

- The tool never requests X credentials or reads browser profiles.
- Analytics stays local unless the user independently moves the outputs.
- Tests and examples use synthetic identities and text.
- Reports warn that post text may be personal or sensitive.
- A public release requires a separate license decision and a secret/privacy
  scan; Stage A does not silently choose a project license.

# Competitive Analysis and Differentiation Gate

Status: Stage A research baseline  
Reviewed: 2026-08-14  
Evidence policy: repository source at pinned commits, not secondary articles

## 1. Decision

X Algorithm Auditor is worth continuing only as a reproducible historical
account-audit engine. It is not worth continuing as another static algorithm
knowledge Skill, single-post draft grader, reply analyzer, or generic creator
advice generator.

The defensible product gap is the complete, inspectable chain:

```text
commit-pinned official source
  -> dynamically parsed and diffable Algorithm Snapshot
  -> nullable batch CSV/XLSX Analytics ingestion
  -> deduplicated and small-sample-stabilized account-relative scoring
  -> four separate audit dimensions
  -> Cheap Exposure and Under-distributed Winner detection
  -> evidence-bearing Markdown and machine-readable CSV
```

If Phase 1 cannot prove the first five steps, or Phase 2 cannot prove the
detectors from calculated account-relative metrics, the project should stop
rather than ship a less rigorous version of an existing project.

## 2. Repositories reviewed

| Repository | Reviewed revision | What it is |
| --- | --- | --- |
| [`xai-org/x-algorithm`](https://github.com/xai-org/x-algorithm) | [`a389166f6cf5da70a286b568c87695d4dcdce3a1`](https://github.com/xai-org/x-algorithm/commit/a389166f6cf5da70a286b568c87695d4dcdce3a1) | Official research/source repository and authoritative public input |
| [`toby-bridges/x-algorithm-for-creators`](https://github.com/toby-bridges/x-algorithm-for-creators) | [`25ebd3872c18c3a010668986ea953043fefd8f9a`](https://github.com/toby-bridges/x-algorithm-for-creators/commit/25ebd3872c18c3a010668986ea953043fefd8f9a) | Source-cited creator knowledge Skill |
| [`JFGAtlas/tweetflare`](https://github.com/JFGAtlas/tweetflare) | [`178589d1eaee8e963b8ca4ea4b4389f1b9c165e1`](https://github.com/JFGAtlas/tweetflare/commit/178589d1eaee8e963b8ca4ea4b4389f1b9c165e1) | Single-post/reply heuristic analysis web application |
| [`attainmentlabs/x-open-source-algorithm-skill`](https://github.com/attainmentlabs/x-open-source-algorithm-skill) | [`55397c021e81006b54868d025c64b07c2582f501`](https://github.com/attainmentlabs/x-open-source-algorithm-skill/commit/55397c021e81006b54868d025c64b07c2582f501) | Static algorithm guidance and draft-optimization Skill |

The third-party repositories predate the official 2026-08-13 update. Their
current commits remain useful evidence of the problems they chose to solve,
but not an authoritative description of the latest official repository.

## 3. What existing projects already solve

### 3.1 xai-org/x-algorithm

The official repository supplies the public algorithm evidence layer:

- current parameter defaults and a source sync timestamp in
  [`home-mixer/params/param.rs`](https://github.com/xai-org/x-algorithm/blob/a389166f6cf5da70a286b568c87695d4dcdce3a1/home-mixer/params/param.rs);
- weighted and alternate value-model paths in
  [`home-mixer/scorers/ranking_scorer.rs`](https://github.com/xai-org/x-algorithm/blob/a389166f6cf5da70a286b568c87695d4dcdce3a1/home-mixer/scorers/ranking_scorer.rs);
- candidate filtering and recommendation constraints under
  [`home-mixer/filters`](https://github.com/xai-org/x-algorithm/tree/a389166f6cf5da70a286b568c87695d4dcdce3a1/home-mixer/filters);
- visibility rule composition under
  [`visibility-filtering`](https://github.com/xai-org/x-algorithm/tree/a389166f6cf5da70a286b568c87695d4dcdce3a1/visibility-filtering);
- production-oriented Phoenix model/training/serving code and SimClusters in
  the August release.

It does not ingest a creator's Analytics export, normalize an account history,
define creator-conversion metrics, or produce a creator audit report. It is a
source dependency, not a substitute for this product.

### 3.2 toby-bridges/x-algorithm-for-creators

This project already provides a careful creator-facing interpretation layer:

- progressive reference files rather than one unstructured prompt;
- citations pinned to an upstream source revision;
- a useful distinction between directly mappable fields, approximate fields,
  pipeline outputs, fields with no model item, and unobservable signals;
- privacy-conscious instructions and explicit unknowns;
- guidance for reading an Analytics export without pretending that every
  export column is a ranking input.

It is not an executable batch audit engine. It has no dynamic fetch/parser,
immutable snapshot/cache/diff contract, ingestion schema, cumulative-export
deduplication, small-sample statistics, generated scored CSV, or detector test
suite.

### 3.3 JFGAtlas/tweetflare

Tweetflare already provides a lightweight creator-facing application for one
tweet and its replies:

- FastAPI/Pydantic structure and a simple local web interaction;
- pasted or optionally scraped reply input;
- deterministic multilingual keyword and regex classification;
- audience, topic, sentiment, intent, hook, and rewrite suggestions;
- structured result cards with human-readable reasons.

Its scores are handcrafted content heuristics rather than an account-relative
Analytics audit. Missing engagement metrics default to zero, formulas use
fixed bonuses and logarithms, and labels such as reply/repost probability do
not come from Phoenix predictions. CSV/JSON comment import and multi-post
comparison are roadmap items rather than the implemented core.

### 3.4 attainmentlabs/x-open-source-algorithm-skill

This project already packages algorithm concepts into a conversational Skill:

- concise routing from a creator question to focused reference material;
- signal-by-signal rationale and draft-oriented advice;
- an accessible workflow for evaluating or rewriting a proposed post.

It is static guidance, not a data pipeline. Its draft score uses authored
weights and thresholds, several quantitative claims come from non-official or
unspecified evidence, and personal voice/profile material is mixed into the
generic workflow. It has no dynamic source validation, Analytics batch model,
missing-state contract, statistical stabilization, structured audit export,
or automated tests.

## 4. Overlap and reuse boundaries

| Capability | Toby | Tweetflare | Attainment | Auditor decision |
| --- | --- | --- | --- | --- |
| Creator-facing explanation | Strong | Strong | Strong | Required, but generated from stored evidence |
| Official-source concepts | Source-cited, static | Broad references | Mixed official and secondary claims | Pin and parse current official source |
| Observable/unobservable distinction | Strong | Weak | Weak | Reimplement as a typed source-relation registry |
| Content classification | Minimal | Deterministic heuristics | Draft patterns | Use a replaceable, unpaid heuristic classifier |
| Skill packaging | Yes | No | Yes | Add only after executable core is proven |
| Batch Analytics computation | No | No | No | Core differentiator |
| Missing versus observed zero | Discussed conceptually | Violated by defaults | Not modeled | Enforce end-to-end in types and tests |
| Small-sample protection | No calculation engine | No account cohort | No calculation engine | Core differentiator |
| Dynamic snapshot and source diff | No | No | No | Core differentiator |
| Four independent scores | No | No | No | Core differentiator |
| Cheap/under-distributed detectors | No | No | No | Core differentiator |
| Generated Markdown and scored CSV | No | No | No | Core differentiator |

Design ideas worth independently reimplementing are:

1. **Evidence-classified signal mapping.** Adopt the general idea of recording
   whether a field is direct, approximate, an outcome, or unobservable. Do not
   copy another project's prose, tables, or stale mappings.
2. **Progressive disclosure.** Keep a short generic Skill that routes to
   executable validation, snapshot, score, and report steps; place detailed
   methodology in project docs.
3. **Replaceable deterministic classification.** Preserve the useful property
   that the first classifier works locally without a paid LLM and explains the
   matched metadata/keywords.
4. **Reason-bearing output models.** Every detector and recommendation should
   expose the metrics and cohort baseline that triggered it.

Explicitly rejected reuse:

- authored or third-party action weights presented as official values;
- one-size-fits-all content-format or posting-time prescriptions;
- handcrafted values labelled as Phoenix or action probabilities;
- missing numeric fields defaulted to observed zero;
- personal voice or account conclusions in the generic core;
- scraping, login, cookies, or a UI in the initial product;
- copied Skill wording or copied scoring formulas.

## 5. What became stale after the 2026-08-13 official update

The August official update is not a minor line-number change. It changes which
facts can be asserted and which source paths must be followed.

### 5.1 Public weights are no longer categorically unavailable

Both creator Skills state or assume that current production-style action
weights and thresholds are private or withheld. The reviewed official
`param.rs` now publishes primary default values for positive and negative
actions, contextual boosts/discounts, filters, and value-model selection.

The correct 2026 statement is narrower: public source defaults are visible and
can be versioned, but experiments, runtime configuration, viewer/post Phoenix
predictions, and all production behavior are not recoverable from Analytics.

### 5.2 Old scorer paths and component diagrams are stale

References to standalone files such as an old `weighted_scorer.rs`,
`author_diversity_scorer.rs`, or `oon_scorer.rs` do not describe the reviewed
tree. The current scorer directory includes integrated ranking logic plus
author cold-start, Phoenix, value-model gate, and VMRanker components. Static
line citations anchored to the May or March trees must not be carried forward.

### 5.3 A single weighted-action story is incomplete

The current default mode is `weighted`, but the code also exposes
`dwell_regret_sigmoid` and `gated_dwell_regret` paths. New/current parameters
cover link/open actions, dwell/regret inputs, post exploration, not-dwelled
feedback, cold-start behavior, diversity, out-of-network handling, and
selection behavior. A snapshot parser must identify the active public default
and explicitly warn when the proxy does not support a selected mode.

### 5.4 Phoenix demo-era descriptions are stale

Descriptions based on an earlier demo/example Phoenix implementation, a fixed
old head count, or a simple four-component final ranker are incomplete after
the production-oriented Phoenix and SimClusters update. Candidate-level model
predictions also do not imply that final ordering is independent of cohort,
author diversity, out-of-network handling, cold start, VMRanker, filters, or
visibility rules.

### 5.5 Several creator-field mappings need qualification

- `profile_visits` belongs in Creator Conversion. A conceptual relationship to
  profile click does not justify an Alignment contribution when the reviewed
  public `ProfileClickWeight` default is zero.
- bookmarks are not a direct terminal action term in the reviewed default
  weighted scorer, but they do appear elsewhere as engagement/history or
  candidate metadata; neither "direct weighted reward" nor "absent from the
  algorithm" is an accurate blanket statement.
- `detail_expands` must not be silently equated with generic click, and
  `media_views` must not be silently equated with photo expand, video open, or
  qualified video view.
- aggregate shares must not be added to DM/copy-link shares unless the export
  schema proves those values are disjoint.
- negative sentiment in replies is not observed block, mute, report, or not
  interested feedback.

Impressions remain the observed Distribution measure, not a Phoenix action
probability. However, the reviewed author cold-start logic can also inspect
view count when deciding eligibility/boost context. Older language that calls
impressions a pure pipeline output with no possible algorithmic use is therefore
too absolute. This context still does not justify adding impressions to the
Alignment composite.

### 5.6 Static pipeline counts are stale-prone facts

May-era counts of candidate sources, pre-score filters, or weighted terms no
longer describe the reviewed tree after SimClusters, expanded filters, and new
scorer terms. The auditor should snapshot identities and changes where useful;
it must not promote a hand-maintained component count into durable creator
advice.

## 6. Required differentiation

The project must demonstrate all of the following to justify release:

### 6.1 Dynamic Algorithm Snapshot

- resolve the moving branch to a full commit before downloading source;
- fetch source bytes by commit and store their hash;
- parse current params without fixed line numbers;
- record active value-model mode and semantic mapping support;
- retain unknown/unparsed signals and compare snapshots;
- label live repository evidence versus validated cached evidence;
- never substitute bundled constants while calling them live.

### 6.2 Batch Analytics computation

- accept CSV and XLSX exports without login, scraping, or paid services;
- normalize alias headers into a nullable canonical schema;
- distinguish unavailable, malformed, observed zero, and positive values;
- reconcile cumulative duplicate exports without summing them;
- calculate account-relative rates and scores reproducibly for every post.

### 6.3 Four-dimensional account audit

- **Algorithm Alignment:** an observed, public-weighted relative proxy;
- **Distribution:** relative exposure only;
- **Creator Conversion:** profile-visit/follow asset funnel;
- **Content Efficiency:** valuable actions per unit exposure.

No dimension may be renamed as an official rank, prediction, probability, or
guarantee. Keeping the dimensions separate is itself a product capability: it
reveals exposure without account value and value creation without distribution.

### 6.4 Robust detectors

- Cheap Exposure must require high relative Distribution plus low relative
  Conversion and low relative Efficiency; it is not a high-impression list.
- Under-distributed Winner must require below-baseline Distribution plus high
  Conversion and Efficiency; it is not a low-impression curiosity list.
- both detectors must exclude unreliable low-exposure rows and disclose their
  percentile rules and triggering metrics.

### 6.5 Structured, auditable outputs

- Markdown provides an explanation and limitations for a human operator;
- CSV retains raw counts, rates, scores, flags, coverage, confidence, and
  signal availability for downstream analysis;
- every recommendation cites a calculated segment comparison, ratio, or
  percentile rather than generic advice;
- synthetic fixtures and automated tests prove unavailable-versus-zero,
  deduplication, small-sample behavior, scoring, detectors, and report output.

## 7. Anti-copy and release gate

This project may reuse public facts, independently derived interface patterns,
and general software-design ideas. It must not copy another repository's Skill
text, reference prose, arbitrary formulas, private presets, branding, examples,
or unsupported conclusions.

Release is blocked if any of these is true:

- the shipped algorithm baseline is a manually maintained static table with no
  commit-pinned refresh path;
- a report calls an Analytics-derived value an official X score or Phoenix
  probability;
- a missing export signal is used as numeric zero;
- top lists or detectors can be dominated by a `3 impressions / 1 reply` row;
- recommendations do not expose the supporting account metrics;
- the Skill can produce claims that the CLI/report engine cannot substantiate;
- the project offers no material capability beyond the three reviewed tools.

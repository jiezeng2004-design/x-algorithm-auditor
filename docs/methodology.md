# X Algorithm Auditor Methodology

Status: Stage A normative scoring specification  
Version: `methodology-v1`  
Date: 2026-08-14

## 1. What is being measured

The primary metric is named **Observed Algorithm Alignment Proxy**.

It asks:

> Relative to other posts in this supplied account history, which posts show a
> stronger structure of actually observed actions that correspond to public X
> weighted-ranking signals?

It does **not** estimate X's official score. In X's online system, Phoenix
predicts action probabilities for a particular `viewer x post` pair. An export
contains retrospective aggregate creator analytics, not those probabilities,
viewer context, candidate-set context, retrieval state, experiments, filters,
or reranker state.

The conceptual correspondence is deliberately one-way:

```text
Official weighted scorer: sum(public weight_s * P(action_s | viewer, post))

Auditor proxy:            sum(public weight_s * stabilized observed rate_s)
```

The second line is a historical, account-relative proxy. It is never passed to
code as a Phoenix probability and is never labelled an official ranking score.

The reviewed official source also includes alternative dwell-regret and gated
scoring paths. `ValueModelMode=weighted` was the parsed default at the reviewed
commit, but experiments and future defaults can differ. Snapshot metadata and
compatibility warnings make this limitation visible.

## 2. Unit of analysis and comparison cohort

The unit is one deduplicated post observation. The comparison cohort is the
deduplicated posts supplied for one account in one audit run. Scores must not be
compared across accounts as if they were on a common absolute scale.

If exports mix accounts, the loader must either split by an explicit account
identifier or fail; it must not rank multiple unknown accounts together.

The four final scores are nullable integers from 0 through 100. They are
rounded percentiles, not calibrated probabilities. A cohort with fewer than
five scoreable posts receives a prominent `very small cohort` warning.
Detectors and strong recommendations require at least eight eligible posts.

The four scores are diagnostic lenses, not four competing north-star KPIs:

- Distribution is an outcome/volume lens;
- Alignment is a public-signal proxy lens;
- Conversion is the creator-asset funnel outcome;
- Efficiency is a per-exposure quality driver/guardrail.

No universal target is set for any score. A score can change when the supplied
account cohort changes, so detector cutoffs are versioned operating rules for
prioritizing review, not external benchmarks or platform targets.

## 3. Missing is not zero

For action `s` on post `j`, retain three distinct states:

1. **Observed positive:** source supplied a valid count greater than zero.
2. **Observed zero:** source supplied a valid numeric zero.
3. **Unavailable:** column absent, cell blank, cell malformed, or the rate has
   no valid denominator.

Only state 2 has numeric value `0`.

If `impressions_j = 0`, exposure is an observed zero for Distribution, but all
per-impression action rates on that row are unavailable because division by
zero is undefined. A negative count is invalid and becomes unavailable with a
validation warning; it is not clipped to zero.

Aggregate `engagements` never fills missing likes, replies, reposts, or other
specific signals. Missing negative-feedback columns such as reports and mutes
remain unavailable and do not contribute a zero penalty.

Markdown prints `unavailable`; CSV emits an empty value. Both include explicit
Observable Signals and Unobservable Signals sections or columns.

## 4. Numeric parsing

The loader accepts ordinary numbers, thousands separators, surrounding
whitespace, and percentage strings where the target field is documented as a
rate. It rejects silent guesses about locale-ambiguous text.

If an export supplies a percentage rather than a count, the adapter preserves
its semantic type. It may derive a count only when the denominator and rounding
rule are explicit; otherwise the rate remains an observed rate and no fake
count is created.

Malformed timestamps remain missing with diagnostics. They may reduce identity
quality and date-range analysis but do not erase otherwise usable metrics.

## 5. Deduplication before statistics

All identity resolution happens before baselines, rates, percentiles, or
content-type summaries. Duplicate cumulative exports are not added together.

Identity precedence:

```text
post_id -> ID from canonical URL -> canonical URL -> normalized text + timestamp
        -> unique insufficient-identity provenance fingerprint
```

The final fingerprint is diagnostic and row-preserving, not an automatic
cross-row merge key. Text without a timestamp, or an entirely blank identity,
cannot safely prove duplication. The report counts these rows so users can
repair the export or provide an explicit adapter without losing observations.

For a duplicate cluster, select an anchor using this deterministic order:

1. most observed canonical fields;
2. latest explicit export date or date-range end;
3. largest valid impressions count;
4. later stable source row.

Fill only missing anchor cells from a compatible duplicate. Never sum and never
take the independent maximum of every metric, because doing so can synthesize a
row that never existed. Record conflicting observed values and the number of
removed duplicate rows.

## 6. Raw rates

For a valid action count `y_sj` and positive impressions `n_j`:

```text
raw_rate_sj = y_sj / n_j
```

Derived display metrics include:

```text
like_rate, reply_rate, repost_rate, quote_rate, share_rate,
bookmark_rate, profile_visit_rate, follow_rate, engagement_rate,
follows_per_1k_impressions = 1000 * follow_rate
```

Observed counts greater than impressions are retained only when the metric can
legitimately contain repeat actions; otherwise they are flagged. The first
version avoids universal clipping at 100% because different export definitions
may count repeated actions.

## 7. Transparent small-sample stabilization

Raw rates are shown, but score inputs use empirical shrinkage toward the
account's own observed baseline.

For signal `s`, estimate the account baseline over valid rows where that signal
is observed:

```text
p_s = sum_j(y_sj) / sum_j(n_j)
```

Define one audit-level prior exposure strength:

```text
k = clip(median(positive impressions), 50, 500)
```

If fewer than five posts have positive impressions, use `k=100` and mark the
cohort very small. Then:

```text
reliability_j      = n_j / (n_j + k)
stabilized_rate_sj = (y_sj + k * p_s) / (n_j + k)
                   = reliability_j * raw_rate_sj
                     + (1 - reliability_j) * p_s
```

This is a transparent weighted average, not a claim of a full Bayesian model.
A `3 impressions / 1 reply` post receives very little reliability and is pulled
strongly toward the account reply baseline.

Define the minimum exposure for top lists and detectors as:

```text
eligibility_floor = clip(P25(positive impressions), 20, 100)
```

Confidence labels:

```text
unavailable   n is missing or n <= 0
low           0 < n < eligibility_floor
medium        eligibility_floor <= n < 4 * eligibility_floor
high          n >= 4 * eligibility_floor
```

Low-confidence rows retain raw rates, stabilized rates, reliability, coverage,
and Distribution, but their rate-derived final Alignment, Conversion, and
Efficiency scores are `unavailable`. They therefore cannot receive a 100th
percentile merely because a tiny stabilized value is still the largest value
in a sparse cohort. They also cannot enter quadrants, top-winner sections,
detectors, or strong recommendations. This score-eligibility rule is the second
guard against tiny denominators.

For a signal with at least 20 score-eligible stabilized observations, values
used in composites are winsorized to that eligible distribution's P5 and P95.
With fewer observations, no winsorization is applied and the small-cohort
warning remains. Raw and stabilized values are always preserved for
explanation.

## 8. Percentile normalization

For a nonmissing composite `x_j` belonging to the score-eligible cohort, use
average ranks for ties:

```text
percentile_j = 100 * (average_rank_j - 1) / (N - 1),  when N > 1
percentile_j = 50,                                      when N = 1
```

Here `N` is the number of eligible posts for that metric, not all input rows.
An ineligible row has an unavailable final rate-derived score; no provisional
percentile is exported under the final score name. Distribution is the one
exception because impressions themselves, rather than a rate denominator,
are the metric being ranked.

Round only the final displayed score to the nearest integer. Intermediate
calculations retain full precision. A percentile states relative position in
this audit cohort; it is not confidence, probability, or an absolute quality
grade.

## 9. Algorithm Alignment Proxy

### 9.1 Source relation and observation state

Two independent axes are retained:

1. **source relation** — whether an Analytics concept is semantically suitable
   for a public scorer parameter; and
2. **observation state** — whether this particular export/post contains an
   observed positive value, observed zero, or unavailable value.

The source-relation values are:

| Relation | Meaning | Alignment use |
| --- | --- | --- |
| `direct` | canonical action and scorer action have sufficiently matched semantics | eligible |
| `conditional` | eligible only when an adapter proves required field/overlap semantics | adapter-controlled |
| `approximate` | related behavior but definitions are not demonstrably identical | excluded; context only |
| `outcome` | pipeline result rather than an action head | excluded |
| `unobservable` | scorer action exists but typical Analytics cannot expose it | excluded unless an exact future adapter observes it |

This classification is versioned with the snapshot/parser contract. It is not
inferred from similar-looking names.

A registered parameter explicitly absent from the commit-pinned ranking source
is excluded from Alignment even if it still parses from `param.rs`. If ranking
source verification is unavailable, the report and row reason state
`unverified`; the proxy may still be calculated from public params, but is not
described as active-scorer verified.

A mapped signal is `dataset-observable` for scoring only when it is validly
observed (including observed zero) in at least 80% of exposure-eligible rows.
Signals below that threshold remain visible in coverage/quality diagnostics
but do not define a cross-post Alignment distribution. This prevents a sparse
column from changing the meaning of the composite for only a few rows.

### 9.2 Supported default mappings

The generic registry maps canonical observed actions to parsed public params:

| Canonical action | Public param | Default relation |
| --- | --- | --- |
| likes | `FavoriteWeight` | direct |
| replies | `ReplyWeight` | direct |
| reposts | `RetweetWeight` | direct |
| quotes | `QuoteWeight` | direct |
| shares | `ShareWeight` | conditional: aggregate/channel overlap |
| shares_via_dm | `ShareViaDmWeight` | direct when explicitly exported |
| shares_via_copy_link | `ShareViaCopyLinkWeight` | direct when explicitly exported |
| follows | `FollowAuthorWeight` | direct when post-attributed |
| not_interested | `NotInterestedWeight` | direct when explicitly exported |
| blocks | `BlockAuthorWeight` | direct when explicitly exported |
| mutes | `MuteAuthorWeight` | direct when explicitly exported |
| reports | `ReportWeight` | direct when explicitly exported |

Weights are read from the selected snapshot, not copied from this document.
Bookmarks, aggregate engagements, profile visits, and media views are not
substituted for public action heads that mean something else. `link_clicks` is
kept in Efficiency: it is only an approximate relation to `OpenLinkWeight`
without an export-adapter guarantee. `detail_expands` is not assumed to equal
`ClickWeight`. `profile_visits` remains a conversion outcome even though a
profile-click scorer param exists; its reviewed public default is zero and the
export attribution is not guaranteed to be identical.

An export's generic `shares` field is treated as the generic share signal. If
an adapter supplies both aggregate and channel-specific share counts, it must
declare whether they overlap. The default is to avoid double-counting by using
the aggregate signal alone unless disjoint semantics are proven.

### 9.3 Per-post composite

Let `D` be the dataset-observable, direct or adapter-proven conditional signals
with parsed nonzero weights. Let `O_j` be the subset of `D` with an observed
action value for post `j` and a positive impression denominator. A public
zero-weight param remains visible in snapshot/context but contributes neither
value nor coverage denominator.

```text
contribution_sj = public_weight_s * stabilized_rate_sj

alignment_raw_j = sum(contribution_sj for s in O_j)

alignment_coverage_adjusted_j =
    alignment_raw_j / sum(abs(public_weight_s) for s in O_j)

alignment_coverage_j =
    sum(abs(public_weight_s) for s in O_j)
    / sum(abs(public_weight_s) for s in D)
```

The absolute-weight denominator makes rows with different legitimate coverage
less likely to look weak merely because a column is unavailable. It does not
turn missing values into zero. The report shows both the numerator and coverage.

For an exposure-eligible row, the score is the midrank percentile of the
coverage-adjusted composite among eligible rows after the stated
stabilization/winsorization policy. An exposure-ineligible row has no final
Alignment score.

A final Alignment score requires at least two used mapped signals and weighted
coverage of at least 0.50. Lower coverage is reported as `insufficient
coverage` and the final score is unavailable; it is never silently compared
with a materially different one-signal composite.

### 9.4 Explainability

Each post can render:

| Signal | Relation | Observed rate | Stabilized rate | Scoring rate | Public weight | Contribution | State |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |

`Scoring rate` is the actual stabilized value after any eligible-only
winsorization, so `Contribution = Public weight x Scoring rate` remains directly
reconstructable. Raw, stabilized, and scoring-rate columns are preserved in
the structured export.

The report also shows `Signals available: used / snapshot-supported` and lists
unavailable signals. Contributions are components of this proxy only.

## 10. Distribution Score

Distribution measures observed exposure, not content quality:

```text
distribution_score_j = percentile(impressions_j)
```

No fixed global impression threshold is used. Zero impressions can validly map
to the bottom of the cohort. Distribution is kept separate because a platform
can expose a post widely even when it converts or engages poorly.

## 11. Creator Conversion Score

Conversion measures whether exposure became account-level intent or assets.
Default components are deliberately narrow:

```text
follow_component  = percentile(stabilized follow_rate)         weight 0.60
profile_component = percentile(stabilized profile_visit_rate)  weight 0.40
```

These component weights are auditor methodology policy, not X public weights.
Components validly observed in at least 80% of eligible rows define the
dataset-level Conversion component set. Available weights are renormalized per
row, but a row requires at least 0.50 of that set's original weight coverage.
The composite and its percentile use only exposure-eligible, adequately
covered rows. Otherwise Conversion is unavailable.
`follows_per_1k_impressions` is shown as an interpretable rescaling of follow
rate, not counted as a second component.

Likes do not enter Creator Conversion. High-intent content actions are handled
by Content Efficiency so the funnel remains interpretable.

Alignment and Conversion must coexist because they answer different questions:

- Alignment: did observed action structure resemble publicly rewarded signals?
- Conversion: did the exposure create profile interest or follows for this
  creator?

A post can be high on one and low on the other; collapsing them would hide the
central distinction between traffic and account value.

## 12. Content Efficiency Score

Efficiency asks how much valuable observed behavior occurred per impression,
independently of total distribution. Each available stabilized rate is first
converted to an account-relative percentile. The default component weights are:

| Component | Weight |
| --- | ---: |
| replies | 0.20 |
| quotes | 0.15 |
| reposts | 0.15 |
| shares | 0.15 |
| bookmarks | 0.15 |
| link clicks | 0.10 |
| detail expands | 0.05 |
| likes | 0.05 |

Available weights are renormalized. Likes can therefore never dominate the
default efficiency composite. Profile visits and follows stay in Conversion;
impressions stay in Distribution. Media views are reported diagnostically but
are excluded by default because their meaning depends heavily on media format.

These component weights are also versioned auditor policy, not official X
weights. Components validly observed in at least 80% of eligible rows define
the dataset-level Efficiency component set. A row must retain at least 0.50 of
that set's original weight coverage after missing values; otherwise its final
Efficiency score is unavailable.

If none of the specific components exists but aggregate engagements is
observed, `engagement_rate` may produce a low-specificity fallback score with a
prominent warning. It is never combined with its child metrics, which would
double-count them.

For exposure-eligible rows, the weighted component-percentile composite is
itself midranked across eligible rows to produce the final 0–100 Efficiency
score. Ineligible rows retain component diagnostics but no final score.

## 13. Quadrants and badges

The exhaustive two-axis quadrant uses the cohort median (score 50) on Alignment
and Creator Conversion:

| Quadrant | Alignment | Conversion | Interpretation |
| --- | --- | --- | --- |
| A — Core Winner zone | >= 50 | >= 50 | aligned and asset-producing |
| B — Traffic Without Asset | >= 50 | < 50 | aligned actions without account conversion |
| C — Conversion-led candidate | < 50 | >= 50 | account value despite weaker alignment proxy |
| D — Low Priority | < 50 | < 50 | weak on both observed axes |

Missing either axis yields `insufficient_data`, not Quadrant D.

The quadrant is descriptive; stronger badges use P75/P25-style detector rules.
A `Core Winner` badge requires Alignment >= 75, Conversion >= 75, eligible
exposure, and adequate signal coverage.

The phrase **Under-distributed Winner** is reserved for the overlay detector
below, not automatically applied to every Quadrant C post. This keeps a true
two-axis quadrant mathematically distinct from a three-metric detector.

## 14. Cheap Exposure detector

Cheap Exposure is not a high-impressions detector. It requires all of:

```text
distribution_score >= 75
conversion_score   <= 25
efficiency_score   <= 25
sample confidence is medium or high
conversion and efficiency are both observed
eligible detector cohort has at least 8 posts
```

Thus high exposure plus good conversion or good efficiency is never labelled
cheap. The thresholds are account-relative percentiles; no absolute impression
number is embedded. They are a versioned triage policy, not an X threshold or
universal performance target.

## 15. Under-distributed Winner detector

The overlay requires:

```text
distribution_score <= 40
conversion_score   >= 75
efficiency_score   >= 75
sample confidence is medium or high
required metrics are observed
eligible detector cohort has at least 8 posts
```

This explicitly detects below-baseline exposure plus strong asset conversion
and per-exposure value. Flagged posts enter the Repackage Queue. The report
suggests testing packaging changes; it does not claim why distribution was low.
These thresholds are a versioned triage policy, not a prediction of deserved
impressions.

## 16. Content type analysis

Phase 2 uses a replaceable, deterministic heuristic classifier. Metadata wins
over text guesses for Reply, Quote, and Thread. Remaining initial labels are:

```text
Tool Hands-on, AI News, Tutorial, Comparison, Builder / Project,
Social, Reply, Quote, Thread, Other
```

Rules are ordered, versioned, and report classifier confidence/reason. A preset
may add user-specific taxonomy and keywords, but the generic core never embeds
private conclusions.

For each type, report eligible sample count, median impressions, median four
scores, median profile-visit rate, median follows per 1k, and Cheap Exposure
ratio. Types with fewer than three eligible posts are `insufficient sample` and
cannot drive a strong recommendation.

## 17. Recommendation evidence rules

Recommendations must cite observed metrics, comparison baseline, sample count,
and uncertainty. Templates may express, for example:

```text
Comparison (n=7 eligible) has median follows/1k 2.3x the account median;
test one additional Comparison post in the next cycle.
```

Default guards:

- no causal wording from observational data;
- no strong type recommendation for fewer than three eligible posts;
- no ratio when the denominator baseline is zero; use an absolute difference;
- no recommendation based only on a low-confidence post;
- no shadowban, guaranteed growth, or guaranteed recommendation language;
- if evidence is insufficient, say so instead of emitting generic advice.

## 18. Algorithm mechanisms kept as context only

The following current mechanisms affect eligibility, score adjustment,
retrieval, or ordering but are not quantitatively inserted into the proxy when
Analytics cannot observe their per-viewer inputs:

- author diversity decay;
- out-of-network handling and reply/repost deboosting;
- new-author cold-start boost;
- Thunder, Phoenix retrieval, and SimClusters candidate sourcing;
- age, duplicate, self-post, previously-seen, previously-served, muted keyword,
  social graph, subscription, topic, inventory, and other filters;
- visibility filtering and its viewer/account/post-label policies;
- VMRanker diversity reranking;
- experiment assignment and runtime overrides;
- dwell-regret/gated mode inputs not present in Analytics.

They appear in Algorithm Context and Limitations, not as invented numeric
features.

## 19. Lead self-check before Phase 1 delegation

Checked against `methodology-v1` on 2026-08-14:

1. **Q1 — Is Alignment explicitly a proxy?** PASS. Its normative name is
   Observed Algorithm Alignment Proxy; final UI shorthand must retain a nearby
   proxy disclaimer.
2. **Q2 — Are Analytics rates treated as Phoenix probabilities?** PASS. The
   types, formula, and report contract explicitly separate them.
3. **Q3 — Is unavailable converted to zero?** PASS. Unavailable remains nullable
   end-to-end; only a supplied numeric zero is zero.
4. **Q4 — Can 3 impressions / 1 reply become Top 1?** PASS. Shrinkage reduces
   the rate and, more importantly, the exposure floor makes all rate-derived
   final scores unavailable. It cannot enter a ranking, winner list, quadrant,
   detector, or strong recommendation.
5. **Q5 — Why both Alignment and Conversion?** PASS. One measures public-signal
   action structure; the other measures creator asset formation.
6. **Q6 — Is Cheap Exposure only high impressions?** PASS. It additionally
   requires bottom-quartile Conversion and Efficiency with adequate evidence.
7. **Q7 — Can Under-distributed Winner find low exposure plus high efficiency?**
   PASS. Its explicit rule combines below-baseline Distribution with top-quartile
   Conversion and Efficiency.
8. **Q8 — Can core conclusions explain each score?** PASS. Raw/stabilized rates,
   weights, contributions, coverage, composite, percentile, and flags are
   retained.
9. **Q9 — Can a future `param.rs` change be detected?** PASS. Commit-pinned
   snapshots, source hashes, structured diffs, missing/unknown params, and mode
   warnings are required.
10. **Q10 — Does any normative output imply an official X score?** PASS. Such
    wording is prohibited in architecture, report contract, acceptance, README,
    Skill, and tests.

All ten checks pass. Phase 1 may be delegated against this specification.

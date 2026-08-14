# X Algorithm Auditor Audit

> Algorithm Alignment is an account-relative observed proxy based on public weights and historical Analytics rates. It is not X's official ranking score and does not contain Phoenix viewer-post probabilities.

## 1. Executive Summary

- Algorithm source: **cached**
- Snapshot commit: `a389166f6cf5da70a286b568c87695d4dcdce3a1`
- Deduplicated posts analyzed: **15**
- Warning: this run used a validated cached public-source snapshot, not a live fetch.
- Detector cohort: 10 observed eligible posts (minimum 8)
- Optional preset: none (generic core only).

## 2. Data Coverage

- Input rows: 16
- Output posts: 15
- Deduplicated rows: 1
- Duplicate conflicts retained as diagnostics: 2
- Rows with insufficient stable identity preserved without weak-identity merging: 0
- Shrinkage k: 165.0000
- Eligibility floor: 70.0000 impressions
- Low-confidence posts retain diagnostics but have unavailable Alignment, Conversion, and Efficiency final scores.
- Warning: Account overview and per-post analytics may use different coverage or attribution semantics and must not be automatically summed or merged.

### Validation diagnostics

| Data quality state | Count |
| --- | --- |
| Absent source columns | 10 |
| Missing source cells | 1 |
| Malformed values | 0 |
| Negative count values | 0 |
| Rates unavailable: zero impressions | 1 |
| Rates unavailable: missing/invalid impressions | 0 |

- `absent_column:blocks`: 1
- `absent_column:canonical_url`: 1
- `absent_column:engagements`: 1
- `absent_column:export_date`: 1
- `absent_column:media_views`: 1
- `absent_column:mutes`: 1
- `absent_column:not_interested`: 1
- `absent_column:reports`: 1
- `absent_column:shares_via_copy_link`: 1
- `absent_column:shares_via_dm`: 1
- `missing_cell:bookmarks`: 1
- `multiple_date_ranges`: 1
- `rate_unavailable:zero_impressions`: 1
- Date range observations: 2026-04-01T00:00:00Z..2026-04-15T00:00:00Z; 2026-04-16T00:00:00Z..2026-04-30T00:00:00Z

### Score sample

| post_id | impressions | Alignment | Distribution | Conversion | Efficiency |
| --- | --- | --- | --- | --- | --- |
| cheap-exposure | 1200.0000 | 0 | 100 | 0 | 0 |
| social-1 | 1000.0000 | 11 | 93 | 11 | 11 |
| project-1 | 800.0000 | 22 | 86 | 22 | 22 |
| reply-1 | 500.0000 | 33 | 79 | 33 | 33 |
| comparison-1 | 300.0000 | 44 | 71 | 44 | 44 |
| news-2 | 220.0000 | 56 | 64 | 56 | 56 |
| news-1 | 180.0000 | 67 | 57 | 67 | 67 |
| tool-3 | 150.0000 | 78 | 50 | 78 | 78 |
| tool-2 | 120.0000 | 89 | 43 | 89 | 89 |
| under-winner | 100.0000 | 100 | 36 | 100 | 100 |

## 3. Algorithm Snapshot

- Repository: `xai-org/x-algorithm`
- Branch resolved: `main`
- Commit: `a389166f6cf5da70a286b568c87695d4dcdce3a1`
- Source mode: **cached**
- Fetched at (UTC): `2026-08-14T01:11:07Z`
- Parameter source: `home-mixer/params/param.rs`
- Parameter sync date: `2026-08-12T04:09:22Z`
- Parameter source SHA-256: `35ee4d84410e688abe162cb4b64f8ad0733136348460c2073c571e18f311a17c`
- ValueModelMode: `weighted`
- Active scorer coverage: `1.0000`

### Snapshot warnings

- unregistered weight parameters retained as context: ContActiveSecs5mResidualNormWeight, ContClickDwellTimeWeight, ContDwellTimeWeight, DwellWeight, NotDwelledWeight, PostUnexploredWeight, QuotedClickWeight, QuotedVqvWeight, VideoOpenWeight, VqvWeight
- Algorithm source: cached (offline/cache-only mode requested); snapshot commit: a389166f6cf5da70a286b568c87695d4dcdce3a1

## 4. Observable Signals

| Analytics field | Public param | Relation | Weight | Active source |
| --- | --- | --- | --- | --- |
| likes | FavoriteWeight | direct | 0.5000 | True |
| replies | ReplyWeight | direct | 5.0000 | True |
| reposts | RetweetWeight | direct | 1.0000 | True |
| quotes | QuoteWeight | direct | 5.0000 | True |
| shares | ShareWeight | conditional | 2.0000 | True |
| follows | FollowAuthorWeight | direct | 4.0000 | True |

## 5. Unobservable Signals

| Analytics concept | Public parameter | Why excluded from Alignment |
| --- | --- | --- |
| link_clicks | OpenLinkWeight | Export link clicks are not automatically OpenLink scorer actions. |
| detail_expands | ClickWeight | Detail expands are not assumed to be generic clicks. |
| media_views | PhotoExpandWeight | Media views do not prove photo/video head semantics. |
| profile_visits | ProfileClickWeight | Profile visits remain a creator-conversion outcome. |
| bookmarks | none — contextual only | No direct terminal weighted parameter is present in the reviewed default path; bookmarks are contextual only. |

Additional run-specific exclusions:
- `ShareViaDmWeight`: dataset-observable coverage 0.000 below threshold
- `ShareViaCopyLinkWeight`: dataset-observable coverage 0.000 below threshold
- `NotInterestedWeight`: dataset-observable coverage 0.000 below threshold
- `BlockAuthorWeight`: dataset-observable coverage 0.000 below threshold
- `MuteAuthorWeight`: dataset-observable coverage 0.000 below threshold
- `ReportWeight`: dataset-observable coverage 0.000 below threshold
- `OpenLinkWeight`: approximate relation
- `ClickWeight`: approximate relation
- `PhotoExpandWeight`: approximate relation
- `ProfileClickWeight`: outcome relation
- `bookmarks (no direct parameter)`: unobservable relation; contextual only

## 6. Core Winners

Core Winner is a stricter badge than Quadrant A: Alignment and Conversion must both be at least 75 with score-eligible exposure and adequate Alignment coverage.

| post_id | impressions | Alignment | Distribution | Conversion | Efficiency |
| --- | --- | --- | --- | --- | --- |
| tool-3 | 150.0000 | 78 | 50 | 78 | 78 |
| tool-2 | 120.0000 | 89 | 43 | 89 | 89 |
| under-winner | 100.0000 | 100 | 36 | 100 | 100 |

## 7. Cheap Exposure

Flag requires account-relative Distribution >= 75 plus Conversion <= 25 and Efficiency <= 25; it is not an impressions-only label.

| post_id | Distribution | Conversion | Efficiency | Trigger reason |
| --- | --- | --- | --- | --- |
| cheap-exposure | 100 | 0 | 0 | qualified conjunctive cheap exposure rule |
| social-1 | 93 | 11 | 11 | qualified conjunctive cheap exposure rule |
| project-1 | 86 | 22 | 22 | qualified conjunctive cheap exposure rule |

## 8. Under-distributed Winners

Flag requires Distribution <= 40 plus Conversion >= 75 and Efficiency >= 75; it is a descriptive repackage-review priority, not a claim about why distribution was lower.

| post_id | Distribution | Conversion | Efficiency | Trigger reason |
| --- | --- | --- | --- | --- |
| under-winner | 36 | 100 | 100 | qualified conjunctive under-distributed winner rule |

### Repackage Queue

| post_id | impressions | Alignment | Distribution | Conversion | Efficiency |
| --- | --- | --- | --- | --- | --- |
| under-winner | 100.0000 | 100 | 36 | 100 | 100 |

## 9. Traffic Without Asset

This is the descriptive Quadrant B zone (Alignment >= 50, Conversion < 50), distinct from the stricter Cheap Exposure detector.

No score-eligible post fell in Quadrant B.

## 10. Content Type Analysis

**Experimental.** Current content classification is heuristic and should be treated as descriptive rather than authoritative.

Classifier: deterministic local heuristic (`content-taxonomy-v1`). Metadata Reply/Quote/Thread labels take precedence over text rules.
Types with fewer than 3 eligible posts are explicitly insufficient samples and cannot drive type recommendations.

| Content type | Posts | Eligible | Evidence | Median impressions | Median Alignment | Median Distribution | Median Conversion | Median Efficiency | Median profile visit rate | Median follows/1k | Cheap Exposure ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tool Hands-on | 4 | 4 | sufficient | 135.0000 | 83.5000 | 46.5000 | 83.5000 | 83.5000 | 0.0075 | 7.5000 | 0.0000 |
| AI News | 3 | 3 | sufficient | 220.0000 | 56.0000 | 64.0000 | 56.0000 | 56.0000 | 0.0045 | 4.5455 | 0.3333 |
| Builder / Project | 1 | 1 | insufficient sample | 800.0000 | 22.0000 | 86.0000 | 22.0000 | 22.0000 | 0.0013 | 1.2500 | 1.0000 |
| Reply | 1 | 1 | insufficient sample | 500.0000 | 33.0000 | 79.0000 | 33.0000 | 33.0000 | 0.0020 | 2.0000 | 0.0000 |
| Social | 1 | 1 | insufficient sample | 1000.0000 | 11.0000 | 93.0000 | 11.0000 | 11.0000 | 0.0010 | 1.0000 | 1.0000 |
| Other | 5 | 0 | insufficient sample | 20.0000 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |

## 11. Operating Recommendations

Every recommendation below is traceable to retained audit metrics and is observational, not causal.

| Recommendation | Supporting metric | Observed value | Baseline | Eligible n | Comparison | Uncertainty |
| --- | --- | --- | --- | --- | --- | --- |
| Repackage Queue: under-winner | Distribution / Conversion / Efficiency detector metrics | Distribution=36; Conversion=100; Efficiency=100 | Under-distributed Winner policy: Distribution <= 40, Conversion >= 75, Efficiency >= 75 | 10 | policy_threshold: qualified | Account-relative observational detector; it does not infer a distribution cause or predict a repackage outcome. |
| Tool Hands-on: account-asset test candidate | median follows per 1k impressions | 7.5000 | account eligible median 3.9394 | 4 | ratio: 1.90x | Eligible-sample descriptive comparison only; content type does not prove the observed conversion difference caused follows. |
| AI News: traffic-without-asset review candidate | Cheap Exposure ratio among eligible posts | 0.3333 | account eligible ratio 0.3000 | 3 | ratio: 1.11x | The detector is account-relative and descriptive; it does not identify a causal conversion mechanism. |

## 12. Methodology Notes

- Rates are action counts divided by positive impressions; zero impressions makes rates unavailable.
- Stabilized rates use the account baseline and the report's shrinkage k before rate-derived scoring.
- Per-signal Alignment contributions use the exported scoring rate (the stabilized rate after conditional eligible-only winsorization), multiplied by the public parameter weight.
- All displayed 0–100 scores are account-relative average-rank percentiles, not probabilities or cross-account benchmarks.
- Conversion/Efficiency component weights are versioned auditor policy, not X parameters.
- Quadrant cutoffs, badges, and detector thresholds are versioned account-relative auditor policy, not X thresholds or predictions.
- Missing values render as `unavailable`; an observed numeric zero remains zero.

## 13. Limitations

- Public repository defaults may differ from experiments or runtime production configuration.
- Aggregate Analytics cannot reveal viewer-post Phoenix predictions, candidate context, filters, or reranking state.
- This report cannot detect shadowbans, visibility enforcement, or guarantee distribution or growth.
- Duplicate reconciliation avoids cumulative summing but cannot recover undocumented export-window semantics.
- Rows without a stable ID, canonical URL, or text-plus-timestamp are preserved rather than weakly merged; they may remain duplicated across exports.

# X Algorithm Auditor Limitations

Status: Current implementation limitations and normative boundaries  
Date: 2026-08-14

## 1. Not an official X score

Algorithm Alignment is an account-relative observed proxy. It is not X's
official ranking score, does not recover Phoenix probabilities, and cannot
reproduce the ranking of a particular viewer's For You feed.

The official scorer uses per-viewer, per-post model outputs plus request,
candidate, experiment, adjustment, filtering, and reranking context that an
Analytics export does not contain.

## 2. Public source is incomplete and time-sensitive

The public repository is authoritative only for what it publishes at a given
commit. X states that some rules and deployment-related code are not included,
and experiments or runtime configuration can differ from checked-in defaults.

The reviewed source contains weighted, dwell-regret, and gated scoring paths.
The auditor's first proxy uses public weighted action params because they map
most transparently to historical observations; it does not simulate alternative
paths.

Cached snapshots can be stale. Reports must state `cached` and the exact commit.
A live fetch proves only that the public source was fetched, not that those
defaults governed every production request.

The August 13, 2026 source update makes older creator guides materially stale:
public default weights are now visible, scorer paths and available modes have
changed, and the Phoenix/visibility surface is broader. The auditor therefore
does not embed conclusions from a guide merely because it once cited the
official repository; every run is tied to a snapshot and parser support level.

## 2.1 Similar names do not prove equivalent metrics

An Analytics label can resemble a scorer action without sharing its exact
definition or attribution. Link clicks/open link, detail expands/click, media
views/media-specific heads, and profile visits/profile click are examples that
require qualification. Approximate relations stay out of Alignment by default.

## 3. Analytics is aggregate and retrospective

Creator Analytics aggregates many viewers, contexts, surfaces, and time points.
It cannot reveal which viewers were candidates, which source retrieved a post,
what each viewer was predicted to do, or which filters affected eligibility.

Action attribution and metric definitions may change between export formats.
Follows and profile visits may not be perfectly attributable to one post.
Multiple exports may contain cumulative or differently windowed observations.
Deduplication reduces double counting but cannot reconstruct unknown export
semantics.

Account overview and per-post analytics may use different coverage or
attribution semantics and must not be automatically summed or merged. The
current CLI audits per-post exports and does not implement an overview
reconciliation engine.

## 4. Missing negative feedback is not evidence of absence

Typical exports do not expose not-interested, mute, block, or report actions.
Those penalties are unavailable, not zero. Consequently, Alignment often
describes the observable positive part of the public signal structure and can
miss meaningful negative feedback.

## 5. Relative scores are cohort-dependent

A score of 90 means the post ranked near the top of the supplied account cohort
under that metric. It does not mean 90% quality, 90% recommendation likelihood,
or superiority to posts from another account.

Changing the date range, removing posts, adding new posts, changing field
coverage, or resolving duplicates can change every percentile. Very small or
homogeneous cohorts have many ties and low resolution.

## 6. Stabilization reduces but does not remove uncertainty

Empirical shrinkage, exposure eligibility, winsorization, and confidence labels
protect against obvious tiny-denominator outliers. They do not produce formal
causal confidence intervals, and they cannot correct selection bias or missing
data that are not random.

Low-confidence posts can be inspected but are excluded from strong labels and
recommendations. A high-confidence label refers to exposure volume only, not
truth of causal interpretation.

## 7. Detectors are operational heuristics

Cheap Exposure and Under-distributed Winner are account-relative heuristic
overlays. They identify useful review candidates; they do not diagnose why a
post was distributed or prove that repackaging will improve results.

When Conversion or Efficiency is unavailable, the corresponding detector stays
unavailable instead of guessing.

## 8. Content classification is experimental and heuristic

Phase 2 classification uses metadata, regex, and keywords without a paid LLM.
Short, multilingual, ironic, or mixed-purpose posts may be misclassified.
Classifier reason and version are reported, and users can override taxonomy via
an optional preset without changing the generic scoring core.
Current content classification is heuristic and should be treated as
descriptive rather than authoritative.

## 9. Recommendations are observational

Recommendations summarize differences in the supplied history. They are not
causal experiments and may reflect timing, audience mix, topic, format, or
external events. The tool does not promise impressions, recommendations,
followers, revenue, or growth.

## 10. No visibility or enforcement diagnosis

The tool cannot detect shadowbans, infer hidden labels, bypass Visibility
Filtering, or determine enforcement state from low impressions. Public
visibility rules are included only as algorithm context unless the user
separately supplies authoritative transparency data in a future feature.

## 11. Input quality limits output quality

Malformed numbers, missing timestamps, ambiguous aliases, mixed accounts,
unknown date windows, and inconsistent duplicate rows reduce confidence.
Validation diagnostics are part of the result and must not be removed merely to
make the report look cleaner.

## 12. Privacy and local handling

Reports can contain post text and account performance data. The tool is local
and performs no upload, but users remain responsible for storage, sharing, and
redaction. Examples and tests must use synthetic content.

## 13. Current scope and deferred work

The current local CLI includes deterministic content taxonomy, account-relative
quadrants/detectors, evidence-backed recommendations, and an optional preset.
The preset is intentionally narrow: it can add classifier keywords and report
context, while historical baselines remain comparison priors. It cannot change
snapshot provenance, Missing != Zero, scoring policy, exposure gates, detector
rules, or current-data conclusions.

Still deferred are a UI or hosted service, X API/OAuth, browser automation,
scraping, paid or hosted LLM classification, cross-account benchmarking,
production deployment, and X Under the Hood transparency-data integration.
The project is ready for a first private export audit only as a local,
inspectable workflow; it is not a claim that every Analytics layout or future
X algorithm version is supported.

It also does not provide reply scraping, single-draft virality probabilities,
fixed writing scores, posting-time prescriptions, format rankings, or personal
voice profiles. Those features would not establish the audit evidence this
project is designed to preserve.

# Product decisions

## Movie quiz interface

The quiz is exclusively a sequence of this-or-that questions. After the
declared-duration question, every interactive screen contains one film pair
and exactly four answers: A, B, either works, and neither fits.

The duration question remains because it is declared viewing context, not a
mood or an attribute-analysis prompt.

### Rejected interface mechanisms

- correctable guess;
- axis labels or axis captions;
- sets of three;
- triads;
- rejection questions;
- a fifth answer.

These mechanisms are rejected by product decision, not deferred. The quiz
exists to read subconscious preference. Any interface element that asks the
viewer to reason explicitly about attributes breaks that purpose.

### Scope rule

No new interface element may be added to the quiz. Future proposals for chips,
labels, explanatory prompts, additional answers, or other interaction types
are vetoed by this principle. Changes may improve transport and reliability,
but the visible quiz remains duration followed only by repeated four-answer
film pairs until the existing stopping rule.

The final recommendation card is delivery after the quiz, not an additional
elicitation screen, and may contain only the product actions defined below.

### Final pick delivery

The three-film shortlist is removed. It was an implementation proposal, not a
product requirement. The result is one pick at a time from the integral ranked
order after eligibility, franchise deduplication, and semantic reranking.
Cluster diversity must not displace a higher-confidence candidate.

The card has exactly two actions:

- `me dá outro` advances to the next item in the frozen ranked order and logs
  an explicit item rejection with its rank. It never recalculates the
  posterior or changes region.
- `vou assistir` accepts the current item and closes the session. Merely
  displaying a recommendation is not acceptance.

After five rejected items, later cards disclose that confidence has fallen:
“daqui pra baixo já é chute”. They remain available.

The product metrics are acceptance@1, effort-to-accept (the count of
`me dá outro` actions), and the per-session `vou assistir` rate. Every
displayed item retains posterior score and rank; every `me dá outro` retains
an explicit rejection and rank; acceptance retains the accepted rank. These
are the only ranking outcomes currently carrying real behavioral ground
truth. Target position and SC@3 remain synthetic/offline diagnostics and are
not product metrics.

### Post-film signals

The post-film thumbs signal answers only “era a vibe que eu esperava?”. It
measures motor mood accuracy, not film quality. Film quality and reviews belong
to Letterboxd. Per-session logs retain accepted-pick position, preceding
rejections, vibe feedback, and whether the film was logged on Letterboxd.

Acceptance schedules one reminder for runtime plus 30 minutes. The reminder is
never repeated. Its `já loguei` action records completion; no response remains
logged as not completed.

### Duration and eligibility

Declared duration is a ceiling, never a range: 90 means any film up to 90
minutes, 120 means any film up to 120 minutes, 150 means any film up to 150
minutes, and `150+` means no limit.

Runtime is an intrinsic catalog fact fetched from TMDB at build time and
embedded in the runtime bundle for all recommendation candidates and probes.
Session eligibility performs no external runtime lookup. Unknown runtime is
always fail-open.

The eligibility mask operates over the complete candidate catalog before
ranking. Card enrichment and availability are informational delivery paths;
their success or failure cannot change eligibility. Availability is not a
candidate filter.

Normal-mode eligibility has a sanity floor of 180 candidates (the operational
interpretation of “about 200”). Breaching it records an alert, notifies the
session, and bypasses the suspect duration filter fail-open.

### Transport result

The resident service/file-id architecture is accepted: the measured
14-round session had callback-to-send p50 `366.74441 ms`, calculation p50
`18.537246 ms`, and media p50 `0.003 ms`. Telegram accounted for about 94% of
the remaining wall time. Pair selection, likelihood, stopping, and the
selection policy were not implicated in the duration-mask incident.

### Production-scale validity closure

The top-80 cutoff was a terminal delivery serialization limit, never posterior
support. Posterior updates, pair selection, entropy, and stopping always used
all 1,215 candidates. The production-scale trajectory conclusions remain
valid: posterior `1.17x` catalog-random, production posterior plus semantic
top-60 `2.34x` (`2.35x` rounded), median target position `421.5`, and ceiling
in `47/50` sessions. The earlier stable-taste estimate of `1.76x` came from
only `3/50` hits and is superseded by the full-catalog census below.

Semantic top-60 recorded four hits versus three for stable taste and two for
pure posterior: one session of descriptive margin over stable taste and two
over posterior. At N=50 these rare-event differences are underpowered and do
not establish superiority.

The 10%-of-eligible semantic window is rejected as the tenth mechanism
hypothesis refuted by ablation. It improved one duration ceiling and degraded
the two largest catalogs. Production keeps fixed window 60 and disables
semantic reranking below 250 eligible candidates.

Final picks from `quiz_20260729_124143_2290` and
`quiz_20260729_131725_2321` are invalid. Their rounds and stopping outcomes
remain valid.

### Legibility intervention

Response legibility is treated as a response-noise intervention, not a
cosmetic layer. Keswani et al., AIES 2024
([arXiv:2407.18889](https://arxiv.org/abs/2407.18889)), report that active
learning can match or underperform random selection when preferences are
unstable or answers are noisy. With a transient mood target and an
approximately 25% noisy synthetic respondent, this adversarial regime is the
leading hypothesis for the weak `1.17x` posterior lift and the sequence of
mechanism refutations. It is a hypothesis, not a demonstrated causal result
for this quiz.

The 3%/10%/20% band ablation leaves 10% as promising but inconclusive:
`none` fell from `68.1282%` to `64.2036%`, with a paired 95% bootstrap
interval for the change of `[-8.6459, +0.6899]` percentage points. The 20%
band is rejected. The 10% band is active as a real-use canary; keep or revert
is decided from per-session `noneRate`, not from the inconclusive offline
interval.

The first remote-LLM legibility benchmark is invalid for model comparison. On
30
deterministically replayed real-session states, the 10% band yielded 10–15
candidates in only 3 states and a median of 2. With provisional mechanical
labels, random selection had `69.8333%` illegible choices, GPT-5 nano
`66.6667%`, and GPT-5 mini `70.0000%`; those near-ties primarily measure the
collapsed input set, not model judgment. The LLM layer is on hold, not
rejected. It may be retested only after the real candidate set contains
10–15 choices. No scorer is distilled from this invalid benchmark.

The collapse diagnosis on 36 replay states found: pool `763`, static semantic
admissibility median `399`, unused-probe removal median `347`, 95%-of-best
A/B-channel EIG floor median `2`, and final 10% total-EIG band median `2`.
Thus probe reuse is not the main cause; the A/B floor is. Refused-region and
repeated-dominant-axis filters were never active in production and were
measured only as counterfactuals.

The 95% A/B-channel floor is the eleventh mechanism hypothesis refuted, and
the most operationally costly: it was introduced without a calibrated value,
remained active for weeks, and silently caused the lack of pair choice being
investigated. Removing it entirely increased `none` from `64.2035964%` to
`67.5359307%` on the current 10%-band protocol, confirming that the A/B
anti-rejection mechanism has real value but that 95% was unjustified.

A 50/70/85/95/off sweep calibrated its replacement. The 50% floor was the
only tested point that restored a median candidate set of 6 while preserving
competitive outcomes: `none 65.3980464%`, posterior SC@3 `6%`, semantic-60
SC@3 `6%`. At 70%, the candidate median was 4 and semantic-60 SC@3 `2%`; at
85%, 2.5 and `2%`; at 95%, 2 and `4%`; off, 6 and `8%` but `none 67.5359307%`.
Production therefore uses the sweep-calibrated 50% floor with the 10% band
canary. It remains subject to real-use `noneRate` evaluation.

Method rule: a new mechanism with a free parameter cannot enter production
until the parameter comes from an explicit calibration or sweep. If nobody
can justify the value, the mechanism is not ready.

The pool itself is also structurally narrow. A provisional mechanical rule
found strong sensitivity to its shared-profile threshold: `21.3630%` of the
763 pairs fall below RMS `0.40`, `42.4639%` below `0.50`, and `84.5347%`
below `0.75`. Therefore the earlier approximately 70% figure is not a
calibrated pool fact.

An offline pool of 4,096 pairs excluding the strict RMS-0.75 rule expanded
coverage from 247 to 280 probes and from 200 to 602 cluster regions. In the
50-target harness it reduced `none` from `60.5299367%` to `54.9057609%`,
changed posterior SC@3 from `4%` to `2%`, semantic-60 SC@3 from `8%` to
`10%`, and median target rank from `421.5` to `402`. It remains staging only:
the mixed accuracy result and uncalibrated threshold do not justify
promotion. Even with 4,096 pairs, the A/B floor still reduced the median to
3 and the final 10% band to 1.5.

### Identifiability closure for axis credit

Named reason-by-axis attribution is closed. Kleindessner and von Luxburg,
“Uniqueness of Ordinal Embedding,” COLT 2014
([PMLR 35](https://proceedings.mlr.press/v35/kleindessner14.html)), establish
ordinal-embedding uniqueness only up to similarity transformations under
their assumptions. Therefore comparisons identify geometry, not an intrinsic
named coordinate basis. With highly correlated named axes, per-axis causal
credit is structurally non-identifiable from ordinal answers alone.

The five axis-credit variants are not implementation failures; they targeted
a non-identifiable object. No whitening, axis mask, or endorsement bonus
variant returns to the roadmap. This does not claim that noisy finite quiz
data perfectly recover geometry; it says named axis attribution is not
uniquely recoverable from that geometry.

### Label-audit queue

Nahum et al.
([arXiv:2410.18889](https://arxiv.org/abs/2410.18889)) support concentrating
human review on high-confidence disagreements from a multi-LLM ensemble.
That confirms the existing three-pass disagreement queue and does not justify
a new labeling campaign. The current seven-film worst-disagreement queue
remains the review scope.

The stronger numerical claim that roughly 6.5% of annotations contain roughly
80% of errors was not found in the verified paper and is deliberately not
recorded as an established result.

Because the deep-research report contained at least this one non-traceable
quantitative assertion, the entire report carries a source-reliability
caveat: each material claim must be verified against its primary source before
it informs a product decision.

### Stopping backlog

GLR/Chernoff stopping remains research backlog only. Kaufmann, Cappé and
Garivier (JMLR 2016) and Garivier and Kaufmann (PMLR 2016) motivate comparing
generalized likelihood-ratio separation between a leader and its nearest
rival instead of requiring a high absolute posterior mass. A future study
should frame the 14-round product as fixed-budget best-arm identification and
always return the best current arm. It should evaluate Borda-style objectives
for potentially non-transitive mood preferences rather than assume a
Condorcet winner, following the dueling-bandit distinction discussed by
Jamieson et al., AISTATS 2015.

Nothing in this backlog changes the current likelihood, posterior, stopping
rule, delivery, or labeling pipeline.

### Terminal LLM delivery rerank

A terminal OpenAI reranker was tested offline before the pair-selection LLM
idea. On the same frozen 50-target production-scale sample, it saw only the
ordered pair/answer history and ordinary candidate metadata. It did not see
targets, axes, posterior values, cluster labels, masses, or confidence.

The best nominal arm was GPT-5 mini over the semantically reranked top-30:
same-cell top-3 `4/50`, versus `2/50` for semantic top-30 and `3/50` for the
current semantic top-60. Exact-target median rank remained `470.5`. This is
only one-session margin over current production.

The no-fame gate was not clean. In the best arm, movement had essentially zero
correlation with IMDb rating (`rho +0.003`) but small positive correlations
with catalog-list count (`+0.132`) and TMDB popularity (`+0.136`). Letterboxd
coverage was only 25 of 1,500 movement observations and cannot adjudicate
bias.

The terminal LLM layer is therefore not promoted. Production remains local
semantic top-60 with the existing fail-open behavior and no new model call.
If revisited, it must beat semantic top-60 again after controlling the
popularity signal. `acceptance@1` remains the decisive real-use metric.

Evidence:
`data/movies-quiz-v3-evaluation/terminal-llm-rerank-production-scale-v1.md`.

### Statistical power of production-scale validation

SC@3 is too rare for configuration decisions with 50 sessions. At a
catalog-random base rate of approximately `3.41%`, observed comparisons such
as posterior `2/50` versus semantic `4/50`, stable taste `3/50` versus
posterior `2/50`, terminal LLM `4/50` versus production `3/50`, and clean-pool
posterior `2/50` versus `1/50` are underpowered. They remain descriptive
observations, not established ordering between policies.

A standard two-sided two-proportion approximation for `4%` versus `8%`,
80% power, and alpha `0.05` requires approximately `553` sessions per arm.
Future SC@3 decisions therefore require hundreds of sessions per arm; no
production configuration may be promoted or rejected from SC@3 at N=50.

The first cost estimate of `US$1.50` per arm / `US$3.01` for two arms did not
describe the implemented paired design accurately. The powered harness shares
one set of 500 respondent trajectories across posterior, semantic, and
terminal arms; it does not pay for 1,500 independent quiz sessions.

At its checkpoint, all 500 trajectories had reached at least round 5, 481 had
reached round 10, and 25 had already stopped: 4,955 answered rounds total.
Those calls cost `US$0.58449375`, or `US$0.00011796` per answered round. The
misleading quotient `US$0.584 / 25 = US$0.023 per completed session` assigns
the substantial work already performed for the 475 active trajectories a
cost of zero and must not be used for projection.

Using the observed per-round cost, the respondent's absolute worst case
through round 14 is about `US$0.826` total. Using the separately measured
terminal-reranker cost of `US$0.001735955` per session, 500 terminal calls add
about `US$0.868`. The powered four-policy comparison is therefore projected
at no more than approximately `US$1.69`, not `US$47`. The checkpoint remains
preserved but paused after Felipe's cancellation request and the quota
failure; do not resume without a new explicit decision after this corrected
accounting.

The N=50 harness has useful power for larger, denser signals. `none` rate
aggregates roughly 650–700 rounds per arm and can resolve effects near eight
percentage points, while five-point effects remain uncertain. Target rank is
continuous over 50 sessions and is more informative than rare SC@3.
Movement/popularity correlations use about 1,500 rows, though repeated films
require clustered rather than naive independent-observation inference.

The clean 4,096-pair pool's approximately eight-point reduction in `none` is
the only current production-scale configuration signal clearly above the
N=50 harness's useful detection range. Its mechanical legibility threshold
still requires Felipe's blind calibration before promotion.

### Terminal LLM real-use canary

Felipe explicitly accepts terminal latency and authorizes the best measured
configuration as a real-use canary despite inconclusive offline accuracy:
GPT-5 mini over the semantically reranked top-30. The decision is grounded in
single-user product judgment, not a claim that `4/50` establishes superiority
over `3/50`.

The terminal call shows Telegram `typing`, has a hard 45-second timeout, and
fails open to the existing semantic order. Input order, output order,
explanation, movements, usage, fallback reason, and wall latency are persisted
for replay and audit.

The deciding product metrics are `acceptance@1` and
effort-to-accept (`me dá outro` count). Popularity correlation is reported
every ten completed real sessions. If either movement correlation with TMDB
popularity or catalog-list count exceeds `+0.25`, the terminal LLM layer is
automatically disabled. No local scorer is distilled.

The card explanation is active as a second output of the same terminal rerank
call, with zero additional provider calls or model latency. It can affect copy
only, never the chosen film or frozen order. The first card uses the concrete
session-grounded explanation; later `me dá outro` cards use their ordinary
metadata copy because the single terminal call explained only its first
placed film.

### Powered existential comparison

No additional parameter sweep is authorized before the powered existential
campaign. The next comparison uses 500 shared targets per arm:

1. pure posterior;
2. posterior plus semantic top-60;
3. posterior plus semantic top-60 plus terminal GPT-5 mini top-30;
4. stable-taste prior without quiz.

The same 500 quiz trajectories are reused for arms 1–3, producing a paired
comparison; arm 4 uses the same 500 targets without elicitation. Report
same-cluster top-3, `none`, median and mean exact-target rank, terminal
popularity correlations, paired uncertainty, and token-derived cost. This
campaign precedes any revisit of A/B floor, near-optimal band, semantic
window, or pair-pool parameters.

The campaign is currently paused, not discarded. Its checkpoint contains 500
trajectories through roughly round 10 and 25 completed trajectories. The next
paid experiment remains the clean-pool validation; do not spend more on
policy comparison while the pair pool may still change.

### Human-calibrated pair legibility

Felipe labeled 32 pair presentations using a product criterion: a pair is
respondable when its question can be named immediately, without forcing an
attribute analysis. The labels contain 15 respondable and 17 non-respondable
presentations, including repeated pairs as they appeared in the blind audit.

The best threshold over distance in the weighted 12-axis geometry reached
only `22/32 = 68.75%` accuracy. It recovered every non-respondable label but
also rejected ten respondable pairs. This confirms that geometry alone does
not represent the production-category distinctions Felipe actually uses.

A conservative metadata rule reached `28/32 = 87.5%`: 13 true positives,
15 true negatives, zero false positives, and four false negatives. A pair is
marked mechanically illegible when either film shares a TMDB collection,
both are animated, both belong to the same explicit Marvel/DC production
universe, or their first two TMDB genres have Jaccard overlap at least `0.67`
and their calibrated mood RMS distance is below `0.47`.

The zero-false-positive operating point is deliberate. The four misses are
semantic categories not safely captured by existing metadata: sports
inspiration, dark investigative thriller, broad franchise blockbuster, and
light family comedy. The rule must not be broadened merely to fit this small
calibration sample.

Applied to the current 763-pair pool, the rule marks `224/763 = 29.3578%`
illegible. A clean 4,096-pair staging build covers 278 probes and 586 cluster
regions. It is not promoted until the blind respondent harness reports
`none`, exact-target rank, and candidate-set size. That validation is
currently blocked by OpenAI `insufficient_quota`; production remains on the
763-pair pool.

Evidence:
`data/movies-quiz-v3-evaluation/legibility-label-calibration-v1.json` and
`data/movies-quiz-v3-evaluation/legible-pool-build-v1.json`.

All four clauses fire on the current pool. Counts before overlap removal are:
same TMDB collection 16, both animated 120, same Marvel/DC universe 57, and
same-primary-genre plus low-mood-contrast 60. Unique contributions are
respectively 6, 113, 41, and 37. No clause is a zero-yield degree of freedom;
the both-animated rule supplies 113 of the union's 224 unique removals.

The in-sample result is not sufficient for promotion. A 30-pair blind
holdout, matched to the original audit's RMS distribution and excluding all
calibration pairs, is awaiting Felipe's R/N labels. Promotion requires about
80% holdout accuracy; below 75% the calibrated compound rule is considered
overfit and must be reduced to mechanically defensible clauses.

Distance-only legibility is closed as the primary solution. Eight of the 17
non-respondable calibration presentations were two animated films, while
animation has weight 0.2 in the standardized mood geometry. The geometry can
place two animations far apart on other mood dimensions while missing the
production category that dominates the human judgment.

### Terminal explanation contract

The card explanation is the second field of the existing terminal rerank
response, never a second model call. The model must first produce the full
permutation and then explain the film it placed first. Inputs contain title,
year, director, genres, synopsis, and ordered session history, including
`nenhum`; they structurally exclude Letterboxd and IMDb ratings.

The explanation must be one short concrete sentence grounded in selected or
rejected films. It may not mention axes, scores, fame, prizes, ratings, or
algorithmic state, and may not reveal twists, endings, or character deaths.
Failure or timeout preserves the semantic order and ordinary metadata copy.

### Stable-taste full-catalog census

The no-quiz stable-taste baseline was evaluated locally on every candidate,
not on a duplicated N=2,000 sample. Repeating 785 targets would add no
information and would falsely narrow uncertainty.

Across the exact 1,215-film catalog, the fixed stable-taste top three cover
the target's cluster for `55/1,215 = 4.526748971%` of targets. A target
bootstrap gives `[3.374485597%, 5.679012346%]`. Exact-target median and mean
rank are both 608; this is an identity for a census of any fixed permutation,
because every rank from 1 through 1,215 occurs exactly once. The census is a
free baseline but cannot decide the project alone; it must be contrasted with
the quiz policy on the same target population.

Against the K=80 random reference of `3.41%`, the census has a descriptive
lift of `+1.116748971` percentage points (`1.327492x`). However, `3.41%` lies
inside the target-bootstrap interval, so the no-quiz stable-taste policy has
not demonstrated a generalizable advantage over random selection. This is
not literal equality—the finite-catalog point estimate is higher—but it
invalidates the former `1.76x` claim as evidence. The project's existential
question is therefore whether any deployed quiz policy demonstrably beats
random selection.

The planned production-scale comparison is paired. Posterior-only,
posterior-plus-semantic, and posterior-plus-semantic-plus-terminal-LLM reuse
the exact same pair trajectory and automatic responses; only their terminal
ordering differs. This preserves validity and reduces cost and variance.
Any arm that changes pair selection, likelihood update, or stopping would
break the pairing and require its own trajectories.

Evidence:
`data/movies-quiz-v3-evaluation/stable-taste-census-v1.json`.

### Legibility holdout and rule refinement

Felipe returned 30 blind holdout labels: 20 respondable, 10
non-respondable, with nine marked as boundary judgments. The v1 metadata rule
scored `25/30 = 83.3333%` overall and `17/21 = 80.9524%` on non-boundary
labels. It therefore cleared the predeclared 80% holdout gate, but its error
structure shows that its clauses are not the final production rule.

The coarse `bothAnimated` clause scored `24/30 = 80%` in isolation. Its two
false positives were exactly Japanese melancholy animation versus western
studio animation: Suzume versus Toy Story 3 and Suzume versus The
Incredibles. Replacing it with an animation-family clause — both western
animated, or both Japanese action animation — scored `26/30 = 86.6667%`
with zero false positives.

The primary-genre plus mood-RMS clause is removed from the candidate rule.
It encodes surface similarity and is structurally aligned with corrected
false rejections such as investigative thrillers that provide very different
experiences. A narrow broad-comedy proxy, requiring both TMDB Comedy, both
`comic_serious` z <= -1.8, and absolute comic-axis difference <= 0.25, catches
Movie 43/Zohan and Baywatch/Deadpool 2. This proxy was derived from the
holdout and is not externally validated.

The resulting candidate rule scored `29/30 = 96.6667%` overall and `21/21 =
100%` on clear labels. These figures are descriptive fit, not a promotion
gate, because animation-family and narrow-comedy refinements used the holdout
error pattern. A new blind sample is required before production use. The only
miss was boundary pair Black Adam/Uncharted.

The holdout is representative of the pool in aggregate RMS and rejection
rate but not in clause composition. Median RMS was `0.5638` versus `0.5422`
in the pool; same-cluster rate `16.67%` versus `18.09%`; v1-rule rejection
rate `30.0%` versus `29.36%`. However animation/animation was `26.67%` in the
holdout versus `15.73%` in the pool, while collection and franchise-universe
clauses were underrepresented. The aggregate match is partly cancellation,
not proof of categorical representativeness.

Legibility filtering must be phase-aware. Of 223 pool pairs rejected by the
refined candidate rule, 55 are same-cluster (`24.66%`). Those pairs are
already irrelevant to coarse cross-cluster localization but may be useful in
fine refinement. Do not globally delete them at build time. A future staging
implementation should retain the full pool and apply family-based exclusions
only during coarse selection, relaxing them in fine.

Felipe corrected five confident-N labels from the first audit to R:
Demon Slayer/Suzume twice, Creed II/The Blind Side, Night at the
Museum/The Princess Bride, and Iron Man 3/The Phantom Menace. Harry Potter
4/Spider-Man 2 becomes boundary rather than confident N. The first audit is
historical discovery evidence only: its labeling criterion changed during
review and it must not be used as an accuracy reference unless all pairs are
blindly relabeled under the final criterion.

Unknown-title protocol: when Felipe does not know either film, label `?` and
exclude the pair from accuracy rather than treating it as N. The Drama/X was
confirmed R after correcting title knowledge. A release-date audit found
only three 2026 probes — Project Hail Mary, The Drama, and The Odyssey — and
TMDB marks all three released before the current date; no objectively
impossible-to-have-seen probe was found.

Evidence:
`data/movies-quiz-v3-evaluation/legibility-holdout-results-v1.json`.

### Third legibility holdout

The refined rule was frozen before drawing a third blind holdout. Thirty new
pairs were sampled after excluding all 58 previously audited unique pairs,
using largest-remainder quotas over the complete rule-signature distribution
of the 763-pair production pool. The sample contains 21 rule-negative pairs,
four animation-family pairs, one collection pair, two franchise-universe
pairs, and two narrow-broad-comedy pairs. Predictions were withheld from the
reviewer. Felipe returned 22 R and eight N, with three boundary judgments and
no unknowns. The frozen rule scored `29/30 = 96.6667%` overall and `26/27 =
96.2963%` on non-boundary pairs. The only error was Bridesmaids/Superbad:
the narrow-comedy proxy rejected it, while Felipe found a clear adult-female
friendship/class versus adolescent-male virginity contrast. The Wilson 95%
intervals are `[83.3296%, 99.4091%]` overall and
`[81.7165%, 99.3432%]` on non-boundary labels.

This validates the family-identity core but not the exact comedy clause.
Do not broaden it post-hoc. A future comedy rule would additionally need
subject/demographic identity and a fresh blind gate.

Poststratifying the preceding 30-pair holdout to the production pool changes
the refined rule's binary rejection accuracy only slightly, to
`96.6298446%`. Exact full-signature reweighting over represented strata gives
`96.5576592%`, covering `747/763 = 97.90%` of the pool. The 16 collection
and collection-plus-universe pairs absent from that holdout imply a strict
full-population accuracy bound of `[94.5328590%, 96.6298446%]`; this remains
an in-sample diagnostic, not external validation.

The third holdout exposed a sampling limitation: stratification matched the
frozen rule's signatures rather than all cultural category-pair
combinations. A mutually exclusive category-pair poststratification covers
`657/763 = 86.1075%` of the pool and estimates `98.8838%` accuracy within
represented strata, but the missing 106 pairs make the full-population point
estimate unidentified; the strict bound is `[85.1464%, 99.0389%]`.
Therefore the raw blind `29/30` is the primary honest result, while the
poststratification is sensitivity analysis rather than a corrected headline.

The decisive enrichment check does not support the hypothesis that the
current selector disproportionately shows identity-illegible pairs. Under
the frozen identity rule, `223/763 = 29.2267%` of the production pool is
rejected, versus `1,048/4,955 = 21.1504%` of pairs actually shown in the
current 500-session checkpoint (`1,045/4,946 = 21.1282%` in coarse).
Thus the active 10% band plus 50% A/B floor selects fewer such pairs than the
pool baseline, not more. The earlier lived illegibility was consistent with
the old 3%/95% candidate collapse; a new coarse metadata filter is now a
marginal refinement, not a demonstrated necessity, and remains out of
production. This check uses the current 763-pair pool; the old globally
filtered 4,096-pair build is not a valid proxy for the intended
preserve-all/coarse-only design.

Historical application separates the real product failure from pool
composition. In `quiz_20260729_131725_2321`, the complete frozen rule flags
`7/14 = 50%` of shown pairs. One flag is the unvalidated comedy false
positive Anyone But You/Baywatch; the validated production-family core flags
`6/14 = 42.8571%`, matching the manual audit. The session nevertheless had
`11/14 = 78.5714%` `none` answers, so at least five rejections occurred on
pairs the validated identity rule considers legible. Legibility therefore
cannot explain the crisis by itself.

Across the five old relay sessions, the complete frozen rule flags only
`3/61 = 4.9180%` of pairs and the validated family core only
`2/61 = 3.2787%`. The 95% A/B-floor collapse caused repetition, scarcity and
poor directional coverage, but did not generally manifest as
same-production-family illegibility. The honest causal record is:

1. The terminal eligibility mask starting from top-80 plus duration-as-range
   reduced the worst real session to 41 candidates and dominated its
   coverage failure.
2. The arbitrary 95% A/B floor collapsed relay candidate menus to about two,
   causing low variation and forced selection.
3. Dense franchise/animation pool composition contributed to identity
   illegibility, but was the smallest of the three mechanisms.

The investigation initially mislabeled a coverage complaint as legibility
and then attributed filter-induced scarcity to pool composition. Historical
illegibility estimates of 70% (arbitrary RMS), 53% (unstable first labels),
33% and 27% (corrected blind samples), and the current 21.15%-shown/29.23%-pool
measurement must be presented with their distinct protocols. The first
sample is historical; the blind frozen-rule result is `29/30`; no fourth
holdout or comedy-clause refinement is authorized.

Terminology is now strict:

- **Illegible** means the person cannot distinguish the experiences proposed
  by the two films. Its intervention is pair/pool composition.
- **Irrelevant** means the distinction is understandable but neither side is
  near the desired direction. Its intervention is candidate coverage and
  region localization.

Felipe had used “illegible” operationally for both. Most complaints in the
failed sessions were irrelevance, not indistinguishability. This conceptual
confusion sent the project through RMS thresholds, metadata rules and three
holdouts aimed at the smaller mechanism. Those audits remain useful
knowledge, but they do not replace the demonstrated coverage diagnosis.

Evidence:
`data/movies-quiz-v3-evaluation/legibility-holdout-results-v2.json`.

### Preregistered interpretation of the N=1,000 paired campaign

The interpretation below was fixed before seeing final campaign results.
The random K=80 reference is `3.41%`. Stable taste without quiz has point
estimate `4.526748971%` and target-bootstrap interval
`[3.374485597%, 5.679012346%]`, so it has not demonstrated lift over random.

- Scenario A: if any quiz arm's SC@3 95% interval lies wholly above 3.41%,
  the quiz has measurable absolute lift and the pessimistic conclusion is
  withdrawn.
- Scenario B: if no arm clears random absolutely but a paired contrast is
  nonzero, terminal ordering matters while absolute SC@3 is limited by
  another component.
- Scenario C: if neither absolute nor paired lift is detected, the data are
  compatible both with no SC@3 value and with hidden-target SC@3 being
  mismatched to a product where multiple films can satisfy a mood. Do not
  resolve that ambiguity with another harness; use real `acceptance@1` and
  effort-to-accept.

No new arm, larger N, or parameter sweep follows this result. The report must
include per-arm SC@3 with 95% intervals relative to 3.41%; paired differences
arm 2 minus arm 1 and arm 3 minus arm 2 with intervals; identical shared
`none` rate; mean and median target rank; arm-3 popularity correlation; final
cost; and an integrity audit proving identical pair/answer trajectories in
all included sessions. Any divergent session is excluded from paired
analysis.

### Powered existential comparison — completed

The preregistered N=1,000 paired campaign completed on 2026-07-29 with exact
pairing integrity: 1,000 trajectories compared and zero divergent sessions.
Against the fixed random reference of 3.41%, arm 1 posterior produced
55/1,000 SC@3 = 5.50% (Wilson 95% CI 4.25–7.09%), arm 2 semantic-60 produced
107/1,000 = 10.70% (8.93–12.77%), and arm 3 terminal GPT-5 mini produced
80/1,000 = 8.00% (6.47–9.85%). All intervals clear random, so the
preregistered result is **Scenario A** and the pessimistic absolute-lift
conclusion is withdrawn.

The paired arm 2 − arm 1 difference was +5.20 pp (target-bootstrap 95% CI
+3.40 to +7.10 pp); arm 3 − arm 2 was −2.70 pp (−4.80 to −0.70 pp).
Semantic-60 ordering helped this hidden-target metric, while terminal LLM
reranking hurt it relative to semantic-60. This authorizes no new arm, larger
N, or sweep. Shared quiz-arm none was identical at 60.4011%. Mean/median
target ranks were 414.932/366.5, 414.025/366.5, and 414.314/366.5. Arm-3
popularity Spearman correlations were +0.09043 for TMDB popularity and
+0.10008 for list count, below the +0.25 disable threshold. Total
token-derived cost was US$3.1792274. Production was not mutated.

This result **refutes** the earlier conclusion that the quiz had not
demonstrated an advantage over stable taste without a quiz. That conclusion
came from `4/50` versus `3/50`: four events versus three. The preregistered
stable-taste estimate is 4.5267% with target-bootstrap 95% interval
3.3745–5.6790%, which does not overlap semantic-60's powered Wilson interval
8.9323–12.7685%. Asking is worth it.

The methodological correction is binding: SC@3 is a rare-event metric and
future decisions based on it require samples in the hundreds or thousands,
not N=50. The full N=1,000 paired campaign cost only US$3.1792274, so adequate
power is cheap relative to carrying a wrong product conclusion for weeks.

The raw arm 2 versus arm 3 contrast has a plausible representation confound:
the synthetic LLM respondent can endorse probes semantically near the hidden
target, and semantic reranking can recover that same representation. This
does not invalidate quiz lift or arm 2 versus arm 1, but it motivated a
read-only quartile diagnostic before treating arm 2 versus arm 3 as a product
decision.

That diagnostic did **not** show the predicted gradient. Using mean cosine
similarity between the hidden target and probes endorsed by A/B answers, arm
2 minus arm 3 SC@3 was +4.07, +0.41, +2.85, and +3.67 percentage points from
the lowest to highest quartile. The low-to-high change was −0.39 pp and the
sequence was not monotonic. Arm 2 was directionally ahead in every quartile;
this specific closed-loop mechanism is therefore unsupported. The metric
remains an offline hidden-target proxy, so real `acceptance@1` and
effort-to-accept are still the product arbiter.

Production now alternates deterministically only in real use: odd real-session
numbers use arm 3 terminal GPT-5 mini and even numbers use arm 2 semantic-60.
The separate `alternate_arms` switch is on in the production unit. Measurement
contexts turn it off and must set one arm explicitly, preserving comparable
replays. The selected arm is logged with `acceptance@1`, effort-to-accept, and
vibe; an arm comparison is emitted every ten accepted real sessions.

Card explanation is a separate post-pick GPT-5 mini call. The selected arm
freezes the order first; the card is sent immediately with neutral copy and
edited if the explanation arrives within 15 seconds. Timeout or failure keeps
the neutral copy and is logged. Input is limited to the chosen film's title,
year, director, genres, synopsis, and session answers—no axes, scores, or
ratings. Recorded reranks and recorded explanations replay without calling a
model.

Only after completion, the separate 4,096-pair staging pool was audited
read-only. Its v4 clustering has 80 clusters, yielding 800 cluster × probing
axis cells rather than the historical 160. There were 681/800 zero cells
(85.125%), versus historical 84/160 (52.50%); compare rates cautiously because
cluster granularity changed. Defining dense clusters as the upper quartile of
nonempty cluster size (at least seven probes), 69/144 full-weight-axis cells
were missing across 18 dense clusters. No coverage optimization was
implemented.

The 69 gaps were then ranked by the mean final posterior mass their cluster
received across the powered sessions. Cluster 23 dominates at 4.4786% mean
mass and has seven missing full-weight axes; cluster 40 follows at 1.5183%
with three. The full ordered list is in
`coverage-gap-impact-v1.{json,md}`.

For the impact check, a session was marked exposed when, at first localization,
one of its localized clusters lacked an axis whose cumulative observed
contrast was still at or below 0.8. Only 127/1,000 sessions localized; 53 were
gap-exposed and 74 localized without a matching gap. SC@3 differences
gap-minus-no-gap were +5.10 pp for posterior, −4.36 pp for semantic-60, and
+6.17 pp for terminal. The small groups and mixed signs do not show sessions
with coverage gaps being systematically worse. Coverage stays a health
diagnostic/backlog item; coverage-as-objective is not authorized.

Evidence:
`data/movies-quiz-v3-evaluation/existential-three-arm-1000-v1.json`,
`data/movies-quiz-v3-evaluation/existential-three-arm-1000-v1.md`, and
`data/movies-quiz-v3-evaluation/staging-4096-cluster-axis-coverage-v1.json`,
`data/movies-quiz-v3-evaluation/representation-confound-quartiles-v1.json`,
and `data/movies-quiz-v3-evaluation/coverage-gap-impact-v1.json`.

### Posterior tempering β — frozen sweep invalidated; 0.70 restored

The previously uncalibrated β=0.70 update tempering was swept read-only over
0.40–1.20 on the 1,000 frozen powered trajectories. A deterministic
SHA-256(session-id) split assigned exactly 500 sessions to selection and 500
to holdout. Arm 2 semantic-60 was fixed, alternation was off, and no API call
was made.

Train selected β=0.40. On holdout, mean target log posterior probability was
−11.85494 at β=0.40 versus −18.35906 at β=0.70: paired gain +6.50412 nats
with SE 0.15748, apparently beyond the preregistered one-SE threshold.
SC@3 was unchanged at 62/500 = 12.4%; mean target rank was 418.314 versus
418.008.

The objective was structurally degenerate here. With frozen evidence,
`p(x) ∝ prior(x) · evidence(x)^β`; changing β primarily compresses or expands
posterior ratios and barely changes ranking. Because the median hidden target
is around rank 370/1,215 rather than near the top, concentrating probability
necessarily removes mass from it. Mean target log probability therefore
rewards a more diffuse posterior, not better recommendation quality, and
would keep favoring smaller β below the tested boundary.

The real finding is posterior misspecification/superconfidence. Mean `exp(H)`
was 51.86 at β=0.40, 15.57 at β=0.70, and 5.94 at β=1.20 while the hidden
target's median rank stayed around 370–373. β changes declared confidence and
therefore the stopping gate, but it is not a quality lever for recommendation
ranking under frozen trajectories. The former shorthand that “13 rounds
become 9.1” was misleading: β discounts confidence, not ranking information.

β=0.40 would also obstruct the confidence stop gate: its mean `exp(H)=51.86`
stays above the approximately 33.3 threshold implied by
`exp(H)/floor ≤ 2.0`. The frozen replay concealed the live pair-selection
channel because EIG never got to choose a new pair from the changed posterior.

The β=0.70 replay exactly reproduced the powered arm-2 evidence
(107/1,000 SC@3; mean rank 414.025), validating the implementation. The brief
β=0.40 promotion was reverted; production and the frozen baseline are back at
β=0.70. The regression suite passed with median 10 and zero regressions.

The final live paired harness compared β=0.70 with β=1.00 on 500 shared
targets per arm, with fresh EIG-driven pair selection, arm-2 semantic-60
delivery fixed, and alternation off. The selection channel is real:
496/500 targets diverged, with 10.62 different-pair rounds per target on
average.

That divergence did not establish a quality gain, but the test was
underpowered for its primary rare-event metric. β=0.70 produced
53/500 SC@3 = 10.6% [8.20%, 13.61%], median/mean target rank
318/394.966; β=1.00 produced 64/500 = 12.8% [10.15%, 16.01%],
median/mean rank 323.5/403.854. The paired SC@3 difference was +2.2 pp
[−1.4, +5.6], and the paired median-rank improvement
β0.70−β1.00 was −5.5 [−48.0, +42.5]. Neither preregistered quality
criterion cleared noise. Resolving an unpaired 10.6% versus 12.8% SC@3
difference at 80% power would require approximately 3,343 sessions per arm,
about seven times the sample that ran. The supported statement is therefore
“not demonstrated in an underpowered test,” not “β=1.00 does not improve.”

β=1.00 concentrated and moved every operational metric in the favorable
direction: mean final `exp(H)` 8.04 versus 15.56, mean stop round 13.086
versus 13.426, ceiling rate 83.8% versus 88.8%, and mean `none` 46.90%
versus 51.21%. These are candidate effects, not resolved effects. Production
remains at β=0.70. The line may be reopened only with a powered design
(roughly US$10.50 at the observed cost rate) and `none` preregistered as the
primary metric; no further β sweep is authorized. The live harness cost
US$1.574458.

Evidence:
`data/movies-quiz-v3-evaluation/beta-tempering-frozen-sweep-v1.json`,
`data/movies-quiz-v3-evaluation/beta-tempering-frozen-sweep-v1.md`, and
`data/movies-quiz-target-test-dataset/current-rules-replay-beta-070-revert-final-v1.json`,
`data/movies-quiz-v3-evaluation/beta-live-eig-070-vs-100-v1.json`, and
`data/movies-quiz-v3-evaluation/beta-live-eig-070-vs-100-v1.md`.

### Level-1 representation diagnostics

Three independent diagnostics located the current representation bottleneck
without changing production.

**Human similarity.** The priority Yao/Harper bitstream was inaccessible
behind an Azure WAF challenge, so the public CC BY 4.0 MovieSim datasets were
used. MovieSim-2 yielded 670 complete joined pairs across 339 catalog films:
Spearman ρ was 0.299 [0.231, 0.370] for the weighted 12-axis space,
0.383 [0.316, 0.447] for TMDB genre Jaccard, and
0.417 [0.350, 0.479] for synopsis embedding cosine. MovieSim-1 independently
replicated the ordering on 427 pairs: 0.485 [0.409, 0.555], 0.548
[0.475, 0.614], and 0.615 [0.549, 0.676], respectively. Absolute correlations
are protocol-dependent, but semantic embeddings led in both datasets and the
12 axes fell below the preregistered 0.40 boundary on the primary dataset.
The axes are weak as a standalone proxy for human movie similarity.

**Seven-axis reduction.** The four correlated tone axes were merged by PCA;
PC1 explained 80.80% of their variance. Clusters and all 1,000 trajectories
were frozen. The reduced representation produced SC@3 11.30% versus 10.70%
(paired +0.60 pp [−1.10, +2.30]), median rank 366 versus 366.5, and identical
`none` by construction. It worsened mean rank to 423.021 from 414.025 and
mean target log probability by −0.73561 [−1.00711, −0.46435]. Reduction did
not earn promotion, but the test is inconclusive by construction rather than
a clean rejection. Freezing 12-axis clusters holds the target definition in
the full representation while asking the reduced representation to navigate
without four of those coordinates. SC@3 nevertheless rose numerically. The
current 12-axis representation stays until both geometries can be scored
against the same external reference.

**Frontier label audit.** A deterministic sample of 150 films covered all
80 clusters and all 38 original languages in the catalog. One pass with
`openai/gpt-5.6-sol` found overall mean absolute disagreement 0.116.
Signed shifts were statistically nonzero but small on `heavy_light` −0.044,
`intimate_epic` −0.028, `slow_propulsive` +0.040,
`cerebral_emotional` +0.048, `gray_cathartic` −0.046, and
`classic_contemporary` −0.046. `comic_serious` had the largest absolute
disagreement (0.253) but no consistent signed bias. Correlation between
absolute disagreement and current confidence was −0.145; the low-confidence
quartile differed by 0.127 versus 0.108 for the high-confidence quartile.
Confidence weakly captures disagreement but does not fully explain it.

The premise that all current labels were three passes of the same mini was
wrong: provenance shows a `sol/terra/sol` ensemble for 11 axes, with only
`comic_serious` coming from mini. This is recorded as an error of premise,
not a refuted hypothesis: the proposed test could not isolate mini bias on
the other 11 axes because the assumed single-model provenance was false.
The frontier audit remains useful as a cross-pass disagreement audit.
`comic_serious` having the largest absolute disagreement is weak evidence in
the expected direction for the only single-model axis, not proof of bias.
The frontier audit completed with zero reported billed cost.

Evidence:
`data/movies-quiz-v3-evaluation/human-similarity-benchmark-v1.json`,
`data/movies-quiz-v3-evaluation/human-similarity-benchmark-v1.md`,
`data/movies-quiz-v3-evaluation/seven-probing-axis-frozen-replay-v1.json`,
`data/movies-quiz-v3-evaluation/seven-probing-axis-frozen-replay-v1.md`,
`data/movies-quiz-v3-evaluation/frontier-label-audit-v1.json`, and
`data/movies-quiz-v3-evaluation/frontier-label-audit-v1.md`.

### Post-diagnostic representation actions

**External cluster alignment.** Four K=80 partitions were scored against
MovieSim pair labels. On MovieSim-2, accuracy/precision/recall for
same-cluster were 43.1%/87.4%/19.7% for current 12-axis clusters,
44.6%/87.2%/22.3% for reduced 7-axis clusters,
55.7%/87.4%/41.0% for synopsis-embedding clusters, and
51.2%/88.3%/33.0% for genre clusters. MovieSim-1 replicated the main result:
62.3%/83.3%/24.9%, 61.4%/81.0%/23.4%,
69.3%/80.7%/45.8%, and 68.6%/90.4%/37.3%, respectively.

Embedding versus current 12-axis accuracy improved by +12.5 pp
[+8.4, +16.7] on MovieSim-2 and +7.0 pp [+2.1, +11.7] on MovieSim-1.
The gain came from recall while precision remained similar. Excluding tied
human judgments preserved the ordering. The 7-axis partition did not
establish equivalence or superiority to 12 axes: +1.5 pp
[−1.5, +4.5] on MovieSim-2 and −0.9 pp [−4.4, +2.6] on MovieSim-1.

This is evidence that embedding geometry is a better external target
structure for human movie similarity. It does not show that axes are useless:
similarity judgments and tonight-mood are adjacent but different constructs,
and axes remain the legible mechanism that generates questions. It does show
that SC@3, whose target clusters are built from the weakest standalone
similarity signal, is not a neutral product-quality metric. Moving target
clusters to embedding space is a major architectural candidate and is not
implemented from this diagnostic alone.

**Human-fitted multisignal rerank.** A Ridge model was fit only on MovieSim-1
(N=427), with α=17.7828 selected by ten-fold cross-validation inside that
training dataset. Standardized weights were +0.07749 for axis similarity,
+0.11902 for genre Jaccard, and +0.17223 for embedding cosine. Spearman ρ was
0.6846 on training and 0.4790 on held-out MovieSim-2, above 0.4173 for
embedding alone.

On the 1,000 frozen trajectories, the current small-embedding semantic rerank
exactly reproduced SC@3 10.7% and mean rank 414.025. A fair large-embedding
comparator reached 12.1% and 413.916; the large-embedding combined model
reached 12.6% and 413.698. Combined versus large embedding alone was
+0.5 pp SC@3 [−1.1, +2.1] and +0.218 mean-rank positions
[0.000, +0.442]. Against current small embedding it was +1.9 pp
[+0.1, +3.8], but that comparison confounds signal combination with the
small-to-large embedding change. The literal two-gate criterion was met
(external ρ and replay SC@3 both rose), but the incremental gain from adding
axes and genre over the fair embedding comparator was not resolved.
No production promotion is authorized.

**`comic_serious` ensemble relabel.** All 1,497 films were relabeled only on
this axis with the same `gpt-5.6-sol / gpt-5.6-terra / gpt-5.6-sol` ensemble
procedure used by the other labels. Old versus new values had Pearson
0.8376, Spearman 0.8275, and mean absolute difference 0.2352. On the frozen
1,000-session replay, SC@3 moved from 10.7% to 11.1%, median/mean target rank
from 366.5/414.025 to 350.5/403.878, and `none` remained 60.4011% by
construction. These favorable offline movements are recorded as candidates;
the new axis was not promoted and production labels were not changed.

The relabel used 502,674 input and 87,200 output tokens including the schema
smoke. Actual billed USD could not be verified: the Responses API did not
return a charge and the credential lacked `api.usage.read`; no zero-cost
claim is made.

Evidence:
`data/movies-quiz-v3-evaluation/cluster-human-alignment-v1.json`,
`data/movies-quiz-v3-evaluation/cluster-human-alignment-v1.md`,
`data/movies-quiz-v3-evaluation/multisignal-human-ridge-rerank-v1.json`,
`data/movies-quiz-v3-evaluation/multisignal-human-ridge-rerank-v1.md`,
`data/movies-quiz-v3-evaluation/comic-serious-ensemble-relabel-v2.json`,
`data/movies-quiz-v3-evaluation/comic-serious-ensemble-relabel-v2.md`,
`data/movies-quiz-v3-evaluation/comic-serious-ensemble-frozen-replay-v2.json`,
and
`data/movies-quiz-v3-evaluation/comic-serious-ensemble-frozen-replay-v2.md`.

### Independent literature alignment

Marjieh et al., *Words are all you need?* (ICLR 2023,
[arXiv:2206.04105](https://arxiv.org/abs/2206.04105)), compared 611
pretrained image, audio, and video models with human similarity judgments.
Language-based methods outperformed the modality-only representations, and
stacking language embeddings with pretrained-model embeddings consistently
performed best across all three modalities. This independently supports the
architecture class used here: an LLM-labeled posterior followed by synopsis
embedding reranking. Internally, that stack is also the strongest powered
effect: semantic-60 over pure posterior was +5.20 pp
[+3.40, +7.10]. The paper supports the architecture class, not the specific
film labels or causal interpretation of this harness.

Sun et al., *Large Language Models as Conversational Movie Recommenders: A
User Study* (2024, [arXiv:2404.19093](https://arxiv.org/abs/2404.19093)),
studied 160 active users. LLM recommendations were strongly explainable but
lagged traditional recommenders in personalization, diversity, and trust;
zero-, one-, and few-shot prompting did not significantly change perceived
recommendation quality. That independently matches the reason for retaining
the terminal LLM only as an alternating real-use arm rather than assuming
prompt mitigation settles ranking quality. The local arm-3 deficit of
−2.70 pp [−4.80, −0.70] remains subject to its documented representation
confound.

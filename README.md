# ThisReelOrThat

**A public reference implementation of an adaptive this-or-that movie quiz.**

You answer a sequence of movie pairs. Each answer updates a Bayesian posterior over a separate candidate catalog. The published API stops on a catalog-specific confidence rule or round ceiling and returns a ranked candidate list. It makes no model calls at quiz time.

> **Implementation status.** The code in this repository is a clean-room reference core extracted from an older engine generation. It is runnable, but it is **not** the current private deployment. The research and design record below describes both generations; features present only in the private deployment are identified explicitly.

## What this repository executes

The published implementation includes:

- validated, catalog-specific bundles with separate probes and candidates;
- candidate embeddings aligned row-for-row with candidate IDs, with model and
  exact input-template provenance carried in the bundle;
- four-answer likelihood (`A`, `B`, `either`, `neither`), tempered posterior updates and cluster-entropy information gain;
- seeded near-optimal pair selection without probe reuse;
- catalog-specific confidence/ceiling stopping;
- frozen single-pick delivery with a skip cursor through the FastAPI adapter;
- injected session storage via the `SessionStore` protocol;
- a complete 12-axis demo bundle and end-to-end test.

The current private deployment additionally has features that are **described in this document but not implemented in the public reference core**:

- semantic mood filtering and mood-prior routing;
- semantic and optional terminal reranking;
- coarse-to-fine pair selection;
- the conditioned A/B information-gain floor;
- refused-region filtering;
- cross-session reuse and vivacity policy inside the variety band;
- build-time personal probe blocklists;
- semantic delivery explanation and transport-specific “another one” UI.

Those private-deployment features require further extraction; their description below is a design/history record, not an API guarantee for this repository.

Eligibility masking is part of the public core. It is constructed over the
entire candidate catalog and applied before sorting: `catalog -> mask -> rank`.
Duration is an inclusive ceiling; unknown runtime is fail-open, because missing
metadata correlates with obscurity and filtering it would bias toward popular
films. Availability is informative and never participates in the mask. The
bundle carries a small-set warning floor and a direct-pick threshold (production
uses 180 and 60); both are validated against the catalog size. A masked support
recomputes its theoretical entropy floor and within-cluster delta, and an empty
mask fails clearly.

Completed sessions expose one pick: the masked posterior argmax after explicit
franchise deduplication. The order is frozen once and a skip advances its cursor
without recalculation. Each entry in `pickSkips` records the concrete film and
its original one-based posterior rank; a skip means “keep looking”, not a
rejection or acceptance. Only `/picks/accept` records acceptance. From the sixth
shown item onward `lowConfidence` is true without blocking further traversal.
Post-film reminders, posters, verified availability and vibe feedback remain
outside the domain core.

Bundles now carry `candidate_embeddings` as inert data for the future semantic
reranker. Production artifacts use `text-embedding-3-large` with this exact
template (reviews are all available excerpts joined by two newlines, or
`[none]`):

```text
Title: {title}
Year: {year}
Synopsis: {synopsis}
Reviews: {reviews_or_none}
```

`probe_embeddings` is required because quiz answers endorse or reject probes,
and the planned reranker builds its semantic reference from those choices.
Probe embeddings must have the same dimension as candidate embeddings. The
demo vectors are synthetic and identified as such in
[`data/demo/README.md`](data/demo/README.md).

## Run the demo

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[api,dev]'
pytest
uvicorn api.demo:app --reload
```

Open <http://127.0.0.1:8000/docs>, call `POST /sessions`, then submit each returned pair to `POST /sessions/{session_id}/answers`. `GET /sessions/{session_id}` returns the current state. The demo deliberately reaches a ranked pick after six answers.

## Research and private-deployment record

What follows is the experiment and design history of the full system. Numerical results refer to the stated historical/private configurations, not automatically to the smaller public implementation.

---

## What's actually measured

Synthetic respondent (calibrated at 75.4% agreement with the human owner), targets hidden from the engine, N=50 per configuration.

| Catalog | Metric | Random | Engine | Ratio |
|---|---|---:|---:|---:|
| 282 films | target's rank | p50 | **p9–11** | **~5×** |
| 1,215 films | target's rank | 608th | 422nd | 1.4× |
| 1,215 films | right mood cell in top-3 * | 3.41% | 8.0% | **2.35×** |
| 1,215 films | *same, no quiz at all* (taste profile only) | 3.41% | 6.0% | 1.76× |
| 50 films | right mood cell in top-3 * | 30.5% | 44.0% | 1.44× |

\* `SC@3` was the metric during synthetic validation. It is **no longer the product metric** — delivery is a single pick, so what matters is the rank of the film the user actually accepts. That number only accumulates from real use.

**The uncomfortable row is the fourth one.** With a large catalog, recommending straight from a stable taste profile — asking zero questions — reaches 1.76× random. The quiz's posterior alone reaches 1.17×; it only beats the no-quiz baseline once a semantic reranking layer is added, and that layer's evidence is 4 sessions versus 2.

**Why the gap between catalogs is mechanical, not a tuning failure.** The engine stops when its posterior concentrates to roughly 33 effective candidates. In a 282-film catalog the target lands around rank 30 — confidence is calibrated. In a 1,215-film catalog it still declares ~33 and the target lands at 422 — **13× overconfident.** Resolution is roughly constant in absolute terms, so the same instrument is a good filter over hundreds of films and a weak one over thousands.

**All of this measures a task the product doesn't perform.** The benchmark asks the engine to recover one specific hidden film. Real use has no target: you have a mood, and many films satisfy it. Whether the recommendations are *good* is not answerable offline.

---

## The core idea

### A pairwise choice is a noisy 1-bit probe — if you control what it measures

"Parasite or Spider-Verse?" has a signal problem: the two differ in realism, country, animation, tone, and pacing simultaneously. When you pick one, which did you express?

The intended fix was **near-twin pairs** — two films close on every axis but one. Films are labeled offline on 12 continuous axes; a good probe differs sharply on exactly one.

It half-worked, and the half that failed is instructive:

- **Near-twins are illegible.** "Norbit or Superbad?" is a real pair the engine produced. Both are light comedies; the contrast is a nuance invisible to a human. Sessions were abandoned over pairs like this.
- **Axis purity is mathematically impossible for the axes that matter.** `heavy_light` correlates +0.90 with `gray_cathartic`, +0.78 with `demanding_casual`, −0.72 with `comic_serious`. A film that differs in weight also differs in catharsis — that's the structure of cinema, not a catalog gap. Requiring purity yields 7–11 usable pairs out of ~80,000.
- **The reason for a choice is not recoverable from the pair's geometry.** Measured directly: agreement between the respondent's declared reason and the axis the engine actually credited was **9.5%**, against a 10.3% chance baseline (n=1,952 rounds). This is the ceiling of the format, and it explains why eight separate attempts to fix credit assignment all failed.

The design that survived: **coarse pairs (high contrast, cross-cluster) until the region is located, then narrow pairs inside it.** Narrow pairs are good once the engine knows the neighborhood and bad before.

### The quiz identifies mood cells, not films

At the resolution of 12 labels, a catalog collapses into a few dozen distinguishable **mood neighborhoods**. Two films with near-identical vectors are indistinguishable by *any* sequence of answers — that's an information floor, not a bug. So:

- The posterior lives over films, but confidence is measured over clusters.
- Stopping is relative to the cluster structure's entropy floor, so it survives catalog swaps.
- Success means "the right kind of film for tonight," which is what a human means by a good recommendation.

### Probes ≠ candidates

**`probeCatalog`** — films you've watched. Only these appear in questions. **`recommendationCatalog`** — films you haven't: your watchlist plus curated public lists, minus watched. The posterior lives here.

---

## The math

Everything below runs in milliseconds. No model calls during the quiz.

### Labels

Each film is a vector in `[-1,+1]^12`: heavy↔light, intimate↔epic, **literally-possible↔impossible**, **stable↔subjective reality**, slow↔propulsive, cerebral↔emotional, morally-gray↔cathartic, classic↔contemporary, animation↔live-action, demanding↔casual, English↔international, comic↔serious.

Produced by an LLM under a frozen rubric with anchor films pinned by year + TMDb ID, **three independent passes per film with per-axis median**, and 15 control films re-inferred in every batch (batch rejected if mean drift > 0.08 or any single axis > 0.15).

**Axis weights are not uniform.** `english_international` is weighted **0** and `animation_live_action` **0.2**. Both are effectively binary — 99.1% and 99.7% of films sit at |v|>0.8 — so a mixed pair contrasts 2.96σ on language against 1.0–1.4σ for real mood axes, and the flag dominates every such pair. Worse, with uniform weights **100% of clusters were >90% pure by language** and no cluster had mood crossing animation: the cluster structure was ~9 mood cells replicated across 4 quadrants, and one spurious credit locked the posterior into the wrong quadrant permanently.

### Posterior and update

Session state is a probability vector over candidates. Each answer applies a tempered soft update, `p ← normalize(p · L(answer)^β)` with β = 0.70. **No hard elimination** — answers are noisy, and a hard cut on question 2 is unrecoverable.

For a pair `(a,b)`: `pref(x)` is `x`'s projection onto `d = a − b` from the midpoint, clipped; `shared(x)` is closeness to what `a` and `b` have in common.

### Four answers

| Answer | Meaning |
|---|---|
| **A / B** | evidence toward that side of the tested contrast |
| **Either works** | utilities close *from above*; weak pull toward the boundary, axis stays re-testable |
| **Neither appeals** | rejection of the pair's *shared* profile — informative about the axes the pair shares, not the one it contrasts |

Calibrated: κ = 3.5, evidence cap 1.25, σ_tie 0.55, "neither" strength 2.0.

**"Neither" is the single most important mechanism in the system.** Forcing a choice measurably poisons the posterior: with the "neither" option removed, median target rank went from 31.5 to 45 and mean from 40 to 77 (n=50). A bad pair answered under duress injects a *confounded direction*; refusing only suppresses. This was first noticed in human sessions (0 "neither" → target at rank 252; 3 "neither" → target as pick #1) and then confirmed in ablation. If you build something like this, build the refusal button first.

### Pair selection in the private deployment

Expected reduction in the cluster posterior's entropy, computed in closed form from the likelihood table. **No per-axis uncertainty ledger** — axes are correlated, so tracking "which axis is least certain" double-counts and wastes questions.

Variety in the public and private engines comes from a deterministic exponential race inside a near-optimal EIG band. The bundle carries both parameters: production currently uses `near_optimal_epsilon = 0.10` and `opening_min_candidates = 10`. At the opening, the selector expands a smaller band to the ten best admissible pairs before drawing. The seed is stable per session and pair (`sha256(session_id:min_probe_index:max_probe_index)`), so a session replays exactly while different sessions can open differently.

The original offline sweep tested ε = 0, 0.03 and 0.05. ε = 0.05 retained 91.6% semantic accuracy versus 93.0% at argmax while increasing distinct first pairs from 1 to 18 in the first 50 sessions. Later operational diagnosis found the effective 3% opening band had only three pairs and repeated across sessions; production widened it to 10% and added the explicit minimum of ten. The public engine uses uniform race weights. Production's soft cross-session reuse, exploration and vivacity weights remain private.

The frozen equivalence gate first proved its value by rejecting an incorrect
extraction specification rather than an implementation bug: the proposed seed
was `hash(session_id, round)`, while production actually hashes the session and
each pair's probe indices. The public extraction follows the observed
production behavior deliberately; the mismatch was not silently normalized.

### Stopping

Ask at least 5; stop when top-3 cluster mass ≥ 0.75 **and** `exp(H)/floor ≤ 2.0`; hard ceiling at 10 + min(neither-count, 4).

⚠️ **In production-scale validation this rule fired in 3 of 50 sessions; 94% hit the ceiling.** No threshold tested fixed it. The confidence gate rarely bites at large catalog sizes. Documented, unsolved.

### Prior: stable taste as a mixture, never a mean

`p₀ ∝ stable^0.30 · uniform^0.70`. Stable taste is a **2–3 component mixture** over highly-rated watched films, never an average — averaging bimodal taste points at a lukewarm film nobody wants. Measured: mean-vector prior scored −7.17 average log-probability, uniform −7.10, 2-cluster mixture **−5.22**. The mean lost to knowing nothing.

### Delivery in the private deployment

**One pick, not a shortlist.** `argmax` of the posterior after eligibility masking, franchise dedupe and optional semantic reranking, with two buttons: **another one** and **I'll watch this**.

*Another one* walks the ranked order without recomputing anything — predictable by design. Every tap is logged as an explicit rejection of that specific film **with its rank**, which is the only item-level channel the system has: choosing within a pair credits a direction, never a film. After five or six rejections the card admits confidence has run out rather than continuing to present guesses as recommendations.

*I'll watch this* marks real acceptance. Nothing counts as accepted without it — the quiz also gets used for testing and for showing people, and without an explicit accept every session would look like a hit.

The ranked order is **integral**: cluster diversity never displaces a high-confidence candidate. Eligibility (runtime, availability, identity) is a **mask applied before ranking**, never a filter after; metadata failure never excludes a candidate. Identity resolves through TMDb.

**Two feedback channels, deliberately separate.** A post-film 👍/👎 asks *"was this the vibe I expected?"* — that evaluates the **engine**. Whether the film was any good goes to a ratings service, not to the quiz. Conflating them teaches the wrong thing: a great film delivered on the wrong night would score 👍.

### Scope rule

**The quiz screen is only this-or-that.** One pair, four buttons, repeat until stopping. Nothing else appears — no mid-session guess confirmation, no direction chips, no axis labels, no fifth answer. Anything that asks for explicit reasoning about attributes breaks the premise of reading preference below the level of articulation.

One exception: a **duration question** at the start. That's declared context, not mood — and it's a *ceiling*, not a band.

---

## Design history: what didn't survive

This section exists because the rejected designs teach more than the surviving ones. Full ledger in [`DECISIONS.md`](DECISIONS.md).

### Label quality was the bottleneck, not the algorithm

Every algorithmic intervention moved the regression suite's median target rank from 30 to 30. **Re-auditing the labels moved it from 30 to 7.**

The audit was crude: read twelve well-known films' vectors and check them against what you know. Four were indefensible — *Pan's Labyrinth* marked English-language, *Groundhog Day* marked realistic (a time loop), *Alien* at −0.9 realistic while *2001* sat at +0.9, *The Godfather* nearly non-epic. Roughly a third of famous films had at least one broken axis.

**And the labeler's self-reported confidence was worthless:** mean 0.939, and every error above carried 0.96–0.99. Only disagreement across independent passes detects errors. Facts that are lookups — language, animation, year — should never come from a language model's memory at all.

**A labeling error is worse than it looks**, because the pair selector picks pairs by *high contrast*: a film with a wrongly extreme value is *preferentially* chosen as a probe. Bad labels don't sit still; they become bad questions.

### Eight refuted mechanisms

Each of these was a plausible causal story about why the posterior drifts. Each was tested by ablation. All eight failed.

| Hypothesis | Result |
|---|---|
| Scale update strength by pair purity | 57.4% → 57.4%, no change |
| Leave-one-out corroboration before stopping | flagged 100% of sessions — the ruler measured itself |
| Credit only the axes the pair was designed to test | made drift worse |
| Similarity bonus to the endorsed film (RBF in label space) | weak and unstable at every β |
| Whitening / Mahalanobis metric | improved 4 targets, hurt 5 |
| Freeze axes the region can't probe | target rank 164 → 229 |
| Attenuate incidental credit (1.0 / 0.5 / 0.3 / 0.0) | monotonically worse — noisy credit is still useful |
| Shared-profile term acting as a ratchet in A/B | 178 → 178 |

The unifying explanation arrived last: reason-versus-credit agreement is 9.5% against a 10.3% chance baseline. **There was no signal to recover.** No update rule can infer *why* a human chose.

### A pool "improvement" that made things worse

Rebuilding the pair pool with weighted geometry cost coverage on 8 of 10 axes (`subjective_unreality` 226 → 45 usable pairs). Cause: the coverage invariant was written as a **floor** (≥32 pairs per axis), so the optimizer satisfied the minimum and spent the rest of the pool elsewhere. **Coverage belongs in the objective function, not in a constraint.** The old pool was restored.

### A safety gate that cost more than it saved

A "blind probe" gate rejected pairs whose midpoint sat far from any high-mass candidate — pairs like "Thor or Uncharted?" on a drama night. Ablation: turning it **off** improved same-cluster accuracy from 32% to 44%. Those pairs are informative precisely *because* they get refused, and refusal suppresses a whole region. Now disabled.

### A promotion that dissolved under audit

The semantic reranking layer was promoted on 500 sessions showing +9.8 p.p. Then a validity check found that in 103 of those sessions **the target itself appeared as a probe and could be endorsed** — a channel production doesn't have, since probes are watched films and candidates aren't. On the 397 clean sessions the gain fell to +1.9 p.p., 1.05× matched random, with target-in-top-3 indistinguishable from chance. The layer remains active with its evidence explicitly marked weak.

**Check for target leakage in your evaluation harness before believing any number it produces.**

### Shadow deployment that couldn't see

The rollout plan was to run the new engine in shadow against the old one on real sessions. Structurally impossible: the new engine diverged from the legacy pair sequence at 12 of 12 pairs, so the shadow ran handcuffed — no adaptive selection, no fourth answer, no stopping, no pick. **Shadow deployment only works when the shadow can act.** For a system whose *questions* are its behavior, you need interleaving or A/B, not shadowing.

### The engine was 0.05% of the wait

For weeks the guiding principle was "zero AI inference during the quiz." It was true of the engine and **false of the transport**.

One real round, measured wall-clock from button tap to next question on screen: **179.2 seconds.**

| stage | time |
|---|---:|
| callback → agent awake | ~34.4 s |
| agent awake → handler starts | ~16.1 s |
| state loading and auxiliary commands | ~1.9 s |
| **pair selection** | **28.6 ms** |
| **media preparation** | **63.7 ms** |
| Telegram API | 1.73 s |
| LLM orchestration between commands | ~141 s |

92 milliseconds of engine inside 179,200 milliseconds of waiting. The remaining 99.95% was an agent waking up, reading its own skill file, looking up a profile, checking `--help`, and deciding what to run — on every button tap.

Every optimization done before this measurement — speculative prefetch of all four answers, vectorizing the information-gain computation, a 300 ms budget on pair selection — improved a component **three orders of magnitude smaller** than the actual bottleneck.

The fix is architectural, not incremental: a resident process that loads the runtime once and keeps it in memory, a dedicated bot so the messaging path is isolated, posters cached permanently (probe films never change), and each pair's composed image uploaded once so subsequent rounds send a reusable ID instead of bytes.

**None of the 850 synthetic sessions could have found this**, because in simulation there is no messaging layer and no agent. It took one real session.

**Generalizable lesson: measure the end-to-end path before optimizing any component.** A CPU profile of your algorithm cannot see a bottleneck that lives in transport.

### The simulator's blind spot

Synthetic personas answer by the same likelihood the engine uses, so a nonsensical pair still produces an internally coherent answer. The simulator cannot represent an *illegible question* — the automated respondent taps "neither" and moves on; a human abandons the session. Every legibility problem in this project was found by a human using it, never by 500 simulated sessions.

---

## Repository layout

```
.
├── README.md                     # this file
├── DECISIONS.md                  # full decision ledger (Portuguese — the working record)
├── PUBLISHING-PLAN.md            # clean-room extraction plan and privacy rules
├── engine/                       # transport-agnostic posterior, likelihood and quiz state
├── api/                          # three-endpoint FastAPI adapter
├── tests/                        # numerical invariants and API lifecycle
├── pyproject.toml                # package and test dependencies
├── catalog.config.json           # which lists build your recommendation catalog
├── data/
│   ├── demo/catalog.json             # runnable 12-axis demonstration bundle
│   └── labels-default-catalog.json   # 1,131 films × 11 legacy axes
└── LICENSE
```

The repository includes a clean-room implementation of the older numerical core and a deliberately small HTTP adapter. Catalog-specific runtime data is injected through `CatalogBundle`: thresholds, entropy floor, cluster structure, pair pool, priors and public metadata travel with the catalog instead of being hard-coded. No private probes, production NPZ files, session logs, agent paths or chat transport are included.

Applications create a `CatalogBundle`, call `api.main.create_app(bundle, store)`, and provide durable session storage for production; the bundled in-memory store is only for demos and tests.

## The pre-labeled catalog

`data/labels-default-catalog.json` contains **1,131 films × 11 legacy axes**, produced under the earlier `axes-v1+comic-serious-v1` rubric. It is useful as public source data, but it is not directly loadable as a current 12-axis runtime bundle. Sources are public lists only, deduplicated **by TMDb ID, never by title**. `data/demo/catalog.json` is the runnable 12-axis example.

Using it means you only pay labeling cost for films it doesn't cover — chiefly your own watched films, which are personal by definition.

## Labeling your own catalog

1. Resolve every film to a TMDb ID; dedupe by ID.
2. Pull language, animation status and year **from TMDb**, not from the model.
3. Label the remaining axes in three passes, median per axis; disagreement across passes is your confidence signal.
4. Include the 15 control films in every batch; reject the batch on drift.
5. Adding an axis? Check its correlation against existing probing dimensions. At |r| ≥ 0.85 it stays as a matching label and never earns quiz questions.
6. Rebuild clusters, entropy floor, δ and stopping thresholds afterward — **thresholds are catalog-specific and do not transfer.**

Keep one rubric version per catalog build. Mixed-rubric labels are the quiet killer of pair quality.

## Restricting to a single list

The engine is catalog-agnostic: point the posterior at any labeled candidate set and keep your watched films as probes. That makes "only recommend from this specific list" a configuration, not a feature.

Three traps, all paid for in practice:

- **An impossible threshold.** A stopping rule expressed as an *absolute* number of effective candidates can sit **below the catalog's entropy floor**, in which case it never fires. Symptom: a sweep over seven threshold values returning identical results on every row. Always express thresholds as a multiple of the floor.
- **A disproportionate round cap.** With 50 candidates and a floor near 7, the instrument cannot resolve better than ~7 films. Spending 14 rounds on that is waste; 8 suffices.
- **Semantic reranking may not help small catalogs.** In a 50-film context it scored 48% against 48.7% for matched random — nothing. Test per context.

Two baselines decide whether a context is worth shipping: three random films from the whole catalog (does the quiz do anything at all?) and random within the rerank window (does the semantic layer earn its place?). In the 50-film context the quiz cleared the first comfortably — 44% versus 30.5%, target-in-top-3 12% versus 6.1% — and failed the second, so it shipped without reranking.

## Honest limitations

- **Instrument resolution is roughly the top 10% of the catalog**, measured five independent times. Chasing exact top-1 is wasted effort.
- **The stopping rule rarely fires at large catalog sizes** (94% ceiling rate). Unsolved.
- **Same-cluster metrics are not comparable across catalogs** — random baselines differ (30.5% at 9 clusters, 3.41% at 80). Report ratio over the catalog-appropriate random control, plus normalized lift.
- **The engine has no demonstrated advantage over a no-quiz taste-profile baseline at large catalog size.**
- **Validation is synthetic-first.** Real ground truth accumulates from post-film feedback, one tap at a time.
- **Similarity to endorsed films optimizes for familiarity**, which may suppress discovery. If recommendations start feeling predictable, the semantic layer is the first suspect.

## License

MIT.

## Acknowledgments

Built through a long dialogue between a human product owner and two AI agents — one designing and reviewing, one implementing and pushing back. Most of the good decisions in this document came from the implementing agent refuting the reviewer's proposal with data, or from the human noticing that a recommendation made no sense before any metric said so. The receipts are in `DECISIONS.md`.

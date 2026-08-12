from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from engine import Answer, QuizEngine


def test_bundle_rejects_unreachable_confidence_threshold(bundle) -> None:
    stop_rule = replace(bundle.stop_rule, entropy_floor_multiple=0.49)

    with pytest.raises(ValueError, match="confidence entropy threshold is unreachable"):
        replace(bundle, stop_rule=stop_rule)


def test_bundle_accepts_minimum_reachable_confidence_threshold(bundle) -> None:
    stop_rule = replace(bundle.stop_rule, entropy_floor_multiple=0.5)

    replace(bundle, stop_rule=stop_rule)


def test_bundle_rejects_entropy_floor_above_candidate_count(bundle) -> None:
    with pytest.raises(ValueError, match="entropy_floor cannot exceed"):
        replace(bundle, entropy_floor=len(bundle.candidate_ids) + 0.01)


def test_bundle_rejects_invalid_variety_parameters(bundle) -> None:
    with pytest.raises(ValueError, match="near_optimal_epsilon"):
        replace(bundle, near_optimal_epsilon=0)
    with pytest.raises(ValueError, match="cannot exceed pair_pool"):
        replace(bundle, opening_min_candidates=len(bundle.pair_pool) + 1)


def test_same_seed_replays_and_different_seeds_vary_opening(bundle) -> None:
    engine = QuizEngine(bundle)
    expected = engine.next_pair(engine.start("same-session"))
    assert engine.next_pair(engine.start("same-session")) == expected

    openings = {
        engine.next_pair(engine.start(f"session-{index}"))[:2]
        for index in range(20)
    }
    assert len(openings) > 1


def test_round_updates_posterior_and_never_reuses_probe(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start()
    left, right, gain = engine.next_pair(state)
    before = state.posterior.copy()
    engine.answer(state, (left, right), Answer.A)
    assert gain >= 0
    assert state.round == 1
    assert np.isclose(state.posterior.sum(), 1.0)
    assert not np.allclose(state.posterior, before)
    next_left, next_right, _ = engine.next_pair(state)
    assert {left, right}.isdisjoint({next_left, next_right})


def test_open_pair_is_stable_and_rejects_a_different_pair(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start()
    open_pair = engine.next_pair(state)
    assert engine.next_pair(state) == open_pair

    different = next(
        (bundle.probe_ids[int(left)], bundle.probe_ids[int(right)])
        for left, right in bundle.pair_pool
        if (bundle.probe_ids[int(left)], bundle.probe_ids[int(right)])
        != open_pair[:2]
    )
    with np.testing.assert_raises_regex(ValueError, "not the open pair"):
        engine.answer(state, different, Answer.A)
    assert state.round == 0
    assert engine.next_pair(state) == open_pair


def test_catalog_specific_ceiling_extends_for_neither(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start()
    for answer in (Answer.NEITHER, Answer.A, Answer.B):
        left, right, _ = engine.next_pair(state)
        engine.answer(state, (left, right), answer)
    assert not state.stopped  # base ceiling 3 + one neither extension
    left, right, _ = engine.next_pair(state)
    engine.answer(state, (left, right), Answer.A)
    assert state.stopped
    assert state.stop_reason == "ceiling"


def test_ranked_candidates_include_public_metadata(bundle) -> None:
    engine = QuizEngine(bundle)
    rows = engine.ranked_candidates(engine.start(), limit=1)
    assert rows[0]["id"] == "c7"  # stable argsort tie behavior
    assert "posterior" in rows[0]


def test_duration_is_inclusive_and_missing_metadata_fails_open(bundle) -> None:
    metadata = {
        candidate_id: {**bundle.metadata.get(candidate_id, {})}
        for candidate_id in bundle.candidate_ids
    }
    metadata["c0"]["runtime_minutes"] = 90
    metadata["c1"]["runtime_minutes"] = 91
    metadata["c2"]["availability"] = []  # availability is informative only
    engine = QuizEngine(replace(bundle, metadata=metadata))

    state = engine.start(duration_ceiling=90)

    assert state.eligibility_mask[0]
    assert not state.eligibility_mask[1]
    assert state.eligibility_mask[2]  # missing runtime and no availability
    assert np.isclose(state.posterior[~state.eligibility_mask].sum(), 0.0)


def test_mask_is_applied_before_ranking_on_full_catalog(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start()
    state.posterior = np.asarray([.30, .25, .20, .10, .06, .04, .03, .02])
    state.eligibility_mask = np.asarray(
        [False, False, False, False, False, True, True, True]
    )

    rows = engine.ranked_candidates(state, limit=2)

    # Ranking first would take c0/c1 and filtering afterward would return none.
    assert [row["id"] for row in rows] == ["c5", "c6"]


def test_mask_recomputes_entropy_floor_and_delta(bundle) -> None:
    metadata = {
        candidate_id: {
            **bundle.metadata.get(candidate_id, {}),
            "runtime_minutes": 200 if index >= 4 else 100,
        }
        for index, candidate_id in enumerate(bundle.candidate_ids)
    }
    state = QuizEngine(replace(bundle, metadata=metadata)).start(
        duration_ceiling=150
    )

    assert state.entropy_floor == 2.0  # two surviving clusters of size two
    assert state.delta90 > 0


def test_empty_eligibility_mask_has_clear_error(bundle) -> None:
    metadata = {
        candidate_id: {"runtime_minutes": 200}
        for candidate_id in bundle.candidate_ids
    }
    engine = QuizEngine(replace(bundle, metadata=metadata))

    with pytest.raises(ValueError, match="removed every candidate"):
        engine.start(duration_ceiling=90)


def test_eligibility_build_invariants(bundle) -> None:
    from engine import EligibilityPolicy

    with pytest.raises(ValueError, match="cannot exceed the candidate count"):
        replace(
            bundle,
            eligibility=EligibilityPolicy(
                sanity_floor=len(bundle.candidate_ids) + 1,
                direct_pick_below=2,
            ),
        )
    with pytest.raises(ValueError, match="cannot exceed sanity_floor"):
        EligibilityPolicy(sanity_floor=3, direct_pick_below=4)


def test_small_eligible_set_warns_and_can_skip_quiz(bundle) -> None:
    metadata = {
        candidate_id: {"runtime_minutes": 200}
        for candidate_id in bundle.candidate_ids
    }
    metadata["c0"]["runtime_minutes"] = 90
    state = QuizEngine(replace(bundle, metadata=metadata)).start(
        duration_ceiling=90
    )

    assert state.eligibility_warning
    assert state.direct_pick
    assert state.stopped
    assert state.stop_reason == "direct_pick"


def test_pick_order_is_frozen_and_skip_logs_original_rank(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start()
    state.stopped = True
    state.posterior = np.asarray([.30, .25, .20, .10, .06, .04, .03, .02])
    first = engine.current_pick(state)
    frozen = list(state.frozen_pick_order)

    state.posterior = state.posterior[::-1].copy()
    second = engine.skip_pick(state)

    assert state.frozen_pick_order == frozen
    assert state.pick_skips == [{
        "candidateId": first["id"],
        "rankPosition": first["rankPosition"],
    }]
    assert second["id"] == frozen[1]["id"]


def test_pick_order_deduplicates_franchise_and_flags_sixth(bundle) -> None:
    metadata = {
        candidate_id: {**bundle.metadata.get(candidate_id, {})}
        for candidate_id in bundle.candidate_ids
    }
    metadata["c7"]["franchise"] = "Same Series"
    metadata["c6"]["franchise"] = "same series"
    engine = QuizEngine(replace(bundle, metadata=metadata))
    state = engine.start()
    state.stopped = True

    order = engine.prepare_pick_order(state)
    assert not ({"c6", "c7"} <= {str(row["id"]) for row in order})
    for _ in range(5):
        engine.skip_pick(state)
    assert engine.current_pick(state)["lowConfidence"]


def test_only_explicit_acceptance_counts(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start()
    state.stopped = True
    engine.current_pick(state)
    assert state.accepted_pick is None

    accepted = engine.accept_pick(state)

    assert accepted == state.accepted_pick


def test_semantic_rerank_uses_endorsed_minus_none_inside_window(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start()
    state.stopped = True
    state.posterior = np.asarray([.30, .25, .20, .10, .06, .04, .03, .02])
    state.endorsed_probes = [1]
    state.rejected_probes = [0]
    posterior_top3 = [row["id"] for row in engine.ranked_candidates(state, 3)]

    reranked = engine.prepare_pick_order(state)

    assert {row["id"] for row in reranked[:3]} == set(posterior_top3)
    assert [row["id"] for row in reranked[:3]] != posterior_top3
    assert [row["id"] for row in reranked[3:]] == [
        row["id"] for row in engine.ranked_candidates(state, 8)[3:]
    ]


def test_phase_transition_uses_mass_without_ab_coherence(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start()
    state.posterior = np.asarray([.45, .45, .025, .025, .025, .01, .01, .005])
    state.answers = [Answer.NEITHER, Answer.NEITHER]

    engine._apply_phase_rule(state)

    assert state.phase == "fine"
    assert state.localized_clusters


def test_phase_stays_coarse_below_both_mass_gates(bundle) -> None:
    from engine import PhasePolicy

    engine = QuizEngine(replace(
        bundle,
        phase=PhasePolicy(top1_mass=.6, top3_mass=.9),
    ))
    state = engine.start()
    state.posterior = np.full(8, 1 / 8)
    engine._apply_phase_rule(state)
    assert state.phase == "coarse"


def test_neither_records_refused_midpoint_and_dominant_axis(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start("history")
    left, right, _ = engine.next_pair(state)
    left_index = bundle.probe_ids.index(left)
    right_index = bundle.probe_ids.index(right)
    engine.answer(state, (left, right), Answer.NEITHER)
    np.testing.assert_allclose(
        state.refused_midpoints[0],
        (bundle.probe_vectors[left_index] + bundle.probe_vectors[right_index]) / 2,
    )
    assert state.recent_dominant_axes[-1] == int(np.argmax(np.abs(
        bundle.probe_vectors[left_index] - bundle.probe_vectors[right_index]
    )))


def test_repeated_axis_filter_relaxes_when_no_alternative(bundle) -> None:
    engine = QuizEngine(bundle)
    state = engine.start("relax")
    state.recent_dominant_axes = list(range(bundle.candidate_vectors.shape[1]))
    assert engine.next_pair(state)

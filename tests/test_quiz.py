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

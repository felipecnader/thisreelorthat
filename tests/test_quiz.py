from __future__ import annotations

import numpy as np

from engine import Answer, QuizEngine


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

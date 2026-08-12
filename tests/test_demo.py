from __future__ import annotations

from fastapi.testclient import TestClient

from api.demo import app, load_demo_bundle
from engine import Answer, QuizEngine


def test_demo_has_real_axis_shape_and_disjoint_catalogs() -> None:
    bundle = load_demo_bundle()
    assert bundle.probe_vectors.shape == (12, 12)
    assert bundle.candidate_vectors.shape == (12, 12)
    assert bundle.candidate_embeddings.shape == (12, 8)
    assert bundle.probe_embeddings.shape == (12, 8)
    assert bundle.embedding_provenance["model"] == "synthetic-deterministic-v1"
    # These synthetic vectors prove bundle mechanics only, not rerank quality.
    assert set(bundle.probe_ids).isdisjoint(bundle.candidate_ids)


def test_demo_runs_from_first_pair_to_ranked_pick() -> None:
    client = TestClient(app)
    response = client.post("/sessions")
    assert response.status_code == 201
    state = response.json()

    while state["status"] == "active":
        pair = state["pair"]
        response = client.post(
            f"/sessions/{state['sessionId']}/answers",
            json={
                "left": pair["left"],
                "right": pair["right"],
                "answer": "a",
            },
        )
        assert response.status_code == 200
        state = response.json()

    assert state["round"] == 6
    assert state["stopReason"] == "ceiling"
    assert {"id", "title", "year", "posterior"} <= state["pick"].keys()


def test_demo_confidence_path_is_reachable() -> None:
    engine = QuizEngine(load_demo_bundle())
    state = engine.start()

    for answer in (Answer.A, Answer.A, Answer.A, Answer.A, Answer.B, Answer.A):
        pair = engine.next_pair(state)[:2]
        engine.answer(state, pair, answer)
        if state.stopped:
            break

    assert state.stop_reason == "confidence"

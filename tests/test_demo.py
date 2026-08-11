from __future__ import annotations

from fastapi.testclient import TestClient

from api.demo import app, load_demo_bundle


def test_demo_has_real_axis_shape_and_disjoint_catalogs() -> None:
    bundle = load_demo_bundle()
    assert bundle.probe_vectors.shape == (12, 12)
    assert bundle.candidate_vectors.shape == (12, 12)
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
    assert len(state["candidates"]) == 12
    assert {"id", "title", "year", "posterior"} <= state["candidates"][0].keys()

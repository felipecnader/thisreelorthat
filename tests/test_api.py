from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app


def test_session_lifecycle(bundle) -> None:
    client = TestClient(create_app(bundle))
    started = client.post("/sessions")
    assert started.status_code == 201
    body = started.json()
    session_id = body["sessionId"]
    assert body["status"] == "active"

    fetched = client.get(f"/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["pair"] == body["pair"]

    pair = body["pair"]
    answered = client.post(
        f"/sessions/{session_id}/answers",
        json={"left": pair["left"], "right": pair["right"], "answer": "a"},
    )
    assert answered.status_code == 200
    assert answered.json()["round"] == 1


def test_unknown_session_is_404(bundle) -> None:
    client = TestClient(create_app(bundle))
    assert client.get("/sessions/missing").status_code == 404


def test_stale_or_mismatched_pair_is_409_without_advancing(bundle) -> None:
    client = TestClient(create_app(bundle))
    started = client.post("/sessions").json()
    session_id = started["sessionId"]
    open_pair = started["pair"]
    mismatched_pair = next(
        {
            "left": bundle.probe_ids[int(left)],
            "right": bundle.probe_ids[int(right)],
        }
        for left, right in bundle.pair_pool
        if (
            bundle.probe_ids[int(left)] != open_pair["left"]
            or bundle.probe_ids[int(right)] != open_pair["right"]
        )
    )

    mismatch = client.post(
        f"/sessions/{session_id}/answers",
        json={**mismatched_pair, "answer": "a"},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"] == "submitted pair is not the open pair"
    unchanged = client.get(f"/sessions/{session_id}").json()
    assert unchanged["round"] == 0
    assert unchanged["pair"] == open_pair

    accepted = client.post(
        f"/sessions/{session_id}/answers",
        json={
            "left": open_pair["left"],
            "right": open_pair["right"],
            "answer": "a",
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["round"] == 1

    duplicate = client.post(
        f"/sessions/{session_id}/answers",
        json={
            "left": open_pair["left"],
            "right": open_pair["right"],
            "answer": "a",
        },
    )
    assert duplicate.status_code == 409
    assert client.get(f"/sessions/{session_id}").json()["round"] == 1

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

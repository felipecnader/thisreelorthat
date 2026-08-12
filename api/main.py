"""FastAPI adapter with three deliberately small endpoints.

Applications normally call ``create_app(bundle)`` and supply their own
catalog-specific bundle. Session persistence is an injected interface; the
default store is process-local and intended for demos/tests only.
"""

from __future__ import annotations

from threading import RLock
from typing import Protocol
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from engine import Answer, CatalogBundle, QuizEngine, QuizState


class SessionStore(Protocol):
    def get(self, session_id: str) -> QuizState | None: ...
    def put(self, session_id: str, state: QuizState) -> None: ...


class MemorySessionStore:
    def __init__(self) -> None:
        self._states: dict[str, QuizState] = {}
        self._lock = RLock()

    def get(self, session_id: str) -> QuizState | None:
        with self._lock:
            return self._states.get(session_id)

    def put(self, session_id: str, state: QuizState) -> None:
        with self._lock:
            self._states[session_id] = state


class AnswerRequest(BaseModel):
    left: str
    right: str
    answer: str


def create_app(bundle: CatalogBundle, store: SessionStore | None = None) -> FastAPI:
    engine = QuizEngine(bundle)
    sessions = store or MemorySessionStore()
    answer_lock = RLock()
    app = FastAPI(title="ThisReelOrThat", version="0.1.0")

    def present(session_id: str, state: QuizState) -> dict[str, object]:
        response: dict[str, object] = {
            "sessionId": session_id,
            "round": state.round,
            "status": "complete" if state.stopped else "active",
            "stopReason": state.stop_reason,
            "metrics": engine.metrics(state),
        }
        if state.stopped:
            response["candidates"] = engine.ranked_candidates(state)
        else:
            left, right, gain = engine.next_pair(state)
            response["pair"] = {"left": left, "right": right, "informationGain": gain}
        return response

    @app.post("/sessions", status_code=201)
    def start_session(duration_ceiling: int | None = None) -> dict[str, object]:
        session_id = uuid4().hex
        try:
            state = engine.start(
                session_id, duration_ceiling=duration_ceiling
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        response = present(session_id, state)
        sessions.put(session_id, state)
        return response

    @app.post("/sessions/{session_id}/answers")
    def record_answer(session_id: str, request: AnswerRequest) -> dict[str, object]:
        choices = {"a": Answer.A, "b": Answer.B, "either": Answer.EITHER, "neither": Answer.NEITHER}
        if request.answer not in choices:
            raise HTTPException(status_code=422, detail="invalid answer")
        with answer_lock:
            state = sessions.get(session_id)
            if state is None:
                raise HTTPException(status_code=404, detail="session not found")
            try:
                engine.answer(state, (request.left, request.right), choices[request.answer])
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            response = present(session_id, state)
            sessions.put(session_id, state)
            return response

    @app.get("/sessions/{session_id}")
    def get_session(session_id: str) -> dict[str, object]:
        with answer_lock:
            state = sessions.get(session_id)
            if state is None:
                raise HTTPException(status_code=404, detail="session not found")
            response = present(session_id, state)
            sessions.put(session_id, state)
            return response

    return app

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from api.mood import prepare_mood
from engine import (
    MoodComponent,
    MoodFilterPolicy,
    PreparedMood,
    QuizEngine,
    mood_mask,
)


def prepared(*components: MoodComponent, vectors=()) -> PreparedMood:
    array = np.asarray(vectors, dtype=float)
    if not len(array):
        array = np.empty((0, 0))
    return PreparedMood("test", components, array)


def test_components_combine_by_minimum_not_average(bundle) -> None:
    mood = prepared(
        MoodComponent(route="axis", axis="tone", direction="light"),
        MoodComponent(route="axis", axis="pace", direction="light"),
    )
    result = mood_mask(bundle, mood)
    np.testing.assert_allclose(
        result.scores, np.min(result.component_scores, axis=1)
    )
    assert result.audit["aggregation"] == "minimum"


def test_all_four_routes_are_scored_and_unrepresentable_warns(bundle) -> None:
    attributes = {
        candidate: {
            "genres": ["crime"] if index < 5 else ["drama"],
            "popularity": float(index + 1),
            "runtime_minutes": 80 + index,
        }
        for index, candidate in enumerate(bundle.candidate_ids)
    }
    routed = replace(bundle, candidate_attributes=attributes)
    mood = prepared(
        MoodComponent(route="axis", axis="pace", direction="light"),
        MoodComponent(route="embedding", text="organized crime"),
        MoodComponent(route="genre", genre="crime"),
        MoodComponent(route="metadata", metadata="popularity", level="high"),
        MoodComponent(route="unrepresentable", attribute="visual beauty"),
        vectors=[[1.0, 0.0, 0.0]],
    )
    result = mood_mask(routed, mood)
    assert result.applied
    assert result.component_scores.shape == (8, 4)
    assert "visual beauty" in str(result.warning)
    assert result.audit["unrepresentable"] == ["visual beauty"]


def test_small_factual_genre_set_direct_picks_and_recalibrates(bundle) -> None:
    attributes = {
        candidate: {
            "genres": ["western"] if index == 3 else ["drama"],
            "popularity": None,
            "runtime_minutes": None,
        }
        for index, candidate in enumerate(bundle.candidate_ids)
    }
    routed = replace(bundle, candidate_attributes=attributes)
    mood = prepared(MoodComponent(route="genre", genre="western"))
    state = QuizEngine(routed).start(mood=mood)
    assert state.stopped and state.direct_pick
    assert state.stop_reason == "direct_pick"
    assert int(state.eligibility_mask.sum()) == 1
    assert state.entropy_floor == 1.0
    assert state.delta90 == 0.0
    assert "só 1 filmes casam" in str(state.mood_warning)


def test_unrepresentable_only_fails_open_with_warning(bundle) -> None:
    mood = prepared(
        MoodComponent(route="unrepresentable", attribute="visual beauty")
    )
    result = mood_mask(bundle, mood)
    assert not result.applied
    assert np.all(result.mask)
    assert result.audit["reason"] == "no_representable_components"


def test_metadata_with_no_coverage_fails_open(bundle) -> None:
    mood = prepared(
        MoodComponent(route="metadata", metadata="popularity", level="high")
    )
    result = mood_mask(bundle, mood)
    assert not result.applied
    assert np.all(result.mask)
    assert result.audit["reason"] == "metadata_unavailable"


def test_provider_boundary_injects_only_components_and_vectors() -> None:
    class Routes:
        def decompose(self, text: str):
            return [MoodComponent(route="embedding", text=f"theme: {text}")]

    class Vectors:
        def embed(self, text: str):
            return [1.0, 2.0, 3.0]

    mood = prepare_mood(
        "mafia", mood_provider=Routes(), embedding_provider=Vectors()
    )
    assert mood.components[0].text == "theme: mafia"
    np.testing.assert_allclose(
        mood.embedding_vectors, np.asarray([[1.0, 2.0, 3.0]]) / np.sqrt(14)
    )


def test_mood_policy_build_invariants(bundle) -> None:
    with pytest.raises(ValueError, match="minimum_candidates"):
        replace(bundle, mood_filter=MoodFilterPolicy(minimum_candidates=99))
    with pytest.raises(ValueError, match="catalog_fraction"):
        MoodFilterPolicy(minimum_candidates=1, catalog_fraction=0)

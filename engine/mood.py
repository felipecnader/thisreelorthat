"""Pure candidate scoring and masking for a declared movie mood."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

from .bundle import CatalogBundle, FloatArray


Route = Literal["axis", "embedding", "genre", "metadata", "unrepresentable"]


@dataclass(frozen=True)
class MoodComponent:
    route: Route
    axis: str | None = None
    direction: str | None = None
    text: str | None = None
    genre: str | None = None
    metadata: str | None = None
    level: str | None = None
    attribute: str | None = None

    def __post_init__(self) -> None:
        required = {
            "axis": (self.axis, self.direction),
            "embedding": (self.text,),
            "genre": (self.genre,),
            "metadata": (self.metadata, self.level),
            "unrepresentable": (self.attribute,),
        }[self.route]
        if any(value is None or not str(value).strip() for value in required):
            raise ValueError(f"{self.route} component is incomplete")


@dataclass(frozen=True)
class PreparedMood:
    text: str
    components: tuple[MoodComponent, ...]
    embedding_vectors: FloatArray

    def __post_init__(self) -> None:
        vectors = np.asarray(self.embedding_vectors, dtype=float)
        object.__setattr__(self, "embedding_vectors", vectors)
        expected = sum(row.route == "embedding" for row in self.components)
        if vectors.ndim != 2 or len(vectors) != expected:
            raise ValueError("one embedding vector is required per embedding component")
        if expected and (
            not np.all(np.isfinite(vectors))
            or np.any(np.linalg.norm(vectors, axis=1) <= 0)
        ):
            raise ValueError("mood embeddings must be finite and nonzero")


@dataclass(frozen=True)
class MoodMaskResult:
    mask: np.ndarray
    scores: FloatArray
    component_scores: FloatArray
    applied: bool
    warning: str | None
    audit: dict[str, object]


def _percentile(values: FloatArray) -> FloatArray:
    order = np.argsort(values, kind="stable")
    result = np.empty(len(values), dtype=float)
    result[order] = (np.arange(len(values), dtype=float) + 0.5) / len(values)
    return result


def mood_mask(bundle: CatalogBundle, mood: PreparedMood) -> MoodMaskResult:
    """Score every candidate, combine requirements by minimum, then mask.

    Minimum is intentionally conjunctive. With an average, The Conversation
    (low scale/high cerebral) and The Raid (high scale/low cerebral) can tie
    Oppenheimer (high/high). Minimum keeps only the candidate satisfying both
    requirements near the top; replacing it with a mean reintroduces that bug.
    """
    represented = [row for row in mood.components if row.route != "unrepresentable"]
    ignored = [
        str(row.attribute) for row in mood.components
        if row.route == "unrepresentable"
    ]
    full = np.ones(len(bundle.candidate_ids), dtype=bool)
    if not represented:
        warning = (
            "não sei filtrar por " + ", ".join(ignored)
            if ignored else None
        )
        return MoodMaskResult(
            full, np.ones(len(full)), np.empty((len(full), 0)), False,
            warning, {"applied": False, "reason": "no_representable_components",
                      "unrepresentable": ignored},
        )

    axis_sign = {
        "heavy": -1, "light": 1, "intimate": -1, "epic": 1,
        "literal": -1, "impossible": 1, "objective": -1, "subjective": 1,
        "slow": -1, "propulsive": 1, "cerebral": -1, "emotional": 1,
        "gray": -1, "cathartic": 1, "classic": -1, "contemporary": 1,
        "animation": -1, "live_action": 1, "demanding": -1, "casual": 1,
        "english": -1, "international": 1, "comic": -1, "serious": 1,
    }
    scores: list[np.ndarray] = []
    embedding_cursor = 0
    has_genre = False
    for component in represented:
        if component.route == "axis":
            if component.axis not in bundle.axis_names:
                raise ValueError(f"unknown mood axis: {component.axis}")
            if component.direction not in axis_sign:
                raise ValueError(f"unknown mood axis direction: {component.direction}")
            column = bundle.axis_names.index(str(component.axis))
            raw = bundle.candidate_vectors[:, column] * axis_sign[str(component.direction)]
            scores.append(_percentile(raw))
        elif component.route == "embedding":
            query = mood.embedding_vectors[embedding_cursor].astype(np.float32)
            embedding_cursor += 1
            if query.shape != (bundle.candidate_embeddings.shape[1],):
                raise ValueError("mood and candidate embedding dimensions differ")
            # Embedding providers/builders own normalization. Production stores
            # normalized float32 vectors and computes cosine as this dot product;
            # renormalizing here changes stable tie order at catalog scale.
            matrix = bundle.candidate_embeddings.astype(np.float32)
            cosine = matrix @ query
            scores.append(_percentile(cosine))
        elif component.route == "genre":
            genre = str(component.genre).casefold()
            values = np.asarray([
                float(genre in {
                    str(item).casefold() for item in
                    (bundle.candidate_attributes[candidate].get("genres") or [])
                })
                for candidate in bundle.candidate_ids
            ])
            has_genre = True
            scores.append(values)
        elif component.route == "metadata":
            if component.metadata not in {"popularity", "runtime_minutes"}:
                raise ValueError(f"unsupported mood metadata: {component.metadata}")
            if component.level not in {"high", "low"}:
                raise ValueError(f"unsupported metadata level: {component.level}")
            raw = np.asarray([
                bundle.candidate_attributes[candidate].get(str(component.metadata))
                for candidate in bundle.candidate_ids
            ], dtype=object)
            known = np.asarray([value is not None for value in raw])
            if not np.any(known):
                return MoodMaskResult(
                    full, np.ones(len(full)), np.empty((len(full), 0)), False,
                    None, {"applied": False, "reason": "metadata_unavailable",
                           "metadata": component.metadata},
                )
            values = np.zeros(len(raw), dtype=float)
            numeric = np.asarray(raw[known], dtype=float)
            directed = numeric if component.level == "high" else -numeric
            values[known] = _percentile(directed)
            scores.append(values)

    component_scores = np.asarray(scores).T
    final_score = np.min(component_scores, axis=1)
    requested = max(
        bundle.mood_filter.minimum_candidates,
        int(math.ceil(bundle.mood_filter.catalog_fraction * len(full))),
    )
    positive = int(np.sum(final_score > 0))
    count = min(requested, positive if has_genre else len(full))
    if count == 0:
        return MoodMaskResult(
            full, final_score, component_scores, False, None,
            {"applied": False, "reason": "genre_has_no_catalog_matches"},
        )
    selected = np.argsort(final_score, kind="stable")[::-1][:count]
    mask = np.zeros(len(full), dtype=bool)
    mask[selected] = True
    warning_parts = []
    if ignored:
        warning_parts.append("não sei filtrar por " + ", ".join(ignored))
    if count < bundle.eligibility.direct_pick_below:
        warning_parts.append(
            f"só {count} filmes casam com {mood.text}, então fui direto ao ponto"
        )
    elif count < bundle.mood_filter.small_set_alert:
        warning_parts.append(f"conjunto de mood pequeno: {count} filmes elegíveis")
    warning = "; ".join(warning_parts) if warning_parts else None
    return MoodMaskResult(
        mask, final_score, component_scores, True, warning,
        {
            "applied": True, "policy": "top_n_hard_mask",
            "aggregation": "minimum", "requestedCandidates": requested,
            "eligibleCandidates": count, "componentCount": len(represented),
            "unrepresentable": ignored,
            "intentionalSmallGenreSet": bool(has_genre and count < requested),
            "smallSetAlert": bool(count < bundle.mood_filter.small_set_alert),
            "directPick": bool(count < bundle.eligibility.direct_pick_below),
        },
    )

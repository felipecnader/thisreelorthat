"""Stateful orchestration over the transport-free numerical engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from .bundle import CatalogBundle
from .math import (
    cluster_mass,
    entropy,
    expected_information_gain,
    likelihood,
    pair_features,
    update,
)
from .selection import near_optimal_index


class Answer(IntEnum):
    A = 0
    B = 1
    EITHER = 2
    NEITHER = 3


@dataclass
class QuizState:
    posterior: np.ndarray
    selection_seed: str = "reference"
    round: int = 0
    used_probes: set[int] = field(default_factory=set)
    answers: list[Answer] = field(default_factory=list)
    pending_pair: tuple[str, str] | None = None
    pending_information_gain: float | None = None
    stopped: bool = False
    stop_reason: str | None = None


class QuizEngine:
    def __init__(self, bundle: CatalogBundle):
        self.bundle = bundle
        params = bundle.parameters
        rows = []
        for left, right in bundle.pair_pool:
            preference, shared = pair_features(
                bundle.cluster_centers,
                bundle.probe_vectors[int(left)],
                bundle.probe_vectors[int(right)],
            )
            rows.append(
                likelihood(
                    preference,
                    shared,
                    kappa=params.kappa,
                    evidence_cap=params.evidence_cap,
                    tie_sigma=params.tie_sigma,
                )
            )
        self._cluster_likelihoods = np.asarray(rows)

    def start(self, selection_seed: str = "reference") -> QuizState:
        if not selection_seed:
            raise ValueError("selection_seed must not be empty")
        return QuizState(
            posterior=self.bundle.prior.copy(),
            selection_seed=selection_seed,
        )

    def next_pair(self, state: QuizState) -> tuple[str, str, float]:
        if state.stopped:
            raise ValueError("quiz has stopped")
        if state.pending_pair is not None:
            assert state.pending_information_gain is not None
            return (*state.pending_pair, state.pending_information_gain)
        cluster_posterior = cluster_mass(
            state.posterior,
            self.bundle.cluster_labels,
            len(self.bundle.cluster_centers),
        )
        gains = expected_information_gain(cluster_posterior, self._cluster_likelihoods)
        if state.used_probes:
            unavailable = np.asarray(
                [
                    int(left) in state.used_probes or int(right) in state.used_probes
                    for left, right in self.bundle.pair_pool
                ]
            )
            gains[unavailable] = -np.inf
        index = near_optimal_index(
            gains,
            self.bundle.pair_pool,
            epsilon=self.bundle.near_optimal_epsilon,
            opening_min_candidates=self.bundle.opening_min_candidates,
            selection_seed=state.selection_seed,
            round_number=state.round + 1,
        )
        left, right = map(int, self.bundle.pair_pool[index])
        state.pending_pair = (
            self.bundle.probe_ids[left], self.bundle.probe_ids[right]
        )
        state.pending_information_gain = float(gains[index])
        return (*state.pending_pair, state.pending_information_gain)

    def answer(self, state: QuizState, pair: tuple[str, str], answer: Answer) -> QuizState:
        if state.stopped:
            raise ValueError("quiz has stopped")
        if state.pending_pair is None:
            raise ValueError("quiz has no open pair")
        if pair != state.pending_pair:
            raise ValueError("submitted pair is not the open pair")
        index = {slug: i for i, slug in enumerate(self.bundle.probe_ids)}
        try:
            left, right = index[pair[0]], index[pair[1]]
        except KeyError as exc:
            raise ValueError("unknown probe") from exc
        if left in state.used_probes or right in state.used_probes:
            raise ValueError("probe has already been used")

        preference, shared = pair_features(
            self.bundle.candidate_vectors,
            self.bundle.probe_vectors[left],
            self.bundle.probe_vectors[right],
        )
        params = self.bundle.parameters
        table = likelihood(
            preference,
            shared,
            kappa=params.kappa,
            evidence_cap=params.evidence_cap,
            tie_sigma=params.tie_sigma,
        )
        state.posterior = update(state.posterior, table[:, int(answer)], params.beta)
        state.round += 1
        state.used_probes.update((left, right))
        state.answers.append(answer)
        state.pending_pair = None
        state.pending_information_gain = None
        self._apply_stop_rule(state)
        return state

    def metrics(self, state: QuizState) -> dict[str, float | bool]:
        pc = cluster_mass(
            state.posterior,
            self.bundle.cluster_labels,
            len(self.bundle.cluster_centers),
        )
        rule = self.bundle.stop_rule
        top = min(3, len(pc))
        top_mass = float(np.sort(pc)[-top:].sum())
        relative_entropy = float(np.exp(entropy(state.posterior)) / self.bundle.entropy_floor)
        return {
            "topClusterMass": top_mass,
            "entropyFloorMultiple": relative_entropy,
            "thresholdMet": bool(
                top_mass >= rule.top_cluster_mass
                and relative_entropy <= rule.entropy_floor_multiple
            ),
        }

    def ranked_candidates(self, state: QuizState, limit: int = 30) -> list[dict[str, object]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        order = np.argsort(state.posterior)[::-1][:limit]
        rows = []
        for i in order:
            candidate_id = self.bundle.candidate_ids[int(i)]
            rows.append(
                {
                    "id": candidate_id,
                    "posterior": float(state.posterior[int(i)]),
                    **self.bundle.metadata.get(candidate_id, {}),
                }
            )
        return rows

    def _apply_stop_rule(self, state: QuizState) -> None:
        rule = self.bundle.stop_rule
        none_count = sum(answer is Answer.NEITHER for answer in state.answers)
        ceiling = rule.base_max_rounds + min(none_count, rule.max_none_extension)
        metrics = self.metrics(state)
        if state.round >= rule.min_rounds and bool(metrics["thresholdMet"]):
            state.stopped = True
            state.stop_reason = "confidence"
        elif state.round >= ceiling:
            state.stopped = True
            state.stop_reason = "ceiling"

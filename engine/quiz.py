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
    eligibility_mask: np.ndarray
    entropy_floor: float
    delta90: float
    eligibility_warning: bool
    direct_pick: bool
    selection_seed: str = "reference"
    round: int = 0
    used_probes: set[int] = field(default_factory=set)
    answers: list[Answer] = field(default_factory=list)
    pending_pair: tuple[str, str] | None = None
    pending_information_gain: float | None = None
    stopped: bool = False
    stop_reason: str | None = None
    frozen_pick_order: list[dict[str, object]] = field(default_factory=list)
    pick_cursor: int = 0
    pick_skips: list[dict[str, object]] = field(default_factory=list)
    accepted_pick: dict[str, object] | None = None


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

    def start(
        self,
        selection_seed: str = "reference",
        *,
        duration_ceiling: int | None = None,
    ) -> QuizState:
        if not selection_seed:
            raise ValueError("selection_seed must not be empty")
        mask = self.eligibility_mask(duration_ceiling=duration_ceiling)
        count = int(mask.sum())
        if count == 0:
            raise ValueError("eligibility mask removed every candidate")
        posterior = np.where(mask, self.bundle.prior, 0.0)
        total = float(posterior.sum())
        if total <= 0:
            raise ValueError("eligible candidates have zero posterior mass")
        posterior /= total
        entropy_floor, delta90 = self._masked_calibration(mask)
        if entropy_floor > count:
            raise ValueError(
                "masked entropy floor cannot exceed eligible candidate count"
            )
        return QuizState(
            posterior=posterior,
            eligibility_mask=mask,
            entropy_floor=entropy_floor,
            delta90=delta90,
            eligibility_warning=count < self.bundle.eligibility.sanity_floor,
            direct_pick=count < self.bundle.eligibility.direct_pick_below,
            selection_seed=selection_seed,
            stopped=count < self.bundle.eligibility.direct_pick_below,
            stop_reason=(
                "direct_pick"
                if count < self.bundle.eligibility.direct_pick_below
                else None
            ),
        )

    def eligibility_mask(
        self, *, duration_ceiling: int | None = None
    ) -> np.ndarray:
        """Build eligibility on the full catalog, before any ranking.

        Duration is an inclusive ceiling. Missing runtime is deliberately
        fail-open; availability metadata is never consulted here.
        """
        if duration_ceiling is not None and duration_ceiling < 1:
            raise ValueError("duration_ceiling must be positive")
        mask = np.ones(len(self.bundle.candidate_ids), dtype=bool)
        if duration_ceiling is None:
            return mask
        for index, candidate_id in enumerate(self.bundle.candidate_ids):
            raw = self.bundle.metadata.get(candidate_id, {}).get("runtime_minutes")
            if raw is not None and int(raw) > duration_ceiling:
                mask[index] = False
        return mask

    def _masked_calibration(self, mask: np.ndarray) -> tuple[float, float]:
        if mask.shape != (len(self.bundle.candidate_ids),):
            raise ValueError("eligibility mask shape does not match candidates")
        indices = np.flatnonzero(mask)
        if len(indices) == 0:
            raise ValueError("eligibility mask removed every candidate")
        if len(indices) == len(mask):
            entropy_floor = self.bundle.entropy_floor
        else:
            labels = self.bundle.cluster_labels[indices]
            _, sizes = np.unique(labels, return_counts=True)
            weights = sizes.astype(float) / float(sizes.sum())
            entropy_floor = float(np.exp(np.sum(weights * np.log(sizes))))
        distances = []
        labels = self.bundle.cluster_labels[indices]
        for label in np.unique(labels):
            members = indices[labels == label]
            points = self.bundle.candidate_vectors[members]
            for offset in range(len(points) - 1):
                distances.extend(
                    np.linalg.norm(points[offset + 1:] - points[offset], axis=1)
                )
        delta90 = float(np.quantile(distances, 0.90)) if distances else 0.0
        return entropy_floor, delta90

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
        relative_entropy = float(np.exp(entropy(state.posterior)) / state.entropy_floor)
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
        # Rank only after the full-catalog eligibility mask has been applied.
        eligible = np.flatnonzero(state.eligibility_mask)
        order = eligible[np.argsort(state.posterior[eligible])[::-1]][:limit]
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

    def prepare_pick_order(self, state: QuizState) -> list[dict[str, object]]:
        """Freeze masked posterior order once, deduplicating franchises."""
        if not state.stopped:
            raise ValueError("quiz has not stopped")
        if state.frozen_pick_order:
            return state.frozen_pick_order
        ranked = self.ranked_candidates(
            state, limit=int(state.eligibility_mask.sum())
        )
        seen_franchises: set[str] = set()
        frozen = []
        for rank_position, row in enumerate(ranked, start=1):
            candidate_id = str(row["id"])
            raw_franchise = self.bundle.metadata.get(candidate_id, {}).get(
                "franchise"
            )
            franchise = (
                str(raw_franchise).strip().casefold()
                if raw_franchise is not None else None
            )
            if franchise is not None and franchise in seen_franchises:
                continue
            if franchise is not None:
                seen_franchises.add(franchise)
            frozen.append({**row, "rankPosition": rank_position})
        if not frozen:
            raise ValueError("no eligible candidate remains for pick")
        state.frozen_pick_order = frozen
        return frozen

    def current_pick(self, state: QuizState) -> dict[str, object]:
        order = self.prepare_pick_order(state)
        if state.pick_cursor >= len(order):
            raise ValueError("pick order exhausted")
        return {
            **order[state.pick_cursor],
            "cursorPosition": state.pick_cursor + 1,
            "lowConfidence": state.pick_cursor >= 5,
        }

    def skip_pick(self, state: QuizState) -> dict[str, object]:
        if state.accepted_pick is not None:
            raise ValueError("a pick has already been accepted")
        current = self.current_pick(state)
        if state.pick_cursor + 1 >= len(state.frozen_pick_order):
            raise ValueError("pick order exhausted")
        state.pick_skips.append({
            "candidateId": current["id"],
            "rankPosition": current["rankPosition"],
        })
        state.pick_cursor += 1
        return self.current_pick(state)

    def accept_pick(self, state: QuizState) -> dict[str, object]:
        if state.accepted_pick is not None:
            raise ValueError("a pick has already been accepted")
        current = self.current_pick(state)
        state.accepted_pick = {
            "candidateId": current["id"],
            "rankPosition": current["rankPosition"],
        }
        return state.accepted_pick

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

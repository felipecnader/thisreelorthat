"""Deterministic selection inside a near-optimal information-gain band."""

from __future__ import annotations

import hashlib
import math

import numpy as np

from .bundle import FloatArray, IntArray


def pair_hash_uniform(selection_seed: str, left: int, right: int) -> float:
    """Stable uniform variate for one session/pair, independent of pool order."""
    digest = hashlib.sha256(
        f"{selection_seed}:{min(left, right)}:{max(left, right)}".encode()
    ).digest()
    value = int.from_bytes(digest[:8], "big")
    return (value + 1) / (2**64 + 1)


def exponential_race_index(
    pairs: IntArray,
    *,
    selection_seed: str,
    weights: FloatArray | None = None,
) -> int:
    """Return the local winner of production's deterministic pair race."""
    pairs = np.asarray(pairs, dtype=int)
    if pairs.ndim != 2 or pairs.shape[1] != 2 or len(pairs) == 0:
        raise ValueError("pairs must have shape (n, 2) with at least one row")
    if weights is None:
        weights = np.ones(len(pairs), dtype=float)
    else:
        weights = np.asarray(weights, dtype=float)
        if weights.shape != (len(pairs),):
            raise ValueError("one weight is required per pair")
        if not np.all(np.isfinite(weights)) or np.any(weights <= 0):
            raise ValueError("pair weights must be finite and positive")
    keys = [
        -math.log(pair_hash_uniform(selection_seed, *map(int, pair)))
        / float(weight)
        for pair, weight in zip(pairs, weights)
    ]
    return int(np.argmin(keys))


def near_optimal_index(
    gains: FloatArray,
    pairs: IntArray,
    *,
    epsilon: float,
    opening_min_candidates: int,
    selection_seed: str,
    round_number: int,
    weights: FloatArray | None = None,
    conditioned_gains: FloatArray | None = None,
    conditioned_relative_floor: float | None = None,
) -> int:
    """Choose by a deterministic exponential race inside the EIG band.

    ``weights`` supports equivalent replay of production's soft exploration,
    reuse and vivacity factors. The public reference engine currently supplies
    uniform weights; those policies remain outside its published scope.
    """
    gains = np.asarray(gains, dtype=float)
    pairs = np.asarray(pairs, dtype=int)
    if gains.shape != (len(pairs),):
        raise ValueError("one gain is required per pair")
    allowed_mask = np.isfinite(gains)
    if conditioned_gains is not None:
        conditioned_gains = np.asarray(conditioned_gains, dtype=float)
        if conditioned_gains.shape != gains.shape:
            raise ValueError("conditioned gains must match total gains")
        if (
            conditioned_relative_floor is None
            or not 0 < conditioned_relative_floor < 1
        ):
            raise ValueError("conditioned_relative_floor must be in (0, 1)")
        candidates = np.flatnonzero(
            allowed_mask & np.isfinite(conditioned_gains)
        )
        if len(candidates) == 0:
            raise RuntimeError("no pair has finite conditioned gain")
        maximum_conditioned = float(np.max(conditioned_gains[candidates]))
        floor = (
            conditioned_relative_floor * maximum_conditioned
            if maximum_conditioned > 0
            else maximum_conditioned - 1e-12
        )
        allowed_mask &= conditioned_gains >= floor
    elif conditioned_relative_floor is not None:
        raise ValueError("conditioned gains are required for a relative floor")
    allowed = np.flatnonzero(allowed_mask)
    if len(allowed) == 0:
        raise RuntimeError("pair pool exhausted")
    maximum = float(np.max(gains[allowed]))
    eligible = allowed[gains[allowed] >= (1 - epsilon) * maximum]
    if round_number == 1 and len(eligible) < opening_min_candidates:
        ranked = allowed[np.argsort(gains[allowed])[::-1]]
        eligible = ranked[: min(opening_min_candidates, len(ranked))]

    if weights is not None:
        weights = np.asarray(weights, dtype=float)
        if weights.shape != (len(pairs),):
            raise ValueError("one weight is required per pair")
    eligible_weights = None if weights is None else weights[eligible]
    local_index = exponential_race_index(
        pairs[eligible],
        selection_seed=selection_seed,
        weights=eligible_weights,
    )
    return int(eligible[local_index])

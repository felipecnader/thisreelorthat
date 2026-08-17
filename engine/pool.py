"""Offline pair-pool construction used by the historical private runtime."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from engine.bundle import EngineParameters
from engine.math import expected_information_gain, likelihood, pair_features


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def build_pair_pool(
    probe_vectors: FloatArray,
    cluster_centers: FloatArray,
    parameters: EngineParameters,
    *,
    limit: int = 768,
    chunk_size: int = 1_000,
) -> IntArray:
    """Return the highest prior-EIG unordered probe pairs.

    This is the literal constructor used for the 768-pair source pool later
    inherited by private production.  It has no contrast gate, coarse/fine
    gate, axis quota, coverage objective, deduplication or diversity term.
    Those mechanisms either belong to online selection or to experiments that
    were not promoted.
    """
    probes = np.asarray(probe_vectors, dtype=float)
    centers = np.asarray(cluster_centers, dtype=float)
    if probes.ndim != 2 or centers.ndim != 2 or probes.shape[1] != centers.shape[1]:
        raise ValueError("probe vectors and cluster centers must be aligned matrices")
    if len(probes) < 2:
        raise ValueError("at least two probes are required")
    if limit < 1 or chunk_size < 1:
        raise ValueError("limit and chunk_size must be positive")

    pairs = np.asarray(
        [(left, right) for left in range(len(probes)) for right in range(left + 1, len(probes))],
        dtype=np.int64,
    )
    prior = np.full(len(centers), 1.0 / len(centers), dtype=float)
    scores = np.empty(len(pairs), dtype=float)

    for start in range(0, len(pairs), chunk_size):
        chunk = pairs[start : start + chunk_size]
        pair_likelihoods = []
        for left, right in chunk:
            preference, shared = pair_features(centers, probes[left], probes[right])
            pair_likelihoods.append(
                likelihood(
                    preference,
                    shared,
                    kappa=parameters.kappa,
                    evidence_cap=parameters.evidence_cap,
                    tie_sigma=parameters.tie_sigma,
                )
            )
        scores[start : start + len(chunk)] = expected_information_gain(
            prior, np.asarray(pair_likelihoods, dtype=float)
        )

    order = np.argsort(scores)[-min(limit, len(pairs)) :][::-1]
    return pairs[order]

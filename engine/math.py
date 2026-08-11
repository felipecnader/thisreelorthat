"""Numerical primitives for posterior updates and pair selection."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


def normalize(values: FloatArray) -> FloatArray:
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("probability weights must be finite and non-negative")
    total = float(values.sum())
    if total <= 0:
        raise ValueError("probability weights must contain positive mass")
    return values / total


def entropy(values: FloatArray) -> float:
    values = normalize(values)
    return -float(np.sum(values * np.log(np.maximum(values, 1e-300))))


def cluster_mass(posterior: FloatArray, labels: NDArray[np.int64], count: int) -> FloatArray:
    return np.bincount(labels, weights=posterior, minlength=count).astype(float)


def pair_features(points: FloatArray, left: FloatArray, right: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Return contrast preference and attraction to the probes' shared profile."""
    direction = left - right
    norm = float(np.dot(direction, direction))
    if norm <= 1e-12:
        preference = np.zeros(len(points), dtype=float)
    else:
        midpoint = (left + right) / 2.0
        preference = np.clip(2.0 * ((points - midpoint) @ direction) / norm, -2.0, 2.0)

    raw_shared = -0.5 * (
        np.mean((points - left) ** 2, axis=1)
        + np.mean((points - right) ** 2, axis=1)
    )
    shared = (raw_shared - float(raw_shared.mean())) / max(float(raw_shared.std()), 0.15)
    return preference, np.clip(shared, -2.5, 2.5)


def likelihood(
    preference: FloatArray,
    shared: FloatArray,
    *,
    kappa: float,
    evidence_cap: float,
    tie_sigma: float,
) -> FloatArray:
    """Four-outcome likelihood ordered as A, B, either, neither."""
    signal = np.clip(preference, -evidence_cap, evidence_cap)
    attraction = 0.72 * shared
    logits = np.column_stack(
        [
            kappa * signal + 0.30 * attraction,
            -kappa * signal + 0.30 * attraction,
            -0.5 * (signal / tie_sigma) ** 2 + attraction - 0.10,
            -0.30 * (signal / 1.2) ** 2 - attraction - 0.20,
        ]
    )
    logits -= logits.max(axis=1, keepdims=True)
    weights = np.exp(logits)
    return weights / weights.sum(axis=1, keepdims=True)


def update(posterior: FloatArray, evidence: FloatArray, beta: float) -> FloatArray:
    if evidence.shape != posterior.shape or np.any(evidence <= 0):
        raise ValueError("evidence must be positive and match the posterior")
    return normalize(posterior * np.power(evidence, beta))


def expected_information_gain(cluster_posterior: FloatArray, pair_likelihoods: FloatArray) -> FloatArray:
    """Expected reduction of cluster entropy for every pair in the pool."""
    outcome = np.einsum("k,pka->pa", cluster_posterior, pair_likelihoods)
    conditional = (
        cluster_posterior[None, :, None]
        * pair_likelihoods
        / np.maximum(outcome[:, None, :], 1e-12)
    )
    conditional_h = -np.sum(
        conditional * np.log(np.maximum(conditional, 1e-300)), axis=1
    )
    expected_h = np.sum(outcome * conditional_h, axis=1)
    return entropy(cluster_posterior) - expected_h

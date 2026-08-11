from __future__ import annotations

import numpy as np

from engine.math import likelihood, normalize, pair_features, update


def test_normalize_is_positive_and_sums_to_one() -> None:
    result = normalize(np.asarray([2.0, 3.0, 5.0]))
    assert np.all(result > 0)
    assert np.isclose(result.sum(), 1.0)


def test_likelihood_is_row_normalized() -> None:
    points = np.asarray([[-1.0, 0.0], [0.0, 0.0], [1.0, 0.0]])
    preference, shared = pair_features(points, np.asarray([1.0, 0.0]), np.asarray([-1.0, 0.0]))
    table = likelihood(preference, shared, kappa=3.5, evidence_cap=1.25, tie_sigma=0.55)
    assert table.shape == (3, 4)
    assert np.all(table > 0)
    assert np.allclose(table.sum(axis=1), 1.0)


def test_swapping_pair_swaps_a_and_b_likelihoods() -> None:
    points = np.asarray([[-0.7, 0.2], [0.3, -0.4], [0.8, 0.9]])
    left, right = np.asarray([1.0, 0.0]), np.asarray([-1.0, 0.0])
    pref, shared = pair_features(points, left, right)
    swapped_pref, swapped_shared = pair_features(points, right, left)
    table = likelihood(pref, shared, kappa=3.5, evidence_cap=1.25, tie_sigma=0.55)
    swapped = likelihood(swapped_pref, swapped_shared, kappa=3.5, evidence_cap=1.25, tie_sigma=0.55)
    assert np.allclose(table[:, 0], swapped[:, 1])
    assert np.allclose(table[:, 1], swapped[:, 0])
    assert np.allclose(table[:, 2:], swapped[:, 2:])


def test_tempered_update_stays_strictly_positive() -> None:
    posterior = np.asarray([0.2, 0.3, 0.5])
    result = update(posterior, np.asarray([0.01, 0.5, 0.99]), beta=0.70)
    assert np.all(result > 0)
    assert np.isclose(result.sum(), 1.0)

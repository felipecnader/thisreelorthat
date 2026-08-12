from __future__ import annotations

import numpy as np
import pytest

from engine.selection import near_optimal_index


PAIRS = np.asarray([[0, 1], [2, 3], [4, 5]])


def test_near_optimal_band_excludes_pairs_below_threshold() -> None:
    gains = np.asarray([1.0, 0.89, 0.5])

    winners = {
        near_optimal_index(
            gains,
            PAIRS,
            epsilon=0.10,
            opening_min_candidates=1,
            selection_seed=f"session-{index}",
            round_number=2,
        )
        for index in range(20)
    }

    assert winners == {0}


def test_opening_minimum_expands_a_single_pair_band() -> None:
    gains = np.asarray([1.0, 0.89, 0.5])

    winners = {
        near_optimal_index(
            gains,
            PAIRS,
            epsilon=0.10,
            opening_min_candidates=2,
            selection_seed=f"session-{index}",
            round_number=1,
        )
        for index in range(20)
    }

    assert winners == {0, 1}


def test_ab_floor_is_relative_to_best_conditioned_gain_not_total_gain() -> None:
    gains = np.asarray([1.00, 0.99, 0.98])
    gains_ab = np.asarray([0.10, 0.80, 0.39])

    chosen = near_optimal_index(
        gains,
        PAIRS,
        epsilon=0.10,
        opening_min_candidates=1,
        selection_seed="ab-floor",
        round_number=2,
        conditioned_gains=gains_ab,
        conditioned_relative_floor=0.50,
    )

    assert chosen == 1  # floor is 0.40; total-gain leader and 0.39 fail


def test_ab_floor_requires_valid_conditioned_inputs() -> None:
    with pytest.raises(ValueError, match="conditioned gains are required"):
        near_optimal_index(
            np.asarray([1.0]),
            np.asarray([[0, 1]]),
            epsilon=0.1,
            opening_min_candidates=1,
            selection_seed="x",
            round_number=1,
            conditioned_relative_floor=0.5,
        )

from __future__ import annotations

import numpy as np

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

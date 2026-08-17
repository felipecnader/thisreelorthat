import numpy as np

from engine.bundle import EngineParameters
from engine.pool import build_pair_pool


def test_pair_pool_contains_only_unique_unordered_pairs() -> None:
    probes = np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])
    centers = np.asarray([[0.0, 0.0], [1.0, 1.0], [-1.0, -1.0]])

    pool = build_pair_pool(probes, centers, EngineParameters(), limit=6, chunk_size=2)

    assert pool.shape == (6, 2)
    assert len({tuple(pair) for pair in pool.tolist()}) == 6
    assert np.all(pool[:, 0] < pool[:, 1])


def test_pair_pool_limit_is_respected() -> None:
    probes = np.asarray([[0.0], [1.0], [2.0], [3.0]])
    centers = np.asarray([[0.0], [3.0]])

    pool = build_pair_pool(probes, centers, EngineParameters(), limit=3)

    assert pool.shape == (3, 2)

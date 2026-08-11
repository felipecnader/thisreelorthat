from __future__ import annotations

import numpy as np
import pytest

from engine import CatalogBundle, EngineParameters, StopRule


@pytest.fixture
def bundle() -> CatalogBundle:
    probe_vectors = np.asarray([
        [-1.0, -0.8], [1.0, 0.8], [-0.9, 0.9], [0.9, -0.9],
        [-0.6, 0.1], [0.6, -0.1], [-0.1, -0.7], [0.1, 0.7],
        [-0.8, -0.2], [0.8, 0.2], [-0.2, 0.8], [0.2, -0.8],
    ])
    candidate_vectors = np.asarray([
        [-0.9, -0.7], [-0.7, -0.5], [0.8, 0.7], [0.6, 0.5],
        [-0.8, 0.8], [-0.6, 0.6], [0.8, -0.8], [0.6, -0.6],
    ])
    return CatalogBundle(
        probe_ids=tuple(f"p{i}" for i in range(len(probe_vectors))),
        candidate_ids=tuple(f"c{i}" for i in range(len(candidate_vectors))),
        probe_vectors=probe_vectors,
        candidate_vectors=candidate_vectors,
        cluster_labels=np.asarray([0, 0, 1, 1, 2, 2, 3, 3]),
        cluster_centers=np.asarray([[-0.8, -0.6], [0.7, 0.6], [-0.7, 0.7], [0.7, -0.7]]),
        pair_pool=np.asarray([[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]]),
        prior=np.full(8, 1 / 8),
        entropy_floor=2.0,
        stop_rule=StopRule(top_cluster_mass=0.99, entropy_floor_multiple=0.1, min_rounds=2, base_max_rounds=3),
        parameters=EngineParameters(),
        metadata={"c0": {"title": "Candidate Zero", "year": 2000}},
    )

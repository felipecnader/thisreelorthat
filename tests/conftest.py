from __future__ import annotations

import numpy as np
import pytest

from engine import CatalogBundle, EligibilityPolicy, EngineParameters, SemanticRerank, StopRule


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
        candidate_embeddings=np.asarray([
            [1.0, 0.0, 0.0], [0.9, 0.1, 0.0],
            [0.0, 1.0, 0.0], [0.1, 0.9, 0.0],
            [0.0, 0.0, 1.0], [0.1, 0.0, 0.9],
            [0.6, 0.6, 0.1], [0.5, 0.5, 0.2],
        ]),
        probe_embeddings=np.asarray([
            [1.0, 0.1, 0.1], [0.9, 0.2, 0.1], [0.8, 0.3, 0.1],
            [0.7, 0.4, 0.1], [0.6, 0.5, 0.1], [0.5, 0.6, 0.1],
            [0.4, 0.7, 0.1], [0.3, 0.8, 0.1], [0.2, 0.9, 0.1],
            [0.1, 1.0, 0.1], [0.1, 0.9, 0.2], [0.1, 0.8, 0.3],
        ]),
        cluster_labels=np.asarray([0, 0, 1, 1, 2, 2, 3, 3]),
        cluster_centers=np.asarray([[-0.8, -0.6], [0.7, 0.6], [-0.7, 0.7], [0.7, -0.7]]),
        pair_pool=np.asarray([[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]]),
        prior=np.full(8, 1 / 8),
        entropy_floor=2.0,
        near_optimal_epsilon=0.10,
        opening_min_candidates=6,
        ab_eig_relative_floor=0.50,
        ab_eig_provenance={
            "decision": "maximize candidate set among statistically tied sweep arms",
            "calibration": "production 50-target sweep: 0.50, 0.70, 0.85, 0.95",
        },
        embedding_provenance={
            "model": "synthetic-test",
            "template": "candidate {id}",
        },
        eligibility=EligibilityPolicy(sanity_floor=3, direct_pick_below=2),
        semantic_rerank=SemanticRerank(
            model="synthetic-test",
            window=3,
            disable_below_eligible=3,
            provenance={"calibration": "test fixture only"},
        ),
        stop_rule=StopRule(
            top_cluster_mass=0.99,
            entropy_floor_multiple=0.5,
            min_rounds=2,
            base_max_rounds=3,
        ),
        parameters=EngineParameters(),
        metadata={"c0": {"title": "Candidate Zero", "year": 2000}},
    )

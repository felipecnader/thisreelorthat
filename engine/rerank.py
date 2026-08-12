"""Pure semantic reranking inside a posterior-defined window."""

from __future__ import annotations

import numpy as np


def semantic_order(
    posterior_order: np.ndarray,
    candidate_embeddings: np.ndarray,
    probe_embeddings: np.ndarray,
    endorsed_probes: list[int],
    rejected_probes: list[int],
    *,
    window: int,
) -> np.ndarray:
    order = np.asarray(posterior_order, dtype=int)
    if not endorsed_probes:
        return order.copy()
    positive = np.mean(probe_embeddings[endorsed_probes], axis=0)
    negative = (
        np.mean(probe_embeddings[rejected_probes], axis=0)
        if rejected_probes else np.zeros_like(positive)
    )
    reference = positive - negative
    norm = float(np.linalg.norm(reference))
    if norm <= 1e-12:
        return order.copy()
    reference /= norm
    width = min(window, len(order))
    prefix = order[:width]
    scores = candidate_embeddings[prefix] @ reference
    semantic_prefix = prefix[np.argsort(-scores, kind="stable")]
    return np.concatenate((semantic_prefix, order[width:]))

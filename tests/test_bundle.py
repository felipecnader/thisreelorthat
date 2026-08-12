from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest


def test_candidate_embedding_row_count_is_validated(bundle) -> None:
    with pytest.raises(ValueError, match="candidate embedding shape"):
        replace(bundle, candidate_embeddings=np.ones((7, 3)))


def test_candidate_embedding_dimension_is_nonempty(bundle) -> None:
    with pytest.raises(ValueError, match="candidate embedding shape"):
        replace(bundle, candidate_embeddings=np.empty((8, 0)))


@pytest.mark.parametrize("bad_value", [0.0, np.nan, np.inf])
def test_candidate_embedding_values_are_validated(bundle, bad_value) -> None:
    embeddings = bundle.candidate_embeddings.copy()
    embeddings[0] = bad_value
    with pytest.raises(ValueError, match="finite and have nonzero norm"):
        replace(bundle, candidate_embeddings=embeddings)


def test_probe_embeddings_must_match_candidate_dimension(bundle) -> None:
    with pytest.raises(ValueError, match="probe embeddings must match"):
        replace(bundle, probe_embeddings=np.ones((12, 2)))


def test_probe_embeddings_accept_matching_matrix(bundle) -> None:
    enriched = replace(bundle, probe_embeddings=np.ones((12, 3)))
    assert enriched.probe_embeddings.shape == (12, 3)


@pytest.mark.parametrize("key", ["model", "template"])
def test_embedding_provenance_is_required(bundle, key) -> None:
    provenance = dict(bundle.embedding_provenance)
    provenance[key] = ""
    with pytest.raises(ValueError, match=f"nonempty {key}"):
        replace(bundle, embedding_provenance=provenance)


def test_candidate_delivery_metadata_is_validated(bundle) -> None:
    with pytest.raises(ValueError, match="unknown candidate"):
        replace(bundle, metadata={"missing": {"title": "Missing"}})
    with pytest.raises(ValueError, match="runtime_minutes"):
        replace(bundle, metadata={"c0": {"runtime_minutes": 0}})
    with pytest.raises(ValueError, match="franchise must be nonempty"):
        replace(bundle, metadata={"c0": {"franchise": " "}})

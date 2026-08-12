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


@pytest.mark.parametrize("floor", [0.0, -0.1, 1.0, 1.1, np.nan])
def test_ab_eig_floor_must_be_strictly_between_zero_and_one(bundle, floor) -> None:
    with pytest.raises(ValueError, match="ab_eig_relative_floor"):
        replace(bundle, ab_eig_relative_floor=floor)


@pytest.mark.parametrize("key", ["decision", "calibration"])
def test_ab_eig_provenance_is_required(bundle, key) -> None:
    provenance = dict(bundle.ab_eig_provenance)
    provenance[key] = ""
    with pytest.raises(ValueError, match=f"nonempty {key}"):
        replace(bundle, ab_eig_provenance=provenance)


def test_axis_names_and_candidate_attributes_are_structurally_validated(bundle) -> None:
    with pytest.raises(ValueError, match="axis_names must match"):
        replace(bundle, axis_names=("only-one",))
    with pytest.raises(ValueError, match="axis_names must be unique"):
        replace(bundle, axis_names=("same", "same"))
    with pytest.raises(ValueError, match="exactly one entry"):
        replace(bundle, candidate_attributes={})
    bad = dict(bundle.candidate_attributes)
    bad["c0"] = {"genres": None, "popularity": None}
    with pytest.raises(ValueError, match="explicitly contain"):
        replace(bundle, candidate_attributes=bad)
    bad = dict(bundle.candidate_attributes)
    bad["c0"] = {"genres": None, "popularity": 0, "runtime_minutes": None}
    with pytest.raises(ValueError, match="null, not zero"):
        replace(bundle, candidate_attributes=bad)


def test_selection_history_parameters_are_validated() -> None:
    from engine import SelectionHistoryPolicy

    with pytest.raises(ValueError, match="strictly descend"):
        SelectionHistoryPolicy(refused_rms_thresholds=(.6, .75))
    with pytest.raises(ValueError, match="lookback"):
        SelectionHistoryPolicy(repeated_axis_lookback=0)

"""Validated, catalog-specific runtime bundle.

The private reference implementation persisted this data in NPZ files.  The
public engine deliberately accepts ordinary Python/numpy values so callers can
choose JSON, NPZ, a database, or another storage format without coupling the
math to a filesystem layout.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class EngineParameters:
    kappa: float = 3.5
    evidence_cap: float = 1.25
    tie_sigma: float = 0.55
    beta: float = 0.70

    def __post_init__(self) -> None:
        if self.kappa <= 0 or self.evidence_cap <= 0 or self.tie_sigma <= 0:
            raise ValueError("likelihood parameters must be positive")
        if not 0 < self.beta <= 1:
            raise ValueError("beta must be in (0, 1]")


@dataclass(frozen=True)
class StopRule:
    top_cluster_mass: float
    entropy_floor_multiple: float
    min_rounds: int = 5
    base_max_rounds: int = 10
    max_none_extension: int = 4

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.top_cluster_mass)
            or not 0 < self.top_cluster_mass <= 1
        ):
            raise ValueError("top_cluster_mass must be in (0, 1]")
        if (
            not math.isfinite(self.entropy_floor_multiple)
            or self.entropy_floor_multiple <= 0
        ):
            raise ValueError("entropy_floor_multiple must be positive")
        if self.min_rounds < 1 or self.base_max_rounds < self.min_rounds:
            raise ValueError("invalid round bounds")


@dataclass(frozen=True)
class EligibilityPolicy:
    sanity_floor: int = 180
    direct_pick_below: int = 60

    def __post_init__(self) -> None:
        if self.sanity_floor < 1:
            raise ValueError("eligibility sanity_floor must be positive")
        if self.direct_pick_below < 1:
            raise ValueError("direct_pick_below must be positive")
        if self.direct_pick_below > self.sanity_floor:
            raise ValueError("direct_pick_below cannot exceed sanity_floor")


@dataclass(frozen=True)
class CatalogBundle:
    probe_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    probe_vectors: FloatArray
    candidate_vectors: FloatArray
    probe_embeddings: FloatArray
    candidate_embeddings: FloatArray
    cluster_labels: IntArray
    cluster_centers: FloatArray
    pair_pool: IntArray
    prior: FloatArray
    entropy_floor: float
    stop_rule: StopRule
    near_optimal_epsilon: float = 0.10
    opening_min_candidates: int = 10
    ab_eig_relative_floor: float = 0.50
    ab_eig_provenance: Mapping[str, object] = field(default_factory=dict)
    embedding_provenance: Mapping[str, object] = field(default_factory=dict)
    eligibility: EligibilityPolicy = field(default_factory=EligibilityPolicy)
    parameters: EngineParameters = field(default_factory=EngineParameters)
    metadata: Mapping[str, Mapping[str, object]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        arrays = {
            "probe_vectors": np.asarray(self.probe_vectors, dtype=float),
            "candidate_vectors": np.asarray(self.candidate_vectors, dtype=float),
            "candidate_embeddings": np.asarray(
                self.candidate_embeddings, dtype=float
            ),
            "probe_embeddings": np.asarray(self.probe_embeddings, dtype=float),
            "cluster_labels": np.asarray(self.cluster_labels, dtype=int),
            "cluster_centers": np.asarray(self.cluster_centers, dtype=float),
            "pair_pool": np.asarray(self.pair_pool, dtype=int),
            "prior": np.asarray(self.prior, dtype=float),
        }
        for name, value in arrays.items():
            object.__setattr__(self, name, value)

        if len(set(self.probe_ids)) != len(self.probe_ids):
            raise ValueError("probe_ids must be unique")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("candidate_ids must be unique")
        if set(self.probe_ids) & set(self.candidate_ids):
            raise ValueError("probes and candidates must be disjoint")
        unknown_metadata = set(self.metadata) - set(self.candidate_ids)
        if unknown_metadata:
            raise ValueError("metadata contains an unknown candidate")
        for candidate_id, item in self.metadata.items():
            runtime = item.get("runtime_minutes")
            if runtime is not None and (
                not isinstance(runtime, int) or isinstance(runtime, bool)
                or runtime < 1
            ):
                raise ValueError(
                    f"runtime_minutes must be a positive integer for {candidate_id}"
                )
            franchise = item.get("franchise")
            if franchise is not None and not str(franchise).strip():
                raise ValueError(
                    f"franchise must be nonempty for {candidate_id}"
                )
        if self.probe_vectors.ndim != 2 or len(self.probe_vectors) != len(self.probe_ids):
            raise ValueError("probe vector shape does not match probe_ids")
        if self.candidate_vectors.ndim != 2 or len(self.candidate_vectors) != len(self.candidate_ids):
            raise ValueError("candidate vector shape does not match candidate_ids")
        if (
            self.candidate_embeddings.ndim != 2
            or len(self.candidate_embeddings) != len(self.candidate_ids)
            or self.candidate_embeddings.shape[1] == 0
        ):
            raise ValueError(
                "candidate embedding shape does not match candidate_ids"
            )
        candidate_embedding_norms = np.linalg.norm(
            self.candidate_embeddings, axis=1
        )
        if (
            not np.all(np.isfinite(self.candidate_embeddings))
            or np.any(candidate_embedding_norms <= 0)
        ):
            raise ValueError(
                "candidate embeddings must be finite and have nonzero norm"
            )
        if (
            self.probe_embeddings.ndim != 2
            or len(self.probe_embeddings) != len(self.probe_ids)
            or self.probe_embeddings.shape[1]
            != self.candidate_embeddings.shape[1]
        ):
            raise ValueError(
                "probe embeddings must match probe_ids and candidate dimension"
            )
        probe_embedding_norms = np.linalg.norm(self.probe_embeddings, axis=1)
        if (
            not np.all(np.isfinite(self.probe_embeddings))
            or np.any(probe_embedding_norms <= 0)
        ):
            raise ValueError(
                "probe embeddings must be finite and have nonzero norm"
            )
        for key in ("model", "template"):
            if not str(self.embedding_provenance.get(key, "")).strip():
                raise ValueError(
                    f"embedding_provenance requires a nonempty {key}"
                )
        if self.probe_vectors.shape[1] != self.candidate_vectors.shape[1]:
            raise ValueError("probe and candidate dimensions differ")
        if self.cluster_centers.ndim != 2 or self.cluster_centers.shape[1] != self.candidate_vectors.shape[1]:
            raise ValueError("cluster center shape is invalid")
        if self.cluster_labels.shape != (len(self.candidate_ids),):
            raise ValueError("one cluster label is required per candidate")
        if np.any(self.cluster_labels < 0) or np.any(self.cluster_labels >= len(self.cluster_centers)):
            raise ValueError("cluster label out of range")
        if self.pair_pool.ndim != 2 or self.pair_pool.shape[1] != 2:
            raise ValueError("pair_pool must have shape (n, 2)")
        if len(self.pair_pool) == 0 or np.any(self.pair_pool < 0) or np.any(self.pair_pool >= len(self.probe_ids)):
            raise ValueError("pair_pool contains an invalid probe index")
        if np.any(self.pair_pool[:, 0] == self.pair_pool[:, 1]):
            raise ValueError("a probe cannot be paired with itself")
        if (
            not math.isfinite(self.near_optimal_epsilon)
            or not 0 < self.near_optimal_epsilon < 1
        ):
            raise ValueError("near_optimal_epsilon must be in (0, 1)")
        if self.opening_min_candidates < 1:
            raise ValueError("opening_min_candidates must be positive")
        if self.opening_min_candidates > len(self.pair_pool):
            raise ValueError("opening_min_candidates cannot exceed pair_pool size")
        if (
            not math.isfinite(self.ab_eig_relative_floor)
            or not 0 < self.ab_eig_relative_floor < 1
        ):
            raise ValueError("ab_eig_relative_floor must be in (0, 1)")
        for key in ("decision", "calibration"):
            if not str(self.ab_eig_provenance.get(key, "")).strip():
                raise ValueError(f"ab_eig_provenance requires a nonempty {key}")
        if self.prior.shape != (len(self.candidate_ids),):
            raise ValueError("prior shape does not match candidates")
        if not np.all(np.isfinite(self.prior)) or np.any(self.prior <= 0):
            raise ValueError("prior must be finite and strictly positive")
        total = float(self.prior.sum())
        if not np.isclose(total, 1.0, atol=1e-8):
            raise ValueError("prior must sum to one")
        if not math.isfinite(self.entropy_floor) or self.entropy_floor <= 0:
            raise ValueError("entropy_floor must be positive")
        if self.entropy_floor > len(self.candidate_ids):
            raise ValueError("entropy_floor cannot exceed the candidate count")
        if self.eligibility.sanity_floor > len(self.candidate_ids):
            raise ValueError(
                "eligibility sanity_floor cannot exceed the candidate count"
            )
        confidence_entropy_limit = (
            self.stop_rule.entropy_floor_multiple * self.entropy_floor
        )
        if confidence_entropy_limit < 1.0:
            raise ValueError(
                "confidence entropy threshold is unreachable: "
                "entropy_floor_multiple * entropy_floor must be at least 1.0"
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "CatalogBundle":
        """Build a bundle from a JSON-like mapping."""
        stop = StopRule(**value["stop_rule"])  # type: ignore[arg-type]
        params = EngineParameters(**value.get("parameters", {}))  # type: ignore[arg-type]
        eligibility = EligibilityPolicy(**value.get("eligibility", {}))  # type: ignore[arg-type]
        return cls(
            probe_ids=tuple(value["probe_ids"]),  # type: ignore[arg-type]
            candidate_ids=tuple(value["candidate_ids"]),  # type: ignore[arg-type]
            probe_vectors=np.asarray(value["probe_vectors"], dtype=float),
            candidate_vectors=np.asarray(value["candidate_vectors"], dtype=float),
            candidate_embeddings=np.asarray(
                value["candidate_embeddings"], dtype=float
            ),
            probe_embeddings=np.asarray(value["probe_embeddings"], dtype=float),
            cluster_labels=np.asarray(value["cluster_labels"], dtype=int),
            cluster_centers=np.asarray(value["cluster_centers"], dtype=float),
            pair_pool=np.asarray(value["pair_pool"], dtype=int),
            prior=np.asarray(value["prior"], dtype=float),
            entropy_floor=float(value["entropy_floor"]),
            stop_rule=stop,
            near_optimal_epsilon=float(value.get("near_optimal_epsilon", 0.10)),
            opening_min_candidates=int(value.get("opening_min_candidates", 10)),
            ab_eig_relative_floor=float(value.get("ab_eig_relative_floor", 0.50)),
            ab_eig_provenance=value.get("ab_eig_provenance", {}),  # type: ignore[arg-type]
            embedding_provenance=value.get("embedding_provenance", {}),  # type: ignore[arg-type]
            eligibility=eligibility,
            parameters=params,
            metadata=value.get("metadata", {}),  # type: ignore[arg-type]
        )

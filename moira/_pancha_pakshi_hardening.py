"""Private Phase 10 full-subsystem hardening for Pancha Pakshi research."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from string import hexdigits

from ._pancha_pakshi_classification import (
    PanchaPakshiHistoricalClassificationPolicyId,
)
from ._pancha_pakshi_network import PanchaPakshiUromarisiPhase9Network


_LAYER_SEQUENCE = (
    "source_atoms",
    "classification",
    "inspectability",
    "explicit_policy",
    "relations",
    "relation_inspectability",
    "local_conditions",
    "aggregate_intelligence",
    "network_intelligence",
)


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in hexdigits for character in value):
        raise ValueError(f"{label} must be one lowercase hexadecimal SHA-256")
    if value != value.lower():
        raise ValueError(f"{label} must use lowercase hexadecimal")


def _structural_payload(network: PanchaPakshiUromarisiPhase9Network) -> dict[str, object]:
    return {
        "schema": "pancha_pakshi_uromarisi_hardened_structure_v1",
        "policy_id": network.aggregate.policy_id.value,
        "nodes": [
            {
                "node_id": node.node_id,
                "identity": [
                    node.identity[0].value,
                    node.identity[1],
                    node.identity[2],
                ],
                "source_binding": list(node.source_binding),
                "disposition": node.profile.classification.disposition.value,
                "time_class": node.profile.classification.time_class.value,
                "semantic_markers": sorted(
                    marker.value
                    for marker in node.profile.classification.semantic_markers
                ),
                "uncertainty_count": node.profile.classification.uncertainty_count,
                "relation_presence": node.profile.relation.presence.value,
                "relation_surface_kind": (
                    node.profile.relation.surface_kind.value
                    if node.profile.relation.surface_kind is not None
                    else None
                ),
                "relation_confidence": node.profile.relation.confidence.value,
                "evaluation_status": node.profile.evaluation_status.value,
            }
            for node in network.nodes
        ],
        "candidate_node_ids": [
            candidate.owner_node_id for candidate in network.relation_candidates
        ],
        "admitted_edges": [],
        "scored_edges": [],
        "blocked_verses": list(network.blocked_verses),
        "metric_status": network.metric_status.value,
    }


def _structural_sha256(network: PanchaPakshiUromarisiPhase9Network) -> str:
    canonical = json.dumps(
        _structural_payload(network),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PanchaPakshiUromarisiPhase10HardeningReceipt:
    """Frozen cross-layer identity and failure-contract receipt."""

    policy_id: PanchaPakshiHistoricalClassificationPolicyId
    layer_sequence: tuple[str, ...]
    node_ids: tuple[str, ...]
    source_bindings: tuple[tuple[str, str], ...]
    profile_count: int
    relation_candidate_count: int
    admitted_edge_count: int
    scored_edge_count: int
    blocked_verses: tuple[int, ...]
    structural_sha256: str
    invariant_status: str = field(default="hardened", init=False)
    ordering_status: str = field(default="deterministic", init=False)
    failure_policy: str = field(default="fail_closed", init=False)
    inference_policy: str = field(default="no_implicit_repair", init=False)
    admission_status: str = field(default="research_only", init=False)

    def __post_init__(self) -> None:
        if (
            self.policy_id
            is not PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL
        ):
            raise ValueError("receipt policy_id must retain the explicit Phase 4 policy")
        if self.layer_sequence != _LAYER_SEQUENCE:
            raise ValueError("receipt must preserve the constitutional layer sequence")
        if not isinstance(self.node_ids, tuple):
            raise TypeError("node_ids must be an immutable tuple")
        if len(self.node_ids) != 24 or len(set(self.node_ids)) != 24:
            raise ValueError("receipt requires 24 unique canonical node identities")
        if not isinstance(self.source_bindings, tuple) or not self.source_bindings:
            raise TypeError("source_bindings must be a nonempty immutable tuple")
        for decision_id, digest in self.source_bindings:
            if not decision_id:
                raise ValueError("source decision identities must not be empty")
            _require_sha256(digest, "source decision digest")
        if self.profile_count != 24:
            raise ValueError("receipt profile_count must equal 24")
        if self.relation_candidate_count != 17:
            raise ValueError("receipt relation_candidate_count must equal 17")
        if self.admitted_edge_count != 0 or self.scored_edge_count != 0:
            raise ValueError("receipt cannot harden invented admitted or scored edges")
        if self.blocked_verses != (250,):
            raise ValueError("receipt must preserve blocked verse 250")
        _require_sha256(self.structural_sha256, "structural_sha256")


def pancha_pakshi_uromarisi_hardening_receipt(
    network: PanchaPakshiUromarisiPhase9Network,
) -> PanchaPakshiUromarisiPhase10HardeningReceipt:
    """Freeze deterministic cross-layer facts without widening their meaning."""

    if not isinstance(network, PanchaPakshiUromarisiPhase9Network):
        raise TypeError("network must be PanchaPakshiUromarisiPhase9Network")
    return PanchaPakshiUromarisiPhase10HardeningReceipt(
        policy_id=network.aggregate.policy_id,
        layer_sequence=_LAYER_SEQUENCE,
        node_ids=network.node_ids,
        source_bindings=network.condition_corpus.relation_corpus.source_bindings,
        profile_count=len(network.nodes),
        relation_candidate_count=len(network.relation_candidates),
        admitted_edge_count=len(network.admitted_edges),
        scored_edge_count=len(network.scored_edges),
        blocked_verses=network.blocked_verses,
        structural_sha256=_structural_sha256(network),
    )


__all__: tuple[str, ...] = ()

"""Private Phase 9 structural network for Pancha Pakshi research.

The network projects the complete Phase 7 local-condition corpus into stable
nodes and attaches the Phase 5 detected clauses as candidate annotations.  It
does not manufacture endpoints, direction, admitted edges, graph metrics,
scores, prognosis, or medical meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ._pancha_pakshi_aggregate import (
    PanchaPakshiUromarisiPhase8AggregateIntelligence,
    pancha_pakshi_uromarisi_aggregate_intelligence,
)
from ._pancha_pakshi_condition import (
    PanchaPakshiHistoricalLocalConditionProfile,
    PanchaPakshiUromarisiPhase7LocalConditionCorpus,
)
from ._pancha_pakshi_relations import PanchaPakshiHistoricalRelationRecord
from .pancha_pakshi import PanchaPakshiActivity


class PanchaPakshiHistoricalNetworkMetricStatus(str, Enum):
    """Availability of topology metrics at the Phase 9 boundary."""

    NOT_EVALUABLE = "not_evaluable_no_admitted_relation_edges"


def _node_id(identity: tuple[PanchaPakshiActivity, int, int]) -> str:
    activity, ordinal, verse = identity
    return f"{activity.value}:{ordinal}:verse:{verse}"


@dataclass(frozen=True, slots=True)
class PanchaPakshiHistoricalNetworkNode:
    """One canonical Phase 7 profile represented as a structural node."""

    profile: PanchaPakshiHistoricalLocalConditionProfile
    node_id: str = field(init=False)
    admission_status: str = field(default="research_only", init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.profile, PanchaPakshiHistoricalLocalConditionProfile
        ):
            raise TypeError(
                "profile must be PanchaPakshiHistoricalLocalConditionProfile"
            )
        object.__setattr__(self, "node_id", _node_id(self.profile.identity))

    @property
    def identity(self) -> tuple[PanchaPakshiActivity, int, int]:
        return self.profile.identity

    @property
    def source_binding(self) -> tuple[str, str]:
        return self.profile.source_binding


@dataclass(frozen=True, slots=True)
class PanchaPakshiHistoricalRelationCandidate:
    """A detected source clause attached to its owning structural node."""

    owner_node_id: str
    relation: PanchaPakshiHistoricalRelationRecord
    endpoint_status: str = field(default="not_established", init=False)
    direction_status: str = field(default="not_established", init=False)
    edge_admission_status: str = field(default="not_admitted", init=False)
    scoring_status: str = field(default="not_performed", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.owner_node_id, str) or not self.owner_node_id:
            raise ValueError("owner_node_id must be a nonempty string")
        if not isinstance(self.relation, PanchaPakshiHistoricalRelationRecord):
            raise TypeError(
                "relation must be PanchaPakshiHistoricalRelationRecord"
            )
        if not self.relation.is_detected:
            raise ValueError("a network candidate must retain a detected clause")
        if self.owner_node_id != _node_id(self.relation.identity):
            raise ValueError("candidate owner must match the relation identity")
        if self.relation.endpoint_status != "not_established":
            raise ValueError("candidate relation endpoints must remain unestablished")
        if self.relation.direction_status != "not_established":
            raise ValueError("candidate relation direction must remain unestablished")
        if self.relation.is_admitted or self.relation.is_scored:
            raise ValueError("candidate relation must remain unadmitted and unscored")

    @property
    def source_binding(self) -> tuple[str, str]:
        return self.relation.source_binding


@dataclass(frozen=True, slots=True)
class PanchaPakshiUromarisiPhase9Network:
    """Deterministic node/candidate projection with no admitted edge graph."""

    condition_corpus: PanchaPakshiUromarisiPhase7LocalConditionCorpus
    aggregate: PanchaPakshiUromarisiPhase8AggregateIntelligence
    nodes: tuple[PanchaPakshiHistoricalNetworkNode, ...]
    relation_candidates: tuple[PanchaPakshiHistoricalRelationCandidate, ...]
    admitted_edges: tuple[object, ...]
    scored_edges: tuple[object, ...]
    blocked_verses: tuple[int, ...]
    metric_status: PanchaPakshiHistoricalNetworkMetricStatus = field(
        default=PanchaPakshiHistoricalNetworkMetricStatus.NOT_EVALUABLE,
        init=False,
    )
    topology_status: str = field(
        default="not_materialized_no_admitted_edges", init=False
    )
    admission_status: str = field(default="research_only", init=False)
    medical_use_status: str = field(default="forbidden", init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.condition_corpus, PanchaPakshiUromarisiPhase7LocalConditionCorpus
        ):
            raise TypeError(
                "condition_corpus must be "
                "PanchaPakshiUromarisiPhase7LocalConditionCorpus"
            )
        if not isinstance(
            self.aggregate, PanchaPakshiUromarisiPhase8AggregateIntelligence
        ):
            raise TypeError(
                "aggregate must be "
                "PanchaPakshiUromarisiPhase8AggregateIntelligence"
            )
        if self.aggregate != pancha_pakshi_uromarisi_aggregate_intelligence(
            self.condition_corpus
        ):
            raise ValueError("aggregate must exactly summarize condition_corpus")
        if not isinstance(self.nodes, tuple):
            raise TypeError("nodes must be an immutable tuple")
        if any(
            not isinstance(node, PanchaPakshiHistoricalNetworkNode)
            for node in self.nodes
        ):
            raise TypeError("nodes must contain PanchaPakshiHistoricalNetworkNode")
        if len(self.nodes) != self.aggregate.profile_count:
            raise ValueError("every local condition must have one network node")
        if tuple(node.profile for node in self.nodes) != self.condition_corpus.profiles:
            raise ValueError("nodes must preserve canonical local-condition order")
        if len(self.node_ids) != len(set(self.node_ids)):
            raise ValueError("network node identities must be unique")

        if not isinstance(self.relation_candidates, tuple):
            raise TypeError("relation_candidates must be an immutable tuple")
        if any(
            not isinstance(candidate, PanchaPakshiHistoricalRelationCandidate)
            for candidate in self.relation_candidates
        ):
            raise TypeError(
                "relation_candidates must contain "
                "PanchaPakshiHistoricalRelationCandidate"
            )
        expected_relations = tuple(
            profile.relation
            for profile in self.condition_corpus.profiles
            if profile.relation_is_detected
        )
        if tuple(
            candidate.relation for candidate in self.relation_candidates
        ) != expected_relations:
            raise ValueError(
                "relation candidates must preserve every detected clause in order"
            )
        if len(self.relation_candidates) != self.aggregate.relation_detected_count:
            raise ValueError("candidate count must equal the detected relation count")

        if not isinstance(self.admitted_edges, tuple):
            raise TypeError("admitted_edges must be an immutable tuple")
        if not isinstance(self.scored_edges, tuple):
            raise TypeError("scored_edges must be an immutable tuple")
        if self.admitted_edges or self.scored_edges:
            raise ValueError("Phase 9 has no admitted or scored relation edges")
        if self.blocked_verses != self.aggregate.blocked_verses:
            raise ValueError("network must preserve the aggregate blocked verses")

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.node_id for node in self.nodes)

    def node_for(
        self, activity: PanchaPakshiActivity, ordinal: int
    ) -> PanchaPakshiHistoricalNetworkNode | None:
        if not isinstance(activity, PanchaPakshiActivity):
            raise TypeError("activity must be PanchaPakshiActivity")
        if type(ordinal) is not int or not 1 <= ordinal <= 5:
            raise ValueError("ordinal must be an integer from 1 through 5")
        return next(
            (
                node
                for node in self.nodes
                if node.identity[0] is activity and node.identity[1] == ordinal
            ),
            None,
        )

    def candidate_for_node(
        self, node_id: str
    ) -> PanchaPakshiHistoricalRelationCandidate | None:
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("node_id must be a nonempty string")
        return next(
            (
                candidate
                for candidate in self.relation_candidates
                if candidate.owner_node_id == node_id
            ),
            None,
        )


def pancha_pakshi_uromarisi_network(
    condition_corpus: PanchaPakshiUromarisiPhase7LocalConditionCorpus,
    *,
    aggregate: PanchaPakshiUromarisiPhase8AggregateIntelligence,
) -> PanchaPakshiUromarisiPhase9Network:
    """Project already-established profile truth without inferring edges."""

    if not isinstance(
        condition_corpus, PanchaPakshiUromarisiPhase7LocalConditionCorpus
    ):
        raise TypeError(
            "condition_corpus must be PanchaPakshiUromarisiPhase7LocalConditionCorpus"
        )
    if not isinstance(aggregate, PanchaPakshiUromarisiPhase8AggregateIntelligence):
        raise TypeError(
            "aggregate must be PanchaPakshiUromarisiPhase8AggregateIntelligence"
        )
    nodes = tuple(
        PanchaPakshiHistoricalNetworkNode(profile=profile)
        for profile in condition_corpus.profiles
    )
    candidates = tuple(
        PanchaPakshiHistoricalRelationCandidate(
            owner_node_id=_node_id(profile.identity),
            relation=profile.relation,
        )
        for profile in condition_corpus.profiles
        if profile.relation_is_detected
    )
    return PanchaPakshiUromarisiPhase9Network(
        condition_corpus=condition_corpus,
        aggregate=aggregate,
        nodes=nodes,
        relation_candidates=candidates,
        admitted_edges=(),
        scored_edges=(),
        blocked_verses=aggregate.blocked_verses,
    )


__all__: tuple[str, ...] = ()

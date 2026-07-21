"""Private Phase 8 aggregate intelligence for Pancha Pakshi research.

This module counts structural facts already present in the complete Phase 7
local-condition corpus.  It performs no ranking, weighting, favorability
judgment, condition scoring, relation interpretation, prognosis, or runtime
admission.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ._pancha_pakshi_classification import (
    PanchaPakshiHistoricalClassificationPolicyId,
)
from ._pancha_pakshi_condition import (
    PanchaPakshiHistoricalLocalConditionEvaluationStatus,
    PanchaPakshiUromarisiPhase7LocalConditionCorpus,
)
from .pancha_pakshi import PanchaPakshiActivity


_ACTIVITY_ORDER = (
    PanchaPakshiActivity.EAT,
    PanchaPakshiActivity.WALK,
    PanchaPakshiActivity.RULE,
    PanchaPakshiActivity.SLEEP,
    PanchaPakshiActivity.DIE,
)


@dataclass(frozen=True, slots=True)
class PanchaPakshiUromarisiPhase8AggregateIntelligence:
    """Deterministic structural counts over the 24 Phase 7 local profiles."""

    policy_id: PanchaPakshiHistoricalClassificationPolicyId
    profile_count: int
    activity_counts: tuple[tuple[PanchaPakshiActivity, int], ...]
    evaluation_status_counts: tuple[
        tuple[PanchaPakshiHistoricalLocalConditionEvaluationStatus, int], ...
    ]
    relation_detected_count: int
    relation_not_recorded_count: int
    relation_unresolved_count: int
    relation_named_surface_count: int
    relation_admitted_count: int
    relation_scored_count: int
    blocked_verses: tuple[int, ...]
    aggregation_status: str = field(default="structural_counts_only", init=False)
    ranking_status: str = field(default="not_performed", init=False)
    weighting_status: str = field(default="not_performed", init=False)
    favorability_status: str = field(default="not_assigned", init=False)
    condition_score: None = field(default=None, init=False)
    prognosis_status: str = field(default="not_performed", init=False)
    admission_status: str = field(default="research_only", init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.policy_id, PanchaPakshiHistoricalClassificationPolicyId
        ):
            raise TypeError(
                "policy_id must be PanchaPakshiHistoricalClassificationPolicyId"
            )
        if (
            self.policy_id
            is not PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL
        ):
            raise ValueError("policy_id is not admitted for Uromarisi aggregation")
        if type(self.profile_count) is not int or self.profile_count != 24:
            raise ValueError("profile_count must equal the closed 24-cell corpus")
        if not isinstance(self.activity_counts, tuple):
            raise TypeError("activity_counts must be an immutable tuple")
        if tuple(activity for activity, _ in self.activity_counts) != _ACTIVITY_ORDER:
            raise ValueError("activity_counts must preserve canonical activity order")
        if any(type(count) is not int or count < 0 for _, count in self.activity_counts):
            raise ValueError("activity counts must be non-negative integers")
        if sum(count for _, count in self.activity_counts) != self.profile_count:
            raise ValueError("activity counts must sum to profile_count")

        if not isinstance(self.evaluation_status_counts, tuple):
            raise TypeError("evaluation_status_counts must be an immutable tuple")
        if self.evaluation_status_counts != (
            (
                PanchaPakshiHistoricalLocalConditionEvaluationStatus.NOT_EVALUABLE,
                self.profile_count,
            ),
        ):
            raise ValueError(
                "all aggregate profiles must remain explicitly not evaluable"
            )

        count_fields = (
            self.relation_detected_count,
            self.relation_not_recorded_count,
            self.relation_unresolved_count,
            self.relation_named_surface_count,
            self.relation_admitted_count,
            self.relation_scored_count,
        )
        if any(type(count) is not int or count < 0 for count in count_fields):
            raise ValueError("relation subset counts must be non-negative integers")
        if (
            self.relation_detected_count + self.relation_not_recorded_count
            != self.profile_count
        ):
            raise ValueError("detected and not-recorded counts must cover all profiles")
        if (
            self.relation_unresolved_count + self.relation_named_surface_count
            != self.relation_detected_count
        ):
            raise ValueError("unresolved and named counts must cover detected relations")
        if not (
            self.relation_scored_count
            <= self.relation_admitted_count
            <= self.relation_detected_count
        ):
            raise ValueError("scored must be a subset of admitted and detected")
        if self.relation_admitted_count != 0 or self.relation_scored_count != 0:
            raise ValueError("Phase 8 has no admitted or scored relations")

        if not isinstance(self.blocked_verses, tuple):
            raise TypeError("blocked_verses must be an immutable tuple")
        if self.blocked_verses != (250,):
            raise ValueError("the aggregate must preserve only blocked verse 250")


def pancha_pakshi_uromarisi_aggregate_intelligence(
    condition_corpus: PanchaPakshiUromarisiPhase7LocalConditionCorpus,
) -> PanchaPakshiUromarisiPhase8AggregateIntelligence:
    """Aggregate stored structural facts without interpreting any profile."""

    if not isinstance(
        condition_corpus, PanchaPakshiUromarisiPhase7LocalConditionCorpus
    ):
        raise TypeError(
            "condition_corpus must be "
            "PanchaPakshiUromarisiPhase7LocalConditionCorpus"
        )

    activity_counter = Counter(
        profile.classification.activity for profile in condition_corpus.profiles
    )
    evaluation_counter = Counter(
        profile.evaluation_status for profile in condition_corpus.profiles
    )
    return PanchaPakshiUromarisiPhase8AggregateIntelligence(
        policy_id=condition_corpus.policy.policy_id,
        profile_count=len(condition_corpus.profiles),
        activity_counts=tuple(
            (activity, activity_counter[activity]) for activity in _ACTIVITY_ORDER
        ),
        evaluation_status_counts=tuple(
            (status, evaluation_counter[status])
            for status in PanchaPakshiHistoricalLocalConditionEvaluationStatus
        ),
        relation_detected_count=sum(
            profile.relation_is_detected for profile in condition_corpus.profiles
        ),
        relation_not_recorded_count=sum(
            not profile.relation_is_detected for profile in condition_corpus.profiles
        ),
        relation_unresolved_count=sum(
            profile.relation.has_unresolved_clause
            for profile in condition_corpus.profiles
        ),
        relation_named_surface_count=sum(
            profile.relation.has_named_surface_category
            for profile in condition_corpus.profiles
        ),
        relation_admitted_count=sum(
            profile.relation_is_admitted for profile in condition_corpus.profiles
        ),
        relation_scored_count=sum(
            profile.relation_is_scored for profile in condition_corpus.profiles
        ),
        blocked_verses=(
            condition_corpus.relation_corpus.classification_corpus.blocked_verses
        ),
    )


__all__: tuple[str, ...] = ()

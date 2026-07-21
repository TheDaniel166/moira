"""Private Phase 7 integrated local conditions for Pancha Pakshi research.

This module joins one closed historical classification to its exact relation
record under the explicit Phase 4 activity/ordinal policy.  The resulting local
profile is structural and deliberately not evaluable: it creates no favorable
or unfavorable judgment, score, prognosis, advice, or runtime doctrine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ._pancha_pakshi_classification import (
    PanchaPakshiHistoricalCellClassification,
    PanchaPakshiHistoricalClassificationPolicy,
    PanchaPakshiHistoricalClassificationPolicyId,
)
from ._pancha_pakshi_relations import (
    PanchaPakshiHistoricalRelationRecord,
    PanchaPakshiUromarisiPhase5RelationCorpus,
)
from .pancha_pakshi import PanchaPakshiActivity


class PanchaPakshiHistoricalLocalConditionEvaluationStatus(str, Enum):
    """Evaluation status admitted at the private Phase 7 boundary."""

    NOT_EVALUABLE = "not_evaluable_no_admitted_condition_doctrine"


@dataclass(frozen=True, slots=True)
class PanchaPakshiHistoricalLocalConditionProfile:
    """One policy-bound classification/relation pair with no judgment."""

    classification: PanchaPakshiHistoricalCellClassification
    relation: PanchaPakshiHistoricalRelationRecord
    policy: PanchaPakshiHistoricalClassificationPolicy
    evaluation_status: PanchaPakshiHistoricalLocalConditionEvaluationStatus = field(
        default=PanchaPakshiHistoricalLocalConditionEvaluationStatus.NOT_EVALUABLE,
        init=False,
    )
    favorability_status: str = field(default="not_assigned", init=False)
    condition_score: None = field(default=None, init=False)
    prognosis_status: str = field(default="not_performed", init=False)
    medical_use_status: str = field(default="forbidden", init=False)
    admission_status: str = field(default="research_only", init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.classification, PanchaPakshiHistoricalCellClassification
        ):
            raise TypeError(
                "classification must be PanchaPakshiHistoricalCellClassification"
            )
        if not isinstance(self.relation, PanchaPakshiHistoricalRelationRecord):
            raise TypeError("relation must be PanchaPakshiHistoricalRelationRecord")
        if not isinstance(self.policy, PanchaPakshiHistoricalClassificationPolicy):
            raise TypeError(
                "policy must be PanchaPakshiHistoricalClassificationPolicy"
            )
        if (
            self.policy.policy_id
            is not PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL
        ):
            raise ValueError("policy_id is not admitted for Uromarisi local conditions")
        classification_identity = (
            self.classification.activity,
            self.classification.ordinal,
            self.classification.verse,
        )
        if classification_identity != self.relation.identity:
            raise ValueError("classification and relation identities must match")
        if self.classification.source_binding != self.relation.source_binding:
            raise ValueError("classification and relation source bindings must match")
        if self.relation.is_admitted:
            raise ValueError("Phase 7 has no admitted relation semantics")
        if self.relation.is_scored:
            raise ValueError("Phase 7 has no scored relation semantics")

    @property
    def identity(self) -> tuple[PanchaPakshiActivity, int, int]:
        """Return the shared activity, ordinal, and verse identity."""

        return (
            self.classification.activity,
            self.classification.ordinal,
            self.classification.verse,
        )

    @property
    def source_binding(self) -> tuple[str, str]:
        """Return the shared source decision identity and digest."""

        return self.classification.source_binding

    @property
    def relation_is_detected(self) -> bool:
        """Expose relation detection without interpreting the condition."""

        return self.relation.is_detected

    @property
    def relation_is_admitted(self) -> bool:
        """Expose relation admission independently from detection."""

        return self.relation.is_admitted

    @property
    def relation_is_scored(self) -> bool:
        """Expose relation scoring independently from admission."""

        return self.relation.is_scored


@dataclass(frozen=True, slots=True)
class PanchaPakshiUromarisiPhase7LocalConditionCorpus:
    """Complete private Phase 7 local-condition corpus over 24 cells."""

    policy: PanchaPakshiHistoricalClassificationPolicy
    relation_corpus: PanchaPakshiUromarisiPhase5RelationCorpus
    profiles: tuple[PanchaPakshiHistoricalLocalConditionProfile, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.policy, PanchaPakshiHistoricalClassificationPolicy):
            raise TypeError(
                "policy must be PanchaPakshiHistoricalClassificationPolicy"
            )
        if not isinstance(
            self.relation_corpus, PanchaPakshiUromarisiPhase5RelationCorpus
        ):
            raise TypeError(
                "relation_corpus must be PanchaPakshiUromarisiPhase5RelationCorpus"
            )
        if not isinstance(self.profiles, tuple):
            raise TypeError("profiles must be an immutable tuple")
        if any(
            not isinstance(profile, PanchaPakshiHistoricalLocalConditionProfile)
            for profile in self.profiles
        ):
            raise TypeError(
                "profiles must contain PanchaPakshiHistoricalLocalConditionProfile"
            )
        if len(self.profiles) != len(self.relation_corpus.records):
            raise ValueError("every relation record must have one local condition")

        for profile, classification, relation in zip(
            self.profiles,
            self.relation_corpus.classification_corpus.cells,
            self.relation_corpus.records,
            strict=True,
        ):
            if profile.policy != self.policy:
                raise ValueError("every local condition must retain the corpus policy")
            if profile.classification != classification:
                raise ValueError(
                    "local conditions must retain canonical classifications"
                )
            if profile.relation != relation:
                raise ValueError("local conditions must retain canonical relations")

    def condition_at(
        self, activity: PanchaPakshiActivity, ordinal: int
    ) -> PanchaPakshiHistoricalLocalConditionProfile | None:
        """Look up one local condition by explicit activity and ordinal."""

        if not isinstance(activity, PanchaPakshiActivity):
            raise TypeError("activity must be PanchaPakshiActivity")
        if type(ordinal) is not int or not 1 <= ordinal <= 5:
            raise ValueError("ordinal must be an integer from 1 through 5")
        return next(
            (
                profile
                for profile in self.profiles
                if profile.classification.activity is activity
                and profile.classification.ordinal == ordinal
            ),
            None,
        )

    def condition_for_verse(
        self, verse: int
    ) -> PanchaPakshiHistoricalLocalConditionProfile | None:
        """Look up one local condition without repairing blocked conflicts."""

        if type(verse) is not int or verse <= 0:
            raise ValueError("verse must be a positive integer")
        return next(
            (profile for profile in self.profiles if profile.classification.verse == verse),
            None,
        )


def pancha_pakshi_uromarisi_local_conditions_under_policy(
    relation_corpus: PanchaPakshiUromarisiPhase5RelationCorpus,
    *,
    policy: PanchaPakshiHistoricalClassificationPolicy,
) -> PanchaPakshiUromarisiPhase7LocalConditionCorpus:
    """Join exact classifications and relations under one explicit policy."""

    if not isinstance(
        relation_corpus, PanchaPakshiUromarisiPhase5RelationCorpus
    ):
        raise TypeError(
            "relation_corpus must be PanchaPakshiUromarisiPhase5RelationCorpus"
        )
    if not isinstance(policy, PanchaPakshiHistoricalClassificationPolicy):
        raise TypeError("policy must be PanchaPakshiHistoricalClassificationPolicy")
    profiles = tuple(
        PanchaPakshiHistoricalLocalConditionProfile(
            classification=classification,
            relation=relation,
            policy=policy,
        )
        for classification, relation in zip(
            relation_corpus.classification_corpus.cells,
            relation_corpus.records,
            strict=True,
        )
    )
    return PanchaPakshiUromarisiPhase7LocalConditionCorpus(
        policy=policy,
        relation_corpus=relation_corpus,
        profiles=profiles,
    )


__all__: tuple[str, ...] = ()

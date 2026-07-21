"""Private Phase 5 relation vessels for Pancha Pakshi research truth.

The vessels in this module formalize whether one already-classified historical
cell contains an activity-relation clause and, where the bounded source atom
preserves one, its exact surface category.  They do not infer endpoints,
direction, favorability, condition, score, prognosis, or runtime behavior.
Hash-bound source records remain validation-owned evidence under
``tests/fixtures``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from string import hexdigits

from ._pancha_pakshi_classification import (
    PanchaPakshiHistoricalSemanticMarker,
    PanchaPakshiUromarisiPhase2ClassificationCorpus,
)
from .pancha_pakshi import PanchaPakshiActivity


class PanchaPakshiHistoricalRelationPresence(str, Enum):
    """Source-owned relation-clause presence, without semantic inference."""

    PRESENT = "present"
    NOT_RECORDED = "not_recorded"


class PanchaPakshiHistoricalRelationSurfaceKind(str, Enum):
    """Exact bounded surface categories retained by the Phase 1 records."""

    UNRESOLVED_CLAUSE = "unresolved_clause"
    NO_ENMITY = "no_enmity"
    RULE_ENMITY_DISALLOWED = "rule_enmity_disallowed"
    RULE_ENMITY_BRANCH = "rule_enmity_branch"
    EARTH_RULE_ENMITY_DISALLOWED = "earth_rule_enmity_disallowed"
    RULE_ENMITY_REQUIRED = "rule_enmity_required"


class PanchaPakshiHistoricalRelationConfidence(str, Enum):
    """Confidence stated by the bounded atom, or its explicit absence."""

    HIGH = "high"
    MEDIUM = "medium"
    NOT_STATED = "not_stated"


_NAMED_SURFACE_KINDS = frozenset(
    kind
    for kind in PanchaPakshiHistoricalRelationSurfaceKind
    if kind is not PanchaPakshiHistoricalRelationSurfaceKind.UNRESOLVED_CLAUSE
)


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in hexdigits for character in value):
        raise ValueError(f"{label} must be one lowercase hexadecimal SHA-256")
    if value != value.lower():
        raise ValueError(f"{label} must use lowercase hexadecimal")


@dataclass(frozen=True, slots=True)
class PanchaPakshiHistoricalRelationRecord:
    """One classified cell's source-owned relation-clause state."""

    activity: PanchaPakshiActivity
    ordinal: int
    verse: int
    presence: PanchaPakshiHistoricalRelationPresence
    surface_kind: PanchaPakshiHistoricalRelationSurfaceKind | None
    confidence: PanchaPakshiHistoricalRelationConfidence
    source_decision_id: str
    source_decision_sha256: str
    endpoint_status: str = field(default="not_established", init=False)
    direction_status: str = field(default="not_established", init=False)
    runtime_semantics_status: str = field(default="not_admitted", init=False)
    scoring_status: str = field(default="not_performed", init=False)
    admission_status: str = field(default="research_only", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.activity, PanchaPakshiActivity):
            raise TypeError("activity must be PanchaPakshiActivity")
        if type(self.ordinal) is not int or not 1 <= self.ordinal <= 5:
            raise ValueError("ordinal must be an integer from 1 through 5")
        if type(self.verse) is not int or self.verse <= 0:
            raise ValueError("verse must be a positive integer")
        if not isinstance(self.presence, PanchaPakshiHistoricalRelationPresence):
            raise TypeError("presence must be PanchaPakshiHistoricalRelationPresence")
        if self.surface_kind is not None and not isinstance(
            self.surface_kind, PanchaPakshiHistoricalRelationSurfaceKind
        ):
            raise TypeError(
                "surface_kind must be PanchaPakshiHistoricalRelationSurfaceKind or None"
            )
        if not isinstance(
            self.confidence, PanchaPakshiHistoricalRelationConfidence
        ):
            raise TypeError(
                "confidence must be PanchaPakshiHistoricalRelationConfidence"
            )
        if not self.source_decision_id:
            raise ValueError("source_decision_id must not be empty")
        _require_sha256(self.source_decision_sha256, "source_decision_sha256")

        if self.presence is PanchaPakshiHistoricalRelationPresence.NOT_RECORDED:
            if self.surface_kind is not None:
                raise ValueError("a relation not recorded cannot have a surface kind")
            if self.confidence is not PanchaPakshiHistoricalRelationConfidence.NOT_STATED:
                raise ValueError("a relation not recorded must use not_stated confidence")
            return

        if self.surface_kind is None:
            raise ValueError("a present relation must retain a surface kind")
        if (
            self.surface_kind
            is PanchaPakshiHistoricalRelationSurfaceKind.UNRESOLVED_CLAUSE
        ):
            if self.confidence not in {
                PanchaPakshiHistoricalRelationConfidence.HIGH,
                PanchaPakshiHistoricalRelationConfidence.MEDIUM,
            }:
                raise ValueError(
                    "an unresolved clause must retain high or medium source confidence"
                )
        elif self.surface_kind in _NAMED_SURFACE_KINDS:
            if self.confidence is not PanchaPakshiHistoricalRelationConfidence.NOT_STATED:
                raise ValueError(
                    "a named surface category must not invent source confidence"
                )

    @property
    def source_binding(self) -> tuple[str, str]:
        """Return the immutable source decision identity and digest."""

        return self.source_decision_id, self.source_decision_sha256


@dataclass(frozen=True, slots=True)
class PanchaPakshiUromarisiPhase5RelationCorpus:
    """Complete Phase 5 relation layer over the closed 24-cell corpus."""

    classification_corpus: PanchaPakshiUromarisiPhase2ClassificationCorpus
    records: tuple[PanchaPakshiHistoricalRelationRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.classification_corpus,
            PanchaPakshiUromarisiPhase2ClassificationCorpus,
        ):
            raise TypeError(
                "classification_corpus must be "
                "PanchaPakshiUromarisiPhase2ClassificationCorpus"
            )
        if not isinstance(self.records, tuple):
            raise TypeError("records must be an immutable tuple")
        if len(self.records) != len(self.classification_corpus.cells):
            raise ValueError("every classified cell must have one relation record")

        relation_keys = tuple(
            (record.activity, record.ordinal, record.verse) for record in self.records
        )
        classification_keys = tuple(
            (cell.activity, cell.ordinal, cell.verse)
            for cell in self.classification_corpus.cells
        )
        if relation_keys != classification_keys:
            raise ValueError(
                "relation records must match classified cells in canonical order"
            )
        if len(relation_keys) != len(set(relation_keys)):
            raise ValueError("relation record identities must be unique")

        for record, classification in zip(
            self.records, self.classification_corpus.cells, strict=True
        ):
            if record.source_binding != classification.source_binding:
                raise ValueError(
                    "relation records must retain classification source bindings"
                )
            has_relation_marker = (
                PanchaPakshiHistoricalSemanticMarker.ACTIVITY_RELATION_CLAUSE
                in classification.semantic_markers
            )
            if has_relation_marker != (
                record.presence is PanchaPakshiHistoricalRelationPresence.PRESENT
            ):
                raise ValueError(
                    "relation presence must project the Phase 2 semantic marker"
                )

        if Counter(record.presence for record in self.records) != Counter(
            {
                PanchaPakshiHistoricalRelationPresence.PRESENT: 17,
                PanchaPakshiHistoricalRelationPresence.NOT_RECORDED: 7,
            }
        ):
            raise ValueError("the bounded corpus requires 17 present and 7 absent clauses")


__all__: tuple[str, ...] = ()

"""Private Phase 2 classification vessels for Pancha Pakshi research truth.

This module contains no source records and exposes no public computation.  It
provides only the typed descriptive vocabulary needed to classify the bounded
Uromarisi illness-context semantic atoms without turning them into prognosis,
condition, score, or advice.  The hash-bound records remain validation-owned
research evidence under ``tests/fixtures``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from string import hexdigits

from .pancha_pakshi import PanchaPakshiActivity


class PanchaPakshiHistoricalDisposition(str, Enum):
    """Descriptive source-statement classes; never favorable/unfavorable."""

    STATED_TO_RESOLVE = "stated_to_resolve"
    STATED_TO_ABATE = "stated_to_abate"
    TIMED_PROGRESSION_WITHOUT_EXPLICIT_RESOLUTION = (
        "timed_progression_without_explicit_resolution"
    )
    STATED_RESOLUTION_WITH_DIFFICULTY = "stated_resolution_with_difficulty"
    STATED_RESOLUTION_WITH_RECURRENCE_WARNING = (
        "stated_resolution_with_recurrence_warning"
    )
    CONDITIONAL_MORTALITY_OR_RESOLUTION = (
        "conditional_mortality_or_resolution"
    )
    BODY_DESTRUCTION_OR_MORTALITY_LANGUAGE = (
        "body_destruction_or_mortality_language"
    )
    LIFE_DEPARTURE_AND_BODY_DESTRUCTION_LANGUAGE = (
        "life_departure_and_body_destruction_language"
    )
    LIFE_DEPARTURE_WITH_RETURN_STATED_DIFFICULT = (
        "life_departure_with_return_stated_difficult"
    )
    CONDITIONAL_DEATH_OCCURRENCE_AND_BODY_DESTRUCTION_LANGUAGE = (
        "conditional_death_occurrence_and_body_destruction_language"
    )
    LIFE_DEPARTURE_AND_NO_RETURN_LANGUAGE = (
        "life_departure_and_no_return_language"
    )


class PanchaPakshiHistoricalTimeClass(str, Enum):
    """Typed shapes of source-stated time, without temporal policy binding."""

    FINITE_ALTERNATIVE_DAYS = "finite_alternative_days"
    EXACT_DAYS = "exact_days"
    UPPER_BOUND_DAYS = "upper_bound_days"
    UPPER_BOUND_MONTHS = "upper_bound_months"
    CONDITIONAL_UPPER_BOUND_MONTHS = "conditional_upper_bound_months"
    CONDITIONAL_MULTIPLE_MONTH_MARKERS = "conditional_multiple_month_markers"
    UNRECONCILED_MULTIPLE_SOURCE_MARKERS = (
        "unreconciled_multiple_source_markers"
    )
    NOT_STATED = "not_stated"


class PanchaPakshiHistoricalSemanticMarker(str, Enum):
    """Presence classes projected directly from Phase 1 semantic atoms."""

    PRESCRIBED_RESPONSE = "prescribed_response"
    TREATMENT_OR_MEDIATION_REFERENCE = "treatment_or_mediation_reference"
    ELEMENTAL_OR_DOSHA_REFERENCE = "elemental_or_dosha_reference"
    DEITY_OR_FATE_REFERENCE = "deity_or_fate_reference"
    EFFECT_REFERENCE = "effect_reference"
    ACTIVITY_RELATION_CLAUSE = "activity_relation_clause"
    MORTALITY_LANGUAGE = "mortality_language"
    SOURCE_BRANCH_REFERENCE = "source_branch_reference"


class PanchaPakshiHistoricalClassificationPolicyId(str, Enum):
    """Explicit private policies admitted over the historical classifications."""

    EXPLICIT_ACTIVITY_ORDINAL = (
        "moira_explicit_uromarisi_activity_ordinal_lookup_research_v1"
    )


_MORTALITY_DISPOSITIONS = frozenset(
    {
        PanchaPakshiHistoricalDisposition.CONDITIONAL_MORTALITY_OR_RESOLUTION,
        PanchaPakshiHistoricalDisposition.BODY_DESTRUCTION_OR_MORTALITY_LANGUAGE,
        PanchaPakshiHistoricalDisposition.LIFE_DEPARTURE_AND_BODY_DESTRUCTION_LANGUAGE,
        PanchaPakshiHistoricalDisposition.LIFE_DEPARTURE_WITH_RETURN_STATED_DIFFICULT,
        PanchaPakshiHistoricalDisposition.CONDITIONAL_DEATH_OCCURRENCE_AND_BODY_DESTRUCTION_LANGUAGE,
        PanchaPakshiHistoricalDisposition.LIFE_DEPARTURE_AND_NO_RETURN_LANGUAGE,
    }
)

_DISPOSITIONS_BY_ACTIVITY = {
    PanchaPakshiActivity.EAT: frozenset(
        {PanchaPakshiHistoricalDisposition.STATED_TO_RESOLVE}
    ),
    PanchaPakshiActivity.WALK: frozenset(
        {
            PanchaPakshiHistoricalDisposition.STATED_TO_RESOLVE,
            PanchaPakshiHistoricalDisposition.STATED_TO_ABATE,
            PanchaPakshiHistoricalDisposition.TIMED_PROGRESSION_WITHOUT_EXPLICIT_RESOLUTION,
        }
    ),
    PanchaPakshiActivity.RULE: frozenset(
        {PanchaPakshiHistoricalDisposition.STATED_TO_RESOLVE}
    ),
    PanchaPakshiActivity.SLEEP: frozenset(
        {
            PanchaPakshiHistoricalDisposition.STATED_TO_RESOLVE,
            PanchaPakshiHistoricalDisposition.STATED_RESOLUTION_WITH_DIFFICULTY,
            PanchaPakshiHistoricalDisposition.STATED_RESOLUTION_WITH_RECURRENCE_WARNING,
            PanchaPakshiHistoricalDisposition.CONDITIONAL_MORTALITY_OR_RESOLUTION,
        }
    ),
    PanchaPakshiActivity.DIE: frozenset(
        {
            PanchaPakshiHistoricalDisposition.BODY_DESTRUCTION_OR_MORTALITY_LANGUAGE,
            PanchaPakshiHistoricalDisposition.LIFE_DEPARTURE_AND_BODY_DESTRUCTION_LANGUAGE,
            PanchaPakshiHistoricalDisposition.LIFE_DEPARTURE_WITH_RETURN_STATED_DIFFICULT,
            PanchaPakshiHistoricalDisposition.CONDITIONAL_DEATH_OCCURRENCE_AND_BODY_DESTRUCTION_LANGUAGE,
            PanchaPakshiHistoricalDisposition.LIFE_DEPARTURE_AND_NO_RETURN_LANGUAGE,
        }
    ),
}

_ACTIVITY_ORDER = {
    PanchaPakshiActivity.EAT: 0,
    PanchaPakshiActivity.WALK: 1,
    PanchaPakshiActivity.RULE: 2,
    PanchaPakshiActivity.SLEEP: 3,
    PanchaPakshiActivity.DIE: 4,
}

_EXPECTED_ACTIVITY_COUNTS = {
    PanchaPakshiActivity.EAT: 5,
    PanchaPakshiActivity.WALK: 5,
    PanchaPakshiActivity.RULE: 5,
    PanchaPakshiActivity.SLEEP: 4,
    PanchaPakshiActivity.DIE: 5,
}

_EXPECTED_VERSES_BY_ACTIVITY = {
    PanchaPakshiActivity.EAT: tuple(range(230, 235)),
    PanchaPakshiActivity.WALK: tuple(range(235, 240)),
    PanchaPakshiActivity.RULE: tuple(range(241, 246)),
    PanchaPakshiActivity.SLEEP: tuple(range(246, 250)),
    PanchaPakshiActivity.DIE: tuple(range(251, 256)),
}

_TIME_CLASSES_BY_ACTIVITY = {
    PanchaPakshiActivity.EAT: frozenset(
        {
            PanchaPakshiHistoricalTimeClass.FINITE_ALTERNATIVE_DAYS,
            PanchaPakshiHistoricalTimeClass.EXACT_DAYS,
        }
    ),
    PanchaPakshiActivity.WALK: frozenset(
        {
            PanchaPakshiHistoricalTimeClass.EXACT_DAYS,
            PanchaPakshiHistoricalTimeClass.UPPER_BOUND_DAYS,
            PanchaPakshiHistoricalTimeClass.UPPER_BOUND_MONTHS,
        }
    ),
    PanchaPakshiActivity.RULE: frozenset(
        {
            PanchaPakshiHistoricalTimeClass.EXACT_DAYS,
            PanchaPakshiHistoricalTimeClass.UPPER_BOUND_DAYS,
        }
    ),
    PanchaPakshiActivity.SLEEP: frozenset(
        {
            PanchaPakshiHistoricalTimeClass.EXACT_DAYS,
            PanchaPakshiHistoricalTimeClass.UPPER_BOUND_DAYS,
            PanchaPakshiHistoricalTimeClass.CONDITIONAL_UPPER_BOUND_MONTHS,
        }
    ),
    PanchaPakshiActivity.DIE: frozenset(
        {
            PanchaPakshiHistoricalTimeClass.CONDITIONAL_MULTIPLE_MONTH_MARKERS,
            PanchaPakshiHistoricalTimeClass.UNRECONCILED_MULTIPLE_SOURCE_MARKERS,
            PanchaPakshiHistoricalTimeClass.NOT_STATED,
        }
    ),
}

_CONDITIONAL_TIME_CLASSES = frozenset(
    {
        PanchaPakshiHistoricalTimeClass.CONDITIONAL_UPPER_BOUND_MONTHS,
        PanchaPakshiHistoricalTimeClass.CONDITIONAL_MULTIPLE_MONTH_MARKERS,
    }
)


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in hexdigits for character in value):
        raise ValueError(f"{label} must be one lowercase hexadecimal SHA-256")
    if value != value.lower():
        raise ValueError(f"{label} must use lowercase hexadecimal")


@dataclass(frozen=True, slots=True)
class PanchaPakshiHistoricalClassificationPolicy:
    """Phase 4 policy requiring explicit source activity and ordinal identity."""

    policy_id: PanchaPakshiHistoricalClassificationPolicyId
    derivation_status: str = field(
        default="modern_moira_research_policy_over_source_owned_ordinals",
        init=False,
    )
    activity_input_status: str = field(
        default="caller_supplied_explicit",
        init=False,
    )
    ordinal_input_status: str = field(
        default="caller_supplied_explicit",
        init=False,
    )
    temporal_selector_binding_status: str = field(
        default="none_source_attested_or_admitted",
        init=False,
    )
    stage2k_selector_composition_status: str = field(
        default="not_admitted",
        init=False,
    )
    outcome_interpretation_status: str = field(
        default="not_performed",
        init=False,
    )
    medical_use_status: str = field(default="forbidden", init=False)
    admission_status: str = field(default="research_only", init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.policy_id, PanchaPakshiHistoricalClassificationPolicyId
        ):
            raise TypeError(
                "policy_id must be PanchaPakshiHistoricalClassificationPolicyId"
            )


@dataclass(frozen=True, slots=True)
class PanchaPakshiHistoricalCellClassification:
    """One Phase 2 classification derived from one preserved source record."""

    activity: PanchaPakshiActivity
    ordinal: int
    verse: int
    disposition: PanchaPakshiHistoricalDisposition
    time_class: PanchaPakshiHistoricalTimeClass
    semantic_markers: frozenset[PanchaPakshiHistoricalSemanticMarker]
    uncertainty_count: int
    source_decision_id: str
    source_decision_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.activity, PanchaPakshiActivity):
            raise TypeError("activity must be PanchaPakshiActivity")
        if type(self.ordinal) is not int or not 1 <= self.ordinal <= 5:
            raise ValueError("ordinal must be an integer from 1 through 5")
        if type(self.verse) is not int or self.verse <= 0:
            raise ValueError("verse must be a positive integer")
        if not isinstance(self.disposition, PanchaPakshiHistoricalDisposition):
            raise TypeError("disposition must be PanchaPakshiHistoricalDisposition")
        if self.disposition not in _DISPOSITIONS_BY_ACTIVITY[self.activity]:
            raise ValueError("disposition is not admitted for the activity")
        if not isinstance(self.time_class, PanchaPakshiHistoricalTimeClass):
            raise TypeError("time_class must be PanchaPakshiHistoricalTimeClass")
        if not isinstance(self.semantic_markers, frozenset):
            raise TypeError("semantic_markers must be a frozenset")
        if not self.semantic_markers or not all(
            isinstance(marker, PanchaPakshiHistoricalSemanticMarker)
            for marker in self.semantic_markers
        ):
            raise ValueError("semantic_markers must contain typed source markers")
        if type(self.uncertainty_count) is not int or self.uncertainty_count < 1:
            raise ValueError("every research classification must retain uncertainty")
        if not self.source_decision_id:
            raise ValueError("source_decision_id must not be empty")
        _require_sha256(self.source_decision_sha256, "source_decision_sha256")

        has_mortality = (
            PanchaPakshiHistoricalSemanticMarker.MORTALITY_LANGUAGE
            in self.semantic_markers
        )
        if has_mortality != (self.disposition in _MORTALITY_DISPOSITIONS):
            raise ValueError(
                "mortality marker must agree exactly with the source disposition"
            )
        if self.activity is PanchaPakshiActivity.DIE and not has_mortality:
            raise ValueError("every DIE classification must preserve mortality language")
        if (
            self.time_class
            is PanchaPakshiHistoricalTimeClass.UNRECONCILED_MULTIPLE_SOURCE_MARKERS
            and self.activity is not PanchaPakshiActivity.DIE
        ):
            raise ValueError("unreconciled source markers belong only to DIE here")
        if self.time_class not in _TIME_CLASSES_BY_ACTIVITY[self.activity]:
            raise ValueError("time class is not admitted for the activity")

    @property
    def identity(self) -> tuple[PanchaPakshiActivity, int]:
        """Return the already-stored activity/ordinal identity."""

        return self.activity, self.ordinal

    @property
    def source_binding(self) -> tuple[str, str]:
        """Return the immutable source decision identity and digest."""

        return self.source_decision_id, self.source_decision_sha256

    @property
    def semantic_marker_names(self) -> tuple[str, ...]:
        """Expose marker values in deterministic lexical order."""

        return tuple(sorted(marker.value for marker in self.semantic_markers))

    @property
    def has_mortality_language(self) -> bool:
        """Report presence of the stored mortality-language marker only."""

        return (
            PanchaPakshiHistoricalSemanticMarker.MORTALITY_LANGUAGE
            in self.semantic_markers
        )

    @property
    def has_stated_time(self) -> bool:
        """Distinguish an absent time expression without interpreting it."""

        return self.time_class is not PanchaPakshiHistoricalTimeClass.NOT_STATED

    @property
    def has_conditional_time(self) -> bool:
        """Report whether the stored time-shape class is conditional."""

        return self.time_class in _CONDITIONAL_TIME_CLASSES

    @property
    def has_unreconciled_time_markers(self) -> bool:
        """Report the exact unreconciled-multiple-marker time class."""

        return (
            self.time_class
            is PanchaPakshiHistoricalTimeClass.UNRECONCILED_MULTIPLE_SOURCE_MARKERS
        )


@dataclass(frozen=True, slots=True)
class PanchaPakshiHistoricalIdentityConflict:
    """A source identity conflict that has no Phase 2 classification payload."""

    verse: int
    candidate_ordinal: int
    heading_activity: PanchaPakshiActivity
    verse_activity: PanchaPakshiActivity
    commentary_activity: PanchaPakshiActivity
    source_decision_id: str
    source_decision_sha256: str

    def __post_init__(self) -> None:
        if type(self.verse) is not int or self.verse <= 0:
            raise ValueError("verse must be a positive integer")
        if type(self.candidate_ordinal) is not int or not 1 <= self.candidate_ordinal <= 5:
            raise ValueError("candidate_ordinal must be an integer from 1 through 5")
        activities = (
            self.heading_activity,
            self.verse_activity,
            self.commentary_activity,
        )
        if not all(isinstance(activity, PanchaPakshiActivity) for activity in activities):
            raise TypeError("every text layer must use PanchaPakshiActivity")
        if len(set(activities)) == 1:
            raise ValueError("a conflict requires disagreeing text-layer activities")
        if not self.source_decision_id:
            raise ValueError("source_decision_id must not be empty")
        _require_sha256(self.source_decision_sha256, "source_decision_sha256")

    @property
    def activity_by_layer(self) -> tuple[tuple[str, PanchaPakshiActivity], ...]:
        """Expose the three stored text-layer assignments without precedence."""

        return (
            ("heading", self.heading_activity),
            ("verse", self.verse_activity),
            ("commentary", self.commentary_activity),
        )

    @property
    def distinct_activities(self) -> frozenset[PanchaPakshiActivity]:
        """Return the distinct stored assignments without resolving them."""

        return frozenset(activity for _, activity in self.activity_by_layer)

    @property
    def heading_and_verse_agree(self) -> bool:
        """Expose exact agreement of the heading and verse layers."""

        return self.heading_activity is self.verse_activity

    @property
    def source_binding(self) -> tuple[str, str]:
        """Return the immutable source decision identity and digest."""

        return self.source_decision_id, self.source_decision_sha256


@dataclass(frozen=True, slots=True)
class PanchaPakshiUromarisiPhase2ClassificationCorpus:
    """Complete bounded Phase 2 corpus; not a runtime profile or outcome API."""

    witness_id: str
    cells: tuple[PanchaPakshiHistoricalCellClassification, ...]
    blocked_conflicts: tuple[PanchaPakshiHistoricalIdentityConflict, ...]

    def __post_init__(self) -> None:
        if not self.witness_id:
            raise ValueError("witness_id must not be empty")
        if not isinstance(self.cells, tuple):
            raise TypeError("cells must be an immutable tuple")
        if not isinstance(self.blocked_conflicts, tuple):
            raise TypeError("blocked_conflicts must be an immutable tuple")
        if len(self.cells) != 24:
            raise ValueError("the bounded corpus requires 24 classified cells")
        if len(self.blocked_conflicts) != 1:
            raise ValueError("the bounded corpus requires one blocked conflict")

        keys = [(cell.activity, cell.ordinal) for cell in self.cells]
        verses = [cell.verse for cell in self.cells]
        if len(keys) != len(set(keys)):
            raise ValueError("activity and ordinal identities must be unique")
        if len(verses) != len(set(verses)):
            raise ValueError("classified verse identities must be unique")
        if Counter(cell.activity for cell in self.cells) != Counter(
            _EXPECTED_ACTIVITY_COUNTS
        ):
            raise ValueError("classified activity coverage is not 5/5/5/4/5")

        expected_order = tuple(
            sorted(self.cells, key=lambda cell: (_ACTIVITY_ORDER[cell.activity], cell.ordinal))
        )
        if self.cells != expected_order:
            raise ValueError("classified cells must use deterministic activity/ordinal order")

        for activity, expected_verses in _EXPECTED_VERSES_BY_ACTIVITY.items():
            activity_cells = tuple(
                cell for cell in self.cells if cell.activity is activity
            )
            if tuple(cell.ordinal for cell in activity_cells) != tuple(
                range(1, len(expected_verses) + 1)
            ):
                raise ValueError("activity ordinals do not match the bounded corpus")
            if tuple(cell.verse for cell in activity_cells) != expected_verses:
                raise ValueError("activity verses do not match the bounded corpus")
            if len({cell.source_binding for cell in activity_cells}) != 1:
                raise ValueError("one activity must retain one source decision binding")

        conflict = self.blocked_conflicts[0]
        if conflict.verse in verses:
            raise ValueError("a blocked conflict cannot also be classified")
        if (
            conflict.verse != 250
            or conflict.candidate_ordinal != 5
            or conflict.heading_activity is not PanchaPakshiActivity.DIE
            or conflict.verse_activity is not PanchaPakshiActivity.DIE
            or conflict.commentary_activity is not PanchaPakshiActivity.SLEEP
        ):
            raise ValueError("the bounded corpus must preserve the exact verse 250 conflict")
        sleep_binding = next(
            cell.source_binding
            for cell in self.cells
            if cell.activity is PanchaPakshiActivity.SLEEP
        )
        if conflict.source_binding != sleep_binding:
            raise ValueError("verse 250 conflict must retain the SLEEP-source binding")

    @property
    def classified_verses(self) -> tuple[int, ...]:
        """Return classified verse identities in canonical corpus order."""

        return tuple(cell.verse for cell in self.cells)

    @property
    def blocked_verses(self) -> tuple[int, ...]:
        """Return blocked verse identities without treating them as cells."""

        return tuple(conflict.verse for conflict in self.blocked_conflicts)

    @property
    def activity_counts(self) -> tuple[tuple[PanchaPakshiActivity, int], ...]:
        """Return deterministic descriptive counts over existing cells."""

        counts = Counter(cell.activity for cell in self.cells)
        return tuple((activity, counts[activity]) for activity in _ACTIVITY_ORDER)

    @property
    def source_bindings(self) -> tuple[tuple[str, str], ...]:
        """Return unique source bindings in first-appearance order."""

        return tuple(dict.fromkeys(cell.source_binding for cell in self.cells))

    @property
    def mortality_language_cells(
        self,
    ) -> tuple[PanchaPakshiHistoricalCellClassification, ...]:
        """Filter only by the already-stored mortality marker."""

        return tuple(cell for cell in self.cells if cell.has_mortality_language)

    @property
    def unstated_time_cells(
        self,
    ) -> tuple[PanchaPakshiHistoricalCellClassification, ...]:
        """Filter only by the already-stored absence-of-time class."""

        return tuple(cell for cell in self.cells if not cell.has_stated_time)

    def cells_for_activity(
        self, activity: PanchaPakshiActivity
    ) -> tuple[PanchaPakshiHistoricalCellClassification, ...]:
        """Return classified cells for one explicit typed activity."""

        if not isinstance(activity, PanchaPakshiActivity):
            raise TypeError("activity must be PanchaPakshiActivity")
        return tuple(cell for cell in self.cells if cell.activity is activity)

    def classification_at(
        self, activity: PanchaPakshiActivity, ordinal: int
    ) -> PanchaPakshiHistoricalCellClassification | None:
        """Look up an existing activity/ordinal identity without fallback."""

        if not isinstance(activity, PanchaPakshiActivity):
            raise TypeError("activity must be PanchaPakshiActivity")
        if type(ordinal) is not int or not 1 <= ordinal <= 5:
            raise ValueError("ordinal must be an integer from 1 through 5")
        return next(
            (
                cell
                for cell in self.cells
                if cell.activity is activity and cell.ordinal == ordinal
            ),
            None,
        )

    def classification_for_verse(
        self, verse: int
    ) -> PanchaPakshiHistoricalCellClassification | None:
        """Look up an existing classified verse without conflict repair."""

        if type(verse) is not int or verse <= 0:
            raise ValueError("verse must be a positive integer")
        return next((cell for cell in self.cells if cell.verse == verse), None)

    def conflict_for_verse(
        self, verse: int
    ) -> PanchaPakshiHistoricalIdentityConflict | None:
        """Look up a blocked conflict independently from classification."""

        if type(verse) is not int or verse <= 0:
            raise ValueError("verse must be a positive integer")
        return next(
            (conflict for conflict in self.blocked_conflicts if conflict.verse == verse),
            None,
        )


def pancha_pakshi_uromarisi_classification_under_policy(
    corpus: PanchaPakshiUromarisiPhase2ClassificationCorpus,
    *,
    policy: PanchaPakshiHistoricalClassificationPolicy,
    activity: PanchaPakshiActivity,
    ordinal: int,
) -> PanchaPakshiHistoricalCellClassification | None:
    """Return one explicit ordinal classification under the named Phase 4 policy.

    This function performs no temporal selection.  It delegates to the exact
    Phase 3 activity/ordinal lookup and preserves absence without fallback.
    """

    if not isinstance(corpus, PanchaPakshiUromarisiPhase2ClassificationCorpus):
        raise TypeError(
            "corpus must be PanchaPakshiUromarisiPhase2ClassificationCorpus"
        )
    if not isinstance(policy, PanchaPakshiHistoricalClassificationPolicy):
        raise TypeError("policy must be PanchaPakshiHistoricalClassificationPolicy")
    if (
        policy.policy_id
        is not PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL
    ):
        raise ValueError("policy_id is not admitted for Uromarisi classification")
    return corpus.classification_at(activity, ordinal)


__all__: tuple[str, ...] = ()

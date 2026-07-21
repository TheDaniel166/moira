"""Private, source-bound Pancha Pakshi research foundation.

This module does not define a default Pancha Pakshi canon.  A caller must name
an explicitly bundled profile, and every bundled profile declares its product
kind and admission status.  The only initial-vowel identity implemented here
is the 1879 witness's *aksara* (question/name-initial) identity; it is not a
natal Moon or nakshatra identity.

The 1879 tables are materialized from the machine-reconciled reading of four
source-stated transition rules.  Identified grid axes govern bird/activity
assignments, while explicit prose and verse govern chronology; visual grid
order is never treated as chronological authority.  Each generated cell
retains the governing rule, grid, and duration locators.

No scoring, cross-witness relationship normalization, or vinadi subdivision
is performed in this private layer.  Astronomical paksha inference is a
separate, source-mapped product and never ambiently selects or materializes a
schedule.  The 2024 natal profile is separately parsed and preserves its
source nakshatra-bird table as an object distinct from Moira's modern
birth-Moon and Lahiri composition.  The one relationship surface remains the
source-scoped, explicitly directed 20-cell matrix from the 1879 witness.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any

from .pancha_pakshi import (
    PanchaPakshiActivity,
    PanchaPakshiAdmissionStatus,
    PanchaPakshiAstronomicalPaksha,
    PanchaPakshiBird,
    PanchaPakshiCapability,
    PanchaPakshiConflictWitness,
    PanchaPakshiDataError,
    PanchaPakshiDirectedRelationship,
    PanchaPakshiHalf,
    PanchaPakshiInitialVowelIdentity,
    PanchaPakshiOmission,
    PanchaPakshiPaksha,
    PanchaPakshiProfileDescriptor,
    PanchaPakshiProfileInfo,
    PanchaPakshiProvenance,
    PanchaPakshiRelation,
    PanchaPakshiSchedule,
    PanchaPakshiScheduleCell,
    PanchaPakshiSource,
    PanchaPakshiSourceLocator,
    PanchaPakshiSookshmaSelectorPolicyId,
    PanchaPakshiWeekday,
)


_DATA_DIRECTORY = Path(__file__).resolve().parent / "data"
_MANIFEST_PATH = _DATA_DIRECTORY / "pancha_pakshi_manifest.json"
_HASH_CANONICALIZATION = (
    "UTF-8 text with CRLF and CR normalized to LF before hashing"
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


_BIRDS = tuple(PanchaPakshiBird)
_ACTIVITIES = tuple(PanchaPakshiActivity)
_WEEKDAYS = tuple(PanchaPakshiWeekday)
_CONTEXTS = {
    (PanchaPakshiPaksha.PURVA, PanchaPakshiHalf.DAY): "purva_day",
    (PanchaPakshiPaksha.PURVA, PanchaPakshiHalf.NIGHT): "purva_night",
    (PanchaPakshiPaksha.AMARA, PanchaPakshiHalf.DAY): "amara_day",
    (PanchaPakshiPaksha.AMARA, PanchaPakshiHalf.NIGHT): "amara_night",
}
_REQUIRED_OMISSIONS = {
    "authority_birds",
    "natal_mapping",
    "scoring",
    "cross_witness_normalized_relationship_policy",
    "vinadi",
    "seasonal_scaling",
}
_REQUIRED_NATAL_OMISSIONS = {
    "aksara_identity",
    "nominal_schedule",
    "directed_relationships",
    "clock_materialization",
    "current_cell_selection",
    "authority_birds",
    "vinadi",
    "condition",
    "scoring",
    "window_search",
}
_REQUIRED_PADU_OMISSIONS = {
    "aksara_identity",
    "nakshatra_bird_mapping",
    "natal_identity",
    "nominal_schedule",
    "directed_relationships",
    "astronomical_paksha_inference",
    "clock_materialization",
    "current_cell_selection",
    "authority_birds",
    "adhikara_bird_mapping",
    "bharana_bird_mapping",
    "vinadi",
    "condition",
    "scoring",
    "window_search",
}
_REQUIRED_SOOKSHMA_OMISSIONS = {
    "uromarisi_outcome_binding",
    "clock_or_civil_time_routing",
    "astronomical_context",
    "schedule_composition",
    "natal_identity",
    "padu_bird_mapping",
    "outcome_interpretation",
    "condition",
    "scoring",
    "window_search",
}
_PRODUCT_CAPABILITIES = {
    "aksara_prasna_operating_schedule": (
        PanchaPakshiCapability.AKSARA_IDENTITY,
        PanchaPakshiCapability.NOMINAL_SCHEDULE,
        PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING,
        PanchaPakshiCapability.DIRECTED_RELATIONSHIPS,
        PanchaPakshiCapability.ASTRONOMICAL_CONTEXT,
        PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE,
        PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION,
        PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION,
        PanchaPakshiCapability.SOLAR_PROPORTIONAL_MATERIALIZATION,
        PanchaPakshiCapability.SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION,
    ),
    "natal_moon_bird_identity": (
        PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING,
        PanchaPakshiCapability.NATAL_IDENTITY,
    ),
    "padu_bird_mapping": (PanchaPakshiCapability.PADU_BIRD_MAPPING,),
    "sookshma_temporal_selector": (
        PanchaPakshiCapability.SOOKSHMA_TEMPORAL_SELECTION,
    ),
}
_PUBLIC_ADMISSION_STATUSES = frozenset(
    {
        PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
        PanchaPakshiAdmissionStatus.CORROBORATED_PUBLIC,
    }
)


@dataclass(frozen=True, slots=True)
class _VowelRule:
    symbols: tuple[str, ...]
    bird: PanchaPakshiBird
    source_locator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _TemporalModel:
    model_kind: str
    day_span_nazhigai: Fraction
    night_span_nazhigai: Fraction
    samam_count_per_half: int
    samam_span_nazhigai: Fraction
    source_locator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _DurationRule:
    activity: PanchaPakshiActivity
    duration_nazhigai: Fraction
    source_locator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _RelationshipRule:
    subject: PanchaPakshiBird
    target: PanchaPakshiBird
    relation: PanchaPakshiRelation
    source_locator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _LunarPakshaMappingRule:
    lunar_phase_half: str
    astronomical_paksha: PanchaPakshiAstronomicalPaksha
    profile_paksha: PanchaPakshiPaksha
    source_locator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _NakshatraBirdRule:
    profile_paksha: PanchaPakshiPaksha
    nakshatra_index: int
    nakshatra: str
    bird: PanchaPakshiBird
    source_locator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PaduBirdRule:
    profile_paksha: PanchaPakshiPaksha
    weekday: PanchaPakshiWeekday
    bird: PanchaPakshiBird
    source_locator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ScheduleGenerator:
    generator_id: str
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    first_eat_by_weekday: tuple[PanchaPakshiBird, ...]
    eat_step_per_samam: int
    activity_offsets: tuple[tuple[PanchaPakshiActivity, int], ...]
    chronological_activities: tuple[PanchaPakshiActivity, ...]
    source_locator_ids: tuple[str, ...]

    def first_eat_bird_for(
        self,
        weekday: PanchaPakshiWeekday,
    ) -> PanchaPakshiBird:
        """Return the source-labelled weekday seed from this generator."""

        if not isinstance(weekday, PanchaPakshiWeekday):
            raise TypeError("weekday must be a PanchaPakshiWeekday")
        for candidate, bird in zip(
            _WEEKDAYS,
            self.first_eat_by_weekday,
            strict=True,
        ):
            if candidate is weekday:
                return bird
        raise PanchaPakshiDataError(
            f"generator {self.generator_id!r} has no first-EAT seed for "
            f"{weekday.value!r}"
        )

    def offset_for(self, activity: PanchaPakshiActivity) -> int:
        for candidate, offset in self.activity_offsets:
            if candidate is activity:
                return offset
        raise PanchaPakshiDataError(
            f"generator {self.generator_id!r} has no offset for {activity.value!r}"
        )


@dataclass(frozen=True, slots=True)
class PanchaPakshiProfile:
    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: tuple[PanchaPakshiCapability, ...]
    admission_decision_id: str
    derivation_status: str
    assembly_policy: str
    title: str
    source: PanchaPakshiSource
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    birds: tuple[PanchaPakshiBird, ...]
    weekdays: tuple[PanchaPakshiWeekday, ...]
    activities: tuple[PanchaPakshiActivity, ...]
    initial_vowel_identity_kind: str
    initial_vowel_is_natal_moon_identity: bool
    vowel_rules: tuple[_VowelRule, ...]
    lunar_paksha_mapping_kind: str
    lunar_paksha_mapping_rules: tuple[_LunarPakshaMappingRule, ...]
    temporal_model: _TemporalModel
    duration_rules: tuple[_DurationRule, ...]
    generators: tuple[_ScheduleGenerator, ...]
    relationship_model_kind: str
    relationship_self_policy: str
    relationship_rules: tuple[_RelationshipRule, ...]
    explicit_omissions: tuple[PanchaPakshiOmission, ...]
    research_conflict_ledger: tuple[PanchaPakshiConflictWitness, ...]

    def locator(self, locator_id: str) -> PanchaPakshiSourceLocator:
        for locator in self.source_locators:
            if locator.locator_id == locator_id:
                return locator
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} references unknown locator {locator_id!r}"
        )

    def duration_rule(
        self, activity: PanchaPakshiActivity
    ) -> _DurationRule:
        for rule in self.duration_rules:
            if rule.activity is activity:
                return rule
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} has no duration for {activity.value!r}"
        )

    def generator(
        self, paksha: PanchaPakshiPaksha, half: PanchaPakshiHalf
    ) -> _ScheduleGenerator:
        for generator in self.generators:
            if generator.paksha is paksha and generator.half is half:
                return generator
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} has no {paksha.value}_{half.value} generator"
        )

    def relationship_rule(
        self, subject: PanchaPakshiBird, target: PanchaPakshiBird
    ) -> _RelationshipRule:
        for rule in self.relationship_rules:
            if rule.subject is subject and rule.target is target:
                return rule
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} has no directed relationship "
            f"{subject.value!r} -> {target.value!r}"
        )

    def lunar_paksha_mapping_rule(
        self,
        astronomical_paksha: PanchaPakshiAstronomicalPaksha,
    ) -> _LunarPakshaMappingRule:
        if not isinstance(
            astronomical_paksha,
            PanchaPakshiAstronomicalPaksha,
        ):
            raise TypeError(
                "astronomical_paksha must be a PanchaPakshiAstronomicalPaksha"
            )
        for rule in self.lunar_paksha_mapping_rules:
            if rule.astronomical_paksha is astronomical_paksha:
                return rule
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} has no mapping for "
            f"{astronomical_paksha.value!r}"
        )


@dataclass(frozen=True, slots=True)
class PanchaPakshiNatalIdentityProfile:
    """Strict internal profile for a source table plus modern natal policy."""

    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: tuple[PanchaPakshiCapability, ...]
    admission_decision_id: str
    derivation_status: str
    assembly_policy: str
    title: str
    source: PanchaPakshiSource
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    lunar_paksha_mapping_kind: str
    lunar_paksha_mapping_rules: tuple[_LunarPakshaMappingRule, ...]
    nakshatra_bird_mapping_kind: str
    source_table_semantics: str
    modern_composition_kind: str
    nakshatra_bird_rules: tuple[_NakshatraBirdRule, ...]
    explicit_omissions: tuple[PanchaPakshiOmission, ...]
    research_conflict_ledger: tuple[PanchaPakshiConflictWitness, ...]

    def locator(self, locator_id: str) -> PanchaPakshiSourceLocator:
        for locator in self.source_locators:
            if locator.locator_id == locator_id:
                return locator
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} references unknown locator {locator_id!r}"
        )

    def lunar_paksha_mapping_rule(
        self,
        astronomical_paksha: PanchaPakshiAstronomicalPaksha,
    ) -> _LunarPakshaMappingRule:
        if not isinstance(astronomical_paksha, PanchaPakshiAstronomicalPaksha):
            raise TypeError(
                "astronomical_paksha must be a PanchaPakshiAstronomicalPaksha"
            )
        for rule in self.lunar_paksha_mapping_rules:
            if rule.astronomical_paksha is astronomical_paksha:
                return rule
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} has no mapping for "
            f"{astronomical_paksha.value!r}"
        )

    def nakshatra_bird_rule(
        self,
        profile_paksha: PanchaPakshiPaksha,
        nakshatra_index: int,
    ) -> _NakshatraBirdRule:
        if not isinstance(profile_paksha, PanchaPakshiPaksha):
            raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
        if isinstance(nakshatra_index, bool) or not isinstance(
            nakshatra_index,
            int,
        ):
            raise TypeError("nakshatra_index must be an integer")
        for rule in self.nakshatra_bird_rules:
            if (
                rule.profile_paksha is profile_paksha
                and rule.nakshatra_index == nakshatra_index
            ):
                return rule
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} has no {profile_paksha.value!r} "
            f"mapping for nakshatra index {nakshatra_index}"
        )


@dataclass(frozen=True, slots=True)
class PanchaPakshiPaduBirdProfile:
    """Strict internal profile for one source-owned Padu-bird table."""

    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: tuple[PanchaPakshiCapability, ...]
    admission_decision_id: str
    derivation_status: str
    assembly_policy: str
    title: str
    source: PanchaPakshiSource
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    padu_bird_mapping_kind: str
    source_table_semantics: str
    padu_bird_rules: tuple[_PaduBirdRule, ...]
    explicit_omissions: tuple[PanchaPakshiOmission, ...]
    research_conflict_ledger: tuple[PanchaPakshiConflictWitness, ...]

    def locator(self, locator_id: str) -> PanchaPakshiSourceLocator:
        for locator in self.source_locators:
            if locator.locator_id == locator_id:
                return locator
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} references unknown locator "
            f"{locator_id!r}"
        )

    def padu_bird_rule(
        self,
        profile_paksha: PanchaPakshiPaksha,
        weekday: PanchaPakshiWeekday,
    ) -> _PaduBirdRule:
        if not isinstance(profile_paksha, PanchaPakshiPaksha):
            raise TypeError("profile_paksha must be a PanchaPakshiPaksha")
        if not isinstance(weekday, PanchaPakshiWeekday):
            raise TypeError("weekday must be a PanchaPakshiWeekday")
        for rule in self.padu_bird_rules:
            if rule.profile_paksha is profile_paksha and rule.weekday is weekday:
                return rule
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} has no {profile_paksha.value!r} "
            f"Padu bird for {weekday.value!r}"
        )


@dataclass(frozen=True, slots=True)
class _SookshmaSelectorRule:
    policy_id: PanchaPakshiSookshmaSelectorPolicyId
    source_layer: str
    partition_kind: str
    container_span_nazhigai: Fraction
    interval_count: int
    interval_ownership: str
    sequence_policy: str
    activity_assignment_status: str
    activity_durations_nazhigai: tuple[
        tuple[PanchaPakshiActivity, Fraction], ...
    ]
    source_locator_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PanchaPakshiSookshmaSelectorProfile:
    """Strict profile for two distinct source-attested Sookshma selectors."""

    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: tuple[PanchaPakshiCapability, ...]
    admission_decision_id: str
    derivation_status: str
    assembly_policy: str
    title: str
    source: PanchaPakshiSource
    source_locators: tuple[PanchaPakshiSourceLocator, ...]
    selector_rules: tuple[_SookshmaSelectorRule, ...]
    automatic_policy_selection: str
    uromarisi_composition_status: str
    outcome_interpretation_status: str
    explicit_omissions: tuple[PanchaPakshiOmission, ...]
    research_conflict_ledger: tuple[PanchaPakshiConflictWitness, ...]

    def locator(self, locator_id: str) -> PanchaPakshiSourceLocator:
        for locator in self.source_locators:
            if locator.locator_id == locator_id:
                return locator
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} references unknown locator "
            f"{locator_id!r}"
        )

    def sookshma_policy_rule(
        self,
        policy_id: PanchaPakshiSookshmaSelectorPolicyId,
    ) -> _SookshmaSelectorRule:
        if not isinstance(policy_id, PanchaPakshiSookshmaSelectorPolicyId):
            raise TypeError(
                "policy_id must be a PanchaPakshiSookshmaSelectorPolicyId"
            )
        for rule in self.selector_rules:
            if rule.policy_id is policy_id:
                return rule
        raise PanchaPakshiDataError(
            f"profile {self.profile_id!r} has no selector policy "
            f"{policy_id.value!r}"
        )


PanchaPakshiAnyProfile = (
    PanchaPakshiProfile
    | PanchaPakshiNatalIdentityProfile
    | PanchaPakshiPaduBirdProfile
    | PanchaPakshiSookshmaSelectorProfile
)


def available_pancha_pakshi_profiles() -> tuple[PanchaPakshiProfileDescriptor, ...]:
    """List explicitly admitted public profiles; no default is selected."""

    entries = _read_manifest(_MANIFEST_PATH)
    return tuple(
        PanchaPakshiProfileDescriptor(
            profile_id=entry["profile_id"],
            admission_status=PanchaPakshiAdmissionStatus(entry["admission_status"]),
            product_kind=entry["product_kind"],
            default_selection_allowed=entry["default_selection_allowed"],
            capabilities=tuple(
                PanchaPakshiCapability(value) for value in entry["capabilities"]
            ),
            admission_decision_id=entry["admission_decision_id"],
        )
        for entry in entries
        if PanchaPakshiAdmissionStatus(entry["admission_status"])
        in _PUBLIC_ADMISSION_STATUSES
    )


def load_pancha_pakshi_profile(profile_id: str) -> PanchaPakshiAnyProfile:
    """Load one explicitly named, hash-verified internal profile."""

    if not isinstance(profile_id, str):
        raise TypeError("profile_id must be a string")
    if not profile_id:
        raise ValueError("profile_id must not be empty; there is no default canon")
    return _load_profile_cached(profile_id, str(_MANIFEST_PATH.resolve()))


def _profile_provenance(
    profile: PanchaPakshiAnyProfile,
    *,
    astronomical_routing_status: str = "not_performed",
) -> PanchaPakshiProvenance:
    if not isinstance(astronomical_routing_status, str) or not (
        astronomical_routing_status.strip()
    ):
        raise PanchaPakshiDataError(
            "astronomical_routing_status must be a non-empty string"
        )
    return PanchaPakshiProvenance(
        profile_id=profile.profile_id,
        admission_status=profile.admission_status,
        product_kind=profile.product_kind,
        default_selection_allowed=profile.default_selection_allowed,
        capabilities=profile.capabilities,
        admission_decision_id=profile.admission_decision_id,
        derivation_status=profile.derivation_status,
        assembly_policy=profile.assembly_policy,
        astronomical_routing_status=astronomical_routing_status,
        source=profile.source,
        declared_omissions=profile.explicit_omissions,
    )


def pancha_pakshi_profile_info(
    profile: PanchaPakshiAnyProfile,
) -> PanchaPakshiProfileInfo:
    """Return public profile metadata without exposing loader internals."""

    _require_any_profile(profile)
    return PanchaPakshiProfileInfo(
        title=profile.title,
        provenance=_profile_provenance(profile),
        source_locators=profile.source_locators,
        known_conflict_witnesses=profile.research_conflict_ledger,
    )


def pancha_pakshi_identity_from_initial_vowel(
    profile: PanchaPakshiProfile,
    initial_vowel: str,
) -> PanchaPakshiInitialVowelIdentity:
    """Resolve the witness's aksara query/name-initial identity only."""

    _require_profile(profile)
    if not isinstance(initial_vowel, str):
        raise TypeError("initial_vowel must be a string")
    symbol = initial_vowel.strip()
    if len(symbol) != 1:
        raise ValueError(
            "initial_vowel must be one explicitly listed vowel symbol; "
            "name parsing and extended vowel groups are not inferred"
        )
    normalized = symbol.upper() if symbol.isascii() else symbol
    for rule in profile.vowel_rules:
        if normalized in rule.symbols:
            return PanchaPakshiInitialVowelIdentity(
                profile_id=profile.profile_id,
                identity_kind=profile.initial_vowel_identity_kind,
                input_symbol=initial_vowel,
                normalized_symbol=normalized,
                bird=rule.bird,
                is_natal_moon_identity=profile.initial_vowel_is_natal_moon_identity,
                source_locators=_resolve_locators(
                    profile, rule.source_locator_ids
                ),
                provenance=_profile_provenance(profile),
            )
    raise ValueError(
        f"initial_vowel {initial_vowel!r} is not explicitly mapped by "
        f"profile {profile.profile_id!r}"
    )


def pancha_pakshi_directed_relationship(
    profile: PanchaPakshiProfile,
    subject: PanchaPakshiBird,
    target: PanchaPakshiBird,
) -> PanchaPakshiDirectedRelationship:
    """Return one explicitly stored directed relationship; never infer reciprocity."""

    _require_profile(profile)
    if not isinstance(subject, PanchaPakshiBird):
        raise TypeError("subject must be a PanchaPakshiBird")
    if not isinstance(target, PanchaPakshiBird):
        raise TypeError("target must be a PanchaPakshiBird")
    if subject is target:
        raise ValueError("the 1879 relationship matrix leaves self-relation undefined")
    rule = profile.relationship_rule(subject, target)
    return PanchaPakshiDirectedRelationship(
        profile_id=profile.profile_id,
        model_kind=profile.relationship_model_kind,
        subject=subject,
        target=target,
        relation=rule.relation,
        is_reciprocal_inference=False,
        source_locators=_resolve_locators(profile, rule.source_locator_ids),
        provenance=_profile_provenance(profile),
    )


def generate_pancha_pakshi_schedule(
    profile: PanchaPakshiProfile,
    *,
    paksha: PanchaPakshiPaksha,
    half: PanchaPakshiHalf,
    weekday: PanchaPakshiWeekday,
) -> PanchaPakshiSchedule:
    """Generate an exact nominal schedule from one explicit source context."""

    _require_profile(profile)
    if not isinstance(paksha, PanchaPakshiPaksha):
        raise TypeError("paksha must be a PanchaPakshiPaksha")
    if not isinstance(half, PanchaPakshiHalf):
        raise TypeError("half must be a PanchaPakshiHalf")
    if not isinstance(weekday, PanchaPakshiWeekday):
        raise TypeError("weekday must be a PanchaPakshiWeekday")

    generator = profile.generator(paksha, half)
    first_eat = generator.first_eat_bird_for(weekday)
    span = (
        profile.temporal_model.day_span_nazhigai
        if half is PanchaPakshiHalf.DAY
        else profile.temporal_model.night_span_nazhigai
    )
    cells: list[PanchaPakshiScheduleCell] = []
    cursor = Fraction(0)
    first_index = profile.birds.index(first_eat)

    for samam_zero in range(profile.temporal_model.samam_count_per_half):
        base_index = (
            first_index + generator.eat_step_per_samam * samam_zero
        ) % len(profile.birds)
        samam_start = cursor
        samam_pairs: set[tuple[PanchaPakshiBird, PanchaPakshiActivity]] = set()
        for sequence_zero, activity in enumerate(
            generator.chronological_activities
        ):
            bird = profile.birds[
                (base_index + generator.offset_for(activity))
                % len(profile.birds)
            ]
            duration_rule = profile.duration_rule(activity)
            end = cursor + duration_rule.duration_nazhigai
            locator_ids = _dedupe(
                profile.temporal_model.source_locator_ids
                + generator.source_locator_ids
                + duration_rule.source_locator_ids
            )
            cell = PanchaPakshiScheduleCell(
                samam_index=samam_zero + 1,
                sequence_index=sequence_zero + 1,
                bird=bird,
                activity=activity,
                start_nazhigai=cursor,
                end_nazhigai=end,
                duration_nazhigai=duration_rule.duration_nazhigai,
                derivation_status=profile.derivation_status,
                assembly_policy=profile.assembly_policy,
                source_locators=_resolve_locators(profile, locator_ids),
            )
            cells.append(cell)
            samam_pairs.add((bird, activity))
            cursor = end

        samam_cells = cells[-len(profile.activities) :]
        if {cell.bird for cell in samam_cells} != set(profile.birds):
            raise PanchaPakshiDataError(
                f"generator {generator.generator_id!r} does not assign every "
                f"bird exactly once in samam {samam_zero + 1}"
            )
        if {cell.activity for cell in samam_cells} != set(profile.activities):
            raise PanchaPakshiDataError(
                f"generator {generator.generator_id!r} does not assign every "
                f"activity exactly once in samam {samam_zero + 1}"
            )
        if len(samam_pairs) != len(profile.activities):
            raise PanchaPakshiDataError("duplicate bird/activity cell in samam")
        if cursor - samam_start != profile.temporal_model.samam_span_nazhigai:
            raise PanchaPakshiDataError(
                f"generator {generator.generator_id!r} has a non-six-nazhigai samam"
            )

    expected_pairs = {
        (bird, activity) for bird in profile.birds for activity in profile.activities
    }
    if {(cell.bird, cell.activity) for cell in cells} != expected_pairs:
        raise PanchaPakshiDataError(
            f"generator {generator.generator_id!r} does not cover each "
            "bird/activity pair exactly once per half"
        )
    if len(cells) != len(expected_pairs):
        raise PanchaPakshiDataError(
            f"generator {generator.generator_id!r} emitted duplicate cells"
        )
    if cursor != span:
        raise PanchaPakshiDataError(
            f"generator {generator.generator_id!r} ends at {cursor}, not {span}"
        )
    if any(not cell.source_locators for cell in cells):
        raise PanchaPakshiDataError("generated cell lacks source provenance")

    return PanchaPakshiSchedule(
        profile_id=profile.profile_id,
        admission_status=profile.admission_status,
        product_kind=profile.product_kind,
        generator_id=generator.generator_id,
        paksha=paksha,
        half=half,
        weekday=weekday,
        first_eat_bird=first_eat,
        temporal_model_kind=profile.temporal_model.model_kind,
        span_nazhigai=span,
        samam_span_nazhigai=profile.temporal_model.samam_span_nazhigai,
        cells=tuple(cells),
        provenance=_profile_provenance(profile),
    )


def generate_purva_day_schedule(
    profile: PanchaPakshiProfile, weekday: PanchaPakshiWeekday
) -> PanchaPakshiSchedule:
    return generate_pancha_pakshi_schedule(
        profile,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=weekday,
    )


def generate_purva_night_schedule(
    profile: PanchaPakshiProfile, weekday: PanchaPakshiWeekday
) -> PanchaPakshiSchedule:
    return generate_pancha_pakshi_schedule(
        profile,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.NIGHT,
        weekday=weekday,
    )


def generate_amara_day_schedule(
    profile: PanchaPakshiProfile, weekday: PanchaPakshiWeekday
) -> PanchaPakshiSchedule:
    return generate_pancha_pakshi_schedule(
        profile,
        paksha=PanchaPakshiPaksha.AMARA,
        half=PanchaPakshiHalf.DAY,
        weekday=weekday,
    )


def generate_amara_night_schedule(
    profile: PanchaPakshiProfile, weekday: PanchaPakshiWeekday
) -> PanchaPakshiSchedule:
    return generate_pancha_pakshi_schedule(
        profile,
        paksha=PanchaPakshiPaksha.AMARA,
        half=PanchaPakshiHalf.NIGHT,
        weekday=weekday,
    )


def _require_profile(profile: PanchaPakshiProfile) -> None:
    if not isinstance(profile, PanchaPakshiProfile):
        raise TypeError("profile must be a PanchaPakshiProfile")


def _require_any_profile(profile: PanchaPakshiAnyProfile) -> None:
    if not isinstance(
        profile,
        (
            PanchaPakshiProfile,
            PanchaPakshiNatalIdentityProfile,
            PanchaPakshiPaduBirdProfile,
            PanchaPakshiSookshmaSelectorProfile,
        ),
    ):
        raise TypeError("profile must be a registered Pancha Pakshi profile")


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _resolve_locators(
    profile: PanchaPakshiAnyProfile, locator_ids: tuple[str, ...]
) -> tuple[PanchaPakshiSourceLocator, ...]:
    return tuple(profile.locator(locator_id) for locator_id in locator_ids)


def _canonical_bytes(path: Path) -> bytes:
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PanchaPakshiDataError(f"cannot read UTF-8 data file {path}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(_canonical_bytes(path))
    except json.JSONDecodeError as exc:
        raise PanchaPakshiDataError(f"invalid JSON in {path}: {exc}") from exc


def _require_dict(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PanchaPakshiDataError(f"{context} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise PanchaPakshiDataError(f"{context} has a non-string key")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise PanchaPakshiDataError(f"{context} must be an array")
    return value


def _require_exact_keys(
    value: dict[str, Any], expected: set[str], context: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise PanchaPakshiDataError(
            f"{context} schema mismatch; missing={missing}, unknown={unknown}"
        )


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise PanchaPakshiDataError(f"{context} must be a non-empty string")
    return value


def _require_utc_timestamp(value: Any, context: str) -> str:
    text = _require_string(value, context)
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise PanchaPakshiDataError(
            f"{context} must be an ISO-8601 UTC timestamp"
        ) from exc
    return text


def _require_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PanchaPakshiDataError(f"{context} must be an integer")
    return value


def _require_bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise PanchaPakshiDataError(f"{context} must be a boolean")
    return value


def _require_enum(enum_type: type[Enum], value: Any, context: str) -> Any:
    text = _require_string(value, context)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise PanchaPakshiDataError(
            f"{context} contains unknown value {text!r}"
        ) from exc


def _parse_fraction(value: Any, context: str) -> Fraction:
    obj = _require_dict(value, context)
    _require_exact_keys(obj, {"numerator", "denominator"}, context)
    numerator = _require_int(obj["numerator"], f"{context}.numerator")
    denominator = _require_int(obj["denominator"], f"{context}.denominator")
    if denominator <= 0:
        raise PanchaPakshiDataError(f"{context}.denominator must be positive")
    if math.gcd(abs(numerator), denominator) != 1:
        raise PanchaPakshiDataError(f"{context} must be in reduced exact form")
    return Fraction(numerator, denominator)


def _parse_locator_ids(
    value: Any, context: str, known_locator_ids: set[str]
) -> tuple[str, ...]:
    raw = _require_list(value, context)
    if not raw:
        raise PanchaPakshiDataError(f"{context} must not be empty")
    locator_ids = tuple(
        _require_string(item, f"{context}[{index}]")
        for index, item in enumerate(raw)
    )
    if len(locator_ids) != len(set(locator_ids)):
        raise PanchaPakshiDataError(f"{context} contains duplicate locators")
    unknown = set(locator_ids) - known_locator_ids
    if unknown:
        raise PanchaPakshiDataError(
            f"{context} references unknown locators {sorted(unknown)}"
        )
    return locator_ids


def _read_manifest(path: Path) -> tuple[dict[str, Any], ...]:
    manifest = _require_dict(_read_json(path), "pancha_pakshi_manifest")
    _require_exact_keys(
        manifest,
        {
            "schema_version",
            "generated_at_utc",
            "hash_algorithm",
            "hash_canonicalization",
            "profiles",
        },
        "pancha_pakshi_manifest",
    )
    if _require_int(manifest["schema_version"], "manifest.schema_version") != 2:
        raise PanchaPakshiDataError("unsupported Pancha Pakshi manifest schema")
    _require_utc_timestamp(
        manifest["generated_at_utc"], "manifest.generated_at_utc"
    )
    if manifest["hash_algorithm"] != "sha256":
        raise PanchaPakshiDataError("manifest hash_algorithm must be sha256")
    if manifest["hash_canonicalization"] != _HASH_CANONICALIZATION:
        raise PanchaPakshiDataError("unknown manifest hash canonicalization")
    raw_entries = _require_list(manifest["profiles"], "manifest.profiles")
    if not raw_entries:
        raise PanchaPakshiDataError("manifest.profiles must not be empty")
    entries: list[dict[str, Any]] = []
    profile_ids: set[str] = set()
    paths: set[str] = set()
    admission_decision_ids: set[str] = set()
    for index, raw_entry in enumerate(raw_entries):
        context = f"manifest.profiles[{index}]"
        entry = _require_dict(raw_entry, context)
        _require_exact_keys(
            entry,
            {
                "profile_id",
                "path",
                "sha256",
                "admission_status",
                "product_kind",
                "default_selection_allowed",
                "capabilities",
                "admission_decision_id",
            },
            context,
        )
        profile_id = _require_string(entry["profile_id"], f"{context}.profile_id")
        relative = Path(_require_string(entry["path"], f"{context}.path"))
        if relative.is_absolute() or len(relative.parts) != 1 or relative.suffix != ".json":
            raise PanchaPakshiDataError(f"{context}.path must be one flat JSON filename")
        digest = _require_string(entry["sha256"], f"{context}.sha256")
        if not _SHA256_PATTERN.fullmatch(digest):
            raise PanchaPakshiDataError(f"{context}.sha256 is not a lowercase SHA-256")
        admission_status = _require_enum(
            PanchaPakshiAdmissionStatus,
            entry["admission_status"],
            f"{context}.admission_status",
        )
        if _require_bool(
            entry["default_selection_allowed"],
            f"{context}.default_selection_allowed",
        ):
            raise PanchaPakshiDataError(
                f"{context}.default_selection_allowed must remain false; "
                "no universal Pancha Pakshi canon is admitted"
            )
        product_kind = _require_string(
            entry["product_kind"], f"{context}.product_kind"
        )
        expected_capabilities = _PRODUCT_CAPABILITIES.get(product_kind)
        if expected_capabilities is None:
            raise PanchaPakshiDataError(f"{context}.product_kind is unknown")
        raw_capabilities = _require_list(
            entry["capabilities"], f"{context}.capabilities"
        )
        capabilities = tuple(
            _require_enum(
                PanchaPakshiCapability,
                raw_capability,
                f"{context}.capabilities[{capability_index}]",
            )
            for capability_index, raw_capability in enumerate(raw_capabilities)
        )
        if not capabilities or len(capabilities) != len(set(capabilities)):
            raise PanchaPakshiDataError(
                f"{context}.capabilities must be non-empty and unique"
            )
        if capabilities != expected_capabilities:
            raise PanchaPakshiDataError(
                f"{context}.capabilities disagree with product_kind or "
                "canonical capability order"
            )
        admission_decision_id = _require_string(
            entry["admission_decision_id"], f"{context}.admission_decision_id"
        )
        if (
            admission_status in _PUBLIC_ADMISSION_STATUSES
            and not admission_decision_id.startswith("pancha_pakshi_")
        ):
            raise PanchaPakshiDataError(
                f"{context}.admission_decision_id is not a Pancha Pakshi decision"
            )
        if (
            profile_id in profile_ids
            or str(relative) in paths
            or admission_decision_id in admission_decision_ids
        ):
            raise PanchaPakshiDataError(
                "manifest contains a duplicate profile, path, or admission "
                "decision identity"
            )
        profile_ids.add(profile_id)
        paths.add(str(relative))
        admission_decision_ids.add(admission_decision_id)
        entries.append(entry)
    return tuple(entries)


@lru_cache(maxsize=None)
def _load_profile_cached(
    profile_id: str, manifest_path_text: str
) -> PanchaPakshiAnyProfile:
    manifest_path = Path(manifest_path_text)
    entries = _read_manifest(manifest_path)
    matches = [entry for entry in entries if entry["profile_id"] == profile_id]
    if not matches:
        raise ValueError(
            f"unknown Pancha Pakshi profile {profile_id!r}; no default canon is selected"
        )
    entry = matches[0]
    data_path = (manifest_path.parent / entry["path"]).resolve()
    if data_path.parent != manifest_path.parent.resolve():
        raise PanchaPakshiDataError("profile path escapes the flat data directory")
    actual_hash = hashlib.sha256(_canonical_bytes(data_path)).hexdigest()
    if actual_hash != entry["sha256"]:
        raise PanchaPakshiDataError(
            f"hash mismatch for Pancha Pakshi profile {profile_id!r}"
        )
    document = _require_dict(_read_json(data_path), f"profile {profile_id!r}")
    parsers = {
        "aksara_prasna_operating_schedule": _parse_profile_document,
        "natal_moon_bird_identity": _parse_natal_identity_profile_document,
        "padu_bird_mapping": _parse_padu_bird_profile_document,
        "sookshma_temporal_selector": (
            _parse_sookshma_selector_profile_document
        ),
    }
    try:
        parser = parsers[entry["product_kind"]]
    except KeyError as exc:
        raise PanchaPakshiDataError(
            f"profile {profile_id!r} has no registered parser"
        ) from exc
    profile = parser(
        document,
        admission_status=PanchaPakshiAdmissionStatus(entry["admission_status"]),
        default_selection_allowed=entry["default_selection_allowed"],
        capabilities=tuple(
            PanchaPakshiCapability(value) for value in entry["capabilities"]
        ),
        admission_decision_id=entry["admission_decision_id"],
    )
    if (
        profile.profile_id != entry["profile_id"]
        or profile.product_kind != entry["product_kind"]
    ):
        raise PanchaPakshiDataError(
            f"manifest metadata disagrees with profile {profile_id!r}"
        )
    if isinstance(profile, PanchaPakshiProfile):
        _validate_generated_completeness(profile)
    elif isinstance(profile, PanchaPakshiNatalIdentityProfile):
        _validate_natal_mapping_completeness(profile)
    elif isinstance(profile, PanchaPakshiPaduBirdProfile):
        _validate_padu_mapping_completeness(profile)
    elif not isinstance(profile, PanchaPakshiSookshmaSelectorProfile):
        raise PanchaPakshiDataError(
            f"unknown parsed Pancha Pakshi profile type for {profile_id!r}"
        )
    return profile


def _parse_profile_document(
    document: dict[str, Any],
    *,
    admission_status: PanchaPakshiAdmissionStatus,
    default_selection_allowed: bool,
    capabilities: tuple[PanchaPakshiCapability, ...],
    admission_decision_id: str,
) -> PanchaPakshiProfile:
    if not isinstance(admission_status, PanchaPakshiAdmissionStatus):
        raise PanchaPakshiDataError("admission_status must be a known enum value")
    _require_bool(default_selection_allowed, "default_selection_allowed")
    if default_selection_allowed:
        raise PanchaPakshiDataError(
            "default_selection_allowed must remain false; no universal canon exists"
        )
    if (
        not isinstance(capabilities, tuple)
        or not capabilities
        or any(
            not isinstance(capability, PanchaPakshiCapability)
            for capability in capabilities
        )
        or len(capabilities) != len(set(capabilities))
    ):
        raise PanchaPakshiDataError(
            "capabilities must be a non-empty tuple of unique known values"
        )
    _require_string(admission_decision_id, "admission_decision_id")

    _require_exact_keys(
        document,
        {
            "schema_version",
            "profile",
            "source",
            "source_locators",
            "lunar_paksha_mapping",
            "birds",
            "weekdays",
            "activities",
            "initial_vowel_identity",
            "temporal_model",
            "duration_vector_nazhigai",
            "schedule_generators",
            "directed_relationships",
            "explicit_omissions",
            "research_conflict_ledger",
        },
        "profile document",
    )
    if _require_int(document["schema_version"], "profile.schema_version") != 3:
        raise PanchaPakshiDataError("unsupported Pancha Pakshi profile schema")

    meta = _require_dict(document["profile"], "profile.profile")
    _require_exact_keys(
        meta,
        {
            "profile_id",
            "product_kind",
            "derivation_status",
            "assembly_policy",
            "title",
        },
        "profile.profile",
    )
    profile_id = _require_string(meta["profile_id"], "profile.profile_id")
    if meta["product_kind"] != "aksara_prasna_operating_schedule":
        raise PanchaPakshiDataError("profile product_kind is unknown")
    if capabilities != _PRODUCT_CAPABILITIES[meta["product_kind"]]:
        raise PanchaPakshiDataError(
            "manifest capabilities disagree with profile product_kind or "
            "canonical capability order"
        )
    if meta["derivation_status"] != (
        "machine_reconciled_source_assignment_with_declared_uncertainty"
    ):
        raise PanchaPakshiDataError("profile derivation_status is unknown")
    if meta["assembly_policy"] != (
        "resolved_grid_axes_assign_birds_explicit_prose_and_verse_govern_"
        "chronology"
    ):
        raise PanchaPakshiDataError("profile assembly_policy is unknown")

    source_obj = _require_dict(document["source"], "profile.source")
    source_keys = {
        "witness_id",
        "title",
        "traditional_attribution",
        "authorship_status",
        "publication_place",
        "publisher",
        "publication_year",
        "language",
        "archive_item_url",
        "archive_original_image_zip_name",
        "archive_original_image_zip_source_status",
        "archive_original_image_zip_md5",
        "archive_original_image_zip_sha1",
        "archive_pdf_name",
        "archive_pdf_source_status",
        "archive_pdf_md5",
        "archive_pdf_sha1",
        "locally_verified_pdf_sha256",
        "catalogued_contributor_note",
        "artifact_distribution_status",
        "redistribution_policy",
        "license_scope",
        "artifact_distribution_note",
    }
    _require_exact_keys(source_obj, source_keys, "profile.source")
    source = PanchaPakshiSource(
        witness_id=_require_string(source_obj["witness_id"], "source.witness_id"),
        title=_require_string(source_obj["title"], "source.title"),
        traditional_attribution=_require_string(
            source_obj["traditional_attribution"], "source.traditional_attribution"
        ),
        authorship_status=_require_string(
            source_obj["authorship_status"], "source.authorship_status"
        ),
        publication_place=_require_string(
            source_obj["publication_place"], "source.publication_place"
        ),
        publisher=_require_string(source_obj["publisher"], "source.publisher"),
        publication_year=_require_int(
            source_obj["publication_year"], "source.publication_year"
        ),
        language=_require_string(source_obj["language"], "source.language"),
        archive_item_url=_require_string(
            source_obj["archive_item_url"], "source.archive_item_url"
        ),
        archive_original_image_zip_name=_require_string(
            source_obj["archive_original_image_zip_name"],
            "source.archive_original_image_zip_name",
        ),
        archive_original_image_zip_source_status=_require_string(
            source_obj["archive_original_image_zip_source_status"],
            "source.archive_original_image_zip_source_status",
        ),
        archive_original_image_zip_md5=_require_string(
            source_obj["archive_original_image_zip_md5"],
            "source.archive_original_image_zip_md5",
        ),
        archive_original_image_zip_sha1=_require_string(
            source_obj["archive_original_image_zip_sha1"],
            "source.archive_original_image_zip_sha1",
        ),
        archive_pdf_name=_require_string(
            source_obj["archive_pdf_name"], "source.archive_pdf_name"
        ),
        archive_pdf_source_status=_require_string(
            source_obj["archive_pdf_source_status"],
            "source.archive_pdf_source_status",
        ),
        archive_pdf_md5=_require_string(
            source_obj["archive_pdf_md5"], "source.archive_pdf_md5"
        ),
        archive_pdf_sha1=_require_string(
            source_obj["archive_pdf_sha1"], "source.archive_pdf_sha1"
        ),
        locally_verified_pdf_sha256=_require_string(
            source_obj["locally_verified_pdf_sha256"],
            "source.locally_verified_pdf_sha256",
        ),
        catalogued_contributor_note=_require_string(
            source_obj["catalogued_contributor_note"],
            "source.catalogued_contributor_note",
        ),
        artifact_distribution_status=_require_string(
            source_obj["artifact_distribution_status"],
            "source.artifact_distribution_status",
        ),
        redistribution_policy=_require_string(
            source_obj["redistribution_policy"],
            "source.redistribution_policy",
        ),
        license_scope=_require_string(
            source_obj["license_scope"], "source.license_scope"
        ),
        artifact_distribution_note=_require_string(
            source_obj["artifact_distribution_note"],
            "source.artifact_distribution_note",
        ),
    )
    if source.authorship_status != "traditional_attribution_not_asserted_authorship":
        raise PanchaPakshiDataError("source authorship_status is unknown")
    if not source.archive_item_url.startswith("https://archive.org/details/"):
        raise PanchaPakshiDataError("source archive_item_url must identify its IA record")
    if Path(source.archive_original_image_zip_name).name != (
        source.archive_original_image_zip_name
    ) or not source.archive_original_image_zip_name.endswith("_images.zip"):
        raise PanchaPakshiDataError(
            "source archive_original_image_zip_name must be one flat image archive"
        )
    if source.archive_original_image_zip_source_status != (
        "internet_archive_original"
    ):
        raise PanchaPakshiDataError(
            "source image ZIP must retain its original-file status"
        )
    if not re.fullmatch(r"[0-9a-f]{32}", source.archive_original_image_zip_md5):
        raise PanchaPakshiDataError("source original image ZIP MD5 is malformed")
    if not re.fullmatch(r"[0-9a-f]{40}", source.archive_original_image_zip_sha1):
        raise PanchaPakshiDataError("source original image ZIP SHA-1 is malformed")
    if Path(source.archive_pdf_name).name != source.archive_pdf_name or not (
        source.archive_pdf_name.endswith(".pdf")
    ):
        raise PanchaPakshiDataError("source archive_pdf_name must be one flat PDF filename")
    if source.archive_pdf_source_status != "internet_archive_derivative":
        raise PanchaPakshiDataError("source PDF must retain its derivative-file status")
    if not re.fullmatch(r"[0-9a-f]{32}", source.archive_pdf_md5):
        raise PanchaPakshiDataError("source archive_pdf_md5 is malformed")
    if not re.fullmatch(r"[0-9a-f]{40}", source.archive_pdf_sha1):
        raise PanchaPakshiDataError("source archive_pdf_sha1 is malformed")
    if not _SHA256_PATTERN.fullmatch(source.locally_verified_pdf_sha256):
        raise PanchaPakshiDataError("source locally verified SHA-256 is malformed")
    if source.artifact_distribution_status != (
        "reference_only_source_artifacts_not_packaged"
    ):
        raise PanchaPakshiDataError(
            "source artifact distribution status is unknown"
        )
    if source.redistribution_policy != (
        "normalized_rules_only_no_scan_ocr_page_images_layout_source_prose_or_"
        "third_party_translation"
    ):
        raise PanchaPakshiDataError("source redistribution policy is unknown")
    if source.license_scope != (
        "mit_covers_moira_authored_code_schema_prose_and_profile_representation"
    ):
        raise PanchaPakshiDataError("source license scope is unknown")

    raw_locators = _require_list(document["source_locators"], "source_locators")
    if not raw_locators:
        raise PanchaPakshiDataError("source_locators must not be empty")
    locators: list[PanchaPakshiSourceLocator] = []
    locator_ids: set[str] = set()
    for index, raw_locator in enumerate(raw_locators):
        context = f"source_locators[{index}]"
        locator = _require_dict(raw_locator, context)
        _require_exact_keys(
            locator,
            {"locator_id", "witness_id", "label", "url", "evidence_role"},
            context,
        )
        parsed = PanchaPakshiSourceLocator(
            locator_id=_require_string(locator["locator_id"], f"{context}.locator_id"),
            witness_id=_require_string(locator["witness_id"], f"{context}.witness_id"),
            label=_require_string(locator["label"], f"{context}.label"),
            url=_require_string(locator["url"], f"{context}.url"),
            evidence_role=_require_string(
                locator["evidence_role"], f"{context}.evidence_role"
            ),
        )
        if parsed.locator_id in locator_ids:
            raise PanchaPakshiDataError("duplicate source locator identity")
        if parsed.witness_id != source.witness_id:
            raise PanchaPakshiDataError("primary locator identifies another witness")
        if not parsed.url.startswith(source.archive_item_url + "/page/"):
            raise PanchaPakshiDataError("primary locator URL leaves the source witness")
        locator_ids.add(parsed.locator_id)
        locators.append(parsed)

    lunar_mapping_obj = _require_dict(
        document["lunar_paksha_mapping"],
        "lunar_paksha_mapping",
    )
    _require_exact_keys(
        lunar_mapping_obj,
        {"mapping_kind", "entries"},
        "lunar_paksha_mapping",
    )
    lunar_paksha_mapping_kind = _require_string(
        lunar_mapping_obj["mapping_kind"],
        "lunar_paksha_mapping.mapping_kind",
    )
    if lunar_paksha_mapping_kind != (
        "source_attested_lunar_phase_half_to_profile_paksha"
    ):
        raise PanchaPakshiDataError("lunar paksha mapping kind is unknown")

    expected_lunar_mappings = (
        (
            "waxing",
            PanchaPakshiAstronomicalPaksha.SHUKLA,
            PanchaPakshiPaksha.PURVA,
            ("ia_n16",),
        ),
        (
            "waning",
            PanchaPakshiAstronomicalPaksha.KRISHNA,
            PanchaPakshiPaksha.AMARA,
            ("ia_n26",),
        ),
    )
    lunar_paksha_mapping_rules: list[_LunarPakshaMappingRule] = []
    raw_lunar_mapping_entries = _require_list(
        lunar_mapping_obj["entries"],
        "lunar_paksha_mapping.entries",
    )
    if len(raw_lunar_mapping_entries) != len(expected_lunar_mappings):
        raise PanchaPakshiDataError(
            "lunar paksha mapping must contain waxing and waning exactly once"
        )
    for index, (raw_rule, expected) in enumerate(
        zip(raw_lunar_mapping_entries, expected_lunar_mappings, strict=True)
    ):
        context = f"lunar_paksha_mapping.entries[{index}]"
        rule = _require_dict(raw_rule, context)
        _require_exact_keys(
            rule,
            {"lunar_phase_half", "profile_paksha", "source_locators"},
            context,
        )
        lunar_phase_half = _require_string(
            rule["lunar_phase_half"],
            f"{context}.lunar_phase_half",
        )
        profile_paksha = _require_enum(
            PanchaPakshiPaksha,
            rule["profile_paksha"],
            f"{context}.profile_paksha",
        )
        source_locator_ids = _parse_locator_ids(
            rule["source_locators"],
            f"{context}.source_locators",
            locator_ids,
        )
        (
            expected_half,
            astronomical_paksha,
            expected_profile_paksha,
            expected_locator_ids,
        ) = expected
        if (
            lunar_phase_half != expected_half
            or profile_paksha is not expected_profile_paksha
            or source_locator_ids != expected_locator_ids
        ):
            raise PanchaPakshiDataError(
                f"{context} disagrees with the source-attested mapping"
            )
        lunar_paksha_mapping_rules.append(
            _LunarPakshaMappingRule(
                lunar_phase_half=lunar_phase_half,
                astronomical_paksha=astronomical_paksha,
                profile_paksha=profile_paksha,
                source_locator_ids=source_locator_ids,
            )
        )

    birds = tuple(
        _require_enum(PanchaPakshiBird, value, f"birds[{index}]")
        for index, value in enumerate(_require_list(document["birds"], "birds"))
    )
    weekdays = tuple(
        _require_enum(PanchaPakshiWeekday, value, f"weekdays[{index}]")
        for index, value in enumerate(_require_list(document["weekdays"], "weekdays"))
    )
    activities = tuple(
        _require_enum(PanchaPakshiActivity, value, f"activities[{index}]")
        for index, value in enumerate(_require_list(document["activities"], "activities"))
    )
    if birds != _BIRDS:
        raise PanchaPakshiDataError("birds must be the complete source order")
    if weekdays != _WEEKDAYS:
        raise PanchaPakshiDataError("weekdays must be complete and Sunday-origin")
    if activities != _ACTIVITIES:
        raise PanchaPakshiDataError("activities must be the complete source order")

    identity_obj = _require_dict(
        document["initial_vowel_identity"], "initial_vowel_identity"
    )
    _require_exact_keys(
        identity_obj,
        {"identity_kind", "not_natal_moon_identity", "entries"},
        "initial_vowel_identity",
    )
    identity_kind = _require_string(
        identity_obj["identity_kind"], "initial_vowel_identity.identity_kind"
    )
    if identity_kind != "aksara_query_or_name_initial_vowel":
        raise PanchaPakshiDataError("initial-vowel identity kind is unknown")
    if identity_obj["not_natal_moon_identity"] is not True:
        raise PanchaPakshiDataError(
            "aksara identity must explicitly deny natal-Moon identity"
        )
    vowel_rules: list[_VowelRule] = []
    seen_symbols: set[str] = set()
    for index, raw_rule in enumerate(
        _require_list(identity_obj["entries"], "initial_vowel_identity.entries")
    ):
        context = f"initial_vowel_identity.entries[{index}]"
        rule = _require_dict(raw_rule, context)
        _require_exact_keys(rule, {"symbols", "bird", "source_locators"}, context)
        symbols = tuple(
            _require_string(symbol, f"{context}.symbols[{symbol_index}]")
            for symbol_index, symbol in enumerate(
                _require_list(rule["symbols"], f"{context}.symbols")
            )
        )
        if not symbols or any(len(symbol) != 1 for symbol in symbols):
            raise PanchaPakshiDataError(f"{context}.symbols must be single characters")
        if seen_symbols.intersection(symbols):
            raise PanchaPakshiDataError("initial-vowel symbols overlap")
        seen_symbols.update(symbols)
        vowel_rules.append(
            _VowelRule(
                symbols=symbols,
                bird=_require_enum(PanchaPakshiBird, rule["bird"], f"{context}.bird"),
                source_locator_ids=_parse_locator_ids(
                    rule["source_locators"], f"{context}.source_locators", locator_ids
                ),
            )
        )
    if tuple(rule.bird for rule in vowel_rules) != birds:
        raise PanchaPakshiDataError(
            "initial-vowel map must identify every bird once in source order"
        )

    temporal_obj = _require_dict(document["temporal_model"], "temporal_model")
    _require_exact_keys(
        temporal_obj,
        {
            "model_kind",
            "day_span_nazhigai",
            "night_span_nazhigai",
            "samam_count_per_half",
            "samam_span_nazhigai",
            "source_locators",
        },
        "temporal_model",
    )
    temporal_model = _TemporalModel(
        model_kind=_require_string(temporal_obj["model_kind"], "temporal_model.model_kind"),
        day_span_nazhigai=_parse_fraction(
            temporal_obj["day_span_nazhigai"], "temporal_model.day_span_nazhigai"
        ),
        night_span_nazhigai=_parse_fraction(
            temporal_obj["night_span_nazhigai"], "temporal_model.night_span_nazhigai"
        ),
        samam_count_per_half=_require_int(
            temporal_obj["samam_count_per_half"],
            "temporal_model.samam_count_per_half",
        ),
        samam_span_nazhigai=_parse_fraction(
            temporal_obj["samam_span_nazhigai"],
            "temporal_model.samam_span_nazhigai",
        ),
        source_locator_ids=_parse_locator_ids(
            temporal_obj["source_locators"],
            "temporal_model.source_locators",
            locator_ids,
        ),
    )
    if temporal_model.model_kind != "fixed_nominal_nazhigai_halves":
        raise PanchaPakshiDataError("temporal model kind is unknown")
    if (
        temporal_model.day_span_nazhigai != 30
        or temporal_model.night_span_nazhigai != 30
        or temporal_model.samam_count_per_half != 5
        or temporal_model.samam_span_nazhigai != 6
    ):
        raise PanchaPakshiDataError(
            "1879 profile requires two 30-nazhigai halves and five six-nazhigai samams"
        )

    duration_rules: list[_DurationRule] = []
    for index, raw_rule in enumerate(
        _require_list(document["duration_vector_nazhigai"], "duration_vector_nazhigai")
    ):
        context = f"duration_vector_nazhigai[{index}]"
        rule = _require_dict(raw_rule, context)
        _require_exact_keys(rule, {"activity", "duration", "source_locators"}, context)
        duration = _parse_fraction(rule["duration"], f"{context}.duration")
        if duration <= 0:
            raise PanchaPakshiDataError(f"{context}.duration must be positive")
        duration_rules.append(
            _DurationRule(
                activity=_require_enum(
                    PanchaPakshiActivity, rule["activity"], f"{context}.activity"
                ),
                duration_nazhigai=duration,
                source_locator_ids=_parse_locator_ids(
                    rule["source_locators"], f"{context}.source_locators", locator_ids
                ),
            )
        )
    if tuple(rule.activity for rule in duration_rules) != activities:
        raise PanchaPakshiDataError("duration vector must be complete in activity order")
    if sum((rule.duration_nazhigai for rule in duration_rules), Fraction()) != 6:
        raise PanchaPakshiDataError("exact duration vector must sum to six nazhigai")

    generators: list[_ScheduleGenerator] = []
    for index, raw_generator in enumerate(
        _require_list(document["schedule_generators"], "schedule_generators")
    ):
        context = f"schedule_generators[{index}]"
        generator_obj = _require_dict(raw_generator, context)
        _require_exact_keys(
            generator_obj,
            {
                "generator_id",
                "paksha",
                "half",
                "first_eat_by_weekday",
                "eat_step_per_samam",
                "activity_offsets",
                "chronological_activities",
                "source_locators",
            },
            context,
        )
        paksha = _require_enum(
            PanchaPakshiPaksha, generator_obj["paksha"], f"{context}.paksha"
        )
        half = _require_enum(
            PanchaPakshiHalf, generator_obj["half"], f"{context}.half"
        )
        generator_id = _require_string(
            generator_obj["generator_id"], f"{context}.generator_id"
        )
        if _CONTEXTS.get((paksha, half)) != generator_id:
            raise PanchaPakshiDataError(f"{context}.generator_id disagrees with context")
        raw_first_eat = _require_list(
            generator_obj["first_eat_by_weekday"],
            f"{context}.first_eat_by_weekday",
        )
        first_eat: list[PanchaPakshiBird] = []
        first_weekdays: list[PanchaPakshiWeekday] = []
        for weekday_index, raw_entry in enumerate(raw_first_eat):
            entry_context = f"{context}.first_eat_by_weekday[{weekday_index}]"
            first_entry = _require_dict(raw_entry, entry_context)
            _require_exact_keys(first_entry, {"weekday", "bird"}, entry_context)
            first_weekdays.append(
                _require_enum(
                    PanchaPakshiWeekday,
                    first_entry["weekday"],
                    f"{entry_context}.weekday",
                )
            )
            first_eat.append(
                _require_enum(
                    PanchaPakshiBird, first_entry["bird"], f"{entry_context}.bird"
                )
            )
        if tuple(first_weekdays) != weekdays:
            raise PanchaPakshiDataError(
                f"{context}.first_eat_by_weekday must cover Sunday-Saturday once"
            )
        step = _require_int(
            generator_obj["eat_step_per_samam"], f"{context}.eat_step_per_samam"
        )
        if math.gcd(abs(step), len(birds)) != 1:
            raise PanchaPakshiDataError(
                f"{context}.eat_step_per_samam cannot traverse every bird"
            )
        offsets_obj = _require_dict(
            generator_obj["activity_offsets"], f"{context}.activity_offsets"
        )
        if set(offsets_obj) != {activity.value for activity in activities}:
            raise PanchaPakshiDataError(
                f"{context}.activity_offsets must cover every known activity"
            )
        offsets = tuple(
            (
                activity,
                _require_int(
                    offsets_obj[activity.value],
                    f"{context}.activity_offsets.{activity.value}",
                ),
            )
            for activity in activities
        )
        if {offset % len(birds) for _, offset in offsets} != set(range(len(birds))):
            raise PanchaPakshiDataError(
                f"{context}.activity_offsets must assign each bird exactly once"
            )
        chronology = tuple(
            _require_enum(
                PanchaPakshiActivity,
                activity,
                f"{context}.chronological_activities[{activity_index}]",
            )
            for activity_index, activity in enumerate(
                _require_list(
                    generator_obj["chronological_activities"],
                    f"{context}.chronological_activities",
                )
            )
        )
        if len(chronology) != len(activities) or set(chronology) != set(activities):
            raise PanchaPakshiDataError(
                f"{context}.chronological_activities must be a complete permutation"
            )
        generators.append(
            _ScheduleGenerator(
                generator_id=generator_id,
                paksha=paksha,
                half=half,
                first_eat_by_weekday=tuple(first_eat),
                eat_step_per_samam=step,
                activity_offsets=offsets,
                chronological_activities=chronology,
                source_locator_ids=_parse_locator_ids(
                    generator_obj["source_locators"],
                    f"{context}.source_locators",
                    locator_ids,
                ),
            )
        )
    actual_contexts = {(generator.paksha, generator.half) for generator in generators}
    if actual_contexts != set(_CONTEXTS) or len(generators) != len(_CONTEXTS):
        raise PanchaPakshiDataError("all four schedule contexts are required exactly once")

    relationship_obj = _require_dict(
        document["directed_relationships"], "directed_relationships"
    )
    _require_exact_keys(
        relationship_obj,
        {"model_kind", "self_relation_policy", "cells"},
        "directed_relationships",
    )
    relationship_model_kind = _require_string(
        relationship_obj["model_kind"], "directed_relationships.model_kind"
    )
    if relationship_model_kind != "source_scoped_directed_1879_machine_reviewed":
        raise PanchaPakshiDataError("directed relationship model kind is unknown")
    relationship_self_policy = _require_string(
        relationship_obj["self_relation_policy"],
        "directed_relationships.self_relation_policy",
    )
    if relationship_self_policy != "undefined":
        raise PanchaPakshiDataError("directed self-relation policy must be undefined")
    relationship_rules: list[_RelationshipRule] = []
    seen_relationships: set[tuple[PanchaPakshiBird, PanchaPakshiBird]] = set()
    for index, raw_relation in enumerate(
        _require_list(relationship_obj["cells"], "directed_relationships.cells")
    ):
        context = f"directed_relationships.cells[{index}]"
        relation_obj = _require_dict(raw_relation, context)
        _require_exact_keys(
            relation_obj,
            {"subject", "target", "relation", "source_locators"},
            context,
        )
        subject = _require_enum(
            PanchaPakshiBird, relation_obj["subject"], f"{context}.subject"
        )
        target = _require_enum(
            PanchaPakshiBird, relation_obj["target"], f"{context}.target"
        )
        if subject is target:
            raise PanchaPakshiDataError(
                f"{context} illegally materializes an undefined self-relation"
            )
        pair = (subject, target)
        if pair in seen_relationships:
            raise PanchaPakshiDataError(f"{context} duplicates a directed pair")
        seen_relationships.add(pair)
        relationship_rules.append(
            _RelationshipRule(
                subject=subject,
                target=target,
                relation=_require_enum(
                    PanchaPakshiRelation,
                    relation_obj["relation"],
                    f"{context}.relation",
                ),
                source_locator_ids=_parse_locator_ids(
                    relation_obj["source_locators"],
                    f"{context}.source_locators",
                    locator_ids,
                ),
            )
        )
    expected_relationships = {
        (subject, target)
        for subject in birds
        for target in birds
        if subject is not target
    }
    if seen_relationships != expected_relationships or len(relationship_rules) != 20:
        raise PanchaPakshiDataError(
            "directed relationship matrix must contain all 20 ordered non-self cells"
        )

    omissions: list[PanchaPakshiOmission] = []
    for index, raw_omission in enumerate(
        _require_list(document["explicit_omissions"], "explicit_omissions")
    ):
        context = f"explicit_omissions[{index}]"
        omission = _require_dict(raw_omission, context)
        _require_exact_keys(omission, {"feature", "status", "reason"}, context)
        parsed = PanchaPakshiOmission(
            feature=_require_string(omission["feature"], f"{context}.feature"),
            status=_require_string(omission["status"], f"{context}.status"),
            reason=_require_string(omission["reason"], f"{context}.reason"),
        )
        if parsed.status != "omitted":
            raise PanchaPakshiDataError(f"{context}.status must be omitted")
        omissions.append(parsed)
    if {omission.feature for omission in omissions} != _REQUIRED_OMISSIONS:
        raise PanchaPakshiDataError(
            "profile must explicitly omit authority birds, natal mapping, "
            "scoring, cross-witness relationship normalization, vinadi, and "
            "seasonal scaling"
        )
    if len(omissions) != len(_REQUIRED_OMISSIONS):
        raise PanchaPakshiDataError("explicit omissions contain duplicates")

    conflicts: list[PanchaPakshiConflictWitness] = []
    for index, raw_conflict in enumerate(
        _require_list(document["research_conflict_ledger"], "research_conflict_ledger")
    ):
        context = f"research_conflict_ledger[{index}]"
        conflict = _require_dict(raw_conflict, context)
        _require_exact_keys(
            conflict,
            {
                "witness_id",
                "bibliographic_label",
                "record_url",
                "record_identity",
                "conflict_locators",
                "evidence_status",
                "runtime_status",
            },
            context,
        )
        conflict_locators = tuple(
            _require_string(locator, f"{context}.conflict_locators[{locator_index}]")
            for locator_index, locator in enumerate(
                _require_list(conflict["conflict_locators"], f"{context}.conflict_locators")
            )
        )
        parsed = PanchaPakshiConflictWitness(
            witness_id=_require_string(conflict["witness_id"], f"{context}.witness_id"),
            bibliographic_label=_require_string(
                conflict["bibliographic_label"], f"{context}.bibliographic_label"
            ),
            record_url=_require_string(conflict["record_url"], f"{context}.record_url"),
            record_identity=_require_string(
                conflict["record_identity"], f"{context}.record_identity"
            ),
            conflict_locators=conflict_locators,
            evidence_status=_require_string(
                conflict["evidence_status"], f"{context}.evidence_status"
            ),
            runtime_status=_require_string(
                conflict["runtime_status"], f"{context}.runtime_status"
            ),
        )
        if parsed.runtime_status != "not_imported":
            raise PanchaPakshiDataError("conflict witness must remain non-runtime")
        if parsed.evidence_status not in {
            "metadata_and_locator_only_not_transcribed",
            "bibliographic_metadata_only_untranscribed",
        }:
            raise PanchaPakshiDataError("conflict witness evidence status is unknown")
        if not parsed.record_url.startswith("https://"):
            raise PanchaPakshiDataError("conflict witness record URL must be HTTPS")
        conflicts.append(parsed)
    if not conflicts or len({conflict.witness_id for conflict in conflicts}) != len(conflicts):
        raise PanchaPakshiDataError("research conflict ledger is empty or duplicated")

    referenced_locator_ids: set[str] = set(temporal_model.source_locator_ids)
    for rule in vowel_rules:
        referenced_locator_ids.update(rule.source_locator_ids)
    for rule in duration_rules:
        referenced_locator_ids.update(rule.source_locator_ids)
    for generator in generators:
        referenced_locator_ids.update(generator.source_locator_ids)
    for rule in relationship_rules:
        referenced_locator_ids.update(rule.source_locator_ids)
    for rule in lunar_paksha_mapping_rules:
        referenced_locator_ids.update(rule.source_locator_ids)
    if referenced_locator_ids != locator_ids:
        raise PanchaPakshiDataError(
            "primary source locator ledger contains unreferenced or missing evidence"
        )

    return PanchaPakshiProfile(
        profile_id=profile_id,
        admission_status=admission_status,
        product_kind=meta["product_kind"],
        default_selection_allowed=default_selection_allowed,
        capabilities=capabilities,
        admission_decision_id=admission_decision_id,
        derivation_status=meta["derivation_status"],
        assembly_policy=meta["assembly_policy"],
        title=_require_string(meta["title"], "profile.title"),
        source=source,
        source_locators=tuple(locators),
        birds=birds,
        weekdays=weekdays,
        activities=activities,
        initial_vowel_identity_kind=identity_kind,
        initial_vowel_is_natal_moon_identity=False,
        vowel_rules=tuple(vowel_rules),
        lunar_paksha_mapping_kind=lunar_paksha_mapping_kind,
        lunar_paksha_mapping_rules=tuple(lunar_paksha_mapping_rules),
        temporal_model=temporal_model,
        duration_rules=tuple(duration_rules),
        generators=tuple(generators),
        relationship_model_kind=relationship_model_kind,
        relationship_self_policy=relationship_self_policy,
        relationship_rules=tuple(relationship_rules),
        explicit_omissions=tuple(omissions),
        research_conflict_ledger=tuple(conflicts),
    )


def _parse_natal_identity_profile_document(
    document: dict[str, Any],
    *,
    admission_status: PanchaPakshiAdmissionStatus,
    default_selection_allowed: bool,
    capabilities: tuple[PanchaPakshiCapability, ...],
    admission_decision_id: str,
) -> PanchaPakshiNatalIdentityProfile:
    """Parse the Bogamuni profile without weakening the schedule schema."""

    from .sidereal import NAKSHATRA_NAMES

    if not isinstance(admission_status, PanchaPakshiAdmissionStatus):
        raise PanchaPakshiDataError("admission_status must be a known enum value")
    _require_bool(default_selection_allowed, "default_selection_allowed")
    if default_selection_allowed:
        raise PanchaPakshiDataError(
            "default_selection_allowed must remain false; no universal canon exists"
        )
    if (
        not isinstance(capabilities, tuple)
        or capabilities != _PRODUCT_CAPABILITIES["natal_moon_bird_identity"]
    ):
        raise PanchaPakshiDataError(
            "manifest capabilities disagree with natal product kind or "
            "canonical capability order"
        )
    _require_string(admission_decision_id, "admission_decision_id")

    _require_exact_keys(
        document,
        {
            "schema_version",
            "profile",
            "source",
            "source_locators",
            "lunar_paksha_mapping",
            "nakshatra_bird_mapping",
            "modern_composition",
            "explicit_omissions",
            "research_conflict_ledger",
        },
        "natal profile document",
    )
    if _require_int(document["schema_version"], "profile.schema_version") != 1:
        raise PanchaPakshiDataError(
            "unsupported Pancha Pakshi natal profile schema"
        )

    meta = _require_dict(document["profile"], "profile.profile")
    _require_exact_keys(
        meta,
        {
            "profile_id",
            "product_kind",
            "derivation_status",
            "assembly_policy",
            "title",
        },
        "profile.profile",
    )
    profile_id = _require_string(meta["profile_id"], "profile.profile_id")
    if profile_id != "bogamuni_chennai_2024_nakshatra_natal_identity":
        raise PanchaPakshiDataError("natal profile identity is unknown")
    if meta["product_kind"] != "natal_moon_bird_identity":
        raise PanchaPakshiDataError("natal profile product_kind is unknown")
    if meta["derivation_status"] != (
        "visually_verified_source_partition_with_explicit_modern_natal_moon_"
        "composition"
    ):
        raise PanchaPakshiDataError("natal profile derivation_status is unknown")
    if meta["assembly_policy"] != (
        "verse_precedence_for_nakshatra_partition"
    ):
        raise PanchaPakshiDataError("natal profile assembly_policy is unknown")
    if meta["title"] != (
        "Bogamuni 2024 nakshatra-bird table with explicit modern Lahiri "
        "natal-Moon composition"
    ):
        raise PanchaPakshiDataError("natal profile title is unknown")

    source_obj = _require_dict(document["source"], "profile.source")
    source_keys = {
        "witness_id",
        "title",
        "traditional_attribution",
        "authorship_status",
        "publication_place",
        "publisher",
        "publication_year",
        "language",
        "archive_item_url",
        "archive_original_image_zip_name",
        "archive_original_image_zip_source_status",
        "archive_original_image_zip_md5",
        "archive_original_image_zip_sha1",
        "archive_pdf_name",
        "archive_pdf_source_status",
        "archive_pdf_md5",
        "archive_pdf_sha1",
        "locally_verified_pdf_sha256",
        "catalogued_contributor_note",
        "artifact_distribution_status",
        "redistribution_policy",
        "license_scope",
        "artifact_distribution_note",
    }
    _require_exact_keys(source_obj, source_keys, "profile.source")
    source = PanchaPakshiSource(
        witness_id=_require_string(source_obj["witness_id"], "source.witness_id"),
        title=_require_string(source_obj["title"], "source.title"),
        traditional_attribution=_require_string(
            source_obj["traditional_attribution"],
            "source.traditional_attribution",
        ),
        authorship_status=_require_string(
            source_obj["authorship_status"],
            "source.authorship_status",
        ),
        publication_place=_require_string(
            source_obj["publication_place"],
            "source.publication_place",
        ),
        publisher=_require_string(source_obj["publisher"], "source.publisher"),
        publication_year=_require_int(
            source_obj["publication_year"],
            "source.publication_year",
        ),
        language=_require_string(source_obj["language"], "source.language"),
        archive_item_url=_require_string(
            source_obj["archive_item_url"],
            "source.archive_item_url",
        ),
        archive_original_image_zip_name=_require_string(
            source_obj["archive_original_image_zip_name"],
            "source.archive_original_image_zip_name",
        ),
        archive_original_image_zip_source_status=_require_string(
            source_obj["archive_original_image_zip_source_status"],
            "source.archive_original_image_zip_source_status",
        ),
        archive_original_image_zip_md5=_require_string(
            source_obj["archive_original_image_zip_md5"],
            "source.archive_original_image_zip_md5",
        ),
        archive_original_image_zip_sha1=_require_string(
            source_obj["archive_original_image_zip_sha1"],
            "source.archive_original_image_zip_sha1",
        ),
        archive_pdf_name=_require_string(
            source_obj["archive_pdf_name"],
            "source.archive_pdf_name",
        ),
        archive_pdf_source_status=_require_string(
            source_obj["archive_pdf_source_status"],
            "source.archive_pdf_source_status",
        ),
        archive_pdf_md5=_require_string(
            source_obj["archive_pdf_md5"],
            "source.archive_pdf_md5",
        ),
        archive_pdf_sha1=_require_string(
            source_obj["archive_pdf_sha1"],
            "source.archive_pdf_sha1",
        ),
        locally_verified_pdf_sha256=_require_string(
            source_obj["locally_verified_pdf_sha256"],
            "source.locally_verified_pdf_sha256",
        ),
        catalogued_contributor_note=_require_string(
            source_obj["catalogued_contributor_note"],
            "source.catalogued_contributor_note",
        ),
        artifact_distribution_status=_require_string(
            source_obj["artifact_distribution_status"],
            "source.artifact_distribution_status",
        ),
        redistribution_policy=_require_string(
            source_obj["redistribution_policy"],
            "source.redistribution_policy",
        ),
        license_scope=_require_string(
            source_obj["license_scope"],
            "source.license_scope",
        ),
        artifact_distribution_note=_require_string(
            source_obj["artifact_distribution_note"],
            "source.artifact_distribution_note",
        ),
    )
    if source.witness_id != "acc.-no.-44757-panjapatchi-sashthiram-2024":
        raise PanchaPakshiDataError("natal profile witness identity is unknown")
    if source.authorship_status != "traditional_attribution_not_asserted_authorship":
        raise PanchaPakshiDataError("source authorship_status is unknown")
    if source.traditional_attribution != "Bogamuni":
        raise PanchaPakshiDataError("source traditional attribution is unknown")
    if source.title != "போகமுனிவர் பஞ்சபட்சி சாஸ்திரம் உரையுடன்":
        raise PanchaPakshiDataError("source title is unknown")
    if source.publication_place != "Vadapalani, Chennai":
        raise PanchaPakshiDataError("source publication_place is unknown")
    if source.publisher != "Thamarai Noolagam":
        raise PanchaPakshiDataError("source publisher is unknown")
    if source.publication_year != 2024:
        raise PanchaPakshiDataError("source publication_year is unknown")
    if source.language != "Tamil":
        raise PanchaPakshiDataError("source language is unknown")
    if "R. C. Mohan" not in source.catalogued_contributor_note:
        raise PanchaPakshiDataError("source editor attribution is unknown")
    if source.archive_item_url != (
        "https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024"
    ):
        raise PanchaPakshiDataError("source archive_item_url is unknown")
    if (
        source.archive_original_image_zip_name
        != "not_applicable_no_original_image_zip_bound"
        or source.archive_original_image_zip_source_status
        != "not_applicable_pdf_is_internet_archive_original"
        or source.archive_original_image_zip_md5 != "not_applicable"
        or source.archive_original_image_zip_sha1 != "not_applicable"
    ):
        raise PanchaPakshiDataError(
            "natal profile must not mislabel an IA derivative image ZIP as original"
        )
    if source.archive_pdf_name != "Acc.No.44757-PanjapatchiSashthiram-2024.pdf":
        raise PanchaPakshiDataError("source archive PDF identity is unknown")
    if source.archive_pdf_source_status != "internet_archive_original":
        raise PanchaPakshiDataError("source PDF must retain its original-file status")
    if source.archive_pdf_md5 != "abe489a832ac38a0270335b7429776f3":
        raise PanchaPakshiDataError("source archive PDF MD5 disagrees with IA metadata")
    if source.archive_pdf_sha1 != "6ddad8f2577883f6859829f534e8ee7b8330ade8":
        raise PanchaPakshiDataError("source archive PDF SHA-1 disagrees with IA metadata")
    if source.locally_verified_pdf_sha256 != (
        "035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990"
    ):
        raise PanchaPakshiDataError("source locally verified PDF SHA-256 is unknown")
    if source.artifact_distribution_status != (
        "reference_only_source_artifacts_not_packaged"
    ):
        raise PanchaPakshiDataError("source artifact distribution status is unknown")
    if source.redistribution_policy != (
        "normalized_rules_only_no_scan_ocr_page_images_layout_source_prose_or_"
        "third_party_translation"
    ):
        raise PanchaPakshiDataError("source redistribution policy is unknown")
    if source.license_scope != (
        "mit_covers_moira_authored_code_schema_prose_and_profile_representation"
    ):
        raise PanchaPakshiDataError("source license scope is unknown")

    expected_locator_specs = (
        (
            "bogar_n52_purva",
            "n52",
            "source_attested_purva_nakshatra_bird_partition",
        ),
        (
            "bogar_n64_amara_verse",
            "n64",
            "governing_amara_verse_nakshatra_bird_partition",
        ),
        (
            "bogar_n64_amara_commentary_conflict",
            "n64",
            "rejected_adjacent_commentary_partition_conflict",
        ),
        (
            "bogar_n167_phase",
            "n167",
            "source_attested_new_moon_purva_full_moon_amara_mapping",
        ),
    )
    raw_locators = _require_list(document["source_locators"], "source_locators")
    if len(raw_locators) != len(expected_locator_specs):
        raise PanchaPakshiDataError("natal profile source locator ledger is incomplete")
    locators: list[PanchaPakshiSourceLocator] = []
    locator_ids: set[str] = set()
    for index, (raw_locator, expected) in enumerate(
        zip(raw_locators, expected_locator_specs, strict=True)
    ):
        context = f"source_locators[{index}]"
        locator = _require_dict(raw_locator, context)
        _require_exact_keys(
            locator,
            {"locator_id", "witness_id", "label", "url", "evidence_role"},
            context,
        )
        parsed = PanchaPakshiSourceLocator(
            locator_id=_require_string(locator["locator_id"], f"{context}.locator_id"),
            witness_id=_require_string(locator["witness_id"], f"{context}.witness_id"),
            label=_require_string(locator["label"], f"{context}.label"),
            url=_require_string(locator["url"], f"{context}.url"),
            evidence_role=_require_string(
                locator["evidence_role"],
                f"{context}.evidence_role",
            ),
        )
        expected_id, expected_leaf, expected_role = expected
        if (
            parsed.locator_id != expected_id
            or parsed.witness_id != source.witness_id
            or parsed.url
            != f"{source.archive_item_url}/page/{expected_leaf}/mode/1up"
            or parsed.evidence_role != expected_role
        ):
            raise PanchaPakshiDataError(f"{context} disagrees with source evidence")
        if parsed.locator_id in locator_ids:
            raise PanchaPakshiDataError("duplicate source locator identity")
        locator_ids.add(parsed.locator_id)
        locators.append(parsed)

    lunar_mapping_obj = _require_dict(
        document["lunar_paksha_mapping"],
        "lunar_paksha_mapping",
    )
    _require_exact_keys(
        lunar_mapping_obj,
        {"mapping_kind", "entries"},
        "lunar_paksha_mapping",
    )
    lunar_paksha_mapping_kind = _require_string(
        lunar_mapping_obj["mapping_kind"],
        "lunar_paksha_mapping.mapping_kind",
    )
    if lunar_paksha_mapping_kind != (
        "source_attested_lunar_phase_half_to_profile_paksha"
    ):
        raise PanchaPakshiDataError("lunar paksha mapping kind is unknown")
    expected_lunar_mappings = (
        (
            "waxing",
            PanchaPakshiAstronomicalPaksha.SHUKLA,
            PanchaPakshiPaksha.PURVA,
        ),
        (
            "waning",
            PanchaPakshiAstronomicalPaksha.KRISHNA,
            PanchaPakshiPaksha.AMARA,
        ),
    )
    raw_lunar_entries = _require_list(
        lunar_mapping_obj["entries"],
        "lunar_paksha_mapping.entries",
    )
    if len(raw_lunar_entries) != 2:
        raise PanchaPakshiDataError(
            "lunar paksha mapping must contain waxing and waning exactly once"
        )
    lunar_paksha_mapping_rules: list[_LunarPakshaMappingRule] = []
    for index, (raw_entry, expected) in enumerate(
        zip(raw_lunar_entries, expected_lunar_mappings, strict=True)
    ):
        context = f"lunar_paksha_mapping.entries[{index}]"
        entry = _require_dict(raw_entry, context)
        _require_exact_keys(
            entry,
            {"lunar_phase_half", "profile_paksha", "source_locators"},
            context,
        )
        lunar_phase_half = _require_string(
            entry["lunar_phase_half"],
            f"{context}.lunar_phase_half",
        )
        profile_paksha = _require_enum(
            PanchaPakshiPaksha,
            entry["profile_paksha"],
            f"{context}.profile_paksha",
        )
        source_locator_ids = _parse_locator_ids(
            entry["source_locators"],
            f"{context}.source_locators",
            locator_ids,
        )
        expected_half, astronomical_paksha, expected_profile_paksha = expected
        if (
            lunar_phase_half != expected_half
            or profile_paksha is not expected_profile_paksha
            or source_locator_ids != ("bogar_n167_phase",)
        ):
            raise PanchaPakshiDataError(
                f"{context} disagrees with the source-attested phase mapping"
            )
        lunar_paksha_mapping_rules.append(
            _LunarPakshaMappingRule(
                lunar_phase_half=lunar_phase_half,
                astronomical_paksha=astronomical_paksha,
                profile_paksha=profile_paksha,
                source_locator_ids=source_locator_ids,
            )
        )

    mapping_obj = _require_dict(
        document["nakshatra_bird_mapping"],
        "nakshatra_bird_mapping",
    )
    _require_exact_keys(
        mapping_obj,
        {"mapping_kind", "source_table_semantics", "assembly_policy", "entries"},
        "nakshatra_bird_mapping",
    )
    mapping_kind = _require_string(
        mapping_obj["mapping_kind"],
        "nakshatra_bird_mapping.mapping_kind",
    )
    if mapping_kind != "profile_paksha_and_nakshatra_to_bird":
        raise PanchaPakshiDataError("nakshatra-bird mapping kind is unknown")
    source_table_semantics = _require_string(
        mapping_obj["source_table_semantics"],
        "nakshatra_bird_mapping.source_table_semantics",
    )
    if source_table_semantics != (
        "nakshatra_bird_table_not_explicitly_natal_moon"
    ):
        raise PanchaPakshiDataError("nakshatra-bird source semantics are unknown")
    if mapping_obj["assembly_policy"] != meta["assembly_policy"]:
        raise PanchaPakshiDataError(
            "nakshatra-bird mapping assembly policy disagrees with profile"
        )

    purva_birds = (
        (PanchaPakshiBird.VULTURE,) * 5
        + (PanchaPakshiBird.OWL,) * 6
        + (PanchaPakshiBird.CROW,) * 5
        + (PanchaPakshiBird.COCK,) * 5
        + (PanchaPakshiBird.PEACOCK,) * 6
    )
    amara_birds = (
        (PanchaPakshiBird.PEACOCK,) * 5
        + (PanchaPakshiBird.COCK,) * 6
        + (PanchaPakshiBird.CROW,) * 5
        + (PanchaPakshiBird.OWL,) * 5
        + (PanchaPakshiBird.VULTURE,) * 6
    )
    expected_mapping_entries = tuple(
        (
            paksha,
            nakshatra_index,
            NAKSHATRA_NAMES[nakshatra_index],
            birds[nakshatra_index],
            (locator_id,),
        )
        for paksha, birds, locator_id in (
            (PanchaPakshiPaksha.PURVA, purva_birds, "bogar_n52_purva"),
            (PanchaPakshiPaksha.AMARA, amara_birds, "bogar_n64_amara_verse"),
        )
        for nakshatra_index in range(27)
    )
    raw_mapping_entries = _require_list(
        mapping_obj["entries"],
        "nakshatra_bird_mapping.entries",
    )
    if len(raw_mapping_entries) != len(expected_mapping_entries):
        raise PanchaPakshiDataError(
            "nakshatra-bird table must contain all 54 Paksha/nakshatra cells"
        )
    nakshatra_bird_rules: list[_NakshatraBirdRule] = []
    for index, (raw_entry, expected) in enumerate(
        zip(raw_mapping_entries, expected_mapping_entries, strict=True)
    ):
        context = f"nakshatra_bird_mapping.entries[{index}]"
        entry = _require_dict(raw_entry, context)
        _require_exact_keys(
            entry,
            {
                "profile_paksha",
                "nakshatra_index",
                "nakshatra",
                "bird",
                "source_locators",
            },
            context,
        )
        parsed = _NakshatraBirdRule(
            profile_paksha=_require_enum(
                PanchaPakshiPaksha,
                entry["profile_paksha"],
                f"{context}.profile_paksha",
            ),
            nakshatra_index=_require_int(
                entry["nakshatra_index"],
                f"{context}.nakshatra_index",
            ),
            nakshatra=_require_string(entry["nakshatra"], f"{context}.nakshatra"),
            bird=_require_enum(
                PanchaPakshiBird,
                entry["bird"],
                f"{context}.bird",
            ),
            source_locator_ids=_parse_locator_ids(
                entry["source_locators"],
                f"{context}.source_locators",
                locator_ids,
            ),
        )
        (
            expected_paksha,
            expected_index,
            expected_name,
            expected_bird,
            expected_locator_ids,
        ) = expected
        if (
            parsed.profile_paksha is not expected_paksha
            or parsed.nakshatra_index != expected_index
            or parsed.nakshatra != expected_name
            or parsed.bird is not expected_bird
            or parsed.source_locator_ids != expected_locator_ids
        ):
            raise PanchaPakshiDataError(
                f"{context} disagrees with the visually verified source partition"
            )
        nakshatra_bird_rules.append(parsed)

    composition = _require_dict(
        document["modern_composition"],
        "modern_composition",
    )
    expected_composition = {
        "composition_kind": (
            "modern_moira_natal_moon_over_source_nakshatra_bird_table"
        ),
        "source_table_natal_status": "not_explicitly_natal_moon",
        "lunar_position": "apparent_geocentric_true_ecliptic_of_date",
        "ayanamsa_system": "Lahiri",
        "ayanamsa_mode": "true",
        "ayanamsa_source_status": "not_attested_by_source_modern_policy",
        "nakshatra_partition": "27_equal_half_open_40_over_3_degree_sectors",
        "boundary_ownership": "exact_internal_boundary_to_following_nakshatra",
        "binary_boundary_recovery": "maximum_one_ulp_below_internal_boundary",
    }
    _require_exact_keys(composition, set(expected_composition), "modern_composition")
    if composition != expected_composition:
        raise PanchaPakshiDataError("modern natal composition doctrine is unknown")

    omissions: list[PanchaPakshiOmission] = []
    for index, raw_omission in enumerate(
        _require_list(document["explicit_omissions"], "explicit_omissions")
    ):
        context = f"explicit_omissions[{index}]"
        omission = _require_dict(raw_omission, context)
        _require_exact_keys(omission, {"feature", "status", "reason"}, context)
        parsed = PanchaPakshiOmission(
            feature=_require_string(omission["feature"], f"{context}.feature"),
            status=_require_string(omission["status"], f"{context}.status"),
            reason=_require_string(omission["reason"], f"{context}.reason"),
        )
        if parsed.status != "omitted":
            raise PanchaPakshiDataError(f"{context}.status must be omitted")
        omissions.append(parsed)
    if (
        {omission.feature for omission in omissions} != _REQUIRED_NATAL_OMISSIONS
        or len(omissions) != len(_REQUIRED_NATAL_OMISSIONS)
    ):
        raise PanchaPakshiDataError(
            "natal profile explicit omissions are incomplete or duplicated"
        )

    conflicts: list[PanchaPakshiConflictWitness] = []
    for index, raw_conflict in enumerate(
        _require_list(
            document["research_conflict_ledger"],
            "research_conflict_ledger",
        )
    ):
        context = f"research_conflict_ledger[{index}]"
        conflict = _require_dict(raw_conflict, context)
        _require_exact_keys(
            conflict,
            {
                "witness_id",
                "bibliographic_label",
                "record_url",
                "record_identity",
                "conflict_locators",
                "evidence_status",
                "runtime_status",
            },
            context,
        )
        conflict_locators = tuple(
            _require_string(locator, f"{context}.conflict_locators[{locator_index}]")
            for locator_index, locator in enumerate(
                _require_list(
                    conflict["conflict_locators"],
                    f"{context}.conflict_locators",
                )
            )
        )
        if not conflict_locators:
            raise PanchaPakshiDataError(f"{context}.conflict_locators is empty")
        parsed = PanchaPakshiConflictWitness(
            witness_id=_require_string(
                conflict["witness_id"],
                f"{context}.witness_id",
            ),
            bibliographic_label=_require_string(
                conflict["bibliographic_label"],
                f"{context}.bibliographic_label",
            ),
            record_url=_require_string(
                conflict["record_url"],
                f"{context}.record_url",
            ),
            record_identity=_require_string(
                conflict["record_identity"],
                f"{context}.record_identity",
            ),
            conflict_locators=conflict_locators,
            evidence_status=_require_string(
                conflict["evidence_status"],
                f"{context}.evidence_status",
            ),
            runtime_status=_require_string(
                conflict["runtime_status"],
                f"{context}.runtime_status",
            ),
        )
        if not parsed.record_url.startswith("https://"):
            raise PanchaPakshiDataError("conflict witness record URL must be HTTPS")
        if parsed.runtime_status not in {
            "rejected_by_declared_verse_precedence",
            "not_imported",
        }:
            raise PanchaPakshiDataError("conflict witness runtime status is unknown")
        conflicts.append(parsed)
    expected_conflict_contracts = (
        (
            "bogamuni_2024_adjacent_amara_commentary",
            source.archive_item_url,
            ("bogar_n64_amara_commentary_conflict",),
            "visually_verified_commentary_overlaps_shravana_and_omits_revati",
            "rejected_by_declared_verse_precedence",
        ),
        (
            "kvc-0354-vinaadi-pajasapatchi-mulamum-1934",
            "https://archive.org/details/kvc-0354-vinaadi-pajasapatchi-mulamum-1934",
            (
                "IA leaf n18: Purva corroboration",
                "IA leaf n61: malformed Amara commentary",
            ),
            (
                "visually_reviewed_secondary_witness_purva_corroboration_and_"
                "amara_commentary_conflict"
            ),
            "not_imported",
        ),
    )
    actual_conflict_contracts = tuple(
        (
            conflict.witness_id,
            conflict.record_url,
            conflict.conflict_locators,
            conflict.evidence_status,
            conflict.runtime_status,
        )
        for conflict in conflicts
    )
    if actual_conflict_contracts != expected_conflict_contracts:
        raise PanchaPakshiDataError(
            "natal research conflict ledger disagrees with the two named "
            "witness contracts"
        )
    if "abe489a832ac38a0270335b7429776f3" not in conflicts[0].record_identity:
        raise PanchaPakshiDataError(
            "Bogamuni conflict witness lacks the original-PDF identity"
        )
    if "5832ca69b64c1429342fba8c3b3012dc" not in conflicts[1].record_identity:
        raise PanchaPakshiDataError(
            "Uromarisi conflict witness lacks the original-PDF identity"
        )

    referenced_locator_ids = {
        locator_id
        for rule in lunar_paksha_mapping_rules
        for locator_id in rule.source_locator_ids
    }
    referenced_locator_ids.update(
        locator_id
        for rule in nakshatra_bird_rules
        for locator_id in rule.source_locator_ids
    )
    referenced_locator_ids.update(
        locator_id
        for conflict in conflicts
        for locator_id in conflict.conflict_locators
        if locator_id in locator_ids
    )
    if referenced_locator_ids != locator_ids:
        raise PanchaPakshiDataError(
            "natal source locator ledger contains unreferenced or missing evidence"
        )

    return PanchaPakshiNatalIdentityProfile(
        profile_id=profile_id,
        admission_status=admission_status,
        product_kind=meta["product_kind"],
        default_selection_allowed=default_selection_allowed,
        capabilities=capabilities,
        admission_decision_id=admission_decision_id,
        derivation_status=meta["derivation_status"],
        assembly_policy=meta["assembly_policy"],
        title=_require_string(meta["title"], "profile.title"),
        source=source,
        source_locators=tuple(locators),
        lunar_paksha_mapping_kind=lunar_paksha_mapping_kind,
        lunar_paksha_mapping_rules=tuple(lunar_paksha_mapping_rules),
        nakshatra_bird_mapping_kind=mapping_kind,
        source_table_semantics=source_table_semantics,
        modern_composition_kind=composition["composition_kind"],
        nakshatra_bird_rules=tuple(nakshatra_bird_rules),
        explicit_omissions=tuple(omissions),
        research_conflict_ledger=tuple(conflicts),
    )


def _parse_padu_bird_profile_document(
    document: dict[str, Any],
    *,
    admission_status: PanchaPakshiAdmissionStatus,
    default_selection_allowed: bool,
    capabilities: tuple[PanchaPakshiCapability, ...],
    admission_decision_id: str,
) -> PanchaPakshiPaduBirdProfile:
    """Parse one pure Bogamuni Paksha-by-weekday Padu-bird table."""

    if not isinstance(admission_status, PanchaPakshiAdmissionStatus):
        raise PanchaPakshiDataError("admission_status must be a known enum value")
    _require_bool(default_selection_allowed, "default_selection_allowed")
    if default_selection_allowed:
        raise PanchaPakshiDataError(
            "default_selection_allowed must remain false; no universal canon exists"
        )
    if capabilities != _PRODUCT_CAPABILITIES["padu_bird_mapping"]:
        raise PanchaPakshiDataError(
            "manifest capabilities disagree with Padu product kind or "
            "canonical capability order"
        )
    _require_string(admission_decision_id, "admission_decision_id")

    _require_exact_keys(
        document,
        {
            "schema_version",
            "profile",
            "source",
            "source_locators",
            "padu_bird_mapping",
            "explicit_omissions",
            "research_conflict_ledger",
        },
        "Padu profile document",
    )
    if _require_int(document["schema_version"], "profile.schema_version") != 1:
        raise PanchaPakshiDataError("unsupported Pancha Pakshi Padu profile schema")

    meta = _require_dict(document["profile"], "profile.profile")
    _require_exact_keys(
        meta,
        {
            "profile_id",
            "product_kind",
            "derivation_status",
            "assembly_policy",
            "title",
        },
        "profile.profile",
    )
    expected_meta = {
        "profile_id": "bogamuni_chennai_2024_padu_bird_mapping",
        "product_kind": "padu_bird_mapping",
        "derivation_status": "visually_verified_source_weekday_padu_bird_table",
        "assembly_policy": (
            "paksha_stanzas_govern_repeated_combined_table_confirms"
        ),
        "title": "Bogamuni 2024 Paksha-and-weekday Padu-bird mapping",
    }
    if meta != expected_meta:
        raise PanchaPakshiDataError("Padu profile identity or doctrine is unknown")

    source_obj = _require_dict(document["source"], "profile.source")
    expected_source = {
        "witness_id": "acc.-no.-44757-panjapatchi-sashthiram-2024",
        "title": "போகமுனிவர் பஞ்சபட்சி சாஸ்திரம் உரையுடன்",
        "traditional_attribution": "Bogamuni",
        "authorship_status": "traditional_attribution_not_asserted_authorship",
        "publication_place": "Vadapalani, Chennai",
        "publisher": "Thamarai Noolagam",
        "publication_year": 2024,
        "language": "Tamil",
        "archive_item_url": "https://archive.org/details/acc.-no.-44757-panjapatchi-sashthiram-2024",
        "archive_original_image_zip_name": "not_applicable_no_original_image_zip_bound",
        "archive_original_image_zip_source_status": "not_applicable_pdf_is_internet_archive_original",
        "archive_original_image_zip_md5": "not_applicable",
        "archive_original_image_zip_sha1": "not_applicable",
        "archive_pdf_name": "Acc.No.44757-PanjapatchiSashthiram-2024.pdf",
        "archive_pdf_source_status": "internet_archive_original",
        "archive_pdf_md5": "abe489a832ac38a0270335b7429776f3",
        "archive_pdf_sha1": "6ddad8f2577883f6859829f534e8ee7b8330ade8",
        "locally_verified_pdf_sha256": "035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990",
        "catalogued_contributor_note": "The sixth edition names R. C. Mohan as editor; Moira does not convert that editorial credit into authorship of the traditionally attributed work.",
        "artifact_distribution_status": "reference_only_source_artifacts_not_packaged",
        "redistribution_policy": "normalized_rules_only_no_scan_ocr_page_images_layout_source_prose_or_third_party_translation",
        "license_scope": "mit_covers_moira_authored_code_schema_prose_and_profile_representation",
        "artifact_distribution_note": "The archive PDF is a research input, not a package asset. Moira distributes only independently normalized rule data, code, schema, and provenance prose; no scan, OCR, page image, copied layout, source prose, or third-party translation is bundled.",
    }
    if source_obj != expected_source:
        raise PanchaPakshiDataError(
            "Padu profile source identity or distribution contract is unknown"
        )
    source = PanchaPakshiSource(**expected_source)

    expected_locator_specs = (
        (
            "bogar_n52_purva_padu",
            "n52",
            (
                "IA leaf n52 / PDF page 53 / printed page 43: Purva "
                "weekday Padu-bird stanza and commentary"
            ),
            "source_attested_purva_weekday_padu_bird_mapping",
        ),
        (
            "bogar_n60_amara_padu",
            "n60",
            (
                "IA leaf n60 / PDF page 61 / printed page 51: Amara "
                "weekday Padu-bird stanza and commentary"
            ),
            "source_attested_amara_weekday_padu_bird_mapping",
        ),
        (
            "bogar_n157_combined_padu_table",
            "n157",
            (
                "IA leaf n157 / PDF page 158 / printed page 148: repeated "
                "combined Purva and Amara weekday Padu-bird table"
            ),
            "source_repeated_combined_weekday_padu_bird_table",
        ),
        (
            "bogar_n158_combined_padu_commentary",
            "n158",
            (
                "IA leaf n158 / PDF page 159 / printed page 149: commentary "
                "restates both weekday Padu-bird mappings"
            ),
            "source_repeated_combined_weekday_padu_bird_commentary",
        ),
    )
    raw_locators = _require_list(document["source_locators"], "source_locators")
    locators = tuple(
        PanchaPakshiSourceLocator(
            locator_id=locator_id,
            witness_id=source.witness_id,
            label=label,
            url=f"{source.archive_item_url}/page/{leaf}/mode/1up",
            evidence_role=evidence_role,
        )
        for locator_id, leaf, label, evidence_role in expected_locator_specs
    )
    expected_locator_documents = [
        {
            "locator_id": locator.locator_id,
            "witness_id": locator.witness_id,
            "label": locator.label,
            "url": locator.url,
            "evidence_role": locator.evidence_role,
        }
        for locator in locators
    ]
    if raw_locators != expected_locator_documents:
        raise PanchaPakshiDataError(
            "Padu profile source locator ledger disagrees with exact evidence"
        )
    locator_ids = {locator.locator_id for locator in locators}

    mapping_obj = _require_dict(
        document["padu_bird_mapping"],
        "padu_bird_mapping",
    )
    _require_exact_keys(
        mapping_obj,
        {"mapping_kind", "source_table_semantics", "assembly_policy", "entries"},
        "padu_bird_mapping",
    )
    mapping_kind = _require_string(
        mapping_obj["mapping_kind"],
        "padu_bird_mapping.mapping_kind",
    )
    if mapping_kind != "profile_paksha_and_weekday_to_padu_bird":
        raise PanchaPakshiDataError("Padu-bird mapping kind is unknown")
    source_table_semantics = _require_string(
        mapping_obj["source_table_semantics"],
        "padu_bird_mapping.source_table_semantics",
    )
    if source_table_semantics != (
        "profile_paksha_weekday_death_or_inoperative_bird_not_schedule_rule_"
        "activity"
    ):
        raise PanchaPakshiDataError("Padu-bird source semantics are unknown")
    if mapping_obj["assembly_policy"] != meta["assembly_policy"]:
        raise PanchaPakshiDataError(
            "Padu-bird mapping assembly policy disagrees with profile"
        )

    purva_birds = (
        PanchaPakshiBird.OWL,
        PanchaPakshiBird.CROW,
        PanchaPakshiBird.COCK,
        PanchaPakshiBird.PEACOCK,
        PanchaPakshiBird.VULTURE,
        PanchaPakshiBird.OWL,
        PanchaPakshiBird.VULTURE,
    )
    amara_birds = (
        PanchaPakshiBird.CROW,
        PanchaPakshiBird.OWL,
        PanchaPakshiBird.VULTURE,
        PanchaPakshiBird.PEACOCK,
        PanchaPakshiBird.COCK,
        PanchaPakshiBird.PEACOCK,
        PanchaPakshiBird.COCK,
    )
    expected_mapping_entries = tuple(
        (paksha, weekday, birds[index], locator_ids_for_paksha)
        for paksha, birds, locator_ids_for_paksha in (
            (
                PanchaPakshiPaksha.PURVA,
                purva_birds,
                (
                    "bogar_n52_purva_padu",
                    "bogar_n157_combined_padu_table",
                    "bogar_n158_combined_padu_commentary",
                ),
            ),
            (
                PanchaPakshiPaksha.AMARA,
                amara_birds,
                (
                    "bogar_n60_amara_padu",
                    "bogar_n157_combined_padu_table",
                    "bogar_n158_combined_padu_commentary",
                ),
            ),
        )
        for index, weekday in enumerate(_WEEKDAYS)
    )
    raw_mapping_entries = _require_list(
        mapping_obj["entries"],
        "padu_bird_mapping.entries",
    )
    expected_mapping_documents = [
        {
            "profile_paksha": paksha.value,
            "weekday": weekday.value,
            "bird": bird.value,
            "source_locators": list(source_locator_ids),
        }
        for paksha, weekday, bird, source_locator_ids in expected_mapping_entries
    ]
    if raw_mapping_entries != expected_mapping_documents:
        raise PanchaPakshiDataError(
            "Padu-bird table disagrees with the 14 visually verified source cells"
        )
    padu_bird_rules = tuple(
        _PaduBirdRule(
            profile_paksha=paksha,
            weekday=weekday,
            bird=bird,
            source_locator_ids=source_locator_ids,
        )
        for paksha, weekday, bird, source_locator_ids in expected_mapping_entries
    )

    omissions: list[PanchaPakshiOmission] = []
    for index, raw_omission in enumerate(
        _require_list(document["explicit_omissions"], "explicit_omissions")
    ):
        context = f"explicit_omissions[{index}]"
        omission = _require_dict(raw_omission, context)
        _require_exact_keys(omission, {"feature", "status", "reason"}, context)
        parsed = PanchaPakshiOmission(
            feature=_require_string(omission["feature"], f"{context}.feature"),
            status=_require_string(omission["status"], f"{context}.status"),
            reason=_require_string(omission["reason"], f"{context}.reason"),
        )
        if parsed.status != "omitted":
            raise PanchaPakshiDataError(f"{context}.status must be omitted")
        omissions.append(parsed)
    if (
        {omission.feature for omission in omissions} != _REQUIRED_PADU_OMISSIONS
        or len(omissions) != len(_REQUIRED_PADU_OMISSIONS)
    ):
        raise PanchaPakshiDataError(
            "Padu profile explicit omissions are incomplete or duplicated"
        )

    conflicts = _require_list(
        document["research_conflict_ledger"],
        "research_conflict_ledger",
    )
    if conflicts:
        raise PanchaPakshiDataError(
            "Padu profile must not invent a research conflict witness"
        )

    referenced_locator_ids = {
        locator_id
        for rule in padu_bird_rules
        for locator_id in rule.source_locator_ids
    }
    if referenced_locator_ids != locator_ids:
        raise PanchaPakshiDataError(
            "Padu source locator ledger contains unreferenced or missing evidence"
        )

    return PanchaPakshiPaduBirdProfile(
        profile_id=meta["profile_id"],
        admission_status=admission_status,
        product_kind=meta["product_kind"],
        default_selection_allowed=default_selection_allowed,
        capabilities=capabilities,
        admission_decision_id=admission_decision_id,
        derivation_status=meta["derivation_status"],
        assembly_policy=meta["assembly_policy"],
        title=meta["title"],
        source=source,
        source_locators=tuple(locators),
        padu_bird_mapping_kind=mapping_kind,
        source_table_semantics=source_table_semantics,
        padu_bird_rules=padu_bird_rules,
        explicit_omissions=tuple(omissions),
        research_conflict_ledger=(),
    )


def _parse_sookshma_selector_profile_document(
    document: dict[str, Any],
    *,
    admission_status: PanchaPakshiAdmissionStatus,
    default_selection_allowed: bool,
    capabilities: tuple[PanchaPakshiCapability, ...],
    admission_decision_id: str,
) -> PanchaPakshiSookshmaSelectorProfile:
    """Parse the distinct weighted and equal-fifths Sookshma policies."""

    if not isinstance(admission_status, PanchaPakshiAdmissionStatus):
        raise PanchaPakshiDataError("admission_status must be a known enum value")
    _require_bool(default_selection_allowed, "default_selection_allowed")
    if default_selection_allowed:
        raise PanchaPakshiDataError(
            "default_selection_allowed must remain false; selector policy "
            "choice is explicit"
        )
    if capabilities != _PRODUCT_CAPABILITIES["sookshma_temporal_selector"]:
        raise PanchaPakshiDataError(
            "manifest capabilities disagree with Sookshma selector product"
        )
    _require_string(admission_decision_id, "admission_decision_id")

    _require_exact_keys(
        document,
        {
            "schema_version",
            "profile",
            "source",
            "source_locators",
            "selector_policies",
            "policy_relation",
            "explicit_omissions",
            "research_conflict_ledger",
        },
        "Sookshma selector profile document",
    )
    if _require_int(document["schema_version"], "profile.schema_version") != 1:
        raise PanchaPakshiDataError(
            "unsupported Pancha Pakshi Sookshma selector profile schema"
        )

    meta = _require_dict(document["profile"], "profile.profile")
    expected_meta = {
        "profile_id": "bogamuni_chennai_2024_sookshma_temporal_selector",
        "product_kind": "sookshma_temporal_selector",
        "derivation_status": (
            "visually_verified_source_sookshma_selector_policies"
        ),
        "assembly_policy": (
            "preserve_weighted_and_equal_fifths_as_distinct_explicit_policies"
        ),
        "title": "Bogamuni 2024 Sookshma temporal selector policies",
    }
    if meta != expected_meta:
        raise PanchaPakshiDataError(
            "Sookshma selector profile identity or doctrine is unknown"
        )

    source_obj = _require_dict(document["source"], "profile.source")
    expected_source = {
        "witness_id": "acc.-no.-44757-panjapatchi-sashthiram-2024",
        "title": "போகமுனிவர் பஞ்சபட்சி சாஸ்திரம் உரையுடன்",
        "traditional_attribution": "Bogamuni",
        "authorship_status": "traditional_attribution_not_asserted_authorship",
        "publication_place": "Vadapalani, Chennai",
        "publisher": "Thamarai Noolagam",
        "publication_year": 2024,
        "language": "Tamil",
        "archive_item_url": (
            "https://archive.org/details/"
            "acc.-no.-44757-panjapatchi-sashthiram-2024"
        ),
        "archive_original_image_zip_name": (
            "not_applicable_no_original_image_zip_bound"
        ),
        "archive_original_image_zip_source_status": (
            "not_applicable_pdf_is_internet_archive_original"
        ),
        "archive_original_image_zip_md5": "not_applicable",
        "archive_original_image_zip_sha1": "not_applicable",
        "archive_pdf_name": "Acc.No.44757-PanjapatchiSashthiram-2024.pdf",
        "archive_pdf_source_status": "internet_archive_original",
        "archive_pdf_md5": "abe489a832ac38a0270335b7429776f3",
        "archive_pdf_sha1": "6ddad8f2577883f6859829f534e8ee7b8330ade8",
        "locally_verified_pdf_sha256": (
            "035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990"
        ),
        "catalogued_contributor_note": (
            "The sixth edition names R. C. Mohan as editor; Moira does not "
            "convert that editorial credit into authorship of the "
            "traditionally attributed work."
        ),
        "artifact_distribution_status": (
            "reference_only_source_artifacts_not_packaged"
        ),
        "redistribution_policy": (
            "normalized_rules_only_no_scan_ocr_page_images_layout_source_"
            "prose_or_third_party_translation"
        ),
        "license_scope": (
            "mit_covers_moira_authored_code_schema_prose_and_profile_"
            "representation"
        ),
        "artifact_distribution_note": (
            "The archive PDF is a research input, not a package asset. Moira "
            "distributes only independently normalized rule data, code, "
            "schema, and provenance prose; no scan, OCR, page image, copied "
            "layout, source prose, or third-party translation is bundled."
        ),
    }
    if source_obj != expected_source:
        raise PanchaPakshiDataError(
            "Sookshma source identity or distribution contract is unknown"
        )
    source = PanchaPakshiSource(**expected_source)

    expected_locator_specs = (
        (
            "bogar_n156_samam_context",
            "n156",
            (
                "IA leaf n156 / PDF page 157 / printed page 147: "
                "six-nazhigai samam context"
            ),
            "source_attested_six_nazhigai_samam_context",
        ),
        (
            "bogar_n157_weighted_sookshma",
            "n157",
            (
                "IA leaf n157 / PDF page 158 / printed page 148: weighted "
                "Sookshma activity vector and cyclic rows"
            ),
            "source_attested_weighted_sookshma_selector",
        ),
        (
            "bogar_n168_eka_sookshma",
            "n168",
            (
                "IA leaf n168 / PDF page 169 / printed page 159: Eka "
                "Sookshma Chakra equal-fifths rule"
            ),
            "source_attested_eka_sookshma_equal_fifths_selector",
        ),
    )
    locators = tuple(
        PanchaPakshiSourceLocator(
            locator_id=locator_id,
            witness_id=source.witness_id,
            label=label,
            url=f"{source.archive_item_url}/page/{leaf}/mode/1up",
            evidence_role=evidence_role,
        )
        for locator_id, leaf, label, evidence_role in expected_locator_specs
    )
    expected_locator_documents = [
        {
            "locator_id": locator.locator_id,
            "witness_id": locator.witness_id,
            "label": locator.label,
            "url": locator.url,
            "evidence_role": locator.evidence_role,
        }
        for locator in locators
    ]
    if _require_list(document["source_locators"], "source_locators") != (
        expected_locator_documents
    ):
        raise PanchaPakshiDataError(
            "Sookshma source locator ledger disagrees with exact evidence"
        )
    locator_ids = {locator.locator_id for locator in locators}

    raw_policies = _require_list(
        document["selector_policies"],
        "selector_policies",
    )
    if len(raw_policies) != 2:
        raise PanchaPakshiDataError(
            "Sookshma profile must contain exactly two explicit policies"
        )
    selector_rules: list[_SookshmaSelectorRule] = []
    for index, raw_policy in enumerate(raw_policies):
        context = f"selector_policies[{index}]"
        obj = _require_dict(raw_policy, context)
        _require_exact_keys(
            obj,
            {
                "policy_id",
                "source_layer",
                "partition_kind",
                "container_span_nazhigai",
                "interval_count",
                "interval_ownership",
                "sequence_policy",
                "activity_assignment_status",
                "activity_durations_nazhigai",
                "source_locators",
            },
            context,
        )
        policy_id = _require_enum(
            PanchaPakshiSookshmaSelectorPolicyId,
            obj["policy_id"],
            f"{context}.policy_id",
        )
        raw_durations = _require_list(
            obj["activity_durations_nazhigai"],
            f"{context}.activity_durations_nazhigai",
        )
        durations: list[tuple[PanchaPakshiActivity, Fraction]] = []
        for duration_index, raw_duration in enumerate(raw_durations):
            duration_context = (
                f"{context}.activity_durations_nazhigai[{duration_index}]"
            )
            duration_obj = _require_dict(raw_duration, duration_context)
            _require_exact_keys(
                duration_obj,
                {"activity", "duration"},
                duration_context,
            )
            durations.append(
                (
                    _require_enum(
                        PanchaPakshiActivity,
                        duration_obj["activity"],
                        f"{duration_context}.activity",
                    ),
                    _parse_fraction(
                        duration_obj["duration"],
                        f"{duration_context}.duration",
                    ),
                )
            )
        rule = _SookshmaSelectorRule(
            policy_id=policy_id,
            source_layer=_require_string(
                obj["source_layer"], f"{context}.source_layer"
            ),
            partition_kind=_require_string(
                obj["partition_kind"], f"{context}.partition_kind"
            ),
            container_span_nazhigai=_parse_fraction(
                obj["container_span_nazhigai"],
                f"{context}.container_span_nazhigai",
            ),
            interval_count=_require_int(
                obj["interval_count"], f"{context}.interval_count"
            ),
            interval_ownership=_require_string(
                obj["interval_ownership"], f"{context}.interval_ownership"
            ),
            sequence_policy=_require_string(
                obj["sequence_policy"], f"{context}.sequence_policy"
            ),
            activity_assignment_status=_require_string(
                obj["activity_assignment_status"],
                f"{context}.activity_assignment_status",
            ),
            activity_durations_nazhigai=tuple(durations),
            source_locator_ids=_parse_locator_ids(
                obj["source_locators"],
                f"{context}.source_locators",
                locator_ids,
            ),
        )
        selector_rules.append(rule)

    expected_policy_ids = set(PanchaPakshiSookshmaSelectorPolicyId)
    if {rule.policy_id for rule in selector_rules} != expected_policy_ids:
        raise PanchaPakshiDataError(
            "Sookshma profile must define each admitted policy exactly once"
        )
    weighted = next(
        rule
        for rule in selector_rules
        if rule.policy_id
        is PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
    )
    if weighted.activity_durations_nazhigai != (
        (PanchaPakshiActivity.EAT, Fraction(3, 2)),
        (PanchaPakshiActivity.WALK, Fraction(5, 4)),
        (PanchaPakshiActivity.RULE, Fraction(2)),
        (PanchaPakshiActivity.SLEEP, Fraction(3, 4)),
        (PanchaPakshiActivity.DIE, Fraction(1, 2)),
    ):
        raise PanchaPakshiDataError(
            "weighted Sookshma duration vector is not canonical"
        )
    if (
        weighted.source_layer != "sookshma_pakshi_editorial_section"
        or weighted.partition_kind != "weighted_activity_durations"
        or weighted.sequence_policy
        != "cyclic_activity_order_with_each_row_beginning_at_its_named_activity"
        or weighted.activity_assignment_status
        != "source_attested_cyclic_activity_rows"
        or weighted.source_locator_ids
        != ("bogar_n156_samam_context", "bogar_n157_weighted_sookshma")
    ):
        raise PanchaPakshiDataError(
            "weighted Sookshma doctrine or evidence binding is not canonical"
        )
    if sum(
        (duration for _, duration in weighted.activity_durations_nazhigai),
        Fraction(),
    ) != Fraction(6):
        raise PanchaPakshiDataError(
            "weighted Sookshma duration vector does not close to six"
        )
    equal = next(
        rule
        for rule in selector_rules
        if rule.policy_id
        is PanchaPakshiSookshmaSelectorPolicyId.EKA_SOOKSHMA_EQUAL_FIFTHS
    )
    if equal.activity_durations_nazhigai:
        raise PanchaPakshiDataError(
            "Eka Sookshma policy must not invent activity assignments"
        )
    if (
        equal.source_layer != "eka_sookshma_chakra_editorial_section"
        or equal.partition_kind != "five_equal_parts"
        or equal.sequence_policy
        != "ordinal_only_no_subactivity_assignment_attested"
        or equal.activity_assignment_status != "not_attested"
        or equal.source_locator_ids
        != ("bogar_n156_samam_context", "bogar_n168_eka_sookshma")
    ):
        raise PanchaPakshiDataError(
            "Eka Sookshma doctrine or evidence binding is not canonical"
        )
    for rule in selector_rules:
        if (
            rule.container_span_nazhigai != Fraction(6)
            or rule.interval_count != 5
            or rule.interval_ownership != "half_open"
        ):
            raise PanchaPakshiDataError(
                "Sookshma policy container or interval contract is invalid"
            )

    relation = _require_dict(document["policy_relation"], "policy_relation")
    expected_relation = {
        "default_policy_id": None,
        "policies_are_interchangeable": False,
        "automatic_policy_selection": "forbidden",
        "uromarisi_composition_status": (
            "not_performed_requires_separate_explicit_cross_witness_decision"
        ),
        "outcome_interpretation_status": "not_performed",
    }
    if relation != expected_relation:
        raise PanchaPakshiDataError(
            "Sookshma policy relation must preserve no-default separation"
        )

    raw_omissions = _require_list(
        document["explicit_omissions"],
        "explicit_omissions",
    )
    omissions: list[PanchaPakshiOmission] = []
    for index, raw_omission in enumerate(raw_omissions):
        context = f"explicit_omissions[{index}]"
        omission = _require_dict(raw_omission, context)
        _require_exact_keys(omission, {"feature", "status", "reason"}, context)
        parsed = PanchaPakshiOmission(
            feature=_require_string(omission["feature"], f"{context}.feature"),
            status=_require_string(omission["status"], f"{context}.status"),
            reason=_require_string(omission["reason"], f"{context}.reason"),
        )
        if parsed.status != "omitted":
            raise PanchaPakshiDataError(f"{context}.status must be omitted")
        omissions.append(parsed)
    if (
        {omission.feature for omission in omissions}
        != _REQUIRED_SOOKSHMA_OMISSIONS
        or len(omissions) != len(_REQUIRED_SOOKSHMA_OMISSIONS)
    ):
        raise PanchaPakshiDataError(
            "Sookshma profile explicit omissions are incomplete or duplicated"
        )
    if _require_list(
        document["research_conflict_ledger"],
        "research_conflict_ledger",
    ):
        raise PanchaPakshiDataError(
            "Sookshma profile must preserve policy conflict internally"
        )
    referenced_locator_ids = {
        locator_id
        for rule in selector_rules
        for locator_id in rule.source_locator_ids
    }
    if referenced_locator_ids != locator_ids:
        raise PanchaPakshiDataError(
            "Sookshma locator ledger contains unreferenced or missing evidence"
        )

    return PanchaPakshiSookshmaSelectorProfile(
        profile_id=meta["profile_id"],
        admission_status=admission_status,
        product_kind=meta["product_kind"],
        default_selection_allowed=default_selection_allowed,
        capabilities=capabilities,
        admission_decision_id=admission_decision_id,
        derivation_status=meta["derivation_status"],
        assembly_policy=meta["assembly_policy"],
        title=meta["title"],
        source=source,
        source_locators=locators,
        selector_rules=tuple(selector_rules),
        automatic_policy_selection=relation["automatic_policy_selection"],
        uromarisi_composition_status=relation["uromarisi_composition_status"],
        outcome_interpretation_status=relation["outcome_interpretation_status"],
        explicit_omissions=tuple(omissions),
        research_conflict_ledger=(),
    )


def _validate_padu_mapping_completeness(
    profile: PanchaPakshiPaduBirdProfile,
) -> None:
    expected_keys = {
        (paksha, weekday)
        for paksha in PanchaPakshiPaksha
        for weekday in PanchaPakshiWeekday
    }
    actual_keys = {
        (rule.profile_paksha, rule.weekday) for rule in profile.padu_bird_rules
    }
    if actual_keys != expected_keys or len(profile.padu_bird_rules) != 14:
        raise PanchaPakshiDataError(
            "Padu profile does not provide exactly one mapping for all 14 cells"
        )
    for paksha, weekday in expected_keys:
        profile.padu_bird_rule(paksha, weekday)


def _validate_natal_mapping_completeness(
    profile: PanchaPakshiNatalIdentityProfile,
) -> None:
    expected_keys = {
        (paksha, nakshatra_index)
        for paksha in PanchaPakshiPaksha
        for nakshatra_index in range(27)
    }
    actual_keys = {
        (rule.profile_paksha, rule.nakshatra_index)
        for rule in profile.nakshatra_bird_rules
    }
    if actual_keys != expected_keys or len(profile.nakshatra_bird_rules) != 54:
        raise PanchaPakshiDataError(
            "natal profile does not provide exactly one mapping for all 54 cells"
        )
    for paksha, nakshatra_index in expected_keys:
        profile.nakshatra_bird_rule(paksha, nakshatra_index)


def _validate_generated_completeness(profile: PanchaPakshiProfile) -> None:
    for paksha, half in _CONTEXTS:
        for weekday in profile.weekdays:
            schedule = generate_pancha_pakshi_schedule(
                profile, paksha=paksha, half=half, weekday=weekday
            )
            if len(schedule.cells) != 25:
                raise PanchaPakshiDataError(
                    f"{schedule.generator_id} {weekday.value} is incomplete"
                )

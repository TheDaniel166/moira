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

No sunrise scaling, astronomical paksha routing, scoring, cross-witness
relationship normalization, vinadi subdivision, or natal mapping is performed
in this private layer.  The one relationship surface is the source-scoped,
explicitly directed 20-cell matrix from the 1879 witness.
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
_PRODUCT_CAPABILITIES = {
    "aksara_prasna_operating_schedule": (
        PanchaPakshiCapability.AKSARA_IDENTITY,
        PanchaPakshiCapability.NOMINAL_SCHEDULE,
        PanchaPakshiCapability.DIRECTED_RELATIONSHIPS,
        PanchaPakshiCapability.ASTRONOMICAL_CONTEXT,
        PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION,
        PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION,
    )
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
class _ScheduleGenerator:
    generator_id: str
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    first_eat_by_weekday: tuple[PanchaPakshiBird, ...]
    eat_step_per_samam: int
    activity_offsets: tuple[tuple[PanchaPakshiActivity, int], ...]
    chronological_activities: tuple[PanchaPakshiActivity, ...]
    source_locator_ids: tuple[str, ...]

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


def load_pancha_pakshi_profile(profile_id: str) -> PanchaPakshiProfile:
    """Load one explicitly named, hash-verified internal profile."""

    if not isinstance(profile_id, str):
        raise TypeError("profile_id must be a string")
    if not profile_id:
        raise ValueError("profile_id must not be empty; there is no default canon")
    return _load_profile_cached(profile_id, str(_MANIFEST_PATH.resolve()))


def _profile_provenance(
    profile: PanchaPakshiProfile,
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
    profile: PanchaPakshiProfile,
) -> PanchaPakshiProfileInfo:
    """Return public profile metadata without exposing loader internals."""

    _require_profile(profile)
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
    first_eat = generator.first_eat_by_weekday[_WEEKDAYS.index(weekday)]
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


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _resolve_locators(
    profile: PanchaPakshiProfile, locator_ids: tuple[str, ...]
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
) -> PanchaPakshiProfile:
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
    profile = _parse_profile_document(
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
    _validate_generated_completeness(profile)
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
    if _require_int(document["schema_version"], "profile.schema_version") != 2:
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
        "machine_reconciled_source_assignment_pending_competent_tamil_review"
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
        temporal_model=temporal_model,
        duration_rules=tuple(duration_rules),
        generators=tuple(generators),
        relationship_model_kind=relationship_model_kind,
        relationship_self_policy=relationship_self_policy,
        relationship_rules=tuple(relationship_rules),
        explicit_omissions=tuple(omissions),
        research_conflict_ledger=tuple(conflicts),
    )


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

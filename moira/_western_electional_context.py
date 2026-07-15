"""Dorotheus Book V rooted electional context.

This module owns a shared, non-scored context vessel for the sequence in
*Carmen Astrologicum* V.6.21-31 and the six matter families in V.31.  It keeps
the Moon (the work's root), the Moon-sign lord (the outcome), the next lunar
connection, matter significators, and optional natal evidence distinct.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .chart import ChartContext, create_chart
from .constants import Body, SIGNS, sign_of
from .houses import HousePolicy, assign_house, describe_angularity
from .profections import DOMICILE_RULERS
from .spk_reader import SpkReader, get_reader
from .void_of_course import MoonConnection, next_moon_connection


__all__ = [
    "WesternElectionClass",
    "DorotheusMatter",
    "DorotheusStrengthState",
    "DorotheusRootOutcomePattern",
    "DorotheusSignificatorCondition",
    "DorotheusPlacementWitness",
    "DorotheusRootOutcomeWitness",
    "DorotheusMatterSignificatorWitness",
    "DorotheusRadicalityWitness",
    "DorotheusRootedContextPolicy",
    "DorotheusRootedContextEvaluation",
    "DOROTHEUS_ROOTED_CONTEXT_V1",
    "evaluate_dorotheus_rooted_context",
    "dorotheus_rooted_context_at",
]


_AUTHORITY_V6 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.6.21-31, printed pp. 236-237"
)
_AUTHORITY_V31 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.31.1-11, printed pp. 276-277"
)
_TRADITIONAL_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
)
_CONFIGURED_OFFSETS = frozenset((0, 2, 3, 4, 6, 8, 9, 10))


class WesternElectionClass(str, Enum):
    """Declared relationship between the election and natal evidence."""

    EPHEMERAL = "ephemeral"
    RADICAL = "radical"


class DorotheusMatter(str, Enum):
    """The six admitted V.31 matter families."""

    LAND_AND_MANAGEMENT = "land_and_management"
    MERCURIAL_AFFAIRS = "mercurial_affairs"
    MARRIAGE_SEX_AND_PLEASURE = "marriage_sex_and_pleasure"
    WAR_AND_ARMS = "war_and_arms"
    RULERS_AND_PETITIONS = "rulers_and_petitions"
    MANIFEST_AND_PROMINENT = "manifest_and_prominent"


_MATTER_SIGNIFICATORS: dict[DorotheusMatter, tuple[str, ...]] = {
    DorotheusMatter.LAND_AND_MANAGEMENT: (Body.SATURN, Body.JUPITER),
    DorotheusMatter.MERCURIAL_AFFAIRS: (Body.MERCURY,),
    DorotheusMatter.MARRIAGE_SEX_AND_PLEASURE: (Body.VENUS,),
    DorotheusMatter.WAR_AND_ARMS: (Body.MARS,),
    DorotheusMatter.RULERS_AND_PETITIONS: (Body.JUPITER,),
    DorotheusMatter.MANIFEST_AND_PROMINENT: (Body.SUN, Body.JUPITER),
}


class DorotheusStrengthState(str, Enum):
    """House-power state used by the V.6 root/outcome sequence."""

    ANGULAR = "angular"
    SUCCEDENT = "succedent"
    CADENT = "cadent"
    NOT_EVALUABLE = "not_evaluable"


class DorotheusRootOutcomePattern(str, Enum):
    """Named V.6 root/outcome patterns; no numeric score is implied."""

    GOOD_ROOT_BAD_OUTCOME = "good_root_bad_outcome"
    DIFFICULT_ROOT_SUITABLE_OUTCOME = "difficult_root_suitable_outcome"
    GOOD_ROOT_AND_OUTCOME = "good_root_and_outcome"
    BAD_ROOT_WORSE_OUTCOME = "bad_root_worse_outcome"
    UNCLASSIFIED = "unclassified"
    NOT_EVALUABLE = "not_evaluable"


class DorotheusSignificatorCondition(str, Enum):
    """Bounded V.31 condition state for one matter significator."""

    CLEAR_OF_COMPUTED_IMPEDIMENTS = "clear_of_computed_impediments"
    ONE_OR_MORE_COMPUTED_IMPEDIMENTS = "one_or_more_computed_impediments"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class DorotheusPlacementWitness:
    body: str
    role: str
    longitude: float
    sign: str
    house: int | None
    strength: DorotheusStrengthState
    house_system_is_quadrant: bool
    explanation: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.longitude) or not 0.0 <= self.longitude < 360.0:
            raise ValueError("placement longitude must be finite in [0, 360)")
        if self.sign not in SIGNS:
            raise ValueError("placement sign must be canonical")
        if self.house is not None and not 1 <= self.house <= 12:
            raise ValueError("placement house must be in [1, 12]")
        if not self.role or not self.explanation:
            raise ValueError("placement role and explanation must be visible")


@dataclass(frozen=True, slots=True)
class DorotheusRootOutcomeWitness:
    moon: DorotheusPlacementWitness
    moon_sign_lord: DorotheusPlacementWitness
    pattern: DorotheusRootOutcomePattern
    outcome_delayed: bool | None
    source_reference: str = _AUTHORITY_V6
    interpretation_scope: str = "source_named_pattern_not_complete_judgement"


@dataclass(frozen=True, slots=True)
class DorotheusMatterSignificatorWitness:
    body: str
    placement: DorotheusPlacementWitness
    under_rays: bool
    solar_distance_degrees: float | None
    configured_malefics: tuple[str, ...]
    looks_at_ascendant: bool
    bad_place_evaluated: bool
    bad_place: bool | None
    condition: DorotheusSignificatorCondition
    source_reference: str = _AUTHORITY_V31
    uncomputed_requirements: tuple[str, ...] = (
        "V.31 'made unfortunate'; whole-sign malefic configuration is evidence only",
        "V.31 'bad place' because this passage does not define its place set",
    )

    def __post_init__(self) -> None:
        if self.solar_distance_degrees is not None and not math.isfinite(
            self.solar_distance_degrees
        ):
            raise ValueError("solar distance must be finite when supplied")
        if self.bad_place_evaluated or self.bad_place is not None:
            raise ValueError("bad-place truth is not admitted in v1")


@dataclass(frozen=True, slots=True)
class DorotheusRadicalityWitness:
    election_class: WesternElectionClass
    natal_required: bool
    natal_provided: bool
    election_ascendant_sign: str
    election_ascendant_lord: str
    natal_ascendant_sign: str | None
    natal_ascendant_lord: str | None
    assessment_semantics: str = "evidence_only_not_success_gate"

    def __post_init__(self) -> None:
        if self.election_ascendant_sign not in SIGNS:
            raise ValueError("election Ascendant sign must be canonical")
        if self.natal_required != (self.election_class is WesternElectionClass.RADICAL):
            raise ValueError("natal requirement must derive from election class")
        if self.natal_required != self.natal_provided:
            raise ValueError("radical requests require natal evidence; ephemeral requests reject it")


@dataclass(frozen=True, slots=True)
class DorotheusRootedContextPolicy:
    """Closed policy for the first shared Dorothean context vessel."""

    profile_id: str = "dorotheus_rooted_context_v1"
    profile_version: str = "1.0.0"
    strength_policy: str = "quadrant_house_angular_succedent_cadent"
    aspect_policy: str = "whole_sign_configuration"
    under_rays_degrees: float = 15.0
    bad_place_policy: str = "not_admitted_without_passage_owned_place_set"
    next_connection_policy: str = "first_exact_traditional_aspect_before_sign_exit"

    def __post_init__(self) -> None:
        expected = DorotheusRootedContextPolicy.__dataclass_fields__
        defaults = {name: field.default for name, field in expected.items()}
        for name, value in defaults.items():
            if getattr(self, name) != value:
                raise ValueError(f"{name} is fixed for this admitted profile")


DOROTHEUS_ROOTED_CONTEXT_V1 = DorotheusRootedContextPolicy()


@dataclass(frozen=True, slots=True)
class DorotheusRootedContextEvaluation:
    jd_ut: float
    profile_id: str
    profile_version: str
    matter: DorotheusMatter
    election_class: WesternElectionClass
    root_outcome: DorotheusRootOutcomeWitness
    matter_significators: tuple[DorotheusMatterSignificatorWitness, ...]
    next_connection: MoonConnection | None
    next_connection_placement: DorotheusPlacementWitness | None
    radicality: DorotheusRadicalityWitness
    reader_provenance: str
    latitude: float
    longitude: float
    requested_house_system: str
    effective_house_system: str
    house_fallback: bool
    authorities: tuple[str, ...] = (_AUTHORITY_V6, _AUTHORITY_V31)
    uncomputed_requirements: tuple[str, ...] = (
        "V.6.29 ninth-part or Lot-of-Fortune ruler variants",
        "a source-owned universal success or auspiciousness score",
    )
    complete_electional_judgement: bool = False
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_ut):
            raise ValueError("jd_ut must be finite")
        if not self.matter_significators:
            raise ValueError("matter significators must be preserved")
        expected = _MATTER_SIGNIFICATORS[self.matter]
        actual = tuple(item.body for item in self.matter_significators)
        if actual != expected:
            raise ValueError("matter significators must derive from the V.31 registry")
        if self.complete_electional_judgement:
            raise ValueError("the rooted context is not a complete electional judgement")


def _shortest_distance(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _whole_sign_offset(a_sign: str, b_sign: str) -> int:
    return (SIGNS.index(b_sign) - SIGNS.index(a_sign)) % 12


def _placement(chart: ChartContext, body: str, role: str) -> DorotheusPlacementWitness:
    planet = chart.planets.get(body)
    if planet is None:
        raise ValueError(f"chart must contain {body}")
    houses = chart.houses
    if houses is None or not houses.is_quadrant_system:
        return DorotheusPlacementWitness(
            body=body,
            role=role,
            longitude=planet.longitude,
            sign=planet.sign,
            house=None,
            strength=DorotheusStrengthState.NOT_EVALUABLE,
            house_system_is_quadrant=False,
            explanation=(
                "Dynamic stake strength requires a quadrant house figure; the "
                "selected effective system does not provide one."
            ),
        )
    placement = assign_house(planet.longitude, houses)
    category = describe_angularity(placement).category.value
    return DorotheusPlacementWitness(
        body=body,
        role=role,
        longitude=planet.longitude,
        sign=planet.sign,
        house=placement.house,
        strength=DorotheusStrengthState(category),
        house_system_is_quadrant=True,
        explanation="Strength is the house's angular, succedent, or cadent stake relation.",
    )


def _root_outcome(
    moon: DorotheusPlacementWitness,
    lord: DorotheusPlacementWitness,
) -> DorotheusRootOutcomeWitness:
    if (
        moon.strength is DorotheusStrengthState.NOT_EVALUABLE
        or lord.strength is DorotheusStrengthState.NOT_EVALUABLE
    ):
        pattern = DorotheusRootOutcomePattern.NOT_EVALUABLE
        delayed = None
    elif moon.strength is DorotheusStrengthState.ANGULAR and lord.strength is DorotheusStrengthState.CADENT:
        pattern = DorotheusRootOutcomePattern.GOOD_ROOT_BAD_OUTCOME
        delayed = False
    elif moon.strength is DorotheusStrengthState.CADENT and lord.strength is DorotheusStrengthState.ANGULAR:
        pattern = DorotheusRootOutcomePattern.DIFFICULT_ROOT_SUITABLE_OUTCOME
        delayed = False
    elif moon.strength is DorotheusStrengthState.ANGULAR and lord.strength is DorotheusStrengthState.ANGULAR:
        pattern = DorotheusRootOutcomePattern.GOOD_ROOT_AND_OUTCOME
        delayed = False
    elif moon.strength is DorotheusStrengthState.CADENT and lord.strength is DorotheusStrengthState.CADENT:
        pattern = DorotheusRootOutcomePattern.BAD_ROOT_WORSE_OUTCOME
        delayed = False
    else:
        pattern = DorotheusRootOutcomePattern.UNCLASSIFIED
        delayed = lord.strength is DorotheusStrengthState.SUCCEDENT
    return DorotheusRootOutcomeWitness(
        moon=moon,
        moon_sign_lord=lord,
        pattern=pattern,
        outcome_delayed=delayed,
    )


def _matter_witness(
    chart: ChartContext,
    body: str,
    policy: DorotheusRootedContextPolicy,
) -> DorotheusMatterSignificatorWitness:
    planet = chart.planets[body]
    sun = chart.planets[Body.SUN]
    distance = None if body == Body.SUN else _shortest_distance(
        planet.longitude, sun.longitude
    )
    under_rays = distance is not None and distance <= policy.under_rays_degrees
    configured: list[str] = []
    for malefic_name in (Body.MARS, Body.SATURN):
        if malefic_name == body:
            continue
        malefic = chart.planets[malefic_name]
        if _whole_sign_offset(planet.sign, malefic.sign) in _CONFIGURED_OFFSETS:
            configured.append(malefic_name)
    asc_sign, _, _ = sign_of(chart.houses.asc)
    looks_at_asc = _whole_sign_offset(planet.sign, asc_sign) in _CONFIGURED_OFFSETS
    computed_impediment = under_rays or not looks_at_asc
    condition = (
        DorotheusSignificatorCondition.ONE_OR_MORE_COMPUTED_IMPEDIMENTS
        if computed_impediment
        else DorotheusSignificatorCondition.INDETERMINATE
    )
    return DorotheusMatterSignificatorWitness(
        body=body,
        placement=_placement(chart, body, "matter_significator"),
        under_rays=under_rays,
        solar_distance_degrees=distance,
        configured_malefics=tuple(configured),
        looks_at_ascendant=looks_at_asc,
        bad_place_evaluated=False,
        bad_place=None,
        condition=condition,
    )


def evaluate_dorotheus_rooted_context(
    chart: ChartContext,
    *,
    matter: DorotheusMatter,
    election_class: WesternElectionClass = WesternElectionClass.EPHEMERAL,
    next_connection: MoonConnection | None,
    natal_chart: ChartContext | None = None,
    reader_provenance: str,
    policy: DorotheusRootedContextPolicy = DOROTHEUS_ROOTED_CONTEXT_V1,
) -> DorotheusRootedContextEvaluation:
    """Evaluate the shared V.6/V.31 context from already-owned chart truth."""

    if not isinstance(policy, DorotheusRootedContextPolicy):
        raise TypeError("policy must be a DorotheusRootedContextPolicy")
    matter = DorotheusMatter(matter)
    election_class = WesternElectionClass(election_class)
    if election_class is WesternElectionClass.EPHEMERAL and natal_chart is not None:
        raise ValueError("ephemeral election context rejects natal chart input")
    if election_class is WesternElectionClass.RADICAL and natal_chart is None:
        raise ValueError("radical election context requires natal chart input")
    if chart.houses is None:
        raise ValueError("election chart must contain houses")
    for body in _TRADITIONAL_BODIES:
        if body not in chart.planets:
            raise ValueError(f"election chart must contain {body}")

    moon = chart.planets[Body.MOON]
    moon_lord_name = DOMICILE_RULERS[moon.sign]
    root_moon = _placement(chart, Body.MOON, "work_root")
    root_lord = _placement(chart, moon_lord_name, "moon_sign_lord_outcome")
    matter_witnesses = tuple(
        _matter_witness(chart, body, policy)
        for body in _MATTER_SIGNIFICATORS[matter]
    )
    connection_placement = None
    if next_connection is not None:
        connection_placement = _placement(
            chart, next_connection.body, "next_moon_connection"
        )

    election_asc_sign, _, _ = sign_of(chart.houses.asc)
    natal_asc_sign = None
    natal_asc_lord = None
    if natal_chart is not None:
        if natal_chart.houses is None:
            raise ValueError("natal chart must contain houses")
        natal_asc_sign, _, _ = sign_of(natal_chart.houses.asc)
        natal_asc_lord = DOMICILE_RULERS[natal_asc_sign]
    radicality = DorotheusRadicalityWitness(
        election_class=election_class,
        natal_required=election_class is WesternElectionClass.RADICAL,
        natal_provided=natal_chart is not None,
        election_ascendant_sign=election_asc_sign,
        election_ascendant_lord=DOMICILE_RULERS[election_asc_sign],
        natal_ascendant_sign=natal_asc_sign,
        natal_ascendant_lord=natal_asc_lord,
    )
    houses = chart.houses
    return DorotheusRootedContextEvaluation(
        jd_ut=chart.jd_ut,
        profile_id=policy.profile_id,
        profile_version=policy.profile_version,
        matter=matter,
        election_class=election_class,
        root_outcome=_root_outcome(root_moon, root_lord),
        matter_significators=matter_witnesses,
        next_connection=next_connection,
        next_connection_placement=connection_placement,
        radicality=radicality,
        reader_provenance=reader_provenance,
        latitude=chart.latitude,
        longitude=chart.longitude,
        requested_house_system=houses.system,
        effective_house_system=houses.effective_system,
        house_fallback=houses.fallback,
    )


def dorotheus_rooted_context_at(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    matter: DorotheusMatter,
    election_class: WesternElectionClass = WesternElectionClass.EPHEMERAL,
    natal_jd_ut: float | None = None,
    natal_latitude: float | None = None,
    natal_longitude: float | None = None,
    natal_house_system: str | None = None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    policy: DorotheusRootedContextPolicy = DOROTHEUS_ROOTED_CONTEXT_V1,
) -> DorotheusRootedContextEvaluation:
    """Construct election/natal inputs and evaluate the rooted context once."""

    election_class = WesternElectionClass(election_class)
    natal_values = (
        natal_jd_ut,
        natal_latitude,
        natal_longitude,
        natal_house_system,
    )
    if election_class is WesternElectionClass.EPHEMERAL and any(
        value is not None for value in natal_values
    ):
        raise ValueError("ephemeral election context rejects natal input")
    if election_class is WesternElectionClass.RADICAL and any(
        value is None for value in natal_values
    ):
        raise ValueError("radical election context requires complete natal input")

    resolved_reader = reader if reader is not None else get_reader()
    chart = create_chart(
        jd_ut,
        latitude,
        longitude,
        house_system=house_system,
        bodies=list(_TRADITIONAL_BODIES),
        reader=resolved_reader,
        policy=house_policy,
    )
    natal_chart = None
    if election_class is WesternElectionClass.RADICAL:
        natal_chart = create_chart(
            float(natal_jd_ut),
            float(natal_latitude),
            float(natal_longitude),
            house_system=str(natal_house_system),
            bodies=list(_TRADITIONAL_BODIES),
            reader=resolved_reader,
            policy=house_policy,
        )
    connection = next_moon_connection(jd_ut, reader=resolved_reader)
    reader_path = getattr(resolved_reader, "path", None)
    provenance = (
        str(reader_path)
        if reader_path is not None
        else f"{type(resolved_reader).__module__}.{type(resolved_reader).__qualname__}"
    )
    return evaluate_dorotheus_rooted_context(
        chart,
        matter=DorotheusMatter(matter),
        election_class=election_class,
        next_connection=connection,
        natal_chart=natal_chart,
        reader_provenance=provenance,
        policy=policy,
    )

"""
Moira - varshaphal.py
Tajika / Varshaphal doctrine layer above the sidereal solar-return substrate.

Boundary: owns Muntha progression, Saham computation, and the structured
Varshaphal annual-chart vessel. Delegates solar-return timing to
moira.transits.varshaphal(), chart assembly to moira.chart/create_chart,
sidereal conversion to moira.sidereal, and house membership to moira.houses.

Doctrinal basis used here:
    - Muntha: progressed Ascendant advanced one sign per completed year, with
      the natal Ascendant degree preserved.
    - Sahams: formulae summarized from B.V. Raman's Varshaphala exposition via
      verified secondary technical summaries. The layer preserves the 30-degree
      correction rule and the default day/night operand reversal doctrine.

This module does not implement Tajika aspects, Mudda Dasha timing, or
interpretive judgement.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from .aspects import AspectData, aspects_between
from .chart import ChartContext
from .constants import HouseSystem, sign_of
from .houses import HouseCusps, HousePolicy, house_of, calculate_houses
from .julian import calendar_datetime_from_jd
from .profections import DOMICILE_RULERS
from .sidereal import Ayanamsa, UserDefinedAyanamsa, ayanamsa, tropical_to_sidereal
from .spk_reader import SpkReader
from .transits import TransitComputationPolicy, varshaphal as _varshaphal_jd, varshaphal_chart as _varshaphal_chart
from .vedic_dignities import (
    DignityConditionProfile as VedicDignityConditionProfile,
    VedicDignityResult,
    DignityTier,
    dignity_condition_profile as vedic_dignity_condition_profile,
    vedic_dignity,
)

__all__ = [
    "VarshaphalSahamDefinition",
    "VarshaphalSaham",
    "TajikaAspectPolicy",
    "TajikaAspect",
    "TajikaYoga",
    "MunthaConditionProfile",
    "VarshaphalChart",
    "muntha",
    "tajika_aspects",
    "tajika_yogas",
    "muntha_condition_profile",
    "varshaphal_sahams",
    "build_varshaphal_chart",
]


@dataclass(frozen=True, slots=True)
class VarshaphalSahamDefinition:
    """Definition of one Tajika Saham formula."""

    name: str
    minuend: str
    subtrahend: str
    addend: str
    reverse_at_night: bool = True


@dataclass(frozen=True, slots=True)
class VarshaphalSaham:
    """Computed Saham with audit-friendly formula metadata."""

    name: str
    longitude: float
    house: int
    ruler: str
    minuend: str
    subtrahend: str
    addend: str
    reversed_for_night: bool
    correction_applied: bool


@dataclass(frozen=True, slots=True)
class TajikaAspectPolicy:
    """
    Policy surface for Tajika annual aspect admission.

    ``classical_12_degree`` follows the common 12-degree effectiveness rule
    preserved in Hayanaratna. ``deeptamsa_half_sum`` uses the half-sum of the
    two planets' Deeptamsa values as the pair orb.
    """

    orb_mode: str = "classical_12_degree"
    include_conjunctions: bool = True


@dataclass(frozen=True, slots=True)
class TajikaAspect:
    """Structured Tajika annual aspect built from one admitted zodiacal aspect."""

    body1: str
    body2: str
    aspect: AspectData
    relation: str
    relation_strength: float
    effect: str
    is_benefic_relation: bool
    perfects_in_future: bool | None
    within_effective_orb: bool


@dataclass(frozen=True, slots=True)
class TajikaYoga:
    """Structured Tajika yoga result over an admitted annual aspect."""

    name: str
    body1: str
    body2: str
    aspect: TajikaAspect
    favorable: bool
    doctrine: str


@dataclass(frozen=True, slots=True)
class MunthaConditionProfile:
    """Structural annual-chart condition profile for Muntha and its lord."""

    muntha_longitude: float
    muntha_house: int
    muntha_sign: str
    muntha_lord: str
    muntha_lord_longitude: float
    muntha_lord_house: int
    muntha_lord_sign: str
    muntha_lord_dignity: VedicDignityResult
    muntha_lord_dignity_profile: VedicDignityConditionProfile
    muntha_lord_house_from_muntha: int
    lord_in_kendra: bool
    lord_in_trikona: bool
    lord_in_dusthana: bool
    lord_in_upachaya: bool
    lord_is_strong: bool
    lord_is_weak: bool


@dataclass(frozen=True, slots=True)
class VarshaphalChart:
    """Structured annual return doctrine vessel for Tajika / Varshaphal work."""

    birth_jd: float
    return_year: int
    years_elapsed: int
    jd_ut: float
    ayanamsa_system: str | UserDefinedAyanamsa
    chart: ChartContext
    sidereal_houses: HouseCusps
    sidereal_planets: dict[str, float]
    natal_sidereal_asc: float
    muntha_longitude: float
    muntha_house: int
    muntha_lord: str
    muntha_profile: MunthaConditionProfile
    tajika_aspects: tuple[TajikaAspect, ...]
    tajika_yogas: tuple[TajikaYoga, ...]
    sahams: tuple[VarshaphalSaham, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sidereal_planets", MappingProxyType(dict(self.sidereal_planets)))

    @property
    def muntha_sign(self) -> str:
        """Return the sidereal sign occupied by Muntha."""

        return sign_of(self.muntha_longitude)[0]

    def saham(self, name: str) -> VarshaphalSaham:
        """Return one Saham by name."""

        for saham in self.sahams:
            if saham.name == name:
                return saham
        raise KeyError(f"Unknown Varshaphal Saham: {name}")


_SAHAM_DEFINITIONS: tuple[VarshaphalSahamDefinition, ...] = (
    VarshaphalSahamDefinition("Punya", "Moon", "Sun", "Asc"),
    VarshaphalSahamDefinition("Vidya", "Sun", "Moon", "Asc"),
    VarshaphalSahamDefinition("Yasa", "Jupiter", "Punya", "Asc"),
    VarshaphalSahamDefinition("Mitra", "Jupiter", "Punya", "Venus"),
    VarshaphalSahamDefinition("Mahatmya", "Punya", "Mars", "Asc"),
    VarshaphalSahamDefinition("Asha", "Saturn", "Mars", "Asc"),
    VarshaphalSahamDefinition("Samartha", "Mars", "Asc Lord", "Asc"),
    VarshaphalSahamDefinition("Bhratru", "Jupiter", "Saturn", "Asc", reverse_at_night=False),
    VarshaphalSahamDefinition("Gaurava", "Jupiter", "Moon", "Sun"),
    VarshaphalSahamDefinition("Pitru", "Saturn", "Sun", "Asc"),
    VarshaphalSahamDefinition("Raja", "Saturn", "Sun", "Asc"),
    VarshaphalSahamDefinition("Matru", "Moon", "Venus", "Asc"),
    VarshaphalSahamDefinition("Putra", "Jupiter", "Moon", "Asc"),
    VarshaphalSahamDefinition("Jeeva", "Saturn", "Jupiter", "Asc"),
    VarshaphalSahamDefinition("Karma", "Mars", "Mercury", "Asc"),
    VarshaphalSahamDefinition("Roga", "Asc", "Moon", "Asc"),
    VarshaphalSahamDefinition("Kali", "Jupiter", "Mars", "Asc"),
    VarshaphalSahamDefinition("Sastra", "Jupiter", "Saturn", "Mercury"),
    VarshaphalSahamDefinition("Bandhu", "Mercury", "Moon", "Asc"),
    VarshaphalSahamDefinition("Mrityu", "8th House Cusp", "Moon", "Asc"),
    VarshaphalSahamDefinition("Paradesa", "9th House Cusp", "9th Lord", "Asc"),
    VarshaphalSahamDefinition("Artha", "2nd House Cusp", "2nd Lord", "Asc"),
    VarshaphalSahamDefinition("Paradara", "Venus", "Sun", "Asc"),
    VarshaphalSahamDefinition("Vanik", "Moon", "Mercury", "Asc"),
    VarshaphalSahamDefinition("Karyasiddhi", "Saturn", "Sun", "Sun-sign Lord"),
    VarshaphalSahamDefinition("Vivaha", "Venus", "Saturn", "Asc"),
    VarshaphalSahamDefinition("Santapa", "Saturn", "Moon", "6th House Cusp"),
    VarshaphalSahamDefinition("Sraddha", "Venus", "Mars", "Asc"),
    VarshaphalSahamDefinition("Preeti", "Sastra", "Punya", "Asc"),
    VarshaphalSahamDefinition("Jadya", "Mars", "Saturn", "Mercury"),
    VarshaphalSahamDefinition("Vyapara", "Mars", "Saturn", "Asc", reverse_at_night=False),
    VarshaphalSahamDefinition("Satru", "Mars", "Saturn", "Asc"),
    VarshaphalSahamDefinition("Jalapathana", "15 Cancer", "Saturn", "Asc"),
    VarshaphalSahamDefinition("Bandhana", "Punya", "Saturn", "Asc"),
    VarshaphalSahamDefinition("Apamrityu", "8th House Cusp", "Mars", "Asc"),
)

_TAJIKA_DEEPTAMSA: dict[str, float] = {
    "Sun": 15.0,
    "Moon": 12.0,
    "Mars": 8.0,
    "Mercury": 7.0,
    "Jupiter": 9.0,
    "Venus": 7.0,
    "Saturn": 9.0,
}

_TAJIKA_RELATIONS: dict[float, tuple[str, float, str, bool]] = {
    0.0: ("same_sign", 1.0, "same-sign conjunction", False),
    60.0: ("secret_friend", 0.25, "perfects the matter sought quietly", True),
    90.0: ("secret_enemy", 0.5, "obstructs the matter with hidden enmity", False),
    120.0: ("open_friend", 0.75, "openly supports and unites the matter", True),
    180.0: ("open_enemy", 1.0, "openly opposes the matter", False),
}

_TAJIKA_MAJORS: tuple[float, ...] = (0.0, 60.0, 90.0, 120.0, 180.0)


def _normalize(longitude: float) -> float:
    return longitude % 360.0


def _arc_contains(start: float, end: float, point: float) -> bool:
    """Return whether *point* lies on the direct zodiacal arc from start to end."""

    span = (end - start) % 360.0
    dist = (point - start) % 360.0
    return dist <= span


def _sign_lord(longitude: float) -> str:
    return DOMICILE_RULERS[sign_of(longitude)[0]]


def muntha(natal_sidereal_asc: float, years_elapsed: int) -> float:
    """Compute Muntha from the natal sidereal Ascendant and completed years."""

    if years_elapsed < 0:
        raise ValueError(f"years_elapsed must be >= 0, got {years_elapsed}")
    return _normalize(natal_sidereal_asc + years_elapsed * 30.0)


def _tajika_allowed_orb(
    body1: str,
    body2: str,
    policy: TajikaAspectPolicy,
) -> float:
    if policy.orb_mode == "classical_12_degree":
        return 12.0
    if policy.orb_mode == "deeptamsa_half_sum":
        return (_TAJIKA_DEEPTAMSA[body1] + _TAJIKA_DEEPTAMSA[body2]) / 2.0
    raise ValueError(f"Unsupported Tajika orb_mode: {policy.orb_mode}")


def tajika_aspects(
    planets: dict[str, float],
    planet_speeds: dict[str, float] | None = None,
    policy: TajikaAspectPolicy | None = None,
) -> tuple[TajikaAspect, ...]:
    """
    Compute Tajika annual aspects for the seven classical planets.

    Source basis:
    - Hayanaratna preserves the benefic/malefic sign-aspect classes
      (3/11, 4/10, 5/9, 7, and same-sign conjunction).
    - This implementation formalizes them through degree-based admission on the
      corresponding angular families so near-boundary cases within the admitted
      orb are preserved.
    """

    active_policy = TajikaAspectPolicy() if policy is None else policy
    classical = [
        body for body in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
        if body in planets
    ]
    results: list[TajikaAspect] = []
    for idx, body1 in enumerate(classical):
        for body2 in classical[idx + 1:]:
            allowed = _tajika_allowed_orb(body1, body2, active_policy)
            pair_aspects = aspects_between(
                body1,
                planets[body1],
                body2,
                planets[body2],
                orbs={angle: allowed for angle in _TAJIKA_MAJORS},
                speed_a=None if planet_speeds is None else planet_speeds.get(body1),
                speed_b=None if planet_speeds is None else planet_speeds.get(body2),
            )
            for aspect in pair_aspects:
                if aspect.angle not in _TAJIKA_RELATIONS:
                    continue
                if aspect.angle == 0.0 and not active_policy.include_conjunctions:
                    continue
                relation, strength, effect, benefic = _TAJIKA_RELATIONS[aspect.angle]
                results.append(
                    TajikaAspect(
                        body1=body1,
                        body2=body2,
                        aspect=aspect,
                        relation=relation,
                        relation_strength=strength,
                        effect=effect,
                        is_benefic_relation=benefic,
                        perfects_in_future=aspect.applying,
                        within_effective_orb=aspect.orb <= aspect.allowed_orb,
                    )
                )
    results.sort(key=lambda item: (item.aspect.orb, item.body1, item.body2, item.aspect.angle))
    return tuple(results)


def tajika_yogas(
    aspects: tuple[TajikaAspect, ...] | list[TajikaAspect],
) -> tuple[TajikaYoga, ...]:
    """
    Classify the foundational Tajika yogas over admitted annual aspects.

    This first doctrine layer admits only the two core applying/separating
    pair yogas: Ithasala and Isarpha.
    """

    results: list[TajikaYoga] = []
    for aspect in aspects:
        if aspect.aspect.angle == 0.0:
            continue
        if aspect.aspect.applying is True:
            results.append(
                TajikaYoga(
                    name="Ithasala",
                    body1=aspect.body1,
                    body2=aspect.body2,
                    aspect=aspect,
                    favorable=True,
                    doctrine="Applying Tajika aspect within effective orb; matter moves toward perfection.",
                )
            )
        elif aspect.aspect.applying is False:
            results.append(
                TajikaYoga(
                    name="Isarpha",
                    body1=aspect.body1,
                    body2=aspect.body2,
                    aspect=aspect,
                    favorable=False,
                    doctrine="Separating Tajika aspect within effective orb; the perfection has passed away.",
                )
            )
    return tuple(results)


def muntha_condition_profile(
    muntha_longitude: float,
    muntha_house: int,
    muntha_lord: str,
    sidereal_planets: dict[str, float],
    sidereal_houses: HouseCusps,
) -> MunthaConditionProfile:
    """Build a structural condition profile for Muntha and its lord."""

    if muntha_lord not in sidereal_planets:
        raise KeyError(f"Muntha lord {muntha_lord!r} not present in sidereal_planets")
    lord_longitude = sidereal_planets[muntha_lord]
    lord_house = house_of(lord_longitude, sidereal_houses)
    relative_house = ((lord_house - muntha_house) % 12) + 1
    dignity = vedic_dignity(muntha_lord, lord_longitude)
    dignity_profile = vedic_dignity_condition_profile(dignity)
    return MunthaConditionProfile(
        muntha_longitude=muntha_longitude,
        muntha_house=muntha_house,
        muntha_sign=sign_of(muntha_longitude)[0],
        muntha_lord=muntha_lord,
        muntha_lord_longitude=lord_longitude,
        muntha_lord_house=lord_house,
        muntha_lord_sign=sign_of(lord_longitude)[0],
        muntha_lord_dignity=dignity,
        muntha_lord_dignity_profile=dignity_profile,
        muntha_lord_house_from_muntha=relative_house,
        lord_in_kendra=lord_house in {1, 4, 7, 10},
        lord_in_trikona=lord_house in {1, 5, 9},
        lord_in_dusthana=lord_house in {6, 8, 12},
        lord_in_upachaya=lord_house in {3, 6, 10, 11},
        lord_is_strong=dignity_profile.tier == DignityTier.STRONG,
        lord_is_weak=dignity_profile.tier == DignityTier.WEAK,
    )


def _resolve_saham_operand(
    operand: str,
    *,
    ascendant: float,
    planets: dict[str, float],
    house_cusps: HouseCusps,
    derived: dict[str, VarshaphalSaham],
) -> float:
    if operand == "Asc":
        return ascendant
    if operand == "Asc Lord":
        return planets[_sign_lord(ascendant)]
    if operand == "2nd House Cusp":
        return house_cusps.cusps[1]
    if operand == "6th House Cusp":
        return house_cusps.cusps[5]
    if operand == "8th House Cusp":
        return house_cusps.cusps[7]
    if operand == "9th House Cusp":
        return house_cusps.cusps[8]
    if operand == "2nd Lord":
        return planets[_sign_lord(house_cusps.cusps[1])]
    if operand == "9th Lord":
        return planets[_sign_lord(house_cusps.cusps[8])]
    if operand == "Sun-sign Lord":
        return planets[_sign_lord(planets["Sun"])]
    if operand == "15 Cancer":
        return 105.0
    if operand in derived:
        return derived[operand].longitude
    if operand in planets:
        return planets[operand]
    raise KeyError(f"Unsupported Varshaphal Saham operand: {operand}")


def _compute_saham(
    definition: VarshaphalSahamDefinition,
    *,
    ascendant: float,
    planets: dict[str, float],
    house_cusps: HouseCusps,
    is_day: bool,
    derived: dict[str, VarshaphalSaham],
) -> VarshaphalSaham:
    minuend_name = definition.minuend
    subtrahend_name = definition.subtrahend
    reversed_for_night = False
    if not is_day and definition.reverse_at_night:
        minuend_name, subtrahend_name = subtrahend_name, minuend_name
        reversed_for_night = True

    minuend = _resolve_saham_operand(
        minuend_name,
        ascendant=ascendant,
        planets=planets,
        house_cusps=house_cusps,
        derived=derived,
    )
    subtrahend = _resolve_saham_operand(
        subtrahend_name,
        ascendant=ascendant,
        planets=planets,
        house_cusps=house_cusps,
        derived=derived,
    )
    addend = _resolve_saham_operand(
        definition.addend,
        ascendant=ascendant,
        planets=planets,
        house_cusps=house_cusps,
        derived=derived,
    )
    longitude = _normalize(minuend - subtrahend + addend)
    correction_applied = not _arc_contains(subtrahend, minuend, ascendant)
    if correction_applied:
        longitude = _normalize(longitude + 30.0)

    house = house_of(longitude, house_cusps)
    ruler = _sign_lord(longitude)
    return VarshaphalSaham(
        name=definition.name,
        longitude=longitude,
        house=house,
        ruler=ruler,
        minuend=minuend_name,
        subtrahend=subtrahend_name,
        addend=definition.addend,
        reversed_for_night=reversed_for_night,
        correction_applied=correction_applied,
    )


def varshaphal_sahams(
    ascendant: float,
    planets: dict[str, float],
    house_cusps: HouseCusps,
    is_day: bool,
) -> tuple[VarshaphalSaham, ...]:
    """Compute the documented Varshaphal Saham set for one annual chart."""

    derived: dict[str, VarshaphalSaham] = {}
    for definition in _SAHAM_DEFINITIONS:
        saham = _compute_saham(
            definition,
            ascendant=ascendant,
            planets=planets,
            house_cusps=house_cusps,
            is_day=is_day,
            derived=derived,
        )
        derived[saham.name] = saham
    return tuple(derived[name] for name in derived)


def build_varshaphal_chart(
    birth_jd: float,
    natal_latitude: float,
    natal_longitude: float,
    year: int,
    latitude: float,
    longitude: float,
    ayanamsa_system: str | UserDefinedAyanamsa = Ayanamsa.LAHIRI,
    house_system: str = HouseSystem.PLACIDUS,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    return_policy: TransitComputationPolicy | None = None,
    house_policy: HousePolicy | None = None,
) -> VarshaphalChart:
    """
    Build a structured Varshaphal annual-return vessel with Muntha and Sahams.

    The low-level annual chart remains available through
    ``moira.transits.varshaphal_chart()``. This higher layer adds the Tajika
    annual-return objects needed before aspect doctrine.
    """
    years_elapsed = year - calendar_datetime_from_jd(birth_jd).year
    if years_elapsed < 0:
        raise ValueError(
            f"Varshaphal year {year} precedes birth year for JD {birth_jd}"
        )

    jd_return = _varshaphal_jd(
        birth_jd,
        year,
        ayanamsa_system=ayanamsa_system,
        reader=reader,
        policy=return_policy,
    )
    chart = _varshaphal_chart(
        birth_jd,
        year,
        latitude,
        longitude,
        ayanamsa_system=ayanamsa_system,
        house_system=house_system,
        bodies=bodies,
        reader=reader,
        return_policy=return_policy,
        house_policy=house_policy,
    )

    return_ayan = ayanamsa(jd_return, ayanamsa_system)
    sidereal_houses = calculate_houses(
        jd_return,
        latitude,
        longitude,
        house_system,
        policy=house_policy,
        ayanamsa_offset=return_ayan,
    )
    sidereal_planets = {
        name: tropical_to_sidereal(planet.longitude, jd_return, system=ayanamsa_system)
        for name, planet in chart.planets.items()
    }

    natal_ayan = ayanamsa(birth_jd, ayanamsa_system)
    natal_sidereal_houses = calculate_houses(
        birth_jd,
        natal_latitude,
        natal_longitude,
        house_system,
        policy=house_policy,
        ayanamsa_offset=natal_ayan,
    )
    natal_sidereal_asc = natal_sidereal_houses.asc
    muntha_longitude = muntha(natal_sidereal_asc, years_elapsed)
    muntha_house = house_of(muntha_longitude, sidereal_houses)
    muntha_lord = _sign_lord(muntha_longitude)
    muntha_profile = muntha_condition_profile(
        muntha_longitude,
        muntha_house,
        muntha_lord,
        sidereal_planets,
        sidereal_houses,
    )
    sahams = varshaphal_sahams(
        sidereal_houses.asc,
        sidereal_planets,
        sidereal_houses,
        chart.is_day,
    )
    planet_speeds = {name: planet.speed for name, planet in chart.planets.items()}
    annual_aspects = tajika_aspects(sidereal_planets, planet_speeds=planet_speeds)
    annual_yogas = tajika_yogas(annual_aspects)
    return VarshaphalChart(
        birth_jd=birth_jd,
        return_year=year,
        years_elapsed=years_elapsed,
        jd_ut=jd_return,
        ayanamsa_system=ayanamsa_system,
        chart=chart,
        sidereal_houses=sidereal_houses,
        sidereal_planets=sidereal_planets,
        natal_sidereal_asc=natal_sidereal_asc,
        muntha_longitude=muntha_longitude,
        muntha_house=muntha_house,
        muntha_lord=muntha_lord,
        muntha_profile=muntha_profile,
        tajika_aspects=annual_aspects,
        tajika_yogas=annual_yogas,
        sahams=sahams,
    )

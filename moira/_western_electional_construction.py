"""Dorotheus Book V.7 construction election profile.

The profile composes the inherited V.2-V.6 and V.31 layers with every clause
in V.7.  It is source-complete but deliberately non-scored.  The lunar
equation sign is evaluated from an explicitly named IERS mean-longitude
product; the still-unresolved ecliptic-crossing region remains visible rather
than being replaced with a modern approximation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._western_electional_context import (
    DOROTHEUS_ROOTED_CONTEXT_V1,
    DorotheusMatter,
    DorotheusRootedContextEvaluation,
    DorotheusRootOutcomePattern,
    WesternElectionClass,
    evaluate_dorotheus_rooted_context,
)
from ._western_electional_dorotheus import (
    DOROTHEUS_MOON_CONDITION_V1,
    DorotheusMeasurement,
    DorotheusMoonConditionEvaluation,
    DorotheusMoonConditionStatus,
    evaluate_dorotheus_moon_condition,
)
from .chart import ChartContext, create_chart
from .constants import Body, SIGNS, sign_of
from .eclipse import EclipseCalculator
from .houses import HousePolicy, assign_house, describe_angularity
from .lunar_direction import (
    LunarEclipticDirectionWitness,
    lunar_ecliptic_direction_at,
)
from .obliquity import true_obliquity
from .planets import planet_at
from .spk_reader import SpkReader, get_reader
from .void_of_course import next_moon_connection


__all__ = [
    "DorotheusAscensionalClass",
    "DorotheusConstructionClauseRole",
    "DorotheusConstructionClauseState",
    "DorotheusConstructionStatus",
    "DorotheusSignNatureWitness",
    "DorotheusConstructionClauseWitness",
    "DorotheusConstructionPolicy",
    "DorotheusConstructionEvaluation",
    "DOROTHEUS_CONSTRUCTION_V1",
    "evaluate_dorotheus_construction",
    "dorotheus_construction_at",
]


_AUTHORITY_SIGN = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.2-5, printed pp. 231-233"
)
_AUTHORITY_CONSTRUCTION = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.7.1-3, printed p. 238"
)
_AUTHORITY_CALCULATION = (
    "Dykes edition glossary, Increasing/decreasing in calculation, printed p. 363"
)
_AUTHORITY_MEAN_LUNAR_LONGITUDE = (
    "IERS Conventions (2010), Chapter 5, section 5.7.2, equation 5.43: "
    "Delaunay F = L - Omega and mean lunar node Omega, evaluated in TT"
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
_CONVERTIBLE_SIGNS = frozenset(("Aries", "Cancer", "Libra", "Capricorn"))
_TWIN_SIGNS = frozenset(("Gemini", "Virgo", "Sagittarius", "Pisces"))
_DIURNAL_SIGNS = frozenset(("Aries", "Leo", "Sagittarius", "Gemini", "Libra", "Aquarius"))


class DorotheusAscensionalClass(str, Enum):
    """Vessel: Registry of dorotheus ascensional class values."""
    STRAIGHT = "straight"
    CROOKED = "crooked"
    NOT_EVALUABLE = "not_evaluable"


class DorotheusConstructionClauseRole(str, Enum):
    """Vessel: Registry of dorotheus construction clause role values."""
    FORTIFIER = "fortifier"
    GATE = "gate"


class DorotheusConstructionClauseState(str, Enum):
    """Vessel: Registry of dorotheus construction clause state values."""
    SATISFIED = "satisfied"
    CLEAR = "clear"
    TRIGGERED = "triggered"
    NOT_EVALUABLE = "not_evaluable"


class DorotheusConstructionStatus(str, Enum):
    """Vessel: Registry of dorotheus construction status values."""
    CLEAR = "clear_of_profile_impediments"
    TRIGGERED = "one_or_more_profile_impediments"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class DorotheusSignNatureWitness:
    """Vessel: Structured dorotheus sign nature witness data."""
    ascendant_longitude: float
    ascendant_sign: str
    geographic_latitude: float
    true_obliquity_degrees: float
    ascensional_arc_degrees: float | None
    ascensional_class: DorotheusAscensionalClass
    base_tempo: str
    configured_fortunes: tuple[str, ...]
    configured_infortunes: tuple[str, ...]
    modifier: str
    convertible: bool
    convertible_effect: str
    twin: bool
    twin_effect: str
    chart_sect: str
    ascendant_sect: str
    moon_sect: str
    sect_fit: bool
    source_reference: str = _AUTHORITY_SIGN

    def __post_init__(self) -> None:
        if not math.isfinite(self.ascendant_longitude):
            raise ValueError("Ascendant longitude must be finite")
        if self.ascendant_sign not in SIGNS:
            raise ValueError("Ascendant sign must be canonical")
        if self.ascensional_arc_degrees is not None and not math.isfinite(
            self.ascensional_arc_degrees
        ):
            raise ValueError("ascensional arc must be finite when supplied")


@dataclass(frozen=True, slots=True)
class DorotheusConstructionClauseWitness:
    """Vessel: Structured dorotheus construction clause witness data."""
    clause_id: str
    source_order: int
    role: DorotheusConstructionClauseRole
    state: DorotheusConstructionClauseState
    measurements: tuple[DorotheusMeasurement, ...]
    explanation: str
    source_reference: str = _AUTHORITY_CONSTRUCTION

    def __post_init__(self) -> None:
        if not 1 <= self.source_order <= 6:
            raise ValueError("construction clause order must be in [1, 6]")
        if not self.clause_id or not self.measurements or not self.explanation:
            raise ValueError("construction clause derivation must remain visible")
        if self.role is DorotheusConstructionClauseRole.GATE:
            if self.state is DorotheusConstructionClauseState.SATISFIED:
                raise ValueError("gate clauses cannot use the satisfied state")
        elif self.state is DorotheusConstructionClauseState.TRIGGERED:
            raise ValueError("fortifier clauses cannot use the triggered state")


@dataclass(frozen=True, slots=True)
class DorotheusConstructionPolicy:
    """Vessel: Structured dorotheus construction policy data."""
    profile_id: str = "dorotheus_construction_v1"
    profile_version: str = "1.1.0"
    ascensional_policy: str = "oblique_ascensional_arc_at_election_latitude"
    straight_threshold_degrees: float = 30.0
    configuration_policy: str = "whole_sign_configuration"
    strong_place_policy: str = "quadrant_angular_house"
    calculation_policy: str = "iers_2010_true_minus_mean_lunar_equation_sign"
    calculation_position_product: str = (
        "apparent_geocentric_longitude_mean_ecliptic_and_equinox_of_date"
    )
    north_crossing_policy: str = "source_indeterminate_with_exact_lunar_crossing_witness"

    def __post_init__(self) -> None:
        defaults = {
            name: field.default
            for name, field in DorotheusConstructionPolicy.__dataclass_fields__.items()
        }
        for name, value in defaults.items():
            if getattr(self, name) != value:
                raise ValueError(f"{name} is fixed for this admitted profile")


DOROTHEUS_CONSTRUCTION_V1 = DorotheusConstructionPolicy()


@dataclass(frozen=True, slots=True)
class DorotheusConstructionEvaluation:
    """Vessel: Structured dorotheus construction evaluation data."""
    jd_ut: float
    profile_id: str
    profile_version: str
    status: DorotheusConstructionStatus
    sign_nature: DorotheusSignNatureWitness
    moon_condition: DorotheusMoonConditionEvaluation
    rooted_context: DorotheusRootedContextEvaluation
    construction_clauses: tuple[DorotheusConstructionClauseWitness, ...]
    triggered_clause_ids: tuple[str, ...]
    not_evaluable_clause_ids: tuple[str, ...]
    reader_provenance: str
    authorities: tuple[str, ...] = (
        _AUTHORITY_SIGN,
        _AUTHORITY_CONSTRUCTION,
        _AUTHORITY_CALCULATION,
        _AUTHORITY_MEAN_LUNAR_LONGITUDE,
    )
    matter: str = "building_construction"
    election_class: str = "ephemeral"
    source_complete: bool = True
    complete_matter_profile: bool = True
    numerically_complete: bool = False
    complete_electional_judgement: bool = False
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"
    scoring: str = "not_provided"

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_ut):
            raise ValueError("jd_ut must be finite")
        if len(self.construction_clauses) != 6:
            raise ValueError("all six V.7 computational clauses must be preserved")
        if tuple(clause.source_order for clause in self.construction_clauses) != tuple(range(1, 7)):
            raise ValueError("construction clauses must remain in source-derived order")
        expected_triggered = tuple(
            clause.clause_id
            for clause in self.construction_clauses
            if clause.state is DorotheusConstructionClauseState.TRIGGERED
        )
        expected_unknown = tuple(
            clause.clause_id
            for clause in self.construction_clauses
            if clause.state is DorotheusConstructionClauseState.NOT_EVALUABLE
        )
        if self.triggered_clause_ids != expected_triggered:
            raise ValueError("triggered clause summary must derive from clauses")
        if self.not_evaluable_clause_ids != expected_unknown:
            raise ValueError("unknown clause summary must derive from clauses")
        if not self.source_complete:
            raise ValueError("the admitted profile must preserve every source layer")
        if not self.complete_matter_profile:
            raise ValueError("the admitted profile must preserve the complete V.7 matter layer")
        if self.numerically_complete:
            raise ValueError("unresolved source semantics prevent numerical completeness")
        if self.complete_electional_judgement:
            raise ValueError("an unresolved non-recommendatory profile is not a complete judgement")


def _measurement(
    name: str,
    value: float | str | bool | None,
    *,
    units: str | None = None,
    comparison: str | None = None,
    threshold: float | str | bool | None = None,
) -> DorotheusMeasurement:
    return DorotheusMeasurement(name, value, units, comparison, threshold)


def _iers_mean_lunar_longitude_degrees(jd_tt: float) -> float:
    """Return IERS 2010 mean lunar longitude ``L = F + Omega`` in TT.

    The two polynomials are the Delaunay argument of latitude ``F`` and mean
    ascending-node longitude ``Omega`` from IERS Conventions (2010), Chapter
    5, equation 5.43.  Keeping the formula here makes the electional witness
    independent of an optional validation library while retaining a direct
    ERFA/SOFA oracle in the tests.
    """

    if not math.isfinite(jd_tt):
        raise ValueError("jd_tt must be finite")
    t = (jd_tt - 2451545.0) / 36525.0
    arcseconds_to_degrees = 1.0 / 3600.0
    argument_of_latitude = (
        335779.526232
        + t * (
            1739527262.8478
            + t * (-12.7512 + t * (-0.001037 + t * 0.00000417))
        )
    ) * arcseconds_to_degrees
    ascending_node = (
        450160.398036
        + t * (
            -6962890.5431
            + t * (7.4722 + t * (0.007702 + t * -0.00005939))
        )
    ) * arcseconds_to_degrees
    return (argument_of_latitude + ascending_node) % 360.0


def _whole_sign_offset(a_sign: str, b_sign: str) -> int:
    return (SIGNS.index(b_sign) - SIGNS.index(a_sign)) % 12


def _configured(a_sign: str, b_sign: str) -> bool:
    return _whole_sign_offset(a_sign, b_sign) in _CONFIGURED_OFFSETS


def _oblique_ascension(
    longitude: float,
    latitude: float,
    obliquity: float,
) -> float | None:
    lon = math.radians(longitude)
    eps = math.radians(obliquity)
    ra = math.degrees(math.atan2(math.sin(lon) * math.cos(eps), math.cos(lon))) % 360.0
    declination = math.asin(math.sin(eps) * math.sin(lon))
    horizon_product = math.tan(math.radians(latitude)) * math.tan(declination)
    if abs(horizon_product) > 1.0:
        return None
    ascensional_difference = math.degrees(math.asin(horizon_product))
    return (ra - ascensional_difference) % 360.0


def _ascensional_arc(chart: ChartContext) -> tuple[float | None, float]:
    obliquity = true_obliquity(chart.jd_tt)
    ascendant_sign, _, _ = sign_of(chart.houses.asc)
    start = SIGNS.index(ascendant_sign) * 30.0
    end = (start + 30.0) % 360.0
    start_oa = _oblique_ascension(start, chart.latitude, obliquity)
    end_oa = _oblique_ascension(end, chart.latitude, obliquity)
    if start_oa is None or end_oa is None:
        return None, obliquity
    return (end_oa - start_oa) % 360.0, obliquity


def _sign_nature(
    chart: ChartContext,
    policy: DorotheusConstructionPolicy,
) -> DorotheusSignNatureWitness:
    houses = chart.houses
    if houses is None:
        raise ValueError("construction profile requires houses")
    asc_sign, _, _ = sign_of(houses.asc)
    arc, obliquity = _ascensional_arc(chart)
    if arc is None:
        ascensional_class = DorotheusAscensionalClass.NOT_EVALUABLE
        base_tempo = "not_evaluable_non_rising_sign_boundary"
    elif arc >= policy.straight_threshold_degrees:
        ascensional_class = DorotheusAscensionalClass.STRAIGHT
        base_tempo = "easy_and_fast"
    else:
        ascensional_class = DorotheusAscensionalClass.CROOKED
        base_tempo = "difficult_slow_and_toilsome"

    fortunes = tuple(
        body
        for body in (Body.JUPITER, Body.VENUS)
        if _configured(asc_sign, chart.planets[body].sign)
    )
    infortunes = tuple(
        body
        for body in (Body.MARS, Body.SATURN)
        if _configured(asc_sign, chart.planets[body].sign)
    )
    if fortunes and infortunes:
        modifier = "mixed_good_and_evil"
    elif ascensional_class is DorotheusAscensionalClass.CROOKED and fortunes:
        modifier = "fortune_removes_burden_and_assists_success"
    elif ascensional_class is DorotheusAscensionalClass.STRAIGHT and infortunes:
        modifier = "infortune_introduces_delay_unrest_and_toil"
    else:
        modifier = "no_source_named_modifier"

    moon = chart.planets[Body.MOON]
    chart_sect = "diurnal" if chart.is_day else "nocturnal"
    asc_sect = "diurnal" if asc_sign in _DIURNAL_SIGNS else "nocturnal"
    moon_sect = "diurnal" if moon.sign in _DIURNAL_SIGNS else "nocturnal"
    return DorotheusSignNatureWitness(
        ascendant_longitude=houses.asc,
        ascendant_sign=asc_sign,
        geographic_latitude=chart.latitude,
        true_obliquity_degrees=obliquity,
        ascensional_arc_degrees=arc,
        ascensional_class=ascensional_class,
        base_tempo=base_tempo,
        configured_fortunes=fortunes,
        configured_infortunes=infortunes,
        modifier=modifier,
        convertible=asc_sign in _CONVERTIBLE_SIGNS,
        convertible_effect=(
            "breaks_off_before_conclusion_and_must_be_begun_again"
            if asc_sign in _CONVERTIBLE_SIGNS
            else "not_convertible"
        ),
        twin=asc_sign in _TWIN_SIGNS,
        twin_effect=(
            "second_matter_enters_and_completes_before_first"
            if asc_sign in _TWIN_SIGNS
            else "not_twin"
        ),
        chart_sect=chart_sect,
        ascendant_sect=asc_sect,
        moon_sect=moon_sect,
        sect_fit=chart_sect == asc_sect == moon_sect,
    )


def _strong_configured_bodies(
    chart: ChartContext,
    bodies: tuple[str, ...],
) -> tuple[tuple[str, ...], bool]:
    houses = chart.houses
    moon = chart.planets[Body.MOON]
    if houses is None or not houses.is_quadrant_system:
        return (), False
    qualified: list[str] = []
    for body in bodies:
        planet = chart.planets[body]
        placement = assign_house(planet.longitude, houses)
        angular = describe_angularity(placement).category.value == "angular"
        if angular and _configured(moon.sign, planet.sign):
            qualified.append(body)
    return tuple(qualified), True


def _clause(
    clause_id: str,
    order: int,
    role: DorotheusConstructionClauseRole,
    state: DorotheusConstructionClauseState,
    measurements: tuple[DorotheusMeasurement, ...],
    explanation: str,
) -> DorotheusConstructionClauseWitness:
    return DorotheusConstructionClauseWitness(
        clause_id=clause_id,
        source_order=order,
        role=role,
        state=state,
        measurements=measurements,
        explanation=explanation,
    )


def evaluate_dorotheus_construction(
    chart: ChartContext,
    *,
    moon_condition: DorotheusMoonConditionEvaluation,
    rooted_context: DorotheusRootedContextEvaluation,
    moon_true_longitude_mean_ecliptic_degrees: float,
    lunar_direction: LunarEclipticDirectionWitness,
    reader_provenance: str,
    policy: DorotheusConstructionPolicy = DOROTHEUS_CONSTRUCTION_V1,
) -> DorotheusConstructionEvaluation:
    """Assemble every inherited and V.7 construction layer without scoring."""

    if not isinstance(policy, DorotheusConstructionPolicy):
        raise TypeError("policy must be a DorotheusConstructionPolicy")
    if chart.houses is None:
        raise ValueError("construction profile requires a house figure")
    if (
        not math.isfinite(moon_true_longitude_mean_ecliptic_degrees)
        or not 0.0 <= moon_true_longitude_mean_ecliptic_degrees < 360.0
    ):
        raise ValueError(
            "Moon true longitude in the mean ecliptic must be finite in [0, 360)"
        )
    if not isinstance(lunar_direction, LunarEclipticDirectionWitness):
        raise TypeError("lunar_direction must be a LunarEclipticDirectionWitness")
    if lunar_direction.jd_ut != chart.jd_ut:
        raise ValueError("lunar_direction must describe the chart instant")
    if moon_condition.jd_ut != chart.jd_ut or rooted_context.jd_ut != chart.jd_ut:
        raise ValueError("all inherited layers must describe the same election instant")
    if rooted_context.matter is not DorotheusMatter.LAND_AND_MANAGEMENT:
        raise ValueError("construction profile requires land_and_management context")

    moon = chart.planets[Body.MOON]
    sun = chart.planets[Body.SUN]
    mean_lunar_longitude = _iers_mean_lunar_longitude_degrees(chart.jd_tt)
    lunar_equation = (
        moon_true_longitude_mean_ecliptic_degrees
        - mean_lunar_longitude
        + 180.0
    ) % 360.0 - 180.0
    increasing_in_calculation = lunar_equation > 0.0
    elongation = (moon.longitude - sun.longitude) % 360.0
    increasing_glow = 0.0 < elongation < 180.0
    benefics, strong_places_evaluable = _strong_configured_bodies(
        chart, (Body.JUPITER, Body.VENUS)
    )
    saturns, _ = _strong_configured_bodies(chart, (Body.SATURN,))
    marses, _ = _strong_configured_bodies(chart, (Body.MARS,))

    clauses = (
        _clause(
            "moon_increasing_in_calculation",
            1,
            DorotheusConstructionClauseRole.FORTIFIER,
            (
                DorotheusConstructionClauseState.SATISFIED
                if increasing_in_calculation
                else DorotheusConstructionClauseState.CLEAR
            ),
            (
                _measurement(
                    "moon_true_longitude_mean_ecliptic",
                    moon_true_longitude_mean_ecliptic_degrees,
                    units="degrees",
                ),
                _measurement(
                    "moon_mean_longitude_iers_2010",
                    mean_lunar_longitude,
                    units="degrees",
                ),
                _measurement(
                    "lunar_equation",
                    lunar_equation,
                    units="degrees",
                    comparison=">",
                    threshold=0.0,
                ),
                _measurement(
                    "equation_direction",
                    (
                        "added"
                        if lunar_equation > 0.0
                        else "subtracted"
                        if lunar_equation < 0.0
                        else "zero"
                    ),
                ),
            ),
            "The glossary defines increase by adding the equation to mean position. The true Moon is compared with the IERS mean lunar longitude in a shared mean ecliptic-of-date frame; daily speed is not substituted.",
        ),
        _clause(
            "moon_increasing_in_glow",
            2,
            DorotheusConstructionClauseRole.FORTIFIER,
            (
                DorotheusConstructionClauseState.SATISFIED
                if increasing_glow
                else DorotheusConstructionClauseState.CLEAR
            ),
            (
                _measurement("signed_sun_moon_elongation", elongation, units="degrees", comparison="in", threshold="(0, 180)"),
                _measurement("increasing_in_glow", increasing_glow),
            ),
            "Increasing glow is the waxing half of the lunation, kept distinct from calculation.",
        ),
        _clause(
            "moon_on_ecliptic_rising_north",
            3,
            DorotheusConstructionClauseRole.FORTIFIER,
            DorotheusConstructionClauseState.NOT_EVALUABLE,
            (
                _measurement("moon_ecliptic_latitude", lunar_direction.latitude_deg, units="degrees"),
                _measurement("moon_latitude_rate", lunar_direction.latitude_rate_deg_per_day, units="degrees/day"),
                _measurement("hemisphere", lunar_direction.hemisphere.value),
                _measurement("latitude_motion", lunar_direction.motion.value),
                _measurement("previous_crossing_jd_ut", lunar_direction.previous_crossing.jd_ut, units="JD UT1"),
                _measurement("previous_crossing_direction", lunar_direction.previous_crossing.direction.value),
                _measurement("next_crossing_jd_ut", lunar_direction.next_crossing.jd_ut, units="JD UT1"),
                _measurement("next_crossing_direction", lunar_direction.next_crossing.direction.value),
                _measurement("nearest_crossing_relation", lunar_direction.nearest_crossing_relation.value),
                _measurement("nearest_crossing_hours_from_query", lunar_direction.nearest_crossing.hours_from_query, units="hours"),
                _measurement("required_missing_semantics", "source-owned interval before or after the exact ascending crossing"),
            ),
            "Northward latitude motion and adjacent exact roots are measured, but V.7 supplies no before/after interval for treating the Moon as on the ecliptic.",
        ),
        _clause(
            "benefic_configured_from_strong_place",
            4,
            DorotheusConstructionClauseRole.FORTIFIER,
            (
                DorotheusConstructionClauseState.NOT_EVALUABLE
                if not strong_places_evaluable
                else DorotheusConstructionClauseState.SATISFIED
                if benefics
                else DorotheusConstructionClauseState.CLEAR
            ),
            (
                _measurement("qualified_benefics", ",".join(benefics) or "none"),
                _measurement("required", "Jupiter or Venus configured to Moon from an angular house"),
            ),
            "With or looking is whole-sign configuration; strong place is an angular quadrant house.",
        ),
        _clause(
            "saturn_configured_from_strong_place",
            5,
            DorotheusConstructionClauseRole.GATE,
            (
                DorotheusConstructionClauseState.NOT_EVALUABLE
                if not strong_places_evaluable
                else DorotheusConstructionClauseState.TRIGGERED
                if saturns
                else DorotheusConstructionClauseState.CLEAR
            ),
            (_measurement("qualified_saturn", bool(saturns)),),
            "A configured angular Saturn preserves V.7's difficulty, disturbance, slowness, toil, and trouble warning.",
        ),
        _clause(
            "mars_configured_from_strong_place",
            6,
            DorotheusConstructionClauseRole.GATE,
            (
                DorotheusConstructionClauseState.NOT_EVALUABLE
                if not strong_places_evaluable
                else DorotheusConstructionClauseState.TRIGGERED
                if marses
                else DorotheusConstructionClauseState.CLEAR
            ),
            (_measurement("qualified_mars", bool(marses)),),
            "A configured angular Mars preserves V.7's conflagration or fire-harm warning.",
        ),
    )

    triggered = tuple(
        clause.clause_id
        for clause in clauses
        if clause.state is DorotheusConstructionClauseState.TRIGGERED
    )
    unknown = tuple(
        clause.clause_id
        for clause in clauses
        if clause.state is DorotheusConstructionClauseState.NOT_EVALUABLE
    )
    inherited_triggered = moon_condition.status is DorotheusMoonConditionStatus.TRIGGERED
    if triggered or inherited_triggered:
        status = DorotheusConstructionStatus.TRIGGERED
    elif (
        unknown
        or moon_condition.status is DorotheusMoonConditionStatus.INDETERMINATE
        or rooted_context.root_outcome.pattern is DorotheusRootOutcomePattern.NOT_EVALUABLE
        or any(item.condition.value == "indeterminate" for item in rooted_context.matter_significators)
    ):
        status = DorotheusConstructionStatus.INDETERMINATE
    else:
        status = DorotheusConstructionStatus.CLEAR

    return DorotheusConstructionEvaluation(
        jd_ut=chart.jd_ut,
        profile_id=policy.profile_id,
        profile_version=policy.profile_version,
        status=status,
        sign_nature=_sign_nature(chart, policy),
        moon_condition=moon_condition,
        rooted_context=rooted_context,
        construction_clauses=clauses,
        triggered_clause_ids=triggered,
        not_evaluable_clause_ids=unknown,
        reader_provenance=reader_provenance,
        election_class=rooted_context.election_class.value,
    )


def dorotheus_construction_at(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    election_class: WesternElectionClass = WesternElectionClass.EPHEMERAL,
    natal_jd_ut: float | None = None,
    natal_latitude: float | None = None,
    natal_longitude: float | None = None,
    natal_house_system: str | None = None,
    unavoidable_time_urgency: bool | None = None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    policy: DorotheusConstructionPolicy = DOROTHEUS_CONSTRUCTION_V1,
) -> DorotheusConstructionEvaluation:
    """Construct all astronomical inputs for one V.7 construction election."""

    election_class = WesternElectionClass(election_class)
    natal_values = (natal_jd_ut, natal_latitude, natal_longitude, natal_house_system)
    if election_class is WesternElectionClass.EPHEMERAL and any(
        value is not None for value in natal_values
    ):
        raise ValueError("ephemeral construction election rejects natal input")
    if election_class is WesternElectionClass.RADICAL and any(
        value is None for value in natal_values
    ):
        raise ValueError("radical construction election requires complete natal input")
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

    eclipse = EclipseCalculator(reader=resolved_reader).calculate_lunar_event_jd(
        jd_ut, kind="penumbral"
    )
    moon_eclipsed = eclipse.is_lunar_eclipse or eclipse.eclipse_type.magnitude_penumbra > 0.0
    reader_path = getattr(resolved_reader, "path", None)
    provenance = (
        str(reader_path)
        if reader_path is not None
        else f"{type(resolved_reader).__module__}.{type(resolved_reader).__qualname__}"
    )
    lunar_direction = lunar_ecliptic_direction_at(jd_ut, reader=resolved_reader)
    moon_condition = evaluate_dorotheus_moon_condition(
        chart,
        moon_eclipsed=moon_eclipsed,
        lunar_direction=lunar_direction,
        unavoidable_time_urgency=unavoidable_time_urgency,
        position_product=DOROTHEUS_MOON_CONDITION_V1.position_product,
        reader_provenance=provenance,
    )
    rooted_context = evaluate_dorotheus_rooted_context(
        chart,
        matter=DorotheusMatter.LAND_AND_MANAGEMENT,
        election_class=election_class,
        next_connection=next_moon_connection(jd_ut, reader=resolved_reader),
        natal_chart=natal_chart,
        reader_provenance=provenance,
        policy=DOROTHEUS_ROOTED_CONTEXT_V1,
    )
    moon_mean_ecliptic = planet_at(
        Body.MOON,
        jd_ut,
        reader=resolved_reader,
        nutation=False,
        jd_tt=chart.jd_tt,
    )
    return evaluate_dorotheus_construction(
        chart,
        moon_condition=moon_condition,
        rooted_context=rooted_context,
        moon_true_longitude_mean_ecliptic_degrees=moon_mean_ecliptic.longitude,
        lunar_direction=lunar_direction,
        reader_provenance=provenance,
        policy=policy,
    )

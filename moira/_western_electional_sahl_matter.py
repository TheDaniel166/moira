"""Source-ordered Sahl matter profiles, §§29-31, 36-40, and 43-55.

This module owns distinct matter layers in Sahl bin Bishr's *On
Elections*.  It deliberately does not turn them into a score or a generic
house-topic election.  Closed clauses compute from a supplied chart;
transmitted terms that remain genuinely open are retained as typed
``not_evaluable`` clauses with their observable alternatives.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .chart import ChartContext, create_chart
from .constants import Body, SIGNS, TRADITIONAL_MOIETY_ORBS, sign_of
from .dignities import EXALTATION
from .egyptian_bounds import EgyptianBoundsDoctrine, EgyptianBoundsPolicy, egyptian_bound_of
from .houses import HouseAngularity, HousePolicy, assign_house, describe_angularity
from .lots import calculate_lots
from .profections import DOMICILE_RULERS
from .spk_reader import SpkReader, get_reader
from .triplicity import triplicity_assignment_for
from .void_of_course import is_void_of_course

if TYPE_CHECKING:
    from .western_electional import (
        SahlBurntPathVariant,
        SahlEighthRuleVariant,
        SahlMoonConditionEvaluation,
        SahlMoonConditionPolicy,
    )


__all__ = [
    "SahlMatterProfileId",
    "SahlMatterClauseRole",
    "SahlMatterClauseState",
    "SahlMatterProfileStatus",
    "SahlMatterMeasurement",
    "SahlMatterClauseWitness",
    "SahlMatterProfilePolicy",
    "SahlMatterProfileEvaluation",
    "SAHL_BUILDING_V1",
    "SAHL_LENDING_V1",
    "SAHL_INVESTMENT_V1",
    "SAHL_PURCHASE_V1",
    "SAHL_SALE_V1",
    "SAHL_DEMOLITION_V1",
    "SAHL_LAND_V1",
    "SAHL_WELLS_AND_RIVERS_V1",
    "SAHL_PLANTING_V1",
    "SAHL_SOWING_V1",
    "SAHL_BUSINESS_PARTNERSHIP_V1",
    "evaluate_sahl_matter_profile",
    "sahl_matter_profile_at",
]


_AUTHORITY_BASE = (
    "Sahl bin Bishr, On Elections, Benjamin N. Dykes trans., Choices & "
    "Inceptions, Part III: Complete Elections"
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
_FORTUNES = (Body.JUPITER, Body.VENUS)
_MALEFICS = (Body.MARS, Body.SATURN)
_FIXED_SIGNS = frozenset(("Taurus", "Leo", "Scorpio", "Aquarius"))
_COMMON_SIGNS = frozenset(("Gemini", "Virgo", "Sagittarius", "Pisces"))
_MOVABLE_SIGNS = frozenset(("Aries", "Cancer", "Libra", "Capricorn"))
_WATERY_SIGNS = frozenset(("Cancer", "Scorpio", "Pisces"))
_AIRY_SIGNS = frozenset(("Gemini", "Libra", "Aquarius"))
_CONFIGURED_OFFSETS = frozenset((0, 2, 3, 4, 6, 8, 9, 10))
_ESTEEM_OFFSETS = frozenset((2, 4, 8, 10))
_HARD_OFFSETS = frozenset((0, 3, 6, 9))


class SahlMatterProfileId(str, Enum):
    """Vessel: Registry of sahl matter profile id values."""
    LENDING = "sahl_lending_v1"
    INVESTMENT = "sahl_investment_v1"
    PURCHASE = "sahl_purchase_v1"
    SALE = "sahl_sale_v1"
    BUILDING = "sahl_building_v1"
    DEMOLITION = "sahl_demolition_v1"
    LAND = "sahl_land_v1"
    WELLS_AND_RIVERS = "sahl_wells_and_rivers_v1"
    PLANTING = "sahl_planting_v1"
    SOWING = "sahl_sowing_v1"
    BUSINESS_PARTNERSHIP = "sahl_business_partnership_v1"


class SahlMatterClauseRole(str, Enum):
    """Vessel: Registry of sahl matter clause role values."""
    FORTIFIER = "fortifier"
    GATE = "gate"
    OUTCOME = "outcome"
    WITNESS = "witness"


class SahlMatterClauseState(str, Enum):
    """Vessel: Registry of sahl matter clause state values."""
    SATISFIED = "satisfied"
    CLEAR = "clear"
    TRIGGERED = "triggered"
    OBSERVED = "observed"
    NOT_EVALUABLE = "not_evaluable"


class SahlMatterProfileStatus(str, Enum):
    """Vessel: Registry of sahl matter profile status values."""
    CLEAR = "clear_of_explicit_profile_gates"
    TRIGGERED = "one_or_more_explicit_profile_gates"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class SahlMatterMeasurement:
    """Vessel: Structured sahl matter measurement data."""
    name: str
    value: float | str | bool | None
    units: str | None = None
    comparison: str | None = None
    threshold: float | str | bool | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("measurement name must be visible")
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("measurement values must be finite")


@dataclass(frozen=True, slots=True)
class SahlMatterClauseWitness:
    """Vessel: Structured sahl matter clause witness data."""
    clause_id: str
    source_order: int
    role: SahlMatterClauseRole
    state: SahlMatterClauseState
    measurements: tuple[SahlMatterMeasurement, ...]
    explanation: str
    source_reference: str
    policy_id: str

    def __post_init__(self) -> None:
        if not self.clause_id or self.source_order < 1 or not self.measurements:
            raise ValueError("clause identity, order, and evidence must remain visible")
        if not self.explanation or not self.source_reference or not self.policy_id:
            raise ValueError("clause policy, authority, and explanation must remain visible")
        if self.role is SahlMatterClauseRole.GATE:
            if self.state not in (
                SahlMatterClauseState.CLEAR,
                SahlMatterClauseState.TRIGGERED,
                SahlMatterClauseState.NOT_EVALUABLE,
            ):
                raise ValueError("gate clauses require clear, triggered, or not-evaluable state")
        elif self.state is SahlMatterClauseState.TRIGGERED:
            raise ValueError("only gate clauses may be triggered")


@dataclass(frozen=True, slots=True)
class SahlMatterProfilePolicy:
    """Vessel: Structured sahl matter profile policy data."""
    profile_id: SahlMatterProfileId
    profile_version: str = "1.0.0"
    aspect_policy: str = "whole_sign_configuration_and_sahl_moiety_join"
    number_policy: str = "source_text_indeterminate"
    eastern_ascending_policy: str = "source_parallels_indeterminate"
    circle_motion_policy: str = "source_parallels_indeterminate"
    cleansing_policy: str = "source_text_open_predicate"
    stake_policy: str = "clause_specific_visible_reference"

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, SahlMatterProfileId):
            raise TypeError("profile_id must be a SahlMatterProfileId")
        fixed = {
            "profile_version": "1.0.0",
            "aspect_policy": "whole_sign_configuration_and_sahl_moiety_join",
            "number_policy": "source_text_indeterminate",
            "eastern_ascending_policy": "source_parallels_indeterminate",
            "circle_motion_policy": "source_parallels_indeterminate",
            "cleansing_policy": "source_text_open_predicate",
            "stake_policy": "clause_specific_visible_reference",
        }
        for name, expected in fixed.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} is fixed for admitted v1 profiles")


SAHL_LENDING_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.LENDING)
SAHL_INVESTMENT_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.INVESTMENT)
SAHL_PURCHASE_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.PURCHASE)
SAHL_SALE_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.SALE)
SAHL_BUILDING_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.BUILDING)
SAHL_DEMOLITION_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.DEMOLITION)
SAHL_LAND_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.LAND)
SAHL_WELLS_AND_RIVERS_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.WELLS_AND_RIVERS)
SAHL_PLANTING_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.PLANTING)
SAHL_SOWING_V1 = SahlMatterProfilePolicy(SahlMatterProfileId.SOWING)
SAHL_BUSINESS_PARTNERSHIP_V1 = SahlMatterProfilePolicy(
    SahlMatterProfileId.BUSINESS_PARTNERSHIP
)
_POLICIES = {
    item.profile_id: item
    for item in (
        SAHL_LENDING_V1,
        SAHL_INVESTMENT_V1,
        SAHL_PURCHASE_V1,
        SAHL_SALE_V1,
        SAHL_BUILDING_V1,
        SAHL_DEMOLITION_V1,
        SAHL_LAND_V1,
        SAHL_WELLS_AND_RIVERS_V1,
        SAHL_PLANTING_V1,
        SAHL_SOWING_V1,
        SAHL_BUSINESS_PARTNERSHIP_V1,
    )
}
_SECTIONS = {
    SahlMatterProfileId.LENDING: "§§29-31, printed p. 103",
    SahlMatterProfileId.INVESTMENT: "§§36-38, printed pp. 104-105",
    SahlMatterProfileId.PURCHASE: "§39, printed p. 105",
    SahlMatterProfileId.SALE: "§40, printed p. 105",
    SahlMatterProfileId.BUILDING: "§§43-46, printed pp. 106-107",
    SahlMatterProfileId.DEMOLITION: "§47, printed p. 107",
    SahlMatterProfileId.LAND: "§§48-49, printed pp. 107-108",
    SahlMatterProfileId.WELLS_AND_RIVERS: "§50, printed pp. 108-109",
    SahlMatterProfileId.PLANTING: "§§51-53, printed p. 109",
    SahlMatterProfileId.SOWING: "§§54-55, printed pp. 109-110",
    SahlMatterProfileId.BUSINESS_PARTNERSHIP: "sections_32_to_35_printed_p_104",
}
_MATTERS = {
    SahlMatterProfileId.LENDING: "borrowing_and_lending",
    SahlMatterProfileId.INVESTMENT: "investing_money_for_profit",
    SahlMatterProfileId.PURCHASE: "purchasing_goods",
    SahlMatterProfileId.SALE: "selling_goods",
    SahlMatterProfileId.BUILDING: "building_a_house",
    SahlMatterProfileId.DEMOLITION: "destroying_a_house",
    SahlMatterProfileId.LAND: "buying_and_occupying_land",
    SahlMatterProfileId.WELLS_AND_RIVERS: "digging_wells_and_diverting_rivers",
    SahlMatterProfileId.PLANTING: "planting_trees",
    SahlMatterProfileId.SOWING: "sowing_seed",
    SahlMatterProfileId.BUSINESS_PARTNERSHIP: "business_partnership",
}


@dataclass(frozen=True, slots=True)
class SahlMatterProfileEvaluation:
    """Vessel: Structured sahl matter profile evaluation data."""
    jd_ut: float
    profile_id: SahlMatterProfileId
    profile_version: str
    matter: str
    status: SahlMatterProfileStatus
    moon_condition: "SahlMoonConditionEvaluation"
    clauses: tuple[SahlMatterClauseWitness, ...]
    triggered_clause_ids: tuple[str, ...]
    not_evaluable_clause_ids: tuple[str, ...]
    reader_provenance: str
    authorities: tuple[str, ...]
    source_complete: bool = True
    complete_matter_profile: bool = True
    numerically_complete: bool = False
    complete_electional_judgement: bool = False
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"
    scoring: str = "not_provided"

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_ut) or self.moon_condition.jd_ut != self.jd_ut:
            raise ValueError("profile and inherited Moon condition must share one finite instant")
        if self.matter != _MATTERS[self.profile_id]:
            raise ValueError("matter must derive from profile identity")
        if tuple(item.source_order for item in self.clauses) != tuple(range(1, len(self.clauses) + 1)):
            raise ValueError("clauses must remain in source order")
        triggered = tuple(
            item.clause_id for item in self.clauses
            if item.state is SahlMatterClauseState.TRIGGERED
        )
        unresolved = tuple(
            item.clause_id for item in self.clauses
            if item.state is SahlMatterClauseState.NOT_EVALUABLE
        )
        if triggered != self.triggered_clause_ids or unresolved != self.not_evaluable_clause_ids:
            raise ValueError("clause summaries must derive from visible clauses")
        expected_status = (
            SahlMatterProfileStatus.TRIGGERED if triggered
            else SahlMatterProfileStatus.INDETERMINATE if unresolved
            else SahlMatterProfileStatus.CLEAR
        )
        if self.status is not expected_status or self.numerically_complete != (not unresolved):
            raise ValueError("summary status and completeness must derive from clauses")
        if not self.source_complete or not self.complete_matter_profile:
            raise ValueError("an admitted profile must preserve its full source layer")
        if self.complete_electional_judgement:
            raise ValueError("a bounded matter profile is not a complete electional judgement")


def _m(name: str, value, *, units=None, comparison=None, threshold=None) -> SahlMatterMeasurement:
    return SahlMatterMeasurement(name, value, units, comparison, threshold)


def _source(profile_id: SahlMatterProfileId, detail: str = "") -> str:
    suffix = f"; {detail}" if detail else ""
    return f"{_AUTHORITY_BASE}, {_SECTIONS[profile_id]}{suffix}"


def _clause(profile_id, clause_id, order, role, state, measurements, explanation, policy_id, detail=""):
    return SahlMatterClauseWitness(
        clause_id=clause_id,
        source_order=order,
        role=role,
        state=state,
        measurements=measurements,
        explanation=explanation,
        source_reference=_source(profile_id, detail),
        policy_id=policy_id,
    )


def _offset(a_sign: str, b_sign: str) -> int:
    return (SIGNS.index(b_sign) - SIGNS.index(a_sign)) % 12


def _relation(a_sign: str, b_sign: str) -> str:
    offset = _offset(a_sign, b_sign)
    if offset == 0:
        return "conjunction"
    if offset in (2, 10):
        return "sextile"
    if offset in (3, 9):
        return "square"
    if offset in (4, 8):
        return "trine"
    if offset == 6:
        return "opposition"
    return "aversion"


def _configured(a_sign: str, b_sign: str) -> bool:
    return _offset(a_sign, b_sign) in _CONFIGURED_OFFSETS


def _joined(a, b) -> tuple[bool, float, float]:
    distance = abs((a.longitude - b.longitude + 180.0) % 360.0 - 180.0)
    threshold = (
        TRADITIONAL_MOIETY_ORBS[a.name]
        + TRADITIONAL_MOIETY_ORBS[b.name]
    ) / 2.0
    return distance <= threshold, distance, threshold


def _house(chart: ChartContext, body_name: str) -> int | None:
    if chart.houses is None or not chart.houses.is_quadrant_system:
        return None
    return assign_house(chart.planets[body_name].longitude, chart.houses).house


def _cadent(chart: ChartContext, body_name: str) -> bool | None:
    if chart.houses is None or not chart.houses.is_quadrant_system:
        return None
    placement = assign_house(chart.planets[body_name].longitude, chart.houses)
    return describe_angularity(placement).category is HouseAngularity.CADENT


def _whole_sign_place(chart: ChartContext, body_name: str) -> int:
    if chart.houses is None:
        raise ValueError("Sahl matter profiles require houses")
    asc_sign, _, _ = sign_of(chart.houses.asc)
    return _offset(asc_sign, chart.planets[body_name].sign) + 1


def _fortune(chart: ChartContext):
    if chart.houses is None:
        raise ValueError("Sahl matter profiles require houses")
    positions = {name: body.longitude for name, body in chart.planets.items()}
    cusps = {index + 1: value for index, value in enumerate(chart.houses.cusps)}
    return next(part for part in calculate_lots(positions, cusps, chart.is_day) if part.name == "Fortune")


def _light_waxing(chart: ChartContext) -> tuple[bool, float]:
    elongation = (chart.planets[Body.MOON].longitude - chart.planets[Body.SUN].longitude) % 360.0
    return 0.0 < elongation < 180.0, elongation


def _malefic_relations(chart: ChartContext, target: str) -> tuple[str, ...]:
    target_body = chart.planets[target]
    return tuple(
        f"{body}:{_relation(target_body.sign, chart.planets[body].sign)}"
        for body in _MALEFICS
        if _offset(target_body.sign, chart.planets[body].sign) in _HARD_OFFSETS
    )


def _solar_observations(chart: ChartContext, body_name: str) -> tuple[SahlMatterMeasurement, ...]:
    body = chart.planets[body_name]
    sun = chart.planets[Body.SUN]
    signed = (body.longitude - sun.longitude + 180.0) % 360.0 - 180.0
    return (
        _m("body", body_name),
        _m("signed_longitude_from_sun", signed, units="degrees"),
        _m("longitude_rate", body.speed, units="degrees/day"),
        _m("direct", body.speed >= 0.0),
        _m("ecliptic_latitude", body.latitude, units="degrees"),
        _m("quadrant_house", _house(chart, body_name)),
    )


def _conjunction_motion(chart: ChartContext, body_name: str) -> tuple[str, float, float]:
    moon = chart.planets[Body.MOON]
    body = chart.planets[body_name]
    signed = (moon.longitude - body.longitude + 180.0) % 360.0 - 180.0
    relative_rate = moon.speed - body.speed
    distance_rate = (
        math.copysign(1.0, signed) * relative_rate if signed != 0.0 else 0.0
    )
    motion = (
        "exact"
        if abs(signed) <= 1e-12
        else "applying"
        if distance_rate < 0.0
        else "separating"
        if distance_rate > 0.0
        else "stationary_relative"
    )
    return motion, abs(signed), distance_rate


def _joined_names(chart: ChartContext, target: str, bodies: tuple[str, ...]) -> tuple[str, ...]:
    target_body = chart.planets[target]
    return tuple(
        body
        for body in bodies
        if _joined(target_body, chart.planets[body])[0]
    )


def _sahl_rule_state(moon_condition, rule_id: str) -> str | None:
    if moon_condition is None:
        return None
    rule = next((item for item in moon_condition.rules if item.rule_id == rule_id), None)
    return None if rule is None else rule.state.value


def _lending(chart, profile_id, policy, moon_condition):
    moon = chart.planets[Body.MOON]
    mercury = chart.planets[Body.MERCURY]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    waxing, elongation = _light_waxing(chart)
    preferred_signs = frozenset(("Leo", "Pisces", "Scorpio", "Sagittarius", "Aquarius"))
    joined_fortunes = _joined_names(chart, Body.MOON, _FORTUNES)
    joined_mercury = _joined(moon, mercury)[0]
    joined_mars = _joined(moon, chart.planets[Body.MARS])[0]
    sun_motion, sun_distance, sun_distance_rate = _conjunction_motion(chart, Body.SUN)
    fortune_motion = tuple(
        f"{body}:{_conjunction_motion(chart, body)[0]}" for body in _FORTUNES
    )
    applying_fortunes = tuple(
        body for body in _FORTUNES if _conjunction_motion(chart, body)[0] == "applying"
    )
    mars_motion, mars_distance, mars_distance_rate = _conjunction_motion(chart, Body.MARS)
    under_rays = sun_distance <= 12.0
    burnt_path_state = _sahl_rule_state(moon_condition, "moon_cadent_or_burnt_path")
    first_degree_signs = frozenset(("Leo", "Gemini", "Sagittarius"))
    moon_degree = moon.longitude % 30.0
    first_degree_gate = moon.sign in first_degree_signs and moon_degree < 1.0
    ascending_sign_gate = asc_sign in first_degree_signs
    benefic_relations = tuple(
        f"{body}:moon={_relation(chart.planets[body].sign, moon.sign)};"
        f"ascendant={_relation(chart.planets[body].sign, asc_sign)}"
        for body in _FORTUNES
    )
    both_fortunes_configured = all(
        _configured(chart.planets[body].sign, moon.sign)
        or _configured(chart.planets[body].sign, asc_sign)
        for body in _FORTUNES
    )
    mercury_joined_malefics = _joined_names(chart, Body.MERCURY, _MALEFICS)
    mercury_square_malefics = tuple(
        body
        for body in _MALEFICS
        if _relation(mercury.sign, chart.planets[body].sign) == "square"
    )
    return (
        _clause(
            profile_id,
            "preferred_moon_and_deficient_fortunes",
            1,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("moon_sign", moon.sign),
                _m("preferred_sign", moon.sign in preferred_signs),
                _m("moon_defective_in_light", not waxing),
                _m("sun_moon_elongation", elongation, units="degrees"),
                _m("fortune_relations", ",".join(benefic_relations)),
                _m("both_fortunes_configured_to_moon_or_ascendant", both_fortunes_configured),
                _m("fortune_deficiency_predicate", None),
            ),
            "The Moon sign and waning light are closed. Sahl does not close what it means for both fortunes to be deficient, so the full §29a compound remains indeterminate.",
            policy.number_policy,
            "§29a and note 89",
        ),
        _clause(
            profile_id,
            "mercury_moon_and_fortune_protections",
            2,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("moon_joined_fortunes", ",".join(joined_fortunes) or "none"),
                _m("moon_joined_mercury", joined_mercury),
                _m("moon_hard_malefic_relations", ",".join(_malefic_relations(chart, Body.MOON)) or "none"),
                _m("mercury_bodily_joined_malefics", ",".join(mercury_joined_malefics) or "none"),
                _m("mercury_square_malefics", ",".join(mercury_square_malefics) or "none"),
                _m("jupiter_cadent", _cadent(chart, Body.JUPITER)),
                _m("venus_cadent", _cadent(chart, Body.VENUS)),
                _m("mercury_cleansed_of_mars", None),
            ),
            "Bodily joins, hard whole-sign relations, and quadrant cadence remain visible. 'Cleansed' and the exhaustive impediment predicate are not replaced with a generic dignity score.",
            policy.cleansing_policy,
            "§29b",
        ),
        _clause(
            profile_id,
            "moon_mars_or_saturn_consequence",
            3,
            SahlMatterClauseRole.GATE,
            (
                SahlMatterClauseState.TRIGGERED
                if joined_mars
                else SahlMatterClauseState.NOT_EVALUABLE
            ),
            (
                _m("moon_joined_mars", joined_mars),
                _m("moon_saturn_relation", _relation(moon.sign, chart.planets[Body.SATURN].sign)),
                _m("saturn_impediment_predicate", None),
            ),
            "A bodily Moon-Mars join triggers Sahl's labor, worry, harshness, and contention warning. The separate phrase 'impeded by Saturn' remains open, so absence of the Mars join cannot clear the compound.",
            policy.cleansing_policy,
            "§29c",
        ),
        _clause(
            profile_id,
            "concealed_lending_sequence",
            4,
            SahlMatterClauseRole.FORTIFIER,
            (
                SahlMatterClauseState.SATISFIED
                if under_rays and sun_motion == "separating" and applying_fortunes
                else SahlMatterClauseState.CLEAR
            ),
            (
                _m("moon_under_12_degree_rays", under_rays),
                _m("moon_sun_conjunction_motion", sun_motion),
                _m("moon_sun_distance_rate", sun_distance_rate, units="degrees/day"),
                _m("fortune_conjunction_motion", ",".join(fortune_motion)),
                _m("applying_fortunes", ",".join(applying_fortunes) or "none"),
            ),
            "§30a's sequence is evaluated as the Moon under its admitted 12-degree solar rays, separating from the Sun, and applying toward conjunction with Jupiter or Venus.",
            "instantaneous_conjunction_motion_with_sahl_solar_ray_orb",
            "§30a",
        ),
        _clause(
            profile_id,
            "emerging_toward_mars_publicity",
            5,
            SahlMatterClauseRole.WITNESS,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("moon_solar_distance", sun_distance, units="degrees"),
                _m("moon_sun_conjunction_motion", sun_motion),
                _m("moon_mars_conjunction_motion", mars_motion),
                _m("moon_mars_distance", mars_distance, units="degrees"),
                _m("moon_mars_distance_rate", mars_distance_rate, units="degrees/day"),
                _m("burned_up_exit_threshold", None),
            ),
            "The motion toward Mars is visible, but §30b supplies no boundary for 'exit out of being burned up'; the publicity testimony remains indeterminate.",
            "source_text_open_burned_up_exit",
            "§30b",
        ),
        _clause(
            profile_id,
            "node_or_burnt_path_warning",
            6,
            SahlMatterClauseRole.GATE,
            (
                SahlMatterClauseState.TRIGGERED
                if burnt_path_state == "triggered"
                else SahlMatterClauseState.NOT_EVALUABLE
            ),
            (
                _m("moon_ecliptic_latitude", moon.latitude, units="degrees"),
                _m("true_node_longitude", chart.nodes[Body.TRUE_NODE].longitude, units="degrees"),
                _m("node_or_tail_tolerance", None, units="degrees"),
                _m("inherited_burnt_path_rule_state", burnt_path_state),
            ),
            "The inherited explicit burnt-path variant can trigger this warning. The Latin parenthesis equating zero latitude with Head or Tail supplies no numerical node tolerance, so that branch remains unresolved.",
            "inherited_burnt_path_variant_and_open_node_tolerance",
            "§30c and note 92",
        ),
        _clause(
            profile_id,
            "first_degree_or_ascending_sign_loan_warning",
            7,
            SahlMatterClauseRole.GATE,
            (
                SahlMatterClauseState.TRIGGERED
                if first_degree_gate or ascending_sign_gate
                else SahlMatterClauseState.CLEAR
            ),
            (
                _m("moon_sign", moon.sign),
                _m("moon_degree_in_sign", moon_degree, units="degrees"),
                _m("moon_in_named_first_degree", first_degree_gate),
                _m("ascendant_sign", asc_sign),
                _m("named_sign_ascending", ascending_sign_gate),
            ),
            "§31's first-degree Moon condition and its separate whole-sign Ascendant condition remain distinct. Note 94's Dorothean comparison does not overwrite Sahl's transmitted Ascendant wording.",
            "first_tropical_degree_and_whole_sign_ascendant",
            "§31 and note 94",
        ),
    )


def _investment(chart, profile_id, policy, _moon_condition):
    moon = chart.planets[Body.MOON]
    mercury = chart.planets[Body.MERCURY]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    assets_sign = SIGNS[(SIGNS.index(asc_sign) + 1) % 12]
    trust_sign = SIGNS[(SIGNS.index(asc_sign) + 10) % 12]
    assets_lord = DOMICILE_RULERS[assets_sign]
    trust_lord = DOMICILE_RULERS[trust_sign]
    trust_cusp = chart.houses.cusps[10]
    joined_mercury, distance, threshold = _joined(moon, mercury)
    return (
        _clause(
            profile_id,
            "adapt_moon_mercury_assets_and_trust",
            1,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("moon_sign", moon.sign),
                _m("mercury_sign", mercury.sign),
                _m("assets_sign", assets_sign),
                _m("assets_lord", assets_lord),
                _m("trust_sign", trust_sign),
                _m("trust_sign_lord", trust_lord),
                _m("trust_house_cusp", trust_cusp, units="degrees"),
                _m("degree_lord_scheme", None),
            ),
            "The named Moon, Mercury, assets house, and trust house are visible. 'Adapt' and the lordship scheme for the degree of the eleventh are not closed by §§36-38.",
            "source_text_open_adaptation_and_degree_lord",
            "§36 and note 101",
        ),
        _clause(
            profile_id,
            "moon_mercury_join_and_mars_cadence",
            2,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("moon_joined_mercury", joined_mercury),
                _m("moon_mercury_distance", distance, units="degrees", threshold=threshold),
                _m("mars_relation_to_moon", _relation(chart.planets[Body.MARS].sign, moon.sign)),
                _m("mars_relation_to_mercury", _relation(chart.planets[Body.MARS].sign, mercury.sign)),
                _m("mars_cadent_from_each_predicate", None),
                _m("mercury_fit_and_purged_predicate", None),
            ),
            "The bodily Moon-Mercury join computes with canonical Moira moieties. 'Cadent from' each significator and Mercury's fit/purged state remain open predicates.",
            "canonical_moiety_join_with_open_cadence_and_purging",
            "§37a",
        ),
        _clause(
            profile_id,
            "retrograde_mercury_branch",
            3,
            SahlMatterClauseRole.WITNESS,
            (
                SahlMatterClauseState.NOT_EVALUABLE
                if mercury.retrograde
                else SahlMatterClauseState.OBSERVED
            ),
            (
                _m("mercury_retrograde", mercury.retrograde),
                _m("mercury_mars_relation", _relation(mercury.sign, chart.planets[Body.MARS].sign)),
                _m("mercury_venus_relation", _relation(mercury.sign, chart.planets[Body.VENUS].sign)),
                _m("mercury_trust_lord_relation", _relation(mercury.sign, chart.planets[trust_lord].sign)),
                _m("cadent_from_light_or_aspect_predicates", None if mercury.retrograde else "branch_not_applicable"),
            ),
            "When Mercury is direct, §37b's conditional branch is recorded as not applicable. When retrograde, its light/aspect cadence language remains unresolved.",
            policy.stake_policy,
            "§37b",
        ),
        _clause(
            profile_id,
            "trust_significators_and_mars_light",
            4,
            SahlMatterClauseRole.WITNESS,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("named_significators", f"Moon,Mercury,{trust_sign},{trust_lord}"),
                _m("mars_relation_to_moon", _relation(chart.planets[Body.MARS].sign, moon.sign)),
                _m("mars_relation_to_mercury", _relation(chart.planets[Body.MARS].sign, mercury.sign)),
                _m("mars_light_cadence_predicate", None),
            ),
            "§38 preserves the trust significators and repeats Mars/light cadence without defining a unique computational operation.",
            "source_text_open_cadent_from_light",
            "§38",
        ),
    )


def _purchase(chart, profile_id, policy, _moon_condition):
    moon = chart.planets[Body.MOON]
    fortune = _fortune(chart)
    waxing, elongation = _light_waxing(chart)
    joined_fortunes = _joined_names(chart, Body.MOON, _FORTUNES)
    fortune_distances = tuple(
        f"{body}:{abs((fortune.longitude - chart.planets[body].longitude + 180.0) % 360.0 - 180.0):.12g}"
        for body in _FORTUNES
    )
    tail = (chart.nodes[Body.TRUE_NODE].longitude + 180.0) % 360.0
    tail_distance = abs((moon.longitude - tail + 180.0) % 360.0 - 180.0)
    explicit_false = not waxing or not joined_fortunes
    return (
        _clause(
            profile_id,
            "fortune_fit_in_jupiter_house_and_joined_fortunes",
            1,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("fortune_longitude", fortune.longitude, units="degrees"),
                _m("fortune_sign", fortune.sign),
                _m("jupiter_domicile_sign", fortune.sign in ("Sagittarius", "Pisces")),
                _m("fortune_to_benefic_distances", ",".join(fortune_distances)),
                _m("fortune_fit_predicate", None),
                _m("lot_joining_orb_policy", None),
            ),
            "Fortune and Jupiter's domicile signs compute. A mathematical point has no planetary moiety in the source, and 'fit' remains open, so the full §39a compound is indeterminate.",
            "source_text_open_fortune_fitness_and_point_join_orb",
            "§39a",
        ),
        _clause(
            profile_id,
            "straight_ascension_light_number_and_fortunes",
            2,
            SahlMatterClauseRole.OUTCOME,
            (
                SahlMatterClauseState.CLEAR
                if explicit_false
                else SahlMatterClauseState.NOT_EVALUABLE
            ),
            (
                _m("moon_sign", moon.sign),
                _m("straight_ascension_predicate", None),
                _m("moon_increasing_in_light", waxing),
                _m("sun_moon_elongation", elongation, units="degrees"),
                _m("number_predicate", None),
                _m("moon_joined_fortunes", ",".join(joined_fortunes) or "none"),
                _m("source_outcome", "better_for_seller_new_owner_loses"),
            ),
            "The light and bodily-join conjuncts compute. Straight ascension and 'in number' remain source-open; an explicitly false closed conjunct can clear, but never fabricate, the compound outcome.",
            policy.number_policy,
            "§39b and note 105",
        ),
        _clause(
            profile_id,
            "mars_cadent_from_moon_and_mercury",
            3,
            SahlMatterClauseRole.GATE,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("mars_quadrant_house", _house(chart, Body.MARS)),
                _m("mars_relation_to_moon", _relation(chart.planets[Body.MARS].sign, moon.sign)),
                _m("mars_relation_to_mercury", _relation(chart.planets[Body.MARS].sign, chart.planets[Body.MERCURY].sign)),
                _m("cadent_from_each_predicate", None),
            ),
            "§39c names labor and contention, but 'cadent from' Moon and Mercury does not select a unique house or aspect operation.",
            "source_text_open_cadent_from_significators",
            "§39c",
        ),
        _clause(
            profile_id,
            "tail_cadent_from_moon",
            4,
            SahlMatterClauseRole.GATE,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("tail_longitude", tail, units="degrees"),
                _m("moon_tail_distance", tail_distance, units="degrees"),
                _m("moon_tail_sign_relation", _relation(moon.sign, sign_of(tail)[0])),
                _m("tail_cadent_from_moon_predicate", None),
            ),
            "The Tail's true-node-derived longitude is visible; §39d does not define the cadence operation or an orb.",
            "source_text_open_cadent_from_node",
            "§39d and note 106",
        ),
    )


def _sale(chart, profile_id, policy, _moon_condition):
    moon = chart.planets[Body.MOON]
    triplicity = triplicity_assignment_for(moon.sign, is_day_chart=chart.is_day)
    dignity = moon.sign in EXALTATION[Body.MOON] or triplicity.active_ruler == Body.MOON
    joined_fortunes = _joined_names(chart, Body.MOON, _FORTUNES)
    configured_malefics = tuple(
        body for body in _MALEFICS if _configured(moon.sign, chart.planets[body].sign)
    )
    joined_malefics = _joined_names(chart, Body.MOON, _MALEFICS)
    relation_satisfied = bool(configured_malefics) and not joined_malefics
    return (
        _clause(
            profile_id,
            "moon_in_exaltation_or_triplicity",
            1,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.SATISFIED if dignity else SahlMatterClauseState.CLEAR,
            (
                _m("moon_sign", moon.sign),
                _m("moon_in_exaltation", moon.sign in EXALTATION[Body.MOON]),
                _m("active_triplicity_ruler", triplicity.active_ruler),
                _m("moon_has_active_triplicity", triplicity.active_ruler == Body.MOON),
            ),
            "The transmitted exaltation-or-triplicity alternative is evaluated with Moira's explicit Dorothean triplicity doctrine.",
            "dorothean_triplicity_and_exaltation",
            "§40",
        ),
        _clause(
            profile_id,
            "moon_separated_from_fortunes",
            2,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("moon_joined_fortunes_now", ",".join(joined_fortunes) or "none"),
                _m("moon_jupiter_relation", _relation(moon.sign, chart.planets[Body.JUPITER].sign)),
                _m("moon_venus_relation", _relation(moon.sign, chart.planets[Body.VENUS].sign)),
                _m("separation_event_window", None),
            ),
            "Current joins and sign relations are visible, but §40 supplies no previous-event interval for identifying which fortune the Moon separated from.",
            "source_text_open_previous_separation_window",
            "§40",
        ),
        _clause(
            profile_id,
            "moon_configured_to_malefics_but_not_joined",
            3,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.SATISFIED if relation_satisfied else SahlMatterClauseState.CLEAR,
            (
                _m("configured_malefics", ",".join(configured_malefics) or "none"),
                _m("bodily_joined_malefics", ",".join(joined_malefics) or "none"),
                _m("compound_satisfied", relation_satisfied),
            ),
            "Dykes note 107 resolves the first relation as sign-based configuration, while the separate prohibition remains a degree-based bodily join under canonical Moira moieties.",
            policy.aspect_policy,
            "§40 and note 107",
        ),
    )


def _building(
    chart: ChartContext,
    profile_id: SahlMatterProfileId,
    policy: SahlMatterProfilePolicy,
    _moon_condition=None,
):
    moon = chart.planets[Body.MOON]
    moon_lord = DOMICILE_RULERS[moon.sign]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    asc_lord = DOMICILE_RULERS[asc_sign]
    fortune = _fortune(chart)
    mars = chart.planets[Body.MARS]
    venus = chart.planets[Body.VENUS]
    saturn = chart.planets[Body.SATURN]
    jupiter = chart.planets[Body.JUPITER]
    tail = (chart.nodes[Body.TRUE_NODE].longitude + 180.0) % 360.0
    waxing, elongation = _light_waxing(chart)
    moon_tail_distance = abs((moon.longitude - tail + 180.0) % 360.0 - 180.0)
    moon_saturn_joined, moon_saturn_distance, moon_saturn_orb = _joined(moon, saturn)
    venus_mars_relation = _relation(venus.sign, mars.sign)
    mars_moon_relation = _relation(mars.sign, moon.sign)
    saturn_house = _house(chart, Body.SATURN)
    saturn_whole_sign_place = _whole_sign_place(chart, Body.SATURN)
    saturn_quadrant_danger = saturn_house in (1, 4)
    saturn_whole_sign_danger = saturn_whole_sign_place in (1, 4)
    explicit_danger = moon_saturn_joined or moon_tail_distance <= 12.0
    angular_state = (
        SahlMatterClauseState.TRIGGERED
        if explicit_danger or (saturn_quadrant_danger and saturn_whole_sign_danger)
        else SahlMatterClauseState.NOT_EVALUABLE
        if saturn_quadrant_danger != saturn_whole_sign_danger
        else SahlMatterClauseState.CLEAR
    )
    clauses = [
        _clause(profile_id, "adapt_moon_and_lord", 1, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_sign", moon.sign), _m("moon_lord", moon_lord), _m("moon_lord_house", _house(chart, moon_lord))),
                "Sahl commands adaptation but §§43-46 do not close that term to an exclusive predicate.", "source_text_open_adaptation", "§43"),
        _clause(profile_id, "adapt_ascendant_and_lord", 2, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.NOT_EVALUABLE,
                (_m("ascendant_sign", asc_sign), _m("ascendant_lord", asc_lord), _m("ascendant_lord_house", _house(chart, asc_lord))),
                "The Ascendant pair is preserved without substituting a generic dignity score for 'adapt.'", "source_text_open_adaptation", "§43"),
        _clause(profile_id, "adapt_fortune_and_mercury", 3, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.NOT_EVALUABLE,
                (_m("fortune_longitude", fortune.longitude, units="degrees"), _m("fortune_sign", fortune.sign), _m("mercury_house", _house(chart, Body.MERCURY))),
                "Fortune and Mercury are computed, while the source's open adaptation command remains explicit.", "source_text_open_adaptation", "§43"),
        _clause(profile_id, "mars_cadent_from_named_significators", 4, SahlMatterClauseRole.GATE,
                SahlMatterClauseState.NOT_EVALUABLE,
                (_m("mars_house", _house(chart, Body.MARS)), _m("mars_cadent_in_quadrant_figure", _cadent(chart, Body.MARS)), _m("mars_sign", mars.sign)),
                "The phrase 'cadent from these significators' does not identify a single house or configuration operation.", "source_text_open_cadent_from_significators", "§44a"),
        _clause(profile_id, "venus_remedy_over_mars", 5, SahlMatterClauseRole.WITNESS,
                SahlMatterClauseState.OBSERVED,
                (_m("venus_mars_relation", venus_mars_relation), _m("qualifying_trine_or_sextile", venus_mars_relation in ("trine", "sextile")), _m("venus_house", _house(chart, Body.VENUS))),
                "The explicit Venus-Mars relation is visible; 'strong in her own place' is not collapsed into a score.", "whole_sign_relation_with_open_strength", "§44b"),
        _clause(profile_id, "saturn_cadent_from_venus_compound", 6, SahlMatterClauseRole.WITNESS,
                SahlMatterClauseState.NOT_EVALUABLE,
                (_m("saturn_house", saturn_house), _m("saturn_venus_relation", _relation(saturn.sign, venus.sign)), _m("saturn_mars_relation", _relation(saturn.sign, mars.sign)), _m("saturn_moon_relation", _relation(saturn.sign, moon.sign))),
                "Dykes note 110 says the Arabic and Latin appear to omit an operative conjunction; the compound cannot be closed honestly.", "dykes_note_110_missing_operative", "§44c and note 110"),
        _clause(profile_id, "moon_increased_in_light_and_number", 7, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_increasing_in_light", waxing), _m("sun_moon_elongation", elongation, units="degrees"), _m("moon_longitude_rate", moon.speed, units="degrees/day"), _m("number_predicate", None)),
                "Increasing light is measurable; 'in number' has no closed predicate in the held source and therefore keeps the compound indeterminate.", policy.number_policy, "§45a"),
        _clause(profile_id, "moon_joined_to_jupiter_by_square_or_opposition", 8, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if _relation(moon.sign, jupiter.sign) in ("square", "opposition") else SahlMatterClauseState.CLEAR,
                (_m("moon_jupiter_relation", _relation(moon.sign, jupiter.sign)), _m("preferred_relation", "square"), _m("lesser_relation", "opposition")),
                "The unusual source ranking—square better than opposition—is preserved without importing a generic aspect hierarchy.", policy.aspect_policy, "§45a"),
        _clause(profile_id, "saturn_tail_or_angular_saturn_danger", 9, SahlMatterClauseRole.GATE,
                angular_state,
                (_m("moon_saturn_joined", moon_saturn_joined), _m("moon_saturn_distance", moon_saturn_distance, units="degrees", threshold=moon_saturn_orb), _m("moon_tail_distance", moon_tail_distance, units="degrees", comparison="<=", threshold=12.0), _m("saturn_quadrant_house", saturn_house), _m("saturn_whole_sign_place", saturn_whole_sign_place)),
                "The bodily and node conditions are explicit. Saturn's Ascendant/fourth placement triggers only when whole-sign and quadrant readings agree; disagreement preserves the stakes ambiguity.", policy.stake_policy, "§45b-c"),
        _clause(profile_id, "mars_aspecting_with_ascending_circle", 10, SahlMatterClauseRole.GATE,
                SahlMatterClauseState.NOT_EVALUABLE if mars_moon_relation != "aversion" else SahlMatterClauseState.CLEAR,
                (_m("mars_moon_relation", mars_moon_relation), *_solar_observations(chart, Body.MARS)),
                "Dykes notes 112-114 preserve a Moon/Mars pronoun ambiguity and incompatible meanings of ascending in the apogee/short circle. A configured Mars exposes the unresolved gate but does not fabricate its second condition.", policy.circle_motion_policy, "§45d and notes 112-114"),
        _clause(profile_id, "lords_aspect_and_are_cleansed", 11, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_lord_relation_to_moon", _relation(chart.planets[moon_lord].sign, moon.sign)), _m("asc_lord_relation_to_asc", _relation(chart.planets[asc_lord].sign, asc_sign)), _m("moon_lord_malefic_relations", ",".join(_malefic_relations(chart, moon_lord)) or "none"), _m("asc_lord_malefic_relations", ",".join(_malefic_relations(chart, asc_lord)) or "none")),
                "The required lord configurations are measured, but 'cleansed of the bad ones' is not closed to these observations alone.", policy.cleansing_policy, "§46"),
    ]
    return tuple(clauses)


def _demolition(chart, profile_id, policy, _moon_condition=None):
    moon = chart.planets[Body.MOON]
    moon_lord = DOMICILE_RULERS[moon.sign]
    fortune_relations = tuple((body, _relation(moon.sign, chart.planets[body].sign)) for body in _FORTUNES)
    malefic_relations = _malefic_relations(chart, Body.MOON)
    lord_relation = _relation(moon.sign, chart.planets[moon_lord].sign)
    return (
        _clause(profile_id, "moon_descending_in_own_circle", 1, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_latitude", moon.latitude, units="degrees"), _m("moon_longitude_rate", moon.speed, units="degrees/day"), _m("moon_house", _house(chart, Body.MOON))),
                "The held passage does not decide whether the Moon's own circle means latitude, local hemisphere, or another inherited circle model.", policy.circle_motion_policy, "§47a"),
        _clause(profile_id, "moon_separated_from_malefics", 2, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("instantaneous_hard_relations", ",".join(malefic_relations) or "none"), _m("moon_speed", moon.speed, units="degrees/day")),
                "The text does not define the eligible aspects, orb, or previous-event interval for 'separated from.'", "source_text_open_separation_window", "§47a"),
        _clause(profile_id, "moon_joined_to_fortunes", 3, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if any(rel == "conjunction" for _, rel in fortune_relations) else SahlMatterClauseState.CLEAR,
                tuple(_m(f"moon_{body.lower()}_relation", rel) for body, rel in fortune_relations),
                "A bodily whole-sign joining to either named fortune is kept separate from the unresolved eastern/ascending condition.", policy.aspect_policy, "§47a"),
        _clause(profile_id, "fortune_eastern_or_ascending_direct", 4, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                tuple(item for body in _FORTUNES for item in _solar_observations(chart, body)),
                "Directness is observed, but eastern and ascending retain multiple source-plausible meanings.", policy.eastern_ascending_policy, "§47a"),
        _clause(profile_id, "moon_to_own_lord_destruction_tempo", 5, SahlMatterClauseRole.OUTCOME, SahlMatterClauseState.OBSERVED,
                (_m("moon_lord", moon_lord), _m("relation", lord_relation), _m("source_outcome", "easier" if lord_relation in ("trine", "sextile") else "more_difficult" if lord_relation in ("square", "opposition") else "not_stated")),
                "The source's easier-versus-more-difficult testimony is reported, not scored or recommended.", policy.aspect_policy, "§47b"),
    )


def _land(chart, profile_id, policy, _moon_condition=None):
    moon = chart.planets[Body.MOON]
    saturn = chart.planets[Body.SATURN]
    jupiter = chart.planets[Body.JUPITER]
    venus = chart.planets[Body.VENUS]
    mars = chart.planets[Body.MARS]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    asc_lord = DOMICILE_RULERS[asc_sign]
    triplicity = triplicity_assignment_for(saturn.sign, is_day_chart=chart.is_day)
    bound = egyptian_bound_of(saturn.longitude, policy=EgyptianBoundsPolicy(EgyptianBoundsDoctrine.EGYPTIAN))
    dignified = saturn.sign in EXALTATION[Body.SATURN] or triplicity.active_ruler == Body.SATURN or bound.ruler == Body.SATURN
    saturn_jupiter_relation = _relation(saturn.sign, jupiter.sign)
    stake_from_saturn = _offset(saturn.sign, jupiter.sign) in (0, 3, 6, 9)
    waxing, elongation = _light_waxing(chart)
    moon_jupiter = _relation(moon.sign, jupiter.sign)
    moon_saturn = _relation(moon.sign, saturn.sign)
    moon_venus = _relation(moon.sign, venus.sign)
    moon_quadrant_mc = _house(chart, Body.MOON) == 10
    moon_whole_sign_mc = _whole_sign_place(chart, Body.MOON) == 10
    moon_exalted = moon.sign in EXALTATION[Body.MOON]
    moon_mc_state = (
        SahlMatterClauseState.SATISFIED
        if moon_exalted or (moon_quadrant_mc and moon_whole_sign_mc)
        else SahlMatterClauseState.NOT_EVALUABLE
        if moon_quadrant_mc != moon_whole_sign_mc
        else SahlMatterClauseState.CLEAR
    )
    return (
        _clause(profile_id, "saturn_exaltation_triplicity_or_bound", 1, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if dignified else SahlMatterClauseState.CLEAR,
                (_m("saturn_sign", saturn.sign), _m("in_exaltation", saturn.sign in EXALTATION[Body.SATURN]), _m("active_triplicity_ruler", triplicity.active_ruler), _m("bound_ruler", bound.ruler)),
                "The three transmitted alternatives remain disjunctive and use Moira's explicit Dorothean triplicity and Egyptian-bound doctrines.", "dorothean_triplicity_and_egyptian_bounds", "§48"),
        _clause(profile_id, "jupiter_aspecting_saturn_from_stake_or_trine", 2, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if stake_from_saturn or saturn_jupiter_relation == "trine" else SahlMatterClauseState.CLEAR,
                (_m("jupiter_saturn_relation", saturn_jupiter_relation), _m("whole_sign_stake_from_saturn", stake_from_saturn)),
                "Dykes note 118 identifies the stake as a whole-sign angle from Saturn, not automatically from the Ascendant.", "dykes_note_118_whole_sign_stake_from_saturn", "§48 and note 118"),
        _clause(profile_id, "mars_cadent_from_saturn_and_jupiter", 3, SahlMatterClauseRole.GATE, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("mars_house", _house(chart, Body.MARS)), _m("mars_cadent_in_quadrant_figure", _cadent(chart, Body.MARS)), _m("mars_saturn_relation", _relation(mars.sign, saturn.sign)), _m("mars_jupiter_relation", _relation(mars.sign, jupiter.sign))),
                "'Cadent from them' does not identify one house or configuration operation, so observed alternatives cannot close the gate.", "source_text_open_cadent_from_planets", "§48"),
        _clause(profile_id, "moon_at_beginning_of_lunar_month", 4, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("sun_moon_elongation", elongation, units="degrees"), _m("moon_increasing_in_light", waxing), _m("numeric_beginning_interval", None)),
                "The source names the beginning of the lunar month but supplies no admissible numeric endpoint.", "source_text_no_lunar_month_endpoint", "§49a"),
        _clause(profile_id, "moon_aspects_saturn_from_esteem", 5, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if _offset(moon.sign, saturn.sign) in _ESTEEM_OFFSETS else SahlMatterClauseState.CLEAR,
                (_m("moon_saturn_relation", moon_saturn),),
                "Esteem is preserved as Sahl's trine-or-sextile relation.", policy.aspect_policy, "§49a"),
        _clause(profile_id, "moon_increased_in_number", 6, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_longitude_rate", moon.speed, units="degrees/day"), _m("number_predicate", None)),
                "The held source does not close 'increased in number' to speed or another numeric lunar quantity.", policy.number_policy, "§49a"),
        _clause(profile_id, "moon_aspect_jupiter_with_venus_fallback", 7, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if _configured(moon.sign, jupiter.sign) or (not _configured(saturn.sign, jupiter.sign) and _configured(moon.sign, venus.sign)) else SahlMatterClauseState.CLEAR,
                (_m("moon_jupiter_relation", moon_jupiter), _m("jupiter_saturn_configured", _configured(saturn.sign, jupiter.sign)), _m("moon_venus_relation", moon_venus)),
                "Venus is admitted only under the source's explicit no-Jupiter-Saturn fallback.", policy.aspect_policy, "§49a-b"),
        _clause(profile_id, "make_watery_signs_fortunate", 8, SahlMatterClauseRole.WITNESS, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_sign", moon.sign), _m("moon_sign_element", "water" if moon.sign in _WATERY_SIGNS else "air" if moon.sign in _AIRY_SIGNS else "other"), _m("named_fortunate_sign_target", None)),
                "The passage ranks watery above airy signs but does not identify one chart point whose sign must be made fortunate.", "source_text_open_sign_target", "§49b"),
        _clause(profile_id, "moon_exaltation_or_midheaven", 9, SahlMatterClauseRole.FORTIFIER,
                moon_mc_state,
                (_m("moon_sign", moon.sign), _m("moon_in_exaltation", moon_exalted), _m("moon_quadrant_house", _house(chart, Body.MOON)), _m("moon_whole_sign_place", _whole_sign_place(chart, Body.MOON))),
                "Exaltation is closed. Midheaven placement is accepted when whole-sign and quadrant readings agree; disagreement remains visible rather than silently selecting a stakes doctrine.", policy.stake_policy, "§49c"),
        _clause(profile_id, "ascendant_lord_aspects_moon", 10, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if _configured(chart.planets[asc_lord].sign, moon.sign) else SahlMatterClauseState.CLEAR,
                (_m("ascendant_lord", asc_lord), _m("relation_to_moon", _relation(chart.planets[asc_lord].sign, moon.sign))),
                "The lord and its whole-sign configuration are explicit.", policy.aspect_policy, "§49c"),
        _clause(profile_id, "moon_and_ascendant_cleansed", 11, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_malefic_relations", ",".join(_malefic_relations(chart, Body.MOON)) or "none"), _m("ascendant_sign", asc_sign), _m("malefics_configured_to_ascendant", ",".join(body for body in _MALEFICS if _offset(asc_sign, chart.planets[body].sign) in _HARD_OFFSETS) or "none")),
                "Observed malefic relations do not exhaust the source's combined 'cleansed of bad ones and defects' predicate.", policy.cleansing_policy, "§49c"),
    )


def _wells(chart, profile_id, policy, _moon_condition=None):
    moon = chart.planets[Body.MOON]
    saturn = chart.planets[Body.SATURN]
    moon_house = _house(chart, Body.MOON)
    saturn_house = _house(chart, Body.SATURN)
    malefics_quadrant_mc = tuple(body for body in _MALEFICS if _house(chart, body) == 10)
    malefics_whole_sign_mc = tuple(body for body in _MALEFICS if _whole_sign_place(chart, body) == 10)
    mc_state = (
        SahlMatterClauseState.TRIGGERED
        if malefics_quadrant_mc and malefics_quadrant_mc == malefics_whole_sign_mc
        else SahlMatterClauseState.CLEAR
        if not malefics_quadrant_mc and not malefics_whole_sign_mc
        else SahlMatterClauseState.NOT_EVALUABLE
    )
    joined = []
    for body in _FORTUNES:
        bodily, distance, threshold = _joined(moon, chart.planets[body])
        if bodily:
            joined.append(body)
    return (
        _clause(profile_id, "saturn_eastern", 1, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                _solar_observations(chart, Body.SATURN),
                "The source does not close easternness to solar orientalness, hemisphere, or another inherited condition.", policy.eastern_ascending_policy, "§50a"),
        _clause(profile_id, "moon_under_earth_in_third_or_fifth", 2, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if moon_house in (3, 5) else SahlMatterClauseState.CLEAR,
                (_m("moon_house", moon_house), _m("required_houses", "3 or 5"), _m("effective_house_system", chart.houses.effective_system)),
                "The explicit houses are evaluated in the caller-declared effective quadrant figure.", "quadrant_houses_3_or_5", "§50a"),
        _clause(profile_id, "moon_free_fortunate_and_received", 3, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_malefic_relations", ",".join(_malefic_relations(chart, Body.MOON)) or "none"), _m("moon_domicile_lord", DOMICILE_RULERS[moon.sign]), _m("moon_lord_relation", _relation(moon.sign, chart.planets[DOMICILE_RULERS[moon.sign]].sign))),
                "The source does not name the receiver or give closed predicates for made fortunate and free; no generic dignity total substitutes for them.", "source_text_open_fortunate_received", "§50a"),
        _clause(profile_id, "malefic_in_midheaven", 4, SahlMatterClauseRole.GATE,
                mc_state,
                (_m("malefics_in_quadrant_tenth", ",".join(malefics_quadrant_mc) or "none"), _m("malefics_in_tenth_whole_sign_place", ",".join(malefics_whole_sign_mc) or "none")),
                "The collapse/drying gate triggers when whole-sign and quadrant Midheaven readings agree; disagreement preserves the stakes ambiguity.", policy.stake_policy, "§50b"),
        _clause(profile_id, "saturn_in_eleventh", 5, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if _whole_sign_place(chart, Body.SATURN) == 11 else SahlMatterClauseState.CLEAR,
                (_m("saturn_whole_sign_place_from_ascendant", _whole_sign_place(chart, Body.SATURN)), _m("saturn_quadrant_house", saturn_house)),
                "The text explicitly says eleventh from the Ascendant; v1 uses the visible whole-sign place and also reports the quadrant house.", "whole_sign_eleventh_from_ascendant", "§50c"),
        _clause(profile_id, "moon_joined_to_fortune_in_fixed_sign", 6, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if joined and moon.sign in _FIXED_SIGNS else SahlMatterClauseState.CLEAR,
                (_m("moon_sign", moon.sign), _m("fixed_sign", moon.sign in _FIXED_SIGNS), _m("joined_fortunes", ",".join(joined) or "none")),
                "The Arabic-moiety bodily join and fixed sign are both required.", "sahl_moiety_join_and_fixed_sign", "§50c"),
        _clause(profile_id, "fortune_ascending_in_circle", 7, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                tuple(item for body in _FORTUNES for item in _solar_observations(chart, body)),
                "Dykes note 121 records Crofts's different reading, 'joined in a fixed, ascending sign'; v1 preserves the conflict.", policy.circle_motion_policy, "§50c and note 121"),
        _clause(profile_id, "jupiter_preferred_or_midheaven_fallback", 8, SahlMatterClauseRole.OUTCOME, SahlMatterClauseState.OBSERVED,
                (_m("moon_joined_jupiter", Body.JUPITER in joined), _m("jupiter_whole_sign_place", _whole_sign_place(chart, Body.JUPITER)), _m("jupiter_quadrant_house", _house(chart, Body.JUPITER)), _m("fallback_jupiter_in_midheaven_both_readings", _whole_sign_place(chart, Body.JUPITER) == 10 and _house(chart, Body.JUPITER) == 10)),
                "Jupiter's preferred and fallback placements are visible without turning lasting/stable testimony into a score.", "source_ordered_jupiter_preference", "§50d"),
    )


def _planting(chart, profile_id, policy, _moon_condition=None):
    moon = chart.planets[Body.MOON]
    moon_lord = DOMICILE_RULERS[moon.sign]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    asc_lord = DOMICILE_RULERS[asc_sign]
    moon_lord_relation = _relation(chart.planets[moon_lord].sign, moon.sign)
    asc_lord_relation = _relation(chart.planets[asc_lord].sign, asc_sign)
    return (
        _clause(profile_id, "moon_in_fixed_sign", 1, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if moon.sign in _FIXED_SIGNS else SahlMatterClauseState.CLEAR,
                (_m("moon_sign", moon.sign), _m("fixed_sign", moon.sign in _FIXED_SIGNS)),
                "The fixed-sign class is explicit.", "classical_quadruplicity", "§51"),
        _clause(profile_id, "moon_lord_aspects_from_watery_sign", 2, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if _configured(chart.planets[moon_lord].sign, moon.sign) and chart.planets[moon_lord].sign in _WATERY_SIGNS else SahlMatterClauseState.CLEAR,
                (_m("moon_lord", moon_lord), _m("moon_lord_sign", chart.planets[moon_lord].sign), _m("relation_to_moon", moon_lord_relation)),
                "Both the watery sign and configuration are required.", policy.aspect_policy, "§51"),
        _clause(profile_id, "ascendant_fixed_or_common", 3, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if asc_sign in _FIXED_SIGNS | _COMMON_SIGNS else SahlMatterClauseState.CLEAR,
                (_m("ascendant_sign", asc_sign), _m("fixed_or_common", asc_sign in _FIXED_SIGNS | _COMMON_SIGNS)),
                "The two admitted quadruplicities are explicit.", "classical_quadruplicity", "§52a"),
        _clause(profile_id, "ascendant_lord_ascending_and_eastern", 4, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                _solar_observations(chart, asc_lord),
                "Dykes note 123 explicitly leaves the sense uncertain: al-Khayyat names latitude, al-Imrani says ascending eastern, and solar rising-before remains possible.", policy.eastern_ascending_policy, "§52a and note 123"),
        _clause(profile_id, "ascending_eastern_tempo_matrix", 5, SahlMatterClauseRole.OUTCOME, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("ascendant_lord", asc_lord), *_solar_observations(chart, asc_lord)),
                "The four sprouting/fruit tempos cannot be selected until eastern and ascending are source-settled; all alternatives remain in the source record.", policy.eastern_ascending_policy, "§52b-d"),
        _clause(profile_id, "lords_aspect_moon_and_ascendant", 6, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if _configured(chart.planets[moon_lord].sign, moon.sign) and _configured(chart.planets[asc_lord].sign, asc_sign) else SahlMatterClauseState.CLEAR,
                (_m("moon_lord_relation", moon_lord_relation), _m("ascendant_lord_relation", asc_lord_relation)),
                "Dykes note 124 resolves which lord aspects which point.", policy.aspect_policy, "§53 and note 124"),
        _clause(profile_id, "lords_free_from_malefics_and_burning", 7, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_lord_malefic_relations", ",".join(_malefic_relations(chart, moon_lord)) or "none"), _m("asc_lord_malefic_relations", ",".join(_malefic_relations(chart, asc_lord)) or "none"), _m("moon_lord_solar_distance", abs((chart.planets[moon_lord].longitude - chart.planets[Body.SUN].longitude + 180.0) % 360.0 - 180.0), units="degrees"), _m("asc_lord_solar_distance", abs((chart.planets[asc_lord].longitude - chart.planets[Body.SUN].longitude + 180.0) % 360.0 - 180.0), units="degrees")),
                "The passage supplies neither an exhaustive malefic relation set nor a numeric burning threshold for these lords.", policy.cleansing_policy, "§53"),
    )


def _sowing(chart, profile_id, policy, _moon_condition=None):
    moon = chart.planets[Body.MOON]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    asc_lord = DOMICILE_RULERS[asc_sign]
    asc_lord_body = chart.planets[asc_lord]
    asc_lord_dispositor = DOMICILE_RULERS[asc_lord_body.sign]
    disposer_relation = _relation(asc_lord_body.sign, chart.planets[asc_lord_dispositor].sign)
    malefics = _malefic_relations(chart, asc_lord)
    waxing, elongation = _light_waxing(chart)
    solar_distance = abs((moon.longitude - chart.planets[Body.SUN].longitude + 180.0) % 360.0 - 180.0)
    under_rays = solar_distance <= 12.0
    return (
        _clause(profile_id, "ascendant_common", 1, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if asc_sign in _COMMON_SIGNS else SahlMatterClauseState.CLEAR,
                (_m("ascendant_sign", asc_sign), _m("common_sign", asc_sign in _COMMON_SIGNS)),
                "The common-sign requirement is explicit.", "classical_quadruplicity", "§54"),
        _clause(profile_id, "ascendant_lord_in_movable_sign", 2, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if asc_lord_body.sign in _MOVABLE_SIGNS else SahlMatterClauseState.CLEAR,
                (_m("ascendant_lord", asc_lord), _m("ascendant_lord_sign", asc_lord_body.sign), _m("movable_sign", asc_lord_body.sign in _MOVABLE_SIGNS)),
                "The movable-sign requirement is explicit.", "classical_quadruplicity", "§54"),
        _clause(profile_id, "ascendant_lord_aspects_its_dispositor", 3, SahlMatterClauseRole.FORTIFIER,
                SahlMatterClauseState.SATISFIED if _configured(asc_lord_body.sign, chart.planets[asc_lord_dispositor].sign) else SahlMatterClauseState.CLEAR,
                (_m("ascendant_lord_dispositor", asc_lord_dispositor), _m("relation", disposer_relation)),
                "Dykes note 126 identifies 'itself' as the Ascendant lord; its current domicile lord is the configured target.", policy.aspect_policy, "§54 and note 126"),
        _clause(profile_id, "malefic_aspects_ascendant_lord", 4, SahlMatterClauseRole.GATE,
                SahlMatterClauseState.TRIGGERED if malefics else SahlMatterClauseState.CLEAR,
                (_m("hard_malefic_relations", ",".join(malefics) or "none"),),
                "A conjunction, square, or opposition by Mars or Saturn triggers the explicit seed-impediment warning.", "whole_sign_hard_malefic_relation", "§54"),
        _clause(profile_id, "moon_increased_in_light_and_number", 5, SahlMatterClauseRole.FORTIFIER, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_increasing_in_light", waxing), _m("sun_moon_elongation", elongation, units="degrees"), _m("moon_longitude_rate", moon.speed, units="degrees/day"), _m("number_predicate", None)),
                "Increasing light is measured; the independent 'number' predicate remains source-indeterminate.", policy.number_policy, "§55a"),
        _clause(profile_id, "moon_under_rays_and_defective_in_number", 6, SahlMatterClauseRole.GATE,
                SahlMatterClauseState.CLEAR if not under_rays else SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_solar_distance", solar_distance, units="degrees", comparison="<=", threshold=12.0), _m("under_sahl_12_degree_rays", under_rays), _m("defective_in_number", None)),
                "When the explicit under-rays condition is false the conjunction is clear; when true, the unresolved number predicate prevents a fabricated trigger.", policy.number_policy, "§55a"),
        _clause(profile_id, "increased_number_sprouting_quantity", 7, SahlMatterClauseRole.OUTCOME, SahlMatterClauseState.NOT_EVALUABLE,
                (_m("moon_longitude_rate", moon.speed, units="degrees/day"), _m("number_predicate", None), _m("source_outcome", "sprouts thinly according to quantity sown")),
                "The outcome testimony is preserved but cannot be selected without a source-owned meaning of increased in number.", policy.number_policy, "§55b"),
    )


def _business_partnership(chart, profile_id, policy, _moon_condition=None):
    """Keep Sahl §§32-35 distinct from the Dorothean partnership profile."""

    moon = chart.planets[Body.MOON]
    asc_sign, _, _ = sign_of(chart.houses.asc)
    seventh_sign = SIGNS[(SIGNS.index(asc_sign) + 6) % 12]
    asc_lord = DOMICILE_RULERS[asc_sign]
    partner_lord = DOMICILE_RULERS[seventh_sign]
    joined_fortunes = _joined_names(chart, Body.MOON, _FORTUNES)
    preferred_signs = _COMMON_SIGNS | frozenset(("Leo", "Taurus"))
    known_separation_signs = frozenset(("Libra", "Aquarius"))
    lords_behold = _configured(
        chart.planets[asc_lord].sign,
        chart.planets[partner_lord].sign,
    )
    return (
        _clause(
            profile_id,
            "moon_cleansed_joined_to_fortunes_and_in_preferred_sign",
            1,
            SahlMatterClauseRole.FORTIFIER,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("moon_sign", moon.sign),
                _m("preferred_sign", moon.sign in preferred_signs),
                _m("moon_joined_fortunes", ",".join(joined_fortunes) or "none"),
                _m("cleansed_predicate", None),
            ),
            "Sections 32-33 join Moon cleansing, bodily fortune contact, and the common, Leo, or Taurus sign condition. The source supplies no closed cleansing predicate, so its compound is not fabricated from the computable conjuncts.",
            policy.cleansing_policy,
            "sections_32_to_33",
        ),
        _clause(
            profile_id,
            "libra_or_aquarius_separation_warning",
            2,
            SahlMatterClauseRole.GATE,
            (
                SahlMatterClauseState.TRIGGERED
                if moon.sign in known_separation_signs or asc_sign in known_separation_signs
                else SahlMatterClauseState.NOT_EVALUABLE
            ),
            (
                _m("moon_sign", moon.sign),
                _m("ascendant_sign", asc_sign),
                _m("named_separation_signs", "Libra,Aquarius"),
                _m("lower_sign_class", "source_not_enumerated"),
            ),
            "Section 33 expressly calls out Libra and Aquarius in its lower-sign and separation language. Other lower-sign classifications are not inferred from a modern taxonomy.",
            "named_signs_with_unenumerated_lower_sign_class",
            "section_33",
        ),
        _clause(
            profile_id,
            "reception_and_aspect_relationship",
            3,
            SahlMatterClauseRole.WITNESS,
            SahlMatterClauseState.NOT_EVALUABLE,
            (
                _m("ascendant_lord", asc_lord),
                _m("partner_lord", partner_lord),
                _m("lord_relation", _relation(chart.planets[asc_lord].sign, chart.planets[partner_lord].sign)),
                _m("reception_predicate", None),
                _m("source_divides_trine_sextile_from_square_opposition", True),
            ),
            "Section 34 distinguishes reception and the softer versus harder aspect families, but it does not close a reception ownership rule or an outcome precedence rule for this product.",
            "source_text_open_reception_and_precedence",
            "section_34",
        ),
        _clause(
            profile_id,
            "partnership_stake_roles",
            4,
            SahlMatterClauseRole.WITNESS,
            SahlMatterClauseState.OBSERVED,
            (
                _m("first_place", "initiating_partner"),
                _m("seventh_place", "other_partner"),
                _m("tenth_place", "partnership_wealth_or_work"),
                _m("fourth_place", "partnership_conclusion"),
                _m("ascendant_sign", asc_sign),
                _m("seventh_sign", seventh_sign),
            ),
            "Section 35's four stake roles remain named witnesses; they do not create a generic house-topic election score.",
            policy.stake_policy,
            "section_35",
        ),
        _clause(
            profile_id,
            "principal_lords_behold_one_another",
            5,
            SahlMatterClauseRole.FORTIFIER,
            (
                SahlMatterClauseState.SATISFIED
                if lords_behold
                else SahlMatterClauseState.CLEAR
            ),
            (
                _m("ascendant_lord", asc_lord),
                _m("partner_lord", partner_lord),
                _m("lord_relation", _relation(chart.planets[asc_lord].sign, chart.planets[partner_lord].sign)),
                _m("lords_behold", lords_behold),
            ),
            "Section 35 requires the two principal lords to behold one another under the profile's fixed whole-sign configuration policy.",
            policy.aspect_policy,
            "section_35",
        ),
    )


_BUILDERS = {
    SahlMatterProfileId.LENDING: _lending,
    SahlMatterProfileId.INVESTMENT: _investment,
    SahlMatterProfileId.PURCHASE: _purchase,
    SahlMatterProfileId.SALE: _sale,
    SahlMatterProfileId.BUILDING: _building,
    SahlMatterProfileId.DEMOLITION: _demolition,
    SahlMatterProfileId.LAND: _land,
    SahlMatterProfileId.WELLS_AND_RIVERS: _wells,
    SahlMatterProfileId.PLANTING: _planting,
    SahlMatterProfileId.SOWING: _sowing,
    SahlMatterProfileId.BUSINESS_PARTNERSHIP: _business_partnership,
}


def evaluate_sahl_matter_profile(
    chart: ChartContext,
    *,
    profile_id: SahlMatterProfileId,
    moon_condition: "SahlMoonConditionEvaluation",
    reader_provenance: str,
    policy: SahlMatterProfilePolicy | None = None,
) -> SahlMatterProfileEvaluation:
    """Evaluate one complete named Sahl source layer without scoring."""

    profile_id = SahlMatterProfileId(profile_id)
    resolved_policy = _POLICIES[profile_id] if policy is None else policy
    if resolved_policy.profile_id is not profile_id:
        raise ValueError("policy identity must match requested profile")
    if chart.houses is None:
        raise ValueError("Sahl matter profiles require a house figure")
    if moon_condition.jd_ut != chart.jd_ut:
        raise ValueError("Moon condition and matter profile must share one instant")
    missing = tuple(body for body in _TRADITIONAL_BODIES if body not in chart.planets)
    if missing:
        raise ValueError(f"Sahl matter profile requires traditional bodies: {', '.join(missing)}")
    if Body.TRUE_NODE not in chart.nodes:
        raise ValueError("Sahl matter profile requires the true lunar node")
    if not reader_provenance:
        raise ValueError("reader_provenance must remain visible")

    clauses = _BUILDERS[profile_id](
        chart,
        profile_id,
        resolved_policy,
        moon_condition,
    )
    triggered = tuple(item.clause_id for item in clauses if item.state is SahlMatterClauseState.TRIGGERED)
    unresolved = tuple(item.clause_id for item in clauses if item.state is SahlMatterClauseState.NOT_EVALUABLE)
    status = (
        SahlMatterProfileStatus.TRIGGERED if triggered
        else SahlMatterProfileStatus.INDETERMINATE if unresolved
        else SahlMatterProfileStatus.CLEAR
    )
    authority = _source(profile_id)
    return SahlMatterProfileEvaluation(
        jd_ut=chart.jd_ut,
        profile_id=profile_id,
        profile_version=resolved_policy.profile_version,
        matter=_MATTERS[profile_id],
        status=status,
        moon_condition=moon_condition,
        clauses=clauses,
        triggered_clause_ids=triggered,
        not_evaluable_clause_ids=unresolved,
        reader_provenance=reader_provenance,
        authorities=(authority,),
        numerically_complete=not unresolved,
    )


def sahl_matter_profile_at(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    profile_id: SahlMatterProfileId,
    burnt_path_variant: "SahlBurntPathVariant",
    eighth_rule_variant: "SahlEighthRuleVariant | None" = None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    policy: SahlMatterProfilePolicy | None = None,
    moon_policy: "SahlMoonConditionPolicy | None" = None,
) -> SahlMatterProfileEvaluation:
    """Build one chart and evaluate the general Sahl layer plus a named matter."""

    from dataclasses import replace
    from .western_electional import (
        SAHL_MOON_CONDITION_V1,
        SahlBurntPathVariant,
        SahlEighthRuleVariant,
        SahlMoonConditionPolicy,
        evaluate_sahl_moon_condition,
    )

    profile_id = SahlMatterProfileId(profile_id)
    if not isinstance(burnt_path_variant, SahlBurntPathVariant):
        raise TypeError("burnt_path_variant must be an explicit SahlBurntPathVariant")
    if eighth_rule_variant is not None and not isinstance(eighth_rule_variant, SahlEighthRuleVariant):
        raise TypeError("eighth_rule_variant must be a SahlEighthRuleVariant or None")
    resolved_moon_policy = SAHL_MOON_CONDITION_V1 if moon_policy is None else moon_policy
    if not isinstance(resolved_moon_policy, SahlMoonConditionPolicy):
        raise TypeError("moon_policy must be a SahlMoonConditionPolicy")
    overrides = {"burnt_path_variant": burnt_path_variant}
    if eighth_rule_variant is not None:
        overrides["eighth_rule_variant"] = eighth_rule_variant
    resolved_moon_policy = replace(resolved_moon_policy, **overrides)
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
    voc = is_void_of_course(jd_ut, reader=resolved_reader, modern=False)
    reader_path = getattr(resolved_reader, "path", None)
    provenance = str(reader_path) if reader_path is not None else f"{type(resolved_reader).__module__}.{type(resolved_reader).__qualname__}"
    moon_condition = evaluate_sahl_moon_condition(
        chart,
        void_of_course=voc,
        position_product=resolved_moon_policy.position_product,
        reader_provenance=provenance,
        policy=resolved_moon_policy,
    )
    return evaluate_sahl_matter_profile(
        chart,
        profile_id=profile_id,
        moon_condition=moon_condition,
        reader_provenance=provenance,
        policy=policy,
    )

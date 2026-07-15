"""Dorotheus Book V.6 bounded Moon-condition doctrine.

This module owns the source-specific computational object behind
``dorotheus_moon_condition_v1``.  It deliberately does not merge Dorotheus's
eleven corruption clauses with the later Ramesey or Sahl lists.

The authority is Dorotheus of Sidon, *Carmen Astrologicum*, the Umar
al-Tabari translation, 2nd edition, translated and edited by Benjamin Dykes,
Book V.6, printed pp. 233-235.  Dykes's glossary supplies the edition-owned
meanings of whole-sign configuration, twelfth-parts, and the 15-degree
under-the-rays convention.  His introduction, printed p. 36, identifies the
Egyptian bounds as Dorotheus's bound table.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .chart import ChartContext, create_chart
from .constants import Body
from .egyptian_bounds import (
    EgyptianBoundsDoctrine,
    EgyptianBoundsPolicy,
    egyptian_bound_of,
)
from .eclipse import EclipseCalculator
from .houses import HousePolicy, assign_house
from .spk_reader import SpkReader, get_reader


__all__ = [
    "DorotheusRuleState",
    "DorotheusMoonConditionStatus",
    "DorotheusRemedyApplicability",
    "DorotheusMeasurement",
    "DorotheusClauseWitness",
    "DorotheusRuleWitness",
    "DorotheusRemedyWitness",
    "DorotheusMoonConditionPolicy",
    "DorotheusMoonConditionEvaluation",
    "DOROTHEUS_MOON_CONDITION_V1",
    "evaluate_dorotheus_moon_condition",
    "dorotheus_moon_condition_at",
]


class DorotheusRuleState(str, Enum):
    """Truth state for one source-defined corruption clause."""

    CLEAR = "clear"
    TRIGGERED = "triggered"
    NOT_EVALUABLE = "not_evaluable"


class DorotheusMoonConditionStatus(str, Enum):
    """Non-scored summary derived from all eleven clauses."""

    CLEAR = "clear_of_profile_impediments"
    TRIGGERED = "one_or_more_profile_impediments"
    INDETERMINATE = "indeterminate"


class DorotheusRemedyApplicability(str, Enum):
    """Applicability of the V.6.15 unavoidable-time instruction."""

    NOT_APPLICABLE = "not_applicable"
    APPLICABLE = "applicable"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class DorotheusMeasurement:
    """One visible input, threshold, or unresolved observation."""

    name: str
    value: float | str | bool | None
    units: str | None = None
    comparison: str | None = None
    threshold: float | str | bool | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("measurement name must be non-empty")
        for label, value in (("value", self.value), ("threshold", self.threshold)):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"measurement {label} must be finite")


@dataclass(frozen=True, slots=True)
class DorotheusClauseWitness:
    """Visible derivation for one clause."""

    clause_id: str
    state: DorotheusRuleState
    policy_id: str
    policy_reference: str
    measurements: tuple[DorotheusMeasurement, ...]
    explanation: str

    def __post_init__(self) -> None:
        if not self.clause_id or not self.policy_id or not self.policy_reference:
            raise ValueError("clause identity, policy, and authority must be visible")
        if not self.measurements:
            raise ValueError("a clause witness must preserve at least one measurement")
        if not self.explanation:
            raise ValueError("clause explanation must be non-empty")


@dataclass(frozen=True, slots=True)
class DorotheusRuleWitness:
    """One V.6 corruption clause in printed source order."""

    rule_id: str
    source_order: int
    state: DorotheusRuleState
    clauses: tuple[DorotheusClauseWitness, ...]
    source_reference: str
    modifiers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= self.source_order <= 11:
            raise ValueError("source_order must be in [1, 11]")
        if not self.clauses:
            raise ValueError("a rule witness must preserve at least one clause")
        expected = _state_from_clauses(self.clauses)
        if self.state is not expected:
            raise ValueError("rule state must derive from its visible clauses")
        if not self.rule_id or not self.source_reference:
            raise ValueError("rule identity and source reference must be visible")


@dataclass(frozen=True, slots=True)
class DorotheusRemedyWitness:
    """Separate V.6.15 instruction, never an eraser of a corruption clause."""

    remedy_id: str
    applicability: DorotheusRemedyApplicability
    triggering_rule_ids: tuple[str, ...]
    unavoidable_time_urgency: bool | None
    source_reference: str
    instructions: tuple[str, ...]
    uncomputed_requirements: tuple[str, ...]
    assessment_semantics: str = "instruction_only_not_fulfillment_assessment"
    erases_triggered_rules: bool = False

    def __post_init__(self) -> None:
        if not self.remedy_id or not self.source_reference:
            raise ValueError("remedy identity and source reference must be visible")
        if not self.instructions or not self.uncomputed_requirements:
            raise ValueError("remedy instructions and uncomputed requirements must be visible")
        if self.assessment_semantics != "instruction_only_not_fulfillment_assessment":
            raise ValueError("Dorotheus v1 remedy semantics are fixed")
        if self.erases_triggered_rules:
            raise ValueError("the remedy cannot erase triggered rule witnesses")
        if self.applicability is DorotheusRemedyApplicability.APPLICABLE:
            if not self.triggering_rule_ids or self.unavoidable_time_urgency is not True:
                raise ValueError("applicability requires a trigger and unavoidable urgency")


_POSITION_PRODUCT = (
    "chart_apparent_geocentric_ecliptic_longitude_with_"
    "planetdata_astrometric_geocentric_longitude_rate"
)


@dataclass(frozen=True, slots=True)
class DorotheusMoonConditionPolicy:
    """Closed computational doctrine for ``dorotheus_moon_condition_v1``."""

    profile_id: str = "dorotheus_moon_condition_v1"
    profile_version: str = "1.0.0"
    eclipse_policy: str = "moira_geometric_lunar_eclipse_contact"
    under_rays_policy: str = "dykes_glossary_15_degree_solar_distance"
    twelfth_part_policy: str = "dodecatemorion_traditional_malefic_domiciles"
    southern_descent_policy: str = "unresolved_no_region_or_crossing_tolerance"
    aspect_policy: str = "dorotheus_whole_sign_configuration"
    solar_disengagement_policy: str = "unresolved_longitude_or_latitude_scope"
    slow_moon_policy: str = "strict_daily_motion_below_12"
    burned_path_policy: str = "whole_tropical_libra_and_scorpio"
    bound_policy: str = "dorotheus_egyptian_terminal_malefic_bound"
    ninth_house_policy: str = "explicit_quadrant_ninth_cadent_from_midheaven"
    position_product: str = _POSITION_PRODUCT

    def __post_init__(self) -> None:
        fixed = {
            "profile_id": "dorotheus_moon_condition_v1",
            "profile_version": "1.0.0",
            "eclipse_policy": "moira_geometric_lunar_eclipse_contact",
            "under_rays_policy": "dykes_glossary_15_degree_solar_distance",
            "twelfth_part_policy": "dodecatemorion_traditional_malefic_domiciles",
            "southern_descent_policy": "unresolved_no_region_or_crossing_tolerance",
            "aspect_policy": "dorotheus_whole_sign_configuration",
            "solar_disengagement_policy": "unresolved_longitude_or_latitude_scope",
            "slow_moon_policy": "strict_daily_motion_below_12",
            "burned_path_policy": "whole_tropical_libra_and_scorpio",
            "bound_policy": "dorotheus_egyptian_terminal_malefic_bound",
            "ninth_house_policy": "explicit_quadrant_ninth_cadent_from_midheaven",
            "position_product": _POSITION_PRODUCT,
        }
        for name, value in fixed.items():
            if getattr(self, name) != value:
                raise ValueError(f"{name} is fixed for this admitted profile")


DOROTHEUS_MOON_CONDITION_V1 = DorotheusMoonConditionPolicy()


@dataclass(frozen=True, slots=True)
class DorotheusMoonConditionEvaluation:
    """Transparent evaluation of V.6.3-14 and its separate remedy."""

    jd_ut: float
    profile_id: str
    profile_version: str
    status: DorotheusMoonConditionStatus
    rules: tuple[DorotheusRuleWitness, ...]
    remedies: tuple[DorotheusRemedyWitness, ...]
    position_product: str
    reader_provenance: str
    latitude: float
    longitude: float
    requested_house_system: str | None
    effective_house_system: str | None
    house_fallback: bool | None
    election_class: str = "ephemeral"
    matter_scope: str = "Dorotheus Book V.6 corruption of the Moon, clauses 3-14"
    complete_electional_judgement: bool = False
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_ut):
            raise ValueError("jd_ut must be finite")
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be in [-90, 90]")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be in [-180, 180]")
        if not self.reader_provenance:
            raise ValueError("reader_provenance must be visible")
        if len(self.rules) != 11:
            raise ValueError("Dorotheus evaluation must contain exactly eleven rules")
        if tuple(rule.source_order for rule in self.rules) != tuple(range(1, 12)):
            raise ValueError("Dorotheus rules must remain in printed source order")
        expected = _status_from_rules(self.rules)
        if self.status is not expected:
            raise ValueError("evaluation status must derive from the eleven rules")
        if len(self.remedies) != 1:
            raise ValueError("Dorotheus v1 preserves exactly one remedy instruction")
        if self.election_class != "ephemeral" or self.complete_electional_judgement:
            raise ValueError("Dorotheus v1 is bounded and ephemeral")
        if self.advice_language != "not_provided" or self.recommendation_language != "not_provided":
            raise ValueError("this profile cannot emit advice or recommendations")

    @property
    def triggered_rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules if rule.state is DorotheusRuleState.TRIGGERED)

    @property
    def not_evaluable_rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules if rule.state is DorotheusRuleState.NOT_EVALUABLE)


_SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
_MALEFIC_DOMICILES = frozenset(("Aries", "Scorpio", "Capricorn", "Aquarius"))
_SOURCE = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "2nd ed., Benjamin Dykes trans. and ed., Book V.6"
)
_RULE_SOURCES = {
    1: f"{_SOURCE}, clause 3, printed p. 233",
    2: f"{_SOURCE}, clauses 4-5, printed p. 234",
    3: f"{_SOURCE}, clause 6, printed p. 234",
    4: f"{_SOURCE}, clause 7 and note 15, printed p. 234",
    5: f"{_SOURCE}, clause 8, printed p. 234",
    6: f"{_SOURCE}, clause 9, printed p. 234",
    7: f"{_SOURCE}, clause 10 and note 18, printed p. 234",
    8: f"{_SOURCE}, clause 11, printed p. 234",
    9: f"{_SOURCE}, clause 12, printed p. 234",
    10: f"{_SOURCE}, clause 13 and note 20, printed p. 234",
    11: f"{_SOURCE}, clause 14, printed p. 235",
}
_GLOSSARY = "Dykes, Carmen Astrologicum 2nd ed., glossary, printed pp. 353-376"
_POLICY_REFERENCES = {
    "required_chart_input": "Moira dorotheus_moon_condition_v1 input contract",
    "moira_geometric_lunar_eclipse_contact": (
        f"{_RULE_SOURCES[1]}; Moira native geometric lunar-eclipse classification"
    ),
    "dykes_glossary_15_degree_solar_distance": f"{_RULE_SOURCES[2]}; {_GLOSSARY}, Sun's rays",
    "dodecatemorion_traditional_malefic_domiciles": f"{_RULE_SOURCES[3]}; {_GLOSSARY}, Twelfth-part",
    "unresolved_no_region_or_crossing_tolerance": f"{_RULE_SOURCES[4]}; note 15 identifies the line as the ecliptic but supplies no region or tolerance",
    "dorotheus_whole_sign_configuration": f"{_RULE_SOURCES[5]}; {_RULE_SOURCES[6]}; {_GLOSSARY}, Configured, Look at, Whole signs",
    "unresolved_longitude_or_latitude_scope": f"{_RULE_SOURCES[7]}; the text supplies neither a connection interval nor a latitude criterion",
    "strict_daily_motion_below_12": _RULE_SOURCES[8],
    "whole_tropical_libra_and_scorpio": _RULE_SOURCES[9],
    "dorotheus_egyptian_terminal_malefic_bound": (
        f"{_RULE_SOURCES[10]}; Dykes introduction printed p. 36 identifies Dorotheus's Egyptian bounds"
    ),
    "explicit_quadrant_ninth_cadent_from_midheaven": f"{_RULE_SOURCES[11]}; {_GLOSSARY}, Cadent and Withdrawal",
    _POSITION_PRODUCT: (
        f"{_SOURCE}; Moira chart apparent-geocentric longitude and PlanetData rate products"
    ),
}


def _measurement(
    name: str,
    value: float | str | bool | None,
    *,
    units: str | None = None,
    comparison: str | None = None,
    threshold: float | str | bool | None = None,
) -> DorotheusMeasurement:
    return DorotheusMeasurement(name, value, units, comparison, threshold)


def _clause(
    clause_id: str,
    state: DorotheusRuleState,
    policy_id: str,
    measurements: tuple[DorotheusMeasurement, ...],
    explanation: str,
) -> DorotheusClauseWitness:
    reference = _POLICY_REFERENCES.get(policy_id)
    if reference is None:
        raise ValueError(f"no Dorotheus authority registered for policy {policy_id!r}")
    return DorotheusClauseWitness(
        clause_id, state, policy_id, reference, measurements, explanation
    )


def _missing(clause_id: str, requirement: str) -> DorotheusClauseWitness:
    return _clause(
        clause_id,
        DorotheusRuleState.NOT_EVALUABLE,
        "required_chart_input",
        (_measurement("missing_input", requirement),),
        f"Required input is absent: {requirement}.",
    )


def _state_from_clauses(
    clauses: tuple[DorotheusClauseWitness, ...],
) -> DorotheusRuleState:
    if any(clause.state is DorotheusRuleState.TRIGGERED for clause in clauses):
        return DorotheusRuleState.TRIGGERED
    if any(clause.state is DorotheusRuleState.NOT_EVALUABLE for clause in clauses):
        return DorotheusRuleState.NOT_EVALUABLE
    return DorotheusRuleState.CLEAR


def _rule(
    rule_id: str,
    order: int,
    clauses: tuple[DorotheusClauseWitness, ...],
    *,
    modifiers: tuple[str, ...] = (),
) -> DorotheusRuleWitness:
    return DorotheusRuleWitness(
        rule_id,
        order,
        _state_from_clauses(clauses),
        clauses,
        _RULE_SOURCES[order],
        modifiers,
    )


def _status_from_rules(
    rules: tuple[DorotheusRuleWitness, ...],
) -> DorotheusMoonConditionStatus:
    if any(rule.state is DorotheusRuleState.TRIGGERED for rule in rules):
        return DorotheusMoonConditionStatus.TRIGGERED
    if any(rule.state is DorotheusRuleState.NOT_EVALUABLE for rule in rules):
        return DorotheusMoonConditionStatus.INDETERMINATE
    return DorotheusMoonConditionStatus.CLEAR


def _shortest_distance(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _whole_sign_offset(a_sign: str, b_sign: str) -> int:
    return (_SIGNS.index(b_sign) - _SIGNS.index(a_sign)) % 12


def _relative_phase(moon, sun) -> tuple[float, float, str]:
    separation = _shortest_distance(moon.longitude, sun.longitude)
    signed = (moon.longitude - sun.longitude + 180.0) % 360.0 - 180.0
    rate = math.copysign(1.0, signed) * (moon.speed - sun.speed) if signed else 0.0
    phase = (
        "exact"
        if separation < 1e-12
        else "applying"
        if rate < 0.0
        else "separating"
        if rate > 0.0
        else "stationary_relative"
    )
    return separation, rate, phase


def _remedy(
    rules: tuple[DorotheusRuleWitness, ...],
    unavoidable_time_urgency: bool | None,
) -> DorotheusRemedyWitness:
    triggered = tuple(
        rule.rule_id for rule in rules if rule.state is DorotheusRuleState.TRIGGERED
    )
    unresolved = any(rule.state is DorotheusRuleState.NOT_EVALUABLE for rule in rules)
    applicability = (
        DorotheusRemedyApplicability.APPLICABLE
        if triggered and unavoidable_time_urgency is True
        else DorotheusRemedyApplicability.NOT_APPLICABLE
        if unavoidable_time_urgency is False or (not triggered and not unresolved)
        else DorotheusRemedyApplicability.INDETERMINATE
    )
    return DorotheusRemedyWitness(
        remedy_id="place_jupiter_or_venus_in_ascendant_or_midheaven",
        applicability=applicability,
        triggering_rule_ids=triggered,
        unavoidable_time_urgency=unavoidable_time_urgency,
        source_reference=f"{_SOURCE}, clause 15, printed p. 235",
        instructions=("Place Jupiter or Venus in the Ascendant or Midheaven.",),
        uncomputed_requirements=(
            "Whether the elected time truly cannot be postponed is caller-owned.",
            "Remedy placement fulfillment is not assessed by this Moon-condition profile.",
        ),
    )


def evaluate_dorotheus_moon_condition(
    chart: ChartContext,
    *,
    moon_eclipsed: bool | None,
    unavoidable_time_urgency: bool | None,
    position_product: str,
    reader_provenance: str,
    policy: DorotheusMoonConditionPolicy = DOROTHEUS_MOON_CONDITION_V1,
) -> DorotheusMoonConditionEvaluation:
    """Evaluate the eleven source-ordered V.6 corruption clauses."""

    if not isinstance(policy, DorotheusMoonConditionPolicy):
        raise TypeError("policy must be a DorotheusMoonConditionPolicy")
    if position_product != policy.position_product:
        raise ValueError("position_product does not match Dorotheus v1")
    if not reader_provenance:
        raise ValueError("reader_provenance must be non-empty")
    if moon_eclipsed is not None and not isinstance(moon_eclipsed, bool):
        raise TypeError("moon_eclipsed must be bool or None")
    if unavoidable_time_urgency is not None and not isinstance(unavoidable_time_urgency, bool):
        raise TypeError("unavoidable_time_urgency must be bool or None")

    moon = chart.planets.get(Body.MOON)
    sun = chart.planets.get(Body.SUN)
    mars = chart.planets.get(Body.MARS)
    saturn = chart.planets.get(Body.SATURN)
    topocentric = tuple(
        body.name
        for body in (moon, sun, mars, saturn)
        if body is not None and body.is_topocentric
    )
    if topocentric:
        raise ValueError(
            "Dorotheus v1 requires geocentric planetary positions; "
            f"topocentric inputs found for {', '.join(topocentric)}"
        )

    rules: list[DorotheusRuleWitness] = []

    eclipse_clause = (
        _missing("moon_eclipsed", "lunar eclipse contact classification")
        if moon_eclipsed is None
        else _clause(
            "moon_eclipsed",
            DorotheusRuleState.TRIGGERED if moon_eclipsed else DorotheusRuleState.CLEAR,
            policy.eclipse_policy,
            (_measurement("moon_eclipsed", moon_eclipsed, comparison="==", threshold=True),),
            "The present Moon is tested against Moira's geometric lunar-eclipse contact classification.",
        )
    )
    rules.append(_rule(
        "moon_eclipsed",
        1,
        (eclipse_clause,),
        modifiers=(
            "Dorotheus intensifies this condition when the eclipse occupies the natal Moon's sign or its trine; natal input is outside this ephemeral profile.",
        ),
    ))

    if moon is None or sun is None:
        missing = Body.MOON if moon is None else Body.SUN
        rules.append(_rule("moon_under_solar_rays", 2, (_missing("sun_moon_distance", missing),)))
    else:
        separation, rate, phase = _relative_phase(moon, sun)
        under_rays = separation <= 15.0
        rules.append(_rule(
            "moon_under_solar_rays",
            2,
            (_clause(
                "moon_within_15deg_sun",
                DorotheusRuleState.TRIGGERED if under_rays else DorotheusRuleState.CLEAR,
                policy.under_rays_policy,
                (
                    _measurement("separation", separation, units="degrees", comparison="<=", threshold=15.0),
                    _measurement("phase", phase),
                    _measurement("separation_rate", rate, units="degrees/day"),
                ),
                "The source says the Moon is unseen; v1 binds that wording to this edition's 15-degree under-rays glossary entry.",
            ),),
            modifiers=(
                "Dorotheus makes this condition beneficial for concealed work and says disengagement plus reappearance is more hidden.",
            ),
        ))

    if moon is None:
        rules.append(_rule("moon_in_malefic_twelfth_part", 3, (_missing("moon_twelfth_part", Body.MOON),)))
    else:
        twelfth_index = (_SIGNS.index(moon.sign) + int(moon.sign_degree / 2.5)) % 12
        twelfth_sign = _SIGNS[twelfth_index]
        malefic = twelfth_sign in _MALEFIC_DOMICILES
        rules.append(_rule(
            "moon_in_malefic_twelfth_part",
            3,
            (_clause(
                "moon_twelfth_part_ruled_by_mars_or_saturn",
                DorotheusRuleState.TRIGGERED if malefic else DorotheusRuleState.CLEAR,
                policy.twelfth_part_policy,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("degree_in_sign", moon.sign_degree, units="degrees"),
                    _measurement("twelfth_part_sign", twelfth_sign),
                    _measurement("malefic_domicile", malefic, comparison="==", threshold=True),
                ),
                "The 2.5-degree twelfth-part maps into a sign; Mars- and Saturn-ruled signs are the malefic twelfth-parts.",
            ),),
        ))

    if moon is None:
        south_clause = _missing("moon_on_ecliptic_descending_south", Body.MOON)
    else:
        south_clause = _clause(
            "moon_on_ecliptic_descending_south",
            DorotheusRuleState.NOT_EVALUABLE,
            policy.southern_descent_policy,
            (
                _measurement("moon_ecliptic_latitude", moon.latitude, units="degrees"),
                _measurement("required_unresolved_semantics", "crossing region and tolerance"),
            ),
            "The edition identifies the line as the ecliptic, but the clause gives no region or numerical crossing tolerance; v1 does not substitute a node orb.",
        )
    rules.append(_rule("moon_on_ecliptic_descending_south", 4, (south_clause,)))

    if moon is None or sun is None:
        missing = Body.MOON if moon is None else Body.SUN
        rules.append(_rule("moon_opposition_sun", 5, (_missing("sun_opposition", missing),)))
    else:
        offset = _whole_sign_offset(moon.sign, sun.sign)
        rules.append(_rule(
            "moon_opposition_sun",
            5,
            (_clause(
                "moon_whole_sign_opposition_sun",
                DorotheusRuleState.TRIGGERED if offset == 6 else DorotheusRuleState.CLEAR,
                policy.aspect_policy,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("sun_sign", sun.sign),
                    _measurement("sign_offset", offset, comparison="==", threshold=6),
                ),
                "Opposition is evaluated first as a whole-sign configuration under the edition's glossary.",
            ),),
        ))

    malefic_clauses: list[DorotheusClauseWitness] = []
    if moon is None:
        malefic_clauses.append(_missing("moon_malefic_configuration", Body.MOON))
    else:
        configured_offsets = frozenset((0, 2, 3, 4, 6, 8, 9, 10))
        for body_name, body in ((Body.MARS, mars), (Body.SATURN, saturn)):
            if body is None:
                malefic_clauses.append(_missing(f"moon_{body_name.lower()}_configuration", body_name))
                continue
            offset = _whole_sign_offset(moon.sign, body.sign)
            malefic_clauses.append(_clause(
                f"moon_with_or_looking_at_{body_name.lower()}",
                DorotheusRuleState.TRIGGERED if offset in configured_offsets else DorotheusRuleState.CLEAR,
                policy.aspect_policy,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement(f"{body_name.lower()}_sign", body.sign),
                    _measurement("sign_offset", offset, comparison="in", threshold="0,2,3,4,6,8,9,10"),
                ),
                "With means the same sign; looking means a whole-sign sextile, square, trine, or opposition.",
            ))
    rules.append(_rule("moon_with_or_looking_at_infortune", 6, tuple(malefic_clauses)))

    if moon is None or sun is None:
        missing = Body.MOON if moon is None else Body.SUN
        disengagement = _missing("moon_disengaging_from_sun", missing)
    else:
        separation, rate, phase = _relative_phase(moon, sun)
        disengagement = _clause(
            "moon_disengaging_from_sun_in_longitude_or_latitude",
            DorotheusRuleState.NOT_EVALUABLE,
            policy.solar_disengagement_policy,
            (
                _measurement("longitude_separation", separation, units="degrees"),
                _measurement("longitude_phase", phase),
                _measurement("longitude_separation_rate", rate, units="degrees/day"),
                _measurement("moon_ecliptic_latitude", moon.latitude, units="degrees"),
                _measurement("required_unresolved_semantics", "connection interval or latitude criterion"),
            ),
            "The text names disengagement in longitude or latitude but supplies no lawful interval or latitude criterion; v1 preserves the measured evidence without inventing a gate.",
        )
    rules.append(_rule("moon_disengaging_from_sun", 7, (disengagement,)))

    if moon is None:
        rules.append(_rule("moon_slow_below_12deg_per_day", 8, (_missing("moon_daily_motion", Body.MOON),)))
    else:
        slow = moon.speed < 12.0
        rules.append(_rule(
            "moon_slow_below_12deg_per_day",
            8,
            (_clause(
                "moon_speed_below_12deg_per_day",
                DorotheusRuleState.TRIGGERED if slow else DorotheusRuleState.CLEAR,
                policy.slow_moon_policy,
                (_measurement("moon_longitude_rate", moon.speed, units="degrees/day", comparison="<", threshold=12.0),),
                "Clause 11 defines the least motion by a strict daily course below 12 degrees; no acceleration derivative is added.",
            ),),
        ))

    if moon is None:
        rules.append(_rule("moon_in_burned_path", 9, (_missing("moon_burned_path", Body.MOON),)))
    else:
        burned = 180.0 <= moon.longitude < 240.0
        rules.append(_rule(
            "moon_in_burned_path",
            9,
            (_clause(
                "moon_in_whole_libra_or_scorpio",
                DorotheusRuleState.TRIGGERED if burned else DorotheusRuleState.CLEAR,
                policy.burned_path_policy,
                (
                    _measurement("moon_longitude", moon.longitude, units="degrees"),
                    _measurement("burned_path_interval", "[180, 240)", units="degrees", comparison="in", threshold="[180, 240)"),
                ),
                "Dorotheus names Libra and Scorpio; v1 preserves both whole tropical signs rather than importing a later 15-to-15 interval.",
            ),),
        ))

    if moon is None:
        rules.append(_rule("moon_in_terminal_malefic_bound", 10, (_missing("moon_bound", Body.MOON),)))
    else:
        bound = egyptian_bound_of(
            moon.longitude,
            policy=EgyptianBoundsPolicy(EgyptianBoundsDoctrine.EGYPTIAN),
        )
        terminal_malefic = bound.segment.end_degree == 30.0 and bound.ruler in (Body.MARS, Body.SATURN)
        rules.append(_rule(
            "moon_in_terminal_malefic_bound",
            10,
            (_clause(
                "moon_terminal_egyptian_bound_ruled_by_malefic",
                DorotheusRuleState.TRIGGERED if terminal_malefic else DorotheusRuleState.CLEAR,
                policy.bound_policy,
                (
                    _measurement("moon_sign", bound.sign),
                    _measurement("degree_in_sign", bound.degree_in_sign, units="degrees"),
                    _measurement("bound_ruler", bound.ruler, comparison="in", threshold="Mars or Saturn"),
                    _measurement("bound_interval", f"[{bound.segment.start_degree}, {bound.segment.end_degree})"),
                ),
                "Only a terminal Egyptian bound ending at 30 degrees and ruled by Mars or Saturn satisfies the clause.",
            ),),
        ))

    if moon is None:
        ninth = _missing("moon_ninth_cadent_from_midheaven", Body.MOON)
    elif chart.houses is None:
        ninth = _missing("moon_ninth_cadent_from_midheaven", "quadrant house cusps")
    elif not chart.houses.is_quadrant_system:
        ninth = _clause(
            "moon_ninth_cadent_from_midheaven",
            DorotheusRuleState.NOT_EVALUABLE,
            policy.ninth_house_policy,
            (
                _measurement("requested_house_system", chart.houses.system),
                _measurement("effective_house_system", chart.houses.effective_system),
            ),
            "The selected effective house system is not a quadrant system, so dynamic falling from the Midheaven cannot be asserted.",
        )
    else:
        placement = assign_house(moon.longitude, chart.houses)
        ninth = _clause(
            "moon_ninth_cadent_from_midheaven",
            DorotheusRuleState.TRIGGERED if placement.house == 9 else DorotheusRuleState.CLEAR,
            policy.ninth_house_policy,
            (
                _measurement("house", placement.house, comparison="==", threshold=9),
                _measurement("requested_house_system", chart.houses.system),
                _measurement("effective_house_system", chart.houses.effective_system),
                _measurement("house_fallback", chart.houses.fallback),
            ),
            "The clause is the ninth-place fall from the Midheaven, not generic cadency in houses 3, 6, 9, and 12.",
        )
    rules.append(_rule("moon_ninth_cadent_from_midheaven", 11, (ninth,)))

    rule_tuple = tuple(rules)
    houses = chart.houses
    return DorotheusMoonConditionEvaluation(
        jd_ut=chart.jd_ut,
        profile_id=policy.profile_id,
        profile_version=policy.profile_version,
        status=_status_from_rules(rule_tuple),
        rules=rule_tuple,
        remedies=(_remedy(rule_tuple, unavoidable_time_urgency),),
        position_product=policy.position_product,
        reader_provenance=reader_provenance,
        latitude=chart.latitude,
        longitude=chart.longitude,
        requested_house_system=houses.system if houses else None,
        effective_house_system=houses.effective_system if houses else None,
        house_fallback=houses.fallback if houses else None,
    )


def dorotheus_moon_condition_at(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    unavoidable_time_urgency: bool | None = None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    policy: DorotheusMoonConditionPolicy = DOROTHEUS_MOON_CONDITION_V1,
) -> DorotheusMoonConditionEvaluation:
    """Build the astronomical inputs and evaluate Dorotheus V.6 once."""

    if not isinstance(policy, DorotheusMoonConditionPolicy):
        raise TypeError("policy must be a DorotheusMoonConditionPolicy")
    resolved_reader = reader if reader is not None else get_reader()
    chart = create_chart(
        jd_ut,
        latitude,
        longitude,
        house_system=house_system,
        bodies=[Body.SUN, Body.MOON, Body.MARS, Body.SATURN],
        reader=resolved_reader,
        policy=house_policy,
    )
    eclipse = EclipseCalculator(reader=resolved_reader).calculate_lunar_event_jd(
        jd_ut,
        kind="penumbral",
    )
    moon_eclipsed = eclipse.is_lunar_eclipse or eclipse.eclipse_type.magnitude_penumbra > 0.0
    reader_path = getattr(resolved_reader, "path", None)
    reader_provenance = (
        str(reader_path)
        if reader_path is not None
        else f"{type(resolved_reader).__module__}.{type(resolved_reader).__qualname__}"
    )
    return evaluate_dorotheus_moon_condition(
        chart,
        moon_eclipsed=moon_eclipsed,
        unavoidable_time_urgency=unavoidable_time_urgency,
        position_product=policy.position_product,
        reader_provenance=reader_provenance,
        policy=policy,
    )

"""Source-owned Western electional doctrine.

This module admits bounded Moon-condition profiles for William Ramesey and
Sahl bin Bishr.  Each profile preserves its own source order, variant policy,
and proof witnesses.  Neither is a complete election, a score, or a
recommendation.

The profile's ambiguity policies are derived from Ramesey's own Book II
definitions and tables.  They remain visible in
``RameseyMoonConditionPolicy`` and in every returned rule witness.  The
generic search transport in :mod:`moira.electional` is deliberately not used
or modified here.

Public surface:
    RameseyRuleState, RameseyMoonConditionStatus, RameseyRemedyApplicability,
    RameseyMeasurement, RameseyClauseWitness, RameseyRuleWitness,
    RameseyRemedyWitness,
    RameseyMoonConditionPolicy, RameseyMoonConditionEvaluation,
    RAMESEY_MOON_CONDITION_V1, evaluate_ramesey_moon_condition,
    ramesey_moon_condition_at.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum

from .chart import ChartContext, create_chart
from .constants import Body
from .egyptian_bounds import EgyptianBoundsDoctrine, EgyptianBoundsPolicy, egyptian_bound_of
from .houses import HouseAngularity, HousePolicy, assign_house, describe_angularity
from .spk_reader import SpkReader, get_reader
from .void_of_course import is_void_of_course

__all__ = [
    "RameseyRuleState",
    "RameseyMoonConditionStatus",
    "RameseyRemedyApplicability",
    "RameseyMeasurement",
    "RameseyClauseWitness",
    "RameseyRuleWitness",
    "RameseyRemedyWitness",
    "RameseyMoonConditionPolicy",
    "RameseyMoonConditionEvaluation",
    "RAMESEY_MOON_CONDITION_V1",
    "evaluate_ramesey_moon_condition",
    "ramesey_moon_condition_at",
    "SahlRuleState",
    "SahlMoonConditionStatus",
    "SahlBurntPathVariant",
    "SahlEighthRuleVariant",
    "SahlMeasurement",
    "SahlClauseWitness",
    "SahlRuleWitness",
    "SahlMoonConditionPolicy",
    "SahlMoonConditionEvaluation",
    "SAHL_MOON_CONDITION_V1",
    "evaluate_sahl_moon_condition",
    "sahl_moon_condition_at",
]


class RameseyRuleState(str, Enum):
    """Truth state for one source-defined gate or compound clause."""

    CLEAR = "clear"
    TRIGGERED = "triggered"
    NOT_EVALUABLE = "not_evaluable"


class RameseyMoonConditionStatus(str, Enum):
    """Non-scored summary of the ten-rule profile."""

    CLEAR = "clear_of_profile_impediments"
    TRIGGERED = "one_or_more_profile_impediments"
    INDETERMINATE = "indeterminate"


class RameseyRemedyApplicability(str, Enum):
    """Applicability of Ramesey's unavoidable-time remedy instruction."""

    NOT_APPLICABLE = "not_applicable"
    APPLICABLE = "applicable"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class RameseyMeasurement:
    """One visible input, measurement, or threshold used by a clause."""

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
class RameseyClauseWitness:
    """Visible derivation of one clause inside a Ramesey rule."""

    clause_id: str
    state: RameseyRuleState
    policy_id: str
    policy_reference: str
    measurements: tuple[RameseyMeasurement, ...]
    explanation: str

    def __post_init__(self) -> None:
        if not self.clause_id or not self.policy_id or not self.policy_reference:
            raise ValueError("clause identity, policy, and authority must be visible")
        if not self.measurements:
            raise ValueError("a clause witness must preserve at least one measurement")
        if not self.explanation:
            raise ValueError("clause explanation must be non-empty")


@dataclass(frozen=True, slots=True)
class RameseyRuleWitness:
    """Result for one rule, preserving its source order and compound clauses."""

    rule_id: str
    source_order: int
    state: RameseyRuleState
    clauses: tuple[RameseyClauseWitness, ...]
    source_reference: str
    modifiers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= self.source_order <= 10:
            raise ValueError("source_order must be in [1, 10]")
        if not self.clauses:
            raise ValueError("a rule witness must preserve at least one clause")
        expected = (
            RameseyRuleState.TRIGGERED
            if any(clause.state is RameseyRuleState.TRIGGERED for clause in self.clauses)
            else RameseyRuleState.NOT_EVALUABLE
            if any(clause.state is RameseyRuleState.NOT_EVALUABLE for clause in self.clauses)
            else RameseyRuleState.CLEAR
        )
        if self.state is not expected:
            raise ValueError("rule state must be derived from its visible clauses")
        if not self.rule_id or not self.source_reference:
            raise ValueError("rule identity and source reference must be visible")


@dataclass(frozen=True, slots=True)
class RameseyRemedyWitness:
    """Separate instruction witness for an unavoidable impeded Moon.

    This vessel records when Ramesey's contingency instruction is relevant.
    It does not claim that the prescribed arrangement has been fulfilled and
    cannot change a gate or the profile's overall Moon-condition status.
    """

    remedy_id: str
    applicability: RameseyRemedyApplicability
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
        if not self.instructions:
            raise ValueError("a remedy witness must preserve its source instructions")
        if not self.uncomputed_requirements:
            raise ValueError("uncomputed remedy requirements must remain visible")
        if self.assessment_semantics != "instruction_only_not_fulfillment_assessment":
            raise ValueError("Ramesey v1 remedy assessment semantics are fixed")
        if self.erases_triggered_rules:
            raise ValueError("a Ramesey remedy cannot erase triggered gate witnesses")
        if self.applicability is RameseyRemedyApplicability.APPLICABLE:
            if not self.triggering_rule_ids or self.unavoidable_time_urgency is not True:
                raise ValueError(
                    "an applicable remedy requires a confirmed impediment and urgent unavoidable time"
                )


# Ramesey, Book II, planetary chapters, printed pp. 53-67.  These are each
# planet's full orb extending before and after an aspect.  A platick aspect
# uses the sum of the two half-orbs (Book II, printed pp. 105-106).
_RAMESEY_FULL_ORBS: tuple[tuple[str, float], ...] = (
    (Body.SATURN, 9.0),
    (Body.JUPITER, 9.0),
    (Body.MARS, 7.0),
    (Body.SUN, 15.0),
    (Body.VENUS, 7.0),
    (Body.MERCURY, 7.0),
    (Body.MOON, 12.0),
)

_POSITION_PRODUCT = (
    "chart_apparent_geocentric_ecliptic_longitude_with_"
    "planetdata_astrometric_geocentric_longitude_rate"
)


@dataclass(frozen=True, slots=True)
class RameseyMoonConditionPolicy:
    """Frozen computational doctrine for ``ramesey_moon_condition_v1``."""

    profile_id: str = "ramesey_moon_condition_v1"
    profile_version: str = "1.0.0"
    degree_policy: str = "ordinal_degree_half_open"
    aspect_policy: str = "ramesey_combined_moieties"
    planetary_full_orbs: tuple[tuple[str, float], ...] = _RAMESEY_FULL_ORBS
    node_policy: str = "true_ecliptic_crossing_node_and_opposition"
    latter_degrees_policy: str = "ramesey_terminal_malefic_term"
    cadency_policy: str = "caller_declared_quadrant_houses_3_6_9_12"
    cancer_beholding_policy: str = "whole_sign_bodily_sextile_or_trine"
    position_product: str = _POSITION_PRODUCT
    void_policy: str = "traditional_planets_exact_perfection_sign_bound"
    via_combusta_policy: str = "tropical_half_open_195_to_225"

    def __post_init__(self) -> None:
        if self.profile_id != "ramesey_moon_condition_v1":
            raise ValueError("profile_id is fixed for this admitted profile")
        if self.profile_version != "1.0.0":
            raise ValueError("profile_version is fixed for this admitted profile")
        if self.planetary_full_orbs != _RAMESEY_FULL_ORBS:
            raise ValueError("Ramesey v1 planetary orbs are source-fixed")
        if self.position_product != _POSITION_PRODUCT:
            raise ValueError("Ramesey v1 position product is source-profile fixed")
        # Keep all remaining doctrine fields closed against accidental caller
        # substitution while still exposing them as inspectable result policy.
        fixed = {
            "degree_policy": "ordinal_degree_half_open",
            "aspect_policy": "ramesey_combined_moieties",
            "node_policy": "true_ecliptic_crossing_node_and_opposition",
            "latter_degrees_policy": "ramesey_terminal_malefic_term",
            "cadency_policy": "caller_declared_quadrant_houses_3_6_9_12",
            "cancer_beholding_policy": "whole_sign_bodily_sextile_or_trine",
            "void_policy": "traditional_planets_exact_perfection_sign_bound",
            "via_combusta_policy": "tropical_half_open_195_to_225",
        }
        for name, value in fixed.items():
            if getattr(self, name) != value:
                raise ValueError(f"{name} is fixed for this admitted profile")


RAMESEY_MOON_CONDITION_V1 = RameseyMoonConditionPolicy()


@dataclass(frozen=True, slots=True)
class RameseyMoonConditionEvaluation:
    """Transparent evaluation of ten gates and a separate remedy witness."""

    jd_ut: float
    profile_id: str
    profile_version: str
    status: RameseyMoonConditionStatus
    rules: tuple[RameseyRuleWitness, ...]
    remedies: tuple[RameseyRemedyWitness, ...]
    position_product: str
    reader_provenance: str
    latitude: float
    longitude: float
    requested_house_system: str | None
    effective_house_system: str | None
    house_fallback: bool | None
    election_class: str = "ephemeral"
    matter_scope: str = (
        "Ramesey's ten Moon impediments plus non-erasing contingency instruction"
    )
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
        if self.complete_electional_judgement:
            raise ValueError("this bounded profile is never a complete electional judgement")
        if len(self.rules) != 10:
            raise ValueError("Ramesey evaluation must contain exactly ten rules")
        if tuple(rule.source_order for rule in self.rules) != tuple(range(1, 11)):
            raise ValueError("Ramesey rules must remain in printed source order")
        if len(self.remedies) != 1:
            raise ValueError("Ramesey v1 must preserve exactly one separate remedy witness")
        triggered_rule_ids = tuple(
            rule.rule_id for rule in self.rules if rule.state is RameseyRuleState.TRIGGERED
        )
        not_evaluable = any(
            rule.state is RameseyRuleState.NOT_EVALUABLE for rule in self.rules
        )
        remedy = self.remedies[0]
        if remedy.triggering_rule_ids != triggered_rule_ids:
            raise ValueError("remedy trigger identity must match the visible gate witnesses")
        expected_remedy_applicability = (
            RameseyRemedyApplicability.APPLICABLE
            if triggered_rule_ids and remedy.unavoidable_time_urgency is True
            else RameseyRemedyApplicability.NOT_APPLICABLE
            if (triggered_rule_ids and remedy.unavoidable_time_urgency is False)
            or (not triggered_rule_ids and not not_evaluable)
            else RameseyRemedyApplicability.INDETERMINATE
        )
        if remedy.applicability is not expected_remedy_applicability:
            raise ValueError(
                "remedy applicability must derive from gates and unavoidable-time context"
            )
        expected_status = (
            RameseyMoonConditionStatus.INDETERMINATE
            if any(rule.state is RameseyRuleState.NOT_EVALUABLE for rule in self.rules)
            else RameseyMoonConditionStatus.TRIGGERED
            if any(rule.state is RameseyRuleState.TRIGGERED for rule in self.rules)
            else RameseyMoonConditionStatus.CLEAR
        )
        if self.status is not expected_status:
            raise ValueError("evaluation status must be derived from the ten rule witnesses")
        if self.election_class != "ephemeral":
            raise ValueError("Ramesey v1 election_class is fixed to ephemeral")
        if self.advice_language != "not_provided" or self.recommendation_language != "not_provided":
            raise ValueError("this profile cannot emit advice or recommendation language")

    @property
    def triggered_rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules if rule.state is RameseyRuleState.TRIGGERED)

    @property
    def not_evaluable_rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules if rule.state is RameseyRuleState.NOT_EVALUABLE)


_SOURCE = "Ramesey 1654, Astrologia Restaurata, Book III, ch. II, p. 127"
_REMEDY_SOURCE = (
    "Ramesey 1654, Astrologia Restaurata, Book III, ch. II, pp. 127-128"
)
_REMEDY_INSTRUCTIONS = (
    "Keep an impeded Moon cadent and without bodily or aspectual relation to the Ascendant.",
    "Place a fortune in the Ascendant or in good aspect with it.",
    "Fortify the Ascendant cusp, its lord, and the lord of the hour.",
)
_REMEDY_UNCOMPUTED_REQUIREMENTS = (
    "Ramesey-specific body/aspect relation policy for the Moon and Ascendant",
    "Jupiter and Venus placement plus Ramesey-specific good-aspect policy to the Ascendant",
    "source-specific fortification judgements for the Ascendant cusp, its lord, and hour lord",
)
_POLICY_REFERENCES = {
    "required_chart_input": "Moira ramesey_moon_condition_v1 input contract",
    "ramesey_explicit_12_degree_combustion": _SOURCE,
    "ordinal_degree_half_open": f"{_SOURCE}; Moira ordinal half-open encoding",
    "ramesey_combined_moieties": (
        "Ramesey 1654, Book II, planetary chapters pp. 53-69 and "
        "application/separation definitions pp. 109-111"
    ),
    "true_ecliptic_crossing_node_and_opposition": (
        "Ramesey 1654, Book II, ch. XVII, p. 76; Moira geometric true-node binding"
    ),
    "ramesey_terminal_malefic_term": (
        "Ramesey 1654, Book II, ch. XIII, pp. 71-72"
    ),
    "caller_declared_quadrant_houses_3_6_9_12": (
        "Ramesey 1654, Book II house/angle doctrine; explicit Moira house-system input"
    ),
    "whole_sign_bodily_sextile_or_trine": (
        f"{_SOURCE}; explicit Moira whole-sign beholding binding"
    ),
    _POSITION_PRODUCT: (
        f"{_SOURCE}; Moira chart apparent-geocentric longitude and "
        "PlanetData astrometric-geocentric rate products"
    ),
    "traditional_planets_exact_perfection_sign_bound": (
        "Ramesey 1654, Book II p. 111 and Book III p. 127; "
        "explicit Moira exact-perfection binding"
    ),
    "tropical_half_open_195_to_225": f"{_SOURCE}; Moira half-open endpoint encoding",
}
_SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
_SLOW_THRESHOLD = 13.0 + 10.0 / 60.0 + 36.0 / 3600.0

# Ramesey, Book II, ch. XIII, printed pp. 71-72: the final term is assigned to
# an infortune in every sign except Leo (where Jupiter is last).  The starts
# below are 30 degrees minus the printed width of that terminal malefic term.
# Half-open intervals make the boundary behavior explicit.
_TERMINAL_MALEFIC_TERMS: dict[str, tuple[float, str]] = {
    "Aries": (26.0, Body.SATURN),
    "Taurus": (24.0, Body.MARS),
    "Gemini": (26.0, Body.SATURN),
    "Cancer": (27.0, Body.SATURN),
    "Virgo": (24.0, Body.SATURN),
    "Libra": (24.0, Body.MARS),
    "Scorpio": (27.0, Body.SATURN),
    "Sagittarius": (25.0, Body.MARS),
    "Capricorn": (25.0, Body.MARS),
    "Aquarius": (25.0, Body.MARS),
    "Pisces": (25.0, Body.SATURN),
}


def _measurement(
    name: str,
    value: float | str | bool | None,
    *,
    units: str | None = None,
    comparison: str | None = None,
    threshold: float | str | bool | None = None,
) -> RameseyMeasurement:
    return RameseyMeasurement(name, value, units, comparison, threshold)


def _clause(
    clause_id: str,
    state: RameseyRuleState,
    policy_id: str,
    measurements: tuple[RameseyMeasurement, ...],
    explanation: str,
) -> RameseyClauseWitness:
    reference = _POLICY_REFERENCES.get(policy_id)
    if reference is None:
        raise ValueError(f"no authority reference registered for policy {policy_id!r}")
    return RameseyClauseWitness(
        clause_id,
        state,
        policy_id,
        reference,
        measurements,
        explanation,
    )


def _missing(clause_id: str, policy_id: str, requirement: str) -> RameseyClauseWitness:
    return _clause(
        clause_id,
        RameseyRuleState.NOT_EVALUABLE,
        policy_id,
        (_measurement("missing_input", requirement),),
        f"Required input is absent: {requirement}.",
    )


def _or_state(clauses: tuple[RameseyClauseWitness, ...]) -> RameseyRuleState:
    if any(clause.state is RameseyRuleState.TRIGGERED for clause in clauses):
        return RameseyRuleState.TRIGGERED
    if any(clause.state is RameseyRuleState.NOT_EVALUABLE for clause in clauses):
        return RameseyRuleState.NOT_EVALUABLE
    return RameseyRuleState.CLEAR


def _rule(
    rule_id: str,
    order: int,
    clauses: tuple[RameseyClauseWitness, ...],
    *,
    modifiers: tuple[str, ...] = (),
) -> RameseyRuleWitness:
    return RameseyRuleWitness(
        rule_id=rule_id,
        source_order=order,
        state=_or_state(clauses),
        clauses=clauses,
        source_reference=_SOURCE,
        modifiers=modifiers,
    )


def _remedy_witness(
    rules: tuple[RameseyRuleWitness, ...],
    unavoidable_time_urgency: bool | None,
) -> RameseyRemedyWitness:
    triggering_rule_ids = tuple(
        rule.rule_id for rule in rules if rule.state is RameseyRuleState.TRIGGERED
    )
    has_indeterminate_gate = any(
        rule.state is RameseyRuleState.NOT_EVALUABLE for rule in rules
    )
    if triggering_rule_ids:
        applicability = (
            RameseyRemedyApplicability.APPLICABLE
            if unavoidable_time_urgency is True
            else RameseyRemedyApplicability.NOT_APPLICABLE
            if unavoidable_time_urgency is False
            else RameseyRemedyApplicability.INDETERMINATE
        )
    else:
        applicability = (
            RameseyRemedyApplicability.INDETERMINATE
            if has_indeterminate_gate
            else RameseyRemedyApplicability.NOT_APPLICABLE
        )
    return RameseyRemedyWitness(
        remedy_id="unavoidable_impeded_moon_arrangement",
        applicability=applicability,
        triggering_rule_ids=triggering_rule_ids,
        unavoidable_time_urgency=unavoidable_time_urgency,
        source_reference=_REMEDY_SOURCE,
        instructions=_REMEDY_INSTRUCTIONS,
        uncomputed_requirements=_REMEDY_UNCOMPUTED_REQUIREMENTS,
    )


def _shortest_distance(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _orb(policy: RameseyMoonConditionPolicy, left: str, right: str) -> float:
    orbs = dict(policy.planetary_full_orbs)
    return (orbs[left] + orbs[right]) / 2.0


def _aspect_clause(
    moon_longitude: float,
    body_name: str,
    body_longitude: float,
    target: float,
    aspect_name: str,
    policy: RameseyMoonConditionPolicy,
) -> RameseyClauseWitness:
    separation = _shortest_distance(moon_longitude, body_longitude)
    error = abs(separation - target)
    threshold = _orb(policy, Body.MOON, body_name)
    triggered = error <= threshold
    return _clause(
        f"moon_{aspect_name.lower()}_{body_name.lower()}",
        RameseyRuleState.TRIGGERED if triggered else RameseyRuleState.CLEAR,
        policy.aspect_policy,
        (
            _measurement("separation", separation, units="degrees"),
            _measurement(
                "aspect_error",
                error,
                units="degrees",
                comparison="<=",
                threshold=threshold,
            ),
        ),
        f"Moon-{body_name} {aspect_name.lower()} tested with combined Ramesey moieties.",
    )


def _moon_rule_missing(order: int, rule_id: str) -> RameseyRuleWitness:
    return _rule(
        rule_id,
        order,
        (_missing("moon_position", "required_chart_input", Body.MOON),),
    )


def evaluate_ramesey_moon_condition(
    chart: ChartContext,
    *,
    void_of_course: bool | None,
    unavoidable_time_urgency: bool | None = None,
    position_product: str,
    reader_provenance: str,
    policy: RameseyMoonConditionPolicy = RAMESEY_MOON_CONDITION_V1,
) -> RameseyMoonConditionEvaluation:
    """Evaluate the ten Ramesey Moon impediments from an existing chart.

    ``position_product`` is an explicit provenance attestation because the
    generic ``ChartContext`` vessel predates correction-regime metadata.
    ``void_of_course`` is explicit because a chart snapshot cannot prove that
    no aspect perfects before the Moon leaves its sign.  Pass ``None`` when
    that forward-search product is unavailable; Rule 10 and the overall result
    then remain honestly indeterminate.  ``ramesey_moon_condition_at`` obtains
    the admitted sign-bounded product automatically.

    ``unavoidable_time_urgency`` is the source's context condition for its
    separate contingency instruction.  ``None`` preserves that applicability
    as indeterminate.  The instruction witness never changes a gate state.
    """

    if not isinstance(policy, RameseyMoonConditionPolicy):
        raise TypeError("policy must be a RameseyMoonConditionPolicy")
    if position_product != policy.position_product:
        raise ValueError(
            "position_product does not match the admitted Ramesey v1 product"
        )
    if not reader_provenance:
        raise ValueError("reader_provenance must be a non-empty string")
    if unavoidable_time_urgency is not None and not isinstance(
        unavoidable_time_urgency, bool
    ):
        raise TypeError("unavoidable_time_urgency must be bool or None")

    moon = chart.planets.get(Body.MOON)
    sun = chart.planets.get(Body.SUN)
    mars = chart.planets.get(Body.MARS)
    saturn = chart.planets.get(Body.SATURN)
    true_node = chart.nodes.get(Body.TRUE_NODE)
    topocentric = tuple(
        body.name
        for body in (moon, sun, mars, saturn)
        if body is not None and body.is_topocentric
    )
    if topocentric:
        raise ValueError(
            "Ramesey v1 requires geocentric planetary positions; "
            f"topocentric inputs found for {', '.join(topocentric)}"
        )
    rules: list[RameseyRuleWitness] = []

    # 1. Combustion within the source's explicit 12-degree distance.
    if moon is None:
        rules.append(_moon_rule_missing(1, "moon_combust_sun_12deg"))
    elif sun is None:
        rules.append(_rule("moon_combust_sun_12deg", 1, (_missing("sun_distance", "required_chart_input", Body.SUN),)))
    else:
        separation = _shortest_distance(moon.longitude, sun.longitude)
        signed = (moon.longitude - sun.longitude + 180.0) % 360.0 - 180.0
        distance_rate = math.copysign(1.0, signed) * (moon.speed - sun.speed) if signed else 0.0
        phase = "exact" if separation < 1e-12 else ("applying" if distance_rate < 0.0 else "separating" if distance_rate > 0.0 else "stationary_relative")
        triggered = separation <= 12.0
        clause = _clause(
            "moon_within_12deg_sun",
            RameseyRuleState.TRIGGERED if triggered else RameseyRuleState.CLEAR,
            "ramesey_explicit_12_degree_combustion",
            (
                _measurement("separation", separation, units="degrees", comparison="<=", threshold=12.0),
                _measurement("phase", phase),
                _measurement("separation_rate", distance_rate, units="degrees/day"),
            ),
            "Shortest Sun-Moon longitude separation; equality is included.",
        )
        modifiers = ("Applying is described by Ramesey as the more afflicted condition.",) if triggered else ()
        rules.append(_rule("moon_combust_sun_12deg", 1, (clause,), modifiers=modifiers))

    # 2. "Third degree" is ordinal: Scorpio [2, 3) degrees.
    if moon is None:
        rules.append(_moon_rule_missing(2, "moon_in_third_degree_scorpio"))
    else:
        triggered = moon.sign == "Scorpio" and 2.0 <= moon.sign_degree < 3.0
        rules.append(_rule(
            "moon_in_third_degree_scorpio",
            2,
            (_clause(
                "ordinal_third_degree_scorpio",
                RameseyRuleState.TRIGGERED if triggered else RameseyRuleState.CLEAR,
                policy.degree_policy,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("degree_in_sign", moon.sign_degree, units="degrees", comparison="in", threshold="[2, 3) Scorpio"),
                ),
                "Historical ordinal degree encoded as a zero-based half-open interval.",
            ),),
        ))

    # 3. Opposition under Ramesey's Sun/Moon combined moieties (13.5 degrees).
    if moon is None:
        rules.append(_moon_rule_missing(3, "moon_opposition_sun"))
    elif sun is None:
        rules.append(_rule("moon_opposition_sun", 3, (_missing("sun_opposition", policy.aspect_policy, Body.SUN),)))
    else:
        rules.append(_rule(
            "moon_opposition_sun",
            3,
            (_aspect_clause(moon.longitude, Body.SUN, sun.longitude, 180.0, "Opposition", policy),),
        ))

    # 4. Conjunction, square, or opposition to Saturn or Mars.  Six clauses
    # remain visible rather than being collapsed into one boolean.
    hard_clauses: list[RameseyClauseWitness] = []
    if moon is None:
        hard_clauses.append(_missing("moon_hard_aspects", policy.aspect_policy, Body.MOON))
    else:
        for body_name, body in ((Body.SATURN, saturn), (Body.MARS, mars)):
            if body is None:
                hard_clauses.append(_missing(f"{body_name.lower()}_hard_aspects", policy.aspect_policy, body_name))
                continue
            for target, name in ((0.0, "Conjunction"), (90.0, "Square"), (180.0, "Opposition")):
                hard_clauses.append(_aspect_clause(moon.longitude, body_name, body.longitude, target, name, policy))
    rules.append(_rule("moon_joined_or_hard_aspect_malefic", 4, tuple(hard_clauses)))

    # 5. The source defines the Dragon's Head/Tail as actual ecliptic crossing
    # places; Moira binds this to the true ascending node and its opposition.
    if moon is None:
        rules.append(_moon_rule_missing(5, "moon_near_lunar_node_12deg"))
    elif true_node is None:
        rules.append(_rule("moon_near_lunar_node_12deg", 5, (_missing("true_node_distance", policy.node_policy, Body.TRUE_NODE),)))
    else:
        head_distance = _shortest_distance(moon.longitude, true_node.longitude)
        tail_longitude = (true_node.longitude + 180.0) % 360.0
        tail_distance = _shortest_distance(moon.longitude, tail_longitude)
        node_clauses = tuple(
            _clause(
                f"moon_within_12deg_{name}",
                RameseyRuleState.TRIGGERED if distance <= 12.0 else RameseyRuleState.CLEAR,
                policy.node_policy,
                (
                    _measurement("node_longitude", longitude, units="degrees"),
                    _measurement("separation", distance, units="degrees", comparison="<=", threshold=12.0),
                ),
                "Shortest tropical longitude separation; equality is included.",
            )
            for name, longitude, distance in (
                ("head", true_node.longitude, head_distance),
                ("tail", tail_longitude, tail_distance),
            )
        )
        rules.append(_rule("moon_near_lunar_node_12deg", 5, node_clauses))

    # 6. The source's "infortune" is the ruler of the terminal term, not the
    # accidental presence of a transiting malefic somewhere in the sign.
    if moon is None:
        rules.append(_moon_rule_missing(6, "moon_latter_degrees_with_infortune"))
    else:
        terminal = _TERMINAL_MALEFIC_TERMS.get(moon.sign)
        triggered = terminal is not None and moon.sign_degree >= terminal[0]
        start, ruler = terminal if terminal is not None else (None, Body.JUPITER)
        rules.append(_rule(
            "moon_latter_degrees_with_infortune",
            6,
            (_clause(
                "terminal_term_ruled_by_infortune",
                RameseyRuleState.TRIGGERED if triggered else RameseyRuleState.CLEAR,
                policy.latter_degrees_policy,
                (
                    _measurement("moon_sign", moon.sign),
                    _measurement("degree_in_sign", moon.sign_degree, units="degrees"),
                    _measurement("terminal_term_start", start, units="degrees", comparison=">=", threshold=start),
                    _measurement("terminal_term_ruler", ruler),
                ),
                "Ramesey's printed terminal term; Leo is clear because Jupiter, not an infortune, is terminal.",
            ),),
        ))

    # 7. Three-valued OR: either a proved cadent placement or the via combusta
    # triggers the rule.  A via trigger remains decisive if houses are absent.
    if moon is None:
        rules.append(_moon_rule_missing(7, "moon_cadent_or_via_combusta"))
    else:
        via = 195.0 <= moon.longitude < 225.0
        via_clause = _clause(
            "moon_in_via_combusta",
            RameseyRuleState.TRIGGERED if via else RameseyRuleState.CLEAR,
            policy.via_combusta_policy,
            (_measurement("moon_longitude", moon.longitude, units="degrees", comparison="in", threshold="[195, 225)"),),
            "Last 15 degrees of Libra through first 15 degrees of Scorpio.",
        )
        if chart.houses is None:
            cadent_clause = _missing("moon_cadent", policy.cadency_policy, "quadrant house cusps")
        elif not chart.houses.is_quadrant_system:
            cadent_clause = _clause(
                "moon_cadent",
                RameseyRuleState.NOT_EVALUABLE,
                policy.cadency_policy,
                (
                    _measurement("requested_house_system", chart.houses.system),
                    _measurement("effective_house_system", chart.houses.effective_system),
                ),
                "The selected effective house system is not a quadrant system.",
            )
        else:
            placement = assign_house(moon.longitude, chart.houses)
            angularity = describe_angularity(placement)
            cadent = angularity.category is HouseAngularity.CADENT
            cadent_clause = _clause(
                "moon_cadent",
                RameseyRuleState.TRIGGERED if cadent else RameseyRuleState.CLEAR,
                policy.cadency_policy,
                (
                    _measurement("house", placement.house),
                    _measurement("angularity", angularity.category.value),
                    _measurement("requested_house_system", chart.houses.system),
                    _measurement("effective_house_system", chart.houses.effective_system),
                    _measurement("house_fallback", chart.houses.fallback),
                ),
                "Cadency is houses 3, 6, 9, or 12 in the explicit effective quadrant figure.",
            )
        rules.append(_rule(
            "moon_cadent_or_via_combusta",
            7,
            (cadent_clause, via_clause),
            modifiers=("Ramesey calls the via-combusta clause the worst impediment and names matter-specific contexts.",) if via else (),
        ))

    # 8. "Own house" is Cancer.  Beholding here is sign relationship: bodily
    # presence, sextile, or trine.  Capricorn and square signs stay visible as
    # their own source clauses.
    if moon is None:
        rules.append(_moon_rule_missing(8, "moon_detriment_or_not_beholding_cancer"))
    else:
        sign_index = _SIGNS.index(moon.sign)
        favorable = sign_index in (1, 3, 5, 7, 11)  # Taurus, Cancer, Virgo, Scorpio, Pisces
        clauses = (
            _clause(
                "moon_in_capricorn_detriment",
                RameseyRuleState.TRIGGERED if moon.sign == "Capricorn" else RameseyRuleState.CLEAR,
                policy.cancer_beholding_policy,
                (_measurement("moon_sign", moon.sign, comparison="==", threshold="Capricorn"),),
                "Capricorn is the Moon's detriment in the source rule.",
            ),
            _clause(
                "moon_sign_quartile_cancer",
                RameseyRuleState.TRIGGERED if moon.sign in ("Aries", "Libra") else RameseyRuleState.CLEAR,
                policy.cancer_beholding_policy,
                (_measurement("moon_sign", moon.sign, comparison="in", threshold="Aries or Libra"),),
                "Aries and Libra are whole-sign squares to Cancer.",
            ),
            _clause(
                "moon_lacks_bodily_sextile_or_trine_to_cancer",
                RameseyRuleState.CLEAR if favorable else RameseyRuleState.TRIGGERED,
                policy.cancer_beholding_policy,
                (_measurement("moon_sign", moon.sign), _measurement("favorable_beholding", favorable)),
                "Cancer bodily, Taurus/Virgo sextile, and Scorpio/Pisces trine are favorable beholding.",
            ),
        )
        rules.append(_rule("moon_detriment_or_not_beholding_cancer", 8, clauses))

    # 9. PlanetData's instantaneous astrometric geocentric longitude rate.
    # The source's strict "less than" makes equality clear.
    if moon is None:
        rules.append(_moon_rule_missing(9, "moon_slow_below_ramesey_mean"))
    else:
        slow = moon.speed < _SLOW_THRESHOLD
        rules.append(_rule(
            "moon_slow_below_ramesey_mean",
            9,
            (_clause(
                "moon_speed_below_13d10m36s",
                RameseyRuleState.TRIGGERED if slow else RameseyRuleState.CLEAR,
                policy.position_product,
                (_measurement("moon_longitude_rate", moon.speed, units="degrees/day", comparison="<", threshold=_SLOW_THRESHOLD),),
                "Strict comparison with Ramesey's stated mean motion.",
            ),),
        ))

    # 10. Forward-search result supplied separately from the chart snapshot.
    if void_of_course is None:
        voc_clause = _missing("moon_void_until_sign_ingress", policy.void_policy, "sign-bounded forward aspect search")
    else:
        voc_clause = _clause(
            "moon_void_until_sign_ingress",
            RameseyRuleState.TRIGGERED if void_of_course else RameseyRuleState.CLEAR,
            policy.void_policy,
            (_measurement("void_of_course", void_of_course, comparison="==", threshold=True),),
            "No exact Ptolemaic aspect perfection to a traditional planet before sign ingress.",
        )
    rules.append(_rule("moon_void_ramesey_sign_bound", 10, (voc_clause,)))

    rule_tuple = tuple(rules)
    if any(rule.state is RameseyRuleState.NOT_EVALUABLE for rule in rule_tuple):
        status = RameseyMoonConditionStatus.INDETERMINATE
    elif any(rule.state is RameseyRuleState.TRIGGERED for rule in rule_tuple):
        status = RameseyMoonConditionStatus.TRIGGERED
    else:
        status = RameseyMoonConditionStatus.CLEAR

    houses = chart.houses
    return RameseyMoonConditionEvaluation(
        jd_ut=chart.jd_ut,
        profile_id=policy.profile_id,
        profile_version=policy.profile_version,
        status=status,
        rules=rule_tuple,
        remedies=(_remedy_witness(rule_tuple, unavoidable_time_urgency),),
        position_product=policy.position_product,
        reader_provenance=reader_provenance,
        latitude=chart.latitude,
        longitude=chart.longitude,
        requested_house_system=houses.system if houses else None,
        effective_house_system=houses.effective_system if houses else None,
        house_fallback=houses.fallback if houses else None,
    )


def ramesey_moon_condition_at(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    unavoidable_time_urgency: bool | None = None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    policy: RameseyMoonConditionPolicy = RAMESEY_MOON_CONDITION_V1,
) -> RameseyMoonConditionEvaluation:
    """Build the admitted astronomical inputs and evaluate the profile.

    ``house_system`` is deliberately required: Ramesey does not identify a
    single historical cusp algorithm, so Moira refuses to hide that material
    choice.  The evaluator accepts only a quadrant system for the cadency
    clause and records requested/effective/fallback truth in the result.
    """

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
    voc = is_void_of_course(jd_ut, reader=resolved_reader, modern=False)
    reader_path = getattr(resolved_reader, "path", None)
    reader_provenance = (
        str(reader_path)
        if reader_path is not None
        else f"{type(resolved_reader).__module__}.{type(resolved_reader).__qualname__}"
    )
    return evaluate_ramesey_moon_condition(
        chart,
        void_of_course=voc,
        unavoidable_time_urgency=unavoidable_time_urgency,
        position_product=policy.position_product,
        reader_provenance=reader_provenance,
        policy=policy,
    )


class SahlRuleState(str, Enum):
    """Truth state for one clause or impediment in Sahl's ten-rule list."""

    CLEAR = "clear"
    TRIGGERED = "triggered"
    NOT_EVALUABLE = "not_evaluable"


class SahlMoonConditionStatus(str, Enum):
    """Non-scored summary of the Sahl Moon-condition profile."""

    CLEAR = "clear_of_profile_impediments"
    TRIGGERED = "one_or_more_profile_impediments"
    INDETERMINATE = "indeterminate"


class SahlBurntPathVariant(str, Enum):
    """Named interpretations of Sahl's non-numeric burnt-path wording."""

    UNRESOLVED_SOURCE_WORDING = "unresolved_source_wording"
    FALL_DEGREES = "fall_degrees_19_libra_to_3_scorpio"
    FIFTEEN_DEGREES = "fifteen_libra_to_fifteen_scorpio"


class SahlEighthRuleVariant(str, Enum):
    """Textual branch used for the first clause of Sahl's eighth rule."""

    ARABIC_AL_RIJAL_TWELFTH_PART = "arabic_al_rijal_twelfth_part"
    LATIN_TWELFTH_SIGN = "latin_twelfth_sign"


@dataclass(frozen=True, slots=True)
class SahlMeasurement:
    """One visible input, threshold, or interpretive selection."""

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
class SahlClauseWitness:
    """Visible derivation of one clause in a Sahl impediment."""

    clause_id: str
    state: SahlRuleState
    policy_id: str
    policy_reference: str
    measurements: tuple[SahlMeasurement, ...]
    explanation: str

    def __post_init__(self) -> None:
        if not self.clause_id or not self.policy_id or not self.policy_reference:
            raise ValueError("clause identity, policy, and authority must be visible")
        if not self.measurements:
            raise ValueError("a clause witness must preserve at least one measurement")
        if not self.explanation:
            raise ValueError("clause explanation must be non-empty")


@dataclass(frozen=True, slots=True)
class SahlRuleWitness:
    """One Sahl impediment in printed order with every compound clause."""

    rule_id: str
    source_order: int
    state: SahlRuleState
    clauses: tuple[SahlClauseWitness, ...]
    source_reference: str
    modifiers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= self.source_order <= 10:
            raise ValueError("source_order must be in [1, 10]")
        if not self.clauses:
            raise ValueError("a rule witness must preserve at least one clause")
        expected = (
            SahlRuleState.TRIGGERED
            if any(clause.state is SahlRuleState.TRIGGERED for clause in self.clauses)
            else SahlRuleState.NOT_EVALUABLE
            if any(clause.state is SahlRuleState.NOT_EVALUABLE for clause in self.clauses)
            else SahlRuleState.CLEAR
        )
        if self.state is not expected:
            raise ValueError("rule state must be derived from its visible clauses")
        if not self.rule_id or not self.source_reference:
            raise ValueError("rule identity and source reference must be visible")


_SAHL_FULL_ORBS: tuple[tuple[str, float], ...] = (
    (Body.SATURN, 9.0),
    (Body.JUPITER, 9.0),
    (Body.MARS, 8.0),
    (Body.SUN, 15.0),
    (Body.VENUS, 7.0),
    (Body.MERCURY, 7.0),
    (Body.MOON, 12.0),
)


@dataclass(frozen=True, slots=True)
class SahlMoonConditionPolicy:
    """Explicit computational doctrine for ``sahl_moon_condition_v1``."""

    profile_id: str = "sahl_moon_condition_v1"
    profile_version: str = "1.0.0"
    degree_policy: str = "ordinal_degree_half_open"
    aspect_policy: str = "sahl_whole_sign_rays_and_arabic_moiety_body_join"
    planetary_full_orbs: tuple[tuple[str, float], ...] = _SAHL_FULL_ORBS
    node_policy: str = "true_ecliptic_crossing_node_and_opposition"
    bound_policy: str = "explicit_egyptian_bounds_binding"
    cadency_policy: str = "caller_declared_quadrant_houses_3_6_9_12"
    burnt_path_variant: SahlBurntPathVariant = (
        SahlBurntPathVariant.UNRESOLVED_SOURCE_WORDING
    )
    eighth_rule_variant: SahlEighthRuleVariant = (
        SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART
    )
    twelfth_part_policy: str = "sign_divided_into_twelve_equal_2d30m_parts"
    position_product: str = _POSITION_PRODUCT
    void_policy: str = "medieval_exact_connection_sign_bound"

    def __post_init__(self) -> None:
        if self.profile_id != "sahl_moon_condition_v1":
            raise ValueError("profile_id is fixed for this admitted profile")
        if self.profile_version != "1.0.0":
            raise ValueError("profile_version is fixed for this admitted profile")
        if self.planetary_full_orbs != _SAHL_FULL_ORBS:
            raise ValueError("Sahl v1 planetary orbs are source-fixed")
        if not isinstance(self.burnt_path_variant, SahlBurntPathVariant):
            raise TypeError("burnt_path_variant must be a SahlBurntPathVariant")
        if not isinstance(self.eighth_rule_variant, SahlEighthRuleVariant):
            raise TypeError("eighth_rule_variant must be a SahlEighthRuleVariant")
        fixed = {
            "degree_policy": "ordinal_degree_half_open",
            "aspect_policy": "sahl_whole_sign_rays_and_arabic_moiety_body_join",
            "node_policy": "true_ecliptic_crossing_node_and_opposition",
            "bound_policy": "explicit_egyptian_bounds_binding",
            "cadency_policy": "caller_declared_quadrant_houses_3_6_9_12",
            "twelfth_part_policy": "sign_divided_into_twelve_equal_2d30m_parts",
            "position_product": _POSITION_PRODUCT,
            "void_policy": "medieval_exact_connection_sign_bound",
        }
        for name, value in fixed.items():
            if getattr(self, name) != value:
                raise ValueError(f"{name} is fixed for this admitted profile")


SAHL_MOON_CONDITION_V1 = SahlMoonConditionPolicy()


@dataclass(frozen=True, slots=True)
class SahlMoonConditionEvaluation:
    """Transparent, non-scored evaluation of Sahl's ten impediments."""

    jd_ut: float
    profile_id: str
    profile_version: str
    status: SahlMoonConditionStatus
    rules: tuple[SahlRuleWitness, ...]
    position_product: str
    reader_provenance: str
    latitude: float
    longitude: float
    requested_house_system: str | None
    effective_house_system: str | None
    house_fallback: bool | None
    burnt_path_variant: SahlBurntPathVariant
    eighth_rule_variant: SahlEighthRuleVariant
    election_class: str = "ephemeral"
    matter_scope: str = "Sahl bin Bishr's ten Moon impediments in On Elections section 22"
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
        if len(self.rules) != 10:
            raise ValueError("Sahl evaluation must contain exactly ten rules")
        if tuple(rule.source_order for rule in self.rules) != tuple(range(1, 11)):
            raise ValueError("Sahl rules must remain in printed source order")
        expected_status = (
            SahlMoonConditionStatus.TRIGGERED
            if any(rule.state is SahlRuleState.TRIGGERED for rule in self.rules)
            else SahlMoonConditionStatus.INDETERMINATE
            if any(rule.state is SahlRuleState.NOT_EVALUABLE for rule in self.rules)
            else SahlMoonConditionStatus.CLEAR
        )
        if self.status is not expected_status:
            raise ValueError("evaluation status must derive from the ten rule witnesses")
        if self.election_class != "ephemeral" or self.complete_electional_judgement:
            raise ValueError("Sahl v1 is an ephemeral bounded profile, not a full judgement")
        if self.advice_language != "not_provided" or self.recommendation_language != "not_provided":
            raise ValueError("this profile cannot emit advice or recommendation language")

    @property
    def triggered_rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules if rule.state is SahlRuleState.TRIGGERED)

    @property
    def not_evaluable_rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules if rule.state is SahlRuleState.NOT_EVALUABLE)


_SAHL_SOURCE = (
    "Sahl bin Bishr, On Elections, section 22b-g, Benjamin Dykes trans., "
    "printed pp. 99-101"
)
_SAHL_RULE_SOURCES = {
    1: f"{_SAHL_SOURCE}, section 22b",
    2: f"{_SAHL_SOURCE}, section 22b",
    3: f"{_SAHL_SOURCE}, section 22b",
    4: f"{_SAHL_SOURCE}, section 22c",
    5: f"{_SAHL_SOURCE}, section 22c",
    6: f"{_SAHL_SOURCE}, section 22c",
    7: f"{_SAHL_SOURCE}, section 22d",
    8: f"{_SAHL_SOURCE}, section 22e and note 70",
    9: f"{_SAHL_SOURCE}, section 22f",
    10: f"{_SAHL_SOURCE}, section 22g",
}
_SAHL_GLOSSARY = (
    "Dykes, Choices & Inceptions glossary, printed pp. 409-415 and 426"
)
_SAHL_POLICY_REFERENCES = {
    "required_chart_input": "Moira sahl_moon_condition_v1 input contract",
    "sahl_explicit_12_degree_burning": _SAHL_RULE_SOURCES[1],
    "ordinal_degree_half_open": f"{_SAHL_RULE_SOURCES[2]}; Moira ordinal half-open encoding",
    "sahl_whole_sign_rays_and_arabic_moiety_body_join": (
        f"{_SAHL_RULE_SOURCES[3]}; {_SAHL_GLOSSARY}; Dykes introduction printed p. 39"
    ),
    "true_ecliptic_crossing_node_and_opposition": (
        f"{_SAHL_RULE_SOURCES[5]}; explicit Moira geometric true-node binding"
    ),
    "explicit_egyptian_bounds_binding": (
        f"{_SAHL_RULE_SOURCES[6]}; explicit Moira Egyptian-bounds selection because Sahl does not name a table"
    ),
    "caller_declared_quadrant_houses_3_6_9_12": (
        f"{_SAHL_RULE_SOURCES[7]}; {_SAHL_GLOSSARY}; explicit Moira house-system input"
    ),
    SahlBurntPathVariant.UNRESOLVED_SOURCE_WORDING.value: (
        f"{_SAHL_RULE_SOURCES[7]}; source says only end of Libra and beginning of Scorpio"
    ),
    SahlBurntPathVariant.FALL_DEGREES.value: (
        f"{_SAHL_RULE_SOURCES[7]}; {_SAHL_GLOSSARY} fall-degree interpretation"
    ),
    SahlBurntPathVariant.FIFTEEN_DEGREES.value: (
        f"{_SAHL_RULE_SOURCES[7]}; {_SAHL_GLOSSARY} 15 Libra to 15 Scorpio interpretation"
    ),
    SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART.value: (
        f"{_SAHL_RULE_SOURCES[8]}; Dykes-preferred Arabic/al-Rijal reading"
    ),
    SahlEighthRuleVariant.LATIN_TWELFTH_SIGN.value: (
        f"{_SAHL_RULE_SOURCES[8]}; literal Latin reading retained as a named variant"
    ),
    "sign_divided_into_twelve_equal_2d30m_parts": f"{_SAHL_GLOSSARY}, twelfth-parts",
    _POSITION_PRODUCT: (
        f"{_SAHL_SOURCE}; Moira chart apparent-geocentric longitude and "
        "PlanetData astrometric-geocentric rate products"
    ),
    "medieval_exact_connection_sign_bound": (
        f"{_SAHL_RULE_SOURCES[10]}; {_SAHL_GLOSSARY}, emptiness of the course"
    ),
}


def _sahl_measurement(
    name: str,
    value: float | str | bool | None,
    *,
    units: str | None = None,
    comparison: str | None = None,
    threshold: float | str | bool | None = None,
) -> SahlMeasurement:
    return SahlMeasurement(name, value, units, comparison, threshold)


def _sahl_clause(
    clause_id: str,
    state: SahlRuleState,
    policy_id: str,
    measurements: tuple[SahlMeasurement, ...],
    explanation: str,
) -> SahlClauseWitness:
    reference = _SAHL_POLICY_REFERENCES.get(policy_id)
    if reference is None:
        raise ValueError(f"no Sahl authority reference registered for policy {policy_id!r}")
    return SahlClauseWitness(
        clause_id,
        state,
        policy_id,
        reference,
        measurements,
        explanation,
    )


def _sahl_missing(clause_id: str, policy_id: str, requirement: str) -> SahlClauseWitness:
    return _sahl_clause(
        clause_id,
        SahlRuleState.NOT_EVALUABLE,
        policy_id,
        (_sahl_measurement("missing_input", requirement),),
        f"Required input is absent: {requirement}.",
    )


def _sahl_rule(
    rule_id: str,
    order: int,
    clauses: tuple[SahlClauseWitness, ...],
    *,
    modifiers: tuple[str, ...] = (),
) -> SahlRuleWitness:
    state = (
        SahlRuleState.TRIGGERED
        if any(clause.state is SahlRuleState.TRIGGERED for clause in clauses)
        else SahlRuleState.NOT_EVALUABLE
        if any(clause.state is SahlRuleState.NOT_EVALUABLE for clause in clauses)
        else SahlRuleState.CLEAR
    )
    return SahlRuleWitness(
        rule_id=rule_id,
        source_order=order,
        state=state,
        clauses=clauses,
        source_reference=_SAHL_RULE_SOURCES[order],
        modifiers=modifiers,
    )


def _sahl_missing_moon(order: int, rule_id: str) -> SahlRuleWitness:
    return _sahl_rule(
        rule_id,
        order,
        (_sahl_missing("moon_position", "required_chart_input", Body.MOON),),
    )


def _sahl_body_join_clause(
    moon_longitude: float,
    body_name: str,
    body_longitude: float,
    policy: SahlMoonConditionPolicy,
) -> SahlClauseWitness:
    separation = _shortest_distance(moon_longitude, body_longitude)
    orbs = dict(policy.planetary_full_orbs)
    threshold = (orbs[Body.MOON] + orbs[body_name]) / 2.0
    return _sahl_clause(
        f"moon_body_join_{body_name.lower()}",
        SahlRuleState.TRIGGERED if separation <= threshold else SahlRuleState.CLEAR,
        policy.aspect_policy,
        (
            _sahl_measurement("separation", separation, units="degrees"),
            _sahl_measurement(
                "combined_moiety",
                threshold,
                units="degrees",
                comparison="<=",
                threshold=threshold,
            ),
        ),
        "Bodily joining uses the early Perso-Arabic combined moieties and may cross a sign boundary.",
    )


def _sahl_whole_sign_ray_clause(
    moon_sign: str,
    body_name: str,
    body_sign: str,
    aspect_name: str,
    offsets: tuple[int, ...],
    policy: SahlMoonConditionPolicy,
) -> SahlClauseWitness:
    offset = (_SIGNS.index(body_sign) - _SIGNS.index(moon_sign)) % 12
    return _sahl_clause(
        f"moon_whole_sign_{aspect_name}_{body_name.lower()}",
        SahlRuleState.TRIGGERED if offset in offsets else SahlRuleState.CLEAR,
        policy.aspect_policy,
        (
            _sahl_measurement("moon_sign", moon_sign),
            _sahl_measurement(f"{body_name.lower()}_sign", body_sign),
            _sahl_measurement("sign_offset", offset, comparison="in", threshold=str(offsets)),
        ),
        f"{aspect_name.replace('_', ' ').title()} is evaluated as a whole-sign ray.",
    )


def _sahl_burnt_path_clause(
    moon_longitude: float,
    variant: SahlBurntPathVariant,
) -> SahlClauseWitness:
    if variant is SahlBurntPathVariant.UNRESOLVED_SOURCE_WORDING:
        return _sahl_clause(
            "moon_in_burnt_path",
            SahlRuleState.NOT_EVALUABLE,
            variant.value,
            (
                _sahl_measurement("moon_longitude", moon_longitude, units="degrees"),
                _sahl_measurement("burnt_path_variant", variant.value),
            ),
            "Sahl gives no numeric endpoints; no later span is silently substituted.",
        )
    start, end = (
        (199.0, 213.0)
        if variant is SahlBurntPathVariant.FALL_DEGREES
        else (195.0, 225.0)
    )
    triggered = start <= moon_longitude < end
    return _sahl_clause(
        "moon_in_burnt_path",
        SahlRuleState.TRIGGERED if triggered else SahlRuleState.CLEAR,
        variant.value,
        (
            _sahl_measurement("moon_longitude", moon_longitude, units="degrees"),
            _sahl_measurement(
                "burnt_path_interval",
                f"[{start}, {end})",
                units="degrees",
                comparison="in",
                threshold=f"[{start}, {end})",
            ),
        ),
        "The selected named interpretation is encoded as a tropical half-open interval.",
    )


def _sahl_eighth_first_clause(
    moon,
    mars,
    saturn,
    policy: SahlMoonConditionPolicy,
) -> SahlClauseWitness:
    malefics = ((Body.MARS, mars), (Body.SATURN, saturn))
    if policy.eighth_rule_variant is SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART:
        twelfth_index = (_SIGNS.index(moon.sign) + int(moon.sign_degree / 2.5)) % 12
        twelfth_sign = _SIGNS[twelfth_index]
        present = tuple(body_name for body_name, body in malefics if body is not None)
        occupied_by = tuple(
            body_name for body_name, body in malefics
            if body is not None and body.sign == twelfth_sign
        )
        state = (
            SahlRuleState.TRIGGERED
            if occupied_by
            else SahlRuleState.NOT_EVALUABLE
            if len(present) != 2
            else SahlRuleState.CLEAR
        )
        return _sahl_clause(
            "moon_twelfth_part_sign_contains_malefic",
            state,
            policy.eighth_rule_variant.value,
            (
                _sahl_measurement("moon_sign", moon.sign),
                _sahl_measurement("degree_in_sign", moon.sign_degree, units="degrees"),
                _sahl_measurement("twelfth_part_sign", twelfth_sign),
                _sahl_measurement("malefics_in_twelfth_part_sign", ",".join(occupied_by) or "none"),
            ),
            "The Moon's 2.5-degree twelfth-part names a sign; the clause tests whether Mars or Saturn occupies it.",
        )

    connected: list[str] = []
    missing: list[str] = []
    for body_name, body in malefics:
        if body is None:
            missing.append(body_name)
            continue
        orbs = dict(policy.planetary_full_orbs)
        threshold = (orbs[Body.MOON] + orbs[body_name]) / 2.0
        if _shortest_distance(moon.longitude, body.longitude) <= threshold:
            connected.append(body_name)
    state = (
        SahlRuleState.TRIGGERED
        if moon.sign == "Gemini" and connected
        else SahlRuleState.NOT_EVALUABLE
        if moon.sign == "Gemini" and missing
        else SahlRuleState.CLEAR
    )
    return _sahl_clause(
        "moon_in_latin_twelfth_sign_with_malefic",
        state,
        policy.eighth_rule_variant.value,
        (
            _sahl_measurement("moon_sign", moon.sign, comparison="==", threshold="Gemini"),
            _sahl_measurement("connected_malefics", ",".join(connected) or "none"),
        ),
        "The literal Latin variant requires the Moon in Gemini with a bodily joined malefic.",
    )


def evaluate_sahl_moon_condition(
    chart: ChartContext,
    *,
    void_of_course: bool | None,
    position_product: str,
    reader_provenance: str,
    policy: SahlMoonConditionPolicy = SAHL_MOON_CONDITION_V1,
) -> SahlMoonConditionEvaluation:
    """Evaluate Sahl's ten Moon impediments from a prebuilt chart."""

    if not isinstance(policy, SahlMoonConditionPolicy):
        raise TypeError("policy must be a SahlMoonConditionPolicy")
    if position_product != policy.position_product:
        raise ValueError("position_product does not match the admitted Sahl v1 product")
    if not reader_provenance:
        raise ValueError("reader_provenance must be a non-empty string")
    if void_of_course is not None and not isinstance(void_of_course, bool):
        raise TypeError("void_of_course must be bool or None")

    moon = chart.planets.get(Body.MOON)
    sun = chart.planets.get(Body.SUN)
    mars = chart.planets.get(Body.MARS)
    saturn = chart.planets.get(Body.SATURN)
    true_node = chart.nodes.get(Body.TRUE_NODE)
    topocentric = tuple(
        body.name
        for body in (moon, sun, mars, saturn)
        if body is not None and body.is_topocentric
    )
    if topocentric:
        raise ValueError(
            "Sahl v1 requires geocentric planetary positions; "
            f"topocentric inputs found for {', '.join(topocentric)}"
        )

    rules: list[SahlRuleWitness] = []

    if moon is None:
        rules.append(_sahl_missing_moon(1, "moon_burned_by_sun_12deg"))
    elif sun is None:
        rules.append(_sahl_rule(
            "moon_burned_by_sun_12deg", 1,
            (_sahl_missing("sun_distance", "required_chart_input", Body.SUN),),
        ))
    else:
        separation = _shortest_distance(moon.longitude, sun.longitude)
        signed = (moon.longitude - sun.longitude + 180.0) % 360.0 - 180.0
        distance_rate = math.copysign(1.0, signed) * (moon.speed - sun.speed) if signed else 0.0
        phase = "exact" if separation < 1e-12 else (
            "applying" if distance_rate < 0.0 else
            "separating" if distance_rate > 0.0 else "stationary_relative"
        )
        rules.append(_sahl_rule(
            "moon_burned_by_sun_12deg",
            1,
            (_sahl_clause(
                "moon_within_12deg_sun",
                SahlRuleState.TRIGGERED if separation <= 12.0 else SahlRuleState.CLEAR,
                "sahl_explicit_12_degree_burning",
                (
                    _sahl_measurement("separation", separation, units="degrees", comparison="<=", threshold=12.0),
                    _sahl_measurement("phase", phase),
                    _sahl_measurement("separation_rate", distance_rate, units="degrees/day"),
                ),
                "Shortest Sun-Moon longitude separation; equality is included.",
            ),),
            modifiers=("Sahl says the condition is easier after the Moon has passed the Sun.",)
            if separation <= 12.0 and phase == "separating" else (),
        ))

    if moon is None:
        rules.append(_sahl_missing_moon(2, "moon_in_degree_of_fall"))
    else:
        in_fall_degree = moon.sign == "Scorpio" and 2.0 <= moon.sign_degree < 3.0
        rules.append(_sahl_rule(
            "moon_in_degree_of_fall",
            2,
            (_sahl_clause(
                "ordinal_third_degree_scorpio",
                SahlRuleState.TRIGGERED if in_fall_degree else SahlRuleState.CLEAR,
                policy.degree_policy,
                (
                    _sahl_measurement("moon_sign", moon.sign),
                    _sahl_measurement("degree_in_sign", moon.sign_degree, units="degrees", comparison="in", threshold="[2, 3) Scorpio"),
                ),
                "The Moon's traditional fall degree is encoded as the ordinal third degree of Scorpio.",
            ),),
        ))

    if moon is None:
        rules.append(_sahl_missing_moon(3, "moon_opposition_sun"))
    elif sun is None:
        rules.append(_sahl_rule(
            "moon_opposition_sun", 3,
            (_sahl_missing("sun_opposition", "required_chart_input", Body.SUN),),
        ))
    else:
        rules.append(_sahl_rule(
            "moon_opposition_sun",
            3,
            (_sahl_whole_sign_ray_clause(
                moon.sign, Body.SUN, sun.sign, "opposition", (6,), policy
            ),),
        ))

    hard_clauses: list[SahlClauseWitness] = []
    if moon is None:
        hard_clauses.append(_sahl_missing("moon_hard_aspects", "required_chart_input", Body.MOON))
    else:
        for body_name, body in ((Body.SATURN, saturn), (Body.MARS, mars)):
            if body is None:
                hard_clauses.append(_sahl_missing(
                    f"{body_name.lower()}_hard_aspects", "required_chart_input", body_name
                ))
                continue
            hard_clauses.append(_sahl_body_join_clause(
                moon.longitude, body_name, body.longitude, policy
            ))
            hard_clauses.append(_sahl_whole_sign_ray_clause(
                moon.sign, body_name, body.sign, "square", (3, 9), policy
            ))
            hard_clauses.append(_sahl_whole_sign_ray_clause(
                moon.sign, body_name, body.sign, "opposition", (6,), policy
            ))
    rules.append(_sahl_rule("moon_joined_or_hard_ray_malefic", 4, tuple(hard_clauses)))

    if moon is None:
        rules.append(_sahl_missing_moon(5, "moon_near_lunar_node_12deg"))
    elif true_node is None:
        rules.append(_sahl_rule(
            "moon_near_lunar_node_12deg", 5,
            (_sahl_missing("true_node_distance", "required_chart_input", Body.TRUE_NODE),),
        ))
    else:
        node_clauses = []
        for name, node_longitude in (
            ("head", true_node.longitude),
            ("tail", (true_node.longitude + 180.0) % 360.0),
        ):
            distance = _shortest_distance(moon.longitude, node_longitude)
            node_clauses.append(_sahl_clause(
                f"moon_within_12deg_{name}",
                SahlRuleState.TRIGGERED if distance <= 12.0 else SahlRuleState.CLEAR,
                policy.node_policy,
                (
                    _sahl_measurement("node_longitude", node_longitude, units="degrees"),
                    _sahl_measurement("separation", distance, units="degrees", comparison="<=", threshold=12.0),
                ),
                "Shortest tropical longitude separation; equality and the exact node are included.",
            ))
        rules.append(_sahl_rule("moon_near_lunar_node_12deg", 5, tuple(node_clauses)))

    if moon is None:
        rules.append(_sahl_missing_moon(6, "moon_in_terminal_malefic_bound"))
    else:
        bound = egyptian_bound_of(
            moon.longitude,
            policy=EgyptianBoundsPolicy(EgyptianBoundsDoctrine.EGYPTIAN),
        )
        malefic_bound = (
            bound.ruler in (Body.MARS, Body.SATURN)
            and bound.segment.end_degree == 30.0
        )
        rules.append(_sahl_rule(
            "moon_in_terminal_malefic_bound",
            6,
            (_sahl_clause(
                "egyptian_bound_ruled_by_malefic",
                SahlRuleState.TRIGGERED if malefic_bound else SahlRuleState.CLEAR,
                policy.bound_policy,
                (
                    _sahl_measurement("moon_sign", bound.sign),
                    _sahl_measurement("degree_in_sign", bound.degree_in_sign, units="degrees"),
                    _sahl_measurement("bound_ruler", bound.ruler, comparison="in", threshold="Mars or Saturn"),
                    _sahl_measurement("bound_interval", f"[{bound.segment.start_degree}, {bound.segment.end_degree})"),
                ),
                "Only the terminal Egyptian bound ending at 30 degrees is tested; Sahl leaves the table unnamed.",
            ),),
        ))

    if moon is None:
        rules.append(_sahl_missing_moon(7, "moon_cadent_or_burnt_path"))
    else:
        burnt = _sahl_burnt_path_clause(moon.longitude, policy.burnt_path_variant)
        if chart.houses is None:
            cadent = _sahl_missing("moon_cadent", policy.cadency_policy, "quadrant house cusps")
        elif not chart.houses.is_quadrant_system:
            cadent = _sahl_clause(
                "moon_cadent",
                SahlRuleState.NOT_EVALUABLE,
                policy.cadency_policy,
                (
                    _sahl_measurement("requested_house_system", chart.houses.system),
                    _sahl_measurement("effective_house_system", chart.houses.effective_system),
                ),
                "The selected effective house system is not a quadrant system.",
            )
        else:
            placement = assign_house(moon.longitude, chart.houses)
            angularity = describe_angularity(placement)
            is_cadent = angularity.category is HouseAngularity.CADENT
            cadent = _sahl_clause(
                "moon_cadent",
                SahlRuleState.TRIGGERED if is_cadent else SahlRuleState.CLEAR,
                policy.cadency_policy,
                (
                    _sahl_measurement("house", placement.house),
                    _sahl_measurement("angularity", angularity.category.value),
                    _sahl_measurement("requested_house_system", chart.houses.system),
                    _sahl_measurement("effective_house_system", chart.houses.effective_system),
                    _sahl_measurement("house_fallback", chart.houses.fallback),
                ),
                "Cadency is houses 3, 6, 9, or 12 in the explicit effective quadrant figure.",
            )
        rules.append(_sahl_rule(
            "moon_cadent_or_burnt_path",
            7,
            (cadent, burnt),
            modifiers=(
                "Sahl calls the seventh impediment the worst but note 69 does not resolve whether that applies to one or both clauses.",
            ),
        ))

    if moon is None:
        rules.append(_sahl_missing_moon(8, "moon_twelfth_part_or_opposed_or_averse_house"))
    else:
        first = _sahl_eighth_first_clause(moon, mars, saturn, policy)
        capricorn = _sahl_clause(
            "moon_opposite_own_house",
            SahlRuleState.TRIGGERED if moon.sign == "Capricorn" else SahlRuleState.CLEAR,
            policy.eighth_rule_variant.value,
            (_sahl_measurement("moon_sign", moon.sign, comparison="==", threshold="Capricorn"),),
            "Capricorn is opposite the Moon's domicile Cancer.",
        )
        averse_signs = ("Gemini", "Leo", "Sagittarius", "Aquarius")
        aversion = _sahl_clause(
            "moon_averse_to_cancer",
            SahlRuleState.TRIGGERED if moon.sign in averse_signs else SahlRuleState.CLEAR,
            policy.eighth_rule_variant.value,
            (_sahl_measurement("moon_sign", moon.sign, comparison="in", threshold=", ".join(averse_signs)),),
            "The second, sixth, eighth, and twelfth signs from Cancer do not behold it.",
        )
        rules.append(_sahl_rule(
            "moon_twelfth_part_or_opposed_or_averse_house",
            8,
            (first, capricorn, aversion),
            modifiers=(
                "Dykes recommends the Arabic/al-Rijal twelfth-part reading; the conflicting Latin twelfth-sign reading remains selectable and labeled.",
            ),
        ))

    if moon is None:
        rules.append(_sahl_missing_moon(9, "moon_slow_below_12deg_per_day"))
    else:
        slow = moon.speed < 12.0
        rules.append(_sahl_rule(
            "moon_slow_below_12deg_per_day",
            9,
            (_sahl_clause(
                "moon_speed_below_12deg_per_day",
                SahlRuleState.TRIGGERED if slow else SahlRuleState.CLEAR,
                policy.position_product,
                (_sahl_measurement("moon_longitude_rate", moon.speed, units="degrees/day", comparison="<", threshold=12.0),),
                "Sahl's comparison is strict: even one minute less than 12 degrees per day triggers.",
            ),),
        ))

    if void_of_course is None:
        voc = _sahl_missing(
            "moon_empty_until_sign_ingress",
            policy.void_policy,
            "medieval sign-bounded forward connection search",
        )
    else:
        voc = _sahl_clause(
            "moon_empty_until_sign_ingress",
            SahlRuleState.TRIGGERED if void_of_course else SahlRuleState.CLEAR,
            policy.void_policy,
            (_sahl_measurement("void_of_course", void_of_course, comparison="==", threshold=True),),
            "No exact traditional-planet connection completes before the Moon leaves its sign.",
        )
    rules.append(_sahl_rule("moon_empty_in_course", 10, (voc,)))

    rule_tuple = tuple(rules)
    status = (
        SahlMoonConditionStatus.TRIGGERED
        if any(rule.state is SahlRuleState.TRIGGERED for rule in rule_tuple)
        else SahlMoonConditionStatus.INDETERMINATE
        if any(rule.state is SahlRuleState.NOT_EVALUABLE for rule in rule_tuple)
        else SahlMoonConditionStatus.CLEAR
    )
    houses = chart.houses
    return SahlMoonConditionEvaluation(
        jd_ut=chart.jd_ut,
        profile_id=policy.profile_id,
        profile_version=policy.profile_version,
        status=status,
        rules=rule_tuple,
        position_product=policy.position_product,
        reader_provenance=reader_provenance,
        latitude=chart.latitude,
        longitude=chart.longitude,
        requested_house_system=houses.system if houses else None,
        effective_house_system=houses.effective_system if houses else None,
        house_fallback=houses.fallback if houses else None,
        burnt_path_variant=policy.burnt_path_variant,
        eighth_rule_variant=policy.eighth_rule_variant,
    )


def sahl_moon_condition_at(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    burnt_path_variant: SahlBurntPathVariant | None = None,
    eighth_rule_variant: SahlEighthRuleVariant | None = None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    policy: SahlMoonConditionPolicy = SAHL_MOON_CONDITION_V1,
) -> SahlMoonConditionEvaluation:
    """Build the astronomical inputs and evaluate Sahl's bounded profile."""

    if not isinstance(policy, SahlMoonConditionPolicy):
        raise TypeError("policy must be a SahlMoonConditionPolicy")
    overrides = {}
    if burnt_path_variant is not None:
        if not isinstance(burnt_path_variant, SahlBurntPathVariant):
            raise TypeError("burnt_path_variant must be a SahlBurntPathVariant or None")
        overrides["burnt_path_variant"] = burnt_path_variant
    if eighth_rule_variant is not None:
        if not isinstance(eighth_rule_variant, SahlEighthRuleVariant):
            raise TypeError("eighth_rule_variant must be a SahlEighthRuleVariant or None")
        overrides["eighth_rule_variant"] = eighth_rule_variant
    resolved_policy = replace(policy, **overrides) if overrides else policy
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
    voc = is_void_of_course(jd_ut, reader=resolved_reader, modern=False)
    reader_path = getattr(resolved_reader, "path", None)
    reader_provenance = (
        str(reader_path)
        if reader_path is not None
        else f"{type(resolved_reader).__module__}.{type(resolved_reader).__qualname__}"
    )
    return evaluate_sahl_moon_condition(
        chart,
        void_of_course=voc,
        position_product=resolved_policy.position_product,
        reader_provenance=reader_provenance,
        policy=resolved_policy,
    )

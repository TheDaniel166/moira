"""Source-bounded Dorothean matter profiles from Carmen V.8, V.9, and V.11.

The three profiles share one public computational vessel because each is a
single-moment, non-scored inspection of a named matter.  Profile identity is
explicit; no profile is treated as a complete election or recommendation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._western_electional_context import (
    DOROTHEUS_ROOTED_CONTEXT_V1,
    DorotheusMatter,
    DorotheusPlacementWitness,
    DorotheusRootedContextEvaluation,
    DorotheusStrengthState,
    WesternElectionClass,
    evaluate_dorotheus_rooted_context,
)
from ._western_electional_dorotheus import (
    DOROTHEUS_MOON_CONDITION_V1,
    DorotheusMeasurement,
    DorotheusMoonConditionEvaluation,
    evaluate_dorotheus_moon_condition,
)
from .chart import ChartContext, create_chart
from .aspect_events import (
    MoonConnectionFlow,
    MoonConnectionFlowPolicy,
    moon_connection_flow_at,
)
from .constants import Body, SIGNS, sign_of
from .eclipse import EclipseCalculator
from .houses import HousePolicy, assign_house, describe_angularity
from .planets import planet_at
from .spk_reader import SpkReader, get_reader
from .void_of_course import next_moon_connection


__all__ = [
    "DorotheusMatterProfileId",
    "DorotheusMatterClauseRole",
    "DorotheusMatterClauseState",
    "DorotheusMatterProfileStatus",
    "DorotheusAngularPlaceWitness",
    "DorotheusMatterClauseWitness",
    "DorotheusMatterProfilePolicy",
    "DorotheusMatterProfileEvaluation",
    "DOROTHEUS_DEMOLITION_V1",
    "DOROTHEUS_LEASING_V1",
    "DOROTHEUS_LAND_PURCHASE_V1",
    "evaluate_dorotheus_matter_profile",
    "dorotheus_matter_profile_at",
]


_AUTHORITY_V8 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.8.1-2, printed p. 238, including note 40"
)
_AUTHORITY_V9 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.9.1-8, printed pp. 239-241, with Dykes's party-role commentary"
)
_AUTHORITY_V11 = (
    "Dorotheus of Sidon, Carmen Astrologicum, Umar al-Tabari translation, "
    "Book V.11.1-3, printed pp. 242-243"
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
_INFORTUNES = (Body.MARS, Body.SATURN)
_CONFIGURED_OFFSETS = frozenset((0, 2, 3, 4, 6, 8, 9, 10))
_WATERY_SIGNS = frozenset(("Cancer", "Scorpio", "Pisces"))
_TWIN_SIGNS = frozenset(("Gemini", "Virgo", "Sagittarius", "Pisces"))


class DorotheusMatterProfileId(str, Enum):
    DEMOLITION = "dorotheus_demolition_v1"
    LEASING = "dorotheus_leasing_v1"
    LAND_PURCHASE = "dorotheus_land_purchase_v1"


class DorotheusMatterClauseRole(str, Enum):
    FORTIFIER = "fortifier"
    GATE = "gate"
    WITNESS = "witness"


class DorotheusMatterClauseState(str, Enum):
    SATISFIED = "satisfied"
    CLEAR = "clear"
    TRIGGERED = "triggered"
    OBSERVED = "observed"
    NOT_EVALUABLE = "not_evaluable"


class DorotheusMatterProfileStatus(str, Enum):
    CLEAR = "clear_of_explicit_profile_impediments"
    TRIGGERED = "one_or_more_explicit_profile_impediments"
    DESCRIPTIVE = "descriptive_witnesses_only"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class DorotheusAngularPlaceWitness:
    whole_sign_place: int
    topic: str
    sign: str
    occupying_fortunes: tuple[str, ...]
    configured_fortunes: tuple[str, ...]
    occupying_infortunes: tuple[str, ...]
    configured_infortunes: tuple[str, ...]
    source_meaning: str

    def __post_init__(self) -> None:
        if self.whole_sign_place not in (1, 4, 7, 10):
            raise ValueError("angular witness must use whole-sign place 1, 4, 7, or 10")
        if self.sign not in SIGNS or not self.topic or not self.source_meaning:
            raise ValueError("angular topic identity and canonical sign must remain visible")


@dataclass(frozen=True, slots=True)
class DorotheusMatterClauseWitness:
    clause_id: str
    source_order: int
    role: DorotheusMatterClauseRole
    state: DorotheusMatterClauseState
    measurements: tuple[DorotheusMeasurement, ...]
    explanation: str
    source_reference: str

    def __post_init__(self) -> None:
        if self.source_order < 1 or not self.clause_id or not self.measurements:
            raise ValueError("matter clause identity, order, and derivation must remain visible")
        if not self.explanation or not self.source_reference:
            raise ValueError("matter clause explanation and authority must remain visible")
        if self.role is DorotheusMatterClauseRole.GATE:
            if self.state not in (
                DorotheusMatterClauseState.CLEAR,
                DorotheusMatterClauseState.TRIGGERED,
                DorotheusMatterClauseState.NOT_EVALUABLE,
            ):
                raise ValueError("gate clauses require clear, triggered, or not-evaluable state")
        elif self.state is DorotheusMatterClauseState.TRIGGERED:
            raise ValueError("only gate clauses can be triggered")


@dataclass(frozen=True, slots=True)
class DorotheusMatterProfilePolicy:
    profile_id: DorotheusMatterProfileId
    profile_version: str = "1.0.0"
    angular_place_policy: str = "whole_sign_places_from_tropical_ascendant"
    configuration_policy: str = "whole_sign_ptolemaic_configuration"
    strength_policy: str = "quadrant_house_angular_succedent_cadent"
    latitude_rate_sample_days: float = 0.01

    def __post_init__(self) -> None:
        if self.profile_version != "1.0.0":
            raise ValueError("profile_version is fixed for admitted v1 profiles")
        if self.angular_place_policy != "whole_sign_places_from_tropical_ascendant":
            raise ValueError("angular_place_policy is fixed")
        if self.configuration_policy != "whole_sign_ptolemaic_configuration":
            raise ValueError("configuration_policy is fixed")
        if self.strength_policy != "quadrant_house_angular_succedent_cadent":
            raise ValueError("strength_policy is fixed")
        if self.latitude_rate_sample_days != 0.01:
            raise ValueError("latitude_rate_sample_days is fixed")


DOROTHEUS_DEMOLITION_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.DEMOLITION
)
DOROTHEUS_LEASING_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.LEASING
)
DOROTHEUS_LAND_PURCHASE_V1 = DorotheusMatterProfilePolicy(
    DorotheusMatterProfileId.LAND_PURCHASE
)
_POLICIES = {
    policy.profile_id: policy
    for policy in (
        DOROTHEUS_DEMOLITION_V1,
        DOROTHEUS_LEASING_V1,
        DOROTHEUS_LAND_PURCHASE_V1,
    )
}
_AUTHORITIES = {
    DorotheusMatterProfileId.DEMOLITION: _AUTHORITY_V8,
    DorotheusMatterProfileId.LEASING: _AUTHORITY_V9,
    DorotheusMatterProfileId.LAND_PURCHASE: _AUTHORITY_V11,
}
_MATTERS = {
    DorotheusMatterProfileId.DEMOLITION: "building_demolition",
    DorotheusMatterProfileId.LEASING: "leasing",
    DorotheusMatterProfileId.LAND_PURCHASE: "land_purchase",
}
_EXPECTED_CLAUSE_COUNTS = {
    DorotheusMatterProfileId.DEMOLITION: 2,
    DorotheusMatterProfileId.LEASING: 5,
    DorotheusMatterProfileId.LAND_PURCHASE: 2,
}


@dataclass(frozen=True, slots=True)
class DorotheusMatterProfileEvaluation:
    jd_ut: float
    profile_id: DorotheusMatterProfileId
    profile_version: str
    matter: str
    status: DorotheusMatterProfileStatus
    moon_condition: DorotheusMoonConditionEvaluation
    rooted_context: DorotheusRootedContextEvaluation
    moon_connection_flow: MoonConnectionFlow | None
    clauses: tuple[DorotheusMatterClauseWitness, ...]
    angular_places: tuple[DorotheusAngularPlaceWitness, ...]
    planetary_strengths: tuple[DorotheusPlacementWitness, ...]
    triggered_clause_ids: tuple[str, ...]
    not_evaluable_clause_ids: tuple[str, ...]
    reader_provenance: str
    authorities: tuple[str, ...]
    source_complete: bool = True
    complete_matter_profile: bool = True
    numerically_complete: bool = True
    complete_electional_judgement: bool = False
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"
    scoring: str = "not_provided"

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_ut):
            raise ValueError("jd_ut must be finite")
        if self.matter != _MATTERS[self.profile_id]:
            raise ValueError("matter must derive from profile identity")
        if (
            self.profile_id is not DorotheusMatterProfileId.LEASING
            and self.moon_connection_flow is not None
        ):
            raise ValueError("Moon connection flow belongs only to the leasing profile")
        if len(self.clauses) != _EXPECTED_CLAUSE_COUNTS[self.profile_id]:
            raise ValueError("profile must preserve every admitted source clause")
        if tuple(item.source_order for item in self.clauses) != tuple(
            range(1, len(self.clauses) + 1)
        ):
            raise ValueError("matter clauses must remain in source-derived order")
        triggered = tuple(
            item.clause_id
            for item in self.clauses
            if item.state is DorotheusMatterClauseState.TRIGGERED
        )
        unknown = tuple(
            item.clause_id
            for item in self.clauses
            if item.state is DorotheusMatterClauseState.NOT_EVALUABLE
        )
        if triggered != self.triggered_clause_ids or unknown != self.not_evaluable_clause_ids:
            raise ValueError("clause summaries must derive from visible clauses")
        if self.numerically_complete != (not unknown):
            raise ValueError("numerical completeness must derive from evaluability")
        if not self.source_complete or not self.complete_matter_profile:
            raise ValueError("an admitted matter profile must preserve its full source layer")
        if self.complete_electional_judgement:
            raise ValueError("a matter profile is not a complete electional judgement")


def _measurement(
    name: str,
    value: float | str | bool | None,
    *,
    units: str | None = None,
    comparison: str | None = None,
    threshold: float | str | bool | None = None,
) -> DorotheusMeasurement:
    return DorotheusMeasurement(name, value, units, comparison, threshold)


def _whole_sign_offset(a_sign: str, b_sign: str) -> int:
    return (SIGNS.index(b_sign) - SIGNS.index(a_sign)) % 12


def _configured(a_sign: str, b_sign: str) -> bool:
    return _whole_sign_offset(a_sign, b_sign) in _CONFIGURED_OFFSETS


def _placement(chart: ChartContext, body: str) -> DorotheusPlacementWitness:
    planet = chart.planets[body]
    houses = chart.houses
    if houses is None or not houses.is_quadrant_system:
        return DorotheusPlacementWitness(
            body=body,
            role="V.8 fortune_or_infortune_strength",
            longitude=planet.longitude,
            sign=planet.sign,
            house=None,
            strength=DorotheusStrengthState.NOT_EVALUABLE,
            house_system_is_quadrant=False,
            explanation="Dynamic strength requires a quadrant house figure.",
        )
    house = assign_house(planet.longitude, houses)
    strength = DorotheusStrengthState(describe_angularity(house).category.value)
    return DorotheusPlacementWitness(
        body=body,
        role="V.8 fortune_or_infortune_strength",
        longitude=planet.longitude,
        sign=planet.sign,
        house=house.house,
        strength=strength,
        house_system_is_quadrant=True,
        explanation="Strength is the house's angular, succedent, or cadent relation.",
    )


def _angular_witness(
    chart: ChartContext,
    place: int,
    topic: str,
    source_meaning: str,
) -> DorotheusAngularPlaceWitness:
    if chart.houses is None:
        raise ValueError("matter profiles require houses")
    asc_sign, _, _ = sign_of(chart.houses.asc)
    target_sign = SIGNS[(SIGNS.index(asc_sign) + place - 1) % 12]

    def occupants(bodies: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(body for body in bodies if chart.planets[body].sign == target_sign)

    def aspecters(bodies: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            body
            for body in bodies
            if chart.planets[body].sign != target_sign
            and _configured(chart.planets[body].sign, target_sign)
        )

    return DorotheusAngularPlaceWitness(
        whole_sign_place=place,
        topic=topic,
        sign=target_sign,
        occupying_fortunes=occupants(_FORTUNES),
        configured_fortunes=aspecters(_FORTUNES),
        occupying_infortunes=occupants(_INFORTUNES),
        configured_infortunes=aspecters(_INFORTUNES),
        source_meaning=source_meaning,
    )


def _clause(
    clause_id: str,
    order: int,
    role: DorotheusMatterClauseRole,
    state: DorotheusMatterClauseState,
    measurements: tuple[DorotheusMeasurement, ...],
    explanation: str,
    source_reference: str,
) -> DorotheusMatterClauseWitness:
    return DorotheusMatterClauseWitness(
        clause_id, order, role, state, measurements, explanation, source_reference
    )


def evaluate_dorotheus_matter_profile(
    chart: ChartContext,
    *,
    profile_id: DorotheusMatterProfileId,
    moon_condition: DorotheusMoonConditionEvaluation,
    rooted_context: DorotheusRootedContextEvaluation,
    moon_connection_flow: MoonConnectionFlow | None = None,
    moon_latitude_rate_degrees_per_day: float,
    reader_provenance: str,
    policy: DorotheusMatterProfilePolicy | None = None,
) -> DorotheusMatterProfileEvaluation:
    """Evaluate one source-closed Dorothean matter layer without scoring."""

    profile_id = DorotheusMatterProfileId(profile_id)
    resolved_policy = _POLICIES[profile_id] if policy is None else policy
    if resolved_policy.profile_id is not profile_id:
        raise ValueError("policy identity must match requested profile")
    if not math.isfinite(moon_latitude_rate_degrees_per_day):
        raise ValueError("Moon latitude rate must be finite")
    if chart.houses is None:
        raise ValueError("matter profiles require a house figure")
    if moon_condition.jd_ut != chart.jd_ut or rooted_context.jd_ut != chart.jd_ut:
        raise ValueError("all inherited layers must describe the same instant")
    if (
        moon_connection_flow is not None
        and moon_connection_flow.jd_query != chart.jd_ut
    ):
        raise ValueError("Moon connection flow must describe the same instant")
    if (
        profile_id is not DorotheusMatterProfileId.LEASING
        and moon_connection_flow is not None
    ):
        raise ValueError("Moon connection flow belongs only to the leasing profile")

    authority = _AUTHORITIES[profile_id]
    angular_places: tuple[DorotheusAngularPlaceWitness, ...] = ()
    strengths: tuple[DorotheusPlacementWitness, ...] = ()

    if profile_id is DorotheusMatterProfileId.DEMOLITION:
        strengths = tuple(_placement(chart, body) for body in _FORTUNES + _INFORTUNES)
        strength_evaluable = all(
            item.strength is not DorotheusStrengthState.NOT_EVALUABLE
            for item in strengths
        )
        descending = moon_latitude_rate_degrees_per_day < 0.0
        clauses = (
            _clause(
                "moon_descending_south_in_latitude",
                1,
                DorotheusMatterClauseRole.FORTIFIER,
                (
                    DorotheusMatterClauseState.SATISFIED
                    if descending
                    else DorotheusMatterClauseState.CLEAR
                ),
                (
                    _measurement(
                        "moon_latitude_rate",
                        moon_latitude_rate_degrees_per_day,
                        units="degrees/day",
                        comparison="<",
                        threshold=0.0,
                    ),
                    _measurement("direction", "southward" if descending else "northward_or_stationary"),
                ),
                "V.8's descent is Hephaistion's southward lunar latitude motion.",
                authority,
            ),
            _clause(
                "fortune_and_infortune_strengths",
                2,
                DorotheusMatterClauseRole.WITNESS,
                (
                    DorotheusMatterClauseState.OBSERVED
                    if strength_evaluable
                    else DorotheusMatterClauseState.NOT_EVALUABLE
                ),
                tuple(
                    _measurement(f"{item.body.lower()}_strength", item.strength.value)
                    for item in strengths
                ),
                "V.8 preserves each fortune and infortune's dynamic strength: fortunes indicate ease and success, while infortunes indicate slowness, difficulty, and toil. No aggregate score is inferred.",
                authority,
            ),
        )
    elif profile_id is DorotheusMatterProfileId.LEASING:
        angular_places = (
            _angular_witness(chart, 1, "hiring_party", "party hiring labor or taking the fixed amount"),
            _angular_witness(chart, 7, "owner_or_provider", "owner or party providing labor, land, or tools"),
            _angular_witness(chart, 10, "amount_or_price", "amount, price, or contractual quantity"),
            _angular_witness(chart, 4, "outcome", "outcome of the work or agreement"),
        )
        leasing_clauses: list[DorotheusMatterClauseWitness] = []
        ids = (
            "infortune_in_hiring_party_place",
            "infortune_in_or_configured_to_owner_place",
            "infortune_in_or_configured_to_amount_place",
            "infortune_in_or_configured_to_outcome_place",
        )
        consequences = (
            "V.9.2-3: the hiring party may back out and take nothing; if the party participates, the text warns of deception, wickedness, and immorality.",
            "V.9.4-5: the owner or provider may back out and withhold the portion; participation carries warnings of immorality, obscenity, and betrayal.",
            "V.9.6: the amount or price will not be put in order and misfortune is attributed to it.",
            "V.9.7: the outcome is described as bad and harmful.",
        )
        for order, (clause_id, witness, consequence) in enumerate(
            zip(ids, angular_places, consequences), start=1
        ):
            malefics = witness.occupying_infortunes
            if witness.whole_sign_place != 1:
                malefics += witness.configured_infortunes
            leasing_clauses.append(
                _clause(
                    clause_id,
                    order,
                    DorotheusMatterClauseRole.GATE,
                    (
                        DorotheusMatterClauseState.TRIGGERED
                        if malefics
                        else DorotheusMatterClauseState.CLEAR
                    ),
                    (
                        _measurement("whole_sign_place", witness.whole_sign_place),
                        _measurement("topic", witness.topic),
                        _measurement("qualifying_infortunes", ",".join(malefics) or "none"),
                    ),
                    consequence + " The warning remains attached to the named party or stake and is not converted into a numeric score.",
                    authority,
                )
            )
        flow = moon_connection_flow
        previous = None if flow is None else flow.previous_separation
        previous_motion = None if flow is None else flow.previous_motion
        connection = None if flow is None else flow.next_connection
        leasing_clauses.append(
            _clause(
                "moon_separation_and_connection_flow",
                5,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.NOT_EVALUABLE,
                (
                    _measurement("next_connection_body", None if connection is None else connection.body),
                    _measurement("next_connection_aspect", None if connection is None else connection.aspect_name),
                    _measurement("next_connection_jd_exact", None if connection is None else connection.jd_exact, units="JD UT1"),
                    _measurement("next_connection_signed_error_at_query", None if connection is None else connection.signed_error_at_query_deg, units="degrees"),
                    _measurement("previous_separation_body", None if previous is None else previous.body),
                    _measurement("previous_separation_aspect", None if previous is None else previous.aspect_name),
                    _measurement("previous_separation_jd_exact", None if previous is None else previous.jd_exact, units="JD UT1"),
                    _measurement("previous_separation_signed_error_at_query", None if previous is None else previous.signed_error_at_query_deg, units="degrees"),
                    _measurement("previous_motion_state", None if previous_motion is None else previous_motion.state.value),
                    _measurement("previous_window_policy", None if flow is None else flow.policy.previous_window.value),
                    _measurement("missing_semantics", "V.9-specific assignment of lunar flow-away and connection to the four leasing stakes"),
                ),
                "V.9.8 requires both what the Moon flows away from and connects to. The neutral geometry is preserved when an explicit previous-event window is supplied, but the surviving V.9 text does not assign those events to its four leasing stakes; the doctrinal clause therefore remains indeterminate.",
                authority,
            )
        )
        clauses = tuple(leasing_clauses)
    else:
        angular_places = (
            _angular_witness(chart, 4, "land", "the land itself"),
            _angular_witness(chart, 10, "trees", "trees on the land"),
            _angular_witness(chart, 7, "vegetation", "grasses, hemp, and vegetation"),
            _angular_witness(chart, 1, "cultivation", "cultivation and management of the land"),
        )
        land = angular_places[0]
        watery = land.sign in _WATERY_SIGNS
        twin = land.sign in _TWIN_SIGNS
        clauses = (
            _clause(
                "fourth_place_terrain_testimony",
                1,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                (
                    _measurement("fourth_place_sign", land.sign),
                    _measurement("watery_sign", watery),
                    _measurement("twin_sign", twin),
                    _measurement(
                        "terrain_testimony",
                        "+".join(
                            item
                            for item, present in (
                                ("near_water_or_much_water", watery),
                                ("mixed_mountains_and_plains", twin),
                            )
                            if present
                        ) or "no_V.11_named_terrain_testimony",
                    ),
                ),
                "V.11 permits both testimonies to coexist; Pisces is not forced into one category.",
                authority,
            ),
            _clause(
                "fortune_and_infortune_testimony_at_remaining_stakes",
                2,
                DorotheusMatterClauseRole.WITNESS,
                DorotheusMatterClauseState.OBSERVED,
                tuple(
                    _measurement(
                        f"{item.topic}_configured_fortunes",
                        ",".join(item.occupying_fortunes + item.configured_fortunes) or "none",
                    )
                    for item in angular_places
                )
                + tuple(
                    _measurement(
                        f"{item.topic}_configured_infortunes",
                        ",".join(item.occupying_infortunes + item.configured_infortunes) or "none",
                    )
                    for item in angular_places
                ),
                "The four topic stakes retain fortune and infortune testimony separately: fortune indicates benefit and infortune harm for the matter attributed to that stake. V.11 supplies no lawful aggregate score.",
                authority,
            ),
        )

    triggered = tuple(
        item.clause_id for item in clauses if item.state is DorotheusMatterClauseState.TRIGGERED
    )
    unknown = tuple(
        item.clause_id for item in clauses if item.state is DorotheusMatterClauseState.NOT_EVALUABLE
    )
    if triggered:
        status = DorotheusMatterProfileStatus.TRIGGERED
    elif unknown:
        status = DorotheusMatterProfileStatus.INDETERMINATE
    elif profile_id is DorotheusMatterProfileId.LEASING:
        status = DorotheusMatterProfileStatus.CLEAR
    else:
        status = DorotheusMatterProfileStatus.DESCRIPTIVE

    return DorotheusMatterProfileEvaluation(
        jd_ut=chart.jd_ut,
        profile_id=profile_id,
        profile_version=resolved_policy.profile_version,
        matter=_MATTERS[profile_id],
        status=status,
        moon_condition=moon_condition,
        rooted_context=rooted_context,
        moon_connection_flow=moon_connection_flow,
        clauses=clauses,
        angular_places=angular_places,
        planetary_strengths=strengths,
        triggered_clause_ids=triggered,
        not_evaluable_clause_ids=unknown,
        reader_provenance=reader_provenance,
        authorities=(authority,),
        numerically_complete=not unknown,
    )


def dorotheus_matter_profile_at(
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    profile_id: DorotheusMatterProfileId,
    election_class: WesternElectionClass = WesternElectionClass.EPHEMERAL,
    natal_jd_ut: float | None = None,
    natal_latitude: float | None = None,
    natal_longitude: float | None = None,
    natal_house_system: str | None = None,
    unavoidable_time_urgency: bool | None = None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    policy: DorotheusMatterProfilePolicy | None = None,
    moon_flow_policy: MoonConnectionFlowPolicy | None = None,
) -> DorotheusMatterProfileEvaluation:
    """Construct the shared astronomy and evaluate one named matter profile."""

    profile_id = DorotheusMatterProfileId(profile_id)
    if profile_id is DorotheusMatterProfileId.LEASING and moon_flow_policy is None:
        raise ValueError(
            "leasing profile requires an explicit moon_flow_policy because the "
            "previous-separation window is not source-settled"
        )
    if profile_id is not DorotheusMatterProfileId.LEASING and moon_flow_policy is not None:
        raise ValueError("moon_flow_policy is accepted only for the leasing profile")
    election_class = WesternElectionClass(election_class)
    natal_values = (natal_jd_ut, natal_latitude, natal_longitude, natal_house_system)
    if election_class is WesternElectionClass.EPHEMERAL and any(
        value is not None for value in natal_values
    ):
        raise ValueError("ephemeral matter profile rejects natal input")
    if election_class is WesternElectionClass.RADICAL and any(
        value is None for value in natal_values
    ):
        raise ValueError("radical matter profile requires complete natal input")

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
    moon_condition = evaluate_dorotheus_moon_condition(
        chart,
        moon_eclipsed=moon_eclipsed,
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
    resolved_policy = _POLICIES[profile_id] if policy is None else policy
    dt = resolved_policy.latitude_rate_sample_days
    before = planet_at(Body.MOON, jd_ut - dt, reader=resolved_reader)
    after = planet_at(Body.MOON, jd_ut + dt, reader=resolved_reader)
    latitude_rate = (after.latitude - before.latitude) / (2.0 * dt)
    moon_flow = (
        moon_connection_flow_at(
            jd_ut,
            policy=moon_flow_policy,
            reader=resolved_reader,
        )
        if moon_flow_policy is not None
        else None
    )
    return evaluate_dorotheus_matter_profile(
        chart,
        profile_id=profile_id,
        moon_condition=moon_condition,
        rooted_context=rooted_context,
        moon_connection_flow=moon_flow,
        moon_latitude_rate_degrees_per_day=latitude_rate,
        reader_provenance=provenance,
        policy=resolved_policy,
    )

"""Atomic source and adversarial tests for :mod:`moira.horary`."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

import pytest

import moira.horary as horary_module
from moira.classical_perfection import (
    ClassicalBodyState,
    ClassicalPerfectionAnalysis,
    ClassicalPerfectionEvent,
    ClassicalPerfectionEventKind,
    ClassicalPerfectionState,
    LILLY_1647_PERFECTION_V1,
    classify_lilly_perfection_events,
    LillyPerfectionPolicy,
)
from moira.constants import Body, HouseSystem
from moira.dignities_types import (
    SolarProximityBand,
    SolarProximityTruth,
    TruthEvaluationStatus,
)
from moira.horary import (
    MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1,
    HoraryChartSect,
    HoraryConsiderationInputs,
    HoraryEvidenceState,
    HoraryHourAgreementState,
    HoraryHourRuleState,
    HoraryHouseGeometryReceipt,
    HoraryHousePolicy,
    HoraryBodyPlacementReceipt,
    HoraryGeometrySourceMode,
    HoraryPerfectionEvidence,
    HoraryPerfectionSearchPolicy,
    HoraryPerfectionState,
    HoraryPlanetaryHourReceipt,
    HoraryQuestionReceipt,
    HoraryQuestionTimeBasis,
    HoraryQuestionTimeReceipt,
    HoraryRuleState,
    HorarySignificatorRole,
    HorarySolarProximityReceipt,
    HorarySourceCalendar,
    HoraryTurnStepKind,
    evaluate_horary_evidence,
    resolve_turned_house,
)
from moira.houses import HouseCusps, HousePolicy, classify_house_system, house_of


_QUESTION_ID = "horary-atomic-test-question"
_LATITUDE = 51.5074
_LONGITUDE = -0.1278
_JD_UT1 = 2451545.0
_GEOMETRY_SOURCE_ID = "unit-house-geometry-v1"


class _ForgedPolicy:
    """Adversarial object that impersonates every value-based policy guard."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False


def _evaluated_time(*, jd_ut1: float = _JD_UT1) -> HoraryQuestionTimeReceipt:
    return HoraryQuestionTimeReceipt(
        state=HoraryEvidenceState.EVALUATED,
        stated_basis=HoraryQuestionTimeBasis.QUESTION_PROPOSED_AND_FIGURE_ERECTED,
        stated_basis_source="Lilly 1647 CA p. 121 atomic test receipt",
        source_calendar=HorarySourceCalendar.GREGORIAN,
        source_instant_label="2000-01-01 12:00 UTC test event",
        normalized_instant=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        normalized_jd_ut1=jd_ut1,
        conversion_policy_id="test_utc_label_to_ut1_receipt_v1",
        reason=None,
    )


def _unresolved_time(
    *,
    basis: HoraryQuestionTimeBasis = HoraryQuestionTimeBasis.QUESTION_PROPOSED_AND_FIGURE_ERECTED,
) -> HoraryQuestionTimeReceipt:
    return HoraryQuestionTimeReceipt(
        state=HoraryEvidenceState.NOT_EVALUABLE,
        stated_basis=basis,
        stated_basis_source="Lilly 1647 source-chart metadata",
        source_calendar=HorarySourceCalendar.JULIAN,
        source_instant_label="27 May 1647 OS, 10:45, London",
        normalized_instant=None,
        normalized_jd_ut1=None,
        conversion_policy_id=None,
        reason="historical_calendar_and_clock_normalization_not_admitted",
    )


def _question(
    *,
    question_id: str = _QUESTION_ID,
    latitude_deg: float = _LATITUDE,
    longitude_deg: float = _LONGITUDE,
    time: HoraryQuestionTimeReceipt | None = None,
    perspective_path: tuple[int, ...] = (),
    terminal_topic_house: int = 9,
) -> HoraryQuestionReceipt:
    return HoraryQuestionReceipt(
        question_id=question_id,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        time=time or _evaluated_time(),
        perspective_path=perspective_path,
        terminal_topic_house=terminal_topic_house,
    )


def _houses(
    *,
    asc: float = 150.0,
    system: str = HouseSystem.REGIOMONTANUS,
    cusp_overrides: dict[int, float] | None = None,
    effective_system: str | None = None,
    fallback: bool = False,
    policy: HousePolicy | None = None,
) -> HouseCusps:
    # Compact source-assignment geometry only.  It is not a reconstructed
    # 1647 ephemeris golden.  H1 is Virgo and H9 is Aries by default, matching
    # the two role assignments named on CA pp. 442-445.
    cusps = [asc, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 350.0, 0.0, 30.0, 60.0, 90.0]
    for house, longitude in (cusp_overrides or {}).items():
        cusps[house - 1] = longitude
    effective = system if effective_system is None else effective_system
    return HouseCusps(
        system=system,
        cusps=tuple(cusps),
        asc=asc,
        mc=30.0,
        armc=0.0,
        effective_system=effective,
        fallback=fallback,
        fallback_reason="test fallback" if fallback else None,
        classification=classify_house_system(effective),
        policy=policy or HousePolicy.strict(),
    )


def _uniform_houses(
    asc: float,
    *,
    system: str = HouseSystem.EQUAL,
) -> HouseCusps:
    cusps = tuple((asc + 30.0 * index) % 360.0 for index in range(12))
    return HouseCusps(
        system=system,
        cusps=cusps,
        asc=asc,
        mc=cusps[9],
        armc=0.0,
        effective_system=system,
        fallback=False,
        fallback_reason=None,
        classification=classify_house_system(system),
        policy=HousePolicy.strict(),
    )


def _geometry(
    question: HoraryQuestionReceipt,
    *,
    houses: HouseCusps | None = None,
    source_id: str = _GEOMETRY_SOURCE_ID,
    source_mode: HoraryGeometrySourceMode = HoraryGeometrySourceMode.COMPUTED,
    question_id: str | None = None,
    latitude_deg: float | None = None,
    longitude_deg: float | None = None,
    jd_ut1: float | None = None,
) -> HoraryHouseGeometryReceipt:
    resolved_jd = (
        question.time.normalized_jd_ut1
        if source_mode is HoraryGeometrySourceMode.COMPUTED and jd_ut1 is None
        else jd_ut1
    )
    return HoraryHouseGeometryReceipt(
        question_id=question.question_id if question_id is None else question_id,
        latitude_deg=question.latitude_deg if latitude_deg is None else latitude_deg,
        longitude_deg=question.longitude_deg if longitude_deg is None else longitude_deg,
        source_id=source_id,
        source_mode=source_mode,
        jd_ut1=resolved_jd,
        house_cusps=houses or _houses(),
    )


def _profile(
    *,
    question: HoraryQuestionReceipt | None = None,
    houses: HouseCusps | None = None,
    geometry: HoraryHouseGeometryReceipt | None = None,
    house_system: str = HouseSystem.REGIOMONTANUS,
    hour: HoraryPlanetaryHourReceipt | None = None,
    considerations: HoraryConsiderationInputs | None = None,
    perfection: ClassicalPerfectionAnalysis | None = None,
):
    resolved_question = question or _question()
    resolved_geometry = geometry or _geometry(
        resolved_question,
        houses=houses or _houses(system=house_system),
    )
    return evaluate_horary_evidence(
        resolved_question,
        resolved_geometry,
        house_policy=HoraryHousePolicy(house_system),
        planetary_hour=hour,
        considerations=considerations,
        perfection_analysis=perfection,
    )


def _hour(
    ruler: str,
    *,
    question_id: str = _QUESTION_ID,
    jd_ut1: float = _JD_UT1,
    latitude_deg: float = _LATITUDE,
    longitude_deg: float = _LONGITUDE,
    hour_number: int = 1,
) -> HoraryPlanetaryHourReceipt:
    period_length = 0.5
    hour_length = period_length / 12.0
    period_index = hour_number - 1 if hour_number <= 12 else hour_number - 13
    period_start = jd_ut1 - (period_index + 0.5) * hour_length
    period_end = period_start + period_length
    hour_start = period_start + period_index * hour_length
    hour_end = hour_start + hour_length
    sunrise = period_start if hour_number <= 12 else period_end
    sunset = period_end if hour_number <= 12 else period_start
    return HoraryPlanetaryHourReceipt(
        question_id=question_id,
        jd_ut1=jd_ut1,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        source_id="unit-planetary-hour-v1",
        hour_ruler=ruler,
        hour_number=hour_number,
        hour_start_jd=hour_start,
        hour_end_jd=hour_end,
        sunrise_jd=sunrise,
        sunset_jd=sunset,
        local_time_algorithm_id="caller_supplied_unequal_hours_receipt_v1",
    )


def _placement(
    body: str,
    longitude_deg: float,
    *,
    question: HoraryQuestionReceipt | None = None,
    geometry: HoraryHouseGeometryReceipt | None = None,
    house: int | None = None,
) -> HoraryBodyPlacementReceipt:
    resolved_question = question or _question()
    resolved_geometry = geometry or _geometry(resolved_question)
    return HoraryBodyPlacementReceipt(
        question_id=resolved_question.question_id,
        body=body,
        longitude_deg=longitude_deg,
        house=house or house_of(longitude_deg, resolved_geometry.house_cusps),
        latitude_deg=resolved_question.latitude_deg,
        longitude_location_deg=resolved_question.longitude_deg,
        geometry_source_id=resolved_geometry.source_id,
        source_id=f"unit-{body.lower()}-placement-v1",
        source_mode=resolved_geometry.source_mode,
        jd_ut1=resolved_geometry.jd_ut1,
    )


def _solar_receipt(
    truth: SolarProximityTruth,
    *,
    body: str = Body.MERCURY,
    question: HoraryQuestionReceipt | None = None,
    geometry: HoraryHouseGeometryReceipt | None = None,
) -> HorarySolarProximityReceipt:
    resolved_question = question or _question()
    resolved_geometry = geometry or _geometry(resolved_question)
    return HorarySolarProximityReceipt(
        question_id=resolved_question.question_id,
        body=body,
        truth=truth,
        calculation_policy_id="typed_solar_proximity_v1",
        latitude_deg=resolved_question.latitude_deg,
        longitude_deg=resolved_question.longitude_deg,
        geometry_source_id=resolved_geometry.source_id,
        source_id="unit-solar-proximity-v1",
        source_mode=resolved_geometry.source_mode,
        jd_ut1=resolved_geometry.jd_ut1,
    )


def _state(body: str, longitude: float, speed: float) -> ClassicalBodyState:
    signs = (
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    )
    normalized = longitude % 360.0
    return ClassicalBodyState(body, normalized, speed, signs[int(normalized // 30.0)])


def _states() -> tuple[ClassicalBodyState, ...]:
    values = {
        Body.SUN: (120.0, 1.0),
        Body.MOON: (200.0, 13.0),
        Body.MERCURY: (0.0, 2.0),
        Body.VENUS: (80.0, 1.2),
        Body.MARS: (160.0, 0.5),
        Body.JUPITER: (5.0, 0.1),
        Body.SATURN: (280.0, 0.05),
    }
    return tuple(_state(body, *values[body]) for body in values)


def _perfection(
    a: str = Body.MERCURY,
    b: str = Body.MARS,
    *,
    jd_start: float = _JD_UT1,
    is_day_chart: bool = True,
) -> ClassicalPerfectionAnalysis:
    return classify_lilly_perfection_events(
        jd_start,
        jd_start + 5.0,
        a,
        b,
        is_day_chart=is_day_chart,
        initial_states=_states(),
        events=(),
        reader_provenance="classifier-produced unit event trace",
        policy=LILLY_1647_PERFECTION_V1,
    )


def _consideration(profile, rule_id: str):
    return next(item for item in profile.considerations if item.rule_id == rule_id)


def _direct_perfection_evidence(
    analysis: ClassicalPerfectionAnalysis,
) -> HoraryPerfectionEvidence:
    return HoraryPerfectionEvidence(
        state=HoraryPerfectionState.COMPOSED,
        principal_querent=Body.MERCURY,
        principal_quesited=Body.MARS,
        analysis=analysis,
        reason=None,
    )


def test_ca_pp442_445_missing_stone_source_chart_is_assignment_only() -> None:
    """No numerical golden: retain only CA pp.442-445's named assignments."""

    question = _question(time=_unresolved_time())
    geometry = _geometry(
        question,
        source_id="lilly-ca-1647-pp442-445-source-chart",
        source_mode=HoraryGeometrySourceMode.HISTORICAL_SOURCE_CHART_ASSIGNMENT,
    )
    profile = _profile(question=question, geometry=geometry)

    assert profile.chart_policy.state is HoraryEvidenceState.EVALUATED
    assert profile.turned_house.resolved_radical_house == 9
    assert profile.significators.principal_querent.role is HorarySignificatorRole.PRINCIPAL_QUERENT
    assert profile.significators.principal_querent.sign == "Virgo"
    assert profile.significators.principal_querent.body == "Mercury"
    assert profile.significators.querent_co_significator.body == "Moon"
    assert profile.significators.principal_quesited.sign == "Aries"
    assert profile.significators.principal_quesited.body == "Mars"
    assert profile.house_geometry is geometry
    assert profile.hour_agreement.state is HoraryHourAgreementState.NOT_EVALUABLE
    assert profile.hour_agreement.reason == "question_epoch_not_evaluable"
    assert profile.perfection.state is HoraryPerfectionState.NOT_EVALUABLE
    assert profile.perfection.reason == "question_epoch_not_evaluable_for_perfection"
    assert profile.provenance.complete_horary_judgement is False
    assert profile.provenance.scoring == "not_provided"
    assert profile.provenance.outcome_language == "not_provided"


def test_turning_preserves_perspective_path_and_terminal_topic() -> None:
    receipt = resolve_turned_house((7,), 2)

    assert receipt.resolved_radical_house == 8
    assert tuple(step.kind for step in receipt.steps) == (
        HoraryTurnStepKind.PERSPECTIVE,
        HoraryTurnStepKind.TERMINAL_TOPIC,
    )
    assert [(step.from_radical_house, step.counted_house, step.resolved_radical_house) for step in receipt.steps] == [
        (1, 7, 7),
        (7, 2, 8),
    ]


def test_multi_step_turn_wraps_without_inference() -> None:
    receipt = resolve_turned_house((12, 12), 2)

    assert [step.resolved_radical_house for step in receipt.steps] == [12, 11, 12]


def test_turn_receipt_rejects_a_forged_path_even_when_step_count_matches() -> None:
    receipt = resolve_turned_house((7,), 2)

    with pytest.raises(ValueError, match="caller-supplied count"):
        replace(receipt, perspective_path=(6,))


def test_turn_receipt_counting_semantics_are_fixed() -> None:
    with pytest.raises(ValueError, match="counting_semantics is fixed"):
        replace(resolve_turned_house((7,), 2), counting_semantics="zero_based")


@pytest.mark.parametrize("path, topic", [((0,), 2), ((13,), 2), ((-1,), 2), ((), 0), ((), 13)])
def test_turning_rejects_invalid_house_counts(path: tuple[int, ...], topic: int) -> None:
    with pytest.raises(ValueError, match=r"\[1, 12\]"):
        resolve_turned_house(path, topic)


def test_house_system_is_explicit_caller_policy_not_regiomontanus_default() -> None:
    profile = _profile(
        houses=_houses(system=HouseSystem.PLACIDUS),
        house_system=HouseSystem.PLACIDUS,
    )

    assert profile.house_policy.house_system == HouseSystem.PLACIDUS
    assert profile.chart_policy.state is HoraryEvidenceState.EVALUATED
    assert profile.significators.principal_querent.body == "Mercury"


def test_house_policy_mismatch_fails_closed_without_using_supplied_cusps() -> None:
    question = _question()
    profile = evaluate_horary_evidence(
        question,
        _geometry(question, houses=_houses(system=HouseSystem.PLACIDUS)),
        house_policy=HoraryHousePolicy(HouseSystem.REGIOMONTANUS),
    )

    assert profile.chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE
    assert profile.chart_policy.reason == "house_result_requested_system_does_not_match_caller_policy"
    assert profile.significators.state is HoraryEvidenceState.NOT_EVALUABLE
    assert profile.significators.principal_querent.body is None
    assert profile.perfection.reason == "principal_significators_not_evaluable"


def test_house_fallback_fails_closed() -> None:
    houses = _houses(
        system=HouseSystem.REGIOMONTANUS,
        effective_system=HouseSystem.PORPHYRY,
        fallback=True,
    )
    profile = _profile(houses=houses)

    assert profile.chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE
    assert profile.significators.same_body_principals is None


def test_default_house_result_policy_is_rejected_even_without_fallback() -> None:
    profile = _profile(houses=_houses(policy=HousePolicy.default()))

    assert profile.chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE
    assert profile.chart_policy.reason == "house_result_policy_is_not_strict"
    assert profile.significators.state is HoraryEvidenceState.NOT_EVALUABLE


@pytest.mark.parametrize(
    "geometry_changes, expected_reason",
    (
        ({"question_id": "different-question"}, "house_geometry_question_id_mismatch"),
        ({"latitude_deg": _LATITUDE + 1.0}, "house_geometry_location_mismatch"),
        ({"longitude_deg": _LONGITUDE + 1.0}, "house_geometry_location_mismatch"),
        ({"jd_ut1": _JD_UT1 + 1.0}, "house_geometry_epoch_mismatch"),
    ),
)
def test_computed_house_geometry_binding_mismatches_fail_closed(
    geometry_changes: dict[str, str | float],
    expected_reason: str,
) -> None:
    question = _question()
    geometry = replace(_geometry(question), **geometry_changes)
    profile = _profile(question=question, geometry=geometry)

    assert profile.house_geometry is geometry
    assert profile.chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE
    assert profile.chart_policy.reason == expected_reason
    assert profile.significators.state is HoraryEvidenceState.NOT_EVALUABLE


def test_computed_geometry_cannot_evaluate_against_unresolved_question_epoch() -> None:
    question = _question(time=_unresolved_time())
    geometry = HoraryHouseGeometryReceipt(
        question_id=question.question_id,
        latitude_deg=question.latitude_deg,
        longitude_deg=question.longitude_deg,
        source_id=_GEOMETRY_SOURCE_ID,
        source_mode=HoraryGeometrySourceMode.COMPUTED,
        jd_ut1=_JD_UT1,
        house_cusps=_houses(),
    )
    profile = _profile(question=question, geometry=geometry)

    assert profile.chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE
    assert profile.chart_policy.reason == "computed_house_geometry_requires_evaluated_question_epoch"


def test_same_body_principals_keep_assignments_but_block_pair_perfection() -> None:
    houses = _houses(cusp_overrides={9: 60.0})  # Gemini, also ruled by Mercury.
    profile = _profile(houses=houses)

    assert profile.significators.state is HoraryEvidenceState.EVALUATED
    assert profile.significators.same_body_principals is True
    assert profile.perfection.state is HoraryPerfectionState.NOT_EVALUABLE
    assert profile.perfection.reason == "principal_significators_are_same_body"


def test_exact_hour_lord_identity_and_nature_paths_are_visible() -> None:
    profile = _profile(hour=_hour("Mercury"))

    assert profile.hour_agreement.state is HoraryHourAgreementState.AGREES
    assert tuple(item.rule_id for item in profile.hour_agreement.rules) == (
        "same_planet",
        "triplicity",
        "same_nature",
    )
    assert [item.state for item in profile.hour_agreement.rules] == [
        HoraryHourRuleState.MATCHED,
        HoraryHourRuleState.NOT_MATCHED,
        HoraryHourRuleState.MATCHED,
    ]
    assert profile.hour_agreement.rules[0].derived_by == "exact_planet_identity"


def test_same_nature_can_establish_hour_agreement_without_identity_or_triplicity() -> None:
    profile = _profile(hour=_hour("Saturn"))

    assert profile.hour_agreement.state is HoraryHourAgreementState.AGREES
    assert [item.state for item in profile.hour_agreement.rules] == [
        HoraryHourRuleState.NOT_MATCHED,
        HoraryHourRuleState.NOT_MATCHED,
        HoraryHourRuleState.MATCHED,
    ]
    assert ("hour_lord_nature", "cold_dry") in profile.hour_agreement.rules[2].observed
    assert (
        "ascendant_lord_nature",
        "cold_dry",
    ) in profile.hour_agreement.rules[2].observed


@pytest.mark.parametrize(
    "asc, day_ruler, night_ruler, element",
    (
        (240.0, Body.SUN, Body.JUPITER, "fire"),
        (270.0, Body.VENUS, Body.MOON, "earth"),
        (180.0, Body.SATURN, Body.MERCURY, "air"),
        (90.0, Body.MARS, Body.MARS, "water"),
    ),
)
def test_lilly_triplicity_table_is_frozen_for_day_and_night(
    asc: float,
    day_ruler: str,
    night_ruler: str,
    element: str,
) -> None:
    houses = _uniform_houses(asc)
    for hour_number, ruler, sect in (
        (1, day_ruler, "day"),
        (13, night_ruler, "night"),
    ):
        profile = _profile(
            houses=houses,
            house_system=HouseSystem.EQUAL,
            hour=_hour(ruler, hour_number=hour_number),
        )
        triplicity = profile.hour_agreement.rules[1]

        assert triplicity.rule_id == "triplicity"
        assert triplicity.state is HoraryHourRuleState.MATCHED
        assert ("element", element) in triplicity.observed
        assert ("sect", sect) in triplicity.observed
        assert ("triplicity_ruler", ruler) in triplicity.observed


def test_lilly_primary_nature_table_is_frozen_for_all_seven_planets() -> None:
    assert dict(horary_module._PLANETARY_NATURE) == {
        Body.SUN: ("hot", "dry"),
        Body.MOON: ("cold", "moist"),
        Body.MERCURY: ("cold", "dry"),
        Body.VENUS: ("cold", "moist"),
        Body.MARS: ("hot", "dry"),
        Body.JUPITER: ("hot", "moist"),
        Body.SATURN: ("cold", "dry"),
    }


def test_all_three_hour_paths_can_fail_without_rejecting_the_chart() -> None:
    profile = _profile(hour=_hour(Body.JUPITER))

    assert profile.chart_policy.state is HoraryEvidenceState.EVALUATED
    assert profile.hour_agreement.state is HoraryHourAgreementState.DOES_NOT_AGREE
    assert all(
        item.state is HoraryHourRuleState.NOT_MATCHED
        for item in profile.hour_agreement.rules
    )


def test_hour_receipt_cannot_smuggle_precomputed_triplicity_or_nature_claims() -> None:
    parameters = inspect.signature(HoraryPlanetaryHourReceipt).parameters

    assert "triplicity_agreement" not in parameters
    assert "nature_agreement" not in parameters


def test_missing_planetary_hour_is_typed_not_evaluable() -> None:
    profile = _profile()

    assert profile.hour_agreement.state is HoraryHourAgreementState.NOT_EVALUABLE
    assert profile.hour_agreement.reason == "planetary_hour_receipt_not_supplied"
    assert all(item.state is HoraryHourRuleState.NOT_EVALUABLE for item in profile.hour_agreement.rules)


@pytest.mark.parametrize(
    "hour_changes, expected_reason",
    (
        ({"question_id": "different-question"}, "planetary_hour_question_id_mismatch"),
        ({"latitude_deg": _LATITUDE + 1.0}, "planetary_hour_location_mismatch"),
        ({"longitude_deg": _LONGITUDE + 1.0}, "planetary_hour_location_mismatch"),
    ),
)
def test_planetary_hour_binding_mismatches_are_preserved_and_fail_closed(
    hour_changes: dict[str, str | float],
    expected_reason: str,
) -> None:
    receipt = replace(_hour(Body.MERCURY), **hour_changes)
    profile = _profile(hour=receipt)

    assert profile.hour_agreement.state is HoraryHourAgreementState.NOT_EVALUABLE
    assert profile.hour_agreement.reason == expected_reason
    assert profile.hour_agreement.planetary_hour_receipt is receipt


def test_planetary_hour_epoch_must_match_the_question_event() -> None:
    receipt = _hour(Body.MERCURY, jd_ut1=_JD_UT1 + 1.0)
    profile = _profile(hour=receipt)

    assert profile.hour_agreement.state is HoraryHourAgreementState.NOT_EVALUABLE
    assert profile.hour_agreement.reason == "planetary_hour_question_epoch_mismatch"
    assert profile.hour_agreement.planetary_hour_receipt is receipt


def test_planetary_hour_constructor_rejects_event_outside_interval() -> None:
    receipt = _hour(Body.MERCURY)

    with pytest.raises(ValueError, match="inside its exact hour interval"):
        replace(receipt, jd_ut1=receipt.hour_end_jd)


def test_planetary_hour_rejects_hour_thirteen_inside_a_daylight_period() -> None:
    daylight = _hour(Body.MERCURY, hour_number=1)

    with pytest.raises(ValueError, match="preceding sunset before following sunrise"):
        replace(daylight, hour_number=13)


def test_planetary_hour_rejects_non_exact_unequal_hour_boundaries() -> None:
    receipt = _hour(Body.MERCURY, hour_number=7)

    with pytest.raises(ValueError, match="exact twelfth"):
        replace(receipt, hour_start_jd=receipt.hour_start_jd + 0.001)


def test_chart_sect_is_bound_to_validated_day_and_night_hour_receipts() -> None:
    day = _profile(hour=_hour(Body.MERCURY, hour_number=1))
    night = _profile(hour=_hour(Body.MERCURY, hour_number=13))

    assert day.chart_sect.state is HoraryEvidenceState.EVALUATED
    assert day.chart_sect.sect is HoraryChartSect.DAY
    assert day.chart_sect.jd_ut1 == day.question.time.normalized_jd_ut1
    assert night.chart_sect.state is HoraryEvidenceState.EVALUATED
    assert night.chart_sect.sect is HoraryChartSect.NIGHT
    assert night.chart_sect.jd_ut1 == night.question.time.normalized_jd_ut1


def test_profile_revalidates_mutated_planetary_hour_interval_semantics() -> None:
    profile = _profile(hour=_hour(Body.MERCURY))
    receipt = profile.hour_agreement.planetary_hour_receipt
    assert receipt is not None
    object.__setattr__(receipt, "hour_end_jd", receipt.hour_end_jd + 0.01)

    with pytest.raises(ValueError, match="exact twelfth"):
        replace(profile)


@pytest.mark.parametrize(
    "asc, early_state, late_state",
    [
        (152.999999, HoraryRuleState.CAUTION, HoraryRuleState.SATISFIED),
        (153.0, HoraryRuleState.SATISFIED, HoraryRuleState.SATISFIED),
        (176.999999, HoraryRuleState.SATISFIED, HoraryRuleState.SATISFIED),
        (177.0, HoraryRuleState.SATISFIED, HoraryRuleState.CAUTION),
    ],
)
def test_ascendant_consideration_boundaries_are_exact(
    asc: float,
    early_state: HoraryRuleState,
    late_state: HoraryRuleState,
) -> None:
    profile = _profile(houses=_houses(asc=asc))

    assert _consideration(profile, "ascendant_below_three_degrees").state is early_state
    assert _consideration(profile, "ascendant_at_or_above_twenty_seven_degrees").state is late_state


@pytest.mark.parametrize(
    "longitude, expected",
    [
        (194.999999, HoraryRuleState.SATISFIED),
        (195.0, HoraryRuleState.CAUTION),
        (224.999999, HoraryRuleState.CAUTION),
        (225.0, HoraryRuleState.SATISFIED),
    ],
)
def test_via_combusta_uses_visible_half_open_boundaries(
    longitude: float,
    expected: HoraryRuleState,
) -> None:
    profile = _profile(
        considerations=HoraryConsiderationInputs(
            moon_placement=_placement(Body.MOON, longitude)
        )
    )

    assert _consideration(profile, "moon_in_via_combusta").state is expected


@pytest.mark.parametrize(
    "placement_changes, expected_reason",
    (
        ({"question_id": "different-question"}, "moon_placement_question_id_mismatch"),
        ({"latitude_deg": _LATITUDE + 1.0}, "moon_placement_location_mismatch"),
        (
            {"longitude_location_deg": _LONGITUDE + 1.0},
            "moon_placement_location_mismatch",
        ),
        (
            {"geometry_source_id": "different-geometry"},
            "moon_placement_geometry_source_mismatch",
        ),
        ({"jd_ut1": _JD_UT1 + 1.0}, "moon_placement_question_epoch_mismatch"),
        (
            {
                "source_mode": HoraryGeometrySourceMode.HISTORICAL_SOURCE_CHART_ASSIGNMENT,
                "jd_ut1": None,
            },
            "moon_placement_source_mode_mismatch",
        ),
    ),
)
def test_moon_placement_binding_mismatches_make_via_combusta_not_evaluable(
    placement_changes: dict[str, object],
    expected_reason: str,
) -> None:
    placement = replace(_placement(Body.MOON, 200.0), **placement_changes)
    inputs = HoraryConsiderationInputs(moon_placement=placement)
    profile = _profile(considerations=inputs)
    via = _consideration(profile, "moon_in_via_combusta")

    assert profile.consideration_inputs is inputs
    assert profile.consideration_inputs.moon_placement is placement
    assert via.state is HoraryRuleState.NOT_EVALUABLE
    assert via.reason == expected_reason


def test_forged_saturn_house_is_rederived_from_bound_geometry_and_rejected() -> None:
    valid = _placement(Body.SATURN, 160.0)
    forged_house = 7 if valid.house != 7 else 1
    forged = replace(valid, house=forged_house)
    inputs = HoraryConsiderationInputs(saturn_placement=forged)
    profile = _profile(considerations=inputs)

    assert profile.consideration_inputs.saturn_placement is forged
    for rule_id in ("saturn_in_first_house", "saturn_in_seventh_house"):
        evidence = _consideration(profile, rule_id)
        assert evidence.state is HoraryRuleState.NOT_EVALUABLE
        assert evidence.reason == "saturn_placement_house_mismatch"


def test_first_ruler_combustion_composes_typed_solar_proximity_truth() -> None:
    profile = _profile(
        considerations=HoraryConsiderationInputs(
            first_ruler_solar_proximity=_solar_receipt(
                SolarProximityTruth(
                    status=TruthEvaluationStatus.EVALUATED,
                    band=SolarProximityBand.COMBUST,
                    distance_from_sun_deg=5.0,
                )
            )
        )
    )

    combust = _consideration(profile, "first_house_ruler_combust")
    assert combust.state is HoraryRuleState.CAUTION
    assert ("solar_proximity_band", "combust") in combust.observed


def test_not_evaluable_solar_proximity_does_not_fabricate_combustion_truth() -> None:
    profile = _profile(
        considerations=HoraryConsiderationInputs(
            first_ruler_solar_proximity=_solar_receipt(
                SolarProximityTruth(
                    status=TruthEvaluationStatus.NOT_EVALUABLE,
                    band=None,
                    distance_from_sun_deg=None,
                    reason="sun_dependency_missing",
                )
            )
        )
    )

    combust = _consideration(profile, "first_house_ruler_combust")
    assert combust.state is HoraryRuleState.NOT_EVALUABLE
    assert combust.reason == "first_house_ruler_solar_proximity_truth_not_evaluable"
    assert ("solar_proximity_reason", "sun_dependency_missing") in combust.observed


def test_solar_proximity_receipt_for_wrong_body_fails_closed() -> None:
    profile = _profile(
        considerations=HoraryConsiderationInputs(
            first_ruler_solar_proximity=_solar_receipt(
                SolarProximityTruth(
                    status=TruthEvaluationStatus.EVALUATED,
                    band=SolarProximityBand.CLEAR,
                    distance_from_sun_deg=30.0,
                ),
                body=Body.VENUS,
            )
        )
    )

    combust = _consideration(profile, "first_house_ruler_combust")
    assert combust.state is HoraryRuleState.NOT_EVALUABLE
    assert combust.reason == "solar_proximity_receipt_body_does_not_match_first_house_ruler"


@pytest.mark.parametrize(
    "receipt_changes, expected_reason",
    (
        ({"question_id": "different-question"}, "solar_proximity_question_id_mismatch"),
        ({"latitude_deg": _LATITUDE + 1.0}, "solar_proximity_location_mismatch"),
        ({"longitude_deg": _LONGITUDE + 1.0}, "solar_proximity_location_mismatch"),
        (
            {"geometry_source_id": "different-geometry"},
            "solar_proximity_geometry_source_mismatch",
        ),
        ({"jd_ut1": _JD_UT1 + 1.0}, "solar_proximity_question_epoch_mismatch"),
        (
            {
                "source_mode": HoraryGeometrySourceMode.HISTORICAL_SOURCE_CHART_ASSIGNMENT,
                "jd_ut1": None,
            },
            "solar_proximity_source_mode_mismatch",
        ),
    ),
)
def test_solar_proximity_binding_mismatches_fail_closed_and_preserve_receipt(
    receipt_changes: dict[str, object],
    expected_reason: str,
) -> None:
    truth = SolarProximityTruth(
        status=TruthEvaluationStatus.EVALUATED,
        band=SolarProximityBand.CLEAR,
        distance_from_sun_deg=30.0,
    )
    receipt = replace(_solar_receipt(truth), **receipt_changes)
    inputs = HoraryConsiderationInputs(first_ruler_solar_proximity=receipt)
    profile = _profile(considerations=inputs)
    combust = _consideration(profile, "first_house_ruler_combust")

    assert profile.consideration_inputs is inputs
    assert profile.consideration_inputs.first_ruler_solar_proximity is receipt
    assert combust.state is HoraryRuleState.NOT_EVALUABLE
    assert combust.reason == expected_reason


def test_profile_preserves_all_caller_supplied_atomic_receipts() -> None:
    question = _question()
    geometry = _geometry(question)
    hour = _hour(Body.MERCURY)
    moon = _placement(Body.MOON, 200.0, question=question, geometry=geometry)
    saturn = _placement(Body.SATURN, 160.0, question=question, geometry=geometry)
    solar = _solar_receipt(
        SolarProximityTruth(
            status=TruthEvaluationStatus.EVALUATED,
            band=SolarProximityBand.CLEAR,
            distance_from_sun_deg=30.0,
        ),
        question=question,
        geometry=geometry,
    )
    inputs = HoraryConsiderationInputs(
        moon_placement=moon,
        saturn_placement=saturn,
        first_ruler_solar_proximity=solar,
    )
    profile = _profile(
        question=question,
        geometry=geometry,
        hour=hour,
        considerations=inputs,
    )

    assert profile.question is question
    assert profile.house_geometry is geometry
    assert profile.hour_agreement.planetary_hour_receipt is hour
    assert profile.consideration_inputs is inputs
    assert profile.consideration_inputs.moon_placement is moon
    assert profile.consideration_inputs.saturn_placement is saturn
    assert profile.consideration_inputs.first_ruler_solar_proximity is solar


def test_missing_consideration_dependencies_never_fabricate_clear_truth() -> None:
    profile = _profile()
    by_id = {item.rule_id: item for item in profile.considerations}

    assert by_id["moon_in_via_combusta"].state is HoraryRuleState.NOT_EVALUABLE
    assert by_id["saturn_in_first_house"].state is HoraryRuleState.NOT_EVALUABLE
    assert by_id["saturn_in_seventh_house"].state is HoraryRuleState.NOT_EVALUABLE
    assert by_id["first_house_ruler_combust"].state is HoraryRuleState.NOT_EVALUABLE


def test_ambiguous_late_moon_and_balanced_testimony_rules_are_excluded() -> None:
    profile = _profile()
    rule_ids = {item.rule_id for item in profile.considerations}

    assert not any("late_moon" in rule_id for rule_id in rule_ids)
    assert not any("void_of_course" in rule_id for rule_id in rule_ids)
    assert not any("seventh_ruler" in rule_id for rule_id in rule_ids)
    assert not any("balanced" in rule_id for rule_id in rule_ids)
    assert "late_moon_numeric_rule" in profile.provenance.excluded_components
    assert "void_of_course_sign_mitigation" in profile.provenance.excluded_components
    assert "seventh_cusp_or_ruler_impediment" in profile.provenance.excluded_components
    assert "balanced_testimony_aggregation" in profile.provenance.excluded_components
    assert any("late_moon" in item for item in profile.provenance.unresolved_policies)
    assert any("early_ascendant" in item for item in profile.provenance.unresolved_policies)
    assert any("late_ascendant" in item for item in profile.provenance.unresolved_policies)
    assert not any(
        "hour_lord_triplicity_and_nature" in item
        for item in profile.provenance.unresolved_policies
    )


def test_existing_lilly_perfection_analysis_is_composed_by_identity() -> None:
    analysis = _perfection()
    profile = _profile(hour=_hour(Body.MERCURY), perfection=analysis)

    assert profile.perfection.state is HoraryPerfectionState.COMPOSED
    assert profile.perfection.analysis is analysis
    assert profile.perfection.principal_querent == "Mercury"
    assert profile.perfection.principal_quesited == "Mars"
    assert profile.perfection.search_policy is MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1
    assert profile.perfection.search_policy.historical_duration_claim is False
    assert (
        profile.perfection.search_policy.interval_selection
        == "caller_supplied_start_and_end_preserved"
    )


def test_perfection_requires_an_evaluated_bound_chart_sect() -> None:
    analysis = _perfection()
    profile = _profile(perfection=analysis)

    assert profile.chart_sect.state is HoraryEvidenceState.NOT_EVALUABLE
    assert profile.chart_sect.reason == "planetary_hour_receipt_not_supplied"
    assert profile.perfection_analysis_input is analysis
    assert profile.perfection.state is HoraryPerfectionState.NOT_EVALUABLE
    assert profile.perfection.reason == "chart_sect_not_evaluable_for_perfection"


def test_night_perfection_composes_only_with_matching_night_chart_sect() -> None:
    analysis = _perfection(is_day_chart=False)
    profile = _profile(
        hour=_hour(Body.MERCURY, hour_number=13),
        perfection=analysis,
    )

    assert profile.chart_sect.sect is HoraryChartSect.NIGHT
    assert profile.perfection.state is HoraryPerfectionState.COMPOSED
    assert profile.perfection.analysis is analysis


def test_perfection_analysis_sect_must_match_bound_question_chart_sect() -> None:
    with pytest.raises(ValueError, match="sect does not match"):
        _profile(
            hour=_hour(Body.MERCURY, hour_number=13),
            perfection=_perfection(is_day_chart=True),
        )
    day_profile = _profile(
        hour=_hour(Body.MERCURY, hour_number=1),
        perfection=_perfection(is_day_chart=True),
    )
    with pytest.raises(ValueError, match="sect does not match"):
        replace(
            day_profile,
            perfection_analysis_input=_perfection(is_day_chart=False),
        )


def test_wrong_perfection_pair_is_rejected_not_reinterpreted() -> None:
    with pytest.raises(ValueError, match="principal pair"):
        _profile(perfection=_perfection("Mercury", "Venus"))


def test_perfection_epoch_must_match_question_and_geometry() -> None:
    analysis = _perfection()

    with pytest.raises(ValueError, match="jd_start must match the question epoch"):
        _profile(perfection=replace(analysis, jd_start=_JD_UT1 + 0.5))


@pytest.mark.parametrize(
    "analysis_changes, expected_exception, expected_message",
    (
        ({"profile_id": "forged-profile"}, ValueError, "exact admitted Lilly policy"),
        ({"profile_version": "9.9.9"}, ValueError, "exact admitted Lilly policy"),
        ({"policy": object()}, TypeError, "concrete LillyPerfectionPolicy"),
    ),
)
def test_perfection_requires_exact_admitted_profile_version_and_policy(
    analysis_changes: dict[str, object],
    expected_exception: type[Exception],
    expected_message: str,
) -> None:
    with pytest.raises(expected_exception, match=expected_message):
        _profile(perfection=replace(_perfection(), **analysis_changes))


def test_custom_equality_cannot_impersonate_the_canonical_lilly_policy() -> None:
    forged = replace(_perfection(), policy=_ForgedPolicy())

    with pytest.raises(TypeError, match="concrete LillyPerfectionPolicy"):
        _direct_perfection_evidence(forged)
    with pytest.raises(TypeError, match="concrete LillyPerfectionPolicy"):
        _profile(hour=_hour(Body.MERCURY), perfection=forged)

    equal_but_noncanonical = replace(
        _perfection(),
        policy=LillyPerfectionPolicy(),
    )
    with pytest.raises(ValueError, match="canonical Lilly policy identity"):
        _direct_perfection_evidence(equal_but_noncanonical)


def test_custom_equality_cannot_impersonate_other_horary_policy_guards() -> None:
    houses = _houses()
    object.__setattr__(houses, "policy", _ForgedPolicy())
    profile = _profile(houses=houses)

    assert profile.chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE
    assert profile.chart_policy.reason == "house_result_policy_is_not_strict"

    analysis = _perfection()
    with pytest.raises(TypeError, match="search_policy must be"):
        HoraryPerfectionEvidence(
            state=HoraryPerfectionState.COMPOSED,
            principal_querent=Body.MERCURY,
            principal_quesited=Body.MARS,
            analysis=analysis,
            reason=None,
            search_policy=_ForgedPolicy(),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="fixed Moira Horary perfection safety policy"):
        HoraryPerfectionEvidence(
            state=HoraryPerfectionState.COMPOSED,
            principal_querent=Body.MERCURY,
            principal_quesited=Body.MARS,
            analysis=analysis,
            reason=None,
            search_policy=HoraryPerfectionSearchPolicy(),
        )


def test_perfection_requires_nonempty_reader_provenance() -> None:
    with pytest.raises(ValueError, match="non-empty reader provenance"):
        _profile(perfection=replace(_perfection(), reader_provenance="   "))


@pytest.mark.parametrize("forgery", ("missing", "duplicate"))
def test_perfection_requires_all_seven_unique_initial_body_states(forgery: str) -> None:
    analysis = _perfection()
    states = analysis.initial_states[:-1]
    if forgery == "duplicate":
        states += (analysis.initial_states[0],)

    with pytest.raises(ValueError, match="all seven unique initial body states"):
        _profile(perfection=replace(analysis, initial_states=states))


@pytest.mark.parametrize("forgery", ("missing", "out_of_order"))
def test_perfection_requires_exactly_six_source_ordered_witnesses(forgery: str) -> None:
    analysis = _perfection()
    if forgery == "missing":
        witnesses = analysis.witnesses[:-1]
    else:
        witnesses = (
            analysis.witnesses[1],
            analysis.witnesses[0],
            *analysis.witnesses[2:],
        )
    present = tuple(item.kind for item in witnesses if item.kind in analysis.present_kinds)
    indeterminate = tuple(
        item.kind for item in witnesses if item.kind in analysis.indeterminate_kinds
    )
    forged = replace(
        analysis,
        witnesses=witnesses,
        present_kinds=present,
        indeterminate_kinds=indeterminate,
    )

    with pytest.raises(ValueError, match="six source-ordered witnesses"):
        _profile(perfection=forged)


def test_perfection_requires_the_admitted_analysis_authority() -> None:
    with pytest.raises(ValueError, match="authority receipt is not admitted"):
        _profile(perfection=replace(_perfection(), authorities=("forged authority",)))


@pytest.mark.parametrize(
    "analysis_changes, expected_exception, expected_message",
    (
        ({"profile_id": "forged-profile"}, ValueError, "exact admitted Lilly policy"),
        ({"profile_version": "9.9.9"}, ValueError, "exact admitted Lilly policy"),
        ({"policy": object()}, TypeError, "concrete LillyPerfectionPolicy"),
        ({"reader_provenance": "   "}, ValueError, "non-empty reader provenance"),
        (
            {"authorities": ("forged authority",)},
            ValueError,
            "authority receipt is not admitted",
        ),
        ({"scoring": "10"}, ValueError, "scoring must remain not_provided"),
        ({"advice_language": "yes"}, ValueError, "advice must remain not_provided"),
    ),
)
def test_direct_perfection_constructor_rejects_analysis_contract_forgery(
    analysis_changes: dict[str, object],
    expected_exception: type[Exception],
    expected_message: str,
) -> None:
    forged = replace(_perfection(), **analysis_changes)

    with pytest.raises(expected_exception, match=expected_message):
        _direct_perfection_evidence(forged)


def test_direct_perfection_constructor_rejects_state_and_witness_forgery() -> None:
    analysis = _perfection()
    duplicate_states = analysis.initial_states[:-1] + (analysis.initial_states[0],)
    with pytest.raises(ValueError, match="all seven unique initial body states"):
        _direct_perfection_evidence(replace(analysis, initial_states=duplicate_states))

    reordered = (analysis.witnesses[1], analysis.witnesses[0], *analysis.witnesses[2:])
    with pytest.raises(ValueError, match="six source-ordered witnesses"):
        _direct_perfection_evidence(replace(analysis, witnesses=reordered))

    forged_witness = replace(analysis.witnesses[0], source_reference="forged authority")
    with pytest.raises(ValueError, match="witness authority receipt is not admitted"):
        _direct_perfection_evidence(
            replace(analysis, witnesses=(forged_witness, *analysis.witnesses[1:]))
        )


def test_direct_perfection_constructor_rejects_pair_and_complete_judgement_forgery() -> None:
    analysis = _perfection()
    with pytest.raises(ValueError, match="principal pair"):
        HoraryPerfectionEvidence(
            state=HoraryPerfectionState.COMPOSED,
            principal_querent=Body.VENUS,
            principal_quesited=Body.MARS,
            analysis=analysis,
            reason=None,
        )

    forged_complete = _perfection()
    object.__setattr__(forged_complete, "complete_electional_judgement", True)
    with pytest.raises(ValueError, match="cannot claim complete judgement"):
        _direct_perfection_evidence(forged_complete)


@pytest.mark.parametrize("forgery", ("state", "event_ids"))
def test_perfection_reconstructs_and_rejects_forged_witness_semantics(
    forgery: str,
) -> None:
    analysis = _perfection()
    original = analysis.witnesses[0]
    if forgery == "state":
        witness = replace(
            original,
            state=ClassicalPerfectionState.PRESENT,
            event_ids=("forged-event",),
        )
    else:
        witness = replace(original, event_ids=("forged-event",))
    witnesses = (witness, *analysis.witnesses[1:])
    present = tuple(
        item.kind
        for item in witnesses
        if item.state is ClassicalPerfectionState.PRESENT
    )
    indeterminate = tuple(
        item.kind
        for item in witnesses
        if item.state is ClassicalPerfectionState.INDETERMINATE
    )
    forged = replace(
        analysis,
        witnesses=witnesses,
        present_kinds=present,
        indeterminate_kinds=indeterminate,
    )

    with pytest.raises(ValueError, match="witness truth must be reconstructed"):
        _direct_perfection_evidence(forged)
    with pytest.raises(ValueError, match="witness truth must be reconstructed"):
        _profile(hour=_hour(Body.MERCURY), perfection=forged)
    valid_profile = _profile(hour=_hour(Body.MERCURY), perfection=analysis)
    with pytest.raises(ValueError, match="witness truth must be reconstructed"):
        replace(valid_profile, perfection_analysis_input=forged)


def test_perfection_nested_strenum_fields_reject_raw_strings() -> None:
    analysis = _perfection()
    witness = analysis.witnesses[0]
    for changes in (
        {"kind": witness.kind.value},
        {"state": witness.state.value},
    ):
        forged_witness = replace(witness, **changes)
        forged = replace(
            analysis,
            witnesses=(forged_witness, *analysis.witnesses[1:]),
        )
        with pytest.raises(TypeError, match="witness kind and state"):
            _direct_perfection_evidence(forged)

    forged_summary = _perfection()
    object.__setattr__(forged_summary, "present_kinds", (witness.kind.value,))
    with pytest.raises(TypeError, match="summary kinds"):
        _direct_perfection_evidence(forged_summary)

    event = ClassicalPerfectionEvent(
        event_id="enum-forgery",
        jd_ut=_JD_UT1 + 1.0,
        kind=ClassicalPerfectionEventKind.ASPECT_EXACT,
        actor=Body.MERCURY,
        target=Body.MARS,
        aspect="trine",
        directional_angle_deg=120.0,
    )
    object.__setattr__(event, "kind", event.kind.value)
    forged_event = _perfection()
    object.__setattr__(forged_event, "events", (event,))
    with pytest.raises(TypeError, match="event kind"):
        _direct_perfection_evidence(forged_event)


def test_perfection_rejects_non_boolean_sect_and_overlong_search_interval() -> None:
    non_boolean_sect = replace(_perfection(), is_day_chart=1)
    overlong = replace(_perfection(), jd_end=_JD_UT1 + 32.0)

    with pytest.raises(TypeError, match="is_day_chart must be a bool"):
        _direct_perfection_evidence(non_boolean_sect)
    with pytest.raises(TypeError, match="is_day_chart must be a bool"):
        _profile(hour=_hour(Body.MERCURY), perfection=non_boolean_sect)
    with pytest.raises(ValueError, match="fixed finite Moira Horary safety policy"):
        _direct_perfection_evidence(overlong)
    with pytest.raises(ValueError, match="fixed finite Moira Horary safety policy"):
        _profile(hour=_hour(Body.MERCURY), perfection=overlong)


def test_question_time_is_explicit_and_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        HoraryQuestionTimeReceipt(
            state=HoraryEvidenceState.EVALUATED,
            stated_basis=HoraryQuestionTimeBasis.QUESTION_PROPOSED_AND_FIGURE_ERECTED,
            stated_basis_source="caller receipt",
            source_calendar=HorarySourceCalendar.GREGORIAN,
            source_instant_label="2026-08-11 12:00 local",
            normalized_instant=datetime(2026, 8, 11, 12, 0),
            normalized_jd_ut1=2461264.0,
            conversion_policy_id="test",
            reason=None,
        )


@pytest.mark.parametrize(
    "alternate_basis",
    (
        HoraryQuestionTimeBasis.UNDERSTOOD_BY_ASTROLOGER,
        HoraryQuestionTimeBasis.LETTER_OPENED_AND_UNDERSTOOD,
        HoraryQuestionTimeBasis.SETTLED_SELF_QUESTION,
        HoraryQuestionTimeBasis.CALLER_SUPPLIED_OTHER,
    ),
)
def test_alternate_question_time_basis_cannot_claim_evaluated_lilly_epoch(
    alternate_basis: HoraryQuestionTimeBasis,
) -> None:
    with pytest.raises(ValueError, match="only question_proposed"):
        replace(_evaluated_time(), stated_basis=alternate_basis)


def test_question_receipt_has_no_free_calendar_or_time_basis_strings() -> None:
    parameters = inspect.signature(HoraryQuestionReceipt).parameters

    assert "calendar" not in parameters
    assert "time_basis_id" not in parameters
    assert "event_time" not in parameters
    assert parameters["time"].annotation in {
        "HoraryQuestionTimeReceipt",
        HoraryQuestionTimeReceipt,
    }


@pytest.mark.parametrize(
    "alternate_basis",
    (
        HoraryQuestionTimeBasis.UNDERSTOOD_BY_ASTROLOGER,
        HoraryQuestionTimeBasis.LETTER_OPENED_AND_UNDERSTOOD,
        HoraryQuestionTimeBasis.SETTLED_SELF_QUESTION,
        HoraryQuestionTimeBasis.CALLER_SUPPLIED_OTHER,
    ),
)
def test_alternate_question_time_bases_are_preserved_but_not_evaluable(
    alternate_basis: HoraryQuestionTimeBasis,
) -> None:
    time = _unresolved_time(basis=alternate_basis)
    question = _question(time=time)
    geometry = _geometry(
        question,
        source_mode=HoraryGeometrySourceMode.HISTORICAL_SOURCE_CHART_ASSIGNMENT,
    )
    profile = _profile(
        question=question,
        geometry=geometry,
        hour=_hour(Body.MERCURY),
        perfection=_perfection(),
    )

    assert profile.question.time.stated_basis is alternate_basis
    assert profile.question.time.normalized_jd_ut1 is None
    assert profile.hour_agreement.state is HoraryHourAgreementState.NOT_EVALUABLE
    assert profile.perfection.state is HoraryPerfectionState.NOT_EVALUABLE


def test_profile_and_nested_policy_are_immutable() -> None:
    profile = _profile()

    with pytest.raises(FrozenInstanceError):
        profile.house_policy.house_system = HouseSystem.PLACIDUS  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        profile.provenance.scoring = "10"  # type: ignore[misc]


def test_profile_replace_cannot_splice_question_identity_location_or_epoch() -> None:
    profile = _profile(hour=_hour(Body.MERCURY), perfection=_perfection())
    shifted_time = replace(
        profile.question.time,
        normalized_jd_ut1=_JD_UT1 + 1.0,
    )
    forged_questions = (
        replace(profile.question, question_id="different-question"),
        replace(profile.question, latitude_deg=_LATITUDE + 1.0),
        replace(profile.question, longitude_deg=_LONGITUDE + 1.0),
        replace(profile.question, time=shifted_time),
    )

    for forged_question in forged_questions:
        with pytest.raises(ValueError, match="must derive from the profile's bound input receipts"):
            replace(profile, question=forged_question)


def test_profile_replace_cannot_keep_evaluated_policy_with_permissive_houses() -> None:
    profile = _profile()
    permissive_cusps = replace(
        profile.house_geometry.house_cusps,
        policy=HousePolicy.default(),
    )
    forged_geometry = replace(profile.house_geometry, house_cusps=permissive_cusps)

    with pytest.raises(ValueError, match="chart_policy must derive"):
        replace(profile, house_geometry=forged_geometry)


def test_profile_replace_rejects_spliced_hour_assignment_and_turn_receipts() -> None:
    profile = _profile(hour=_hour(Body.MERCURY))
    foreign_question = _question(question_id="foreign-question")
    foreign_geometry = _geometry(foreign_question)
    foreign_profile = _profile(
        question=foreign_question,
        geometry=foreign_geometry,
        hour=_hour(Body.MERCURY, question_id="foreign-question"),
    )
    alternate_assignments = _profile(
        houses=_uniform_houses(180.0),
        house_system=HouseSystem.EQUAL,
    ).significators

    for field_name, forged_component in (
        ("hour_agreement", foreign_profile.hour_agreement),
        ("significators", alternate_assignments),
        ("turned_house", resolve_turned_house((7,), 2)),
    ):
        expected_component = "chart_sect" if field_name == "hour_agreement" else field_name
        with pytest.raises(ValueError, match=f"{expected_component} must derive"):
            replace(profile, **{field_name: forged_component})


def test_profile_replace_rejects_spliced_body_and_solar_receipts() -> None:
    question = _question()
    geometry = _geometry(question)
    moon = _placement(Body.MOON, 200.0, question=question, geometry=geometry)
    saturn = _placement(Body.SATURN, 160.0, question=question, geometry=geometry)
    solar = _solar_receipt(
        SolarProximityTruth(
            status=TruthEvaluationStatus.EVALUATED,
            band=SolarProximityBand.CLEAR,
            distance_from_sun_deg=30.0,
        ),
        question=question,
        geometry=geometry,
    )
    inputs = HoraryConsiderationInputs(
        moon_placement=moon,
        saturn_placement=saturn,
        first_ruler_solar_proximity=solar,
    )
    profile = _profile(
        question=question,
        geometry=geometry,
        considerations=inputs,
    )
    forged_inputs = (
        replace(inputs, moon_placement=replace(moon, question_id="foreign-question")),
        replace(inputs, saturn_placement=replace(saturn, geometry_source_id="foreign")),
        replace(inputs, first_ruler_solar_proximity=replace(solar, jd_ut1=_JD_UT1 + 1.0)),
    )

    for forged in forged_inputs:
        with pytest.raises(ValueError, match="considerations must derive"):
            replace(profile, consideration_inputs=forged)


def test_every_horary_strenum_field_rejects_its_raw_string_value() -> None:
    question = _question()
    geometry = _geometry(question)
    moon = _placement(Body.MOON, 200.0, question=question, geometry=geometry)
    saturn = _placement(Body.SATURN, 160.0, question=question, geometry=geometry)
    solar = _solar_receipt(
        SolarProximityTruth(
            status=TruthEvaluationStatus.EVALUATED,
            band=SolarProximityBand.CLEAR,
            distance_from_sun_deg=30.0,
        ),
        question=question,
        geometry=geometry,
    )
    profile = _profile(
        question=question,
        geometry=geometry,
        hour=_hour(Body.MERCURY),
        considerations=HoraryConsiderationInputs(
            moon_placement=moon,
            saturn_placement=saturn,
            first_ruler_solar_proximity=solar,
        ),
        perfection=_perfection(),
    )
    turn_step = profile.turned_house.steps[0]
    principal = profile.significators.principal_querent
    cases = (
        (profile.question.time, {"state": profile.question.time.state.value}),
        (
            profile.question.time,
            {"stated_basis": profile.question.time.stated_basis.value},
        ),
        (
            profile.question.time,
            {"source_calendar": profile.question.time.source_calendar.value},
        ),
        (
            profile.house_geometry,
            {"source_mode": profile.house_geometry.source_mode.value},
        ),
        (profile.chart_policy, {"state": profile.chart_policy.state.value}),
        (turn_step, {"kind": turn_step.kind.value}),
        (principal, {"role": principal.role.value}),
        (principal, {"state": principal.state.value}),
        (profile.significators, {"state": profile.significators.state.value}),
        (profile.chart_sect, {"state": profile.chart_sect.state.value}),
        (profile.chart_sect, {"sect": profile.chart_sect.sect.value}),
        (
            profile.hour_agreement.rules[0],
            {"state": profile.hour_agreement.rules[0].state.value},
        ),
        (
            profile.hour_agreement,
            {"state": profile.hour_agreement.state.value},
        ),
        (moon, {"source_mode": moon.source_mode.value}),
        (solar, {"source_mode": solar.source_mode.value}),
        (
            profile.considerations[0],
            {"state": profile.considerations[0].state.value},
        ),
        (profile.perfection, {"state": profile.perfection.state.value}),
    )

    for receipt, changes in cases:
        with pytest.raises(TypeError):
            replace(receipt, **changes)


def test_module_has_no_forbidden_import_and_only_adapter_calls_perfection_solver() -> None:
    tree = ast.parse(inspect.getsource(horary_module))
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.lstrip(".").split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)

    assert imported_roots.isdisjoint({"numpy", "scipy", "jplephem", "swisseph"})
    assert "classify_lilly_perfection_events" in called_names

    solver_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "lilly_perfection_at"
    ]
    adapter_tree = ast.parse(inspect.getsource(horary_module.horary_evidence_at))
    adapter_solver_calls = [
        node
        for node in ast.walk(adapter_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "lilly_perfection_at"
    ]
    atomic_tree = ast.parse(inspect.getsource(evaluate_horary_evidence))
    atomic_called_names = {
        node.func.id
        for node in ast.walk(atomic_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert len(solver_calls) == 1
    assert len(adapter_solver_calls) == 1
    assert "lilly_perfection_at" not in atomic_called_names

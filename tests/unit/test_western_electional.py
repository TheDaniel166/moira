"""Focused doctrine and boundary tests for the first Western electional profile."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest
from hypothesis import given, settings, strategies as st

import moira
import moira.facade as facade
import moira.western_electional as western
from moira.chart import ChartContext
from moira.constants import Body, HouseSystem, SIGNS
from moira.houses import HouseCusps, HousePolicy, classify_house_system
from moira.nodes import NodeData
from moira.planets import PlanetData


def _planet(
    name: str,
    longitude: float,
    speed: float = 1.0,
    *,
    is_topocentric: bool = False,
) -> PlanetData:
    return PlanetData(
        name=name,
        longitude=longitude % 360.0,
        latitude=0.0,
        distance=1.0,
        speed=speed,
        retrograde=speed < 0.0,
        is_topocentric=is_topocentric,
    )


def _houses(system: str = HouseSystem.PORPHYRY) -> HouseCusps:
    cusps = tuple(float(degree) for degree in range(0, 360, 30))
    return HouseCusps(
        system=system,
        cusps=cusps,
        asc=0.0,
        mc=270.0,
        armc=270.0,
        effective_system=system,
        classification=classify_house_system(system),
        policy=HousePolicy.default(),
    )


def _chart(
    *,
    moon_longitude: float = 40.0,
    moon_speed: float = 13.5,
    sun_longitude: float = 100.0,
    sun_speed: float = 1.0,
    mars_longitude: float = 200.0,
    saturn_longitude: float = 280.0,
    node_longitude: float = 80.0,
    houses: HouseCusps | None = None,
    include_moon: bool = True,
    include_sun: bool = True,
    include_mars: bool = True,
    include_saturn: bool = True,
    include_node: bool = True,
    moon_topocentric: bool = False,
) -> ChartContext:
    planets: dict[str, PlanetData] = {}
    if include_moon:
        planets[Body.MOON] = _planet(
            Body.MOON,
            moon_longitude,
            moon_speed,
            is_topocentric=moon_topocentric,
        )
    if include_sun:
        planets[Body.SUN] = _planet(Body.SUN, sun_longitude, sun_speed)
    if include_mars:
        planets[Body.MARS] = _planet(Body.MARS, mars_longitude, 0.5)
    if include_saturn:
        planets[Body.SATURN] = _planet(Body.SATURN, saturn_longitude, 0.1)
    nodes = {}
    if include_node:
        nodes[Body.TRUE_NODE] = NodeData(Body.TRUE_NODE, node_longitude, -0.05)
    return ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0,
        latitude=0.0,
        longitude=0.0,
        planets=planets,
        nodes=nodes,
        houses=_houses() if houses is None else houses,
    )


def _evaluation(
    chart: ChartContext,
    *,
    voc: bool | None = False,
    unavoidable_time_urgency: bool | None = None,
) -> western.RameseyMoonConditionEvaluation:
    return western.evaluate_ramesey_moon_condition(
        chart,
        void_of_course=voc,
        unavoidable_time_urgency=unavoidable_time_urgency,
        position_product=western.RAMESEY_MOON_CONDITION_V1.position_product,
        reader_provenance="synthetic_unit_fixture",
    )


def _rule(result: western.RameseyMoonConditionEvaluation, order: int) -> western.RameseyRuleWitness:
    return result.rules[order - 1]


def test_public_surface_is_promoted_through_root_and_facade() -> None:
    expected = {
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
        "WesternElectionalProfileId",
        "WesternElectionalQualificationStatus",
        "WesternElectionalProfileParameter",
        "WesternElectionalProfileScanPolicy",
        "WesternElectionalStatusCount",
        "WesternElectionalProfileWindow",
        "WesternElectionalProfileScan",
        "scan_western_electional_profile",
    }
    assert set(western.__all__) == expected
    assert len(western.__all__) == len(set(western.__all__))
    for name in expected:
        assert hasattr(western, name)
        assert getattr(moira, name) is getattr(western, name)
        assert getattr(facade, name) is getattr(western, name)
        assert name in moira.__all__
        assert name in facade.__all__


def test_moira_facade_method_delegates_with_bound_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel_result = object()
    sentinel_reader = object()
    captured: dict[str, object] = {}

    def fake_ramesey(*args: object, **kwargs: object) -> object:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return sentinel_result

    monkeypatch.setattr(facade, "ramesey_moon_condition_at", fake_ramesey)
    engine = moira.Moira()
    engine._reader_obj = sentinel_reader
    result = engine.ramesey_moon_condition_at(
        2451545.0,
        51.5,
        -0.1,
        house_system=HouseSystem.REGIOMONTANUS,
        unavoidable_time_urgency=True,
    )

    assert result is sentinel_result
    assert captured["args"] == (2451545.0, 51.5, -0.1)
    assert captured["kwargs"] == {
        "house_system": HouseSystem.REGIOMONTANUS,
        "unavoidable_time_urgency": True,
        "reader": sentinel_reader,
        "house_policy": None,
        "policy": western.RAMESEY_MOON_CONDITION_V1,
    }


def test_source_fixed_policy_rejects_caller_orb_substitution() -> None:
    changed = tuple(
        (body, 13.0 if body == Body.MOON else orb)
        for body, orb in western.RAMESEY_MOON_CONDITION_V1.planetary_full_orbs
    )
    with pytest.raises(ValueError, match="source-fixed"):
        western.RameseyMoonConditionPolicy(planetary_full_orbs=changed)


@pytest.mark.parametrize(
    "field_name",
    (
        "profile_id",
        "profile_version",
        "degree_policy",
        "aspect_policy",
        "node_policy",
        "latter_degrees_policy",
        "cadency_policy",
        "cancer_beholding_policy",
        "position_product",
        "void_policy",
        "via_combusta_policy",
    ),
)
def test_every_scalar_policy_field_is_closed_against_substitution(field_name: str) -> None:
    with pytest.raises(ValueError):
        replace(western.RAMESEY_MOON_CONDITION_V1, **{field_name: "substituted"})


def test_clear_profile_has_ten_ordered_visible_witnesses() -> None:
    result = _evaluation(_chart())

    assert result.status is western.RameseyMoonConditionStatus.CLEAR
    assert result.triggered_rule_ids == ()
    assert result.not_evaluable_rule_ids == ()
    assert tuple(rule.source_order for rule in result.rules) == tuple(range(1, 11))
    assert all(rule.clauses for rule in result.rules)
    assert all(clause.policy_reference for rule in result.rules for clause in rule.clauses)
    assert result.requested_house_system == HouseSystem.PORPHYRY
    assert result.effective_house_system == HouseSystem.PORPHYRY
    assert result.house_fallback is False
    assert len(result.remedies) == 1
    assert result.remedies[0].applicability is western.RameseyRemedyApplicability.NOT_APPLICABLE
    assert result.remedies[0].triggering_rule_ids == ()


def test_triggered_gate_and_missing_urgency_preserve_indeterminate_remedy() -> None:
    result = _evaluation(_chart(moon_longitude=212.5))
    remedy = result.remedies[0]

    assert result.status is western.RameseyMoonConditionStatus.TRIGGERED
    assert result.triggered_rule_ids
    assert remedy.applicability is western.RameseyRemedyApplicability.INDETERMINATE
    assert remedy.triggering_rule_ids == result.triggered_rule_ids
    assert remedy.unavoidable_time_urgency is None
    assert remedy.erases_triggered_rules is False
    assert remedy.assessment_semantics == "instruction_only_not_fulfillment_assessment"
    assert len(remedy.instructions) == 3
    assert len(remedy.uncomputed_requirements) == 3


@pytest.mark.parametrize(
    ("unavoidable_time_urgency", "expected"),
    (
        (True, western.RameseyRemedyApplicability.APPLICABLE),
        (False, western.RameseyRemedyApplicability.NOT_APPLICABLE),
    ),
)
def test_remedy_context_never_erases_confirmed_impediments(
    unavoidable_time_urgency: bool,
    expected: western.RameseyRemedyApplicability,
) -> None:
    result = _evaluation(
        _chart(moon_longitude=212.5),
        unavoidable_time_urgency=unavoidable_time_urgency,
    )

    assert result.status is western.RameseyMoonConditionStatus.TRIGGERED
    assert "moon_in_third_degree_scorpio" in result.triggered_rule_ids
    assert result.remedies[0].applicability is expected
    assert result.remedies[0].triggering_rule_ids == result.triggered_rule_ids


def test_unknown_gate_keeps_remedy_applicability_indeterminate() -> None:
    result = _evaluation(_chart(), voc=None, unavoidable_time_urgency=True)

    assert result.triggered_rule_ids == ()
    assert result.not_evaluable_rule_ids == ("moon_void_ramesey_sign_bound",)
    assert result.remedies[0].applicability is western.RameseyRemedyApplicability.INDETERMINATE


def test_remedy_context_rejects_non_boolean_substitution() -> None:
    with pytest.raises(TypeError, match="bool or None"):
        western.evaluate_ramesey_moon_condition(
            _chart(),
            void_of_course=False,
            unavoidable_time_urgency=1,  # type: ignore[arg-type]
            position_product=western.RAMESEY_MOON_CONDITION_V1.position_product,
            reader_provenance="synthetic_unit_fixture",
        )


def test_missing_forward_voc_product_is_indeterminate_not_clear() -> None:
    result = _evaluation(_chart(), voc=None)

    assert result.status is western.RameseyMoonConditionStatus.INDETERMINATE
    assert result.not_evaluable_rule_ids == ("moon_void_ramesey_sign_bound",)
    assert _rule(result, 10).state is western.RameseyRuleState.NOT_EVALUABLE


def test_prebuilt_chart_requires_explicit_admitted_position_product() -> None:
    with pytest.raises(ValueError, match="position_product"):
        western.evaluate_ramesey_moon_condition(
            _chart(),
            void_of_course=False,
            position_product="geometric_geocentric_tropical_ecliptic_longitude",
            reader_provenance="synthetic_unit_fixture",
        )


def test_topocentric_planet_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="geocentric"):
        _evaluation(_chart(moon_topocentric=True))


def test_combustion_includes_exactly_twelve_degrees_and_records_phase() -> None:
    applying = _evaluation(_chart(moon_longitude=40.0, sun_longitude=28.0, moon_speed=-1.0, sun_speed=1.0))
    outside = _evaluation(_chart(moon_longitude=40.000001, sun_longitude=28.0))

    assert _rule(applying, 1).state is western.RameseyRuleState.TRIGGERED
    measurements = _rule(applying, 1).clauses[0].measurements
    assert measurements[0].value == pytest.approx(12.0)
    assert measurements[1].value == "applying"
    assert _rule(applying, 1).modifiers
    assert _rule(outside, 1).state is western.RameseyRuleState.CLEAR


@pytest.mark.parametrize(
    ("longitude", "expected"),
    (
        (211.999999, western.RameseyRuleState.CLEAR),
        (212.0, western.RameseyRuleState.TRIGGERED),
        (212.999999, western.RameseyRuleState.TRIGGERED),
        (213.0, western.RameseyRuleState.CLEAR),
    ),
)
def test_third_degree_scorpio_uses_ordinal_half_open_interval(
    longitude: float,
    expected: western.RameseyRuleState,
) -> None:
    assert _rule(_evaluation(_chart(moon_longitude=longitude)), 2).state is expected


def test_sun_opposition_uses_ramesey_combined_moieties() -> None:
    # Moon half-orb 6 + Sun half-orb 7.5 = 13.5 degrees.
    boundary = _evaluation(_chart(moon_longitude=40.0, sun_longitude=233.5))
    outside = _evaluation(_chart(moon_longitude=40.0, sun_longitude=233.501))

    assert _rule(boundary, 3).state is western.RameseyRuleState.TRIGGERED
    aspect_error = _rule(boundary, 3).clauses[0].measurements[1]
    assert aspect_error.value == pytest.approx(13.5)
    assert aspect_error.threshold == pytest.approx(13.5)
    assert _rule(outside, 3).state is western.RameseyRuleState.CLEAR


def test_hard_malefic_aspects_preserve_body_specific_moieties() -> None:
    # Moon-Saturn threshold is 6 + 4.5 = 10.5 degrees around the square.
    boundary = _evaluation(_chart(moon_longitude=40.0, saturn_longitude=140.5))
    outside = _evaluation(_chart(moon_longitude=40.0, saturn_longitude=140.5001))

    assert _rule(boundary, 4).state is western.RameseyRuleState.TRIGGERED
    saturn_square = next(clause for clause in _rule(boundary, 4).clauses if clause.clause_id == "moon_square_saturn")
    assert saturn_square.measurements[1].threshold == pytest.approx(10.5)
    assert saturn_square.state is western.RameseyRuleState.TRIGGERED
    assert _rule(outside, 4).state is western.RameseyRuleState.CLEAR


@pytest.mark.parametrize("node_longitude", (52.0, 232.0))
def test_true_head_and_opposite_tail_include_twelve_degree_boundary(node_longitude: float) -> None:
    result = _evaluation(_chart(moon_longitude=40.0, node_longitude=node_longitude))

    assert _rule(result, 5).state is western.RameseyRuleState.TRIGGERED
    assert any(clause.state is western.RameseyRuleState.TRIGGERED for clause in _rule(result, 5).clauses)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    (
        (25.999999, western.RameseyRuleState.CLEAR),
        (26.0, western.RameseyRuleState.TRIGGERED),
        (149.999999, western.RameseyRuleState.CLEAR),  # Leo: Jupiter is terminal.
        (359.999999, western.RameseyRuleState.TRIGGERED),
    ),
)
def test_terminal_malefic_terms_use_ramesey_table_boundaries(
    longitude: float,
    expected: western.RameseyRuleState,
) -> None:
    assert _rule(_evaluation(_chart(moon_longitude=longitude)), 6).state is expected


@pytest.mark.parametrize(
    ("sign_index", "start"),
    (
        (0, 26.0),
        (1, 24.0),
        (2, 26.0),
        (3, 27.0),
        (5, 24.0),
        (6, 24.0),
        (7, 27.0),
        (8, 25.0),
        (9, 25.0),
        (10, 25.0),
        (11, 25.0),
    ),
)
def test_every_ramesey_terminal_malefic_term_has_half_open_start(
    sign_index: int,
    start: float,
) -> None:
    sign_start = sign_index * 30.0
    before = _evaluation(_chart(moon_longitude=sign_start + start - 1e-9))
    at_start = _evaluation(_chart(moon_longitude=sign_start + start))

    assert _rule(before, 6).state is western.RameseyRuleState.CLEAR
    assert _rule(at_start, 6).state is western.RameseyRuleState.TRIGGERED


@pytest.mark.parametrize(
    ("longitude", "expected"),
    (
        (194.999999, western.RameseyRuleState.CLEAR),
        (195.0, western.RameseyRuleState.TRIGGERED),
        (224.999999, western.RameseyRuleState.TRIGGERED),
        (225.0, western.RameseyRuleState.CLEAR),
    ),
)
def test_via_combusta_is_half_open_195_to_225(
    longitude: float,
    expected: western.RameseyRuleState,
) -> None:
    result = _evaluation(_chart(moon_longitude=longitude))
    via_clause = next(clause for clause in _rule(result, 7).clauses if clause.clause_id == "moon_in_via_combusta")
    assert via_clause.state is expected


def test_cadency_uses_explicit_quadrant_house_placement() -> None:
    result = _evaluation(_chart(moon_longitude=70.0))  # Synthetic cusp figure places this in house 3.

    cadent = next(clause for clause in _rule(result, 7).clauses if clause.clause_id == "moon_cadent")
    assert cadent.state is western.RameseyRuleState.TRIGGERED
    assert cadent.measurements[0].value == 3
    assert cadent.measurements[1].value == "cadent"


def test_non_quadrant_cadency_is_not_silently_inferred() -> None:
    result = _evaluation(_chart(moon_longitude=40.0, houses=_houses(HouseSystem.WHOLE_SIGN)))

    assert _rule(result, 7).state is western.RameseyRuleState.NOT_EVALUABLE
    assert result.status is western.RameseyMoonConditionStatus.INDETERMINATE


def test_via_trigger_is_decisive_even_if_cadency_is_not_evaluable() -> None:
    result = _evaluation(_chart(moon_longitude=200.0, houses=_houses(HouseSystem.WHOLE_SIGN)))

    assert _rule(result, 7).state is western.RameseyRuleState.TRIGGERED


@pytest.mark.parametrize(
    ("longitude", "expected"),
    (
        (40.0, western.RameseyRuleState.CLEAR),       # Taurus sextile Cancer
        (100.0, western.RameseyRuleState.CLEAR),      # Cancer bodily
        (220.0, western.RameseyRuleState.CLEAR),      # Scorpio trine Cancer
        (10.0, western.RameseyRuleState.TRIGGERED),   # Aries square Cancer
        (70.0, western.RameseyRuleState.TRIGGERED),   # Gemini lacks bodily/sextile/trine
        (280.0, western.RameseyRuleState.TRIGGERED),  # Capricorn detriment
    ),
)
def test_cancer_beholding_is_whole_sign_and_clause_visible(
    longitude: float,
    expected: western.RameseyRuleState,
) -> None:
    assert _rule(_evaluation(_chart(moon_longitude=longitude)), 8).state is expected


def test_slow_motion_is_strictly_less_than_ramesey_threshold() -> None:
    threshold = 13.0 + 10.0 / 60.0 + 36.0 / 3600.0
    equal = _evaluation(_chart(moon_speed=threshold))
    below = _evaluation(_chart(moon_speed=math.nextafter(threshold, 0.0)))

    assert _rule(equal, 9).state is western.RameseyRuleState.CLEAR
    assert _rule(below, 9).state is western.RameseyRuleState.TRIGGERED


def test_void_of_course_boolean_remains_a_separate_forward_search_input() -> None:
    clear = _evaluation(_chart(), voc=False)
    void = _evaluation(_chart(), voc=True)

    assert _rule(clear, 10).state is western.RameseyRuleState.CLEAR
    assert _rule(void, 10).state is western.RameseyRuleState.TRIGGERED


@pytest.mark.parametrize("boundary", tuple(float(value) for value in range(0, 360, 30)))
def test_every_zodiac_sign_boundary_is_total_and_half_open(boundary: float) -> None:
    before = math.nextafter(boundary if boundary else 360.0, 0.0) % 360.0
    at_boundary = boundary
    after = math.nextafter(boundary, math.inf)
    expected_index = int(boundary // 30.0) % 12

    before_result = _evaluation(_chart(moon_longitude=before))
    boundary_result = _evaluation(_chart(moon_longitude=at_boundary))
    after_result = _evaluation(_chart(moon_longitude=after))

    def moon_sign(result: western.RameseyMoonConditionEvaluation) -> str:
        measurement = next(
            item
            for item in _rule(result, 2).clauses[0].measurements
            if item.name == "moon_sign"
        )
        assert isinstance(measurement.value, str)
        return measurement.value

    assert moon_sign(before_result) == SIGNS[(expected_index - 1) % 12]
    assert moon_sign(boundary_result) == SIGNS[expected_index]
    assert moon_sign(after_result) == SIGNS[expected_index]
    assert all(len(result.rules) == 10 for result in (before_result, boundary_result, after_result))


@settings(max_examples=120, deadline=None)
@given(
    moon_longitude=st.floats(
        min_value=0.0,
        max_value=math.nextafter(360.0, 0.0),
        allow_nan=False,
        allow_infinity=False,
    ),
    moon_speed=st.floats(
        min_value=-20.0,
        max_value=20.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    void_of_course=st.booleans(),
    unavoidable_time_urgency=st.one_of(st.none(), st.booleans()),
)
def test_full_zodiac_outputs_are_finite_deterministic_and_witness_complete(
    moon_longitude: float,
    moon_speed: float,
    void_of_course: bool,
    unavoidable_time_urgency: bool | None,
) -> None:
    chart = _chart(moon_longitude=moon_longitude, moon_speed=moon_speed)
    first = _evaluation(
        chart,
        voc=void_of_course,
        unavoidable_time_urgency=unavoidable_time_urgency,
    )
    second = _evaluation(
        chart,
        voc=void_of_course,
        unavoidable_time_urgency=unavoidable_time_urgency,
    )

    assert first == second
    assert hash(first) == hash(second)
    assert tuple(rule.source_order for rule in first.rules) == tuple(range(1, 11))
    assert len({rule.rule_id for rule in first.rules}) == 10
    assert all(rule.clauses for rule in first.rules)
    assert all(
        clause.policy_id and clause.policy_reference and clause.explanation
        for rule in first.rules
        for clause in rule.clauses
    )
    assert first.remedies[0].triggering_rule_ids == first.triggered_rule_ids
    for rule in first.rules:
        for clause in rule.clauses:
            for measurement in clause.measurements:
                if isinstance(measurement.value, float):
                    assert math.isfinite(measurement.value)
                if isinstance(measurement.threshold, float):
                    assert math.isfinite(measurement.threshold)


@settings(max_examples=80, deadline=None)
@given(
    longitude_millidegrees=st.integers(min_value=0, max_value=359_999),
    rotations=st.integers(min_value=-8, max_value=8),
)
def test_equivalent_normalized_longitudes_preserve_doctrine_state(
    longitude_millidegrees: int,
    rotations: int,
) -> None:
    longitude = longitude_millidegrees / 1000.0
    baseline = _evaluation(_chart(moon_longitude=longitude))
    rotated = _evaluation(_chart(moon_longitude=longitude + rotations * 360.0))

    assert rotated.status is baseline.status
    assert rotated.triggered_rule_ids == baseline.triggered_rule_ids
    assert rotated.not_evaluable_rule_ids == baseline.not_evaluable_rule_ids
    assert tuple(rule.state for rule in rotated.rules) == tuple(
        rule.state for rule in baseline.rules
    )
    assert rotated.remedies[0].applicability is baseline.remedies[0].applicability


def test_high_level_entry_point_requires_and_preserves_house_system(monkeypatch: pytest.MonkeyPatch) -> None:
    chart = _chart()
    calls: dict[str, object] = {}

    def fake_create_chart(*args: object, **kwargs: object) -> ChartContext:
        calls["create_args"] = args
        calls["create_kwargs"] = kwargs
        return chart

    def fake_voc(*args: object, **kwargs: object) -> bool:
        calls["voc_args"] = args
        calls["voc_kwargs"] = kwargs
        return False

    monkeypatch.setattr(western, "create_chart", fake_create_chart)
    monkeypatch.setattr(western, "is_void_of_course", fake_voc)

    class FakeReader:
        path = "synthetic-de441.bsp"

    result = western.ramesey_moon_condition_at(
        2451545.0,
        51.5,
        -0.1,
        house_system=HouseSystem.PORPHYRY,
        unavoidable_time_urgency=True,
        reader=FakeReader(),  # type: ignore[arg-type]
    )

    assert result.status is western.RameseyMoonConditionStatus.CLEAR
    create_kwargs = calls["create_kwargs"]
    assert isinstance(create_kwargs, dict)
    assert create_kwargs["house_system"] == HouseSystem.PORPHYRY
    assert create_kwargs["bodies"] == [Body.SUN, Body.MOON, Body.MARS, Body.SATURN]
    voc_kwargs = calls["voc_kwargs"]
    assert isinstance(voc_kwargs, dict)
    assert voc_kwargs["modern"] is False
    assert result.reader_provenance == "synthetic-de441.bsp"
    assert result.remedies[0].unavoidable_time_urgency is True

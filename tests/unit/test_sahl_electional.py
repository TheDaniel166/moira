"""Source, boundary, and public-surface tests for Sahl's bounded profile."""

from __future__ import annotations

from dataclasses import replace

import pytest

import moira
import moira.facade as facade
import moira.western_electional as western
from moira.chart import ChartContext
from moira.constants import Body, HouseSystem
from moira.houses import HouseCusps, HousePolicy, classify_house_system
from moira.nodes import NodeData
from moira.planets import PlanetData


def _planet(name: str, longitude: float, speed: float = 1.0) -> PlanetData:
    return PlanetData(
        name=name,
        longitude=longitude % 360.0,
        latitude=0.0,
        distance=1.0,
        speed=speed,
        retrograde=speed < 0.0,
    )


def _houses(system: str = HouseSystem.PORPHYRY) -> HouseCusps:
    return HouseCusps(
        system=system,
        cusps=tuple(float(degree) for degree in range(0, 360, 30)),
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
    mars_longitude: float = 200.0,
    saturn_longitude: float = 280.0,
    node_longitude: float = 80.0,
    houses: HouseCusps | None = None,
    include_houses: bool = True,
    include_mars: bool = True,
    include_saturn: bool = True,
) -> ChartContext:
    planets = {
        Body.MOON: _planet(Body.MOON, moon_longitude, moon_speed),
        Body.SUN: _planet(Body.SUN, sun_longitude, 1.0),
    }
    if include_mars:
        planets[Body.MARS] = _planet(Body.MARS, mars_longitude, 0.5)
    if include_saturn:
        planets[Body.SATURN] = _planet(Body.SATURN, saturn_longitude, 0.1)
    return ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0,
        latitude=0.0,
        longitude=0.0,
        planets=planets,
        nodes={Body.TRUE_NODE: NodeData(Body.TRUE_NODE, node_longitude, -0.05)},
        houses=(houses or _houses()) if include_houses else None,
    )


def _evaluation(
    chart: ChartContext,
    *,
    voc: bool | None = False,
    burnt_path: western.SahlBurntPathVariant = western.SahlBurntPathVariant.DYKES_GLOSSARY_FALL_DEGREES,
    eighth: western.SahlEighthRuleVariant = western.SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART,
) -> western.SahlMoonConditionEvaluation:
    policy = replace(
        western.SAHL_MOON_CONDITION_V1,
        burnt_path_variant=burnt_path,
        eighth_rule_variant=eighth,
    )
    return western.evaluate_sahl_moon_condition(
        chart,
        void_of_course=voc,
        position_product=policy.position_product,
        reader_provenance="synthetic_unit_fixture",
        policy=policy,
    )


def _rule(
    result: western.SahlMoonConditionEvaluation,
    order: int,
) -> western.SahlRuleWitness:
    return result.rules[order - 1]


def test_sahl_surface_is_public_through_root_facade_and_moira_class() -> None:
    names = {
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
    }
    for name in names:
        assert hasattr(western, name)
        assert hasattr(facade, name)
        assert hasattr(moira, name)
    assert hasattr(moira.Moira, "sahl_moon_condition_at")


def test_policy_rejects_hidden_doctrine_substitution() -> None:
    with pytest.raises(ValueError, match="aspect_policy is fixed"):
        replace(western.SAHL_MOON_CONDITION_V1, aspect_policy="borrowed")
    with pytest.raises(TypeError, match="burnt_path_variant"):
        replace(western.SAHL_MOON_CONDITION_V1, burnt_path_variant="15_to_15")


def test_moira_facade_method_delegates_with_bound_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel_result = object()
    sentinel_reader = object()
    captured: dict[str, object] = {}

    def fake_sahl(*args: object, **kwargs: object) -> object:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return sentinel_result

    monkeypatch.setattr(facade, "sahl_moon_condition_at", fake_sahl)
    engine = moira.Moira()
    engine._reader_obj = sentinel_reader
    result = engine.sahl_moon_condition_at(
        2451545.0,
        51.5,
        -0.1,
        house_system=HouseSystem.REGIOMONTANUS,
        burnt_path_variant=western.SahlBurntPathVariant.DYKES_GLOSSARY_FALL_DEGREES,
    )
    assert result is sentinel_result
    assert captured["kwargs"]["reader"] is sentinel_reader  # type: ignore[index]
    assert captured["kwargs"]["policy"] is western.SAHL_MOON_CONDITION_V1  # type: ignore[index]


def test_clear_profile_has_ten_ordered_witnesses_with_explicit_variant() -> None:
    result = _evaluation(_chart())
    assert result.status is western.SahlMoonConditionStatus.CLEAR
    assert result.triggered_rule_ids == ()
    assert result.not_evaluable_rule_ids == ()
    assert tuple(rule.source_order for rule in result.rules) == tuple(range(1, 11))
    assert result.burnt_path_variant is western.SahlBurntPathVariant.DYKES_GLOSSARY_FALL_DEGREES


def test_unresolved_sahl_burnt_path_is_visible_not_silently_defaulted() -> None:
    result = _evaluation(
        _chart(),
        burnt_path=western.SahlBurntPathVariant.SAHL_TEXT_INDETERMINATE,
    )
    rule = _rule(result, 7)
    burnt = next(clause for clause in rule.clauses if clause.clause_id == "moon_in_burnt_path")
    assert burnt.state is western.SahlRuleState.NOT_EVALUABLE
    assert result.status is western.SahlMoonConditionStatus.INDETERMINATE
    assert result.not_evaluable_rule_ids == ("moon_cadent_or_burnt_path",)


def test_confirmed_impediment_dominates_an_unresolved_other_clause() -> None:
    result = _evaluation(
        _chart(moon_longitude=70.0),
        burnt_path=western.SahlBurntPathVariant.SAHL_TEXT_INDETERMINATE,
    )
    assert _rule(result, 7).state is western.SahlRuleState.TRIGGERED
    assert result.status is western.SahlMoonConditionStatus.TRIGGERED


def test_burning_includes_twelve_degrees_and_records_easier_after_modifier() -> None:
    result = _evaluation(_chart(moon_longitude=40.0, sun_longitude=28.0))
    rule = _rule(result, 1)
    assert rule.state is western.SahlRuleState.TRIGGERED
    assert rule.modifiers
    assert rule.clauses[0].measurements[0].threshold == 12.0


def test_sun_opposition_and_malefic_rays_are_whole_sign() -> None:
    sun_opposition = _evaluation(_chart(moon_longitude=5.0, sun_longitude=195.0))
    assert _rule(sun_opposition, 3).state is western.SahlRuleState.TRIGGERED

    mars_square = _evaluation(_chart(moon_longitude=5.0, mars_longitude=119.0))
    square = next(
        clause for clause in _rule(mars_square, 4).clauses
        if clause.clause_id == "moon_whole_sign_square_mars"
    )
    assert square.state is western.SahlRuleState.TRIGGERED


def test_malefic_body_join_uses_body_specific_arabic_moieties() -> None:
    mars_inside = _evaluation(_chart(moon_longitude=0.0, mars_longitude=10.0))
    mars_outside = _evaluation(_chart(moon_longitude=0.0, mars_longitude=10.000001))
    inside_clause = next(
        clause for clause in _rule(mars_inside, 4).clauses
        if clause.clause_id == "moon_body_join_mars"
    )
    outside_clause = next(
        clause for clause in _rule(mars_outside, 4).clauses
        if clause.clause_id == "moon_body_join_mars"
    )
    assert inside_clause.state is western.SahlRuleState.TRIGGERED
    assert outside_clause.state is western.SahlRuleState.CLEAR


def test_node_boundary_and_egyptian_malefic_bound_are_explicit() -> None:
    node = _evaluation(_chart(moon_longitude=68.0, node_longitude=80.0))
    assert _rule(node, 5).state is western.SahlRuleState.TRIGGERED

    nonterminal_mars = _evaluation(_chart(moon_longitude=20.0))
    assert _rule(nonterminal_mars, 6).state is western.SahlRuleState.CLEAR

    bound = _evaluation(_chart(moon_longitude=25.0))
    rule = _rule(bound, 6)
    assert rule.state is western.SahlRuleState.TRIGGERED
    assert rule.clauses[0].measurements[2].value == Body.SATURN


@pytest.mark.parametrize(
    ("variant", "inside", "outside"),
    [
        (western.SahlBurntPathVariant.DYKES_GLOSSARY_FALL_DEGREES, 199.0, 213.0),
        (western.SahlBurntPathVariant.LATER_FIFTEEN_DEGREES, 195.0, 225.0),
    ],
)
def test_named_burnt_path_intervals_are_half_open(
    variant: western.SahlBurntPathVariant,
    inside: float,
    outside: float,
) -> None:
    assert _rule(_evaluation(_chart(moon_longitude=inside), burnt_path=variant), 7).state is western.SahlRuleState.TRIGGERED
    burnt = next(
        clause for clause in _rule(_evaluation(_chart(moon_longitude=outside), burnt_path=variant), 7).clauses
        if clause.clause_id == "moon_in_burnt_path"
    )
    assert burnt.state is western.SahlRuleState.CLEAR
    assert any(
        item.name == "interval_start_inclusive" and item.value is True
        for item in burnt.measurements
    )


@pytest.mark.parametrize("longitude", [0.0, 360.0, -360.0])
def test_named_burnt_path_intervals_do_not_wrap_across_aries(longitude: float) -> None:
    result = _evaluation(
        _chart(moon_longitude=longitude),
        burnt_path=western.SahlBurntPathVariant.DYKES_GLOSSARY_FALL_DEGREES,
    )
    burnt = next(
        clause
        for clause in _rule(result, 7).clauses
        if clause.clause_id == "moon_in_burnt_path"
    )
    assert burnt.state is western.SahlRuleState.CLEAR


def test_arabic_eighth_rule_uses_moons_twelfth_part_sign() -> None:
    result = _evaluation(_chart(moon_longitude=34.0, mars_longitude=65.0))
    first = _rule(result, 8).clauses[0]
    assert first.clause_id == "moon_twelfth_part_sign_contains_malefic"
    assert first.state is western.SahlRuleState.TRIGGERED
    assert first.measurements[2].value == "Gemini"


def test_latin_eighth_rule_remains_selectable_and_labeled() -> None:
    result = _evaluation(
        _chart(moon_longitude=65.0, mars_longitude=73.0),
        eighth=western.SahlEighthRuleVariant.LATIN_TWELFTH_SIGN,
    )
    first = _rule(result, 8).clauses[0]
    assert first.clause_id == "moon_in_latin_twelfth_sign_with_malefic"
    assert first.policy_id == "latin_twelfth_sign"
    assert first.state is western.SahlRuleState.TRIGGERED


def test_slow_motion_is_strictly_below_twelve_and_voc_is_separate() -> None:
    equal = _evaluation(_chart(moon_speed=12.0), voc=False)
    below = _evaluation(_chart(moon_speed=11.999999), voc=True)
    assert _rule(equal, 9).state is western.SahlRuleState.CLEAR
    assert _rule(below, 9).state is western.SahlRuleState.TRIGGERED
    assert _rule(equal, 10).state is western.SahlRuleState.CLEAR
    assert _rule(below, 10).state is western.SahlRuleState.TRIGGERED


def test_missing_forward_voc_and_nonquadrant_cadency_remain_indeterminate() -> None:
    missing_voc = _evaluation(_chart(), voc=None)
    assert _rule(missing_voc, 10).state is western.SahlRuleState.NOT_EVALUABLE

    nonquadrant = _evaluation(_chart(houses=_houses(HouseSystem.WHOLE_SIGN)))
    cadent = next(
        clause for clause in _rule(nonquadrant, 7).clauses
        if clause.clause_id == "moon_cadent"
    )
    assert cadent.state is western.SahlRuleState.NOT_EVALUABLE


def test_high_level_entrypoint_preserves_variants_reader_and_voc_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chart = _chart()
    calls: dict[str, object] = {}

    def fake_create_chart(*args: object, **kwargs: object) -> ChartContext:
        calls["chart_kwargs"] = kwargs
        return chart

    def fake_voc(*args: object, **kwargs: object) -> bool:
        calls["voc_kwargs"] = kwargs
        return False

    monkeypatch.setattr(western, "create_chart", fake_create_chart)
    monkeypatch.setattr(western, "is_void_of_course", fake_voc)

    class FakeReader:
        path = "synthetic-de441.bsp"

    result = western.sahl_moon_condition_at(
        2451545.0,
        51.5,
        -0.1,
        house_system=HouseSystem.PORPHYRY,
        burnt_path_variant=western.SahlBurntPathVariant.LATER_FIFTEEN_DEGREES,
        eighth_rule_variant=western.SahlEighthRuleVariant.LATIN_TWELFTH_SIGN,
        reader=FakeReader(),  # type: ignore[arg-type]
    )
    assert result.reader_provenance == "synthetic-de441.bsp"
    assert result.burnt_path_variant is western.SahlBurntPathVariant.LATER_FIFTEEN_DEGREES
    assert result.eighth_rule_variant is western.SahlEighthRuleVariant.LATIN_TWELFTH_SIGN
    assert calls["chart_kwargs"]["house_system"] == HouseSystem.PORPHYRY  # type: ignore[index]
    assert calls["voc_kwargs"]["modern"] is False  # type: ignore[index]

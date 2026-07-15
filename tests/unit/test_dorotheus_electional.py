"""Source, boundary, and public-surface tests for Dorotheus V.6."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade
import moira.western_electional as western
import moira._western_electional_dorotheus as dorotheus
from moira.chart import ChartContext
from moira.constants import Body, HouseSystem
from moira.houses import HouseCusps, HousePolicy, classify_house_system
from moira.planets import PlanetData


def _planet(
    name: str,
    longitude: float,
    speed: float = 1.0,
    *,
    latitude: float = 0.0,
) -> PlanetData:
    return PlanetData(
        name=name,
        longitude=longitude % 360.0,
        latitude=latitude,
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
    moon_latitude: float = 1.0,
    sun_longitude: float = 100.0,
    mars_longitude: float = 65.0,
    saturn_longitude: float = 185.0,
    houses: HouseCusps | None = None,
    include_houses: bool = True,
    include_mars: bool = True,
    include_saturn: bool = True,
) -> ChartContext:
    planets = {
        Body.MOON: _planet(
            Body.MOON,
            moon_longitude,
            moon_speed,
            latitude=moon_latitude,
        ),
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
        nodes={},
        houses=(houses or _houses()) if include_houses else None,
    )


def _lunar_direction(
    chart: ChartContext,
    *,
    rate: float = -0.2,
) -> western.LunarEclipticDirectionWitness:
    moon = chart.planets[Body.MOON]
    policy = western.LUNAR_ECLIPTIC_DIRECTION_V1
    previous = western.LunarNodeCrossingWitness(
        jd_ut=chart.jd_ut - 1.0,
        direction=western.LunarNodeCrossingDirection.ASCENDING,
        longitude_deg=(moon.longitude - 13.0) % 360.0,
        latitude_residual_deg=0.0,
        latitude_rate_deg_per_day=0.4,
        hours_from_query=-24.0,
    )
    following = western.LunarNodeCrossingWitness(
        jd_ut=chart.jd_ut + 1.0,
        direction=western.LunarNodeCrossingDirection.DESCENDING,
        longitude_deg=(moon.longitude + 13.0) % 360.0,
        latitude_residual_deg=0.0,
        latitude_rate_deg_per_day=-0.4,
        hours_from_query=24.0,
    )
    return western.LunarEclipticDirectionWitness(
        jd_ut=chart.jd_ut,
        latitude_deg=moon.latitude,
        latitude_rate_deg_per_day=rate,
        hemisphere=(
            western.LunarEclipticHemisphere.NORTH
            if moon.latitude > 0.0
            else western.LunarEclipticHemisphere.SOUTH
        ),
        motion=(
            western.LunarLatitudeMotion.NORTHWARD
            if rate > 0.0
            else western.LunarLatitudeMotion.SOUTHWARD
        ),
        previous_crossing=previous,
        next_crossing=following,
        nearest_crossing=previous,
        nearest_crossing_relation=western.LunarNodeCrossingRelation.PREVIOUS,
        policy=policy,
    )


def _evaluation(
    chart: ChartContext,
    *,
    eclipsed: bool | None = False,
    urgency: bool | None = None,
) -> western.DorotheusMoonConditionEvaluation:
    return western.evaluate_dorotheus_moon_condition(
        chart,
        moon_eclipsed=eclipsed,
        lunar_direction=_lunar_direction(chart),
        unavoidable_time_urgency=urgency,
        position_product=western.DOROTHEUS_MOON_CONDITION_V1.position_product,
        reader_provenance="synthetic_unit_fixture",
    )


def _rule(
    result: western.DorotheusMoonConditionEvaluation,
    order: int,
) -> western.DorotheusRuleWitness:
    return result.rules[order - 1]


def test_dorotheus_surface_is_public_through_root_facade_and_moira_class() -> None:
    names = {
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
    }
    for name in names:
        assert hasattr(western, name)
        assert hasattr(facade, name)
        assert hasattr(moira, name)
    assert hasattr(moira.Moira, "dorotheus_moon_condition_at")


def test_policy_rejects_substituted_later_lineage_semantics() -> None:
    with pytest.raises(ValueError, match="under_rays_policy is fixed"):
        replace(
            western.DOROTHEUS_MOON_CONDITION_V1,
            under_rays_policy="later_combustion_orb",
        )
    with pytest.raises(ValueError, match="burned_path_policy is fixed"):
        replace(
            western.DOROTHEUS_MOON_CONDITION_V1,
            burned_path_policy="fifteen_libra_to_fifteen_scorpio",
        )


def test_evaluation_preserves_eleven_source_ordered_rules_and_two_unknowns() -> None:
    result = _evaluation(_chart())
    assert tuple(rule.source_order for rule in result.rules) == tuple(range(1, 12))
    assert result.status is western.DorotheusMoonConditionStatus.INDETERMINATE
    assert result.triggered_rule_ids == ()
    assert result.not_evaluable_rule_ids == (
        "moon_on_ecliptic_descending_south",
        "moon_disengaging_from_sun",
    )


def test_eclipse_gate_and_natal_intensifier_are_kept_distinct() -> None:
    result = _evaluation(_chart(), eclipsed=True)
    rule = _rule(result, 1)
    assert rule.state is western.DorotheusRuleState.TRIGGERED
    assert "natal Moon" in rule.modifiers[0]
    assert result.status is western.DorotheusMoonConditionStatus.TRIGGERED


def test_under_rays_uses_edition_glossary_fifteen_degree_boundary() -> None:
    boundary = _evaluation(_chart(moon_longitude=40.0, sun_longitude=25.0))
    outside = _evaluation(_chart(moon_longitude=40.0, sun_longitude=24.999999))
    assert _rule(boundary, 2).state is western.DorotheusRuleState.TRIGGERED
    assert _rule(outside, 2).state is western.DorotheusRuleState.CLEAR
    assert "concealed work" in _rule(boundary, 2).modifiers[0]


def test_twelfth_part_uses_malefic_domicile_not_malefic_occupancy() -> None:
    result = _evaluation(_chart(moon_longitude=17.5))
    rule = _rule(result, 3)
    assert rule.state is western.DorotheusRuleState.TRIGGERED
    assert rule.clauses[0].measurements[2].value == "Scorpio"


def test_opposition_and_infortune_looking_are_whole_sign_configurations() -> None:
    opposition = _evaluation(_chart(moon_longitude=5.0, sun_longitude=195.0))
    assert _rule(opposition, 5).state is western.DorotheusRuleState.TRIGGERED

    trine = _evaluation(_chart(moon_longitude=5.0, mars_longitude=125.0))
    assert _rule(trine, 6).state is western.DorotheusRuleState.TRIGGERED

    aversion = _evaluation(
        _chart(moon_longitude=5.0, mars_longitude=35.0, saturn_longitude=155.0)
    )
    assert _rule(aversion, 6).state is western.DorotheusRuleState.CLEAR


def test_unresolved_crossing_and_disengagement_preserve_measured_evidence() -> None:
    result = _evaluation(_chart(moon_latitude=-0.01))
    southern = _rule(result, 4).clauses[0]
    disengaging = _rule(result, 7).clauses[0]
    assert southern.state is western.DorotheusRuleState.NOT_EVALUABLE
    assert southern.measurements[0].value == -0.01
    assert disengaging.state is western.DorotheusRuleState.NOT_EVALUABLE
    assert any(m.name == "longitude_phase" for m in disengaging.measurements)


def test_slow_motion_is_strictly_below_twelve_without_acceleration_proxy() -> None:
    equal = _evaluation(_chart(moon_speed=12.0))
    below = _evaluation(_chart(moon_speed=11.999999))
    assert _rule(equal, 8).state is western.DorotheusRuleState.CLEAR
    assert _rule(below, 8).state is western.DorotheusRuleState.TRIGGERED


@pytest.mark.parametrize(
    ("longitude", "state"),
    [
        (179.999999, western.DorotheusRuleState.CLEAR),
        (180.0, western.DorotheusRuleState.TRIGGERED),
        (239.999999, western.DorotheusRuleState.TRIGGERED),
        (240.0, western.DorotheusRuleState.CLEAR),
    ],
)
def test_burned_path_is_exactly_whole_libra_and_scorpio(
    longitude: float,
    state: western.DorotheusRuleState,
) -> None:
    assert _rule(_evaluation(_chart(moon_longitude=longitude)), 9).state is state


def test_terminal_bound_uses_dorotheus_egyptian_table() -> None:
    terminal = _evaluation(_chart(moon_longitude=25.0))
    nonterminal = _evaluation(_chart(moon_longitude=20.0))
    assert _rule(terminal, 10).state is western.DorotheusRuleState.TRIGGERED
    assert _rule(terminal, 10).clauses[0].measurements[2].value == Body.SATURN
    assert _rule(nonterminal, 10).state is western.DorotheusRuleState.CLEAR


def test_final_clause_is_ninth_house_not_generic_cadency() -> None:
    ninth = _evaluation(_chart(moon_longitude=250.0))
    twelfth = _evaluation(_chart(moon_longitude=340.0))
    assert _rule(ninth, 11).state is western.DorotheusRuleState.TRIGGERED
    assert _rule(twelfth, 11).state is western.DorotheusRuleState.CLEAR

    nonquadrant = _evaluation(_chart(houses=_houses(HouseSystem.WHOLE_SIGN)))
    assert _rule(nonquadrant, 11).state is western.DorotheusRuleState.NOT_EVALUABLE


def test_remedy_applicability_requires_trigger_and_unavoidable_time() -> None:
    triggered = _evaluation(_chart(moon_speed=11.0), urgency=True)
    assert triggered.remedies[0].applicability is western.DorotheusRemedyApplicability.APPLICABLE
    assert triggered.remedies[0].erases_triggered_rules is False

    unresolved = _evaluation(_chart(), urgency=True)
    assert unresolved.remedies[0].applicability is western.DorotheusRemedyApplicability.INDETERMINATE

    deferrable = _evaluation(_chart(moon_speed=11.0), urgency=False)
    assert deferrable.remedies[0].applicability is western.DorotheusRemedyApplicability.NOT_APPLICABLE


def test_high_level_entrypoint_uses_existing_eclipse_geometry_and_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    def fake_create_chart(*args: object, **kwargs: object) -> ChartContext:
        calls["chart_kwargs"] = kwargs
        return _chart()

    class FakeCalculator:
        def __init__(self, *, reader: object) -> None:
            calls["eclipse_reader"] = reader

        def calculate_lunar_event_jd(self, jd_ut: float, *, kind: str) -> object:
            calls["eclipse_call"] = (jd_ut, kind)
            return SimpleNamespace(
                is_lunar_eclipse=False,
                eclipse_type=SimpleNamespace(magnitude_penumbra=0.25),
            )

    class FakeReader:
        path = "synthetic-de441.bsp"

    reader = FakeReader()
    monkeypatch.setattr(dorotheus, "create_chart", fake_create_chart)
    monkeypatch.setattr(dorotheus, "EclipseCalculator", FakeCalculator)
    monkeypatch.setattr(
        dorotheus,
        "lunar_ecliptic_direction_at",
        lambda *_args, **_kwargs: _lunar_direction(_chart()),
    )
    result = western.dorotheus_moon_condition_at(
        2451545.0,
        51.5,
        -0.1,
        house_system=HouseSystem.REGIOMONTANUS,
        reader=reader,  # type: ignore[arg-type]
    )
    assert _rule(result, 1).state is western.DorotheusRuleState.TRIGGERED
    assert calls["eclipse_reader"] is reader
    assert calls["eclipse_call"] == (2451545.0, "penumbral")
    assert calls["chart_kwargs"]["house_system"] == HouseSystem.REGIOMONTANUS  # type: ignore[index]


def test_moira_method_delegates_with_bound_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel_result = object()
    sentinel_reader = object()
    captured: dict[str, object] = {}

    def fake_dorotheus(*args: object, **kwargs: object) -> object:
        captured["kwargs"] = kwargs
        return sentinel_result

    monkeypatch.setattr(facade, "dorotheus_moon_condition_at", fake_dorotheus)
    engine = moira.Moira()
    engine._reader_obj = sentinel_reader
    result = engine.dorotheus_moon_condition_at(
        2451545.0,
        51.5,
        -0.1,
        house_system=HouseSystem.REGIOMONTANUS,
    )
    assert result is sentinel_result
    assert captured["kwargs"]["reader"] is sentinel_reader  # type: ignore[index]
    assert captured["kwargs"]["policy"] is western.DOROTHEUS_MOON_CONDITION_V1  # type: ignore[index]

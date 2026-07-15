"""Source-layer and public-surface tests for Dorotheus V.7 construction."""

from __future__ import annotations

from dataclasses import replace

import pytest

import moira
import moira.facade as facade
import moira.western_electional as western
from moira.chart import ChartContext
from moira.constants import Body, HouseSystem
from moira.houses import HouseCusps, HousePolicy, classify_house_system
from moira.planets import PlanetData


def _planet(name: str, longitude: float, *, latitude: float = 0.0) -> PlanetData:
    return PlanetData(name, longitude % 360.0, latitude, 1.0, 1.0, False)


def _houses(
    *,
    asc: float = 0.0,
    system: str = HouseSystem.PORPHYRY,
) -> HouseCusps:
    return HouseCusps(
        system=system,
        cusps=tuple((asc + degree) % 360.0 for degree in range(0, 360, 30)),
        asc=asc,
        mc=(asc + 270.0) % 360.0,
        armc=(asc + 270.0) % 360.0,
        effective_system=system,
        classification=classify_house_system(system),
        policy=HousePolicy.default(),
    )


def _chart(
    *,
    latitude: float = 40.0,
    asc: float = 0.0,
    system: str = HouseSystem.PORPHYRY,
    moon: float = 10.0,
    sun: float = 280.0,
    mercury: float = 65.0,
    venus: float = 35.0,
    mars: float = 185.0,
    jupiter: float = 95.0,
    saturn: float = 275.0,
) -> ChartContext:
    return ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0,
        latitude=latitude,
        longitude=0.0,
        planets={
            Body.SUN: _planet(Body.SUN, sun),
            Body.MOON: _planet(Body.MOON, moon, latitude=0.05),
            Body.MERCURY: _planet(Body.MERCURY, mercury),
            Body.VENUS: _planet(Body.VENUS, venus),
            Body.MARS: _planet(Body.MARS, mars),
            Body.JUPITER: _planet(Body.JUPITER, jupiter),
            Body.SATURN: _planet(Body.SATURN, saturn),
        },
        nodes={},
        houses=_houses(asc=asc, system=system),
    )


def _evaluate(chart: ChartContext) -> western.DorotheusConstructionEvaluation:
    moon_condition = western.evaluate_dorotheus_moon_condition(
        chart,
        moon_eclipsed=False,
        unavoidable_time_urgency=None,
        position_product=western.DOROTHEUS_MOON_CONDITION_V1.position_product,
        reader_provenance="synthetic_unit_fixture",
    )
    context = western.evaluate_dorotheus_rooted_context(
        chart,
        matter=western.DorotheusMatter.LAND_AND_MANAGEMENT,
        election_class=western.WesternElectionClass.EPHEMERAL,
        next_connection=None,
        reader_provenance="synthetic_unit_fixture",
    )
    return western.evaluate_dorotheus_construction(
        chart,
        moon_condition=moon_condition,
        rooted_context=context,
        moon_latitude_rate_degrees_per_day=0.2,
        reader_provenance="synthetic_unit_fixture",
    )


def test_construction_surface_is_public_through_root_facade_and_moira() -> None:
    names = {
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
    }
    assert names <= set(western.__all__)
    assert names <= set(moira.__all__)
    assert names <= set(facade.__all__)
    assert hasattr(moira.Moira, "dorotheus_construction_at")


def test_v2_ascensional_class_uses_computed_arc_at_latitude() -> None:
    crooked = _evaluate(_chart(asc=0.0)).sign_nature
    straight = _evaluate(_chart(asc=90.0)).sign_nature
    assert crooked.ascendant_sign == "Aries"
    assert crooked.ascensional_arc_degrees < 30.0
    assert crooked.ascensional_class is western.DorotheusAscensionalClass.CROOKED
    assert straight.ascendant_sign == "Cancer"
    assert straight.ascensional_arc_degrees > 30.0
    assert straight.ascensional_class is western.DorotheusAscensionalClass.STRAIGHT


def test_v3_v4_and_v5_sign_nature_remain_named_evidence() -> None:
    aries = _evaluate(_chart(asc=0.0)).sign_nature
    gemini = _evaluate(_chart(asc=60.0)).sign_nature
    assert aries.convertible is True
    assert "breaks_off" in aries.convertible_effect
    assert gemini.twin is True
    assert "second_matter" in gemini.twin_effect
    assert aries.chart_sect in {"diurnal", "nocturnal"}
    assert isinstance(aries.sect_fit, bool)


def test_v7_preserves_all_six_clauses_and_source_order() -> None:
    result = _evaluate(_chart())
    assert [clause.source_order for clause in result.construction_clauses] == list(range(1, 7))
    assert [clause.clause_id for clause in result.construction_clauses] == [
        "moon_increasing_in_calculation",
        "moon_increasing_in_glow",
        "moon_on_ecliptic_rising_north",
        "benefic_configured_from_strong_place",
        "saturn_configured_from_strong_place",
        "mars_configured_from_strong_place",
    ]
    assert result.source_complete is True
    assert result.complete_matter_profile is True
    assert result.complete_electional_judgement is False
    assert result.scoring == "not_provided"


def test_calculation_and_ecliptic_crossing_are_not_replaced_by_proxies() -> None:
    result = _evaluate(_chart())
    calculation, _, crossing = result.construction_clauses[:3]
    assert calculation.state is western.DorotheusConstructionClauseState.NOT_EVALUABLE
    assert crossing.state is western.DorotheusConstructionClauseState.NOT_EVALUABLE
    assert "mean lunar longitude" in str(calculation.measurements[1].value)
    assert crossing.measurements[1].name == "moon_latitude_rate"
    assert result.numerically_complete is False


def test_angular_whole_sign_benefic_and_malefic_conditions_are_visible() -> None:
    result = _evaluate(_chart())
    benefic, saturn, mars = result.construction_clauses[3:]
    assert benefic.state is western.DorotheusConstructionClauseState.SATISFIED
    assert benefic.measurements[0].value == Body.JUPITER
    assert saturn.state is western.DorotheusConstructionClauseState.TRIGGERED
    assert mars.state is western.DorotheusConstructionClauseState.TRIGGERED
    assert result.triggered_clause_ids == (
        "saturn_configured_from_strong_place",
        "mars_configured_from_strong_place",
    )
    assert result.status is western.DorotheusConstructionStatus.TRIGGERED


def test_nonquadrant_strong_place_clauses_are_not_evaluable() -> None:
    result = _evaluate(_chart(system=HouseSystem.WHOLE_SIGN))
    assert all(
        clause.state is western.DorotheusConstructionClauseState.NOT_EVALUABLE
        for clause in result.construction_clauses[3:]
    )


def test_policy_is_closed() -> None:
    with pytest.raises(ValueError, match="straight_threshold_degrees"):
        replace(western.DOROTHEUS_CONSTRUCTION_V1, straight_threshold_degrees=29.0)

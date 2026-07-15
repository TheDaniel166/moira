"""Source-order and policy tests for Sahl §§43-55 matter profiles."""

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


def _planet(name: str, longitude: float, speed: float = 1.0, latitude: float = 0.0) -> PlanetData:
    return PlanetData(name, longitude % 360.0, latitude, 1.0, speed, speed < 0.0)


def _houses() -> HouseCusps:
    return HouseCusps(
        system=HouseSystem.PORPHYRY,
        cusps=tuple(float(value) for value in range(0, 360, 30)),
        asc=0.0,
        mc=270.0,
        armc=270.0,
        effective_system=HouseSystem.PORPHYRY,
        classification=classify_house_system(HouseSystem.PORPHYRY),
        policy=HousePolicy.default(),
    )


def _chart(**overrides: float) -> ChartContext:
    longitudes = {
        Body.SUN: 100.0,
        Body.MOON: 40.0,
        Body.MERCURY: 120.0,
        Body.VENUS: 160.0,
        Body.MARS: 220.0,
        Body.JUPITER: 310.0,
        Body.SATURN: 280.0,
    }
    longitudes.update(overrides)
    speeds = {
        Body.SUN: 1.0,
        Body.MOON: 13.2,
        Body.MERCURY: 1.1,
        Body.VENUS: 1.0,
        Body.MARS: 0.5,
        Body.JUPITER: 0.08,
        Body.SATURN: 0.03,
    }
    return ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0,
        latitude=0.0,
        longitude=0.0,
        planets={name: _planet(name, value, speeds[name]) for name, value in longitudes.items()},
        nodes={Body.TRUE_NODE: NodeData(Body.TRUE_NODE, 80.0, -0.05)},
        houses=_houses(),
    )


def _moon_condition(chart: ChartContext) -> western.SahlMoonConditionEvaluation:
    policy = replace(
        western.SAHL_MOON_CONDITION_V1,
        burnt_path_variant=western.SahlBurntPathVariant.DYKES_GLOSSARY_FALL_DEGREES,
    )
    return western.evaluate_sahl_moon_condition(
        chart,
        void_of_course=False,
        position_product=policy.position_product,
        reader_provenance="synthetic_sahl_matter_fixture",
        policy=policy,
    )


def _evaluate(profile_id: western.SahlMatterProfileId, chart: ChartContext | None = None):
    chart = _chart() if chart is None else chart
    return western.evaluate_sahl_matter_profile(
        chart,
        profile_id=profile_id,
        moon_condition=_moon_condition(chart),
        reader_provenance="synthetic_sahl_matter_fixture",
    )


def _clause(result, clause_id: str):
    return next(item for item in result.clauses if item.clause_id == clause_id)


def test_sahl_matter_surface_is_public_at_every_library_layer() -> None:
    names = {
        "SahlMatterProfileId",
        "SahlMatterClauseRole",
        "SahlMatterClauseState",
        "SahlMatterProfileStatus",
        "SahlMatterMeasurement",
        "SahlMatterClauseWitness",
        "SahlMatterProfilePolicy",
        "SahlMatterProfileEvaluation",
        "SAHL_BUILDING_V1",
        "SAHL_DEMOLITION_V1",
        "SAHL_LAND_V1",
        "SAHL_WELLS_AND_RIVERS_V1",
        "SAHL_PLANTING_V1",
        "SAHL_SOWING_V1",
        "evaluate_sahl_matter_profile",
        "sahl_matter_profile_at",
    }
    for name in names:
        assert hasattr(western, name)
        assert hasattr(facade, name)
        assert hasattr(moira, name)
    assert hasattr(moira.Moira, "sahl_matter_profile_at")


@pytest.mark.parametrize("profile_id", tuple(western.SahlMatterProfileId))
def test_every_profile_preserves_complete_source_order_and_explicit_indeterminacy(profile_id) -> None:
    result = _evaluate(profile_id)
    assert result.profile_id is profile_id
    assert tuple(item.source_order for item in result.clauses) == tuple(range(1, len(result.clauses) + 1))
    assert result.source_complete is True
    assert result.complete_matter_profile is True
    assert result.complete_electional_judgement is False
    assert result.scoring == "not_provided"
    assert result.not_evaluable_clause_ids
    assert result.numerically_complete is False
    assert all(item.source_reference.startswith("Sahl bin Bishr") for item in result.clauses)


def test_profile_families_are_not_collapsed_into_one_clause_set() -> None:
    clause_sets = {
        profile_id: tuple(item.clause_id for item in _evaluate(profile_id).clauses)
        for profile_id in western.SahlMatterProfileId
    }
    assert len(set(clause_sets.values())) == len(western.SahlMatterProfileId)
    assert clause_sets[western.SahlMatterProfileId.BUILDING][0] == "adapt_moon_and_lord"
    assert clause_sets[western.SahlMatterProfileId.SOWING][0] == "ascendant_common"


def test_building_explicit_saturn_danger_triggers_without_closing_apogee_ambiguity() -> None:
    result = _evaluate(
        western.SahlMatterProfileId.BUILDING,
        _chart(**{Body.MOON: 280.0, Body.SATURN: 281.0}),
    )
    danger = _clause(result, "saturn_tail_or_angular_saturn_danger")
    apogee = _clause(result, "mars_aspecting_with_ascending_circle")
    assert danger.state is western.SahlMatterClauseState.TRIGGERED
    assert apogee.state in (
        western.SahlMatterClauseState.CLEAR,
        western.SahlMatterClauseState.NOT_EVALUABLE,
    )
    assert result.status is western.SahlMatterProfileStatus.TRIGGERED


def test_wells_malefic_in_tenth_whole_sign_place_triggers_named_gate() -> None:
    result = _evaluate(
        western.SahlMatterProfileId.WELLS_AND_RIVERS,
        _chart(**{Body.MARS: 275.0}),
    )
    gate = _clause(result, "malefic_in_midheaven")
    assert gate.state is western.SahlMatterClauseState.TRIGGERED
    assert Body.MARS in str(gate.measurements[0].value).split(",")


def test_sowing_under_rays_compound_short_circuits_only_when_explicit_clause_is_false() -> None:
    clear = _evaluate(western.SahlMatterProfileId.SOWING, _chart(**{Body.MOON: 40.0, Body.SUN: 100.0}))
    unknown = _evaluate(western.SahlMatterProfileId.SOWING, _chart(**{Body.MOON: 105.0, Body.SUN: 100.0}))
    assert _clause(clear, "moon_under_rays_and_defective_in_number").state is western.SahlMatterClauseState.CLEAR
    assert _clause(unknown, "moon_under_rays_and_defective_in_number").state is western.SahlMatterClauseState.NOT_EVALUABLE


def test_policy_identity_and_fixed_source_semantics_are_enforced() -> None:
    with pytest.raises(ValueError, match="number_policy is fixed"):
        replace(western.SAHL_SOWING_V1, number_policy="moon_speed_above_average")
    with pytest.raises(ValueError, match="policy identity"):
        western.evaluate_sahl_matter_profile(
            _chart(),
            profile_id=western.SahlMatterProfileId.LAND,
            moon_condition=_moon_condition(_chart()),
            reader_provenance="fixture",
            policy=western.SAHL_BUILDING_V1,
        )

"""Source-order and policy tests for admitted Sahl matter profiles."""

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
        "SAHL_LENDING_V1",
        "SAHL_INVESTMENT_V1",
        "SAHL_PURCHASE_V1",
        "SAHL_SALE_V1",
        "SAHL_BUILDING_V1",
        "SAHL_DEMOLITION_V1",
        "SAHL_LAND_V1",
        "SAHL_WELLS_AND_RIVERS_V1",
        "SAHL_PLANTING_V1",
        "SAHL_SOWING_V1",
        "SAHL_BUSINESS_PARTNERSHIP_V1",
        "evaluate_sahl_matter_profile",
        "sahl_matter_profile_at",
    }
    for name in names:
        assert hasattr(western, name)
        assert hasattr(facade, name)
        assert hasattr(moira, name)
    assert hasattr(moira.Moira, "sahl_matter_profile_at")


@pytest.mark.required_enumeration
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


def test_business_partnership_preserves_distinct_sahl_stakes_and_open_reception() -> None:
    result = _evaluate(
        western.SahlMatterProfileId.BUSINESS_PARTNERSHIP,
        _chart(**{Body.MOON: 180.0}),
    )
    assert result.matter == "business_partnership"
    assert [item.source_order for item in result.clauses] == [1, 2, 3, 4, 5]
    assert _clause(result, "reception_and_aspect_relationship").state is western.SahlMatterClauseState.NOT_EVALUABLE
    assert _clause(result, "partnership_stake_roles").state is western.SahlMatterClauseState.OBSERVED


def test_lending_preserves_sections_29_to_31_and_first_degree_gate() -> None:
    result = _evaluate(
        western.SahlMatterProfileId.LENDING,
        _chart(**{Body.MOON: 120.25}),
    )
    assert [item.clause_id for item in result.clauses] == [
        "preferred_moon_and_deficient_fortunes",
        "mercury_moon_and_fortune_protections",
        "moon_mars_or_saturn_consequence",
        "concealed_lending_sequence",
        "emerging_toward_mars_publicity",
        "node_or_burnt_path_warning",
        "first_degree_or_ascending_sign_loan_warning",
    ]
    gate = _clause(result, "first_degree_or_ascending_sign_loan_warning")
    assert gate.state is western.SahlMatterClauseState.TRIGGERED
    assert {item.name: item.value for item in gate.measurements}[
        "moon_in_named_first_degree"
    ] is True
    protections = _clause(result, "mercury_moon_and_fortune_protections")
    protection_measurements = {
        item.name: item.value for item in protections.measurements
    }
    assert protection_measurements["mercury_bodily_joined_malefics"] == "none"
    assert protection_measurements["mercury_square_malefics"] == Body.MARS


def test_investment_keeps_adaptation_cadence_and_degree_lord_open() -> None:
    result = _evaluate(western.SahlMatterProfileId.INVESTMENT)
    assert [item.clause_id for item in result.clauses] == [
        "adapt_moon_mercury_assets_and_trust",
        "moon_mercury_join_and_mars_cadence",
        "retrograde_mercury_branch",
        "trust_significators_and_mars_light",
    ]
    first = {item.name: item.value for item in result.clauses[0].measurements}
    assert first["assets_sign"] == "Taurus"
    assert first["trust_sign"] == "Aquarius"
    assert first["degree_lord_scheme"] is None


def test_purchase_uses_canonical_moieties_and_does_not_invent_lot_orb() -> None:
    result = _evaluate(
        western.SahlMatterProfileId.PURCHASE,
        _chart(**{Body.SUN: 0.0, Body.MOON: 40.0, Body.JUPITER: 51.5}),
    )
    fortune_clause = _clause(
        result, "fortune_fit_in_jupiter_house_and_joined_fortunes"
    )
    moon_clause = _clause(
        result, "straight_ascension_light_number_and_fortunes"
    )
    assert {item.name: item.value for item in fortune_clause.measurements}[
        "lot_joining_orb_policy"
    ] is None
    moon_measurements = {item.name: item.value for item in moon_clause.measurements}
    assert moon_measurements["moon_joined_fortunes"] == Body.JUPITER
    assert moon_clause.state is western.SahlMatterClauseState.NOT_EVALUABLE


def test_sale_separates_sign_configuration_from_bodily_join() -> None:
    result = _evaluate(
        western.SahlMatterProfileId.SALE,
        _chart(**{Body.MOON: 40.0, Body.MARS: 100.0, Body.SATURN: 280.0}),
    )
    relation = _clause(result, "moon_configured_to_malefics_but_not_joined")
    measurements = {item.name: item.value for item in relation.measurements}
    assert Body.MARS in measurements["configured_malefics"].split(",")
    assert measurements["bodily_joined_malefics"] == "none"
    assert relation.state is western.SahlMatterClauseState.SATISFIED


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

"""Source-order and public-surface tests for Dorotheus V.8, V.9, and V.11."""

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


def _chart(*, asc: float = 0.0, mars: float = 95.0, saturn: float = 35.0) -> ChartContext:
    houses = HouseCusps(
        system=HouseSystem.PORPHYRY,
        cusps=tuple((asc + degree) % 360.0 for degree in range(0, 360, 30)),
        asc=asc,
        mc=(asc + 270.0) % 360.0,
        armc=(asc + 270.0) % 360.0,
        effective_system=HouseSystem.PORPHYRY,
        classification=classify_house_system(HouseSystem.PORPHYRY),
        policy=HousePolicy.default(),
    )
    return ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0,
        latitude=40.0,
        longitude=0.0,
        planets={
            Body.SUN: _planet(Body.SUN, 280.0),
            Body.MOON: _planet(Body.MOON, 10.0, latitude=0.05),
            Body.MERCURY: _planet(Body.MERCURY, 65.0),
            Body.VENUS: _planet(Body.VENUS, 155.0),
            Body.MARS: _planet(Body.MARS, mars),
            Body.JUPITER: _planet(Body.JUPITER, 215.0),
            Body.SATURN: _planet(Body.SATURN, saturn),
        },
        nodes={},
        houses=houses,
    )


def _evaluate(
    profile_id: western.DorotheusMatterProfileId,
    *,
    chart: ChartContext | None = None,
    latitude_rate: float = -0.2,
) -> western.DorotheusMatterProfileEvaluation:
    chart = _chart() if chart is None else chart
    moon = western.evaluate_dorotheus_moon_condition(
        chart,
        moon_eclipsed=False,
        unavoidable_time_urgency=None,
        position_product=western.DOROTHEUS_MOON_CONDITION_V1.position_product,
        reader_provenance="synthetic_unit_fixture",
    )
    rooted = western.evaluate_dorotheus_rooted_context(
        chart,
        matter=western.DorotheusMatter.LAND_AND_MANAGEMENT,
        election_class=western.WesternElectionClass.EPHEMERAL,
        next_connection=None,
        reader_provenance="synthetic_unit_fixture",
    )
    return western.evaluate_dorotheus_matter_profile(
        chart,
        profile_id=profile_id,
        moon_condition=moon,
        rooted_context=rooted,
        moon_latitude_rate_degrees_per_day=latitude_rate,
        reader_provenance="synthetic_unit_fixture",
    )


def test_matter_profile_surface_is_public_through_engine_facade_and_root() -> None:
    names = {
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
    }
    assert names <= set(western.__all__)
    assert names <= set(moira.__all__)
    assert names <= set(facade.__all__)
    assert hasattr(moira.Moira, "dorotheus_matter_profile_at")


def test_v8_preserves_descent_and_each_planetary_strength_without_scoring() -> None:
    result = _evaluate(western.DorotheusMatterProfileId.DEMOLITION)
    assert result.profile_version == "1.0.0"
    assert result.status is western.DorotheusMatterProfileStatus.DESCRIPTIVE
    assert result.clauses[0].state is western.DorotheusMatterClauseState.SATISFIED
    assert result.clauses[0].measurements[1].value == "southward"
    assert [item.body for item in result.planetary_strengths] == [
        Body.JUPITER,
        Body.VENUS,
        Body.MARS,
        Body.SATURN,
    ]
    assert result.scoring == "not_provided"
    assert result.complete_electional_judgement is False


def test_v8_northward_motion_is_clear_not_a_fabricated_impediment() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.DEMOLITION,
        latitude_rate=0.2,
    )
    assert result.clauses[0].state is western.DorotheusMatterClauseState.CLEAR
    assert result.triggered_clause_ids == ()


def test_v9_uses_occupancy_only_for_ascendant_and_configuration_for_other_stakes() -> None:
    result = _evaluate(western.DorotheusMatterProfileId.LEASING)
    assert [item.whole_sign_place for item in result.angular_places] == [1, 7, 10, 4]
    assert [item.topic for item in result.angular_places] == [
        "hiring_party",
        "owner_or_provider",
        "amount_or_price",
        "outcome",
    ]
    assert result.clauses[0].state is western.DorotheusMatterClauseState.CLEAR
    assert result.clauses[1].state is western.DorotheusMatterClauseState.TRIGGERED
    assert result.clauses[3].state is western.DorotheusMatterClauseState.TRIGGERED
    assert result.clauses[4].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert "back out" in result.clauses[0].explanation
    assert "betrayal" in result.clauses[1].explanation
    assert "amount or price" in result.clauses[2].explanation
    assert "bad and harmful" in result.clauses[3].explanation
    assert result.status is western.DorotheusMatterProfileStatus.TRIGGERED
    assert result.numerically_complete is False


def test_v11_pisces_fourth_place_preserves_both_terrain_testimonies() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.LAND_PURCHASE,
        chart=_chart(asc=240.0),
    )
    terrain = result.clauses[0]
    assert result.angular_places[0].sign == "Pisces"
    assert terrain.measurements[1].value is True
    assert terrain.measurements[2].value is True
    assert terrain.measurements[3].value == (
        "near_water_or_much_water+mixed_mountains_and_plains"
    )
    assert result.status is western.DorotheusMatterProfileStatus.DESCRIPTIVE
    assert result.numerically_complete is True


def test_profile_policy_identity_is_closed() -> None:
    chart = _chart()
    with pytest.raises(ValueError, match="policy identity"):
        _evaluate_with_policy = western.evaluate_dorotheus_matter_profile
        moon = western.evaluate_dorotheus_moon_condition(
            chart,
            moon_eclipsed=False,
            unavoidable_time_urgency=None,
            position_product=western.DOROTHEUS_MOON_CONDITION_V1.position_product,
            reader_provenance="synthetic_unit_fixture",
        )
        rooted = western.evaluate_dorotheus_rooted_context(
            chart,
            matter=western.DorotheusMatter.LAND_AND_MANAGEMENT,
            election_class=western.WesternElectionClass.EPHEMERAL,
            next_connection=None,
            reader_provenance="synthetic_unit_fixture",
        )
        _evaluate_with_policy(
            chart,
            profile_id=western.DorotheusMatterProfileId.DEMOLITION,
            moon_condition=moon,
            rooted_context=rooted,
            moon_latitude_rate_degrees_per_day=-0.2,
            reader_provenance="synthetic_unit_fixture",
            policy=western.DOROTHEUS_LEASING_V1,
        )
    with pytest.raises(ValueError, match="profile_version"):
        replace(western.DOROTHEUS_DEMOLITION_V1, profile_version="2.0.0")

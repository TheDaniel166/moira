"""Source-order and public-surface tests for Dorotheus V.8-V.11."""

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
from moira._western_electional_construction import (
    _iers_mean_lunar_longitude_degrees,
)


def _planet(
    name: str,
    longitude: float,
    *,
    latitude: float = 0.0,
    speed: float = 1.0,
) -> PlanetData:
    return PlanetData(name, longitude % 360.0, latitude, 1.0, speed, speed < 0.0)


def _chart(
    *,
    asc: float = 0.0,
    sun: float = 280.0,
    moon: float = 10.0,
    moon_speed: float = 13.2,
    mercury: float = 65.0,
    venus: float = 155.0,
    jupiter: float = 215.0,
    mars: float = 95.0,
    saturn: float = 35.0,
) -> ChartContext:
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
            Body.SUN: _planet(Body.SUN, sun),
            Body.MOON: _planet(
                Body.MOON,
                moon,
                latitude=0.05,
                speed=moon_speed,
            ),
            Body.MERCURY: _planet(Body.MERCURY, mercury),
            Body.VENUS: _planet(Body.VENUS, venus),
            Body.MARS: _planet(Body.MARS, mars),
            Body.JUPITER: _planet(Body.JUPITER, jupiter),
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
    lunar_equation: float = 5.0,
    policy: western.DorotheusMatterProfilePolicy | None = None,
) -> western.DorotheusMatterProfileEvaluation:
    chart = _chart() if chart is None else chart
    moon = western.evaluate_dorotheus_moon_condition(
        chart,
        moon_eclipsed=False,
        unavoidable_time_urgency=None,
        position_product=western.DOROTHEUS_MOON_CONDITION_V1.position_product,
        reader_provenance="synthetic_unit_fixture",
    )
    rooted = (
        None
        if profile_id in {
            western.DorotheusMatterProfileId.TRAVEL,
            western.DorotheusMatterProfileId.SHIP_ACQUISITION,
            western.DorotheusMatterProfileId.SHIP_CONSTRUCTION,
            western.DorotheusMatterProfileId.SHIP_LAUNCH,
            western.DorotheusMatterProfileId.LAND_TRAVEL,
            western.DorotheusMatterProfileId.SEA_TRAVEL,
            western.DorotheusMatterProfileId.WRITING_A_WILL,
        }
        else western.evaluate_dorotheus_rooted_context(
            chart,
            matter=(
                western.DorotheusMatter.MERCURIAL_AFFAIRS
                if profile_id
                in {
                    western.DorotheusMatterProfileId.BUYING_AND_SELLING,
                    western.DorotheusMatterProfileId.LUNAR_PRICE_TIMING,
                    western.DorotheusMatterProfileId.PARTNERSHIP,
                    western.DorotheusMatterProfileId.DEBT_AND_PAYMENT,
                }
                else western.DorotheusMatter.LAND_AND_MANAGEMENT
            ),
            election_class=western.WesternElectionClass.EPHEMERAL,
            next_connection=None,
            reader_provenance="synthetic_unit_fixture",
        )
    )
    return western.evaluate_dorotheus_matter_profile(
        chart,
        profile_id=profile_id,
        moon_condition=moon,
        rooted_context=rooted,
        moon_latitude_rate_degrees_per_day=latitude_rate,
        moon_true_longitude_mean_ecliptic_degrees=(
            (_iers_mean_lunar_longitude_degrees(chart.jd_tt) + lunar_equation)
            % 360.0
            if profile_id
            in {
                western.DorotheusMatterProfileId.LUNAR_PRICE_TIMING,
                western.DorotheusMatterProfileId.TRAVEL,
                western.DorotheusMatterProfileId.SHIP_CONSTRUCTION,
                western.DorotheusMatterProfileId.WRITING_A_WILL,
            }
            else None
        ),
        reader_provenance="synthetic_unit_fixture",
        policy=policy,
    )


def test_matter_profile_surface_is_public_through_engine_facade_and_root() -> None:
    names = {
        "DorotheusMatterProfileId",
        "DorotheusSignNatureVariant",
        "DorotheusMatterClauseRole",
        "DorotheusMatterClauseState",
        "DorotheusMatterProfileStatus",
        "DorotheusAngularPlaceWitness",
        "DorotheusMatterClauseWitness",
        "DorotheusMatterProfilePolicy",
        "DorotheusMatterProfileEvaluation",
        "DOROTHEUS_DEMOLITION_V1",
        "DOROTHEUS_LEASING_V1",
        "DOROTHEUS_BUYING_AND_SELLING_V1",
        "DOROTHEUS_LUNAR_PRICE_TIMING_V1",
        "DOROTHEUS_LAND_PURCHASE_V1",
        "DOROTHEUS_TRAVEL_V1",
        "DOROTHEUS_SHIP_ACQUISITION_V1",
        "DOROTHEUS_SHIP_CONSTRUCTION_V1",
        "DOROTHEUS_SHIP_LAUNCH_V1",
        "DOROTHEUS_LAND_TRAVEL_V1",
        "DOROTHEUS_SEA_TRAVEL_V1",
        "DOROTHEUS_PARTNERSHIP_V1",
        "DOROTHEUS_DEBT_AND_PAYMENT_V1",
        "DOROTHEUS_WRITING_A_WILL_V1",
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


def test_v9_public_constructor_rejects_an_implicit_previous_event_window() -> None:
    with pytest.raises(ValueError, match="explicit moon_flow_policy"):
        western.dorotheus_matter_profile_at(
            2451545.0,
            40.0,
            0.0,
            house_system=HouseSystem.PORPHYRY,
            profile_id=western.DorotheusMatterProfileId.LEASING,
            reader=object(),
        )


def test_v10_preserves_both_role_maps_without_aggregating_them() -> None:
    result = _evaluate(western.DorotheusMatterProfileId.BUYING_AND_SELLING)
    assert result.rooted_context.matter is western.DorotheusMatter.MERCURIAL_AFFAIRS
    assert result.clauses[0].clause_id == "moon_flow_role_assignments"
    assert result.clauses[0].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert [item.topic for item in result.angular_places] == [
        "buyer",
        "seller",
        "price",
        "commodity",
    ]
    assert [item.whole_sign_place for item in result.angular_places] == [1, 7, 10, 4]
    assert result.clauses[1].clause_id == "four_stake_role_assignments"
    assert result.clauses[1].state is western.DorotheusMatterClauseState.OBSERVED
    assert result.status is western.DorotheusMatterProfileStatus.INDETERMINATE
    assert result.scoring == "not_provided"


def test_v10_public_constructor_rejects_an_implicit_previous_event_window() -> None:
    with pytest.raises(ValueError, match="explicit moon_flow_policy"):
        western.dorotheus_matter_profile_at(
            2451545.0,
            40.0,
            0.0,
            house_system=HouseSystem.PORPHYRY,
            profile_id=western.DorotheusMatterProfileId.BUYING_AND_SELLING,
            reader=object(),
        )


def test_v44_computes_recension_price_relation_and_preserves_parallel_gap() -> None:
    dear = _evaluate(
        western.DorotheusMatterProfileId.LUNAR_PRICE_TIMING,
        chart=_chart(sun=325.0, moon=10.0),
        latitude_rate=0.2,
        lunar_equation=5.0,
    )
    dear_measurements = {item.name: item.value for item in dear.clauses[0].measurements}
    assert dear_measurements["node_region"] == "rising_aquarius_through_cancer"
    assert dear_measurements["calculation_direction"] == "increasing"
    assert dear_measurements["price_relation"] == "above_value"
    assert dear.clauses[1].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert {item.name: item.value for item in dear.clauses[1].measurements}[
        "speed_threshold"
    ] is None
    assert dear.status is western.DorotheusMatterProfileStatus.INDETERMINATE
    assert dear.numerically_complete is False
    assert len(dear.authorities) == 3

    cheap = _evaluate(
        western.DorotheusMatterProfileId.LUNAR_PRICE_TIMING,
        chart=_chart(sun=155.0, moon=200.0),
        latitude_rate=-0.2,
        lunar_equation=-5.0,
    )
    cheap_measurements = {
        item.name: item.value for item in cheap.clauses[0].measurements
    }
    assert cheap_measurements["node_region"] == "falling_leo_through_capricorn"
    assert cheap_measurements["calculation_direction"] == "decreasing"
    assert cheap_measurements["price_relation"] == "below_value"


@pytest.mark.parametrize(
    ("elongation", "interval", "effect"),
    (
        (45.0, "solar_conjunction_to_left_square", "fair_equivalent_price_for_buying_or_selling"),
        (135.0, "left_square_to_opposition", "seller_benefit"),
        (225.0, "opposition_to_right_square", "buyer_benefit"),
        (315.0, "right_square_to_solar_conjunction", "benefit_for_truthful_and_just_intent"),
    ),
)
def test_v44_preserves_each_directed_phase_interval(
    elongation: float,
    interval: str,
    effect: str,
) -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.LUNAR_PRICE_TIMING,
        chart=_chart(sun=0.0, moon=elongation),
    )
    measurements = {item.name: item.value for item in result.clauses[2].measurements}
    assert measurements["phase_interval"] == interval
    assert measurements["source_effect"] == effect


@pytest.mark.parametrize(
    ("elongation", "boundary"),
    (
        (0.0, "exact_solar_conjunction"),
        (90.0, "exact_left_square"),
        (180.0, "exact_opposition"),
        (270.0, "exact_right_square"),
    ),
)
def test_v44_keeps_exact_phase_boundaries_unassigned(
    elongation: float,
    boundary: str,
) -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.LUNAR_PRICE_TIMING,
        chart=_chart(sun=0.0, moon=elongation),
    )
    measurements = {item.name: item.value for item in result.clauses[2].measurements}
    assert measurements["phase_interval"] == boundary
    assert measurements["source_effect"] == "boundary_between_adjacent_source_intervals"


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


def test_v22_travel_preserves_its_own_stakes_without_inventing_v31_matter() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.TRAVEL,
        chart=_chart(
            moon=40.0,
            mercury=120.0,
            venus=90.0,
            mars=0.0,
            jupiter=220.0,
            saturn=100.0,
        ),
    )
    assert result.rooted_context is None
    assert result.matter == "travel_and_departure"
    assert result.status is western.DorotheusMatterProfileStatus.CLEAR
    assert result.numerically_complete is True
    assert [item.topic for item in result.angular_places] == [
        "traveler",
        "destination_land",
        "business_or_needed_thing",
        "outcome",
    ]
    assert [item.clause_id for item in result.clauses] == [
        "travel_stake_assignments",
        "departure_prerequisites",
        "moon_in_sixth_or_twelfth_travel_harm",
        "moon_increasing_in_calculation_comfort",
        "fortunes_in_ascendant_journey_condition",
        "fortunes_in_seventh_destination_benefit",
        "moon_with_infortune_in_travel_stakes",
        "travel_lords_stationary",
        "fortune_square_or_opposition_moon_connection",
        "infortune_square_or_opposition_moon",
    ]
    assert result.clauses[3].state is western.DorotheusMatterClauseState.SATISFIED
    assert result.clauses[8].state is western.DorotheusMatterClauseState.SATISFIED
    assert result.clauses[9].state is western.DorotheusMatterClauseState.CLEAR
    assert len(result.authorities) == 4


def test_v22_travel_keeps_an_applying_benefic_connection_indeterminate_without_orb() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.TRAVEL,
        chart=_chart(
            moon=40.0,
            mercury=120.0,
            venus=90.0,
            mars=0.0,
            jupiter=225.0,
            saturn=100.0,
        ),
    )
    clause = result.clauses[8]
    measurements = {item.name: item.value for item in clause.measurements}
    assert clause.state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert measurements["jupiter_motion_state"] == "applying"
    assert measurements["applying_fortunes_with_unresolved_degree_interval"] == "Jupiter"
    assert result.status is western.DorotheusMatterProfileStatus.INDETERMINATE


def test_v22_travel_marks_named_moon_place_and_malefic_hard_aspect_as_gates() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.TRAVEL,
        chart=_chart(
            moon=150.0,
            mercury=120.0,
            venus=90.0,
            mars=0.0,
            jupiter=330.0,
            saturn=60.0,
        ),
    )
    assert result.clauses[1].state is western.DorotheusMatterClauseState.TRIGGERED
    assert result.clauses[2].measurements[1].value is True
    assert result.clauses[9].state is western.DorotheusMatterClauseState.TRIGGERED
    assert result.status is western.DorotheusMatterProfileStatus.TRIGGERED


def test_v24_ship_acquisition_preserves_source_order_and_unrooted_preference_gaps() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.SHIP_ACQUISITION,
        chart=_chart(
            asc=30.0,
            moon=30.0,
            jupiter=120.0,
        ),
    )
    assert result.rooted_context is None
    assert result.matter == "ship_acquisition_or_commission"
    assert result.status is western.DorotheusMatterProfileStatus.INDETERMINATE
    assert result.numerically_complete is False
    assert [item.topic for item in result.angular_places] == ["ship_acquisition"]
    assert [item.clause_id for item in result.clauses] == [
        "fortune_in_fourth_looking_at_ascendant_and_moon",
        "water_or_jupiter_venus_house_preference",
        "ascendant_and_moon_in_named_ship_acquisition_signs",
        "ascendant_and_moon_in_pisces",
        "source_ranked_sign_preferences",
    ]
    assert result.clauses[0].state is western.DorotheusMatterClauseState.SATISFIED
    assert result.clauses[1].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert result.clauses[2].state is western.DorotheusMatterClauseState.SATISFIED
    assert result.clauses[4].state is western.DorotheusMatterClauseState.OBSERVED
    assert {item.name: item.value for item in result.clauses[4].measurements}["source_rank"] == 1


def test_v24_ship_acquisition_computes_named_water_preference_and_preserves_capricorn_gap() -> None:
    water = _evaluate(
        western.DorotheusMatterProfileId.SHIP_ACQUISITION,
        chart=_chart(
            asc=0.0,
            moon=0.0,
            jupiter=90.0,
        ),
    )
    assert water.status is western.DorotheusMatterProfileStatus.DESCRIPTIVE
    assert water.clauses[1].state is western.DorotheusMatterClauseState.SATISFIED
    capricorn = _evaluate(
        western.DorotheusMatterProfileId.SHIP_ACQUISITION,
        chart=_chart(
            asc=270.0,
            moon=270.0,
            jupiter=0.0,
        ),
    )
    assert capricorn.clauses[2].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert capricorn.clauses[4].state is western.DorotheusMatterClauseState.NOT_EVALUABLE


def test_v24_ship_acquisition_rejects_radical_or_natal_input() -> None:
    with pytest.raises(ValueError, match="source-unrooted"):
        western.dorotheus_matter_profile_at(
            2451545.0,
            40.0,
            0.0,
            house_system=HouseSystem.PORPHYRY,
            profile_id=western.DorotheusMatterProfileId.SHIP_ACQUISITION,
            election_class=western.WesternElectionClass.RADICAL,
            reader=object(),
        )


def test_v25_ship_construction_preserves_all_source_clauses_and_open_sign_tables() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.SHIP_CONSTRUCTION,
        chart=_chart(moon=300.0, sun=180.0, mars=30.0),
    )
    assert result.rooted_context is None
    assert len(result.clauses) == 6
    assert result.clauses[0].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert result.clauses[3].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert result.numerically_complete is False


def test_v26_ship_launch_preserves_all_thirty_eight_paragraphs_without_a_v31_root() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.SHIP_LAUNCH,
        chart=_chart(moon=0.0, sun=120.0, jupiter=210.0, venus=330.0),
    )
    assert result.rooted_context is None
    assert len(result.clauses) == 38
    assert [item.source_order for item in result.clauses] == list(range(1, 39))
    assert result.clauses[12].clause_id == "launch_sign_table_precondition"
    assert result.clauses[36].clause_id == "launch_moment_distinguished_from_passenger_boarding"
    assert result.clauses[37].state is western.DorotheusMatterClauseState.NOT_EVALUABLE


def test_v26_land_travel_requires_the_named_dry_sign_authority() -> None:
    chart = _chart(asc=0.0, moon=180.0, mars=0.0)
    source_faithful = _evaluate(
        western.DorotheusMatterProfileId.LAND_TRAVEL,
        chart=chart,
    )
    assert source_faithful.rooted_context is None
    assert len(source_faithful.clauses) == 5
    assert source_faithful.clauses[0].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert source_faithful.policy.sign_nature_variant is (
        western.DorotheusSignNatureVariant.SOURCE_TEXT_UNRESOLVED
    )

    lilly = _evaluate(
        western.DorotheusMatterProfileId.LAND_TRAVEL,
        chart=chart,
        policy=western.DorotheusMatterProfilePolicy(
            western.DorotheusMatterProfileId.LAND_TRAVEL,
            sign_nature_variant=(
                western.DorotheusSignNatureVariant.LILLY_1647_ELEMENTAL_QUALITIES
            ),
        ),
    )
    assert lilly.clauses[0].state is western.DorotheusMatterClauseState.TRIGGERED
    assert lilly.clauses[1].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert lilly.clauses[-1].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert lilly.numerically_complete is False


def test_v26_sea_travel_uses_dorotheus_named_water_signs() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.SEA_TRAVEL,
        chart=_chart(moon=180.0, saturn=90.0),
    )
    assert result.rooted_context is None
    assert len(result.clauses) == 3
    assert result.clauses[0].state is western.DorotheusMatterClauseState.TRIGGERED
    assert result.clauses[1].state is western.DorotheusMatterClauseState.OBSERVED
    assert result.clauses[-1].state is western.DorotheusMatterClauseState.NOT_EVALUABLE


def test_v20_partnership_and_v21_debt_keep_their_mercurial_root_contexts() -> None:
    partnership = _evaluate(
        western.DorotheusMatterProfileId.PARTNERSHIP,
        chart=_chart(asc=60.0, moon=60.0, saturn=0.0),
    )
    debt = _evaluate(
        western.DorotheusMatterProfileId.DEBT_AND_PAYMENT,
        chart=_chart(asc=0.0, moon=120.0, mercury=90.0, saturn=90.0),
    )
    assert partnership.rooted_context is not None
    assert partnership.matter == "entering_a_partnership"
    assert len(partnership.clauses) == 19
    assert partnership.clauses[3].state is western.DorotheusMatterClauseState.SATISFIED
    assert debt.rooted_context is not None
    assert debt.matter == "debt_and_payment"
    assert len(debt.clauses) == 8
    assert debt.clauses[2].state is western.DorotheusMatterClauseState.TRIGGERED


def test_v43_writing_a_will_preserves_open_connected_star_condition() -> None:
    result = _evaluate(
        western.DorotheusMatterProfileId.WRITING_A_WILL,
        chart=_chart(asc=0.0, moon=65.0, sun=0.0),
    )
    assert result.rooted_context is None
    assert len(result.clauses) == 6
    assert result.clauses[1].state is western.DorotheusMatterClauseState.NOT_EVALUABLE
    assert result.clauses[2].state is western.DorotheusMatterClauseState.NOT_EVALUABLE


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

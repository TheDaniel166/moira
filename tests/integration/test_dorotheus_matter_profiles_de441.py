"""DE441 regression and invariant evidence for Dorotheus matter profiles."""

from __future__ import annotations

from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.constants import HouseSystem
from moira.spk_reader import SpkReader
from moira.western_electional import (
    MoonConnectionFlowPolicy,
    MoonPreviousEventWindowPolicy,
    DorotheusMatterProfileId,
    DorotheusMatterProfileStatus,
    DorotheusSignNatureVariant,
    dorotheus_matter_profile_at,
)


@pytest.mark.requires_ephemeris
def test_j2000_matter_profiles_share_one_kernel_bound_public_contract() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    with SpkReader(kernel) as reader:
        results = {
            profile_id: dorotheus_matter_profile_at(
                2451545.0,
                51.5074,
                -0.1278,
                house_system=HouseSystem.REGIOMONTANUS,
                profile_id=profile_id,
                moon_flow_policy=(
                    MoonConnectionFlowPolicy(
                        MoonPreviousEventWindowPolicy.CURRENT_SIGN
                    )
                    if profile_id in {
                        DorotheusMatterProfileId.LEASING,
                        DorotheusMatterProfileId.BUYING_AND_SELLING,
                    }
                    else None
                ),
                sign_nature_variant=(
                    DorotheusSignNatureVariant.SOURCE_TEXT_UNRESOLVED
                    if profile_id
                    in {
                        DorotheusMatterProfileId.LAND_TRAVEL,
                        DorotheusMatterProfileId.SEA_TRAVEL,
                    }
                    else None
                ),
                reader=reader,
            )
            for profile_id in DorotheusMatterProfileId
        }

    demolition = results[DorotheusMatterProfileId.DEMOLITION]
    leasing = results[DorotheusMatterProfileId.LEASING]
    commerce = results[DorotheusMatterProfileId.BUYING_AND_SELLING]
    price_timing = results[DorotheusMatterProfileId.LUNAR_PRICE_TIMING]
    land = results[DorotheusMatterProfileId.LAND_PURCHASE]
    travel = results[DorotheusMatterProfileId.TRAVEL]
    ship_acquisition = results[DorotheusMatterProfileId.SHIP_ACQUISITION]
    ship_construction = results[DorotheusMatterProfileId.SHIP_CONSTRUCTION]
    ship_launch = results[DorotheusMatterProfileId.SHIP_LAUNCH]
    land_travel = results[DorotheusMatterProfileId.LAND_TRAVEL]
    sea_travel = results[DorotheusMatterProfileId.SEA_TRAVEL]
    partnership = results[DorotheusMatterProfileId.PARTNERSHIP]
    debt = results[DorotheusMatterProfileId.DEBT_AND_PAYMENT]
    will = results[DorotheusMatterProfileId.WRITING_A_WILL]
    assert all(Path(item.reader_provenance).name == "de441.bsp" for item in results.values())
    assert demolition.clauses[0].measurements[0].value < 0.0
    assert demolition.status is DorotheusMatterProfileStatus.DESCRIPTIVE
    assert leasing.angular_places[0].whole_sign_place == 1
    assert leasing.clauses[-1].clause_id == "moon_separation_and_connection_flow"
    assert leasing.moon_connection_flow is not None
    assert leasing.moon_connection_flow.previous_separation is not None
    assert leasing.moon_connection_flow.next_connection is not None
    assert leasing.moon_connection_flow.previous_motion is not None
    assert leasing.clauses[-1].measurements[-1].value.startswith("V.9-specific")
    assert leasing.numerically_complete is False
    assert commerce.rooted_context.matter.value == "mercurial_affairs"
    assert commerce.moon_connection_flow is not None
    assert commerce.clauses[0].state.value == "observed"
    commerce_measurements = {
        item.name: item.value for item in commerce.clauses[0].measurements
    }
    assert commerce_measurements["commodity_significator"] == "Moon"
    assert commerce_measurements["seller_significator"] is not None
    assert commerce_measurements["buyer_significator"] is not None
    assert commerce_measurements["price_significator"] == commerce_measurements[
        "buyer_significator"
    ]
    assert price_timing.rooted_context.matter.value == "mercurial_affairs"
    assert price_timing.clauses[0].clause_id == (
        "tabari_sign_region_and_calculation_price_relation"
    )
    assert price_timing.clauses[1].clause_id == (
        "hephaistion_parallel_latitude_and_speed_reading"
    )
    assert price_timing.clauses[1].state.value == "not_evaluable"
    phase_measurements = {
        item.name: item.value for item in price_timing.clauses[2].measurements
    }
    assert 0.0 <= phase_measurements["moon_sun_elongation"] < 360.0
    assert phase_measurements["phase_interval"]
    assert price_timing.numerically_complete is False
    assert [item.topic for item in land.angular_places] == [
        "land",
        "trees",
        "vegetation",
        "cultivation",
    ]
    assert all(item.complete_electional_judgement is False for item in results.values())
    assert travel.rooted_context is None
    assert travel.matter == "travel_and_departure"
    assert len(travel.clauses) == 10
    assert travel.clauses[0].clause_id == "travel_stake_assignments"
    assert ship_acquisition.rooted_context is None
    assert ship_acquisition.matter == "ship_acquisition_or_commission"
    assert len(ship_acquisition.clauses) == 5
    assert ship_acquisition.clauses[0].clause_id == (
        "fortune_in_fourth_looking_at_ascendant_and_moon"
    )
    assert ship_construction.rooted_context is None
    assert len(ship_construction.clauses) == 6
    assert ship_launch.rooted_context is None
    assert len(ship_launch.clauses) == 38
    assert land_travel.rooted_context is None
    assert land_travel.policy.sign_nature_variant is (
        DorotheusSignNatureVariant.SOURCE_TEXT_UNRESOLVED
    )
    assert len(land_travel.clauses) == 5
    assert sea_travel.rooted_context is None
    assert sea_travel.policy.sign_nature_variant is (
        DorotheusSignNatureVariant.SOURCE_TEXT_UNRESOLVED
    )
    assert len(sea_travel.clauses) == 3
    assert partnership.rooted_context.matter.value == "mercurial_affairs"
    assert len(partnership.clauses) == 19
    assert debt.rooted_context.matter.value == "mercurial_affairs"
    assert len(debt.clauses) == 8
    assert will.rooted_context is None
    assert len(will.clauses) == 6

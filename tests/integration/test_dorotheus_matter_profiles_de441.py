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
                reader=reader,
            )
            for profile_id in DorotheusMatterProfileId
        }

    demolition = results[DorotheusMatterProfileId.DEMOLITION]
    leasing = results[DorotheusMatterProfileId.LEASING]
    commerce = results[DorotheusMatterProfileId.BUYING_AND_SELLING]
    price_timing = results[DorotheusMatterProfileId.LUNAR_PRICE_TIMING]
    land = results[DorotheusMatterProfileId.LAND_PURCHASE]
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

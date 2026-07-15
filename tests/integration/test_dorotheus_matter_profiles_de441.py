"""DE441 regression and invariant evidence for Dorotheus matter profiles."""

from __future__ import annotations

from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.constants import HouseSystem
from moira.spk_reader import SpkReader
from moira.western_electional import (
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
                reader=reader,
            )
            for profile_id in DorotheusMatterProfileId
        }

    demolition = results[DorotheusMatterProfileId.DEMOLITION]
    leasing = results[DorotheusMatterProfileId.LEASING]
    land = results[DorotheusMatterProfileId.LAND_PURCHASE]
    assert all(Path(item.reader_provenance).name == "de441.bsp" for item in results.values())
    assert demolition.clauses[0].measurements[0].value < 0.0
    assert demolition.status is DorotheusMatterProfileStatus.DESCRIPTIVE
    assert leasing.angular_places[0].whole_sign_place == 1
    assert leasing.clauses[-1].clause_id == "moon_separation_and_connection_flow"
    assert leasing.numerically_complete is False
    assert [item.topic for item in land.angular_places] == [
        "land",
        "trees",
        "vegetation",
        "cultivation",
    ]
    assert all(item.complete_electional_judgement is False for item in results.values())

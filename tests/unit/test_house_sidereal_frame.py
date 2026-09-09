"""Selected-zodiac sign sectors and invariant physical house frames.

Authority: the explicit 30-degree sign-sector definition. Synthetic ARMC,
true obliquity and latitude isolate frame arithmetic; these are not external
astronomical accuracy fixtures. Circular residual tolerance 1e-10 degrees
covers double-precision coordinate relabelling, not cusp membership policy.
"""

import pytest

from moira.constants import HouseSystem
from moira.houses import (
    HousePolicy,
    PolarFallbackPolicy,
    assign_house,
    calculate_houses,
    houses_from_armc,
)


@pytest.mark.parametrize(
    "offset", [0.0, 8.0, 23.853219346200856, 24.0, -12.125, 350.25]
)
@pytest.mark.parametrize("system", [HouseSystem.WHOLE_SIGN, HouseSystem.SOLAR_SIGN])
def test_sign_defined_houses_start_at_selected_zodiac_sign(offset, system):
    result = houses_from_armc(
        100.0, 23.4, 40.0, system, sun_longitude=8.5, ayanamsa_offset=offset
    )
    anchor = result.asc if system == HouseSystem.WHOLE_SIGN else (8.5 - offset) % 360
    opening = int(anchor // 30) * 30
    assert result.cusps == tuple((opening + 30 * i) % 360 for i in range(12))
    assert result.armc == 100
    assert assign_house(anchor, result).house == 1
    for house, cusp in enumerate(result.cusps, 1):
        assert assign_house(cusp, result).house == house


@pytest.mark.parametrize(
    "system",
    [
        HouseSystem.PLACIDUS,
        HouseSystem.PORPHYRY,
        HouseSystem.EQUAL,
        HouseSystem.CAMPANUS,
    ],
)
def test_physical_membership_and_armc_are_preserved_for_non_sign_systems(system):
    offset = 23.853219346200856
    physical = houses_from_armc(100, 23.4, 40, system, include_boundary_geometry=True)
    shifted = houses_from_armc(
        100, 23.4, 40, system, ayanamsa_offset=offset, include_boundary_geometry=True
    )
    assert physical.armc == shifted.armc
    for longitude in [i * 7.125 for i in range(51)]:
        assert (
            assign_house(longitude, physical).house
            == assign_house((longitude - offset) % 360, shifted).house
        )
    for first, second in zip(
        physical.boundary_geometry.boundaries, shifted.boundary_geometry.boundaries
    ):
        assert first.anchor_direction == second.anchor_direction
        assert first.plane_normal == second.plane_normal
        residual = (
            second.cusp_longitude - (first.cusp_longitude - offset) + 180
        ) % 360 - 180
        assert abs(residual) < 1e-10


def test_polar_fallback_whole_sign_is_constructed_in_selected_zodiac():
    policy = HousePolicy(polar_fallback=PolarFallbackPolicy.FALLBACK_TO_WHOLE_SIGN)
    result = houses_from_armc(
        100, 23.4, 80, HouseSystem.KOCH, policy=policy, ayanamsa_offset=24
    )
    assert result.system == HouseSystem.KOCH
    assert result.effective_system == HouseSystem.WHOLE_SIGN
    assert result.fallback and result.fallback_reason
    assert result.cusps[0] == int(result.asc // 30) * 30
    assert all(c % 30 == 0 for c in result.cusps)


def test_calculate_houses_forwards_the_selected_zodiac(jd_j2000):
    result = calculate_houses(
        jd_j2000, 51.5, -0.1, HouseSystem.WHOLE_SIGN, ayanamsa_offset=24
    )
    assert result.cusps[0] == int(result.asc // 30) * 30
    assert all(c % 30 == 0 for c in result.cusps)

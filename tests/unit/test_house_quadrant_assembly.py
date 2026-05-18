"""
Quadrant house-figure assembly covenant tests.

These are primary proof tests for the shared cusp-assembly doctrine used by
the Moira-owned quadrant systems rewritten in the clean-room audit program.
"""

from __future__ import annotations

import pytest

from moira.constants import HouseSystem
from moira.houses import calculate_houses


@pytest.mark.parametrize(
    "system",
    [
        HouseSystem.KOCH,
        HouseSystem.REGIOMONTANUS,
        HouseSystem.TOPOCENTRIC,
        HouseSystem.KRUSINSKI,
    ],
)
@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 80.0, 0.0),
        (2456334.666667, 89.9, 0.0),
        (2456334.500000, -89.9, 0.0),
    ],
)
def test_quadrant_assembly_preserves_cardinal_and_antipodal_doctrine(
    system: str,
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
) -> None:
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, system)

    assert houses.cusps[0] == pytest.approx(houses.asc, abs=1e-9)
    assert houses.cusps[6] == pytest.approx((houses.cusps[0] + 180.0) % 360.0, abs=1e-9)
    assert houses.cusps[3] == pytest.approx((houses.cusps[9] + 180.0) % 360.0, abs=1e-9)

    for source, opposite in ((1, 7), (2, 8), (3, 9), (5, 11), (6, 12)):
        assert houses.cusps[opposite - 1] == pytest.approx(
            (houses.cusps[source - 1] + 180.0) % 360.0,
            abs=1e-9,
        ), (system, jd_ut, latitude_deg, source, opposite)

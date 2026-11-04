"""Geometric witnesses from Savard's 2012 description and the declared domain."""

import math

import pytest

from moira.constants import HouseSystem
from moira.houses import houses_from_armc


@pytest.mark.parametrize("latitude", (45.0, -45.0, 0.0, 80.0, -80.0))
def test_declination_cuts_and_boundary_planes(latitude):
    obliquity = 23.44
    figure = houses_from_armc(
        0.0, obliquity, latitude, HouseSystem.SAVARD_A, include_boundary_geometry=True,
    )
    phi, eps = map(math.radians, (latitude, obliquity))
    expected = []
    for house in range(1, 13):
        # At ARMC zero the east component is y. This equation reconstructs
        # the prime-vertical point using its prescribed declination directly.
        quarter, step = divmod(house - 1, 3)
        fraction = (step if quarter % 2 == 0 else 3 - step) / 3
        height = math.sin(phi * fraction)
        vertical = height / math.sin(phi) if phi else fraction
        eastward = math.sqrt(1.0 - vertical**2)
        if quarter in (1, 2):
            eastward = -eastward
        if quarter in (0, 1):
            vertical = -vertical
            height = -height
        # Move parallel to north until z = y tan(eps), then read longitude.
        displacement = (eastward * math.tan(eps) - height) / math.cos(phi)
        x = vertical * math.cos(phi) - displacement * math.sin(phi)
        expected.append(math.degrees(math.atan2(eastward / math.cos(eps), x)) % 360)

    assert figure.cusps == pytest.approx(expected, abs=1e-9, rel=0)
    assert figure.cusps[0] == pytest.approx(figure.asc)
    assert figure.cusps[9] == pytest.approx(figure.mc)
    for boundary in figure.boundary_geometry.boundaries:
        nx, _, nz = boundary.plane_normal
        assert -nx * math.sin(phi) + nz * math.cos(phi) == pytest.approx(0, abs=1e-12)


def test_equator_limit_is_continuous_and_distinct_from_campanus():
    equator = houses_from_armc(0, 23.44, 0, HouseSystem.SAVARD_A)
    for latitude in (-1e-7, 1e-7):
        figure = houses_from_armc(0, 23.44, latitude, HouseSystem.SAVARD_A)
        assert figure.cusps == pytest.approx(equator.cusps, abs=1e-7, rel=0)
    savard = houses_from_armc(0, 23.44, 45, HouseSystem.SAVARD_A)
    campanus = houses_from_armc(0, 23.44, 45, HouseSystem.CAMPANUS)
    assert savard.cusps[1:3] == pytest.approx((132.243356743, 149.465043814), abs=1e-9)
    assert abs(savard.cusps[1] - campanus.cusps[1]) > 6


@pytest.mark.parametrize(("armc", "latitude", "reason"), (
    (270, 66.56, "degenerate"),
    (90, -66.56, "degenerate"),
    (270, 80, "reverses"),
    (90, -80, "reverses"),
    (0, 90, "non-polar"),
    (0, -90, "non-polar"),
))
def test_undefined_or_reversed_figure_is_rejected(armc, latitude, reason):
    with pytest.raises(ValueError, match=reason):
        houses_from_armc(armc, 23.44, latitude, HouseSystem.SAVARD_A)

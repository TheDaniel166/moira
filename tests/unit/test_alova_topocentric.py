"""Alova (2010), tables 1–3 and the effective-latitude construction."""

import math

import pytest

from moira.constants import HouseSystem
from moira.houses import houses_from_armc


_OBLIQUITY = 23.44222


def _published_construction(armc, latitude):
    pole = latitude - (latitude + 2 * _OBLIQUITY - 90) ** 2 / (4 * _OBLIQUITY)
    eps = math.radians(_OBLIQUITY)
    tangent = math.tan(math.radians(pole))
    result = []
    for offset, factor in ((-60, 1 / 3), (-30, 2 / 3), (0, 1), (30, 2 / 3), (60, 1 / 3)):
        theta = math.radians(armc + offset)
        result.append(math.degrees(math.atan2(
            math.cos(theta), -math.cos(eps) * math.sin(theta) - math.sin(eps) * tangent * factor,
        )) % 360)
    theta = math.radians(armc)
    mc = math.degrees(math.atan2(math.sin(theta), math.cos(theta) * math.cos(eps))) % 360
    return pole, (mc, *result)


@pytest.mark.parametrize(("latitude", "printed"), (
    (50, ((47, 28), (85, 8), (119, 34), (147, 36), (167, 48), (193, 57))),
    (70, ((47, 28), (90, 54), (127, 33), (153, 18), (169, 31), (192, 49))),
))
def test_published_tables(latitude, printed):
    result = houses_from_armc(45, _OBLIQUITY, latitude, HouseSystem.ALOVA_TOPOCENTRIC)
    effective_latitude, expected = _published_construction(45, latitude)
    cusps = result.cusps[9:] + result.cusps[:3]
    assert result.effective_latitude == pytest.approx(effective_latitude, abs=1e-11, rel=0)
    assert cusps == pytest.approx(expected, abs=1e-10, rel=0)
    errors = [(cusp - degree) * 60 - minute for cusp, (degree, minute) in zip(cusps, printed, strict=True)]
    assert [index for index, error in enumerate(errors) if abs(error) > 1] == ([4] if latitude == 70 else [])
    if latitude == 70:
        assert errors[4] == pytest.approx(-3.334228754, abs=1e-8)


def test_matches_topocentric_through_threshold():
    latitude = 90 - 2 * _OBLIQUITY
    classic = houses_from_armc(45, _OBLIQUITY, latitude, HouseSystem.TOPOCENTRIC)
    alova = houses_from_armc(45, _OBLIQUITY, latitude, HouseSystem.ALOVA_TOPOCENTRIC)
    assert alova.cusps == classic.cusps
    assert alova.effective_latitude == latitude


def test_distinct_physical_ascendant_and_virtual_horizon():
    north = houses_from_armc(45, _OBLIQUITY, 80, HouseSystem.ALOVA_TOPOCENTRIC, include_boundary_geometry=True)
    south = houses_from_armc(225, _OBLIQUITY, -80, HouseSystem.ALOVA_TOPOCENTRIC)
    assert north.astronomical_asc_defined is True
    assert north.asc == pytest.approx(166.319276992)
    assert north.cusps[0] == pytest.approx(155.071348246)
    assert south.effective_latitude == -north.effective_latitude
    assert south.cusps == pytest.approx(tuple((cusp + 180) % 360 for cusp in north.cusps))
    theta, phi = map(math.radians, (45, north.effective_latitude))
    zenith = (math.cos(theta) * math.cos(phi), math.sin(theta) * math.cos(phi), math.sin(phi))
    assert north.boundary_geometry.boundaries[0].plane_normal == pytest.approx(zenith)
    assert north.boundary_geometry.observer_latitude_deg == 80


def test_pole_limit_and_singularity():
    near = houses_from_armc(270, _OBLIQUITY, 89.999999, HouseSystem.ALOVA_TOPOCENTRIC)
    assert near.cusps[0] == pytest.approx(0, abs=1e-10)
    at_pole = houses_from_armc(45, _OBLIQUITY, 90, HouseSystem.ALOVA_TOPOCENTRIC)
    assert at_pole.astronomical_asc_defined is False
    assert at_pole.cusps[0] == pytest.approx(155.701882638)
    with pytest.raises(ValueError, match="singular"):
        houses_from_armc(270, _OBLIQUITY, 90, HouseSystem.ALOVA_TOPOCENTRIC)


def test_published_cusp_crossing_is_not_reordered():
    _, (_, _, h12, h1, _, _) = _published_construction(236, 80)
    assert h12 > h1
    with pytest.raises(ValueError, match="ordered cusp cycle"):
        houses_from_armc(236, _OBLIQUITY, 80, HouseSystem.ALOVA_TOPOCENTRIC)

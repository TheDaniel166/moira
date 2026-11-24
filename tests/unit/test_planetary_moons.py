"""Analytic geometry and failure-policy tests for planetary moon snapshots."""

from math import asin, atan, cos, sin, sqrt

import pytest

from moira._planetary_moon_geometry import disk_overlap, sky_offsets_arcsec
from moira.planetary_moons import PlanetaryMoons, _received
from moira.spk_reader import OutOfRangeError


@pytest.mark.parametrize("axis,radius", [(1, 10.0), (2, 8.0)])
def test_spheroid_contacts_along_principal_sky_axes(axis, radius):
    # The tangent plane of the perspective spheroid has half-axes
    # R / sqrt(D**2 - a**2) for equatorial incidence.
    planet = (10_000.0, 0.0, 0.0)
    limb = atan(radius / sqrt(10_000.0**2 - 10.0**2))
    moon_radius = asin(1.0 / 9_800.0)

    def overlap(angle):
        target = [9_800.0 * cos(angle), 0.0, 0.0]
        target[axis] = 9_800.0 * sin(angle)
        return disk_overlap(planet, (0.0, 0.0, 1.0), (10.0, 8.0), tuple(target), 1.0)

    assert overlap(limb + moon_radius + 1e-8) == "clear"
    assert overlap(limb + moon_radius) == "contact"
    assert overlap(limb) == "partial"
    assert overlap(limb - moon_radius) == "contact"
    assert overlap(limb - moon_radius - 1e-8) == "contained"


def test_spherical_limb_and_sky_axis_signs():
    assert disk_overlap((100.0, 0.0, 0.0), (0.0, 0.0, 1.0), (3.0, 3.0),
                        (90.0, 0.0, 0.0), 1.0) == "contained"
    east, north = sky_offsets_arcsec((100.0, 0.0, 0.0), (90.0, 1.0, -1.0))
    assert east > 0.0 > north
    assert east == -north


def test_light_time_checks_retarded_coverage():
    def position(body, offset):
        assert body == 501
        if offset < 0:
            raise OutOfRangeError("missing emission segment", out_of_range_times=True)
        return 1000.0, 0.0, 0.0

    with pytest.raises(OutOfRangeError, match="emission"):
        _received(501, (0.0, 0.0, 0.0), 0.0, position)


def test_light_time_uses_emission_segment_at_a_priority_seam():
    def position(body, offset):
        return (1000.0 if offset >= 0.0 else 2000.0, 0.0, 0.0)

    xyz, offset = _received(501, (0.0, 0.0, 0.0), 0.0, position)
    assert xyz == (2000.0, 0.0, 0.0)
    assert offset < 0.0


def test_missing_or_invalid_manifest_fails_before_opening_kernel(tmp_path):
    manifest = tmp_path / "manifest.json"
    with pytest.raises(FileNotFoundError):
        PlanetaryMoons.open(de441_path=tmp_path / "base.bsp", manifest_path=manifest)
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        PlanetaryMoons.open(de441_path=tmp_path / "base.bsp", manifest_path=manifest)

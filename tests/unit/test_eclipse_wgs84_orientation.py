"""Analytic and real solar ray evidence independent of Earth orientation."""
from fractions import Fraction
import math
import random

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_wgs84_orientation import (
    bound_conditional_solar_ray_any_orientation, bound_wgs84_solar_axis_any_orientation,
)
from moira.constants import Body, C_KM_PER_DAY
from moira.corrections import _apply_light_time_split
from moira.eclipse import _WGS84_POLAR_RADIUS_KM, _eclipse_body_pair
from moira.planets import _barycentric_at_tt_offset, _earth_barycentric_at_tt_offset


def _box(x, y, z):
    return tuple(I.point(value) for value in (x, y, z))


@pytest.mark.parametrize("y,expected", [
    (0.0, "intersects_every_orientation"),
    (7000.0, "misses_every_orientation"),
    (float.fromhex("0x1.8d4c097aa975cp+12"), "unresolved"),
    (6378.137, "unresolved"),
])
def test_parallel_rays_with_known_sphere_outcomes(y, expected):
    evidence = bound_wgs84_solar_axis_any_orientation(_box(100000384000.0, y, 0), _box(384000, y, 0))
    assert evidence.result == expected
    assert not evidence.source_vectors_attested
    assert not evidence.rounded_legacy_orientation_enclosed
    assert not evidence.solar_eclipse_occurrence_certified
    assert not evidence.event_wide_path_certified


def test_forward_direction_and_degenerate_ray_are_handled():
    away = bound_wgs84_solar_axis_any_orientation(_box(-100000000, 0, 0), _box(384000, 0, 0))
    assert away.result == "misses_every_orientation"
    with pytest.raises(EnclosureUnavailable, match="direction"):
        bound_wgs84_solar_axis_any_orientation(_box(1, 2, 3), _box(1, 2, 3))


def test_pinned_polar_radius_matches_current_source_constant():
    evidence = bound_wgs84_solar_axis_any_orientation(_box(100000384000, 0, 0), _box(384000, 0, 0))
    assert evidence.polar_radius_km == Fraction.from_float(_WGS84_POLAR_RADIUS_KM)
    assert "pinned" in evidence.polar_radius_model


@pytest.mark.parametrize("y,hit", [(0.0, True), (7000.0, False)])
def test_analytic_result_agrees_with_sampled_oriented_ellipsoid_quadratics(y, hit):
    rng = random.Random(718)
    sun, moon = (100000384000.0, y, 0.0), (384000.0, y, 0.0)
    b = float.fromhex("0x1.8d4c097aa975cp+12")
    for _ in range(50):
        theta, phi = rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi)

        def rotate(vector):
            x, yy, z = vector
            x, yy = math.cos(theta) * x - math.sin(theta) * yy, math.sin(theta) * x + math.cos(theta) * yy
            return math.cos(phi) * x + math.sin(phi) * z, yy, -math.sin(phi) * x + math.cos(phi) * z

        s, m = rotate(sun), rotate(moon)
        d = tuple(a - z for a, z in zip(m, s))
        weights = (1 / 6378.137**2, 1 / 6378.137**2, 1 / b**2)
        a = sum(w * value * value for w, value in zip(weights, d))
        half_b = sum(w * point * value for w, point, value in zip(weights, m, d))
        c = sum(w * value * value for w, value in zip(weights, m)) - 1
        discriminant = half_b * half_b - a * c
        assert (discriminant > 0) is hit


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt,expected", [
    (2460409.263, "intersects_every_orientation"),
    (2460416.263, "misses_every_orientation"),
])
def test_real_split_solar_source_vectors_and_ray_evidence(planetary_reader, tt, expected):
    evidence = bound_conditional_solar_ray_any_orientation(
        planetary_reader, tt, I(Fraction(-5, 86400), Fraction(5, 86400)),
    )
    assert evidence.ray.result == expected
    assert len(evidence.vectors.spk_usages) == 34
    assert not evidence.source_and_arithmetic_attested
    assert not evidence.rounded_legacy_axis_or_orientation_enclosed
    for seconds in (-4, 0, 4):
        epoch = tt + seconds / 86400
        sun, moon = _eclipse_body_pair(epoch, planetary_reader, sun_retarded=True, moon_retarded=True)
        assert all(box.contains(value) for box, value in zip(evidence.vectors.sun_retarded_km, sun))
        assert all(box.contains(value) for box, value in zip(evidence.vectors.moon_retarded_km, moon))
        point = bound_wgs84_solar_axis_any_orientation(tuple(I.point(x) for x in sun), tuple(I.point(x) for x in moon))
        assert point.result == expected
        earth = _earth_barycentric_at_tt_offset(epoch, 0.0, planetary_reader)
        for body_name, steps in ((Body.SUN, evidence.vectors.sun_iterations),
                                 (Body.MOON, evidence.vectors.moon_iterations)):
            seen = []

            def body(body_id, reception, offset, reader):
                bary = _barycentric_at_tt_offset(body_id, reception, offset, reader)
                seen.append((offset, bary))
                return bary

            _apply_light_time_split(body_name, epoch, planetary_reader, earth, body)
            relative = Fraction.from_float(epoch) - Fraction.from_float(tt)
            for (offset, bary), step in zip(seen[1:], steps):
                assert step.emission_tt_offset_days.contains(relative + Fraction.from_float(offset))
                xyz = tuple(a - b for a, b in zip(bary, earth))
                assert all(box.contains(value) for box, value in zip(step.geocentric_km, xyz))
                assert step.next_delay_days.contains(math.sqrt(sum(value * value for value in xyz)) / C_KM_PER_DAY)

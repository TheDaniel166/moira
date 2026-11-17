"""Analytic and independently optimized tests for opt-in shadow geometry."""
from dataclasses import FrozenInstanceError
import math
import random

import pytest

from moira.lunar_shadow_models import (
    LunarShadowDomainError,
    danjon_angular_shadow,
    spherical_cone_shadow,
)


def _rotate(v):
    # An exactly orthogonal permutation avoids an approximate matrix oracle.
    return v[2], -v[0], -v[1]


def _numeric_cone_distance(t, r, k):
    # Independently optimize distance to the union of cross-section disks.
    def f(u):
        return (u - t) ** 2 + max(0.0, r - k * u) ** 2
    lo, hi = 0.0, max(1.0, abs(t) + r / k + 10.0)
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    left, right = hi - ratio * (hi - lo), lo + ratio * (hi - lo)
    for _ in range(120):
        if f(left) <= f(right):
            hi, right = right, left
            left = hi - ratio * (hi - lo)
        else:
            lo, left = left, right
            right = lo + ratio * (hi - lo)
    return math.sqrt(min(f(0), f(lo), f(hi)))


def test_danjon_exact_tangencies_and_legacy_mixed_geometry_witness():
    re, rs, rm = 6378.137, 696340.0, 1737.4
    s, d = 149597870.7, 384400.0
    alpha = math.asin(rm / d)
    pen = 1.01 * math.asin(re / d) + math.asin(rs / s) + math.asin(re / s)
    umb = 1.01 * math.asin(re / d) - math.asin(rs / s) + math.asin(re / s)
    sun = (s, 0.0, 0.0)
    for boundary, attr in ((pen + alpha, "penumbral_margin"),
                           (umb + alpha, "umbral_margin"),
                           (umb - alpha, "total_margin")):
        for offset in (-1e-8, 0.0, 1e-8):
            angle = boundary + offset
            moon = (-d * math.cos(angle), d * math.sin(angle), 0.0)
            result = danjon_angular_shadow(sun, moon, earth_radius_km=re,
                                           sun_radius_km=rs, moon_radius_km=rm)
            assert getattr(result, attr) == pytest.approx(-offset, abs=2e-17)
            assert result.gamma == pytest.approx(d * math.sin(angle) / re)
            assert result.axis_distance_km == pytest.approx(d * math.sin(angle))
            assert result.margin_unit == "rad"
            assert result.penumbral_magnitude == pytest.approx(result.penumbral_margin / (2 * alpha))
            rotated = danjon_angular_shadow(_rotate(sun), _rotate(moon),
                earth_radius_km=re, sun_radius_km=rs, moon_radius_km=rm)
            assert rotated == result
    # The legacy mixed axis distance and arc lengths are inconsistent with
    # the explicitly defined angular circles at their exact contact.
    assert d * (pen + alpha - math.sin(pen + alpha)) == pytest.approx(1.122924670, abs=1e-8)
    with pytest.raises(FrozenInstanceError):
        result.gamma = 0


def test_cone_mantle_overlap_and_containment_boundaries():
    re, rs, rm, s, z = 10.0, 20.0, 2.0, 1000.0, 300.0
    sun = (s, 0.0, 0.0)
    su, sp = (rs - re) / s, (rs + re) / s
    cu, cp = math.sqrt(1 - su * su), math.sqrt(1 - sp * sp)
    for sine, cosine, side, attr in (
        (sp, cp, 1, "penumbral_margin"),
        (su, cu, -1, "umbral_margin"),
        (su, cu, -1, "total_margin"),
    ):
        threshold = (re + side * sine * z + (rm if attr != "total_margin" else -rm)) / cosine
        for delta in (-1e-5, 0.0, 1e-5):
            moon = (-z, threshold + delta, 0.0)
            result = spherical_cone_shadow(sun, moon, earth_radius_km=re,
                                            sun_radius_km=rs, moon_radius_km=rm)
            assert getattr(result, attr) == pytest.approx(-cosine * delta, abs=1e-12)
            assert result.margin_unit == "km"
            assert result.policy == "static_finite_cone"
            assert result.penumbral_magnitude is None
            assert spherical_cone_shadow(_rotate(sun), _rotate(moon), earth_radius_km=re,
                sun_radius_km=rs, moon_radius_km=rm) == result


def test_umbra_apex_intersection_tangency_and_false_positive():
    kw = dict(earth_radius_km=10, sun_radius_km=20, moon_radius_km=2)
    sun = (1000, 0, 0)
    assert spherical_cone_shadow(sun, (-1001, 0, 0), **kw).umbral_margin == pytest.approx(1)
    assert spherical_cone_shadow(sun, (-1002, 0, 0), **kw).umbral_margin == pytest.approx(0)
    assert spherical_cone_shadow(sun, (-1003, 0, 0), **kw).umbral_margin == pytest.approx(-1)
    # The extended-side formula alone incorrectly gives positive 1.5 here.
    assert spherical_cone_shadow(sun, (-1050, 0, 0), **kw).umbral_margin == pytest.approx(-48)


def test_cone_overlap_predicates_against_independent_disk_minimization():
    rng = random.Random(102936)
    re, rs, rm, s = 10.0, 20.0, 2.0, 1000.0
    su, sp = (rs - re) / s, (rs + re) / s
    ku, kp = (su / math.sqrt(1 - su * su), sp / math.sqrt(1 - sp * sp))
    for _ in range(250):
        z, radial = rng.uniform(12.1, 1200), rng.uniform(0, 100)
        result = spherical_cone_shadow((s, 0, 0), (-z, radial, 0),
            earth_radius_km=re, sun_radius_km=rs, moon_radius_km=rm)
        for margin, t, k in ((result.umbral_margin, re / su - z, ku),
                             (result.penumbral_margin, z + re / sp, kp)):
            expected = _numeric_cone_distance(t, radial, k)
            assert (margin > 0) == (expected < rm)
            if expected > 1e-9:
                assert margin == pytest.approx(rm - expected, abs=1e-10)


@pytest.mark.parametrize("sun,moon,kwargs", [
    ((0, 0, 0), (-100, 0, 0), {}),
    ((1000, 0, 0), (float("nan"), 0, 0), {}),
    ((1000, 0, 0), (-100, 0, 0), {"earth_radius_km": -1}),
    ((1000, 0, 0), (-100, 0, 0), {"sun_radius_km": float("inf")}),
    ((1000, 0, 0), (-100, 0, 0), {"earth_radius_km": 10, "sun_radius_km": 20,
                                    "moon_radius_km": 2, "earth_radius_scale": 0}),
    ((1000, 0, 0), (-11, 0, 0), {"earth_radius_km": 10, "sun_radius_km": 20,
                                   "moon_radius_km": 2}),
])
def test_cone_rejects_invalid_or_unsupported_domain(sun, moon, kwargs):
    with pytest.raises(LunarShadowDomainError):
        spherical_cone_shadow(sun, moon, **kwargs)


def test_cone_explicit_earth_scaling_keeps_physical_gamma():
    kw = dict(earth_radius_km=10, sun_radius_km=20, moon_radius_km=2)
    a = spherical_cone_shadow((1000, 0, 0), (-300, 4, 0), **kw)
    b = spherical_cone_shadow((1000, 0, 0), (-300, 4, 0), earth_radius_scale=1.01, **kw)
    assert a.gamma == b.gamma == pytest.approx(0.4)
    assert a.umbral_margin != b.umbral_margin


def test_angular_rejects_antisolar_domain_violation():
    with pytest.raises(LunarShadowDomainError):
        danjon_angular_shadow((149597870.7, 0, 0), (384400, 0, 0))

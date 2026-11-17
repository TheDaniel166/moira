"""The phase route guards planetary light-time without changing normal values."""
from unittest.mock import patch
import math

import pytest

from moira import corrections, planets
from moira.constants import Body
from moira.coordinates import vec_add
from moira.julian import tt_to_tdb


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [Body.SUN, Body.MOON])
@pytest.mark.parametrize("tt", [1026285.7107341307, 2459891.9582497696, 2688456.25])
def test_guarded_planetary_light_time_preserves_legacy_values(planetary_reader, body, tt):
    reader = planetary_reader
    earth = planets._earth_barycentric(tt, reader)
    initial = planets._barycentric(body, tt, reader)
    tdb = tt_to_tdb(tt)
    pairs = planets._NPE_BODY_ROUTE_PAIRS[body]
    calls = []

    def emission(delay):
        calls.append(delay)
        value = (0.0, 0.0, 0.0)
        for center, target in pairs:
            value = vec_add(value, reader._position_tdb_offset(center, target, tdb, -delay))
        return value

    legacy = corrections._iterate_light_time(earth, initial, emission)
    assert calls
    guarded = planets._apply_planetary_light_time(body, tt, reader, earth, planets._barycentric)
    assert guarded == legacy


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [Body.SUN, Body.MOON])
@pytest.mark.parametrize("bad_norm", [float("nan"), float("inf"), -1.0, 1e300])
def test_phase_planetary_route_rejects_invalid_norm(planetary_reader, body, bad_norm):
    tt = 2459891.9582497696
    earth = planets._earth_barycentric(tt, planetary_reader)
    with patch.object(corrections, "vec_norm", return_value=bad_norm):
        with pytest.raises(ArithmeticError):
            planets._apply_planetary_light_time(body, tt, planetary_reader, earth, planets._barycentric)


@pytest.mark.requires_ephemeris
def test_other_planets_keep_the_unguarded_legacy_route(planetary_reader, monkeypatch):
    tt = 2459891.9582497696
    earth = planets._earth_barycentric(tt, planetary_reader)
    observed = []
    original = planets._iterate_light_time

    def record(*args, **kwargs):
        observed.append(kwargs.get("guard_norm", False))
        return original(*args, **kwargs)

    monkeypatch.setattr(planets, "_iterate_light_time", record)
    planets._apply_planetary_light_time(Body.MERCURY, tt, planetary_reader, earth, planets._barycentric)
    assert observed == [False]


@pytest.mark.parametrize("x", [0.0, math.ulp(0.0), 1e-200, math.nextafter(2.0**-500, 0.0)])
def test_lower_guard_retains_underflow_scale_behavior(monkeypatch, x):
    monkeypatch.setattr(corrections, "vec_norm", lambda xyz: 0.0)
    vector = (x, 0.0, 0.0)
    result = corrections._iterate_light_time((0.0, 0.0, 0.0), vector, lambda delay: vector, guard_norm=True)
    assert result == (vector, 0.0)


@pytest.mark.parametrize("x", [2.0**-500, math.nextafter(2.0**-500, math.inf), 1.0, 1e100])
def test_lower_guard_rejects_invalid_normal_scale_norm(monkeypatch, x):
    monkeypatch.setattr(corrections, "vec_norm", lambda xyz: 0.0)
    vector = (x, 0.0, 0.0)
    with pytest.raises(ArithmeticError, match="below"):
        corrections._iterate_light_time((0.0, 0.0, 0.0), vector, lambda delay: vector, guard_norm=True)


@pytest.mark.parametrize("x", [math.nextafter(2.0**-500, 0.0), 2.0**-500,
                               math.nextafter(2.0**-500, math.inf), 1.0, 1e100])
def test_lower_guard_preserves_actual_norm_at_and_above_threshold(x):
    vector = (x, 0.0, 0.0)
    actual = corrections._iterate_light_time((0.0, 0.0, 0.0), vector, lambda delay: vector, guard_norm=True)
    legacy = corrections._iterate_light_time((0.0, 0.0, 0.0), vector, lambda delay: vector)
    assert actual == legacy

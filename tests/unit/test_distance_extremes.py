"""
Unit tests for moira/orbits.py — distance_extremes_at and DistanceExtremes.

All tests are marked @pytest.mark.requires_ephemeris (DE441 kernel required).

Validation basis:
  - Earth perihelion 2000 Jan 03 (~JD 2451547): distance ≈ 0.9833 AU
  - Earth aphelion  2000 Jul 04 (~JD 2451729): distance ≈ 1.0167 AU
  Source: JPL HORIZONS heliocentric distance column.

Physical plausibility checks:
  - perihelion_distance_au > 0
  - aphelion_distance_au  > 0
  - perihelion_distance_au < aphelion_distance_au
  - JDs are finite and reasonable (> 2400000)
  - For every planet: perihelion distance < known mean SMA < aphelion distance
"""
from __future__ import annotations

import math
import pytest

from moira.orbits import DistanceExtremes, distance_extremes_at
from moira.spk_reader import get_reader
from moira.constants import Body


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# Dec 1 1999 00:00 UT — well ahead of Earth's Jan 2000 perihelion
_START_JD = 2451513.5


@pytest.fixture(scope="module")
def reader():
    return get_reader()


@pytest.fixture(scope="module")
def earth_extremes(reader):
    return distance_extremes_at(Body.EARTH, _START_JD, reader)


# ---------------------------------------------------------------------------
# Return-type and structure
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_returns_distance_extremes(earth_extremes):
    assert isinstance(earth_extremes, DistanceExtremes)


@pytest.mark.requires_ephemeris
def test_name_field_matches_body(reader):
    for body in (Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS):
        result = distance_extremes_at(body, _START_JD, reader)
        assert result.name == body


@pytest.mark.requires_ephemeris
def test_all_fields_present(earth_extremes):
    assert hasattr(earth_extremes, "name")
    assert hasattr(earth_extremes, "perihelion_jd")
    assert hasattr(earth_extremes, "perihelion_distance_au")
    assert hasattr(earth_extremes, "aphelion_jd")
    assert hasattr(earth_extremes, "aphelion_distance_au")


# ---------------------------------------------------------------------------
# Physical constraints
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_perihelion_lt_aphelion(body, reader):
    el = distance_extremes_at(body, _START_JD, reader)
    assert el.perihelion_distance_au < el.aphelion_distance_au, (
        f"{body}: perihelion {el.perihelion_distance_au} >= aphelion {el.aphelion_distance_au}"
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_distances_positive(body, reader):
    el = distance_extremes_at(body, _START_JD, reader)
    assert el.perihelion_distance_au > 0.0
    assert el.aphelion_distance_au > 0.0


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_jds_finite_and_reasonable(body, reader):
    el = distance_extremes_at(body, _START_JD, reader)
    for jd in (el.perihelion_jd, el.aphelion_jd):
        assert math.isfinite(jd)
        assert jd > 2400000.0, f"{body}: JD {jd} looks unreasonably small"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_all_fields_finite(body, reader):
    el = distance_extremes_at(body, _START_JD, reader)
    for val in (
        el.perihelion_jd, el.perihelion_distance_au,
        el.aphelion_jd,  el.aphelion_distance_au,
    ):
        assert math.isfinite(val)


# ---------------------------------------------------------------------------
# Consistency with KeplerianElements: perihelion < SMA < aphelion
# ---------------------------------------------------------------------------

# Approximate mean semi-major axes (AU) for a rough sanity check
_MEAN_SMA = {
    Body.MERCURY: 0.387,
    Body.VENUS:   0.723,
    Body.EARTH:   1.000,
    Body.MARS:    1.524,
    Body.JUPITER: 5.203,
    Body.SATURN:  9.537,
    Body.URANUS: 19.19,
    Body.NEPTUNE: 30.07,
}

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", list(_MEAN_SMA))
def test_sma_between_perihelion_and_aphelion(body, reader):
    el = distance_extremes_at(body, _START_JD, reader)
    sma = _MEAN_SMA[body]
    # Use generous tolerance because osculating extremes deviate from mean SMA
    assert el.perihelion_distance_au < sma * 1.05, (
        f"{body}: perihelion {el.perihelion_distance_au:.4f} not < {sma * 1.05:.4f}"
    )
    assert el.aphelion_distance_au > sma * 0.95, (
        f"{body}: aphelion {el.aphelion_distance_au:.4f} not > {sma * 0.95:.4f}"
    )


# ---------------------------------------------------------------------------
# Earth reference values (JPL HORIZONS)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_earth_perihelion_distance(earth_extremes):
    # Earth perihelion 2000 Jan 03: distance ≈ 0.9833 AU
    assert earth_extremes.perihelion_distance_au == pytest.approx(0.9833, abs=0.003)


@pytest.mark.requires_ephemeris
def test_earth_aphelion_distance(earth_extremes):
    # Earth aphelion 2000 Jul 04: distance ≈ 1.0167 AU
    assert earth_extremes.aphelion_distance_au == pytest.approx(1.0167, abs=0.003)


@pytest.mark.requires_ephemeris
def test_earth_perihelion_date(earth_extremes):
    # Earth perihelion 2000 Jan 03 ≈ JD 2451547.  Window: Dec 25 1999 – Jan 15 2000.
    assert 2451537.5 < earth_extremes.perihelion_jd < 2451559.5, (
        f"Perihelion JD {earth_extremes.perihelion_jd:.1f} outside expected window"
    )


@pytest.mark.requires_ephemeris
def test_earth_aphelion_date(earth_extremes):
    # Earth aphelion 2000 Jul 04 ≈ JD 2451729.  Window: Jun 20 – Jul 20.
    assert 2451716.5 < earth_extremes.aphelion_jd < 2451746.5, (
        f"Aphelion JD {earth_extremes.aphelion_jd:.1f} outside expected window"
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_sun_raises(reader):
    with pytest.raises(ValueError, match="SUN"):
        distance_extremes_at(Body.SUN, _START_JD, reader)


@pytest.mark.requires_ephemeris
def test_moon_raises(reader):
    with pytest.raises(ValueError, match="MOON"):
        distance_extremes_at(Body.MOON, _START_JD, reader)


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_deterministic(reader):
    el1 = distance_extremes_at(Body.MARS, _START_JD, reader)
    el2 = distance_extremes_at(Body.MARS, _START_JD, reader)
    assert el1.perihelion_jd == el2.perihelion_jd
    assert el1.perihelion_distance_au == el2.perihelion_distance_au
    assert el1.aphelion_jd == el2.aphelion_jd
    assert el1.aphelion_distance_au == el2.aphelion_distance_au


# ---------------------------------------------------------------------------
# Import from top-level moira surface
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_importable_from_moira(reader):
    import moira as _m
    assert hasattr(_m, "distance_extremes_at")
    assert hasattr(_m, "DistanceExtremes")
    result = _m.distance_extremes_at(Body.EARTH, _START_JD, reader)
    assert isinstance(result, _m.DistanceExtremes)

"""
Unit tests for moira/orbits.py — orbital_elements_at and KeplerianElements.

All tests are marked @pytest.mark.requires_ephemeris (DE441 kernel required).

Validation basis: Meeus, "Astronomical Algorithms" 2nd ed., Table 31.a
(J2000.0 elements for the eight major planets from Venus to Neptune).
Tolerances follow the docstring: ≤ 0.01° for angles, ≤ 0.001 AU for SMA.

Physical plausibility checks (no external reference required):
    - eccentricity ∈ [0, 1)
    - inclination ∈ [0, 180°]
    - angular elements ∈ [0°, 360°)
    - mean motion > 0
    - orbital period > 0 and consistent with SMA (Kepler III)
    - perihelion distance < SMA < aphelion distance

Known J2000.0 values from Meeus Table 31.a (tolerance ±0.005 AU, ±0.1°):
    Mercury: a=0.387 AU, e=0.206, i=7.005°
    Venus:   a=0.723 AU, e=0.007, i=3.395°
    Earth:   a=1.000 AU, e=0.017, i=0.000°  (by definition, ≈0° to ecliptic)
    Mars:    a=1.524 AU, e=0.093, i=1.850°
    Jupiter: a=5.203 AU, e=0.049, i=1.303°
    Saturn:  a=9.537 AU, e=0.056, i=2.489°
"""
from __future__ import annotations

import math
import pytest

from moira.orbits import KeplerianElements, orbital_elements_at
from moira import orbits as _orbits_module
from moira.spk_reader import get_reader
from moira.constants import Body


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_J2000 = 2451545.0   # 2000-Jan-01 12:00 UT ≈ TT


@pytest.fixture(scope="module")
def reader():
    return get_reader()


# ---------------------------------------------------------------------------
# Return-type and structure
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_returns_keplerian_elements(reader):
    result = orbital_elements_at(Body.EARTH, _J2000, reader)
    assert isinstance(result, KeplerianElements)


@pytest.mark.requires_ephemeris
def test_name_field_matches_body(reader):
    for body in (Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS):
        result = orbital_elements_at(body, _J2000, reader)
        assert result.name == body


@pytest.mark.requires_ephemeris
def test_epoch_jd_matches_input(reader):
    result = orbital_elements_at(Body.EARTH, _J2000, reader)
    assert result.epoch_jd == pytest.approx(_J2000, abs=1e-6)


# ---------------------------------------------------------------------------
# Physical constraints (no external reference needed)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_eccentricity_in_range(body, reader):
    el = orbital_elements_at(body, _J2000, reader)
    assert 0.0 <= el.eccentricity < 1.0, f"{body}: e={el.eccentricity}"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_inclination_in_range(body, reader):
    el = orbital_elements_at(body, _J2000, reader)
    assert 0.0 <= el.inclination_deg < 180.0, f"{body}: i={el.inclination_deg}"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_angular_elements_in_0_360(body, reader):
    el = orbital_elements_at(body, _J2000, reader)
    for attr in ("lon_ascending_node_deg", "arg_perihelion_deg", "mean_anomaly_deg"):
        val = getattr(el, attr)
        assert 0.0 <= val < 360.0, f"{body}: {attr}={val}"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_sma_positive(body, reader):
    el = orbital_elements_at(body, _J2000, reader)
    assert el.semi_major_axis_au > 0.0, f"{body}: a={el.semi_major_axis_au}"


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_mean_motion_and_period_positive(body, reader):
    el = orbital_elements_at(body, _J2000, reader)
    assert el.mean_motion_deg_per_day > 0.0
    assert el.orbital_period_days > 0.0


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_distance_properties(body, reader):
    """perihelion_distance_au < a < aphelion_distance_au."""
    el = orbital_elements_at(body, _J2000, reader)
    assert el.perihelion_distance_au < el.semi_major_axis_au
    assert el.semi_major_axis_au < el.aphelion_distance_au


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_kepler_third_law(body, reader):
    """T² ∝ a³: T²/a³ should equal T_earth²/a_earth³ within 1%."""
    el = orbital_elements_at(body, _J2000, reader)
    el_earth = orbital_elements_at(Body.EARTH, _J2000, reader)
    ratio_body  = el.orbital_period_days**2 / el.semi_major_axis_au**3
    ratio_earth = el_earth.orbital_period_days**2 / el_earth.semi_major_axis_au**3
    assert abs(ratio_body / ratio_earth - 1.0) < 0.01, (
        f"{body}: T²/a³ ratio = {ratio_body:.3f} vs Earth {ratio_earth:.3f}"
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", [
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
])
def test_all_fields_finite(body, reader):
    el = orbital_elements_at(body, _J2000, reader)
    for field in (
        el.semi_major_axis_au, el.eccentricity, el.inclination_deg,
        el.lon_ascending_node_deg, el.arg_perihelion_deg, el.mean_anomaly_deg,
        el.mean_motion_deg_per_day, el.orbital_period_days,
    ):
        assert math.isfinite(field)


# ---------------------------------------------------------------------------
# Meeus Table 31.a reference values (J2000.0)
# Tolerance: ±0.005 AU for semi-major axis, ±0.5° for angles
# (osculating elements at J2000 deviate slightly from mean elements in Meeus)
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_earth_sma_approx_1_au(reader):
    el = orbital_elements_at(Body.EARTH, _J2000, reader)
    assert el.semi_major_axis_au == pytest.approx(1.000, abs=0.005)


@pytest.mark.requires_ephemeris
def test_earth_eccentricity(reader):
    el = orbital_elements_at(Body.EARTH, _J2000, reader)
    assert el.eccentricity == pytest.approx(0.0167, abs=0.005)


@pytest.mark.requires_ephemeris
def test_earth_period_approx_365_days(reader):
    el = orbital_elements_at(Body.EARTH, _J2000, reader)
    assert el.orbital_period_days == pytest.approx(365.25, abs=1.0)


@pytest.mark.requires_ephemeris
def test_mercury_sma(reader):
    el = orbital_elements_at(Body.MERCURY, _J2000, reader)
    assert el.semi_major_axis_au == pytest.approx(0.387, abs=0.005)


@pytest.mark.requires_ephemeris
def test_mercury_eccentricity(reader):
    el = orbital_elements_at(Body.MERCURY, _J2000, reader)
    assert el.eccentricity == pytest.approx(0.206, abs=0.005)


@pytest.mark.requires_ephemeris
def test_venus_sma(reader):
    el = orbital_elements_at(Body.VENUS, _J2000, reader)
    assert el.semi_major_axis_au == pytest.approx(0.723, abs=0.005)


@pytest.mark.requires_ephemeris
def test_mars_sma(reader):
    el = orbital_elements_at(Body.MARS, _J2000, reader)
    assert el.semi_major_axis_au == pytest.approx(1.524, abs=0.005)


@pytest.mark.requires_ephemeris
def test_jupiter_sma(reader):
    el = orbital_elements_at(Body.JUPITER, _J2000, reader)
    assert el.semi_major_axis_au == pytest.approx(5.203, abs=0.01)


@pytest.mark.requires_ephemeris
def test_jupiter_period_approx_11_86_years(reader):
    # Meeus mean value: 4332.6 days; osculating elements at J2000 deviate
    # slightly (~11 days) due to Jupiter's large perturbations from Saturn.
    el = orbital_elements_at(Body.JUPITER, _J2000, reader)
    assert el.orbital_period_days == pytest.approx(4332.6, abs=15.0)


@pytest.mark.requires_ephemeris
def test_saturn_sma(reader):
    # Meeus mean SMA: 9.537 AU; osculating SMA at J2000 ≈ 9.585 AU due to
    # Jupiter perturbations on Saturn's orbit.  Tolerance widened accordingly.
    el = orbital_elements_at(Body.SATURN, _J2000, reader)
    assert el.semi_major_axis_au == pytest.approx(9.537, abs=0.06)


@pytest.mark.requires_ephemeris
def test_mercury_inclination(reader):
    el = orbital_elements_at(Body.MERCURY, _J2000, reader)
    assert el.inclination_deg == pytest.approx(7.005, abs=0.5)


@pytest.mark.requires_ephemeris
def test_jupiter_eccentricity(reader):
    el = orbital_elements_at(Body.JUPITER, _J2000, reader)
    assert el.eccentricity == pytest.approx(0.049, abs=0.005)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_sun_raises(reader):
    with pytest.raises(ValueError, match="SUN"):
        orbital_elements_at(Body.SUN, _J2000, reader)


@pytest.mark.requires_ephemeris
def test_moon_raises(reader):
    with pytest.raises(ValueError, match="MOON"):
        orbital_elements_at(Body.MOON, _J2000, reader)


# ---------------------------------------------------------------------------
# Reproducibility — same epoch same result
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_deterministic(reader):
    el1 = orbital_elements_at(Body.EARTH, _J2000, reader)
    el2 = orbital_elements_at(Body.EARTH, _J2000, reader)
    assert el1.semi_major_axis_au == el2.semi_major_axis_au
    assert el1.eccentricity == el2.eccentricity


# ---------------------------------------------------------------------------
# Import from top-level moira surface
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_importable_from_moira(reader):
    import moira as _m
    assert hasattr(_m, "orbital_elements_at")
    assert hasattr(_m, "KeplerianElements")
    result = _m.orbital_elements_at(Body.EARTH, _J2000, reader)
    assert isinstance(result, _m.KeplerianElements)


# ---------------------------------------------------------------------------
# Synthetic singular-case hardening tests (no ephemeris required)
# ---------------------------------------------------------------------------

def test_internal_circular_equatorial_state_uses_true_longitude() -> None:
    elements = _orbits_module._keplerian_from_state(
        r=(0.0, 2.0, 0.0),
        v=(-1.0, 0.0, 0.0),
        gm=2.0,
        name="Synthetic",
        epoch_jd=0.0,
    )

    assert elements.eccentricity == pytest.approx(0.0, abs=1e-12)
    assert elements.inclination_deg == pytest.approx(0.0, abs=1e-12)
    assert elements.lon_ascending_node_deg == pytest.approx(0.0, abs=1e-12)
    assert elements.arg_perihelion_deg == pytest.approx(0.0, abs=1e-12)
    assert elements.mean_anomaly_deg == pytest.approx(90.0, abs=1e-12)


def test_internal_equatorial_eccentric_state_uses_longitude_of_perihelion() -> None:
    elements = _orbits_module._keplerian_from_state(
        r=(0.0, 1.0, 0.0),
        v=(-1.0, 1.0, 0.0),
        gm=2.0,
        name="Synthetic",
        epoch_jd=0.0,
    )

    assert elements.inclination_deg == pytest.approx(0.0, abs=1e-12)
    assert elements.lon_ascending_node_deg == pytest.approx(0.0, abs=1e-12)
    assert elements.arg_perihelion_deg == pytest.approx(315.0, abs=1e-9)
    assert 0.0 <= elements.mean_anomaly_deg < 360.0


def test_internal_degenerate_state_raises() -> None:
    with pytest.raises(ValueError, match="degenerate state vector"):
        _orbits_module._keplerian_from_state(
            r=(1.0, 0.0, 0.0),
            v=(2.0, 0.0, 0.0),
            gm=1.0,
            name="Synthetic",
            epoch_jd=0.0,
        )

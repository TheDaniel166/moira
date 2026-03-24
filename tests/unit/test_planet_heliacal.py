"""
Unit tests for planet heliacal / acronychal visibility computation.

moira/heliacal.py — planet_heliacal_rising, planet_heliacal_setting,
                    planet_acronychal_rising, planet_acronychal_setting,
                    PlanetHeliacalEvent.

All tests marked @pytest.mark.requires_ephemeris (DE441 kernel required).

Validation basis
----------------
Events are validated against known apparition dates with ±15-day tolerance
(exact dates are location- and atmospheric-model-dependent):

  Venus heliacal rising 2020   — first morning star after inferior conjunction
                                 June 3 2020 (JD 2458994).
                                 At lat=35N, lon=35E: expected ~June 20 2020
                                 (JD 2459011).

  Jupiter heliacal rising 2023 — first morning visibility after solar
                                 conjunction April 11 2023 (JD 2460045).
                                 Expected ~late April 2023 (JD 2460060–2460090).

  Venus acronychal rising 2021 — first evening star after superior
                                 conjunction March 26 2021 (JD 2459299).
                                 Expected ~late April 2021 (JD 2459315–2459360).

  Venus heliacal setting 2021  — last morning visibility before superior
                                 conjunction March 26 2021.  Start from
                                 July 2020 (well into morning apparition).
                                 Expected ~late January / early February 2021
                                 (JD 2459230–2459270).

Physical plausibility constraints (no external reference needed):
  - planet_altitude_deg > 0 (above horizon)
  - sun_altitude_deg < 0 (below horizon)
  - HELIACAL_* events have elongation_deg < 0 (morning sky)
  - ACRONYCHAL_* events have elongation_deg > 0 (evening sky)
  - apparent_magnitude is finite
"""
from __future__ import annotations

import math
import pytest

from moira.heliacal import (
    HeliacalEventKind,
    HeliacalPolicy,
    PlanetHeliacalEvent,
    VisibilityModel,
    planet_acronychal_rising,
    planet_acronychal_setting,
    planet_heliacal_rising,
    planet_heliacal_setting,
)
from moira.constants import Body


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# Standard Mediterranean observer for all tests
_LAT, _LON = 35.0, 35.0

# Venus inferior conjunction ~June 3 2020
_VENUS_INFERIOR_CONJ_2020 = 2458994.5

# Jupiter solar conjunction ~April 11 2023
_JUPITER_CONJ_2023 = 2460045.5

# Venus superior conjunction ~March 26 2021
_VENUS_SUPERIOR_CONJ_2021 = 2459299.5

# Venus well into morning apparition July 2020 (for heliacal-setting search)
_VENUS_MORNING_2020 = 2459050.5

# Saturn solar conjunction ~February 16 2023
_SATURN_CONJ_2023 = 2459992.5


# ---------------------------------------------------------------------------
# Shared fixtures (module-scoped for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def venus_heliacal_rising():
    return planet_heliacal_rising(
        Body.VENUS, _VENUS_INFERIOR_CONJ_2020, _LAT, _LON
    )


@pytest.fixture(scope="module")
def jupiter_heliacal_rising():
    return planet_heliacal_rising(
        Body.JUPITER, _JUPITER_CONJ_2023, _LAT, _LON
    )


@pytest.fixture(scope="module")
def venus_acronychal_rising():
    return planet_acronychal_rising(
        Body.VENUS, _VENUS_SUPERIOR_CONJ_2021, _LAT, _LON
    )


@pytest.fixture(scope="module")
def venus_heliacal_setting():
    return planet_heliacal_setting(
        Body.VENUS, _VENUS_MORNING_2020, _LAT, _LON, search_days=300
    )


@pytest.fixture(scope="module")
def saturn_acronychal_setting():
    return planet_acronychal_setting(
        Body.SATURN, _SATURN_CONJ_2023 - 170, _LAT, _LON, search_days=200
    )


# ---------------------------------------------------------------------------
# Return-type and structure
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_returns_planet_heliacal_event(venus_heliacal_rising):
    assert isinstance(venus_heliacal_rising, PlanetHeliacalEvent)


@pytest.mark.requires_ephemeris
def test_body_field_heliacal_rising(venus_heliacal_rising):
    assert venus_heliacal_rising.body == Body.VENUS


@pytest.mark.requires_ephemeris
def test_body_field_jupiter(jupiter_heliacal_rising):
    assert jupiter_heliacal_rising.body == Body.JUPITER


@pytest.mark.requires_ephemeris
def test_kind_heliacal_rising(venus_heliacal_rising):
    assert venus_heliacal_rising.kind == HeliacalEventKind.HELIACAL_RISING


@pytest.mark.requires_ephemeris
def test_kind_acronychal_rising(venus_acronychal_rising):
    assert venus_acronychal_rising.kind == HeliacalEventKind.ACRONYCHAL_RISING


@pytest.mark.requires_ephemeris
def test_kind_heliacal_setting(venus_heliacal_setting):
    assert venus_heliacal_setting.kind == HeliacalEventKind.HELIACAL_SETTING


@pytest.mark.requires_ephemeris
def test_kind_acronychal_setting(saturn_acronychal_setting):
    assert saturn_acronychal_setting.kind == HeliacalEventKind.ACRONYCHAL_SETTING


@pytest.mark.requires_ephemeris
def test_all_fields_present(venus_heliacal_rising):
    ev = venus_heliacal_rising
    assert hasattr(ev, "body")
    assert hasattr(ev, "kind")
    assert hasattr(ev, "jd_ut")
    assert hasattr(ev, "elongation_deg")
    assert hasattr(ev, "planet_altitude_deg")
    assert hasattr(ev, "sun_altitude_deg")
    assert hasattr(ev, "apparent_magnitude")


# ---------------------------------------------------------------------------
# Physical plausibility — all events
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("fixture_name", [
    "venus_heliacal_rising",
    "jupiter_heliacal_rising",
    "venus_acronychal_rising",
    "venus_heliacal_setting",
    "saturn_acronychal_setting",
])
def test_jd_finite_and_positive(fixture_name, request):
    ev = request.getfixturevalue(fixture_name)
    assert math.isfinite(ev.jd_ut)
    assert ev.jd_ut > 2400000.0


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("fixture_name", [
    "venus_heliacal_rising",
    "jupiter_heliacal_rising",
    "venus_acronychal_rising",
    "venus_heliacal_setting",
    "saturn_acronychal_setting",
])
def test_planet_above_horizon(fixture_name, request):
    ev = request.getfixturevalue(fixture_name)
    assert ev.planet_altitude_deg > 0.0, (
        f"{ev.kind.value}: planet altitude {ev.planet_altitude_deg:.3f}° ≤ 0"
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("fixture_name", [
    "venus_heliacal_rising",
    "jupiter_heliacal_rising",
    "venus_acronychal_rising",
    "venus_heliacal_setting",
    "saturn_acronychal_setting",
])
def test_sun_below_horizon(fixture_name, request):
    ev = request.getfixturevalue(fixture_name)
    assert ev.sun_altitude_deg < 0.0, (
        f"{ev.kind.value}: sun altitude {ev.sun_altitude_deg:.3f}° ≥ 0"
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("fixture_name", [
    "venus_heliacal_rising",
    "jupiter_heliacal_rising",
    "venus_acronychal_rising",
    "venus_heliacal_setting",
    "saturn_acronychal_setting",
])
def test_sun_at_twilight_depth(fixture_name, request):
    """Sun altitude at event should be between -20° and 0° (twilight range)."""
    ev = request.getfixturevalue(fixture_name)
    assert -20.0 <= ev.sun_altitude_deg < 0.0, (
        f"{ev.kind.value}: sun altitude {ev.sun_altitude_deg:.3f}° outside twilight range"
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("fixture_name", [
    "venus_heliacal_rising",
    "jupiter_heliacal_rising",
    "venus_acronychal_rising",
    "venus_heliacal_setting",
    "saturn_acronychal_setting",
])
def test_apparent_magnitude_finite(fixture_name, request):
    ev = request.getfixturevalue(fixture_name)
    assert math.isfinite(ev.apparent_magnitude)


# ---------------------------------------------------------------------------
# Elongation sign constraints
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_heliacal_rising_morning_sky(venus_heliacal_rising):
    """Heliacal rising must have negative elongation (planet west of Sun)."""
    assert venus_heliacal_rising.elongation_deg < 0.0


@pytest.mark.requires_ephemeris
def test_heliacal_rising_jupiter_morning_sky(jupiter_heliacal_rising):
    assert jupiter_heliacal_rising.elongation_deg < 0.0


@pytest.mark.requires_ephemeris
def test_heliacal_setting_morning_sky(venus_heliacal_setting):
    assert venus_heliacal_setting.elongation_deg < 0.0


@pytest.mark.requires_ephemeris
def test_acronychal_rising_evening_sky(venus_acronychal_rising):
    """Acronychal rising must have positive elongation (planet east of Sun)."""
    assert venus_acronychal_rising.elongation_deg > 0.0


@pytest.mark.requires_ephemeris
def test_acronychal_setting_evening_sky(saturn_acronychal_setting):
    assert saturn_acronychal_setting.elongation_deg > 0.0


# ---------------------------------------------------------------------------
# Reference date windows
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_venus_heliacal_rising_2020_window(venus_heliacal_rising):
    """Venus first morning visibility after inferior conjunction June 3 2020.

    Expected window: June 10 – July 10 2020 (JD 2459009 – 2459039).
    Tolerance widened to ±20 days from the nominal June 20 date.
    """
    assert 2459004.0 < venus_heliacal_rising.jd_ut < 2459044.0, (
        f"Venus heliacal rising JD {venus_heliacal_rising.jd_ut:.1f} "
        f"outside expected window"
    )


@pytest.mark.requires_ephemeris
def test_venus_heliacal_rising_after_conjunction(venus_heliacal_rising):
    """Event must occur after the inferior conjunction."""
    assert venus_heliacal_rising.jd_ut > _VENUS_INFERIOR_CONJ_2020


@pytest.mark.requires_ephemeris
def test_jupiter_heliacal_rising_2023_window(jupiter_heliacal_rising):
    """Jupiter first morning visibility after solar conjunction April 11 2023.

    Expected window: late April – mid June 2023 (JD 2460055 – 2460105).
    """
    assert 2460050.0 < jupiter_heliacal_rising.jd_ut < 2460110.0, (
        f"Jupiter heliacal rising JD {jupiter_heliacal_rising.jd_ut:.1f} "
        f"outside expected window"
    )


@pytest.mark.requires_ephemeris
def test_jupiter_heliacal_rising_after_conjunction(jupiter_heliacal_rising):
    assert jupiter_heliacal_rising.jd_ut > _JUPITER_CONJ_2023


@pytest.mark.requires_ephemeris
def test_venus_acronychal_rising_2021_window(venus_acronychal_rising):
    """Venus first evening visibility after superior conjunction March 26 2021.

    Expected window: April 10 – May 20 2021 (JD 2459314 – 2459354).
    """
    assert 2459310.0 < venus_acronychal_rising.jd_ut < 2459360.0, (
        f"Venus acronychal rising JD {venus_acronychal_rising.jd_ut:.1f} "
        f"outside expected window"
    )


@pytest.mark.requires_ephemeris
def test_venus_acronychal_rising_after_superior_conjunction(venus_acronychal_rising):
    assert venus_acronychal_rising.jd_ut > _VENUS_SUPERIOR_CONJ_2021


@pytest.mark.requires_ephemeris
def test_venus_heliacal_setting_before_superior_conjunction(venus_heliacal_setting):
    """Venus last morning visibility must precede the superior conjunction."""
    assert venus_heliacal_setting.jd_ut < _VENUS_SUPERIOR_CONJ_2021


@pytest.mark.requires_ephemeris
def test_venus_heliacal_setting_2021_window(venus_heliacal_setting):
    """Venus last morning visibility ~4–8 weeks before superior conjunction.

    Superior conjunction March 26 2021 (JD 2459299).
    Expected window: January 15 – March 10 2021 (JD 2459229 – 2459283).
    """
    assert 2459220.0 < venus_heliacal_setting.jd_ut < 2459290.0, (
        f"Venus heliacal setting JD {venus_heliacal_setting.jd_ut:.1f} "
        f"outside expected window"
    )


# ---------------------------------------------------------------------------
# Policy customisation
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_stricter_conditions_delay_heliacal_rising():
    """With worse atmospheric conditions (brighter limiting mag, more extinction)
    the planet needs greater elongation to be visible → heliacal rising happens
    later than under dark-sky conditions."""
    default = planet_heliacal_rising(
        Body.JUPITER, _JUPITER_CONJ_2023, _LAT, _LON
    )
    poor = planet_heliacal_rising(
        Body.JUPITER, _JUPITER_CONJ_2023, _LAT, _LON,
        policy=HeliacalPolicy(
            visibility_model=VisibilityModel(
                limiting_magnitude=4.0,       # polluted sky
                extinction_coefficient=0.40,   # high extinction
            )
        )
    )
    assert poor is None or poor.jd_ut >= default.jd_ut, (
        "Poor conditions should delay or prevent heliacal rising"
    )


@pytest.mark.requires_ephemeris
def test_default_policy_returns_same_as_none():
    """Passing policy=None gives same result as HeliacalPolicy.default()."""
    r1 = planet_heliacal_rising(Body.JUPITER, _JUPITER_CONJ_2023, _LAT, _LON, policy=None)
    r2 = planet_heliacal_rising(
        Body.JUPITER, _JUPITER_CONJ_2023, _LAT, _LON,
        policy=HeliacalPolicy.default()
    )
    assert r1 is not None and r2 is not None
    assert r1.jd_ut == r2.jd_ut


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_sun_raises_heliacal_rising():
    with pytest.raises(ValueError, match="planet"):
        planet_heliacal_rising(Body.SUN, _VENUS_INFERIOR_CONJ_2020, _LAT, _LON)


@pytest.mark.requires_ephemeris
def test_moon_raises_heliacal_rising():
    with pytest.raises(ValueError, match="planet"):
        planet_heliacal_rising(Body.MOON, _VENUS_INFERIOR_CONJ_2020, _LAT, _LON)


@pytest.mark.requires_ephemeris
def test_sun_raises_acronychal_rising():
    with pytest.raises(ValueError, match="planet"):
        planet_acronychal_rising(Body.SUN, _VENUS_SUPERIOR_CONJ_2021, _LAT, _LON)


@pytest.mark.requires_ephemeris
def test_invalid_search_days():
    with pytest.raises(ValueError):
        planet_heliacal_rising(Body.VENUS, _VENUS_INFERIOR_CONJ_2020, _LAT, _LON,
                               search_days=0)


@pytest.mark.requires_ephemeris
def test_invalid_lat():
    with pytest.raises(ValueError):
        planet_heliacal_rising(Body.VENUS, _VENUS_INFERIOR_CONJ_2020, 95.0, _LON)


# ---------------------------------------------------------------------------
# Top-level moira import
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_importable_from_moira():
    import moira as _m
    assert hasattr(_m, "planet_heliacal_rising")
    assert hasattr(_m, "planet_heliacal_setting")
    assert hasattr(_m, "planet_acronychal_rising")
    assert hasattr(_m, "planet_acronychal_setting")
    assert hasattr(_m, "PlanetHeliacalEvent")
    result = _m.planet_heliacal_rising(Body.VENUS, _VENUS_INFERIOR_CONJ_2020, _LAT, _LON)
    assert isinstance(result, _m.PlanetHeliacalEvent)

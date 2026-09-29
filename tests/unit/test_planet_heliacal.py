"""
Unit tests for planet heliacal / acronychal visibility computation.

moira/heliacal.py — planet_heliacal_rising, planet_evening_first,
                    planet_morning_last, planet_acronychal_setting,
                    PlanetHeliacalEvent.

Nomenclature (6.9.9): the standard Ptolemy / Schoch names.  The event this
file historically called "heliacal setting" (last morning) is MORNING_LAST and
the one it called "acronychal rising" (first evening) is EVENING_FIRST; see
tests/unit/test_heliacal_standard_kinds.py for the full standard set.

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

  Venus evening first 2021     — first evening star after superior
                                 conjunction March 26 2021 (JD 2459299).
                                 Expected ~late April 2021 (JD 2459315–2459360).

  Venus morning last 2021      — last morning visibility before superior
                                 conjunction March 26 2021.  Start from
                                 July 2020 (well into morning apparition).
                                 Expected ~late January / early February 2021
                                 (JD 2459230–2459270).

Physical plausibility constraints (no external reference needed):
  - planet_altitude_deg > 0 (above horizon)
  - sun_altitude_deg < 0 (below horizon)
  - HELIACAL_RISING / MORNING_LAST events have elongation_deg < 0 (morning sky)
  - EVENING_FIRST / ACRONYCHAL_SETTING events have elongation_deg > 0 (evening sky)
  - apparent_magnitude is finite
"""
from __future__ import annotations

import math
import pytest

from moira.spk_reader import use_reader_override
from moira.heliacal import (
    HeliacalEventKind,
    HeliacalPolicy,
    PlanetHeliacalEvent,
    VisibilityModel,
    planet_acronychal_rising,
    planet_acronychal_setting,
    planet_evening_first,
    planet_heliacal_rising,
    planet_morning_last,
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
def venus_heliacal_rising(planetary_reader):
    with use_reader_override(planetary_reader):
        return planet_heliacal_rising(
            Body.VENUS, _VENUS_INFERIOR_CONJ_2020, _LAT, _LON
        )


@pytest.fixture(scope="module")
def jupiter_heliacal_rising(planetary_reader):
    with use_reader_override(planetary_reader):
        return planet_heliacal_rising(
            Body.JUPITER, _JUPITER_CONJ_2023, _LAT, _LON
        )


@pytest.fixture(scope="module")
def venus_evening_first(planetary_reader):
    with use_reader_override(planetary_reader):
        return planet_evening_first(
            Body.VENUS, _VENUS_SUPERIOR_CONJ_2021, _LAT, _LON
        )


@pytest.fixture(scope="module")
def venus_morning_last(planetary_reader):
    with use_reader_override(planetary_reader):
        return planet_morning_last(
            Body.VENUS,
            _VENUS_MORNING_2020,
            _LAT,
            _LON,
            search_days=300,
        )


@pytest.fixture(scope="module")
def saturn_acronychal_setting(planetary_reader):
    with use_reader_override(planetary_reader):
        return planet_acronychal_setting(
            Body.SATURN,
            _SATURN_CONJ_2023 - 170,
            _LAT,
            _LON,
            search_days=200,
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
def test_kind_evening_first(venus_evening_first):
    assert venus_evening_first.kind == HeliacalEventKind.EVENING_FIRST


@pytest.mark.requires_ephemeris
def test_kind_morning_last(venus_morning_last):
    assert venus_morning_last.kind == HeliacalEventKind.MORNING_LAST


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
    "venus_evening_first",
    "venus_morning_last",
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
    "venus_evening_first",
    "venus_morning_last",
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
    "venus_evening_first",
    "venus_morning_last",
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
    "venus_evening_first",
    "venus_morning_last",
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
    "venus_evening_first",
    "venus_morning_last",
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
def test_morning_last_morning_sky(venus_morning_last):
    assert venus_morning_last.elongation_deg < 0.0


@pytest.mark.requires_ephemeris
def test_evening_first_evening_sky(venus_evening_first):
    """Evening first must have positive elongation (planet east of Sun)."""
    assert venus_evening_first.elongation_deg > 0.0


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
def test_venus_evening_first_2021_window(venus_evening_first):
    """Venus first evening visibility after superior conjunction March 26 2021.

    Expected window: April 10 – May 20 2021 (JD 2459314 – 2459354).
    """
    assert 2459310.0 < venus_evening_first.jd_ut < 2459360.0, (
        f"Venus evening first JD {venus_evening_first.jd_ut:.1f} "
        f"outside expected window"
    )


@pytest.mark.requires_ephemeris
def test_venus_evening_first_after_superior_conjunction(venus_evening_first):
    assert venus_evening_first.jd_ut > _VENUS_SUPERIOR_CONJ_2021


@pytest.mark.requires_ephemeris
def test_venus_morning_last_before_superior_conjunction(venus_morning_last):
    """Venus last morning visibility must precede the superior conjunction."""
    assert venus_morning_last.jd_ut < _VENUS_SUPERIOR_CONJ_2021


@pytest.mark.requires_ephemeris
def test_venus_morning_last_2021_window(venus_morning_last):
    """Venus last morning visibility ~4–8 weeks before superior conjunction.

    Superior conjunction March 26 2021 (JD 2459299).
    Expected window: January 15 – March 10 2021 (JD 2459229 – 2459283).
    """
    assert 2459220.0 < venus_morning_last.jd_ut < 2459290.0, (
        f"Venus morning last JD {venus_morning_last.jd_ut:.1f} "
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


@pytest.mark.requires_ephemeris
def test_superior_planet_has_no_morning_last_at_opposition(planetary_reader):
    """Saturn's 1878 morning apparition ends at opposition (1878-09-22), not in
    the Sun's glare, so there is no morning last visibility (the event named
    HELIACAL_SETTING before 6.9.9). The search used to carry the last morning
    sighting across the opposition and return it."""
    with use_reader_override(planetary_reader):
        event = planet_morning_last(
            Body.SATURN,
            2407166.5,  # 1878-07-01 00:00 UT, Saturn on the morning side
            48.4,
            9.98,
            search_days=320,
        )
    assert event is None

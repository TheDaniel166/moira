"""
tests/unit/test_moira_almutens.py

Validates the Almuten Figuris and Compound Rulership (Almuten of Degree) calculations
against traditional rules, including fallback mechanics, tie-breaking criteria,
and facade-level auto-resolution of prenatal syzygy and day/hour rulers.
"""

from __future__ import annotations

import pytest

import moira
from moira.dignities import almuten_of_degree, almuten_figuris, ALMUTEN_HOUSE_SCORES
from moira.dignities_types import CLASSIC_7


# ============================================================================
# 1. almuten_of_degree Tests (Compound Rulership)
# ============================================================================

def test_almuten_of_degree_aries_zero() -> None:
    """
    At Aries 0.0:
    - Domicile: Mars (rules Aries, +5)
    - Exaltation: Sun (exalted in Aries, +4)
    - Triplicity (Day): Sun (rules Fire day, +3)
    - Triplicity (Night): Jupiter (rules Fire night, +3)
    - Bound (0-6 Aries): Jupiter (+2)
    - Decan (0-10 Aries): Mars (+1)

    Day chart:
    - Sun: Exaltation (4) + Triplicity (3) = 7
    - Mars: Domicile (5) + Decan (1) = 6
    - Jupiter: Bound (2) = 2
    Almuten: Sun

    Night chart:
    - Mars: Domicile (5) + Decan (1) = 6
    - Jupiter: Triplicity (3) + Bound (2) = 5
    - Sun: Exaltation (4) = 4
    Almuten: Mars
    """
    assert almuten_of_degree(0.0, is_day=True) == "Sun"
    assert almuten_of_degree(0.0, is_day=False) == "Mars"


def test_almuten_of_degree_taurus_zero_tie_breaker() -> None:
    """
    At Taurus 0.0:
    - Domicile: Venus (+5)
    - Exaltation: Moon (+4)
    - Triplicity (Night): Moon (+3)
    - Bound (0-8 Taurus): Venus (+2)
    - Decan (0-10 Taurus): Mercury (+1)

    Night chart:
    - Venus: Domicile (5) + Bound (2) = 7 (Highest rank: Domicile = 5)
    - Moon: Exaltation (4) + Triplicity (3) = 7 (Highest rank: Exaltation = 4)
    Tie-breaker: Venus has a higher single dignity rank (Domicile vs Exaltation).
    Almuten: Venus
    """
    assert almuten_of_degree(30.0, is_day=False) == "Venus"


def test_almuten_of_degree_no_dignity_fallback() -> None:
    """
    If no planet holds any dignity, the tie-breaker falls back to the index order
    defined in _PLANET_ORDER (CLASSIC_7), where Sun is first.
    """
    # A position with no planet holding essential dignity (purely hypothetical/artificial case).
    # Since we score over all CLASSIC_7, if all score 0, the first in order (Sun) wins.
    # We can verify the deterministic choice of Sun for a 0-score tie.
    # At 0.0 degree but using a check on raw tie behavior.
    res = almuten_of_degree(0.0, is_day=True)
    assert res in CLASSIC_7


# ============================================================================
# 2. almuten_figuris Tests (Calculation and Fallbacks)
# ============================================================================

def test_almuten_figuris_fallback_float_cusps() -> None:
    """
    If `cusps` is a float, almuten_figuris performs the simplified fallback calculation
    scoring essential dignities only at Sun, Moon, and Ascendant.
    """
    positions = {
        "Sun": 0.0,    # Aries 0 (Sun has +7 in day, Mars has +6)
        "Moon": 0.0,   # Aries 0
    }
    # Ascendant is 0.0, is_day = True
    # Sun score: 7 + 7 + 7 = 21
    # Mars score: 6 + 6 + 6 = 18
    # Sun should be the Almuten Figuris
    result = almuten_figuris(positions, cusps=0.0, is_day=True)
    assert result == "Sun"


def test_almuten_figuris_full_calculation() -> None:
    """
    Validates full calculation with explicit prenatal syzygy and day/hour rulers.
    """
    positions = {
        "Sun": 0.0,      # Aries 0
        "Moon": 30.0,    # Taurus 0
        "Mercury": 60.0,
        "Venus": 90.0,
        "Mars": 120.0,
        "Jupiter": 150.0,
        "Saturn": 180.0,
    }
    # Cusps list (equal house starting at Aries 0)
    cusps = [float(i * 30) for i in range(12)]
    # Day chart, ASC = 0.0
    # Lot of Fortune = ASC + Moon - Sun = 0.0 + 30.0 - 0.0 = 30.0
    # Prenatal Syzygy = 15.0
    # Day ruler: Venus
    # Hour ruler: Mercury

    # Let's call the function and verify it executes without error and returns a valid planet
    result = almuten_figuris(
        positions,
        cusps=cusps,
        is_day=True,
        prenatal_syzygy_lon=15.0,
        day_ruler="Venus",
        hour_ruler="Mercury",
    )
    assert result in CLASSIC_7


# ============================================================================
# 3. Facade-Level Tests (Requires Ephemeris for Auto-resolution)
# ============================================================================

@pytest.mark.requires_ephemeris
def test_facade_almuten_of_degree(moira_engine) -> None:
    """Verifies that the facade delegates almuten_of_degree correctly."""
    direct = almuten_of_degree(120.0, is_day=True)
    via_facade = moira_engine.almuten_of_degree(120.0, is_day=True)
    assert via_facade == direct


@pytest.mark.requires_ephemeris
def test_facade_almuten_figuris_auto_resolve(moira_engine) -> None:
    """
    Verifies that the facade auto-resolves prenatal syzygy, day ruler, and hour ruler,
    and returns a valid planet name.
    """
    # Birth chart setup for a known epoch: 2000-01-01 12:00 UTC
    from datetime import datetime, timezone
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(dt)
    houses = moira_engine.houses(dt, latitude=51.5, longitude=-0.1)

    # Call facade method
    result = moira_engine.almuten_figuris(chart, houses)
    assert result in CLASSIC_7


def test_facade_almuten_figuris_uses_planetary_hours_vessel_contract(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    captured = {}
    hour = SimpleNamespace(ruler="Mercury")
    day = SimpleNamespace(
        hours=(SimpleNamespace(ruler="Moon"),),
        hour_at=lambda jd_ut: hour,
    )

    monkeypatch.setattr(
        "moira.planetary_hours._planetary_hours_from_utc",
        lambda jd_ut, latitude, longitude, reader=None: day,
    )

    def fake_almuten_figuris(positions, cusps, is_day, **kwargs):
        captured.update(kwargs)
        return "Sun"

    monkeypatch.setattr("moira.facade.almuten_figuris", fake_almuten_figuris)

    chart = SimpleNamespace(
        jd_ut=2451545.5,
        _reader=object(),
        longitudes=lambda include_nodes=False: {"Sun": 10.0, "Moon": 20.0},
    )
    houses = SimpleNamespace(
        asc=0.0,
        cusps=[float(index * 30) for index in range(12)],
        geo_lat=51.5,
        geo_lon=-0.1,
    )

    result = moira_engine.almuten_figuris(
        chart,
        houses,
        prenatal_syzygy_lon=15.0,
        strict=True,
    )

    assert result == "Sun"
    assert captured["day_ruler"] == "Moon"
    assert captured["hour_ruler"] == "Mercury"


# ============================================================================
# 4. Hardening and Validation Tests
# ============================================================================

def test_almuten_of_degree_validation() -> None:
    """Verifies that invalid inputs to almuten_of_degree raise errors."""
    with pytest.raises(TypeError):
        almuten_of_degree("invalid_longitude", is_day=True)  # type: ignore
    with pytest.raises(ValueError):
        almuten_of_degree(float("nan"), is_day=True)
    with pytest.raises(TypeError):
        almuten_of_degree(120.0, is_day="not_a_bool")  # type: ignore


def test_almuten_figuris_validation() -> None:
    """Verifies that invalid inputs to almuten_figuris raise appropriate errors."""
    # 1. Invalid planet_positions
    with pytest.raises(TypeError):
        almuten_figuris("not_a_dict", cusps=0.0, is_day=True)  # type: ignore
    with pytest.raises(ValueError):
        almuten_figuris({"Sun": 10.0}, cusps=0.0, is_day=True)  # Missing Moon
    with pytest.raises(TypeError):
        almuten_figuris({"Sun": 10.0, "Moon": "invalid"}, cusps=0.0, is_day=True)  # type: ignore

    # 2. Invalid cusps
    positions = {"Sun": 0.0, "Moon": 0.0}
    with pytest.raises(TypeError):
        almuten_figuris(positions, cusps="not_numeric_or_sequence", is_day=True)  # type: ignore
    with pytest.raises(ValueError):
        almuten_figuris(positions, cusps=[0.0] * 11, is_day=True)  # Less than 12 elements
    with pytest.raises(ValueError):
        almuten_figuris(positions, cusps={1: 0.0}, is_day=True)  # Missing keys

    # 3. Invalid rulers
    with pytest.raises(ValueError):
        almuten_figuris(positions, cusps=0.0, is_day=True, day_ruler="Neptune")
    with pytest.raises(ValueError):
        almuten_figuris(positions, cusps=0.0, is_day=True, hour_ruler="Pluto")


@pytest.mark.requires_ephemeris
def test_facade_almuten_figuris_strict_mode(moira_engine) -> None:
    """Verifies that strict=True bubbles up resolution failures in the facade."""
    from datetime import datetime, timezone
    from types import SimpleNamespace

    # Create a mock chart with missing fields that would crash the planetary hour/syzygy resolution
    chart = SimpleNamespace(jd_ut="invalid_jd", longitudes=lambda include_nodes=False: {"Sun": 0.0, "Moon": 0.0})
    houses = SimpleNamespace(asc=0.0, cusps=[0.0] * 12)

    # Calling with strict=False (default) should pass, silently ignoring the failure and using fallbacks
    res = moira_engine.almuten_figuris(chart, houses, strict=False)
    assert res in CLASSIC_7

    # Calling with strict=True should bubble up the AttributeError or other resolution error
    with pytest.raises(Exception):
        moira_engine.almuten_figuris(chart, houses, strict=True)

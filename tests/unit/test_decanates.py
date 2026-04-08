"""
Unit tests for moira.decanates — Chaldean faces, triplicity decans, Vedic drekkanas.

All three systems are tested for:
  - Correct ruling planet at known reference longitudes
  - Correct decan_number (1/2/3)
  - Correct degree_in_decan arithmetic
  - Correct sign assignment
  - Correct ruling_sign (or None for Chaldean)
  - Domain coverage (all 36 faces / all 36 sign-decan slots)
  - Boundary behaviour (0°, 360°, sign cusps, decan cusps)
  - DecanatePosition field invariants
"""
from __future__ import annotations

import math
import pytest

from moira.decanates import DecanatePosition, chaldean_face, triplicity_decan, vedic_drekkana


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JD_J2000 = 2451545.0  # 2000 Jan 1.5 TT


# ---------------------------------------------------------------------------
# DecanatePosition — structural invariants
# ---------------------------------------------------------------------------

def test_decanate_position_is_frozen():
    pos = chaldean_face(0.0)
    with pytest.raises((AttributeError, TypeError)):
        pos.ruling_planet = 'Saturn'  # type: ignore[misc]


def test_decanate_position_fields_present():
    pos = chaldean_face(45.0)
    assert hasattr(pos, 'system')
    assert hasattr(pos, 'decan_number')
    assert hasattr(pos, 'ruling_planet')
    assert hasattr(pos, 'ruling_sign')
    assert hasattr(pos, 'sign')
    assert hasattr(pos, 'sign_symbol')
    assert hasattr(pos, 'degree_in_decan')
    assert hasattr(pos, 'longitude_used')


def test_degree_in_decan_always_in_range():
    for lon in range(0, 360, 7):
        for fn in (chaldean_face, triplicity_decan):
            pos = fn(float(lon))
            assert 0.0 <= pos.degree_in_decan < 10.0, (
                f"{fn.__name__}({lon}): degree_in_decan={pos.degree_in_decan}"
            )


def test_decan_number_always_1_2_or_3():
    for lon in range(0, 360, 3):
        for fn in (chaldean_face, triplicity_decan):
            pos = fn(float(lon))
            assert pos.decan_number in (1, 2, 3)


def test_longitude_used_reduced_to_0_360():
    pos = chaldean_face(720.0)
    assert 0.0 <= pos.longitude_used < 360.0
    pos2 = triplicity_decan(-30.0)
    assert 0.0 <= pos2.longitude_used < 360.0


# ---------------------------------------------------------------------------
# Chaldean Faces — ruling planet table
#
# Reference: Agrippa, Three Books of Occult Philosophy, Book II, Ch. 37.
# Cycle: Mars, Sun, Venus, Mercury, Moon, Saturn, Jupiter (repeating).
# ---------------------------------------------------------------------------

_CHALDEAN_REFERENCE: tuple[tuple[float, str, str], ...] = (
    # (longitude, expected_planet, expected_sign)
    (0.0,   'Mars',    'Aries'),       # face 0
    (10.0,  'Sun',     'Aries'),       # face 1
    (20.0,  'Venus',   'Aries'),       # face 2
    (30.0,  'Mercury', 'Taurus'),      # face 3
    (40.0,  'Moon',    'Taurus'),      # face 4
    (50.0,  'Saturn',  'Taurus'),      # face 5
    (60.0,  'Jupiter', 'Gemini'),      # face 6
    (70.0,  'Mars',    'Gemini'),      # face 7 — cycle repeats
    (80.0,  'Sun',     'Gemini'),      # face 8
    (120.0, 'Saturn',  'Leo'),         # face 12
    (180.0, 'Moon',    'Libra'),       # face 18
    (210.0, 'Mars',    'Scorpio'),     # face 21 — Mars again
    (330.0, 'Saturn',  'Pisces'),      # face 33
    (340.0, 'Jupiter', 'Pisces'),      # face 34
    (350.0, 'Mars',    'Pisces'),      # face 35 — last face
)


@pytest.mark.parametrize(("lon", "planet", "sign"), _CHALDEAN_REFERENCE)
def test_chaldean_face_ruling_planet(lon: float, planet: str, sign: str) -> None:
    pos = chaldean_face(lon)
    assert pos.ruling_planet == planet, (
        f"lon={lon}: expected {planet}, got {pos.ruling_planet}"
    )
    assert pos.sign == sign


def test_chaldean_face_ruling_sign_is_none():
    for lon in (0.0, 45.0, 180.0, 350.0):
        assert chaldean_face(lon).ruling_sign is None


def test_chaldean_face_system_label():
    assert chaldean_face(0.0).system == 'chaldean_face'


def test_chaldean_face_covers_all_36_faces():
    """Every 10° step must yield a valid classical planet."""
    classical = {'Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn'}
    planets_seen = set()
    for i in range(36):
        pos = chaldean_face(float(i * 10))
        assert pos.ruling_planet in classical
        planets_seen.add(pos.ruling_planet)
    assert planets_seen == classical


def test_chaldean_face_decan_number_at_boundaries():
    assert chaldean_face(0.0).decan_number == 1
    assert chaldean_face(9.999).decan_number == 1
    assert chaldean_face(10.0).decan_number == 2
    assert chaldean_face(20.0).decan_number == 3
    assert chaldean_face(29.999).decan_number == 3


def test_chaldean_face_degree_in_decan_arithmetic():
    pos = chaldean_face(7.5)      # Aries 7.5° — decan 1
    assert math.isclose(pos.degree_in_decan, 7.5)
    pos = chaldean_face(13.25)    # Aries 13.25° — decan 2, 3.25° in
    assert math.isclose(pos.degree_in_decan, 3.25)
    pos = chaldean_face(25.0)     # Aries 25° — decan 3, 5.0° in
    assert math.isclose(pos.degree_in_decan, 5.0)


# ---------------------------------------------------------------------------
# Triplicity Decans — rulership table
#
# Source: Dorotheus, Carmen Astrologicum; Valens, Anthology.
# Each sign's decans are ruled by the same-element signs in zodiacal order.
# ---------------------------------------------------------------------------

_TRIPLICITY_REFERENCE: tuple[tuple[float, str, str, str], ...] = (
    # (longitude, sign, ruling_sign, ruling_planet)
    # Fire triplicity
    (0.0,   'Aries',       'Aries',       'Mars'),
    (15.0,  'Aries',       'Leo',         'Sun'),
    (25.0,  'Aries',       'Sagittarius', 'Jupiter'),
    (120.0, 'Leo',         'Leo',         'Sun'),
    (135.0, 'Leo',         'Sagittarius', 'Jupiter'),
    (145.0, 'Leo',         'Aries',       'Mars'),
    (240.0, 'Sagittarius', 'Sagittarius', 'Jupiter'),
    (255.0, 'Sagittarius', 'Aries',       'Mars'),
    (265.0, 'Sagittarius', 'Leo',         'Sun'),
    # Earth triplicity
    (30.0,  'Taurus',    'Taurus',    'Venus'),
    (45.0,  'Taurus',    'Virgo',     'Mercury'),
    (55.0,  'Taurus',    'Capricorn', 'Saturn'),
    (150.0, 'Virgo',     'Virgo',     'Mercury'),
    (270.0, 'Capricorn', 'Capricorn', 'Saturn'),
    # Air triplicity
    (60.0,  'Gemini',    'Gemini',    'Mercury'),
    (75.0,  'Gemini',    'Libra',     'Venus'),
    (85.0,  'Gemini',    'Aquarius',  'Saturn'),
    (180.0, 'Libra',     'Libra',     'Venus'),
    (300.0, 'Aquarius',  'Aquarius',  'Saturn'),
    # Water triplicity
    (90.0,  'Cancer',  'Cancer',  'Moon'),
    (105.0, 'Cancer',  'Scorpio', 'Mars'),
    (115.0, 'Cancer',  'Pisces',  'Jupiter'),
    (210.0, 'Scorpio', 'Scorpio', 'Mars'),
    (330.0, 'Pisces',  'Pisces',  'Jupiter'),
)


@pytest.mark.parametrize(("lon", "sign", "r_sign", "r_planet"), _TRIPLICITY_REFERENCE)
def test_triplicity_decan_rulership(
    lon: float, sign: str, r_sign: str, r_planet: str
) -> None:
    pos = triplicity_decan(lon)
    assert pos.sign == sign, f"lon={lon}: sign {pos.sign} != {sign}"
    assert pos.ruling_sign == r_sign, f"lon={lon}: ruling_sign {pos.ruling_sign} != {r_sign}"
    assert pos.ruling_planet == r_planet, f"lon={lon}: planet {pos.ruling_planet} != {r_planet}"


def test_triplicity_decan_system_label():
    assert triplicity_decan(0.0).system == 'triplicity'


def test_triplicity_decan_ruling_sign_is_never_none():
    for lon in range(0, 360, 5):
        assert triplicity_decan(float(lon)).ruling_sign is not None


def test_triplicity_decan_ruling_sign_same_element_as_sign():
    """Ruling sign must share the same element (fire/earth/air/water) as the body's sign."""
    fire = {'Aries', 'Leo', 'Sagittarius'}
    earth = {'Taurus', 'Virgo', 'Capricorn'}
    air = {'Gemini', 'Libra', 'Aquarius'}
    water = {'Cancer', 'Scorpio', 'Pisces'}
    elements = [fire, earth, air, water]

    for lon in range(0, 360, 3):
        pos = triplicity_decan(float(lon))
        body_element = next(e for e in elements if pos.sign in e)
        assert pos.ruling_sign in body_element, (
            f"lon={lon}: {pos.sign} (body) and {pos.ruling_sign} (ruler) "
            "are not the same element"
        )


# ---------------------------------------------------------------------------
# Vedic Drekkanas — sidereal frame and Vedic rulership
# ---------------------------------------------------------------------------

def test_vedic_drekkana_system_label():
    pos = vedic_drekkana(0.0, _JD_J2000)
    assert pos.system == 'vedic_drekkana'


def test_vedic_drekkana_longitude_used_is_sidereal():
    """longitude_used must differ from the tropical input by ~ayanamsha."""
    from moira.sidereal import ayanamsa, Ayanamsa
    trop = 45.0
    pos = vedic_drekkana(trop, _JD_J2000)
    ayan = ayanamsa(_JD_J2000, Ayanamsa.LAHIRI)
    expected_sid = (trop - ayan) % 360.0
    assert math.isclose(pos.longitude_used, expected_sid, abs_tol=1e-10)


def test_vedic_drekkana_ruling_sign_same_element():
    """Ruling sign must share the same element as the sidereal sign."""
    fire = {'Aries', 'Leo', 'Sagittarius'}
    earth = {'Taurus', 'Virgo', 'Capricorn'}
    air = {'Gemini', 'Libra', 'Aquarius'}
    water = {'Cancer', 'Scorpio', 'Pisces'}
    elements = [fire, earth, air, water]

    for lon in range(0, 360, 10):
        pos = vedic_drekkana(float(lon), _JD_J2000)
        body_element = next(e for e in elements if pos.sign in e)
        assert pos.ruling_sign in body_element


def test_vedic_drekkana_uses_traditional_rulers_only():
    """No outer planets may appear as drekkana rulers."""
    outer = {'Uranus', 'Neptune', 'Pluto'}
    for lon in range(0, 360, 5):
        pos = vedic_drekkana(float(lon), _JD_J2000)
        assert pos.ruling_planet not in outer, (
            f"lon={lon}: outer planet {pos.ruling_planet} in drekkana ruler"
        )


def test_vedic_drekkana_scorpio_ruled_by_mars():
    """In Vedic tradition, Scorpio is ruled by Mars, not Pluto."""
    from moira.sidereal import ayanamsa, Ayanamsa
    # Find a longitude that maps to sidereal Scorpio decan 1
    # Scorpio sidereal starts at ~210° + ayanamsha from tropical
    ayan = ayanamsa(_JD_J2000, Ayanamsa.LAHIRI)
    scorpio_sid_start = 210.0
    trop = (scorpio_sid_start + ayan) % 360.0
    pos = vedic_drekkana(trop + 2.0, _JD_J2000)  # +2° into Scorpio decan 1
    assert pos.sign == 'Scorpio'
    assert pos.ruling_planet == 'Mars'


def test_vedic_drekkana_accepts_ayanamsa_system_override():
    from moira.sidereal import Ayanamsa
    pos_lahiri  = vedic_drekkana(45.0, _JD_J2000, ayanamsa_system=Ayanamsa.LAHIRI)
    pos_fagan   = vedic_drekkana(45.0, _JD_J2000, ayanamsa_system=Ayanamsa.FAGAN_BRADLEY)
    # Different systems produce different sidereal longitudes
    assert pos_lahiri.longitude_used != pos_fagan.longitude_used


def test_vedic_drekkana_decan_number_in_range():
    for lon in range(0, 360, 7):
        pos = vedic_drekkana(float(lon), _JD_J2000)
        assert pos.decan_number in (1, 2, 3)


# ---------------------------------------------------------------------------
# Cross-system consistency
# ---------------------------------------------------------------------------

def test_all_systems_return_decanate_position():
    for fn, args in (
        (chaldean_face, (0.0,)),
        (triplicity_decan, (0.0,)),
        (vedic_drekkana, (0.0, _JD_J2000)),
    ):
        result = fn(*args)
        assert isinstance(result, DecanatePosition)


def test_triplicity_and_vedic_same_ruler_when_ayanamsha_zero():
    """
    If ayanamsha is zero (tropical == sidereal), triplicity and Vedic drekkana
    must agree on ruling planet and ruling sign for every longitude.
    """
    from moira.sidereal import UserDefinedAyanamsa
    zero_ayan = UserDefinedAyanamsa(reference_value_j2000=0.0)
    for lon in range(0, 360, 10):
        trip = triplicity_decan(float(lon))
        vedic = vedic_drekkana(float(lon), _JD_J2000, ayanamsa_system=zero_ayan)
        assert trip.ruling_planet == vedic.ruling_planet, (
            f"lon={lon}: triplicity={trip.ruling_planet}, vedic={vedic.ruling_planet}"
        )
        assert trip.ruling_sign == vedic.ruling_sign

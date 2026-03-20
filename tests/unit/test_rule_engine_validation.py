"""
tests/unit/test_rule_engine_validation.py

Validation suite for Moira's pure rule-engine / arithmetic modules.

These modules have no ephemeris dependency and no continuous astronomical
model: their correctness is entirely a question of formula implementation
and edge-case logic.  The validation approach is therefore:

  - derive every expected value by hand from first principles or published
    canonical tables
  - lock those values in as the regression baseline
  - apply invariant tests where the mathematics demands a specific property
    regardless of input

Modules covered
---------------
1. antiscia      — solstice-axis and equinox-axis mirror formulas
2. midpoints     — shorter-arc midpoint and 90° dial projection
3. profections   — annual/monthly profection arithmetic
4. planetary_hours — Chaldean sequence and day-ruler assignment
5. harmonics     — harmonic position formula and round-trip invariant
6. lots          — Arabic Parts formula, day/night reversal
7. dignities     — essential dignity table lookups and accidental scoring

Oracle / authority
------------------
Each section cites the primary traditional source used to derive the
expected values.  No external software was used; all values were computed
from the published formulas.

Thresholds
----------
  - Float geometry results: < 1e-9° (machine precision; no model uncertainty)
  - Categorical / string results: exact match
  - Integer results: exact match
"""

from __future__ import annotations

import math
import pytest


# ---------------------------------------------------------------------------
# 1. Antiscia
# ---------------------------------------------------------------------------
# Canon: Vettius Valens, Anthology II.37; William Lilly, Christian Astrology
#        (1647) p. 90.
#
# Antiscion formula  : (180° − lon) mod 360°  [solstice axis]
# Contra-antiscion   : (360° − lon) mod 360°  [equinox axis]
#
# Hand-derived reference table (all longitude values in decimal degrees):
#
#   lon    antiscion          contra-antiscion
#   0.0    180.0              0.0   (edge: equinox point)
#   90.0   90.0               270.0 (edge: solstice point — maps to itself)
#   45.0   135.0              315.0
#   135.0  45.0               225.0
#   200.0  340.0              160.0
#   359.0  181.0              1.0
#   360.0  180.0              0.0   (treated as 0.0 mod 360)
#
# Round-trip invariant: antiscion(antiscion(lon)) == lon mod 360
# Contra round-trip  : contra(contra(lon)) == lon mod 360

_ANTISCIA_TABLE = [
    (0.0,   180.0, 0.0),
    (90.0,  90.0,  270.0),
    (45.0,  135.0, 315.0),
    (135.0, 45.0,  225.0),
    (200.0, 340.0, 160.0),
    (359.0, 181.0, 1.0),
    (360.0, 180.0, 0.0),
]

_FLOAT_TOL = 1e-9


class TestAntiscia:
    def test_antiscion_formula(self):
        from moira.antiscia import antiscion
        for lon, expected, _ in _ANTISCIA_TABLE:
            result = antiscion(lon)
            assert abs(result - expected) < _FLOAT_TOL, (
                f"antiscion({lon}) = {result}, expected {expected}"
            )

    def test_contra_antiscion_formula(self):
        from moira.antiscia import contra_antiscion
        for lon, _, expected in _ANTISCIA_TABLE:
            result = contra_antiscion(lon)
            assert abs(result - expected) < _FLOAT_TOL, (
                f"contra_antiscion({lon}) = {result}, expected {expected}"
            )

    def test_antiscion_round_trip(self):
        from moira.antiscia import antiscion
        for lon in [0.0, 30.0, 90.0, 135.0, 180.0, 270.0, 359.9]:
            assert abs(antiscion(antiscion(lon)) - (lon % 360.0)) < _FLOAT_TOL

    def test_contra_antiscion_round_trip(self):
        from moira.antiscia import contra_antiscion
        for lon in [0.0, 30.0, 90.0, 135.0, 180.0, 270.0, 359.9]:
            assert abs(contra_antiscion(contra_antiscion(lon)) - (lon % 360.0)) < _FLOAT_TOL

    def test_find_antiscia_detects_exact_contact(self):
        from moira.antiscia import find_antiscia, antiscion
        # Sun at 45°; its antiscion is 135°.  Place Moon exactly there.
        positions = {"Sun": 45.0, "Moon": 135.0}
        result = find_antiscia(positions, orb=0.5)
        assert len(result) == 1
        assert result[0].aspect == "Antiscion"
        assert result[0].orb < _FLOAT_TOL

    def test_find_antiscia_detects_contra_exact(self):
        from moira.antiscia import find_antiscia, contra_antiscion
        # Venus at 60°; its contra-antiscion is 300°.
        positions = {"Venus": 60.0, "Mars": 300.0}
        result = find_antiscia(positions, orb=0.5)
        assert len(result) == 1
        assert result[0].aspect == "Contra-Antiscion"

    def test_find_antiscia_orb_exclusion(self):
        from moira.antiscia import find_antiscia
        # Sun at 45° (antiscion 135°).  Moon 3° away at 138°.
        positions = {"Sun": 45.0, "Moon": 138.0}
        within_orb = find_antiscia(positions, orb=3.0)
        outside_orb = find_antiscia(positions, orb=2.0)
        assert len(within_orb) == 1
        assert len(outside_orb) == 0

    def test_antiscia_to_point(self):
        from moira.antiscia import antiscia_to_point
        # Mars at 30° (antiscion = 150°); test point at 150°
        result = antiscia_to_point(150.0, {"Mars": 30.0}, orb=0.5)
        assert len(result) == 1
        assert result[0].aspect == "Antiscion"

    def test_zero_crossing(self):
        from moira.antiscia import antiscion, contra_antiscion
        # 180° is its own antiscion (the solstice axis midpoint)
        assert abs(antiscion(180.0) - 0.0) < _FLOAT_TOL
        # 0° contra-antiscion is itself
        assert abs(contra_antiscion(0.0) - 0.0) < _FLOAT_TOL


# ---------------------------------------------------------------------------
# 2. Midpoints
# ---------------------------------------------------------------------------
# Canon: Reinhold Ebertin, The Combination of Stellar Influences (1940);
#        Alfred Witte, Rules for Planetary Pictures (Hamburg School).
#
# Shorter-arc midpoint formula:
#   diff = |a - b| mod 360
#   if diff <= 180:  mid = (a + b) / 2
#   else:            mid = ((a + b) / 2 + 180) mod 360
#
# Hand-derived table:
#
#   a      b       shorter-arc midpoint
#   0      180     90.0  (equal arcs; shorter arc is 90°)
#   10     350     0.0   (crosses 0°/360° seam; mid = 0°)
#   30     60      45.0
#   0      90      45.0
#   90     270     0.0   (or 180; shorter arc mid)
#   300    60      0.0   (60° arc across 0°)
#
# 90° dial: dial = (lon * 4) mod 90
#   lon=45  → 180 mod 90 = 0
#   lon=22.5 → 90 mod 90 = 0
#   lon=0   → 0
#   lon=10  → 40

_MIDPOINT_TABLE = [
    (0.0,   180.0, 90.0),
    (30.0,  60.0,  45.0),
    (0.0,   90.0,  45.0),
    (10.0,  350.0, 0.0),
    (300.0, 60.0,  0.0),
]

_DIAL90_TABLE = [
    (0.0,   0.0),
    (10.0,  40.0),
    (22.5,  0.0),
    (45.0,  0.0),
    (91.0,  4.0),
]


class TestMidpoints:
    def test_midpoint_formula(self):
        from moira.midpoints import _midpoint
        for a, b, expected in _MIDPOINT_TABLE:
            result = _midpoint(a, b)
            assert abs(result - expected) < _FLOAT_TOL, (
                f"_midpoint({a}, {b}) = {result}, expected {expected}"
            )

    def test_midpoint_commutative(self):
        from moira.midpoints import _midpoint
        for a, b, _ in _MIDPOINT_TABLE:
            assert abs(_midpoint(a, b) - _midpoint(b, a)) < _FLOAT_TOL

    def test_midpoint_self(self):
        from moira.midpoints import _midpoint
        for lon in [0.0, 45.0, 180.0, 270.0, 359.9]:
            assert abs(_midpoint(lon, lon) - lon % 360) < _FLOAT_TOL

    def test_dial_90_projection(self):
        from moira.midpoints import to_dial_90
        for lon, expected in _DIAL90_TABLE:
            result = to_dial_90(lon)
            assert abs(result - expected) < _FLOAT_TOL, (
                f"to_dial_90({lon}) = {result}, expected {expected}"
            )

    def test_calculate_midpoints_count(self):
        from moira.midpoints import calculate_midpoints
        # Classic 7: C(7,2) = 21 pairs
        lons = {
            "Sun": 280.0, "Moon": 15.0, "Mercury": 265.0,
            "Venus": 241.0, "Mars": 328.0, "Jupiter": 25.0, "Saturn": 60.0,
        }
        mps = calculate_midpoints(lons, planet_set="classic")
        assert len(mps) == 21

    def test_calculate_midpoints_sorted(self):
        from moira.midpoints import calculate_midpoints
        lons = {
            "Sun": 100.0, "Moon": 200.0, "Mercury": 50.0,
            "Venus": 300.0, "Mars": 150.0, "Jupiter": 250.0, "Saturn": 10.0,
        }
        mps = calculate_midpoints(lons, planet_set="classic")
        for i in range(len(mps) - 1):
            assert mps[i].longitude <= mps[i + 1].longitude

    def test_midpoints_to_point_finds_hit(self):
        from moira.midpoints import midpoints_to_point, _midpoint
        # Sun at 0°, Moon at 90° → midpoint at 45°
        lons = {"Sun": 0.0, "Moon": 90.0, "Mercury": 200.0,
                "Venus": 220.0, "Mars": 240.0, "Jupiter": 260.0, "Saturn": 280.0}
        hits = midpoints_to_point(45.0, lons, orb=0.01)
        pair_keys = {(h[0].planet_a, h[0].planet_b) for h in hits}
        assert ("Moon", "Sun") in pair_keys or ("Sun", "Moon") in pair_keys

    def test_seam_midpoint_0_360(self):
        from moira.midpoints import _midpoint
        # 350° and 10° — shorter arc is 20°; midpoint should be 0°
        result = _midpoint(350.0, 10.0)
        assert abs(result - 0.0) < _FLOAT_TOL or abs(result - 360.0) < _FLOAT_TOL


# ---------------------------------------------------------------------------
# 3. Profections
# ---------------------------------------------------------------------------
# Canon: Chris Brennan, Hellenistic Astrology (2017), Ch. 9;
#        Vettius Valens, Anthology, Book IV.
#
# Annual profection rule: profected ASC = (natal_asc + age * 30°) mod 360°
#
# Hand-derived table (natal ASC = 0° Aries = 0.0°):
#
#   age  profected_lon  sign         lord        house
#    0    0.0           Aries        Mars          1
#    1   30.0           Taurus       Venus         2
#    2   60.0           Gemini       Mercury       3
#    6  180.0           Libra        Venus         7
#   11  330.0           Pisces       Jupiter      12
#   12    0.0           Aries        Mars          1  (cycle restarts)
#   30    0.0           Aries        Mars          7  (30 mod 12 = 6 → house 7)
#
# Note on house numbering: house = (age mod 12) + 1
#   age=0  → house 1
#   age=11 → house 12
#   age=12 → house 1
#   age=30 → house 7

_PROFECTION_TABLE = [
    (0.0,  0,  0.0,   "Aries",        "Mars",    1),
    (0.0,  1,  30.0,  "Taurus",       "Venus",   2),
    (0.0,  2,  60.0,  "Gemini",       "Mercury", 3),
    (0.0,  6,  180.0, "Libra",        "Venus",   7),
    (0.0,  11, 330.0, "Pisces",       "Jupiter", 12),
    (0.0,  12, 0.0,   "Aries",        "Mars",    1),
    (0.0,  30, 180.0, "Libra",        "Venus",   7),
    (15.0, 1,  45.0,  "Taurus",       "Venus",   2),
    (150.0,3,  240.0, "Sagittarius",  "Jupiter", 4),
]


class TestProfections:
    def test_annual_profection_longitude(self):
        from moira.profections import annual_profection
        for natal_asc, age, expected_lon, expected_sign, expected_lord, expected_house in _PROFECTION_TABLE:
            result = annual_profection(natal_asc, age)
            assert abs(result.profected_asc_lon - expected_lon) < _FLOAT_TOL, (
                f"natal={natal_asc}, age={age}: lon={result.profected_asc_lon}, expected {expected_lon}"
            )

    def test_annual_profection_sign(self):
        from moira.profections import annual_profection
        for natal_asc, age, _, expected_sign, _, _ in _PROFECTION_TABLE:
            result = annual_profection(natal_asc, age)
            assert result.profected_sign == expected_sign, (
                f"natal={natal_asc}, age={age}: sign={result.profected_sign}, expected {expected_sign}"
            )

    def test_annual_profection_lord(self):
        from moira.profections import annual_profection
        for natal_asc, age, _, _, expected_lord, _ in _PROFECTION_TABLE:
            result = annual_profection(natal_asc, age)
            assert result.lord_of_year == expected_lord, (
                f"natal={natal_asc}, age={age}: lord={result.lord_of_year}, expected {expected_lord}"
            )

    def test_annual_profection_house(self):
        from moira.profections import annual_profection
        for natal_asc, age, _, _, _, expected_house in _PROFECTION_TABLE:
            result = annual_profection(natal_asc, age)
            assert result.profected_house == expected_house, (
                f"natal={natal_asc}, age={age}: house={result.profected_house}, expected {expected_house}"
            )

    def test_profected_house_range(self):
        from moira.profections import annual_profection
        for age in range(50):
            r = annual_profection(0.0, age)
            assert 1 <= r.profected_house <= 12

    def test_monthly_lords_length(self):
        from moira.profections import annual_profection
        r = annual_profection(0.0, 0)
        assert len(r.monthly_lords) == 12

    def test_monthly_lords_first_matches_lord_of_year(self):
        from moira.profections import annual_profection
        for _, age, _, _, expected_lord, _ in _PROFECTION_TABLE:
            r = annual_profection(0.0, age)
            assert r.monthly_lords[0] == r.lord_of_year

    def test_monthly_profection_function(self):
        from moira.profections import monthly_profection
        # natal_asc=0°, age=0, month_index=1 → 30° Taurus, Venus
        lon, sign, lord = monthly_profection(0.0, 0, 1)
        assert abs(lon - 30.0) < _FLOAT_TOL
        assert sign == "Taurus"
        assert lord == "Venus"

    def test_12_year_cycle_identity(self):
        from moira.profections import annual_profection
        for natal_asc in [0.0, 15.0, 90.0, 180.0]:
            r0 = annual_profection(natal_asc, 0)
            r12 = annual_profection(natal_asc, 12)
            assert abs(r0.profected_asc_lon - r12.profected_asc_lon) < _FLOAT_TOL
            assert r0.profected_sign == r12.profected_sign
            assert r0.lord_of_year == r12.lord_of_year


# ---------------------------------------------------------------------------
# 4. Planetary Hours
# ---------------------------------------------------------------------------
# Canon: Porphyry, Introduction to Tetrabiblos; Hephaestio of Thebes,
#        Apotelesmatika I.
#
# Chaldean order: Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon
# Day rulers (first hour of daylight):
#   Sunday    → Sun    (index 3)
#   Monday    → Moon   (index 6)
#   Tuesday   → Mars   (index 2)
#   Wednesday → Mercury (index 5)
#   Thursday  → Jupiter (index 1)
#   Friday    → Venus  (index 4)
#   Saturday  → Saturn (index 0)
#
# The first night hour follows hour 12 of the day, continuing the Chaldean
# sequence.  For Sunday (day ruler = Sun, index 3):
#   Day hours 1–12: Sun(3), Venus(4), Mercury(5), Moon(6), Saturn(0),
#                   Jupiter(1), Mars(2), Sun(3), Venus(4), Mercury(5),
#                   Moon(6), Saturn(0)
#   Night hour 1 (hour 13): Jupiter(1)   [index (3+12) % 7 = 1]
#
# Hand-verified sequence for Sunday:
#   hour 1: Sun
#   hour 2: Venus
#   hour 3: Mercury
#   hour 4: Moon
#   hour 5: Saturn
#   hour 6: Jupiter
#   hour 7: Mars
#   hour 8: Sun
#   hour 9: Venus
#   hour 10: Mercury
#   hour 11: Moon
#   hour 12: Saturn
#   hour 13 (night 1): Jupiter

_CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

_DAY_RULER_IDX = {
    0: 3,  # Sunday   → Sun
    1: 6,  # Monday   → Moon
    2: 2,  # Tuesday  → Mars
    3: 5,  # Wednesday → Mercury
    4: 1,  # Thursday  → Jupiter
    5: 4,  # Friday    → Venus
    6: 0,  # Saturday  → Saturn
}

_DAY_RULER_NAME = {
    0: "Sun",
    1: "Moon",
    2: "Mars",
    3: "Mercury",
    4: "Jupiter",
    5: "Venus",
    6: "Saturn",
}


class TestPlanetaryHoursChaldean:
    def test_chaldean_day_sequence_sunday(self):
        day_ruler_idx = _DAY_RULER_IDX[0]  # Sunday
        expected_day = [
            "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter",
            "Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn",
        ]
        for i, expected_planet in enumerate(expected_day):
            ruler_idx = (day_ruler_idx + i) % 7
            assert _CHALDEAN[ruler_idx] == expected_planet, (
                f"Sunday day hour {i+1}: expected {expected_planet}, "
                f"got {_CHALDEAN[ruler_idx]}"
            )

    def test_chaldean_night_hour_1_sunday(self):
        day_ruler_idx = _DAY_RULER_IDX[0]  # Sunday
        night_start_idx = (day_ruler_idx + 12) % 7
        assert _CHALDEAN[night_start_idx] == "Jupiter"

    def test_day_ruler_sequence(self):
        expected_day_rulers = {
            0: "Sun",
            1: "Moon",
            2: "Mars",
            3: "Mercury",
            4: "Jupiter",
            5: "Venus",
            6: "Saturn",
        }
        for dow, expected_ruler in expected_day_rulers.items():
            idx = _DAY_RULER_IDX[dow]
            assert _CHALDEAN[idx] == expected_ruler, (
                f"DoW {dow}: expected {expected_ruler}, got {_CHALDEAN[idx]}"
            )

    def test_chaldean_24_hours_all_days(self):
        for dow in range(7):
            day_ruler_idx = _DAY_RULER_IDX[dow]
            rulers = []
            for i in range(12):
                rulers.append(_CHALDEAN[(day_ruler_idx + i) % 7])
            night_start = (day_ruler_idx + 12) % 7
            for i in range(12):
                rulers.append(_CHALDEAN[(night_start + i) % 7])
            assert len(rulers) == 24
            assert all(r in _CHALDEAN for r in rulers)

    def test_next_day_ruler_derivation(self):
        # The first hour of the next day is always hour 25 of the current day,
        # which is (start_idx + 24) % 7.
        # Because 24 mod 7 = 3, the next day's ruler is 3 positions ahead
        # in the Chaldean sequence from today's day ruler.
        for dow in range(7):
            today_start = _DAY_RULER_IDX[dow]
            tomorrow_start_computed = (today_start + 24) % 7
            tomorrow_start_table = _DAY_RULER_IDX[(dow + 1) % 7]
            assert tomorrow_start_computed == tomorrow_start_table, (
                f"DoW {dow}: next-day derivation gives idx {tomorrow_start_computed}, "
                f"table gives {tomorrow_start_table}"
            )

    def test_planetary_hours_module_day_sequence(self):
        from moira.planetary_hours import _CHALDEAN as module_chaldean
        from moira.planetary_hours import _DAY_RULER_IDX as module_idx
        # Verify the module's tables match our canonical reference
        assert list(module_chaldean) == _CHALDEAN
        assert dict(module_idx) == _DAY_RULER_IDX


# ---------------------------------------------------------------------------
# 5. Harmonics
# ---------------------------------------------------------------------------
# Canon: John Addey, Harmonics in Astrology (1976).
#
# Formula: harmonic_longitude = (natal_longitude * H) mod 360°
#
# Hand-derived table:
#
#   natal   H    harmonic_lon
#   30.0    1    30.0   (H1 = identity)
#   30.0    2    60.0
#   30.0    4    120.0
#   30.0    7    210.0
#   45.0    8    360.0 mod 360 = 0.0
#   90.0    4    360.0 mod 360 = 0.0
#   180.0   3    540.0 mod 360 = 180.0
#   270.0   2    540.0 mod 360 = 180.0
#   100.0   5    500.0 mod 360 = 140.0
#
# Invariant: H1 = identity (harmonic_lon == natal_lon)
# Invariant: harmonic_lon is in [0, 360)

_HARMONIC_TABLE = [
    (30.0,  1, 30.0),
    (30.0,  2, 60.0),
    (30.0,  4, 120.0),
    (30.0,  7, 210.0),
    (45.0,  8, 0.0),
    (90.0,  4, 0.0),
    (180.0, 3, 180.0),
    (270.0, 2, 180.0),
    (100.0, 5, 140.0),
]


class TestHarmonics:
    def test_harmonic_formula(self):
        from moira.harmonics import calculate_harmonic
        for natal, h, expected in _HARMONIC_TABLE:
            result = calculate_harmonic({"Body": natal}, h)
            assert len(result) == 1
            got = result[0].harmonic_longitude
            assert abs(got - expected) < _FLOAT_TOL, (
                f"natal={natal}, H={h}: got {got}, expected {expected}"
            )

    def test_h1_is_identity(self):
        from moira.harmonics import calculate_harmonic
        for lon in [0.0, 15.0, 90.0, 179.9, 270.0, 359.9]:
            result = calculate_harmonic({"Body": lon}, 1)
            assert abs(result[0].harmonic_longitude - lon % 360.0) < _FLOAT_TOL

    def test_harmonic_output_in_range(self):
        from moira.harmonics import calculate_harmonic
        for natal in [0.0, 45.0, 90.0, 179.9, 270.0, 359.9]:
            for h in [2, 3, 4, 5, 7, 9]:
                result = calculate_harmonic({"Body": natal}, h)
                lon = result[0].harmonic_longitude
                assert 0.0 <= lon < 360.0, (
                    f"natal={natal}, H={h}: harmonic_lon={lon} out of [0,360)"
                )

    def test_harmonic_sorted_by_longitude(self):
        from moira.harmonics import calculate_harmonic
        lons = {"Sun": 10.0, "Moon": 100.0, "Mars": 200.0, "Venus": 300.0}
        result = calculate_harmonic(lons, 3)
        for i in range(len(result) - 1):
            assert result[i].harmonic_longitude <= result[i + 1].harmonic_longitude

    def test_natal_longitude_preserved(self):
        from moira.harmonics import calculate_harmonic
        result = calculate_harmonic({"Sun": 123.456}, 5)
        assert abs(result[0].natal_longitude - 123.456) < _FLOAT_TOL

    def test_harmonic_number_clamped_to_1(self):
        from moira.harmonics import calculate_harmonic
        result = calculate_harmonic({"Sun": 50.0}, 0)
        # harmonic clamped to max(1, 0) = 1 → identity
        assert abs(result[0].harmonic_longitude - 50.0) < _FLOAT_TOL


# ---------------------------------------------------------------------------
# 6. Lots / Arabic Parts
# ---------------------------------------------------------------------------
# Canon: Paulus Alexandrinus, Introductory Matters (~375 CE);
#        Vettius Valens, Anthology, Books II–IV;
#        Masha'allah / Sahl Ibn Bishr.
#
# Formula: Lot = (ASC + Add − Sub) mod 360°
# Day/night reversal (where reverse_at_night=True):
#   Night chart: swap Add and Sub before applying formula
#
# Hand-derived reference (all longitudes decimal degrees):
#
# Part of Fortune (day formula: ASC + Moon − Sun; night: ASC + Sun − Moon)
#   Day chart:   ASC=10°, Moon=200°, Sun=100°  → (10+200-100) mod 360 = 110°
#   Night chart: ASC=10°, Sun=100°, Moon=200°  → (10+100-200) mod 360 = 270° (wraps via mod)
#     Actually: (10 + 100 - 200) = -90 → -90 mod 360 = 270°
#
# Part of Spirit (day: ASC + Sun − Moon; night: ASC + Moon − Sun)
#   Day chart:   ASC=10°, Sun=100°, Moon=200°  → (10+100-200) mod 360 = 270°
#   Night chart: ASC=10°, Moon=200°, Sun=100°  → (10+200-100) mod 360 = 110°
#
# Wraparound case:
#   ASC=350°, Add=20°, Sub=10° → (350+20-10) mod 360 = 360 mod 360 = 0°
#   ASC=10°, Add=5°, Sub=30°   → (10+5-30) mod 360 = -15 mod 360 = 345°

_LOTS_DAY_FORTUNE   = 110.0   # ASC=10, Moon=200, Sun=100 (day chart)
_LOTS_NIGHT_FORTUNE = 270.0   # same positions, night chart
_LOTS_DAY_SPIRIT    = 270.0   # ASC=10, Sun=100, Moon=200 (day chart)
_LOTS_NIGHT_SPIRIT  = 110.0   # same positions, night chart


class TestLots:
    def _make_inputs(self, asc, sun, moon):
        planet_lons = {
            "Sun": sun, "Moon": moon, "Mercury": 50.0,
            "Venus": 80.0, "Mars": 120.0, "Jupiter": 150.0, "Saturn": 200.0,
        }
        # Equal-house cusps from ASC
        house_cusps = {i + 1: (asc + i * 30.0) % 360.0 for i in range(12)}
        return planet_lons, house_cusps

    def test_fortune_day_formula(self):
        from moira.lots import ArabicPartsService
        svc = ArabicPartsService()
        lons, cusps = self._make_inputs(asc=10.0, sun=100.0, moon=200.0)
        parts = svc.calculate_parts(lons, cusps, is_day_chart=True)
        fortune = next((p for p in parts if p.name == "Fortune"), None)
        assert fortune is not None
        assert abs(fortune.longitude - _LOTS_DAY_FORTUNE) < _FLOAT_TOL, (
            f"Fortune day: {fortune.longitude}, expected {_LOTS_DAY_FORTUNE}"
        )

    def test_fortune_night_reversal(self):
        from moira.lots import ArabicPartsService
        svc = ArabicPartsService()
        lons, cusps = self._make_inputs(asc=10.0, sun=100.0, moon=200.0)
        parts = svc.calculate_parts(lons, cusps, is_day_chart=False)
        fortune = next((p for p in parts if p.name == "Fortune"), None)
        assert fortune is not None
        assert abs(fortune.longitude - _LOTS_NIGHT_FORTUNE) < _FLOAT_TOL, (
            f"Fortune night: {fortune.longitude}, expected {_LOTS_NIGHT_FORTUNE}"
        )

    def test_spirit_day_formula(self):
        from moira.lots import ArabicPartsService
        svc = ArabicPartsService()
        lons, cusps = self._make_inputs(asc=10.0, sun=100.0, moon=200.0)
        parts = svc.calculate_parts(lons, cusps, is_day_chart=True)
        spirit = next((p for p in parts if p.name == "Spirit"), None)
        assert spirit is not None
        assert abs(spirit.longitude - _LOTS_DAY_SPIRIT) < _FLOAT_TOL

    def test_spirit_night_reversal(self):
        from moira.lots import ArabicPartsService
        svc = ArabicPartsService()
        lons, cusps = self._make_inputs(asc=10.0, sun=100.0, moon=200.0)
        parts = svc.calculate_parts(lons, cusps, is_day_chart=False)
        spirit = next((p for p in parts if p.name == "Spirit"), None)
        assert spirit is not None
        assert abs(spirit.longitude - _LOTS_NIGHT_SPIRIT) < _FLOAT_TOL

    def test_lot_longitude_in_range(self):
        from moira.lots import ArabicPartsService
        svc = ArabicPartsService()
        lons, cusps = self._make_inputs(asc=350.0, sun=10.0, moon=20.0)
        parts = svc.calculate_parts(lons, cusps, is_day_chart=True)
        for part in parts:
            assert 0.0 <= part.longitude < 360.0, (
                f"{part.name}: longitude {part.longitude} out of [0, 360)"
            )

    def test_fortune_spirit_complement(self):
        # Part of Fortune and Part of Spirit are complementary:
        # fortune + spirit = 2 * ASC (mod 360) for day charts
        # (since Fortune = ASC + Moon - Sun and Spirit = ASC + Sun - Moon,
        #  their sum = 2*ASC)
        from moira.lots import ArabicPartsService
        svc = ArabicPartsService()
        lons, cusps = self._make_inputs(asc=45.0, sun=100.0, moon=200.0)
        parts = svc.calculate_parts(lons, cusps, is_day_chart=True)
        fortune = next(p for p in parts if p.name == "Fortune")
        spirit = next(p for p in parts if p.name == "Spirit")
        total = (fortune.longitude + spirit.longitude) % 360.0
        expected = (2 * 45.0) % 360.0
        assert abs(total - expected) < _FLOAT_TOL, (
            f"Fortune + Spirit = {total}, expected 2*ASC = {expected}"
        )


# ---------------------------------------------------------------------------
# 7. Dignities
# ---------------------------------------------------------------------------
# Canon: William Lilly, Christian Astrology (1647), Book I, Ch. XII–XIII;
#        Ptolemy, Tetrabiblos I.17–22.
#
# Essential dignity table (traditional rulerships):
#
#   Planet    Domicile        Exaltation    Detriment           Fall
#   Sun       Leo             Aries         Aquarius            Libra
#   Moon      Cancer          Taurus        Capricorn           Scorpio
#   Mercury   Gemini, Virgo   Virgo         Sagittarius, Pisces Pisces
#   Venus     Taurus, Libra   Pisces        Scorpio, Aries      Virgo
#   Mars      Aries, Scorpio  Capricorn     Libra, Taurus       Cancer
#   Jupiter   Sagittarius,    Cancer        Gemini, Virgo       Capricorn
#             Pisces
#   Saturn    Capricorn,      Libra         Cancer, Leo         Aries
#             Aquarius
#
# Hand-derived test cases (planet longitude → expected essential dignity):
#
#   Sun at 130° = 10° Leo → Domicile
#   Sun at 15°  = 15° Aries → Exaltation
#   Moon at 45° = 15° Taurus → Exaltation
#   Mars at 5°  = 5° Aries → Domicile
#   Saturn at 195° = 15° Libra → Exaltation
#   Venus at 340° = 10° Pisces → Exaltation
#   Mercury at 65° = 5° Gemini → Domicile
#   Jupiter at 100° = 10° Cancer → Exaltation
#
#   Sun at 300° = 0° Aquarius → Detriment
#   Moon at 240° = 0° Scorpio → Fall
#
# Accidental dignity: Angular house (+4), Cadent house (-2), Retrograde (-5),
#   Cazimi (within 0.283° of Sun) (+5), Combust (<8°) (-5)

_ESSENTIAL_DIGNITY_TABLE = [
    # planet, lon, expected_dignity, expected_score
    ("Sun",     130.0, "Domicile",   5),
    ("Sun",      15.0, "Exaltation", 4),
    ("Moon",     45.0, "Exaltation", 4),
    ("Mars",      5.0, "Domicile",   5),
    ("Saturn",  195.0, "Exaltation", 4),
    ("Venus",   340.0, "Exaltation", 4),
    ("Mercury",  65.0, "Domicile",   5),
    ("Jupiter", 100.0, "Exaltation", 4),
    ("Sun",     300.0, "Detriment",  -5),
    ("Moon",    225.0, "Fall",       -4),  # 225° = 15° Scorpio
    ("Mars",    195.0, "Detriment",  -5),  # Mars in Libra (180–210°)
    ("Venus",   150.0, "Fall",       -4),  # Venus in Virgo → Fall
]

_ESSENTIAL_DIGNITY_TABLE_CORRECTED = _ESSENTIAL_DIGNITY_TABLE


class TestDignities:
    def _make_planet(self, name: str, degree: float, is_retrograde: bool = False) -> dict:
        return {"name": name, "degree": degree, "is_retrograde": is_retrograde}

    def _make_houses(self, asc: float = 0.0) -> list[dict]:
        return [{"number": i + 1, "degree": (asc + i * 30.0) % 360.0} for i in range(12)]

    def test_essential_dignity_lookup(self):
        from moira.dignities import DignitiesService
        svc = DignitiesService()
        for planet, lon, expected_dignity, expected_score in _ESSENTIAL_DIGNITY_TABLE_CORRECTED:
            planet_positions = [self._make_planet(planet, lon)]
            # Place Sun somewhere neutral for accidental tests
            if planet != "Sun":
                planet_positions.append(self._make_planet("Sun", 0.0))
            result = svc.calculate_dignities(planet_positions, self._make_houses())
            target = next((d for d in result if d.planet == planet), None)
            assert target is not None, f"{planet} not found in result"
            assert target.essential_dignity == expected_dignity, (
                f"{planet} at {lon}°: dignity={target.essential_dignity}, expected {expected_dignity}"
            )
            assert target.essential_score == expected_score, (
                f"{planet} at {lon}°: score={target.essential_score}, expected {expected_score}"
            )

    def test_angular_house_bonus(self):
        from moira.dignities import calculate_dignities
        # Mars at 0° (Aries, domicile) in house 1 (angular) → score includes +4
        planet_positions = [
            {"name": "Mars", "degree": 5.0},
            {"name": "Sun",  "degree": 0.0},
        ]
        # Cusps: H1=0°, so Mars at 5° falls in H1 (angular)
        house_positions = self._make_houses(0.0)
        result = calculate_dignities(planet_positions, house_positions)
        mars = next(d for d in result if d.planet == "Mars")
        assert "Angular (H1)" in mars.accidental_dignities

    def test_cadent_house_penalty(self):
        from moira.dignities import calculate_dignities
        # Place Mars in H3 (cadent): ASC=0°, H3 starts at 60°; Mars at 65°
        planet_positions = [
            {"name": "Mars", "degree": 65.0},
            {"name": "Sun",  "degree": 0.0},
        ]
        house_positions = self._make_houses(0.0)
        result = calculate_dignities(planet_positions, house_positions)
        mars = next(d for d in result if d.planet == "Mars")
        assert "Cadent (H3)" in mars.accidental_dignities

    def test_retrograde_penalty(self):
        from moira.dignities import calculate_dignities
        planet_positions = [
            {"name": "Mars", "degree": 65.0, "is_retrograde": True},
            {"name": "Sun",  "degree": 0.0},
        ]
        result = calculate_dignities(planet_positions, self._make_houses())
        mars = next(d for d in result if d.planet == "Mars")
        assert "Retrograde" in mars.accidental_dignities

    def test_cazimi_bonus(self):
        from moira.dignities import calculate_dignities
        # Venus within 0.1° of Sun → Cazimi
        sun_lon = 100.0
        planet_positions = [
            {"name": "Sun",   "degree": sun_lon},
            {"name": "Venus", "degree": sun_lon + 0.1},
        ]
        result = calculate_dignities(planet_positions, self._make_houses())
        venus = next(d for d in result if d.planet == "Venus")
        assert "Cazimi" in venus.accidental_dignities

    def test_combust_penalty(self):
        from moira.dignities import calculate_dignities
        sun_lon = 100.0
        planet_positions = [
            {"name": "Sun",   "degree": sun_lon},
            {"name": "Venus", "degree": sun_lon + 5.0},  # 5° from Sun → combust
        ]
        result = calculate_dignities(planet_positions, self._make_houses())
        venus = next(d for d in result if d.planet == "Venus")
        assert "Combust" in venus.accidental_dignities

    def test_mutual_reception_detection(self):
        from moira.dignities import calculate_dignities
        # Venus in Aries (Mars rules Aries) + Mars in Taurus (Venus rules Taurus) → mutual reception
        planet_positions = [
            {"name": "Venus", "degree": 15.0},   # Aries (0–30)
            {"name": "Mars",  "degree": 45.0},   # Taurus (30–60)
            {"name": "Sun",   "degree": 200.0},
        ]
        result = calculate_dignities(planet_positions, self._make_houses())
        venus = next(d for d in result if d.planet == "Venus")
        mars_d = next(d for d in result if d.planet == "Mars")
        assert any("Mutual Reception" in acc for acc in venus.accidental_dignities)
        assert any("Mutual Reception" in acc for acc in mars_d.accidental_dignities)

    def test_total_score_equals_sum(self):
        from moira.dignities import calculate_dignities
        planet_positions = [
            {"name": "Sun",     "degree": 130.0},
            {"name": "Moon",    "degree": 45.0},
            {"name": "Mars",    "degree": 5.0},
            {"name": "Mercury", "degree": 65.0},
            {"name": "Venus",   "degree": 340.0},
            {"name": "Jupiter", "degree": 100.0},
            {"name": "Saturn",  "degree": 195.0},
        ]
        result = calculate_dignities(planet_positions, self._make_houses())
        for d in result:
            assert d.total_score == d.essential_score + d.accidental_score, (
                f"{d.planet}: total={d.total_score}, "
                f"essential={d.essential_score}, accidental={d.accidental_score}"
            )

    def test_traditional_planet_order(self):
        from moira.dignities import calculate_dignities
        planet_positions = [
            {"name": "Saturn",  "degree": 200.0},
            {"name": "Mars",    "degree": 5.0},
            {"name": "Sun",     "degree": 130.0},
            {"name": "Moon",    "degree": 45.0},
            {"name": "Mercury", "degree": 65.0},
            {"name": "Venus",   "degree": 340.0},
            {"name": "Jupiter", "degree": 100.0},
        ]
        result = calculate_dignities(planet_positions, self._make_houses())
        expected_order = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
        actual_order = [d.planet for d in result]
        assert actual_order == expected_order

    def test_sect_light_day(self):
        from moira.dignities import sect_light, is_day_chart
        # Sun above horizon: sun_lon in houses 7–12 means (sun - asc) mod 360 >= 180
        # ASC=0°, Sun=180° → (180-0)%360=180 >= 180 → day chart
        assert sect_light(180.0, 0.0) == "Sun"
        assert is_day_chart(180.0, 0.0) is True

    def test_sect_light_night(self):
        from moira.dignities import sect_light, is_day_chart
        # ASC=0°, Sun=90° → (90-0)%360=90 < 180 → night chart
        assert sect_light(90.0, 0.0) == "Moon"
        assert is_day_chart(90.0, 0.0) is False

    def test_is_in_hayz_sun_day_chart(self):
        from moira.dignities import is_in_hayz
        # Sun (diurnal) in a day chart, in a masculine sign (Leo=fire), above horizon (H9)
        assert is_in_hayz("Sun", "Leo", 9, is_day_chart=True) is True

    def test_is_in_hayz_sun_night_chart_fails(self):
        from moira.dignities import is_in_hayz
        # Sun (diurnal) in a night chart → fails sect condition
        assert is_in_hayz("Sun", "Leo", 9, is_day_chart=False) is False

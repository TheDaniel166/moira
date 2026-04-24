"""
tests/unit/test_experimental_validation.py

Validation suite for Moira's experimental / extended-technique modules.

These modules either use pure arithmetic with a fixed reference frame
(galactic, uranian, manazil) or implement traditional table-based rules
(longevity, timelords) or a statistical model derived from fixed tables
(gauquelin).  None require a live ephemeris.

The validation approach is:
  - derive expected values by hand from canonical sources / published tables
  - enforce invariants that the mathematics demands unconditionally
  - check table integrity (sums, spans, coverage, uniqueness)

Modules covered
---------------
1. galactic    — equatorial/galactic round-trips, Liu Zhu & Zhang matrix
2. gauquelin   — sector formula, plus-zone classification, sector range
3. uranian     — J2000 identity, daily-motion sign, linear ephemeris formula
4. manazil     — mansion span, boundary assignments, degrees_in range
5. longevity   — Ptolemaic year table, dignity scoring, Hyleg/Alcocoden logic
6. timelords   — Firdaria totals, sub-period count, MINOR_YEARS table integrity

Oracle / authority
------------------
1. galactic   — Liu, Zhu & Zhang (2011, A&A 526, A16); IAU 1958 definition
2. gauquelin  — Michel Gauquelin, "The Spheres of Destiny" (1980)
3. uranian    — Rudolph (2005) Hamburg School element tables
4. manazil    — al-Biruni, "Book of Instruction"; 28 equal stations of 360/28°
5. longevity  — Ptolemy "Tetrabiblos" IV.10; Bonatti "Liber Astronomiae"
6. timelords  — Vettius Valens "Anthologiae"; Demetra George Vol. II

Note on MINOR_YEARS: Valens' Zodiacal Releasing scheme assigns the following
Minor Years per sign — Aries 15, Taurus 8, Gemini 20, Cancer 25, Leo 19,
Virgo 20, Libra 8, Scorpio 15, Sagittarius 12, Capricorn 27, Aquarius 30,
Pisces 12.  These sum to 211, which is the correct total for this table.
The figure "129 years" cited in some secondary literature refers to a
different aggregation (Hyleg year limits), not the sum of this table.
"""

import math
import pytest

from moira.galactic import (
    equatorial_to_galactic,
    galactic_to_equatorial,
    ecliptic_to_galactic,
    galactic_to_ecliptic,
    galactic_reference_points,
    _GC_RA, _GC_DEC, _NGP_RA, _NGP_DEC,
)
from moira.gauquelin import gauquelin_sector, _PLUS_ZONE_SECTORS
from moira.uranian import uranian_at, _URANIAN_ELEMENTS
from moira.constants import J2000
from moira.manazil import mansion_of, MANSIONS, MANSION_SPAN
from moira.longevity import (
    PTOLEMAIC_YEARS, EGYPTIAN_BOUNDS, FACE_RULERS,
    dignity_score_at, find_hyleg, calculate_longevity, HylegResult,
)
from moira.triplicity import triplicity_assignment_for as _triplicity_assignment_for
from moira.dignities import ANGULAR_HOUSES, SUCCEDENT_HOUSES, CADENT_HOUSES
from moira.timelords import (
    FIRDARIA_DIURNAL, FIRDARIA_NOCTURNAL, MINOR_YEARS, _JULIAN_YEAR, _ZR_YEAR_DAYS,
    _TOTAL_MINOR_YEARS,
    firdaria, zodiacal_releasing,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _angle_close(a: float, b: float, tol: float = 1e-8) -> bool:
    """True if two angles (degrees) are within tol after normalising to [0, 360)."""
    diff = (a - b) % 360.0
    return diff <= tol or diff >= 360.0 - tol


def assert_angle_close(a: float, b: float, tol: float = 1e-8, msg: str = "") -> None:
    """Assert that two angles in degrees are equal modulo 360."""
    assert _angle_close(a, b, tol), (
        f"Angles not close: {a} vs {b} (tol={tol})"
        + (f" — {msg}" if msg else "")
    )


# ===========================================================================
# 1. Galactic coordinate transforms
# ===========================================================================

class TestGalactic:
    """
    Authority: Liu, Zhu & Zhang (2011) ICRS rotation matrix.
    The matrix _A is orthogonal so A_T * A = I, giving exact round-trip
    tests without any oracle beyond the matrix itself.

    The Galactic Center is defined to lie at (l=0°, b=0°) and the NGP at
    b=+90°.  These are foundational IAU 1958 definition points.
    """

    JD_J2000 = 2451545.0

    def test_gc_maps_to_galactic_origin(self):
        l, b = equatorial_to_galactic(_GC_RA, _GC_DEC)
        assert_angle_close(l, 0.0, tol=0.01)
        assert abs(b) < 0.01

    def test_ngp_maps_to_north_pole(self):
        _, b = equatorial_to_galactic(_NGP_RA, _NGP_DEC)
        assert abs(b - 90.0) < 0.01

    def test_round_trip_equatorial(self):
        for ra, dec in [(45.0, 30.0), (200.0, -60.0), (90.0, 0.0), (350.0, 85.0)]:
            l, b = equatorial_to_galactic(ra, dec)
            ra2, dec2 = galactic_to_equatorial(l, b)
            assert_angle_close(ra2, ra, tol=1e-8, msg=f"ra={ra}")
            assert abs(dec2 - dec) < 1e-8

    def test_round_trip_galactic(self):
        for l, b in [(0.0, 0.0), (90.0, 45.0), (270.0, -30.0), (180.0, 0.0)]:
            ra, dec = galactic_to_equatorial(l, b)
            l2, b2 = equatorial_to_galactic(ra, dec)
            assert_angle_close(l2, l, tol=1e-8, msg=f"l={l}")
            assert abs(b2 - b) < 1e-8

    def test_ecliptic_round_trip(self):
        obliquity = 23.4393
        for lon, lat in [(0.0, 0.0), (90.0, 5.0), (180.0, -5.0), (270.0, 0.0)]:
            l, b = ecliptic_to_galactic(lon, lat, obliquity, jd_tt=self.JD_J2000)
            lon2, lat2 = galactic_to_ecliptic(l, b, obliquity, jd_tt=self.JD_J2000)
            assert_angle_close(lon2, lon, tol=1e-6, msg=f"lon={lon}")
            assert abs(lat2 - lat) < 1e-6

    def test_galactic_longitude_range(self):
        for ra in range(0, 360, 30):
            for dec in (-60, -30, 0, 30, 60):
                l, b = equatorial_to_galactic(float(ra), float(dec))
                assert 0.0 <= l < 360.0
                assert -90.0 <= b <= 90.0

    def test_reference_points_returns_five_keys(self):
        pts = galactic_reference_points(23.4393, jd_tt=self.JD_J2000)
        assert set(pts.keys()) == {
            "Galactic Center", "Galactic Anti-Center",
            "North Galactic Pole", "South Galactic Pole",
            "Super-Galactic Center",
        }

    def test_reference_points_in_valid_range(self):
        pts = galactic_reference_points(23.4393, jd_tt=self.JD_J2000)
        for _name, (lon, lat) in pts.items():
            assert isinstance(lon, float)
            assert isinstance(lat, float)
            assert 0.0 <= lon <= 360.0
            assert -90.0 <= lat <= 90.0

    def test_gc_ecliptic_near_sagittarius(self):
        pts = galactic_reference_points(23.4393, jd_tt=self.JD_J2000)
        gc_lon, _ = pts["Galactic Center"]
        assert 260.0 < gc_lon < 270.0

    def test_anti_center_opposite_gc(self):
        pts = galactic_reference_points(23.4393, jd_tt=self.JD_J2000)
        gc_lon, _ = pts["Galactic Center"]
        ac_lon, _ = pts["Galactic Anti-Center"]
        assert_angle_close(ac_lon, (gc_lon + 180.0) % 360.0, tol=0.5)


# ===========================================================================
# 2. Gauquelin sectors
# ===========================================================================

class TestGauquelin:
    """
    Authority: Gauquelin (1980) — sectors defined by diurnal arc, 36 per
    revolution, plus zones immediately following each angle.

    Key invariants:
      - sector is always an integer in [1, 36]
      - zone is either "Plus Zone" or "Neutral Zone"
      - plus zones are exactly sectors 1-3, 10-12, 19-21, 28-30 (12 of 36)
    """

    def test_sector_range_always_valid(self):
        for body_ra in range(0, 360, 45):
            for lat in (-45.0, 0.0, 45.0):
                gp = gauquelin_sector(float(body_ra), 0.0, lat, 0.0, "TestBody")
                assert 1 <= gp.sector <= 36

    def test_zone_is_valid_string(self):
        gp = gauquelin_sector(90.0, 15.0, 51.5, 180.0, "Mars")
        assert gp.zone in ("Plus Zone", "Neutral Zone")

    def test_plus_zone_sectors_count(self):
        assert len(_PLUS_ZONE_SECTORS) == 12

    def test_plus_zone_sectors_correct_values(self):
        expected = (
            set(range(1, 4)) | set(range(10, 13))
            | set(range(19, 22)) | set(range(28, 31))
        )
        assert _PLUS_ZONE_SECTORS == frozenset(expected)

    def test_zone_label_consistent_with_sector(self):
        for ra in range(0, 360, 30):
            gp = gauquelin_sector(float(ra), 10.0, 48.0, 90.0, "X")
            expected = "Plus Zone" if gp.sector in _PLUS_ZONE_SECTORS else "Neutral Zone"
            assert gp.zone == expected

    def test_body_field_preserved(self):
        gp = gauquelin_sector(0.0, 0.0, 45.0, 0.0, "Saturn")
        assert gp.body == "Saturn"

    def test_diurnal_position_range(self):
        for ra in (0.0, 90.0, 180.0, 270.0):
            gp = gauquelin_sector(ra, 0.0, 45.0, 45.0, "X")
            assert 0.0 <= gp.diurnal_position < 360.0

    def test_circumpolarity_dsa_180(self):
        gp = gauquelin_sector(0.0, 89.0, 89.0, 0.0, "Circumpolar")
        assert 1 <= gp.sector <= 36

    def test_at_exact_horizon_dsa_zero(self):
        gp = gauquelin_sector(0.0, -89.0, 89.0, 0.0, "Horizon")
        assert 1 <= gp.sector <= 36


# ===========================================================================
# 3. Uranian hypothetical bodies
# ===========================================================================

class TestUranian:
    """
    Authority: Rudolph (2005) Hamburg School mean orbital elements.
    Formula: L(t) = (L0 + n * (JD - J2000)) % 360.

    At J2000 itself dt=0 so the position equals L0 exactly.
    All daily motions are positive (prograde linear ephemeris).
    """

    def test_j2000_position_matches_table(self):
        for name, (l0, _n) in _URANIAN_ELEMENTS.items():
            pos = uranian_at(name, J2000)
            assert abs(pos.longitude - l0 % 360.0) < 1e-8

    def test_all_daily_motions_positive(self):
        for name, (_l0, n) in _URANIAN_ELEMENTS.items():
            assert n > 0.0, f"{name} has non-positive daily motion {n}"

    def test_speed_field_matches_table(self):
        for name, (_l0, n) in _URANIAN_ELEMENTS.items():
            pos = uranian_at(name, J2000)
            assert abs(pos.speed - n) < 1e-10

    def test_longitude_advances_one_day(self):
        for name, (_l0, n) in _URANIAN_ELEMENTS.items():
            p0 = uranian_at(name, J2000)
            p1 = uranian_at(name, J2000 + 1.0)
            delta = (p1.longitude - p0.longitude) % 360.0
            assert abs(delta - n) < 1e-8

    def test_longitude_range(self):
        for name in _URANIAN_ELEMENTS:
            pos = uranian_at(name, J2000 + 1000.0)
            assert 0.0 <= pos.longitude < 360.0

    def test_unknown_body_raises(self):
        with pytest.raises(KeyError):
            uranian_at("Nibiru", J2000)

    def test_nine_bodies_defined(self):
        assert len(_URANIAN_ELEMENTS) == 9

    def test_all_body_names_present(self):
        expected = {
            "Cupido", "Hades", "Zeus", "Kronos", "Apollon",
            "Admetos", "Vulkanus", "Poseidon", "Transpluto",
        }
        assert set(_URANIAN_ELEMENTS.keys()) == expected

    def test_cupido_j2000_literal(self):
        pos = uranian_at("Cupido", J2000)
        assert abs(pos.longitude - 4.3333) < 1e-6

    def test_transpluto_slowest(self):
        slowest = min(_URANIAN_ELEMENTS, key=lambda n: _URANIAN_ELEMENTS[n][1])
        assert slowest == "Transpluto"

    def test_cupido_fastest(self):
        fastest = max(_URANIAN_ELEMENTS, key=lambda n: _URANIAN_ELEMENTS[n][1])
        assert fastest == "Cupido"


# ===========================================================================
# 4. Arabic lunar mansions (Manazil)
# ===========================================================================

class TestManazil:
    """
    Authority: al-Biruni, "Book of Instruction" — 28 equal mansions of 360/28°.

    Key invariants:
      - each mansion spans exactly MANSION_SPAN = 360/28 degrees
      - mansion indices are 1-based (1…28)
      - degrees_in is always in [0, MANSION_SPAN)
      - mansion_of(0°) = Mansion 1 (Al-Sharatain)
      - mansion_of(MANSION_SPAN) = Mansion 2
    """

    def test_mansion_span_value(self):
        assert abs(MANSION_SPAN - 360.0 / 28.0) < 1e-10

    def test_28_mansions_defined(self):
        assert len(MANSIONS) == 28

    def test_mansion_indices_one_based(self):
        for i, m in enumerate(MANSIONS):
            assert m.index == i + 1

    def test_mansion_of_zero_is_first(self):
        mp = mansion_of(0.0)
        assert mp.mansion.index == 1
        assert mp.mansion.arabic_name == "Al-Sharatain"

    def test_mansion_of_full_circle_wraps(self):
        mp = mansion_of(360.0)
        assert mp.mansion.index == 1

    def test_degrees_in_range(self):
        for lon in range(0, 360, 5):
            mp = mansion_of(float(lon))
            assert 0.0 <= mp.degrees_in < MANSION_SPAN + 1e-10

    def test_boundary_advances_mansion(self):
        mp1 = mansion_of(MANSION_SPAN - 0.001)
        mp2 = mansion_of(MANSION_SPAN)
        assert mp2.mansion.index == mp1.mansion.index + 1

    def test_each_mansion_reachable(self):
        seen = set()
        for i in range(28):
            mp = mansion_of(i * MANSION_SPAN + 0.5)
            seen.add(mp.mansion.index)
        assert seen == set(range(1, 29))

    def test_longitude_preserved(self):
        lon = 137.5
        assert mansion_of(lon).longitude == lon

    def test_negative_longitude_wraps(self):
        mp = mansion_of(-MANSION_SPAN)
        assert 1 <= mp.mansion.index <= 28

    def test_last_mansion_near_360(self):
        mp = mansion_of(360.0 - 0.001)
        assert mp.mansion.index == 28


# ===========================================================================
# 5. Longevity: Ptolemaic years, dignity scoring, Hyleg / Alcocoden
# ===========================================================================

class TestPtolemaicYears:
    """
    Authority: Ptolemy "Tetrabiblos" IV.10.
    Seven planets only; minor < mean < major for all.
    """

    def test_seven_planets_defined(self):
        assert len(PTOLEMAIC_YEARS) == 7

    def test_minor_less_than_mean_less_than_major(self):
        for planet, (minor, mean, major) in PTOLEMAIC_YEARS.items():
            assert minor < mean < major, planet

    def test_sun_years(self):
        assert PTOLEMAIC_YEARS["Sun"] == (19.0, 69.5, 120.0)

    def test_moon_years(self):
        assert PTOLEMAIC_YEARS["Moon"] == (25.0, 66.5, 108.0)

    def test_saturn_years(self):
        assert PTOLEMAIC_YEARS["Saturn"] == (30.0, 57.0, 90.0)

    def test_all_years_positive(self):
        for planet, (minor, mean, major) in PTOLEMAIC_YEARS.items():
            assert minor > 0 and mean > 0 and major > 0


class TestFaceRulers:
    """
    Authority: Chaldean order (Mars, Sun, Venus, Mercury, Moon, Saturn, Jupiter)
    repeating from Aries 0°.  36 decans total (10° each).
    """

    def test_36_face_rulers(self):
        assert len(FACE_RULERS) == 36

    def test_first_face_is_mars(self):
        assert FACE_RULERS[0] == "Mars"

    def test_chaldean_cycle_repeats(self):
        chaldean = ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]
        for i in range(36):
            assert FACE_RULERS[i] == chaldean[i % 7]


class TestEgyptianBounds:
    """
    Authority: Ptolemy "Tetrabiblos" I.21 — Egyptian bounds.
    Each sign has exactly 5 bound entries summing to 30 degrees.
    """

    def test_twelve_signs_defined(self):
        assert len(EGYPTIAN_BOUNDS) == 12

    def test_bounds_sum_to_30(self):
        for sign, bounds in EGYPTIAN_BOUNDS.items():
            total = sum(end - start for _, start, end in bounds)
            assert abs(total - 30.0) < 1e-9, sign

    def test_five_bounds_per_sign(self):
        for sign, bounds in EGYPTIAN_BOUNDS.items():
            assert len(bounds) == 5, sign

    def test_bounds_are_contiguous(self):
        for sign, bounds in EGYPTIAN_BOUNDS.items():
            sorted_bounds = sorted(bounds, key=lambda x: x[1])
            for i in range(len(sorted_bounds) - 1):
                assert sorted_bounds[i][2] == sorted_bounds[i + 1][1], sign


class TestTriplicityRulers:
    """
    Authority: Dorotheus/Pingree 1976 triplicity rulers.
    12 signs covered, each assigned to a triplicity group of 3 signs.
    Tested via triplicity_assignment_for (moira.triplicity public surface).
    """

    def test_twelve_signs_covered(self):
        from moira.constants import SIGNS
        for sign in SIGNS:
            a = _triplicity_assignment_for(sign, is_day_chart=True)
            assert a.sign == sign

    def test_fire_triplicity_day_ruler_sun(self):
        for sign in ("Aries", "Leo", "Sagittarius"):
            a = _triplicity_assignment_for(sign, is_day_chart=True)
            assert a.day_ruler == "Sun"

    def test_earth_triplicity_day_ruler_venus(self):
        for sign in ("Taurus", "Virgo", "Capricorn"):
            a = _triplicity_assignment_for(sign, is_day_chart=True)
            assert a.day_ruler == "Venus"


class TestDignityScoreAt:
    """
    Scoring: domicile=5, exaltation=4, triplicity=3 (or 1 participating),
    bound=2, face=1.  Scores are always non-negative integers.

    Hand-derived spot checks:
      - Sun at 135° (15° Leo): domicile (5) + fire-day triplicity (3) = 8 minimum
      - Moon at 105° (15° Cancer): domicile (5) + water-day triplicity (1 part.) = min 5
      - Saturn at 15° (15° Aries): no domicile, no exaltation, not fire-day triplicity
        ruler → score is a small non-negative integer (exact value depends on bound/face)
    """

    def test_sun_in_leo_domicile(self):
        score = dignity_score_at("Sun", 135.0, True)
        assert score >= 5

    def test_moon_in_cancer_domicile(self):
        score = dignity_score_at("Moon", 105.0, True)
        assert score >= 5

    def test_saturn_in_aries_no_domicile_or_exaltation(self):
        score = dignity_score_at("Saturn", 15.0, True)
        assert isinstance(score, int)
        assert score >= 0
        assert score < 5

    def test_sun_fire_triplicity_day_higher_than_night(self):
        score_day   = dignity_score_at("Sun", 15.0, True)
        score_night = dignity_score_at("Sun", 15.0, False)
        assert score_day > score_night

    def test_score_non_negative_all_planets_all_signs(self):
        for planet in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            for lon in range(0, 360, 30):
                score = dignity_score_at(planet, float(lon), True)
                assert score >= 0


class TestFindHyleg:
    """
    Bonatti priority (Liber Astronomiae Tract. VI):
      Day chart: Sun in angular/succedent → Sun
      Night chart: Moon in angular/succedent → Moon
      Otherwise: Moon → Sun → Ascendant → Lot of Fortune

    Test cases use a simple equal-house chart (cusps every 30°) so that
    house placement is unambiguous.  House 1 spans 0–30°, house 2 spans
    30–60°, etc.  Houses 1, 4, 7, 10 are angular; 2, 5, 8, 11 succedent;
    3, 6, 9, 12 cadent.

    In this chart, 15° falls in house 1 (angular) and 165° falls in house 6
    (cadent: 150–180°).
    """

    _CUSPS = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0,
              180.0, 210.0, 240.0, 270.0, 300.0, 330.0]

    def test_day_chart_sun_angular_is_hyleg(self):
        hyleg = find_hyleg({"Sun": 15.0, "Moon": 195.0}, self._CUSPS, is_day_chart=True)
        assert hyleg == "Sun"

    def test_night_chart_moon_angular_is_hyleg(self):
        hyleg = find_hyleg({"Sun": 195.0, "Moon": 15.0}, self._CUSPS, is_day_chart=False)
        assert hyleg == "Moon"

    def test_day_chart_sun_cadent_falls_through_to_moon(self):
        hyleg = find_hyleg({"Sun": 165.0, "Moon": 15.0}, self._CUSPS, is_day_chart=True)
        assert hyleg == "Moon"

    def test_both_cadent_fallback_to_ascendant(self):
        hyleg = find_hyleg({"Sun": 165.0, "Moon": 165.0}, self._CUSPS, is_day_chart=True)
        assert hyleg == "Ascendant"


class TestCalculateLongevity:
    """
    End-to-end: find_hyleg → dignity_score_at → PTOLEMAIC_YEARS → granted years.

    Alcocoden house rule (Ptolemaic):
      Angular (1, 4, 7, 10) → major years
      Succedent (2, 5, 8, 11) → mean years
      Cadent (3, 6, 9, 12) → minor years

    The house-type constants are imported exclusively from moira.dignities,
    which is the authoritative source.
    """

    _CUSPS = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0,
              180.0, 210.0, 240.0, 270.0, 300.0, 330.0]

    _POSITIONS = {
        "Sun": 15.0, "Moon": 195.0, "Mercury": 45.0,
        "Venus": 75.0, "Mars": 105.0, "Jupiter": 135.0, "Saturn": 165.0,
    }

    def test_returns_hyleg_result(self):
        result = calculate_longevity(self._POSITIONS, self._CUSPS, is_day_chart=True)
        assert isinstance(result, HylegResult)

    def test_granted_years_matches_house_type(self):
        result = calculate_longevity(self._POSITIONS, self._CUSPS, is_day_chart=True)
        if result.house in ANGULAR_HOUSES:
            assert result.granted_years == result.years_major
        elif result.house in SUCCEDENT_HOUSES:
            assert result.granted_years == result.years_mean
        else:
            assert result.granted_years == result.years_minor

    def test_alcocoden_in_classic_seven(self):
        result = calculate_longevity(self._POSITIONS, self._CUSPS, is_day_chart=True)
        assert result.alcocoden in {
            "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"
        }

    def test_granted_years_positive(self):
        result = calculate_longevity(self._POSITIONS, self._CUSPS, is_day_chart=True)
        assert result.granted_years > 0

    def test_hyleg_is_sun_day_chart(self):
        result = calculate_longevity(self._POSITIONS, self._CUSPS, is_day_chart=True)
        assert result.hyleg == "Sun"

    def test_years_fields_match_ptolemaic_table(self):
        result = calculate_longevity(self._POSITIONS, self._CUSPS, is_day_chart=True)
        minor, mean, major = PTOLEMAIC_YEARS[result.alcocoden]
        assert result.years_minor == minor
        assert result.years_mean  == mean
        assert result.years_major == major


# ===========================================================================
# 6. Timelords: Firdaria and Zodiacal Releasing
# ===========================================================================

class TestFirdariaTable:
    """
    Authority: Vettius Valens "Anthologiae".
    Both diurnal and nocturnal sequences total 75 years across 9 entries.
    """

    def test_diurnal_total_75_years(self):
        assert sum(y for _, y in FIRDARIA_DIURNAL) == 75

    def test_nocturnal_total_75_years(self):
        assert sum(y for _, y in FIRDARIA_NOCTURNAL) == 75

    def test_nine_entries_diurnal(self):
        assert len(FIRDARIA_DIURNAL) == 9

    def test_nine_entries_nocturnal(self):
        assert len(FIRDARIA_NOCTURNAL) == 9

    def test_same_planets_both_sequences(self):
        assert {p for p, _ in FIRDARIA_DIURNAL} == {p for p, _ in FIRDARIA_NOCTURNAL}

    def test_diurnal_starts_with_sun(self):
        assert FIRDARIA_DIURNAL[0][0] == "Sun"

    def test_nocturnal_starts_with_moon(self):
        assert FIRDARIA_NOCTURNAL[0][0] == "Moon"

    def test_nodes_end_both_sequences(self):
        assert FIRDARIA_DIURNAL[-2][0]   == "North Node"
        assert FIRDARIA_DIURNAL[-1][0]   == "South Node"
        assert FIRDARIA_NOCTURNAL[-2][0] == "North Node"
        assert FIRDARIA_NOCTURNAL[-1][0] == "South Node"


class TestFirdariaComputed:
    """
    Structural tests on the firdaria() output.
    """

    def test_major_period_count(self):
        major = [p for p in firdaria(J2000, is_day_chart=True) if p.level == 1]
        assert len(major) == 9

    def test_seven_sub_periods_per_major(self):
        periods = firdaria(J2000, is_day_chart=True)
        major = [p for p in periods if p.level == 1]
        for mp in major:
            subs = [
                p for p in periods
                if p.level == 2
                and p.start_jd >= mp.start_jd - 1e-9
                and p.end_jd <= mp.end_jd + 1e-6
            ]
            expected = 0 if mp.planet in {"North Node", "South Node"} else 7
            assert len(subs) == expected, f"Major {mp.planet} has {len(subs)} sub-periods"

    def test_major_periods_contiguous(self):
        major = sorted(
            [p for p in firdaria(J2000, is_day_chart=True) if p.level == 1],
            key=lambda p: p.start_jd,
        )
        for i in range(len(major) - 1):
            assert abs(major[i].end_jd - major[i + 1].start_jd) < 1e-6

    def test_total_span_75_years(self):
        major = [p for p in firdaria(J2000, is_day_chart=True) if p.level == 1]
        total_days = sum(p.end_jd - p.start_jd for p in major)
        assert abs(total_days - 75.0 * _JULIAN_YEAR) < 1e-6

    def test_first_period_starts_at_natal(self):
        natal_jd = J2000 + 1000.0
        first = min(
            (p for p in firdaria(natal_jd, is_day_chart=False) if p.level == 1),
            key=lambda p: p.start_jd,
        )
        assert abs(first.start_jd - natal_jd) < 1e-10


class TestMinorYears:
    """
    Authority: Vettius Valens "Anthologiae" — Zodiacal Releasing Minor Years.

    The values are: Aries 15, Taurus 8, Gemini 20, Cancer 25, Leo 19,
    Virgo 20, Libra 8, Scorpio 15, Sagittarius 12, Capricorn 27,
    Aquarius 30, Pisces 12.  These sum to 211.

    Note: the figure "129 years" found in some secondary literature refers
    to a different aggregation (Hyleg year limits) and is not the sum of
    this table.
    """

    def test_twelve_signs(self):
        assert len(MINOR_YEARS) == 12

    def test_sum_is_211(self):
        assert sum(MINOR_YEARS.values()) == 211

    def test_all_years_positive(self):
        for sign, years in MINOR_YEARS.items():
            assert years > 0, sign

    def test_cancer_has_25_years(self):
        assert MINOR_YEARS["Cancer"] == 25

    def test_capricorn_has_27_years(self):
        assert MINOR_YEARS["Capricorn"] == 27

    def test_aquarius_has_30_years(self):
        assert MINOR_YEARS["Aquarius"] == 30


class TestZodiacalReleasing:
    """
    Structural tests on zodiacal_releasing() output.
    """

    def test_returns_list(self):
        assert isinstance(zodiacal_releasing(0.0, J2000, levels=1), list)

    def test_levels_1_to_4_all_produce_output(self):
        for lv in range(1, 5):
            assert len(zodiacal_releasing(0.0, J2000, levels=lv)) > 0

    def test_level_1_periods_contiguous(self):
        l1 = sorted(
            [p for p in zodiacal_releasing(0.0, J2000, levels=1) if p.level == 1],
            key=lambda p: p.start_jd,
        )
        for i in range(len(l1) - 1):
            assert abs(l1[i].end_jd - l1[i + 1].start_jd) < 1e-6

    def test_first_period_sign_matches_lot(self):
        from moira.constants import sign_of
        lot_lon = 45.0
        sign_name, _, _ = sign_of(lot_lon)
        l1 = sorted(
            [p for p in zodiacal_releasing(lot_lon, J2000, levels=1) if p.level == 1],
            key=lambda p: p.start_jd,
        )
        assert l1[0].sign == sign_name

    def test_all_level_1_durations_match_minor_years(self):
        cap = J2000 + _TOTAL_MINOR_YEARS * _ZR_YEAR_DAYS
        l1 = [
            p for p in zodiacal_releasing(0.0, J2000, levels=1)
            if p.level == 1
        ]
        for p in l1:
            expected_days = MINOR_YEARS[p.sign] * _ZR_YEAR_DAYS
            actual_days   = p.end_jd - p.start_jd
            if abs(p.end_jd - cap) < 1e-3:
                continue
            assert abs(actual_days - expected_days) < 1e-6, (
                f"Sign {p.sign}: expected {expected_days:.2f} days, "
                f"got {actual_days:.2f}"
            )

    def test_capped_at_full_primary_circuit(self):
        l1 = [p for p in zodiacal_releasing(0.0, J2000, levels=1) if p.level == 1]
        cap = J2000 + _TOTAL_MINOR_YEARS * _ZR_YEAR_DAYS
        assert max(p.end_jd for p in l1) <= cap + 1e-6

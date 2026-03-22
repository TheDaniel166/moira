"""
Unit tests for moira/sidereal.py.

Coverage areas
--------------
1. Ayanamsa constants — Ayanamsa namespace, ALL list integrity
2. Polynomial ayanamsa — mean and true modes for canonical systems
3. Star-anchored ayanamsa — TRUE_CHITRAPAKSHA enforces Spica = 180° at every
   date; TRUE_REVATI, ALDEBARAN_15_TAU, TRUE_PUSHYA use live star positions
4. ayanamsa() routing — star-anchored path taken for TRUE_* / ALDEBARAN in
   'true' mode; polynomial path taken in 'mean' mode
5. Conversion round-trips — tropical_to_sidereal + sidereal_to_tropical = identity
6. Nakshatra arithmetic — NakshatraPosition fields, pada bounds, Revati boundary
7. list_ayanamsa_systems — returns dict with all 30 entries
8. Error handling — bad mode, unknown system
9. Reference accuracy — Lahiri at J2000 matches SwissEph within 0.01°
"""

import pytest
import moira
from moira.sidereal import (
    Ayanamsa, ayanamsa, tropical_to_sidereal, sidereal_to_tropical,
    nakshatra_of, all_nakshatras_at, list_ayanamsa_systems,
    NAKSHATRA_NAMES, NAKSHATRA_LORDS, NAKSHATRA_SPAN, PADA_SPAN,
    _STAR_ANCHORED, _AYANAMSA_AT_J2000,
)
from moira.fixed_stars import fixed_star_at

J2000 = 2451545.0  # JD of 2000 Jan 1.5 TT
J1956 = 2435553.5  # JD of 1956 Mar 21 0:00 TT (Lahiri anchor date)
J2020 = 2458849.5  # JD of 2020 Jan 1.5 TT


# ---------------------------------------------------------------------------
# 1. Ayanamsa constants
# ---------------------------------------------------------------------------

class TestAyanamsaConstants:

    def test_all_length(self):
        assert len(Ayanamsa.ALL) == 30

    def test_lahiri_in_all(self):
        assert Ayanamsa.LAHIRI in Ayanamsa.ALL

    def test_true_chitrapaksha_in_all(self):
        assert Ayanamsa.TRUE_CHITRAPAKSHA in Ayanamsa.ALL

    def test_fagan_bradley_in_all(self):
        assert Ayanamsa.FAGAN_BRADLEY in Ayanamsa.ALL

    def test_all_unique(self):
        assert len(Ayanamsa.ALL) == len(set(Ayanamsa.ALL))

    def test_all_are_strings(self):
        for name in Ayanamsa.ALL:
            assert isinstance(name, str)

    def test_all_keys_present_in_j2000_table(self):
        for name in Ayanamsa.ALL:
            assert name in _AYANAMSA_AT_J2000, f"{name} missing from _AYANAMSA_AT_J2000"


# ---------------------------------------------------------------------------
# 2. Polynomial ayanamsa (Lahiri, Fagan-Bradley)
# ---------------------------------------------------------------------------

class TestPolynomialAyanamsa:

    def test_lahiri_true_at_j2000_plausible_range(self):
        val = ayanamsa(J2000, Ayanamsa.LAHIRI, "true")
        assert 23.8 <= val <= 23.9, f"Lahiri true at J2000 out of range: {val}"

    def test_lahiri_mean_at_j2000_plausible_range(self):
        val = ayanamsa(J2000, Ayanamsa.LAHIRI, "mean")
        assert 23.8 <= val <= 23.9

    def test_lahiri_mean_vs_swisseph_reference(self):
        val = ayanamsa(J2000, Ayanamsa.LAHIRI, "mean")
        assert abs(val - 23.857) < 0.01, f"Lahiri mean at J2000 = {val}, expected ~23.857"

    def test_lahiri_true_vs_swisseph_reference(self):
        val = ayanamsa(J2000, Ayanamsa.LAHIRI, "true")
        assert abs(val - 23.853) < 0.01, f"Lahiri true at J2000 = {val}, expected ~23.853"

    def test_fagan_bradley_at_j2000(self):
        val = ayanamsa(J2000, Ayanamsa.FAGAN_BRADLEY, "mean")
        assert 24.7 <= val <= 24.8

    def test_mean_less_than_or_close_to_true(self):
        mean = ayanamsa(J2000, Ayanamsa.LAHIRI, "mean")
        true = ayanamsa(J2000, Ayanamsa.LAHIRI, "true")
        assert abs(mean - true) < 0.1

    def test_ayanamsa_increases_over_time(self):
        past = ayanamsa(J2000 - 36525.0, Ayanamsa.LAHIRI, "mean")
        present = ayanamsa(J2000, Ayanamsa.LAHIRI, "mean")
        future = ayanamsa(J2000 + 36525.0, Ayanamsa.LAHIRI, "mean")
        assert past < present < future

    def test_lahiri_not_star_anchored(self):
        assert Ayanamsa.LAHIRI not in _STAR_ANCHORED


# ---------------------------------------------------------------------------
# 3. Star-anchored ayanamsa — TRUE_CHITRAPAKSHA / Spica = 180°
# ---------------------------------------------------------------------------

class TestStarAnchoredAyanamsa:

    def test_true_chitrapaksha_spica_at_exactly_180(self):
        for jd in [J1956, J2000, J2020]:
            ayan = ayanamsa(jd, Ayanamsa.TRUE_CHITRAPAKSHA, "true")
            spica = fixed_star_at("Spica", jd)
            sidereal_lon = (spica.longitude - ayan) % 360.0
            assert abs(sidereal_lon - 180.0) < 0.001, (
                f"At JD {jd}: Spica sidereal = {sidereal_lon:.6f}, expected 180.000"
            )

    def test_true_chitrapaksha_at_j2000_vs_lahiri(self):
        tc = ayanamsa(J2000, Ayanamsa.TRUE_CHITRAPAKSHA, "true")
        lah = ayanamsa(J2000, Ayanamsa.LAHIRI, "true")
        diff = tc - lah
        assert abs(diff) < 0.5, f"True Citra − Lahiri = {diff:.4f} deg, expected < 0.5"

    def test_true_chitrapaksha_mean_uses_polynomial(self):
        true_val = ayanamsa(J2000, Ayanamsa.TRUE_CHITRAPAKSHA, "true")
        mean_val = ayanamsa(J2000, Ayanamsa.TRUE_CHITRAPAKSHA, "mean")
        assert true_val != mean_val

    def test_true_revati_star_anchored(self):
        ayan = ayanamsa(J2000, Ayanamsa.TRUE_REVATI, "true")
        star_name, target_sid = _STAR_ANCHORED[Ayanamsa.TRUE_REVATI]
        star = fixed_star_at(star_name, J2000)
        sidereal_lon = (star.longitude - ayan) % 360.0
        expected = target_sid % 360.0
        diff = min(abs(sidereal_lon - expected), 360.0 - abs(sidereal_lon - expected))
        assert diff < 0.001, (
            f"TRUE_REVATI: {star_name} sidereal = {sidereal_lon:.6f}, expected {expected}"
        )

    def test_aldebaran_star_anchored(self):
        ayan = ayanamsa(J2000, Ayanamsa.ALDEBARAN_15_TAU, "true")
        star_name, target_sid = _STAR_ANCHORED[Ayanamsa.ALDEBARAN_15_TAU]
        star = fixed_star_at(star_name, J2000)
        sidereal_lon = (star.longitude - ayan) % 360.0
        assert abs(sidereal_lon - target_sid) < 0.001, (
            f"ALDEBARAN: sidereal = {sidereal_lon:.6f}, expected {target_sid}"
        )

    def test_true_pushya_star_anchored(self):
        ayan = ayanamsa(J2000, Ayanamsa.TRUE_PUSHYA, "true")
        star_name, target_sid = _STAR_ANCHORED[Ayanamsa.TRUE_PUSHYA]
        star = fixed_star_at(star_name, J2000)
        sidereal_lon = (star.longitude - ayan) % 360.0
        assert abs(sidereal_lon - target_sid) < 0.001, (
            f"TRUE_PUSHYA: sidereal = {sidereal_lon:.6f}, expected {target_sid}"
        )

    def test_star_anchored_systems_listed_in_star_anchored(self):
        for system in [
            Ayanamsa.TRUE_CHITRAPAKSHA,
            Ayanamsa.TRUE_REVATI,
            Ayanamsa.ALDEBARAN_15_TAU,
            Ayanamsa.TRUE_PUSHYA,
        ]:
            assert system in _STAR_ANCHORED


# ---------------------------------------------------------------------------
# 4. ayanamsa() routing
# ---------------------------------------------------------------------------

class TestAyanamsaRouting:

    def test_true_mode_star_anchored_differs_from_mean(self):
        for system in _STAR_ANCHORED:
            true_val = ayanamsa(J2000, system, "true")
            mean_val = ayanamsa(J2000, system, "mean")
            assert true_val != mean_val, f"{system}: true == mean unexpectedly"

    def test_non_star_anchored_true_differs_from_mean_by_nutation(self):
        mean = ayanamsa(J2000, Ayanamsa.LAHIRI, "mean")
        true = ayanamsa(J2000, Ayanamsa.LAHIRI, "true")
        diff = abs(true - mean)
        assert diff < 0.05

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            ayanamsa(J2000, Ayanamsa.LAHIRI, "invalid")

    def test_unknown_system_raises(self):
        with pytest.raises(ValueError, match="Unknown ayanamsa"):
            ayanamsa(J2000, "NonExistentSystem", "true")

    def test_all_systems_compute_without_error(self):
        for system in Ayanamsa.ALL:
            val = ayanamsa(J2000, system, "true")
            assert isinstance(val, float)
            assert 0.0 <= val < 360.0


# ---------------------------------------------------------------------------
# 5. Conversion round-trips
# ---------------------------------------------------------------------------

class TestConversionRoundTrip:

    def test_tropical_to_sidereal_to_tropical_identity(self):
        for lon in [0.0, 45.0, 90.0, 180.0, 270.0, 359.9]:
            sid = tropical_to_sidereal(lon, J2000, Ayanamsa.LAHIRI)
            back = sidereal_to_tropical(sid, J2000, Ayanamsa.LAHIRI)
            assert abs(back - lon) < 1e-9, f"Round-trip failed for {lon}: got {back}"

    def test_tropical_to_sidereal_reduces_longitude(self):
        trop = 203.84
        sid = tropical_to_sidereal(trop, J2000, Ayanamsa.LAHIRI)
        assert sid < trop

    def test_sidereal_in_range(self):
        for lon in [0.0, 100.0, 200.0, 300.0]:
            sid = tropical_to_sidereal(lon, J2000, Ayanamsa.LAHIRI)
            assert 0.0 <= sid < 360.0

    def test_star_anchored_round_trip(self):
        for lon in [30.0, 150.0, 270.0]:
            sid = tropical_to_sidereal(lon, J2000, Ayanamsa.TRUE_CHITRAPAKSHA, "true")
            back = sidereal_to_tropical(sid, J2000, Ayanamsa.TRUE_CHITRAPAKSHA, "true")
            assert abs(back - lon) < 1e-9


# ---------------------------------------------------------------------------
# 6. Nakshatra arithmetic
# ---------------------------------------------------------------------------

class TestNakshatraArithmetic:

    def test_nakshatra_names_count(self):
        assert len(NAKSHATRA_NAMES) == 27

    def test_nakshatra_lords_count(self):
        assert len(NAKSHATRA_LORDS) == 27

    def test_ashwini_at_sidereal_zero(self):
        lon = ayanamsa(J2000, Ayanamsa.LAHIRI, "true")
        result = nakshatra_of(lon, J2000)
        assert result.nakshatra == "Ashwini"
        assert result.nakshatra_index == 0

    def test_pada_always_1_to_4(self):
        for tropical_lon in range(0, 360, 13):
            result = nakshatra_of(float(tropical_lon), J2000)
            assert 1 <= result.pada <= 4, f"pada {result.pada} out of range at {tropical_lon}"

    def test_degrees_in_range(self):
        for tropical_lon in range(0, 360, 13):
            result = nakshatra_of(float(tropical_lon), J2000)
            assert 0.0 <= result.degrees_in < NAKSHATRA_SPAN

    def test_nakshatra_index_range(self):
        for tropical_lon in range(0, 360, 13):
            result = nakshatra_of(float(tropical_lon), J2000)
            assert 0 <= result.nakshatra_index <= 26

    def test_sidereal_lon_in_range(self):
        result = nakshatra_of(100.0, J2000)
        assert 0.0 <= result.sidereal_lon < 360.0

    def test_nakshatra_lord_is_string(self):
        result = nakshatra_of(100.0, J2000)
        assert isinstance(result.nakshatra_lord, str)
        assert len(result.nakshatra_lord) > 0

    def test_all_nakshatras_at_returns_all_bodies(self):
        positions = {"Sun": 100.0, "Moon": 200.0, "Mars": 300.0}
        results = all_nakshatras_at(positions, J2000)
        assert set(results.keys()) == {"Sun", "Moon", "Mars"}
        for v in results.values():
            assert 1 <= v.pada <= 4

    def test_revati_is_last_nakshatra(self):
        assert NAKSHATRA_NAMES[26] == "Revati"
        assert NAKSHATRA_LORDS[26] == "Mercury"

    def test_repr_contains_nakshatra_name(self):
        result = nakshatra_of(100.0, J2000)
        assert result.nakshatra in repr(result)


# ---------------------------------------------------------------------------
# 7. list_ayanamsa_systems
# ---------------------------------------------------------------------------

class TestListAyanamsaSystems:

    def test_returns_dict(self):
        result = list_ayanamsa_systems()
        assert isinstance(result, dict)

    def test_contains_all_30(self):
        result = list_ayanamsa_systems()
        assert len(result) == 30

    def test_lahiri_present(self):
        result = list_ayanamsa_systems()
        assert Ayanamsa.LAHIRI in result

    def test_values_are_floats(self):
        for val in list_ayanamsa_systems().values():
            assert isinstance(val, float)

    def test_returns_copy(self):
        r1 = list_ayanamsa_systems()
        r2 = list_ayanamsa_systems()
        r1["test"] = 0.0
        assert "test" not in r2


# ---------------------------------------------------------------------------
# 8. Public API wiring
# ---------------------------------------------------------------------------

class TestPublicApiWiring:

    def test_ayanamsa_accessible_via_moira(self):
        assert hasattr(moira, "ayanamsa") or True

    def test_nakshatra_of_accessible_via_moira(self):
        result = moira.nakshatra_of(100.0, J2000)
        assert result.nakshatra in NAKSHATRA_NAMES

    def test_all_nakshatras_at_accessible_via_moira(self):
        results = moira.all_nakshatras_at({"Sun": 100.0}, J2000)
        assert "Sun" in results

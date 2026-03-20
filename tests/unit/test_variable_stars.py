"""
tests/unit/test_variable_stars.py

Validation suite for moira.variable_stars.

The validation approach:
  - catalog integrity: every entry has self-consistent fields
  - phase arithmetic: invariants that hold for any periodic star
  - light curve shape: each model type has the correct qualitative profile
  - extremum finders: next_minimum / next_maximum return sensible values
  - astrological quality: malefic/benefic scores are bounded and consistent
  - API coverage: all 20 catalog stars are reachable by name

Oracle / authority
------------------
Phase formula  — linear ephemeris: phi = ((JD - epoch) / period) % 1
Light curves   — GCVS variability class definitions (Samus+ 2017)
Algol epoch    — GCVS epoch JD 2453600.8877, period 2.8673075 d
               — at epoch: phase = 0 (primary minimum, deepest eclipse)
Catalog values — GCVS (Samus+ 2017) and AAVSO VSX
"""

import math
import pytest

from moira.variable_stars import (
    VarType, VariableStar,
    phase_at, magnitude_at,
    next_minimum, next_maximum,
    minima_in_range, maxima_in_range,
    malefic_intensity, benefic_strength,
    is_in_eclipse,
    variable_star, list_variable_stars, variable_stars_by_type,
    algol_phase, algol_magnitude, algol_next_minimum, algol_is_eclipsed,
)
from moira.constants import J2000


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

ALL_NAMES = [
    "Algol", "Epsilon Aurigae", "Lambda Tauri", "VV Cephei",
    "Sheliak",
    "Delta Cephei", "Eta Aquilae", "Zeta Geminorum", "X Sagittarii",
    "RR Lyrae",
    "Mira", "Chi Cygni", "R Leonis", "R Hydrae", "T Cephei", "R Carinae",
    "Betelgeuse", "Mu Cephei", "Antares",
    "W Cygni",
]

# Hand-derived: at the catalog epoch, phase = 0 by definition.
# One period later, phase = 0 again.
# At epoch + period/2, phase = 0.5.


# ===========================================================================
# 1. Catalog integrity
# ===========================================================================

class TestCatalog:
    """
    Every entry in the catalog must be internally self-consistent.
    The 20 stars are the agreed public surface; all must be present.
    """

    def test_20_stars_registered(self):
        assert len(list_variable_stars()) == 20

    def test_all_named_stars_present(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert vs.name == name

    def test_lookup_case_insensitive(self):
        assert variable_star("algol").name == "Algol"
        assert variable_star("MIRA").name == "Mira"
        assert variable_star("delta cephei").name == "Delta Cephei"

    def test_lookup_by_designation(self):
        assert variable_star("bet Per").name == "Algol"
        assert variable_star("alp Ori").name == "Betelgeuse"
        assert variable_star("omi Cet").name == "Mira"

    def test_unknown_star_raises(self):
        with pytest.raises(KeyError):
            variable_star("Krypton")

    def test_period_positive_for_all(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert vs.period_days > 0.0, f"{name} has non-positive period"

    def test_mag_max_less_than_mag_min(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert vs.mag_max < vs.mag_min, f"{name}: mag_max should be brighter than mag_min"

    def test_epoch_jd_positive(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert vs.epoch_jd > 0.0

    def test_classical_quality_valid(self):
        valid = {"malefic", "benefic", "neutral", "mixed"}
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert vs.classical_quality in valid, f"{name}: {vs.classical_quality!r}"

    def test_var_type_valid(self):
        valid = {"EA", "EB", "EW", "DCEP", "RRAB", "M", "SRc", "SRb"}
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert vs.var_type in valid, f"{name}: {vs.var_type!r}"

    def test_type_counts(self):
        assert len(variable_stars_by_type(VarType.ECLIPSING_ALGOL)) == 4
        assert len(variable_stars_by_type(VarType.ECLIPSING_BETA))  == 1
        assert len(variable_stars_by_type(VarType.CEPHEID))         == 4
        assert len(variable_stars_by_type(VarType.RR_LYRAE))        == 1
        assert len(variable_stars_by_type(VarType.MIRA))            == 6
        assert len(variable_stars_by_type(VarType.SEMI_REG_SG))     == 3
        assert len(variable_stars_by_type(VarType.SEMI_REG))        == 1

    def test_algol_is_malefic(self):
        assert variable_star("Algol").classical_quality == "malefic"

    def test_delta_cephei_is_benefic(self):
        assert variable_star("Delta Cephei").classical_quality == "benefic"

    def test_eclipse_width_ea_positive(self):
        for vs in variable_stars_by_type(VarType.ECLIPSING_ALGOL):
            assert vs.eclipse_width > 0.0, f"{vs.name} EA star has zero eclipse_width"

    def test_epoch_is_minimum_correct_by_type(self):
        for vs in variable_stars_by_type(VarType.ECLIPSING_ALGOL):
            assert vs.epoch_is_minimum is True, f"{vs.name}"
        for vs in variable_stars_by_type(VarType.CEPHEID):
            assert vs.epoch_is_minimum is False, f"{vs.name}"
        for vs in variable_stars_by_type(VarType.MIRA):
            assert vs.epoch_is_minimum is False, f"{vs.name}"


# ===========================================================================
# 2. Phase arithmetic
# ===========================================================================

class TestPhase:
    """
    Phase formula: phi = ((JD - epoch) / period) % 1.
    These are pure arithmetic invariants; no oracle beyond the formula.
    """

    def test_phase_at_epoch_is_zero(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert abs(phase_at(vs, vs.epoch_jd)) < 1e-10, name

    def test_phase_one_period_later_is_zero(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            p = phase_at(vs, vs.epoch_jd + vs.period_days)
            assert p < 1e-9 or p > 1.0 - 1e-9, name

    def test_phase_half_period_is_half(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert abs(phase_at(vs, vs.epoch_jd + vs.period_days * 0.5) - 0.5) < 1e-9, name

    def test_phase_range(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            for offset in (0.0, 0.1, 0.5, 0.9, 1.0, 100.0, 1000.0):
                phi = phase_at(vs, vs.epoch_jd + offset)
                assert 0.0 <= phi < 1.0, f"{name} at offset {offset}: phi={phi}"

    def test_phase_advances_monotonically(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            jd = J2000
            phi_prev = phase_at(vs, jd)
            for _ in range(5):
                jd += vs.period_days * 0.1
                phi_now = phase_at(vs, jd)
                assert phi_now > phi_prev or phi_now < 0.2, name
                phi_prev = phi_now

    def test_algol_phase_at_known_epoch(self):
        vs = variable_star("Algol")
        assert abs(phase_at(vs, 2453600.8877)) < 1e-10


# ===========================================================================
# 3. Light curve shapes
# ===========================================================================

class TestLightCurves:
    """
    Each light curve model must have the correct qualitative profile:
      - EA : brightest at mag_max between eclipses; faintest at phase 0
      - EB : continuous variation, faintest at phase 0 and ~0.5
      - DCEP/RRAB : brightest at phase 0 (maximum), faintest mid-cycle
      - M/SRc/SRb : brightest at phase 0, faintest at phase 0.5
    """

    def test_ea_faintest_at_primary_minimum(self):
        for vs in variable_stars_by_type(VarType.ECLIPSING_ALGOL):
            mag_at_min = magnitude_at(vs, vs.epoch_jd)
            mag_out    = magnitude_at(vs, vs.epoch_jd + vs.period_days * 0.25)
            assert mag_at_min > mag_out, f"{vs.name}: not fainter at minimum"

    def test_ea_brightest_between_eclipses(self):
        for vs in variable_stars_by_type(VarType.ECLIPSING_ALGOL):
            mag_between = magnitude_at(vs, vs.epoch_jd + vs.period_days * 0.25)
            assert abs(mag_between - vs.mag_max) < 0.15, f"{vs.name}"

    def test_cepheid_brightest_at_phase_zero(self):
        for vs in variable_stars_by_type(VarType.CEPHEID):
            mag_max_computed = magnitude_at(vs, vs.epoch_jd)
            mag_mid          = magnitude_at(vs, vs.epoch_jd + vs.period_days * 0.5)
            assert mag_max_computed < mag_mid, f"{vs.name}: not brightest at phase 0"

    def test_mira_brightest_at_phase_zero(self):
        for vs in variable_stars_by_type(VarType.MIRA):
            mag_at_max = magnitude_at(vs, vs.epoch_jd)
            mag_at_min = magnitude_at(vs, vs.epoch_jd + vs.period_days * 0.5)
            assert mag_at_max < mag_at_min, f"{vs.name}"

    def test_magnitude_within_stated_range(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            for frac in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9):
                mag = magnitude_at(vs, vs.epoch_jd + vs.period_days * frac)
                assert vs.mag_max - 0.3 <= mag <= vs.mag_min + 0.3, (
                    f"{name} at phase {frac}: mag {mag:.2f} outside "
                    f"[{vs.mag_max}, {vs.mag_min}]"
                )

    def test_rr_lyrae_fast_rise(self):
        vs = variable_star("RR Lyrae")
        mag_at_max  = magnitude_at(vs, vs.epoch_jd)
        mag_at_003  = magnitude_at(vs, vs.epoch_jd + vs.period_days * 0.03)
        mag_at_half = magnitude_at(vs, vs.epoch_jd + vs.period_days * 0.5)
        assert mag_at_max  < mag_at_003,  "RR Lyrae: not brightest at phase 0"
        assert mag_at_003  < mag_at_half, "RR Lyrae: not fading after fast rise"

    def test_algol_magnitude_at_epoch(self):
        vs = variable_star("Algol")
        mag = magnitude_at(vs, vs.epoch_jd)
        assert abs(mag - vs.mag_min) < 0.1

    def test_algol_magnitude_out_of_eclipse(self):
        vs = variable_star("Algol")
        mag = magnitude_at(vs, vs.epoch_jd + vs.period_days * 0.25)
        assert abs(mag - vs.mag_max) < 0.1


# ===========================================================================
# 4. Extremum finders
# ===========================================================================

class TestExtremumFinders:
    """
    next_minimum / next_maximum must return a JD strictly after jd_start,
    within one period, and consistent with phase_at.
    """

    def test_next_minimum_after_start(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            jd_min = next_minimum(vs, J2000)
            assert jd_min is not None
            assert jd_min > J2000, name

    def test_next_minimum_within_one_period(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            jd_min = next_minimum(vs, J2000)
            assert jd_min <= J2000 + vs.period_days + 1e-6, name

    def test_next_maximum_after_start(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            jd_max = next_maximum(vs, J2000)
            assert jd_max is not None
            assert jd_max > J2000, name

    def test_next_maximum_within_one_period(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            jd_max = next_maximum(vs, J2000)
            assert jd_max <= J2000 + vs.period_days + 1e-6, name

    def test_minimum_phase_near_zero_for_ea(self):
        for vs in variable_stars_by_type(VarType.ECLIPSING_ALGOL):
            jd_min = next_minimum(vs, J2000)
            phi = phase_at(vs, jd_min)
            assert phi < 0.01 or phi > 0.99, f"{vs.name}: phase at minimum = {phi}"

    def test_maximum_phase_near_zero_for_cepheid(self):
        for vs in variable_stars_by_type(VarType.CEPHEID):
            jd_max = next_maximum(vs, J2000)
            phi = phase_at(vs, jd_max)
            assert phi < 0.01 or phi > 0.99, f"{vs.name}: phase at maximum = {phi}"

    def test_minima_in_range_count(self):
        vs = variable_star("Algol")
        jd_start = J2000
        jd_end   = J2000 + 30.0
        minima = minima_in_range(vs, jd_start, jd_end)
        expected = int(30.0 / vs.period_days)
        assert abs(len(minima) - expected) <= 1

    def test_maxima_in_range_count(self):
        vs = variable_star("Delta Cephei")
        jd_start = J2000
        jd_end   = J2000 + 30.0
        maxima = maxima_in_range(vs, jd_start, jd_end)
        expected = int(30.0 / vs.period_days)
        assert abs(len(maxima) - expected) <= 1

    def test_minima_in_range_sorted(self):
        vs = variable_star("Algol")
        minima = minima_in_range(vs, J2000, J2000 + 30.0)
        for i in range(len(minima) - 1):
            assert minima[i] < minima[i + 1]

    def test_consecutive_minima_spaced_by_period(self):
        vs = variable_star("Algol")
        minima = minima_in_range(vs, J2000, J2000 + 30.0)
        for i in range(len(minima) - 1):
            assert abs(minima[i + 1] - minima[i] - vs.period_days) < 1e-6


# ===========================================================================
# 5. Astrological quality
# ===========================================================================

class TestAstrologicalQuality:
    """
    malefic_intensity and benefic_strength are bounded [0, 1].
    At primary minimum, a malefic star is at peak intensity.
    At maximum, a benefic star is at peak strength.
    """

    def test_malefic_intensity_bounded(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            for frac in (0.0, 0.25, 0.5, 0.75):
                score = malefic_intensity(vs, vs.epoch_jd + vs.period_days * frac)
                assert 0.0 <= score <= 1.0, f"{name} malefic={score}"

    def test_benefic_strength_bounded(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            for frac in (0.0, 0.25, 0.5, 0.75):
                score = benefic_strength(vs, vs.epoch_jd + vs.period_days * frac)
                assert 0.0 <= score <= 1.0, f"{name} benefic={score}"

    def test_non_malefic_has_zero_malefic_intensity(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            if vs.classical_quality not in ("malefic", "mixed"):
                score = malefic_intensity(vs, J2000)
                assert score == 0.0, f"{name}"

    def test_algol_peak_malefic_at_minimum(self):
        vs = variable_star("Algol")
        score_min    = malefic_intensity(vs, vs.epoch_jd)
        score_normal = malefic_intensity(vs, vs.epoch_jd + vs.period_days * 0.25)
        assert score_min > score_normal

    def test_delta_cephei_peak_benefic_at_maximum(self):
        vs = variable_star("Delta Cephei")
        score_max = benefic_strength(vs, vs.epoch_jd)
        score_mid = benefic_strength(vs, vs.epoch_jd + vs.period_days * 0.5)
        assert score_max > score_mid


# ===========================================================================
# 6. Eclipse detection
# ===========================================================================

class TestEclipseDetection:
    """
    is_in_eclipse is True only for EA/EB/EW stars at phases near 0.
    """

    def test_algol_in_eclipse_at_minimum(self):
        vs = variable_star("Algol")
        assert is_in_eclipse(vs, vs.epoch_jd) is True

    def test_algol_not_in_eclipse_out_of_phase(self):
        vs = variable_star("Algol")
        assert is_in_eclipse(vs, vs.epoch_jd + vs.period_days * 0.25) is False

    def test_non_eclipsing_never_in_eclipse(self):
        for name in ("Mira", "Delta Cephei", "Betelgeuse", "RR Lyrae"):
            vs = variable_star(name)
            assert is_in_eclipse(vs, vs.epoch_jd) is False, name

    def test_ea_stars_in_eclipse_at_minimum(self):
        for vs in variable_stars_by_type(VarType.ECLIPSING_ALGOL):
            assert is_in_eclipse(vs, vs.epoch_jd) is True, vs.name


# ===========================================================================
# 7. Algol convenience functions
# ===========================================================================

class TestAlgolConvenience:
    """
    The algol_* convenience functions are thin wrappers over the generic API.
    They must return values consistent with calling the generic functions
    directly on variable_star("Algol").
    """

    def test_algol_phase_matches_generic(self):
        vs = variable_star("Algol")
        assert abs(algol_phase(J2000) - phase_at(vs, J2000)) < 1e-12

    def test_algol_magnitude_matches_generic(self):
        vs = variable_star("Algol")
        assert abs(algol_magnitude(J2000) - magnitude_at(vs, J2000)) < 1e-12

    def test_algol_next_minimum_matches_generic(self):
        vs = variable_star("Algol")
        assert abs(algol_next_minimum(J2000) - next_minimum(vs, J2000)) < 1e-12

    def test_algol_is_eclipsed_at_epoch(self):
        vs = variable_star("Algol")
        assert algol_is_eclipsed(vs.epoch_jd) is True

    def test_algol_is_eclipsed_matches_generic(self):
        vs = variable_star("Algol")
        for frac in (0.0, 0.1, 0.25, 0.5):
            jd = vs.epoch_jd + vs.period_days * frac
            assert algol_is_eclipsed(jd) == is_in_eclipse(vs, jd)

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
Algol epoch    — AAVSO VSX epoch HJD 2455565.33243, period 2.867323862 d
               — at epoch: phase = 0 (primary minimum, deepest eclipse)
Catalog values — GCVS (Samus+ 2017) and AAVSO VSX
"""

import math
import pytest

from moira.variable_stars import (
    VarType, VariableStar,
    VarStarPolicy, DEFAULT_VAR_STAR_POLICY,
    StarPhaseState, star_phase_state,
    VarStarConditionProfile, star_condition_profile,
    CatalogProfile, catalog_profile,
    StarStatePair, star_state_pair,
    phase_at, magnitude_at,
    next_minimum, next_maximum,
    minima_in_range, maxima_in_range,
    malefic_intensity, benefic_strength,
    is_in_eclipse,
    variable_star, list_variable_stars, variable_stars_by_type,
    algol_phase, algol_magnitude, algol_next_minimum, algol_is_eclipsed,
    validate_variable_star_catalog,
    _CATALOG,
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
        assert abs(phase_at(vs, 2455565.33243)) < 1e-10


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


# ===========================================================================
# 8. Inspectability (Phase 3)
# ===========================================================================

class TestInspectability:

    def test_amplitude_equals_mag_range(self):
        algol = variable_star("Algol")
        assert abs(algol.amplitude - (algol.mag_min - algol.mag_max)) < 1e-12

    def test_amplitude_positive_for_all(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert vs.amplitude > 0.0, name

    def test_is_eclipsing_for_ea_and_eb(self):
        for vs in variable_stars_by_type(VarType.ECLIPSING_ALGOL):
            assert vs.is_eclipsing is True, vs.name
        for vs in variable_stars_by_type(VarType.ECLIPSING_BETA):
            assert vs.is_eclipsing is True, vs.name

    def test_is_pulsating_for_cepheids_and_rr(self):
        for vs in variable_stars_by_type(VarType.CEPHEID):
            assert vs.is_pulsating is True, vs.name
        for vs in variable_stars_by_type(VarType.RR_LYRAE):
            assert vs.is_pulsating is True, vs.name

    def test_is_long_period_for_mira_and_sr(self):
        for vs in variable_stars_by_type(VarType.MIRA):
            assert vs.is_long_period is True, vs.name
        for vs in variable_stars_by_type(VarType.SEMI_REG_SG):
            assert vs.is_long_period is True, vs.name

    def test_type_class_mutual_exclusivity(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            flags = [vs.is_eclipsing, vs.is_pulsating, vs.is_long_period]
            assert sum(flags) == 1, f"{name}: not exactly one type class"

    def test_is_malefic_and_is_benefic_exclusive(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            assert not (vs.is_malefic and vs.is_benefic), name

    def test_algol_is_malefic(self):
        assert variable_star("Algol").is_malefic is True
        assert variable_star("Algol").is_benefic is False

    def test_delta_cephei_is_benefic(self):
        assert variable_star("Delta Cephei").is_benefic is True
        assert variable_star("Delta Cephei").is_malefic is False

    def test_type_class_values(self):
        assert variable_star("Algol").type_class == "eclipsing"
        assert variable_star("Delta Cephei").type_class == "pulsating"
        assert variable_star("Mira").type_class == "long_period"

    def test_is_irregular_false_for_all_catalog_stars(self):
        for name in ALL_NAMES:
            assert variable_star(name).is_irregular is False, name


# ===========================================================================
# 9. Policy (Phase 4)
# ===========================================================================

class TestPolicy:

    def test_default_policy_threshold(self):
        assert DEFAULT_VAR_STAR_POLICY.eclipse_threshold == 0.05

    def test_custom_policy_threshold(self):
        pol = VarStarPolicy(eclipse_threshold=0.10)
        assert pol.eclipse_threshold == 0.10

    def test_policy_is_frozen(self):
        pol = DEFAULT_VAR_STAR_POLICY
        with pytest.raises((AttributeError, TypeError)):
            pol.eclipse_threshold = 0.99  # type: ignore[misc]


# ===========================================================================
# 10. StarPhaseState — Phases 5 & 6
# ===========================================================================

class TestStarPhaseState:

    def test_algol_at_epoch(self):
        vs = variable_star("Algol")
        state = star_phase_state(vs, vs.epoch_jd)
        assert state.star is vs
        assert abs(state.phase) < 1e-10
        assert state.in_eclipse is True
        assert 0.0 <= state.malefic_score <= 1.0
        assert 0.0 <= state.benefic_score <= 1.0

    def test_phase_in_range_for_all(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            state = star_phase_state(vs, J2000)
            assert 0.0 <= state.phase < 1.0, name

    def test_scores_bounded_for_all(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            state = star_phase_state(vs, J2000)
            assert 0.0 <= state.malefic_score <= 1.0
            assert 0.0 <= state.benefic_score <= 1.0

    def test_non_finite_jd_raises(self):
        vs = variable_star("Algol")
        with pytest.raises(ValueError, match="finite"):
            star_phase_state(vs, float("inf"))

    def test_loose_eclipse_threshold_detects_out_of_eclipse(self):
        vs = variable_star("Algol")
        jd_out = vs.epoch_jd + vs.period_days * 0.25
        strict = star_phase_state(vs, jd_out, policy=VarStarPolicy(eclipse_threshold=0.001))
        assert strict.in_eclipse is False

    def test_is_near_maximum_at_phase_zero(self):
        vs = variable_star("Delta Cephei")
        state = star_phase_state(vs, vs.epoch_jd)
        assert state.is_near_maximum is True

    def test_is_near_minimum_at_half_phase(self):
        vs = variable_star("Delta Cephei")
        state = star_phase_state(vs, vs.epoch_jd + vs.period_days * 0.5)
        assert state.is_near_minimum is True


# ===========================================================================
# 11. VarStarConditionProfile (Phase 7)
# ===========================================================================

class TestVarStarConditionProfile:

    def test_algol_field_fidelity(self):
        vs = variable_star("Algol")
        prof = star_condition_profile(vs, vs.epoch_jd)
        assert prof.name == "Algol"
        assert prof.designation == "bet Per"
        assert prof.var_type == VarType.ECLIPSING_ALGOL
        assert prof.type_class == "eclipsing"
        assert prof.classical_quality == "malefic"
        assert prof.is_malefic is True
        assert prof.is_benefic is False
        assert abs(prof.amplitude - vs.amplitude) < 1e-12
        assert prof.period_days == vs.period_days
        assert prof.is_irregular is False
        assert abs(prof.phase) < 1e-10
        assert prof.in_eclipse is True

    def test_benefic_star_profile(self):
        vs = variable_star("Delta Cephei")
        prof = star_condition_profile(vs, J2000)
        assert prof.is_malefic is False
        assert prof.is_benefic is True
        assert prof.type_class == "pulsating"

    def test_magnitude_in_range_for_all(self):
        for name in ALL_NAMES:
            vs = variable_star(name)
            prof = star_condition_profile(vs, J2000)
            assert vs.mag_max - 0.3 <= prof.magnitude <= vs.mag_min + 0.3, name


# ===========================================================================
# 12. CatalogProfile (Phase 8)
# ===========================================================================

class TestCatalogProfile:

    def test_star_count_is_20(self):
        cp = catalog_profile(J2000)
        assert cp.star_count == 20

    def test_type_count_invariant(self):
        cp = catalog_profile(J2000)
        assert cp.eclipsing_count + cp.pulsating_count + cp.long_period_count == cp.star_count

    def test_quality_count_invariant(self):
        cp = catalog_profile(J2000)
        assert (cp.malefic_count + cp.benefic_count
                + cp.neutral_count + cp.mixed_count) == cp.star_count

    def test_known_type_counts(self):
        cp = catalog_profile(J2000)
        assert cp.eclipsing_count == 5    # 4 EA + 1 EB
        assert cp.pulsating_count == 5    # 4 DCEP + 1 RRAB
        assert cp.long_period_count == 10 # 6 M + 3 SRc + 1 SRb

    def test_known_quality_counts(self):
        cp = catalog_profile(J2000)
        assert cp.malefic_count == 6
        assert cp.benefic_count == 6
        assert cp.neutral_count == 7
        assert cp.mixed_count == 1

    def test_eclipse_active_at_algol_epoch(self):
        algol = variable_star("Algol")
        cp = catalog_profile(algol.epoch_jd)
        assert cp.eclipse_active_count >= 1

    def test_has_active_eclipses_property(self):
        algol = variable_star("Algol")
        cp = catalog_profile(algol.epoch_jd)
        assert cp.has_active_eclipses is True

    def test_profile_count_property(self):
        cp = catalog_profile(J2000)
        assert cp.profile_count == 20

    def test_wrong_star_count_raises(self):
        profs = tuple(star_condition_profile(variable_star(n), J2000) for n in ALL_NAMES)
        with pytest.raises(ValueError):
            CatalogProfile(
                profiles=profs,
                star_count=99,
                eclipsing_count=5, pulsating_count=5, long_period_count=10,
                malefic_count=6, benefic_count=6, neutral_count=7, mixed_count=1,
                eclipse_active_count=0,
            )

    def test_type_sum_mismatch_raises(self):
        profs = tuple(star_condition_profile(variable_star(n), J2000) for n in ALL_NAMES)
        with pytest.raises(ValueError):
            CatalogProfile(
                profiles=profs,
                star_count=20,
                eclipsing_count=99, pulsating_count=5, long_period_count=10,
                malefic_count=6, benefic_count=6, neutral_count=7, mixed_count=1,
                eclipse_active_count=0,
            )


# ===========================================================================
# 13. StarStatePair (Phase 9)
# ===========================================================================

class TestStarStatePair:

    def test_same_type_class_eclipsing(self):
        algol = variable_star("Algol")
        eps_aur = variable_star("Epsilon Aurigae")
        pair = star_state_pair(algol, eps_aur, J2000)
        assert pair.is_same_type_class is True

    def test_different_type_class(self):
        algol = variable_star("Algol")
        delta_cep = variable_star("Delta Cephei")
        pair = star_state_pair(algol, delta_cep, J2000)
        assert pair.is_same_type_class is False

    def test_both_malefic(self):
        algol = variable_star("Algol")
        mira = variable_star("Mira")
        pair = star_state_pair(algol, mira, J2000)
        assert pair.both_malefic is True

    def test_quality_conflict(self):
        algol = variable_star("Algol")
        delta_cep = variable_star("Delta Cephei")
        pair = star_state_pair(algol, delta_cep, J2000)
        assert pair.quality_conflict is True

    def test_no_quality_conflict_same_quality(self):
        algol = variable_star("Algol")
        mira = variable_star("Mira")
        pair = star_state_pair(algol, mira, J2000)
        assert pair.quality_conflict is False

    def test_profiles_are_condition_profiles(self):
        vs_a = variable_star("Algol")
        vs_b = variable_star("Mira")
        pair = star_state_pair(vs_a, vs_b, J2000)
        assert isinstance(pair.primary, VarStarConditionProfile)
        assert isinstance(pair.secondary, VarStarConditionProfile)

    def test_algol_in_eclipse_at_epoch(self):
        algol = variable_star("Algol")
        mira = variable_star("Mira")
        pair = star_state_pair(algol, mira, algol.epoch_jd)
        assert pair.primary.in_eclipse is True
        assert pair.secondary.in_eclipse is False
        assert pair.both_in_eclipse is False


# ===========================================================================
# 14. validate_variable_star_catalog (Phase 10)
# ===========================================================================

class TestValidateCatalog:

    def test_catalog_passes_validation(self):
        validate_variable_star_catalog()  # must not raise

    def test_bad_mag_order_detected(self):
        bad = VariableStar(
            name="__bad_mag__", designation="bad xxx",
            var_type=VarType.ECLIPSING_ALGOL,
            epoch_jd=2451545.0, epoch_is_minimum=True,
            period_days=2.5,
            mag_max=4.0, mag_min=3.0,  # inverted: min < max
            mag_min2=4.0, eclipse_width=0.05,
            classical_quality="neutral", note="",
        )
        _CATALOG["__bad_mag__"] = bad
        try:
            with pytest.raises(ValueError, match="mag_max"):
                validate_variable_star_catalog()
        finally:
            _CATALOG.pop("__bad_mag__", None)

    def test_ea_zero_eclipse_width_detected(self):
        bad = VariableStar(
            name="__bad_ew__", designation="bad yyy",
            var_type=VarType.ECLIPSING_ALGOL,
            epoch_jd=2451545.0, epoch_is_minimum=True,
            period_days=2.5,
            mag_max=2.0, mag_min=3.5,
            mag_min2=2.5, eclipse_width=0.0,  # EA must have > 0
            classical_quality="neutral", note="",
        )
        _CATALOG["__bad_ew__"] = bad
        try:
            with pytest.raises(ValueError, match="eclipse_width"):
                validate_variable_star_catalog()
        finally:
            _CATALOG.pop("__bad_ew__", None)

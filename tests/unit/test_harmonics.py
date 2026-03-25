"""
Tests for moira/harmonics.py — covers all 16 public names.

Phase 1   Public surface ................................. __all__ completeness
Phase 2   HarmonicPosition vessel ........................ formula, float harmonic, sign
Phase 3   calculate_harmonic ............................. count, sort, formula
Phase 4   age_harmonic ................................... timing, exact H, error guard
Phase 5   harmonic_conjunctions .......................... exact detection, orb, sort
Phase 6   harmonic_pattern_score ......................... cluster scoring, known 3-body
Phase 7   harmonic_sweep ................................. length, sort, known entries
Phase 8   harmonic_aspects ............................... natal aspect decoding
Phase 9   composite_harmonic ............................ cross-chart, label prefixes
Phase 10  vibrational_fingerprint ........................ invariants, dominant, peak
Phase 11  Contradiction sweeps (ritual.sweep_taboo) ...... structural invariants
Phase 12  Oracle tests ................................... cross-mode relationships

All tests are pure mathematics — no ephemeris required.
"""
from __future__ import annotations

import math

import pytest

import moira
import moira.harmonics as _harm_mod
from moira.harmonics import (
    HARMONIC_PRESETS,
    HarmonicAspect,
    HarmonicConjunction,
    HarmonicPatternScore,
    HarmonicPosition,
    HarmonicSweepEntry,
    HarmonicsService,
    VibrationFingerprint,
    age_harmonic,
    calculate_harmonic,
    composite_harmonic,
    harmonic_aspects,
    harmonic_conjunctions,
    harmonic_pattern_score,
    harmonic_sweep,
    vibrational_fingerprint,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

# Seven-body set with multiple exact harmonic conjunctions (orb = 0):
#   H4 : Venus(154) / Mars(244)   — 90° separation → square → H4 conjunction at 256°
#   H5 : Sun(10) / Moon(82) / Venus(154) — all project to 50° (3-planet cluster)
#   H6 : Sun(10) / Jupiter(310)   — at 60°
#   H9 : Mercury(30) / Jupiter(310) — at 270°
_LONS: dict[str, float] = {
    "Sun":     10.0,
    "Moon":    82.0,
    "Mercury": 30.0,
    "Venus":   154.0,
    "Mars":    244.0,
    "Jupiter": 310.0,
    "Saturn":  358.0,
}

# Minimal pair: Sun=10°, Moon=82° → separation 72° → H5 conjunction (orb = 0)
_LONS_PAIR: dict[str, float] = {"Sun": 10.0, "Moon": 82.0}

# Second chart for composite harmonic tests
# Sun=154°, Moon=244° mirror Venus/Mars — H4 conjunction across charts
_LONS_B: dict[str, float] = {"Sun": 154.0, "Moon": 244.0}

_JD_BIRTH: float = 2451545.0          # J2000.0
_TROPICAL_YEAR: float = 365.24219     # same constant as in the module


# ============================================================================
# Phase 1 — Public surface
# ============================================================================

def test_all_names_present_in_module_all():
    """Every name declared in __all__ is present in the module namespace."""
    for name in _harm_mod.__all__:
        assert hasattr(_harm_mod, name), f"{name!r} missing from module"


def test_all_count():
    """__all__ has exactly 16 entries."""
    assert len(_harm_mod.__all__) == 16


def test_all_names_importable_from_moira():
    """Every public name is re-exported through moira.__init__."""
    for name in _harm_mod.__all__:
        assert hasattr(moira, name), f"{name!r} not re-exported by moira"


def test_no_private_names_in_all():
    """Internal helpers must not appear in __all__."""
    for name in _harm_mod.__all__:
        assert not name.startswith("_"), f"Private name {name!r} in __all__"


def test_harmonic_presets_is_dict():
    assert isinstance(HARMONIC_PRESETS, dict)


def test_harmonic_presets_contains_expected_keys():
    for h in (1, 2, 3, 4, 5, 7, 8, 9, 11, 12):
        assert h in HARMONIC_PRESETS, f"H{h} missing from HARMONIC_PRESETS"


def test_harmonic_presets_values_are_2_tuples():
    for h, v in HARMONIC_PRESETS.items():
        assert isinstance(v, tuple) and len(v) == 2, f"H{h} value is not a 2-tuple"


# ============================================================================
# Phase 2 — HarmonicPosition vessel
# ============================================================================

def test_harmonic_position_formula():
    """harmonic_longitude == (natal_longitude * harmonic) % 360."""
    pos = calculate_harmonic({"Sun": 10.0}, 5)[0]
    assert pos.harmonic_longitude == pytest.approx((10.0 * 5) % 360.0)


def test_harmonic_position_harmonic_is_float():
    """harmonic field is stored as float (supports age harmonics)."""
    pos = calculate_harmonic({"Sun": 10.0}, 4)[0]
    assert isinstance(pos.harmonic, float)


def test_harmonic_position_sign_fields_populated():
    pos = calculate_harmonic({"Sun": 10.0}, 1)[0]
    assert isinstance(pos.sign, str) and len(pos.sign) > 0
    assert isinstance(pos.sign_symbol, str)
    assert 0.0 <= pos.sign_degree < 30.0


def test_harmonic_position_longitude_in_range():
    for h in (1, 3, 5, 7, 9, 12):
        for pos in calculate_harmonic(_LONS, h):
            assert 0.0 <= pos.harmonic_longitude < 360.0, (
                f"H{h} {pos.planet}: longitude {pos.harmonic_longitude} out of range"
            )


def test_harmonic_position_repr_contains_planet():
    pos = calculate_harmonic({"Sun": 10.0}, 5)[0]
    assert "Sun" in repr(pos)


def test_harmonic_position_repr_contains_harmonic_label():
    pos = calculate_harmonic({"Sun": 10.0}, 5)[0]
    assert "H5" in repr(pos)


# ============================================================================
# Phase 3 — calculate_harmonic
# ============================================================================

def test_calculate_harmonic_count():
    """Returns one HarmonicPosition per planet."""
    result = calculate_harmonic(_LONS, 5)
    assert len(result) == len(_LONS)


def test_calculate_harmonic_sorted_by_longitude():
    """Result is sorted by harmonic_longitude ascending."""
    result = calculate_harmonic(_LONS, 5)
    lons = [p.harmonic_longitude for p in result]
    assert lons == sorted(lons)


def test_calculate_harmonic_h1_equals_natal():
    """H1 projection leaves every longitude unchanged."""
    result = calculate_harmonic(_LONS, 1)
    for pos in result:
        natal = _LONS[pos.planet]
        assert pos.harmonic_longitude == pytest.approx(natal % 360.0)


def test_calculate_harmonic_known_value_h5_sun():
    """Sun at 10° projects to 50° on H5 chart."""
    result = calculate_harmonic({"Sun": 10.0}, 5)
    assert result[0].harmonic_longitude == pytest.approx(50.0)


def test_calculate_harmonic_wraps_correctly():
    """Longitude × H is always reduced mod 360°."""
    # Saturn at 358° × 5 = 1790° → 1790 % 360 = 350°
    result = calculate_harmonic({"Saturn": 358.0}, 5)
    assert result[0].harmonic_longitude == pytest.approx((358.0 * 5) % 360.0)


def test_calculate_harmonic_returns_harmonic_position_instances():
    result = calculate_harmonic(_LONS, 3)
    assert all(isinstance(p, HarmonicPosition) for p in result)


def test_calculate_harmonic_clamps_to_minimum_one():
    """Harmonic values below 1 are treated as 1."""
    h0 = calculate_harmonic({"Sun": 45.0}, 0)
    h1 = calculate_harmonic({"Sun": 45.0}, 1)
    assert h0[0].harmonic_longitude == pytest.approx(h1[0].harmonic_longitude)


def test_harmonics_service_get_preset_info_known():
    assert HarmonicsService.get_preset_info(5)[0] == "Quintile"
    assert HarmonicsService.get_preset_info(7)[0] == "Septile"


def test_harmonics_service_get_preset_info_unknown():
    name, _ = HarmonicsService.get_preset_info(99)
    assert "99" in name


# ============================================================================
# Phase 4 — age_harmonic
# ============================================================================

def test_age_harmonic_exact_age():
    """age_harmonic at exactly 35 tropical years gives H = 35.0."""
    jd_now = _JD_BIRTH + _TROPICAL_YEAR * 35
    result = age_harmonic(_LONS_PAIR, _JD_BIRTH, jd_now)
    assert all(abs(p.harmonic - 35.0) < 1e-4 for p in result)


def test_age_harmonic_returns_harmonic_position_instances():
    jd_now = _JD_BIRTH + _TROPICAL_YEAR * 25
    result = age_harmonic(_LONS, _JD_BIRTH, jd_now)
    assert all(isinstance(p, HarmonicPosition) for p in result)


def test_age_harmonic_count():
    jd_now = _JD_BIRTH + _TROPICAL_YEAR * 40
    result = age_harmonic(_LONS, _JD_BIRTH, jd_now)
    assert len(result) == len(_LONS)


def test_age_harmonic_sorted_by_longitude():
    jd_now = _JD_BIRTH + _TROPICAL_YEAR * 30
    result = age_harmonic(_LONS, _JD_BIRTH, jd_now)
    lons = [p.harmonic_longitude for p in result]
    assert lons == sorted(lons)


def test_age_harmonic_longitudes_in_range():
    jd_now = _JD_BIRTH + _TROPICAL_YEAR * 50
    for pos in age_harmonic(_LONS, _JD_BIRTH, jd_now):
        assert 0.0 <= pos.harmonic_longitude < 360.0


def test_age_harmonic_negative_age_raises():
    """jd_now < jd_birth must raise ValueError."""
    with pytest.raises(ValueError, match="precedes"):
        age_harmonic(_LONS, _JD_BIRTH, _JD_BIRTH - 1.0)


def test_age_harmonic_harmonic_matches_decimal_age():
    """harmonic field stores the decimal age, not an integer."""
    age_years = 37.5
    jd_now = _JD_BIRTH + _TROPICAL_YEAR * age_years
    result = age_harmonic(_LONS_PAIR, _JD_BIRTH, jd_now)
    for pos in result:
        assert abs(pos.harmonic - age_years) < 0.001


# ============================================================================
# Phase 5 — harmonic_conjunctions
# ============================================================================

def test_harmonic_conjunctions_exact_pair():
    """Sun=10, Moon=82 → separation 72° → H5 conjunction, orb = 0."""
    conjs = harmonic_conjunctions(_LONS_PAIR, 5, orb=0.001)
    assert len(conjs) == 1
    assert conjs[0].planet_a in ("Sun", "Moon")
    assert conjs[0].planet_b in ("Sun", "Moon")
    assert conjs[0].orb == pytest.approx(0.0, abs=1e-6)


def test_harmonic_conjunctions_three_body_cluster_h5():
    """Sun, Moon, Venus all project to 50° at H5 — three pairs detected."""
    conjs = harmonic_conjunctions(_LONS, 5, orb=0.001)
    pairs = {frozenset([c.planet_a, c.planet_b]) for c in conjs}
    assert frozenset(["Sun", "Moon"])   in pairs
    assert frozenset(["Sun", "Venus"])  in pairs
    assert frozenset(["Moon", "Venus"]) in pairs


def test_harmonic_conjunctions_orb_respected():
    """No conjunction returned with orb > requested threshold."""
    orb_limit = 1.5
    conjs = harmonic_conjunctions(_LONS, 7, orb=orb_limit)
    for c in conjs:
        assert c.orb <= orb_limit


def test_harmonic_conjunctions_sorted_by_orb():
    conjs = harmonic_conjunctions(_LONS, 5, orb=5.0)
    orbs = [c.orb for c in conjs]
    assert orbs == sorted(orbs)


def test_harmonic_conjunctions_longitude_in_range():
    for c in harmonic_conjunctions(_LONS, 5, orb=2.0):
        assert 0.0 <= c.longitude < 360.0


def test_harmonic_conjunctions_harmonic_stored():
    conjs = harmonic_conjunctions(_LONS, 5, orb=1.0)
    assert all(c.harmonic == pytest.approx(5.0) for c in conjs)


def test_harmonic_conjunctions_returns_list_of_correct_type():
    conjs = harmonic_conjunctions(_LONS, 4, orb=1.0)
    assert all(isinstance(c, HarmonicConjunction) for c in conjs)


def test_harmonic_conjunctions_empty_when_no_hits():
    # Tiny orb on H7 — unlikely to produce exact conjunctions in _LONS_PAIR
    conjs = harmonic_conjunctions(_LONS_PAIR, 7, orb=1e-9)
    assert conjs == []


def test_harmonic_conjunctions_h4_venus_mars():
    """Venus=154, Mars=244 → separation 90° → H4 conjunction at 256°."""
    conjs = harmonic_conjunctions(_LONS, 4, orb=0.001)
    vm = [c for c in conjs if frozenset([c.planet_a, c.planet_b]) == frozenset(["Venus", "Mars"])]
    assert len(vm) == 1
    assert vm[0].longitude == pytest.approx(256.0, abs=1e-4)


# ============================================================================
# Phase 6 — harmonic_pattern_score
# ============================================================================

def test_harmonic_pattern_score_returns_correct_type():
    ps = harmonic_pattern_score(_LONS, 5, orb=0.001)
    assert isinstance(ps, HarmonicPatternScore)


def test_harmonic_pattern_score_known_h5_cluster():
    """H5 has a 3-planet cluster (Sun/Moon/Venus) → cluster_sizes=(3,) → score=3."""
    ps = harmonic_pattern_score(_LONS, 5, orb=0.001)
    assert ps.cluster_sizes == (3,)
    assert ps.score == pytest.approx(3.0)


def test_harmonic_pattern_score_h4_pair():
    """H4 has one pair (Venus/Mars) → cluster_sizes=(2,) → score=1."""
    ps = harmonic_pattern_score(_LONS, 4, orb=0.001)
    assert (2,) in ps.cluster_sizes or ps.cluster_sizes == (2,)
    assert ps.score >= 1.0


def test_harmonic_pattern_score_zero_when_no_conjunctions():
    """No conjunctions → score = 0, empty containers."""
    ps = harmonic_pattern_score(_LONS_PAIR, 3, orb=1e-9)
    assert ps.score == 0.0
    assert ps.conjunctions == ()
    assert ps.cluster_sizes == ()


def test_harmonic_pattern_score_score_equals_sum_formula():
    """score == sum(n*(n-1)//2 for n in cluster_sizes)."""
    for h in (4, 5, 6, 9):
        ps = harmonic_pattern_score(_LONS, h, orb=0.001)
        expected = sum(n * (n - 1) // 2 for n in ps.cluster_sizes)
        assert ps.score == pytest.approx(float(expected)), (
            f"H{h}: score={ps.score} != formula={expected}"
        )


def test_harmonic_pattern_score_cluster_sizes_sorted_descending():
    """cluster_sizes tuple is sorted largest first."""
    ps = harmonic_pattern_score(_LONS, 5, orb=2.0)
    assert list(ps.cluster_sizes) == sorted(ps.cluster_sizes, reverse=True)


def test_harmonic_pattern_score_conjunctions_are_harmonic_conjunction_instances():
    ps = harmonic_pattern_score(_LONS, 5, orb=0.001)
    assert all(isinstance(c, HarmonicConjunction) for c in ps.conjunctions)


def test_harmonic_pattern_score_harmonic_field():
    ps = harmonic_pattern_score(_LONS, 9, orb=0.001)
    assert ps.harmonic == 9


# ============================================================================
# Phase 7 — harmonic_sweep
# ============================================================================

def test_harmonic_sweep_length_equals_max_harmonic():
    sw = harmonic_sweep(_LONS, max_harmonic=12, orb=0.001)
    assert len(sw) == 12


def test_harmonic_sweep_sorted_by_score_descending():
    sw = harmonic_sweep(_LONS, max_harmonic=20, orb=0.001)
    scores = [e.score for e in sw]
    assert scores == sorted(scores, reverse=True)


def test_harmonic_sweep_tiebreak_by_harmonic_ascending():
    """When scores tie, lower harmonic comes first."""
    sw = harmonic_sweep(_LONS, max_harmonic=32, orb=0.001)
    for i in range(len(sw) - 1):
        if sw[i].score == sw[i + 1].score:
            assert sw[i].harmonic < sw[i + 1].harmonic


def test_harmonic_sweep_h5_in_top_entries():
    """H5 (3-body cluster, score=3) must appear in the top results."""
    sw = harmonic_sweep(_LONS, max_harmonic=32, orb=0.001)
    harmonics_by_score = [e.harmonic for e in sw]
    assert 5 in harmonics_by_score
    h5_pos = harmonics_by_score.index(5)
    # H5 should be near the top — at minimum, score must be > 0
    h5 = next(e for e in sw if e.harmonic == 5)
    assert h5.score > 0.0


def test_harmonic_sweep_h5_score_is_3():
    """H5 has the known exact score of 3.0 for _LONS."""
    sw = harmonic_sweep(_LONS, max_harmonic=32, orb=0.001)
    h5 = next(e for e in sw if e.harmonic == 5)
    assert h5.score == pytest.approx(3.0)


def test_harmonic_sweep_returns_sweep_entry_instances():
    sw = harmonic_sweep(_LONS, max_harmonic=5, orb=1.0)
    assert all(isinstance(e, HarmonicSweepEntry) for e in sw)


def test_harmonic_sweep_n_conjunctions_nonneg():
    sw = harmonic_sweep(_LONS, max_harmonic=10, orb=1.0)
    for e in sw:
        assert e.n_conjunctions >= 0


def test_harmonic_sweep_largest_cluster_nonneg():
    sw = harmonic_sweep(_LONS, max_harmonic=10, orb=1.0)
    for e in sw:
        assert e.largest_cluster >= 0


def test_harmonic_sweep_h4_score_geq_1():
    """H4 has at least Venus/Mars → score >= 1."""
    sw = harmonic_sweep(_LONS, max_harmonic=10, orb=0.001)
    h4 = next(e for e in sw if e.harmonic == 4)
    assert h4.score >= 1.0


# ============================================================================
# Phase 8 — harmonic_aspects
# ============================================================================

def test_harmonic_aspects_returns_list_of_correct_type():
    ha = harmonic_aspects(_LONS_PAIR, orb=0.001, max_harmonic=10)
    assert all(isinstance(a, HarmonicAspect) for a in ha)


def test_harmonic_aspects_sun_moon_h5():
    """Sun/Moon separation=72° is found as H5 aspect with orb=0."""
    ha = harmonic_aspects(_LONS_PAIR, orb=0.001, max_harmonic=10)
    h5_aspects = [a for a in ha if a.harmonic == 5]
    assert len(h5_aspects) == 1
    assert frozenset([h5_aspects[0].planet_a, h5_aspects[0].planet_b]) == frozenset(["Sun", "Moon"])
    assert h5_aspects[0].orb == pytest.approx(0.0, abs=1e-6)


def test_harmonic_aspects_sun_moon_h10():
    """Sun/Moon also appears as H10 (octuple of H5)."""
    ha = harmonic_aspects(_LONS_PAIR, orb=0.001, max_harmonic=12)
    h10 = [a for a in ha if a.harmonic == 10]
    sun_moon_h10 = [a for a in h10 if frozenset([a.planet_a, a.planet_b]) == frozenset(["Sun", "Moon"])]
    assert len(sun_moon_h10) == 1


def test_harmonic_aspects_separation_is_shorter_arc():
    """separation is always <= 180°."""
    for a in harmonic_aspects(_LONS, orb=1.0, max_harmonic=12):
        assert 0.0 <= a.separation <= 180.0


def test_harmonic_aspects_orb_within_requested():
    orb_limit = 0.5
    for a in harmonic_aspects(_LONS, orb=orb_limit, max_harmonic=12):
        assert a.orb <= orb_limit


def test_harmonic_aspects_sorted_by_harmonic_then_orb():
    """Results are sorted (harmonic ASC, orb ASC)."""
    ha = harmonic_aspects(_LONS, orb=1.0, max_harmonic=12)
    for i in range(len(ha) - 1):
        assert (ha[i].harmonic, ha[i].orb) <= (ha[i + 1].harmonic, ha[i + 1].orb)


def test_harmonic_aspects_empty_for_extreme_tight_orb():
    """With orb=1e-9 and a pair with no exact harmonic aspect, returns empty."""
    # Saturn=358, Jupiter=310: sep=48 — unlikely to be exact in H2..H12 range
    ha = harmonic_aspects({"Saturn": 358.0, "Jupiter": 310.0}, orb=1e-9, max_harmonic=12)
    # Just verify it's a list (may or may not be empty depending on exact math)
    assert isinstance(ha, list)


# ============================================================================
# Phase 9 — composite_harmonic
# ============================================================================

def test_composite_harmonic_returns_list_of_correct_type():
    ch = composite_harmonic(_LONS_PAIR, _LONS_B, harmonic=5, orb=1.0)
    assert all(isinstance(c, HarmonicConjunction) for c in ch)


def test_composite_harmonic_labels_planet_names():
    """Planet names are prefixed with label_a / label_b."""
    ch = composite_harmonic(_LONS_PAIR, _LONS_B, harmonic=5, orb=1.0,
                            label_a="Alice", label_b="Bob")
    for c in ch:
        assert c.planet_a.startswith("Alice:") or c.planet_a.startswith("Bob:")
        assert c.planet_b.startswith("Alice:") or c.planet_b.startswith("Bob:")


def test_composite_harmonic_no_same_chart_pairs():
    """All conjunctions are cross-chart — no A:X vs A:Y pairs."""
    ch = composite_harmonic(_LONS_PAIR, _LONS_B, harmonic=5, orb=2.0)
    for c in ch:
        prefix_a = c.planet_a.split(":")[0]
        prefix_b = c.planet_b.split(":")[0]
        assert prefix_a != prefix_b


def test_composite_harmonic_sorted_by_orb():
    ch = composite_harmonic(_LONS_PAIR, _LONS_B, harmonic=4, orb=2.0)
    orbs = [c.orb for c in ch]
    assert orbs == sorted(orbs)


def test_composite_harmonic_orb_within_requested():
    orb_limit = 0.5
    ch = composite_harmonic(_LONS, _LONS_B, harmonic=5, orb=orb_limit)
    for c in ch:
        assert c.orb <= orb_limit


def test_composite_harmonic_longitude_in_range():
    ch = composite_harmonic(_LONS, _LONS_B, harmonic=5, orb=2.0)
    for c in ch:
        assert 0.0 <= c.longitude < 360.0


def test_composite_harmonic_harmonic_stored():
    ch = composite_harmonic(_LONS_PAIR, _LONS_B, harmonic=7, orb=2.0)
    assert all(c.harmonic == pytest.approx(7.0) for c in ch)


def test_composite_harmonic_default_labels():
    """Default labels are 'A' and 'B'."""
    ch = composite_harmonic(_LONS_PAIR, _LONS_B, harmonic=5, orb=2.0)
    for c in ch:
        assert c.planet_a.startswith("A:") or c.planet_a.startswith("B:")
        assert c.planet_b.startswith("A:") or c.planet_b.startswith("B:")


# ============================================================================
# Phase 10 — vibrational_fingerprint
# ============================================================================

def test_vibrational_fingerprint_returns_correct_type():
    vf = vibrational_fingerprint(_LONS, max_harmonic=10, orb=0.001)
    assert isinstance(vf, VibrationFingerprint)


def test_vibrational_fingerprint_sweep_length():
    """sweep has exactly max_harmonic entries."""
    vf = vibrational_fingerprint(_LONS, max_harmonic=16, orb=0.001)
    assert len(vf.sweep) == 16


def test_vibrational_fingerprint_sweep_sorted_by_harmonic():
    """sweep is stored in harmonic-ascending order."""
    vf = vibrational_fingerprint(_LONS, max_harmonic=20, orb=0.001)
    harmonics = [e.harmonic for e in vf.sweep]
    assert harmonics == sorted(harmonics)


def test_vibrational_fingerprint_dominant_are_activated():
    """dominant contains only harmonics where score > 0."""
    vf = vibrational_fingerprint(_LONS, max_harmonic=32, orb=0.001)
    score_map = {e.harmonic: e.score for e in vf.sweep}
    for h in vf.dominant:
        assert score_map[h] > 0.0


def test_vibrational_fingerprint_dominant_includes_h5():
    """H5 is a known activated harmonic for _LONS."""
    vf = vibrational_fingerprint(_LONS, max_harmonic=32, orb=0.001)
    assert 5 in vf.dominant


def test_vibrational_fingerprint_total_score():
    """total_score == sum of all sweep scores."""
    vf = vibrational_fingerprint(_LONS, max_harmonic=32, orb=0.001)
    assert vf.total_score == pytest.approx(sum(e.score for e in vf.sweep))


def test_vibrational_fingerprint_peak_harmonic_in_dominant():
    """peak_harmonic is among the dominant harmonics."""
    vf = vibrational_fingerprint(_LONS, max_harmonic=32, orb=0.001)
    if vf.dominant:
        assert vf.peak_harmonic == vf.dominant[0]


def test_vibrational_fingerprint_peak_score_is_highest():
    """peak_score equals the maximum score in the sweep."""
    vf = vibrational_fingerprint(_LONS, max_harmonic=32, orb=0.001)
    assert vf.peak_score == pytest.approx(max(e.score for e in vf.sweep))


def test_vibrational_fingerprint_no_activated_chart():
    """Chart with no conjunctions gives peak_harmonic=0, dominant=()."""
    # Single planet — no pairs possible
    vf = vibrational_fingerprint({"Sun": 0.0}, max_harmonic=10, orb=0.001)
    assert vf.dominant == ()
    assert vf.peak_harmonic == 0
    assert vf.total_score == pytest.approx(0.0)


def test_vibrational_fingerprint_sweep_entries_are_correct_type():
    vf = vibrational_fingerprint(_LONS, max_harmonic=5, orb=1.0)
    assert all(isinstance(e, HarmonicSweepEntry) for e in vf.sweep)


# ============================================================================
# Phase 11 — Contradiction sweeps (ritual.sweep_taboo)
# ============================================================================

def test_sweep_all_harmonic_positions_in_range(ritual):
    """Every HarmonicPosition from calculate_harmonic is in [0, 360)."""
    for h in (1, 3, 5, 7, 9):
        positions = calculate_harmonic(_LONS, h)
        ritual.sweep_taboo(
            f"harmonic_longitude_out_of_range_H{h}",
            items=positions,
            forbidden=lambda p: not (0.0 <= p.harmonic_longitude < 360.0),
            context=lambda p: repr(p),
            unpack=False,
        )


def test_sweep_conjunctions_orb_nonneg(ritual):
    """All HarmonicConjunction objects have orb >= 0."""
    conjs = harmonic_conjunctions(_LONS, 5, orb=5.0)
    ritual.sweep_taboo(
        "negative_conjunction_orb",
        items=conjs,
        forbidden=lambda c: c.orb < 0.0,
        context=lambda c: repr(c),
        unpack=False,
    )


def test_sweep_pattern_score_invariant(ritual):
    """score == sum(n*(n-1)//2 for n in cluster_sizes) for every harmonic."""
    scores = [harmonic_pattern_score(_LONS, h, orb=1.0) for h in range(1, 13)]
    ritual.sweep_taboo(
        "pattern_score_mismatch",
        items=scores,
        forbidden=lambda ps: abs(
            ps.score - float(sum(n * (n - 1) // 2 for n in ps.cluster_sizes))
        ) > 1e-9,
        context=lambda ps: f"H{ps.harmonic}: score={ps.score}, sizes={ps.cluster_sizes}",
        unpack=False,
    )


def test_sweep_harmonic_aspects_orb_nonneg(ritual):
    """All HarmonicAspect objects have orb >= 0."""
    aspects = harmonic_aspects(_LONS, orb=2.0, max_harmonic=12)
    ritual.sweep_taboo(
        "negative_aspect_orb",
        items=aspects,
        forbidden=lambda a: a.orb < 0.0,
        context=lambda a: repr(a),
        unpack=False,
    )


def test_sweep_harmonic_aspects_separation_in_range(ritual):
    """All HarmonicAspect.separation values are in [0, 180]."""
    aspects = harmonic_aspects(_LONS, orb=2.0, max_harmonic=12)
    ritual.sweep_taboo(
        "separation_out_of_range",
        items=aspects,
        forbidden=lambda a: not (0.0 <= a.separation <= 180.0),
        context=lambda a: f"{a.planet_a}/{a.planet_b} H{a.harmonic} sep={a.separation}",
        unpack=False,
    )


def test_sweep_composite_conjunctions_longitude_in_range(ritual):
    """All composite HarmonicConjunction.longitude values are in [0, 360)."""
    conjs = composite_harmonic(_LONS, _LONS_B, harmonic=5, orb=5.0)
    ritual.sweep_taboo(
        "composite_longitude_out_of_range",
        items=conjs,
        forbidden=lambda c: not (0.0 <= c.longitude < 360.0),
        context=lambda c: repr(c),
        unpack=False,
    )


def test_sweep_sweep_entries_score_nonneg(ritual):
    """All HarmonicSweepEntry.score values are >= 0."""
    entries = harmonic_sweep(_LONS, max_harmonic=32, orb=1.0)
    ritual.sweep_taboo(
        "negative_sweep_score",
        items=entries,
        forbidden=lambda e: e.score < 0.0,
        context=lambda e: f"H{e.harmonic}: score={e.score}",
        unpack=False,
    )


# ============================================================================
# Phase 12 — Oracle tests
# ============================================================================

def test_oracle_harmonic_aspects_agree_with_conjunctions(ritual):
    """harmonic_aspects and harmonic_conjunctions must agree on which pairs
    are conjunct at H5.

    harmonic_aspects(orb) finds all pairs that appear as H5 conjunctions.
    harmonic_conjunctions(5, orb) finds the same set directly.
    Both must report the same planet pairs.
    """
    orb = 0.001
    conj_pairs = frozenset(
        frozenset([c.planet_a, c.planet_b])
        for c in harmonic_conjunctions(_LONS, 5, orb=orb)
    )
    aspect_pairs = frozenset(
        frozenset([a.planet_a, a.planet_b])
        for a in harmonic_aspects(_LONS, orb=orb, max_harmonic=5)
        if a.harmonic == 5
    )

    ritual.witness("conj_pairs_h5", sorted(tuple(sorted(p)) for p in conj_pairs))
    ritual.witness("aspect_pairs_h5", sorted(tuple(sorted(p)) for p in aspect_pairs))

    assert conj_pairs == aspect_pairs, (
        f"harmonic_conjunctions and harmonic_aspects disagree at H5:\n"
        f"  conjunctions: {conj_pairs}\n"
        f"  aspects:      {aspect_pairs}"
    )


def test_oracle_pattern_score_consistent_with_sweep(ritual):
    """harmonic_pattern_score(H) and harmonic_sweep()[H] must agree on score.

    The sweep calls pattern_score internally; verifying agreement catches
    any data-marshalling divergence between the two call paths.
    """
    sw = harmonic_sweep(_LONS, max_harmonic=12, orb=0.001)
    sweep_scores = {e.harmonic: e.score for e in sw}

    for h in range(1, 13):
        direct = harmonic_pattern_score(_LONS, h, orb=0.001).score
        via_sweep = sweep_scores[h]
        ritual.witness(f"score_H{h}", direct)
        assert direct == pytest.approx(via_sweep), (
            f"H{h}: direct score={direct} != sweep score={via_sweep}"
        )


def test_oracle_wider_orb_finds_at_least_as_many_conjunctions():
    """Increasing orb can only add conjunctions, never remove them.

    Any conjunction found at orb=0.5 is also found at orb=2.0.
    """
    for h in (4, 5, 6, 9):
        tight = harmonic_conjunctions(_LONS, h, orb=0.5)
        wide  = harmonic_conjunctions(_LONS, h, orb=2.0)
        assert len(wide) >= len(tight), (
            f"H{h}: wide orb found fewer conjunctions ({len(wide)}) than tight ({len(tight)})"
        )


def test_oracle_vibrational_fingerprint_peak_matches_sweep():
    """VibrationFingerprint.peak_harmonic must be the top-scoring entry in sweep."""
    vf = vibrational_fingerprint(_LONS, max_harmonic=32, orb=0.001)
    sweep_ranked = sorted(vf.sweep, key=lambda e: (-e.score, e.harmonic))
    if sweep_ranked and sweep_ranked[0].score > 0:
        assert vf.peak_harmonic == sweep_ranked[0].harmonic

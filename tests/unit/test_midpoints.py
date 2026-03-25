"""
Tests for moira/midpoints.py — covers all 28 public names.

Phase 1   Public surface ................................ __all__ completeness
Phase 2   Pure math: _midpoint, to_dial family .......... formula verification
Phase 3   Antiscia and contra-antiscia .................. reflection formulas
Phase 4   Core computation: calculate_midpoints ......... enumeration + sorting
Phase 5   midpoints_to_point ............................ proximity search on 360°
Phase 6   midpoint_tree ................................. all four dials
Phase 7   planetary_pictures ............................ A=B/C enumeration
Phase 8   midpoint_weighting ............................ MWA ranking
Phase 9   activated_midpoints ........................... dynamic activation
Phase 10  midpoint_clusters ............................. hotspot detection
Phase 11  Contradiction sweeps (ritual.sweep_taboo) ..... structural invariants
Phase 12  Oracle tests .................................. cross-mode relationships

All tests are pure mathematics — no ephemeris required.
"""
from __future__ import annotations

import math

import pytest

import moira
import moira.midpoints as _mid_mod
from moira.midpoints import (
    CLASSIC_7,
    EXTENDED,
    MODERN_10,
    MODERN_3,
    MidpointCluster,
    MidpointWeight,
    MidpointsService,
    PlanetaryPicture,
    Midpoint,
    activated_midpoints,
    antiscion,
    calculate_midpoints,
    contra_antiscion,
    dial_22_5_midpoints,
    dial_45_midpoints,
    dial_90_midpoints,
    midpoint_clusters,
    midpoint_tree,
    midpoint_weighting,
    midpoints_to_point,
    planetary_pictures,
    to_dial,
    to_dial_22_5,
    to_dial_45,
    to_dial_90,
)


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

# Realistic-ish longitudes — no ephemeris required.
_LONS: dict[str, float] = {
    "Sun":     280.46,
    "Moon":     83.23,
    "Mercury": 257.40,
    "Venus":   275.02,
    "Mars":    347.68,
    "Jupiter":  25.84,
    "Saturn":  337.52,
}

# Constructed so that Mercury sits at the exact Sun/Moon midpoint:
# midpoint(Sun=10°, Moon=50°) = (10+50)/2 = 30° = Mercury
_LONS_EXACT: dict[str, float] = {
    "Sun":     10.0,
    "Moon":    50.0,
    "Mercury": 30.0,   # exact midpoint of Sun/Moon
    "Venus":   100.0,
    "Mars":    200.0,
    "Jupiter": 150.0,
    "Saturn":  300.0,
}

# Constructed for the 90° dial oracle test.
# Sun=0°, Moon=90° → midpoint=45°  → to_dial(45,4)=0°
# Venus=180°                        → to_dial(180,4)=0°  ← same dial position
# So "Venus = Sun/Moon" is a picture on the 90° dial but NOT on the 360° wheel
# (|180° − 45°| = 135°, far outside any reasonable orb).
_LONS_DIAL90_PICTURE: dict[str, float] = {
    "Sun":     0.0,
    "Moon":    90.0,
    "Venus":   180.0,
    "Mercury": 60.0,
    "Mars":    150.0,
    "Jupiter": 240.0,
    "Saturn":  330.0,
}

# Constructed for cluster detection: Sun/Moon=11°, Sun/Mercury=12°, Moon/Mercury=13°
# — three midpoints within 2° of each other on the 360° dial.
_LONS_CLUSTERED: dict[str, float] = {
    "Sun":     10.0,
    "Moon":    12.0,
    "Mercury": 14.0,
    "Venus":   190.0,
    "Mars":    100.0,
    "Jupiter": 200.0,
    "Saturn":  300.0,
}


# ============================================================================
# Phase 1 — Public surface
# ============================================================================

_EXPECTED_PUBLIC = frozenset({
    "Midpoint", "PlanetaryPicture", "MidpointWeight", "MidpointCluster",
    "MidpointsService",
    "CLASSIC_7", "MODERN_3", "MODERN_10", "EXTENDED",
    "calculate_midpoints", "midpoints_to_point",
    "to_dial", "to_dial_90", "to_dial_45", "to_dial_22_5",
    "dial_90_midpoints", "dial_45_midpoints", "dial_22_5_midpoints",
    "midpoint_tree",
    "antiscion", "contra_antiscion",
    "planetary_pictures", "midpoint_weighting",
    "activated_midpoints", "midpoint_clusters",
})


def test_module_all_is_exact():
    """__all__ exposes exactly the 28 expected public names."""
    assert frozenset(_mid_mod.__all__) == _EXPECTED_PUBLIC


def test_internal_names_absent_from_all():
    """No internal _name appears in __all__."""
    leaked = {n for n in _mid_mod.__all__ if n.startswith("_")}
    assert not leaked, f"Internal names in __all__: {leaked}"


def test_parent_package_exports_all_midpoint_names():
    """moira.__all__ re-exports every name in midpoints.__all__."""
    parent_all = frozenset(moira.__all__)
    missing = _EXPECTED_PUBLIC - parent_all
    assert not missing, f"moira.__all__ missing: {missing}"


def test_planet_set_classic_has_7():
    assert len(CLASSIC_7) == 7


def test_planet_set_modern_3_is_outer_planets():
    assert MODERN_3 == {"Uranus", "Neptune", "Pluto"}


def test_planet_set_modern_10_extends_classic():
    assert CLASSIC_7.issubset(MODERN_10)
    assert MODERN_3.issubset(MODERN_10)
    assert len(MODERN_10) == 10


def test_planet_set_extended_is_superset():
    assert MODERN_10.issubset(EXTENDED)


# ============================================================================
# Phase 2 — Pure math: _midpoint and to_dial family
# ============================================================================

def test_midpoint_shorter_arc_no_wraparound():
    """Midpoint of two nearby longitudes is their arithmetic mean."""
    result = _mid_mod._midpoint(10.0, 50.0)
    assert result == pytest.approx(30.0, abs=1e-10)


def test_midpoint_shorter_arc_wraparound():
    """Midpoint of 10° and 350° uses the shorter arc (through 0°), giving 0°."""
    result = _mid_mod._midpoint(10.0, 350.0)
    assert result == pytest.approx(0.0, abs=1e-10)


def test_midpoint_symmetric():
    """_midpoint(a, b) == _midpoint(b, a)."""
    assert _mid_mod._midpoint(80.0, 200.0) == pytest.approx(
        _mid_mod._midpoint(200.0, 80.0), abs=1e-10
    )


def test_midpoint_result_in_range():
    """_midpoint always returns a value in [0, 360)."""
    for a, b in [(0, 0), (359, 1), (180, 360), (90, 270), (0, 180)]:
        result = _mid_mod._midpoint(a, b)
        assert 0.0 <= result < 360.0, f"_midpoint({a},{b}) = {result} out of [0,360)"


@pytest.mark.parametrize("harmonic,multiples", [
    (4,  [0.0, 90.0, 180.0, 270.0]),
    (8,  [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]),
    (16, [i * 22.5 for i in range(16)]),
])
def test_to_dial_collapses_all_harmonic_multiples(harmonic, multiples):
    """All multiples of (360/harmonic) must project to 0° on the dial."""
    for lon in multiples:
        result = to_dial(lon, harmonic)
        assert result == pytest.approx(0.0, abs=1e-9), (
            f"to_dial({lon}, {harmonic}) = {result}, expected 0.0"
        )


def test_to_dial_result_in_range():
    """to_dial result is always in [0, 360/harmonic)."""
    for harmonic in (1, 4, 8, 16):
        dial_size = 360.0 / harmonic
        for lon in [0.0, 45.0, 90.0, 135.0, 180.0, 270.0, 359.9]:
            result = to_dial(lon, harmonic)
            assert 0.0 <= result < dial_size, (
                f"to_dial({lon}, {harmonic}) = {result} outside [0, {dial_size})"
            )


def test_to_dial_90_matches_to_dial_harmonic_4():
    for lon in [0.0, 45.0, 135.0, 190.0, 271.5]:
        assert to_dial_90(lon) == pytest.approx(to_dial(lon, 4), abs=1e-12)


def test_to_dial_45_matches_to_dial_harmonic_8():
    for lon in [0.0, 45.0, 135.0, 190.0, 271.5]:
        assert to_dial_45(lon) == pytest.approx(to_dial(lon, 8), abs=1e-12)


def test_to_dial_22_5_matches_to_dial_harmonic_16():
    for lon in [0.0, 22.5, 67.5, 190.0, 337.5]:
        assert to_dial_22_5(lon) == pytest.approx(to_dial(lon, 16), abs=1e-12)


def test_to_dial_90_known_values():
    """Spot-check: 0°Cap (270°) → 0° on 90° dial; 15°Tau (45°) → 0° on 90° dial."""
    assert to_dial_90(270.0) == pytest.approx(0.0, abs=1e-10)
    assert to_dial_90(45.0)  == pytest.approx(0.0, abs=1e-10)


# ============================================================================
# Phase 3 — Antiscia and contra-antiscia
# ============================================================================

@pytest.mark.parametrize("lon,expected_antiscion", [
    (15.0,  165.0),   # Aries 15°  → Virgo 15°
    (45.0,  135.0),   # Taurus 15° → Leo 15°
    (75.0,  105.0),   # Gemini 15° → Cancer 15°
    (195.0, 345.0),   # Libra 15°  → Pisces 15°
    (225.0, 315.0),   # Scorpio 15° → Aquarius 15°
    (255.0, 285.0),   # Sagittarius 15° → Capricorn 15°
])
def test_antiscion_known_sign_pairs(lon, expected_antiscion):
    """antiscion reflects correctly across the Cancer–Capricorn axis."""
    assert antiscion(lon) == pytest.approx(expected_antiscion, abs=1e-10)


@pytest.mark.parametrize("lon,expected_contra", [
    (15.0,  345.0),   # Aries 15°   → Pisces 15°
    (135.0, 225.0),   # Leo 15°     → Scorpio 15°
    (45.0,  315.0),   # Taurus 15°  → Aquarius 15°
])
def test_contra_antiscion_known_sign_pairs(lon, expected_contra):
    """contra_antiscion reflects correctly across the Aries–Libra axis."""
    assert contra_antiscion(lon) == pytest.approx(expected_contra, abs=1e-10)


def test_contra_antiscion_equals_antiscion_plus_180():
    """contra_antiscion(x) == (antiscion(x) + 180) % 360 for all x."""
    for lon in [0.0, 15.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0, 359.0]:
        expected = (antiscion(lon) + 180.0) % 360.0
        assert contra_antiscion(lon) == pytest.approx(expected, abs=1e-10), (
            f"contra_antiscion({lon}) ≠ antiscion({lon})+180"
        )


@pytest.mark.parametrize("lon", [0.0, 15.0, 90.0, 135.0, 180.0, 225.0, 270.0, 335.7])
def test_antiscion_involution(lon):
    """antiscion(antiscion(x)) == x mod 360."""
    assert antiscion(antiscion(lon)) == pytest.approx(lon % 360.0, abs=1e-9)


@pytest.mark.parametrize("lon", [0.0, 15.0, 90.0, 135.0, 180.0, 225.0, 270.0, 335.7])
def test_contra_antiscion_involution(lon):
    """contra_antiscion(contra_antiscion(x)) == x mod 360."""
    assert contra_antiscion(contra_antiscion(lon)) == pytest.approx(lon % 360.0, abs=1e-9)


def test_antiscion_axis_points_are_fixed():
    """0° Cancer (90°) and 0° Capricorn (270°) are their own antiscia."""
    assert antiscion(90.0)  == pytest.approx(90.0,  abs=1e-10)
    assert antiscion(270.0) == pytest.approx(270.0, abs=1e-10)


def test_antiscion_result_in_range():
    for lon in [0.0, 45.0, 90.0, 180.0, 270.0, 359.9, -10.0, 400.0]:
        result = antiscion(lon)
        assert 0.0 <= result < 360.0, f"antiscion({lon}) = {result} outside [0,360)"


def test_contra_antiscion_result_in_range():
    for lon in [0.0, 45.0, 90.0, 180.0, 270.0, 359.9, -10.0, 400.0]:
        result = contra_antiscion(lon)
        assert 0.0 <= result < 360.0, f"contra_antiscion({lon}) = {result} outside [0,360)"


# ============================================================================
# Phase 4 — calculate_midpoints
# ============================================================================

def test_calculate_midpoints_count_classic():
    """7 planets → C(7,2) = 21 midpoints."""
    mps = calculate_midpoints(_LONS)
    assert len(mps) == 21


def test_calculate_midpoints_sorted_by_longitude():
    """Result is sorted by longitude ascending."""
    mps = calculate_midpoints(_LONS)
    lons = [m.longitude for m in mps]
    assert lons == sorted(lons)


def test_calculate_midpoints_all_in_range():
    """All midpoint longitudes are in [0, 360)."""
    mps = calculate_midpoints(_LONS)
    for m in mps:
        assert 0.0 <= m.longitude < 360.0, f"{m!r} longitude out of range"


def test_calculate_midpoints_planet_labels_present():
    """Every Midpoint record has non-empty planet_a and planet_b."""
    mps = calculate_midpoints(_LONS)
    for m in mps:
        assert isinstance(m.planet_a, str) and m.planet_a
        assert isinstance(m.planet_b, str) and m.planet_b


def test_calculate_midpoints_sign_derived():
    """sign, sign_symbol, sign_degree are populated in every record."""
    mps = calculate_midpoints(_LONS)
    for m in mps:
        assert isinstance(m.sign, str) and m.sign
        assert isinstance(m.sign_symbol, str) and m.sign_symbol
        assert 0.0 <= m.sign_degree < 30.0


def test_calculate_midpoints_modern_planet_set():
    """modern planet_set includes outer planets when present in longitudes."""
    lons_modern = dict(_LONS) | {"Uranus": 40.0, "Neptune": 350.0, "Pluto": 230.0}
    mps = calculate_midpoints(lons_modern, planet_set="modern")
    # C(10,2) = 45 midpoints
    assert len(mps) == 45


def test_calculate_midpoints_unknown_set_defaults_to_classic():
    """Unknown planet_set string silently defaults to CLASSIC_7."""
    mps_default  = calculate_midpoints(_LONS)
    mps_unknown  = calculate_midpoints(_LONS, planet_set="nonexistent")
    assert len(mps_default) == len(mps_unknown)


def test_calculate_midpoints_exact_known_value():
    """midpoint(Sun=10°, Moon=50°) = 30° in _LONS_EXACT."""
    mps = calculate_midpoints(_LONS_EXACT)
    sun_moon = next(
        m for m in mps
        if {m.planet_a, m.planet_b} == {"Sun", "Moon"}
    )
    assert sun_moon.longitude == pytest.approx(30.0, abs=1e-10)


# ============================================================================
# Phase 5 — midpoints_to_point
# ============================================================================

def test_midpoints_to_point_finds_exact_hit():
    """Point at the exact Sun/Moon midpoint returns that pair with orb ≈ 0."""
    hits = midpoints_to_point(30.0, _LONS_EXACT)
    assert any(
        {h.planet_a, h.planet_b} == {"Sun", "Moon"} and orb == pytest.approx(0.0, abs=1e-6)
        for h, orb in hits
    )


def test_midpoints_to_point_sorted_by_orb():
    """Results are sorted tightest orb first."""
    hits = midpoints_to_point(30.0, _LONS_EXACT)
    orbs = [orb for _, orb in hits]
    assert orbs == sorted(orbs)


def test_midpoints_to_point_respects_orb():
    """No result exceeds the specified orb."""
    orb_limit = 1.5
    hits = midpoints_to_point(30.0, _LONS_EXACT, orb=orb_limit)
    for _, orb in hits:
        assert orb <= orb_limit


def test_midpoints_to_point_returns_nothing_outside_orb():
    """With orb=0.001, only the exact Sun/Moon hit is returned."""
    hits = midpoints_to_point(30.0, _LONS_EXACT, orb=0.001)
    assert len(hits) == 1
    assert {hits[0][0].planet_a, hits[0][0].planet_b} == {"Sun", "Moon"}


# ============================================================================
# Phase 6 — midpoint_tree
# ============================================================================

def test_midpoint_tree_360_finds_hits():
    """midpoint_tree on 360° wheel returns (Midpoint, orb) pairs."""
    hits = midpoint_tree(30.0, _LONS_EXACT, orb=1.0, dial=360)
    assert any({h.planet_a, h.planet_b} == {"Sun", "Moon"} for h, _ in hits)


def test_midpoint_tree_90_finds_hits():
    """midpoint_tree on 90° dial returns results."""
    hits = midpoint_tree(0.0, _LONS_DIAL90_PICTURE, orb=1.0, dial=90)
    assert len(hits) > 0


def test_midpoint_tree_45_returns_list():
    hits = midpoint_tree(0.0, _LONS, orb=2.0, dial=45)
    assert isinstance(hits, list)


def test_midpoint_tree_22_5_returns_list():
    hits = midpoint_tree(0.0, _LONS, orb=2.0, dial=22.5)
    assert isinstance(hits, list)


def test_midpoint_tree_sorted_by_orb():
    """Results from midpoint_tree are sorted tightest first."""
    hits = midpoint_tree(30.0, _LONS_EXACT, orb=5.0, dial=360)
    orbs = [orb for _, orb in hits]
    assert orbs == sorted(orbs)


def test_midpoint_tree_respects_orb():
    """No result in tree exceeds the requested orb."""
    orb_limit = 2.0
    hits = midpoint_tree(100.0, _LONS, orb=orb_limit, dial=90)
    for _, orb in hits:
        assert orb <= orb_limit


def test_midpoint_tree_invalid_dial_raises():
    """Unsupported dial value raises ValueError."""
    with pytest.raises(ValueError, match="dial must be"):
        midpoint_tree(0.0, _LONS, dial=60)


def test_dial_90_midpoints_sorted_by_dial_position():
    mps = dial_90_midpoints(_LONS)
    positions = [to_dial_90(m.longitude) for m in mps]
    assert positions == sorted(positions)


def test_dial_45_midpoints_sorted_by_dial_position():
    mps = dial_45_midpoints(_LONS)
    positions = [to_dial_45(m.longitude) for m in mps]
    assert positions == sorted(positions)


def test_dial_22_5_midpoints_sorted_by_dial_position():
    mps = dial_22_5_midpoints(_LONS)
    positions = [to_dial_22_5(m.longitude) for m in mps]
    assert positions == sorted(positions)


def test_all_dial_sort_functions_return_same_members():
    """dial_*_midpoints returns the same set of midpoints, only sorted differently."""
    mps_360 = calculate_midpoints(_LONS)
    mps_90  = dial_90_midpoints(_LONS)
    mps_45  = dial_45_midpoints(_LONS)
    mps_22  = dial_22_5_midpoints(_LONS)
    key = lambda m: (m.planet_a, m.planet_b)
    assert sorted(mps_360, key=key) == sorted(mps_90,  key=key)
    assert sorted(mps_360, key=key) == sorted(mps_45,  key=key)
    assert sorted(mps_360, key=key) == sorted(mps_22,  key=key)


# ============================================================================
# Phase 7 — planetary_pictures
# ============================================================================

def test_planetary_pictures_returns_list_of_correct_type():
    pics = planetary_pictures(_LONS_EXACT)
    assert all(isinstance(p, PlanetaryPicture) for p in pics)


def test_planetary_pictures_focus_not_in_pair():
    """Focus planet is never a member of its own generating pair."""
    for pic in planetary_pictures(_LONS_EXACT, orb=5.0):
        assert pic.focus not in (pic.pair_a, pic.pair_b), (
            f"{pic!r}: focus appears in its own pair"
        )


def test_planetary_pictures_sorted_by_orb():
    pics = planetary_pictures(_LONS_EXACT, orb=5.0)
    orbs = [p.orb for p in pics]
    assert orbs == sorted(orbs)


def test_planetary_pictures_orb_within_threshold():
    orb_limit = 2.0
    for pic in planetary_pictures(_LONS_EXACT, orb=orb_limit):
        assert pic.orb <= orb_limit


def test_planetary_pictures_known_exact():
    """Mercury = Sun/Moon picture has orb ≈ 0 in _LONS_EXACT."""
    pics = planetary_pictures(_LONS_EXACT, orb=1.0, dial=360)
    mercury_sun_moon = [
        p for p in pics
        if p.focus == "Mercury" and {p.pair_a, p.pair_b} == {"Sun", "Moon"}
    ]
    assert len(mercury_sun_moon) == 1
    assert mercury_sun_moon[0].orb == pytest.approx(0.0, abs=1e-6)


def test_planetary_pictures_dial_stored_correctly():
    for dial_val in [360.0, 90.0, 45.0, 22.5]:
        pics = planetary_pictures(_LONS_EXACT, orb=5.0, dial=dial_val)
        assert all(p.dial == dial_val for p in pics)


def test_planetary_pictures_invalid_dial_raises():
    with pytest.raises(ValueError):
        planetary_pictures(_LONS, dial=60.0)


# ============================================================================
# Phase 8 — midpoint_weighting
# ============================================================================

def test_midpoint_weighting_returns_all_planets():
    """Every planet in the classic set appears in the result."""
    weights = midpoint_weighting(_LONS)
    planets = {w.planet for w in weights}
    # All classic planets present in input are included
    input_planets = {n.strip().title() for n in _LONS if n.strip().title() in CLASSIC_7}
    assert input_planets.issubset(planets)


def test_midpoint_weighting_sorted_by_score_descending():
    weights = midpoint_weighting(_LONS, orb=3.0)
    scores = [w.score for w in weights]
    assert scores == sorted(scores, reverse=True)


def test_midpoint_weighting_score_equals_len_pictures():
    """score == len(pictures) for every MidpointWeight."""
    for w in midpoint_weighting(_LONS, orb=3.0):
        assert w.score == len(w.pictures), (
            f"{w.planet}: score={w.score} != len(pictures)={len(w.pictures)}"
        )


def test_midpoint_weighting_total_equals_planetary_pictures_count():
    """Sum of all scores equals total number of planetary pictures."""
    orb = 2.0
    pics    = planetary_pictures(_LONS, orb=orb)
    weights = midpoint_weighting(_LONS, orb=orb)
    assert sum(w.score for w in weights) == len(pics)


def test_midpoint_weighting_pictures_sorted_by_orb():
    """Each MidpointWeight.pictures tuple is sorted by orb, tightest first."""
    for w in midpoint_weighting(_LONS, orb=3.0):
        orbs = [p.orb for p in w.pictures]
        assert orbs == sorted(orbs), (
            f"{w.planet}: pictures not sorted by orb"
        )


def test_midpoint_weighting_exact_planet_has_nonzero_score():
    """Mercury has score >= 1 with orb=0.1 since it sits exactly on Sun/Moon."""
    weights = {w.planet: w for w in midpoint_weighting(_LONS_EXACT, orb=0.1)}
    assert "Mercury" in weights
    assert weights["Mercury"].score >= 1


# ============================================================================
# Phase 9 — activated_midpoints
# ============================================================================

def test_activated_midpoints_exact_hit_360():
    """Transit at exact Sun/Moon midpoint (30°) returns that pair with orb ≈ 0."""
    natal_mps = calculate_midpoints(_LONS_EXACT)
    hits = activated_midpoints(30.0, natal_mps, orb=1.0, dial=360)
    assert any(
        {h.planet_a, h.planet_b} == {"Sun", "Moon"} and orb == pytest.approx(0.0, abs=1e-6)
        for h, orb in hits
    )


def test_activated_midpoints_sorted_by_orb():
    natal_mps = calculate_midpoints(_LONS_EXACT)
    hits = activated_midpoints(30.0, natal_mps, orb=10.0, dial=360)
    orbs = [orb for _, orb in hits]
    assert orbs == sorted(orbs)


def test_activated_midpoints_respects_orb():
    natal_mps = calculate_midpoints(_LONS)
    orb_limit = 1.5
    hits = activated_midpoints(100.0, natal_mps, orb=orb_limit, dial=360)
    for _, orb in hits:
        assert orb <= orb_limit


def test_activated_midpoints_on_90_dial():
    """Venus at 180° activates the Sun/Moon midpoint (45°) on the 90° dial."""
    natal_mps = calculate_midpoints(_LONS_DIAL90_PICTURE)
    hits = activated_midpoints(180.0, natal_mps, orb=0.5, dial=90)
    sun_moon_hit = [h for h, _ in hits if {h.planet_a, h.planet_b} == {"Sun", "Moon"}]
    assert len(sun_moon_hit) >= 1


def test_activated_midpoints_returns_midpoint_instances():
    natal_mps = calculate_midpoints(_LONS)
    hits = activated_midpoints(90.0, natal_mps, orb=5.0, dial=90)
    assert all(isinstance(h, Midpoint) for h, _ in hits)


def test_activated_midpoints_invalid_dial_raises():
    natal_mps = calculate_midpoints(_LONS)
    with pytest.raises(ValueError):
        activated_midpoints(0.0, natal_mps, dial=60.0)


# ============================================================================
# Phase 10 — midpoint_clusters
# ============================================================================

def test_midpoint_clusters_detects_known_cluster():
    """_LONS_CLUSTERED has Sun/Moon=11°, Sun/Mercury=12°, Moon/Mercury=13°.
    With cluster_orb=2.0 on 360° wheel, all three should form one cluster."""
    clusters = midpoint_clusters(
        _LONS_CLUSTERED, cluster_orb=2.0, min_size=3, dial=360
    )
    assert len(clusters) >= 1
    # The largest cluster should contain the three known midpoints
    top = clusters[0]
    pairs_in_top = [{m.planet_a, m.planet_b} for m in top.midpoints]
    assert {"Sun", "Moon"}    in pairs_in_top
    assert {"Sun", "Mercury"} in pairs_in_top
    assert {"Moon", "Mercury"} in pairs_in_top


def test_midpoint_clusters_min_size_respected():
    """No cluster returned with fewer members than min_size."""
    for min_sz in [2, 3, 4]:
        clusters = midpoint_clusters(_LONS, cluster_orb=1.5, min_size=min_sz, dial=90)
        for c in clusters:
            assert len(c.midpoints) >= min_sz


def test_midpoint_clusters_sorted_by_size_descending():
    clusters = midpoint_clusters(_LONS_CLUSTERED, cluster_orb=2.0, min_size=2, dial=360)
    sizes = [len(c.midpoints) for c in clusters]
    assert sizes == sorted(sizes, reverse=True)


def test_midpoint_clusters_dial_position_in_range():
    """dial_position is always within [0, dial)."""
    for dial_val in [360.0, 90.0, 45.0, 22.5]:
        clusters = midpoint_clusters(_LONS, cluster_orb=2.0, min_size=2, dial=dial_val)
        for c in clusters:
            assert 0.0 <= c.dial_position < dial_val, (
                f"dial_position={c.dial_position} outside [0, {dial_val})"
            )


def test_midpoint_clusters_spread_nonneg():
    """spread is always >= 0."""
    clusters = midpoint_clusters(_LONS_CLUSTERED, cluster_orb=3.0, min_size=2, dial=360)
    for c in clusters:
        assert c.spread >= 0.0


def test_midpoint_clusters_dial_field_matches_parameter():
    for dial_val in [90.0, 45.0]:
        clusters = midpoint_clusters(_LONS, cluster_orb=2.0, min_size=2, dial=dial_val)
        for c in clusters:
            assert c.dial == dial_val


def test_midpoint_clusters_empty_when_no_cluster():
    """Returns empty list when no cluster of required size exists."""
    # Use a very tight orb on a realistic chart — unlikely to find min_size=10
    clusters = midpoint_clusters(_LONS, cluster_orb=0.01, min_size=10, dial=90)
    assert clusters == []


def test_midpoint_clusters_invalid_dial_raises():
    with pytest.raises(ValueError):
        midpoint_clusters(_LONS, dial=60.0)


def test_midpoint_clusters_members_are_midpoint_instances():
    clusters = midpoint_clusters(_LONS_CLUSTERED, cluster_orb=2.0, min_size=2, dial=360)
    for c in clusters:
        assert all(isinstance(m, Midpoint) for m in c.midpoints)


# ============================================================================
# Phase 11 — Contradiction sweeps (ritual.sweep_taboo)
# ============================================================================

def test_sweep_midpoints_longitude_in_range(ritual):
    """All midpoints from calculate_midpoints are in [0, 360)."""
    mps = calculate_midpoints(_LONS)
    ritual.sweep_taboo(
        "midpoint_longitude_out_of_range",
        items=mps,
        forbidden=lambda m: not (0.0 <= m.longitude < 360.0),
        context=lambda m: f"{m!r}",
        unpack=False,
    )


def test_sweep_planetary_pictures_orb_nonneg(ritual):
    """All planetary pictures have orb >= 0."""
    pics = planetary_pictures(_LONS, orb=3.0, dial=90)
    ritual.sweep_taboo(
        "negative_picture_orb",
        items=pics,
        forbidden=lambda p: p.orb < 0.0,
        context=lambda p: repr(p),
        unpack=False,
    )


def test_sweep_mwa_score_equals_pictures_len(ritual):
    """score == len(pictures) for every MidpointWeight."""
    weights = midpoint_weighting(_LONS, orb=3.0)
    ritual.sweep_taboo(
        "mwa_score_mismatch",
        items=weights,
        forbidden=lambda w: w.score != len(w.pictures),
        context=lambda w: f"planet={w.planet!r}, score={w.score}, len={len(w.pictures)}",
        unpack=False,
    )


def test_sweep_clusters_spread_nonneg(ritual):
    """spread >= 0 for every MidpointCluster on every dial."""
    for dial_val in [360.0, 90.0, 45.0]:
        clusters = midpoint_clusters(
            _LONS_CLUSTERED, cluster_orb=3.0, min_size=2, dial=dial_val
        )
        ritual.sweep_taboo(
            "negative_cluster_spread",
            items=clusters,
            forbidden=lambda c: c.spread < 0.0,
            context=lambda c: repr(c),
            unpack=False,
        )


def test_sweep_clusters_min_size_invariant(ritual):
    """No cluster has fewer members than the requested min_size."""
    min_size = 3
    clusters = midpoint_clusters(_LONS_CLUSTERED, cluster_orb=2.0, min_size=min_size, dial=360)
    ritual.sweep_taboo(
        "cluster_below_min_size",
        items=clusters,
        forbidden=lambda c: len(c.midpoints) < min_size,
        context=lambda c: f"size={len(c.midpoints)}, cluster={c!r}",
        unpack=False,
    )


# ============================================================================
# Phase 12 — Oracle tests
# ============================================================================

def test_oracle_90_dial_finds_at_least_as_many_pictures_as_360(ritual):
    """The 90° dial finds >= pictures than the 360° wheel at the same orb.

    Adding harmonic equivalences can only discover more pictures, never fewer.
    Venus = Sun/Moon is found on the 90° dial but not the 360° wheel.
    """
    orb = 0.5
    pics_360 = planetary_pictures(_LONS_DIAL90_PICTURE, orb=orb, dial=360)
    pics_90  = planetary_pictures(_LONS_DIAL90_PICTURE, orb=orb, dial=90)

    ritual.witness("pictures_360_dial90_test", len(pics_360))
    ritual.witness("pictures_90_dial90_test",  len(pics_90))

    assert len(pics_90) >= len(pics_360), (
        f"90° dial found fewer pictures ({len(pics_90)}) than 360° ({len(pics_360)})"
    )
    # Specifically, the Venus=Sun/Moon picture must appear on 90° but not 360°
    venus_pic_90  = [p for p in pics_90  if p.focus == "Venus" and {p.pair_a, p.pair_b} == {"Sun", "Moon"}]
    venus_pic_360 = [p for p in pics_360 if p.focus == "Venus" and {p.pair_a, p.pair_b} == {"Sun", "Moon"}]
    assert len(venus_pic_90)  >= 1, "Venus=Sun/Moon not found on 90° dial"
    assert len(venus_pic_360) == 0, "Venus=Sun/Moon should NOT be found on 360° wheel"


def test_oracle_activated_midpoints_agrees_with_midpoints_to_point(ritual):
    """activated_midpoints and midpoints_to_point return the same pairs on 360°.

    Both functions search for natal midpoints within orb of a target longitude.
    They must agree on which pairs are activated.
    """
    natal_mps = calculate_midpoints(_LONS_EXACT)
    target    = 30.0
    orb       = 5.0

    hits_activated = activated_midpoints(target, natal_mps, orb=orb, dial=360)
    hits_to_point  = midpoints_to_point(target, _LONS_EXACT, orb=orb)

    pairs_activated = frozenset(
        frozenset([h.planet_a, h.planet_b]) for h, _ in hits_activated
    )
    pairs_to_point = frozenset(
        frozenset([h.planet_a, h.planet_b]) for h, _ in hits_to_point
    )

    ritual.witness("activated_pairs", sorted(str(p) for p in pairs_activated))
    ritual.witness("to_point_pairs",  sorted(str(p) for p in pairs_to_point))

    assert pairs_activated == pairs_to_point, (
        f"activated_midpoints and midpoints_to_point disagree:\n"
        f"  activated:  {pairs_activated}\n"
        f"  to_point:   {pairs_to_point}"
    )


def test_oracle_cluster_members_are_subset_of_all_midpoints():
    """Every member of every cluster is in the full midpoints list."""
    all_mps  = calculate_midpoints(_LONS_CLUSTERED)
    all_keys = {(m.planet_a, m.planet_b) for m in all_mps}

    clusters = midpoint_clusters(_LONS_CLUSTERED, cluster_orb=2.0, min_size=2, dial=360)
    for c in clusters:
        for m in c.midpoints:
            assert (m.planet_a, m.planet_b) in all_keys, (
                f"Cluster member {m!r} not found in calculate_midpoints result"
            )


def test_oracle_finer_dial_finds_more_or_equal_clusters():
    """Finer dials collapse more aspects, so cluster counts can only increase.

    On the 45° dial the same physical degrees are visited by more combinations
    than on the 90° dial — any two midpoints within orb on the 90° dial are
    also within orb on the 45° dial (the dial is smaller but the orb is the
    same absolute degrees), so cluster counts should be >= the 90° result.
    """
    n_clusters_90 = len(midpoint_clusters(_LONS, cluster_orb=2.0, min_size=2, dial=90))
    n_clusters_45 = len(midpoint_clusters(_LONS, cluster_orb=2.0, min_size=2, dial=45))
    # Finer dial projects more midpoints closer together → at least as many clusters
    assert n_clusters_45 >= n_clusters_90

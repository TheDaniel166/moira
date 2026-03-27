"""
Tests for moira/void_of_course.py — covers all 12 VALIDATION CODEX rules.

Phase 1  Public surface + pure functions (no ephemeris) .... RULE-12, RULE-07, RULE-08
Phase 2  Result vessel structure ............................. RULE-01, RULE-03, RULE-04, RULE-05
Phase 3  API behaviour + sign validity ....................... RULE-02, RULE-09, RULE-10, RULE-11
Phase 4  Contradiction sweeps (ritual.sweep_taboo) .......... RULE-03, RULE-04, RULE-05, RULE-09
Phase 5  Oracle tests (cross-mode + sign-stability) ......... RULE-07 relationship, RULE-02
Phase 6  No-aspect VOC ....................................... RULE-06

Scan anchor: J2000 + 14 days (~4–5 Moon sign transits). Heavy tests use the
`voc_scan_windows` session fixture to avoid recomputing the range repeatedly.
"""
from __future__ import annotations

import pytest

import moira
import moira.void_of_course as _voc_mod
from moira.constants import SIGNS
from moira.void_of_course import (
    LastAspect,
    VoidOfCourseWindow,
    is_void_of_course,
    next_void_of_course,
    void_of_course_window,
    void_periods_in_range,
)

# ---------------------------------------------------------------------------
# Scan range constants — J2000 + 14 days covers ~4–5 Moon sign transits.
# Used by sweep fixtures.  Widened to 30 days for RULE-06 search.
# ---------------------------------------------------------------------------
_SCAN_START = 2451545.0       # J2000.0
_SCAN_END   = 2451559.0       # +14 days
_SCAN_END_WIDE = 2451575.0    # +30 days


# ---------------------------------------------------------------------------
# Session fixture: pre-compute the 14-day window list once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def voc_scan_windows(moira_engine):
    """All VOC windows in the 14-day J2000 scan range (computed once per session)."""
    return void_periods_in_range(_SCAN_START, _SCAN_END)


# ============================================================================
# Phase 1 — Public surface and pure functions (no ephemeris needed)
# ============================================================================

_EXPECTED_PUBLIC = frozenset({
    "LastAspect",
    "VoidOfCourseWindow",
    "void_of_course_window",
    "is_void_of_course",
    "next_void_of_course",
    "void_periods_in_range",
})

_EXPECTED_INTERNAL = frozenset({
    "_TRADITIONAL_BODIES", "_MODERN_BODIES", "_ASPECT_TARGETS",
    "_ASPECT_NAMES", "_MAX_SIGN_TRANSIT_DAYS", "_SCAN_STEP",
    "_BISECT_ITER", "_BISECT_TOL",
    "_moon_longitude", "_planet_longitude", "_moon_sign_index",
    "_moon_last_sign_ingress", "_moon_next_sign_ingress",
    "_aspect_signal", "_bisect_aspect", "_find_aspect_perfections",
    "_build_voc_window",
})


def test_module_all_is_exact():
    """RULE-12: void_of_course.__all__ exposes exactly the six public names."""
    assert frozenset(_voc_mod.__all__) == _EXPECTED_PUBLIC


def test_internal_names_absent_from_all():
    """RULE-12: no internal _name appears in __all__."""
    leaked = _EXPECTED_INTERNAL & frozenset(_voc_mod.__all__)
    assert not leaked, f"Internal names leaked into __all__: {leaked}"


def test_traditional_body_count():
    """RULE-07: _TRADITIONAL_BODIES contains exactly 6 bodies."""
    assert len(_voc_mod._TRADITIONAL_BODIES) == 6


def test_traditional_body_names():
    """RULE-07: traditional set is exactly Sun, Mercury, Venus, Mars, Jupiter, Saturn."""
    from moira.constants import Body
    expected = {Body.SUN, Body.MERCURY, Body.VENUS, Body.MARS, Body.JUPITER, Body.SATURN}
    assert set(_voc_mod._TRADITIONAL_BODIES) == expected


def test_modern_body_count():
    """RULE-07 corollary: modern set adds exactly 3 outer planets (9 total)."""
    assert len(_voc_mod._MODERN_BODIES) == 9


def test_modern_bodies_extend_traditional():
    """RULE-07: every traditional body is also in the modern set."""
    trad = set(_voc_mod._TRADITIONAL_BODIES)
    mod  = set(_voc_mod._MODERN_BODIES)
    assert trad.issubset(mod), f"Traditional bodies missing from modern: {trad - mod}"


def test_aspect_target_count():
    """RULE-08: _ASPECT_TARGETS contains exactly 8 values."""
    assert len(_voc_mod._ASPECT_TARGETS) == 8


def test_aspect_target_values():
    """RULE-08: targets are exactly {0, 60, 90, 120, 180, 240, 270, 300} degrees."""
    assert set(_voc_mod._ASPECT_TARGETS) == {0.0, 60.0, 90.0, 120.0, 180.0, 240.0, 270.0, 300.0}


# --- Pure function: _aspect_signal ------------------------------------------
# The crossing-detection formula is frozen; these tests verify it in isolation.

def test_aspect_signal_at_exact_conjunction():
    """Formula: signal == 0 at exact Moon–planet conjunction (target=0)."""
    assert _voc_mod._aspect_signal(90.0, 90.0, 0.0) == pytest.approx(0.0, abs=1e-10)


def test_aspect_signal_at_exact_trine():
    """Formula: signal == 0 when Moon is exactly 120° ahead (target=120)."""
    assert _voc_mod._aspect_signal(210.0, 90.0, 120.0) == pytest.approx(0.0, abs=1e-10)


def test_aspect_signal_at_exact_opposition():
    """Formula: signal == 0 at exact 180° separation (target=180)."""
    assert _voc_mod._aspect_signal(270.0, 90.0, 180.0) == pytest.approx(0.0, abs=1e-10)


def test_aspect_signal_changes_sign_at_crossing():
    """Formula: signal flips negative→positive as Moon crosses a trine (target=120)."""
    before = _voc_mod._aspect_signal(209.9, 90.0, 120.0)
    after  = _voc_mod._aspect_signal(210.1, 90.0, 120.0)
    assert before < 0.0
    assert after  > 0.0


def test_aspect_signal_guard_rejects_wraparound_false_positive():
    """Guard: large-magnitude signal jump at opposition point for target=0 is suppressed.

    When the Moon–planet separation passes through 180° while scanning for
    target=0 (Conjunction), the signal jumps from ~+179 to ~-179.  The guard
    ``abs(sig_prev) < 90 and abs(sig_next) < 90`` must reject this crossing
    because neither magnitude is below 90.
    """
    sig_before = _voc_mod._aspect_signal(269.0, 90.0, 0.0)   # sep ≈ 179°
    sig_after  = _voc_mod._aspect_signal(271.0, 90.0, 0.0)   # sep ≈ 181°
    # Signs DO flip (which would look like a crossing without the guard)
    assert sig_before * sig_after < 0.0
    # But both magnitudes are > 90 → guard correctly rejects this
    assert abs(sig_before) > 90.0
    assert abs(sig_after)  > 90.0


def test_aspect_signal_real_conjunction_passes_guard():
    """Guard: a genuine Conjunction crossing has small-magnitude signals (< 90)."""
    sig_before = _voc_mod._aspect_signal(89.9, 90.0, 0.0)    # just before conjunction
    sig_after  = _voc_mod._aspect_signal(90.1, 90.0, 0.0)    # just after
    assert sig_before * sig_after < 0.0     # sign change
    assert abs(sig_before) < 90.0           # passes guard
    assert abs(sig_after)  < 90.0           # passes guard


# ============================================================================
# Phase 2 — Result vessel structure (ephemeris required)
# ============================================================================

def test_window_returns_vocwindow_type(moira_engine, jd_j2000):
    """RULE-01: void_of_course_window always returns a VoidOfCourseWindow instance."""
    result = void_of_course_window(jd_j2000)
    assert isinstance(result, VoidOfCourseWindow)


def test_window_never_raises_for_valid_jd(moira_engine, jd_j2000):
    """RULE-01: does not raise for a standard finite JD."""
    void_of_course_window(jd_j2000)   # must not raise


def test_window_vessel_fields_typed(moira_engine, jd_j2000, ritual):
    """RULE-01: every field of the result vessel has the correct type."""
    window = ritual.witness("voc_window_j2000", void_of_course_window(jd_j2000))
    assert isinstance(window.moon_sign,      str)
    assert isinstance(window.moon_sign_next, str)
    assert isinstance(window.jd_voc_start,   float)
    assert isinstance(window.jd_voc_end,     float)
    assert isinstance(window.duration_hours, float)
    assert window.last_aspect is None or isinstance(window.last_aspect, LastAspect)


def test_last_aspect_fields_when_present(moira_engine, voc_scan_windows):
    """RULE-01: when last_aspect is not None its fields are correctly typed."""
    windows_with_aspect = [w for w in voc_scan_windows if w.last_aspect is not None]
    if not windows_with_aspect:
        pytest.skip("no window with last_aspect found in scan range")
    la = windows_with_aspect[0].last_aspect
    assert isinstance(la.body,        str)
    assert isinstance(la.aspect_name, str)
    assert isinstance(la.angle,       float)
    assert isinstance(la.jd_exact,    float)
    assert la.angle in _voc_mod._ASPECT_TARGETS
    assert la.aspect_name in _voc_mod._ASPECT_NAMES.values()


def test_window_ordering_j2000(moira_engine, jd_j2000):
    """RULE-03: jd_voc_start ≤ jd_voc_end for the J2000 window."""
    window = void_of_course_window(jd_j2000)
    assert window.jd_voc_start <= window.jd_voc_end


def test_duration_is_derived_j2000(moira_engine, jd_j2000):
    """RULE-04: duration_hours == (jd_voc_end − jd_voc_start) × 24 within 1e-9."""
    window   = void_of_course_window(jd_j2000)
    expected = (window.jd_voc_end - window.jd_voc_start) * 24.0
    assert abs(window.duration_hours - expected) < 1e-9


def test_is_long_true_when_duration_exceeds_12(moira_engine, voc_scan_windows):
    """RULE-05: is_long is True for every window whose duration_hours > 12.0."""
    long_windows = [w for w in voc_scan_windows if w.duration_hours > 12.0]
    if not long_windows:
        pytest.skip("no long VOC window found in 14-day scan")
    for w in long_windows:
        assert w.is_long, f"Expected is_long=True for duration {w.duration_hours:.4f}h"


def test_is_long_false_when_duration_at_most_12(moira_engine, voc_scan_windows):
    """RULE-05: is_long is False for every window whose duration_hours ≤ 12.0."""
    short_windows = [w for w in voc_scan_windows if w.duration_hours <= 12.0]
    if not short_windows:
        pytest.skip("no short VOC window found in 14-day scan")
    for w in short_windows:
        assert not w.is_long, f"Expected is_long=False for duration {w.duration_hours:.4f}h"


# ============================================================================
# Phase 3 — API behaviour and sign name validity
# ============================================================================

def test_is_voc_at_j2000_agrees_with_window(moira_engine, jd_j2000):
    """RULE-02: is_void_of_course at J2000 matches window bound check."""
    window     = void_of_course_window(jd_j2000)
    in_window  = window.jd_voc_start <= jd_j2000 <= window.jd_voc_end
    assert is_void_of_course(jd_j2000) == in_window


def test_is_voc_true_at_window_midpoint(moira_engine, voc_scan_windows):
    """RULE-02: is_void_of_course returns True at the midpoint of each window."""
    for window in voc_scan_windows:
        jd_mid = (window.jd_voc_start + window.jd_voc_end) / 2.0
        assert is_void_of_course(jd_mid) is True, (
            f"is_voc returned False at midpoint of {window!r}"
        )


def test_sign_names_valid_j2000(moira_engine, jd_j2000):
    """RULE-09: moon_sign and moon_sign_next are members of moira.constants.SIGNS."""
    window = void_of_course_window(jd_j2000)
    assert window.moon_sign      in SIGNS, f"{window.moon_sign!r} not in SIGNS"
    assert window.moon_sign_next in SIGNS, f"{window.moon_sign_next!r} not in SIGNS"


def test_next_voc_is_strictly_future(moira_engine, jd_j2000):
    """RULE-10: next_void_of_course(jd).jd_voc_start > jd."""
    result = next_void_of_course(jd_j2000)
    assert result is not None, "next_void_of_course returned None within 60 days of J2000"
    assert result.jd_voc_start > jd_j2000


def test_range_is_chronologically_sorted(moira_engine, voc_scan_windows):
    """RULE-11: void_periods_in_range returns windows sorted by jd_voc_start."""
    starts = [w.jd_voc_start for w in voc_scan_windows]
    assert starts == sorted(starts), "VOC windows are not in chronological order"


def test_range_contains_multiple_windows(moira_engine, voc_scan_windows):
    """Smoke: 14-day range contains at least 2 complete VOC windows."""
    assert len(voc_scan_windows) >= 2, (
        f"Expected ≥2 VOC windows in 14-day scan, got {len(voc_scan_windows)}"
    )


# ============================================================================
# Phase 4 — Contradiction sweeps (ritual.sweep_taboo)
# ============================================================================

def test_sweep_no_inverted_ordering(moira_engine, voc_scan_windows, ritual):
    """RULE-03 (sweep): jd_voc_start ≤ jd_voc_end for every window in 14-day range."""
    ritual.sweep_taboo(
        "inverted_voc_window",
        items=voc_scan_windows,
        forbidden=lambda w: w.jd_voc_start > w.jd_voc_end,
        context=lambda w: repr(w),
        unpack=False,
    )


def test_sweep_duration_is_derived(moira_engine, voc_scan_windows, ritual):
    """RULE-04 (sweep): duration_hours == (end − start) × 24 for every window."""
    ritual.sweep_taboo(
        "duration_not_derived",
        items=voc_scan_windows,
        forbidden=lambda w: abs(
            w.duration_hours - (w.jd_voc_end - w.jd_voc_start) * 24.0
        ) > 1e-9,
        context=lambda w: (
            f"duration_hours={w.duration_hours:.12f}, "
            f"computed={(w.jd_voc_end - w.jd_voc_start) * 24.0:.12f}"
        ),
        unpack=False,
    )


def test_sweep_is_long_threshold_consistent(moira_engine, voc_scan_windows, ritual):
    """RULE-05 (sweep): is_long == (duration_hours > 12.0) for every window."""
    ritual.sweep_taboo(
        "is_long_threshold_broken",
        items=voc_scan_windows,
        forbidden=lambda w: w.is_long != (w.duration_hours > 12.0),
        context=lambda w: f"is_long={w.is_long}, duration={w.duration_hours:.6f}h",
        unpack=False,
    )


def test_sweep_sign_names_valid(moira_engine, voc_scan_windows, ritual):
    """RULE-09 (sweep): both moon_sign and moon_sign_next are in SIGNS for every window."""
    ritual.sweep_taboo(
        "invalid_sign_name",
        items=voc_scan_windows,
        forbidden=lambda w: w.moon_sign not in SIGNS or w.moon_sign_next not in SIGNS,
        context=lambda w: (
            f"moon_sign={w.moon_sign!r}, moon_sign_next={w.moon_sign_next!r}"
        ),
        unpack=False,
    )


def test_sweep_is_voc_agrees_with_window(moira_engine, voc_scan_windows, ritual):
    """RULE-02 (sweep): is_void_of_course is True at the midpoint of every window."""
    ritual.sweep_taboo(
        "is_voc_disagrees_with_window_midpoint",
        items=voc_scan_windows,
        forbidden=lambda w: not is_void_of_course(
            (w.jd_voc_start + w.jd_voc_end) / 2.0
        ),
        context=lambda w: repr(w),
        unpack=False,
    )


def test_sweep_no_negative_duration(moira_engine, voc_scan_windows, ritual):
    """Invariant (sweep): duration_hours is never negative."""
    ritual.sweep_taboo(
        "negative_voc_duration",
        items=voc_scan_windows,
        forbidden=lambda w: w.duration_hours < 0.0,
        context=lambda w: f"duration_hours={w.duration_hours:.6f}",
        unpack=False,
    )


# ============================================================================
# Phase 5 — Oracle tests
# ============================================================================

def test_modern_voc_starts_no_earlier_than_traditional(moira_engine, jd_j2000, ritual):
    """RULE-07 oracle: adding outer planets can only delay or preserve the VOC start.

    More bodies → more potential aspect perfections → the last one can only
    be equal or later in time.  Both modes share the same sign exit (jd_voc_end).
    """
    trad   = void_of_course_window(jd_j2000, modern=False)
    modern = void_of_course_window(jd_j2000, modern=True)

    ritual.witness("voc_traditional_j2000", trad)
    ritual.witness("voc_modern_j2000", modern)

    # Same sign transit → identical sign exit
    assert abs(trad.jd_voc_end - modern.jd_voc_end) < 1e-5, (
        f"Expected same sign exit: trad={trad.jd_voc_end}, modern={modern.jd_voc_end}"
    )
    # More bodies → VOC start is equal or later
    assert modern.jd_voc_start >= trad.jd_voc_start - 1e-6, (
        f"modern VOC starts earlier than traditional: "
        f"modern={modern.jd_voc_start:.6f} < trad={trad.jd_voc_start:.6f}"
    )


def test_window_stable_within_same_sign_transit(moira_engine, jd_j2000, ritual):
    """Oracle: any JD in the same Moon sign transit returns the identical window.

    void_of_course_window is keyed to the Moon's sign, not to the query time.
    Querying at J2000 and at the midpoint of its window must yield the same
    jd_voc_start, jd_voc_end, moon_sign, and moon_sign_next.
    """
    window_ref = void_of_course_window(jd_j2000)
    jd_mid     = (window_ref.jd_voc_start + window_ref.jd_voc_end) / 2.0
    window_mid = void_of_course_window(jd_mid)

    ritual.cross_witness(
        window_ref, window_mid,
        keys=["jd_voc_start", "jd_voc_end", "moon_sign", "moon_sign_next"],
        abs_tol=1e-5,
        label="same sign transit → identical window bounds",
    )


def test_next_voc_is_a_vocwindow(moira_engine, jd_j2000):
    """RULE-10: next_void_of_course returns a proper VoidOfCourseWindow."""
    result = next_void_of_course(jd_j2000)
    assert result is not None
    assert isinstance(result, VoidOfCourseWindow)
    # And the window itself satisfies the structural invariants
    assert result.jd_voc_start <= result.jd_voc_end
    assert abs(result.duration_hours - (result.jd_voc_end - result.jd_voc_start) * 24.0) < 1e-9
    assert result.moon_sign      in SIGNS
    assert result.moon_sign_next in SIGNS


def test_range_windows_ordered_temporal_covenant(moira_engine, voc_scan_windows, ritual):
    """RULE-11 temporal: consecutive windows in range are chronologically ordered."""
    starts = [w.jd_voc_start for w in voc_scan_windows]
    ritual.temporal_covenant(
        starts,
        lambda a, b: a <= b,
        label="VOC windows must be sorted by jd_voc_start",
    )


# ============================================================================
# Phase 6 — No-aspect VOC (RULE-06)
# ============================================================================

def test_no_aspect_voc_last_aspect_is_none(moira_engine):
    """RULE-06: when Moon enters sign already VOC, last_aspect is None.

    Scans 30 days for a no-aspect window.  If found, verifies the structural
    invariant: querying at jd_voc_start + epsilon returns the same jd_voc_start,
    proving it is the sign-entry time, not an aspect perfection time.
    """
    windows = void_periods_in_range(_SCAN_START, _SCAN_END_WIDE)
    no_aspect = [w for w in windows if w.last_aspect is None]

    if not no_aspect:
        pytest.skip("no no-aspect VOC window found in 30-day scan — RULE-06 not exercised")

    for w in no_aspect:
        # Probe just inside the window: the window must be stable
        jd_probe    = w.jd_voc_start + 0.001
        window_probe = void_of_course_window(jd_probe)
        assert abs(window_probe.jd_voc_start - w.jd_voc_start) < 1e-5, (
            f"RULE-06: no-aspect VOC start is unstable at jd_voc_start+0.001\n"
            f"  original={w.jd_voc_start:.6f}, probed={window_probe.jd_voc_start:.6f}"
        )
        assert window_probe.last_aspect is None, (
            "RULE-06: probing inside a no-aspect window returned last_aspect != None"
        )
        # The window must span a non-zero duration (sign transit has positive length)
        assert w.duration_hours > 0.0, "RULE-06: no-aspect VOC window has zero duration"

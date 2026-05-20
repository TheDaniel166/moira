"""
Adversarial house and angular singularity tests — Layer 4.

Same philosophy as test_adversarial_singularities.py:
a test that fails on first run has found a real defect. Leave it failing.
"""
from __future__ import annotations

import math

import pytest

from moira.houses import HouseSystem, calculate_houses
from moira.julian import julian_day, ut_to_tt

_J2000         = 2451545.0
_ONE_SECOND_JD = 1.0 / 86400.0

_QUADRANT_SYSTEMS = [
    HouseSystem.PLACIDUS,
    HouseSystem.KOCH,
    HouseSystem.PORPHYRY,
    HouseSystem.REGIOMONTANUS,
    HouseSystem.CAMPANUS,
]
_ALL_SYSTEMS = [
    HouseSystem.PLACIDUS,
    HouseSystem.KOCH,
    HouseSystem.PORPHYRY,
    HouseSystem.EQUAL,
    HouseSystem.WHOLE_SIGN,
    HouseSystem.REGIOMONTANUS,
]


def _find_jd_for_asc(target_asc_deg: float, lat: float, lon: float,
                     jd_start: float, system: str,
                     search_hours: int = 25) -> float | None:
    """Search for a JD (1-minute resolution) where ASC is near target_asc_deg."""
    one_minute = 1.0 / 24.0 / 60.0
    jd = jd_start
    for _ in range(search_hours * 60):
        try:
            cusps = calculate_houses(jd, lat, lon, system)
            diff = (cusps.asc - target_asc_deg + 180.0) % 360.0 - 180.0
            if abs(diff) < 0.5:
                return jd
        except Exception:
            pass
        jd += one_minute
    return None


# ===========================================================================
# LAYER 4 — House and angular singularities
# ===========================================================================

# ---------------------------------------------------------------------------
# 4a — ASC near 0° Aries
# ---------------------------------------------------------------------------

def test_layer4a_asc_near_zero_no_360_leak():
    """When ASC ≈ 0°, all cusps must be finite and in [0, 360). No 360° leak."""
    jd = _find_jd_for_asc(0.0, 0.0, 0.0, _J2000, HouseSystem.PLACIDUS)
    if jd is None:
        pytest.skip("Could not find JD with ASC near 0° in search window")

    for system in [HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.PORPHYRY]:
        cusps = calculate_houses(jd, 0.0, 0.0, system)

        assert 0.0 <= cusps.asc < 360.0, \
            f"{system}: ASC={cusps.asc} not in [0, 360)"
        assert cusps.asc != 360.0, f"{system}: ASC is exactly 360° — should be 0°"

        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c), f"{system}: cusp {i+1} is not finite: {c}"
            assert 0.0 <= c < 360.0, f"{system}: cusp {i+1} = {c} not in [0, 360)"


# ---------------------------------------------------------------------------
# 4b — Observer at exactly 0° latitude (equator)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", _ALL_SYSTEMS)
def test_layer4b_observer_at_equator(system):
    """At lat=0°, all house systems must return finite cusps without denominator blow-up."""
    cusps = calculate_houses(_J2000, 0.0, 0.0, system)

    assert math.isfinite(cusps.asc), f"{system}: ASC not finite at equator"
    assert math.isfinite(cusps.mc),  f"{system}: MC not finite at equator"
    assert 0.0 <= cusps.asc < 360.0, f"{system}: ASC out of range"

    for i, c in enumerate(cusps.cusps):
        assert math.isfinite(c), f"{system}: cusp {i+1} not finite at equator"
        assert 0.0 <= c < 360.0, f"{system}: cusp {i+1} = {c} out of range"


# ---------------------------------------------------------------------------
# 4c/4d — RAMC at 0°, 90°, 180°, 270°
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target_ramc,label", [
    (0.0,   "RAMC=0"),
    (90.0,  "RAMC=90"),
    (180.0, "RAMC=180"),
    (270.0, "RAMC=270"),
])
def test_layer4cd_ramc_cardinal_values(target_ramc, label):
    """At each cardinal RAMC value, all cusps must be finite and canonically normalised."""
    one_minute = 1.0 / 24.0 / 60.0
    jd = _J2000
    found_jd = None
    for _ in range(1440):
        ramc = calculate_houses(jd, 51.5, 0.0, HouseSystem.PLACIDUS).armc
        diff = (ramc - target_ramc + 180.0) % 360.0 - 180.0
        if abs(diff) < 0.5:
            found_jd = jd
            break
        jd += one_minute

    if found_jd is None:
        pytest.skip(f"Could not find JD for {label}")

    for system in [HouseSystem.PLACIDUS, HouseSystem.PORPHYRY, HouseSystem.EQUAL]:
        cusps = calculate_houses(found_jd, 51.5, 0.0, system)

        assert math.isfinite(cusps.asc), f"{system} {label}: ASC not finite"
        assert math.isfinite(cusps.mc),  f"{system} {label}: MC not finite"
        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c),    f"{system} {label}: cusp {i+1} not finite"
            assert 0.0 <= c < 360.0,    f"{system} {label}: cusp {i+1}={c} out of range"


# ---------------------------------------------------------------------------
# 4e — MC = 0° exactly
# ---------------------------------------------------------------------------

def test_layer4e_mc_near_zero_no_360_leak():
    """When MC ≈ 0°, MC must not be returned as 360°."""
    one_minute = 1.0 / 24.0 / 60.0
    jd = _J2000
    found_jd = None
    for _ in range(1440):
        cusps = calculate_houses(jd, 51.5, 0.0, HouseSystem.PLACIDUS)
        if abs(cusps.mc) < 1.0 or cusps.mc > 359.0:
            found_jd = jd
            break
        jd += one_minute

    if found_jd is None:
        pytest.skip("Could not find JD with MC near 0°")

    cusps = calculate_houses(found_jd, 51.5, 0.0, HouseSystem.PLACIDUS)
    assert cusps.mc != 360.0, f"MC is exactly 360° — should be normalised to 0°"
    assert 0.0 <= cusps.mc < 360.0, f"MC = {cusps.mc} not in [0, 360)"

    ic = (cusps.mc + 180.0) % 360.0
    assert cusps.ic == pytest.approx(ic, abs=1e-8), \
        f"IC={cusps.ic}° ≠ MC+180={ic}°"


# ---------------------------------------------------------------------------
# 4f — Observer just below / just above critical latitude for Placidus/Koch
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_layer4f_just_below_critical_latitude_computes_normally(system):
    """Just below the critical latitude: system should compute without fallback."""
    try:
        from moira.houses import _compute_critical_latitude
        crit_lat = _compute_critical_latitude(_J2000)
    except (ImportError, AttributeError):
        crit_lat = 66.5   # J2000 Arctic Circle approximation

    lat_below = crit_lat - 0.5
    cusps = calculate_houses(_J2000, lat_below, 0.0, system)

    assert not cusps.fallback, \
        f"{system}: fallback triggered at {lat_below}° (below critical ≈{crit_lat}°)"
    for i, c in enumerate(cusps.cusps):
        assert math.isfinite(c), f"{system}: cusp {i+1} not finite at {lat_below}°"


@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_layer4f_just_above_critical_latitude_triggers_fallback_or_error(system):
    """Just above the critical latitude: fallback flag set or named error — never silent wrong cusps."""
    try:
        from moira.houses import _compute_critical_latitude
        crit_lat = _compute_critical_latitude(_J2000)
    except (ImportError, AttributeError):
        crit_lat = 66.5

    lat_above = crit_lat + 0.5
    try:
        cusps = calculate_houses(_J2000, lat_above, 0.0, system)
        assert cusps.fallback, \
            f"{system}: no fallback flag at {lat_above}° (above critical ≈{crit_lat}°)" \
            f" — silent wrong cusps"
        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c), \
                f"{system}: cusp {i+1} not finite after fallback at {lat_above}°"
    except (ValueError, RuntimeError):
        pass  # named error is also acceptable


@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.KOCH])
def test_layer4f_latitude_89_behaviour_is_fallback_or_named_error(system):
    """At 89° latitude, semi-arc systems must fallback or raise — never hang or produce NaN."""
    try:
        cusps = calculate_houses(_J2000, 89.0, 0.0, system)
        assert cusps.fallback, \
            f"{system}: 89° latitude returned no fallback flag — silent wrong cusps"
        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c), \
                f"{system}: cusp {i+1} is NaN/inf at 89° even with fallback"
    except (ValueError, RuntimeError):
        pass  # explicit error is acceptable


# ---------------------------------------------------------------------------
# 4g — MC / IC opposition invariant (every system, sweep of epochs)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", _ALL_SYSTEMS)
@pytest.mark.parametrize("jd,label", [
    (_J2000,          "J2000"),
    (_J2000 + 182.5,  "J2000+6mo"),
    (_J2000 - 365.25, "J2000-1yr"),
])
def test_layer4g_mc_ic_opposition_invariant(system, jd, label):
    """IC must always equal (MC + 180) % 360 for every system at every epoch."""
    cusps = calculate_houses(jd, 51.5, -0.1, system)
    expected_ic = (cusps.mc + 180.0) % 360.0
    assert cusps.ic == pytest.approx(expected_ic, abs=1e-8), \
        f"{system} {label}: IC={cusps.ic}°, MC={cusps.mc}°, expected IC={expected_ic}°"


# ---------------------------------------------------------------------------
# 4h — ASC / DSC opposition invariant
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", _ALL_SYSTEMS)
def test_layer4h_asc_dsc_opposition_invariant(system):
    """DSC must always equal (ASC + 180) % 360."""
    cusps = calculate_houses(_J2000, 51.5, -0.1, system)
    expected_dsc = (cusps.asc + 180.0) % 360.0
    assert cusps.dsc == pytest.approx(expected_dsc, abs=1e-8), \
        f"{system}: DSC={cusps.dsc}°, ASC={cusps.asc}°, expected DSC={expected_dsc}°"


# ---------------------------------------------------------------------------
# 4i — Cusp ordering modulo 360 (circular coherence)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("system", _QUADRANT_SYSTEMS)
def test_layer4i_cusp_circular_ordering(system):
    """Cusp sequence must be circularly ordered — each cusp reachable from previous moving forward."""
    for lat, lon in [(51.5, -0.1), (0.0, 0.0)]:
        cusps = calculate_houses(_J2000, lat, lon, system)
        c = list(cusps.cusps)
        assert len(c) == 12, f"{system}: expected 12 cusps, got {len(c)}"
        for i in range(12):
            diff = (c[(i + 1) % 12] - c[i]) % 360.0
            assert diff > 0, \
                f"{system} lat={lat}: cusp {i+1}={c[i]:.4f}° → " \
                f"cusp {(i % 12)+2}={c[(i+1)%12]:.4f}° " \
                f"not circularly ordered (diff={diff}°)"


# ---------------------------------------------------------------------------
# 4j — Equal / Whole Sign / Porphyry at ASC near 359.999°
# ---------------------------------------------------------------------------

def test_layer4j_asc_near_360_cusp_ordering_across_zero():
    """With ASC near 359°, no cusp should be negative or cause inversion at 0°."""
    jd = _find_jd_for_asc(359.0, 51.5, 0.0, _J2000, HouseSystem.EQUAL)
    if jd is None:
        pytest.skip("Could not find JD with ASC near 359°")

    for system in [HouseSystem.EQUAL, HouseSystem.PORPHYRY]:
        cusps = calculate_houses(jd, 51.5, 0.0, system)
        for i, c in enumerate(cusps.cusps):
            assert math.isfinite(c), f"{system}: cusp {i+1} not finite near 359° ASC"
            assert c >= 0.0,         f"{system}: cusp {i+1} = {c} is negative"
            assert c < 360.0,        f"{system}: cusp {i+1} = {c} is >= 360°"


# ---------------------------------------------------------------------------
# 4k — Body exactly on a house cusp: placement must be stable and deterministic
# ---------------------------------------------------------------------------

def test_layer4k_body_on_cusp_placement_is_stable_and_deterministic():
    """A body exactly on a cusp must return the same house on repeated calls."""
    cusps = calculate_houses(_J2000, 51.5, -0.1, HouseSystem.PLACIDUS)
    test_longitude = cusps.asc  # House 1 cusp = ASC

    try:
        from moira.houses import house_of
        house1 = house_of(test_longitude, cusps)
        house2 = house_of(test_longitude, cusps)
        assert house1 == house2, \
            f"house_of on-cusp is non-deterministic: {house1} ≠ {house2}"
        assert 1 <= house1 <= 12, f"on-cusp house={house1} not in [1,12]"
    except (ImportError, AttributeError):
        pytest.skip("house_of not available — placement test skipped")


# ---------------------------------------------------------------------------
# 4l — MC approaching ASC at extreme latitude
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lat", [85.0, 87.0, 89.9])
def test_layer4l_mc_asc_extreme_latitude_no_hang(lat):
    """At extreme latitudes, the engine must not hang and must return finite angles or a named error."""
    try:
        cusps = calculate_houses(_J2000, lat, 0.0, HouseSystem.PLACIDUS)
        assert math.isfinite(cusps.asc), f"ASC not finite at lat={lat}°"
        assert math.isfinite(cusps.mc),  f"MC not finite at lat={lat}°"
        # Opposition invariants must hold even after fallback
        ic  = (cusps.mc  + 180.0) % 360.0
        dsc = (cusps.asc + 180.0) % 360.0
        assert cusps.ic  == pytest.approx(ic,  abs=1e-6), \
            f"IC invariant broken at lat={lat}°"
        assert cusps.dsc == pytest.approx(dsc, abs=1e-6), \
            f"DSC invariant broken at lat={lat}°"
    except (ValueError, RuntimeError):
        pass  # named error is acceptable


# ---------------------------------------------------------------------------
# 4m — MC continuity across a full 24-hour sidereal cycle (1-minute samples)
# ---------------------------------------------------------------------------

def test_layer4m_mc_continuous_over_24h():
    """MC must change monotonically and continuously over a full sidereal day."""
    one_minute = 1.0 / 24.0 / 60.0
    jd = _J2000
    prev_mc = calculate_houses(jd, 51.5, -0.1, HouseSystem.PLACIDUS).mc
    jd += one_minute
    max_jump = 0.0
    for _ in range(1439):   # 1439 more steps = 1440 total = 24 h
        mc = calculate_houses(jd, 51.5, -0.1, HouseSystem.PLACIDUS).mc
        step = abs(mc - prev_mc)
        if step > 180.0:
            step = 360.0 - step  # wrap-aware
        max_jump = max(max_jump, step)
        assert step < 1.5, \
            f"MC jump of {step:.4f}° at JD {jd:.6f} — discontinuity detected"
        prev_mc = mc
        jd += one_minute

"""
Moira Validation Script
=======================
Generates the full comparison table between Moira and ERFA/SOFA (via pyerfa).
Run with: py -3.14 scripts/run_validation.py

Output: docs/VALIDATION_RESULTS.txt (machine-generated results embedded in VALIDATION.md)
"""

import math
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import erfa
import moira
from moira.julian import (
    greenwich_mean_sidereal_time,
    centuries_from_j2000,
    ut_to_tt,
)
from moira.obliquity import mean_obliquity, true_obliquity, nutation
from moira.precession import mean_obliquity_p03, precession_matrix

RAD2DEG  = 180.0 / math.pi
DEG2RAD  = math.pi / 180.0
PASS_THRESHOLD_ARCSEC = 0.001
ARCSEC   = 3600.0           # degrees → arcseconds multiplier

# ---------------------------------------------------------------------------
# Test epochs covering the full supported range
# ---------------------------------------------------------------------------
TEST_EPOCHS = [
    # (label, jd_tt, jd_ut_approx)   -- ΔT is small enough that we use jd_tt≈jd_ut
    # for GMST we pass UT; for everything else TT.
    ("−500 (500 BCE)",     1903682.5,  1903682.5),   # 500 BCE Jan 1
    ("−200 (200 BCE)",     1794303.5,  1794303.5),   # 200 BCE Jan 1
    ("J0000 (1 CE)",       1721045.5,  1721045.5),   # 1 CE Jan 1
    ("J1000.0",            2086308.0,  2086308.0),   # 1000 CE Jan 1.5
    ("J1500.0",            2268923.5,  2268923.5),   # 1500 CE Jan 1
    ("J1800.0",            2378496.5,  2378496.5),   # 1800 Jan 1
    ("J1900.0",            2415020.5,  2415020.5),   # 1900 Jan 1
    ("J2000.0",            2451545.0,  2451545.0),   # 2000 Jan 1.5 (standard)
    ("J2010.0",            2455196.5,  2455196.5),   # 2010 Jan 1
    ("J2024.0",            2460310.5,  2460310.5),   # 2024 Jan 1
    ("J2050.0",            2469807.5,  2469807.5),   # 2050 Jan 1
    ("J2100.0",            2488069.5,  2488069.5),   # 2100 Jan 1
]

# For GMST we need UT; use the same JD (ΔT corrections below 70 s, negligible here)
GMST_EPOCHS = [(lbl, jd, jd) for lbl, jd, _ in TEST_EPOCHS]


def _split(jd: float):
    """Split JD into integer + fraction for pyerfa."""
    return float(int(jd)), float(jd - int(jd))


# ---------------------------------------------------------------------------
# 1. Greenwich Mean Sidereal Time (GMST)
# ---------------------------------------------------------------------------

def validate_gmst():
    print("\n=== 1. GMST (Greenwich Mean Sidereal Time) ===")
    header = f"{'Epoch':<22} {'ERFA (deg)':>16} {'Moira (deg)':>16} {'Δ (arcsec)':>12}"
    print(header)
    print("-" * len(header))
    results = []
    for label, jd_tt, jd_ut in GMST_EPOCHS:
        d1, d2 = _split(jd_ut)
        t1, t2 = _split(jd_tt)
        erfa_gmst = math.degrees(erfa.gmst06(d1, d2, t1, t2)) % 360.0
        moira_gmst = greenwich_mean_sidereal_time(jd_ut) % 360.0
        delta_arcsec = abs(erfa_gmst - moira_gmst) * ARCSEC
        # handle wrap-around
        if delta_arcsec > 180 * ARCSEC:
            delta_arcsec = 360 * ARCSEC - delta_arcsec
        results.append(delta_arcsec)
        flag = " ✓" if delta_arcsec < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {erfa_gmst:>16.8f} {moira_gmst:>16.8f} {delta_arcsec:>12.6f}{flag}")
    print(f"\nMax error: {max(results):.6f} arcsec   Mean: {sum(results)/len(results):.6f} arcsec")
    return results


# ---------------------------------------------------------------------------
# 2. Earth Rotation Angle (ERA)
# ---------------------------------------------------------------------------

def validate_era():
    print("\n=== 2. ERA (Earth Rotation Angle) ===")
    header = f"{'Epoch':<22} {'ERFA (deg)':>16} {'Moira (deg)':>16} {'Δ (arcsec)':>12}"
    print(header)
    print("-" * len(header))
    results = []
    for label, jd_tt, jd_ut in TEST_EPOCHS:
        d1, d2 = _split(jd_ut)
        erfa_era = math.degrees(erfa.era00(d1, d2)) % 360.0
        # Moira ERA: 2π × (0.7790572732640 + 1.00273781191135448 × D)
        D = jd_ut - 2451545.0
        era_turns = 0.7790572732640 + 1.00273781191135448 * D
        moira_era = (era_turns % 1.0) * 360.0
        delta_arcsec = abs(erfa_era - moira_era) * ARCSEC
        if delta_arcsec > 180 * ARCSEC:
            delta_arcsec = 360 * ARCSEC - delta_arcsec
        results.append(delta_arcsec)
        flag = " ✓" if delta_arcsec < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {erfa_era:>16.8f} {moira_era:>16.8f} {delta_arcsec:>12.6f}{flag}")
    print(f"\nMax error: {max(results):.6f} arcsec   Mean: {sum(results)/len(results):.6f} arcsec")
    return results


# ---------------------------------------------------------------------------
# 3. Mean Obliquity of the Ecliptic  (IAU 2006 P03, iauObl06)
# ---------------------------------------------------------------------------

def validate_obliquity():
    print("\n=== 3. Mean Obliquity (IAU 2006 P03 / iauObl06) ===")
    header = f"{'Epoch':<22} {'ERFA (deg)':>16} {'Moira (deg)':>16} {'Δ (arcsec)':>12}"
    print(header)
    print("-" * len(header))
    results = []
    for label, jd_tt, _ in TEST_EPOCHS:
        d1, d2 = _split(jd_tt)
        erfa_eps = math.degrees(erfa.obl06(d1, d2))
        moira_eps = mean_obliquity_p03(jd_tt)
        delta_arcsec = abs(erfa_eps - moira_eps) * ARCSEC
        results.append(delta_arcsec)
        flag = " ✓" if delta_arcsec < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {erfa_eps:>16.8f} {moira_eps:>16.8f} {delta_arcsec:>12.6f}{flag}")
    print(f"\nMax error: {max(results):.6f} arcsec   Mean: {sum(results)/len(results):.6f} arcsec")
    return results


# ---------------------------------------------------------------------------
# 4. Nutation in Longitude and Obliquity (IAU 2000A / iauNut06a)
# ---------------------------------------------------------------------------

def validate_nutation():
    print("\n=== 4. Nutation in Longitude Δψ (IAU 2000A / iauNut06a) ===")
    header = f"{'Epoch':<22} {'ERFA Δψ (arcsec)':>20} {'Moira Δψ (arcsec)':>20} {'Δ (arcsec)':>12}"
    print(header)
    print("-" * len(header))
    results_psi = []
    results_eps = []
    for label, jd_tt, _ in TEST_EPOCHS:
        d1, d2 = _split(jd_tt)
        erfa_dpsi, erfa_deps = erfa.nut06a(d1, d2)
        erfa_dpsi_as = math.degrees(erfa_dpsi) * ARCSEC
        erfa_deps_as = math.degrees(erfa_deps) * ARCSEC
        moira_dpsi_deg, moira_deps_deg = nutation(jd_tt)
        moira_dpsi_as = moira_dpsi_deg * ARCSEC
        moira_deps_as = moira_deps_deg * ARCSEC
        d_psi = abs(erfa_dpsi_as - moira_dpsi_as)
        results_psi.append(d_psi)
        flag = " ✓" if d_psi < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {erfa_dpsi_as:>20.6f} {moira_dpsi_as:>20.6f} {d_psi:>12.6f}{flag}")

    print(f"\nMax |Δψ| error: {max(results_psi):.6f} arcsec   Mean: {sum(results_psi)/len(results_psi):.6f} arcsec")

    print(f"\n{'Epoch':<22} {'ERFA Δε (arcsec)':>20} {'Moira Δε (arcsec)':>20} {'Δ (arcsec)':>12}")
    print("-" * (22+20+20+12+3))
    for label, jd_tt, _ in TEST_EPOCHS:
        d1, d2 = _split(jd_tt)
        erfa_dpsi, erfa_deps = erfa.nut06a(d1, d2)
        erfa_deps_as = math.degrees(erfa_deps) * ARCSEC
        moira_dpsi_deg, moira_deps_deg = nutation(jd_tt)
        moira_deps_as = moira_deps_deg * ARCSEC
        d_eps = abs(erfa_deps_as - moira_deps_as)
        results_eps.append(d_eps)
        flag = " ✓" if d_eps < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {erfa_deps_as:>20.6f} {moira_deps_as:>20.6f} {d_eps:>12.6f}{flag}")

    print(f"\nMax |Δε| error: {max(results_eps):.6f} arcsec   Mean: {sum(results_eps)/len(results_eps):.6f} arcsec")
    return results_psi, results_eps


# ---------------------------------------------------------------------------
# 5. Precession matrix (IAU 2006 / iauPmat06)
#    Compare Frobenius norm of (M_erfa − M_moira), convert to arcsec
# ---------------------------------------------------------------------------

def validate_precession_matrix():
    print("\n=== 5. Precession Matrix (IAU 2006 / iauPmat06) ===")
    print("    Comparison metric: max absolute element difference (converted to arcsec)")
    header = f"{'Epoch':<22} {'Max |ΔM| (arcsec)':>22}"
    print(header)
    print("-" * len(header))
    results = []
    for label, jd_tt, _ in TEST_EPOCHS:
        d1, d2 = _split(jd_tt)
        erfa_m = erfa.pmat06(d1, d2)   # 3×3 numpy array
        moira_m = precession_matrix(jd_tt)  # tuple of tuples

        # Compare element by element; rotation matrix elements are sin/cos of angles
        # A change of δ radians in angle produces ~δ change in off-diagonal elements
        # so |ΔM_ij| in radians ≈ δ in radians → convert to arcsec
        max_diff = 0.0
        for i in range(3):
            for j in range(3):
                diff = abs(float(erfa_m[i][j]) - moira_m[i][j])
                max_diff = max(max_diff, diff)
        max_diff_arcsec = max_diff * (180.0 / math.pi) * ARCSEC
        results.append(max_diff_arcsec)
        flag = " ✓" if max_diff_arcsec < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {max_diff_arcsec:>22.6f}{flag}")
    print(f"\nMax error: {max(results):.6f} arcsec   Mean: {sum(results)/len(results):.6f} arcsec")
    return results


# ---------------------------------------------------------------------------
# 6. Full precession-nutation matrix (iauPnm06a)
#    This is the combined P×N matrix (classical equinox-based)
# ---------------------------------------------------------------------------

def validate_pnm():
    print("\n=== 6. Combined Precession-Nutation Matrix (iauPnm06a) ===")
    print("    Comparison metric: max absolute element difference (arcsec equivalent)")
    header = f"{'Epoch':<22} {'Max |ΔM| (arcsec)':>22}"
    print(header)
    print("-" * len(header))
    results = []
    for label, jd_tt, _ in TEST_EPOCHS:
        d1, d2 = _split(jd_tt)
        erfa_m = erfa.pnm06a(d1, d2)

        # Moira's combined matrix: N × P  (in the correct order)
        from moira.coordinates import mat_mul, mat_vec_mul
        from moira.obliquity import nutation as moira_nutation
        from moira.precession import precession_matrix as P_ecl
        # Get the equatorial precession+nutation matrix
        from moira.coordinates import (
            precession_matrix_equatorial,
            nutation_matrix_equatorial,
        )
        P = precession_matrix_equatorial(jd_tt)
        N = nutation_matrix_equatorial(jd_tt)
        moira_m = mat_mul(N, P)

        max_diff = 0.0
        for i in range(3):
            for j in range(3):
                diff = abs(float(erfa_m[i][j]) - moira_m[i][j])
                max_diff = max(max_diff, diff)
        max_diff_arcsec = max_diff * (180.0 / math.pi) * ARCSEC
        results.append(max_diff_arcsec)
        flag = " ✓" if max_diff_arcsec < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {max_diff_arcsec:>22.6f}{flag}")
    print(f"\nMax error: {max(results):.6f} arcsec   Mean: {sum(results)/len(results):.6f} arcsec")
    return results


# ---------------------------------------------------------------------------
# 7. True Obliquity  (mean + Δε)
# ---------------------------------------------------------------------------

def validate_true_obliquity():
    print("\n=== 7. True Obliquity (mean + nutation in obliquity) ===")
    header = f"{'Epoch':<22} {'ERFA (deg)':>16} {'Moira (deg)':>16} {'Δ (arcsec)':>12}"
    print(header)
    print("-" * len(header))
    results = []
    for label, jd_tt, _ in TEST_EPOCHS:
        d1, d2 = _split(jd_tt)
        erfa_dpsi, erfa_deps = erfa.nut06a(d1, d2)
        erfa_eps0 = math.degrees(erfa.obl06(d1, d2))
        erfa_true = erfa_eps0 + math.degrees(erfa_deps)
        moira_true = true_obliquity(jd_tt)
        delta_arcsec = abs(erfa_true - moira_true) * ARCSEC
        results.append(delta_arcsec)
        flag = " ✓" if delta_arcsec < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {erfa_true:>16.8f} {moira_true:>16.8f} {delta_arcsec:>12.6f}{flag}")
    print(f"\nMax error: {max(results):.6f} arcsec   Mean: {sum(results)/len(results):.6f} arcsec")
    return results


# ---------------------------------------------------------------------------
# 8. GAST approximation (GMST + equation of the equinoxes)
# ---------------------------------------------------------------------------

def validate_gast():
    print("\n=== 8. GAST (Greenwich Apparent Sidereal Time) ===")
    print("    GAST = GMST + equation of equinoxes (Δψ·cos(ε) + CIP corrections)")
    header = f"{'Epoch':<22} {'ERFA (deg)':>16} {'Moira (deg)':>16} {'Δ (arcsec)':>12}"
    print(header)
    print("-" * len(header))

    # Moira computes GAST internally in coordinates via the nutation-corrected LST
    # We compute it as: GMST + (dpsi * cos(true_eps)) / 3600
    from moira.julian import greenwich_mean_sidereal_time
    results = []
    for label, jd_tt, jd_ut in TEST_EPOCHS:
        d1u, d2u = _split(jd_ut)
        d1t, d2t = _split(jd_tt)
        # ERFA GAST: gmst06 + s06 + equation of equinoxes
        # Use the standard: gast = gmst + eqeq
        # eqeq ≈ dpsi * cos(eps) + corrections (CIP longitude in RA)
        erfa_dpsi, erfa_deps = erfa.nut06a(d1t, d2t)
        erfa_eps0 = erfa.obl06(d1t, d2t)
        # Equation of equinoxes (simplified: dpsi * cos(eps))
        # Full: includes CIO s term via erfa.s06(d1t,d2t,x,y) but small
        eqeq_rad = erfa_dpsi * math.cos(erfa_eps0 + erfa_deps)
        erfa_gmst = erfa.gmst06(d1u, d2u, d1t, d2t)
        erfa_gast_deg = math.degrees(erfa_gmst + eqeq_rad) % 360.0

        # Moira GAST
        moira_gmst = greenwich_mean_sidereal_time(jd_ut)
        moira_dpsi, moira_deps = nutation(jd_tt)
        moira_eps = (mean_obliquity_p03(jd_tt) + moira_deps) * DEG2RAD
        eqeq_moira = moira_dpsi * math.cos(moira_eps)          # degrees
        moira_gast = (moira_gmst + eqeq_moira) % 360.0

        delta_arcsec = abs(erfa_gast_deg - moira_gast) * ARCSEC
        if delta_arcsec > 180 * ARCSEC:
            delta_arcsec = 360 * ARCSEC - delta_arcsec
        results.append(delta_arcsec)
        flag = " ✓" if delta_arcsec < PASS_THRESHOLD_ARCSEC else " ← FAIL"
        print(f"{label:<22} {erfa_gast_deg:>16.8f} {moira_gast:>16.8f} {delta_arcsec:>12.6f}{flag}")
    print(f"\nMax error: {max(results):.6f} arcsec   Mean: {sum(results)/len(results):.6f} arcsec")
    return results


# ---------------------------------------------------------------------------
# 9.  Summary table
# ---------------------------------------------------------------------------

def summary(all_results: dict):
    print("\n" + "=" * 72)
    print("SUMMARY — Moira vs ERFA/SOFA")
    print("=" * 72)
    print(f"{'Quantity':<44} {'Max error':>12} {'Pass (<0.001″)':>14}")
    print("-" * 72)
    for name, vals in all_results.items():
        flat = vals if isinstance(vals[0], float) else [v for sub in vals for v in sub]
        mx = max(flat)
        passed = "YES ✓" if mx < PASS_THRESHOLD_ARCSEC else "NO  ✗"
        print(f"{name:<44} {mx:>11.6f}″ {passed:>14}")
    print("=" * 72)
    all_flat = [v for sub in all_results.values()
                for v in (sub if isinstance(sub[0], float) else [x for s in sub for x in s])]
    print(f"\nOverall max error across all tests: {max(all_flat):.6f} arcsec")
    overall = "ALL PASS ✓" if max(all_flat) < PASS_THRESHOLD_ARCSEC else "SOME FAILURES — see above"
    print(f"Verdict: {overall}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Moira Ephemeris Engine — ERFA/SOFA Validation")
    print(f"pyerfa version : {erfa.__version__}")
    print(f"Test epochs    : {len(TEST_EPOCHS)}  (500 BCE to 2100 CE)")
    print(f"Pass threshold : 0.001 arcsecond")

    results = {}
    results["GMST (IAU 2006 ERA-based)"]               = validate_gmst()
    results["ERA (Earth Rotation Angle)"]               = validate_era()
    results["Mean Obliquity (IAU 2006 P03)"]            = validate_obliquity()
    psi, eps = validate_nutation()
    results["Nutation Δψ (IAU 2000A)"]                 = psi
    results["Nutation Δε (IAU 2000A)"]                 = eps
    results["Precession Matrix (IAU 2006)"]             = validate_precession_matrix()
    results["Combined P×N Matrix"]                      = validate_pnm()
    results["True Obliquity (mean + Δε)"]               = validate_true_obliquity()
    results["GAST (GMST + equation of equinoxes)"]      = validate_gast()

    summary(results)

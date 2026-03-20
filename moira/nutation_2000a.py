"""
Moira — nutation_2000a.py
The Nutation Engine: governs computation of nutation in longitude (Δψ) and
obliquity (Δε) using the full IAU 2000A model with IAU 2006 adjustments.

Boundary: owns the complete nutation pipeline from IERS table parsing through
fundamental argument evaluation to final Δψ/Δε output in degrees. Delegates
time conversion (Julian centuries from J2000) to julian. Does not own
precession, coordinate transforms, or any display formatting.

Public surface:
    nutation_2000a(jd_tt) -> tuple[float, float]

Import-time side effects:
    Parses and caches two IERS nutation table files at module import time:
      - moira/data/iau2000a_ls.txt  → cached into _LS_TERMS (1358 terms)
      - moira/data/iau2000a_pl.txt  → cached into _PL_TERMS (1056 terms)
    Both files are read once; subsequent calls to nutation_2000a() use the
    in-memory caches exclusively.

External dependency assumptions:
    - moira/data/iau2000a_ls.txt must exist and be readable at import time.
    - moira/data/iau2000a_pl.txt must exist and be readable at import time.
    - Both files must conform to the IERS Conventions 2010 Chapter 5 table
      format (whitespace-delimited rows, first column is a row index).
"""

import math
import os
from pathlib import Path

from .constants import ARCSEC2RAD
from .julian import centuries_from_j2000

# ---------------------------------------------------------------------------
# Paths to the IERS data files
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"
_LS_FILE  = _DATA_DIR / "iau2000a_ls.txt"   # Δψ
_PL_FILE  = _DATA_DIR / "iau2000a_pl.txt"   # Δε

# ---------------------------------------------------------------------------
# Parse IERS table files
# Each data row looks like:
#   i    coeff1    coeff2    n1 n2 n3 n4 n5  [n6..n14]
# We skip header/separator lines (not starting with a digit or leading space+digit).
# ---------------------------------------------------------------------------

def _parse_table(path: Path) -> list[tuple]:
    """
    Parse an IERS nutation table file.
    Returns list of tuples: (c1, c2, args...)
    where c1, c2 are floats (microarcsec) and args are ints (argument multipliers).
    """
    terms: list[tuple] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            # Data lines: leading whitespace then a digit (row index)
            stripped = line.lstrip()
            if not stripped or not stripped[0].isdigit():
                continue
            parts = stripped.split()
            if len(parts) < 4:
                continue
            try:
                # parts[0] = row index (int, discard)
                c1   = float(parts[1])
                c2   = float(parts[2])
                args = tuple(int(x) for x in parts[3:])
                terms.append((c1, c2) + args)
            except (ValueError, IndexError):
                continue
    return terms


# Load tables once at import time (fast — just reading text files)
_LS_TERMS: list[tuple] = _parse_table(_LS_FILE)   # Δψ: 1320 j=0 + 38 j=1
_PL_TERMS: list[tuple] = _parse_table(_PL_FILE)   # Δε: 1037 j=0 + 19 j=1

# j=1 (time-dependent) terms begin at index 1320 in ls and 1037 in pl
_LS_J0_COUNT = 1320
_PL_J0_COUNT = 1037


# ---------------------------------------------------------------------------
# Fundamental arguments — IAU 2000A / IERS 2003 formulas
# All results in radians.
# ---------------------------------------------------------------------------

def _fundamental_args(T: float) -> tuple[float, ...]:
    """
    Compute the 14 fundamental arguments of the nutation theory.

    Parameters
    ----------
    T : Julian centuries from J2000.0 (TT)

    Returns
    -------
    (l, l', F, D, Om, L_Me, L_Ve, L_E, L_Ma, L_J, L_Sa, L_Ur, L_Ne, p_A)
    First five in radians; planetary longitudes in radians (modulo 2π).
    """
    # --- Luni-solar (Delaunay arguments) — IERS 2003, Eq. (B.10)-(B.14)
    # Coefficients in arcseconds; convert to radians at end

    arcsec = math.pi / 648000.0   # 1 arcsecond in radians

    l  = (485868.249036
          + T * (1717915923.2178
          + T * (31.8792
          + T * (0.051635
          + T * (-0.00024470))))) * arcsec

    lp = (1287104.793048
          + T * (129596581.0481
          + T * (-0.5532
          + T * (0.000136
          + T * (-0.00001149))))) * arcsec

    F  = (335779.526232
          + T * (1739527262.8478
          + T * (-12.7512
          + T * (-0.001037
          + T * (0.00000417))))) * arcsec

    D  = (1072260.703692
          + T * (1602961601.2090
          + T * (-6.3706
          + T * (0.006593
          + T * (-0.00003169))))) * arcsec

    Om = (450160.398036
          + T * (-6962890.5431
          + T * (7.4722
          + T * (0.007702
          + T * (-0.00005939))))) * arcsec

    # --- Planetary (linear in T, radians) — IERS 2003, Eq. (B.21)-(B.29)
    tau = math.tau  # 2π

    L_Me = (4.402608842 + 2608.7903141574 * T) % tau
    L_Ve = (3.176146697 + 1021.3285546211 * T) % tau
    L_E  = (1.753470314 +  628.3075849991 * T) % tau
    L_Ma = (6.203480913 +  334.0612426700 * T) % tau
    L_J  = (0.599546497 +   52.9690962641 * T) % tau
    L_Sa = (0.874016757 +   21.3299104960 * T) % tau
    L_Ur = (5.481293872 +    7.4781598567 * T) % tau
    L_Ne = (5.311886287 +    3.8133035638 * T) % tau
    p_A  = (0.02438175  +    0.00000538691 * T) % tau

    return l, lp, F, D, Om, L_Me, L_Ve, L_E, L_Ma, L_J, L_Sa, L_Ur, L_Ne, p_A


def _argument(args: tuple[int, ...], fa: tuple[float, ...]) -> float:
    """Compute nutation argument = Σ n_i × fa_i (radians)."""
    return sum(n * a for n, a in zip(args, fa))


# ---------------------------------------------------------------------------
# Main nutation function
# ---------------------------------------------------------------------------

def nutation_2000a(jd_tt: float) -> tuple[float, float]:
    """
    Compute nutation in longitude (Δψ) and obliquity (Δε) using the full
    IAU 2000A model with IAU 2006 adjustments.

    Parameters
    ----------
    jd_tt : Julian Day in Terrestrial Time (TT)

    Returns
    -------
    (delta_psi, delta_eps) in degrees

    Notes
    -----
    Accuracy: ~0.1 µas for 1995–2050; degrades gracefully for historical dates.
    """
    T  = centuries_from_j2000(jd_tt)
    fa = _fundamental_args(T)

    # Unit conversion: microarcseconds → degrees
    uas2deg = 1e-6 / 3600.0

    # --- Δψ from Table 5.3a ---
    # j=0:  Σ [A_i · sin(arg) + A"_i · cos(arg)]
    # j=1:  T · Σ [A'_i · sin(arg) + A"'_i · cos(arg)]

    dpsi = 0.0
    for term in _LS_TERMS[:_LS_J0_COUNT]:
        A, Ap = term[0], term[1]        # A_i, A"_i
        arg   = _argument(term[2:], fa)
        dpsi += A * math.sin(arg) + Ap * math.cos(arg)

    for term in _LS_TERMS[_LS_J0_COUNT:]:
        Ap, App = term[0], term[1]      # A'_i, A"'_i
        arg     = _argument(term[2:], fa)
        dpsi   += T * (Ap * math.sin(arg) + App * math.cos(arg))

    # --- Δε from Table 5.3b (IERS Conventions 2010, Chapter 5) ---
    # Column order in iau2000a_pl.txt (j=0 terms):
    #   col 0: S_i  — coefficient of sin(arg)   [called Bpp here]
    #   col 1: C_i  — coefficient of cos(arg)   [called B here]
    # Formula: Δε = Σ C_i·cos(arg_i) + S_i·sin(arg_i)
    # Reference: IERS 2010 Table 5.3b, https://www.iers.org/IERS/EN/Publications/TechnicalNotes/tn36.html
    deps = 0.0
    for term in _PL_TERMS[:_PL_J0_COUNT]:
        Bpp, B = term[0], term[1]       # B"_i (sin), B_i (cos)
        arg    = _argument(term[2:], fa)
        deps  += B * math.cos(arg) + Bpp * math.sin(arg)

    for term in _PL_TERMS[_PL_J0_COUNT:]:
        Bpp, B = term[0], term[1]
        arg    = _argument(term[2:], fa)
        deps  += T * (B * math.cos(arg) + Bpp * math.sin(arg))

    return dpsi * uas2deg, deps * uas2deg

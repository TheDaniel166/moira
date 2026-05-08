"""
Moira — nutation_2000a.py
The Nutation Engine: governs computation of nutation in longitude (Δψ) and
obliquity (Δε) by evaluating the full IAU 2000A series.

Boundary: owns the complete nutation-series pipeline from IERS table parsing
through fundamental argument evaluation to final Δψ/Δε output in degrees.
Delegates time conversion (Julian centuries from J2000) to julian. Does not
own precession, coordinate transforms, or any display formatting.

Public surface:
    nutation_2000a(jd_tt) -> tuple[float, float]

Import-time side effects:
    No file I/O. The IERS nutation tables are loaded lazily on the first call
    to nutation_2000a():
      - moira/data/iau2000a_ls.txt  → cached into _LS_TERMS (1358 terms)
      - moira/data/iau2000a_pl.txt  → cached into _PL_TERMS (1056 terms)
    Both files are read once; subsequent calls use the in-memory caches
    exclusively.

External dependency assumptions:
    - moira/data/iau2000a_ls.txt must exist and be readable before first use.
    - moira/data/iau2000a_pl.txt must exist and be readable before first use.
    - Both files must conform to the IERS Conventions 2010 Chapter 5 table
      format (whitespace-delimited rows, first column is a row index).
"""

import math
import threading
from pathlib import Path

try:
    from . import moira_native as _moira_native
except ImportError:
    _moira_native = None

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


# Loaded lazily on first use to keep package import free of file I/O.
_LS_TERMS: list[tuple] | None = None   # Δψ: 1320 j=0 + 38 j=1
_PL_TERMS: list[tuple] | None = None   # Δε: 1037 j=0 + 19 j=1
_TABLES_LOCK = threading.Lock()
_NATIVE_TABLES_REGISTERED = False

# j=1 (time-dependent) terms begin at index 1320 in ls and 1037 in pl
_LS_J0_COUNT = 1320
_PL_J0_COUNT = 1037

# 1 arcsecond in radians — used by _fundamental_args
_ARCSEC = math.pi / 648000.0


def _ensure_tables_loaded() -> tuple[list[tuple], list[tuple]]:
    """Load and cache the nutation coefficient tables on first use."""
    global _LS_TERMS, _PL_TERMS, _NATIVE_TABLES_REGISTERED

    if _LS_TERMS is not None and _PL_TERMS is not None:
        if _moira_native is not None and not _NATIVE_TABLES_REGISTERED:
            _moira_native.set_nutation_2000a_tables(_LS_TERMS, _PL_TERMS, _LS_J0_COUNT, _PL_J0_COUNT)
            _NATIVE_TABLES_REGISTERED = True
        return _LS_TERMS, _PL_TERMS

    with _TABLES_LOCK:
        if _LS_TERMS is None:
            _LS_TERMS = _parse_table(_LS_FILE)
        if _PL_TERMS is None:
            _PL_TERMS = _parse_table(_PL_FILE)
        if _moira_native is not None and not _NATIVE_TABLES_REGISTERED:
            _moira_native.set_nutation_2000a_tables(_LS_TERMS, _PL_TERMS, _LS_J0_COUNT, _PL_J0_COUNT)
            _NATIVE_TABLES_REGISTERED = True
    return _LS_TERMS, _PL_TERMS


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

    l  = (485868.249036
          + T * (1717915923.2178
          + T * (31.8792
          + T * (0.051635
          + T * (-0.00024470))))) * _ARCSEC

    lp = (1287104.793048
          + T * (129596581.0481
          + T * (-0.5532
          + T * (0.000136
          + T * (-0.00001149))))) * _ARCSEC

    F  = (335779.526232
          + T * (1739527262.8478
          + T * (-12.7512
          + T * (-0.001037
          + T * (0.00000417))))) * _ARCSEC

    D  = (1072260.703692
          + T * (1602961601.2090
          + T * (-6.3706
          + T * (0.006593
          + T * (-0.00003169))))) * _ARCSEC

    Om = (450160.398036
          + T * (-6962890.5431
          + T * (7.4722
          + T * (0.007702
          + T * (-0.00005939))))) * _ARCSEC

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
# Pure Python inner computation (canonical / auditable path)
# ---------------------------------------------------------------------------

def _nutation_python(T: float, fa: tuple) -> tuple[float, float]:
    """
    Pure Python nutation computation over all IERS terms.

    This is the canonical implementation — fully auditable without any
    compiled dependencies. It is the governing path for Moira's nutation
    series evaluation.
    """
    ls_terms, pl_terms = _ensure_tables_loaded()
    uas2deg = 1e-6 / 3600.0

    # --- Δψ from Table 5.3a ---
    # j=0:  Σ [A_i · sin(arg) + A"_i · cos(arg)]
    # j=1:  T · Σ [A'_i · sin(arg) + A"'_i · cos(arg)]

    dpsi = 0.0
    for term in ls_terms[:_LS_J0_COUNT]:
        A, Ap = term[0], term[1]        # A_i, A"_i
        arg   = _argument(term[2:], fa)
        dpsi += A * math.sin(arg) + Ap * math.cos(arg)

    for term in ls_terms[_LS_J0_COUNT:]:
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
    for term in pl_terms[:_PL_J0_COUNT]:
        Bpp, B = term[0], term[1]       # B"_i (sin), B_i (cos)
        arg    = _argument(term[2:], fa)
        deps  += B * math.cos(arg) + Bpp * math.sin(arg)

    for term in pl_terms[_PL_J0_COUNT:]:
        Bpp, B = term[0], term[1]
        arg    = _argument(term[2:], fa)
        deps  += T * (B * math.cos(arg) + Bpp * math.sin(arg))

    return dpsi * uas2deg, deps * uas2deg


# ---------------------------------------------------------------------------
# Public function — canonical path only
# ---------------------------------------------------------------------------

def nutation_2000a(jd_tt: float) -> tuple[float, float]:
    """
    Compute nutation in longitude (Δψ) and obliquity (Δε) using the full
    IAU 2000A series.

    Parameters
    ----------
    jd_tt : Julian Day in Terrestrial Time (TT)

    Returns
    -------
    (delta_psi, delta_eps) in degrees

    Notes
    -----
    Standards context: this function evaluates the IAU 2000A nutation series.
    In Moira's validated stack it is paired with IAU 2006 precession and
    checked against ERFA/SOFA ``nut06a`` through the surrounding integration
    tests.

    Validated agreement: the current ERFA oracle suite verifies the enclosing
    nutation / precession stack to within 0.001 arcsecond over the tested grid
    from 500 BCE through 2100 CE.

    The scalar series evaluator is the governing implementation. It is kept
    fully visible and dependency-light per Moira's doctrine of inspectable
    astronomical derivation.
    """
    _ensure_tables_loaded()
    if _moira_native is not None and _NATIVE_TABLES_REGISTERED:
        return _moira_native.nutation_2000a(jd_tt)

    T = centuries_from_j2000(jd_tt)
    fa = _fundamental_args(T)
    return _nutation_python(T, fa)

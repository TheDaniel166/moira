"""
Moira — delta_t_physical.py
The Oracle of ΔT: governs physics-based hybrid Delta T computation by
decomposing ΔT into secular, core-mantle, cryosphere, and residual components.

Boundary: owns the full ΔT decomposition pipeline — secular parabola, core
angular momentum integration, GRACE/GRACE-FO cryosphere contribution, and
IERS residual spline fitting. Delegates IERS measured ΔT lookup to
moira.julian.delta_t (used only during residual spline construction). Does not
own time-scale conversion, calendar arithmetic, or any display formatting.

Public surface:
    secular_trend, fluid_lowfreq, core_delta_t, cryo_delta_t, delta_t_hybrid,
    delta_t_hybrid_uncertainty

Import-time side effects: None

External dependency assumptions:
    - scipy.interpolate.UnivariateSpline is required for the modern-era
      residual spline. The hybrid ΔT model must not silently degrade when
      this dependency is absent.
    - Data files under moira/data/ (delta_t_hpiers_2016.txt,
      grace_lod_contribution.txt, core_angular_momentum.txt) are loaded
      lazily on first call via @cache decorated loaders; missing files are
      handled gracefully (empty series / fallback values).
"""

import math
import statistics
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from .constants import JULIAN_YEAR
from .julian import julian_day

__all__ = [
    "TIDAL_COEFF",
    "GIA_COEFF",
    "REFERENCE_LOD",
    "REFERENCE_YEAR",
    "secular_trend",
    "fluid_lowfreq",
    "historical_core_delta_t",
    "core_delta_t",
    "cryo_delta_t",
    "delta_t_hybrid",
    "delta_t_hybrid_uncertainty",
    "DeltaTBreakdown",
    "delta_t_breakdown",
]


_DATA_DIR = Path(__file__).resolve().parent / "data"

TIDAL_COEFF: float = 31.0
GIA_COEFF: float = -3.0
REFERENCE_LOD: float = 69.11474233219883
REFERENCE_YEAR: float = 2026.0

_CORE_COVERAGE_START: float = 1840.0
_CORE_DECORRELATION_YEARS: float = 10.0
_RESIDUAL_FIT_START: float = 1962.5
_RESIDUAL_TAPER_START: float = 2021.5
_RESIDUAL_TAPER_END: float = 2024.5
_SEAM_TAPER_YEARS: float = 2.0
_FLUID_LAG_YEARS: float = 4.0
_FLUID_ADMISSION_SCALE: float = 1.0
_GIA_COEFF_SIGMA: float = 0.5
_CRYO_TREND_SIGMA: float = 0.002
_CORE_HISTORICAL_SIGMA: float = 0.3
_RESIDUAL_FUTURE_RMS_FALLBACK: float = 0.4


def _require_univariate_spline() -> type:
    """
    Return scipy's UnivariateSpline or raise a hard runtime error.

    The residual spline is not optional for Moira's asserted hybrid ΔT model.
    If scipy is missing, callers must see a clear failure instead of a silent
    fallback to an incomplete model.
    """
    try:
        from scipy.interpolate import UnivariateSpline
    except ImportError as exc:
        raise RuntimeError(
            "delta_t_hybrid requires scipy.interpolate.UnivariateSpline. "
            "Install Moira runtime dependencies to enable the residual spline."
        ) from exc
    return UnivariateSpline


@dataclass(frozen=True, slots=True)
class _ResidualSplineFit:
    """Internal vessel for the residual spline plus its diagnostics."""
    spline: object | None
    cv_rms: float
    in_sample_rms: float
    knot_count: int


@cache
def _modern_bridge_coefficients() -> tuple[float, float]:
    """
    Return the measured-era smooth bridge coefficients ``(c2, c3)``.

    The long-horizon tidal+GIA parabola provides the physical curvature, but
    by itself it leaves a large low-frequency drift across the 1962.5–2024.5
    annual-mean era. This helper calibrates a smooth bridge polynomial
    ``c2*t^2 + c3*t^3`` over that measured interval, constrained to vanish and
    have zero first derivative at REFERENCE_YEAR so the post-REFERENCE future
    secular path is unchanged and C1-continuous at the handoff.
    """
    from .julian import delta_t as _iers_delta_t

    s22 = 0.0
    s23 = 0.0
    s33 = 0.0
    b2 = 0.0
    b3 = 0.0
    y = _RESIDUAL_FIT_START
    while y <= _RESIDUAL_TAPER_END + 0.01:
        t = (y - REFERENCE_YEAR) / 100.0
        corrected = (
            _iers_delta_t(y)
            - REFERENCE_LOD
            - (TIDAL_COEFF + GIA_COEFF) * t * t
            - fluid_lowfreq(y)
            - core_delta_t(y)
            - cryo_delta_t(y)
        )
        t2 = t * t
        t3 = t2 * t
        s22 += t2 * t2
        s23 += t2 * t3
        s33 += t3 * t3
        b2 += t2 * corrected
        b3 += t3 * corrected
        y += 1.0
    det = s22 * s33 - s23 * s23
    if abs(det) < 1e-30:
        # Near-singular normal matrix — return zero coefficients rather than
        # producing a numerically garbage solution.
        return (0.0, 0.0)
    c2 = (b2 * s33 - b3 * s23) / det
    c3 = (s22 * b3 - s23 * b2) / det
    return (c2, c3)


@cache
def _left_seam_correction() -> float:
    """
    Initialization offset at the start of the measured era (1962.5).

    Returns the residual ``IERS(1962.5) − (secular + fluid + poly_bridge +
    core + cryo)`` at _RESIDUAL_FIT_START. Applied as a cosine-fade correction
    over _SEAM_TAPER_YEARS so the bridge exactly absorbs the first-epoch
    offset while decaying smoothly to zero by 1964.5.
    """
    from .julian import delta_t as _iers_delta_t

    y = _RESIDUAL_FIT_START
    t = (y - REFERENCE_YEAR) / 100.0
    c2, c3 = _modern_bridge_coefficients()
    poly_bridge = c2 * t * t + c3 * t * t * t
    model = (
        secular_trend(y)
        + fluid_lowfreq(y)
        + poly_bridge
        + core_delta_t(y)
        + cryo_delta_t(y)
    )
    return _iers_delta_t(y) - model


def _modern_bridge_delta_t(year: float) -> float:
    """
    Measured-era affine bridge term, zero outside the calibrated modern window.

    This narrows the residual spline's role to local structure by removing the
    dominant low-frequency drift between the physical curvature baseline and
    measured annual-mean Delta T. The bridge is constrained to be exactly zero
    at REFERENCE_YEAR and is not carried into the future regime.

    A cosine-fade seam correction over _SEAM_TAPER_YEARS absorbs the
    initialization offset at 1962.5 without disturbing the global polynomial
    calibration or the C1-continuity constraint at REFERENCE_YEAR.
    """
    if year < _RESIDUAL_FIT_START or year > REFERENCE_YEAR:
        return 0.0
    t = (year - REFERENCE_YEAR) / 100.0
    c2, c3 = _modern_bridge_coefficients()
    poly_val = c2 * t * t + c3 * t * t * t
    if year <= _RESIDUAL_FIT_START + _SEAM_TAPER_YEARS:
        phase = (year - _RESIDUAL_FIT_START) / _SEAM_TAPER_YEARS
        correction = _left_seam_correction() * math.cos(math.pi / 2.0 * phase) ** 2
        return poly_val + correction
    return poly_val


def _load_aam_glaam_annual() -> tuple[tuple[float, float], ...]:
    path = _DATA_DIR / "aam_glaam_annual.txt"
    if not path.exists():
        return ()
    rows: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            rows.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    rows.sort(key=lambda r: r[0])
    return tuple(rows)


def _load_oam_ecco_annual() -> tuple[tuple[float, float], ...]:
    path = _DATA_DIR / "oam_ecco_annual.txt"
    if not path.exists():
        return ()
    rows: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            rows.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    rows.sort(key=lambda r: r[0])
    return tuple(rows)


def _integrated_fluid_proxy(
    series: tuple[tuple[float, float], ...]
) -> tuple[tuple[float, float], ...]:
    if not series:
        return ()
    years = [y for y, _ in series]
    vals = [v for _, v in series]
    _, vals_smoothed = _three_year_smooth(years, vals)
    mean_val = sum(vals_smoothed) / len(vals_smoothed)
    result: list[tuple[float, float]] = [(years[0], 0.0)]
    cumulative = 0.0
    for i in range(1, len(series)):
        y0 = years[i - 1]
        y1 = years[i]
        v0 = vals_smoothed[i - 1] - mean_val
        v1 = vals_smoothed[i] - mean_val
        dt_days = _series_epoch_delta_days(y0, y1)
        cumulative += ((v0 + v1) / 2.0) * dt_days / 86400.0
        result.append((y1, cumulative))
    return tuple(result)


@cache
def _fit_fluid_lowfreq_coefficients() -> tuple[float, float]:
    """
    Fit a conservative low-frequency fluid term from annual AAM + OAM proxies.

    A single shared lag is imposed for both proxies. This avoids the
    physically suspicious opposite-lag solutions that minimized RMS in the
    diagnostic envelope search while still transferring a substantial portion
    of the measured-era low-frequency bridge into an explicit physical term.
    """
    aam = dict(_integrated_fluid_proxy(_load_aam_glaam_annual()))
    oam = dict(_integrated_fluid_proxy(_load_oam_ecco_annual()))
    if not aam or not oam:
        return (0.0, 0.0)
    from .julian import delta_t as _iers_delta_t

    rows: list[tuple[float, float, float]] = []
    for year in sorted(y for y in aam if y in oam and _RESIDUAL_FIT_START <= y <= 2002.5):
        shifted = year + _FLUID_LAG_YEARS
        if shifted not in aam or shifted not in oam:
            continue
        t = (year - REFERENCE_YEAR) / 100.0
        target = (
            _iers_delta_t(year)
            - REFERENCE_LOD
            - (TIDAL_COEFF + GIA_COEFF) * t * t
            - core_delta_t(year)
            - cryo_delta_t(year)
        )
        rows.append((aam[shifted], oam[shifted], target))
    if len(rows) < 10:
        return (0.0, 0.0)

    saa = sum(r[0] * r[0] for r in rows)
    sao = sum(r[0] * r[1] for r in rows)
    soo = sum(r[1] * r[1] for r in rows)
    sab = sum(r[0] * r[2] for r in rows)
    sob = sum(r[1] * r[2] for r in rows)
    det = saa * soo - sao * sao
    if det == 0.0:
        return (0.0, 0.0)
    alpha = (sab * soo - sob * sao) / det
    beta = (saa * sob - sao * sab) / det
    return (alpha, beta)


@cache
def _fluid_lowfreq_series() -> tuple[tuple[float, float], ...]:
    aam = dict(_integrated_fluid_proxy(_load_aam_glaam_annual()))
    oam = dict(_integrated_fluid_proxy(_load_oam_ecco_annual()))
    alpha, beta = _fit_fluid_lowfreq_coefficients()
    if alpha == 0.0 and beta == 0.0:
        return ()

    rows: list[tuple[float, float]] = []
    for year in sorted(y for y in aam if y in oam and _RESIDUAL_FIT_START <= y <= 2002.5):
        shifted = year + _FLUID_LAG_YEARS
        if shifted not in aam or shifted not in oam:
            continue
        rows.append((
            year,
            _FLUID_ADMISSION_SCALE * (alpha * aam[shifted] + beta * oam[shifted]),
        ))
    return tuple(rows)


def fluid_lowfreq(year: float) -> float:
    """
    Low-frequency fluid angular-momentum contribution to Delta T.

    This is a conservative live admission of the physical low-frequency layer:
    annual AAM + OAM proxies, a shared lag policy, and a smooth taper back to
    zero before the future regime. It does not attempt to replace the bridge
    entirely; it transfers the physically explainable portion into an explicit
    term and leaves the residual remainder to the bridge and spline.
    """
    series = _fluid_lowfreq_series()
    if not series:
        return 0.0
    if year < series[0][0] or year >= _RESIDUAL_TAPER_END:
        return 0.0
    if year >= series[-1][0]:
        return series[-1][1] * _support_fade_taper(
            year,
            start=series[-1][0],
            end=_RESIDUAL_TAPER_END,
        )
    for i in range(len(series) - 1):
        y0, v0 = series[i]
        y1, v1 = series[i + 1]
        if y0 <= year <= y1:
            frac = (year - y0) / (y1 - y0)
            return (v0 + frac * (v1 - v0)) * _cosine_taper(year)
    return 0.0


@cache
def _load_smh2016_table() -> tuple[tuple[float, float], ...]:
    path = _DATA_DIR / "delta_t_hpiers_2016.txt"
    rows: dict[float, float] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            year = float(parts[0])
            dt = float(parts[1])
        except ValueError:
            continue
        rows[year] = dt
    return tuple(sorted(rows.items()))


def _smh2016_lookup(year: float) -> float:
    """Interpolate the SMH 2016 ΔT table at the given decimal year."""
    table = _load_smh2016_table()
    if not table:
        t = (year - 1820.0) / 100.0
        return -20.0 + 32.0 * t * t
    if year <= table[0][0]:
        return table[0][1]
    if year >= table[-1][0]:
        return table[-1][1]
    for (y0, dt0), (y1, dt1) in zip(table, table[1:]):
        if y0 <= year <= y1:
            frac = (year - y0) / (y1 - y0)
            return dt0 + frac * (dt1 - dt0)
    return table[-1][1]


def secular_trend(year: float) -> float:
    """
    Physics-based secular Delta T trend from tidal braking + GIA.

    Both coefficients are re-expressed around REFERENCE_YEAR after expanding
    the original 1820/2000 reference epochs — the linear and constant terms
    are absorbed into REFERENCE_LOD via the continuity constraint.
    See DELTA_T_HYBRID_MODEL.md section 3, Phase 1 for the full derivation.

    Parameters
    ----------
    year : decimal year

    Returns
    -------
    ΔT in seconds
    """
    t = (year - REFERENCE_YEAR) / 100.0
    return REFERENCE_LOD + (TIDAL_COEFF + GIA_COEFF) * t * t


@cache
def _load_grace_series() -> tuple[tuple[float, float, int], ...]:
    """
    Load pre-processed GRACE/GRACE-FO LOD contribution series.

    File: moira/data/grace_lod_contribution.txt
    Format: decimal_year  cumulative_delta_t_seconds  gap_flag
            where gap_flag=1 means the month was interpolated across the
            2017-10 to 2018-06 GRACE/GRACE-FO gap.

    Generated by: scripts/fetch_grace_j2.py
    Returns empty tuple if the file does not yet exist.
    """
    path = _DATA_DIR / "grace_lod_contribution.txt"
    if not path.exists():
        return ()
    rows: list[tuple[float, float, int]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            yr = float(parts[0])
            val = float(parts[1])
            flag = int(parts[2]) if len(parts) >= 3 else 0
        except ValueError:
            continue
        rows.append((yr, val, flag))
    rows.sort(key=lambda r: r[0])
    return tuple(rows)


def cryo_delta_t(year: float) -> float:
    """
    Cryosphere/hydrosphere contribution to Delta T from the pre-integrated
    GRACE/GRACE-FO J2 series.

    Returns 0.0 if the data file does not yet exist or if year < GRACE start.
    For years beyond the last GRACE-FO measurement, extrapolates using the
    linear trend of the last 5 years of available data.

    Integration constant: cryo_delta_t(first_epoch) ≡ 0 by construction.
    See DELTA_T_HYBRID_MODEL.md section 3, Phase 2 for details.

    Parameters
    ----------
    year : decimal year

    Returns
    -------
    ΔT contribution in seconds
    """
    series = _load_grace_series()
    if not series:
        return 0.0
    if year <= series[0][0]:
        return 0.0
    if year <= series[-1][0]:
        for i in range(len(series) - 1):
            y0, v0, _ = series[i]
            y1, v1, _ = series[i + 1]
            if y0 <= year <= y1:
                frac = (year - y0) / (y1 - y0)
                return v0 + frac * (v1 - v0)
        return series[-1][1]
    window = [(r[0], r[1]) for r in series if r[0] >= series[-1][0] - 5.0]
    if len(window) < 2:
        return series[-1][1]
    n = len(window)
    mean_y = sum(y for y, _ in window) / n
    mean_v = sum(v for _, v in window) / n
    ss_xy = sum((window[i][0] - mean_y) * (window[i][1] - mean_v) for i in range(n))
    ss_xx = sum((window[i][0] - mean_y) ** 2 for i in range(n))
    if ss_xx == 0.0:
        return series[-1][1]
    slope = ss_xy / ss_xx
    intercept = mean_v - slope * mean_y
    return intercept + slope * year


@cache
def _load_core_series() -> tuple[tuple[float, float], ...]:
    """
    Load the Gillet et al. core angular momentum series.

    File: moira/data/core_angular_momentum.txt
    Format: decimal_year  delta_lod_ms
    Source: Gillet et al. (2019/2022) supplementary tables.
    Returns empty tuple if the file does not yet exist.
    """
    path = _DATA_DIR / "core_angular_momentum.txt"
    if not path.exists():
        return ()
    rows: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            yr = float(parts[0])
            lod_ms = float(parts[1])
        except ValueError:
            continue
        rows.append((yr, lod_ms))
    rows.sort(key=lambda r: r[0])
    return tuple(rows)


@cache
def _load_historical_core_series() -> tuple[tuple[float, float], ...]:
    """
    Load the Gillet et al. historical core angular momentum series.

    File: moira/data/historical_core_angular_momentum.txt
    Format: decimal_year  delta_lod_ms
    Source: Gillet et al. historical reconstruction (not yet released).
    Returns empty tuple if the file does not yet exist.
    """
    path = _DATA_DIR / "historical_core_angular_momentum.txt"
    if not path.exists():
        return ()
    rows: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            yr = float(parts[0])
            lod_ms = float(parts[1])
        except ValueError:
            continue
        rows.append((yr, lod_ms))
    rows.sort(key=lambda r: r[0])
    return tuple(rows)


@cache
def _get_historical_core_dt_series() -> tuple[tuple[float, float], ...]:
    """Return the cached historical core ΔT series derived from LOD anomalies."""
    return _lod_series_to_delta_t(_load_historical_core_series())


def historical_core_delta_t(year: float) -> float:
    """
    Historical core-mantle angular momentum contribution to Delta T (1840–1962).

    Returns 0.0 until moira/data/historical_core_angular_momentum.txt is
    populated with Gillet et al. historical LOD reconstruction data. Once
    present, the series is integrated exactly as core_delta_t does for the
    modern era. The historical bridge polynomial automatically recalibrates
    to absorb only the residual that the core term does not explain.

    Parameters
    ----------
    year : decimal year

    Returns
    -------
    ΔT contribution in seconds
    """
    series = _get_historical_core_dt_series()
    if not series:
        return 0.0
    if year <= series[0][0] or year >= series[-1][0]:
        return 0.0
    for i in range(len(series) - 1):
        y0, v0 = series[i]
        y1, v1 = series[i + 1]
        if y0 <= year <= y1:
            frac = (year - y0) / (y1 - y0)
            return v0 + frac * (v1 - v0)
    return 0.0


def _historical_bridge_delta_t(year: float) -> float:
    """
    Historical era bridge term for 1840 ≤ year ≤ 1962.5.

    Absorbs the gap between the secular trend and the SMH2016 observational
    constraint: secular_trend alone overshoots by ~158 s at 1840. The bridge
    is defined as ``smh2016(year) − secular_trend(year) − historical_core_delta_t(year)``
    so that the sum ``secular + bridge + historical_core = smh2016`` exactly.

    When Gillet historical LOD reconstruction data is loaded, historical_core_delta_t
    becomes non-zero and the bridge automatically shrinks to cover only the
    unexplained secular residual, decoupling the physical signal from the
    empirical correction.

    Returns 0.0 outside [_CORE_COVERAGE_START, _RESIDUAL_FIT_START].
    """
    if year < _CORE_COVERAGE_START or year > _RESIDUAL_FIT_START:
        return 0.0
    return _smh2016_lookup(year) - secular_trend(year) - historical_core_delta_t(year)


def _lod_series_to_delta_t(
    series: tuple[tuple[float, float], ...]
) -> tuple[tuple[float, float], ...]:
    """
    Convert a LOD anomaly series (ms/day, annual resolution) to cumulative
    Delta T contribution (seconds) by discrete integration.

    ΔT(y) = Σ (ΔLOD(t_i) - mean_LOD) × Δt_i / 1000
    where Δt_i is days between successive annual epochs and ΔLOD is in ms/day.

    Unit derivation: ΔLOD (ms/day) × Δt (days) = ms; dividing by 1000 gives
    seconds.  The historic erroneous divisor of 86400 understated the
    integrated contribution by a factor of 86.4.

    The series mean is subtracted before integration so the cumulative
    integral is zero-mean rather than drifting with the absolute LOD
    baseline.  This ensures the core component does not introduce a secular
    offset that duplicates the secular_trend parabola.
    """
    if not series:
        return ()
    mean_lod = sum(lod for _, lod in series) / len(series)
    result: list[tuple[float, float]] = [(series[0][0], 0.0)]
    cumulative = 0.0
    for i in range(1, len(series)):
        y0, lod0 = series[i - 1]
        y1, lod1 = series[i]
        dt_days = _series_epoch_delta_days(y0, y1)
        avg_lod_ms = ((lod0 - mean_lod) + (lod1 - mean_lod)) / 2.0
        cumulative += avg_lod_ms * dt_days / 1000.0
        result.append((y1, cumulative))
    return tuple(result)


def _series_epoch_delta_days(year0: float, year1: float) -> float:
    """
    Return the exact day spacing between two series epochs when available.

    The core LOD file declares annual means at ``calendar year + 0.5``
    (mid-year). For those epochs we compute the true midpoint-to-midpoint span
    from calendar-year boundaries, so leap years propagate into the integral.

    For any other year coordinates we fall back to a uniform Julian-year scale.
    """
    jd0 = _annual_mean_midyear_jd(year0)
    jd1 = _annual_mean_midyear_jd(year1)
    if jd0 is not None and jd1 is not None:
        return jd1 - jd0
    return (year1 - year0) * JULIAN_YEAR


def _annual_mean_midyear_jd(year: float) -> float | None:
    """
    Return the JD of a calendar-year midpoint for epochs encoded as ``Y + 0.5``.

    This matches the convention documented in ``core_angular_momentum.txt``.
    Returns ``None`` when the year value does not match that annual-mean format.
    """
    whole_year = math.floor(year)
    frac = year - whole_year
    if abs(frac - 0.5) > 1e-9:
        return None
    start = julian_day(int(whole_year), 1, 1, 0.0)
    end = julian_day(int(whole_year) + 1, 1, 1, 0.0)
    return (start + end) / 2.0


@cache
def _get_core_dt_series() -> tuple[tuple[float, float], ...]:
    """Return the cached core ΔT series derived from LOD anomalies."""
    return _lod_series_to_delta_t(_load_core_series())


@cache
def _core_recent_stats() -> tuple[float, float]:
    """Return (mean, std) of the core ΔT series over the last decorrelation window."""
    series = _get_core_dt_series()
    if not series:
        return 0.0, _CORE_HISTORICAL_SIGMA
    cutoff = series[-1][0] - _CORE_DECORRELATION_YEARS
    window = [v for y, v in series if y >= cutoff]
    if len(window) < 2:
        window = [v for _, v in series]
    mean = sum(window) / len(window)
    std = statistics.stdev(window) if len(window) >= 2 else _CORE_HISTORICAL_SIGMA
    return mean, std


@cache
def _core_terminal_value() -> float:
    """
    Return the most recent measured core ΔT value (the final series point).

    Used as the frozen future-era core contribution to ensure C0 continuity
    at the measured→future boundary.  The 10-year backward mean
    (``_core_recent_stats()[0]``) is appropriate for uncertainty estimation
    but creates a seam discontinuity when the series is strongly trending;
    the terminal value avoids that by anchoring the future exactly where the
    measured era ends.
    """
    series = _get_core_dt_series()
    return series[-1][1] if series else 0.0


def core_delta_t(year: float) -> float:
    """
    Core-mantle angular momentum contribution to Delta T.

    Coverage: determined by moira/data/core_angular_momentum.txt.
    Target data: Gillet et al. (2019/2022), 1840–present.
    Outside coverage: returns 0.0 (absorbed into residual for historical era;
    replaced by the 10-year mean for future extrapolation — see delta_t_hybrid).

    Parameters
    ----------
    year : decimal year

    Returns
    -------
    ΔT contribution in seconds
    """
    series = _get_core_dt_series()
    if not series:
        return 0.0
    if year <= series[0][0] or year >= series[-1][0]:
        return 0.0
    for i in range(len(series) - 1):
        y0, v0 = series[i]
        y1, v1 = series[i + 1]
        if y0 <= year <= y1:
            frac = (year - y0) / (y1 - y0)
            return v0 + frac * (v1 - v0)
    return 0.0


def _three_year_smooth(
    years: list[float], values: list[float]
) -> tuple[list[float], list[float]]:
    """
    Apply a 3-year centred moving average to suppress AAM noise.
    Boundary points use the available neighbours only.
    """
    n = len(years)
    if n == 0:
        return [], []
    smoothed = []
    for i in range(n):
        lo = max(0, i - 1)
        hi = min(n - 1, i + 1)
        avg = sum(values[lo : hi + 1]) / (hi - lo + 1)
        smoothed.append(avg)
    return years, smoothed


def _cosine_taper(year: float) -> float:
    """
    Cosine taper window over [_RESIDUAL_TAPER_START, _RESIDUAL_TAPER_END].
    Returns 1.0 before the window, 0.0 after, cosine ramp within.
    """
    if year <= _RESIDUAL_TAPER_START:
        return 1.0
    if year >= _RESIDUAL_TAPER_END:
        return 0.0
    span = _RESIDUAL_TAPER_END - _RESIDUAL_TAPER_START
    phase = (year - _RESIDUAL_TAPER_START) / span
    return 0.5 * (1.0 + math.cos(math.pi * phase))


def _support_fade_taper(year: float, start: float, end: float) -> float:
    """Cosine fade from 1.0 at ``start`` to 0.0 at ``end``."""
    if year <= start:
        return 1.0
    if year >= end:
        return 0.0
    span = end - start
    phase = (year - start) / span
    return 0.5 * (1.0 + math.cos(math.pi * phase))


@cache
def _fitted_residual_spline() -> _ResidualSplineFit:
    """
    Fit a smoothing spline to IERS_measured − (secular + core + cryo) over
    the 1962–taper-end window.

    Returns the spline plus named diagnostics. The spline dependency is
    mandatory for the asserted hybrid ΔT model and will raise if scipy is
    unavailable.

    Procedure (per DELTA_T_HYBRID_MODEL.md section 3, Phase 4):
    1. Compute raw residual at each annual IERS Bulletin B point.
    2. 3-year centred pre-smooth.
    3. Apply cosine taper over 2021–2024.
    4. Fit UnivariateSpline with k=3, s=N, ext=1.
    5. Interior LOO-CV diagnostic on non-boundary annual-mean epochs.
    """
    UnivariateSpline = _require_univariate_spline()

    from .julian import delta_t as _iers_delta_t

    years_raw: list[float] = []
    residuals_raw: list[float] = []

    y = _RESIDUAL_FIT_START
    while y <= _RESIDUAL_TAPER_END + 0.01:
        iers_val = _iers_delta_t(y)
        model_val = (
            secular_trend(y)
            + _modern_bridge_delta_t(y)
            + fluid_lowfreq(y)
            + core_delta_t(y)
            + cryo_delta_t(y)
        )
        years_raw.append(y)
        residuals_raw.append(iers_val - model_val)
        y += 1.0

    if len(years_raw) < 5:
        return _ResidualSplineFit(
            spline=None,
            cv_rms=_RESIDUAL_FUTURE_RMS_FALLBACK,
            in_sample_rms=_RESIDUAL_FUTURE_RMS_FALLBACK,
            knot_count=0,
        )

    _, res_smooth = _three_year_smooth(years_raw, residuals_raw)

    for i in range(len(years_raw)):
        res_smooth[i] *= _cosine_taper(years_raw[i])

    spline_years = years_raw[:]
    spline_residuals = res_smooth[:]
    if len(spline_years) >= 2:
        # Give the left boundary a reflected support point so the first
        # measured epoch is not treated as a free cubic seam.
        left_anchor_year = spline_years[0] - 1.0
        left_anchor_val = 2.0 * spline_residuals[0] - spline_residuals[1]
        spline_years.insert(0, left_anchor_year)
        spline_residuals.insert(0, left_anchor_val)

    n_raw = len(years_raw)
    # Target s_factor: n_raw / 15 drives the spline toward ~5-8 interior knots
    # so that decade-scale residual oscillations are captured without the
    # over-smoothing that results from the legacy s = n initialisation (which
    # stalls at 2 knots once SSE < n).
    s_factor = float(n_raw) / 15.0
    spline = UnivariateSpline(spline_years, spline_residuals, k=3, s=s_factor, ext=1)

    knot_count = len(spline.get_knots())
    if knot_count > 20:
        s_factor = float(n_raw) * (knot_count / 20.0) / 15.0
        spline = UnivariateSpline(spline_years, spline_residuals, k=3, s=s_factor, ext=1)

    loo_errors: list[float] = []
    for i in range(1, len(years_raw) - 1):
        ys_loo = spline_years[:]
        rs_loo = spline_residuals[:]
        del ys_loo[i + 1]
        del rs_loo[i + 1]
        if len(ys_loo) < 5:
            continue
        try:
            sp_loo = UnivariateSpline(ys_loo, rs_loo, k=3, s=s_factor, ext=1)
            loo_errors.append((res_smooth[i] - float(sp_loo(years_raw[i]))) ** 2)
        except Exception:
            pass

    if loo_errors:
        cv_rms = math.sqrt(sum(loo_errors) / len(loo_errors))
        if cv_rms > 0.4:
            s_factor *= cv_rms / 0.4
            spline = UnivariateSpline(spline_years, spline_residuals, k=3, s=s_factor, ext=1)
    else:
        cv_rms = _RESIDUAL_FUTURE_RMS_FALLBACK

    in_sample_errors = [
        (res_smooth[i] - float(spline(years_raw[i]))) ** 2
        for i in range(n_raw)
    ]
    in_sample_rms = math.sqrt(sum(in_sample_errors) / n_raw) if in_sample_errors else _RESIDUAL_FUTURE_RMS_FALLBACK

    return _ResidualSplineFit(
        spline=spline,
        cv_rms=cv_rms,
        in_sample_rms=in_sample_rms,
        knot_count=len(spline.get_knots()),
    )


def _residual_at(year: float) -> float:
    """Evaluate the fitted residual spline at the given decimal year."""
    fit = _fitted_residual_spline()
    if fit.spline is None:
        return 0.0
    return float(fit.spline(year))


def delta_t_hybrid(year: float) -> float:
    """
    Physics-based hybrid Delta T model.

    Era routing:
      pre-1840  : delegates to SMH 2016 table (unchanged)
      1840–2026 : secular + core + cryo + IERS residual spline
      2026+     : secular + cryo trend extrapolation + core terminal value

    Component status:
      The historical core angular momentum component (``historical_core_delta_t``)
      contributes zero at all epochs because the required data file
      ``moira/data/historical_core_angular_momentum.txt`` is not present in
      this installation.  The function therefore sums four active components,
      not five.  When the data file is added, the core component becomes
      non-zero and the bridge term automatically shrinks to compensate.

    See DELTA_T_HYBRID_MODEL.md for the full architecture, era coverage
    table, and continuity constraint derivation.

    Parameters
    ----------
    year : decimal year

    Returns
    -------
    ΔT = TT − UT1 in seconds
    """
    return delta_t_breakdown(year).total


def delta_t_hybrid_uncertainty(year: float) -> float:
    """
    ±1σ uncertainty on delta_t_hybrid(year), in seconds.

    Components are combined in quadrature (independent sources).
    Dominant term for future dates is core-mantle unpredictability.
    See DELTA_T_HYBRID_MODEL.md section 8 for the full derivation.

    Parameters
    ----------
    year : decimal year

    Returns
    -------
    ±1σ in seconds
    """
    y = float(year)
    t = (y - REFERENCE_YEAR) / 100.0

    sigma_tidal = abs(TIDAL_COEFF * t * t) * (0.003 / 25.858)

    sigma_gia = _GIA_COEFF_SIGMA * t * t

    grace_series = _load_grace_series()
    grace_end = grace_series[-1][0] if grace_series else REFERENCE_YEAR
    if y <= grace_end:
        sigma_cryo = 0.003
    else:
        sigma_cryo = _CRYO_TREND_SIGMA * (y - grace_end)

    core_series = _get_core_dt_series()
    if core_series and y <= core_series[-1][0]:
        sigma_core = _CORE_HISTORICAL_SIGMA
    else:
        _, core_std = _core_recent_stats()
        sigma_core = core_std if core_std > 0.0 else _CORE_HISTORICAL_SIGMA

    fit = _fitted_residual_spline()
    # Measured-era: 10 % of in-sample RMS (spline corrects the bulk).
    # Future: cv_rms is the honest out-of-sample prediction error; it is
    # always >= in_sample_rms and preserves monotone growth of sigma past
    # the REFERENCE_YEAR hand-off.
    sigma_residual = fit.in_sample_rms * 0.1 if y <= REFERENCE_YEAR else fit.cv_rms

    return math.sqrt(
        sigma_tidal ** 2
        + sigma_gia ** 2
        + sigma_cryo ** 2
        + sigma_core ** 2
        + sigma_residual ** 2
    )


@dataclass(frozen=True, slots=True)
class DeltaTBreakdown:
    """
    Component breakdown of the hybrid ΔT model for a single decimal year.

    All values are in seconds (TT − UT1 contribution).
    ``secular + core + cryo + fluid + bridge + residual == total`` for all eras.

    Attributes
    ----------
    year : float
        Decimal year of the computation.
    total : float
        Total ΔT in seconds — equals ``delta_t_hybrid(year)``.
    secular : float
        Tidal + GIA secular parabola contribution.  In the ``'pre-1840'`` era
        this equals the full SMH 2016 table value (``_smh2016_lookup(year)``),
        not ``secular_trend(year)`` — it is *not*
        ``secular_trend(year)``.  In all other eras it equals
        ``secular_trend(year)``.
    core : float
        Core-mantle angular momentum contribution.  In the future era this
        is the terminal measured series value (``_core_terminal_value()``) —
        the most recent data point — ensuring C0 continuity at the
        measured→future boundary.  In the pre-1840 era it is zero.
    cryo : float
        Cryosphere/hydrosphere GRACE/GRACE-FO contribution.
    fluid : float
        Low-frequency fluid AAM + OAM contribution (measured era only;
        zero otherwise).
    bridge : float
        Smooth polynomial bridge term used in the measured era
        (``_modern_bridge_delta_t``) or the historical era
        (``_historical_bridge_delta_t``); zero in the future and pre-1840
        eras.
    residual : float
        IERS residual spline correction (measured era only; zero otherwise).
    era : str
        Which era routing was applied.  One of ``'pre-1840'``,
        ``'historical'``, ``'measured'``, or ``'future'``.
    """

    year: float
    total: float
    secular: float
    core: float
    cryo: float
    fluid: float
    bridge: float
    residual: float
    era: str


def delta_t_breakdown(year: float) -> DeltaTBreakdown:
    """
    Return the component breakdown of the hybrid ΔT model for the given year.

    The returned :class:`DeltaTBreakdown` exposes every additive term that
    ``delta_t_hybrid`` uses internally so that callers can inspect the
    relative magnitude of tidal forcing, core-mantle variation,
    cryospheric loading, and the IERS residual correction without having to
    call each component function individually.

    Parameters
    ----------
    year : decimal year

    Returns
    -------
    DeltaTBreakdown
        Immutable dataclass whose fields sum to ``total == delta_t_hybrid(year)``.

    Examples
    --------
    >>> from moira.delta_t_physical import delta_t_breakdown
    >>> bd = delta_t_breakdown(2024.5)
    >>> import math
    >>> math.isclose(bd.total, bd.secular + bd.core + bd.cryo + bd.fluid + bd.bridge + bd.residual)
    True
    """
    y = float(year)

    if y < _CORE_COVERAGE_START:
        # Pre-1840: entire value sourced from the SMH 2016 table.
        # secular holds the raw table value (not secular_trend); all other components are zero.
        total = _smh2016_lookup(y)
        return DeltaTBreakdown(
            year=y,
            total=total,
            secular=total,
            core=0.0,
            cryo=0.0,
            fluid=0.0,
            bridge=0.0,
            residual=0.0,
            era='pre-1840',
        )

    if y < _RESIDUAL_FIT_START:
        # 1840–1962.4: physics-based historical era.
        # secular + historical bridge + historical core.
        sec = secular_trend(y)
        hist_core = historical_core_delta_t(y)
        hist_bridge = _historical_bridge_delta_t(y)
        total = sec + hist_bridge + hist_core
        return DeltaTBreakdown(
            year=y,
            total=total,
            secular=sec,
            core=hist_core,
            cryo=0.0,
            fluid=0.0,
            bridge=hist_bridge,
            residual=0.0,
            era='historical',
        )

    sec = secular_trend(y)
    cryo = cryo_delta_t(y)

    if y <= REFERENCE_YEAR:
        # Measured era: secular + fluid + bridge + core + cryo + residual spline.
        fluid = fluid_lowfreq(y)
        core = core_delta_t(y)
        bridge = _modern_bridge_delta_t(y)
        resid = _residual_at(y)
        total = sec + fluid + bridge + core + cryo + resid
        return DeltaTBreakdown(
            year=y,
            total=total,
            secular=sec,
            core=core,
            cryo=cryo,
            fluid=fluid,
            bridge=bridge,
            residual=resid,
            era='measured',
        )

    # Future era (> REFERENCE_YEAR): secular + core terminal value + cryo trend.
    # Use the most recent measured value rather than the 10-year backward mean
    # so the core contribution is C0 continuous at the era boundary.
    core_frozen = _core_terminal_value()
    total = sec + core_frozen + cryo
    return DeltaTBreakdown(
        year=y,
        total=total,
        secular=sec,
        core=core_frozen,
        cryo=cryo,
        fluid=0.0,
        bridge=0.0,
        residual=0.0,
        era='future',
    )

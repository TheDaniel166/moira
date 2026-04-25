"""
validate_delta_t_hybrid.py — Comparison study: hybrid vs measured/conventional Delta T.

Three comparisons:
  1. hybrid vs current delta_t()         — 1962.5–2024.5 measured annual-mean era
  2. hybrid future vs conventional forecast — 2026–2100 extrapolation divergence
  3. hybrid apparent-position impact     — delta_t difference converted to arcseconds
     for Moon, Sun, and outer planets using angular velocity approximations
  4. residual budget decomposition       — how much structure remains after each
     physical layer across the measured annual-mean era

Usage:
    python scripts/validate_delta_t_hybrid.py

No network access required.  matplotlib used for plots if available.
"""

import math
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from moira.delta_t_physical import (
    core_delta_t,
    cryo_delta_t,
    delta_t_hybrid,
    delta_t_hybrid_uncertainty,
    fluid_lowfreq,
    secular_trend,
    _modern_bridge_delta_t,
    _fitted_residual_spline,
    _residual_at,
    _three_year_smooth,
)
from moira.julian import delta_t as current_delta_t
from moira.julian import delta_t_nasa_canon as conventional_delta_t
from moira.julian import julian_day


# ---------------------------------------------------------------------------
# Angular velocity approximations (deg/day) for arcsecond conversion
# ---------------------------------------------------------------------------

_BODY_DEG_PER_DAY: dict[str, float] = {
    "Moon":    13.176,
    "Sun":      0.9856,
    "Mercury":  4.0923,
    "Venus":    1.6021,
    "Mars":     0.5240,
    "Jupiter":  0.0831,
    "Saturn":   0.0335,
    "Uranus":   0.0117,
    "Neptune":  0.0060,
}

_AAM_ANNUAL_PATH = _REPO_ROOT / "moira" / "data" / "aam_glaam_annual.txt"
_OAM_ANNUAL_PATH = _REPO_ROOT / "moira" / "data" / "oam_ecco_annual.txt"


def _arcsec_from_dt_diff(dt_diff_s: float, deg_per_day: float) -> float:
    deg_per_second = deg_per_day / 86400.0
    return abs(dt_diff_s) * deg_per_second * 3600.0


# ---------------------------------------------------------------------------
# Comparison 1: hybrid vs current delta_t — measured annual-mean era 1962.5–2024.5
# ---------------------------------------------------------------------------

def comparison_1_measured_era() -> list[tuple[float, float, float, float]]:
    rows = []
    yf = 1962.5
    while yf <= 2024.5 + 1e-9:
        cur = current_delta_t(yf)
        hyb = delta_t_hybrid(yf)
        diff = hyb - cur
        rows.append((yf, cur, hyb, diff))
        yf += 1.0
    return rows


# ---------------------------------------------------------------------------
# Comparison 2: hybrid future vs conventional long-term forecast — 2026–2100
# ---------------------------------------------------------------------------

def comparison_2_future() -> list[tuple[float, float, float, float, float]]:
    rows = []
    for y in range(2026, 2101):
        yf = float(y)
        table = conventional_delta_t(yf)
        hyb = delta_t_hybrid(yf)
        sigma = delta_t_hybrid_uncertainty(yf)
        diff = hyb - table
        rows.append((yf, table, hyb, diff, sigma))
    return rows


# ---------------------------------------------------------------------------
# Comparison 3: apparent-position impact — dt difference to arcseconds
# ---------------------------------------------------------------------------

def comparison_3_arcsec(
    rows_future: list[tuple[float, float, float, float, float]]
) -> dict[str, list[tuple[float, float]]]:
    result: dict[str, list[tuple[float, float]]] = {body: [] for body in _BODY_DEG_PER_DAY}
    for yf, _table, _hyb, diff, _sigma in rows_future:
        for body, deg_per_day in _BODY_DEG_PER_DAY.items():
            arcsec = _arcsec_from_dt_diff(diff, deg_per_day)
            result[body].append((yf, arcsec))
    return result


# ---------------------------------------------------------------------------
# Comparison 4: residual budget decomposition — measured annual-mean era
# ---------------------------------------------------------------------------

def comparison_4_residual_budget() -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    y = 1962.5
    while y <= 2024.5 + 1e-9:
        measured = current_delta_t(y)
        secular = secular_trend(y)
        core = core_delta_t(y)
        cryo = cryo_delta_t(y)
        residual = _residual_at(y)
        rows.append({
            "year": y,
            "measured": measured,
            "secular_only_residual": measured - secular,
            "secular_fluid_residual": measured - (secular + fluid_lowfreq(y)),
            "secular_fluid_bridge_residual": measured - (secular + fluid_lowfreq(y) + _modern_bridge_delta_t(y)),
            "secular_fluid_bridge_core_residual": measured - (secular + fluid_lowfreq(y) + _modern_bridge_delta_t(y) + core),
            "secular_fluid_bridge_core_cryo_residual": measured - (secular + fluid_lowfreq(y) + _modern_bridge_delta_t(y) + core + cryo),
            "final_model_residual": measured - (secular + fluid_lowfreq(y) + _modern_bridge_delta_t(y) + core + cryo + residual),
            "fluid": fluid_lowfreq(y),
            "core": core,
            "cryo": cryo,
            "bridge": _modern_bridge_delta_t(y),
            "residual_term": residual,
        })
        y += 1.0
    return rows


def _load_aam_glaam_annual() -> list[tuple[float, float]]:
    if not _AAM_ANNUAL_PATH.exists():
        return []
    rows: list[tuple[float, float]] = []
    for raw in _AAM_ANNUAL_PATH.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        rows.append((float(parts[0]), float(parts[1])))
    return rows


def _load_oam_ecco_annual() -> list[tuple[float, float]]:
    if not _OAM_ANNUAL_PATH.exists():
        return []
    rows: list[tuple[float, float]] = []
    for raw in _OAM_ANNUAL_PATH.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 2:
            continue
        rows.append((float(parts[0]), float(parts[1])))
    return rows


def _series_epoch_delta_days(year0: float, year1: float) -> float:
    start0 = julian_day(int(math.floor(year0)), 1, 1, 0.0)
    end0 = julian_day(int(math.floor(year0)) + 1, 1, 1, 0.0)
    jd0 = (start0 + end0) / 2.0
    start1 = julian_day(int(math.floor(year1)), 1, 1, 0.0)
    end1 = julian_day(int(math.floor(year1)) + 1, 1, 1, 0.0)
    jd1 = (start1 + end1) / 2.0
    return jd1 - jd0


def _integrated_aam_proxy(rows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not rows:
        return []
    years = [y for y, _ in rows]
    vals = [v for _, v in rows]
    _, vals_smoothed = _three_year_smooth(years, vals)
    mean_val = _mean(vals_smoothed)
    result: list[tuple[float, float]] = [(years[0], 0.0)]
    cumulative = 0.0
    for i in range(1, len(rows)):
        y0 = years[i - 1]
        y1 = years[i]
        v0 = vals_smoothed[i - 1] - mean_val
        v1 = vals_smoothed[i] - mean_val
        dt_days = _series_epoch_delta_days(y0, y1)
        cumulative += ((v0 + v1) / 2.0) * dt_days / 86400.0
        result.append((y1, cumulative))
    return result


def _integrated_oam_proxy(rows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not rows:
        return []
    years = [y for y, _ in rows]
    vals = [v for _, v in rows]
    _, vals_smoothed = _three_year_smooth(years, vals)
    mean_val = _mean(vals_smoothed)
    result: list[tuple[float, float]] = [(years[0], 0.0)]
    cumulative = 0.0
    for i in range(1, len(rows)):
        y0 = years[i - 1]
        y1 = years[i]
        v0 = vals_smoothed[i - 1] - mean_val
        v1 = vals_smoothed[i] - mean_val
        dt_days = _series_epoch_delta_days(y0, y1)
        cumulative += ((v0 + v1) / 2.0) * dt_days / 86400.0
        result.append((y1, cumulative))
    return result


def comparison_5_aam_bridge_overlap() -> dict[str, object] | None:
    rows = _load_aam_glaam_annual()
    proxy = _integrated_aam_proxy(rows)
    if not proxy:
        return None

    overlap = [(y, v) for y, v in proxy if 1962.5 <= y <= 2014.5]
    if len(overlap) < 10:
        return None

    years = [y for y, _ in overlap]
    proxy_vals = [v for _, v in overlap]
    bridge_vals = [_modern_bridge_delta_t(y) for y in years]

    num = sum(p * b for p, b in zip(proxy_vals, bridge_vals))
    den = sum(p * p for p in proxy_vals)
    scale = num / den if den != 0.0 else 0.0

    fitted = [scale * p for p in proxy_vals]
    residual = [bridge_vals[i] - fitted[i] for i in range(len(years))]
    bridge_rms = _rms(bridge_vals)
    unexplained_rms = _rms(residual)
    corr_num = sum(
        (proxy_vals[i] - _mean(proxy_vals)) * (bridge_vals[i] - _mean(bridge_vals))
        for i in range(len(years))
    )
    corr_den = math.sqrt(
        sum((p - _mean(proxy_vals)) ** 2 for p in proxy_vals)
        * sum((b - _mean(bridge_vals)) ** 2 for b in bridge_vals)
    )
    corr = corr_num / corr_den if corr_den != 0.0 else 0.0

    sample_rows = [
        {
            "year": years[i],
            "proxy": proxy_vals[i],
            "bridge": bridge_vals[i],
            "fitted": fitted[i],
            "residual": residual[i],
        }
        for i in range(0, len(years), 5)
    ]

    return {
        "years": (years[0], years[-1]),
        "scale": scale,
        "corr": corr,
        "bridge_rms": bridge_rms,
        "unexplained_rms": unexplained_rms,
        "sample_rows": sample_rows,
    }


def comparison_6_aam_oam_bridge_overlap() -> dict[str, object] | None:
    aam_rows = _load_aam_glaam_annual()
    oam_rows = _load_oam_ecco_annual()
    aam_proxy = dict(_integrated_aam_proxy(aam_rows))
    oam_proxy = dict(_integrated_oam_proxy(oam_rows))
    common_years = sorted(
        y for y in aam_proxy.keys()
        if y in oam_proxy and 1962.5 <= y <= 2002.5
    )
    if len(common_years) < 10:
        return None

    a_vals = [aam_proxy[y] for y in common_years]
    o_vals = [oam_proxy[y] for y in common_years]
    b_vals = [_modern_bridge_delta_t(y) for y in common_years]

    saa = sum(a * a for a in a_vals)
    sao = sum(a_vals[i] * o_vals[i] for i in range(len(common_years)))
    soo = sum(o * o for o in o_vals)
    sab = sum(a_vals[i] * b_vals[i] for i in range(len(common_years)))
    sob = sum(o_vals[i] * b_vals[i] for i in range(len(common_years)))
    det = saa * soo - sao * sao
    if det == 0.0:
        return None
    alpha = (sab * soo - sob * sao) / det
    beta = (saa * sob - sao * sab) / det

    fitted = [alpha * a_vals[i] + beta * o_vals[i] for i in range(len(common_years))]
    residual = [b_vals[i] - fitted[i] for i in range(len(common_years))]

    sample_rows = [
        {
            "year": common_years[i],
            "aam_proxy": a_vals[i],
            "oam_proxy": o_vals[i],
            "bridge": b_vals[i],
            "fit": fitted[i],
            "residual": residual[i],
        }
        for i in range(0, len(common_years), 5)
    ]

    return {
        "years": (common_years[0], common_years[-1]),
        "alpha": alpha,
        "beta": beta,
        "bridge_rms": _rms(b_vals),
        "unexplained_rms": _rms(residual),
        "sample_rows": sample_rows,
    }


def comparison_7_fluid_replacement_budget() -> dict[str, object] | None:
    fit = comparison_6_aam_oam_bridge_overlap()
    if fit is None:
        return None

    aam_proxy = dict(_integrated_aam_proxy(_load_aam_glaam_annual()))
    oam_proxy = dict(_integrated_oam_proxy(_load_oam_ecco_annual()))

    years = [
        y for y in sorted(aam_proxy.keys())
        if y in oam_proxy and 1962.5 <= y <= 2002.5
    ]
    if len(years) < 10:
        return None

    alpha = float(fit["alpha"])
    beta = float(fit["beta"])

    rows: list[dict[str, float]] = []
    for y in years:
        measured = current_delta_t(y)
        secular = secular_trend(y)
        core = core_delta_t(y)
        cryo = cryo_delta_t(y)
        fluid = alpha * aam_proxy[y] + beta * oam_proxy[y]
        bridge = _modern_bridge_delta_t(y)
        rows.append({
            "year": y,
            "fluid": fluid,
            "bridge": bridge,
            "bridge_remainder": bridge - fluid,
            "post_secular_core_cryo": measured - (secular + core + cryo),
            "post_fluid": measured - (secular + fluid + core + cryo),
            "post_bridge": measured - (secular + bridge + core + cryo),
            "post_fluid_plus_bridge_remainder": measured - (secular + fluid + (bridge - fluid) + core + cryo),
        })

    return {
        "years": (years[0], years[-1]),
        "rows": rows,
        "bridge_rms": _rms([row["bridge"] for row in rows]),
        "fluid_rms": _rms([row["fluid"] for row in rows]),
        "bridge_remainder_rms": _rms([row["bridge_remainder"] for row in rows]),
        "post_fluid_rms": _rms([row["post_fluid"] for row in rows]),
        "post_bridge_rms": _rms([row["post_bridge"] for row in rows]),
        "post_fluid_plus_bridge_remainder_rms": _rms([row["post_fluid_plus_bridge_remainder"] for row in rows]),
        "sample_rows": [rows[i] for i in range(0, len(rows), 5)],
    }


def comparison_8_lagged_fluid_plus_core_bridge_overlap(
    lag_years: float = 4.0,
) -> dict[str, object] | None:
    aam_proxy = dict(_integrated_aam_proxy(_load_aam_glaam_annual()))
    oam_proxy = dict(_integrated_oam_proxy(_load_oam_ecco_annual()))
    years = sorted(
        y for y in aam_proxy.keys()
        if y in oam_proxy and 1962.5 <= y <= 2002.5
    )
    rows: list[tuple[float, float, float, float, float]] = []
    for y in years:
        yl = y + lag_years
        if yl not in aam_proxy or yl not in oam_proxy:
            continue
        rows.append((
            y,
            aam_proxy[yl],
            oam_proxy[yl],
            core_delta_t(y),
            _modern_bridge_delta_t(y),
        ))
    if len(rows) < 10:
        return None

    import numpy as np

    mat = np.array([[row[1], row[2], row[3]] for row in rows], dtype=float)
    vec = np.array([row[4] for row in rows], dtype=float)
    scales = np.array(
        [
            max(float(np.max(np.abs(mat[:, i]))), 1.0)
            for i in range(mat.shape[1])
        ],
        dtype=float,
    )
    mat_scaled = mat / scales
    coeff_scaled = np.linalg.lstsq(mat_scaled, vec, rcond=None)[0]
    coeff = coeff_scaled / scales
    fitted = mat @ coeff
    residual = vec - fitted

    sample_rows = [
        {
            "year": rows[i][0],
            "bridge": rows[i][4],
            "fit": float(fitted[i]),
            "residual": float(residual[i]),
            "core": rows[i][3],
        }
        for i in range(0, len(rows), 5)
    ]

    return {
        "years": (rows[0][0], rows[-1][0]),
        "lag_years": lag_years,
        "alpha": float(coeff[0]),
        "beta": float(coeff[1]),
        "gamma_core": float(coeff[2]),
        "bridge_rms": _rms(list(vec)),
        "unexplained_rms": _rms(list(residual)),
        "sample_rows": sample_rows,
    }


def comparison_9_envelope_search() -> dict[str, object] | None:
    aam_proxy = dict(_integrated_aam_proxy(_load_aam_glaam_annual()))
    oam_proxy = dict(_integrated_oam_proxy(_load_oam_ecco_annual()))
    base_years = sorted(
        y for y in aam_proxy.keys()
        if 1962.5 <= y <= 2002.5
    )
    if not base_years:
        return None

    import numpy as np

    best: dict[str, object] | None = None
    for aam_lag in range(-5, 6):
        for oam_lag in range(-5, 6):
            rows: list[tuple[float, float, float, float, float]] = []
            for y in base_years:
                ya = y + float(aam_lag)
                yo = y + float(oam_lag)
                if ya not in aam_proxy or yo not in oam_proxy:
                    continue
                rows.append((
                    y,
                    aam_proxy[ya],
                    oam_proxy[yo],
                    core_delta_t(y),
                    _modern_bridge_delta_t(y),
                ))
            if len(rows) < 20:
                continue

            # Search both with and without the core regressor.
            for include_core in (False, True):
                mat_cols = [
                    [row[1], row[2]] if not include_core else [row[1], row[2], row[3]]
                    for row in rows
                ]
                mat = np.array(mat_cols, dtype=float)
                vec = np.array([row[4] for row in rows], dtype=float)
                scales = np.array(
                    [max(float(np.max(np.abs(mat[:, i]))), 1.0) for i in range(mat.shape[1])],
                    dtype=float,
                )
                mat_scaled = mat / scales
                coeff_scaled = np.linalg.lstsq(mat_scaled, vec, rcond=None)[0]
                coeff = coeff_scaled / scales
                fitted = mat @ coeff
                residual = vec - fitted
                unexplained_rms = _rms(list(residual))

                candidate = {
                    "years": (rows[0][0], rows[-1][0]),
                    "aam_lag": float(aam_lag),
                    "oam_lag": float(oam_lag),
                    "include_core": include_core,
                    "bridge_rms": _rms(list(vec)),
                    "unexplained_rms": unexplained_rms,
                    "coefficients": [float(c) for c in coeff],
                    "sample_rows": [
                        {
                            "year": rows[i][0],
                            "bridge": rows[i][4],
                            "fit": float(fitted[i]),
                            "residual": float(residual[i]),
                        }
                        for i in range(0, len(rows), max(1, len(rows) // 8))
                    ],
                }
                if best is None or unexplained_rms < float(best["unexplained_rms"]):
                    best = candidate
    return best


def comparison_10_core_construction_audit() -> dict[str, float] | None:
    from moira.delta_t_physical import _get_core_dt_series, _load_core_series

    raw_series = _load_core_series()
    core_dt = _get_core_dt_series()
    if not raw_series or not core_dt:
        return None

    current_core_vals = [v for y, v in core_dt if 1962.5 <= y <= 2024.5]
    bridge_vals = [_modern_bridge_delta_t(y) for y, _ in raw_series if 1962.5 <= y <= 2024.5]
    if not current_core_vals or not bridge_vals:
        return None

    no_mean: list[tuple[float, float]] = [(raw_series[0][0], 0.0)]
    cumulative = 0.0
    for i in range(1, len(raw_series)):
        y0, lod0 = raw_series[i - 1]
        y1, lod1 = raw_series[i]
        dt_days = _series_epoch_delta_days(y0, y1)
        avg_lod_ms = (lod0 + lod1) / 2.0
        cumulative += avg_lod_ms * dt_days / 1000.0
        no_mean.append((y1, cumulative))

    no_mean_vals = [v for y, v in no_mean if 1962.5 <= y <= 2024.5]
    end_anchor = no_mean[-1][1]
    end_anchored_vals = [v - end_anchor for y, v in no_mean if 1962.5 <= y <= 2024.5]

    return {
        "current_core_rms": _rms(current_core_vals),
        "current_core_max_abs": max(abs(v) for v in current_core_vals),
        "no_mean_core_rms": _rms(no_mean_vals),
        "no_mean_core_max_abs": max(abs(v) for v in no_mean_vals),
        "end_anchored_core_rms": _rms(end_anchored_vals),
        "end_anchored_core_max_abs": max(abs(v) for v in end_anchored_vals),
        "bridge_rms": _rms(bridge_vals),
        "bridge_max_abs": max(abs(v) for v in bridge_vals),
    }


# ---------------------------------------------------------------------------
# Print tables
# ---------------------------------------------------------------------------

def _print_table_1(rows: list[tuple[float, float, float, float]]) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 1 - Hybrid vs current delta_t()  [annual-mean era 1962.5-2024.5]")
    print("=" * 70)
    print(f"{'Year':>6}  {'current':>10}  {'hybrid':>10}  {'diff':>10}  {'|diff|':>8}")
    print("-" * 52)
    for y, cur, hyb, diff in rows[::5]:
        print(f"{y:6.1f}  {cur:10.3f}  {hyb:10.3f}  {diff:+10.3f}  {abs(diff):8.3f}")
    diffs = [abs(r[3]) for r in rows]
    rms = math.sqrt(sum(d * d for d in diffs) / len(diffs))
    print("-" * 52)
    print(f"  Max |diff|: {max(diffs):.3f} s    RMS: {rms:.3f} s    Mean: {sum(diffs)/len(diffs):.3f} s")


def _print_table_2(rows: list[tuple[float, float, float, float, float]]) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 2 - Hybrid vs conventional forecast  [future 2026-2100]")
    print("=" * 70)
    print(f"{'Year':>6}  {'forecast':>10}  {'hybrid':>10}  {'diff':>10}  {'+-1s':>8}")
    print("-" * 55)
    for y, table, hyb, diff, sigma in rows[::5]:
        print(f"{y:6.0f}  {table:10.3f}  {hyb:10.3f}  {diff:+10.3f}  {sigma:8.3f}")
    diffs = [abs(r[3]) for r in rows]
    print("-" * 55)
    print(f"  Max |diff| by 2100: {max(diffs):.3f} s")
    print(f"  Hybrid +-1s at 2100: {rows[-1][4]:.3f} s")
    print(f"  Forecast at 2100:   {rows[-1][1]:.3f} s")
    print(f"  Hybrid    at 2100:  {rows[-1][2]:.3f} s")


def _print_table_3(arcsec_data: dict[str, list[tuple[float, float]]]) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 3 - Apparent-position impact of hybrid-forecast diff")
    print("             [arcseconds, future 2026–2100]")
    print("=" * 70)
    check_years = [2030, 2040, 2050, 2060, 2075, 2100]
    header = f"{'Body':<10}" + "".join(f"  {y:>8}" for y in check_years)
    print(header)
    print("-" * (10 + 10 * len(check_years)))
    for body in _BODY_DEG_PER_DAY:
        series = dict(arcsec_data[body])
        row = f"{body:<10}"
        for y in check_years:
            val = series.get(float(y), 0.0)
            row += f"  {val:8.3f}"
        print(row)
    print()
    print("  Note: values are |hybrid - conventional forecast| converted to apparent arcseconds.")
    print("  These represent the position difference IF the two models diverge by")
    print("  that amount - not an error relative to Horizons.")


def _rms(values: list[float]) -> float:
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _decadal_mean_abs(rows: list[dict[str, float]], key: str) -> list[tuple[int, float]]:
    buckets: dict[int, list[float]] = {}
    for row in rows:
        decade = int(math.floor(row["year"] / 10.0) * 10)
        buckets.setdefault(decade, []).append(abs(row[key]))
    return [(decade, _mean(vals)) for decade, vals in sorted(buckets.items())]


def _print_table_4(rows: list[dict[str, float]]) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 4 - Residual budget decomposition  [annual-mean era 1962.5-2024.5]")
    print("=" * 70)
    print(
        f"{'Layer':<28} {'RMS':>10} {'Mean|res|':>12} {'Max|res|':>12}"
    )
    print("-" * 66)

    layer_keys = [
        ("Measured - secular", "secular_only_residual"),
        ("Measured - (secular + fluid)", "secular_fluid_residual"),
        ("Measured - (secular + fluid + bridge)", "secular_fluid_bridge_residual"),
        ("Measured - (secular + fluid + bridge + core)", "secular_fluid_bridge_core_residual"),
        ("Measured - (secular + fluid + bridge + core + cryo)", "secular_fluid_bridge_core_cryo_residual"),
        ("Measured - final hybrid", "final_model_residual"),
    ]
    for label, key in layer_keys:
        vals = [row[key] for row in rows]
        abs_vals = [abs(v) for v in vals]
        print(
            f"{label:<28} {_rms(vals):10.3f} {_mean(abs_vals):12.3f} {max(abs_vals):12.3f}"
        )

    print("\nSample epochs:")
    print(
        f"{'Year':>6} {'fluid':>9} {'bridge':>9} {'core':>9} {'cryo':>9} {'resid term':>11} {'post sec':>11} {'post sec+fluid':>15} {'post sec+fluid+bridge':>22} {'post sec+fluid+bridge+core':>27} {'final':>9}"
    )
    print("-" * 165)
    for row in rows[::5]:
        print(
            f"{row['year']:6.1f} {row['fluid']:9.3f} {row['bridge']:9.3f} {row['core']:9.3f} {row['cryo']:9.3f} {row['residual_term']:11.3f} "
            f"{row['secular_only_residual']:11.3f} {row['secular_fluid_residual']:15.3f} {row['secular_fluid_bridge_residual']:22.3f} "
            f"{row['secular_fluid_bridge_core_residual']:27.3f} {row['final_model_residual']:9.3f}"
        )

    print("\nDecadal mean |residual|:")
    decade_series = [
        ("post secular", "secular_only_residual"),
        ("post secular+fluid", "secular_fluid_residual"),
        ("post secular+fluid+bridge", "secular_fluid_bridge_residual"),
        ("post secular+fluid+bridge+core", "secular_fluid_bridge_core_residual"),
        ("post secular+fluid+bridge+core+cryo", "secular_fluid_bridge_core_cryo_residual"),
        ("final hybrid", "final_model_residual"),
    ]
    for label, key in decade_series:
        decade_vals = _decadal_mean_abs(rows, key)
        formatted = ", ".join(f"{decade}s={val:.3f}" for decade, val in decade_vals)
        print(f"  {label:<22} {formatted}")


def _print_table_5(result: dict[str, object] | None) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 5 - AAM proxy vs measured-era bridge")
    print("=" * 70)
    if result is None:
        print("AAM annual proxy file not present or insufficient overlap.")
        print(f"Expected path: {_AAM_ANNUAL_PATH}")
        return

    y0, y1 = result["years"]
    print(f"Overlap years: {y0:.1f}–{y1:.1f}")
    print(f"Fitted scale: {result['scale']:.6e}")
    print(f"Correlation:  {result['corr']:.3f}")
    print(f"Bridge RMS:   {result['bridge_rms']:.3f} s")
    print(f"Unexplained bridge RMS after AAM fit: {result['unexplained_rms']:.3f} s")
    print()
    print(f"{'Year':>6} {'AAM proxy':>14} {'bridge':>10} {'fit':>10} {'resid':>10}")
    print("-" * 60)
    for row in result["sample_rows"]:
        print(
            f"{row['year']:6.1f} {row['proxy']:14.6e} {row['bridge']:10.3f} "
            f"{row['fitted']:10.3f} {row['residual']:10.3f}"
        )


def _print_table_6(result: dict[str, object] | None) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 6 - AAM + OAM proxy vs measured-era bridge")
    print("=" * 70)
    if result is None:
        print("AAM/OAM overlap data not present or insufficient.")
        print(f"Expected paths: {_AAM_ANNUAL_PATH} and {_OAM_ANNUAL_PATH}")
        return

    y0, y1 = result["years"]
    print(f"Overlap years: {y0:.1f}–{y1:.1f}")
    print(f"AAM scale alpha: {result['alpha']:.6e}")
    print(f"OAM scale beta:  {result['beta']:.6e}")
    print(f"Bridge RMS:      {result['bridge_rms']:.3f} s")
    print(f"Unexplained bridge RMS after AAM+OAM fit: {result['unexplained_rms']:.3f} s")
    print()
    print(f"{'Year':>6} {'AAM proxy':>14} {'OAM proxy':>14} {'bridge':>10} {'fit':>10} {'resid':>10}")
    print("-" * 74)
    for row in result["sample_rows"]:
        print(
            f"{row['year']:6.1f} {row['aam_proxy']:14.6e} {row['oam_proxy']:14.6e} "
            f"{row['bridge']:10.3f} {row['fit']:10.3f} {row['residual']:10.3f}"
        )


def _print_table_7(result: dict[str, object] | None) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 7 - Fluid-term replacement budget")
    print("=" * 70)
    if result is None:
        print("Fluid replacement budget unavailable.")
        return

    y0, y1 = result["years"]
    print(f"Overlap years: {y0:.1f}–{y1:.1f}")
    print(f"Bridge RMS:                 {result['bridge_rms']:.3f} s")
    print(f"Fluid-term RMS:             {result['fluid_rms']:.3f} s")
    print(f"Bridge remainder RMS:       {result['bridge_remainder_rms']:.3f} s")
    print(f"Post secular+core+cryo RMS: {result['post_fluid_rms']:.3f} s  [using fluid term only]")
    print(f"Post bridge RMS:            {result['post_bridge_rms']:.3f} s  [using current bridge]")
    print(
        f"Post fluid+remainder RMS:   {result['post_fluid_plus_bridge_remainder_rms']:.3f} s"
        "  [identity check]"
    )
    print()
    print(
        f"{'Year':>6} {'fluid':>10} {'bridge':>10} {'remainder':>11} "
        f"{'post fluid':>11} {'post bridge':>12}"
    )
    print("-" * 70)
    for row in result["sample_rows"]:
        print(
            f"{row['year']:6.1f} {row['fluid']:10.3f} {row['bridge']:10.3f} "
            f"{row['bridge_remainder']:11.3f} {row['post_fluid']:11.3f} {row['post_bridge']:12.3f}"
        )


def _print_table_8(result: dict[str, object] | None) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 8 - Lagged fluid + core vs measured-era bridge")
    print("=" * 70)
    if result is None:
        print("Lagged fluid + core comparison unavailable.")
        return

    y0, y1 = result["years"]
    print(f"Overlap years: {y0:.1f}–{y1:.1f}")
    print(f"Lag applied to AAM/OAM: {result['lag_years']:.1f} years")
    print(f"AAM scale alpha:        {result['alpha']:.6e}")
    print(f"OAM scale beta:         {result['beta']:.6e}")
    print(f"Core scale gamma:       {result['gamma_core']:.6e}")
    print(f"Bridge RMS:             {result['bridge_rms']:.3f} s")
    print(f"Unexplained RMS:        {result['unexplained_rms']:.3f} s")
    print()
    print(f"{'Year':>6} {'bridge':>10} {'fit':>10} {'resid':>10} {'core':>9}")
    print("-" * 54)
    for row in result["sample_rows"]:
        print(
            f"{row['year']:6.1f} {row['bridge']:10.3f} {row['fit']:10.3f} "
            f"{row['residual']:10.3f} {row['core']:9.3f}"
        )


def _print_table_9(result: dict[str, object] | None) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 9 - Envelope search for fluid proxy formulation")
    print("=" * 70)
    if result is None:
        print("Envelope search unavailable.")
        return

    y0, y1 = result["years"]
    print(f"Best overlap years: {y0:.1f}–{y1:.1f}")
    print(f"Best AAM lag:       {result['aam_lag']:.1f} years")
    print(f"Best OAM lag:       {result['oam_lag']:.1f} years")
    print(f"Include core:       {result['include_core']}")
    print(f"Bridge RMS:         {result['bridge_rms']:.3f} s")
    print(f"Unexplained RMS:    {result['unexplained_rms']:.3f} s")
    coeffs = result["coefficients"]
    if result["include_core"]:
        print(f"Coefficients:       AAM={coeffs[0]:.6e}, OAM={coeffs[1]:.6e}, CORE={coeffs[2]:.6e}")
    else:
        print(f"Coefficients:       AAM={coeffs[0]:.6e}, OAM={coeffs[1]:.6e}")
    print()
    print(f"{'Year':>6} {'bridge':>10} {'fit':>10} {'resid':>10}")
    print("-" * 42)
    for row in result["sample_rows"]:
        print(f"{row['year']:6.1f} {row['bridge']:10.3f} {row['fit']:10.3f} {row['residual']:10.3f}")


def _print_table_10(result: dict[str, float] | None) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 10 - Core construction audit")
    print("=" * 70)
    if result is None:
        print("Core construction audit unavailable.")
        return
    print(f"Current core RMS:              {result['current_core_rms']:.3f} s")
    print(f"Current core max |value|:      {result['current_core_max_abs']:.3f} s")
    print(f"No-mean core RMS:              {result['no_mean_core_rms']:.3f} s")
    print(f"No-mean core max |value|:      {result['no_mean_core_max_abs']:.3f} s")
    print(f"End-anchored core RMS:         {result['end_anchored_core_rms']:.3f} s")
    print(f"End-anchored core max |value|: {result['end_anchored_core_max_abs']:.3f} s")
    print(f"Bridge RMS over same era:      {result['bridge_rms']:.3f} s")
    print(f"Bridge max |value|:            {result['bridge_max_abs']:.3f} s")


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _plot(
    rows_1: list[tuple[float, float, float, float]],
    rows_2: list[tuple[float, float, float, float, float]],
    arcsec_data: dict[str, list[tuple[float, float]]],
    rows_4: list[dict[str, float]],
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not available — skipping plots)")
        return

    fig, axes = plt.subplots(4, 1, figsize=(13, 18))

    # — Plot 1: measured era
    ax = axes[0]
    years_1 = [r[0] for r in rows_1]
    current_vals = [r[1] for r in rows_1]
    hybrid_vals = [r[2] for r in rows_1]
    diffs_1 = [r[3] for r in rows_1]
    ax2 = ax.twinx()
    ax.plot(years_1, current_vals, label="current delta_t()", lw=1.5, color="C0")
    ax.plot(years_1, hybrid_vals, label="delta_t_hybrid()", lw=1.5, linestyle="--", color="C1")
    ax2.plot(years_1, diffs_1, label="diff (hybrid − current)", lw=1.0, color="C2", alpha=0.7)
    ax2.axhline(0, color="k", lw=0.6, linestyle=":")
    ax.set_ylabel("DeltaT (s)")
    ax2.set_ylabel("diff (s)", color="C2")
    ax.set_title("Comparison 1 - Hybrid vs current delta_t()  [1962.5-2024.5 annual means]")
    ax.legend(loc="upper left")
    ax2.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    # — Plot 2: future
    ax = axes[1]
    years_2 = [r[0] for r in rows_2]
    table_vals = [r[1] for r in rows_2]
    hyb_vals = [r[2] for r in rows_2]
    sigmas = [r[4] for r in rows_2]
    hyb_arr = hyb_vals
    sig_arr = sigmas
    ax.plot(years_2, table_vals, label="conventional forecast", lw=1.5, color="C0")
    ax.plot(years_2, hyb_arr, label="delta_t_hybrid()", lw=1.5, linestyle="--", color="C1")
    ax.fill_between(
        years_2,
        [h - s for h, s in zip(hyb_arr, sig_arr)],
        [h + s for h, s in zip(hyb_arr, sig_arr)],
        alpha=0.25, color="C1", label="hybrid +-1s"
    )
    ax.set_ylabel("DeltaT (s)")
    ax.set_title("Comparison 2 - Hybrid vs conventional forecast  [2026-2100]")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # — Plot 3: arcseconds
    ax = axes[2]
    highlight = ["Moon", "Sun", "Mercury", "Mars", "Jupiter"]
    for body in highlight:
        series = arcsec_data[body]
        ax.plot([r[0] for r in series], [r[1] for r in series], label=body, lw=1.5)
    ax.axhline(0.75, color="r", lw=0.8, linestyle="--", label="0.75 arcsec Horizons threshold")
    ax.set_ylabel("Apparent position diff (arcsec)")
    ax.set_xlabel("Year")
    ax.set_title("Comparison 3 - Apparent-position impact (hybrid - forecast)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # — Plot 4: residual budget
    ax = axes[3]
    years_4 = [row["year"] for row in rows_4]
    ax.plot(years_4, [row["secular_only_residual"] for row in rows_4], label="measured - secular", lw=1.2)
    ax.plot(years_4, [row["secular_bridge_residual"] for row in rows_4], label="measured - (secular + bridge)", lw=1.2)
    ax.plot(years_4, [row["secular_core_residual"] for row in rows_4], label="measured - (secular + bridge + core)", lw=1.2)
    ax.plot(years_4, [row["secular_core_cryo_residual"] for row in rows_4], label="measured - (secular + bridge + core + cryo)", lw=1.2)
    ax.plot(years_4, [row["final_model_residual"] for row in rows_4], label="measured - final hybrid", lw=1.4, linestyle="--")
    ax.axhline(0, color="k", lw=0.6, linestyle=":")
    ax.set_ylabel("Residual (s)")
    ax.set_xlabel("Year")
    ax.set_title("Comparison 4 - Residual budget by layer")
    ax.legend(ncol=2)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = _REPO_ROOT / "validate_delta_t_comparison.png"
    plt.savefig(out, dpi=130)
    print(f"\nPlot saved to {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("Running Delta T hybrid comparison study...")

    fit = _fitted_residual_spline()
    print(f"  Residual spline: {'fitted' if fit.spline is not None else 'NOT fitted'}")
    print(f"  CV RMS:          {fit.cv_rms:.4f} s")
    print(f"  In-sample RMS:   {fit.in_sample_rms:.4f} s")
    print(f"  Knot count:      {fit.knot_count}")

    rows_1 = comparison_1_measured_era()
    rows_2 = comparison_2_future()
    arcsec_data = comparison_3_arcsec(rows_2)
    rows_4 = comparison_4_residual_budget()
    aam_bridge = comparison_5_aam_bridge_overlap()
    aam_oam_bridge = comparison_6_aam_oam_bridge_overlap()
    fluid_budget = comparison_7_fluid_replacement_budget()
    lagged_fluid_core = comparison_8_lagged_fluid_plus_core_bridge_overlap()
    envelope = comparison_9_envelope_search()
    core_audit = comparison_10_core_construction_audit()

    _print_table_1(rows_1)
    _print_table_2(rows_2)
    _print_table_3(arcsec_data)
    _print_table_4(rows_4)
    _print_table_5(aam_bridge)
    _print_table_6(aam_oam_bridge)
    _print_table_7(fluid_budget)
    _print_table_8(lagged_fluid_core)
    _print_table_9(envelope)
    _print_table_10(core_audit)

    _plot(rows_1, rows_2, arcsec_data, rows_4)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    diffs_1 = [abs(r[3]) for r in rows_1]
    rms_1 = math.sqrt(sum(d * d for d in diffs_1) / len(diffs_1))
    print(f"  Measured annual-mean era (1962.5-2024.5):")
    print(f"    RMS  |hybrid - current| = {rms_1:.3f} s")
    print(f"    Max  |hybrid - current| = {max(diffs_1):.3f} s")

    diffs_2 = [abs(r[3]) for r in rows_2]
    print(f"\n  Future era (2026-2100):")
    print(f"    Max  |hybrid - forecast|  = {max(diffs_2):.3f} s")
    print(f"    Hybrid +-1s at 2100        = {rows_2[-1][4]:.3f} s")

    moon_2100 = dict(arcsec_data["Moon"])[2100.0]
    sun_2100  = dict(arcsec_data["Sun"])[2100.0]
    print(f"\n  Apparent-position impact at 2100:")
    print(f"    Moon:  {moon_2100:.2f} arcsec")
    print(f"    Sun:   {sun_2100:.2f} arcsec")
    print(f"    (relative to conventional forecast, not Horizons)")

    final_abs = [abs(row["final_model_residual"]) for row in rows_4]
    post_fluid_abs = [abs(row["secular_fluid_residual"]) for row in rows_4]
    post_bridge_abs = [abs(row["secular_fluid_bridge_residual"]) for row in rows_4]
    post_core_abs = [abs(row["secular_fluid_bridge_core_residual"]) for row in rows_4]
    post_cryo_abs = [abs(row["secular_fluid_bridge_core_cryo_residual"]) for row in rows_4]
    print(f"\n  Residual budget:")
    print(f"    RMS  after secular only        = {_rms([row['secular_only_residual'] for row in rows_4]):.3f} s")
    print(f"    RMS  after secular + fluid     = {_rms([row['secular_fluid_residual'] for row in rows_4]):.3f} s")
    print(f"    RMS  after secular + fluid+bridge      = {_rms([row['secular_fluid_bridge_residual'] for row in rows_4]):.3f} s")
    print(f"    RMS  after secular + fluid+bridge+core = {_rms([row['secular_fluid_bridge_core_residual'] for row in rows_4]):.3f} s")
    print(f"    RMS  after secular + fluid+bridge+core+cryo = {_rms([row['secular_fluid_bridge_core_cryo_residual'] for row in rows_4]):.3f} s")
    print(f"    RMS  after final hybrid        = {_rms([row['final_model_residual'] for row in rows_4]):.3f} s")
    print(f"    Mean |res| post fluid          = {_mean(post_fluid_abs):.3f} s")
    print(f"    Mean |res| post bridge         = {_mean(post_bridge_abs):.3f} s")
    print(f"    Mean |res| post core           = {_mean(post_core_abs):.3f} s")
    print(f"    Mean |res| post core+cryo      = {_mean(post_cryo_abs):.3f} s")
    print(f"    Mean |res| final hybrid        = {_mean(final_abs):.3f} s")

    if aam_bridge is not None:
        print(f"\n  AAM bridge overlap:")
        print(f"    Correlation(proxy, bridge)     = {aam_bridge['corr']:.3f}")
        print(f"    Bridge RMS over overlap        = {aam_bridge['bridge_rms']:.3f} s")
        print(f"    Unexplained RMS after AAM fit  = {aam_bridge['unexplained_rms']:.3f} s")
    if aam_oam_bridge is not None:
        print(f"\n  AAM + OAM bridge overlap:")
        print(f"    Bridge RMS over overlap        = {aam_oam_bridge['bridge_rms']:.3f} s")
        print(f"    Unexplained RMS after fit      = {aam_oam_bridge['unexplained_rms']:.3f} s")
    if fluid_budget is not None:
        print(f"\n  Fluid replacement budget:")
        print(f"    Fluid-term RMS                 = {fluid_budget['fluid_rms']:.3f} s")
        print(f"    Bridge remainder RMS           = {fluid_budget['bridge_remainder_rms']:.3f} s")
        print(f"    Post-fluid RMS                 = {fluid_budget['post_fluid_rms']:.3f} s")
        print(f"    Post-bridge RMS                = {fluid_budget['post_bridge_rms']:.3f} s")
    if lagged_fluid_core is not None:
        print(f"\n  Lagged fluid + core overlap:")
        print(f"    Lagged fit unexplained RMS     = {lagged_fluid_core['unexplained_rms']:.3f} s")
        print(f"    Core scale gamma               = {lagged_fluid_core['gamma_core']:.3f}")
    if envelope is not None:
        print(f"\n  Envelope search best fit:")
        print(f"    Best unexplained RMS           = {envelope['unexplained_rms']:.3f} s")
        print(f"    Best AAM/OAM lags              = {envelope['aam_lag']:.1f} / {envelope['oam_lag']:.1f} years")
        print(f"    Include core                   = {envelope['include_core']}")
    if core_audit is not None:
        print(f"\n  Core construction audit:")
        print(f"    Current core RMS               = {core_audit['current_core_rms']:.3f} s")
        print(f"    No-mean core RMS               = {core_audit['no_mean_core_rms']:.3f} s")
        print(f"    End-anchored core RMS          = {core_audit['end_anchored_core_rms']:.3f} s")
        print(f"    Bridge RMS                     = {core_audit['bridge_rms']:.3f} s")

    return 0


if __name__ == "__main__":
    sys.exit(main())

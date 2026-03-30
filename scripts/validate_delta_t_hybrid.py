"""
validate_delta_t_hybrid.py — Comparison study: hybrid vs current delta_t vs quadratic.

Three comparisons:
  1. hybrid vs current delta_t()         — 1962.5–2024.5 measured annual-mean era
  2. hybrid future vs current quadratic  — 2026–2100 extrapolation divergence
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
    secular_trend,
    _fitted_residual_spline,
    _residual_at,
)
from moira.julian import delta_t as current_delta_t


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


def _arcsec_from_dt_diff(dt_diff_s: float, deg_per_day: float) -> float:
    deg_per_second = deg_per_day / 86400.0
    return abs(dt_diff_s) * deg_per_second * 3600.0


def _current_quadratic(year: float) -> float:
    t = year - 2026.0
    return 69.3 + 0.04 * t + 0.001 * t * t


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
# Comparison 2: hybrid future vs current quadratic — 2026–2100
# ---------------------------------------------------------------------------

def comparison_2_future() -> list[tuple[float, float, float, float, float]]:
    rows = []
    for y in range(2026, 2101):
        yf = float(y)
        quad = _current_quadratic(yf)
        hyb = delta_t_hybrid(yf)
        sigma = delta_t_hybrid_uncertainty(yf)
        diff = hyb - quad
        rows.append((yf, quad, hyb, diff, sigma))
    return rows


# ---------------------------------------------------------------------------
# Comparison 3: apparent-position impact — dt difference to arcseconds
# ---------------------------------------------------------------------------

def comparison_3_arcsec(
    rows_future: list[tuple[float, float, float, float, float]]
) -> dict[str, list[tuple[float, float]]]:
    result: dict[str, list[tuple[float, float]]] = {body: [] for body in _BODY_DEG_PER_DAY}
    for yf, _quad, _hyb, diff, _sigma in rows_future:
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
            "secular_core_residual": measured - (secular + core),
            "secular_core_cryo_residual": measured - (secular + core + cryo),
            "final_model_residual": measured - (secular + core + cryo + residual),
            "core": core,
            "cryo": cryo,
            "residual_term": residual,
        })
        y += 1.0
    return rows


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
    print("COMPARISON 2 - Hybrid vs current quadratic  [future 2026-2100]")
    print("=" * 70)
    print(f"{'Year':>6}  {'quadratic':>10}  {'hybrid':>10}  {'diff':>10}  {'+-1s':>8}")
    print("-" * 55)
    for y, quad, hyb, diff, sigma in rows[::5]:
        print(f"{y:6.0f}  {quad:10.3f}  {hyb:10.3f}  {diff:+10.3f}  {sigma:8.3f}")
    diffs = [abs(r[3]) for r in rows]
    print("-" * 55)
    print(f"  Max |diff| by 2100: {max(diffs):.3f} s")
    print(f"  Hybrid +-1s at 2100: {rows[-1][4]:.3f} s")
    print(f"  Quadratic at 2100:  {rows[-1][1]:.3f} s")
    print(f"  Hybrid    at 2100:  {rows[-1][2]:.3f} s")


def _print_table_3(arcsec_data: dict[str, list[tuple[float, float]]]) -> None:
    print("\n" + "=" * 70)
    print("COMPARISON 3 - Apparent-position impact of hybrid-quadratic diff")
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
    print("  Note: values are |hybrid - quadratic| converted to apparent arcseconds.")
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
        ("Measured - (secular + core)", "secular_core_residual"),
        ("Measured - (secular + core + cryo)", "secular_core_cryo_residual"),
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
        f"{'Year':>6} {'core':>9} {'cryo':>9} {'resid term':>11} {'post sec':>11} {'post sec+core':>14} {'post sec+core+cryo':>19} {'final':>9}"
    )
    print("-" * 100)
    for row in rows[::5]:
        print(
            f"{row['year']:6.1f} {row['core']:9.3f} {row['cryo']:9.3f} {row['residual_term']:11.3f} "
            f"{row['secular_only_residual']:11.3f} {row['secular_core_residual']:14.3f} "
            f"{row['secular_core_cryo_residual']:19.3f} {row['final_model_residual']:9.3f}"
        )

    print("\nDecadal mean |residual|:")
    decade_series = [
        ("post secular", "secular_only_residual"),
        ("post secular+core", "secular_core_residual"),
        ("post secular+core+cryo", "secular_core_cryo_residual"),
        ("final hybrid", "final_model_residual"),
    ]
    for label, key in decade_series:
        decade_vals = _decadal_mean_abs(rows, key)
        formatted = ", ".join(f"{decade}s={val:.3f}" for decade, val in decade_vals)
        print(f"  {label:<22} {formatted}")


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
    quad_vals = [r[1] for r in rows_2]
    hyb_vals = [r[2] for r in rows_2]
    sigmas = [r[4] for r in rows_2]
    hyb_arr = hyb_vals
    sig_arr = sigmas
    ax.plot(years_2, quad_vals, label="current quadratic", lw=1.5, color="C0")
    ax.plot(years_2, hyb_arr, label="delta_t_hybrid()", lw=1.5, linestyle="--", color="C1")
    ax.fill_between(
        years_2,
        [h - s for h, s in zip(hyb_arr, sig_arr)],
        [h + s for h, s in zip(hyb_arr, sig_arr)],
        alpha=0.25, color="C1", label="hybrid +-1s"
    )
    ax.set_ylabel("DeltaT (s)")
    ax.set_title("Comparison 2 - Hybrid vs current quadratic  [2026-2100]")
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
    ax.set_title("Comparison 3 - Apparent-position impact (hybrid - quadratic)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # — Plot 4: residual budget
    ax = axes[3]
    years_4 = [row["year"] for row in rows_4]
    ax.plot(years_4, [row["secular_only_residual"] for row in rows_4], label="measured - secular", lw=1.2)
    ax.plot(years_4, [row["secular_core_residual"] for row in rows_4], label="measured - (secular + core)", lw=1.2)
    ax.plot(years_4, [row["secular_core_cryo_residual"] for row in rows_4], label="measured - (secular + core + cryo)", lw=1.2)
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

    _print_table_1(rows_1)
    _print_table_2(rows_2)
    _print_table_3(arcsec_data)
    _print_table_4(rows_4)

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
    print(f"    Max  |hybrid - quadratic| = {max(diffs_2):.3f} s  (at 2100)")
    print(f"    Hybrid +-1s at 2100        = {rows_2[-1][4]:.3f} s")

    moon_2100 = dict(arcsec_data["Moon"])[2100.0]
    sun_2100  = dict(arcsec_data["Sun"])[2100.0]
    print(f"\n  Apparent-position impact at 2100:")
    print(f"    Moon:  {moon_2100:.2f} arcsec")
    print(f"    Sun:   {sun_2100:.2f} arcsec")
    print(f"    (relative to current quadratic, not Horizons)")

    final_abs = [abs(row["final_model_residual"]) for row in rows_4]
    post_core_abs = [abs(row["secular_core_residual"]) for row in rows_4]
    post_cryo_abs = [abs(row["secular_core_cryo_residual"]) for row in rows_4]
    print(f"\n  Residual budget:")
    print(f"    RMS  after secular only        = {_rms([row['secular_only_residual'] for row in rows_4]):.3f} s")
    print(f"    RMS  after secular + core      = {_rms([row['secular_core_residual'] for row in rows_4]):.3f} s")
    print(f"    RMS  after secular + core+cryo = {_rms([row['secular_core_cryo_residual'] for row in rows_4]):.3f} s")
    print(f"    RMS  after final hybrid        = {_rms([row['final_model_residual'] for row in rows_4]):.3f} s")
    print(f"    Mean |res| post core           = {_mean(post_core_abs):.3f} s")
    print(f"    Mean |res| post core+cryo      = {_mean(post_cryo_abs):.3f} s")
    print(f"    Mean |res| final hybrid        = {_mean(final_abs):.3f} s")

    return 0


if __name__ == "__main__":
    sys.exit(main())

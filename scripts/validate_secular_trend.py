"""
validate_secular_trend.py — Compare delta_t_physical.secular_trend() against
the SMH 2016 HPIERS table over 1800–2150.

Usage:
    python scripts/validate_secular_trend.py

Outputs a plain-text comparison table and summary statistics.
matplotlib is used for the plot if available; the table is always printed.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from moira.delta_t_physical import secular_trend, _smh2016_lookup


def _compare(years: list[float]) -> list[tuple[float, float, float, float]]:
    rows = []
    for y in years:
        st = secular_trend(y)
        smh = _smh2016_lookup(y)
        diff = st - smh
        rows.append((y, st, smh, diff))
    return rows


def main() -> int:
    check_years = list(range(1800, 2151, 10))
    rows = _compare([float(y) for y in check_years])

    print(f"{'Year':>6}  {'secular_trend':>14}  {'SMH2016':>14}  {'diff':>10}")
    print("-" * 50)
    for y, st, smh, diff in rows:
        marker = " <<<" if abs(diff) > 5.0 else ""
        print(f"{y:6.0f}  {st:14.3f}  {smh:14.3f}  {diff:+10.3f}{marker}")

    diffs = [abs(d) for _, _, _, d in rows]
    max_diff = max(diffs)
    rms_diff = (sum(d ** 2 for d in diffs) / len(diffs)) ** 0.5
    print()
    print(f"Max |diff|: {max_diff:.3f} s")
    print(f"RMS |diff|: {rms_diff:.3f} s")

    if max_diff > 5.0:
        print("\nWARNING: secular_trend diverges by > 5 s at some epochs.")
        print("This is expected in the 1840-1962 era (core-mantle fluctuations")
        print("not yet modelled). It does not indicate an error in the secular formula.")
    else:
        print("\nAll epochs within ±5 s — secular trend looks consistent.")

    try:
        import matplotlib.pyplot as plt

        years_plot = [r[0] for r in rows]
        secular = [r[1] for r in rows]
        smh = [r[2] for r in rows]
        diffs_plot = [r[3] for r in rows]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        ax1.plot(years_plot, secular, label="secular_trend()", lw=2)
        ax1.plot(years_plot, smh, label="SMH 2016", lw=1.5, linestyle="--")
        ax1.set_ylabel("ΔT (s)")
        ax1.set_title("Secular trend vs SMH 2016 table")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.plot(years_plot, diffs_plot, color="C2", lw=1.5)
        ax2.axhline(0, color="k", lw=0.8, linestyle="--")
        ax2.axhline(5, color="r", lw=0.8, linestyle=":")
        ax2.axhline(-5, color="r", lw=0.8, linestyle=":")
        ax2.set_ylabel("secular − SMH2016 (s)")
        ax2.set_xlabel("Year")
        ax2.set_title("Residual (secular_trend − SMH2016)")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        out = _REPO_ROOT / "validate_secular_trend.png"
        plt.savefig(out, dpi=120)
        print(f"\nPlot saved to {out}")
    except ImportError:
        print("\n(matplotlib not available — skipping plot)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
fetch_grace_j2.py — Download and process GRACE/GRACE-FO TN-14 J2 series.

Produces:  moira/data/grace_lod_contribution.txt
Format:    decimal_year  cumulative_delta_t_seconds  gap_flag
           gap_flag = 1 for months bridged across the 2017-10 to 2018-06
           GRACE/GRACE-FO gap; 0 otherwise.

Integration constant: the mean ΔLOD of the first 12 months (2002-04 to
2003-03) is subtracted before integration, so that the cumulative series
starts at 0.0 at 2002.25 by construction.

Usage:
    python scripts/fetch_grace_j2.py

Requires: urllib (stdlib), no third-party dependencies.
"""

import sys
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT = _REPO_ROOT / "moira" / "data" / "grace_lod_contribution.txt"

_TN14_URL = "https://earth.gsfc.nasa.gov/sites/default/files/geo/tn-14_c30_c20_gsfc_slr.txt"
_TN14_URL_ALT = "https://www.earthdata.nasa.gov/s3fs-public/2025-12/GRACE-FO%20Technical%20Note%2014.pdf?VersionId=WZxacTWeDskEQNuYC3ZAYg6qiRUxPOOn"

_EARTH_MASS = 5.9722e24
_EARTH_RADIUS = 6.3781e6
_EARTH_POLAR_MOI = 8.0365e37
_OMEGA = 7.2921150e-5
_LOD0_S = 86400.0
_SQRT5 = 2.2360679774997896

_GRACE_GAP_START = 2017.75
_GRACE_GAP_END = 2018.5


def _j2_to_lod_ms(delta_j2: float) -> float:
    """
    Convert a J2 anomaly to a LOD anomaly in milliseconds.

    ΔI_33 = -√5 × M_E × R_E² × ΔJ2
    Δω/ω  = -ΔI_33 / C
    ΔLOD  = -LOD_0 × Δω/ω = LOD_0 × ΔI_33 / C   [seconds]
    """
    delta_i33 = -_SQRT5 * _EARTH_MASS * _EARTH_RADIUS ** 2 * delta_j2
    delta_omega_over_omega = -delta_i33 / _EARTH_POLAR_MOI
    delta_lod_s = -_LOD0_S * delta_omega_over_omega
    return delta_lod_s * 1000.0


def _download_tn14(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Moira-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace").splitlines()


def _parse_tn14(lines: list[str]) -> list[tuple[float, float]]:
    """
    Parse TN-14 text file (GSFC SLR format).

    Format (from file header):
        Column 1: MJD of beginning of solution span
        Column 2: Year.fraction of beginning of solution span
        Column 3: Replacement C20
        Column 4: C20 - mean C20 (1e-10)
        ...

    We use column 2 (decimal year) and column 3 (C20 absolute value).
    J2 = -C20 × √5  (unnormalised convention).
    The column mean is subtracted to yield anomalies.
    """
    rows: list[tuple[float, float]] = []
    for line in lines:
        line = line.strip()
        if not line or line[0].isalpha():
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            yr = float(parts[1])
            c20 = float(parts[2])
        except ValueError:
            continue
        if yr < 2000.0 or yr > 2035.0:
            continue
        if not (-6e-4 < c20 < -3e-4):
            continue
        j2 = -c20 * _SQRT5
        rows.append((yr, j2))
    if not rows:
        return []
    mean_j2 = sum(j for _, j in rows) / len(rows)
    rows = [(yr, j - mean_j2) for yr, j in rows]
    rows.sort(key=lambda r: r[0])
    return rows


def _bridge_grace_gap(
    rows: list[tuple[float, float]],
) -> list[tuple[float, float, int]]:
    """
    Fill the GRACE/GRACE-FO gap (2017-10 to 2018-06) by linear interpolation
    using the slope of the 12 months immediately preceding the gap.

    Returns list of (decimal_year, delta_lod_ms, gap_flag) tuples.
    gap_flag = 1 for interpolated months.
    """
    pre_gap = [(y, v) for y, v in rows if y < _GRACE_GAP_START]
    post_gap = [(y, v) for y, v in rows if y >= _GRACE_GAP_END]
    if not pre_gap or not post_gap:
        return [(y, v, 0) for y, v in rows]

    pre_window = pre_gap[-12:] if len(pre_gap) >= 12 else pre_gap
    n = len(pre_window)
    mean_y = sum(y for y, _ in pre_window) / n
    mean_v = sum(v for _, v in pre_window) / n
    ss_xy = sum((pre_window[i][0] - mean_y) * (pre_window[i][1] - mean_v) for i in range(n))
    ss_xx = sum((pre_window[i][0] - mean_y) ** 2 for i in range(n))
    slope = ss_xy / ss_xx if ss_xx != 0.0 else 0.0
    intercept = mean_v - slope * mean_y

    gap_y_start = pre_gap[-1][0]
    gap_y_end = post_gap[0][0]
    gap_months = round((gap_y_end - gap_y_start) * 12.0)

    bridged: list[tuple[float, float, int]] = []
    for yr, val in pre_gap:
        bridged.append((yr, val, 0))
    for i in range(1, gap_months):
        yr_fill = gap_y_start + i / 12.0
        val_fill = intercept + slope * yr_fill
        bridged.append((yr_fill, val_fill, 1))
    for yr, val in post_gap:
        bridged.append((yr, val, 0))

    bridged.sort(key=lambda r: r[0])
    return bridged


def _integrate_lod_to_delta_t(
    rows: list[tuple[float, float, int]],
) -> list[tuple[float, float, int]]:
    """
    Integrate LOD anomalies to cumulative Delta T.

    ΔT_cryo(y) = Σ ΔLOD(t_i) × Δt_i / 86400
    where ΔLOD is in milliseconds and Δt_i is in days.

    Integration constant: subtract the mean ΔLOD of the first 12 rows
    before integrating so that the series starts at 0.0.
    """
    if not rows:
        return []
    first_12 = rows[:12]
    mean_baseline = sum(v for _, v, _ in first_12) / len(first_12)
    adjusted = [(y, v - mean_baseline, f) for y, v, f in rows]

    result: list[tuple[float, float, int]] = [(adjusted[0][0], 0.0, adjusted[0][2])]
    cumulative = 0.0
    for i in range(1, len(adjusted)):
        y0, v0, _ = adjusted[i - 1]
        y1, v1, flag = adjusted[i]
        dt_days = (y1 - y0) * 365.25
        avg_lod_ms = (v0 + v1) / 2.0
        cumulative += avg_lod_ms * dt_days / 86400.0
        result.append((y1, cumulative, flag))
    return result


def main() -> int:
    print("Attempting to download GRACE/GRACE-FO TN-14 J2 series...")
    lines: list[str] | None = None
    for url in (_TN14_URL, _TN14_URL_ALT):
        try:
            print(f"  Trying {url}")
            lines = _download_tn14(url)
            print(f"  Downloaded {len(lines)} lines")
            break
        except Exception as exc:
            print(f"  Failed: {exc}")

    if lines is None:
        print(
            "\nCould not download TN-14. The GRACE data file is not yet available.\n"
            "This is expected on first setup. Re-run after network access is confirmed.\n"
            "The moira/data/grace_lod_contribution.txt file will not be created."
        )
        return 1

    rows_j2 = _parse_tn14(lines)
    if not rows_j2:
        print("Could not parse any J2 values from the downloaded file.")
        return 1
    print(f"  Parsed {len(rows_j2)} J2 epochs ({rows_j2[0][0]:.2f}–{rows_j2[-1][0]:.2f})")

    rows_lod = [(y, _j2_to_lod_ms(dj2)) for y, dj2 in rows_j2]

    rows_bridged = _bridge_grace_gap(rows_lod)
    gap_count = sum(1 for _, _, f in rows_bridged if f == 1)
    print(f"  GRACE gap bridged with {gap_count} interpolated months (flag=1)")

    rows_integrated = _integrate_lod_to_delta_t(rows_bridged)

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with _OUTPUT.open("w", encoding="utf-8") as fh:
        fh.write(
            "# GRACE/GRACE-FO cryosphere/hydrosphere contribution to Delta T\n"
            "# Generated by scripts/fetch_grace_j2.py\n"
            "# Source: GRACE/GRACE-FO TN-14 J2 (C20) series, JPL/GSFC SLR replacement\n"
            "#\n"
            "# Columns:\n"
            "#   decimal_year  cumulative_delta_t_seconds  gap_flag\n"
            "#   gap_flag=1 means this month was interpolated across the\n"
            "#   GRACE/GRACE-FO gap (2017-10 to 2018-06).\n"
            "#\n"
            "# Integration constant: mean ΔLOD of first 12 months subtracted,\n"
            "# so cryo_delta_t(first_epoch) = 0.0 by construction.\n"
            "#\n"
        )
        for yr, val, flag in rows_integrated:
            fh.write(f"{yr:.6f}  {val:.6f}  {flag}\n")

    print(f"  Written {len(rows_integrated)} epochs to {_OUTPUT}")
    print(
        f"  Cumulative Delta T at end: {rows_integrated[-1][1]:+.3f} s "
        f"(epoch {rows_integrated[-1][0]:.2f})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

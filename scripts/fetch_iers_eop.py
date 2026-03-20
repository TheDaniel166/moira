"""
fetch_iers_eop.py — Download IERS EOP C04 (1962–present) and extract the
LOD column as an annual mean series for use as the core angular momentum
proxy in moira/data/core_angular_momentum.txt.

Physical basis
--------------
The IERS EOP C04 LOD series is the observed length-of-day anomaly in
milliseconds.  After removing the known tidal contribution (which is already
captured by secular_trend) and the atmospheric/oceanic angular momentum (AAM/
OAM) signal (which is captured by the residual spline), the residual LOD
signal is dominated by core-mantle angular momentum exchange on decadal
timescales — exactly the core_delta_t component we need.

For the 1962–present era we use the raw annual-mean LOD anomaly as a proxy
for core angular momentum rather than a model-derived reconstruction.  This
is a deliberate simplification: the raw series includes AAM/OAM contamination
at the 0.3–0.5 ms level, but because the residual spline is fit to
IERS_measured − (secular + core + cryo), that AAM/OAM signal will be absorbed
by the residual spline rather than double-counted.  The core component
therefore contributes the decadal-scale signal; the residual captures the
interannual noise.  This is fully consistent with the era coverage table in
DELTA_T_HYBRID_MODEL.md.

For 1840–1962 this file produces no data (returns the series starting at
1962.0).  The Gillet et al. model reconstruction for 1840–1962 can be appended
manually when it becomes available; the loader in delta_t_physical.py will
merge the two without code changes.

Output format
-------------
moira/data/core_angular_momentum.txt
    decimal_year  delta_lod_ms
    # annual means of EOP C04 LOD column (ms), 1962–present

Usage
-----
    python scripts/fetch_iers_eop.py

No third-party dependencies required.
"""

import sys
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT = _REPO_ROOT / "moira" / "data" / "core_angular_momentum.txt"

_EOP_C04_URL = (
    "https://datacenter.iers.org/products/eop/long-term/"
    "c04_operational/csv/eopc04.1962-now.csv"
)

_MJD_J2000 = 51544.5
_DAYS_PER_YEAR = 365.25


def _mjd_to_decimal_year(mjd: float) -> float:
    j2000_years = (mjd - _MJD_J2000) / _DAYS_PER_YEAR
    return 2000.0 + j2000_years


def _download(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Moira-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace").splitlines()


def _parse_eop_c04(lines: list[str]) -> list[tuple[float, float]]:
    """
    Parse EOP C04 CSV.

    Format (semicolon-delimited, confirmed from IERS):
        MJD ; Year ; Month ; Day ; [type] ; x_pole ; ... ; LOD ; sigma_LOD ; ...

    LOD is in milliseconds.  Missing or flagged values appear as empty strings.
    We keep only rows where LOD is a valid float.
    """
    header = lines[0].split(";")
    try:
        mjd_col = header.index("MJD")
        lod_col = header.index("LOD")
    except ValueError:
        mjd_col = 0
        lod_col = 16

    rows: list[tuple[float, float]] = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(";")
        if len(parts) <= max(mjd_col, lod_col):
            continue
        try:
            mjd = float(parts[mjd_col])
            lod_s = float(parts[lod_col])
        except ValueError:
            continue
        decimal_year = _mjd_to_decimal_year(mjd)
        rows.append((decimal_year, lod_s * 1000.0))
    rows.sort(key=lambda r: r[0])
    return rows


def _annual_means(
    rows: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """
    Compute calendar-year annual means from a daily LOD series.

    Returns one (decimal_year, mean_lod_ms) per year where decimal_year
    is the mid-year value (year + 0.5).
    """
    by_year: dict[int, list[float]] = {}
    for yr_decimal, lod in rows:
        yr_int = int(yr_decimal)
        by_year.setdefault(yr_int, []).append(lod)

    result: list[tuple[float, float]] = []
    for yr_int in sorted(by_year):
        vals = by_year[yr_int]
        if len(vals) < 30:
            continue
        mean_lod = sum(vals) / len(vals)
        result.append((yr_int + 0.5, mean_lod))
    return result


def main() -> int:
    print("Downloading IERS EOP C04 (1962–present)...")
    print(f"  URL: {_EOP_C04_URL}")
    try:
        lines = _download(_EOP_C04_URL)
    except Exception as exc:
        print(f"  Failed: {exc}")
        return 1

    print(f"  Downloaded {len(lines)} rows")

    daily = _parse_eop_c04(lines)
    if not daily:
        print("  Could not parse any LOD values.")
        return 1

    print(
        f"  Parsed {len(daily)} daily LOD values "
        f"({daily[0][0]:.2f}–{daily[-1][0]:.2f})"
    )

    annual = _annual_means(daily)
    if not annual:
        print("  Could not compute annual means.")
        return 1

    print(f"  Computed {len(annual)} annual means ({annual[0][0]:.1f}–{annual[-1][0]:.1f})")

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with _OUTPUT.open("w", encoding="utf-8") as fh:
        fh.write(
            "# Core angular momentum proxy — annual-mean LOD anomaly\n"
            "# Source: IERS EOP C04 (1962–present), annual means\n"
            "# URL: https://datacenter.iers.org/products/eop/long-term/"
            "c04_operational/csv/eopc04.1962-now.csv\n"
            "#\n"
            "# Physical interpretation:\n"
            "#   Annual-mean LOD anomaly in milliseconds.  On decadal timescales\n"
            "#   this is dominated by core-mantle angular momentum exchange.\n"
            "#   AAM/OAM contamination (~0.3-0.5 ms) is absorbed by the residual\n"
            "#   spline in delta_t_physical.py (see DELTA_T_HYBRID_MODEL.md).\n"
            "#\n"
            "# For 1840-1962: Gillet et al. model reconstruction (not yet available).\n"
            "# When obtained, prepend those rows to this file.\n"
            "#\n"
            "# Columns: decimal_year  delta_lod_ms\n"
            "#   decimal_year = calendar year + 0.5 (mid-year)\n"
            "#   delta_lod_ms = annual mean LOD in milliseconds\n"
            "#\n"
        )
        for yr, lod in annual:
            fh.write(f"{yr:.1f}  {lod:.4f}\n")

    print(f"  Written to {_OUTPUT}")
    print(f"  LOD range: {min(v for _, v in annual):.3f} to {max(v for _, v in annual):.3f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())

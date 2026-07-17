"""
fetch_iers_eop.py — quarantined IERS EOP C04 total-LOD research generator.

The source LOD column is a total Earth-rotation product.  Annual averaging
does not identify a core-angular-momentum contribution, and this script does
not remove atmospheric, oceanic, mantle, or cryospheric terms.  Its historical
output filename is retained for audit compatibility only; the generated data
is not admitted by ``delta_t_physical``.

Output format
-------------
moira/data/core_angular_momentum.txt
    decimal_year  delta_lod_ms
    # annual means of EOP C04 LOD (source seconds, output milliseconds)

Usage
-----
    python scripts/archive/one_shot_debug_and_diagnostics/fetch_iers_eop.py \
        --quarantined-research-output

No third-party dependencies required.
"""

import math
import sys
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_OUTPUT = _REPO_ROOT / "moira" / "data" / "core_angular_momentum.txt"

_EOP_C04_URL = (
    "https://datacenter.iers.org/products/eop/long-term/"
    "c04_operational/csv/eopc04.1962-now.csv"
)

def _download(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Moira-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace").splitlines()


def _parse_eop_c04(lines: list[str]) -> list[tuple[int, float]]:
    """
    Parse EOP C04 CSV.

    Format (semicolon-delimited, confirmed from IERS):
        MJD ; Year ; Month ; Day ; [type] ; x_pole ; ... ; LOD ; sigma_LOD ; ...

    The source ``LOD`` column is in seconds.  Output values are converted to
    milliseconds.  Calendar grouping uses the source ``Year`` column rather
    than deriving an approximate year from MJD.  Missing or flagged values
    appear as empty strings; only finite numeric rows are retained.
    """
    if not lines:
        return []
    header = [field.strip().lstrip("\ufeff") for field in lines[0].split(";")]
    columns = {name.casefold(): index for index, name in enumerate(header)}
    try:
        year_col = columns["year"]
        lod_col = columns["lod"]
    except KeyError as exc:
        raise ValueError("IERS EOP C04 CSV requires named Year and LOD columns") from exc

    rows: list[tuple[int, float]] = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(";")
        if len(parts) <= max(year_col, lod_col):
            continue
        try:
            year_value = float(parts[year_col].strip())
            lod_seconds = float(parts[lod_col].strip())
        except ValueError:
            continue
        if (
            not math.isfinite(year_value)
            or not year_value.is_integer()
            or not math.isfinite(lod_seconds)
        ):
            continue
        year = int(year_value)
        rows.append((year, lod_seconds * 1000.0))
    rows.sort(key=lambda r: r[0])
    return rows


def _annual_means(
    rows: list[tuple[int, float]],
) -> list[tuple[float, float]]:
    """
    Compute calendar-year annual means from a daily LOD series.

    Returns one (decimal_year, mean_lod_ms) per year where decimal_year
    is the mid-year value (year + 0.5).
    """
    by_year: dict[int, list[float]] = {}
    for source_year, lod_ms in rows:
        by_year.setdefault(source_year, []).append(lod_ms)

    result: list[tuple[float, float]] = []
    for yr_int in sorted(by_year):
        vals = by_year[yr_int]
        if len(vals) < 30:
            continue
        mean_lod = sum(vals) / len(vals)
        result.append((yr_int + 0.5, mean_lod))
    return result


def main() -> int:
    if "--quarantined-research-output" not in sys.argv[1:]:
        print(
            "Refusing to regenerate a quarantined total-LOD artifact without "
            "--quarantined-research-output. Annual C04 LOD is not a core "
            "angular-momentum inversion."
        )
        return 2

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
        f"({daily[0][0]}–{daily[-1][0]})"
    )

    annual = _annual_means(daily)
    if not annual:
        print("  Could not compute annual means.")
        return 1

    print(f"  Computed {len(annual)} annual means ({annual[0][0]:.1f}–{annual[-1][0]:.1f})")

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with _OUTPUT.open("w", encoding="utf-8") as fh:
        fh.write(
            "# QUARANTINED RESEARCH PROXY — NOT RUNTIME-ADMITTED\n"
            "# Historical filename retained for compatibility\n"
            "# Annual-mean TOTAL LOD; not a core-angular-momentum inversion\n"
            "# Source: IERS EOP C04 (1962–present), annual means\n"
            "# URL: https://datacenter.iers.org/products/eop/long-term/"
            "c04_operational/csv/eopc04.1962-now.csv\n"
            "#\n"
            "# Physical interpretation:\n"
            "#   Source LOD is in seconds and is converted to milliseconds.\n"
            "#   Total annual-mean LOD anomaly. Atmospheric,\n"
            "#   oceanic, mantle, cryospheric, and core effects are not separated.\n"
            "#\n"
            "# Columns: decimal_year  delta_lod_ms\n"
            "#   decimal_year = source Year column + 0.5 (mid-year label)\n"
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

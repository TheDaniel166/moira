"""
fetch_aam_glaam.py — download and annualize NOAA PSL GLAAM monthly series.

Source:
    NOAA Physical Sciences Laboratory monthly GLAAM time series
    https://psl.noaa.gov/data/timeseries/month/GLAAM/

Output:
    moira/data/aam_glaam_annual.txt

This is a diagnostic data pipeline for evaluating whether a low-frequency
atmospheric angular momentum term can explain part of Moira's measured-era
Delta T bridge. It does not alter the production Delta T model.
"""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen


_URL = "https://psl.noaa.gov/data/correlation/glaam.data"
_OUT = Path(__file__).resolve().parent.parent / "moira" / "data" / "aam_glaam_annual.txt"


def _parse_psl_standard(text: str) -> list[tuple[int, list[float]]]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    rows: list[tuple[int, list[float]]] = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 13:
            continue
        year = int(parts[0])
        months = [float(x) for x in parts[1:13]]
        rows.append((year, months))
    return rows


def _annual_means(rows: list[tuple[int, list[float]]]) -> list[tuple[float, float]]:
    annual: list[tuple[float, float]] = []
    for year, months in rows:
        annual.append((year + 0.5, sum(months) / len(months)))
    return annual


def main() -> int:
    print("Downloading NOAA PSL GLAAM monthly series...")
    with urlopen(_URL, timeout=60) as response:
        raw = response.read().decode("utf-8")

    rows = _parse_psl_standard(raw)
    annual = _annual_means(rows)
    if not annual:
        print("No annual GLAAM rows parsed.")
        return 1

    _OUT.write_text(
        "".join(
            [
                "# Atmospheric angular momentum proxy — annual-mean NOAA PSL GLAAM\n",
                "# Source: https://psl.noaa.gov/data/timeseries/month/GLAAM/\n",
                "# Raw file: https://psl.noaa.gov/data/correlation/glaam.data\n",
                "# Temporal coverage: 1958.5–2014.5\n",
                "# Units: AAM (as published by NOAA PSL)\n",
                "# Construction: simple annual mean of the 12 monthly values\n",
                "# Purpose: diagnostic-only low-frequency physical proxy for\n",
                "#          measured-era Delta T bridge analysis.\n",
                "# Columns:\n",
                "#   decimal_year annual_mean_aam\n",
            ]
            + [f"{year:7.1f}  {val:.10e}\n" for year, val in annual]
        ),
        encoding="utf-8",
    )

    vals = [v for _, v in annual]
    print(f"Wrote {_OUT}")
    print(f"Rows: {len(annual)}")
    print(f"Years: {annual[0][0]:.1f}–{annual[-1][0]:.1f}")
    print(f"AAM range: {min(vals):.6e} to {max(vals):.6e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

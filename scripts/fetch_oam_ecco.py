"""
fetch_oam_ecco.py — download and annualize IERS ECCO_50yr oceanic excitation.

Source:
    IERS Datacenter / ECCO_50yr.chi
    https://datacenter.iers.org/data/191/ECCO_50yr.chi

Output:
    moira/data/oam_ecco_annual.txt

Diagnostic-only data pipeline for evaluating whether an explicit oceanic
angular momentum low-frequency term can explain part of Moira's measured-era
Delta T bridge.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys
from urllib.request import urlopen


_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
_OUT = _REPO_ROOT / "moira" / "data" / "oam_ecco_annual.txt"
_URL = "https://datacenter.iers.org/data/191/ECCO_50yr.chi"


def _mjd_to_year(mjd: float) -> int:
    from moira.julian import calendar_from_jd

    year, _month, _day, _hour = calendar_from_jd(mjd + 2400000.5)
    return year


def _parse_ecco_50yr(text: str) -> list[tuple[int, float]]:
    rows: list[tuple[int, float]] = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw or not raw[0].isdigit():
            continue
        parts = raw.split()
        if len(parts) < 7:
            continue
        try:
            mjd = float(parts[0])
            lod_mass_ms = float(parts[3])
            lod_motion_ms = float(parts[6])
        except ValueError:
            continue
        rows.append((_mjd_to_year(mjd), lod_mass_ms + lod_motion_ms))
    return rows


def _annual_means(rows: list[tuple[int, float]]) -> list[tuple[float, float]]:
    buckets: dict[int, list[float]] = defaultdict(list)
    for year, lod_ms in rows:
        buckets[year].append(lod_ms)
    annual = [(year + 0.5, sum(vals) / len(vals)) for year, vals in sorted(buckets.items())]
    return annual


def main() -> int:
    print("Downloading IERS ECCO_50yr ocean excitation series...")
    with urlopen(_URL, timeout=60) as response:
        raw = response.read().decode("utf-8", errors="replace")

    rows = _parse_ecco_50yr(raw)
    annual = _annual_means(rows)
    if not annual:
        print("No annual OAM rows parsed.")
        return 1

    _OUT.write_text(
        "".join(
            [
                "# Ocean angular momentum proxy — annual-mean ECCO_50yr total lod\n",
                "# Source: https://datacenter.iers.org/data/191/ECCO_50yr.chi\n",
                "# Temporal coverage: 1949.5–2002.5\n",
                "# Units: milliseconds of lod (mass + motion terms)\n",
                "# Construction: simple annual mean of 10-day ECCO_50yr total lod values\n",
                "# Purpose: diagnostic-only low-frequency physical proxy for\n",
                "#          measured-era Delta T bridge analysis.\n",
                "# Columns:\n",
                "#   decimal_year annual_mean_oam_lod_ms\n",
            ]
            + [f"{year:7.1f}  {val:.10e}\n" for year, val in annual]
        ),
        encoding="utf-8",
    )

    vals = [v for _, v in annual]
    print(f"Wrote {_OUT}")
    print(f"Rows: {len(annual)}")
    print(f"Years: {annual[0][0]:.1f}–{annual[-1][0]:.1f}")
    print(f"OAM LOD range: {min(vals):.6e} to {max(vals):.6e} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

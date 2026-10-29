"""Build the NASA Five Millennium 1901-2100 eclipse completeness fixture.

usage: build_nasa_eclipse_completeness_fixture.py <5MKSEcatalog.txt> <5MKLEcatalog.txt>
           --retrieved YYYY-MM-DD --output tests/fixtures/<name>.json

The inputs are the official NASA/GSFC ASCII catalogs, downloaded separately
from the URLs recorded below; this script never touches the network. It copies
static catalog facts for every eclipse whose TD date falls in 1901-2100 and
records each source file's byte count and SHA-256, so the fixture can be
regenerated and audited against the same bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOLAR_URL = "https://eclipse.gsfc.nasa.gov/5MCSE/5MKSEcatalog.txt"
LUNAR_URL = "https://eclipse.gsfc.nasa.gov/5MCLE/5MKLEcatalog.txt"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
FIRST_YEAR = 1901
LAST_YEAR = 2100


def _source(path: Path, url: str, publication: str) -> dict:
    data = path.read_bytes()
    return {
        "url": url,
        "publication": publication,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _rows(path: Path, *, solar: bool) -> list[dict]:
    # Solar rows carry a catalog plate column after the catalog number; lunar
    # rows do not. Column meanings follow NASA's published catalog keys.
    offset = 2 if solar else 1
    rows = []
    for line in path.read_text(encoding="latin-1").splitlines():
        columns = line.split()
        if len(columns) < offset + 10 or not columns[0].isdigit():
            continue
        if columns[offset + 1] not in MONTHS:
            continue
        year = int(columns[offset])
        if not FIRST_YEAR <= year <= LAST_YEAR:
            continue
        row = {
            "catalog_number": columns[0],
            "date": f"{year:04d}-{columns[offset + 1]}-{int(columns[offset + 2]):02d}",
            "greatest_td": columns[offset + 3],
            "delta_t_s": int(columns[offset + 4]),
            "type_code": columns[offset + 7],
            "gamma": float(columns[offset + 9]),
        }
        if solar:
            row["magnitude"] = float(columns[offset + 10])
        else:
            row["penumbral_magnitude"] = float(columns[offset + 10])
            row["umbral_magnitude"] = float(columns[offset + 11])
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("solar_catalog", type=Path)
    parser.add_argument("lunar_catalog", type=Path)
    parser.add_argument("--retrieved", required=True, help="retrieval date, YYYY-MM-DD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    solar = _rows(args.solar_catalog, solar=True)
    lunar = _rows(args.lunar_catalog, solar=False)
    fixture = {
        "source": {
            "authority": "NASA/GSFC Five Millennium Catalogs of Solar and Lunar Eclipses",
            "solar": _source(args.solar_catalog, SOLAR_URL, "NASA/TP-2008-214170"),
            "lunar": _source(args.lunar_catalog, LUNAR_URL, "NASA/TP-2009-214173"),
            "retrieved_utc": args.retrieved,
            "span_td_years": [FIRST_YEAR, LAST_YEAR],
            "catalog_time_scale": "TD/TT",
            "catalog_ephemeris": "VSOP87/ELP2000-82",
            "lunar_shadow_enlargement": "Danjon",
            "evidence_class": "primary-authority cross-model completeness corpus",
            "builder": "scripts/build_nasa_eclipse_completeness_fixture.py",
            "note": (
                "Static facts copied from the official ASCII catalogs; no network "
                "access is used by tests. Catalog ephemeris, Delta T, lunar limb "
                "and shadow model differ from Moira's DE441 physical model."
            ),
        },
        "solar": solar,
        "lunar": lunar,
    }
    args.output.write_text(json.dumps(fixture, indent=1) + "\n", encoding="utf-8")
    print(f"solar rows {len(solar)}, lunar rows {len(lunar)} -> {args.output}")


if __name__ == "__main__":
    main()

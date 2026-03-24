"""
download_gaia.py — Download a G < 10 subset of Gaia DR3 and save as a
compact binary catalog for use by moira/gaia.py.

Usage
-----
    py -3 scripts/download_gaia.py
    py -3 scripts/download_gaia.py --mag 8 --out data/gaia_g8.bin
    py -3 scripts/download_gaia.py --mag 10 --out data/gaia_g10.bin --csv

Options
-------
    --mag FLOAT     G-band magnitude limit (default: 10.0)
    --out PATH      Output binary path (default: data/gaia_g10.bin)
    --csv           Also save the raw CSV alongside the binary
    --chunk INT     Download rows per HTTP chunk (default: 100000)

Output binary format (little-endian, no padding)
-------------------------------------------------
Header  : 4 bytes magic b'GAIA'
          4 bytes uint32 — number of records N
Record  : 10 x float32 per star (40 bytes), N records
Fields  : ra, dec, pmra, pmdec, parallax, radial_velocity,
          phot_g_mean_mag, bp_rp, teff_gspphot, parallax_error

Missing / null float values are stored as NaN (IEEE 754).

ESA Gaia Archive TAP endpoint: https://gea.esac.esa.int/tap-server/tap
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


_TAP_URL   = "https://gea.esac.esa.int/tap-server/tap/sync"
_MAGIC     = b"GAIA"
_RECORD_FMT = "<10f"
_RECORD_SIZE = struct.calcsize(_RECORD_FMT)

_ADQL = """\
SELECT ra, dec, pmra, pmdec, parallax, parallax_error,
       radial_velocity, phot_g_mean_mag, bp_rp, teff_gspphot
FROM gaiadr3.gaia_source
WHERE phot_g_mean_mag < {mag}
  AND ra IS NOT NULL
  AND dec IS NOT NULL
  AND parallax IS NOT NULL
"""


def _nan(v: str) -> float:
    v = v.strip()
    if v == "" or v.lower() == "null":
        return math.nan
    return float(v)


def _query_tap(adql: str, fmt: str = "csv") -> bytes:
    params = urllib.parse.urlencode({
        "REQUEST": "doQuery",
        "LANG":    "ADQL",
        "FORMAT":  fmt,
        "QUERY":   adql,
    }).encode("utf-8")

    req = urllib.request.Request(
        _TAP_URL,
        data=params,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    print(f"Querying ESA Gaia TAP... (this may take several minutes)")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = resp.read()
    elapsed = time.time() - t0
    print(f"Downloaded {len(data):,} bytes in {elapsed:.1f}s")
    return data


def _parse_csv(raw: bytes) -> list[tuple[float, ...]]:
    text   = raw.decode("utf-8", errors="replace")
    lines  = text.splitlines()
    if not lines:
        raise ValueError("Empty response from TAP server")

    header = [h.strip() for h in lines[0].split(",")]
    col    = {name: idx for idx, name in enumerate(header)}

    needed = ["ra", "dec", "pmra", "pmdec", "parallax", "parallax_error",
              "radial_velocity", "phot_g_mean_mag", "bp_rp", "teff_gspphot"]
    for n in needed:
        if n not in col:
            raise ValueError(f"Expected column {n!r} not in response header: {header}")

    records: list[tuple[float, ...]] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        try:
            rec = tuple(_nan(parts[col[n]]) for n in needed)
        except (IndexError, ValueError):
            continue
        records.append(rec)

    return records


def _write_binary(records: list[tuple[float, ...]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = len(records)
    with path.open("wb") as fh:
        fh.write(_MAGIC)
        fh.write(struct.pack("<I", n))
        for rec in records:
            fh.write(struct.pack(_RECORD_FMT, *rec))
    size_mb = path.stat().st_size / 1_048_576
    print(f"Wrote {n:,} stars -> {path}  ({size_mb:.1f} MB)")


def _write_csv(raw: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    print(f"Saved raw CSV → {path}  ({len(raw)/1_048_576:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Gaia DR3 subset for Moira")
    parser.add_argument("--mag",   type=float, default=10.0,
                        help="G-band magnitude limit (default 10.0)")
    parser.add_argument("--out",   type=str,   default=None,
                        help="Output binary path (default: data/gaia_g<mag>.bin)")
    parser.add_argument("--csv",   action="store_true",
                        help="Also save raw CSV")
    args = parser.parse_args()

    mag     = args.mag
    mag_str = str(int(mag)) if mag == int(mag) else str(mag)
    out_bin = Path(args.out) if args.out else Path(f"data/gaia_g{mag_str}.bin")
    out_csv = out_bin.with_suffix(".csv")

    adql = _ADQL.format(mag=mag)
    print(f"ADQL query (G < {mag}):")
    print(adql)

    raw = _query_tap(adql, fmt="csv")

    if args.csv:
        _write_csv(raw, out_csv)

    print("Parsing CSV...")
    t0 = time.time()
    records = _parse_csv(raw)
    print(f"Parsed {len(records):,} records in {time.time()-t0:.1f}s")

    _write_binary(records, out_bin)
    print("Done.")


if __name__ == "__main__":
    main()

"""Add explicit astrometric metadata columns to the sovereign star registry.

usage: augment_star_registry_astrometry.py epoch [--registry PATH]

``epoch`` adds ``ref_epoch_jd`` and ``frame`` to every row that lacks them.
Every current row was resolved through astroquery's SIMBAD interface, whose
coordinate output is ICRS at epoch J2000.0, so those rows receive
``2451545.0`` and ``ICRS``. Rows that already carry values are left
unchanged, and existing cell text is written back verbatim.

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Section 3.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[2] / "moira" / "data" / "star_registry.csv"
SIMBAD_EPOCH_JD = "2451545.0"
SIMBAD_FRAME = "ICRS"


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_epoch(path: Path) -> int:
    fieldnames, rows = _read(path)
    for column in ("ref_epoch_jd", "frame"):
        if column not in fieldnames:
            fieldnames.append(column)
    changed = 0
    for row in rows:
        if not (row.get("ref_epoch_jd") or "").strip():
            row["ref_epoch_jd"] = SIMBAD_EPOCH_JD
            changed += 1
        if not (row.get("frame") or "").strip():
            row["frame"] = SIMBAD_FRAME
    _write(path, fieldnames, rows)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["epoch"])
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args()
    if args.step == "epoch":
        print(f"rows given an explicit epoch: {add_epoch(args.registry)}")


if __name__ == "__main__":
    main()

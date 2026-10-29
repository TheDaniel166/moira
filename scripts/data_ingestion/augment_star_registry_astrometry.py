"""Add explicit astrometric metadata to the sovereign star registry.

usage:
  augment_star_registry_astrometry.py epoch
  augment_star_registry_astrometry.py fetch-rv --out CANDIDATE.json     (network)
  augment_star_registry_astrometry.py apply-rv --candidate CANDIDATE.json

``epoch`` adds ``ref_epoch_jd`` and ``frame`` to every row that lacks them.
Every current row was resolved through astroquery's SIMBAD interface, whose
coordinate output is ICRS at epoch J2000.0, so those rows receive
``2451545.0`` and ``ICRS``.

``fetch-rv`` queries the SIMBAD TAP service for each row's recorded SIMBAD
identifier (the one named in ``star_provenance.json``) and writes a candidate
file for review: SIMBAD's adopted radial velocity with its error, quality and
bibliographic reference, the references of the adopted position, proper
motion and parallax, and SIMBAD's current astrometry so the review can see
whether the registry still matches it. Nothing in ``moira/data`` changes.

``apply-rv`` applies a reviewed candidate: it adds ``radial_velocity_km_s``
and ``radial_velocity_status`` to the registry and the per-field sources to
``star_provenance.json``. A velocity is admitted only when SIMBAD reports a
radial velocity (type ``v``) with quality A to D; otherwise the status is
``unknown`` and the value zero. Existing cell text is written back verbatim.

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Section 3.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "moira" / "data"
REGISTRY = DATA / "star_registry.csv"
PROVENANCE = DATA / "star_provenance.json"
SIMBAD_EPOCH_JD = "2451545.0"
SIMBAD_FRAME = "ICRS"
SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
# Official SIMBAD mirror at the Harvard-Smithsonian Center for Astrophysics.
SIMBAD_TAP_MIRROR = "https://simbad.harvard.edu/simbad/sim-tap/sync"
ADMITTED_RV_QUALITY = ("A", "B", "C", "D")
_QUERY = (
    "SELECT i.id, b.main_id, b.rvz_type, b.rvz_radvel, b.rvz_err, b.rvz_qual, b.rvz_bibcode, "
    "b.coo_bibcode, b.pm_bibcode, b.plx_bibcode, b.ra, b.dec, b.pmra, b.pmdec, b.plx_value "
    "FROM ident AS i JOIN basic AS b ON i.oidref = b.oid WHERE i.id IN ({ids})"
)


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


def _simbad_identifier(provenance: dict) -> str:
    match = re.search(r"\(([^()]+)\)\s*$", provenance.get("matching_status", ""))
    if not match:
        raise ValueError(f"no SIMBAD identifier recorded in {provenance!r}")
    return match.group(1).strip()


# SIMBAD stores catalog identifiers in fixed-width form: "HR     3",
# "HD     28". Exact matching needs that spelling.
_SIMBAD_FIXED_WIDTH = {"HR": 6, "HD": 7}


def _simbad_spelling(identifier: str) -> str:
    match = re.fullmatch(r"(HR|HD) (\d+)", identifier)
    if not match:
        return identifier
    catalog, number = match.groups()
    return f"{catalog}{int(number):>{_SIMBAD_FIXED_WIDTH[catalog]}}"


def _tap(ids: list[str], service: str) -> list[dict]:
    quoted = ",".join("'" + i.replace("'", "''") + "'" for i in ids)
    body = urllib.parse.urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": _QUERY.format(ids=quoted),
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(service, data=body), timeout=120) as response:
        payload = json.load(response)
    names = [column["name"] for column in payload["metadata"]]
    return [dict(zip(names, row)) for row in payload["data"]]


def fetch_rv(out: Path, service: str, batch: int = 200) -> None:
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    _, rows = _read(REGISTRY)
    wanted = {row["name"]: _simbad_identifier(provenance[row["name"]]) for row in rows}
    by_id: dict[str, dict] = {}
    spelled = {_simbad_spelling(ident): ident for ident in set(wanted.values())}
    # SIMBAD may answer in its own spelling of the identifier, so results are
    # mapped back on whitespace-normalized text.
    by_normalized = {" ".join(ident.split()): ident for ident in set(wanted.values())}
    ids = sorted(spelled)
    for start in range(0, len(ids), batch):
        for record in _tap(ids[start:start + batch], service):
            original = by_normalized.get(" ".join(record["id"].split()))
            if original is not None:
                by_id[original] = record
        print(f"  queried {min(start + batch, len(ids))}/{len(ids)} identifiers", flush=True)
    # SIMBAD can answer in a spelling of its own ("NAME Pistol Star"). Query
    # each identifier still unresolved on its own, where every answer belongs
    # to that one identifier.
    for ident in sorted(set(wanted.values()) - set(by_id)):
        records = _tap([_simbad_spelling(ident)], service)
        if len({record["main_id"] for record in records}) == 1:
            by_id[ident] = records[0]
    print(f"  resolved {len(by_id)}/{len(ids)} identifiers", flush=True)
    stars, unmatched = {}, []
    for name, ident in wanted.items():
        record = by_id.get(ident)
        if record is None:
            unmatched.append({"name": name, "simbad_id": ident})
            continue
        stars[name] = {"simbad_id": ident, **{k: v for k, v in record.items() if k != "id"}}
    out.write_text(json.dumps({
        "source": {"service": service, "query": _QUERY,
                   "retrieved_utc": datetime.now(timezone.utc).isoformat()},
        "stars": stars, "unmatched": unmatched,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"matched {len(stars)}, unmatched {len(unmatched)} -> {out}")


def _admitted_velocity(record: dict) -> float | None:
    value = record.get("rvz_radvel")
    if record.get("rvz_type") != "v" or value is None or not math.isfinite(float(value)):
        return None
    if (record.get("rvz_qual") or "").strip() not in ADMITTED_RV_QUALITY:
        return None
    return float(value)


def apply_rv(candidate_path: Path) -> None:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    retrieved = candidate["source"]["retrieved_utc"]
    fieldnames, rows = _read(REGISTRY)
    for column in ("radial_velocity_km_s", "radial_velocity_status"):
        if column not in fieldnames:
            fieldnames.append(column)
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    measured = 0
    for row in rows:
        record = candidate["stars"].get(row["name"])
        velocity = _admitted_velocity(record) if record else None
        row["radial_velocity_km_s"] = repr(velocity) if velocity is not None else "0.0"
        row["radial_velocity_status"] = "measured" if velocity is not None else "unknown"
        measured += velocity is not None
        if record is None:
            continue
        provenance[row["name"]]["astrometry_sources"] = {
            "service": candidate["source"]["service"],
            "retrieved_utc": retrieved,
            "simbad_id": record["simbad_id"],
            "position_bibcode": record.get("coo_bibcode"),
            "proper_motion_bibcode": record.get("pm_bibcode"),
            "parallax_bibcode": record.get("plx_bibcode"),
            "radial_velocity": {
                "admitted": velocity is not None,
                "value_km_s": record.get("rvz_radvel"),
                "error_km_s": record.get("rvz_err"),
                "quality": record.get("rvz_qual"),
                "type": record.get("rvz_type"),
                "bibcode": record.get("rvz_bibcode"),
            },
        }
    _write(REGISTRY, fieldnames, rows)
    PROVENANCE.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"radial velocities admitted: {measured} of {len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["epoch", "fetch-rv", "apply-rv"])
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--service", default=SIMBAD_TAP,
                        help=f"SIMBAD TAP endpoint (mirror: {SIMBAD_TAP_MIRROR})")
    args = parser.parse_args()
    if args.step == "epoch":
        print(f"rows given an explicit epoch: {add_epoch(args.registry)}")
    elif args.step == "fetch-rv":
        fetch_rv(args.out, args.service)
    else:
        apply_rv(args.candidate)


if __name__ == "__main__":
    main()

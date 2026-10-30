"""Add explicit astrometric metadata to the sovereign star registry.

usage:
  augment_star_registry_astrometry.py epoch
  augment_star_registry_astrometry.py fetch-rv --out CANDIDATE.json     (network)
  augment_star_registry_astrometry.py apply-rv --candidate CANDIDATE.json
  augment_star_registry_astrometry.py fetch-hg --hip NAME=HIP[:GAIA_ID] ... --out CANDIDATE.json  (network)
  augment_star_registry_astrometry.py apply-hg --candidate CANDIDATE.json

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

``fetch-hg`` is for a star whose catalog proper motion is a snapshot of an
orbit (a binary whose Hipparcos and Gaia proper motions disagree). For each
named row it fetches, from the ESA Gaia archive, the Hipparcos new reduction
(van Leeuwen 2007, J1991.25) and the Gaia DR3 source matched to it by Gaia's
own cross-match (``gaiadr3.hipparcos2_best_neighbour``, J2016.0), and derives
(a star the cross-match omits needs its Gaia DR3 source named explicitly, and
the candidate records that the match was stated, not catalogued):

- the long-term proper motion: the change of position between the two
  catalogs divided by their 24.75-year separation;
- the J2000.0 position on that chord; and
- the parallax: Gaia DR3 when its solution is well behaved (RUWE at most
  ``GAIA_RUWE_LIMIT``), otherwise Hipparcos.

``apply-hg`` writes a reviewed candidate's astrometry into the registry rows
and records the inputs and derivation in ``star_provenance.json``.

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
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
HIPPARCOS_EPOCH_YEAR = 1991.25
GAIA_DR3_EPOCH_YEAR = 2016.0
# Gaia DR3's usual threshold for a well-behaved single-star astrometric fit.
GAIA_RUWE_LIMIT = 1.4
_HG_QUERY = (
    "SELECT n.original_ext_source_id AS hip, g.source_id, g.ra, g.dec, g.parallax, "
    "g.parallax_error, g.pmra, g.pmdec, g.ruwe, g.ref_epoch, "
    "h.ra AS hip_ra, h.dec AS hip_dec, h.plx AS hip_plx, h.e_plx AS hip_plx_error, "
    "h.pm_ra AS hip_pmra, h.pm_de AS hip_pmdec, h.sn AS hip_solution, h.nc AS hip_components "
    "FROM gaiadr3.hipparcos2_best_neighbour AS n "
    "JOIN gaiadr3.gaia_source AS g ON g.source_id = n.source_id "
    "JOIN public.hipparcos_newreduction AS h ON h.hip = n.original_ext_source_id "
    "WHERE n.original_ext_source_id IN ({ids})"
)
_HG_STATED_QUERY = (
    "SELECT {hip} AS hip, g.source_id, g.ra, g.dec, g.parallax, "
    "g.parallax_error, g.pmra, g.pmdec, g.ruwe, g.ref_epoch, "
    "h.ra AS hip_ra, h.dec AS hip_dec, h.plx AS hip_plx, h.e_plx AS hip_plx_error, "
    "h.pm_ra AS hip_pmra, h.pm_de AS hip_pmdec, h.sn AS hip_solution, h.nc AS hip_components "
    "FROM gaiadr3.gaia_source AS g, public.hipparcos_newreduction AS h "
    "WHERE g.source_id = {source_id} AND h.hip = {hip}"
)
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


def _unit(ra_deg: float, dec_deg: float) -> tuple[float, float, float]:
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))


def _offset_mas(ra0: float, dec0: float, ra1: float, dec1: float) -> tuple[float, float]:
    """Gnomonic (east, north) offset of (ra1, dec1) from (ra0, dec0), in mas."""
    ra0, dec0, ra1, dec1 = map(math.radians, (ra0, dec0, ra1, dec1))
    cos_c = math.sin(dec0) * math.sin(dec1) + math.cos(dec0) * math.cos(dec1) * math.cos(ra1 - ra0)
    x = math.cos(dec1) * math.sin(ra1 - ra0) / cos_c
    y = (math.cos(dec0) * math.sin(dec1) - math.sin(dec0) * math.cos(dec1) * math.cos(ra1 - ra0)) / cos_c
    return math.degrees(x) * 3.6e6, math.degrees(y) * 3.6e6


def hipparcos_gaia_astrometry(record: dict) -> dict:
    """Long-term astrometry at J2000.0 from one Hipparcos/Gaia DR3 pair."""
    span = GAIA_DR3_EPOCH_YEAR - HIPPARCOS_EPOCH_YEAR
    east, north = _offset_mas(record["hip_ra"], record["hip_dec"], record["ra"], record["dec"])
    fraction = (2000.0 - HIPPARCOS_EPOCH_YEAR) / span
    a, b = _unit(record["hip_ra"], record["hip_dec"]), _unit(record["ra"], record["dec"])
    point = [x + fraction * (y - x) for x, y in zip(a, b)]
    norm = math.sqrt(sum(c * c for c in point))
    ra = math.degrees(math.atan2(point[1], point[0])) % 360.0
    dec = math.degrees(math.asin(point[2] / norm))
    gaia_parallax_ok = record["ruwe"] is not None and record["ruwe"] <= GAIA_RUWE_LIMIT
    return {
        "ra_deg": ra,
        "dec_deg": dec,
        "pmra_mas_yr": round(east / span, 3),
        "pmdec_mas_yr": round(north / span, 3),
        "parallax_mas": round(record["parallax"] if gaia_parallax_ok else record["hip_plx"], 4),
        "parallax_source": "gaia_dr3" if gaia_parallax_ok else "hipparcos_2007",
    }


def _gaia_tap(query: str) -> list[dict]:
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": query}).encode()
    with urllib.request.urlopen(urllib.request.Request(GAIA_TAP, data=body), timeout=120) as response:
        payload = json.load(response)
    names = [column["name"] for column in payload["metadata"]]
    return [dict(zip(names, row)) for row in payload["data"]]


def fetch_hg(targets: dict[str, tuple[int, int | None]], out: Path) -> None:
    """``targets`` maps a registry name to (HIP number, stated Gaia DR3 source or None)."""
    ids = ",".join(str(hip) for hip, _ in targets.values())
    by_hip = {int(r["hip"]): r for r in _gaia_tap(_HG_QUERY.format(ids=ids))}
    stars = {}
    for name, (hip, stated) in targets.items():
        if stated is not None:
            rows = _gaia_tap(_HG_STATED_QUERY.format(hip=hip, source_id=stated))
            if len(rows) != 1:
                raise SystemExit(f"stated Gaia DR3 source {stated} or HIP {hip} not found ({name})")
            record, match = rows[0], "stated"
        else:
            record, match = by_hip.get(hip), "gaia_dr3_hipparcos2_best_neighbour"
            if record is None:
                raise SystemExit(f"no Gaia DR3 cross-match for HIP {hip} ({name}); state the source")
        record["match"] = match
        stars[name] = {"inputs": record, "derived": hipparcos_gaia_astrometry(record)}
    out.write_text(json.dumps({
        "source": {"service": GAIA_TAP, "query": _HG_QUERY, "stated_query": _HG_STATED_QUERY,
                   "retrieved_utc": datetime.now(timezone.utc).isoformat()},
        "stars": stars,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"derived {len(stars)} rows -> {out}")


def apply_hg(candidate_path: Path) -> None:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    fieldnames, rows = _read(REGISTRY)
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    applied = 0
    for row in rows:
        entry = candidate["stars"].get(row["name"])
        if entry is None:
            continue
        derived, inputs = entry["derived"], entry["inputs"]
        if derived != hipparcos_gaia_astrometry(inputs):
            raise SystemExit(f"{row['name']}: candidate derivation does not reproduce")
        row["ra_deg"] = repr(derived["ra_deg"])
        row["dec_deg"] = repr(derived["dec_deg"])
        row["pmra_mas_yr"] = repr(derived["pmra_mas_yr"])
        row["pmdec_mas_yr"] = repr(derived["pmdec_mas_yr"])
        row["parallax_mas"] = repr(derived["parallax_mas"])
        row["ref_epoch_jd"] = SIMBAD_EPOCH_JD
        row["frame"] = SIMBAD_FRAME
        sources = provenance[row["name"]].setdefault("astrometry_sources", {})
        sources["position_bibcode"] = "Hipparcos 2007 / Gaia DR3 chord at J2000.0"
        sources["proper_motion_bibcode"] = "Hipparcos 2007 to Gaia DR3 long-term proper motion"
        sources["parallax_bibcode"] = (
            "2023A&A...674A...1G" if derived["parallax_source"] == "gaia_dr3" else "2007A&A...474..653V"
        )
        sources["hipparcos_gaia"] = {
            "service": candidate["source"]["service"],
            "retrieved_utc": candidate["source"]["retrieved_utc"],
            "hip": inputs["hip"],
            "gaia_dr3_source_id": inputs["source_id"],
            "gaia_match": inputs["match"],
            "gaia_ruwe": inputs["ruwe"],
            "parallax_source": derived["parallax_source"],
            "method": (
                "proper motion = (Gaia DR3 J2016.0 position - Hipparcos J1991.25 position) / "
                "24.75 yr; position = that chord at J2000.0; replaces the snapshot "
                "proper motion of a binary"
            ),
        }
        applied += 1
    _write(REGISTRY, fieldnames, rows)
    PROVENANCE.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"rows refreshed from Hipparcos and Gaia: {applied}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["epoch", "fetch-rv", "apply-rv", "fetch-hg", "apply-hg"])
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--service", default=SIMBAD_TAP,
                        help=f"SIMBAD TAP endpoint (mirror: {SIMBAD_TAP_MIRROR})")
    parser.add_argument("--hip", action="append", default=[],
                        help="NAME=HIP: a registry row and its Hipparcos number (fetch-hg)")
    args = parser.parse_args()
    if args.step == "epoch":
        print(f"rows given an explicit epoch: {add_epoch(args.registry)}")
    elif args.step == "fetch-rv":
        fetch_rv(args.out, args.service)
    elif args.step == "apply-rv":
        apply_rv(args.candidate)
    elif args.step == "fetch-hg":
        targets = {}
        for pair in args.hip:
            name, ids = pair.split("=", 1)
            hip, _, gaia = ids.partition(":")
            targets[name] = (int(hip), int(gaia) if gaia else None)
        fetch_hg(targets, args.out)
    else:
        apply_hg(args.candidate)


if __name__ == "__main__":
    main()

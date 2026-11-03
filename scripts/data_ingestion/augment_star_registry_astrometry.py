"""Add explicit astrometric metadata to the sovereign star registry.

usage:
  augment_star_registry_astrometry.py epoch
  augment_star_registry_astrometry.py fetch-rv --out CANDIDATE.json     (network)
  augment_star_registry_astrometry.py apply-rv --candidate CANDIDATE.json
  augment_star_registry_astrometry.py fetch-hg --hip NAME=HIP[:GAIA_ID] ... --out CANDIDATE.json  (network)
  augment_star_registry_astrometry.py apply-hg --candidate CANDIDATE.json
  augment_star_registry_astrometry.py fetch-plx --out CANDIDATE.json   (network; needs gaiadr3-zeropoint==0.1.0)
  augment_star_registry_astrometry.py derive-plx --candidate CANDIDATE.json   (offline re-derivation)

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

``fetch-plx`` fetches, for every registry row, the primary-catalog parallax
candidates and writes them with the derived adoption for review. The Gaia DR3
source and the Hipparcos number come from the row's SIMBAD identifier list;
Gaia DR3 astrometry and the Hipparcos new reduction (van Leeuwen 2007) come
from the ESA Gaia archive; the Gaia parallax zero-point (Lindegren et al. 2021)
is computed here with the ``gaiadr3-zeropoint`` package and stored, so nothing
downstream needs the package or the network. ``adopt_parallax`` is the pure
derivation of the adopted parallax and its uncertainty from those inputs; its
rules are Section 4.2 of docs/architecture/STAR_PARALLAX_SIGNIFICANCE_POLICY_DESIGN.md.
Nothing in ``moira/data`` changes.

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Section 3.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
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
# A Gaia and a Hipparcos parallax more than this many combined standard
# errors apart are discordant: the adopted error is widened to span both.
PARALLAX_DISCORDANCE_Z = 3.0
ZEROPOINT_PACKAGE = ("gaiadr3-zeropoint", "0.1.0")
PLX_CATALOGS = {
    "gaia_dr3": "2023A&A...674A...1G",
    "hipparcos_2007": "2007A&A...474..653V",
}
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


# --- parallax candidates and adoption -----------------------------------

_PLX_IDENT_QUERY = (
    "SELECT i.id AS q, i2.id AS other FROM ident AS i JOIN ident AS i2 ON i.oidref = i2.oidref "
    "WHERE i.id IN ({ids}) AND (i2.id LIKE 'Gaia DR3 %' OR i2.id LIKE 'HIP %')"
)
_PLX_SIMBAD_QUERY = (
    "SELECT i.id AS q, b.main_id, b.plx_value, b.plx_err, b.plx_qual, b.plx_bibcode "
    "FROM ident AS i JOIN basic AS b ON i.oidref = b.oid WHERE i.id IN ({ids})"
)
_PLX_GAIA_COLUMNS = (
    "source_id, ra, dec, pmra, pmdec, parallax, parallax_error, ruwe, astrometric_params_solved, "
    "phot_g_mean_mag, nu_eff_used_in_astrometry, pseudocolour, ecl_lat"
)
_PLX_GAIA_QUERY = "SELECT " + _PLX_GAIA_COLUMNS + " FROM gaiadr3.gaia_source WHERE source_id IN ({ids})"
_PLX_HIP_NEIGHBOUR_QUERY = (
    "SELECT n.source_id, h.hip, h.plx, h.e_plx FROM gaiadr3.hipparcos2_best_neighbour AS n "
    "JOIN public.hipparcos_newreduction AS h ON h.hip = n.original_ext_source_id "
    "WHERE n.source_id IN ({ids})"
)
_PLX_HIP_QUERY = "SELECT hip, plx, e_plx FROM public.hipparcos_newreduction WHERE hip IN ({ids})"
_PLX_DISTANCE_QUERY = (
    "SELECT source_id, r_med_geo, r_lo_geo, r_hi_geo FROM external.gaiaedr3_distance "
    "WHERE source_id IN ({ids})"
)


def _tap_query(service: str, adql: str, tries: int = 6) -> list[dict]:
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": adql}).encode()
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(service, data=body), timeout=180) as response:
                payload = json.load(response)
            names = [column["name"] for column in payload["metadata"]]
            return [dict(zip(names, row)) for row in payload["data"]]
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(10.0 * (attempt + 1))  # busy archives answer 503 for a while
    raise AssertionError("unreachable")


def _batches(items, size: int):
    items = list(items)
    for start in range(0, len(items), size):
        yield items[start:start + size]


def gaia_zero_point(gaia: dict) -> float | None:
    """Lindegren et al. (2021) parallax zero-point in mas, or None outside its validity.

    The published fit covers 5- and 6-parameter solutions with 6 <= G <= 21, and
    for a 5-parameter solution 1.1 <= nu_eff <= 1.9, for a 6-parameter solution
    1.24 <= pseudocolour <= 1.72.
    """
    magnitude, beta, params = gaia["phot_g_mean_mag"], gaia["ecl_lat"], gaia["astrometric_params_solved"]
    nu_eff, pseudocolour = gaia["nu_eff_used_in_astrometry"], gaia["pseudocolour"]
    if magnitude is None or beta is None or params not in (31, 95) or not 6.0 <= magnitude <= 21.0:
        return None
    if params == 31 and (nu_eff is None or not 1.1 <= nu_eff <= 1.9):
        return None
    if params == 95 and (pseudocolour is None or not 1.24 <= pseudocolour <= 1.72):
        return None
    import numpy as np
    from importlib.metadata import version
    from zero_point import zpt

    if version(ZEROPOINT_PACKAGE[0]) != ZEROPOINT_PACKAGE[1]:
        raise SystemExit(f"{ZEROPOINT_PACKAGE[0]}=={ZEROPOINT_PACKAGE[1]} is required")
    if not getattr(gaia_zero_point, "_loaded", False):
        zpt.load_tables()
        gaia_zero_point._loaded = True

    # The package rejects Python scalars under NumPy 2; it accepts arrays.
    def column(value):
        return np.array([np.nan if value is None else value], dtype=float)

    value = zpt.get_zpt(column(magnitude), column(nu_eff), column(pseudocolour), column(beta),
                        np.array([params]), _warnings=False)[0]
    return float(value) if math.isfinite(value) else None


def _positive(value) -> bool:
    return value is not None and math.isfinite(value) and value > 0.0


def adopt_parallax(inputs: dict) -> dict:
    """Adopt one parallax and its uncertainty from a row's Gaia, Hipparcos and SIMBAD inputs.

    Rules: docs/architecture/STAR_PARALLAX_SIGNIFICANCE_POLICY_DESIGN.md, Section 4.2.
    ``inputs`` holds ``gaia`` (with ``zero_point``), ``hipparcos`` and ``simbad``,
    each a dict or None. The result names the source, lists any flags and records
    every candidate used.
    """
    candidates, flags = {}, []
    gaia = inputs.get("gaia")
    if (gaia and gaia["astrometric_params_solved"] in (31, 95) and gaia["ruwe"] is not None
            and gaia["parallax"] is not None and _positive(gaia["parallax_error"])):
        zero_point = gaia["zero_point"]
        candidates["gaia"] = {
            "parallax_mas": gaia["parallax"] - (zero_point or 0.0),
            "error_mas": gaia["parallax_error"] * max(1.0, gaia["ruwe"]),
            "zero_point_mas": zero_point,
            "uncalibrated": zero_point is None,
        }
    hipparcos = inputs.get("hipparcos")
    if hipparcos and hipparcos["plx"] is not None and _positive(hipparcos["e_plx"]):
        candidates["hipparcos"] = {"parallax_mas": hipparcos["plx"], "error_mas": hipparcos["e_plx"]}
    result = {"candidates": candidates, "flags": flags}
    if "gaia" in candidates and "hipparcos" in candidates:
        g, h = candidates["gaia"], candidates["hipparcos"]
        w_g, w_h = g["error_mas"] ** -2, h["error_mas"] ** -2
        parallax = (g["parallax_mas"] * w_g + h["parallax_mas"] * w_h) / (w_g + w_h)
        error = (w_g + w_h) ** -0.5
        gap = abs(g["parallax_mas"] - h["parallax_mas"])
        z = gap / math.hypot(g["error_mas"], h["error_mas"])
        result["discordance_z"] = z
        if z > PARALLAX_DISCORDANCE_Z:
            # When the catalogs conflict beyond their stated errors those errors cannot
            # weight them. The midpoint with a half-gap error spans both measurements
            # and is correct whichever of the two is the wrong one.
            parallax = (g["parallax_mas"] + h["parallax_mas"]) / 2.0
            error = max(error, gap / 2.0)
            flags.append("discordant")
            source = "gaia_hipparcos_combined_discordant"
        else:
            source = "gaia_hipparcos_combined"
        if g["uncalibrated"]:
            flags.append("gaia_uncalibrated")
        result.update(parallax_mas=parallax, parallax_error_mas=error, parallax_source=source,
                      parallax_bibcodes=[PLX_CATALOGS["gaia_dr3"], PLX_CATALOGS["hipparcos_2007"]])
    elif "gaia" in candidates:
        g = candidates["gaia"]
        if g["uncalibrated"]:
            flags.append("gaia_uncalibrated")
        result.update(parallax_mas=g["parallax_mas"], parallax_error_mas=g["error_mas"],
                      parallax_source="gaia_dr3_uncalibrated" if g["uncalibrated"] else "gaia_dr3",
                      parallax_bibcodes=[PLX_CATALOGS["gaia_dr3"]])
    elif "hipparcos" in candidates:
        h = candidates["hipparcos"]
        result.update(parallax_mas=h["parallax_mas"], parallax_error_mas=h["error_mas"],
                      parallax_source="hipparcos_2007", parallax_bibcodes=[PLX_CATALOGS["hipparcos_2007"]])
    else:
        simbad = inputs.get("simbad")
        if simbad and simbad["plx_value"] is not None and _positive(simbad["plx_err"]):
            result.update(parallax_mas=simbad["plx_value"], parallax_error_mas=simbad["plx_err"],
                          parallax_source="simbad_fallback", parallax_bibcodes=[simbad["plx_bibcode"]])
        else:
            result.update(parallax_mas=None, parallax_error_mas=None, parallax_source="none",
                          parallax_bibcodes=[])
    return result


def _gaia_rows(adql: str) -> list[dict]:
    return _tap_query(GAIA_TAP, adql)


def _catalog_offset_arcsec(row: dict, gaia: dict) -> float:
    """Separation of the registry J2000.0 position from the Gaia DR3 position carried back to J2000.0."""
    years = GAIA_DR3_EPOCH_YEAR - 2000.0
    cos_dec = max(math.cos(math.radians(gaia["dec"])), 1e-9)
    ra = gaia["ra"] - (gaia["pmra"] or 0.0) / 3.6e6 / cos_dec * years
    dec = gaia["dec"] - (gaia["pmdec"] or 0.0) / 3.6e6 * years
    return math.hypot((float(row["ra_deg"]) - ra) * cos_dec, float(row["dec_deg"]) - dec) * 3600.0


def derive_plx(candidate_path: Path) -> None:
    """Recompute every row's adoption from its frozen inputs, after a rule change; no network."""
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    changed = 0
    for entry in candidate["stars"].values():
        derived = adopt_parallax(entry["inputs"])
        changed += derived != entry["derived"]
        entry["derived"] = derived
    candidate_path.write_text(json.dumps(candidate, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"rows re-derived: {len(candidate['stars'])}; changed: {changed}")


def fetch_plx(out: Path, service: str) -> None:
    """Fetch every row's parallax candidates and write them, with the derived adoption, to ``out``."""
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    _, rows = _read(REGISTRY)
    wanted = {row["name"]: _simbad_identifier(provenance[row["name"]]) for row in rows}
    registry = {row["name"]: row for row in rows}
    normalized = {" ".join(i.split()): i for i in set(wanted.values())}
    spelled = sorted({_simbad_spelling(i) for i in set(wanted.values())})

    def quoted(items):
        return ",".join("'" + str(i).replace("'", "''") + "'" for i in items)

    gaia_ids: dict[str, set[int]] = {}
    hip_ids: dict[str, set[int]] = {}
    simbad: dict[str, dict] = {}
    for done, batch in enumerate(_batches(spelled, 150), start=1):
        for record in _tap_query(service, _PLX_IDENT_QUERY.format(ids=quoted(batch))):
            key = normalized.get(" ".join(record["q"].split()))
            tail = record["other"].split()[-1]
            # Component suffixes ("HIP 9640B") name another star.
            if key is not None and tail.isdigit():
                (gaia_ids if record["other"].startswith("Gaia") else hip_ids).setdefault(key, set()).add(int(tail))
        for record in _tap_query(service, _PLX_SIMBAD_QUERY.format(ids=quoted(batch))):
            key = normalized.get(" ".join(record["q"].split()))
            if key is not None:
                simbad[key] = {k: record[k] for k in ("main_id", "plx_value", "plx_err", "plx_qual", "plx_bibcode")}
        print(f"  SIMBAD batch {done}", flush=True)

    source_ids = sorted({g for ids in gaia_ids.values() for g in ids})
    gaia: dict[int, dict] = {}
    neighbour: dict[int, dict] = {}
    distance: dict[int, dict] = {}
    for done, batch in enumerate(_batches(source_ids, 200), start=1):
        listed = ",".join(map(str, batch))
        for record in _gaia_rows(_PLX_GAIA_QUERY.format(ids=listed)):
            gaia[record["source_id"]] = record
        for record in _gaia_rows(_PLX_HIP_NEIGHBOUR_QUERY.format(ids=listed)):
            neighbour[record["source_id"]] = record
        for record in _gaia_rows(_PLX_DISTANCE_QUERY.format(ids=listed)):
            distance[record["source_id"]] = record
        print(f"  Gaia batch {done}", flush=True)
    hip: dict[int, dict] = {r["hip"]: r for r in neighbour.values()}
    extra = sorted({h for ids in hip_ids.values() for h in ids} - set(hip))
    for batch in _batches(extra, 200):
        for record in _gaia_rows(_PLX_HIP_QUERY.format(ids=",".join(map(str, batch)))):
            hip[record["hip"]] = record

    stars = {}
    for name, ident in wanted.items():
        sources = sorted(gaia_ids.get(ident, ()))
        row_gaia = gaia.get(sources[0]) if sources else None
        entry_gaia, offset = None, None
        if row_gaia is not None and row_gaia["parallax"] is not None:
            entry_gaia = dict(row_gaia, zero_point=gaia_zero_point(row_gaia))
            offset = _catalog_offset_arcsec(registry[name], row_gaia)
        chosen_hip, match = None, None
        for number in sorted(hip_ids.get(ident, ())):
            if number in hip:
                chosen_hip, match = hip[number], "simbad_identifier"
                break
        if row_gaia is not None and row_gaia["source_id"] in neighbour:
            chosen_hip, match = neighbour[row_gaia["source_id"]], "gaia_dr3_hipparcos2_best_neighbour"
        inputs = {
            "simbad_identifier": ident,
            "simbad": simbad.get(ident),
            "gaia_source_ids": sources,
            "gaia": entry_gaia,
            "hipparcos": None if chosen_hip is None else {
                "hip": chosen_hip["hip"], "plx": chosen_hip["plx"], "e_plx": chosen_hip["e_plx"], "match": match},
            "gaia_position_offset_arcsec": offset,
            "bailer_jones_2021": distance.get(sources[0]) if sources else None,
        }
        stars[name] = {"inputs": inputs, "derived": adopt_parallax(inputs)}
    from importlib.metadata import version
    out.write_text(json.dumps({
        "source": {
            "simbad_service": service, "gaia_service": GAIA_TAP,
            "queries": {"ident": _PLX_IDENT_QUERY, "simbad": _PLX_SIMBAD_QUERY, "gaia": _PLX_GAIA_QUERY,
                        "hipparcos_neighbour": _PLX_HIP_NEIGHBOUR_QUERY, "hipparcos": _PLX_HIP_QUERY,
                        "distance": _PLX_DISTANCE_QUERY},
            "zero_point_package": f"{ZEROPOINT_PACKAGE[0]}=={version(ZEROPOINT_PACKAGE[0])}",
            "discordance_z": PARALLAX_DISCORDANCE_Z,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        },
        "stars": stars,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    counts: dict[str, int] = {}
    for entry in stars.values():
        key = entry["derived"]["parallax_source"]
        counts[key] = counts.get(key, 0) + 1
    print(f"candidates for {len(stars)} rows -> {out}\n  {counts}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["epoch", "fetch-rv", "apply-rv", "fetch-hg", "apply-hg", "fetch-plx", "derive-plx"])
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
    elif args.step == "fetch-plx":
        fetch_plx(args.out, args.service)
    elif args.step == "derive-plx":
        derive_plx(args.candidate)
    else:
        apply_hg(args.candidate)


if __name__ == "__main__":
    main()

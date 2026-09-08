"""Refresh Moira's curated deep-sky coordinate-anchor catalog.

The selection is Moira-owned and intentionally small.  SIMBAD supplies the
resolved object identity and its best current ICRS/J2000 coordinate record;
the NASA Exoplanet Archive independently confirms the host-star subset.  This
tool is build-time only and adds no network dependency to the runtime package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO_ROOT / "moira" / "data" / "deep_sky_catalog.json"
DEFAULT_METADATA = REPO_ROOT / "moira" / "data" / "deep_sky_catalog.metadata.json"
SIMBAD_IDENTIFIER_URL = "https://simbad.cds.unistra.fr/simbad/sim-id"
SIMBAD_TAP_URL = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
NASA_EXOPLANET_TAP_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
CATALOG_ID = "moira-deep-sky"
CATALOG_VERSION = "2026.09.07.1"
EXPECTED_CLASS_COUNTS = {
    "galaxy": 15,
    "nebula": 15,
    "star_cluster": 15,
    "compact_object": 5,
    "stellar_remnant": 5,
    "host_star": 5,
}
ADMITTED_SIMBAD_PROPER_MOTION = frozenset(
    {
        "Pleiades",
        "Hyades",
        "Beehive Cluster",
        "Double Cluster h Persei",
        "Double Cluster chi Persei",
        "Omega Centauri",
        "47 Tucanae",
        "Hercules Cluster",
        "Messier 3",
        "Messier 5",
        "Messier 15",
        "Sagittarius Cluster",
        "Messier 67",
        "Jewel Box Cluster",
        "Wild Duck Cluster",
        "Cygnus X-1",
        "V404 Cygni",
        "SS 433",
    }
)


def _entry(
    canonical_name: str,
    designation: str,
    object_class: str,
    *aliases: str,
    star_registry_name: str | None = None,
    nasa_hostname: str | None = None,
    is_extended: bool = True,
) -> dict[str, Any]:
    """Build one immutable selection record before source enrichment."""

    return {
        "canonical_name": canonical_name,
        "designation": designation,
        "object_class": object_class,
        "aliases": list(aliases),
        "star_registry_name": star_registry_name,
        "nasa_exoplanet_archive_hostname": nasa_hostname,
        "is_extended": is_extended,
    }


CURATED_SELECTION = (
    # Galaxies: catalog centers, never dynamical point masses.
    _entry("Andromeda Galaxy", "M 31", "galaxy", "M31", "NGC 224"),
    _entry("Triangulum Galaxy", "M 33", "galaxy", "M33", "NGC 598"),
    _entry("Whirlpool Galaxy", "M 51", "galaxy", "M51", "NGC 5194"),
    _entry("Bode's Galaxy", "M 81", "galaxy", "M81", "NGC 3031"),
    _entry("Cigar Galaxy", "M 82", "galaxy", "M82", "NGC 3034"),
    _entry("Sombrero Galaxy", "M 104", "galaxy", "M104", "NGC 4594"),
    _entry("Pinwheel Galaxy", "M 101", "galaxy", "M101", "NGC 5457"),
    _entry("Black Eye Galaxy", "M 64", "galaxy", "M64", "NGC 4826"),
    _entry("Sunflower Galaxy", "M 63", "galaxy", "M63", "NGC 5055"),
    _entry("Southern Pinwheel Galaxy", "M 83", "galaxy", "M83", "NGC 5236"),
    _entry("Sculptor Galaxy", "NGC 253", "galaxy"),
    _entry("Centaurus A", "NGC 5128", "galaxy", "Cen A"),
    _entry("Large Magellanic Cloud", "LMC", "galaxy"),
    _entry("Small Magellanic Cloud", "SMC", "galaxy"),
    _entry("M87 Galaxy", "M 87", "galaxy", "M87", "Virgo A", "NGC 4486"),
    # Nebulae: use emission-region identities where SIMBAD exposes them separately;
    # mixed Messier/NGC records retain SIMBAD's source type without changing Moira's class.
    _entry("Orion Nebula", "M 42", "nebula", "M42", "NGC 1976"),
    _entry("Lagoon Nebula", "NGC 6523", "nebula", "M8", "M 8"),
    _entry("Trifid Nebula", "NGC 6514", "nebula", "M20", "M 20"),
    _entry("Eagle Nebula", "Sh 2-49", "nebula", "M16", "M 16", "IC 4703"),
    _entry("Omega Nebula", "Sh 2-45", "nebula", "M17", "M 17", "Swan Nebula"),
    _entry("Rosette Nebula", "NAME Rosette Nebula", "nebula", "NGC 2237"),
    _entry("Carina Nebula", "NGC 3372", "nebula", "Eta Carinae Nebula"),
    _entry("North America Nebula", "NGC 7000", "nebula", "Caldwell 20"),
    _entry("Helix Nebula", "NGC 7293", "nebula", "Caldwell 63"),
    _entry("Ring Nebula", "M 57", "nebula", "M57", "NGC 6720"),
    _entry("Dumbbell Nebula", "M 27", "nebula", "M27", "NGC 6853"),
    _entry("Cat's Eye Nebula", "NGC 6543", "nebula", "Caldwell 6"),
    _entry("Horsehead Nebula", "NAME Horsehead Nebula", "nebula", "Barnard 33", "B33"),
    _entry("Tarantula Nebula", "NAME Tarantula Nebula", "nebula", "30 Doradus", "NGC 2070"),
    _entry("California Nebula", "NGC 1499", "nebula"),
    # Open and globular cluster centers.
    _entry("Pleiades", "M 45", "star_cluster", "M45", "Melotte 22", "Seven Sisters"),
    _entry("Hyades", "NAME Hyades", "star_cluster", "Melotte 25"),
    _entry("Beehive Cluster", "M 44", "star_cluster", "M44", "Praesepe", "NGC 2632"),
    _entry("Double Cluster h Persei", "NGC 869", "star_cluster", "h Persei"),
    _entry("Double Cluster chi Persei", "NGC 884", "star_cluster", "chi Persei"),
    _entry("Omega Centauri", "NGC 5139", "star_cluster", "Caldwell 80"),
    _entry("47 Tucanae", "NGC 104", "star_cluster", "47 Tuc", "Caldwell 106"),
    _entry("Hercules Cluster", "M 13", "star_cluster", "M13", "NGC 6205"),
    _entry("Messier 3", "M 3", "star_cluster", "M3", "NGC 5272"),
    _entry("Messier 5", "M 5", "star_cluster", "M5", "NGC 5904"),
    _entry("Messier 15", "M 15", "star_cluster", "M15", "NGC 7078"),
    _entry("Sagittarius Cluster", "M 22", "star_cluster", "M22", "NGC 6656"),
    _entry("Messier 67", "M 67", "star_cluster", "M67", "NGC 2682"),
    _entry("Jewel Box Cluster", "NGC 4755", "star_cluster", "Caldwell 94"),
    _entry("Wild Duck Cluster", "M 11", "star_cluster", "M11", "NGC 6705"),
    # Compact systems and nuclei use their catalog point, with SIMBAD PM when present.
    _entry("Sagittarius A*", "NAME Sgr A*", "compact_object", "Sgr A*", is_extended=False),
    _entry("Cygnus X-1", "Cyg X-1", "compact_object", "HD 226868", is_extended=False),
    _entry("V404 Cygni", "V404 Cyg", "compact_object", "GS 2023+338", is_extended=False),
    _entry("SS 433", "SS 433", "compact_object", "V1343 Aql", is_extended=False),
    _entry("3C 273", "3C 273", "compact_object", "QSO B1226+023", is_extended=False),
    # Supernova-remnant centers remain explicitly extended catalog anchors.
    _entry("Crab Nebula", "M 1", "stellar_remnant", "M1", "NGC 1952", "Taurus A"),
    _entry("Cassiopeia A", "Cas A", "stellar_remnant", "3C 461"),
    _entry("Tycho Supernova Remnant", "SNR G120.1+01.4", "stellar_remnant", "SN 1572", "3C 10"),
    _entry("Kepler Supernova Remnant", "NAME Kepler SNR", "stellar_remnant", "SN 1604", "SNR G4.5+6.8"),
    _entry("Vela Supernova Remnant", "NAME Vela SNR", "stellar_remnant", "SNR G263.9-3.3"),
    # Host stars delegate runtime positions to the sovereign star registry.
    _entry("Helvetios", "51 Peg", "host_star", "51 Pegasi", star_registry_name="Helvetios", nasa_hostname="51 Peg", is_extended=False),
    _entry("Copernicus", "55 Cnc", "host_star", "55 Cancri", star_registry_name="Copernicus", nasa_hostname="55 Cnc", is_extended=False),
    _entry("Ran", "eps Eri", "host_star", "Epsilon Eridani", star_registry_name="Ran", nasa_hostname="eps Eri", is_extended=False),
    _entry("Proxima Centauri", "NAME Proxima Centauri", "host_star", "Proxima Cen", "Alpha Centauri C", star_registry_name="Proxima Centauri", nasa_hostname="Proxima Cen", is_extended=False),
    _entry("Beta Pictoris", "bet Pic", "host_star", "Beta Pic", star_registry_name="bet Pic", nasa_hostname="bet Pic", is_extended=False),
)


def _http_bytes(request: urllib.request.Request, *, attempts: int = 3) -> bytes:
    """Return one HTTP response body with bounded retries."""

    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - surfaced after bounded retries
            last_error = exc
    assert last_error is not None
    raise last_error


def _resolve_simbad_identifier(identifier: str) -> str:
    """Resolve a flexible SIMBAD identifier to exactly one main identifier."""

    query = urllib.parse.urlencode({"Ident": identifier, "output.format": "VOTable"})
    request = urllib.request.Request(
        f"{SIMBAD_IDENTIFIER_URL}?{query}",
        headers={"User-Agent": "Moira deep-sky catalog refresh"},
    )
    payload = _http_bytes(request)
    root = ET.fromstring(payload)
    rows = root.findall(".//{*}TABLEDATA/{*}TR")
    if len(rows) != 1:
        raise ValueError(f"SIMBAD identifier {identifier!r} resolved to {len(rows)} rows")
    cells = rows[0].findall("{*}TD")
    if len(cells) < 7 or not (cells[3].text or "").strip():
        raise ValueError(f"SIMBAD identifier {identifier!r} returned no main identity")
    return (cells[3].text or "").strip()


def _post_json(url: str, fields: dict[str, str]) -> dict[str, Any]:
    """POST URL-encoded fields and decode one JSON object response."""

    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(fields).encode("ascii"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Moira deep-sky catalog refresh",
        },
    )
    return json.loads(_http_bytes(request).decode("utf-8"))


def _simbad_rows(main_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch source-bound astrometry for resolved SIMBAD main identifiers."""

    quoted = ", ".join("'" + item.replace("'", "''") + "'" for item in main_ids)
    adql = (
        "SELECT main_id, ra, dec, otype, coo_bibcode, coo_qual, pmra, pmdec "
        f"FROM basic WHERE main_id IN ({quoted})"
    )
    payload = _post_json(
        SIMBAD_TAP_URL,
        {"request": "doQuery", "lang": "adql", "format": "json", "query": adql},
    )
    columns = [item["name"] for item in payload["metadata"]]
    rows = {str(row[0]): dict(zip(columns, row, strict=True)) for row in payload["data"]}
    missing = sorted(set(main_ids) - set(rows))
    if missing:
        raise ValueError(f"SIMBAD TAP omitted resolved identities: {missing}")
    return rows


def _nasa_host_counts(hostnames: list[str]) -> dict[str, int]:
    """Return confirmed-planet row counts for the selected NASA host names."""

    quoted = ", ".join("'" + item.replace("'", "''") + "'" for item in hostnames)
    adql = (
        "SELECT hostname, count(pl_name) AS planet_count FROM pscomppars "
        f"WHERE hostname IN ({quoted}) GROUP BY hostname"
    )
    query = urllib.parse.urlencode({"query": adql, "format": "json"})
    request = urllib.request.Request(
        f"{NASA_EXOPLANET_TAP_URL}?{query}",
        headers={"Accept": "application/json", "User-Agent": "Moira deep-sky catalog refresh"},
    )
    rows = json.loads(_http_bytes(request).decode("utf-8"))
    counts = {str(row["hostname"]): int(row["planet_count"]) for row in rows}
    missing = sorted(set(hostnames) - set(counts))
    if missing:
        raise ValueError(f"NASA Exoplanet Archive omitted selected hosts: {missing}")
    return counts


def _validate_selection() -> None:
    """Reject duplicate labels or an accidental change to the admitted scope."""

    counts = Counter(str(item["object_class"]) for item in CURATED_SELECTION)
    if dict(counts) != EXPECTED_CLASS_COUNTS:
        raise ValueError(f"class counts {dict(counts)} != {EXPECTED_CLASS_COUNTS}")
    labels: dict[str, str] = {}
    for item in CURATED_SELECTION:
        for label in (item["canonical_name"], item["designation"], *item["aliases"]):
            key = " ".join(str(label).split()).casefold()
            owner = labels.get(key)
            if owner is not None and owner != item["canonical_name"]:
                raise ValueError(f"label {label!r} collides between {owner!r} and {item['canonical_name']!r}")
            labels[key] = str(item["canonical_name"])


def _catalog_payload() -> dict[str, Any]:
    """Resolve the curated selection and return the packaged catalog payload."""

    _validate_selection()
    with ThreadPoolExecutor(max_workers=6) as executor:
        main_ids = list(executor.map(_resolve_simbad_identifier, (item["designation"] for item in CURATED_SELECTION)))
    source_rows = _simbad_rows(main_ids)
    hostnames = [str(item["nasa_exoplanet_archive_hostname"]) for item in CURATED_SELECTION if item["nasa_exoplanet_archive_hostname"]]
    host_counts = _nasa_host_counts(hostnames)

    records: list[dict[str, Any]] = []
    for selection, main_id in zip(CURATED_SELECTION, main_ids, strict=True):
        source = source_rows[main_id]
        ra = float(source["ra"])
        dec = float(source["dec"])
        if not (math.isfinite(ra) and 0.0 <= ra < 360.0 and math.isfinite(dec) and -90.0 <= dec <= 90.0):
            raise ValueError(f"invalid SIMBAD coordinate for {main_id!r}: {ra}, {dec}")
        aliases = list(dict.fromkeys(str(alias) for alias in selection["aliases"] if alias))
        proper_motion_admitted = selection["canonical_name"] in ADMITTED_SIMBAD_PROPER_MOTION
        if proper_motion_admitted and (source["pmra"] is None or source["pmdec"] is None):
            raise ValueError(f"admitted proper motion is missing for {main_id!r}")
        record = {
            "canonical_name": selection["canonical_name"],
            "designation": selection["designation"],
            "aliases": aliases,
            "object_class": selection["object_class"],
            "is_extended": bool(selection["is_extended"]),
            "position_semantics": "sovereign_star_propagation" if selection["object_class"] == "host_star" else "catalog_center",
            "simbad_main_id": main_id,
            "simbad_otype": str(source["otype"]),
            "ra_deg": ra,
            "dec_deg": dec,
            "pmra_mas_yr": None if source["pmra"] is None else float(source["pmra"]),
            "pmdec_mas_yr": None if source["pmdec"] is None else float(source["pmdec"]),
            "proper_motion_admitted": proper_motion_admitted,
            "coordinate_bibcode": str(source["coo_bibcode"] or ""),
            "coordinate_quality": str(source["coo_qual"] or ""),
            "star_registry_name": selection["star_registry_name"],
            "nasa_exoplanet_archive_hostname": selection["nasa_exoplanet_archive_hostname"],
            "confirmed_planet_count": None,
        }
        hostname = selection["nasa_exoplanet_archive_hostname"]
        if hostname:
            record["confirmed_planet_count"] = host_counts[str(hostname)]
        records.append(record)

    return {
        "schema_version": 1,
        "catalog_id": CATALOG_ID,
        "catalog_version": CATALOG_VERSION,
        "records": records,
    }


def _json_bytes(payload: Any) -> bytes:
    """Serialize a package artifact with stable UTF-8 formatting."""

    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build_artifacts(snapshot_utc: str, simbad_release: str) -> tuple[bytes, bytes]:
    """Return catalog and metadata bytes for one explicit source snapshot."""

    catalog = _catalog_payload()
    catalog_bytes = _json_bytes(catalog)
    metadata = {
        "schema_version": 1,
        "catalog_id": CATALOG_ID,
        "catalog_version": CATALOG_VERSION,
        "selection_policy": {
            "owner": "Moira",
            "purpose": "curated non-interpretive coordinate anchors requested in GitHub Discussion 19",
            "class_counts": EXPECTED_CLASS_COUNTS,
            "extended_object_policy": "a catalog center is an angular anchor, not a physical point mass",
            "host_star_policy": "confirmed host identity is checked against NASA; runtime position delegates to the sovereign star registry",
            "solar_system_exclusion": "planets, satellites, asteroids, comets, and interstellar visitors require time-dependent ephemerides and are excluded",
        },
        "coordinate_model": {
            "source_frame": "ICRS",
            "source_epoch": "J2000.0",
            "source_epoch_jd_tt": 2451545.0,
            "runtime_frame": "true_ecliptic_of_date",
            "runtime_path": "class-admitted SIMBAD proper motion; Moira IAU 2006 precession; IAU 2000A nutation; true obliquity",
            "proper_motion_policy": "only selected cluster centers and stellar compact systems use SIMBAD proper motion; galaxy, nebula, remnant, quasar, and Galactic-center anchors remain fixed at their released J2000 coordinate",
            "observer_model": "geocentric direction only; no topocentric parallax or atmospheric refraction",
        },
        "sources": {
            "simbad": {
                "service": "SIMBAD astronomical database, CDS Strasbourg",
                "release": simbad_release,
                "snapshot_utc": snapshot_utc,
                "identifier_endpoint": SIMBAD_IDENTIFIER_URL,
                "tap_endpoint": SIMBAD_TAP_URL,
                "fields": ["main_id", "ra", "dec", "otype", "coo_bibcode", "coo_qual", "pmra", "pmdec"],
                "license": "Open Data Commons Open Database License (ODbL) 1.0",
                "acknowledgement": "This research has made use of the SIMBAD database, operated at CDS, Strasbourg, France.",
                "reference": "2000A&AS..143....9W",
            },
            "nasa_exoplanet_archive": {
                "service": "NASA Exoplanet Archive",
                "snapshot_utc": snapshot_utc,
                "tap_endpoint": NASA_EXOPLANET_TAP_URL,
                "table": "pscomppars",
                "fields": ["hostname", "count(pl_name)"],
                "doi": "10.26133/NEA1",
            },
        },
        "artifact": {
            "path": "moira/data/deep_sky_catalog.json",
            "sha256": hashlib.sha256(catalog_bytes).hexdigest(),
            "record_count": len(catalog["records"]),
            "class_counts": EXPECTED_CLASS_COUNTS,
        },
    }
    return catalog_bytes, _json_bytes(metadata)


def main() -> None:
    """Refresh and write the release-bound catalog and metadata receipt."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--simbad-release", default="SIMBAD4 1.8 - 2026-07")
    parser.add_argument(
        "--snapshot-utc",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()
    catalog_bytes, metadata_bytes = build_artifacts(args.snapshot_utc, args.simbad_release)
    args.catalog.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.catalog.write_bytes(catalog_bytes)
    args.metadata.write_bytes(metadata_bytes)
    print(f"wrote {args.catalog} ({len(json.loads(catalog_bytes)['records'])} records)")
    print(f"wrote {args.metadata}")


if __name__ == "__main__":
    main()

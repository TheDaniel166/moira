"""
Build canonical asteroid orbit class registry for Moira 6.8.0.

Queries JPL SBDB Query API for all non-MBA numbered classes (CEN, TNO, IEO, ATE, APO,
AMO, MCA, TJN, IMB, OMB, AST, PAA, HYA) and assigns MBA to all remaining admitted bodies.
Produces moira/data/asteroid_orbit_classes.json mapping NAIF ID string -> {
    "code": "CEN" | "TNO" | "MBA" | ...,
    "title": "Centaur" | ...
}
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAIF_CATALOG_PATH = ROOT / "moira" / "data" / "asteroid_catalog_naif.json"
OUTPUT_PATH = ROOT / "moira" / "data" / "asteroid_orbit_classes.json"
METADATA_PATH = ROOT / "moira" / "data" / "asteroid_orbit_classes.metadata.json"

SBDB_QUERY_URL = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Moira-Astro/6.8.0"

CLASS_TITLES: dict[str, str] = {
    "IEO": "Atira",
    "ATE": "Aten",
    "APO": "Apollo",
    "AMO": "Amor",
    "MCA": "Mars-crossing Asteroid",
    "IMB": "Inner Main-belt Asteroid",
    "MBA": "Main-belt Asteroid",
    "OMB": "Outer Main-belt Asteroid",
    "TJN": "Jupiter Trojan",
    "AST": "Asteroid",
    "CEN": "Centaur",
    "TNO": "TransNeptunian Object",
    "PAA": "Parabolic Asteroid",
    "HYA": "Hyperbolic Asteroid",
}


def _fetch_classes(sb_classes: str) -> list[tuple[int, str]]:
    url = f"{SBDB_QUERY_URL}?fields=spkid,class&sb-class={sb_classes}&sb-ns=n"
    print(f"Fetching classes for {sb_classes}...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    records = []
    for row in data.get("data", []):
        spkid, cls = row
        mpc_num = int(spkid) - 20000000
        naif_id = 2000000 + mpc_num
        records.append((naif_id, cls))
    print(f"  Received {len(records)} records.", flush=True)
    return records


def build_catalog() -> None:
    catalog: dict[str, int] = json.loads(NAIF_CATALOG_PATH.read_text(encoding="utf-8"))
    admitted_naifs = set(catalog.values())
    print(f"Total admitted bodies in NAIF catalog: {len(admitted_naifs)}")

    # 1. Fetch non-MBA classes
    known_classes: dict[int, str] = {}
    
    # CEN, TNO
    for naif_id, cls in _fetch_classes("CEN,TNO"):
        if naif_id in admitted_naifs:
            known_classes[naif_id] = cls
    time.sleep(1)

    # Near-Earth & Mars-crossers
    for naif_id, cls in _fetch_classes("IEO,ATE,APO,AMO,MCA"):
        if naif_id in admitted_naifs:
            known_classes[naif_id] = cls
    time.sleep(1)

    # Jupiter Trojans
    for naif_id, cls in _fetch_classes("TJN"):
        if naif_id in admitted_naifs:
            known_classes[naif_id] = cls
    time.sleep(1)

    # IMB, OMB
    for naif_id, cls in _fetch_classes("IMB,OMB"):
        if naif_id in admitted_naifs:
            known_classes[naif_id] = cls
    time.sleep(1)

    # Rare/other
    for naif_id, cls in _fetch_classes("AST,PAA,HYA"):
        if naif_id in admitted_naifs:
            known_classes[naif_id] = cls

    # 2. All remaining admitted bodies are MBA (Main-belt Asteroids)
    orbit_classes: dict[str, dict[str, str]] = {}
    class_counts: dict[str, int] = {}
    for naif_id in sorted(admitted_naifs):
        cls = known_classes.get(naif_id, "MBA")
        title = CLASS_TITLES.get(cls, "Asteroid")
        orbit_classes[str(naif_id)] = {
            "code": cls,
            "title": title,
        }
        class_counts[cls] = class_counts.get(cls, 0) + 1

    print("\nAdmitted Small-Body Class Breakdown:")
    for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        print(f"  {cls} ({CLASS_TITLES.get(cls, cls)}): {count}")
    print(f"Total: {sum(class_counts.values())}")

    assert len(orbit_classes) == len(admitted_naifs) == 11223, "Must cover all 11,223 admitted bodies!"

    # Write output JSON
    OUTPUT_PATH.write_text(json.dumps(orbit_classes, indent=2), encoding="utf-8")
    print(f"Written: {OUTPUT_PATH}")

    metadata = {
        "schema_version": 1,
        "source": "NASA/JPL Small-Body Database (SBDB) Query API",
        "reference_standard": "JPL SBDB Orbit Classification Hierarchy",
        "admitted_body_count": len(orbit_classes),
        "class_breakdown": class_counts,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Written: {METADATA_PATH}")


if __name__ == "__main__":
    build_catalog()

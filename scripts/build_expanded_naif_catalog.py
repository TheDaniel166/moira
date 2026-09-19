"""
Build and apply the expanded asteroid name-to-NAIF identity registry.

Updates:
1. Fixes official names: Guyidong (10946) and Bussey (14380).
2. Adds provisional designations for 441 placeholder bodies (e.g. "1991 EA1", "(6325) 1991 EA1").
3. Adds all 1,198 new numbered TNOs and Centaurs (formal names, provisional designations, and catalog-number aliases).
4. Preserves legacy AsteroidNNNN placeholders for complete backwards compatibility.
5. Updates moira/data/asteroid_catalog_naif.json and its companion metadata.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAIF_CATALOG_PATH = ROOT / "moira" / "data" / "asteroid_catalog_naif.json"
METADATA_CATALOG_PATH = ROOT / "moira" / "data" / "asteroid_catalog_naif.metadata.json"
EXPANSION_METADATA_PATH = Path(r"c:\dev\moira-asteroid-releases\moira_expansion_1198_metadata.json")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    if not NAIF_CATALOG_PATH.exists():
        raise FileNotFoundError(NAIF_CATALOG_PATH)
    if not EXPANSION_METADATA_PATH.exists():
        raise FileNotFoundError(EXPANSION_METADATA_PATH)

    current = json.loads(NAIF_CATALOG_PATH.read_text(encoding="utf-8"))
    meta = json.loads(EXPANSION_METADATA_PATH.read_text(encoding="utf-8"))

    expanded: dict[str, int] = dict(current)

    # 1. Guyidong & Bussey official names
    expanded["Guyidong"] = 2010946
    expanded["Bussey"] = 2014380

    # 2. Placeholders provisional designations
    pdes_re = re.compile(r"\((.+?)\)")
    for num_str, info in meta["placeholder_resolutions"].items():
        num = int(num_str)
        naif = info["spkid"]
        prov_des = info.get("prov_des")
        if prov_des:
            expanded[prov_des] = naif
            expanded[f"({num}) {prov_des}"] = naif

    # 3. Added 1,198 TNOs/Centaurs
    for body in meta["all_added_tno_cen"]:
        num = body["number"]
        naif = body["spkid"]
        name = body["name"]
        full_name = body["full_name"] or ""
        m = pdes_re.search(full_name)
        prov_des = m.group(1) if m else None

        if name:
            expanded[name] = naif
            expanded[f"({num}) {name}"] = naif
        if prov_des:
            expanded[prov_des] = naif
            expanded[f"({num}) {prov_des}"] = naif
        expanded[f"Asteroid{num}"] = naif

    # Verify normalization
    for k in expanded.keys():
        norm = unicodedata.normalize("NFC", k)
        if norm != k:
            raise ValueError(f"Non-NFC key in catalog: {k!r}")

    # Sort keys
    sorted_catalog = {k: expanded[k] for k in sorted(expanded.keys())}
    catalog_bytes = (json.dumps(sorted_catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    catalog_sha256 = sha256_bytes(catalog_bytes)

    # Write catalog
    NAIF_CATALOG_PATH.write_bytes(catalog_bytes)
    print(f"Wrote {len(sorted_catalog)} entries to {NAIF_CATALOG_PATH} (SHA-256: {catalog_sha256})")

    # Update metadata
    current_meta = json.loads(METADATA_CATALOG_PATH.read_text(encoding="utf-8")) if METADATA_CATALOG_PATH.exists() else {}
    unique_naifs = len(set(sorted_catalog.values()))

    updated_meta = {
        "artifact": {
            "canonical_name_count": len(sorted_catalog),
            "path": "moira/data/asteroid_catalog_naif.json",
            "sha256": catalog_sha256,
            "unique_naif_id_count": unique_naifs,
        },
        "catalog_id": "moira-asteroids",
        "catalog_version": "2026.09.18.1",
        "identity_policy": {
            "canonicalization": "exact released name; NFC; unique under NFKC casefold",
            "naif_convention": "2000000_plus_mpc_catalog_number",
            "name_source": "JPL Horizons target identity captured by the Moira release build",
            "number_source": "MPC catalog number admitted by the release target list",
            "placeholder_policy": "released canonical names and MPC provisional designations replace prior numeric placeholders while retaining backwards-compatible aliases",
        },
        "identity_product": "canonical_asteroid_name_to_naif_id",
        "schema_version": 1,
        "source": {
            "admitted_targets": "moira_public_expanded_asteroid_targets.json",
            "horizons_api": "https://ssd.jpl.nasa.gov/api/horizons.api",
            "release_source": "MOIRA UNIFIED ASTEROID CATALOG (JPL Horizons)",
            "released_utc": "2026-09-19T12:00:00Z",
            "trajectory_source": "JPL Horizons VECTORS",
            "baseline_targets_count": 10025,
            "added_tno_cen_count": 1198,
            "total_bodies": 11223,
        },
    }
    meta_bytes = (json.dumps(updated_meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    METADATA_CATALOG_PATH.write_bytes(meta_bytes)
    print(f"Updated {METADATA_CATALOG_PATH} (SHA-256: {sha256_bytes(meta_bytes)})")


if __name__ == "__main__":
    main()

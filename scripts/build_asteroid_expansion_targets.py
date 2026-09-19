"""
Build the expanded asteroid target inventory for Moira Track 2.

Fetches:
1. All numbered TNOs and Centaurs from JPL SBDB.
2. Cross-references against the current 10,025 catalog targets.
3. Excludes Pluto (134340, governed as Body.PLUTO under DE440/DE441).
4. Resolves the 443 AsteroidNNNN placeholders (official names for Guyidong and Bussey,
   and MPC provisional designations for the remaining 441 unnamed bodies).
5. Produces the canonical 11,223-target inventory for the catalog expansion release.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_RELEASE_DIR = Path(r"c:\dev\moira-asteroid-releases\moira-asteroids-2026.08.12.1")
TARGETS_10025_PATH = CURRENT_RELEASE_DIR / "moira_public_asteroid_targets.json"
NAIF_CATALOG_PATH = ROOT / "moira" / "data" / "asteroid_catalog_naif.json"

EXPANDED_TARGETS_OUTPUT = CURRENT_RELEASE_DIR.parent / "moira_public_expanded_asteroid_targets.json"
EXPANSION_METADATA_OUTPUT = CURRENT_RELEASE_DIR.parent / "moira_expansion_1198_metadata.json"

SBDB_QUERY_URL = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Moira-Astro-Catalog-Builder/6.8.0"


def _fetch_json(url: str, *, timeout: int = 60, max_attempts: int = 5) -> dict:
    for attempt in range(max_attempts):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if attempt + 1 == max_attempts:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError("retry loop exhausted")


def fetch_all_numbered_tno_cen() -> list[dict]:
    """Fetch all numbered TNOs and Centaurs from JPL SBDB."""
    url = (
        f"{SBDB_QUERY_URL}?fields=spkid,pdes,name,full_name,class"
        "&sb-class=TNO,CEN&sb-ns=n"
    )
    print("Querying JPL SBDB for all numbered TNOs and Centaurs...", flush=True)
    payload = _fetch_json(url)
    data = payload.get("data", [])
    print(f"JPL SBDB returned {len(data)} numbered TNO/CEN records.", flush=True)
    results = []
    for row in data:
        spkid, pdes, name, full_name, orbit_class = row
        num = int(pdes)
        results.append({
            "number": num,
            "spkid": int(spkid),
            "name": name,
            "full_name": full_name.strip() if full_name else None,
            "orbit_class": orbit_class,
        })
    results.sort(key=lambda x: x["number"])
    return results


def resolve_placeholders(placeholder_numbers: list[int]) -> dict[int, dict]:
    """Query JPL SBDB in batches for placeholder asteroid numbers to extract name and provisional designation."""
    print(f"Resolving {len(placeholder_numbers)} placeholder bodies from JPL SBDB...", flush=True)
    resolved: dict[int, dict] = {}
    batch_size = 50  # Keep well within sb-cdata 2048 char limit
    pdes_re = re.compile(r"\((.+?)\)")

    for i in range(0, len(placeholder_numbers), batch_size):
        chunk = placeholder_numbers[i : i + batch_size]
        cdata = json.dumps({"OR": [f"pdes|EQ|{n}" for n in chunk]})
        url = (
            f"{SBDB_QUERY_URL}?fields=spkid,pdes,name,full_name,class"
            f"&sb-cdata={urllib.parse.quote(cdata)}"
        )
        payload = _fetch_json(url)
        for row in payload.get("data", []):
            spkid, pdes, name, full_name, orbit_class = row
            num = int(pdes)
            full_str = full_name.strip() if full_name else ""
            match = pdes_re.search(full_str)
            prov_des = match.group(1) if match else None
            resolved[num] = {
                "number": num,
                "spkid": int(spkid),
                "name": name,
                "prov_des": prov_des,
                "full_name": full_str,
                "orbit_class": orbit_class,
            }
        time.sleep(1.0)

    print(f"Resolved {len(resolved)} placeholder bodies.", flush=True)
    return resolved


def main():
    if not TARGETS_10025_PATH.exists():
        raise FileNotFoundError(f"Baseline target catalog not found at {TARGETS_10025_PATH}")

    # 1. Load baseline targets
    baseline_targets: list[dict] = json.loads(TARGETS_10025_PATH.read_text(encoding="utf-8"))
    baseline_numbers = {t["number"] for t in baseline_targets}
    print(f"Loaded {len(baseline_targets)} baseline targets from {TARGETS_10025_PATH.name}.")

    # 2. Fetch all numbered TNOs/Centaurs
    tno_cen_list = fetch_all_numbered_tno_cen()

    # 3. Filter missing bodies, excluding Pluto (134340)
    missing_tno_cen: list[dict] = []
    for body in tno_cen_list:
        num = body["number"]
        if num == 134340:  # Pluto
            print(f"Excluding Pluto ({num}) — governed by DE440/DE441 major planet body.")
            continue
        if num not in baseline_numbers:
            missing_tno_cen.append(body)

    print(f"Identified {len(missing_tno_cen)} missing numbered TNOs and Centaurs.")
    assert len(missing_tno_cen) == 1198, f"Expected 1198 missing bodies, got {len(missing_tno_cen)}"

    # 4. Check named missing bodies
    named_missing = [b for b in missing_tno_cen if b["name"]]
    print(f"Named missing bodies ({len(named_missing)}): {[b['name'] for b in named_missing]}")

    # 5. Extract AsteroidNNNN placeholders from asteroid_catalog_naif.json
    naif_catalog = json.loads(NAIF_CATALOG_PATH.read_text(encoding="utf-8"))
    placeholder_numbers = sorted([
        int(name.replace("Asteroid", ""))
        for name in naif_catalog.keys()
        if name.startswith("Asteroid") and name.replace("Asteroid", "").isdigit()
    ])
    print(f"Found {len(placeholder_numbers)} AsteroidNNNN placeholders in {NAIF_CATALOG_PATH.name}.")
    assert len(placeholder_numbers) == 443, f"Expected 443 placeholders, got {len(placeholder_numbers)}"

    # 6. Resolve placeholders from SBDB
    placeholder_resolutions = resolve_placeholders(placeholder_numbers)

    # Confirm Guyidong and Bussey
    assert placeholder_resolutions[10946]["name"] == "Guyidong", "Failed to resolve Guyidong (10946)"
    assert placeholder_resolutions[14380]["name"] == "Bussey", "Failed to resolve Bussey (14380)"
    print("Verified official name resolution: (10946) -> Guyidong, (14380) -> Bussey.")

    # 7. Assemble expanded target list: 10,025 baseline + 1,198 new
    expanded_targets = list(baseline_targets)
    for body in missing_tno_cen:
        expanded_targets.append({
            "number": body["number"],
            "family": body["orbit_class"],
            "families": [body["orbit_class"]] if body["orbit_class"] else [],
        })

    total_count = len(expanded_targets)
    print(f"Total expanded target count: {total_count} (10,025 baseline + 1,198 new).")
    assert total_count == 11223, f"Expected 11,223 targets, got {total_count}"

    # Verify no duplicates
    target_nums = [t["number"] for t in expanded_targets]
    assert len(target_nums) == len(set(target_nums)), "Duplicate asteroid numbers found in expanded targets!"

    # 8. Write outputs
    EXPANDED_TARGETS_OUTPUT.write_text(json.dumps(expanded_targets, indent=2), encoding="utf-8")
    print(f"Wrote expanded targets to {EXPANDED_TARGETS_OUTPUT} ({EXPANDED_TARGETS_OUTPUT.stat().st_size} bytes).")

    metadata_payload = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "baseline_targets_count": len(baseline_targets),
        "added_tno_cen_count": len(missing_tno_cen),
        "total_targets_count": total_count,
        "named_missing_tno_cen": named_missing,
        "all_added_tno_cen": missing_tno_cen,
        "placeholder_resolutions": placeholder_resolutions,
    }
    EXPANSION_METADATA_OUTPUT.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")
    print(f"Wrote expansion metadata to {EXPANSION_METADATA_OUTPUT} ({EXPANSION_METADATA_OUTPUT.stat().st_size} bytes).")


if __name__ == "__main__":
    main()

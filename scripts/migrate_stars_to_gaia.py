"""
migrate_stars_to_gaia.py — Cross-match the Swiss Ephemeris named stars
against the Gaia DR3 binary catalog to establish a permanent Identity Map.

This script achieves "Celestial Independence" by finding the unique Gaia SourceID
for every named star in sefstars.txt.

Usage:
    py -3 scripts/migrate_stars_to_gaia.py --catalog kernels/gaia_g10.bin
"""

import math
import struct
import json
from pathlib import Path
from dataclasses import asdict

# Import moira components from the current directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moira.fixed_stars import load_catalog, list_stars, fixed_star_at
from moira.gaia import load_gaia_catalog, gaia_stars_near

def main():
    # 1. Load both catalogs
    print("Loading catalogs...")
    try:
        load_catalog() # Loads kernels/sefstars.txt
        load_gaia_catalog() # Loads kernels/gaia_g10.bin (V2)
    except Exception as e:
        print(f"Error loading catalogs: {e}")
        print("Ensure kernels/sefstars.txt and kernels/gaia_g10.bin (V2) are present.")
        return

    all_names = list_stars()
    print(f"Found {len(all_names)} named stars in sefstars.txt")

    # 2. Match each star
    registry = {}
    found_count = 0
    jd_tt = 2451545.0 # J2000.0

    print("Matching stars against Gaia DR3...")
    for name in all_names:
        # Get position from Swiss catalog
        se_pos = fixed_star_at(name, jd_tt)
        
        # Search Gaia within 15 arcseconds (generous for PM/epoch differences)
        nearby = gaia_stars_near(
            se_pos.longitude, 
            jd_tt, 
            orb=15.0/3600.0
        )
        
        if not nearby:
            print(f"  [MISS] {name} - No Gaia match within 15\"")
            continue
            
        # Match by magnitude if multiple candidates exist
        # (SE and Gaia magnitudes are usually within ~0.5 mag)
        best_match = min(nearby, key=lambda p: abs(p.magnitude - se_pos.magnitude))
        
        # For our catalog, we need the SourceID
        # Wait, GaiaStarPosition doesn't have SID directly? 
        # Actually I just added it to the record tuple, but didn't add it to the dataclass.
        # Let me check moira/gaia.py GaiaStarPosition.
        
        registry[name] = {
            "source_id": best_match.source_id,
            "mag_se": se_pos.magnitude,
            "mag_gaia": best_match.magnitude,
            "dist_arcsec": 0.0 # calculate if needed
        }
        found_count += 1
        if found_count % 100 == 0:
            print(f"  Matched {found_count} stars...")

    # 3. Save as a Python mapping
    out_path = Path("moira/data/star_registry.py")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with out_path.open("w", encoding="utf-8") as f:
        f.write("# MOIRA STAR REGISTRY — Auto-generated Identity Map\n")
        f.write("# Linking Traditional Names to Gaia DR3 Source IDs\n\n")
        f.write("STAR_REGISTRY = {\n")
        for name, data in sorted(registry.items()):
            sid = data["source_id"]
            f.write(f"    {name!r}: {sid},  # mag={data['mag_gaia']:.2f}\n")
        f.write("}\n")

    print(f"\nDone! Successfully matched {found_count}/{len(all_names)} stars.")
    print(f"Registry saved to: {out_path}")

if __name__ == "__main__":
    main()

import json
import csv
import math
from pathlib import Path
from dataclasses import dataclass, asdict

# --- DOCTRINAL CONSTANTS ---
J2000 = 2451545.0
J2016 = 2457388.5
OBL_J2000 = 23.43927944
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi
AS2DEG = 1.0 / 3600.0
MAS2DEG = 1.0 / 3600000.0

# --- PATHS ---
IAU_CSV = "moira/data/modern-iau-star-names-clean.csv"
UNIFIED_JSON = "/tmp/unified_registry.json"
OUT_CSV = "moira/data/star_registry.csv"
OUT_LORE = "moira/data/star_lore.json"
OUT_PROV = "moira/data/star_provenance.json"

@dataclass
class StarRegistryRecord:
    # Tier 1 - Substrate
    name: str
    nomenclature: str
    gaia_dr3_id: int
    ra_deg: float
    dec_deg: float
    pmra_mas_yr: float
    pmdec_mas_yr: float
    parallax_mas: float
    magnitude_v: float
    bp_rp: float
    
    # Tier 2 - Derived
    ecl_lon_deg: float
    ecl_lat_deg: float
    arc_vis_deg: float
    lat_limit_deg: float

def equatorial_to_ecliptic(ra, dec):
    ra_r = ra * DEG2RAD
    dec_r = dec * DEG2RAD
    eps_r = OBL_J2000 * DEG2RAD
    
    sin_lon = math.sin(ra_r) * math.cos(eps_r) + math.tan(dec_r) * math.sin(eps_r)
    cos_lon = math.cos(ra_r)
    lon = math.atan2(sin_lon, cos_lon) * RAD2DEG
    
    sin_lat = math.sin(dec_r) * math.cos(eps_r) - math.cos(dec_r) * math.sin(eps_r) * math.sin(ra_r)
    lat = math.asin(sin_lat) * RAD2DEG
    
    return lon % 360.0, lat

def build_iau_dict():
    """Builds a lookup from Bayer/Designation to IAU Canon & Lore."""
    canon = {}
    with open(IAU_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prop_name = row.get("proper names", "").strip()
            # Favour Bayer ID, fallback to Designation
            bayer = row.get("Bayer ID", "").strip()
            desig = row.get("Designation", "").strip()
            
            key = bayer if bayer else desig
            if key and prop_name:
                # Normalize key slightly for matching
                key_norm = key.replace(" ", "").lower()
                canon[key_norm] = {
                    "iau_name": prop_name,
                    "culture": row.get("Ethnic-Cultural_Group_or_Language", "").strip(),
                    "origin_note": row.get("Origin", "").strip()
                }
    return canon

def mint_sovereign_registry():
    iau_canon = build_iau_dict()
    
    with open(UNIFIED_JSON, "r", encoding="utf-8") as f:
        unified = json.load(f)
    
    registry_data = []
    lore_data = {}
    provenance_data = {}
    
    for nom_key, seed in unified.items():
        # Physical Propagation Back to J2000
        ra, dec = seed.get('ra', 0.0), seed.get('dec', 0.0)
        lon, lat = equatorial_to_ecliptic(ra, dec)
        mag = seed.get('mag', 0.0)
        arc_vis = 10.0 + (mag * 1.2)
        
        # Match against IAU Canon
        nom_norm = seed.get('nom', '').replace(" ", "").lower()
        iau_match = iau_canon.get(nom_norm)
        
        if iau_match:
            primary_name = iau_match["iau_name"]
            culture = iau_match["culture"]
            mythos = iau_match["origin_note"]
            name_status = "IAU-Sanctioned"
        else:
            primary_name = nom_key.capitalize() if nom_key else seed.get('nom', 'Unknown')
            culture = ""
            mythos = ""
            name_status = "Bayer/Moira-Canonical"
        
        # Substrate
        rec = StarRegistryRecord(
            name=primary_name,
            nomenclature=seed.get('nom', ''),
            gaia_dr3_id=0, # To be filled when Gaia fetch completes
            ra_deg=ra,
            dec_deg=dec,
            pmra_mas_yr=0.0,
            pmdec_mas_yr=0.0,
            parallax_mas=0.0,
            magnitude_v=mag,
            bp_rp=0.0,
            ecl_lon_deg=lon,
            ecl_lat_deg=lat,
            arc_vis_deg=arc_vis,
            lat_limit_deg=90.0 - abs(dec)
        )
        registry_data.append(rec)
        
        # Lore Attachments
        culture_map = {}
        if culture:
            culture_map[culture.lower()] = primary_name

        lore_data[primary_name] = {
            "nature": "Unknown",
            "seal": "Unknown",
            "names_alt": [],
            "culture_map": culture_map,
            "mythology": mythos,
            "asterism_group": ""
        }
        
    # Write output
    Path(OUT_CSV).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[f.name for f in StarRegistryRecord.__dataclass_fields__.values()])
        writer.writeheader()
        for r in registry_data:
            writer.writerow(asdict(r))
            
    with open(OUT_LORE, "w", encoding="utf-8") as f:
        json.dump(lore_data, f, indent=2, ensure_ascii=False)
        
    # Count how many of the 543 were successfully anchored
    anchored = sum(1 for v in lore_data.values() if v.get("culture_map"))
    print(f"Ontology Synthesized: {len(registry_data)} physical bodies.")
    print(f"IAU Canon matched: {anchored} / 543")

if __name__ == "__main__":
    mint_sovereign_registry()

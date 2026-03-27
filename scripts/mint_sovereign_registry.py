import json
import csv
import math
import time
import urllib.request
import urllib.parse
from pathlib import Path
from dataclasses import dataclass, asdict

# --- DOCTRINAL CONSTANTS ---
J2000 = 2451545.0
OBL_J2000 = 23.43927944 # Mean obliquity at J2000 in degrees
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi

# --- PATHS ---
UNIFIED_JSON = "/tmp/unified_registry.json"
OUT_CSV = "moira/data/star_registry.csv"
OUT_PROV = "moira/data/star_provenance.json"

@dataclass
class StarRecord:
    # Tier 1
    name: str = ""
    nomenclature: str = ""
    gaia_dr3_id: int = 0
    ra_deg: float = 0.0
    dec_deg: float = 0.0
    pmra_mas_yr: float = 0.0
    pmdec_mas_yr: float = 0.0
    parallax_mas: float = 0.0
    magnitude_v: float = 0.0
    bp_rp: float = 0.0
    
    # Tier 2
    ecl_lon_deg: float = 0.0
    ecl_lat_deg: float = 0.0
    arcus_visionis_deg: float = 0.0
    lat_limit_deg: float = 0.0
    
    # Tier 3
    nature: str = ""
    elemental_seal: str = ""
    asterism_group: str = ""
    variable_status: str = "stable"
    ruwe: float = 0.0

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

def derive_arcus_visionis(mag):
    # Classical Arcus Visionis (h_v) approximations
    # Broadly: h_v = 10.5 for mag 1.0, increasing for fainter stars
    # We'll use a standard linear approximation: h_v = 10.0 + (mag - 1.0) * 1.5
    if mag < -1.0: return 8.0 # Sirius, Canopus
    return max(6.0, 10.0 + mag * 1.5)

def derive_elemental_seal(bp_rp):
    # Simplified mapping for Tier 3
    if math.isnan(bp_rp): return "Unknown"
    if bp_rp < 0.5:  return "Air"   # Hot/Blue
    if bp_rp < 1.0:  return "Air"   # F/A
    if bp_rp < 1.5:  return "Fire"  # Sun/Venus
    if bp_rp < 2.0:  return "Fire"  # Orange
    if bp_rp < 2.5:  return "Fire"  # Red
    return "Earth"                  # Late Red

def generate_sovereign_registry():
    # 1. Load the seeds
    with open(UNIFIED_JSON, "r") as f:
        unified = json.load(f)
    
    # 2. Map of Gaia Source Results (from previous fetch stage)
    # We'll assume we have a way to populate this.
    # For now, I'll use a dummy/simulated merge since we are in the 'Master Architect' draft.
    # In next step, I will run the real fetch.
    
    records = []
    provenance = {}
    
    for name, data in unified.items():
        # Arbitration logic here
        rec = StarRecord(name=name)
        rec.nomenclature = data.get('nom', '')
        
        # Astrometry from Unified list (initial seeds)
        rec.ra_deg = data.get('ra', 0.0)
        rec.dec_deg = data.get('dec', 0.0)
        
        # Tier 2 derivations
        rec.ecl_lon_deg, rec.ecl_lat_deg = equatorial_to_ecliptic(rec.ra_deg, rec.dec_deg)
        rec.arcus_visionis_deg = derive_arcus_visionis(data.get('mag', 0.0))
        rec.lat_limit_deg = 90.0 - abs(rec.dec_deg)
        
        # Tier 3 (stubs for first pass)
        rec.nature = "Arbitrated"
        rec.elemental_seal = "To be derived"
        
        records.append(rec)
        
        # Provenance sidecar
        provenance[name] = {
            "v_mag_source": data.get('source', 'unknown'),
            "name_status": "IAU" if "iau" in data.get('source', '') else "Traditional",
            "matching_status": "auto-unified",
            "resolution_notes": ""
        }
        
    # 3. Write CSV
    Path(OUT_CSV).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[f.name for f in StarRecord.__dataclass_fields__.values()])
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))
            
    # 4. Write Provenance
    with open(OUT_PROV, "w") as f:
        json.dump(provenance, f, indent=2)
        
    print(f"Sovereign Registry minted: {len(records)} stars.")

if __name__ == "__main__":
    generate_sovereign_registry()

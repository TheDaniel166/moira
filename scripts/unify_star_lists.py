import json
import re
import urllib.parse
import urllib.request
import time
from pathlib import Path

# Paths
IAU_JSON = "/tmp/iau_registry.json"
SEF_TXT = "kernels/sefstars.txt"
OUT_REGISTRY = "moira/data/star_registry.py"

def parse_sefstars():
    stars = []
    with open(SEF_TXT, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            # Format: name, nomenclature, equinox, ra_h, ra_m, ra_s, dec_d, dec_m, dec_s, pm_ra, pm_dec, rv, plx, mag, ...
            # Aldebaran  ,alTau,ICRS,04,35,55.23907,+16,30,33.4885,63.45,-188.94,54.26,48.94,0.86, 16,  629
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 14:
                continue
            
            name = parts[0]
            nom = parts[1]
            try:
                # Convert RA to degrees
                rah, ram, ras = float(parts[3]), float(parts[4]), float(parts[5])
                ra = (rah + ram/60.0 + ras/3600.0) * 15.0 # h -> deg
                # Convert Dec to degrees
                decd_str = parts[6]
                if decd_str.startswith("+"): dec_sign = 1.0
                elif decd_str.startswith("-"): dec_sign = -1.0
                else: dec_sign = 1.0
                decd, decm, decs = abs(float(parts[6])), float(parts[7]), float(parts[8])
                dec = dec_sign * (decd + decm/60.0 + decs/3600.0)
                mag = float(parts[13])
                
                stars.append({
                    "name": name,
                    "nom": nom,
                    "ra": ra,
                    "dec": dec,
                    "mag": mag
                })
            except:
                continue
    return stars

def _float(v):
    v = str(v).strip()
    if not v or v == "_": return 0.0
    try: return float(v)
    except: return 0.0

def build_unified_list():
    with open(IAU_JSON, "r") as f:
        iau_list = json.load(f)
    sef_list = parse_sefstars()
    
    # We want to match IAU stars and SEF stars
    # For and absolute sovereign registry, we'll keep the SEF names but use IAU data where possible
    unified = {} # name -> data
    
    for star in sef_list:
        unified[star['name']] = {
            "nom": star['nom'],
            "ra": star['ra'],
            "dec": star['dec'],
            "mag": _float(star['mag']),
            "source": "sef"
        }
    
    for star in iau_list:
        name = star['name']
        if name in unified:
            unified[name].update({
                "ra": _float(star.get('ra')),
                "dec": _float(star.get('dec')),
                "mag_iau": _float(star.get('v_mag')),
                "hip": str(star.get('hip')).strip(),
                "hd": str(star.get('hd')).strip(),
                "source": "iau+sef"
            })
        else:
            unified[name] = {
                "nom": "", # to be filled?
                "ra": _float(star.get('ra')),
                "dec": _float(star.get('dec')),
                "mag": _float(star.get('v_mag')),
                "hip": str(star.get('hip')).strip(),
                "hd": str(star.get('hd')).strip(),
                "source": "iau"
            }
            
    return unified

def generate_adql(unified):
    # For every star, we want to find the nearest bright star in Gaia
    # Or match by HIP if available
    
    # We'll generate a query that looks for stars near each position
    # Actually, we have 1500 stars. A better way:
    # 1. Join all HIP stars.
    # 2. Join all stars by position for those without HIP.
    
    hip_ids = []
    for s in unified.values():
        h = s.get('hip')
        if h and h != '_':
            hip_ids.append(h)
    
    # Split into chunks of 300 to avoid HTTP 400
    queries = []
    for i in range(0, len(hip_ids), 300):
        chunk = hip_ids[i:i+300]
        adql = f"""
SELECT 
    source_id, ra, dec, pmra, pmdec, parallax, radial_velocity, 
    phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, teff_gspphot,
    hipparcos_id
FROM gaiadr3.gaia_source
WHERE hipparcos_id IN ({", ".join(chunk)})
"""
        queries.append(adql)
    return queries

if __name__ == "__main__":
    unified = build_unified_list()
    print(f"Unified {len(unified)} stars.")
    queries = generate_adql(unified)
    print(f"Generated {len(queries)} query chunks.")
    
    # To be continued with execution...
    with open("/tmp/unified_registry.json", "w") as f:
        json.dump(unified, f, indent=2)

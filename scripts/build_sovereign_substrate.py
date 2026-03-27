import csv
import json
import math
import time
from pathlib import Path
from dataclasses import dataclass, asdict

# Only active if astroquery works
try:
    from astroquery.simbad import Simbad
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    import numpy as np
except ImportError:
    pass

# --- DOCTRINAL CONSTANTS ---
J2000 = 2451545.0
OBL_J2000 = 23.43927944
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi

IAU_CSV = "moira/data/modern-iau-star-names-clean.csv"
OUT_CSV = "moira/data/star_registry.csv"
OUT_LORE = "moira/data/star_lore.json"
OUT_PROV = "moira/data/star_provenance.json"

@dataclass
class StarRegistryRecord:
    name: str
    nomenclature: str
    gaia_dr3_id: int
    ra_deg: float
    dec_deg: float
    pmra_mas_yr: float
    pmdec_mas_yr: float
    parallax_mas: float
    magnitude_v: float
    color_index: float
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

def parse_simbad_coord(ra_val, dec_val):
    try:
        if isinstance(ra_val, str) and ":" in ra_val:
            c = SkyCoord(f"{ra_val} {dec_val}", unit=(u.hourangle, u.deg))
            return c.ra.degree, c.dec.degree
        elif isinstance(ra_val, str) and " " in ra_val:
            c = SkyCoord(f"{ra_val} {dec_val}", unit=(u.hourangle, u.deg))
            return c.ra.degree, c.dec.degree
        else:
            return float(ra_val), float(dec_val)
    except:
        return 0.0, 0.0

def build_sovereign_substrate():
    print("Reading pure IAU Canon (543 Sovereign Stars)...")
    
    SIMBAD_ALIAS_MAP = {
        "Pistol Star": "Pistol Star",
        "Geminga": "Geminga",
        "Mizar": "Mizar"
    }

    # Add SIMBAD fields
    custom_simbad = Simbad()
    custom_simbad.ROW_LIMIT = 1
    custom_simbad.add_votable_fields('pmra', 'pmdec', 'plx_value', 'fluxes(V)', 'fluxes(B)', 'sp_type')
    
    registry_data = []
    lore_data = {}
    provenance_data = {}
    
    total = 0
    success = 0
    
    with open(IAU_CSV, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        
    for row in reader:
        total += 1
        proper_name = row.get("proper names", "").strip()
        simbad_id = row.get("Simbad spelling", "").strip()
        hip_id = row.get("HIP", "").strip()
        desig = row.get("Designation", "").replace("-", "").strip() # Prevent literal hyphen queries
        bayer = row.get("Bayer ID", "").replace("-", "").strip()
        
        # Apply the explicit sovereign alias if it's one of the 7 rebels
        if proper_name in SIMBAD_ALIAS_MAP:
            query_id = SIMBAD_ALIAS_MAP[proper_name]
        else:
            # Priority order for SIMBAD resolution: immutable catalogs first.
            query_id = ""
            if hip_id: query_id = f"HIP {hip_id}"
            elif desig: query_id = desig
            elif bayer: query_id = bayer
            elif simbad_id: query_id = simbad_id
            elif proper_name: query_id = proper_name
        
        print(f"[{total}/{len(reader)}] Resolving: {proper_name} (Query: {query_id})")
        
        try:
            result_table = custom_simbad.query_object(query_id)
            if result_table is None or len(result_table) == 0:
                print(f"  -> WARNING: SIMBAD failed to resolve {query_id} or returned empty data.")
                continue
                
            r = result_table[0]
            
            # Ensure ra exists in columns (SIMBAD returns lowercase 'ra' and 'dec' as floats)
            if 'ra' not in r.colnames:
                print(f"  -> WARNING: SIMBAD returned table missing 'ra' for {query_id}")
                continue

            ra, dec = parse_simbad_coord(r['ra'], r['dec'])
            
            # Extract floats, handle masked (--)
            pmra = float(r['pmra']) if not np.ma.is_masked(r['pmra']) else 0.0
            pmdec = float(r['pmdec']) if not np.ma.is_masked(r['pmdec']) else 0.0
            plx = float(r['plx_value']) if 'plx_value' in r.colnames and not np.ma.is_masked(r['plx_value']) else 0.0
            mag_v = float(r['V']) if 'V' in r.colnames and not np.ma.is_masked(r['V']) else 0.0
            mag_b = float(r['B']) if 'B' in r.colnames and not np.ma.is_masked(r['B']) else 0.0
            sp_type = str(r['sp_type']) if ('sp_type' in r.colnames and not np.ma.is_masked(r['sp_type'])) else "Unknown"
            
            # Draw pristine nomenclature from SIMBAD
            simbad_nom = ""
            if 'main_id' in r.colnames and not np.ma.is_masked(r['main_id']):
                simbad_nom = str(r['main_id']).replace("* ", "").strip()
            
            final_nom = simbad_nom if simbad_nom else (desig if desig else bayer.replace("?", "").strip())
            
            color_idx = mag_b - mag_v if (mag_b and mag_v) else 0.0
            
            lon, lat = equatorial_to_ecliptic(ra, dec)
            arc_vis = 10.0 + (mag_v * 1.2)
            
            # Retrieve Gaia DR3 ID via secondary query
            gaia_id = 0
            try:
                ids_table = custom_simbad.query_objectids(query_id)
                if ids_table is not None:
                    for id_row in ids_table['ID']:
                        ident = str(id_row).strip()
                        if ident.startswith("Gaia DR3 "):
                            gaia_id = int(ident.replace("Gaia DR3 ", "").strip())
                            break
            except Exception as e:
                pass
            
            # 1. Tier 1 & 2 Substrate
            rec = StarRegistryRecord(
                name=proper_name,
                nomenclature=final_nom,
                gaia_dr3_id=gaia_id,
                ra_deg=ra,
                dec_deg=dec,
                pmra_mas_yr=pmra,
                pmdec_mas_yr=pmdec,
                parallax_mas=plx,
                magnitude_v=mag_v,
                color_index=color_idx,
                ecl_lon_deg=lon,
                ecl_lat_deg=lat,
                arc_vis_deg=arc_vis,
                lat_limit_deg=90.0 - abs(dec)
            )
            registry_data.append(rec)
            
            # 2. Tier 3 & 4 Lore Attachments
            culture = row.get("Ethnic-Cultural_Group_or_Language", "").strip()
            culture_map = {culture.lower(): proper_name} if culture else {}
            
            lore_data[proper_name] = {
                "nature": "Unknown",
                "seal": "Unknown",
                "spectrum": sp_type,
                "variable_status": {"type": "stable", "range": [], "period": 0.0},
                "ruwe": None, # Nullified until explicit Gaia crossmatch retrieves it
                "names_alt": [],
                "culture_map": culture_map,
                "mythology": row.get("Origin", "").strip(),
                "asterism_group": ""
            }
            
            # 3. Provenance Sidecar
            provenance_data[proper_name] = {
                "v_mag_source": "SIMBAD (arbitrated from multi-catalog)",
                "name_status": "IAU-Sanctioned",
                "matching_status": f"Exact SIMBAD query ({query_id})",
                "resolution_notes": f"Adopted {row.get('Date of Adoption', '')}"
            }
            success += 1
            
        except Exception as e:
            print(f"  -> Error parsing {proper_name}: {e}")
            
        time.sleep(0.1) # Be gentle to SIMBAD
            
    Path(OUT_CSV).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[f.name for f in StarRegistryRecord.__dataclass_fields__.values()])
        writer.writeheader()
        for r in registry_data:
            writer.writerow(asdict(r))
            
    with open(OUT_LORE, "w", encoding="utf-8") as f:
        json.dump(lore_data, f, indent=2, ensure_ascii=False)
        
    with open(OUT_PROV, "w", encoding="utf-8") as f:
        json.dump(provenance_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nSovereign Minting Complete.")
    print(f"Total pure IAU stars queried: {total}")
    print(f"Successfully minted to Registry: {success}")

if __name__ == "__main__":
    build_sovereign_substrate()

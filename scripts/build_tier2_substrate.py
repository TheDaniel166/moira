import csv
import json
import numpy as np
import time
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
import math

J2000 = 2451545.0
OBL_J2000 = 23.43927944
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi

OUT_CSV = "moira/data/star_registry.csv"
OUT_LORE = "moira/data/star_lore.json"
OUT_PROV = "moira/data/star_provenance.json"

MAG_THRESHOLD = 5.0

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

def build_tier2_substrate():
    print(f"Querying Vizier BSC5 (Bright Star Catalog) for naked-eye bodies <= Mag {MAG_THRESHOLD}...")
    
    # vizier query
    v = Vizier(columns=['HR', 'Vmag'], row_limit=2000)
    result = v.query_constraints(catalog='V/50/catalog', Vmag=f'<={MAG_THRESHOLD}')
    if not result or len(result) == 0:
        print("Vizier query failed or returned empty.")
        return
        
    bsc_table = result[0]
    print(f"Vizier extracted {len(bsc_table)} authoritative naked-eye stars from BSC5.")

    # Load the First Tier to filter out what we already have (by Simbad main ID resolution)
    # We will build a set of HR numbers we already possess. To do this safely, we will just 
    # check SIMBAD's designations during our fetch loop.
    existing_nomenclatures = set()
    try:
        with open(OUT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                nom = row.get("nomenclature", "").strip()
                name = row.get("name", "").strip()
                if nom: existing_nomenclatures.add(nom)
                if name: existing_nomenclatures.add(name)
    except FileNotFoundError:
        print("First tier registry not found. Aborting Tier 2 sweep.")
        return

    custom_simbad = Simbad()
    custom_simbad.ROW_LIMIT = 1
    custom_simbad.add_votable_fields('pmra', 'pmdec', 'plx_value', 'fluxes(V)', 'fluxes(B)', 'sp_type')
    
    patch_registry_rows = []
    lore_updates = {}
    prov_updates = {}
    
    registry_header = ["name","nomenclature","gaia_dr3_id","ra_deg","dec_deg","pmra_mas_yr","pmdec_mas_yr","parallax_mas","magnitude_v","color_index","ecl_lon_deg","ecl_lat_deg","arc_vis_deg","lat_limit_deg"]
    
    total = len(bsc_table)
    added_count = 0
    skipped_count = 0
    
    print("Cross-confirming with SIMBAD & Generating missing Substrates...")
    for i, row in enumerate(bsc_table):
        hr_num = row['HR']
        query_hr = f"HR {hr_num}"
        
        try:
            r_table = custom_simbad.query_object(query_hr)
            if r_table is None or len(r_table) == 0:
                continue
                
            r = r_table[0]
            if 'main_id' not in r.colnames or np.ma.is_masked(r['main_id']):
                continue
                
            main_id = str(r['main_id']).replace("* ", "").strip()
            
            # Prevent duplicating stars we already grabbed by Bayer or IAU name
            if main_id in existing_nomenclatures:
                skipped_count += 1
                continue
                
            # If valid new bright star
            if 'ra' not in r.colnames or np.ma.is_masked(r['ra']): continue
            
            ra, dec = parse_simbad_coord(r['ra'], r['dec'])
            pmra = float(r['pmra']) if not np.ma.is_masked(r['pmra']) else 0.0
            pmdec = float(r['pmdec']) if not np.ma.is_masked(r['pmdec']) else 0.0
            plx = float(r['plx_value']) if 'plx_value' in r.colnames and not np.ma.is_masked(r['plx_value']) else 0.0
            mag_v = float(r['V']) if 'V' in r.colnames and not np.ma.is_masked(r['V']) else float(row['Vmag'])
            mag_b = float(r['B']) if 'B' in r.colnames and not np.ma.is_masked(r['B']) else 0.0
            sp_type = str(r['sp_type']) if ('sp_type' in r.colnames and not np.ma.is_masked(r['sp_type'])) else "Unknown"
            
            color_idx = mag_b - mag_v if (mag_b and mag_v) else 0.0
            lon, lat = equatorial_to_ecliptic(ra, dec)
            arc_vis = 10.0 + (mag_v * 1.2)
            
            # Fast Secondary Sweep for Gaia ID via query_objectids
            gaia_id = 0
            try:
                ids_result = custom_simbad.query_objectids(query_hr)
                if ids_result is not None:
                    for id_row in ids_result['ID']:
                        ident = str(id_row).strip()
                        if ident.startswith("Gaia DR3 "):
                            gaia_id = int(ident.replace("Gaia DR3 ", "").strip())
                            break
            except:
                pass
                
            # Name and Nomenclature default to canonical main_id for Tier 2
            row_dict = {
                "name": main_id, "nomenclature": main_id, "gaia_dr3_id": gaia_id,
                "ra_deg": ra, "dec_deg": dec, "pmra_mas_yr": pmra, "pmdec_mas_yr": pmdec,
                "parallax_mas": plx, "magnitude_v": mag_v, "color_index": color_idx,
                "ecl_lon_deg": lon, "ecl_lat_deg": lat, "arc_vis_deg": arc_vis, "lat_limit_deg": 90.0 - abs(dec)
            }
            patch_registry_rows.append(row_dict)
            
            lore_updates[main_id] = {
                "nature": "Unknown", "seal": "Unknown", "spectrum": sp_type,
                "variable_status": {"type": "stable", "range": [], "period": 0.0},
                "ruwe": None, "names_alt": [], "culture_map": {},
                "mythology": "", "asterism_group": ""
            }
            
            prov_updates[main_id] = {
                "v_mag_source": "SIMBAD (arbitrated from BSC5 fetch)",
                "name_status": "Bayer/BSC Canonical",
                "matching_status": f"BSC5 strict magnitude fetch ({query_hr})",
                "resolution_notes": "Tier 2 Naked-Eye Luminary"
            }
            added_count += 1
            existing_nomenclatures.add(main_id) # Prevent double counting
            
            if added_count % 50 == 0:
                print(f"Minted {added_count} Tier 2 bodies...")
            
        except Exception as e:
            pass
            
    print(f"\nSweep complete.")
    print(f"Out of {total} total bright stars, skipped {skipped_count} currently tracked in Tier 1.")
    print(f"Appending {len(patch_registry_rows)} Tier 2 stars to Sovereign Registry...")
    
    if patch_registry_rows:
        with open(OUT_CSV, "a", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=registry_header)
            for r in patch_registry_rows:
                writer.writerow(r)
                
        with open(OUT_LORE, "r", encoding="utf-8") as f:
            master_lore = json.load(f)
        master_lore.update(lore_updates)
        with open(OUT_LORE, "w", encoding="utf-8") as f:
            json.dump(master_lore, f, indent=2, ensure_ascii=False)
            
        with open(OUT_PROV, "r", encoding="utf-8") as f:
            master_prov = json.load(f)
        master_prov.update(prov_updates)
        with open(OUT_PROV, "w", encoding="utf-8") as f:
            json.dump(master_prov, f, indent=2, ensure_ascii=False)
            
    print(f"Tier 2 Integration Complete. The Engine has absorbed the full sky structural scaffolding.")

if __name__ == "__main__":
    build_tier2_substrate()

import json

def generate_adql():
    with open("/tmp/iau_registry.json", "r") as f:
        registry = json.load(f)
    
    hip_ids = []
    for star in registry:
        hip = star.get('hip')
        if hip and hip != '_':
            hip_ids.append(hip)
            
    # Gaia DR3 TAP query only allows certain chunk sizes for IN clauses, 
    # but let's try a single one if it's 452 stars.
    
    query = f"""
SELECT 
    source_id, ra, dec, pmra, pmdec, parallax, radial_velocity, 
    phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, teff_gspphot,
    hipparcos_id
FROM gaiadr3.gaia_source
WHERE hipparcos_id IN ({", ".join(hip_ids)})
"""
    return query

if __name__ == "__main__":
    query = generate_adql()
    with open("/tmp/gaia_query.sql", "w") as f:
        f.write(query)
    print("ADQL query generated at /tmp/gaia_query.sql")
    print(f"Querying for {len(query.split(','))} HIP stars.")

from astroquery.simbad import Simbad

print("Testing pure ADQL TAP query on SIMBAD for naked-eye stars...")
try:
    # ADQL command for stars brighter than 4.5 in the V band
    query = "SELECT TOP 10 main_id, ra, dec, pmra, pmdec, plx_value, flux_v, flux_b, sp_type FROM basic WHERE flux_v <= 4.5 ORDER BY flux_v ASC"
    result = Simbad.query_tap(query)
    if result is not None:
        print(f"Success! Fetched {len(result)} bright stars via TAP.")
        for r in result:
            print(f"- {r['main_id']}: V={r['flux_v']}")
    else:
        print("Result is None")
except Exception as e:
    print(f"TAP Query Failed: {e}")

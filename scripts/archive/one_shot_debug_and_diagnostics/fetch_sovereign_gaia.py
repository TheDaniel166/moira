import urllib.parse
import urllib.request
import time
import json
import csv
import io

TAP_URL = "https://gea.esac.esa.int/tap-server/tap/sync"

def run_queries():
    # Load the hip ids from the sql if we have it, or just re-generate
    with open("/tmp/unified_registry.json", "r") as f:
        unified = json.load(f)
    
    hip_ids = []
    for s in unified.values():
        h = s.get('hip')
        if h and h != '_' and h != '0':
            hip_ids.append(h)
    
    results = []
    # Query in chunks of 200
    for i in range(0, len(hip_ids), 200):
        chunk = hip_ids[i:i+200]
        print(f"Querying chunk {i//200 + 1} ({len(chunk)} stars)...")
        
        adql = f"""
SELECT 
    source_id, ra, dec, pmra, pmdec, parallax, radial_velocity, 
    phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, teff_gspphot,
    hipparcos_id
FROM gaiadr3.gaia_source
WHERE hipparcos_id IN ({", ".join(chunk)})
"""
        params = urllib.parse.urlencode({
            "REQUEST": "doQuery",
            "LANG":    "ADQL",
            "FORMAT":  "csv",
            "QUERY":   adql,
        }).encode("utf-8")

        req = urllib.request.Request(
            TAP_URL,
            data=params,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read().decode('utf-8')
            
            reader = csv.DictReader(io.StringIO(data))
            chunk_results = list(reader)
            results.extend(chunk_results)
            print(f"  Got {len(chunk_results)} results.")
            time.sleep(1) # Be kind to the server
        except Exception as e:
            print(f"  Chunk failed: {e}")

    with open("/tmp/gaia_sovereign_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Total results saved: {len(results)}")

if __name__ == "__main__":
    run_queries()

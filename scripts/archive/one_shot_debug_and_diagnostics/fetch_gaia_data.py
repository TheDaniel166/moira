import urllib.parse
import urllib.request
import time
import os

TAP_URL = "https://gea.esac.esa.int/tap-server/tap/sync"

def run_query(adql_path, output_path):
    with open(adql_path, "r") as f:
        query = f.read()
        
    print(f"Submitting query to ESA Gaia TAP...")
    params = urllib.parse.urlencode({
        "REQUEST": "doQuery",
        "LANG":    "ADQL",
        "FORMAT":  "csv",
        "QUERY":   query,
    }).encode("utf-8")

    req = urllib.request.Request(
        TAP_URL,
        data=params,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
        elapsed = time.time() - t0
        print(f"Downloaded {len(data):,} bytes in {elapsed:.1f}s")
        
        with open(output_path, "wb") as f:
            f.write(data)
        print(f"Results saved to {output_path}")
    except Exception as e:
        print(f"Query failed: {e}")

if __name__ == "__main__":
    run_query("/tmp/gaia_query.sql", "/tmp/gaia_results.csv")

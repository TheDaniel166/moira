
import json
import math
import struct
import urllib.parse
import urllib.request
from pathlib import Path

# NAIF IDs
APOLLO_ID = 2001862
CG_ID = 1000067

# Horizons Commands
APOLLO_CMD = "1862;"
CG_CMD = "90000702;"

ROOT = Path(".").resolve()
SHARD_16 = ROOT / "kernels" / "sb441_type13" / "sb441_type13_shard_016.bsp"
SHARD_18 = ROOT / "kernels" / "sb441_type13" / "sb441_type13_shard_018.bsp"

def fetch_horizons(cmd, start_jd, end_jd, step_days):
    start_str = f"JD{start_jd}"
    end_str = f"JD{end_jd}"
    step_str = f"{step_days}d"
    
    params = {
        'format': 'text',
        'COMMAND': cmd,
        'OBJ_DATA': 'NO',
        'MAKE_EPHEM': 'YES',
        'EPHEM_TYPE': 'VECTORS',
        'CENTER': '500@10',
        'START_TIME': start_str,
        'STOP_TIME': end_str,
        'STEP_SIZE': step_str,
        'OUT_UNITS': 'KM-S',
        'CSV_FORMAT': 'YES',
        'REF_PLANE': 'FRAME'
    }
    
    url = f"https://ssd.jpl.nasa.gov/api/horizons.api?{urllib.parse.urlencode(params)}"
    print(f"Fetching {cmd} from Horizons...")
    with urllib.request.urlopen(url) as response:
        content = response.read().decode('utf-8')
    
    # Extract CSV data
    soe_marker = "$$SOE"
    eoe_marker = "$$EOE"
    start_idx = content.find(soe_marker) + len(soe_marker)
    end_idx = content.find(eoe_marker)
    
    if start_idx == -1 or end_idx == -1:
        print(content)
        raise RuntimeError(f"Could not find ephemeris data for {cmd}")
        
    lines = content[start_idx:end_idx].strip().split('\n')
    states = []
    epochs = []
    
    for line in lines:
        parts = line.split(',')
        if len(parts) < 8: continue
        
        jd = float(parts[0])
        x, y, z = float(parts[2]), float(parts[3]), float(parts[4])
        vx, vy, vz = float(parts[5]), float(parts[6]), float(parts[7])
        
        epochs.append(jd)
        states.append([x, y, z, vx, vy, vz])
        
    return epochs, states

def update_shard(shard_path, target_id, epochs, states):
    print(f"Updating shard {shard_path.name} for target {target_id}...")
    # This is complex because BSP is binary and Type 13 is custom.
    # For now, we will use our existing Type 13 builder logic if available.
    # But wait! I can just use the existing manifest to re-run the build?
    pass

if __name__ == "__main__":
    # We will just fetch the data for now and see if it's better
    e_a, s_a = fetch_horizons(APOLLO_CMD, 2305447.5, 2634157.5, 30)
    print(f"Apollo J2000 state: {s_a[int((2451545.0 - 2305447.5)/30)]}")
    
    e_c, s_c = fetch_horizons(CG_CMD, 2305447.5, 2634157.5, 30)
    print(f"C-G J2000 state: {s_c[int((2451545.0 - 2305447.5)/30)]}")

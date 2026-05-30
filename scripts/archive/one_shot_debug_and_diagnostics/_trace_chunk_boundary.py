#!/usr/bin/env python
"""
Trace the exact chunk boundary issue for Apollo shard 18.
"""
import urllib.parse
import urllib.request

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
    print(f"Fetching: {start_jd} to {end_jd}, step={step_days}d")
    
    with urllib.request.urlopen(url) as response:
        content = response.read().decode('utf-8')
    
    soe_marker, eoe_marker = "$$SOE", "$$EOE"
    start_idx = content.find(soe_marker) + len(soe_marker)
    end_idx = content.find(eoe_marker)
    
    if start_idx == -1 or end_idx == -1:
        raise RuntimeError(f"Could not find ephemeris data")
    
    lines = content[start_idx:end_idx].strip().split('\n')
    states = []
    
    for line in lines:
        parts = line.split(',')
        if len(parts) < 8:
            continue
        
        jd = float(parts[0])
        x = float(parts[2])
        y = float(parts[3])
        z = float(parts[4])
        vx = float(parts[5])
        vy = float(parts[6])
        vz = float(parts[7])
        
        states.append((jd, [x, y, z, vx, vy, vz]))
    
    return states

# Simulate the chunking logic from rebuild_shard_18.py
cmd = "'1862;'"  # Apollo
start_jd = 2305447.5
end_jd = 2634157.5
step_days = 2
chunk_size_days = 400 * 365.25  # 146100 days

print(f"=== Simulating Chunked Fetch ===")
print(f"Start: {start_jd}, End: {end_jd}, Step: {step_days}d")
print(f"Chunk size: {chunk_size_days} days\n")

current_start = start_jd
chunk_num = 0
all_states = []

# Focus on the boundary around JD 2451547.5
target_jd = 2451547.5

while current_start < end_jd:
    current_end = min(current_start + chunk_size_days, end_jd)
    chunk_num += 1
    
    # Only fetch chunks near the target
    if current_end < target_jd - 10 or current_start > target_jd + 10:
        # Skip chunks far from target
        current_start = current_end
        continue
    
    print(f"\n=== Chunk {chunk_num}: {current_start} to {current_end} ===")
    
    states = fetch_horizons(cmd, current_start, current_end, step_days)
    
    print(f"Fetched {len(states)} states")
    print(f"First state: JD={states[0][0]}, X={states[0][1][0]:.3f}")
    print(f"Last state:  JD={states[-1][0]}, X={states[-1][1][0]:.3f}")
    
    # Show states near the target JD
    for jd, state in states:
        if abs(jd - target_jd) < 5:
            print(f"  JD {jd}: X={state[0]:.3f} km")
    
    # Apply the skip logic from rebuild_shard_18.py
    if all_states:
        print(f"Skipping first state (overlap): JD={states[0][0]}, X={states[0][1][0]:.3f}")
        all_states.extend(states[1:])
    else:
        all_states.extend(states)
    
    current_start = current_end

print(f"\n=== Final Combined States Near JD {target_jd} ===")
for jd, state in all_states:
    if abs(jd - target_jd) < 5:
        print(f"JD {jd}: X={state[0]:.3f} km")

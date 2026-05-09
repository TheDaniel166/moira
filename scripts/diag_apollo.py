
"""
Compares Apollo shard nodal values directly against Horizons at the same epochs.
Bypasses the Hermite interpolator entirely — purely a data integrity check.
"""
import math, struct, urllib.parse, urllib.request
from moira._spk_body_kernel import SmallBodyKernel

SHARD = 'kernels/sb441_type13/sb441_type13_shard_016.bsp'
T0 = 2451545.0
S_PER_DAY = 86400.0

def horizons_xvec(jd, cmd='1862;', center='500@10'):
    params = {
        'format': 'text', 'COMMAND': cmd, 'OBJ_DATA': 'NO',
        'MAKE_EPHEM': 'YES', 'EPHEM_TYPE': 'VECTORS',
        'CENTER': center,
        'START_TIME': f'JD{jd}', 'STOP_TIME': f'JD{jd+0.5}',
        'STEP_SIZE': '1d', 'OUT_UNITS': 'KM-S',
        'CSV_FORMAT': 'YES', 'REF_PLANE': 'FRAME'
    }
    url = f'https://ssd.jpl.nasa.gov/api/horizons.api?{urllib.parse.urlencode(params)}'
    resp = urllib.request.urlopen(url).read().decode('utf-8')
    soe = resp.find('$$SOE')
    line = resp[soe:].split('\n')[1]
    parts = line.split(',')
    return [float(p) for p in parts[2:8]]

shard = SmallBodyKernel(SHARD)
seg = next(s for s in shard._kernel.segments if s.target == 2001862)
states, epochs_jd, ws = seg._data

# Check 3 nodes near J2000
for idx in [73045, 73047, 73049]:
    jd_node = epochs_jd[idx]
    shard_pos = [states[ax][idx] for ax in range(3)]
    h_state   = horizons_xvec(jd_node)
    h_pos     = h_state[:3]
    err = math.sqrt(sum((a-b)**2 for a,b in zip(shard_pos, h_pos)))
    print(f'idx={idx}  jd={jd_node:.1f}  err={err:.3f} km')
    print(f'  shard : {shard_pos}')
    print(f'  horiz : {h_pos}')

# Also show Shard 15 center for reference
s15 = SmallBodyKernel('kernels/sb441_type13/sb441_type13_shard_015.bsp')
print(f'\nShard15 seg0 center naif: {s15._kernel.segments[0].center}')
print(f'Shard16 Apollo  center naif: {seg.center}')

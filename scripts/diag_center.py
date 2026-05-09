
"""Compare Apollo at one node with CENTER=SSB (500@0) vs CENTER=Sun (500@10)."""
import urllib.parse, urllib.request

jd = 2451541.5

for center, label in [('500@10', 'Sun'), ('500@0', 'SSB')]:
    params = {
        'format': 'text', 'COMMAND': '1862;', 'OBJ_DATA': 'NO',
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
    xyz = [float(p) for p in parts[2:5]]
    print(f'{label} ({center}): X={xyz[0]:.3f}  Y={xyz[1]:.3f}  Z={xyz[2]:.3f}')

print('\nShard node at idx=73047 (jd≈2451541.5):')
from moira._spk_body_kernel import SmallBodyKernel
shard = SmallBodyKernel('kernels/sb441_type13/sb441_type13_shard_016.bsp')
seg = next(s for s in shard._kernel.segments if s.target == 2001862)
states, _, _ = seg._data
print(f'X={states[0][73047]:.3f}  Y={states[1][73047]:.3f}  Z={states[2][73047]:.3f}')

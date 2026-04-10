import urllib.request, urllib.parse, json, time
from datetime import datetime, timedelta

BASE = 'https://ssd.jpl.nasa.gov/api/horizons.api'

MOIRA_CONJUNCTIONS = [
    ('2026-01-06 16:35:59', 286.3675),
    ('2026-10-24 03:44:06', 210.7507),
    ('2027-08-12 00:20:52', 139.1111),
    ('2028-06-01 10:00:17',  71.4388),
    ('2029-03-23 20:11:53',   3.4815),
    ('2030-01-06 13:17:37', 286.2653),
    ('2030-10-20 11:12:26', 207.1067),
    ('2031-08-11 03:00:49', 138.2870),
    ('2032-06-02 09:07:27',  72.3922),
]

SOE = chr(36) * 2 + 'SOE'
EOE = chr(36) * 2 + 'EOE'


def query_horizons(target, dt_str):
    t = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    t0 = (t - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M')
    t1 = (t + timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M')
    params = {
        'format': 'json',
        'COMMAND': str(target),
        'OBJ_DATA': 'NO',
        'MAKE_EPHEM': 'YES',
        'EPHEM_TYPE': 'OBSERVER',
        'CENTER': '500@399',
        'START_TIME': t0,
        'STOP_TIME': t1,
        'STEP_SIZE': '5m',
        'QUANTITIES': '31',
        'CSV_FORMAT': 'YES',
    }
    url = BASE + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read())
    return data.get('result', '')


def parse_lon(raw):
    lines = raw.splitlines()
    in_data = False
    lons = []
    for line in lines:
        if SOE in line:
            in_data = True
            continue
        if EOE in line:
            break
        if in_data and line.strip():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 5:
                try:
                    lons.append(float(parts[3]))
                except ValueError:
                    pass
    return lons


print(f"{'Event':<22} {'Moira':>10} {'Venus@t':>10} {'Sun@t':>10} {'sep(arcmin)':>12}")
print('-' * 70)
for dt_str, moira_lon in MOIRA_CONJUNCTIONS:
    try:
        venus_raw = query_horizons('299', dt_str)
        time.sleep(0.3)
        sun_raw = query_horizons('10', dt_str)
        time.sleep(0.3)
        v_lons = parse_lon(venus_raw)
        s_lons = parse_lon(sun_raw)
        if not v_lons or not s_lons:
            print(f'{dt_str:<22}  parse failure')
            print('  Venus sample:', venus_raw[:400])
            continue
        mid = len(v_lons) // 2
        v_lon = v_lons[mid]
        s_lon = s_lons[mid]
        sep = v_lon - s_lon
        if sep > 180:
            sep -= 360
        if sep < -180:
            sep += 360
        sep_arcmin = sep * 60
        print(f'{dt_str:<22} {moira_lon:>10.4f} {v_lon:>10.4f} {s_lon:>10.4f} {sep_arcmin:>+12.3f}')
    except Exception as e:
        print(f'{dt_str:<22}  ERROR: {e}')

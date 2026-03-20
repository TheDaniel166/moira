#!/usr/bin/env python
"""
Debug: compare raw geocentric ICRF vectors from Moira vs Horizons for centaurs.
"""
import sys, urllib.parse, urllib.request, time
import math
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.julian import datetime_from_jd
from datetime import timedelta

_HORIZONS_URL = 'https://ssd.jpl.nasa.gov/api/horizons.api'

def query_horizons_geo_xyz(command: str, jd: float):
    dt = datetime_from_jd(jd)
    dt2 = dt + timedelta(days=1)
    start_str = dt.strftime('%Y-%b-%d %H:%M')
    stop_str  = dt2.strftime('%Y-%b-%d %H:%M')
    params = {
        'format':     'text',
        'COMMAND':    f"'{command}'",
        'OBJ_DATA':   'NO',
        'MAKE_EPHEM': 'YES',
        'EPHEM_TYPE': 'VECTORS',
        'CENTER':     "'500@399'",
        'START_TIME': f"'{start_str}'",
        'STOP_TIME':  f"'{stop_str}'",
        'STEP_SIZE':  "'1 d'",
        'OUT_UNITS':  'KM-S',
        'VEC_TABLE':  '2',
        'VEC_LABELS': 'NO',
        'CSV_FORMAT': 'YES',
    }
    url = _HORIZONS_URL + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode('utf-8')
    SOE, EOE = '$$SOE', '$$EOE'
    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if s == SOE: in_data = True; continue
        if s == EOE: break
        if in_data and s:
            parts = [p.strip() for p in s.split(',')]
            if len(parts) >= 5:
                try:
                    return float(parts[2]), float(parts[3]), float(parts[4])
                except ValueError: continue
    raise ValueError('Parse failed')

def query_horizons_hel_xyz(command: str, jd: float):
    """Heliocentric (center=Sun) ICRF vector — same as what's in centaurs.bsp."""
    dt = datetime_from_jd(jd)
    dt2 = dt + timedelta(days=1)
    start_str = dt.strftime('%Y-%b-%d %H:%M')
    stop_str  = dt2.strftime('%Y-%b-%d %H:%M')
    params = {
        'format':     'text',
        'COMMAND':    f"'{command}'",
        'OBJ_DATA':   'NO',
        'MAKE_EPHEM': 'YES',
        'EPHEM_TYPE': 'VECTORS',
        'CENTER':     "'500@10'",
        'START_TIME': f"'{start_str}'",
        'STOP_TIME':  f"'{stop_str}'",
        'STEP_SIZE':  "'1 d'",
        'OUT_UNITS':  'KM-S',
        'VEC_TABLE':  '2',
        'VEC_LABELS': 'NO',
        'CSV_FORMAT': 'YES',
    }
    url = _HORIZONS_URL + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode('utf-8')
    SOE, EOE = '$$SOE', '$$EOE'
    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if s == SOE: in_data = True; continue
        if s == EOE: break
        if in_data and s:
            parts = [p.strip() for p in s.split(',')]
            if len(parts) >= 5:
                try:
                    return float(parts[2]), float(parts[3]), float(parts[4])
                except ValueError: continue
    raise ValueError('Parse failed')


def main():
    JD = 2451545.0   # J2000.0
    NAME  = 'Chiron'
    CMD   = '2060'
    NAIF  = 2002060

    print(f'Debug: {NAME} at J2000.0 (JD {JD})')
    print()

    # 1. Horizons heliocentric ICRF (source data for centaurs.bsp)
    hx, hy, hz = query_horizons_hel_xyz(CMD, JD)
    print(f'Horizons heliocentric (km): x={hx:.3f}  y={hy:.3f}  z={hz:.3f}')
    time.sleep(1.5)

    # 2. Horizons geocentric ICRF (the truth we compare against)
    gx, gy, gz = query_horizons_geo_xyz(CMD, JD)
    print(f'Horizons geocentric   (km): x={gx:.3f}  y={gy:.3f}  z={gz:.3f}')
    time.sleep(1.5)

    # 3. Read Chiron directly from centaurs.bsp via jplephem (no Moira pipeline)
    from moira.asteroids import _ensure_tertiary_kernel
    kern = _ensure_tertiary_kernel()
    if kern is None:
        print('ERROR: tertiary kernel not loaded')
        return

    # Check what bodies are in the tertiary kernel
    print(f'Tertiary kernel bodies: {kern.list_naif_ids()}')

    # Get the raw position from kernel at JD
    try:
        pos_km = kern.position(NAIF, JD)
        print(f'Kernel heliocentric   (km): x={pos_km[0]:.3f}  y={pos_km[1]:.3f}  z={pos_km[2]:.3f}')
        diff_hel = math.sqrt((pos_km[0]-hx)**2 + (pos_km[1]-hy)**2 + (pos_km[2]-hz)**2)
        print(f'  vs Horizons hel: {diff_hel:.1f} km ({diff_hel/1.496e8*1e6:.1f} arcsec at 1 AU scale)')
    except Exception as exc:
        print(f'Kernel read error: {exc}')

    # 4. Moira's full asteroid_at pipeline
    from moira.asteroids import asteroid_at
    data = asteroid_at(NAME, JD)
    print()
    print(f'Moira asteroid_at longitude: {data.longitude:.4f} deg')

    # 5. Reference: convert Horizons geocentric ICRF → tropical longitude
    from moira.obliquity import true_obliquity, nutation
    from moira.precession import general_precession_in_longitude
    import math
    obl = true_obliquity(JD)
    obl_r = math.radians(obl)
    # Ecliptic rotation
    y_ecl = gy * math.cos(obl_r) + gz * math.sin(obl_r)
    lon_ecl = math.degrees(math.atan2(y_ecl, gx)) % 360.0
    dpsi, _ = nutation(JD)
    dpsi_deg = dpsi / 3600.0   # arcsec → deg
    prec = general_precession_in_longitude(JD)
    ref_lon = (lon_ecl + prec + dpsi_deg) % 360.0
    print(f'Reference (Horizons geo+pipeline): {ref_lon:.4f} deg')
    diff = ((data.longitude - ref_lon) + 180) % 360 - 180
    print(f'Difference: {diff*60:+.2f} arcmin')
    print()
    print(f'  obliquity = {obl:.6f} deg')
    print(f'  prec      = {prec:.6f} deg')
    print(f'  dpsi      = {dpsi:.6f} arcsec ({dpsi_deg:.6f} deg)')
    print(f'  lon_ecl (no prec/nutation) = {lon_ecl:.4f} deg')

    # Also compute reference WITHOUT precession/nutation
    ref_lon_icrf = math.degrees(math.atan2(y_ecl, gx)) % 360.0
    moira_minus_prec = (data.longitude - prec - dpsi_deg) % 360.0
    print()
    print(f'Moira lon - prec - dpsi = {moira_minus_prec:.4f}  vs Horizons ecliptic = {ref_lon_icrf:.4f}')
    ecl_diff = ((moira_minus_prec - ref_lon_icrf) + 180) % 360 - 180
    print(f'  diff (ecliptic, no prec/nutation): {ecl_diff:.4f} deg = {ecl_diff*60:.2f} arcmin')


if __name__ == '__main__':
    main()

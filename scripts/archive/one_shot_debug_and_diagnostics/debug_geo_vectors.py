#!/usr/bin/env python
"""
Compare Moira geocentric ICRF vector vs Horizons reference for Chiron.
"""
import sys, urllib.parse, urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.julian import datetime_from_jd
from moira.spk_reader import get_reader
from moira.asteroids import _ensure_tertiary_kernel, _asteroid_geocentric, ut_to_tt
from moira.planets import _earth_barycentric, vec_add, vec_sub, vec_norm
from datetime import timedelta

_HORIZONS_URL = 'https://ssd.jpl.nasa.gov/api/horizons.api'

def query_horizons_xyz(command, center_str, jd):
    dt = datetime_from_jd(jd)
    dt2 = dt + timedelta(days=1)
    params = {
        'format':     'text',
        'COMMAND':    f"'{command}'",
        'OBJ_DATA':   'NO',
        'MAKE_EPHEM': 'YES',
        'EPHEM_TYPE': 'VECTORS',
        'CENTER':     f"'{center_str}'",
        'START_TIME': f"'{dt.strftime('%Y-%b-%d %H:%M')}'",
        'STOP_TIME':  f"'{dt2.strftime('%Y-%b-%d %H:%M')}'",
        'STEP_SIZE':  "'1 d'",
        'OUT_UNITS':  'KM-S',
        'VEC_TABLE':  '2',
        'VEC_LABELS': 'NO',
        'CSV_FORMAT': 'YES',
    }
    url = _HORIZONS_URL + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode('utf-8')
    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if s == '$$SOE': in_data = True; continue
        if s == '$$EOE': break
        if in_data and s:
            parts = [p.strip() for p in s.split(',')]
            if len(parts) >= 5:
                try: return float(parts[2]), float(parts[3]), float(parts[4])
                except ValueError: continue
    raise ValueError(f'Parse failed for {command}')


def main():
    JD   = 2451545.0
    NAIF = 2002060

    reader = get_reader()
    jd_tt  = ut_to_tt(JD)
    kern   = _ensure_tertiary_kernel()

    print(f'JD_UT = {JD}  |  JD_TT = {jd_tt:.6f}  |  delta = {(jd_tt-JD)*86400:.2f} s')
    print()

    # --- DE441 Sun and Earth positions ---
    sun_bary = reader.position(0, 10, jd_tt)
    earth_bary = _earth_barycentric(jd_tt, reader)
    print(f'Sun  barycentric (DE441): x={sun_bary[0]:.3f}  y={sun_bary[1]:.3f}  z={sun_bary[2]:.3f} km')
    print(f'Earth barycentric (DE441): x={earth_bary[0]:.3f}  y={earth_bary[1]:.3f}  z={earth_bary[2]:.3f} km')

    # --- Kernel heliocentric ---
    hel = kern.position(NAIF, jd_tt)
    print(f'Chiron heliocentric (kernel): x={hel[0]:.3f}  y={hel[1]:.3f}  z={hel[2]:.3f} km')

    # --- Moira computed geocentric ---
    ast_bary = vec_add(hel, sun_bary)
    moira_geo = vec_sub(ast_bary, earth_bary)
    print(f'Moira geocentric (computed): x={moira_geo[0]:.3f}  y={moira_geo[1]:.3f}  z={moira_geo[2]:.3f} km')

    # --- Horizons geocentric (truth) ---
    import time
    hgx, hgy, hgz = query_horizons_xyz('2060', '500@399', JD)
    print(f'Horizons geocentric:         x={hgx:.3f}  y={hgy:.3f}  z={hgz:.3f} km')
    time.sleep(1.5)

    # --- Compare ---
    dx = moira_geo[0] - hgx
    dy = moira_geo[1] - hgy
    dz = moira_geo[2] - hgz
    diff_km = (dx**2 + dy**2 + dz**2) ** 0.5
    dist_km = vec_norm(moira_geo)
    diff_arcsec = (diff_km / dist_km) * (180.0 / 3.14159265) * 3600.0
    print(f'  diff: dx={dx:.1f}  dy={dy:.1f}  dz={dz:.1f}  |diff|={diff_km:.1f} km  ({diff_arcsec:.2f} arcsec)')
    print()

    # --- Also query Horizons for Earth to get Sun-Earth vector ---
    ehx, ehy, ehz = query_horizons_xyz('399', '500@0', JD)
    print(f'Earth barycentric (Horizons): x={ehx:.3f}  y={ehy:.3f}  z={ehz:.3f} km')
    time.sleep(1.5)
    print(f'Earth barycentric (DE441):    x={earth_bary[0]:.3f}  y={earth_bary[1]:.3f}  z={earth_bary[2]:.3f} km')
    edx = earth_bary[0] - ehx
    edy = earth_bary[1] - ehy
    edz = earth_bary[2] - ehz
    earth_diff = (edx**2 + edy**2 + edz**2) ** 0.5
    print(f'  Earth diff: {earth_diff:.3f} km')

    # --- Sun ---
    shx, shy, shz = query_horizons_xyz('10', '500@0', JD)
    print(f'Sun barycentric (Horizons):   x={shx:.3f}  y={shy:.3f}  z={shz:.3f} km')
    print(f'Sun barycentric (DE441):      x={sun_bary[0]:.3f}  y={sun_bary[1]:.3f}  z={sun_bary[2]:.3f} km')
    sdx = sun_bary[0] - shx
    sdy = sun_bary[1] - shy
    sdz = sun_bary[2] - shz
    sun_diff = (sdx**2 + sdy**2 + sdz**2) ** 0.5
    print(f'  Sun diff: {sun_diff:.3f} km')


if __name__ == '__main__':
    main()

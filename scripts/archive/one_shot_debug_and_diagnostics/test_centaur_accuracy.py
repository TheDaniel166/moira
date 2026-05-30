#!/usr/bin/env python
"""
scripts/test_centaur_accuracy.py
Compare Moira centaur longitudes against JPL Horizons OBSERVER geocentric ecliptic.
Uses the OBSERVER table directly (quantity 31 = ObsEcLon/ObsEcLat) so no frame
conversion is needed — this is exactly what astrological software should match.
"""

import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.asteroids import asteroid_at
from moira.julian import datetime_from_jd
from datetime import timedelta

_HORIZONS_URL = 'https://ssd.jpl.nasa.gov/api/horizons.api'


def _query_horizons_observer_eclon(command: str, jd_ut: float) -> float:
    """
    Return Horizons geocentric ecliptic longitude (deg) for *command* at *jd_ut*.
    Uses OBSERVER table, quantity 31 (ObsEcLon), no reference frame ambiguity.
    """
    dt = datetime_from_jd(jd_ut)
    dt2 = dt + timedelta(days=1)
    start_str = dt.strftime('%Y-%b-%d %H:%M')
    stop_str  = dt2.strftime('%Y-%b-%d %H:%M')

    params = {
        'format':     'text',
        'COMMAND':    f"'{command}'",
        'OBJ_DATA':   'NO',
        'MAKE_EPHEM': 'YES',
        'EPHEM_TYPE': 'OBSERVER',
        'CENTER':     "'500@399'",   # geocentric Earth
        'START_TIME': f"'{start_str}'",
        'STOP_TIME':  f"'{stop_str}'",
        'STEP_SIZE':  "'1 d'",
        'QUANTITIES': "'31'",        # 31 = ObsEcLon ObsEcLat
        'ANG_FORMAT': 'DEG',
    }
    url = _HORIZONS_URL + '?' + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode('utf-8')

    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if s == '$$SOE':
            in_data = True
            continue
        if s == '$$EOE':
            break
        if in_data and s:
            # Format: date  ObsEcLon  ObsEcLat
            parts = s.split()
            # Find the longitude: first numeric token after the date/time
            nums = []
            for p in parts:
                try:
                    nums.append(float(p))
                except ValueError:
                    pass
            if len(nums) >= 2:
                return nums[0]   # ObsEcLon

    for line in text.splitlines():
        if 'ERROR' in line.upper():
            raise ValueError(f'Horizons error: {line.strip()}')
    raise ValueError(f'No observer data found for {command!r}')


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

TESTS = [
    # (moira_name, horizons_command, date_label, jd_ut)
    ('Chiron',   '2060',  'J2000.0',    2451545.0),
    ('Chiron',   '2060',  '1960-Jan-01', 2436934.5),
    ('Chiron',   '2060',  '2024-Jan-01', 2460310.5),
    ('Pholus',   '5145',  'J2000.0',    2451545.0),
    ('Chariklo', '10199', 'J2000.0',    2451545.0),
    ('Nessus',   '7066',  'J2000.0',    2451545.0),
    ('Asbolus',  '8405',  'J2000.0',    2451545.0),
    ('Hylonome', '10370', 'J2000.0',    2451545.0),
]


def angle_diff(a: float, b: float) -> float:
    d = (a - b) % 360.0
    if d > 180.0:
        d -= 360.0
    return d


def main() -> None:
    print('Centaur accuracy: Moira vs JPL Horizons OBSERVER (geocentric ecliptic)')
    print('=' * 70)

    prev_body = None
    for moira_name, cmd, label, jd in TESTS:
        if moira_name != prev_body:
            print(f'\n{moira_name}:')
            prev_body = moira_name

        try:
            data = asteroid_at(moira_name, jd)
            moira_lon = data.longitude
        except Exception as exc:
            print(f'  {label:<20}  MOIRA ERROR: {exc}')
            continue

        try:
            ref_lon = _query_horizons_observer_eclon(cmd, jd)
        except Exception as exc:
            print(f'  {label:<20}  moira={moira_lon:.4f}  HORIZONS ERROR: {exc}')
            time.sleep(1.5)
            continue

        diff_deg  = angle_diff(moira_lon, ref_lon)
        diff_amin = diff_deg * 60.0
        flag = '  OK' if abs(diff_amin) < 5.0 else '  *** LARGE ERROR ***'
        print(f'  {label:<20}  moira={moira_lon:.4f}  ref={ref_lon:.4f}  '
              f'diff={diff_amin:+.1f} arcmin{flag}')

        time.sleep(1.5)

    print()
    print('Done.')


if __name__ == '__main__':
    main()

"""Re-evaluate retained hybrid witness pairs and their horizon sensitivity.

This is same-model constructive evidence, not an exhaustive path classifier.
Raising the diagnostic horizon can invalidate a stored pair without proving
that an event lacks another legal witness. Outputs are new, never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import moira
from moira import moira_native
from moira._kernel_paths import find_planetary_kernel
from moira.eclipse import (
    EclipseCalculator, _axis_surface_point_from_shadow, _earth_fixed_solar_shadow,
    _shadow_dot, _shadow_subtract, _solar_shadow_discs, _wgs84_surface_normal_unit,
)
from moira.spk_reader import SpkReader


def _witness(calc, epoch):
    shadow = _earth_fixed_solar_shadow(calc, epoch)
    if shadow is None:
        return {'valid': False, 'reason': 'shadow unavailable'}
    axis = _axis_surface_point_from_shadow(shadow)
    if axis is None:
        return {'valid': False, 'reason': 'axis unavailable'}
    xyz = axis.xyz_itrf_km
    solar = _shadow_subtract(shadow.sun_xyz_from_earth_itrf_km, xyz)
    sine_altitude = _shadow_dot(_wgs84_surface_normal_unit(xyz), solar)/math.sqrt(_shadow_dot(solar, solar))
    if not math.isfinite(sine_altitude) or abs(sine_altitude) > 1+1e-12:
        return {'valid': False, 'reason': 'nonfinite or out-of-domain geometric horizon'}
    altitude = math.degrees(math.asin(max(-1., min(1., sine_altitude))))
    radius = shadow.central_radius_km-shadow.central_cone_slope*_shadow_dot(
        _shadow_subtract(xyz, shadow.fundamental_plane_point_xyz_km), shadow.axis_unit_away_from_sun)
    _, sun_radius, moon_radius = _solar_shadow_discs(shadow, xyz)
    ratio = moon_radius/sun_radius-1
    return dict(valid=all(math.isfinite(x) for x in (altitude, radius, ratio)),
                jd_ut1=epoch, altitude_deg=altitude, signed_radius_km=radius,
                angular_radius_ratio_minus_one=ratio)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--witnesses', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; use a new evidence path')
    with args.witnesses.open(newline='', encoding='utf-8-sig') as stream:
        inputs = list(csv.DictReader(stream))
    if not inputs or len({row['lunation_number'] for row in inputs}) != len(inputs):
        parser.error('nonempty unique-lunation witness rows required')
    kernel = find_planetary_kernel()
    if kernel is None:
        raise RuntimeError('planetary kernel unavailable; run with MOIRA_NO_DOWNLOAD=1')
    reader = SpkReader(kernel)
    kernel_sha256 = reader._source_identity.sha256
    rows = []
    try:
        calc = EclipseCalculator(reader=reader)
        for index, row in enumerate(inputs, 1):
            annular = _witness(calc, float(row['annular_jd_ut1']))
            total = _witness(calc, float(row['total_jd_ut1']))
            valid = (annular['valid'] and total['valid']
                     and annular['altitude_deg'] > 0 and total['altitude_deg'] > 0
                     and annular['signed_radius_km'] < -1e-6 and total['signed_radius_km'] > 1e-6
                     and annular['angular_radius_ratio_minus_one'] < -1e-12
                     and total['angular_radius_ratio_minus_one'] > 1e-12)
            rows.append(dict(lunation=int(row['lunation_number']), date_tt=row['date_tt'],
                             valid_pair=bool(valid), annular=annular, total=total))
            if index % 100 == 0:
                print(f'evaluated {index}/{len(inputs)} retained witness pairs', flush=True)
    finally:
        reader.close()
    valid_rows = [row for row in rows if row['valid_pair']]
    thresholds = (0., .001, .01, .05, .1, 1.)
    sensitivity = {str(threshold): sum(
        min(row['annular']['altitude_deg'], row['total']['altitude_deg']) > threshold
        for row in valid_rows) for threshold in thresholds}
    result = {
        'scope': 'fresh constructive pairs under native WGS84/geometric Sun-centre policy',
        'not_claimed': ['complete central intervals', 'all transitions', 'H1/H2/H3',
                        'non-hybrid absence', 'observational visibility', 'physical accuracy'],
        'input_path': str(args.witnesses.resolve()),
        'input_sha256': hashlib.sha256(args.witnesses.read_bytes()).hexdigest(),
        'kernel_path': str(kernel),
        'kernel_sha256_at_reader_open': kernel_sha256,
        'engine_version': moira.__version__,
        'native_binary_sha256': hashlib.sha256(Path(moira_native.__backend_file__).read_bytes()).hexdigest(),
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'native_build_source_attested': False,
        'pairs_evaluated': len(rows), 'valid_pairs': len(valid_rows),
        'minimum_stored_pair_altitude_deg': min(
            (min(row['annular']['altitude_deg'], row['total']['altitude_deg']) for row in valid_rows),
            default=None),
        'stored_pairs_clearing_raised_geometric_horizon_deg': sensitivity,
        'sensitivity_warning': 'a rejected stored pair does not exclude other witnesses or the event',
        'cases': rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'cases'}, indent=2), flush=True)
    return 0 if len(valid_rows) == len(rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())

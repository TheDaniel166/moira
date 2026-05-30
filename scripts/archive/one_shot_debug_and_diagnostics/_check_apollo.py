#!/usr/bin/env python
"""Diagnose Apollo interpolation error."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force fresh kernel load
import moira.asteroids as ast
ast._quaternary_kernel = None

from moira.asteroids import load_quaternary_kernel, asteroid_at, _ensure_quaternary_kernel

load_quaternary_kernel()
qk = _ensure_quaternary_kernel()
print("Kernel loaded:", qk._path)
print("Apollo in kernel:", qk.has_body(2001862))

# Check raw kernel position vs Horizons
from moira.spk_reader import get_reader
from moira.julian import ut_to_tt
from moira.coordinates import icrf_to_ecliptic
from moira.obliquity import true_obliquity
from moira.asteroids import _asteroid_apparent

reader = get_reader()

for label, jd_ut, ref_lon in [
    ("2000-01-01", 2451545.0, 218.756090),
    ("2010-07-01", 2455378.5, 145.144797),
    ("2024-01-01", 2460310.5, 116.403464),
]:
    jd_tt = ut_to_tt(jd_ut)
    obliquity = true_obliquity(jd_tt)
    xyz = _asteroid_apparent(2001862, jd_tt, qk, reader)
    lon, lat, dist = icrf_to_ecliptic(xyz, obliquity)
    err = ((lon - ref_lon + 180) % 360 - 180) * 3600
    print(f"{label}: moira={lon:.6f}  horizons={ref_lon:.6f}  err={err:+.2f}\"")

# Also check raw heliocentric position from kernel
print()
print("Raw kernel position at J2000:")
jd_tt = ut_to_tt(2451545.0)
pos = qk.position(2001862, jd_tt)
print(f"  x={pos[0]:.3f} y={pos[1]:.3f} z={pos[2]:.3f} km")
print(f"  center={qk.segment_center(2001862)}")

# Check number of segments and their time coverage
from jplephem.spk import SPK
spk = SPK.open(str(qk._path))
for seg in spk.segments:
    if seg.target == 2001862:
        print(f"  segment: center={seg.center} target={seg.target} "
              f"start={seg.start_jd:.1f} end={seg.end_jd:.1f}")

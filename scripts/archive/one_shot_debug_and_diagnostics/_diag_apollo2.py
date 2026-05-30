#!/usr/bin/env python
"""Check Apollo kernel epochs near J2000 and compare with Horizons at exact same JD."""
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import moira.asteroids as _ast_mod
_ast_mod._quaternary_kernel = None

from moira.asteroids import load_quaternary_kernel, _ensure_quaternary_kernel
from moira.asteroids import _Type13Segment

load_quaternary_kernel()
qk = _ensure_quaternary_kernel()

# Find the segment for Apollo
from jplephem.spk import SPK
spk = SPK.open(str(qk._path))
apollo_seg = None
for seg in spk.segments:
    if seg.target == 2001862:
        apollo_seg = seg
        break

print(f"Segment type: {type(apollo_seg).__name__}")
print(f"Segment start: {apollo_seg.start_jd}  end: {apollo_seg.end_jd}")

# Get the actual epoch nodes near J2000
states, epochs_jd, ws = apollo_seg._data
print(f"Total epochs: {len(epochs_jd)}")
print(f"Window size: {ws}")
print(f"First epoch: {epochs_jd[0]:.4f}")
print(f"Last epoch:  {epochs_jd[-1]:.4f}")

# Find epochs bracketing J2000 = 2451545.0
from bisect import bisect_left
idx = bisect_left(epochs_jd, 2451545.0)
print(f"\nEpochs around J2000 (2451545.0):")
for i in range(max(0, idx-3), min(len(epochs_jd), idx+4)):
    print(f"  [{i}] {epochs_jd[i]:.4f}  (delta={epochs_jd[i]-2451545.0:+.4f} days)")

# Now fetch Horizons at the exact kernel epoch nearest J2000
nearest_jd = epochs_jd[idx] if idx < len(epochs_jd) else epochs_jd[idx-1]
print(f"\nNearest kernel epoch to J2000: {nearest_jd:.4f}")

# Get kernel position at that exact epoch
pos_kernel = qk.position(2001862, nearest_jd)
print(f"Kernel position at {nearest_jd:.4f}: x={pos_kernel[0]:.3f} y={pos_kernel[1]:.3f} z={pos_kernel[2]:.3f}")

# Fetch Horizons at that exact JD
from moira.julian import datetime_from_jd
from datetime import timedelta
dt = datetime_from_jd(nearest_jd)
dt2 = dt + timedelta(days=1)
fmt = "%Y-%b-%d %H:%M"

params = {
    "format":     "text",
    "COMMAND":    "'1862;'",
    "OBJ_DATA":   "NO",
    "MAKE_EPHEM": "YES",
    "EPHEM_TYPE": "VECTORS",
    "CENTER":     "'500@10'",
    "START_TIME": f"'{dt.strftime(fmt)}'",
    "STOP_TIME":  f"'{dt2.strftime(fmt)}'",
    "STEP_SIZE":  "'1 d'",
    "OUT_UNITS":  "KM-S",
    "VEC_TABLE":  "2",
    "VEC_LABELS": "NO",
    "CSV_FORMAT": "YES",
    "REF_SYSTEM": "ICRF",
    "REF_PLANE":  "FRAME",
}
url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
with urllib.request.urlopen(url, timeout=30) as r:
    text = r.read().decode()

in_data = False
for line in text.splitlines():
    s = line.strip()
    if s == "$$SOE":
        in_data = True
        continue
    if s == "$$EOE":
        break
    if in_data and s:
        parts = [p.strip() for p in s.split(",")]
        if len(parts) >= 7:
            jd_h = float(parts[0])
            x_h, y_h, z_h = float(parts[2]), float(parts[3]), float(parts[4])
            print(f"Horizons at JD {jd_h:.4f}: x={x_h:.3f} y={y_h:.3f} z={z_h:.3f}")
            sep = ((pos_kernel[0]-x_h)**2 + (pos_kernel[1]-y_h)**2 + (pos_kernel[2]-z_h)**2)**0.5
            print(f"Separation: {sep:.3f} km")
        break

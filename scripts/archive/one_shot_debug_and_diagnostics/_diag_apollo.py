#!/usr/bin/env python
"""
Deep diagnostic for Apollo position error.
Compare each pipeline stage against Horizons VECTORS output.
"""
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import moira.asteroids as _ast_mod
_ast_mod._quaternary_kernel = None

from moira.asteroids import load_quaternary_kernel, _ensure_quaternary_kernel, _asteroid_barycentric, _asteroid_apparent
from moira.planets import _earth_barycentric
from moira.corrections import apply_light_time
from moira.coordinates import icrf_to_ecliptic, vec_sub, vec_norm
from moira.obliquity import true_obliquity
from moira.julian import ut_to_tt
from moira.spk_reader import get_reader

load_quaternary_kernel()
qk = _ensure_quaternary_kernel()
reader = get_reader()

JD_UT  = 2451545.0   # 2000-01-01
JD_TT  = ut_to_tt(JD_UT)
NAIF   = 2001862

print(f"JD_UT={JD_UT}  JD_TT={JD_TT:.6f}")
print()

# --- Stage 1: raw heliocentric from kernel ---
raw = qk.position(NAIF, JD_TT)
print(f"Stage 1 — heliocentric (kernel):  x={raw[0]:.3f}  y={raw[1]:.3f}  z={raw[2]:.3f} km")

# --- Stage 2: barycentric ---
bary = _asteroid_barycentric(NAIF, JD_TT, qk, reader)
print(f"Stage 2 — barycentric:            x={bary[0]:.3f}  y={bary[1]:.3f}  z={bary[2]:.3f} km")

# --- Stage 3: geocentric (light-time corrected) ---
earth_ssb = _earth_barycentric(JD_TT, reader)
print(f"Stage 3 — Earth SSB:              x={earth_ssb[0]:.3f}  y={earth_ssb[1]:.3f}  z={earth_ssb[2]:.3f} km")

def _bary_fn(nid, t, r):
    return _asteroid_barycentric(nid, t, qk, reader)

geo, lt = apply_light_time(NAIF, JD_TT, reader, earth_ssb, _bary_fn)
print(f"Stage 3 — geocentric (lt={lt*86400:.1f}s):  x={geo[0]:.3f}  y={geo[1]:.3f}  z={geo[2]:.3f} km")
dist_km = vec_norm(geo)
print(f"           distance = {dist_km:.3f} km  ({dist_km/1.496e8:.6f} AU)")

# --- Stage 4: full apparent ---
obliquity = true_obliquity(JD_TT)
xyz_app = _asteroid_apparent(NAIF, JD_TT, qk, reader)
lon, lat, dist = icrf_to_ecliptic(xyz_app, obliquity)
print(f"Stage 4 — apparent ecliptic:      lon={lon:.6f}°  lat={lat:.6f}°  dist={dist:.3f} km")
print(f"          Horizons reference:     lon=218.756090°  lat=2.688300°")
print(f"          Error:                  dlon={((lon-218.756090+180)%360-180)*3600:+.2f}\"  dlat={(lat-2.688300)*3600:+.2f}\"")

# --- Fetch Horizons VECTORS at J2000 for comparison ---
print()
print("Fetching Horizons VECTORS (heliocentric) at J2000 for Apollo...")
params = {
    "format":     "text",
    "COMMAND":    "'1862;'",
    "OBJ_DATA":   "NO",
    "MAKE_EPHEM": "YES",
    "EPHEM_TYPE": "VECTORS",
    "CENTER":     "'500@10'",
    "START_TIME": "'2000-Jan-01'",
    "STOP_TIME":  "'2000-Jan-02'",
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
            vx_h, vy_h, vz_h = float(parts[5]), float(parts[6]), float(parts[7])
            print(f"Horizons heliocentric @ JD {jd_h}:")
            print(f"  x={x_h:.3f}  y={y_h:.3f}  z={z_h:.3f} km")
            print(f"  Kernel delta: dx={raw[0]-x_h:.3f}  dy={raw[1]-y_h:.3f}  dz={raw[2]-z_h:.3f} km")
            sep = ((raw[0]-x_h)**2 + (raw[1]-y_h)**2 + (raw[2]-z_h)**2)**0.5
            print(f"  3D separation: {sep:.3f} km")
        break

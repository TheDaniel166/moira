#!/usr/bin/env python
"""
Check all 6 minor bodies in the kernel against live Horizons data.
Tests 3 epochs per body to identify which bodies have stale/diverged data.
"""
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from bisect import bisect_left

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import moira.asteroids  # noqa: F401 — registers Type13
from jplephem.spk import SPK
from moira.julian import datetime_from_jd
from moira._kernel_paths import find_kernel

kernel_path = find_kernel("minor_bodies.bsp")
spk = SPK.open(str(kernel_path))

# Build segment map: target → segment
segs: dict[int, object] = {}
for seg in spk.segments:
    segs[seg.target] = seg

BODIES = {
    "Pandora":    (2000055, "55;"),
    "Amor":       (2001221, "1221;"),
    "Icarus":     (2001566, "1566;"),
    "Apollo":     (2001862, "1862;"),
    "Karma":      (2003811, "3811;"),
    "Persephone": (2000399, "399;"),
}

TEST_JDS = [2415020.5, 2451544.5, 2488069.5]  # ~1900, ~2000, ~2100

url = "https://ssd.jpl.nasa.gov/api/horizons.api"

def fetch_horizons(command: str, jd: float) -> tuple[float, float, float] | None:
    dt = datetime_from_jd(jd)
    date_str = dt.strftime("%Y-%b-%d %H:%M")
    params = {
        "format":     "text",
        "COMMAND":    f"'{command}'",
        "OBJ_DATA":   "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER":     "'500@10'",
        "START_TIME": f"'{date_str}'",
        "STOP_TIME":  f"'JD {jd + 0.5}'",
        "STEP_SIZE":  "'1 d'",
        "OUT_UNITS":  "KM-S",
        "VEC_TABLE":  "2",
        "VEC_LABELS": "NO",
        "CSV_FORMAT": "YES",
        "REF_SYSTEM": "ICRF",
        "REF_PLANE":  "FRAME",
    }
    full_url = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full_url, timeout=60) as r:
            text = r.read().decode("utf-8")
    except Exception as e:
        print(f"    FETCH ERROR: {e}")
        return None

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
            if len(parts) >= 8:
                try:
                    return float(parts[2]), float(parts[3]), float(parts[4])
                except ValueError:
                    pass
    return None


print(f"{'Body':<12} {'Epoch':<8} {'|delta| km':>14}  Status")
print("-" * 50)

for name, (naif_id, command) in BODIES.items():
    if naif_id not in segs:
        print(f"{name:<12} NOT IN KERNEL")
        continue

    seg = segs[naif_id]
    states, epochs_jd, ws = seg._data

    for test_jd in TEST_JDS:
        year = int(datetime_from_jd(test_jd).strftime("%Y"))
        idx = bisect_left(epochs_jd, test_jd)
        if idx >= len(epochs_jd):
            idx = len(epochs_jd) - 1
        node_jd = epochs_jd[idx]

        kx = states[0][idx]
        ky = states[1][idx]
        kz = states[2][idx]

        hpos = fetch_horizons(command, node_jd)
        time.sleep(0.5)

        if hpos is None:
            print(f"{name:<12} {year:<8} {'FETCH FAIL':>14}")
            continue

        hx, hy, hz = hpos
        dx = kx - hx
        dy = ky - hy
        dz = kz - hz
        dist = (dx**2 + dy**2 + dz**2) ** 0.5

        status = "OK" if dist < 1000 else ("WARN" if dist < 100_000 else "BAD")
        print(f"{name:<12} {year:<8} {dist:>14.1f}  {status}")

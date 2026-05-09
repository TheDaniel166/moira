#!/usr/bin/env python
"""
List what bodies are in asteroids.bsp and comets.bsp
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moira.spk_reader import SpkReader

# Bodies we're looking for in shard 16
SHARD_16_BODIES = {
    "Pandora": 2000055,
    "Persephone": 2000399,
    "Amor": 2001221,
    "Icarus": 2001566,
    "Apollo": 2001862,
    "Karma": 2003811,
}

# Bodies we're looking for in shard 18
SHARD_18_BODIES = {
    "Halley": 1000001,
    "Encke": 1000002,
    "Tempel 1": 1000009,
    "C-G": 1000067,
    "Swift-Tuttle": 1000109,
}

print("=== Checking asteroids.bsp for shard 16 bodies ===\n")
with SpkReader("kernels/asteroids.bsp") as reader:
    for name, naif in SHARD_16_BODIES.items():
        if reader.has_segment(10, naif):
            epoch_range = reader.epoch_range(10, naif)
            if epoch_range:
                start_jd = epoch_range[0] / 86400.0 + 2451545.0
                end_jd = epoch_range[1] / 86400.0 + 2451545.0
                print(f"✓ {name:12} (NAIF {naif}): JD {start_jd:.1f} to {end_jd:.1f}")
            else:
                print(f"? {name:12} (NAIF {naif}): found but no epoch range")
        else:
            print(f"✗ {name:12} (NAIF {naif}): NOT FOUND")

print("\n=== Checking comets.bsp for shard 18 bodies ===\n")
with SpkReader("kernels/comets.bsp") as reader:
    for name, naif in SHARD_18_BODIES.items():
        if reader.has_segment(10, naif):
            epoch_range = reader.epoch_range(10, naif)
            if epoch_range:
                start_jd = epoch_range[0] / 86400.0 + 2451545.0
                end_jd = epoch_range[1] / 86400.0 + 2451545.0
                print(f"✓ {name:12} (NAIF {naif}): JD {start_jd:.1f} to {end_jd:.1f}")
            else:
                print(f"? {name:12} (NAIF {naif}): found but no epoch range")
        else:
            print(f"✗ {name:12} (NAIF {naif}): NOT FOUND")

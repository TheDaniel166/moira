#!/usr/bin/env python
"""
Check if Apollo is already in the existing official kernels.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moira.spk_reader import SpkReader

APOLLO_NAIF = 2001862

kernels_to_check = [
    "kernels/asteroids.bsp",
    "kernels/sb441-n373s.bsp",
    "kernels/minor_bodies.bsp",
    "kernels/sb441_type13/sb441_type13_shard_016.bsp"
]

print("Checking for Apollo (NAIF 2001862) in existing kernels...\n")

for kernel_path in kernels_to_check:
    path = Path(kernel_path)
    if not path.exists():
        print(f"✗ {kernel_path} - NOT FOUND")
        continue
    
    try:
        with SpkReader(path) as reader:
            if reader.has_segment(10, APOLLO_NAIF):
                epoch_range = reader.epoch_range(10, APOLLO_NAIF)
                if epoch_range:
                    start_jd = epoch_range[0] / 86400.0 + 2451545.0
                    end_jd = epoch_range[1] / 86400.0 + 2451545.0
                    print(f"✓ {kernel_path}")
                    print(f"  Coverage: JD {start_jd:.1f} to {end_jd:.1f}")
                    print(f"  Span: {(end_jd - start_jd) / 365.25:.1f} years\n")
                else:
                    print(f"? {kernel_path} - has segment but no epoch range\n")
            else:
                print(f"✗ {kernel_path} - Apollo not found\n")
    except Exception as e:
        print(f"✗ {kernel_path} - Error: {e}\n")

"""Check what Moon segments are available in de441.bsp"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._kernel_paths import find_planetary_kernel
from moira.spk_reader import SpkReader

planetary_path = find_planetary_kernel()
reader = SpkReader(planetary_path)

try:
    coverage = reader.coverage()
    
    print("Moon-related segments in de441.bsp:")
    print("=" * 60)
    
    for (center, target), (start_jd, end_jd) in sorted(coverage.items()):
        if target == 301 or center == 301:
            print(f"Center {center:3d} → Target {target:3d}: JD {start_jd:.1f} to {end_jd:.1f}")
    
    print("\nEarth-related segments:")
    print("=" * 60)
    for (center, target), (start_jd, end_jd) in sorted(coverage.items()):
        if target == 399 or center == 399:
            print(f"Center {center:3d} → Target {target:3d}: JD {start_jd:.1f} to {end_jd:.1f}")
            
finally:
    reader.close()

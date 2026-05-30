#!/usr/bin/env python
"""
Check Apollo's coverage in the official sb441-n373s.bsp kernel.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moira.spk_reader import SpkReader

APOLLO_NAIF = 2001862

kernel_path = Path("kernels/sb441-n373s.bsp")

print("Checking Apollo in official sb441-n373s.bsp kernel...\n")

try:
    with SpkReader(kernel_path) as reader:
        # Check all possible center-target combinations
        centers = [0, 10]  # SSB and Sun
        
        for center in centers:
            if reader.has_segment(center, APOLLO_NAIF):
                epoch_range = reader.epoch_range(center, APOLLO_NAIF)
                if epoch_range:
                    start_jd = epoch_range[0] / 86400.0 + 2451545.0
                    end_jd = epoch_range[1] / 86400.0 + 2451545.0
                    
                    # Convert to calendar dates
                    from moira.julian import calendar_from_jd
                    y1, m1, d1, _ = calendar_from_jd(start_jd)
                    y2, m2, d2, _ = calendar_from_jd(end_jd)
                    
                    print(f"✓ Found Apollo with center={center}")
                    print(f"  Coverage: JD {start_jd:.1f} to {end_jd:.1f}")
                    print(f"  Dates: {y1}-{m1:02d}-{d1:02d} to {y2}-{m2:02d}-{d2:02d}")
                    print(f"  Span: {(end_jd - start_jd) / 365.25:.1f} years")
                    
                    # Test a position at J2000
                    test_jd = 2451545.0
                    if start_jd <= test_jd <= end_jd:
                        test_jd_tdb = (test_jd - 2451545.0) * 86400.0
                        pos = reader.position(center, APOLLO_NAIF, test_jd_tdb)
                        print(f"\n  Position at J2000.0:")
                        print(f"    X={pos[0]:.3f} Y={pos[1]:.3f} Z={pos[2]:.3f} km")
                    print()
        
        if not any(reader.has_segment(c, APOLLO_NAIF) for c in centers):
            print("✗ Apollo not found in this kernel")
            
except Exception as e:
    print(f"✗ Error reading kernel: {e}")
    import traceback
    traceback.print_exc()

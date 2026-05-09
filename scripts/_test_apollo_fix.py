#!/usr/bin/env python
"""
Test that Apollo fetch works correctly within its observational coverage (1930-2026).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rebuild_shard_16 import fetch_horizons_long

cmd = "'1862;'"  # Apollo
start_jd = 2426033.5  # 1930-01-01
end_jd = 2461041.5    # 2026-12-31
step_days = 2

print("Testing Apollo fetch within observational coverage (1930-2026)...")
print(f"Start: {start_jd}, End: {end_jd}, Step: {step_days}d\n")

try:
    states = fetch_horizons_long(cmd, start_jd, end_jd, step_days)
    print(f"\n✓ SUCCESS: Fetched {len(states)} states")
    print(f"  First state: X={states[0][0]:.3f} Y={states[0][1]:.3f} Z={states[0][2]:.3f} km")
    print(f"  Last state:  X={states[-1][0]:.3f} Y={states[-1][1]:.3f} Z={states[-1][2]:.3f} km")
    
    # Check for J2000.0 epoch
    target_jd = 2451545.0
    target_idx = int((target_jd - start_jd) / step_days)
    if 0 <= target_idx < len(states):
        print(f"\n  At J2000.0 (JD {target_jd}):")
        print(f"    X={states[target_idx][0]:.3f} km")
        print(f"    Expected: ~-246M km (from Horizons)")
        
except RuntimeError as e:
    print(f"\n✗ FAILED: {e}")

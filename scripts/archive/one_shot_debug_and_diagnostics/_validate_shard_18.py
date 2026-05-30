#!/usr/bin/env python
"""
Validate shard 18 (comets) for discontinuities.
Check if the stored ephemeris has any sudden jumps that indicate chunking errors.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moira.spk_reader import SpkReader

SHARD_18_BODIES = {
    "Halley": 1000001,
    "Encke": 1000002,
    "Tempel 1": 1000009,
    "C-G": 1000067,
    "Swift-Tuttle": 1000109,
}

print("=== Validating Shard 18 for Discontinuities ===\n")

kernel_path = Path("kernels/sb441_type13/sb441_type13_shard_018.bsp")

if not kernel_path.exists():
    print(f"✗ {kernel_path} not found")
    sys.exit(1)

try:
    with SpkReader(kernel_path) as reader:
        for name, naif in SHARD_18_BODIES.items():
            print(f"Checking {name} (NAIF {naif})...")
            
            if not reader.has_segment(10, naif):
                print(f"  ✗ Not found in kernel\n")
                continue
            
            # Get epoch range
            epoch_range = reader.epoch_range(10, naif)
            if not epoch_range:
                print(f"  ✗ No epoch range\n")
                continue
            
            start_jd = epoch_range[0] / 86400.0 + 2451545.0
            end_jd = epoch_range[1] / 86400.0 + 2451545.0
            
            print(f"  Coverage: JD {start_jd:.1f} to {end_jd:.1f}")
            print(f"  Span: {(end_jd - start_jd) / 365.25:.1f} years")
            
            # Sample positions at regular intervals and check for discontinuities
            # Expected chunk boundary at JD 2451547.5 (same as Apollo issue)
            test_epochs = [
                2305447.5,  # Start
                2451545.5,  # Around chunk boundary - 2 days
                2451547.5,  # Exact chunk boundary
                2451549.5,  # After chunk boundary + 2 days
                2634157.5,  # End
            ]
            
            positions = []
            for jd in test_epochs:
                if start_jd <= jd <= end_jd:
                    jd_tdb = (jd - 2451545.0) * 86400.0
                    try:
                        pos = reader.position(10, naif, jd_tdb)
                        positions.append((jd, pos))
                    except Exception as e:
                        print(f"  ✗ Error at JD {jd}: {e}")
            
            # Check for discontinuities
            max_jump = 0.0
            max_jump_jd = None
            
            for i in range(1, len(positions)):
                jd_prev, pos_prev = positions[i-1]
                jd_curr, pos_curr = positions[i]
                
                # Calculate position change
                dx = pos_curr[0] - pos_prev[0]
                dy = pos_curr[1] - pos_prev[1]
                dz = pos_curr[2] - pos_prev[2]
                sep = (dx**2 + dy**2 + dz**2)**0.5
                
                # Calculate time difference
                dt_days = jd_curr - jd_prev
                
                # Expected velocity for comets: ~10-50 km/s
                # Over 2 days: ~1.7M - 8.6M km
                # Over 146100 days (400 years): ~1.5B - 7.3B km
                # Use velocity to estimate expected change
                velocity_estimate = sep / (dt_days * 86400.0)  # km/s
                
                if sep > max_jump:
                    max_jump = sep
                    max_jump_jd = (jd_prev, jd_curr)
                
                print(f"  JD {jd_prev:.1f} → {jd_curr:.1f} ({dt_days:.0f} days):")
                print(f"    Position change: {sep:.3f} km")
                print(f"    Implied velocity: {velocity_estimate:.3f} km/s")
                
                # Flag suspicious jumps
                # For 2-day intervals, expect < 10M km
                # For 400-year intervals, expect < 10B km
                if dt_days < 10 and sep > 10e6:
                    print(f"    ⚠️  SUSPICIOUS: Large jump over short interval!")
                elif dt_days > 100000 and sep > 10e9:
                    print(f"    ⚠️  SUSPICIOUS: Extremely large jump!")
            
            print(f"  Max position jump: {max_jump:.3f} km")
            if max_jump_jd:
                print(f"    Between JD {max_jump_jd[0]:.1f} and {max_jump_jd[1]:.1f}")
            
            # Final verdict
            if max_jump < 1e6:  # Less than 1 million km jump
                print(f"  ✓ PASS: No significant discontinuities detected\n")
            elif max_jump < 10e6:  # Less than 10 million km
                print(f"  ⚠️  WARNING: Moderate discontinuity detected\n")
            else:
                print(f"  ✗ FAIL: Large discontinuity detected (similar to Apollo issue)\n")
                
except Exception as e:
    print(f"✗ Error reading kernel: {e}")
    import traceback
    traceback.print_exc()

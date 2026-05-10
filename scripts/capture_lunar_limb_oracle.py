"""
Capture official LOLA profile adjustment baseline (Oracle).
This script runs the legacy NumPy-based implementation against a set of known inputs
to record the 'Truth' before migration.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from moira.lunar_limb import official_lunar_limb_profile_adjustment

def capture_baseline():
    inputs = [
        # (jd_ut, lat, lon, elev, pa, dist)
        (2460408.5, 35.0, -90.0, 100.0, 0.0, 360000.0),    # 2024 Eclipseish
        (2460408.5, 35.0, -90.0, 100.0, 90.0, 360000.0),
        (2460408.5, 35.0, -90.0, 100.0, 180.0, 360000.0),
        (2460408.5, 35.0, -90.0, 100.0, 270.0, 360000.0),
        
        (2461171.0, 51.47, 0.0, 50.0, 45.0, 384400.0),    # May 2026
        (2461171.0, 51.47, 0.0, 50.0, 135.0, 384400.0),
        (2461171.0, 51.47, 0.0, 50.0, 225.0, 384400.0),
        (2461171.0, 51.47, 0.0, 50.0, 315.0, 384400.0),
        
        (2451545.0, 0.0, 0.0, 0.0, 10.0, 400000.0),       # J2000
    ]
    
    results = []
    print(f"Capturing baseline for {len(inputs)} test cases...")
    
    for i, inp in enumerate(inputs):
        jd, lat, lon, elev, pa, dist = inp
        print(f"Processing case {i+1}/{len(inputs)}: JD={jd}, PA={pa}...")
        try:
            correction = official_lunar_limb_profile_adjustment(jd, lat, lon, elev, pa, dist)
            results.append({
                "input": {
                    "jd_ut": jd,
                    "observer_lat": lat,
                    "observer_lon": lon,
                    "observer_elev_m": elev,
                    "position_angle_deg": pa,
                    "moon_distance_km": dist
                },
                "output": correction
            })
        except Exception as e:
            print(f"Error in case {i+1}: {e}")
            
    output_path = Path("tests/oracle_lunar_limb_baseline.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Baseline captured and saved to {output_path}")

if __name__ == "__main__":
    capture_baseline()

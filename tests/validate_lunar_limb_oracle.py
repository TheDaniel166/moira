"""
Phase 5: Oracle Validation for LOLA profile adjustment.
Compares native-backed results against the captured NumPy baseline.
"""

import json
import pytest
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from moira.lunar_limb import official_lunar_limb_profile_adjustment

def test_lunar_limb_oracle_parity():
    baseline_path = Path("tests/oracle_lunar_limb_baseline.json")
    if not baseline_path.exists():
        pytest.skip("Oracle baseline not found. Run scripts/capture_lunar_limb_oracle.py first.")
        
    with open(baseline_path, "r") as f:
        baseline = json.load(f)
        
    print(f"\nValidating {len(baseline)} test cases against oracle...")
    
    failures = []
    for i, entry in enumerate(baseline):
        inp = entry["input"]
        expected = entry["output"]
        
        actual = official_lunar_limb_profile_adjustment(
            inp["jd_ut"],
            inp["observer_lat"],
            inp["observer_lon"],
            inp["observer_elev_m"],
            inp["position_angle_deg"],
            inp["moon_distance_km"]
        )
        
        diff = abs(actual - expected)
        # Parity threshold: 1e-6 degrees (Requirement 20.2)
        if diff > 1e-6:
            failures.append({
                "case": i + 1,
                "input": inp,
                "expected": expected,
                "actual": actual,
                "diff": diff
            })
        else:
            print(f"Case {i+1}: PASS (diff={diff:.2e})")
            
    if failures:
        print("\nFAILURES detected:")
        for f in failures:
            print(f"Case {f['case']}: Expected {f['expected']}, Got {f['actual']}, Diff {f['diff']}")
        assert not failures, f"{len(failures)} oracle validation failures"
    else:
        print("\nALL ORACLE CASES PASSED.")

if __name__ == "__main__":
    test_lunar_limb_oracle_parity()

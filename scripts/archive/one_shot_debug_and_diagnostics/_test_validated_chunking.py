#!/usr/bin/env python
"""
Test the validated chunking logic for Apollo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import the fixed function
from rebuild_shard_18 import fetch_horizons_long

cmd = "'1862;'"  # Apollo
start_jd = 2305447.5
end_jd = 2451600.0  # Just past the problematic boundary
step_days = 2

print("Testing validated chunking for Apollo...")
print(f"Start: {start_jd}, End: {end_jd}, Step: {step_days}d\n")

try:
    states = fetch_horizons_long(cmd, start_jd, end_jd, step_days)
    print(f"\nSUCCESS: Fetched {len(states)} states")
except RuntimeError as e:
    print(f"\nEXPECTED ERROR: {e}")
    print("\nThis confirms the discontinuity. We need a different approach.")

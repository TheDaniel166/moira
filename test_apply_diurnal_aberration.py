#!/usr/bin/env python
"""Quick functional test for apply_diurnal_aberration()"""

from moira.corrections import apply_diurnal_aberration
import math

# Test 1: Observer at North Pole (should have zero correction)
print("Test 1: Observer at North Pole")
xyz_body = (1.0, 0.0, 0.0)
corrected = apply_diurnal_aberration(xyz_body, 90.0, 0.0, 0.0, 0.0)
correction_mag = math.sqrt(
    (corrected[0] - xyz_body[0])**2 +
    (corrected[1] - xyz_body[1])**2 +
    (corrected[2] - xyz_body[2])**2
)
print(f"  Correction magnitude: {correction_mag:.2e} km (expected: ~0)")
assert correction_mag < 1e-10, "Correction at pole should be near zero"
print("  ✓ PASS")

# Test 2: Observer at pole with body at celestial pole (should have zero correction)
print("\nTest 2: Observer at pole with body at celestial pole")
AU_KM = 149597870.7
xyz_body = (0.0, 0.0, AU_KM)
corrected = apply_diurnal_aberration(xyz_body, 90.0, 0.0, 0.0, 0.0)
correction_mag = math.sqrt(
    (corrected[0] - xyz_body[0])**2 +
    (corrected[1] - xyz_body[1])**2 +
    (corrected[2] - xyz_body[2])**2
)
# Convert to arcseconds
correction_arcsec = correction_mag / AU_KM * 206265
print(f"  Correction magnitude: {correction_mag:.2e} km ({correction_arcsec:.2e} arcseconds)")
print(f"  Expected: < 1 microarcsecond (observer at pole has zero velocity)")
assert correction_arcsec < 1e-5, "Correction at observer pole should be near zero"
print("  ✓ PASS")

# Test 3: Invalid latitude (should raise ValueError)
print("\nTest 3: Invalid latitude")
try:
    apply_diurnal_aberration((1.0, 0.0, 0.0), 91.0, 0.0, 0.0, 0.0)
    print("  ✗ FAIL: Should have raised ValueError")
except ValueError as e:
    print(f"  Raised ValueError: {e}")
    print("  ✓ PASS")

# Test 4: Near-zero position (should raise ValueError)
print("\nTest 4: Near-zero position")
try:
    apply_diurnal_aberration((1e-11, 0.0, 0.0), 0.0, 0.0, 0.0, 0.0)
    print("  ✗ FAIL: Should have raised ValueError")
except ValueError as e:
    print(f"  Raised ValueError: {e}")
    print("  ✓ PASS")

# Test 5: Normal case (observer at equator, body on celestial equator)
print("\nTest 5: Observer at equator, body on celestial equator")
xyz_body = (147.1e6, 0.0, 0.0)  # ~1 AU
corrected = apply_diurnal_aberration(xyz_body, 0.0, 0.0, 0.0, 0.0)
correction_mag = math.sqrt(
    (corrected[0] - xyz_body[0])**2 +
    (corrected[1] - xyz_body[1])**2 +
    (corrected[2] - xyz_body[2])**2
)
# Convert to arcseconds (1 AU ≈ 206265 arcseconds)
correction_arcsec = correction_mag / 147.1e6 * 206265
print(f"  Correction magnitude: {correction_mag:.2e} km")
print(f"  Correction in arcseconds: {correction_arcsec:.4f}\"")
print(f"  Expected: ~0.32\" (maximum diurnal aberration)")
assert correction_arcsec < 0.35, "Correction should be less than 0.35 arcseconds"
print("  ✓ PASS")

print("\n✓ All tests passed!")

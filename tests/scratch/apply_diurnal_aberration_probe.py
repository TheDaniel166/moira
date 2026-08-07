#!/usr/bin/env python
"""Manual functional probe for ``apply_diurnal_aberration()``."""

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
if correction_mag >= 1e-10:
    raise AssertionError("Correction at pole should be near zero")
print("  PASS")

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
print("  Expected: < 1 microarcsecond (observer at pole has zero velocity)")
if correction_arcsec >= 1e-5:
    raise AssertionError("Correction at observer pole should be near zero")
print("  PASS")

# Test 3: Invalid latitude (should raise ValueError)
print("\nTest 3: Invalid latitude")
try:
    apply_diurnal_aberration((1.0, 0.0, 0.0), 91.0, 0.0, 0.0, 0.0)
except ValueError as e:
    print(f"  Raised ValueError: {e}")
    print("  PASS")
else:
    raise AssertionError("Invalid latitude should raise ValueError")

# Test 4: Near-zero position (should raise ValueError)
print("\nTest 4: Near-zero position")
try:
    apply_diurnal_aberration((1e-11, 0.0, 0.0), 0.0, 0.0, 0.0, 0.0)
except ValueError as e:
    print(f"  Raised ValueError: {e}")
    print("  PASS")
else:
    raise AssertionError("Near-zero position should raise ValueError")

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
print("  Expected: ~0.32\" (maximum diurnal aberration)")
if not 0.30 < correction_arcsec < 0.35:
    raise AssertionError("Correction should remain near 0.32 arcseconds")
print("  PASS")

print("\nAll tests passed.")

"""
Investigate the Moon's 0.255 arcsecond longitude error against Horizons.

This script examines the computational path from barycentric state vectors
through geocentric conversion, ecliptic transformation, and apparent position
to identify where the 0.255" discrepancy originates.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body
from moira.julian import julian_day
from moira.planets import planet_at
from moira.spk_reader import SpkReader

# Test date from oracle: 2026-05-09 00:00:00 UTC
TARGET_DATE = (2026, 5, 9, 0.0)
JD_UT = julian_day(*TARGET_DATE)

# Oracle values from Horizons
HORIZONS_LON = 308.3696307
HORIZONS_LAT = -2.3375902

print("=" * 80)
print("Moon Longitude Error Investigation")
print("=" * 80)
print(f"\nTarget: {TARGET_DATE[0]}-{TARGET_DATE[1]:02d}-{TARGET_DATE[2]:02d} {TARGET_DATE[3]:02.0f}:00:00 UTC")
print(f"JD_UT: {JD_UT}")
print(f"\nHorizons Reference:")
print(f"  Longitude: {HORIZONS_LON}°")
print(f"  Latitude:  {HORIZONS_LAT}°")

# Load planetary kernel
planetary_path = find_planetary_kernel()
if planetary_path is None:
    raise RuntimeError("No planetary kernel found")

print(f"\nKernel: {planetary_path.name}")

# Compute Moon position using Moira
reader = SpkReader(planetary_path)
try:
    result = planet_at(Body.MOON, JD_UT, reader=reader)
    
    print(f"\nMoira Result:")
    print(f"  Longitude: {result.longitude}°")
    print(f"  Latitude:  {result.latitude}°")
    print(f"  Distance:  {result.distance} km")
    print(f"  Speed:     {result.speed}°/day")
    
    # Calculate error
    lon_error_deg = result.longitude - HORIZONS_LON
    lon_error_arcsec = lon_error_deg * 3600.0
    lat_error_deg = result.latitude - HORIZONS_LAT
    lat_error_arcsec = lat_error_deg * 3600.0
    
    print(f"\nError vs Horizons:")
    print(f"  Longitude: {lon_error_arcsec:+.6f}″ ({lon_error_deg:+.10f}°)")
    print(f"  Latitude:  {lat_error_arcsec:+.6f}″ ({lat_error_deg:+.10f}°)")
    
    # Now let's examine the intermediate steps
    print("\n" + "=" * 80)
    print("Computational Path Analysis")
    print("=" * 80)
    
    # Get raw barycentric state for Moon (NAIF 301 relative to SSB 0)
    moon_bary_pos, moon_bary_vel = reader.position_and_velocity(0, 301, JD_UT)
    print(f"\n1. Moon Barycentric State (NAIF 301 relative to SSB 0):")
    print(f"   Position: [{moon_bary_pos[0]:15.6f}, {moon_bary_pos[1]:15.6f}, {moon_bary_pos[2]:15.6f}] km")
    print(f"   Velocity: [{moon_bary_vel[0]:15.10f}, {moon_bary_vel[1]:15.10f}, {moon_bary_vel[2]:15.10f}] km/s")
    
    # Get Earth barycentric state (NAIF 399 relative to SSB 0)
    earth_bary_pos, earth_bary_vel = reader.position_and_velocity(0, 399, JD_UT)
    print(f"\n2. Earth Barycentric State (NAIF 399 relative to SSB 0):")
    print(f"   Position: [{earth_bary_pos[0]:15.6f}, {earth_bary_pos[1]:15.6f}, {earth_bary_pos[2]:15.6f}] km")
    print(f"   Velocity: [{earth_bary_vel[0]:15.10f}, {earth_bary_vel[1]:15.10f}, {earth_bary_vel[2]:15.10f}] km/s")
    
    # Compute geocentric state
    moon_geo_pos = [
        moon_bary_pos[0] - earth_bary_pos[0],
        moon_bary_pos[1] - earth_bary_pos[1],
        moon_bary_pos[2] - earth_bary_pos[2],
    ]
    moon_geo_vel = [
        moon_bary_vel[0] - earth_bary_vel[0],
        moon_bary_vel[1] - earth_bary_vel[1],
        moon_bary_vel[2] - earth_bary_vel[2],
    ]
    
    print(f"\n3. Moon Geocentric State (Moon - Earth):")
    print(f"   Position: [{moon_geo_pos[0]:15.6f}, {moon_geo_pos[1]:15.6f}, {moon_geo_pos[2]:15.6f}] km")
    print(f"   Velocity: [{moon_geo_vel[0]:15.10f}, {moon_geo_vel[1]:15.10f}, {moon_geo_vel[2]:15.10f}] km/s")
    
    # Distance
    import math
    distance = math.sqrt(moon_geo_pos[0]**2 + moon_geo_pos[1]**2 + moon_geo_pos[2]**2)
    print(f"   Distance: {distance:.6f} km")
    
    # Convert to ecliptic coordinates manually
    # Moira uses J2000 ecliptic, obliquity ε ≈ 23.43928°
    from moira.ecliptic import equatorial_to_ecliptic
    
    ecl_pos = equatorial_to_ecliptic(moon_geo_pos[0], moon_geo_pos[1], moon_geo_pos[2])
    print(f"\n4. Ecliptic Coordinates (J2000):")
    print(f"   X: {ecl_pos[0]:15.6f} km")
    print(f"   Y: {ecl_pos[1]:15.6f} km")
    print(f"   Z: {ecl_pos[2]:15.6f} km")
    
    # Compute longitude and latitude
    lon_rad = math.atan2(ecl_pos[1], ecl_pos[0])
    lon_deg = math.degrees(lon_rad)
    if lon_deg < 0:
        lon_deg += 360.0
    
    ecl_distance = math.sqrt(ecl_pos[0]**2 + ecl_pos[1]**2 + ecl_pos[2]**2)
    lat_rad = math.asin(ecl_pos[2] / ecl_distance)
    lat_deg = math.degrees(lat_rad)
    
    print(f"\n5. Spherical Ecliptic:")
    print(f"   Longitude: {lon_deg}°")
    print(f"   Latitude:  {lat_deg}°")
    print(f"   Distance:  {ecl_distance:.6f} km")
    
    # Compare with Moira's result
    print(f"\n6. Comparison with Moira planet_at():")
    print(f"   Moira longitude: {result.longitude}°")
    print(f"   Manual longitude: {lon_deg}°")
    print(f"   Difference: {(result.longitude - lon_deg) * 3600.0:.6f}″")
    
    print("\n" + "=" * 80)
    print("Hypothesis Testing")
    print("=" * 80)
    
    print("\nPossible sources of 0.255″ error:")
    print("1. Light-time correction (Horizons uses apparent position)")
    print("2. Aberration (annual + diurnal)")
    print("3. Nutation (Horizons may apply nutation to ecliptic)")
    print("4. Precession (if Horizons uses date ecliptic vs J2000)")
    print("5. Numerical precision in kernel interpolation")
    print("6. Different obliquity constants")
    
    # Light-time estimate
    light_speed_km_s = 299792.458
    light_time_s = distance / light_speed_km_s
    light_time_days = light_time_s / 86400.0
    
    # Moon moves ~13.2°/day, so light-time shift is:
    moon_motion_deg_per_day = 13.2  # approximate
    light_time_shift_deg = moon_motion_deg_per_day * light_time_days
    light_time_shift_arcsec = light_time_shift_deg * 3600.0
    
    print(f"\nLight-time correction estimate:")
    print(f"  Distance: {distance:.1f} km")
    print(f"  Light-time: {light_time_s:.6f} s ({light_time_days * 86400:.6f} s)")
    print(f"  Moon motion: ~{moon_motion_deg_per_day}°/day")
    print(f"  Expected shift: ~{light_time_shift_arcsec:.3f}″")
    print(f"  Observed error: {lon_error_arcsec:.3f}″")
    print(f"  Ratio: {lon_error_arcsec / light_time_shift_arcsec:.2f}x")
    
    print("\n" + "=" * 80)
    print("Conclusion")
    print("=" * 80)
    print("\nThe 0.255″ error is likely due to:")
    if abs(lon_error_arcsec / light_time_shift_arcsec - 1.0) < 0.2:
        print("  → Light-time correction (Horizons uses apparent position)")
        print("    Moira computes geometric position, Horizons returns apparent.")
    else:
        print("  → Combination of light-time, aberration, and/or frame differences")
        print("    Further investigation needed to isolate the exact cause.")
    
finally:
    reader.close()

print("\n" + "=" * 80)

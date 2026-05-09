"""
Simple investigation: Is the 0.255″ Moon error due to light-time correction?

Horizons returns "apparent" positions with light-time applied.
Moira also applies light-time by default.

The Moon moves ~13.2°/day, and light-time is ~1.28 seconds.
Expected light-time shift: 13.2° × (1.28/86400) ≈ 0.195 arcseconds

The observed error is 0.255″, which is close but not exact.
Let's test if disabling light-time (apparent=False) eliminates the error.
"""
from __future__ import annotations

import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body
from moira.julian import julian_day
from moira.planets import planet_at
from moira.spk_reader import SpkReader

# Test date from oracle
TARGET_DATE = date(2026, 5, 9)
JD_UT = julian_day(2026, 5, 9, 0.0)

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

def get_horizons_position(command: str, target_date: date) -> tuple[float, float]:
    """Fetch Horizons OBSERVER geocentric apparent ecliptic position."""
    start_dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, tzinfo=timezone.utc)
    stop_dt = start_dt + timedelta(days=1)
    fmt = "%Y-%b-%d %H:%M"
    params = {
        "format": "text",
        "COMMAND": command,
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",
        "START_TIME": f"'{start_dt.strftime(fmt)}'",
        "STOP_TIME": f"'{stop_dt.strftime(fmt)}'",
        "STEP_SIZE": "'1 d'",
        "QUANTITIES": "'31'",
        "ANG_FORMAT": "DEG",
    }
    url = HORIZONS_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode("utf-8")

    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if s == "$SOE":
            in_data = True
            continue
        if s == "$EOE":
            break
        if not in_data or not s:
            continue
        parts = s.split()
        if len(parts) >= 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                pass
    raise RuntimeError(f"Could not parse Horizons response for {command}")

print("=" * 80)
print("Moon 0.255″ Error Investigation")
print("=" * 80)
print(f"\nDate: {TARGET_DATE}")
print(f"JD_UT: {JD_UT}")

# Get Horizons reference
print("\nFetching Horizons reference...")
horizons_lon, horizons_lat = get_horizons_position("301", TARGET_DATE)
print(f"Horizons (apparent): {horizons_lon}° lon, {horizons_lat}° lat")

# Load kernel
planetary_path = find_planetary_kernel()
reader = SpkReader(planetary_path)

try:
    # Test 1: Moira with apparent=True (default, includes light-time)
    result_apparent = planet_at(Body.MOON, JD_UT, reader=reader, apparent=True)
    lon_error_apparent = (result_apparent.longitude - horizons_lon) * 3600.0
    
    print(f"\nMoira (apparent=True):  {result_apparent.longitude}° lon")
    print(f"  Error: {lon_error_apparent:+.6f}″")
    
    # Test 2: Moira with apparent=False (geometric, no light-time)
    result_geometric = planet_at(Body.MOON, JD_UT, reader=reader, apparent=False)
    lon_error_geometric = (result_geometric.longitude - horizons_lon) * 3600.0
    
    print(f"\nMoira (apparent=False): {result_geometric.longitude}° lon")
    print(f"  Error: {lon_error_geometric:+.6f}″")
    
    # Difference between apparent and geometric
    lon_diff = (result_apparent.longitude - result_geometric.longitude) * 3600.0
    print(f"\nDifference (apparent - geometric): {lon_diff:+.6f}″")
    
    # Estimate light-time shift
    distance_km = result_apparent.distance
    light_speed_km_s = 299792.458
    light_time_s = distance_km / light_speed_km_s
    moon_motion_deg_per_day = result_apparent.speed
    light_time_shift_arcsec = moon_motion_deg_per_day * (light_time_s / 86400.0) * 3600.0
    
    print(f"\nLight-time calculation:")
    print(f"  Distance: {distance_km:.1f} km")
    print(f"  Light-time: {light_time_s:.6f} s")
    print(f"  Moon motion: {moon_motion_deg_per_day:.6f}°/day")
    print(f"  Expected shift: {light_time_shift_arcsec:.6f}″")
    
    print("\n" + "=" * 80)
    print("Analysis")
    print("=" * 80)
    
    if abs(lon_error_geometric) < abs(lon_error_apparent):
        print("\n✓ Geometric position is closer to Horizons than apparent position.")
        print("  This suggests Horizons may NOT be applying light-time correction,")
        print("  or is using a different correction methodology.")
    else:
        print("\n✓ Apparent position is closer to Horizons than geometric position.")
        print("  This confirms Horizons is applying light-time correction.")
    
    if abs(lon_diff - light_time_shift_arcsec) < 0.05:
        print(f"\n✓ Moira's light-time shift ({lon_diff:.3f}″) matches the expected")
        print(f"  shift ({light_time_shift_arcsec:.3f}″) within 0.05″.")
    else:
        print(f"\n⚠ Moira's light-time shift ({lon_diff:.3f}″) differs from expected")
        print(f"  shift ({light_time_shift_arcsec:.3f}″) by {abs(lon_diff - light_time_shift_arcsec):.3f}″.")
    
    print("\n" + "=" * 80)
    print("Conclusion")
    print("=" * 80)
    
    if abs(lon_error_apparent) < 0.1:
        print("\n✓ The 0.255″ error is within sub-0.3 arcsecond precision.")
        print("  This is excellent agreement for lunar ephemeris.")
        print("  The residual likely comes from:")
        print("    - Different nutation series (IAU 2000A vs IAU 2000B)")
        print("    - Different obliquity constants")
        print("    - Numerical precision in Chebyshev interpolation")
        print("    - Frame bias differences")
    else:
        print(f"\n⚠ The {lon_error_apparent:.3f}″ error requires further investigation.")
        print("  Possible causes:")
        print("    - Light-time iteration convergence")
        print("    - Aberration methodology")
        print("    - Nutation series differences")
        print("    - Precession model differences")
    
finally:
    reader.close()

print("\n" + "=" * 80)

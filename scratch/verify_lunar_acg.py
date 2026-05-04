
import math
from moira.planets import sky_position_at, planet_at
from moira.constants import DEG2RAD, RAD2DEG
from moira.julian import apparent_sidereal_time, ut_to_tt
from moira.obliquity import nutation, true_obliquity

# JD for a recent date: 2024-01-01 00:00:00 UTC
jd_ut = 2460310.5
phi = 45.0  # Latitude 45°N
phi_r = phi * DEG2RAD
_WGS84_E2 = 0.00669437999014
phi_gc_r = math.atan((1.0 - _WGS84_E2) * math.tan(phi_r))

# 1. Get Geocentric Moon RA/Dec
jd_tt = ut_to_tt(jd_ut)
dpsi, deps = nutation(jd_tt)
obliq = true_obliquity(jd_tt)
gast = apparent_sidereal_time(jd_ut, dpsi, obliq)

moon_geo = planet_at("Moon", jd_ut, apparent=True)
ra_geo = moon_geo.right_ascension if hasattr(moon_geo, 'right_ascension') else moon_geo.longitude # Wait, planet_at returns PlanetData (ecliptic) or Cartesian.
# Actually sky_position_at is better for RA/Dec.

# Use sky_position_at with a dummy location to get "geocentric-like" RA/Dec if needed, 
# but better to just use geocentric=True vs topocentric.
# Actually, sky_position_at ALWAYS does topocentric.
# planet_at does geocentric by default.

# Let's get raw RA/Dec from coordinates to be sure.
from moira.coordinates import icrf_to_equatorial
# Geocentric ICRF
xyz_geo = planet_at("Moon", jd_ut, frame='cartesian', apparent=True).x, planet_at("Moon", jd_ut, frame='cartesian', apparent=True).y, planet_at("Moon", jd_ut, frame='cartesian', apparent=True).z
ra_geo, dec_geo, _ = icrf_to_equatorial(xyz_geo)

# 2. Get Topocentric Moon RA/Dec at Latitude 45
# We need an approximate longitude to get LST. Let's just pick 0 for now.
sky_topo = sky_position_at("Moon", jd_ut, observer_lat=phi, observer_lon=0.0)
ra_topo = sky_topo.right_ascension
dec_topo = sky_topo.declination

print(f"Moon RA (Geo): {ra_geo:.5f}°, Dec: {dec_geo:.5f}°")
print(f"Moon RA (Topo at Lat 45): {ra_topo:.5f}°, Dec: {dec_topo:.5f}°")

# 3. Calculate Hour Angle and Longitude for ASC
def calc_lon_asc(ra, dec, phi_gc_rad, gast_deg):
    dec_r = dec * DEG2RAD
    cos_ha = -math.tan(phi_gc_rad) * math.tan(dec_r)
    if abs(cos_ha) > 1.0: return None
    ha_deg = math.acos(cos_ha) * RAD2DEG
    return (ra - gast_deg - ha_deg) % 360.0

lon_geo = calc_lon_asc(ra_geo, dec_geo, phi_gc_r, gast)
lon_topo = calc_lon_asc(ra_topo, dec_topo, phi_gc_r, gast)

if lon_geo and lon_topo:
    diff_deg = (lon_topo - lon_geo + 180) % 360 - 180
    diff_km = diff_deg * 111.32 * math.cos(phi_r) # Approx km at this latitude
    print(f"Geocentric ASC Longitude: {lon_geo:.5f}°")
    print(f"Topocentric ASC Longitude: {lon_topo:.5f}°")
    print(f"Difference: {diff_deg:.5f}° (approx {abs(diff_km):.2f} km)")
else:
    print("Moon is circumpolar at this latitude.")

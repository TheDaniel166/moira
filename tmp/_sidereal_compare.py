"""Compare GMST (oracle) vs apparent_sidereal_time (Moira) and resulting Sun altitude."""
import math
from moira.julian import apparent_sidereal_time, greenwich_mean_sidereal_time
from moira.heliacal import _sun_alt

LAT, LON = 32.55, 44.42

# JD for 2025-Aug-03 01:41.6 UT (oracle's twilight for Sirius)
JD = 2460890.5 + 1.694 / 24.0  # = 2460890.57058

# My oracle's GMST (IAU 1982 formula, from the validation script)
def my_gmst(jd_ut):
    T = (jd_ut - 2451545.0) / 36525.0
    θ = (
        280.46061837
        + 360.98564736629 * (jd_ut - 2451545.0)
        + 0.000387933 * T * T
        - T * T * T / 38710000.0
    )
    return θ % 360.0

moira_gast_deg = apparent_sidereal_time(JD, LON) * 15.0 % 360.0   # Moira apparent sidereal time → degrees
try:
    moira_gmst_deg = greenwich_mean_sidereal_time(JD) * 15.0 % 360.0
    print(f"Moira GMST:  {moira_gmst_deg:.6f}°")
except Exception as e:
    moira_gmst_deg = None
    print(f"GMST not available: {e}")

my_gmst_deg = my_gmst(JD)
my_lst_deg  = (my_gmst_deg + LON) % 360.0

print(f"JD:                {JD:.6f}")
print(f"My GMST:           {my_gmst_deg:.6f}°")
print(f"My LST (Babylon):  {my_lst_deg:.6f}°")
print(f"Moira GAST (LST):  {moira_gast_deg:.6f}°")
print(f"Difference:        {moira_gast_deg - my_lst_deg:+.6f}°")
print()

# Now compute Sun altitude two ways
# 1. Oracle: Horizons RA/Dec for the Sun at approximately this moment
# Let's use a Horizons typical Sun RA/Dec for Aug-03 2025 dawn at Babylon
# From the 2-min run we know the crossing is around 01:41.6 UT Aug-03
# Let me use what the script would have interpolated
# I'll approximate: Sun RA ~131.5°, Sun Dec ~17.3° for Aug-03 at dawn
# (cardinal values from rough calcs)
# Actually let me just show the sidereal-time difference effect

print("Sidereal time impact on Sun altitude:")
print(f"  If LST shifts by {moira_gast_deg - my_lst_deg:+.4f}°,")
# Sun altitude sensitivity at HA ~= LST - Sun_RA
# Near horizon, dalt/dHA ≈ cos(lat)*cos(dec)*sin(HA) / cos(alt)
# At dawn, HA ~ -80° (rough), dec ~ 17°, lat = 32.55°, alt ~ -7.5°
HA_rad = math.radians(-80)
dec_rad = math.radians(17.0)
lat_rad = math.radians(LAT)
alt_rad = math.radians(-7.5)
dalt_dHA = - math.cos(lat_rad) * math.cos(dec_rad) * math.sin(HA_rad) / math.cos(alt_rad)
delta_lst = moira_gast_deg - my_lst_deg
delta_alt = dalt_dHA * delta_lst
print(f"  dalt/dHA @ HA=-80°, dec=17°: {dalt_dHA:.4f} °/°")
print(f"  Expected altitude shift: {delta_alt:.4f}°")
print()

# Moira's _sun_alt
print(f"Moira _sun_alt(JD, LAT, LON) = {_sun_alt(JD, LAT, LON):.4f}°")
print(f"Oracle constructed Sun=-av = -7.500°")
print(f"Difference: {_sun_alt(JD, LAT, LON) - (-7.5):+.4f}°")

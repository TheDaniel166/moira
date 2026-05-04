import math
import erfa

# Kapteyn's Star
ra_deg = 77.9190989
dec_deg = -45.0184083
pmra_mas = 6505.74
pmdec_mas = -5731.39
px_mas = 255.27
rv_km_s = 245.5

ra_rad = math.radians(ra_deg)
dec_rad = math.radians(dec_deg)
pmra_rad_yr = (pmra_mas / 1000.0 / 3600.0) * (math.pi / 180.0) / math.cos(dec_rad)
pmdec_rad_yr = (pmdec_mas / 1000.0 / 3600.0) * (math.pi / 180.0)
px_arcsec = px_mas / 1000.0

# ERFA propagated 8000 years
dt_years = 8000.0
ra2, dec2, _, _, _, _ = erfa.starpm(ra_rad, dec_rad, pmra_rad_yr, pmdec_rad_yr, px_arcsec, rv_km_s, 2451545.0, 0.0, 2451545.0 + dt_years * 365.25, 0.0)
print(f"ERFA +8000 ra: {math.degrees(ra2)}, dec: {math.degrees(dec2)}")

# Moira method
cos_dec = math.cos(dec_rad)
sin_dec = math.sin(dec_rad)
cos_ra = math.cos(ra_rad)
sin_ra = math.sin(ra_rad)

p_hat = (cos_dec * cos_ra, cos_dec * sin_ra, sin_dec)
east_hat = (-sin_ra, cos_ra, 0.0)
north_hat = (-sin_dec * cos_ra, -sin_dec * sin_ra, cos_dec)

dra_dt = pmra_mas * (math.pi / 180.0 / 3600.0 / 1000.0) / cos_dec
ddec_dt = pmdec_mas * (math.pi / 180.0 / 3600.0 / 1000.0)

tangential_velocity = (
    dra_dt * cos_dec * east_hat[0] + ddec_dt * north_hat[0],
    dra_dt * cos_dec * east_hat[1] + ddec_dt * north_hat[1],
    dra_dt * cos_dec * east_hat[2] + ddec_dt * north_hat[2]
)

distance_pc = 1000.0 / px_mas

# EXACT conversion factor for km/s to pc/yr
# 1 AU = 149597870.7 km
# 1 pc = 206264.806247096355 AU
# 1 Julian year = 31557600 s
_KM_S_TO_PC_YR = 31557600.0 / (149597870.7 * 206264.806247096355)

rv_pc_yr = rv_km_s * _KM_S_TO_PC_YR

propagated = (
    distance_pc * p_hat[0] + (distance_pc * tangential_velocity[0] + rv_pc_yr * p_hat[0]) * dt_years,
    distance_pc * p_hat[1] + (distance_pc * tangential_velocity[1] + rv_pc_yr * p_hat[1]) * dt_years,
    distance_pc * p_hat[2] + (distance_pc * tangential_velocity[2] + rv_pc_yr * p_hat[2]) * dt_years
)

norm = math.sqrt(propagated[0]**2 + propagated[1]**2 + propagated[2]**2)
moira_x = propagated[0]/norm
moira_y = propagated[1]/norm
moira_z = propagated[2]/norm

m_dec = math.degrees(math.asin(moira_z))
m_ra = math.degrees(math.atan2(moira_y, moira_x)) % 360.0
print(f"Moira proposed ra2: {m_ra}, dec2: {m_dec}")

dot = math.cos(ra2)*math.cos(dec2)*moira_x + math.sin(ra2)*math.cos(dec2)*moira_y + math.sin(dec2)*moira_z
print(f"Divergence: {math.degrees(math.acos(dot))} degrees")

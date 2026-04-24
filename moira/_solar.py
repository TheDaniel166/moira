"""
Moira — _solar.py
Internal solar helpers shared by hermetic_decans and planetary_hours.

Boundary: owns solar declination/RA derivation and the sunrise/sunset
approximation + iterative refinement pipeline. Does NOT own planetary
hour arithmetic, decan assignment, or any public API surface. Delegates
planetary position computation to planets.py and obliquity calculation
to obliquity.py.

Import-time side effects: None

External dependency assumptions:
    - DE441 kernel must be accessible via spk_reader for solar positions
    - No Qt main thread requirements
    - Pure computational module

Public surface / exports:
    _solar_declination_ra()    — internal solar declination and RA computation
    _sunrise_sunset_approx()   — internal sunrise/sunset approximation helpers
    (Note: This is an internal module with no public API)
"""

import math

from .constants import Body
from .julian import ut_to_tt
from .obliquity import true_obliquity
from .planets import planet_at
from .spk_reader import SpkReader


def _solar_declination_ra(jd: float, reader: SpkReader) -> tuple[float, float]:
    """Return (declination_deg, right_ascension_deg) of the Sun at jd."""
    p = planet_at(Body.SUN, jd, reader=reader)
    obl = true_obliquity(ut_to_tt(jd))
    obl_r = math.radians(obl)
    lon_r = math.radians(p.longitude)
    lat_r = math.radians(p.latitude)

    x = math.cos(lat_r) * math.cos(lon_r)
    y = math.cos(lat_r) * math.sin(lon_r) * math.cos(obl_r) - math.sin(lat_r) * math.sin(obl_r)
    z = math.cos(lat_r) * math.sin(lon_r) * math.sin(obl_r) + math.sin(lat_r) * math.cos(obl_r)

    dec = math.degrees(math.asin(z))
    ra  = math.degrees(math.atan2(y, x)) % 360.0
    return dec, ra


def _sunrise_sunset(
    jd_noon: float,
    latitude: float,
    longitude: float,
    reader: SpkReader,
    altitude_deg: float = -0.833,
) -> tuple[float, float]:
    """
    Compute sunrise and sunset JD for the calendar day containing jd_noon.

    Parameters
    ----------
    jd_noon      : approximate solar noon JD for the day
    latitude     : geographic latitude (degrees, N positive)
    longitude    : geographic longitude (degrees, E positive)
    altitude_deg : solar altitude at rise/set (default −0.833° ≈ −50')

    Returns
    -------
    (jd_sunrise, jd_sunset) in UT
    """
    dec, _ = _solar_declination_ra(jd_noon, reader)
    lat_r = math.radians(latitude)
    dec_r = math.radians(dec)
    alt_r = math.radians(altitude_deg)

    cos_H = ((math.sin(alt_r) - math.sin(lat_r) * math.sin(dec_r))
             / (math.cos(lat_r) * math.cos(dec_r)))

    if cos_H > 1.0:
        return jd_noon, jd_noon          # polar night — sun never rises
    if cos_H < -1.0:
        return jd_noon - 0.5, jd_noon + 0.5   # midnight sun — sun never sets

    H_deg = math.degrees(math.acos(cos_H))

    jd_day_start = math.floor(jd_noon - 0.5) + 0.5
    noon_frac = 0.5 - longitude / 360.0
    jd_solar_noon = jd_day_start + noon_frac

    sunrise_frac = H_deg / 360.0
    jd_sunrise = jd_solar_noon - sunrise_frac
    jd_sunset  = jd_solar_noon + sunrise_frac

    return jd_sunrise, jd_sunset


def _refine_sunrise(
    jd_approx: float,
    latitude: float,
    longitude: float,
    reader: SpkReader,
    is_rise: bool,
    tol_days: float = 1.0 / 86400,   # 1 second
) -> float:
    """Iteratively refine sunrise or sunset time."""
    jd = jd_approx
    for _ in range(5):
        dec, _ = _solar_declination_ra(jd, reader)
        lat_r = math.radians(latitude)
        dec_r = math.radians(dec)
        alt_r = math.radians(-0.833)

        cos_H = ((math.sin(alt_r) - math.sin(lat_r) * math.sin(dec_r))
                 / (math.cos(lat_r) * math.cos(dec_r)))
        cos_H = max(-1.0, min(1.0, cos_H))
        H_deg = math.degrees(math.acos(cos_H))

        jd_day_start = math.floor(jd - 0.5) + 0.5
        noon_frac = 0.5 - longitude / 360.0
        jd_solar_noon = jd_day_start + noon_frac

        sunrise_frac = H_deg / 360.0
        jd_new = jd_solar_noon - sunrise_frac if is_rise else jd_solar_noon + sunrise_frac

        if abs(jd_new - jd) < tol_days:
            break
        jd = jd_new
    return jd

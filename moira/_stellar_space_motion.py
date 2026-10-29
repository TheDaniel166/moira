"""Stellar space motion: the single implementation of catalog propagation.

Governing object: a star moving in a straight line at constant velocity
relative to the solar-system barycenter. The catalog supplies its ICRS
direction at a reference epoch, its proper motion (right ascension component
already multiplied by cos(declination)), its parallax and its radial velocity.
Stage 1 of ``wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md`` advances that
position by the elapsed Julian years; the direction of the result is the
astrometric direction at the date.

The expressions are written once over an arithmetic adapter, so that float
evaluation (``moira.stars``, ``moira.deep_sky``,
``moira.lunar_occultation_contacts``) and the certified interval enclosures of
``moira._gochara_window_astronomy`` evaluate the same formula in the same
order. Normalization stays with the caller, because floats and intervals
normalize differently.

The native ``FixedStarEvaluator`` is the admitted C++ counterpart of this
stage; its parity is tested separately.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

# One milliarcsecond in radians.
MAS_TO_RAD = math.radians(1.0 / (1000.0 * 3600.0))
JULIAN_YEAR_DAYS = 365.25
# km/s to parsec per Julian year: Julian year in seconds, IAU 2012 au in km,
# parsec in au.
KM_S_TO_PC_PER_YEAR = 31557600.0 / (149597870.7 * 206264.806247096355)


@dataclass(frozen=True, slots=True)
class StellarArithmetic:
    """Vessel: the operations stage 1 needs from a number system.

    ``ra_rate(pmra_mas_yr, cos_dec)`` returns d(alpha)/dt in radians per year
    and owns the policy at the celestial poles, where cos(declination) is zero.
    """

    radians: Callable[[float], Any]
    cos: Callable[[Any], Any]
    sin: Callable[[Any], Any]
    const: Callable[[float], Any]
    mas_to_rad: Any
    km_s_to_pc_per_year: Any
    ra_rate: Callable[[float, Any], Any]


def _float_ra_rate(pmra_mas_yr: float, cos_dec: float) -> float:
    # At a pole the right-ascension rate is undefined; the tangent-plane
    # velocity there comes from the declination component alone.
    if abs(cos_dec) > 1e-12:
        return pmra_mas_yr * MAS_TO_RAD / cos_dec
    return 0.0


FLOAT_ARITHMETIC = StellarArithmetic(
    radians=math.radians,
    cos=math.cos,
    sin=math.sin,
    const=float,
    mas_to_rad=MAS_TO_RAD,
    km_s_to_pc_per_year=KM_S_TO_PC_PER_YEAR,
    ra_rate=_float_ra_rate,
)


def space_motion(
    ra_deg: float,
    dec_deg: float,
    pmra_mas_yr: float,
    pmdec_mas_yr: float,
    parallax_mas: float,
    radial_velocity_km_s: float,
    dt_years: Any,
    arithmetic: StellarArithmetic,
) -> tuple[tuple[Any, Any, Any], tuple[Any, Any, Any], bool]:
    """Advance a catalog star by ``dt_years`` of straight-line motion.

    Returns ``(catalog_unit, vector, has_distance)``:

    - ``catalog_unit``: the unit ICRS direction at the reference epoch;
    - ``vector``: the position after ``dt_years``, in parsecs when the parallax
      is finite and positive (``has_distance``), otherwise a direction-only
      vector whose length is not a distance;
    - ``has_distance``: whether radial velocity and distance participated.

    Without a usable parallax the star is treated as infinitely distant: only
    the proper motion moves the direction, and radial velocity has no effect.
    """

    a = arithmetic
    ra = a.radians(ra_deg)
    dec = a.radians(dec_deg)
    cos_dec, sin_dec = a.cos(dec), a.sin(dec)
    cos_ra, sin_ra = a.cos(ra), a.sin(ra)

    catalog_unit = (cos_dec * cos_ra, cos_dec * sin_ra, sin_dec)
    east = (-sin_ra, cos_ra, a.const(0.0))
    north = (-sin_dec * cos_ra, -sin_dec * sin_ra, cos_dec)

    ra_rate = a.ra_rate(pmra_mas_yr, cos_dec)
    dec_rate = pmdec_mas_yr * a.mas_to_rad
    tangential = tuple(
        ra_rate * cos_dec * e + dec_rate * n for e, n in zip(east, north)
    )

    if math.isfinite(parallax_mas) and parallax_mas > 0.0:
        distance_pc = a.const(1000.0) / parallax_mas
        radial_pc_per_year = radial_velocity_km_s * a.km_s_to_pc_per_year
        vector = tuple(
            distance_pc * p + (v * distance_pc + radial_pc_per_year * p) * dt_years
            for p, v in zip(catalog_unit, tangential)
        )
        return catalog_unit, vector, True
    vector = tuple(p + v * dt_years for p, v in zip(catalog_unit, tangential))
    return catalog_unit, vector, False


def astrometric_direction(
    ra_deg: float,
    dec_deg: float,
    pmra_mas_yr: float,
    pmdec_mas_yr: float,
    parallax_mas: float,
    radial_velocity_km_s: float,
    ref_epoch_jd: float,
    jd_tt: float,
) -> tuple[tuple[float, float, float], float | None]:
    """Return the float astrometric unit direction at ``jd_tt`` and the distance.

    The distance is in parsecs when the parallax is usable, else ``None``.
    At the reference epoch itself the catalog direction is returned unchanged.
    """

    dt_years = (jd_tt - ref_epoch_jd) / JULIAN_YEAR_DAYS
    catalog_unit, vector, has_distance = space_motion(
        ra_deg, dec_deg, pmra_mas_yr, pmdec_mas_yr, parallax_mas,
        radial_velocity_km_s, dt_years, FLOAT_ARITHMETIC,
    )
    norm = math.sqrt(vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2])
    distance_pc = norm if has_distance else None
    if dt_years == 0.0:
        return catalog_unit, distance_pc
    if norm == 0.0:
        return catalog_unit, distance_pc
    return (vector[0] / norm, vector[1] / norm, vector[2] / norm), distance_pc


__all__ = [
    "FLOAT_ARITHMETIC",
    "JULIAN_YEAR_DAYS",
    "KM_S_TO_PC_PER_YEAR",
    "MAS_TO_RAD",
    "StellarArithmetic",
    "astrometric_direction",
    "space_motion",
]

"""Instantaneous solar Besselian elements from Moira's native shadow axis.

The governing object is the lunar shadow line expressed on the geocentric
fundamental plane: the plane through Earth's centre perpendicular to that
line.  Positive ``x`` is east, positive ``y`` is north, and ``x``, ``y``,
``l1``, and ``l2`` are measured in Earth equatorial radii.  ``d`` and ``mu``
are degrees; the cone slopes ``tan_f1`` and ``tan_f2`` are dimensionless.

This module owns the coordinate representation and result semantics.  The
eclipse engine remains responsible for acquiring the DE/LE ephemeris states
and for enforcing Moira's Earth-reception light-time policy.

Authority:
    NASA/GSFC, "Besselian Elements of Solar Eclipses" and the eclipse
    technical-publication explanation of the fundamental plane.  Those
    sources govern the field meanings, orientation, units, polynomial time
    basis, and signed ``l2`` convention; they do not replace Moira's native
    DE441 state or mean-limb radius policy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from numbers import Real

from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from .coordinates import (
    mat_vec_mul,
    nutation_matrix_equatorial,
    precession_matrix_equatorial,
)
from .julian import apparent_sidereal_time
from .obliquity import nutation, true_obliquity


_Vec3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class _SolarShadowAxisState:
    """Private native shadow state shared by eclipse and Besselian products.

    ``axis_unit_away_from_sun`` points from the Moon away from the Sun.  The
    signed ``axis_projection_km`` is the Moon-origin projection on that axis;
    it is negative when the forward shadow ray reaches the geocentric
    fundamental plane.  Existing eclipse geometry reports an infinite axis
    distance when that physical ray points away from Earth.
    """

    sun_xyz_km: _Vec3
    moon_xyz_km: _Vec3
    axis_unit_away_from_sun: _Vec3
    axis_projection_km: float
    fundamental_plane_point_xyz_km: _Vec3 | None
    axis_distance_km: float
    sun_moon_distance_km: float
    center_sun_radius_deg: float
    center_moon_radius_deg: float
    surface_sun_radius_deg: float | None
    surface_moon_radius_deg: float | None


@dataclass(frozen=True, slots=True)
class SolarBesselianElements:
    """One instantaneous DE441/LE441-native solar Besselian element set.

    Parameters are evaluated at ``jd_tt``; ``jd_ut1`` records the public
    eclipse-engine input whose reader-bound clock conversion produced that TT
    instant.  This vessel is an instantaneous coordinate product and never
    performs an eclipse search.

    Field doctrine
    --------------
    ``x``, ``y``
        Shadow-axis coordinates on the fundamental plane in Earth equatorial
        radii.  Positive ``x`` is east and positive ``y`` is north.
    ``d``
        Declination of the Moon-to-Sun shadow-axis direction in the true
        equator and equinox of date, in degrees.
    ``mu``
        TT/TDT ephemeris hour angle of that direction at Greenwich, in
        degrees on ``[0, 360)``.  It is not physical GAST at ``jd_ut1``.
    ``l1``
        Penumbral radius on the fundamental plane in Earth equatorial radii.
    ``l2``
        NASA-signed central-shadow radius in Earth equatorial radii: negative
        is umbral/total at the plane; positive is antumbral/annular.
    ``tan_f1``, ``tan_f2``
        Dimensionless tangents of the penumbral and umbral cone half-angles.

    The radius metadata makes Moira's spherical mean-limb policy inspectable.
    NASA/GSFC's separate eclipse-map ``k1``/``k2`` lunar-radius convention is
    retained only as an external validation comparator.
    """

    jd_ut1: float
    jd_tt: float
    x: float
    y: float
    d: float
    mu: float
    l1: float
    l2: float
    tan_f1: float
    tan_f2: float
    ephemeris: str

    axis_model: str = field(
        default="earth_reception_light_time_center_of_mass",
        init=False,
    )
    frame: str = field(
        default="true_equator_and_equinox_of_date",
        init=False,
    )
    hour_angle_model: str = field(
        default="tt_ephemeris_hour_angle",
        init=False,
    )
    radius_model: str = field(
        default="moira_spherical_mean_limb",
        init=False,
    )
    earth_equatorial_radius_km: float = field(
        default=EARTH_RADIUS_KM,
        init=False,
    )
    sun_radius_km: float = field(default=SUN_RADIUS_KM, init=False)
    moon_radius_km: float = field(default=MOON_RADIUS_KM, init=False)

    def __post_init__(self) -> None:
        numeric_fields = (
            "jd_ut1",
            "jd_tt",
            "x",
            "y",
            "d",
            "mu",
            "l1",
            "l2",
            "tan_f1",
            "tan_f2",
        )
        for name in numeric_fields:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"SolarBesselianElements.{name} must be a real number")
            value = float(value)
            if not math.isfinite(value):
                raise ValueError(f"SolarBesselianElements.{name} must be finite")
            object.__setattr__(self, name, value)

        if not isinstance(self.ephemeris, str) or not self.ephemeris.strip():
            raise ValueError("SolarBesselianElements.ephemeris must identify its source")
        if not -90.0 <= self.d <= 90.0:
            raise ValueError("SolarBesselianElements.d must be within [-90, 90] degrees")
        if not 0.0 <= self.mu < 360.0:
            raise ValueError("SolarBesselianElements.mu must be within [0, 360) degrees")
        if not self.tan_f1 > self.tan_f2 > 0.0:
            raise ValueError("solar cone slopes must satisfy tan_f1 > tan_f2 > 0")
        if not self.l1 > 0.0:
            raise ValueError("the penumbral fundamental-plane radius l1 must be positive")
        if not self.l1 > abs(self.l2):
            raise ValueError(
                "the penumbral radius l1 must exceed the magnitude of signed l2"
            )


def _dot(a: _Vec3, b: _Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _ephemeris_apparent_sidereal_angle_tt(jd_tt: float) -> float:
    """Return the TT/TDT ephemeris sidereal angle used by Besselian ``mu``.

    Besselian polynomials use dynamical time and define ``mu`` as an ephemeris
    hour angle.  The IAU apparent-sidereal expression is therefore evaluated
    on that TT argument.  This named wrapper prevents callers from confusing
    the result with the physical Greenwich apparent sidereal time at UT1.
    """

    dpsi_deg, _deps_deg = nutation(jd_tt)
    return apparent_sidereal_time(
        jd_tt,
        dpsi_deg,
        true_obliquity(jd_tt),
    )


def _besselian_elements_from_native_shadow_state(
    *,
    jd_ut1: float,
    jd_tt: float,
    ephemeris: str,
    state: _SolarShadowAxisState,
) -> SolarBesselianElements:
    """Project one native shadow state onto the Besselian fundamental plane."""

    plane_point = state.fundamental_plane_point_xyz_km
    if plane_point is None or not math.isfinite(state.axis_distance_km):
        raise ValueError(
            "solar Besselian elements require the Moon-to-Sun geometry to place "
            "the forward lunar shadow ray toward Earth's fundamental plane"
        )

    # Besselian +Z points from the Moon toward the Sun.  The native eclipse ray
    # is stored in the physically propagating, away-from-Sun direction.
    axis_sunward_icrf = tuple(
        -component for component in state.axis_unit_away_from_sun
    )

    precession = precession_matrix_equatorial(jd_tt)
    nutation_matrix = nutation_matrix_equatorial(jd_tt)

    def to_true_equator_of_date(vector: _Vec3) -> _Vec3:
        return mat_vec_mul(
            nutation_matrix,
            mat_vec_mul(precession, vector),
        )

    axis = to_true_equator_of_date(axis_sunward_icrf)
    point = to_true_equator_of_date(plane_point)
    axis_norm = math.sqrt(_dot(axis, axis))
    if axis_norm == 0.0 or not math.isfinite(axis_norm):
        raise ArithmeticError("solar shadow axis has no finite direction")
    axis = tuple(component / axis_norm for component in axis)

    alpha_rad = math.atan2(axis[1], axis[0])
    d_rad = math.asin(max(-1.0, min(1.0, axis[2])))
    sin_alpha = math.sin(alpha_rad)
    cos_alpha = math.cos(alpha_rad)
    sin_d = math.sin(d_rad)
    cos_d = math.cos(d_rad)

    # Orthonormal fundamental-plane basis imposed by the governing object:
    # east is increasing right ascension; north is increasing declination.
    east = (-sin_alpha, cos_alpha, 0.0)
    north = (-sin_d * cos_alpha, -sin_d * sin_alpha, cos_d)
    x = _dot(point, east) / EARTH_RADIUS_KM
    y = _dot(point, north) / EARTH_RADIUS_KM

    d_deg = math.degrees(d_rad)
    alpha_deg = math.degrees(alpha_rad) % 360.0
    mu = (_ephemeris_apparent_sidereal_angle_tt(jd_tt) - alpha_deg) % 360.0

    distance_to_plane_er = -state.axis_projection_km / EARTH_RADIUS_KM
    if distance_to_plane_er <= 0.0 or not math.isfinite(distance_to_plane_er):
        raise ValueError("lunar shadow does not advance toward the fundamental plane")
    moon_radius_er = MOON_RADIUS_KM / EARTH_RADIUS_KM

    # Exact common-tangent geometry.  The radius ratio is sin(f), not tan(f).
    # At the Moon-centre plane the cone intercept is R_moon / cos(f); advancing
    # to the fundamental plane then changes the radius by zeta * tan(f).
    sin_f1 = (
        SUN_RADIUS_KM + MOON_RADIUS_KM
    ) / state.sun_moon_distance_km
    sin_f2 = (
        SUN_RADIUS_KM - MOON_RADIUS_KM
    ) / state.sun_moon_distance_km
    if not 0.0 < sin_f2 < sin_f1 < 1.0:
        raise ArithmeticError("solar and lunar radii cannot define physical shadow cones")
    cos_f1 = math.sqrt((1.0 - sin_f1) * (1.0 + sin_f1))
    cos_f2 = math.sqrt((1.0 - sin_f2) * (1.0 + sin_f2))
    tan_f1 = sin_f1 / cos_f1
    tan_f2 = sin_f2 / cos_f2
    l1 = moon_radius_er / cos_f1 + distance_to_plane_er * tan_f1
    # NASA's published sign: negative umbral/total, positive antumbral/annular.
    l2 = distance_to_plane_er * tan_f2 - moon_radius_er / cos_f2

    return SolarBesselianElements(
        jd_ut1=jd_ut1,
        jd_tt=jd_tt,
        x=x,
        y=y,
        d=d_deg,
        mu=mu,
        l1=l1,
        l2=l2,
        tan_f1=tan_f1,
        tan_f2=tan_f2,
        ephemeris=ephemeris,
    )


__all__ = ["SolarBesselianElements"]

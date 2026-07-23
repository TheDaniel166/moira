"""First-class global circumstances for one lunar eclipse.

The product assembled here is geocentric.  It describes the Moon's passage
through Earth's shadow under one explicit computational mode; observer
visibility remains the responsibility of ``LunarEclipseVisibilityMap`` and
``LunarEclipseLocalCircumstances``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import Body
from .coordinates import (
    icrf_to_equatorial,
    mat_vec_mul,
    nutation_matrix_equatorial,
    precession_matrix_equatorial,
)
from .eclipse_canon import (
    DEFAULT_LUNAR_CANON_METHOD,
    LunarCanonContacts,
    _lunar_canon_vectors_tt,
    lunar_canon_geometry,
)
from .eclipse_contacts import LunarEclipseContacts
from .eclipse_geometry import (
    EARTH_RADIUS_KM,
    MOON_RADIUS_KM,
    SUN_RADIUS_KM,
    apparent_radius,
    lunar_parallax,
    solar_parallax,
)
from .eclipse_global import EclipseEpoch, EclipseGeocentricBodyState
from ._ephemeris_time import _reader_identity_at, _ut1_to_ephemeris_tt

if TYPE_CHECKING:
    from .eclipse import EclipseCalculator, LunarEclipseAnalysis

__all__ = [
    "LunarEclipseShadowState",
    "LunarEclipseGlobalCircumstances",
]


_APPARENT_COORDINATE_POLICY = (
    "Earth-reception light-time and annual aberration; true equator and "
    "equinox of date; no gravitational deflection, topocentric parallax, "
    "or atmospheric refraction"
)
_TRUE_EQUATORIAL_FRAME = "true_equator_and_equinox_of_date"
_GEOCENTRIC_ORIGIN = "earth_center"


def _require_nonempty_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_finite(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class LunarEclipseShadowState:
    """Earth-shadow geometry at lunar greatest eclipse."""

    gamma_earth_radii: float
    axis_distance_km: float
    moon_radius_earth_radii: float
    umbra_radius_earth_radii: float
    penumbra_radius_earth_radii: float
    umbral_magnitude: float
    penumbral_magnitude: float
    shadow_model: str

    def __post_init__(self) -> None:
        for name in (
            "gamma_earth_radii",
            "axis_distance_km",
            "moon_radius_earth_radii",
            "umbra_radius_earth_radii",
            "penumbra_radius_earth_radii",
            "umbral_magnitude",
            "penumbral_magnitude",
        ):
            _require_finite(name, getattr(self, name))
        _require_nonempty_text("shadow_model", self.shadow_model)
        if float(self.axis_distance_km) < 0.0:
            raise ValueError("axis_distance_km must be non-negative")
        for name in (
            "moon_radius_earth_radii",
            "umbra_radius_earth_radii",
            "penumbra_radius_earth_radii",
        ):
            if float(getattr(self, name)) <= 0.0:
                raise ValueError(f"{name} must be positive")
        if float(self.penumbra_radius_earth_radii) <= float(
            self.umbra_radius_earth_radii
        ):
            raise ValueError("penumbra radius must exceed umbra radius")
        if float(self.penumbral_magnitude) < float(self.umbral_magnitude):
            raise ValueError("penumbral magnitude must not be below umbral magnitude")
        recovered_gamma = float(self.axis_distance_km) / EARTH_RADIUS_KM
        if not math.isclose(
            abs(float(self.gamma_earth_radii)),
            recovered_gamma,
            rel_tol=0.0,
            abs_tol=2.0e-12,
        ):
            raise ValueError("gamma magnitude must match axis_distance_km")


@dataclass(frozen=True, slots=True)
class LunarEclipseGlobalCircumstances:
    """Complete geocentric summary for one searched lunar eclipse."""

    analysis: "LunarEclipseAnalysis"
    greatest: EclipseEpoch
    sun: EclipseGeocentricBodyState
    moon: EclipseGeocentricBodyState
    shadow: LunarEclipseShadowState
    penumbral_duration_seconds: float | None
    partial_duration_seconds: float | None
    total_duration_seconds: float | None
    ephemeris: str
    mode: str
    source_model: str

    def __post_init__(self) -> None:
        _require_nonempty_text("ephemeris", self.ephemeris)
        _require_nonempty_text("mode", self.mode)
        _require_nonempty_text("source_model", self.source_model)
        analysis_mode = getattr(self.analysis, "mode", None)
        if analysis_mode != self.mode:
            raise ValueError("analysis mode must match global-circumstances mode")
        for name in (
            "penumbral_duration_seconds",
            "partial_duration_seconds",
            "total_duration_seconds",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_finite(name, value)
                if float(value) < 0.0:
                    raise ValueError(f"{name} must be non-negative")
        if self.sun.body != Body.SUN or self.moon.body != Body.MOON:
            raise ValueError("sun and moon body states must retain canonical identity")


def _true_equatorial_state(
    *,
    body: str,
    jd_tt: float,
    xyz: tuple[float, float, float],
) -> EclipseGeocentricBodyState:
    true_xyz = mat_vec_mul(
        nutation_matrix_equatorial(jd_tt),
        mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz),
    )
    right_ascension_deg, declination_deg, distance_km = icrf_to_equatorial(
        true_xyz
    )
    physical_radius = SUN_RADIUS_KM if body == Body.SUN else MOON_RADIUS_KM
    parallax = (
        solar_parallax(distance_km)
        if body == Body.SUN
        else lunar_parallax(distance_km)
    )
    return EclipseGeocentricBodyState(
        body=body,
        right_ascension_deg=right_ascension_deg % 360.0,
        declination_deg=declination_deg,
        distance_km=distance_km,
        semidiameter_deg=apparent_radius(physical_radius, distance_km),
        horizontal_parallax_deg=parallax,
        origin=_GEOCENTRIC_ORIGIN,
        frame=_TRUE_EQUATORIAL_FRAME,
        correction_policy=_APPARENT_COORDINATE_POLICY,
    )


def _duration_seconds(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return (end - start) * 86400.0


def _contact_times(
    contacts: LunarEclipseContacts | LunarCanonContacts,
) -> tuple[
    float | None,
    float | None,
    float | None,
    float | None,
    float | None,
    float | None,
]:
    if isinstance(contacts, LunarCanonContacts):
        return (
            contacts.p1_tt,
            contacts.u1_tt,
            contacts.u2_tt,
            contacts.u3_tt,
            contacts.u4_tt,
            contacts.p4_tt,
        )
    return (
        contacts.p1,
        contacts.u1,
        contacts.u2,
        contacts.u3,
        contacts.u4,
        contacts.p4,
    )


def _native_shadow_state(
    calculator: "EclipseCalculator",
    jd_tt: float,
) -> LunarEclipseShadowState:
    (
        axis_km,
        northward_offset_km,
        moon_radius_km,
        umbra_radius_km,
        penumbra_radius_km,
        _moon_distance_km,
    ) = calculator._native_lunar_event_axis_geometry_tt(
        jd_tt,
        retarded_moon=False,
    )
    gamma_magnitude = axis_km / EARTH_RADIUS_KM
    gamma = math.copysign(gamma_magnitude, northward_offset_km)
    moon_r = moon_radius_km / EARTH_RADIUS_KM
    umbra_r = umbra_radius_km / EARTH_RADIUS_KM
    penumbra_r = penumbra_radius_km / EARTH_RADIUS_KM
    return LunarEclipseShadowState(
        gamma_earth_radii=gamma,
        axis_distance_km=axis_km,
        moon_radius_earth_radii=moon_r,
        umbra_radius_earth_radii=umbra_r,
        penumbra_radius_earth_radii=penumbra_r,
        umbral_magnitude=(umbra_r + moon_r - gamma_magnitude) / (2.0 * moon_r),
        penumbral_magnitude=(
            penumbra_r + moon_r - gamma_magnitude
        ) / (2.0 * moon_r),
        shadow_model=(
            "Moira native physical conical Earth shadow with spherical "
            "mean-limb Sun and Moon"
        ),
    )


def _compat_shadow_state(
    calculator: "EclipseCalculator",
    jd_tt: float,
) -> LunarEclipseShadowState:
    geometry = lunar_canon_geometry(
        calculator,
        jd_tt,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    return LunarEclipseShadowState(
        gamma_earth_radii=geometry.gamma_earth_radii,
        axis_distance_km=geometry.axis_km,
        moon_radius_earth_radii=geometry.moon_radius_earth_radii,
        umbra_radius_earth_radii=geometry.umbra_radius_earth_radii,
        penumbra_radius_earth_radii=geometry.penumbra_radius_earth_radii,
        umbral_magnitude=geometry.umbral_magnitude,
        penumbral_magnitude=geometry.penumbral_magnitude,
        shadow_model=(
            f"Moira lunar canon {DEFAULT_LUNAR_CANON_METHOD}; spherical "
            "mean-limb conical shadow"
        ),
    )


def _build_lunar_global_circumstances(
    calculator: "EclipseCalculator",
    analysis: "LunarEclipseAnalysis",
) -> LunarEclipseGlobalCircumstances:
    """Assemble one mode-pure lunar global-circumstances result."""

    if analysis.mode == "native":
        jd_ut1 = analysis.event.jd_ut
        jd_tt = _ut1_to_ephemeris_tt(jd_ut1, calculator._reader)
        time_policy = "content-identified ephemeris-bound Moira Delta T"
        shadow = _native_shadow_state(calculator, jd_tt)
    elif analysis.mode == "nasa_compat":
        if not isinstance(analysis.contacts, LunarCanonContacts):
            raise TypeError("nasa_compat analysis requires LunarCanonContacts")
        jd_tt = analysis.contacts.greatest_tt
        jd_ut1 = analysis.contacts.greatest_ut
        time_policy = "NASA lunar-canon catalog Delta T"
        shadow = _compat_shadow_state(calculator, jd_tt)
    else:
        raise ValueError(
            f"Unsupported lunar eclipse analysis mode: {analysis.mode!r}"
        )

    identity = _reader_identity_at(calculator._reader, jd_tt)
    if (
        identity is None
        or identity.planetary_ephemeris != "DE441"
        or identity.lunar_ephemeris != "LE441"
    ):
        raise RuntimeError(
            "lunar global circumstances are admitted only for a "
            "content-identified DE441/LE441 reader"
        )

    sun_xyz, moon_xyz = _lunar_canon_vectors_tt(
        calculator,
        jd_tt,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    sun = _true_equatorial_state(body=Body.SUN, jd_tt=jd_tt, xyz=sun_xyz)
    moon = _true_equatorial_state(body=Body.MOON, jd_tt=jd_tt, xyz=moon_xyz)
    p1, u1, u2, u3, u4, p4 = _contact_times(analysis.contacts)
    return LunarEclipseGlobalCircumstances(
        analysis=analysis,
        greatest=EclipseEpoch(
            jd_tt=jd_tt,
            jd_ut1=jd_ut1,
            delta_t_seconds=(jd_tt - jd_ut1) * 86400.0,
            time_policy=time_policy,
        ),
        sun=sun,
        moon=moon,
        shadow=shadow,
        penumbral_duration_seconds=_duration_seconds(p1, p4),
        partial_duration_seconds=_duration_seconds(u1, u4),
        total_duration_seconds=_duration_seconds(u2, u3),
        ephemeris=identity.summary_label,
        mode=analysis.mode,
        source_model=analysis.source_model,
    )

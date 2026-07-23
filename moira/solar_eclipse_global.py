"""Global circumstances for one searched solar eclipse.

This admission preserves the existing path and footprint products by
reference while assembling their greatest-eclipse, central-line-limit,
P-contact, Besselian, body-state, magnitude, obscuration, width, and duration
information.  It also exposes independently solved U1-U4 cone tangencies,
equatorial and ecliptic conjunctions, and greatest-duration circumstances.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from .constants import Body
from .coordinates import icrf_to_equatorial
from .eclipse_besselian import SolarBesselianElements
from .eclipse_geometry import (
    MOON_RADIUS_KM,
    SUN_RADIUS_KM,
    apparent_radius,
    lunar_parallax,
    solar_parallax,
)
from .eclipse_global import EclipseEpoch, EclipseGeocentricBodyState
from .planets import planet_at
from ._ephemeris_time import _reader_identity_at, _ut1_to_ephemeris_tt
from ._eclipse_solar_geometry import _topocentric_solar_disc_geometry

if TYPE_CHECKING:
    from .eclipse import (
        EclipseCalculator,
        EclipseEvent,
        SolarEclipseVisibilityFootprint,
    )

__all__ = [
    "SolarEclipseCentralLineLimit",
    "SolarEclipseConjunctionKind",
    "SolarEclipseConjunction",
    "SolarEclipseUmbralContactKind",
    "SolarEclipseUmbralContact",
    "SolarEclipseUmbralContacts",
    "SolarEclipseGreatestSite",
    "SolarEclipseGlobalCircumstances",
]


_GEOCENTRIC_CORRECTION_POLICY = (
    "full apparent geocentric reduction with reception light-time, annual "
    "aberration, frame bias, precession, and nutation; gravitational "
    "deflection disabled; no topocentric parallax or refraction"
)


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


@dataclass(frozen=True, slots=True)
class SolarEclipseCentralLineLimit:
    kind: str
    epoch: EclipseEpoch
    latitude_deg: float
    longitude_deg: float

    def __post_init__(self) -> None:
        if self.kind not in {"first", "last"}:
            raise ValueError("central-line-limit kind must be 'first' or 'last'")
        if not -90.0 <= _finite("latitude_deg", self.latitude_deg) <= 90.0:
            raise ValueError("latitude_deg must be in [-90, 90]")
        if not -180.0 <= _finite("longitude_deg", self.longitude_deg) <= 180.0:
            raise ValueError("longitude_deg must be in [-180, 180]")


class SolarEclipseConjunctionKind(str, Enum):
    EQUATORIAL = "equatorial"
    ECLIPTIC = "ecliptic"


@dataclass(frozen=True, slots=True)
class SolarEclipseConjunction:
    kind: SolarEclipseConjunctionKind
    epoch: EclipseEpoch

    def __post_init__(self) -> None:
        try:
            kind = SolarEclipseConjunctionKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid solar conjunction kind") from exc
        object.__setattr__(self, "kind", kind)


class SolarEclipseUmbralContactKind(str, Enum):
    U1 = "u1"
    U2 = "u2"
    U3 = "u3"
    U4 = "u4"


@dataclass(frozen=True, slots=True)
class SolarEclipseUmbralContact:
    kind: SolarEclipseUmbralContactKind
    epoch: EclipseEpoch
    latitude_deg: float
    longitude_deg: float

    def __post_init__(self) -> None:
        try:
            kind = SolarEclipseUmbralContactKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid solar umbral contact kind") from exc
        object.__setattr__(self, "kind", kind)
        if not -90.0 <= _finite("latitude_deg", self.latitude_deg) <= 90.0:
            raise ValueError("latitude_deg must be in [-90, 90]")
        if not -180.0 <= _finite("longitude_deg", self.longitude_deg) <= 180.0:
            raise ValueError("longitude_deg must be in [-180, 180]")


@dataclass(frozen=True, slots=True)
class SolarEclipseUmbralContacts:
    u1: SolarEclipseUmbralContact
    u2: SolarEclipseUmbralContact
    u3: SolarEclipseUmbralContact
    u4: SolarEclipseUmbralContact

    def __post_init__(self) -> None:
        contacts = (self.u1, self.u2, self.u3, self.u4)
        expected = tuple(SolarEclipseUmbralContactKind)
        if tuple(contact.kind for contact in contacts) != expected:
            raise ValueError("umbral contacts must carry U1 through U4")
        epochs = tuple(contact.epoch.jd_ut1 for contact in contacts)
        if any(left >= right for left, right in zip(epochs, epochs[1:])):
            raise ValueError("umbral contacts must be strictly ordered U1 through U4")


@dataclass(frozen=True, slots=True)
class SolarEclipseGreatestSite:
    epoch: EclipseEpoch
    latitude_deg: float
    longitude_deg: float
    path_width_km: float
    central_duration_seconds: float
    sun_altitude_deg: float
    sun_azimuth_deg: float
    moon_altitude_deg: float
    moon_azimuth_deg: float
    separation_deg: float
    sun_semidiameter_deg: float
    moon_semidiameter_deg: float
    magnitude: float
    obscuration: float
    local_class: str

    def __post_init__(self) -> None:
        for name in (
            "latitude_deg",
            "longitude_deg",
            "path_width_km",
            "central_duration_seconds",
            "sun_altitude_deg",
            "sun_azimuth_deg",
            "moon_altitude_deg",
            "moon_azimuth_deg",
            "separation_deg",
            "sun_semidiameter_deg",
            "moon_semidiameter_deg",
            "magnitude",
            "obscuration",
        ):
            _finite(name, getattr(self, name))
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("latitude_deg must be in [-90, 90]")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("longitude_deg must be in [-180, 180]")
        if self.path_width_km < 0.0 or self.central_duration_seconds < 0.0:
            raise ValueError("width and duration must be non-negative")
        if not 0.0 <= self.obscuration <= 1.0:
            raise ValueError("obscuration must be in [0, 1]")
        if self.magnitude < 0.0:
            raise ValueError("magnitude must be non-negative")
        if self.local_class not in {"none", "partial", "annular", "total"}:
            raise ValueError("invalid local eclipse class")


@dataclass(frozen=True, slots=True)
class SolarEclipseGlobalCircumstances:
    event: "EclipseEvent"
    greatest: SolarEclipseGreatestSite
    greatest_duration: SolarEclipseGreatestSite | None
    equatorial_conjunction: SolarEclipseConjunction
    ecliptic_conjunction: SolarEclipseConjunction
    footprint: "SolarEclipseVisibilityFootprint"
    besselian: SolarBesselianElements
    sun: EclipseGeocentricBodyState
    moon: EclipseGeocentricBodyState
    gamma_earth_radii: float
    umbral_contacts: SolarEclipseUmbralContacts | None
    first_central_line_limit: SolarEclipseCentralLineLimit | None
    last_central_line_limit: SolarEclipseCentralLineLimit | None
    ephemeris: str
    surface_model: str = field(default="WGS84_ZERO_ELEVATION", init=False)
    limb_model: str = field(default="SPHERICAL_MEAN_LIMB", init=False)
    umbral_contacts_admitted: bool = field(default=True, init=False)
    greatest_duration_admitted: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        _finite("gamma_earth_radii", self.gamma_earth_radii)
        if not isinstance(self.ephemeris, str) or not self.ephemeris.strip():
            raise ValueError("ephemeris is required")
        if self.footprint.event != self.event:
            raise ValueError("footprint and global circumstances must share event")
        if self.equatorial_conjunction.kind is not SolarEclipseConjunctionKind.EQUATORIAL:
            raise ValueError("equatorial_conjunction has the wrong conjunction kind")
        if self.ecliptic_conjunction.kind is not SolarEclipseConjunctionKind.ECLIPTIC:
            raise ValueError("ecliptic_conjunction has the wrong conjunction kind")
        if abs(self.greatest.epoch.jd_ut1 - self.event.jd_ut) > 1.0e-10:
            raise ValueError("greatest epoch must equal searched event epoch")
        if (self.first_central_line_limit is None) != (
            self.last_central_line_limit is None
        ):
            raise ValueError("central-line limits must be paired")
        if self.first_central_line_limit is not None:
            if not (
                self.first_central_line_limit.epoch.jd_ut1
                < self.greatest.epoch.jd_ut1
                < self.last_central_line_limit.epoch.jd_ut1
            ):
                raise ValueError("central-line limits must bracket greatest eclipse")
        is_central = any(
            (
                self.event.data.eclipse_type.is_annular,
                self.event.data.eclipse_type.is_total,
                self.event.data.eclipse_type.is_hybrid,
            )
        )
        if is_central and self.umbral_contacts is None:
            raise ValueError("central eclipses require admitted U1-U4 contacts")
        if not is_central and self.umbral_contacts is not None:
            raise ValueError("partial eclipses cannot carry U1-U4 contacts")
        if is_central and self.greatest_duration is None:
            raise ValueError("central eclipses require a greatest-duration site")
        if not is_central and self.greatest_duration is not None:
            raise ValueError("partial eclipses cannot carry a greatest-duration site")
        if self.umbral_contacts is not None and not (
            self.footprint.contacts.p1.point.jd_ut
            < self.umbral_contacts.u1.epoch.jd_ut1
            < self.umbral_contacts.u2.epoch.jd_ut1
            < self.greatest.epoch.jd_ut1
            < self.umbral_contacts.u3.epoch.jd_ut1
            < self.umbral_contacts.u4.epoch.jd_ut1
            < self.footprint.contacts.p4.point.jd_ut
        ):
            raise ValueError("U1-U4 contacts must lie within P1-P4 and bracket GE")


def _epoch(calculator: "EclipseCalculator", jd_ut1: float) -> EclipseEpoch:
    jd_tt = _ut1_to_ephemeris_tt(jd_ut1, calculator._reader)
    return EclipseEpoch(
        jd_tt=jd_tt,
        jd_ut1=jd_ut1,
        delta_t_seconds=(jd_tt - jd_ut1) * 86400.0,
        time_policy="content-identified ephemeris-bound Moira Delta T",
    )


def _geocentric_body_state(
    calculator: "EclipseCalculator",
    body: str,
    epoch: EclipseEpoch,
) -> EclipseGeocentricBodyState:
    position = planet_at(
        body,
        epoch.jd_ut1,
        reader=calculator._reader,
        apparent=True,
        grav_deflection=False,
        center="geocentric",
        frame="cartesian",
        jd_tt=epoch.jd_tt,
    )
    right_ascension, declination, distance = icrf_to_equatorial(
        (position.x, position.y, position.z)
    )
    physical_radius = SUN_RADIUS_KM if body == Body.SUN else MOON_RADIUS_KM
    parallax = solar_parallax(distance) if body == Body.SUN else lunar_parallax(distance)
    return EclipseGeocentricBodyState(
        body=body,
        right_ascension_deg=right_ascension % 360.0,
        declination_deg=declination,
        distance_km=distance,
        semidiameter_deg=apparent_radius(physical_radius, distance),
        horizontal_parallax_deg=parallax,
        origin="earth_center",
        frame="true_equator_and_equinox_of_date",
        correction_policy=_GEOCENTRIC_CORRECTION_POLICY,
    )


def _build_solar_global_circumstances(
    calculator: "EclipseCalculator",
    *,
    jd_start: float,
    kind: str,
    backward: bool,
) -> SolarEclipseGlobalCircumstances:
    # Local imports preserve eclipse.py as the owner of established path and
    # WGS-84 central-interval machinery without creating a module cycle.
    from .eclipse import (
        _solar_axis_surface_point,
        _solve_local_solar_central_duration_s,
        _solve_solar_central_interval,
        _solve_solar_umbral_width_km,
        _solve_solar_umbral_contacts,
    )

    event = calculator._search_solar_eclipse(
        jd_start,
        kind=kind,
        backward=backward,
    )

    def longitude_difference(jd_ut1: float, *, frame: str) -> float:
        jd_tt = _ut1_to_ephemeris_tt(jd_ut1, calculator._reader)
        if frame == "ecliptic":
            sun_position = planet_at(
                Body.SUN,
                jd_ut1,
                reader=calculator._reader,
                apparent=True,
                grav_deflection=False,
                center="geocentric",
                frame="ecliptic",
                jd_tt=jd_tt,
            )
            moon_position = planet_at(
                Body.MOON,
                jd_ut1,
                reader=calculator._reader,
                apparent=True,
                grav_deflection=False,
                center="geocentric",
                frame="ecliptic",
                jd_tt=jd_tt,
            )
            sun_angle = sun_position.longitude
            moon_angle = moon_position.longitude
        else:
            sun_state = _geocentric_body_state(
                calculator,
                Body.SUN,
                _epoch(calculator, jd_ut1),
            )
            moon_state = _geocentric_body_state(
                calculator,
                Body.MOON,
                _epoch(calculator, jd_ut1),
            )
            sun_angle = sun_state.right_ascension_deg
            moon_angle = moon_state.right_ascension_deg
        return (moon_angle - sun_angle + 180.0) % 360.0 - 180.0

    def solve_conjunction(frame: str) -> EclipseEpoch:
        half_window_days = 0.25
        scan_count = 49
        times = tuple(
            event.jd_ut
            - half_window_days
            + 2.0 * half_window_days * index / (scan_count - 1)
            for index in range(scan_count)
        )
        values = tuple(longitude_difference(epoch, frame=frame) for epoch in times)
        brackets: list[tuple[float, float]] = []
        for index in range(scan_count - 1):
            if values[index] == 0.0:
                return _epoch(calculator, times[index])
            if values[index] * values[index + 1] < 0.0:
                if abs(values[index] - values[index + 1]) < 180.0:
                    brackets.append((times[index], times[index + 1]))
        if not brackets:
            raise ArithmeticError(
                f"{frame} conjunction was not bracketed around greatest eclipse"
            )
        left, right = min(
            brackets,
            key=lambda bracket: abs((bracket[0] + bracket[1]) / 2.0 - event.jd_ut),
        )
        left_value = longitude_difference(left, frame=frame)
        for _ in range(52):
            midpoint = (left + right) / 2.0
            midpoint_value = longitude_difference(midpoint, frame=frame)
            if midpoint_value == 0.0:
                left = right = midpoint
                break
            if left_value * midpoint_value <= 0.0:
                right = midpoint
            else:
                left = midpoint
                left_value = midpoint_value
        return _epoch(calculator, (left + right) / 2.0)

    equatorial_conjunction = SolarEclipseConjunction(
        kind=SolarEclipseConjunctionKind.EQUATORIAL,
        epoch=solve_conjunction("equatorial"),
    )
    ecliptic_conjunction = SolarEclipseConjunction(
        kind=SolarEclipseConjunctionKind.ECLIPTIC,
        epoch=solve_conjunction("ecliptic"),
    )
    greatest_epoch = _epoch(calculator, event.jd_ut)
    identity = _reader_identity_at(calculator._reader, greatest_epoch.jd_tt)
    if (
        identity is None
        or identity.planetary_ephemeris != "DE441"
        or identity.lunar_ephemeris != "LE441"
    ):
        raise RuntimeError(
            "solar global circumstances are admitted only for a "
            "content-identified DE441/LE441 reader"
        )

    footprint = calculator.solar_eclipse_footprint(
        jd_start,
        kind=kind,
        backward=backward,
        sample_count=9,
    )
    path = calculator.solar_eclipse_path(
        jd_start,
        kind=kind,
        backward=backward,
        sample_count=2,
    )
    besselian = calculator.solar_besselian_elements(event.jd_ut)
    discs = _topocentric_solar_disc_geometry(
        calculator,
        event.jd_ut,
        path.max_eclipse_lat,
        path.max_eclipse_lon,
    )

    central = any(
        (
            event.data.eclipse_type.is_annular,
            event.data.eclipse_type.is_total,
            event.data.eclipse_type.is_hybrid,
        )
    )
    first_limit = None
    last_limit = None
    if central:
        first, last = _solve_solar_central_interval(calculator, event.jd_ut)
        first_limit = SolarEclipseCentralLineLimit(
            kind="first",
            epoch=_epoch(calculator, first.jd_ut),
            latitude_deg=first.point.latitude_deg,
            longitude_deg=first.point.longitude_deg,
        )
        last_limit = SolarEclipseCentralLineLimit(
            kind="last",
            epoch=_epoch(calculator, last.jd_ut),
            latitude_deg=last.point.latitude_deg,
            longitude_deg=last.point.longitude_deg,
        )

    greatest_duration = None
    if central:
        assert first_limit is not None and last_limit is not None
        interval_start = first_limit.epoch.jd_ut1
        interval_end = last_limit.epoch.jd_ut1
        sample_count = 33
        sample_times = tuple(
            interval_start
            + (interval_end - interval_start) * index / (sample_count - 1)
            for index in range(sample_count)
        )
        duration_cache: dict[float, float] = {}

        def duration_at(jd_ut1: float) -> float:
            cached = duration_cache.get(jd_ut1)
            if cached is not None:
                return cached
            point = _solar_axis_surface_point(calculator, jd_ut1)
            if point is None:
                duration = 0.0
            else:
                duration = _solve_local_solar_central_duration_s(
                    calculator,
                    jd_ut1,
                    point.latitude_deg,
                    point.longitude_deg,
                )
            duration_cache[jd_ut1] = duration
            return duration

        sample_durations = tuple(duration_at(jd_ut1) for jd_ut1 in sample_times)
        candidates: list[tuple[float, float]] = [
            (sample_times[0], sample_durations[0]),
            (sample_times[-1], sample_durations[-1]),
        ]
        golden = (math.sqrt(5.0) - 1.0) / 2.0
        for index in range(1, sample_count - 1):
            if not (
                sample_durations[index] >= sample_durations[index - 1]
                and sample_durations[index] >= sample_durations[index + 1]
            ):
                continue
            left = sample_times[index - 1]
            right = sample_times[index + 1]
            x1 = right - golden * (right - left)
            x2 = left + golden * (right - left)
            f1 = duration_at(x1)
            f2 = duration_at(x2)
            for _ in range(48):
                if f1 < f2:
                    left = x1
                    x1, f1 = x2, f2
                    x2 = left + golden * (right - left)
                    f2 = duration_at(x2)
                else:
                    right = x2
                    x2, f2 = x1, f1
                    x1 = right - golden * (right - left)
                    f1 = duration_at(x1)
            refined_time = (left + right) / 2.0
            candidates.append((refined_time, duration_at(refined_time)))

        duration_time, duration_seconds = max(
            candidates,
            key=lambda candidate: (candidate[1], -candidate[0]),
        )
        duration_point = _solar_axis_surface_point(calculator, duration_time)
        if duration_point is None:
            raise ArithmeticError(
                "greatest-duration epoch has no WGS-84 shadow-axis intersection"
            )
        duration_discs = _topocentric_solar_disc_geometry(
            calculator,
            duration_time,
            duration_point.latitude_deg,
            duration_point.longitude_deg,
        )
        at_central_limit = min(
            abs(duration_time - interval_start),
            abs(duration_time - interval_end),
        ) <= 1.0e-10
        greatest_duration = SolarEclipseGreatestSite(
            epoch=_epoch(calculator, duration_time),
            latitude_deg=duration_point.latitude_deg,
            longitude_deg=duration_point.longitude_deg,
            path_width_km=(
                0.0
                if at_central_limit
                else _solve_solar_umbral_width_km(calculator, duration_time)
            ),
            central_duration_seconds=duration_seconds,
            sun_altitude_deg=duration_discs.sun_altitude_deg,
            sun_azimuth_deg=duration_discs.sun_azimuth_deg,
            moon_altitude_deg=duration_discs.moon_altitude_deg,
            moon_azimuth_deg=duration_discs.moon_azimuth_deg,
            separation_deg=duration_discs.separation_deg,
            sun_semidiameter_deg=duration_discs.sun_radius_deg,
            moon_semidiameter_deg=duration_discs.moon_radius_deg,
            magnitude=duration_discs.magnitude,
            obscuration=duration_discs.obscuration,
            local_class=duration_discs.local_class,
        )
    umbral_contacts = (
        _solve_solar_umbral_contacts(calculator, event.jd_ut)
        if central
        else None
    )

    return SolarEclipseGlobalCircumstances(
        event=event,
        greatest=SolarEclipseGreatestSite(
            epoch=greatest_epoch,
            latitude_deg=path.max_eclipse_lat,
            longitude_deg=path.max_eclipse_lon,
            path_width_km=path.umbral_width_km,
            central_duration_seconds=path.duration_at_max_s,
            sun_altitude_deg=discs.sun_altitude_deg,
            sun_azimuth_deg=discs.sun_azimuth_deg,
            moon_altitude_deg=discs.moon_altitude_deg,
            moon_azimuth_deg=discs.moon_azimuth_deg,
            separation_deg=discs.separation_deg,
            sun_semidiameter_deg=discs.sun_radius_deg,
            moon_semidiameter_deg=discs.moon_radius_deg,
            magnitude=discs.magnitude,
            obscuration=discs.obscuration,
            local_class=discs.local_class,
        ),
        greatest_duration=greatest_duration,
        equatorial_conjunction=equatorial_conjunction,
        ecliptic_conjunction=ecliptic_conjunction,
        footprint=footprint,
        besselian=besselian,
        sun=_geocentric_body_state(calculator, Body.SUN, greatest_epoch),
        moon=_geocentric_body_state(calculator, Body.MOON, greatest_epoch),
        gamma_earth_radii=math.copysign(
            math.hypot(besselian.x, besselian.y),
            besselian.y,
        ),
        umbral_contacts=umbral_contacts,
        first_central_line_limit=first_limit,
        last_central_line_limit=last_limit,
        ephemeris=identity.summary_label,
    )

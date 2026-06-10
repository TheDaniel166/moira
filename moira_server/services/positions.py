"""Phase-2 planetary and sky-position service helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from moira import Body, Moira, PlanetData, SkyPosition
from moira.julian import delta_t_from_jd, datetime_from_jd, jd_from_datetime, local_sidereal_time, utc_to_tt, utc_to_ut1
from moira.obliquity import nutation, true_obliquity
from moira.planets import _resolve_small_body_name, planet_at, sky_position_at

from ..models.positions import PlanetPositionRequest, SkyPositionRequest


_VALID_PLANET_BODIES = frozenset(Body.ALL_PLANETS)
_PLANET_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "utc_to_tt",
    "utc_to_ut1",
    "chart_assembly",
    "all_planets_at",
    "light_time",
    "gravitational_deflection",
    "annual_aberration",
    "frame_bias",
    "precession",
    "nutation",
    "optional_topocentric_parallax",
    "ecliptic_projection",
    "planet_selection",
]
_SKY_STAGE_SEQUENCE = [
    "datetime_to_jd",
    "utc_to_tt",
    "light_time",
    "gravitational_deflection",
    "annual_aberration",
    "frame_bias",
    "precession",
    "nutation",
    "topocentric_parallax",
    "diurnal_aberration",
    "equatorial_projection",
    "horizontal_projection",
    "optional_refraction",
]


@dataclass(frozen=True, slots=True)
class PositionObserverContext:
    latitude: float | None
    longitude: float | None
    elevation_m: float
    local_sidereal_time_deg: float | None


@dataclass(frozen=True, slots=True)
class PlanetPositionReductionContext:
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_tt: float
    delta_t_seconds: float
    observer: PositionObserverContext
    stage_sequence: list[str]
    obliquity_deg: float
    topocentric_requested: bool
    topocentric_applied: bool
    # Correction flags as requested (to reflect actual applied subset in reduction truth).
    apparent: bool
    aberration: bool
    grav_deflection: bool
    nutation: bool


@dataclass(frozen=True, slots=True)
class SkyPositionReductionContext:
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_tt: float
    delta_t_seconds: float
    observer: PositionObserverContext
    stage_sequence: list[str]
    obliquity_deg: float
    # Refraction and correction params as requested (to avoid hardcodes in truth and support partial).
    aberration: bool
    grav_deflection: bool
    nutation: bool
    refraction: bool
    pressure_mbar: float
    temperature_c: float
    relative_humidity: float


def _require_aware_datetime(value) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime inputs must be timezone-aware")


def _require_supported_planet_body(body: str) -> None:
    if body in _VALID_PLANET_BODIES:
        return
    if _resolve_small_body_name(body) is not None:
        return
    supported = ", ".join(sorted(_VALID_PLANET_BODIES))
    raise ValueError(
        f"unsupported planet body {body!r}; supported bodies: {supported}, plus admitted asteroid/comet names"
    )


def _sidereal_context(jd_utc: float, longitude: float) -> tuple[float, float]:
    jd_tt = utc_to_tt(jd_utc)
    jd_ut1 = utc_to_ut1(jd_utc)
    dpsi_deg, _ = nutation(jd_tt)
    obliquity_deg = true_obliquity(jd_tt)
    lst_deg = local_sidereal_time(jd_ut1, longitude, dpsi_deg, obliquity_deg)
    return lst_deg, obliquity_deg


def compute_planet_position(engine: Moira, request: PlanetPositionRequest) -> PlanetData:
    """Compute one planet position from a transport request using pure low-level planet_at
    to support independent correction controls (closing the chart-mediated gap).
    """

    _require_aware_datetime(request.dt)
    _require_supported_planet_body(request.body)
    jd_ut = jd_from_datetime(request.dt)
    return planet_at(
        request.body,
        jd_ut,
        reader=None,  # use active reader (set by the Moira engine instance in server lifecycle)
        apparent=request.apparent,
        aberration=request.aberration,
        grav_deflection=request.grav_deflection,
        nutation=request.nutation,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )


def compute_planet_position_with_reduction(
    engine: Moira,
    request: PlanetPositionRequest,
) -> tuple[PlanetData, PlanetPositionReductionContext]:
    """Compute one planet position together with transport-safe reduction truth
    using pure low-level path and requested correction flags (no hardcodes).
    """

    _require_aware_datetime(request.dt)
    _require_supported_planet_body(request.body)
    jd_ut = jd_from_datetime(request.dt)
    planet = planet_at(
        request.body,
        jd_ut,
        reader=None,
        apparent=request.apparent,
        aberration=request.aberration,
        grav_deflection=request.grav_deflection,
        nutation=request.nutation,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )

    jd_tt = utc_to_tt(jd_ut)
    lst_deg: float | None = None
    if request.observer_lat is not None and request.observer_lon is not None:
        lst_deg, _ = _sidereal_context(jd_ut, request.observer_lon)
    obliquity_deg = true_obliquity(jd_tt)
    delta_t_seconds = delta_t_from_jd(jd_ut)
    normalized_datetime_utc = datetime_from_jd(jd_ut).astimezone(timezone.utc).isoformat()

    reduction = PlanetPositionReductionContext(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=normalized_datetime_utc,
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        delta_t_seconds=delta_t_seconds,
        observer=PositionObserverContext(
            latitude=request.observer_lat,
            longitude=request.observer_lon,
            elevation_m=request.observer_elev_m,
            local_sidereal_time_deg=lst_deg,
        ),
        stage_sequence=list(_PLANET_STAGE_SEQUENCE),
        obliquity_deg=obliquity_deg,
        topocentric_requested=(request.observer_lat is not None and request.observer_lon is not None),
        topocentric_applied=planet.is_topocentric,
        apparent=request.apparent,
        aberration=request.aberration,
        grav_deflection=request.grav_deflection,
        nutation=request.nutation,
    )
    return planet, reduction


def compute_sky_position(engine: Moira, request: SkyPositionRequest) -> SkyPosition:
    """Compute one sky position from a transport request using low-level sky_position_at
    with controllable correction and refraction params (closing hardcode gap).
    """

    _require_aware_datetime(request.dt)
    jd_ut = jd_from_datetime(request.dt)
    return sky_position_at(
        request.body,
        jd_ut,
        request.latitude,
        request.longitude,
        observer_elev_m=request.elevation_m,
        reader=None,
        aberration=request.aberration,
        grav_deflection=request.grav_deflection,
        nutation=request.nutation,
        refraction=request.refraction,
        pressure_mbar=request.pressure_mbar,
        temperature_c=request.temperature_c,
        relative_humidity=request.relative_humidity,
    )


def compute_sky_position_with_reduction(
    engine: Moira,
    request: SkyPositionRequest,
) -> tuple[SkyPosition, SkyPositionReductionContext]:
    """Compute one sky position together with transport-safe reduction truth
    using requested correction/refraction params (no hardcodes in truth).
    """

    _require_aware_datetime(request.dt)
    jd_ut = jd_from_datetime(request.dt)
    position = sky_position_at(
        request.body,
        jd_ut,
        request.latitude,
        request.longitude,
        observer_elev_m=request.elevation_m,
        reader=None,
        aberration=request.aberration,
        grav_deflection=request.grav_deflection,
        nutation=request.nutation,
        refraction=request.refraction,
        pressure_mbar=request.pressure_mbar,
        temperature_c=request.temperature_c,
        relative_humidity=request.relative_humidity,
    )
    jd_tt = utc_to_tt(jd_ut)
    lst_deg, obliquity_deg = _sidereal_context(jd_ut, request.longitude)
    delta_t_seconds = delta_t_from_jd(jd_ut)
    # Derive normalized from the jd used in computation (addressing the input-projection gap)
    normalized_datetime_utc = datetime_from_jd(jd_ut).astimezone(timezone.utc).isoformat()
    reduction = SkyPositionReductionContext(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=normalized_datetime_utc,
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        delta_t_seconds=delta_t_seconds,
        observer=PositionObserverContext(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation_m=request.elevation_m,
            local_sidereal_time_deg=lst_deg,
        ),
        stage_sequence=list(_SKY_STAGE_SEQUENCE),
        obliquity_deg=obliquity_deg,
        aberration=request.aberration,
        grav_deflection=request.grav_deflection,
        nutation=request.nutation,
        refraction=request.refraction,
        pressure_mbar=request.pressure_mbar,
        temperature_c=request.temperature_c,
        relative_humidity=request.relative_humidity,
    )
    return position, reduction

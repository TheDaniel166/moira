"""Krishnamurti stellar longitude chains and reader-bound Placidus charts."""
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from ._ephemeris_time import _bind_ephemeris_time
from .constants import HouseSystem
from .daily_panchanga import _finite_number, _validate_solar_location
from .dasha import VIMSHOTTARI_YEARS, _sequence_from
from .houses import HousePolicy, houses_from_armc
from .julian import _local_sidereal_time_at_tt, jd_from_datetime, utc_to_ut1
from .nodes import mean_node, true_node
from .obliquity import mean_obliquity, nutation
from .planets import planet_at
from .sidereal import Ayanamsa, NAKSHATRA_LORDS, NAKSHATRA_NAMES, _ayanamsa_truth_at_tt
from .spk_reader import KernelReader, get_reader, use_reader_override
from .varga import _normalize_longitude
from .vedic_dignities import _SIGN_RULER

__all__ = [
    "KPProfile", "KPSector", "KPLongitude", "KPChart", "kp_profiles", "kp_longitude", "kp_chart_for_datetime",
]

KPProfileId = Literal["krishnamurti_moira_placidus"]
KPNodeMode = Literal["mean", "true"]

_TICKS_PER_DEGREE = 10800  # three ticks per arcsecond
_STAR_TICKS = 144000
_SIGN_TICKS = 324000
_STAR_STARTS = tuple(i * _STAR_TICKS / _TICKS_PER_DEGREE for i in range(27))
_CLASSICAL = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")


@dataclass(frozen=True, slots=True)
class KPProfile:
    """The published division and the chart's declared modern realization."""

    profile_id: KPProfileId
    source_reference: str
    ayanamsa_system: str
    ayanamsa_mode: Literal["true"]
    house_system: str


_PROFILE = KPProfile(
    "krishnamurti_moira_placidus", "Krishnamurti Readers I, III pp. 503–504, VI; Astro Secrets Part V",
    Ayanamsa.KRISHNAMURTI, "true", HouseSystem.PLACIDUS,
)


@dataclass(frozen=True, slots=True)
class KPSector:
    """One half-open circular interval, expressed in thirds of an arcsecond."""

    lord: str
    start_ticks: int
    end_ticks: int


@dataclass(frozen=True, slots=True)
class KPLongitude:
    """The sign, star, sub and sub-sub corresponding to one sidereal angle."""

    profile_id: KPProfileId
    sidereal_longitude: float
    sign_index: int
    sign: KPSector
    nakshatra_index: int
    nakshatra: str
    star: KPSector
    sub: KPSector
    sub_sub: KPSector


@dataclass(frozen=True, slots=True)
class KPChart:
    """Geocentric chains and availability of the requested house geometry."""

    profile: KPProfile
    dt_utc: datetime
    jd_ut1: float
    jd_tt: float
    latitude: float
    longitude: float
    ayanamsa_degrees: float
    ayanamsa_path: str
    node_mode: KPNodeMode
    reader_binding: Literal["caller_owned_reader", "active_reader"]
    ephemeris_identity: str
    planets: dict[str, KPLongitude]
    cusps: tuple[KPLongitude, ...]
    cusp_status: Literal["available", "unavailable"]
    effective_house_system: str | None
    cusp_unavailable_reason: str | None


def kp_profiles() -> tuple[KPProfile, ...]:
    """List the admitted KP profile."""

    return (_PROFILE,)


def _require_profile(profile_id: KPProfileId) -> None:
    if profile_id != _PROFILE.profile_id:
        raise ValueError(f"Unknown KP profile: {profile_id!r}")


def _subdivision(longitude: float, parent: KPSector, unit: int) -> KPSector:
    start = parent.start_ticks
    for lord in _sequence_from(parent.lord):
        end = start + unit * VIMSHOTTARI_YEARS[lord]
        # A float input equal to the nearest representation of an exact
        # boundary belongs to the following interval.
        if longitude < end / _TICKS_PER_DEGREE:
            return KPSector(lord, start, end)
        start = end
    raise ArithmeticError("KP longitude falls outside its parent interval")


def kp_longitude(
    sidereal_longitude: float, *, profile_id: KPProfileId = "krishnamurti_moira_placidus",
) -> KPLongitude:
    """Classify an angle in [0, 360) using the published Vimshottari rotation."""

    _require_profile(profile_id)
    _finite_number("sidereal_longitude", sidereal_longitude)
    if not 0 <= sidereal_longitude < 360:
        raise ValueError("sidereal_longitude must be in [0, 360)")
    sign_index = int(sidereal_longitude // 30)
    sign = KPSector(_SIGN_RULER[sign_index], sign_index * _SIGN_TICKS, (sign_index + 1) * _SIGN_TICKS)
    star_index = bisect_right(_STAR_STARTS, sidereal_longitude) - 1
    star = KPSector(NAKSHATRA_LORDS[star_index], star_index * _STAR_TICKS, (star_index + 1) * _STAR_TICKS)
    sub = _subdivision(sidereal_longitude, star, 1200)
    sub_sub = _subdivision(sidereal_longitude, sub, 10 * VIMSHOTTARI_YEARS[sub.lord])
    return KPLongitude(
        profile_id, sidereal_longitude, sign_index, sign, star_index, NAKSHATRA_NAMES[star_index], star, sub, sub_sub,
    )


def kp_chart_for_datetime(
    dt: datetime, latitude: float, longitude: float, *,
    node_mode: KPNodeMode, profile_id: KPProfileId = "krishnamurti_moira_placidus",
    reader: KernelReader | None = None,
) -> KPChart:
    """Compose seven classical planets, both nodes and twelve Placidus cusp chains."""

    _require_profile(profile_id)
    _validate_solar_location(latitude, longitude)
    if node_mode not in ("mean", "true"):
        raise ValueError("node_mode must be 'mean' or 'true'")
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("dt must be a timezone-aware civil datetime")
    utc = dt.astimezone(timezone.utc)
    civil = utc.astimezone(dt.tzinfo)
    if civil.replace(tzinfo=None) != dt.replace(tzinfo=None) or civil.fold != dt.fold:
        raise ValueError("dt is a nonexistent or inconsistent local civil instant")
    jd_ut1 = utc_to_ut1(jd_from_datetime(utc))
    bound = get_reader() if reader is None else reader
    with use_reader_override(bound):
        epoch = _bind_ephemeris_time(jd_ut1, bound)
        jd_tt = epoch.epoch_tt
        frame = _ayanamsa_truth_at_tt(jd_tt, _PROFILE.ayanamsa_system, mode=_PROFILE.ayanamsa_mode, jd_ut=jd_ut1)
        point_longitudes = {
            body: planet_at(body, jd_ut1, reader=bound, jd_tt=jd_tt).longitude
            for body in _CLASSICAL
        }
        node = (mean_node(jd_ut1, jd_tt=jd_tt) if node_mode == "mean"
                else true_node(jd_ut1, reader=bound, jd_tt=jd_tt))
    point_longitudes["Rahu"] = node.longitude
    point_longitudes["Ketu"] = _normalize_longitude(node.longitude + 180.0)
    offset = frame.ayanamsa_deg
    planets = {body: kp_longitude(_normalize_longitude(lon - offset)) for body, lon in point_longitudes.items()}

    houses = None
    reason = None
    if abs(latitude) == 90:
        reason = "geographic_pole"
    else:
        mean_eps = mean_obliquity(jd_tt)
        dpsi, deps = nutation(jd_tt)
        armc = _local_sidereal_time_at_tt(jd_ut1, jd_tt, longitude, dpsi, mean_eps)
        try:
            houses = houses_from_armc(
                armc, mean_eps + deps, latitude, _PROFILE.house_system, policy=HousePolicy.strict(),
                ayanamsa_offset=offset,
            )
        except ValueError as exc:
            if not str(exc).startswith("latitude |") or "no unique ordered solution" not in str(exc):
                raise
            reason = "placidus_no_unique_ordered_solution"
    return KPChart(
        _PROFILE, utc, jd_ut1, jd_tt, latitude, longitude, offset, frame.effective_path, node_mode,
        "active_reader" if reader is None else "caller_owned_reader",
        epoch.identity.summary_label, planets,
        () if houses is None else tuple(kp_longitude(lon) for lon in houses.cusps),
        "unavailable" if houses is None else "available",
        None if houses is None else houses.effective_system, reason,
    )

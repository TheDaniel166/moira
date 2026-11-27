"""Source-defined Tithi Pravesha and monthly Tājika return timing."""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone as utc_timezone
from functools import lru_cache
from typing import Literal

from .chart import create_chart
from .constants import HouseSystem
from .daily_panchanga import (
    DailyPanchangaPolicy, PanchangaMoment, _civil_bounds, _finite_number, _moment,
    _resolve_timezone, _validate_solar_location,
)
from .julian import jd_from_datetime, utc_to_ut1
from .lunar_month import CalendarBoundary, _angular_boundaries
from .planets import planet_at
from .sidereal import ayanamsa_with_truth
from .spk_reader import get_reader, use_reader_override
from .transits import varshaphal

__all__ = [
    "VedicReturnCrossing", "VedicReturnChart", "TithiPraveshaCandidate", "TithiPraveshaResult",
    "MonthlyTajikaResult", "tithi_pravesha", "monthly_tajika",
]

_TithiProfile = Literal["rao_2014_tropical", "rao_2014_sidereal_comparison"]
_SECOND_TOL = 0.04


@dataclass(frozen=True, slots=True)
class VedicReturnCrossing:
    """Numerical angular evidence in UT1 with a signed residual in degrees."""

    jd_ut1: float
    lower_jd_ut1: float
    upper_jd_ut1: float
    target_degrees: float
    residual_degrees: float


@dataclass(frozen=True, slots=True)
class VedicReturnChart:
    """A sidereal snapshot with separately labelled apparent tropical inputs."""

    jd_ut1: float
    jd_tt: float
    ayanamsa_system: str
    ayanamsa_degrees: float
    latitude: float
    longitude: float
    house_system: str
    effective_house_system: str
    tropical_ascendant: float
    sidereal_ascendant: float
    sidereal_cusps: tuple[float, ...]
    tropical_longitudes: dict[str, float]
    sidereal_longitudes: dict[str, float]


@dataclass(frozen=True, slots=True)
class TithiPraveshaCandidate:
    """One matching lunation and the candidate return owned by it."""

    conjunction: CalendarBoundary
    next_conjunction: CalendarBoundary
    conjunction_sign_index: int
    crossing: VedicReturnCrossing
    time: PanchangaMoment


@dataclass(frozen=True, slots=True)
class TithiPraveshaResult:
    """Annual search evidence including all matches when selection is ambiguous."""

    profile_id: _TithiProfile
    return_year: int
    timezone: str
    year_start_jd_ut1: float
    year_end_jd_ut1: float
    natal_phase_degrees: float
    natal_conjunction: CalendarBoundary | None
    natal_conjunction_sign_index: int | None
    candidates: tuple[TithiPraveshaCandidate, ...]
    status: Literal["available", "unavailable", "ambiguous"]
    reason: str | None
    chart: VedicReturnChart | None
    source_reference: str = field(init=False, default="Narasimha Rao, Re-defining Tithi Pravesha Chart (2014)")


@dataclass(frozen=True, slots=True)
class MonthlyTajikaResult:
    """A modern ephemeris realization of one monthly sidereal solar return."""

    return_year: int
    month: int
    annual_return_jd_ut1: float
    next_annual_return_jd_ut1: float
    target_sidereal_sun_degrees: float
    time: PanchangaMoment
    crossing: VedicReturnCrossing | None
    chart: VedicReturnChart
    profile_id: Literal["hayanaratna_sidereal_ephemeris"] = field(
        init=False, default="hayanaratna_sidereal_ephemeris",
    )
    source_reference: str = field(init=False, default="Balabhadra, Hayanaratna 8.1–8.3, ed. Gansten")


def _sidereal_offset(jd, system):
    truth = ayanamsa_with_truth(jd, system)
    if truth.fallback_applied:
        raise ValueError("return calculation requires the selected ayanamsa anchor")
    return truth.ayanamsa_deg


def _return_chart(jd, latitude, longitude, system, house_system, reader):
    chart = create_chart(jd, latitude, longitude, house_system=house_system, reader=reader)
    houses = chart.houses
    offset = _sidereal_offset(jd, system)
    tropical = {name: position.longitude for name, position in (chart.planets | chart.nodes).items()}
    sidereal = {name: (value - offset) % 360 for name, value in tropical.items()}
    return VedicReturnChart(
        jd, chart.jd_tt, system, offset, latitude, longitude, str(houses.system), str(houses.effective_system),
        houses.asc, (houses.asc - offset) % 360, tuple((cusp - offset) % 360 for cusp in houses.cusps),
        tropical, sidereal,
    )


def _natal_jd(natal_dt, return_year, zone):
    if not isinstance(natal_dt, datetime) or natal_dt.tzinfo is None or natal_dt.utcoffset() is None:
        raise ValueError("natal_dt must be an aware civil datetime")
    utc = natal_dt.astimezone(utc_timezone.utc)
    roundtrip = utc.astimezone(natal_dt.tzinfo)
    if roundtrip.replace(tzinfo=None) != natal_dt.replace(tzinfo=None) or roundtrip.fold != natal_dt.fold:
        raise ValueError("natal_dt is a nonexistent or inconsistent civil instant")
    year = natal_dt.astimezone(zone).year
    if type(return_year) is not int or not 2 <= year < return_year <= 9997:
        raise ValueError("return_year must follow the local natal year and be at most 9997")
    return utc_to_ut1(jd_from_datetime(utc))


def _crossing(root, target, angle):
    jd = root.jd_ut1
    residual = (angle(jd) - target + 180) % 360 - 180
    return VedicReturnCrossing(jd, root.lower_jd_ut1, root.upper_jd_ut1, target, residual)


def _conjunction_sign(root, longitude):
    earlier = int(longitude(root.lower_jd_ut1) // 30)
    later = int(longitude(root.upper_jd_ut1) // 30)
    return earlier if earlier == later else None


def tithi_pravesha(
    natal_dt: datetime, return_year: int, latitude: float, longitude: float, *,
    timezone: str, profile: _TithiProfile, ayanamsa_system: str = "True Pushya",
    house_system: str = HouseSystem.PLACIDUS, reader=None,
) -> TithiPraveshaResult:
    """Find the exact natal elongation in lunations matching Rao's conjunction sign.

    The explicit timezone defines the Gregorian candidate year. A previous
    conjunction may occur before that year if its phase return lies inside it.
    Duplicate matches are returned without selecting one.
    """
    if profile not in ("rao_2014_tropical", "rao_2014_sidereal_comparison"):
        raise ValueError("unknown Tithi Pravesha profile")
    _validate_solar_location(latitude, longitude)
    system = DailyPanchangaPolicy(ayanamsa_system=ayanamsa_system).ayanamsa_system
    zone = _resolve_timezone(timezone)
    natal_jd = _natal_jd(natal_dt, return_year, zone)
    start, _ = _civil_bounds(date(return_year, 1, 1), zone)
    end, _ = _civil_bounds(date(return_year + 1, 1, 1), zone)
    bound = get_reader() if reader is None else reader

    with use_reader_override(bound):
        @lru_cache(maxsize=4096)
        def sun(jd):
            return planet_at("Sun", jd, reader=bound).longitude

        @lru_cache(maxsize=4096)
        def phase(jd):
            return (planet_at("Moon", jd, reader=bound).longitude - sun(jd)) % 360

        def sign_longitude(jd):
            if profile == "rao_2014_tropical":
                return sun(jd)
            return (sun(jd) - _sidereal_offset(jd, system)) % 360

        def new_moons(left, right):
            return _angular_boundaries(left, right, phase, 360, _SECOND_TOL, True)

        natal_phase = phase(natal_jd)
        natal_roots = new_moons(natal_jd - 40, natal_jd + 1)
        natal = max((x for x in natal_roots if x.jd_ut1 <= natal_jd), key=lambda x: x.jd_ut1)
        natal_sign = _conjunction_sign(natal, sign_longitude)
        fields = (profile, return_year, timezone, start, end, natal_phase)
        if any(x.lower_jd_ut1 <= natal_jd < x.upper_jd_ut1 for x in natal_roots):
            return TithiPraveshaResult(*fields, None, None, (), "ambiguous", "natal_conjunction_boundary", None)
        if natal_sign is None:
            return TithiPraveshaResult(*fields, natal, None, (), "ambiguous", "natal_conjunction_sign_boundary", None)

        new = new_moons(start - 40, end + 40)
        if not new or new[0].jd_ut1 >= start or new[-1].lower_jd_ut1 <= end:
            raise RuntimeError("Tithi Pravesha could not bracket the requested civil year")
        candidates, uncertain = [], False
        for left, right in zip(new, new[1:]):
            if left.lower_jd_ut1 >= end or right.jd_ut1 < start:
                continue
            coordinate = _conjunction_sign(left, sign_longitude)
            if coordinate is None:
                if natal_sign not in {int(sign_longitude(jd) // 30)
                                      for jd in (left.lower_jd_ut1, left.upper_jd_ut1)}:
                    continue
            elif coordinate != natal_sign:
                continue

            # Exclude the adjacent lunation's event if the phase is close to
            # a conjunction. One day inward at the opposite end is far from
            # the requested half-cycle and preserves the desired crossing.
            if natal_phase == 0:
                root = left
            else:
                before, after = (left.lower_jd_ut1 - 0.01, right.lower_jd_ut1 - 1)
                if natal_phase > 180:
                    before, after = (left.jd_ut1 + 1, right.jd_ut1 + 0.01)
                roots = _angular_boundaries(before, after, lambda jd: (phase(jd) - natal_phase) % 360,
                                            360, _SECOND_TOL, True)
                if len(roots) != 1:
                    raise RuntimeError("Tithi Pravesha did not solve a unique phase inside the candidate lunation")
                root = roots[0]
            if root.jd_ut1 < start or root.lower_jd_ut1 >= end:
                continue
            if (coordinate is None or root.lower_jd_ut1 < start <= root.jd_ut1
                    or root.lower_jd_ut1 < end <= root.jd_ut1):
                uncertain = True
            crossing = _crossing(root, natal_phase, phase)
            candidates.append(TithiPraveshaCandidate(
                left, right, natal_sign, crossing, _moment(crossing.jd_ut1, zone),
            ))

        candidates = tuple(candidates)
        status, reason, chart = "available", None, None
        if uncertain or len(candidates) > 1:
            status, reason = "ambiguous", "boundary_uncertain" if uncertain else "multiple_matching_lunations"
        elif not candidates:
            status, reason = "unavailable", "no_matching_lunation_in_year"
        else:
            chart = _return_chart(
                candidates[0].crossing.jd_ut1, latitude, longitude, system, house_system, bound,
            )
        return TithiPraveshaResult(*fields, natal, natal_sign, candidates, status, reason, chart)


def monthly_tajika(
    birth_jd_ut1: float, return_year: int, month: int, latitude: float, longitude: float, *,
    timezone: str = "UTC", ayanamsa_system: str = "Lahiri",
    house_system: str = HouseSystem.PLACIDUS, reader=None,
) -> MonthlyTajikaResult:
    """Solve Balabhadra's true solar target using Moira's sidereal annual anchor.

    Month 1 inherits Varshaphal's exact annual instant. Months 2 through 12
    solve successive 30-degree increments within that annual year.
    """
    _finite_number("birth_jd_ut1", birth_jd_ut1)
    if type(month) is not int or not 1 <= month <= 12:
        raise ValueError("month must be an integer in [1, 12]")
    if type(return_year) is not int or not 2 <= return_year <= 9997:
        raise ValueError("return_year must be an integer in [2, 9997]")
    _validate_solar_location(latitude, longitude)
    zone = _resolve_timezone(timezone)
    if not -10_000_000 <= birth_jd_ut1 <= 10_000_000:
        raise ValueError("birth_jd_ut1 is out of bounds")
    if birth_jd_ut1 >= _civil_bounds(date(return_year + 1, 1, 1), utc_timezone.utc)[0]:
        raise ValueError("return_year precedes the natal epoch")
    system = DailyPanchangaPolicy(ayanamsa_system=ayanamsa_system).ayanamsa_system
    bound = get_reader() if reader is None else reader

    with use_reader_override(bound):
        def solar(jd):
            return (planet_at("Sun", jd, reader=bound).longitude - _sidereal_offset(jd, system)) % 360

        natal = solar(birth_jd_ut1)
        annual = varshaphal(birth_jd_ut1, return_year, system, reader=bound)
        following = varshaphal(birth_jd_ut1, return_year + 1, system, reader=bound)
        if annual < birth_jd_ut1 - 0.04 / 86400 or not 360 < following - annual < 370:
            raise ValueError("annual return must occur at or after birth and precede the following return")
        motion = 30 * (month - 1)
        target = (natal + motion) % 360
        jd, crossing = annual, None
        if month != 1:
            candidates = _angular_boundaries(annual, following, lambda t: (solar(t) - target) % 360,
                                             360, _SECOND_TOL, False)
            if len(candidates) != 1:
                raise RuntimeError("could not bracket the unique monthly solar crossing")
            crossing = _crossing(candidates[0], target, solar)
            jd = crossing.jd_ut1
        chart = _return_chart(jd, latitude, longitude, system, house_system, bound)
    return MonthlyTajikaResult(return_year, month, annual, following, target, _moment(jd, zone), crossing, chart)

"""Chart-backed Church of Light progression geometry and Astrodyne assembly."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Mapping, Sequence

from .astrodynes import (
    ASTRODYNE_ASPECT_ORB_ROWS,
    ASTRODYNE_PLANETS,
    ASTRODYNE_POINTS,
    ASTRODYNE_SIGNS,
    AstrodyneChartResult,
    mutual_reception,
    natal_astrodynes_from_geometry,
)
from .constants import HouseSystem
from .coordinates import ecliptic_to_equatorial
from .houses import (
    HousePolicy,
    assign_house,
    calculate_houses,
    describe_angularity,
    houses_from_armc,
)
from .julian import datetime_from_jd, jd_from_datetime
from .obliquity import true_obliquity
from .planets import get_reader, planet_at
from .progressed_astrodynes import (
    ProgressedAccessoryAspectRelation,
    ProgressedAstrodyneTerminal,
    ProgressedBaselineValue,
    ProgressedBodyPlacement,
    ProgressedMajorAspectRelation,
    ProgressedMutualReceptionAllocation,
    ProgressedNatalBodyValue,
    ProgressedNormalHoroscope,
    ProgressedPracticalHoroscope,
    ProgressedReenforcementTruth,
    ProgressedTerminalKind,
    ProgressedTerminalLocation,
    dated_aspect_from_major_relation,
    evaluate_accessory_progressed_relation,
    evaluate_major_progressed_relation,
    normal_progressed_horoscope,
    practical_progressed_horoscope,
    reenforce_major_progressed_relation,
)


_BODY_ORDER = (*ASTRODYNE_PLANETS, *ASTRODYNE_POINTS)
_ASPECTS = tuple(row.aspect for row in ASTRODYNE_ASPECT_ORB_ROWS)


@dataclass(frozen=True, slots=True)
class ChurchOfLightProgressionPolicy:
    """Fixed geometry doctrine from Church of Light Course X-2."""

    major_month_hours: float = 2.0
    major_day_minutes: float = 4.0
    symbolic_month_days: float = 30.0
    minor_ephemeris_days_per_year: float = 27.3
    life_year_days: float = 365.25
    minor_search_span_days: float = 20.0
    minor_search_step_days: float = 0.25
    planetary_frame: str = "geocentric_apparent"
    angle_method: str = "sun_mc_constant_and_natal_latitude_horizon"

    def __post_init__(self) -> None:
        defaults = ChurchOfLightProgressionPolicy.__dataclass_fields__
        for name, field in defaults.items():
            if getattr(self, name) != field.default:
                raise ValueError(f"unsupported Church of Light policy variant: {name}")


DEFAULT_CHURCH_OF_LIGHT_PROGRESSION_POLICY = ChurchOfLightProgressionPolicy()


@dataclass(frozen=True, slots=True)
class ChurchOfLightSymbolicDate:
    """Thirty-day-month calendar date used by the Limiting Date arithmetic."""

    year: int
    month: int
    day: float

    def __post_init__(self) -> None:
        if self.month not in range(1, 13):
            raise ValueError("symbolic month must be in [1, 12]")
        if not isfinite(self.day) or not 0.0 < self.day <= 30.0:
            raise ValueError("symbolic day must be finite and in (0, 30]")


@dataclass(frozen=True, slots=True)
class ChurchOfLightProgressionTimeTruth:
    """Vessel: Structured Church of Light progression time truth data."""
    natal_jd_ut: float
    target_jd_ut: float
    greenwich_noon_jd_ut: float
    egmt_interval_hours: float
    limiting_date: ChurchOfLightSymbolicDate
    major_completed_years: int
    major_calendar_offset_days: float
    major_egmt_interval_hours: float
    major_ephemeris_jd_ut: float
    minor_approximate_jd_ut: float
    minor_ephemeris_jd_ut: float
    transit_jd_ut: float
    solar_constant_deg: float
    minor_moon_target_longitude_deg: float
    midheaven_constant_deg: float

    @property
    def major_ephemeris_datetime(self) -> datetime:
        return datetime_from_jd(self.major_ephemeris_jd_ut)

    @property
    def minor_ephemeris_datetime(self) -> datetime:
        return datetime_from_jd(self.minor_ephemeris_jd_ut)


@dataclass(frozen=True, slots=True)
class ChurchOfLightProgressionGeometry:
    """Vessel: Structured Church of Light progression geometry data."""
    natal_dt: datetime
    target_dt: datetime
    observer_lat: float
    observer_lon: float
    requested_house_system: str
    effective_house_system: str
    house_fallback: bool
    house_fallback_reason: str | None
    natal_cusps: tuple[float, ...]
    time_truth: ChurchOfLightProgressionTimeTruth
    natal_terminals: tuple[ProgressedAstrodyneTerminal, ...]
    major_terminals: tuple[ProgressedAstrodyneTerminal, ...]
    minor_terminals: tuple[ProgressedAstrodyneTerminal, ...]
    transit_terminals: tuple[ProgressedAstrodyneTerminal, ...]

    def __post_init__(self) -> None:
        for label, terminals, kind in (
            ("natal", self.natal_terminals, ProgressedTerminalKind.RADICAL),
            ("major", self.major_terminals, ProgressedTerminalKind.MAJOR_PROGRESSED),
            ("minor", self.minor_terminals, ProgressedTerminalKind.MINOR_PROGRESSED),
            ("transit", self.transit_terminals, ProgressedTerminalKind.TRANSIT),
        ):
            if tuple(item.body for item in terminals) != _BODY_ORDER:
                raise ValueError(f"{label} terminals are not in canonical order")
            if any(item.kind is not kind for item in terminals):
                raise ValueError(f"{label} terminal kinds are inconsistent")

    def terminal(self, terminal_id: str) -> ProgressedAstrodyneTerminal:
        for terminal in (
            *self.natal_terminals,
            *self.major_terminals,
            *self.minor_terminals,
            *self.transit_terminals,
        ):
            if terminal.terminal_id == terminal_id:
                return terminal
        raise KeyError(terminal_id)


@dataclass(frozen=True, slots=True)
class ChurchOfLightProgressedAstrodynesChart:
    """Vessel: Structured Church of Light progressed astrodynes chart data."""
    geometry: ChurchOfLightProgressionGeometry
    natal: AstrodyneChartResult
    normal: ProgressedNormalHoroscope
    major_relations: tuple[ProgressedMajorAspectRelation, ...]
    minor_relations: tuple[ProgressedAccessoryAspectRelation, ...]
    transit_relations: tuple[ProgressedAccessoryAspectRelation, ...]
    reenforcements: tuple[ProgressedReenforcementTruth, ...]
    practical: ProgressedPracticalHoroscope

    def __post_init__(self) -> None:
        for relations in (
            self.major_relations,
            self.minor_relations,
            self.transit_relations,
        ):
            ids = tuple(item.relation_id for item in relations)
            if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
                raise ValueError("progressed relations must be uniquely sorted")


def _aware_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _validate_observer(latitude: float, longitude: float) -> tuple[float, float]:
    if not isfinite(latitude) or not -90.0 <= latitude <= 90.0:
        raise ValueError("observer_lat must be finite and in [-90, 90]")
    if not isfinite(longitude) or not -180.0 <= longitude <= 180.0:
        raise ValueError("observer_lon must be finite and in [-180, 180]")
    return float(latitude), float(longitude)


def _symbolic_shift(
    year: int,
    month: int,
    day: float,
    delta_months: int,
    delta_days: float,
) -> ChurchOfLightSymbolicDate:
    month_index = year * 12 + month - 1 + delta_months
    shifted_day = day + delta_days
    while shifted_day <= 0.0:
        month_index -= 1
        shifted_day += 30.0
    while shifted_day > 30.0:
        month_index += 1
        shifted_day -= 30.0
    shifted_year, shifted_month = divmod(month_index, 12)
    return ChurchOfLightSymbolicDate(shifted_year, shifted_month + 1, shifted_day)


def _limiting_date(
    natal_utc: datetime,
) -> tuple[float, float, ChurchOfLightSymbolicDate]:
    noon = datetime(
        natal_utc.year,
        natal_utc.month,
        natal_utc.day,
        12,
        tzinfo=timezone.utc,
    )
    egmt_hours = (natal_utc - noon).total_seconds() / 3600.0
    magnitude = abs(egmt_hours)
    months = int(magnitude // 2.0)
    days = (magnitude - months * 2.0) * 15.0
    direction = 1 if egmt_hours < 0.0 else -1
    limiting = _symbolic_shift(
        natal_utc.year,
        natal_utc.month,
        float(natal_utc.day),
        direction * months,
        direction * days,
    )
    return jd_from_datetime(noon), egmt_hours, limiting


def _major_ephemeris_jd(
    natal_noon_jd: float,
    limiting: ChurchOfLightSymbolicDate,
    target_utc: datetime,
) -> tuple[int, float, float, float]:
    target_day = target_utc.day + (
        target_utc.hour
        + target_utc.minute / 60.0
        + target_utc.second / 3600.0
        + target_utc.microsecond / 3_600_000_000.0
        - 12.0
    ) / 24.0
    offset = (
        (target_utc.month - limiting.month) * 30.0
        + target_day
        - limiting.day
    )
    year_delta = target_utc.year - limiting.year
    while offset <= -180.0:
        offset += 360.0
        year_delta -= 1
    while offset > 180.0:
        offset -= 360.0
        year_delta += 1
    egmt_hours = offset * (4.0 / 60.0)
    return year_delta, offset, egmt_hours, natal_noon_jd + year_delta + egmt_hours / 24.0


def _angle_delta(first: float, second: float) -> float:
    return (first - second + 180.0) % 360.0 - 180.0


def _minor_ephemeris_jd(
    reader,
    approximate_jd: float,
    target_moon_longitude: float,
    policy: ChurchOfLightProgressionPolicy,
) -> float:
    def residual(jd: float) -> float:
        moon = planet_at("Moon", jd, reader=reader).longitude
        return _angle_delta(moon, target_moon_longitude)

    roots: list[float] = []
    left = approximate_jd - policy.minor_search_span_days
    stop = approximate_jd + policy.minor_search_span_days
    f_left = residual(left)
    while left < stop:
        right = min(left + policy.minor_search_step_days, stop)
        f_right = residual(right)
        if f_left == 0.0 or (
            f_left * f_right < 0.0 and abs(f_left - f_right) < 180.0
        ):
            lo, hi, f_lo = left, right, f_left
            for _ in range(52):
                mid = (lo + hi) / 2.0
                f_mid = residual(mid)
                if f_lo * f_mid <= 0.0:
                    hi = mid
                else:
                    lo, f_lo = mid, f_mid
            roots.append((lo + hi) / 2.0)
        left, f_left = right, f_right
    if not roots:
        raise ValueError("minor ephemeris Moon solve found no root in the source window")
    return min(roots, key=lambda value: abs(value - approximate_jd))


def _angle_longitudes(
    sun_longitude: float,
    natal_sun_longitude: float,
    natal_mc_longitude: float,
    jd_ut: float,
    latitude: float,
    system: str,
    house_policy: HousePolicy,
) -> tuple[float, float]:
    mc = (natal_mc_longitude + sun_longitude - natal_sun_longitude) % 360.0
    obliquity = true_obliquity(jd_ut)
    armc = ecliptic_to_equatorial(mc, 0.0, obliquity)[0]
    frame = houses_from_armc(
        armc,
        obliquity,
        latitude,
        system=system,
        policy=house_policy,
        sun_longitude=sun_longitude,
    )
    return mc, frame.asc


def _terminal_set(
    reader,
    jd_ut: float,
    kind: ProgressedTerminalKind,
    natal_houses,
    natal_sun_longitude: float,
    natal_mc_longitude: float,
    latitude: float,
    system: str,
    house_policy: HousePolicy,
) -> tuple[ProgressedAstrodyneTerminal, ...]:
    obliquity = true_obliquity(jd_ut)
    positions = {
        body: planet_at(body, jd_ut, reader=reader)
        for body in ASTRODYNE_PLANETS
    }
    sun_longitude = positions["Sun"].longitude
    if kind is ProgressedTerminalKind.RADICAL:
        mc, asc = natal_houses.mc, natal_houses.asc
    else:
        mc, asc = _angle_longitudes(
            sun_longitude,
            natal_sun_longitude,
            natal_mc_longitude,
            jd_ut,
            latitude,
            system,
            house_policy,
        )
    longitudes = {
        **{body: position.longitude for body, position in positions.items()},
        "M.C.": mc,
        "Asc.": asc,
    }
    latitudes = {
        **{body: position.latitude for body, position in positions.items()},
        "M.C.": 0.0,
        "Asc.": 0.0,
    }
    result = []
    for body in _BODY_ORDER:
        placement = assign_house(longitudes[body], natal_houses)
        house_class = describe_angularity(placement).category.value
        declination = ecliptic_to_equatorial(
            longitudes[body], latitudes[body], obliquity
        )[1]
        result.append(
            ProgressedAstrodyneTerminal(
                body,
                kind,
                longitudes[body],
                house_class,
                declination,
            )
        )
    return tuple(result)


def church_of_light_progression_geometry(
    natal_dt: datetime,
    target_dt: datetime,
    observer_lat: float,
    observer_lon: float,
    *,
    house_system: str = HouseSystem.PLACIDUS,
    allow_house_fallback: bool = False,
    reader=None,
    policy: ChurchOfLightProgressionPolicy | None = None,
) -> ChurchOfLightProgressionGeometry:
    """Build radical, major, minor, and transit terminal geometry."""

    active_policy = DEFAULT_CHURCH_OF_LIGHT_PROGRESSION_POLICY if policy is None else policy
    if not isinstance(active_policy, ChurchOfLightProgressionPolicy):
        raise TypeError("policy must be ChurchOfLightProgressionPolicy")
    natal_utc = _aware_utc(natal_dt, "natal_dt")
    target_utc = _aware_utc(target_dt, "target_dt")
    if target_utc < natal_utc:
        raise ValueError("target_dt must not precede natal_dt")
    latitude, longitude = _validate_observer(observer_lat, observer_lon)
    if reader is None:
        reader = get_reader()
    natal_jd = jd_from_datetime(natal_utc)
    target_jd = jd_from_datetime(target_utc)
    house_policy = HousePolicy.default() if allow_house_fallback else HousePolicy.strict()
    natal_houses = calculate_houses(
        natal_jd,
        latitude,
        longitude,
        system=house_system,
        policy=house_policy,
    )
    natal_noon_jd, egmt_hours, limiting = _limiting_date(natal_utc)
    completed_years, offset_days, major_egmt, major_jd = _major_ephemeris_jd(
        natal_noon_jd,
        limiting,
        target_utc,
    )
    natal_sun = planet_at("Sun", natal_jd, reader=reader).longitude
    natal_moon = planet_at("Moon", natal_jd, reader=reader).longitude
    transit_sun = planet_at("Sun", target_jd, reader=reader).longitude
    solar_constant = _angle_delta(natal_sun, natal_moon)
    minor_moon_target = (transit_sun - solar_constant) % 360.0
    age_years = (target_jd - natal_jd) / active_policy.life_year_days
    minor_approximate_jd = (
        natal_jd + age_years * active_policy.minor_ephemeris_days_per_year
    )
    minor_jd = _minor_ephemeris_jd(
        reader,
        minor_approximate_jd,
        minor_moon_target,
        active_policy,
    )
    natal_terminals = _terminal_set(
        reader,
        natal_jd,
        ProgressedTerminalKind.RADICAL,
        natal_houses,
        natal_sun,
        natal_houses.mc,
        latitude,
        house_system,
        house_policy,
    )
    major_terminals = _terminal_set(
        reader,
        major_jd,
        ProgressedTerminalKind.MAJOR_PROGRESSED,
        natal_houses,
        natal_sun,
        natal_houses.mc,
        latitude,
        house_system,
        house_policy,
    )
    minor_terminals = _terminal_set(
        reader,
        minor_jd,
        ProgressedTerminalKind.MINOR_PROGRESSED,
        natal_houses,
        natal_sun,
        natal_houses.mc,
        latitude,
        house_system,
        house_policy,
    )
    transit_terminals = _terminal_set(
        reader,
        target_jd,
        ProgressedTerminalKind.TRANSIT,
        natal_houses,
        natal_sun,
        natal_houses.mc,
        latitude,
        house_system,
        house_policy,
    )
    time_truth = ChurchOfLightProgressionTimeTruth(
        natal_jd_ut=natal_jd,
        target_jd_ut=target_jd,
        greenwich_noon_jd_ut=natal_noon_jd,
        egmt_interval_hours=egmt_hours,
        limiting_date=limiting,
        major_completed_years=completed_years,
        major_calendar_offset_days=offset_days,
        major_egmt_interval_hours=major_egmt,
        major_ephemeris_jd_ut=major_jd,
        minor_approximate_jd_ut=minor_approximate_jd,
        minor_ephemeris_jd_ut=minor_jd,
        transit_jd_ut=target_jd,
        solar_constant_deg=solar_constant,
        minor_moon_target_longitude_deg=minor_moon_target,
        midheaven_constant_deg=_angle_delta(natal_sun, natal_houses.mc),
    )
    return ChurchOfLightProgressionGeometry(
        natal_dt=natal_utc,
        target_dt=target_utc,
        observer_lat=latitude,
        observer_lon=longitude,
        requested_house_system=house_system,
        effective_house_system=natal_houses.effective_system,
        house_fallback=natal_houses.fallback,
        house_fallback_reason=natal_houses.fallback_reason,
        natal_cusps=tuple(natal_houses.cusps),
        time_truth=time_truth,
        natal_terminals=natal_terminals,
        major_terminals=major_terminals,
        minor_terminals=minor_terminals,
        transit_terminals=transit_terminals,
    )


def _zodiacal_distance(first: float, second: float, aspect: str) -> float:
    row = next(row for row in ASTRODYNE_ASPECT_ORB_ROWS if row.aspect == aspect)
    separation = abs(_angle_delta(first, second))
    return abs(separation - row.exact_angle_deg) * 60.0


def _parallel_distance(
    first: ProgressedAstrodyneTerminal,
    second: ProgressedAstrodyneTerminal,
) -> float:
    assert first.declination_deg is not None and second.declination_deg is not None
    return abs(abs(first.declination_deg) - abs(second.declination_deg)) * 60.0


def _major_relations(
    geometry: ChurchOfLightProgressionGeometry,
    natal_values: Mapping[str, ProgressedNatalBodyValue],
) -> tuple[ProgressedMajorAspectRelation, ...]:
    radical = {item.body: item for item in geometry.natal_terminals}
    major = {item.body: item for item in geometry.major_terminals}
    relations: dict[str, ProgressedMajorAspectRelation] = {}

    def admit(
        first,
        second,
        counterpart_first,
        counterpart_second,
        aspect,
    ) -> None:
        relation = evaluate_major_progressed_relation(
            first,
            second,
            counterpart_first,
            counterpart_second,
            natal_values[first.body],
            natal_values[second.body],
            aspect,
        )
        if relation.admitted:
            relations[relation.relation_id] = relation

    for body_a in _BODY_ORDER:
        for body_b in _BODY_ORDER:
            first, second = major[body_a], radical[body_b]
            counterpart_a = None if body_a == body_b else radical[body_a]
            counterpart_b = None if body_a == body_b else major[body_b]
            for aspect in _ASPECTS:
                if _zodiacal_distance(first.longitude_deg, second.longitude_deg, aspect) <= 60.0:
                    admit(first, second, counterpart_a, counterpart_b, aspect)
            if _parallel_distance(first, second) <= 60.0:
                admit(first, second, counterpart_a, counterpart_b, "parallel")
    for index, body_a in enumerate(_BODY_ORDER):
        for body_b in _BODY_ORDER[index + 1 :]:
            first, second = major[body_a], major[body_b]
            for aspect in _ASPECTS:
                if _zodiacal_distance(first.longitude_deg, second.longitude_deg, aspect) <= 60.0:
                    admit(first, second, radical[body_a], radical[body_b], aspect)
            if _parallel_distance(first, second) <= 60.0:
                admit(first, second, radical[body_a], radical[body_b], "parallel")
    return tuple(relations[key] for key in sorted(relations))


def _accessory_relations(
    moving_terminals: Sequence[ProgressedAstrodyneTerminal],
    geometry: ChurchOfLightProgressionGeometry,
    natal_values: Mapping[str, ProgressedNatalBodyValue],
) -> tuple[ProgressedAccessoryAspectRelation, ...]:
    radical = {item.body: item for item in geometry.natal_terminals}
    major = {item.body: item for item in geometry.major_terminals}
    relations: dict[str, ProgressedAccessoryAspectRelation] = {}
    for moving in moving_terminals:
        for target_map, counterpart_map in ((radical, major), (major, radical)):
            for body in _BODY_ORDER:
                target, counterpart = target_map[body], counterpart_map[body]
                for aspect in _ASPECTS:
                    if _zodiacal_distance(moving.longitude_deg, target.longitude_deg, aspect) <= 60.0:
                        relation = evaluate_accessory_progressed_relation(
                            moving,
                            target,
                            counterpart,
                            natal_values[moving.body],
                            natal_values[target.body],
                            aspect,
                        )
                        if relation.admitted:
                            relations[relation.relation_id] = relation
                if _parallel_distance(moving, target) <= 60.0:
                    relation = evaluate_accessory_progressed_relation(
                        moving,
                        target,
                        counterpart,
                        natal_values[moving.body],
                        natal_values[target.body],
                        "parallel",
                    )
                    if relation.admitted:
                        relations[relation.relation_id] = relation
    return tuple(relations[key] for key in sorted(relations))


def _mutual_reception_allocations(
    relations: Sequence[ProgressedMajorAspectRelation],
) -> tuple[ProgressedMutualReceptionAllocation, ...]:
    allocations: dict[str, ProgressedMutualReceptionAllocation] = {}
    for relation in relations:
        first, second = relation.direct_terminals
        if first.body not in ASTRODYNE_PLANETS or second.body not in ASTRODYNE_PLANETS:
            continue
        if first.body == second.body:
            continue
        first_sign = ASTRODYNE_SIGNS[int(first.longitude_deg // 30.0)]
        second_sign = ASTRODYNE_SIGNS[int(second.longitude_deg // 30.0)]
        reception = mutual_reception(first.body, first_sign, second.body, second_sign)
        if not reception.admitted:
            continue
        direct_ids = {item.body: item.terminal_id for item in relation.direct_terminals}
        indirect_ids = {item.body: item.terminal_id for item in relation.indirect_terminals}
        for body in (first.body, second.body):
            allocation_id = f"{relation.relation_id}|mr|{body}"
            allocations[allocation_id] = ProgressedMutualReceptionAllocation(
                allocation_id,
                body,
                (direct_ids[body],),
                (indirect_ids[body],),
                2.5,
            )
    return tuple(allocations[key] for key in sorted(allocations))


def church_of_light_progressed_astrodynes_chart(
    natal_dt: datetime,
    target_dt: datetime,
    observer_lat: float,
    observer_lon: float,
    *,
    house_system: str = HouseSystem.PLACIDUS,
    allow_house_fallback: bool = False,
    reader=None,
    policy: ChurchOfLightProgressionPolicy | None = None,
) -> ChurchOfLightProgressedAstrodynesChart:
    """Compute the complete chart-backed Church of Light progressed product."""

    if reader is None:
        reader = get_reader()
    geometry = church_of_light_progression_geometry(
        natal_dt,
        target_dt,
        observer_lat,
        observer_lon,
        house_system=house_system,
        allow_house_fallback=allow_house_fallback,
        reader=reader,
        policy=policy,
    )
    radical = {item.body: item for item in geometry.natal_terminals}
    planet_longitudes = {body: radical[body].longitude_deg for body in ASTRODYNE_PLANETS}
    declinations = {body: radical[body].declination_deg for body in _BODY_ORDER}
    natal = natal_astrodynes_from_geometry(
        planet_longitudes,
        declinations,
        geometry.natal_cusps,
        radical["M.C."].longitude_deg,
        radical["Asc."].longitude_deg,
    )
    natal_values = {
        profile.body: ProgressedNatalBodyValue(
            profile.body,
            profile.total_power,
            profile.total_harmony,
            profile.total_discord,
        )
        for profile in natal.profiles
    }
    sign_values = {
        entry.sign: ProgressedBaselineValue(
            entry.total_power,
            entry.total_harmony,
            entry.total_discord,
        )
        for entry in natal.aggregate.signs
    }
    house_values = {
        entry.house: ProgressedBaselineValue(
            entry.total_power,
            entry.total_harmony,
            entry.total_discord,
        )
        for entry in natal.aggregate.houses
    }
    major_by_body = {item.body: item for item in geometry.major_terminals}
    placements = tuple(
        ProgressedBodyPlacement(
            body,
            major_by_body[body].longitude_deg,
            assign_house(major_by_body[body].longitude_deg, _house_figure(geometry)).house,
        )
        for body in _BODY_ORDER
    )
    normal = normal_progressed_horoscope(
        tuple(natal_values[body] for body in _BODY_ORDER),
        sign_values,
        house_values,
        placements,
    )
    major_relations = _major_relations(geometry, natal_values)
    minor_relations = _accessory_relations(
        geometry.minor_terminals,
        geometry,
        natal_values,
    )
    transit_relations = _accessory_relations(
        geometry.transit_terminals,
        geometry,
        natal_values,
    )
    reenforcements = []
    for minor in minor_relations:
        for major in major_relations:
            if minor.target_terminal.terminal_id in {
                item.terminal_id
                for item in (*major.direct_terminals, *major.indirect_terminals)
            }:
                reenforcements.append(reenforce_major_progressed_relation(major, minor))
    reenforcements.sort(key=lambda item: (item.major_relation_id, item.minor_relation_id))
    dated = tuple(dated_aspect_from_major_relation(item) for item in major_relations)
    locations = tuple(
        ProgressedTerminalLocation(
            terminal.terminal_id,
            ASTRODYNE_SIGNS[int(terminal.longitude_deg // 30.0)],
            assign_house(terminal.longitude_deg, _house_figure(geometry)).house,
        )
        for terminal in (*geometry.natal_terminals, *geometry.major_terminals)
    )
    cusp_signs = {
        index + 1: ASTRODYNE_SIGNS[int(cusp // 30.0)]
        for index, cusp in enumerate(geometry.natal_cusps)
    }
    interceptions = {
        entry.house: entry.intercepted_signs
        for entry in natal.aggregate.houses
        if entry.intercepted_signs
    }
    practical = practical_progressed_horoscope(
        normal,
        dated,
        locations,
        cusp_signs,
        interceptions,
        _mutual_reception_allocations(major_relations),
    )
    return ChurchOfLightProgressedAstrodynesChart(
        geometry=geometry,
        natal=natal,
        normal=normal,
        major_relations=major_relations,
        minor_relations=minor_relations,
        transit_relations=transit_relations,
        reenforcements=tuple(reenforcements),
        practical=practical,
    )


def _house_figure(geometry: ChurchOfLightProgressionGeometry):
    """Rebuild the immutable natal house figure for public placement helpers."""

    return calculate_houses(
        geometry.time_truth.natal_jd_ut,
        geometry.observer_lat,
        geometry.observer_lon,
        system=geometry.requested_house_system,
        policy=HousePolicy.default() if geometry.house_fallback else HousePolicy.strict(),
    )


__all__ = [
    "ChurchOfLightProgressedAstrodynesChart",
    "ChurchOfLightProgressionGeometry",
    "ChurchOfLightProgressionPolicy",
    "ChurchOfLightProgressionTimeTruth",
    "ChurchOfLightSymbolicDate",
    "DEFAULT_CHURCH_OF_LIGHT_PROGRESSION_POLICY",
    "church_of_light_progressed_astrodynes_chart",
    "church_of_light_progression_geometry",
]

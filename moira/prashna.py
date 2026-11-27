"""Tri-, Chatus- and Pancha-sphuta in B. V. Raman's Prasna Marga edition."""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone as utc_timezone
from fractions import Fraction
from math import nextafter
from typing import Literal

from ._ephemeris_time import _bind_ephemeris_time
from .daily_panchanga import (
    DailyPanchangaPolicy, PanchangaMoment, PanchangaSunriseDefinition,
    _civil_bounds, _finite_number, _moment, _resolve_timezone, _solar_cycle_on, _solar_date, _validate_solar_location,
)
from .julian import jd_from_datetime, utc_to_ut1
from .nodes import mean_node, true_node
from .planets import planet_at
from .sayanadi_dated import _UndefinedLagnaError, _lagna_at_tt
from .sidereal import _ayanamsa_truth_at_tt
from .spk_reader import get_reader, use_reader_override
from .upagrahas import _mandi_defining_jd
from .varga import _normalize_longitude

__all__ = ["PrashnaSphutas", "PrashnaGulikaEvidence", "PrashnaSphutasChart",
           "prashna_sphutas", "prashna_sphutas_for_datetime"]


@dataclass(frozen=True, slots=True)
class PrashnaSphutas:
    """Five sidereal operands and their three reduced sums."""

    lagna: float
    moon: float
    gulika: float
    sun: float
    rahu: float
    tri: float
    chatus: float
    pancha: float
    profile_id: Literal["prasna_marga_raman_1991"] = field(init=False, default="prasna_marga_raman_1991")
    source_reference: str = field(init=False, default="Prasna Marga, Raman part I (1991), V.17–18, pp. 162–163")


@dataclass(frozen=True, slots=True)
class PrashnaGulikaEvidence:
    """The Māndi clock and sidereal ascendant used as Gulika in this edition."""

    sunrise_date: date
    period: Literal["day", "night"]
    arc_start: PanchangaMoment
    arc_end: PanchangaMoment
    defining_moment: PanchangaMoment
    jd_tt: float
    tropical_lagna: float
    sidereal_longitude: float
    ayanamsa_degrees: float
    ayanamsa_path: str
    policy: Literal["raman_mandi_30_ghati_table"] = field(init=False, default="raman_mandi_30_ghati_table")


@dataclass(frozen=True, slots=True)
class PrashnaSphutasChart:
    """One sidereal question chart with its required Gulika and Rahu policies."""

    question: PanchangaMoment
    timezone: str
    latitude: float
    longitude: float
    ayanamsa_system: str
    rahu_mode: Literal["mean", "true"]
    sunrise_definition: PanchangaSunriseDefinition
    reader_binding: Literal["caller_owned_reader", "active_or_default_reader"]
    status: Literal["available", "unavailable"]
    unavailable_reason: str | None = None
    gulika: PrashnaGulikaEvidence | None = None
    result: PrashnaSphutas | None = None
    jd_tt: float | None = None
    ayanamsa_degrees: float | None = None
    ayanamsa_path: str | None = None
    ephemeris_identity: str | None = None
    profile_id: Literal["prasna_marga_raman_1991"] = field(init=False, default="prasna_marga_raman_1991")


def prashna_sphutas(*, lagna: float, moon: float, gulika: float, sun: float, rahu: float) -> PrashnaSphutas:
    """Evaluate the three successive sums from one frame's supplied longitudes."""
    inputs = dict(lagna=lagna, moon=moon, gulika=gulika, sun=sun, rahu=rahu)
    for name, value in inputs.items():
        _finite_number(name, value)
        if not 0 <= value < 360:
            raise ValueError(f"{name} must be a sidereal longitude in [0, 360)")
    lagna_x, moon_x, gulika_x, sun_x, rahu_x = map(Fraction, inputs.values())
    tri = (lagna_x + moon_x + gulika_x) % 360
    chatus = (tri + sun_x) % 360
    pancha = (chatus + rahu_x) % 360
    # Retain the correct side of the wrap when a fraction rounds up to 360.
    sums = tuple(min(float(value), nextafter(360.0, 0.0)) for value in (tri, chatus, pancha))
    return PrashnaSphutas(lagna, moon, gulika, sun, rahu, *sums)


def _question_cycle(local_date, jd_ut1, zone, latitude, longitude, altitude):
    today = _solar_date(local_date, zone, latitude, longitude, altitude)
    if len(today.sunrises) == 1 and jd_ut1 < today.sunrises[0].jd_ut1:
        previous = _solar_date(local_date - timedelta(days=1), zone, latitude, longitude, altitude)
        return previous.local_date, _solar_cycle_on(previous, today)
    following = _solar_date(local_date + timedelta(days=1), zone, latitude, longitude, altitude)
    return local_date, _solar_cycle_on(today, following)


def prashna_sphutas_for_datetime(
    dt: datetime, latitude: float, longitude: float, *, timezone: str,
    rahu_mode: Literal["mean", "true"], ayanamsa_system: str = "Lahiri",
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB,
    reader=None,
) -> PrashnaSphutasChart:
    """Resolve a question chart and the work's Māndi-based Gulika in one frame.

    Ayanamsa and the Rahu model are modern materialization choices. The
    work's weekday table is applied to the sunrise-owned local civil date.
    """
    if rahu_mode not in ("mean", "true"):
        raise ValueError("rahu_mode must be 'mean' or 'true'")
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("dt must be a timezone-aware civil datetime")
    zone = _resolve_timezone(timezone)
    utc = dt.astimezone(utc_timezone.utc)
    roundtrip = utc.astimezone(dt.tzinfo)
    local = utc.astimezone(zone)
    if roundtrip.replace(tzinfo=None) != dt.replace(tzinfo=None) or roundtrip.fold != dt.fold:
        raise ValueError("dt is a nonexistent or inconsistent local civil instant")
    if not 2 <= local.year <= 9998:
        raise ValueError("local date must allow adjacent solar dates")
    _validate_solar_location(latitude, longitude)
    policy = DailyPanchangaPolicy(ayanamsa_system, sunrise_definition)
    system = policy.ayanamsa_system
    _civil_bounds(local.date(), zone)
    jd_ut1 = utc_to_ut1(jd_from_datetime(utc))
    common = dict(
        question=PanchangaMoment(jd_ut1, utc, local), timezone=timezone, latitude=latitude,
        longitude=longitude, ayanamsa_system=system, rahu_mode=rahu_mode,
        sunrise_definition=sunrise_definition,
        reader_binding="active_or_default_reader" if reader is None else "caller_owned_reader",
    )
    if abs(latitude) == 90:
        return PrashnaSphutasChart(**common, status="unavailable", unavailable_reason="lagna_geometry_undefined")

    bound = get_reader() if reader is None else reader
    with use_reader_override(bound):
        sunrise_date, (rise, setting, next_rise, reason) = _question_cycle(
            local.date(), jd_ut1, zone, latitude, longitude, sunrise_definition.altitude_degrees,
        )
        if reason is not None:
            return PrashnaSphutasChart(**common, status="unavailable", unavailable_reason=reason)
        is_day = jd_ut1 < setting.jd_ut1
        arc_start, arc_end = (rise, setting) if is_day else (setting, next_rise)
        mandi_ut1 = _mandi_defining_jd((sunrise_date.weekday() + 1) % 7, is_day,
                                     arc_start.jd_ut1, arc_end.jd_ut1)
        question_epoch = _bind_ephemeris_time(jd_ut1, bound)
        jd_tt = question_epoch.epoch_tt
        mandi_tt = _bind_ephemeris_time(mandi_ut1, bound).epoch_tt
        question_frame = _ayanamsa_truth_at_tt(jd_tt, system, jd_ut=jd_ut1)
        mandi_frame = _ayanamsa_truth_at_tt(mandi_tt, system, jd_ut=mandi_ut1)
        if question_frame.fallback_applied or mandi_frame.fallback_applied:
            return PrashnaSphutasChart(**common, status="unavailable", unavailable_reason="ayanamsa_anchor_unavailable")
        try:
            _, lagna = _lagna_at_tt(jd_ut1, jd_tt, question_frame.ayanamsa_deg, latitude, longitude)
            mandi_tropical, mandi = _lagna_at_tt(mandi_ut1, mandi_tt, mandi_frame.ayanamsa_deg, latitude, longitude)
        except _UndefinedLagnaError:
            return PrashnaSphutasChart(**common, status="unavailable", unavailable_reason="lagna_geometry_undefined")
        offset = question_frame.ayanamsa_deg
        moon = planet_at("Moon", jd_ut1, reader=bound, jd_tt=jd_tt).longitude
        sun = planet_at("Sun", jd_ut1, reader=bound, jd_tt=jd_tt).longitude
        node = (mean_node(jd_ut1, jd_tt=jd_tt) if rahu_mode == "mean"
                else true_node(jd_ut1, reader=bound, jd_tt=jd_tt))
        result = prashna_sphutas(
            lagna=_normalize_longitude(lagna), moon=_normalize_longitude(moon - offset),
            gulika=_normalize_longitude(mandi), sun=_normalize_longitude(sun - offset),
            rahu=_normalize_longitude(node.longitude - offset),
        )
    gulika = PrashnaGulikaEvidence(
        sunrise_date, "day" if is_day else "night", arc_start, arc_end, _moment(mandi_ut1, zone),
        mandi_tt, mandi_tropical, result.gulika, mandi_frame.ayanamsa_deg, mandi_frame.effective_path,
    )
    return PrashnaSphutasChart(
        **common, status="available", gulika=gulika, result=result,
        jd_tt=jd_tt, ayanamsa_degrees=offset, ayanamsa_path=question_frame.effective_path,
        ephemeris_identity=question_epoch.identity.summary_label,
    )

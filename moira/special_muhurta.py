"""Source-selected Godhuli, Vijaya and three Muhurta yoga families.

Timing and combination presence are distinct from activity suitability. See
the VED-007 five-name source packet for inspected editions and disagreements.
The date product also carries the existing canonical Abhijit/Brahma result.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from fractions import Fraction
from functools import lru_cache
import math

from .daily_panchanga import DailyPanchangaPolicy, PanchangaMoment, _moment, _resolve_timezone, _solar_date
from .named_muhurta import (
    NamedMuhurtaDay, NamedMuhurtaPolicy, _fraction, _jd, _number,
    named_muhurta_for_date,
)
from .muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from .planets import planet_at
from .rise_set import _altitude
from .sidereal import NAKSHATRA_NAMES, tropical_to_sidereal
from .spk_reader import MissingKernelError, OutOfRangeError, get_reader, use_reader_override
from ._ephemeris_time import _EphemerisTimeBasisError

__all__ = [
    "SpecialMuhurtaPolicy", "SpecialMuhurtaBoundary", "SpecialMuhurtaWindow",
    "SpecialMuhurtaResult", "SpecialMuhurtaSolarResult", "MuhurtaYogaMatch",
    "MuhurtaYogaSnapshot", "SpecialMuhurtaDay", "special_muhurta_from_solar_times",
    "muhurta_yogas_from_longitudes", "special_muhurta_for_date",
]

_VRINDAVANA = "Vivaha Vrindavana, Sitarama Jha Vasantalakshmi, ch.9 vv.5-6, pp.72-73"
_SADHANA = "Muhurta Sadhana, Samjna; TransLiteral digital witness (print edition unidentified)"
_CHINTAMANI = "Muhurta Chintamani, Avasthi 2004, Shubhashubha vv.27-29, pp.13-14"
_KALAPRAKASIKA = "Kalaprakasika, N.P. Subramania Iyer, AES 1982, ch.XXXV, pp.199-201"

# Monday-first, zero-based Ashwini-first indices. Independently transcribed
# name-based source fixtures verify every entry, not merely sampled dates.
_AMRITA_SIDDHI = ((4,), (0,), (16,), (7,), (26,), (3,), (12,))
_AMIRTHA = (
    (3, 4, 14, 21, 6), (6, 7, 8, 9, 10, 4, 12, 13, 14),
    (5, 6, 7, 8, 9, 12, 13, 14, 15, 21), (0, 6, 7, 9, 14),
    (0, 1, 10, 26), (2, 3, 23, 14), (),
)
_SARVARTHA = (
    (21, 3, 4, 7, 16), (0, 25, 2, 8), (3, 16, 12, 2, 4),
    (26, 16, 0, 6, 7), (26, 16, 0, 6, 21), (21, 3, 14),
    (12, 18, 11, 20, 25, 7, 0),
)
_RAVI = frozenset((4, 6, 9, 10, 13, 20))


@dataclass(frozen=True, slots=True)
class SpecialMuhurtaPolicy:
    """Named readings; solar_policy also governs the included Abhijit/Brahma."""

    amrita_basis: str = "sadhana_amrita_siddhi"
    godhuli_weekday_rule: str = "vrindavana_visibility"
    godhuli_horizon: str = "standard_refraction_34_arcmin"
    ayanamsa_system: str = "Lahiri"
    solar_policy: NamedMuhurtaPolicy = field(default_factory=NamedMuhurtaPolicy)
    godhuli_basis: str = field(init=False, default="vrindavana_half_ghati_each_side_half_set")
    vijaya_basis: str = field(init=False, default="sadhana_pauranika_eleventh_daylight_part")
    ravi_basis: str = field(init=False, default="chintamani_inclusive_sun_moon_nakshatra_count")
    sarvarthasiddhi_basis: str = field(init=False, default="chintamani_weekday_nakshatra")
    weekday_basis: str = field(init=False, default="Monday=0,Sunday=6; requested sunrise date")
    nakshatra_basis: str = field(init=False, default="27 equal sidereal parts; Ashwini=0; true ayanamsa")
    endpoint_convention: str = field(init=False, default="[start,end); root brackets remain uncertain")
    godhuli_semidiameter_arcminutes: float = field(init=False, default=16.0)
    activity_suitability: str = field(init=False, default="not_evaluated")

    def __post_init__(self):
        if self.amrita_basis not in ("sadhana_amrita_siddhi", "kalaprakasika_amirtha"):
            raise ValueError("unsupported Amrita identity")
        if self.godhuli_weekday_rule not in ("vrindavana_visibility", "geometry_only"):
            raise ValueError("unsupported Godhuli weekday rule")
        if self.godhuli_horizon not in ("standard_refraction_34_arcmin", "geometric_disc"):
            raise ValueError("unsupported Godhuli horizon")
        if not isinstance(self.solar_policy, NamedMuhurtaPolicy):
            raise TypeError("solar_policy must be NamedMuhurtaPolicy")
        canonical = DailyPanchangaPolicy(ayanamsa_system=self.ayanamsa_system)
        object.__setattr__(self, "ayanamsa_system", canonical.ayanamsa_system)


def _policy(value):
    if value is None:
        return SpecialMuhurtaPolicy()
    if not isinstance(value, SpecialMuhurtaPolicy):
        raise TypeError("policy must be SpecialMuhurtaPolicy")
    return value


def _weekday(value):
    if type(value) is not int or not 0 <= value <= 6:
        raise ValueError("weekday must be an integer in [0,6], Monday=0")
    return value


@dataclass(frozen=True, slots=True)
class SpecialMuhurtaBoundary:
    kind: str
    jd_ut1: float
    lower_jd_ut1: float
    upper_jd_ut1: float
    moment: PanchangaMoment | None = None

    def __post_init__(self):
        low, jd, high = (_jd(key, getattr(self, key)) for key in
                        ("lower_jd_ut1", "jd_ut1", "upper_jd_ut1"))
        if not low <= jd <= high:
            raise ValueError("boundary must lie within its bracket")
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("boundary kind is required")
        if self.moment is not None and self.moment.jd_ut1 != jd:
            raise ValueError("boundary moment disagrees with UT1")


@dataclass(frozen=True, slots=True)
class SpecialMuhurtaWindow:
    start: SpecialMuhurtaBoundary
    end: SpecialMuhurtaBoundary
    eligibility: str = "not_evaluated"
    evidence: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.start, SpecialMuhurtaBoundary) or not isinstance(self.end, SpecialMuhurtaBoundary):
            raise TypeError("window requires typed boundaries")
        if not self.start.upper_jd_ut1 < self.end.lower_jd_ut1:
            raise ValueError("window must have a resolved positive interior")
        if self.eligibility not in ("not_evaluated", "excluded", "not_excluded_by_selected_rule"):
            raise ValueError("unknown eligibility")

    def contains(self, jd_ut1: float) -> bool | None:
        """Geometric membership; root uncertainty returns None, not False."""
        jd = _jd("query_jd_ut1", jd_ut1)
        if jd < self.start.lower_jd_ut1 or jd >= self.end.upper_jd_ut1:
            return False
        if self.start.upper_jd_ut1 <= jd < self.end.lower_jd_ut1:
            return True
        return None


@dataclass(frozen=True, slots=True)
class SpecialMuhurtaResult:
    name: str
    basis: str
    citations: tuple[str, ...]
    status: str
    unavailable_reasons: tuple[str, ...]
    windows: tuple[SpecialMuhurtaWindow, ...]
    activity_suitability: str = field(init=False, default="not_evaluated")

    def __post_init__(self):
        if self.name not in ("Godhuli", "Vijaya", "Amrita Siddhi", "Amirtha", "Ravi Yoga", "Sarvarthasiddhi"):
            raise ValueError("unknown named result")
        if self.status not in ("available", "partial", "unavailable"):
            raise ValueError("unknown result status")
        if (self.status == "available") == bool(self.unavailable_reasons):
            raise ValueError("availability and reasons disagree")
        if self.status == "unavailable" and self.windows:
            raise ValueError("unavailable result cannot carry windows")
        if not isinstance(self.windows, tuple) or any(not isinstance(w, SpecialMuhurtaWindow) for w in self.windows):
            raise TypeError("windows must be a tuple of typed windows")


def _status(results):
    states = {r.status for r in results}
    return next(iter(states)) if len(states) == 1 else "partial"


@dataclass(frozen=True, slots=True)
class SpecialMuhurtaSolarResult:
    policy: SpecialMuhurtaPolicy
    weekday: int
    anchors: tuple[SpecialMuhurtaBoundary, ...]
    results: tuple[SpecialMuhurtaResult, ...]
    anchor_basis: str

    def __post_init__(self):
        _policy(self.policy)
        _weekday(self.weekday)
        if self.anchor_basis != "caller_supplied_ut1":
            raise ValueError("direct solar anchors require caller ownership")
        if tuple(r.name for r in self.results) != ("Vijaya", "Godhuli"):
            raise ValueError("solar results must contain Vijaya and Godhuli")
        if any(not isinstance(a, SpecialMuhurtaBoundary) for a in self.anchors):
            raise TypeError("anchors must be typed boundaries")

    @property
    def status(self):
        return _status(self.results)


@dataclass(frozen=True, slots=True)
class MuhurtaYogaMatch:
    name: str
    basis: str
    citations: tuple[str, ...]
    present: bool
    evidence: tuple[str, ...]
    activity_suitability: str = field(init=False, default="not_evaluated")

    def __post_init__(self):
        if self.name not in ("Amrita Siddhi", "Amirtha", "Ravi Yoga", "Sarvarthasiddhi") or type(self.present) is not bool:
            raise ValueError("yoga match requires a known name and boolean presence")


@dataclass(frozen=True, slots=True)
class MuhurtaYogaSnapshot:
    policy: SpecialMuhurtaPolicy
    weekday: int
    sun_sidereal_longitude: float
    moon_sidereal_longitude: float
    sun_nakshatra_index: int
    moon_nakshatra_index: int
    sun_nakshatra: str
    moon_nakshatra: str
    inclusive_sun_moon_count: int
    results: tuple[MuhurtaYogaMatch, ...]
    longitude_basis: str = field(init=False, default="caller_supplied_sidereal; no ayanamsa applied")

    def __post_init__(self):
        _policy(self.policy)
        _weekday(self.weekday)
        for value, index, name in ((self.sun_sidereal_longitude, self.sun_nakshatra_index, self.sun_nakshatra),
                                   (self.moon_sidereal_longitude, self.moon_nakshatra_index, self.moon_nakshatra)):
            if not 0 <= _number("sidereal_longitude", value) < 360 or type(index) is not int or index != _index(value):
                raise ValueError("snapshot longitude and nakshatra disagree")
            if name != NAKSHATRA_NAMES[index]:
                raise ValueError("snapshot nakshatra name disagrees")
        if self.inclusive_sun_moon_count != (self.moon_nakshatra_index-self.sun_nakshatra_index) % 27+1:
            raise ValueError("snapshot inclusive count disagrees")
        _check_yoga_order(self.results, self.policy)


@dataclass(frozen=True, slots=True)
class SpecialMuhurtaDay:
    """Five additions plus the canonical pair; yoga cells are not merged.

    Yoga presence inside transition_bands is unresolved. This includes short
    occurrences wholly inside overlapping Sun/Moon root brackets; an empty
    windows tuple does not assert absence inside those bands. Outside them,
    each returned cell has constant Sun/Moon nakshatras and weekday ownership.
    """

    policy: SpecialMuhurtaPolicy
    named: NamedMuhurtaDay
    anchors: tuple[SpecialMuhurtaBoundary, ...]
    results: tuple[SpecialMuhurtaResult, ...]
    transition_bands: tuple[SpecialMuhurtaBoundary, ...]
    yoga_interval_basis: str = field(init=False, default="requested sunrise to next sunrise; constant-star cells; uncertainty bands unresolved")

    def __post_init__(self):
        _policy(self.policy)
        if not isinstance(self.named, NamedMuhurtaDay) or self.named.result.policy != self.policy.solar_policy:
            raise ValueError("date composition must retain the selected canonical solar policy")
        if len(self.results) != 5 or tuple(r.name for r in self.results[:2]) != ("Vijaya", "Godhuli"):
            raise ValueError("date result must contain the five selected additions")
        _check_yoga_order(self.results[2:], self.policy)
        if any(not isinstance(a, SpecialMuhurtaBoundary) for a in (*self.anchors, *self.transition_bands)):
            raise TypeError("date anchors and bands must be typed boundaries")

    @property
    def status(self):
        return _status((*self.results, self.named.result))

    def contains_yoga(self, name: str, jd_ut1: float) -> bool | None:
        """Membership in this day's selected yoga, preserving uncertainty.

        False outside this sunrise day does not assert absence on another day.
        None means missing anchors or a numerical transition/ownership band.
        """
        jd = _jd("query_jd_ut1", jd_ut1)
        row = next((r for r in self.results[2:] if r.name == name), None)
        if row is None:
            raise ValueError("name must identify a yoga in this selected profile")
        if row.status == "unavailable":
            return None
        if any(b.lower_jd_ut1 <= jd < b.upper_jd_ut1 for b in self.transition_bands):
            return None
        values = tuple(w.contains(jd) for w in row.windows)
        return True if True in values else None if None in values else False


def _index(longitude):
    # Compare explicit boundaries rather than rounded division; nextafter
    # on either side of each binary64 boundary retains half-open ownership.
    return sum(longitude >= i * (360.0 / 27) for i in range(1, 27))


def _check_yoga_order(results, policy):
    amrita = "Amirtha" if policy.amrita_basis == "kalaprakasika_amirtha" else "Amrita Siddhi"
    if tuple(r.name for r in results) != (amrita, "Ravi Yoga", "Sarvarthasiddhi"):
        raise ValueError("yoga identities disagree with the selected policy")


def muhurta_yogas_from_longitudes(sun_sidereal_longitude: float, moon_sidereal_longitude: float,
                                  *, weekday: int, policy: SpecialMuhurtaPolicy | None = None) -> MuhurtaYogaSnapshot:
    """Three source-selected combinations at caller-supplied longitudes.

    Inputs must already be sidereal in [0,360); no normalization, clock, reader
    or ayanamsa conversion is performed. The caller owns the sunrise weekday.
    """
    active, weekday = _policy(policy), _weekday(weekday)
    sun, moon = (_number("sidereal_longitude", x) for x in (sun_sidereal_longitude, moon_sidereal_longitude))
    if not 0 <= sun < 360 or not 0 <= moon < 360:
        raise ValueError("sidereal longitudes must be in [0,360)")
    s, m = _index(sun), _index(moon)
    count = (m - s) % 27 + 1
    alternate = active.amrita_basis == "kalaprakasika_amirtha"
    table = _AMIRTHA if alternate else _AMRITA_SIDDHI
    evidence = (f"weekday_monday_zero={weekday}", f"moon_nakshatra_ashwini_zero={m}")
    matches = (
        MuhurtaYogaMatch("Amirtha" if alternate else "Amrita Siddhi", active.amrita_basis,
            (_KALAPRAKASIKA if alternate else _SADHANA + ", vv.78-79",), m in table[weekday], evidence),
        MuhurtaYogaMatch("Ravi Yoga", active.ravi_basis, (_CHINTAMANI,), count in _RAVI,
            (f"sun_nakshatra_ashwini_zero={s}", f"moon_nakshatra_ashwini_zero={m}", f"inclusive_count={count}")),
        MuhurtaYogaMatch("Sarvarthasiddhi", active.sarvarthasiddhi_basis, (_CHINTAMANI,), m in _SARVARTHA[weekday], evidence),
    )
    return MuhurtaYogaSnapshot(active, weekday, sun, moon, s, m, NAKSHATRA_NAMES[s], NAKSHATRA_NAMES[m], count, matches)


def _point(kind, value):
    if value is None:
        return None
    value = _jd(kind, value)
    return SpecialMuhurtaBoundary(kind, value, value, value)


def _shift(anchor, offset, kind):
    return SpecialMuhurtaBoundary(kind, *(float(Fraction.from_float(x) + offset) for x in
        (anchor.jd_ut1, anchor.lower_jd_ut1, anchor.upper_jd_ut1)))


def _between(a, b, numerator, kind):
    return SpecialMuhurtaBoundary(kind, *(_fraction(x, y, numerator, 15) for x, y in zip(
        (a.jd_ut1, a.lower_jd_ut1, a.upper_jd_ut1), (b.jd_ut1, b.lower_jd_ut1, b.upper_jd_ut1))))


def _solar_results(rise, setting, half_set, full_set, weekday, policy):
    specs = (("Vijaya", policy.vijaya_basis, (_SADHANA + ", vv.62/68-69",)),
             ("Godhuli", policy.godhuli_basis, (_VRINDAVANA,)))
    results = []
    for name, basis, citations in specs:
        reasons, windows = (), ()
        if name == "Vijaya":
            if rise is None or setting is None:
                reasons = tuple(key + "_unavailable" for key, a in (("sunrise", rise), ("sunset", setting)) if a is None)
            elif rise.upper_jd_ut1 >= setting.lower_jd_ut1:
                reasons = ("daylight_anchors_unresolved",)
            else:
                a, b = _between(rise, setting, 10, "vijaya_start"), _between(rise, setting, 11, "vijaya_end")
                if a.upper_jd_ut1 < b.lower_jd_ut1:
                    windows = (SpecialMuhurtaWindow(a, b, evidence=("daylight_parts_10_to_11_of_15",)),)
                else:
                    reasons = ("interval_endpoints_unresolved",)
        elif half_set is None:
            reasons = ("half_set_unavailable",)
        else:
            a, b = _shift(half_set, -Fraction(1, 120), "godhuli_start"), _shift(half_set, Fraction(1, 120), "godhuli_end")
            if a.upper_jd_ut1 >= b.lower_jd_ut1:
                reasons = ("interval_endpoints_unresolved",)
            elif policy.godhuli_weekday_rule == "geometry_only":
                windows = (SpecialMuhurtaWindow(a, b),)
            elif weekday not in (3, 5):
                windows = (SpecialMuhurtaWindow(a, b, "not_excluded_by_selected_rule"),)
            elif full_set is None:
                windows = (SpecialMuhurtaWindow(a, b),)
                reasons = ("upper_limb_sunset_unavailable_for_weekday_rule",)
            else:
                # Disc visibility, not merely the half-set midpoint, owns
                # v.5's Thursday/Saturday partition. Keep excluded geometry.
                before = "excluded" if weekday == 3 else "not_excluded_by_selected_rule"
                after = "not_excluded_by_selected_rule" if weekday == 3 else "excluded"
                if full_set.upper_jd_ut1 <= a.lower_jd_ut1:
                    windows = (SpecialMuhurtaWindow(a, b, after),)
                elif full_set.lower_jd_ut1 >= b.upper_jd_ut1:
                    windows = (SpecialMuhurtaWindow(a, b, before),)
                elif a.upper_jd_ut1 < full_set.lower_jd_ut1 and full_set.upper_jd_ut1 < b.lower_jd_ut1:
                    windows = (SpecialMuhurtaWindow(a, full_set, before), SpecialMuhurtaWindow(full_set, b, after))
                else:
                    windows = (SpecialMuhurtaWindow(a, b),)
                    reasons = ("weekday_partition_overlaps_endpoint_uncertainty",)
        status = "available" if not reasons else "partial" if windows else "unavailable"
        results.append(SpecialMuhurtaResult(name, basis, citations, status, reasons, windows))
    return tuple(results)


def special_muhurta_from_solar_times(*, weekday: int, sunrise_jd_ut1: float | None = None,
        sunset_jd_ut1: float | None = None, half_set_jd_ut1: float | None = None,
        upper_limb_sunset_jd_ut1: float | None = None,
        policy: SpecialMuhurtaPolicy | None = None) -> SpecialMuhurtaSolarResult:
    """Vijaya/Godhuli from supplied, already-resolved UT1 solar anchors.

    Half-set means the centre on the apparent/geometric horizon selected by
    policy. Upper-limb sunset is separate and must not precede half-set.
    Astronomical identity of supplied anchors remains caller-owned.
    """
    active, weekday = _policy(policy), _weekday(weekday)
    rise, setting, half, full = (_point(k, v) for k, v in (
        ("sunrise", sunrise_jd_ut1), ("sunset", sunset_jd_ut1),
        ("half_set", half_set_jd_ut1), ("upper_limb_sunset", upper_limb_sunset_jd_ut1)))
    if rise is not None and any(x is not None and x.jd_ut1 <= rise.jd_ut1 for x in (setting, half, full)):
        raise ValueError("evening anchors must follow sunrise")
    if half is not None and full is not None and full.jd_ut1 <= half.jd_ut1:
        raise ValueError("upper-limb sunset must follow half-set")
    return SpecialMuhurtaSolarResult(active, weekday, tuple(x for x in (rise, setting, half, full) if x is not None),
        _solar_results(rise, setting, half, full, weekday, active), "caller_supplied_ut1")


def _convert(anchor, kind=None):
    if anchor is None:
        return None
    return SpecialMuhurtaBoundary(kind or anchor.kind, anchor.jd_ut1, anchor.lower_jd_ut1, anchor.upper_jd_ut1, anchor.moment)


def _solar_root(event, kind, altitude, lat, lon, zone, tolerance):
    direction = 1 if kind == "next_sunrise" else -1
    def signal(jd):
        return direction * (_altitude(jd, lat, lon, "Sun") - altitude)
    for seconds in (1, 2, 4, 8, 16, 32, 60):
        low, high = event.jd_ut1 - seconds/86400, event.jd_ut1 + seconds/86400
        left, right = signal(low), signal(high)
        if math.isfinite(left) and math.isfinite(right) and left <= 0 <= right:
            break
    else:
        return None
    while (high - low) * 86400 > tolerance:
        mid = (low + high) / 2
        value = signal(mid)
        if not math.isfinite(value) or mid in (low, high):
            return None
        if value < 0:
            low = mid
        else:
            high = mid
    jd = (low + high) / 2
    return SpecialMuhurtaBoundary(kind, jd, low, high, _moment(jd, zone))


def _star_roots(body, phases, start, end, tolerance):
    """Bounded forward-phase scan; solve both bodies, never interpolate speed."""
    roots = []
    left, phase = start, phases(start)[body]
    span = 360.0 / 27
    while left < end:
        right = min(left + 1/24, end)
        after = phases(right)[body]
        advance = (after - phase) % 360
        if not 0 < advance < span/2:
            raise RuntimeError("special Muhurta forward phase bound violated")
        remaining = (_index(phase) + 1) * span - phase
        if advance >= remaining:
            low, high = left, right
            while (high-low)*86400 > tolerance:
                mid = (low+high)/2
                if (phases(mid)[body]-phase) % 360 < remaining:
                    low = mid
                else:
                    high = mid
            roots.append(SpecialMuhurtaBoundary(("Sun", "Moon")[body] + "_nakshatra", (low+high)/2, low, high))
        left, phase = right, after
    return roots


def _yoga_cells(start, end, phases, weekday, policy, zone):
    tol = policy.solar_policy.solver_tolerance_seconds
    raw = [start, end]
    for body in (0, 1):
        raw.extend(_star_roots(body, phases, start.lower_jd_ut1, end.upper_jd_ut1, tol))
    # Merge intersecting uncertainty bands, preserving all contributing kinds.
    groups = []
    for boundary in sorted(raw, key=lambda x: x.lower_jd_ut1):
        if groups and boundary.lower_jd_ut1 <= groups[-1].upper_jd_ut1:
            old = groups.pop()
            low, high = old.lower_jd_ut1, max(old.upper_jd_ut1, boundary.upper_jd_ut1)
            groups.append(SpecialMuhurtaBoundary(old.kind + "+" + boundary.kind, (low+high)/2, low, high))
        else:
            groups.append(boundary)
    windows = [[], [], []]
    templates = muhurta_yogas_from_longitudes(*phases((start.jd_ut1+end.jd_ut1)/2), weekday=weekday, policy=policy).results
    for a, b in zip(groups, groups[1:]):
        if not a.upper_jd_ut1 < b.lower_jd_ut1:
            continue
        snapshot = muhurta_yogas_from_longitudes(*phases((a.upper_jd_ut1+b.lower_jd_ut1)/2), weekday=weekday, policy=policy)
        for i, match in enumerate(snapshot.results):
            if match.present:
                windows[i].append(SpecialMuhurtaWindow(a, b, evidence=match.evidence))
    results = tuple(SpecialMuhurtaResult(m.name, m.basis, m.citations, "available", (), tuple(w))
                    for m, w in zip(templates, windows))
    bands = tuple(replace(b, moment=_moment(b.jd_ut1, zone)) for b in groups if b.lower_jd_ut1 < b.upper_jd_ut1)
    return results, bands


def special_muhurta_for_date(local_date: date, latitude: float, longitude: float, *, timezone: str,
        policy: SpecialMuhurtaPolicy | None = None, reader=None) -> SpecialMuhurtaDay:
    """Complete seven-name date product, including selectable Amrita identity.

    Direct geometry and yoga presence never assert universal auspiciousness.
    The caller-owned reader is bound for every solar, position and clock call.
    """
    active = _policy(policy)
    # Existing date admission validates civil dates and inputs before acquiring
    # resources. Its three-date solar witnesses are reused below.
    named = named_muhurta_for_date(local_date, latitude, longitude, timezone=timezone,
                                  policy=active.solar_policy, reader=reader)
    weekday, zone = local_date.weekday(), _resolve_timezone(timezone)
    rise, setting = _convert(named.result.sunrise), _convert(named.result.sunset)
    tolerance = active.solar_policy.solver_tolerance_seconds
    try:
        bound = get_reader() if reader is None else reader
        with use_reader_override(bound):
            following = named.solar_dates[2]
            next_rise = None
            if len(following.sunrises) == 1:
                next_rise = _solar_root(following.sunrises[0], "next_sunrise",
                    active.solar_policy.sunrise_definition.altitude_degrees, latitude, longitude, zone, tolerance)
                if next_rise is not None and not (following.civil_start.jd_ut1 <= next_rise.lower_jd_ut1
                                                  <= next_rise.upper_jd_ut1 < following.civil_end.jd_ut1):
                    next_rise = None
            half = full = None
            if rise is not None:
                refraction = 34/60 if active.godhuli_horizon == "standard_refraction_34_arcmin" else 0.0
                found = []
                for kind, height in (("half_set", -refraction), ("upper_limb_sunset", -refraction-16/60)):
                    events = [event for day in named.solar_dates
                              for event in _solar_date(day.local_date, zone, latitude, longitude, height).sunsets
                              if rise.jd_ut1 < event.jd_ut1 and (next_rise is None or event.jd_ut1 < next_rise.jd_ut1)]
                    # The first descending crossing after this sunrise owns
                    # the evening even when the following sunrise is absent.
                    # Discovery never leaves the existing three civil dates.
                    event = min(events, key=lambda x: x.jd_ut1) if events else None
                    found.append(None if event is None else _solar_root(event, kind, height, latitude, longitude, zone, tolerance))
                half, full = found
            results = _solar_results(rise, setting, half, full, weekday, active)
            reasons = tuple(k + "_unavailable" for k, x in (("sunrise", rise), ("next_sunrise", next_rise)) if x is None)
            if not reasons and (rise.upper_jd_ut1 >= next_rise.lower_jd_ut1 or next_rise.jd_ut1-rise.jd_ut1 > 2):
                reasons = ("sunrise_day_unresolved",)
            bands = ()
            if reasons:
                templates = muhurta_yogas_from_longitudes(0, 0, weekday=weekday, policy=active).results
                yoga = tuple(SpecialMuhurtaResult(m.name, m.basis, m.citations, "unavailable", reasons, ()) for m in templates)
            else:
                @lru_cache(maxsize=4096)
                def phases(jd):
                    return tuple(tropical_to_sidereal(planet_at(body, jd, reader=bound).longitude, jd, active.ayanamsa_system)
                                 for body in ("Sun", "Moon"))
                yoga, bands = _yoga_cells(rise, next_rise, phases, weekday, active, zone)
            def civil(window):
                return replace(window, **{key: replace(getattr(window, key), moment=_moment(getattr(window, key).jd_ut1, zone))
                                          for key in ("start", "end")})
            results = tuple(replace(r, windows=tuple(civil(w) for w in r.windows)) for r in (*results, *yoga))
            anchors = tuple(x for x in (rise, setting, half, full, next_rise) if x is not None)
            return SpecialMuhurtaDay(active, named, anchors, results, bands)
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError("special Muhurta date is outside kernel coverage") from exc
    except (MissingKernelError, _EphemerisTimeBasisError, LookupError, FileNotFoundError) as exc:
        raise MuhurtaResourceError("required special Muhurta resource is unavailable") from exc

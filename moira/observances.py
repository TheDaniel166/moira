"""Source-declared Vedic observances on local sunrise-owned dates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, tzinfo
from functools import cache
from itertools import product
from typing import Literal

from .daily_panchanga import (
    PanchangaMoment,
    PanchangaSunriseDefinition,
    _civil_bounds,
    _finite_number,
    _moment,
    _resolve_timezone,
    _solar_cycle_on,
    _solar_date,
    _validate_solar_location,
)
from .lunar_month import (
    LunarMonthPolicy,
    LunarMonthResult,
    _angular_crossings,
    _regional_label,
    lunar_month_at,
)
from .planets import planet_at
from .rise_set import _altitude
from .spk_reader import get_reader, use_reader_override

ObservanceRuleId = Literal["mahashivaratri_dharmasindhu_later_v1"]
ObservanceStatus = Literal[
    "selected", "not_applicable", "ambiguous", "unavailable",
    "excluded_by_profile", "unsupported_rule",
]
ObservanceCoverage = Literal["none", "partial", "full"]
ObservanceSunriseTithi = Literal[
    "before_caturdashi", "caturdashi", "after_caturdashi", "boundary_ambiguous",
]
ObservanceVowTiming = Literal["selected_morning_after_daily_rites"]
ObservanceReason = Literal[
    "only_covered_night", "full_over_partial", "later_equal_coverage", "later_no_coverage",
    "winner_stable_across_brackets", "boundary_brackets_can_change_date",
    "no_local_caturdashi", "outside_magha", "month_boundary_ambiguous",
    "intercalation_rule_unverified", "civil_date_skipped", "solar_context_unavailable",
    "solar_bracket_unresolved", "night_sequence_unresolved",
    "missing_practitioner_context", "tithi_does_not_span_following_sunrise",
    "parana_boundary_brackets_overlap", "readiness_before_following_sunrise",
    "readiness_outside_following_date",
    "preparations_allow_in_tithi_parana", "insufficient_time_after_daily_rites",
    "darsha_shraddha_applies",
]
_TOLERANCE_SECONDS = 0.1
_HOUR = 1 / 24
_DAY = timedelta(days=1)
_SUNRISE = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
_COVERAGE_RANK = {"none": 0, "partial": 1, "full": 2}
_PARANA_SOURCE = "https://whm.cdsharma.in/dharma-nirnay?g=ds&p=20&t=path"
_VOW_SOURCE = "https://vedapath.app/en/shiva-purana/kotirudra/38"


@dataclass(frozen=True, slots=True)
class ObservanceProfile:
    """Catalogue identity, doctrinal choices and independent admission states."""

    rule_id: ObservanceRuleId
    name: str
    date_admission: Literal["ordinary_month_admitted"]
    fasting_admission: Literal["conditional_ordinary_parana_admitted"]
    amanta_month: str
    ordinary_purnimanta_month: str
    paksha: Literal["Krishna"]
    tithi_number: int
    night_muhurta: int
    equal_coverage_precedence: Literal["later"]
    ayanamsa_system: str
    sunrise_definition: PanchangaSunriseDefinition
    date_source: str
    date_source_url: str
    fasting_source_url: str
    vow_start_rule: ObservanceVowTiming
    vow_source_url: str


_PROFILE = ObservanceProfile(
    "mahashivaratri_dharmasindhu_later_v1", "Mahāśivarātri",
    "ordinary_month_admitted", "conditional_ordinary_parana_admitted", "Magha", "Phalguna",
    "Krishna", 14, 8, "later", "Lahiri", _SUNRISE,
    "Dharmasindhu, Nirnaya Sagara 1888 edition, second Pariccheda, Magha-masa, Shivaratri",
    "https://whm.cdsharma.in/dharma-nirnay?g=ds&p=19&t=path", _PARANA_SOURCE,
    "selected_morning_after_daily_rites", _VOW_SOURCE,
)


@dataclass(frozen=True, slots=True)
class _Bracket:
    """Closed UT1 range containing one event."""

    lower: float
    upper: float

    @property
    def midpoint(self) -> float:
        return self.lower + (self.upper - self.lower) / 2


@dataclass(frozen=True, slots=True)
class ObservanceBoundary:
    """A boundary's UT1 bracket and representative UTC and local instant."""

    lower_jd_ut1: float
    upper_jd_ut1: float
    moment: PanchangaMoment


@dataclass(frozen=True, slots=True)
class ObservanceInterval:
    """A half-open interval with independently retained boundary brackets."""

    start: ObservanceBoundary
    end: ObservanceBoundary


@dataclass(frozen=True, slots=True)
class ObservanceNight:
    """Sunrise-day ownership, solar witnesses and possible Niśītha coverage."""

    local_date: date
    sunrise: ObservanceBoundary | None
    sunset: ObservanceBoundary | None
    next_sunrise: ObservanceBoundary | None
    nisitha: ObservanceInterval | None
    coverage: tuple[ObservanceCoverage, ...]
    solar_issue: str | None = None


@dataclass(frozen=True, slots=True)
class ObservancePairedMaghaEvidence:
    """Two candidate splits for a paired Caturdaśī in the Kshaya calendar."""

    elapsed_time_midpoint: ObservanceBoundary
    elongation_342_crossing: ObservanceBoundary


@dataclass(frozen=True, slots=True)
class ObservanceDateResult:
    """Decision for the requested local date, with a neighboring winner if known."""

    status: ObservanceStatus
    reason: ObservanceReason
    selected_date: date | None = None
    month: LunarMonthResult | None = None
    regional_context: LunarMonthResult | None = None
    tithi: ObservanceInterval | None = None
    nights: tuple[ObservanceNight, ...] = ()
    paired_magha: ObservancePairedMaghaEvidence | None = None


@dataclass(frozen=True, slots=True)
class ObservanceVowResult:
    """Selected morning and physical tithi at its sunrise."""

    status: ObservanceStatus
    local_date: date | None = None
    timing: ObservanceVowTiming | None = None
    sunrise: ObservanceBoundary | None = None
    sunrise_tithi: ObservanceSunriseTithi | None = None


@dataclass(frozen=True, slots=True)
class ObservanceFastingContext:
    """Practitioner-supplied Darśa applicability and readiness after morning rites."""

    darsha_shraddha_applies: bool
    ready_for_parana_jd_ut1: float | None = None

    def __post_init__(self) -> None:
        if type(self.darsha_shraddha_applies) is not bool:
            raise TypeError("darsha_shraddha_applies must be a boolean")
        if self.ready_for_parana_jd_ut1 is not None:
            _finite_number("ready_for_parana_jd_ut1", self.ready_for_parana_jd_ut1)
            if not -10_000_000 <= self.ready_for_parana_jd_ut1 <= 10_000_000:
                raise ValueError("ready_for_parana_jd_ut1 must be within [-10000000,10000000]")


@dataclass(frozen=True, slots=True)
class ObservanceParanaResult:
    """Conditional time directive for breaking the fast and its solar witness."""

    status: ObservanceStatus
    reason: ObservanceReason
    mode: Literal["at_tithi_end", "within_tithi"] | None = None
    following_sunrise: ObservanceBoundary | None = None
    tithi_end: ObservanceBoundary | None = None
    interval: ObservanceInterval | None = None


@dataclass(frozen=True, slots=True)
class ObservanceProvenance:
    """Reader ownership, UT1 convention and numerical policies."""

    reader_binding: Literal["caller_owned_reader", "active_or_default_reader"]
    event_timescale: Literal["UT1"] = "UT1"
    tithi_elongation_degrees: tuple[int, int] = (336, 348)
    angular_scan_step_hours: float = 1.0
    boundary_tolerance_seconds: float = _TOLERANCE_SECONDS
    solar_altitude_degrees: float = _SUNRISE.altitude_degrees


@dataclass(frozen=True, slots=True)
class ObservanceResult:
    """Versioned date decision with vow placement and pāraṇa availability."""

    profile: ObservanceProfile
    local_date: date
    timezone: str
    latitude: float
    longitude: float
    provenance: ObservanceProvenance
    date_result: ObservanceDateResult
    parana: ObservanceParanaResult
    vow: ObservanceVowResult


def observance_catalogue() -> tuple[ObservanceProfile, ...]:
    """Return the finite source-owned catalogue without accessing a kernel."""
    return (_PROFILE,)


def _coverage(
    start: _Bracket, end: _Bracket, left: _Bracket, right: _Bracket,
) -> tuple[ObservanceCoverage, ...]:
    """Return the possible coverage classes for two ordered half-open intervals."""
    possible: list[ObservanceCoverage] = []
    if end.lower <= left.upper or right.lower <= start.upper:
        possible.append("none")
    if (left.lower < start.upper and start.lower < right.upper
            or left.lower < end.upper and end.lower < right.upper):
        possible.append("partial")
    if start.lower <= left.upper and right.lower <= end.upper:
        possible.append("full")
    return tuple(possible)


def _prefer_later(
    earlier: tuple[ObservanceCoverage, ...], later: tuple[ObservanceCoverage, ...],
) -> tuple[int | None, ObservanceReason]:
    """Apply the text's priority to every possible pair of coverage classes."""
    outcomes = set()
    for first, second in product(earlier, later):
        winner = int(_COVERAGE_RANK[first] <= _COVERAGE_RANK[second])
        if first == second:
            reason = "later_no_coverage" if first == "none" else "later_equal_coverage"
        else:
            reason = "only_covered_night" if "none" in (first, second) else "full_over_partial"
        outcomes.add((winner, reason))
    if len(outcomes) == 1:
        return next(iter(outcomes))
    winners = {winner for winner, _ in outcomes}
    if len(winners) == 1:
        return next(iter(winners)), "winner_stable_across_brackets"
    return None, "boundary_brackets_can_change_date"


def _boundary(bracket: _Bracket, zone: tzinfo) -> ObservanceBoundary:
    return ObservanceBoundary(bracket.lower, bracket.upper, _moment(bracket.midpoint, zone))


def _interval(start: _Bracket, end: _Bracket, zone: tzinfo) -> ObservanceInterval:
    return ObservanceInterval(_boundary(start, zone), _boundary(end, zone))


def _elongation(jd: float, reader) -> float:
    sun = planet_at("Sun", jd, reader=reader).longitude
    moon = planet_at("Moon", jd, reader=reader).longitude
    return (moon - sun) % 360.0


def _tithi_near(start: float, end: float, reader) -> tuple[_Bracket, _Bracket] | None:
    """Find the Caturdaśī touching the search span, with pad for complete roots."""
    opening = None
    for angle, low, high in _angular_crossings(
        start - 2, end + 2, lambda jd: _elongation(jd, reader),
        12.0, _TOLERANCE_SECONDS, scan_step_days=_HOUR,
    ):
        if angle == 336:
            opening = _Bracket(low, high)
        elif angle == 348 and opening and opening.lower < end and high > start:
            return opening, _Bracket(low, high)
    return None


def _paired_magha_evidence(
    start: _Bracket, end: _Bracket, zone: tzinfo, reader,
) -> ObservancePairedMaghaEvidence:
    """Retain both numerical interpretations of half a tithi."""
    elapsed = _Bracket(
        start.lower + (end.lower - start.lower) / 2,
        start.upper + (end.upper - start.upper) / 2,
    )
    for angle, low, high in _angular_crossings(
        start.upper, end.lower, lambda jd: _elongation(jd, reader),
        6.0, _TOLERANCE_SECONDS, scan_step_days=_HOUR,
    ):
        if angle == 342.0:
            return ObservancePairedMaghaEvidence(
                _boundary(elapsed, zone), _boundary(_Bracket(low, high), zone),
            )
    raise RuntimeError("paired Māgha Caturdaśī does not contain the expected 342° crossing")


def _month_assessment(jd: float, reader) -> tuple[
    LunarMonthResult, LunarMonthResult | None, tuple[ObservanceStatus, ObservanceReason] | None,
]:
    """Admit ordinary Māgha after checking month identities that a mapping can change."""
    month = lunar_month_at(jd, reader=reader)
    if month.status == "boundary_ambiguous":
        return month, None, ("ambiguous", "month_boundary_ambiguous")
    label = month.label
    regional = None
    if label.name in ("Pausha", "Magha", "Phalguna"):
        context = lunar_month_at(jd, policy=LunarMonthPolicy(naming_profile="dharmasindhu_dual"),
                                 reader=reader)
        if context.regional_lunations or context.status != "available":
            regional = context
            if context.status == "boundary_ambiguous":
                return month, regional, ("ambiguous", "month_boundary_ambiguous")
            if context.status == "unsupported_intercalation":
                return month, regional, ("unsupported_rule", "intercalation_rule_unverified")
            names = {label.name, context.paired_month_name}
            for profile in ("leow_eastern", "leow_northwestern"):
                mapped, _ = _regional_label(profile, context.amanta_lunation, context.regional_lunations)
                names.add(mapped.name)
            if "Magha" in names:
                return month, regional, ("unsupported_rule", "intercalation_rule_unverified")
    if label.name != "Magha":
        return month, regional, ("not_applicable", "outside_magha")
    if label.qualifier != "ordinary":
        return month, regional, ("unsupported_rule", "intercalation_rule_unverified")
    return month, regional, None


def _solar_bracket(
    event: PanchangaMoment, latitude: float, longitude: float, *, rising: bool,
) -> _Bracket | None:
    """Verify a narrow directional bracket on the original geometric altitude signal."""
    half = (_TOLERANCE_SECONDS / 2) / 86400.0
    low, high = event.jd_ut1 - half, event.jd_ut1 + half
    before = _altitude(low, latitude, longitude, "Sun") - _SUNRISE.altitude_degrees
    after = _altitude(high, latitude, longitude, "Sun") - _SUNRISE.altitude_degrees
    left, right = (before, after) if rising else (after, before)
    if left <= 0 <= right and left < right:
        return _Bracket(low, high)
    return None


def _night(
    day: date, zone: tzinfo, solar_on, latitude: float, longitude: float,
    start: _Bracket, end: _Bracket,
) -> ObservanceNight:
    current, following = solar_on(day), solar_on(day + _DAY)
    if current is None or following is None:
        return ObservanceNight(day, None, None, None, None, (), "civil_date_skipped")
    rise, sunset, next_rise, issue = _solar_cycle_on(current, following)
    brackets = tuple(
        _solar_bracket(event, latitude, longitude, rising=rising) if event is not None else None
        for event, rising in ((rise, True), (sunset, False), (next_rise, True))
    )
    solar = tuple(_boundary(bound, zone) if bound is not None else None for bound in brackets)
    if issue:
        return ObservanceNight(day, *solar, None, (), issue)
    if any(bound is None for bound in brackets):
        return ObservanceNight(day, *solar, None, (), "solar_bracket_unresolved")
    rising, setting, following_rise = brackets
    if not rising.upper < setting.lower or not setting.upper < following_rise.lower:
        return ObservanceNight(day, *solar, None, (), "solar_bracket_unresolved")
    # Both weighted sums are increasing in both solar endpoints.
    left, right = (
        _Bracket(
            setting.lower + (following_rise.lower - setting.lower) * fraction,
            setting.upper + (following_rise.upper - setting.upper) * fraction,
        )
        for fraction in (7 / 15, 8 / 15)
    )
    return ObservanceNight(day, *solar, _interval(left, right, zone), _coverage(start, end, left, right))


def _candidate_nights(
    nights: tuple[ObservanceNight, ...], start: _Bracket, end: _Bracket,
) -> tuple[tuple[ObservanceNight, ...], ObservanceReason | None]:
    """Find consecutive possible candidates and fail on unresolved solar context."""
    before = [i for i, n in enumerate(nights)
              if n.nisitha and n.nisitha.end.upper_jd_ut1 <= start.lower]
    after = [i for i, n in enumerate(nights)
             if n.nisitha and end.upper <= n.nisitha.start.lower_jd_ut1]
    window = nights[max(before) if before else 0:min(after) + 1 if after else None]
    if any(n.solar_issue == "solar_bracket_unresolved" for n in window):
        return window, "solar_bracket_unresolved"
    if any(n.solar_issue is not None for n in window) or not before or not after:
        return window, "solar_context_unavailable"
    if any(a.nisitha.end.upper_jd_ut1 >= b.nisitha.start.lower_jd_ut1
           for a, b in zip(window, window[1:])):
        return window, "night_sequence_unresolved"

    overlaps = tuple(n for n in window if n.coverage != ("none",))
    if len(overlaps) > 2 or (len(overlaps) == 2 and overlaps[1].local_date - overlaps[0].local_date != _DAY):
        return window, "night_sequence_unresolved"
    if len(overlaps) == 2:
        return overlaps, None
    if len(overlaps) == 1:
        hit = overlaps[0]
        if "none" in hit.coverage:
            # No-contact alternatives still need the two windows that bracket the tithi.
            if end.lower <= hit.nisitha.start.upper_jd_ut1:
                return window[:2], None
            return window[-2:], None
        # The other night is evidence only when one hit is certain.
        previous_gap = start.midpoint - window[0].nisitha.end.moment.jd_ut1
        following_gap = window[-1].nisitha.start.moment.jd_ut1 - end.midpoint
        return (window[:2] if previous_gap < following_gap else window[-2:]), None
    return window, None


def _evaluate_date(local_date, zone, latitude, longitude, reader, limits) -> ObservanceDateResult:
    tithi = _tithi_near(*limits, reader)
    if tithi is None:
        return ObservanceDateResult("not_applicable", "no_local_caturdashi")
    start, end = tithi
    interval = _interval(start, end, zone)
    month, regional, admission = _month_assessment((start.midpoint + end.midpoint) / 2, reader)
    if admission is not None and admission[0] == "not_applicable":
        return ObservanceDateResult(*admission, month=month, regional_context=regional, tithi=interval)

    @cache
    def solar_on(day: date):
        try:
            _civil_bounds(day, zone)
        except ValueError as exc:
            if str(exc) != "requested date or adjacent date is skipped in timezone":
                raise
            return None
        return _solar_date(day, zone, latitude, longitude, _SUNRISE.altitude_degrees)

    # Solar cycles can straddle midnight, and DST shifts the civil clock.
    # Keep a wider civil envelope than the tithi to witness a night on each side.
    first = interval.start.moment.local.date() - 2 * _DAY
    last = interval.end.moment.local.date() + _DAY
    all_nights = tuple(
        _night(first + offset * _DAY, zone, solar_on, latitude, longitude, start, end)
        for offset in range((last - first).days + 1)
    )
    nights, issue = _candidate_nights(all_nights, start, end)
    evidence = dict(month=month, regional_context=regional, tithi=interval, nights=nights)
    if admission is not None:
        paired = None
        if regional is not None and regional.paired_month_name == "Magha":
            paired = _paired_magha_evidence(start, end, zone, reader)
        return ObservanceDateResult(*admission, paired_magha=paired, **evidence)
    if issue is not None:
        return ObservanceDateResult("unavailable", issue, **evidence)
    winner, reason = _prefer_later(nights[0].coverage, nights[1].coverage)
    if winner is None:
        return ObservanceDateResult("ambiguous", reason, **evidence)
    selected = nights[winner].local_date
    status = "selected" if selected == local_date else "not_applicable"
    return ObservanceDateResult(status, reason, selected_date=selected, **evidence)


def _sunrise_tithi(
    sunrise: ObservanceBoundary, tithi: ObservanceInterval,
) -> ObservanceSunriseTithi:
    """Classify the sunrise against the half-open Caturdaśī brackets."""
    start, end = tithi.start, tithi.end
    if sunrise.upper_jd_ut1 < start.lower_jd_ut1:
        return "before_caturdashi"
    if end.upper_jd_ut1 <= sunrise.lower_jd_ut1:
        return "after_caturdashi"
    if start.upper_jd_ut1 <= sunrise.lower_jd_ut1 and sunrise.upper_jd_ut1 < end.lower_jd_ut1:
        return "caturdashi"
    return "boundary_ambiguous"


def _vow(decision: ObservanceDateResult) -> ObservanceVowResult:
    """Attach the morning-before-vigil directive to the selected Śivarātri day."""
    if decision.status != "selected":
        return ObservanceVowResult(decision.status)
    winner = next(night for night in decision.nights if night.local_date == decision.selected_date)
    return ObservanceVowResult(
        "selected", winner.local_date, _PROFILE.vow_start_rule,
        winner.sunrise, _sunrise_tithi(winner.sunrise, decision.tithi),
    )


def _parana(
    decision: ObservanceDateResult, context: ObservanceFastingContext | None, zone: tzinfo,
) -> ObservanceParanaResult:
    """Resolve the author's conditional rule within the witnessed post-night scope."""
    if decision.status != "selected":
        return ObservanceParanaResult(decision.status, decision.reason)
    winner = next(night for night in decision.nights if night.local_date == decision.selected_date)
    sunrise = winner.next_sunrise
    end = decision.tithi.end
    evidence = dict(following_sunrise=sunrise, tithi_end=end)
    following_tithi = _sunrise_tithi(sunrise, decision.tithi)
    if following_tithi == "boundary_ambiguous":
        return ObservanceParanaResult("ambiguous", "parana_boundary_brackets_overlap", **evidence)
    if following_tithi != "caturdashi":
        return ObservanceParanaResult("unsupported_rule", "tithi_does_not_span_following_sunrise", **evidence)

    if context is None:
        return ObservanceParanaResult("unavailable", "missing_practitioner_context", **evidence)
    if context.darsha_shraddha_applies:
        return ObservanceParanaResult("selected", "darsha_shraddha_applies", "at_tithi_end", **evidence)
    ready = context.ready_for_parana_jd_ut1
    if ready is None:
        return ObservanceParanaResult("unavailable", "missing_practitioner_context", **evidence)
    # Reject unrelated civil dates before translating the readiness into a window.
    if abs(ready - sunrise.moment.jd_ut1) >= 2:
        return ObservanceParanaResult("unavailable", "readiness_outside_following_date", **evidence)
    readiness = _boundary(_Bracket(ready, ready), zone)
    if readiness.moment.local.date() != sunrise.moment.local.date():
        return ObservanceParanaResult("unavailable", "readiness_outside_following_date", **evidence)
    if ready < sunrise.lower_jd_ut1:
        return ObservanceParanaResult("unavailable", "readiness_before_following_sunrise", **evidence)
    if ready < sunrise.upper_jd_ut1 or end.lower_jd_ut1 <= ready < end.upper_jd_ut1:
        return ObservanceParanaResult("ambiguous", "parana_boundary_brackets_overlap", **evidence)
    if end.upper_jd_ut1 <= ready:
        return ObservanceParanaResult("selected", "insufficient_time_after_daily_rites",
                                      "at_tithi_end", **evidence)
    interval = ObservanceInterval(readiness, end)
    return ObservanceParanaResult("selected", "preparations_allow_in_tithi_parana", "within_tithi",
                                  interval=interval, **evidence)


def evaluate_observance(
    rule_id: ObservanceRuleId, local_date: date, latitude: float, longitude: float, *,
    timezone: str, fasting_context: ObservanceFastingContext | None = None, reader=None,
) -> ObservanceResult:
    """Evaluate one named rule on a local Gregorian date with a caller-owned reader.

    An optional practitioner context enables conditional ordinary-month
    pāraṇa in the covered next-morning geometry.
    """
    if rule_id != _PROFILE.rule_id:
        raise ValueError(f"Unknown observance rule {rule_id!r}")
    if type(local_date) is not date:
        raise TypeError("local_date must be a date")
    if not date(1, 1, 10) <= local_date <= date(9999, 12, 22):
        raise ValueError("local_date must allow the observance solver's adjacent dates")
    if fasting_context is not None and not isinstance(fasting_context, ObservanceFastingContext):
        raise TypeError("fasting_context must be ObservanceFastingContext")
    _validate_solar_location(latitude, longitude)
    zone = _resolve_timezone(timezone)
    provenance = ObservanceProvenance(
        "caller_owned_reader" if reader is not None else "active_or_default_reader",
    )
    try:
        _civil_bounds(local_date, zone)
        lower, _ = _civil_bounds(local_date - _DAY, zone)
        _, upper = _civil_bounds(local_date + _DAY, zone)
    except ValueError as exc:
        if str(exc) != "requested date or adjacent date is skipped in timezone":
            raise
        result = ObservanceDateResult("unavailable", "civil_date_skipped")
    else:
        if reader is None:
            reader = get_reader()
        with use_reader_override(reader):
            result = _evaluate_date(local_date, zone, latitude, longitude, reader, (lower, upper))
    parana = _parana(result, fasting_context, zone)
    return ObservanceResult(
        _PROFILE, local_date, timezone, latitude, longitude, provenance, result, parana, _vow(result),
    )


__all__ = [
    "ObservanceProfile", "ObservanceBoundary", "ObservanceInterval", "ObservanceNight",
    "ObservancePairedMaghaEvidence", "ObservanceVowResult",
    "ObservanceDateResult", "ObservanceFastingContext", "ObservanceParanaResult", "ObservanceProvenance",
    "ObservanceResult", "observance_catalogue", "evaluate_observance",
]

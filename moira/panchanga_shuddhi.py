"""VED-008 source-selected Panchanga restrictions, without score migration.

Authority, variants and derived clocks are recorded in the owning standard.
All direct astronomical inputs are caller-owned. Dated composition lives in
_panchanga_shuddhi_day; no universal electional verdict is inferred here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction
import math

from .daily_panchanga import DailyPanchangaPolicy, PanchangaSunriseDefinition
from .muhurta import tara_bala
from .panchanga import KARANA_NAMES, YOGA_NAMES, _karana_name

__all__ = [
    "PanchangaShuddhiPolicy", "ShuddhiBoundary", "ShuddhiInterval",
    "ShuddhiFinding", "ShuddhiInputs", "ShuddhiValues",
    "PanchangaShuddhiAssessment", "ShuddhiCatalogueEntry", "ShuddhiCatalogue",
    "panchanga_shuddhi_catalogue", "panchanga_shuddhi_from_longitudes",
    "panchaka_rahita", "PanchakaRahita", "panchanga_shuddhi_for_date",
    "ShuddhiCell", "PanchangaShuddhiDay",
]

MC_TARA = "mc_gochara_13_quarters.v1"
PS_TARA = "ps_sastri_scientific_273_navaka.v1"
PANCHAKA = "mypanchang_2025_panchaka_30_tithi.v1"
YOGA = "mc_34_35_fixed_ghati_temporal_half.v1"
KARANA = "bs_1946_100_karana_activity.v1"
BHADRA = "mc_43_45_bhadra_components.v1"
BHADRA_CLOCK = "mc_44_tithi_eighths_normalized.v1"
_MC = "Muhurta Chintamani, Avasthi 2004, Shubhashubha 34-35/43-45, pp.16-17/20-21"
_MC_TARA = "Muhurta Chintamani, Avasthi 2004, Gochara 13, p.71; Sanskrit quarter reading"
_PS = "P.S. Sastri, Text Book of Scientific Hindu Astrology, p.273; scan e82c593677"
_BS = "Brihat Samhita, V.Subrahmanya Sastri/M.R.Bhat 1946, 100.1-5, pp.748-750"
_MP = "myPanchang/Hindu Council of Australia, Darwin 2025, PDF p.2; Kalaprakasika AES1982 pp.151-152"
_LABELS = {1: "mrityu", 2: "agni", 4: "raja", 6: "chora", 8: "roga"}
_GHATIS = {0: 3, 5: 6, 8: 5, 9: 6, 12: 9, 14: 3}
_BHADRA_ROWS = {3: (5, 8), 7: (2, 1), 10: (7, 6), 14: (4, 3),
                17: (8, 7), 21: (3, 2), 24: (6, 5), 28: (1, 4)}
_RULES = ("panchaka", "tara_cycle", "nitya_yoga", "karana_auspicious_prohibition",
          "bhadra_presence", "bhadra_earth", "bhadra_day_night_exception",
          "bhadra_mouth", "bhadra_tail")
_STATES = ("clear", "restricted", "detected", "exception_applies", "unavailable",
           "not_applicable", "not_evaluated", "uncertain")
_ACTIVITIES = (
    ("auspicious", "temporary", "lasting", "nourishment"),
    ("religious", "meritorious", "assistance_to_brahmins"),
    ("affection", "friendship"), ("prosperity", "shelter", "household"),
    ("cultivation", "sowing", "shelter"), ("lasting", "commerce"),
    ("historical_hostile_acts",), ("meritorious", "nourishment", "auspicious"),
    ("nourishment", "historical_medicine", "mantra"),
    ("cattle", "brahmins", "ancestors", "royal_affairs"),
    ("lasting", "historical_fierce_acts"),
)


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite real number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _integer(name, value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low},{high}]")
    return value


def _longitude(name, value):
    value = _number(name, value)
    if not 0 <= value < 360:
        raise ValueError(f"{name} must be in [0,360)")
    return value


def _sector(longitude, divisions):
    # Integer-ratio comparison avoids an additional rounded-span division.
    return int(Fraction.from_float(float(longitude)) * divisions // 360)


@dataclass(frozen=True, slots=True)
class PanchangaShuddhiPolicy:
    """Named Shuddhi profiles with sidereal, solar, and boundary conventions."""

    tara_profile: str = MC_TARA
    ayanamsa_system: str = "Lahiri"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: float = 0.1
    panchaka_profile: str = field(init=False, default=PANCHAKA)
    yoga_profile: str = field(init=False, default=YOGA)
    karana_profile: str = field(init=False, default=KARANA)
    bhadra_profile: str = field(init=False, default=BHADRA)
    bhadra_clock: str = field(init=False, default=BHADRA_CLOCK)
    exception_precedence: str = field(init=False, default="independent_claims_no_universal_override")
    weekday_basis: str = field(init=False, default="Sunday=0; local sunrise-date ownership")
    endpoint_convention: str = field(init=False, default="[start,end); nonzero root bands uncertain")

    def __post_init__(self):
        if self.tara_profile not in (MC_TARA, PS_TARA):
            raise ValueError("unsupported Tara profile")
        value = DailyPanchangaPolicy(self.ayanamsa_system, self.sunrise_definition, self.solver_tolerance_seconds)
        object.__setattr__(self, "ayanamsa_system", value.ayanamsa_system)


def _policy(value):
    if value is None:
        return PanchangaShuddhiPolicy()
    if not isinstance(value, PanchangaShuddhiPolicy):
        raise ValueError("policy must be PanchangaShuddhiPolicy")
    return value


@dataclass(frozen=True, slots=True)
class ShuddhiBoundary:
    """A UT1 boundary estimate and the bracket that bounds its uncertainty."""

    kind: str
    jd_ut1: float
    lower_jd_ut1: float
    upper_jd_ut1: float

    def __post_init__(self):
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("boundary needs a kind")
        values = [_number(k, getattr(self, k)) for k in ("lower_jd_ut1", "jd_ut1", "upper_jd_ut1")]
        if not values[0] <= values[1] <= values[2] or values[2] - values[0] > 1/24:
            raise ValueError("boundary bracket must contain the estimate and span at most one hour")


def _point(kind, jd):
    return ShuddhiBoundary(kind, jd, jd, jd)


@dataclass(frozen=True, slots=True)
class ShuddhiInterval:
    """A half-open interval whose endpoints retain their uncertainty brackets."""

    start: ShuddhiBoundary
    end: ShuddhiBoundary

    def __post_init__(self):
        if not isinstance(self.start, ShuddhiBoundary) or not isinstance(self.end, ShuddhiBoundary):
            raise ValueError("interval endpoints must be ShuddhiBoundary")
        if not 0 < self.end.jd_ut1 - self.start.jd_ut1 <= 3:
            raise ValueError("interval must be positive and at most three days")

    def contains(self, jd_ut1):
        jd = _number("jd_ut1", jd_ut1)
        for b in (self.start, self.end):
            if b.lower_jd_ut1 < b.upper_jd_ut1 and b.lower_jd_ut1 <= jd <= b.upper_jd_ut1:
                return None
        return self.start.jd_ut1 <= jd < self.end.jd_ut1


def _affine(interval, fraction, kind):
    f = Fraction(fraction)
    def combine(attr):
        a, b = (Fraction.from_float(float(getattr(x, attr))) for x in (interval.start, interval.end))
        return float((1-f)*a + f*b)
    return ShuddhiBoundary(kind, *(combine(k) for k in ("jd_ut1", "lower_jd_ut1", "upper_jd_ut1")))


def _shift(boundary, seconds, kind):
    offset = Fraction(seconds, 86400)
    return ShuddhiBoundary(kind, *(float(Fraction.from_float(float(getattr(boundary, k))) + offset)
                                  for k in ("jd_ut1", "lower_jd_ut1", "upper_jd_ut1")))


def _extreme(a, b, function, kind):
    return ShuddhiBoundary(kind, *(function(getattr(a, k), getattr(b, k))
                                  for k in ("jd_ut1", "lower_jd_ut1", "upper_jd_ut1")))


def _clip(interval, extent):
    a = _extreme(interval.start, extent.start, max, interval.start.kind)
    b = _extreme(interval.end, extent.end, min, interval.end.kind)
    return ShuddhiInterval(a, b) if a.jd_ut1 < b.jd_ut1 else None


@dataclass(frozen=True, slots=True)
class PanchakaRahita:
    """One-based Panchaka inputs, their total, and the classified remainder."""

    tithi_number: int
    weekday_number: int
    nakshatra_number: int
    lagna_number: int
    total: int
    remainder: int
    category: str
    profile: str = field(init=False, default=PANCHAKA)

    def __post_init__(self):
        for name, top in (("tithi_number", 30), ("weekday_number", 7), ("nakshatra_number", 27), ("lagna_number", 12)):
            _integer(name, getattr(self, name), 1, top)
        total = self.tithi_number + self.weekday_number + self.nakshatra_number + self.lagna_number
        if type(self.total) is not int or self.total != total or type(self.remainder) is not int or self.remainder != total % 9:
            raise ValueError("Panchaka arithmetic disagrees with inputs")
        if self.category != _LABELS.get(total % 9, "rahita"):
            raise ValueError("Panchaka category disagrees with remainder")


def panchaka_rahita(tithi_number, weekday_number, nakshatra_number, lagna_number):
    """One-based source arithmetic: month tithi 1..30; Sunday weekday 1."""
    for name, value, maximum in (("tithi_number", tithi_number, 30), ("weekday_number", weekday_number, 7),
                                  ("nakshatra_number", nakshatra_number, 27), ("lagna_number", lagna_number, 12)):
        _integer(name, value, 1, maximum)
    total = tithi_number + weekday_number + nakshatra_number + lagna_number
    return PanchakaRahita(tithi_number, weekday_number, nakshatra_number, lagna_number,
                         total, total % 9, _LABELS.get(total % 9, "rahita"))


@dataclass(frozen=True, slots=True)
class ShuddhiCatalogueEntry:
    """A named profile or Karana entry with citations and descriptive tags."""

    kind: str
    name: str
    profile: str
    citations: tuple[str, ...]
    tags: tuple[str, ...]

    def __post_init__(self):
        if self.kind not in ("profile", "karana") or not isinstance(self.name, str) or not self.name:
            raise ValueError("catalogue entry requires a known kind and name")
        if self.profile not in (MC_TARA, PS_TARA, PANCHAKA, YOGA, KARANA, BHADRA, BHADRA_CLOCK):
            raise ValueError("unknown catalogue profile")
        for name in ("citations", "tags"):
            values = getattr(self, name)
            if type(values) is not tuple or not values or any(type(v) is not str or not v for v in values):
                raise ValueError("catalogue evidence must be nonempty immutable strings")


@dataclass(frozen=True, slots=True)
class ShuddhiCatalogue:
    """Admitted Shuddhi profiles and Karana entries with explicit exclusions."""

    profiles: tuple[ShuddhiCatalogueEntry, ...]
    karanas: tuple[ShuddhiCatalogueEntry, ...]
    excluded_profiles: tuple[str, ...]

    def __post_init__(self):
        if type(self.profiles) is not tuple or type(self.karanas) is not tuple:
            raise ValueError("catalogues must be immutable tuples")
        if any(not isinstance(x, ShuddhiCatalogueEntry) for x in (*self.profiles, *self.karanas)):
            raise ValueError("catalogue rows must be typed")


def panchanga_shuddhi_catalogue():
    """Finite admitted policies, historical activity tags and explicit omissions."""
    profiles = tuple(ShuddhiCatalogueEntry("profile", p, p, (source,), tags) for p, source, tags in (
        (PANCHAKA, _MP, ("month_tithi_1_to_30", "current_lagna")),
        (MC_TARA, _MC_TARA, ("three_cycles", "angular_quarters_1_4_3", "interpretation_declared")),
        (PS_TARA, _PS, ("three_cycles", "modern_scholarship", "scan_owned")),
        (YOGA, _MC, ("fixed_24_minute_ghati", "derived_temporal_half")),
        (KARANA, _BS, ("activity_evidence_only",)),
        (BHADRA, _MC, ("independent_claims",)),
        (BHADRA_CLOCK, _MC, ("derived_tithi_duration_normalization", "clip_to_actual_karana")),
    ))
    return ShuddhiCatalogue(profiles, tuple(ShuddhiCatalogueEntry("karana", n, KARANA, (_BS,), a)
        for n, a in zip(KARANA_NAMES, _ACTIVITIES)),
        ("mc_hindi_thirds_discrepancy", "raman_initial_ghati_3_vs_7", "sadhana_anatomical_variants",
         "noon_or_strength_overrides", "ritual_remedies", "universal_bhadra_precedence", "complete_activity_elections"))


@dataclass(frozen=True, slots=True)
class ShuddhiInputs:
    """Caller-supplied sidereal positions and optional context for Shuddhi rules."""

    sun_sidereal_longitude: float
    moon_sidereal_longitude: float
    jd_ut1: float | None = None
    weekday: int | None = None
    lagna_sidereal_longitude: float | None = None
    natal_nakshatra_index: int | None = None
    is_daytime: bool | None = None
    yoga_span: ShuddhiInterval | None = None
    tithi_span: ShuddhiInterval | None = None
    karana_span: ShuddhiInterval | None = None

    def __post_init__(self):
        _longitude("sun_sidereal_longitude", self.sun_sidereal_longitude)
        _longitude("moon_sidereal_longitude", self.moon_sidereal_longitude)
        for name in ("sun_sidereal_longitude", "moon_sidereal_longitude", "lagna_sidereal_longitude"):
            if getattr(self, name) is not None:
                _longitude(name, getattr(self, name))
        if self.jd_ut1 is not None:
            _number("jd_ut1", self.jd_ut1)
        for name, maximum in (("weekday", 6), ("natal_nakshatra_index", 26)):
            if getattr(self, name) is not None:
                _integer(name, getattr(self, name), 0, maximum)
        if self.is_daytime is not None and type(self.is_daytime) is not bool:
            raise ValueError("is_daytime must be a boolean or None")
        for name in ("yoga_span", "tithi_span", "karana_span"):
            span = getattr(self, name)
            if span is not None:
                if not isinstance(span, ShuddhiInterval) or self.jd_ut1 is None:
                    raise ValueError("supplied event spans require typed intervals and jd_ut1")
                if span.contains(self.jd_ut1) is False:
                    raise ValueError(f"{name} does not contain jd_ut1")
        if self.tithi_span is not None and self.karana_span is not None:
            t, k = self.tithi_span, self.karana_span
            if k.start.upper_jd_ut1 < t.start.lower_jd_ut1 or k.end.lower_jd_ut1 > t.end.upper_jd_ut1:
                raise ValueError("Karana bounds must lie within the supplied tithi")


@dataclass(frozen=True, slots=True)
class ShuddhiValues:
    """Derived Panchanga, Tara, Panchaka, and Bhadra values for one assessment."""

    tithi_index: int
    nakshatra_index: int
    pada: int
    yoga_index: int
    yoga_name: str
    karana_index: int
    karana_name: str
    moon_sign_index: int
    tara_count: int | None
    tara_number: int | None
    tara_cycle: int | None
    base_tara_polarity: str | None
    panchaka: PanchakaRahita | None
    bhadra_residence: str | None
    karana_activity_tags: tuple[str, ...]

    def __post_init__(self):
        for name, top in (("tithi_index", 29), ("nakshatra_index", 26), ("yoga_index", 26),
                          ("karana_index", 59), ("moon_sign_index", 11)):
            _integer(name, getattr(self, name), 0, top)
        _integer("pada", self.pada, 1, 4)
        if self.karana_name != _karana_name(self.karana_index) or self.yoga_name != YOGA_NAMES[self.yoga_index]:
            raise ValueError("limb names must match indices")
        if self.tithi_index != self.karana_index//2:
            raise ValueError("Karana must belong to tithi")
        if self.karana_activity_tags != _ACTIVITIES[KARANA_NAMES.index(self.karana_name)]:
            raise ValueError("Karana tags must match source table")
        if self.tara_count is not None:
            _integer("tara_count", self.tara_count, 1, 27)
            _integer("tara_number", self.tara_number, 1, 9)
            _integer("tara_cycle", self.tara_cycle, 1, 3)
            if self.tara_number != (self.tara_count-1)%9+1 or self.tara_cycle != (self.tara_count-1)//9+1:
                raise ValueError("Tara number/cycle must agree with inclusive count")
        elif any(x is not None for x in (self.tara_number, self.tara_cycle, self.base_tara_polarity)):
            raise ValueError("Tara identity requires a natal count")


@dataclass(frozen=True, slots=True)
class ShuddhiFinding:
    """One source-profile rule's finding, evidence, and applicable time windows."""

    rule_id: str
    profile: str
    state: str
    detected: bool | None
    citations: tuple[str, ...]
    reasons: tuple[str, ...] = ()
    windows: tuple[ShuddhiInterval, ...] = ()
    unclipped_windows: tuple[ShuddhiInterval, ...] = ()

    def __post_init__(self):
        if self.rule_id not in _RULES or self.state not in _STATES:
            raise ValueError("unknown Shuddhi rule or state")
        profiles = {"panchaka": (PANCHAKA,), "tara_cycle": (MC_TARA, PS_TARA),
                    "nitya_yoga": (YOGA,), "karana_auspicious_prohibition": (KARANA,),
                    "bhadra_mouth": (BHADRA_CLOCK,), "bhadra_tail": (BHADRA_CLOCK,)}
        if self.profile not in profiles.get(self.rule_id, (BHADRA,)):
            raise ValueError("finding profile must belong to its rule")
        for name in ("citations", "reasons", "windows", "unclipped_windows"):
            if type(getattr(self, name)) is not tuple:
                raise ValueError("finding evidence must be immutable tuples")
        if self.detected is not None and type(self.detected) is not bool:
            raise ValueError("detected must be bool or None")
        if (self.detected is None) != (self.state in ("unavailable", "not_evaluated", "uncertain")):
            raise ValueError("unknown detection must agree with the finding state")
        if not self.citations or any(type(x) is not str for x in (*self.citations, *self.reasons)):
            raise ValueError("findings require citations and string reasons")
        if any(not isinstance(x, ShuddhiInterval) for x in (*self.windows, *self.unclipped_windows)):
            raise ValueError("windows must be typed")


@dataclass(frozen=True, slots=True)
class PanchangaShuddhiAssessment:
    """Independent Shuddhi findings with inputs, values, and applied profiles."""

    policy: PanchangaShuddhiPolicy
    inputs: ShuddhiInputs
    values: ShuddhiValues
    findings: tuple[ShuddhiFinding, ...]
    applied_profiles: tuple[str, ...]
    simultaneous_bhadra_claims: bool
    input_basis: str = "caller_supplied_sidereal_and_ut1; no_ayanamsa_applied"
    activity_suitability: str = field(init=False, default="not_evaluated")

    def __post_init__(self):
        if not isinstance(self.policy, PanchangaShuddhiPolicy):
            raise ValueError("assessment policy must be typed")
        if not isinstance(self.inputs, ShuddhiInputs) or not isinstance(self.values, ShuddhiValues):
            raise ValueError("assessment inputs/values must be typed")
        if type(self.findings) is not tuple or any(not isinstance(x, ShuddhiFinding) for x in self.findings):
            raise ValueError("assessment findings must be immutable typed records")
        if tuple(x.rule_id for x in self.findings) != _RULES:
            raise ValueError("assessment must contain the canonical rule order")
        if self.findings[1].profile != self.policy.tara_profile:
            raise ValueError("Tara finding must match the selected profile")
        applied = tuple(dict.fromkeys(x.profile for x in self.findings if x.state not in ("unavailable", "not_evaluated")))
        if self.applied_profiles != applied:
            raise ValueError("applied policies must reflect evaluated findings")
        claims = any(f.state == "exception_applies" for f in self.findings[5:]) and any(f.state == "restricted" for f in self.findings[3:])
        if type(self.simultaneous_bhadra_claims) is not bool or self.simultaneous_bhadra_claims != claims:
            raise ValueError("simultaneous claims must agree with findings")


def _timed_finding(rule, profile, citation, jd, window, *, favorable=False, raw=None):
    contains = window.contains(jd) if window is not None else False
    state = "uncertain" if contains is None else ("exception_applies" if favorable else "restricted") if contains else "clear"
    return ShuddhiFinding(rule, profile, state, contains, (citation,), (),
                          (window,) if window else (), (raw,) if raw else ())


def panchanga_shuddhi_from_longitudes(sun_sidereal_longitude, moon_sidereal_longitude, *,
        jd_ut1=None, weekday=None, lagna_sidereal_longitude=None, natal_nakshatra_index=None,
        is_daytime=None, yoga_span=None, tithi_span=None, karana_span=None, policy=None):
    """Independent source findings; weekday is zero-based Sunday, never JD weekday.

    Supplied full-event intervals must contain the instant; identities and
    astronomical correctness of their endpoints remain caller-owned. Missing
    inputs affect only dependent components, not independent findings.
    """
    active = _policy(policy)
    inputs = ShuddhiInputs(sun_sidereal_longitude, moon_sidereal_longitude, jd_ut1, weekday,
                          lagna_sidereal_longitude, natal_nakshatra_index, is_daytime,
                          yoga_span, tithi_span, karana_span)
    sun, moon = float(sun_sidereal_longitude), float(moon_sidereal_longitude)
    elongation = (moon-sun) % 360
    tithi, nak, pada, yoga, karana, sign = (_sector(elongation, 30), _sector(moon, 27),
        _sector(moon, 108) % 4 + 1, _sector((sun+moon) % 360, 27), _sector(elongation, 60), _sector(moon, 12))
    panchaka = None if weekday is None or lagna_sidereal_longitude is None else panchaka_rahita(
        tithi+1, weekday+1, nak+1, _sector(lagna_sidereal_longitude, 12)+1)
    base = None if natal_nakshatra_index is None else tara_bala(natal_nakshatra_index, nak)
    cycle = None if base is None else (base.count-1)//9+1
    vishti = karana in (7, 14, 21, 28, 35, 42, 49, 56)
    residence = None if not vishti else "earth" if sign in (3, 4, 10, 11) else "heaven" if sign in (0, 1, 2, 7) else "underworld"
    name = _karana_name(karana)
    values = ShuddhiValues(tithi, nak, pada, yoga, YOGA_NAMES[yoga], karana, name, sign,
        None if base is None else base.count, None if base is None else base.tara_number, cycle,
        None if base is None else base.polarity, panchaka, residence, _ACTIVITIES[KARANA_NAMES.index(name)])
    findings = []
    def add(rule, profile, state, detected, citation, *reasons):
        findings.append(ShuddhiFinding(rule, profile, state, detected, (citation,), tuple(reasons)))
    if panchaka is None:
        add("panchaka", PANCHAKA, "unavailable", None, _MP, "weekday_and_current_lagna_required")
    else:
        bad = panchaka.category != "rahita"
        add("panchaka", PANCHAKA, "restricted" if bad else "clear", bad, _MP, panchaka.category)
    source = _MC_TARA if active.tara_profile == MC_TARA else _PS
    if base is None:
        add("tara_cycle", active.tara_profile, "unavailable", None, source, "natal_nakshatra_required")
    elif active.tara_profile == PS_TARA:
        bad = base.count in (1, 7, 12, 16, 23, 25)
        add("tara_cycle", PS_TARA, "restricted" if bad else "clear", bad, source)
    elif base.tara_number == 1:
        add("tara_cycle", MC_TARA, "not_evaluated", None, source, "Janma_purpose_exceptions_not_evaluated", "base_caution_retained")
    else:
        bad_tara = base.tara_number in (3, 5, 7)
        bad = bad_tara and (cycle == 1 or cycle == 2 and pada == {3: 1, 5: 4, 7: 3}[base.tara_number])
        add("tara_cycle", MC_TARA, "restricted" if bad else "exception_applies" if bad_tara else "clear", bad, source)
    if yoga in (16, 26):
        if yoga_span is None:
            add("nitya_yoga", YOGA, "restricted", True, _MC, "whole_occurrence")
        else:
            findings.append(_timed_finding("nitya_yoga", YOGA, _MC, jd_ut1, yoga_span))
    elif yoga not in _GHATIS and yoga != 18:
        add("nitya_yoga", YOGA, "clear", False, _MC)
    elif yoga_span is None:
        add("nitya_yoga", YOGA, "unavailable", None, _MC, "full_yoga_span_and_instant_required")
    else:
        end = _affine(yoga_span, Fraction(1, 2), "Parigha_half") if yoga == 18 else _extreme(
            _shift(yoga_span.start, _GHATIS[yoga]*1440, "yoga_initial_ghatis"), yoga_span.end, min, "yoga_exclusion_end")
        findings.append(_timed_finding("nitya_yoga", YOGA, _MC, jd_ut1, ShuddhiInterval(yoga_span.start, end)))
    add("karana_auspicious_prohibition", KARANA, "restricted" if vishti else "clear", vishti, _BS,
        "activity_tags_are_not_complete_election")
    add("bhadra_presence", BHADRA, "detected" if vishti else "not_applicable", vishti, _MC)
    add("bhadra_earth", BHADRA, ("detected" if residence == "earth" else "exception_applies") if vishti else "not_applicable",
        residence == "earth" if vishti else False, _MC, *( (residence,) if vishti else () ))
    if not vishti:
        add("bhadra_day_night_exception", BHADRA, "not_applicable", False, _MC)
    elif is_daytime is None:
        add("bhadra_day_night_exception", BHADRA, "unavailable", None, _MC, "local_solar_day_night_required")
    else:
        exception = (karana % 2 == 1) == is_daytime
        add("bhadra_day_night_exception", BHADRA, "exception_applies" if exception else "clear", exception, _MC)
    for rule, favorable in (("bhadra_mouth", False), ("bhadra_tail", True)):
        if not vishti:
            add(rule, BHADRA_CLOCK, "not_applicable", False, _MC)
        elif tithi_span is None or karana_span is None:
            add(rule, BHADRA_CLOCK, "unavailable", None, _MC, "full_tithi_and_karana_spans_required")
        else:
            m, q = _BHADRA_ROWS[tithi]
            a, b = (Fraction(q, 8)-Fraction(1, 20), Fraction(q, 8)) if favorable else (
                Fraction(m-1, 8), Fraction(m-1, 8)+Fraction(1, 12))
            raw = ShuddhiInterval(_affine(tithi_span, a, rule+"_start"), _affine(tithi_span, b, rule+"_end"))
            findings.append(_timed_finding(rule, BHADRA_CLOCK, _MC, jd_ut1, _clip(raw, karana_span), favorable=favorable, raw=raw))
    claims = any(f.state == "exception_applies" for f in findings[5:]) and any(f.state == "restricted" for f in findings[3:])
    applied = tuple(dict.fromkeys(f.profile for f in findings if f.state not in ("unavailable", "not_evaluated")))
    return PanchangaShuddhiAssessment(active, inputs, values, tuple(findings), applied, claims)


@dataclass(frozen=True, slots=True)
class ShuddhiCell:
    """A bounded time interval paired with its Shuddhi assessment."""

    interval: ShuddhiInterval
    assessment: PanchangaShuddhiAssessment

    def __post_init__(self):
        if not isinstance(self.interval, ShuddhiInterval) or not isinstance(self.assessment, PanchangaShuddhiAssessment):
            raise ValueError("cell requires typed interval and assessment")
        jd = self.assessment.inputs.jd_ut1
        if jd is None or self.interval.contains(jd) is not True:
            raise ValueError("cell sample must be outside endpoint uncertainty bands")


@dataclass(frozen=True, slots=True)
class PanchangaShuddhiDay:
    """A local sunrise day partitioned into Shuddhi cells and transition bands."""

    local_date: date
    timezone: str
    latitude: float
    longitude: float
    policy: PanchangaShuddhiPolicy
    status: str
    unavailable_reasons: tuple[str, ...]
    sunrise: ShuddhiBoundary | None
    next_sunrise: ShuddhiBoundary | None
    sunset: ShuddhiBoundary | None
    cells: tuple[ShuddhiCell, ...]
    transition_bands: tuple[ShuddhiBoundary, ...]
    kernel_label: str
    reader_binding: str
    activity_suitability: str = field(init=False, default="not_evaluated")

    def __post_init__(self):
        if not isinstance(self.policy, PanchangaShuddhiPolicy) or type(self.local_date) is not date:
            raise ValueError("day requires a typed date and policy")
        if type(self.cells) is not tuple or type(self.transition_bands) is not tuple:
            raise ValueError("day cells/bands must be immutable tuples")
        if any(not isinstance(c, ShuddhiCell) or c.assessment.policy != self.policy for c in self.cells):
            raise ValueError("day cells must share the selected policy")
        if any(not isinstance(b, ShuddhiBoundary) for b in self.transition_bands):
            raise ValueError("day transition bands must be typed")
        if self.status not in ("available", "partial", "unavailable"):
            raise ValueError("invalid day status")
        if bool(self.cells) != (self.status != "unavailable"):
            raise ValueError("day availability must agree with cells")
        if bool(self.unavailable_reasons) != (self.status != "available"):
            raise ValueError("unavailable components require explicit reasons")
        if any(a.interval.end != b.interval.start for a, b in zip(self.cells, self.cells[1:])):
            raise ValueError("day cells must be contiguous at their uncertainty bands")

    def at(self, jd_ut1):
        """Constant rule findings, or None outside the day/in any root band.

        The returned assessment's longitudes are the cell's representative
        sample, not a fresh astronomical calculation at the queried instant.
        """
        jd = _number("jd_ut1", jd_ut1)
        if any(b.lower_jd_ut1 < b.upper_jd_ut1 and b.lower_jd_ut1 <= jd <= b.upper_jd_ut1
               for b in self.transition_bands):
            return None
        return next((c.assessment for c in self.cells if c.interval.contains(jd) is True), None)


def panchanga_shuddhi_for_date(local_date, latitude, longitude, *, timezone,
        natal_nakshatra_index=None, policy=None, reader=None):
    """One sunrise-owned day; exact transition cells outside uncertainty bands."""
    from ._panchanga_shuddhi_day import calculate_day
    return calculate_day(local_date, latitude, longitude, timezone=timezone,
        natal_nakshatra_index=natal_nakshatra_index, policy=policy, reader=reader)

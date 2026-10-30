"""Source-qualified Lilly P3 considerations and lunar qualifications.

Authority: Christian Astrology (1647), pp.113-114,121-124; collated P3
C01-C08/M06/M08. Conditions retain raw triggers, contextual qualifications,
source attribution and unknown inputs. No chart-invalidity switch, strength
score, outcome prediction or automatic new significator is produced.
Existing horary/perfection v1, P2, facade and REST composition stay unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from types import MappingProxyType

from ._strenum import StrEnum
from .horary_reception import (
    LillySnapshotContext, LillyConditionSnapshot, LillyDignityBasis,
    lilly_position_from_longitude,
)
from .horary_moon import LillyP3State, LillyVOCResult, _finite, _text, _strings, _context, _angle
from .triplicity import TriplicityDoctrine, triplicity_assignment_for
from .dignities import DOMICILE

__all__ = [
    "LillyFigureKind", "LillySolarBand", "LillyQualitativeKind", "LillyQualitativeEvidence",
    "LillyConsiderationEvidence", "LillySolarEvidence", "LillyLunarOrientation",
    "LillyVOCQualification", "LillyQuestionBinding", "LillyHourAssertion",
    "LillyHourAgreement", "lilly_early_ascendant", "lilly_late_ascendant",
    "lilly_late_moon", "lilly_via_combusta", "lilly_saturn_considerations",
    "lilly_artist_warning", "lilly_seventh_lord_warning", "lilly_solar_proximity",
    "lilly_first_ruler_combust", "lilly_lunar_orientation", "lilly_voc_qualification",
    "lilly_testimony_balance", "lilly_hour_agreement", "adapt_horary_planetary_hour",
]

_PLANETS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
_SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
_DOMICILE = MappingProxyType({s: p for p in _PLANETS for s in DOMICILE[p]})
_NATURE = MappingProxyType({"Sun": ("hot", "dry"), "Moon": ("cold", "moist"), "Mercury": ("cold", "dry"),
           "Venus": ("cold", "moist"), "Mars": ("hot", "dry"), "Jupiter": ("hot", "moist"), "Saturn": ("cold", "dry")})
_TRIPLICITY = MappingProxyType({s: tuple(triplicity_assignment_for(s, is_day_chart=d,
    doctrine=TriplicityDoctrine.WILLIAM_LILLY_1647).active_ruler for d in (True, False)) for s in _SIGNS})
_PROFILE = "lilly_1647_moon_considerations_v1"
_SOURCE = "Lilly 1647 pp.113-114,121-124; P3 C01-C08/M06/M08"
_RULES = ("C01_early_ascendant", "C02_late_ascendant", "C03_late_moon", "C04_via_combusta",
          "C05_saturn_first", "C05_saturn_seventh", "C05_artist_warning", "C05_seventh_lord",
          "C06_first_ruler_combust", "C08_testimony_balance")


class LillyFigureKind(StrEnum):
    """A posed question and a precisely timed event figure are distinct contexts."""
    QUESTION = "question"
    TIMED_EVENT = "timed_event"


class LillySolarBand(StrEnum):
    """Separate solar thresholds and their deliberately unresolved exact edges."""
    CAZIMI = "cazimi"
    CAZIMI_BOUNDARY = "cazimi_boundary"
    COMBUST = "combust"
    COMBUST_BOUNDARY = "combust_boundary"
    UNDER_BEAMS = "under_beams"
    BEAMS_BOUNDARY = "beams_boundary"
    CLEAR = "clear"


class LillyQualitativeKind(StrEnum):
    """The proposition itself is bound, in addition to subjects and epoch."""
    VERY_YOUNG = "very_young"
    DESCRIPTION_MATCHES = "description_matches"
    AGE_CORRESPONDS = "age_corresponds"
    CERTAIN_EVENT_TIME = "certain_event_time"
    LATE_MOON = "late_moon"
    SATURN_RETROGRADE = "saturn_retrograde"
    SEVENTH_CUSP_AFFLICTED = "seventh_cusp_afflicted"
    SEVENTH_LORD_RETROGRADE = "seventh_lord_retrograde"
    SEVENTH_LORD_IMPEDED = "seventh_lord_impeded"
    SEVENTH_LORD_UNFORTUNATE = "seventh_lord_unfortunate"
    PRINCIPALS_VERY_STRONG = "principals_very_strong"
    BALANCED_TESTIMONIES = "balanced_testimonies"


def _state(value):
    if value is None:
        return LillyP3State.NOT_EVALUABLE
    return LillyP3State.PRESENT if value else LillyP3State.ABSENT


def _boolean(value, name):
    if value is not None and type(value) is not bool:
        raise TypeError(f"{name} must be bool or None")


def _any(states):
    states = tuple(states)
    if LillyP3State.PRESENT in states:
        return LillyP3State.PRESENT
    if LillyP3State.NOT_EVALUABLE in states:
        return LillyP3State.NOT_EVALUABLE
    return LillyP3State.ABSENT


def _all(states):
    states = tuple(states)
    if LillyP3State.ABSENT in states:
        return LillyP3State.ABSENT
    if LillyP3State.NOT_EVALUABLE in states:
        return LillyP3State.NOT_EVALUABLE
    return LillyP3State.PRESENT


@dataclass(frozen=True, slots=True)
class LillyQualitativeEvidence:
    """An attributed assessment, bound to actual subjects and an explicit epoch.

This records a caller's source-qualified proposition. It does not establish
that proposition by comparing a dignity score or arbitrary testimony counts.
"""
    context: LillySnapshotContext
    kind: LillyQualitativeKind
    state: LillyP3State
    subjects: tuple[str, ...]
    source_id: str
    explanation: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self):
        _context(self.context)
        if not isinstance(self.kind, LillyQualitativeKind):
            raise TypeError("a typed qualitative proposition kind is required")
        if not isinstance(self.state, LillyP3State) or self.state is LillyP3State.NOT_APPLICABLE:
            raise ValueError("qualitative evidence is present, absent or unknown")
        _strings(self.subjects, "qualitative subjects")
        _strings(self.evidence_ids, "qualitative evidence IDs")
        if not self.subjects or not self.evidence_ids:
            raise ValueError("qualitative evidence requires subjects and evidence IDs")
        _text(self.source_id, "qualitative source")
        _text(self.explanation, "qualitative explanation")


def _assessment(value, context, subjects, kind):
    if value is None:
        return LillyP3State.NOT_EVALUABLE
    if not isinstance(value, LillyQualitativeEvidence):
        raise TypeError("qualitative inputs require attributed Lilly evidence")
    if value.context != context or value.subjects != subjects or value.kind is not kind:
        raise ValueError("qualitative evidence context/subjects/proposition do not match this rule")
    return value.state


def _snapshot(value, context, body=None):
    if value is None:
        return None
    if not isinstance(value, LillyConditionSnapshot):
        raise TypeError("a typed P2 condition snapshot is required")
    if value.context != context or (body is not None and value.position.body != body):
        raise ValueError("condition snapshot context/body mismatch")
    return value


@dataclass(frozen=True, slots=True)
class LillyConsiderationEvidence:
    """One atomic consideration; qualifications never become global verdicts."""
    rule_id: str
    context: LillySnapshotContext
    trigger: LillyP3State
    qualification: LillyP3State
    state: LillyP3State
    scope: str
    observed: tuple[tuple[str, str | float | bool | None], ...]
    evidence: tuple[LillyQualitativeEvidence, ...] = ()
    attribution: str = "Lilly"
    profile_id: str = field(default=_PROFILE, init=False)
    source_reference: str = field(default=_SOURCE, init=False)

    def __post_init__(self):
        _context(self.context)
        if self.rule_id not in _RULES or any(not isinstance(x, LillyP3State) for x in (self.trigger, self.qualification, self.state)):
            raise ValueError("known P3 rule and typed states required")
        _text(self.scope, "consideration scope")
        _text(self.attribution, "consideration attribution")
        if not isinstance(self.observed, tuple) or not isinstance(self.evidence, tuple):
            raise TypeError("observations/evidence must be immutable tuples")
        for row in self.observed:
            if not isinstance(row, tuple) or len(row) != 2:
                raise TypeError("observations must be immutable name/value pairs")
            _text(row[0], "observation name")
            if row[1] is not None and type(row[1]) not in (str, bool, float, int):
                raise TypeError("observation values must be scalar evidence")
            if type(row[1]) in (int, float):
                _finite(row[1], "observation")
        for evidence in self.evidence:
            if not isinstance(evidence, LillyQualitativeEvidence) or evidence.context != self.context:
                raise ValueError("consideration evidence must match context")


def _consideration(rule, context, trigger, qualification=LillyP3State.NOT_APPLICABLE,
                   *, mode="none", scope="contextual_caution", observed=(), evidence=(), attribution="Lilly"):
    _context(context)
    if mode == "eligibility" and qualification is LillyP3State.ABSENT:
        result = LillyP3State.NOT_APPLICABLE
    elif trigger is LillyP3State.ABSENT:
        result = LillyP3State.ABSENT
    elif trigger is LillyP3State.NOT_APPLICABLE:
        result = LillyP3State.NOT_APPLICABLE
    elif trigger is LillyP3State.NOT_EVALUABLE:
        result = LillyP3State.NOT_EVALUABLE
    elif mode != "none" and qualification is LillyP3State.NOT_EVALUABLE:
        result = LillyP3State.NOT_EVALUABLE
    elif mode == "exception" and qualification is LillyP3State.PRESENT:
        result = LillyP3State.ABSENT
    else:
        result = trigger
    return LillyConsiderationEvidence(rule, context, trigger, qualification, result, scope,
        tuple(observed), tuple(x for x in evidence if x is not None), attribution)


def _degree(value):
    if value is None:
        return None
    value = _finite(value, "degree in sign")
    if not 0 <= value < 30:
        raise ValueError("degree in sign must be in [0,30)")
    return value


def lilly_early_ascendant(degree, *, context: LillySnapshotContext,
                          very_young=None, description_matches=None) -> LillyConsiderationEvidence:
    """C01: early-degree caution with the conjunction of two contextual exceptions."""
    degree = _degree(degree)
    youth = _assessment(very_young, context, ("querent",), LillyQualitativeKind.VERY_YOUNG)
    description = _assessment(description_matches, context, ("querent",), LillyQualitativeKind.DESCRIPTION_MATCHES)
    return _consideration("C01_early_ascendant", context, _state(None if degree is None else degree < 3),
        _all((youth, description)), mode="exception", observed=(("degree_in_sign", degree),),
        evidence=(very_young, description_matches))


def lilly_late_ascendant(degree, *, context: LillySnapshotContext,
                         figure_kind: LillyFigureKind | None,
                         age_corresponds=None, certain_event_time=None) -> LillyConsiderationEvidence:
    """C02: age correspondence OR a known timed-event figure, not merely a timestamp."""
    degree = _degree(degree)
    if figure_kind is not None and not isinstance(figure_kind, LillyFigureKind):
        raise TypeError("figure kind must be explicit LillyFigureKind or None")
    age = _assessment(age_corresponds, context, ("querent",), LillyQualitativeKind.AGE_CORRESPONDS)
    event_time = _assessment(certain_event_time, context, ("figure_event",), LillyQualitativeKind.CERTAIN_EVENT_TIME)
    event = _all((_state(None if figure_kind is None else figure_kind is LillyFigureKind.TIMED_EVENT), event_time))
    return _consideration("C02_late_ascendant", context, _state(None if degree is None else degree >= 27),
        _any((age, event)), mode="exception", observed=(("degree_in_sign", degree),
        ("figure_kind", None if figure_kind is None else figure_kind.value)), evidence=(age_corresponds, certain_event_time))


def lilly_late_moon(moon: LillyConditionSnapshot | None, *, context: LillySnapshotContext,
                    late=None) -> LillyConsiderationEvidence:
    """C03: source-qualified late assessment, without a borrowed degree cutoff."""
    _snapshot(moon, context, "Moon")
    state = _assessment(late, context, ("Moon",), LillyQualitativeKind.LATE_MOON)
    sign = None if moon is None else moon.position.sign
    return _consideration("C03_late_moon", context, state,
        observed=(("sign", sign), ("degree_in_sign", None if moon is None else moon.position.degree),
                  ("source_emphasis_sign", None if sign is None else sign in ("Gemini", "Scorpio", "Capricorn"))), evidence=(late,))


def lilly_via_combusta(moon: LillyConditionSnapshot | None, *, context: LillySnapshotContext) -> LillyConsiderationEvidence:
    """C04: half-open operational interval, retaining the source's qualified attribution."""
    _snapshot(moon, context, "Moon")
    value = None
    if moon is not None:
        sign, degree = moon.position.sign, moon.position.degree
        if sign not in ("Libra", "Scorpio"):
            value = False
        elif degree is not None:
            value = degree >= 15 if sign == "Libra" else degree < 15
    return _consideration("C04_via_combusta", context, _state(value), attribution="as_some_say",
        observed=(("interval_start_deg", 195.), ("interval_end_deg_exclusive", 225.)))


def lilly_saturn_considerations(house: int | None, *, context: LillySnapshotContext,
                                 retrograde=None) -> tuple[LillyConsiderationEvidence, ...]:
    """C05: distinct first/seventh clauses; no imported non-seventh-topic exception."""
    if house is not None and (type(house) is not int or not 1 <= house <= 12):
        raise ValueError("Saturn house must be integer 1..12 or None")
    retro = _assessment(retrograde, context, ("Saturn",), LillyQualitativeKind.SATURN_RETROGRADE)
    return tuple(_consideration(rule, context, _state(None if house is None else house == target),
        scope=scope, observed=(("house", house), ("retrograde_enhancement", retro.value)),
        evidence=(retrograde,), attribution="Arabian_rules_reported_by_Lilly")
        for rule, target, scope in (("C05_saturn_first", 1, "matter_difficulty"),
                                   ("C05_saturn_seventh", 7, "judgement_reliability_or_matter_difficulty")))


def lilly_artist_warning(*, context: LillySnapshotContext, matter_concerns_seventh: bool | None,
                         cusp_afflicted=None, lord_retrograde=None, lord_impeded=None) -> LillyConsiderationEvidence:
    """P.122 artist warning with its explicit topic qualification and unknown vocabulary."""
    _boolean(matter_concerns_seventh, "matter_concerns_seventh")
    states = (_assessment(cusp_afflicted, context, ("seventh_cusp",), LillyQualitativeKind.SEVENTH_CUSP_AFFLICTED),
              _assessment(lord_retrograde, context, ("seventh_lord",), LillyQualitativeKind.SEVENTH_LORD_RETROGRADE),
              _assessment(lord_impeded, context, ("seventh_lord",), LillyQualitativeKind.SEVENTH_LORD_IMPEDED))
    eligibility = _state(None if matter_concerns_seventh is None else not matter_concerns_seventh)
    return _consideration("C05_artist_warning", context, _any(states), eligibility, mode="eligibility",
        scope="judgement_reliability", observed=(("matter_concerns_seventh", matter_concerns_seventh),),
        evidence=(cusp_afflicted, lord_retrograde, lord_impeded))


def lilly_seventh_lord_warning(lord: LillyConditionSnapshot | None, *, context: LillySnapshotContext,
                               unfortunate=None) -> LillyConsiderationEvidence:
    """P.123 unfortunate/fallen/malefic-term alternatives without a point-total substitute."""
    _snapshot(lord, context)
    misfortune = _assessment(unfortunate, context, ("seventh_lord",), LillyQualitativeKind.SEVENTH_LORD_UNFORTUNATE)
    fall, term = LillyP3State.NOT_EVALUABLE, LillyP3State.NOT_EVALUABLE
    if lord is not None:
        fall = _state(lord.fall)
        rulers = next(e.possible_rulers for e in lord.dignities if e.basis is LillyDignityBasis.TERM)
        malefic = {"Mars", "Saturn"}
        term = (LillyP3State.PRESENT if set(rulers) <= malefic else LillyP3State.ABSENT
                if not set(rulers) & malefic else LillyP3State.NOT_EVALUABLE)
    return _consideration("C05_seventh_lord", context, _any((misfortune, fall, term)),
        scope="judgement_reliability", observed=(("fall", fall.value), ("malefic_term", term.value)),
        evidence=(unfortunate,), attribution="Arabian_rules_reported_by_Lilly")


@dataclass(frozen=True, slots=True)
class LillySolarEvidence:
    """Separate distance, sign condition, thresholds and unresolved exact boundaries."""
    body: str
    context: LillySnapshotContext
    sun_longitude_deg: float | None
    planet_longitude_deg: float | None
    distance_arcminutes: float | None = field(init=False)
    same_sign: bool | None = field(init=False)
    roundoff_arcminutes: float | None = field(init=False)
    band: LillySolarBand | None = field(init=False)
    combustion: LillyP3State = field(init=False)
    thresholds_arcminutes: tuple[tuple[str, float], ...] = field(default=(("cazimi",17.),("combustion",510.),("beams",1020.)), init=False)
    profile_id: str = field(default=_PROFILE, init=False)
    source_reference: str = field(default="Lilly 1647 pp.113-114; P3 C06", init=False)

    def __post_init__(self):
        _context(self.context)
        if self.body not in _PLANETS:
            raise ValueError("solar evidence requires a classical body")
        for name in ("sun_longitude_deg", "planet_longitude_deg"):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, _angle(getattr(self, name)))
        a, b = self.sun_longitude_deg, self.planet_longitude_deg
        distance, same, band, roundoff = None, None, None, None
        combustion = LillyP3State.NOT_EVALUABLE
        if self.body == "Sun":
            combustion = LillyP3State.NOT_APPLICABLE
        elif a is not None and b is not None:
            difference = b - a
            reduced = math.remainder(difference, 360.)
            distance = abs(reduced) * 60
            # Preserve a numerical representation envelope at source thresholds;
            # this derives from float arithmetic, not a new angular orb policy.
            roundoff = 2 * (math.ulp(a) + math.ulp(b) + math.ulp(difference) + math.ulp(reduced)) * 60 + math.ulp(distance)
            same = int(a // 30) == int(b // 30)
            band = (LillySolarBand.CAZIMI_BOUNDARY if abs(distance - 17) <= roundoff else LillySolarBand.CAZIMI if distance < 17
                    else LillySolarBand.COMBUST_BOUNDARY if same and abs(distance - 510) <= roundoff else LillySolarBand.COMBUST if same and distance < 510
                    else LillySolarBand.BEAMS_BOUNDARY if abs(distance - 1020) <= roundoff else LillySolarBand.UNDER_BEAMS if distance < 1020
                    else LillySolarBand.CLEAR)
            combustion = (LillyP3State.PRESENT if band is LillySolarBand.COMBUST else LillyP3State.NOT_EVALUABLE
                          if band in (LillySolarBand.CAZIMI_BOUNDARY, LillySolarBand.COMBUST_BOUNDARY) else LillyP3State.ABSENT)
            if not same:
                combustion = LillyP3State.ABSENT
        for name, value in (("distance_arcminutes", distance), ("same_sign", same), ("roundoff_arcminutes", roundoff), ("band", band), ("combustion", combustion)):
            object.__setattr__(self, name, value)


def lilly_solar_proximity(body, sun_longitude_deg, planet_longitude_deg, *, context: LillySnapshotContext) -> LillySolarEvidence:
    """Evaluate a supplied geometry without changing any existing solar-policy default."""
    return LillySolarEvidence(body, context, sun_longitude_deg, planet_longitude_deg)


def lilly_first_ruler_combust(solar: LillySolarEvidence | None, *, context: LillySnapshotContext,
                             first_ruler: str | None) -> LillyConsiderationEvidence:
    """Apply the p.123 first-ruler clause to correctly bound C06 geometry."""
    if first_ruler is not None and first_ruler not in _PLANETS:
        raise ValueError("first ruler must be a classical body or None")
    if solar is not None:
        if not isinstance(solar, LillySolarEvidence) or solar.context != context or solar.body != first_ruler:
            raise ValueError("solar evidence context/body must match the first ruler")
    state = (LillyP3State.NOT_APPLICABLE if first_ruler == "Sun" else LillyP3State.NOT_EVALUABLE
             if solar is None else solar.combustion)
    return _consideration("C06_first_ruler_combust", context, state, scope="querent_condition",
        observed=(("first_ruler", first_ruler), ("solar_band", None if solar is None or solar.band is None else solar.band.value)))


@dataclass(frozen=True, slots=True)
class LillyLunarOrientation:
    """Lunar solar-cycle orientation; geometric labels do not establish visibility."""
    context: LillySnapshotContext
    moon_longitude_deg: float | None
    sun_longitude_deg: float | None
    elongation_deg: float | None = field(init=False)
    state: str = field(init=False)
    visibility_inferred: bool = field(default=False, init=False)
    profile_id: str = field(default=_PROFILE, init=False)
    source_reference: str = field(default="Lilly 1647 p.114; P3 M08", init=False)

    def __post_init__(self):
        _context(self.context)
        for name in ("moon_longitude_deg", "sun_longitude_deg"):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, _angle(getattr(self, name)))
        angle = None if self.moon_longitude_deg is None or self.sun_longitude_deg is None else (self.moon_longitude_deg - self.sun_longitude_deg) % 360
        state = ("not_evaluable" if angle is None else "conjunction_boundary" if angle == 0 else "opposition_boundary"
                 if angle == 180 else "occidental" if angle < 180 else "oriental")
        object.__setattr__(self, "elongation_deg", angle)
        object.__setattr__(self, "state", state)


def lilly_lunar_orientation(moon_longitude_deg, sun_longitude_deg, *, context: LillySnapshotContext) -> LillyLunarOrientation:
    """M08 orientation from two coeval tropical longitudes."""
    return LillyLunarOrientation(context, moon_longitude_deg, sun_longitude_deg)


@dataclass(frozen=True, slots=True)
class LillyVOCQualification:
    """P.122 qualifications retain raw VOC and both independent qualifying facts."""
    voc: LillyVOCResult
    moon: LillyConditionSnapshot | None
    principals: tuple[str, str]
    very_strong: LillyQualitativeEvidence | None = None
    sign_qualification: LillyP3State = field(init=False)
    strength_qualification: LillyP3State = field(init=False)
    state: LillyP3State = field(init=False)
    predicted_outcome: None = field(default=None, init=False)
    profile_id: str = field(default=_PROFILE, init=False)
    source_reference: str = field(default="Lilly 1647 p.122; P3 M06", init=False)

    def __post_init__(self):
        if not isinstance(self.voc, LillyVOCResult):
            raise TypeError("a typed selected VOC result is required")
        context = self.voc.trace.context
        if not isinstance(self.principals, tuple) or len(self.principals) != 2 or any(p not in _PLANETS for p in self.principals):
            raise ValueError("both actual classical principal roles must be specified")
        _snapshot(self.moon, context, "Moon")
        if self.moon is not None and self.voc.trace.moon_longitude_at_query is not None:
            actual = lilly_position_from_longitude("Moon", self.voc.trace.moon_longitude_at_query)
            if self.moon.position.sign != actual.sign or (self.moon.position.degree is not None and self.moon.position.degree != actual.degree):
                raise ValueError("Moon qualification position does not match the trace query")
        sign = _state(None if self.moon is None else self.moon.position.sign in ("Taurus", "Cancer", "Sagittarius", "Pisces"))
        strength = _assessment(self.very_strong, context, tuple(f"principal_{label}:{body}" for label, body in zip(("a", "b"), self.principals)), LillyQualitativeKind.PRINCIPALS_VERY_STRONG)
        state = (LillyP3State.NOT_APPLICABLE if self.voc.state in (LillyP3State.ABSENT, LillyP3State.NOT_APPLICABLE)
                 else LillyP3State.NOT_EVALUABLE if self.voc.state is LillyP3State.NOT_EVALUABLE else _any((sign, strength)))
        for name, value in (("sign_qualification", sign), ("strength_qualification", strength), ("state", state)):
            object.__setattr__(self, name, value)


def lilly_voc_qualification(voc: LillyVOCResult, moon: LillyConditionSnapshot | None, *,
                            principals: tuple[str, str], very_strong=None) -> LillyVOCQualification:
    """M06: qualify the testimony without erasing raw VOC or inventing strength."""
    return LillyVOCQualification(voc, moon, principals, very_strong)


def lilly_testimony_balance(*, context: LillySnapshotContext, balance=None) -> LillyConsiderationEvidence:
    """C08 accepts an attributed qualitative balance, never equality of arbitrary counts."""
    state = _assessment(balance, context, ("fortunate_unfortunate_testimonies",), LillyQualitativeKind.BALANCED_TESTIMONIES)
    return _consideration("C08_testimony_balance", context, state, scope="judgement_deferral", evidence=(balance,))


@dataclass(frozen=True, slots=True)
class LillyQuestionBinding:
    """Explicit question/location identity for a supplied planetary-hour receipt."""
    context: LillySnapshotContext
    question_id: str
    latitude_deg: float | None
    longitude_deg: float | None

    def __post_init__(self):
        _context(self.context)
        _text(self.question_id, "question ID")
        if (self.latitude_deg is None) != (self.longitude_deg is None):
            raise ValueError("both observer coordinates or neither are required")
        for name, limit in (("latitude_deg", 90), ("longitude_deg", 180)):
            if getattr(self, name) is not None:
                value = _finite(getattr(self, name), name)
                if not -limit <= value <= limit:
                    raise ValueError("observer coordinate out of bounds")
                object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class LillyHourAssertion:
    """A documentary hour assertion or adapter-bound existing planetary-hour receipt."""
    binding: LillyQuestionBinding
    ruler: str
    source_id: str
    origin: str = "source_asserted"
    hour_is_day_chart: bool | None = None

    def __post_init__(self):
        if not isinstance(self.binding, LillyQuestionBinding) or self.ruler not in _PLANETS:
            raise ValueError("typed question binding and classical hour ruler required")
        _text(self.source_id, "hour source")
        _boolean(self.hour_is_day_chart, "hour_is_day_chart")
        if (self.hour_is_day_chart is not None and self.binding.context.is_day_chart is not None
                and self.hour_is_day_chart != self.binding.context.is_day_chart):
            raise ValueError("hour receipt sect and snapshot sect disagree")
        if self.origin not in ("source_asserted", "supplied_bound_horary_receipt"):
            raise ValueError("unsupported hour assertion origin")
        if self.origin == "supplied_bound_horary_receipt" and (self.binding.context.jd_ut is None or self.binding.latitude_deg is None or self.hour_is_day_chart is None):
            raise ValueError("bound hour receipt requires an epoch, observer and proven sect")


@dataclass(frozen=True, slots=True)
class LillyHourAgreement:
    """Independent identity, triplicity and nature routes; no chart-invalidity claim."""
    binding: LillyQuestionBinding
    ascendant_sign: str | None
    hour: LillyHourAssertion | None
    identity: LillyP3State = field(init=False)
    triplicity: LillyP3State = field(init=False)
    nature: LillyP3State = field(init=False)
    state: LillyP3State = field(init=False)
    profile_id: str = field(default=_PROFILE, init=False)
    source_reference: str = field(default="Lilly 1647 pp.121-122; P3 C07", init=False)

    def __post_init__(self):
        if not isinstance(self.binding, LillyQuestionBinding):
            raise TypeError("an explicit question binding is required")
        if self.ascendant_sign is not None and self.ascendant_sign not in _SIGNS:
            raise ValueError("recognized rising sign or None required")
        if self.hour is not None and (not isinstance(self.hour, LillyHourAssertion) or self.hour.binding != self.binding):
            raise ValueError("hour question/context/location binding mismatch")
        identity = triplicity = nature = LillyP3State.NOT_EVALUABLE
        if self.hour is not None and self.ascendant_sign is not None:
            lord, hour = _DOMICILE[self.ascendant_sign], self.hour.ruler
            identity, nature = _state(lord == hour), _state(_NATURE[lord] == _NATURE[hour])
            day = self.binding.context.is_day_chart
            if day is None:
                day = self.hour.hour_is_day_chart
            rulers = _TRIPLICITY[self.ascendant_sign]
            choices = set(rulers)
            triplicity = (_state(hour in choices) if day is None and len(choices) == 1 else
                LillyP3State.ABSENT if day is None and hour not in choices else LillyP3State.NOT_EVALUABLE if day is None else
                _state(hour == rulers[0 if day else 1]))
        for name, value in (("identity", identity), ("triplicity", triplicity), ("nature", nature),
                            ("state", _any((identity, triplicity, nature)))):
            object.__setattr__(self, name, value)


def lilly_hour_agreement(ascendant_sign, *, binding: LillyQuestionBinding, hour: LillyHourAssertion | None) -> LillyHourAgreement:
    """C07 agreement evidence at the supplied, explicitly bound question."""
    return LillyHourAgreement(binding, ascendant_sign, hour)


def adapt_horary_planetary_hour(receipt, *, binding: LillyQuestionBinding) -> LillyHourAssertion:
    """Bind the existing validated v1 hour vocabulary without changing its semantics."""
    from .horary import HoraryPlanetaryHourReceipt, HoraryChartSect, _validate_planetary_hour_semantics

    if not isinstance(binding, LillyQuestionBinding) or not isinstance(receipt, HoraryPlanetaryHourReceipt):
        raise TypeError("a typed P3 binding and existing horary hour receipt are required")
    if (receipt.question_id, receipt.jd_ut1, receipt.latitude_deg, receipt.longitude_deg) != (
            binding.question_id, binding.context.jd_ut, binding.latitude_deg, binding.longitude_deg):
        raise ValueError("horary hour receipt must match question, epoch and observer")
    sect = _validate_planetary_hour_semantics(receipt)
    return LillyHourAssertion(binding, receipt.hour_ruler, receipt.source_id, "supplied_bound_horary_receipt", sect is HoraryChartSect.DAY)

"""Time-ordered classical perfection analysis under named source policy.

The neutral layer records exact zodiacal aspects, stations, and sign ingresses.
The admitted classifier is William Lilly's 1647 profile only.  It does not
merge Sahl, Bonatti, or later practice into a generic ``traditional`` mode.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations

from .constants import Body, SIGNS, TRADITIONAL_MOIETY_ORBS, sign_of
from .dignities import DOMICILE, EXALTATION
from .egyptian_bounds import EgyptianBoundsDoctrine, EgyptianBoundsPolicy, egyptian_bound_of
from .longevity import FACE_RULERS
from .planets import planet_at
from .spk_reader import SpkReader, get_reader
from .stations import find_stations
from .triplicity import triplicity_assignment_for

__all__ = [
    "ClassicalPerfectionEventKind",
    "ClassicalPerfectionState",
    "LillyPerfectionKind",
    "ClassicalBodyState",
    "ClassicalPerfectionEvent",
    "LillyPerfectionWitness",
    "LillyPerfectionPolicy",
    "ClassicalPerfectionAnalysis",
    "LILLY_1647_PERFECTION_V1",
    "classify_lilly_perfection_events",
    "lilly_perfection_at",
]


_BODIES = (Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.MARS, Body.JUPITER, Body.SATURN)
_TARGETS = ((0.0, "conjunction"), (60.0, "sextile"), (90.0, "square"),
            (120.0, "trine"), (180.0, "opposition"), (240.0, "trine"),
            (270.0, "square"), (300.0, "sextile"))
_SCAN_STEP = 0.25
_TIME_TOL = 1.0 / 86400.0
_ANGLE_TOL = 1e-7
_AUTHORITY = (
    "William Lilly, Christian Astrology (London, 1647), Book I, printed "
    "pp. 110-113 and 125-126; Wellcome Collection scan b30338724"
)


class ClassicalPerfectionEventKind(StrEnum):
    """Vessel: Registry of classical perfection event kind values."""
    ASPECT_EXACT = "aspect_exact"
    STATION_RETROGRADE = "station_retrograde"
    STATION_DIRECT = "station_direct"
    SIGN_INGRESS = "sign_ingress"


class ClassicalPerfectionState(StrEnum):
    """Vessel: Registry of classical perfection state values."""
    PRESENT = "present"
    ABSENT = "absent"
    INDETERMINATE = "indeterminate"


class LillyPerfectionKind(StrEnum):
    """Vessel: Registry of Lilly perfection kind values."""
    DIRECT = "direct_perfection"
    TRANSLATION = "translation_of_light"
    COLLECTION = "collection_of_light"
    PROHIBITION = "prohibition"
    REFRANATION = "refranation"
    FRUSTRATION = "frustration"


@dataclass(frozen=True, slots=True)
class ClassicalBodyState:
    """Vessel: Structured classical body state data."""
    body: str
    longitude: float
    speed: float
    sign: str

    def __post_init__(self) -> None:
        if self.body not in _BODIES or self.sign not in SIGNS:
            raise ValueError("body state must use a traditional planet and tropical sign")
        if not all(math.isfinite(value) for value in (self.longitude, self.speed)):
            raise ValueError("body-state longitude and speed must be finite")
        if not 0.0 <= self.longitude < 360.0 or sign_of(self.longitude)[0] != self.sign:
            raise ValueError("body-state sign must derive from normalized longitude")


@dataclass(frozen=True, slots=True)
class ClassicalPerfectionEvent:
    """Vessel: Structured classical perfection event data."""
    event_id: str
    jd_ut: float
    kind: ClassicalPerfectionEventKind
    actor: str
    target: str | None = None
    aspect: str | None = None
    directional_angle_deg: float | None = None
    longitude_deg: float | None = None
    sign_before: str | None = None
    sign_after: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id or not math.isfinite(self.jd_ut) or self.actor not in _BODIES:
            raise ValueError("event identity, epoch, and actor must be valid")
        if self.kind is ClassicalPerfectionEventKind.ASPECT_EXACT:
            if self.target not in _BODIES or self.target == self.actor or self.aspect is None:
                raise ValueError("exact aspects require two distinct traditional planets")
        elif self.target is not None or self.aspect is not None:
            raise ValueError("non-aspect events cannot carry an aspect target")

    def involves(self, body: str) -> bool:
        return self.actor == body or self.target == body


@dataclass(frozen=True, slots=True)
class LillyPerfectionWitness:
    """Vessel: Structured Lilly perfection witness data."""
    kind: LillyPerfectionKind
    state: ClassicalPerfectionState
    actors: tuple[str, ...]
    event_ids: tuple[str, ...]
    explanation: str
    source_reference: str
    reception_bases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LillyPerfectionPolicy:
    """Vessel: Structured Lilly perfection policy data."""
    profile_id: str = "lilly_1647_perfection_v1"
    profile_version: str = "1.0.0"
    aspect_scope: str = "tropical_zodiacal_ptolemaic_exact"
    contact_scope: str = "summed_planetary_moieties"
    ingress_policy: str = "prior_ingress_makes_application_indeterminate"
    tie_policy: str = "events_within_one_second_are_indeterminate"
    translation_reception: str = "house_triplicity_or_term"
    collection_reception: str = "any_lilly_essential_dignity"
    bounds_doctrine: str = "egyptian"
    triplicity_doctrine: str = "dorothean_sect_active"
    planetary_moiety_table: str = "lilly_1647_traditional_moieties"
    longitude_product: str = "apparent_geocentric_true_ecliptic_of_date"
    motion_product: str = "astrometric_geocentric_longitude_rate"
    input_timescale: str = "ut1_with_internal_tt_ephemeris_conversion"
    max_span_days: float = 31.0

    def __post_init__(self) -> None:
        fixed = {
            "profile_id": "lilly_1647_perfection_v1",
            "profile_version": "1.0.0",
            "aspect_scope": "tropical_zodiacal_ptolemaic_exact",
            "contact_scope": "summed_planetary_moieties",
            "ingress_policy": "prior_ingress_makes_application_indeterminate",
            "tie_policy": "events_within_one_second_are_indeterminate",
            "translation_reception": "house_triplicity_or_term",
            "collection_reception": "any_lilly_essential_dignity",
            "bounds_doctrine": "egyptian",
            "triplicity_doctrine": "dorothean_sect_active",
            "planetary_moiety_table": "lilly_1647_traditional_moieties",
            "longitude_product": "apparent_geocentric_true_ecliptic_of_date",
            "motion_product": "astrometric_geocentric_longitude_rate",
            "input_timescale": "ut1_with_internal_tt_ephemeris_conversion",
            "max_span_days": 31.0,
        }
        for name, expected in fixed.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} is fixed for the admitted Lilly v1 profile")


LILLY_1647_PERFECTION_V1 = LillyPerfectionPolicy()


@dataclass(frozen=True, slots=True)
class ClassicalPerfectionAnalysis:
    """Vessel: Structured classical perfection analysis data."""
    jd_start: float
    jd_end: float
    significator_a: str
    significator_b: str
    is_day_chart: bool
    profile_id: str
    profile_version: str
    policy: LillyPerfectionPolicy
    initial_states: tuple[ClassicalBodyState, ...]
    events: tuple[ClassicalPerfectionEvent, ...]
    witnesses: tuple[LillyPerfectionWitness, ...]
    present_kinds: tuple[LillyPerfectionKind, ...]
    indeterminate_kinds: tuple[LillyPerfectionKind, ...]
    reader_provenance: str
    authorities: tuple[str, ...] = (_AUTHORITY,)
    complete_electional_judgement: bool = False
    scoring: str = "not_provided"
    advice_language: str = "not_provided"

    def __post_init__(self) -> None:
        if not (math.isfinite(self.jd_start) and math.isfinite(self.jd_end) and self.jd_end > self.jd_start):
            raise ValueError("analysis interval must be finite and increasing")
        if self.significator_a == self.significator_b:
            raise ValueError("significators must be distinct")
        if tuple(sorted(self.events, key=lambda item: (item.jd_ut, item.event_id))) != self.events:
            raise ValueError("events must be deterministically time ordered")
        present = tuple(item.kind for item in self.witnesses if item.state is ClassicalPerfectionState.PRESENT)
        uncertain = tuple(item.kind for item in self.witnesses if item.state is ClassicalPerfectionState.INDETERMINATE)
        if present != self.present_kinds or uncertain != self.indeterminate_kinds:
            raise ValueError("classification summaries must derive from witnesses")
        if self.complete_electional_judgement:
            raise ValueError("perfection analysis is not a complete electional judgement")


def _signal(lon_a: float, lon_b: float, target: float) -> float:
    return ((lon_a - lon_b - target + 180.0) % 360.0) - 180.0


def _moiety(a: str, b: str) -> float:
    return (TRADITIONAL_MOIETY_ORBS[a] + TRADITIONAL_MOIETY_ORBS[b]) / 2.0


def _current_relation(a: ClassicalBodyState, b: ClassicalBodyState):
    best = None
    for angle, name in _TARGETS:
        error = _signal(a.longitude, b.longitude, angle)
        candidate = (abs(error), error, a.speed - b.speed, angle, name)
        if best is None or candidate[0] < best[0]:
            best = candidate
    assert best is not None
    distance, error, rate, angle, name = best
    motion = "exact" if distance <= _ANGLE_TOL else "applying" if error * rate < 0.0 else "separating"
    return name, angle, distance, motion, distance <= _moiety(a.body, b.body)


def _pair(event: ClassicalPerfectionEvent) -> frozenset[str]:
    return frozenset((event.actor, event.target))


def _aspect_events(events, a: str, b: str, directional_angle_deg: float | None = None):
    pair = frozenset((a, b))
    return tuple(
        item for item in events
        if item.kind is ClassicalPerfectionEventKind.ASPECT_EXACT
        and _pair(item) == pair
        and (
            directional_angle_deg is None
            or item.directional_angle_deg is not None
            and math.isclose(item.directional_angle_deg, directional_angle_deg, abs_tol=_ANGLE_TOL)
        )
    )


def _signs_behold(a: ClassicalBodyState, b: ClassicalBodyState) -> bool:
    separation = (SIGNS.index(a.sign) - SIGNS.index(b.sign)) % 12
    return separation in {0, 2, 3, 4, 6, 8, 9, 10}


def _prior_interruptions(events, bodies: tuple[str, ...], deadline: float):
    return tuple(item for item in events if item.jd_ut < deadline - _TIME_TOL and item.actor in bodies
                 and item.kind in (ClassicalPerfectionEventKind.SIGN_INGRESS,
                                   ClassicalPerfectionEventKind.STATION_RETROGRADE,
                                   ClassicalPerfectionEventKind.STATION_DIRECT))


def _reception_bases(receiver: str, guest: ClassicalBodyState, is_day: bool) -> tuple[str, ...]:
    bases: list[str] = []
    if guest.sign in DOMICILE[receiver]:
        bases.append("house")
    if guest.sign in EXALTATION[receiver]:
        bases.append("exaltation")
    if triplicity_assignment_for(guest.sign, is_day_chart=is_day).active_ruler == receiver:
        bases.append("triplicity")
    if egyptian_bound_of(guest.longitude, policy=EgyptianBoundsPolicy(EgyptianBoundsDoctrine.EGYPTIAN)).ruler == receiver:
        bases.append("term")
    if FACE_RULERS[int(guest.longitude // 10.0)] == receiver:
        bases.append("face")
    return tuple(bases)


def _witness(kind, state, actors, event_ids, explanation, bases=()):
    pages = {
        LillyPerfectionKind.DIRECT: "printed pp. 125-126",
        LillyPerfectionKind.TRANSLATION: "printed pp. 111 and 125-126",
        LillyPerfectionKind.COLLECTION: "printed p. 126",
        LillyPerfectionKind.PROHIBITION: "printed pp. 110-111",
        LillyPerfectionKind.REFRANATION: "printed p. 111",
        LillyPerfectionKind.FRUSTRATION: "printed pp. 112-113",
    }
    return LillyPerfectionWitness(kind, state, tuple(actors), tuple(event_ids), explanation,
                                  f"{_AUTHORITY}; {pages[kind]}", tuple(bases))


def classify_lilly_perfection_events(
    jd_start: float,
    jd_end: float,
    significator_a: str,
    significator_b: str,
    *,
    is_day_chart: bool,
    initial_states: tuple[ClassicalBodyState, ...],
    events: tuple[ClassicalPerfectionEvent, ...],
    reader_provenance: str = "caller_supplied_event_trace",
    policy: LillyPerfectionPolicy = LILLY_1647_PERFECTION_V1,
) -> ClassicalPerfectionAnalysis:
    """Classify a complete caller-supplied trace under Lilly's named policy."""

    if policy is not LILLY_1647_PERFECTION_V1 and policy != LILLY_1647_PERFECTION_V1:
        raise ValueError("only the admitted Lilly 1647 v1 policy is supported")
    if (not math.isfinite(jd_start) or not math.isfinite(jd_end) or jd_end <= jd_start
            or jd_end - jd_start > policy.max_span_days):
        raise ValueError("analysis interval must be finite, increasing, and no longer than 31 days")
    if significator_a not in _BODIES or significator_b not in _BODIES or significator_a == significator_b:
        raise ValueError("two distinct traditional significators are required")
    states = {item.body: item for item in initial_states}
    if len(initial_states) != len(_BODIES) or set(states) != set(_BODIES):
        raise ValueError("initial_states must contain each traditional planet exactly once")
    ordered = tuple(sorted(events, key=lambda item: (item.jd_ut, item.event_id)))
    if len({item.event_id for item in ordered}) != len(ordered):
        raise ValueError("event_id values must be unique within one analysis")
    if any(not jd_start <= item.jd_ut <= jd_end for item in ordered):
        raise ValueError("every event must fall within the analysis interval")

    a, b = states[significator_a], states[significator_b]
    relation = _current_relation(a, b)
    pair_events = _aspect_events(ordered, a.body, b.body, relation[1])
    direct_event = pair_events[0] if pair_events else None
    eligible_direct = direct_event is not None and relation[3] in ("applying", "exact") and relation[4]
    deadline = direct_event.jd_ut if direct_event else jd_end
    interruptions = _prior_interruptions(ordered, (a.body, b.body), deadline)
    applying_body = a.body if abs(a.speed) > abs(b.speed) else b.body
    retro = tuple(item for item in interruptions
                  if item.kind is ClassicalPerfectionEventKind.STATION_RETROGRADE
                  and item.actor == applying_body)
    ingress = tuple(item for item in interruptions if item.kind is ClassicalPerfectionEventKind.SIGN_INGRESS)

    third_aspects = tuple(item for item in ordered if item.kind is ClassicalPerfectionEventKind.ASPECT_EXACT
                          and item.jd_ut < deadline - _TIME_TOL
                          and len(_pair(item) & {a.body, b.body}) == 1
                          and (item.actor not in (a.body, b.body) or item.target not in (a.body, b.body)))
    slower = a.body if abs(a.speed) <= abs(b.speed) else b.body
    prohibitions = []
    for third in (states[name] for name in _BODIES if name not in (a.body, b.body)):
        relation_a = _current_relation(third, a)
        relation_b = _current_relation(third, b)
        events_a = _aspect_events(ordered, third.body, a.body, relation_a[1])
        events_b = _aspect_events(ordered, third.body, b.body, relation_b[1])
        before_a = tuple(item for item in events_a if item.jd_ut < deadline - _TIME_TOL)
        before_b = tuple(item for item in events_b if item.jd_ut < deadline - _TIME_TOL)
        if (before_a and before_b
                and abs(third.speed) > abs(a.speed) and abs(third.speed) > abs(b.speed)
                and relation_a[3] == relation_b[3] == "applying"
                and relation_a[4] and relation_b[4]):
            first_a, first_b = before_a[0], before_b[0]
            prohibitions.append((third, first_a, first_b))
    prohibiting_bodies = {third.body for third, _, _ in prohibitions}
    frustrations = []
    for item in third_aspects:
        if not (relation[4] and relation[0] == "conjunction"
                and item.aspect == "conjunction" and item.involves(slower)):
            continue
        third_name = next(name for name in (item.actor, item.target) if name not in (a.body, b.body))
        slower_relation = _current_relation(states[slower], states[third_name])
        if (third_name not in prohibiting_bodies and slower_relation[0] == "conjunction"
                and slower_relation[3] == "applying" and slower_relation[4]
                and item.directional_angle_deg is not None
                and math.isclose(item.directional_angle_deg, slower_relation[1], abs_tol=_ANGLE_TOL)):
            frustrations.append(item)
    tie = bool(direct_event and any(abs(item.jd_ut - direct_event.jd_ut) <= _TIME_TOL for item in third_aspects + interruptions))

    witnesses: list[LillyPerfectionWitness] = []
    if not eligible_direct:
        direct_state = ClassicalPerfectionState.ABSENT
        direct_reason = "The significators have no in-moiety applying exact perfection in the selected interval."
    elif ingress or tie:
        direct_state = ClassicalPerfectionState.INDETERMINATE
        direct_reason = "A prior sign ingress or exact event tie prevents v1 from asserting uninterrupted perfection."
    elif retro or frustrations or prohibitions:
        direct_state = ClassicalPerfectionState.ABSENT
        direct_reason = "A source-defined intervening event occurs before the intended exact aspect."
    else:
        direct_state = ClassicalPerfectionState.PRESENT
        direct_reason = "The in-moiety application reaches exactitude before any admitted interruption."
    witnesses.append(_witness(LillyPerfectionKind.DIRECT, direct_state, (a.body, b.body),
                              (() if direct_event is None else (direct_event.event_id,)), direct_reason))

    witnesses.append(_witness(
        LillyPerfectionKind.REFRANATION,
        ClassicalPerfectionState.PRESENT if eligible_direct and retro else ClassicalPerfectionState.ABSENT,
        (a.body, b.body), tuple(item.event_id for item in retro),
        "An applying significator stations retrograde before exactitude." if retro else
        "No applying significator stations retrograde before the intended perfection.",
    ))
    witnesses.append(_witness(
        LillyPerfectionKind.FRUSTRATION,
        ClassicalPerfectionState.PRESENT if eligible_direct and frustrations else ClassicalPerfectionState.ABSENT,
        (a.body, b.body, *((next(name for name in (frustrations[0].actor, frustrations[0].target)
                                  if name not in (a.body, b.body)),) if frustrations else ())),
        tuple(item.event_id for item in frustrations),
        "A third planet conjoins the slower significator before the intended union." if frustrations else
        "No prior conjunction to the slower significator frustrates the intended union.",
    ))
    witnesses.append(_witness(
        LillyPerfectionKind.PROHIBITION,
        ClassicalPerfectionState.PRESENT if eligible_direct and prohibitions else ClassicalPerfectionState.ABSENT,
        (a.body, b.body, *((prohibitions[0][0].body,) if prohibitions else ())),
        tuple(item.event_id for _, first_a, first_b in prohibitions for item in (first_a, first_b)),
        "One swifter third planet perfects with both significators before their intended perfection." if prohibitions else
        "No swifter third planet perfects successively with both significators first.",
    ))

    translations = []
    for source, destination in ((a, b), (b, a)):
        for translator in (states[name] for name in _BODIES if name not in (a.body, b.body)):
            source_relation = _current_relation(translator, source)
            dest_relation = _current_relation(translator, destination)
            future = _aspect_events(ordered, translator.body, destination.body, dest_relation[1])
            if not future:
                continue
            event = future[0]
            allowed_bases = tuple(base for base in _reception_bases(source.body, translator, is_day_chart)
                                  if base in ("house", "triplicity", "term"))
            translator_interruptions = _prior_interruptions(ordered, (translator.body,), event.jd_ut)
            intervening_contacts = tuple(
                item for item in ordered
                if item.kind is ClassicalPerfectionEventKind.ASPECT_EXACT
                and item.jd_ut < event.jd_ut - _TIME_TOL
                and item.involves(translator.body)
            )
            if (abs(translator.speed) > abs(source.speed) and abs(translator.speed) > abs(destination.speed)
                    and source_relation[3] == "separating" and source_relation[4]
                    and dest_relation[3] == "applying" and dest_relation[4]
                    and allowed_bases and not translator_interruptions and not intervening_contacts):
                translations.append((translator, source, destination, event, allowed_bases))
    if translations:
        translator, source, destination, event, bases = translations[0]
        witnesses.append(_witness(LillyPerfectionKind.TRANSLATION, ClassicalPerfectionState.PRESENT,
                                  (translator.body, source.body, destination.body), (event.event_id,),
                                  "A lighter planet separates from a receiving significator and applies next to the other.", bases))
    else:
        witnesses.append(_witness(LillyPerfectionKind.TRANSLATION, ClassicalPerfectionState.ABSENT,
                                  (a.body, b.body), (), "No complete received translation occurs in the supplied trace."))

    collections = []
    pair_beholds = _signs_behold(a, b)
    for collector in (states[name] for name in _BODIES if name not in (a.body, b.body)):
        rel_a, rel_b = _current_relation(a, collector), _current_relation(b, collector)
        event_a = _aspect_events(ordered, a.body, collector.body, rel_a[1])
        event_b = _aspect_events(ordered, b.body, collector.body, rel_b[1])
        if not event_a or not event_b:
            continue
        bases_a = _reception_bases(a.body, collector, is_day_chart)
        bases_b = _reception_bases(b.body, collector, is_day_chart)
        last_deadline = max(event_a[0].jd_ut, event_b[0].jd_ut)
        interrupted = _prior_interruptions(ordered, (a.body, b.body, collector.body), last_deadline)
        if (not pair_beholds and abs(collector.speed) < abs(a.speed) and abs(collector.speed) < abs(b.speed)
                and rel_a[3] == rel_b[3] == "applying" and rel_a[4] and rel_b[4]
                and bases_a and bases_b and not interrupted):
            collections.append((collector, event_a[0], event_b[0], bases_a, bases_b))
    if collections:
        collector, event_a, event_b, bases_a, bases_b = collections[0]
        bases = tuple(f"{a.body}:{x}" for x in bases_a) + tuple(f"{b.body}:{x}" for x in bases_b)
        witnesses.append(_witness(LillyPerfectionKind.COLLECTION, ClassicalPerfectionState.PRESENT,
                                  (a.body, b.body, collector.body), (event_a.event_id, event_b.event_id),
                                  "Two averse significators apply to and receive one heavier collector.", bases))
    else:
        witnesses.append(_witness(LillyPerfectionKind.COLLECTION, ClassicalPerfectionState.ABSENT,
                                  (a.body, b.body), (), "No complete received collection occurs in the supplied trace."))

    witnesses.sort(key=lambda item: list(LillyPerfectionKind).index(item.kind))
    witness_tuple = tuple(witnesses)
    return ClassicalPerfectionAnalysis(
        jd_start, jd_end, a.body, b.body, is_day_chart, policy.profile_id, policy.profile_version, policy,
        tuple(states[name] for name in _BODIES), ordered, witness_tuple,
        tuple(item.kind for item in witness_tuple if item.state is ClassicalPerfectionState.PRESENT),
        tuple(item.kind for item in witness_tuple if item.state is ClassicalPerfectionState.INDETERMINATE),
        reader_provenance,
    )


def _trace(jd_start: float, jd_end: float, reader: SpkReader):
    cache: dict[tuple[str, float], object] = {}

    def position(body, jd):
        key = (body, round(jd, 12))
        if key not in cache:
            cache[key] = planet_at(body, jd, reader=reader)
        return cache[key]

    events: list[ClassicalPerfectionEvent] = []
    for body_a, body_b in combinations(_BODIES, 2):
        for angle, aspect in _TARGETS:
            jd = jd_start
            previous = _signal(position(body_a, jd).longitude, position(body_b, jd).longitude, angle)
            while jd < jd_end:
                nxt = min(jd + _SCAN_STEP, jd_end)
                current = _signal(position(body_a, nxt).longitude, position(body_b, nxt).longitude, angle)
                if previous == 0.0 or (previous * current < 0.0 and abs(previous) < 90.0 and abs(current) < 90.0):
                    lo, hi, sig_lo = jd, nxt, previous
                    for _ in range(40):
                        if hi - lo <= _TIME_TOL:
                            break
                        mid = (lo + hi) / 2.0
                        sig_mid = _signal(position(body_a, mid).longitude, position(body_b, mid).longitude, angle)
                        if sig_lo * sig_mid <= 0.0:
                            hi = mid
                        else:
                            lo, sig_lo = mid, sig_mid
                    exact = (lo + hi) / 2.0
                    eid = f"aspect:{body_a}:{body_b}:{angle:g}:{exact:.8f}"
                    events.append(ClassicalPerfectionEvent(eid, exact, ClassicalPerfectionEventKind.ASPECT_EXACT,
                                                           body_a, body_b, aspect, angle))
                jd, previous = nxt, current

    for body in _BODIES:
        jd = jd_start
        previous_sign = sign_of(position(body, jd).longitude)[0]
        while jd < jd_end:
            nxt = min(jd + _SCAN_STEP, jd_end)
            next_sign = sign_of(position(body, nxt).longitude)[0]
            if next_sign != previous_sign:
                lo, hi, lo_sign = jd, nxt, previous_sign
                for _ in range(40):
                    if hi - lo <= _TIME_TOL:
                        break
                    mid = (lo + hi) / 2.0
                    if sign_of(position(body, mid).longitude)[0] == lo_sign:
                        lo = mid
                    else:
                        hi = mid
                exact = (lo + hi) / 2.0
                after = sign_of(position(body, hi).longitude)[0]
                events.append(ClassicalPerfectionEvent(f"ingress:{body}:{exact:.8f}", exact,
                    ClassicalPerfectionEventKind.SIGN_INGRESS, body,
                    longitude_deg=position(body, exact).longitude, sign_before=lo_sign, sign_after=after))
            jd, previous_sign = nxt, next_sign

        for station in find_stations(body, jd_start, jd_end, reader=reader):
            kind = (ClassicalPerfectionEventKind.STATION_RETROGRADE if station.station_type == "retrograde"
                    else ClassicalPerfectionEventKind.STATION_DIRECT)
            events.append(ClassicalPerfectionEvent(f"station:{body}:{station.station_type}:{station.jd_ut:.8f}",
                                                    station.jd_ut, kind, body, longitude_deg=station.longitude))
    unique = {item.event_id: item for item in events}
    return tuple(sorted(unique.values(), key=lambda item: (item.jd_ut, item.event_id)))


def lilly_perfection_at(
    jd_start: float,
    jd_end: float,
    significator_a: str,
    significator_b: str,
    *,
    is_day_chart: bool,
    reader: SpkReader | None = None,
    policy: LillyPerfectionPolicy = LILLY_1647_PERFECTION_V1,
) -> ClassicalPerfectionAnalysis:
    """Trace and classify one bounded Lilly perfection interval."""

    if not all(math.isfinite(value) for value in (jd_start, jd_end)) or jd_end <= jd_start:
        raise ValueError("jd_end must be later than finite jd_start")
    if jd_end - jd_start > policy.max_span_days:
        raise ValueError(f"analysis span cannot exceed {policy.max_span_days:g} days")
    resolved = reader if reader is not None else get_reader()
    states = []
    for body in _BODIES:
        position = planet_at(body, jd_start, reader=resolved)
        states.append(ClassicalBodyState(body, position.longitude, position.speed, sign_of(position.longitude)[0]))
    events = _trace(jd_start, jd_end, resolved)
    path = getattr(resolved, "path", None)
    provenance = str(path) if path is not None else f"{type(resolved).__module__}.{type(resolved).__qualname__}"
    return classify_lilly_perfection_events(
        jd_start, jd_end, significator_a, significator_b, is_day_chart=is_day_chart,
        initial_states=tuple(states), events=events, reader_provenance=provenance, policy=policy,
    )

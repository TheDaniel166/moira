"""Lilly P4 perfection routes, blocking events and chronology.

Authority: Christian Astrology (1647), pp.110-113 and 124-127, and the P4
decisions P01-P09, B01-B05, K01-K07, H01, E01, Q01, Q02 and T01
(wiki/05_research/horary/lilly_core_2026/LILLY_P4_PERFECTION_DECISIONS_2026-10-30.md).
Book II readings (translation, refranation, frustration, collection,
dwelling, malevolent aspect, beholding) follow the Book II collation
(LILLY_P4_BOOK_II_COLLATION_2026-10-30.md); ``LILLY_BOOK_II_PRACTICE`` names
the attested selection, which the caller must still pass explicitly.

Two layers. The evaluators take typed evidence (legs, blocking events,
conditions, coverage) and return route or blocker records; every textual
alternative is an explicit reading with no default. The trace builder
derives contacts, stations and ingresses for the seven planets from one
explicitly identified longitude product, and ``lilly_perfection_routes``
turns a trace into route records for one querent/quesited pair.

Nothing here is a yes/no judgement, a probability or a timing prediction, and
no route outranks another. The v1 classifier (``classical_perfection``) and
the P2/P3 evidence layers are unchanged. Finite scan completion is not an
interval certificate of every unsampled oscillation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math

from ._strenum import StrEnum
from ._fixed_aspect_search import _FixedScanPolicy, _scan_fixed_aspects, _bisect_scalar
from .horary_moon import (
    LillyCoverageState, LillyMoonCoverage, LillyMoonProvenance, LillyMoonScanReceipt,
    LillyP3State, LillyTimeInterval,
)
from .horary_reception import (
    LillyDignityBasis, LillyDirectedReception, LillyEvidenceState, LillySnapshotContext,
    lilly_condition_snapshot, lilly_orb_evidence, lilly_position_from_longitude,
)
from .horary_considerations import lilly_solar_proximity


__all__ = [
    "LillyRouteState", "LillyRouteKind", "LillyBlockerKind", "LillyTranslationReading",
    "LillyProhibitionReading", "LillyMalevolentReading", "LillyBeholdingReading",
    "LillyHeavinessReading", "LillyRefranationReading", "LillyFrustrationReading", "LillyCollectionReading",
    "LillyDwellingReading", "LILLY_BOOK_II_PRACTICE", "LillyConditionEpoch", "LillyHouseClass", "LillyThirdRelation",
    "LillyRouteCondition", "LillyEpochValues", "LillyRouteEvent", "LillyRouteBlocker",
    "LillyAspectIntervention", "LillyThirdContact", "LillyRouteStation", "LillyThirdConjunction",
    "LillyReceptionBases", "LillyRouteRecord", "LillyBlockerRecord", "LillyRouteSummary",
    "LillyContinuationReceipt", "lilly_condition", "lilly_heavier",
    "lilly_conjunction_route", "lilly_sextile_trine_route", "lilly_square_route",
    "lilly_opposition_route", "lilly_translation_route", "lilly_collection_route",
    "lilly_reception_route", "lilly_dwelling_route", "lilly_prohibition", "lilly_refranation",
    "lilly_frustration", "lilly_route_summary", "lilly_continuation",
    "LillyPerfectionSearchPolicy", "LillyPairContact", "LillyBodyStation", "LillyBodyIngress",
    "LillyBodyMotion", "LillyPerfectionTrace", "LillyPerfectionReadings", "LillyRouteConditions",
    "LillyPrincipalRelation", "LillyPerfectionRoutes", "trace_lilly_perfection",
    "lilly_merge_perfection_traces", "lilly_perfection_routes", "lilly_perfection_routes_at",
]

_PROFILE = "lilly_1647_perfection_routes_v1"
_SOURCE = "Lilly 1647 pp.110-113,124-127; P4 "
_PLANETS = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")
_SUPERIOR = frozenset(("Saturn", "Jupiter", "Mars"))
_INFERIOR = frozenset(("Venus", "Mercury", "Moon"))
_MALEFICS = frozenset(("Saturn", "Mars"))
_TARGETS = (0., 60., 90., 120., 180., 240., 270., 300.)
_ASPECT_OF = {0.: "conjunction", 60.: "sextile", 300.: "sextile", 90.: "square", 270.: "square",
              120.: "trine", 240.: "trine", 180.: "opposition"}
_ASPECTS = frozenset(_ASPECT_OF.values())
_P06_BASES = frozenset((LillyDignityBasis.DOMICILE, LillyDignityBasis.TRIPLICITY, LillyDignityBasis.TERM))


# ---------------------------------------------------------------------- vocabularies

class LillyRouteState(StrEnum):
    """One route's outcome under its named reading; never a judgement."""
    COMPLETE = "complete"
    BLOCKED = "blocked"
    CONDITION_UNMET = "condition_unmet"
    ABSENT = "absent"
    NOT_EVALUABLE = "not_evaluable"


class LillyRouteKind(StrEnum):
    """Routes of P01-P09."""
    CONJUNCTION = "conjunction"
    SEXTILE = "sextile"
    TRINE = "trine"
    SQUARE = "square"
    OPPOSITION = "opposition"
    TRANSLATION = "translation"
    COLLECTION = "collection"
    MUTUAL_RECEPTION = "mutual_reception"
    DWELLING = "dwelling"


class LillyBlockerKind(StrEnum):
    """Blocking events of B01-B04, each with its own stated effect."""
    PROHIBITION_BODILY = "prohibition_bodily"
    PROHIBITION_ASPECT = "prohibition_aspect"
    REFRANATION = "refranation"
    FRUSTRATION = "frustration"

    @property
    def effect(self) -> str:
        """Return Lilly's stated effect (pp.110-113)."""
        return {"prohibition_bodily": "hindered_and_retarded", "prohibition_aspect": "hindered_and_retarded",
                "refranation": "never_effected", "frustration": "third_party_gains"}[self.value]


class LillyTranslationReading(StrEnum):
    """P05 (p.111), P06 (p.126) and Book II practice (pp.186, 317-318, 388); no default."""
    P111_STRUCTURAL = "p111_structural"
    P126_FULL = "p126_full"
    BOOK_II_PRACTICE = "book_ii_practice"


class LillyProhibitionReading(StrEnum):
    """B01/B02 readings; no default."""
    INTERPOSITION_TO_EITHER = "interposition_to_either"
    SUCCESSIVE_TO_BOTH = "successive_to_both"


class LillyMalevolentReading(StrEnum):
    """B05 readings of "malevolent aspect"; no default.

``MALEFIC_OR_EVIL_LORD`` is the Book II usage (pp.227, 409, 433, 446): a square
or opposition from a malefic or from a lord of the sixth, eighth or twelfth,
without reception.
"""
    MALEFIC_PLANET = "malefic_planet"
    HARD_ASPECT = "hard_aspect"
    MALEFIC_OR_EVIL_LORD = "malefic_or_evil_lord_hard_aspect"


class LillyBeholdingReading(StrEnum):
    """P07 readings of "do not behold"; no default.

``NOT_REQUIRED`` is Book II practice: the test is never applied (C09, p.239).
"""
    SIGN_AVERSION = "sign_aversion"
    NO_CURRENT_ASPECT = "no_current_aspect"
    NOT_REQUIRED = "not_required"


class LillyRefranationReading(StrEnum):
    """B03: whose station refrains; no default.

``APPLYING_PRINCIPAL`` follows p.111; ``EITHER_PRINCIPAL`` follows p.317
("Retrogradation of the principall Significators intervening").
"""
    APPLYING_PRINCIPAL = "applying_principal"
    EITHER_PRINCIPAL = "either_principal"


class LillyFrustrationReading(StrEnum):
    """B04: what can be frustrated; no default.

``CONJUNCTION_ONLY`` follows pp.112-113; ``CONJUNCTION_OR_ASPECT`` follows
Book II ("frustrates their aspect", p.305; pp.220, 373).
"""
    CONJUNCTION_ONLY = "conjunction_only"
    CONJUNCTION_OR_ASPECT = "conjunction_or_aspect"


class LillyCollectionReading(StrEnum):
    """P07: who receives whom, and the collector's condition; no default.

``P126_PRINCIPALS_RECEIVE`` follows p.126 (both principals receive the
collector). ``BOOK_II_PRACTICE`` follows pp.186, 239, 433-434 and 446: an
infortune or impedited collector must itself receive both principals, and
the collector is not retrograde, combust or cadent and does not leave its
sign before both legs.
"""
    P126_PRINCIPALS_RECEIVE = "p126_principals_receive_collector"
    BOOK_II_PRACTICE = "book_ii_practice"


class LillyDwellingReading(StrEnum):
    """P09: dwelling in houses; no default.

``P126_REJECTED_EXCEPT_LUNAR`` follows pp.126-127 (the placement "holds not
true" without a lunar translation); ``BOOK_II_ROUTE`` follows pp.186, 205
and 444, where the placement is a route of its own.
"""
    P126_REJECTED_EXCEPT_LUNAR = "p126_rejected_except_lunar"
    BOOK_II_ROUTE = "book_ii_route"


class LillyHeavinessReading(StrEnum):
    """H01 readings of lighter and heavier; no default."""
    TRADITIONAL_ORDER = "traditional_order"
    INSTANTANEOUS_SPEED = "instantaneous_speed"
    SUPERIOR_INFERIOR = "superior_inferior"


class LillyConditionEpoch(StrEnum):
    """E01 evaluation epochs."""
    QUESTION = "question"
    LEG_START = "leg_start"
    CONTACT = "contact"


class LillyHouseClass(StrEnum):
    """P01 house classes and their stated qualifiers."""
    ANGULAR = "angular"
    SUCCEDENT = "succedent"
    CADENT = "cadent"

    @property
    def qualifier(self) -> str:
        """Return the p.125 conjunction qualifier."""
        return {"angular": "without_let", "succedent": "perfected_not_so_soon",
                "cadent": "loss_of_time_difficulty"}[self.value]


class LillyThirdRelation(StrEnum):
    """A third planet's relation to the applying principal at the start (B02)."""
    APPLYING = "applying"
    SEPARATING = "separating"


# ---------------------------------------------------------------------- validation helpers

def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _strings(value, name):
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    for item in value:
        _text(item, name)
    if len(set(value)) != len(value):
        raise ValueError(f"{name} must be distinct")


def _planet(value):
    if value not in _PLANETS:
        raise ValueError("body must be one of the classical seven planets")


def _typed(value, cls, name, *, optional=False):
    if optional and value is None:
        return
    if not isinstance(value, cls):
        raise TypeError(f"{name} must be {cls.__name__}")


def _rows(value, cls, name):
    if not isinstance(value, tuple) or any(not isinstance(r, cls) for r in value):
        raise TypeError(f"{name} must be an immutable tuple of {cls.__name__}")
    ids = [r.event_id for r in value]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name} event IDs must be distinct")


def _order(a: LillyTimeInterval, b: LillyTimeInterval) -> str:
    """K01: 'before', 'after' or 'overlap' for two envelopes."""
    if a.high < b.low:
        return "before"
    if b.high < a.low:
        return "after"
    return "overlap"


def _complete(coverage) -> bool:
    _typed(coverage, LillyCoverageState, "coverage")
    return coverage is LillyCoverageState.COMPLETE


def _every(states):
    states = tuple(states)
    if LillyP3State.ABSENT in states:
        return LillyP3State.ABSENT
    if LillyP3State.NOT_EVALUABLE in states:
        return LillyP3State.NOT_EVALUABLE
    return LillyP3State.PRESENT


# ---------------------------------------------------------------------- evidence vessels

@dataclass(frozen=True, slots=True)
class LillyRouteCondition:
    """A source condition at a named epoch; known states cite evidence (Q01)."""
    name: str
    state: LillyP3State
    epoch: LillyConditionEpoch
    source: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        _text(self.name, "condition name")
        _text(self.source, "condition source")
        _typed(self.epoch, LillyConditionEpoch, "condition epoch")
        if self.state not in (LillyP3State.PRESENT, LillyP3State.ABSENT, LillyP3State.NOT_EVALUABLE):
            raise ValueError("condition state must be present, absent or not evaluable")
        _strings(self.evidence_ids, "condition evidence IDs")
        if self.state is not LillyP3State.NOT_EVALUABLE and not self.evidence_ids:
            raise ValueError("a known condition needs supporting evidence IDs")


def lilly_condition(name: str, value: bool | None, *, epoch: LillyConditionEpoch, source: str,
                    evidence_ids: tuple[str, ...] = ()) -> LillyRouteCondition:
    """Build a condition from a bool or ``None`` (unknown)."""
    if value is not None and type(value) is not bool:
        raise TypeError("condition value must be bool or None")
    state = LillyP3State.NOT_EVALUABLE if value is None else LillyP3State.PRESENT if value else LillyP3State.ABSENT
    return LillyRouteCondition(name, state, epoch, source, evidence_ids)


def _unknown(name, epoch=LillyConditionEpoch.QUESTION):
    return LillyRouteCondition(name, LillyP3State.NOT_EVALUABLE, epoch, "not_supplied")


@dataclass(frozen=True, slots=True)
class LillyEpochValues:
    """E01: one proposition's values at named epochs; never transported."""
    name: str
    values: tuple[tuple[LillyConditionEpoch, bool | None], ...]

    def __post_init__(self):
        _text(self.name, "epoch value name")
        if not isinstance(self.values, tuple):
            raise TypeError("epoch values must be an immutable tuple")
        epochs = [e for e, _ in self.values]
        if len(epochs) != len(set(epochs)) or any(not isinstance(e, LillyConditionEpoch) for e in epochs):
            raise ValueError("epoch values need distinct typed epochs")
        if any(v is not None and type(v) is not bool for _, v in self.values):
            raise TypeError("epoch values must be bool or None")

    def at(self, epoch: LillyConditionEpoch) -> LillyP3State:
        """Return the value at exactly this epoch; a missing epoch is not evaluable."""
        _typed(epoch, LillyConditionEpoch, "epoch")
        value = dict(self.values).get(epoch)
        return LillyP3State.NOT_EVALUABLE if value is None else LillyP3State.PRESENT if value else LillyP3State.ABSENT


@dataclass(frozen=True, slots=True)
class LillyRouteEvent:
    """A leg's completing contact or a separation, with its time envelope."""
    event_id: str
    time: LillyTimeInterval

    def __post_init__(self):
        _text(self.event_id, "event ID")
        _typed(self.time, LillyTimeInterval, "event time")


@dataclass(frozen=True, slots=True)
class LillyRouteBlocker:
    """A blocking event against a leg (``leg_id`` names it where a route has several).

``resolved=False`` marks a blocker whose own record is not evaluable: it can
leave the route unresolved but never blocks it.
"""
    event_id: str
    kind: LillyBlockerKind
    time: LillyTimeInterval
    leg_id: str | None = None
    resolved: bool = True

    def __post_init__(self):
        _text(self.event_id, "blocker ID")
        _typed(self.kind, LillyBlockerKind, "blocker kind")
        _typed(self.time, LillyTimeInterval, "blocker time")
        if self.leg_id is not None:
            _text(self.leg_id, "blocker leg")
        if type(self.resolved) is not bool:
            raise TypeError("resolved must be a bool")


@dataclass(frozen=True, slots=True)
class LillyAspectIntervention:
    """An aspect cast to a principal before a sextile or trine perfects (B05).

``from_evil_lord`` (the caster rules the sixth, eighth or twelfth) and
``received`` (reception either way between caster and principal) are
``None`` when unknown; only the Book II reading reads them.
"""
    event_id: str
    time: LillyTimeInterval
    from_malefic: bool
    aspect: str
    from_evil_lord: bool | None = None
    received: bool | None = None

    def __post_init__(self):
        _text(self.event_id, "intervention ID")
        _typed(self.time, LillyTimeInterval, "intervention time")
        if type(self.from_malefic) is not bool or self.aspect not in _ASPECTS - {"conjunction"}:
            raise ValueError("intervention needs a malefic flag and an aspect")
        for name in ("from_evil_lord", "received"):
            if getattr(self, name) is not None and type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool or None")

    def malevolent(self, reading: LillyMalevolentReading) -> bool | None:
        """Return whether this intervention is malevolent under the reading (``None``: unknown)."""
        _typed(reading, LillyMalevolentReading, "malevolent reading")
        if reading is LillyMalevolentReading.MALEFIC_PLANET:
            return self.from_malefic
        hard = self.aspect in ("square", "opposition")
        if reading is LillyMalevolentReading.HARD_ASPECT:
            return hard
        if not hard or self.received is True:
            return False
        evil = True if self.from_malefic else self.from_evil_lord
        if evil is False:
            return False
        return None if evil is None or self.received is None else True


@dataclass(frozen=True, slots=True)
class LillyThirdContact:
    """A third planet's contact with the applying or the heavier principal (B01/B02)."""
    event_id: str
    principal: str
    mode: str
    time: LillyTimeInterval

    def __post_init__(self):
        _text(self.event_id, "contact ID")
        if self.principal not in ("applying", "heavier") or self.mode not in ("body", "aspect"):
            raise ValueError("third contact needs principal applying|heavier and mode body|aspect")
        _typed(self.time, LillyTimeInterval, "contact time")


@dataclass(frozen=True, slots=True)
class LillyRouteStation:
    """A station of the applying or the heavier principal (B03)."""
    event_id: str
    body_role: str
    time: LillyTimeInterval

    def __post_init__(self):
        _text(self.event_id, "station ID")
        if self.body_role not in ("applying", "heavier"):
            raise ValueError("station body role must be applying or heavier")
        _typed(self.time, LillyTimeInterval, "station time")


@dataclass(frozen=True, slots=True)
class LillyThirdConjunction:
    """The heavier principal's contact with a third planet (B04)."""
    event_id: str
    aspect: str
    time: LillyTimeInterval

    def __post_init__(self):
        _text(self.event_id, "contact ID")
        if self.aspect not in _ASPECTS:
            raise ValueError("unknown aspect")
        _typed(self.time, LillyTimeInterval, "contact time")


@dataclass(frozen=True, slots=True)
class LillyReceptionBases:
    """Directed reception bases: established ones and ones left unresolved (P2)."""
    present: tuple[LillyDignityBasis, ...]
    unresolved: tuple[LillyDignityBasis, ...] = ()

    def __post_init__(self):
        for name in ("present", "unresolved"):
            rows = getattr(self, name)
            if not isinstance(rows, tuple) or any(not isinstance(b, LillyDignityBasis) for b in rows):
                raise TypeError(f"{name} reception bases must be a tuple of LillyDignityBasis")
        if set(self.present) & set(self.unresolved):
            raise ValueError("a basis cannot be both present and unresolved")

    @classmethod
    def from_directed(cls, reception: LillyDirectedReception) -> "LillyReceptionBases":
        """Adapt one P2 directed reception witness."""
        _typed(reception, LillyDirectedReception, "reception")
        return cls(tuple(e.basis for e in reception.dignities if e.state is LillyEvidenceState.PRESENT),
                   tuple(e.basis for e in reception.dignities if e.state is LillyEvidenceState.NOT_EVALUABLE))

    def received(self, allowed=None) -> LillyP3State:
        """Present if an allowed basis is established; unknown if one is unresolved."""
        allowed = frozenset(LillyDignityBasis) if allowed is None else frozenset(allowed)
        if allowed & set(self.present):
            return LillyP3State.PRESENT
        if allowed & set(self.unresolved):
            return LillyP3State.NOT_EVALUABLE
        return LillyP3State.ABSENT


@dataclass(frozen=True, slots=True)
class LillyRouteRecord:
    """One route under its reading: legs, blockers, conditions and stated effects."""
    kind: LillyRouteKind
    state: LillyRouteState
    reading: str | None
    actors: tuple[str, ...]
    leg_ids: tuple[str, ...]
    blocking_ids: tuple[str, ...]
    effects: tuple[str, ...]
    conditions: tuple[LillyRouteCondition, ...]
    completion: LillyTimeInterval | None
    qualifier: str | None = None
    desirability: str | None = None
    attribution: str | None = None
    reasons: tuple[str, ...] = ()
    source_reference: str = ""
    profile_id: str = field(default=_PROFILE, init=False)
    verdict: None = field(default=None, init=False)

    def __post_init__(self):
        _typed(self.kind, LillyRouteKind, "route kind")
        _typed(self.state, LillyRouteState, "route state")
        _strings(self.leg_ids, "leg IDs")
        _strings(self.blocking_ids, "blocking IDs")
        if not isinstance(self.effects, tuple) or not isinstance(self.reasons, tuple):
            raise TypeError("effects and reasons must be tuples")
        _rows_conditions(self.conditions)
        _typed(self.completion, LillyTimeInterval, "completion", optional=True)
        if (self.state is LillyRouteState.COMPLETE) != (self.completion is not None) and self.kind not in (
                LillyRouteKind.MUTUAL_RECEPTION, LillyRouteKind.DWELLING):
            raise ValueError("only a complete route has a completion envelope")
        if (self.state is LillyRouteState.BLOCKED) != bool(self.blocking_ids):
            raise ValueError("blocking IDs exactly when the route is blocked")


def _rows_conditions(rows):
    if not isinstance(rows, tuple) or any(not isinstance(r, LillyRouteCondition) for r in rows):
        raise TypeError("conditions must be an immutable tuple of LillyRouteCondition")


@dataclass(frozen=True, slots=True)
class LillyBlockerRecord:
    """One blocker under its reading, with the third planet's role (B01-B04)."""
    kind: str
    reading: str | None
    state: LillyP3State
    event_ids: tuple[str, ...]
    effect: str
    third_role: str | None = None
    contact_kind: str | None = None
    note: str | None = None
    source_reference: str = ""
    profile_id: str = field(default=_PROFILE, init=False)

    def __post_init__(self):
        _text(self.kind, "blocker kind")
        if self.state not in (LillyP3State.PRESENT, LillyP3State.ABSENT, LillyP3State.NOT_EVALUABLE):
            raise ValueError("blocker state must be present, absent or not evaluable")
        _strings(self.event_ids, "blocker event IDs")


# ---------------------------------------------------------------------- shared route ordering

def _route_state(*, leg_missing, coverage, conditions, blocker_orders, unknown=False):
    """Missing leg, unmet condition, definite blocker, unresolved, else complete."""
    if leg_missing:
        return LillyRouteState.ABSENT if _complete(coverage) else LillyRouteState.NOT_EVALUABLE
    met = _every(c.state for c in conditions)
    if met is LillyP3State.ABSENT:
        return LillyRouteState.CONDITION_UNMET
    if "before" in blocker_orders:
        return LillyRouteState.BLOCKED
    if met is LillyP3State.NOT_EVALUABLE or unknown or "overlap" in blocker_orders or not _complete(coverage):
        return LillyRouteState.NOT_EVALUABLE
    return LillyRouteState.COMPLETE


def _blocked(blockers, leg):
    rows = [(b, _order(b.time, leg.time) if b.resolved else "overlap") for b in blockers]
    definite = sorted(b.event_id for b, o in rows if o == "before")
    effects = tuple(sorted({b.kind.effect for b, o in rows if o == "before"}))
    return [o for _, o in rows], tuple(definite), effects


def _direct(kind, actors, contact, conditions, blockers, coverage, reading=None, reasons=(), pages=""):
    _typed(contact, LillyRouteEvent, "contact", optional=True)
    _rows(blockers, LillyRouteBlocker, "blockers")
    _rows_conditions(conditions)
    orders, blocking, effects = ([], (), ()) if contact is None else _blocked(blockers, contact)
    state = _route_state(leg_missing=contact is None, coverage=coverage, conditions=conditions, blocker_orders=orders)
    return LillyRouteRecord(kind, state, reading, actors, () if contact is None else (contact.event_id,),
                            blocking if state is LillyRouteState.BLOCKED else (),
                            effects if state is LillyRouteState.BLOCKED else (), conditions,
                            contact.time if state is LillyRouteState.COMPLETE else None,
                            reasons=tuple(reasons), source_reference=_SOURCE + pages)


# ---------------------------------------------------------------------- route evaluators

def lilly_conjunction_route(contact: LillyRouteEvent | None, *, house_class: LillyHouseClass | None,
                            blockers: tuple[LillyRouteBlocker, ...], coverage: LillyCoverageState,
                            ingresses: tuple[LillyRouteEvent, ...] = (),
                            actors: tuple[str, ...] = ()) -> LillyRouteRecord:
    """P01: conjunction of the principals, qualified by house class (K05 ingress recorded)."""
    _typed(house_class, LillyHouseClass, "house class", optional=True)
    _rows(ingresses, LillyRouteEvent, "ingresses")
    record = _direct(LillyRouteKind.CONJUNCTION, actors, contact, (), blockers, coverage,
                     reasons=tuple(f"ingress_recorded_not_blocking:{i.event_id}" for i in ingresses), pages="p.125; P01")
    if record.state is LillyRouteState.COMPLETE:
        qualifier = "not_evaluable" if house_class is None else house_class.qualifier
        return _with(record, qualifier=qualifier)
    return record


def _with(record, **changes):
    values = {name: getattr(record, name) for name in (
        "kind", "state", "reading", "actors", "leg_ids", "blocking_ids", "effects", "conditions", "completion",
        "qualifier", "desirability", "attribution", "reasons", "source_reference")}
    values.update(changes)
    return LillyRouteRecord(**values)


def lilly_sextile_trine_route(contact: LillyRouteEvent | None, *, aspect: str, good_houses: LillyRouteCondition,
                              well_dignified: LillyRouteCondition,
                              interventions: tuple[LillyAspectIntervention, ...],
                              reading: LillyMalevolentReading, coverage: LillyCoverageState,
                              actors: tuple[str, ...] = ()) -> LillyRouteRecord:
    """P02 with B05 under an explicitly selected reading."""
    if aspect not in ("sextile", "trine"):
        raise ValueError("P02 concerns sextile or trine")
    _typed(reading, LillyMalevolentReading, "malevolent reading")
    _rows(interventions, LillyAspectIntervention, "interventions")
    conditions = (good_houses, well_dignified)
    _rows_conditions(conditions)
    orders, blocking = [], ()
    if contact is not None:
        _typed(contact, LillyRouteEvent, "contact")
        relevant = []
        for i in interventions:
            malevolent = i.malevolent(reading)
            if malevolent is False:
                continue
            order = _order(i.time, contact.time)
            # Unknown malevolence before the contact leaves the route unresolved.
            relevant.append((i, order if malevolent else "overlap" if order != "after" else "after"))
        orders = [o for _, o in relevant]
        blocking = tuple(sorted(i.event_id for i, o in relevant if o == "before"))
    state = _route_state(leg_missing=contact is None, coverage=coverage, conditions=conditions, blocker_orders=orders)
    kind = LillyRouteKind.SEXTILE if aspect == "sextile" else LillyRouteKind.TRINE
    return LillyRouteRecord(kind, state, reading.value, actors, () if contact is None else (contact.event_id,),
                            blocking if state is LillyRouteState.BLOCKED else (),
                            ("condition_of_p02_unmet",) if state is LillyRouteState.BLOCKED else (), conditions,
                            contact.time if state is LillyRouteState.COMPLETE else None,
                            source_reference=_SOURCE + "p.125; P02, B05")


def lilly_square_route(contact: LillyRouteEvent | None, *, querent_degree_dignity: LillyRouteCondition,
                       quesited_degree_dignity: LillyRouteCondition, proper_good_houses: LillyRouteCondition,
                       blockers: tuple[LillyRouteBlocker, ...], coverage: LillyCoverageState,
                       actors: tuple[str, ...] = ()) -> LillyRouteRecord:
    """P03: dignity in the degrees and good houses, "otherwise not"."""
    return _direct(LillyRouteKind.SQUARE, actors, contact,
                   (querent_degree_dignity, quesited_degree_dignity, proper_good_houses), blockers, coverage,
                   pages="p.125; P03")


def lilly_opposition_route(contact: LillyRouteEvent | None, *, mutual_house_reception: LillyRouteCondition,
                           friendly_houses: LillyRouteCondition, moon_condition: LillyRouteCondition,
                           blockers: tuple[LillyRouteBlocker, ...], coverage: LillyCoverageState,
                           actors: tuple[str, ...] = ()) -> LillyRouteRecord:
    """P04: three joint conditions; completion and regret reported separately."""
    record = _direct(LillyRouteKind.OPPOSITION, actors, contact,
                     (mutual_house_reception, friendly_houses, moon_condition), blockers, coverage,
                     pages="p.125; P04, Q02")
    return _with(record, desirability="regret_reported") if record.state is LillyRouteState.COMPLETE else record


def lilly_translation_route(reading: LillyTranslationReading, *, separation: LillyRouteEvent,
                            second_leg: LillyRouteEvent | None, translator_lighter: LillyRouteCondition,
                            principals_prior_separation: LillyRouteCondition,
                            reception: LillyReceptionBases | None,
                            intervening_contacts: tuple[LillyRouteEvent, ...],
                            blockers: tuple[LillyRouteBlocker, ...], coverage: LillyCoverageState,
                            actors: tuple[str, ...] = (),
                            translator_conditions: tuple[LillyRouteCondition, ...] = (),
                            infortune_received: LillyRouteCondition | None = None) -> LillyRouteRecord:
    """P05, P06 or Book II practice under an explicitly selected reading (K02 leg order).

``separation`` is the first leg. Under ``BOOK_II_PRACTICE`` it may also be a
future contact with the first principal (C13, p.388); that reading uses no
heaviness, principal-history or intervening-contact test, and instead the
translator's condition (``translator_conditions``) and, for an infortune
receiving the light, ``infortune_received`` (p.186; unknown when omitted).
"""
    _typed(reading, LillyTranslationReading, "translation reading")
    _typed(separation, LillyRouteEvent, "separation")
    _typed(second_leg, LillyRouteEvent, "second leg", optional=True)
    _typed(reception, LillyReceptionBases, "reception", optional=True)
    _rows(intervening_contacts, LillyRouteEvent, "intervening contacts")
    _rows(blockers, LillyRouteBlocker, "blockers")
    _rows_conditions(translator_conditions)
    _typed(infortune_received, LillyRouteCondition, "infortune reception", optional=True)
    pages = {LillyTranslationReading.P111_STRUCTURAL: "p.111; P05",
             LillyTranslationReading.P126_FULL: "pp.125-126; P06",
             LillyTranslationReading.BOOK_II_PRACTICE: "pp.186, 317-318, 388, 433-434; P05/P06 Book II"}[reading]
    legs = (separation.event_id,) + (() if second_leg is None else (second_leg.event_id,))
    if second_leg is None:
        state = _route_state(leg_missing=True, coverage=coverage, conditions=(), blocker_orders=[])
        return LillyRouteRecord(LillyRouteKind.TRANSLATION, state, reading.value, actors, legs, (), (), (), None,
                                source_reference=_SOURCE + pages)
    order = _order(separation.time, second_leg.time)
    if order == "after":
        return LillyRouteRecord(LillyRouteKind.TRANSLATION, LillyRouteState.ABSENT, reading.value, actors, legs,
                                (), (), (), None, reasons=("separation_follows_second_leg",),
                                source_reference=_SOURCE + pages)
    if reading is LillyTranslationReading.P111_STRUCTURAL:
        conditions = (translator_lighter,)
    elif reading is LillyTranslationReading.BOOK_II_PRACTICE:
        conditions = translator_conditions + (infortune_received or _unknown("receiving_infortune_received"),)
    else:
        received = (LillyP3State.NOT_EVALUABLE if reception is None else reception.received(_P06_BASES))
        between = [_order(i.time, second_leg.time) for i in intervening_contacts
                   if _order(separation.time, i.time) == "before"]
        clear = (LillyP3State.ABSENT if "before" in between else
                 LillyP3State.NOT_EVALUABLE if "overlap" in between else LillyP3State.PRESENT)
        conditions = (principals_prior_separation,
                      LillyRouteCondition("received_by_house_triplicity_or_term", received,
                                          LillyConditionEpoch.QUESTION, "P2_directed_reception",
                                          () if received is LillyP3State.NOT_EVALUABLE else ("reception",)),
                      LillyRouteCondition("no_intervening_contact", clear, LillyConditionEpoch.LEG_START,
                                          "trace_contacts", () if clear is LillyP3State.NOT_EVALUABLE else
                                          tuple(i.event_id for i in intervening_contacts) or ("trace",)))
    _rows_conditions(conditions)
    orders, blocking, effects = _blocked(blockers, second_leg)
    state = _route_state(leg_missing=False, coverage=coverage, conditions=conditions, blocker_orders=orders,
                         unknown=order == "overlap")
    return LillyRouteRecord(LillyRouteKind.TRANSLATION, state, reading.value, actors, legs,
                            blocking if state is LillyRouteState.BLOCKED else (),
                            effects if state is LillyRouteState.BLOCKED else (), conditions,
                            second_leg.time if state is LillyRouteState.COMPLETE else None,
                            source_reference=_SOURCE + pages)


def lilly_collection_route(reading: LillyBeholdingReading, *, principals_behold_by_sign: LillyRouteCondition,
                           principals_current_aspect: LillyRouteCondition,
                           collector_heavier: LillyRouteCondition,
                           reception_by_querent: LillyReceptionBases | None,
                           reception_by_quesited: LillyReceptionBases | None,
                           leg_querent: LillyRouteEvent | None, leg_quesited: LillyRouteEvent | None,
                           blockers: tuple[LillyRouteBlocker, ...], coverage: LillyCoverageState,
                           actors: tuple[str, ...] = (), collection: LillyCollectionReading,
                           querent_received_by_collector: LillyReceptionBases | None = None,
                           quesited_received_by_collector: LillyReceptionBases | None = None,
                           collector_infortune: LillyRouteCondition | None = None,
                           collector_conditions: tuple[LillyRouteCondition, ...] = ()) -> LillyRouteRecord:
    """P07 under explicitly selected beholding and collection readings; leg order is reported.

Under ``P126_PRINCIPALS_RECEIVE`` both principals receive the collector.
Under ``BOOK_II_PRACTICE`` an infortune or impedited collector
(``collector_infortune``) must itself receive both principals, one being
not enough (p.186), and ``collector_conditions`` carry the collector's
condition (pp.433-434, 446).
"""
    _typed(reading, LillyBeholdingReading, "beholding reading")
    _typed(collection, LillyCollectionReading, "collection reading")
    _rows(blockers, LillyRouteBlocker, "blockers")
    _rows_conditions(collector_conditions)
    _typed(collector_infortune, LillyRouteCondition, "collector infortune", optional=True)
    label = f"{collection.value}+{reading.value}"
    pages = ("p.126; P07" if collection is LillyCollectionReading.P126_PRINCIPALS_RECEIVE
             else "pp.186, 225, 239, 433-434, 446; P07 Book II")
    legs = tuple(leg.event_id for leg in (leg_querent, leg_quesited) if leg is not None)
    if leg_querent is None or leg_quesited is None:
        state = _route_state(leg_missing=True, coverage=coverage, conditions=(), blocker_orders=[])
        return LillyRouteRecord(LillyRouteKind.COLLECTION, state, label, actors, legs, (), (), (), None,
                                source_reference=_SOURCE + pages)
    conditions = []
    if reading is not LillyBeholdingReading.NOT_REQUIRED:
        behold = (principals_behold_by_sign if reading is LillyBeholdingReading.SIGN_AVERSION
                  else principals_current_aspect)
        flipped = {LillyP3State.PRESENT: LillyP3State.ABSENT, LillyP3State.ABSENT: LillyP3State.PRESENT}.get(
            behold.state, LillyP3State.NOT_EVALUABLE)
        conditions.append(LillyRouteCondition("principals_do_not_behold", flipped, behold.epoch, behold.source,
                                              behold.evidence_ids))
    conditions.append(collector_heavier)
    if collection is LillyCollectionReading.P126_PRINCIPALS_RECEIVE:
        for name, value in (("received_by_querent", reception_by_querent),
                            ("received_by_quesited", reception_by_quesited)):
            state = LillyP3State.NOT_EVALUABLE if value is None else value.received()
            conditions.append(LillyRouteCondition(name, state, LillyConditionEpoch.QUESTION, "P2_directed_reception",
                                                  () if state is LillyP3State.NOT_EVALUABLE else (name,)))
    else:
        both = _every(LillyP3State.NOT_EVALUABLE if value is None else value.received()
                      for value in (querent_received_by_collector, quesited_received_by_collector))
        infortune = (collector_infortune or _unknown("collector_infortune_or_impedited")).state
        state = (LillyP3State.PRESENT if infortune is LillyP3State.ABSENT or both is LillyP3State.PRESENT
                 else LillyP3State.ABSENT if infortune is LillyP3State.PRESENT and both is LillyP3State.ABSENT
                 else LillyP3State.NOT_EVALUABLE)
        evidence = () if state is LillyP3State.NOT_EVALUABLE else (
            ("collector_not_infortune",) if infortune is LillyP3State.ABSENT else ("collector_reception",))
        conditions.append(LillyRouteCondition("infortune_collector_receives_both", state, LillyConditionEpoch.QUESTION,
                                              "P2_directed_reception", evidence))
        conditions.extend(collector_conditions)
    conditions = tuple(conditions)
    leg = {"querent": leg_querent, "quesited": leg_quesited}
    rows = []
    for b in blockers:
        if b.leg_id not in leg:
            raise ValueError("a collection blocker must name its leg: querent or quesited")
        rows.append((b, _order(b.time, leg[b.leg_id].time) if b.resolved else "overlap"))
    orders = [o for _, o in rows]
    blocking = tuple(sorted(b.event_id for b, o in rows if o == "before"))
    effects = tuple(sorted({b.kind.effect for b, o in rows if o == "before"}))
    state = _route_state(leg_missing=False, coverage=coverage, conditions=conditions, blocker_orders=orders)
    order = {"before": "querent_first", "after": "quesited_first", "overlap": "simultaneous_or_unresolved"}[
        _order(leg_querent.time, leg_quesited.time)]
    completion = None
    if state is LillyRouteState.COMPLETE:
        completion = LillyTimeInterval(max(leg_querent.time.low, leg_quesited.time.low),
                                       max(leg_querent.time.high, leg_quesited.time.high))
    return LillyRouteRecord(LillyRouteKind.COLLECTION, state, label, actors, legs,
                            blocking if state is LillyRouteState.BLOCKED else (),
                            effects if state is LillyRouteState.BLOCKED else (), conditions, completion,
                            qualifier=order, source_reference=_SOURCE + pages + ", K02")


def lilly_reception_route(querent_in_quesited_dignity: LillyReceptionBases | None,
                          quesited_in_querent_dignity: LillyReceptionBases | None, *,
                          actors: tuple[str, ...] = ()) -> LillyRouteRecord:
    """P08: mutual reception as its own route; it never alters another route's record."""
    states = [LillyP3State.NOT_EVALUABLE if r is None else r.received()
              for r in (querent_in_quesited_dignity, quesited_in_querent_dignity)]
    met = _every(states)
    state = {LillyP3State.PRESENT: LillyRouteState.COMPLETE, LillyP3State.ABSENT: LillyRouteState.ABSENT}.get(
        met, LillyRouteState.NOT_EVALUABLE)
    qualifier = None
    if state is LillyRouteState.COMPLETE:
        by_house = all(LillyDignityBasis.DOMICILE in r.present
                       for r in (querent_in_quesited_dignity, quesited_in_querent_dignity))
        qualifier = "strongest_by_house" if by_house else "other_essential_dignity"
    conditions = tuple(LillyRouteCondition(name, s, LillyConditionEpoch.QUESTION, "P2_directed_reception",
                                           () if s is LillyP3State.NOT_EVALUABLE else (name,))
                       for name, s in zip(("querent_in_quesited_dignity", "quesited_in_querent_dignity"), states))
    return LillyRouteRecord(LillyRouteKind.MUTUAL_RECEPTION, state, None, actors, (), (), (), conditions, None,
                            qualifier=qualifier, reasons=("never_overrides_another_route",),
                            source_reference=_SOURCE + "p.112; P08")


def lilly_dwelling_route(placement: LillyRouteCondition, moon_translation: LillyRouteRecord | None, *,
                         reading: LillyDwellingReading, actors: tuple[str, ...] = ()) -> LillyRouteRecord:
    """P09 under an explicitly selected reading.

``P126_REJECTED_EXCEPT_LUNAR``: the placement is reported as rejected and only
the lunar-translation form is a route. ``BOOK_II_ROUTE``: the placement is a
route of its own (pp.186, 205, 444), with no completion envelope.
"""
    _typed(placement, LillyRouteCondition, "placement")
    _typed(moon_translation, LillyRouteRecord, "Moon translation", optional=True)
    _typed(reading, LillyDwellingReading, "dwelling reading")
    if moon_translation is not None and moon_translation.kind is not LillyRouteKind.TRANSLATION:
        raise ValueError("the dwelling exception is a lunar translation")
    if reading is LillyDwellingReading.BOOK_II_ROUTE:
        state = {LillyP3State.PRESENT: LillyRouteState.COMPLETE, LillyP3State.ABSENT: LillyRouteState.ABSENT}.get(
            placement.state, LillyRouteState.NOT_EVALUABLE)
        return LillyRouteRecord(LillyRouteKind.DWELLING, state, reading.value, actors, (), (), (), (placement,), None,
                                attribution="book_ii_testimony" if state is LillyRouteState.COMPLETE else None,
                                source_reference=_SOURCE + "pp.186, 205, 444; P09 Book II")
    attribution = {LillyP3State.PRESENT: "reported_rejected_by_lilly", LillyP3State.ABSENT: "absent"}.get(
        placement.state, "not_evaluable")
    if placement.state is LillyP3State.ABSENT:
        state = LillyRouteState.ABSENT
    elif placement.state is LillyP3State.NOT_EVALUABLE:
        state = LillyRouteState.NOT_EVALUABLE
    else:
        state = LillyRouteState.NOT_EVALUABLE if moon_translation is None else moon_translation.state
    legs = () if moon_translation is None else moon_translation.leg_ids
    blocking = moon_translation.blocking_ids if state is LillyRouteState.BLOCKED else ()
    effects = moon_translation.effects if state is LillyRouteState.BLOCKED else ()
    return LillyRouteRecord(LillyRouteKind.DWELLING, state, reading.value, actors, legs, blocking, effects, (placement,),
                            moon_translation.completion if state is LillyRouteState.COMPLETE else None,
                            attribution=attribution, source_reference=_SOURCE + "pp.126-127; P09")


# ---------------------------------------------------------------------- blocker evaluators

def lilly_prohibition(reading: LillyProhibitionReading, *, intended: LillyRouteEvent,
                      third_relation: LillyThirdRelation | None, contacts: tuple[LillyThirdContact, ...],
                      coverage: LillyCoverageState) -> LillyBlockerRecord:
    """B01/B02 under an explicitly selected reading; a separating third is a translator."""
    _typed(reading, LillyProhibitionReading, "prohibition reading")
    _typed(intended, LillyRouteEvent, "intended contact")
    _typed(third_relation, LillyThirdRelation, "third relation", optional=True)
    _rows(contacts, LillyThirdContact, "third contacts")
    role = {LillyThirdRelation.APPLYING: "prohibitor_candidate",
            LillyThirdRelation.SEPARATING: "translator_candidate"}.get(third_relation, "not_evaluable")
    ids, kind = (), None
    if third_relation is LillyThirdRelation.APPLYING:
        early = [c for c in contacts if _order(c.time, intended.time) == "before"]
        modes = {c.mode for c in early}
        kind = None if not modes else "mixed" if len(modes) == 2 else {"body": "bodily", "aspect": "aspect"}[modes.pop()]
        if reading is LillyProhibitionReading.INTERPOSITION_TO_EITHER:
            orders = [_order(c.time, intended.time) for c in contacts]
            state = (LillyP3State.PRESENT if "before" in orders else LillyP3State.NOT_EVALUABLE
                     if "overlap" in orders or not _complete(coverage) else LillyP3State.ABSENT)
            ids = tuple(sorted(c.event_id for c in early)) if state is LillyP3State.PRESENT else ()
        else:
            states, found = [], []
            for a in (c for c in contacts if c.principal == "applying"):
                for h in (c for c in contacts if c.principal == "heavier"):
                    if _order(a.time, h.time) == "before" and _order(h.time, intended.time) == "before":
                        states.append(LillyP3State.PRESENT)
                        found.extend((a.event_id, h.event_id))
                    elif ("after" in (_order(a.time, h.time),) or _order(intended.time, h.time) == "before"
                          or _order(intended.time, a.time) == "before"):
                        states.append(LillyP3State.ABSENT)
                    else:
                        states.append(LillyP3State.NOT_EVALUABLE)
            state = (LillyP3State.PRESENT if LillyP3State.PRESENT in states else LillyP3State.NOT_EVALUABLE
                     if LillyP3State.NOT_EVALUABLE in states or not _complete(coverage) else LillyP3State.ABSENT)
            ids = tuple(sorted(set(found)))
    else:
        state = LillyP3State.ABSENT if third_relation is LillyThirdRelation.SEPARATING else LillyP3State.NOT_EVALUABLE
    blocker = ("prohibition_bodily" if kind == "bodily" else "prohibition_aspect" if kind == "aspect"
               else "prohibition")
    return LillyBlockerRecord(blocker, reading.value, state, ids, "hindered_and_retarded", role, kind,
                              source_reference=_SOURCE + "pp.110-111; B01, B02")


def lilly_refranation(reading: LillyRefranationReading, *, application_established: LillyP3State,
                      station: LillyRouteStation | None, exact_contact: LillyRouteEvent | None,
                      coverage: LillyCoverageState) -> LillyBlockerRecord:
    """B03: a principal stations during an established application before exactitude.

Under ``APPLYING_PRINCIPAL`` (p.111) only the applying planet's station
refrains; under ``EITHER_PRINCIPAL`` (p.317) either principal's does.
"""
    _typed(reading, LillyRefranationReading, "refranation reading")
    if application_established not in (LillyP3State.PRESENT, LillyP3State.ABSENT, LillyP3State.NOT_EVALUABLE):
        raise ValueError("application premise must be present, absent or not evaluable")
    _typed(station, LillyRouteStation, "station", optional=True)
    _typed(exact_contact, LillyRouteEvent, "exact contact", optional=True)
    note = None
    if application_established is not LillyP3State.PRESENT:
        state = LillyP3State.ABSENT if application_established is LillyP3State.ABSENT else LillyP3State.NOT_EVALUABLE
    elif station is None:
        state = LillyP3State.ABSENT if _complete(coverage) else LillyP3State.NOT_EVALUABLE
    elif station.body_role == "heavier" and reading is LillyRefranationReading.APPLYING_PRINCIPAL:
        state, note = LillyP3State.ABSENT, "station_of_heavier_not_refranation"
    elif exact_contact is None:
        state = LillyP3State.PRESENT
    else:
        state = {"before": LillyP3State.PRESENT, "after": LillyP3State.ABSENT,
                 "overlap": LillyP3State.NOT_EVALUABLE}[_order(station.time, exact_contact.time)]
    ids = (station.event_id,) if station is not None and state is LillyP3State.PRESENT else ()
    pages = "p.111; B03" if reading is LillyRefranationReading.APPLYING_PRINCIPAL else "pp.111, 317; B03 Book II"
    return LillyBlockerRecord("refranation", reading.value, state, ids, "never_effected", note=note,
                              source_reference=_SOURCE + pages)


def lilly_frustration(reading: LillyFrustrationReading, *, intended_aspect: str,
                      application_established: LillyP3State, heavier_contact: LillyThirdConjunction | None,
                      intended_contact: LillyRouteEvent | None, coverage: LillyCoverageState) -> LillyBlockerRecord:
    """B04: the heavier principal joins a third before the intended contact.

Under ``CONJUNCTION_ONLY`` (pp.112-113) both contacts are bodily; under
``CONJUNCTION_OR_ASPECT`` (Book II, pp.220, 305, 373) either may be an aspect.
"""
    _typed(reading, LillyFrustrationReading, "frustration reading")
    if intended_aspect not in _ASPECTS:
        raise ValueError("unknown intended aspect")
    _typed(heavier_contact, LillyThirdConjunction, "heavier contact", optional=True)
    _typed(intended_contact, LillyRouteEvent, "intended contact", optional=True)
    bodily = reading is LillyFrustrationReading.CONJUNCTION_ONLY
    if (bodily and intended_aspect != "conjunction") or application_established is LillyP3State.ABSENT:
        state = LillyP3State.ABSENT
    elif application_established is not LillyP3State.PRESENT:
        state = LillyP3State.NOT_EVALUABLE
    elif heavier_contact is None:
        state = LillyP3State.ABSENT if _complete(coverage) else LillyP3State.NOT_EVALUABLE
    elif bodily and heavier_contact.aspect != "conjunction":
        state = LillyP3State.ABSENT
    elif intended_contact is None:
        state = LillyP3State.PRESENT
    else:
        state = {"before": LillyP3State.PRESENT, "after": LillyP3State.ABSENT,
                 "overlap": LillyP3State.NOT_EVALUABLE}[_order(heavier_contact.time, intended_contact.time)]
    ids = (heavier_contact.event_id,) if state is LillyP3State.PRESENT else ()
    pages = "pp.112-113; B04" if bodily else "pp.112-113, 220, 305, 373; B04 Book II"
    return LillyBlockerRecord("frustration", reading.value, state, ids, "third_party_gains",
                              source_reference=_SOURCE + pages)


def lilly_heavier(body_a: str, body_b: str, reading: LillyHeavinessReading, *,
                  abs_speed_a: float | None = None, abs_speed_b: float | None = None) -> str | None:
    """H01: the heavier body under the reading, or ``None`` when unresolved."""
    _planet(body_a)
    _planet(body_b)
    if body_a == body_b:
        raise ValueError("heaviness compares two distinct planets")
    _typed(reading, LillyHeavinessReading, "heaviness reading")
    if reading is LillyHeavinessReading.TRADITIONAL_ORDER:
        return body_a if _PLANETS.index(body_a) < _PLANETS.index(body_b) else body_b
    if reading is LillyHeavinessReading.INSTANTANEOUS_SPEED:
        speeds = []
        for value in (abs_speed_a, abs_speed_b):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("instantaneous speed reading needs two finite absolute speeds")
            speeds.append(float(value))
        return None if speeds[0] == speeds[1] else body_a if speeds[0] < speeds[1] else body_b
    if body_a in _SUPERIOR and body_b in _INFERIOR:
        return body_a
    if body_b in _SUPERIOR and body_a in _INFERIOR:
        return body_b
    return None


# ---------------------------------------------------------------------- chronology

@dataclass(frozen=True, slots=True)
class LillyRouteSummary:
    """K03/K04: every route kept, the earliest completions reported, no verdict."""
    route_ids: tuple[str, ...]
    earliest_complete_ids: tuple[str, ...]
    verdict: None = field(default=None, init=False)


def lilly_route_summary(routes: tuple[tuple[str, LillyRouteRecord], ...]) -> LillyRouteSummary:
    """Report earliest-completing routes by envelope; ties and overlaps are kept together."""
    if not isinstance(routes, tuple) or any(not isinstance(r, tuple) or len(r) != 2 for r in routes):
        raise TypeError("routes must be a tuple of (id, record) pairs")
    ids = [i for i, _ in routes]
    _strings(tuple(ids), "route IDs")
    done = [(i, r) for i, r in routes if r.state is LillyRouteState.COMPLETE and r.completion is not None]
    earliest = sorted(i for i, r in done if not any(_order(o.completion, r.completion) == "before" for _, o in done))
    return LillyRouteSummary(tuple(ids), tuple(earliest))


@dataclass(frozen=True, slots=True)
class LillyContinuationReceipt:
    """K07: whether a later window may complete a route from earlier state."""
    state: LillyRouteState
    reasons: tuple[str, ...]


def lilly_continuation(*, first_window: LillyCoverageState, second_window: LillyCoverageState,
                       contact_window: int, frontier_carried: bool) -> LillyContinuationReceipt:
    """A route closing in a later window needs the carried frontier and complete coverage of both windows."""
    if contact_window not in (1, 2) or type(frontier_carried) is not bool:
        raise ValueError("contact window must be 1 or 2 and frontier_carried a bool")
    reasons = []
    if not _complete(first_window):
        reasons.append("first_window_incomplete")
    if contact_window == 2:
        if not frontier_carried:
            reasons.append("frontier_discarded")
        if not _complete(second_window):
            reasons.append("second_window_incomplete")
    return LillyContinuationReceipt(LillyRouteState.NOT_EVALUABLE if reasons else LillyRouteState.COMPLETE,
                                    tuple(reasons))


# ---------------------------------------------------------------------- trace layer

@dataclass(frozen=True, slots=True)
class LillyPerfectionSearchPolicy:
    """Numerical work and resolution policy; never an astrological duration rule."""
    past_days: float = 30.
    future_days: float = 30.
    step_days: float = .125
    time_tolerance_seconds: float = .5
    angular_tolerance_deg: float = 1e-7
    rate_tolerance_deg_per_day: float = 1e-6
    longitude_curvature_tolerance_deg: float = .1
    rate_curvature_tolerance_deg_per_day: float = .01
    velocity_step_days: float = .01
    max_position_evaluations: int = 400000
    max_subdivisions: int = 50000
    max_depth: int = 16
    policy_id: str = field(default="moira_lilly_p4_bounded_scan_v1", init=False)
    assurance: str = field(default="bounded_adaptive_scan_not_interval_certification", init=False)

    def __post_init__(self):
        for name in ("past_days", "future_days", "step_days", "time_tolerance_seconds", "angular_tolerance_deg",
                     "rate_tolerance_deg_per_day", "longitude_curvature_tolerance_deg",
                     "rate_curvature_tolerance_deg_per_day", "velocity_step_days"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a positive finite number")
            object.__setattr__(self, name, float(value))
        if self.past_days + self.future_days > 400 or self.step_days > 1:
            raise ValueError("study is bounded to 400 days and step to one day")
        if self.time_tolerance_seconds / 86400 >= self.step_days / 8:
            raise ValueError("time resolution must be smaller than the scan step")
        for name in ("max_position_evaluations", "max_subdivisions", "max_depth"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class LillyPairContact:
    """One exact contact between two planets; the angle is ``body_a - body_b``."""
    event_id: str
    body_a: str
    body_b: str
    directed_angle_deg: float
    time: LillyTimeInterval

    def __post_init__(self):
        _text(self.event_id, "contact ID")
        _planet(self.body_a)
        _planet(self.body_b)
        if self.body_a == self.body_b or self.directed_angle_deg not in _ASPECT_OF:
            raise ValueError("contact needs two planets and a classical directed target")
        _typed(self.time, LillyTimeInterval, "contact time")

    @property
    def aspect(self) -> str:
        """Return the aspect name."""
        return _ASPECT_OF[self.directed_angle_deg]

    def involves(self, body: str) -> bool:
        """Return whether ``body`` takes part."""
        return body in (self.body_a, self.body_b)

    def other(self, body: str) -> str:
        """Return the partner of ``body``."""
        if not self.involves(body):
            raise ValueError("body is not part of this contact")
        return self.body_b if body == self.body_a else self.body_a

    def angle_from(self, body: str) -> float:
        """Return the directed angle measured from ``body`` to its partner."""
        return self.directed_angle_deg if body == self.body_a else (-self.directed_angle_deg) % 360.


@dataclass(frozen=True, slots=True)
class LillyBodyStation:
    """A verified sign change of one planet's longitude rate."""
    event_id: str
    body: str
    direction: str
    time: LillyTimeInterval

    def __post_init__(self):
        _text(self.event_id, "station ID")
        _planet(self.body)
        if self.direction not in ("retrograde", "direct"):
            raise ValueError("station direction must be retrograde or direct")
        _typed(self.time, LillyTimeInterval, "station time")


@dataclass(frozen=True, slots=True)
class LillyBodyIngress:
    """A verified sign crossing of one planet."""
    event_id: str
    body: str
    time: LillyTimeInterval
    sign_before: int
    sign_after: int

    def __post_init__(self):
        _text(self.event_id, "ingress ID")
        _planet(self.body)
        _typed(self.time, LillyTimeInterval, "ingress time")
        if any(type(s) is not int or not 0 <= s < 12 for s in (self.sign_before, self.sign_after)):
            raise ValueError("ingress signs must be zero-based zodiac signs")


@dataclass(frozen=True, slots=True)
class LillyBodyMotion:
    """One planet's longitude and longitude rate at the query (same product)."""
    body: str
    longitude_deg: float
    rate_deg_per_day: float


@dataclass(frozen=True, slots=True)
class LillyPerfectionTrace:
    """Contacts, stations and ingresses of the seven planets over a declared study."""
    context: LillySnapshotContext
    provenance: LillyMoonProvenance
    study: LillyTimeInterval
    motions: tuple[LillyBodyMotion, ...]
    contacts: tuple[LillyPairContact, ...]
    stations: tuple[LillyBodyStation, ...]
    ingresses: tuple[LillyBodyIngress, ...]
    coverage: LillyMoonCoverage
    scan_receipts: tuple[LillyMoonScanReceipt, ...] = ()
    position_evaluations: int = 0
    search_policy: LillyPerfectionSearchPolicy | None = None
    continuation: LillyContinuationReceipt | None = None
    profile_id: str = field(default=_PROFILE, init=False)

    def __post_init__(self):
        if not isinstance(self.context, LillySnapshotContext) or self.context.jd_ut is None:
            raise ValueError("a dated Lilly snapshot context is required")
        _typed(self.provenance, LillyMoonProvenance, "provenance")
        _typed(self.study, LillyTimeInterval, "study")
        if not self.study.low <= self.context.jd_ut < self.study.high:
            raise ValueError("study must contain the query")
        if tuple(m.body for m in self.motions) != _PLANETS:
            raise ValueError("motions must list the seven planets in traditional order")
        ids = []
        for name, cls in (("contacts", LillyPairContact), ("stations", LillyBodyStation), ("ingresses", LillyBodyIngress)):
            rows = getattr(self, name)
            if not isinstance(rows, tuple) or any(not isinstance(r, cls) for r in rows):
                raise TypeError(f"{name} must be an immutable tuple of {cls.__name__}")
            ids.extend(r.event_id for r in rows)
            object.__setattr__(self, name, tuple(sorted(rows, key=lambda r: (r.time.low, r.event_id))))
        if len(ids) != len(set(ids)):
            raise ValueError("trace event IDs must be distinct")
        _typed(self.coverage, LillyMoonCoverage, "coverage")

    def motion(self, body: str) -> LillyBodyMotion:
        """Return one planet's motion at the query."""
        return next(m for m in self.motions if m.body == body)


def _difference(a, b):
    return (a - b + 180.) % 360. - 180.


class _PositionBudget(RuntimeError):
    """Request-local exhaustion signal; never interpreted as absent evidence."""


def trace_lilly_perfection(context: LillySnapshotContext, *, longitude_at, provenance: LillyMoonProvenance,
                           policy: LillyPerfectionSearchPolicy = LillyPerfectionSearchPolicy()) -> LillyPerfectionTrace:
    """Derive contacts, stations and ingresses from one explicitly identified longitude product.

The callable takes ``(body, jd_ut1)`` and returns normalized longitude. Its
exceptions propagate; resource exhaustion keeps earlier evidence and marks
coverage partial.
"""
    if not isinstance(context, LillySnapshotContext) or context.jd_ut is None:
        raise ValueError("a dated Lilly snapshot context is required")
    _typed(provenance, LillyMoonProvenance, "provenance")
    _typed(policy, LillyPerfectionSearchPolicy, "policy")
    if not callable(longitude_at):
        raise TypeError("longitude_at must be callable")
    q = context.jd_ut
    low, high = q - policy.past_days, q + policy.future_days
    study = LillyTimeInterval(low, high)
    tol = policy.time_tolerance_seconds / 86400
    pad = max(4 * tol, 4 * math.ulp(q), 4 * math.ulp(low), 4 * math.ulp(high))
    cache, reasons, receipts = {}, set(), []
    contacts, stations, ingresses = [], [], []

    def position(body, jd):
        key = body, jd
        if key not in cache:
            if len(cache) >= policy.max_position_evaluations:
                raise _PositionBudget
            value = float(longitude_at(body, jd))
            if not math.isfinite(value) or not 0 <= value < 360:
                raise ValueError("longitude_at must return a normalized finite longitude")
            cache[key] = value
        return cache[key]

    def envelope(t):
        return LillyTimeInterval(max(low, t - pad), min(high, t + pad))

    scanner = _FixedScanPolicy(policy.step_days, tol, policy.angular_tolerance_deg,
                               policy.longitude_curvature_tolerance_deg, policy.max_position_evaluations,
                               policy.max_subdivisions, policy.max_depth,
                               min(policy.velocity_step_days, policy.step_days / 8), policy.rate_tolerance_deg_per_day)

    def scan(function, targets, label):
        result = _scan_fixed_aspects(function, targets, ((low, high, "study_start", "study_end"),), scanner)
        receipts.append(LillyMoonScanReceipt(label, result.complete, result.evaluations, result.subdivisions,
                                             tuple(LillyTimeInterval(a, b) for a, b in result.scanned_intervals),
                                             result.reasons))
        if not result.complete:
            reasons.update(f"{label}:{r}" for r in result.reasons)
        return result

    def rate(function, t):
        h = min(policy.velocity_step_days, policy.step_days / 8, (high - low) / 8)
        if t - h < low:
            return (4 * _difference(function(t + h), function(t)) - _difference(function(t + 2 * h), function(t))) / (2 * h)
        if t + h > high:
            return (-4 * _difference(function(t - h), function(t)) + _difference(function(t - 2 * h), function(t))) / (2 * h)
        return _difference(function(t + h), function(t - h)) / (2 * h)

    def station_roots(body):
        def f(t):
            return position(body, t)
        count = math.ceil((high - low) / policy.step_days)
        if count > policy.max_position_evaluations:
            raise _PositionBudget
        pending = [(low + (high - low) * i / count, low + (high - low) * (i + 1) / count, 0) for i in range(count)]
        subdivisions = 0
        while pending:
            a, b, depth = pending.pop()
            m = a / 2 + b / 2
            ra, rm, rb = (rate(f, t) for t in (a, m, b))
            if abs(ra - 2 * rm + rb) > policy.rate_curvature_tolerance_deg_per_day:
                if depth >= policy.max_depth or subdivisions >= policy.max_subdivisions or m in (a, b):
                    reasons.add(body + ":station_partition_incomplete")
                else:
                    subdivisions += 1
                    pending.extend(((a, m, depth + 1), (m, b, depth + 1)))
                    continue
            for u, v, ru, rv in ((a, m, ra, rm), (m, b, rm, rb)):
                if abs(ru) <= policy.rate_tolerance_deg_per_day and low < u:
                    # A root on a knot: confirm the sign change on both sides.
                    d = min(policy.step_days / 8, (u - low) / 2, (high - u) / 2)
                    left, right = rate(f, u - d), rate(f, u + d)
                    if left * right < 0:
                        stations.append(LillyBodyStation(f"station:{body}:{u.hex()}", body,
                                                         "retrograde" if right < 0 else "direct", envelope(u)))
                    else:
                        reasons.add(body + ":station_at_numerical_stationary_limit")
                    continue
                if ru * rv < 0 and abs(rv) > policy.rate_tolerance_deg_per_day:
                    try:
                        t = _bisect_scalar(lambda x: rate(f, x), u, v, tol, policy.rate_tolerance_deg_per_day)
                    except ValueError:
                        reasons.add(body + ":station_root_unresolved")
                        continue
                    stations.append(LillyBodyStation(f"station:{body}:{t.hex()}", body,
                                                     "retrograde" if rv < 0 else "direct", envelope(t)))

    def crossings(body):
        def f(t):
            return position(body, t)
        result = scan(f, tuple((0., float(a), 0.) for a in range(0, 360, 30)), body + ":ingress")
        for hit in result.passes:
            t, angle = hit.jd_ut1, hit.directed_angle_deg
            h = min(.001, (t - low) / 2, (high - t) / 2)
            if h <= 0:
                reasons.add(body + ":ingress_at_study_edge")
                continue
            left, right = _difference(f(t - h), angle), _difference(f(t + h), angle)
            if left * right >= 0:
                continue
            boundary = int(angle / 30)
            before, after = ((boundary - 1) % 12, boundary) if right > left else (boundary, (boundary - 1) % 12)
            ingresses.append(LillyBodyIngress(f"ingress:{body}:{angle:g}:{t.hex()}", body, envelope(t), before, after))

    motions = []
    try:
        for body in _PLANETS:
            motions.append(LillyBodyMotion(body, position(body, q), rate(lambda t, b=body: position(b, t), q)))
        for body in _PLANETS:
            crossings(body)
            if body not in ("Sun", "Moon"):
                station_roots(body)
        for i, a in enumerate(_PLANETS):
            for b in _PLANETS[i + 1:]:
                def relative(t, a=a, b=b):
                    return position(a, t) - position(b, t)
                result = scan(relative, tuple((0., angle, 0.) for angle in _TARGETS), f"{a}-{b}:aspect")
                for hit in result.passes:
                    contacts.append(LillyPairContact(f"contact:{a}:{b}:{hit.directed_angle_deg:g}:{hit.jd_ut1.hex()}",
                                                     a, b, float(hit.directed_angle_deg), envelope(hit.jd_ut1)))
    except _PositionBudget:
        reasons.add("position_budget_exhausted")
    if len(motions) != len(_PLANETS):
        raise RuntimeError("position budget too small for the query motions")
    reason_tuple = tuple(sorted(reasons))
    coverage = LillyMoonCoverage(study, LillyCoverageState.PARTIAL if reason_tuple else LillyCoverageState.COMPLETE,
                                 provenance.source_id, reason_tuple, policy.assurance)
    return LillyPerfectionTrace(context, provenance, study, tuple(motions), tuple(contacts), tuple(stations),
                                tuple(ingresses), coverage, tuple(receipts), len(cache), policy)


def lilly_merge_perfection_traces(first: LillyPerfectionTrace, second: LillyPerfectionTrace) -> LillyPerfectionTrace:
    """K07: join two contiguous traces of one product, carrying the first window's events.

The merged trace keeps the first trace's query and motions. Events found in
both windows near the shared boundary are kept once per identifier.
"""
    _typed(first, LillyPerfectionTrace, "first trace")
    _typed(second, LillyPerfectionTrace, "second trace")
    if first.provenance != second.provenance or first.context.is_day_chart != second.context.is_day_chart:
        raise ValueError("merged traces must share one provenance and sect")
    if not first.study.low < second.study.low <= first.study.high < second.study.high:
        raise ValueError("second trace must continue the first without a gap")
    receipt = lilly_continuation(first_window=first.coverage.state, second_window=second.coverage.state,
                                 contact_window=2, frontier_carried=True)
    reasons = tuple(sorted(set(first.coverage.reasons) | set(second.coverage.reasons)))
    study = LillyTimeInterval(first.study.low, second.study.high)
    coverage = LillyMoonCoverage(study, LillyCoverageState.PARTIAL if reasons else LillyCoverageState.COMPLETE,
                                 first.coverage.source_id, reasons, first.coverage.assurance)

    def union(a, b):
        seen = {r.event_id: r for r in a}
        for r in b:
            if r.event_id not in seen and not any(
                    type(r) is type(o) and _same_event(r, o) for o in seen.values()):
                seen[r.event_id] = r
        return tuple(seen.values())

    return LillyPerfectionTrace(first.context, first.provenance, study, first.motions,
                                union(first.contacts, second.contacts), union(first.stations, second.stations),
                                union(first.ingresses, second.ingresses), coverage,
                                first.scan_receipts + second.scan_receipts,
                                first.position_evaluations + second.position_evaluations, first.search_policy, receipt)


def _same_event(a, b):
    if _order(a.time, b.time) != "overlap":
        return False
    if isinstance(a, LillyPairContact):
        return (a.body_a, a.body_b, a.directed_angle_deg) == (b.body_a, b.body_b, b.directed_angle_deg)
    if isinstance(a, LillyBodyStation):
        return (a.body, a.direction) == (b.body, b.direction)
    return (a.body, a.sign_before, a.sign_after) == (b.body, b.sign_before, b.sign_after)


# ---------------------------------------------------------------------- trace to routes

@dataclass(frozen=True, slots=True)
class LillyPerfectionReadings:
    """Every textual alternative, selected explicitly by the caller (no defaults)."""
    translation: LillyTranslationReading
    prohibition: LillyProhibitionReading
    malevolent: LillyMalevolentReading
    beholding: LillyBeholdingReading
    heaviness: LillyHeavinessReading
    refranation: LillyRefranationReading
    frustration: LillyFrustrationReading
    collection: LillyCollectionReading
    dwelling: LillyDwellingReading

    def __post_init__(self):
        for name, cls in _READING_FIELDS:
            _typed(getattr(self, name), cls, name)


_READING_FIELDS = (("translation", LillyTranslationReading), ("prohibition", LillyProhibitionReading),
                   ("malevolent", LillyMalevolentReading), ("beholding", LillyBeholdingReading),
                   ("heaviness", LillyHeavinessReading), ("refranation", LillyRefranationReading),
                   ("frustration", LillyFrustrationReading), ("collection", LillyCollectionReading),
                   ("dwelling", LillyDwellingReading))

#: The readings Lilly's Book II judgements attest (LILLY_P4_BOOK_II_COLLATION_2026-10-30).
#: A named selection the caller passes explicitly; never applied by default.
LILLY_BOOK_II_PRACTICE = LillyPerfectionReadings(
    translation=LillyTranslationReading.BOOK_II_PRACTICE,
    prohibition=LillyProhibitionReading.INTERPOSITION_TO_EITHER,
    malevolent=LillyMalevolentReading.MALEFIC_OR_EVIL_LORD,
    beholding=LillyBeholdingReading.NOT_REQUIRED,
    heaviness=LillyHeavinessReading.TRADITIONAL_ORDER,
    refranation=LillyRefranationReading.EITHER_PRINCIPAL,
    frustration=LillyFrustrationReading.CONJUNCTION_OR_ASPECT,
    collection=LillyCollectionReading.BOOK_II_PRACTICE,
    dwelling=LillyDwellingReading.BOOK_II_ROUTE,
)


@dataclass(frozen=True, slots=True)
class LillyRouteConditions:
    """Caller-supplied source conditions (Q01); anything not supplied stays unknown.

``planet_house_classes`` gives each listed planet's house class (cadency of a
translator or collector), ``evil_house_lords`` the lords of the sixth, eighth
and twelfth, and ``impedited_planets`` the planets the caller judges impeded
(p.186); ``None`` or an unlisted planet is unknown.
"""
    house_class: LillyHouseClass | None = None
    good_houses: LillyRouteCondition | None = None
    well_dignified: LillyRouteCondition | None = None
    querent_degree_dignity: LillyRouteCondition | None = None
    quesited_degree_dignity: LillyRouteCondition | None = None
    proper_good_houses: LillyRouteCondition | None = None
    friendly_houses: LillyRouteCondition | None = None
    moon_condition: LillyRouteCondition | None = None
    dwelling_placement: LillyRouteCondition | None = None
    planet_house_classes: tuple[tuple[str, LillyHouseClass], ...] = ()
    evil_house_lords: tuple[str, ...] | None = None
    impedited_planets: tuple[str, ...] | None = None

    def __post_init__(self):
        _typed(self.house_class, LillyHouseClass, "house class", optional=True)
        for name in ("good_houses", "well_dignified", "querent_degree_dignity", "quesited_degree_dignity",
                     "proper_good_houses", "friendly_houses", "moon_condition", "dwelling_placement"):
            _typed(getattr(self, name), LillyRouteCondition, name, optional=True)
        if not isinstance(self.planet_house_classes, tuple) or any(
                not isinstance(r, tuple) or len(r) != 2 or not isinstance(r[1], LillyHouseClass)
                for r in self.planet_house_classes):
            raise TypeError("planet house classes must be a tuple of (planet, LillyHouseClass) pairs")
        bodies = [b for b, _ in self.planet_house_classes]
        for name, rows in (("planet house classes", bodies), ("evil house lords", self.evil_house_lords or ()),
                           ("impedited planets", self.impedited_planets or ())):
            for body in rows:
                _planet(body)
            if len(set(rows)) != len(rows):
                raise ValueError(f"{name} must name distinct planets")
        for name in ("evil_house_lords", "impedited_planets"):
            if getattr(self, name) is not None and not isinstance(getattr(self, name), tuple):
                raise TypeError(f"{name} must be a tuple or None")

    def get(self, name: str) -> LillyRouteCondition:
        """Return a supplied condition or an explicit unknown."""
        return getattr(self, name) or _unknown(name)

    def house_class_of(self, body: str) -> LillyHouseClass | None:
        """Return a planet's supplied house class, or ``None`` when unknown."""
        return dict(self.planet_house_classes).get(body)

    def member(self, name: str, body: str) -> bool | None:
        """Membership of ``body`` in a supplied planet list, or ``None`` when the list is unknown."""
        rows = getattr(self, name)
        return None if rows is None else body in rows


@dataclass(frozen=True, slots=True)
class LillyPrincipalRelation:
    """The principals' relation at the query: aspect, residual, orb and motion."""
    aspect: str | None
    directed_angle_deg: float | None
    residual_deg: float | None
    within_moiety: bool
    motion: str


@dataclass(frozen=True, slots=True)
class LillyPerfectionRoutes:
    """Every route and blocker for one principal pair; no verdict and no ranking."""
    trace: LillyPerfectionTrace
    querent: str
    quesited: str
    readings: LillyPerfectionReadings
    relation: LillyPrincipalRelation
    routes: tuple[tuple[str, LillyRouteRecord], ...]
    blockers: tuple[tuple[str, LillyBlockerRecord], ...]
    summary: LillyRouteSummary
    profile_id: str = field(default=_PROFILE, init=False)
    verdict: None = field(default=None, init=False)


def _relation(trace, a, b, context):
    """Nearest directed target at the query, with residual, moiety and approach."""
    ma, mb = trace.motion(a), trace.motion(b)
    rel = _difference(ma.longitude_deg, mb.longitude_deg) % 360.
    rate = ma.rate_deg_per_day - mb.rate_deg_per_day
    best = min(_TARGETS, key=lambda angle: abs(_difference(rel, angle)))
    residual = _difference(rel, best)
    moiety = lilly_orb_evidence(a, b, 0., context=context).combined_moiety_deg
    if residual == 0:
        motion = "exact"
    else:
        motion = "applying" if residual * rate < 0 else "separating"
    return LillyPrincipalRelation(_ASPECT_OF[best], best, residual, abs(residual) < moiety, motion)


def _contacts(trace, a, b):
    return tuple(c for c in trace.contacts if c.involves(a) and c.involves(b))


def _event(contact):
    return None if contact is None else LillyRouteEvent(contact.event_id, contact.time)


def _bases(host, guest, trace):
    """P2 reception: host's dignity at the guest's query position."""
    position = lilly_position_from_longitude(guest, trace.motion(guest).longitude_deg)
    snapshot = lilly_condition_snapshot(position, context=trace.context)
    return LillyReceptionBases.from_directed(LillyDirectedReception(host, snapshot))


def _received_either(a, b, trace):
    """Reception in either direction between two planets at the query (P2)."""
    states = (_bases(a, b, trace).received(), _bases(b, a, trace).received())
    return (LillyP3State.PRESENT if LillyP3State.PRESENT in states else LillyP3State.ABSENT
            if all(s is LillyP3State.ABSENT for s in states) else LillyP3State.NOT_EVALUABLE)


def _known(name, state, source, evidence, epoch=LillyConditionEpoch.QUESTION):
    return LillyRouteCondition(name, state, epoch, source, () if state is LillyP3State.NOT_EVALUABLE else evidence)


def _unimpeded(body, role, trace, conditions):
    """Book II: not retrograde, not combust, not cadent at the query (pp.317-318, 433-434, 446)."""
    rate = trace.motion(body).rate_deg_per_day
    retrograde = LillyP3State.ABSENT if rate < 0 else LillyP3State.PRESENT
    combustion = lilly_solar_proximity(body, trace.motion("Sun").longitude_deg, trace.motion(body).longitude_deg,
                                       context=trace.context).combustion
    combust = {LillyP3State.PRESENT: LillyP3State.ABSENT,
               LillyP3State.NOT_EVALUABLE: LillyP3State.NOT_EVALUABLE}.get(combustion, LillyP3State.PRESENT)
    house = conditions.house_class_of(body)
    cadent = (LillyP3State.NOT_EVALUABLE if house is None else LillyP3State.ABSENT
              if house is LillyHouseClass.CADENT else LillyP3State.PRESENT)
    return (_known(f"{role}_not_retrograde", retrograde, "trace_motion", ("motions",)),
            _known(f"{role}_not_combust", combust, "P3_C06_solar_proximity", ("motions",)),
            _known(f"{role}_not_cadent", cadent, "caller_house_class", (f"house_class:{body}",)))


def _infortune_state(body, conditions):
    """p.186: a malefic, or a planet the caller lists as impeded ("infortunate")."""
    if body in _MALEFICS:
        return LillyP3State.PRESENT
    impeded = conditions.member("impedited_planets", body)
    return LillyP3State.NOT_EVALUABLE if impeded is None else LillyP3State.PRESENT if impeded else LillyP3State.ABSENT


def _infortune_received(translator, receiver, trace, conditions):
    """p.186: an impeded infortune receiving the light spoils it "unlesse ... againe received".

"Againe received" is read as the translator receiving the infortune (P2,
any dignity); that reading of the phrase is Moira's, recorded in the source.
"""
    name, source = "receiving_infortune_received", "p186_translator_receives_infortune"
    if receiver not in _MALEFICS:
        return _known(name, LillyP3State.PRESENT, source, ("receiver_not_infortune",))
    received = _bases(translator, receiver, trace).received()
    impeded = conditions.member("impedited_planets", receiver)
    if received is LillyP3State.PRESENT or impeded is False:
        state = LillyP3State.PRESENT
    elif impeded is True and received is LillyP3State.ABSENT:
        state = LillyP3State.ABSENT
    else:
        state = LillyP3State.NOT_EVALUABLE
    return _known(name, state, source, ("reception", f"impedited:{receiver}"))


def _stays_in_sign(body, legs, trace, coverage):
    """pp.433-434, 446: the collector does not "goe out of that Signe" before both legs."""
    name, source = "collector_stays_in_sign", "trace_ingresses"
    if None in legs:
        return _unknown(name, LillyConditionEpoch.LEG_START)
    last = max((leg.time for leg in legs), key=lambda t: t.high)
    orders = [_order(i.time, last) for i in trace.ingresses if i.body == body and i.time.low > trace.context.jd_ut]
    state = (LillyP3State.ABSENT if "before" in orders else LillyP3State.NOT_EVALUABLE
             if "overlap" in orders or not _complete(coverage) else LillyP3State.PRESENT)
    return _known(name, state, source, ("ingresses",), LillyConditionEpoch.LEG_START)


def _lighter_condition(body, others, trace, reading):
    states, evidence = [], []
    for other in others:
        heavier = lilly_heavier(body, other, reading, abs_speed_a=abs(trace.motion(body).rate_deg_per_day),
                                abs_speed_b=abs(trace.motion(other).rate_deg_per_day))
        states.append(LillyP3State.NOT_EVALUABLE if heavier is None else
                      LillyP3State.PRESENT if heavier == other else LillyP3State.ABSENT)
        evidence.append(f"heaviness:{reading.value}:{body}:{other}")
    state = _every(states)
    return LillyRouteCondition("translator_lighter_than_both", state, LillyConditionEpoch.QUESTION,
                               "H01:" + reading.value, () if state is LillyP3State.NOT_EVALUABLE else tuple(evidence))


def lilly_perfection_routes(trace: LillyPerfectionTrace, querent: str, quesited: str, *,
                            readings: LillyPerfectionReadings,
                            conditions: LillyRouteConditions = LillyRouteConditions()) -> LillyPerfectionRoutes:
    """Derive every route and blocker for one principal pair from a trace.

The direct route uses the next exact contact of the principals' current
applying aspect. Translators are planets separating at the query from one
principal (from their last contact) whose next contact is with the other;
collectors are planets both principals contact next. Conditions not derivable
from the trace (house class, good houses, dignity in the degrees, the
opposition's Moon sequence, the dwelling placement) come from ``conditions``
and otherwise stay unknown.
"""
    _typed(trace, LillyPerfectionTrace, "trace")
    _planet(querent)
    _planet(quesited)
    if querent == quesited:
        raise ValueError("querent and quesited significators must differ")
    _typed(readings, LillyPerfectionReadings, "readings")
    _typed(conditions, LillyRouteConditions, "conditions")
    q, context, coverage = trace.context.jd_ut, trace.context, trace.coverage.state
    after = lambda c: c.time.low > q  # noqa: E731
    relation = _relation(trace, querent, quesited, context)
    heavier = lilly_heavier(querent, quesited, readings.heaviness,
                            abs_speed_a=abs(trace.motion(querent).rate_deg_per_day),
                            abs_speed_b=abs(trace.motion(quesited).rate_deg_per_day))
    applying = None if heavier is None else quesited if heavier == querent else querent
    routes, blockers = [], []
    actors = (querent, quesited)

    # ------------------------------------------------ direct route
    if relation.motion == "applying" and relation.within_moiety:
        angle = relation.directed_angle_deg
        intended = next((c for c in _contacts(trace, querent, quesited)
                         if after(c) and c.angle_from(querent) == angle), None)
        established = LillyP3State.PRESENT
    else:
        angle, intended, established = None, None, LillyP3State.ABSENT
    intended_event = _event(intended)
    route_blockers = []
    if established is LillyP3State.PRESENT and applying is not None:
        own = [s for s in trace.stations if s.direction == "retrograde" and s.time.low > q
               and s.body in (applying, heavier)]
        for s in own:
            role = "applying" if s.body == applying else "heavier"
            record = lilly_refranation(readings.refranation, application_established=established,
                                       station=LillyRouteStation(s.event_id, role, s.time),
                                       exact_contact=intended_event, coverage=coverage)
            blockers.append((f"refranation:{s.event_id}", record))
            if record.state is not LillyP3State.ABSENT:
                route_blockers.append(LillyRouteBlocker(s.event_id, LillyBlockerKind.REFRANATION, s.time,
                                                        resolved=record.state is LillyP3State.PRESENT))
        if not own:
            blockers.append(("refranation:none", lilly_refranation(
                readings.refranation, application_established=established, station=None,
                exact_contact=intended_event, coverage=coverage)))
        for third in (p for p in _PLANETS if p not in actors):
            rel = _relation(trace, third, applying, context)
            third_relation = (LillyThirdRelation.APPLYING if rel.motion == "applying" else
                              LillyThirdRelation.SEPARATING if rel.motion == "separating" else None)
            contacts = tuple(
                LillyThirdContact(c.event_id, "applying" if c.involves(applying) else "heavier",
                                  "body" if c.aspect == "conjunction" else "aspect", c.time)
                for c in trace.contacts if after(c) and c.involves(third) and (c.involves(applying) or c.involves(heavier))
                and (intended is None or c.time.low <= intended.time.high))
            if intended_event is None or not contacts:
                continue
            record = lilly_prohibition(readings.prohibition, intended=intended_event, third_relation=third_relation,
                                       contacts=contacts, coverage=coverage)
            blockers.append((f"prohibition:{third}", record))
            if record.state is not LillyP3State.ABSENT and record.event_ids:
                kind = (LillyBlockerKind.PROHIBITION_BODILY if record.contact_kind == "bodily"
                        else LillyBlockerKind.PROHIBITION_ASPECT)
                times = [c.time for c in contacts if c.event_id in record.event_ids]
                route_blockers.append(LillyRouteBlocker(f"prohibition:{third}", kind,
                                                        max(times, key=lambda t: t.high),
                                                        resolved=record.state is LillyP3State.PRESENT))
        by_aspect = readings.frustration is LillyFrustrationReading.CONJUNCTION_OR_ASPECT
        if by_aspect or relation.aspect == "conjunction":
            for c in trace.contacts:
                if (after(c) and c.involves(heavier) and not c.involves(applying)
                        and (by_aspect or c.aspect == "conjunction")):
                    # B04: the heavier principal joins a planet heavier still; a
                    # lighter planet catching it is a translator or prohibitor.
                    third = c.other(heavier)
                    still_heavier = lilly_heavier(heavier, third, readings.heaviness,
                                                  abs_speed_a=abs(trace.motion(heavier).rate_deg_per_day),
                                                  abs_speed_b=abs(trace.motion(third).rate_deg_per_day))
                    if still_heavier == heavier:
                        continue
                    record = lilly_frustration(readings.frustration, intended_aspect=relation.aspect,
                                               application_established=established if still_heavier == third
                                               else LillyP3State.NOT_EVALUABLE,
                                               heavier_contact=LillyThirdConjunction(c.event_id, c.aspect, c.time),
                                               intended_contact=intended_event, coverage=coverage)
                    blockers.append((f"frustration:{c.event_id}", record))
                    if record.state is not LillyP3State.ABSENT:
                        route_blockers.append(LillyRouteBlocker(c.event_id, LillyBlockerKind.FRUSTRATION, c.time,
                                                                resolved=record.state is LillyP3State.PRESENT))
    if established is LillyP3State.PRESENT:
        blocker_tuple = tuple(route_blockers)
        # Heaviness unresolved under the reading leaves blocker roles unknown,
        # so the blocker search counts as incomplete for the direct route.
        direct_coverage = coverage if applying is not None else LillyCoverageState.PARTIAL
        kind = relation.aspect
        if kind == "conjunction":
            record = lilly_conjunction_route(intended_event, house_class=conditions.house_class,
                                             blockers=blocker_tuple, coverage=direct_coverage, actors=actors,
                                             ingresses=tuple(LillyRouteEvent(i.event_id, i.time) for i in trace.ingresses
                                                             if i.body in actors and after(i) and (
                                                                 intended is None or i.time.high < intended.time.low)))
        elif kind in ("sextile", "trine"):
            interventions = []
            for c in trace.contacts:
                if not after(c) or c.aspect == "conjunction" or len({c.body_a, c.body_b} & set(actors)) != 1:
                    continue
                caster = c.body_b if c.body_a in actors else c.body_a
                principal = c.other(caster)
                received = None
                if readings.malevolent is LillyMalevolentReading.MALEFIC_OR_EVIL_LORD:
                    either = _received_either(caster, principal, trace)
                    received = None if either is LillyP3State.NOT_EVALUABLE else either is LillyP3State.PRESENT
                interventions.append(LillyAspectIntervention(
                    c.event_id, c.time, caster in _MALEFICS, c.aspect,
                    from_evil_lord=conditions.member("evil_house_lords", caster), received=received))
            interventions = tuple(interventions)
            record = lilly_sextile_trine_route(intended_event, aspect=kind, good_houses=conditions.get("good_houses"),
                                               well_dignified=conditions.get("well_dignified"),
                                               interventions=interventions, reading=readings.malevolent,
                                               coverage=direct_coverage, actors=actors)
        elif kind == "square":
            record = lilly_square_route(intended_event, querent_degree_dignity=conditions.get("querent_degree_dignity"),
                                        quesited_degree_dignity=conditions.get("quesited_degree_dignity"),
                                        proper_good_houses=conditions.get("proper_good_houses"),
                                        blockers=blocker_tuple, coverage=direct_coverage, actors=actors)
        else:
            mutual = lilly_reception_route(_bases(quesited, querent, trace), _bases(querent, quesited, trace))
            by_house = mutual.state is LillyRouteState.COMPLETE and mutual.qualifier == "strongest_by_house"
            house_state = (LillyP3State.PRESENT if by_house else LillyP3State.NOT_EVALUABLE
                           if mutual.state is LillyRouteState.NOT_EVALUABLE else LillyP3State.ABSENT)
            record = lilly_opposition_route(
                intended_event,
                mutual_house_reception=LillyRouteCondition("mutual_house_reception", house_state,
                                                           LillyConditionEpoch.QUESTION, "P2_directed_reception",
                                                           () if house_state is LillyP3State.NOT_EVALUABLE else ("mutual",)),
                friendly_houses=conditions.get("friendly_houses"), moon_condition=conditions.get("moon_condition"),
                blockers=blocker_tuple, coverage=direct_coverage, actors=actors)
        if kind in ("square", "opposition"):
            # P08 / p.317: reception qualifies a hard aspect ("with a little
            # difficulty", otherwise "onely hopes"); it never removes a blocker.
            reception = {LillyP3State.PRESENT: "with_reception", LillyP3State.ABSENT: "without_reception"}.get(
                _received_either(querent, quesited, trace), "reception_not_evaluable")
            record = _with(record, reasons=record.reasons + (f"reception_qualifier:{reception}",))
        unperfected = [b for b in blocker_tuple if b.resolved
                       and b.kind in (LillyBlockerKind.REFRANATION, LillyBlockerKind.FRUSTRATION)]
        if intended is None and unperfected and record.state in (LillyRouteState.ABSENT, LillyRouteState.NOT_EVALUABLE):
            # The established application ends in a station or interception with
            # no later exact contact (B03, B04, A19): blocked, not merely absent.
            record = _with(record, state=LillyRouteState.BLOCKED,
                           blocking_ids=tuple(sorted(b.event_id for b in unperfected)),
                           effects=tuple(sorted({b.kind.effect for b in unperfected})),
                           reasons=record.reasons + ("application_ended_without_contact",))
        routes.append((f"direct:{kind}", record))

    # ------------------------------------------------ translation
    principal_contacts = [c for c in _contacts(trace, querent, quesited) if c.time.high < q]
    if relation.motion == "applying":
        history = LillyP3State.ABSENT
    elif principal_contacts:
        history = (LillyP3State.PRESENT if principal_contacts[-1].aspect in ("conjunction", "sextile", "trine")
                   else LillyP3State.ABSENT)
    else:
        history = LillyP3State.NOT_EVALUABLE
    history_condition = LillyRouteCondition(
        "principals_separated_from_good_aspect", history, LillyConditionEpoch.QUESTION, "trace_contacts",
        () if history is LillyP3State.NOT_EVALUABLE else ((principal_contacts[-1].event_id,) if principal_contacts
                                                         else ("principal_relation",)))
    book_ii = readings.translation is LillyTranslationReading.BOOK_II_PRACTICE
    for third in (p for p in _PLANETS if p not in actors):
        for source, destination in ((querent, quesited), (quesited, querent)):
            past = [c for c in trace.contacts if c.involves(third) and c.involves(source) and c.time.high < q]
            motion = _relation(trace, third, source, context).motion
            meets = lambda c, start: (c.time.low > start and c.involves(third)  # noqa: E731
                                      and (c.involves(source) or c.involves(destination)))
            if past and motion == "separating":
                separation = past[-1]
                start = q
            elif book_ii and motion == "applying":
                # C13 (p.388): the translator still applies to the first
                # principal and carries its light on after that contact.
                separation = next((c for c in trace.contacts if meets(c, q)), None)
                if separation is None or not separation.involves(source):
                    continue
                start = separation.time.high
            else:
                continue
            # The translator's next meeting with either principal: a return to
            # the source is not a translation in this direction.
            second = next((c for c in trace.contacts if meets(c, start) and c is not separation), None)
            if second is not None and not second.involves(destination):
                continue
            intervening = tuple(LillyRouteEvent(c.event_id, c.time) for c in trace.contacts
                                if c.involves(third) and not c.involves(source) and not c.involves(destination)
                                and c.time.low > separation.time.high
                                and (second is None or c.time.low <= second.time.high))
            station = [s for s in trace.stations if s.body == third and s.direction == "retrograde" and s.time.low > q]
            extra = {}
            if book_ii:
                extra = {"translator_conditions": _unimpeded(third, "translator", trace, conditions),
                         "infortune_received": _infortune_received(third, destination, trace, conditions)}
            route = lilly_translation_route(
                readings.translation, separation=LillyRouteEvent(separation.event_id, separation.time),
                second_leg=_event(second),
                translator_lighter=_lighter_condition(third, (source, destination), trace, readings.heaviness),
                principals_prior_separation=history_condition, reception=_bases(source, third, trace),
                intervening_contacts=intervening,
                blockers=tuple(LillyRouteBlocker(s.event_id, LillyBlockerKind.REFRANATION, s.time) for s in station),
                coverage=coverage, actors=(third, source, destination), **extra)
            routes.append((f"translation:{third}:{source}->{destination}", route))

    # ------------------------------------------------ collection
    sign = lambda b: int(trace.motion(b).longitude_deg // 30)  # noqa: E731
    behold_by_sign = (sign(querent) - sign(quesited)) % 12 in (0, 2, 3, 4, 6, 8, 9, 10)
    behold_condition = lilly_condition("principals_behold_by_sign", behold_by_sign, epoch=LillyConditionEpoch.QUESTION,
                                       source="sign_relation_at_query", evidence_ids=("motions",))
    current_condition = lilly_condition("principals_current_aspect", relation.within_moiety,
                                        epoch=LillyConditionEpoch.QUESTION, source="P2_orb_policy",
                                        evidence_ids=("motions",))
    for collector in (p for p in _PLANETS if p not in actors):
        legs = []
        for principal in actors:
            if _relation(trace, principal, collector, context).motion != "applying":
                legs.append(None)
                continue
            legs.append(next((c for c in trace.contacts if after(c) and c.involves(principal) and c.involves(collector)),
                             None))
        if legs == [None, None]:
            continue
        heavier_state = _every(
            LillyP3State.NOT_EVALUABLE if h is None else LillyP3State.PRESENT if h == collector else LillyP3State.ABSENT
            for h in (lilly_heavier(collector, p, readings.heaviness,
                                    abs_speed_a=abs(trace.motion(collector).rate_deg_per_day),
                                    abs_speed_b=abs(trace.motion(p).rate_deg_per_day)) for p in actors))
        station = [LillyRouteBlocker(s.event_id, LillyBlockerKind.REFRANATION, s.time,
                                     "querent" if s.body == querent else "quesited")
                   for s in trace.stations if s.body in actors and s.direction == "retrograde" and s.time.low > q]
        extra = {}
        if readings.collection is LillyCollectionReading.BOOK_II_PRACTICE:
            extra = {"querent_received_by_collector": _bases(collector, querent, trace),
                     "quesited_received_by_collector": _bases(collector, quesited, trace),
                     "collector_infortune": _known("collector_infortune_or_impedited",
                                                   _infortune_state(collector, conditions), "p186_infortune",
                                                   (f"infortune:{collector}",)),
                     "collector_conditions": _unimpeded(collector, "collector", trace, conditions)
                     + (_stays_in_sign(collector, legs, trace, coverage),)}
        route = lilly_collection_route(
            readings.beholding, principals_behold_by_sign=behold_condition,
            principals_current_aspect=current_condition,
            collector_heavier=LillyRouteCondition("collector_heavier_than_both", heavier_state,
                                                  LillyConditionEpoch.QUESTION, "H01:" + readings.heaviness.value,
                                                  () if heavier_state is LillyP3State.NOT_EVALUABLE else ("motions",)),
            reception_by_querent=_bases(querent, collector, trace), reception_by_quesited=_bases(quesited, collector, trace),
            leg_querent=_event(legs[0]), leg_quesited=_event(legs[1]), blockers=tuple(station), coverage=coverage,
            actors=(querent, quesited, collector), collection=readings.collection, **extra)
        routes.append((f"collection:{collector}", route))

    # ------------------------------------------------ mutual reception and dwelling
    routes.append(("mutual_reception", lilly_reception_route(_bases(quesited, querent, trace),
                                                             _bases(querent, quesited, trace), actors=actors)))
    if conditions.dwelling_placement is not None:
        lunar = next((r for i, r in routes if i.startswith("translation:Moon:") and r.actors[1:] == (quesited, querent)),
                     None)
        routes.append(("dwelling", lilly_dwelling_route(conditions.dwelling_placement, lunar,
                                                        reading=readings.dwelling, actors=actors)))
    route_tuple = tuple(routes)
    return LillyPerfectionRoutes(trace, querent, quesited, readings, relation, route_tuple, tuple(blockers),
                                 lilly_route_summary(route_tuple))


def lilly_perfection_routes_at(context: LillySnapshotContext, querent: str, quesited: str, *, reader,
                        readings: LillyPerfectionReadings,
                        conditions: LillyRouteConditions = LillyRouteConditions(),
                        policy: LillyPerfectionSearchPolicy = LillyPerfectionSearchPolicy()) -> LillyPerfectionRoutes:
    """Trace the explicit reader's apparent geocentric tropical longitudes and derive routes.

The reader (an ``SpkReader`` or a ``KernelPool``) is mandatory; this surface
never acquires a kernel. Reduction is owned by ``planet_at`` exactly as for the
P3 lunar trace; provenance names the pool's primary planetary kernel.
"""
    from .planets import _default_apparent_longitude
    from .spk_reader import KernelPool, SpkReader
    from .julian import ut_to_tt

    if not isinstance(context, LillySnapshotContext) or context.jd_ut is None:
        raise ValueError("a dated Lilly snapshot context is required")
    if isinstance(reader, KernelPool):
        # A pool's planetary truth is its first content-identified planetary reader.
        primary, reader_kind = reader._primary_planetary_reader(), "kernel_pool"
    elif isinstance(reader, SpkReader):
        primary, reader_kind = reader, "spk_reader"
    else:
        raise TypeError("an explicit open SpkReader or KernelPool is required")
    identity = reader._ephemeris_kernel_identity_at(ut_to_tt(context.jd_ut))
    if identity is None or primary is None:
        raise ValueError("reader cannot identify a planetary/lunar product at the query")
    provenance = LillyMoonProvenance(
        str(primary.path), "geocentric_true_ecliptic_and_equinox_of_date",
        "planet_at:apparent_light_time_aberration_deflection_precession_nutation",
        "UT1_to_TT:moira.julian_canonical;TT_to_TDB:SPK_boundary",
        (("planetary_ephemeris", str(identity.planetary_ephemeris)),
         ("lunar_ephemeris", str(identity.lunar_ephemeris)),
         ("kernel_sha256", primary._source_identity.sha256),
         ("reader_kind", reader_kind),
         ("query_jd_ut1", repr(context.jd_ut)),
         ("query_jd_tt", repr(ut_to_tt(context.jd_ut))),
         ("delta_t_policy", "moira.julian_canonical_default")))
    # planet_at's longitude product without its unused speed differentiation;
    # scans sample several planets at one epoch, so a request-local memo lets
    # them share that epoch's apparent context.
    contexts: dict = {}

    def longitude_at(body, jd):
        return _default_apparent_longitude(body, jd, reader, contexts)

    trace = trace_lilly_perfection(context, longitude_at=longitude_at,
                                   provenance=provenance, policy=policy)
    return lilly_perfection_routes(trace, querent, quesited, readings=readings, conditions=conditions)

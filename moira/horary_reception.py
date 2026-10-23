"""Lilly 1647 condition snapshots and directed reception evidence.

Owns the finite DG01-DG08, OR01-OR05 and RC01-RC08 decisions in the
2026-10-23 Lilly packet. Authority: Christian Astrology (1647), printed
pp.102-105,107,110,112,115,126; Wellcome b30338724 and the collated EEBO
witness. Reuses Moira's source-owned dignity, triplicity and face tables.

Inputs are caller-supplied positions and explicit snapshot context. Missing
degree/sect remains unknown where it matters. No kernel, event search,
question-time inference, motion, judgement or historical reconstruction is
performed. The separate profile does not change horary/perfection v1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
import math
from types import MappingProxyType

from ._strenum import StrEnum
from .constants import SIGNS
from .decanates import chaldean_face
from .dignities import DOMICILE, EXALTATION, DETRIMENT, FALL, LILLY_1647_TERMS
from .dignities_types import PlanetaryReception, ReceptionBasis
from .triplicity import TriplicityDoctrine, triplicity_assignment_for

__all__ = [
    "LillyEvidenceState", "LillyDignityBasis", "LillyOrbState", "LillyMechanism",
    "LillyEvidencePolicy", "LILLY_1647_CONDITION_RECEPTION", "LillySnapshotContext",
    "LillyPlanetPosition", "LillyDignityEvidence", "LillyConditionSnapshot",
    "LillyDirectedReception", "LillyMutualReception", "LillyReceptionNetwork",
    "LillyReceptionRequirement", "LillyMechanismReceptionPrerequisites", "LillyOrbEvidence",
    "lilly_position_from_longitude", "lilly_condition_snapshot", "lilly_reception_evidence",
    "lilly_translation_reception", "lilly_collection_reception", "lilly_orb_evidence",
    "adapt_generic_lilly_reception",
]

_PLANETS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
_SIGNS = tuple(SIGNS)
_SOURCE = "William Lilly, Christian Astrology (1647), pp.102-105,112,115; b30338724"


class LillyEvidenceState(StrEnum):
    """Truth of a bounded proposition; unknown is distinct from absence."""
    PRESENT = "present"
    ABSENT = "absent"
    NOT_EVALUABLE = "not_evaluable"


class LillyDignityBasis(StrEnum):
    """Five positive dignity bases; domicile is the packet's house basis."""
    DOMICILE = "domicile"
    EXALTATION = "exaltation"
    TRIPLICITY = "triplicity"
    TERM = "term"
    FACE = "face"


class LillyOrbState(StrEnum):
    """Exact mathematical relation to the selected summed moiety."""
    INTERIOR = "interior"
    BOUNDARY = "boundary"
    EXTERIOR = "exterior"


class LillyMechanism(StrEnum):
    """Mechanisms for which this layer evaluates reception prerequisites."""
    TRANSLATION = "translation"
    COLLECTION = "collection"


_BASES = tuple(LillyDignityBasis)
_POINTS = MappingProxyType({
    LillyDignityBasis.DOMICILE: 5, LillyDignityBasis.EXALTATION: 4,
    LillyDignityBasis.TRIPLICITY: 3, LillyDignityBasis.TERM: 2, LillyDignityBasis.FACE: 1,
})
# Full orbs from p.107's second printed set, selected by OR01; not v1's table.
_ORBS = MappingProxyType({
    "Saturn": 9.0, "Jupiter": 9.0, "Mars": 7.0, "Sun": 15.0,
    "Venus": 7.0, "Mercury": 7.0, "Moon": 12.0,
})
_DOMICILE = MappingProxyType({p: tuple(DOMICILE[p]) for p in _PLANETS})
_EXALTATION = MappingProxyType({p: tuple(EXALTATION[p]) for p in _PLANETS})
_DETRIMENT = MappingProxyType({p: tuple(DETRIMENT[p]) for p in _PLANETS})
_FALL = MappingProxyType({p: tuple(FALL[p]) for p in _PLANETS})
_TERMS = MappingProxyType({s: tuple(LILLY_1647_TERMS[s]) for s in _SIGNS})
_FACES = MappingProxyType({s: tuple(chaldean_face(i * 30 + j * 10).ruling_planet
                                     for j in range(3)) for i, s in enumerate(_SIGNS)})
_TRIPLICITY = MappingProxyType({s: tuple(triplicity_assignment_for(
    s, is_day_chart=day, doctrine=TriplicityDoctrine.WILLIAM_LILLY_1647,
).active_ruler for day in (True, False)) for s in _SIGNS})
_TRANSLATION_BASES = (LillyDignityBasis.DOMICILE, LillyDignityBasis.TRIPLICITY,
                      LillyDignityBasis.TERM)


def _planet(value: str) -> None:
    if value not in _PLANETS:
        raise ValueError("body must be one of the classical seven planets")


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number, not a boolean")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _any_state(states) -> LillyEvidenceState:
    states = tuple(states)
    if LillyEvidenceState.PRESENT in states:
        return LillyEvidenceState.PRESENT
    if LillyEvidenceState.NOT_EVALUABLE in states:
        return LillyEvidenceState.NOT_EVALUABLE
    return LillyEvidenceState.ABSENT


def _all_state(states) -> LillyEvidenceState:
    states = tuple(states)
    if LillyEvidenceState.ABSENT in states:
        return LillyEvidenceState.ABSENT
    if LillyEvidenceState.NOT_EVALUABLE in states:
        return LillyEvidenceState.NOT_EVALUABLE
    return LillyEvidenceState.PRESENT


@dataclass(frozen=True, slots=True)
class LillyEvidencePolicy:
    """Fixed identity of this additive evidence profile and its source choices."""
    profile_id: str = field(default="lilly_1647_condition_reception_v1", init=False)
    source_contract: str = field(default="lilly_1647_core_candidate_2026_10_23", init=False)
    dignity_table: str = field(default="william_lilly_1647", init=False)
    orb_table: str = field(default="lilly_1647_p107_second", init=False)
    orb_boundary: str = field(default="strict_interior", init=False)
    epoch_selection: str = field(default="caller_supplied_snapshot", init=False)
    body_scope: tuple[str, ...] = field(default=_PLANETS, init=False)
    full_orbs_deg: tuple[tuple[str, float], ...] = field(
        default=tuple((p, _ORBS[p]) for p in _PLANETS), init=False,
    )


LILLY_1647_CONDITION_RECEPTION = LillyEvidencePolicy()


@dataclass(frozen=True, slots=True)
class LillySnapshotContext:
    """Explicit epoch label, optional UT1 JD and known or unknown chart sect.

    An epoch such as ``didactic_unspecified`` preserves an unspecified source
    time. Supplying a tag does not manufacture a historical date. Equality of
    the complete context is required when combining snapshot evidence.
    """
    epoch: str
    is_day_chart: bool | None
    jd_ut: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.epoch, str) or not self.epoch.strip():
            raise ValueError("an explicit nonempty snapshot epoch is required")
        if self.is_day_chart is not None and type(self.is_day_chart) is not bool:
            raise TypeError("is_day_chart must be bool or None")
        if self.jd_ut is not None:
            object.__setattr__(self, "jd_ut", _finite(self.jd_ut, "jd_ut"))


@dataclass(frozen=True, slots=True)
class LillyPlanetPosition:
    """Classical planet and sign with an optional continuous degree in [0,30)."""
    body: str
    sign: str
    degree: float | None = None

    def __post_init__(self) -> None:
        _planet(self.body)
        if self.sign not in _SIGNS:
            raise ValueError("sign must be a recognized tropical zodiac sign")
        if self.degree is not None:
            degree = _finite(self.degree, "degree")
            if not 0.0 <= degree < 30.0:
                raise ValueError("degree must be in [0,30) within its stated sign")
            object.__setattr__(self, "degree", degree)


@dataclass(frozen=True, slots=True)
class LillyDignityEvidence:
    """Positive dignity membership; source points are magnitudes, not a score."""
    basis: LillyDignityBasis
    state: LillyEvidenceState
    possible_rulers: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    source_points: int

    def __post_init__(self) -> None:
        if not isinstance(self.basis, LillyDignityBasis) or not isinstance(self.state, LillyEvidenceState):
            raise TypeError("typed Lilly dignity basis and evidence state are required")
        if not isinstance(self.possible_rulers, tuple) or not isinstance(self.missing_inputs, tuple):
            raise TypeError("rulers and missing inputs must be immutable tuples")
        if (any(p not in _PLANETS for p in self.possible_rulers)
                or len(set(self.possible_rulers)) != len(self.possible_rulers)):
            raise ValueError("possible rulers must be distinct classical planets")
        if type(self.source_points) is not int or self.source_points != _POINTS[self.basis]:
            raise ValueError("source points must match Lilly's printed magnitude for the basis")
        if self.state is LillyEvidenceState.NOT_EVALUABLE:
            expected = ("chart_sect",) if self.basis is LillyDignityBasis.TRIPLICITY else ("degree",)
            if (self.basis not in (LillyDignityBasis.TRIPLICITY, LillyDignityBasis.TERM, LillyDignityBasis.FACE)
                    or self.missing_inputs != expected or len(self.possible_rulers) < 2):
                raise ValueError("unknown membership must retain the required missing input and alternatives")
        elif self.missing_inputs or (self.state is LillyEvidenceState.PRESENT and len(self.possible_rulers) != 1):
            raise ValueError("known membership cannot carry unresolved inputs or ambiguous positive ownership")


def _dignities_at(
    host: str, position: LillyPlanetPosition, day: bool | None,
) -> tuple[LillyDignityEvidence, ...]:
    sign, degree = position.sign, position.degree
    triplicity = _TRIPLICITY[sign]
    term_rulers = (tuple(r for r, _, _ in _TERMS[sign]) if degree is None else
                   (next(r for r, start, end in _TERMS[sign] if start <= degree < end),))
    face_rulers = _FACES[sign] if degree is None else (_FACES[sign][int(degree // 10)],)
    owners = (
        tuple(p for p in _PLANETS if sign in _DOMICILE[p]),
        tuple(p for p in _PLANETS if sign in _EXALTATION[p]),
        triplicity if day is None else (triplicity[0 if day else 1],),
        term_rulers, face_rulers,
    )
    result = []
    for basis, candidates in zip(_BASES, owners):
        candidates = tuple(p for p in _PLANETS if p in candidates)
        if host not in candidates:
            state, missing = LillyEvidenceState.ABSENT, ()
        elif len(candidates) == 1:
            state, missing = LillyEvidenceState.PRESENT, ()
        else:
            state = LillyEvidenceState.NOT_EVALUABLE
            missing = ("chart_sect",) if basis is LillyDignityBasis.TRIPLICITY else ("degree",)
        result.append(LillyDignityEvidence(basis, state, candidates, missing, _POINTS[basis]))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class LillyConditionSnapshot:
    """Derived essential condition at one explicit snapshot; no aggregate score."""
    position: LillyPlanetPosition
    context: LillySnapshotContext
    dignities: tuple[LillyDignityEvidence, ...] = field(init=False)
    detriment: bool = field(init=False)
    fall: bool = field(init=False)
    peregrine: LillyEvidenceState = field(init=False)
    policy: LillyEvidencePolicy = field(default=LILLY_1647_CONDITION_RECEPTION, init=False)
    source_reference: str = field(default=_SOURCE, init=False)
    scope: str = field(default="essential_condition_snapshot", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.position, LillyPlanetPosition) or not isinstance(self.context, LillySnapshotContext):
            raise TypeError("a Lilly position and snapshot context are required")
        evidence = _dignities_at(self.position.body, self.position, self.context.is_day_chart)
        positive = _any_state(e.state for e in evidence)
        peregrine = {LillyEvidenceState.PRESENT: LillyEvidenceState.ABSENT,
                     LillyEvidenceState.ABSENT: LillyEvidenceState.PRESENT,
                     LillyEvidenceState.NOT_EVALUABLE: LillyEvidenceState.NOT_EVALUABLE}[positive]
        object.__setattr__(self, "dignities", evidence)
        object.__setattr__(self, "detriment", self.position.sign in _DETRIMENT[self.position.body])
        object.__setattr__(self, "fall", self.position.sign in _FALL[self.position.body])
        object.__setattr__(self, "peregrine", peregrine)


@dataclass(frozen=True, slots=True)
class LillyDirectedReception:
    """Host rules dignity at the guest's position; no aspect or reverse implied."""
    host: str
    guest_snapshot: LillyConditionSnapshot
    dignities: tuple[LillyDignityEvidence, ...] = field(init=False)
    state: LillyEvidenceState = field(init=False)

    def __post_init__(self) -> None:
        _planet(self.host)
        if not isinstance(self.guest_snapshot, LillyConditionSnapshot):
            raise TypeError("guest_snapshot must be a Lilly condition snapshot")
        if self.host == self.guest:
            raise ValueError("self dignity is not reception between distinct planets")
        evidence = _dignities_at(self.host, self.guest_snapshot.position, self.context.is_day_chart)
        object.__setattr__(self, "dignities", evidence)
        object.__setattr__(self, "state", _any_state(e.state for e in evidence))

    @property
    def guest(self) -> str:
        """Return the visiting planet, not its dignity host."""
        return self.guest_snapshot.position.body

    @property
    def context(self) -> LillySnapshotContext:
        """Return the actual evaluation context of the guest position."""
        return self.guest_snapshot.context

    @property
    def present_bases(self) -> tuple[LillyDignityBasis, ...]:
        """Return only bases established by the supplied inputs."""
        return tuple(e.basis for e in self.dignities if e.state is LillyEvidenceState.PRESENT)


def _same_context(snapshots: tuple[LillyConditionSnapshot, ...]) -> None:
    if not snapshots or any(not isinstance(s, LillyConditionSnapshot) for s in snapshots):
        raise TypeError("nonempty Lilly condition snapshots are required")
    if any(s.context != snapshots[0].context or s.policy != snapshots[0].policy for s in snapshots):
        raise ValueError("snapshot context and policy must match; epochs cannot be reused")
    bodies = tuple(s.position.body for s in snapshots)
    if len(bodies) != len(set(bodies)):
        raise ValueError("snapshot participants must be distinct planets")


@dataclass(frozen=True, slots=True)
class LillyMutualReception:
    """Two independently evaluated directions, with same and mixed witnesses."""
    forward: LillyDirectedReception
    reverse: LillyDirectedReception
    state: LillyEvidenceState = field(init=False)
    same_bases: tuple[LillyDignityBasis, ...] = field(init=False)
    mixed_bases: tuple[tuple[LillyDignityBasis, LillyDignityBasis], ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.forward, LillyDirectedReception) or not isinstance(self.reverse, LillyDirectedReception):
            raise TypeError("two directed reception witnesses are required")
        if (self.forward.host, self.forward.guest) != (self.reverse.guest, self.reverse.host):
            raise ValueError("mutual evidence must contain the two opposite directions")
        _same_context((self.forward.guest_snapshot, self.reverse.guest_snapshot))
        a, b = self.forward.present_bases, self.reverse.present_bases
        object.__setattr__(self, "state", _all_state((self.forward.state, self.reverse.state)))
        object.__setattr__(self, "same_bases", tuple(basis for basis in _BASES if basis in a and basis in b))
        object.__setattr__(self, "mixed_bases", tuple((x, y) for x in a for y in b if x != y))


@dataclass(frozen=True, slots=True)
class LillyReceptionNetwork:
    """All supplied pair directions, including absence/unknown; no path search."""
    snapshots: tuple[LillyConditionSnapshot, ...]
    directed: tuple[LillyDirectedReception, ...] = field(init=False)
    mutual: tuple[LillyMutualReception, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.snapshots, tuple):
            raise TypeError("snapshots must be an immutable tuple")
        _same_context(self.snapshots)
        snapshots = tuple(sorted(self.snapshots, key=lambda s: _PLANETS.index(s.position.body)))
        edges = tuple(LillyDirectedReception(a.position.body, b) for a in snapshots
                      for b in snapshots if a is not b)
        by_pair = {(e.host, e.guest): e for e in edges}
        mutual = tuple(LillyMutualReception(by_pair[(a.position.body, b.position.body)],
                                            by_pair[(b.position.body, a.position.body)])
                       for a, b in combinations(snapshots, 2))
        object.__setattr__(self, "snapshots", snapshots)
        object.__setattr__(self, "directed", edges)
        object.__setattr__(self, "mutual", mutual)


@dataclass(frozen=True, slots=True)
class LillyReceptionRequirement:
    """One role-qualified reception prerequisite, rather than full perfection."""
    evidence: LillyDirectedReception
    host_role: str
    guest_role: str
    allowed_bases: tuple[LillyDignityBasis, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, LillyDirectedReception):
            raise TypeError("directed Lilly reception evidence is required")
        if (not isinstance(self.allowed_bases, tuple) or not self.allowed_bases
                or any(not isinstance(b, LillyDignityBasis) for b in self.allowed_bases)):
            raise TypeError("allowed bases must be a nonempty immutable tuple of Lilly bases")
        if len(set(self.allowed_bases)) != len(self.allowed_bases):
            raise ValueError("allowed bases must be distinct")
        if any(not isinstance(role, str) or not role.strip() for role in (self.host_role, self.guest_role)):
            raise ValueError("explicit host and guest roles are required")

    @property
    def state(self) -> LillyEvidenceState:
        """Evaluate only the mechanism's permitted bases with three-valued logic."""
        return _any_state(e.state for e in self.evidence.dignities if e.basis in self.allowed_bases)

    @property
    def qualifying_bases(self) -> tuple[LillyDignityBasis, ...]:
        """Return established, mechanism-permitted bases."""
        return tuple(b for b in self.evidence.present_bases if b in self.allowed_bases)


@dataclass(frozen=True, slots=True)
class LillyMechanismReceptionPrerequisites:
    """Lilly p.126 receiving roles at a caller-selected snapshot, reception only."""
    mechanism: LillyMechanism
    principals: tuple[LillyConditionSnapshot, ...]
    intermediary: LillyConditionSnapshot
    requirements: tuple[LillyReceptionRequirement, ...] = field(init=False)
    state: LillyEvidenceState = field(init=False)
    scope: str = field(default="reception_prerequisites_only", init=False)
    source_reference: str = field(default="Lilly 1647 p.126; RC05-RC06", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mechanism, LillyMechanism) or not isinstance(self.principals, tuple):
            raise TypeError("a Lilly mechanism and immutable principal tuple are required")
        translation = self.mechanism is LillyMechanism.TRANSLATION
        if len(self.principals) != (1 if translation else 2):
            raise ValueError("translation needs one source; collection needs two principals")
        _same_context((*self.principals, self.intermediary))
        roles = ("source_principal",) if translation else ("principal_a", "principal_b")
        guest_role = "translator" if translation else "collector"
        bases = _TRANSLATION_BASES if translation else _BASES
        requirements = tuple(LillyReceptionRequirement(
            LillyDirectedReception(p.position.body, self.intermediary), role, guest_role, bases,
        ) for p, role in zip(self.principals, roles))
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(self, "state", _all_state(r.state for r in requirements))


@dataclass(frozen=True, slots=True)
class LillyOrbEvidence:
    """Selected p.107 second-set contact range; no applying/separating inference."""
    body_a: str
    body_b: str
    aspect_error_deg: float
    context: LillySnapshotContext
    full_orb_a_deg: float = field(init=False)
    full_orb_b_deg: float = field(init=False)
    combined_moiety_deg: float = field(init=False)
    state: LillyOrbState = field(init=False)
    policy: LillyEvidencePolicy = field(default=LILLY_1647_CONDITION_RECEPTION, init=False)
    source_reference: str = field(default="Lilly 1647 pp.107,110; OR01-OR03", init=False)

    def __post_init__(self) -> None:
        _planet(self.body_a)
        _planet(self.body_b)
        if self.body_a == self.body_b:
            raise ValueError("orb evidence needs distinct planets")
        if not isinstance(self.context, LillySnapshotContext):
            raise TypeError("an explicit Lilly snapshot context is required")
        error = _finite(self.aspect_error_deg, "aspect_error_deg")
        if abs(error) > 180:
            raise ValueError("aspect error must be a signed circular residual in [-180,180]")
        limit = (_ORBS[self.body_a] + _ORBS[self.body_b]) / 2
        state = (LillyOrbState.INTERIOR if abs(error) < limit else
                 LillyOrbState.BOUNDARY if abs(error) == limit else LillyOrbState.EXTERIOR)
        object.__setattr__(self, "aspect_error_deg", error)
        object.__setattr__(self, "full_orb_a_deg", _ORBS[self.body_a])
        object.__setattr__(self, "full_orb_b_deg", _ORBS[self.body_b])
        object.__setattr__(self, "combined_moiety_deg", limit)
        object.__setattr__(self, "state", state)

    @property
    def within_orb(self) -> bool:
        """Return strict interior membership; an exact boundary is separate."""
        return self.state is LillyOrbState.INTERIOR


def lilly_position_from_longitude(body: str, longitude: float) -> LillyPlanetPosition:
    """Normalize finite tropical longitude modulo 360 into sign/degree data."""
    normalized = _finite(longitude, "longitude") % 360.0
    return LillyPlanetPosition(body, _SIGNS[int(normalized // 30) % 12], normalized % 30)


def lilly_condition_snapshot(position: LillyPlanetPosition, *, context: LillySnapshotContext) -> LillyConditionSnapshot:
    """Evaluate only essential condition at the supplied snapshot."""
    return LillyConditionSnapshot(position, context)


def lilly_reception_evidence(snapshots: tuple[LillyConditionSnapshot, ...]) -> LillyReceptionNetwork:
    """Evaluate every ordered pair among the supplied, consistently bound bodies."""
    return LillyReceptionNetwork(snapshots)


def lilly_translation_reception(
    source: LillyConditionSnapshot, translator: LillyConditionSnapshot,
) -> LillyMechanismReceptionPrerequisites:
    """Require the source to receive the translator by domicile/triplicity/term."""
    return LillyMechanismReceptionPrerequisites(LillyMechanism.TRANSLATION, (source,), translator)


def lilly_collection_reception(principal_a: LillyConditionSnapshot, principal_b: LillyConditionSnapshot,
                               collector: LillyConditionSnapshot) -> LillyMechanismReceptionPrerequisites:
    """Require both principals to receive the collector in positive dignity."""
    return LillyMechanismReceptionPrerequisites(LillyMechanism.COLLECTION, (principal_a, principal_b), collector)


def lilly_orb_evidence(body_a: str, body_b: str, aspect_error_deg: float, *,
                       context: LillySnapshotContext) -> LillyOrbEvidence:
    """Evaluate a supplied aspect residual using the separately named orb policy."""
    return LillyOrbEvidence(body_a, body_b, aspect_error_deg, context)


def adapt_generic_lilly_reception(relation: PlanetaryReception, *,
                                  guest_snapshot: LillyConditionSnapshot,
                                  relation_context: LillySnapshotContext) -> LillyDirectedReception:
    """Bind generic terminology explicitly: its receiving_planet is our guest.

    The caller must supply the generic relation's evaluation context. The
    declared domicile/exaltation basis must be verified at that snapshot.
    Generic MUTUAL metadata never manufactures a reverse edge or an epoch.
    """
    if not isinstance(relation, PlanetaryReception) or not isinstance(guest_snapshot, LillyConditionSnapshot):
        raise TypeError("a generic reception and Lilly guest snapshot are required")
    if not isinstance(relation_context, LillySnapshotContext) or relation_context != guest_snapshot.context:
        raise ValueError("generic relation context must match the guest snapshot")
    if ((relation.receiving_planet, relation.receiving_sign)
            != (guest_snapshot.position.body, guest_snapshot.position.sign)):
        raise ValueError("generic receiving planet/sign must match the Lilly guest")
    basis = {ReceptionBasis.DOMICILE: LillyDignityBasis.DOMICILE,
             ReceptionBasis.EXALTATION: LillyDignityBasis.EXALTATION}.get(relation.basis)
    if basis is None:
        raise ValueError("only the generic domicile/exaltation bases are supported")
    evidence = LillyDirectedReception(relation.host_planet, guest_snapshot)
    if basis not in evidence.present_bases:
        raise ValueError("generic claimed basis is not established at the supplied snapshot")
    return evidence

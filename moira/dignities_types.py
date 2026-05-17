"""
Dignity Types — moira/dignities_types.py

Pure data layer for the Dignity Engine.  Contains all enumerations, policy
dataclasses, and result-vessel dataclasses that underpin
``moira.dignities.DignitiesService``.

Separating these types from the computational engine lets callers import
result types without pulling in the full service class, and resolves the
internal forward dependency that would otherwise require
``DignitiesService`` to be referenced from within ``__post_init__`` methods
before the class is defined.

Import-time side effects: None.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .constants import SIGNS

__all__ = [
    # Enums
    "ConditionPolarity",
    "EssentialDignityKind",
    "AccidentalConditionKind",
    "SectStateKind",
    "SolarConditionKind",
    "ReceptionKind",
    "ReceptionBasis",
    "ReceptionMode",
    "DispositorshipSubjectSet",
    "DispositorshipRulership",
    "DispositorshipTerminationKind",
    "UnsupportedSubjectHandling",
    "DispositorshipConditionState",
    "PlanetaryConditionState",
    "EssentialDignityDoctrine",
    "MercurySectModel",
    # Policy dataclasses
    "EssentialDignityPolicy",
    "SolarConditionPolicy",
    "MutualReceptionPolicy",
    "SectHayzPolicy",
    "AccidentalDignityPolicy",
    "DignityComputationPolicy",
    "DispositorshipSubjectPolicy",
    "DispositorshipRulershipPolicy",
    "DispositorshipTerminationPolicy",
    "DispositorshipUnsupportedSubjectPolicy",
    "DispositorshipOrderingPolicy",
    "DispositorshipComputationPolicy",
    # Result / truth dataclasses
    "PlanetaryReception",
    "DispositorLink",
    "DispositorshipChain",
    "DispositorshipProfile",
    "DispositorshipConditionProfile",
    "DispositorshipChartConditionProfile",
    "DispositorshipNetworkEdgeMode",
    "DispositorshipNetworkNode",
    "DispositorshipNetworkEdge",
    "DispositorshipNetworkProfile",
    "DispositorshipSubsystemProfile",
    "DispositorshipComparisonItem",
    "DispositorshipComparisonBundle",
    "PlanetaryConditionProfile",
    "ChartConditionProfile",
    "ConditionNetworkNode",
    "ConditionNetworkEdge",
    "ConditionNetworkProfile",
    "EssentialDignityClassification",
    "AccidentalConditionClassification",
    "AccidentalDignityClassification",
    "SectClassification",
    "SolarConditionClassification",
    "ReceptionClassification",
    "EssentialDignityTruth",
    "AccidentalDignityCondition",
    "SolarConditionTruth",
    "MutualReceptionTruth",
    "SectTruth",
    "AccidentalDignityTruth",
    "PlanetaryDignity",
]

# ---------------------------------------------------------------------------
# Classic 7 and ordering constant (used internally and by the service layer)
# ---------------------------------------------------------------------------

CLASSIC_7: set[str] = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}

_PLANET_ORDER = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]


def _normalize_dispositorship_subject_name(subject: str) -> str:
    """Normalize dispositorship subject names to the canonical chart form."""

    return subject.strip().title()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConditionPolarity(StrEnum):
    """Classification polarity derived from existing scoring and labels."""

    STRENGTHENING = "strengthening"
    WEAKENING = "weakening"
    NEUTRAL = "neutral"


class EssentialDignityKind(StrEnum):
    """Typed essential dignity kinds for the five-level classical scheme."""

    DOMICILE = "domicile"
    EXALTATION = "exaltation"
    TRIPLICITY = "triplicity"
    BOUND = "bound"
    FACE = "face"
    DETRIMENT = "detriment"
    FALL = "fall"
    PEREGRINE = "peregrine"


class AccidentalConditionKind(StrEnum):
    """Typed accidental dignity/debility kinds already computed by the engine."""

    ANGULAR = "angular"
    SUCCEDENT = "succedent"
    CADENT = "cadent"
    DIRECT = "direct"
    RETROGRADE = "retrograde"
    CAZIMI = "cazimi"
    COMBUST = "combust"
    UNDER_SUNBEAMS = "under_sunbeams"
    MUTUAL_RECEPTION = "mutual_reception"
    MUTUAL_EXALTATION = "mutual_exaltation"
    HAYZ = "hayz"
    JOY = "joy"
    HALB = "halb"
    ORIENTAL = "oriental"
    OCCIDENTAL = "occidental"
    BESIEGED = "besieged"


class SectStateKind(StrEnum):
    """Lean sect-state classification derived from already-computed sect truth."""

    IN_HAYZ = "in_hayz"
    IN_HALB = "in_halb"
    IN_SECT = "in_sect"
    OUT_OF_SECT = "out_of_sect"


class SolarConditionKind(StrEnum):
    """Typed solar-condition classification derived from solar truth."""

    NONE = "none"
    CAZIMI = "cazimi"
    COMBUST = "combust"
    UNDER_SUNBEAMS = "under_sunbeams"


class ReceptionKind(StrEnum):
    """Typed mutual reception classification derived from reception truth."""

    DOMICILE = "domicile"
    EXALTATION = "exaltation"


class ReceptionBasis(StrEnum):
    """Doctrinal basis for a planetary reception relation."""

    DOMICILE = "domicile"
    EXALTATION = "exaltation"


class ReceptionMode(StrEnum):
    """Relational mode for a planetary reception."""

    UNILATERAL = "unilateral"
    MUTUAL = "mutual"


class DispositorshipSubjectSet(StrEnum):
    """Named subject-set doctrines supported by the dispositorship layer."""

    CLASSIC_7 = "classic_7"


class DispositorshipRulership(StrEnum):
    """Named sign-rulership doctrines supported by the dispositorship layer."""

    TRADITIONAL_DOMICILE = "traditional_domicile"


class DispositorshipTerminationKind(StrEnum):
    """Terminal outcome class for one dispositorship traversal."""

    FINAL_DISPOSITOR = "final_dispositor"
    TERMINAL_CYCLE = "terminal_cycle"
    UNRESOLVED = "unresolved"


class UnsupportedSubjectHandling(StrEnum):
    """Policy for chart subjects that fall outside dispositorship scope."""

    IGNORE = "ignore"
    REJECT = "reject"
    SEGREGATE = "segregate"


class DispositorshipConditionState(StrEnum):
    """Integrated local condition state for one dispositorship subject."""

    SELF_DISPOSED = "self_disposed"
    RESOLVED_TO_FINAL = "resolved_to_final"
    TERMINAL_CYCLE = "terminal_cycle"
    UNRESOLVED = "unresolved"
    OUT_OF_SCOPE = "out_of_scope"


class DispositorshipNetworkEdgeMode(StrEnum):
    """Visibility mode for one directed dispositorship network edge."""

    UNILATERAL = "unilateral"
    RECIPROCAL = "reciprocal"


class PlanetaryConditionState(StrEnum):
    """Derived structural state for a planet's integrated condition profile."""

    REINFORCED = "reinforced"
    MIXED = "mixed"
    WEAKENED = "weakened"


class EssentialDignityDoctrine(StrEnum):
    """Named essential-dignity table doctrines supported by this engine."""

    TRADITIONAL_CLASSIC_7 = "traditional_classic_7"


class MercurySectModel(StrEnum):
    """Named Mercury sect models supported by this engine."""

    LONGITUDE_HEURISTIC = "longitude_heuristic"


# ---------------------------------------------------------------------------
# Policy dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EssentialDignityPolicy:
    """Policy surface for the essential dignity table doctrine."""

    doctrine: EssentialDignityDoctrine = EssentialDignityDoctrine.TRADITIONAL_CLASSIC_7


@dataclass(frozen=True, slots=True)
class SolarConditionPolicy:
    """Policy surface for solar-condition inclusion behavior."""

    include_cazimi: bool = True
    include_combust: bool = True
    include_under_sunbeams: bool = True
    include_for_luminaries: bool = False


@dataclass(frozen=True, slots=True)
class MutualReceptionPolicy:
    """Policy surface for mutual reception inclusion behavior."""

    include_domicile: bool = True
    include_exaltation: bool = True


@dataclass(frozen=True, slots=True)
class SectHayzPolicy:
    """Policy surface for sect and hayz doctrine already embodied by the engine."""

    mercury_sect_model: MercurySectModel = MercurySectModel.LONGITUDE_HEURISTIC
    include_hayz: bool = True


@dataclass(frozen=True, slots=True)
class AccidentalDignityPolicy:
    """Policy surface for accidental dignity inclusion behavior."""

    include_house_strength: bool = True
    include_motion: bool = True
    solar: SolarConditionPolicy = field(default_factory=SolarConditionPolicy)
    mutual_reception: MutualReceptionPolicy = field(default_factory=MutualReceptionPolicy)
    sect: SectHayzPolicy = field(default_factory=SectHayzPolicy)


@dataclass(frozen=True, slots=True)
class DignityComputationPolicy:
    """
    Lean backend policy surface for dignity computation.

    This makes the engine's current doctrine explicit. The default policy is
    intentionally identical to the current engine behavior.
    """

    essential: EssentialDignityPolicy = field(default_factory=EssentialDignityPolicy)
    accidental: AccidentalDignityPolicy = field(default_factory=AccidentalDignityPolicy)

    @property
    def includes_any_solar_condition(self) -> bool:
        """Return True when any solar-condition band is enabled."""

        solar = self.accidental.solar
        return solar.include_cazimi or solar.include_combust or solar.include_under_sunbeams

    @property
    def includes_any_mutual_reception(self) -> bool:
        """Return True when any mutual reception mode is enabled."""

        reception = self.accidental.mutual_reception
        return reception.include_domicile or reception.include_exaltation

    @property
    def is_default(self) -> bool:
        """Return True when this policy matches the current default doctrine."""

        return self == DignityComputationPolicy()


@dataclass(frozen=True, slots=True)
class DispositorshipSubjectPolicy:
    """Policy surface for dispositorship subject-set scope."""

    subject_set: DispositorshipSubjectSet = DispositorshipSubjectSet.CLASSIC_7


@dataclass(frozen=True, slots=True)
class DispositorshipRulershipPolicy:
    """Policy surface for dispositorship sign-rulership doctrine."""

    doctrine: DispositorshipRulership = DispositorshipRulership.TRADITIONAL_DOMICILE


@dataclass(frozen=True, slots=True)
class DispositorshipTerminationPolicy:
    """Policy surface for dispositorship chain termination semantics."""

    final_requires_self_domicile: bool = True
    cycles_are_terminal: bool = True


@dataclass(frozen=True, slots=True)
class DispositorshipUnsupportedSubjectPolicy:
    """Policy surface for subjects outside dispositorship scope."""

    handling: UnsupportedSubjectHandling = UnsupportedSubjectHandling.IGNORE


@dataclass(frozen=True, slots=True)
class DispositorshipOrderingPolicy:
    """Policy surface for dispositorship result ordering."""

    use_dignity_order: bool = True


@dataclass(frozen=True, slots=True)
class DispositorshipComputationPolicy:
    """Lean backend policy surface for dispositorship computation."""

    subject: DispositorshipSubjectPolicy = field(default_factory=DispositorshipSubjectPolicy)
    rulership: DispositorshipRulershipPolicy = field(default_factory=DispositorshipRulershipPolicy)
    termination: DispositorshipTerminationPolicy = field(default_factory=DispositorshipTerminationPolicy)
    unsupported_subjects: DispositorshipUnsupportedSubjectPolicy = field(default_factory=DispositorshipUnsupportedSubjectPolicy)
    ordering: DispositorshipOrderingPolicy = field(default_factory=DispositorshipOrderingPolicy)

    @property
    def is_default(self) -> bool:
        """Return True when this policy matches the current Phase 1 doctrine."""

        return self == DispositorshipComputationPolicy()


# ---------------------------------------------------------------------------
# Module-level helpers (extracted from DignitiesService static methods)
# These break the forward reference that would otherwise require importing
# DignitiesService from inside __post_init__ of the result-vessel types.
# ---------------------------------------------------------------------------

def _score_polarity(score: int) -> ConditionPolarity:
    if score > 0:
        return ConditionPolarity.STRENGTHENING
    if score < 0:
        return ConditionPolarity.WEAKENING
    return ConditionPolarity.NEUTRAL


def _derive_condition_state(
    strengthening_count: int,
    weakening_count: int,
) -> PlanetaryConditionState:
    if strengthening_count > 0 and weakening_count == 0:
        return PlanetaryConditionState.REINFORCED
    if weakening_count > 0 and strengthening_count == 0:
        return PlanetaryConditionState.WEAKENED
    return PlanetaryConditionState.MIXED


def _derive_dispositorship_condition_state(
    subject_in_scope: bool,
    termination_kind: DispositorshipTerminationKind,
    initial_subject: str,
    terminal_subjects: tuple[str, ...],
) -> DispositorshipConditionState:
    if not subject_in_scope:
        return DispositorshipConditionState.OUT_OF_SCOPE
    if termination_kind is DispositorshipTerminationKind.TERMINAL_CYCLE:
        return DispositorshipConditionState.TERMINAL_CYCLE
    if termination_kind is DispositorshipTerminationKind.UNRESOLVED:
        return DispositorshipConditionState.UNRESOLVED
    if terminal_subjects == (initial_subject,):
        return DispositorshipConditionState.SELF_DISPOSED
    return DispositorshipConditionState.RESOLVED_TO_FINAL


# ---------------------------------------------------------------------------
# Result / truth dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlanetaryReception:
    """
    Formal relational reception truth for one receiving planet.

    This is backend-only doctrine truth. It does not itself imply scoring;
    current dignity scoring uses only the admitted mutual subset.
    """

    receiving_planet: str
    host_planet: str
    basis: ReceptionBasis
    mode: ReceptionMode
    receiving_sign: str
    host_sign: str
    host_matching_signs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.receiving_planet == self.host_planet:
            raise ValueError("PlanetaryReception invariant failed: receiving_planet must differ from host_planet")
        if self.receiving_sign not in self.host_matching_signs:
            raise ValueError("PlanetaryReception invariant failed: receiving_sign must be included in host_matching_signs")

    @property
    def is_mutual(self) -> bool:
        """Return True when this reception is mutual rather than unilateral."""

        return self.mode is ReceptionMode.MUTUAL


@dataclass(slots=True)
class DispositorLink:
    """One directed dispositorship step under the active rulership policy."""

    subject: str
    subject_sign: str
    dispositor: str

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("DispositorLink invariant failed: subject must be non-empty")
        if self.subject_sign not in SIGNS:
            raise ValueError("DispositorLink invariant failed: subject_sign must be a recognised sign")
        if self.dispositor not in CLASSIC_7:
            raise ValueError("DispositorLink invariant failed: dispositor must be one of the Classic 7")


@dataclass(slots=True)
class DispositorshipChain:
    """Dispositorship traversal result for one initial chart subject."""

    initial_subject: str
    initial_sign: str | None
    subject_in_scope: bool
    subject_has_dispositor: bool
    links: list[DispositorLink] = field(default_factory=list)
    visited_subjects: tuple[str, ...] = ()
    termination_kind: DispositorshipTerminationKind = DispositorshipTerminationKind.UNRESOLVED
    terminal_subjects: tuple[str, ...] = ()
    cycle_members: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.initial_subject:
            raise ValueError("DispositorshipChain invariant failed: initial_subject must be non-empty")
        if self.initial_sign is not None and self.initial_sign not in SIGNS:
            raise ValueError("DispositorshipChain invariant failed: initial_sign must be a recognised sign when present")
        if not self.subject_in_scope:
            if self.subject_has_dispositor:
                raise ValueError("DispositorshipChain invariant failed: out-of-scope subjects cannot have dispositors")
            if self.links:
                raise ValueError("DispositorshipChain invariant failed: out-of-scope subjects cannot have dispositorship links")
        if self.termination_kind is DispositorshipTerminationKind.FINAL_DISPOSITOR:
            if len(self.terminal_subjects) != 1:
                raise ValueError("DispositorshipChain invariant failed: final dispositor chains must report exactly one terminal subject")
            if self.cycle_members:
                raise ValueError("DispositorshipChain invariant failed: final dispositor chains cannot carry cycle members")
        if self.termination_kind is DispositorshipTerminationKind.TERMINAL_CYCLE:
            if len(self.cycle_members) < 2:
                raise ValueError("DispositorshipChain invariant failed: terminal cycles must report at least two cycle members")
            if self.terminal_subjects != self.cycle_members:
                raise ValueError("DispositorshipChain invariant failed: terminal cycle subjects must match cycle_members exactly")
        if self.termination_kind is DispositorshipTerminationKind.UNRESOLVED and self.cycle_members:
            raise ValueError("DispositorshipChain invariant failed: unresolved chains cannot carry cycle members")

    @property
    def is_final_dispositor(self) -> bool:
        """Return True when the chain terminates in a final dispositor."""

        return self.termination_kind is DispositorshipTerminationKind.FINAL_DISPOSITOR

    @property
    def is_terminal_cycle(self) -> bool:
        """Return True when the chain terminates in a cycle."""

        return self.termination_kind is DispositorshipTerminationKind.TERMINAL_CYCLE


@dataclass(slots=True)
class DispositorshipProfile:
    """Chart-wide dispositorship profile derived from explicit policy."""

    chains: list[DispositorshipChain] = field(default_factory=list)
    final_dispositors: tuple[str, ...] = ()
    terminal_cycles: tuple[tuple[str, ...], ...] = ()
    unsupported_subjects: tuple[str, ...] = ()
    policy: DispositorshipComputationPolicy = field(default_factory=DispositorshipComputationPolicy)

    def __post_init__(self) -> None:
        in_scope_names = [
            chain.initial_subject for chain in self.chains
            if chain.subject_in_scope and chain.initial_subject in _PLANET_ORDER
        ]
        if self.policy.ordering.use_dignity_order:
            expected_in_scope = [planet for planet in _PLANET_ORDER if planet in in_scope_names]
        else:
            expected_in_scope = list(in_scope_names)
        if in_scope_names != expected_in_scope:
            raise ValueError("DispositorshipProfile invariant failed: in-scope chains must follow the active ordering policy")

        final_set = {
            terminal
            for chain in self.chains
            if chain.termination_kind is DispositorshipTerminationKind.FINAL_DISPOSITOR
            for terminal in chain.terminal_subjects
        }
        if self.policy.ordering.use_dignity_order:
            expected_finals = tuple(planet for planet in _PLANET_ORDER if planet in final_set)
        else:
            expected_finals = tuple(planet for planet in in_scope_names if planet in final_set)
        if self.final_dispositors != expected_finals:
            raise ValueError("DispositorshipProfile invariant failed: final_dispositors must match chain terminations under the active ordering policy")

        expected_cycles: list[tuple[str, ...]] = []
        seen_cycles: set[tuple[str, ...]] = set()
        for chain in self.chains:
            if chain.termination_kind is not DispositorshipTerminationKind.TERMINAL_CYCLE:
                continue
            if chain.cycle_members in seen_cycles:
                continue
            seen_cycles.add(chain.cycle_members)
            expected_cycles.append(chain.cycle_members)
        if self.terminal_cycles != tuple(expected_cycles):
            raise ValueError("DispositorshipProfile invariant failed: terminal_cycles must match unique chain cycle terminations")

    def get_chain(self, subject: str) -> DispositorshipChain:
        """Return the dispositorship chain for the named initial subject."""

        normalized = _normalize_dispositorship_subject_name(subject)
        for chain in self.chains:
            if chain.initial_subject == normalized:
                return chain
        raise KeyError("dispositorship chain not found")


@dataclass(slots=True)
class DispositorshipConditionProfile:
    """
    Integrated local condition profile derived from one dispositorship chain.

    This is a backend synthesis layer only. It consumes existing
    DispositorshipChain truth and does not recompute dispositorship doctrine.
    """

    initial_subject: str
    initial_sign: str | None
    subject_in_scope: bool
    subject_has_dispositor: bool
    termination_kind: DispositorshipTerminationKind
    terminal_subjects: tuple[str, ...] = ()
    cycle_members: tuple[str, ...] = ()
    visited_subjects: tuple[str, ...] = ()
    chain_length: int = 0
    state: DispositorshipConditionState = DispositorshipConditionState.UNRESOLVED

    def __post_init__(self) -> None:
        derived_state = _derive_dispositorship_condition_state(
            self.subject_in_scope,
            self.termination_kind,
            self.initial_subject,
            self.terminal_subjects,
        )
        if self.state is not derived_state:
            raise ValueError("DispositorshipConditionProfile invariant failed: state must match derived dispositorship condition state")
        if self.chain_length != len(self.visited_subjects):
            raise ValueError("DispositorshipConditionProfile invariant failed: chain_length must match visited_subjects length")
        if self.termination_kind is DispositorshipTerminationKind.TERMINAL_CYCLE and self.terminal_subjects != self.cycle_members:
            raise ValueError("DispositorshipConditionProfile invariant failed: cycle terminations must keep terminal_subjects aligned with cycle_members")

    @property
    def is_self_disposed(self) -> bool:
        """Return True when the subject is itself the final dispositor."""

        return self.state is DispositorshipConditionState.SELF_DISPOSED

    @property
    def resolves_to_final(self) -> bool:
        """Return True when the subject resolves to a final dispositor."""

        return self.state in (
            DispositorshipConditionState.SELF_DISPOSED,
            DispositorshipConditionState.RESOLVED_TO_FINAL,
        )

    @property
    def is_terminal_cycle(self) -> bool:
        """Return True when the subject terminates in a dispositorship cycle."""

        return self.state is DispositorshipConditionState.TERMINAL_CYCLE

    @property
    def is_unresolved(self) -> bool:
        """Return True when the subject remains unresolved under current policy."""

        return self.state is DispositorshipConditionState.UNRESOLVED

    @property
    def is_out_of_scope(self) -> bool:
        """Return True when the subject was outside dispositorship policy scope."""

        return self.state is DispositorshipConditionState.OUT_OF_SCOPE


@dataclass(slots=True)
class DispositorshipChartConditionProfile:
    """
    Chart-wide dispositorship condition profile derived from per-subject
    dispositorship condition profiles.

    This is a backend aggregation layer only. It consumes existing
    DispositorshipConditionProfile results and does not recompute
    dispositorship doctrine.
    """

    profiles: list[DispositorshipConditionProfile] = field(default_factory=list)
    self_disposed_count: int = 0
    resolved_to_final_count: int = 0
    terminal_cycle_count: int = 0
    unresolved_count: int = 0
    out_of_scope_count: int = 0
    final_dispositor_count: int = 0
    cycle_count: int = 0
    has_mixed_terminals: bool = False

    def __post_init__(self) -> None:
        self_disposed = sum(
            1 for profile in self.profiles if profile.state is DispositorshipConditionState.SELF_DISPOSED
        )
        resolved = sum(
            1 for profile in self.profiles if profile.state is DispositorshipConditionState.RESOLVED_TO_FINAL
        )
        cycle = sum(
            1 for profile in self.profiles if profile.state is DispositorshipConditionState.TERMINAL_CYCLE
        )
        unresolved = sum(
            1 for profile in self.profiles if profile.state is DispositorshipConditionState.UNRESOLVED
        )
        out_of_scope = sum(
            1 for profile in self.profiles if profile.state is DispositorshipConditionState.OUT_OF_SCOPE
        )
        if (
            self.self_disposed_count,
            self.resolved_to_final_count,
            self.terminal_cycle_count,
            self.unresolved_count,
            self.out_of_scope_count,
        ) != (
            self_disposed,
            resolved,
            cycle,
            unresolved,
            out_of_scope,
        ):
            raise ValueError("DispositorshipChartConditionProfile invariant failed: state counts must match profile states")

        final_dispositors = {
            terminal
            for profile in self.profiles
            if profile.termination_kind is DispositorshipTerminationKind.FINAL_DISPOSITOR
            for terminal in profile.terminal_subjects
        }
        cycles = {
            profile.cycle_members
            for profile in self.profiles
            if profile.termination_kind is DispositorshipTerminationKind.TERMINAL_CYCLE
        }
        if self.final_dispositor_count != len(final_dispositors):
            raise ValueError("DispositorshipChartConditionProfile invariant failed: final_dispositor_count must match profile terminals")
        if self.cycle_count != len(cycles):
            raise ValueError("DispositorshipChartConditionProfile invariant failed: cycle_count must match unique profile cycles")

        expected_mixed = (
            bool(final_dispositors) and bool(cycles)
        ) or (bool(final_dispositors or cycles) and self.unresolved_count > 0)
        if self.has_mixed_terminals is not expected_mixed:
            raise ValueError("DispositorshipChartConditionProfile invariant failed: has_mixed_terminals must match derived chart state")

        in_scope_names = [
            profile.initial_subject
            for profile in self.profiles
            if profile.subject_in_scope and profile.initial_subject in _PLANET_ORDER
        ]
        expected_in_scope = [planet for planet in _PLANET_ORDER if planet in in_scope_names]
        if in_scope_names != expected_in_scope:
            raise ValueError("DispositorshipChartConditionProfile invariant failed: profiles must be in deterministic dignity order")

    @property
    def profile_count(self) -> int:
        """Return the number of dispositorship condition profiles aggregated."""

        return len(self.profiles)


@dataclass(slots=True)
class DispositorshipNetworkNode:
    """
    Node in the derived dispositorship condition network.

    This is a backend inspectability layer only. It consumes existing
    dispositorship condition profiles and direct dispositorship links.
    """

    subject: str
    profile: DispositorshipConditionProfile
    outgoing_count: int = 0
    incoming_count: int = 0
    reciprocal_count: int = 0

    def __post_init__(self) -> None:
        if self.subject != self.profile.initial_subject:
            raise ValueError("DispositorshipNetworkNode invariant failed: subject must match profile.initial_subject")
        if self.reciprocal_count > min(self.outgoing_count, self.incoming_count):
            raise ValueError("DispositorshipNetworkNode invariant failed: reciprocal_count cannot exceed incoming/outgoing counts")

    @property
    def degree_count(self) -> int:
        """Return the direct degree count for this node."""

        return self.outgoing_count + self.incoming_count

    @property
    def is_isolated(self) -> bool:
        """Return True when the node has no direct dispositorship links."""

        return self.degree_count == 0


@dataclass(slots=True)
class DispositorshipNetworkEdge:
    """
    Directed edge in the derived dispositorship condition network.

    Each edge corresponds to one direct dispositorship relation between
    in-scope subjects and does not recompute dispositorship doctrine.
    """

    source_subject: str
    target_subject: str
    mode: DispositorshipNetworkEdgeMode

    def __post_init__(self) -> None:
        if self.source_subject == self.target_subject:
            raise ValueError("DispositorshipNetworkEdge invariant failed: source_subject and target_subject must differ")


@dataclass(slots=True)
class DispositorshipNetworkProfile:
    """
    Network profile derived from dispositorship condition profiles and direct
    dispositorship links.

    This is a backend aggregation layer only. It consumes existing condition
    profiles and their already-formalized direct dispositorship relations.
    """

    nodes: list[DispositorshipNetworkNode] = field(default_factory=list)
    edges: list[DispositorshipNetworkEdge] = field(default_factory=list)
    isolated_subjects: list[str] = field(default_factory=list)
    most_connected_subjects: list[str] = field(default_factory=list)
    reciprocal_edge_count: int = 0
    unilateral_edge_count: int = 0

    def __post_init__(self) -> None:
        ordered_names = [
            node.subject for node in sorted(
                self.nodes,
                key=lambda node: _PLANET_ORDER.index(node.subject) if node.subject in _PLANET_ORDER else 99,
            )
        ]
        if [node.subject for node in self.nodes] != ordered_names:
            raise ValueError("DispositorshipNetworkProfile invariant failed: nodes must be in deterministic dignity order")

        ordered_edges = sorted(
            self.edges,
            key=lambda edge: (
                _PLANET_ORDER.index(edge.source_subject) if edge.source_subject in _PLANET_ORDER else 99,
                _PLANET_ORDER.index(edge.target_subject) if edge.target_subject in _PLANET_ORDER else 99,
            ),
        )
        if self.edges != ordered_edges:
            raise ValueError("DispositorshipNetworkProfile invariant failed: edges must be in deterministic dignity order")

        reciprocal = sum(1 for edge in self.edges if edge.mode is DispositorshipNetworkEdgeMode.RECIPROCAL)
        unilateral = sum(1 for edge in self.edges if edge.mode is DispositorshipNetworkEdgeMode.UNILATERAL)
        if self.reciprocal_edge_count != reciprocal:
            raise ValueError("DispositorshipNetworkProfile invariant failed: reciprocal_edge_count must match edges")
        if self.unilateral_edge_count != unilateral:
            raise ValueError("DispositorshipNetworkProfile invariant failed: unilateral_edge_count must match edges")

        edge_pairs = {(edge.source_subject, edge.target_subject) for edge in self.edges}
        for edge in self.edges:
            reverse_present = (edge.target_subject, edge.source_subject) in edge_pairs
            if edge.mode is DispositorshipNetworkEdgeMode.RECIPROCAL and not reverse_present:
                raise ValueError("DispositorshipNetworkProfile invariant failed: reciprocal edges must have a reverse edge")
            if edge.mode is DispositorshipNetworkEdgeMode.UNILATERAL and reverse_present:
                raise ValueError("DispositorshipNetworkProfile invariant failed: unilateral edges must not have a reverse edge")

        node_map = {node.subject: node for node in self.nodes}
        outgoing = {name: 0 for name in node_map}
        incoming = {name: 0 for name in node_map}
        reciprocal_counts = {name: 0 for name in node_map}
        for edge in self.edges:
            if edge.source_subject not in node_map or edge.target_subject not in node_map:
                raise ValueError("DispositorshipNetworkProfile invariant failed: edges must reference known nodes")
            outgoing[edge.source_subject] += 1
            incoming[edge.target_subject] += 1
            if edge.mode is DispositorshipNetworkEdgeMode.RECIPROCAL:
                reciprocal_counts[edge.source_subject] += 1
        for node in self.nodes:
            if node.outgoing_count != outgoing[node.subject] or node.incoming_count != incoming[node.subject]:
                raise ValueError("DispositorshipNetworkProfile invariant failed: node incoming/outgoing counts must match edges")
            if node.reciprocal_count != reciprocal_counts[node.subject]:
                raise ValueError("DispositorshipNetworkProfile invariant failed: node reciprocal_count must match reciprocal edges")

        expected_isolated = [node.subject for node in self.nodes if node.is_isolated]
        if self.isolated_subjects != expected_isolated:
            raise ValueError("DispositorshipNetworkProfile invariant failed: isolated_subjects must match nodes")

        if self.nodes:
            max_degree = max(node.degree_count for node in self.nodes)
            expected_most_connected = [
                node.subject for node in self.nodes if node.degree_count == max_degree and max_degree > 0
            ]
        else:
            expected_most_connected = []
        if self.most_connected_subjects != expected_most_connected:
            raise ValueError("DispositorshipNetworkProfile invariant failed: most_connected_subjects must match node degrees")

    @property
    def node_count(self) -> int:
        """Return the number of network nodes."""

        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Return the number of directed network edges."""

        return len(self.edges)


@dataclass(slots=True)
class DispositorshipSubsystemProfile:
    """
    Full dispositorship subsystem profile tying together the Phase 1-9 layers.

    This is a backend hardening layer only. It consumes existing dispositorship
    results and verifies cross-layer consistency without recomputing doctrine.
    """

    profile: DispositorshipProfile
    condition_profiles: list[DispositorshipConditionProfile] = field(default_factory=list)
    chart_condition_profile: DispositorshipChartConditionProfile | None = None
    network_profile: DispositorshipNetworkProfile | None = None

    def __post_init__(self) -> None:
        condition_names = [profile.initial_subject for profile in self.condition_profiles]
        profile_names = [chain.initial_subject for chain in self.profile.chains]
        if condition_names != profile_names:
            raise ValueError("DispositorshipSubsystemProfile invariant failed: condition_profiles must align one-to-one with profile.chains")

        chain_map = {chain.initial_subject: chain for chain in self.profile.chains}
        for condition in self.condition_profiles:
            chain = chain_map.get(condition.initial_subject)
            if chain is None:
                raise ValueError(
                    "DispositorshipSubsystemProfile invariant failed: "
                    "condition profile references an unknown chain"
                )
            if condition.initial_sign != chain.initial_sign:
                raise ValueError("DispositorshipSubsystemProfile invariant failed: condition profile sign must match chain")
            if condition.subject_in_scope != chain.subject_in_scope:
                raise ValueError("DispositorshipSubsystemProfile invariant failed: condition profile scope must match chain")
            if condition.subject_has_dispositor != chain.subject_has_dispositor:
                raise ValueError("DispositorshipSubsystemProfile invariant failed: condition profile dispositor flag must match chain")
            if condition.termination_kind is not chain.termination_kind:
                raise ValueError("DispositorshipSubsystemProfile invariant failed: condition profile termination kind must match chain")
            if condition.terminal_subjects != chain.terminal_subjects:
                raise ValueError("DispositorshipSubsystemProfile invariant failed: condition profile terminal subjects must match chain")
            if condition.cycle_members != chain.cycle_members:
                raise ValueError("DispositorshipSubsystemProfile invariant failed: condition profile cycle members must match chain")
            if condition.visited_subjects != chain.visited_subjects:
                raise ValueError("DispositorshipSubsystemProfile invariant failed: condition profile visited_subjects must match chain")

        if self.chart_condition_profile is None:
            raise ValueError("DispositorshipSubsystemProfile invariant failed: chart_condition_profile must be present")
        if self.network_profile is None:
            raise ValueError("DispositorshipSubsystemProfile invariant failed: network_profile must be present")
        if self.chart_condition_profile.profiles != self.condition_profiles:
            raise ValueError("DispositorshipSubsystemProfile invariant failed: chart_condition_profile.profiles must match condition_profiles")

        in_scope_condition_names = [
            profile.initial_subject for profile in self.condition_profiles
            if profile.subject_in_scope and profile.initial_subject in _PLANET_ORDER
        ]
        network_node_names = [node.subject for node in self.network_profile.nodes]
        if network_node_names != in_scope_condition_names:
            raise ValueError("DispositorshipSubsystemProfile invariant failed: network nodes must align with in-scope condition profiles")

        expected_final_count = len(self.profile.final_dispositors)
        if self.chart_condition_profile.final_dispositor_count != expected_final_count:
            raise ValueError("DispositorshipSubsystemProfile invariant failed: chart final_dispositor_count must match profile.final_dispositors")

        expected_out_of_scope = sum(1 for profile in self.condition_profiles if profile.is_out_of_scope)
        if self.chart_condition_profile.out_of_scope_count != expected_out_of_scope:
            raise ValueError("DispositorshipSubsystemProfile invariant failed: chart out_of_scope_count must match condition profiles")

        direct_relations: set[tuple[str, str]] = set()
        for chain in self.profile.chains:
            if not chain.subject_in_scope or not chain.links:
                continue
            first = chain.links[0]
            if first.subject == first.dispositor:
                continue
            if first.dispositor not in network_node_names:
                continue
            direct_relations.add((first.subject, first.dispositor))
        network_relations = {(edge.source_subject, edge.target_subject) for edge in self.network_profile.edges}
        if network_relations != direct_relations:
            raise ValueError("DispositorshipSubsystemProfile invariant failed: network edges must match direct in-scope dispositorship relations")


@dataclass(slots=True)
class DispositorshipComparisonItem:
    """One named dispositorship result inside a comparative bundle."""

    name: str
    profile: DispositorshipProfile

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("DispositorshipComparisonItem invariant failed: name must be non-empty")


@dataclass(slots=True)
class DispositorshipComparisonBundle:
    """Comparative bundle of multiple named dispositorship profiles."""

    items: list[DispositorshipComparisonItem] = field(default_factory=list)
    shared_final_dispositors: tuple[str, ...] = ()
    all_final_dispositors: tuple[str, ...] = ()
    doctrine_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("DispositorshipComparisonBundle invariant failed: items must be non-empty")
        expected_names = tuple(item.name for item in self.items)
        if self.doctrine_names != expected_names:
            raise ValueError("DispositorshipComparisonBundle invariant failed: doctrine_names must match item names in order")

        shared: set[str] | None = None
        all_finals: set[str] = set()
        for item in self.items:
            finals = set(item.profile.final_dispositors)
            all_finals.update(finals)
            shared = finals if shared is None else shared & finals

        expected_shared = self._ordered_subjects(shared or set())
        expected_all = self._ordered_subjects(all_finals)
        if self.shared_final_dispositors != expected_shared:
            raise ValueError("DispositorshipComparisonBundle invariant failed: shared_final_dispositors must match the item intersection")
        if self.all_final_dispositors != expected_all:
            raise ValueError("DispositorshipComparisonBundle invariant failed: all_final_dispositors must match the item union")

    def get_item(self, name: str) -> DispositorshipComparisonItem:
        """Return the named comparison item."""

        for item in self.items:
            if item.name == name:
                return item
        raise KeyError("dispositorship comparison item not found")

    def _ordered_subjects(self, members: set[str]) -> tuple[str, ...]:
        ordered: list[str] = []
        for item in self.items:
            for subject in item.profile.final_dispositors:
                if subject in members and subject not in ordered:
                    ordered.append(subject)
        return tuple(ordered)


@dataclass(slots=True)
class PlanetaryConditionProfile:
    """
    Integrated per-planet condition profile derived from an existing dignity result.

    This is a backend synthesis layer only. It consumes preserved truth and
    classification already present on `PlanetaryDignity` and does not
    independently recompute doctrine.
    """

    planet: str
    essential_truth: EssentialDignityTruth | None
    essential_classification: EssentialDignityClassification | None
    accidental_truth: AccidentalDignityTruth
    accidental_classification: AccidentalDignityClassification
    sect_truth: SectTruth | None
    sect_classification: SectClassification | None
    solar_truth: SolarConditionTruth
    solar_classification: SolarConditionClassification
    all_receptions: list[PlanetaryReception] = field(default_factory=list)
    admitted_receptions: list[PlanetaryReception] = field(default_factory=list)
    scored_receptions: list[PlanetaryReception] = field(default_factory=list)
    mutual_reception_truth: list[MutualReceptionTruth] = field(default_factory=list)
    reception_classification: list[ReceptionClassification] = field(default_factory=list)
    strengthening_count: int = 0
    weakening_count: int = 0
    neutral_count: int = 0
    state: PlanetaryConditionState = PlanetaryConditionState.MIXED

    def __post_init__(self) -> None:
        derived_state = _derive_condition_state(
            self.strengthening_count,
            self.weakening_count,
        )
        if self.state is not derived_state:
            raise ValueError("PlanetaryConditionProfile invariant failed: state must match derived polarity counts")
        for reception in self.admitted_receptions:
            if reception not in self.all_receptions:
                raise ValueError("PlanetaryConditionProfile invariant failed: admitted receptions must be a subset of all_receptions")
        expected_scored = tuple(
            reception for reception in self.admitted_receptions if reception.mode is ReceptionMode.MUTUAL
        )
        if tuple(self.scored_receptions) != expected_scored:
            raise ValueError("PlanetaryConditionProfile invariant failed: scored_receptions must match admitted mutual receptions")

    @property
    def is_reinforced(self) -> bool:
        """Return True when the profile is structurally reinforced."""

        return self.state is PlanetaryConditionState.REINFORCED

    @property
    def is_mixed(self) -> bool:
        """Return True when the profile is structurally mixed."""

        return self.state is PlanetaryConditionState.MIXED

    @property
    def is_weakened(self) -> bool:
        """Return True when the profile is structurally weakened."""

        return self.state is PlanetaryConditionState.WEAKENED


@dataclass(slots=True)
class ChartConditionProfile:
    """
    Chart-wide condition profile derived from per-planet condition profiles.

    This is a backend aggregation layer only. It consumes existing
    `PlanetaryConditionProfile` results and does not recompute dignity
    doctrine independently.
    """

    profiles: list[PlanetaryConditionProfile] = field(default_factory=list)
    reinforced_count: int = 0
    mixed_count: int = 0
    weakened_count: int = 0
    strengthening_total: int = 0
    weakening_total: int = 0
    neutral_total: int = 0
    strongest_planets: list[str] = field(default_factory=list)
    weakest_planets: list[str] = field(default_factory=list)
    essential_strengthening_total: int = 0
    essential_weakening_total: int = 0
    accidental_strengthening_total: int = 0
    accidental_weakening_total: int = 0
    reception_participation_total: int = 0

    def __post_init__(self) -> None:
        reinforced = sum(1 for profile in self.profiles if profile.state is PlanetaryConditionState.REINFORCED)
        mixed = sum(1 for profile in self.profiles if profile.state is PlanetaryConditionState.MIXED)
        weakened = sum(1 for profile in self.profiles if profile.state is PlanetaryConditionState.WEAKENED)
        if (self.reinforced_count, self.mixed_count, self.weakened_count) != (reinforced, mixed, weakened):
            raise ValueError("ChartConditionProfile invariant failed: state counts must match profile states")

        strengthening_total = sum(profile.strengthening_count for profile in self.profiles)
        weakening_total = sum(profile.weakening_count for profile in self.profiles)
        neutral_total = sum(profile.neutral_count for profile in self.profiles)
        if (self.strengthening_total, self.weakening_total, self.neutral_total) != (
            strengthening_total,
            weakening_total,
            neutral_total,
        ):
            raise ValueError("ChartConditionProfile invariant failed: polarity totals must match profile totals")

        expected_reception_participation = sum(len(profile.admitted_receptions) for profile in self.profiles)
        if self.reception_participation_total != expected_reception_participation:
            raise ValueError("ChartConditionProfile invariant failed: reception participation total must match profile receptions")

        ordered_names = [
            profile.planet for profile in sorted(
                self.profiles,
                key=lambda profile: _PLANET_ORDER.index(profile.planet)
                if profile.planet in _PLANET_ORDER else 99,
            )
        ]
        if [profile.planet for profile in self.profiles] != ordered_names:
            raise ValueError("ChartConditionProfile invariant failed: profiles must be in deterministic planet order")

    @property
    def strongest_count(self) -> int:
        """Return the number of strongest planets reported."""

        return len(self.strongest_planets)

    @property
    def weakest_count(self) -> int:
        """Return the number of weakest planets reported."""

        return len(self.weakest_planets)


@dataclass(slots=True)
class ConditionNetworkNode:
    """Per-planet node summary for the reception / condition network."""

    planet: str
    profile: PlanetaryConditionProfile
    incoming_count: int = 0
    outgoing_count: int = 0
    mutual_count: int = 0
    total_degree: int = 0

    def __post_init__(self) -> None:
        if self.planet != self.profile.planet:
            raise ValueError("ConditionNetworkNode invariant failed: node planet must match profile planet")
        if self.total_degree != self.incoming_count + self.outgoing_count:
            raise ValueError("ConditionNetworkNode invariant failed: total_degree must equal incoming_count + outgoing_count")
        if self.mutual_count > self.outgoing_count:
            raise ValueError("ConditionNetworkNode invariant failed: mutual_count cannot exceed outgoing_count")

    @property
    def is_isolated(self) -> bool:
        """Return True when the node has no incoming or outgoing reception links."""

        return self.total_degree == 0


@dataclass(slots=True)
class ConditionNetworkEdge:
    """Directed reception edge in the reception / condition network."""

    source_planet: str
    target_planet: str
    basis: ReceptionBasis
    mode: ReceptionMode

    def __post_init__(self) -> None:
        if self.source_planet == self.target_planet:
            raise ValueError("ConditionNetworkEdge invariant failed: source_planet must differ from target_planet")

    @property
    def is_mutual(self) -> bool:
        """Return True when this edge participates in a mutual reception."""

        return self.mode is ReceptionMode.MUTUAL


@dataclass(slots=True)
class ConditionNetworkProfile:
    """
    Directed reception / condition network derived from existing backend truth.

    This is a structural backend graph layer only. It consumes integrated
    condition profiles and their admitted receptions and does not recompute
    dignity doctrine independently.
    """

    nodes: list[ConditionNetworkNode] = field(default_factory=list)
    edges: list[ConditionNetworkEdge] = field(default_factory=list)
    isolated_planets: list[str] = field(default_factory=list)
    most_connected_planets: list[str] = field(default_factory=list)
    mutual_edge_count: int = 0
    unilateral_edge_count: int = 0

    def __post_init__(self) -> None:
        isolated = [node.planet for node in self.nodes if node.is_isolated]
        if self.isolated_planets != isolated:
            raise ValueError("ConditionNetworkProfile invariant failed: isolated_planets must match node isolation state")
        if self.mutual_edge_count != sum(1 for edge in self.edges if edge.is_mutual):
            raise ValueError("ConditionNetworkProfile invariant failed: mutual_edge_count must match mutual edges")
        if self.unilateral_edge_count != sum(1 for edge in self.edges if not edge.is_mutual):
            raise ValueError("ConditionNetworkProfile invariant failed: unilateral_edge_count must match unilateral edges")
        expected_node_order = [
            node.planet for node in sorted(
                self.nodes,
                key=lambda node: _PLANET_ORDER.index(node.planet) if node.planet in _PLANET_ORDER else 99,
            )
        ]
        if [node.planet for node in self.nodes] != expected_node_order:
            raise ValueError("ConditionNetworkProfile invariant failed: nodes must be in deterministic planet order")

    @property
    def node_count(self) -> int:
        """Return the number of network nodes."""

        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Return the number of directed network edges."""

        return len(self.edges)


@dataclass(slots=True)
class EssentialDignityClassification:
    """Lean typed classification of the already-computed essential dignity truth."""

    kind: EssentialDignityKind
    polarity: ConditionPolarity


@dataclass(slots=True)
class AccidentalConditionClassification:
    """Typed classification for one already-computed accidental condition."""

    kind: AccidentalConditionKind
    category: str
    polarity: ConditionPolarity
    score: int
    label: str


@dataclass(slots=True)
class AccidentalDignityClassification:
    """Classification wrapper over the existing accidental condition truth."""

    conditions: list[AccidentalConditionClassification] = field(default_factory=list)


@dataclass(slots=True)
class SectClassification:
    """Lean typed sect-state classification for already-computed sect truth."""

    state: SectStateKind
    in_sect: bool
    in_hayz: bool


@dataclass(slots=True)
class SolarConditionClassification:
    """Typed solar-condition classification for already-computed solar truth."""

    kind: SolarConditionKind
    polarity: ConditionPolarity
    present: bool


@dataclass(slots=True)
class ReceptionClassification:
    """Typed mutual-reception classification for one already-computed reception."""

    kind: ReceptionKind
    polarity: ConditionPolarity
    other_planet: str
    label: str
    score: int

@dataclass(slots=True)
class EssentialDignityTruth:
    """
    Structured record of the essential dignity rule that matched.

    This preserves the doctrinal path used to reach the public
    `essential_dignity` label without changing scoring or rule priority.
    """

    category: str
    label: str
    score: int
    sign: str
    matching_signs: tuple[str, ...]
    matched: bool = True


@dataclass(slots=True)
class AccidentalDignityCondition:
    """One explicit accidental dignity or debility that contributed to the result."""

    category: str
    code: str
    label: str
    score: int


@dataclass(slots=True)
class SolarConditionTruth:
    """Structured solar-proximity truth for non-luminary planets."""

    present: bool
    condition: str | None = None
    label: str | None = None
    score: int = 0
    distance_from_sun: float | None = None


@dataclass(slots=True)
class MutualReceptionTruth:
    """Structured mutual reception truth for one counterpart planet."""

    other_planet: str
    reception_type: str
    label: str
    score: int


@dataclass(slots=True)
class SectTruth:
    """
    Structured sect and hayz truth.

    This preserves the intermediate judgments currently used only to decide
    whether the flattened `In Hayz` accidental label should be emitted.
    """

    is_day_chart: bool
    sect_light: str
    planet_sect: str | None
    mercury_rises_before_sun: bool
    in_sect: bool
    in_hayz: bool
    preferred_hemisphere: str | None
    actual_hemisphere: str
    hemisphere_matches: bool
    preferred_gender: str | None
    actual_gender: str
    gender_matches: bool


@dataclass(slots=True)
class AccidentalDignityTruth:
    """Structured accidental dignity truth emitted alongside legacy labels."""

    conditions: list[AccidentalDignityCondition] = field(default_factory=list)
    house_condition: AccidentalDignityCondition | None = None
    motion_condition: AccidentalDignityCondition | None = None
    solar_condition: SolarConditionTruth = field(default_factory=lambda: SolarConditionTruth(False))
    mutual_receptions: list[MutualReceptionTruth] = field(default_factory=list)
    hayz_condition: AccidentalDignityCondition | None = None
    halb_condition: AccidentalDignityCondition | None = None
    joy_condition: AccidentalDignityCondition | None = None
    oriental_condition: AccidentalDignityCondition | None = None
    besieged_condition: AccidentalDignityCondition | None = None


@dataclass(slots=True)
class PlanetaryDignity:
    """
    RITE: The Crowned Planet — the complete dignity portrait of a single
          planet in a chart, from its essential throne to every accidental
          honour or affliction it carries.

    THEOREM: Immutable record of a planet's essential dignity, accidental
             dignities, and composite score, computed from its sign, house,
             motion, solar proximity, and mutual receptions, while also
             preserving the structured doctrinal path behind those judgments.

    RITE OF PURPOSE:
        PlanetaryDignity is the result vessel of DignitiesService.  It
        consolidates every dignity judgment for one planet into a single
        object so that callers can read the essential dignity label, the
        list of accidental conditions, and the total score without
        re-running any computation.  Without this vessel, dignity results
        would be scattered across multiple parallel lists.

    LAW OF OPERATION:
        Responsibilities:
            - Store the public dignity labels and scores used by current
              callers.
            - Preserve structured essential, accidental, sect/hayz, solar,
              and reception truth for later classification, policy, and
              formal reception layers.
            - Expose a lean explicit classification layer that describes,
              but does not alter, already-computed truth.
            - Expose small read-only inspectability properties so callers
              can query the classification surface directly.
            - Distinguish doctrine-detected receptions, policy-admitted
              receptions, and the scored mutual subset explicitly.
            - Expose an integrated per-planet condition profile derived from
              the existing dignity, sect, solar, and reception truth.
            - Enforce internal consistency so truth, classification, and
              legacy labels do not silently drift apart.
            - Render a compact tabular repr.
        Non-responsibilities:
            - Does not compute dignities; that is DignitiesService's role.
            - Does not validate that essential_dignity is a known label.
            - Does not perform doctrinal policy, interpretation, or
              chart-wide condition synthesis.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - None beyond Python builtins.
        Structural invariants:
            - total_score == essential_score + accidental_score.
            - essential_dignity is one of: Domicile, Exaltation, Detriment,
              Fall, Peregrine.

    Canon: William Lilly, Christian Astrology (1647), Book I

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.dignities.PlanetaryDignity",
        "risk": "low",
        "api": {"frozen": ["planet", "sign", "degree", "house", "essential_dignity", "essential_score", "accidental_dignities", "accidental_score", "total_score", "is_retrograde", "essential_truth", "accidental_truth", "sect_truth", "solar_truth", "mutual_reception_truth", "essential_classification", "accidental_classification", "sect_classification", "solar_classification", "reception_classification"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    planet:              str
    sign:                str
    degree:              float
    house:               int
    essential_dignity:   str          # "Domicile" | "Exaltation" | "Detriment" | "Fall" | "Peregrine"
    essential_score:     int
    accidental_dignities: list[str]  = field(default_factory=list)
    accidental_score:    int          = 0
    total_score:         int          = 0
    is_retrograde:       bool         = False
    essential_truth:     EssentialDignityTruth | None = None
    accidental_truth:    AccidentalDignityTruth = field(default_factory=AccidentalDignityTruth)
    sect_truth:          SectTruth | None = None
    solar_truth:         SolarConditionTruth = field(default_factory=lambda: SolarConditionTruth(False))
    all_receptions:      list[PlanetaryReception] = field(default_factory=list)
    receptions:          list[PlanetaryReception] = field(default_factory=list)
    mutual_reception_truth: list[MutualReceptionTruth] = field(default_factory=list)
    essential_classification: EssentialDignityClassification | None = None
    accidental_classification: AccidentalDignityClassification = field(default_factory=AccidentalDignityClassification)
    sect_classification: SectClassification | None = None
    solar_classification: SolarConditionClassification = field(
        default_factory=lambda: SolarConditionClassification(SolarConditionKind.NONE, ConditionPolarity.NEUTRAL, False)
    )
    reception_classification: list[ReceptionClassification] = field(default_factory=list)
    condition_profile: PlanetaryConditionProfile | None = None

    def __post_init__(self) -> None:
        self._validate_consistency()

    @property
    def essential_kind(self) -> EssentialDignityKind | None:
        """Read-only pass-through for the classified essential dignity kind."""

        return None if self.essential_classification is None else self.essential_classification.kind

    @property
    def essential_polarity(self) -> ConditionPolarity | None:
        """Read-only pass-through for the classified essential dignity polarity."""

        return None if self.essential_classification is None else self.essential_classification.polarity

    @property
    def accidental_condition_kinds(self) -> tuple[AccidentalConditionKind, ...]:
        """Read-only pass-through for accidental condition kinds."""

        return tuple(condition.kind for condition in self.accidental_classification.conditions)

    @property
    def sect_state(self) -> SectStateKind | None:
        """Read-only pass-through for the classified sect state."""

        return None if self.sect_classification is None else self.sect_classification.state

    @property
    def solar_kind(self) -> SolarConditionKind:
        """Read-only pass-through for the classified solar condition kind."""

        return self.solar_classification.kind

    @property
    def reception_kinds(self) -> tuple[ReceptionKind, ...]:
        """Read-only pass-through for mutual reception kinds."""

        return tuple(reception.kind for reception in self.reception_classification)

    @property
    def reception_modes(self) -> tuple[ReceptionMode, ...]:
        """Read-only pass-through for formal reception modes."""

        return tuple(reception.mode for reception in self.receptions)

    @property
    def admitted_receptions(self) -> tuple[PlanetaryReception, ...]:
        """Policy-admitted receptions considered by the current dignity run."""

        return tuple(self.receptions)

    @property
    def scored_receptions(self) -> tuple[PlanetaryReception, ...]:
        """Admitted receptions that actually contribute to current scoring."""

        return tuple(reception for reception in self.receptions if reception.mode is ReceptionMode.MUTUAL)

    @property
    def detected_reception_bases(self) -> tuple[ReceptionBasis, ...]:
        """Doctrinal bases present across all detected receptions."""

        return tuple(reception.basis for reception in self.all_receptions)

    @property
    def admitted_reception_bases(self) -> tuple[ReceptionBasis, ...]:
        """Doctrinal bases present across policy-admitted receptions."""

        return tuple(reception.basis for reception in self.receptions)

    @property
    def has_solar_condition(self) -> bool:
        """Return True when a solar condition is explicitly present."""

        return self.solar_classification.present

    @property
    def has_mutual_reception(self) -> bool:
        """Return True when at least one mutual reception is present."""

        return bool(self.reception_classification)

    @property
    def has_unilateral_reception(self) -> bool:
        """Return True when at least one unilateral reception is present."""

        return any(reception.mode is ReceptionMode.UNILATERAL for reception in self.receptions)

    @property
    def has_detected_reception(self) -> bool:
        """Return True when any reception is doctrinally detected, admitted or not."""

        return bool(self.all_receptions)

    @property
    def condition_state(self) -> PlanetaryConditionState | None:
        """Read-only pass-through for the integrated condition profile state."""

        return None if self.condition_profile is None else self.condition_profile.state

    def _validate_consistency(self) -> None:
        if self.total_score != self.essential_score + self.accidental_score:
            raise ValueError("PlanetaryDignity invariant failed: total_score must equal essential_score + accidental_score")

        if self.essential_truth is not None:
            if self.essential_truth.label != self.essential_dignity:
                raise ValueError("PlanetaryDignity invariant failed: essential_truth.label must match essential_dignity")
            if self.essential_truth.score != self.essential_score:
                raise ValueError("PlanetaryDignity invariant failed: essential_truth.score must match essential_score")
            if self.essential_truth.sign != self.sign:
                raise ValueError("PlanetaryDignity invariant failed: essential_truth.sign must match sign")

        accidental_labels = [condition.label for condition in self.accidental_truth.conditions]
        accidental_scores = [condition.score for condition in self.accidental_truth.conditions]
        if accidental_labels != self.accidental_dignities:
            raise ValueError("PlanetaryDignity invariant failed: accidental_truth labels must match accidental_dignities")
        if sum(accidental_scores) != self.accidental_score:
            raise ValueError("PlanetaryDignity invariant failed: accidental_truth scores must sum to accidental_score")

        if self.solar_truth != self.accidental_truth.solar_condition:
            raise ValueError("PlanetaryDignity invariant failed: solar_truth must match accidental_truth.solar_condition")
        if self.mutual_reception_truth != self.accidental_truth.mutual_receptions:
            raise ValueError("PlanetaryDignity invariant failed: mutual_reception_truth must match accidental_truth.mutual_receptions")

        for reception in self.receptions:
            if reception not in self.all_receptions:
                raise ValueError("PlanetaryDignity invariant failed: admitted receptions must be a subset of all_receptions")

        mutual_relations = [reception for reception in self.receptions if reception.mode is ReceptionMode.MUTUAL]
        if len(mutual_relations) != len(self.mutual_reception_truth):
            raise ValueError("PlanetaryDignity invariant failed: mutual reception relation count mismatch")
        for relation, truth in zip(mutual_relations, self.mutual_reception_truth):
            if relation.host_planet != truth.other_planet:
                raise ValueError("PlanetaryDignity invariant failed: mutual reception relation host mismatch")
            if relation.basis.value != truth.reception_type:
                raise ValueError("PlanetaryDignity invariant failed: mutual reception relation basis mismatch")

        if self.essential_classification is not None:
            if self.essential_truth is None:
                raise ValueError("PlanetaryDignity invariant failed: essential_classification requires essential_truth")
            if self.essential_polarity != _score_polarity(self.essential_truth.score):
                raise ValueError("PlanetaryDignity invariant failed: essential classification polarity mismatch")

        classification_labels = [condition.label for condition in self.accidental_classification.conditions]
        classification_scores = [condition.score for condition in self.accidental_classification.conditions]
        if classification_labels != accidental_labels:
            raise ValueError("PlanetaryDignity invariant failed: accidental classification labels must match accidental truth labels")
        if classification_scores != accidental_scores:
            raise ValueError("PlanetaryDignity invariant failed: accidental classification scores must match accidental truth scores")

        if self.sect_classification is not None:
            if self.sect_truth is None:
                raise ValueError("PlanetaryDignity invariant failed: sect_classification requires sect_truth")
            if self.sect_classification.in_sect != self.sect_truth.in_sect:
                raise ValueError("PlanetaryDignity invariant failed: sect classification in_sect mismatch")
            if self.sect_classification.in_hayz != self.sect_truth.in_hayz:
                raise ValueError("PlanetaryDignity invariant failed: sect classification in_hayz mismatch")

        if self.solar_classification.present != self.solar_truth.present:
            raise ValueError("PlanetaryDignity invariant failed: solar classification presence mismatch")
        if self.solar_classification.polarity != _score_polarity(self.solar_truth.score):
            raise ValueError("PlanetaryDignity invariant failed: solar classification polarity mismatch")

        if len(self.reception_classification) != len(self.mutual_reception_truth):
            raise ValueError("PlanetaryDignity invariant failed: reception classification count mismatch")
        for classified, truth in zip(self.reception_classification, self.mutual_reception_truth):
            if classified.other_planet != truth.other_planet:
                raise ValueError("PlanetaryDignity invariant failed: reception classification counterpart mismatch")
            if classified.label != truth.label:
                raise ValueError("PlanetaryDignity invariant failed: reception classification label mismatch")
            if classified.score != truth.score:
                raise ValueError("PlanetaryDignity invariant failed: reception classification score mismatch")
            if classified.polarity != _score_polarity(truth.score):
                raise ValueError("PlanetaryDignity invariant failed: reception classification polarity mismatch")
        if tuple(self.scored_receptions) != tuple(mutual_relations):
            raise ValueError("PlanetaryDignity invariant failed: scored_receptions must match admitted mutual receptions")
        if self.condition_profile is not None:
            if self.condition_profile.planet != self.planet:
                raise ValueError("PlanetaryDignity invariant failed: condition profile planet mismatch")
            if self.condition_profile.essential_truth != self.essential_truth:
                raise ValueError("PlanetaryDignity invariant failed: condition profile essential truth mismatch")
            if self.condition_profile.accidental_truth != self.accidental_truth:
                raise ValueError("PlanetaryDignity invariant failed: condition profile accidental truth mismatch")
            if self.condition_profile.sect_truth != self.sect_truth:
                raise ValueError("PlanetaryDignity invariant failed: condition profile sect truth mismatch")
            if self.condition_profile.solar_truth != self.solar_truth:
                raise ValueError("PlanetaryDignity invariant failed: condition profile solar truth mismatch")
            if tuple(self.condition_profile.admitted_receptions) != tuple(self.receptions):
                raise ValueError("PlanetaryDignity invariant failed: condition profile admitted receptions mismatch")
            if tuple(self.condition_profile.scored_receptions) != tuple(self.scored_receptions):
                raise ValueError("PlanetaryDignity invariant failed: condition profile scored receptions mismatch")

    def __repr__(self) -> str:
        acc = ", ".join(self.accidental_dignities) if self.accidental_dignities else "—"
        return (f"{self.planet:<9} {self.sign:<13} H{self.house:2d}  "
                f"{self.essential_dignity:<10} score={self.total_score:+d}  "
                f"[{acc}]")

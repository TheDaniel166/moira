"""
Moira -- primary_directions.py
The Primary Direction Engine: governs Placidus mundane primary direction
arc computation for natal charts.

Boundary: owns speculum construction, mundane fraction arithmetic, direct and
converse arc computation, and symbolic time-key conversion. Delegates ecliptic-
to-equatorial coordinate transformation to constants (DEG2RAD/RAD2DEG). Does
NOT own natal chart construction, house computation, or ephemeris state.

Public surface:
    DIRECT, CONVERSE,
    SpeculumEntry, PrimaryArc,
    speculum, find_primary_arcs

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - Chart and HouseCusps instances must be fully constructed before calling
      speculum() or find_primary_arcs().
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Iterable

from .constants import Body, DEG2RAD
from .primary_direction_converse import PrimaryDirectionConverseDoctrine
from .primary_direction_keys import (
    PrimaryDirectionKey,
    PrimaryDirectionKeyFamily,
    PrimaryDirectionKeyPolicy,
    convert_arc_to_time,
)
from .primary_direction_methods import PrimaryDirectionMethod
from .primary_direction_perfections import (
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionPerfectionPolicy,
)
from .primary_direction_spaces import PrimaryDirectionSpace
from .primary_direction_targets import (
    PrimaryDirectionTargetClass,
    PrimaryDirectionTargetPolicy,
    primary_direction_target_truth,
)

__all__ = [
    "DIRECT",
    "CONVERSE",
    "PrimaryDirectionSpace",
    "PrimaryDirectionMotion",
    "PrimaryDirectionConverseDoctrine",
    "PrimaryDirectionsConditionState",
    "PrimaryDirectionsPolicy",
    "PrimaryDirectionKey",
    "PrimaryDirectionKeyFamily",
    "PrimaryDirectionKeyPolicy",
    "PrimaryDirectionMethod",
    "PrimaryDirectionPerfectionKind",
    "PrimaryDirectionPerfectionPolicy",
    "PrimaryDirectionTargetClass",
    "PrimaryDirectionTargetPolicy",
    "SpeculumEntry",
    "PrimaryArc",
    "PrimaryDirectionRelation",
    "PrimaryDirectionRelationProfile",
    "PrimaryDirectionsSignificatorProfile",
    "PrimaryDirectionsAggregateProfile",
    "PrimaryDirectionsNetworkNode",
    "PrimaryDirectionsNetworkEdge",
    "PrimaryDirectionsNetworkProfile",
    "speculum",
    "find_primary_arcs",
    "relate_primary_arc",
    "evaluate_primary_direction_relations",
    "evaluate_primary_direction_condition",
    "evaluate_primary_directions_aggregate",
    "evaluate_primary_directions_network",
]

if TYPE_CHECKING:
    from .__init__ import Chart
    from .houses import HouseCusps


_DEFAULT_SOLAR_RATE = 360.0 / 365.25

DIRECT = "D"
CONVERSE = "C"

class PrimaryDirectionMotion(StrEnum):
    DIRECT = "direct"
    CONVERSE = "converse"


class PrimaryDirectionsConditionState(StrEnum):
    DIRECT_ONLY = "direct_only"
    CONVERSE_ONLY = "converse_only"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsPolicy:
    method: PrimaryDirectionMethod = PrimaryDirectionMethod.PLACIDUS_MUNDANE
    space: PrimaryDirectionSpace = PrimaryDirectionSpace.IN_MUNDO
    include_converse: bool = True
    converse_doctrine: PrimaryDirectionConverseDoctrine = (
        PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
    )
    key_policy: PrimaryDirectionKeyPolicy = field(default_factory=PrimaryDirectionKeyPolicy)
    target_policy: PrimaryDirectionTargetPolicy = field(default_factory=PrimaryDirectionTargetPolicy)
    perfection_policy: PrimaryDirectionPerfectionPolicy = field(default_factory=PrimaryDirectionPerfectionPolicy)

    def __post_init__(self) -> None:
        if self.method is not PrimaryDirectionMethod.PLACIDUS_MUNDANE:
            if self.method is not PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC:
                raise ValueError(f"Unsupported primary direction method: {self.method}")
        if self.space not in (PrimaryDirectionSpace.IN_MUNDO, PrimaryDirectionSpace.IN_ZODIACO):
            raise ValueError(f"Unsupported primary direction space: {self.space}")
        if self.include_converse and self.converse_doctrine is PrimaryDirectionConverseDoctrine.DIRECT_ONLY:
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: include_converse requires converse doctrine"
            )
        if (not self.include_converse) and (
            self.converse_doctrine is not PrimaryDirectionConverseDoctrine.DIRECT_ONLY
        ):
            raise ValueError(
                "PrimaryDirectionsPolicy invariant failed: direct-only policy must disable converse"
            )
        if self.space is PrimaryDirectionSpace.IN_MUNDO:
            if self.perfection_policy.kind is not PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION:
                raise ValueError(
                    "PrimaryDirectionsPolicy invariant failed: in_mundo requires mundane position perfection"
                )
        else:
            if self.perfection_policy.kind is not PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION:
                raise ValueError(
                    "PrimaryDirectionsPolicy invariant failed: in_zodiaco requires zodiacal longitude perfection"
                )

    @property
    def admitted_motions(self) -> tuple[PrimaryDirectionMotion, ...]:
        if self.include_converse:
            return (PrimaryDirectionMotion.DIRECT, PrimaryDirectionMotion.CONVERSE)
        return (PrimaryDirectionMotion.DIRECT,)


@dataclass(slots=True)
class SpeculumEntry:
    name: str
    lon: float
    lat: float
    ra: float
    dec: float
    ha: float
    dsa: float
    nsa: float
    upper: bool
    f: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("SpeculumEntry requires a non-empty name")
        if not (0.0 <= self.lon < 360.0):
            raise ValueError(f"SpeculumEntry longitude must be normalized: {self.lon}")
        if not (0.0 <= self.ra < 360.0):
            raise ValueError(f"SpeculumEntry right ascension must be normalized: {self.ra}")
        if not (-90.0 <= self.dec <= 90.0):
            raise ValueError(f"SpeculumEntry declination out of range: {self.dec}")
        if not (-180.0 <= self.ha <= 180.0):
            raise ValueError(f"SpeculumEntry hour angle out of range: {self.ha}")
        if not (0.0 <= self.dsa <= 180.0):
            raise ValueError(f"SpeculumEntry DSA out of range: {self.dsa}")
        if not (0.0 <= self.nsa <= 180.0):
            raise ValueError(f"SpeculumEntry NSA out of range: {self.nsa}")
        if abs((self.dsa + self.nsa) - 180.0) > 1e-7:
            raise ValueError("SpeculumEntry invariant failed: dsa + nsa must equal 180")
        if not (-2.0 - 1e-9 <= self.f <= 2.0 + 1e-9):
            raise ValueError(f"SpeculumEntry mundane fraction out of range: {self.f}")
        if self.upper != (abs(self.ha) <= self.dsa + 1e-9):
            raise ValueError(
                "SpeculumEntry invariant failed: upper hemisphere flag does not match HA/DSA"
            )

    @classmethod
    def build(
        cls,
        name: str,
        lon: float,
        lat: float,
        armc: float,
        obliquity: float,
        geo_lat: float,
    ) -> SpeculumEntry:
        eps = obliquity * DEG2RAD
        phi = geo_lat * DEG2RAD
        l = lon * DEG2RAD
        b = lat * DEG2RAD

        sin_dec = math.sin(b) * math.cos(eps) + math.cos(b) * math.sin(eps) * math.sin(l)
        sin_dec = max(-1.0, min(1.0, sin_dec))
        dec_r = math.asin(sin_dec)

        y = math.sin(l) * math.cos(eps) - math.tan(b) * math.sin(eps)
        ra = math.degrees(math.atan2(y, math.cos(l))) % 360.0
        dec = math.degrees(dec_r)

        ha = (armc - ra + 180.0) % 360.0 - 180.0

        arg = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec_r)))
        dsa = math.degrees(math.acos(arg))
        nsa = 180.0 - dsa

        upper = abs(ha) <= dsa + 1e-9
        if upper:
            f = ha / dsa if dsa > 1e-9 else 0.0
        elif ha > 0:
            f = 1.0 + (ha - dsa) / nsa if nsa > 1e-9 else 1.0
        else:
            f = -1.0 - (-ha - dsa) / nsa if nsa > 1e-9 else -1.0

        return cls(
            name=name,
            lon=lon % 360.0,
            lat=lat,
            ra=ra,
            dec=dec,
            ha=ha,
            dsa=dsa,
            nsa=nsa,
            upper=upper,
            f=f,
        )

    @property
    def hemisphere(self) -> str:
        return "upper" if self.upper else "lower"

    @property
    def is_eastern(self) -> bool:
        return self.ha < 0.0

    @property
    def is_western(self) -> bool:
        return self.ha > 0.0

    @property
    def mundane_sector(self) -> str:
        if self.upper:
            return "upper_east" if self.is_eastern else "upper_west"
        return "lower_east" if self.is_eastern else "lower_west"

    def __repr__(self) -> str:
        hem = "UH" if self.upper else "LH"
        return (
            f"Speculum({self.name:<12} "
            f"lon={self.lon:7.3f}deg RA={self.ra:7.3f}deg Dec={self.dec:+7.3f}deg "
            f"HA={self.ha:+8.3f}deg DSA={self.dsa:6.3f}deg "
            f"f={self.f:+6.3f} {hem})"
        )


@dataclass(slots=True)
class PrimaryArc:
    significator: str
    promissor: str
    arc: float
    direction: str
    method: PrimaryDirectionMethod = field(default=PrimaryDirectionMethod.PLACIDUS_MUNDANE)
    space: PrimaryDirectionSpace = field(default=PrimaryDirectionSpace.IN_MUNDO)
    motion: PrimaryDirectionMotion = field(default=PrimaryDirectionMotion.DIRECT)
    solar_rate: float = field(default=_DEFAULT_SOLAR_RATE)

    def __post_init__(self) -> None:
        if not self.significator or not self.promissor:
            raise ValueError("PrimaryArc requires non-empty significator and promissor")
        if self.significator == self.promissor:
            raise ValueError("PrimaryArc invariant failed: self-directions are not admitted")
        if self.arc <= 0.0:
            raise ValueError("PrimaryArc invariant failed: arc must be positive")
        if self.solar_rate <= 0.0:
            raise ValueError("PrimaryArc invariant failed: solar_rate must be positive")
        expected_direction = DIRECT if self.motion is PrimaryDirectionMotion.DIRECT else CONVERSE
        if self.direction != expected_direction:
            raise ValueError("PrimaryArc invariant failed: direction must match motion")
        if self.method not in (
            PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
        ):
            raise ValueError(f"Unsupported primary direction method: {self.method}")
        if self.space not in (PrimaryDirectionSpace.IN_MUNDO, PrimaryDirectionSpace.IN_ZODIACO):
            raise ValueError(f"Unsupported primary direction space: {self.space}")

    def years(self, key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD) -> float:
        return convert_arc_to_time(self.arc, key, solar_rate=self.solar_rate)

    @property
    def is_direct(self) -> bool:
        return self.motion is PrimaryDirectionMotion.DIRECT

    @property
    def is_converse(self) -> bool:
        return self.motion is PrimaryDirectionMotion.CONVERSE

    @property
    def key_family(self) -> PrimaryDirectionKeyFamily:
        return PrimaryDirectionKeyPolicy().family

    def __repr__(self) -> str:
        return (
            f"PrimaryArc({self.significator} <- {self.promissor}  "
            f"arc={self.arc:.4f}  {self.direction}  "
            f"{self.years():.2f} yr [Naibod])"
        )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelation:
    arc: PrimaryArc
    relation_kind: PrimaryDirectionPerfectionKind
    converse_doctrine: PrimaryDirectionConverseDoctrine
    key_policy: PrimaryDirectionKeyPolicy

    def __post_init__(self) -> None:
        if self.relation_kind not in (
            PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION,
            PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION,
        ):
            raise ValueError(f"Unsupported primary direction relation kind: {self.relation_kind}")
        if (
            self.arc.motion is PrimaryDirectionMotion.CONVERSE
            and self.converse_doctrine is PrimaryDirectionConverseDoctrine.DIRECT_ONLY
        ):
            raise ValueError(
                "PrimaryDirectionRelation invariant failed: converse arc not admitted by direct-only doctrine"
            )

    @property
    def years(self) -> float:
        return self.arc.years(self.key_policy.key)


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationProfile:
    arc: PrimaryArc
    detected_relation: PrimaryDirectionRelation
    admitted_relations: tuple[PrimaryDirectionRelation, ...]
    scored_relations: tuple[PrimaryDirectionRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.arc != self.arc:
            raise ValueError(
                "PrimaryDirectionRelationProfile invariant failed: detected relation must belong to arc"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionRelationProfile invariant failed: scored relations must be admitted"
                )

    @property
    def admitted_relation_kinds(self) -> tuple[PrimaryDirectionPerfectionKind, ...]:
        return tuple(relation.relation_kind for relation in self.admitted_relations)

    @property
    def scored_relation_kinds(self) -> tuple[PrimaryDirectionPerfectionKind, ...]:
        return tuple(relation.relation_kind for relation in self.scored_relations)


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsSignificatorProfile:
    significator: str
    arcs: tuple[PrimaryArc, ...]
    relation_profiles: tuple[PrimaryDirectionRelationProfile, ...]
    state: PrimaryDirectionsConditionState
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float

    def __post_init__(self) -> None:
        if not self.significator:
            raise ValueError("PrimaryDirectionsSignificatorProfile requires a significator")
        if not self.arcs:
            raise ValueError("PrimaryDirectionsSignificatorProfile requires at least one arc")
        if len(self.arcs) != len(self.relation_profiles):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: arcs/profiles length mismatch"
            )
        if any(arc.significator != self.significator for arc in self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: all arcs must share significator"
            )
        if self.direct_count + self.converse_count != len(self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: direction counts do not match arc count"
            )
        if self.nearest_arc != min(arc.arc for arc in self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: nearest_arc mismatch"
            )
        if self.farthest_arc != max(arc.arc for arc in self.arcs):
            raise ValueError(
                "PrimaryDirectionsSignificatorProfile invariant failed: farthest_arc mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsAggregateProfile:
    profiles: tuple[PrimaryDirectionsSignificatorProfile, ...]
    total_arcs: int
    direct_count: int
    converse_count: int
    nearest_arc: float
    farthest_arc: float
    strongest_significator: str
    weakest_significator: str

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionsAggregateProfile requires at least one significator profile")
        unique_significators = {profile.significator for profile in self.profiles}
        if len(unique_significators) != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: duplicate significator profiles"
            )
        computed_total = sum(len(profile.arcs) for profile in self.profiles)
        if self.total_arcs != computed_total:
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: total_arcs mismatch"
            )
        if self.direct_count != sum(profile.direct_count for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: direct_count mismatch"
            )
        if self.converse_count != sum(profile.converse_count for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: converse_count mismatch"
            )
        if self.nearest_arc != min(profile.nearest_arc for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: nearest_arc mismatch"
            )
        if self.farthest_arc != max(profile.farthest_arc for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: farthest_arc mismatch"
            )
        strength_map = {profile.significator: len(profile.arcs) for profile in self.profiles}
        strongest = max(strength_map.items(), key=lambda item: (item[1], item[0]))[0]
        weakest = min(strength_map.items(), key=lambda item: (item[1], item[0]))[0]
        if self.strongest_significator != strongest:
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: strongest_significator mismatch"
            )
        if self.weakest_significator != weakest:
            raise ValueError(
                "PrimaryDirectionsAggregateProfile invariant failed: weakest_significator mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsNetworkNode:
    name: str
    incoming_count: int
    outgoing_count: int
    total_count: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("PrimaryDirectionsNetworkNode requires a non-empty name")
        if self.total_count != self.incoming_count + self.outgoing_count:
            raise ValueError(
                "PrimaryDirectionsNetworkNode invariant failed: total_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsNetworkEdge:
    promissor: str
    significator: str
    count: int
    nearest_arc: float

    def __post_init__(self) -> None:
        if not self.promissor or not self.significator:
            raise ValueError("PrimaryDirectionsNetworkEdge requires endpoint names")
        if self.promissor == self.significator:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: self-edge not admitted")
        if self.count <= 0:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: count must be positive")
        if self.nearest_arc <= 0.0:
            raise ValueError("PrimaryDirectionsNetworkEdge invariant failed: nearest_arc must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsNetworkProfile:
    nodes: tuple[PrimaryDirectionsNetworkNode, ...]
    edges: tuple[PrimaryDirectionsNetworkEdge, ...]
    most_connected: str
    isolated: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionsNetworkProfile requires at least one node")
        node_names = [node.name for node in self.nodes]
        if len(set(node_names)) != len(node_names):
            raise ValueError(
                "PrimaryDirectionsNetworkProfile invariant failed: duplicate node names"
            )
        node_set = set(node_names)
        for edge in self.edges:
            if edge.promissor not in node_set or edge.significator not in node_set:
                raise ValueError(
                    "PrimaryDirectionsNetworkProfile invariant failed: dangling edge"
                )
        if set(self.isolated) - node_set:
            raise ValueError(
                "PrimaryDirectionsNetworkProfile invariant failed: isolated list contains unknown node"
            )
        computed_most = max(self.nodes, key=lambda node: (node.total_count, node.name)).name
        if self.most_connected != computed_most:
            raise ValueError(
                "PrimaryDirectionsNetworkProfile invariant failed: most_connected mismatch"
            )


def _required_ha(f: float, dsa: float, nsa: float) -> float:
    if abs(f) <= 1.0:
        return f * dsa
    if f > 1.0:
        return dsa + (f - 1.0) * nsa
    return -dsa - (-f - 1.0) * nsa


def _mundane_arcs(sig: SpeculumEntry, prom: SpeculumEntry) -> tuple[float, float]:
    req_ha = _required_ha(sig.f, prom.dsa, prom.nsa)
    direct = req_ha - prom.ha
    converse = -direct
    return direct, converse


def _placidian_mundane_position(significator: SpeculumEntry, armc: float) -> float:
    """Return the Placidian mundane position on the equator for one significator."""
    if significator.upper:
        ratio = abs(significator.ha) / significator.dsa if significator.dsa > 1e-9 else 0.0
        if significator.is_eastern:
            return (armc + 90.0 * ratio) % 360.0
        return (armc - 90.0 * ratio) % 360.0

    ic_ra = (armc + 180.0) % 360.0
    lower_md = abs(abs(significator.ha) - significator.dsa)
    ratio = lower_md / significator.nsa if significator.nsa > 1e-9 else 0.0
    if significator.is_eastern:
        return (ic_ra - 90.0 * ratio) % 360.0
    return (ic_ra + 90.0 * ratio) % 360.0


def _placidian_classic_semi_arc_arcs(
    sig: SpeculumEntry,
    prom: SpeculumEntry,
    *,
    oa_asc: float,
    armc: float,
    geo_lat: float,
) -> tuple[float, float]:
    """Compute semi-arc directions via the promissor end-point on the significator's curve."""
    mp_sig = _placidian_mundane_position(sig, armc)
    phi = geo_lat * DEG2RAD
    dec = prom.dec * DEG2RAD
    offset = (oa_asc - mp_sig) * DEG2RAD
    term = math.tan(dec) * math.tan(phi) * math.cos(offset)
    term = max(-1.0, min(1.0, term))

    # The principal branch gives the current narrow semi-arc admission. Later
    # branch work may need alternate branch handling by quadrant/doctrine.
    ra_end = (math.degrees(math.asin(term)) + mp_sig) % 360.0
    direct = (prom.ra - ra_end) % 360.0
    converse = (-direct) % 360.0
    return direct, converse


def _zodiacal_longitude_arcs(sig: SpeculumEntry, prom: SpeculumEntry) -> tuple[float, float]:
    """Compute narrow zodiacal directions by pure longitude perfection."""
    direct = (sig.lon - prom.lon) % 360.0
    converse = (-direct) % 360.0
    return direct, converse


def _state_for_arcs(arcs: tuple[PrimaryArc, ...]) -> PrimaryDirectionsConditionState:
    direct_count = sum(1 for arc in arcs if arc.is_direct)
    converse_count = len(arcs) - direct_count
    if converse_count == 0:
        return PrimaryDirectionsConditionState.DIRECT_ONLY
    if direct_count == 0:
        return PrimaryDirectionsConditionState.CONVERSE_ONLY
    return PrimaryDirectionsConditionState.MIXED


def _sorted_profiles(profiles: Iterable[PrimaryDirectionsSignificatorProfile]) -> tuple[PrimaryDirectionsSignificatorProfile, ...]:
    return tuple(sorted(profiles, key=lambda profile: (profile.significator, profile.nearest_arc)))


def speculum(
    chart: Chart,
    houses: HouseCusps,
    geo_lat: float,
    obliquity: float | None = None,
    bodies: list[str] | None = None,
) -> list[SpeculumEntry]:
    obl = obliquity if obliquity is not None else chart.obliquity
    armc = houses.armc

    entries: list[SpeculumEntry] = []
    planet_names = bodies if bodies is not None else list(chart.planets.keys())
    for name in planet_names:
        if name in chart.planets:
            p = chart.planets[name]
            entries.append(SpeculumEntry.build(name, p.longitude, p.latitude, armc, obl, geo_lat))

    for name, nd in chart.nodes.items():
        entries.append(SpeculumEntry.build(name, nd.longitude, 0.0, armc, obl, geo_lat))

    for ang_name, ang_lon in [
        ("ASC", houses.asc),
        ("MC", houses.mc),
        ("DSC", houses.dsc),
        ("IC", houses.ic),
    ]:
        entries.append(SpeculumEntry.build(ang_name, ang_lon, 0.0, armc, obl, geo_lat))

    return entries


def find_primary_arcs(
    chart: Chart,
    houses: HouseCusps,
    geo_lat: float,
    max_arc: float = 90.0,
    include_converse: bool = True,
    significators: list[str] | None = None,
    promissors: list[str] | None = None,
    solar_speed: float | None = None,
    obliquity: float | None = None,
    policy: PrimaryDirectionsPolicy | None = None,
) -> list[PrimaryArc]:
    resolved_policy = (
        policy
        if policy is not None
        else PrimaryDirectionsPolicy(
            include_converse=include_converse,
            converse_doctrine=(
                PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
                if include_converse
                else PrimaryDirectionConverseDoctrine.DIRECT_ONLY
            ),
        )
    )
    obl = obliquity if obliquity is not None else chart.obliquity

    if max_arc <= 0.0:
        raise ValueError("find_primary_arcs requires max_arc > 0")

    if solar_speed is not None:
        s_rate = abs(solar_speed)
    else:
        sun = chart.planets.get(Body.SUN)
        s_rate = abs(sun.speed) if sun else _DEFAULT_SOLAR_RATE
    if s_rate <= 0.0:
        s_rate = _DEFAULT_SOLAR_RATE

    spec = speculum(chart, houses, geo_lat, obliquity=obl)
    sp_map = {e.name: e for e in spec}
    oa_asc = sp_map["ASC"].ra

    target_truths = {name: primary_direction_target_truth(name) for name in sp_map}
    all_names = list(sp_map.keys())
    sig_candidates = set(significators) if significators is not None else set(all_names)
    prom_candidates = set(promissors) if promissors is not None else set(all_names)
    sig_set = {
        name
        for name in sig_candidates
        if name in target_truths
        and target_truths[name].target_class in resolved_policy.target_policy.admitted_significator_classes
    }
    prom_set = {
        name
        for name in prom_candidates
        if name in target_truths
        and target_truths[name].target_class in resolved_policy.target_policy.admitted_promissor_classes
    }

    results: list[PrimaryArc] = []
    for sig_e in spec:
        if sig_e.name not in sig_set:
            continue
        for prom_e in spec:
            if prom_e.name not in prom_set or sig_e.name == prom_e.name:
                continue

            if resolved_policy.space is PrimaryDirectionSpace.IN_ZODIACO:
                raw_dir, raw_conv = _zodiacal_longitude_arcs(sig_e, prom_e)
            else:
                if resolved_policy.method is PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC:
                    raw_dir, raw_conv = _placidian_classic_semi_arc_arcs(
                        sig_e,
                        prom_e,
                        oa_asc=oa_asc,
                        armc=houses.armc,
                        geo_lat=geo_lat,
                    )
                else:
                    raw_dir, raw_conv = _mundane_arcs(sig_e, prom_e)
            arc_dir = raw_dir % 360.0
            arc_conv = raw_conv % 360.0

            if 0.0 < arc_dir <= max_arc:
                results.append(
                    PrimaryArc(
                        significator=sig_e.name,
                        promissor=prom_e.name,
                        arc=arc_dir,
                        direction=DIRECT,
                        method=resolved_policy.method,
                        space=resolved_policy.space,
                        motion=PrimaryDirectionMotion.DIRECT,
                        solar_rate=s_rate,
                    )
                )

            if resolved_policy.include_converse and 0.0 < arc_conv <= max_arc:
                results.append(
                    PrimaryArc(
                        significator=sig_e.name,
                        promissor=prom_e.name,
                        arc=arc_conv,
                        direction=CONVERSE,
                        method=resolved_policy.method,
                        space=resolved_policy.space,
                        motion=PrimaryDirectionMotion.CONVERSE,
                        solar_rate=s_rate,
                    )
                )

    results.sort(key=lambda arc: (arc.arc, arc.significator, arc.promissor, arc.direction))
    return results


def relate_primary_arc(
    arc: PrimaryArc,
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionRelation:
    resolved_policy = policy if policy is not None else PrimaryDirectionsPolicy()
    return PrimaryDirectionRelation(
        arc=arc,
        relation_kind=resolved_policy.perfection_policy.kind,
        converse_doctrine=resolved_policy.converse_doctrine,
        key_policy=resolved_policy.key_policy,
    )


def evaluate_primary_direction_relations(
    arc: PrimaryArc,
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionRelationProfile:
    relation = relate_primary_arc(arc, policy=policy)
    admitted = (relation,)
    scored = admitted
    return PrimaryDirectionRelationProfile(
        arc=arc,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=scored,
    )


def evaluate_primary_direction_condition(
    arcs: Iterable[PrimaryArc],
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionsSignificatorProfile:
    arc_tuple = tuple(sorted(arcs, key=lambda arc: (arc.arc, arc.promissor, arc.direction)))
    if not arc_tuple:
        raise ValueError("evaluate_primary_direction_condition requires at least one arc")
    significator = arc_tuple[0].significator
    if any(arc.significator != significator for arc in arc_tuple):
        raise ValueError(
            "evaluate_primary_direction_condition requires all arcs to share one significator"
        )
    relation_profiles = tuple(
        evaluate_primary_direction_relations(arc, policy=policy) for arc in arc_tuple
    )
    direct_count = sum(1 for arc in arc_tuple if arc.is_direct)
    converse_count = len(arc_tuple) - direct_count
    return PrimaryDirectionsSignificatorProfile(
        significator=significator,
        arcs=arc_tuple,
        relation_profiles=relation_profiles,
        state=_state_for_arcs(arc_tuple),
        direct_count=direct_count,
        converse_count=converse_count,
        nearest_arc=arc_tuple[0].arc,
        farthest_arc=arc_tuple[-1].arc,
    )


def evaluate_primary_directions_aggregate(
    arcs: Iterable[PrimaryArc],
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionsAggregateProfile:
    grouped: dict[str, list[PrimaryArc]] = {}
    for arc in arcs:
        grouped.setdefault(arc.significator, []).append(arc)
    if not grouped:
        raise ValueError("evaluate_primary_directions_aggregate requires at least one arc")
    profiles = _sorted_profiles(
        evaluate_primary_direction_condition(group, policy=policy)
        for group in grouped.values()
    )
    strength_map = {profile.significator: len(profile.arcs) for profile in profiles}
    strongest = max(strength_map.items(), key=lambda item: (item[1], item[0]))[0]
    weakest = min(strength_map.items(), key=lambda item: (item[1], item[0]))[0]
    return PrimaryDirectionsAggregateProfile(
        profiles=profiles,
        total_arcs=sum(len(profile.arcs) for profile in profiles),
        direct_count=sum(profile.direct_count for profile in profiles),
        converse_count=sum(profile.converse_count for profile in profiles),
        nearest_arc=min(profile.nearest_arc for profile in profiles),
        farthest_arc=max(profile.farthest_arc for profile in profiles),
        strongest_significator=strongest,
        weakest_significator=weakest,
    )


def evaluate_primary_directions_network(
    arcs: Iterable[PrimaryArc],
    policy: PrimaryDirectionsPolicy | None = None,
) -> PrimaryDirectionsNetworkProfile:
    arc_tuple = tuple(arcs)
    if not arc_tuple:
        raise ValueError("evaluate_primary_directions_network requires at least one arc")

    node_names: set[str] = set()
    edge_map: dict[tuple[str, str], list[PrimaryArc]] = {}
    incoming: dict[str, int] = {}
    outgoing: dict[str, int] = {}
    for arc in arc_tuple:
        node_names.add(arc.significator)
        node_names.add(arc.promissor)
        edge_map.setdefault((arc.promissor, arc.significator), []).append(arc)
        outgoing[arc.promissor] = outgoing.get(arc.promissor, 0) + 1
        incoming[arc.significator] = incoming.get(arc.significator, 0) + 1

    nodes = tuple(
        sorted(
            (
                PrimaryDirectionsNetworkNode(
                    name=name,
                    incoming_count=incoming.get(name, 0),
                    outgoing_count=outgoing.get(name, 0),
                    total_count=incoming.get(name, 0) + outgoing.get(name, 0),
                )
                for name in node_names
            ),
            key=lambda node: node.name,
        )
    )
    edges = tuple(
        sorted(
            (
                PrimaryDirectionsNetworkEdge(
                    promissor=promissor,
                    significator=significator,
                    count=len(group),
                    nearest_arc=min(arc.arc for arc in group),
                )
                for (promissor, significator), group in edge_map.items()
            ),
            key=lambda edge: (edge.nearest_arc, edge.promissor, edge.significator),
        )
    )
    most_connected = max(nodes, key=lambda node: (node.total_count, node.name)).name
    isolated = tuple(sorted(node.name for node in nodes if node.total_count == 0))
    return PrimaryDirectionsNetworkProfile(
        nodes=nodes,
        edges=edges,
        most_connected=most_connected,
        isolated=isolated,
    )

"""Exact transit forecasting against composite and Davison chart geometry.

This module is a composition layer.  It does not own relationship-chart
construction, aspect geometry, or transit solving.  Composite and Davison
identity comes from :mod:`moira.synastry`, aspect definitions come from
:mod:`moira.constants`, and every exact perfection is delegated to
:func:`moira.transits.find_transits` as a crossing of a static, derived-chart
longitude offset.

Progressing or directing a relationship chart is deliberately outside this
contract.  Those techniques require a source-owned policy for how a synthetic
composite is advanced.  The bounded surface here answers only the reproducible
question: when does a moving body perfect a requested aspect to this exact
composite or Davison target?
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from ._strenum import StrEnum
from .constants import ASPECT_TIERS, AspectDefinition
from .spk_reader import SpkReader
from .synastry import (
    CompositeChart,
    CompositeComputationTruth,
    DavisonChart,
    DavisonComputationTruth,
)
from .transits import (
    TransitComputationPolicy,
    TransitEvent,
    TransitTargetKind,
    find_transits,
)

__all__ = [
    "RelationshipChartKind",
    "RelationshipTargetKind",
    "RelationshipChartIdentity",
    "RelationshipTransitTarget",
    "RelationshipChartTargetSet",
    "RelationshipTransitEvent",
    "RelationshipTransitSearchTruth",
    "RelationshipTransitSearchResult",
    "relationship_chart_targets",
    "find_relationship_transits",
    "find_composite_transits",
    "find_davison_transits",
]


_FRAME = "apparent_geocentric_true_ecliptic_of_date"
_TIMESCALE = "UT1_input_with_internal_TT_ephemeris"
_EVENT_SOURCE = "moira.transits.find_transits:numeric_longitude_offset"


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


class RelationshipChartKind(StrEnum):
    """Relationship-chart families admitted as static transit targets."""

    COMPOSITE = "composite"
    DAVISON = "davison"


class RelationshipTargetKind(StrEnum):
    """Kinds of ecliptic points exposed from one relationship chart."""

    PLANET = "planet"
    NODE = "node"
    ANGLE = "angle"
    HOUSE_CUSP = "house_cusp"


@dataclass(frozen=True, slots=True)
class RelationshipChartIdentity:
    """Reproducible identity and provenance for derived-chart geometry."""

    chart_id: str
    chart_kind: RelationshipChartKind
    method: str
    epoch_jd_ut: float
    includes_house_frame: bool
    relation_basis: str
    geometry_sha256: str
    construction_truth: CompositeComputationTruth | DavisonComputationTruth
    reference_latitude: float | None = None
    reference_longitude: float | None = None
    correction_mode: str | None = None
    reference_frame: str = _FRAME
    timescale: str = _TIMESCALE

    def __post_init__(self) -> None:
        object.__setattr__(self, "chart_kind", RelationshipChartKind(self.chart_kind))
        if not self.method:
            raise ValueError("relationship chart identity method must not be empty")
        if not math.isfinite(self.epoch_jd_ut):
            raise ValueError("relationship chart identity epoch_jd_ut must be finite")
        if not isinstance(self.includes_house_frame, bool):
            raise ValueError("relationship chart identity includes_house_frame must be bool")
        if not self.relation_basis:
            raise ValueError("relationship chart identity relation_basis must not be empty")
        if self.chart_kind is RelationshipChartKind.COMPOSITE:
            if not isinstance(self.construction_truth, CompositeComputationTruth):
                raise TypeError("composite identity requires CompositeComputationTruth")
            expected_epoch = self.construction_truth.jd_mean
        else:
            if not isinstance(self.construction_truth, DavisonComputationTruth):
                raise TypeError("Davison identity requires DavisonComputationTruth")
            expected_epoch = self.construction_truth.used_jd
        if self.method != self.construction_truth.method:
            raise ValueError("relationship identity method must match construction truth")
        if self.epoch_jd_ut != expected_epoch:
            raise ValueError("relationship identity epoch must match construction truth")
        if len(self.geometry_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.geometry_sha256
        ):
            raise ValueError("relationship chart geometry_sha256 must be lowercase SHA-256 hex")
        expected_id = f"{self.chart_kind.value}:{self.geometry_sha256[:16]}"
        if self.chart_id != expected_id:
            raise ValueError("relationship chart_id must derive from chart kind and geometry digest")
        if self.reference_latitude is not None:
            if not math.isfinite(self.reference_latitude) or not -90.0 <= self.reference_latitude <= 90.0:
                raise ValueError("relationship reference_latitude must lie in [-90, 90]")
        if self.reference_longitude is not None:
            if not math.isfinite(self.reference_longitude) or not -180.0 <= self.reference_longitude <= 180.0:
                raise ValueError("relationship reference_longitude must lie in [-180, 180]")


@dataclass(frozen=True, slots=True)
class RelationshipTransitTarget:
    """One immutable ecliptic target extracted from a relationship chart."""

    chart_id: str
    name: str
    target_kind: RelationshipTargetKind
    longitude: float
    source_path: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_kind", RelationshipTargetKind(self.target_kind))
        if not self.chart_id or not self.name or not self.source_path:
            raise ValueError("relationship transit target identity fields must not be empty")
        if not math.isfinite(self.longitude):
            raise ValueError("relationship transit target longitude must be finite")
        object.__setattr__(self, "longitude", self.longitude % 360.0)


@dataclass(frozen=True, slots=True)
class RelationshipChartTargetSet:
    """One chart identity plus the explicitly selected static target points."""

    identity: RelationshipChartIdentity
    targets: tuple[RelationshipTransitTarget, ...]

    def __post_init__(self) -> None:
        if not self.targets:
            raise ValueError("relationship chart target set must contain at least one target")
        names: set[str] = set()
        for target in self.targets:
            if target.chart_id != self.identity.chart_id:
                raise ValueError("relationship target chart_id must match target-set identity")
            if target.name in names:
                raise ValueError("relationship target names must be unique")
            names.add(target.name)

    @property
    def target_count(self) -> int:
        return len(self.targets)


@dataclass(frozen=True, slots=True)
class RelationshipTransitEvent:
    """One exact aspect perfection to a static relationship-chart target."""

    chart_id: str
    target: RelationshipTransitTarget
    moving_body: str
    aspect_name: str
    aspect_symbol: str
    aspect_angle_deg: float
    directional_offset_deg: float
    transit: TransitEvent
    event_source: str = _EVENT_SOURCE
    orb_boundaries_computed: bool = False
    interpretation: str = "none_geometry_only"

    def __post_init__(self) -> None:
        if self.chart_id != self.target.chart_id:
            raise ValueError("relationship transit event chart_id must match target")
        if not self.moving_body or self.transit.body != self.moving_body:
            raise ValueError("relationship transit moving_body must match canonical transit")
        if not self.aspect_name or not self.aspect_symbol:
            raise ValueError("relationship transit aspect identity must not be empty")
        if not math.isfinite(self.aspect_angle_deg) or not 0.0 <= self.aspect_angle_deg <= 180.0:
            raise ValueError("relationship transit aspect_angle_deg must lie in [0, 180]")
        if not math.isfinite(self.directional_offset_deg):
            raise ValueError("relationship transit directional_offset_deg must be finite")
        object.__setattr__(self, "directional_offset_deg", self.directional_offset_deg % 360.0)
        allowed_offsets = _directional_offsets(self.aspect_angle_deg)
        if not any(_angular_distance(self.directional_offset_deg, value) <= 1e-12 for value in allowed_offsets):
            raise ValueError("relationship transit directional offset must match its aspect")
        expected_longitude = (self.target.longitude + self.directional_offset_deg) % 360.0
        if _angular_distance(self.transit.longitude, expected_longitude) > 1e-9:
            raise ValueError("canonical transit longitude must match target plus aspect offset")
        if self.transit.computation_truth is None:
            raise ValueError("relationship transit requires canonical transit computation truth")
        if self.transit.classification is None or self.transit.relation is None:
            raise ValueError("relationship transit requires canonical classification and relation")
        if self.transit.condition_profile is None:
            raise ValueError("relationship transit requires canonical condition profile")
        if self.transit.target_kind is not TransitTargetKind.NUMERIC_LONGITUDE:
            raise ValueError("relationship transit must use a static numeric longitude target")
        if self.orb_boundaries_computed:
            raise ValueError("relationship transit v1 does not compute orb boundaries")

    @property
    def jd_exact(self) -> float:
        return self.transit.jd_ut

    @property
    def direction(self) -> str:
        return self.transit.direction

    @property
    def perfection_longitude(self) -> float:
        return self.transit.longitude


@dataclass(frozen=True, slots=True)
class RelationshipTransitSearchTruth:
    """All caller policy and delegated authority for one bounded search."""

    chart_id: str
    moving_bodies: tuple[str, ...]
    target_names: tuple[str, ...]
    tier: int
    aspect_names: tuple[str, ...]
    jd_start: float
    jd_end: float
    step_days: float | None
    policy_step_days_override: float | None
    solver_tolerance_days: float
    step_policy: str
    transit_policy_source: str
    direction: str
    search_motion: str
    search_call_count: int
    event_count: int
    event_source: str = _EVENT_SOURCE
    target_motion: str = "static_derived_chart_geometry"
    event_kind: str = "exact_aspect_perfection"
    orb_window_policy: str = "not_computed"
    interpretation: str = "none_geometry_only"

    def __post_init__(self) -> None:
        if not self.chart_id or not self.moving_bodies or not self.target_names:
            raise ValueError("relationship transit search identity sets must not be empty")
        if len(set(self.moving_bodies)) != len(self.moving_bodies):
            raise ValueError("relationship transit moving_bodies must be unique")
        if len(set(self.target_names)) != len(self.target_names):
            raise ValueError("relationship transit target_names must be unique")
        if self.tier not in ASPECT_TIERS:
            raise ValueError("relationship transit tier must be 0, 1, or 2")
        if not self.aspect_names:
            raise ValueError("relationship transit aspect_names must not be empty")
        available_aspects = {aspect.name for aspect in ASPECT_TIERS[self.tier]}
        if len(set(self.aspect_names)) != len(self.aspect_names) or any(
            name not in available_aspects
            for name in self.aspect_names
        ):
            raise ValueError(
                "relationship transit aspect_names must be unique and admitted by tier"
            )
        if not all(math.isfinite(value) for value in (self.jd_start, self.jd_end)):
            raise ValueError("relationship transit search bounds must be finite")
        if self.jd_end <= self.jd_start:
            raise ValueError("relationship transit search range must be strictly increasing")
        if self.step_days is not None and (
            not _is_finite_number(self.step_days) or self.step_days <= 0.0
        ):
            raise ValueError("relationship transit step_days must be positive and finite")
        if self.policy_step_days_override is not None and (
            not _is_finite_number(self.policy_step_days_override)
            or self.policy_step_days_override <= 0.0
        ):
            raise ValueError(
                "relationship transit policy step override must be positive and finite"
            )
        if (
            not _is_finite_number(self.solver_tolerance_days)
            or self.solver_tolerance_days <= 0.0
        ):
            raise ValueError(
                "relationship transit solver tolerance must be positive and finite"
            )
        expected_step_policy = (
            "explicit_argument"
            if self.step_days is not None
            else (
                "transit_policy_override"
                if self.policy_step_days_override is not None
                else "canonical_per_body_auto"
            )
        )
        if self.step_policy != expected_step_policy:
            raise ValueError("relationship transit step policy is inconsistent")
        if self.transit_policy_source not in {"default", "caller_supplied"}:
            raise ValueError("relationship transit policy source is invalid")
        if self.direction not in {"direct", "retrograde", "either"}:
            raise ValueError("relationship transit direction must be direct, retrograde, or either")
        if self.search_motion not in {"forward", "backward"}:
            raise ValueError("relationship transit search_motion must be forward or backward")
        if self.search_call_count <= 0 or self.event_count < 0:
            raise ValueError("relationship transit search counts are inconsistent")


@dataclass(frozen=True, slots=True)
class RelationshipTransitSearchResult:
    """Complete exact-event search with targets, events, and provenance."""

    target_set: RelationshipChartTargetSet
    events: tuple[RelationshipTransitEvent, ...]
    computation_truth: RelationshipTransitSearchTruth

    def __post_init__(self) -> None:
        if self.target_set.identity.chart_id != self.computation_truth.chart_id:
            raise ValueError("relationship search truth chart_id must match target set")
        if self.computation_truth.target_names != tuple(
            target.name for target in self.target_set.targets
        ):
            raise ValueError("relationship search truth target_names must match target set")
        if self.computation_truth.event_count != len(self.events):
            raise ValueError("relationship search event_count must match events")
        aspect_by_name = {
            aspect.name: aspect
            for aspect in ASPECT_TIERS[self.computation_truth.tier]
            if aspect.name in self.computation_truth.aspect_names
        }
        expected_search_calls = (
            len(self.computation_truth.moving_bodies)
            * len(self.target_set.targets)
            * sum(
                len(_directional_offsets(aspect.angle))
                for aspect in aspect_by_name.values()
            )
        )
        if self.computation_truth.search_call_count != expected_search_calls:
            raise ValueError(
                "relationship search call count must match bodies, targets, and aspects"
            )
        targets_by_name = {
            target.name: target
            for target in self.target_set.targets
        }
        for event in self.events:
            if event.chart_id != self.target_set.identity.chart_id:
                raise ValueError("relationship search event chart_id must match target set")
            if event.moving_body not in self.computation_truth.moving_bodies:
                raise ValueError("relationship search event body must match search truth")
            if targets_by_name.get(event.target.name) != event.target:
                raise ValueError("relationship search event target must match target set")
            if event.aspect_name not in self.computation_truth.aspect_names:
                raise ValueError("relationship search event aspect must match search truth")
            if (
                self.computation_truth.direction != "either"
                and event.direction != self.computation_truth.direction
            ):
                raise ValueError("relationship search event direction must match search truth")
            if not (
                self.computation_truth.jd_start
                <= event.jd_exact
                <= self.computation_truth.jd_end
            ):
                raise ValueError("relationship search event epoch must lie within search bounds")
        expected = tuple(
            sorted(
                self.events,
                key=_event_sort_key,
                reverse=self.computation_truth.search_motion == "backward",
            )
        )
        if self.events != expected:
            raise ValueError("relationship transit events must follow search-motion order")

    @property
    def event_count(self) -> int:
        return len(self.events)


def _angular_distance(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


def _float_token(value: float | None) -> str | None:
    return None if value is None else float(value).hex()


def _geometry_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _construction_payload(
    truth: CompositeComputationTruth | DavisonComputationTruth,
) -> dict[str, object]:
    return {
        name: _float_token(value) if isinstance(value, float) else value
        for name, value in asdict(truth).items()
    }


def _ordered_geometry(
    planets: dict[str, float],
    nodes: dict[str, float],
    angles: dict[str, float],
    cusps: tuple[float, ...],
) -> dict[str, object]:
    return {
        "planets": [[name, _float_token(value % 360.0)] for name, value in sorted(planets.items())],
        "nodes": [[name, _float_token(value % 360.0)] for name, value in sorted(nodes.items())],
        "angles": [[name, _float_token(value % 360.0)] for name, value in sorted(angles.items())],
        "cusps": [_float_token(value % 360.0) for value in cusps],
    }


def _chart_geometry(chart: CompositeChart | DavisonChart) -> tuple[
    RelationshipChartIdentity,
    dict[str, float],
    dict[str, float],
    dict[str, float],
    tuple[float, ...],
]:
    if isinstance(chart, CompositeChart):
        truth = chart.computation_truth
        classification = chart.classification
        relation = chart.relation
        if truth is None or classification is None or relation is None:
            raise ValueError("composite transit targets require authoritative chart provenance")
        planets = {name: float(value) for name, value in chart.planets.items()}
        nodes = {name: float(value) for name, value in chart.nodes.items()}
        angles = {}
        if chart.asc is not None:
            angles["Ascendant"] = chart.asc
        if chart.mc is not None:
            angles["Midheaven"] = chart.mc
        cusps = tuple(float(value) for value in chart.cusps)
        kind = RelationshipChartKind.COMPOSITE
        method = truth.method
        epoch = chart.jd_mean
        includes_house_frame = truth.includes_house_frame
        relation_basis = relation.basis
        reference_latitude = truth.reference_latitude
        reference_longitude = None
        correction_mode = None
    elif isinstance(chart, DavisonChart):
        truth = chart.info.computation_truth
        classification = chart.info.classification
        relation = chart.info.relation
        if truth is None or classification is None or relation is None:
            raise ValueError("Davison transit targets require authoritative chart provenance")
        planets = {
            name: float(position.longitude)
            for name, position in chart.chart.planets.items()
        }
        nodes = {
            name: float(position.longitude)
            for name, position in chart.chart.nodes.items()
        }
        angles = {}
        cusps = ()
        if chart.houses is not None:
            angles = {
                "Ascendant": float(chart.houses.asc),
                "Midheaven": float(chart.houses.mc),
            }
            cusps = tuple(float(value) for value in chart.houses.cusps)
        kind = RelationshipChartKind.DAVISON
        method = truth.method
        epoch = chart.info.jd_midpoint
        includes_house_frame = chart.houses is not None
        relation_basis = relation.basis
        reference_latitude = chart.info.latitude_midpoint
        reference_longitude = chart.info.longitude_midpoint
        correction_mode = classification.correction_mode
    else:
        raise TypeError("relationship transit chart must be CompositeChart or DavisonChart")

    digest_payload = {
        "chart_kind": kind.value,
        "method": method,
        "epoch_jd_ut": _float_token(epoch),
        "includes_house_frame": includes_house_frame,
        "relation_basis": relation_basis,
        "reference_latitude": _float_token(reference_latitude),
        "reference_longitude": _float_token(reference_longitude),
        "correction_mode": correction_mode,
        "construction_truth": _construction_payload(truth),
        "geometry": _ordered_geometry(planets, nodes, angles, cusps),
    }
    digest = _geometry_digest(digest_payload)
    identity = RelationshipChartIdentity(
        chart_id=f"{kind.value}:{digest[:16]}",
        chart_kind=kind,
        method=method,
        epoch_jd_ut=epoch,
        includes_house_frame=includes_house_frame,
        relation_basis=relation_basis,
        geometry_sha256=digest,
        construction_truth=truth,
        reference_latitude=reference_latitude,
        reference_longitude=reference_longitude,
        correction_mode=correction_mode,
    )
    return identity, planets, nodes, angles, cusps


def relationship_chart_targets(
    chart: CompositeChart | DavisonChart,
    *,
    include_nodes: bool = True,
    include_angles: bool = False,
    include_cusps: bool = False,
    target_names: Sequence[str] | None = None,
) -> RelationshipChartTargetSet:
    """Extract a deterministic static target set from one relationship chart."""

    if not all(isinstance(value, bool) for value in (include_nodes, include_angles, include_cusps)):
        raise ValueError("relationship target inclusion flags must be boolean")
    identity, planets, nodes, angles, cusps = _chart_geometry(chart)
    targets: list[RelationshipTransitTarget] = []
    for name, longitude in sorted(planets.items()):
        targets.append(
            RelationshipTransitTarget(
                chart_id=identity.chart_id,
                name=name,
                target_kind=RelationshipTargetKind.PLANET,
                longitude=longitude,
                source_path=f"planets.{name}",
            )
        )
    if include_nodes:
        for name, longitude in sorted(nodes.items()):
            targets.append(
                RelationshipTransitTarget(
                    chart_id=identity.chart_id,
                    name=name,
                    target_kind=RelationshipTargetKind.NODE,
                    longitude=longitude,
                    source_path=f"nodes.{name}",
                )
            )
    if include_angles:
        for name in ("Ascendant", "Midheaven"):
            if name in angles:
                targets.append(
                    RelationshipTransitTarget(
                        chart_id=identity.chart_id,
                        name=name,
                        target_kind=RelationshipTargetKind.ANGLE,
                        longitude=angles[name],
                        source_path=f"angles.{name}",
                    )
                )
    if include_cusps:
        for index, longitude in enumerate(cusps, start=1):
            name = f"House {index} Cusp"
            targets.append(
                RelationshipTransitTarget(
                    chart_id=identity.chart_id,
                    name=name,
                    target_kind=RelationshipTargetKind.HOUSE_CUSP,
                    longitude=longitude,
                    source_path=f"cusps.house_{index}",
                )
            )

    if target_names is not None:
        if isinstance(target_names, (str, bytes)):
            raise ValueError("relationship target_names must be a sequence of names")
        requested = tuple(target_names)
        if not requested or any(not isinstance(name, str) or not name.strip() for name in requested):
            raise ValueError("relationship target_names must contain non-empty strings")
        if len(set(requested)) != len(requested):
            raise ValueError("relationship target_names must be unique")
        by_name = {target.name: target for target in targets}
        missing = [name for name in requested if name not in by_name]
        if missing:
            raise ValueError(f"relationship target_names are unavailable: {', '.join(missing)}")
        targets = [by_name[name] for name in requested]

    return RelationshipChartTargetSet(identity=identity, targets=tuple(targets))


def _directional_offsets(angle: float) -> tuple[float, ...]:
    normalized = angle % 360.0
    if _angular_distance(normalized, 0.0) <= 1e-12:
        return (0.0,)
    if _angular_distance(normalized, 180.0) <= 1e-12:
        return (180.0,)
    return (normalized, (360.0 - normalized) % 360.0)


def _event_sort_key(event: RelationshipTransitEvent) -> tuple[float, str, str, float, str]:
    return (
        event.jd_exact,
        event.moving_body,
        event.target.name,
        event.directional_offset_deg,
        event.aspect_name,
    )


def _selected_aspects(
    tier: int,
    aspect_names: Sequence[str] | None = None,
) -> tuple[AspectDefinition, ...]:
    if isinstance(tier, bool) or tier not in ASPECT_TIERS:
        raise ValueError("relationship transit tier must be 0, 1, or 2")
    aspects = tuple(ASPECT_TIERS[tier])
    if aspect_names is None:
        return aspects
    if isinstance(aspect_names, (str, bytes)):
        raise ValueError("relationship aspect_names must be a sequence of names")
    requested = tuple(aspect_names)
    if not requested or any(
        not isinstance(name, str) or not name.strip()
        for name in requested
    ):
        raise ValueError("relationship aspect_names must contain non-empty strings")
    if len(set(requested)) != len(requested):
        raise ValueError("relationship aspect_names must be unique")
    by_name = {aspect.name: aspect for aspect in aspects}
    missing = [name for name in requested if name not in by_name]
    if missing:
        raise ValueError(
            f"relationship aspect_names are unavailable at tier {tier}: "
            f"{', '.join(missing)}"
        )
    return tuple(by_name[name] for name in requested)


def find_relationship_transits(
    chart: CompositeChart | DavisonChart,
    moving_bodies: Sequence[str],
    jd_start: float,
    jd_end: float,
    *,
    tier: int = 0,
    aspect_names: Sequence[str] | None = None,
    include_nodes: bool = True,
    include_angles: bool = False,
    include_cusps: bool = False,
    target_names: Sequence[str] | None = None,
    direction: str = "either",
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
    search_motion: str = "forward",
) -> RelationshipTransitSearchResult:
    """Find exact transiting aspects to selected composite or Davison points.

    Symmetric aspects are searched in both directional branches.  For example,
    a square to a 10-degree target searches crossings of both 100 and 280
    degrees.  Orb entry/exit windows are intentionally not computed.
    """

    if isinstance(moving_bodies, (str, bytes)):
        raise ValueError("relationship transit moving_bodies must be a sequence")
    bodies = tuple(moving_bodies)
    if not bodies or any(not isinstance(body, str) or not body.strip() for body in bodies):
        raise ValueError("relationship transit moving_bodies must contain non-empty strings")
    if len(set(bodies)) != len(bodies):
        raise ValueError("relationship transit moving_bodies must be unique")
    if not all(_is_finite_number(value) for value in (jd_start, jd_end)) or jd_end <= jd_start:
        raise ValueError("relationship transit range must be finite and strictly increasing")
    if step_days is not None and (
        not _is_finite_number(step_days) or step_days <= 0.0
    ):
        raise ValueError("relationship transit step_days must be positive and finite")
    if direction not in {"direct", "retrograde", "either"}:
        raise ValueError("relationship transit direction must be direct, retrograde, or either")
    if search_motion not in {"forward", "backward"}:
        raise ValueError("relationship transit search_motion must be forward or backward")

    aspects = _selected_aspects(tier, aspect_names)
    resolved_policy = policy or TransitComputationPolicy()
    target_set = relationship_chart_targets(
        chart,
        include_nodes=include_nodes,
        include_angles=include_angles,
        include_cusps=include_cusps,
        target_names=target_names,
    )
    events: list[RelationshipTransitEvent] = []
    search_call_count = 0
    for moving_body in bodies:
        for target in target_set.targets:
            for aspect in aspects:
                for offset in _directional_offsets(aspect.angle):
                    search_call_count += 1
                    perfection_longitude = (target.longitude + offset) % 360.0
                    canonical_events = find_transits(
                        moving_body,
                        perfection_longitude,
                        jd_start,
                        jd_end,
                        step_days=step_days,
                        reader=reader,
                        policy=policy,
                        search_motion=search_motion,
                    )
                    for canonical_event in canonical_events:
                        if direction != "either" and canonical_event.direction != direction:
                            continue
                        events.append(
                            RelationshipTransitEvent(
                                chart_id=target_set.identity.chart_id,
                                target=target,
                                moving_body=moving_body,
                                aspect_name=aspect.name,
                                aspect_symbol=aspect.symbol,
                                aspect_angle_deg=aspect.angle,
                                directional_offset_deg=offset,
                                transit=canonical_event,
                            )
                        )

    events.sort(key=_event_sort_key, reverse=search_motion == "backward")
    truth = RelationshipTransitSearchTruth(
        chart_id=target_set.identity.chart_id,
        moving_bodies=bodies,
        target_names=tuple(target.name for target in target_set.targets),
        tier=tier,
        aspect_names=tuple(aspect.name for aspect in aspects),
        jd_start=jd_start,
        jd_end=jd_end,
        step_days=step_days,
        policy_step_days_override=resolved_policy.transit.step_days_override,
        solver_tolerance_days=resolved_policy.transit.solver_tolerance_days,
        step_policy=(
            "explicit_argument"
            if step_days is not None
            else (
                "transit_policy_override"
                if resolved_policy.transit.step_days_override is not None
                else "canonical_per_body_auto"
            )
        ),
        transit_policy_source=("caller_supplied" if policy is not None else "default"),
        direction=direction,
        search_motion=search_motion,
        search_call_count=search_call_count,
        event_count=len(events),
    )
    return RelationshipTransitSearchResult(
        target_set=target_set,
        events=tuple(events),
        computation_truth=truth,
    )


def find_composite_transits(
    chart: CompositeChart,
    moving_bodies: Sequence[str],
    jd_start: float,
    jd_end: float,
    **kwargs: object,
) -> RelationshipTransitSearchResult:
    """Typed convenience wrapper for :func:`find_relationship_transits`."""

    if not isinstance(chart, CompositeChart):
        raise TypeError("find_composite_transits requires a CompositeChart")
    return find_relationship_transits(chart, moving_bodies, jd_start, jd_end, **kwargs)


def find_davison_transits(
    chart: DavisonChart,
    moving_bodies: Sequence[str],
    jd_start: float,
    jd_end: float,
    **kwargs: object,
) -> RelationshipTransitSearchResult:
    """Typed convenience wrapper for :func:`find_relationship_transits`."""

    if not isinstance(chart, DavisonChart):
        raise TypeError("find_davison_transits requires a DavisonChart")
    return find_relationship_transits(chart, moving_bodies, jd_start, jd_end, **kwargs)

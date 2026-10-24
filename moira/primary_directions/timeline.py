"""
Moira -- primary_directions/timeline.py
Chronological Life Timeline Engine for Primary Directions.

Boundary
--------
Owns the chronological projection of primary direction arcs, distributor periods,
and participating aspects into an integrated chronological life timeline.
Combines geometric arcs with dynamic or static time-key conversions to yield
perfection ages, calendar timestamps, and traditional distributor/participator
governance throughout human lifespan.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from numbers import Real
from typing import Iterable

from ..julian import safe_datetime_from_jd, _ut1_to_utc
from ..constants import Body
from ._chart_time import _chart_ut1
from .derived_points import _resolve_primary_direction_derived_points
from ..egyptian_bounds import EgyptianBoundsDoctrine
from .keys import (
    PrimaryDirectionKey,
    PrimaryDirectionKeyPolicy,
    project_primary_direction_arc_time,
    _arc_for_age,
)
from .methods import PrimaryDirectionMethod
from .spaces import PrimaryDirectionSpace
from .converse import PrimaryDirectionMotion, PrimaryDirectionConverseDoctrine
from .relations import PrimaryDirectionRelationalKind
from .targets import resolve_primary_direction_bound_targets, primary_direction_target_truth
from .distributor import (
    DistributorPeriod,
    resolve_distributor_chronology,
)

__all__ = [
    "PrimaryDirectionTimelineEvent",
    "PrimaryDirectionsTimeline",
    "compute_primary_directions_timeline",
]


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTimelineEvent:
    """
    Vessel: A single chronological directional event perfected during life.

    Attributes:
        significator: The directed significator (e.g. "Ascendant", "Sun").
        promissor: The promissor or aspectual point (e.g. "Mars", "Term of Jupiter").
        arc_deg: The directional angular arc in degrees.
        direction: Motion indicator ("D" for direct, "C" for converse).
        motion: PrimaryDirectionMotion enum value.
        method: PrimaryDirectionMethod calculation method.
        space: PrimaryDirectionSpace (in_mundo or in_zodiaco).
        relational_kind: PrimaryDirectionRelationalKind of the perfection.
        age_years: Chronological age at perfection in tropical years.
        perfection_jd_ut: Julian Date (UT) of perfection.
        perfection_iso: ISO 8601 UTC timestamp of perfection.
        distributor: Planet ruling the active term/bound at this age, if known.
        bound_name: Name of the active term/bound segment at this age, if known.
        participator: Aspectual partner planet casting a ray during this bound, if applicable.
        is_bound_boundary: True if this event marks an entry into a new term/bound.
    """
    significator: str
    promissor: str
    arc_deg: float
    direction: str
    motion: PrimaryDirectionMotion
    method: PrimaryDirectionMethod
    space: PrimaryDirectionSpace
    relational_kind: PrimaryDirectionRelationalKind
    age_years: float
    perfection_jd_ut: float
    perfection_iso: str
    distributor: str | None = None
    bound_name: str | None = None
    participator: str | None = None
    is_bound_boundary: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.significator, str) or not self.significator.strip():
            raise ValueError("PrimaryDirectionTimelineEvent requires non-empty significator")
        if not isinstance(self.promissor, str) or not self.promissor.strip():
            raise ValueError("PrimaryDirectionTimelineEvent requires non-empty promissor")
        if not isinstance(self.arc_deg, Real) or not math.isfinite(self.arc_deg) or self.arc_deg <= 0.0:
            raise ValueError("PrimaryDirectionTimelineEvent arc_deg must be positive finite real")
        if not isinstance(self.age_years, Real) or not math.isfinite(self.age_years) or self.age_years <= 0.0:
            raise ValueError("PrimaryDirectionTimelineEvent age_years must be positive finite real")
        if not isinstance(self.perfection_jd_ut, Real) or not math.isfinite(self.perfection_jd_ut):
            raise ValueError("PrimaryDirectionTimelineEvent perfection_jd_ut must be finite real")
        if not isinstance(self.perfection_iso, str) or not self.perfection_iso.strip():
            raise ValueError("PrimaryDirectionTimelineEvent requires non-empty perfection_iso")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionsTimeline:
    """
    Vessel: The complete chronological life timeline of primary directions.

    Attributes:
        chart_id: Identifier or label of the source natal chart.
        natal_jd_ut: Julian Date (UT1) of the natal origin; display dates use UTC.
        max_age_years: Upper bound age for timeline inclusion.
        key: Primary direction time-key used for arc-to-time projection.
        bound_doctrine: Bounds table used for distributor chronology.
        events: Chronologically sorted tuple of timeline events.
        distributor_periods: Chronological bound periods spanning the life.
    """
    chart_id: str
    natal_jd_ut: float
    max_age_years: float
    key: PrimaryDirectionKey
    events: tuple[PrimaryDirectionTimelineEvent, ...]
    distributor_periods: tuple[DistributorPeriod, ...]
    bound_doctrine: EgyptianBoundsDoctrine = EgyptianBoundsDoctrine.EGYPTIAN

    def __post_init__(self) -> None:
        if not isinstance(self.natal_jd_ut, Real) or not math.isfinite(self.natal_jd_ut):
            raise ValueError("PrimaryDirectionsTimeline natal_jd_ut must be finite real")
        if not isinstance(self.max_age_years, Real) or not math.isfinite(self.max_age_years) or self.max_age_years <= 0.0:
            raise ValueError("PrimaryDirectionsTimeline max_age_years must be positive finite real")
        if not isinstance(self.key, PrimaryDirectionKey):
            raise ValueError("PrimaryDirectionsTimeline key must be PrimaryDirectionKey")
        if not isinstance(self.bound_doctrine, EgyptianBoundsDoctrine):
            raise ValueError(
                "PrimaryDirectionsTimeline bound_doctrine must be EgyptianBoundsDoctrine"
            )


def _project_arc_to_time(
    arc_deg: float,
    *,
    key: PrimaryDirectionKey,
    natal_jd_ut: float,
    reader: object,
    solar_rate: float | None = None,
) -> tuple[float, float]:
    """Project one arc without silently substituting another key doctrine."""
    return project_primary_direction_arc_time(
        natal_jd_ut, arc_deg, key, solar_rate=solar_rate, reader=reader,
    )


def compute_primary_directions_timeline(
    chart: object,
    houses: object,
    geo_lat: float,
    *,
    policy: object = None,
    key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD,
    max_age_years: float = 100.0,
    max_arc: float | None = None,
    significators: Iterable[str] | None = None,
    promissors: Iterable[str] | None = None,
    obliquity: float | None = None,
    reader: object = None,
    bound_doctrine: EgyptianBoundsDoctrine = EgyptianBoundsDoctrine.EGYPTIAN,
) -> PrimaryDirectionsTimeline:
    """Compute an integrated chronological life timeline of primary directions.

    Performs primary arc calculation, bound distribution partitioning, and
    arc-to-time conversion across the requested lifespan.

    Parameters:
        chart: Natal Chart snapshot.
        houses: Natal HouseCusps snapshot.
        geo_lat: Geographic latitude of the observer.
        policy: Optional PrimaryDirectionsPolicy.
        key: PrimaryDirectionKey or str name (default: NAIBOD).
        max_age_years: Lifespan limit in tropical years (default: 100.0).
        max_arc: Search horizon arc in degrees (default: auto derived from max_age_years).
        significators: Optional iterable of significator body names.
        promissors: Optional iterable of promissor body names.
        obliquity: Optional true obliquity override.
        reader: Optional SPK reader for ephemeris inquiries.
        bound_doctrine: Bounds table doctrine (default: EGYPTIAN).

    Returns:
        PrimaryDirectionsTimeline containing chronological events and distributor periods.
    """
    if not isinstance(max_age_years, Real) or isinstance(max_age_years, bool) or not math.isfinite(max_age_years) or max_age_years <= 0.0:
        raise ValueError("max_age_years must be a positive finite real")

    from . import (
        PrimaryDirectionsPolicy,
        PrimaryDirectionsPreset,
        find_primary_arcs,
        primary_directions_policy_preset,
        _identity_tuple,
        _finite_real,
    )

    resolved_key = PrimaryDirectionKey(str(key).lower()) if not isinstance(key, PrimaryDirectionKey) else key

    sig_names = _identity_tuple(significators, "timeline significators")
    prom_names = _identity_tuple(promissors, "timeline promissors")
    chart_jd = _chart_ut1(chart)
    sun = chart.planets.get(Body.SUN)
    natal_solar_rate = (abs(_finite_real(sun.speed, "timeline natal Sun speed"))
                        if sun is not None else None)
    if max_arc is None:
        resolved_max_arc = _arc_for_age(chart_jd, float(max_age_years), resolved_key,
                                       solar_rate=natal_solar_rate, reader=reader)
    else:
        resolved_max_arc = _finite_real(max_arc, "timeline max_arc")
        if not 0. < resolved_max_arc <= 360.:
            raise ValueError("timeline max_arc must be in (0, 360]")

    # Policy setup: ensure bound targets are present if not explicitly populated
    if policy is None:
        base_policy = primary_directions_policy_preset(
            PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
            key_policy=PrimaryDirectionKeyPolicy(resolved_key),
        )
    elif isinstance(policy, PrimaryDirectionsPolicy):
        base_policy = policy
    else:
        raise ValueError("policy must be PrimaryDirectionsPolicy or None")

    from .relations import PrimaryDirectionRelationPolicy, PrimaryDirectionRelationalKind

    generated_bounds = resolve_primary_direction_bound_targets(doctrine=bound_doctrine)
    if base_policy.bound_targets and set(base_policy.bound_targets) != set(generated_bounds):
        raise ValueError("timeline bound targets must be the complete canonical table for bound_doctrine")
    if base_policy.converse_doctrine is PrimaryDirectionConverseDoctrine.SIGNED_PRIMARY_MOTION:
        raise ValueError("timeline bound chronology does not admit the signed-primary-motion preset")
    admitted = set(base_policy.relation_policy.admitted_kinds) | {PrimaryDirectionRelationalKind.TERM_BOUND}
    effective_policy = replace(
        base_policy, bound_targets=generated_bounds,
        relation_policy=PrimaryDirectionRelationPolicy(frozenset(admitted)),
    )

    # Search directional arcs
    raw_arcs = find_primary_arcs(
        chart=chart,
        houses=houses,
        geo_lat=geo_lat,
        max_arc=resolved_max_arc,
        include_converse=effective_policy.include_converse,
        significators=sig_names,
        promissors=prom_names,
        obliquity=obliquity,
        policy=effective_policy,
    )

    # Natal longitude lookup needs no rise/set projection of unrelated bodies.
    natal_longitudes = {name: point.longitude for name, point in chart.planets.items()}
    natal_longitudes.update({name: point.longitude for name, point in chart.nodes.items()})
    natal_longitudes.update({"ASC": houses.asc, "MC": houses.mc, "DSC": houses.dsc, "IC": houses.ic})
    active_points = (target for target in effective_policy.derived_point_targets
                     if primary_direction_target_truth(target.name).target_class
                     in effective_policy.target_policy.admitted_significator_classes
                     and (sig_names is None or target.name in sig_names))
    natal_longitudes.update({name: longitude for name, longitude, _ in
                            _resolve_primary_direction_derived_points(active_points, chart, houses).values()})
    if sig_names is not None:
        sig_order = sig_names
        for name in sig_order:
            if name.startswith("H") and name[1:].isdigit() and 1 <= int(name[1:]) <= 12:
                natal_longitudes[name] = houses.cusps[int(name[1:]) - 1]
    else:
        available = []
        for name in natal_longitudes:
            try:
                truth = primary_direction_target_truth(name)
            except ValueError:
                continue
            if truth.target_class in effective_policy.target_policy.admitted_significator_classes:
                available.append(name)
        sig_order = tuple(sorted(available))

    if effective_policy.placidian_rapt_parallel_motion is not None:
        # Rapt motion is relation-specific; the ambient converse boolean is
        # deliberately false. Use the already admitted ordinary bound law in
        # the matching motion, retaining direct context for configured stars.
        admitted_distributor_motions = [effective_policy.placidian_rapt_parallel_motion]
        if effective_policy.fixed_star_targets and PrimaryDirectionMotion.DIRECT not in admitted_distributor_motions:
            admitted_distributor_motions.insert(0, PrimaryDirectionMotion.DIRECT)
    else:
        admitted_distributor_motions = list(effective_policy.admitted_motions)
    has_converse = PrimaryDirectionMotion.CONVERSE in admitted_distributor_motions
    bound_policy = PrimaryDirectionsPolicy(
        method=effective_policy.method, space=effective_policy.space,
        latitude_policy=effective_policy.latitude_policy,
        latitude_source_policy=effective_policy.latitude_source_policy,
        perfection_policy=effective_policy.perfection_policy,
        target_policy=effective_policy.target_policy,
        key_policy=effective_policy.key_policy,
        include_converse=has_converse,
        converse_doctrine=(effective_policy.converse_doctrine if has_converse
                          else PrimaryDirectionConverseDoctrine.DIRECT_ONLY),
        bound_targets=generated_bounds,
        derived_point_targets=effective_policy.derived_point_targets,
        relation_policy=PrimaryDirectionRelationPolicy(frozenset({PrimaryDirectionRelationalKind.TERM_BOUND})),
    )
    # Structural crossings are independent of event filters and target-family
    # gates. Empty requested significators produce an empty timeline.
    bound_arcs = find_primary_arcs(
        chart, houses, geo_lat, policy=bound_policy, max_arc=resolved_max_arc,
        significators=sig_order, promissors=tuple(b.name for b in generated_bounds),
        obliquity=obliquity,
    ) if sig_order else []
    bound_arcs = [a for a in bound_arcs if a.motion in admitted_distributor_motions]
    aspect_arcs = [a for a in raw_arcs if a.relational_kind is not PrimaryDirectionRelationalKind.TERM_BOUND]
    raw_arcs = aspect_arcs + [a for a in bound_arcs if prom_names is None or a.promissor in prom_names]

    distributor_periods_by_sig_motion: dict[tuple[str, PrimaryDirectionMotion], list[DistributorPeriod]] = {}
    for sig in sig_order:
        natal_lon = natal_longitudes.get(sig)

        if natal_lon is not None:
            for mot in admitted_distributor_motions:
                periods = resolve_distributor_chronology(
                    significator=sig,
                    natal_longitude=natal_lon,
                    bound_arcs=bound_arcs,
                    participating_arcs=aspect_arcs,
                    doctrine=bound_doctrine,
                    motion=mot,
                    max_arc=resolved_max_arc,
                )
                enriched_periods: list[DistributorPeriod] = []
                for p in periods:
                    if p.entry_arc_deg <= 0.0:
                        ent_age = 0.0
                        ent_jd = chart_jd
                    else:
                        ent_age, ent_jd = _project_arc_to_time(
                            p.entry_arc_deg,
                            key=resolved_key,
                            natal_jd_ut=chart_jd,
                            reader=reader,
                            solar_rate=natal_solar_rate,
                        )

                    ext_age, ext_jd = _project_arc_to_time(
                        p.exit_arc_deg,
                        key=resolved_key,
                        natal_jd_ut=chart_jd,
                        reader=reader,
                        solar_rate=natal_solar_rate,
                    )

                    ent_iso = safe_datetime_from_jd(_ut1_to_utc(ent_jd)).isoformat()
                    ext_iso = safe_datetime_from_jd(_ut1_to_utc(ext_jd)).isoformat()

                    enriched_periods.append(
                        replace(
                            p,
                            entry_age=ent_age,
                            exit_age=ext_age,
                            entry_date_utc=ent_iso,
                            exit_date_utc=ext_iso,
                        )
                    )
                distributor_periods_by_sig_motion[(sig, mot)] = enriched_periods

    # Assemble timeline events
    events: list[PrimaryDirectionTimelineEvent] = []
    for arc in raw_arcs:
        age, perf_jd = _project_arc_to_time(
            arc.arc,
            key=resolved_key,
            natal_jd_ut=chart_jd,
            reader=reader,
            solar_rate=arc.solar_rate,
        )

        if not (0.0 < age <= max_age_years):
            continue

        perf_iso = safe_datetime_from_jd(_ut1_to_utc(perf_jd)).isoformat()

        # Check distributor and bound context
        is_bound_boundary = arc.relational_kind is PrimaryDirectionRelationalKind.TERM_BOUND
        distributor = None
        bound_name = None
        participator = None

        sig_periods = distributor_periods_by_sig_motion.get((arc.significator, arc.motion))
        if sig_periods:
            covering_period = None
            for idx, p in enumerate(sig_periods):
                is_last = idx == len(sig_periods) - 1
                if is_last:
                    matches = p.entry_arc_deg <= arc.arc <= p.exit_arc_deg
                else:
                    matches = p.entry_arc_deg <= arc.arc < p.exit_arc_deg
                if matches:
                    covering_period = p
                    break
            if covering_period is not None:
                distributor = covering_period.ruler
                bound_name = f"{covering_period.sign} {covering_period.bound_start_deg:.0f}°-{covering_period.bound_end_deg:.0f}° ({covering_period.ruler})"

        if is_bound_boundary and distributor is None:
            from .distributor import _parse_bound_promissor
            parsed = _parse_bound_promissor(arc.promissor)
            if parsed is not None:
                ruler, sign, deg = parsed
                distributor = ruler
                if bound_name is None:
                    bound_name = f"{sign} {deg:.0f}° ({ruler})"

        if not is_bound_boundary:
            participator = arc.promissor

        events.append(
            PrimaryDirectionTimelineEvent(
                significator=arc.significator,
                promissor=arc.promissor,
                arc_deg=arc.arc,
                direction=arc.direction,
                motion=arc.motion,
                method=arc.method,
                space=arc.space,
                relational_kind=arc.relational_kind,
                age_years=age,
                perfection_jd_ut=perf_jd,
                perfection_iso=perf_iso,
                distributor=distributor,
                bound_name=bound_name,
                participator=participator,
                is_bound_boundary=is_bound_boundary,
            )
        )

    # Sort strictly chronologically
    events.sort(key=lambda ev: (ev.age_years, ev.arc_deg, ev.significator, ev.promissor))

    # Aggregate distributor periods across all resolved significators
    all_distributor_periods: list[DistributorPeriod] = []
    for sig_periods in distributor_periods_by_sig_motion.values():
        all_distributor_periods.extend(sig_periods)
    all_distributor_periods.sort(
        key=lambda period: (
            period.entry_age if period.entry_age is not None else math.inf,
            period.significator,
            period.motion.value,
            period.entry_arc_deg,
            period.exit_arc_deg,
            period.ruler,
        )
    )

    chart_identifier = getattr(chart, "id", "") or getattr(chart, "name", "") or "natal"

    return PrimaryDirectionsTimeline(
        chart_id=chart_identifier,
        natal_jd_ut=chart_jd,
        max_age_years=float(max_age_years),
        key=resolved_key,
        bound_doctrine=bound_doctrine,
        events=tuple(events),
        distributor_periods=tuple(all_distributor_periods),
    )

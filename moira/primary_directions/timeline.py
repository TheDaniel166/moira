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
from typing import Iterable, Sequence

from ..constants import TROPICAL_YEAR
from ..julian import safe_datetime_from_jd
from ..egyptian_bounds import EgyptianBoundsDoctrine
from .keys import (
    PrimaryDirectionKey,
    PrimaryDirectionKeyPolicy,
    convert_arc_to_time,
    invert_solar_arc_lon,
    invert_solar_arc_ra,
)
from .methods import PrimaryDirectionMethod
from .spaces import PrimaryDirectionSpace
from .converse import PrimaryDirectionMotion
from .relations import PrimaryDirectionRelationalKind
from .targets import (
    PrimaryDirectionBoundTarget,
    resolve_primary_direction_bound_targets,
)
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
        natal_jd_ut: Julian Date (UT) of the natal origin.
        max_age_years: Upper bound age for timeline inclusion.
        key: Primary direction time-key used for arc-to-time projection.
        events: Chronologically sorted tuple of timeline events.
        distributor_periods: Chronological bound periods spanning the life.
    """
    chart_id: str
    natal_jd_ut: float
    max_age_years: float
    key: PrimaryDirectionKey
    events: tuple[PrimaryDirectionTimelineEvent, ...]
    distributor_periods: tuple[DistributorPeriod, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.natal_jd_ut, Real) or not math.isfinite(self.natal_jd_ut):
            raise ValueError("PrimaryDirectionsTimeline natal_jd_ut must be finite real")
        if not isinstance(self.max_age_years, Real) or not math.isfinite(self.max_age_years) or self.max_age_years <= 0.0:
            raise ValueError("PrimaryDirectionsTimeline max_age_years must be positive finite real")
        if not isinstance(self.key, PrimaryDirectionKey):
            raise ValueError("PrimaryDirectionsTimeline key must be PrimaryDirectionKey")


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
        speculum,
    )

    resolved_key = PrimaryDirectionKey(str(key).lower()) if not isinstance(key, PrimaryDirectionKey) else key

    # Derive safe angular search arc to cover max_age_years
    if max_arc is None:
        # Solar RA velocity can reach ~1.15 deg/day; allow 15% margin + 2 deg
        resolved_max_arc = min(180.0, float(max_age_years) * 1.15 + 2.0)
    else:
        resolved_max_arc = float(max_arc)

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

    if not base_policy.bound_targets:
        generated_bounds = resolve_primary_direction_bound_targets(doctrine=bound_doctrine)
        admitted = set(base_policy.relation_policy.admitted_kinds) | {PrimaryDirectionRelationalKind.TERM_BOUND}
        effective_policy = replace(
            base_policy,
            bound_targets=generated_bounds,
            relation_policy=PrimaryDirectionRelationPolicy(frozenset(admitted)),
        )
    else:
        admitted = set(base_policy.relation_policy.admitted_kinds) | {PrimaryDirectionRelationalKind.TERM_BOUND}
        effective_policy = replace(
            base_policy,
            relation_policy=PrimaryDirectionRelationPolicy(frozenset(admitted)),
        )

    # Search directional arcs
    raw_arcs = find_primary_arcs(
        chart=chart,
        houses=houses,
        geo_lat=geo_lat,
        max_arc=resolved_max_arc,
        include_converse=effective_policy.include_converse,
        significators=list(significators) if significators is not None else None,
        promissors=list(promissors) if promissors is not None else None,
        obliquity=obliquity,
        policy=effective_policy,
    )

    # Obtain natal time
    chart_jd = getattr(chart, "jd_ut", getattr(chart, "jd", None))
    if chart_jd is None or not math.isfinite(chart_jd):
        chart_jd = 2451545.0  # Fallback anchor

    # Speculum mapping for natal longitudes
    obl = obliquity if obliquity is not None else getattr(chart, "obliquity", 23.4392911)
    spec_entries = speculum(chart, houses, geo_lat, obliquity=obl)
    sp_map = {entry.name: entry for entry in spec_entries}

    # Partition bound boundaries and aspectual arcs for distributor chronology
    bound_arcs = [a for a in raw_arcs if a.relational_kind is PrimaryDirectionRelationalKind.TERM_BOUND]
    aspect_arcs = [a for a in raw_arcs if a.relational_kind is not PrimaryDirectionRelationalKind.TERM_BOUND]

    # Resolve distributor periods for significators (all significators present if not specified)
    sig_set = set(significators) if significators is not None else {a.significator for a in raw_arcs}
    if not sig_set:
        sig_set = {"Ascendant"}

    admitted_distributor_motions = [PrimaryDirectionMotion.DIRECT]
    if effective_policy.include_converse:
        admitted_distributor_motions.append(PrimaryDirectionMotion.CONVERSE)

    distributor_periods_by_sig_motion: dict[tuple[str, PrimaryDirectionMotion], list[DistributorPeriod]] = {}
    for sig in sig_set:
        natal_lon = None
        if sig in sp_map:
            natal_lon = getattr(sp_map[sig], "lon", getattr(sp_map[sig], "longitude", None))
        elif sig == "Ascendant" and hasattr(houses, "asc"):
            natal_lon = houses.asc
        elif sig == "Midheaven" and hasattr(houses, "mc"):
            natal_lon = houses.mc

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
                        if resolved_key is PrimaryDirectionKey.SOLAR_RA_DYNAMIC:
                            try:
                                ent_age, ent_jd = invert_solar_arc_ra(chart_jd, p.entry_arc_deg, reader=reader)
                            except Exception:
                                ent_age = convert_arc_to_time(p.entry_arc_deg, key=resolved_key, natal_jd_ut=chart_jd, reader=reader)
                                ent_jd = chart_jd + ent_age * TROPICAL_YEAR
                        elif resolved_key is PrimaryDirectionKey.SOLAR_LON_DYNAMIC:
                            try:
                                ent_age, ent_jd = invert_solar_arc_lon(chart_jd, p.entry_arc_deg, reader=reader)
                            except Exception:
                                ent_age = convert_arc_to_time(p.entry_arc_deg, key=resolved_key, natal_jd_ut=chart_jd, reader=reader)
                                ent_jd = chart_jd + ent_age * TROPICAL_YEAR
                        else:
                            ent_age = convert_arc_to_time(p.entry_arc_deg, key=resolved_key, natal_jd_ut=chart_jd, reader=reader)
                            ent_jd = chart_jd + ent_age * TROPICAL_YEAR

                    if resolved_key is PrimaryDirectionKey.SOLAR_RA_DYNAMIC:
                        try:
                            ext_age, ext_jd = invert_solar_arc_ra(chart_jd, p.exit_arc_deg, reader=reader)
                        except Exception:
                            ext_age = convert_arc_to_time(p.exit_arc_deg, key=resolved_key, natal_jd_ut=chart_jd, reader=reader)
                            ext_jd = chart_jd + ext_age * TROPICAL_YEAR
                    elif resolved_key is PrimaryDirectionKey.SOLAR_LON_DYNAMIC:
                        try:
                            ext_age, ext_jd = invert_solar_arc_lon(chart_jd, p.exit_arc_deg, reader=reader)
                        except Exception:
                            ext_age = convert_arc_to_time(p.exit_arc_deg, key=resolved_key, natal_jd_ut=chart_jd, reader=reader)
                            ext_jd = chart_jd + ext_age * TROPICAL_YEAR
                    else:
                        ext_age = convert_arc_to_time(p.exit_arc_deg, key=resolved_key, natal_jd_ut=chart_jd, reader=reader)
                        ext_jd = chart_jd + ext_age * TROPICAL_YEAR

                    ent_iso = safe_datetime_from_jd(ent_jd).isoformat()
                    ext_iso = safe_datetime_from_jd(ext_jd).isoformat()

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
        if resolved_key is PrimaryDirectionKey.SOLAR_RA_DYNAMIC:
            try:
                age, perf_jd = invert_solar_arc_ra(chart_jd, arc.arc, reader=reader)
            except Exception:
                age = convert_arc_to_time(arc.arc, key=resolved_key, solar_rate=arc.solar_rate, natal_jd_ut=chart_jd, reader=reader)
                perf_jd = chart_jd + age * TROPICAL_YEAR
        elif resolved_key is PrimaryDirectionKey.SOLAR_LON_DYNAMIC:
            try:
                age, perf_jd = invert_solar_arc_lon(chart_jd, arc.arc, reader=reader)
            except Exception:
                age = convert_arc_to_time(arc.arc, key=resolved_key, solar_rate=arc.solar_rate, natal_jd_ut=chart_jd, reader=reader)
                perf_jd = chart_jd + age * TROPICAL_YEAR
        else:
            age = convert_arc_to_time(arc.arc, key=resolved_key, solar_rate=arc.solar_rate, natal_jd_ut=chart_jd, reader=reader)
            perf_jd = chart_jd + age * TROPICAL_YEAR

        if not (0.0 < age <= max_age_years):
            continue

        perf_iso = safe_datetime_from_jd(perf_jd).isoformat()

        # Check distributor and bound context
        is_bound_boundary = arc.relational_kind is PrimaryDirectionRelationalKind.TERM_BOUND
        distributor = None
        bound_name = None
        participator = None

        sig_periods = distributor_periods_by_sig_motion.get((arc.significator, arc.motion))
        if sig_periods is None and arc.motion is not None:
            sig_periods = distributor_periods_by_sig_motion.get((arc.significator, PrimaryDirectionMotion.DIRECT))
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

    chart_identifier = getattr(chart, "id", "") or getattr(chart, "name", "") or "natal"

    return PrimaryDirectionsTimeline(
        chart_id=chart_identifier,
        natal_jd_ut=chart_jd,
        max_age_years=float(max_age_years),
        key=resolved_key,
        events=tuple(events),
        distributor_periods=tuple(all_distributor_periods),
    )

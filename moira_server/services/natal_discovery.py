"""Compose natal evidence using existing Moira doctrine and ephemeris products.

Supplied longitude geometry is preserved. Lunar products additionally require a
numerical witness against the named geocentric chart instant and zodiac frame.
No classification, rulership, aspect-orb or ephemeris algorithm lives here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from moira import Moira
from moira.aspects import aspects_between
from moira.chart_shape import _compute_gaps, _sorted_longitudes, classify_chart_shape
from moira.constants import Aspect, Body, SIGNS
from moira.coordinates import angular_distance, normalize_degrees
from moira.dignities import DOMICILE, calculate_dispositorship
from moira.julian import jd_from_datetime, utc_to_ut1, utc_datetime_from_ut1
from moira.phase import illuminated_fraction, phase_angle, synodic_phase_state
from moira.planets import planet_at
from moira.sidereal import ayanamsa
from moira.spk_reader import use_reader_override
from moira.transits import last_full_moon, last_new_moon

from ..models.natal_discovery import (
    NatalDiscoveryRequest,
    NatalDiscoverySource,
    NatalDispositorChain,
    NatalDispositorLink,
    NatalDispositorsResponse,
    NatalLunarContactPolicy,
    NatalLunarContextResponse,
    NatalLunarPhase,
    NatalLunationContact,
    NatalLunationEvent,
    NatalRulership,
    NatalShapeClassification,
    NatalShapeGap,
    NatalShapePosition,
    NatalShapeResponse,
    NatalSourceConsistency,
)


# Transport consistency, not an advertised ephemeris accuracy: comfortably
# admits the website's decimal serialization and microsecond civil-time input.
_SOURCE_TOLERANCE_DEG = 1e-6


def _source(request: NatalDiscoveryRequest) -> NatalDiscoverySource:
    dt = datetime.fromisoformat(request.dt.replace("Z", "+00:00"))
    return NatalDiscoverySource(
        requested_datetime=request.dt,
        normalized_datetime_utc=dt.astimezone(timezone.utc).isoformat(),
        jd_ut1=utc_to_ut1(jd_from_datetime(dt)),
        zodiac=request.zodiac,
        ayanamsa_system=request.ayanamsa_system,
        time_unknown=request.time_unknown,
        reference_kind="noon_reference" if request.time_unknown else "recorded_time",
    )


def compute_natal_dispositors(request: NatalDiscoveryRequest) -> NatalDispositorsResponse:
    """Expose classic-seven traditional chains without completing hidden bodies."""

    profile = calculate_dispositorship(
        [{"name": name, "degree": degree} for name, degree in request.longitudes.items()]
    )
    chains = []
    for chain in profile.chains:
        termination = chain.termination_kind.value
        missing_ruler = None
        if not chain.subject_in_scope:
            termination = "out_of_scope"
        elif termination == "unresolved":
            termination = "missing_selected_ruler"
            missing_ruler = chain.links[-1].dispositor if chain.links else None
        chains.append(NatalDispositorChain(
            body=chain.initial_subject,
            sign=chain.initial_sign,
            longitude_deg=request.longitudes[chain.initial_subject],
            in_scope=chain.subject_in_scope,
            links=[NatalDispositorLink(
                subject=link.subject,
                subject_sign=link.subject_sign,
                dispositor=link.dispositor,
            ) for link in chain.links],
            visited_subjects=list(chain.visited_subjects),
            termination=termination,
            terminal_subjects=list(chain.terminal_subjects),
            cycle_members=list(chain.cycle_members),
            missing_ruler=missing_ruler,
        ))
    return NatalDispositorsResponse(
        source=_source(request),
        rulerships=[NatalRulership(
            sign=sign,
            ruler=next(planet for planet, signs in DOMICILE.items() if sign in signs),
        ) for sign in SIGNS],
        chains=chains,
        final_dispositors=list(profile.final_dispositors),
        terminal_cycles=[list(cycle) for cycle in profile.terminal_cycles],
        excluded_subjects=list(profile.unsupported_subjects),
    )


def compute_natal_shape(request: NatalDiscoveryRequest) -> NatalShapeResponse:
    """Expose Jones classification and full-chart circular gaps independently."""

    source = _source(request)
    missing = [body for body in Body.ALL_PLANETS if body not in request.longitudes]
    ordered = _sorted_longitudes(request.longitudes)
    positions = [NatalShapePosition(body=body, longitude_deg=degree) for degree, body in ordered]
    if missing:
        return NatalShapeResponse(
            source=source, status="insufficient_selection", missing_bodies=missing,
            positions=positions, classification=None, gaps=[],
            classification_note="Jones's method requires all ten planets from Sun through Pluto. Select the missing planets to classify this chart.",
        )
    shape = classify_chart_shape(request.longitudes)
    gaps = _compute_gaps(ordered)
    largest_full_gap = max(gap for gap, _, _ in gaps)
    bucket = shape.handle_planet is not None
    return NatalShapeResponse(
        source=source, status="classified", missing_bodies=[], positions=positions,
        classification=NatalShapeClassification(
            shape=shape.shape.value,
            occupied_arc_deg=shape.occupied_arc,
            largest_gap_deg=shape.largest_gap,
            leading_planet=shape.leading_planet,
            handle_planet=shape.handle_planet,
            handle_bodies=sorted(shape.handle_bodies),
            clusters=[sorted(cluster) for cluster in shape.clusters],
            metrics_scope="nine_planet_bowl_core" if bucket else "all_ten",
        ),
        gaps=[NatalShapeGap(
            from_body=ordered[start][1], to_body=ordered[end][1],
            from_longitude_deg=ordered[start][0], to_longitude_deg=ordered[end][0],
            gap_deg=gap, is_largest=gap == largest_full_gap,
        ) for gap, start, end in gaps],
        classification_note=(
            "Bucket arc and gap measure the nine-planet Bowl core with its single handle removed. The gap list separately measures all ten planets."
            if bucket else
            "Splash is Moira's documented residual choice after the other Jones structures are tested; borderline charts remain a judgement call in Jones's source."
            if shape.shape.value == "Splash" else
            "Classified under Jones's ten-planet temperament method, using Moira's declared detection order and source-specific gap and aspect-orb rules."
        ),
    )


def _frame_offset(request: NatalDiscoveryRequest, jd_ut1: float) -> float:
    return ayanamsa(jd_ut1, request.ayanamsa_system, "true") if request.zodiac == "Sidereal" else 0.0


def compute_natal_lunar_context(engine: Moira, request: NatalDiscoveryRequest) -> NatalLunarContextResponse:
    """Compose matched natal phase geometry and strict preceding geocentric lunations."""

    source = _source(request)
    missing = [body for body in (Body.SUN, Body.MOON) if body not in request.longitudes]
    if request.time_unknown or missing:
        return NatalLunarContextResponse(
            source=source, status="unknown_time" if request.time_unknown else "missing_luminaries",
            missing_bodies=missing, phase=None, events=[], contacts=[],
            contact_policy=None, source_consistency=None,
        )
    with use_reader_override(engine._reader):
        return _compute_known_lunar_context(engine, request, source)


def _compute_known_lunar_context(
    engine: Moira,
    request: NatalDiscoveryRequest,
    source: NatalDiscoverySource,
) -> NatalLunarContextResponse:
    """Use one reader context for every ephemeris product in the packet."""

    instant = datetime.fromisoformat(request.dt.replace("Z", "+00:00"))
    witness = engine.chart(instant, bodies=list(request.longitudes), include_nodes=False)
    if set(witness.planets) != set(request.longitudes):
        raise ValueError("The engine could not witness every selected natal planet. Recalculate the natal chart.")
    offset = _frame_offset(request, source.jd_ut1)
    residuals = {
        body: angular_distance(request.longitudes[body], normalize_degrees(position.longitude - offset))
        for body, position in witness.planets.items()
    }
    mismatched = [body for body, residual in residuals.items() if residual > _SOURCE_TOLERANCE_DEG]
    if mismatched:
        raise ValueError("The accepted chart longitudes do not match the supplied birth time and zodiac for "
                         + ", ".join(mismatched) + ". Recalculate the natal chart before opening lunar context.")

    sun = request.longitudes[Body.SUN]
    moon = request.longitudes[Body.MOON]
    angle = normalize_degrees(moon - sun)
    physical_angle = phase_angle(Body.MOON, source.jd_ut1)
    reader = engine._reader
    solved = [
        ("New Moon", last_new_moon(source.jd_ut1, reader=reader)),
        ("Full Moon", last_full_moon(source.jd_ut1, reader=reader)),
    ]
    if any(jd >= source.jd_ut1 for _, jd in solved):
        raise ValueError("A strictly preceding lunation could not be established at this exact reference instant.")
    latest = max(jd for _, jd in solved)
    events = []
    contacts = []
    for label, jd in sorted(solved, key=lambda item: item[1]):
        event_offset = _frame_offset(request, jd)
        event_sun = normalize_degrees(planet_at(Body.SUN, jd, reader=reader).longitude - event_offset)
        event_moon = normalize_degrees(planet_at(Body.MOON, jd, reader=reader).longitude - event_offset)
        events.append(NatalLunationEvent(
            phase=label, jd_ut1=jd,
            # Solvers return UT1; civil display uses Moira's admitted inverse,
            # preserving the historical proxy / atomic UTC boundary policy.
            datetime_utc=utc_datetime_from_ut1(jd).isoformat(),
            sun_longitude_deg=event_sun, moon_longitude_deg=event_moon,
            ayanamsa_deg=event_offset, days_before_reference=source.jd_ut1 - jd,
            is_prenatal_syzygy=jd == latest,
        ))
        for body in Body.ALL_PLANETS:
            if body not in request.longitudes:
                continue
            for aspect in aspects_between(Body.MOON, event_moon, body, request.longitudes[body], tier=0, orb_factor=1.0):
                contacts.append(NatalLunationContact(
                    event_phase=label, event_jd_ut1=jd, body=body,
                    event_moon_longitude_deg=event_moon,
                    natal_longitude_deg=request.longitudes[body], aspect=aspect.aspect,
                    angle_deg=aspect.angle, separation_deg=aspect.separation,
                    orb_deg=aspect.orb, allowed_orb_deg=aspect.allowed_orb,
                ))
    return NatalLunarContextResponse(
        source=source, status="calculated", missing_bodies=[],
        phase=NatalLunarPhase(
            angle_deg=angle, state=synodic_phase_state(angle), waxing=angle < 180.0,
            physical_phase_angle_deg=physical_angle,
            illuminated_fraction=illuminated_fraction(physical_angle),
            sun_longitude_deg=sun, moon_longitude_deg=moon,
        ),
        events=events, contacts=contacts,
        contact_policy=NatalLunarContactPolicy(aspects=[aspect.name for aspect in Aspect.MAJOR]),
        source_consistency=NatalSourceConsistency(
            tolerance_deg=_SOURCE_TOLERANCE_DEG,
            maximum_residual_deg=max(residuals.values()),
        ),
    )

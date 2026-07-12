"""Engine-only service boundary for progressed Astrodynes REST routes."""

from __future__ import annotations

from moira import Moira
from moira.progressed_astrodynes import (
    DEFAULT_PROGRESSED_ASTRODYNE_POLICY,
    PROGRESSED_ASTRODYNE_SOURCE_ANOMALIES,
    ProgressedAstrodyneTier,
    ProgressedAstrodyneTerminal,
    ProgressedCompoundDuration,
    ProgressedInfluenceUnit,
    ProgressedMutualReceptionAllocation,
    ProgressedTerminalKind,
    ProgressedTerminalLocation,
    ProgressedBaselineValue,
    ProgressedBodyPlacement,
    ProgressedNatalBodyValue,
    normal_progressed_horoscope,
    evaluate_accessory_progressed_relation,
    evaluate_major_progressed_relation,
    practical_progressed_horoscope,
    progressed_dated_aspect,
    progressed_compound_total_influence,
    progressed_total_influence,
    reenforce_major_progressed_relation,
)
from moira.progressed_astrodynes_search import ProgressedContactQuery

from ..models.progressed_astrodynes import (
    ProgressedAccessoryRelationRequest,
    ProgressedAstrodynesChartRequest,
    ProgressedCompoundInfluenceRequest,
    ProgressedContactSearchRequest,
    ProgressedDatedAspectRequest,
    ProgressedMajorRelationRequest,
    ProgressedNormalRequest,
    ProgressedPracticalRequest,
    ProgressedReenforcementRequest,
    ProgressedTotalInfluenceRequest,
    ProgressedInfluenceIntegrationRequest,
)


def _terminal(request):
    return ProgressedAstrodyneTerminal(
        request.body,
        request.kind,
        request.longitude_deg,
        request.house_class,
        request.declination_deg,
    )


def _natal(request):
    return ProgressedNatalBodyValue(
        request.body,
        request.power,
        request.harmony,
        request.discord,
    )


def get_progressed_astrodynes_doctrine() -> dict[str, object]:
    return {
        "doctrine": "church_of_light_progressed_astrodynes",
        "parity_status": "doctrinal_parity_with_published_anomalies",
        "kernel_required": False,
        "policy": DEFAULT_PROGRESSED_ASTRODYNE_POLICY,
        "tiers": tuple(item.value for item in ProgressedAstrodyneTier),
        "terminal_kinds": tuple(item.value for item in ProgressedTerminalKind),
        "source_anomalies": PROGRESSED_ASTRODYNE_SOURCE_ANOMALIES,
    }


def compute_progressed_chart(
    engine: Moira,
    request: ProgressedAstrodynesChartRequest,
):
    return engine.progressed_astrodynes_chart(
        request.natal_dt,
        request.target_dt,
        request.observer_lat,
        request.observer_lon,
        house_system=request.house_system,
        allow_house_fallback=request.allow_house_fallback,
    )


def _contact_query(request) -> ProgressedContactQuery:
    return ProgressedContactQuery(
        request.body_a,
        request.kind_a,
        request.body_b,
        request.kind_b,
        request.aspect,
    )


def search_progressed_contact_windows(
    engine: Moira,
    request: ProgressedContactSearchRequest,
):
    return engine.search_progressed_astrodyne_contacts(
        request.natal_dt,
        request.start_dt,
        request.end_dt,
        request.observer_lat,
        request.observer_lon,
        _contact_query(request.query),
        house_system=request.house_system,
        allow_house_fallback=request.allow_house_fallback,
        coarse_step_hours=request.coarse_step_hours,
        boundary_tolerance_seconds=request.boundary_tolerance_seconds,
        perfection_tolerance_seconds=request.perfection_tolerance_seconds,
        perfection_distance_tolerance_arcmin=(
            request.perfection_distance_tolerance_arcmin
        ),
        max_samples=request.max_samples,
        reenforces_major=(
            None
            if request.reenforces_major is None
            else _contact_query(request.reenforces_major)
        ),
    )


def integrate_progressed_contact_influence(
    engine: Moira,
    request: ProgressedInfluenceIntegrationRequest,
):
    return engine.integrate_progressed_astrodyne_influence(
        request.natal_dt,
        request.start_dt,
        request.end_dt,
        request.observer_lat,
        request.observer_lon,
        _contact_query(request.query),
        house_system=request.house_system,
        allow_house_fallback=request.allow_house_fallback,
        max_step_hours=request.max_step_hours,
        max_samples=request.max_samples,
    )


def compute_progressed_normal(request: ProgressedNormalRequest):
    return normal_progressed_horoscope(
        tuple(
            ProgressedNatalBodyValue(
                item.body,
                item.power,
                item.harmony,
                item.discord,
            )
            for item in request.birth_bodies
        ),
        {
            sign: ProgressedBaselineValue(value.power, value.harmony, value.discord)
            for sign, value in request.birth_signs.items()
        },
        {
            house: ProgressedBaselineValue(value.power, value.harmony, value.discord)
            for house, value in request.birth_houses.items()
        },
        tuple(
            ProgressedBodyPlacement(item.body, item.longitude_deg, item.house)
            for item in request.placements
        ),
    )


def compute_progressed_dated_aspect(request: ProgressedDatedAspectRequest):
    return progressed_dated_aspect(
        request.relation_id,
        request.body_a,
        request.body_b,
        request.aspect,
        request.direct_terminal_ids,
        request.indirect_terminal_ids,
        request.peak_power,
        request.distance_arcmin,
    )


def compute_progressed_major_relation(request: ProgressedMajorRelationRequest):
    return evaluate_major_progressed_relation(
        _terminal(request.direct_a),
        _terminal(request.direct_b),
        _terminal(request.counterpart_a) if request.counterpart_a else None,
        _terminal(request.counterpart_b) if request.counterpart_b else None,
        _natal(request.natal_a),
        _natal(request.natal_b),
        request.aspect,
    )


def compute_progressed_accessory_relation(
    request: ProgressedAccessoryRelationRequest,
):
    return evaluate_accessory_progressed_relation(
        _terminal(request.moving_terminal),
        _terminal(request.target_terminal),
        _terminal(request.target_counterpart),
        _natal(request.natal_moving),
        _natal(request.natal_target),
        request.aspect,
    )


def compute_progressed_reenforcement(request: ProgressedReenforcementRequest):
    return reenforce_major_progressed_relation(
        compute_progressed_major_relation(request.major),
        compute_progressed_accessory_relation(request.minor),
    )


def compute_progressed_practical(request: ProgressedPracticalRequest):
    normal = compute_progressed_normal(request.normal)
    aspects = tuple(compute_progressed_dated_aspect(item) for item in request.aspects)
    locations = tuple(
        ProgressedTerminalLocation(item.terminal_id, item.sign, item.house)
        for item in request.terminal_locations
    )
    receptions = tuple(
        ProgressedMutualReceptionAllocation(
            item.allocation_id,
            item.body,
            item.direct_terminal_ids,
            item.indirect_terminal_ids,
            item.harmony,
        )
        for item in request.mutual_receptions
    )
    return practical_progressed_horoscope(
        normal,
        aspects,
        locations,
        request.house_cusp_signs,
        request.intercepted_signs,
        receptions,
    )


def compute_progressed_total_influence(request: ProgressedTotalInfluenceRequest):
    return progressed_total_influence(
        request.peak_power,
        request.peak_harmony,
        request.peak_discord,
        request.duration,
        ProgressedInfluenceUnit(request.unit),
    )


def compute_progressed_compound_influence(
    request: ProgressedCompoundInfluenceRequest,
):
    return progressed_compound_total_influence(
        request.peak_power,
        request.peak_harmony,
        request.peak_discord,
        ProgressedCompoundDuration(
            years=request.duration.years,
            months=request.duration.months,
            days=request.duration.days,
        ),
    )


__all__ = [
    "compute_progressed_accessory_relation",
    "compute_progressed_compound_influence",
    "compute_progressed_chart",
    "compute_progressed_dated_aspect",
    "compute_progressed_major_relation",
    "compute_progressed_normal",
    "compute_progressed_practical",
    "compute_progressed_reenforcement",
    "compute_progressed_total_influence",
    "get_progressed_astrodynes_doctrine",
    "integrate_progressed_contact_influence",
    "search_progressed_contact_windows",
]

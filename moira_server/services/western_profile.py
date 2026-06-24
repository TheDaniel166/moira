"""Composition service for Western chart-profile bundles."""

from __future__ import annotations

from moira import Moira

from ..models.chart import ChartRequest, HousesRequest
from ..models.dignities import DignitiesChartRequest
from ..models.profile_bundles import ProfileBundleProvenanceResponse
from ..models.western_profile import (
    WesternChartProfileRequest,
    WesternChartProfileResponse,
)
from ..serializers.chart import (
    serialize_chart_with_reduction,
    serialize_houses_with_reduction,
)
from ..serializers.dignities import (
    serialize_chart_condition_profile,
    serialize_dignities_result,
)
from .chart import compute_chart_with_reduction, compute_houses_with_reduction
from .dignities import compute_dignities_chart, compute_dignities_chart_profile


def _chart_request(request: WesternChartProfileRequest) -> ChartRequest:
    return ChartRequest(
        dt=request.dt,
        bodies=request.bodies,
        include_nodes=request.include_nodes,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )


def _houses_request(request: WesternChartProfileRequest) -> HousesRequest:
    return HousesRequest(
        dt=request.dt,
        latitude=request.observer_lat,
        longitude=request.observer_lon,
        system=request.house_system,
        policy=request.house_policy,
    )


def _dignities_request(request: WesternChartProfileRequest) -> DignitiesChartRequest:
    return DignitiesChartRequest(
        dt=request.dt,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
        house_system=request.house_system,
        policy=request.dignity_policy,
    )


def _provenance(
    included_sections: tuple[str, ...],
    included_surfaces: tuple[str, ...],
) -> ProfileBundleProvenanceResponse:
    return ProfileBundleProvenanceResponse(
        source_surface="/v1/western/chart-profile",
        doctrine_boundary=(
            "Western convenience bundle; composes existing chart, houses, "
            "and classical dignity route surfaces without introducing "
            "interpretive synthesis."
        ),
        included_existing_surfaces=included_surfaces,
        stage_sequence=included_sections,
    )


def compute_western_chart_profile(
    engine: Moira,
    request: WesternChartProfileRequest,
) -> WesternChartProfileResponse:
    """Compute a Western profile bundle from existing route-equivalent strata."""

    included_sections: list[str] = []
    included_surfaces: list[str] = []
    chart_response = None
    chart_reduction = None
    houses_response = None
    houses_reduction = None
    dignities_response = None
    dignity_profile_response = None

    if request.include.chart:
        chart, reduction = compute_chart_with_reduction(engine, _chart_request(request))
        serialized = serialize_chart_with_reduction(chart, reduction)
        chart_response = serialized.result
        chart_reduction = serialized.reduction
        included_sections.extend(("chart", "chart_reduction"))
        included_surfaces.append("POST /v1/chart/reduction")

    if request.include.houses:
        houses, reduction = compute_houses_with_reduction(
            engine,
            _houses_request(request),
        )
        serialized = serialize_houses_with_reduction(houses, reduction)
        houses_response = serialized.result
        houses_reduction = serialized.reduction
        included_sections.extend(("houses", "houses_reduction"))
        included_surfaces.append("POST /v1/houses/reduction")

    dignity_request = _dignities_request(request)
    if request.include.dignities:
        dignities_response = serialize_dignities_result(
            compute_dignities_chart(engine, dignity_request)
        )
        included_sections.append("dignities")
        included_surfaces.append("POST /v1/dignities/chart")

    if request.include.dignity_profile:
        dignity_profile_response = serialize_chart_condition_profile(
            compute_dignities_chart_profile(engine, dignity_request)
        )
        included_sections.append("dignity_profile")
        included_surfaces.append("POST /v1/dignities/chart/profile")

    sections = tuple(included_sections)
    return WesternChartProfileResponse(
        request=request,
        included_sections=sections,
        chart=chart_response,
        chart_reduction=chart_reduction,
        houses=houses_response,
        houses_reduction=houses_reduction,
        dignities=dignities_response,
        dignity_profile=dignity_profile_response,
        provenance=_provenance(sections, tuple(included_surfaces)),
    )


__all__ = ["compute_western_chart_profile"]

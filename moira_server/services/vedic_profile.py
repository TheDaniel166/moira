"""Composition service for Vedic chart-profile bundles."""

from __future__ import annotations

from moira import Moira

from ..models.chart import ChartRequest
from ..models.dasha import DashaCurrentRequest, DashaNatalRequest
from ..models.panchanga import PanchangaChartRequest
from ..models.profile_bundles import ProfileBundleProvenanceResponse
from ..models.shadbala import ShadbalaChartRequest
from ..models.vedic_profile import (
    VedicChartProfileRequest,
    VedicChartProfileResponse,
)
from ..serializers.chart import serialize_chart_with_reduction
from ..serializers.dasha import (
    serialize_dasha_active_line,
    serialize_dasha_lord_pair,
)
from ..serializers.panchanga import (
    serialize_panchanga_profile,
    serialize_panchanga_result,
)
from ..serializers.shadbala import (
    serialize_shadbala_chart_profile,
    serialize_shadbala_result,
)
from .chart import compute_chart_with_reduction
from .dasha import compute_dasha_active_line, compute_dasha_lord_pair_service
from .panchanga import compute_panchanga_chart, compute_panchanga_chart_profile
from .shadbala import compute_shadbala_chart, compute_shadbala_chart_profile


def _chart_request(request: VedicChartProfileRequest) -> ChartRequest:
    return ChartRequest(
        dt=request.dt,
        bodies=request.bodies,
        include_nodes=request.include_nodes,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )


def _panchanga_request(request: VedicChartProfileRequest) -> PanchangaChartRequest:
    return PanchangaChartRequest(
        dt=request.dt,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
        ayanamsa_system=request.ayanamsa_system,
        policy=request.panchanga_policy,
    )


def _shadbala_request(request: VedicChartProfileRequest) -> ShadbalaChartRequest:
    return ShadbalaChartRequest(
        dt=request.dt,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
        house_system=request.house_system,
        ayanamsa_system=request.ayanamsa_system,
        hora_lord=request.hora_lord,
        policy=request.shadbala_policy,
    )


def _dasha_request(request: VedicChartProfileRequest) -> DashaCurrentRequest:
    if request.current_dt is None:
        raise ValueError(
            "current_dt is required when requesting Vedic dasha snapshot sections"
        )
    return DashaCurrentRequest(
        natal=DashaNatalRequest(
            dt=request.dt,
            ayanamsa=request.ayanamsa_system,
            year_basis=request.dasha_year_basis,
        ),
        current_dt=request.current_dt,
        levels=request.dasha_levels,
    )


def _provenance(
    included_sections: tuple[str, ...],
    included_surfaces: tuple[str, ...],
) -> ProfileBundleProvenanceResponse:
    return ProfileBundleProvenanceResponse(
        source_surface="/v1/vedic/chart-profile",
        doctrine_boundary=(
            "Vedic convenience bundle; composes existing chart, Panchanga, "
            "Shadbala, and optional Vimshottari route surfaces without "
            "mixing them with Western profile doctrine."
        ),
        included_existing_surfaces=included_surfaces,
        stage_sequence=included_sections,
    )


def compute_vedic_chart_profile(
    engine: Moira,
    request: VedicChartProfileRequest,
) -> VedicChartProfileResponse:
    """Compute a Vedic profile bundle from existing route-equivalent strata."""

    included_sections: list[str] = []
    included_surfaces: list[str] = []
    chart_response = None
    chart_reduction = None
    panchanga_response = None
    panchanga_profile_response = None
    shadbala_response = None
    shadbala_profile_response = None
    dasha_current_response = None
    dasha_lord_pair_response = None

    if request.include.chart:
        chart, reduction = compute_chart_with_reduction(engine, _chart_request(request))
        serialized = serialize_chart_with_reduction(chart, reduction)
        chart_response = serialized.result
        chart_reduction = serialized.reduction
        included_sections.extend(("chart", "chart_reduction"))
        included_surfaces.append("POST /v1/chart/reduction")

    panchanga_request = _panchanga_request(request)
    if request.include.panchanga:
        panchanga_response = serialize_panchanga_result(
            compute_panchanga_chart(engine, panchanga_request)
        )
        included_sections.append("panchanga")
        included_surfaces.append("POST /v1/panchanga/chart")

    if request.include.panchanga_profile:
        panchanga_profile_response = serialize_panchanga_profile(
            compute_panchanga_chart_profile(engine, panchanga_request)
        )
        included_sections.append("panchanga_profile")
        included_surfaces.append("POST /v1/panchanga/chart/profile")

    shadbala_request = _shadbala_request(request)
    if request.include.shadbala:
        shadbala_response = serialize_shadbala_result(
            compute_shadbala_chart(engine, shadbala_request)
        )
        included_sections.append("shadbala")
        included_surfaces.append("POST /v1/shadbala/chart")

    if request.include.shadbala_profile:
        shadbala_profile_response = serialize_shadbala_chart_profile(
            compute_shadbala_chart_profile(engine, shadbala_request)
        )
        included_sections.append("shadbala_profile")
        included_surfaces.append("POST /v1/shadbala/chart/profile")

    if request.include.dasha_current or request.include.dasha_lord_pair:
        dasha_request = _dasha_request(request)
        if request.include.dasha_current:
            dasha_current_response = serialize_dasha_active_line(
                compute_dasha_active_line(engine, dasha_request)
            )
            included_sections.append("dasha_current")
            included_surfaces.append("POST /v1/dasha/vimshottari/current")
        if request.include.dasha_lord_pair:
            dasha_lord_pair_response = serialize_dasha_lord_pair(
                compute_dasha_lord_pair_service(engine, dasha_request)
            )
            included_sections.append("dasha_lord_pair")
            included_surfaces.append("POST /v1/dasha/vimshottari/lord-pair")

    sections = tuple(included_sections)
    return VedicChartProfileResponse(
        request=request,
        included_sections=sections,
        chart=chart_response,
        chart_reduction=chart_reduction,
        panchanga=panchanga_response,
        panchanga_profile=panchanga_profile_response,
        shadbala=shadbala_response,
        shadbala_profile=shadbala_profile_response,
        dasha_current=dasha_current_response,
        dasha_lord_pair=dasha_lord_pair_response,
        provenance=_provenance(sections, tuple(included_surfaces)),
    )


__all__ = ["compute_vedic_chart_profile"]

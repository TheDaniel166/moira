"""Service layer for draconic chart-frame routes."""

from __future__ import annotations

from moira import Moira
from moira.draconic import (
    DraconicAnchor,
    DraconicChart,
    draconic_chart,
    draconic_chart_from_positions,
    draconic_longitude,
)

from ..models.chart import ChartRequest
from ..models.draconic import (
    DraconicAnchorResponse,
    DraconicChartRequest,
    DraconicChartResponse,
    DraconicLongitudeRequest,
    DraconicLongitudeResponse,
    DraconicPositionResponse,
    DraconicPositionsRequest,
    DraconicProvenanceResponse,
)
from ._shared import build_chart_context


def _serialize_anchor(anchor: DraconicAnchor) -> DraconicAnchorResponse:
    return DraconicAnchorResponse(
        node_mode=anchor.node_mode,
        node_name=anchor.node_name,
        longitude=anchor.longitude,
        rotation_degrees=anchor.rotation_degrees,
        source=anchor.source,
        source_zodiac=anchor.source_zodiac,
        formula=anchor.formula,
    )


def _serialize_chart(
    vessel: DraconicChart,
    provenance: DraconicProvenanceResponse,
) -> DraconicChartResponse:
    positions = [
        DraconicPositionResponse(
            body=position.body,
            source_longitude=position.source_longitude,
            draconic_longitude=position.draconic_longitude,
            sign=position.sign,
            sign_symbol=position.sign_symbol,
            sign_degree=position.sign_degree,
        )
        for position in vessel.positions
    ]
    return DraconicChartResponse(
        anchor=_serialize_anchor(vessel.anchor),
        positions=positions,
        count=len(positions),
        jd_ut=vessel.jd_ut,
        frame=vessel.frame,
        source_zodiac=vessel.source_zodiac,
        interpretation_scope=vessel.interpretation_scope,
        anchor_residual=vessel.anchor_residual,
        provenance=provenance,
    )


def compute_draconic_longitude(
    request: DraconicLongitudeRequest,
) -> DraconicLongitudeResponse:
    return DraconicLongitudeResponse(
        source_longitude=request.source_longitude,
        anchor_longitude=request.anchor_longitude,
        draconic_longitude=draconic_longitude(
            request.source_longitude, request.anchor_longitude
        ),
        normalized_range=[0.0, 360.0],
        provenance=DraconicProvenanceResponse(
            engine_entrypoint="draconic_longitude",
            node_policy=None,
            anchor_owner="caller_supplied",
            chart_construction_owner="not_this_route",
            ephemeris="not_used",
            stage_sequence=[
                "longitude_validation",
                "draconic_rotation",
                "draconic_longitude_response_serialization",
            ],
        ),
    )


def compute_draconic_positions(
    request: DraconicPositionsRequest,
) -> DraconicChartResponse:
    anchor = DraconicAnchor(
        node_mode=request.node_mode,
        longitude=request.anchor_longitude,
    )
    vessel = draconic_chart_from_positions(
        request.positions,
        anchor=anchor,
        jd_ut=request.jd_ut,
    )
    return _serialize_chart(
        vessel,
        DraconicProvenanceResponse(
            engine_entrypoint="draconic_chart_from_positions",
            node_policy=anchor.node_mode,
            anchor_owner="caller_supplied",
            chart_construction_owner="not_this_route",
            ephemeris="not_used",
            stage_sequence=[
                "positions_validation",
                "anchor_policy_resolution",
                "anchor_vessel_materialization",
                "draconic_rotation",
                "draconic_chart_vessel_materialization",
                "draconic_chart_response_serialization",
            ],
        ),
    )


def compute_draconic_chart(
    engine: Moira,
    request: DraconicChartRequest,
) -> DraconicChartResponse:
    # The anchor node must exist on the source chart, so the engine chart is
    # always built with nodes; request.include_nodes governs only whether node
    # points appear among the transformed output positions.
    chart_request = ChartRequest(
        dt=request.dt,
        bodies=request.bodies,
        include_nodes=True,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )
    chart = build_chart_context(engine, chart_request)
    vessel = draconic_chart(
        chart,
        node_mode=request.node_mode,
        include_nodes=request.include_nodes,
    )
    return _serialize_chart(
        vessel,
        DraconicProvenanceResponse(
            engine_entrypoint="draconic_chart",
            node_policy=vessel.anchor.node_mode,
            anchor_owner="engine_chart_nodes",
            chart_construction_owner="engine",
            ephemeris="engine_reader",
            stage_sequence=[
                "chart_request_validation",
                "engine_chart_materialization_with_nodes",
                "anchor_policy_resolution",
                "anchor_node_extraction",
                "draconic_rotation",
                "draconic_chart_vessel_materialization",
                "draconic_chart_response_serialization",
            ],
        ),
    )

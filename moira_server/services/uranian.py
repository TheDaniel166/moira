"""Service layer for Uranian / Hamburg School hypothetical-body routes."""

from __future__ import annotations

from moira import Moira
from moira.uranian import UranianPosition, all_uranian_at, list_uranian, uranian_at

from ..models.uranian import (
    UranianBulkRequest,
    UranianBulkResponse,
    UranianCatalogResponse,
    UranianPositionRequest,
    UranianPositionResponse,
    UranianProvenanceResponse,
    UranianSingleResponse,
)


def _provenance(
    entrypoint: str,
    stage_sequence: list[str],
    *,
    spk_kernel_used: bool,
) -> UranianProvenanceResponse:
    return UranianProvenanceResponse(
        engine_entrypoint=entrypoint,
        stage_sequence=stage_sequence,
        spk_kernel_used=spk_kernel_used,
    )


def _serialize_position(position: UranianPosition) -> UranianPositionResponse:
    return UranianPositionResponse(
        name=position.name,
        longitude=position.longitude,
        latitude=position.latitude,
        distance_au=position.distance_au,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        sign_degree=position.sign_degree,
        speed=position.speed,
        retrograde=position.retrograde,
        body_group=position.body_group,
        source_family=position.source_family,
        model=position.model,
        frame=position.frame,
    )


def _validate_known_name(name: str) -> None:
    if name not in list_uranian():
        valid = ", ".join(list_uranian())
        raise ValueError(
            f"Unknown Uranian body {name!r}. Valid names: {valid}"
        )


def list_uranian_catalog() -> UranianCatalogResponse:
    names = list_uranian()
    return UranianCatalogResponse(
        names=names,
        count=len(names),
        provenance=_provenance(
            "list_uranian",
            [
                "catalog_name_table_read",
                "hypothetical_body_provenance_assignment",
                "uranian_catalog_response_serialization",
            ],
            spk_kernel_used=False,
        ),
    )


def compute_uranian_position(
    engine: Moira,
    request: UranianPositionRequest,
) -> UranianSingleResponse:
    _validate_known_name(request.name)
    position = uranian_at(request.name, request.jd_ut, reader=engine._reader)
    return UranianSingleResponse(
        position=_serialize_position(position),
        provenance=_provenance(
            "uranian_at",
            [
                "jd_ut_validation",
                "case_sensitive_name_lookup",
                "ut1_to_kernel_tt_conversion",
                "source_orbit_materialization",
                "earth_sun_kernel_geometry",
                "apparent_geocentric_reduction",
                "finite_difference_longitude_rate",
                "sign_derivation",
                "uranian_position_response_serialization",
            ],
            spk_kernel_used=True,
        ),
    )


def compute_uranian_bulk(
    engine: Moira,
    request: UranianBulkRequest,
) -> UranianBulkResponse:
    if request.names is None:
        positions = all_uranian_at(request.jd_ut, reader=engine._reader)
        requested_names = list(positions)
        entrypoint = "all_uranian_at"
    else:
        for name in request.names:
            _validate_known_name(name)
        positions = {
            name: uranian_at(name, request.jd_ut, reader=engine._reader)
            for name in request.names
        }
        requested_names = request.names
        entrypoint = "uranian_at"

    serialized = {name: _serialize_position(position) for name, position in positions.items()}
    return UranianBulkResponse(
        positions=serialized,
        count=len(serialized),
        requested_names=requested_names,
        provenance=_provenance(
            entrypoint,
            [
                "jd_ut_validation",
                "case_sensitive_name_list_resolution",
                "ut1_to_kernel_tt_conversion",
                "source_orbit_materialization",
                "earth_sun_kernel_geometry",
                "apparent_geocentric_reduction",
                "finite_difference_longitude_rate",
                "sign_derivation",
                "uranian_bulk_response_serialization",
            ],
            spk_kernel_used=True,
        ),
    )

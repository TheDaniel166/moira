"""Service layer for P12-04 ordinary antiscia routes."""

from __future__ import annotations

from moira.antiscia import (
    AntisciaAspect,
    antiscion,
    antiscia_to_point,
    contra_antiscion,
    find_antiscia,
)

from ..models.antiscia import (
    AntisciaContactResponse,
    AntisciaContactsRequest,
    AntisciaContactsResponse,
    AntisciaProvenanceResponse,
    AntisciaReflectRequest,
    AntisciaReflectResponse,
    AntisciaToPointRequest,
)


def _serialize_contact(contact: AntisciaAspect) -> AntisciaContactResponse:
    return AntisciaContactResponse(
        body1=contact.body1,
        body2=contact.body2,
        aspect=contact.aspect,
        lon1=contact.lon1,
        lon2=contact.lon2,
        shadow=contact.shadow,
        orb=contact.orb,
    )


def compute_antiscia_reflection(
    request: AntisciaReflectRequest,
) -> AntisciaReflectResponse:
    requested_antiscion = request.kind in {"antiscion", "both"}
    requested_contra = request.kind in {"contra_antiscion", "both"}
    engine_entrypoint = {
        "antiscion": "antiscion",
        "contra_antiscion": "contra_antiscion",
        "both": "antiscion+contra_antiscion",
    }[request.kind]

    return AntisciaReflectResponse(
        longitude=request.longitude,
        antiscion=antiscion(request.longitude) if requested_antiscion else None,
        contra_antiscion=contra_antiscion(request.longitude) if requested_contra else None,
        normalized_range=[0.0, 360.0],
        provenance=AntisciaProvenanceResponse(
            engine_entrypoint=engine_entrypoint,
            stage_sequence=[
                "longitude_validation",
                "reflection_kind_resolution",
                "direct_reflection_computation",
                "antiscia_reflection_response_serialization",
            ],
        ),
    )


def compute_antiscia_contacts(
    request: AntisciaContactsRequest,
) -> AntisciaContactsResponse:
    contacts = [_serialize_contact(contact) for contact in find_antiscia(request.positions, request.orb)]
    return AntisciaContactsResponse(
        contacts=contacts,
        count=len(contacts),
        orb=request.orb,
        provenance=AntisciaProvenanceResponse(
            engine_entrypoint="find_antiscia",
            result_ordering="increasing_orb",
            stage_sequence=[
                "positions_validation",
                "orb_validation",
                "pair_contact_search",
                "increasing_orb_sorting",
                "antiscia_contacts_response_serialization",
            ],
        ),
    )


def compute_antiscia_to_point(
    request: AntisciaToPointRequest,
) -> AntisciaContactsResponse:
    contacts = [
        _serialize_contact(contact)
        for contact in antiscia_to_point(
            request.point_longitude,
            request.positions,
            point_name=request.point_name,
            orb=request.orb,
        )
    ]
    return AntisciaContactsResponse(
        contacts=contacts,
        count=len(contacts),
        orb=request.orb,
        provenance=AntisciaProvenanceResponse(
            engine_entrypoint="antiscia_to_point",
            result_ordering="increasing_orb",
            stage_sequence=[
                "point_longitude_validation",
                "positions_validation",
                "orb_validation",
                "point_contact_search",
                "increasing_orb_sorting",
                "antiscia_to_point_response_serialization",
            ],
        ),
    )

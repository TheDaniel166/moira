"""Service layer for admitted planetary and small-body node routes."""

from __future__ import annotations

from typing import Any

from moira import Moira
from moira.planetary_nodes import OrbitalNode, all_planetary_nodes, geometric_node, planetary_node

from ..models.nodes import (
    GeometricNodeRequest,
    MeanPlanetaryNodeRequest,
    MeanPlanetaryNodesBulkProvenanceResponse,
    MeanPlanetaryNodesBulkRequest,
    MeanPlanetaryNodesBulkResponse,
    NodeCatalogItemResponse,
    NodeCatalogProvenanceResponse,
    NodeCatalogResponse,
    NodeComputationMethod,
    NodeProvenanceResponse,
    NodeResponse,
    OrbitalNodeResponse,
)


MEAN_NODE_PLANETS = (
    "Mercury",
    "Venus",
    "Earth",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
)


def _get_reader(engine: Moira) -> Any | None:
    try:
        return engine._reader
    except Exception:
        return None


def _kernel_source(reader: Any | None) -> str:
    return "loaded_engine_reader" if reader is not None else "module_default_reader"


def _serialize_node(node: OrbitalNode) -> OrbitalNodeResponse:
    return OrbitalNodeResponse(
        body=node.planet,
        ascending_node=node.ascending_node,
        descending_node=node.descending_node,
        perihelion=node.perihelion,
        aphelion=node.aphelion,
        inclination=node.inclination,
        eccentricity=node.eccentricity,
        semi_major_axis=node.semi_major_axis,
    )


def list_node_catalog() -> NodeCatalogResponse:
    bodies = [
        NodeCatalogItemResponse(
            name=planet,
            methods=[NodeComputationMethod.mean_elements, NodeComputationMethod.geometric_osculating],
            mean_requires_kernel=False,
            geometric_requires_kernel=True,
            notes=[
                "mean_elements is kernel-free",
                "geometric_osculating requires a loaded reader",
            ],
        )
        for planet in MEAN_NODE_PLANETS
    ]
    bodies.append(
        NodeCatalogItemResponse(
            name="loaded_spk_body",
            methods=[NodeComputationMethod.geometric_osculating],
            geometric_requires_kernel=True,
            notes=[
                "geometric nodes are available only for bodies covered by the active reader",
                "Sun and Moon are not meaningful heliocentric-node targets for this route",
            ],
        )
    )
    return NodeCatalogResponse(
        bodies=bodies,
        total=len(bodies),
        provenance=NodeCatalogProvenanceResponse(
            stage_sequence=["node_method_catalog_serialization"],
        ),
    )


def compute_mean_planetary_node(request: MeanPlanetaryNodeRequest) -> NodeResponse:
    node = planetary_node(request.planet, request.jd)
    return NodeResponse(
        node=_serialize_node(node),
        provenance=NodeProvenanceResponse(
            method=NodeComputationMethod.mean_elements,
            requested_body=request.planet,
            returned_body=node.planet,
            jd=request.jd,
            jd_scale="TT_or_UT_negligible_for_slow_mean_elements",
            frame="heliocentric_tropical_ecliptic",
            coordinate_basis="Meeus_Simon_mean_orbital_elements",
            kernel_required=False,
            kernel_source="kernel_free_mean_element_table",
            validity_note=(
                "Mean element table is documented by the engine as approximately "
                "valid from 2000 BCE to 3000 CE."
            ),
            stage_sequence=[
                "jd_validation",
                "mean_planet_identity_resolution",
                "mean_element_polynomial_evaluation",
                "orbital_node_response_serialization",
            ],
        ),
    )


def compute_mean_planetary_nodes_bulk(
    request: MeanPlanetaryNodesBulkRequest,
) -> MeanPlanetaryNodesBulkResponse:
    if request.planets is None:
        nodes = all_planetary_nodes(request.jd)
        requested_planets = list(MEAN_NODE_PLANETS)
    else:
        nodes = {planet: planetary_node(planet, request.jd) for planet in request.planets}
        requested_planets = request.planets

    serialized = {name: _serialize_node(node) for name, node in nodes.items()}
    return MeanPlanetaryNodesBulkResponse(
        nodes=serialized,
        total=len(serialized),
        provenance=MeanPlanetaryNodesBulkProvenanceResponse(
            requested_planets=requested_planets,
            returned_planets=[node.body for node in serialized.values()],
            jd=request.jd,
            stage_sequence=[
                "jd_validation",
                "mean_planet_list_resolution",
                "mean_element_polynomial_evaluation",
                "orbital_node_bulk_response_serialization",
            ],
        ),
    )


def compute_geometric_node(engine: Moira, request: GeometricNodeRequest) -> NodeResponse:
    reader = _get_reader(engine)
    node = geometric_node(request.body, request.jd_ut, reader=reader)
    return NodeResponse(
        node=_serialize_node(node),
        provenance=NodeProvenanceResponse(
            method=NodeComputationMethod.geometric_osculating,
            requested_body=request.body,
            returned_body=node.planet,
            jd=request.jd_ut,
            jd_scale="UT_input_converted_to_TT_inside_engine",
            frame="heliocentric_tropical_ecliptic",
            coordinate_basis="osculating_state_vector_angular_momentum_and_eccentricity_vector",
            kernel_required=True,
            kernel_source=_kernel_source(reader),
            validity_note=(
                "Geometric nodes are instantaneous osculating elements for the "
                "requested body in the active SPK reader; loaded-body availability "
                "is determined by the reader, not by REST catalog identity."
            ),
            stage_sequence=[
                "jd_ut_validation",
                "reader_selection",
                "heliocentric_state_vector_derivation",
                "osculating_node_geometry",
                "orbital_node_response_serialization",
            ],
        ),
    )

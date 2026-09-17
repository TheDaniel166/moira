"""Service layer for admitted planetary and small-body node routes."""

from __future__ import annotations

from typing import Any

from moira import Moira
from moira.planetary_nodes import (
    OrbitalNode,
    _geometric_node_computation,
    all_planetary_nodes,
    planetary_node,
)

from ..models.nodes import (
    GeometricNodeRequest,
    GeometricNodeProvenanceResponse,
    GeometricNodeResponse,
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
from ..models.orbits import OrbitalFrameConstructionResponse
from .orbits import (
    _serialize_elements_time,
    _serialize_gravity,
    _serialize_state_source,
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
                "geometric_osculating uses the strict Sun-centered orbital core",
                "true-date geometric nodes require JD(TT) 2415020.0 through 2488070.0",
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
                "asteroid and comet geometric nodes require a receipted active-reader route",
                "body availability and exact epoch coverage come from the loaded catalog manifests",
                "true-date geometric nodes require JD(TT) 2415020.0 through 2488070.0",
                "Sun and Moon are not meaningful heliocentric-node targets for this route",
            ],
        )
    )
    return NodeCatalogResponse(
        bodies=bodies,
        total=len(bodies),
        provenance=NodeCatalogProvenanceResponse(
            stage_sequence=[
                "strict_orbital_core_policy_declaration",
                "node_method_catalog_serialization",
            ],
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


def compute_geometric_node(
    engine: Moira,
    request: GeometricNodeRequest,
) -> GeometricNodeResponse:
    reader = _get_reader(engine)
    computation = _geometric_node_computation(
        request.body,
        request.jd_ut,
        reader=reader,
    )
    node = computation.node
    elements = computation.elements
    frame = elements.provenance.frame_construction
    return GeometricNodeResponse(
        node=_serialize_node(node),
        provenance=GeometricNodeProvenanceResponse(
            method=NodeComputationMethod.geometric_osculating,
            requested_body=request.body,
            returned_body=node.planet,
            jd=request.jd_ut,
            jd_scale="UT1_JD",
            frame=elements.frame.value,
            coordinate_basis=(
                "strict_orbital_core_angular_momentum_and_eccentricity_vector"
            ),
            kernel_required=True,
            kernel_source=_kernel_source(reader),
            validity_note=(
                "Instantaneous Sun-centered osculating geometry in the true "
                "ecliptic of date. The frame is admitted only for JD(TT) "
                "2415020.0 through 2488070.0; body availability and exact "
                "coverage are determined by the receipted active reader."
            ),
            center=elements.center.value,
            body_naif_id=elements.body.naif_id,
            body_kind=elements.body.kind.value,
            time=_serialize_elements_time(elements),
            gravity=_serialize_gravity(elements.provenance.gravity),
            frame_construction=OrbitalFrameConstructionResponse(
                frame=frame.frame.value,
                routine=frame.routine,
                router_branch=frame.router_branch,
                precession_model=frame.precession_model,
                obliquity_model=frame.obliquity_model,
                nutation_model=frame.nutation_model,
                admitted_interval_tt=(
                    None
                    if elements.provenance.frame_model_interval_tt is None
                    else list(elements.provenance.frame_model_interval_tt)
                ),
            ),
            state_source=_serialize_state_source(
                elements.provenance.state_source
            ),
            singularity_policy=(
                elements.provenance.singularity_thresholds.policy
            ),
            undefined_element_policy=(
                "raise OrbitalStateDegenerateError when the unchanged "
                "OrbitalNode vessel cannot represent a required undefined field"
            ),
            stage_sequence=[
                "jd_ut_validation",
                "reader_selection",
                "strict_orbital_body_resolution",
                "ut1_tt_tdb_binding",
                "receipted_sun_centered_state_routing",
                "true_ecliptic_of_date_frame_construction",
                "strict_osculating_element_extraction",
                "orbital_node_compatibility_adaptation",
                "orbital_node_response_serialization",
            ],
        ),
    )

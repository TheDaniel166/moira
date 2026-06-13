"""Service layer for P12-03 phase, elongation, and photometry routes."""

from __future__ import annotations

import math

from moira.constants import Body
from moira.phase import (
    angular_diameter,
    apparent_magnitude,
    elongation,
    illuminated_fraction,
    phase_angle,
    synodic_phase_angle,
    synodic_phase_state,
)

from ..models.phase import (
    AngularDiameterResponse,
    ApparentMagnitudeRequest,
    ApparentMagnitudeResponse,
    ElongationResponse,
    IlluminatedFractionRequest,
    IlluminatedFractionResponse,
    PhaseAngleResponse,
    PhaseBodyRequest,
    PhaseProvenanceResponse,
    SynodicPhaseRequest,
    SynodicPhaseResponse,
)


ANGULAR_DIAMETER_BODIES = [
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
]

APPARENT_MAGNITUDE_BODIES = [
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
]

APPARENT_MAGNITUDE_EXCLUSIONS = [
    Body.SUN,
    Body.PLUTO,
    "dwarf_planets",
    "asteroids",
    "comets",
    "fixed_stars",
    "variable_stars",
]

_MAGNITUDE_MODEL_DETAILS = {
    Body.MOON: (
        "Schaefer_1993_moon_phase_law",
        "Schaefer_1993",
        [
            "Approximate lunar phase law.",
            "No opposition surge correction.",
            "No eclipse darkening correction.",
        ],
    ),
    Body.MERCURY: (
        "Mallama_Hilton_2018_Mercury_phase_polynomial",
        "Mallama_Hilton_2018",
        ["Geocentric modern Mercury phase polynomial."],
    ),
    Body.VENUS: (
        "Mallama_Hilton_2018_Venus_piecewise_phase_polynomial",
        "Mallama_Hilton_2018",
        ["Geocentric Venus phase treatment with large-crescent branch."],
    ),
    Body.MARS: (
        "Mallama_Hilton_2018_Mars_with_rotational_orbital_terms",
        "Mallama_Hilton_2018",
        ["Includes Mars rotational and orbital brightness corrections."],
    ),
    Body.JUPITER: (
        "Mallama_Hilton_2018_Jupiter_low_phase_polynomial",
        "Mallama_Hilton_2018",
        ["Earth-based small-phase-angle Jupiter treatment."],
    ),
    Body.SATURN: (
        "Mallama_Hilton_2018_Saturn_ring_aware_or_globe_fallback",
        "Mallama_Hilton_2018",
        [
            "Ring-aware branch is used only inside admitted validity conditions.",
            "Falls back to globe-only treatment outside ring branch conditions.",
        ],
    ),
    Body.URANUS: (
        "Mallama_Hilton_2018_Uranus_planetographic_sub_latitude",
        "Mallama_Hilton_2018",
        ["Includes effective planetographic sub-latitude term."],
    ),
    Body.NEPTUNE: (
        "Mallama_Hilton_2018_Neptune_time_dependent_phase_branch",
        "Mallama_Hilton_2018",
        ["Includes time-dependent geocentric V(1,0) and post-2000 phase branch."],
    ),
}


def _assert_finite_result(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} result must be finite")
    return value


def _validate_supported_body(body: str, supported: list[str], product: str) -> None:
    if body not in supported:
        valid = ", ".join(supported)
        raise ValueError(f"{product} does not support body {body!r}. Supported bodies: {valid}")


def compute_illuminated_fraction(
    request: IlluminatedFractionRequest,
) -> IlluminatedFractionResponse:
    fraction = _assert_finite_result(
        "illuminated_fraction",
        illuminated_fraction(request.phase_angle),
    )
    return IlluminatedFractionResponse(
        phase_angle=request.phase_angle,
        illuminated_fraction=fraction,
        range=[0.0, 1.0],
        provenance=PhaseProvenanceResponse(
            engine_entrypoint="illuminated_fraction",
            product="illuminated_fraction",
            basis="k = (1 + cos(phase_angle)) / 2",
            support_set=["finite_phase_angle"],
            kernel_required=False,
            stage_sequence=[
                "phase_angle_validation",
                "scalar_illumination_formula",
                "illuminated_fraction_response_serialization",
            ],
        ),
    )


def compute_synodic_phase(request: SynodicPhaseRequest) -> SynodicPhaseResponse:
    angle = _assert_finite_result(
        "synodic_phase_angle",
        synodic_phase_angle(request.body1, request.body2, request.jd_ut),
    )
    state = synodic_phase_state(angle) if request.include_state else None
    return SynodicPhaseResponse(
        body1=request.body1,
        body2=request.body2,
        jd_ut=request.jd_ut,
        angle=angle,
        state=state,
        angle_range=[0.0, 360.0],
        state_policy="quadrant_labels_with_45_degree_boundaries",
        provenance=PhaseProvenanceResponse(
            engine_entrypoint="synodic_phase_angle",
            product="synodic",
            requested_body1=request.body1,
            requested_body2=request.body2,
            jd_ut=request.jd_ut,
            basis="forward_ecliptic_longitude_difference_body1_to_body2",
            support_set=["bodies_resolvable_by_planet_at"],
            kernel_required=True,
            coordinate_frame="geocentric_ecliptic_longitude",
            stage_sequence=[
                "body_pair_validation",
                "jd_ut_validation",
                "planet_at_ecliptic_lookup",
                "synodic_phase_angle_computation",
                "synodic_phase_response_serialization",
            ],
        ),
    )


def compute_elongation(request: PhaseBodyRequest) -> ElongationResponse:
    value = _assert_finite_result("elongation", elongation(request.body, request.jd_ut))
    return ElongationResponse(
        body=request.body,
        jd_ut=request.jd_ut,
        elongation=value,
        angle_range=[0.0, 180.0],
        basis="geocentric_ecliptic_spherical_law_of_cosines",
        provenance=PhaseProvenanceResponse(
            engine_entrypoint="elongation",
            product="elongation",
            requested_body=request.body,
            jd_ut=request.jd_ut,
            basis="geocentric_ecliptic_spherical_law_of_cosines",
            support_set=["bodies_resolvable_by_planet_at"],
            kernel_required=True,
            coordinate_frame="geocentric_ecliptic_longitude_latitude",
            stage_sequence=[
                "body_validation",
                "jd_ut_validation",
                "planet_at_ecliptic_lookup",
                "elongation_computation",
                "elongation_response_serialization",
            ],
        ),
    )


def compute_phase_angle(request: PhaseBodyRequest) -> PhaseAngleResponse:
    value = _assert_finite_result("phase_angle", phase_angle(request.body, request.jd_ut))
    return PhaseAngleResponse(
        body=request.body,
        jd_ut=request.jd_ut,
        phase_angle=value,
        angle_range=[0.0, 180.0],
        basis="Sun_body_Earth_vector_angle",
        provenance=PhaseProvenanceResponse(
            engine_entrypoint="phase_angle",
            product="phase_angle",
            requested_body=request.body,
            jd_ut=request.jd_ut,
            basis="Sun_body_Earth_vector_angle",
            support_set=["bodies_resolvable_by_barycentric_reader"],
            kernel_required=True,
            coordinate_frame="ICRF_barycentric_vectors",
            stage_sequence=[
                "body_validation",
                "jd_ut_validation",
                "barycentric_vector_lookup",
                "sun_body_earth_phase_angle_computation",
                "phase_angle_response_serialization",
            ],
        ),
    )


def compute_angular_diameter(request: PhaseBodyRequest) -> AngularDiameterResponse:
    _validate_supported_body(
        request.body,
        ANGULAR_DIAMETER_BODIES,
        "angular_diameter",
    )
    value = _assert_finite_result(
        "angular_diameter",
        angular_diameter(request.body, request.jd_ut),
    )
    return AngularDiameterResponse(
        body=request.body,
        jd_ut=request.jd_ut,
        angular_diameter_arcseconds=value,
        radius_source="moira.phase physical radius table",
        distance_basis="planet_at geocentric distance in kilometers",
        provenance=PhaseProvenanceResponse(
            engine_entrypoint="angular_diameter",
            product="angular_diameter",
            requested_body=request.body,
            jd_ut=request.jd_ut,
            basis="2 * atan(physical_radius_km / geocentric_distance_km)",
            support_set=ANGULAR_DIAMETER_BODIES,
            kernel_required=True,
            coordinate_frame="geocentric_distance_from_planet_at",
            stage_sequence=[
                "body_validation",
                "angular_diameter_support_set_validation",
                "jd_ut_validation",
                "planet_at_distance_lookup",
                "angular_diameter_computation",
                "angular_diameter_response_serialization",
            ],
        ),
    )


def compute_apparent_magnitude(
    request: ApparentMagnitudeRequest,
) -> ApparentMagnitudeResponse:
    _validate_supported_body(
        request.body,
        APPARENT_MAGNITUDE_BODIES,
        "apparent_magnitude",
    )
    value = _assert_finite_result(
        "apparent_magnitude",
        apparent_magnitude(request.body, request.jd_ut),
    )
    model_name, model_family, limitations = _MAGNITUDE_MODEL_DETAILS[request.body]
    return ApparentMagnitudeResponse(
        body=request.body,
        jd_ut=request.jd_ut,
        apparent_magnitude=value,
        model_name=model_name if request.include_model_detail else None,
        model_family=model_family if request.include_model_detail else None,
        model_limitations=limitations if request.include_model_detail else None,
        provenance=PhaseProvenanceResponse(
            engine_entrypoint="apparent_magnitude",
            product="apparent_magnitude",
            requested_body=request.body,
            jd_ut=request.jd_ut,
            basis="body_specific_phase_distance_visual_magnitude_model",
            support_set=APPARENT_MAGNITUDE_BODIES,
            kernel_required=True,
            coordinate_frame="ICRF_barycentric_vectors",
            model_family=model_family,
            unsupported_exclusions=APPARENT_MAGNITUDE_EXCLUSIONS,
            stage_sequence=[
                "body_validation",
                "apparent_magnitude_support_set_validation",
                "jd_ut_validation",
                "barycentric_vector_lookup",
                "body_specific_magnitude_model",
                "apparent_magnitude_response_serialization",
            ],
        ),
    )

"""Frame-explicit house-boundary geometry covenants."""

from __future__ import annotations

import math

import pytest

from moira.constants import HouseSystem
from moira.houses import (
    HouseBoundaryGeometryAvailability,
    HouseBoundaryGeometryKind,
    houses_from_armc,
)


def _norm(vector: tuple[float, float, float]) -> float:
    return math.sqrt(sum(component * component for component in vector))


def test_boundary_geometry_is_explicitly_opt_in() -> None:
    houses = houses_from_armc(123.0, 23.4393, 35.0, HouseSystem.CAMPANUS)

    assert houses.boundary_geometry is None


@pytest.mark.parametrize(
    "system",
    (
        HouseSystem.CAMPANUS,
        HouseSystem.AZIMUTHAL,
        HouseSystem.REGIOMONTANUS,
        HouseSystem.TOPOCENTRIC,
        HouseSystem.KOCH,
        HouseSystem.ALCABITIUS,
    ),
)
def test_plane_defined_families_publish_twelve_exact_boundaries(system: str) -> None:
    houses = houses_from_armc(
        123.0,
        23.4393,
        35.0,
        system,
        include_boundary_geometry=True,
    )
    geometry = houses.boundary_geometry

    assert geometry is not None
    assert geometry.effective_system == system
    assert geometry.availability == HouseBoundaryGeometryAvailability.COMPLETE
    assert geometry.frame == "true_equator_and_equinox_of_date"
    assert tuple(boundary.house for boundary in geometry.boundaries) == tuple(range(1, 13))

    for boundary, cusp in zip(geometry.boundaries, houses.cusps, strict=True):
        assert boundary.kind == HouseBoundaryGeometryKind.GREAT_CIRCLE_PLANE
        assert boundary.cusp_longitude == pytest.approx(cusp, abs=1e-12)
        assert boundary.plane_normal is not None
        assert _norm(boundary.plane_normal) == pytest.approx(1.0, abs=1e-12)
        assert _norm(boundary.anchor_direction) == pytest.approx(1.0, abs=1e-12)
        assert sum(
            normal * anchor
            for normal, anchor in zip(
                boundary.plane_normal,
                boundary.anchor_direction,
                strict=True,
            )
        ) == pytest.approx(0.0, abs=1e-8)


def test_placidus_publishes_cardinal_planes_and_semi_arc_event_curves() -> None:
    latitude_deg = 51.5
    houses = houses_from_armc(
        123.0,
        23.4393,
        latitude_deg,
        HouseSystem.PLACIDUS,
        include_boundary_geometry=True,
    )
    geometry = houses.boundary_geometry

    assert geometry is not None
    assert geometry.availability == HouseBoundaryGeometryAvailability.COMPLETE
    assert {
        boundary.house
        for boundary in geometry.boundaries
        if boundary.kind == HouseBoundaryGeometryKind.GREAT_CIRCLE_PLANE
    } == {1, 4, 7, 10}
    assert {
        boundary.house
        for boundary in geometry.boundaries
        if boundary.kind == HouseBoundaryGeometryKind.SEMI_ARC_EVENT_CURVE
    } == {2, 3, 5, 6, 8, 9, 11, 12}

    for boundary in geometry.boundaries:
        if not boundary.event_phase or boundary.event_phase.startswith("antipodal_"):
            continue
        assert boundary.event_fraction is not None
        for point in boundary.curve_points:
            declination_rad = math.radians(point.declination_deg)
            argument = -math.tan(math.radians(latitude_deg)) * math.tan(declination_rad)
            dsa_deg = math.degrees(math.acos(max(-1.0, min(1.0, argument))))
            if boundary.event_phase == "upper":
                expected_ra = houses.armc + boundary.event_fraction * dsa_deg
            else:
                expected_ra = (
                    houses.armc
                    + 180.0
                    - boundary.event_fraction * (180.0 - dsa_deg)
                )
            residual = (
                point.right_ascension_deg - expected_ra + 180.0
            ) % 360.0 - 180.0
            assert residual == pytest.approx(0.0, abs=1e-10)
        assert any(
            point.direction == pytest.approx(boundary.anchor_direction, abs=1e-12)
            for point in boundary.curve_points
        )


@pytest.mark.parametrize("latitude_deg", (-51.5, 77.0))
def test_placidus_event_curves_remain_governing_geometry_off_the_nominal_case(
    latitude_deg: float,
) -> None:
    armc_deg = 90.0 if latitude_deg == 77.0 else 237.0
    houses = houses_from_armc(
        armc_deg,
        23.4393,
        latitude_deg,
        HouseSystem.PLACIDUS,
        include_boundary_geometry=True,
    )
    geometry = houses.boundary_geometry

    assert geometry is not None
    assert geometry.availability == HouseBoundaryGeometryAvailability.COMPLETE
    for boundary in geometry.boundaries:
        if (
            boundary.kind != HouseBoundaryGeometryKind.SEMI_ARC_EVENT_CURVE
            or not boundary.event_phase
            or boundary.event_phase.startswith("antipodal_")
        ):
            continue
        assert boundary.event_fraction is not None
        anchor = min(
            boundary.curve_points,
            key=lambda point: sum(
                (component - anchor_component) ** 2
                for component, anchor_component in zip(
                    point.direction,
                    boundary.anchor_direction,
                    strict=True,
                )
            ),
        )
        argument = max(
            -1.0,
            min(
                1.0,
                -math.tan(math.radians(latitude_deg))
                * math.tan(math.radians(anchor.declination_deg)),
            ),
        )
        dsa_deg = math.degrees(math.acos(argument))
        expected_ra = (
            houses.armc + boundary.event_fraction * dsa_deg
            if boundary.event_phase == "upper"
            else houses.armc
            + 180.0
            - boundary.event_fraction * (180.0 - dsa_deg)
        )
        residual = (anchor.right_ascension_deg - expected_ra + 180.0) % 360.0 - 180.0
        assert residual == pytest.approx(0.0, abs=1e-8)
        assert anchor.direction == pytest.approx(boundary.anchor_direction, abs=1e-12)


def test_fallback_geometry_describes_the_effective_system_not_the_request() -> None:
    houses = houses_from_armc(
        123.0,
        23.4393,
        80.0,
        HouseSystem.CAMPANUS,
        include_boundary_geometry=True,
    )
    geometry = houses.boundary_geometry

    assert houses.effective_system == HouseSystem.PORPHYRY
    assert geometry is not None
    assert geometry.effective_system == HouseSystem.PORPHYRY
    assert geometry.availability == HouseBoundaryGeometryAvailability.CUSP_INTERSECTIONS_ONLY
    assert geometry.boundaries == ()
    assert geometry.reason is not None


def test_sidereal_offset_changes_labels_without_rotating_physical_boundaries() -> None:
    tropical = houses_from_armc(
        123.0,
        23.4393,
        35.0,
        HouseSystem.CAMPANUS,
        include_boundary_geometry=True,
    )
    sidereal = houses_from_armc(
        123.0,
        23.4393,
        35.0,
        HouseSystem.CAMPANUS,
        ayanamsa_offset=24.0,
        include_boundary_geometry=True,
    )

    assert tropical.boundary_geometry is not None
    assert sidereal.boundary_geometry is not None
    assert sidereal.boundary_geometry.zodiac_offset_deg == pytest.approx(24.0)
    for tropical_boundary, sidereal_boundary in zip(
        tropical.boundary_geometry.boundaries,
        sidereal.boundary_geometry.boundaries,
        strict=True,
    ):
        assert sidereal_boundary.cusp_longitude == pytest.approx(
            (tropical_boundary.cusp_longitude - 24.0) % 360.0,
            abs=1e-12,
        )
        assert sidereal_boundary.anchor_direction == pytest.approx(
            tropical_boundary.anchor_direction,
            abs=1e-12,
        )
        assert sidereal_boundary.plane_normal == pytest.approx(
            tropical_boundary.plane_normal,
            abs=1e-12,
        )


@pytest.mark.parametrize(
    "system",
    (HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL, HouseSystem.PORPHYRY),
)
def test_cusp_only_systems_fail_closed_instead_of_inventing_spatial_walls(
    system: str,
) -> None:
    houses = houses_from_armc(
        123.0,
        23.4393,
        35.0,
        system,
        include_boundary_geometry=True,
    )
    geometry = houses.boundary_geometry

    assert geometry is not None
    assert geometry.effective_system == system
    assert geometry.availability == HouseBoundaryGeometryAvailability.CUSP_INTERSECTIONS_ONLY
    assert geometry.boundaries == ()
    assert geometry.reason is not None

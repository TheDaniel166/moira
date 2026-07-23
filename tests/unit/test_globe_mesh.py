from __future__ import annotations

from collections import Counter

import pytest

from moira._globe_mesh import (
    build_icosphere,
    edge_angle_deg,
    extract_contour_components,
    mesh_edges,
    refine_mesh_edges,
    spherical_midpoint,
    split_antimeridian_component,
)


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_icosphere_is_closed_deterministic_and_has_expected_counts(
    depth: int,
) -> None:
    mesh = build_icosphere(depth)
    repeated = build_icosphere(depth)
    assert mesh == repeated
    assert len(mesh.vertices) == 10 * (4**depth) + 2
    assert len(mesh.triangles) == 20 * (4**depth)
    edges = Counter()
    for triangle in mesh.triangles:
        a, b, c = triangle.vertices
        for left, right in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((left, right)))] += 1
    assert set(edges.values()) == {2}


def test_spherical_contour_is_closed_without_polar_or_antimeridian_repairs() -> None:
    mesh = build_icosphere(2)
    values = tuple(vertex.xyz[2] for vertex in mesh.vertices)
    components = extract_contour_components(mesh, values, 0.1)
    assert len(components) == 1
    component = components[0]
    assert component.closed is True
    assert component.points[0] == component.points[-1]
    assert len(component.points) > 20
    assert all(-90.0 <= latitude <= 90.0 for latitude, _ in component.points)
    assert all(-180.0 <= longitude <= 180.0 for _, longitude in component.points)


def test_selected_edge_refinement_remains_closed_and_local() -> None:
    mesh = build_icosphere(0)
    edge = mesh_edges(mesh)[0]
    refined = refine_mesh_edges(mesh, (edge,))
    repeated = refine_mesh_edges(mesh, (edge,))
    assert refined == repeated
    assert len(refined.vertices) == len(mesh.vertices) + 1
    assert len(refined.triangles) == len(mesh.triangles) + 2
    counts = Counter()
    for triangle in refined.triangles:
        a, b, c = triangle.vertices
        for left, right in ((a, b), (b, c), (c, a)):
            counts[tuple(sorted((left, right)))] += 1
    assert set(counts.values()) == {2}
    midpoint = spherical_midpoint(mesh.vertices[edge[0]], mesh.vertices[edge[1]])
    assert refined.vertices[-1].xyz == pytest.approx(midpoint.xyz)
    assert edge_angle_deg(mesh.vertices[edge[0]], refined.vertices[-1]) == (
        pytest.approx(
            edge_angle_deg(mesh.vertices[edge[0]], mesh.vertices[edge[1]]) / 2.0
        )
    )


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_exact_threshold_vertices_form_one_closed_component(depth: int) -> None:
    mesh = build_icosphere(depth)
    values = tuple(vertex.xyz[2] for vertex in mesh.vertices)
    components = extract_contour_components(mesh, values, 0.0)
    assert len(components) == 1
    assert components[0].closed is True
    assert components[0].points[0] == components[0].points[-1]
    assert all(latitude == pytest.approx(0.0) for latitude, _ in components[0].points)


def test_antimeridian_split_preserves_component_identity_without_map_spans() -> None:
    mesh = build_icosphere(2)
    values = tuple(vertex.xyz[2] for vertex in mesh.vertices)
    component = extract_contour_components(mesh, values, 0.0)[0]
    segments = split_antimeridian_component(component)
    assert segments
    assert all(segment.closed is False for segment in segments)
    assert all(
        abs(right[1] - left[1]) <= 180.0
        for segment in segments
        for left, right in zip(segment.points, segment.points[1:])
    )
    seam_endpoints = [
        point
        for segment in segments
        for point in (segment.points[0], segment.points[-1])
        if abs(point[1]) == 180.0
    ]
    assert len(seam_endpoints) == 2 * len(segments)


def test_contour_extraction_rejects_mismatched_or_nonfinite_fields() -> None:
    mesh = build_icosphere(0)
    with pytest.raises(ValueError, match="one scalar"):
        extract_contour_components(mesh, (0.0,), 0.5)
    values = tuple(0.0 for _ in mesh.vertices)
    with pytest.raises(ValueError, match="threshold"):
        extract_contour_components(mesh, values, float("nan"))

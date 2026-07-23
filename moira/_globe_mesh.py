"""Deterministic, dependency-free spherical triangulation and contours."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GlobeVertex:
    """Vessel: Structured globe vertex data."""
    index: int
    xyz: tuple[float, float, float]
    latitude_deg: float
    longitude_deg: float


@dataclass(frozen=True, slots=True)
class GlobeTriangle:
    """Vessel: Structured globe triangle data."""
    vertices: tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class GlobeMesh:
    """Vessel: Structured globe mesh data."""
    vertices: tuple[GlobeVertex, ...]
    triangles: tuple[GlobeTriangle, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class GlobeContourComponent:
    """Vessel: Structured globe contour component data."""
    points: tuple[tuple[float, float], ...]
    closed: bool


def mesh_edges(mesh: GlobeMesh) -> tuple[tuple[int, int], ...]:
    return tuple(
        sorted(
            {
                tuple(sorted((left, right)))
                for triangle in mesh.triangles
                for left, right in (
                    (triangle.vertices[0], triangle.vertices[1]),
                    (triangle.vertices[1], triangle.vertices[2]),
                    (triangle.vertices[2], triangle.vertices[0]),
                )
            }
        )
    )


def spherical_midpoint(
    left: GlobeVertex,
    right: GlobeVertex,
    *,
    index: int = -1,
) -> GlobeVertex:
    return _vertex(
        index,
        tuple(left.xyz[axis] + right.xyz[axis] for axis in range(3)),
    )


def edge_angle_deg(left: GlobeVertex, right: GlobeVertex) -> float:
    dot = sum(left.xyz[axis] * right.xyz[axis] for axis in range(3))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def refine_mesh_edges(
    mesh: GlobeMesh,
    edges,
) -> GlobeMesh:
    """Conformingly bisect selected shared edges of a spherical mesh."""

    selected = {
        tuple(sorted(edge))
        for edge in edges
    }
    lawful_edges = set(mesh_edges(mesh))
    if not selected <= lawful_edges:
        raise ValueError("refinement edges must belong to the mesh")
    if not selected:
        return mesh

    vertices = list(mesh.vertices)
    midpoint_indices: dict[tuple[int, int], int] = {}
    for edge in sorted(selected):
        index = len(vertices)
        midpoint_indices[edge] = index
        vertices.append(
            spherical_midpoint(
                mesh.vertices[edge[0]],
                mesh.vertices[edge[1]],
                index=index,
            )
        )

    triangles: list[GlobeTriangle] = []
    for triangle in mesh.triangles:
        a, b, c = triangle.vertices
        ab_edge = tuple(sorted((a, b)))
        bc_edge = tuple(sorted((b, c)))
        ca_edge = tuple(sorted((c, a)))
        ab = midpoint_indices.get(ab_edge)
        bc = midpoint_indices.get(bc_edge)
        ca = midpoint_indices.get(ca_edge)
        split_count = sum(index is not None for index in (ab, bc, ca))
        if split_count == 0:
            triangles.append(triangle)
        elif split_count == 1:
            if ab is not None:
                triangles.extend(
                    (GlobeTriangle((a, ab, c)), GlobeTriangle((ab, b, c)))
                )
            elif bc is not None:
                triangles.extend(
                    (GlobeTriangle((b, bc, a)), GlobeTriangle((bc, c, a)))
                )
            else:
                assert ca is not None
                triangles.extend(
                    (GlobeTriangle((c, ca, b)), GlobeTriangle((ca, a, b)))
                )
        elif split_count == 2:
            if ab is not None and bc is not None:
                triangles.extend(
                    (
                        GlobeTriangle((b, bc, ab)),
                        GlobeTriangle((a, ab, bc)),
                        GlobeTriangle((a, bc, c)),
                    )
                )
            elif bc is not None and ca is not None:
                triangles.extend(
                    (
                        GlobeTriangle((c, ca, bc)),
                        GlobeTriangle((a, b, bc)),
                        GlobeTriangle((a, bc, ca)),
                    )
                )
            else:
                assert ca is not None and ab is not None
                triangles.extend(
                    (
                        GlobeTriangle((a, ab, ca)),
                        GlobeTriangle((b, c, ca)),
                        GlobeTriangle((b, ca, ab)),
                    )
                )
        else:
            assert ab is not None and bc is not None and ca is not None
            triangles.extend(
                (
                    GlobeTriangle((a, ab, ca)),
                    GlobeTriangle((b, bc, ab)),
                    GlobeTriangle((c, ca, bc)),
                    GlobeTriangle((ab, bc, ca)),
                )
            )
    return GlobeMesh(
        vertices=tuple(vertices),
        triangles=tuple(triangles),
        depth=mesh.depth + 1,
    )


def split_antimeridian_component(
    component: GlobeContourComponent,
) -> tuple[GlobeContourComponent, ...]:
    """Split a spherical contour into projection-safe longitude segments."""

    points = component.points
    if len(points) < 2:
        raise ValueError("contour component requires at least two points")
    segments: list[list[tuple[float, float]]] = []
    current = [points[0]]
    for left, right in zip(points, points[1:]):
        left_latitude, left_longitude = left
        right_latitude, right_longitude = right
        longitude_jump = right_longitude - left_longitude
        if abs(longitude_jump) <= 180.0:
            current.append(right)
            continue

        right_unwrapped = (
            right_longitude + 360.0
            if longitude_jump < -180.0
            else right_longitude - 360.0
        )
        seam_longitude = 180.0 if left_longitude > 0.0 else -180.0
        fraction = (seam_longitude - left_longitude) / (
            right_unwrapped - left_longitude
        )

        def xyz(latitude_deg: float, longitude_deg: float):
            latitude = math.radians(latitude_deg)
            longitude = math.radians(longitude_deg)
            cos_latitude = math.cos(latitude)
            return (
                cos_latitude * math.cos(longitude),
                cos_latitude * math.sin(longitude),
                math.sin(latitude),
            )

        left_xyz = xyz(left_latitude, left_longitude)
        right_xyz = xyz(right_latitude, right_longitude)
        crossing_xyz = _unit(
            tuple(
                left_xyz[axis] * (1.0 - fraction)
                + right_xyz[axis] * fraction
                for axis in range(3)
            )
        )
        crossing_latitude = math.degrees(
            math.asin(max(-1.0, min(1.0, crossing_xyz[2])))
        )
        current.append((crossing_latitude, seam_longitude))
        segments.append(current)
        current = [(crossing_latitude, -seam_longitude), right]
    segments.append(current)

    if len(segments) == 1:
        return (component,)
    if component.closed and points[0] == points[-1]:
        merged = [*segments[-1][:-1], *segments[0]]
        segments = [merged, *segments[1:-1]]
    result = []
    for segment in segments:
        unique = [segment[0]]
        for point in segment[1:]:
            if point != unique[-1]:
                unique.append(point)
        if len(unique) >= 2:
            result.append(
                GlobeContourComponent(points=tuple(unique), closed=False)
            )
    return tuple(result)


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(norm) or norm == 0.0:
        raise ValueError("spherical vertex must have finite non-zero norm")
    return tuple(value / norm for value in vector)


def _vertex(index: int, xyz: tuple[float, float, float]) -> GlobeVertex:
    x, y, z = _unit(xyz)
    return GlobeVertex(
        index=index,
        xyz=(x, y, z),
        latitude_deg=math.degrees(math.asin(max(-1.0, min(1.0, z)))),
        longitude_deg=math.degrees(math.atan2(y, x)),
    )


def build_icosphere(depth: int = 0) -> GlobeMesh:
    """Return a closed icosphere after ``depth`` uniform subdivisions."""

    if isinstance(depth, bool) or not isinstance(depth, int):
        raise TypeError("depth must be an integer")
    if not 0 <= depth <= 6:
        raise ValueError("depth must be between 0 and 6")
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    base = (
        (-1.0, phi, 0.0),
        (1.0, phi, 0.0),
        (-1.0, -phi, 0.0),
        (1.0, -phi, 0.0),
        (0.0, -1.0, phi),
        (0.0, 1.0, phi),
        (0.0, -1.0, -phi),
        (0.0, 1.0, -phi),
        (phi, 0.0, -1.0),
        (phi, 0.0, 1.0),
        (-phi, 0.0, -1.0),
        (-phi, 0.0, 1.0),
    )
    faces = [
        (0, 11, 5),
        (0, 5, 1),
        (0, 1, 7),
        (0, 7, 10),
        (0, 10, 11),
        (1, 5, 9),
        (5, 11, 4),
        (11, 10, 2),
        (10, 7, 6),
        (7, 1, 8),
        (3, 9, 4),
        (3, 4, 2),
        (3, 2, 6),
        (3, 6, 8),
        (3, 8, 9),
        (4, 9, 5),
        (2, 4, 11),
        (6, 2, 10),
        (8, 6, 7),
        (9, 8, 1),
    ]
    xyz_values = [_unit(value) for value in base]
    for _ in range(depth):
        midpoint_cache: dict[tuple[int, int], int] = {}

        def midpoint(left: int, right: int) -> int:
            edge = (left, right) if left < right else (right, left)
            cached = midpoint_cache.get(edge)
            if cached is not None:
                return cached
            point = _unit(
                tuple(
                    xyz_values[left][axis] + xyz_values[right][axis]
                    for axis in range(3)
                )
            )
            index = len(xyz_values)
            xyz_values.append(point)
            midpoint_cache[edge] = index
            return index

        refined: list[tuple[int, int, int]] = []
        for a, b, c in faces:
            ab = midpoint(a, b)
            bc = midpoint(b, c)
            ca = midpoint(c, a)
            refined.extend(
                (
                    (a, ab, ca),
                    (b, bc, ab),
                    (c, ca, bc),
                    (ab, bc, ca),
                )
            )
        faces = refined
    return GlobeMesh(
        vertices=tuple(_vertex(index, xyz) for index, xyz in enumerate(xyz_values)),
        triangles=tuple(GlobeTriangle(face) for face in faces),
        depth=depth,
    )


def _spherical_interpolation(
    left: GlobeVertex,
    right: GlobeVertex,
    fraction: float,
) -> tuple[float, float]:
    xyz = _unit(
        tuple(
            left.xyz[axis] * (1.0 - fraction)
            + right.xyz[axis] * fraction
            for axis in range(3)
        )
    )
    latitude = math.degrees(math.asin(max(-1.0, min(1.0, xyz[2]))))
    longitude = math.degrees(math.atan2(xyz[1], xyz[0]))
    return latitude, longitude


def extract_contour_components(
    mesh: GlobeMesh,
    values: tuple[float, ...],
    threshold: float,
) -> tuple[GlobeContourComponent, ...]:
    """Extract closed marching-triangle contours from one scalar field."""

    if len(values) != len(mesh.vertices):
        raise ValueError("values must contain one scalar per mesh vertex")
    if not math.isfinite(threshold):
        raise ValueError("threshold must be finite")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("contour values must be finite")

    node_key = tuple[str, int, int]
    segments_by_nodes: dict[
        tuple[node_key, node_key],
        tuple[
            node_key,
            tuple[float, float],
            node_key,
            tuple[float, float],
        ]
    ] = {}
    for triangle in mesh.triangles:
        crossings: list[tuple[node_key, tuple[float, float]]] = []
        a, b, c = triangle.vertices
        for left_index, right_index in ((a, b), (b, c), (c, a)):
            left_value = values[left_index] - threshold
            right_value = values[right_index] - threshold
            # Treat exact-threshold vertices as the positive side, but retain
            # their exact interpolation point.  This symbolic perturbation
            # makes vertex/edge coincidences deterministic without changing
            # the scalar field by a numerical epsilon.
            left_sign = 1 if left_value == 0.0 else (-1 if left_value < 0.0 else 1)
            right_sign = (
                1 if right_value == 0.0 else (-1 if right_value < 0.0 else 1)
            )
            if left_sign == right_sign:
                continue
            denominator = values[right_index] - values[left_index]
            if denominator == 0.0:
                continue
            fraction = (threshold - values[left_index]) / denominator
            if not 0.0 <= fraction <= 1.0:
                continue
            if fraction == 0.0:
                identity: node_key = ("vertex", left_index, -1)
            elif fraction == 1.0:
                identity = ("vertex", right_index, -1)
            else:
                edge = (
                    (left_index, right_index)
                    if left_index < right_index
                    else (right_index, left_index)
                )
                identity = ("edge", edge[0], edge[1])
            crossings.append(
                (
                    identity,
                    _spherical_interpolation(
                        mesh.vertices[left_index],
                        mesh.vertices[right_index],
                        fraction,
                    ),
                )
            )
        unique = {identity: point for identity, point in crossings}
        if len(unique) == 2:
            (first_node, first_point), (last_node, last_point) = unique.items()
            segment_identity = (
                (first_node, last_node)
                if first_node < last_node
                else (last_node, first_node)
            )
            segments_by_nodes.setdefault(
                segment_identity,
                (first_node, first_point, last_node, last_point),
            )

    segments = list(segments_by_nodes.values())
    if not segments:
        return ()
    adjacency: dict[node_key, list[int]] = {}
    for index, segment in enumerate(segments):
        adjacency.setdefault(segment[0], []).append(index)
        adjacency.setdefault(segment[2], []).append(index)

    unused = set(range(len(segments)))
    components: list[GlobeContourComponent] = []
    while unused:
        first_index = min(unused)
        first = segments[first_index]
        unused.remove(first_index)
        start_edge = first[0]
        current_edge = first[2]
        points = [first[1], first[3]]
        closed = current_edge == start_edge
        while not closed:
            candidates = [
                index
                for index in adjacency.get(current_edge, ())
                if index in unused
            ]
            if not candidates:
                break
            next_index = min(candidates)
            unused.remove(next_index)
            segment = segments[next_index]
            if segment[0] == current_edge:
                current_edge = segment[2]
                points.append(segment[3])
            else:
                current_edge = segment[0]
                points.append(segment[1])
            closed = current_edge == start_edge
        if closed and points[-1] != points[0]:
            points.append(points[0])
        components.append(
            GlobeContourComponent(points=tuple(points), closed=closed)
        )
    return tuple(components)

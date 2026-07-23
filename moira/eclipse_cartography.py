"""NumPy-free solar eclipse magnitude and obscuration cartography."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from numbers import Real
from typing import TYPE_CHECKING

from ._eclipse_solar_geometry import (
    _SolarApparentDiscGeometry,
    _topocentric_solar_disc_geometry,
)
from ._globe_mesh import (
    build_icosphere,
    edge_angle_deg,
    extract_contour_components,
    mesh_edges,
    refine_mesh_edges,
    spherical_midpoint,
    split_antimeridian_component,
)

if TYPE_CHECKING:
    from .eclipse import EclipseCalculator
    from .solar_eclipse_global import SolarEclipseGlobalCircumstances

__all__ = [
    "SolarEclipseMapSample",
    "EclipseContourComponent",
    "EclipseContourLevel",
    "SolarEclipseCartography",
]


@dataclass(frozen=True, slots=True)
class SolarEclipseMapSample:
    """Vessel: Structured solar eclipse map sample data."""
    latitude_deg: float
    longitude_deg: float
    visible: bool
    magnitude: float
    magnitude_jd_ut1: float | None
    obscuration: float
    obscuration_jd_ut1: float | None
    local_class: str
    sun_altitude_deg: float | None

    def __post_init__(self) -> None:
        if not -90.0 <= _finite("latitude_deg", self.latitude_deg) <= 90.0:
            raise ValueError("latitude_deg must be in [-90, 90]")
        if not -180.0 <= _finite("longitude_deg", self.longitude_deg) <= 180.0:
            raise ValueError("longitude_deg must be in [-180, 180]")
        if not isinstance(self.visible, bool):
            raise TypeError("visible must be a boolean")
        magnitude = _finite("magnitude", self.magnitude)
        obscuration = _finite("obscuration", self.obscuration)
        if magnitude < 0.0:
            raise ValueError("magnitude must be non-negative")
        if not 0.0 <= obscuration <= 1.0:
            raise ValueError("obscuration must be in [0, 1]")
        if self.local_class not in {"none", "partial", "annular", "total"}:
            raise ValueError("invalid local eclipse class")
        if self.visible:
            if self.magnitude_jd_ut1 is None or self.obscuration_jd_ut1 is None:
                raise ValueError("visible samples require both maximum epochs")
            _finite("magnitude_jd_ut1", self.magnitude_jd_ut1)
            _finite("obscuration_jd_ut1", self.obscuration_jd_ut1)
            if self.sun_altitude_deg is None:
                raise ValueError("visible samples require Sun altitude")
            altitude = _finite("sun_altitude_deg", self.sun_altitude_deg)
            if not 0.0 <= altitude <= 90.0:
                raise ValueError("visible sample Sun altitude must be in [0, 90]")
            if self.local_class == "none" or magnitude <= 0.0:
                raise ValueError("visible samples require an eclipse classification")
        elif (
            magnitude != 0.0
            or obscuration != 0.0
            or self.magnitude_jd_ut1 is not None
            or self.obscuration_jd_ut1 is not None
            or self.local_class != "none"
            or self.sun_altitude_deg is not None
        ):
            raise ValueError("non-visible samples must carry the explicit zero state")


@dataclass(frozen=True, slots=True)
class EclipseContourComponent:
    """Vessel: Structured eclipse contour component data."""
    quantity: str
    threshold: float
    component_id: int
    segment_id: int
    closed: bool
    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if self.quantity not in {"magnitude", "obscuration"}:
            raise ValueError("invalid contour quantity")
        if not 0.0 < _finite("threshold", self.threshold) <= 1.0:
            raise ValueError("contour threshold must be in (0, 1]")
        for name in ("component_id", "segment_id"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if not isinstance(self.closed, bool):
            raise TypeError("closed must be a boolean")
        points = tuple(self.points)
        if len(points) < 2:
            raise ValueError("contour component requires at least two points")
        for latitude, longitude in points:
            if not -90.0 <= _finite("latitude", latitude) <= 90.0:
                raise ValueError("contour latitude must be in [-90, 90]")
            if not -180.0 <= _finite("longitude", longitude) <= 180.0:
                raise ValueError("contour longitude must be in [-180, 180]")
        if self.closed and points[0] != points[-1]:
            raise ValueError("closed contour components must repeat their first point")
        if any(
            abs(right[1] - left[1]) > 180.0
            for left, right in zip(points, points[1:])
        ):
            raise ValueError("contour segments must be split at the antimeridian")
        object.__setattr__(self, "points", points)


@dataclass(frozen=True, slots=True)
class EclipseContourLevel:
    """Vessel: Structured eclipse contour level data."""
    quantity: str
    threshold: float
    components: tuple[EclipseContourComponent, ...]

    def __post_init__(self) -> None:
        if self.quantity not in {"magnitude", "obscuration"}:
            raise ValueError("invalid contour quantity")
        threshold = _finite("threshold", self.threshold)
        components = tuple(self.components)
        if any(
            component.quantity != self.quantity
            or component.threshold != threshold
            for component in components
        ):
            raise ValueError("contour level components must share quantity and threshold")
        identities = tuple(
            (component.component_id, component.segment_id)
            for component in components
        )
        if len(identities) != len(set(identities)):
            raise ValueError("contour component/segment identities must be unique")
        object.__setattr__(self, "components", components)


@dataclass(frozen=True, slots=True)
class SolarEclipseCartography:
    """Vessel: Structured solar eclipse cartography data."""
    global_circumstances: "SolarEclipseGlobalCircumstances"
    samples: tuple[SolarEclipseMapSample, ...]
    magnitude_levels: tuple[EclipseContourLevel, ...]
    obscuration_levels: tuple[EclipseContourLevel, ...]
    mesh_depth: int
    achieved_mesh_depth: int
    mesh_triangle_count: int
    time_samples: int
    angular_tolerance_deg: float
    field_tolerance: float
    maximum_angular_edge_deg: float
    converged: bool
    unresolved_edge_count: int
    daylight_policy: str = field(
        default="GEOMETRIC_SUN_CENTER_NONNEGATIVE_ALTITUDE",
        init=False,
    )
    duration_contours_available: bool = field(default=False, init=False)
    projection: str = field(default="SPHERICAL_GEOGRAPHIC", init=False)

    def __post_init__(self) -> None:
        if isinstance(self.mesh_depth, bool) or not isinstance(self.mesh_depth, int):
            raise TypeError("mesh_depth must be an integer")
        if not 0 <= self.mesh_depth <= 3:
            raise ValueError("mesh_depth must be between 0 and 3")
        if (
            isinstance(self.time_samples, bool)
            or not isinstance(self.time_samples, int)
        ):
            raise TypeError("time_samples must be an integer")
        if not 9 <= self.time_samples <= 129 or self.time_samples % 2 == 0:
            raise ValueError(
                "time_samples must be an odd integer between 9 and 129"
            )
        samples = tuple(self.samples)
        if len(samples) < 12:
            raise ValueError("cartography requires at least the base globe vertices")
        if (
            isinstance(self.achieved_mesh_depth, bool)
            or not isinstance(self.achieved_mesh_depth, int)
            or not 0 <= self.achieved_mesh_depth <= self.mesh_depth
        ):
            raise ValueError("achieved_mesh_depth must lie within the depth budget")
        if (
            isinstance(self.mesh_triangle_count, bool)
            or not isinstance(self.mesh_triangle_count, int)
            or self.mesh_triangle_count < 20
        ):
            raise ValueError("mesh_triangle_count must describe a closed globe mesh")
        for name, lower, upper in (
            ("angular_tolerance_deg", 0.1, 90.0),
            ("field_tolerance", 1.0e-6, 0.25),
            ("maximum_angular_edge_deg", 0.0, 180.0),
        ):
            value = _finite(name, getattr(self, name))
            if not lower <= value <= upper:
                raise ValueError(f"{name} must be in [{lower}, {upper}]")
        if not isinstance(self.converged, bool):
            raise TypeError("converged must be a boolean")
        if (
            isinstance(self.unresolved_edge_count, bool)
            or not isinstance(self.unresolved_edge_count, int)
            or self.unresolved_edge_count < 0
        ):
            raise ValueError("unresolved_edge_count must be non-negative")
        if self.converged != (self.unresolved_edge_count == 0):
            raise ValueError("convergence flag must match unresolved_edge_count")
        for quantity, levels in (
            ("magnitude", tuple(self.magnitude_levels)),
            ("obscuration", tuple(self.obscuration_levels)),
        ):
            if not levels or any(level.quantity != quantity for level in levels):
                raise ValueError(f"{quantity} contour levels have invalid identity")
            thresholds = tuple(level.threshold for level in levels)
            if thresholds != tuple(sorted(set(thresholds))):
                raise ValueError(f"{quantity} contour thresholds must be ordered")
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "magnitude_levels", tuple(self.magnitude_levels))
        object.__setattr__(self, "obscuration_levels", tuple(self.obscuration_levels))


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _golden_maximum(
    objective,
    left: float,
    right: float,
    *,
    iterations: int = 36,
) -> tuple[float, float]:
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    x1 = right - ratio * (right - left)
    x2 = left + ratio * (right - left)
    f1 = objective(x1)
    f2 = objective(x2)
    for _ in range(iterations):
        if f1 < f2:
            left = x1
            x1, f1 = x2, f2
            x2 = left + ratio * (right - left)
            f2 = objective(x2)
        else:
            right = x2
            x2, f2 = x1, f1
            x1 = right - ratio * (right - left)
            f1 = objective(x1)
    candidates = ((x1, f1), (x2, f2), (left, objective(left)), (right, objective(right)))
    return max(candidates, key=lambda item: item[1])


def _horizon_root(evaluate, left: float, right: float) -> float:
    left_altitude = evaluate(left).sun_altitude_deg
    right_altitude = evaluate(right).sun_altitude_deg
    if left_altitude == 0.0:
        return left
    if right_altitude == 0.0:
        return right
    if left_altitude * right_altitude > 0.0:
        raise ValueError("horizon root requires an altitude sign change")
    for _ in range(48):
        midpoint = (left + right) / 2.0
        altitude = evaluate(midpoint).sun_altitude_deg
        if altitude == 0.0:
            return midpoint
        if left_altitude * altitude <= 0.0:
            right = midpoint
            right_altitude = altitude
        else:
            left = midpoint
            left_altitude = altitude
    return (left + right) / 2.0


def _solar_site_maximum(
    calculator: "EclipseCalculator",
    global_circumstances: "SolarEclipseGlobalCircumstances",
    latitude_deg: float,
    longitude_deg: float,
    *,
    time_samples: int,
) -> SolarEclipseMapSample:
    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError("latitude_deg must be in [-90, 90]")
    if not -180.0 <= longitude_deg <= 180.0:
        raise ValueError("longitude_deg must be in [-180, 180]")
    contacts = global_circumstances.footprint.contacts
    start = contacts.p1.point.jd_ut
    end = contacts.p4.point.jd_ut
    cache: dict[float, _SolarApparentDiscGeometry] = {}

    def evaluate(jd_ut1: float) -> _SolarApparentDiscGeometry:
        key = float(jd_ut1)
        if key not in cache:
            cache[key] = _topocentric_solar_disc_geometry(
                calculator,
                key,
                latitude_deg,
                longitude_deg,
            )
        return cache[key]

    times = tuple(
        start + (end - start) * index / (time_samples - 1)
        for index in range(time_samples)
    )
    snapshots = tuple(evaluate(epoch) for epoch in times)
    horizon_epochs = []
    for index in range(len(times) - 1):
        left_altitude = snapshots[index].sun_altitude_deg
        right_altitude = snapshots[index + 1].sun_altitude_deg
        if left_altitude == 0.0:
            horizon_epochs.append(times[index])
        elif left_altitude * right_altitude < 0.0:
            horizon_epochs.append(
                _horizon_root(evaluate, times[index], times[index + 1])
            )

    def solve(quantity: str) -> tuple[float | None, float]:
        def objective(epoch: float) -> float:
            snapshot = evaluate(epoch)
            if snapshot.sun_altitude_deg < 0.0:
                return -1.0
            return float(getattr(snapshot, quantity))

        candidates: list[tuple[float, float]] = [
            (epoch, objective(epoch))
            for epoch in (start, end, *horizon_epochs)
        ]
        sampled_values = tuple(objective(epoch) for epoch in times)
        for index in range(1, len(times) - 1):
            if (
                sampled_values[index] >= sampled_values[index - 1]
                and sampled_values[index] >= sampled_values[index + 1]
                and sampled_values[index] >= 0.0
            ):
                candidates.append(
                    _golden_maximum(
                        objective,
                        times[index - 1],
                        times[index + 1],
                    )
                )
        for epoch, value in zip(times, sampled_values):
            candidates.append((epoch, value))
        best_epoch, best_value = max(candidates, key=lambda item: item[1])
        if best_value <= 0.0:
            return None, 0.0
        return best_epoch, best_value

    magnitude_epoch, magnitude = solve("magnitude")
    obscuration_epoch, obscuration = solve("obscuration")
    if magnitude_epoch is None:
        return SolarEclipseMapSample(
            latitude_deg=latitude_deg,
            longitude_deg=longitude_deg,
            visible=False,
            magnitude=0.0,
            magnitude_jd_ut1=None,
            obscuration=0.0,
            obscuration_jd_ut1=None,
            local_class="none",
            sun_altitude_deg=None,
        )
    maximum = evaluate(magnitude_epoch)
    return SolarEclipseMapSample(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        visible=True,
        magnitude=magnitude,
        magnitude_jd_ut1=magnitude_epoch,
        obscuration=obscuration,
        obscuration_jd_ut1=obscuration_epoch,
        local_class=maximum.local_class,
        sun_altitude_deg=maximum.sun_altitude_deg,
    )


def _validate_levels(name: str, values) -> tuple[float, ...]:
    levels = tuple(values)
    if not levels:
        raise ValueError(f"{name} must not be empty")
    parsed: list[float] = []
    for value in levels:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{name} values must be real numbers")
        number = float(value)
        if not math.isfinite(number) or not 0.0 < number <= 1.0:
            raise ValueError(f"{name} values must be in (0, 1]")
        parsed.append(number)
    if parsed != sorted(set(parsed)):
        raise ValueError(f"{name} values must be strictly increasing and unique")
    return tuple(parsed)


def _contour_levels(mesh, samples, quantity: str, thresholds):
    values = tuple(float(getattr(sample, quantity)) for sample in samples)
    levels = []
    for threshold in thresholds:
        components = tuple(
            EclipseContourComponent(
                quantity=quantity,
                threshold=threshold,
                component_id=component_id,
                segment_id=segment_id,
                closed=segment.closed,
                points=segment.points,
            )
            for component_id, component in enumerate(
                extract_contour_components(mesh, values, threshold)
            )
            for segment_id, segment in enumerate(
                split_antimeridian_component(component)
            )
        )
        levels.append(
            EclipseContourLevel(
                quantity=quantity,
                threshold=threshold,
                components=components,
            )
        )
    return tuple(levels)


def _build_solar_eclipse_cartography(
    calculator: "EclipseCalculator",
    *,
    jd_start: float,
    kind: str,
    backward: bool,
    magnitude_levels,
    obscuration_levels,
    mesh_depth: int,
    time_samples: int,
    angular_tolerance_deg: float,
    field_tolerance: float,
) -> SolarEclipseCartography:
    magnitude_thresholds = _validate_levels(
        "magnitude_levels",
        magnitude_levels,
    )
    obscuration_thresholds = _validate_levels(
        "obscuration_levels",
        obscuration_levels,
    )
    if isinstance(mesh_depth, bool) or not isinstance(mesh_depth, int):
        raise TypeError("mesh_depth must be an integer")
    if not 0 <= mesh_depth <= 3:
        raise ValueError("mesh_depth must be between 0 and 3")
    if isinstance(time_samples, bool) or not isinstance(time_samples, int):
        raise TypeError("time_samples must be an integer")
    if not 9 <= time_samples <= 129 or time_samples % 2 == 0:
        raise ValueError("time_samples must be an odd integer between 9 and 129")
    angular_tolerance_deg = _finite(
        "angular_tolerance_deg",
        angular_tolerance_deg,
    )
    if not 0.1 <= angular_tolerance_deg <= 90.0:
        raise ValueError("angular_tolerance_deg must be in [0.1, 90]")
    field_tolerance = _finite("field_tolerance", field_tolerance)
    if not 1.0e-6 <= field_tolerance <= 0.25:
        raise ValueError("field_tolerance must be in [1e-6, 0.25]")

    global_circumstances = calculator.solar_global_circumstances(
        jd_start,
        kind=kind,
        backward=backward,
    )
    mesh = build_icosphere(0)
    sample_cache: dict[tuple[float, float, float], SolarEclipseMapSample] = {}

    def evaluate_vertex(vertex) -> SolarEclipseMapSample:
        sample = sample_cache.get(vertex.xyz)
        if sample is None:
            sample = _solar_site_maximum(
                calculator,
                global_circumstances,
                vertex.latitude_deg,
                vertex.longitude_deg,
                time_samples=time_samples,
            )
            sample_cache[vertex.xyz] = sample
        return sample

    def refinement_edges(current_mesh):
        selected: set[tuple[int, int]] = set()
        for edge in mesh_edges(current_mesh):
            left_vertex = current_mesh.vertices[edge[0]]
            right_vertex = current_mesh.vertices[edge[1]]
            midpoint_vertex = spherical_midpoint(left_vertex, right_vertex)
            left = evaluate_vertex(left_vertex)
            right = evaluate_vertex(right_vertex)
            midpoint = evaluate_vertex(midpoint_vertex)
            angle = edge_angle_deg(left_vertex, right_vertex)
            magnitude_values = (left.magnitude, midpoint.magnitude, right.magnitude)
            obscuration_values = (
                left.obscuration,
                midpoint.obscuration,
                right.obscuration,
            )
            interpolation_error = max(
                abs(midpoint.magnitude - (left.magnitude + right.magnitude) / 2.0),
                abs(
                    midpoint.obscuration
                    - (left.obscuration + right.obscuration) / 2.0
                ),
            )
            brackets_requested_level = any(
                min(magnitude_values) <= threshold <= max(magnitude_values)
                for threshold in magnitude_thresholds
            ) or any(
                min(obscuration_values) <= threshold <= max(obscuration_values)
                for threshold in obscuration_thresholds
            )
            state_changes = len(
                {
                    (sample.visible, sample.local_class)
                    for sample in (left, midpoint, right)
                }
            ) > 1
            seam_or_polar = (
                max(magnitude_values) > 0.0
                and (
                    abs(left_vertex.longitude_deg - right_vertex.longitude_deg)
                    > 180.0
                    or max(
                        abs(left_vertex.latitude_deg),
                        abs(midpoint_vertex.latitude_deg),
                        abs(right_vertex.latitude_deg),
                    )
                    >= 75.0
                )
            )
            if (
                interpolation_error > field_tolerance
                or (
                    angle > angular_tolerance_deg
                    and (brackets_requested_level or state_changes or seam_or_polar)
                )
            ):
                selected.add(edge)
        return selected

    while mesh.depth < mesh_depth:
        selected_edges = refinement_edges(mesh)
        if not selected_edges:
            break
        mesh = refine_mesh_edges(mesh, selected_edges)

    unresolved_edges = refinement_edges(mesh)
    samples = tuple(evaluate_vertex(vertex) for vertex in mesh.vertices)
    maximum_angular_edge_deg = max(
        edge_angle_deg(mesh.vertices[left], mesh.vertices[right])
        for left, right in mesh_edges(mesh)
    )
    return SolarEclipseCartography(
        global_circumstances=global_circumstances,
        samples=samples,
        magnitude_levels=_contour_levels(
            mesh,
            samples,
            "magnitude",
            magnitude_thresholds,
        ),
        obscuration_levels=_contour_levels(
            mesh,
            samples,
            "obscuration",
            obscuration_thresholds,
        ),
        mesh_depth=mesh_depth,
        achieved_mesh_depth=mesh.depth,
        mesh_triangle_count=len(mesh.triangles),
        time_samples=time_samples,
        angular_tolerance_deg=angular_tolerance_deg,
        field_tolerance=field_tolerance,
        maximum_angular_edge_deg=maximum_angular_edge_deg,
        converged=not unresolved_edges,
        unresolved_edge_count=len(unresolved_edges),
    )

"""Internal render adapter for admitted Astrocartography line truth.

This module prepares already-computed ACG line vessels for browser map drawing.
It does not compute Astrocartography lines, own a projection, or define a
public REST route.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from moira.astrocartography import ACGLine

from ..models.astrocartography import AstrocartographyLinesResponse


ASTROCARTOGRAPHY_RENDER_ADAPTER_NAME = "moira_server.astrocartography_rendering"
ASTROCARTOGRAPHY_RENDER_ADAPTER_VERSION = "0.1"

AstrocartographyPrimitiveType = Literal["sampled_curve", "meridian"]
AstrocartographyWrapPolicy = Literal["none", "antimeridian_split"]

_LINE_TYPE_ORDER = {
    "MC": 0,
    "IC": 1,
    "ASC": 2,
    "DSC": 3,
}


@dataclass(frozen=True, slots=True)
class AstrocartographyRenderPoint:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class AstrocartographyRenderPrimitive:
    body: str
    line_type: str
    primitive_type: AstrocartographyPrimitiveType
    segments: tuple[tuple[AstrocartographyRenderPoint, ...], ...]
    source_index: int
    wrap_policy: AstrocartographyWrapPolicy
    style_key: str
    source_provenance: Any


@dataclass(frozen=True, slots=True)
class AstrocartographyRenderMetadata:
    adapter_name: str
    adapter_version: str
    generated_primitive_count: int
    segment_count: int
    antimeridian_split_count: int


@dataclass(frozen=True, slots=True)
class AstrocartographyRenderPacket:
    primitives: tuple[AstrocartographyRenderPrimitive, ...]
    source_provenance: Any
    metadata: AstrocartographyRenderMetadata


@dataclass(frozen=True, slots=True)
class _LineTruth:
    body: str
    line_type: str
    longitude: float | None
    points: tuple[tuple[float, float], ...]
    source_index: int


def adapt_acg_lines_for_rendering(
    lines: list[ACGLine] | tuple[ACGLine, ...] | list[Any] | tuple[Any, ...],
    *,
    source_provenance: Any = None,
    style_hints: dict[str, str] | None = None,
    meridian_latitude_min: float = -90.0,
    meridian_latitude_max: float = 90.0,
) -> AstrocartographyRenderPacket:
    """Return render primitives for already-computed ACG line truth."""

    if meridian_latitude_min >= meridian_latitude_max:
        raise ValueError("meridian_latitude_min must be less than meridian_latitude_max")

    line_truth = tuple(
        _line_truth(line, source_index=index)
        for index, line in enumerate(lines)
    )
    primitives = tuple(
        sorted(
            (
                _primitive_from_line(
                    line,
                    source_provenance=source_provenance,
                    style_hints=style_hints or {},
                    meridian_latitude_min=meridian_latitude_min,
                    meridian_latitude_max=meridian_latitude_max,
                )
                for line in line_truth
            ),
            key=_primitive_sort_key,
        )
    )
    return AstrocartographyRenderPacket(
        primitives=primitives,
        source_provenance=source_provenance,
        metadata=AstrocartographyRenderMetadata(
            adapter_name=ASTROCARTOGRAPHY_RENDER_ADAPTER_NAME,
            adapter_version=ASTROCARTOGRAPHY_RENDER_ADAPTER_VERSION,
            generated_primitive_count=len(primitives),
            segment_count=sum(len(primitive.segments) for primitive in primitives),
            antimeridian_split_count=sum(
                1
                for primitive in primitives
                if primitive.wrap_policy == "antimeridian_split"
            ),
        ),
    )


def adapt_astrocartography_response_for_rendering(
    response: AstrocartographyLinesResponse | dict[str, Any],
    *,
    style_hints: dict[str, str] | None = None,
    meridian_latitude_min: float = -90.0,
    meridian_latitude_max: float = 90.0,
) -> AstrocartographyRenderPacket:
    """Adapt an admitted Astrocartography line response shape for rendering."""

    if isinstance(response, dict):
        lines = response["lines"]
        source_provenance = response.get("provenance")
    else:
        lines = response.lines
        source_provenance = response.provenance
    return adapt_acg_lines_for_rendering(
        lines,
        source_provenance=source_provenance,
        style_hints=style_hints,
        meridian_latitude_min=meridian_latitude_min,
        meridian_latitude_max=meridian_latitude_max,
    )


def _line_truth(line: Any, *, source_index: int) -> _LineTruth:
    if isinstance(line, dict):
        body = line["planet"]
        line_type = line["line_type"]
        longitude = line.get("longitude")
        raw_points = line.get("points", ())
    else:
        body = getattr(line, "planet")
        line_type = getattr(line, "line_type")
        longitude = getattr(line, "longitude")
        raw_points = getattr(line, "points")

    points = tuple(_point_tuple(point) for point in raw_points)
    return _LineTruth(
        body=body,
        line_type=line_type,
        longitude=longitude,
        points=points,
        source_index=source_index,
    )


def _point_tuple(point: Any) -> tuple[float, float]:
    if isinstance(point, dict):
        return float(point["latitude"]), float(point["longitude"])
    if hasattr(point, "latitude") and hasattr(point, "longitude"):
        return float(point.latitude), float(point.longitude)
    return float(point[0]), float(point[1])


def _primitive_from_line(
    line: _LineTruth,
    *,
    source_provenance: Any,
    style_hints: dict[str, str],
    meridian_latitude_min: float,
    meridian_latitude_max: float,
) -> AstrocartographyRenderPrimitive:
    if line.line_type in ("MC", "IC"):
        if line.longitude is None:
            raise ValueError(f"{line.line_type} line requires a meridian longitude")
        segments = (
            (
                AstrocartographyRenderPoint(
                    latitude=meridian_latitude_min,
                    longitude=_normalize_longitude(line.longitude),
                ),
                AstrocartographyRenderPoint(
                    latitude=meridian_latitude_max,
                    longitude=_normalize_longitude(line.longitude),
                ),
            ),
        )
        primitive_type: AstrocartographyPrimitiveType = "meridian"
        wrap_policy: AstrocartographyWrapPolicy = "none"
    else:
        segments, wrap_policy = _split_sampled_curve(line.points)
        primitive_type = "sampled_curve"

    return AstrocartographyRenderPrimitive(
        body=line.body,
        line_type=line.line_type,
        primitive_type=primitive_type,
        segments=segments,
        source_index=line.source_index,
        wrap_policy=wrap_policy,
        style_key=_style_key(line.body, line.line_type, style_hints),
        source_provenance=source_provenance,
    )


def _split_sampled_curve(
    points: tuple[tuple[float, float], ...],
) -> tuple[
    tuple[tuple[AstrocartographyRenderPoint, ...], ...],
    AstrocartographyWrapPolicy,
]:
    if not points:
        return (), "none"

    segments: list[tuple[AstrocartographyRenderPoint, ...]] = []
    current: list[AstrocartographyRenderPoint] = []
    previous_longitude: float | None = None
    split_occurred = False

    for latitude, longitude in points:
        point = AstrocartographyRenderPoint(
            latitude=latitude,
            longitude=_normalize_longitude(longitude),
        )
        if (
            previous_longitude is not None
            and abs(point.longitude - previous_longitude) > 180.0
        ):
            segments.append(tuple(current))
            current = []
            split_occurred = True
        current.append(point)
        previous_longitude = point.longitude

    if current:
        segments.append(tuple(current))

    return tuple(segments), "antimeridian_split" if split_occurred else "none"


def _normalize_longitude(longitude: float) -> float:
    wrapped = (float(longitude) + 180.0) % 360.0 - 180.0
    if wrapped == -180.0 and longitude > 0.0:
        return 180.0
    return wrapped


def _style_key(body: str, line_type: str, style_hints: dict[str, str]) -> str:
    return (
        style_hints.get(f"{body}:{line_type}")
        or style_hints.get(line_type)
        or style_hints.get(body)
        or f"{body}:{line_type}"
    )


def _primitive_sort_key(
    primitive: AstrocartographyRenderPrimitive,
) -> tuple[str, int, int]:
    return (
        primitive.body.casefold(),
        _LINE_TYPE_ORDER.get(primitive.line_type, 99),
        primitive.source_index,
    )


__all__ = [
    "ASTROCARTOGRAPHY_RENDER_ADAPTER_NAME",
    "ASTROCARTOGRAPHY_RENDER_ADAPTER_VERSION",
    "AstrocartographyRenderMetadata",
    "AstrocartographyRenderPacket",
    "AstrocartographyRenderPoint",
    "AstrocartographyRenderPrimitive",
    "adapt_acg_lines_for_rendering",
    "adapt_astrocartography_response_for_rendering",
]

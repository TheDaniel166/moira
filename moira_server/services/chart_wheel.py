"""Website-only chart-wheel primitive service helpers."""

from __future__ import annotations

import math

from moira import Moira
from moira.aspects import find_aspects
from moira.constants import SIGNS, SIGN_SYMBOLS, sign_of
from moira.houses import HouseCusps, assign_house

from ..models.chart import HousesRequest
from ..models.chart_wheel import (
    ChartWheelAspectPrimitiveResponse,
    ChartWheelAspectPolicyTruthResponse,
    ChartWheelCollisionGroupResponse,
    ChartWheelComputationTruthResponse,
    ChartWheelConfig,
    ChartWheelConfigValidationResponse,
    ChartWheelConfigWarningResponse,
    ChartWheelCoordinateResponse,
    ChartWheelHousePolicyTruthResponse,
    ChartWheelHouseCuspPrimitiveResponse,
    ChartWheelHouseSectorPrimitiveResponse,
    ChartWheelLabelPlacementTruthResponse,
    ChartWheelNodeSelectionTruthResponse,
    ChartWheelOrientationTruthResponse,
    ChartWheelPacketRequest,
    ChartWheelPacketResponse,
    ChartWheelPointPrimitiveResponse,
    ChartWheelStylePresetResponse,
    ChartWheelZodiacSegmentResponse,
)
from ..serializers.chart import serialize_chart, serialize_houses
from .chart import compute_chart, compute_houses


_ORIENTATIONS = frozenset({"aries_left", "aries_right", "ascendant_left", "ascendant_right"})
_PRESETS = frozenset({"classic", "dense", "minimal", "print", "dark"})
_GLYPH_SETS = frozenset({"unicode", "text"})
_LABEL_MODES = frozenset({"full", "standard", "compact", "hidden"})
_PLANET_GLYPHS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
    "Uranus": "♅",
    "Neptune": "♆",
    "Pluto": "♇",
    "True Node": "☊",
    "Mean Node": "☊",
    "Lilith": "⚸",
    "True Lilith": "⚸",
}
_TEXT_GLYPHS = {
    "Sun": "Su",
    "Moon": "Mo",
    "Mercury": "Me",
    "Venus": "Ve",
    "Mars": "Ma",
    "Jupiter": "Ju",
    "Saturn": "Sa",
    "Uranus": "Ur",
    "Neptune": "Ne",
    "Pluto": "Pl",
    "True Node": "NN",
    "Mean Node": "NN",
    "Lilith": "Li",
    "True Lilith": "Li",
}


def _warning(code: str, message: str, severity: str = "warning") -> ChartWheelConfigWarningResponse:
    return ChartWheelConfigWarningResponse(code=code, message=message, severity=severity)


def _validate_config(config: ChartWheelConfig) -> list[ChartWheelConfigWarningResponse]:
    warnings: list[ChartWheelConfigWarningResponse] = []
    if config.orientation not in _ORIENTATIONS:
        warnings.append(_warning("unknown_orientation", "orientation is not supported", "error"))
    if config.preset not in _PRESETS:
        warnings.append(_warning("unknown_preset", "preset is not supported", "error"))
    if config.glyph_set not in _GLYPH_SETS:
        warnings.append(_warning("unknown_glyph_set", "glyph_set is not supported", "error"))
    if config.label_mode not in _LABEL_MODES:
        warnings.append(_warning("unknown_label_mode", "label_mode is not supported", "error"))
    if config.aspect_tier is not None and config.aspect_tier not in (0, 1, 2):
        warnings.append(_warning("unknown_aspect_tier", "aspect_tier must be 0, 1, 2, or null", "error"))
    if config.orb_factor <= 0.0:
        warnings.append(_warning("non_positive_orb_factor", "orb_factor must be positive", "error"))
    if config.aspect_radius >= config.point_radius:
        warnings.append(
            _warning("aspect_radius_not_inside_points", "aspect_radius should be smaller than point_radius")
        )
    if config.point_radius >= config.zodiac_radius:
        warnings.append(
            _warning("point_radius_outside_zodiac", "point_radius should be inside zodiac_radius")
        )
    if config.label_mode != "hidden" and config.label_radius <= config.point_radius:
        warnings.append(
            _warning("label_radius_inside_points", "label_radius should be outside point_radius for readable labels")
        )
    if config.include_aspects and config.aspect_tier == 2:
        warnings.append(
            _warning("dense_aspect_tier", "aspect_tier=2 may be visually dense on small wheels", "info")
        )
    return warnings


def _ensure_valid_config(config: ChartWheelConfig) -> list[ChartWheelConfigWarningResponse]:
    warnings = _validate_config(config)
    errors = [warning for warning in warnings if warning.severity == "error"]
    if errors:
        joined = "; ".join(f"{warning.code}: {warning.message}" for warning in errors)
        raise ValueError(joined)
    return warnings


def chart_wheel_presets() -> list[ChartWheelStylePresetResponse]:
    return [
        ChartWheelStylePresetResponse(
            name="classic",
            description="Balanced full-size chart wheel with major aspects.",
            config=ChartWheelConfig(),
        ),
        ChartWheelStylePresetResponse(
            name="dense",
            description="More compact labels and all aspect tiers for detail-heavy desktop views.",
            config=ChartWheelConfig(preset="dense", aspect_tier=2, label_mode="compact", collision_orb_deg=2.0),
        ),
        ChartWheelStylePresetResponse(
            name="minimal",
            description="No aspect lines, compact labels, and fewer visual distractions.",
            config=ChartWheelConfig(preset="minimal", include_aspects=False, label_mode="compact"),
        ),
        ChartWheelStylePresetResponse(
            name="print",
            description="Text glyphs and wider labels for monochrome or print output.",
            config=ChartWheelConfig(preset="print", glyph_set="text", label_mode="full", label_radius=0.88),
        ),
        ChartWheelStylePresetResponse(
            name="dark",
            description="Dark-site preset contract; colors remain owned by the website.",
            config=ChartWheelConfig(preset="dark"),
        ),
    ]


def validate_chart_wheel_config(config: ChartWheelConfig) -> ChartWheelConfigValidationResponse:
    warnings = _validate_config(config)
    return ChartWheelConfigValidationResponse(
        valid=not any(warning.severity == "error" for warning in warnings),
        normalized_config=config,
        warnings=warnings,
    )


def _norm(value: float) -> float:
    return value % 360.0


def _angle_for_longitude(longitude: float, offset: float) -> float:
    return _norm(offset - longitude)


def _xy(angle_deg: float, radius: float) -> ChartWheelCoordinateResponse:
    radians = math.radians(angle_deg)
    return ChartWheelCoordinateResponse(
        x=math.cos(radians) * radius,
        y=math.sin(radians) * radius,
    )


def _angular_distance(a: float, b: float) -> float:
    return abs((_norm(a - b + 180.0)) - 180.0)


def _signed_angular_delta(value: float, origin: float) -> float:
    return (_norm(value - origin + 180.0)) - 180.0


def _minimum_circular_separation(angles: list[float]) -> float | None:
    if len(angles) < 2:
        return None
    ordered = sorted(_norm(angle) for angle in angles)
    gaps = [
        ordered[index + 1] - ordered[index]
        for index in range(len(ordered) - 1)
    ]
    gaps.append(ordered[0] + 360.0 - ordered[-1])
    return min(gaps)


def _layout_label_angles(
    points: list[tuple[str, float, int]],
    requested_separation: float,
) -> tuple[dict[str, float], str, float, float | None, bool]:
    """Lay out labels on a circle without changing their source point angles."""

    if not points:
        return {}, "identity", 0.0, None, True

    ordered = sorted(
        ((key, _norm(angle), priority) for key, angle, priority in points),
        key=lambda item: (item[1], -item[2], item[0].casefold(), item[0]),
    )
    if len(ordered) == 1 or requested_separation <= 0.0:
        angles = {key: angle for key, angle, _ in ordered}
        achieved = _minimum_circular_separation(list(angles.values()))
        return angles, "identity", requested_separation, achieved, True

    effective_separation = min(requested_separation, 360.0 / len(ordered))
    tolerance = 1.0e-10
    candidates: list[
        tuple[float, tuple[str, ...], dict[str, float]]
    ] = []

    for cut_index in range(len(ordered)):
        start_index = (cut_index + 1) % len(ordered)
        rotated = ordered[start_index:] + ordered[:start_index]
        unwrapped: list[tuple[str, float, int]] = []
        previous_angle: float | None = None
        for key, angle, priority in rotated:
            unwrapped_angle = angle
            if previous_angle is not None:
                while unwrapped_angle < previous_angle - tolerance:
                    unwrapped_angle += 360.0
                if unwrapped_angle < previous_angle:
                    unwrapped_angle = previous_angle
            unwrapped.append((key, unwrapped_angle, priority))
            previous_angle = unwrapped_angle

        packed_angles = [unwrapped[0][1]]
        for _, true_angle, _ in unwrapped[1:]:
            packed_angles.append(
                max(true_angle, packed_angles[-1] + effective_separation)
            )

        if packed_angles[-1] - packed_angles[0] > (
            360.0 - effective_separation + tolerance
        ):
            continue

        weights = [max(priority, 1) for _, _, priority in unwrapped]
        displacements = [
            packed_angle - true_angle
            for packed_angle, (_, true_angle, _) in zip(packed_angles, unwrapped)
        ]
        translation = -sum(
            weight * displacement
            for weight, displacement in zip(weights, displacements)
        ) / sum(weights)
        translated_angles = [angle + translation for angle in packed_angles]
        cost = sum(
            weight * (angle + translation - true_angle) ** 2
            for weight, angle, (_, true_angle, _) in zip(
                weights,
                packed_angles,
                unwrapped,
            )
        )
        candidates.append(
            (
                cost,
                tuple(key for key, _, _ in unwrapped),
                {
                    key: _norm(label_angle)
                    for (key, _, _), label_angle in zip(
                        unwrapped,
                        translated_angles,
                    )
                },
            )
        )

    if candidates:
        _, _, label_angles = min(
            candidates,
            key=lambda candidate: (candidate[0], candidate[1]),
        )
    else:
        # The effective separation is geometrically feasible by construction.
        # This branch is only a numerical fallback and preserves the sorted order.
        label_angles = {
            key: _norm(ordered[0][1] + index * effective_separation)
            for index, (key, _, _) in enumerate(ordered)
        }

    achieved = _minimum_circular_separation(list(label_angles.values()))
    requested_satisfied = (
        achieved is None or achieved + 1.0e-8 >= requested_separation
    )
    return (
        label_angles,
        "cyclic_weighted_forward_pack_v1",
        effective_separation,
        achieved,
        requested_satisfied,
    )


def _mean_longitude(longitudes: list[float]) -> float:
    x = sum(math.cos(math.radians(value)) for value in longitudes)
    y = sum(math.sin(math.radians(value)) for value in longitudes)
    return _norm(math.degrees(math.atan2(y, x)))


def _orientation_offset(config: ChartWheelConfig, asc: float | None) -> float:
    if config.orientation == "aries_left":
        return 180.0
    if config.orientation == "aries_right":
        return 0.0
    if config.orientation == "ascendant_left":
        if asc is None:
            raise ValueError("ascendant_left orientation requires houses")
        return _norm(180.0 + asc)
    if config.orientation == "ascendant_right":
        if asc is None:
            raise ValueError("ascendant_right orientation requires houses")
        return _norm(asc)
    raise ValueError(
        "orientation must be aries_left, aries_right, ascendant_left, or ascendant_right"
    )


def _glyph(name: str, config: ChartWheelConfig) -> str:
    if config.glyph_set == "text":
        return _TEXT_GLYPHS.get(name, name[:2])
    return _PLANET_GLYPHS.get(name, name[:2])


def _label(name: str, config: ChartWheelConfig) -> str:
    if config.label_mode == "hidden":
        return ""
    if config.label_mode == "compact":
        return _glyph(name, config)
    if config.label_mode == "full":
        return name
    return f"{_glyph(name, config)} {name}"


def _label_priority(kind: str, name: str) -> int:
    if name in {"Sun", "Moon"}:
        return 100
    if kind == "planet":
        return 80
    return 60


def _stroke_key(aspect_name: str, family: str | None) -> str:
    key = aspect_name.casefold().replace(" ", "_")
    return f"{family or 'aspect'}:{key}"


def _zodiac(config: ChartWheelConfig, offset: float) -> list[ChartWheelZodiacSegmentResponse]:
    segments: list[ChartWheelZodiacSegmentResponse] = []
    for index, sign in enumerate(SIGNS):
        start = float(index * 30)
        end = float((index + 1) * 30)
        segments.append(
            ChartWheelZodiacSegmentResponse(
                sign=sign,
                sign_symbol=SIGN_SYMBOLS[index],
                start_longitude=start,
                end_longitude=end,
                start_angle_deg=_angle_for_longitude(start, offset),
                end_angle_deg=_angle_for_longitude(end, offset),
                radius=config.zodiac_radius,
            )
        )
    return segments


def _collision_groups(
    points: list[tuple[str, float]],
    threshold: float,
) -> tuple[dict[str, int], list[ChartWheelCollisionGroupResponse]]:
    if threshold <= 0.0 or len(points) < 2:
        return {}, []

    sorted_points = sorted(points, key=lambda item: item[1])
    groups: list[list[tuple[str, float]]] = []
    current = [sorted_points[0]]
    for item in sorted_points[1:]:
        if _angular_distance(current[-1][1], item[1]) <= threshold:
            current.append(item)
        else:
            groups.append(current)
            current = [item]
    groups.append(current)

    if len(groups) > 1 and _angular_distance(groups[0][0][1], groups[-1][-1][1]) <= threshold:
        groups[0] = groups[-1] + groups[0]
        groups.pop()

    assignments: dict[str, int] = {}
    responses: list[ChartWheelCollisionGroupResponse] = []
    group_id = 1
    for group in groups:
        if len(group) < 2:
            continue
        members = [name for name, _ in group]
        for member in members:
            assignments[member] = group_id
        responses.append(
            ChartWheelCollisionGroupResponse(
                group_id=group_id,
                members=members,
                center_longitude=_mean_longitude([longitude for _, longitude in group]),
                label_lane=group_id,
            )
        )
        group_id += 1
    return assignments, responses


def _house_for(longitude: float, houses: HouseCusps | None) -> int | None:
    if houses is None:
        return None
    return assign_house(longitude, houses).house


def compute_chart_wheel_packet(
    engine: Moira,
    request: ChartWheelPacketRequest,
) -> ChartWheelPacketResponse:
    """Build deterministic chart-wheel drawing primitives for the website."""

    chart_request = request.chart.model_copy(update={"include_nodes": request.config.include_nodes})
    warnings = _ensure_valid_config(request.config)
    chart = compute_chart(engine, chart_request)
    houses = None
    if request.houses is not None:
        houses = compute_houses(
            engine,
            HousesRequest(
                dt=request.chart.dt,
                time_unknown=request.chart.time_unknown,
                latitude=request.houses.latitude,
                longitude=request.houses.longitude,
                system=request.houses.system,
            ),
        )

    config = request.config
    asc = None if houses is None else houses.asc
    offset = _orientation_offset(config, asc)

    point_sources: list[tuple[str, str, float, bool | None]] = [
        (name, "planet", planet.longitude, planet.retrograde)
        for name, planet in chart.planets.items()
    ]
    if config.include_nodes:
        point_sources.extend(
            (name, "node", node.longitude, node.speed < 0.0)
            for name, node in chart.nodes.items()
        )

    collisions, collision_groups = _collision_groups(
        [(name, longitude) for name, _, longitude, _ in point_sources],
        config.collision_orb_deg,
    )

    true_point_angles = {
        name: _angle_for_longitude(longitude, offset)
        for name, _, longitude, _ in point_sources
    }
    if config.label_mode == "hidden":
        label_angles = dict(true_point_angles)
        label_algorithm = "hidden"
        effective_label_separation = 0.0
        achieved_label_separation = None
        requested_label_constraint_satisfied = True
    else:
        (
            label_angles,
            label_algorithm,
            effective_label_separation,
            achieved_label_separation,
            requested_label_constraint_satisfied,
        ) = _layout_label_angles(
            [
                (name, true_point_angles[name], _label_priority(kind, name))
                for name, kind, _, _ in point_sources
            ],
            config.min_label_separation_deg,
        )
        if effective_label_separation + 1.0e-8 < config.min_label_separation_deg:
            warnings.append(
                _warning(
                    "label_separation_reduced",
                    "min_label_separation_deg exceeds the circular capacity for "
                    f"{len(point_sources)} labels; effective separation is "
                    f"{effective_label_separation:.12g} degrees",
                    "warning",
                )
            )

    points: list[ChartWheelPointPrimitiveResponse] = []
    for name, kind, longitude, retrograde in point_sources:
        angle = true_point_angles[name]
        label_angle = label_angles[name]
        sign, sign_symbol, sign_degree = sign_of(longitude)
        points.append(
            ChartWheelPointPrimitiveResponse(
                key=name,
                kind=kind,
                longitude=longitude,
                angle_deg=angle,
                radius=config.point_radius,
                position=_xy(angle, config.point_radius),
                label_angle_deg=label_angle,
                label_position=_xy(label_angle, config.label_radius),
                label_displacement_deg=_signed_angular_delta(label_angle, angle),
                label=_label(name, config),
                glyph=_glyph(name, config),
                sign=sign,
                sign_symbol=sign_symbol,
                sign_degree=sign_degree,
                retrograde=retrograde,
                house=_house_for(longitude, houses),
                collision_group=collisions.get(name),
                label_priority=_label_priority(kind, name),
                hidden_label=(config.label_mode == "hidden"),
            )
        )

    label_displacements = [
        abs(point.label_displacement_deg)
        for point in points
    ]

    house_cusps: list[ChartWheelHouseCuspPrimitiveResponse] = []
    if houses is not None:
        for index, longitude in enumerate(houses.cusps, start=1):
            angle = _angle_for_longitude(longitude, offset)
            house_cusps.append(
                ChartWheelHouseCuspPrimitiveResponse(
                    house=index,
                    longitude=longitude,
                    angle_deg=angle,
                    radius=config.house_radius,
                    endpoint=_xy(angle, config.house_radius),
                )
            )

    house_sectors: list[ChartWheelHouseSectorPrimitiveResponse] = []
    if houses is not None:
        for index, longitude in enumerate(houses.cusps, start=1):
            next_longitude = houses.cusps[index % 12]
            house_sectors.append(
                ChartWheelHouseSectorPrimitiveResponse(
                    house=index,
                    start_longitude=longitude,
                    end_longitude=next_longitude,
                    start_angle_deg=_angle_for_longitude(longitude, offset),
                    end_angle_deg=_angle_for_longitude(next_longitude, offset),
                    radius=config.house_radius,
                )
            )

    aspects: list[ChartWheelAspectPrimitiveResponse] = []
    if config.include_aspects:
        positions = chart.longitudes(include_nodes=config.include_nodes)
        speeds = {
            name: planet.speed for name, planet in chart.planets.items()
        }
        speeds.update({name: node.speed for name, node in chart.nodes.items()})
        for aspect in find_aspects(
            positions,
            speeds=speeds,
            tier=config.aspect_tier,
            orb_factor=config.orb_factor,
        ):
            start_angle = _angle_for_longitude(positions[aspect.body1], offset)
            end_angle = _angle_for_longitude(positions[aspect.body2], offset)
            tier = None
            if aspect.classification is not None:
                tier = aspect.classification.tier.value
                family = aspect.classification.family.value
            else:
                family = None
            aspects.append(
                ChartWheelAspectPrimitiveResponse(
                    body1=aspect.body1,
                    body2=aspect.body2,
                    aspect=aspect.aspect,
                    symbol=aspect.symbol,
                    angle=aspect.angle,
                    orb=aspect.orb,
                    allowed_orb=aspect.allowed_orb,
                    classification_tier=tier,
                    family=family,
                    stroke_key=_stroke_key(aspect.aspect, family),
                    applying=aspect.applying,
                    start=_xy(start_angle, config.aspect_radius),
                    end=_xy(end_angle, config.aspect_radius),
                )
            )

    chart_response = serialize_chart(chart)
    houses_response = serialize_houses(houses) if houses is not None else None
    orientation_uses_ascendant = config.orientation.startswith("ascendant_")

    return ChartWheelPacketResponse(
        chart=chart_response,
        houses=houses_response,
        config=config,
        orientation_offset_deg=offset,
        warnings=warnings,
        zodiac=_zodiac(config, offset),
        house_cusps=house_cusps,
        house_sectors=house_sectors,
        points=points,
        aspects=aspects,
        collision_groups=collision_groups,
        computation_truth=ChartWheelComputationTruthResponse(
            house_engine_entrypoint=(
                "Moira.houses" if houses_response is not None else None
            ),
            node_selection=ChartWheelNodeSelectionTruthResponse(
                chart_requested_include_nodes=request.chart.include_nodes,
                config_requested_include_nodes=config.include_nodes,
                effective_include_nodes=config.include_nodes,
                config_override_applied=(
                    request.chart.include_nodes != config.include_nodes
                ),
            ),
            houses=ChartWheelHousePolicyTruthResponse(
                houses_requested=request.houses is not None,
                requested_system=(
                    request.houses.system if request.houses is not None else None
                ),
                effective_system=(
                    houses_response.effective_system
                    if houses_response is not None
                    else None
                ),
                fallback_applied=(
                    houses_response.fallback if houses_response is not None else None
                ),
                fallback_reason=(
                    houses_response.fallback_reason
                    if houses_response is not None
                    else None
                ),
                applied_policy=(
                    houses_response.policy if houses_response is not None else None
                ),
            ),
            orientation=ChartWheelOrientationTruthResponse(
                requested_orientation=config.orientation,
                source=(
                    "house_ascendant"
                    if orientation_uses_ascendant
                    else "fixed_aries"
                ),
                anchor_longitude_deg=asc if orientation_uses_ascendant else 0.0,
                offset_deg=offset,
            ),
            aspects=ChartWheelAspectPolicyTruthResponse(
                include_aspects_requested=config.include_aspects,
                included=config.include_aspects,
                tier=config.aspect_tier,
                orb_factor=config.orb_factor,
                positions_include_nodes=config.include_nodes,
                returned_count=len(aspects),
            ),
            label_placement=ChartWheelLabelPlacementTruthResponse(
                mode=config.label_mode,
                algorithm=label_algorithm,
                requested_minimum_separation_deg=config.min_label_separation_deg,
                effective_minimum_separation_deg=effective_label_separation,
                achieved_minimum_separation_deg=achieved_label_separation,
                requested_constraint_satisfied=requested_label_constraint_satisfied,
                collision_threshold_deg=config.collision_orb_deg,
                labels_considered=(
                    0 if config.label_mode == "hidden" else len(points)
                ),
                labels_displaced=sum(
                    displacement > 1.0e-8 for displacement in label_displacements
                ),
                max_absolute_displacement_deg=(
                    max(label_displacements) if label_displacements else 0.0
                ),
            ),
        ),
    )


__all__ = ["chart_wheel_presets", "compute_chart_wheel_packet", "validate_chart_wheel_config"]

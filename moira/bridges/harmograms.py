"""
Moira — Harmogram Bridge Engine
Governs the translation of Moira's astronomical computations into harmogram-compatible data structures for external visualization and analysis systems.

Boundary: owns harmogram data structure generation and position source normalization. Delegates astronomical computation to the core Moira engine and chart systems.

Import-time side effects: None

External dependencies:
    - Moira core engine for chart computation
    - datetime and timedelta for temporal sampling
    - collections.abc for type annotations

Public surface:
    filter_harmogram_body_positions, build_dynamic_harmogram_samples,
    build_transit_to_natal_harmogram_samples, build_directed_to_natal_harmogram_samples,
    build_progressed_to_natal_harmogram_samples, build_dynamic_harmogram_samples_for_range,
    build_transit_to_natal_harmogram_samples_for_range, build_progression_family_harmogram_samples,
    build_secondary_progressed_harmogram_samples, build_tertiary_progressed_harmogram_samples,
    build_tertiary_ii_progressed_harmogram_samples, build_minor_progressed_harmogram_samples,
    build_solar_arc_directed_harmogram_samples, build_converse_secondary_progressed_harmogram_samples,
    build_converse_tertiary_progressed_harmogram_samples, build_converse_tertiary_ii_progressed_harmogram_samples,
    build_converse_minor_progressed_harmogram_samples, build_converse_solar_arc_directed_harmogram_samples,
    HarmogramProgressionFamily
"""

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, cast

from ..facade import Chart, Moira
from ..julian import jd_from_datetime
from ..progressions import ProgressedChart

PositionSource = Chart | ProgressedChart | Mapping[str, float] | Sequence[Mapping[str, Any]]


class HarmogramProgressionFamily(StrEnum):
    """RITE: The Progression-Labeller — the symbolic key that names which
    time-direction technique a harmogram sample series was built from.

THEOREM: Immutable string-enum whose members are the canonical family
         identifiers for the ten supported progression and direction
         techniques used in harmogram visualisation.

RITE OF PURPOSE:
    HarmogramProgressionFamily gives the harmogram bridge a controlled
    vocabulary for selecting the correct ``Moira`` method when building
    dynamic harmogram sample series.  Without it, callers would pass
    bare strings that could silently drift from the registered method
    map, causing silent attribution errors in rendered harmograms.

LAW OF OPERATION:
    Responsibilities:
        - Enumerate the ten harmogram progression/direction families.
        - Map to the ``Moira`` method name via ``_PROGRESSION_METHODS``.
    Non-responsibilities:
        - Does not own any progression computation.
        - Does not validate epoch validity; that is the progression engine.
    Dependencies:
        - enum.StrEnum.
    Structural invariants:
        - Every member has a corresponding entry in ``_PROGRESSION_METHODS``.

Canon: Moira Harmogram Bridge Architecture; moira.progressions doctrine.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira.bridges.harmograms.HarmogramProgressionFamily",
    "risk": "low",
    "api": {"frozen": ["SECONDARY", "TERTIARY", "TERTIARY_II", "MINOR", "SOLAR_ARC", "CONVERSE_SECONDARY", "CONVERSE_TERTIARY", "CONVERSE_TERTIARY_II", "CONVERSE_MINOR", "CONVERSE_SOLAR_ARC"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "none"},
    "succession": {"stance": "terminal", "override_points": []},
    "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    TERTIARY_II = "tertiary_ii"
    MINOR = "minor"
    SOLAR_ARC = "solar_arc"
    CONVERSE_SECONDARY = "converse_secondary"
    CONVERSE_TERTIARY = "converse_tertiary"
    CONVERSE_TERTIARY_II = "converse_tertiary_ii"
    CONVERSE_MINOR = "converse_minor"
    CONVERSE_SOLAR_ARC = "converse_solar_arc"


_PROGRESSION_METHODS: dict[HarmogramProgressionFamily, str] = {
    HarmogramProgressionFamily.SECONDARY: "progression",
    HarmogramProgressionFamily.TERTIARY: "tertiary_progression",
    HarmogramProgressionFamily.TERTIARY_II: "tertiary_ii_progression",
    HarmogramProgressionFamily.MINOR: "minor_progression",
    HarmogramProgressionFamily.SOLAR_ARC: "solar_arc_directions",
    HarmogramProgressionFamily.CONVERSE_SECONDARY: "converse_progression",
    HarmogramProgressionFamily.CONVERSE_TERTIARY: "converse_tertiary_progression",
    HarmogramProgressionFamily.CONVERSE_TERTIARY_II: "converse_tertiary_ii_progression",
    HarmogramProgressionFamily.CONVERSE_MINOR: "converse_minor_progression",
    HarmogramProgressionFamily.CONVERSE_SOLAR_ARC: "converse_solar_arc",
}

_DIRECTED_PROGRESSION_FAMILIES = {
    HarmogramProgressionFamily.SOLAR_ARC,
    HarmogramProgressionFamily.CONVERSE_SOLAR_ARC,
}


def _normalize_body_filters(
    bodies: Sequence[str] | None,
    exclude_bodies: Sequence[str] | None,
) -> tuple[set[str] | None, set[str]]:
    include_set = None if bodies is None else {str(body) for body in bodies}
    exclude_set = set() if exclude_bodies is None else {str(body) for body in exclude_bodies}
    return include_set, exclude_set


def _filter_positions(
    positions: Sequence[dict[str, float | str]],
    *,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, float | str]]:
    include_set, exclude_set = _normalize_body_filters(bodies, exclude_bodies)
    filtered = [
        {"name": item["name"], "degree": item["degree"]}
        for item in positions
        if (include_set is None or cast(str, item["name"]) in include_set)
        and cast(str, item["name"]) not in exclude_set
    ]
    if not filtered:
        raise ValueError("harmogram bridge body filter removed every position")
    return filtered


def _positions_from_source(
    source: PositionSource,
    *,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, float | str]]:
    if isinstance(source, Chart):
        positions = source.longitudes(include_nodes=include_nodes)
        items = [{"name": name, "degree": degree} for name, degree in positions.items()]
        return _filter_positions(items, bodies=bodies, exclude_bodies=exclude_bodies)

    if isinstance(source, ProgressedChart):
        items = [
            {"name": name, "degree": position.longitude}
            for name, position in source.positions.items()
        ]
        return _filter_positions(items, bodies=bodies, exclude_bodies=exclude_bodies)

    if isinstance(source, Mapping):
        items: list[dict[str, float | str]] = []
        for name, degree in source.items():
            items.append({"name": str(name), "degree": float(degree)})
        return _filter_positions(items, bodies=bodies, exclude_bodies=exclude_bodies)

    if isinstance(source, Sequence) and not isinstance(source, (str, bytes, bytearray)):
        normalized: list[dict[str, float | str]] = []
        for index, item in enumerate(source):
            if not isinstance(item, Mapping):
                raise ValueError(f"position sequence item {index} must be a mapping")
            name = item.get("name")
            degree = item.get("degree")
            if name is None or degree is None:
                raise ValueError(f"position sequence item {index} must contain name and degree")
            normalized.append({"name": str(name), "degree": float(degree)})
        if not normalized:
            raise ValueError("position sequence must be non-empty")
        return _filter_positions(normalized, bodies=bodies, exclude_bodies=exclude_bodies)

    raise TypeError("unsupported position source for harmogram bridge")


def filter_harmogram_body_positions(
    source: PositionSource,
    *,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, float | str]]:
    """Normalize a chart-like source and apply explicit body filters."""

    return _positions_from_source(
        source,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def _build_relational_samples(
    samples: Sequence[tuple[float, PositionSource]],
    *,
    sample_key: str,
    natal_source: PositionSource,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    natal_positions = _positions_from_source(
        natal_source,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )
    return [
        {
            "time": float(sample_time),
            sample_key: _positions_from_source(
                source,
                include_nodes=include_nodes,
                bodies=bodies,
                exclude_bodies=exclude_bodies,
            ),
            "natal_positions": natal_positions,
        }
        for sample_time, source in samples
    ]


def build_dynamic_harmogram_samples(
    samples: Sequence[tuple[float, PositionSource]],
    *,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    """Build sky-only harmogram snapshots from native chart-like sources."""

    return [
        {
            "time": float(sample_time),
            "positions": _positions_from_source(
                source,
                include_nodes=include_nodes,
                bodies=bodies,
                exclude_bodies=exclude_bodies,
            ),
        }
        for sample_time, source in samples
    ]


def build_transit_to_natal_harmogram_samples(
    transit_samples: Sequence[tuple[float, PositionSource]],
    natal_source: PositionSource,
    *,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    """Build transit-to-natal harmogram snapshots from native chart-like sources."""

    return _build_relational_samples(
        transit_samples,
        sample_key="transit_positions",
        natal_source=natal_source,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_directed_to_natal_harmogram_samples(
    directed_samples: Sequence[tuple[float, PositionSource]],
    natal_source: PositionSource,
    *,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    """Build directed-to-natal harmogram snapshots from native chart-like sources."""

    return _build_relational_samples(
        directed_samples,
        sample_key="directed_positions",
        natal_source=natal_source,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_progressed_to_natal_harmogram_samples(
    progressed_samples: Sequence[tuple[float, PositionSource]],
    natal_source: PositionSource,
    *,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    """Build progressed-to-natal harmogram snapshots from native chart-like sources."""

    return _build_relational_samples(
        progressed_samples,
        sample_key="progressed_positions",
        natal_source=natal_source,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def _sample_datetimes(
    start_dt: datetime,
    stop_dt: datetime,
    step: timedelta,
) -> list[datetime]:
    if step <= timedelta(0):
        raise ValueError("harmogram bridge range step must be positive")
    if stop_dt < start_dt:
        raise ValueError("harmogram bridge range stop must be >= start")

    samples: list[datetime] = []
    current = start_dt
    while current <= stop_dt:
        samples.append(current)
        current += step
    return samples


def build_dynamic_harmogram_samples_for_range(
    engine: Moira,
    start_dt: datetime,
    stop_dt: datetime,
    step: timedelta,
    *,
    chart_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
) -> list[dict[str, object]]:
    """Build sky-only harmogram samples by sampling native charts across a datetime range."""

    samples: list[tuple[float, PositionSource]] = []
    for sample_dt in _sample_datetimes(start_dt, stop_dt, step):
        chart = engine.chart(
            sample_dt,
            bodies=None if chart_bodies is None else list(chart_bodies),
            include_nodes=include_nodes,
            observer_lat=observer_lat,
            observer_lon=observer_lon,
            observer_elev_m=observer_elev_m,
        )
        samples.append((jd_from_datetime(sample_dt), chart))
    return build_dynamic_harmogram_samples(
        samples,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_transit_to_natal_harmogram_samples_for_range(
    engine: Moira,
    natal_source: PositionSource,
    start_dt: datetime,
    stop_dt: datetime,
    step: timedelta,
    *,
    chart_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
) -> list[dict[str, object]]:
    """Build transit-to-natal harmogram samples by sampling native charts across a datetime range."""

    transit_samples: list[tuple[float, PositionSource]] = []
    for sample_dt in _sample_datetimes(start_dt, stop_dt, step):
        chart = engine.chart(
            sample_dt,
            bodies=None if chart_bodies is None else list(chart_bodies),
            include_nodes=include_nodes,
            observer_lat=observer_lat,
            observer_lon=observer_lon,
            observer_elev_m=observer_elev_m,
        )
        transit_samples.append((jd_from_datetime(sample_dt), chart))
    return build_transit_to_natal_harmogram_samples(
        transit_samples,
        natal_source,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_progression_family_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    family: HarmogramProgressionFamily,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    """Build relational harmogram samples from a declared native progression family."""

    natal_positions_source = natal_source
    if natal_positions_source is None:
        natal_positions_source = engine.chart(
            natal_dt,
            bodies=None if progression_bodies is None else list(progression_bodies),
            include_nodes=include_nodes,
        )

    method_name = _PROGRESSION_METHODS[family]
    progression_method = cast(
        Callable[[datetime, datetime], ProgressedChart],
        getattr(engine, method_name),
    )
    progression_samples: list[tuple[float, PositionSource]] = []
    for target_dt in target_dates:
        progressed = progression_method(
            natal_dt,
            target_dt,
            bodies=None if progression_bodies is None else list(progression_bodies),
        )
        progression_samples.append((jd_from_datetime(target_dt), progressed))

    if family in _DIRECTED_PROGRESSION_FAMILIES:
        return build_directed_to_natal_harmogram_samples(
            progression_samples,
            natal_positions_source,
            include_nodes=include_nodes,
            bodies=bodies,
            exclude_bodies=exclude_bodies,
        )

    return build_progressed_to_natal_harmogram_samples(
        progression_samples,
        natal_positions_source,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_secondary_progressed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.SECONDARY,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_tertiary_progressed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.TERTIARY,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_tertiary_ii_progressed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.TERTIARY_II,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_minor_progressed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.MINOR,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_solar_arc_directed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.SOLAR_ARC,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_converse_secondary_progressed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.CONVERSE_SECONDARY,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_converse_tertiary_progressed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.CONVERSE_TERTIARY,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_converse_tertiary_ii_progressed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.CONVERSE_TERTIARY_II,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_converse_minor_progressed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.CONVERSE_MINOR,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )


def build_converse_solar_arc_directed_harmogram_samples(
    engine: Moira,
    natal_dt: datetime,
    target_dates: Sequence[datetime],
    *,
    natal_source: PositionSource | None = None,
    progression_bodies: Sequence[str] | None = None,
    include_nodes: bool = False,
    bodies: Sequence[str] | None = None,
    exclude_bodies: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    return build_progression_family_harmogram_samples(
        engine,
        natal_dt,
        target_dates,
        family=HarmogramProgressionFamily.CONVERSE_SOLAR_ARC,
        natal_source=natal_source,
        progression_bodies=progression_bodies,
        include_nodes=include_nodes,
        bodies=bodies,
        exclude_bodies=exclude_bodies,
    )

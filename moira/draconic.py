"""
Moira - Draconic Chart Frame
============================

Archetype: Engine

Purpose
-------
Governs the draconic longitude frame: a transparent rotation of source
ecliptic longitudes by the lunar North Node so that the selected North Node
is placed at 0 Aries.

Boundary declaration
--------------------
Owns: the draconic rotation formula, explicit mean/true node anchor policy,
      transformed-position vessels, and chart-backed materialization from an
      existing Moira Chart snapshot.
Delegates: sign derivation to ``moira.constants.sign_of`` and angle reduction
           to ``moira.coordinates.normalize_degrees``.

Import-time side effects: None

Admitted doctrine
-----------------
The draconic chart is a derived longitude frame, not a second sky chart.  It
does not recompute planets, houses, sect, dignity, or node speed.  The caller
must choose the anchor node policy explicitly: ``"mean"`` or ``"true"``.

Public surface
--------------
``DraconicNodeMode``          - literal node policy type.
``DRACONIC_NODE_MODES``       - admitted node policies.
``DraconicAnchor``            - first-class North Node anchor vessel.
``DraconicPosition``          - one transformed body position.
``DraconicChart``             - transformed chart-frame vessel.
``draconic_longitude``        - rotate one longitude by the anchor.
``draconic_positions``        - rotate a mapping of longitudes.
``draconic_chart_from_positions`` - build a vessel from caller positions.
``draconic_chart``            - build a vessel from a Moira Chart snapshot.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, cast

from .constants import Body, sign_of
from .coordinates import angular_distance, normalize_degrees

DraconicNodeMode = Literal["mean", "true"]

DRACONIC_NODE_MODES: tuple[DraconicNodeMode, ...] = ("mean", "true")

__all__ = [
    "DraconicNodeMode",
    "DRACONIC_NODE_MODES",
    "DraconicAnchor",
    "DraconicPosition",
    "DraconicChart",
    "draconic_longitude",
    "draconic_positions",
    "draconic_chart_from_positions",
    "draconic_chart",
]

_NODE_NAMES: dict[DraconicNodeMode, str] = {
    "mean": Body.MEAN_NODE,
    "true": Body.TRUE_NODE,
}

_NODE_SOURCES: dict[DraconicNodeMode, str] = {
    "mean": "moira.mean_node",
    "true": "moira.true_node",
}

_FORMULA = "normalize_degrees(source_longitude - anchor_longitude)"
_SOURCE_ZODIAC = "tropical"
_FRAME = "draconic"
_INTERPRETATION_SCOPE = "longitude_frame_transform_only"


def _require_finite_longitude(value: float, label: str) -> float:
    lon = float(value)
    if not math.isfinite(lon):
        raise ValueError(f"{label} must be a finite longitude in degrees")
    return lon


def _validate_node_mode(node_mode: object) -> DraconicNodeMode:
    if not isinstance(node_mode, str):
        raise TypeError("draconic node_mode must be 'mean' or 'true'")
    mode = node_mode.strip().lower()
    if mode not in DRACONIC_NODE_MODES:
        raise ValueError("draconic node_mode must be 'mean' or 'true'")
    return cast(DraconicNodeMode, mode)


def draconic_longitude(source_longitude: float, anchor_longitude: float) -> float:
    """Return ``source_longitude`` in the node-anchored draconic frame."""

    # Reduce each input to [0, 360) before subtracting: the reduction is exact
    # (IEEE fmod), so multi-revolution longitudes lose no precision to the
    # subtraction, and every caller reaches the rotation by one identical path.
    source = normalize_degrees(_require_finite_longitude(source_longitude, "source_longitude"))
    anchor = normalize_degrees(_require_finite_longitude(anchor_longitude, "anchor_longitude"))
    return normalize_degrees(source - anchor)


@dataclass(frozen=True, slots=True)
class DraconicAnchor:
    """First-class North Node anchor for a draconic longitude frame."""

    node_mode: DraconicNodeMode
    longitude: float
    node_name: str = ""
    source: str = ""
    source_zodiac: str = _SOURCE_ZODIAC
    formula: str = _FORMULA

    def __post_init__(self) -> None:
        mode = _validate_node_mode(self.node_mode)
        expected_name = _NODE_NAMES[mode]
        node_name = self.node_name or expected_name
        if node_name != expected_name:
            raise ValueError(
                f"draconic anchor node_name {node_name!r} does not match "
                f"node_mode {mode!r}"
            )

        source = self.source or _NODE_SOURCES[mode]
        if not isinstance(source, str) or not source.strip():
            raise ValueError("draconic anchor source must be a non-empty string")
        if self.source_zodiac != _SOURCE_ZODIAC:
            raise ValueError("draconic anchor currently admits only tropical source longitudes")
        if self.formula != _FORMULA:
            raise ValueError("draconic anchor formula is fixed by doctrine")

        object.__setattr__(self, "node_mode", mode)
        object.__setattr__(self, "longitude", normalize_degrees(
            _require_finite_longitude(self.longitude, "anchor longitude")
        ))
        object.__setattr__(self, "node_name", node_name)
        object.__setattr__(self, "source", source.strip())

    @property
    def rotation_degrees(self) -> float:
        """Rotation added to source longitudes to place the anchor at 0 Aries."""

        return normalize_degrees(-self.longitude)


@dataclass(frozen=True, slots=True)
class DraconicPosition:
    """One source body transformed into the draconic longitude frame."""

    body: str
    source_longitude: float
    draconic_longitude: float
    anchor_longitude: float
    sign: str = field(init=False)
    sign_symbol: str = field(init=False)
    sign_degree: float = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.body, str) or not self.body.strip():
            raise ValueError("draconic position body must be a non-empty string")

        source = normalize_degrees(
            _require_finite_longitude(self.source_longitude, f"{self.body} source_longitude")
        )
        anchor = normalize_degrees(
            _require_finite_longitude(self.anchor_longitude, "anchor_longitude")
        )
        draconic = normalize_degrees(
            _require_finite_longitude(self.draconic_longitude, f"{self.body} draconic_longitude")
        )
        expected = draconic_longitude(source, anchor)
        if angular_distance(draconic, expected) > 1e-12:
            raise ValueError(
                f"{self.body} draconic_longitude does not match source-anchor rotation"
            )

        sign, symbol, degree = sign_of(draconic)
        object.__setattr__(self, "body", self.body.strip())
        object.__setattr__(self, "source_longitude", source)
        object.__setattr__(self, "draconic_longitude", draconic)
        object.__setattr__(self, "anchor_longitude", anchor)
        object.__setattr__(self, "sign", sign)
        object.__setattr__(self, "sign_symbol", symbol)
        object.__setattr__(self, "sign_degree", degree)


@dataclass(frozen=True, slots=True)
class DraconicChart:
    """A chart snapshot expressed in the node-anchored draconic frame."""

    anchor: DraconicAnchor
    positions: tuple[DraconicPosition, ...]
    jd_ut: float | None = None
    source_zodiac: str = _SOURCE_ZODIAC
    frame: str = _FRAME
    interpretation_scope: str = _INTERPRETATION_SCOPE

    def __post_init__(self) -> None:
        if not isinstance(self.anchor, DraconicAnchor):
            raise TypeError("DraconicChart.anchor must be a DraconicAnchor")
        if self.source_zodiac != _SOURCE_ZODIAC:
            raise ValueError("DraconicChart currently admits only tropical source longitudes")
        if self.frame != _FRAME:
            raise ValueError("DraconicChart.frame must be 'draconic'")
        if self.interpretation_scope != _INTERPRETATION_SCOPE:
            raise ValueError(
                "DraconicChart.interpretation_scope must remain "
                "'longitude_frame_transform_only'"
            )

        positions = tuple(self.positions)
        seen: set[str] = set()
        for position in positions:
            if not isinstance(position, DraconicPosition):
                raise TypeError("DraconicChart.positions must contain DraconicPosition values")
            if position.body in seen:
                raise ValueError(f"duplicate draconic position for {position.body!r}")
            seen.add(position.body)
            if angular_distance(position.anchor_longitude, self.anchor.longitude) > 1e-12:
                raise ValueError(
                    f"{position.body} anchor_longitude does not match chart anchor"
                )

        if self.jd_ut is not None:
            jd = float(self.jd_ut)
            if not math.isfinite(jd):
                raise ValueError("DraconicChart.jd_ut must be finite when supplied")
            object.__setattr__(self, "jd_ut", jd)
        object.__setattr__(self, "positions", positions)

    def longitudes(self) -> dict[str, float]:
        """Return body name to draconic longitude."""

        return {position.body: position.draconic_longitude for position in self.positions}

    def source_longitudes(self) -> dict[str, float]:
        """Return body name to source longitude before draconic rotation."""

        return {position.body: position.source_longitude for position in self.positions}

    def position(self, body: str) -> DraconicPosition | None:
        """Return the transformed position for ``body``, if present."""

        for position in self.positions:
            if position.body == body:
                return position
        return None

    @property
    def anchor_residual(self) -> float | None:
        """Distance from the included anchor node to 0 Aries, if present."""

        anchor_position = self.position(self.anchor.node_name)
        if anchor_position is None:
            return None
        return angular_distance(anchor_position.draconic_longitude, 0.0)


def draconic_positions(
    positions: Mapping[str, float],
    anchor_longitude: float,
) -> tuple[DraconicPosition, ...]:
    """Rotate a mapping of source longitudes into the draconic frame."""

    if not isinstance(positions, Mapping):
        raise TypeError("draconic positions must be supplied as a mapping")
    anchor = normalize_degrees(_require_finite_longitude(anchor_longitude, "anchor_longitude"))
    return tuple(
        DraconicPosition(
            body=body,
            source_longitude=longitude,
            draconic_longitude=draconic_longitude(longitude, anchor),
            anchor_longitude=anchor,
        )
        for body, longitude in positions.items()
    )


def draconic_chart_from_positions(
    positions: Mapping[str, float],
    *,
    anchor: DraconicAnchor,
    jd_ut: float | None = None,
) -> DraconicChart:
    """Materialize a draconic chart vessel from caller-supplied longitudes."""

    if not isinstance(anchor, DraconicAnchor):
        raise TypeError("anchor must be a DraconicAnchor")
    return DraconicChart(
        anchor=anchor,
        positions=draconic_positions(positions, anchor.longitude),
        jd_ut=jd_ut,
    )


def _anchor_from_chart(chart: object, node_mode: DraconicNodeMode) -> DraconicAnchor:
    mode = _validate_node_mode(node_mode)
    node_name = _NODE_NAMES[mode]
    nodes = getattr(chart, "nodes", None)
    if not isinstance(nodes, Mapping):
        raise TypeError("source chart must expose a nodes mapping")
    if node_name not in nodes:
        raise ValueError(
            f"source chart does not contain {node_name!r}; build it with include_nodes=True"
        )
    node = nodes[node_name]
    try:
        longitude = node.longitude
    except AttributeError as exc:
        raise TypeError(f"source chart node {node_name!r} must expose longitude") from exc
    return DraconicAnchor(
        node_mode=mode,
        longitude=longitude,
        node_name=node_name,
        source=_NODE_SOURCES[mode],
    )


def draconic_chart(
    chart: object,
    *,
    node_mode: DraconicNodeMode,
    include_nodes: bool = True,
) -> DraconicChart:
    """Materialize a draconic chart vessel from a Moira Chart snapshot."""

    if not isinstance(include_nodes, bool):
        raise TypeError("include_nodes must be boolean")

    anchor = _anchor_from_chart(chart, node_mode)
    longitudes = getattr(chart, "longitudes", None)
    if not callable(longitudes):
        raise TypeError("source chart must expose longitudes(include_nodes=...)")
    positions = longitudes(include_nodes=include_nodes)
    if not isinstance(positions, Mapping):
        raise TypeError("source chart longitudes() must return a mapping")
    return draconic_chart_from_positions(
        positions,
        anchor=anchor,
        jd_ut=getattr(chart, "jd_ut", None),
    )

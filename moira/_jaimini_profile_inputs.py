"""Strict, immutable inputs for bounded VED-013 computations; no ephemeris IO."""

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Literal

__all__ = ["JaiminiChart", "ArgalaReference", "CharaProjection"]

CLASSICAL = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
NINE = CLASSICAL + ("Rahu", "Ketu")
PROJECTION = "moira_fixed_365_25_day_projection_v1"


def finite_number(value, name, *, canonical=False):
    """Reject coercion, overflow and booleans before any arithmetic."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number without coercion")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not isfinite(value) or (canonical and not 0 <= value < 360):
        raise ValueError(
            f"{name} must be finite" + (" and in [0,360)" if canonical else "")
        )
    return value


def strict_int(value, low, high, name):
    """Validate an exact integer domain, excluding bool and float."""
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low},{high}]")
    return value


@dataclass(frozen=True, slots=True)
class JaiminiChart:
    """Caller-supplied signs or canonical sidereal degrees, snapshotted in body order."""

    basis: Literal["signs", "sidereal_longitudes"]
    positions: tuple[tuple[str, int | float], ...]
    lagna: int | float

    def __post_init__(self):
        if (
            self.basis not in ("signs", "sidereal_longitudes")
            or type(self.basis) is not str
        ):
            raise ValueError("unknown chart basis")
        positions = self.positions
        if isinstance(positions, Mapping):
            positions = tuple(positions.items())
        if type(positions) is not tuple or any(
            type(row) is not tuple or len(row) != 2 or type(row[0]) is not str
            for row in positions
        ):
            raise ValueError(
                "positions must be a body map or tuple of body/value pairs"
            )
        names = tuple(p for p, _ in positions)
        if len(names) != len(set(names)) or set(names) not in (
            set(CLASSICAL),
            set(NINE),
        ):
            raise ValueError(
                "positions must contain exactly seven classical bodies or all nine bodies"
            )
        values = dict(positions)

        def admit(value, name):
            return (
                strict_int(value, 0, 11, name)
                if self.basis == "signs"
                else finite_number(value, name, canonical=True)
            )

        object.__setattr__(
            self,
            "positions",
            tuple((p, admit(values[p], p)) for p in NINE if p in values),
        )
        object.__setattr__(self, "lagna", admit(self.lagna, "lagna"))


def admit_chart(chart, bodies):
    """Revalidate even manually forged vessels and enforce the operation's body pool."""
    if type(chart) is not JaiminiChart:
        raise ValueError("chart must be a JaiminiChart")
    chart = JaiminiChart(chart.basis, chart.positions, chart.lagna)
    if tuple(p for p, _ in chart.positions) != bodies:
        raise ValueError("chart has the wrong participant pool for this profile")
    return chart


def chart_signs(chart):
    """Convert admitted precision to signs without inventing missing degrees."""
    if chart.basis == "signs":
        return dict(chart.positions), chart.lagna
    return {p: int(v // 30) for p, v in chart.positions}, int(chart.lagna // 30)


@dataclass(frozen=True, slots=True)
class ArgalaReference:
    """Semantic reference identity; a node and its occupied house are distinct."""

    kind: Literal["lagna", "house", "planet"]
    value: int | str | None = None

    def __post_init__(self):
        if type(self.kind) is not str:
            raise ValueError("reference kind must be a string identity")
        if self.kind == "lagna" and self.value is None:
            return
        if self.kind == "house":
            strict_int(self.value, 1, 12, "reference house")
            return
        if self.kind == "planet" and type(self.value) is str and self.value in NINE:
            return
        raise ValueError("reference must be lagna, house 1..12, or a named planet")


def admit_references(references):
    """Snapshot and canonicalize a bounded set without merging semantic identities."""
    if type(references) not in (tuple, list) or not 1 <= len(references) <= 22:
        raise ValueError("one to twenty-two references required")
    result = []
    for ref in references:
        if type(ref) is not ArgalaReference:
            raise ValueError("references must be ArgalaReference values")
        result.append(ArgalaReference(ref.kind, ref.value))
    if len(set(result)) != len(result):
        raise ValueError("duplicate reference identity")

    def order(ref):
        return (
            0
            if ref.kind == "lagna"
            else ref.value
            if ref.kind == "house"
            else 13 + NINE.index(ref.value)
        )

    return tuple(sorted(result, key=order))


@dataclass(frozen=True, slots=True)
class CharaProjection:
    """Explicit Moira fixed-day projection, without a source calendar attribution."""

    epoch_jd: float
    projection_id: Literal["moira_fixed_365_25_day_projection_v1"] = PROJECTION

    def __post_init__(self):
        if type(self.projection_id) is not str or self.projection_id != PROJECTION:
            raise ValueError("unsupported Chara projection")
        object.__setattr__(self, "epoch_jd", finite_number(self.epoch_jd, "epoch_jd"))


def legacy_argala_inputs(longitudes, lagna, nodes):
    """Harden invalid legacy inputs while preserving optional partial node maps."""
    if not isinstance(longitudes, Mapping) or set(longitudes) != set(CLASSICAL):
        raise ValueError(
            "sidereal_longitudes must contain exactly the seven classical planets"
        )
    longitudes = {p: finite_number(longitudes[p], p) for p in CLASSICAL}
    lagna = finite_number(lagna, "lagna_sidereal_lon")
    if nodes is not None:
        if not isinstance(nodes, Mapping) or not set(nodes) <= {"Rahu", "Ketu"}:
            raise ValueError("node_longitudes may contain only Rahu and Ketu")
        nodes = {p: finite_number(v, p) for p, v in nodes.items()}
    return longitudes, lagna, nodes

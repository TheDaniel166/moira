"""Transport models for the almuten routes (degree and figuris).

Kernel-free: the caller supplies longitudes, cusps and sect. The doctrine
defaults to ``william_lilly_1647`` (Lilly, Christian Astrology 1647); the
pre-6.9.9 count is available by name as ``moira_legacy_v1``. The doctrine
actually computed is named in every response (see the ``moira.dignities``
note above ``AlmutenDoctrine``).
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, StrictBool, field_validator

from moira.dignities import AlmutenDoctrine, DignityNodeDoctrine

from .common import _StrictModel


_CLASSIC_7 = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
ClassicPlanet = Literal["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]


def _finite(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


class AlmutenDegreeRequest(_StrictModel):
    longitude: float
    is_day_chart: StrictBool
    doctrine: AlmutenDoctrine = AlmutenDoctrine.WILLIAM_LILLY_1647

    @field_validator("longitude")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        return _finite(value, "longitude")


class AlmutenFigurisRequest(_StrictModel):
    """Almuten figuris: 12 cusps (cusps[0] = Ascendant).

    ``william_lilly_1647`` (default) is Lilly's own whole-figure rule: each
    planet's total of essential and accidental dignities in Lilly's table of
    fortitudes (p. 115). It needs all seven planets, ``speeds`` (degrees/day,
    negative for retrograde), ``north_node_longitude`` and
    ``fixed_star_longitudes`` for Regulus, Spica and Algol.
    ``william_lilly_1647_others_five_places`` scores Asc, Midheaven
    (``midheaven_longitude`` or cusps[9]), Sun, Moon and Part of Fortune.
    Both Lilly rules refuse the legacy-only inputs
    ``prenatal_syzygy_longitude``, ``day_ruler`` and ``hour_ruler``.
    """

    positions: dict[ClassicPlanet, float]
    house_cusps: list[float] = Field(min_length=12, max_length=12)
    is_day_chart: StrictBool
    doctrine: AlmutenDoctrine = AlmutenDoctrine.WILLIAM_LILLY_1647
    midheaven_longitude: float | None = None
    speeds: dict[ClassicPlanet, float] | None = None
    north_node_longitude: float | None = None
    node_doctrine: DignityNodeDoctrine = DignityNodeDoctrine.MEAN_NODE
    fixed_star_longitudes: dict[Literal["Regulus", "Spica", "Algol"], float] | None = None
    prenatal_syzygy_longitude: float | None = None
    day_ruler: ClassicPlanet | None = None
    hour_ruler: ClassicPlanet | None = None

    @field_validator("positions")
    @classmethod
    def _valid_positions(cls, value: dict[str, float]) -> dict[str, float]:
        missing = [name for name in ("Sun", "Moon") if name not in value]
        if missing:
            raise ValueError(f"positions missing required keys: {', '.join(missing)}")
        for name, longitude in value.items():
            _finite(longitude, f"positions[{name}]")
        return value

    @field_validator("house_cusps")
    @classmethod
    def _finite_cusps(cls, value: list[float]) -> list[float]:
        for index, cusp in enumerate(value):
            _finite(cusp, f"house_cusps[{index}]")
        return value

    @field_validator("speeds", "fixed_star_longitudes")
    @classmethod
    def _finite_maps(cls, value: dict[str, float] | None, info) -> dict[str, float] | None:
        if value is not None:
            for name, number in value.items():
                _finite(number, f"{info.field_name}[{name}]")
        return value

    @field_validator("prenatal_syzygy_longitude", "midheaven_longitude", "north_node_longitude")
    @classmethod
    def _finite_optional(cls, value: float | None, info) -> float | None:
        return None if value is None else _finite(value, info.field_name)


class AlmutenTallyResponse(_StrictModel):
    planet: str
    essential_points: int
    house_points: int
    ruler_points: int
    accidental_points: int
    total: int


class AlmutenScoredPointResponse(_StrictModel):
    name: str
    longitude: float


class AlmutenProvenanceResponse(_StrictModel):
    source_module: str = "moira.dignities"
    engine_entrypoint: str
    doctrine_source: str
    essential_point_scale: str = "domicile 5, exaltation 4, triplicity 3, term 2, face 1"
    essential_point_scale_source: str = (
        "William Lilly, Christian Astrology (1647), Book I, table of fortitudes, p. 115"
    )
    bounds_table: str
    triplicity_table: str
    face_table: str = "chaldean"
    unsourced_elements: list[str]
    not_computed: list[str]
    tie_break: str
    chart_construction: str = "not_computed"
    sect_determination: str = "caller_supplied"


class AlmutenResponse(_StrictModel):
    doctrine: str
    almuten: str | None
    is_day_chart: bool
    tallies: list[AlmutenTallyResponse]
    scored_points: list[AlmutenScoredPointResponse]
    tied_planets: list[str]
    reason: str | None = None
    provenance: AlmutenProvenanceResponse


__all__ = [
    "AlmutenDegreeRequest",
    "AlmutenFigurisRequest",
    "AlmutenProvenanceResponse",
    "AlmutenResponse",
    "AlmutenScoredPointResponse",
    "AlmutenTallyResponse",
]

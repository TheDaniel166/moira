"""Shared admission for source-defined yoga computations; no doctrine dispatch."""

from collections.abc import Mapping
from math import isfinite

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


def number(value, name: str, *, canonical: bool = False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number, not a boolean or string")
    try:
        finite = isfinite(value)
    except OverflowError:
        finite = False
    if not finite or (canonical and not 0 <= value < 360):
        raise ValueError(
            f"{name} must be finite" + (" and in [0, 360)" if canonical else "")
        )
    return value


def longitudes(value, *, canonical: bool = False):
    if not isinstance(value, Mapping) or set(value) != set(PLANETS):
        raise ValueError(
            "sidereal_longitudes must contain exactly the seven classical planets"
        )
    return {
        p: number(value[p], f"longitude for {p}", canonical=canonical) for p in PLANETS
    }


def speeds(value):
    if value is None:
        return None
    if not isinstance(value, Mapping) or not set(value) <= set(PLANETS):
        raise ValueError("planet_speeds must be a map of classical planet names")
    return {p: number(v, f"speed for {p}") for p, v in value.items()}

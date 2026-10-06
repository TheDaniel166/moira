"""Bounded numeric and identity types for direct Vedic transport inputs."""
from typing import Annotated, Literal
from pydantic import Field

FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
ClassicalPlanet = Literal["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
NodePlanet = Literal["Rahu", "Ketu"]
VedicReference = Literal["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"]
SignIndex = Annotated[int, Field(strict=True, ge=0, le=11)]
RekhaCount = Annotated[int, Field(strict=True, ge=0, le=8)]
RekhaTable = Annotated[tuple[RekhaCount, ...], Field(min_length=12, max_length=12)]
CLASSICAL_PLANETS = frozenset(("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"))


def require_classical(value: dict[str, float]) -> dict[str, float]:
    """Require the complete seven-body input expected by existing chart rules."""
    missing = CLASSICAL_PLANETS - value.keys()
    if missing:
        raise ValueError(f"sidereal_longitudes missing classical planets: {sorted(missing)}")
    return value


def require_sign_references(value: dict[str, int]) -> dict[str, int]:
    """Require the eight natal sign references used by Ashtakavarga."""
    missing = (CLASSICAL_PLANETS | {"Lagna"}) - value.keys()
    if missing:
        raise ValueError(f"sign_indices missing natal references: {sorted(missing)}")
    return value

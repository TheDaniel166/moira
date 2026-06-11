"""Transport models for return endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .transits import TransitComputationTruthResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SolarReturnRequest(_StrictModel):
    natal_sun_lon: float
    year: int
    step_days: float | None = None
    # Optional caller-supplied scan step (days) for the return search.
    # When None (default), the engine uses per-body auto or ReturnSearchPolicy override.
    # See moira.transits.ReturnSearchPolicy and planet_return.
    solver_tolerance_days: float | None = None
    # Optional solver tolerance (days) for bisection refinement.
    # Default in ReturnSearchPolicy is 1e-6.


class LunarReturnRequest(_StrictModel):
    natal_moon_lon: float
    jd_start: float
    step_days: float | None = None
    # Optional caller-supplied scan step (days) for the return search.
    # When None (default), the engine uses per-body auto or ReturnSearchPolicy override.
    # See moira.transits.ReturnSearchPolicy and planet_return.
    solver_tolerance_days: float | None = None
    # Optional solver tolerance (days) for bisection refinement.
    # Default in ReturnSearchPolicy is 1e-6.


class PlanetReturnRequest(_StrictModel):
    body: str
    natal_lon: float
    jd_start: float
    direction: str = "direct"
    step_days: float | None = None
    # Optional caller-supplied scan step (days) for the return search.
    # When None (default), the engine uses per-body auto or ReturnSearchPolicy override.
    # See moira.transits.ReturnSearchPolicy and planet_return.
    solver_tolerance_days: float | None = None
    # Optional solver tolerance (days) for bisection refinement.
    # Default in ReturnSearchPolicy is 1e-6.


class ReturnEventResponse(_StrictModel):
    return_type: str
    body: str
    jd_ut: float
    datetime_utc: str
    computation_truth: TransitComputationTruthResponse | None = None
    # Embedded reduction truth from the internal next_transit (reused from transits family).
    # Contains target resolution (natal_lon as numeric), search brackets, step, solver_tolerance,
    # direction_filter, wrapper as PLANET_RETURN, etc. Populated via low-level capture in service.
    # Enhanced for reduction visibility per Returns Closure Plan.


__all__ = [
    "LunarReturnRequest",
    "PlanetReturnRequest",
    "ReturnEventResponse",
    "SolarReturnRequest",
]

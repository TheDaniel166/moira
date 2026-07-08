"""Transport models for the Yoga engine route family."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import field_validator

from .common import _StrictModel


_SEVEN_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
)


class YogaPolicyRequest(_StrictModel):
    """Doctrine switches (defaults are BPHS-primary)."""

    moon_benefic_mode: Literal["paksha", "always_benefic"] = "paksha"
    mercury_benefic_mode: Literal["conditional", "always_benefic"] = "conditional"
    mahapurusha_reference: Literal["lagna", "lagna_or_moon"] = "lagna"
    gajakesari_mode: Literal["parashara", "common"] = "parashara"
    budhaditya_combustion_cancel: bool = False
    viparita_mode: Literal[
        "phaladeepika", "uttara_kalamrita", "raman"
    ] = "phaladeepika"


class YogaEvaluateRequest(_StrictModel):
    """Direct yoga evaluation from sidereal longitudes."""

    sidereal_longitudes: dict[str, float]
    lagna_sidereal_lon: float
    planet_speeds: dict[str, float] | None = None
    policy: YogaPolicyRequest | None = None
    include_absent: bool = False

    @field_validator("sidereal_longitudes")
    @classmethod
    def _seven_classical(cls, value: dict[str, float]) -> dict[str, float]:
        missing = _SEVEN_PLANETS - set(value)
        if missing:
            raise ValueError(
                f"sidereal_longitudes must include all seven classical "
                f"planets; missing: {sorted(missing)}"
            )
        for name, lon in value.items():
            if not math.isfinite(lon):
                raise ValueError(f"longitude for {name} must be finite")
        return value

    @field_validator("lagna_sidereal_lon")
    @classmethod
    def _finite_lagna(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("lagna_sidereal_lon must be finite")
        return value


class YogaConditionResponse(_StrictModel):
    description: str
    satisfied: bool
    observed: str


class YogaResultResponse(_StrictModel):
    name: str
    family: str
    formed: bool
    cancelled: bool
    present: bool
    conditions: tuple[YogaConditionResponse, ...]
    cancellations: tuple[YogaConditionResponse, ...]
    participants: tuple[str, ...]
    houses_involved: tuple[int, ...]
    source: str
    suppressed_by: str | None
    notes: str


class YogaChartResponse(_StrictModel):
    """Full yoga evaluation — every proof object, or presents only."""

    lagna_sign_index: int
    present_names: tuple[str, ...]
    evaluated_count: int
    yogas: tuple[YogaResultResponse, ...]


__all__ = [
    "YogaChartResponse",
    "YogaConditionResponse",
    "YogaEvaluateRequest",
    "YogaPolicyRequest",
    "YogaResultResponse",
]

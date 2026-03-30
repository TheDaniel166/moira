"""
Moira -- primary_directions/keys.py
Standalone time-key doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, family classification, and arc-to-time conversion
rules for currently admitted primary-direction keys. This module is intentionally
orthogonal to primary-direction geometry and direction space.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "PrimaryDirectionKey",
    "PrimaryDirectionKeyFamily",
    "PrimaryDirectionKeyPolicy",
    "PrimaryDirectionKeyTruth",
    "convert_arc_to_time",
    "primary_direction_key_truth",
]


_NAIBOD_RATE = 360.0 / 365.25
_PTOLEMY_RATE = 1.0
_CARDAN_RATE = 59.0 / 60.0 + 12.0 / 3600.0


class PrimaryDirectionKey(StrEnum):
    PTOLEMY = "ptolemy"
    NAIBOD = "naibod"
    CARDAN = "cardan"
    SOLAR = "solar"


class PrimaryDirectionKeyFamily(StrEnum):
    STATIC = "static"
    DYNAMIC = "dynamic"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionKeyPolicy:
    key: PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD

    def __post_init__(self) -> None:
        if not isinstance(self.key, PrimaryDirectionKey):
            raise ValueError(f"Unsupported primary direction key: {self.key}")

    @property
    def family(self) -> PrimaryDirectionKeyFamily:
        if self.key is PrimaryDirectionKey.SOLAR:
            return PrimaryDirectionKeyFamily.DYNAMIC
        return PrimaryDirectionKeyFamily.STATIC


@dataclass(frozen=True, slots=True)
class PrimaryDirectionKeyTruth:
    key: PrimaryDirectionKey
    family: PrimaryDirectionKeyFamily
    rate_degrees_per_year: float

    def __post_init__(self) -> None:
        expected_family = PrimaryDirectionKeyPolicy(self.key).family
        if self.family is not expected_family:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: family does not match key"
            )
        if self.rate_degrees_per_year <= 0.0:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: rate_degrees_per_year must be positive"
            )


def _normalize_key(key: str | PrimaryDirectionKey) -> PrimaryDirectionKey:
    try:
        return key if isinstance(key, PrimaryDirectionKey) else PrimaryDirectionKey(str(key).lower())
    except ValueError:
        return PrimaryDirectionKey.NAIBOD


def primary_direction_key_truth(
    key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD,
    *,
    solar_rate: float | None = None,
) -> PrimaryDirectionKeyTruth:
    resolved_key = _normalize_key(key)
    if resolved_key is PrimaryDirectionKey.SOLAR:
        resolved_rate = abs(solar_rate) if solar_rate is not None else _NAIBOD_RATE
        if resolved_rate <= 0.0:
            resolved_rate = _NAIBOD_RATE
    elif resolved_key is PrimaryDirectionKey.PTOLEMY:
        resolved_rate = _PTOLEMY_RATE
    elif resolved_key is PrimaryDirectionKey.CARDAN:
        resolved_rate = _CARDAN_RATE
    else:
        resolved_rate = _NAIBOD_RATE
    policy = PrimaryDirectionKeyPolicy(resolved_key)
    return PrimaryDirectionKeyTruth(
        key=resolved_key,
        family=policy.family,
        rate_degrees_per_year=resolved_rate,
    )


def convert_arc_to_time(
    arc: float,
    key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD,
    *,
    solar_rate: float | None = None,
) -> float:
    if arc <= 0.0:
        raise ValueError("convert_arc_to_time requires a positive arc")
    truth = primary_direction_key_truth(key, solar_rate=solar_rate)
    return arc / truth.rate_degrees_per_year

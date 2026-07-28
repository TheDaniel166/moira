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

import math
from dataclasses import dataclass
from .._strenum import StrEnum
from numbers import Real

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
    """Vessel: Enumeration of specific time-keys used for arc-to-year conversion."""
    PTOLEMY = "ptolemy"
    NAIBOD = "naibod"
    CARDAN = "cardan"
    SOLAR = "solar"


class PrimaryDirectionKeyFamily(StrEnum):
    """Vessel: Classification of time-keys as static or dynamic (solar-arc dependent)."""
    STATIC = "static"
    DYNAMIC = "dynamic"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionKeyPolicy:
    """Vessel: Governance policy for time-key selection and family derivation."""
    key: PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD

    def __post_init__(self) -> None:
        if not isinstance(self.key, PrimaryDirectionKey):
            raise ValueError(f"Unsupported primary direction key: {self.key}")

    @property
    def family(self) -> PrimaryDirectionKeyFamily:
        # This admitted key divides by one explicitly supplied natal solar
        # rate.  It is chart-conditioned, but it is not a dynamic symbolic-key
        # integration and must not claim that stronger semantics.
        return PrimaryDirectionKeyFamily.STATIC


@dataclass(frozen=True, slots=True)
class PrimaryDirectionKeyTruth:
    """Vessel: Record of the exact mathematical rate and family for a specific time-key."""
    key: PrimaryDirectionKey
    family: PrimaryDirectionKeyFamily
    rate_degrees_per_year: float
    requested_key: str = ""
    fallback_applied: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.key, PrimaryDirectionKey):
            raise ValueError("PrimaryDirectionKeyTruth key must be PrimaryDirectionKey")
        if not isinstance(self.family, PrimaryDirectionKeyFamily):
            raise ValueError("PrimaryDirectionKeyTruth family must be PrimaryDirectionKeyFamily")
        expected_family = PrimaryDirectionKeyPolicy(self.key).family
        if self.family is not expected_family:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: family does not match key"
            )
        if (
            not isinstance(self.rate_degrees_per_year, Real)
            or isinstance(self.rate_degrees_per_year, bool)
            or not math.isfinite(self.rate_degrees_per_year)
            or self.rate_degrees_per_year <= 0.0
        ):
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: rate_degrees_per_year must be positive"
            )
        if not isinstance(self.requested_key, str):
            raise ValueError("PrimaryDirectionKeyTruth requested_key must be str")
        if not isinstance(self.fallback_applied, bool):
            raise ValueError("PrimaryDirectionKeyTruth fallback_applied must be bool")
        if self.fallback_applied and self.key is not PrimaryDirectionKey.NAIBOD:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: fallback must resolve to Naibod"
            )


def _resolve_key(key: str | PrimaryDirectionKey) -> tuple[PrimaryDirectionKey, bool]:
    if isinstance(key, PrimaryDirectionKey):
        return key, False
    if not isinstance(key, str):
        raise ValueError("Primary direction key must be a string or PrimaryDirectionKey")
    try:
        return PrimaryDirectionKey(str(key).lower()), False
    except ValueError:
        return PrimaryDirectionKey.NAIBOD, True


def primary_direction_key_truth(
    key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD,
    *,
    solar_rate: float | None = None,
) -> PrimaryDirectionKeyTruth:
    resolved_key, fallback_applied = _resolve_key(key)
    if resolved_key is PrimaryDirectionKey.SOLAR:
        if (
            not isinstance(solar_rate, Real)
            or isinstance(solar_rate, bool)
            or not math.isfinite(solar_rate)
            or solar_rate <= 0.0
        ):
            raise ValueError(
                "The solar primary-direction key requires an explicit positive finite natal solar rate"
            )
        resolved_rate = float(solar_rate)
    elif resolved_key is PrimaryDirectionKey.PTOLEMY:
        resolved_rate = _PTOLEMY_RATE
    elif resolved_key is PrimaryDirectionKey.CARDAN:
        resolved_rate = _CARDAN_RATE
    else:
        resolved_rate = _NAIBOD_RATE
    policy = PrimaryDirectionKeyPolicy(resolved_key)
    # Key resolution is case-insensitive (see _resolve_key), but the recorded
    # requested_key preserves the caller's original token verbatim so that a
    # fallback remains diagnosable exactly as it was requested.
    requested = key.value if isinstance(key, PrimaryDirectionKey) else str(key)
    return PrimaryDirectionKeyTruth(
        key=resolved_key,
        family=policy.family,
        rate_degrees_per_year=resolved_rate,
        requested_key=requested,
        fallback_applied=fallback_applied,
    )


def convert_arc_to_time(
    arc: float,
    key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD,
    *,
    solar_rate: float | None = None,
) -> float:
    if (
        not isinstance(arc, Real)
        or isinstance(arc, bool)
        or not math.isfinite(arc)
        or arc <= 0.0
    ):
        raise ValueError("convert_arc_to_time requires a positive arc")
    truth = primary_direction_key_truth(key, solar_rate=solar_rate)
    return arc / truth.rate_degrees_per_year

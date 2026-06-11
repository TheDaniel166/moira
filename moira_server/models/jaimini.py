"""Transport models for Phase-9 Jaimini route family (P9-03)."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import field_validator, model_validator

from .common import _StrictModel


class JaiminiPolicyRequest(_StrictModel):
    """Explicit Jaimini computation policy."""

    scheme: int = 7
    ayanamsa_system: str = "Lahiri"

    @field_validator("scheme")
    @classmethod
    def _valid_scheme(cls, value: int) -> int:
        if value not in (7, 8):
            raise ValueError("scheme must be 7 or 8")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class JaiminiDirectRequest(_StrictModel):
    """Direct Jaimini request using caller-supplied sidereal longitudes."""

    sidereal_longitudes: dict[str, float]
    scheme: int = 7
    ayanamsa_system: str = "Lahiri"
    policy: JaiminiPolicyRequest | None = None

    @field_validator("sidereal_longitudes")
    @classmethod
    def _finite_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        for planet, longitude in value.items():
            if not math.isfinite(longitude):
                raise ValueError(f"sidereal_longitudes[{planet!r}] must be finite")
        return value

    @field_validator("scheme")
    @classmethod
    def _valid_scheme(cls, value: int) -> int:
        if value not in (7, 8):
            raise ValueError("scheme must be 7 or 8")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class JaiminiChartRequest(_StrictModel):
    """Chart-backed Jaimini request deriving sidereal longitudes through Moira."""

    dt: datetime
    scheme: int = 7
    ayanamsa_system: str = "Lahiri"
    policy: JaiminiPolicyRequest | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("scheme")
    @classmethod
    def _valid_scheme(cls, value: int) -> int:
        if value not in (7, 8):
            raise ValueError("scheme must be 7 or 8")
        return value

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class JaiminiConditionDirectRequest(JaiminiDirectRequest):
    """Direct Jaimini condition request for one assignment selector."""

    karaka_name: str | None = None
    planet: str | None = None

    @model_validator(mode="after")
    def _exactly_one_selector(self):
        if (self.karaka_name is None) == (self.planet is None):
            raise ValueError("provide exactly one of karaka_name or planet")
        return self


class JaiminiConditionChartRequest(JaiminiChartRequest):
    """Chart-backed Jaimini condition request for one assignment selector."""

    karaka_name: str | None = None
    planet: str | None = None

    @model_validator(mode="after")
    def _exactly_one_selector(self):
        if (self.karaka_name is None) == (self.planet is None):
            raise ValueError("provide exactly one of karaka_name or planet")
        return self


class JaiminiPairDirectRequest(JaiminiDirectRequest):
    """Direct Jaimini pair request for two karaka roles."""

    role_a: str
    role_b: str

    @model_validator(mode="after")
    def _distinct_roles(self):
        if self.role_a == self.role_b:
            raise ValueError("role_a and role_b must be different")
        return self


class JaiminiPairChartRequest(JaiminiChartRequest):
    """Chart-backed Jaimini pair request for two karaka roles."""

    role_a: str
    role_b: str

    @model_validator(mode="after")
    def _distinct_roles(self):
        if self.role_a == self.role_b:
            raise ValueError("role_a and role_b must be different")
        return self


class KarakaAssignmentResponse(_StrictModel):
    karaka_name: str
    karaka_rank: int
    planet: str
    degree_in_sign: float
    sidereal_longitude: float
    is_rahu_inverted: bool


class JaiminiKarakaResultResponse(_StrictModel):
    scheme: int
    atmakaraka: str
    assignments: list[KarakaAssignmentResponse]
    tie_warnings: list[tuple[str, str]]
    has_ties: bool


class KarakaConditionProfileResponse(_StrictModel):
    karaka_name: str
    karaka_rank: int
    planet: str
    planet_type: str
    degree_in_sign: float
    sidereal_longitude: float
    is_rahu_inverted: bool
    is_atmakaraka: bool
    is_darakaraka: bool


class JaiminiChartProfileResponse(_StrictModel):
    scheme: int
    atmakaraka_planet: str
    darakaraka_planet: str
    has_node_atmakaraka: bool
    has_node_darakaraka: bool
    has_ties: bool
    tie_count: int
    profiles: list[KarakaConditionProfileResponse]


class KarakaPairResponse(_StrictModel):
    role_a: str
    role_b: str
    planet_a: str
    planet_b: str
    type_a: str
    type_b: str
    involves_node: bool
    both_are_nodes: bool


__all__ = [
    "JaiminiChartProfileResponse",
    "JaiminiChartRequest",
    "JaiminiConditionChartRequest",
    "JaiminiConditionDirectRequest",
    "JaiminiDirectRequest",
    "JaiminiKarakaResultResponse",
    "JaiminiPairChartRequest",
    "JaiminiPairDirectRequest",
    "JaiminiPolicyRequest",
    "KarakaAssignmentResponse",
    "KarakaConditionProfileResponse",
    "KarakaPairResponse",
]

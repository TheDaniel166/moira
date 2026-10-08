"""Bounded numeric and identity types for direct Vedic transport inputs."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import AfterValidator, BeforeValidator, Field

from moira.constants import HOUSE_SYSTEM_NAMES
from moira.dasha import VIMSHOTTARI_YEAR_BASIS
from moira.sidereal import list_ayanamsa_systems

FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
ClassicalPlanet = Literal["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
NodePlanet = Literal["Rahu", "Ketu"]
VedicReference = Literal["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"]
SignIndex = Annotated[int, Field(strict=True, ge=0, le=11)]
RekhaCount = Annotated[int, Field(strict=True, ge=0, le=8)]
RekhaTable = Annotated[tuple[RekhaCount, ...], Field(min_length=12, max_length=12)]
CLASSICAL_PLANETS = frozenset(("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"))


def require_civil_datetime(value):
    """Admit civil timestamp text or datetime objects, never Unix epochs."""
    if not isinstance(value, (str, datetime)) or (
        isinstance(value, str) and not any(separator in value for separator in ("T", "t", " "))
    ):
        raise ValueError("datetime must be a timezone-aware civil datetime, not a numeric timestamp")
    # Whitespace does not turn an epoch string into civil timestamp text.
    if isinstance(value, str):
        text = value.strip()
        if len(text) < 11 or text[4:5] != "-" or text[7:8] != "-":
            raise ValueError("datetime must be a timezone-aware civil datetime, not a numeric timestamp")
    return value


def require_aware_civil_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value


def require_ayanamsa(value: str) -> str:
    if not value:
        raise ValueError("ayanamsa_system must be non-empty")
    if value not in list_ayanamsa_systems():
        raise ValueError(f"Unknown ayanamsa system: {value!r}")
    return value


def require_vimshottari_year_basis(value: str) -> str:
    if value not in VIMSHOTTARI_YEAR_BASIS:
        raise ValueError("year_basis must be a supported Vimshottari doctrine key")
    return value


def resolve_vedic_house_system(value: str) -> str:
    """Resolve admitted engine codes/names without an unknown-system fallback."""
    key = " ".join(value.replace("_", " ").replace("-", " ").casefold().split())
    for code, name in HOUSE_SYSTEM_NAMES.items():
        if key in (code.casefold(), name.casefold()):
            return code
    raise ValueError(f"unsupported house system: {value!r}")


def require_house_system(value: str) -> str:
    resolve_vedic_house_system(value)
    return value


CivilDateTime = Annotated[datetime, BeforeValidator(require_civil_datetime), AfterValidator(require_aware_civil_datetime)]
KnownAyanamsa = Annotated[str, AfterValidator(require_ayanamsa)]
VimshottariYearBasis = Annotated[str, AfterValidator(require_vimshottari_year_basis)]
KnownHouseSystem = Annotated[str, AfterValidator(require_house_system)]


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

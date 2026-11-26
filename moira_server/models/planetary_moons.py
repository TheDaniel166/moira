"""Request and response contracts for Jupiter and Saturn moon states."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from moira.planetary_moon_events import (
    PLANETARY_MOON_DEFAULT_EVALUATIONS,
    PLANETARY_MOON_EVENT_KINDS,
    PLANETARY_MOON_MAX_EVALUATIONS,
    PLANETARY_MOON_MAX_RESULTS,
    PLANETARY_MOON_MAX_WINDOW_DAYS,
    PlanetaryMoonEventKind,
    PlanetaryMoonEventSearch,
    PlanetaryMoonSearchMode,
)


Planet = Literal["Jupiter", "Saturn"]


class PlanetaryMoonsSnapshotRequest(BaseModel):
    """Select a TT epoch and optionally one parent planet."""

    model_config = ConfigDict(extra="forbid")

    jd_tt: float = Field(strict=True, allow_inf_nan=False, description="Julian day in Terrestrial Time.")
    planet: Planet | None = Field(default=None, description="Omit to query both systems.")


class PlanetaryMoonEventsRequest(BaseModel):
    """Search a TT interval for selected disk events or its first new event."""

    model_config = ConfigDict(extra="forbid")

    jd_start_tt: float = Field(strict=True, allow_inf_nan=False)
    jd_end_tt: float = Field(strict=True, allow_inf_nan=False)
    planet: Planet | None = None
    moon_ids: tuple[Annotated[int, Field(strict=True)], ...] = Field(default=(), max_length=12)
    kinds: tuple[PlanetaryMoonEventKind, ...] = Field(
        default=PLANETARY_MOON_EVENT_KINDS, min_length=1, max_length=3,
    )
    mode: PlanetaryMoonSearchMode = "window"
    max_evaluations: int = Field(
        default=PLANETARY_MOON_DEFAULT_EVALUATIONS, strict=True, ge=1, le=PLANETARY_MOON_MAX_EVALUATIONS,
    )
    max_results: int = Field(default=256, strict=True, ge=1, le=PLANETARY_MOON_MAX_RESULTS)

    @model_validator(mode="after")
    def _bounded_window(self):
        if not 0 < self.jd_end_tt - self.jd_start_tt <= PLANETARY_MOON_MAX_WINDOW_DAYS:
            raise ValueError("Planetary moon search needs an ordered TT window of at most 90 days.")
        return self


class PlanetaryMoonEventsResponse(BaseModel):
    """The search request and its nominal contact and coverage evidence."""

    request: PlanetaryMoonEventsRequest
    result: PlanetaryMoonEventSearch


class _EngineResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EarthMoonViewResponse(_EngineResult):
    """Earth-center view with separate retarded planet and moon states."""

    east_arcsec: float
    north_arcsec: float
    range_offset_km: float
    moon_emission_offset_days: float
    planet_emission_offset_days: float
    side: Literal["near", "far", "same_range"]
    overlap: Literal["clear", "contact", "partial", "contained"]
    event: Literal["transit", "occultation"] | None


class MoonPhaseResponse(_EngineResult):
    """Nominal illuminated fraction and phase angle as seen from the parent center."""

    angle_deg: float
    illuminated_fraction: float
    emission_offset_days: float


class PlanetaryMoonResponse(_EngineResult):
    """Parent-relative ICRF state and observer-dependent geometry for one moon."""

    name: str
    naif_id: int
    planet: Planet
    planet_naif_id: int
    position_km: tuple[float, float, float]
    velocity_km_per_day: tuple[float, float, float]
    distance_km: float
    earth_view: EarthMoonViewResponse
    phase: MoonPhaseResponse
    eclipse: Literal["clear", "contact", "partial", "total"]
    eclipse_epoch_offset_days: float


class PlanetaryMoonSourceResponse(_EngineResult):
    """Provenance for the admitted JPL source and installed satellite extract."""

    planet: Planet
    source_url: str
    source_sha256: str
    extract_sha256: str


class PlanetaryMoonsSnapshotResponse(_EngineResult):
    """State and source receipts for the requested systems at one epoch."""

    jd_tt: float
    jd_tdb: float
    moons: tuple[PlanetaryMoonResponse, ...]
    sources: tuple[PlanetaryMoonSourceResponse, ...]
    de441_sha256: str
    figure_pck_sha256: str


class PlanetaryMoonsCoverageInterval(BaseModel):
    """Closed geometric state interval in TDB Julian days."""

    start_jd_tdb: float
    end_jd_tdb: float


class PlanetaryMoonsSystemCoverage(BaseModel):
    """Joint state coverage for one installed planetary system."""

    planet: Planet
    intervals_tdb: tuple[PlanetaryMoonsCoverageInterval, ...]


class PlanetaryMoonsCoverageResponse(BaseModel):
    """Joint geometric state coverage for the installed systems."""

    systems: tuple[PlanetaryMoonsSystemCoverage, ...]

"""Transport models for the hyleg and alcocoden routes (William Lilly 1647).

Kernel-free: the caller supplies the luminaries, 12 quadrant cusps
(cusps[0] = Ascendant) and sect. ``armc``, ``obliquity`` and
``geographic_latitude`` are needed only when a body or the Part of Fortune is
under the earth in the 1st house (Lilly's 25-degree equatorial limit);
without them that case is refused with 422. The five planets, the preceding
new Moon (day) or full Moon (night) and, by night, which syzygy came last are
needed only when no luminary is hylegiacal (Lilly's dominion step); without
them the result is not_evaluable with a named reason.
"""

from __future__ import annotations

import math

from typing import Literal

from pydantic import Field, StrictBool, field_validator

from moira.longevity import AlcocodenStatus, HylegDoctrine, HylegStatus

from .common import _StrictModel


class HylegLilly1647Request(_StrictModel):
    sun_longitude: float
    moon_longitude: float
    house_cusps: list[float] = Field(min_length=12, max_length=12)
    is_day_chart: StrictBool
    armc: float | None = None
    obliquity: float | None = Field(default=None, ge=0.0, le=90.0)
    geographic_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    planets: dict[Literal["Mercury", "Venus", "Mars", "Jupiter", "Saturn"], float] | None = None
    prenatal_new_moon_longitude: float | None = None
    prenatal_full_moon_longitude: float | None = None
    latest_prenatal_syzygy: Literal["new_moon", "full_moon"] | None = None

    @field_validator("planets")
    @classmethod
    def _finite_planets(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is not None:
            for name, longitude in value.items():
                if not math.isfinite(longitude):
                    raise ValueError(f"planets[{name}] must be finite")
        return value

    @field_validator(
        "sun_longitude", "moon_longitude", "armc", "obliquity", "geographic_latitude",
        "prenatal_new_moon_longitude", "prenatal_full_moon_longitude",
    )
    @classmethod
    def _finite(cls, value: float | None, info) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError(f"{info.field_name} must be finite")
        return value

    @field_validator("house_cusps")
    @classmethod
    def _finite_cusps(cls, value: list[float]) -> list[float]:
        for index, cusp in enumerate(value):
            if not math.isfinite(cusp):
                raise ValueError(f"house_cusps[{index}] must be finite")
        return value


class HylegiacalPlaceResponse(_StrictModel):
    body: str
    longitude: float
    strict_house: int
    orb_house: int
    above_horizon: bool
    oblique_ascension_below_ascendant_deg: float | None
    is_hylegiacal: bool
    reason: str


class HylegDominionCountResponse(_StrictModel):
    planet: str
    dignities_by_place: dict[str, list[str]]
    dignity_count: int
    points: int
    qualifies: bool


class HylegProvenanceResponse(_StrictModel):
    source_module: str = "moira.longevity"
    engine_entrypoint: str = "find_hyleg_lilly_1647"
    source: str = (
        "William Lilly, Christian Astrology (1647), Book III ch. CIV, pp. 527-529; "
        "house orb from Book I ch. IV, pp. 31-32; dominion dignities by the table "
        "of Book I ch. XVIII (p. 104) and the scale of p. 115"
    )
    hylegiacal_houses: list[int] = [1, 7, 9, 10, 11]
    cusp_orb_deg: float = 5.0
    under_earth_limit: str = (
        "1st house only, within 25 degrees of oblique ascension below the Ascendant"
    )
    dominion_places: str = (
        "day: Sun, preceding new Moon, Ascendant; night: Moon, preceding full Moon, "
        "Part of Fortune (Asc + Moon - Sun)"
    )
    dominion_rule: str = (
        "at least three essential dignities over the three places; most points wins; "
        "must stand in a hylegiacal place"
    )
    not_admitted_steps: list[str] = [
        "preference_of_greater_virtue_when_both_luminaries_qualify",
    ]
    house_system: str = "caller_supplied_cusps"
    chart_construction: str = "not_computed"
    sect_determination: str = "caller_supplied"


class HylegLilly1647Response(_StrictModel):
    doctrine: HylegDoctrine
    status: HylegStatus
    hyleg: str | None
    is_day_chart: bool
    candidates: list[HylegiacalPlaceResponse]
    both_luminaries_hylegiacal: bool
    reason: str | None
    selection_step: str | None = None
    hyleg_longitude: float | None = None
    dominion_places: dict[str, float] = Field(default_factory=dict)
    dominion_counts: list[HylegDominionCountResponse] = Field(default_factory=list)
    dominion_planet: str | None = None
    dominion_planet_place: HylegiacalPlaceResponse | None = None
    part_of_fortune_place: HylegiacalPlaceResponse | None = None
    provenance: HylegProvenanceResponse = Field(default_factory=HylegProvenanceResponse)


_CLASSIC_7 = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")


class AlcocodenLilly1647Request(_StrictModel):
    """All seven planets, 12 quadrant cusps and sect; equatorial inputs as for the hyleg."""

    positions: dict[str, float]
    house_cusps: list[float] = Field(min_length=12, max_length=12)
    is_day_chart: StrictBool
    armc: float | None = None
    obliquity: float | None = Field(default=None, ge=0.0, le=90.0)
    geographic_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    prenatal_new_moon_longitude: float | None = None
    prenatal_full_moon_longitude: float | None = None
    latest_prenatal_syzygy: Literal["new_moon", "full_moon"] | None = None

    @field_validator("positions")
    @classmethod
    def _seven_planets(cls, value: dict[str, float]) -> dict[str, float]:
        unknown = sorted(set(value) - set(_CLASSIC_7))
        if unknown:
            raise ValueError(f"positions admits only the seven planets; got {', '.join(unknown)}")
        missing = [name for name in _CLASSIC_7 if name not in value]
        if missing:
            raise ValueError(f"positions missing: {', '.join(missing)}")
        for name, longitude in value.items():
            if not math.isfinite(longitude):
                raise ValueError(f"positions[{name}] must be finite")
        return value

    @field_validator(
        "armc", "obliquity", "geographic_latitude",
        "prenatal_new_moon_longitude", "prenatal_full_moon_longitude",
    )
    @classmethod
    def _finite(cls, value: float | None, info) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError(f"{info.field_name} must be finite")
        return value

    @field_validator("house_cusps")
    @classmethod
    def _finite_cusps(cls, value: list[float]) -> list[float]:
        for index, cusp in enumerate(value):
            if not math.isfinite(cusp):
                raise ValueError(f"house_cusps[{index}] must be finite")
        return value


class AlcocodenCandidateResponse(_StrictModel):
    planet: str
    longitude: float
    essential_points: int
    dignities: list[str]
    aspect_to_hyleg: str | None
    aspect_distance_deg: float | None
    orb_deg: float
    beholds_hyleg: bool
    eastern: bool


class AlcocodenProvenanceResponse(_StrictModel):
    source_module: str = "moira.longevity"
    engine_entrypoint: str = "find_alcocoden_lilly_1647"
    source: str = (
        "William Lilly, Christian Astrology (1647), Book III ch. CIV, pp. 530-531; "
        "essential dignities per Book I ch. XVIII table (p. 104) and scale (p. 115); "
        "planetary orbs and years per Book I chs. VIII-XIV (pp. 57-83)"
    )
    requirement: str = (
        "most essential dignity in the hyleg's degree among planets that behold it "
        "(conjunction, sextile, square, trine, opposition within the planet's own orb); "
        "a luminary hyleg in its own domicile or exaltation is its own alcocoden"
    )
    tie_rule: str = "by day the planet nearer the Ascendant than the Descendant; else not_evaluable"
    reported_not_mechanised: list[str] = [
        "sign_ruler_of_hyleg_as_alcocoden_pp_530_531",
    ]
    granted_years: str = (
        "not_computed: Lilly gives no mechanical rule; he allows the greater years "
        "when the alcocoden is angular, strong and fortunate, especially in the 1st or 10th"
    )
    chart_construction: str = "not_computed"
    sect_determination: str = "caller_supplied"


class AlcocodenLilly1647Response(_StrictModel):
    doctrine: HylegDoctrine
    status: AlcocodenStatus
    hyleg: HylegLilly1647Response
    hyleg_longitude: float | None
    alcocoden: str | None
    selection_basis: str | None
    candidates: list[AlcocodenCandidateResponse]
    sign_ruler_of_hyleg: str | None
    alcocoden_house: int | None
    years_least: float | None
    years_mean: float | None
    years_greater: float | None
    angular_in_first_or_tenth: bool | None
    reason: str | None
    provenance: AlcocodenProvenanceResponse = Field(default_factory=AlcocodenProvenanceResponse)


__all__ = [
    "AlcocodenCandidateResponse",
    "AlcocodenLilly1647Request",
    "AlcocodenLilly1647Response",
    "AlcocodenProvenanceResponse",
    "HylegDominionCountResponse",
    "HylegLilly1647Request",
    "HylegLilly1647Response",
    "HylegProvenanceResponse",
    "HylegiacalPlaceResponse",
]

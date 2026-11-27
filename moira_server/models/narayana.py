"""Typed natal D1 Narayana sequence and active-period transport."""
from typing import Annotated, Literal

from pydantic import Field

from ._vedic_inputs import FiniteNumber, SignIndex
from .common import _StrictModel

_HalfOpenLongitude = Annotated[FiniteNumber, Field(ge=0, lt=360)]
_YearBasis = Literal["julian_365.25", "savana_360", "tropical_365.2422", "sidereal_365.2564"]


class NarayanaProfileResponse(_StrictModel):
    """Discover the admitted source variant and the choices it accepts."""

    profile_id: Literal["rath_book_resolved_strength"]
    source_reference: str
    year_bases: tuple[_YearBasis, ...]
    accepts_resolved_strength: Literal[True]
    accepts_resolved_co_lords: Literal[True]


class NarayanaRequest(_StrictModel):
    """Natal D1 inputs with optional resolved strengths and an explicit UT1 clock."""

    lagna_sidereal_longitude: _HalfOpenLongitude
    sidereal_longitudes: Annotated[dict[str, _HalfOpenLongitude], Field(min_length=9, max_length=9)]
    resolved_strength: Annotated[dict[int, SignIndex], Field(max_length=12)] | None = None
    resolved_co_lords: Annotated[dict[int, Literal["Mars", "Ketu", "Saturn", "Rahu"]], Field(max_length=2)] | None = None
    birth_jd_ut1: FiniteNumber | None = None
    year_basis: _YearBasis | None = None


class NarayanaActiveRequest(NarayanaRequest):
    """The same sequence inputs with a projected UT1 query."""

    birth_jd_ut1: FiniteNumber
    year_basis: _YearBasis
    query_jd_ut1: FiniteNumber


class NarayanaDecisionResponse(_StrictModel):
    """Winner and the comparison rule for two opposing signs."""

    reference_sign: int
    opposite_sign: int
    winner: int | None
    rule: str


class NarayanaPeriodResponse(_StrictModel):
    """A source-year period, projected bounds and optional subperiods."""

    sign_index: int
    cycle: int
    lord: str | None
    source_years_numerator: int
    source_years_denominator: int
    source_start_years: float
    source_end_years: float
    start_jd_ut1: float | None
    end_jd_ut1: float | None
    antardasha_decision: NarayanaDecisionResponse | None
    antardasha_direction: str | None
    antardashas: tuple["NarayanaPeriodResponse", ...]


class NarayanaResponse(_StrictModel):
    """Both complementary cycles and all available decision evidence."""

    profile_id: Literal["rath_book_resolved_strength"]
    source_reference: str
    lagna_sign_index: int
    starting_sign_index: int | None
    starting_decision: NarayanaDecisionResponse
    direction: str | None
    exception: str | None
    major_order: tuple[int, ...]
    resolved_co_lords: dict[int, str | None]
    co_lord_rules: dict[int, str]
    periods: tuple[NarayanaPeriodResponse, ...]
    unresolved: tuple[str, ...]
    year_basis: str | None
    birth_jd_ut1: float | None


class NarayanaActiveResponse(_StrictModel):
    """The projected schedule's active major and optional subperiod."""

    query_jd_ut1: float
    unresolved: tuple[str, ...]
    active: tuple[NarayanaPeriodResponse, ...]

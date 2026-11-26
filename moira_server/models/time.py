"""Transport contracts for Moira's admitted time transformations."""

from __future__ import annotations

from calendar import monthrange
from typing import Annotated, Literal

from pydantic import AwareDatetime, ConfigDict, Field, field_validator, model_validator

from moira.delta_t_physical import DeltaTBreakdown, DeltaTDistribution
from moira.julian import DateTimeToJulianTruth, DeltaTTruth, LocalSiderealTimeTruth, UtcToTtTruth, UtcToUt1Truth

from .chart import CalendarDateTimeResponse
from .common import _StrictModel


TimeScale = Literal["civil_utc", "UTC", "UT1", "TT", "TDB"]
_Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
TIME_CONVERSIONS = frozenset({
    ("civil_utc", "UTC"), ("UTC", "civil_utc"), ("UTC", "UT1"), ("UTC", "TT"),
    ("UT1", "TT"), ("TT", "UT1"), ("TT", "TDB"), ("TDB", "TT"),
})


class TimeConversionRequest(_StrictModel):
    """One directed conversion between explicitly selected scales.

    RITE:
        Validate the time scales and epoch representation at the REST boundary.

    THEOREM:
        An admitted request names a pair in TIME_CONVERSIONS and supplies
        exactly one epoch representation appropriate to its source scale.

    RITE OF PURPOSE:
        Give the conversion service a validated direction and source epoch.

    LAW OF OPERATION:
        Require an offset-aware dt for civil_utc and a finite numeric jd for
        every other source scale. Reject numeric dt inputs, unsupported scale
        pairs, extra fields, and missing or conflicting epoch inputs.
        Pydantic and _StrictModel govern validation. The time service owns
        the conversion itself. Validators read the request fields without
        mutating them or accessing external data.

    Canon: TIME_CONVERSIONS and the POST /v1/time/convert request contract.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.server.models.time.TimeConversionRequest",
      "risk": "low",
      "api": {
        "frozen": ["source_scale", "target_scale", "jd", "dt"],
        "internal": ["_reject_numeric_epoch", "_conversion_inputs"]
      },
      "state": {"mutable": true, "owners": ["TimeConversionRequest instance"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise", "invalid_input": "pydantic.ValidationError"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": []}
    }
    [/MACHINE_CONTRACT]
    """

    model_config = ConfigDict(
        json_schema_extra={"description": "One directed conversion between explicitly selected scales."},
    )

    source_scale: TimeScale
    target_scale: TimeScale
    jd: _Finite | None = None
    dt: AwareDatetime | None = None

    @field_validator("dt", mode="before")
    @classmethod
    def _reject_numeric_epoch(cls, value):
        if isinstance(value, (int, float)):
            raise ValueError("dt must be a civil datetime with an explicit offset")
        return value

    @model_validator(mode="after")
    def _conversion_inputs(self):
        if (self.source_scale, self.target_scale) not in TIME_CONVERSIONS:
            raise ValueError("unsupported directed time conversion")
        if self.source_scale == "civil_utc":
            if self.dt is None or self.jd is not None:
                raise ValueError("civil_utc input requires dt alone")
        elif self.jd is None or self.dt is not None:
            raise ValueError("Julian-day input requires jd alone")
        return self


class GregorianCalendarInput(_StrictModel):
    """Proleptic Gregorian UTC date and time with astronomical year numbering.

    RITE:
        Validate one structured civil date and its UTC clock fields.

    THEOREM:
        The day must exist in the requested proleptic Gregorian month.

    RITE OF PURPOSE:
        Represent year zero, BCE dates and years beyond Python datetime.

    LAW OF OPERATION:
        Pydantic validates integer field ranges. The standard library's
        calendar.monthrange checks the month length for the supplied year.
        The validator reads the fields directly and raises on an invalid day.

    Canon: Gregorian month lengths and astronomical year numbering.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.server.models.time.GregorianCalendarInput",
      "risk": "low",
      "api": {
        "frozen": ["year", "month", "day", "hour", "minute", "second", "microsecond"],
        "internal": ["_validate_day_of_month"]
      },
      "state": {"mutable": true, "owners": ["GregorianCalendarInput instance"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise", "invalid_input": "pydantic.ValidationError"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": []}
    }
    [/MACHINE_CONTRACT]
    """

    model_config = ConfigDict(
        json_schema_extra={"description": "Proleptic Gregorian UTC date and time with astronomical year numbering."},
    )

    year: int = Field(strict=True, ge=-100_000, le=100_000)
    month: int = Field(strict=True, ge=1, le=12)
    day: int = Field(strict=True, ge=1, le=31)
    hour: int = Field(default=0, strict=True, ge=0, le=23)
    minute: int = Field(default=0, strict=True, ge=0, le=59)
    second: int = Field(default=0, strict=True, ge=0, le=59)
    microsecond: int = Field(default=0, strict=True, ge=0, le=999_999)

    @model_validator(mode="after")
    def _validate_day_of_month(self):
        if self.day > monthrange(self.year, self.month)[1]:
            raise ValueError("day must exist in the supplied proleptic Gregorian month")
        return self


class CalendarTimeConversionRequest(_StrictModel):
    """Convert one structured UTC calendar instant to a civil Julian day."""

    source_scale: Literal["civil_utc"]
    target_scale: Literal["UTC"]
    calendar: GregorianCalendarInput


TimeConversionInput = TimeConversionRequest | CalendarTimeConversionRequest


class TimeConversionResponse(_StrictModel):
    """A converted epoch with its scale selection and canonical source evidence."""

    request: TimeConversionInput
    jd: float | None = None
    calendar_utc: CalendarDateTimeResponse | None = None
    model: str
    provenance: DateTimeToJulianTruth | UtcToUt1Truth | UtcToTtTruth | DeltaTTruth | None = None


class DeltaTEstimateRequest(_StrictModel):
    """Evaluate the active Delta-T source for a UT1 epoch."""

    kind: Literal["estimate"]
    jd_ut1: _Finite


class DeltaTBreakdownRequest(_StrictModel):
    """Describe the canonical Delta-T model at a decimal year."""

    kind: Literal["breakdown", "distribution"]
    year: _Finite


DeltaTRequest = Annotated[DeltaTEstimateRequest | DeltaTBreakdownRequest, Field(discriminator="kind")]


class DeltaTResponse(_StrictModel):
    """Source estimate or decimal-year model components and policy scale, in seconds."""

    request: DeltaTRequest
    result: DeltaTTruth | DeltaTBreakdown | DeltaTDistribution
    units: Literal["seconds"] = "seconds"
    uncertainty_interpretation: Literal["normal_approximation_with_model_policy_scale"] | None = None


class _SiderealTimeRequest(_StrictModel):
    """Explicit UT1 and TT Julian days for one instant and sidereal mode."""

    jd_ut1: _Finite
    jd_tt: _Finite
    mode: Literal["mean", "apparent"]


class GreenwichSiderealTimeRequest(_SiderealTimeRequest):
    """Evaluate sidereal time on the Greenwich meridian."""

    reference: Literal["greenwich"]


class LocalSiderealTimeRequest(_SiderealTimeRequest):
    """Evaluate sidereal time on the supplied east-positive meridian."""

    reference: Literal["local"]
    longitude_deg_east: Annotated[_Finite, Field(ge=-180.0, le=180.0)]


SiderealTimeRequest = Annotated[
    GreenwichSiderealTimeRequest | LocalSiderealTimeRequest, Field(discriminator="reference")
]


class SiderealTimeResponse(_StrictModel):
    """Sidereal angle in [0, 360) degrees with the canonical reduction truth."""

    request: SiderealTimeRequest
    sidereal_time_deg: float
    provenance: LocalSiderealTimeTruth

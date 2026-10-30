"""
Moira — julian.py
The Julian Day Engine: governs all conversions between calendar dates,
Julian Day Numbers, and the time scales used by the DE441 ephemeris.
Civil UTC and astronomical UT1 remain distinct.  UTC-to-UT1 conversion uses
the bundled Earth-orientation record when it covers the requested instant;
UT1-to-TT conversion uses the same record through a continuous Delta-T surface.

Boundary: owns the full pipeline from Python datetime / calendar tuple to
Julian Day (JD), Terrestrial Time (TT), and sidereal time. Delegates
long-range ΔT table loading to the bundled data file
``moira/data/delta_t_hpiers_2016.txt`` at import time. Does not own
coordinate transforms, house calculations, or any display formatting.

Public surface:
    CalendarDateTime, DeltaTPolicy,
    DateTimeToJulianTruth, JulianToDateTimeTruth,
    DeltaTTidalBasisTruth, DeltaTTruth, UtcToUt1Truth, UtcToTtTruth,
    LocalSiderealTimeTruth,
    format_calendar_utc, format_jd_utc,
    julian_day, calendar_from_jd,
    jd_from_datetime, jd_from_datetime_with_truth,
    decimal_year, decimal_year_from_jd,
    calendar_datetime_from_jd, safe_datetime_from_jd,
    datetime_from_jd, datetime_from_jd_with_truth,
    centuries_from_j2000,
    delta_t, delta_t_from_jd, delta_t_from_jd_with_truth, delta_t_nasa_canon,
    ut_to_tt, ut_to_tt_nasa_canon, tt_to_ut, tt_to_ut_nasa_canon,
    utc_to_ut1, utc_to_ut1_with_truth, utc_to_tt, utc_to_tt_with_truth,
    tt_to_tdb,
    greenwich_mean_sidereal_time, apparent_sidereal_time,
    apparent_sidereal_time_at, local_sidereal_time,
    local_sidereal_time_with_truth

Import-time side effects:
    Reads ``moira/data/delta_t_hpiers_2016.txt`` once at module load to
    populate ``_DELTA_T_HPIERS_2016``. No network I/O; no other side effects.

External dependency assumptions:
    stdlib math and datetime only (plus pathlib for the data-file load).
    No jplephem, no Qt, no third-party packages.
"""

from __future__ import annotations

import math
import bisect
from numbers import Real
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from .dispatch import accelerate
from .constants import J2000, JULIAN_CENTURY, TAI_TT_OFFSET
from .data.leap_seconds import LEAP_SECONDS


def _require_finite(name: str, value: float) -> None:
    """Reject non-finite public time coordinates before calendar arithmetic."""

    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite, got {value!r}")


# Computational guard, not a scientific-validity claim.  It comfortably
# contains every admitted kernel span while keeping binary64 JD resolution
# below a millisecond at the boundary.
_MAX_ABS_DELTA_T_YEAR: float = 100_000.0
_MAX_ABS_TIME_JD: float = 40_000_000.0
# Continuous UTC (effective 2027-05-20) permits |UT1-UTC| up to 3600 s.
_MAX_ABS_DUT1_SECONDS: float = 3600.0


def _require_representable_delta_t_year(year: float) -> None:
    _require_finite("year", year)
    if abs(float(year)) > _MAX_ABS_DELTA_T_YEAR:
        raise ValueError(
            "year lies outside Moira's representable Delta-T domain "
            f"[-{_MAX_ABS_DELTA_T_YEAR:g}, {_MAX_ABS_DELTA_T_YEAR:g}]: {year!r}"
        )


def _require_representable_time_jd(name: str, jd: float) -> None:
    _require_finite(name, jd)
    if abs(float(jd)) > _MAX_ABS_TIME_JD:
        raise ValueError(
            f"{name} lies outside Moira's representable time-transform domain "
            f"[-{_MAX_ABS_TIME_JD:g}, {_MAX_ABS_TIME_JD:g}]: {jd!r}"
        )


# Historical/telescopic ΔT anchors retained for the pre-HPIERS polynomial
# fallback domain.  The admitted HPIERS table takes precedence wherever its
# published coverage exists.
# Source: NASA Eclipse Web Site, "Historical Values of Delta T (ΔT)",
# adapted from Espenak & Meeus and Morrison & Stephenson historical records.
# These values extend the table-driven regime backward instead of leaving the
# entire 1600–1955 span on piecewise polynomials.
_DELTA_T_HISTORICAL: tuple[tuple[float, float], ...] = (
    (1600.0, 120.0),
    (1700.0, 9.0),
    (1750.0, 13.0),
    (1800.0, 14.0),
    (1850.0, 7.0),
)

# Denser pre-1955 transition table.
# The 1900–1955 span is much more sensitive in strict apparent-position
# validation, especially for the Moon. Using only coarse 1900/1950 anchors
# introduces several arcseconds of artificial error. These 5-year anchors
# preserve the historical curve closely while still moving more of the modern
# era into table-driven interpolation.
_DELTA_T_PRE1955_5Y: tuple[tuple[float, float], ...] = (
    (1900.0, -2.7900),
    (1905.0, 3.8347),
    (1910.0, 10.3884),
    (1915.0, 17.0861),
    (1920.0, 21.2000),
    (1925.0, 23.7839),
    (1930.0, 24.1329),
    (1935.0, 23.8174),
    (1940.0, 24.4074),
    (1945.0, 26.8786),
    (1950.0, 29.0700),
    (1955.0, 31.0468),
)

# Annual mean ΔT (TT − UT1, seconds) from USNO deltat.data (maia.usno.navy.mil/ser7/deltat.data).
# Values are 12-month arithmetic means of monthly observations. Finer resolution replaces the
# coarse 5-year table for the modern era.
# 2015–2025: fully observed (all 12 months averaged from USNO deltat.data).
# 2026: partial-year mean of Jan–Apr from USNO/IERS Bulletin A+B as of 2026-04-25.
#   Jan=69.1099, Feb=69.1133, Mar=69.1168, Apr=69.1330 → 4-month mean=69.12.
#   Update to the 12-month mean once December 2026 Bulletin B is published (~Jan 2027).
def _monthly_mean_representative_epoch(year: int, month_count: int) -> float:
    """Return the mean decimal epoch of first-of-month source samples."""

    if not 1 <= month_count <= 12:
        raise RuntimeError("Delta-T monthly sample count must be in 1..12")
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    month_lengths = (
        31,
        29 if leap else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    starts = [0]
    for days in month_lengths[:-1]:
        starts.append(starts[-1] + days)
    mean_day_offset = math.fsum(starts[:month_count]) / month_count
    return year + mean_day_offset / math.fsum(month_lengths)


# The first coordinate is the mean epoch of the first-of-month observations
# included in each arithmetic mean, not the integer product label.  The final
# coordinate is the mean epoch of the four Jan-Apr 2026 source samples.
_DELTA_T_ANNUAL: tuple[tuple[float, float], ...] = (
    (_monthly_mean_representative_epoch(2015, 12), 67.84),
    (_monthly_mean_representative_epoch(2016, 12), 68.35),
    (_monthly_mean_representative_epoch(2017, 12), 68.78),
    (_monthly_mean_representative_epoch(2018, 12), 69.09),
    (_monthly_mean_representative_epoch(2019, 12), 69.32),
    (_monthly_mean_representative_epoch(2020, 12), 69.39),
    (_monthly_mean_representative_epoch(2021, 12), 69.33),
    (_monthly_mean_representative_epoch(2022, 12), 69.25),
    (_monthly_mean_representative_epoch(2023, 12), 69.20),
    (_monthly_mean_representative_epoch(2024, 12), 69.17),
    (_monthly_mean_representative_epoch(2025, 12), 69.13),
    (_monthly_mean_representative_epoch(2026, 4), 69.12),
)


@dataclass(frozen=True, slots=True)
class _DeltaTObservationBoundary:
    """Single non-recursive owner of the observed-to-scenario handoff."""

    year: float
    total: float
    slope: float


def _delta_t_observation_boundary() -> _DeltaTObservationBoundary:
    """Return the final aggregate value and representative-epoch slope.

    This helper deliberately reads the admitted annual table directly.  It
    must never call :func:`delta_t`, because the post-observation branch of
    that function delegates to ``delta_t_physical``.  The slope divides the
    final two representative sample epochs; because the current final row is
    a Jan-Apr partial mean, it remains provisional scenario policy rather than
    an observed instantaneous derivative.
    """

    if len(_DELTA_T_ANNUAL) < 2:
        raise RuntimeError("Delta-T annual boundary requires at least two rows")
    previous_year: float | None = None
    for year, total in _DELTA_T_ANNUAL:
        if not math.isfinite(year) or not math.isfinite(total):
            raise RuntimeError("Delta-T annual boundary contains a non-finite row")
        if previous_year is not None and year <= previous_year:
            raise RuntimeError(
                "Delta-T aggregate representative epochs must be strictly increasing"
            )
        previous_year = year

    year0, total0 = _DELTA_T_ANNUAL[-2]
    year1, total1 = _DELTA_T_ANNUAL[-1]
    return _DeltaTObservationBoundary(
        year=year1,
        total=total1,
        slope=(total1 - total0) / (year1 - year0),
    )


_HPIERS_EXPECTED_DATA_ROWS: int = 348
_HPIERS_MODERN_HALF_YEAR_EPOCHS: tuple[float, ...] = tuple(
    1950.0 + 0.5 * index for index in range(133)
)
# These are explicit compatibility choices for conflicting published rows,
# not rounded modern half-year labels.  The 1850 row is a precision/regime
# join; -1600 is a duplicate inside one extrapolated regime whose later value
# remains established Moira policy rather than source-derived truth.
_HPIERS_LATER_ROW_CONFLICT_EPOCHS: frozenset[float] = frozenset(
    {-1600.0, 1850.0}
)


def _load_delta_t_hpiers_2016(
    path: Path | None = None,
) -> tuple[tuple[float, float], ...]:
    """
    Load the official HPIERS/HMNAO Delta T table derived from the 2016
    Stephenson-Morrison-Hohenkerk historical rotation model.

    The text file stores rows as:
        year  delta_t_seconds  quoted_error_seconds  ...

    The source-declared 1950--2016 half-year cadence is stored with explicit
    decimal epochs.  Exact duplicate rows are harmless; the two known
    conflicting source-boundary epochs use an explicit later-row policy.
    Unknown conflicting duplicates fail closed.  The quoted error is parsed
    here even though the canonical mean surface does not consume it, so a
    damaged authority row cannot be admitted by this loader while the
    physical-policy loader rejects it.
    """
    packaged_source = path is None
    if path is None:
        path = Path(__file__).resolve().parent / "data" / "delta_t_hpiers_2016.txt"
    if not path.exists():
        raise FileNotFoundError(f"Required Delta-T authority table is missing: {path}")

    rows: dict[float, tuple[float, float]] = {}
    previous_year: float | None = None
    data_rows = 0
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 3:
            raise ValueError(
                f"{path}:{line_number}: expected year, Delta-T, and quoted error"
            )
        try:
            year = float(parts[0])
            dt = float(parts[1])
            error = float(parts[2])
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: non-numeric Delta-T row") from exc
        if not all(math.isfinite(value) for value in (year, dt, error)):
            raise ValueError(f"{path}:{line_number}: non-finite Delta-T row")
        if error < 0.0:
            raise ValueError(f"{path}:{line_number}: negative quoted error")
        if previous_year is not None and year < previous_year:
            raise ValueError(f"{path}:{line_number}: source epochs are not non-decreasing")
        previous_year = year
        data_rows += 1
        previous = rows.get(year)
        current = (dt, error)
        if (
            previous is not None
            and previous != current
            and year not in _HPIERS_LATER_ROW_CONFLICT_EPOCHS
        ):
            raise ValueError(
                f"{path}:{line_number}: conflicting duplicate Delta-T epoch {year:g}"
            )
        rows[year] = current

    if data_rows == 0:
        raise ValueError(f"Required Delta-T authority table is empty: {path}")
    if packaged_source and data_rows != _HPIERS_EXPECTED_DATA_ROWS:
        raise ValueError(
            f"Unexpected HPIERS row count {data_rows}; "
            f"expected {_HPIERS_EXPECTED_DATA_ROWS}"
        )
    modern_epochs = tuple(
        year for year in sorted(rows) if 1950.0 <= year <= 2016.0
    )
    if packaged_source and modern_epochs != _HPIERS_MODERN_HALF_YEAR_EPOCHS:
        raise ValueError(
            "HPIERS 1950--2016 epochs do not preserve the declared "
            "half-year cadence"
        )
    table = tuple((year, values[0]) for year, values in sorted(rows.items()))
    if table[0][0] != -2000.0 or table[-1][0] != 2016.0:
        raise ValueError(
            f"Unexpected HPIERS coverage {table[0][0]:g}..{table[-1][0]:g}; "
            "expected -2000..2016"
        )
    return table


_DELTA_T_HPIERS_2016: tuple[tuple[float, float], ...] = _load_delta_t_hpiers_2016()


def _interpolate_delta_t_table(
    table: tuple[tuple[float, float], ...],
    year: float,
) -> float:
    """Linearly interpolate a finite year inside a non-empty ordered table."""

    if not table:
        raise RuntimeError("Delta-T interpolation table is empty")
    if year < table[0][0] or year > table[-1][0]:
        raise ValueError(
            f"Delta-T interpolation year {year:g} lies outside "
            f"{table[0][0]:g}..{table[-1][0]:g}"
        )
    if year == table[-1][0]:
        return table[-1][1]
    for (year0, total0), (year1, total1) in zip(table, table[1:]):
        if year0 <= year <= year1:
            fraction = (year - year0) / (year1 - year0)
            return total0 + fraction * (total1 - total0)
    raise RuntimeError("Delta-T interpolation failed inside declared coverage")


def _delta_t_hpiers_annual_bridge() -> tuple[tuple[float, float], ...]:
    """Return the explicit C0 bridge into the first admitted aggregate.

    HPIERS owns the mean through its final distinct knot before the monthly-
    source aggregate table begins. The one source interval between that knot
    and the first aggregate representative epoch is an explicit linear
    reconciliation, rather than an abrupt source switch or a hidden return to
    the superseded coarse five-year table.
    """

    annual_start = _DELTA_T_ANNUAL[0]
    preceding = tuple(
        row for row in _DELTA_T_HPIERS_2016 if row[0] < annual_start[0]
    )
    if not preceding:
        raise RuntimeError(
            "HPIERS Delta-T data does not precede the first annual boundary"
        )
    return (preceding[-1], annual_start)


@dataclass(frozen=True, slots=True)
class CalendarDateTime:
    """
    RITE: The Calendar Vessel — immutable carrier of a BCE-safe proleptic
    Gregorian date-time.

    THEOREM: Governs the representation of a calendar instant across the full
    astronomical date range, including BCE years and year-0, as a frozen
    dataclass with ISO-8601-compatible formatting methods.

    RITE OF PURPOSE:
        Python's ``datetime`` type cannot represent dates before year 1 AD,
        which makes it unsuitable for historical and ancient astrological
        computation. CalendarDateTime fills that gap: it is the canonical
        result vessel for any JD-to-calendar conversion in Moira, carrying
        year, month, day, and sub-second time fields in a single immutable
        object that can be safely passed across module boundaries without
        mutation risk.

    LAW OF OPERATION:
        Responsibilities:
            - Store a proleptic Gregorian calendar instant with microsecond
              precision, using astronomical year numbering (year 0 = 1 BC).
            - Provide ISO-8601-style string formatting for both CE and BCE
              dates via ``isoformat()``, ``date_string()``, and
              ``time_string()``.
        Non-responsibilities:
            - Does not perform any calendar arithmetic or JD conversion.
            - Does not validate field ranges (month 1–12, day 1–31, etc.);
              callers are responsible for supplying well-formed values.
            - Does not handle time-zone offsets other than UTC.
        Dependencies:
            - Python stdlib ``dataclasses`` (frozen, slots).
        Structural invariants:
            - All fields are immutable after construction (frozen=True).
            - ``tzname`` is always ``"UTC"``; no other time zone is stored.
        Behavioral invariants:
            - ``isoformat()`` always returns a string ending in ``+00:00``.
            - ``date_string()`` zero-pads year to at least 4 digits and
              prepends ``"-"`` for negative (BCE) years.
        Failure behavior:
            - No exceptions are raised by the formatting methods; they are
              pure string operations on already-stored integer fields.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.julian.CalendarDateTime",
      "risk": "medium",
      "api": {
        "frozen": ["isoformat", "date_string", "time_string", "is_leap_second"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["CalendarDateTime"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]

    Uses astronomical year numbering:
      1 AD  -> year=1
      1 BC  -> year=0
      2 BC  -> year=-1
    """

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    microsecond: int = 0
    tzname: str = "UTC"

    def isoformat(self) -> str:
        """Return an ISO-8601 UTC string with microseconds, BCE-safe (e.g. ``-0044-03-15T12:00:00.000000+00:00``)."""
        sign = "-" if self.year < 0 else ""
        year_abs = abs(self.year)
        return (
            f"{sign}{year_abs:04d}-{self.month:02d}-{self.day:02d}T"
            f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"
            f".{self.microsecond:06d}+00:00"
        )

    def date_string(self) -> str:
        """Return a zero-padded date string ``YYYY-MM-DD``, prefixed with ``"-"`` for BCE years."""
        sign = "-" if self.year < 0 else ""
        year_abs = abs(self.year)
        return f"{sign}{year_abs:04d}-{self.month:02d}-{self.day:02d}"

    def time_string(self) -> str:
        """Return a zero-padded time string ``HH:MM:SS``."""
        return f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"

    @property
    def is_leap_second(self) -> bool:
        """True for an inserted leap second (``23:59:60.x``), which ``datetime`` cannot hold."""
        return self.second == 60


@dataclass(frozen=True, slots=True)
class DateTimeToJulianTruth:
    """Inspectable civil-datetime to UTC-coded Julian-date conversion."""

    input_datetime: datetime
    normalized_datetime_utc: datetime
    jd_utc: float
    source_scale: str = "civil_datetime_with_explicit_offset"
    target_scale: str = "UTC_coded_civil_JD"
    scale_conversion_applied: bool = True


@dataclass(frozen=True, slots=True)
class JulianToDateTimeTruth:
    """Inspectable calendar decomposition of one caller-labelled Julian date."""

    jd: float
    input_scale: str
    calendar_datetime: datetime
    calendar: str = "proleptic_Gregorian"
    python_timezone_container: str = "datetime.timezone.utc_label_only"
    scale_conversion_applied: bool = False


@dataclass(frozen=True, slots=True)
class DeltaTTidalBasisTruth:
    """Public representation of one source-owned Delta-T tidal-basis term."""

    source_product: str
    epoch_year: float
    source_ndot_arcsec_per_cy2: float
    coefficient: float


@dataclass(frozen=True, slots=True)
class DeltaTTruth:
    """Inspectable Delta-T result with source and tidal-basis policy."""

    jd_ut1: float
    seconds: float
    source_product: str
    retarget_mode: str
    tidal_terms: tuple[DeltaTTidalBasisTruth, ...]
    input_timescale: str = "UT1"
    output_quantity: str = "TT_minus_UT1_seconds"


@dataclass(frozen=True, slots=True)
class UtcToUt1Truth:
    """Inspectable UTC-to-UT1 conversion and its selected data branch."""

    jd_utc: float
    jd_ut1: float
    dut1_seconds: float
    source_mode: str
    admitted_eop_applied: bool
    historical_proxy_applied: bool
    delta_t_source_product: str | None
    source_scale: str = "UTC"
    target_scale: str = "UT1"


@dataclass(frozen=True, slots=True)
class UtcToTtTruth:
    """Inspectable UTC-to-TT conversion and its civil-clock policy."""

    jd_utc: float
    jd_ut1: float
    jd_tt: float
    delta_t_seconds: float
    delta_t_source_product: str
    conversion_mode: str
    tai_minus_utc_seconds: float | None
    delta_t_applied_to_tt_conversion: bool
    source_scale: str = "UTC"
    target_scale: str = "TT"


@dataclass(frozen=True, slots=True)
class LocalSiderealTimeTruth:
    """Explicit mean/apparent local sidereal-time reduction."""

    jd_ut1: float
    jd_tt: float
    longitude_deg_east: float
    requested_mode: str
    effective_mode: str
    local_sidereal_time_deg: float
    greenwich_mean_sidereal_time_deg: float
    equation_of_equinoxes_deg: float
    nutation_longitude_deg: float | None
    equation_of_equinoxes_obliquity_deg: float | None
    nutation_source: str
    input_timescale: str = "UT1"
    equinox_terms_timescale: str = "TT"
    mean_sidereal_model: str = "IAU_2006_ERA_plus_equinox_precession"
    equation_of_equinoxes_model: str = "IAU_2000A_with_IERS_2010_complementary_terms"


def format_calendar_utc(
    cal: CalendarDateTime,
    *,
    include_time: bool = True,
    include_seconds: bool = False,
) -> str:
    """Format a BCE-safe UTC calendar object for display."""
    date_part = cal.date_string()
    if not include_time:
        return date_part
    if include_seconds:
        return f"{date_part} {cal.time_string()} UTC"
    return f"{date_part} {cal.hour:02d}:{cal.minute:02d} UTC"


def format_jd_utc(
    jd: float,
    *,
    include_time: bool = True,
    include_seconds: bool = False,
) -> str:
    """Format a JD as a BCE-safe UTC string."""
    return format_calendar_utc(
        calendar_datetime_from_jd(jd),
        include_time=include_time,
        include_seconds=include_seconds,
    )

# ---------------------------------------------------------------------------
# Julian Day Number
# ---------------------------------------------------------------------------

@accelerate("julian_day")
def julian_day(year: int, month: int, day: int, hour: float = 0.0) -> float:
    """
    Convert a proleptic Gregorian calendar date and decimal UT hour to a
    Julian Day Number (JD).

    Governs the standard Meeus algorithm (Astronomical Algorithms, ch. 7),
    valid for any proleptic Gregorian date including dates before the 1582
    Gregorian reform. The result is a continuous real number where the integer
    part changes at noon UT (JD epoch = noon, 1 Jan 4713 BC).

    Args:
        year:  Astronomical year number (0 = 1 BC, -1 = 2 BC, etc.).
        month: Month number 1–12.
        day:   Day of month 1–31.
        hour:  Decimal UT hours in [0, 24).

    Returns:
        Julian Day Number as a float (fractional day since JD epoch).

    Raises:
        Nothing — no input validation is performed; callers must supply
        well-formed Gregorian dates.

    Side effects:
        None.
    """
    if month <= 2:
        year -= 1
        month += 12

    A = math.floor(year / 100.0)
    B = 2 - A + math.floor(A / 4.0)

    jd = (math.floor(365.25 * (year + 4716))
          + math.floor(30.6001 * (month + 1))
          + day + B - 1524.5
          + hour / 24.0)
    return jd


@accelerate("calendar_from_jd")
def calendar_from_jd(jd: float) -> tuple[int, int, int, float]:
    """
    Convert a Julian Day Number to a proleptic Gregorian calendar date.

    Governs the proleptic Gregorian inverse of Meeus ch. 7, applying the
    alpha/A correction for ALL dates — not just post-reform dates. This keeps
    the function consistent with ``julian_day``, which also uses the proleptic
    Gregorian formula (B = 2 − A + floor(A/4)) for all epochs. Round-trips
    ``julian_day(y, m, d) → calendar_from_jd → (y, m, d)`` are exact for any
    epoch including year 0 and deep historical JDs.

    Args:
        jd: Julian Day Number (fractional days since JD epoch).

    Returns:
        A 4-tuple ``(year, month, day, decimal_hour)`` in proleptic Gregorian
        calendar with astronomical year numbering. ``decimal_hour`` is in
        [0, 24).

    Raises:
        Nothing — pure arithmetic; no domain restriction is enforced.

    Side effects:
        None.
    """
    jd = jd + 0.5
    Z = math.floor(jd)
    F = jd - Z

    alpha = math.floor((Z - 1867216.25) / 36524.25)
    A = Z + 1 + alpha - math.floor(alpha / 4.0)

    B = A + 1524
    C = math.floor((B - 122.1) / 365.25)
    D = math.floor(365.25 * C)
    E = math.floor((B - D) / 30.6001)

    day   = B - D - math.floor(30.6001 * E)
    month = E - 1 if E < 14 else E - 13
    year  = C - 4716 if month > 2 else C - 4715
    hour  = F * 24.0

    return int(year), int(month), int(day), hour


def jd_from_datetime(dt: datetime) -> float:
    """
    Convert a Python ``datetime`` to a UTC-coded civil Julian Day Number.

    The input must be timezone-aware. The datetime is converted to UTC before
    the Julian Day is calculated. The result is still a civil coordinate, not
    automatically UT1 or TT; pass it through :func:`utc_to_ut1` or
    :func:`utc_to_tt` before an astronomical reduction. For dates before the
    admitted leap-second era, those adapters explicitly preserve Moira's
    historical convention that a civil JD is a UT1 proxy.

    Args:
        dt: A timezone-aware Python ``datetime``.

    Returns:
        UTC-coded civil Julian Day Number as a float.

    Raises:
        ValueError: If ``dt`` is naive and therefore ambiguous.

    Side effects:
        None.
    """
    if dt.tzinfo is None:
        raise ValueError(
            "jd_from_datetime requires a timezone-aware datetime; "
            "pass an explicit tzinfo instead of relying on an implicit UTC assumption."
        )
    dt = dt.astimezone(timezone.utc)

    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3_600_000_000.0
    return julian_day(dt.year, dt.month, dt.day, hour)


def jd_from_datetime_with_truth(dt: datetime) -> DateTimeToJulianTruth:
    """Return the legacy UTC-coded JD together with its civil-time conversion truth."""

    jd_utc = jd_from_datetime(dt)
    normalized = dt.astimezone(timezone.utc)
    return DateTimeToJulianTruth(
        input_datetime=dt,
        normalized_datetime_utc=normalized,
        jd_utc=jd_utc,
    )


def decimal_year(year: int, month: int = 1) -> float:
    """
    Convert a calendar year and month to a NASA eclipse-site decimal year.

    Uses the convention ``y = year + (month − 0.5) / 12``, which places the
    decimal midpoint of each month at its centre rather than its start.

    Args:
        year:  Integer calendar year (astronomical numbering).
        month: Month number 1–12 (default 1 = January).

    Returns:
        Decimal year as a float.

    Side effects:
        None.
    """
    return year + (month - 0.5) / 12.0


def decimal_year_from_jd(jd: float) -> float:
    """Return the NASA-style decimal year corresponding to a Julian day."""
    year, month, _day, _hour = calendar_from_jd(jd)
    return decimal_year(year, month)


def _continuous_decimal_year_from_jd(jd: float) -> float:
    """Return an exact proleptic-Gregorian year coordinate for a JD.

    ``decimal_year_from_jd()`` deliberately preserves NASA's month-midpoint
    convention and is therefore stepwise.  A time-scale transform cannot use
    that reporting convention: a monthly Delta-T step makes the UT1-to-TT map
    discontinuous and, at some epochs, non-injective.  This private coordinate
    measures the exact fraction between consecutive January 1 boundaries.
    """

    _require_representable_time_jd("jd", jd)
    year, _month, _day, _hour = calendar_from_jd(jd)
    year_start = julian_day(year, 1, 1, 0.0)
    next_year_start = julian_day(year + 1, 1, 1, 0.0)
    span = next_year_start - year_start
    if not math.isfinite(span) or span <= 0.0:
        raise ValueError(f"jd has no resolvable calendar-year span: {jd!r}")
    return year + (jd - year_start) / span


def calendar_datetime_from_jd(jd: float) -> CalendarDateTime:
    """
    Convert a Julian Day Number (UT) to a BCE-safe ``CalendarDateTime`` vessel.

    Governs the full decomposition of a fractional JD into integer year,
    month, day, hour, minute, second, and microsecond fields, including
    carry-over correction when floating-point rounding pushes microseconds
    to 1 000 000 or seconds/minutes to 60.

    Args:
        jd: Julian Day Number in UT (fractional days).

    Returns:
        A frozen ``CalendarDateTime`` with all fields populated and tzname
        set to ``"UTC"``.

    Raises:
        Nothing — pure arithmetic.

    Side effects:
        None.
    """
    year, month, day, hour = calendar_from_jd(jd)
    h = int(hour)
    remainder = (hour - h) * 60.0
    m = int(remainder)
    remainder = (remainder - m) * 60.0
    s = int(remainder)
    us = round((remainder - s) * 1_000_000)
    if us == 1_000_000:
        us = 0
        s += 1
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        h += 1
    if h == 24:
        h = 0
        next_midnight = julian_day(year, month, day, 0.0) + 1.0
        year, month, day, _hour = calendar_from_jd(next_midnight)
    return CalendarDateTime(year, month, day, h, m, s, us)


def safe_datetime_from_jd(jd: float) -> datetime | None:
    """
    Convert a JD to a UTC ``datetime``, returning ``None`` for out-of-range years.

    Python's ``datetime`` only supports years 1–9999. This function returns
    ``None`` rather than raising when the JD maps to a year outside that range,
    making it safe to call for any astronomical date.

    Args:
        jd: Julian Day Number in UT.

    Returns:
        A timezone-aware UTC ``datetime`` for CE years 1–9999, or ``None``
        for BCE dates and years beyond 9999.

    Side effects:
        None.
    """
    cal = calendar_datetime_from_jd(jd)
    if not (1 <= cal.year <= 9999):
        return None
    return datetime(
        cal.year,
        cal.month,
        cal.day,
        cal.hour,
        cal.minute,
        cal.second,
        cal.microsecond,
        tzinfo=timezone.utc,
    )


def datetime_from_jd(jd: float) -> datetime:
    """
    Convert a Julian Day Number (UT) to a UTC ``datetime`` for CE years only.

    Enforces that the result is representable by Python's ``datetime`` type.
    Callers that need BCE or year-0 support must use
    ``calendar_datetime_from_jd()`` instead.

    Args:
        jd: Julian Day Number in UT.

    Returns:
        A timezone-aware UTC ``datetime``.

    Raises:
        ValueError: If the JD maps to an astronomical year outside 1–9999.

    Side effects:
        None.
    """
    dt = safe_datetime_from_jd(jd)
    if dt is None:
        cal = calendar_datetime_from_jd(jd)
        raise ValueError(
            f"datetime_from_jd cannot represent astronomical year {cal.year}; "
            "use calendar_datetime_from_jd() for BCE/year-0 support."
        )
    return dt


def datetime_from_jd_with_truth(
    jd: float,
    *,
    input_scale: str = "unspecified_JD",
) -> JulianToDateTimeTruth:
    """Decompose a JD while disclosing that no time-scale conversion occurs."""

    scale = str(input_scale).strip()
    if not scale:
        raise ValueError("input_scale must be a non-empty label")
    value = float(jd)
    return JulianToDateTimeTruth(
        jd=value,
        input_scale=scale,
        calendar_datetime=datetime_from_jd(value),
    )


# ---------------------------------------------------------------------------
# Julian centuries from J2000.0
# ---------------------------------------------------------------------------

def centuries_from_j2000(jd: float) -> float:
    """Return Julian centuries (T) since J2000.0 for a given JD."""
    return (jd - J2000) / JULIAN_CENTURY


# ---------------------------------------------------------------------------
# ΔT — difference TT − UT1 in seconds
#
# The difference ΔT = TT − UT1 converts between the Earth-rotation coordinate
# UT1 and the uniform Terrestrial Time used for ephemeris lookup. Civil UTC is
# distinct and must first pass through the explicit UTC/UT1 policy below.
# Accuracy and uncertainty depend on the admitted source era; the future branch
# is a declared scenario rather than a prediction of actual Earth rotation.
# ---------------------------------------------------------------------------

# Lunar orbital tidal accelerations in arcsec/cy².  These constants describe
# source/ephemeris bases; they do not license an ambient correction in the
# generic clock model.  The legacy Morrison/Stephenson reductions used -26.0,
# while HPIERS/HMNAO explicitly belongs with DE430/LE430 at -25.85.  Horizons
# documents -25.936 for DE441.
_TIDAL_NDOT_POLYNOMIAL: float = -26.0
_TIDAL_NDOT_HPIERS: float = -25.85
_TIDAL_NDOT_DE441: float = -25.936

# Conversion factor: seconds of ΔT per (arcsec/cy²) per century² of baseline.
# Derivation: McCarthy & Babcock 1986; see also Morrison & Stephenson 2012.
# The published correction formula uses the 1955.0 reference epoch.  Whether a
# source product requires the correction in a particular era is owned by that
# source's policy, not by the generic arithmetic helper below.
_TIDAL_CONVERSION: float = 0.91072
_TIDAL_REF_EPOCH: float = 1955.0


def _tidacc_correction(
    year: float,
    source_ndot: float,
    target_ndot: float,
) -> float:
    """
    Return an explicit source-to-target tidal-basis correction in seconds.

    The source convention published with the NASA eclipse canon is::

        c = -0.91072 * (n_target - n_source) * ((year - 1955) / 100) ** 2
        DeltaT_corrected = DeltaT_source + c

    This helper is intentionally not called by :func:`delta_t`: the generic
    clock surface has no authoritative knowledge of which SPK/LE ephemeris a
    downstream computation will use.  Applying a DE441 correction there would
    silently corrupt DE430 computations.  A target-aware event computation may
    call this helper only after it has established the ephemeris identity.

    Args:
        year: Decimal year.
        source_ndot: Lunar tidal acceleration of the source Delta-T product.
        target_ndot: Lunar tidal acceleration of the target ephemeris.

    Returns:
        Correction in seconds to add to the raw source Delta-T.
    """
    _require_finite("year", year)
    _require_finite("source_ndot", source_ndot)
    _require_finite("target_ndot", target_ndot)
    t = (year - _TIDAL_REF_EPOCH) / 100.0
    return (
        -_TIDAL_CONVERSION
        * (target_ndot - source_ndot)
        * t
        * t
    )


@dataclass(frozen=True, slots=True)
class _TidalBasisTerm:
    """One linear contribution from a declared Delta-T tidal basis.

    ``coefficient`` is deliberately not restricted to ``[0, 1]``.  Source
    bridges use ordinary interpolation weights, while EOP reconciliation
    subtracts the year-model contribution at an admitted boundary and
    therefore requires signed terms.
    """

    source_product: str
    epoch_year: float
    source_ndot: float
    coefficient: float = 1.0

    def __post_init__(self) -> None:
        if not self.source_product:
            raise ValueError("Tidal-basis source_product must not be empty")
        _require_finite("epoch_year", self.epoch_year)
        _require_finite("source_ndot", self.source_ndot)
        _require_finite("coefficient", self.coefficient)

    def correction_to(self, target_ndot: float) -> float:
        """Return this term's source-to-target correction in seconds."""

        _require_finite("target_ndot", target_ndot)
        return self.coefficient * _tidacc_correction(
            self.epoch_year,
            self.source_ndot,
            target_ndot,
        )


_DELTA_T_RETARGET_MODES: frozenset[str] = frozenset(
    {"declared", "basis_neutral", "policy_locked"}
)


@dataclass(frozen=True, slots=True)
class _ResolvedDeltaT:
    """Private source-aware Delta-T product.

    The public clock surfaces return only ``seconds``.  This private vessel
    retains enough provenance for a later reader/event boundary to translate
    a reconstructed historical product to a verified target lunar ephemeris
    without changing generic Delta-T semantics.
    """

    seconds: float
    source_product: str
    retarget_mode: str
    tidal_terms: tuple[_TidalBasisTerm, ...] = ()

    def __post_init__(self) -> None:
        _require_finite("seconds", self.seconds)
        if not self.source_product:
            raise ValueError("Resolved Delta-T source_product must not be empty")
        if self.retarget_mode not in _DELTA_T_RETARGET_MODES:
            raise ValueError(
                "Resolved Delta-T retarget_mode must be one of "
                f"{sorted(_DELTA_T_RETARGET_MODES)!r}; got {self.retarget_mode!r}"
            )
        terms = tuple(self.tidal_terms)
        object.__setattr__(self, "tidal_terms", terms)
        if self.retarget_mode == "declared" and not terms:
            raise ValueError("Declared Delta-T basis requires at least one tidal term")
        if self.retarget_mode != "declared" and terms:
            raise ValueError(
                f"{self.retarget_mode!r} Delta-T products cannot carry tidal terms"
            )

    def correction_to(self, target_ndot: float) -> float:
        """Return the admitted correction for ``target_ndot`` in seconds.

        Basis-neutral products need no translation.  Policy-locked products
        (currently fixed and NASA-canon policies) already own their numerical
        convention and must not be retargeted automatically.
        """

        _require_finite("target_ndot", target_ndot)
        if self.retarget_mode != "declared":
            return 0.0
        return math.fsum(term.correction_to(target_ndot) for term in self.tidal_terms)

    def retargeted_seconds(self, target_ndot: float) -> float:
        """Return raw seconds plus the admitted source-to-target correction."""

        return self.seconds + self.correction_to(target_ndot)


def _tidal_term(
    source_product: str,
    epoch_year: float,
    source_ndot: float,
    coefficient: float = 1.0,
) -> tuple[_TidalBasisTerm, ...]:
    """Build a zero-free tidal-term tuple for interpolation assembly."""

    if coefficient == 0.0:
        return ()
    return (
        _TidalBasisTerm(
            source_product=source_product,
            epoch_year=epoch_year,
            source_ndot=source_ndot,
            coefficient=coefficient,
        ),
    )


def _scaled_tidal_terms(
    resolved: _ResolvedDeltaT,
    coefficient: float,
) -> tuple[_TidalBasisTerm, ...]:
    """Return ``resolved`` tidal terms multiplied by a signed coefficient."""

    _require_finite("coefficient", coefficient)
    if coefficient == 0.0 or not resolved.tidal_terms:
        return ()
    return tuple(
        _TidalBasisTerm(
            source_product=term.source_product,
            epoch_year=term.epoch_year,
            source_ndot=term.source_ndot,
            coefficient=term.coefficient * coefficient,
        )
        for term in resolved.tidal_terms
        if term.coefficient * coefficient != 0.0
    )


def _resolved_delta_t(
    seconds: float,
    source_product: str,
    tidal_terms: tuple[_TidalBasisTerm, ...] = (),
    *,
    policy_locked: bool = False,
) -> _ResolvedDeltaT:
    """Construct a resolved product with an explicit retargeting doctrine."""

    terms = tuple(term for term in tidal_terms if term.coefficient != 0.0)
    if policy_locked:
        if terms:
            raise ValueError("Policy-locked Delta-T cannot carry tidal terms")
        mode = "policy_locked"
    else:
        mode = "declared" if terms else "basis_neutral"
    return _ResolvedDeltaT(
        seconds=seconds,
        source_product=source_product,
        retarget_mode=mode,
        tidal_terms=terms,
    )


def _resolve_delta_t(year: float) -> _ResolvedDeltaT:
    """Resolve the year-model total together with its source-basis doctrine.

    This is the single owner of the routing exposed numerically by
    :func:`delta_t`.  It deliberately records source-basis terms without
    applying them to any target ephemeris.
    """

    y = float(year)
    _require_representable_delta_t_year(y)
    u: float

    # Direct modern aggregates are clock observations, not lunar-ephemeris
    # reductions, so they carry no retargetable tidal basis.
    annual_start = _DELTA_T_ANNUAL[0][0]
    annual_end = _delta_t_observation_boundary().year
    if annual_start <= y <= annual_end:
        return _resolved_delta_t(
            _interpolate_delta_t_table(_DELTA_T_ANNUAL, y),
            "usno_monthly_aggregate",
        )

    # Retarget the HPIERS endpoint before interpolating toward the neutral
    # aggregate endpoint.  The coefficient tends to zero at annual_start,
    # preserving the declared C0 source handoff after retargeting.
    bridge = _delta_t_hpiers_annual_bridge()
    if bridge[0][0] <= y < bridge[-1][0]:
        hpiers_year = bridge[0][0]
        fraction = (y - bridge[0][0]) / (bridge[-1][0] - bridge[0][0])
        return _resolved_delta_t(
            _interpolate_delta_t_table(bridge, y),
            "hpiers_to_usno_bridge",
            _tidal_term(
                "hpiers_de430_le430",
                hpiers_year,
                _TIDAL_NDOT_HPIERS,
                1.0 - fraction,
            ),
        )

    hpiers_start = _DELTA_T_HPIERS_2016[0][0]
    if hpiers_start <= y < bridge[0][0]:
        return _resolved_delta_t(
            _interpolate_delta_t_table(_DELTA_T_HPIERS_2016, y),
            "hpiers_de430_le430",
            _tidal_term(
                "hpiers_de430_le430",
                y,
                _TIDAL_NDOT_HPIERS,
            ),
        )

    # The bridge is a materialized relation between two source endpoints, not
    # an observation at an invented effective basis.  Retarget each endpoint
    # first, then apply the same interpolation weights as the raw C0 bridge.
    ancient_bridge_start = hpiers_start - 100.0
    if ancient_bridge_start <= y < hpiers_start:
        u0 = (ancient_bridge_start - 1820.0) / 100.0
        polynomial_total = -20.0 + 32.0 * u0 * u0
        hpiers_total = _DELTA_T_HPIERS_2016[0][1]
        fraction = (y - ancient_bridge_start) / (
            hpiers_start - ancient_bridge_start
        )
        return _resolved_delta_t(
            polynomial_total + fraction * (hpiers_total - polynomial_total),
            "polynomial_to_hpiers_bridge",
            (
                *_tidal_term(
                    "morrison_stephenson_polynomial",
                    ancient_bridge_start,
                    _TIDAL_NDOT_POLYNOMIAL,
                    1.0 - fraction,
                ),
                *_tidal_term(
                    "hpiers_de430_le430",
                    hpiers_start,
                    _TIDAL_NDOT_HPIERS,
                    fraction,
                ),
            ),
        )

    # These retained table branches are currently shadowed by HPIERS coverage,
    # but remain source-described if that packaged coverage is ever narrowed.
    hist_start = _DELTA_T_HISTORICAL[0][0]
    if hist_start <= y < 1900.0:
        table = _DELTA_T_HISTORICAL + ((1900.0, -2.7900),)
        total = _DELTA_T_HISTORICAL[-1][1]
        for (y0, dt0), (y1, dt1) in zip(table, table[1:]):
            if y0 <= y <= y1:
                fraction = (y - y0) / (y1 - y0)
                total = dt0 + fraction * (dt1 - dt0)
                break
        return _resolved_delta_t(
            total,
            "historical_anchor_fallback",
            _tidal_term(
                "historical_anchor_fallback",
                y,
                _TIDAL_NDOT_POLYNOMIAL,
            ),
        )

    if 1900.0 <= y < 1955.0:
        total = _DELTA_T_PRE1955_5Y[-1][1]
        for (y0, dt0), (y1, dt1) in zip(
            _DELTA_T_PRE1955_5Y,
            _DELTA_T_PRE1955_5Y[1:],
        ):
            if y0 <= y <= y1:
                fraction = (y - y0) / (y1 - y0)
                total = dt0 + fraction * (dt1 - dt0)
                break
        return _resolved_delta_t(
            total,
            "pre1955_anchor_fallback",
            _tidal_term(
                "pre1955_anchor_fallback",
                y,
                _TIDAL_NDOT_POLYNOMIAL,
            ),
        )

    if y < -500:
        u = (y - 1820.0) / 100.0
        total = -20.0 + 32.0 * u * u
    elif y < 500:
        u = y / 100.0
        total = (
            10583.6
            - 1014.41 * u
            + 33.78311 * u**2
            - 5.952053 * u**3
            - 0.1798452 * u**4
            + 0.022174192 * u**5
            + 0.0090316521 * u**6
        )
    elif y < 1600:
        u = (y - 1000.0) / 100.0
        total = (
            1574.2
            - 556.01 * u
            + 71.23472 * u**2
            + 0.319781 * u**3
            - 0.8503463 * u**4
            - 0.005050998 * u**5
            + 0.0083572073 * u**6
        )
    elif y < 1700:
        t = y - 1600.0
        total = 120.0 - 0.9808 * t - 0.01532 * t**2 + t**3 / 7129.0
    elif y < 1800:
        t = y - 1700.0
        total = (
            8.83
            + 0.1603 * t
            - 0.0059285 * t**2
            + 0.00013336 * t**3
            - t**4 / 1174000.0
        )
    elif y < 1860:
        t = y - 1800.0
        total = (
            13.72
            - 0.332447 * t
            + 0.0068612 * t**2
            + 0.0041116 * t**3
            - 0.00037436 * t**4
            + 0.0000121272 * t**5
            - 0.0000001699 * t**6
            + 0.000000000875 * t**7
        )
    elif y < 1900:
        t = y - 1860.0
        total = (
            7.62
            + 0.5737 * t
            - 0.251754 * t**2
            + 0.01680668 * t**3
            - 0.0004473624 * t**4
            + t**5 / 233174.0
        )
    elif y < 1920:
        t = y - 1900.0
        total = (
            -2.79
            + 1.494119 * t
            - 0.0598939 * t**2
            + 0.0061966 * t**3
            - 0.000197 * t**4
        )
    elif y < 1941:
        t = y - 1920.0
        total = 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3
    elif y < 1961:
        t = y - 1950.0
        total = 29.07 + 0.407 * t - t**2 / 233.0 + t**3 / 2547.0
    elif y < 1986:
        t = y - 1975.0
        total = 45.45 + 1.067 * t - t**2 / 260.0 - t**3 / 718.0
    elif y < 2005:
        t = y - 2000.0
        total = (
            63.86
            + 0.3345 * t
            - 0.060374 * t**2
            + 0.0017275 * t**3
            + 0.000651814 * t**4
            + 0.00002373599 * t**5
        )
    else:
        # Post-observation years are owned by the required future model.
        from .delta_t_physical import delta_t_hybrid as _hyb

        return _resolved_delta_t(_hyb(y), "future_scenario")

    return _resolved_delta_t(
        total,
        "morrison_stephenson_polynomial",
        _tidal_term(
            "morrison_stephenson_polynomial",
            y,
            _TIDAL_NDOT_POLYNOMIAL,
        ),
    )


def delta_t(year: float) -> float:
    """
    ΔT = TT − UT1 in seconds for any decimal year.

    Doctrine: highest-authority source per epoch. Where direct observations
    exist, observations govern. Where they end, Moira's declared future
    scenario governs. Source totals remain on their published tidal basis;
    generic clock conversion never guesses a downstream ephemeris identity.

    This is not a fallback cascade — it is an epistemic priority queue:

    +------------------+-----------------------------------------------+
    | Epoch            | Source and authority                          |
    +==================+===============================================+
    | After final      | Required ``delta_t_physical.delta_t_hybrid``  |
    | aggregate epoch  | future scenario                              |
    +------------------+-----------------------------------------------+
    | 2015.456–2026.123| USNO aggregate means at representative epochs |
    +------------------+-----------------------------------------------+
    | -2000–1955.5     | HPIERS/HMNAO mean on its declared             |
    |                  | DE430/LE430 tidal basis                        |
    +------------------+-----------------------------------------------+
    | 1955.5–2015.0    | HPIERS/HMNAO atomic-era mean, unadjusted       |
    +------------------+-----------------------------------------------+
    | 2015.0–2015.456  | Explicit HPIERS-to-aggregate C0 bridge        |
    +------------------+-----------------------------------------------+
    | -2100–-2000      | Explicit C0 source-floor reconciliation       |
    +------------------+-----------------------------------------------+
    | Earlier than     | Morrison & Stephenson (2004) polynomials      |
    | -2100            | on their published source basis               |
    +------------------+-----------------------------------------------+

    Table-driven ranges use linear interpolation. Polynomial branches apply
    only when no table covers the requested year. The required future model
    owns post-observation extrapolation; import or validation failures from
    that model propagate rather than selecting an undeclared weaker formula.

    Args:
        year: Decimal year (e.g. ``2000.5``).

    Returns:
        ΔT in seconds (positive means TT is ahead of UT1).

    Raises:
        ValueError: If ``year`` is not finite.
        ImportError: If the required future-model module cannot be imported.

    Side effects:
        None.
    """
    return _resolve_delta_t(year).seconds


def _resolve_delta_t_for_ut1(
    jd_ut: float,
    year: float | None = None,
    delta_t_policy: DeltaTPolicy | None = None,
) -> _ResolvedDeltaT:
    """Resolve the exact source product used for one UT1-to-TT conversion.

    Public clock functions intentionally expose only the numerical Delta-T.
    Reader-bound ephemeris work needs the same number together with its source
    doctrine so a historical lunar-ephemeris basis can be translated without
    altering direct observations or caller-owned policies.
    """

    _require_representable_time_jd("jd_ut", jd_ut)
    explicit_year = year is not None
    if explicit_year:
        _require_finite("year", year)

    if delta_t_policy is None or delta_t_policy.model == "hybrid":
        if explicit_year:
            return _resolve_delta_t(float(year))
        admitted = EOPRegistry._delta_t_from_ut1(jd_ut)
        if admitted is not None:
            return _resolved_delta_t(admitted, "iers_eop_direct")
        return EOPRegistry._model_delta_t_handoff_resolved(jd_ut)

    policy_year = (
        float(year)
        if explicit_year
        else _policy_year_from_jd(jd_ut, delta_t_policy)
    )
    return _resolved_delta_t(
        delta_t_policy.compute(policy_year),
        f"delta_t_policy_{delta_t_policy.model}",
        policy_locked=True,
    )


def delta_t_from_jd(jd_ut: float) -> float:
    """
    Approximate ΔT = TT − UT1 in seconds for a Julian Day in UT1.

    Uses the bundled daily Earth-orientation record when it covers ``jd_ut``.
    At each outer coverage edge, a local reconciliation correction tapers to
    zero over one Julian year; it is never extended into remote epochs.
    Internal gaps interpolate between the two surrounding admitted EOP
    boundaries.  These explicit C0 handoffs prevent a source step.

    Args:
        jd_ut: Julian Day Number in UT1.

    Returns:
        ΔT in seconds (positive means TT is ahead of UT1).

    Raises:
        ValueError: If ``jd_ut`` is not finite.

    Side effects:
        None.
    """
    return _resolve_delta_t_for_ut1(jd_ut).seconds


def delta_t_from_jd_with_truth(jd_ut: float) -> DeltaTTruth:
    """Return Delta-T with the exact selected source product and basis policy."""

    value = float(jd_ut)
    resolved = _resolve_delta_t_for_ut1(value)
    return DeltaTTruth(
        jd_ut1=value,
        seconds=resolved.seconds,
        source_product=resolved.source_product,
        retarget_mode=resolved.retarget_mode,
        tidal_terms=tuple(
            DeltaTTidalBasisTruth(
                source_product=term.source_product,
                epoch_year=term.epoch_year,
                source_ndot_arcsec_per_cy2=term.source_ndot,
                coefficient=term.coefficient,
            )
            for term in resolved.tidal_terms
        ),
    )


def delta_t_nasa_canon(year: float) -> float:
    """
    NASA eclipse-canon ΔT model in seconds.

    Governs the Espenak/Meeus piecewise polynomial expressions used by the
    Five Millennium Canon of Solar Eclipses. Differs from ``delta_t()`` in
    two ways: it uses the NASA polynomial set without the HPIERS table override,
    and outside 1955–2005 it applies NASA's lunar secular-acceleration
    correction ``−0.000012932 × (year − 1955)²``. NASA explicitly requires no
    such ephemeris correction inside 1955–2005, where the values are derived
    independently of a lunar ephemeris.

    Use this function when comparing against NASA eclipse contact times or
    the Five Millennium catalog; use ``delta_t()`` for general ephemeris work.

    Args:
        year: Decimal year (e.g. ``2000.5``).

    Returns:
        ΔT in seconds including the lunar secular-acceleration correction.

    Raises:
        ValueError: If ``year`` is not finite.

    Side effects:
        None.
    """
    y = float(year)
    _require_representable_delta_t_year(y)
    u: float

    if y < -500:
        u = (y - 1820.0) / 100.0
        base = -20 + 32 * u * u
    elif y < 500:
        u = y / 100.0
        base = (
            10583.6
            - 1014.41 * u
            + 33.78311 * u**2
            - 5.952053 * u**3
            - 0.1798452 * u**4
            + 0.022174192 * u**5
            + 0.0090316521 * u**6
        )
    elif y < 1600:
        u = (y - 1000.0) / 100.0
        base = (
            1574.2
            - 556.01 * u
            + 71.23472 * u**2
            + 0.319781 * u**3
            - 0.8503463 * u**4
            - 0.005050998 * u**5
            + 0.0083572073 * u**6
        )
    elif y < 1700:
        t = y - 1600.0
        base = 120 - 0.9808 * t - 0.01532 * t**2 + t**3 / 7129.0
    elif y < 1800:
        t = y - 1700.0
        base = (
            8.83
            + 0.1603 * t
            - 0.0059285 * t**2
            + 0.00013336 * t**3
            - t**4 / 1174000.0
        )
    elif y < 1860:
        t = y - 1800.0
        base = (
            13.72
            - 0.332447 * t
            + 0.0068612 * t**2
            + 0.0041116 * t**3
            - 0.00037436 * t**4
            + 0.0000121272 * t**5
            - 0.0000001699 * t**6
            + 0.000000000875 * t**7
        )
    elif y < 1900:
        t = y - 1860.0
        base = (
            7.62
            + 0.5737 * t
            - 0.251754 * t**2
            + 0.01680668 * t**3
            - 0.0004473624 * t**4
            + t**5 / 233174.0
        )
    elif y < 1920:
        t = y - 1900.0
        base = -2.79 + 1.494119 * t - 0.0598939 * t**2 + 0.0061966 * t**3 - 0.000197 * t**4
    elif y < 1941:
        t = y - 1920.0
        base = 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3
    elif y < 1961:
        t = y - 1950.0
        base = 29.07 + 0.407 * t - t**2 / 233.0 + t**3 / 2547.0
    elif y < 1986:
        t = y - 1975.0
        base = 45.45 + 1.067 * t - t**2 / 260.0 - t**3 / 718.0
    elif y < 2005:
        t = y - 2000.0
        base = (
            63.86
            + 0.3345 * t
            - 0.060374 * t**2
            + 0.0017275 * t**3
            + 0.000651814 * t**4
            + 0.00002373599 * t**5
        )
    elif y < 2050:
        t = y - 2000.0
        base = 62.92 + 0.32217 * t + 0.005589 * t**2
    elif y < 2150:
        base = -20 + 32 * ((y - 1820.0) / 100.0) ** 2 - 0.5628 * (2150.0 - y)
    else:
        u = (y - 1820.0) / 100.0
        base = -20 + 32 * u * u

    correction = (
        -0.000012932 * (y - 1955.0) ** 2
        if y < 1955.0 or y > 2005.0
        else 0.0
    )
    return base + correction


@dataclass(frozen=True, slots=True)
class DeltaTPolicy:
    """
    Typed policy object controlling how ΔT (TT − UT1) is computed.

    DeltaTPolicy replaces legacy global ``set_delta_t_userdef``-style
    mutation pattern with a typed, immutable, per-call policy. Pass a
    DeltaTPolicy instance to ``ut_to_tt()``, ``tt_to_ut()``, or
    ``planet_at()`` to override the default hybrid model for that call.

    Attributes
    ----------
    model : str
        Which ΔT algorithm to use.  Accepted values:

        ``'hybrid'`` (default)
            Moira's multi-source table cascade (see ``delta_t()``).  Covers
            all eras via IERS Bulletin B/A, HPIERS 2016, and
            Morrison-Stephenson polynomials. JD-aware ``ut_to_tt()`` and
            ``tt_to_ut()`` calls additionally prefer the bundled daily EOP
            record; ``compute(year)`` remains the year-only estimate.

        ``'physical'``
            The explicit model in ``delta_t_physical.delta_t_hybrid()``. See
            that module for its current authority domain, admitted components,
            and uncertainty semantics. It deliberately bypasses the JD-aware
            EOP priority used by the default hybrid conversion.

        ``'nasa_canon'``
            NASA eclipse-canon polynomial model (see ``delta_t_nasa_canon()``).
            JD transforms use a continuous implicit year to avoid artificial
            month steps. Exact published-catalog reproduction requires an
            explicit NASA month-midpoint year or the dedicated NASA eclipse
            compatibility path. Raw polynomial boundary seams remain explicit.

        ``'fixed'``
            Use a single fixed ΔT value supplied in ``fixed_delta_t``.
            Useful for controlled numerical tests or for epochs where no
            reliable table data exists and a known value is preferred.

    fixed_delta_t : float or None
        The fixed ΔT value in seconds to use when ``model='fixed'``.
        Must be provided when ``model='fixed'``; ignored otherwise.

    Examples
    --------
    >>> from moira.julian import DeltaTPolicy, ut_to_tt
    >>> policy = DeltaTPolicy(model='fixed', fixed_delta_t=69.0)
    >>> jd_tt = ut_to_tt(2451545.0, delta_t_policy=policy)
    """

    model: str = 'hybrid'
    fixed_delta_t: float | None = None

    def __post_init__(self) -> None:
        allowed = ('hybrid', 'physical', 'nasa_canon', 'fixed')
        if self.model not in allowed:
            raise ValueError(
                f"DeltaTPolicy.model must be one of {allowed!r}, got {self.model!r}"
            )
        if self.model == 'fixed':
            if self.fixed_delta_t is None:
                raise ValueError(
                    "DeltaTPolicy.model='fixed' requires fixed_delta_t to be set"
                )
            try:
                fixed_value = float(self.fixed_delta_t)
            except (TypeError, ValueError) as exc:
                raise ValueError("DeltaTPolicy.fixed_delta_t must be numeric and finite") from exc
            if not math.isfinite(fixed_value):
                raise ValueError("DeltaTPolicy.fixed_delta_t must be finite")
            object.__setattr__(self, 'fixed_delta_t', fixed_value)

    def compute(self, year: float) -> float:
        """Return the year-only ΔT estimate under this policy.

        The default hybrid policy gains daily EOP resolution only when a UT1
        Julian Day is available through ``ut_to_tt()`` or ``tt_to_ut()``.
        """
        _require_finite("year", year)
        if self.model == 'fixed':
            return float(self.fixed_delta_t)  # type: ignore[arg-type]
        if self.model == 'nasa_canon':
            return delta_t_nasa_canon(year)
        if self.model == 'physical':
            from .delta_t_physical import delta_t_hybrid  # deferred: delta_t_physical imports julian
            return delta_t_hybrid(year)
        return delta_t(year)


def _policy_year_from_jd(
    jd: float,
    policy: DeltaTPolicy | None,
) -> float:
    """Select the year coordinate required by a Delta-T policy.

    Every JD-based time transform requires a continuous coordinate. NASA's
    published month-midpoint convention remains available through an explicit
    ``year`` argument and the year-only catalog function; it is not used as an
    implicit clock coordinate because its monthly steps are non-injective.
    """

    if policy is not None and policy.model == "fixed":
        return 0.0
    return _continuous_decimal_year_from_jd(jd)


_PRE_1972_UTC_DRIFT: tuple[tuple[float, float, float, float], ...] = (
    # effective MJD, offset at reference MJD [s], reference MJD, drift [s/day]
    # IAU SOFA ``iauDat`` pre-leap-second UTC segments.  The first segment is
    # authoritative from 1960-01-01 (MJD 36934); earlier UTC is outside this
    # clock product rather than a synthetic zero/10-second extension.
    (36934.0, 1.4178180, 37300.0, 0.0012960),
    (37300.0, 1.4228180, 37300.0, 0.0012960),
    (37512.0, 1.3728180, 37300.0, 0.0012960),
    (37665.0, 1.8458580, 37665.0, 0.0011232),
    (38334.0, 1.9458580, 37665.0, 0.0011232),
    (38395.0, 3.2401300, 38761.0, 0.0012960),
    (38486.0, 3.3401300, 38761.0, 0.0012960),
    (38639.0, 3.4401300, 38761.0, 0.0012960),
    (38761.0, 3.5401300, 38761.0, 0.0012960),
    (38820.0, 3.6401300, 38761.0, 0.0012960),
    (38942.0, 3.7401300, 38761.0, 0.0012960),
    (39004.0, 3.8401300, 38761.0, 0.0012960),
    (39126.0, 4.3131700, 39126.0, 0.0025920),
    (39887.0, 4.2131700, 39126.0, 0.0025920),
)
_PRE_1972_UTC_START_JD: float = 2400000.5 + _PRE_1972_UTC_DRIFT[0][0]


def tai_minus_utc(jd_utc: float) -> float:
    """
    Return TAI - UTC in seconds for a UTC-coded Julian Date.

    From 1972 onward this uses IERS Bulletin C leap-second steps.  From
    1960-01-01 through 1971-12-31 it uses the IAU SOFA ``iauDat`` piecewise
    offset-and-drift history.  Dates before 1960 are rejected because this
    UTC-to-TAI product is not defined there; historical astronomy should use
    the explicit UT1/TT model instead.
    """
    _require_representable_time_jd("jd_utc", jd_utc)
    if jd_utc < _PRE_1972_UTC_START_JD:
        raise ValueError(
            "TAI-UTC is defined by this clock model only from 1960-01-01; "
            "use the historical UT1/TT model for earlier epochs"
        )

    # LEAP_SECONDS is a list of (JD, offset) sorted by JD.  Find the largest
    # effective epoch not later than the requested civil instant.
    idx = bisect.bisect_right(LEAP_SECONDS, (jd_utc, float('inf'))) - 1
    if idx >= 0:
        return LEAP_SECONDS[idx][1]

    mjd_utc = jd_utc - 2400000.5
    for effective_mjd, offset, reference_mjd, drift in reversed(
        _PRE_1972_UTC_DRIFT
    ):
        if mjd_utc >= effective_mjd:
            return offset + (mjd_utc - reference_mjd) * drift
    raise AssertionError("pre-1972 UTC drift table does not cover admitted epoch")


def utc_to_tai(jd_utc: float) -> float:
    """Convert UTC to TAI over the admitted 1960-present clock history."""
    _require_representable_time_jd("jd_utc", jd_utc)
    return jd_utc + tai_minus_utc(jd_utc) / 86400.0


def tai_to_tt(jd_tai: float) -> float:
    """Convert Julian Day in TAI to Terrestrial Time (TT)."""
    _require_representable_time_jd("jd_tai", jd_tai)
    return jd_tai + TAI_TT_OFFSET / 86400.0


_UTC_ATOMIC_HANDOFF_WINDOW_DAYS: float = 1.0


def _atomic_utc_to_ut1(jd_utc: float) -> float:
    """Reduce an atomic-era UTC coordinate to UT1 without EOP data."""

    return tt_to_ut(tai_to_tt(utc_to_tai(jd_utc)))


def utc_to_tt(jd_utc: float) -> float:
    """
    Convert Julian Day in UTC to Terrestrial Time (TT).

    From 1972-01-01 onward, this is the atomic UTC -> TAI -> TT reduction.
    Before the first admitted leap-second-table epoch, Moira does not pretend
    that the table's ``10 s`` compatibility placeholder is authoritative UTC
    history. A proleptic civil JD is instead interpreted as the established
    historical UT1 proxy and TT is derived from that same coordinate. This
    keeps historical facade inputs coherent with the Delta-T model.
    """
    _require_representable_time_jd("jd_utc", jd_utc)
    if jd_utc < LEAP_SECONDS[0][0]:
        return ut_to_tt(utc_to_ut1(jd_utc))
    return tai_to_tt(utc_to_tai(jd_utc))


_EOP_HANDOFF_WINDOW_DAYS: float = 365.25


class EOPRegistry:
    """
    RITE: The Earth Orientation Registry.

    THEOREM: Governs lazy loading and leap-safe interpolation of DUT1
    (UT1-UTC) and Delta-T values from the bundled Earth-orientation data file.

    RITE OF PURPOSE:
        EOPRegistry provides the narrow bridge between bundled IERS-style
        Earth-orientation data and Moira's time-scale conversion layer. It
        keeps the file-backed DUT1 table off the import path until needed,
        then exposes stable UTC-to-UT1 and UT1-to-TT lookup surfaces.

    LAW OF OPERATION:
        Responsibilities:
            - Load the bundled DUT1 table on first demand.
            - Cache the parsed MJD-to-DUT1 mapping for reuse.
            - Interpolate the continuous UT1-TAI quantity between daily rows.
            - Build continuous UT1/Delta-T segments from UTC-midnight rows.
            - Return a deterministic DUT1 value or a zero compatibility fallback.
        Non-responsibilities:
            - Does not download, refresh, or validate external IERS feeds.
            - Does not own TT, TDB, or sidereal-time conversion policy.
        Dependencies:
            - stdlib ``pathlib`` for bundled file access.
        Structural invariants:
            - ``_data`` is either ``None`` or a dict keyed by integer MJD.
            - ``_path`` always points to the bundled EOP text file location.
        Failure behavior:
            - A missing file yields the explicit empty-data fallback.
            - A present but malformed, non-finite, duplicate, or unordered row
              raises before any partial table is cached.

    Canon: IERS-style DUT1 tabulation as bundled repository data.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.julian.EOPRegistry",
      "risk": "medium",
      "api": {
        "frozen": ["get_dut1"],
        "internal": ["_load", "_dut1_optional", "_segment_bounds", "_delta_t_from_ut1", "_utc_from_ut1", "_ut1_from_tt", "_model_delta_t_handoff", "_data", "_path"]
      },
      "state": {
        "mutable": true,
        "owners": ["EOPRegistry"]
      },
      "effects": {
        "signals_emitted": [],
        "io": ["bundled_file_read"]
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only"
      },
      "failures": {
        "policy": "raise"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": ["api_change"]
      }
    }
    [/MACHINE_CONTRACT]
    """
    _data: dict[int, float] | None = None
    _path = Path(__file__).resolve().parent / "data" / "iers_eop.txt"
    _ordered_mjds_owner: dict[int, float] | None = None
    _ordered_mjds_cache: tuple[int, ...] = ()

    @classmethod
    def _ensure_loaded(cls) -> dict[int, float]:
        if cls._data is None:
            cls._load()
        assert cls._data is not None
        return cls._data

    @staticmethod
    def _utc_midnight(mjd: int) -> float:
        return float(mjd) + 2400000.5

    @classmethod
    def _ordered_mjds(cls, data: dict[int, float]) -> tuple[int, ...]:
        """Return sorted row epochs, refreshing when tests replace the table."""

        if cls._ordered_mjds_owner is not data:
            cls._ordered_mjds_cache = tuple(sorted(data))
            cls._ordered_mjds_owner = data
        return cls._ordered_mjds_cache

    @classmethod
    def _segment_bounds(
        cls,
        mjd0: int,
        data: dict[int, float],
    ) -> tuple[float, float, float, float] | None:
        """Return ``(UT1_0, DeltaT_0, UT1_1, DeltaT_1)`` for one EOP row.

        A following consecutive row supplies the end knot.  Otherwise the row
        owns only its own UTC day, with UT1-TAI held constant to that day's end.
        This rule neither extrapolates the admitted record nor bridges a gap.
        """

        dut1_0 = data.get(mjd0)
        if dut1_0 is None:
            return None

        utc0 = cls._utc_midnight(mjd0)
        tai_utc_0 = tai_minus_utc(utc0)
        ut1_minus_tai_0 = dut1_0 - tai_utc_0
        ut1_0 = utc0 + dut1_0 / 86400.0
        delta_t_0 = TAI_TT_OFFSET - ut1_minus_tai_0

        utc1 = cls._utc_midnight(mjd0 + 1)
        tai_utc_1 = tai_minus_utc(utc1)
        dut1_1 = data.get(mjd0 + 1)
        if dut1_1 is None:
            ut1_minus_tai_1 = ut1_minus_tai_0
            dut1_1 = ut1_minus_tai_1 + tai_utc_1
        else:
            ut1_minus_tai_1 = dut1_1 - tai_utc_1
        ut1_1 = utc1 + dut1_1 / 86400.0
        delta_t_1 = TAI_TT_OFFSET - ut1_minus_tai_1
        return ut1_0, delta_t_0, ut1_1, delta_t_1

    @classmethod
    def _dut1_optional(cls, jd_utc: float) -> float | None:
        """Return leap-safe interpolated DUT1, or ``None`` outside coverage."""

        _require_representable_time_jd("jd_utc", jd_utc)
        data = cls._ensure_loaded()
        mjd_value = jd_utc - 2400000.5
        mjd0 = math.floor(mjd_value)
        fraction = mjd_value - mjd0
        dut1_0 = data.get(mjd0)
        if dut1_0 is None:
            return None

        utc0 = cls._utc_midnight(mjd0)
        tai_utc_0 = tai_minus_utc(utc0)
        ut1_minus_tai_0 = dut1_0 - tai_utc_0

        dut1_1 = data.get(mjd0 + 1)
        if dut1_1 is None:
            # A daily EOP row governs its own UTC day.  Holding the continuous
            # UT1-TAI value avoids bridging an internal gap or extrapolating
            # beyond the final row.
            ut1_minus_tai = ut1_minus_tai_0
        else:
            utc1 = cls._utc_midnight(mjd0 + 1)
            ut1_minus_tai_1 = dut1_1 - tai_minus_utc(utc1)
            ut1_minus_tai = (
                ut1_minus_tai_0
                + fraction * (ut1_minus_tai_1 - ut1_minus_tai_0)
            )

        # Add the offset effective at the requested UTC instant.  Interpolating
        # UT1-TAI rather than raw DUT1 prevents a leap-second step from being
        # smeared across the preceding day.
        return ut1_minus_tai + tai_minus_utc(jd_utc)

    @classmethod
    def _delta_t_from_ut1(cls, jd_ut1: float) -> float | None:
        """Return EOP-derived TT-UT1 seconds for a UT1 JD, if covered.

        Each daily UTC row supplies a knot whose independent coordinate is the
        corresponding UT1 midnight and whose dependent value is Delta-T.  The
        interpolation therefore remains continuous across UTC leap seconds and
        does not require guessing a UTC date from a UT1 number.
        """

        _require_representable_time_jd("jd_ut1", jd_ut1)
        data = cls._ensure_loaded()
        approximate_mjd = math.floor(jd_ut1 - 2400000.5)

        # |UT1-UTC| is constrained below one second in this data era, so the
        # governing UTC day can only be the approximate day or an immediate
        # neighbour at a day boundary.
        for mjd0 in (approximate_mjd - 1, approximate_mjd, approximate_mjd + 1):
            segment = cls._segment_bounds(mjd0, data)
            if segment is None:
                continue
            ut1_0, delta_t_0, ut1_1, delta_t_1 = segment

            if ut1_0 <= jd_ut1 < ut1_1:
                span = ut1_1 - ut1_0
                if span <= 0.0:
                    return delta_t_0
                fraction = (jd_ut1 - ut1_0) / span
                return delta_t_0 + fraction * (delta_t_1 - delta_t_0)
        return None

    @classmethod
    def _ut1_from_tt(cls, jd_tt: float) -> float | None:
        """Invert an EOP segment directly in its TT coordinate, if covered."""

        _require_representable_time_jd("jd_tt", jd_tt)
        data = cls._ensure_loaded()
        approximate_mjd = math.floor(jd_tt - 2400000.5)
        for mjd0 in range(approximate_mjd - 2, approximate_mjd + 2):
            segment = cls._segment_bounds(mjd0, data)
            if segment is None:
                continue
            ut1_0, delta_t_0, ut1_1, delta_t_1 = segment
            tt_0 = ut1_0 + delta_t_0 / 86400.0
            tt_1 = ut1_1 + delta_t_1 / 86400.0
            if tt_0 <= jd_tt < tt_1:
                span = tt_1 - tt_0
                if span <= 0.0:
                    return ut1_0
                fraction = (jd_tt - tt_0) / span
                return ut1_0 + fraction * (ut1_1 - ut1_0)
        return None

    @classmethod
    def _utc_from_ut1(cls, jd_ut1: float) -> float | None:
        """Invert an admitted EOP row without smearing a UTC leap second.

        The registry interpolates UT1-TAI through a UTC day, then applies the
        TAI-UTC offset effective at the requested civil instant.  Inverting the
        row's UT1 endpoints directly would distribute a leap second across the
        preceding 24 hours.  Solve that same within-day affine relation instead.
        """

        _require_representable_time_jd("jd_ut1", jd_ut1)
        data = cls._ensure_loaded()
        approximate_mjd = math.floor(jd_ut1 - 2400000.5)
        for mjd0 in range(approximate_mjd - 2, approximate_mjd + 2):
            dut1_0 = data.get(mjd0)
            if dut1_0 is None:
                continue
            utc0 = cls._utc_midnight(mjd0)
            tai_utc_0 = tai_minus_utc(utc0)
            ut1_minus_tai_0 = dut1_0 - tai_utc_0
            dut1_1 = data.get(mjd0 + 1)
            if dut1_1 is None:
                ut1_minus_tai_1 = ut1_minus_tai_0
            else:
                utc1 = cls._utc_midnight(mjd0 + 1)
                ut1_minus_tai_1 = dut1_1 - tai_minus_utc(utc1)

            slope = 1.0 + (
                ut1_minus_tai_1 - ut1_minus_tai_0
            ) / 86400.0
            fraction = (
                jd_ut1
                - utc0
                - (ut1_minus_tai_0 + tai_utc_0) / 86400.0
            ) / slope
            tolerance = 4.0 * math.ulp(max(1.0, abs(jd_ut1)))
            if -tolerance <= fraction <= 1.0 + tolerance:
                return utc0 + min(1.0, max(0.0, fraction))
        return None

    @classmethod
    def _model_delta_t_handoff_resolved(cls, jd_ut1: float) -> _ResolvedDeltaT:
        """Resolve the year model with bounded C0 EOP reconciliation.

        At each outer admitted EOP boundary, the local correction tapers to
        zero over one Julian year.  It is never propagated into remote epochs.
        Across an internal gap, the two surrounding boundary corrections are
        linearly interpolated.  The underlying source model remains visible;
        this method owns only the local source reconciliation.  Signed tidal
        terms subtract the corresponding boundary-model contribution, so a
        later target-basis translation preserves the same C0 handoff.
        """

        _require_representable_time_jd("jd_ut1", jd_ut1)
        data = cls._ensure_loaded()

        def model_product(epoch: float) -> _ResolvedDeltaT:
            return _resolve_delta_t(_continuous_decimal_year_from_jd(epoch))

        def taper_weight(distance: float) -> float:
            if distance >= _EOP_HANDOFF_WINDOW_DAYS:
                return 0.0
            proximity = 1.0 - max(0.0, distance) / _EOP_HANDOFF_WINDOW_DAYS
            return proximity * proximity * (3.0 - 2.0 * proximity)

        def reconciled(
            seconds: float,
            source_product: str,
            base: _ResolvedDeltaT,
            *boundary_terms: tuple[_ResolvedDeltaT, float],
        ) -> _ResolvedDeltaT:
            terms = list(base.tidal_terms)
            for boundary, coefficient in boundary_terms:
                terms.extend(_scaled_tidal_terms(boundary, coefficient))
            return _resolved_delta_t(seconds, source_product, tuple(terms))

        if not data:
            return model_product(jd_ut1)

        keys = cls._ordered_mjds(data)
        first_segment = cls._segment_bounds(keys[0], data)
        last_segment = cls._segment_bounds(keys[-1], data)
        assert first_segment is not None and last_segment is not None
        first_ut1, first_dt = first_segment[0], first_segment[1]
        last_ut1, last_dt = last_segment[2], last_segment[3]
        first_model = model_product(first_ut1)
        last_model = model_product(last_ut1)
        first_correction = first_dt - first_model.seconds
        last_correction = last_dt - last_model.seconds
        base = model_product(jd_ut1)

        if jd_ut1 <= first_ut1:
            weight = taper_weight(first_ut1 - jd_ut1)
            if weight == 0.0:
                return base
            return reconciled(
                base.seconds + first_correction * weight,
                "eop_first_boundary_handoff",
                base,
                (first_model, -weight),
            )
        if jd_ut1 >= last_ut1:
            weight = taper_weight(jd_ut1 - last_ut1)
            if weight == 0.0:
                return base
            return reconciled(
                base.seconds + last_correction * weight,
                "eop_last_boundary_handoff",
                base,
                (last_model, -weight),
            )

        mjd_value = jd_ut1 - 2400000.5
        right_index = bisect.bisect_right(keys, mjd_value)
        # A positive DUT1 places a row's UT1 start just after its integer-MJD
        # UTC label.  In that narrow interval bisect has already stepped past
        # the row even though it is still the right-hand boundary of the gap.
        if right_index > 0:
            candidate = cls._segment_bounds(keys[right_index - 1], data)
            assert candidate is not None
            if jd_ut1 < candidate[0]:
                right_index -= 1
        if right_index <= 0 or right_index >= len(keys):
            # The explicit first/last UT1 boundary checks above should own
            # these cases; retain a deterministic nearest-boundary fallback
            # against floating-point label/coordinate edge effects.
            if right_index <= 0:
                correction = first_correction
                boundary_model = first_model
            else:
                correction = last_correction
                boundary_model = last_model
            return reconciled(
                base.seconds + correction,
                "eop_nearest_boundary_handoff",
                base,
                (boundary_model, -1.0),
            )
        left_mjd = keys[right_index - 1]
        right_mjd = keys[right_index]
        left_segment = cls._segment_bounds(left_mjd, data)
        right_segment = cls._segment_bounds(right_mjd, data)
        assert left_segment is not None and right_segment is not None
        left_ut1, left_dt = left_segment[2], left_segment[3]
        right_ut1, right_dt = right_segment[0], right_segment[1]
        left_model = model_product(left_ut1)
        right_model = model_product(right_ut1)
        left_correction = left_dt - left_model.seconds
        right_correction = right_dt - right_model.seconds
        span = right_ut1 - left_ut1
        if span <= 0.0:
            return reconciled(
                base.seconds + left_correction,
                "eop_gap_left_boundary_handoff",
                base,
                (left_model, -1.0),
            )
        fraction = min(1.0, max(0.0, (jd_ut1 - left_ut1) / span))
        correction = left_correction + fraction * (
            right_correction - left_correction
        )
        return reconciled(
            base.seconds + correction,
            "eop_internal_gap_handoff",
            base,
            (left_model, -(1.0 - fraction)),
            (right_model, -fraction),
        )

    @classmethod
    def _model_delta_t_handoff(cls, jd_ut1: float) -> float:
        """Return only the raw seconds from the source-aware EOP handoff."""

        return cls._model_delta_t_handoff_resolved(jd_ut1).seconds

    @classmethod
    def get_dut1(cls, jd_utc: float) -> float:
        """Return UT1-UTC in seconds for a given JD."""
        value = cls._dut1_optional(jd_utc)
        return 0.0 if value is None else value

    @classmethod
    def _load(cls) -> None:
        if not cls._path.exists():
            cls._data = {}
            return
        rows: dict[int, float] = {}
        previous_mjd: int | None = None
        with cls._path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                parts = stripped.split()
                if len(parts) != 2:
                    raise ValueError(
                        f"Malformed EOP row {cls._path}:{line_number}: "
                        "expected exactly two numeric fields"
                    )
                try:
                    mjd_value = float(parts[0])
                    dut1 = float(parts[1])
                except ValueError as exc:
                    raise ValueError(
                        f"Malformed EOP row {cls._path}:{line_number}: non-numeric field"
                    ) from exc
                if not math.isfinite(mjd_value) or not mjd_value.is_integer():
                    raise ValueError(
                        f"Malformed EOP row {cls._path}:{line_number}: MJD must be a finite integer"
                    )
                if not math.isfinite(dut1) or abs(dut1) > _MAX_ABS_DUT1_SECONDS:
                    raise ValueError(
                        f"Malformed EOP row {cls._path}:{line_number}: "
                        f"DUT1 must be finite and within [-{_MAX_ABS_DUT1_SECONDS:g}, +{_MAX_ABS_DUT1_SECONDS:g}] seconds"
                    )
                mjd = int(mjd_value)
                if previous_mjd is not None and mjd <= previous_mjd:
                    raise ValueError(
                        f"Malformed EOP row {cls._path}:{line_number}: "
                        "MJD values must be strictly increasing and unique"
                    )
                rows[mjd] = dut1
                previous_mjd = mjd
        if not rows:
            raise ValueError(f"EOP data file contains no rows: {cls._path}")
        cls._data = rows


def utc_to_ut1(jd_utc: float) -> float:
    """
    Convert Julian Day in UTC to Universal Time (UT1).
    This bridges civil time to Earth's rotation for sidereal calculations.
    """
    _require_representable_time_jd("jd_utc", jd_utc)
    # Prefer admitted DUT1 from the IERS registry if available.  ``None`` is
    # the missing-data sentinel because zero is a valid admitted DUT1 value.
    dut1 = EOPRegistry._dut1_optional(jd_utc)
    if dut1 is not None:
        return jd_utc + dut1 / 86400.0

    # The bundled atomic UTC authority begins on 1972-01-01.  Earlier civil
    # timestamps retain Moira's explicit historical convention: their numeric
    # JD is the UT1 proxy.  Using the pre-1972 ``TAI-UTC = 10 s`` placeholder
    # here would create a false shift of 42.184 s - Delta-T, reaching hours for
    # ancient dates.
    atomic_boundary = LEAP_SECONDS[0][0]
    if jd_utc < atomic_boundary:
        handoff_start = atomic_boundary - _UTC_ATOMIC_HANDOFF_WINDOW_DAYS
        if jd_utc <= handoff_start:
            return jd_utc

        # A hard proxy-to-atomic switch is non-injective because the first
        # atomic rule places UT1 slightly before its UTC boundary.  Reconcile
        # only the final civil day with a monotonic smoothstep.  This is an
        # explicit clock-policy handoff, not reconstructed pre-1972 DUT1 data.
        atomic_boundary_ut1 = _atomic_utc_to_ut1(atomic_boundary)
        proximity = (jd_utc - handoff_start) / _UTC_ATOMIC_HANDOFF_WINDOW_DAYS
        smoothstep = proximity * proximity * (3.0 - 2.0 * proximity)
        return jd_utc + smoothstep * (atomic_boundary_ut1 - atomic_boundary)
        
    # Outside EOP coverage, solve the same boundary-conditioned TT/UT1
    # relation used by the inverse conversion.  This keeps both directions on
    # one continuous model surface.
    return tt_to_ut(utc_to_tt(jd_utc))


def utc_to_ut1_with_truth(jd_utc: float) -> UtcToUt1Truth:
    """Convert UTC to UT1 and disclose the admitted/proxy/model branch used."""

    value = float(jd_utc)
    _require_representable_time_jd("jd_utc", value)
    admitted_dut1 = EOPRegistry._dut1_optional(value)
    result = utc_to_ut1(value)
    atomic_boundary = LEAP_SECONDS[0][0]
    handoff_start = atomic_boundary - _UTC_ATOMIC_HANDOFF_WINDOW_DAYS

    if admitted_dut1 is not None:
        source_mode = "iers_eop_admitted_dut1"
        admitted_eop_applied = True
        historical_proxy_applied = False
        dut1_seconds = admitted_dut1
    elif value <= handoff_start:
        source_mode = "historical_civil_jd_as_ut1_proxy"
        admitted_eop_applied = False
        historical_proxy_applied = True
        dut1_seconds = 0.0
    elif value < atomic_boundary:
        source_mode = "historical_proxy_to_atomic_smooth_handoff"
        admitted_eop_applied = False
        historical_proxy_applied = True
        dut1_seconds = (result - value) * 86400.0
    else:
        source_mode = "atomic_utc_with_delta_t_model_outside_eop"
        admitted_eop_applied = False
        historical_proxy_applied = False
        dut1_seconds = (result - value) * 86400.0

    delta_source = None
    if source_mode != "historical_civil_jd_as_ut1_proxy":
        delta_source = _resolve_delta_t_for_ut1(result).source_product
    return UtcToUt1Truth(
        jd_utc=value,
        jd_ut1=result,
        dut1_seconds=dut1_seconds,
        source_mode=source_mode,
        admitted_eop_applied=admitted_eop_applied,
        historical_proxy_applied=historical_proxy_applied,
        delta_t_source_product=delta_source,
    )


def utc_to_tt_with_truth(jd_utc: float) -> UtcToTtTruth:
    """Convert UTC to TT and disclose the atomic or historical policy branch."""

    value = float(jd_utc)
    _require_representable_time_jd("jd_utc", value)
    ut1_truth = utc_to_ut1_with_truth(value)
    delta_truth = delta_t_from_jd_with_truth(ut1_truth.jd_ut1)
    result = utc_to_tt(value)
    if ut1_truth.source_mode == "historical_proxy_to_atomic_smooth_handoff":
        conversion_mode = "historical_proxy_to_atomic_handoff_plus_Delta_T"
        atomic_offset = None
        delta_t_applied = True
    elif value < LEAP_SECONDS[0][0]:
        conversion_mode = "historical_civil_UT1_proxy_plus_Delta_T"
        atomic_offset = None
        delta_t_applied = True
    else:
        conversion_mode = "atomic_UTC_to_TAI_to_TT"
        atomic_offset = tai_minus_utc(value)
        delta_t_applied = False
    return UtcToTtTruth(
        jd_utc=value,
        jd_ut1=ut1_truth.jd_ut1,
        jd_tt=result,
        delta_t_seconds=delta_truth.seconds,
        delta_t_source_product=delta_truth.source_product,
        conversion_mode=conversion_mode,
        tai_minus_utc_seconds=atomic_offset,
        delta_t_applied_to_tt_conversion=delta_t_applied,
    )


def _leap_second_gap(jd_ut1: float) -> tuple[float, float, float, float] | None:
    """Locate a UT1 instant inside an inserted leap second.

    Returns ``(leap_jd, jd_tt, gap_start_tt, gap_end_tt)``, where ``leap_jd`` is the
    UTC-coded Julian Day of the boundary 00:00 after the leap day and the two
    ``gap`` values bound the one-second TT interval that no UTC-coded Julian Day
    labels; ``None`` when ``jd_ut1`` is not inside a leap second.

    Side effects: None.
    """

    index = bisect.bisect_right(LEAP_SECONDS, (jd_ut1 + 2.0, float("inf"))) - 1
    for candidate in (index, index - 1):
        if candidate < 1:
            continue
        leap_jd, post_offset = LEAP_SECONDS[candidate]
        pre_offset = LEAP_SECONDS[candidate - 1][1]
        if post_offset <= pre_offset:
            continue
        gap_start_tt = leap_jd + (pre_offset + TAI_TT_OFFSET) / 86400.0
        gap_end_tt = leap_jd + (post_offset + TAI_TT_OFFSET) / 86400.0
        jd_tt = ut_to_tt(jd_ut1)
        if gap_start_tt <= jd_tt < gap_end_tt:
            return leap_jd, jd_tt, gap_start_tt, gap_end_tt
    return None


def _leap_second_gap_utc(jd_ut1: float) -> float | None:
    """UTC label for a UT1 instant that falls inside an inserted leap second.

    A UTC-coded Julian Day has 86400 seconds per day, so the inserted second
    23:59:60 has no label: :func:`utc_to_tt` steps by one second at the leap
    boundary ``D`` and no UTC JD maps to the TT interval
    ``[D + (pre + 32.184 s), D + (post + 32.184 s))``.  Without a rule the
    inversion alternated between the two sides of the step, which made the
    label run backwards in time and put the round trip through TT one second
    out.  The rule here is monotone and nearest-boundary: the first half of the
    gap takes the last representable instant before ``D``, the second half takes
    ``D``, so the TT round trip is off by at most 0.5 s and only inside that
    one second.  Timing code must not use the label inside the gap; it takes TT
    directly (every event path does, through ``_ut1_to_ephemeris_tt``).

    Returns ``None`` when ``jd_ut1`` is not inside a leap second.  Civil display
    that can carry second 60 uses :func:`utc_calendar_from_ut1` instead.

    Side effects: None.
    """

    gap = _leap_second_gap(jd_ut1)
    if gap is None:
        return None
    leap_jd, jd_tt, gap_start_tt, gap_end_tt = gap
    if jd_tt < 0.5 * (gap_start_tt + gap_end_tt):
        return math.nextafter(leap_jd, -math.inf)
    return leap_jd


def _ut1_to_utc(jd_ut1: float) -> float:
    """Convert a UT1 JD to the corresponding civil UTC-coded JD.

    This is private display/serialization plumbing.  Within bundled EOP
    coverage it inverts the admitted daily segment directly.  Outside that
    coverage it preserves the pre-1972 historical UT1-proxy convention, or
    solves the post-1972 atomic UTC relation through the shared TT instant.
    An instant inside an inserted leap second has no UTC-coded JD and takes the
    deterministic label of :func:`_leap_second_gap_utc`.
    """

    _require_representable_time_jd("jd_ut1", jd_ut1)
    gap_label = _leap_second_gap_utc(jd_ut1)
    if gap_label is not None:
        return gap_label
    admitted_utc = EOPRegistry._utc_from_ut1(jd_ut1)
    if admitted_utc is not None:
        return admitted_utc

    atomic_boundary = LEAP_SECONDS[0][0]
    handoff_start = atomic_boundary - _UTC_ATOMIC_HANDOFF_WINDOW_DAYS
    atomic_boundary_ut1 = _atomic_utc_to_ut1(atomic_boundary)
    if handoff_start <= jd_ut1 < atomic_boundary_ut1:
        low = handoff_start
        high = atomic_boundary
        for _ in range(64):
            midpoint = (low + high) / 2.0
            if utc_to_ut1(midpoint) < jd_ut1:
                low = midpoint
            else:
                high = midpoint
        candidates = (low, high, (low + high) / 2.0)
        return min(candidates, key=lambda value: abs(utc_to_ut1(value) - jd_ut1))
    if jd_ut1 < handoff_start:
        return jd_ut1

    jd_tt = ut_to_tt(jd_ut1)
    jd_utc = jd_tt - (
        TAI_TT_OFFSET + tai_minus_utc(jd_ut1)
    ) / 86400.0
    for _ in range(8):
        next_utc = jd_tt - (
            TAI_TT_OFFSET + tai_minus_utc(jd_utc)
        ) / 86400.0
        if next_utc == jd_utc:
            break
        jd_utc = next_utc
    return jd_utc


def utc_calendar_from_ut1(jd_ut1: float) -> CalendarDateTime:
    """Civil UTC calendar time of a UT1 instant, carrying an inserted leap second.

    Inside a leap second the result is ``23:59:60.x`` on the leap day (``x`` the
    real elapsed fraction of that second from TT), which :class:`CalendarDateTime`
    holds and ISO 8601 / RFC 3339 allow but ``datetime`` cannot.  Everywhere else
    it is the calendar form of :func:`_ut1_to_utc`.  Use this for display and
    serialization of a UT1 instant; timing code takes TT, never a civil label.

    Raises:
        ValueError: If ``jd_ut1`` is not finite and representable.

    Side effects: None.
    """

    _require_representable_time_jd("jd_ut1", jd_ut1)
    gap = _leap_second_gap(jd_ut1)
    if gap is not None:
        leap_jd, jd_tt, gap_start_tt, _gap_end_tt = gap
        year, month, day, _hour = calendar_from_jd(leap_jd - 0.5)
        microsecond = min(999_999, int((jd_tt - gap_start_tt) * 86_400.0 * 1_000_000.0))
        return CalendarDateTime(year, month, day, 23, 59, 60, microsecond)
    return calendar_datetime_from_jd(_ut1_to_utc(jd_ut1))


def utc_datetime_from_ut1(jd_ut1: float) -> datetime:
    """UTC ``datetime`` of a UT1 instant, for CE years only.

    ``datetime`` has no second 60, so an instant inside a leap second takes the
    monotone nearest-boundary label of :func:`_leap_second_gap_utc` (23:59:59.999999
    or the following 00:00:00, at most 0.5 s away).  :func:`utc_calendar_from_ut1`
    shows the true ``23:59:60.x``.

    Raises:
        ValueError: If the instant lies outside astronomical years 1-9999.

    Side effects: None.
    """

    return datetime_from_jd(_ut1_to_utc(jd_ut1))


def safe_utc_datetime_from_ut1(jd_ut1: float) -> datetime | None:
    """:func:`utc_datetime_from_ut1`, returning ``None`` outside years 1-9999.

    Side effects: None.
    """

    return safe_datetime_from_jd(_ut1_to_utc(jd_ut1))


def ut_to_tt(
    jd_ut: float,
    year: float | None = None,
    delta_t_policy: 'DeltaTPolicy | None' = None,
) -> float:
    """
    Convert Julian Day in UT1 to Terrestrial Time (TT).

    Args:
        jd_ut: Julian Day Number in Universal Time.
        year:  Explicit decimal-year coordinate. It bypasses JD/EOP source
            selection and governs Delta-T exactly; when ``None``, the selected
            policy derives a continuous coordinate from ``jd_ut``.
        delta_t_policy: Optional ``DeltaTPolicy`` controlling which ΔT model
            is used.  When ``None``, the default hybrid model is used.

    Returns:
        Julian Day Number in TT (= jd_ut + ΔT / 86400).

    Raises:
        ValueError: If ``jd_ut`` or an explicit ``year`` is not finite.

    Side effects:
        None.
    """
    resolved = _resolve_delta_t_for_ut1(
        jd_ut,
        year=year,
        delta_t_policy=delta_t_policy,
    )
    return jd_ut + resolved.seconds / 86400.0


def ut_to_tt_nasa_canon(jd_ut: float, year: float | None = None) -> float:
    """
    Convert a UT Julian Day to TT using the NASA eclipse-canon ``delta_t_nasa_canon()``.

    Args:
        jd_ut: Julian Day Number in Universal Time.
        year:  Explicit NASA decimal-year coordinate. Pass the public
            month-midpoint convention when reproducing a catalog row. When
            ``None``, a continuous calendar-year coordinate removes the
            catalog convention's artificial monthly steps. The raw NASA
            polynomial's own piecewise boundary seams remain visible.

    Returns:
        Julian Day Number in TT (= jd_ut + ΔT_nasa / 86400).

    Side effects:
        None.
    """
    _require_representable_time_jd("jd_ut", jd_ut)
    if year is not None:
        _require_finite("year", year)
    if year is None:
        year = _continuous_decimal_year_from_jd(jd_ut)
    dt_sec = delta_t_nasa_canon(float(year))
    return jd_ut + dt_sec / 86400.0


_NASA_CANON_SEAM_YEARS: tuple[int, ...] = (
    -500,
    500,
    1600,
    1700,
    1800,
    1860,
    1900,
    1920,
    1941,
    1955,
    1961,
    1986,
    2005,
    2050,
    2150,
)


def _nasa_canon_noninvertible_seam(jd_tt: float) -> int | None:
    """Return the raw NASA polynomial seam owning an ambiguous/gap TT."""

    for year in _NASA_CANON_SEAM_YEARS:
        boundary = julian_day(year, 1, 1)
        samples_ut = (
            math.nextafter(boundary, -math.inf),
            boundary,
            math.nextafter(boundary, math.inf),
        )
        samples_tt = tuple(
            ut_to_tt_nasa_canon(jd_ut) for jd_ut in samples_ut
        )
        for left_ut, right_ut, left_tt, right_tt in zip(
            samples_ut,
            samples_ut[1:],
            samples_tt,
            samples_tt[1:],
        ):
            jump_seconds = (
                (right_tt - left_tt) - (right_ut - left_ut)
            ) * 86400.0
            if abs(jump_seconds) <= 1.0e-6:
                continue
            low, high = sorted((left_tt, right_tt))
            if right_tt < left_tt:
                if low <= jd_tt <= high:
                    return year
            elif low < jd_tt < high:
                return year
    return None


def tt_to_ut(
    jd_tt: float,
    year: float | None = None,
    delta_t_policy: 'DeltaTPolicy | None' = None,
) -> float:
    """
    Convert a Julian Day in TT to Universal Time (UT1) using the selected policy.

    Args:
        jd_tt: Julian Day Number in Terrestrial Time.
        year:  Explicit decimal-year coordinate. It bypasses JD/EOP source
            selection and governs the exact inverse of
            ``ut_to_tt(..., year=year)``; when ``None``, the selected policy
            iterates on a continuous coordinate.
        delta_t_policy: Optional ``DeltaTPolicy`` controlling which ΔT model
            is used.  When ``None``, the default hybrid model is used.

    Returns:
        Julian Day Number in UT (= jd_tt − ΔT / 86400).

    Raises:
        ValueError: If ``jd_tt`` or an explicit ``year`` is not finite.

    Side effects:
        None.
    """
    # ΔT depends on the UT year, but UT is what is being solved for.  Iterate
    # to self-consistency (4 passes converge to sub-millisecond accuracy).
    _require_representable_time_jd("jd_tt", jd_tt)
    explicit_year = year is not None
    if year is not None:
        _require_finite("year", year)
    if year is None:
        year = _policy_year_from_jd(jd_tt, delta_t_policy)
    if delta_t_policy is None or delta_t_policy.model == 'hybrid':
        if explicit_year:
            return jd_tt - delta_t(float(year)) / 86400.0

        admitted_ut1 = EOPRegistry._ut1_from_tt(jd_tt)
        if admitted_ut1 is not None:
            return admitted_ut1

        # The input coordinate is TT, not UT1, so seed from the year model,
        # then solve on the boundary-conditioned JD surface.
        jd_ut = jd_tt - delta_t(float(year)) / 86400.0
        for _ in range(8):
            dt_sec = delta_t_from_jd(jd_ut)
            jd_ut = jd_tt - dt_sec / 86400.0
    else:
        if explicit_year:
            return jd_tt - delta_t_policy.compute(float(year)) / 86400.0
        if delta_t_policy.model == "nasa_canon":
            return tt_to_ut_nasa_canon(jd_tt)
        jd_ut = jd_tt - delta_t_policy.compute(float(year)) / 86400.0
        for _ in range(4):
            y = _policy_year_from_jd(jd_ut, delta_t_policy)
            jd_ut = jd_tt - delta_t_policy.compute(y) / 86400.0
    return jd_ut


def tt_to_ut_nasa_canon(jd_tt: float, year: float | None = None) -> float:
    """
    Convert a TT Julian Day to UT using the NASA eclipse-canon Delta T model.

    With no explicit coordinate, the function solves the continuous-year
    equation by fixed-point iteration. The raw NASA piecewise polynomial has
    small discontinuities at several model boundaries; TT intervals that are
    ambiguous or absent at those seams fail explicitly rather than selecting
    a silent branch.

    Args:
        jd_tt: Julian Day Number in Terrestrial Time.
        year:  Explicit NASA decimal-year coordinate. When supplied it governs
            the exact inverse of the matching forward call. When ``None``, a
            continuous calendar-year coordinate is solved iteratively.

    Returns:
        Julian Day Number in UT, self-consistent with ``delta_t_nasa_canon()``.

    Raises:
        ValueError: If ``jd_tt`` or an explicit ``year`` is not finite, or if
            the no-hint inverse lies in a non-invertible raw-model seam.

    Side effects:
        None.
    """
    _require_representable_time_jd("jd_tt", jd_tt)
    explicit_year = year is not None
    if year is not None:
        _require_finite("year", year)
    if year is None:
        year = _continuous_decimal_year_from_jd(jd_tt)
    if explicit_year:
        return jd_tt - delta_t_nasa_canon(float(year)) / 86400.0
    seam_year = _nasa_canon_noninvertible_seam(jd_tt)
    if seam_year is not None:
        raise ValueError(
            "NASA-canon raw polynomial time conversion is not uniquely "
            f"invertible at the {seam_year} model seam; pass an explicit "
            "year coordinate or use the hybrid clock policy"
        )
    jd_ut = jd_tt - delta_t_nasa_canon(float(year)) / 86400.0
    for _ in range(4):
        y = _continuous_decimal_year_from_jd(jd_ut)
        jd_ut = jd_tt - delta_t_nasa_canon(y) / 86400.0
    return jd_ut


# ---------------------------------------------------------------------------
# TT <-> TDB -- pinned NAIF LSK operational model
# ---------------------------------------------------------------------------

# NASA/JPL NAIF ``naif0012.tls`` (retrieved 2026-09-15).  The source artifact
# is deliberately identified beside the constants so downstream provenance
# does not have to duplicate or infer the time model.
NAIF_LSK_TT_TDB_POLICY = "NAIF_LSK_DELTET"
NAIF_LSK_TT_TDB_VERSION = "naif0012"
NAIF_LSK_TT_TDB_SOURCE_URL = (
    "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls"
)
NAIF_LSK_TT_TDB_SOURCE_BYTES = 5257
NAIF_LSK_TT_TDB_SOURCE_SHA256 = (
    "678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b"
)

_NAIF_DELTET_K_SECONDS = 1.657e-3
_NAIF_DELTET_EB = 1.671e-2
_NAIF_DELTET_M0_RADIANS = 6.239996
_NAIF_DELTET_M1_RADIANS_PER_SECOND = 1.99096871e-7
_TT_TDB_FIXED_POINT_MAX_ITERATIONS = 8
_TT_TDB_FIXED_POINT_RESIDUAL_SECONDS = 1e-15
_SECONDS_PER_DAY = 86400.0


@dataclass(frozen=True, slots=True)
class _TtTdbConversion:
    """Private receipt for one pinned TT/TDB conversion."""

    epoch_tt: float
    epoch_tdb: float
    tdb_minus_tt_seconds: float
    iterations: int


def _require_tt_tdb_jd(name: str, value: float) -> float:
    """Return one finite, representable, non-Boolean Julian-day coordinate."""

    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real number other than bool")
    result = float(value)
    _require_representable_time_jd(name, result)
    return result


def _naif_tdb_minus_tt_seconds_at_tdb(epoch_tdb: float) -> float:
    """Evaluate the pinned LSK periodic term at a TDB Julian day.

    ``naif0012.tls`` defines ``M`` in ephemeris seconds from J2000 and the
    operational relation ``TDB-TT = K*sin(M + EB*sin(M))``.  Reducing the
    phase before calling ``sin`` keeps the arithmetic well conditioned over
    Moira's admitted time-transform domain.
    """

    seconds_from_j2000 = math.fsum((epoch_tdb, -J2000)) * _SECONDS_PER_DAY
    mean_anomaly = math.remainder(
        _NAIF_DELTET_M0_RADIANS
        + _NAIF_DELTET_M1_RADIANS_PER_SECOND * seconds_from_j2000,
        math.tau,
    )
    eccentric_anomaly = mean_anomaly + _NAIF_DELTET_EB * math.sin(mean_anomaly)
    return _NAIF_DELTET_K_SECONDS * math.sin(eccentric_anomaly)


def _tt_to_tdb_with_receipt(jd_tt: float) -> _TtTdbConversion:
    """Convert TT to TDB and retain the pre-assembly periodic offset."""

    epoch_tt = _require_tt_tdb_jd("jd_tt", jd_tt)
    epoch_tdb = epoch_tt
    previous_offset: float | None = None
    for iteration in range(1, _TT_TDB_FIXED_POINT_MAX_ITERATIONS + 1):
        offset_seconds = _naif_tdb_minus_tt_seconds_at_tdb(epoch_tdb)
        epoch_tdb = math.fsum((epoch_tt, offset_seconds / _SECONDS_PER_DAY))
        if (
            previous_offset is not None
            and abs(offset_seconds - previous_offset)
            <= _TT_TDB_FIXED_POINT_RESIDUAL_SECONDS
        ):
            return _TtTdbConversion(
                epoch_tt=epoch_tt,
                epoch_tdb=epoch_tdb,
                tdb_minus_tt_seconds=offset_seconds,
                iterations=iteration,
            )
        previous_offset = offset_seconds
    raise ArithmeticError(
        "NAIF LSK TT-to-TDB fixed-point iteration did not converge"
    )


def tt_to_tdb(jd_tt: float) -> float:
    """Convert a TT Julian day to TDB using pinned ``naif0012.tls``.

    The LSK expression is implicit because its phase is a function of TDB
    seconds from J2000.  Moira solves that fixed point under a bounded policy
    and returns the nearest representable single-part binary64 Julian day.
    """

    return _tt_to_tdb_with_receipt(jd_tt).epoch_tdb


def tdb_to_tt(jd_tdb: float) -> float:
    """Invert Moira's pinned NAIF LSK TT-to-TDB policy."""

    epoch_tdb = _require_tt_tdb_jd("jd_tdb", jd_tdb)
    offset_seconds = _naif_tdb_minus_tt_seconds_at_tdb(epoch_tdb)
    return math.fsum((epoch_tdb, -offset_seconds / _SECONDS_PER_DAY))


# ---------------------------------------------------------------------------
# Sidereal time
# ---------------------------------------------------------------------------

@accelerate("earth_rotation_angle")
def earth_rotation_angle(jd_ut: float) -> float:
    """
    Compute the Earth Rotation Angle (ERA) in degrees.

    Implements the IAU 2000 linear model (IERS Conventions 2010 §5.4.2;
    SOFA ``iauEra00``):

        ERA = 360 * (0.7790572732640 + 1.00273781191135448 * D)  mod 360

    where D = JD(UT1) − 2451545.0.

    Args:
        jd_ut: Julian Day Number in UT1.

    Returns:
        ERA in degrees, normalised to [0, 360).

    Raises:
        Nothing — pure arithmetic.

    Side effects:
        None.
    """
    # SOFA iauEra00 evaluation order: the whole turns carried by the Julian
    # day fraction are taken exactly, and only the 0.0027378... excess rate
    # multiplies the long baseline.  Multiplying the full 1.0027378... rate by
    # D instead loses ~0.3 mas at -2000 to binary64 rounding.
    D = jd_ut - J2000
    era_turns = math.fmod(jd_ut, 1.0) + 0.7790572732640 + 0.00273781191135448 * D
    return (era_turns % 1.0) * 360.0


def _resolve_sidereal_jd_tt(jd_ut: float, jd_tt: float | None) -> float:
    """Return the TT coordinate that accompanies one UT1 sidereal-time epoch.

    Earth rotation (ERA) is a function of UT1, while the precession
    polynomial, nutation, and equation of the equinoxes are functions of TT
    (IERS Conventions 2010 §5.5; SOFA ``iauGmst06``/``iauGst06a``).  A caller
    that holds a reader-bound or otherwise policy-selected TT supplies it
    verbatim.  When it supplies none, TT is derived from ``jd_ut`` with the
    default Delta-T policy (:func:`ut_to_tt`); the UT1 value is never reused
    as a TT coordinate.
    """
    _require_representable_time_jd("jd_ut", jd_ut)
    if jd_tt is None:
        return ut_to_tt(jd_ut)
    _require_representable_time_jd("jd_tt", jd_tt)
    return float(jd_tt)


def greenwich_mean_sidereal_time(jd_ut: float, jd_tt: float | None = None) -> float:
    """
    Compute Greenwich Mean Sidereal Time (GMST) in degrees.

    Governs the IAU 2006 formula (Capitaine et al. 2003, A&A 412, 567–586;
    SOFA ``iauGmst06``). This is the Earth Rotation Angle (ERA, a function of
    UT1) plus a 5th-order polynomial correction (a function of TT) that
    accounts for the offset between the mean equinox and the Celestial
    Intermediate Origin.  This is *not* the older IAU 1982 polynomial (Aoki
    et al. 1982); the two differ by up to ~0.55 arcsec at dates two centuries
    from J2000.

    Args:
        jd_ut: Julian Day Number in UT1.
        jd_tt: Julian Day Number in TT for the same instant.  When ``None``
            it is derived as ``ut_to_tt(jd_ut)`` under the default Delta-T
            policy; pass the caller's bound TT to keep one clock per
            computation.

    Returns:
        GMST in degrees, normalised to [0, 360).

    Raises:
        ValueError: If either epoch is not finite and representable.

    Side effects:
        None.
    """
    return _greenwich_mean_sidereal_time_at_tt(jd_ut, _resolve_sidereal_jd_tt(jd_ut, jd_tt))


@accelerate("greenwich_mean_sidereal_time")
def _greenwich_mean_sidereal_time_at_tt(jd_ut1: float, jd_tt: float) -> float:
    """IAU 2006 GMST: ERA at UT1, equinox precession polynomial at TT.

    Source: SOFA/ERFA gmst06 (Capitaine et al. 2003). No clock conversion is
    performed here; the caller owns both coordinates.  The native
    counterpart is ``greenwich_mean_sidereal_time(jd_ut, jd_tt)``.
    """
    D = jd_tt - J2000           # TT days from J2000.0
    T = D / JULIAN_CENTURY       # Julian centuries

    # Earth Rotation Angle (ERA) — IAU 2000 definition of UT1
    era_deg = earth_rotation_angle(jd_ut1)

    # Polynomial correction (arcseconds → degrees)
    poly_arcsec = (  0.014506
                   + 4612.156534    * T
                   +    1.3915817   * T**2
                   -    0.00000044  * T**3
                   -    0.000029956 * T**4
                   -    0.0000000368* T**5)

    return (era_deg + poly_arcsec / 3600.0) % 360.0


def _gast_complementary_terms(jd_ut: float) -> float:
    """
    IAU 2006 complementary terms for the equation of the equinoxes (degrees).

    These periodic terms (Capitaine et al. 2003; IERS Conventions 2010 §5.4.4)
    correct GAST beyond the simple Δψ·cos(ε) IAU 1982 formula.  The dominant
    term peaks at ±0.00264″ (from the Moon's node Ω); all terms sum to ≤0.04″.

    Reference: IERS TN 36, Table 5.2c; SOFA iauEect00.
    """
    T   = (jd_ut - J2000) / JULIAN_CENTURY
    tau = math.tau

    # Fundamental arguments (arcseconds → radians via modulo 2π)
    arcsec = math.pi / 648000.0

    # Moon's ascending node Ω (dominant source of CT)
    Om  = (450160.398036 + T * (-6962890.5431 + T * (7.4722 + T * 0.007702))) * arcsec
    Om  = Om % tau

    # Moon's argument of latitude F
    F   = (335779.526232 + T * 1739527262.8478) * arcsec % tau

    # Moon's mean elongation D
    D   = (1072260.703692 + T * 1602961601.2090) * arcsec % tau

    # Complementary terms (IERS 2010, Table 5.2c) — arcseconds
    ct  = (  0.00264096 * math.sin(Om)
           + 0.00006352 * math.sin(2.0 * Om)
           + 0.00001175 * math.sin(2.0 * F - 2.0 * D + 3.0 * Om)
           + 0.00001121 * math.sin(2.0 * F - 2.0 * D + Om)
           - 0.00000455 * math.sin(2.0 * F - 2.0 * D + 2.0 * Om)
           + 0.00000202 * math.sin(2.0 * F + 3.0 * Om)
           + 0.00000198 * math.sin(2.0 * F + Om)
           - 0.00000172 * math.sin(3.0 * Om)
           - 0.00000087 * T * math.sin(Om))

    return ct / 3600.0   # arcseconds → degrees


def _local_sidereal_time_at_tt(jd_ut1: float, jd_tt: float, longitude: float,
                               nutation_longitude: float, mean_obliquity: float) -> float:
    """Reader-bound LAST with TT equinox terms and UT1 Earth rotation.

    Equation of the equinoxes uses mean obliquity (SOFA/ERFA ee00), while
    horizon/ecliptic geometry separately uses true obliquity. Reuses Moira's
    existing complementary-term approximation, evaluated here at TT.
    """
    gmst = _greenwich_mean_sidereal_time_at_tt(jd_ut1, jd_tt)
    ee = (nutation_longitude * math.cos(math.radians(mean_obliquity))
          + _gast_complementary_terms(jd_tt))
    return (gmst + ee + longitude) % 360.0


def _mean_obliquity_p03_degrees(jd: float) -> float:
    """IAU 2006 mean obliquity ε_A in degrees (SOFA ``iauObl06``).

    Mirrors ``moira.precession.mean_obliquity_p03`` and the native
    ``mean_obliquity_p03``; it lives here because ``precession`` imports this
    module.  Term order matches the native evaluation.
    """
    T = (jd - J2000) / JULIAN_CENTURY
    return (84381.406
            - 46.836769 * T
            - 0.0001831 * T * T
            + 0.00200340 * T * T * T
            - 0.000000576 * T * T * T * T
            - 0.0000000434 * T * T * T * T * T) / 3600.0


def apparent_sidereal_time(
    jd_ut: float,
    nutation_longitude: float,
    obliquity: float,
    jd_tt: float | None = None,
) -> float:
    """
    Compute Greenwich Apparent Sidereal Time (GAST) in degrees.

    Governs the full IAU 2006 equation of the equinoxes (SOFA ``iauEe00``):
        EE = Δψ · cos(ε_A) + CT
    where ε_A is the IAU 2006 *mean* obliquity and CT are the Capitaine et
    al. (2003) complementary terms (≤ 0.04″) computed by
    ``_gast_complementary_terms()``.  Time scales follow SOFA ``iauGst06a``:
    the Earth rotation angle uses UT1, while the GMST precession polynomial,
    ε_A, and CT use TT.

    Args:
        jd_ut:              Julian Day Number in UT1.
        nutation_longitude: Δψ (nutation in longitude) in degrees, evaluated
                            at TT by the caller.
        obliquity:          Retained for API compatibility and ignored.
                            Callers pass the *true* obliquity they use for
                            horizon/ecliptic geometry; using it in EE would
                            bias GAST by up to ~0.26 mas against SOFA.
        jd_tt:              Julian Day Number in TT for the same instant.
                            When ``None`` it is derived as
                            ``ut_to_tt(jd_ut)`` under the default Delta-T
                            policy; a caller that holds a reader-bound TT
                            passes it so Δψ and the sidereal time share one
                            clock.

    Returns:
        GAST in degrees, normalised to [0, 360).

    Raises:
        ValueError: If either epoch is not finite and representable.

    Side effects:
        None.
    """
    tt = _resolve_sidereal_jd_tt(jd_ut, jd_tt)
    return _apparent_sidereal_time_at_tt(jd_ut, tt, nutation_longitude)


@accelerate("apparent_sidereal_time")
def _apparent_sidereal_time_at_tt(jd_ut1: float, jd_tt: float, nutation_longitude: float) -> float:
    """GAST with UT1 Earth rotation and TT equinox terms (SOFA ``iauGst06a``/``iauEe00``).

    The native counterpart is ``apparent_sidereal_time(jd_ut, jd_tt,
    nutation_longitude)``.  No clock conversion is performed here.
    """
    gmst = _greenwich_mean_sidereal_time_at_tt(jd_ut1, jd_tt)
    ee   = (nutation_longitude * math.cos(_mean_obliquity_p03_degrees(jd_tt) * math.pi / 180.0)
            + _gast_complementary_terms(jd_tt))
    return (gmst + ee) % 360.0


def apparent_sidereal_time_at(jd_ut: float, longitude: float = 0.0) -> float:
    """
    Compute Greenwich (or Local) Apparent Sidereal Time in degrees from a
    Julian Day alone.

    Convenience wrapper over ``apparent_sidereal_time`` that derives the
    required nutation-in-longitude and true obliquity internally.  When a
    non-zero ``longitude`` is supplied the result is Local Apparent Sidereal
    Time (LAST); at the default of 0.0 it is GAST.

    The nutation and obliquity are computed via a deferred import of
    ``moira.obliquity`` to avoid a module-level circular dependency
    (``obliquity`` imports ``julian``).

    Args:
        jd_ut:     Julian Day Number in UT1.
        longitude: Observer's geographic east longitude in degrees
                   (default 0.0 → GAST).

    Returns:
        Apparent sidereal time in degrees, normalised to [0, 360).

    Raises:
        Nothing — pure arithmetic.

    Side effects:
        None (deferred import of ``moira.obliquity`` on first call).
    """
    from .obliquity import nutation as _nutation, true_obliquity as _true_obliquity
    jd_tt = ut_to_tt(jd_ut)
    dpsi, _deps = _nutation(jd_tt)
    obl = _true_obliquity(jd_tt)
    return (apparent_sidereal_time(jd_ut, dpsi, obl, jd_tt) + longitude) % 360.0


def local_sidereal_time(jd_ut: float, longitude: float,
                        nutation_longitude: float = 0.0,
                        obliquity: float = 23.4392911,
                        jd_tt: float | None = None) -> float:
    """
    Compute Local Apparent Sidereal Time (LAST) in degrees.

    Adds the observer's geographic east longitude to GAST. When
    ``nutation_longitude`` is left at its default of 0.0 the Δψ·cos(ε_A) term
    vanishes, but the IAU 2006 complementary terms (≤ 2.6 mas) remain, so the
    result is LMST only to that bound; use
    :func:`local_sidereal_time_with_truth` with ``mode="mean"`` for exact mean
    sidereal time.  Pass the true Δψ for full apparent time.

    Args:
        jd_ut:              Julian Day Number in UT1.
        longitude:          Observer's geographic east longitude in degrees.
        nutation_longitude: Δψ in degrees, evaluated at TT (default 0.0).
        obliquity:          Retained for API compatibility and ignored; see
                            :func:`apparent_sidereal_time`. Use
                            :func:`local_sidereal_time_with_truth` for a
                            self-contained, explicit mean/apparent reduction.
        jd_tt:              Julian Day Number in TT for the same instant. When
                            ``None`` it is derived as ``ut_to_tt(jd_ut)``
                            under the default Delta-T policy.

    Returns:
        LAST in degrees, normalised to [0, 360).

    Side effects:
        None.
    """
    _require_representable_time_jd("jd_ut", jd_ut)
    _require_finite("longitude", longitude)
    _require_finite("nutation_longitude", nutation_longitude)
    _require_finite("obliquity", obliquity)
    gast = apparent_sidereal_time(jd_ut, nutation_longitude, obliquity, jd_tt)
    return (gast + longitude) % 360.0


def local_sidereal_time_with_truth(
    jd_ut: float,
    longitude: float,
    *,
    mode: str = "apparent",
    nutation_longitude: float | None = None,
    obliquity: float | None = None,
) -> LocalSiderealTimeTruth:
    """Return explicit LMST or LAST with the complete UT1/TT reduction truth.

    The legacy :func:`local_sidereal_time` keeps its historical defaults.
    This additive surface defaults to a self-contained apparent reduction and
    derives missing equinox terms from the supplied UT1 epoch.
    """

    jd_ut1 = float(jd_ut)
    longitude_deg = float(longitude)
    _require_representable_time_jd("jd_ut", jd_ut1)
    _require_finite("longitude", longitude_deg)
    selected_mode = str(mode).strip().lower()
    if selected_mode not in {"mean", "apparent"}:
        raise ValueError("mode must be 'mean' or 'apparent'")

    jd_tt = ut_to_tt(jd_ut1)
    gmst = _greenwich_mean_sidereal_time_at_tt(jd_ut1, jd_tt)
    if selected_mode == "mean":
        if nutation_longitude is not None or obliquity is not None:
            raise ValueError(
                "mean sidereal time does not accept nutation_longitude or obliquity"
            )
        result = (gmst + longitude_deg) % 360.0
        return LocalSiderealTimeTruth(
            jd_ut1=jd_ut1,
            jd_tt=jd_tt,
            longitude_deg_east=longitude_deg,
            requested_mode=selected_mode,
            effective_mode="mean",
            local_sidereal_time_deg=result,
            greenwich_mean_sidereal_time_deg=gmst,
            equation_of_equinoxes_deg=0.0,
            nutation_longitude_deg=None,
            equation_of_equinoxes_obliquity_deg=None,
            nutation_source="not_applied",
        )

    from .obliquity import mean_obliquity as _mean_obliquity, nutation as _nutation

    derived_nutation = nutation_longitude is None
    derived_obliquity = obliquity is None
    if derived_nutation:
        dpsi, _deps = _nutation(jd_tt)
    else:
        dpsi = float(nutation_longitude)
        _require_finite("nutation_longitude", dpsi)
    if derived_obliquity:
        equation_obliquity = _mean_obliquity(jd_tt)
    else:
        equation_obliquity = float(obliquity)
        _require_finite("obliquity", equation_obliquity)

    result = _local_sidereal_time_at_tt(
        jd_ut1,
        jd_tt,
        longitude_deg,
        dpsi,
        equation_obliquity,
    )
    equation_of_equinoxes = (
        dpsi * math.cos(math.radians(equation_obliquity))
        + _gast_complementary_terms(jd_tt)
    )
    if derived_nutation and derived_obliquity:
        source = "derived_IAU_2000A_and_IAU_2006"
    elif not derived_nutation and not derived_obliquity:
        source = "caller_supplied"
    else:
        source = "mixed_caller_and_derived"
    return LocalSiderealTimeTruth(
        jd_ut1=jd_ut1,
        jd_tt=jd_tt,
        longitude_deg_east=longitude_deg,
        requested_mode=selected_mode,
        effective_mode="apparent",
        local_sidereal_time_deg=result,
        greenwich_mean_sidereal_time_deg=gmst,
        equation_of_equinoxes_deg=equation_of_equinoxes,
        nutation_longitude_deg=dpsi,
        equation_of_equinoxes_obliquity_deg=equation_obliquity,
        nutation_source=source,
    )

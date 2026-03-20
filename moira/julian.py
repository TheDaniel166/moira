"""
Moira — julian.py
The Julian Day Engine: governs all conversions between calendar dates,
Julian Day Numbers, and the time scales used by the DE441 ephemeris.

Boundary: owns the full pipeline from Python datetime / calendar tuple to
Julian Day (JD), Terrestrial Time (TT), and sidereal time. Delegates
long-range ΔT table loading to the bundled data file
``moira/data/delta_t_hpiers_2016.txt`` at import time. Does not own
coordinate transforms, house calculations, or any display formatting.

Public surface:
    CalendarDateTime,
    format_calendar_utc, format_jd_utc,
    julian_day, calendar_from_jd, jd_from_datetime,
    decimal_year, decimal_year_from_jd,
    calendar_datetime_from_jd, safe_datetime_from_jd, datetime_from_jd,
    centuries_from_j2000,
    delta_t, delta_t_nasa_canon,
    ut_to_tt, ut_to_tt_nasa_canon, tt_to_ut, tt_to_ut_nasa_canon,
    greenwich_mean_sidereal_time, apparent_sidereal_time, local_sidereal_time

Import-time side effects:
    Reads ``moira/data/delta_t_hpiers_2016.txt`` once at module load to
    populate ``_DELTA_T_HPIERS_2016``. No network I/O; no other side effects.

External dependency assumptions:
    stdlib math and datetime only (plus pathlib for the data-file load).
    No jplephem, no Qt, no third-party packages.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .constants import J2000, JULIAN_CENTURY

_DELTA_T_OBSERVED_5Y: tuple[tuple[float, float], ...] = (
    (1955.0, 31.1),
    (1960.0, 33.2),
    (1965.0, 35.7),
    (1970.0, 40.2),
    (1975.0, 45.5),
    (1980.0, 50.5),
    (1985.0, 54.3),
    (1990.0, 56.9),
    (1995.0, 60.8),
    (2000.0, 63.8),
    (2005.0, 64.7),
    (2010.0, 66.1),
)

# Historical/telescopic ΔT anchors before the modern observed table.
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

# Annual observed ΔT (TT − UT1, seconds) from IERS Bulletin B, 2015–2026.
# Finer resolution replaces the coarse 5-year table for the modern era.
# 2025–2026 are IERS Bulletin A predictions (updated as bulletins are released).
_DELTA_T_ANNUAL: tuple[tuple[float, float], ...] = (
    (2015.0, 68.1),
    (2016.0, 68.3),
    (2017.0, 68.6),
    (2018.0, 69.0),
    (2019.0, 69.2),
    (2020.0, 69.4),
    (2021.0, 69.5),
    (2022.0, 69.6),
    (2023.0, 69.5),
    (2024.0, 69.4),
    (2025.0, 69.3),
    (2026.0, 69.3),
)


def _load_delta_t_hpiers_2016() -> tuple[tuple[float, float], ...]:
    """
    Load the official HPIERS/HMNAO Delta T table derived from the 2016
    Stephenson-Morrison-Hohenkerk historical rotation model.

    The text file stores rows as:
        year  delta_t_seconds  ...

    Duplicate years are present in the source table at some boundaries; the
    later occurrence is kept.
    """
    path = Path(__file__).resolve().parent / "data" / "delta_t_hpiers_2016.txt"
    rows: dict[float, float] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            year = float(parts[0])
            dt = float(parts[1])
        except ValueError:
            continue
        rows[year] = dt
    return tuple(sorted(rows.items()))


_DELTA_T_HPIERS_2016: tuple[tuple[float, float], ...] = _load_delta_t_hpiers_2016()


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
        "frozen": ["isoformat", "date_string", "time_string"],
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


def calendar_from_jd(jd: float) -> tuple[int, int, int, float]:
    """
    Convert a Julian Day Number to a proleptic Gregorian calendar date.

    Governs the inverse Meeus algorithm (Astronomical Algorithms, ch. 7).
    Handles both the Julian calendar era (JD < 2299161, i.e. before 15 Oct
    1582) and the Gregorian era transparently via the standard alpha/A
    correction factor.

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

    if Z < 2299161:
        A = Z
    else:
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
    Convert a Python ``datetime`` to a Julian Day Number in UT.

    Naïve ``datetime`` objects are treated as UTC. Timezone-aware objects are
    first converted to UTC before the JD computation, so any tzinfo is
    accepted.

    Args:
        dt: A Python ``datetime`` (naïve or timezone-aware).

    Returns:
        Julian Day Number (UT) as a float.

    Raises:
        Nothing — delegates to ``julian_day()`` which performs no validation.

    Side effects:
        None.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3_600_000_000.0
    return julian_day(dt.year, dt.month, dt.day, hour)


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


# ---------------------------------------------------------------------------
# Julian centuries from J2000.0
# ---------------------------------------------------------------------------

def centuries_from_j2000(jd: float) -> float:
    """Return Julian centuries (T) since J2000.0 for a given JD."""
    return (jd - J2000) / JULIAN_CENTURY


# ---------------------------------------------------------------------------
# ΔT — difference TT − UT1 in seconds
#
# Uses the polynomial approximations from Morrison & Stephenson (2004)
# and Espenak & Meeus for the modern period.
# Accurate to a few seconds for historical dates; sub-second for 1900–2100.
# ---------------------------------------------------------------------------

def delta_t(year: float) -> float:
    """
    Approximate ΔT = TT − UT1 in seconds for any decimal year.

    Governs a layered lookup strategy that selects the highest-accuracy
    available source for each era:

    - 2015–2026: annual IERS Bulletin B/A observed values (sub-second).
    - 1955–2015: 5-year observed table blended into the annual table.
    - HPIERS range: tabulated values from the 2016 Stephenson-Morrison-
      Hohenkerk Earth-rotation model (loaded from disk at import time).
    - 1600–1900: historical/telescopic anchor table (Espenak & Meeus).
    - 1900–1955: denser 5-year pre-modern table.
    - All other eras: Morrison & Stephenson (2004) piecewise polynomials.

    All table-driven ranges use linear interpolation between anchor points.
    Polynomial branches are used only when no table covers the requested year.

    Args:
        year: Decimal year (e.g. ``2000.5``).

    Returns:
        ΔT in seconds (positive means TT is ahead of UT1).

    Raises:
        Nothing — the function covers all real-valued years via the
        far-past/far-future polynomial fallback.

    Side effects:
        None.
    """
    y = float(year)
    u: float

    # Annual IERS table takes priority for 2015–2026 (highest accuracy)
    _annual_start = _DELTA_T_ANNUAL[0][0]
    _annual_end   = _DELTA_T_ANNUAL[-1][0]
    if _annual_start <= y <= _annual_end:
        for (y0, dt0), (y1, dt1) in zip(_DELTA_T_ANNUAL, _DELTA_T_ANNUAL[1:]):
            if y0 <= y <= y1:
                frac = (y - y0) / (y1 - y0)
                return dt0 + frac * (dt1 - dt0)
        return _DELTA_T_ANNUAL[-1][1]

    # 5-year table for 1955–2015
    if 1955.0 <= y < _annual_start:
        # Blend last 5-year entry into first annual entry at 2015
        table = _DELTA_T_OBSERVED_5Y + ((2015.0, 68.1),)
        for (y0, dt0), (y1, dt1) in zip(table, table[1:]):
            if y0 <= y <= y1:
                frac = (y - y0) / (y1 - y0)
                return dt0 + frac * (dt1 - dt0)
        return _DELTA_T_OBSERVED_5Y[-1][1]

    # Historical table from the HPIERS/HMNAO implementation of the 2016
    # Stephenson-Morrison-Hohenkerk model. This replaces the older polynomial
    # branches for the historical era with published tabulated values.
    _hpiers_start = _DELTA_T_HPIERS_2016[0][0]
    _hpiers_end = _DELTA_T_HPIERS_2016[-1][0]
    if _hpiers_start <= y < _annual_start:
        for (y0, dt0), (y1, dt1) in zip(_DELTA_T_HPIERS_2016, _DELTA_T_HPIERS_2016[1:]):
            if y0 <= y <= y1:
                frac = (y - y0) / (y1 - y0)
                return dt0 + frac * (dt1 - dt0)
        return _DELTA_T_HPIERS_2016[-1][1]

    # Historical/telescopic anchor table for 1600–1900.
    _hist_start = _DELTA_T_HISTORICAL[0][0]
    _hist_end = _DELTA_T_HISTORICAL[-1][0]
    if _hist_start <= y < 1900.0:
        table = _DELTA_T_HISTORICAL + ((1900.0, -2.7900),)
        for (y0, dt0), (y1, dt1) in zip(table, table[1:]):
            if y0 <= y <= y1:
                frac = (y - y0) / (y1 - y0)
                return dt0 + frac * (dt1 - dt0)
        return _DELTA_T_HISTORICAL[-1][1]

    # Denser 5-year anchor table for 1900–1955.
    if 1900.0 <= y < 1955.0:
        for (y0, dt0), (y1, dt1) in zip(_DELTA_T_PRE1955_5Y, _DELTA_T_PRE1955_5Y[1:]):
            if y0 <= y <= y1:
                frac = (y - y0) / (y1 - y0)
                return dt0 + frac * (dt1 - dt0)
        return _DELTA_T_PRE1955_5Y[-1][1]

    if y < -500:
        u = (y - 1820.0) / 100.0
        return -20 + 32 * u * u

    if y < 500:
        u = y / 100.0
        return (10583.6
                - 1014.41 * u
                + 33.78311 * u**2
                - 5.952053 * u**3
                - 0.1798452 * u**4
                + 0.022174192 * u**5
                + 0.0090316521 * u**6)

    if y < 1600:
        u = (y - 1000.0) / 100.0
        return (1574.2
                - 556.01 * u
                + 71.23472 * u**2
                + 0.319781 * u**3
                - 0.8503463 * u**4
                - 0.005050998 * u**5
                + 0.0083572073 * u**6)

    if y < 1700:
        t = y - 1600.0
        return 120 - 0.9808 * t - 0.01532 * t**2 + t**3 / 7129.0

    if y < 1800:
        t = y - 1700.0
        return (8.83
                + 0.1603 * t
                - 0.0059285 * t**2
                + 0.00013336 * t**3
                - t**4 / 1174000.0)

    if y < 1860:
        t = y - 1800.0
        return (13.72
                - 0.332447 * t
                + 0.0068612 * t**2
                + 0.0041116 * t**3
                - 0.00037436 * t**4
                + 0.0000121272 * t**5
                - 0.0000001699 * t**6
                + 0.000000000875 * t**7)

    if y < 1900:
        t = y - 1860.0
        return (7.62
                + 0.5737 * t
                - 0.251754 * t**2
                + 0.01680668 * t**3
                - 0.0004473624 * t**4
                + t**5 / 233174.0)

    if y < 1920:
        t = y - 1900.0
        return (- 2.79
                + 1.494119 * t
                - 0.0598939 * t**2
                + 0.0061966 * t**3
                - 0.000197 * t**4)

    if y < 1941:
        t = y - 1920.0
        return 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3

    if y < 1961:
        t = y - 1950.0
        return 29.07 + 0.407 * t - t**2 / 233.0 + t**3 / 2547.0

    if y < 1986:
        t = y - 1975.0
        return 45.45 + 1.067 * t - t**2 / 260.0 - t**3 / 718.0

    if y < 2005:
        t = y - 2000.0
        return (63.86
                + 0.3345 * t
                - 0.060374 * t**2
                + 0.0017275 * t**3
                + 0.000651814 * t**4
                + 0.00002373599 * t**5)

    if y < 2050:
        # Anchored to 2026.0 = 69.3s (IERS Bulletin A prediction).
        # Slow growth ~0.04s/yr reflects current LOD trend.
        t = y - 2026.0
        return 69.3 + 0.04 * t + 0.001 * t**2

    if y < 2150:
        return -20 + 32 * ((y - 1820.0) / 100.0) ** 2 - 0.5628 * (2150.0 - y)

    u = (y - 1820.0) / 100.0
    return -20 + 32 * u * u


def delta_t_nasa_canon(year: float) -> float:
    """
    NASA eclipse-canon ΔT model in seconds.

    Governs the Espenak/Meeus piecewise polynomial expressions used by the
    Five Millennium Canon of Solar Eclipses. Differs from ``delta_t()`` in
    two ways: it uses the unmodified NASA polynomial set without the HPIERS
    table override, and it applies the lunar secular-acceleration correction
    ``−0.000012932 × (year − 1955)²`` required to reproduce the catalog's
    timing basis.

    Use this function when comparing against NASA eclipse contact times or
    the Five Millennium catalog; use ``delta_t()`` for general ephemeris work.

    Args:
        year: Decimal year (e.g. ``2000.5``).

    Returns:
        ΔT in seconds including the lunar secular-acceleration correction.

    Raises:
        Nothing — covers all real-valued years.

    Side effects:
        None.
    """
    y = float(year)
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

    correction = -0.000012932 * (y - 1955.0) ** 2
    return base + correction


def ut_to_tt(jd_ut: float, year: float | None = None) -> float:
    """
    Convert a Julian Day in UT to Terrestrial Time (TT) using ``delta_t()``.

    Args:
        jd_ut: Julian Day Number in Universal Time.
        year:  Decimal year hint; derived from ``jd_ut`` when ``None``.

    Returns:
        Julian Day Number in TT (= jd_ut + ΔT / 86400).

    Side effects:
        None.
    """
    if year is None:
        year = decimal_year_from_jd(jd_ut)
    dt_sec = delta_t(float(year))
    return jd_ut + dt_sec / 86400.0


def ut_to_tt_nasa_canon(jd_ut: float, year: float | None = None) -> float:
    """
    Convert a UT Julian Day to TT using the NASA eclipse-canon ``delta_t_nasa_canon()``.

    Args:
        jd_ut: Julian Day Number in Universal Time.
        year:  Decimal year hint; derived from ``jd_ut`` when ``None``.

    Returns:
        Julian Day Number in TT (= jd_ut + ΔT_nasa / 86400).

    Side effects:
        None.
    """
    if year is None:
        year = decimal_year_from_jd(jd_ut)
    dt_sec = delta_t_nasa_canon(float(year))
    return jd_ut + dt_sec / 86400.0


def tt_to_ut(jd_tt: float, year: float | None = None) -> float:
    """
    Convert a Julian Day in TT to Universal Time (UT) using ``delta_t()``.

    Args:
        jd_tt: Julian Day Number in Terrestrial Time.
        year:  Decimal year hint; derived from ``jd_tt`` when ``None``.

    Returns:
        Julian Day Number in UT (= jd_tt − ΔT / 86400).

    Side effects:
        None.
    """
    if year is None:
        year = decimal_year_from_jd(jd_tt)
    dt_sec = delta_t(float(year))
    return jd_tt - dt_sec / 86400.0


def tt_to_ut_nasa_canon(jd_tt: float, year: float | None = None) -> float:
    """
    Convert a TT Julian Day to UT using the NASA eclipse-canon Delta T model.

    Because ΔT depends on the resulting UT calendar year, a direct subtraction
    is not self-consistent. This function solves the implicit equation by
    fixed-point iteration (4 passes), which converges to sub-millisecond
    accuracy for all historical and modern dates.

    Args:
        jd_tt: Julian Day Number in Terrestrial Time.
        year:  Decimal year hint for the initial ΔT estimate; derived from
               ``jd_tt`` when ``None``.

    Returns:
        Julian Day Number in UT, self-consistent with ``delta_t_nasa_canon()``.

    Raises:
        Nothing — iteration always converges for finite inputs.

    Side effects:
        None.
    """
    if year is None:
        year = decimal_year_from_jd(jd_tt)
    jd_ut = jd_tt - delta_t_nasa_canon(float(year)) / 86400.0
    for _ in range(4):
        y = decimal_year_from_jd(jd_ut)
        jd_ut = jd_tt - delta_t_nasa_canon(y) / 86400.0
    return jd_ut


# ---------------------------------------------------------------------------
# Sidereal time
# ---------------------------------------------------------------------------

def greenwich_mean_sidereal_time(jd_ut: float) -> float:
    """
    Compute Greenwich Mean Sidereal Time (GMST) in degrees.

    Governs the IAU 2006 formula (Capitaine et al. 2003, A&A 412, 567–586;
    SOFA ``iauGmst06``). This is the Earth Rotation Angle (ERA) plus a
    5th-order polynomial correction that accounts for the offset between the
    mean equinox and the Celestial Intermediate Origin. Agreement with SOFA
    ``iauGmst06`` is better than 0.0001 arcsec for 1800–2200.

    This is *not* the older IAU 1982 polynomial (Aoki et al. 1982); the two
    differ by up to ~0.55 arcsec at dates two centuries from J2000.

    Args:
        jd_ut: Julian Day Number in UT1.

    Returns:
        GMST in degrees, normalised to [0, 360).

    Raises:
        Nothing — pure arithmetic.

    Side effects:
        None.
    """
    D = jd_ut - J2000           # days from J2000.0
    T = D / JULIAN_CENTURY       # Julian centuries

    # Earth Rotation Angle (ERA) — IAU 2000 definition of UT1
    era_turns = 0.7790572732640 + 1.00273781191135448 * D
    era_deg   = (era_turns % 1.0) * 360.0

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


def apparent_sidereal_time(jd_ut: float, nutation_longitude: float, obliquity: float) -> float:
    """
    Compute Greenwich Apparent Sidereal Time (GAST) in degrees.

    Governs the full IAU 2006 equation of the equinoxes:
        EE = Δψ · cos(ε) + CT
    where CT are the Capitaine et al. (2003) complementary terms (≤ 0.04″)
    computed by ``_gast_complementary_terms()``.

    Args:
        jd_ut:              Julian Day Number in UT1.
        nutation_longitude: Δψ (nutation in longitude) in degrees.
        obliquity:          True obliquity of the ecliptic in degrees.

    Returns:
        GAST in degrees, normalised to [0, 360).

    Raises:
        Nothing — pure arithmetic.

    Side effects:
        None.
    """
    gmst = greenwich_mean_sidereal_time(jd_ut)
    ee   = (nutation_longitude * math.cos(obliquity * math.pi / 180.0)
            + _gast_complementary_terms(jd_ut))
    return (gmst + ee) % 360.0


def local_sidereal_time(jd_ut: float, longitude: float,
                        nutation_longitude: float = 0.0,
                        obliquity: float = 23.4392911) -> float:
    """
    Compute Local Apparent Sidereal Time (LAST) in degrees.

    Adds the observer's geographic east longitude to GAST. When
    ``nutation_longitude`` is left at its default of 0.0 the result is Local
    Mean Sidereal Time (LMST); pass the true Δψ for full apparent time.

    Args:
        jd_ut:              Julian Day Number in UT1.
        longitude:          Observer's geographic east longitude in degrees.
        nutation_longitude: Δψ in degrees (default 0.0 → mean sidereal time).
        obliquity:          True obliquity in degrees (default J2000 value).

    Returns:
        LAST in degrees, normalised to [0, 360).

    Side effects:
        None.
    """
    gast = apparent_sidereal_time(jd_ut, nutation_longitude, obliquity)
    return (gast + longitude) % 360.0

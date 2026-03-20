"""
Sothic Cycle Engine — moira/sothic.py

Archetype: Engine
Purpose: Computes the heliacal rising of Sirius year by year, tracks its
         drift through the ancient Egyptian civil calendar, detects Sothic
         epochs (years of calendar realignment), and converts Julian Days
         to Egyptian civil calendar dates — all anchored to the historically
         confirmed 139 AD Sothic epoch of Censorinus.

Boundary declaration:
    Owns: Egyptian civil calendar arithmetic, Sothic drift computation,
          epoch detection, drift-rate regression, and the EgyptianDate,
          SothicEntry, and SothicEpoch result types.
    Delegates: heliacal rising computation to
               moira.fixed_stars.heliacal_rising; Julian Day arithmetic to
               moira.julian (julian_day, calendar_from_jd,
               calendar_datetime_from_jd, safe_datetime_from_jd).

Import-time side effects: None

External dependency assumptions:
    - moira.fixed_stars.heliacal_rising("Sirius", jd_start, lat, lon,
      arcus_visionis, search_days) returns a float JD or None.
    - moira.julian.julian_day(year, month, day, hour) returns a JD float.
    - moira.julian.safe_datetime_from_jd returns None for out-of-range JDs
      rather than raising.

Public surface / exports:
    EgyptianDate              — civil calendar date in the Egyptian year
    SothicEntry               — heliacal rising record for one year
    SothicEpoch               — a year of Sothic calendar realignment
    EGYPTIAN_MONTHS           — ordered list of 13 month names
    EGYPTIAN_SEASONS          — season → month-name mapping
    EPAGOMENAL_BIRTHS         — deities born on the 5 intercalary days
    HISTORICAL_SOTHIC_EPOCHS  — known/inferred epoch records
    egyptian_civil_date()     — convert JD to EgyptianDate
    days_from_1_thoth()       — fractional days elapsed since 1 Thoth
    sothic_rising()           — year-by-year heliacal rising table
    sothic_epochs()           — years of Sothic calendar realignment
    sothic_drift_rate()       — observed drift rate in days/year
    predicted_sothic_epoch_year() — forward/backward epoch prediction
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .julian import (
    julian_day,
    calendar_from_jd,
    calendar_datetime_from_jd,
    safe_datetime_from_jd,
)
from .fixed_stars import heliacal_rising as _heliacal_rising


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Censorinus epoch: heliacal rising = 1 Thoth, July 20, 139 AD.
# In Moira's JD/calendar conventions, midnight at the start of 139-07-20
# corresponds to JD 1772027.5.
_SOTHIC_EPOCH_139_JD: float = 1772027.5

# Length of the Egyptian civil year (exactly 365 days, no leap)
_EGYPTIAN_YEAR_DAYS: int = 365

# Sothic cycle: 1460 Julian years = 1461 Egyptian civil years = 533265 Julian days
# Identity: 1460 × 365.25 = 533265 = 1461 × 365  (exact)
_SOTHIC_CYCLE_YEARS: float = 1460.0
_SOTHIC_CYCLE_DAYS:  float = 533_265.0

# Egyptian month names in order (12 × 30 days + 5 epagomenal)
EGYPTIAN_MONTHS: list[str] = [
    "Thoth", "Phaophi", "Athyr", "Choiak",      # Akhet (Inundation)
    "Tybi", "Mechir", "Phamenoth", "Pharmuthi",  # Peret (Emergence)
    "Pachon", "Payni", "Epiphi", "Mesore",       # Shemu (Harvest)
    "Epagomenal",                                 # 5 intercalary days
]

EGYPTIAN_SEASONS: dict[str, list[str]] = {
    "Akhet":      ["Thoth", "Phaophi", "Athyr", "Choiak"],
    "Peret":      ["Tybi", "Mechir", "Phamenoth", "Pharmuthi"],
    "Shemu":      ["Pachon", "Payni", "Epiphi", "Mesore"],
    "Epagomenal": ["Epagomenal"],
}

# Births associated with the 5 epagomenal days (Plutarch, De Iside)
EPAGOMENAL_BIRTHS: list[str] = [
    "Osiris", "Arueris (Elder Horus)", "Set", "Isis", "Nephthys"
]


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EgyptianDate:
    """
    RITE: The Wandering Day — a position in the ancient Egyptian civil
          calendar that drifts freely through the seasons, untethered to
          any astronomical anchor except the Sothic epoch.

    THEOREM: Immutable record of a date in the 365-day Egyptian civil
             calendar, carrying month name, month number, day, season,
             day-of-year, and the birth deity for epagomenal days.

    RITE OF PURPOSE:
        EgyptianDate is the result vessel of egyptian_civil_date().  It
        translates a Julian Day into the symbolic language of the ancient
        Egyptian year — month, season, and the mythic births of the
        epagomenal days — so that callers can express astronomical events
        in the sacred calendar without performing the modular arithmetic
        themselves.  Without this vessel, callers would receive raw
        day-of-year integers with no semantic context.

    LAW OF OPERATION:
        Responsibilities:
            - Store month_name, month_number (1–13), day (1–30 or 1–5
              for Epagomenal), season, day_of_year (1–365), and
              epagomenal_birth (str or None).
            - Render a human-readable string (e.g. "14 Thoth (Akhet)"
              or "Epagomenal day 3 (Set)").
        Non-responsibilities:
            - Does not perform calendar conversion; that is
              egyptian_civil_date()'s role.
            - Does not validate that day is within the month's range.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - None beyond Python builtins.
        Structural invariants:
            - month_number is in [1, 13].
            - day is in [1, 30] for months 1–12, [1, 5] for month 13.
            - day_of_year is in [1, 365].
            - epagomenal_birth is non-None only when month_number == 13.

    Canon: Plutarch, De Iside et Osiride (epagomenal births)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.sothic.EgyptianDate",
        "risk": "low",
        "api": {"frozen": ["month_name", "month_number", "day", "season", "day_of_year", "epagomenal_birth"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    month_name:    str    # e.g. "Thoth", "Mesore", "Epagomenal"
    month_number:  int    # 1–13 (13 = Epagomenal)
    day:           int    # 1–30 (1–5 for Epagomenal)
    season:        str    # "Akhet", "Peret", "Shemu", or "Epagomenal"
    day_of_year:   int    # 1–365 in the Egyptian civil year
    epagomenal_birth: str | None  # birth deity if Epagomenal day, else None

    def __str__(self) -> str:
        if self.month_name == "Epagomenal":
            birth = f" ({self.epagomenal_birth})" if self.epagomenal_birth else ""
            return f"Epagomenal day {self.day}{birth}"
        return f"{self.day} {self.month_name} ({self.season})"


@dataclass(slots=True)
class SothicEntry:
    """
    RITE: The Annual Witness — the record of Sirius's heliacal rising for
          a single year, marking where the sacred star stood in the
          Egyptian civil calendar and how far it had drifted from the
          New Year anchor.

    THEOREM: Immutable record of the heliacal rising of Sirius for one
             astronomical year at a given observer location, carrying the
             JD of the rising, its Gregorian and Egyptian calendar dates,
             the drift from 1 Thoth, and the position within the Sothic
             cycle.

    RITE OF PURPOSE:
        SothicEntry is the per-year result vessel of sothic_rising().  It
        gives callers a complete picture of each year's heliacal rising —
        not just when it occurred, but where it fell in the sacred calendar
        and how far the cycle has progressed.  Without this vessel, the
        year-by-year table would be a list of unstructured tuples requiring
        callers to reconstruct all derived quantities.

    LAW OF OPERATION:
        Responsibilities:
            - Store year, jd_rising, date_utc (or None for out-of-range
              years), calendar_year/month/day, day_of_year, drift_days,
              cycle_position, and egyptian_date.
            - Render a compact repr showing year (BC/AD), JD, Gregorian
              date, Egyptian date, and drift.
        Non-responsibilities:
            - Does not compute heliacal rising times; that is
              sothic_rising()'s role.
            - Does not validate that drift_days is within [0, 365).
            - Does not perform any I/O or kernel access.
        Dependencies:
            - EgyptianDate for the egyptian_date field.
        Structural invariants:
            - jd_rising is a finite float.
            - drift_days is in [0, 365).
            - cycle_position is in [0, 1460).

    Canon: Censorinus, De Die Natali 21.10 (reference epoch)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.sothic.SothicEntry",
        "risk": "low",
        "api": {"frozen": ["year", "jd_rising", "date_utc", "calendar_year", "calendar_month", "calendar_day", "day_of_year", "drift_days", "cycle_position", "egyptian_date"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    year:              int      # astronomical year (0 = 1 BC, negative = BC)
    jd_rising:         float    # JD UT of heliacal rising
    date_utc:          datetime | None # Gregorian UTC date when representable
    calendar_year:     int
    calendar_month:    int
    calendar_day:      int
    day_of_year:       int      # Gregorian day-of-year (1–366) of the rising

    # How far the rising has drifted from the reference (1 Thoth at Memphis)
    # Positive = rising is later in the civil calendar than the anchor
    # Negative = rising is earlier
    drift_days:        float

    # Position in the Sothic cycle (0–~1460), measured in days from the
    # most recent Sothic epoch at the reference location
    cycle_position:    float

    # Egyptian civil calendar date at the reference epoch's calendar
    egyptian_date:     EgyptianDate

    def __repr__(self) -> str:
        year_str = f"{abs(self.year)} BC" if self.year < 0 else f"{self.year} AD"
        date_str = (
            self.date_utc.strftime('%b %d')
            if self.date_utc is not None
            else f"{self.calendar_year:04d}-{self.calendar_month:02d}-{self.calendar_day:02d}"
        )
        return (
            f"SothicEntry({year_str}: JD {self.jd_rising:.1f}, "
            f"{date_str}, "
            f"Egyptian {self.egyptian_date}, "
            f"drift {self.drift_days:+.1f} d)"
        )


@dataclass(slots=True)
class SothicEpoch:
    """
    RITE: The Great Return — the rare year when the wandering star and the
          wandering calendar meet again at the threshold of the New Year,
          closing one Sothic cycle and opening the next.

    THEOREM: Immutable record of a Sothic epoch year — a year in which the
             heliacal rising of Sirius falls within the configured tolerance
             of 1 Thoth in the Egyptian civil calendar — carrying the year,
             JD of the rising, Gregorian date, and residual drift.

    RITE OF PURPOSE:
        SothicEpoch is the result vessel of sothic_epochs().  It marks the
        historically and astronomically significant moments when the Egyptian
        civil calendar and the heliacal rising of Sirius realign, completing
        the ~1460-year Sothic cycle.  Without this vessel, callers would need
        to filter SothicEntry records themselves and recompute the residual
        drift from the alignment threshold.

    LAW OF OPERATION:
        Responsibilities:
            - Store year, jd_rising, date_utc (or None), calendar_year/
              month/day, and drift_days (residual from exact alignment,
              normalised to [-182.5, 182.5]).
            - Render a compact repr showing year (BC/AD), JD, Gregorian
              date, and residual drift.
        Non-responsibilities:
            - Does not detect epochs; that is sothic_epochs()'s role.
            - Does not validate that drift_days is within tolerance.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - None beyond Python builtins.
        Structural invariants:
            - jd_rising is a finite float.
            - drift_days is in [-182.5, 182.5] (normalised signed drift).

    Canon: Censorinus, De Die Natali 21.10 (confirmed 139 AD epoch)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.sothic.SothicEpoch",
        "risk": "low",
        "api": {"frozen": ["year", "jd_rising", "date_utc", "calendar_year", "calendar_month", "calendar_day", "drift_days"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    year:          int      # astronomical year
    jd_rising:     float    # JD UT of the heliacal rising
    date_utc:      datetime | None
    calendar_year: int
    calendar_month:int
    calendar_day:  int
    drift_days:    float    # residual drift from exact alignment (days)

    def __repr__(self) -> str:
        year_str = f"{abs(self.year)} BC" if self.year < 0 else f"{self.year} AD"
        date_str = (
            self.date_utc.strftime('%b %d')
            if self.date_utc is not None
            else f"{self.calendar_year:04d}-{self.calendar_month:02d}-{self.calendar_day:02d}"
        )
        return (f"SothicEpoch({year_str}: JD {self.jd_rising:.1f}, "
                f"{date_str}, "
                f"residual {self.drift_days:+.2f} d)")


# ---------------------------------------------------------------------------
# Egyptian civil calendar
# ---------------------------------------------------------------------------

def egyptian_civil_date(
    jd: float,
    epoch_jd: float = _SOTHIC_EPOCH_139_JD,
) -> EgyptianDate:
    """
    Convert a Julian Day to an Egyptian civil calendar date.

    The Egyptian civil calendar is a wandering calendar of exactly 365 days
    per year.  It is anchored to the given *epoch_jd* as 1 Thoth of year 0.

    Parameters
    ----------
    jd       : Julian Day to convert
    epoch_jd : JD of 1 Thoth in the reference year (default: 139 AD Sothic epoch)

    Returns
    -------
    EgyptianDate giving the month, day, and season.

    Notes
    -----
    Because the Egyptian year does not drift with the seasons (no leap year),
    the returned date tells you *where in the Egyptian civil calendar* a given
    astronomical event falls, relative to the anchor epoch.
    """
    # Days elapsed since the epoch (mod 365)
    elapsed = jd - epoch_jd
    day_of_year = int(elapsed % _EGYPTIAN_YEAR_DAYS)
    if day_of_year < 0:
        day_of_year += _EGYPTIAN_YEAR_DAYS

    # 1-indexed
    doy = day_of_year + 1    # 1–365

    if doy <= 360:
        month_idx = (doy - 1) // 30      # 0–11
        day       = (doy - 1) % 30 + 1   # 1–30
        month_name = EGYPTIAN_MONTHS[month_idx]
        month_number = month_idx + 1
        # Season
        if month_idx < 4:
            season = "Akhet"
        elif month_idx < 8:
            season = "Peret"
        else:
            season = "Shemu"
        return EgyptianDate(
            month_name=month_name,
            month_number=month_number,
            day=day,
            season=season,
            day_of_year=doy,
            epagomenal_birth=None,
        )
    else:
        # Epagomenal days: doy 361–365
        epag_day = doy - 360    # 1–5
        birth = EPAGOMENAL_BIRTHS[epag_day - 1] if epag_day <= 5 else None
        return EgyptianDate(
            month_name="Epagomenal",
            month_number=13,
            day=epag_day,
            season="Epagomenal",
            day_of_year=doy,
            epagomenal_birth=birth,
        )


def days_from_1_thoth(jd: float, epoch_jd: float = _SOTHIC_EPOCH_139_JD) -> float:
    """
    Return how many civil calendar days have elapsed since 1 Thoth of the
    current Egyptian year relative to the epoch.

    Equivalent to (day_of_year - 1) with a fractional day component.
    """
    elapsed = jd - epoch_jd
    return elapsed % _EGYPTIAN_YEAR_DAYS


# ---------------------------------------------------------------------------
# Core: Sothic rising computation
# ---------------------------------------------------------------------------

def sothic_rising(
    latitude: float,
    longitude: float,
    year_start: int,
    year_end: int,
    epoch_jd: float = _SOTHIC_EPOCH_139_JD,
    arcus_visionis: float = 10.0,
) -> list[SothicEntry]:
    """
    Compute the heliacal rising of Sirius for each year in the given range.

    This is the central function of the Sothic cycle — a year-by-year record
    of when Sirius first appeared on the eastern horizon before sunrise,
    and where that moment fell in the Egyptian civil calendar.

    Parameters
    ----------
    latitude        : observer geographic latitude (degrees, signed)
    longitude       : observer geographic east longitude (degrees)
    year_start      : first astronomical year to compute (negative = BC)
    year_end        : last astronomical year to compute (inclusive)
    epoch_jd        : reference Sothic epoch JD (default: 139 AD at Alexandria)
    arcus_visionis  : solar depression required for Sirius visibility (degrees).
                      Default 10° is appropriate for Sirius (magnitude −1.46)
                      in a clear ancient Mediterranean sky.  Increase to 11–12°
                      for modern polluted skies.

    Returns
    -------
    list[SothicEntry], one per year where a heliacal rising was found.
    Years where Sirius is circumpolar or never rises are omitted.

    Notes
    -----
    At latitudes above ~73°N, Sirius never rises; this function returns an
    empty list for such latitudes.

    The search for each year begins on January 1 (proleptic Gregorian) and
    looks forward up to 400 days.  The heliacal rising of Sirius occurs in
    boreal summer at most latitudes; if a year is skipped, it typically means
    the rising occurred very close to year-end and was captured in the
    adjacent year.
    """
    results: list[SothicEntry] = []

    for year in range(year_start, year_end + 1):
        # Start search from January 1 of this year
        jd_start = julian_day(year, 1, 1, 0.0)

        try:
            jd_rise = _heliacal_rising(
                "Sirius", jd_start, latitude, longitude,
                arcus_visionis=arcus_visionis,
                search_days=400,
            )
        except Exception:
            continue   # catalog not loaded or other error

        if jd_rise is None:
            continue   # Sirius does not rise heliacally at this latitude/year

        # Calendar date
        cal_year, cal_month, cal_day, _ = calendar_from_jd(jd_rise)
        dt = safe_datetime_from_jd(jd_rise)
        doy = _day_of_year(dt) if dt is not None else int(jd_rise - julian_day(cal_year, 1, 1, 0.0)) + 1

        # Drift: how many Egyptian civil calendar days from 1 Thoth?
        # At the reference epoch, the rising fell on day 1 of the Egyptian year.
        # Each ~4 years the rising drifts one day further through the calendar.
        drift = days_from_1_thoth(jd_rise, epoch_jd)

        # Year within the 1460-year Sothic cycle (0.0 → 1460.0)
        cycle_pos = ((jd_rise - epoch_jd) / 365.25) % _SOTHIC_CYCLE_YEARS

        # Egyptian date at the reference epoch's calendar
        egypt_date = egyptian_civil_date(jd_rise, epoch_jd)

        results.append(SothicEntry(
            year=year,
            jd_rising=jd_rise,
            date_utc=dt,
            calendar_year=cal_year,
            calendar_month=cal_month,
            calendar_day=cal_day,
            day_of_year=doy,
            drift_days=drift,
            cycle_position=cycle_pos,
            egyptian_date=egypt_date,
        ))

    return results


# ---------------------------------------------------------------------------
# Sothic epoch finder
# ---------------------------------------------------------------------------

def sothic_epochs(
    latitude: float,
    longitude: float,
    year_start: int,
    year_end: int,
    epoch_jd: float = _SOTHIC_EPOCH_139_JD,
    tolerance_days: float = 1.0,
    arcus_visionis: float = 10.0,
) -> list[SothicEpoch]:
    """
    Find years within the range where the heliacal rising of Sirius returns
    to within *tolerance_days* of the original civil New Year anchor.

    These are the "Sothic epochs" — the sacred moments when the sacred star
    and the sacred calendar realign.

    Parameters
    ----------
    latitude / longitude : observer location
    year_start / year_end : search range (astronomical years)
    epoch_jd       : reference anchor JD (default: 139 AD)
    tolerance_days : how close to 1 Thoth counts as an epoch (default ±1 day)
    arcus_visionis : solar depression required (default 10° for Sirius)

    Returns
    -------
    list[SothicEpoch], one per epoch found in the range.

    Notes
    -----
    The Sothic cycle length (~1460 Julian years or ~1507 tropical years) means
    a range of 2000 years will typically contain 1–2 epochs.  Use a range of
    10,000+ years for the full historical picture.
    """
    entries = sothic_rising(latitude, longitude, year_start, year_end,
                             epoch_jd=epoch_jd, arcus_visionis=arcus_visionis)
    epochs: list[SothicEpoch] = []

    for e in entries:
        # Drift relative to 1 Thoth: we want drift close to 0 (or 365)
        drift = e.drift_days
        # Normalise to [-182.5, 182.5] so we can measure closeness to both
        # 0 and 365 (which are the same point in the cycle)
        if drift > _EGYPTIAN_YEAR_DAYS / 2:
            drift -= _EGYPTIAN_YEAR_DAYS

        if abs(drift) <= tolerance_days:
            epochs.append(SothicEpoch(
                year=e.year,
                jd_rising=e.jd_rising,
                date_utc=e.date_utc,
                calendar_year=e.calendar_year,
                calendar_month=e.calendar_month,
                calendar_day=e.calendar_day,
                drift_days=drift,
            ))

    return epochs


# ---------------------------------------------------------------------------
# Drift analysis
# ---------------------------------------------------------------------------

def sothic_drift_rate(entries: list[SothicEntry]) -> float:
    """
    Estimate the observed drift rate of the heliacal rising through the
    Egyptian civil calendar in days per year, computed from a list of
    SothicEntry records.

    For the standard Egyptian civil calendar this should be ~0.242 days/year
    (approximately 1 day per 4.13 years).

    Parameters
    ----------
    entries : list from sothic_rising() — must span at least 5 years

    Returns
    -------
    Drift rate in days per year (positive = rising moves later in calendar)
    """
    if len(entries) < 5:
        raise ValueError("Need at least 5 entries to estimate drift rate")

    # Linear regression on drift_days vs year
    n = len(entries)
    xs = [e.year for e in entries]
    ys = [e.drift_days for e in entries]

    # Unwrap: remove the 365-day jumps when drift wraps around
    for i in range(1, n):
        diff = ys[i] - ys[i - 1]
        if diff > 182.5:
            for j in range(i, n):
                ys[j] -= _EGYPTIAN_YEAR_DAYS
        elif diff < -182.5:
            for j in range(i, n):
                ys[j] += _EGYPTIAN_YEAR_DAYS

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if abs(den) < 1e-10:
        return 0.0
    return num / den


def predicted_sothic_epoch_year(
    known_epoch_year: int,
    n_cycles: int,
    cycle_length_years: float = 1460.0,
) -> float:
    """
    Predict the year of a Sothic epoch *n_cycles* after a known epoch.

    Parameters
    ----------
    known_epoch_year  : astronomical year of a known Sothic epoch
    n_cycles          : number of cycles forward (positive) or backward (negative)
    cycle_length_years: assumed Sothic cycle length (default 1460.0 Julian years)

    Returns
    -------
    Predicted astronomical year (float)
    """
    return known_epoch_year + n_cycles * cycle_length_years


# ---------------------------------------------------------------------------
# Convenience: historical epochs
# ---------------------------------------------------------------------------

# Known / inferred Sothic epochs at Memphis (lat 29.8°N, lon 31.3°E)
HISTORICAL_SOTHIC_EPOCHS: list[dict] = [
    {"year": -2780, "note": "First Sothic Period — beginning of the Egyptian calendar (inferred)"},
    {"year": -1320, "note": "Second Sothic Period — Ebers Papyrus (9th year of Amenhotep I, inferred)"},
    {"year":   139, "note": "Third Sothic Period — Censorinus (confirmed, 139 AD)"},
    {"year":  1599, "note": "Fourth Sothic Period — computed from the 139 AD epoch"},
]


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------

def _day_of_year(dt: datetime) -> int:
    """Return the day-of-year (1–366) for a datetime."""
    return dt.timetuple().tm_yday


def _safe_datetime_from_jd(jd: float) -> datetime | None:
    """Backward-compatible local alias; use moira.julian.safe_datetime_from_jd."""
    return safe_datetime_from_jd(jd)

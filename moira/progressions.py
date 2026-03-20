"""
Moira — progressions.py
The Progression Engine: governs secondary progressions, solar arc directions,
tertiary progressions, converse progressions, and minor progressions.

Boundary: owns all symbolic time-advancement techniques (one-day-one-year and
variants). Delegates body position computation to planets. Delegates Julian Day
arithmetic to julian. Does NOT own ephemeris state or natal chart construction.

Public surface:
    ProgressedPosition, ProgressedChart,
    secondary_progression, solar_arc, tertiary_progression,
    converse_secondary_progression, converse_solar_arc, minor_progression

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - SpkReader must be initialised before any public function is called.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .constants import Body, sign_of
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, jd_from_datetime, delta_t, ut_to_tt
from .planets import planet_at, all_planets_at
from .spk_reader import get_reader, SpkReader


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ProgressedPosition:
    """
    RITE: The Progressed Position Vessel

    THEOREM: Governs the storage of a single body's position in a progressed or
    directed chart.

    RITE OF PURPOSE:
        ProgressedPosition is the authoritative data vessel for a single body's
        ecliptic longitude in any progressed or directed chart produced by the
        Progression Engine. It captures the body name, longitude, speed, retrograde
        flag, and derived sign fields. Without it, callers would receive unstructured
        tuples with no field-level guarantees. It exists to give every higher-level
        consumer a single, named, mutable record of each progressed body position.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single progressed body position as named, typed fields
            - Derive sign, sign_symbol, and sign_degree via __post_init__
            - Serve as a value inside ProgressedChart.positions
        Non-responsibilities:
            - Computing progressed positions (delegates to secondary_progression etc.)
            - Resolving body positions from ephemeris (delegates to planets)
        Dependencies:
            - sign, sign_symbol, sign_degree derived from sign_of(longitude) at init
        Structural invariants:
            - longitude is in [0, 360)
            - sign is a valid zodiac sign name
        Behavioral invariants:
            - sign fields are always consistent with longitude

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.progressions.ProgressedPosition",
      "risk": "high",
      "api": {
        "frozen": ["name", "longitude", "speed", "retrograde"],
        "internal": ["sign", "sign_symbol", "sign_degree"]
      },
      "state": {"mutable": true, "owners": ["secondary_progression", "solar_arc", "tertiary_progression", "converse_secondary_progression", "converse_solar_arc", "minor_progression"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:        str
    longitude:   float
    speed:       float  = 0.0
    retrograde:  bool   = False
    sign:        str    = field(init=False)
    sign_symbol: str    = field(init=False)
    sign_degree: float  = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    def __repr__(self) -> str:
        r = "R" if self.retrograde else " "
        return (f"{self.name:<10}{r} {self.longitude:>9.4f}  "
                f"{self.sign} {self.sign_degree:.2f}")


@dataclass(slots=True)
class ProgressedChart:
    """
    RITE: The Progressed Chart Vessel

    THEOREM: Governs the storage of a complete progressed or directed chart for a
    given real-world target date.

    RITE OF PURPOSE:
        ProgressedChart is the authoritative data vessel for a complete progressed
        or directed chart produced by the Progression Engine. It captures the chart
        type label, natal and progressed Julian Days, the real-world target date,
        the solar arc applied, and the full dictionary of progressed body positions.
        Without it, callers would receive unstructured collections with no
        field-level guarantees. It exists to give every higher-level consumer a
        single, named, mutable record of each complete progressed chart.

    LAW OF OPERATION:
        Responsibilities:
            - Store a complete progressed chart as named, typed fields
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as the return type of all progression functions
        Non-responsibilities:
            - Computing progressed positions (delegates to progression functions)
            - Resolving body positions from ephemeris (delegates to planets)
        Dependencies:
            - positions dict populated by the owning progression function
            - datetime_utc delegates to datetime_from_jd()
            - calendar_utc delegates to calendar_datetime_from_jd()
        Structural invariants:
            - chart_type is one of the recognised progression type labels
            - solar_arc_deg is 0.0 for non-solar-arc techniques
        Behavioral invariants:
            - All consumers treat ProgressedChart fields as read-only after construction

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.progressions.ProgressedChart",
      "risk": "high",
      "api": {
        "frozen": ["chart_type", "natal_jd_ut", "progressed_jd_ut", "target_date", "solar_arc_deg", "positions"],
        "internal": ["datetime_utc", "calendar_utc"]
      },
      "state": {"mutable": true, "owners": ["secondary_progression", "solar_arc", "tertiary_progression", "converse_secondary_progression", "converse_solar_arc", "minor_progression"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    chart_type:       str          # "Secondary Progression" | "Solar Arc Direction"
    natal_jd_ut:      float
    progressed_jd_ut: float        # JD used to cast the chart (SP) or natal JD (SA)
    target_date:      datetime     # The real-world date for which we progressed
    solar_arc_deg:    float        # Arc applied (0 for SP, actual arc for SA)
    positions:        dict[str, ProgressedPosition]

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.progressed_jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.progressed_jd_ut)


# ---------------------------------------------------------------------------
# Secondary Progressions
# ---------------------------------------------------------------------------

def secondary_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
) -> ProgressedChart:
    """
    Calculate Secondary Progressed chart.

    One solar year of life = one day after birth.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate progressions
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance

    Returns
    -------
    ProgressedChart with chart_type="Secondary Progression"
    """
    if reader is None:
        reader = get_reader()

    # Age in tropical years at target_date
    target_jd = jd_from_datetime(target_date)
    age_years  = (target_jd - natal_jd_ut) / 365.24219

    # Progressed JD = natal + age as days
    prog_jd = natal_jd_ut + age_years

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    raw = all_planets_at(prog_jd, bodies=bodies, reader=reader)
    positions = {
        name: ProgressedPosition(
            name=name,
            longitude=p.longitude,
            speed=p.speed,
            retrograde=p.retrograde,
        )
        for name, p in raw.items()
    }

    return ProgressedChart(
        chart_type="Secondary Progression",
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=prog_jd,
        target_date=target_date,
        solar_arc_deg=0.0,
        positions=positions,
    )


# ---------------------------------------------------------------------------
# Solar Arc Directions
# ---------------------------------------------------------------------------

def solar_arc(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
) -> ProgressedChart:
    """
    Calculate Solar Arc Direction chart.

    Arc = Progressed Sun − Natal Sun.
    Every natal point is advanced by that arc.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate directions
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance

    Returns
    -------
    ProgressedChart with chart_type="Solar Arc Direction"
    """
    if reader is None:
        reader = get_reader()

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    # Natal Sun
    natal_sun  = planet_at(Body.SUN, natal_jd_ut, reader=reader).longitude

    # Progressed Sun (secondary progression date)
    target_jd  = jd_from_datetime(target_date)
    age_years  = (target_jd - natal_jd_ut) / 365.24219
    prog_jd    = natal_jd_ut + age_years
    prog_sun   = planet_at(Body.SUN, prog_jd, reader=reader).longitude

    # Solar arc (forward direction, 0–360)
    arc = (prog_sun - natal_sun) % 360.0

    # Apply arc to all natal positions
    natal_raw  = all_planets_at(natal_jd_ut, bodies=bodies, reader=reader)
    positions  = {
        name: ProgressedPosition(
            name=name,
            longitude=(p.longitude + arc) % 360.0,
            speed=p.speed,
            retrograde=p.retrograde,
        )
        for name, p in natal_raw.items()
    }

    return ProgressedChart(
        chart_type="Solar Arc Direction",
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=prog_jd,
        target_date=target_date,
        solar_arc_deg=arc,
        positions=positions,
    )


# ---------------------------------------------------------------------------
# Tertiary Progressions (1 day = 1 lunar month)
# ---------------------------------------------------------------------------

def tertiary_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
) -> ProgressedChart:
    """
    Tertiary progressions: one synodic month (~29.53 days) = one year of life.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate progressions
    """
    if reader is None:
        reader = get_reader()

    _SYNODIC_MONTH = 29.53058868  # days

    target_jd = jd_from_datetime(target_date)
    age_years  = (target_jd - natal_jd_ut) / 365.24219
    # 1 year = 1 month → 1 day = 1/12 month
    prog_jd    = natal_jd_ut + age_years * (_SYNODIC_MONTH / 365.24219)

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    raw = all_planets_at(prog_jd, bodies=bodies, reader=reader)
    positions = {
        name: ProgressedPosition(
            name=name,
            longitude=p.longitude,
            speed=p.speed,
            retrograde=p.retrograde,
        )
        for name, p in raw.items()
    }

    return ProgressedChart(
        chart_type="Tertiary Progression",
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=prog_jd,
        target_date=target_date,
        solar_arc_deg=0.0,
        positions=positions,
    )


# ---------------------------------------------------------------------------
# Converse Secondary Progression
# ---------------------------------------------------------------------------

def converse_secondary_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
) -> ProgressedChart:
    """
    Converse secondary progression: go BACKWARD from birth.

    Instead of advancing the chart forward (natal_JD + age_days),
    the converse chart goes backward: natal_JD − age_years.

    Used to find when progressed planets conjunct natal positions from
    the other direction, and in rectification work.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance
    """
    if reader is None:
        reader = get_reader()

    target_jd = jd_from_datetime(target_date)
    age_years  = (target_jd - natal_jd_ut) / 365.24219

    # Converse: go BACKWARD from natal by age_years (as days)
    prog_jd = natal_jd_ut - age_years

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    raw = all_planets_at(prog_jd, bodies=bodies, reader=reader)
    positions = {
        name: ProgressedPosition(
            name=name,
            longitude=p.longitude,
            speed=p.speed,
            retrograde=p.retrograde,
        )
        for name, p in raw.items()
    }

    return ProgressedChart(
        chart_type="Converse Secondary Progression",
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=prog_jd,
        target_date=target_date,
        solar_arc_deg=0.0,
        positions=positions,
    )


# ---------------------------------------------------------------------------
# Converse Solar Arc
# ---------------------------------------------------------------------------

def converse_solar_arc(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
) -> ProgressedChart:
    """
    Converse solar arc: apply the solar arc in REVERSE (subtract from natal).

    Arc = progressed Sun − natal Sun (same as forward solar arc).
    Converse: each natal point is SUBTRACTED by that arc.

    Used alongside standard solar arc to find additional direction hits.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance
    """
    if reader is None:
        reader = get_reader()

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    # Natal Sun
    natal_sun = planet_at(Body.SUN, natal_jd_ut, reader=reader).longitude

    # Progressed Sun (secondary progression date)
    target_jd  = jd_from_datetime(target_date)
    age_years  = (target_jd - natal_jd_ut) / 365.24219
    prog_jd    = natal_jd_ut + age_years
    prog_sun   = planet_at(Body.SUN, prog_jd, reader=reader).longitude

    # Solar arc (same magnitude as forward, but applied in reverse)
    arc = (prog_sun - natal_sun) % 360.0

    # Apply arc in reverse to all natal positions
    natal_raw = all_planets_at(natal_jd_ut, bodies=bodies, reader=reader)
    positions = {
        name: ProgressedPosition(
            name=name,
            longitude=(p.longitude - arc) % 360.0,
            speed=p.speed,
            retrograde=p.retrograde,
        )
        for name, p in natal_raw.items()
    }

    return ProgressedChart(
        chart_type="Converse Solar Arc",
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=prog_jd,
        target_date=target_date,
        solar_arc_deg=-arc,          # negative indicates converse direction
        positions=positions,
    )


# ---------------------------------------------------------------------------
# Minor Progressions
# ---------------------------------------------------------------------------

def minor_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
) -> ProgressedChart:
    """
    Minor progressions: one lunar month = one year of life.

    The progressed JD advances by (age_years × synodic_month / year).
    Slower than secondary progressions (29.53 days instead of 365.25),
    giving a different rhythm to the progressed planets.

    Progressed JD = natal_JD + (age_years × 29.53058868 / 365.24219)

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate progressions
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance
    """
    if reader is None:
        reader = get_reader()

    _SYNODIC_MONTH = 29.53058868   # days

    target_jd = jd_from_datetime(target_date)
    age_years  = (target_jd - natal_jd_ut) / 365.24219
    # 1 year of life = 1 synodic month of ephemeris time
    prog_jd    = natal_jd_ut + age_years * (_SYNODIC_MONTH / 365.24219)

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    raw = all_planets_at(prog_jd, bodies=bodies, reader=reader)
    positions = {
        name: ProgressedPosition(
            name=name,
            longitude=p.longitude,
            speed=p.speed,
            retrograde=p.retrograde,
        )
        for name, p in raw.items()
    }

    return ProgressedChart(
        chart_type="Minor Progression",
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=prog_jd,
        target_date=target_date,
        solar_arc_deg=0.0,
        positions=positions,
    )

"""
moira/cycles.py — Planetary Cycles Engine

Governs cyclical timing frameworks grounded in astronomical periodicity:

    Return series        when a planet revisits its natal longitude
    Synodic cycles       the phase relationship between two bodies
    Great conjunctions   the Jupiter–Saturn 20/200/800-year doctrine
    Planetary ages       Ptolemy's seven-age model (Tetrabiblos I.10)
    Firdar               the Persian time-lord system (Abu Ma'shar, Bonatti)
    Planetary days       the Chaldean weekday rulers
    Planetary hours      unequal temporal hours with Chaldean rulers

Authority
---------
    Return series      — astronomical (ephemeris-derived via transits.py)
    Synodic cycles     — astronomical (ephemeris-derived via phenomena.py / phase.py)
    Great conjunctions — Abu Ma'shar (*On the Great Conjunctions*), Kepler,
                         observational astronomy
    Planetary ages     — Ptolemy (*Tetrabiblos* I.10)
    Firdar             — Abu Ma'shar (*On the Revolutions of the Years
                         of Nativities*), Guido Bonatti (*Liber Astronomiae*)
    Planetary days     — universal Chaldean tradition
    Planetary hours    — Chaldean temporal hours, Hellenistic and medieval
                         universal practice
"""

from dataclasses import dataclass, field
from enum import Enum

from .constants import Body, sign_of
from .spk_reader import SpkReader, get_reader


# ===========================================================================
# PUBLIC API
# ===========================================================================

__all__ = [
    # Enums
    "SynodicPhase",
    "GreatMutationElement",
    "PlanetaryAgeName",
    # Return series
    "ReturnEvent",
    "ReturnSeries",
    "return_series",
    "half_return_series",
    "lifetime_returns",
    # Synodic cycles
    "SynodicCyclePosition",
    "synodic_cycle_position",
    # Great conjunctions
    "GreatConjunction",
    "GreatConjunctionSeries",
    "MutationPeriod",
    "great_conjunctions",
    "mutation_period_at",
    # Planetary ages
    "PlanetaryAgePeriod",
    "PlanetaryAgeProfile",
    "planetary_age_at",
    "planetary_age_profile",
    # Firdar
    "FirdarPeriod",
    "FirdarSubPeriod",
    "FirdarSeries",
    "firdar_series",
    "firdar_at",
    # Planetary days and hours
    "PlanetaryDayInfo",
    "PlanetaryHour",
    "PlanetaryHoursProfile",
    "planetary_day_ruler",
    "planetary_hours_for_day",
]


# ===========================================================================
# CONSTANTS
# ===========================================================================

# The Chaldean order: descending geocentric orbital period.
# This sequence governs planetary hours and the weekday ruler derivation.
CHALDEAN_ORDER: tuple[str, ...] = (
    Body.SATURN, Body.JUPITER, Body.MARS, Body.SUN,
    Body.VENUS, Body.MERCURY, Body.MOON,
)

_CHALDEAN_INDEX: dict[str, int] = {p: i for i, p in enumerate(CHALDEAN_ORDER)}

# Julian year in days — the firdar and age computation standard.
_JULIAN_YEAR: float = 365.25


# ===========================================================================
# SECTION 1 — ENUMS
# ===========================================================================

class SynodicPhase(str, Enum):
    """
    Eight-fold synodic phase classification.

    Based on the phase angle from body1 to body2 (0–360°):
        0°   = conjunction
        90°  = first quarter (waxing square)
        180° = opposition
        270° = last quarter (waning square)

    The eight phases are the four cardinals ± 45° bands, bisected
    into crescent/gibbous halves — a convention traceable to
    Rudhyar and adopted widely in modern practice.
    """

    NEW               = "new"                # 0° ± 22.5°
    WAXING_CRESCENT   = "waxing_crescent"    # 22.5° – 67.5°
    FIRST_QUARTER     = "first_quarter"      # 67.5° – 112.5°
    WAXING_GIBBOUS    = "waxing_gibbous"     # 112.5° – 157.5°
    FULL              = "full"               # 157.5° – 202.5°
    WANING_GIBBOUS    = "waning_gibbous"     # 202.5° – 247.5°
    LAST_QUARTER      = "last_quarter"       # 247.5° – 292.5°
    WANING_CRESCENT   = "waning_crescent"    # 292.5° – 337.5°
    # Closes back to NEW at 337.5°

    @staticmethod
    def from_angle(angle_deg: float) -> "SynodicPhase":
        """Classify a synodic phase angle (0–360°) into one of eight phases."""
        a = angle_deg % 360.0
        if a < 22.5 or a >= 337.5:
            return SynodicPhase.NEW
        if a < 67.5:
            return SynodicPhase.WAXING_CRESCENT
        if a < 112.5:
            return SynodicPhase.FIRST_QUARTER
        if a < 157.5:
            return SynodicPhase.WAXING_GIBBOUS
        if a < 202.5:
            return SynodicPhase.FULL
        if a < 247.5:
            return SynodicPhase.WANING_GIBBOUS
        if a < 292.5:
            return SynodicPhase.LAST_QUARTER
        return SynodicPhase.WANING_CRESCENT


class GreatMutationElement(str, Enum):
    """The four elemental trigons of the great conjunction cycle."""

    FIRE  = "fire"    # Aries, Leo, Sagittarius
    EARTH = "earth"   # Taurus, Virgo, Capricorn
    AIR   = "air"     # Gemini, Libra, Aquarius
    WATER = "water"   # Cancer, Scorpio, Pisces


class PlanetaryAgeName(str, Enum):
    """
    The seven planetary ages of human life (Ptolemy, Tetrabiblos I.10).

    Each planet governs a stage of development corresponding to its
    astronomical nature.  The Moon governs infancy (rapid change), Mercury
    governs childhood (learning), and so on through Saturn's governance
    of old age (contraction and cold).
    """

    MOON    = "Moon"
    MERCURY = "Mercury"
    VENUS   = "Venus"
    SUN     = "Sun"
    MARS    = "Mars"
    JUPITER = "Jupiter"
    SATURN  = "Saturn"


# ===========================================================================
# SECTION 2 — RESULT VESSELS
# ===========================================================================

# ---- Return Series ----

@dataclass(frozen=True, slots=True)
class ReturnEvent:
    """
    One planetary return occurrence.

    Fields
    ------
    body : str
        The returned body.
    return_number : int
        Ordinal return number (1 = first return, 2 = second, ...).
    jd_ut : float
        Julian Day (UT) of exact return.
    longitude : float
        The natal longitude returned to (degrees).
    is_half : bool
        True if this is a half-return (opposition to natal longitude).
    """

    body:          str
    return_number: int
    jd_ut:         float
    longitude:     float
    is_half:       bool = False


@dataclass(frozen=True, slots=True)
class ReturnSeries:
    """
    A complete series of returns for one body.

    Fields
    ------
    body : str
        The body whose returns are tracked.
    natal_longitude : float
        The natal longitude (degrees).
    jd_start : float
        Start of the search window.
    jd_end : float
        End of the search window.
    returns : tuple[ReturnEvent, ...]
        All returns found, ordered chronologically.
    count : int
        Number of returns found.
    """

    body:             str
    natal_longitude:  float
    jd_start:         float
    jd_end:           float
    returns:          tuple[ReturnEvent, ...]
    count:            int


# ---- Synodic Cycle ----

@dataclass(frozen=True, slots=True)
class SynodicCyclePosition:
    """
    Snapshot of where two bodies stand in their synodic cycle.

    Fields
    ------
    body1, body2 : str
        The two bodies.
    jd_ut : float
        Moment of evaluation.
    phase_angle : float
        Phase angle from body1 to body2, 0–360° (0 = conjunction).
    phase : SynodicPhase
        Eight-fold phase classification.
    is_waxing : bool
        True if the phase angle is increasing (0–180°).
    lon1, lon2 : float
        Ecliptic longitudes at evaluation moment.
    """

    body1:       str
    body2:       str
    jd_ut:       float
    phase_angle: float
    phase:       SynodicPhase
    is_waxing:   bool
    lon1:        float
    lon2:        float


# ---- Great Conjunctions ----

@dataclass(frozen=True, slots=True)
class GreatConjunction:
    """
    One Jupiter–Saturn conjunction with elemental classification.

    Fields
    ------
    jd_ut : float
        Julian Day (UT) of conjunction.
    longitude : float
        Ecliptic longitude of the conjunction (degrees).
    sign : str
        Zodiac sign name.
    sign_symbol : str
        Zodiac sign symbol.
    degree_in_sign : float
        Degree within the sign.
    element : GreatMutationElement
        Elemental trigon of the conjunction sign.
    """

    jd_ut:          float
    longitude:      float
    sign:           str
    sign_symbol:    str
    degree_in_sign: float
    element:        GreatMutationElement


@dataclass(frozen=True, slots=True)
class GreatConjunctionSeries:
    """
    A series of Jupiter–Saturn conjunctions over a date range.

    Fields
    ------
    jd_start, jd_end : float
        Search window.
    conjunctions : tuple[GreatConjunction, ...]
        All conjunctions found, chronologically ordered.
    count : int
        Number of conjunctions.
    elements_represented : tuple[GreatMutationElement, ...]
        Distinct elements that appear, in order of first occurrence.
    """

    jd_start:              float
    jd_end:                float
    conjunctions:          tuple[GreatConjunction, ...]
    count:                 int
    elements_represented:  tuple[GreatMutationElement, ...]


@dataclass(frozen=True, slots=True)
class MutationPeriod:
    """
    A ~200-year period during which great conjunctions predominate
    in one elemental trigon.

    Fields
    ------
    element : GreatMutationElement
        The dominant element.
    start_conjunction : GreatConjunction
        The first conjunction that inaugurated this element period.
    end_conjunction : GreatConjunction | None
        The final conjunction in this element before mutation. None if
        the period extends beyond the search window.
    conjunction_count : int
        Number of conjunctions in this element during this period.
    """

    element:              GreatMutationElement
    start_conjunction:    GreatConjunction
    end_conjunction:      GreatConjunction | None
    conjunction_count:    int


# ---- Planetary Ages ----

@dataclass(frozen=True, slots=True)
class PlanetaryAgePeriod:
    """
    One stage in Ptolemy's seven ages of life.

    Planetary ages (Tetrabiblos I.10):
        Moon      0–4    infancy (rapid growth, nourishment)
        Mercury   4–14   childhood (learning, speech, reason)
        Venus    14–22   adolescence (desire, erotic impulse)
        Sun      22–41   prime (authority, ambition, mastery)
        Mars     41–56   maturity (severity, toil, discontent)
        Jupiter  56–68   elder years (retreat, dignity, foresight)
        Saturn   68+     old age (cooling, dulling, decay)
    """

    ruler:      PlanetaryAgeName
    start_age:  float
    end_age:    float | None    # None for Saturn (open-ended)
    label:      str


@dataclass(frozen=True, slots=True)
class PlanetaryAgeProfile:
    """
    The full seven-age model as a single object.

    Fields
    ------
    periods : tuple[PlanetaryAgePeriod, ...]
        All seven age periods in order.
    current : PlanetaryAgePeriod | None
        The age period for a queried age, or None if not queried.
    queried_age : float | None
        The age that was queried (years), or None.
    """

    periods:      tuple[PlanetaryAgePeriod, ...]
    current:      PlanetaryAgePeriod | None = None
    queried_age:  float | None = None


# ---- Firdar ----

@dataclass(frozen=True, slots=True)
class FirdarSubPeriod:
    """
    One sub-period within a major firdar.

    Each major firdar is divided into 7 sub-periods (one for each classical
    planet), each proportional to the major firdar's duration.  The sub-rulers
    follow the Chaldean order starting from the major ruler.

    Fields
    ------
    sub_ruler : str
        The planet governing this sub-period.
    start_jd : float
        Start of this sub-period (JD UT).
    end_jd : float
        End of this sub-period (JD UT).
    duration_years : float
        Duration in Julian years.
    """

    sub_ruler:      str
    start_jd:       float
    end_jd:         float
    duration_years: float


@dataclass(frozen=True, slots=True)
class FirdarPeriod:
    """
    One major firdar period.

    Authority: Abu Ma'shar, Bonatti.

    Diurnal sequence (day births):
        Sun(10) → Venus(8) → Mercury(13) → Moon(9) → Saturn(11) →
        Jupiter(12) → Mars(7) → North Node(3) → South Node(2) = 75 years

    Nocturnal sequence (night births):
        Moon(9) → Saturn(11) → Jupiter(12) → Mars(7) → Sun(10) →
        Venus(8) → Mercury(13) → North Node(3) → South Node(2) = 75 years

    Fields
    ------
    ruler : str
        The planet (or node) governing this firdar.
    start_jd : float
        Start of this firdar (JD UT).
    end_jd : float
        End of this firdar (JD UT).
    duration_years : float
        Duration in Julian years.
    ordinal : int
        Position in the sequence (1–9).
    sub_periods : tuple[FirdarSubPeriod, ...] | None
        The 7 planetary sub-periods (None for nodal firdars which some
        authorities leave undivided).
    """

    ruler:           str
    start_jd:        float
    end_jd:          float
    duration_years:  float
    ordinal:         int
    sub_periods:     tuple[FirdarSubPeriod, ...] | None


@dataclass(frozen=True, slots=True)
class FirdarSeries:
    """
    The complete 75-year firdar sequence for a nativity.

    Fields
    ------
    birth_jd : float
        Birth Julian Day.
    is_day_birth : bool
        True if diurnal nativity.
    periods : tuple[FirdarPeriod, ...]
        All 9 firdar periods in sequence.
    total_years : float
        Sum of all periods (~75 Julian years).
    """

    birth_jd:     float
    is_day_birth: bool
    periods:      tuple[FirdarPeriod, ...]
    total_years:  float


# ---- Planetary Days and Hours ----

@dataclass(frozen=True, slots=True)
class PlanetaryDayInfo:
    """
    The planetary ruler of a calendar day.

    Fields
    ------
    ruler : str
        The planet ruling this day.
    weekday_name : str
        The name of the weekday.
    weekday_number : int
        ISO weekday (1 = Monday, 7 = Sunday).
    """

    ruler:          str
    weekday_name:   str
    weekday_number: int


@dataclass(frozen=True, slots=True)
class PlanetaryHour:
    """
    One planetary hour within a day.

    Fields
    ------
    hour_number : int
        1–24 (1–12 are day hours, 13–24 are night hours).
    ruler : str
        The planet governing this hour.
    start_jd : float
        Start of this hour (JD UT).
    end_jd : float
        End of this hour (JD UT).
    is_day_hour : bool
        True if this is a daytime (diurnal) hour.
    """

    hour_number: int
    ruler:       str
    start_jd:    float
    end_jd:      float
    is_day_hour: bool


@dataclass(frozen=True, slots=True)
class PlanetaryHoursProfile:
    """
    All 24 planetary hours for one day, with day ruler.

    Fields
    ------
    day_info : PlanetaryDayInfo
        The day's planetary ruler and weekday.
    sunrise_jd : float
        Sunrise JD used.
    sunset_jd : float
        Sunset JD used.
    next_sunrise_jd : float
        Next sunrise JD used (for nighttime hour duration).
    hours : tuple[PlanetaryHour, ...]
        All 24 planetary hours in order (1–24).
    day_hour_length : float
        Duration of one daytime hour (days).
    night_hour_length : float
        Duration of one nighttime hour (days).
    """

    day_info:          PlanetaryDayInfo
    sunrise_jd:        float
    sunset_jd:         float
    next_sunrise_jd:   float
    hours:             tuple[PlanetaryHour, ...]
    day_hour_length:   float
    night_hour_length: float


# ===========================================================================
# SECTION 3 — RETURN SERIES
# ===========================================================================

def return_series(
    body: str,
    natal_lon: float,
    jd_start: float,
    jd_end: float,
    reader: SpkReader | None = None,
) -> ReturnSeries:
    """
    Find all returns of *body* to *natal_lon* within a date range.

    Iterates forward from *jd_start*, calling the ephemeris solver for
    each successive return until *jd_end* is exceeded.

    Parameters
    ----------
    body       : body name constant (e.g. Body.SATURN)
    natal_lon  : natal ecliptic longitude to return to (degrees)
    jd_start   : search window start (JD UT)
    jd_end     : search window end (JD UT)
    reader     : optional SpkReader

    Returns
    -------
    ReturnSeries with all returns found.
    """
    from .transits import planet_return

    if reader is None:
        reader = get_reader()

    events: list[ReturnEvent] = []
    jd = jd_start
    n = 0

    # When planet_return fails (search window exhausted), advance by
    # a fraction of the search window to avoid skipping over any return.
    # planet_return's window is _RETURN_SEARCH_DAYS which is ~450 for Saturn.
    # We advance by half that, ensuring overlap so no return is missed.
    from .transits import _RETURN_SEARCH_DAYS
    _advance = _RETURN_SEARCH_DAYS.get(body, 400.0) * 0.5

    while jd < jd_end:
        try:
            jd_ret = planet_return(body, natal_lon, jd, reader=reader)
        except RuntimeError:
            # Search window exhausted without finding a return.
            # Advance by half the search window and retry.
            jd += _advance
            continue
        except Exception:
            break
        if jd_ret > jd_end:
            break
        n += 1
        events.append(ReturnEvent(
            body=body,
            return_number=n,
            jd_ut=jd_ret,
            longitude=natal_lon,
        ))
        # Advance past this return by a safe margin.
        jd = jd_ret + 5.0

    return ReturnSeries(
        body=body,
        natal_longitude=natal_lon,
        jd_start=jd_start,
        jd_end=jd_end,
        returns=tuple(events),
        count=len(events),
    )


def half_return_series(
    body: str,
    natal_lon: float,
    jd_start: float,
    jd_end: float,
    reader: SpkReader | None = None,
) -> ReturnSeries:
    """
    Find all half-returns (oppositions to natal longitude) within a date range.

    A half-return occurs when the body reaches natal_lon + 180°.

    Parameters
    ----------
    body       : body name constant
    natal_lon  : natal longitude (degrees)
    jd_start   : search window start (JD UT)
    jd_end     : search window end (JD UT)
    reader     : optional SpkReader

    Returns
    -------
    ReturnSeries with is_half=True on every event.
    """
    from .transits import planet_return

    if reader is None:
        reader = get_reader()

    opp_lon = (natal_lon + 180.0) % 360.0
    events: list[ReturnEvent] = []
    jd = jd_start
    n = 0

    from .transits import _RETURN_SEARCH_DAYS
    _advance = _RETURN_SEARCH_DAYS.get(body, 400.0) * 0.5

    while jd < jd_end:
        try:
            jd_ret = planet_return(body, opp_lon, jd, reader=reader)
        except RuntimeError:
            jd += _advance
            continue
        except Exception:
            break
        if jd_ret > jd_end:
            break
        n += 1
        events.append(ReturnEvent(
            body=body,
            return_number=n,
            jd_ut=jd_ret,
            longitude=natal_lon,
            is_half=True,
        ))
        jd = jd_ret + 5.0

    return ReturnSeries(
        body=body,
        natal_longitude=natal_lon,
        jd_start=jd_start,
        jd_end=jd_end,
        returns=tuple(events),
        count=len(events),
    )


def lifetime_returns(
    body: str,
    natal_lon: float,
    birth_jd: float,
    years: float = 90.0,
    reader: SpkReader | None = None,
) -> ReturnSeries:
    """
    Convenience wrapper: all returns of *body* over a human lifetime.

    Parameters
    ----------
    body       : body name constant
    natal_lon  : natal longitude (degrees)
    birth_jd   : birth Julian Day (UT)
    years      : lifespan to cover (default 90 years)
    reader     : optional SpkReader

    Returns
    -------
    ReturnSeries covering birth_jd to birth_jd + years.
    """
    jd_end = birth_jd + years * _JULIAN_YEAR
    return return_series(body, natal_lon, birth_jd, jd_end, reader=reader)


# ===========================================================================
# SECTION 4 — SYNODIC CYCLE ANALYSIS
# ===========================================================================

def synodic_cycle_position(
    body1: str,
    body2: str,
    jd_ut: float,
    reader: SpkReader | None = None,
) -> SynodicCyclePosition:
    """
    Evaluate where two bodies stand in their synodic cycle at a given moment.

    Parameters
    ----------
    body1, body2 : body names
    jd_ut        : moment of evaluation (JD UT)
    reader       : optional SpkReader

    Returns
    -------
    SynodicCyclePosition with phase angle, 8-fold phase, waxing flag,
    and the longitudes of both bodies.
    """
    from .planets import planet_at

    if reader is None:
        reader = get_reader()

    p1 = planet_at(body1, jd_ut, reader=reader, apparent=True)
    p2 = planet_at(body2, jd_ut, reader=reader, apparent=True)
    angle = (p2.longitude - p1.longitude) % 360.0
    phase = SynodicPhase.from_angle(angle)

    return SynodicCyclePosition(
        body1=body1,
        body2=body2,
        jd_ut=jd_ut,
        phase_angle=angle,
        phase=phase,
        is_waxing=(0.0 < angle < 180.0),
        lon1=p1.longitude,
        lon2=p2.longitude,
    )


# ===========================================================================
# SECTION 5 — GREAT CONJUNCTIONS (Jupiter–Saturn)
# ===========================================================================

# Sign-to-element mapping. Indices 0–11 map to Aries through Pisces.
_SIGN_ELEMENT: tuple[GreatMutationElement, ...] = (
    GreatMutationElement.FIRE,    # Aries
    GreatMutationElement.EARTH,   # Taurus
    GreatMutationElement.AIR,     # Gemini
    GreatMutationElement.WATER,   # Cancer
    GreatMutationElement.FIRE,    # Leo
    GreatMutationElement.EARTH,   # Virgo
    GreatMutationElement.AIR,     # Libra
    GreatMutationElement.WATER,   # Scorpio
    GreatMutationElement.FIRE,    # Sagittarius
    GreatMutationElement.EARTH,   # Capricorn
    GreatMutationElement.AIR,     # Aquarius
    GreatMutationElement.WATER,   # Pisces
)


def mutation_period_at(longitude: float) -> GreatMutationElement:
    """
    Return the elemental trigon for a given ecliptic longitude.

    This answers: "A great conjunction at this longitude falls in which
    elemental trigon?"
    """
    idx = int(longitude % 360.0 // 30.0)
    return _SIGN_ELEMENT[idx]


def great_conjunctions(
    jd_start: float,
    jd_end: float,
    reader: SpkReader | None = None,
) -> GreatConjunctionSeries:
    """
    Find all Jupiter–Saturn conjunctions in a date range.

    Each conjunction is classified by zodiac sign and elemental trigon.
    The ~20-year Jupiter–Saturn cycle is the foundation of mundane astrology's
    great conjunction doctrine (Abu Ma'shar, Kepler).

    Approximate periodicity:
        Synodic period     ~19.86 years
        Trigon shift       ~10 conjunctions (~200 years) per element
        Full mutation      ~4 elements × ~200 years = ~800 years

    Parameters
    ----------
    jd_start : search window start (JD UT)
    jd_end   : search window end (JD UT)
    reader   : optional SpkReader

    Returns
    -------
    GreatConjunctionSeries
    """
    from .phenomena import conjunctions_in_range as _conj_range

    if reader is None:
        reader = get_reader()

    raw = _conj_range(Body.JUPITER, Body.SATURN, jd_start, jd_end, reader=reader)

    conjs: list[GreatConjunction] = []
    seen_elements: list[GreatMutationElement] = []

    for ev in raw:
        sign_name, sign_sym, deg_in_sign = sign_of(ev.value)
        element = mutation_period_at(ev.value)

        conjs.append(GreatConjunction(
            jd_ut=ev.jd_ut,
            longitude=ev.value,
            sign=sign_name,
            sign_symbol=sign_sym,
            degree_in_sign=deg_in_sign,
            element=element,
        ))
        if element not in seen_elements:
            seen_elements.append(element)

    return GreatConjunctionSeries(
        jd_start=jd_start,
        jd_end=jd_end,
        conjunctions=tuple(conjs),
        count=len(conjs),
        elements_represented=tuple(seen_elements),
    )


# ===========================================================================
# SECTION 6 — PLANETARY AGES (Ptolemy, Tetrabiblos I.10)
# ===========================================================================
#
# Ptolemy assigns each planet governance over an age of life, following
# the Chaldean order from fastest (Moon) to slowest (Saturn):
#
#   Moon     0–4     infancy, nourishment, rapid physical change
#   Mercury  4–14    childhood, learning, speech, rational faculty
#   Venus   14–22    adolescence, desire, erotic impulse
#   Sun     22–41    prime of life, authority, ambition, action
#   Mars    41–56    maturity, severity, toil, the beginning of decline
#   Jupiter 56–68    elder years, withdrawal, dignity, philosophy
#   Saturn  68+      old age, cooling, lessening, contraction
#
# The boundaries are Ptolemy's; the interpretive tone is his.
# ===========================================================================

_PTOLEMAIC_AGES: tuple[tuple[PlanetaryAgeName, float, float | None, str], ...] = (
    (PlanetaryAgeName.MOON,    0.0,  4.0,  "Infancy: nourishment, rapid growth"),
    (PlanetaryAgeName.MERCURY, 4.0,  14.0, "Childhood: learning, reason, speech"),
    (PlanetaryAgeName.VENUS,   14.0, 22.0, "Adolescence: desire, beauty, erotic impulse"),
    (PlanetaryAgeName.SUN,     22.0, 41.0, "Prime: authority, ambition, mastery"),
    (PlanetaryAgeName.MARS,    41.0, 56.0, "Maturity: severity, toil, discontent"),
    (PlanetaryAgeName.JUPITER, 56.0, 68.0, "Elder years: retreat, dignity, foresight"),
    (PlanetaryAgeName.SATURN,  68.0, None, "Old age: cooling, contraction, decay"),
)


def _build_age_period(row: tuple[PlanetaryAgeName, float, float | None, str]) -> PlanetaryAgePeriod:
    return PlanetaryAgePeriod(ruler=row[0], start_age=row[1], end_age=row[2], label=row[3])


def planetary_age_at(age_years: float) -> PlanetaryAgePeriod:
    """
    Return the Ptolemaic planetary age period for a given age in years.

    Parameters
    ----------
    age_years : age in years (may be fractional)

    Returns
    -------
    PlanetaryAgePeriod for the applicable stage of life.

    Raises
    ------
    ValueError if age_years is negative.
    """
    if age_years < 0:
        raise ValueError(f"age must be non-negative, got {age_years}")
    for row in _PTOLEMAIC_AGES:
        if row[2] is None or age_years < row[2]:
            return _build_age_period(row)
    # Should not reach here; Saturn is open-ended.
    return _build_age_period(_PTOLEMAIC_AGES[-1])


def planetary_age_profile(age_years: float | None = None) -> PlanetaryAgeProfile:
    """
    Return the complete seven-age model.

    Parameters
    ----------
    age_years : optional age to identify the current period.

    Returns
    -------
    PlanetaryAgeProfile with all 7 periods and optionally the current one.
    """
    periods = tuple(_build_age_period(row) for row in _PTOLEMAIC_AGES)
    current = planetary_age_at(age_years) if age_years is not None else None
    return PlanetaryAgeProfile(
        periods=periods,
        current=current,
        queried_age=age_years,
    )


# ===========================================================================
# SECTION 7 — FIRDAR (Abu Ma'shar, Bonatti)
# ===========================================================================
#
# The firdar (firdāriyyāt, from Greek periodos) divides a 75-year life
# cycle into 9 major periods, each ruled by a planet or node.
#
# Two sequences exist — one for day births, one for night births —
# differing only in the planetary starting ruler.  The final two
# periods (North Node, South Node) are shared.
#
# Each planetary firdar (the first 7) is subdivided into 7 sub-periods,
# each ruled by one of the 7 classical planets in Chaldean order,
# beginning from the major ruler.  The nodal firdars (last 2) are
# traditionally left undivided by most authorities.
# ===========================================================================

# (ruler_name, duration_in_years)
_FIRDAR_DIURNAL: tuple[tuple[str, float], ...] = (
    (Body.SUN,     10.0),
    (Body.VENUS,    8.0),
    (Body.MERCURY, 13.0),
    (Body.MOON,     9.0),
    (Body.SATURN,  11.0),
    (Body.JUPITER, 12.0),
    (Body.MARS,     7.0),
    ("North Node",  3.0),
    ("South Node",  2.0),
)

_FIRDAR_NOCTURNAL: tuple[tuple[str, float], ...] = (
    (Body.MOON,     9.0),
    (Body.SATURN,  11.0),
    (Body.JUPITER, 12.0),
    (Body.MARS,     7.0),
    (Body.SUN,     10.0),
    (Body.VENUS,    8.0),
    (Body.MERCURY, 13.0),
    ("North Node",  3.0),
    ("South Node",  2.0),
)

_NODE_RULERS = frozenset({"North Node", "South Node"})


def _firdar_sub_periods(
    ruler: str,
    start_jd: float,
    duration_years: float,
) -> tuple[FirdarSubPeriod, ...]:
    """
    Generate the 7 sub-periods for a planetary firdar.

    Each sub-period is proportional: duration = major_duration / 7.
    Sub-rulers follow the Chaldean order starting from the major ruler.
    """
    sub_dur_years = duration_years / 7.0
    sub_dur_days = sub_dur_years * _JULIAN_YEAR

    # Find starting index in the Chaldean order.
    start_idx = _CHALDEAN_INDEX.get(ruler, 0)

    subs: list[FirdarSubPeriod] = []
    jd = start_jd
    for i in range(7):
        sub_ruler = CHALDEAN_ORDER[(start_idx + i) % 7]
        subs.append(FirdarSubPeriod(
            sub_ruler=sub_ruler,
            start_jd=jd,
            end_jd=jd + sub_dur_days,
            duration_years=sub_dur_years,
        ))
        jd += sub_dur_days

    return tuple(subs)


def firdar_series(birth_jd: float, is_day_birth: bool) -> FirdarSeries:
    """
    Compute the complete 75-year firdar sequence for a nativity.

    Parameters
    ----------
    birth_jd     : birth Julian Day (UT)
    is_day_birth : True for diurnal chart, False for nocturnal

    Returns
    -------
    FirdarSeries with all 9 major periods and their sub-periods.
    """
    sequence = _FIRDAR_DIURNAL if is_day_birth else _FIRDAR_NOCTURNAL
    periods: list[FirdarPeriod] = []
    jd = birth_jd
    total = 0.0

    for ordinal, (ruler, dur_years) in enumerate(sequence, start=1):
        dur_days = dur_years * _JULIAN_YEAR
        is_node = ruler in _NODE_RULERS

        subs = None if is_node else _firdar_sub_periods(ruler, jd, dur_years)

        periods.append(FirdarPeriod(
            ruler=ruler,
            start_jd=jd,
            end_jd=jd + dur_days,
            duration_years=dur_years,
            ordinal=ordinal,
            sub_periods=subs,
        ))
        jd += dur_days
        total += dur_years

    return FirdarSeries(
        birth_jd=birth_jd,
        is_day_birth=is_day_birth,
        periods=tuple(periods),
        total_years=total,
    )


def firdar_at(
    birth_jd: float,
    target_jd: float,
    is_day_birth: bool,
) -> FirdarPeriod:
    """
    Find the active firdar at a specific moment.

    Parameters
    ----------
    birth_jd     : birth Julian Day (UT)
    target_jd    : moment to query (JD UT)
    is_day_birth : True for diurnal chart

    Returns
    -------
    The FirdarPeriod active at target_jd.

    Raises
    ------
    ValueError if target_jd is before birth or beyond the 75-year cycle.
    """
    if target_jd < birth_jd:
        raise ValueError("target_jd precedes birth_jd")

    series = firdar_series(birth_jd, is_day_birth)
    for period in series.periods:
        if period.start_jd <= target_jd < period.end_jd:
            return period

    raise ValueError(
        f"target_jd {target_jd} is beyond the 75-year firdar cycle "
        f"(ends at {series.periods[-1].end_jd})"
    )


# ===========================================================================
# SECTION 8 — PLANETARY DAYS AND HOURS
# ===========================================================================
#
# The planetary weekday scheme assigns each day to a planet based on the
# Chaldean order.  The first "hour" of each day (starting at sunrise) is
# ruled by that day's planet; subsequent hours follow the Chaldean sequence.
#
# Day/night are divided into 12 temporal hours each (unequal hours that
# vary by season and latitude).
#
# Day-ruler table:
#   Monday     Moon        Friday     Venus
#   Tuesday    Mars        Saturday   Saturn
#   Wednesday  Mercury     Sunday     Sun
#   Thursday   Jupiter
#
# The system is self-consistent: the 25th hour (= first hour of the
# next day) falls on the next day's ruler in the Chaldean sequence.
# ===========================================================================

_WEEKDAY_NAMES: tuple[str, ...] = (
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
)

# Maps ISO weekday index (0=Mon … 6=Sun) to the day ruler.
_DAY_RULERS: tuple[str, ...] = (
    Body.MOON,     # Monday
    Body.MARS,     # Tuesday
    Body.MERCURY,  # Wednesday
    Body.JUPITER,  # Thursday
    Body.VENUS,    # Friday
    Body.SATURN,   # Saturday
    Body.SUN,      # Sunday
)


def _jd_to_weekday(jd: float) -> int:
    """
    Return the ISO weekday index (0 = Monday, 6 = Sunday) for a Julian Day.

    The Julian Day count starts at noon; JD 0.0 = Monday noon,
    January 1, 4713 BC (proleptic Julian).
    """
    return int(jd + 0.5) % 7


def planetary_day_ruler(jd: float) -> PlanetaryDayInfo:
    """
    Return the planetary day ruler for a given Julian Day.

    The "astrological day" begins at sunrise, but for this function we use
    the calendar day (midnight to midnight ≈ noon JD convention) since
    sunrise requires geographic coordinates.  For sunrise-accurate day rulers,
    compare jd to the sunrise_jd of the location.

    Parameters
    ----------
    jd : Julian Day (UT)

    Returns
    -------
    PlanetaryDayInfo with ruler, weekday name, and ISO weekday number.
    """
    wd = _jd_to_weekday(jd)
    return PlanetaryDayInfo(
        ruler=_DAY_RULERS[wd],
        weekday_name=_WEEKDAY_NAMES[wd],
        weekday_number=wd + 1,  # ISO 1–7
    )


def planetary_hours_for_day(
    sunrise_jd: float,
    sunset_jd: float,
    next_sunrise_jd: float | None = None,
) -> PlanetaryHoursProfile:
    """
    Compute the 24 planetary hours for a single day.

    The astrological day begins at sunrise.  Daytime (sunrise → sunset) is
    divided into 12 equal temporal hours; nighttime (sunset → next sunrise)
    into another 12.  Each hour is ruled by a planet following the Chaldean
    sequence from the day ruler.

    Parameters
    ----------
    sunrise_jd      : Julian Day of sunrise
    sunset_jd       : Julian Day of sunset
    next_sunrise_jd : Julian Day of next sunrise.  If None, estimated as
                      sunrise_jd + 1.0 (approximate).

    Returns
    -------
    PlanetaryHoursProfile with all 24 hours and their rulers.
    """
    if next_sunrise_jd is None:
        next_sunrise_jd = sunrise_jd + 1.0

    day_length = sunset_jd - sunrise_jd
    night_length = next_sunrise_jd - sunset_jd
    day_hour = day_length / 12.0
    night_hour = night_length / 12.0

    # The day ruler is determined by the weekday at sunrise.
    day_info = planetary_day_ruler(sunrise_jd)
    start_chaldean_idx = _CHALDEAN_INDEX[day_info.ruler]

    hours: list[PlanetaryHour] = []

    for h in range(24):
        ruler = CHALDEAN_ORDER[(start_chaldean_idx + h) % 7]
        if h < 12:
            # Day hours
            h_start = sunrise_jd + h * day_hour
            h_end = sunrise_jd + (h + 1) * day_hour
            is_day = True
        else:
            # Night hours
            n = h - 12
            h_start = sunset_jd + n * night_hour
            h_end = sunset_jd + (n + 1) * night_hour
            is_day = False

        hours.append(PlanetaryHour(
            hour_number=h + 1,
            ruler=ruler,
            start_jd=h_start,
            end_jd=h_end,
            is_day_hour=is_day,
        ))

    return PlanetaryHoursProfile(
        day_info=day_info,
        sunrise_jd=sunrise_jd,
        sunset_jd=sunset_jd,
        next_sunrise_jd=next_sunrise_jd,
        hours=tuple(hours),
        day_hour_length=day_hour,
        night_hour_length=night_hour,
    )

"""
Moira — profections.py
The Profection Engine: governs annual and monthly profection calculations
(Hellenistic time-lord technique).

Boundary: owns profection arithmetic, domicile ruler lookup, and activated-planet
detection. Delegates sign derivation to constants. Delegates Julian Day arithmetic
to julian. Does NOT own natal chart construction or ephemeris state.

Public surface:
    DOMICILE_RULERS, ProfectionResult,
    annual_profection, monthly_profection, profection_schedule

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
"""

from dataclasses import dataclass

from .constants import sign_of
from .julian import decimal_year_from_jd

__all__ = [
    "DOMICILE_RULERS",
    "ProfectionResult",
    "annual_profection",
    "monthly_profection",
    "profection_schedule",
]


# ---------------------------------------------------------------------------
# Domicile rulers — classical 7 planets only
# Scorpio → Mars, Aquarius → Saturn, Pisces → Jupiter (pre-modern rulerships)
# ---------------------------------------------------------------------------

DOMICILE_RULERS: dict[str, str] = {
    "Aries":       "Mars",
    "Taurus":      "Venus",
    "Gemini":      "Mercury",
    "Cancer":      "Moon",
    "Leo":         "Sun",
    "Virgo":       "Mercury",
    "Libra":       "Venus",
    "Scorpio":     "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn":   "Saturn",
    "Aquarius":    "Saturn",
    "Pisces":      "Jupiter",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ProfectionResult:
    """
    RITE: The Profection Result Vessel

    THEOREM: Governs the storage of a complete annual profection calculation for a
    given age.

    RITE OF PURPOSE:
        ProfectionResult is the authoritative data vessel for a complete annual
        profection produced by the Profection Engine. It captures the completed age,
        the profected house number, the profected Ascendant longitude, the profected
        sign, the Lord of the Year, any activated planets, and the twelve monthly
        lords. Without it, callers would receive unstructured tuples with no
        field-level guarantees. It exists to give every higher-level consumer a
        single, named, mutable record of each annual profection.

    LAW OF OPERATION:
        Responsibilities:
            - Store a complete annual profection as named, typed fields
            - Carry the twelve monthly lords as a list of classical ruler names
            - Carry activated planets as a list of body names within orb
            - Serve as the return type of annual_profection() and profection_schedule()
        Non-responsibilities:
            - Computing profection arithmetic (delegates to annual_profection)
            - Resolving natal positions from ephemeris (delegates to planets)
        Dependencies:
            - Populated by annual_profection() and profection_schedule()
        Structural invariants:
            - profected_house is in [1, 12]
            - profected_asc_lon is in [0, 360)
            - monthly_lords has exactly 12 entries
        Behavioral invariants:
            - All consumers treat ProfectionResult fields as read-only after construction

    Canon: Chris Brennan, "Hellenistic Astrology" Ch.9; Vettius Valens, Anthology

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.profections.ProfectionResult",
      "risk": "high",
      "api": {
        "frozen": ["age_years", "profected_house", "profected_asc_lon", "profected_sign", "lord_of_year", "activated_planets", "monthly_lords"],
        "internal": []
      },
      "state": {"mutable": true, "owners": ["annual_profection", "profection_schedule"]},
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
    age_years:         int
    profected_house:   int        # 1–12
    profected_asc_lon: float      # ecliptic longitude of the profected Ascendant
    profected_sign:    str        # sign name at the profected Ascendant
    lord_of_year:      str        # classical domicile ruler of the profected sign
    activated_planets: list[str]  # planets within orb of the profected Ascendant
    monthly_lords:     list[str]  # lord of each of the 12 profected months (12 items)

    def __repr__(self) -> str:
        acts = ", ".join(self.activated_planets) if self.activated_planets else "—"
        return (
            f"ProfectionResult(age={self.age_years}, "
            f"house={self.profected_house}, sign={self.profected_sign}, "
            f"lord={self.lord_of_year}, activated=[{acts}])"
        )


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _angular_distance(a: float, b: float) -> float:
    """Minimum arc between two ecliptic longitudes (0–180°)."""
    diff = abs(a % 360.0 - b % 360.0)
    return min(diff, 360.0 - diff)


def _monthly_lord_list(profected_asc_lon: float) -> list[str]:
    """
    Return the list of 12 monthly lords, starting from the profected Ascendant
    sign and advancing one sign per month.
    """
    lords: list[str] = []
    for month_idx in range(12):
        lon = (profected_asc_lon + month_idx * 30.0) % 360.0
        sign, _, _ = sign_of(lon)
        lords.append(DOMICILE_RULERS[sign])
    return lords


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def annual_profection(
    natal_asc: float,
    age_years: int,
    natal_positions: dict[str, float] | None = None,
    activation_orb: float = 5.0,
) -> ProfectionResult:
    """
    Calculate the Annual Profection for a given age.

    The natal Ascendant moves 30° per year of life; the sign reached becomes
    the Profected House and its classical ruler is the Lord of the Year.

    Parameters
    ----------
    natal_asc : float
        Natal Ascendant longitude in degrees (0–360).
    age_years : int
        Completed years of life (e.g. 30 for someone who has turned 30).
    natal_positions : dict[str, float] or None
        Mapping of body name → natal longitude.  Used to find activated
        planets (bodies conjunct the profected Ascendant within orb).
    activation_orb : float
        Orb in degrees for activated planet detection (default 5.0°).

    Returns
    -------
    ProfectionResult
    """
    profected_asc_lon = (natal_asc + age_years * 30.0) % 360.0
    profected_sign, _, _ = sign_of(profected_asc_lon)
    lord_of_year = DOMICILE_RULERS[profected_sign]
    profected_house = (age_years % 12) + 1

    # Activated planets: natal bodies conjunct the profected Ascendant
    activated: list[str] = []
    if natal_positions:
        for name, lon in natal_positions.items():
            if _angular_distance(profected_asc_lon, lon) <= activation_orb:
                activated.append(name)

    monthly_lords = _monthly_lord_list(profected_asc_lon)

    return ProfectionResult(
        age_years=age_years,
        profected_house=profected_house,
        profected_asc_lon=profected_asc_lon,
        profected_sign=profected_sign,
        lord_of_year=lord_of_year,
        activated_planets=activated,
        monthly_lords=monthly_lords,
    )


def monthly_profection(
    natal_asc: float,
    age_years: int,
    month_index: int,
) -> tuple[float, str, str]:
    """
    Calculate a monthly profection within the profected year.

    Month 0 is the opening month (same sign as the annual profection);
    Month 11 is 11 houses further.

    Parameters
    ----------
    natal_asc : float
        Natal Ascendant longitude in degrees (0–360).
    age_years : int
        Completed years of life.
    month_index : int
        Month offset within the profected year (0–11).

    Returns
    -------
    tuple[float, str, str]
        (profected_longitude, sign_name, lord_of_month)
    """
    annual_lon = (natal_asc + age_years * 30.0) % 360.0
    monthly_lon = (annual_lon + month_index * 30.0) % 360.0
    sign, _, _ = sign_of(monthly_lon)
    lord = DOMICILE_RULERS[sign]
    return monthly_lon, sign, lord


def profection_schedule(
    natal_asc: float,
    natal_jd: float,
    current_jd: float,
    natal_positions: dict[str, float] | None = None,
) -> ProfectionResult:
    """
    Compute the current profection from birth JD and current JD.

    Age is determined from the fractional elapsed Julian years (365.25 days).
    The integer part of the elapsed years is used as the completed age.

    Parameters
    ----------
    natal_asc : float
        Natal Ascendant longitude in degrees (0–360).
    natal_jd : float
        Julian Day (UT) of birth.
    current_jd : float
        Julian Day (UT) of the date to evaluate.
    natal_positions : dict[str, float] or None
        Natal planet positions for activated-planet detection.

    Returns
    -------
    ProfectionResult
    """
    elapsed_days = current_jd - natal_jd
    age_years    = int(elapsed_days / 365.25)  # completed years
    return annual_profection(natal_asc, age_years, natal_positions)

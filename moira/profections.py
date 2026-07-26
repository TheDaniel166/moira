"""
Moira — profections.py
The Profection Engine: governs annual and monthly profection calculations
(Hellenistic time-lord technique).

Boundary: owns profection arithmetic, civil-anniversary age resolution,
domicile ruler lookup, and activated-planet detection. Delegates sign
derivation to constants. Does NOT own natal chart construction or ephemeris
state.

Public surface:
    DOMICILE_RULERS, LeapDayAnniversaryPolicy, ProfectionActivationStatus,
    ProfectionActivationBodyTruth, ProfectionActivationTruth, ProfectionResult,
    profection_activation_truth, annual_profection, monthly_profection,
    profection_schedule

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import math

from .constants import sign_of

__all__ = [
    "DOMICILE_RULERS",
    "LeapDayAnniversaryPolicy",
    "ProfectionActivationStatus",
    "ProfectionActivationBodyTruth",
    "ProfectionActivationTruth",
    "ProfectionResult",
    "profection_activation_truth",
    "annual_profection",
    "monthly_profection",
    "profection_schedule",
]


class LeapDayAnniversaryPolicy(StrEnum):
    """Civil-anniversary policy for a February 29 nativity."""

    FEBRUARY_28 = "february_28"
    MARCH_1 = "march_1"


class ProfectionActivationStatus(StrEnum):
    """Whether natal-position activation was actually evaluated."""

    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"


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
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ProfectionActivationBodyTruth:
    """One supplied natal body's distance from the profected Ascendant."""

    body: str
    natal_longitude: float
    distance_from_profected_asc_deg: float
    activated: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.body, str)
            or not self.body
            or self.body != self.body.strip()
        ):
            raise ValueError(
                "ProfectionActivationBodyTruth body must be a "
                "non-empty trimmed string"
            )
        if not math.isfinite(self.natal_longitude) or not (
            0.0 <= self.natal_longitude < 360.0
        ):
            raise ValueError(
                "ProfectionActivationBodyTruth natal_longitude must be in [0, 360)"
            )
        if not math.isfinite(self.distance_from_profected_asc_deg) or not (
            0.0 <= self.distance_from_profected_asc_deg <= 180.0
        ):
            raise ValueError(
                "ProfectionActivationBodyTruth distance must be in [0, 180]"
            )
        if not isinstance(self.activated, bool):
            raise ValueError(
                "ProfectionActivationBodyTruth activated must be a boolean"
            )


@dataclass(frozen=True, slots=True)
class ProfectionActivationTruth:
    """Typed natal-body activation receipt for one annual profection."""

    status: ProfectionActivationStatus
    profected_asc_lon: float
    activation_orb_deg: float
    body_truths: tuple[ProfectionActivationBodyTruth, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ProfectionActivationStatus):
            raise ValueError(
                "ProfectionActivationTruth status must be a "
                "ProfectionActivationStatus"
            )
        if not math.isfinite(self.profected_asc_lon) or not (
            0.0 <= self.profected_asc_lon < 360.0
        ):
            raise ValueError(
                "ProfectionActivationTruth profected_asc_lon must be in [0, 360)"
            )
        if not math.isfinite(self.activation_orb_deg) or (
            self.activation_orb_deg < 0.0
        ):
            raise ValueError(
                "ProfectionActivationTruth activation_orb_deg must be "
                "finite and non-negative"
            )
        if any(
            not isinstance(item, ProfectionActivationBodyTruth)
            for item in self.body_truths
        ):
            raise ValueError(
                "ProfectionActivationTruth body_truths must contain "
                "ProfectionActivationBodyTruth values"
            )
        body_names = tuple(item.body for item in self.body_truths)
        if len(body_names) != len(set(body_names)):
            raise ValueError(
                "ProfectionActivationTruth body names must be unique"
            )
        for item in self.body_truths:
            expected_distance = _angular_distance(
                self.profected_asc_lon,
                item.natal_longitude,
            )
            if not math.isclose(
                item.distance_from_profected_asc_deg,
                expected_distance,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    "ProfectionActivationTruth body distance must match "
                    "the profected and natal longitudes"
                )
            expected = (
                item.distance_from_profected_asc_deg
                <= self.activation_orb_deg
            )
            if item.activated is not expected:
                raise ValueError(
                    "ProfectionActivationTruth body activation must match "
                    "distance and orb"
                )
        if self.status is ProfectionActivationStatus.EVALUATED:
            if self.reason is not None:
                raise ValueError(
                    "ProfectionActivationTruth evaluated results cannot "
                    "carry a reason"
                )
        elif (
            self.body_truths
            or self.reason != "natal_positions_not_supplied"
        ):
            raise ValueError(
                "ProfectionActivationTruth not_evaluable results require "
                "no body truth and reason='natal_positions_not_supplied'"
            )

    @property
    def supplied_bodies(self) -> tuple[str, ...]:
        """Body names in caller-supplied mapping order."""

        return tuple(item.body for item in self.body_truths)

    @property
    def activated_planets(self) -> tuple[str, ...]:
        """Compatibility activation list derived from evaluated body truth."""

        if self.status is not ProfectionActivationStatus.EVALUATED:
            return ()
        return tuple(item.body for item in self.body_truths if item.activated)


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
            - activated_planets is the compatibility projection of
              activation_truth when raw truth is present
        Behavioral invariants:
            - All consumers treat ProfectionResult fields as read-only after construction

    Canon: Chris Brennan, "Hellenistic Astrology" Ch.9; Vettius Valens, Anthology

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.profections.ProfectionResult",
      "risk": "high",
      "api": {
        "frozen": ["age_years", "profected_house", "profected_asc_lon", "profected_sign", "lord_of_year", "activated_planets", "monthly_lords", "age_basis", "leap_day_policy", "activation_truth"],
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
    age_basis:          str = "explicit_completed_age"
    leap_day_policy:    LeapDayAnniversaryPolicy | None = None
    activation_truth:   ProfectionActivationTruth | None = None

    def __post_init__(self) -> None:
        if self.activation_truth is None:
            return
        if self.activation_truth.profected_asc_lon != self.profected_asc_lon:
            raise ValueError(
                "ProfectionResult activation_truth longitude must match "
                "profected_asc_lon"
            )
        if list(self.activation_truth.activated_planets) != self.activated_planets:
            raise ValueError(
                "ProfectionResult activated_planets must be the compatibility "
                "projection of activation_truth"
            )

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


def profection_activation_truth(
    profected_asc_lon: float,
    natal_positions: dict[str, float] | None,
    activation_orb: float = 5.0,
) -> ProfectionActivationTruth:
    """Evaluate natal-body conjunctions without collapsing missing inputs."""

    if not math.isfinite(profected_asc_lon):
        raise ValueError("profected_asc_lon must be finite")
    if not math.isfinite(activation_orb) or activation_orb < 0.0:
        raise ValueError("activation_orb must be finite and non-negative")

    target = profected_asc_lon % 360.0
    if natal_positions is None:
        return ProfectionActivationTruth(
            status=ProfectionActivationStatus.NOT_EVALUABLE,
            profected_asc_lon=target,
            activation_orb_deg=activation_orb,
            reason="natal_positions_not_supplied",
        )
    if not isinstance(natal_positions, dict):
        raise TypeError(
            "natal_positions must be a dict of body longitudes or None"
        )

    body_truths: list[ProfectionActivationBodyTruth] = []
    for name, longitude in natal_positions.items():
        if (
            not isinstance(name, str)
            or not name
            or name != name.strip()
        ):
            raise ValueError(
                "natal_positions body names must be non-empty trimmed strings"
            )
        if not math.isfinite(longitude):
            raise ValueError(
                f"natal_positions[{name!r}] must be finite"
            )
        normalized = longitude % 360.0
        distance = _angular_distance(target, normalized)
        body_truths.append(
            ProfectionActivationBodyTruth(
                body=name,
                natal_longitude=normalized,
                distance_from_profected_asc_deg=distance,
                activated=distance <= activation_orb,
            )
        )
    return ProfectionActivationTruth(
        status=ProfectionActivationStatus.EVALUATED,
        profected_asc_lon=target,
        activation_orb_deg=activation_orb,
        body_truths=tuple(body_truths),
    )


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

    activation_truth = profection_activation_truth(
        profected_asc_lon,
        natal_positions,
        activation_orb,
    )
    activated = list(activation_truth.activated_planets)

    monthly_lords = _monthly_lord_list(profected_asc_lon)

    return ProfectionResult(
        age_years=age_years,
        profected_house=profected_house,
        profected_asc_lon=profected_asc_lon,
        profected_sign=profected_sign,
        lord_of_year=lord_of_year,
        activated_planets=activated,
        monthly_lords=monthly_lords,
        activation_truth=activation_truth,
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
    natal_dt: datetime,
    current_dt: datetime,
    natal_positions: dict[str, float] | None = None,
    *,
    leap_day_policy: LeapDayAnniversaryPolicy | str | None = None,
    activation_orb: float = 5.0,
) -> ProfectionResult:
    """
    Compute the current profection from civil anniversary chronology.

    Completed age advances on the anniversary of the natal local date and time,
    not after a fixed 365.25-day quotient. Both datetimes must be timezone-aware;
    the current instant is compared in the natal timezone. A February 29
    nativity requires an explicit anniversary policy.

    Parameters
    ----------
    natal_asc : float
        Natal Ascendant longitude in degrees (0–360).
    natal_dt : datetime
        Timezone-aware civil birth datetime.
    current_dt : datetime
        Timezone-aware instant to evaluate.
    natal_positions : dict[str, float] or None
        Natal planet positions for activated-planet detection.
    activation_orb : float
        Orb in degrees for activated-planet detection (default 5.0°).

    Returns
    -------
    ProfectionResult
    """
    for label, value in (("natal_dt", natal_dt), ("current_dt", current_dt)):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{label} must be timezone-aware")
    if current_dt < natal_dt:
        raise ValueError("current_dt must not be before natal_dt")

    resolved_policy: LeapDayAnniversaryPolicy | None
    if leap_day_policy is None:
        resolved_policy = None
    else:
        try:
            resolved_policy = LeapDayAnniversaryPolicy(leap_day_policy)
        except ValueError as exc:
            raise ValueError(
                "leap_day_policy must be 'february_28' or 'march_1'"
            ) from exc

    is_leap_day_nativity = natal_dt.month == 2 and natal_dt.day == 29
    if is_leap_day_nativity and resolved_policy is None:
        raise ValueError(
            "leap_day_policy is required for a February 29 nativity"
        )

    current_local = current_dt.astimezone(natal_dt.tzinfo)
    candidate_age = current_local.year - natal_dt.year
    try:
        anniversary = natal_dt.replace(year=current_local.year)
    except ValueError:
        assert resolved_policy is not None
        if resolved_policy is LeapDayAnniversaryPolicy.FEBRUARY_28:
            anniversary = natal_dt.replace(
                year=current_local.year,
                month=2,
                day=28,
            )
        else:
            anniversary = natal_dt.replace(
                year=current_local.year,
                month=3,
                day=1,
            )
    age_years = candidate_age - int(current_local < anniversary)

    result = annual_profection(
        natal_asc,
        age_years,
        natal_positions,
        activation_orb=activation_orb,
    )
    result.age_basis = "civil_anniversary"
    result.leap_day_policy = resolved_policy
    return result

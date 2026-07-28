"""
Moira — profections.py
The Profection Engine: governs annual and monthly profection calculations
(Hellenistic time-lord technique).

Boundary: owns profection arithmetic, civil-anniversary age resolution,
domicile ruler lookup, and activated-planet detection. Delegates sign
derivation to constants. Does NOT own natal chart construction or ephemeris
state.

Public surface:
    DOMICILE_RULERS, LeapDayAnniversaryPolicy,
    MonthlyProfectionIntervalPolicy, ProfectionAmbiguousTimePolicy,
    ProfectionChronologyMethod,
    ProfectionIntervalBoundarySemantics, ProfectionActivationStatus,
    ProfectionActivationBodyTruth, ProfectionActivationTruth,
    MonthlyProfectionInterval, ProfectionChronology, ProfectionResult,
    profection_activation_truth, profection_chronology, annual_profection,
    monthly_profection, profection_schedule

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - Explicit IANA timezone chronology uses the host database exposed through
      ``zoneinfo`` and fails closed when that database does not contain the
      requested key.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone, tzinfo
from ._strenum import StrEnum
from functools import lru_cache
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .constants import sign_of
from .julian import jd_from_datetime

__all__ = [
    "DOMICILE_RULERS",
    "LeapDayAnniversaryPolicy",
    "MonthlyProfectionIntervalPolicy",
    "ProfectionAmbiguousTimePolicy",
    "ProfectionChronologyMethod",
    "ProfectionIntervalBoundarySemantics",
    "ProfectionActivationStatus",
    "ProfectionActivationBodyTruth",
    "ProfectionActivationTruth",
    "MonthlyProfectionInterval",
    "ProfectionChronology",
    "ProfectionResult",
    "profection_activation_truth",
    "profection_chronology",
    "annual_profection",
    "monthly_profection",
    "profection_schedule",
]


class LeapDayAnniversaryPolicy(StrEnum):
    """Civil-anniversary policy for a February 29 nativity."""

    FEBRUARY_28 = "february_28"
    MARCH_1 = "march_1"


class MonthlyProfectionIntervalPolicy(StrEnum):
    """Admitted projection from one civil anniversary to twelve intervals."""

    EQUAL_TWELFTHS_OF_CIVIL_ANNIVERSARY_YEAR = (
        "equal_twelfths_of_civil_anniversary_year"
    )


class ProfectionAmbiguousTimePolicy(StrEnum):
    """Explicit resolution for an anniversary wall time repeated by DST."""

    EARLIER_OCCURRENCE = "earlier_occurrence"
    LATER_OCCURRENCE = "later_occurrence"


class ProfectionChronologyMethod(StrEnum):
    """Historical classification of the dated interval construction."""

    COMPUTATIONAL_PROJECTION = "computational_projection"


class ProfectionIntervalBoundarySemantics(StrEnum):
    """Membership rule used by every dated monthly interval."""

    START_INCLUSIVE_END_EXCLUSIVE = "start_inclusive_end_exclusive"


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


@dataclass(frozen=True, slots=True)
class MonthlyProfectionInterval:
    """One dated sign step in an annual profection chronology."""

    month_index: int
    profected_longitude: float
    sign: str
    lord_of_month: str
    start_utc: datetime
    end_utc: datetime
    start_jd: float
    end_jd: float
    active: bool

    def __post_init__(self) -> None:
        if type(self.month_index) is not int or not 0 <= self.month_index <= 11:
            raise ValueError(
                "MonthlyProfectionInterval month_index must be an integer "
                "in [0, 11]"
            )
        if not math.isfinite(self.profected_longitude) or not (
            0.0 <= self.profected_longitude < 360.0
        ):
            raise ValueError(
                "MonthlyProfectionInterval profected_longitude must be "
                "in [0, 360)"
            )
        expected_sign, _, _ = sign_of(self.profected_longitude)
        if self.sign != expected_sign:
            raise ValueError(
                "MonthlyProfectionInterval sign must match "
                "profected_longitude"
            )
        if self.lord_of_month != DOMICILE_RULERS[self.sign]:
            raise ValueError(
                "MonthlyProfectionInterval lord_of_month must match "
                "the classical domicile ruler"
            )
        for name, value in (
            ("start_utc", self.start_utc),
            ("end_utc", self.end_utc),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(
                    f"MonthlyProfectionInterval {name} must be timezone-aware"
                )
            if value.utcoffset() != timedelta(0):
                raise ValueError(
                    f"MonthlyProfectionInterval {name} must be expressed in UTC"
                )
        if self.end_utc <= self.start_utc:
            raise ValueError(
                "MonthlyProfectionInterval end_utc must be after start_utc"
            )
        if (
            not math.isfinite(self.start_jd)
            or not math.isfinite(self.end_jd)
            or self.end_jd <= self.start_jd
        ):
            raise ValueError(
                "MonthlyProfectionInterval Julian boundaries must be finite "
                "and increasing"
            )
        if not math.isclose(
            self.start_jd,
            jd_from_datetime(self.start_utc),
            rel_tol=0.0,
            abs_tol=1e-9,
        ) or not math.isclose(
            self.end_jd,
            jd_from_datetime(self.end_utc),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "MonthlyProfectionInterval Julian boundaries must match "
                "the UTC boundaries"
            )
        if not isinstance(self.active, bool):
            raise ValueError(
                "MonthlyProfectionInterval active must be a boolean"
            )


@dataclass(frozen=True, slots=True)
class ProfectionChronology:
    """Typed receipt for one query-specific dated monthly projection.

    The sequence itself is the admitted twelve-sign monthly profection
    sequence. Dates are a declared computational projection: twelve equal
    elapsed-time partitions of the exact civil-anniversary year. This is not
    a claim to implement Valens' separate luminary-distance method.
    """

    age_years: int
    civil_timezone: str
    timezone_data_source: str
    timezone_data_version: str | None
    interval_policy: MonthlyProfectionIntervalPolicy
    ambiguous_time_policy: ProfectionAmbiguousTimePolicy | None
    ambiguous_time_resolution_applied: bool
    method: ProfectionChronologyMethod
    boundary_semantics: ProfectionIntervalBoundarySemantics
    leap_day_policy: LeapDayAnniversaryPolicy | None
    query_utc: datetime
    query_jd: float
    annual_start_utc: datetime
    annual_end_utc: datetime
    annual_start_jd: float
    annual_end_jd: float
    active_month_index: int
    intervals: tuple[MonthlyProfectionInterval, ...]

    def __post_init__(self) -> None:
        if type(self.age_years) is not int or self.age_years < 0:
            raise ValueError(
                "ProfectionChronology age_years must be a non-negative integer"
            )
        if (
            not isinstance(self.civil_timezone, str)
            or not self.civil_timezone
            or self.civil_timezone != self.civil_timezone.strip()
        ):
            raise ValueError(
                "ProfectionChronology civil_timezone must be a "
                "non-empty trimmed string"
            )
        if (
            not isinstance(self.timezone_data_source, str)
            or not self.timezone_data_source
            or self.timezone_data_source != self.timezone_data_source.strip()
        ):
            raise ValueError(
                "ProfectionChronology timezone_data_source must be a "
                "non-empty trimmed string"
            )
        if (
            self.timezone_data_version is not None
            and (
                not isinstance(self.timezone_data_version, str)
                or not self.timezone_data_version
                or self.timezone_data_version
                != self.timezone_data_version.strip()
            )
        ):
            raise ValueError(
                "ProfectionChronology timezone_data_version must be a "
                "non-empty trimmed string or None"
            )
        if self.timezone_data_source in {
            "stdlib_zoneinfo",
            "caller_supplied_tzinfo",
        }:
            if self.timezone_data_version is not None:
                raise ValueError(
                    "ProfectionChronology host or caller-supplied timezone "
                    "receipts cannot claim a bundled timezone-data version"
                )
        else:
            raise ValueError(
                "ProfectionChronology timezone_data_source must be "
                "'stdlib_zoneinfo' or 'caller_supplied_tzinfo'"
            )
        if not isinstance(
            self.interval_policy,
            MonthlyProfectionIntervalPolicy,
        ):
            raise ValueError(
                "ProfectionChronology interval_policy must be a "
                "MonthlyProfectionIntervalPolicy"
            )
        if (
            self.ambiguous_time_policy is not None
            and not isinstance(
                self.ambiguous_time_policy,
                ProfectionAmbiguousTimePolicy,
            )
        ):
            raise ValueError(
                "ProfectionChronology ambiguous_time_policy must be a "
                "ProfectionAmbiguousTimePolicy or None"
            )
        if not isinstance(self.ambiguous_time_resolution_applied, bool):
            raise ValueError(
                "ProfectionChronology ambiguous_time_resolution_applied "
                "must be a boolean"
            )
        if (
            self.ambiguous_time_resolution_applied
            and self.ambiguous_time_policy is None
        ):
            raise ValueError(
                "ProfectionChronology cannot resolve an ambiguous anniversary "
                "without an explicit policy"
            )
        if self.method is not ProfectionChronologyMethod.COMPUTATIONAL_PROJECTION:
            raise ValueError(
                "ProfectionChronology method must be computational_projection"
            )
        if (
            self.boundary_semantics
            is not ProfectionIntervalBoundarySemantics.START_INCLUSIVE_END_EXCLUSIVE
        ):
            raise ValueError(
                "ProfectionChronology boundary_semantics must be "
                "start_inclusive_end_exclusive"
            )
        if (
            self.leap_day_policy is not None
            and not isinstance(
                self.leap_day_policy,
                LeapDayAnniversaryPolicy,
            )
        ):
            raise ValueError(
                "ProfectionChronology leap_day_policy must be a "
                "LeapDayAnniversaryPolicy or None"
            )
        for name, value in (
            ("query_utc", self.query_utc),
            ("annual_start_utc", self.annual_start_utc),
            ("annual_end_utc", self.annual_end_utc),
        ):
            if (
                value.tzinfo is None
                or value.utcoffset() is None
                or value.utcoffset() != timedelta(0)
            ):
                raise ValueError(
                    f"ProfectionChronology {name} must be expressed in UTC"
                )
        if not self.annual_start_utc <= self.query_utc < self.annual_end_utc:
            raise ValueError(
                "ProfectionChronology query_utc must belong to the "
                "civil-anniversary year"
            )
        for name, value, expected in (
            ("query_jd", self.query_jd, self.query_utc),
            ("annual_start_jd", self.annual_start_jd, self.annual_start_utc),
            ("annual_end_jd", self.annual_end_jd, self.annual_end_utc),
        ):
            if not math.isfinite(value) or not math.isclose(
                value,
                jd_from_datetime(expected),
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                raise ValueError(
                    f"ProfectionChronology {name} must match its UTC instant"
                )
        if type(self.active_month_index) is not int or not (
            0 <= self.active_month_index <= 11
        ):
            raise ValueError(
                "ProfectionChronology active_month_index must be in [0, 11]"
            )
        if (
            len(self.intervals) != 12
            or any(
                not isinstance(item, MonthlyProfectionInterval)
                for item in self.intervals
            )
        ):
            raise ValueError(
                "ProfectionChronology intervals must contain exactly twelve "
                "MonthlyProfectionInterval values"
            )
        if tuple(item.month_index for item in self.intervals) != tuple(range(12)):
            raise ValueError(
                "ProfectionChronology intervals must be ordered Month 0 "
                "through Month 11"
            )
        if (
            self.intervals[0].start_utc != self.annual_start_utc
            or self.intervals[-1].end_utc != self.annual_end_utc
        ):
            raise ValueError(
                "ProfectionChronology intervals must cover the exact "
                "civil-anniversary year"
            )
        if any(
            left.end_utc != right.start_utc
            for left, right in zip(self.intervals, self.intervals[1:])
        ):
            raise ValueError(
                "ProfectionChronology intervals must be contiguous"
            )
        if (
            self.intervals[0].start_jd != self.annual_start_jd
            or self.intervals[-1].end_jd != self.annual_end_jd
            or any(
                left.end_jd != right.start_jd
                for left, right in zip(self.intervals, self.intervals[1:])
            )
        ):
            raise ValueError(
                "ProfectionChronology Julian intervals must be contiguous "
                "and cover the exact civil-anniversary year"
            )
        durations = tuple(
            item.end_utc - item.start_utc for item in self.intervals
        )
        if max(durations) - min(durations) > timedelta(microseconds=1):
            raise ValueError(
                "ProfectionChronology interval durations must differ by no "
                "more than one microsecond"
            )
        if any(
            not math.isclose(
                right.profected_longitude,
                (left.profected_longitude + 30.0) % 360.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            for left, right in zip(self.intervals, self.intervals[1:])
        ):
            raise ValueError(
                "ProfectionChronology intervals must advance one sign in order"
            )
        active_indices = tuple(
            item.month_index for item in self.intervals if item.active
        )
        if active_indices != (self.active_month_index,):
            raise ValueError(
                "ProfectionChronology must have exactly one active interval "
                "matching active_month_index"
            )
        active = self.intervals[self.active_month_index]
        if not active.start_utc <= self.query_utc < active.end_utc:
            raise ValueError(
                "ProfectionChronology active interval must contain query_utc"
            )
        if not active.start_jd <= self.query_jd < active.end_jd:
            raise ValueError(
                "ProfectionChronology active Julian interval must contain "
                "query_jd"
            )


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
        "frozen": ["age_years", "profected_house", "profected_asc_lon", "profected_sign", "lord_of_year", "activated_planets", "monthly_lords", "age_basis", "leap_day_policy", "activation_truth", "chronology"],
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
    chronology:          ProfectionChronology | None = None

    def __post_init__(self) -> None:
        if type(self.age_years) is not int or self.age_years < 0:
            raise ValueError(
                "ProfectionResult age_years must be a non-negative integer"
            )
        expected_house = (self.age_years % 12) + 1
        if (
            type(self.profected_house) is not int
            or self.profected_house != expected_house
        ):
            raise ValueError(
                "ProfectionResult profected_house must match age_years"
            )
        if (
            not math.isfinite(self.profected_asc_lon)
            or not 0.0 <= self.profected_asc_lon < 360.0
        ):
            raise ValueError(
                "ProfectionResult profected_asc_lon must be in [0, 360)"
            )
        expected_sign, _, _ = sign_of(self.profected_asc_lon)
        if self.profected_sign != expected_sign:
            raise ValueError(
                "ProfectionResult profected_sign must match "
                "profected_asc_lon"
            )
        if self.lord_of_year != DOMICILE_RULERS[self.profected_sign]:
            raise ValueError(
                "ProfectionResult lord_of_year must match profected_sign"
            )
        if (
            not isinstance(self.activated_planets, list)
            or any(
                not isinstance(name, str)
                or not name
                or name != name.strip()
                for name in self.activated_planets
            )
            or len(self.activated_planets) != len(set(self.activated_planets))
        ):
            raise ValueError(
                "ProfectionResult activated_planets must be a list of unique "
                "non-empty trimmed names"
            )
        if (
            not isinstance(self.monthly_lords, list)
            or self.monthly_lords
            != _monthly_lord_list(self.profected_asc_lon)
        ):
            raise ValueError(
                "ProfectionResult monthly_lords must be the exact ordered "
                "twelve-sign ruler sequence"
            )
        if self.age_basis not in {
            "explicit_completed_age",
            "civil_anniversary",
        }:
            raise ValueError(
                "ProfectionResult age_basis must be "
                "'explicit_completed_age' or 'civil_anniversary'"
            )
        if (
            self.leap_day_policy is not None
            and not isinstance(
                self.leap_day_policy,
                LeapDayAnniversaryPolicy,
            )
        ):
            raise ValueError(
                "ProfectionResult leap_day_policy must be a "
                "LeapDayAnniversaryPolicy or None"
            )
        if self.activation_truth is None:
            raise ValueError(
                "ProfectionResult must preserve activation_truth"
            )
        if not isinstance(
            self.activation_truth,
            ProfectionActivationTruth,
        ):
            raise ValueError(
                "ProfectionResult activation_truth must be a "
                "ProfectionActivationTruth"
            )
        if (
            self.age_basis == "civil_anniversary"
            and self.chronology is None
        ):
            raise ValueError(
                "ProfectionResult civil-anniversary results must preserve "
                "chronology"
            )
        if (
            self.age_basis == "explicit_completed_age"
            and (
                self.chronology is not None
                or self.leap_day_policy is not None
            )
        ):
            raise ValueError(
                "ProfectionResult explicit-age results cannot carry civil "
                "chronology or leap-day policy"
            )
        if self.chronology is not None:
            if not isinstance(self.chronology, ProfectionChronology):
                raise ValueError(
                    "ProfectionResult chronology must be a "
                    "ProfectionChronology or None"
                )
            if self.chronology.age_years != self.age_years:
                raise ValueError(
                    "ProfectionResult chronology age must match age_years"
                )
            if self.age_basis != "civil_anniversary":
                raise ValueError(
                    "ProfectionResult chronology requires "
                    "age_basis='civil_anniversary'"
                )
            if self.leap_day_policy is not self.chronology.leap_day_policy:
                raise ValueError(
                    "ProfectionResult chronology leap-day policy must match "
                    "leap_day_policy"
                )
            if [
                item.lord_of_month for item in self.chronology.intervals
            ] != self.monthly_lords:
                raise ValueError(
                    "ProfectionResult monthly_lords must match chronology"
                )
            first_longitude = self.chronology.intervals[0].profected_longitude
            if not math.isclose(
                first_longitude,
                self.profected_asc_lon,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    "ProfectionResult chronology must begin at "
                    "profected_asc_lon"
                )
        if not math.isclose(
            self.activation_truth.profected_asc_lon,
            self.profected_asc_lon,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
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


def _validated_natal_asc(natal_asc: float) -> float:
    if isinstance(natal_asc, bool):
        raise TypeError("natal_asc must be a finite number")
    try:
        finite = math.isfinite(natal_asc)
    except TypeError as exc:
        raise TypeError("natal_asc must be a finite number") from exc
    if not finite:
        raise ValueError("natal_asc must be finite")
    return natal_asc % 360.0


def _validated_age_years(age_years: int) -> int:
    if type(age_years) is not int or age_years < 0:
        raise ValueError("age_years must be a non-negative integer")
    return age_years


def _validated_month_index(month_index: int) -> int:
    if type(month_index) is not int or not 0 <= month_index <= 11:
        raise ValueError("month_index must be an integer in [0, 11]")
    return month_index


def _resolved_leap_day_policy(
    leap_day_policy: LeapDayAnniversaryPolicy | str | None,
) -> LeapDayAnniversaryPolicy | None:
    if leap_day_policy is None:
        return None
    try:
        return LeapDayAnniversaryPolicy(leap_day_policy)
    except ValueError as exc:
        raise ValueError(
            "leap_day_policy must be 'february_28' or 'march_1'"
        ) from exc


def _resolved_interval_policy(
    interval_policy: MonthlyProfectionIntervalPolicy | str,
) -> MonthlyProfectionIntervalPolicy:
    try:
        return MonthlyProfectionIntervalPolicy(interval_policy)
    except ValueError as exc:
        raise ValueError(
            "interval_policy must be "
            "'equal_twelfths_of_civil_anniversary_year'"
        ) from exc


def _resolved_ambiguous_time_policy(
    ambiguous_time_policy: ProfectionAmbiguousTimePolicy | str | None,
) -> ProfectionAmbiguousTimePolicy | None:
    if ambiguous_time_policy is None:
        return None
    try:
        return ProfectionAmbiguousTimePolicy(ambiguous_time_policy)
    except ValueError as exc:
        raise ValueError(
            "ambiguous_time_policy must be 'earlier_occurrence' or "
            "'later_occurrence'"
        ) from exc


@lru_cache(maxsize=128)
def _stdlib_iana_timezone(key: str) -> ZoneInfo:
    if (
        len(key) > 255
        or key.startswith("/")
        or "\\" in key
        or any(part in {"", ".", ".."} for part in key.split("/"))
        or any(
            not (
                character.isascii()
                and (
                    character.isalnum()
                    or character in "._+-/"
                )
            )
            for character in key
        )
    ):
        raise ValueError(f"invalid IANA timezone key: {key!r}")
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            "civil_timezone is not a recognized IANA timezone or is not "
            f"available in the host database: {key!r}"
        ) from exc


def _resolved_civil_timezone(
    natal_dt: datetime,
    civil_timezone: str | None,
) -> tuple[tzinfo, str, str, str | None]:
    if civil_timezone is None:
        assert natal_dt.tzinfo is not None
        zone = natal_dt.tzinfo
        identifier = getattr(zone, "key", None) or str(zone)
        return zone, identifier, "caller_supplied_tzinfo", None
    if (
        not isinstance(civil_timezone, str)
        or not civil_timezone
        or civil_timezone != civil_timezone.strip()
    ):
        raise ValueError(
            "civil_timezone must be a non-empty trimmed IANA timezone"
        )
    zone = _stdlib_iana_timezone(civil_timezone)
    return zone, zone.key, "stdlib_zoneinfo", None


def _civil_anniversary(
    natal_local: datetime,
    year: int,
    leap_day_policy: LeapDayAnniversaryPolicy | None,
    ambiguous_time_policy: ProfectionAmbiguousTimePolicy | None,
    civil_timezone: str,
) -> tuple[datetime, bool]:
    month = natal_local.month
    day = natal_local.day
    try:
        naive = natal_local.replace(
            year=year,
            tzinfo=None,
        )
    except ValueError:
        assert month == 2 and day == 29 and leap_day_policy is not None
        if leap_day_policy is LeapDayAnniversaryPolicy.FEBRUARY_28:
            month, day = 2, 28
        else:
            month, day = 3, 1
        naive = natal_local.replace(
            year=year,
            month=month,
            day=day,
            tzinfo=None,
        )

    assert natal_local.tzinfo is not None
    valid_candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(
            tzinfo=natal_local.tzinfo,
            fold=fold,
        )
        round_trip = candidate.astimezone(timezone.utc).astimezone(
            natal_local.tzinfo
        )
        if round_trip.replace(tzinfo=None) == naive:
            valid_candidates.append(candidate)
    if not valid_candidates:
        raise ValueError(
            "civil anniversary falls in a nonexistent local time under "
            f"{civil_timezone!r}; Moira does not silently shift DST gaps"
        )
    candidates_by_instant = {
        candidate.astimezone(timezone.utc): candidate
        for candidate in valid_candidates
    }
    if len(candidates_by_instant) == 1:
        return next(iter(candidates_by_instant.values())), False
    if ambiguous_time_policy is None:
        raise ValueError(
            "civil anniversary falls in an ambiguous local time under "
            f"{civil_timezone!r}; ambiguous_time_policy is required"
        )
    ordered = sorted(candidates_by_instant.items())
    selected = (
        ordered[0][1]
        if ambiguous_time_policy
        is ProfectionAmbiguousTimePolicy.EARLIER_OCCURRENCE
        else ordered[-1][1]
    )
    return selected, True


def _civil_anniversary_for_age(
    natal_local: datetime,
    age_years: int,
    leap_day_policy: LeapDayAnniversaryPolicy | None,
    ambiguous_time_policy: ProfectionAmbiguousTimePolicy | None,
    civil_timezone: str,
) -> tuple[datetime, bool]:
    """Resolve one completed-age anchor, preserving the exact birth instant."""

    if age_years == 0:
        return natal_local, False
    try:
        year = natal_local.year + age_years
    except OverflowError as exc:
        raise ValueError(
            "civil anniversary falls outside Python datetime range"
        ) from exc
    if not 1 <= year <= 9999:
        raise ValueError(
            "civil anniversary falls outside Python datetime range"
        )
    return _civil_anniversary(
        natal_local,
        year,
        leap_day_policy,
        ambiguous_time_policy,
        civil_timezone,
    )


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
    normalized_asc = _validated_natal_asc(natal_asc)
    resolved_age = _validated_age_years(age_years)
    profected_asc_lon = (normalized_asc + resolved_age * 30.0) % 360.0
    profected_sign, _, _ = sign_of(profected_asc_lon)
    lord_of_year = DOMICILE_RULERS[profected_sign]
    profected_house = (resolved_age % 12) + 1

    activation_truth = profection_activation_truth(
        profected_asc_lon,
        natal_positions,
        activation_orb,
    )
    activated = list(activation_truth.activated_planets)

    monthly_lords = _monthly_lord_list(profected_asc_lon)

    return ProfectionResult(
        age_years=resolved_age,
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
    normalized_asc = _validated_natal_asc(natal_asc)
    resolved_age = _validated_age_years(age_years)
    resolved_month = _validated_month_index(month_index)
    annual_lon = (normalized_asc + resolved_age * 30.0) % 360.0
    monthly_lon = (annual_lon + resolved_month * 30.0) % 360.0
    sign, _, _ = sign_of(monthly_lon)
    lord = DOMICILE_RULERS[sign]
    return monthly_lon, sign, lord


def profection_chronology(
    natal_asc: float,
    natal_dt: datetime,
    current_dt: datetime,
    *,
    civil_timezone: str | None = None,
    leap_day_policy: LeapDayAnniversaryPolicy | str | None = None,
    ambiguous_time_policy: ProfectionAmbiguousTimePolicy | str | None = None,
    interval_policy: MonthlyProfectionIntervalPolicy | str = (
        MonthlyProfectionIntervalPolicy.EQUAL_TWELFTHS_OF_CIVIL_ANNIVERSARY_YEAR
    ),
) -> ProfectionChronology:
    """Project the twelve-sign sequence onto one civil-anniversary year.

    The annual anchors preserve the natal local wall time in the selected
    civil timezone. The elapsed UTC duration between those anchors is divided
    into twelve contiguous intervals whose lengths differ by no more than one
    microsecond. Every boundary is start-inclusive and end-exclusive.

    This is an explicit computational projection for product chronology. It
    does not implement or claim equivalence to Valens' luminary-distance
    method for locating the month.
    """

    normalized_asc = _validated_natal_asc(natal_asc)
    for label, value in (("natal_dt", natal_dt), ("current_dt", current_dt)):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{label} must be timezone-aware")
    natal_utc = natal_dt.astimezone(timezone.utc)
    current_utc = current_dt.astimezone(timezone.utc)
    if current_utc < natal_utc:
        raise ValueError("current_dt must not be before natal_dt")

    resolved_leap_policy = _resolved_leap_day_policy(leap_day_policy)
    resolved_ambiguous_policy = _resolved_ambiguous_time_policy(
        ambiguous_time_policy
    )
    (
        zone,
        zone_identifier,
        timezone_data_source,
        timezone_data_version,
    ) = _resolved_civil_timezone(natal_dt, civil_timezone)
    resolved_interval_policy = _resolved_interval_policy(interval_policy)
    natal_local = natal_utc.astimezone(zone)
    current_local = current_utc.astimezone(zone)
    is_leap_day_nativity = (
        natal_local.month == 2 and natal_local.day == 29
    )
    if is_leap_day_nativity and resolved_leap_policy is None:
        raise ValueError(
            "leap_day_policy is required for a February 29 nativity"
        )

    candidate_age = current_local.year - natal_local.year
    candidate_anniversary, candidate_ambiguous = _civil_anniversary_for_age(
        natal_local,
        candidate_age,
        resolved_leap_policy,
        resolved_ambiguous_policy,
        zone_identifier,
    )
    age_years = candidate_age - int(
        current_utc < candidate_anniversary.astimezone(timezone.utc)
    )
    if age_years < 0:
        raise ValueError("current_dt must not be before natal_dt")

    annual_start_local, start_ambiguous = _civil_anniversary_for_age(
        natal_local,
        age_years,
        resolved_leap_policy,
        resolved_ambiguous_policy,
        zone_identifier,
    )
    annual_end_local, end_ambiguous = _civil_anniversary_for_age(
        natal_local,
        age_years + 1,
        resolved_leap_policy,
        resolved_ambiguous_policy,
        zone_identifier,
    )
    annual_start_utc = annual_start_local.astimezone(timezone.utc)
    annual_end_utc = annual_end_local.astimezone(timezone.utc)
    if not annual_start_utc <= current_utc < annual_end_utc:
        raise RuntimeError(
            "resolved civil-anniversary year does not contain current_dt"
        )

    elapsed = annual_end_utc - annual_start_utc
    total_microseconds = (
        (elapsed.days * 86_400 + elapsed.seconds) * 1_000_000
        + elapsed.microseconds
    )
    offsets = tuple(
        total_microseconds * index // 12
        for index in range(13)
    )
    boundaries = tuple(
        annual_start_utc + timedelta(microseconds=offset)
        for offset in offsets
    )
    active_month_index = next(
        index
        for index in range(12)
        if boundaries[index] <= current_utc < boundaries[index + 1]
    )
    boundary_jds = tuple(jd_from_datetime(value) for value in boundaries)
    interval_values: list[MonthlyProfectionInterval] = []
    for index in range(12):
        longitude, sign, lord = monthly_profection(
            normalized_asc,
            age_years,
            index,
        )
        interval_values.append(
            MonthlyProfectionInterval(
                month_index=index,
                profected_longitude=longitude,
                sign=sign,
                lord_of_month=lord,
                start_utc=boundaries[index],
                end_utc=boundaries[index + 1],
                start_jd=boundary_jds[index],
                end_jd=boundary_jds[index + 1],
                active=index == active_month_index,
            )
        )

    return ProfectionChronology(
        age_years=age_years,
        civil_timezone=zone_identifier,
        timezone_data_source=timezone_data_source,
        timezone_data_version=timezone_data_version,
        interval_policy=resolved_interval_policy,
        ambiguous_time_policy=resolved_ambiguous_policy,
        ambiguous_time_resolution_applied=(
            candidate_ambiguous
            or start_ambiguous
            or end_ambiguous
        ),
        method=ProfectionChronologyMethod.COMPUTATIONAL_PROJECTION,
        boundary_semantics=(
            ProfectionIntervalBoundarySemantics.START_INCLUSIVE_END_EXCLUSIVE
        ),
        leap_day_policy=resolved_leap_policy,
        query_utc=current_utc,
        query_jd=jd_from_datetime(current_utc),
        annual_start_utc=annual_start_utc,
        annual_end_utc=annual_end_utc,
        annual_start_jd=boundary_jds[0],
        annual_end_jd=boundary_jds[-1],
        active_month_index=active_month_index,
        intervals=tuple(interval_values),
    )


def profection_schedule(
    natal_asc: float,
    natal_dt: datetime,
    current_dt: datetime,
    natal_positions: dict[str, float] | None = None,
    *,
    civil_timezone: str | None = None,
    leap_day_policy: LeapDayAnniversaryPolicy | str | None = None,
    ambiguous_time_policy: ProfectionAmbiguousTimePolicy | str | None = None,
    interval_policy: MonthlyProfectionIntervalPolicy | str = (
        MonthlyProfectionIntervalPolicy.EQUAL_TWELFTHS_OF_CIVIL_ANNIVERSARY_YEAR
    ),
    activation_orb: float = 5.0,
) -> ProfectionResult:
    """
    Compute the current profection from civil anniversary chronology.

    Completed age advances on the anniversary of the natal local date and time,
    not after a fixed 365.25-day quotient. Both datetimes must be timezone-aware.
    ``civil_timezone`` may select the authoritative IANA zone when transport has
    normalized the supplied instants to UTC. A February 29 nativity requires an
    explicit anniversary policy.

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
    civil_timezone : str or None
        Authoritative IANA civil timezone for anniversary construction. If
        omitted, the timezone attached to ``natal_dt`` is retained.
    leap_day_policy : LeapDayAnniversaryPolicy, str, or None
        Explicit February 29 anniversary policy when required.
    interval_policy : MonthlyProfectionIntervalPolicy or str
        Dated monthly projection policy.
    activation_orb : float
        Orb in degrees for activated-planet detection (default 5.0°).

    Returns
    -------
    ProfectionResult
    """
    chronology = profection_chronology(
        natal_asc,
        natal_dt,
        current_dt,
        civil_timezone=civil_timezone,
        leap_day_policy=leap_day_policy,
        ambiguous_time_policy=ambiguous_time_policy,
        interval_policy=interval_policy,
    )

    result = annual_profection(
        natal_asc,
        chronology.age_years,
        natal_positions,
        activation_orb=activation_orb,
    )
    return replace(
        result,
        age_basis="civil_anniversary",
        leap_day_policy=chronology.leap_day_policy,
        chronology=chronology,
    )

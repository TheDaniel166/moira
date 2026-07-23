"""
Moira — babylonian.py
Babylonian Chronology Oracle: governs historical calendar conversion and
coordinate support for ancient astronomical validation.

Purpose: provides a small, explicit historical-calendar substrate for Babylonian
planetary validation rows without entangling that work with sothic.py or the
core Julian/Gregorian conversion module.

Boundary: owns Babylon city coordinates, Julian-calendar civil-date support for
ancient source dates, Parker/Dubberstein month-start conversion for Babylonian
calendar dates, and Babylonian Mercury reference rows for validation. Delegates
modern calendar conversion to julian.py and does not own ruler-name/regnal-year
reconstruction or public facade exposure.

Import-time side effects: None

External dependency assumptions:
    - No external kernels or databases required
    - Pure computational module for historical calendar work

Public surface / exports:
    BABYLON_LATITUDE_DEG      — historical city latitude
    BABYLON_LONGITUDE_DEG     — historical city longitude
    BabylonianCivilDay        — vessel for Julian-calendar source dates
    BabylonianCalendarDate    — vessel for Babylonian calendar dates
    babylonian_calendar_to_civil_day() — calendar conversion
    babylonian_month_start()  — Parker/Dubberstein month start lookup
    babylonian_planetary_reference()   — access to historical oracle rows
    BABYLONIAN_MERCURY_REFERENCES      — Mercury validation data
    BABYLONIAN_VENUS_REFERENCES        — Venus validation data
    (Full API surface documented in __all__)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from .constants import Body
from .heliacal import HeliacalEventKind
from .julian import CalendarDateTime, calendar_datetime_from_jd, julian_day

__all__ = [
    "BABYLON_LATITUDE_DEG",
    "BABYLON_LONGITUDE_DEG",
    "BabylonianChronologyAuthority",
    "HistoricalCalendar",
    "BabylonianObservationClass",
    "BabylonianAdmissionStrength",
    "BabylonianHoldoutReason",
    "BabylonianValidationStatus",
    "BabylonianCivilDay",
    "BabylonianCivilWindow",
    "BabylonianCalendarDate",
    "BabylonianSourceQuality",
    "ChronologyConfidence",
    "BabylonianHistoricalPhenomenon",
    "BabylonianPlanetaryVisibilityEvidence",
    "BabylonianPlanetaryReference",
    "BABYLONIAN_MERCURY_REFERENCES",
    "BABYLONIAN_VENUS_REFERENCES",
    "BABYLONIAN_VENUS_AMMISADUQA_PHENOMENA",
    "admitted_babylonian_mercury_references",
    "admitted_babylonian_venus_references",
    "holdout_babylonian_mercury_references",
    "holdout_babylonian_venus_references",
    "babylonian_venus_ammisaduqa_phenomena",
    "babylonian_calendar_to_civil_day",
    "babylonian_month_length",
    "babylonian_month_start",
    "babylonian_planetary_reference",
    "julian_calendar_day_from_jd",
    "julian_calendar_day_to_jd",
]


BABYLON_LATITUDE_DEG = 32.55
BABYLON_LONGITUDE_DEG = 44.42

_BABYLONIAN_CHRONOLOGY_PATH = (
    Path(__file__).resolve().parent / "data" / "babylonian_chronology_pd_1971.dat"
)
_INTERCALARY_MONTH_CODES = frozenset({"6b", "12b"})


class BabylonianChronologyAuthority(StrEnum):
    """Vessel: Registry of authoritative chronology regimes."""
    DE_JONG_2021 = "de_jong_2021"
    DE_JONG_FOERTMEYER_2010 = "de_jong_foertmeyer_2010"
    PARKER_DUBBERSTEIN_1956 = "parker_dubberstein_1956"


class HistoricalCalendar(StrEnum):
    """Vessel: Registry of supported historical calendar systems."""
    JULIAN = "julian"


class BabylonianObservationClass(StrEnum):
    """Vessel: Categorization of Babylonian observation types."""
    OBSERVED = "observed"
    IDEAL = "ideal"
    OBSERVED_AND_IDEAL = "observed_and_ideal"
    EXPECTED = "expected"
    OMITTED = "omitted"
    TERMINUS_SUPPORT = "terminus_support"


class BabylonianAdmissionStrength(StrEnum):
    """Vessel: Qualitative strength of oracle admission."""
    STRONG = "strong"
    BOUNDED = "bounded"
    WEAK = "weak"
    HOLDOUT = "holdout"


class BabylonianValidationStatus(StrEnum):
    """Vessel: Admission lifecycle state for validation rows."""
    ADMITTED = "admitted"
    CANDIDATE = "candidate"


class BabylonianHoldoutReason(StrEnum):
    """Vessel: Rationale for excluding a candidate validation row."""
    EXPECTED_ONLY_SOURCE = "expected_only_source"
    OMITTED_PHASE_SOURCE = "omitted_phase_source"
    TERMINUS_SUPPORT_ONLY = "terminus_support_only"
    SOURCE_SOLVER_MISMATCH = "source_solver_mismatch"
    VISIBILITY_DOCTRINE_NOT_IMPLEMENTED = "visibility_doctrine_not_implemented"
    MIXED = "mixed"


class BabylonianSourceQuality(StrEnum):
    """Vessel: Reliability categorization for historical source material."""
    RELIABLE = "reliable"
    RELATIVELY_CONSISTENT = "relatively_consistent"
    QUESTIONED = "questioned"


class ChronologyConfidence(StrEnum):
    """Vessel: Qualitative confidence in the underlying chronology."""
    DISPUTED = "disputed"
    SOURCE_TABLE_AVAILABLE = "source_table_available"


def julian_calendar_day_to_jd(year: int, month: int, day: int, hour: float = 0.0) -> float:
    """
    Convert a civil Julian-calendar date to JD.

    This is intentionally separate from ``moira.julian.julian_day()``, which
    governs the Gregorian-correction path used elsewhere in the engine. Ancient
    historical sources normally publish absolute dates in the Julian civil
    calendar, so Babylonian validation rows need an explicit Julian-calendar
    conversion surface of their own.
    """
    if month <= 2:
        year -= 1
        month += 12

    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        - 1524.5
        + hour / 24.0
    )


@dataclass(frozen=True, slots=True)
class BabylonianCivilDay:
    """Vessel: Representation of a Julian-calendar civil date for ancient sources."""
    year: int
    month: int
    day: int
    calendar: HistoricalCalendar = HistoricalCalendar.JULIAN

    def __post_init__(self) -> None:
        if self.calendar is not HistoricalCalendar.JULIAN:
            raise ValueError("BabylonianCivilDay currently supports only Julian-calendar source dates")
        if not 1 <= self.month <= 12:
            raise ValueError("BabylonianCivilDay month must be between 1 and 12")
        if not 1 <= self.day <= 31:
            raise ValueError("BabylonianCivilDay day must be between 1 and 31")

    @property
    def jd(self) -> float:
        return julian_calendar_day_to_jd(self.year, self.month, self.day, 0.0)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        """Return the equivalent instant expressed in Moira's Gregorian calendar."""
        return calendar_datetime_from_jd(self.jd)

    @property
    def date_tuple(self) -> tuple[int, int, int]:
        """Return the source's Julian-calendar civil label."""
        return (self.year, self.month, self.day)


def julian_calendar_day_from_jd(jd: float) -> BabylonianCivilDay:
    """Convert a JD instant to its proleptic Julian-calendar civil day."""

    if not math.isfinite(jd):
        raise ValueError("jd must be finite")

    shifted = jd + 0.5
    z = math.floor(shifted)
    f = shifted - z
    b = z + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day = math.floor(b - d - math.floor(30.6001 * e) + f)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    return BabylonianCivilDay(year, month, day)


@dataclass(frozen=True, slots=True)
class BabylonianCivilWindow:
    """Vessel: Temporal window spanning multiple Julian-calendar civil days."""
    start: BabylonianCivilDay
    end: BabylonianCivilDay
    authority: BabylonianChronologyAuthority
    note: str

    def __post_init__(self) -> None:
        if self.end.jd < self.start.jd:
            raise ValueError("BabylonianCivilWindow end must not precede start")

    def contains_calendar_date(self, date: CalendarDateTime) -> bool:
        """Test a Moira Gregorian calendar result against this absolute window."""

        jd = julian_day(date.year, date.month, date.day, 0.0)
        return self.start.jd <= jd < self.end.jd + 1.0


def _normalize_month_code(month: int | str) -> str:
    if isinstance(month, int):
        if not 1 <= month <= 12:
            raise ValueError("Babylonian month integers must be between 1 and 12")
        return str(month)

    normalized = month.strip().lower()
    if normalized.endswith("ii"):
        normalized = normalized.replace("ii", "b")
    if normalized not in {*(str(value) for value in range(1, 13)), *_INTERCALARY_MONTH_CODES}:
        raise ValueError(f"Unsupported Babylonian month code: {month!r}")
    return normalized


@lru_cache(maxsize=1)
def _load_parker_dubberstein_rows() -> tuple[tuple[int, str, BabylonianCivilDay], ...]:
    rows: list[tuple[int, str, BabylonianCivilDay]] = []
    for raw in _BABYLONIAN_CHRONOLOGY_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        year_text, month_code, civil_year_text, civil_month_text, civil_day_text = parts[:5]
        rows.append(
            (
                int(year_text),
                month_code.lower(),
                BabylonianCivilDay(
                    int(civil_year_text),
                    int(civil_month_text),
                    int(civil_day_text),
                ),
            )
        )
    return tuple(rows)


@lru_cache(maxsize=1)
def _parker_dubberstein_lookup() -> dict[tuple[int, str], BabylonianCivilDay]:
    return {
        (year, month_code): civil_day
        for year, month_code, civil_day in _load_parker_dubberstein_rows()
    }


def babylonian_month_start(year: int, month: int | str) -> BabylonianCivilDay:
    key = (year, _normalize_month_code(month))
    try:
        return _parker_dubberstein_lookup()[key]
    except KeyError as exc:
        raise KeyError(f"No Parker/Dubberstein Babylonian month start for year={year}, month={month!r}") from exc


def babylonian_month_length(year: int, month: int | str) -> int:
    month_code = _normalize_month_code(month)
    rows = _load_parker_dubberstein_rows()
    for index, (row_year, row_month, civil_day) in enumerate(rows):
        if row_year != year or row_month != month_code:
            continue
        if index + 1 >= len(rows):
            raise KeyError(
                f"No following month available to determine Babylonian month length for year={year}, month={month!r}"
            )
        return int(round(rows[index + 1][2].jd - civil_day.jd))
    raise KeyError(f"No Parker/Dubberstein Babylonian month length for year={year}, month={month!r}")


@dataclass(frozen=True, slots=True)
class BabylonianCalendarDate:
    """Vessel: Representation of a date in the Babylonian lunisolar calendar."""
    year: int
    month: str | int
    day: int
    authority: BabylonianChronologyAuthority = BabylonianChronologyAuthority.PARKER_DUBBERSTEIN_1956

    def __post_init__(self) -> None:
        if self.authority is not BabylonianChronologyAuthority.PARKER_DUBBERSTEIN_1956:
            raise ValueError("BabylonianCalendarDate currently supports Parker/Dubberstein chronology only")
        month_length = babylonian_month_length(self.year, self.month)
        if not 1 <= self.day <= month_length:
            raise ValueError(
                f"BabylonianCalendarDate day must be between 1 and {month_length} for year={self.year}, month={self.month!r}"
            )

    @property
    def month_code(self) -> str:
        return _normalize_month_code(self.month)

    @property
    def civil_day(self) -> BabylonianCivilDay:
        return babylonian_calendar_to_civil_day(self.year, self.month_code, self.day)


@dataclass(frozen=True, slots=True)
class BabylonianHistoricalPhenomenon:
    """Vessel: Raw historical phenomenon record from ancient sources."""
    id: str
    body: str
    event_kind: HeliacalEventKind
    source_family: str
    epoch_label: str
    chronology_confidence: ChronologyConfidence
    source_quality: BabylonianSourceQuality
    source_year: int
    babylonian_month: str
    babylonian_day: str
    source: str
    source_url: str
    note: str

    def __post_init__(self) -> None:
        if self.body not in {Body.MERCURY, Body.VENUS}:
            raise ValueError("BabylonianHistoricalPhenomenon currently supports Mercury and Venus only")
        if not self.epoch_label:
            raise ValueError("BabylonianHistoricalPhenomenon epoch_label must be non-empty")
        if not self.babylonian_month:
            raise ValueError("BabylonianHistoricalPhenomenon babylonian_month must be non-empty")
        if not self.babylonian_day:
            raise ValueError("BabylonianHistoricalPhenomenon babylonian_day must be non-empty")


def babylonian_calendar_to_civil_day(year: int, month: int | str, day: int) -> BabylonianCivilDay:
    month_code = _normalize_month_code(month)
    month_start = babylonian_month_start(year, month_code)
    month_length = babylonian_month_length(year, month_code)
    if not 1 <= day <= month_length:
        raise ValueError(
            f"Babylonian day must be between 1 and {month_length} for year={year}, month={month!r}"
        )
    jd = month_start.jd + (day - 1)
    return julian_calendar_day_from_jd(jd)


@dataclass(frozen=True, slots=True)
class BabylonianPlanetaryVisibilityEvidence:
    """Source-published physical visibility quantities for one planetary row."""

    extinction_coefficient_mag_per_airmass: float
    refracted_elevation_deg: float
    geometric_arcus_visionis_deg: float
    nominal_date_delta_days: int
    source_fit_bracketed: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.extinction_coefficient_mag_per_airmass):
            raise ValueError("Visibility evidence extinction coefficient must be finite")
        if self.extinction_coefficient_mag_per_airmass < 0.0:
            raise ValueError("Visibility evidence extinction coefficient must be non-negative")
        if not math.isfinite(self.refracted_elevation_deg):
            raise ValueError("Visibility evidence refracted elevation must be finite")
        if not math.isfinite(self.geometric_arcus_visionis_deg):
            raise ValueError("Visibility evidence geometric arcus visionis must be finite")


@dataclass(frozen=True, slots=True)
class BabylonianPlanetaryReference:
    """Vessel: Refined planetary validation row for oracle comparison."""
    id: str
    body: str
    event_kind: HeliacalEventKind
    latitude_deg: float
    longitude_deg: float
    observation_class: BabylonianObservationClass
    admission_strength: BabylonianAdmissionStrength
    validation_status: BabylonianValidationStatus
    holdout_reason: BabylonianHoldoutReason | None
    source_window: BabylonianCivilWindow
    admitted_window: BabylonianCivilWindow | None
    source: str
    source_url: str
    note: str
    visibility_evidence: BabylonianPlanetaryVisibilityEvidence | None = None

    def __post_init__(self) -> None:
        if self.body not in {Body.MERCURY, Body.VENUS}:
            raise ValueError("BabylonianPlanetaryReference currently supports Mercury and Venus rows only")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("BabylonianPlanetaryReference latitude must be between -90 and 90")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("BabylonianPlanetaryReference longitude must be between -180 and 180")
        expected_status = (
            BabylonianValidationStatus.ADMITTED
            if self.admission_strength in {
                BabylonianAdmissionStrength.STRONG,
                BabylonianAdmissionStrength.BOUNDED,
                BabylonianAdmissionStrength.WEAK,
            }
            else BabylonianValidationStatus.CANDIDATE
        )
        if self.validation_status is not expected_status:
            raise ValueError("BabylonianPlanetaryReference validation_status must match admission_strength")
        if self.validation_status is BabylonianValidationStatus.ADMITTED and self.admitted_window is None:
            raise ValueError("Admitted BabylonianPlanetaryReference rows require an admitted_window")
        if self.validation_status is BabylonianValidationStatus.CANDIDATE and self.admitted_window is not None:
            raise ValueError("Candidate BabylonianPlanetaryReference rows must not define an admitted_window")
        if self.validation_status is BabylonianValidationStatus.ADMITTED and self.holdout_reason is not None:
            raise ValueError("Admitted BabylonianPlanetaryReference rows must not define a holdout_reason")
        if self.validation_status is BabylonianValidationStatus.CANDIDATE and self.holdout_reason is None:
            raise ValueError("Candidate BabylonianPlanetaryReference rows must define a holdout_reason")

    @property
    def comparison_window(self) -> BabylonianCivilWindow:
        return self.admitted_window if self.admitted_window is not None else self.source_window


BABYLONIAN_MERCURY_REFERENCES: tuple[BabylonianPlanetaryReference, ...] = (
    BabylonianPlanetaryReference(
        id="mercury_artaxerxes_ii_y16_mf",
        body=Body.MERCURY,
        event_kind=HeliacalEventKind.HELIACAL_RISING,
        latitude_deg=BABYLON_LATITUDE_DEG,
        longitude_deg=BABYLON_LONGITUDE_DEG,
        observation_class=BabylonianObservationClass.OBSERVED_AND_IDEAL,
        admission_strength=BabylonianAdmissionStrength.BOUNDED,
        validation_status=BabylonianValidationStatus.ADMITTED,
        holdout_reason=None,
        source_window=BabylonianCivilWindow(
            start=BabylonianCivilDay(-388, 10, 25),
            end=BabylonianCivilDay(-388, 10, 30),
            authority=BabylonianChronologyAuthority.DE_JONG_2021,
            note=(
                "Planetary Text No. 59 preserves an ideal first appearance on 25 Oct "
                "389 BCE and an observed first appearance on 30 Oct 389 BCE."
            ),
        ),
        admitted_window=BabylonianCivilWindow(
            start=BabylonianCivilDay(-388, 10, 25),
            end=BabylonianCivilDay(-388, 10, 30),
            authority=BabylonianChronologyAuthority.DE_JONG_2021,
            note=(
                "Admit the source-preserved ideal-to-observed interval directly as the "
                "Babylon comparison window."
            ),
        ),
        source="de Jong 2021, Planetary Text No. 59, year 16 of Artaxerxes II",
        source_url="https://link.springer.com/article/10.1007/s00407-020-00269-6",
        note=(
            "Month VII, day 13: Mercury first appearance in the east near alpha Librae; "
            "paper identifies this as 30 Oct 389 BCE."
        ),
    ),
    BabylonianPlanetaryReference(
        id="mercury_artaxerxes_ii_y16_ml",
        body=Body.MERCURY,
        event_kind=HeliacalEventKind.HELIACAL_SETTING,
        latitude_deg=BABYLON_LATITUDE_DEG,
        longitude_deg=BABYLON_LONGITUDE_DEG,
        observation_class=BabylonianObservationClass.EXPECTED,
        admission_strength=BabylonianAdmissionStrength.HOLDOUT,
        validation_status=BabylonianValidationStatus.CANDIDATE,
        holdout_reason=BabylonianHoldoutReason.MIXED,
        source_window=BabylonianCivilWindow(
            start=BabylonianCivilDay(-388, 4, 13),
            end=BabylonianCivilDay(-388, 4, 14),
            authority=BabylonianChronologyAuthority.DE_JONG_2021,
            note=(
                "Planetary Text No. 59 reports the expected last appearance in the east "
                "on the 13th or 14th day in April 389 BCE."
            ),
        ),
        admitted_window=None,
        source="de Jong 2021, Planetary Text No. 59, year 16 of Artaxerxes II",
        source_url="https://link.springer.com/article/10.1007/s00407-020-00269-6",
        note=(
            "Candidate only. The source itself frames this as an expected date for a very "
            "faint final morning visibility, so the admissible observational slack still "
            "needs an explicit policy decision."
        ),
    ),
    BabylonianPlanetaryReference(
        id="mercury_se79_viii_9_mf",
        body=Body.MERCURY,
        event_kind=HeliacalEventKind.HELIACAL_RISING,
        latitude_deg=BABYLON_LATITUDE_DEG,
        longitude_deg=BABYLON_LONGITUDE_DEG,
        observation_class=BabylonianObservationClass.OMITTED,
        admission_strength=BabylonianAdmissionStrength.HOLDOUT,
        validation_status=BabylonianValidationStatus.CANDIDATE,
        holdout_reason=BabylonianHoldoutReason.MIXED,
        source_window=BabylonianCivilWindow(
            start=babylonian_calendar_to_civil_day(79, 8, 9),
            end=babylonian_calendar_to_civil_day(79, 8, 9),
            authority=BabylonianChronologyAuthority.PARKER_DUBBERSTEIN_1956,
            note=(
                "Diary No. -232 (SE 79) gives Month VIII, day 9 for Mercury's first appearance "
                "in the east; Parker/Dubberstein converts that Babylonian date to a Julian civil day."
            ),
        ),
        admitted_window=None,
        source="de Jong 2021 quoting ADART II, 105; Parker & Dubberstein chronology",
        source_url="https://link.springer.com/article/10.1007/s00407-020-00269-6",
        note=(
            "Candidate only. The diary says 'I did not watch', so this is an omitted-phase record "
            "with explicit calendrical conversion but not yet an admitted oracle window."
        ),
    ),
    BabylonianPlanetaryReference(
        id="mercury_se79_viii_14_el",
        body=Body.MERCURY,
        event_kind=HeliacalEventKind.ACRONYCHAL_SETTING,
        latitude_deg=BABYLON_LATITUDE_DEG,
        longitude_deg=BABYLON_LONGITUDE_DEG,
        observation_class=BabylonianObservationClass.OMITTED,
        admission_strength=BabylonianAdmissionStrength.HOLDOUT,
        validation_status=BabylonianValidationStatus.CANDIDATE,
        holdout_reason=BabylonianHoldoutReason.MIXED,
        source_window=BabylonianCivilWindow(
            start=babylonian_calendar_to_civil_day(79, 8, 14),
            end=babylonian_calendar_to_civil_day(79, 8, 14),
            authority=BabylonianChronologyAuthority.PARKER_DUBBERSTEIN_1956,
            note=(
                "Diary No. -232 (SE 79) gives Month VIII, day 14 for Mercury's last appearance "
                "in the west; Parker/Dubberstein converts that Babylonian date to a Julian civil day."
            ),
        ),
        admitted_window=None,
        source="de Jong 2021 quoting ADART II, 105; Parker & Dubberstein chronology",
        source_url="https://link.springer.com/article/10.1007/s00407-020-00269-6",
        note=(
            "Candidate only. The diary says the observer did not see Mercury from first to last "
            "appearance when watched; calendrical conversion is now explicit, but validation "
            "admission still needs doctrine."
        ),
    ),
    BabylonianPlanetaryReference(
        id="mercury_text_m_el_403_bce",
        body=Body.MERCURY,
        event_kind=HeliacalEventKind.ACRONYCHAL_SETTING,
        latitude_deg=BABYLON_LATITUDE_DEG,
        longitude_deg=BABYLON_LONGITUDE_DEG,
        observation_class=BabylonianObservationClass.TERMINUS_SUPPORT,
        admission_strength=BabylonianAdmissionStrength.HOLDOUT,
        validation_status=BabylonianValidationStatus.CANDIDATE,
        holdout_reason=BabylonianHoldoutReason.MIXED,
        source_window=BabylonianCivilWindow(
            start=BabylonianCivilDay(-402, 7, 2),
            end=BabylonianCivilDay(-402, 7, 2),
            authority=BabylonianChronologyAuthority.DE_JONG_2021,
            note=(
                "The paper identifies the observational basis for Text M as Mercury's last "
                "appearance in the evening on 2 Jul 403 BCE."
            ),
        ),
        admitted_window=None,
        source="de Jong 2021, Text M discussion",
        source_url="https://link.springer.com/article/10.1007/s00407-020-00269-6",
        note=(
            "Candidate only. The date is explicit, but the row is currently used in the "
            "paper as a terminus post quem and observational basis for the ephemeris, not "
            "yet as an admitted one-day validation oracle."
        ),
    ),
)


BABYLONIAN_VENUS_AMMISADUQA_PHENOMENA: tuple[BabylonianHistoricalPhenomenon, ...] = (
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y1_el",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.ACRONYCHAL_SETTING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=1,
        babylonian_month="XI",
        babylonian_day="14",
        source="Fournet 2021, EAE 63 Year 1",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 1 evening last is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y1_mf",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.HELIACAL_RISING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=1,
        babylonian_month="XI",
        babylonian_day="18",
        source="Fournet 2021, EAE 63 Year 1",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 1 morning first is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y2_ml",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.HELIACAL_SETTING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=2,
        babylonian_month="VIII",
        babylonian_day="10",
        source="Fournet 2021, EAE 63 Year 2",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 2 morning last is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y2_ef",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.ACRONYCHAL_RISING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=2,
        babylonian_month="X",
        babylonian_day="19",
        source="Fournet 2021, EAE 63 Year 2",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 2 evening first is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y3_el",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.ACRONYCHAL_SETTING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=3,
        babylonian_month="VI",
        babylonian_day="22",
        source="Fournet 2021, EAE 63 Year 3",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 3 evening last is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y3_mf",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.HELIACAL_RISING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=3,
        babylonian_month="VII",
        babylonian_day="13",
        source="Fournet 2021, EAE 63 Year 3",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 3 morning first is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y4_ml",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.HELIACAL_SETTING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=4,
        babylonian_month="IV",
        babylonian_day="1",
        source="Fournet 2021, EAE 63 Year 4",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 4 morning last is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y4_ef",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.ACRONYCHAL_RISING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=4,
        babylonian_month="VI",
        babylonian_day="3",
        source="Fournet 2021, EAE 63 Year 4",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 4 evening first is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y10_ml",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.HELIACAL_SETTING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=10,
        babylonian_month="VIII",
        babylonian_day="9",
        source="Fournet 2021, EAE 63 Year 10",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 10 morning last is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y10_ef",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.ACRONYCHAL_RISING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=10,
        babylonian_month="X",
        babylonian_day="16",
        source="Fournet 2021, EAE 63 Year 10",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 10 evening first is marked reliable in the 2021 reassessment.",
    ),
    BabylonianHistoricalPhenomenon(
        id="venus_ammisaduqa_y14_mf",
        body=Body.VENUS,
        event_kind=HeliacalEventKind.HELIACAL_RISING,
        source_family="ammisaduqa_2021",
        epoch_label="ancient_babylonian",
        chronology_confidence=ChronologyConfidence.SOURCE_TABLE_AVAILABLE,
        source_quality=BabylonianSourceQuality.RELIABLE,
        source_year=14,
        babylonian_month="VIII",
        babylonian_day="7",
        source="Fournet 2021, EAE 63 Year 14",
        source_url="https://aaatec.org/documents/article/fournetar4.pdf",
        note="Year 14 morning first is marked reliable in the 2021 reassessment.",
    ),
)


_DE_JONG_FOERTMEYER_2010_SOURCE = (
    "de Jong & Foertmeyer 2010 Table 1 (Long Chronology)"
)
_DE_JONG_FOERTMEYER_2010_URL = (
    "https://www.exorientelux.nl/download/JEOL/JEOL42_De_Jong_Foertmeyer.pdf"
)


def _de_jong_foertmeyer_venus_reference(
    *,
    reference_id: str,
    event_kind: HeliacalEventKind,
    source_day: BabylonianCivilDay,
    row_label: str,
    extinction_coefficient: float,
    refracted_elevation_deg: float,
    geometric_arcus_visionis_deg: float,
    nominal_date_delta_days: int,
    source_fit_bracketed: bool = False,
) -> BabylonianPlanetaryReference:
    """Build one source-faithful Table 1 row without claiming solver admission."""

    return BabylonianPlanetaryReference(
        id=reference_id,
        body=Body.VENUS,
        event_kind=event_kind,
        latitude_deg=BABYLON_LATITUDE_DEG,
        longitude_deg=BABYLON_LONGITUDE_DEG,
        observation_class=BabylonianObservationClass.OBSERVED,
        admission_strength=BabylonianAdmissionStrength.HOLDOUT,
        validation_status=BabylonianValidationStatus.CANDIDATE,
        holdout_reason=BabylonianHoldoutReason.VISIBILITY_DOCTRINE_NOT_IMPLEMENTED,
        source_window=BabylonianCivilWindow(
            start=source_day,
            end=source_day,
            authority=BabylonianChronologyAuthority.DE_JONG_FOERTMEYER_2010,
            note=f"Long Chronology Table 1 row, {row_label}.",
        ),
        admitted_window=None,
        source=_DE_JONG_FOERTMEYER_2010_SOURCE,
        source_url=_DE_JONG_FOERTMEYER_2010_URL,
        note=(
            "Physical-visibility source row retained as a candidate until Moira "
            "implements and validates the source's Tousey-Koomen point-source doctrine."
        ),
        visibility_evidence=BabylonianPlanetaryVisibilityEvidence(
            extinction_coefficient_mag_per_airmass=extinction_coefficient,
            refracted_elevation_deg=refracted_elevation_deg,
            geometric_arcus_visionis_deg=geometric_arcus_visionis_deg,
            nominal_date_delta_days=nominal_date_delta_days,
            source_fit_bracketed=source_fit_bracketed,
        ),
    )


BABYLONIAN_VENUS_REFERENCES: tuple[BabylonianPlanetaryReference, ...] = (
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y1_el_long",
        event_kind=HeliacalEventKind.ACRONYCHAL_SETTING,
        source_day=BabylonianCivilDay(-1700, 3, 23),
        row_label="Year 1 EL, Julian date 23-Mar -1700",
        extinction_coefficient=0.25,
        refracted_elevation_deg=5.0,
        geometric_arcus_visionis_deg=7.3,
        nominal_date_delta_days=0,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y1_mf_long",
        event_kind=HeliacalEventKind.HELIACAL_RISING,
        source_day=BabylonianCivilDay(-1700, 3, 28),
        row_label="Year 1 MF, Julian date 28-Mar -1700",
        extinction_coefficient=0.19,
        refracted_elevation_deg=3.6,
        geometric_arcus_visionis_deg=5.9,
        nominal_date_delta_days=-1,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y2_ml_long",
        event_kind=HeliacalEventKind.HELIACAL_SETTING,
        source_day=BabylonianCivilDay(-1700, 12, 12),
        row_label="Year 2 ML, Julian date 12-Dec -1700",
        extinction_coefficient=0.31,
        refracted_elevation_deg=4.1,
        geometric_arcus_visionis_deg=7.7,
        nominal_date_delta_days=-4,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y2_ef_long",
        event_kind=HeliacalEventKind.ACRONYCHAL_RISING,
        source_day=BabylonianCivilDay(-1699, 2, 17),
        row_label="Year 2 EF, Julian date 17-Feb -1699",
        extinction_coefficient=0.29,
        refracted_elevation_deg=3.6,
        geometric_arcus_visionis_deg=7.4,
        nominal_date_delta_days=2,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y3_el_long",
        event_kind=HeliacalEventKind.ACRONYCHAL_SETTING,
        source_day=BabylonianCivilDay(-1699, 10, 13),
        row_label="Year 3 EL, Julian date 13-Oct -1699",
        extinction_coefficient=0.52,
        refracted_elevation_deg=5.6,
        geometric_arcus_visionis_deg=9.6,
        nominal_date_delta_days=-6,
        source_fit_bracketed=True,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y3_mf_long",
        event_kind=HeliacalEventKind.HELIACAL_RISING,
        source_day=BabylonianCivilDay(-1699, 11, 4),
        row_label="Year 3 MF, Julian date 4-Nov -1699",
        extinction_coefficient=0.13,
        refracted_elevation_deg=3.8,
        geometric_arcus_visionis_deg=4.4,
        nominal_date_delta_days=-2,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y4_ml_long",
        event_kind=HeliacalEventKind.HELIACAL_SETTING,
        source_day=BabylonianCivilDay(-1698, 7, 15),
        row_label="Year 4 ML, Julian date 15-Jul -1698",
        extinction_coefficient=0.29,
        refracted_elevation_deg=3.1,
        geometric_arcus_visionis_deg=7.3,
        nominal_date_delta_days=-4,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y4_ef_long",
        event_kind=HeliacalEventKind.ACRONYCHAL_RISING,
        source_day=BabylonianCivilDay(-1698, 9, 13),
        row_label="Year 4 EF, Julian date 13-Sep -1698",
        extinction_coefficient=0.18,
        refracted_elevation_deg=3.0,
        geometric_arcus_visionis_deg=5.3,
        nominal_date_delta_days=-11,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y10_ml_long",
        event_kind=HeliacalEventKind.HELIACAL_SETTING,
        source_day=BabylonianCivilDay(-1692, 12, 12),
        row_label="Year 10 ML, Julian date 12-Dec -1692",
        extinction_coefficient=0.28,
        refracted_elevation_deg=2.8,
        geometric_arcus_visionis_deg=7.1,
        nominal_date_delta_days=-2,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y10_ef_long",
        event_kind=HeliacalEventKind.ACRONYCHAL_RISING,
        source_day=BabylonianCivilDay(-1691, 2, 15),
        row_label="Year 10 EF, Julian date 15-Feb -1691",
        extinction_coefficient=0.29,
        refracted_elevation_deg=3.7,
        geometric_arcus_visionis_deg=7.4,
        nominal_date_delta_days=3,
    ),
    _de_jong_foertmeyer_venus_reference(
        reference_id="venus_ammisaduqa_y14_mf_long",
        event_kind=HeliacalEventKind.HELIACAL_RISING,
        source_day=BabylonianCivilDay(-1687, 1, 13),
        row_label="Year 14 MF, Julian date 13-Jan -1687",
        extinction_coefficient=0.23,
        refracted_elevation_deg=4.6,
        geometric_arcus_visionis_deg=6.7,
        nominal_date_delta_days=0,
    ),
)


def admitted_babylonian_mercury_references() -> tuple[BabylonianPlanetaryReference, ...]:
    return tuple(
        reference
        for reference in BABYLONIAN_MERCURY_REFERENCES
        if reference.validation_status is BabylonianValidationStatus.ADMITTED
    )


def holdout_babylonian_mercury_references() -> tuple[BabylonianPlanetaryReference, ...]:
    return tuple(
        reference
        for reference in BABYLONIAN_MERCURY_REFERENCES
        if reference.validation_status is BabylonianValidationStatus.CANDIDATE
    )


def babylonian_venus_ammisaduqa_phenomena() -> tuple[BabylonianHistoricalPhenomenon, ...]:
    return BABYLONIAN_VENUS_AMMISADUQA_PHENOMENA


def admitted_babylonian_venus_references() -> tuple[BabylonianPlanetaryReference, ...]:
    return tuple(
        reference
        for reference in BABYLONIAN_VENUS_REFERENCES
        if reference.validation_status is BabylonianValidationStatus.ADMITTED
    )


def holdout_babylonian_venus_references() -> tuple[BabylonianPlanetaryReference, ...]:
    return tuple(
        reference
        for reference in BABYLONIAN_VENUS_REFERENCES
        if reference.validation_status is BabylonianValidationStatus.CANDIDATE
    )


def babylonian_planetary_reference(reference_id: str) -> BabylonianPlanetaryReference:
    for reference in BABYLONIAN_MERCURY_REFERENCES + BABYLONIAN_VENUS_REFERENCES:
        if reference.id == reference_id:
            return reference
    raise KeyError(f"Unknown Babylonian planetary reference id: {reference_id}")

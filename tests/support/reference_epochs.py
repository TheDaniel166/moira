"""Exact numeric reference-JD anchors for invariant sweeps.

These records declare how each number is defined. They are numeric anchors,
not permission to treat a TT-defined epoch coordinate as a UT physical instant
in a timescale-sensitive test.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum


class EpochConvention(Enum):
    """Authority convention used to define a numeric Julian Date."""

    JULIAN = "Julian epoch coordinate"
    BESSELIAN = "Besselian epoch coordinate"
    PROLEPTIC_GREGORIAN = "proleptic Gregorian civil anchor"


@dataclass(frozen=True, slots=True)
class CivilAnchor:
    """Proleptic-Gregorian rendering of a numeric Julian Date."""

    year: int
    month: int
    day: int
    hour: float

    def __post_init__(self) -> None:
        for field_name in ("year", "month", "day"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer, not {value!r}.")
        date(self.year, self.month, self.day)
        if isinstance(self.hour, bool) or not isinstance(self.hour, (int, float)):
            raise TypeError(f"hour must be a real number, not {self.hour!r}.")
        if not math.isfinite(float(self.hour)) or not 0.0 <= self.hour < 24.0:
            raise ValueError(f"hour must be finite and in [0, 24); got {self.hour!r}.")


@dataclass(frozen=True, slots=True)
class ReferenceEpoch:
    """One authority-defined JD and its explicit calendar rendering."""

    key: str
    label: str
    jd: float
    convention: EpochConvention
    calendar: CivilAnchor
    definition: str
    epoch_year: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or re.fullmatch(
            r"[a-z0-9][a-z0-9_]*",
            self.key,
        ) is None:
            raise ValueError(f"key must be a stable lowercase slug; got {self.key!r}.")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label must be a nonblank string.")
        if isinstance(self.jd, bool) or not isinstance(self.jd, (int, float)):
            raise TypeError(f"jd must be a real number, not {self.jd!r}.")
        if not math.isfinite(float(self.jd)):
            raise ValueError(f"jd must be finite; got {self.jd!r}.")
        if not isinstance(self.convention, EpochConvention):
            raise TypeError("convention must be an EpochConvention.")
        if not isinstance(self.calendar, CivilAnchor):
            raise TypeError("calendar must be a CivilAnchor.")
        if not isinstance(self.definition, str) or not self.definition.strip():
            raise ValueError("definition must be a nonblank string.")

        requires_epoch_year = self.convention in {
            EpochConvention.JULIAN,
            EpochConvention.BESSELIAN,
        }
        if requires_epoch_year:
            if isinstance(self.epoch_year, bool) or not isinstance(
                self.epoch_year,
                (int, float),
            ):
                raise TypeError(
                    f"{self.convention.value} requires a finite epoch_year."
                )
            if not math.isfinite(float(self.epoch_year)):
                raise ValueError("epoch_year must be finite.")
        elif self.epoch_year is not None:
            raise ValueError("civil anchors must not declare an epoch_year.")


REFERENCE_EPOCHS = (
    ReferenceEpoch(
        key="j2000",
        label="J2000.0",
        jd=2451545.0,
        convention=EpochConvention.JULIAN,
        epoch_year=2000.0,
        calendar=CivilAnchor(2000, 1, 1, 12.0),
        definition="ERFA epj2jd(2000.0); Julian epoch coordinate.",
    ),
    ReferenceEpoch(
        key="b1900",
        label="B1900.0",
        jd=2415020.31352,
        convention=EpochConvention.BESSELIAN,
        epoch_year=1900.0,
        calendar=CivilAnchor(1899, 12, 31, 19.52448),
        definition="ERFA epb2jd(1900.0); Besselian epoch coordinate.",
    ),
    ReferenceEpoch(
        key="gregorian_reform_1582_10_15",
        label="Gregorian_reform_1582_10_15",
        jd=2299160.5,
        convention=EpochConvention.PROLEPTIC_GREGORIAN,
        calendar=CivilAnchor(1582, 10, 15, 0.0),
        definition="ERFA cal2jd(1582, 10, 15); first historical Gregorian date.",
    ),
    ReferenceEpoch(
        key="proleptic_gregorian_0001_01_01",
        label="Proleptic_Gregorian_0001_01_01",
        jd=1721425.5,
        convention=EpochConvention.PROLEPTIC_GREGORIAN,
        calendar=CivilAnchor(1, 1, 1, 0.0),
        definition="ERFA cal2jd(1, 1, 1); proleptic Gregorian civil anchor.",
    ),
    ReferenceEpoch(
        key="j2100",
        label="J2100.0",
        jd=2488070.0,
        convention=EpochConvention.JULIAN,
        epoch_year=2100.0,
        calendar=CivilAnchor(2100, 1, 1, 12.0),
        definition="ERFA epj2jd(2100.0); Julian epoch coordinate.",
    ),
)

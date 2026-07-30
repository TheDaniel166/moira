"""Authority and calendar contracts for shared numeric reference-JD anchors."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import erfa
import pytest

from moira.julian import calendar_from_jd, julian_day
from support.reference_epochs import (
    REFERENCE_EPOCHS,
    EpochConvention,
    ReferenceEpoch,
)


def _erfa_reference_jd(anchor: ReferenceEpoch) -> float:
    if anchor.convention is EpochConvention.JULIAN:
        assert anchor.epoch_year is not None
        return float(sum(erfa.epj2jd(anchor.epoch_year)))
    if anchor.convention is EpochConvention.BESSELIAN:
        assert anchor.epoch_year is not None
        return float(sum(erfa.epb2jd(anchor.epoch_year)))
    if anchor.convention is EpochConvention.PROLEPTIC_GREGORIAN:
        assert anchor.epoch_year is None
        date1, date2 = erfa.cal2jd(
            anchor.calendar.year,
            anchor.calendar.month,
            anchor.calendar.day,
        )
        return float(date1 + date2 + anchor.calendar.hour / 24.0)
    raise AssertionError(f"Unadmitted epoch convention: {anchor.convention!r}")


def test_reference_epoch_set_is_explicit_and_unique() -> None:
    assert tuple(anchor.label for anchor in REFERENCE_EPOCHS) == (
        "J2000.0",
        "B1900.0",
        "Gregorian_reform_1582_10_15",
        "Proleptic_Gregorian_0001_01_01",
        "J2100.0",
    )
    assert len({anchor.key for anchor in REFERENCE_EPOCHS}) == len(REFERENCE_EPOCHS)
    assert len({anchor.jd for anchor in REFERENCE_EPOCHS}) == len(REFERENCE_EPOCHS)


@pytest.mark.parametrize(
    "anchor",
    REFERENCE_EPOCHS,
    ids=lambda anchor: anchor.key,
)
def test_reference_epoch_matches_independent_erfa_definition(
    anchor: ReferenceEpoch,
) -> None:
    assert anchor.jd == _erfa_reference_jd(anchor)


@pytest.mark.parametrize(
    "anchor",
    REFERENCE_EPOCHS,
    ids=lambda anchor: anchor.key,
)
def test_reference_epoch_round_trips_through_moira_proleptic_gregorian_calendar(
    anchor: ReferenceEpoch,
) -> None:
    assert julian_day(
        anchor.calendar.year,
        anchor.calendar.month,
        anchor.calendar.day,
        anchor.calendar.hour,
    ) == anchor.jd

    year, month, day, hour = calendar_from_jd(anchor.jd)
    assert (year, month, day) == (
        anchor.calendar.year,
        anchor.calendar.month,
        anchor.calendar.day,
    )
    assert hour == pytest.approx(anchor.calendar.hour, abs=1e-8)


def test_reference_epoch_records_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        REFERENCE_EPOCHS[0].jd = 0.0  # type: ignore[misc]

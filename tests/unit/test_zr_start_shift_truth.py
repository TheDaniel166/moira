"""Zodiacal Releasing start-shift receipt (Valens' Spirit/Fortune same-sign rule).

Source rule, as already implemented by the releasing engine: when releasing
from Spirit and Spirit shares Fortune's sign, Level 1 starts from the
following sign. These tests pin the typed receipt that records which branch
applied, so omitting Fortune is visible instead of silently unshifted.
"""

from __future__ import annotations

import pytest

import moira
import moira.classical as classical
import moira.facade as facade
from moira.timelords import (
    TimelordEvaluationStatus,
    ZRStartShiftTruth,
    current_releasing,
    zodiacal_releasing,
    zr_start_shift_truth,
)

NATAL_JD = 2451545.0
SPIRIT_ARIES = 10.0
FORTUNE_ARIES = 15.0
FORTUNE_GEMINI = 75.0


def test_spirit_without_fortune_is_not_evaluable_and_unshifted() -> None:
    truth = zr_start_shift_truth(SPIRIT_ARIES, "Spirit", None)

    assert truth.status is TimelordEvaluationStatus.NOT_EVALUABLE
    assert truth.reason == "fortune_not_supplied"
    assert truth.rule_applies is True
    assert truth.shift_applied is None
    assert truth.start_sign == "Aries"


def test_spirit_sharing_fortunes_sign_starts_from_the_next_sign() -> None:
    truth = zr_start_shift_truth(SPIRIT_ARIES, "Spirit", FORTUNE_ARIES)

    assert truth.status is TimelordEvaluationStatus.EVALUATED
    assert truth.shift_applied is True
    assert (truth.lot_sign, truth.fortune_sign, truth.start_sign) == (
        "Aries",
        "Aries",
        "Taurus",
    )


def test_spirit_in_another_sign_and_other_lots_are_unshifted() -> None:
    other = zr_start_shift_truth(SPIRIT_ARIES, "Spirit", FORTUNE_GEMINI)
    assert other.status is TimelordEvaluationStatus.EVALUATED
    assert other.shift_applied is False
    assert other.start_sign == "Aries"

    for lot in ("Fortune", "Eros", "Necessity"):
        truth = zr_start_shift_truth(SPIRIT_ARIES, lot, None)
        assert truth.status is TimelordEvaluationStatus.EVALUATED
        assert truth.rule_applies is False
        assert truth.shift_applied is False
        assert truth.start_sign == "Aries"


@pytest.mark.parametrize(
    ("fortune", "expected_start"),
    [(None, "Aries"), (FORTUNE_ARIES, "Taurus"), (FORTUNE_GEMINI, "Aries")],
)
def test_every_period_carries_the_receipt_that_chose_its_start(
    fortune: float | None,
    expected_start: str,
) -> None:
    periods = zodiacal_releasing(
        SPIRIT_ARIES,
        NATAL_JD,
        levels=3,
        lot_name="Spirit",
        fortune_longitude=fortune,
    )
    truth = periods[0].start_shift_truth

    assert periods[0].level == 1
    assert periods[0].sign == expected_start == truth.start_sign
    assert all(period.start_shift_truth is truth for period in periods)

    active = current_releasing(
        SPIRIT_ARIES,
        NATAL_JD,
        NATAL_JD + 1000.0,
        lot_name="Spirit",
        fortune_longitude=fortune,
        levels=2,
    )
    assert all(period.start_shift_truth == truth for period in active)


def test_receipt_rejects_fabricated_branches() -> None:
    with pytest.raises(ValueError, match="same-sign rule"):
        ZRStartShiftTruth(
            status=TimelordEvaluationStatus.EVALUATED,
            lot_name="Spirit",
            lot_sign="Aries",
            fortune_sign="Aries",
            rule_applies=True,
            shift_applied=False,
            start_sign="Aries",
        )
    with pytest.raises(ValueError, match="fortune_not_supplied"):
        ZRStartShiftTruth(
            status=TimelordEvaluationStatus.NOT_EVALUABLE,
            lot_name="Spirit",
            lot_sign="Aries",
            fortune_sign=None,
            rule_applies=True,
            shift_applied=None,
            start_sign="Taurus",
            reason="fortune_not_supplied",
        )
    with pytest.raises(ValueError, match="only for Spirit"):
        ZRStartShiftTruth(
            status=TimelordEvaluationStatus.EVALUATED,
            lot_name="Fortune",
            lot_sign="Aries",
            fortune_sign=None,
            rule_applies=True,
            shift_applied=False,
            start_sign="Aries",
        )


def test_receipt_is_exported_on_every_public_surface() -> None:
    for surface in (moira, classical, facade):
        assert surface.ZRStartShiftTruth is ZRStartShiftTruth
        assert surface.zr_start_shift_truth is zr_start_shift_truth
        assert "ZRStartShiftTruth" in surface.__all__
        assert "zr_start_shift_truth" in surface.__all__

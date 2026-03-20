from __future__ import annotations

import pytest

from moira.sothic import (
    EPAGOMENAL_BIRTHS,
    _EGYPTIAN_YEAR_DAYS,
    _SOTHIC_EPOCH_139_JD,
    days_from_1_thoth,
    egyptian_civil_date,
    predicted_sothic_epoch_year,
    sothic_drift_rate,
)


def test_egyptian_civil_date_epoch_is_1_thoth() -> None:
    date = egyptian_civil_date(_SOTHIC_EPOCH_139_JD)

    assert date.month_name == "Thoth"
    assert date.month_number == 1
    assert date.day == 1
    assert date.season == "Akhet"
    assert date.day_of_year == 1
    assert date.epagomenal_birth is None


def test_egyptian_civil_date_handles_month_and_epagomenal_boundaries() -> None:
    end_of_thoth = egyptian_civil_date(_SOTHIC_EPOCH_139_JD + 29)
    start_of_phaophi = egyptian_civil_date(_SOTHIC_EPOCH_139_JD + 30)
    first_epagomenal = egyptian_civil_date(_SOTHIC_EPOCH_139_JD + 360)
    fifth_epagomenal = egyptian_civil_date(_SOTHIC_EPOCH_139_JD + 364)

    assert end_of_thoth.month_name == "Thoth"
    assert end_of_thoth.day == 30

    assert start_of_phaophi.month_name == "Phaophi"
    assert start_of_phaophi.month_number == 2
    assert start_of_phaophi.day == 1

    assert first_epagomenal.month_name == "Epagomenal"
    assert first_epagomenal.month_number == 13
    assert first_epagomenal.day == 1
    assert first_epagomenal.epagomenal_birth == EPAGOMENAL_BIRTHS[0]

    assert fifth_epagomenal.month_name == "Epagomenal"
    assert fifth_epagomenal.day == 5
    assert fifth_epagomenal.epagomenal_birth == EPAGOMENAL_BIRTHS[4]


def test_days_from_1_thoth_wraps_cleanly() -> None:
    assert days_from_1_thoth(_SOTHIC_EPOCH_139_JD) == pytest.approx(0.0, abs=1e-12)
    assert days_from_1_thoth(_SOTHIC_EPOCH_139_JD + 10.25) == pytest.approx(10.25, abs=1e-12)
    assert days_from_1_thoth(_SOTHIC_EPOCH_139_JD + _EGYPTIAN_YEAR_DAYS + 2.5) == pytest.approx(2.5, abs=1e-12)
    assert days_from_1_thoth(_SOTHIC_EPOCH_139_JD - 1.0) == pytest.approx(364.0, abs=1e-12)


def test_predicted_sothic_epoch_year_uses_simple_cycle_arithmetic() -> None:
    assert predicted_sothic_epoch_year(139, 1) == pytest.approx(1599.0, abs=1e-12)
    assert predicted_sothic_epoch_year(139, -1) == pytest.approx(-1321.0, abs=1e-12)
    assert predicted_sothic_epoch_year(-1321, -1) == pytest.approx(-2781.0, abs=1e-12)


def test_sothic_drift_rate_recovers_wrapped_linear_trend() -> None:
    entries = []
    drift = 360.0
    for year in range(0, 10):
        entries.append(type("Entry", (), {"year": year, "drift_days": drift}))
        drift = (drift + 0.242) % _EGYPTIAN_YEAR_DAYS

    rate = sothic_drift_rate(entries)
    assert rate == pytest.approx(0.242, abs=1e-6)

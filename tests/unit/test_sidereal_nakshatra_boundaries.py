"""Exact boundary and TT-entry tests for the sidereal nakshatra partition."""

from __future__ import annotations

import math

import pytest

import moira.sidereal as sidereal_module
from moira.dasha import VIMSHOTTARI_YEARS, dasha_balance, vimshottari
from moira.julian import ut_to_tt
from moira.sidereal import (
    Ayanamsa,
    NAKSHATRA_LORDS,
    NAKSHATRA_NAMES,
    _ayanamsa_at_tt,
    _nakshatra_position_from_sidereal,
    _nakshatra_sector,
    _tropical_to_sidereal_at_tt,
    ayanamsa,
    nakshatra_of,
    sidereal_to_tropical,
    tropical_to_sidereal,
)


J2000 = 2451545.0


@pytest.mark.parametrize("boundary_number", range(1, 28))
def test_all_nakshatra_boundaries_are_half_open_before_exact_after(
    boundary_number: int,
) -> None:
    boundary = boundary_number * 40.0 / 3.0
    if boundary_number < 27:
        # The first predecessor is reserved for the bounded one-ULP recovery.
        strictly_before = math.nextafter(
            math.nextafter(boundary, -math.inf),
            -math.inf,
        )
        expected_exact = boundary_number
    else:
        strictly_before = math.nextafter(360.0, -math.inf)
        expected_exact = 0
    strictly_after = math.nextafter(boundary, math.inf)

    _, before_index, _ = _nakshatra_sector(strictly_before)
    _, exact_index, exact_degrees = _nakshatra_sector(boundary)
    _, after_index, _ = _nakshatra_sector(strictly_after)

    assert before_index == boundary_number - 1
    assert exact_index == expected_exact
    assert after_index == expected_exact
    assert exact_degrees == 0.0


@pytest.mark.parametrize("boundary_number", range(1, 27))
def test_internal_boundary_recovers_exactly_one_predecessor_ulp(
    boundary_number: int,
) -> None:
    boundary = boundary_number * 40.0 / 3.0
    predecessor = math.nextafter(boundary, -math.inf)
    second_predecessor = math.nextafter(predecessor, -math.inf)

    recovered_lon, recovered_index, recovered_degrees = _nakshatra_sector(predecessor)
    _, preceding_index, _ = _nakshatra_sector(second_predecessor)

    assert recovered_lon == boundary
    assert recovered_index == boundary_number
    assert recovered_degrees == 0.0
    assert preceding_index == boundary_number - 1


def test_zodiac_wrap_does_not_recover_predecessor_of_360() -> None:
    before_wrap = _nakshatra_position_from_sidereal(
        math.nextafter(360.0, -math.inf)
    )
    at_wrap = _nakshatra_position_from_sidereal(360.0)
    below_zero = _nakshatra_position_from_sidereal(
        math.nextafter(0.0, -math.inf)
    )

    assert before_wrap.nakshatra_index == 26
    assert below_zero.nakshatra_index == 26
    assert at_wrap.nakshatra_index == 0
    assert at_wrap.degrees_in == 0.0


@pytest.mark.parametrize("boundary_number", range(1, 27))
def test_public_nakshatra_and_vimshottari_share_boundary_ownership(
    boundary_number: int,
) -> None:
    sidereal_boundary = boundary_number * 40.0 / 3.0
    tropical_longitude = sidereal_to_tropical(
        sidereal_boundary,
        J2000,
        Ayanamsa.LAHIRI,
    )

    position = nakshatra_of(tropical_longitude, J2000, Ayanamsa.LAHIRI)
    periods = vimshottari(
        tropical_longitude,
        J2000,
        levels=1,
        ayanamsa_system=Ayanamsa.LAHIRI,
    )
    balance_lord, balance_years = dasha_balance(
        tropical_longitude,
        J2000,
        ayanamsa_system=Ayanamsa.LAHIRI,
    )

    expected_lord = NAKSHATRA_LORDS[boundary_number]
    assert position.nakshatra_index == boundary_number
    assert periods[0].birth_nakshatra == NAKSHATRA_NAMES[boundary_number]
    assert periods[0].nakshatra_fraction == pytest.approx(0.0, abs=1e-14)
    assert balance_lord == expected_lord
    assert balance_years == pytest.approx(
        float(VIMSHOTTARI_YEARS[expected_lord]),
        abs=1e-12,
    )


@pytest.mark.parametrize("mode", ["mean", "true"])
def test_tt_explicit_polynomial_helpers_match_public_ut_contract(mode: str) -> None:
    jd_tt = ut_to_tt(J2000)
    longitude = 123.456789

    assert _ayanamsa_at_tt(jd_tt, Ayanamsa.LAHIRI, mode) == ayanamsa(
        J2000,
        Ayanamsa.LAHIRI,
        mode,
    )
    assert _tropical_to_sidereal_at_tt(
        longitude,
        jd_tt,
        Ayanamsa.LAHIRI,
        mode,
    ) == tropical_to_sidereal(longitude, J2000, Ayanamsa.LAHIRI, mode)


def test_tt_explicit_helpers_never_apply_ut_to_tt_again(monkeypatch) -> None:
    jd_tt = ut_to_tt(J2000)

    def reject_duplicate_conversion(_jd: float) -> float:
        raise AssertionError("TT-explicit sidereal path attempted UT-to-TT again")

    monkeypatch.setattr(sidereal_module, "ut_to_tt", reject_duplicate_conversion)

    ayan = _ayanamsa_at_tt(jd_tt, Ayanamsa.LAHIRI, "true")
    sidereal = _tropical_to_sidereal_at_tt(
        123.456789,
        jd_tt,
        Ayanamsa.LAHIRI,
        "true",
    )

    assert math.isfinite(ayan)
    assert 0.0 <= sidereal < 360.0


def test_public_tropical_conversion_applies_ut_to_tt_once(monkeypatch) -> None:
    calls: list[float] = []

    def witnessed_conversion(jd_ut: float) -> float:
        calls.append(jd_ut)
        return jd_ut + 0.25

    monkeypatch.setattr(sidereal_module, "ut_to_tt", witnessed_conversion)
    monkeypatch.setattr(
        sidereal_module,
        "general_precession_in_longitude",
        lambda _jd_tt: 0.0,
    )
    monkeypatch.setattr(sidereal_module, "nutation", lambda _jd_tt: (0.0, 0.0))

    tropical_to_sidereal(100.0, J2000, Ayanamsa.LAHIRI, "true")

    assert calls == [J2000]


@pytest.mark.parametrize("entrypoint", [ayanamsa, tropical_to_sidereal])
def test_public_invalid_mode_precedes_clock_conversion(monkeypatch, entrypoint) -> None:
    def reject_clock_conversion(_jd: float) -> float:
        raise AssertionError("invalid mode must fail before clock conversion")

    monkeypatch.setattr(sidereal_module, "ut_to_tt", reject_clock_conversion)

    args = (J2000,) if entrypoint is ayanamsa else (100.0, J2000)
    with pytest.raises(ValueError, match="mode"):
        entrypoint(*args, mode="invalid")

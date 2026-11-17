"""Independent precision checks for the private two-part NAIF time path."""

from decimal import Decimal, localcontext
import math

import pytest

from moira.julian import (
    _naif_tdb_minus_tt_seconds_at_tdb_split,
    _tt_to_tdb_split,
    tt_to_tdb,
)


DAY = Decimal(86400)
J2000 = Decimal(2451545)
PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816")


def _decimal_sin(value: Decimal) -> Decimal:
    """Evaluate sine by an independent high-precision Taylor series."""
    value %= 2 * PI
    if value > PI:
        value -= 2 * PI
    if value < -PI:
        value += 2 * PI
    total = term = value
    for index in range(1, 100):
        term *= -(value * value) / Decimal((2 * index) * (2 * index + 1))
        total += term
        if abs(term) < Decimal("1e-68"):
            break
    return total


def _reference_tdb(tt1: float, tt2: float) -> Decimal:
    """Solve the pinned LSK equation using independently evaluated Decimal sine."""
    with localcontext() as context:
        context.prec = 70
        tt = Decimal.from_float(tt1) + Decimal.from_float(tt2)
        tdb = tt
        for _ in range(8):
            mean = Decimal("6.239996") + Decimal("1.99096871e-7") * (tdb - J2000) * DAY
            eccentric = mean + Decimal("1.671e-2") * _decimal_sin(mean)
            updated = tt + Decimal("1.657e-3") * _decimal_sin(eccentric) / DAY
            if abs(updated - tdb) < Decimal("1e-60"):
                return updated
            tdb = updated
        raise AssertionError("independent Decimal time equation did not converge")


@pytest.mark.parametrize(
    ("tt1", "tt2"),
    [
        (1009276.276767078, -1.25 / 86400.0),
        (1026285.7107341307, -499.0 / 86400.0),
        (1538582.439889415, 0.0),
        (2440432.5, 1.0e-6 / 86400.0),
        (2451545.0, -1.0e-6 / 86400.0),
        (2467674.350456808, -1.25 / 86400.0),
        (4000000.75, 0.0),
    ],
)
def test_split_tdb_matches_independent_decimal_naif_equation(tt1: float, tt2: float) -> None:
    with localcontext() as context:
        context.prec = 70
        whole, fractional = _tt_to_tdb_split(tt1, tt2)
        actual = Decimal.from_float(whole) + Decimal.from_float(fractional)
        error_seconds = abs((actual - _reference_tdb(tt1, tt2)) * DAY)
    assert whole == math.floor(whole)
    assert 0.0 <= fractional < 1.0
    # One fractional-day binary64 rounding is at most about five picoseconds.
    assert error_seconds < Decimal("2e-11")


def test_emission_offset_is_not_rounded_away_before_conversion() -> None:
    reception = 1026285.7107341307
    delay = 1.25 / 86400.0
    with localcontext() as context:
        context.prec = 70
        actual = _tt_to_tdb_split(reception, -delay)
        split_tdb = Decimal.from_float(actual[0]) + Decimal.from_float(actual[1])
        reference = _reference_tdb(reception, -delay)
        split_error = abs((split_tdb - reference) * DAY)
        rounded_input = tt_to_tdb(reception - delay)
        legacy_error = abs((Decimal.from_float(rounded_input) - reference) * DAY)
    assert split_error < Decimal("2e-11")
    assert legacy_error > Decimal("1e-7")


@pytest.mark.parametrize(
    ("tt1", "tt2"),
    [(1026285.7107341307, -1.25 / 86400.0),
     (2440432.5, 1e-6 / 86400.0),
     (2451545.0, -1e-6 / 86400.0),
     (2467674.350456808, -499.0 / 86400.0)],
)
def test_erfa_two_part_assembly_with_the_same_naif_offset(tt1: float, tt2: float) -> None:
    erfa = pytest.importorskip("erfa")
    whole, fractional = _tt_to_tdb_split(tt1, tt2)
    pinned_offset = _naif_tdb_minus_tt_seconds_at_tdb_split(whole, fractional)
    erfa_first, erfa_second = erfa.tttdb(tt1, tt2, pinned_offset)
    with localcontext() as context:
        context.prec = 70
        ours = Decimal.from_float(whole) + Decimal.from_float(fractional)
        theirs = Decimal.from_float(float(erfa_first)) + Decimal.from_float(float(erfa_second))
        error_seconds = abs((ours - theirs) * DAY)
    # This compares time representation using the identical pinned offset,
    # not ERFA's distinct physical model for TDB-TT.
    assert error_seconds < Decimal("2e-11")


@pytest.mark.parametrize("jd", [1000000.25, 2440432.5, 2451545.0, 4000000.75])
def test_public_single_part_contract_is_preserved(jd: float) -> None:
    whole, fractional = _tt_to_tdb_split(jd)
    assert abs(math.fsum((whole, fractional)) - tt_to_tdb(jd)) <= math.ulp(jd)


@pytest.mark.parametrize("bad", [True, False, math.nan, math.inf, -math.inf, 1e20])
def test_invalid_split_inputs_are_rejected(bad: float) -> None:
    with pytest.raises(ValueError):
        _tt_to_tdb_split(bad, 0.0)
    with pytest.raises(ValueError):
        _tt_to_tdb_split(2451545.0, bad)


def test_combined_coordinate_must_be_in_the_representable_domain() -> None:
    with pytest.raises(ValueError, match="representable"):
        _tt_to_tdb_split(40000000.0, 1e-6)
    with pytest.raises(ValueError, match="representable"):
        _tt_to_tdb_split(-40000000.0, -1e-6)

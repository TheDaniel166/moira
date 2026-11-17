"""Continuous exact implicit reference clock enclosures and contraction."""
from decimal import Decimal, localcontext
from fractions import Fraction
import math

import pytest

from moira import julian
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_reference_clock import bound_continuous_reference_tdb


def _decimal_reference_correction(tt):
    # Independent high-precision decimal fixed-point/Taylor check. It is a
    # numerical witness; the interval and contraction proofs are separate.
    with localcontext() as context:
        context.prec = 100
        pi = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068")

        def sine(value):
            x = value % (2 * pi)
            if x > pi:
                x -= 2 * pi
            if x < -pi:
                x += 2 * pi
            result = term = x
            for n in range(1, 100):
                term *= -(x * x) / Decimal((2 * n) * (2 * n + 1))
                result += term
            return result

        k = Decimal.from_float(julian._NAIF_DELTET_K_SECONDS)
        m0 = Decimal.from_float(julian._NAIF_DELTET_M0_RADIANS)
        m1 = Decimal.from_float(julian._NAIF_DELTET_M1_RADIANS_PER_SECOND)
        eb = Decimal.from_float(julian._NAIF_DELTET_EB)
        t = Decimal.from_float(tt)
        correction = Decimal(0)
        for _ in range(12):
            mean = m0 + m1 * Decimal(86400) * (t + correction - Decimal(2451545))
            correction = k / Decimal(86400) * sine(mean + eb * sine(mean))
        return Fraction(correction)


@pytest.mark.parametrize("tt", [-1200954.75, 1026285.7107341307, 2459891.9582497696, 6104045.25])
def test_continuous_clock_encloses_independent_decimal_points(tt, monkeypatch):
    monkeypatch.setattr(math, "sin", lambda *args: (_ for _ in ()).throw(AssertionError("platform sin used")))
    monkeypatch.setattr(math, "cos", lambda *args: (_ for _ in ()).throw(AssertionError("platform cos used")))
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = bound_continuous_reference_tdb(tt, offsets)
    assert result.continuous_on_domain
    assert 0 < result.contraction_ratio < Fraction(1, 10**8)
    assert result.derivative_tdb_per_tt.lo > 0
    assert not result.legacy_converter_enclosed
    assert not result.ut1_enclosed
    for seconds in (-4, 0, 4):
        epoch = tt + seconds / 86400
        correction = _decimal_reference_correction(epoch)
        assert result.correction_days.contains(correction)
        relative = Fraction.from_float(epoch) - Fraction.from_float(tt) + correction
        assert result.tdb_offset_days.contains(relative)


def test_reference_clock_rejects_unsupported_domain_and_bad_budget():
    with pytest.raises(EnclosureUnavailable):
        bound_continuous_reference_tdb(40000000.0, I.point(1))
    with pytest.raises(ValueError):
        bound_continuous_reference_tdb(2451545.0, I.point(0), steps=0)

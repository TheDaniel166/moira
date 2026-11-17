"""Conditional amplitude bounds cover both nutation serving paths."""
from fractions import Fraction
import math
import random
import sys

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_nutation_amplitudes import bound_conditional_nutation_amplitudes
from moira import nutation_2000a as nutation_module


PREMISES = dict(assume_ieee_arithmetic=True, assume_finite_unit_trig=True,
                assume_registered_tables_and_caches_match=True)


@pytest.mark.parametrize("tt", [-1200954.75, 991000.3, 2459891.7008, 2460409.201, 6104045.25])
def test_loaded_nutation_series_enclosed_at_represented_epochs(tt):
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = bound_conditional_nutation_amplitudes(tt, offsets, **PREMISES)
    assert len(result.coefficient_sha256) == 64
    assert result.longitude_term_count >= 1320 and result.obliquity_term_count >= 1037
    assert result.native_registered_tables_match_required
    assert result.python_and_native_caches_match_required
    assert not result.registered_tables_attested
    assert not result.actual_source_totality_proved
    assert not result.physical_accuracy_certified
    for seconds in (-4, 0, 4):
        epoch = tt + seconds / 86400
        t = nutation_module.centuries_from_j2000(epoch)
        python = nutation_module._nutation_python(t, nutation_module._fundamental_args(t))
        native = nutation_module.nutation_2000a(epoch)
        for value in (python, native):
            assert result.longitude_degrees.contains(value[0])
            assert result.obliquity_degrees.contains(value[1])


def test_seeded_full_catalog_range_native_values_enclosed():
    rng = random.Random(6163)
    # One 5000-year interval uses conservative amplitude/|T| bounds once.
    first, last = 990574.5, 2817152.5
    result = bound_conditional_nutation_amplitudes(first, I(0, last - first), **PREMISES)
    for _ in range(80):
        epoch = rng.uniform(first, last)
        longitude, obliquity = nutation_module.nutation_2000a(epoch)
        assert result.longitude_degrees.contains(longitude)
        assert result.obliquity_degrees.contains(obliquity)


def test_no_claim_without_arithmetic_and_registered_table_premises():
    with pytest.raises(EnclosureUnavailable, match="premises"):
        bound_conditional_nutation_amplitudes(2459891.0, I.point(0))
    with pytest.raises(TypeError):
        bound_conditional_nutation_amplitudes(2459891.0, (0, 1), **PREMISES)
    with pytest.raises(ValueError):
        bound_conditional_nutation_amplitudes(math.nan, I.point(0), **PREMISES)
    with pytest.raises(EnclosureUnavailable, match="domain"):
        bound_conditional_nutation_amplitudes(40000001.0, I.point(0), **PREMISES)


def test_invalid_or_nonfinite_coefficient_tables_fail_closed(monkeypatch):
    monkeypatch.setattr(nutation_module, "_LS_J0_COUNT", 1)
    monkeypatch.setattr(nutation_module, "_PL_J0_COUNT", 1)
    monkeypatch.setattr(nutation_module, "_ensure_tables_loaded",
                        lambda: ([(float("inf"), 0.0, 1)], [(0.0, 1.0, 1)]))
    with pytest.raises(EnclosureUnavailable, match="coefficients"):
        bound_conditional_nutation_amplitudes(2459891.0, I.point(0), **PREMISES)


def test_unscaled_time_order_term_overflow_fails_before_zero_time_weight(monkeypatch):
    # Even at T=0, the source evaluates c1*sin+c2*cos before multiplying by T.
    # Its intermediate can be nonfinite although the exact weighted sum is 0.
    monkeypatch.setattr(nutation_module, "_LS_J0_COUNT", 0)
    monkeypatch.setattr(nutation_module, "_PL_J0_COUNT", 1)
    monkeypatch.setattr(nutation_module, "_ensure_tables_loaded",
                        lambda: ([(sys.float_info.max, -sys.float_info.max, 1)],
                                 [(0.0, 0.0, 1)]))
    with pytest.raises(EnclosureUnavailable, match="unscaled term"):
        bound_conditional_nutation_amplitudes(2451545.0, I.point(0), **PREMISES)


def test_large_finite_and_subnormal_coefficients_are_conservatively_enclosed(monkeypatch):
    terms = [(1e290, -1e290, 1), (5e-324, -5e-324, 1)]
    monkeypatch.setattr(nutation_module, "_LS_J0_COUNT", 1)
    monkeypatch.setattr(nutation_module, "_PL_J0_COUNT", 1)
    monkeypatch.setattr(nutation_module, "_ensure_tables_loaded", lambda: (terms, terms))
    result = bound_conditional_nutation_amplitudes(2451545.0, I.point(0), **PREMISES)
    python = nutation_module._nutation_python(0.0, (math.pi / 2,))
    assert result.longitude_degrees.contains(python[0])
    assert result.obliquity_degrees.contains(python[1])

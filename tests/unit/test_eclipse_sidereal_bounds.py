"""Conditional GAST bounds exercise both serving paths and explicit limits."""
from fractions import Fraction
import math
import random

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_sidereal_bounds import (
    bound_conditional_sidereal_from_nutation_tables, bound_conditional_sidereal_time,
)
from moira import julian, moira_native
from moira.obliquity import nutation


PREMISES = dict(assume_ieee_arithmetic=True,
                assume_correctly_rounded_integer_powers=True,
                assume_finite_unit_trig=True)


def test_explicit_arithmetic_and_nutation_boxes_are_required():
    with pytest.raises(EnclosureUnavailable, match="premises"):
        bound_conditional_sidereal_time(2459891.0, I.point(0), 2459891.0,
                                       I.point(0), I(-1, 1))
    with pytest.raises(TypeError):
        bound_conditional_sidereal_time(2459891.0, I.point(0), 2459891.0,
                                       I.point(0), 0.0, **PREMISES)


@pytest.mark.parametrize("ut,tt", [
    (2459891.7, 2459891.7008),
    (2460409.2, 2460409.201),
    (991000.3, 991000.6),
    (-1200954.75, -1200950.0),
    (6104045.25, 6104045.8),
])
def test_python_and_native_represented_values_are_enclosed(ut, tt):
    span = I(Fraction(-2, 86400), Fraction(2, 86400))
    dpsi_samples = [nutation(tt + seconds / 86400)[0] for seconds in (-1, 0, 1)]
    # Conservative supplied dpsi domain; its provenance is not certified.
    margin = 0.0001
    dpsi_box = I(min(dpsi_samples) - margin, max(dpsi_samples) + margin)
    bounds = bound_conditional_sidereal_time(ut, span, tt, span, dpsi_box, **PREMISES)
    assert bounds.caller_supplied_nutation_enclosure_required
    assert not bounds.nutation_enclosure_attested
    assert not bounds.source_and_arithmetic_attested
    assert not bounds.earth_fixed_orientation_certified
    for seconds, dpsi in zip((-1, 0, 1), dpsi_samples):
        u, t = ut + seconds / 86400, tt + seconds / 86400
        py_era = julian.earth_rotation_angle.__wrapped__(u)
        py_gmst = julian._greenwich_mean_sidereal_time_at_tt.__wrapped__(u, t)
        py_gast = julian._apparent_sidereal_time_at_tt.__wrapped__(u, t, dpsi)
        assert bounds.era_degrees.contains(py_era)
        assert bounds.gmst_degrees.contains(py_gmst)
        assert bounds.gast_degrees.contains(py_gast)
        assert bounds.gmst_degrees.contains(moira_native.greenwich_mean_sidereal_time(u, t))
        assert bounds.gast_degrees.contains(moira_native.apparent_sidereal_time(u, t, dpsi))


def test_random_dpsi_values_include_mixed_signs():
    rng = random.Random(74103)
    ut, tt = 2459891.7, 2459891.7008
    box = I(-0.03, 0.03)
    bounds = bound_conditional_sidereal_time(ut, I.point(0), tt, I.point(0), box, **PREMISES)
    for _ in range(200):
        dpsi = rng.uniform(-0.03, 0.03)
        assert bounds.gast_degrees.contains(julian._apparent_sidereal_time_at_tt.__wrapped__(ut, tt, dpsi))
        assert bounds.gast_degrees.contains(moira_native.apparent_sidereal_time(ut, tt, dpsi))


def test_integer_day_and_modulo_seams_fail_closed():
    with pytest.raises(EnclosureUnavailable):
        bound_conditional_sidereal_time(2459892.0, I(-0.001, 0.001),
                                       2459892.0, I.point(0), I(-0.01, 0.01), **PREMISES)
    # Force the final 0/360 GAST wrap via a supplied, sign-indefinite dpsi.
    with pytest.raises(EnclosureUnavailable, match="modulo"):
        bound_conditional_sidereal_time(2459891.7, I.point(0), 2459891.7,
                                       I.point(0), I(-400, 400), **PREMISES)


def test_invalid_tt_and_bad_premises_are_rejected():
    with pytest.raises(ValueError):
        bound_conditional_sidereal_time(2459891.7, I.point(0), math.nan,
                                       I.point(0), I.point(0), **PREMISES)
    with pytest.raises(EnclosureUnavailable, match="domain"):
        bound_conditional_sidereal_time(2459891.7, I.point(0), 40000001.0,
                                       I.point(0), I.point(0), **PREMISES)


@pytest.mark.parametrize("ut,tt", [(2459891.7, 2459891.7008), (991000.3, 991000.6)])
def test_loaded_nutation_source_composes_into_serving_gast(ut, tt):
    span = I(Fraction(-2, 86400), Fraction(2, 86400))
    bound = bound_conditional_sidereal_from_nutation_tables(
        ut, span, tt, span, assume_registered_tables_and_caches_match=True, **PREMISES,
    )
    assert not bound.source_and_arithmetic_attested
    assert not bound.nutation.registered_tables_attested
    assert not bound.earth_fixed_orientation_certified
    for seconds in (-1, 0, 1):
        u, t = ut + seconds / 86400, tt + seconds / 86400
        dpsi = nutation(t)[0]
        assert bound.nutation.longitude_degrees.contains(dpsi)
        assert bound.sidereal.gast_degrees.contains(
            julian._apparent_sidereal_time_at_tt.__wrapped__(u, t, dpsi)
        )
        assert bound.sidereal.gast_degrees.contains(moira_native.apparent_sidereal_time(u, t, dpsi))

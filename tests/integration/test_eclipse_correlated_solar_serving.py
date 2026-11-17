"""Correlated Moon source boxes include every checked actual split call."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_solar_serving import bound_conditional_solar_serving_vectors
from moira.eclipse import _eclipse_body_pair


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('anchor',[1045155.526661839,2457987.27,2763363.82])
def test_correlated_serving_pair_encloses_literal_calls_over_a_minute(planetary_reader,anchor):
    domain = I(F(-31,86400),F(31,86400))
    independent = bound_conditional_solar_serving_vectors(planetary_reader,anchor,domain,
        tight_norm=True,refined_split_clock=True)
    correlated = bound_conditional_solar_serving_vectors(planetary_reader,anchor,domain,
        tight_norm=True,refined_split_clock=True,correlated_moon=True)
    assert correlated.correlated_moon_used and correlated.split_clock_convergence_conditionally_proved
    for offset in (F(-30,86400),F(0),F(30,86400)):
        native_tt = float(F.from_float(anchor)+offset)
        assert domain.contains(F.from_float(native_tt)-F.from_float(anchor))
        sun,moon = _eclipse_body_pair(native_tt,planetary_reader,sun_retarded=True,moon_retarded=True)
        for value,box in zip(sun,correlated.sun_retarded_km):
            assert box.contains(F.from_float(value))
        for value,box in zip(moon,correlated.moon_retarded_km):
            assert box.contains(F.from_float(value))
    assert max(box.width for box in correlated.moon_retarded_km)<max(box.width for box in independent.moon_retarded_km)/10

"""Copied-record interval calls agree with literal serving and audited boxes."""
from fractions import Fraction as F

import pytest

from moira._eclipse_frozen_native_vectors import freeze_native_vector_scope,bound_frozen_native_vectors
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_solar_serving import bound_conditional_solar_serving_vectors
from moira._eclipse_serving_astro import bound_conditional_lunar_serving_vectors
from moira.eclipse import _eclipse_body_pair


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('anchor',[1045155.526661839,2001312.51,2457987.27,2763363.82])
@pytest.mark.parametrize('retarded',[False,True])
def test_literal_native_calls_and_distinct_adapters_are_enclosed(planetary_reader,anchor,retarded):
    domain = I(F(-31,86400),F(31,86400))
    scope = freeze_native_vector_scope(planetary_reader,anchor,domain)
    new = bound_frozen_native_vectors(scope,domain,moon_retarded=retarded)
    assert new.split_clock_convergence_conditionally_proved
    assert new.distinct_clock_evaluations<new.route_calls
    old = (bound_conditional_solar_serving_vectors(planetary_reader,anchor,domain,
            tight_norm=True,refined_split_clock=True,correlated_moon=True) if retarded else
           bound_conditional_lunar_serving_vectors(planetary_reader,anchor,domain,tight_norm=True))
    old_moon = old.moon_retarded_km if retarded else old.moon_geometric_km
    assert all(a.intersect(b) is not None for a,b in zip(new.sun_retarded_km,old.sun_retarded_km))
    assert all(a.intersect(b) is not None for a,b in zip(new.moon_retarded_km,old_moon))
    for seconds in (-30,0,30):
        tt = anchor+seconds/86400
        sun,moon = _eclipse_body_pair(tt,planetary_reader,sun_retarded=True,moon_retarded=retarded)
        assert all(box.contains(F.from_float(value)) for box,value in zip(new.sun_retarded_km,sun))
        assert all(box.contains(F.from_float(value)) for box,value in zip(new.moon_retarded_km,moon))


@pytest.mark.requires_ephemeris
def test_source_seam_and_outside_request_never_become_absence(planetary_reader):
    scope = freeze_native_vector_scope(planetary_reader,2001312.5,I(F(-1,1000),F(1,1000)))
    with pytest.raises(EnclosureUnavailable,match='record|day'):
        bound_frozen_native_vectors(scope,scope.requested_domain)
    with pytest.raises(ValueError,match='outside'):
        bound_frozen_native_vectors(scope,I.point(1))


@pytest.mark.requires_ephemeris
def test_frozen_scope_can_cross_a_whole_tdb_day(planetary_reader):
    scope = freeze_native_vector_scope(planetary_reader,2459892.,I(F(-1,6),F(1,6)))
    assert scope.clock_convergence_iterations<=4
    for offset in (F(-1,10),F(1,10)):
        result = bound_frozen_native_vectors(scope,I.point(offset))
        assert result.sun_retarded_km and result.moon_retarded_km

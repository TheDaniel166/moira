"""Native phase boxes cover actual selected-policy calls and full controls."""
from fractions import Fraction as F

import pytest

from moira._eclipse_frozen_native_vectors import freeze_native_vector_scope,bound_frozen_native_vectors
from moira._eclipse_native_lunar_stage3 import bound_native_danjon_margins,cover_native_lunar_stage3
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira.eclipse import _eclipse_body_pair
from moira.lunar_shadow_models import danjon_angular_shadow


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('epoch',[1124726.318610764,2001312.523536443,2459891.96])
def test_literal_danjon_calls_are_enclosed_over_a_whole_minute(planetary_reader,epoch):
    domain = I(F(-31,86400),F(31,86400))
    scope = freeze_native_vector_scope(planetary_reader,epoch,domain)
    vectors = bound_frozen_native_vectors(scope,domain,moon_retarded=False)
    margins = bound_native_danjon_margins(vectors.sun_retarded_km,vectors.moon_retarded_km)
    for seconds in (-30,0,30):
        sun,moon = _eclipse_body_pair(epoch+seconds/86400,planetary_reader,sun_retarded=True,moon_retarded=False)
        geometry = danjon_angular_shadow(sun,moon)
        actual = geometry.penumbral_margin,geometry.umbral_margin,geometry.total_margin
        assert all(box.contains(F.from_float(value)) for box,value in zip(margins,actual))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('policy,scale',[('danjon_angular',1.),('static_finite_cone',1.01)])
def test_native_six_contact_control_complete_on_the_whole_domain(planetary_reader,policy,scale):
    domain = I(F(-1,6),F(1,6))
    scope = freeze_native_vector_scope(planetary_reader,2459891.96,domain)
    result = cover_native_lunar_stage3(scope,planetary_reader,domain,policy=policy,earth_radius_scale=scale)
    assert result.all_represented_inputs_covered
    assert all(phase.event_interval_enclosed and len(phase.components)==1 for phase in result.phases)
    assert not result.real_continuity_claimed


def test_outside_antisolar_domain_is_unavailable_not_absent():
    with pytest.raises(EnclosureUnavailable,match='antisolar'):
        bound_native_danjon_margins(tuple(map(I.point,(1.5e8,0,0))),tuple(map(I.point,(4e5,0,0))))

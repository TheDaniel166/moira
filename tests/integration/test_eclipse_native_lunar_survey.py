"""Full requested TT time is checked, including the intervening new moons."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_native_lunar_survey import survey_native_lunar_interval,first_native_lunar_candidate


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('policy,scale',[('danjon_angular',1.),('static_finite_cone',1.01)])
def test_all_34_days_exclude_everything_outside_the_contact_neighborhood(planetary_reader,policy,scale):
    result = survey_native_lunar_interval(planetary_reader,2459891.96,I(-17,17),policy=policy,
        earth_radius_scale=scale,covered_event_domains=(I(F(-3,10),F(3,10)),))
    assert result.all_represented_inputs_resolved
    candidates = [cell for cell in result.cells if cell.status=='candidate']
    assert candidates and all(cell.domain.lo>=F(-3,10) and cell.domain.hi<=F(3,10) for cell in candidates)
    assert any(cell.status=='excluded' and cell.domain.contains(F(-147,10)) for cell in result.cells)
    assert first_native_lunar_candidate(result).status=='candidate'


def test_unsupported_reader_never_becomes_absence():
    domain = I(-17,17)
    result = survey_native_lunar_interval(object(),2459891.96,domain,policy='danjon_angular')
    assert not result.all_represented_inputs_resolved
    assert len(result.cells)==1 and result.cells[0].domain==domain
    assert first_native_lunar_candidate(result).status=='unresolved'

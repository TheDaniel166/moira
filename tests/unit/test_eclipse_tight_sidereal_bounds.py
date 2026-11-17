"""Tight equation-of-equinoxes bounds cover both implemented schedules."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_sidereal_bounds import bound_conditional_sidereal_time,_tight_complementary_terms
from moira import julian,moira_native
from moira.obliquity import nutation


PREMISES = dict(assume_ieee_arithmetic=True,assume_correctly_rounded_integer_powers=True,
                assume_finite_unit_trig=True)


@pytest.mark.parametrize('epoch',[1045155.526661839,2001312.51,2457987.27,2763363.82])
def test_narrow_actual_sidereal_values_cover_python_and_native(epoch):
    domain = I(F(-1,864000),F(1,864000))
    dpsi = I(nutation(epoch)[0]-1e-8,nutation(epoch)[0]+1e-8)
    broad = bound_conditional_sidereal_time(epoch,domain,epoch,domain,dpsi,**PREMISES)
    tight = bound_conditional_sidereal_time(epoch,domain,epoch,domain,dpsi,
        tight_equation_of_equinoxes=True,**PREMISES)
    assert tight.gast_degrees.width<broad.gast_degrees.width
    point_broad = bound_conditional_sidereal_time(epoch,I.point(0),epoch,I.point(0),dpsi,**PREMISES)
    point_tight = bound_conditional_sidereal_time(epoch,I.point(0),epoch,I.point(0),dpsi,
        tight_equation_of_equinoxes=True,**PREMISES)
    assert point_tight.gast_degrees.width<point_broad.gast_degrees.width/100
    for seconds in (-.099,0,.099):
        jd = epoch+seconds/86400
        dp = nutation(jd)[0]
        assert dpsi.contains(dp)
        assert tight.gast_degrees.contains(julian._apparent_sidereal_time_at_tt.__wrapped__(jd,jd,dp))
        assert tight.gast_degrees.contains(moira_native.apparent_sidereal_time(jd,jd,dp))


@pytest.mark.parametrize('centuries',[-50,-30,0,20,50])
def test_complementary_terms_include_literal_python_schedule(centuries):
    box = I(F(centuries)-F(1,10**8),F(centuries)+F(1,10**8))
    result = _tight_complementary_terms(box)
    for offset in (-.9e-8,0,.9e-8):
        jd = 2451545.+(centuries+offset)*36525
        assert result.contains(julian._gast_complementary_terms(jd))

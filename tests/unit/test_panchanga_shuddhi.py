"""Independent source-table expectations and mathematical boundary tests."""
from dataclasses import replace
from fractions import Fraction
from itertools import product
import json
import math
from pathlib import Path

import pytest

import moira
import moira.facade as facade
import moira.vedic as vedic
import moira.panchanga_shuddhi as sh
from moira.muhurta import tara_bala
from moira.panchanga import YOGA_NAMES

SOURCE = json.loads((Path(__file__).parents[1]/'fixtures/panchanga_shuddhi_sources.json').read_text())


def interval(a, b, uncertainty=0):
    def point(x):
        return sh.ShuddhiBoundary('fixture', x, x-uncertainty, x+uncertainty)
    return sh.ShuddhiInterval(point(a), point(b))


def finding(result, name):
    return next(f for f in result.findings if f.rule_id == name)


def test_all_panchaka_inputs_against_independent_kalaprakasika_offsets():
    count = 0
    for numbers in product(range(1,31), range(1,8), range(1,28), range(1,13)):
        expected = [label for offset,label in SOURCE['kalaprakasika_offsets'] if (sum(numbers)+offset)%9==5]
        result = sh.panchaka_rahita(*numbers)
        assert result.category == (expected[0] if expected else 'rahita')
        count += 1
    assert count == 68040
    for *numbers,remainder,label in SOURCE['panchaka_examples']:
        result = sh.panchaka_rahita(*numbers)
        assert (result.remainder,result.category) == (remainder,label)


@pytest.mark.parametrize('profile',[sh.MC_TARA,sh.PS_TARA])
def test_all_natal_transit_stars_and_quarters(profile):
    policy = sh.PanchangaShuddhiPolicy(tara_profile=profile)
    seconds = dict(SOURCE['mc_second_cycle_padas'])
    for natal,transit,pada in product(range(27),range(27),range(1,5)):
        count = (transit-natal)%27+1
        moon = (transit*4+pada-.5)*10/3
        result = sh.panchanga_shuddhi_from_longitudes(0,moon,natal_nakshatra_index=natal,policy=policy)
        base = tara_bala(natal,transit)
        assert result.values.base_tara_polarity == base.polarity
        assert (result.values.tara_count,result.values.pada) == (count,pada)
        f = finding(result,'tara_cycle')
        if profile == sh.PS_TARA:
            assert f.detected == (count in SOURCE['sastri_restricted_counts'])
        elif count in (1,10,19):
            assert f.state == 'not_evaluated' and f.detected is None
        else:
            assert f.detected == (count in (3,5,7) or seconds.get(count)==pada)
            if count in (21,23,25):
                assert f.state == 'exception_applies'


@pytest.mark.parametrize('name',YOGA_NAMES)
def test_every_yoga_and_initial_end_ownership(name):
    longitude = (YOGA_NAMES.index(name)+.5)*40/3
    span = interval(100,101.2)
    def at(jd):
        return finding(sh.panchanga_shuddhi_from_longitudes(0,longitude,jd_ut1=jd,yoga_span=span),'nitya_yoga')
    if name in SOURCE['yoga_initial_ghatis']:
        end = 100+SOURCE['yoga_initial_ghatis'][name]/60
        assert at(100).state=='restricted'
        assert at(math.nextafter(end,-math.inf)).state=='restricted'
        assert at(end).state=='clear'
        assert at(end).windows[0].end.jd_ut1==end
    elif name == SOURCE['yoga_half']:
        assert at(100.59).state=='restricted' and at(100.6).state=='clear'
    else:
        assert at(100.9).state==('restricted' if name in SOURCE['yoga_whole'] else 'clear')


def test_yoga_capping_missing_span_and_uncertainty():
    assert finding(sh.panchanga_shuddhi_from_longitudes(0,1),'nitya_yoga').state=='unavailable'
    result=sh.panchanga_shuddhi_from_longitudes(0,1,jd_ut1=100.005,yoga_span=interval(100,100.01))
    assert finding(result,'nitya_yoga').windows[0].end.jd_ut1==100.01
    result=sh.panchanga_shuddhi_from_longitudes(0,1,jd_ut1=100.05,yoga_span=interval(100,101,.000001))
    assert finding(result,'nitya_yoga').state=='uncertain'


@pytest.mark.parametrize('row',SOURCE['bhadra_tithi_mouth_tail'])
@pytest.mark.parametrize('duration',[.8,1,1.2])
def test_bhadra_table_with_unequal_actual_karana_halves(row,duration):
    tithi,mouth,tail=row
    karana = next(k for k in (7,14,21,28,35,42,49,56) if k//2==tithi-1)
    a,b=100.,100.+duration
    split=a+duration*.49
    kspan=interval(split,b) if karana%2 else interval(a,split)
    result=sh.panchanga_shuddhi_from_longitudes(0,karana*6+3,
        jd_ut1=(kspan.start.jd_ut1+kspan.end.jd_ut1)/2,tithi_span=interval(a,b),karana_span=kspan)
    for rule,left,right in (
        ('bhadra_mouth',Fraction(mouth-1,8),Fraction(mouth-1,8)+Fraction(1,12)),
        ('bhadra_tail',Fraction(tail,8)-Fraction(1,20),Fraction(tail,8))):
        f=finding(result,rule)
        raw=f.unclipped_windows[0]
        expected=[float(Fraction(a)*(1-x)+Fraction(b)*x) for x in (left,right)]
        assert [raw.start.jd_ut1,raw.end.jd_ut1]==expected
        if f.windows:
            clipped=f.windows[0]
            assert clipped.start.jd_ut1==max(expected[0],kspan.start.jd_ut1)
            assert clipped.end.jd_ut1==min(expected[1],kspan.end.jd_ut1)


def test_all_bhadra_residences_origin_exceptions_and_nonvishti():
    for residence, signs in SOURCE['residence_signs_1based'].items():
        for sign,karana,daytime in product(signs,range(60),(False,True)):
            moon=(sign-.5)*30
            sun=(moon-(karana+.5)*6)%360
            r=sh.panchanga_shuddhi_from_longitudes(sun,moon,is_daytime=daytime)
            present=karana in (7,14,21,28,35,42,49,56)
            assert finding(r,'bhadra_presence').detected==present
            assert r.values.bhadra_residence==(residence if present else None)
            if present:
                assert finding(r,'bhadra_day_night_exception').detected==((karana%2==1)==daytime)
                assert finding(r,'karana_auspicious_prohibition').state=='restricted'
                assert r.simultaneous_bhadra_claims==(residence!='earth' or (karana%2==1)==daytime)


def test_catalogue_fixed_karanas_and_exports():
    catalogue=sh.panchanga_shuddhi_catalogue()
    assert [x.name for x in catalogue.karanas]==SOURCE['karana_order']
    assert len(catalogue.profiles)==7 and len(set(x.name for x in catalogue.profiles))==7
    assert 'auspicious' in next(x for x in catalogue.karanas if x.name=='Kimstughna').tags
    for name in sh.__all__:
        assert getattr(moira,name) is getattr(vedic,name) is getattr(facade,name) is getattr(sh,name)
        assert name in moira.__all__ and name in vedic.__all__ and name in facade.__all__


@pytest.mark.parametrize('kwargs',[
    {'sun_sidereal_longitude':None},{'moon_sidereal_longitude':True},
    {'moon_sidereal_longitude':'1'},{'moon_sidereal_longitude':float('inf')},
    {'moon_sidereal_longitude':360},{'weekday':True},{'weekday':7},
    {'natal_nakshatra_index':27},{'is_daytime':1},{'lagna_sidereal_longitude':-1},
    {'policy':{}},{'yoga_span':interval(1,2)}, {'jd_ut1':3,'yoga_span':interval(1,2)},
    {'jd_ut1':1.5,'tithi_span':interval(1,2),'karana_span':interval(.5,1.8)},
])
def test_strict_admission(kwargs):
    values={'sun_sidereal_longitude':0,'moon_sidereal_longitude':45,**kwargs}
    with pytest.raises(ValueError):
        sh.panchanga_shuddhi_from_longitudes(**values)


def test_boundary_half_open_and_vessel_invariants():
    span=interval(1,2)
    assert span.contains(1) and not span.contains(2)
    assert interval(1,2,.00001).contains(1) is None
    with pytest.raises(ValueError):
        replace(sh.panchaka_rahita(1,1,1,1),remainder=0)
    result=sh.panchanga_shuddhi_from_longitudes(0,45)
    with pytest.raises(ValueError):
        replace(result,simultaneous_bhadra_claims=False)
    with pytest.raises(ValueError):
        replace(result,policy=None)
    with pytest.raises(ValueError):
        replace(result,findings=list(result.findings))
    with pytest.raises(ValueError):
        replace(result.findings[0],state='clear',detected=None)
    with pytest.raises(ValueError):
        replace(result.findings[0],profile=sh.MC_TARA)


def test_adaptive_sector_solver_wraps_and_fails_closed():
    from moira._panchanga_shuddhi_day import _crossings, _bands
    roots=_crossings(lambda t:(359+720*t)%360,12,0,.1,.01,.1,'fast')
    assert len(roots)==3
    for b,angle in zip(roots,(360,390,420)):
        expected=(angle-359)/720
        assert b.lower_jd_ut1<=expected<=b.upper_jd_ut1
        assert (b.upper_jd_ut1-b.lower_jd_ut1)*86400<=.1
    with pytest.raises(ValueError,match='nonmonotonic'):
        _crossings(lambda t:(20-t)%360,12,0,.1,.01,.1,'backward')
    a=sh.ShuddhiBoundary('a',1,1,1.000001)
    b=sh.ShuddhiBoundary('b',1.000001,1.0000005,1.000002)
    merged=_bands([a,b])
    assert len(merged)==1 and merged[0].kind=='a+b'

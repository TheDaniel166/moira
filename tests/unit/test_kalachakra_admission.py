"""Hostile direct inputs and forged-result contracts."""
from dataclasses import replace
from fractions import Fraction as F
import math
import pytest
from moira.kalachakra import (
    KalachakraSeed, KalachakraInputError, KalachakraEpoch, KalachakraProjection,
    kalachakra_sequence, kalachakra_profiles, project_kalachakra_sequence, current_kalachakra_periods,
)
from moira.kalachakra_policy import PROFILE_ID


@pytest.mark.parametrize('bad',[True,False,'12',None,[],{},F(1,3),float('nan'),float('inf'),-1,360,10**1000])
def test_bad_longitude(bad):
    with pytest.raises(KalachakraInputError):
        KalachakraSeed('sidereal',bad)


@pytest.mark.parametrize('bad',[True,False,0,3,2.0,'2',None,1000000])
def test_bad_depth_before_resources(bad,monkeypatch):
    monkeypatch.setattr('moira._kalachakra_astronomy.derive',lambda *a: pytest.fail('unexpected astronomy'))
    with pytest.raises(KalachakraInputError):
        kalachakra_sequence(KalachakraSeed('sidereal',0),profile_id=PROFILE_ID,levels=bad)


def test_candidates_and_incompatible_branches():
    for p in kalachakra_profiles().profiles:
        if p.selectable:
            continue
        assert not p.selectable
        with pytest.raises(KalachakraInputError):
            kalachakra_sequence(KalachakraSeed('sidereal',0),profile_id=p.profile_id)
    with pytest.raises(KalachakraInputError):
        KalachakraSeed('sidereal',0,'Lahiri')
    with pytest.raises(KalachakraInputError):
        KalachakraSeed('tropical',0)
    with pytest.raises(KalachakraInputError):
        kalachakra_sequence(KalachakraSeed('tropical',0,'Lahiri'),profile_id=PROFILE_ID)
    with pytest.raises(KalachakraInputError):
        KalachakraProjection('tropical_365.2422')
    with pytest.raises(KalachakraInputError):
        kalachakra_sequence(KalachakraSeed('sidereal',0),profile_id=PROFILE_ID,projection=KalachakraProjection('savana_360'))


@pytest.mark.parametrize('field,value',[
    ('profile_id','unadmitted'),('levels',True),('generated_node_count',9),
    ('visible_node_count',0),('eligibility_status','eligible'),('conflict_ids',()),
    ('rule_ids',()),('profile_version','unknown'),('periods',()),('transitions',()),
])
def test_sequence_construction_revalidates(field,value):
    r = kalachakra_sequence(KalachakraSeed('sidereal',45.8),profile_id=PROFILE_ID)
    with pytest.raises(KalachakraInputError):
        replace(r,**{field:value})


@pytest.mark.parametrize('field,value',[
    ('row_position',False),('path',(8,)),('parent_path',(1,)),('ruler','Moon'),
    ('md_cycle_index',5),('denominator',83),('children',()),('row_id','A2/2'),
])
def test_forged_frozen_period_rejected(field,value):
    r = kalachakra_sequence(KalachakraSeed('sidereal',34.8),profile_id=PROFILE_ID)
    object.__setattr__(r.periods[0],field,value)
    with pytest.raises(KalachakraInputError):
        project_kalachakra_sequence(r,birth_epoch=KalachakraEpoch('jd_utc',2451545),year_basis='savana_360')


def test_forged_recursive_tree_bounded():
    r = kalachakra_sequence(KalachakraSeed('sidereal',0),profile_id=PROFILE_ID)
    object.__setattr__(r.periods[0].children[0],'children',(r.periods[0],)*9)
    with pytest.raises(KalachakraInputError):
        project_kalachakra_sequence(r,birth_epoch=KalachakraEpoch('jd_utc',2451545),year_basis='savana_360')


def test_smallest_float_exact_ratios_fit_contract():
    r = kalachakra_sequence(KalachakraSeed('sidereal',math.ulp(0.0)),profile_id=PROFILE_ID)
    assert r.birth.fraction_in_pada > 0
    for md in r.periods:
        for p in (md,*md.children):
            for value in (p.full_years.start,p.full_years.end):
                assert max(len(str(abs(value.numerator))),len(str(value.denominator))) < 400


def test_current_constructor_and_serializer_revalidate_line():
    from moira.kalachakra import KalachakraInvariantError
    from moira_server.serializers.kalachakra import serialize_current
    epoch = KalachakraEpoch('jd_utc',2451545)
    r = kalachakra_sequence(KalachakraSeed('sidereal',45.8),profile_id=PROFILE_ID,
        birth_epoch=epoch,projection=KalachakraProjection('savana_360'))
    current = current_kalachakra_periods(r,epoch)
    with pytest.raises(KalachakraInputError):
        replace(current,status='before_birth')
    with pytest.raises(KalachakraInputError):
        replace(current,active_line=())
    object.__setattr__(current.active_line[0],'sign_index',0)
    with pytest.raises(KalachakraInvariantError):
        serialize_current(current)


def test_public_birth_and_period_constructors_validate():
    r = kalachakra_sequence(KalachakraSeed('sidereal',45.8),profile_id=PROFILE_ID)
    with pytest.raises(KalachakraInputError):
        replace(r.birth,deha_sign_index=0)
    with pytest.raises(KalachakraInputError):
        replace(r.periods[0],children=r.periods[0].children[:8])
    with pytest.raises(KalachakraInputError):
        replace(r.periods[0].children[0],md_cycle_index=True)

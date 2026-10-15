"""Clock projection and half-open lookup; rounding never edits source periods."""
from dataclasses import replace
from datetime import datetime,timezone
from fractions import Fraction as F
import math
import pytest
from moira.kalachakra import (
    KalachakraSeed, KalachakraEpoch, KalachakraInputError, KalachakraProjectionError,
    kalachakra_sequence, project_kalachakra_sequence, current_kalachakra_periods,
)
from moira.kalachakra_policy import PROFILE_ID


@pytest.mark.parametrize('basis,days',[('savana_360',F(360)),('julian_365.25',F(1461,4))])
def test_projection_and_every_endpoint(basis,days):
    source = kalachakra_sequence(KalachakraSeed('sidereal',45.8),profile_id=PROFILE_ID)
    r = project_kalachakra_sequence(source,birth_epoch=KalachakraEpoch('jd_utc',2451545),year_basis=basis)
    assert r.birth == source.birth and r.projection.year_days == days
    for md in r.periods:
        for p in (md,*md.children):
            assert p.full_dates.start_jd_utc == float(F(2451545)+p.full_years.start*days)
            assert p.full_dates.end_jd_utc == float(F(2451545)+p.full_years.end*days)
            if p.visible_dates:
                t = p.visible_dates.start_jd_utc
                current = current_kalachakra_periods(r,KalachakraEpoch('jd_utc',t))
                assert p.path in [a.path for a in current.active_line]
                assert len(current.active_line) == 2
                before = current_kalachakra_periods(r,KalachakraEpoch('jd_utc',math.nextafter(t,-math.inf)))
                assert p.path not in [a.path for a in before.active_line]
                after = current_kalachakra_periods(r,KalachakraEpoch('jd_utc',math.nextafter(t,math.inf)))
                assert p.path in [a.path for a in after.active_line]
        assert md.children[0].full_dates.start_jd_utc == md.full_dates.start_jd_utc
        assert md.children[-1].full_dates.end_jd_utc == md.full_dates.end_jd_utc
    end = r.coverage_dates.end_jd_utc
    assert current_kalachakra_periods(r,KalachakraEpoch('jd_utc',end)).status == 'after_coverage'
    assert current_kalachakra_periods(r,KalachakraEpoch('jd_utc',math.nextafter(end,-math.inf))).status == 'active'
    assert current_kalachakra_periods(r,KalachakraEpoch('jd_utc',2451544)).status == 'before_birth'


def test_source_success_independent_of_projection_precision():
    # Just before the first 7/100 source-year cutover in the first pada.
    lon = math.nextafter(float(F(7,30)),-math.inf)
    r = kalachakra_sequence(KalachakraSeed('sidereal',lon),profile_id=PROFILE_ID)
    assert 0 < r.birth.birth_md_remaining_years < F(1,10**10)
    with pytest.raises(KalachakraProjectionError):
        project_kalachakra_sequence(r,birth_epoch=KalachakraEpoch('jd_utc',2451545),year_basis='savana_360')
    assert len(r.periods) == 9
    for huge in (1e308,-1e308):
        with pytest.raises(KalachakraProjectionError):
            project_kalachakra_sequence(r,birth_epoch=KalachakraEpoch('jd_utc',huge),year_basis='savana_360')


def test_epoch_and_clock_identity():
    r = kalachakra_sequence(KalachakraSeed('sidereal',10),profile_id=PROFILE_ID,levels=1)
    with pytest.raises(KalachakraInputError):
        current_kalachakra_periods(r,KalachakraEpoch('jd_utc',2451545))
    with pytest.raises(KalachakraInputError):
        KalachakraEpoch('datetime',datetime(2000,1,1))
    a = project_kalachakra_sequence(r,birth_epoch=KalachakraEpoch('datetime',datetime(2000,1,1,12,tzinfo=timezone.utc)),year_basis='savana_360')
    b = project_kalachakra_sequence(r,birth_epoch=KalachakraEpoch('jd_utc',2451545),year_basis='savana_360')
    assert a.periods == b.periods
    assert len(current_kalachakra_periods(a,KalachakraEpoch('jd_utc',2451545)).active_line) == 1
    with pytest.raises(KalachakraInputError):
        project_kalachakra_sequence(a,birth_epoch=KalachakraEpoch('jd_utc',2451546),year_basis='savana_360')
    with pytest.raises(KalachakraInputError):
        replace(a,projection=replace(a.projection,year_days=F(365)))

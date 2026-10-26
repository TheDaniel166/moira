"""Rao's source windows, boundaries, projection and hostile aggregate admission."""
from dataclasses import replace
from datetime import datetime,timezone
from fractions import Fraction as F
import math

import pytest

from moira import Moira
from moira.kalachakra import (
    KalachakraSeed,KalachakraEpoch,KalachakraProjection,KalachakraInputError,
    KalachakraInvariantError,kalachakra_sequence,project_kalachakra_sequence,
    current_kalachakra_periods,
)
from moira.kalachakra_policy import PROFILE_ID,RAO_PROFILE_ID
from moira_server.serializers.kalachakra import serialize_sequence,serialize_current
from tests.unit.test_kalachakra_rao_sources import DATA,SIGNS,WEIGHTS,source_seed,source_window


def sequence(lon,levels=2):
    return kalachakra_sequence(KalachakraSeed('sidereal',lon),profile_id=RAO_PROFILE_ID,levels=levels)


@pytest.mark.parametrize('case',DATA['balances'],ids=lambda c:c['id'])
def test_worked_examples(case):
    d,m,s = case['dms']
    exact = F(d)+F(m,60)+F(s,3600)
    lon = float(exact)
    expected = source_seed(F(lon))
    r = sequence(lon)
    assert r.profile_id == RAO_PROFILE_ID and r.profile_version == 'ved014.rao2000.1'
    assert r.birth.row_id == f"R2000/{case['group']}/{case['pada']}"
    assert r.birth.birth_row_position == case['position']
    assert r.birth.elapsed_row_years == expected['elapsed']
    assert r.birth.birth_md_remaining_years == expected['balance']
    assert r.coverage.end == expected['coverage']
    assert abs(expected['balance']-F(case['balance'])) <= abs(F(lon)-exact)*F(3*expected['total'],10)
    assert [SIGNS[p.sign_index] for p in r.periods] == case['sequence'].split()
    assert SIGNS[r.birth.deha_sign_index] == case['deha']
    assert SIGNS[r.birth.jeeva_sign_index] == case['jeeva']
    assert r.birth.deha_jeeva_reference == 'birth_nine_md_window'
    if case['id']=='example95':
        active = next(c for c in r.periods[0].children if c.visible_years is not None)
        assert active.path == (0,3) and SIGNS[active.sign_index] == 'Le'
        assert abs(active.visible_years.end-F(17,50)) <= abs(F(lon)-exact)*F(3*83,10)


@pytest.mark.parametrize('k',range(108))
def test_every_pada_boundaries_and_full_partitions(k):
    edge = float(F(10*k,3))
    for lon in (math.nextafter(edge,-math.inf),edge,math.nextafter(edge,math.inf),float(F(10*k+5,3))):
        if not 0 <= lon < 360:
            continue
        expected = source_seed(F(lon))
        r = sequence(lon)
        b = r.birth
        assert (b.group,b.pada_number,b.birth_row_position) == (expected['group'],expected['pada'],expected['position'])
        assert b.birth_md_remaining_years == expected['balance']
        assert r.coverage.end == expected['coverage']
        assert [SIGNS[p.sign_index] for p in r.periods] == list(expected['sequence'])
        assert len({p.path for md in r.periods for p in (md,*md.children)}) == r.generated_node_count == 90
        cursor = b.birth_md_remaining_years-b.birth_md_full_years
        origin = (4*(int(b.group[1])-1)+b.pada_number-1)*9+b.birth_row_position
        for m,md in enumerate(r.periods):
            cycle,within = divmod(origin+m,72)
            row,pos = divmod(within,9)
            assert (md.row_id,md.row_position,md.md_cycle_index) == (f'R2000/{b.group[0]}{row//4+1}/{row%4+1}',pos,cycle)
            assert md.full_years.start == cursor
            cursor += WEIGHTS[SIGNS[md.sign_index]]
            assert md.full_years.end == cursor
            child_signs = source_window(b.group,b.pada_number,b.birth_row_position+m)
            denominator = sum(WEIGHTS[s] for s in child_signs)
            assert [SIGNS[c.sign_index] for c in md.children] == list(child_signs)
            child_cursor = md.full_years.start
            for a,c in enumerate(md.children):
                assert c.denominator == denominator
                assert c.full_years.start == child_cursor
                child_cursor += F(md.weight*WEIGHTS[child_signs[a]],denominator)
                assert c.full_years.end == child_cursor
                assert c.md_cycle_index == md.md_cycle_index
                if child_cursor <= 0:
                    assert c.visible_years is None
                else:
                    assert (c.visible_years.start,c.visible_years.end) == (max(F(0),c.full_years.start),child_cursor)
            assert child_cursor == md.full_years.end
            assert sum((c.visible_years.end-c.visible_years.start for c in md.children if c.visible_years),F()) == md.visible_years.end-md.visible_years.start
        assert cursor == r.coverage.end


def test_all_row_occurrence_cutovers_and_bounded_denominators():
    from moira._kalachakra_recipes import DENOMINATORS
    seen = {1}
    for group,members in DATA['groups'].items():
        for pada in range(1,5):
            start = F(10*((members[0]-1)*4+pada-1),3)
            row = source_window(group,pada,0)
            total = sum(WEIGHTS[s] for s in row)
            cursor = 0
            for pos,sign in enumerate(row):
                seen.add(sum(WEIGHTS[s] for s in source_window(group,pada,pos)))
                boundary = float(start+F(10*cursor,3*total))
                for lon in (math.nextafter(boundary,-math.inf),boundary,math.nextafter(boundary,math.inf)):
                    if not 0 <= lon < 360:
                        continue
                    b = sequence(lon,1).birth
                    expected = source_seed(F(lon))
                    assert (b.group,b.pada_number,b.birth_row_position,b.birth_md_remaining_years) == (
                        expected['group'],expected['pada'],expected['position'],expected['balance'])
                cursor += WEIGHTS[sign]
    assert seen == set(DENOMINATORS)


@pytest.mark.parametrize('basis',['savana_360','julian_365.25'])
def test_projected_endpoints_current_and_profile_preservation(basis):
    s = sequence(45+50/60)
    epoch = KalachakraEpoch('jd_utc',2451545)
    r = project_kalachakra_sequence(s,birth_epoch=epoch,year_basis=basis)
    assert r.profile_id == RAO_PROFILE_ID and r.birth == s.birth
    assert r.rule_ids == s.rule_ids and r.conflict_ids == s.conflict_ids
    for md in r.periods:
        for p in (md,*md.children):
            assert p.full_dates.end_jd_utc == float(F(2451545)+p.full_years.end*r.projection.year_days)
            if p.visible_dates is None:
                continue
            t = p.visible_dates.start_jd_utc
            for q,belongs in ((math.nextafter(t,-math.inf),False),(t,True),(math.nextafter(t,math.inf),True)):
                current = current_kalachakra_periods(r,KalachakraEpoch('jd_utc',q))
                assert current.profile_id == RAO_PROFILE_ID
                assert (p.path in [a.path for a in current.active_line]) == belongs
    assert current_kalachakra_periods(r,KalachakraEpoch('jd_utc',r.coverage_dates.end_jd_utc)).status=='after_coverage'
    assert Moira.current_kalachakra_periods(object(),r,epoch) == current_kalachakra_periods(r,epoch)


def test_directed_gati_belongs_to_selected_profile():
    seen = {'S':set(),'A':set()}
    for group,members in DATA['groups'].items():
        for pada in range(4):
            r = sequence(float(F(10*((members[0]-1)*4+pada)+5,3)))
            labels = {tuple(pair):name for name,pairs in DATA['gati'][group[0]].items() for pair in pairs}
            for edge in r.transitions:
                pair = (SIGNS[edge.source_sign_index],SIGNS[edge.destination_sign_index])
                assert edge.rule_id == 'R2000_GATI' and not edge.conflict_ids
                assert edge.classification == labels.get(pair)
                assert edge.classification_status == ('classified' if pair in labels else 'not_classified_by_profile')
                seen[group[0]].add(pair)
        assert set(labels) <= seen[group[0]]
    old = kalachakra_sequence(KalachakraSeed('sidereal',0),profile_id=PROFILE_ID)
    assert any(e.classification_status=='unresolved_source_conflict' and e.conflict_ids==('KC-10',) for e in old.transitions)


@pytest.mark.parametrize('field,value',[
    ('profile_id',PROFILE_ID),('profile_version','ved014.1'),('source_ids',('L02',)),
    ('rule_ids',()),('conflict_ids',()),
])
def test_rao_aggregate_cannot_claim_another_recipe(field,value):
    r = sequence(45.8)
    with pytest.raises(KalachakraInputError):
        replace(r,**{field:value})
    object.__setattr__(r,field,value)
    with pytest.raises(KalachakraInvariantError):
        serialize_sequence(r)


def test_periods_reject_wrong_denominators_rows_and_forged_current():
    r = sequence(45.8)
    with pytest.raises(KalachakraInputError):
        replace(r.birth,deha_jeeva_reference='natal_row')
    with pytest.raises(KalachakraInputError):
        replace(r.periods[1].children[0],denominator=83)
    epoch = KalachakraEpoch('jd_utc',2451545)
    projected = project_kalachakra_sequence(r,birth_epoch=epoch,year_basis='savana_360')
    current = current_kalachakra_periods(projected,epoch)
    object.__setattr__(current,'profile_id',PROFILE_ID)
    with pytest.raises(KalachakraInvariantError):
        serialize_current(current)
    object.__setattr__(r.periods[0],'row_id',r.periods[0].row_id.removeprefix('R2000/'))
    with pytest.raises(KalachakraInputError):
        project_kalachakra_sequence(r,birth_epoch=epoch,year_basis='savana_360')


@pytest.mark.requires_ephemeris
def test_real_reader_facade_and_supplied_seed_parity(moira_engine):
    dt = datetime(2000,1,1,12,tzinfo=timezone.utc)
    derived = moira_engine.kalachakra_for_datetime(dt,profile_id=RAO_PROFILE_ID,
        ayanamsa_system='Lahiri',projection=KalachakraProjection('savana_360'))
    direct = kalachakra_sequence(KalachakraSeed('sidereal',derived.provenance.moon_sidereal_lon),
        profile_id=RAO_PROFILE_ID,birth_epoch=KalachakraEpoch('datetime',dt),projection=KalachakraProjection('savana_360'))
    tropical = moira_engine.kalachakra_sequence(KalachakraSeed('tropical',derived.provenance.moon_tropical_lon,'Lahiri'),
        profile_id=RAO_PROFILE_ID,birth_epoch=KalachakraEpoch('datetime',dt),projection=KalachakraProjection('savana_360'))
    assert derived.periods == direct.periods == tropical.periods
    assert derived.provenance.astronomy.planetary_ephemeris=='DE441'
    assert serialize_sequence(derived).profile_id == RAO_PROFILE_ID

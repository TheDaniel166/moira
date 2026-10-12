"""Independent fixture and exact partition checks for the selected profile."""
from fractions import Fraction as F
import math
import pytest
from moira.kalachakra import KalachakraSeed, kalachakra_sequence
from moira.kalachakra_policy import PROFILE_ID, ROWS, GROUPS, WEIGHTS
from tests.unit.test_kalachakra_sources import DATA, SIGNS, WEIGHTS as SOURCE_WEIGHTS, source_seed


def sequence(lon, levels=2):
    return kalachakra_sequence(KalachakraSeed('sidereal',lon),profile_id=PROFILE_ID,levels=levels)


def test_catalogue_independent_transcription():
    assert dict(GROUPS) == {g:tuple(ns) for g,ns in DATA['groups'].items()}
    assert WEIGHTS == tuple(DATA['weights'])
    for group,pada,text,total,deha,jeeva in DATA['rows']:
        assert ROWS[f'{group}/{pada}'] == tuple(SIGNS.index(s) for s in text.split())


@pytest.mark.parametrize('case',DATA['balances'],ids=lambda c:c['id'])
def test_published_balance_and_float_conversion(case):
    d,m,s = case['dms']
    exact = F(d)+F(m,60)+F(s,3600)
    lon = float(exact)
    result = sequence(lon)
    row,index,elapsed,remaining = source_seed(F(lon))
    birth = result.birth
    assert (birth.group,birth.pada_number,birth.birth_row_position) == (case['group'],case['pada'],case['position'])
    assert birth.elapsed_row_years == elapsed and birth.birth_md_remaining_years == remaining
    # Only input conversion accounts for deviation from the exact sexagesimal witness.
    assert abs(remaining-F(case['balance'])) <= abs(F(lon)-exact)*F(3*row[3],10)
    if 'sequence' in case:
        assert [SIGNS[p.sign_index] for p in result.periods] == case['sequence'].split()
    if case['id'] == 'pvr95_shared_balance':
        # BPHS AD ordering differs from Rao. Independently accumulate natal-row weights.
        signs = row[2].split()
        cursor = remaining-SOURCE_WEIGHTS[signs[index]]
        visible = []
        for a in range(9):
            right = cursor+F(7*SOURCE_WEIGHTS[signs[(index+a)%9]],83)
            if right > 0:
                visible.append((a,signs[(index+a)%9],max(F(0),cursor),right))
            cursor = right
        actual = [(p.path[1],SIGNS[p.sign_index],p.visible_years.start,p.visible_years.end)
                  for p in result.periods[0].children if p.visible_years is not None]
        assert actual == visible
        assert actual[0][1] != DATA['comparators']['rao_ex95_active_AD_sign']


@pytest.mark.parametrize('k',range(108))
def test_every_pada_and_adjacent_binary_values(k):
    boundary = float(F(10*k,3))
    for lon in (math.nextafter(boundary,-math.inf),boundary,math.nextafter(boundary,math.inf),float(F(10*k+5,3))):
        if not 0 <= lon < 360:
            continue
        expected,index,elapsed,remaining = source_seed(F(lon))
        r = sequence(lon)
        assert r.birth.row_id == f'{expected[0]}/{expected[1]}'
        assert r.birth.birth_row_position == index
        assert r.birth.elapsed_row_years == elapsed
        assert r.birth.birth_md_remaining_years == remaining
        assert r.generated_node_count == 90
        assert len({p.path for md in r.periods for p in (md,*md.children)}) == 90
        assert len(r.transitions) == 80
        assert r.periods[0].visible_years.start == 0
        assert r.periods[-1].visible_years.end == r.birth.coverage_years
        for m,md in enumerate(r.periods):
            assert md.row_position == (index+m)%9
            assert md.md_cycle_index == (index+m)//9
            assert md.children[0].full_years.start == md.full_years.start
            assert md.children[-1].full_years.end == md.full_years.end
            assert sum((p.full_years.end-p.full_years.start for p in md.children),F(0)) == md.weight
            assert sum((p.visible_years.end-p.visible_years.start for p in md.children if p.visible_years),F(0)) == md.visible_years.end-md.visible_years.start
            for a,c in enumerate(md.children):
                assert c.md_cycle_index == md.md_cycle_index
                assert c.row_position == (md.row_position+a)%9
                assert c.full_years.end-c.full_years.start == F(md.weight*c.weight,r.birth.row_total_years)
                if a:
                    assert md.children[a-1].full_years.end == c.full_years.start
            if m:
                assert r.periods[m-1].full_years.end == md.full_years.start


@pytest.mark.parametrize('row',DATA['rows'],ids=lambda r:f'{r[0]}_{r[1]}')
def test_every_within_row_cutover(row):
    group,pada,text,total,deha,jeeva = row
    n = DATA['groups'][group][0]
    start = F(10*((n-1)*4+pada-1),3)
    cumulative = 0
    for sign in text.split():
        exact = start+F(10*cumulative,3*total)
        marker = float(exact)
        for lon in (math.nextafter(marker,-math.inf),marker,math.nextafter(marker,math.inf)):
            if 0 <= lon < 360:
                expected,index,elapsed,remaining = source_seed(F(lon))
                r = sequence(lon,1)
                assert r.birth.row_id == f'{expected[0]}/{expected[1]}'
                assert r.birth.birth_row_position == index
                assert r.birth.birth_md_remaining_years == remaining
                assert r.generated_node_count == 9
        cumulative += SOURCE_WEIGHTS[sign]


def test_gati_direction_seams_visibility_and_terminal():
    seen = set()
    for k in range(108):
        r = sequence(float(F(10*k+8,3)))
        for edge in r.transitions:
            pair = edge.source_sign_index,edge.destination_sign_index
            if edge.row_seam:
                assert edge.classification_status == 'row_seam_not_classified'
                assert edge.classification is None
            elif pair in ((3,4),(4,3)):
                assert edge.classification_status == 'unresolved_source_conflict'
                assert edge.conflict_ids == ('KC-10',)
                assert edge.classification is None
                seen.add(pair)
            elif edge.classification:
                assert pair in ((5,3),(4,2),(11,7),(8,0))
                seen.add(pair)
            else:
                assert edge.classification_status == 'not_classified_by_profile'
            assert edge.visible == (0 <= edge.boundary_years < r.coverage.end)
            assert edge.destination_path != (9,)
            if edge.level == 2:
                assert edge.source_path[0] == edge.destination_path[0]
    assert seen == {(3,4),(4,3),(5,3),(4,2),(11,7),(8,0)}

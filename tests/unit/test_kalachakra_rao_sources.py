"""Independent Table-43 ring oracle; no Moira imports or generated expectations."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

DATA_PATH = Path(__file__).parents[1]/'fixtures/kalachakra/rao_2000_source_cases.json'
DATA = json.loads(DATA_PATH.read_text())
SIGNS = DATA['signs'].split()
WEIGHTS = dict(zip(SIGNS, DATA['weights']))
GATI_PATH = DATA_PATH.with_name('rao_2000_markati_contexts.json')
GATI_CONTEXTS = json.loads(GATI_PATH.read_text())['cases']


def source_window(group, pada, position, count=9):
    """Use the independently transcribed 24-position ring, not runtime row traversal."""
    ring = DATA['rings'][group[0]].split()
    origin = (4*(int(group[1])-1)+pada-1)*9+position
    return tuple(ring[(origin+i)%24] for i in range(count))


def source_gati(group, pada, position):
    """Classify a ring occurrence; Markati's repeated pair needs source context."""
    family = group[0]
    ring_position = ((4*(int(group[1])-1)+pada-1)*9+position)%24
    pair = source_window(group,pada,position,2)
    for case in GATI_CONTEXTS:
        if (family,ring_position) == (case['family'],case['source_ring_position']):
            return case['classification']
    for label,pairs in DATA['gati'][family].items():
        if label != 'markati' and pair in map(tuple,pairs):
            return label
    return None


def source_seed(longitude):
    k = next(k for k in range(108) if F(10*k,3) <= longitude < F(10*(k+1),3))
    group = next(g for g,ns in DATA['groups'].items() if k//4+1 in ns)
    pada = k%4+1
    row = source_window(group,pada,0)
    total = sum(WEIGHTS[s] for s in row)
    elapsed = (longitude-F(10*k,3))*F(3,10)*total
    left = F(0)
    for i,sign in enumerate(row):
        right = left+WEIGHTS[sign]
        if left <= elapsed < right:
            window = source_window(group,pada,i)
            coverage = sum(WEIGHTS[s] for s in window)-(elapsed-left)
            deha,jeeva = (window[0],window[-1]) if group[0]=='S' else (window[-1],window[0])
            return dict(group=group,pada=pada,position=i,total=total,elapsed=elapsed,
                        balance=right-elapsed,sequence=window,coverage=coverage,deha=deha,jeeva=jeeva)
        left = right
    raise AssertionError('source interval not covered')


def test_printed_balances_continuations_and_deha_jeeva():
    for case in DATA['balances']:
        d,m,s = case['dms']
        result = source_seed(F(d)+F(m,60)+F(s,3600))
        for name in ('group','pada','position','deha','jeeva'):
            assert result[name] == case[name]
        for name in ('elapsed','balance','coverage'):
            assert result[name] == F(case[name])
        assert result['sequence'] == tuple(case['sequence'].split())
        if 'printed_sequence' in case:
            assert len(case['printed_sequence'].split()) == 10
            assert result['sequence'] == tuple(case['printed_sequence'].split()[:9])


def test_printed_ad_sequences_and_derived_fractions():
    for case in DATA['antardashas']:
        signs = source_window(case['group'],case['pada'],case['position'])
        total = sum(WEIGHTS[s] for s in signs)
        assert signs == tuple(case['sequence'].split())
        assert total == case['denominator']
        assert F(WEIGHTS[signs[0]]**2,total) == F(case['first_years'])
    clip = DATA['clipping']
    signs = DATA['antardashas'][0]['sequence'].split()
    cursor = F(0)
    for i,sign in enumerate(signs[:4]):
        cursor += F(7*WEIGHTS[sign],100)
        assert cursor == F(clip['first_four_cumulative_full_ends'][i])
    assert cursor-F(clip['elapsed_md']) == F(clip['remaining'])
    assert signs[clip['active_child_ordinal']] == clip['active_sign']
    assert F(clip['first_four_cumulative_full_ends'][2]) < F(clip['elapsed_md'])


def test_all_memberships_rows_denominators_and_directed_gati():
    assert sorted(n for ns in DATA['groups'].values() for n in ns) == list(range(1,28))
    denominators = set()
    for group in DATA['groups']:
        for pada in range(1,5):
            for pos in range(9):
                window = source_window(group,pada,pos)
                total = sum(WEIGHTS[s] for s in window)
                denominators.add(total)
                assert sum((F(WEIGHTS[window[0]]*WEIGHTS[s],total) for s in window),F()) == WEIGHTS[window[0]]
    assert min(denominators)>0 and 97 in denominators
    for family,readings in DATA['gati'].items():
        ring = DATA['rings'][family].split()
        edges = set(zip(ring,ring[1:]+ring[:1]))
        for pairs in readings.values():
            assert all(tuple(pair) in edges for pair in pairs)


def test_source_fixture_is_frozen():
    fingerprint = '99075505715be0a25da0bdd2116e327474d19eee66b0c9918308885951e461bb'
    assert hashlib.sha256(DATA_PATH.read_bytes()).hexdigest() == fingerprint


def test_markati_source_contexts_distinguish_reversal_from_regular_progression():
    for family in ('S','A'):
        ring = DATA['rings'][family].split()
        cases = [c for c in GATI_CONTEXTS if c['family']==family]
        assert len(cases)==2 and {c['classification'] for c in cases}=={None,'markati'}
        pair = tuple(cases[0]['context'].split()[1:3])
        positions = {i for i in range(24) if (ring[i],ring[(i+1)%24])==pair}
        assert positions == {c['source_ring_position'] for c in cases}
        for case in cases:
            pos = case['source_ring_position']
            context = tuple(ring[(pos+offset)%24] for offset in (-1,0,1,2))
            assert context == tuple(case['context'].split())
            # Independent zodiac-direction check of the printed temporary reversal.
            steps = [(SIGNS.index(b)-SIGNS.index(a)+6)%12-6 for a,b in zip(context,context[1:])]
            reversal = steps[0]*steps[1] < 0 and steps[1]*steps[2] < 0
            assert reversal == (case['classification']=='markati')
            seed = source_seed(F(case['moon_sidereal_lon']))
            assert source_window(seed['group'],seed['pada'],seed['position']+case['md_source_ordinal']-1,4) == context
            assert source_gati(seed['group'],seed['pada'],seed['position']+case['md_source_ordinal']) == case['classification']


def test_markati_context_fixture_is_frozen():
    assert hashlib.sha256(GATI_PATH.read_bytes()).hexdigest() == '9bded4c5fc07341c350dc5d5967fc657f9cce8b0d1ae104b2104cee6dc1e5450'

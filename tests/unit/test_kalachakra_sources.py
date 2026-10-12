"""Independent rational source checks, with no Kalachakra implementation imports."""
import json
import hashlib
import shutil
import subprocess
from fractions import Fraction as F
from pathlib import Path
import pytest

DATA = json.loads((Path(__file__).parents[1] / "fixtures/kalachakra/source_cases.json").read_text())
SIGNS = DATA["signs"].split()
WEIGHTS = dict(zip(SIGNS, DATA["weights"]))


@pytest.mark.parametrize('autocrlf',('false','true'))
def test_source_fixture_fingerprint_survives_git_checkout(tmp_path,autocrlf):
    """The published source receipt binds bytes on Windows and POSIX alike."""
    if shutil.which('git') is None:
        pytest.skip('Git is required to verify checkout byte preservation')
    root = Path(__file__).parents[2]
    relative = 'tests/fixtures/kalachakra/source_cases.json'
    fingerprint = 'f646f4ab82907988da8cdff128785a62e0c9502a66019c15c70885505952f823'
    def git(*args):
        return subprocess.run(['git',*args],cwd=tmp_path,check=True,capture_output=True).stdout
    git('init','--quiet')
    git('config','core.autocrlf',autocrlf)
    git('config','core.safecrlf','false')
    shutil.copyfile(root/'.gitattributes',tmp_path/'.gitattributes')
    target = tmp_path/relative
    target.parent.mkdir(parents=True)
    shutil.copyfile(root/relative,target)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==fingerprint
    git('add','.gitattributes',relative)
    assert hashlib.sha256(git('show',':'+relative)).hexdigest()==fingerprint
    destination = tmp_path/'checkout'
    git('checkout-index','--all',f'--prefix={destination.as_posix()}/')
    assert hashlib.sha256((destination/relative).read_bytes()).hexdigest()==fingerprint


def source_seed(longitude):
    """Independent interval-list oracle on an exact rational input."""
    k = next(k for k in range(108) if F(10*k, 3) <= longitude < F(10*(k+1), 3))
    group = next(g for g, members in DATA["groups"].items() if k//4+1 in members)
    row = next(r for r in DATA["rows"] if r[:2] == [group, k%4+1])
    signs = row[2].split()
    elapsed = (longitude - F(10*k, 3)) * F(3, 10) * row[3]
    cursor = F(0)
    for index, sign in enumerate(signs):
        right = cursor + WEIGHTS[sign]
        if cursor <= elapsed < right:
            return row, index, elapsed, right-elapsed
        cursor = right
    raise AssertionError("uncovered source interval")


def test_independent_catalogue_and_rotations():
    assert sorted(n for ns in DATA["groups"].values() for n in ns) == list(range(1, 28))
    assert len(DATA["rows"]) == 16
    for n, row in enumerate(DATA["rows"]):
        group, pada, text, total, deha, jeeva = row
        signs = text.split()
        ring = DATA["rings"][n//8].split()
        assert signs == [ring[((n%8)*9+i)%24] for i in range(9)]
        assert sum(WEIGHTS[s] for s in signs) == total
        assert (deha, jeeva) == ((signs[0], signs[-1]) if group[0] == 'S' else (signs[-1], signs[0]))
        for i in range(9):
            assert sum(F(WEIGHTS[signs[i]]*WEIGHTS[signs[(i+j)%9]], total) for j in range(9)) == WEIGHTS[signs[i]]
    for k in range(108):
        row, position, elapsed, remaining = source_seed(F(10*k, 3))
        assert row[1] == k%4+1 and position == 0 and elapsed == 0


def test_published_balances_and_cells():
    for case in DATA["balances"]:
        d, m, s = case["dms"]
        row, index, elapsed, remaining = source_seed(F(d)+F(m,60)+F(s,3600))
        assert row[:2] == [case['group'], case['pada']]
        assert index == case['position'] and row[2].split()[index] == case['sign']
        assert elapsed == F(case['elapsed_row']) and remaining == F(case['balance'])
        if 'sequence' in case:
            signs = row[2].split()
            assert [signs[(index+j)%9] for j in range(9)] == case['sequence'].split()
            assert row[3]-elapsed == F(case['natal_row_remaining'])
            assert row[3]-(WEIGHTS[signs[index]]-remaining) == F(case['coverage'])
    for cell in DATA['antardashas']:
        row = next(r for r in DATA['rows'] if f'{r[0]}/{r[1]}' == cell['row'])
        signs = row[2].split()
        i, j = cell['parent_position'], cell['child_ordinal']
        years = F(WEIGHTS[signs[i]]*WEIGHTS[signs[(i+j)%9]],row[3])
        assert years == F(cell['years'])
        y,m,d,g = cell['traditional']
        assert years == F(y)+F(m,12)+F(d,360)+F(g,21600)


def test_competing_methods_are_distinct():
    c = DATA['comparators']
    assert F(c['rao_taurus_AD']) != F(DATA['antardashas'][1]['years'])
    assert c['rao_bphs_input_continuation'] != DATA['balances'][0]['sequence']
    assert F(c['fixed_15_time_balance']) != F(c['actual_quarter_time_balance'])
    assert len(DATA['balances'][-1]['printed_sequence'].split()) == 10
    assert DATA['balances'][1]['competing_sign'] != DATA['balances'][1]['sign']

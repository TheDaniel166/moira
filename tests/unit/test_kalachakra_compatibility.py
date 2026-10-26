"""Frozen pre-refactor Santhanam transport regression; not an external oracle."""
import hashlib
import json
from pathlib import Path
import pytest
from moira.kalachakra import (
    KalachakraSeed,KalachakraEpoch,kalachakra_sequence,project_kalachakra_sequence,
    current_kalachakra_periods,
)
from moira.kalachakra_policy import PROFILE_ID
from moira_server.serializers.kalachakra import serialize_sequence,serialize_current

PATH = Path(__file__).parents[1]/'fixtures/kalachakra/santhanam_compatibility_2026_10_26.json'
DATA = json.loads(PATH.read_text())


def test_frozen_regression_fingerprint():
    assert hashlib.sha256(PATH.read_bytes()).hexdigest() == 'e7d22d56e104cc180aa344bb7886d45e7271b6f29ba37c1b35177082cf95d7ba'


@pytest.mark.parametrize('case',DATA['cases'])
def test_santhanam_output_unchanged(case):
    result = kalachakra_sequence(KalachakraSeed('sidereal',case['longitude']),profile_id=PROFILE_ID,levels=case['levels'])
    if case['year_basis']:
        result = project_kalachakra_sequence(result,birth_epoch=KalachakraEpoch('jd_utc',2451545),year_basis=case['year_basis'])
    bodies = [serialize_sequence(result).model_dump(mode='json')]
    if case['year_basis']:
        bodies += [serialize_current(current_kalachakra_periods(result,KalachakraEpoch('jd_utc',q))).model_dump(mode='json')
                   for q in (2451545,result.coverage_dates.end_jd_utc)]
    actual = hashlib.sha256(json.dumps(bodies,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert actual == case['sha256']

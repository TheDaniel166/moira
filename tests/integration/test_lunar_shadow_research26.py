"""Replay the pre-implementation 26-disagreement sensitivity study."""
import json
from pathlib import Path

import pytest

from moira._ephemeris_time import _ephemeris_tt_to_ut1
from moira.lunar_shadow_events import inspect_lunar_shadow_candidate

pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]
DATA = json.loads((Path(__file__).parents[1] / 'fixtures/lunar_shadow_26_research_reference.json').read_text())


@pytest.mark.parametrize('case', DATA['cases'], ids=lambda c: str(c['lunation']))
@pytest.mark.parametrize('policy,scale,key', [
    ('danjon_angular', 1.0, 'angular_maximum_margins_km'),
    ('static_finite_cone', 1.01, 'cone_maximum_margins_km'),
])
def test_research_disagreement_replay(eclipse_calculator, case, policy, scale, key):
    seed = _ephemeris_tt_to_ut1(case['seed_tt'], eclipse_calculator._reader)
    result = inspect_lunar_shadow_candidate(eclipse_calculator, seed, policy=policy, earth_radius_scale=scale)
    margins = case[key]
    if margins['penumbral'] < -0.01:
        assert result.status == 'unresolved' and result.event is None
        return
    assert result.status == 'detected'
    event = result.event
    expected = ('total' if margins['umbral_total'] > 0 else
                'partial' if margins['umbral_partial'] > 0 else 'penumbral')
    assert event.candidate_type == expected
    # This compares against a separately coded, pre-implementation grid +
    # golden search, with identical ephemeris and model, not catalog truth.
    state = event.geometry_at_greatest
    if policy == 'danjon_angular':
        _, _, _, _, moon_distance = eclipse_calculator._lunar_event_geometry_ut(event.greatest_jd_ut, retarded_moon=False)
        calculated = state.penumbral_margin * moon_distance
    else:
        calculated = state.penumbral_margin
    assert calculated == pytest.approx(margins['penumbral'], abs=0.05)
    assert not result.complete and not event.completeness_certified

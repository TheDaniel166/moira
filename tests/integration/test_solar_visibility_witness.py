"""Fixed-site native WGS-84 common-ray visibility regressions."""
import json
import math
from pathlib import Path

import pytest

from moira.julian import julian_day
from moira.solar_visibility_witness import (inspect_solar_visibility_candidates,
                                           refine_solar_visibility_candidate, solar_visibility_at_site)

pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]
DATA = json.loads((Path(__file__).parents[1] / 'fixtures/solar_visibility_disputed_five.json').read_text())
ARCSEC_PER_RAD = 180 / math.pi * 3600


@pytest.mark.parametrize('case', DATA['records'], ids=lambda item: str(item['lunation']))
def test_five_disputed_catalog_sites(eclipse_calculator, case):
    result = solar_visibility_at_site(eclipse_calculator, case['jd_ut1'], case['latitude_deg'],
                                      case['longitude_deg'], lunation=case['lunation'])
    geometry = result.geometry
    assert geometry.status == case['expected_status']
    assert result.lunation == case['lunation']
    assert result.ephemeris == 'DE-0441LE-0441'
    assert geometry.separation_margin_rad * ARCSEC_PER_RAD == pytest.approx(case['separation_margin_arcsec'], abs=0.02)
    if case['maximum_altitude_arcsec'] is not None:
        assert geometry.maximum_altitude_rad * ARCSEC_PER_RAD == pytest.approx(case['maximum_altitude_arcsec'], abs=0.02)
        assert geometry.witness_direction is not None
    else:
        assert geometry.witness_direction is None


def test_positive_and_unresolved_sample_search(eclipse_calculator):
    hidden = DATA['records'][0]
    visible = DATA['records'][2]
    def sample(row):
        return (row['jd_ut1'], row['latitude_deg'], row['longitude_deg'])
    none = inspect_solar_visibility_candidates(eclipse_calculator, [sample(hidden)])
    assert none.status == 'unresolved' and none.witness is None and not none.complete
    found = inspect_solar_visibility_candidates(eclipse_calculator, [sample(hidden), sample(visible)], lunation=visible['lunation'])
    assert found.status == 'witness_found' and found.tested_count == 2 and not found.complete
    assert found.witness.geometry.status == 'visible'


def test_modern_total_control_is_visible_and_legacy_unchanged(eclipse_calculator):
    # 2024-04-08, Dallas: this is a same-model geometric visibility check,
    # not a timing or atmospheric comparison against the catalog.
    when = julian_day(2024, 4, 8, 18 + 40/60)
    before = eclipse_calculator.calculate_jd(when)
    result = solar_visibility_at_site(eclipse_calculator, when, 32.7767, -96.7970)
    assert result.geometry.status == 'visible'
    assert result.geometry.witness_direction is not None
    assert eclipse_calculator.calculate_jd(when) == before


@pytest.mark.parametrize('case', DATA['records'], ids=lambda item: str(item['lunation']))
def test_five_disputed_bounded_refinements(eclipse_calculator, case):
    t, lat, lon = case['jd_ut1'], case['latitude_deg'], case['longitude_deg']
    seed = (t + 20/86400, lat + 0.01, lon + 0.01)
    if case['lunation'] == -33903:
        assert solar_visibility_at_site(eclipse_calculator, *seed).geometry.status == 'hidden'
    result = refine_solar_visibility_candidate(
        eclipse_calculator, seed, time_bounds_ut1=(t - 120/86400, t + 120/86400),
        latitude_bounds_deg=(lat-.1, lat+.1), longitude_bounds_deg=(lon-.1, lon+.1),
        lunation=case['lunation'], time_tolerance_seconds=1., angular_tolerance_deg=.001,
    )
    expected = 'witness_found' if case['expected_status'] == 'visible' else 'unresolved'
    assert result.status == expected
    assert result.converged and not result.complete
    assert result.final_step_seconds <= 1. and result.final_step_latitude_deg <= .001
    if result.witness is not None:
        assert result.witness.geometry.status == 'visible'
        assert result.witness.geometry.witness_direction is not None
        assert result.witness.lunation == case['lunation']
    else:
        # Only this local search was unsuccessful; global absence is unproved.
        assert case['expected_status'] == 'disjoint'


def test_near_horizon_witness_refinement_converges_in_time_and_angle(eclipse_calculator):
    case = next(row for row in DATA['records'] if row['lunation'] == -33903)
    t, lat, lon = case['jd_ut1'], case['latitude_deg'], case['longitude_deg']
    seed = (t + 20/86400, lat+.01, lon+.01)
    bounds = dict(time_bounds_ut1=(t - 120/86400, t + 120/86400),
                  latitude_bounds_deg=(lat-.1, lat+.1), longitude_bounds_deg=(lon-.1, lon+.1))
    coarse = refine_solar_visibility_candidate(eclipse_calculator, seed, **bounds,
                                               time_tolerance_seconds=2., angular_tolerance_deg=.002)
    fine = refine_solar_visibility_candidate(eclipse_calculator, seed, **bounds,
                                             time_tolerance_seconds=.25, angular_tolerance_deg=.00025)
    assert coarse.status == fine.status == 'witness_found'
    assert coarse.converged and fine.converged
    assert fine.final_step_seconds < coarse.final_step_seconds
    assert fine.final_step_latitude_deg < coarse.final_step_latitude_deg
    # Convergence of the heuristic is a numerical check only, not an error
    # bound on the optimum or a guarantee of a global visible region.
    def score(result):
        geom = result.best_candidate.geometry
        return min(geom.separation_margin_rad, geom.maximum_altitude_rad)
    assert abs(score(coarse)-score(fine)) * ARCSEC_PER_RAD < 0.1

"""Synthetic bounded-refinement tests, independent of any ephemeris kernel."""
from types import SimpleNamespace

import pytest

from moira import solar_visibility_witness as visibility


EPOCH = 2451545.0
BOUNDS = dict(time_bounds_ut1=(EPOCH-10/86400, EPOCH+10/86400),
              latitude_bounds_deg=(-3.0, 3.0), longitude_bounds_deg=(-4.0, 4.0))


def make_site(jd, lat, lon, score, *, status=None, direction=True):
    if status is None:
        status = 'visible' if score > 1e-12 else 'hidden'
    geometry = SimpleNamespace(status=status, separation_margin_rad=1.0,
                               maximum_altitude_rad=score,
                               witness_direction=(1.0, 0.0, 0.0) if direction else None)
    return SimpleNamespace(jd_ut1=jd, latitude_deg=lat, longitude_deg=lon,
                           geometry=geometry)


def test_bounded_interior_peak_yields_strict_witness(monkeypatch):
    calls = []
    def model(calc, jd, lat, lon, **kwargs):
        calls.append((jd, lat, lon))
        seconds = (jd-EPOCH)*86400
        score = 1e-4 - 1e-5*((seconds-2)**2 + (lat-1)**2 + (lon+1)**2)
        return make_site(jd, lat, lon, score)
    monkeypatch.setattr(visibility, 'solar_visibility_at_site', model)
    result = visibility.refine_solar_visibility_candidate(
        object(), (EPOCH-5/86400, -2., 2.), **BOUNDS, max_iterations=100,
        time_tolerance_seconds=.01, angular_tolerance_deg=.001)
    assert result.status == 'witness_found'
    assert result.witness is not None
    assert result.witness.geometry.status == 'visible'
    assert result.witness.geometry.witness_direction is not None
    assert result.complete is False
    assert result.evaluations == len(calls)
    assert len(set(calls)) == len(calls)
    assert result.iterations <= 100
    for jd, lat, lon in calls:
        assert BOUNDS['time_bounds_ut1'][0] <= jd <= BOUNDS['time_bounds_ut1'][1]
        assert BOUNDS['latitude_bounds_deg'][0] <= lat <= BOUNDS['latitude_bounds_deg'][1]
        assert BOUNDS['longitude_bounds_deg'][0] <= lon <= BOUNDS['longitude_bounds_deg'][1]


def test_boundary_peak_and_no_global_absence_claim(monkeypatch):
    # The exact unconstrained maximum lies outside the box: the best lawful
    # objective occurs on three distinct temporal/spatial boundary faces.
    def model(calc, jd, lat, lon, **kwargs):
        seconds = (jd-EPOCH)*86400
        score = -1e-3*((seconds-15)**2 + (lat-4)**2 + (lon+5)**2)
        return make_site(jd, lat, lon, score)
    monkeypatch.setattr(visibility, 'solar_visibility_at_site', model)
    result = visibility.refine_solar_visibility_candidate(
        object(), (EPOCH, 0., 0.), **BOUNDS, max_iterations=120,
        time_tolerance_seconds=.05, angular_tolerance_deg=.005)
    assert result.status == 'unresolved'
    assert result.witness is None
    assert result.complete is False
    best = result.best_candidate
    assert (best.jd_ut1-EPOCH)*86400 == pytest.approx(10, abs=.15)
    assert best.latitude_deg == pytest.approx(3., abs=.02)
    assert best.longitude_deg == pytest.approx(-4., abs=.02)
    assert result.converged is True
    assert result.final_step_seconds <= .05
    assert result.final_step_latitude_deg <= .005
    assert result.final_step_longitude_deg <= .005


def test_numerical_tangency_is_unresolved(monkeypatch):
    for status, direction in (('indeterminate', True), ('tangent', True)):
        def model(calc, jd, lat, lon, **kwargs):
            return make_site(jd, lat, lon, 1e-14, status=status, direction=direction)
        monkeypatch.setattr(visibility, 'solar_visibility_at_site', model)
        result = visibility.refine_solar_visibility_candidate(
            object(), (EPOCH, 0., 0.), **BOUNDS, max_iterations=60,
            time_tolerance_seconds=.1, angular_tolerance_deg=.01)
        assert result.status == 'unresolved'
        assert result.witness is None
        assert result.complete is False


def test_visible_without_witness_is_reported_as_provider_error(monkeypatch):
    def model(calc, jd, lat, lon, **kwargs):
        return make_site(jd, lat, lon, 1e-14, status='visible', direction=False)
    monkeypatch.setattr(visibility, 'solar_visibility_at_site', model)
    with pytest.raises(ArithmeticError, match='witness'):
        visibility.refine_solar_visibility_candidate(object(), (EPOCH, 0., 0.), **BOUNDS)


def test_nonconvergence_is_reported_without_claiming_absence(monkeypatch):
    def model(calc, jd, lat, lon, **kwargs):
        return make_site(jd, lat, lon, -1.)
    monkeypatch.setattr(visibility, 'solar_visibility_at_site', model)
    result = visibility.refine_solar_visibility_candidate(
        object(), (EPOCH, 0., 0.), **BOUNDS, max_iterations=1,
        time_tolerance_seconds=.001, angular_tolerance_deg=.0001)
    assert result.status == 'unresolved'
    assert result.converged is False
    assert result.complete is False


def test_best_nonwitness_does_not_overwrite_prior_witness(monkeypatch):
    def model(calc, jd, lat, lon, **kwargs):
        seconds = (jd-EPOCH)*86400
        score = 1.0 - .01*((seconds-2)**2 + (lat-1)**2 + (lon+1)**2)
        # Simulate a degenerate but high-scoring lens near the optimum.
        return make_site(jd, lat, lon, score,
                         status='tangent' if score > .999 else 'visible',
                         direction=score <= .999)
    monkeypatch.setattr(visibility, 'solar_visibility_at_site', model)
    result = visibility.refine_solar_visibility_candidate(
        object(), (EPOCH, 0., 0.), **BOUNDS, max_iterations=120,
        time_tolerance_seconds=.01, angular_tolerance_deg=.001)
    assert result.status == 'witness_found'
    assert result.witness.geometry.status == 'visible'
    assert result.witness.geometry.witness_direction is not None
    assert result.best_candidate.geometry.status == 'tangent'


def test_site_provider_exception_propagates(monkeypatch):
    def fail(*args, **kwargs):
        raise ArithmeticError('synthetic state unavailable')
    monkeypatch.setattr(visibility, 'solar_visibility_at_site', fail)
    with pytest.raises(ArithmeticError, match='synthetic state unavailable'):
        visibility.refine_solar_visibility_candidate(object(), (EPOCH, 0., 0.), **BOUNDS)


@pytest.mark.parametrize('seed,updates', [
    ((EPOCH, 0., 0.), {'time_bounds_ut1': (EPOCH+1, EPOCH)}),
    ((EPOCH, 4., 0.), {}),
    ((EPOCH, 0., 0.), {'latitude_bounds_deg': (-91., 3.)}),
    ((EPOCH, 0., 0.), {'longitude_bounds_deg': (-4., 181.)}),
    ((EPOCH, 0., 0.), {'time_tolerance_seconds': 0.}),
    ((EPOCH, 0., 0.), {'time_tolerance_seconds': 1e-10}),
    ((EPOCH, 0., 0.), {'angular_tolerance_deg': float('nan')}),
    ((EPOCH, 0., 0.), {'max_iterations': 0}),
])
def test_invalid_bounds_and_search_settings_rejected(seed, updates):
    opts = dict(BOUNDS)
    opts.update(updates)
    with pytest.raises((TypeError, ValueError)):
        visibility.refine_solar_visibility_candidate(object(), seed, **opts)

"""Boundary and error propagation for native solar visibility witnesses."""
from types import SimpleNamespace

import pytest

from moira import eclipse
from moira import solar_visibility_witness as witness


class Calculator:
    _reader = None


def test_overlapping_sun_moon_depth_intervals_are_unsupported(monkeypatch):
    monkeypatch.setattr(witness, '_ut1_to_ephemeris_tt', lambda jd, reader: jd)
    state = SimpleNamespace(fundamental_plane_point_xyz_km=(1e8, 0., 0.),
                            axis_unit_away_from_sun=(1., 0., 0.), axis_projection_km=0.,
                            sun_xyz_from_earth_itrf_km=(1e8, 0., 0.))
    monkeypatch.setattr(eclipse, '_earth_fixed_solar_shadow', lambda *args, **kwargs: state)
    with pytest.raises(witness.SolarVisibilityDomainError, match='depth intervals'):
        witness.solar_visibility_at_site(Calculator(), 2451545., 0., 0.)


def test_provider_failure_propagates_through_candidate_search(monkeypatch):
    monkeypatch.setattr(witness, '_ut1_to_ephemeris_tt', lambda jd, reader: jd)
    def fail(*args, **kwargs):
        raise NotImplementedError('provider failure')
    monkeypatch.setattr(eclipse, '_earth_fixed_solar_shadow', fail)
    with pytest.raises(NotImplementedError, match='provider failure'):
        witness.inspect_solar_visibility_candidates(Calculator(), [(2451545., 0., 0.)])


def test_invalid_site_and_empty_search_are_rejected():
    with pytest.raises(ValueError, match='latitude'):
        witness.solar_visibility_at_site(Calculator(), 2451545., 91., 0.)
    with pytest.raises(ValueError, match='at least one'):
        witness.inspect_solar_visibility_candidates(Calculator(), [])

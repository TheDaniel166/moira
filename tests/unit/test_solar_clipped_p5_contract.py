"""Uncertain topology is not mistaken for absence or a calculation error."""
from types import SimpleNamespace

import pytest

from moira import solar_eclipse_clipped as clipped


def test_closely_spaced_crossings_remain_unresolved(monkeypatch):
    calls = iter(([0.0, 1e-10], []))
    monkeypatch.setattr(clipped, "_roots_in_unit_interval", lambda _coeff: next(calls))
    shadow = SimpleNamespace(
        fundamental_plane_point_xyz_km=(0., 0., 0.),
        axis_unit_away_from_sun=(0., 0., 1.),
        central_cone_slope=0.1,
        central_radius_km=1.,
    )
    circle = ((0., 0., 0.), (1., 0., 0.), (0., 1., 0.))
    with pytest.raises(clipped.ClippedBoundaryIndeterminate, match="closely spaced"):
        clipped._horizon_crossings(shadow, circle)


def test_generator_topology_error_is_narrowly_converted(monkeypatch):
    def fail(_branch):
        raise ArithmeticError("penumbral cone has no strict WGS-84 intersection")
    monkeypatch.setattr(clipped, "_penumbral_lawful_azimuth_interval", fail)
    with pytest.raises(clipped.ClippedBoundaryIndeterminate):
        clipped._generator_interval(object())


@pytest.mark.parametrize("error", [ArithmeticError("bad numeric state"), RuntimeError("kernel unavailable")])
def test_unexpected_generator_error_propagates(monkeypatch, error):
    def fail(_branch):
        raise error
    monkeypatch.setattr(clipped, "_penumbral_lawful_azimuth_interval", fail)
    with pytest.raises(type(error), match=str(error)):
        clipped._generator_interval(object())


def test_provider_error_propagates_through_inspection(monkeypatch):
    def fail(_calc, _jd):
        raise RuntimeError("missing kernel")
    monkeypatch.setattr(clipped, "_earth_fixed_solar_shadow", fail)
    with pytest.raises(RuntimeError, match="missing kernel"):
        clipped.inspect_instantaneous_clipped_central_boundary(None, 2451545.)

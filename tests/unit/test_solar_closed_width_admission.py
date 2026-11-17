"""Fail-closed checks for the central-width admission contract."""
import pytest

import moira.eclipse as eclipse


def test_missing_tangent_with_complete_generator_family_still_raises(monkeypatch):
    shadow = object()

    def no_tangent(*_args):
        raise eclipse._AxisTrackTangentUnavailable("no neighboring surface point")

    monkeypatch.setattr(eclipse, "_solve_solar_umbral_width_km", no_tangent)
    monkeypatch.setattr(eclipse, "_earth_fixed_solar_shadow", lambda *_args: shadow)
    monkeypatch.setattr(eclipse, "_axis_surface_point_from_shadow", lambda *_args: object())
    monkeypatch.setattr(eclipse, "_central_shadow_generator_points", lambda *_args: (object(),))
    with pytest.raises(eclipse._AxisTrackTangentUnavailable, match="no neighboring"):
        eclipse._central_width_at_epoch(object(), 2450000.0)


@pytest.mark.parametrize("missing", ["shadow", "axis"])
def test_no_axis_sentinel_is_not_reported_as_available(monkeypatch, missing):
    shadow = None if missing == "shadow" else object()
    monkeypatch.setattr(eclipse, "_solve_solar_umbral_width_km", lambda *_args: 0.0)
    monkeypatch.setattr(eclipse, "_earth_fixed_solar_shadow", lambda *_args: shadow)
    monkeypatch.setattr(eclipse, "_axis_surface_point_from_shadow", lambda *_args: None)
    with pytest.raises(ArithmeticError, match="no axis surface point"):
        eclipse._central_width_at_epoch(object(), 2450000.0)

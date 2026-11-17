"""Pure spherical containment and swept-witness contract tests."""
import math
from types import SimpleNamespace

import pytest

from moira import solar_swept_witness as swept


SUN = (100., 0., 0.)
MOON = (10., 0., 0.)
ZENITH = (1., 0., 0.)
KW = dict(sun_radius_km=10., moon_radius_km=2.)


def rotate(v):
    return v[2], -v[0], -v[1]


def moon_at(angle):
    return 10*math.cos(angle), 10*math.sin(angle), 0.


def test_strict_total_and_annular_containment():
    total = swept.central_shadow_interior(SUN, MOON, ZENITH, **KW)
    assert total.status == 'interior_witness'
    assert total.phase == 'total'
    assert total.central_margin_rad == pytest.approx(math.asin(.2)-math.asin(.1))
    assert total.sun_altitude_rad == pytest.approx(math.pi/2)
    annular = swept.central_shadow_interior(SUN, MOON, ZENITH,
        sun_radius_km=10, moon_radius_km=.5)
    assert annular.status == 'interior_witness'
    assert annular.phase == 'annular'
    assert annular.central_margin_rad == pytest.approx(math.asin(.1)-math.asin(.05))


@pytest.mark.parametrize('moon_radius', [2., .5])
def test_internal_tangency_and_small_angular_margins_are_not_witnesses(moon_radius):
    delta = abs(math.asin(moon_radius/10)-math.asin(.1))
    for offset in (0., 5e-13, -5e-13):
        out = swept.central_shadow_interior(SUN, moon_at(delta+offset), ZENITH,
            sun_radius_km=10, moon_radius_km=moon_radius)
        assert out.status == 'unresolved'
        assert out.phase is None
    outside = swept.central_shadow_interior(SUN, moon_at(delta+1e-8), ZENITH,
        sun_radius_km=10, moon_radius_km=moon_radius)
    assert outside.status == 'unresolved'
    inside = swept.central_shadow_interior(SUN, moon_at(delta-1e-8), ZENITH,
        sun_radius_km=10, moon_radius_km=moon_radius)
    assert inside.status == 'interior_witness'


def test_apex_equal_angular_radii_and_horizon_guards():
    apex = swept.central_shadow_interior(SUN, MOON, ZENITH,
        sun_radius_km=10, moon_radius_km=1)
    assert apex.status == 'unresolved'
    assert apex.phase is None
    for altitude in (0., -1e-8, 5e-13):
        zenith = (math.sin(altitude), math.cos(altitude), 0.)
        result = swept.central_shadow_interior(SUN, MOON, zenith, **KW)
        assert result.status == 'unresolved'
        assert result.phase is None
    zenith = (math.sin(1e-8), math.cos(1e-8), 0.)
    assert swept.central_shadow_interior(SUN, MOON, zenith, **KW).status == 'interior_witness'


def test_containment_is_rotation_invariant():
    m = moon_at(.03)
    original = swept.central_shadow_interior(SUN, m, ZENITH, **KW)
    rotated = swept.central_shadow_interior(rotate(SUN), rotate(m), rotate(ZENITH), **KW)
    assert rotated.status == original.status == 'interior_witness'
    assert rotated.phase == original.phase == 'total'
    assert rotated.central_margin_rad == pytest.approx(original.central_margin_rad, abs=1e-15)
    assert rotated.sun_altitude_rad == pytest.approx(original.sun_altitude_rad, abs=1e-15)


@pytest.mark.parametrize('sun,moon,zenith,kwargs', [
    ((0,0,0), MOON, ZENITH, KW),
    (SUN, (float('nan'),0,0), ZENITH, KW),
    (SUN, MOON, (0,0,0), KW),
    (SUN, MOON, ZENITH, dict(sun_radius_km=-1, moon_radius_km=2)),
    (SUN, (95,0,0), ZENITH, KW),  # distance intervals overlap
    (SUN, MOON, ZENITH, dict(**KW, tolerance_rad=1e-300)),
    (SUN, MOON, ZENITH, dict(**KW, tolerance_rad=float('nan'))),
])
def test_invalid_or_unsupported_input_rejected(sun, moon, zenith, kwargs):
    with pytest.raises((TypeError, ValueError)):
        swept.central_shadow_interior(sun, moon, zenith, **kwargs)


def mock_provider(monkeypatch, *, zenith=(1.,0.,0.)):
    from moira import eclipse
    monkeypatch.setattr(eclipse, '_wgs84_surface_xyz_km', lambda lat,lon: (0.,0.,0.))
    monkeypatch.setattr(eclipse, '_wgs84_surface_normal_unit', lambda point: zenith)
    monkeypatch.setattr(swept, '_ut1_to_ephemeris_tt', lambda jd,reader: jd+.1)
    state = SimpleNamespace(fundamental_plane_point_xyz_km=(384400.,0.,0.),
                            axis_unit_away_from_sun=(1.,0.,0.), axis_projection_km=0.,
                            sun_xyz_from_earth_itrf_km=(149597870.7,0.,0.))
    monkeypatch.setattr(eclipse, '_earth_fixed_solar_shadow', lambda *a,**k: state)
    monkeypatch.setattr(eclipse, '_reader_identity_at',
                        lambda *a,**k: SimpleNamespace(summary_label='synthetic'))
    return SimpleNamespace(_reader=object())


@pytest.mark.parametrize('sample', [100., 101.])
def test_closed_interval_endpoints_are_valid_witnesses(monkeypatch, sample):
    calc = mock_provider(monkeypatch)
    result = swept.inspect_swept_central_interior(calc, 12., -33., [sample],
        interval_ut1=(100.,101.), lunation=42)
    assert result.status == 'interior_witness'
    assert result.witness.jd_ut1 == sample
    assert result.witness.jd_tt == pytest.approx(sample+.1)
    assert result.witness.geometry.phase == 'annular'
    assert result.witness.ephemeris == 'synthetic'
    assert result.interval_ut1 == (100.,101.)
    assert result.lunation == 42
    assert result.complete is False


def test_unwitnessed_samples_are_unresolved_and_not_absence(monkeypatch):
    calc = mock_provider(monkeypatch, zenith=(-1.,0.,0.))
    result = swept.inspect_swept_central_interior(calc, 0., 0., [100.,100.5,101.],
        interval_ut1=(100.,101.))
    assert result.status == 'unresolved'
    assert result.witness is None
    assert len(result.samples) == 3
    assert result.complete is False


@pytest.mark.parametrize('samples,interval', [
    ([100.5,101.1], (100.,101.)),
    ([100.5,float('nan')], (100.,101.)),
    ([], (100.,101.)),
    ([100.5], (101.,100.)),
])
def test_times_fully_validated_before_any_provider_call(monkeypatch, samples, interval):
    def forbidden(*args, **kwargs):
        raise AssertionError('provider must not be consulted before full interval validation')
    monkeypatch.setattr(swept, '_ut1_to_ephemeris_tt', forbidden)
    with pytest.raises(ValueError):
        swept.inspect_swept_central_interior(SimpleNamespace(_reader=object()), 0.,0., samples,
                                             interval_ut1=interval)


def test_provider_error_propagates(monkeypatch):
    def fail(*args, **kwargs):
        raise ArithmeticError('synthetic provider failed')
    monkeypatch.setattr(swept, '_ut1_to_ephemeris_tt', fail)
    with pytest.raises(ArithmeticError, match='synthetic provider failed'):
        swept.inspect_swept_central_interior(SimpleNamespace(_reader=object()), 0.,0., [100.],
                                             interval_ut1=(100.,101.))

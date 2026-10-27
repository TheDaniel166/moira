"""Independent physical-horizon covenants for ACG, not output snapshots.

Authority: ERFA hd2ae (geodetic zenith) and gd2gc (WGS-84 observer).
Fixed directions use a 1e-10 degree altitude tolerance. Synthetic finite-distance
Moon cases isolate parallax with zero polar motion and diurnal aberration;
their independently evaluated altitude tolerance is 1e-8 degrees. The horizon
is the body centre at 0 degrees or the declared constant -0.5667 degrees.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import erfa
import pytest

from moira.astrocartography import acg_lines, _compute_acg_curve_samples


def _curves(lines):
    return {line.line_type: line.points for line in lines if line.line_type in ("ASC", "DSC")}


def test_exact_tangent_is_retained_without_extending_beyond_cutoff():
    lats = [-70 - 1e-7, -70.0, -70 + 1e-7, 70 - 1e-7, 70.0, 70 + 1e-7]
    curves = _compute_acg_curve_samples(0.0, 20.0, 0.0, lats, 0.0)
    for points in curves:
        assert [lat for lat, _ in points] == lats[1:-1]
        for lat, lon in points:
            elevation = math.degrees(erfa.hd2ae(math.radians(lon), math.radians(20), math.radians(lat))[1])
            assert elevation == pytest.approx(0.0, abs=1e-10)


@pytest.mark.parametrize("declination", [-89.9, -45.05, -23.44, -20.1, -19.5, 0.0, 19.5, 20.1, 23.44, 45.05, 89.9])
@pytest.mark.parametrize("refraction", [False, True])
def test_fixed_direction_vertices_and_cutoffs_use_geodetic_horizon(declination, refraction):
    ra, gast = 123.0, 17.0
    horizon = -0.5667 if refraction else 0.0
    curves = _curves(acg_lines({"Direction": (ra, declination)}, gast, lat_step=1, refraction=refraction))
    expected = set()
    for lat in range(-89, 90):
        elevations = [math.degrees(erfa.hd2ae(h, math.radians(declination), math.radians(lat))[1]) for h in (0.0, math.pi)]
        if min(elevations) - 1e-12 <= horizon <= max(elevations) + 1e-12:
            expected.add(float(lat))
    for points in curves.values():
        assert {lat for lat, _ in points} == expected
        for lat, lon in points:
            hour_angle = math.radians((gast + lon - ra) % 360)
            altitude = math.degrees(erfa.hd2ae(hour_angle, math.radians(declination), math.radians(lat))[1])
            assert altitude == pytest.approx(horizon, abs=1e-10)


@pytest.mark.parametrize("declination", [-27.3, -0.2, 0.2, 27.3])
@pytest.mark.parametrize("refraction", [False, True])
def test_lunar_parallax_is_solved_at_each_returned_location(monkeypatch, declination, refraction):
    ra, gast, distance = 30.0, 17.0, 384400.0
    ra_r, dec_r = math.radians(ra), math.radians(declination)
    vector = (distance * math.cos(dec_r) * math.cos(ra_r), distance * math.cos(dec_r) * math.sin(ra_r), distance * math.sin(dec_r))
    expected_reader = object()

    def topocentric(lat, lon):
        # ERFA supplies the ellipsoid conversion; this is not the ACG formula.
        observer = erfa.gd2gc(1, math.radians(gast + lon), math.radians(lat), 0.0) / 1000
        return tuple(component - offset for component, offset in zip(vector, observer))

    def altitude(lat, lon):
        xyz = topocentric(lat, lon)
        topo_ra, topo_dec = erfa.c2s(xyz)
        return math.degrees(erfa.hd2ae(math.radians(gast + lon) - topo_ra, topo_dec, math.radians(lat))[1])

    def fake_planet(body, jd_ut, *, reader: object, frame: str):
        assert body == "Moon" and frame == "cartesian"
        assert reader is expected_reader
        return SimpleNamespace(x=vector[0], y=vector[1], z=vector[2])

    def fake_sky(body, jd_ut, observer_lat, observer_lon, **kwargs):
        xyz = topocentric(observer_lat, observer_lon)
        topo_ra, topo_dec = erfa.c2s(xyz)
        return SimpleNamespace(right_ascension=math.degrees(topo_ra) % 360, declination=math.degrees(topo_dec))

    monkeypatch.setattr("moira.planets.planet_at", fake_planet)
    monkeypatch.setattr("moira.planets.sky_position_at", fake_sky)
    monkeypatch.setattr("moira.corrections.apply_diurnal_aberration", lambda xyz, *args, **kwargs: xyz)
    monkeypatch.setattr("moira.corrections.PolarMotionRegistry.polar_motion_at", lambda jd: (0.0, 0.0))
    horizon = -0.5667 if refraction else 0.0
    curves = _curves(acg_lines({"Moon": (ra, declination)}, gast, lat_step=1, jd_ut=2451545.0, reader=expected_reader, refraction=refraction))
    expected = {
        float(lat) for lat in range(-89, 90)
        if min(altitude(lat, ra - gast), altitude(lat, ra - gast + 180)) <= horizon
        <= max(altitude(lat, ra - gast), altitude(lat, ra - gast + 180))
    }
    for branch, points in curves.items():
        assert {lat for lat, _ in points} == expected
        for lat, lon in points:
            assert altitude(lat, lon) == pytest.approx(horizon, abs=1e-8)
            # Differentiate in longitude: ASC is the increasing-altitude branch.
            slope = altitude(lat, lon + 1e-4) - altitude(lat, lon - 1e-4)
            assert slope > 0 if branch == "ASC" else slope < 0

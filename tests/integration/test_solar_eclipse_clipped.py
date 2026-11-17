import math
import pytest
from moira.eclipse import _earth_fixed_solar_shadow, _central_shadow_clearance_km, EARTH_RADIUS_KM, _WGS84_POLAR_RADIUS_KM
from moira.julian import julian_day
from moira.solar_eclipse_clipped import instantaneous_clipped_central_boundary, ClippedBoundaryIndeterminate, _roots_in_unit_interval


def test_roots_and_grazing():
    roots = _roots_in_unit_interval([-0.04, 0, 1])
    assert roots == pytest.approx([-0.2, 0.2], abs=1e-12)
    with pytest.raises(ClippedBoundaryIndeterminate):
        _roots_in_unit_interval([0, 0, 1])


def test_2003_may_31_instantaneous_surface(eclipse_calculator):
    jd = julian_day(2003, 5, 31, 4 + 8/60)
    shadow = _earth_fixed_solar_shadow(eclipse_calculator, jd)
    result = instantaneous_clipped_central_boundary(eclipse_calculator, jd, arc_samples=129)
    assert result.scope == 'INSTANTANEOUS'
    for p in result.cone_arc + result.horizon_arc:
        x, y, z = p.xyz_itrf_km
        assert abs((x*x+y*y)/EARTH_RADIUS_KM**2 + z*z/_WGS84_POLAR_RADIUS_KM**2-1) < 2e-12
    for p in result.cone_arc:
        assert abs(_central_shadow_clearance_km(shadow, p.xyz_itrf_km)) < 1e-6
    for p in result.cone_arc:
        x, y, z = p.xyz_itrf_km
        sx, sy, sz = shadow.sun_xyz_from_earth_itrf_km
        h = (x*(sx-x)+y*(sy-y))/EARTH_RADIUS_KM**2 + z*(sz-z)/_WGS84_POLAR_RADIUS_KM**2
        assert h >= -1e-6
    for p in result.horizon_arc:
        assert _central_shadow_clearance_km(shadow, p.xyz_itrf_km) >= -1e-5
        x, y, z = p.xyz_itrf_km
        sx,sy,sz = shadow.sun_xyz_from_earth_itrf_km
        h = (x*(sx-x)+y*(sy-y))/EARTH_RADIUS_KM**2 + z*(sz-z)/_WGS84_POLAR_RADIUS_KM**2
        assert abs(h) < 2e-10


def test_nasa_2003_path_limit_cross_model_check(eclipse_calculator):
    # Independent NASA DE200/LE200 table, 04:08 UT, rounded to 0.1 arcmin:
    # https://eclipse.gsfc.nasa.gov/SEpubs/20030000/tables/table_1.3.html
    # North limit is on the geometric horizon and has positive central-shadow
    # clearance; the southern limit is on the central cone. These are samples
    # of a time-stamped table, corroborating instantaneous arcs only. The
    # northern point is not established as a swept-union boundary.
    result = instantaneous_clipped_central_boundary(
        eclipse_calculator, julian_day(2003, 5, 31, 4+8/60), arc_samples=513
    )
    def approximate_distance(point, lat, lon):
        return EARTH_RADIUS_KM * math.hypot(
            math.radians(point.latitude_deg-lat),
            math.cos(math.radians(lat))*math.radians(point.longitude_deg-lon),
        )
    north = min(approximate_distance(p, 64+1.6/60, -28) for p in result.horizon_arc)
    south = min(approximate_distance(p, 72+30.5/60, -(8+25.8/60)) for p in result.cone_arc)
    assert north < 5.0
    assert south < 5.0


def test_periodic_generator_topology_fails_closed(monkeypatch):
    import moira.solar_eclipse_clipped as clipped
    monkeypatch.setattr(clipped, "_earth_fixed_solar_shadow", lambda calc, jd: object())
    monkeypatch.setattr(clipped, "_noncentral_shadow_branch", lambda shadow: shadow)
    monkeypatch.setattr(clipped, "_penumbral_lawful_azimuth_interval", lambda branch: (0, math.tau, True))
    with pytest.raises(ClippedBoundaryIndeterminate, match="bounded"):
        clipped.instantaneous_clipped_central_boundary(object(), 2451545.0)


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        instantaneous_clipped_central_boundary(None, float('nan'))
    with pytest.raises(ValueError):
        instantaneous_clipped_central_boundary(None, 2451545.0, arc_samples=2)


@pytest.mark.parametrize("minute", [6, 10])
def test_nearby_snapshots_preserve_arc_junctions(eclipse_calculator, minute):
    result = instantaneous_clipped_central_boundary(
        eclipse_calculator, julian_day(2003, 5, 31, 4+minute/60)
    )
    def separation(a, b):
        return math.sqrt(sum((x-y)**2 for x, y in zip(a.xyz_itrf_km, b.xyz_itrf_km)))
    assert separation(result.cone_arc[-1], result.horizon_arc[0]) < 0.001
    assert separation(result.horizon_arc[-1], result.cone_arc[0]) < 0.001

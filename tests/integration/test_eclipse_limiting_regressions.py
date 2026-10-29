"""Named eclipse limits: native geometry invariants plus catalog identity.

Issue discovery: https://github.com/TheDaniel166/moira/issues/24
Published solar date/type references (VSOP87/ELP2000-82; not Moira's model):
https://eclipse.gsfc.nasa.gov/SEcat5/SE1801-1900.html
https://eclipse.gsfc.nasa.gov/SEcat5/SE1901-2000.html
https://eclipse.gsfc.nasa.gov/SEcat5/SE2001-2100.html
https://eclipse.gsfc.nasa.gov/SEcat5/SE2101-2200.html

The one-day identity window makes no subsecond clock or exact catalog-parity
claim. Native cone/WGS-84 overlap supplies the independent physical checks.
The lunar limiting row explicitly retains the two declared vector policies.
"""

import math

import pytest

import moira.eclipse as eclipse
from moira.eclipse_canon import lunar_canon_geometry
from moira.julian import julian_day


pytestmark = pytest.mark.requires_ephemeris

POLAR_PARTIALS = (
    (1862, 11, 21), (1880, 12, 2), (1898, 12, 13), (1916, 12, 24),
    (1928, 6, 17), (1931, 9, 12), (1935, 1, 5), (2054, 8, 3),
    (2069, 5, 20), (2098, 10, 24), (2145, 10, 16),
)


@pytest.mark.parametrize("date", POLAR_PARTIALS, ids=lambda date: "%04d-%02d-%02d" % date)
def test_polar_partial_survives_snapshot_forward_backward_and_bulk_discovery(
    eclipse_calculator, date,
):
    target = julian_day(*date)
    forward = eclipse_calculator.next_solar_eclipse(target - 1.0)
    backward = eclipse_calculator.previous_solar_eclipse(target + 2.0)
    bulk = eclipse_calculator.solar_eclipses_in_range(target - 1.0, target + 2.0)
    assert len(bulk) == 1
    for event in (forward, backward, bulk[0]):
        assert target <= event.jd_ut < target + 1.0
        assert event.data.is_solar_eclipse
        assert event.data.eclipse_type.is_partial
        assert event.data.angular_separation_3d > 1.5
        assert 0.0 < event.data.eclipse_magnitude < 1.0
        assert event.data == eclipse_calculator.calculate_jd(event.jd_ut)

    shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, forward.jd_ut)
    azimuth, margin = eclipse._penumbral_generator_extrema(shadow)[0]
    assert margin > 0.0
    point = eclipse._penumbral_generator_point(shadow, azimuth)
    assert point is not None
    x, y, z = point.xyz_itrf_km
    assert (
        (x*x + y*y) / eclipse.EARTH_RADIUS_KM**2
        + z*z / eclipse._WGS84_POLAR_RADIUS_KM**2
    ) == pytest.approx(1.0, abs=2.0e-12)
    assert eclipse._central_generator_extrema(shadow)[0][1] < 0.0


@pytest.mark.parametrize(
    "date", [(1855, 4, 16), (1953, 1, 15)],
    ids=lambda date: "%04d-%02d-%02d" % date,
)
def test_wider_candidate_window_does_not_create_phantom_eclipses(eclipse_calculator, date):
    target = julian_day(*date)
    candidate = eclipse.next_moon_phase(
        "New Moon", target - 2.0, reader=eclipse_calculator._reader,
    ).jd_ut
    greatest = eclipse._refine_solar_maximum(eclipse_calculator, candidate, tol_days=1e-9)
    snapshot = eclipse_calculator.calculate_jd(greatest)
    assert 1.5 < snapshot.angular_separation_3d < 2.0
    assert not snapshot.is_solar_eclipse
    assert snapshot.eclipse_magnitude == 0.0
    assert eclipse_calculator.solar_eclipses_in_range(target - 1.0, target + 2.0) == []
    shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, greatest)
    assert eclipse._penumbral_generator_extrema(shadow)[0][1] < 0.0


def test_2051_solar_eclipse_is_partial_with_no_umbral_surface_overlap(eclipse_calculator):
    """NASA: P, 0.9849; 0.0002 is a named cross-model magnitude envelope.

    https://eclipse.gsfc.nasa.gov/SEsearch/SEdata.php?Ecl=20510411
    """
    target = julian_day(2051, 4, 11)
    event = eclipse_calculator.next_solar_eclipse(target - 1.0, kind="partial")
    assert target <= event.jd_ut < target + 1.0
    assert event.data.eclipse_type.is_partial
    assert event.data.eclipse_magnitude == pytest.approx(0.9849, abs=0.0002)
    shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, event.jd_ut)
    assert eclipse._axis_surface_point_from_shadow(shadow) is None
    assert eclipse._penumbral_generator_extrema(shadow)[0][1] > 0.0
    assert eclipse._central_generator_extrema(shadow)[0][1] < 0.0


@pytest.mark.parametrize(
    ("date", "kind"),
    [((2043, 4, 9), "total"), ((2014, 4, 29), "annular")],
)
def test_noncentral_total_and_annular_remain_distinct_from_axis_centrality(
    eclipse_calculator, date, kind,
):
    """NASA T+/A- controls, SEdata.php?Ecl=20430409 and =20140429."""
    target = julian_day(*date)
    event = eclipse_calculator.next_solar_eclipse(target - 1.0, kind=kind)
    assert target <= event.jd_ut < target + 1.0
    assert str(event.data.eclipse_type).lower() == kind
    shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, event.jd_ut)
    assert eclipse._axis_surface_point_from_shadow(shadow) is None
    assert eclipse._central_generator_extrema(shadow)[0][1] > 0.0
    central = eclipse_calculator.next_solar_eclipse(target - 1.0, kind="central")
    assert central.jd_ut > target + 2.0
    # A real noncentral eclipse does not acquire a fictitious central path.
    path = eclipse_calculator.solar_eclipse_path(target - 1.0, kind=kind)
    assert path.central_line_lats == path.central_line_lons == ()
    assert path.umbral_width_km is None
    assert path.duration_at_max_s > 0.0
    assert len(path.noncentral_footprints) >= 9


@pytest.mark.parametrize(
    "date",
    [(1858, 3, 15), (1876, 3, 25), (1927, 1, 3), (1948, 5, 9), (2146, 3, 12)],
    ids=lambda date: "%04d-%02d-%02d" % date,
)
def test_near_hybrid_annular_catalog_controls_keep_native_type(eclipse_calculator, date):
    """NASA A controls: the repair must preserve the native hybrid criterion."""
    target = julian_day(*date)
    event = eclipse_calculator.next_solar_eclipse(target - 1.0)
    assert target <= event.jd_ut < target + 1.0
    assert event.data.eclipse_type.is_annular
    assert not event.data.eclipse_type.is_hybrid
    assert 0.999 < event.data.eclipse_magnitude < 1.0


def test_2015_lunar_limit_preserves_native_and_compatibility_models(eclipse_calculator):
    """NASA publishes T/1.0008; native is a separate physical-Moon product.

    https://eclipse.gsfc.nasa.gov/OH/OH2015.html
    """
    start = julian_day(2015, 4, 1)
    native = eclipse_calculator.next_lunar_eclipse(start)
    canon = eclipse_calculator.next_lunar_eclipse_canon(start)
    target = julian_day(2015, 4, 4)
    for event in (native, canon):
        assert target <= event.jd_ut < target + 1.0
    assert native.data.eclipse_type.is_partial
    assert 0.999 < native.data.eclipse_magnitude < 1.0
    assert canon.data.eclipse_type.is_total
    assert 1.0 < canon.data.eclipse_magnitude < 1.002
    assert native.data == eclipse_calculator.calculate_jd(native.jd_ut)

    # Shared TT removes the distinct reporting clocks and event maxima from
    # the comparison. Both paths use Danjon; the state reduction flips type.
    tt = eclipse_calculator._jd_tt_from_ut(native.jd_ut)
    axis, _, moon_radius, umbra_radius, _, _ = (
        eclipse_calculator._native_lunar_event_axis_geometry_tt(tt, retarded_moon=False)
    )
    apparent = lunar_canon_geometry(eclipse_calculator, tt)
    apparent_margin = (
        (apparent.umbra_radius_earth_radii - apparent.moon_radius_earth_radii)
        * eclipse.EARTH_RADIUS_KM - apparent.axis_km
    )
    assert umbra_radius - moon_radius - axis < 0.0 < apparent_margin
    assert abs(umbra_radius - apparent.umbra_radius_earth_radii * eclipse.EARTH_RADIUS_KM) < 0.01
    geometric = lunar_canon_geometry(eclipse_calculator, tt, method="nasa_shadow_axis_geometric_moon")
    assert geometric.axis_km == pytest.approx(axis, abs=0.002)
    assert 3.0 < axis - apparent.axis_km < 5.0
    partial = eclipse_calculator.next_lunar_eclipse(start, kind="partial")
    assert partial.jd_ut == native.jd_ut
    assert eclipse_calculator.next_lunar_eclipse(start, kind="total").jd_ut > target + 20.0


def test_1986_near_hybrid_survives_every_solar_search_path(eclipse_calculator):
    """NASA: H, magnitude 1.0000, 1 km path, 00m00s duration; native magnitude 0.99995.

    https://eclipse.gsfc.nasa.gov/SEsearch/SEdata.php?Ecl=19861003

    The penumbral greatest-point refinement once exhausted its iteration
    budget on this event's long, narrow clearance ridge, so every Python-route
    search raised. The native/NASA type difference at this limit is a declared
    model difference and is deliberately not asserted here.
    """
    target = julian_day(1986, 10, 3)
    forward = eclipse_calculator.next_solar_eclipse(target - 30.0)
    backward = eclipse_calculator.previous_solar_eclipse(target + 30.0)
    python_range = eclipse_calculator._solar_eclipses_in_range_python(
        target - 1.0, target + 2.0,
    )
    bulk = eclipse_calculator.solar_eclipses_in_range(target - 1.0, target + 2.0)
    assert len(python_range) == len(bulk) == 1
    for event in (forward, backward, python_range[0], bulk[0]):
        assert target <= event.jd_ut < target + 1.0
        assert event.data.is_solar_eclipse
        assert not event.data.eclipse_type.is_partial
        assert 0.999 < event.data.eclipse_magnitude < 1.001
        assert event.data == eclipse_calculator.calculate_jd(event.jd_ut)


def test_penumbral_greatest_point_is_a_local_maximum_on_a_narrow_ridge(
    eclipse_calculator,
):
    # The search epoch below is where the pre-repair refinement raised. Its
    # clearance ridge is ~100 km long and only a few km wide. The returned
    # site must not be beaten anywhere on rings out to 30 km by more than the
    # quadratic loss implied by the solver's 1 m finest step.
    jd_ut = 2446707.2880275436
    shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, jd_ut)
    site = eclipse._solve_solar_penumbral_greatest_point(
        eclipse_calculator, jd_ut, shadow=shadow, include_solar_limb=True,
    )

    def clearance(latitude_deg, longitude_deg):
        return eclipse._penumbral_clearance_km(
            shadow, eclipse._wgs84_surface_xyz_km(latitude_deg, longitude_deg),
        )

    best = clearance(site.latitude_deg, site.longitude_deg)
    for radius_km in (0.01, 0.1, 1.0, 5.0, 30.0):
        for index in range(72):
            angle = index * math.tau / 72.0
            latitude_deg, longitude_deg = eclipse._offset_geographic_km(
                site.latitude_deg,
                site.longitude_deg,
                radius_km * math.cos(angle),
                radius_km * math.sin(angle),
            )
            assert clearance(latitude_deg, longitude_deg) <= best + 1.0e-5

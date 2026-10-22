"""Noncentral physical shadow products: native invariants and bounded NASA anchors.

The NASA path tables use WGS84 and spherical mean limbs but different state
policies: DE405 / Delta T=67.3 s (2014) and VSOP87/ELP2000-85 / 86.4 s (2043).
Their absence of a central line/width is a topology reference. The 2014
day-side cone envelope admits 0.2 degrees, a cross-model envelope rather than
an accuracy claim. Published horizon anchors are tested as covered horizon
sites, not misidentified as C=0 cone edges. Physical cone and ellipsoid
residuals supply the independent main proof.
"""

from dataclasses import replace
import math

import pytest

import moira.eclipse as eclipse
from moira.julian import julian_day


pytestmark = pytest.mark.requires_ephemeris


@pytest.fixture(params=[((2014, 4, 29), "annular"), ((2043, 4, 9), "total")])
def noncentral_case(request, eclipse_calculator):
    date, kind = request.param
    start = julian_day(*date) - 1.0
    path = eclipse_calculator.solar_eclipse_path(start, kind=kind, sample_count=9)
    global_result = eclipse_calculator.solar_global_circumstances(start, kind=kind)
    return date, kind, start, path, global_result


def test_noncentral_path_global_geometry_and_duration(eclipse_calculator, noncentral_case):
    _, kind, start, path, result = noncentral_case
    assert path.central_line_lats == path.central_line_lons == ()
    assert path.umbral_width_km is None
    assert result.greatest.path_width_km is None
    assert result.first_central_line_limit is result.last_central_line_limit is None
    assert result.greatest.local_class == kind
    assert result.greatest_duration.local_class == kind
    assert result.greatest_duration.path_width_km is None
    assert result.greatest_duration.central_duration_seconds >= path.duration_at_max_s > 0.0
    contacts = result.umbral_contacts
    assert contacts.u2 is contacts.u3 is None
    assert (result.footprint.contacts.p1.point.jd_ut < contacts.u1.epoch.jd_ut1
            < result.event.jd_ut < contacts.u4.epoch.jd_ut1
            < result.footprint.contacts.p4.point.jd_ut)
    times = tuple(item.jd_ut for item in path.noncentral_footprints)
    assert tuple(sorted(set(times))) == times
    assert times[0] == contacts.u1.epoch.jd_ut1
    assert times[-1] == contacts.u4.epoch.jd_ut1
    assert result.event.jd_ut in times
    for snapshot in path.noncentral_footprints:
        assert snapshot.horizon_policy == "UNCLIPPED_PHYSICAL_CONE"
        assert snapshot.boundary[0] == snapshot.boundary[-1]
        shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, snapshot.jd_ut)
        assert eclipse._axis_surface_point_from_shadow(shadow) is None
        for point in snapshot.boundary:
            xyz = eclipse._wgs84_surface_xyz_km(point.latitude_deg, point.longitude_deg)
            x, y, z = xyz
            assert ((x*x + y*y) / eclipse.EARTH_RADIUS_KM**2
                    + z*z / eclipse._WGS84_POLAR_RADIUS_KM**2) == pytest.approx(1.0, abs=2e-12)
            # Julian-day binary64 spacing is ~40 microseconds here. The
            # contact-time rounding budget is 1 cm; interior contours use
            # 0.2 mm and do not inherit that temporal rounding budget.
            tolerance = 1e-5 if len(snapshot.boundary) == 1 else 2e-7
            assert eclipse._central_shadow_clearance_km(shadow, xyz) == pytest.approx(0.0, abs=tolerance)
    for contact in (contacts.u1, contacts.u4):
        shadow = eclipse._earth_fixed_solar_shadow(eclipse_calculator, contact.epoch.jd_ut1)
        # The continuous root must lie within the adjacent representable JDs.
        margins = [eclipse._central_generator_extrema(eclipse._earth_fixed_solar_shadow(
            eclipse_calculator, math.nextafter(contact.epoch.jd_ut1, direction),
        ))[0][1] for direction in (-math.inf, math.inf)]
        assert margins[0] * margins[1] <= 0.0
    # Presentation density never creates a central line or moves contact/GE epochs.
    sparse = eclipse_calculator.solar_eclipse_path(start, kind=kind, sample_count=1)
    assert sparse.noncentral_footprints == result.noncentral_footprints
    assert sparse.max_eclipse_lat == path.max_eclipse_lat
    assert sparse.duration_at_max_s == path.duration_at_max_s
    site = result.greatest_duration
    assert eclipse._solve_local_solar_central_duration_s(
        eclipse_calculator, site.epoch.jd_ut1, site.latitude_deg, site.longitude_deg,
        clip_horizon=False,
    ) == pytest.approx(site.central_duration_seconds, abs=1e-4)
    # A missing internal pair is lawful; a fabricated half-pair is not.
    with pytest.raises(ValueError, match="paired"):
        replace(contacts, u2=replace(contacts.u1, kind="u2"))


@pytest.mark.parametrize(
    "date,hour,cone_anchor,horizon_anchor",
    [
        ((2014, 4, 29), 6 + 4/60, (-68 - 19.5/60, 126 + 35.4/60),
                                  (-70 - 30.1/60, 131 + 38.6/60)),
        ((2043, 4, 9), 18 + 56/60, None, (61 + 15.8/60, 152 + 0.8/60)),
    ],
)
def test_noncentral_geometry_against_named_nasa_path_anchors(
    eclipse_calculator, date, hour, cone_anchor, horizon_anchor,
):
    """Sources: https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2014Apr29Apath.html
    and https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2043Apr09Tpath.html.
    The rows contain both cone envelopes and horizon sites. Never compare
    a horizon closure to a C=0 envelope, or NASA 'Limits' to U1/U4.
    """
    epoch = julian_day(*date, hour)
    step = eclipse._SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS
    states = [eclipse._noncentral_shadow_branch(eclipse._earth_fixed_solar_shadow(
        eclipse_calculator, t,
    )) for t in (epoch, epoch-step, epoch+step)]
    if cone_anchor is not None:
        limits = eclipse._penumbral_envelope_points(*states)
        actual = [point for points in limits.values() for point in points]
        latitude, longitude = cone_anchor
        assert any(abs(point.latitude_deg-latitude) < 0.2
                   and abs((point.longitude_deg-longitude+180.0) % 360.0-180.0) < 0.2
                   for point in actual)
    xyz = eclipse._wgs84_surface_xyz_km(*horizon_anchor)
    altitude = math.degrees(math.asin(eclipse._topocentric_solar_altitude_proxy(states[0], xyz)))
    assert abs(altitude) < 0.01  # degrees, cross-model geometric horizon anchor
    assert eclipse._penumbral_clearance_km(states[0], xyz) > 0.0

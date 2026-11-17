"""Frozen native examples corroborate the new real snapshot predicates.

These tests freeze represented ITRF coordinates as exact model inputs.
They do not attest continuous native execution or an event-wide domain.
"""
import math

import pytest

from moira._eclipse_solar_surface_bounds import (SolarSceneBox,bound_scene_on_patch,
    certify_common_solar_ray)
from moira._eclipse_solar_surface_cover import cover_solar_surface_snapshot
from moira._eclipse_surface_patches import patch_through_cartesian_ray
from moira.eclipse import (_earth_fixed_solar_shadow,_axis_surface_point_from_shadow,
    _wgs84_surface_normal_unit)
from moira.solar_disc_visibility import solar_disc_visibility


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('ut1',[2457987.267724502,2460409.275])
def test_2017_and_2024_axis_sites_have_rechecked_visible_common_rays(eclipse_calculator,ut1):
    shadow = _earth_fixed_solar_shadow(eclipse_calculator,ut1)
    point = _axis_surface_point_from_shadow(shadow)
    assert point is not None
    moon = tuple(p+a*shadow.axis_projection_km for p,a in zip(
        shadow.fundamental_plane_point_xyz_km,shadow.axis_unit_away_from_sun))
    scene = SolarSceneBox(shadow.sun_xyz_from_earth_itrf_km,moon)
    patch = patch_through_cartesian_ray(point.xyz_itrf_km)
    bound = bound_scene_on_patch(scene,patch)
    sun_ray = tuple(s-p for s,p in zip(scene.sun_itrf_km,point.xyz_itrf_km))
    moon_ray = tuple(m-p for m,p in zip(scene.moon_itrf_km,point.xyz_itrf_km))
    s,m = (tuple(float(v.midpoint) for v in ray) for ray in (sun_ray,moon_ray))
    ordinary = solar_disc_visibility(s,m,_wgs84_surface_normal_unit(point.xyz_itrf_km),
        math.asin(float(scene.sun_radius_km)/math.hypot(*s)),
        math.asin(float(scene.moon_radius_km)/math.hypot(*m)))
    # The ordinary helper deliberately rejects a near-coincident circle
    # basis. A centre direction is still a lawful, untrusted candidate;
    # the rational cap and horizon margins decide whether it is a witness.
    assert ordinary.status in ('visible','indeterminate')
    hint = ordinary.witness_direction if ordinary.witness_direction is not None else s
    witness = certify_common_solar_ray(bound,hint)
    assert not bound.excluded and witness is not None
    assert witness.horizon_sine.lo>0


@pytest.mark.requires_ephemeris
def test_frozen_nonconjunction_scene_is_excluded_on_all_six_faces(eclipse_calculator):
    # One day after the 2017 positive control, within the source cone's
    # admitted Sunward geometry. No negative sample
    # determines the result: all six entire face rectangles must be excluded.
    shadow = _earth_fixed_solar_shadow(eclipse_calculator,2457988.267724502)
    assert shadow is not None
    moon = tuple(p+a*shadow.axis_projection_km for p,a in zip(
        shadow.fundamental_plane_point_xyz_km,shadow.axis_unit_away_from_sun))
    result = cover_solar_surface_snapshot(SolarSceneBox(shadow.sun_xyz_from_earth_itrf_km,moon),
        max_patch_evaluations=6,max_witness_site_evaluations=0)
    assert result.absence_proved and result.full_spatial_partition_resolved
    assert len(result.cells)==6 and all(c.status=='excluded' for c in result.cells)
    assert not result.time_interval_coverage_proved and not result.source_route_attested

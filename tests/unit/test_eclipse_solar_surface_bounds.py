"""Joint horizon-lens exclusion and strict same-ray controls."""
from fractions import Fraction as F
import math

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_solar_surface_bounds import (bound_common_solar_rays,
    certify_common_solar_ray,SolarSceneBox)
from moira._eclipse_solar_surface_cover import cover_solar_surface_snapshot
from moira.solar_disc_visibility import solar_disc_visibility


def rays(h):
    h,a,r = map(math.radians,(h,.2,.3))
    s = math.cos(h)*math.cos(a),math.cos(h)*math.sin(a),math.sin(h)
    m = s[0],-s[1],s[2]
    result = bound_common_solar_rays(tuple(1e6*x for x in s),tuple(1000*x for x in m),(0,0,1),
        sun_radius_km=1e6*math.sin(r),moon_radius_km=1000*math.sin(r))
    return result,solar_disc_visibility(s,m,(0,0,1),r,r)


def test_joint_certificate_excludes_a_lens_although_each_disc_reaches_horizon():
    b,ordinary = rays(-.24)
    assert ordinary.status=='hidden'
    assert b.excluded and b.reason=='joint_cap_horizon_separation'
    assert b.exclusion_slack.lo>0 and all(w>=0 for w in b.multipliers)
    # Individual-cap horizon predicates cannot exclude this example.
    assert b.sun[2].hi+math.sin(math.radians(.3))>0
    assert b.moon[2].hi+math.sin(math.radians(.3))>0


def test_existing_common_ray_hint_is_rechecked_by_rational_bounds():
    b,ordinary = rays(-.22)
    assert ordinary.status=='visible' and not b.excluded
    witness = certify_common_solar_ray(b,ordinary.witness_direction)
    assert witness is not None
    assert min(witness.sun_clearance.lo,witness.moon_clearance.lo,witness.horizon_sine.lo)>0
    assert certify_common_solar_ray(b,(0,0,1)) is None


@pytest.mark.parametrize('radius,expected',[(59.99,'excluded'),(60.,'unresolved'),(60.01,'visible')])
def test_exact_horizon_tangency_is_not_a_positive_or_negative(radius,expected):
    b = bound_common_solar_rays((8000,0,-6000),(80,0,-60),(0,0,1),
        sun_radius_km=100*radius,moon_radius_km=radius)
    witness = certify_common_solar_ray(b,(1,0,F(1,100000)))
    assert ('excluded' if b.excluded else 'visible' if witness else 'unresolved')==expected


def test_reversed_foreground_order_remains_unsupported():
    with pytest.raises(EnclosureUnavailable,match='foreground'):
        bound_common_solar_rays((1000,0,0),(100000,0,0),(1,0,0),sun_radius_km=10,moon_radius_km=1)


def test_whole_ellipsoid_negative_requires_all_six_faces():
    scene = SolarSceneBox((150000000,0,0),(-400000,0,0))
    result = cover_solar_surface_snapshot(scene,max_patch_evaluations=6)
    assert result.absence_proved and result.full_spatial_partition_resolved
    assert not result.presence_proved and len(result.cells)==6
    assert result.patch_evaluations==6 and all(c.status=='excluded' for c in result.cells)
    assert result.scene==scene and all(c.exclusion_slack.lo>0 for c in result.cells)


def test_a_global_positive_has_a_strict_point_witness_not_a_complete_surface_map():
    scene = SolarSceneBox((150000000,0,0),(400000,0,0))
    result = cover_solar_surface_snapshot(scene,max_patch_evaluations=6)
    assert result.presence_proved and result.witness is not None
    assert not result.absence_proved and not result.full_spatial_partition_resolved
    assert any(c.status=='unresolved' for c in result.cells)
    assert not result.time_interval_coverage_proved and not result.source_route_attested


def test_budget_exhaustion_retains_every_face_and_never_proves_absence():
    result = cover_solar_surface_snapshot(SolarSceneBox((150000000,0,0),(-400000,0,0)),max_patch_evaluations=0)
    assert len(result.cells)==6 and all(c.status=='unresolved' for c in result.cells)
    assert not result.presence_proved and not result.absence_proved
    assert result.patch_evaluations==result.witness_site_evaluations==0


def test_rejected_geometry_is_a_covering_unknown():
    result = cover_solar_surface_snapshot(SolarSceneBox((1000,0,0),(100000,0,0)),
        max_patch_evaluations=6,max_witness_site_evaluations=0,max_depth=0)
    assert len(result.cells)==6 and all(c.status=='unresolved' for c in result.cells)
    assert not result.absence_proved


def test_subdivision_and_exhaustion_preserve_parameter_area_on_every_face():
    result = cover_solar_surface_snapshot(SolarSceneBox((150000000,0,0),(400000,0,0)),
        max_patch_evaluations=25,max_witness_site_evaluations=0,stop_after_witness=False)
    for axis in range(3):
        for sign in (-1,1):
            leaves = [c.patch for c in result.cells if (c.patch.axis,c.patch.sign)==(axis,sign)]
            assert sum(p.u.width*p.v.width for p in leaves)==4
    assert not result.absence_proved


def test_a_scene_box_is_not_replaced_by_its_visible_midpoint():
    scene = SolarSceneBox((150000000,0,0),(I.point(400000),I(-15000,15000),I.point(0)))
    result = cover_solar_surface_snapshot(scene,max_patch_evaluations=6,max_witness_site_evaluations=6,max_depth=0)
    assert not result.presence_proved and not result.absence_proved
    assert any(c.status=='unresolved' for c in result.cells)


@pytest.mark.parametrize('kwargs',[{'max_patch_evaluations':True},
    {'max_witness_site_evaluations':-1},{'max_depth':True},
    {'stop_after_witness':'yes'},{'min_parameter_width':0}])
def test_budget_and_stop_controls_are_explicit(kwargs):
    with pytest.raises((ValueError,TypeError)):
        cover_solar_surface_snapshot(SolarSceneBox((150000000,0,0),(400000,0,0)),**kwargs)


def test_an_unavailable_native_shadow_is_not_accepted_as_an_empty_scene():
    with pytest.raises(TypeError,match='SolarSceneBox'):
        cover_solar_surface_snapshot(None)

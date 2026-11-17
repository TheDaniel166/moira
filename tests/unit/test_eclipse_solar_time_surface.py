"""Whole interval/surface controls, including a midpoint-negative trap."""
from fractions import Fraction as F

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_solar_surface_bounds import SolarSceneBox
from moira._eclipse_solar_time_surface import cover_solar_time_surface, global_disc_separation
from moira._eclipse_surface_patches import EllipsoidPatch


def test_whole_time_earth_separation_excludes_without_a_scene_or_shadow():
    def forbidden(_):
        raise AssertionError('orientation and cone eligibility are unnecessary')
    def separation(t):
        return global_disc_separation((150000000,0,0),(-380000,1000*t,0))
    cover = cover_solar_time_surface(I(-17,17),forbidden,separation_provider=separation)
    assert cover.absence_proved and cover.time_interval_coverage_proved
    assert not cover.unresolved and cover.cells[0].time == I(-17,17)
    assert cover.cells[0].patch is None  # whole six-chart ellipsoid


def test_midpoint_miss_does_not_discard_short_positive_interval():
    # The complete input box spans the alignment at t=1/8, although t=0
    # and both endpoints miss it. This is a provider contract test, not
    # an ephemeris trajectory or an invented physical time scale.
    def scene(t):
        return SolarSceneBox((150000000,0,0),(380000,200000*(t-F(1,8)),0))
    def separation(t):
        s = scene(t)
        return global_disc_separation(s.sun_itrf_km,s.moon_itrf_km)
    assert separation(I.point(0)).lo > 0
    cover = cover_solar_time_surface(I(-1,1),scene,separation_provider=separation,
        witness_hints=((F(1,8),EllipsoidPatch(0,1,I.point(0),I.point(0)),None),))
    assert cover.presence_proved and not cover.absence_proved
    assert cover.witness.time == F(1,8) and cover.unresolved[0].time == I(-1,1)


def test_missing_provider_and_budget_leave_exact_full_domain_unknown():
    def unavailable(_):
        from moira._eclipse_interval_roots import EnclosureUnavailable
        raise EnclosureUnavailable('missing resource')
    for calls in (0,3):
        cover = cover_solar_time_surface(I(-2,3),unavailable,
            separation_provider=unavailable,max_evaluations=calls)
        assert not cover.absence_proved and not cover.presence_proved
        assert cover.unresolved and cover.full_domain_retained
        intervals = sorted((c.time for c in cover.cells),key=lambda t:t.lo)
        assert intervals[0].lo == -2 and intervals[-1].hi == 3
        assert all(a.hi == b.lo for a,b in zip(intervals,intervals[1:]))


def test_false_witness_hint_is_rechecked_and_rejected():
    def scene(_):
        return SolarSceneBox((150000000,0,0),(-380000,0,0))
    result = cover_solar_time_surface(I(-1,1),scene,
        witness_hints=((0,EllipsoidPatch(0,1,I.point(0),I.point(0)),(1,0,0)),),
        max_evaluations=1)
    assert not result.presence_proved and result.unresolved


def test_unseeded_product_search_finds_and_rechecks_a_ray():
    def scene(_):
        return SolarSceneBox((150000000,0,0),(380000,0,0))
    result = cover_solar_time_surface(I(F(-1,100000),F(1,100000)),scene,
                                      max_evaluations=100,max_surface_depth=6)
    assert result.presence_proved and not result.absence_proved
    assert result.unresolved and result.witness.patch.u.width == 0

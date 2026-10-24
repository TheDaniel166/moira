"""Regression laws for primary-direction search dependencies, clocks and timelines."""

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from moira.constants import Body, HouseSystem, TROPICAL_YEAR
from moira.egyptian_bounds import EgyptianBoundsDoctrine
from moira.julian import _ut1_to_utc, safe_datetime_from_jd, utc_to_tt, utc_to_ut1
from moira.primary_directions import (
    PlacidianRaptParallelTarget, PrimaryDirectionFixedStarTarget,
    PrimaryDirectionAntisciaTarget, PrimaryDirectionMidpointTarget,
    PrimaryDirectionKey, PrimaryDirectionKeyPolicy, PrimaryDirectionMotion,
    PrimaryDirectionTargetClass, PrimaryDirectionTargetPolicy,
    PrimaryDirectionsPreset, compute_primary_directions_timeline,
    find_primary_arcs, primary_directions_policy_preset,
    resolve_primary_direction_bound_targets,
)
from moira.primary_directions.distributor import resolve_distributor_chronology
from moira.primary_directions.keys import project_primary_direction_arc_time


@pytest.fixture(scope="module")
def figure(moira_engine):
    moment = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    return (
        moira_engine.chart(moment),
        moira_engine.houses(moment, 51.5, 0., system=HouseSystem.PLACIDUS),
        moira_engine._reader_obj,
    )


def _timeline(figure, **kwargs):
    chart, houses, reader = figure
    options = dict(significators=["ASC"], max_age_years=100., reader=reader)
    options.update(kwargs)
    return compute_primary_directions_timeline(chart, houses, 51.5, **options)


def _partition(timeline):
    return tuple((p.significator, p.motion, p.entry_arc_deg, p.exit_arc_deg,
                  p.ruler, p.sign, p.bound_start_deg, p.bound_end_deg)
                 for p in timeline.distributor_periods)


@pytest.mark.parametrize("promissors", [[Body.SUN], [Body.JUPITER], []])
def test_event_filter_preserves_the_complete_distributor_partition(figure, promissors):
    full = _timeline(figure)
    selected = _timeline(figure, promissors=promissors)
    assert len(full.distributor_periods) > 2
    assert _partition(selected) == _partition(full)
    expected = [e for e in full.events if e.promissor in promissors]
    assert selected.events == tuple(expected)
    for period in selected.distributor_periods:
        assert all(a.promissor in promissors for a in period.participators)


@pytest.mark.parametrize("container", [tuple, iter])
def test_significator_and_promissor_iterables_have_list_semantics(figure, container):
    expected = _timeline(figure, significators=[Body.VENUS], promissors=[Body.MOON])
    actual = _timeline(figure, significators=container([Body.VENUS]),
                       promissors=container([Body.MOON]))
    assert actual == expected
    assert {p.significator for p in actual.distributor_periods} == {Body.VENUS}


def test_empty_significators_do_not_invent_an_ascendant_period(figure):
    result = _timeline(figure, significators=iter(()))
    assert result.events == result.distributor_periods == ()


@pytest.mark.parametrize("names", ["ASC", ["ASC", "ASC"], [""]])
def test_timeline_preserves_identity_validation(figure, names):
    with pytest.raises(ValueError):
        _timeline(figure, significators=names)


@pytest.mark.parametrize("motion", [PrimaryDirectionMotion.DIRECT, PrimaryDirectionMotion.CONVERSE])
def test_rapt_timeline_uses_matching_admitted_bound_motion(figure, motion):
    chart, houses, _ = figure
    preset = (PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT
              if motion is PrimaryDirectionMotion.DIRECT
              else PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE)
    policy = primary_directions_policy_preset(
        preset, include_converse=False,
        placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget(Body.MOON),))
    result = _timeline(figure, policy=policy, significators=[Body.VENUS],
                       max_age_years=400., max_arc=360., promissors=["Moon Rapt Parallel"])
    assert result.events
    assert {p.motion for p in result.distributor_periods} == {motion}
    # The structural chronology uses the existing ordinary bound law with the
    # same method, latitude and named traditional-converse construction.
    bounds = resolve_primary_direction_bound_targets()
    ordinary = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_CLASSIC_MUNDANE,
        include_converse=True, bound_targets=bounds)
    boundary_arcs = find_primary_arcs(chart, houses, 51.5, policy=ordinary,
        max_arc=360., significators=[Body.VENUS], promissors=[b.name for b in bounds])
    expected = resolve_distributor_chronology(
        Body.VENUS, chart.planets[Body.VENUS].longitude, boundary_arcs,
        motion=motion, max_arc=360.)
    assert [(p.entry_arc_deg, p.exit_arc_deg, p.ruler) for p in result.distributor_periods] == [
        (p.entry_arc_deg, p.exit_arc_deg, p.ruler) for p in expected]
    for event in result.events:
        assert event.motion is motion
        period = next(p for p in result.distributor_periods
                      if p.entry_arc_deg <= event.arc_deg < p.exit_arc_deg)
        assert event.distributor == period.ruler
        assert any(a.promissor == event.promissor for a in period.participators)


@pytest.mark.parametrize("kind", ["conflict", "mixed", "partial", "wrong_coordinate"])
def test_timeline_rejects_noncanonical_or_conflicting_bound_tables(figure, kind):
    egyptian = resolve_primary_direction_bound_targets()
    ptolemaic = resolve_primary_direction_bound_targets(EgyptianBoundsDoctrine.PTOLEMAIC)
    if kind == "conflict":
        targets = ptolemaic
    elif kind == "mixed":
        targets = (ptolemaic[0],) + egyptian[1:]
    elif kind == "partial":
        targets = egyptian[:-1]
    else:
        targets = (replace(egyptian[0], absolute_longitude=1.),) + egyptian[1:]
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
                                             bound_targets=targets)
    with pytest.raises(ValueError, match="bound"):
        _timeline(figure, policy=policy)


@pytest.mark.parametrize("doctrine", list(EgyptianBoundsDoctrine))
def test_matching_complete_bound_table_is_accepted_in_any_order(figure, doctrine):
    bounds = resolve_primary_direction_bound_targets(doctrine)
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
                                             bound_targets=tuple(reversed(bounds)))
    actual = _timeline(figure, policy=policy, bound_doctrine=doctrine)
    expected = _timeline(figure, bound_doctrine=doctrine)
    assert actual == expected


@pytest.mark.parametrize("key", list(PrimaryDirectionKey))
def test_automatic_horizon_covers_the_requested_age_with_the_selected_key(figure, key):
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.MERIDIAN_MUNDANE,
                                             key_policy=PrimaryDirectionKeyPolicy(key))
    result = _timeline(figure, policy=policy, key=key, max_age_years=250.)
    assert result.events
    assert max(p.exit_age for p in result.distributor_periods) == pytest.approx(250., abs=2e-5)
    # A wider explicit core search is an independent completeness comparison;
    # it must not find in-range events omitted by the automatic horizon.
    wider = _timeline(figure, policy=policy, key=key, max_age_years=250., max_arc=360.)
    assert result.events == wider.events


@pytest.mark.parametrize("key", list(PrimaryDirectionKey))
def test_automatic_horizon_rejects_an_unrepresentable_primary_rotation(figure, key):
    with pytest.raises(ValueError, match="rotation"):
        _timeline(figure, key=key, max_age_years=1000.)


@pytest.mark.parametrize("key", [PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
                                 PrimaryDirectionKey.SOLAR_LON_DYNAMIC])
def test_cycle_midpoint_does_not_truncate_the_last_admissible_arc(monkeypatch, key):
    import moira.primary_directions.keys as keys
    import moira._solar as solar
    natal = 2451545.
    # A linear coordinate isolates the stopping-bracket law: the true cycle
    # is at 360 days, but a valid bisection midpoint can precede it.
    def coordinate(jd, reader):
        return (jd - natal) % 360.

    monkeypatch.setattr(solar, "_solar_longitude", coordinate)
    monkeypatch.setattr(solar, "_solar_declination_ra", lambda jd, reader: (0., coordinate(jd, reader)))
    name = "invert_solar_arc_ra" if key is PrimaryDirectionKey.SOLAR_RA_DYNAMIC else "invert_solar_arc_lon"
    monkeypatch.setattr(keys, name, lambda *args, **kwargs: (360. - 2e-7, natal))
    arc = keys._arc_for_age(natal, 360. - 1e-7, key, solar_rate=None, reader=object())
    assert 359.999999 < arc < 360.
    with pytest.raises(ValueError, match="rotation"):
        keys._arc_for_age(natal, 360. + 1e-7, key, solar_rate=None, reader=object())


def _polar_pair():
    chart = SimpleNamespace(
        planets={Body.SUN: SimpleNamespace(longitude=0., latitude=0., speed=1.),
                 Body.MOON: SimpleNamespace(longitude=10., latitude=0., speed=13.)},
        nodes={}, obliquity=23.4393, jd_ut=2451545., jd_tt=2451545.00074)
    houses = SimpleNamespace(armc=30., asc=0., mc=0., dsc=180., ic=180.,
                             cusps=tuple(i * 30. for i in range(12)))
    return chart, houses


@pytest.mark.parametrize("extra_kind", ["planet", "node", "angle"])
def test_filtered_search_is_independent_of_unrequested_circumpolar_objects(extra_kind):
    chart, houses = _polar_pair()
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
                                             include_converse=False)
    options = dict(policy=policy, max_arc=360., significators=[Body.SUN], promissors=[Body.MOON])
    expected = find_primary_arcs(chart, houses, 70., **options)
    assert expected and expected[0].arc == pytest.approx(12.844948338345027, abs=1e-10)
    if extra_kind == "planet":
        chart.planets[Body.VENUS] = SimpleNamespace(longitude=90., latitude=0., speed=1.)
    elif extra_kind == "node":
        chart.nodes[Body.TRUE_NODE] = SimpleNamespace(longitude=90.)
    else:
        houses.asc = 90.
    assert find_primary_arcs(chart, houses, 70., **options) == expected


def test_requested_circumpolar_source_still_fails_closed():
    chart, houses = _polar_pair()
    chart.planets[Body.MOON].longitude = 90.
    with pytest.raises(ValueError, match="semi-arcs"):
        find_primary_arcs(chart, houses, 70., significators=[Body.SUN], promissors=[Body.MOON])


def test_policy_excluded_circumpolar_objects_are_not_search_dependencies():
    chart, houses = _polar_pair()
    planets = frozenset({PrimaryDirectionTargetClass.PLANET})
    policy = replace(primary_directions_policy_preset(PrimaryDirectionsPreset.PTOLEMY_MUNDANE),
                     target_policy=PrimaryDirectionTargetPolicy(planets, planets))
    expected = find_primary_arcs(chart, houses, 70., policy=policy, max_arc=360.)
    assert expected
    chart.nodes[Body.TRUE_NODE] = SimpleNamespace(longitude=90.)
    houses.asc = 90.
    assert find_primary_arcs(chart, houses, 70., policy=policy, max_arc=360.) == expected


@pytest.mark.parametrize("family", ["aspect", "midpoint", "antiscion", "rapt"])
def test_filtered_search_retains_derived_target_source_dependencies(family):
    chart, houses = _polar_pair()
    kwargs = {}
    preset = PrimaryDirectionsPreset.PTOLEMY_MUNDANE
    if family == "aspect":
        preset = PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT
        name = "Moon Opposition"
    elif family == "midpoint":
        target = PrimaryDirectionMidpointTarget(Body.SUN, Body.MOON)
        kwargs["midpoint_targets"] = (target,)
        name = target.name
    elif family == "antiscion":
        preset = PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA
        target = PrimaryDirectionAntisciaTarget(Body.MOON)
        kwargs["antiscia_targets"] = (target,)
        name = target.name
    else:
        preset = PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT
        target = PlacidianRaptParallelTarget(Body.MOON)
        kwargs["placidian_rapt_parallel_targets"] = (target,)
        name = target.name
    policy = primary_directions_policy_preset(preset, include_converse=False, **kwargs)
    options = dict(policy=policy, max_arc=360., significators=[Body.SUN], promissors=[name])
    expected = find_primary_arcs(chart, houses, 70., **options)
    assert expected
    chart.planets[Body.VENUS] = SimpleNamespace(longitude=90., latitude=0., speed=1.)
    assert find_primary_arcs(chart, houses, 70., **options) == expected


def test_converse_rapt_and_direct_fixed_star_keep_separate_period_context(figure):
    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE,
        include_converse=False,
        placidian_rapt_parallel_targets=(PlacidianRaptParallelTarget(Body.MOON),),
        fixed_star_targets=(PrimaryDirectionFixedStarTarget("Sirius"),))
    result = _timeline(figure, policy=policy, significators=[Body.VENUS],
                       max_age_years=400., max_arc=360.)
    assert {e.motion for e in result.events} == set(PrimaryDirectionMotion)
    for event in result.events:
        period = next(p for p in result.distributor_periods if p.motion is event.motion
                      and p.entry_arc_deg <= event.arc_deg < p.exit_arc_deg)
        assert event.distributor == period.ruler
        if not event.is_bound_boundary:
            assert any(a.promissor == event.promissor for a in period.participators)


def test_fixed_star_tt_only_and_legacy_ut1_snapshots_retain_their_clock_contract():
    from moira.primary_directions._chart_time import _chart_tt, _chart_ut1

    assert _chart_tt(SimpleNamespace(jd_tt=2451545.25)) == 2451545.25
    legacy = SimpleNamespace(jd_ut=2451545., delta_t=64.)
    assert _chart_ut1(legacy) == 2451545.
    assert _chart_tt(legacy) == 2451545. + 64. / 86400.
    with pytest.raises(ValueError, match="finite"):
        _chart_tt(SimpleNamespace(jd_tt=float("nan")))


def test_fixed_star_receives_facade_tt_without_adding_delta_t_to_utc(figure, monkeypatch):
    import moira.primary_directions as pd
    chart, houses, _ = figure
    witnessed = []

    def star(target, *, jd_tt):
        witnessed.append(jd_tt)
        return target.star_name, 140., 0.

    monkeypatch.setattr(pd, "resolve_primary_direction_fixed_star_point", star)
    policy = primary_directions_policy_preset(PrimaryDirectionsPreset.MERIDIAN_MUNDANE,
        fixed_star_targets=(PrimaryDirectionFixedStarTarget("Sirius"),))
    find_primary_arcs(chart, houses, 51.5, policy=policy,
                      significators=["MC"], promissors=["Sirius"])
    # At J2000 the atomic relation is TT-UTC = 32 + 32.184 seconds.
    expected_tt = chart.jd_ut + 64.184 / 86400.
    assert witnessed == pytest.approx([expected_tt], abs=1e-10)
    assert abs((witnessed[0] - (chart.jd_ut + chart.delta_t / 86400.)) * 86400.) > .3


@pytest.mark.parametrize("key", [PrimaryDirectionKey.PTOLEMY,
                                 PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
                                 PrimaryDirectionKey.SOLAR_LON_DYNAMIC])
def test_facade_and_explicit_ut1_charts_have_identical_timeline_clocks(figure, key):
    chart, houses, reader = figure
    explicit = SimpleNamespace(planets=chart.planets, nodes=chart.nodes,
        obliquity=chart.obliquity, jd_ut=utc_to_ut1(chart.jd_ut),
        jd_tt=utc_to_tt(chart.jd_ut), delta_t=chart.delta_t)
    expected = compute_primary_directions_timeline(explicit, houses, 51.5, key=key,
        reader=reader, significators=["MC"], promissors=[Body.MOON], max_age_years=80.)
    actual = _timeline(figure, key=key, significators=["MC"], promissors=[Body.MOON],
                        max_age_years=80.)
    assert actual == expected
    assert actual.natal_jd_ut == utc_to_ut1(chart.jd_ut)
    for event in actual.events:
        age, jd_ut1 = project_primary_direction_arc_time(
            actual.natal_jd_ut, event.arc_deg, key, reader=reader)
        assert event.age_years == age
        assert event.perfection_jd_ut == jd_ut1
        assert event.perfection_iso == safe_datetime_from_jd(_ut1_to_utc(jd_ut1)).isoformat()
    for period in actual.distributor_periods:
        jd_ut1 = actual.natal_jd_ut + period.exit_age * TROPICAL_YEAR
        assert period.exit_date_utc == safe_datetime_from_jd(_ut1_to_utc(jd_ut1)).isoformat()

"""Source-bound Fortune and existing-office composition, without synthetic planets."""

from dataclasses import replace
from datetime import datetime, timezone
import math
from types import SimpleNamespace

import pytest

from moira.constants import HouseSystem, Body
from moira.hellenistic_offices import find_predominator_ptolemy
from moira.lots import calculate_lots
from moira.primary_directions import (
    PrimaryDirectionFortuneDoctrine as Formula,
    PrimaryDirectionFortuneTarget as Fortune,
    PrimaryDirectionPredominatorTarget as Predominator,
    PrimaryDirectionKey, PrimaryDirectionKeyPolicy, PrimaryDirectionMotion,
    PrimaryDirectionTargetClass, PrimaryDirectionTargetPolicy,
    PrimaryDirectionAntisciaTarget, PrimaryDirectionMidpointTarget,
    PrimaryDirectionsPolicy, PrimaryDirectionsPreset,
    compute_primary_directions_timeline, find_primary_arcs,
    primary_directions_policy_preset, resolve_primary_direction_derived_point,
)
from moira.primary_directions.targets import (
    classify_primary_direction_target, primary_direction_target_truth,
)


def _figure(**overrides):
    positions = dict(Sun=10., Moon=100., Mercury=20., Venus=40., Mars=80.,
                     Jupiter=200., Saturn=300.)
    positions.update(overrides)
    chart = SimpleNamespace(
        planets={name: SimpleNamespace(longitude=lon, latitude=5. if name == "Moon" else 0., speed=1.)
                 for name, lon in positions.items()},
        nodes={}, obliquity=23.44, jd_ut=2451545.,
    )
    houses = SimpleNamespace(asc=100., mc=10., dsc=280., ic=190., armc=9.19,
                             cusps=tuple((100. + i * 30) % 360 for i in range(12)))
    return chart, houses, positions


def _policy(*targets, preset=PrimaryDirectionsPreset.PTOLEMY_MUNDANE, **kwargs):
    return primary_directions_policy_preset(preset, derived_point_targets=targets, **kwargs)


@pytest.mark.parametrize("day", [True, False])
def test_ptolemy_fortune_is_unreversed_with_zero_ecliptic_latitude(day):
    chart, houses, _ = _figure(Sun=350., Moon=20.)
    assert resolve_primary_direction_derived_point(Fortune(is_day_chart=day), chart, houses) == (
        "Fortune", 130., 0.)


@pytest.mark.parametrize("day, expected", [(True, 190.), (False, 10.)])
def test_sect_reversed_fortune_agrees_with_existing_lots_owner(day, expected):
    chart, houses, positions = _figure()
    point = resolve_primary_direction_derived_point(Fortune(Formula.SECT_REVERSED, day), chart, houses)
    lots = calculate_lots(positions, list(houses.cusps), day,
                          asc_longitude=houses.asc, mc_longitude=houses.mc)
    lot = next(lot for lot in lots if lot.name == "Fortune")
    assert point == ("Fortune", expected, 0.)
    assert point[1] == lot.longitude


@pytest.mark.parametrize("kwargs", [dict(doctrine="ptolemy_tetrabiblos_iii_10"),
    dict(doctrine=Formula.SECT_REVERSED), dict(is_day_chart=1), dict(is_day_chart="night")])
def test_fortune_requires_typed_doctrine_and_explicit_sect_when_used(kwargs):
    with pytest.raises(ValueError):
        Fortune(**kwargs)


@pytest.mark.parametrize("selected, overrides, context", [
    ("Sun", {}, dict(is_day_chart=True)),
    ("Moon", dict(Sun=250., Moon=10.), dict(is_day_chart=False)),
    ("ASC", dict(Sun=180., Moon=160., Mercury=150., Venus=150., Mars=150., Jupiter=150., Saturn=150.),
     dict(is_day_chart=True, prenatal_new_moon_longitude=175.)),
    ("Fortune", dict(Sun=180., Moon=160., Mercury=150., Venus=150., Mars=150., Jupiter=150., Saturn=150.),
     dict(is_day_chart=False, prenatal_full_moon_longitude=340., latest_prenatal_syzygy="full_moon")),
])
def test_existing_predominator_is_composed_without_reselection_or_identity_loss(selected, overrides, context):
    chart, houses, positions = _figure(**overrides)
    det = find_predominator_ptolemy(positions=positions, asc_longitude=houses.asc, **context)
    target = Predominator(det)
    name, lon, lat = resolve_primary_direction_derived_point(target, chart, houses)
    assert name == target.name == selected
    assert lon == det.predominator_longitude
    assert lat == (5. if selected == "Moon" else 0.)
    assert target.determination is det
    arcs = find_primary_arcs(chart, houses, 35., max_arc=360., policy=_policy(target),
                             significators=[target.name], promissors=["Venus"])
    assert arcs
    assert {a.significator for a in arcs} == {selected}
    if selected in {"Sun", "Moon", "ASC"}:
        ordinary = find_primary_arcs(chart, houses, 35., max_arc=360., policy=_policy(),
                                     significators=[selected], promissors=["Venus"])
        assert arcs == ordinary


def test_selected_ruler_is_the_existing_planet_too():
    chart, houses, positions = _figure()
    houses.asc = 200.
    det = find_predominator_ptolemy(positions=positions, asc_longitude=200., is_day_chart=True,
                                    prenatal_new_moon_longitude=355.)
    assert det.predominator == "Venus"
    assert resolve_primary_direction_derived_point(Predominator(det), chart, houses) == ("Venus", 40., 0.)


def test_unresolved_office_keeps_the_original_reason_and_never_falls_back():
    _, houses, positions = _figure(Sun=180., Moon=160.)
    det = find_predominator_ptolemy(positions=positions, asc_longitude=houses.asc, is_day_chart=True)
    assert det.reason == "prenatal_new_moon_longitude_required"
    with pytest.raises(ValueError, match=det.reason):
        Predominator(det)


def test_predominator_fortune_retains_unreversed_bound_chronology_at_night():
    chart, houses, positions = _figure(Sun=180., Moon=160., Mercury=150., Venus=150.,
                                       Mars=150., Jupiter=150., Saturn=150.)
    det = find_predominator_ptolemy(positions=positions, asc_longitude=houses.asc,
                                    is_day_chart=False, prenatal_full_moon_longitude=340.,
                                    latest_prenatal_syzygy="full_moon")
    options = dict(significators=["Fortune"], promissors=["Mars"], max_age_years=100.)
    actual = compute_primary_directions_timeline(chart, houses, 35., policy=_policy(Predominator(det)), **options)
    expected = compute_primary_directions_timeline(chart, houses, 35., policy=_policy(Fortune()), **options)
    assert actual == expected
    assert actual.distributor_periods


def test_existing_planet_and_root_export_contracts_do_not_gain_a_synthetic_body():
    import moira
    assert "Fortune" not in Body.ALL_PLANETS
    assert not hasattr(moira, "PrimaryDirectionFortuneTarget")


@pytest.mark.parametrize("mutation", ["unselected_planet", "ascendant", "fortune", "selected", "missing_planet"])
def test_predominator_rejects_stale_or_inconsistent_coordinate_records(mutation):
    chart, houses, positions = _figure()
    det = find_predominator_ptolemy(positions=positions, asc_longitude=houses.asc, is_day_chart=True)
    if mutation == "unselected_planet":
        chart.planets["Saturn"].longitude += .01
    elif mutation == "ascendant":
        houses.asc += .01
    elif mutation == "fortune":
        det = replace(det, lot_of_fortune_longitude=det.lot_of_fortune_longitude + .01)
    elif mutation == "selected":
        det = replace(det, predominator_longitude=det.predominator_longitude + .01)
    else:
        del chart.planets["Saturn"]
    with pytest.raises(ValueError, match="match chart|requires natal"):
        resolve_primary_direction_derived_point(Predominator(det), chart, houses)


@pytest.mark.parametrize("changes", [dict(is_day_chart=1), dict(predominator_longitude=float("nan")),
    dict(places=()), dict(predominator="Neptune"), dict(status="selected")])
def test_weak_owner_vessels_are_validated_at_the_adapter_boundary(changes):
    _, houses, positions = _figure()
    det = find_predominator_ptolemy(positions=positions, asc_longitude=houses.asc, is_day_chart=True)
    with pytest.raises(ValueError):
        Predominator(replace(det, **changes))


def test_fortune_has_its_own_class_and_does_not_become_a_planet_or_an_aspect_source():
    truth = primary_direction_target_truth("Fortune")
    assert truth.target_class is PrimaryDirectionTargetClass.DERIVED_POINT
    assert not classify_primary_direction_target(truth).admitted_as_significator
    policy = _policy(Fortune())
    classified = classify_primary_direction_target(truth, policy=policy.target_policy)
    assert classified.admitted_as_significator and not classified.admitted_as_promissor
    for name in ["Fortune Trine", "Fortune Mundane Square", "Fortune/Sun Midpoint", "Spirit", "Predominator"]:
        with pytest.raises(ValueError):
            primary_direction_target_truth(name)


def test_scope_and_duplicate_identity_are_explicit():
    assert _policy(Fortune(), preset=PrimaryDirectionsPreset.REGIOMONTANUS_MUNDANE).derived_point_targets == (Fortune(),)
    with pytest.raises(ValueError, match="unique"):
        _policy(Fortune(), Fortune(Formula.SECT_REVERSED, False))
    with pytest.raises(ValueError, match="explicit"):
        replace(_policy(), derived_point_targets=(Fortune(),))
    with pytest.raises(ValueError, match="significators only"):
        PrimaryDirectionsPolicy(
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.DERIVED_POINT})))


@pytest.mark.parametrize("preset", [PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
                                    PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT])
def test_fortune_is_a_typed_opt_in_significator_in_both_spaces(preset):
    chart, houses, _ = _figure()
    policy = _policy(Fortune(), preset=preset)
    arcs = find_primary_arcs(chart, houses, 35., max_arc=360., policy=policy,
                             significators=["Fortune"], promissors=["Mars"])
    assert arcs and {a.significator for a in arcs} == {"Fortune"}
    assert {a.motion for a in arcs} == set(PrimaryDirectionMotion)
    with pytest.raises(ValueError, match="unavailable|not admitted"):
        find_primary_arcs(chart, houses, 35., policy=_policy(preset=preset), significators=["Fortune"])
    with pytest.raises(ValueError, match="not admitted"):
        find_primary_arcs(chart, houses, 35., policy=policy, significators=["Sun"], promissors=["Fortune"])


def test_default_search_and_explicit_ordinary_pairs_are_unchanged():
    chart, houses, _ = _figure()
    ordinary = find_primary_arcs(chart, houses, 35., policy=_policy())
    configured = find_primary_arcs(chart, houses, 35., policy=_policy(Fortune()))
    assert [a for a in configured if a.significator != "Fortune"] == ordinary
    assert any(a.significator == "Fortune" for a in configured)
    assert find_primary_arcs(chart, houses, 35., policy=_policy(Fortune()),
                             significators=["Sun"], promissors=["Moon"]) == find_primary_arcs(
                                 chart, houses, 35., policy=_policy(), significators=["Sun"], promissors=["Moon"])


@pytest.mark.parametrize("obliquity", [0., 23.44])
def test_fortune_arcs_recover_independent_equatorial_limit(obliquity):
    # At the equator every semi-arc is 90 degrees. Both points here are in
    # the same upper western quadrant, so III.10 reduces to their RA gap.
    chart, houses, _ = _figure(Mars=200.)
    chart.obliquity = obliquity
    houses.armc = 240.
    def ra(longitude):
        lon, obl = math.radians(longitude), math.radians(obliquity)
        return math.degrees(math.atan2(math.sin(lon) * math.cos(obl), math.cos(lon))) % 360
    expected = (ra(200.) - ra(190.)) % 360
    arcs = find_primary_arcs(chart, houses, 0., max_arc=360., policy=_policy(Fortune()),
                             significators=["Fortune"], promissors=["Mars"])
    assert {a.motion: a.arc for a in arcs} == pytest.approx({
        PrimaryDirectionMotion.DIRECT: expected,
        PrimaryDirectionMotion.CONVERSE: 360. - expected,
    }, abs=1e-11)


@pytest.mark.parametrize("preset", [p for p in PrimaryDirectionsPreset if p.value.startswith("ptolemy_")])
def test_every_ptolemy_preset_retains_the_typed_configuration(preset):
    target = Fortune()
    policy = _policy(target, preset=preset)
    assert policy.derived_point_targets == (target,)
    assert PrimaryDirectionTargetClass.DERIVED_POINT in policy.target_policy.admitted_significator_classes


def test_target_iterable_is_consumed_once_and_wrong_vessels_are_rejected():
    assert _policy(*(Fortune(),)).derived_point_targets == primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_MUNDANE, derived_point_targets=iter([Fortune()])).derived_point_targets
    for values in [None, "Fortune", [object()]]:
        with pytest.raises(ValueError):
            primary_directions_policy_preset(PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
                                             derived_point_targets=values)


def test_unrequested_predominator_does_not_expand_the_projection_dependency_closure():
    chart, houses, positions = _figure()
    det = find_predominator_ptolemy(positions=positions, asc_longitude=houses.asc, is_day_chart=True)
    target = Predominator(det)
    chart.planets["Saturn"].longitude += 1.
    expected = find_primary_arcs(chart, houses, 35., policy=_policy(),
                                 significators=["Venus"], promissors=["Moon"])
    assert find_primary_arcs(chart, houses, 35., policy=_policy(target),
                             significators=["Venus"], promissors=["Moon"]) == expected


def test_policy_excluded_predominator_does_not_activate_timeline_dependencies():
    chart, houses, positions = _figure()
    det = find_predominator_ptolemy(positions=positions, asc_longitude=houses.asc, is_day_chart=True)
    chart.planets["Saturn"].longitude += 1.
    target_policy = PrimaryDirectionTargetPolicy(
        admitted_significator_classes=frozenset({PrimaryDirectionTargetClass.ANGLE}))
    ordinary = replace(_policy(), target_policy=target_policy)
    configured = replace(_policy(Predominator(det)), target_policy=target_policy)
    options = dict(promissors=["Mars"], max_age_years=100.)
    assert compute_primary_directions_timeline(chart, houses, 35., policy=configured, **options) == (
        compute_primary_directions_timeline(chart, houses, 35., policy=ordinary, **options))


def test_fortune_uses_source_longitudes_without_projecting_circumpolar_sources():
    chart, houses, _ = _figure()
    chart.planets["Moon"].latitude = 85.
    assert find_primary_arcs(chart, houses, 70., policy=_policy(Fortune()),
                             significators=["Fortune"], promissors=["Venus"], max_arc=360.)


@pytest.mark.parametrize("family", ["antiscia", "midpoint"])
def test_configured_fortune_cannot_bypass_the_derived_source_scope(family):
    with pytest.raises(ValueError, match="source"):
        kwargs = (dict(antiscia_targets=(PrimaryDirectionAntisciaTarget("Fortune"),))
                  if family == "antiscia"
                  else dict(midpoint_targets=(PrimaryDirectionMidpointTarget("Fortune", "Sun"),)))
        _policy(Fortune(), **kwargs)


@pytest.mark.parametrize("field", ["asc", "Sun", "Moon"])
def test_fortune_rejects_nonfinite_source_coordinates(field):
    chart, houses, _ = _figure()
    if field == "asc":
        houses.asc = float("nan")
    else:
        chart.planets[field].longitude = float("nan")
    with pytest.raises(ValueError, match="finite"):
        resolve_primary_direction_derived_point(Fortune(), chart, houses)


@pytest.fixture(scope="module")
def real_figure(moira_engine):
    moment = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    return (moira_engine.chart(moment),
            moira_engine.houses(moment, 51.5, 0., system=HouseSystem.PLACIDUS),
            moira_engine._reader_obj)


@pytest.mark.parametrize("key", list(PrimaryDirectionKey))
@pytest.mark.parametrize("preset", [PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
                                    PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT])
def test_fortune_timeline_has_full_bound_context_for_all_six_exact_keys(real_figure, key, preset):
    chart, houses, reader = real_figure
    policy = _policy(Fortune(), preset=preset, key_policy=PrimaryDirectionKeyPolicy(key=key))
    options = dict(policy=policy, significators=["Fortune"], max_age_years=100., reader=reader)
    full = compute_primary_directions_timeline(chart, houses, 51.5, **options)
    selected = compute_primary_directions_timeline(chart, houses, 51.5, promissors=["Mars"], **options)
    empty = compute_primary_directions_timeline(chart, houses, 51.5, promissors=[], **options)
    assert full.events and selected.events
    assert selected.events == tuple(e for e in full.events if e.promissor == "Mars")
    def partition(tl):
        return tuple((p.motion, p.ruler, p.entry_arc_deg, p.exit_arc_deg) for p in tl.distributor_periods)
    assert partition(full) == partition(selected) == partition(empty)
    assert {p.motion for p in full.distributor_periods} == set(PrimaryDirectionMotion)
    assert not empty.events

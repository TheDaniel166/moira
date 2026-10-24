"""Catalogue-lot directional composition; arithmetic stays with the lots owner."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import math
from types import SimpleNamespace

import pytest

from moira.constants import HouseSystem
import moira.primary_directions.derived_points as derived_points
from moira.lots import (
    PARTS_DEFINITIONS, LotsComputationPolicy,
    LotsDerivedReferencePolicy, LotsExternalReferencePolicy,
    LotsReferenceFailureMode, evaluate_lots,
)
from moira.primary_directions import (
    PrimaryDirectionLotTarget as Lot,
    PrimaryDirectionFortuneTarget as Fortune,
    PrimaryDirectionFortuneDoctrine,
    PrimaryDirectionKey, PrimaryDirectionKeyPolicy,
    PrimaryDirectionMotion,
    PrimaryDirectionMidpointTarget,
    PrimaryDirectionTargetClass,
    PrimaryDirectionsPreset, compute_primary_directions_timeline,
    find_primary_arcs, primary_directions_policy_preset,
    resolve_primary_direction_derived_point,
)
from moira.primary_directions.derived_points import _resolve_primary_direction_derived_points
from moira.primary_directions.targets import primary_direction_target_truth


def _figure():
    positions = dict(Sun=10., Moon=100., Mercury=20., Venus=40., Mars=80.,
                     Jupiter=200., Saturn=300., Uranus=140., Neptune=250., Pluto=310.)
    chart = SimpleNamespace(
        planets={name: SimpleNamespace(longitude=lon, latitude=5., speed=1.)
                 for name, lon in positions.items()},
        nodes={"True Node": SimpleNamespace(longitude=60.)},
        obliquity=23.44, jd_ut=2451545.,
    )
    houses = SimpleNamespace(asc=100., mc=10., dsc=280., ic=190., armc=9.19,
                             cusps=tuple((100. + i * 30) % 360 for i in range(12)))
    return chart, houses


def _policy(*targets, preset=PrimaryDirectionsPreset.PTOLEMY_MUNDANE, **kwargs):
    return primary_directions_policy_preset(preset, derived_point_targets=targets, **kwargs)


@pytest.mark.parametrize("day", [True, False])
@pytest.mark.parametrize("preset", [PrimaryDirectionsPreset.PLACIDUS_MUNDANE,
    PrimaryDirectionsPreset.PTOLEMY_MUNDANE, PrimaryDirectionsPreset.PLACIDIAN_CLASSIC_MUNDANE,
    PrimaryDirectionsPreset.MERIDIAN_MUNDANE, PrimaryDirectionsPreset.MORINUS_MUNDANE,
    PrimaryDirectionsPreset.REGIOMONTANUS_MUNDANE, PrimaryDirectionsPreset.CAMPANUS_MUNDANE,
    PrimaryDirectionsPreset.TOPOCENTRIC_MUNDANE])
def test_entire_catalogue_matches_the_lots_owner_without_duplicate_formula_logic(day, preset, monkeypatch):
    chart, houses = _figure()
    context = dict(syzygy=145., prenatal_new_moon=120., prenatal_full_moon=300., lord_of_hour=40.)
    positions = {name: p.longitude for group in (chart.planets, chart.nodes) for name, p in group.items()}
    expected = evaluate_lots(positions, list(houses.cusps), day,
                             asc_longitude=houses.asc, mc_longitude=houses.mc, **context)
    assert not expected.not_evaluable
    assert len(expected.parts) == len(PARTS_DEFINITIONS)
    calls = []
    original = derived_points._evaluate_lot_definitions
    def counted(self, definitions, *args, **kwargs):
        calls.append(tuple(p.name for p in definitions))
        return original(self, definitions, *args, **kwargs)
    monkeypatch.setattr(derived_points, "_evaluate_lot_definitions", counted)
    # Every catalogue entry runs in one owner evaluation with full context.
    targets = tuple(Lot(part.name, day, **context) for part in expected.parts)
    actual = _resolve_primary_direction_derived_points(targets, chart, houses)
    assert len(calls) == 1
    assert set(calls[0]) == {part.name for part in expected.parts}
    assert len(actual) == len(expected.parts)
    for part in expected.parts:
        name = Lot(part.name, day).name
        assert actual[name] == (name, part.longitude, 0.)
        assert primary_direction_target_truth(name).target_class is PrimaryDirectionTargetClass.DERIVED_POINT
    assert len(expected.parts) + len(expected.not_evaluable) == len(PARTS_DEFINITIONS)
    calls.clear()
    arcs = find_primary_arcs(chart, houses, 35., policy=_policy(*targets, preset=preset), max_arc=360.,
                             significators=[t.name for t in targets], promissors=["Venus", "Mars"])
    assert {a.significator for a in arcs} == {t.name for t in targets}
    assert {a.motion for a in arcs} == set(PrimaryDirectionMotion)
    assert len(calls) == 1


@pytest.mark.parametrize("name, day, expected", [
    ("Spirit", True, 10.), ("Spirit", False, 190.),
    ("Basis (Valens)", True, 280.), ("Basis (Valens)", False, 280.),
    # Saturn projects Mars-Mercury here; substituting ASC gives 160, not 0.
    ("Theft (Valens)", True, 0.),
    ("Debt (Valens)", True, 20.), ("Debt (Valens)", False, 20.),
])
def test_independent_recipes_cover_reversal_shortest_arc_and_non_asc_projector(name, day, expected):
    chart, houses = _figure()
    point = resolve_primary_direction_derived_point(Lot(name, day), chart, houses)
    assert point == (f"Lot: {name}", expected, 0.)


def test_shortest_arc_is_not_directed_arc_and_uses_catalogue_dependencies():
    chart, houses = _figure()
    chart.planets["Moon"].longitude = 30.
    # Fortune=120, Spirit=80. The shortest gap is 40, not directed 320.
    assert resolve_primary_direction_derived_point(Lot("Basis (Valens)", True), chart, houses)[1] == 140.


@pytest.mark.parametrize("day", [True, False])
def test_catalogue_fortune_has_the_existing_canonical_identity_and_sect_formula(day):
    chart, houses = _figure()
    target = Lot("Fortune", day)
    assert target.name == "Fortune"
    assert resolve_primary_direction_derived_point(target, chart, houses) == (
        resolve_primary_direction_derived_point(Fortune(PrimaryDirectionFortuneDoctrine.SECT_REVERSED, day), chart, houses))
    with pytest.raises(ValueError, match="unique"):
        _policy(target, Fortune())


@pytest.mark.parametrize("mode", list(LotsReferenceFailureMode))
def test_missing_requested_reference_preserves_owner_reason_under_both_failure_modes(mode):
    chart, houses = _figure()
    target = Lot("Releaser", True, policy=LotsComputationPolicy(unresolved_reference_mode=mode))
    with pytest.raises(ValueError, match="unresolved_lot_ingredient_reference.*Syzygy"):
        resolve_primary_direction_derived_point(target, chart, houses)


def test_selected_evaluation_does_not_raise_for_unrequested_catalogue_entries(monkeypatch):
    chart, houses = _figure()
    original = derived_points._evaluate_lot_definitions
    calls = []
    def selected(self, definitions, *args, **kwargs):
        calls.append(tuple(p.name for p in definitions))
        return original(self, definitions, *args, **kwargs)
    monkeypatch.setattr(derived_points, "_evaluate_lot_definitions", selected)
    target = Lot("Spirit", True, policy=LotsComputationPolicy(unresolved_reference_mode=LotsReferenceFailureMode.RAISE))
    assert resolve_primary_direction_derived_point(target, chart, houses)[1] == 10.
    assert calls == [("Spirit",)]


@pytest.mark.parametrize("name, keyword, value", [
    ("Releaser", "syzygy", 145.), ("Life (Male)", "prenatal_new_moon", 120.),
    ("Life (Female)", "prenatal_full_moon", 300.), ("Outcomes", "lord_of_hour", 40.),
])
def test_optional_reference_context_is_explicit_and_policy_gated(name, keyword, value):
    chart, houses = _figure()
    assert math.isfinite(resolve_primary_direction_derived_point(Lot(name, True, **{keyword: value}), chart, houses)[1])
    external = replace(LotsExternalReferencePolicy(), **{"include_" + keyword: False})
    with pytest.raises(ValueError, match="not evaluable"):
        resolve_primary_direction_derived_point(Lot(name, True,
            policy=LotsComputationPolicy(external=external), **{keyword: value}), chart, houses)


def test_derived_dependency_policy_cannot_be_reconstructed_around():
    chart, houses = _figure()
    policy = LotsComputationPolicy(derived=LotsDerivedReferencePolicy(include_fortune=False))
    with pytest.raises(ValueError, match="Fortune"):
        resolve_primary_direction_derived_point(Lot("Basis (Valens)", True, policy=policy), chart, houses)


def test_synthetic_chart_entries_cannot_override_derived_reference_policy():
    chart, houses = _figure()
    chart.planets["Fortune"] = SimpleNamespace(longitude=1., latitude=0., speed=1.)
    policy = LotsComputationPolicy(derived=LotsDerivedReferencePolicy(include_fortune=False))
    with pytest.raises(ValueError, match="Fortune"):
        resolve_primary_direction_derived_point(Lot("Basis (Valens)", True, policy=policy), chart, houses)


@pytest.mark.parametrize("target", [Lot("Spirit", True), Fortune()])
def test_chart_entries_cannot_substitute_for_typed_point_coordinates(target):
    chart, houses = _figure()
    options = dict(significators=[target.name], promissors=["Venus"], max_arc=360.)
    expected = find_primary_arcs(chart, houses, 35., policy=_policy(target), **options)
    chart.planets[target.name] = SimpleNamespace(longitude=1., latitude=85., speed=1.)
    assert find_primary_arcs(chart, houses, 35., policy=_policy(target), **options) == expected
    # Even explicit macro admission does not construct a point from a label.
    without_typed_target = replace(_policy(target), derived_point_targets=())
    with pytest.raises(ValueError, match="unavailable"):
        find_primary_arcs(chart, houses, 35., policy=without_typed_target, **options)


def test_a_lot_does_not_require_irrelevant_luminaries_or_natal_latitudes():
    chart, houses = _figure()
    del chart.planets["Sun"]
    del chart.planets["Moon"]
    chart.planets["Saturn"].latitude = float("nan")
    assert resolve_primary_direction_derived_point(Lot("Debt (Valens)", True), chart, houses)[1:] == (20., 0.)


def test_resolution_uses_current_chart_and_houses_instead_of_stale_result_coordinates():
    chart, houses = _figure()
    target = Lot("Spirit", True)
    assert resolve_primary_direction_derived_point(target, chart, houses)[1] == 10.
    chart.planets["Sun"].longitude += 2.
    houses.asc += 3.
    assert resolve_primary_direction_derived_point(target, chart, houses)[1] == 15.


def test_batches_keep_distinct_lot_contexts_separate():
    chart, houses = _figure()
    targets = (Lot("Spirit", True), Lot("Necessity (Valens)", False),
               Lot("Releaser", True, syzygy=145.), Lot("Life (Male)", True, prenatal_new_moon=120.))
    expected = {t.name: resolve_primary_direction_derived_point(t, chart, houses) for t in targets}
    assert _resolve_primary_direction_derived_points(iter(targets), chart, houses) == expected


@pytest.mark.parametrize("obliquity", [0., 23.44])
def test_lot_arcs_match_independent_equatorial_limit(obliquity):
    chart, houses = _figure()
    chart.obliquity = obliquity
    chart.planets["Venus"].latitude = 0.
    houses.armc = 60.
    def ra(longitude):
        lon, obl = math.radians(longitude), math.radians(obliquity)
        return math.degrees(math.atan2(math.sin(lon) * math.cos(obl), math.cos(lon))) % 360.
    # Spirit=10, Venus=40, both upper western. At the equator their
    # equal 90-degree semi-arcs reduce the direction to the RA gap.
    target = Lot("Spirit", True)
    expected = ra(40.) - ra(10.)
    arcs = find_primary_arcs(chart, houses, 0., policy=_policy(target), max_arc=360.,
                             significators=[target.name], promissors=["Venus"])
    assert {a.motion: a.arc for a in arcs} == pytest.approx({
        PrimaryDirectionMotion.DIRECT: expected,
        PrimaryDirectionMotion.CONVERSE: 360. - expected,
    }, abs=1e-11)


def test_one_indexed_cusp_maps_match_ordered_cusps():
    chart, houses = _figure()
    target = Lot("Death", True)
    expected = resolve_primary_direction_derived_point(target, chart, houses)
    houses.cusps = {number: cusp for number, cusp in enumerate(houses.cusps, 1)}
    assert resolve_primary_direction_derived_point(target, chart, houses) == expected


@pytest.mark.parametrize("args, kwargs", [
    (("Spirit", 1), {}), (("spirit", True), {}), (("Lot: Spirit", True), {}),
    (("Unknown", True), {}), (("Spirit", True), dict(policy={})),
    (("Spirit", True), dict(syzygy=True)), (("Spirit", True), dict(lord_of_hour=float("nan"))),
    (("Spirit", True), dict(policy=LotsComputationPolicy(derived=LotsDerivedReferencePolicy(include_spirit=1)))),
])
def test_targets_reject_unknown_recipes_weak_policies_and_nonfinite_or_untyped_context(args, kwargs):
    with pytest.raises(ValueError):
        Lot(*args, **kwargs)


def test_target_is_immutable_and_external_longitudes_are_normalized():
    target = Lot("Spirit", True, syzygy=505.)
    assert target.syzygy == 145.
    with pytest.raises(FrozenInstanceError):
        target.lot_name = "Death"


def test_namespaced_lots_have_derived_identity_and_require_typed_coordinates():
    chart, houses = _figure()
    target = Lot("Spirit", True)
    assert primary_direction_target_truth(target.name).target_class is PrimaryDirectionTargetClass.DERIVED_POINT
    for name in ["Lot: Unknown", "Lot: Fortune", "Lot: Spirit Trine", "Lot: Spirit/Sun Midpoint"]:
        with pytest.raises(ValueError):
            primary_direction_target_truth(name)
    with pytest.raises(ValueError, match="unavailable|not admitted"):
        find_primary_arcs(chart, houses, 35., policy=_policy(), significators=[target.name])
    with pytest.raises(ValueError, match="not admitted"):
        find_primary_arcs(chart, houses, 35., policy=_policy(target), significators=["Sun"], promissors=[target.name])
    with pytest.raises(ValueError, match="derived-promissor source"):
        _policy(target, midpoint_targets=(PrimaryDirectionMidpointTarget(target.name, "Sun"),))
    with pytest.raises(ValueError, match="explicit"):
        replace(_policy(), derived_point_targets=(target,))
    assert _policy(target, preset=PrimaryDirectionsPreset.MERIDIAN_MUNDANE).derived_point_targets == (target,)


def test_unrequested_lot_and_ordinary_pairs_preserve_default_behavior():
    chart, houses = _figure()
    options = dict(significators=["Sun"], promissors=["Venus"], max_arc=360.)
    expected = find_primary_arcs(chart, houses, 35., policy=_policy(), **options)
    assert find_primary_arcs(chart, houses, 35., policy=_policy(Lot("Releaser", True)), **options) == expected
    assert compute_primary_directions_timeline(chart, houses, 35., policy=_policy(Lot("Releaser", True)),
        max_age_years=100., significators=["Sun"], promissors=["Venus"]) == compute_primary_directions_timeline(
            chart, houses, 35., policy=_policy(), max_age_years=100., significators=["Sun"], promissors=["Venus"])


@pytest.mark.parametrize("preset", [p for p in PrimaryDirectionsPreset if p.value.startswith("ptolemy_")])
def test_every_admitted_preset_preserves_lot_configuration(preset):
    target = Lot("Spirit", True)
    assert _policy(target, preset=preset).derived_point_targets == (target,)


@pytest.mark.parametrize("field", ["asc", "mc", "cusps", "planet"])
def test_invalid_natal_context_cannot_fabricate_a_lot(field):
    chart, houses = _figure()
    if field == "cusps":
        houses.cusps = houses.cusps[:11]
    elif field == "planet":
        chart.planets["Saturn"].longitude = float("nan")
    else:
        setattr(houses, field, float("nan"))
    with pytest.raises(ValueError):
        resolve_primary_direction_derived_point(Lot("Spirit", True), chart, houses)


@pytest.fixture(scope="module")
def real_figure(moira_engine):
    moment = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    return (moira_engine.chart(moment),
            moira_engine.houses(moment, 51.5, 0., system=HouseSystem.PLACIDUS),
            moira_engine._reader_obj)


@pytest.mark.parametrize("key", list(PrimaryDirectionKey))
@pytest.mark.parametrize("preset", [PrimaryDirectionsPreset.PTOLEMY_MUNDANE,
                                    PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ASPECT])
def test_lot_timelines_retain_exact_keys_and_complete_bound_context(real_figure, key, preset):
    chart, houses, reader = real_figure
    targets = (Lot("Spirit", True), Lot("Basis (Valens)", True))
    policy = _policy(*targets, preset=preset, key_policy=PrimaryDirectionKeyPolicy(key=key))
    options = dict(policy=policy, significators=[t.name for t in targets], reader=reader, max_age_years=100.)
    full = compute_primary_directions_timeline(chart, houses, 51.5, **options)
    selected = compute_primary_directions_timeline(chart, houses, 51.5, promissors=["Mars"], **options)
    def partition(tl):
        return tuple((p.significator, p.motion, p.entry_arc_deg, p.exit_arc_deg, p.ruler)
                     for p in tl.distributor_periods)
    assert partition(full) == partition(selected)
    assert {p.significator for p in full.distributor_periods} == {t.name for t in targets}
    assert selected.events == tuple(e for e in full.events if e.promissor == "Mars")
    assert selected.events

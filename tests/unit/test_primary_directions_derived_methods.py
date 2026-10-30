"""Typed target admission across all existing directional laws and presets."""

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from moira.constants import HouseSystem
from moira.hellenistic_offices import find_predominator_ptolemy
import moira.primary_directions.geometry as geometry
from moira.primary_directions import (
    PrimaryDirectionFortuneTarget as Fortune,
    PrimaryDirectionFortuneDoctrine,
    PrimaryDirectionLotTarget as Lot,
    PrimaryDirectionPredominatorTarget as Predominator,
    PrimaryDirectionMethod, PrimaryDirectionMotion, PrimaryDirectionSpace,
    PrimaryDirectionConverseDoctrine, PrimaryDirectionKey, PrimaryDirectionKeyPolicy,
    PrimaryDirectionTargetClass, PrimaryDirectionTargetPolicy,
    PrimaryDirectionRelationPolicy, PrimaryDirectionRelationalKind,
    PrimaryDirectionsPolicy, PrimaryDirectionsPreset as Preset,
    PrimaryDirectionAntisciaTarget, PtolemaicParallelTarget,
    PrimaryDirectionMundaneAspectTarget, PrimaryDirectionMundaneParallelTarget,
    PlacidianRaptParallelTarget, PrimaryDirectionFixedStarTarget,
    compute_primary_directions_timeline, find_primary_arcs,
    primary_directions_policy_preset,
)

@pytest.fixture
def apparent_star_reader(planetary_reader):
    """Fixed-star targets are apparent places: Earth's state comes from the kernel."""
    from moira.spk_reader import use_reader_override

    with use_reader_override(planetary_reader):
        yield planetary_reader



BASE_PRESETS = (
    Preset.PLACIDUS_MUNDANE, Preset.PTOLEMY_MUNDANE,
    Preset.PLACIDIAN_CLASSIC_MUNDANE, Preset.MERIDIAN_MUNDANE,
    Preset.MORINUS_MUNDANE, Preset.REGIOMONTANUS_MUNDANE,
    Preset.CAMPANUS_MUNDANE, Preset.TOPOCENTRIC_MUNDANE,
)
KINDS = ("fortune", "fortune_night", "lot", "basis", "pred_sun", "pred_moon", "pred_asc", "pred_fortune")
RAPT_PRESETS = {Preset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT,
                Preset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_CONVERSE}


def _figure(kind="fortune"):
    positions = dict(Sun=10., Moon=100., Mercury=20., Venus=40., Mars=80., Jupiter=200., Saturn=300.)
    if kind == "pred_moon":
        positions.update(Sun=250., Moon=10.)
    elif kind in {"pred_asc", "pred_fortune"}:
        positions.update(Sun=180., Moon=160., Mercury=150., Venus=150., Mars=150., Jupiter=150., Saturn=150.)
    chart = SimpleNamespace(planets={n: SimpleNamespace(longitude=x, latitude=5. if n == "Moon" else 0., speed=1.)
                                     for n, x in positions.items()}, nodes={}, obliquity=23.44, jd_ut=2451545.)
    houses = SimpleNamespace(asc=100., mc=10., dsc=280., ic=190., armc=9.19,
                             cusps=tuple((100. + 30 * i) % 360. for i in range(12)))
    if kind.startswith("pred_"):
        context = dict(is_day_chart=kind not in {"pred_moon", "pred_fortune"})
        if kind == "pred_asc":
            context["prenatal_new_moon_longitude"] = 175.
        elif kind == "pred_fortune":
            context.update(prenatal_full_moon_longitude=340., latest_prenatal_syzygy="full_moon")
        target = Predominator(find_predominator_ptolemy(positions=positions, asc_longitude=houses.asc, **context))
    else:
        target = {"fortune": Fortune(),
                  "fortune_night": Fortune(PrimaryDirectionFortuneDoctrine.SECT_REVERSED, False),
                  "lot": Lot("Spirit", True), "basis": Lot("Basis (Valens)", True)}[kind]
    return chart, houses, target


def _policy(preset, target=None, **kwargs):
    # Existing specialized presets keep their own promissor and motion laws.
    promissor = "Mars"
    if preset in RAPT_PRESETS:
        rapt = PlacidianRaptParallelTarget("Mars")
        kwargs.update(include_converse=False, placidian_rapt_parallel_targets=(rapt,))
        promissor = rapt.name
    elif preset is Preset.PTOLEMY_ZODIACAL_ANTISCIA:
        reflected = PrimaryDirectionAntisciaTarget("Mars")
        kwargs["antiscia_targets"] = (reflected,)
        promissor = reflected.name
    elif preset is Preset.PTOLEMY_ZODIACAL_PARALLEL:
        parallel = PtolemaicParallelTarget("Mars")
        kwargs["ptolemaic_parallel_targets"] = (parallel,)
        promissor = parallel.name
    elif preset in {Preset.PLACIDUS_MUNDANE_ASPECT, Preset.PTOLEMY_MUNDANE_ASPECT}:
        aspect = PrimaryDirectionMundaneAspectTarget("Mars", "Dexter Square", 1.)
        kwargs["mundane_aspect_targets"] = (aspect,)
        promissor = aspect.name
    elif preset is Preset.PLACIDIAN_MUNDANE_PARALLEL:
        parallel = PrimaryDirectionMundaneParallelTarget("Mars")
        kwargs["mundane_parallel_targets"] = (parallel,)
        promissor = parallel.name
    return primary_directions_policy_preset(
        preset, derived_point_targets=() if target is None else (target,), **kwargs), promissor


@pytest.mark.parametrize("preset", list(Preset))
@pytest.mark.parametrize("kind", KINDS)
def test_all_presets_construct_typed_targets_and_retain_their_source_identity(preset, kind):
    chart, houses, target = _figure(kind)
    policy, promissor = _policy(preset, target)
    assert policy.derived_point_targets == (target,)
    arcs = find_primary_arcs(chart, houses, 35., policy=policy, max_arc=360.,
                             significators=[target.name], promissors=[promissor])
    assert arcs
    assert {a.significator for a in arcs} == {target.name}
    assert {a.method for a in arcs} == {policy.method}
    if kind in {"pred_sun", "pred_moon", "pred_asc"}:
        ordinary, _ = _policy(preset)
        assert arcs == find_primary_arcs(chart, houses, 35., policy=ordinary, max_arc=360.,
                                         significators=[target.name], promissors=[promissor])


@pytest.mark.parametrize("preset", BASE_PRESETS)
@pytest.mark.parametrize("kind", ["fortune", "lot", "pred_moon"])
def test_admitted_native_paths_match_python_for_the_new_termini(preset, kind, monkeypatch):
    chart, houses, target = _figure(kind)
    policy, promissor = _policy(preset, target)
    args = dict(policy=policy, max_arc=360., significators=[target.name], promissors=[promissor])
    native = find_primary_arcs(chart, houses, 35., **args)
    monkeypatch.setattr(geometry, "_moira_native", None)
    python = find_primary_arcs(chart, houses, 35., **args)
    assert [(a.significator, a.promissor, a.motion) for a in native] == [
        (a.significator, a.promissor, a.motion) for a in python]
    assert [a.arc for a in native] == pytest.approx([a.arc for a in python], abs=1e-10)


@pytest.mark.parametrize("preset", BASE_PRESETS)
@pytest.mark.parametrize("kind", ["fortune", "lot"])
def test_all_methods_recover_the_independent_equatorial_ra_limit(preset, kind):
    chart, houses, target = _figure(kind)
    chart.obliquity = 0.
    longitude = 190. if kind == "fortune" else 10.
    houses.armc = longitude + 50.
    chart.planets["Jupiter"].longitude = longitude + 10.
    policy, _ = _policy(preset, target)
    # At zero obliquity and geographic latitude, RA=longitude and all
    # semi-arcs are 90. Both termini are upper western: RA gap=10 degrees.
    arcs = find_primary_arcs(chart, houses, 0., policy=policy, max_arc=360.,
                             significators=[target.name], promissors=["Jupiter"])
    # Meridian owns the existing sig.RA-prom.RA orientation. Under-pole
    # and semi-arc families use the opposite ordered gap at this limit.
    direct = 350. if preset is Preset.MERIDIAN_MUNDANE else 10.
    assert {a.motion: a.arc for a in arcs} == pytest.approx({
        PrimaryDirectionMotion.DIRECT: direct, PrimaryDirectionMotion.CONVERSE: 360. - direct,
    }, abs=1e-10)


@pytest.mark.parametrize("preset", BASE_PRESETS)
@pytest.mark.parametrize("kind", ["fortune", "lot", "pred_moon"])
def test_neo_converse_keeps_the_selected_law_and_complement_definition(preset, kind):
    chart, houses, target = _figure(kind)
    policy, promissor = _policy(preset, target, converse_doctrine=PrimaryDirectionConverseDoctrine.NEO_CONVERSE)
    arcs = find_primary_arcs(chart, houses, 35., policy=policy, max_arc=360.,
                             significators=[target.name], promissors=[promissor])
    by_motion = {a.motion: a.arc for a in arcs}
    assert by_motion[PrimaryDirectionMotion.CONVERSE] == pytest.approx(
        360. - by_motion[PrimaryDirectionMotion.DIRECT], abs=1e-10)


@pytest.mark.parametrize("preset", BASE_PRESETS)
def test_direct_only_policy_does_not_invent_a_converse_for_derived_points(preset):
    chart, houses, target = _figure()
    policy, promissor = _policy(preset, target, include_converse=False)
    arcs = find_primary_arcs(chart, houses, 35., policy=policy, max_arc=360.,
                             significators=[target.name], promissors=[promissor])
    assert arcs and {a.motion for a in arcs} == {PrimaryDirectionMotion.DIRECT}


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("preset", BASE_PRESETS)
def test_fixed_star_conjunction_accepts_only_explicit_typed_derived_significators(preset, apparent_star_reader):
    chart, houses, target = _figure("lot")
    policy, _ = _policy(preset, target, fixed_star_targets=(PrimaryDirectionFixedStarTarget("Regulus"),))
    arcs = find_primary_arcs(chart, houses, 35., policy=policy, max_arc=360.,
                             significators=[target.name], promissors=["Regulus"])
    assert arcs and {a.significator for a in arcs} == {target.name}
    with pytest.raises(ValueError):
        replace(policy, derived_point_targets=())
    # Node/house-cusp star admission remains outside this extension.
    with pytest.raises(ValueError):
        replace(policy, target_policy=PrimaryDirectionTargetPolicy(
            policy.target_policy.admitted_significator_classes | {PrimaryDirectionTargetClass.NODE},
            policy.target_policy.admitted_promissor_classes))


@pytest.mark.parametrize("preset", BASE_PRESETS)
def test_unrequested_missing_lot_does_not_change_ordinary_pairs(preset):
    chart, houses, _ = _figure()
    target = Lot("Releaser", True)  # no syzygy supplied
    configured, promissor = _policy(preset, target)
    ordinary, _ = _policy(preset)
    args = dict(significators=["Sun"], promissors=[promissor], max_arc=360.)
    assert find_primary_arcs(chart, houses, 35., policy=configured, **args) == (
        find_primary_arcs(chart, houses, 35., policy=ordinary, **args))
    with pytest.raises(ValueError, match="not evaluable.*Syzygy"):
        find_primary_arcs(chart, houses, 35., policy=configured,
                          significators=[target.name], promissors=[promissor])


def test_direct_policy_construction_accepts_all_typed_methods_without_a_preset():
    for method in PrimaryDirectionMethod:
        point_policy = PrimaryDirectionTargetPolicy(
            PrimaryDirectionTargetPolicy().admitted_significator_classes | {PrimaryDirectionTargetClass.DERIVED_POINT})
        policy = PrimaryDirectionsPolicy(method=method, derived_point_targets=(Fortune(),), target_policy=point_policy)
        assert policy.method is method


@pytest.mark.parametrize("preset", BASE_PRESETS)
def test_existing_polar_domain_boundaries_are_preserved(preset):
    chart, houses, target = _figure()
    chart.planets["Sun"].longitude = 0.
    chart.planets["Moon"].longitude = 350.
    # Fortune=90, declination=obliquity, circumpolar at 80 N. Sun at
    # 0 Aries has zero declination and retains defined rise/set semi-arcs.
    policy, _ = _policy(preset, target)
    options = dict(policy=policy, significators=[target.name], promissors=["Sun"], max_arc=360.)
    if preset in {Preset.PLACIDUS_MUNDANE, Preset.PTOLEMY_MUNDANE,
                  Preset.PLACIDIAN_CLASSIC_MUNDANE, Preset.TOPOCENTRIC_MUNDANE}:
        with pytest.raises(ValueError, match="rise/set semi-arcs"):
            find_primary_arcs(chart, houses, 80., **options)
    else:
        assert find_primary_arcs(chart, houses, 80., **options)


@pytest.mark.parametrize("method", [PrimaryDirectionMethod.PLACIDUS_MUNDANE,
                                    PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC])
def test_mundane_only_methods_do_not_gain_an_unadmitted_zodiacal_space(method):
    policy = PrimaryDirectionsPolicy(method=method, derived_point_targets=(Fortune(),),
        target_policy=PrimaryDirectionTargetPolicy(
            PrimaryDirectionTargetPolicy().admitted_significator_classes | {PrimaryDirectionTargetClass.DERIVED_POINT}))
    with pytest.raises(ValueError, match="in_zodiaco"):
        replace(policy, space=PrimaryDirectionSpace.IN_ZODIACO)


def test_signed_branch_preserves_strict_relation_target_and_timeline_gates():
    chart, houses, target = _figure("lot")
    policy, _ = _policy(Preset.TOPOCENTRIC_ZODIACAL_ASPECT_SIGNED_PRIMARY_MOTION, target)
    with pytest.raises(ValueError, match="target policy"):
        replace(policy, target_policy=PrimaryDirectionTargetPolicy())
    with pytest.raises(ValueError, match="relation and target policy"):
        replace(policy, relation_policy=PrimaryDirectionRelationPolicy(frozenset({PrimaryDirectionRelationalKind.CONJUNCTION})))
    with pytest.raises(ValueError, match="signed-primary-motion"):
        compute_primary_directions_timeline(chart, houses, 35., policy=policy,
            significators=[target.name], promissors=["Mars"], max_age_years=100.)


@pytest.mark.parametrize("offset, motion", [(10., PrimaryDirectionMotion.DIRECT),
    (-10., PrimaryDirectionMotion.CONVERSE), (0., None), (180., "antipodal")])
def test_signed_typed_points_preserve_single_motion_zero_and_antipodal_semantics(offset, motion):
    chart, houses, target = _figure("lot")
    chart.obliquity = 0.
    houses.armc = 60.
    chart.planets["Jupiter"].longitude = (10. + offset) % 360.
    policy, _ = _policy(Preset.TOPOCENTRIC_ZODIACAL_ASPECT_SIGNED_PRIMARY_MOTION, target)
    options = dict(policy=policy, significators=[target.name], promissors=["Jupiter"], max_arc=180.)
    if motion == "antipodal":
        with pytest.raises(ValueError, match="antipodal"):
            find_primary_arcs(chart, houses, 0., **options)
    else:
        arcs = find_primary_arcs(chart, houses, 0., **options)
        if motion is None:
            assert arcs == []
        else:
            assert len(arcs) == 1 and arcs[0].motion is motion
            assert arcs[0].arc == pytest.approx(10., abs=1e-10)


@pytest.mark.parametrize("preset", list(RAPT_PRESETS))
@pytest.mark.parametrize("kind", ["fortune", "lot", "pred_fortune"])
def test_rapt_timeline_retains_its_matching_bound_motion(preset, kind):
    chart, houses, target = _figure(kind)
    policy, promissor = _policy(preset, target)
    options = dict(policy=policy, significators=[target.name], max_age_years=400., max_arc=360.)
    full = compute_primary_directions_timeline(chart, houses, 35., **options)
    selected = compute_primary_directions_timeline(chart, houses, 35., promissors=[promissor], **options)
    expected = (PrimaryDirectionMotion.DIRECT if preset is Preset.PLACIDIAN_MUNDANE_RAPT_PARALLEL_DIRECT
                else PrimaryDirectionMotion.CONVERSE)
    assert selected.events and {e.motion for e in selected.events} == {expected}
    assert {p.motion for p in selected.distributor_periods} == {expected}
    assert [(p.entry_arc_deg, p.exit_arc_deg, p.ruler) for p in selected.distributor_periods] == [
        (p.entry_arc_deg, p.exit_arc_deg, p.ruler) for p in full.distributor_periods]


@pytest.fixture(scope="module")
def real_figure(moira_engine):
    moment = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    return (moira_engine.chart(moment), moira_engine.houses(moment, 51.5, 0., system=HouseSystem.PLACIDUS),
            moira_engine._reader_obj)


@pytest.mark.parametrize("preset", BASE_PRESETS)
@pytest.mark.parametrize("key", list(PrimaryDirectionKey))
def test_each_method_and_key_preserve_derived_target_bound_context(real_figure, preset, key):
    chart, houses, reader = real_figure
    target = Lot("Spirit", True)
    policy, _ = _policy(preset, target, key_policy=PrimaryDirectionKeyPolicy(key))
    args = dict(policy=policy, significators=[target.name], max_age_years=100., reader=reader)
    full = compute_primary_directions_timeline(chart, houses, 51.5, **args)
    # The chosen planet must actually perfect in this method's 100-year
    # interval. Meridian's orientation differs from the semi-arc families.
    native_events = [event for event in full.events if event.promissor in chart.planets]
    assert native_events
    promissor = native_events[0].promissor
    selected = compute_primary_directions_timeline(chart, houses, 51.5, promissors=[promissor], **args)
    def partition(tl):
        return tuple((p.significator, p.motion, p.entry_arc_deg, p.exit_arc_deg, p.ruler)
                     for p in tl.distributor_periods)
    assert partition(full) == partition(selected)
    assert {p.motion for p in selected.distributor_periods} == set(PrimaryDirectionMotion)
    assert selected.events == tuple(e for e in full.events if e.promissor == promissor)
    assert selected.events

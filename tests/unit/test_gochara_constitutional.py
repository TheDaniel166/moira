"""Gochara constitutional gates: source separation, typed policies and projections."""

from dataclasses import FrozenInstanceError, replace
from itertools import product
import pickle

import pytest
import moira.gochara as gochara_module
import moira.gochara_policy as policy_module

from moira.ashtakavarga import BhinnashtakavargaResult
from moira.gochara import (
    GOCHARA_PLANETS, GocharaBaselineClass, GocharaBavAvailability,
    GocharaChartSummary, GocharaLocalCondition as Condition, GocharaLocalProfile,
    GocharaNetworkNode, GocharaSubsystemProfile, GocharaVedhaNetwork,
    GocharaPlanetResult, GocharaPosition, GocharaResult,
    GocharaVedhaStatus as Status, gochara_from_positions, gochara_local_profiles,
    gochara_subsystem_profile,
)
from moira.gochara_policy import (
    DEFAULT_GOCHARA_POLICY, GocharaAdmissionStatus as Admission,
    GocharaBavMode, GocharaCompleteness, GocharaDoctrineOption,
    GocharaPolicy, GocharaSourceProfile, GocharaVedhaMode, gochara_doctrine_options,
)


def _positions():
    return {p: (60.0 if p == "Sun" else 240.0 if p in ("Moon", "Saturn") else 0.0)
            for p in GOCHARA_PLANETS}


def _bav(planet, count=4):
    return BhinnashtakavargaResult(planet, (count,) * 12, count * 12)


def test_default_policy_preserves_core_results_and_has_cited_choices():
    implicit = gochara_from_positions(0, _positions())
    explicit = gochara_from_positions(0, _positions(), policy=GocharaPolicy())
    assert implicit == explicit
    assert implicit.policy == DEFAULT_GOCHARA_POLICY
    assert implicit.for_planet("Sun").baseline_class is GocharaBaselineClass.FAVORABLE
    assert implicit.for_planet("Saturn").baseline_class is GocharaBaselineClass.OUTSIDE_FAVORABLE_SET
    options = implicit.policy.selected_options
    assert len({o.id for o in options}) == 8
    assert all(o.status is Admission.ADMITTED for o in options)
    assert {o.authority_kind for o in options} == {"textual", "engine_scope"}


def test_baseline_only_is_an_omitted_layer_with_the_same_indication():
    ordinary = gochara_from_positions(0, _positions()).for_planet("Sun")
    policy = GocharaPolicy(vedha_mode=GocharaVedhaMode.BASELINE_ONLY)
    baseline = gochara_from_positions(0, _positions(), policy=policy).for_planet("Sun")
    assert baseline.baseline_favorable
    assert baseline.indication == ordinary.indication
    assert baseline.vedha_house == ordinary.vedha_house == 9
    assert baseline.vedha_status is Status.OMITTED
    assert baseline.vedha_witnesses == baseline.missing_blockers == ()
    assert "ordinary_vedha" not in baseline.evaluated_layers
    assert "vedha.baseline_only" in {o.id for o in baseline.policy.selected_options}


def test_inspection_retains_active_exempt_and_potential_blockers_separately():
    result = gochara_from_positions(0, _positions()).for_planet("Sun")
    assert [w.blocker.planet for w in result.active_vedha_witnesses] == ["Moon"]
    assert [w.blocker.planet for w in result.exempt_vedha_witnesses] == ["Saturn"]
    assert result.eligible_blockers == ("Moon", "Mars", "Mercury", "Jupiter", "Venus")
    assert result.vedha_observation_complete is True
    omitted = replace(result, policy=GocharaPolicy(vedha_mode=GocharaVedhaMode.BASELINE_ONLY))
    assert omitted.active_vedha_witnesses == omitted.exempt_vedha_witnesses == ()
    assert omitted.eligible_blockers == result.eligible_blockers
    assert omitted.vedha_observation_complete is None


def test_complete_input_policy_rejects_partial_even_in_baseline_only_scope():
    for mode in GocharaVedhaMode:
        policy = GocharaPolicy(completeness=GocharaCompleteness.REQUIRE_COMPLETE, vedha_mode=mode)
        complete = gochara_from_positions(0, _positions(), policy=policy)
        assert not complete.missing_planets
        assert GocharaResult(0, tuple(GocharaPosition(p, lon) for p, lon in _positions().items()), policy=policy) == complete
        with pytest.raises(ValueError, match="complete snapshot"):
            gochara_from_positions(0, {"Sun": 60}, policy=policy)
        with pytest.raises(ValueError, match="complete snapshot"):
            GocharaPlanetResult(GocharaPosition("Sun", 60), 0, (GocharaPosition("Sun", 60),), policy=policy)


def test_bav_omission_requires_no_supplied_tables_and_retains_explicit_availability():
    policy = GocharaPolicy(bav_mode=GocharaBavMode.OMIT)
    result = gochara_from_positions(0, _positions(), policy=policy)
    assert all(p.ashtakavarga_availability is GocharaBavAvailability.OMITTED for p in result.planets)
    with pytest.raises(ValueError, match="omitted"):
        gochara_from_positions(0, _positions(), bhinna={"Sun": _bav("Sun")}, policy=policy)
    assert gochara_from_positions(0, {"Sun": 60}).for_planet("Sun").ashtakavarga_availability is GocharaBavAvailability.NOT_SUPPLIED


def test_required_bav_is_for_all_supplied_subjects_and_is_still_raw():
    policy = GocharaPolicy(bav_mode=GocharaBavMode.REQUIRE_ALL_RAW)
    with pytest.raises(ValueError, match="raw BAV required"):
        gochara_from_positions(0, _positions(), bhinna={"Sun": _bav("Sun")}, policy=policy)
    tables = {p: _bav(p, 8) for p in GOCHARA_PLANETS}
    result = gochara_from_positions(0, _positions(), bhinna=tables, policy=policy)
    assert result.for_planet("Sun").vedha_status is Status.BLOCKED
    assert all(p.ashtakavarga_rekhas == 8 and p.ashtakavarga_availability is GocharaBavAvailability.SUPPLIED for p in result.planets)
    partial = gochara_from_positions(0, {"Sun": 60}, bhinna={"Sun": _bav("Sun", 0)}, policy=policy)
    assert partial.for_planet("Sun").vedha_status is Status.INCOMPLETE
    assert partial.for_planet("Sun").ashtakavarga_rekhas == 0


@pytest.mark.parametrize("field,value", [
    ("source_profile", "prasna_marga"), ("source_profile", GocharaSourceProfile.PHALADEEPICA_26.value),
    ("vedha_mode", "ordinary"), ("vedha_mode", True),
    ("completeness", "retain_partial"), ("bav_mode", "raw_if_supplied"),
])
def test_policy_requires_admitted_enum_values(field, value):
    with pytest.raises(TypeError):
        GocharaPolicy(**{field: value})


def test_policy_reference_and_participants_cannot_be_replaced_or_mutated():
    with pytest.raises(TypeError):
        GocharaPolicy(reference="natal_sun")
    with pytest.raises(TypeError):
        GocharaPolicy(blockers=("Rahu",))
    with pytest.raises(FrozenInstanceError):
        DEFAULT_GOCHARA_POLICY.vedha_mode = GocharaVedhaMode.BASELINE_ONLY
    with pytest.raises(TypeError):
        gochara_from_positions(0, _positions(), policy={"reference": "natal_moon"})
    changed = replace(gochara_from_positions(0, _positions()), policy=GocharaPolicy(vedha_mode=GocharaVedhaMode.BASELINE_ONLY))
    assert all(p.policy == changed.policy for p in changed.planets)
    assert changed.for_planet("Sun").vedha_status is Status.OMITTED


def test_catalogue_keeps_attestation_dispute_and_admission_distinct():
    options = gochara_doctrine_options()
    assert len(options) == len({o.id for o in options})
    assert all(o.sources and o.statement and o.limitation for o in options)
    assert {o.status for o in options} == set(Admission)
    nodes = gochara_doctrine_options("nodes")
    assert len(nodes) == 3 and all(o.status is not Admission.ADMITTED for o in nodes)
    phala = next(o for o in nodes if o.id == "nodes.phaladeepika_sun_like")
    prasna = next(o for o in nodes if o.id == "nodes.prasna_marga_saturn_like")
    assert "10" in phala.statement and "10" not in prasna.statement
    assert "26.2" in phala.sources[0] and "22.51" in prasna.sources[0]
    assert all(o.status is Admission.DISPUTED for o in gochara_doctrine_options("source_discrepancies"))
    with pytest.raises(ValueError):
        gochara_doctrine_options("invented")
    with pytest.raises(TypeError):
        gochara_doctrine_options(1)


def test_catalogue_vessels_detach_source_lists_and_reject_invalid_status():
    sources = ["A named passage"]
    option = GocharaDoctrineOption("example", "reference", Admission.RESEARCH_REQUIRED, "research", sources, "A research question", "Not admitted")
    sources.clear()
    assert option.sources == ("A named passage",)
    with pytest.raises(FrozenInstanceError):
        option.status = Admission.ADMITTED
    with pytest.raises(TypeError):
        replace(option, status="admitted")
    with pytest.raises(TypeError):
        replace(option, sources="a passage")
    with pytest.raises(ValueError):
        replace(option, sources=())
    with pytest.raises(ValueError):
        replace(option, authority_kind="universal")


def test_relations_partition_detected_occupancy_and_keep_partial_observation_visible():
    from moira.gochara import GocharaVedhaRelationClass as Relation

    result = gochara_from_positions(0, {"Sun": 60, "Moon": 240, "Saturn": 240}).for_planet("Sun")
    assert result.vedha_status is Status.BLOCKED
    assert result.vedha_observation_complete is False
    assert [w.relation_class for w in result.vedha_witnesses] == [Relation.OBSTRUCTION, Relation.EXEMPT_OCCUPANCY]
    assert all(w.directed_pair == (3, 9) for w in result.vedha_witnesses)
    assert result.active_vedha_witnesses + result.exempt_vedha_witnesses == result.vedha_witnesses
    assert gochara_from_positions(0, {"Sun": 0}).for_planet("Sun").vedha_observation_complete is None


@pytest.mark.parametrize("positions,policy,expected", [
    ({"Sun": 0}, GocharaPolicy(), Condition.OUTSIDE_FAVORABLE_SET),
    ({"Sun": 60}, GocharaPolicy(), Condition.FAVORABLE_INCOMPLETE),
    ({"Sun": 60, "Moon": 240}, GocharaPolicy(), Condition.FAVORABLE_BLOCKED),
    ({p: 60 for p in GOCHARA_PLANETS}, GocharaPolicy(), Condition.FAVORABLE_UNOBSTRUCTED),
    ({"Sun": 60}, GocharaPolicy(vedha_mode=GocharaVedhaMode.BASELINE_ONLY), Condition.FAVORABLE_VEDHA_OMITTED),
])
def test_local_condition_integrates_existing_truth_without_a_strength_override(positions, policy, expected):
    snapshot = gochara_from_positions(0, positions, bhinna={"Sun": _bav("Sun", 8)}, policy=policy)
    local = next(p for p in gochara_local_profiles(snapshot) if p.planet == "Sun")
    assert local.condition is expected
    assert local.assessment is snapshot.for_planet("Sun")
    assert local.ashtakavarga_rekhas == 8


def test_aggregate_retains_known_blockers_incomplete_observations_and_missing_subjects():
    snapshot = gochara_from_positions(0, {"Sun": 60, "Moon": 240, "Venus": 0})
    summary = GocharaChartSummary(snapshot)
    assert summary.favorable_planets == ("Sun", "Venus")
    assert summary.outside_favorable_planets == ("Moon",)
    assert summary.blocked_planets == ("Sun",)
    assert summary.incomplete_verdict_planets == ("Venus",)
    assert summary.incomplete_observation_planets == ("Sun", "Venus")
    assert summary.missing_planets == ("Mars", "Mercury", "Jupiter", "Saturn")
    assert dict(summary.condition_counts) == {
        Condition.FAVORABLE_UNOBSTRUCTED: 0, Condition.FAVORABLE_BLOCKED: 1,
        Condition.FAVORABLE_INCOMPLETE: 1, Condition.FAVORABLE_VEDHA_OMITTED: 0,
        Condition.OUTSIDE_FAVORABLE_SET: 1,
    }


def test_network_direction_degrees_and_exempt_edges_match_the_known_relations():
    snapshot = gochara_from_positions(0, _positions())
    network = GocharaVedhaNetwork(snapshot)
    assert network.vedha_evaluated
    assert [(w.blocker.planet, w.subject.planet) for w in network.active_edges] == [("Moon", "Sun")]
    assert [(w.blocker.planet, w.subject.planet) for w in network.exempt_edges] == [("Saturn", "Sun")]
    nodes = {n.planet: n for n in network.nodes}
    assert (nodes["Moon"].observed_out_degree, nodes["Moon"].observed_in_degree) == (1, 0)
    assert (nodes["Sun"].observed_out_degree, nodes["Sun"].observed_in_degree) == (0, 1)
    assert nodes["Saturn"].observed_out_degree == 0
    assert nodes["Saturn"].exempt_blocking == network.exempt_edges
    assert nodes["Sun"].exempt_from == network.exempt_edges
    assert network.observed_unconnected_planets == ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")


def test_reciprocal_vedha_is_a_pair_of_directed_obstructions_not_automatic_relief():
    snapshot = gochara_from_positions(0, {"Mercury": 210, "Venus": 0})
    network = GocharaVedhaNetwork(snapshot)
    assert [(w.blocker.planet, w.subject.planet) for w in network.active_edges] == [
        ("Venus", "Mercury"), ("Mercury", "Venus")
    ]
    assert all(n.observed_in_degree == n.observed_out_degree == 1 for n in network.nodes)
    assert all(p.vedha_status is Status.BLOCKED for p in snapshot.planets)
    assert network.incomplete_observation_planets == ("Mercury", "Venus")
    assert network.missing_planets == ("Sun", "Moon", "Mars", "Jupiter", "Saturn")
    assert network.observed_unconnected_planets == ()


def test_omitted_network_never_claims_an_unconnected_graph_or_clearance():
    policy = GocharaPolicy(vedha_mode=GocharaVedhaMode.BASELINE_ONLY)
    profile = gochara_subsystem_profile(gochara_from_positions(0, _positions(), policy=policy))
    network = profile.vedha_network
    assert not network.vedha_evaluated
    assert network.active_edges == network.exempt_edges == network.observed_unconnected_planets == ()
    assert profile.chart_summary.omitted_vedha_planets == ("Sun", "Venus")
    assert profile.chart_summary.unobstructed_planets == ()


def test_projection_vessels_have_derived_fields_and_recompute_snapshot_replacement():
    snapshot = gochara_from_positions(0, _positions())
    profile = GocharaSubsystemProfile(snapshot)
    assert profile.local_profiles == profile.chart_summary.local_profiles
    assert all(p.assessment.policy == snapshot.policy for p in profile.local_profiles)
    assert sum(count for _, count in profile.chart_summary.condition_counts) == len(snapshot.positions)
    assert sum(n.observed_in_degree for n in profile.vedha_network.nodes) == len(profile.vedha_network.active_edges)
    assert sum(n.observed_out_degree for n in profile.vedha_network.nodes) == len(profile.vedha_network.active_edges)
    with pytest.raises(TypeError):
        GocharaLocalProfile(snapshot.for_planet("Sun"), condition=Condition.FAVORABLE_UNOBSTRUCTED)
    with pytest.raises(FrozenInstanceError):
        profile.chart_summary.blocked_planets = ()
    with pytest.raises(KeyError):
        GocharaNetworkNode(gochara_from_positions(0, {"Sun": 60}), "Moon")
    changed = replace(profile, snapshot=gochara_from_positions(0, {"Sun": 0}))
    assert changed.chart_summary.outside_favorable_planets == ("Sun",)
    assert changed.vedha_network.active_edges == ()
    assert len(changed.local_profiles) == 1


@pytest.mark.parametrize("constructor", [GocharaLocalProfile, GocharaChartSummary, GocharaNetworkNode, GocharaVedhaNetwork, GocharaSubsystemProfile])
def test_projection_vessels_reject_untyped_sources(constructor):
    with pytest.raises(TypeError):
        constructor(None, "Sun") if constructor is GocharaNetworkNode else constructor(None)


@pytest.mark.parametrize("vedha,completeness,bav", list(product(GocharaVedhaMode, GocharaCompleteness, GocharaBavMode)))
def test_all_admitted_policy_combinations_preserve_cross_layer_invariants(vedha, completeness, bav):
    policy = GocharaPolicy(vedha_mode=vedha, completeness=completeness, bav_mode=bav)
    tables = None if bav is GocharaBavMode.OMIT else {p: _bav(p) for p in GOCHARA_PLANETS}
    snapshot = gochara_from_positions(0, _positions(), bhinna=tables, policy=policy)
    profile = gochara_subsystem_profile(snapshot)
    summary = profile.chart_summary
    network = profile.vedha_network
    assert profile.local_profiles == summary.local_profiles == gochara_local_profiles(snapshot)
    assert tuple(p.planet for p in profile.local_profiles) == tuple(n.planet for n in network.nodes) == GOCHARA_PLANETS
    assert sum(count for _, count in summary.condition_counts) == 7
    assert set(summary.favorable_planets).isdisjoint(summary.outside_favorable_planets)
    assert set(summary.favorable_planets + summary.outside_favorable_planets) == set(GOCHARA_PLANETS)
    assert set(summary.blocked_planets + summary.unobstructed_planets + summary.incomplete_verdict_planets + summary.omitted_vedha_planets) == set(summary.favorable_planets)
    assert network.missing_planets == summary.missing_planets == snapshot.missing_planets == ()
    assert network.incomplete_observation_planets == summary.incomplete_observation_planets == ()
    assert sum(n.observed_in_degree for n in network.nodes) == sum(n.observed_out_degree for n in network.nodes) == len(network.active_edges)
    active_subjects = {w.subject.planet for w in network.active_edges}
    assert active_subjects == set(summary.blocked_planets)
    assert not set(network.active_edges).intersection(network.exempt_edges)
    assert all(p.assessment.policy == policy for p in profile.local_profiles)
    assert all(o.status is Admission.ADMITTED for o in policy.selected_options)
    assert "astronomy.caller_sidereal" in {o.id for o in policy.selected_options}
    if vedha is GocharaVedhaMode.BASELINE_ONLY:
        assert network.active_edges == network.exempt_edges == ()
    else:
        assert len(network.active_edges) == len(network.exempt_edges) == 1
    assert summary.raw_bav_planets == (() if bav is GocharaBavMode.OMIT else GOCHARA_PLANETS)


def test_canonical_policy_profile_and_network_are_deterministic_and_pickleable():
    positions = _positions()
    tables = {p: _bav(p) for p in GOCHARA_PLANETS}
    first = gochara_subsystem_profile(gochara_from_positions(0, positions, bhinna=tables))
    second = gochara_subsystem_profile(gochara_from_positions(0, dict(reversed(list(positions.items()))), bhinna=dict(reversed(list(tables.items())))))
    assert first == second
    assert pickle.loads(pickle.dumps(first)) == first
    assert first.snapshot.policy.selected_options == second.snapshot.policy.selected_options


def test_disputed_or_unadmitted_rules_cannot_be_selected_via_catalogue_or_policy():
    with pytest.raises(ValueError):
        GocharaSourceProfile("brihat_samhita_104")
    with pytest.raises(ValueError):
        GocharaVedhaMode("counter_vedha")
    with pytest.raises(ValueError):
        GocharaBavMode("four_or_more_override")
    for node in ("Rahu", "Ketu"):
        with pytest.raises(ValueError):
            gochara_from_positions(0, {node: 0})
    counter = gochara_doctrine_options("counter_vedha")
    assert counter[0].status is Admission.SOURCE_ATTESTED
    assert "exceptions" in counter[0].limitation
    four = next(o for o in gochara_doctrine_options("ashtakavarga") if o.id == "bav.four_rekhas")
    assert four.status is Admission.DISPUTED
    assert all(o.id != four.id for o in DEFAULT_GOCHARA_POLICY.selected_options)


def test_phase12_curated_surfaces_are_exact_bound_and_helper_free():
    policy_names = {
        "GOCHARA_PROFILE", "GOCHARA_PLANETS", "DEFAULT_GOCHARA_POLICY",
        "GocharaSourceProfile", "GocharaVedhaMode", "GocharaCompleteness",
        "GocharaBavMode", "GocharaAdmissionStatus", "GocharaDoctrineOption",
        "GocharaPolicy", "gochara_doctrine_options",
    }
    assert set(policy_module.__all__) == policy_names
    assert len(policy_module.__all__) == len(policy_names)
    assert len(gochara_module.__all__) == len(set(gochara_module.__all__)) == 28
    assert policy_names <= set(gochara_module.__all__)
    for module in (policy_module, gochara_module):
        assert all(not name.startswith("_") and hasattr(module, name) for name in module.__all__)
    assert "_OPTIONS" not in policy_module.__all__
    assert "_VEDHA" not in gochara_module.__all__

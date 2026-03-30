from __future__ import annotations

from moira.star_types import (
    FixedStarClassification,
    FixedStarTruth,
    HeliacalEvent,
    HeliacalEventClassification,
    HeliacalEventTruth,
    StarConditionProfile,
    StarConditionState,
    StarPosition,
    StarPositionClassification,
    StarPositionTruth,
    StarRelation,
    UnifiedStarRelation,
)
from moira.stars import (
    FixedStar,
    star_chart_condition_profile,
    star_condition_network_profile,
)


def _catalog_position() -> StarPosition:
    relation = StarRelation(
        kind="catalog_lookup",
        basis="named_star_lookup",
        star_name="Sirius",
        reference="Sirius",
    )
    return StarPosition(
        name="Sirius",
        nomenclature="alp CMa",
        longitude=104.08,
        latitude=-39.61,
        magnitude=-1.46,
        computation_truth=StarPositionTruth(
            queried_name="Sirius",
            lookup_mode="traditional_name",
            matched_name="Sirius",
            matched_nomenclature="alp CMa",
            source_frame="icrs",
            frame_path="icrs_to_true_ecliptic",
            catalog_epoch_jd=2451545.0,
            parallax_applied=False,
        ),
        classification=StarPositionClassification(
            lookup_kind="traditional_name",
            frame_kind="true_ecliptic_of_date",
            parallax_state="not_applied",
        ),
        relation=relation,
        condition_profile=StarConditionProfile(
            result_kind="catalog_position",
            condition_state=StarConditionState("catalog_position"),
            relation_kind=relation.kind,
            relation_basis=relation.basis,
            lookup_kind="traditional_name",
            source_kind="catalog",
        ),
    )


def _heliacal_event() -> HeliacalEvent:
    relation = StarRelation(
        kind="heliacal_event",
        basis="arcus_visionis_threshold",
        star_name="Sirius",
        event_kind="heliacal_rising",
    )
    return HeliacalEvent(
        event_kind="heliacal_rising",
        star_name="Sirius",
        jd_ut=2461255.614366472,
        is_found=True,
        computation_truth=HeliacalEventTruth(
            event_kind="heliacal_rising",
            star_name="Sirius",
            jd_start=2461245.5,
            search_days=30,
            arcus_visionis=10.0,
            elongation_threshold=12.0,
            conjunction_offset=None,
            qualifying_day_offset=10,
            qualifying_elongation=-14.2,
            qualifying_sun_altitude=-10.0,
            event_jd_ut=2461255.614366472,
        ),
        classification=HeliacalEventClassification(
            event_kind="heliacal_rising",
            search_kind="forward_visibility_scan",
            visibility_state="found",
        ),
        relation=relation,
        condition_profile=StarConditionProfile(
            result_kind="heliacal_event",
            condition_state=StarConditionState("found"),
            relation_kind=relation.kind,
            relation_basis=relation.basis,
            event_kind="heliacal_rising",
        ),
    )


def _fixed_star() -> FixedStar:
    relation = UnifiedStarRelation(
        kind="catalog_merge",
        basis="sovereign_registry",
        star_name="Sirius",
        source_kind="sovereign",
        gaia_source_index=None,
    )
    return FixedStar(
        name="Sirius",
        nomenclature="alp CMa",
        constellation="Canis Major",
        longitude=104.08,
        latitude=-39.61,
        magnitude=-1.46,
        source="sovereign",
        computation_truth=FixedStarTruth(
            lookup_kind="traditional_name",
            hipparcos_name="Sirius",
            constellation="Canis Major",
            source_mode="sovereign_registry",
            gaia_match_status="native_registry",
            gaia_source_index=None,
            is_topocentric=False,
            true_position=True,
            dedup_applied=False,
        ),
        classification=FixedStarClassification(
            lookup_kind="traditional_name",
            source_kind="sovereign",
            merge_state="native_registry",
            observer_mode="geocentric",
        ),
        relation=relation,
    )


def test_star_chart_condition_profile_aggregates_catalog_heliacal_and_unified() -> None:
    chart = star_chart_condition_profile(
        catalog_positions=[_catalog_position()],
        heliacal_events=[_heliacal_event()],
        fixed_stars=[_fixed_star()],
    )

    assert len(chart.profiles) == 3
    assert chart.catalog_position_count == 1
    assert chart.heliacal_event_count == 1
    assert chart.unified_merge_count == 1
    assert len(chart.strongest_profiles) == 1
    assert chart.strongest_profiles[0].result_kind == "heliacal_event"
    assert len(chart.weakest_profiles) == 1
    assert chart.weakest_profiles[0].condition_state.name == "catalog_position"


def test_star_condition_network_profile_builds_deterministic_edges() -> None:
    network = star_condition_network_profile(
        catalog_positions=[_catalog_position()],
        heliacal_events=[_heliacal_event()],
        fixed_stars=[_fixed_star()],
    )

    assert [node.node_id for node in network.nodes] == [
        "event:heliacal_rising:Sirius:2461255.614366",
        "source:catalog_lookup:named_star_lookup:Sirius",
        "source:catalog_merge:sovereign_registry:sovereign:Sirius",
        "star:Sirius",
    ]
    assert [edge.relation_kind for edge in network.edges] == [
        "heliacal_event",
        "catalog_lookup",
        "catalog_merge",
    ]
    assert [edge.condition_state for edge in network.edges] == [
        "found",
        "catalog_position",
        "unified_merge",
    ]
    assert network.isolated_nodes == ()
    assert len(network.most_connected_nodes) == 1
    assert network.most_connected_nodes[0].node_id == "star:Sirius"


def test_star_condition_network_profile_derives_missing_fixed_star_condition_profile() -> None:
    network = star_condition_network_profile(fixed_stars=[_fixed_star()])

    assert len(network.nodes) == 2
    assert len(network.edges) == 1
    assert network.edges[0].relation_kind == "catalog_merge"
    assert network.edges[0].condition_state == "unified_merge"

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira import Body, HouseSystem, Moira
from moira.houses import assign_house
from moira.aspects import aspects_between
from moira.midpoints import _midpoint
from moira.synastry import (
    _lon_midpoint,
    CompositeClassification,
    CompositeChart,
    CompositeComputationTruth,
    SynastryAspectPolicy,
    SynastryAspectClassification,
    SynastryAspectContact,
    SynastryConditionNetworkEdge,
    SynastryConditionNetworkNode,
    SynastryConditionNetworkProfile,
    SynastryChartConditionProfile,
    SynastryConditionProfile,
    SynastryConditionState,
    SynastryRelation,
    SynastryAspectTruth,
    SynastryCompositePolicy,
    SynastryComputationPolicy,
    SynastryDavisonPolicy,
    SynastryOverlayPolicy,
    composite_chart_reference_place,
    davison_chart_reference_place,
    house_overlay,
    mutual_overlay_relations,
    synastry_aspects,
    synastry_chart_condition_profile,
    synastry_condition_network_profile,
    synastry_condition_profiles,
    synastry_contact_relations,
    synastry_contacts,
)


def _aspect_signature(aspect) -> tuple[str, str, str, float, bool]:
    return (
        aspect.body1,
        aspect.body2,
        aspect.aspect if hasattr(aspect, "aspect") else aspect.aspect_name,
        round(aspect.orb, 8),
        bool(getattr(aspect, "applying", False)),
    )


@pytest.mark.requires_ephemeris
def test_synastry_aspects_match_cross_chart_engine_surface() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1991, 6, 15, 18, 30, tzinfo=timezone.utc)

    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)

    via_engine = sorted(
        _aspect_signature(a)
        for a in engine.synastry_aspects(chart_a, chart_b, tier=2, include_nodes=True)
    )
    lons_a = chart_a.longitudes(include_nodes=True)
    lons_b = chart_b.longitudes(include_nodes=True)
    speeds_a = chart_a.speeds()
    speeds_b = chart_b.speeds()

    manual_aspects = []
    for name_a, lon_a in lons_a.items():
        for name_b, lon_b in lons_b.items():
            manual_aspects.extend(
                aspects_between(
                    name_a,
                    lon_a,
                    name_b,
                    lon_b,
                    tier=2,
                    speed_a=speeds_a.get(name_a),
                    speed_b=speeds_b.get(name_b),
                )
            )
    manual = sorted(_aspect_signature(a) for a in manual_aspects)

    assert via_engine == manual
    assert via_engine
    assert all(sig[0] in chart_a.longitudes() for sig in via_engine)
    assert all(sig[1] in chart_b.longitudes() for sig in via_engine)


@pytest.mark.requires_ephemeris
def test_synastry_contacts_preserve_pair_truth_without_changing_aspect_semantics() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1991, 6, 15, 18, 30, tzinfo=timezone.utc)

    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    aspects = engine.synastry_aspects(chart_a, chart_b, tier=2, include_nodes=True)
    contacts = synastry_contacts(chart_a, chart_b, tier=2, include_nodes=True, source_label="A", target_label="B")

    assert [_aspect_signature(contact.aspect) for contact in contacts] == [
        _aspect_signature(aspect) for aspect in aspects
    ]
    assert contacts
    first = contacts[0]
    assert first.truth.source_label == "A"
    assert first.truth.target_label == "B"
    assert first.truth.tier == 2
    assert first.truth.include_nodes is True
    assert first.truth.orb_factor == pytest.approx(1.0, abs=1e-12)
    assert first.truth.custom_orbs is False
    assert first.truth.source_body == first.aspect.body1
    assert first.truth.target_body == first.aspect.body2
    assert first.classification is not None
    assert first.classification.contact_mode == "cross_chart_aspect"
    assert first.classification.pair_mode == "pair"
    assert first.classification.includes_nodes is True
    assert first.classification.uses_custom_orbs is False
    assert first.contact_mode == "cross_chart_aspect"
    assert first.pair_mode == "pair"
    assert first.includes_nodes is True
    assert first.uses_custom_orbs is False
    assert first.has_source_speed is True
    assert first.has_target_speed is True
    assert first.relation is not None
    assert first.relation.kind == "cross_chart_contact"
    assert first.relation.basis == "aspect"
    assert first.relation.source_ref == first.truth.source_body
    assert first.relation.target_ref == first.truth.target_body
    assert first.relation_kind == "cross_chart_contact"
    assert first.relation_basis == "aspect"
    assert first.has_relation is True
    assert first.relation.is_contact_relation is True
    assert first.relation.is_overlay_relation is False
    assert first.relation.is_relationship_chart_relation is False
    assert first.condition_profile is not None
    assert first.condition_profile.result_kind == "cross_chart_aspect"
    assert first.condition_profile.condition_state.name == "contact"
    assert first.condition_state == "contact"


@pytest.mark.requires_ephemeris
def test_composite_chart_uses_shorter_arc_midpoints_for_planets_nodes_and_houses() -> None:
    engine = Moira()
    dt_a = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    dt_b = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    houses_a = engine.houses(dt_a, 51.5, -0.1, HouseSystem.PLACIDUS)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)

    composite = engine.composite_chart(chart_a, chart_b, houses_a, houses_b)

    assert composite.jd_mean == pytest.approx((chart_a.jd_ut + chart_b.jd_ut) / 2.0, abs=1e-12)
    assert composite.computation_truth is not None
    assert composite.computation_truth.method == "midpoint"
    assert composite.computation_truth.includes_house_frame is True
    assert composite.computation_truth.jd_mean == pytest.approx(composite.jd_mean, abs=1e-12)
    assert composite.classification is not None
    assert composite.classification.chart_mode == "composite"
    assert composite.classification.method == "midpoint"
    assert composite.classification.includes_house_frame is True
    assert composite.chart_mode == "composite"
    assert composite.method == "midpoint"
    assert composite.includes_house_frame is True
    assert composite.source_house_system == houses_a.system
    assert composite.source_effective_house_system == houses_a.effective_system
    assert composite.relation is not None
    assert composite.relation.kind == "relationship_chart"
    assert composite.relation.basis == "midpoint_composite"
    assert composite.relation.method == "midpoint"
    assert composite.relation_kind == "relationship_chart"
    assert composite.relation_basis == "midpoint_composite"
    assert composite.relation_method == "midpoint"
    assert composite.has_relation is True
    assert composite.relation.is_relationship_chart_relation is True
    assert composite.relation.is_composite_relation is True
    assert composite.relation.is_davison_relation is False
    assert composite.condition_profile is not None
    assert composite.condition_profile.condition_state.name == "relationship_chart"
    assert composite.condition_profile.method == "midpoint"
    assert composite.condition_state == "relationship_chart"

    for name in chart_a.planets:
        assert composite.planets[name] == pytest.approx(
            _midpoint(chart_a.planets[name].longitude, chart_b.planets[name].longitude),
            abs=1e-12,
        )

    for name in chart_a.nodes:
        assert composite.nodes[name] == pytest.approx(
            _midpoint(chart_a.nodes[name].longitude, chart_b.nodes[name].longitude),
            abs=1e-12,
        )

    assert len(composite.cusps) == 12
    for idx in range(12):
        assert composite.cusps[idx] == pytest.approx(
            _midpoint(houses_a.cusps[idx], houses_b.cusps[idx]),
            abs=1e-12,
        )

    assert composite.asc == pytest.approx(_midpoint(houses_a.asc, houses_b.asc), abs=1e-12)
    assert composite.mc == pytest.approx(_midpoint(houses_a.mc, houses_b.mc), abs=1e-12)


def test_composite_wraparound_midpoint_and_lon_midpoint_handle_seams() -> None:
    assert _midpoint(350.0, 10.0) == pytest.approx(0.0, abs=1e-12)
    assert _midpoint(10.0, 350.0) == pytest.approx(0.0, abs=1e-12)
    assert _lon_midpoint(170.0, -170.0) == pytest.approx(180.0, abs=1e-12)
    assert _lon_midpoint(-170.0, 170.0) == pytest.approx(180.0, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_house_overlay_assigns_source_points_into_target_houses_using_house_engine() -> None:
    engine = Moira()
    dt_a = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    dt_b = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    chart_a = engine.chart(dt_a)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)
    overlay = engine.house_overlay(chart_a, houses_b, include_nodes=True, source_label="A", target_label="B")

    expected_longitudes = chart_a.longitudes(include_nodes=True)
    assert overlay.source_label == "A"
    assert overlay.target_label == "B"
    assert overlay.include_nodes is True
    assert overlay.computation_truth is not None
    assert overlay.computation_truth.source_label == "A"
    assert overlay.computation_truth.target_label == "B"
    assert overlay.computation_truth.include_nodes is True
    assert overlay.computation_truth.point_count == len(expected_longitudes)
    assert overlay.computation_truth.target_house_system == houses_b.system
    assert overlay.computation_truth.target_effective_house_system == houses_b.effective_system
    assert overlay.computation_truth.target_has_fallback is houses_b.fallback
    assert overlay.classification is not None
    assert overlay.classification.overlay_mode == "directional_house_overlay"
    assert overlay.classification.pair_mode == "pair"
    assert overlay.classification.includes_nodes is True
    assert overlay.classification.has_house_fallback is houses_b.fallback
    assert overlay.overlay_mode == "directional_house_overlay"
    assert overlay.pair_mode == "pair"
    assert overlay.includes_nodes is True
    assert overlay.target_house_system == houses_b.system
    assert overlay.target_effective_house_system == houses_b.effective_system
    assert overlay.has_house_fallback is houses_b.fallback
    assert overlay.relation is not None
    assert overlay.relation.kind == "house_overlay"
    assert overlay.relation.basis == "house_membership"
    assert overlay.relation_kind == "house_overlay"
    assert overlay.relation_basis == "house_membership"
    assert overlay.has_relation is True
    assert overlay.relation.is_overlay_relation is True
    assert overlay.relation.is_contact_relation is False
    assert overlay.condition_profile is not None
    assert overlay.condition_profile.condition_state.name == "overlay"
    assert overlay.condition_profile.has_house_fallback is houses_b.fallback
    assert overlay.condition_state == "overlay"
    assert set(overlay.placements) == set(expected_longitudes)

    for name, longitude in expected_longitudes.items():
        expected = assign_house(longitude, houses_b)
        actual = overlay.placements[name]
        assert actual.house == expected.house
        assert actual.longitude == pytest.approx(expected.longitude, abs=1e-12)
        assert actual.exact_on_cusp is expected.exact_on_cusp
        assert actual.cusp_longitude == pytest.approx(expected.cusp_longitude, abs=1e-12)

    for house in range(1, 13):
        expected_names = tuple(sorted(
            name for name, longitude in expected_longitudes.items()
            if assign_house(longitude, houses_b).house == house
        ))
        assert overlay.bodies_in_house(house) == expected_names


@pytest.mark.requires_ephemeris
def test_mutual_house_overlays_preserve_both_directions() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    dt_b = datetime(1992, 7, 15, 18, 0, tzinfo=timezone.utc)

    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    houses_a = engine.houses(dt_a, 51.5, -0.1, HouseSystem.PLACIDUS)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)

    mutual = engine.mutual_house_overlays(chart_a, houses_a, chart_b, houses_b, include_nodes=False)

    direct_a_in_b = engine.house_overlay(chart_a, houses_b, include_nodes=False, source_label="A", target_label="B")
    direct_b_in_a = engine.house_overlay(chart_b, houses_a, include_nodes=False, source_label="B", target_label="A")

    assert mutual.first_in_second.source_label == "A"
    assert mutual.first_in_second.target_label == "B"
    assert mutual.second_in_first.source_label == "B"
    assert mutual.second_in_first.target_label == "A"
    assert mutual.first_in_second.include_nodes is False
    assert mutual.second_in_first.include_nodes is False
    assert {
        name: placement.house for name, placement in mutual.first_in_second.placements.items()
    } == {
        name: placement.house for name, placement in direct_a_in_b.placements.items()
    }
    assert {
        name: placement.house for name, placement in mutual.second_in_first.placements.items()
    } == {
        name: placement.house for name, placement in direct_b_in_a.placements.items()
    }


@pytest.mark.requires_ephemeris
def test_davison_chart_matches_midpoint_time_and_location_chart_cast() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    dt_b = datetime(1992, 7, 15, 18, 0, tzinfo=timezone.utc)
    lat_a, lon_a = 51.5, -0.1
    lat_b, lon_b = 40.7128, -74.0060

    davison = engine.davison_chart(
        dt_a,
        lat_a,
        lon_a,
        dt_b,
        lat_b,
        lon_b,
        house_system=HouseSystem.PLACIDUS,
    )

    expected_dt = datetime.fromtimestamp(
        (dt_a.timestamp() + dt_b.timestamp()) / 2.0,
        tz=timezone.utc,
    )
    expected_lat = (lat_a + lat_b) / 2.0
    expected_lon = _lon_midpoint(lon_a, lon_b)
    expected_chart = engine.chart(expected_dt)
    expected_houses = engine.houses(expected_dt, expected_lat, expected_lon, HouseSystem.PLACIDUS)

    assert davison.info.computation_truth is not None
    assert davison.info.computation_truth.method == "midpoint_location"
    assert davison.info.computation_truth.latitude_mode == "arithmetic_midpoint"
    assert davison.info.computation_truth.longitude_mode == "shorter_arc_midpoint"
    assert davison.info.computation_truth.house_system == HouseSystem.PLACIDUS
    assert davison.info.classification is not None
    assert davison.info.classification.chart_mode == "davison"
    assert davison.info.classification.method == "midpoint_location"
    assert davison.info.classification.correction_mode == "uncorrected"
    assert davison.chart_mode == "davison"
    assert davison.method == "midpoint_location"
    assert davison.latitude_mode == "arithmetic_midpoint"
    assert davison.longitude_mode == "shorter_arc_midpoint"
    assert davison.is_corrected is False
    assert davison.info.relation is not None
    assert davison.info.relation.kind == "relationship_chart"
    assert davison.info.relation.basis == "midpoint_location_davison"
    assert davison.info.relation.method == "midpoint_location"
    assert davison.info.relation_kind == "relationship_chart"
    assert davison.info.relation_basis == "midpoint_location_davison"
    assert davison.info.relation_method == "midpoint_location"
    assert davison.info.has_relation is True
    assert davison.info.relation.is_relationship_chart_relation is True
    assert davison.info.relation.is_davison_relation is True
    assert davison.info.relation.is_composite_relation is False
    assert davison.info.condition_profile is not None
    assert davison.info.condition_profile.condition_state.name == "relationship_chart"
    assert davison.info.condition_profile.method == "midpoint_location"
    assert davison.info.condition_state == "relationship_chart"
    assert davison.info.datetime_utc == expected_dt
    assert davison.info.latitude_midpoint == pytest.approx(expected_lat, abs=1e-12)
    assert davison.info.longitude_midpoint == pytest.approx(expected_lon, abs=1e-12)
    assert davison.info.jd_midpoint == pytest.approx(expected_chart.jd_ut, abs=1e-12)

    for body in Body.ALL_PLANETS:
        assert davison.chart.planets[body].longitude == pytest.approx(
            expected_chart.planets[body].longitude,
            abs=1e-12,
        )

    for node_name in (Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH):
        assert davison.chart.nodes[node_name].longitude == pytest.approx(
            expected_chart.nodes[node_name].longitude,
            abs=1e-12,
        )

    assert davison.chart.obliquity == pytest.approx(expected_chart.obliquity, abs=1e-12)
    assert davison.houses is not None
    assert list(davison.houses.cusps) == pytest.approx(list(expected_houses.cusps), abs=1e-12)
    assert davison.houses.asc == pytest.approx(expected_houses.asc, abs=1e-12)
    assert davison.houses.mc == pytest.approx(expected_houses.mc, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_davison_variants_expose_distinct_mainstream_location_doctrines() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 6, 0, tzinfo=timezone.utc)
    dt_b = datetime(1992, 7, 15, 18, 0, tzinfo=timezone.utc)
    lat_a, lon_a = 51.5, 170.0
    lat_b, lon_b = 40.7128, -170.0

    uncorrected = engine.davison_chart_uncorrected(
        dt_a, lat_a, lon_a, dt_b, lat_b, lon_b, house_system=HouseSystem.PLACIDUS
    )
    reference_place = engine.davison_chart_reference_place(
        dt_a, dt_b, 34.0522, -118.2437, house_system=HouseSystem.PLACIDUS
    )
    spherical = engine.davison_chart_spherical_midpoint(
        dt_a, lat_a, lon_a, dt_b, lat_b, lon_b, house_system=HouseSystem.PLACIDUS
    )

    expected_dt = datetime.fromtimestamp(
        (dt_a.timestamp() + dt_b.timestamp()) / 2.0,
        tz=timezone.utc,
    )
    assert uncorrected.info.datetime_utc == expected_dt
    assert reference_place.info.datetime_utc == expected_dt
    assert spherical.info.datetime_utc == expected_dt
    assert uncorrected.info.computation_truth is not None
    assert uncorrected.info.computation_truth.method == "uncorrected"
    assert uncorrected.info.computation_truth.longitude_mode == "arithmetic_midpoint"
    assert uncorrected.info.classification is not None
    assert uncorrected.info.classification.method == "uncorrected"
    assert uncorrected.info.relation is not None
    assert uncorrected.info.relation.basis == "uncorrected_davison"
    assert reference_place.info.computation_truth is not None
    assert reference_place.info.computation_truth.method == "reference_place"
    assert reference_place.info.classification is not None
    assert reference_place.info.classification.method == "reference_place"
    assert reference_place.info.relation is not None
    assert reference_place.info.relation.basis == "reference_place_davison"
    assert spherical.info.computation_truth is not None
    assert spherical.info.computation_truth.method == "spherical_midpoint"
    assert spherical.info.classification is not None
    assert spherical.info.classification.method == "spherical_midpoint"
    assert spherical.info.relation is not None
    assert spherical.info.relation.basis == "spherical_midpoint_davison"
    assert uncorrected.info.longitude_midpoint == pytest.approx(0.0, abs=1e-12)
    assert reference_place.info.latitude_midpoint == pytest.approx(34.0522, abs=1e-12)
    assert reference_place.info.longitude_midpoint == pytest.approx(-118.2437, abs=1e-12)
    assert spherical.info.longitude_midpoint != pytest.approx(uncorrected.info.longitude_midpoint, abs=1e-6)


@pytest.mark.requires_ephemeris
def test_corrected_davison_preserves_midpoint_mc_doctrine() -> None:
    engine = Moira()
    dt_a = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    dt_b = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    lat_a, lon_a = 51.5, -0.1
    lat_b, lon_b = 40.7128, -74.0060

    corrected = engine.davison_chart_corrected(
        dt_a, lat_a, lon_a, dt_b, lat_b, lon_b, house_system=HouseSystem.PLACIDUS
    )
    natal_houses_a = engine.houses(dt_a, lat_a, lon_a, HouseSystem.PLACIDUS)
    natal_houses_b = engine.houses(dt_b, lat_b, lon_b, HouseSystem.PLACIDUS)
    target_mc = _midpoint(natal_houses_a.mc, natal_houses_b.mc)

    assert corrected.houses is not None
    assert corrected.info.computation_truth is not None
    assert corrected.info.computation_truth.method == "corrected"
    assert corrected.info.computation_truth.corrected_target_mc == pytest.approx(target_mc, abs=1e-12)
    assert corrected.info.classification is not None
    assert corrected.info.classification.correction_mode == "corrected"
    assert corrected.is_corrected is True
    assert corrected.info.relation is not None
    assert corrected.info.relation.basis == "corrected_davison"
    assert corrected.houses.mc == pytest.approx(target_mc, abs=1e-6)


@pytest.mark.requires_ephemeris
def test_composite_reference_place_method_preserves_planet_midpoints_and_reference_place_houses() -> None:
    engine = Moira()
    dt_a = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    dt_b = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    houses_a = engine.houses(dt_a, 51.5, -0.1, HouseSystem.PLACIDUS)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)

    composite = engine.composite_chart_reference_place(
        chart_a,
        chart_b,
        houses_a,
        houses_b,
        reference_latitude=34.0522,
        house_system=HouseSystem.PLACIDUS,
    )

    plain = engine.composite_chart(chart_a, chart_b)
    assert composite.planets == plain.planets
    assert composite.nodes == plain.nodes
    assert composite.computation_truth is not None
    assert composite.computation_truth.method == "reference_place"
    assert composite.computation_truth.reference_latitude == pytest.approx(34.0522, abs=1e-12)
    assert composite.computation_truth.house_system == HouseSystem.PLACIDUS
    assert composite.classification is not None
    assert composite.classification.method == "reference_place"
    assert composite.method == "reference_place"
    assert composite.reference_latitude == pytest.approx(34.0522, abs=1e-12)
    assert composite.relation is not None
    assert composite.relation.basis == "reference_place_composite"
    assert composite.mc == pytest.approx(_midpoint(houses_a.mc, houses_b.mc), abs=1e-9)
    assert composite.asc is not None
    assert len(composite.cusps) == 12


@pytest.mark.requires_ephemeris
def test_synastry_relation_helpers_are_deterministic_and_aligned() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1991, 6, 15, 18, 30, tzinfo=timezone.utc)
    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    houses_a = engine.houses(dt_a, 51.5, -0.1, HouseSystem.PLACIDUS)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)

    contacts = synastry_contacts(chart_a, chart_b, source_label="A", target_label="B")
    mutual = engine.mutual_house_overlays(chart_a, houses_a, chart_b, houses_b, include_nodes=False)

    contact_relations = synastry_contact_relations(contacts)
    contact_profiles = synastry_condition_profiles(contacts)
    overlay_relations = mutual_overlay_relations(mutual)

    assert len(contact_relations) == len(contacts)
    assert len(contact_profiles) == len(contacts)
    assert all(relation.kind == "cross_chart_contact" for relation in contact_relations)
    assert all(profile.condition_state.name == "contact" for profile in contact_profiles)
    assert len(overlay_relations) == 2
    assert {relation.basis for relation in overlay_relations} == {"house_membership"}
    assert all(relation.is_contact_relation for relation in contact_relations)
    assert all(relation.is_overlay_relation for relation in overlay_relations)


@pytest.mark.requires_ephemeris
def test_synastry_chart_condition_profile_is_deterministic_and_aligned() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1991, 6, 15, 18, 30, tzinfo=timezone.utc)
    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    houses_a = engine.houses(dt_a, 51.5, -0.1, HouseSystem.PLACIDUS)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)
    contacts = synastry_contacts(chart_a, chart_b, source_label="A", target_label="B")
    overlays = engine.mutual_house_overlays(chart_a, houses_a, chart_b, houses_b, include_nodes=False)
    composite = engine.composite_chart(chart_a, chart_b, houses_a, houses_b)
    davison = engine.davison_chart(dt_a, 51.5, -0.1, dt_b, 40.7128, -74.0060, house_system=HouseSystem.PLACIDUS)

    profile = synastry_chart_condition_profile(
        contacts=contacts,
        overlays=overlays,
        composite=composite,
        davison=davison,
    )

    assert profile.profile_count == len(contacts) + 4
    assert profile.contact_count == len(contacts)
    assert profile.overlay_count == 2
    assert profile.relationship_chart_count == 2
    assert profile.strongest_profiles
    assert all(item.condition_state.name == "relationship_chart" for item in profile.strongest_profiles)
    assert profile.weakest_profiles
    assert all(item.condition_state.name == "contact" for item in profile.weakest_profiles)


def test_synastry_chart_condition_profile_invariants_fail_loudly() -> None:
    profile = SynastryConditionProfile(
        result_kind="cross_chart_aspect",
        condition_state=SynastryConditionState("contact"),
        pair_mode="pair",
        relation_kind="cross_chart_contact",
        relation_basis="aspect",
        includes_nodes=True,
    )

    with pytest.raises(ValueError, match="must match profiles"):
        SynastryChartConditionProfile(
            profiles=(profile,),
            contact_count=0,
            overlay_count=0,
            relationship_chart_count=0,
            strongest_profiles=(profile,),
            weakest_profiles=(profile,),
        )

    stronger = SynastryConditionProfile(
        result_kind="davison",
        condition_state=SynastryConditionState("relationship_chart"),
        pair_mode="pair",
        relation_kind="relationship_chart",
        relation_basis="midpoint_location_davison",
        method="midpoint_location",
        includes_house_frame=True,
    )
    with pytest.raises(ValueError, match="strongest_profiles must match derived ranking"):
        SynastryChartConditionProfile(
            profiles=(profile, stronger),
            contact_count=1,
            overlay_count=0,
            relationship_chart_count=1,
            strongest_profiles=(profile, stronger),
            weakest_profiles=(profile,),
        )


@pytest.mark.requires_ephemeris
def test_synastry_condition_network_profile_is_deterministic_and_aligned() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1991, 6, 15, 18, 30, tzinfo=timezone.utc)
    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    houses_a = engine.houses(dt_a, 51.5, -0.1, HouseSystem.PLACIDUS)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)
    contacts = synastry_contacts(chart_a, chart_b, source_label="A", target_label="B")
    overlays = engine.mutual_house_overlays(chart_a, houses_a, chart_b, houses_b, include_nodes=False)
    composite = engine.composite_chart(chart_a, chart_b, houses_a, houses_b)
    davison = engine.davison_chart(dt_a, 51.5, -0.1, dt_b, 40.7128, -74.0060, house_system=HouseSystem.PLACIDUS)

    network = synastry_condition_network_profile(
        contacts=contacts,
        overlays=overlays,
        composite=composite,
        davison=davison,
    )

    assert network.node_count >= 4
    assert network.edge_count == len(contacts) + 6
    assert any(edge.relation_kind == "cross_chart_contact" for edge in network.edges)
    assert any(edge.relation_kind == "house_overlay" for edge in network.edges)
    assert any(edge.relation_basis == "midpoint_composite" for edge in network.edges)
    assert any(edge.relation_basis == "midpoint_location_davison" for edge in network.edges)
    assert network.most_connected_nodes
    assert all(node.total_degree >= 0 for node in network.nodes)


def test_synastry_condition_network_invariants_fail_loudly() -> None:
    node = SynastryConditionNetworkNode(
        node_id="pair:A",
        kind="pair",
        incoming_count=0,
        outgoing_count=0,
    )
    edge = SynastryConditionNetworkEdge(
        source_id="pair:A",
        target_id="pair:B",
        relation_kind="house_overlay",
        relation_basis="house_membership",
        condition_state="overlay",
    )

    with pytest.raises(ValueError, match="must reference known nodes"):
        SynastryConditionNetworkProfile(
            nodes=(node,),
            edges=(edge,),
            isolated_nodes=(),
            most_connected_nodes=(node,),
        )

    node_b = SynastryConditionNetworkNode(
        node_id="pair:B",
        kind="pair",
        incoming_count=1,
        outgoing_count=0,
    )
    with pytest.raises(ValueError, match="cross-chart contact edges must use contact condition_state"):
        SynastryConditionNetworkProfile(
            nodes=(node, node_b),
            edges=(
                SynastryConditionNetworkEdge(
                    source_id="pair:A",
                    target_id="pair:B",
                    relation_kind="cross_chart_contact",
                    relation_basis="aspect",
                    condition_state="overlay",
                ),
            ),
            isolated_nodes=(),
            most_connected_nodes=(node, node_b),
        )


def test_synastry_classification_and_inspectability_invariants_fail_loudly() -> None:
    truth = SynastryAspectTruth(
        source_label="A",
        target_label="B",
        source_body="Sun",
        target_body="Moon",
        tier=2,
        include_nodes=True,
        orb_factor=1.0,
        custom_orbs=False,
        source_speed=1.0,
        target_speed=13.0,
    )
    aspect = aspects_between("Sun", 0.0, "Moon", 90.0, tier=2, speed_a=1.0, speed_b=13.0)[0]

    with pytest.raises(ValueError, match="includes_nodes must match truth"):
        SynastryAspectContact(
            aspect=aspect,
            truth=truth,
            classification=SynastryAspectClassification(
                contact_mode="cross_chart_aspect",
                pair_mode="pair",
                includes_nodes=False,
                uses_custom_orbs=False,
            ),
        )

    with pytest.raises(ValueError, match="relation basis must be aspect"):
        SynastryAspectContact(
            aspect=aspect,
            truth=truth,
            relation=SynastryRelation(
                kind="cross_chart_contact",
                basis="house_membership",
                source_label="A",
                target_label="B",
                source_ref="Sun",
                target_ref="Moon",
            ),
        )

    with pytest.raises(ValueError, match="relationship chart relation method must match basis"):
        SynastryRelation(
            kind="relationship_chart",
            basis="reference_place_composite",
            source_label="A",
            target_label="B",
            source_ref="A",
            target_ref="B",
            method="midpoint",
        )

    with pytest.raises(ValueError, match="result_kind must match classification"):
        CompositeChart(
            planets={"Sun": 10.0},
            nodes={},
            cusps=[],
            asc=None,
            mc=None,
            jd_mean=100.0,
            computation_truth=CompositeComputationTruth(
                method="midpoint",
                jd_mean=100.0,
                includes_house_frame=False,
            ),
            classification=CompositeClassification(
                chart_mode="composite",
                method="midpoint",
                includes_house_frame=False,
            ),
            relation=SynastryRelation(
                kind="relationship_chart",
                basis="midpoint_composite",
                source_label="A",
                target_label="B",
                source_ref="A",
                target_ref="B",
                method="midpoint",
            ),
            condition_profile=SynastryConditionProfile(
                result_kind="davison",
                condition_state=SynastryConditionState("relationship_chart"),
                pair_mode="pair",
                relation_kind="relationship_chart",
                relation_basis="midpoint_composite",
                method="midpoint",
                includes_house_frame=False,
            ),
        )

    with pytest.raises(ValueError, match="includes_house_frame must match computation_truth"):
        CompositeChart(
            planets={"Sun": 10.0},
            nodes={},
            cusps=[],
            asc=None,
            mc=None,
            jd_mean=100.0,
            computation_truth=CompositeComputationTruth(
                method="midpoint",
                jd_mean=100.0,
                includes_house_frame=False,
            ),
            classification=CompositeClassification(
                chart_mode="composite",
                method="midpoint",
                includes_house_frame=True,
            ),
        )


@pytest.mark.requires_ephemeris
def test_default_synastry_policy_preserves_existing_behavior() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1991, 6, 15, 18, 30, tzinfo=timezone.utc)

    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    default_policy = SynastryComputationPolicy()

    direct = synastry_contacts(chart_a, chart_b, tier=2, include_nodes=True)
    via_policy = synastry_contacts(chart_a, chart_b, policy=default_policy)

    assert [_aspect_signature(item.aspect) for item in via_policy] == [
        _aspect_signature(item.aspect) for item in direct
    ]
    assert [item.truth.include_nodes for item in via_policy] == [item.truth.include_nodes for item in direct]


@pytest.mark.requires_ephemeris
def test_narrower_synastry_policy_explicitly_governs_contact_overlay_and_chart_defaults() -> None:
    engine = Moira()
    dt_a = datetime(1987, 9, 23, 4, 0, tzinfo=timezone.utc)
    dt_b = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    houses_a = engine.houses(dt_a, 51.5, -0.1, HouseSystem.PLACIDUS)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)
    policy = SynastryComputationPolicy(
        aspects=SynastryAspectPolicy(tier=1, include_nodes=False, orb_factor=0.5),
        overlays=SynastryOverlayPolicy(include_nodes=False),
        composite=SynastryCompositePolicy(reference_place_house_system=HouseSystem.WHOLE_SIGN),
        davison=SynastryDavisonPolicy(default_house_system=HouseSystem.WHOLE_SIGN),
    )

    contacts = synastry_contacts(chart_a, chart_b, policy=policy)
    overlay = house_overlay(chart_a, houses_b, source_label="A", target_label="B", policy=policy)
    composite = composite_chart_reference_place(
        chart_a,
        chart_b,
        houses_a,
        houses_b,
        reference_latitude=34.0522,
        policy=policy,
    )
    davison = davison_chart_reference_place(
        dt_a,
        dt_b,
        34.0522,
        -118.2437,
        policy=policy,
    )

    assert contacts
    assert all(contact.truth.include_nodes is False for contact in contacts)
    assert all(contact.truth.tier == 1 for contact in contacts)
    assert all(contact.truth.orb_factor == pytest.approx(0.5, abs=1e-12) for contact in contacts)
    assert overlay.include_nodes is False
    assert set(overlay.placements) == set(chart_a.longitudes(include_nodes=False))
    assert composite.computation_truth is not None
    assert composite.computation_truth.house_system == HouseSystem.WHOLE_SIGN
    assert davison.info.computation_truth is not None
    assert davison.info.computation_truth.house_system == HouseSystem.WHOLE_SIGN
    assert davison.houses is not None
    assert davison.houses.system == HouseSystem.WHOLE_SIGN


def test_invalid_synastry_policy_values_fail_clearly() -> None:
    with pytest.raises(ValueError, match="tier must be 1 or 2"):
        SynastryAspectPolicy(tier=3)

    with pytest.raises(ValueError, match="orb_factor must be positive and finite"):
        SynastryAspectPolicy(orb_factor=0.0)

    with pytest.raises(ValueError, match="reference_place_house_system must be non-empty"):
        SynastryCompositePolicy(reference_place_house_system="")


def test_synastry_malformed_inputs_fail_deterministically() -> None:
    with pytest.raises(ValueError, match="synastry labels must be non-empty"):
        synastry_contacts(None, None, source_label="", target_label="B")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="synastry tier must be 1 or 2"):
        synastry_aspects(None, None, tier=3)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="synastry overlay include_nodes must be boolean"):
        house_overlay(None, None, include_nodes="yes")  # type: ignore[arg-type]


@pytest.mark.requires_ephemeris
def test_synastry_additional_hardening_failures_are_deterministic() -> None:
    engine = Moira()
    dt_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_b = datetime(1991, 6, 15, 18, 30, tzinfo=timezone.utc)
    chart_a = engine.chart(dt_a)
    chart_b = engine.chart(dt_b)
    houses_a = engine.houses(dt_a, 51.5, -0.1, HouseSystem.PLACIDUS)
    houses_b = engine.houses(dt_b, 40.7128, -74.0060, HouseSystem.PLACIDUS)

    with pytest.raises(ValueError, match="composite chart requires both houses_a and houses_b or neither"):
        engine.composite_chart(chart_a, chart_b, houses_a, None)

    with pytest.raises(ValueError, match="reference_latitude must be finite"):
        composite_chart_reference_place(chart_a, chart_b, houses_a, houses_b, float("nan"))

    with pytest.raises(ValueError, match="lat_a must be finite"):
        engine.davison_chart(dt_a, float("nan"), -0.1, dt_b, 40.7128, -74.0060)

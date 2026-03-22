from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira import Body, HouseSystem, Moira
from moira.houses import assign_house
from moira.aspects import aspects_between
from moira.midpoints import _midpoint
from moira.synastry import _lon_midpoint


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
    assert composite.mc == pytest.approx(_midpoint(houses_a.mc, houses_b.mc), abs=1e-9)
    assert composite.asc is not None
    assert len(composite.cusps) == 12

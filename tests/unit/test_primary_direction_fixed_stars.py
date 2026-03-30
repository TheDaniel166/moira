from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from moira.primary_directions.fixed_stars import (
    PrimaryDirectionFixedStarTarget,
    resolve_primary_direction_fixed_star_point,
)
from moira.primary_directions import (
    PrimaryDirectionConverseDoctrine,
    PrimaryDirectionFixedStarTarget as PublicPrimaryDirectionFixedStarTarget,
    PrimaryDirectionLatitudeDoctrine,
    PrimaryDirectionLatitudePolicy,
    PrimaryDirectionLatitudeSource,
    PrimaryDirectionLatitudeSourcePolicy,
    PrimaryDirectionMethod,
    PrimaryDirectionPerfectionKind,
    PrimaryDirectionPerfectionPolicy,
    PrimaryDirectionSpace,
    PrimaryDirectionTargetClass,
    PrimaryDirectionTargetPolicy,
    PrimaryDirectionsPolicy,
    find_primary_arcs,
)
from moira.stars import star_at


def test_primary_direction_fixed_star_target_requires_sovereign_catalog_name() -> None:
    target = PrimaryDirectionFixedStarTarget("Sirius")

    assert target.name == "Sirius"

    with pytest.raises(ValueError):
        PrimaryDirectionFixedStarTarget("Not A Real Star")


def test_resolve_primary_direction_fixed_star_point_uses_sovereign_star_engine() -> None:
    jd_tt = 2451545.0

    name, longitude, latitude = resolve_primary_direction_fixed_star_point(
        PrimaryDirectionFixedStarTarget("Sirius"),
        jd_tt=jd_tt,
    )
    star = star_at("Sirius", jd_tt)

    assert name == "Sirius"
    assert longitude == pytest.approx(star.longitude)
    assert latitude == pytest.approx(star.latitude)


@dataclass
class _FixturePlanet:
    longitude: float
    latitude: float = 0.0
    speed: float = 1.0


@dataclass
class _FixtureNode:
    longitude: float


@dataclass
class _FixtureChart:
    planets: dict[str, _FixturePlanet]
    nodes: dict[str, _FixtureNode]
    obliquity: float
    jd_tt: float


@dataclass
class _FixtureHouses:
    armc: float
    asc: float
    mc: float
    dsc: float
    ic: float
    cusps: tuple[float, ...]


def _fixed_star_examples() -> list[dict[str, object]]:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "primary_directions_fixed_star_examples.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _fixture_chart(example: dict[str, object]) -> tuple[_FixtureChart, _FixtureHouses]:
    chart = _FixtureChart(
        planets={
            "Sun": _FixturePlanet(15.0, 0.0, 0.9856),
            "Moon": _FixturePlanet(82.0, 5.0, 13.0),
            "Venus": _FixturePlanet(134.0, 2.0, 1.2),
        },
        nodes={"North Node": _FixtureNode(203.0)},
        obliquity=float(example["obliquity"]),
        jd_tt=float(example["jd_tt"]),
    )
    houses = _FixtureHouses(
        armc=float(example["armc"]),
        asc=float(example["asc"]),
        mc=float(example["mc"]),
        dsc=float(example["dsc"]),
        ic=float(example["ic"]),
        cusps=(118.0, 145.0, 173.0, 221.0, 250.0, 280.0, 298.0, 325.0, 352.0, 41.0, 73.0, 101.0),
    )
    return chart, houses


@pytest.mark.parametrize(
    "example_id",
    [
        "fixed_star_meridian_sirius_to_asc",
        "fixed_star_ptolemy_algol_to_mc",
        "fixed_star_meridian_sirius_to_venus",
        "fixed_star_ptolemy_algol_to_sun",
    ],
)
def test_fixed_star_examples_match_fixture_points_and_arcs(example_id: str) -> None:
    example = next(item for item in _fixed_star_examples() if item["example_id"] == example_id)
    chart, houses = _fixture_chart(example)
    geo_lat = float(example["geo_lat"])
    star_name = str(example["star_name"])

    name, longitude, latitude = resolve_primary_direction_fixed_star_point(
        PrimaryDirectionFixedStarTarget(star_name),
        jd_tt=chart.jd_tt,
    )
    assert name == star_name
    assert longitude == pytest.approx(float(example["expected_longitude"]))
    assert latitude == pytest.approx(float(example["expected_latitude"]))

    if example["method"] == "meridian":
        policy = PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.MERIDIAN,
            include_converse=False,
            converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.PLANET,
                    }
                ),
                admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.PLANET}),
            ),
            fixed_star_targets=(PublicPrimaryDirectionFixedStarTarget(star_name),),
        )
    else:
        policy = PrimaryDirectionsPolicy(
            method=PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            space=PrimaryDirectionSpace.IN_ZODIACO,
            include_converse=False,
            converse_doctrine=PrimaryDirectionConverseDoctrine.DIRECT_ONLY,
            latitude_policy=PrimaryDirectionLatitudePolicy(
                PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
            ),
            latitude_source_policy=PrimaryDirectionLatitudeSourcePolicy(
                PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
            ),
            perfection_policy=PrimaryDirectionPerfectionPolicy(
                PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
            ),
            target_policy=PrimaryDirectionTargetPolicy(
                admitted_significator_classes=frozenset(
                    {
                        PrimaryDirectionTargetClass.ANGLE,
                        PrimaryDirectionTargetClass.PLANET,
                    }
                ),
                admitted_promissor_classes=frozenset({PrimaryDirectionTargetClass.PLANET}),
            ),
            fixed_star_targets=(PublicPrimaryDirectionFixedStarTarget(star_name),),
        )

    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=geo_lat,
        max_arc=360.0,
        significators=[str(example["significator"])],
        promissors=[star_name],
        policy=policy,
    )

    assert len(arcs) == 1
    assert arcs[0].arc == pytest.approx(float(example["expected_arc"]))

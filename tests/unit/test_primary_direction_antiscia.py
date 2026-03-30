from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from moira.antiscia import antiscion, contra_antiscion
from moira.primary_directions.antiscia import (
    PrimaryDirectionAntisciaKind,
    PrimaryDirectionAntisciaTarget,
    project_primary_direction_antiscia_longitude,
)
from moira.primary_directions import (
    PrimaryDirectionsPreset,
    primary_directions_policy_preset,
    find_primary_arcs,
)


def test_primary_direction_antiscia_target_exposes_stable_names() -> None:
    assert PrimaryDirectionAntisciaTarget("Sun").name == "Sun Antiscion"
    assert (
        PrimaryDirectionAntisciaTarget("Sun", PrimaryDirectionAntisciaKind.CONTRA_ANTISCION).name
        == "Sun Contra-Antiscion"
    )


def test_primary_direction_antiscia_projection_matches_sovereign_formula() -> None:
    assert project_primary_direction_antiscia_longitude(
        15.0,
        PrimaryDirectionAntisciaKind.ANTISCION,
    ) == pytest.approx(antiscion(15.0))
    assert project_primary_direction_antiscia_longitude(
        15.0,
        PrimaryDirectionAntisciaKind.CONTRA_ANTISCION,
    ) == pytest.approx(contra_antiscion(15.0))


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


def _antiscia_examples() -> list[dict[str, object]]:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "primary_directions_antiscia_examples.json"
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
        "ptolemy_zodiacal_venus_antiscion_to_asc",
        "ptolemy_zodiacal_venus_contra_antiscion_to_asc",
        "ptolemy_zodiacal_node_antiscion_to_asc",
        "ptolemy_zodiacal_asc_contra_antiscion_to_asc",
    ],
)
def test_antiscia_examples_match_fixture_projection_and_arc(example_id: str) -> None:
    example = next(item for item in _antiscia_examples() if item["example_id"] == example_id)
    chart, houses = _fixture_chart(example)
    source_name = str(example["source_name"])
    kind = PrimaryDirectionAntisciaKind(str(example["kind"]))
    target = PrimaryDirectionAntisciaTarget(source_name, kind)

    if source_name == "ASC":
        source_longitude = houses.asc
    elif source_name in chart.planets:
        source_longitude = chart.planets[source_name].longitude
    else:
        source_longitude = chart.nodes[source_name].longitude

    reflected = project_primary_direction_antiscia_longitude(source_longitude, kind)
    assert reflected == pytest.approx(float(example["expected_reflected_longitude"]))

    policy = primary_directions_policy_preset(
        PrimaryDirectionsPreset.PTOLEMY_ZODIACAL_ANTISCIA,
        include_converse=False,
        antiscia_targets=(target,),
    )
    arcs = find_primary_arcs(
        chart,
        houses,
        geo_lat=float(example["geo_lat"]),
        max_arc=360.0,
        significators=[str(example["significator"])],
        promissors=[target.name],
        policy=policy,
    )

    assert len(arcs) == 1
    assert arcs[0].arc == pytest.approx(float(example["expected_arc"]))

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.primary_direction_placidus import (
    PlacidianRaptParallelTarget,
    compute_placidian_converse_rapt_parallel_arc,
    compute_placidian_rapt_parallel_arc,
)
from moira.primary_directions import SpeculumEntry


_EXAMPLE_FIXTURES = json.loads(
    Path("tests/fixtures/primary_directions_placidus_examples.json").read_text(encoding="utf-8")
)


def _entry(
    name: str,
    *,
    ra: float,
    ha: float,
    dsa: float,
    nsa: float,
    upper: bool,
) -> SpeculumEntry:
    return SpeculumEntry(
        name=name,
        lon=0.0,
        lat=0.0,
        ra=ra,
        dec=0.0,
        ha=ha,
        dsa=dsa,
        nsa=nsa,
        upper=upper,
        f=0.0,
    )


def _entry_from_fixture(payload: dict[str, object]) -> SpeculumEntry:
    return _entry(
        str(payload["name"]),
        ra=float(payload["ra"]),
        ha=float(payload["ha"]),
        dsa=float(payload["dsa"]),
        nsa=float(payload["nsa"]),
        upper=bool(payload["upper"]),
    )


def test_placidian_rapt_parallel_target_exposes_stable_name() -> None:
    assert PlacidianRaptParallelTarget("Moon").name == "Moon Rapt Parallel"


def test_compute_placidian_rapt_parallel_arc_handles_same_hemisphere_case() -> None:
    promissor = _entry("Moon", ra=25.8375555556, ha=-80.1713888889, dsa=85.1691666667, nsa=94.8308333333, upper=True)
    significator = _entry("Mars", ra=287.3413888889, ha=-40.0, dsa=114.2928333333, nsa=65.7071666667, upper=True)

    arc = compute_placidian_rapt_parallel_arc(promissor, significator)

    expected_secondary_distance = 98.4961666667 * 85.1691666667 / (85.1691666667 + 114.2928333333)
    assert arc == pytest.approx(abs(80.1713888889 - expected_secondary_distance))


def test_compute_placidian_rapt_parallel_arc_handles_opposite_hemisphere_case() -> None:
    promissor = _entry("Saturn", ra=339.9380555556, ha=67.8833333333, dsa=76.2955555556, nsa=103.7044444444, upper=True)
    significator = _entry("Moon", ra=103.4305555556, ha=-120.0, dsa=113.4677777778, nsa=66.5322222222, upper=False)

    arc = compute_placidian_rapt_parallel_arc(promissor, significator)

    expected_secondary_distance = 56.5075 * 76.2955555556 / (76.2955555556 + 66.5322222222)
    assert arc == pytest.approx(abs(67.8833333333 - expected_secondary_distance), abs=1e-9)


def test_compute_placidian_converse_rapt_parallel_arc_matches_leo_style_example() -> None:
    promissor = _entry("Saturn", ra=339.95, ha=-67.8833333333, dsa=76.2955555556, nsa=103.7044444444, upper=True)
    significator = _entry("Moon", ra=103.45, ha=120.0, dsa=113.5, nsa=66.5, upper=False)

    arc = compute_placidian_converse_rapt_parallel_arc(promissor, significator)

    expected_secondary_distance = 123.5 * 103.7044444444 / (103.7044444444 + 66.5)
    assert arc == pytest.approx(abs(112.1166666667 - expected_secondary_distance), abs=1e-9)


def test_placidian_worked_example_fixtures_preserve_direct_and_converse_rapt_arcs() -> None:
    direct_example = _EXAMPLE_FIXTURES["direct_rapt_parallel_opposite_hemisphere"]
    converse_example = _EXAMPLE_FIXTURES["converse_rapt_parallel"]

    direct_promissor = _entry_from_fixture(direct_example["promissor"])
    direct_significator = _entry_from_fixture(direct_example["significator"])
    converse_promissor = _entry_from_fixture(converse_example["promissor"])
    converse_significator = _entry_from_fixture(converse_example["significator"])

    direct_arc = compute_placidian_rapt_parallel_arc(direct_promissor, direct_significator)
    converse_arc = compute_placidian_converse_rapt_parallel_arc(
        converse_promissor,
        converse_significator,
    )

    assert direct_arc == pytest.approx(direct_example["expected_arc_degrees"], abs=1e-9)
    assert direct_arc == pytest.approx(direct_example["published_arc_degrees"], abs=0.02)
    assert converse_arc == pytest.approx(converse_example["expected_arc_degrees"], abs=1e-9)
    assert converse_arc == pytest.approx(converse_example["published_arc_degrees"], abs=0.02)


def test_placidian_worked_example_fixtures_preserve_secondary_distances() -> None:
    direct_example = _EXAMPLE_FIXTURES["direct_rapt_parallel_opposite_hemisphere"]
    converse_example = _EXAMPLE_FIXTURES["converse_rapt_parallel"]

    direct_promissor = direct_example["promissor"]
    direct_significator = direct_example["significator"]
    converse_promissor = converse_example["promissor"]
    converse_significator = converse_example["significator"]

    direct_secondary = (
        float(direct_example["exact_ra_difference"]) * float(direct_promissor["dsa"])
        / (float(direct_promissor["dsa"]) + float(direct_significator["nsa"]))
    )
    converse_secondary = (
        float(converse_example["exact_ra_difference"]) * float(converse_promissor["nsa"])
        / (float(converse_promissor["nsa"]) + float(converse_significator["nsa"]))
    )

    assert direct_secondary == pytest.approx(direct_example["expected_secondary_distance"], abs=1e-9)
    assert direct_secondary == pytest.approx(direct_example["published_secondary_distance"], abs=0.02)
    assert converse_secondary == pytest.approx(converse_example["expected_secondary_distance"], abs=1e-9)
    assert converse_secondary == pytest.approx(converse_example["published_secondary_distance"], abs=0.02)

    direct_published_secondary = (
        float(direct_example["published_ra_difference"]) * float(direct_promissor["dsa"])
        / (float(direct_promissor["dsa"]) + float(direct_significator["nsa"]))
    )
    assert direct_published_secondary == pytest.approx(
        direct_example["published_secondary_distance"],
        abs=0.02,
    )

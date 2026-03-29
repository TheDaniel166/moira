from __future__ import annotations

import json
from pathlib import Path

import pytest

import moira.primary_direction_ptolemy as ptolemy_module
from moira.primary_direction_ptolemy import (
    PtolemaicParallelRelation,
    PtolemaicParallelTarget,
    project_ptolemaic_declination_point,
)


_EXAMPLE_FIXTURES = json.loads(
    Path("tests/fixtures/primary_directions_ptolemy_examples.json").read_text(encoding="utf-8")
)


def _published_arc_from_rising_times(source_hours: float, target_hours: float) -> float:
    return ((target_hours - source_hours) % 24.0) * 15.0


def test_ptolemaic_declination_projection_matches_parallel_style_examples() -> None:
    saturn_like = project_ptolemaic_declination_point(
        source_longitude=340.0,
        source_declination=6.0 + 54.0 / 60.0,
        obliquity=23.4392911,
        relation=PtolemaicParallelRelation.CONTRA_PARALLEL,
    )
    uranus_like = project_ptolemaic_declination_point(
        source_longitude=100.0,
        source_declination=23.0 + 24.0 / 60.0,
        obliquity=23.4392911,
        relation=PtolemaicParallelRelation.PARALLEL,
    )

    assert saturn_like == pytest.approx(342.6, abs=0.5)
    assert uranus_like == pytest.approx(93.22323381173652, abs=1e-6)


def test_ptolemaic_projection_matches_worked_example_fixtures() -> None:
    uranus_example = _EXAMPLE_FIXTURES["parallel_direct_uranus"]
    saturn_example = _EXAMPLE_FIXTURES["declination_equivalent_saturn"]

    uranus_longitude = project_ptolemaic_declination_point(
        source_longitude=uranus_example["source_longitude"],
        source_declination=uranus_example["source_declination"],
        obliquity=uranus_example["obliquity"],
        relation=PtolemaicParallelRelation(uranus_example["relation"]),
    )
    saturn_longitude = project_ptolemaic_declination_point(
        source_longitude=saturn_example["source_longitude"],
        source_declination=saturn_example["source_declination"],
        obliquity=saturn_example["obliquity"],
        relation=PtolemaicParallelRelation(saturn_example["relation"]),
    )

    assert uranus_longitude == pytest.approx(uranus_example["expected_equivalent_longitude"], abs=1e-9)
    assert uranus_longitude == pytest.approx(uranus_example["published_equivalent_longitude"], abs=1.0)
    assert saturn_longitude == pytest.approx(saturn_example["expected_equivalent_longitude"], abs=1e-9)
    assert saturn_longitude == pytest.approx(saturn_example["published_equivalent_longitude"], abs=0.25)


def test_ptolemaic_worked_example_fixtures_preserve_published_arc_measure() -> None:
    uranus_example = _EXAMPLE_FIXTURES["parallel_direct_uranus"]
    saturn_example = _EXAMPLE_FIXTURES["declination_equivalent_saturn"]

    uranus_arc = _published_arc_from_rising_times(
        uranus_example["published_source_rise_st_hours"],
        uranus_example["published_target_rise_st_hours"],
    )
    saturn_arc = _published_arc_from_rising_times(
        saturn_example["published_source_rise_st_hours"],
        saturn_example["published_target_rise_st_hours"],
    )

    assert uranus_arc == pytest.approx(uranus_example["published_arc_degrees"], abs=1e-9)
    assert saturn_arc == pytest.approx(saturn_example["published_arc_degrees"], abs=1e-9)


def test_ptolemaic_declination_projection_contra_parallel_negates_declination() -> None:
    parallel_longitude = project_ptolemaic_declination_point(
        source_longitude=134.0,
        source_declination=10.0,
        obliquity=23.4392911,
        relation=PtolemaicParallelRelation.PARALLEL,
    )
    contra_longitude = project_ptolemaic_declination_point(
        source_longitude=134.0,
        source_declination=10.0,
        obliquity=23.4392911,
        relation=PtolemaicParallelRelation.CONTRA_PARALLEL,
    )

    assert parallel_longitude == pytest.approx(154.11626662979472, abs=1e-9)
    assert contra_longitude == pytest.approx(205.88373337020528, abs=1e-9)


def test_ptolemaic_declination_projection_rejects_unreachable_declination() -> None:
    with pytest.raises(ValueError):
        project_ptolemaic_declination_point(
            source_longitude=120.0,
            source_declination=30.0,
            obliquity=23.4392911,
            relation=PtolemaicParallelRelation.PARALLEL,
        )


def test_ptolemaic_parallel_target_exposes_stable_name() -> None:
    assert PtolemaicParallelTarget("Uranus").name == "Uranus Parallel"
    assert (
        PtolemaicParallelTarget("Saturn", PtolemaicParallelRelation.CONTRA_PARALLEL).name
        == "Saturn Contra-Parallel"
    )


def test_ptolemy_module_exports_curated_surface() -> None:
    assert {
        "PtolemaicParallelRelation",
        "PtolemaicParallelTarget",
        "project_ptolemaic_declination_point",
    } <= set(ptolemy_module.__all__)

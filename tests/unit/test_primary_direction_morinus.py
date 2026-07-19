from __future__ import annotations

import math

import pytest

import moira.primary_directions.morinus as morinus_module
from moira.primary_directions.morinus import (
    MorinusAspectContext,
    project_morinus_aspect_point,
)


def test_morinus_aspect_projection_matches_published_example() -> None:
    longitude, latitude = project_morinus_aspect_point(
        longitude=203.0 + 34.0 / 60.0,
        latitude=1.0 + 10.0 / 60.0,
        maximum_latitude=1.0 + 34.0 / 60.0,
        moving_toward_maximum=False,
        aspect_angle=60.0,
    )

    assert longitude == pytest.approx(263.0 + 33.0 / 60.0, abs=0.2)
    assert latitude == pytest.approx(-(20.0 / 60.0), abs=0.2)


def test_morinus_context_rejects_invalid_maximum_latitude() -> None:
    with pytest.raises(ValueError):
        MorinusAspectContext(source_name="Moon", maximum_latitude=0.0, moving_toward_maximum=True)


def test_morinus_context_requires_a_string_identity_and_normalizes_outer_space() -> None:
    with pytest.raises(ValueError, match="string source_name"):
        MorinusAspectContext(  # type: ignore[arg-type]
            source_name=123,
            maximum_latitude=5.0,
            moving_toward_maximum=True,
        )
    with pytest.raises(ValueError, match="string source_name"):
        MorinusAspectContext(
            source_name="   ",
            maximum_latitude=5.0,
            moving_toward_maximum=True,
        )

    context = MorinusAspectContext(
        source_name="  Moon  ",
        maximum_latitude=5.0,
        moving_toward_maximum=True,
    )
    assert context.source_name == "Moon"


def test_morinus_aspect_projection_preserves_quadrants_and_normalization() -> None:
    before_square, _ = project_morinus_aspect_point(
        longitude=0.0,
        latitude=0.0,
        maximum_latitude=6.0,
        moving_toward_maximum=True,
        aspect_angle=89.999,
    )
    after_square, _ = project_morinus_aspect_point(
        longitude=0.0,
        latitude=0.0,
        maximum_latitude=6.0,
        moving_toward_maximum=True,
        aspect_angle=90.001,
    )
    trine, _ = project_morinus_aspect_point(
        longitude=0.0,
        latitude=0.0,
        maximum_latitude=6.0,
        moving_toward_maximum=True,
        aspect_angle=120.0,
    )
    opposition, _ = project_morinus_aspect_point(
        longitude=0.0,
        latitude=0.0,
        maximum_latitude=6.0,
        moving_toward_maximum=True,
        aspect_angle=180.0,
    )

    assert abs(after_square - before_square) < 0.003
    assert 90.0 < trine < 180.0
    assert opposition == pytest.approx(180.0)
    assert all(0.0 <= value < 360.0 for value in (before_square, after_square, trine, opposition))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"latitude": 20.0, "maximum_latitude": 5.0}, "exceeds its path maximum"),
        ({"latitude": -1.0, "maximum_latitude": 5.0}, "opposite signs"),
        ({"longitude": math.nan}, "finite real longitude"),
        ({"aspect_angle": math.inf}, "finite real aspect_angle"),
        ({"moving_toward_maximum": 1}, "boolean moving_toward_maximum"),
    ],
)
def test_morinus_aspect_projection_rejects_invalid_or_impossible_context(
    kwargs: dict[str, object],
    message: str,
) -> None:
    inputs: dict[str, object] = {
        "longitude": 20.0,
        "latitude": 1.0,
        "maximum_latitude": 5.0,
        "moving_toward_maximum": True,
        "aspect_angle": 60.0,
    }
    inputs.update(kwargs)
    with pytest.raises(ValueError, match=message):
        project_morinus_aspect_point(**inputs)


def test_morinus_module_exports_curated_surface() -> None:
    assert {"MorinusAspectContext", "project_morinus_aspect_point"} <= set(morinus_module.__all__)

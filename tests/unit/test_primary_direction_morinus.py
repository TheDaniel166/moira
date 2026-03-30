from __future__ import annotations

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


def test_morinus_module_exports_curated_surface() -> None:
    assert {"MorinusAspectContext", "project_morinus_aspect_point"} <= set(morinus_module.__all__)

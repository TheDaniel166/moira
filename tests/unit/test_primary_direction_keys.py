from __future__ import annotations

import pytest

import moira.primary_directions.keys as key_module
from moira.primary_directions.keys import (
    PrimaryDirectionKey,
    PrimaryDirectionKeyFamily,
    PrimaryDirectionKeyPolicy,
    convert_arc_to_time,
    primary_direction_key_truth,
)


def test_primary_direction_key_truth_exposes_expected_families_and_rates() -> None:
    ptolemy = primary_direction_key_truth(PrimaryDirectionKey.PTOLEMY)
    naibod = primary_direction_key_truth(PrimaryDirectionKey.NAIBOD)
    cardan = primary_direction_key_truth(PrimaryDirectionKey.CARDAN)
    solar = primary_direction_key_truth(PrimaryDirectionKey.SOLAR, solar_rate=0.9)

    assert ptolemy.family is PrimaryDirectionKeyFamily.STATIC
    assert ptolemy.rate_degrees_per_year == pytest.approx(1.0)
    assert naibod.family is PrimaryDirectionKeyFamily.STATIC
    assert naibod.rate_degrees_per_year == pytest.approx(360.0 / 365.25)
    assert cardan.family is PrimaryDirectionKeyFamily.STATIC
    assert cardan.rate_degrees_per_year == pytest.approx(59.0 / 60.0 + 12.0 / 3600.0)
    assert solar.family is PrimaryDirectionKeyFamily.DYNAMIC
    assert solar.rate_degrees_per_year == pytest.approx(0.9)


def test_primary_direction_key_truth_normalizes_unknown_and_bad_solar_rate() -> None:
    unknown = primary_direction_key_truth("unknown")
    solar = primary_direction_key_truth("solar", solar_rate=0.0)

    assert unknown.key is PrimaryDirectionKey.NAIBOD
    assert solar.rate_degrees_per_year == pytest.approx(360.0 / 365.25)


def test_convert_arc_to_time_uses_key_truth() -> None:
    assert convert_arc_to_time(10.0, PrimaryDirectionKey.PTOLEMY) == pytest.approx(10.0)
    assert convert_arc_to_time(10.0, PrimaryDirectionKey.NAIBOD) == pytest.approx(
        10.0 / (360.0 / 365.25)
    )
    assert convert_arc_to_time(10.0, PrimaryDirectionKey.CARDAN) == pytest.approx(
        10.0 / (59.0 / 60.0 + 12.0 / 3600.0)
    )
    assert convert_arc_to_time(10.0, PrimaryDirectionKey.SOLAR, solar_rate=0.5) == pytest.approx(20.0)


def test_convert_arc_to_time_rejects_non_positive_arc() -> None:
    with pytest.raises(ValueError):
        convert_arc_to_time(0.0)


def test_primary_direction_key_module_exports_curated_surface() -> None:
    expected = {
        "PrimaryDirectionKey",
        "PrimaryDirectionKeyFamily",
        "PrimaryDirectionKeyPolicy",
        "PrimaryDirectionKeyTruth",
        "convert_arc_to_time",
        "primary_direction_key_truth",
    }
    assert expected <= set(key_module.__all__)
    assert "_normalize_key" not in key_module.__all__


def test_primary_direction_key_policy_rejects_unsupported_type() -> None:
    with pytest.raises(ValueError):
        PrimaryDirectionKeyPolicy("ptolemy")  # type: ignore[arg-type]

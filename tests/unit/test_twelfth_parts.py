"""Natal twelfth-part atom and source-owned golden."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.twelfth_parts import twelfth_part_of


_GOLDEN = Path(__file__).parents[1] / "golden" / "hellenistic_twelfth_parts.json"


def test_twelfth_part_golden_cases() -> None:
    payload = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    for case in payload["cases"]:
        result = twelfth_part_of(case["longitude"])
        assert result.occupied_sign == case["occupied_sign"]
        assert result.slice_index == case["slice_index"]
        assert result.twelfth_part_sign == case["twelfth_part_sign"]
        assert result.projected_longitude == pytest.approx(
            case["projected_longitude"]
        )


def test_twelfth_part_rejects_non_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        twelfth_part_of(float("nan"))


def test_twelfth_part_is_not_vedic_dwadashamsa_counterexample() -> None:
    """Even signs in some D12 schemes start from a different sign than 12×."""

    result = twelfth_part_of(287.0)
    assert result.twelfth_part_sign == "Cancer"
    assert result.projected_longitude == pytest.approx(114.0)

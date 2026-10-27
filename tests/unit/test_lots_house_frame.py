"""Lots results record the house frame whose cusps produced them.

House-based lots change between Whole Sign and quadrant cusps, and a quadrant
request can fall back to another system at high latitude. The facade records
the requested and effective system on every part and on the evaluation.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import moira
import moira.classical as classical
import moira.facade as facade
from moira.constants import HouseSystem
from moira.lots import LotsHouseFrame, evaluate_lots

NATAL_DT = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_facade_lots_record_the_requested_and_effective_system(moira_engine) -> None:
    chart = moira_engine.chart(NATAL_DT)
    for system in (HouseSystem.WHOLE_SIGN, HouseSystem.PLACIDUS):
        houses = moira_engine.houses(NATAL_DT, 51.5085, -0.1257, system)
        expected = LotsHouseFrame(
            system=system,
            effective_system=system,
            fallback=False,
        )

        parts = moira_engine.lots(chart, houses)
        evaluation = moira_engine.evaluate_lots(chart, houses)

        assert parts and all(part.house_frame == expected for part in parts)
        assert evaluation.house_frame == expected
        assert all(part.house_frame == expected for part in evaluation.parts)


def test_facade_lots_record_a_polar_quadrant_fallback(moira_engine) -> None:
    chart = moira_engine.chart(NATAL_DT)
    houses = moira_engine.houses(NATAL_DT, 70.0, 20.0, HouseSystem.PLACIDUS)
    assert houses.fallback is True

    evaluation = moira_engine.evaluate_lots(chart, houses)

    assert evaluation.house_frame.system == HouseSystem.PLACIDUS
    assert evaluation.house_frame.effective_system == houses.effective_system
    assert evaluation.house_frame.effective_system != HouseSystem.PLACIDUS
    assert evaluation.house_frame.fallback is True
    assert evaluation.house_frame.fallback_reason == houses.fallback_reason


def test_core_lots_leave_the_frame_unset_unless_supplied() -> None:
    positions = {
        "Sun": 10.0,
        "Moon": 45.0,
        "Mercury": 80.0,
        "Venus": 125.0,
        "Mars": 170.0,
        "Jupiter": 230.0,
        "Saturn": 300.0,
    }
    cusps = {number: (number - 1) * 30.0 for number in range(1, 13)}

    evaluation = evaluate_lots(positions, cusps, True, asc_longitude=15.0)

    assert evaluation.house_frame is None
    assert all(part.house_frame is None for part in evaluation.parts)


def test_house_frame_rejects_an_inconsistent_fallback_flag() -> None:
    with pytest.raises(ValueError, match="fallback must be true exactly"):
        LotsHouseFrame(system="P", effective_system="O", fallback=False)
    with pytest.raises(ValueError, match="fallback must be true exactly"):
        LotsHouseFrame(system="P", effective_system="P", fallback=True)


def test_house_frame_is_exported_on_every_public_surface() -> None:
    for surface in (moira, classical, facade):
        assert surface.LotsHouseFrame is LotsHouseFrame
        assert "LotsHouseFrame" in surface.__all__

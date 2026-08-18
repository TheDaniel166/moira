"""Supporting Exaltation / Basis helpers stay outside the profile partition."""

from __future__ import annotations

import pytest

from moira.hellenistic import HELLENISTIC_PROFILE_LOTS
from moira.lots import (
    HELLENISTIC_SUPPORTING_LOTS,
    exaltation_lot_name,
    evaluate_lots,
    select_supporting_hellenistic_lots,
)


POSITIONS = {
    "Sun": 10.0,
    "Moon": 45.0,
    "Mercury": 80.0,
    "Venus": 125.0,
    "Mars": 170.0,
    "Jupiter": 230.0,
    "Saturn": 300.0,
}
CUSPS = {number: (number - 1) * 30.0 for number in range(1, 13)}


def test_exaltation_name_follows_sect() -> None:
    assert exaltation_lot_name(is_day_chart=True) == "Exaltation (Day)"
    assert exaltation_lot_name(is_day_chart=False) == "Exaltation (Night)"


def test_supporting_lots_are_outside_profile_partition() -> None:
    assert set(HELLENISTIC_SUPPORTING_LOTS).isdisjoint(HELLENISTIC_PROFILE_LOTS)


def test_select_supporting_lots_from_evaluation() -> None:
    evaluation = evaluate_lots(
        POSITIONS,
        CUSPS,
        True,
        asc_longitude=15.0,
        mc_longitude=280.0,
    )
    evaluated, unresolved = select_supporting_hellenistic_lots(
        evaluation,
        is_day_chart=True,
    )
    names = {part.name for part in evaluated} | {item.name for item in unresolved}
    assert names == {"Exaltation (Day)", "Basis (Valens)"}
    assert "Exaltation (Night)" not in names


def test_exaltation_lot_name_requires_bool() -> None:
    with pytest.raises(TypeError):
        exaltation_lot_name(is_day_chart=1)  # type: ignore[arg-type]

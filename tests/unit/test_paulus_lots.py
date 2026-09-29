"""Paulus Alexandrinus, Introduction ch. 23 (Schmidt trans., 1993, pp. 42-44):
Eros "from the Lot of Spirit to the degree of Aphrodite" and Necessity "from
the degree of Hermes to Lot of the Fortune" by day, "the reverse" by night.

Paulus gives no worked example for these lots; the tests check the formula
directly and against the independent ``moira.nine_parts`` path, which
implements the same chapter.
"""

from __future__ import annotations

import pytest

from moira.lots import calculate_lots
from moira.nine_parts import nine_parts_abu_mashar

_POSITIONS = {
    "Sun": 10.0, "Moon": 100.0, "Mercury": 20.0, "Venus": 40.0,
    "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
}
_ASC = 15.0
_CUSPS = {i + 1: (_ASC + 30.0 * i) % 360.0 for i in range(12)}


@pytest.mark.parametrize("is_day", [True, False])
def test_paulus_necessity_and_eros_follow_chapter_23(is_day: bool) -> None:
    parts = {part.name: part.longitude for part in calculate_lots(_POSITIONS, _CUSPS, is_day)}
    fortune, spirit = parts["Fortune"], parts["Spirit"]
    mercury, venus = _POSITIONS["Mercury"], _POSITIONS["Venus"]
    if is_day:
        necessity = (_ASC + fortune - mercury) % 360.0
        eros = (_ASC + venus - spirit) % 360.0
    else:
        necessity = (_ASC + mercury - fortune) % 360.0
        eros = (_ASC + spirit - venus) % 360.0
    assert parts["Necessity (Paulus)"] == pytest.approx(necessity)
    assert parts["Eros (Paulus)"] == pytest.approx(eros)

    seven = {
        str(part.name): part.longitude
        for part in nine_parts_abu_mashar(_ASC, _POSITIONS, not is_day).parts_set.parts
    }
    assert parts["Necessity (Paulus)"] == pytest.approx(seven["Necessity"])
    assert parts["Eros (Paulus)"] == pytest.approx(seven["Love"])

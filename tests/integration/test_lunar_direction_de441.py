"""DE441 integration evidence for the neutral lunar crossing witness."""

from __future__ import annotations

from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira.constants import Body
from moira.lunar_direction import lunar_ecliptic_direction_at
from moira.planets import planet_at
from moira.spk_reader import SpkReader


@pytest.mark.requires_ephemeris
def test_de441_crossings_bracket_query_and_change_latitude_sign() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None
    assert Path(kernel).name == "de441.bsp"
    query = 2451545.0
    with SpkReader(kernel) as reader:
        result = lunar_ecliptic_direction_at(query, reader=reader)
        for crossing in (result.previous_crossing, result.next_crossing):
            before = planet_at(Body.MOON, crossing.jd_ut - 1e-4, reader=reader)
            after = planet_at(Body.MOON, crossing.jd_ut + 1e-4, reader=reader)
            assert before.latitude * after.latitude < 0.0
            assert abs(crossing.latitude_residual_deg) < 1e-9

    assert result.previous_crossing.jd_ut <= query <= result.next_crossing.jd_ut
    assert result.reference_frame.startswith("apparent_geocentric")

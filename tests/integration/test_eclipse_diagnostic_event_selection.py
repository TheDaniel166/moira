"""Boundary selection for the opt-in diagnostic, independent of HTTP."""
import math

import pytest

from moira.phenomena import next_moon_phase
from moira_server.services.eclipse_diagnostics import _select_solar_event

pytestmark = pytest.mark.requires_ephemeris


@pytest.mark.parametrize(
    "seed,backward",
    [(2457986.0, True), (2460054.0, False), (2460408.0, True)],
)
def test_adjacent_solar_maximum_at_new_moon_and_neighbouring_floats(
    eclipse_calculator, seed, backward,
):
    phase = next_moon_phase("New Moon", seed, reader=eclipse_calculator._reader).jd_ut
    event = eclipse_calculator._solar_eclipse_near_syzygy(phase, kind_key="any")
    assert event is not None
    assert (event.jd_ut < phase) is backward
    for query in (math.nextafter(phase, -math.inf), phase, math.nextafter(phase, math.inf)):
        selected = _select_solar_event(eclipse_calculator, query, backward=backward)
        assert selected.jd_ut == pytest.approx(event.jd_ut, abs=0.05 / 86400)


def test_2024_backward_seed_between_greatest_and_new_moon(eclipse_calculator):
    selected = _select_solar_event(eclipse_calculator, 2460409.26325, backward=True)
    assert selected.jd_ut == pytest.approx(2460409.2620393815, abs=0.05 / 86400)

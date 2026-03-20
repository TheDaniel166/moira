from __future__ import annotations

import pytest

from moira.compat.nasa.eclipse import (
    next_nasa_lunar_eclipse,
    translate_lunar_eclipse_event,
)
from moira.eclipse import EclipseCalculator


@pytest.mark.slow
def test_nasa_lunar_adapter_returns_canon_fields() -> None:
    calc = EclipseCalculator()
    event = calc.next_lunar_eclipse(2451560.0, kind="total")
    compat = translate_lunar_eclipse_event(calc, event)
    assert compat.jd_tt > compat.jd_ut
    assert compat.gamma_earth_radii >= 0.0
    assert compat.umbral_magnitude > 1.0
    assert compat.penumbral_magnitude > compat.umbral_magnitude
    assert compat.contacts.u2_ut is not None
    assert compat.contacts.u3_ut is not None
    assert compat.canon_method == "nasa_shadow_axis_geometric_moon"
    assert "geometric Moon" in compat.source_model


@pytest.mark.slow
def test_next_nasa_lunar_eclipse_wrapper_finds_total_event() -> None:
    compat = next_nasa_lunar_eclipse(2451560.0, kind="total")
    assert compat.moira_event.data.is_lunar_eclipse
    assert compat.moira_event.data.eclipse_type.is_total
    assert compat.canon_method == "nasa_shadow_axis_geometric_moon"

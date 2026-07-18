from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

import moira.eclipse_canon as eclipse_canon
from moira.constants import Body
from moira.eclipse_canon import (
    _find_roots,
    _tt_to_ut_nasa_catalog,
    _ut_to_tt_nasa_catalog,
    find_lunar_contacts_canon,
)
from moira.julian import julian_day
from moira.compat.nasa.eclipse import (
    next_nasa_lunar_eclipse,
    translate_lunar_eclipse_event,
)


@pytest.mark.slow
def test_nasa_lunar_adapter_returns_canon_fields(eclipse_calculator) -> None:
    calc = eclipse_calculator
    event = calc.next_lunar_eclipse(2451560.0, kind="total")
    compat = translate_lunar_eclipse_event(calc, event)
    assert compat.jd_tt > compat.jd_ut
    assert compat.gamma_earth_radii == pytest.approx(-0.2957, abs=0.0015)
    assert compat.umbral_magnitude > 1.0
    assert compat.umbral_magnitude < 2.0
    assert compat.penumbral_magnitude > compat.umbral_magnitude
    assert compat.contacts.u2_ut is not None
    assert compat.contacts.u3_ut is not None
    assert compat.canon_method == "nasa_shadow_axis_apparent_sun_moon"
    assert "annual-aberration" in compat.source_model


@pytest.mark.slow
def test_next_nasa_lunar_eclipse_wrapper_finds_total_event() -> None:
    compat = next_nasa_lunar_eclipse(2451560.0, kind="total")
    assert compat.moira_event.data.is_lunar_eclipse
    assert compat.moira_event.data.eclipse_type.is_total
    assert compat.canon_method == "nasa_shadow_axis_apparent_sun_moon"


def test_apparent_canon_vector_policy_applies_light_time_then_aberration_to_both_bodies(
    monkeypatch,
) -> None:
    reader = object()
    calculator = SimpleNamespace(_reader=reader)
    earth_position = (10.0, 20.0, 30.0)
    earth_velocity = (1.0, 2.0, 3.0)
    sun_light_time = (100.0, 101.0, 102.0)
    moon_light_time = (200.0, 201.0, 202.0)
    sun_apparent = (110.0, 111.0, 112.0)
    moon_apparent = (210.0, 211.0, 212.0)
    calls: list[tuple[str, object]] = []

    def earth_state(jd_tt, actual_reader):
        assert jd_tt == 2451545.0
        assert actual_reader is reader
        calls.append(("earth_state", actual_reader))
        return earth_position, earth_velocity

    def light_time(body, jd_tt, actual_reader, earth_ssb, barycentric_fn):
        assert jd_tt == 2451545.0
        assert actual_reader is reader
        assert earth_ssb is earth_position
        assert barycentric_fn is eclipse_canon._barycentric
        calls.append(("light_time", body))
        vector = sun_light_time if body == Body.SUN else moon_light_time
        return vector, 0.0

    def aberration(vector, velocity):
        assert velocity is earth_velocity
        calls.append(("aberration", vector))
        if vector is sun_light_time:
            return sun_apparent
        if vector is moon_light_time:
            return moon_apparent
        raise AssertionError("aberration received a vector not produced by light-time")

    monkeypatch.setattr(eclipse_canon, "_earth_barycentric_state", earth_state)
    monkeypatch.setattr(eclipse_canon, "apply_light_time", light_time)
    monkeypatch.setattr(eclipse_canon, "apply_aberration", aberration)

    sun, moon = eclipse_canon._lunar_canon_vectors_tt(
        calculator,
        2451545.0,
        method="nasa_shadow_axis_apparent_sun_moon",
    )

    assert (sun, moon) == (sun_apparent, moon_apparent)
    assert calls == [
        ("earth_state", reader),
        ("light_time", Body.SUN),
        ("light_time", Body.MOON),
        ("aberration", sun_light_time),
        ("aberration", moon_light_time),
    ]


def test_nasa_catalog_inverse_rejects_month_overlap() -> None:
    boundary = julian_day(-2000, 2, 1)
    left_tt = _ut_to_tt_nasa_catalog(math.nextafter(boundary, -math.inf))
    right_tt = _ut_to_tt_nasa_catalog(boundary)
    assert right_tt < left_tt

    with pytest.raises(ValueError, match="multiple self-consistent UT branches"):
        _tt_to_ut_nasa_catalog((left_tt + right_tt) / 2.0)


def test_nasa_catalog_inverse_rejects_month_gap() -> None:
    boundary = julian_day(3000, 2, 1)
    left_tt = _ut_to_tt_nasa_catalog(math.nextafter(boundary, -math.inf))
    right_tt = _ut_to_tt_nasa_catalog(boundary)
    assert right_tt > left_tt

    with pytest.raises(ValueError, match="no self-consistent UT branch"):
        _tt_to_ut_nasa_catalog((left_tt + right_tt) / 2.0)


def test_canon_root_scan_deduplicates_exact_grid_root() -> None:
    assert _find_roots(lambda value: value - 1.0, 0.0, 2.0, 1.0) == [1.0]


def test_canon_root_scan_clamps_final_step_to_window_end() -> None:
    assert _find_roots(lambda value: value - 1.1, 0.0, 1.0, 0.6) == []
    assert _find_roots(lambda value: value - 1.0, 0.0, 1.0, 0.6) == [1.0]


@pytest.mark.parametrize(
    ("start", "end", "step_days", "message"),
    [
        (math.nan, 1.0, 0.1, "bounds must be finite"),
        (0.0, math.inf, 0.1, "bounds must be finite"),
        (1.0, 1.0, 0.1, "end must be greater"),
        (1.0, 0.0, 0.1, "end must be greater"),
        (0.0, 1.0, 0.0, "finite and positive"),
        (0.0, 1.0, -0.1, "finite and positive"),
        (0.0, 1.0, math.nan, "finite and positive"),
        (0.0, 1.0, math.inf, "finite and positive"),
        (2451545.0, 2451546.0, 1e-20, "too small to advance"),
    ],
)
def test_canon_root_scan_rejects_invalid_window_or_step(
    start: float,
    end: float,
    step_days: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _find_roots(lambda value: value, start, end, step_days)


def test_canon_root_scan_rejects_nonfinite_function_value() -> None:
    with pytest.raises(ValueError, match="function returned a non-finite"):
        _find_roots(lambda _value: math.nan, 0.0, 1.0, 0.1)


@pytest.mark.parametrize("window_days", [0.0, -0.1, math.nan, math.inf])
def test_canon_contact_solver_rejects_invalid_window(window_days: float) -> None:
    with pytest.raises(ValueError, match="window_days must be finite and positive"):
        find_lunar_contacts_canon(None, 2451545.0, window_days=window_days)


@pytest.mark.parametrize("coarse_step_seconds", [0.0, -1.0, math.nan, math.inf])
def test_canon_contact_solver_rejects_invalid_step(coarse_step_seconds: float) -> None:
    with pytest.raises(ValueError, match="coarse_step_seconds must be finite and positive"):
        find_lunar_contacts_canon(
            None,
            2451545.0,
            coarse_step_seconds=coarse_step_seconds,
        )


@pytest.mark.parametrize(
    ("center_jd_ut", "window_days"),
    [
        (2451545.0, 1.0e-20),
        (1.0e308, 1.0e308),
    ],
)
def test_canon_contact_solver_rejects_collapsed_or_nonfinite_derived_window(
    center_jd_ut: float,
    window_days: float,
) -> None:
    with pytest.raises(ValueError, match="finite ordered bounds"):
        find_lunar_contacts_canon(
            None,
            center_jd_ut,
            window_days=window_days,
        )


def test_canon_contact_solver_rejects_day_step_underflow_before_computation() -> None:
    with pytest.raises(ValueError, match="too small to form a positive day step"):
        find_lunar_contacts_canon(
            None,
            2451545.0,
            coarse_step_seconds=math.nextafter(0.0, 1.0),
        )

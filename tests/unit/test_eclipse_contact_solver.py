from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

import moira.eclipse_canon as eclipse_canon
from moira._eclipse_contact_solver import _find_contact_pair
from moira.eclipse_contacts import find_lunar_contacts


def test_off_grid_quadratic_tangent_returns_equal_contacts() -> None:
    tangent = 0.37

    ingress, egress = _find_contact_pair(
        lambda value: (value - tangent) ** 2,
        0.0,
        1.0,
        0.2,
        greatest_jd=0.35,
        clearance_tolerance=1.0e-10,
    )

    assert ingress == egress
    assert ingress == pytest.approx(tangent, abs=1.0e-7)


def test_negative_dip_narrower_than_coarse_step_returns_two_contacts() -> None:
    minimum = 0.37
    ingress, egress = _find_contact_pair(
        lambda value: (value - minimum) ** 2 - 1.0e-4,
        0.0,
        1.0,
        0.2,
        greatest_jd=0.35,
        clearance_tolerance=1.0e-10,
    )

    assert ingress == pytest.approx(0.36, abs=1.0e-7)
    assert egress == pytest.approx(0.38, abs=1.0e-7)
    assert ingress < minimum < egress


@pytest.mark.parametrize(
    ("start", "end", "expected_ingress", "expected_egress"),
    [
        (0.37, 1.0, None, 0.38),
        (0.0, 0.37, 0.36, None),
    ],
)
def test_truncated_window_preserves_only_the_contact_inside_it(
    start: float,
    end: float,
    expected_ingress: float | None,
    expected_egress: float | None,
) -> None:
    ingress, egress = _find_contact_pair(
        lambda value: (value - 0.37) ** 2 - 1.0e-4,
        start,
        end,
        0.2,
        greatest_jd=0.37,
        clearance_tolerance=1.0e-10,
    )

    if expected_ingress is None:
        assert ingress is None
    else:
        assert ingress == pytest.approx(expected_ingress, abs=1.0e-7)
    if expected_egress is None:
        assert egress is None
    else:
        assert egress == pytest.approx(expected_egress, abs=1.0e-7)


def test_near_miss_above_clearance_tolerance_has_no_contacts() -> None:
    assert _find_contact_pair(
        lambda value: (value - 0.37) ** 2 + 1.1e-6,
        0.0,
        1.0,
        0.2,
        greatest_jd=0.37,
        clearance_tolerance=1.0e-6,
    ) == (None, None)


@pytest.mark.parametrize(
    ("start", "end", "greatest", "expected"),
    [
        (0.5, 1.0, 0.5, (0.5, None)),
        (0.0, 0.5, 0.5, (None, 0.5)),
    ],
)
def test_contact_at_window_boundary_is_admitted_only_on_that_side(
    start: float,
    end: float,
    greatest: float,
    expected: tuple[float | None, float | None],
) -> None:
    assert _find_contact_pair(
        lambda value: (value - 0.5) ** 2,
        start,
        end,
        0.2,
        greatest_jd=greatest,
        clearance_tolerance=1.0e-10,
    ) == expected


def test_contact_pair_rejects_constant_zero_plateau() -> None:
    with pytest.raises(ValueError, match="constant zero plateau"):
        _find_contact_pair(
            lambda _value: 0.0,
            0.0,
            1.0,
            0.2,
            greatest_jd=0.5,
            clearance_tolerance=1.0e-6,
        )


@pytest.mark.parametrize("non_finite", [math.nan, math.inf, -math.inf])
def test_contact_pair_rejects_non_finite_margin(non_finite: float) -> None:
    with pytest.raises(ValueError, match="function returned a non-finite value"):
        _find_contact_pair(
            lambda _value: non_finite,
            0.0,
            1.0,
            0.2,
            greatest_jd=0.5,
            clearance_tolerance=1.0e-6,
        )


def test_contact_pair_rejects_step_too_small_to_advance() -> None:
    with pytest.raises(ValueError, match="too small to advance"):
        _find_contact_pair(
            lambda value: value,
            2_451_545.0,
            2_451_546.0,
            1.0e-20,
            greatest_jd=2_451_545.5,
            clearance_tolerance=1.0e-6,
        )


class _NativeTangentCalculator:
    _center = 2_451_545.0

    def calculate_jd(self, _jd: float) -> SimpleNamespace:
        return SimpleNamespace(
            eclipse_type=SimpleNamespace(is_partial=False, is_total=False),
        )

    def _lunar_shadow_axis_distance_km(
        self,
        jd: float,
        *,
        retarded_moon: bool,
    ) -> float:
        assert not retarded_moon
        return 2.0 + (jd - self._center) ** 2

    def _lunar_event_geometry_ut(
        self,
        jd: float,
        *,
        retarded_moon: bool,
    ) -> tuple[float, float, float, float, float]:
        assert not retarded_moon
        axis = 2.0 + (jd - self._center) ** 2
        return axis, 1.0, 0.5, 1.0, 384_400.0


def test_native_contact_vessel_preserves_a_tangent_as_both_sides() -> None:
    contacts = find_lunar_contacts(
        _NativeTangentCalculator(),
        _NativeTangentCalculator._center,
        window_days=0.1,
        coarse_step_seconds=3600.0,
    )

    assert contacts.p1 == contacts.p4
    assert contacts.p1 == pytest.approx(_NativeTangentCalculator._center, abs=1.0e-7)
    assert contacts.u1 is None
    assert contacts.u4 is None
    assert contacts.u2 is None
    assert contacts.u3 is None


def test_canon_contact_vessel_uses_the_same_physical_tangent_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    center_tt = 2_451_545.0
    monkeypatch.setattr(
        eclipse_canon,
        "refine_lunar_greatest_eclipse_canon_tt",
        lambda *_args, **_kwargs: center_tt,
    )

    def geometry(_calculator, jd_tt: float, *, method: str) -> SimpleNamespace:
        del method
        gamma = 2.0 + (jd_tt - center_tt) ** 2
        return SimpleNamespace(
            gamma_earth_radii=gamma,
            moon_radius_earth_radii=1.0,
            umbra_radius_earth_radii=0.5,
            penumbra_radius_earth_radii=1.0,
        )

    monkeypatch.setattr(eclipse_canon, "lunar_canon_geometry", geometry)
    contacts = eclipse_canon.find_lunar_contacts_canon(
        None,
        center_tt,
        window_days=0.1,
        coarse_step_seconds=3600.0,
    )

    assert contacts.p1_tt == contacts.p4_tt
    assert contacts.p1_tt == pytest.approx(center_tt, abs=1.0e-7)
    assert contacts.u1_tt is None
    assert contacts.u4_tt is None
    assert contacts.u2_tt is None
    assert contacts.u3_tt is None

"""Checked scalar Vondrak precession samples and fail-closed boundaries."""
import math

import pytest

from moira import _eclipse_strict_vondrak as strict
from moira import precession
from moira._eclipse_interval_roots import EnclosureUnavailable


@pytest.mark.parametrize("centuries", [-2000.0, -152.0, -116.5, -50.0, 0.0, 50.0, 152.0, 2000.0])
def test_strict_vondrak_matches_ordinary_model_numerically(centuries):
    tt = 2451545.0 + centuries * 36525.0
    actual = strict.strict_vondrak_precession_matrix(tt)
    expected = precession._vondrak_bias_precession_matrix(tt)
    for row, reference in zip(actual, expected):
        for value, expected_value in zip(row, reference):
            assert value == pytest.approx(expected_value, abs=2e-14)


@pytest.mark.parametrize("centuries", [-50.0, -152.0, 50.0, 152.0])
def test_strict_vondrak_does_not_call_platform_sin_cos(monkeypatch, centuries):
    tt = 2451545.0 + centuries * 36525.0
    expected = precession._vondrak_bias_precession_matrix(tt)

    def forbidden(*args):
        raise AssertionError("platform trigonometry used")

    monkeypatch.setattr(math, "sin", forbidden)
    monkeypatch.setattr(math, "cos", forbidden)
    actual = strict.strict_vondrak_precession_matrix(tt)
    for row, reference in zip(actual, expected):
        for value, expected_value in zip(row, reference):
            assert value == pytest.approx(expected_value, abs=2e-14)


def test_singular_equinox_is_unavailable(monkeypatch):
    pole = (0.0, 0.0, 1.0)
    monkeypatch.setattr(strict, "_ecliptic_pole", lambda t: pole)
    monkeypatch.setattr(strict, "_equatorial_pole", lambda t: pole)
    with pytest.raises(EnclosureUnavailable, match="singular"):
        strict.strict_vondrak_precession_matrix(2451545.0)


@pytest.mark.parametrize("tt", [True, float("inf"), float("nan"), 10**400])
def test_nonfinite_or_boolean_tt_is_rejected(tt):
    with pytest.raises(ValueError, match="finite"):
        strict.strict_vondrak_precession_matrix(tt)


def test_outside_model_domain_is_unavailable():
    with pytest.raises(EnclosureUnavailable, match="domain"):
        strict.strict_vondrak_precession_matrix(2451545.0 + 2001 * 36525.0)

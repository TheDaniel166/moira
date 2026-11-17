"""Conditional FW phase residual exclusion, including wrap/degenerate cases."""
from fractions import Fraction
import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from moira import _eclipse_phase_exclusion as phase
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira.constants import Body
from moira.planets import planet_at


def _synthetic_vectors(monkeypatch, sun, moon):
    zero = I.point(0)
    sun_box = tuple(I.point(value) for value in sun)
    moon_box = tuple(I.point(value) for value in moon)
    data = SimpleNamespace(sun_retarded_km=sun_box, moon_retarded_km=moon_box,
                           earth_velocity_km_per_day=(zero, zero, zero))
    monkeypatch.setattr(phase, "bound_phase_planetary_vectors", lambda *args: data)
    monkeypatch.setattr(phase, "bound_phase_aberration", lambda vector, velocity: SimpleNamespace(position_km=vector))


@pytest.mark.parametrize("delta", [0.0, -0.0, 1e-10, -1e-10, 5e-8, -5e-8])
@pytest.mark.parametrize("opposite", [False, True])
def test_wrap_and_near_threshold_do_not_claim_exclusion(monkeypatch, delta, opposite):
    _synthetic_vectors(monkeypatch, (1.0, 0.0, 0.0), (-1.0 if opposite else 1.0, delta, 0.0))
    result = phase.bound_fw_phase_zero_exclusion(None, 2451545.0, I.point(0))
    assert result.status == "unresolved"
    assert result.new_residual_sign is None
    assert result.full_residual_sign is None
    assert not result.execution_environment_attested
    assert not result.complete_search_certified


@pytest.mark.parametrize("sign", [-1.0, 1.0])
@pytest.mark.parametrize("opposite", [False, True])
def test_separated_wrap_and_full_branches_can_be_excluded_conditionally(monkeypatch, sign, opposite):
    _synthetic_vectors(monkeypatch, (1.0, 0.0, 0.0), (-1.0 if opposite else 1.0, sign * 1e-4, 0.0))
    result = phase.bound_fw_phase_zero_exclusion(None, 2451545.0, I.point(0))
    assert result.status == "excluded"
    assert result.full_residual_sign == (-int(sign) if opposite else None)
    assert result.new_residual_sign == (None if opposite else int(sign))
    assert not result.source_and_kernel_attested
    assert not result.ut1_enclosed


def test_degenerate_projection_is_unavailable(monkeypatch):
    # Mean ecliptic pole direction has an effectively zero XY projection.
    pole = phase.bound_fw_mean_ecliptic_pole(2451545.0, I.point(0))
    direction = tuple(10.0 * float(component.midpoint) for component in pole.pole)
    _synthetic_vectors(monkeypatch, (1.0, 0.0, 0.0), direction)
    with pytest.raises(EnclosureUnavailable, match="degenerate"):
        phase.bound_fw_phase_zero_exclusion(None, 2451545.0, I.point(0))


def test_reference_determinant_does_not_assume_an_orthogonal_matrix(monkeypatch):
    receipt = phase.bound_fw_mean_ecliptic_pole(2451545.0, I.point(0))
    zero, one, two = I.point(0), I.point(1), I.point(2)
    matrix = ((two, zero, zero), (zero, one, zero), (zero, zero, one))
    altered = replace(receipt, mean_matrix=matrix, pole=(zero, zero, one))
    monkeypatch.setattr(phase, "bound_fw_mean_ecliptic_pole", lambda *args: altered)
    _synthetic_vectors(monkeypatch, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    result = phase.bound_fw_phase_zero_exclusion(None, 2451545.0, I.point(0))
    assert result.cross_km2.contains(2)
    assert not result.cross_km2.contains(1)
    assert result.new_residual_sign is None and result.full_residual_sign is None


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026289.7107341307, 2459895.9582497696, 2688460.25])
def test_de441_actual_phase_samples_away_from_the_excluded_region(planetary_reader, tt):
    # This is sampling evidence for the conditional enclosure, not its proof.
    result = phase.bound_fw_phase_zero_exclusion(planetary_reader, tt, I(Fraction(-5, 86400), Fraction(5, 86400)))
    assert result.status == "excluded"
    # Supply the exact same TT to both real public reduction calls. These
    # point samples are evidence for the conditional interval, not its proof.
    for seconds in (-2, 0, 2):
        epoch = tt + seconds / 86400
        sun = planet_at(Body.SUN, tt, reader=planetary_reader, jd_tt=epoch).longitude
        moon = planet_at(Body.MOON, tt, reader=planetary_reader, jd_tt=epoch).longitude
        angle = (moon - sun) % 360.0
        assert math.isfinite(angle)
        assert min(abs(angle), abs(angle - 180), abs(angle - 360)) > 0.01
        new_residual = (angle + 180.0) % 360.0 - 180.0
        full_residual = (angle - 180.0 + 180.0) % 360.0 - 180.0
        if result.new_residual_sign is not None:
            assert new_residual != 0.0
            assert math.copysign(1, new_residual) == result.new_residual_sign
        if result.full_residual_sign is not None:
            assert full_residual != 0.0
            assert math.copysign(1, full_residual) == result.full_residual_sign

"""Conditional UT clock and represented phase-sign composition."""
from fractions import Fraction
import math
from types import SimpleNamespace

import pytest

from moira import _eclipse_phase_ut as phase_ut
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.phenomena import _sun_moon_phase_angle


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("ut", [1026289.7107341307, 2459895.9582497696, 2688460.25])
def test_conditional_ut_phase_signs_match_actual_represented_samples(planetary_reader, ut):
    result = phase_ut.bound_conditional_ut_phase_signs(
        planetary_reader, ut, I(Fraction(-5, 86400), Fraction(5, 86400)),
    )
    assert not result.source_and_arithmetic_attested
    assert not result.continuous_root_proved
    assert not result.complete_search_certified
    assert not result.phase.source_and_kernel_attested
    assert result.same_reader_clock_data_and_context_required
    for seconds in (-2, 0, 2):
        epoch = ut + seconds / 86400
        tt = _ut1_to_ephemeris_tt(epoch, planetary_reader)
        relative_tt = Fraction.from_float(tt) - Fraction.from_float(ut)
        assert result.clock.bounds.output_offset_days.contains(relative_tt)
        angle = _sun_moon_phase_angle(epoch, planetary_reader)
        new = (angle + 180.0) % 360.0 - 180.0
        full = (angle - 180.0 + 180.0) % 360.0 - 180.0
        if result.phase.new_residual_sign is not None:
            assert new != 0.0
            assert math.copysign(1, new) == result.phase.new_residual_sign
        if result.phase.full_residual_sign is not None:
            assert full != 0.0
            assert math.copysign(1, full) == result.phase.full_residual_sign
    assert result.phase.new_residual_sign is not None or result.phase.full_residual_sign is not None


def test_unavailable_clock_cannot_be_interpreted_as_phase_absence(monkeypatch):
    def unavailable(*args, **kwargs):
        raise EnclosureUnavailable("clock handoff")

    monkeypatch.setattr(phase_ut, "bound_native_ut1_to_tt", unavailable)
    with pytest.raises(EnclosureUnavailable, match="clock handoff"):
        phase_ut.bound_conditional_ut_phase_signs(None, 2451545.0, I.point(0))


def test_phase_branch_or_record_seam_remains_unavailable(monkeypatch):
    clock = SimpleNamespace(bounds=SimpleNamespace(output_offset_days=I.point(0)))
    monkeypatch.setattr(phase_ut, "bound_native_ut1_to_tt", lambda *args, **kwargs: clock)

    def unavailable(*args):
        raise EnclosureUnavailable("FW/Vondrak branch seam")

    monkeypatch.setattr(phase_ut, "bound_fw_phase_zero_exclusion", unavailable)
    with pytest.raises(EnclosureUnavailable, match="branch seam"):
        phase_ut.bound_conditional_ut_phase_signs(None, 2451545.0, I.point(0))

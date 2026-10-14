from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from moira.constants import Body
from moira.void_of_course import (
    VOID_OF_COURSE_DEFAULT_NEXT_HORIZON_DAYS,
    next_void_of_course,
    next_void_of_course_with_truth,
    void_of_course_state_with_truth,
    void_of_course_window,
    void_of_course_window_with_truth,
    void_periods_in_range,
    void_periods_in_range_with_truth,
)


pytestmark = pytest.mark.requires_ephemeris


class TestR3DVoidOfCourseTruthEvidence:
    """Bounded DE441 and invariant evidence for the R3D VOC contract."""

    @staticmethod
    def _reader(moira_engine):
        return getattr(moira_engine, "_reader", None)

    def test_truth_window_preserves_legacy_result(self, moira_engine) -> None:
        reader = self._reader(moira_engine)
        legacy = void_of_course_window(2451545.0, reader=reader)
        result = void_of_course_window_with_truth(2451545.0, reader=reader)

        assert result.window == legacy
        assert result.truth.request_kind == "current_sign_window"
        assert result.truth.sign_entry_jd_ut1 < 2451545.0
        assert result.truth.sign_exit_jd_ut1 == legacy.jd_voc_end

    def test_de441_j2000_window_regression(self, moira_engine) -> None:
        result = void_of_course_window_with_truth(
            2451545.0,
            reader=self._reader(moira_engine),
        )

        assert result.window.moon_sign == "Scorpio"
        assert result.window.moon_sign_next == "Sagittarius"
        assert result.window.jd_voc_start == pytest.approx(2451546.3111614613, abs=2.0e-6)
        assert result.window.jd_voc_end == pytest.approx(2451546.397037506, abs=2.0e-6)
        assert result.window.last_aspect is not None
        assert result.window.last_aspect.body == Body.MARS
        assert result.window.last_aspect.aspect_name == "Square"
        assert result.window.last_aspect.angle == 270.0
        assert result.truth.reduction_at_request.planetary_ephemeris == "DE441"
        assert result.truth.reduction_at_request.lunar_ephemeris == "LE441"

    def test_last_aspect_witness_has_small_signed_residual(self, moira_engine) -> None:
        result = void_of_course_window_with_truth(
            2451545.0,
            reader=self._reader(moira_engine),
        )
        witness = result.truth.last_aspect_witness

        assert witness is not None
        assert witness.jd_exact_ut1 == result.window.jd_voc_start
        assert abs(witness.signed_target_residual_deg) < 2.0e-4
        assert result.truth.aspect_perfection_count == 4

    def test_traditional_policy_is_explicit(self, moira_engine) -> None:
        truth = void_of_course_window_with_truth(
            2451545.0,
            reader=self._reader(moira_engine),
        ).truth

        assert truth.policy.effective_mode == "traditional"
        assert truth.policy.aspect_bodies == (
            Body.SUN,
            Body.MERCURY,
            Body.VENUS,
            Body.MARS,
            Body.JUPITER,
            Body.SATURN,
        )
        assert truth.policy.exactness_rule == "exact_perfection_not_orb_entry"
        assert truth.policy.voc_end_rule == "next_tropical_sign_ingress"

    def test_modern_policy_adds_only_outer_planets(self, moira_engine) -> None:
        truth = void_of_course_window_with_truth(
            2451545.0,
            reader=self._reader(moira_engine),
            modern=True,
        ).truth

        assert truth.policy.requested_modern
        assert truth.policy.effective_mode == "modern"
        assert truth.policy.aspect_bodies[-3:] == (
            Body.URANUS,
            Body.NEPTUNE,
            Body.PLUTO,
        )
        assert len(truth.policy.aspect_bodies) == 9

    def test_reduction_truth_names_clock_frame_and_corrections(self, moira_engine) -> None:
        truth = void_of_course_window_with_truth(
            2451545.0,
            reader=self._reader(moira_engine),
        ).truth.reduction_at_request

        assert truth.jd_ut1 < truth.jd_tt
        assert truth.jd_tt != truth.jd_tdb
        assert truth.observer_center == "geocenter"
        assert truth.source_vector_frame == "ICRF_barycentric"
        assert truth.result_frame == "true_ecliptic_and_equinox_of_date"
        assert truth.zodiac == "tropical"
        assert truth.position_mode == "apparent"
        assert truth.light_time_applied
        assert truth.annual_aberration_applied
        assert truth.gravitational_deflection_applied
        assert truth.precession_applied
        assert truth.nutation_applied
        assert not truth.topocentric_applied

    def test_state_truth_uses_inclusive_window_bounds(self, moira_engine) -> None:
        reader = self._reader(moira_engine)
        window = void_of_course_window(2451545.0, reader=reader)
        before = void_of_course_state_with_truth(2451545.0, reader=reader)
        active = void_of_course_state_with_truth(
            (window.jd_voc_start + window.jd_voc_end) / 2.0,
            reader=reader,
        )

        assert not before.is_void_of_course
        assert active.is_void_of_course
        assert active.truth.policy.active_state_rule == (
            "jd_voc_start_inclusive_through_jd_voc_end_inclusive"
        )

    def test_next_truth_preserves_legacy_result_and_horizon(self, moira_engine) -> None:
        reader = self._reader(moira_engine)
        legacy = next_void_of_course(2451545.0, reader=reader)
        result = next_void_of_course_with_truth(2451545.0, reader=reader)

        assert result is not None
        assert result.window == legacy
        assert result.truth.request_kind == "next_strictly_future_window"
        assert result.truth.search_end_jd_ut1 == (
            2451545.0 + VOID_OF_COURSE_DEFAULT_NEXT_HORIZON_DAYS
        )

    def test_range_truth_preserves_legacy_order_and_count(self, moira_engine) -> None:
        reader = self._reader(moira_engine)
        legacy = void_periods_in_range(2451545.0, 2451550.0, reader=reader)
        result = void_periods_in_range_with_truth(
            2451545.0,
            2451550.0,
            reader=reader,
        )

        assert [item.window for item in result.windows] == legacy
        assert result.truth.result_count == len(legacy) == 2
        assert result.truth.source_identity_at_search_start.planetary_ephemeris == "DE441"
        assert all(item.truth.request_kind == "range_member" for item in result.windows)

    def test_truth_vessels_are_immutable(self, moira_engine) -> None:
        truth = void_of_course_window_with_truth(
            2451545.0,
            reader=self._reader(moira_engine),
        ).truth

        with pytest.raises(FrozenInstanceError):
            truth.request_kind = "changed"

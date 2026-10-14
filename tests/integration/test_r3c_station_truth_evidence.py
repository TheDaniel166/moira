from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from moira.planets import PLANET_LONGITUDE_RATE_SAMPLE_HALF_SPAN_DAYS, planet_at
from moira.stations import (
    STATION_REFINEMENT_TOLERANCE_DAYS,
    STATION_SPEED_THRESHOLD_DEG_PER_DAY,
    find_stations,
    find_stations_with_truth,
    next_station,
    next_station_with_truth,
    station_state_with_truth,
)


pytestmark = pytest.mark.requires_ephemeris


class TestR3CStationTruthEvidence:
    """Bounded DE441 and invariant evidence for the R3C station contract."""

    @staticmethod
    def _reader(moira_engine):
        return getattr(moira_engine, "_reader", None)

    def test_truth_search_preserves_legacy_events(self, moira_engine) -> None:
        reader = self._reader(moira_engine)
        legacy = find_stations(
            "Mercury", 2451545.0, 2451545.0 + 365.25, reader=reader
        )
        result = find_stations_with_truth(
            "Mercury", 2451545.0, 2451545.0 + 365.25, reader=reader
        )

        assert [item.event for item in result.events] == legacy
        assert result.truth.result_count == len(legacy) == 6
        assert result.truth.no_result_reason is None

    def test_de441_mercury_station_regression(self, moira_engine) -> None:
        result = find_stations_with_truth(
            "Mercury",
            2451545.0,
            2451545.0 + 365.25,
            reader=self._reader(moira_engine),
        )
        first = result.events[0]

        assert first.event.station_type == "retrograde"
        assert first.event.jd_ut == pytest.approx(2451596.032222748, abs=2.0e-6)
        assert first.event.longitude == pytest.approx(347.1784, abs=1.0e-4)
        assert first.truth.reduction.planetary_ephemeris == "DE441"
        assert first.truth.reduction.lunar_ephemeris == "LE441"

    def test_event_truth_carries_a_real_signed_speed_bracket(self, moira_engine) -> None:
        result = find_stations_with_truth(
            "Mercury", 2451545.0, 2451600.0, reader=self._reader(moira_engine)
        )
        event = result.events[0]
        truth = event.truth

        assert truth.coarse_bracket_start_jd_ut < event.event.jd_ut
        assert event.event.jd_ut < truth.coarse_bracket_end_jd_ut
        assert (
            truth.speed_at_bracket_start_deg_per_day
            * truth.speed_at_bracket_end_deg_per_day
            < 0.0
        )
        assert abs(truth.signed_speed_at_station_deg_per_day) < 1.0e-6
        assert truth.station_speed_threshold_deg_per_day == 0.0

    def test_search_truth_names_the_effective_policy(self, moira_engine) -> None:
        result = find_stations_with_truth(
            "Venus",
            2451545.0,
            2451745.0,
            step_days=1.25,
            reader=self._reader(moira_engine),
        )
        truth = result.truth

        assert truth.requested_step_days == 1.25
        assert truth.effective_step_days == 1.25
        assert truth.search_timescale == "UT1"
        assert truth.station_detection_rule == "strict_signed_speed_sign_change"
        assert truth.refinement_tolerance_days == STATION_REFINEMENT_TOLERANCE_DAYS
        assert truth.station_speed_threshold_deg_per_day == STATION_SPEED_THRESHOLD_DEG_PER_DAY

    def test_reduction_truth_names_frame_corrections_clock_and_rate(self, moira_engine) -> None:
        result = find_stations_with_truth(
            "Mercury", 2451545.0, 2451600.0, reader=self._reader(moira_engine)
        )
        truth = result.events[0].truth.reduction

        assert truth.observer_center == "geocenter"
        assert truth.body_family == "major_planet"
        assert truth.ephemeris_identity_scope == "serving_de_le_model_identity"
        assert truth.source_vector_frame == "ICRF_barycentric"
        assert truth.result_frame == "true_ecliptic_and_equinox_of_date"
        assert truth.position_mode == "apparent"
        assert truth.light_time_applied
        assert truth.annual_aberration_applied
        assert truth.gravitational_deflection_applied
        assert truth.precession_applied
        assert truth.nutation_applied
        assert not truth.topocentric_applied
        assert truth.speed_method == "centered_circular_finite_difference"
        assert truth.speed_sample_timescale == "TT"
        assert (
            truth.speed_sample_half_span_days
            == PLANET_LONGITUDE_RATE_SAMPLE_HALF_SPAN_DAYS
        )
        assert truth.jd_ut1 < truth.jd_tt
        assert truth.jd_tt != truth.jd_tdb

    def test_state_truth_is_the_planet_speed_witness(self, moira_engine) -> None:
        reader = self._reader(moira_engine)
        state = station_state_with_truth("Mercury", 2451545.0, reader=reader)
        position = planet_at("Mercury", 2451545.0, reader=reader)

        assert state.truth.signed_longitude_speed_deg_per_day == position.speed
        assert state.is_retrograde is (position.speed < 0.0)
        assert state.truth.retrograde_rule == (
            "signed_longitude_speed_deg_per_day_below_zero"
        )

    def test_next_truth_preserves_legacy_result(self, moira_engine) -> None:
        reader = self._reader(moira_engine)
        legacy = next_station("Mercury", 2451545.0, reader=reader)
        result = next_station_with_truth("Mercury", 2451545.0, reader=reader)

        assert result.event is not None
        assert result.event.event == legacy
        assert result.search_truth.search_end_jd_ut == 2451945.0

    def test_non_retrograding_body_has_explicit_no_result_without_reader(self) -> None:
        search = find_stations_with_truth("Sun", 2451545.0, 2451645.0)
        state = station_state_with_truth("Sun", 2451545.0)

        assert search.events == ()
        assert search.truth.no_result_reason == "body_has_no_retrograde_motion"
        assert search.truth.source_identity_at_search_start is None
        assert not state.is_retrograde
        assert state.truth.signed_longitude_speed_deg_per_day == 0.0
        assert state.truth.state_reason == "body_has_no_retrograde_motion"

    def test_empty_planet_search_distinguishes_window_absence(self, moira_engine) -> None:
        search = find_stations_with_truth(
            "Mercury", 2451545.0, 2451546.0, reader=self._reader(moira_engine)
        )

        assert search.events == ()
        assert search.truth.no_result_reason == "no_station_in_search_window"
        assert search.truth.source_identity_at_search_start is not None
        assert (
            search.truth.source_identity_at_search_start.planetary_ephemeris
            == "DE441"
        )

    def test_station_event_is_immutable_as_declared(self, moira_engine) -> None:
        event = find_stations_with_truth(
            "Mercury", 2451545.0, 2451600.0, reader=self._reader(moira_engine)
        ).events[0].event

        with pytest.raises(FrozenInstanceError):
            event.jd_ut = 0.0

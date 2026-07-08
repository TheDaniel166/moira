"""
Unit tests for moira.sade_sati.

Coverage
--------
1. sade_sati_status — house counting, phase mapping, Ashtama/Kantaka flags.
2. Vessel invariants — frozen, slots, validation.
3. sade_sati_windows — kernel-backed scan: window chronology, phase
   correctness against instantaneous status, ingress/egress marking,
   retrograde re-entry honesty (requires_ephemeris).

Source authority: standard Jyotish transit doctrine (Sade Sati phases from
the janma rashi); timing derived from kernel ephemerides.
"""
import pytest

from moira.sade_sati import (
    SADE_SATI_PHASES,
    SadeSatiStatus,
    SadeSatiWindow,
    sade_sati_status,
    sade_sati_windows,
)

_J2000 = 2451545.0


class TestSadeSatiStatus:

    def test_phase_mapping_constants(self) -> None:
        assert SADE_SATI_PHASES == {12: "rising", 1: "peak", 2: "setting"}

    def test_twelfth_house_is_rising(self) -> None:
        s = sade_sati_status(35.0, 5.0)   # Moon Taurus, Saturn Aries
        assert s.house_from_moon == 12
        assert s.phase == "rising"
        assert s.in_sade_sati is True

    def test_same_sign_is_peak(self) -> None:
        s = sade_sati_status(35.0, 40.0)
        assert s.house_from_moon == 1
        assert s.phase == "peak"

    def test_second_house_is_setting(self) -> None:
        s = sade_sati_status(35.0, 70.0)
        assert s.phase == "setting"

    def test_outside_sade_sati_has_no_phase(self) -> None:
        s = sade_sati_status(35.0, 35.0 + 150.0)   # 6th house
        assert s.in_sade_sati is False
        assert s.phase is None

    def test_eighth_house_is_ashtama_shani(self) -> None:
        s = sade_sati_status(35.0, 35.0 + 210.0)
        assert s.is_ashtama_shani is True
        assert s.in_sade_sati is False

    def test_fourth_house_is_kantaka_shani(self) -> None:
        s = sade_sati_status(35.0, 35.0 + 90.0)
        assert s.is_kantaka_shani is True

    def test_all_twelve_houses_consistent(self) -> None:
        for house in range(1, 13):
            s = sade_sati_status(15.0, 15.0 + (house - 1) * 30.0)
            assert s.house_from_moon == house
            assert s.in_sade_sati is (house in (12, 1, 2))
            assert s.is_ashtama_shani is (house == 8)
            assert s.is_kantaka_shani is (house == 4)

    def test_status_vessel_is_frozen(self) -> None:
        s = sade_sati_status(35.0, 5.0)
        with pytest.raises((AttributeError, TypeError)):
            s.phase = "peak"  # type: ignore[misc]

    def test_window_requires_ordered_bounds(self) -> None:
        with pytest.raises(ValueError, match="start_jd"):
            SadeSatiWindow(
                phase="peak", sign_index=1,
                start_jd=100.0, end_jd=100.0,
                start_is_ingress=True, end_is_egress=True,
            )

    def test_window_rejects_unknown_phase(self) -> None:
        with pytest.raises(ValueError, match="phase"):
            SadeSatiWindow(
                phase="zenith", sign_index=1,
                start_jd=100.0, end_jd=200.0,
                start_is_ingress=True, end_is_egress=True,
            )


@pytest.mark.requires_ephemeris
class TestSadeSatiWindows:

    @pytest.fixture(scope="class")
    def result(self, moira_engine):
        from moira.facade import use_reader_override
        with use_reader_override(moira_engine._reader_obj):
            return sade_sati_windows(35.0, _J2000, _J2000 + 12 * 365.25)

    def test_windows_are_chronological_and_non_overlapping(self, result) -> None:
        windows = result.windows
        assert windows, "expected Sade Sati windows for a Taurus Moon around J2000"
        for a, b in zip(windows, windows[1:]):
            assert a.end_jd <= b.start_jd + 1e-6

    def test_every_window_sign_matches_its_phase(self, result) -> None:
        for w in result.windows:
            house = (w.sign_index - result.janma_rashi_index) % 12 + 1
            assert SADE_SATI_PHASES[house] == w.phase

    def test_window_interiors_agree_with_instantaneous_status(
        self, result, moira_engine
    ) -> None:
        from moira.facade import use_reader_override
        from moira.planets import planet_at
        from moira.sidereal import tropical_to_sidereal

        with use_reader_override(moira_engine._reader_obj):
            for w in result.windows:
                mid = 0.5 * (w.start_jd + w.end_jd)
                lon = tropical_to_sidereal(
                    planet_at("Saturn", mid).longitude, mid,
                    system=result.ayanamsa_system,
                )
                s = sade_sati_status(35.0, lon)
                assert s.phase == w.phase, (w, mid)

    def test_range_clamps_are_marked(self, result) -> None:
        first = result.windows[0]
        # J2000 starts mid-phase for a Taurus Moon (Saturn in Aries).
        assert first.start_jd == pytest.approx(result.start_jd)
        assert first.start_is_ingress is False

    def test_invalid_range_raises(self) -> None:
        with pytest.raises(ValueError, match="start_jd"):
            sade_sati_windows(35.0, _J2000, _J2000)

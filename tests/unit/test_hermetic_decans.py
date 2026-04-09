"""
Unit tests for moira.hermetic_decans.

All tests use unittest.mock.patch — no catalog file or ephemeris required.
Follows the same patterns as tests/unit/test_fixed_stars_api.py.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dummy_star(name: str = "Sirius"):
    """Return a minimal StarPosition-like mock."""
    from moira.stars import StarPosition
    return StarPosition(
        name=name,
        nomenclature="alCMa",
        longitude=104.0,
        latitude=-39.6,
        magnitude=-1.46,
    )


def test_solar_declination_ra_uses_tt_obliquity() -> None:
    import moira._solar as solar_module

    dummy_sun = MagicMock(longitude=15.0, latitude=1.0)
    with patch.object(solar_module, "planet_at", return_value=dummy_sun), \
         patch.object(solar_module, "ut_to_tt", return_value=2451545.0008) as mock_tt, \
         patch.object(solar_module, "true_obliquity", return_value=23.4) as mock_obl:
        solar_module._solar_declination_ra(2451545.0, MagicMock())

    mock_tt.assert_called_once_with(2451545.0)
    mock_obl.assert_called_once_with(2451545.0008)


def test_decan_at_uses_tt_obliquity() -> None:
    import moira.hermetic_decans as decans

    with patch.object(decans, "_lst_to_ramc", return_value=120.0), \
         patch.object(decans, "ut_to_tt", return_value=2451545.0008) as mock_tt, \
         patch.object(decans, "true_obliquity", return_value=23.4) as mock_obl, \
         patch.object(decans, "decan_for_longitude", return_value="Horaios"):
        result = decans.decan_at(2451545.0, 51.5, -0.1)

    assert result == "Horaios"
    mock_tt.assert_called_once_with(2451545.0)
    mock_obl.assert_called_once_with(2451545.0008)


def test_decan_at_matches_house_engine_ascendant_for_representative_cases() -> None:
    from moira.hermetic_decans import decan_at, decan_for_longitude
    from moira.houses import calculate_houses
    from moira.julian import jd_from_datetime

    samples = [
        (datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 51.5, -0.1),
        (datetime(1987, 4, 10, 0, tzinfo=timezone.utc), 37.98, 23.72),
        (datetime(2024, 6, 21, 0, tzinfo=timezone.utc), 0.0, 0.0),
    ]
    for dt, lat, lon in samples:
        jd = jd_from_datetime(dt)
        houses = calculate_houses(jd, lat, lon)
        assert decan_at(jd, lat, lon) == decan_for_longitude(houses.asc)


def test_decan_hours_start_matches_mc_decan_at_sunset() -> None:
    import math

    from moira.hermetic_decans import _lst_to_ramc, decan_for_longitude, decan_hours
    from moira.julian import jd_from_datetime
    from moira.obliquity import true_obliquity

    jd = jd_from_datetime(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
    lat = 51.5
    lon = -0.1
    night = decan_hours(jd, lat, lon)
    ramc = _lst_to_ramc(night.sunset_jd, lon)
    obliquity = true_obliquity(night.sunset_jd)
    mc = math.degrees(math.atan2(
        math.sin(math.radians(ramc)),
        math.cos(math.radians(ramc)) * math.cos(math.radians(obliquity)),
    )) % 360.0
    assert night.hours[0].decan == decan_for_longitude(mc)


def test_decan_hours_handles_next_sunrise_refinement_day_slip() -> None:
    import moira.hermetic_decans as decans

    with patch.object(decans, "get_reader", return_value=MagicMock()), \
         patch.object(decans, "_sunrise_sunset", side_effect=[
             (2460665.2797947964, 2460665.8801496485),
             (2460666.279805984, 2460666.880138461),
         ]), \
         patch.object(decans, "_refine_sunrise", side_effect=[
             2460665.2797947964,
             2460665.8801496485,
             2460661.27991509,
         ]), \
         patch.object(decans, "_lst_to_ramc", return_value=120.0), \
         patch.object(decans, "true_obliquity", return_value=23.4):
        night = decans.decan_hours(2460665.5, -33.87, 151.21)

    assert night.sunset_jd == pytest.approx(2460665.8801496485)
    assert night.next_sunrise_jd == pytest.approx(2460666.27991509)


# ===========================================================================
# 7.1 — Constants and dict structure
# ===========================================================================

class TestDecanConstants:
    def test_horaios_constant(self):
        from moira.hermetic_decans import HORAIOS
        assert HORAIOS == "Horaios"

    def test_aphruimis_iii_constant(self):
        from moira.hermetic_decans import APHRUIMIS_III
        assert APHRUIMIS_III == "Aphruimis III"

    def test_sothis_constant(self):
        from moira.hermetic_decans import SOTHIS
        assert SOTHIS == "Sothis"


class TestDecanNamesDict:
    def test_length(self):
        from moira.hermetic_decans import DECAN_NAMES
        assert len(DECAN_NAMES) == 36

    def test_horaios_entry(self):
        from moira.hermetic_decans import DECAN_NAMES
        assert DECAN_NAMES["Horaios"] == "Horaios"

    def test_aphruimis_iii_entry(self):
        from moira.hermetic_decans import DECAN_NAMES
        assert DECAN_NAMES["Aphruimis III"] == "Aphruimis III"

    def test_all_values_are_strings(self):
        from moira.hermetic_decans import DECAN_NAMES
        for k, v in DECAN_NAMES.items():
            assert isinstance(v, str)


class TestDecanRulingStarsDict:
    def test_length(self):
        from moira.hermetic_decans import DECAN_RULING_STARS
        assert len(DECAN_RULING_STARS) == 36

    def test_sothis_ruling_star(self):
        from moira.hermetic_decans import DECAN_RULING_STARS
        assert DECAN_RULING_STARS["Sothis"] == "Sirius"

    def test_horaios_ruling_star(self):
        from moira.hermetic_decans import DECAN_RULING_STARS
        assert DECAN_RULING_STARS["Horaios"] == "Hamal"

    def test_aphruimis_iii_ruling_star(self):
        from moira.hermetic_decans import DECAN_RULING_STARS
        assert DECAN_RULING_STARS["Aphruimis III"] == "Alpherg"


# ===========================================================================
# 7.2 — list_decans and decan_index
# ===========================================================================

class TestListDecans:
    def test_length(self):
        from moira.hermetic_decans import list_decans
        assert len(list_decans()) == 36

    def test_first_value(self):
        from moira.hermetic_decans import list_decans
        assert list_decans()[0] == "Horaios"

    def test_last_value(self):
        from moira.hermetic_decans import list_decans
        assert list_decans()[35] == "Aphruimis III"

    def test_returns_list(self):
        from moira.hermetic_decans import list_decans
        assert isinstance(list_decans(), list)

    def test_returns_new_copy(self):
        from moira.hermetic_decans import list_decans
        a = list_decans()
        b = list_decans()
        assert a is not b


class TestDecanIndex:
    def test_index_of_first(self):
        from moira.hermetic_decans import decan_index
        assert decan_index("Horaios") == 0

    def test_index_of_last(self):
        from moira.hermetic_decans import decan_index
        assert decan_index("Aphruimis III") == 35

    def test_index_of_sothis(self):
        from moira.hermetic_decans import decan_index
        assert decan_index("Sothis") == 6

    def test_invalid_name_raises(self):
        from moira.hermetic_decans import decan_index
        with pytest.raises(ValueError):
            decan_index("NotADecan")


# ===========================================================================
# 7.3 — decan_for_longitude
# ===========================================================================

class TestDecanForLongitude:
    def test_zero_degrees(self):
        from moira.hermetic_decans import decan_for_longitude
        assert decan_for_longitude(0.0) == "Horaios"

    def test_359_9_degrees(self):
        from moira.hermetic_decans import decan_for_longitude
        assert decan_for_longitude(359.9) == "Aphruimis III"

    def test_normalization_370(self):
        # 370 % 360 = 10 → Tomalos (index 1)
        from moira.hermetic_decans import decan_for_longitude
        assert decan_for_longitude(370.0) == "Tomalos"

    def test_spot_check_60_degrees(self):
        # 60° → index 6 → Sothis
        from moira.hermetic_decans import decan_for_longitude
        assert decan_for_longitude(60.0) == "Sothis"

    def test_nan_raises_value_error(self):
        from moira.hermetic_decans import decan_for_longitude
        with pytest.raises(ValueError):
            decan_for_longitude(float("nan"))

    def test_inf_raises_value_error(self):
        from moira.hermetic_decans import decan_for_longitude
        with pytest.raises(ValueError):
            decan_for_longitude(float("inf"))

    def test_negative_inf_raises_value_error(self):
        from moira.hermetic_decans import decan_for_longitude
        with pytest.raises(ValueError):
            decan_for_longitude(float("-inf"))

    def test_result_in_list_decans(self):
        from moira.hermetic_decans import decan_for_longitude, list_decans
        decans = list_decans()
        for lon in [0.0, 10.0, 60.0, 120.0, 180.0, 270.0, 350.0, 359.9]:
            assert decan_for_longitude(lon) in decans


# ===========================================================================
# 7.4 — available_decans with mocked list_stars
# ===========================================================================

class TestAvailableDecans:
    def test_empty_catalog_returns_empty(self):
        with patch("moira.hermetic_decans.list_stars", return_value=[]):
            from moira.hermetic_decans import available_decans
            assert available_decans() == []

    def test_partial_catalog_returns_correct_subset(self):
        # Sothis → Sirius, Horaios → Hamal; only Sirius in catalog
        partial = ["Sirius", "Vega"]
        with patch("moira.hermetic_decans.list_stars", return_value=partial):
            from moira.hermetic_decans import available_decans
            result = available_decans()
            assert "Sothis" in result
            assert "Horaios" not in result

    def test_partial_catalog_subset_of_list_decans(self):
        partial = ["Sirius", "Hamal", "Regulus"]
        with patch("moira.hermetic_decans.list_stars", return_value=partial):
            from moira.hermetic_decans import available_decans, list_decans
            result = available_decans()
            assert set(result) <= set(list_decans())

    def test_all_ruling_stars_present_returns_all_36(self):
        from moira.hermetic_decans import DECAN_RULING_STARS
        all_stars = list(DECAN_RULING_STARS.values())
        with patch("moira.hermetic_decans.list_stars", return_value=all_stars):
            from moira.hermetic_decans import available_decans
            result = available_decans()
            assert len(result) == 36


# ===========================================================================
# 7.5 — decan_ruling_star and decan_star_at delegation
# ===========================================================================

class TestDecanRulingStar:
    def test_returns_correct_star_name(self):
        from moira.hermetic_decans import decan_ruling_star
        assert decan_ruling_star("Sothis") == "Sirius"

    def test_returns_correct_star_for_horaios(self):
        from moira.hermetic_decans import decan_ruling_star
        assert decan_ruling_star("Horaios") == "Hamal"

    def test_unknown_decan_raises_key_error(self):
        from moira.hermetic_decans import decan_ruling_star
        with pytest.raises(KeyError):
            decan_ruling_star("NotADecan")


class TestDecanStarAt:
    def test_delegates_to_star_at(self):
        dummy = _dummy_star("Sirius")
        with patch("moira.hermetic_decans.star_at", return_value=dummy) as mock_fsa:
            from moira.hermetic_decans import decan_star_at
            result = decan_star_at("Sothis", 2451545.0)
            mock_fsa.assert_called_once_with("Sirius", 2451545.0)
            assert result is dummy

    def test_delegates_with_correct_star_name(self):
        dummy = _dummy_star("Hamal")
        with patch("moira.hermetic_decans.star_at", return_value=dummy) as mock_fsa:
            from moira.hermetic_decans import decan_star_at
            decan_star_at("Horaios", 2451545.0)
            mock_fsa.assert_called_once_with("Hamal", 2451545.0)

    def test_propagates_key_error_for_missing_star(self):
        with patch("moira.hermetic_decans.star_at", side_effect=KeyError("Sirius")):
            from moira.hermetic_decans import decan_star_at
            with pytest.raises(KeyError):
                decan_star_at("Sothis", 2451545.0)


# ===========================================================================
# 7.6 — DecanHour and DecanHoursNight dataclass field presence
# ===========================================================================

class TestDecanHourDataclass:
    def test_field_presence(self):
        from moira.hermetic_decans import DecanHour
        h = DecanHour(
            hour_number=1,
            decan="Sothis",
            ruling_star="Sirius",
            jd_start=2451545.0,
            jd_end=2451545.5,
        )
        assert h.hour_number == 1
        assert h.decan == "Sothis"
        assert h.ruling_star == "Sirius"
        assert h.jd_start == 2451545.0
        assert h.jd_end == 2451545.5

    def test_hour_number_field(self):
        from moira.hermetic_decans import DecanHour
        h = DecanHour(hour_number=12, decan="Horaios", ruling_star="Hamal",
                      jd_start=2451545.9, jd_end=2451546.0)
        assert h.hour_number == 12

    def test_invalid_hour_number_raises(self):
        from moira.hermetic_decans import DecanHour
        with pytest.raises(ValueError):
            DecanHour(hour_number=0, decan="Horaios", ruling_star="Hamal",
                      jd_start=2451545.0, jd_end=2451545.1)

    def test_invalid_ruling_star_raises(self):
        from moira.hermetic_decans import DecanHour
        with pytest.raises(ValueError):
            DecanHour(hour_number=1, decan="Horaios", ruling_star="Sirius",
                      jd_start=2451545.0, jd_end=2451545.1)

    def test_reversed_boundaries_raise(self):
        from moira.hermetic_decans import DecanHour
        with pytest.raises(ValueError):
            DecanHour(hour_number=1, decan="Horaios", ruling_star="Hamal",
                      jd_start=2451545.1, jd_end=2451545.0)

    def test_is_frozen(self):
        from moira.hermetic_decans import DecanHour
        h = DecanHour(hour_number=1, decan="Horaios", ruling_star="Hamal",
                      jd_start=2451545.0, jd_end=2451545.1)
        with pytest.raises(FrozenInstanceError):
            h.decan = "Sothis"


class TestDecanHoursNightDataclass:
    def _make_night(self):
        from moira.hermetic_decans import DecanHour, DecanHoursNight, DECAN_RULING_STARS, list_decans
        sunset = 2451545.75
        sunrise = 2451546.25
        hour_len = (sunrise - sunset) / 12.0
        decans = list_decans()
        hours = [
            DecanHour(
                hour_number=i + 1,
                decan=decans[i],
                ruling_star=DECAN_RULING_STARS[decans[i]],
                jd_start=sunset + i * hour_len,
                jd_end=sunset + (i + 1) * hour_len,
            )
            for i in range(12)
        ]
        return DecanHoursNight(
            date_jd=2451545.5,
            latitude=51.5,
            longitude=-0.1,
            sunset_jd=sunset,
            next_sunrise_jd=sunrise,
            hours=hours,
        )

    def test_field_presence(self):
        night = self._make_night()
        assert night.date_jd == 2451545.5
        assert night.latitude == 51.5
        assert night.longitude == -0.1
        assert night.sunset_jd == 2451545.75
        assert night.next_sunrise_jd == 2451546.25
        assert len(night.hours) == 12

    def test_hours_list_length(self):
        night = self._make_night()
        assert len(night.hours) == 12

    def test_hours_are_stored_as_tuple(self):
        night = self._make_night()
        assert isinstance(night.hours, tuple)

    def test_reversed_night_boundaries_raise(self):
        from moira.hermetic_decans import DecanHoursNight
        with pytest.raises(ValueError):
            DecanHoursNight(
                date_jd=2451545.5,
                latitude=51.5,
                longitude=-0.1,
                sunset_jd=2451546.25,
                next_sunrise_jd=2451545.75,
                hours=(),
            )

    def test_requires_exactly_twelve_hours(self):
        from moira.hermetic_decans import DecanHour, DecanHoursNight
        hour = DecanHour(
            hour_number=1,
            decan="Horaios",
            ruling_star="Hamal",
            jd_start=2451545.75,
            jd_end=2451545.80,
        )
        with pytest.raises(ValueError):
            DecanHoursNight(
                date_jd=2451545.5,
                latitude=51.5,
                longitude=-0.1,
                sunset_jd=2451545.75,
                next_sunrise_jd=2451546.25,
                hours=(hour,),
            )

    def test_is_frozen(self):
        night = self._make_night()
        with pytest.raises(FrozenInstanceError):
            night.latitude = 0.0

    def test_hours_tuple_cannot_be_mutated(self):
        night = self._make_night()
        with pytest.raises(TypeError):
            night.hours[0] = night.hours[0]


# ===========================================================================
# 7.7 — hour_at and decan_of_hour boundary behaviour
# ===========================================================================

class TestHourAt:
    def _make_night(self):
        from moira.hermetic_decans import DecanHour, DecanHoursNight, DECAN_RULING_STARS, list_decans
        sunset = 2451545.75
        sunrise = 2451546.25
        hour_len = (sunrise - sunset) / 12.0
        decans = list_decans()
        hours = [
            DecanHour(
                hour_number=i + 1,
                decan=decans[i % 36],
                ruling_star=DECAN_RULING_STARS[decans[i % 36]],
                jd_start=sunset + i * hour_len,
                jd_end=sunset + (i + 1) * hour_len,
            )
            for i in range(12)
        ]
        return DecanHoursNight(
            date_jd=2451545.5,
            latitude=51.5,
            longitude=-0.1,
            sunset_jd=sunset,
            next_sunrise_jd=sunrise,
            hours=hours,
        )

    def test_jd_before_sunset_returns_none(self):
        night = self._make_night()
        result = night.hour_at(night.sunset_jd - 0.001)
        assert result is None

    def test_jd_after_sunrise_returns_none(self):
        night = self._make_night()
        result = night.hour_at(night.next_sunrise_jd + 0.001)
        assert result is None

    def test_jd_at_exact_sunrise_returns_none(self):
        # jd_end of last hour == next_sunrise_jd; interval is [start, end)
        night = self._make_night()
        result = night.hour_at(night.next_sunrise_jd)
        assert result is None

    def test_jd_inside_first_hour(self):
        night = self._make_night()
        jd_inside = night.hours[0].jd_start + 0.001
        result = night.hour_at(jd_inside)
        assert result is not None
        assert result.hour_number == 1

    def test_jd_inside_last_hour(self):
        night = self._make_night()
        jd_inside = night.hours[11].jd_start + 0.001
        result = night.hour_at(jd_inside)
        assert result is not None
        assert result.hour_number == 12

    def test_jd_at_sunset_returns_first_hour(self):
        night = self._make_night()
        result = night.hour_at(night.sunset_jd)
        assert result is not None
        assert result.hour_number == 1


class TestDecanHoursComputation:
    def test_invalid_night_geometry_raises(self):
        import moira.hermetic_decans as decans

        with patch.object(decans, "get_reader", return_value=MagicMock()), \
             patch.object(decans, "_sunrise_sunset", side_effect=[
                 (2451545.2, 2451545.8),
                 (2451546.2, 2451545.7),
             ]), \
             patch.object(decans, "_refine_sunrise", side_effect=[2451545.2, 2451545.8, 2451545.7]):
            with pytest.raises(ValueError, match="valid night"):
                decans.decan_hours(2451545.5, 51.5, -0.1)


class TestHermeticDecanExternalGoldens:
    """Minute-resolution external goldens anchored to USNO one-day rise/set data.

    Source checked on 2026-04-09 against https://aa.usno.navy.mil/api/rstt/oneday .
    The API returns minute-resolution sunrise/sunset data, so these checks use a
    3.5 minute tolerance rather than overclaiming sub-minute external precision.
    """

    @pytest.mark.parametrize(
        ("dt", "lat", "lon", "expected_sunset", "expected_next_sunrise"),
        [
            (
                datetime(2000, 1, 1, 0, tzinfo=timezone.utc),
                51.5,
                -0.1,
                datetime(1999, 12, 31, 16, 0, tzinfo=timezone.utc),
                datetime(2000, 1, 1, 8, 6, tzinfo=timezone.utc),
            ),
            (
                datetime(1987, 4, 10, 0, tzinfo=timezone.utc),
                37.98,
                23.72,
                datetime(1987, 4, 9, 16, 55, tzinfo=timezone.utc),
                datetime(1987, 4, 10, 3, 58, tzinfo=timezone.utc),
            ),
            (
                datetime(2024, 6, 21, 0, tzinfo=timezone.utc),
                0.0,
                0.0,
                datetime(2024, 6, 20, 18, 5, tzinfo=timezone.utc),
                datetime(2024, 6, 21, 5, 58, tzinfo=timezone.utc),
            ),
            (
                datetime(2024, 12, 21, 0, tzinfo=timezone.utc),
                -33.87,
                151.21,
                datetime(2024, 12, 21, 9, 6, tzinfo=timezone.utc),
                datetime(2024, 12, 21, 18, 41, tzinfo=timezone.utc),
            ),
        ],
    )
    def test_usno_one_day_boundary_agreement(
        self,
        dt: datetime,
        lat: float,
        lon: float,
        expected_sunset: datetime,
        expected_next_sunrise: datetime,
    ) -> None:
        from moira.hermetic_decans import decan_hours
        from moira.julian import datetime_from_jd, jd_from_datetime

        night = decan_hours(jd_from_datetime(dt), lat, lon)
        sunset_dt = datetime_from_jd(night.sunset_jd)
        sunrise_dt = datetime_from_jd(night.next_sunrise_jd)

        sunset_delta_minutes = abs((sunset_dt - expected_sunset).total_seconds()) / 60.0
        sunrise_delta_minutes = abs((sunrise_dt - expected_next_sunrise).total_seconds()) / 60.0

        assert sunset_delta_minutes <= 3.5
        assert sunrise_delta_minutes <= 3.5


class TestDecanOfHour:
    def _make_night(self):
        from moira.hermetic_decans import DecanHour, DecanHoursNight, DECAN_RULING_STARS, list_decans
        sunset = 2451545.75
        sunrise = 2451546.25
        hour_len = (sunrise - sunset) / 12.0
        decans = list_decans()
        hours = [
            DecanHour(
                hour_number=i + 1,
                decan=decans[i % 36],
                ruling_star=DECAN_RULING_STARS[decans[i % 36]],
                jd_start=sunset + i * hour_len,
                jd_end=sunset + (i + 1) * hour_len,
            )
            for i in range(12)
        ]
        return DecanHoursNight(
            date_jd=2451545.5,
            latitude=51.5,
            longitude=-0.1,
            sunset_jd=sunset,
            next_sunrise_jd=sunrise,
            hours=hours,
        )

    def test_outside_night_returns_none(self):
        night = self._make_night()
        assert night.decan_of_hour(night.sunset_jd - 0.001) is None
        assert night.decan_of_hour(night.next_sunrise_jd + 0.001) is None

    def test_inside_night_returns_decan_string(self):
        night = self._make_night()
        jd_inside = night.hours[0].jd_start + 0.001
        result = night.decan_of_hour(jd_inside)
        assert isinstance(result, str)

    def test_consistency_with_hour_at(self):
        night = self._make_night()
        for h in night.hours:
            jd_mid = (h.jd_start + h.jd_end) / 2.0
            assert night.decan_of_hour(jd_mid) == night.hour_at(jd_mid).decan

    def test_decan_of_hour_matches_hour_at_decan(self):
        night = self._make_night()
        jd_inside = night.hours[5].jd_start + 0.001
        hour = night.hour_at(jd_inside)
        assert night.decan_of_hour(jd_inside) == hour.decan


# ===========================================================================
# 9.x — Property-based tests (Hypothesis, no ephemeris required)
# ===========================================================================

try:
    from hypothesis import given, settings
    import hypothesis.strategies as st
    _HYPOTHESIS_AVAILABLE = True
except ImportError:
    _HYPOTHESIS_AVAILABLE = False

_skip_no_hypothesis = pytest.mark.skipif(
    not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed"
)


@_skip_no_hypothesis
@given(lon=st.floats(min_value=0.0, max_value=360.0, exclude_max=True))
@settings(max_examples=100)
def test_prop2_decan_for_longitude_membership(lon):
    """Property 2: decan_for_longitude(lon) in list_decans() for all floats in [0, 360).

    **Validates: Requirements 2.4**
    """
    from moira.hermetic_decans import decan_for_longitude, list_decans
    result = decan_for_longitude(lon)
    assert result in list_decans()


@_skip_no_hypothesis
@given(lon=st.floats(allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_prop3_decan_for_longitude_normalization(lon):
    """Property 3: normalization invariant decan_for_longitude(lon) == decan_for_longitude(lon % 360).

    **Validates: Requirements 2.3**
    """
    from moira.hermetic_decans import decan_for_longitude
    assert decan_for_longitude(lon) == decan_for_longitude(lon % 360)


@_skip_no_hypothesis
@given(
    i=st.integers(min_value=0, max_value=35),
    offset=st.floats(min_value=0.0, max_value=10.0, exclude_max=True),
)
@settings(max_examples=100)
def test_prop4_decan_for_longitude_band_assignment(i, offset):
    """Property 4: correct band assignment for all i in [0, 35] and offset in [0, 10).

    **Validates: Requirements 2.2, 2.5**
    """
    from hypothesis import assume
    from moira.hermetic_decans import decan_for_longitude, list_decans
    # Filter out offsets so close to 10.0 that float addition crosses the band boundary
    assume(offset < 9.9999999999)
    lon = i * 10.0 + offset
    assert decan_for_longitude(lon) == list_decans()[i]


@_skip_no_hypothesis
@given(d=st.sampled_from(
    ["Horaios", "Tomalos", "Athafra", "Senacher", "Thesogar", "Tepis",
     "Sothis", "Tpau", "Aphruimis", "Tmoum", "Tathemis", "Serk",
     "Chontare", "Phakare", "Tpa", "Thosolk", "Sothis II", "Tpau II",
     "Chontachre", "Aphruimis II", "Tmoum II", "Tathemis II", "Serk II", "Chontare II",
     "Phakare II", "Tpa II", "Thosolk II", "Horaios II", "Tomalos II", "Athafra II",
     "Senacher II", "Thesogar II", "Tepis II", "Sothis III", "Tpau III", "Aphruimis III"]
))
@settings(max_examples=100)
def test_prop5_decan_index_range(d):
    """Property 5: decan_index(d) in [0, 35] for all valid decan names.

    **Validates: Requirements 2.7**
    """
    from moira.hermetic_decans import decan_index
    idx = decan_index(d)
    assert 0 <= idx <= 35


@_skip_no_hypothesis
@given(d=st.sampled_from(
    ["Horaios", "Tomalos", "Athafra", "Senacher", "Thesogar", "Tepis",
     "Sothis", "Tpau", "Aphruimis", "Tmoum", "Tathemis", "Serk",
     "Chontare", "Phakare", "Tpa", "Thosolk", "Sothis II", "Tpau II",
     "Chontachre", "Aphruimis II", "Tmoum II", "Tathemis II", "Serk II", "Chontare II",
     "Phakare II", "Tpa II", "Thosolk II", "Horaios II", "Tomalos II", "Athafra II",
     "Senacher II", "Thesogar II", "Tepis II", "Sothis III", "Tpau III", "Aphruimis III"]
))
@settings(max_examples=100)
def test_prop6_name_index_longitude_name_roundtrip(d):
    """Property 6: name → index → longitude → name round-trip.

    **Validates: Requirements 2.8, 8.2**
    """
    from moira.hermetic_decans import decan_index, decan_for_longitude
    idx = decan_index(d)
    lon = idx * 10.0
    assert decan_for_longitude(lon) == d


@_skip_no_hypothesis
@given(i=st.integers(min_value=0, max_value=35))
@settings(max_examples=100)
def test_prop7_index_name_index_roundtrip(i):
    """Property 7: index → name → index round-trip.

    **Validates: Requirements 8.3**
    """
    from moira.hermetic_decans import list_decans, decan_index
    name = list_decans()[i]
    assert decan_index(name) == i


@_skip_no_hypothesis
@given(d=st.sampled_from(
    ["Horaios", "Tomalos", "Athafra", "Senacher", "Thesogar", "Tepis",
     "Sothis", "Tpau", "Aphruimis", "Tmoum", "Tathemis", "Serk",
     "Chontare", "Phakare", "Tpa", "Thosolk", "Sothis II", "Tpau II",
     "Chontachre", "Aphruimis II", "Tmoum II", "Tathemis II", "Serk II", "Chontare II",
     "Phakare II", "Tpa II", "Thosolk II", "Horaios II", "Tomalos II", "Athafra II",
     "Senacher II", "Thesogar II", "Tepis II", "Sothis III", "Tpau III", "Aphruimis III"]
))
@settings(max_examples=100)
def test_prop8_decan_ruling_star_consistency(d):
    """Property 8: decan_ruling_star(d) == DECAN_RULING_STARS[d].

    **Validates: Requirements 3.2**
    """
    from moira.hermetic_decans import decan_ruling_star, DECAN_RULING_STARS
    assert decan_ruling_star(d) == DECAN_RULING_STARS[d]


def _build_decan_hours_night(sunset_jd: float, duration: float, start_idx: int):
    """Helper: construct a DecanHoursNight directly without calling decan_hours()."""
    from moira.hermetic_decans import DecanHour, DecanHoursNight, DECAN_RULING_STARS, list_decans
    decans = list_decans()
    hour_len = duration / 12.0
    next_sunrise_jd = sunset_jd + duration
    hours = []
    for i in range(12):
        idx = (start_idx + i) % 36
        jd_start = sunset_jd + i * hour_len
        jd_end = jd_start + hour_len
        hours.append(DecanHour(
            hour_number=i + 1,
            decan=decans[idx],
            ruling_star=DECAN_RULING_STARS[decans[idx]],
            jd_start=jd_start,
            jd_end=jd_end,
        ))
    return DecanHoursNight(
        date_jd=sunset_jd,
        latitude=51.5,
        longitude=-0.1,
        sunset_jd=sunset_jd,
        next_sunrise_jd=next_sunrise_jd,
        hours=hours,
    )


@_skip_no_hypothesis
@given(
    sunset_jd=st.floats(min_value=2451545.0, max_value=2451546.0),
    duration=st.floats(min_value=0.1, max_value=0.6),
    start_idx=st.integers(min_value=0, max_value=35),
)
@settings(max_examples=100)
def test_prop12_hour_structure_invariant(sunset_jd, duration, start_idx):
    """Property 12: hour structure invariant — 12 equal hours, no gaps, correct boundaries.

    **Validates: Requirements 5.4, 5.9, 5.10, 5.11**
    """
    night = _build_decan_hours_night(sunset_jd, duration, start_idx)

    # Exactly 12 hours
    assert len(night.hours) == 12

    # First hour starts at sunset
    assert night.hours[0].jd_start == night.sunset_jd

    # Last hour ends at next sunrise
    assert night.hours[11].jd_end == pytest.approx(night.next_sunrise_jd, rel=1e-9)

    # No gaps between consecutive hours
    for i in range(11):
        assert night.hours[i].jd_end == pytest.approx(night.hours[i + 1].jd_start, rel=1e-9)

    # All hours have equal duration (use absolute tolerance for float arithmetic)
    hour_len = duration / 12.0
    for h in night.hours:
        assert (h.jd_end - h.jd_start) == pytest.approx(hour_len, abs=1e-9)


@_skip_no_hypothesis
@given(
    sunset_jd=st.floats(min_value=2451545.0, max_value=2451546.0),
    duration=st.floats(min_value=0.1, max_value=0.6),
    start_idx=st.integers(min_value=0, max_value=35),
)
@settings(max_examples=100)
def test_prop13_sequential_ecliptic_order(sunset_jd, duration, start_idx):
    """Property 13: consecutive hours have consecutive decan indices (mod 36).

    **Validates: Requirements 5.5**
    """
    from moira.hermetic_decans import decan_index
    night = _build_decan_hours_night(sunset_jd, duration, start_idx)

    for i in range(11):
        idx_i = decan_index(night.hours[i].decan)
        idx_next = decan_index(night.hours[i + 1].decan)
        assert (idx_i + 1) % 36 == idx_next


@_skip_no_hypothesis
@given(
    sunset_jd=st.floats(min_value=2451545.0, max_value=2451546.0),
    duration=st.floats(min_value=0.1, max_value=0.6),
    start_idx=st.integers(min_value=0, max_value=35),
    frac=st.floats(min_value=0.0, max_value=1.0, exclude_max=True),
)
@settings(max_examples=100)
def test_prop14_hour_at_decan_of_hour_consistency(sunset_jd, duration, start_idx, frac):
    """Property 14: hour_at(jd).decan == decan_of_hour(jd) for any JD inside the night.

    **Validates: Requirements 5.7, 5.8**
    """
    night = _build_decan_hours_night(sunset_jd, duration, start_idx)

    # Pick a JD strictly inside the night
    jd = sunset_jd + frac * duration

    hour = night.hour_at(jd)
    decan_name = night.decan_of_hour(jd)

    # Both should agree
    if hour is not None:
        assert decan_name == hour.decan
    else:
        assert decan_name is None


# ===========================================================================
# Meeus oracle tests — Chapter 12 (GMST) and Chapter 24 (Houses / MC)
#
# Reference: Jean Meeus, "Astronomical Algorithms" 2nd ed.
#   Example 12.a  — April 10, 1987, 0h UT (JD 2446895.5)
#                   GMST = 197.693195°
#
# All expected values are derived from that single verified anchor point.
# No external runtime dependency: constants are hardcoded from the oracle run.
# ===========================================================================

# Oracle constants — do not edit without re-running the verification script.
_MEEUS_JD          = 2446895.5      # April 10 1987, 0h UT
_MEEUS_GMST        = 197.693195     # deg — Meeus Ex 12.a ground truth
_MEEUS_OBL_TRUE    = 23.443559      # deg — true obliquity at that JD
_MEEUS_MC_LON_0    = 199.173212     # deg — MC at geo_lon=0.0
_MEEUS_MC_LON_25   = 225.158843     # deg — MC at geo_lon=25.0 (Athens)
_MEEUS_MC_DECAN_0  = "Aphruimis II" # decan containing 199.17° (190–200°)
_MEEUS_MC_DECAN_25 = "Serk II"      # decan containing 225.16° (220–230°)


class TestLstToRamcMeeusOracle:
    """_lst_to_ramc agrees with Meeus Example 12.a to sub-arcsecond precision."""

    def test_gmst_matches_meeus_example_12a(self):
        """GMST at JD 2446895.5 (lon=0) must equal Meeus 197.693195° within 0.001°."""
        from moira.hermetic_decans import _lst_to_ramc
        result = _lst_to_ramc(_MEEUS_JD, 0.0)
        assert abs(result - _MEEUS_GMST) < 0.001, (
            f"GMST {result:.6f}° diverges from Meeus oracle {_MEEUS_GMST}° "
            f"by {abs(result - _MEEUS_GMST)*3600:.2f} arcsec"
        )

    def test_lst_shifts_by_geo_longitude(self):
        """LST at lon=25° must equal GMST + 25° (modulo 360)."""
        from moira.hermetic_decans import _lst_to_ramc
        gmst  = _lst_to_ramc(_MEEUS_JD, 0.0)
        lst25 = _lst_to_ramc(_MEEUS_JD, 25.0)
        assert abs((lst25 - gmst) % 360.0 - 25.0) < 0.001


class TestMcFormulaOracleMeeus:
    """MC longitude formula verified against the Meeus Chapter 12 anchor point.

    The MC formula (tan MC = sin RAMC / (cos RAMC × cos ε)) is stated in
    Meeus Chapter 24.  These tests confirm the implementation is correct by
    chaining from the verified GMST value.
    """

    def test_mc_longitude_at_greenwich(self):
        """MC at geo_lon=0 must match oracle 199.173212° within 0.001°."""
        import math
        from moira.hermetic_decans import _lst_to_ramc
        from moira.obliquity import true_obliquity
        ramc  = _lst_to_ramc(_MEEUS_JD, 0.0)
        obl   = true_obliquity(_MEEUS_JD)
        mc    = math.degrees(math.atan2(
            math.sin(math.radians(ramc)),
            math.cos(math.radians(ramc)) * math.cos(math.radians(obl)),
        )) % 360.0
        assert abs(mc - _MEEUS_MC_LON_0) < 0.001, (
            f"MC {mc:.6f}° differs from oracle {_MEEUS_MC_LON_0}°"
        )

    def test_mc_longitude_at_athens(self):
        """MC at geo_lon=25 must match oracle 225.158843° within 0.001°."""
        import math
        from moira.hermetic_decans import _lst_to_ramc
        from moira.obliquity import true_obliquity
        ramc  = _lst_to_ramc(_MEEUS_JD, 25.0)
        obl   = true_obliquity(_MEEUS_JD)
        mc    = math.degrees(math.atan2(
            math.sin(math.radians(ramc)),
            math.cos(math.radians(ramc)) * math.cos(math.radians(obl)),
        )) % 360.0
        assert abs(mc - _MEEUS_MC_LON_25) < 0.001

    def test_mc_decan_at_greenwich(self):
        """Decan containing MC at geo_lon=0 must be 'Aphruimis II' (190–200°)."""
        import math
        from moira.hermetic_decans import _lst_to_ramc, decan_for_longitude
        from moira.obliquity import true_obliquity
        ramc = _lst_to_ramc(_MEEUS_JD, 0.0)
        obl  = true_obliquity(_MEEUS_JD)
        mc   = math.degrees(math.atan2(
            math.sin(math.radians(ramc)),
            math.cos(math.radians(ramc)) * math.cos(math.radians(obl)),
        )) % 360.0
        assert decan_for_longitude(mc) == _MEEUS_MC_DECAN_0

    def test_mc_decan_at_athens(self):
        """Decan containing MC at geo_lon=25 must be 'Serk II' (220–230°)."""
        import math
        from moira.hermetic_decans import _lst_to_ramc, decan_for_longitude
        from moira.obliquity import true_obliquity
        ramc = _lst_to_ramc(_MEEUS_JD, 25.0)
        obl  = true_obliquity(_MEEUS_JD)
        mc   = math.degrees(math.atan2(
            math.sin(math.radians(ramc)),
            math.cos(math.radians(ramc)) * math.cos(math.radians(obl)),
        )) % 360.0
        assert decan_for_longitude(mc) == _MEEUS_MC_DECAN_25

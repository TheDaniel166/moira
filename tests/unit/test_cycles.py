"""
tests/unit/test_cycles.py

Unit tests for the Planetary Cycles Engine (moira.cycles).

Scope: SynodicPhase, planetary ages, firdar, planetary days/hours,
       mutation element classification, and result vessel invariants.

Ephemeris-dependent tests (return_series, great_conjunctions,
synodic_cycle_position) are in the integration section and marked
with @pytest.mark.requires_ephemeris.
"""

import math
import pytest

from moira.cycles import (
    # Enums
    SynodicPhase,
    GreatMutationElement,
    PlanetaryAgeName,
    # Return series
    ReturnEvent,
    ReturnSeries,
    return_series,
    half_return_series,
    lifetime_returns,
    # Synodic
    SynodicCyclePosition,
    synodic_cycle_position,
    # Great conjunctions
    GreatConjunction,
    GreatConjunctionSeries,
    MutationPeriod,
    great_conjunctions,
    mutation_period_at,
    # Ages
    PlanetaryAgePeriod,
    PlanetaryAgeProfile,
    planetary_age_at,
    planetary_age_profile,
    # Firdar
    FirdarPeriod,
    FirdarSubPeriod,
    FirdarSeries,
    firdar_series,
    firdar_at,
    # Days/hours
    PlanetaryDayInfo,
    PlanetaryHour,
    PlanetaryHoursProfile,
    planetary_day_ruler,
    planetary_hours_for_day,
    # Constants
    CHALDEAN_ORDER,
)

from moira.constants import Body


# ===========================================================================
# SYNODIC PHASE CLASSIFICATION
# ===========================================================================

class TestSynodicPhase:
    def test_eight_members(self):
        assert len(SynodicPhase) == 8

    @pytest.mark.parametrize("angle,expected", [
        (0.0, SynodicPhase.NEW),
        (10.0, SynodicPhase.NEW),
        (350.0, SynodicPhase.NEW),  # 337.5-360 wraps to NEW
        (355.0, SynodicPhase.NEW),  # wraps
        (45.0, SynodicPhase.WAXING_CRESCENT),
        (90.0, SynodicPhase.FIRST_QUARTER),
        (135.0, SynodicPhase.WAXING_GIBBOUS),
        (180.0, SynodicPhase.FULL),
        (225.0, SynodicPhase.WANING_GIBBOUS),
        (270.0, SynodicPhase.LAST_QUARTER),
        (315.0, SynodicPhase.WANING_CRESCENT),
    ])
    def test_angle_classification(self, angle, expected):
        assert SynodicPhase.from_angle(angle) is expected

    def test_normalization_beyond_360(self):
        assert SynodicPhase.from_angle(360.0) is SynodicPhase.NEW
        assert SynodicPhase.from_angle(450.0) is SynodicPhase.FIRST_QUARTER

    def test_negative_angles_handled(self):
        # -90 = 270 mod 360
        assert SynodicPhase.from_angle(-90.0) is SynodicPhase.LAST_QUARTER


# ===========================================================================
# MUTATION ELEMENT CLASSIFICATION
# ===========================================================================

class TestMutationElement:
    @pytest.mark.parametrize("lon,expected", [
        (0.0, GreatMutationElement.FIRE),      # Aries
        (30.0, GreatMutationElement.EARTH),     # Taurus
        (60.0, GreatMutationElement.AIR),       # Gemini
        (90.0, GreatMutationElement.WATER),     # Cancer
        (120.0, GreatMutationElement.FIRE),     # Leo
        (150.0, GreatMutationElement.EARTH),    # Virgo
        (180.0, GreatMutationElement.AIR),      # Libra
        (210.0, GreatMutationElement.WATER),    # Scorpio
        (240.0, GreatMutationElement.FIRE),     # Sagittarius
        (270.0, GreatMutationElement.EARTH),    # Capricorn
        (300.0, GreatMutationElement.AIR),      # Aquarius
        (330.0, GreatMutationElement.WATER),    # Pisces
    ])
    def test_all_twelve_signs(self, lon, expected):
        assert mutation_period_at(lon) is expected

    def test_normalization(self):
        assert mutation_period_at(360.0) is GreatMutationElement.FIRE
        assert mutation_period_at(-30.0) is GreatMutationElement.WATER  # Pisces


# ===========================================================================
# PLANETARY AGES (Ptolemy)
# ===========================================================================

class TestPlanetaryAges:
    @pytest.mark.parametrize("age,expected_ruler", [
        (0.0, PlanetaryAgeName.MOON),
        (2.0, PlanetaryAgeName.MOON),
        (4.0, PlanetaryAgeName.MERCURY),
        (10.0, PlanetaryAgeName.MERCURY),
        (14.0, PlanetaryAgeName.VENUS),
        (20.0, PlanetaryAgeName.VENUS),
        (22.0, PlanetaryAgeName.SUN),
        (35.0, PlanetaryAgeName.SUN),
        (41.0, PlanetaryAgeName.MARS),
        (50.0, PlanetaryAgeName.MARS),
        (56.0, PlanetaryAgeName.JUPITER),
        (65.0, PlanetaryAgeName.JUPITER),
        (68.0, PlanetaryAgeName.SATURN),
        (90.0, PlanetaryAgeName.SATURN),
        (120.0, PlanetaryAgeName.SATURN),  # open-ended
    ])
    def test_age_boundaries(self, age, expected_ruler):
        period = planetary_age_at(age)
        assert period.ruler is expected_ruler

    def test_negative_age_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            planetary_age_at(-1.0)

    def test_seven_periods_total(self):
        profile = planetary_age_profile()
        assert len(profile.periods) == 7

    def test_profile_with_queried_age(self):
        profile = planetary_age_profile(35.0)
        assert profile.queried_age == 35.0
        assert profile.current is not None
        assert profile.current.ruler is PlanetaryAgeName.SUN

    def test_profile_without_queried_age(self):
        profile = planetary_age_profile()
        assert profile.queried_age is None
        assert profile.current is None

    def test_periods_are_contiguous(self):
        profile = planetary_age_profile()
        for i in range(len(profile.periods) - 1):
            assert profile.periods[i].end_age == profile.periods[i + 1].start_age

    def test_saturn_is_open_ended(self):
        profile = planetary_age_profile()
        assert profile.periods[-1].ruler is PlanetaryAgeName.SATURN
        assert profile.periods[-1].end_age is None

    def test_periods_are_frozen(self):
        period = planetary_age_at(30)
        with pytest.raises(AttributeError):
            period.ruler = PlanetaryAgeName.MOON


# ===========================================================================
# FIRDAR (Abu Ma'shar)
# ===========================================================================

class TestFirdar:
    BIRTH_JD = 2451545.0  # J2000.0

    def test_diurnal_sequence_sum_is_75(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        assert series.total_years == 75.0

    def test_nocturnal_sequence_sum_is_75(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=False)
        assert series.total_years == 75.0

    def test_nine_periods(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        assert len(series.periods) == 9

    def test_diurnal_starts_with_sun(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        assert series.periods[0].ruler == Body.SUN

    def test_nocturnal_starts_with_moon(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=False)
        assert series.periods[0].ruler == Body.MOON

    def test_diurnal_durations(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        durations = [p.duration_years for p in series.periods]
        assert durations == [10, 8, 13, 9, 11, 12, 7, 3, 2]

    def test_nocturnal_durations(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=False)
        durations = [p.duration_years for p in series.periods]
        assert durations == [9, 11, 12, 7, 10, 8, 13, 3, 2]

    def test_periods_are_contiguous(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        for i in range(len(series.periods) - 1):
            assert abs(series.periods[i].end_jd - series.periods[i + 1].start_jd) < 0.001

    def test_first_period_starts_at_birth(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        assert series.periods[0].start_jd == self.BIRTH_JD

    def test_planetary_firdars_have_7_sub_periods(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        for p in series.periods[:7]:  # first 7 are planetary
            assert p.sub_periods is not None
            assert len(p.sub_periods) == 7

    def test_nodal_firdars_have_no_sub_periods(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        for p in series.periods[7:]:  # last 2 are nodal
            assert p.sub_periods is None

    def test_sub_periods_are_contiguous(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        for p in series.periods[:7]:
            for i in range(len(p.sub_periods) - 1):
                assert abs(p.sub_periods[i].end_jd - p.sub_periods[i + 1].start_jd) < 0.001

    def test_sub_period_starts_with_major_ruler(self):
        """First sub-period ruler matches the major firdar ruler."""
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        for p in series.periods[:7]:
            assert p.sub_periods[0].sub_ruler == p.ruler

    def test_sub_periods_follow_chaldean_order(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        sun_firdar = series.periods[0]  # Sun firdar
        rulers = [s.sub_ruler for s in sun_firdar.sub_periods]
        # Sun is at Chaldean index 3; sequence: Sun, Venus, Mercury, Moon, Saturn, Jupiter, Mars
        expected = [CHALDEAN_ORDER[(3 + i) % 7] for i in range(7)]
        assert rulers == expected

    def test_firdar_at_birth(self):
        p = firdar_at(self.BIRTH_JD, self.BIRTH_JD, is_day_birth=True)
        assert p.ruler == Body.SUN
        assert p.ordinal == 1

    def test_firdar_at_age_20(self):
        """Age 20: Sun(10) + Venus(8) = 18 elapsed, Mercury starts at 18."""
        target = self.BIRTH_JD + 20 * 365.25
        p = firdar_at(self.BIRTH_JD, target, is_day_birth=True)
        assert p.ruler == Body.MERCURY
        assert p.ordinal == 3

    def test_firdar_at_before_birth_raises(self):
        with pytest.raises(ValueError, match="precedes"):
            firdar_at(self.BIRTH_JD, self.BIRTH_JD - 1, is_day_birth=True)

    def test_firdar_at_beyond_cycle_raises(self):
        target = self.BIRTH_JD + 76 * 365.25
        with pytest.raises(ValueError, match="beyond"):
            firdar_at(self.BIRTH_JD, target, is_day_birth=True)

    def test_ordinals_are_sequential(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        ordinals = [p.ordinal for p in series.periods]
        assert ordinals == list(range(1, 10))

    def test_periods_are_frozen(self):
        series = firdar_series(self.BIRTH_JD, is_day_birth=True)
        with pytest.raises(AttributeError):
            series.periods[0].ruler = Body.MOON


# ===========================================================================
# PLANETARY DAYS
# ===========================================================================

class TestPlanetaryDay:
    def test_j2000_is_saturday_saturn(self):
        """J2000.0 (2000-01-01 12:00 TT) was a Saturday."""
        day = planetary_day_ruler(2451545.0)
        assert day.weekday_name == "Saturday"
        assert day.ruler == Body.SATURN
        assert day.weekday_number == 6  # ISO Saturday

    @pytest.mark.parametrize("offset,expected_day,expected_ruler", [
        (0, "Saturday", Body.SATURN),
        (1, "Sunday", Body.SUN),
        (2, "Monday", Body.MOON),
        (3, "Tuesday", Body.MARS),
        (4, "Wednesday", Body.MERCURY),
        (5, "Thursday", Body.JUPITER),
        (6, "Friday", Body.VENUS),
        (7, "Saturday", Body.SATURN),  # full cycle
    ])
    def test_full_week_from_j2000(self, offset, expected_day, expected_ruler):
        day = planetary_day_ruler(2451545.0 + offset)
        assert day.weekday_name == expected_day
        assert day.ruler == expected_ruler


# ===========================================================================
# PLANETARY HOURS
# ===========================================================================

class TestPlanetaryHours:
    def test_24_hours_generated(self):
        profile = planetary_hours_for_day(2451545.25, 2451545.75)
        assert len(profile.hours) == 24

    def test_12_day_12_night(self):
        profile = planetary_hours_for_day(2451545.25, 2451545.75)
        day_hours = [h for h in profile.hours if h.is_day_hour]
        night_hours = [h for h in profile.hours if not h.is_day_hour]
        assert len(day_hours) == 12
        assert len(night_hours) == 12

    def test_first_hour_ruled_by_day_ruler(self):
        """The first hour of the day must be ruled by the day's planet."""
        profile = planetary_hours_for_day(2451545.25, 2451545.75)
        assert profile.hours[0].ruler == profile.day_info.ruler

    def test_25th_hour_is_next_day_ruler(self):
        """
        The Chaldean system is self-consistent: the ruler of what would be
        the 25th hour (= first hour of the next day) should be the next
        day's planetary ruler.
        """
        # Saturday's ruler = Saturn (index 0 in Chaldean)
        # After 24 hours: (0 + 24) % 7 = 3 → Sun
        # Sunday's ruler = Sun. Consistent!
        profile = planetary_hours_for_day(2451545.25, 2451545.75)
        saturn_idx = CHALDEAN_ORDER.index(Body.SATURN)
        hour_25_ruler = CHALDEAN_ORDER[(saturn_idx + 24) % 7]
        assert hour_25_ruler == Body.SUN

    def test_hours_are_contiguous(self):
        profile = planetary_hours_for_day(2451545.25, 2451545.75)
        for i in range(len(profile.hours) - 1):
            assert abs(profile.hours[i].end_jd - profile.hours[i + 1].start_jd) < 1e-10

    def test_day_hours_span_sunrise_to_sunset(self):
        sunrise = 2451545.25
        sunset = 2451545.75
        profile = planetary_hours_for_day(sunrise, sunset)
        assert abs(profile.hours[0].start_jd - sunrise) < 1e-10
        assert abs(profile.hours[11].end_jd - sunset) < 1e-10

    def test_night_hours_span_sunset_to_next_sunrise(self):
        sunrise = 2451545.25
        sunset = 2451545.75
        next_sunrise = 2451546.25
        profile = planetary_hours_for_day(sunrise, sunset, next_sunrise)
        assert abs(profile.hours[12].start_jd - sunset) < 1e-10
        assert abs(profile.hours[23].end_jd - next_sunrise) < 1e-10

    def test_unequal_hours_in_summer(self):
        """Long day, short night: day hours should be longer than night hours."""
        sunrise = 2451545.20    # early sunrise
        sunset = 2451545.82     # late sunset
        next_sunrise = 2451546.20
        profile = planetary_hours_for_day(sunrise, sunset, next_sunrise)
        assert profile.day_hour_length > profile.night_hour_length

    def test_equinox_hours_nearly_equal(self):
        """At equinox, day and night hours should be roughly equal."""
        sunrise = 2451545.25
        sunset = 2451545.75
        profile = planetary_hours_for_day(sunrise, sunset)
        ratio = profile.day_hour_length / profile.night_hour_length
        assert 0.95 < ratio < 1.05

    def test_hour_numbers_are_1_to_24(self):
        profile = planetary_hours_for_day(2451545.25, 2451545.75)
        numbers = [h.hour_number for h in profile.hours]
        assert numbers == list(range(1, 25))

    def test_profile_is_frozen(self):
        profile = planetary_hours_for_day(2451545.25, 2451545.75)
        with pytest.raises(AttributeError):
            profile.day_hour_length = 999.0

    def test_chaldean_sequence_repeats(self):
        """Hour rulers must follow the 7-element Chaldean cycle."""
        profile = planetary_hours_for_day(2451545.25, 2451545.75)
        rulers = [h.ruler for h in profile.hours]
        for i in range(len(rulers)):
            assert rulers[i] == CHALDEAN_ORDER[(CHALDEAN_ORDER.index(rulers[0]) + i) % 7]


# ===========================================================================
# RETURN SERIES (ephemeris-dependent)
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestReturnSeries:
    def test_saturn_returns_in_90_years(self):
        """Saturn returns ~3 times in 100 years (~29.5y sidereal period).

        Due to retrograde motion, Saturn may cross the same longitude
        multiple times per revolution (direct-retro-direct triple pass),
        so the count can exceed the number of sidereal revolutions.
        """
        birth_jd = 2451545.0  # J2000
        series = lifetime_returns(Body.SATURN, 68.0, birth_jd, years=100)
        # 3 sidereal revolutions, each potentially 1-3 crossings
        assert 3 <= series.count <= 10
        assert series.body == Body.SATURN

    def test_solar_returns_match_years(self):
        """Sun returns once per year; 10-year window should yield ~10 returns."""
        birth_jd = 2451545.0
        jd_end = birth_jd + 10 * 365.25
        series = return_series(Body.SUN, 280.0, birth_jd, jd_end)
        assert 9 <= series.count <= 11

    def test_return_events_are_chronological(self):
        birth_jd = 2451545.0
        jd_end = birth_jd + 5 * 365.25
        series = return_series(Body.SUN, 280.0, birth_jd, jd_end)
        for i in range(len(series.returns) - 1):
            assert series.returns[i].jd_ut < series.returns[i + 1].jd_ut

    def test_return_numbers_are_sequential(self):
        birth_jd = 2451545.0
        jd_end = birth_jd + 3 * 365.25
        series = return_series(Body.SUN, 280.0, birth_jd, jd_end)
        for i, evt in enumerate(series.returns, start=1):
            assert evt.return_number == i

    def test_half_return_series(self):
        """Half-returns for Sun should also be ~annual (opposition to natal lon)."""
        birth_jd = 2451545.0
        jd_end = birth_jd + 5 * 365.25
        series = half_return_series(Body.SUN, 280.0, birth_jd, jd_end)
        assert series.count > 0
        assert all(evt.is_half for evt in series.returns)

    def test_empty_range_returns_zero(self):
        """Tiny window that can't contain a return."""
        series = return_series(Body.SATURN, 0.0, 2451545.0, 2451546.0)
        assert series.count == 0
        assert series.returns == ()


# ===========================================================================
# SYNODIC CYCLE POSITION (ephemeris-dependent)
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestSynodicCyclePosition:
    def test_returns_correct_bodies(self):
        pos = synodic_cycle_position(Body.JUPITER, Body.SATURN, 2451545.0)
        assert pos.body1 == Body.JUPITER
        assert pos.body2 == Body.SATURN

    def test_phase_angle_in_range(self):
        pos = synodic_cycle_position(Body.SUN, Body.MOON, 2451545.0)
        assert 0.0 <= pos.phase_angle < 360.0

    def test_waxing_flag_consistent(self):
        pos = synodic_cycle_position(Body.SUN, Body.MOON, 2451545.0)
        if 0.0 < pos.phase_angle < 180.0:
            assert pos.is_waxing is True
        elif pos.phase_angle > 180.0:
            assert pos.is_waxing is False

    def test_phase_matches_angle(self):
        pos = synodic_cycle_position(Body.SUN, Body.MOON, 2451545.0)
        expected_phase = SynodicPhase.from_angle(pos.phase_angle)
        assert pos.phase is expected_phase


# ===========================================================================
# GREAT CONJUNCTIONS (ephemeris-dependent)
# ===========================================================================

@pytest.mark.requires_ephemeris
class TestGreatConjunctions:
    def test_one_conjunction_in_20_year_window(self):
        """Jupiter-Saturn conjunctions occur every ~20 years."""
        # 2000-2025 contains the 2020 great conjunction
        jd_start = 2451545.0          # 2000-01-01
        jd_end = 2451545.0 + 25 * 365.25  # ~2025
        series = great_conjunctions(jd_start, jd_end)
        assert series.count >= 1

    def test_conjunction_has_element(self):
        jd_start = 2451545.0
        jd_end = 2451545.0 + 25 * 365.25
        series = great_conjunctions(jd_start, jd_end)
        if series.count > 0:
            gc = series.conjunctions[0]
            assert isinstance(gc.element, GreatMutationElement)
            assert gc.sign != ""

    def test_elements_represented_populated(self):
        jd_start = 2451545.0
        jd_end = 2451545.0 + 25 * 365.25
        series = great_conjunctions(jd_start, jd_end)
        assert len(series.elements_represented) >= 1


# ===========================================================================
# PUBLIC API CONTRACT
# ===========================================================================

class TestCyclesPublicApi:
    def test_all_curated_names_resolve(self):
        import moira.cycles as _mod
        for name in _mod.__all__:
            assert hasattr(_mod, name), f"moira.cycles.{name} not found"

    def test_all_count(self):
        import moira.cycles as _mod
        assert len(_mod.__all__) == 29

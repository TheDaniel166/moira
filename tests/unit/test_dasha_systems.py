"""
Unit tests for moira.dasha_systems.

Coverage
--------
1. Constant tables — totals, sequence lengths, Yogini planets.
2. ashtottari() — structural output (period count, cycle span, jd continuity).
3. ashtottari() — system label on all periods.
4. ashtottari() — year basis policy changes span.
5. ashtottari() — levels > 1 populates sub-periods.
6. ashtottari() — eligibility bypass flag.
7. yogini_dasha() — structural output (period count, 36-year cycle).
8. yogini_dasha() — sub-periods for levels=2.
9. Period jd continuity (start of next == end of previous).
10. AlternateDashaPeriod vessel invariants.
11. Error handling.
12. Public surface — __all__ completeness.

Source authority: BPHS Ashtottari Dasha Adhyaya; K.N. Rao, "Yogini Dasha" (1993).
"""
from __future__ import annotations

import math
import pytest

from moira.dasha_systems import (
    ASHTOTTARI_NAKSHATRA_LORD,
    ASHTOTTARI_SEQUENCE,
    ASHTOTTARI_TOTAL,
    ASHTOTTARI_YEARS,
    YOGINI_PLANETS,
    YOGINI_SEQUENCE,
    YOGINI_TOTAL,
    YOGINI_YEARS,
    AlternateDashaPeriod,
    AlternateDashaSequenceProfile,
    AlternatePeriodProfile,
    AshtottariPolicy,
    YoginiPolicy,
    alternate_period_profile,
    alternate_sequence_profile,
    ashtottari,
    validate_alternate_dasha_output,
    yogini_dasha,
)

_J2000 = 2451545.0
_JULIAN_YEAR = 365.25


# ===========================================================================
# 1. Constant tables
# ===========================================================================

class TestConstantTables:

    def test_ashtottari_years_total_108(self):
        assert sum(ASHTOTTARI_YEARS.values()) == ASHTOTTARI_TOTAL == 108

    def test_ashtottari_sequence_length_8(self):
        assert len(ASHTOTTARI_SEQUENCE) == 8

    def test_ashtottari_sequence_no_duplicates(self):
        assert len(set(ASHTOTTARI_SEQUENCE)) == 8

    def test_ashtottari_nakshatra_lord_length_27(self):
        assert len(ASHTOTTARI_NAKSHATRA_LORD) == 27

    def test_ashtottari_nakshatra_lord_all_valid(self):
        for lord in ASHTOTTARI_NAKSHATRA_LORD:
            assert lord in ASHTOTTARI_SEQUENCE

    def test_yogini_years_total_36(self):
        assert sum(YOGINI_YEARS.values()) == YOGINI_TOTAL == 36

    def test_yogini_sequence_length_8(self):
        assert len(YOGINI_SEQUENCE) == 8

    def test_yogini_planets_has_8_entries(self):
        assert len(YOGINI_PLANETS) == 8

    def test_yogini_planets_all_map_to_known_bodies(self):
        valid = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"}
        for yogini, planet in YOGINI_PLANETS.items():
            assert planet in valid, f"{yogini} maps to unknown {planet!r}"

    def test_yogini_years_consecutive_sum_to_36(self):
        total = sum(YOGINI_YEARS[y] for y in YOGINI_SEQUENCE)
        assert total == 36


# ===========================================================================
# 2. ashtottari() — structural output
# ===========================================================================

class TestAshtottariStructure:

    @pytest.fixture()
    def periods(self) -> list[AlternateDashaPeriod]:
        return ashtottari(0.0, _J2000, levels=1,
                          policy=AshtottariPolicy(bypass_eligibility=True))

    def test_returns_list(self, periods):
        assert isinstance(periods, list)

    def test_at_least_one_period(self, periods):
        assert len(periods) >= 1

    def test_all_periods_system_is_ashtottari(self, periods):
        for p in periods:
            assert p.system == "ashtottari"

    def test_first_period_starts_at_natal_jd(self, periods):
        assert periods[0].start_jd == pytest.approx(_J2000)

    def test_last_period_ends_within_108_years(self, periods):
        expected_end = _J2000 + 108 * _JULIAN_YEAR
        assert periods[-1].end_jd == pytest.approx(expected_end, rel=1e-4)

    def test_total_span_is_108_julian_years(self, periods):
        total_days = periods[-1].end_jd - periods[0].start_jd
        assert total_days == pytest.approx(108 * _JULIAN_YEAR, rel=1e-4)

    def test_all_lords_are_valid_ashtottari_lords(self, periods):
        for p in periods:
            assert p.lord in ASHTOTTARI_SEQUENCE

    def test_level_1_periods_have_empty_sub(self, periods):
        for p in periods:
            assert p.sub == []

    def test_period_count_is_8_or_more(self, periods):
        # Exactly 8 unless partial first period shifts a second cycle
        assert 8 <= len(periods) <= 9


# ===========================================================================
# 3. ashtottari() — jd continuity
# ===========================================================================

class TestAshtottariContinuity:

    def test_periods_are_contiguous(self):
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        for i in range(len(periods) - 1):
            assert periods[i].end_jd == pytest.approx(periods[i + 1].start_jd)

    def test_sub_periods_are_contiguous_for_level_2(self):
        periods = ashtottari(0.0, _J2000, levels=2,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        for p in periods:
            if p.sub:
                for i in range(len(p.sub) - 1):
                    assert p.sub[i].end_jd == pytest.approx(p.sub[i + 1].start_jd)


# ===========================================================================
# 4. ashtottari() — year basis policy
# ===========================================================================

class TestAshtottariYearBasis:

    def test_savana_year_gives_shorter_duration_than_julian(self):
        p_julian = ashtottari(0.0, _J2000, levels=1,
                              policy=AshtottariPolicy(bypass_eligibility=True,
                                                      year_basis="julian_365.25"))
        p_savana = ashtottari(0.0, _J2000, levels=1,
                              policy=AshtottariPolicy(bypass_eligibility=True,
                                                      year_basis="savana_360"))
        span_julian = p_julian[-1].end_jd - p_julian[0].start_jd
        span_savana = p_savana[-1].end_jd - p_savana[0].start_jd
        assert span_savana < span_julian

    def test_invalid_year_basis_raises_value_error(self):
        with pytest.raises(ValueError):
            ashtottari(0.0, _J2000, levels=1,
                       policy=AshtottariPolicy(bypass_eligibility=True,
                                               year_basis="unknown"))


# ===========================================================================
# 5. ashtottari() — levels > 1 populates sub-periods
# ===========================================================================

class TestAshtottariSubPeriods:

    def test_levels_2_produces_sub_periods(self):
        periods = ashtottari(0.0, _J2000, levels=2,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        assert any(len(p.sub) > 0 for p in periods)

    def test_sub_periods_have_level_2(self):
        periods = ashtottari(0.0, _J2000, levels=2,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        for p in periods:
            for sub in p.sub:
                assert sub.level == 2

    def test_sub_period_spans_sum_to_mahadasha_span(self):
        periods = ashtottari(0.0, _J2000, levels=2,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        for p in periods:
            if p.sub:
                sub_span = sum(s.end_jd - s.start_jd for s in p.sub)
                maha_span = p.end_jd - p.start_jd
                assert sub_span == pytest.approx(maha_span, rel=1e-9)


# ===========================================================================
# 6. ashtottari() — eligibility
# ===========================================================================

class TestAshtottariEligibility:

    def test_bypass_true_does_not_raise(self):
        # Should not raise regardless of lagna
        ashtottari(0.0, _J2000, levels=1,
                   policy=AshtottariPolicy(bypass_eligibility=True))

    def test_lagna_provided_without_bypass_raises(self):
        # The current implementation raises for lagna_sign_index without bypass
        with pytest.raises(ValueError):
            ashtottari(0.0, _J2000, levels=1,
                       policy=AshtottariPolicy(bypass_eligibility=False,
                                               lagna_sign_index=0))


# ===========================================================================
# 7. yogini_dasha() — structural output
# ===========================================================================

class TestYoginiDashaStructure:

    @pytest.fixture()
    def periods(self) -> list[AlternateDashaPeriod]:
        return yogini_dasha(0.0, _J2000, levels=1)

    def test_returns_list(self, periods):
        assert isinstance(periods, list)

    def test_at_least_one_period(self, periods):
        assert len(periods) >= 1

    def test_all_system_labels_are_yogini(self, periods):
        for p in periods:
            assert p.system == "yogini"

    def test_first_period_starts_at_natal(self, periods):
        assert periods[0].start_jd == pytest.approx(_J2000)

    def test_total_span_is_36_years(self, periods):
        total = periods[-1].end_jd - periods[0].start_jd
        assert total == pytest.approx(36 * _JULIAN_YEAR, rel=1e-4)

    def test_all_lords_in_yogini_sequence(self, periods):
        for p in periods:
            assert p.lord in YOGINI_SEQUENCE


# ===========================================================================
# 8. yogini_dasha() — sub-periods
# ===========================================================================

class TestYoginiSubPeriods:

    def test_levels_2_produces_sub_periods(self):
        periods = yogini_dasha(0.0, _J2000, levels=2)
        assert any(len(p.sub) > 0 for p in periods)

    def test_sub_period_spans_sum_to_maha_span(self):
        periods = yogini_dasha(0.0, _J2000, levels=2)
        for p in periods:
            if p.sub:
                sub_span = sum(s.end_jd - s.start_jd for s in p.sub)
                assert sub_span == pytest.approx(p.end_jd - p.start_jd, rel=1e-9)

    def test_yogini_periods_contiguous(self):
        periods = yogini_dasha(0.0, _J2000, levels=1)
        for i in range(len(periods) - 1):
            assert periods[i].end_jd == pytest.approx(periods[i + 1].start_jd)


# ===========================================================================
# 9. AlternateDashaPeriod vessel
# ===========================================================================

class TestAlternateDashaPeriodVessel:

    def test_period_is_frozen(self):
        periods = yogini_dasha(0.0, _J2000, levels=1)
        p = periods[0]
        with pytest.raises((AttributeError, TypeError)):
            p.lord = "mutated"  # type: ignore[misc]

    def test_period_has_slots(self):
        periods = yogini_dasha(0.0, _J2000, levels=1)
        assert "__dict__" not in type(periods[0]).__slots__

    def test_all_periods_have_positive_duration(self):
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        for p in periods:
            assert p.end_jd > p.start_jd

    def test_level_field_is_1_for_mahadashas(self):
        periods = yogini_dasha(0.0, _J2000, levels=1)
        for p in periods:
            assert p.level == 1


# ===========================================================================
# 10. Error handling
# ===========================================================================

class TestDashaSystemsErrors:

    def test_ashtottari_nan_natal_jd_raises(self):
        with pytest.raises(ValueError, match="natal_jd must be finite"):
            ashtottari(0.0, float("nan"), levels=1,
                       policy=AshtottariPolicy(bypass_eligibility=True))

    def test_yogini_nan_natal_jd_raises(self):
        with pytest.raises(ValueError, match="natal_jd must be finite"):
            yogini_dasha(0.0, float("nan"), levels=1)

    def test_ashtottari_inf_natal_jd_raises(self):
        with pytest.raises(ValueError):
            ashtottari(0.0, float("inf"), levels=1,
                       policy=AshtottariPolicy(bypass_eligibility=True))


# ===========================================================================
# 11. Public surface
# ===========================================================================

class TestPublicSurface:

    def test_all_names_importable(self):
        import moira.dasha_systems as mod
        for name in mod.__all__:
            assert hasattr(mod, name), f"__all__ lists {name!r} but absent"

    def test_key_names_present(self):
        import moira.dasha_systems as mod
        for name in ("ASHTOTTARI_YEARS", "YOGINI_YEARS", "AlternateDashaPeriod",
                     "AshtottariPolicy", "YoginiPolicy", "ashtottari", "yogini_dasha"):
            assert name in mod.__all__


# ===========================================================================
# 12. Phase 3 — AlternateDashaPeriod inspectability
# ===========================================================================

class TestAlternateDashaPeriodInspectability:

    @pytest.fixture()
    def period(self) -> AlternateDashaPeriod:
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        return periods[0]

    def test_years_property_positive(self, period):
        assert period.years > 0.0

    def test_years_property_consistent_with_jd_span(self, period):
        expected = (period.end_jd - period.start_jd) / 365.25
        assert period.years == pytest.approx(expected)

    def test_is_terminal_true_for_level1_no_sub(self, period):
        assert period.is_terminal is True

    def test_is_terminal_false_for_period_with_sub(self):
        periods = ashtottari(0.0, _J2000, levels=2,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        p = periods[0]
        assert p.is_terminal is False

    def test_yogini_years_property(self):
        periods = yogini_dasha(0.0, _J2000, levels=1)
        for p in periods:
            assert p.years > 0.0


# ===========================================================================
# 13. Phase 10 — AlternateDashaPeriod guards
# ===========================================================================

class TestAlternateDashaPeriodGuards:

    def _valid(self, **overrides):
        defaults = dict(
            system='ashtottari',
            level=1,
            lord='Sun',
            start_jd=_J2000,
            end_jd=_J2000 + 365.25,
            sub=[],
        )
        defaults.update(overrides)
        return AlternateDashaPeriod(**defaults)

    def test_valid_period_accepted(self):
        p = self._valid()
        assert p.lord == 'Sun'

    def test_invalid_system_raises(self):
        with pytest.raises(ValueError, match="system"):
            self._valid(system='kalachakra')

    def test_level_zero_raises(self):
        with pytest.raises(ValueError, match="level"):
            self._valid(level=0)

    def test_empty_lord_raises(self):
        with pytest.raises(ValueError, match="lord"):
            self._valid(lord='')

    def test_start_ge_end_raises(self):
        with pytest.raises(ValueError, match="start_jd"):
            self._valid(start_jd=_J2000 + 1, end_jd=_J2000)

    def test_start_equal_end_raises(self):
        with pytest.raises(ValueError):
            self._valid(start_jd=_J2000, end_jd=_J2000)

    def test_nan_start_raises(self):
        with pytest.raises(ValueError):
            self._valid(start_jd=float('nan'))

    def test_yogini_system_accepted(self):
        p = self._valid(system='yogini', lord='Mangala')
        assert p.system == 'yogini'


# ===========================================================================
# 14. Phase 4 — Policy guards
# ===========================================================================

class TestPolicyGuards:

    def test_ashtottari_invalid_year_basis_raises(self):
        with pytest.raises(ValueError, match="year_basis"):
            AshtottariPolicy(year_basis='stone_year')

    def test_ashtottari_empty_ayanamsa_raises(self):
        with pytest.raises(ValueError, match="ayanamsa"):
            AshtottariPolicy(ayanamsa_system='')

    def test_yogini_invalid_year_basis_raises(self):
        with pytest.raises(ValueError, match="year_basis"):
            YoginiPolicy(year_basis='bad')

    def test_yogini_empty_ayanamsa_raises(self):
        with pytest.raises(ValueError, match="ayanamsa"):
            YoginiPolicy(ayanamsa_system='')

    def test_ashtottari_default_policy_accepted(self):
        p = AshtottariPolicy()
        assert p.year_basis == 'julian_365.25'

    def test_yogini_default_policy_accepted(self):
        p = YoginiPolicy()
        assert p.year_basis == 'julian_365.25'


# ===========================================================================
# 15. Phase 7 — alternate_period_profile
# ===========================================================================

class TestAlternatePeriodProfile:

    @pytest.fixture()
    def ashtottari_profile(self) -> AlternatePeriodProfile:
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        return alternate_period_profile(periods[0])

    def test_system_preserved(self, ashtottari_profile):
        assert ashtottari_profile.system == 'ashtottari'

    def test_level_preserved(self, ashtottari_profile):
        assert ashtottari_profile.level == 1

    def test_lord_preserved(self, ashtottari_profile):
        # First lord depends on Moon nakshatra; just confirm non-empty
        assert ashtottari_profile.lord in ASHTOTTARI_SEQUENCE

    def test_planet_equals_lord_for_ashtottari(self, ashtottari_profile):
        assert ashtottari_profile.planet == ashtottari_profile.lord

    def test_years_positive(self, ashtottari_profile):
        assert ashtottari_profile.years > 0.0

    def test_rahu_lord_is_node(self):
        # Force Moon to nakshatra that maps to Rahu lord
        # ASHTOTTARI_NAKSHATRA_LORD[6] = 'Rahu' (index 6 % 8 = 6 = Rahu)
        # nakshatra 6 = 6 × (360/27) ≈ 80°
        moon_lon = 6 * (360.0 / 27) + 1.0
        periods = ashtottari(moon_lon, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        # Find the Rahu period
        rahu_period = next((p for p in periods if p.lord == 'Rahu'), None)
        if rahu_period:
            profile = alternate_period_profile(rahu_period)
            assert profile.is_node_lord is True
            assert profile.is_luminary_lord is False

    def test_sun_lord_is_luminary(self):
        # ASHTOTTARI_NAKSHATRA_LORD[0] = 'Sun', nakshatra 0 = Ashwini (0–13.33°)
        periods = ashtottari(1.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        sun_period = next((p for p in periods if p.lord == 'Sun'), None)
        if sun_period:
            profile = alternate_period_profile(sun_period)
            assert profile.is_luminary_lord is True
            assert profile.is_node_lord is False

    def test_yogini_profile_planet_differs_from_lord(self):
        periods = yogini_dasha(0.0, _J2000, levels=1)
        # All Yogini lords map to different planet names
        for p in periods:
            profile = alternate_period_profile(p)
            assert profile.planet == YOGINI_PLANETS[profile.lord]

    def test_yogini_sankata_maps_to_rahu_node(self):
        periods = yogini_dasha(0.0, _J2000, levels=1)
        sankata = next((p for p in periods if p.lord == 'Sankata'), None)
        if sankata:
            profile = alternate_period_profile(sankata)
            assert profile.planet == 'Rahu'
            assert profile.is_node_lord is True


# ===========================================================================
# 16. Phase 8 — alternate_sequence_profile
# ===========================================================================

class TestAlternateSequenceProfile:

    @pytest.fixture()
    def ashtottari_seq(self) -> AlternateDashaSequenceProfile:
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        return alternate_sequence_profile(periods)

    @pytest.fixture()
    def yogini_seq(self) -> AlternateDashaSequenceProfile:
        periods = yogini_dasha(0.0, _J2000, levels=1)
        return alternate_sequence_profile(periods)

    def test_system_is_ashtottari(self, ashtottari_seq):
        assert ashtottari_seq.system == 'ashtottari'

    def test_total_years_is_108(self, ashtottari_seq):
        assert ashtottari_seq.total_years == 108

    def test_mahadasha_count_matches_profiles(self, ashtottari_seq):
        assert ashtottari_seq.mahadasha_count == len(ashtottari_seq.profiles)

    def test_profiles_count_ge_8(self, ashtottari_seq):
        assert ashtottari_seq.mahadasha_count >= 8

    def test_yogini_total_years_is_36(self, yogini_seq):
        assert yogini_seq.total_years == 36

    def test_yogini_system_label(self, yogini_seq):
        assert yogini_seq.system == 'yogini'

    def test_empty_periods_raises(self):
        with pytest.raises(ValueError):
            alternate_sequence_profile([])

    def test_mismatched_count_raises(self):
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        profiles = [alternate_period_profile(p) for p in periods]
        with pytest.raises(ValueError, match="mahadasha_count"):
            AlternateDashaSequenceProfile(
                system='ashtottari',
                total_years=108,
                mahadasha_count=999,   # wrong
                profiles=profiles,
            )


# ===========================================================================
# 17. Phase 10 — validate_alternate_dasha_output
# ===========================================================================

class TestValidateAlternateDashaOutput:

    def test_valid_ashtottari_passes(self):
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        validate_alternate_dasha_output(periods)  # must not raise

    def test_valid_yogini_passes(self):
        periods = yogini_dasha(0.0, _J2000, levels=1)
        validate_alternate_dasha_output(periods)

    def test_empty_list_raises(self):
        with pytest.raises(ValueError):
            validate_alternate_dasha_output([])

    def test_invalid_lord_detected(self):
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        p = periods[0]
        bad = AlternateDashaPeriod(
            system='ashtottari',
            level=1,
            lord='Uranus',   # not a valid Ashtottari lord
            start_jd=p.start_jd,
            end_jd=p.end_jd,
            sub=[],
        )
        bad_list = [bad] + list(periods[1:])
        with pytest.raises(ValueError, match="lord"):
            validate_alternate_dasha_output(bad_list)

    def test_gap_between_periods_detected(self):
        periods = ashtottari(0.0, _J2000, levels=1,
                             policy=AshtottariPolicy(bypass_eligibility=True))
        p0, p1 = periods[0], periods[1]
        # Build p0 ending early → creates a gap with p1
        early_end = AlternateDashaPeriod(
            system=p0.system, level=p0.level, lord=p0.lord,
            start_jd=p0.start_jd, end_jd=p0.end_jd - 10.0, sub=[],
        )
        with pytest.raises(ValueError, match="Gap"):
            validate_alternate_dasha_output([early_end, p1] + list(periods[2:]))

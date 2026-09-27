"""
Unit tests for moira.dasha_systems.

Coverage
--------
1. BPHS chapter 46 Ashtottari 28-place lord allocation and balance.
2. BPHS chapter 46 Yogini add-three/remainder-eight allocation and balance.
3. Einstein Jyeshtha oracle: Mercury and Bhadrika.
4. Structural output, cycle span, JD continuity, and year-basis policy.
5. Nested sub-period structural behavior.
6. Eligibility-policy boundary and error handling.
7. Public surface and vessel invariants.

Primary source authority: Brihat Parashara Hora Shastra, chapter 46,
verses 17–23 (Ashtottari) and 195–200 (Yogini).  Sanskrit witness:
https://sanskritdocuments.org/doc_z_misc_sociology_astrology/par4650.html
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
_NAKSHATRA_SPAN = 40.0 / 3.0
_ABHIJIT_START = 270.0 + 6.0 + 40.0 / 60.0
_ABHIJIT_END = 270.0 + 10.0 + 53.0 / 60.0 + 20.0 / 3600.0


# The BPHS 46.17–22 sequence, represented by a midpoint in each of its 28
# counting places.  The three irregular midpoints apply the separately named
# traditional Abhijit boundary convention used by the engine.
_ASHTOTTARI_SOURCE_CASES = [
    ("Ardra", 5.5 * _NAKSHATRA_SPAN, "Sun", 0, 4),
    ("Punarvasu", 6.5 * _NAKSHATRA_SPAN, "Sun", 1, 4),
    ("Pushya", 7.5 * _NAKSHATRA_SPAN, "Sun", 2, 4),
    ("Ashlesha", 8.5 * _NAKSHATRA_SPAN, "Sun", 3, 4),
    ("Magha", 9.5 * _NAKSHATRA_SPAN, "Moon", 0, 3),
    ("Purva Phalguni", 10.5 * _NAKSHATRA_SPAN, "Moon", 1, 3),
    ("Uttara Phalguni", 11.5 * _NAKSHATRA_SPAN, "Moon", 2, 3),
    ("Hasta", 12.5 * _NAKSHATRA_SPAN, "Mars", 0, 4),
    ("Chitra", 13.5 * _NAKSHATRA_SPAN, "Mars", 1, 4),
    ("Swati", 14.5 * _NAKSHATRA_SPAN, "Mars", 2, 4),
    ("Vishakha", 15.5 * _NAKSHATRA_SPAN, "Mars", 3, 4),
    ("Anuradha", 16.5 * _NAKSHATRA_SPAN, "Mercury", 0, 3),
    ("Jyeshtha", 17.5 * _NAKSHATRA_SPAN, "Mercury", 1, 3),
    ("Mula", 18.5 * _NAKSHATRA_SPAN, "Mercury", 2, 3),
    ("Purva Ashadha", 19.5 * _NAKSHATRA_SPAN, "Saturn", 0, 4),
    (
        "Uttara Ashadha",
        (20.0 * _NAKSHATRA_SPAN + _ABHIJIT_START) / 2.0,
        "Saturn",
        1,
        4,
    ),
    ("Abhijit", (_ABHIJIT_START + _ABHIJIT_END) / 2.0, "Saturn", 2, 4),
    (
        "Shravana",
        (_ABHIJIT_END + 22.0 * _NAKSHATRA_SPAN) / 2.0,
        "Saturn",
        3,
        4,
    ),
    ("Dhanishtha", 22.5 * _NAKSHATRA_SPAN, "Jupiter", 0, 3),
    ("Shatabhisha", 23.5 * _NAKSHATRA_SPAN, "Jupiter", 1, 3),
    ("Purva Bhadrapada", 24.5 * _NAKSHATRA_SPAN, "Jupiter", 2, 3),
    ("Uttara Bhadrapada", 25.5 * _NAKSHATRA_SPAN, "Rahu", 0, 4),
    ("Revati", 26.5 * _NAKSHATRA_SPAN, "Rahu", 1, 4),
    ("Ashwini", 0.5 * _NAKSHATRA_SPAN, "Rahu", 2, 4),
    ("Bharani", 1.5 * _NAKSHATRA_SPAN, "Rahu", 3, 4),
    ("Krittika", 2.5 * _NAKSHATRA_SPAN, "Venus", 0, 3),
    ("Rohini", 3.5 * _NAKSHATRA_SPAN, "Venus", 1, 3),
    ("Mrigashira", 4.5 * _NAKSHATRA_SPAN, "Venus", 2, 3),
]


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

    def test_ashtottari_ordinary_nakshatra_projection_matches_bphs_groups(self):
        assert ASHTOTTARI_NAKSHATRA_LORD == [
            "Rahu", "Rahu", "Venus", "Venus", "Venus",
            "Sun", "Sun", "Sun", "Sun",
            "Moon", "Moon", "Moon",
            "Mars", "Mars", "Mars", "Mars",
            "Mercury", "Mercury", "Mercury",
            "Saturn", "Saturn", "Saturn",
            "Jupiter", "Jupiter", "Jupiter",
            "Rahu", "Rahu",
        ]

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
# BPHS chapter 46 source-derived entry rules
# ===========================================================================

class TestPrimarySourceEntryRules:

    @pytest.mark.parametrize(
        "name,sidereal_longitude,expected_lord,segment_ordinal,group_size",
        _ASHTOTTARI_SOURCE_CASES,
        ids=[case[0] for case in _ASHTOTTARI_SOURCE_CASES],
    )
    def test_ashtottari_all_28_counting_places_and_balances(
        self,
        monkeypatch,
        name,
        sidereal_longitude,
        expected_lord,
        segment_ordinal,
        group_size,
    ):
        monkeypatch.setattr(
            "moira.sidereal.tropical_to_sidereal",
            lambda *args, **kwargs: sidereal_longitude,
        )

        first = ashtottari(
            0.0,
            _J2000,
            levels=1,
            policy=AshtottariPolicy(bypass_eligibility=True),
        )[0]

        expected_years = ASHTOTTARI_YEARS[expected_lord] * (
            1.0 - (segment_ordinal + 0.5) / group_size
        )
        actual_years = (first.end_jd - first.start_jd) / _JULIAN_YEAR
        assert first.lord == expected_lord, name
        assert actual_years == pytest.approx(expected_years, abs=1e-11), name

    def test_yogini_all_27_birth_nakshatras_use_add_three_rule(self, monkeypatch):
        for nakshatra_index in range(27):
            sidereal_longitude = (nakshatra_index + 0.5) * _NAKSHATRA_SPAN
            monkeypatch.setattr(
                "moira.sidereal.tropical_to_sidereal",
                lambda *args, value=sidereal_longitude, **kwargs: value,
            )

            first = yogini_dasha(0.0, _J2000, levels=1)[0]
            expected_lord = YOGINI_SEQUENCE[(nakshatra_index + 3) % 8]
            actual_years = (first.end_jd - first.start_jd) / _JULIAN_YEAR

            assert first.lord == expected_lord
            assert actual_years == pytest.approx(
                YOGINI_YEARS[expected_lord] / 2.0,
                abs=1e-11,
            )

    def test_einstein_jyeshtha_starts_mercury_and_bhadrika(self):
        # 1879-03-14 10:50 UTC, Ulm.  The fixed tropical Moon longitude is
        # 254.52591156 degrees; Moira's Lahiri conversion places it 42.6606%
        # through Jyeshtha.  The value is a fixed Moira DE441 result that was
        # corroborated against JPL Horizons during source research; this
        # kernel-free unit test does not itself perform that external query.
        natal_jd = 2407422.95138889
        moon_tropical_longitude = 254.52591156

        ashtottari_first = ashtottari(
            moon_tropical_longitude,
            natal_jd,
            levels=1,
            policy=AshtottariPolicy(bypass_eligibility=True),
        )[0]
        yogini_first = yogini_dasha(
            moon_tropical_longitude,
            natal_jd,
            levels=1,
        )[0]

        assert ashtottari_first.lord == "Mercury"
        assert ashtottari_first.years == pytest.approx(8.9158985291, abs=1e-9)
        assert yogini_first.lord == "Bhadrika"
        assert yogini_first.years == pytest.approx(2.8669692904, abs=1e-9)


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
# Shared nakshatra boundary ownership
# ===========================================================================

class TestSharedNakshatraBoundaryOwnership:

    @pytest.mark.parametrize("system", ("ashtottari", "yogini"))
    def test_first_predecessor_of_internal_boundary_belongs_to_following_sector(
        self,
        monkeypatch,
        system,
    ):
        boundary = 40.0 / 3.0
        predecessor = math.nextafter(boundary, -math.inf)
        monkeypatch.setattr(
            "moira.sidereal.tropical_to_sidereal",
            lambda *args, **kwargs: predecessor,
        )

        if system == "ashtottari":
            periods = ashtottari(
                0.0,
                _J2000,
                levels=1,
                policy=AshtottariPolicy(bypass_eligibility=True),
            )
            expected_lord = ASHTOTTARI_NAKSHATRA_LORD[1]
            expected_years = 3.0
        else:
            periods = yogini_dasha(0.0, _J2000, levels=1)
            expected_lord = YOGINI_SEQUENCE[(1 + 3) % 8]
            expected_years = float(YOGINI_YEARS[expected_lord])

        assert periods[0].lord == expected_lord
        assert periods[0].start_jd == _J2000
        assert periods[0].years == pytest.approx(expected_years, abs=1e-12)

    @pytest.mark.parametrize(
        "boundary,expected_remaining_years",
        [
            (_ABHIJIT_START, 5.0),
            (_ABHIJIT_END, 2.5),
        ],
    )
    def test_abhijit_boundary_and_first_predecessor_share_forward_ownership(
        self,
        monkeypatch,
        boundary,
        expected_remaining_years,
    ):
        for longitude in (boundary, math.nextafter(boundary, -math.inf)):
            monkeypatch.setattr(
                "moira.sidereal.tropical_to_sidereal",
                lambda *args, value=longitude, **kwargs: value,
            )
            first = ashtottari(
                0.0,
                _J2000,
                levels=1,
                policy=AshtottariPolicy(bypass_eligibility=True),
            )[0]

            assert first.lord == "Saturn"
            assert first.years == pytest.approx(
                expected_remaining_years,
                abs=1e-12,
            )


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
        # A complete sequence always includes the Rahu period.
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
        # A complete sequence always includes the Sun period.
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

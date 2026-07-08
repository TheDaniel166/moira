"""
Unit tests for moira.upagrahas.

Coverage
--------
1. Sun-derived group (BPHS 3.61-64): the exact chain against Santhanam's
   worked example (Sun 40°), the verse's own self-check identity
   (Upaketu + 30° ≡ Sun) across a longitude sweep, and the 180°-pair
   invariants (Dhuma-Indrachapa, Vyatipata-Parivesha).
2. Kalavela group (BPHS 3.66-70, kernel-backed): day/night arc selection,
   weekday lord tables (Saturday day → Saturn part 1; night start from
   the 5th weekday lord), portion-point and lord-sequence policies,
   Mandi alias vs Kalidasa-table modes.
3. Policy validation.
"""
import pytest

from moira.upagrahas import (
    UpagrahaPolicy,
    kalavela_upagrahas,
    sun_based_upagrahas,
)


# ===========================================================================
# 1. Sun-derived upagrahas (exact arithmetic)
# ===========================================================================

class TestSunBasedUpagrahas:

    def test_santhanam_worked_example_sun_40(self):
        u = sun_based_upagrahas(40.0)
        assert u.dhuma == pytest.approx(173.0 + 20.0 / 60.0)
        assert u.vyatipata == pytest.approx(186.0 + 40.0 / 60.0)
        assert u.parivesha == pytest.approx(6.0 + 40.0 / 60.0)
        assert u.indrachapa == pytest.approx(353.0 + 20.0 / 60.0)
        assert u.upaketu == pytest.approx(10.0)

    def test_bphs_364_self_check_across_sweep(self):
        # The verse states its own identity: Upaketu + 30° ≡ Sun.
        for sun in (0.0, 17.5, 133.33, 210.0, 359.9):
            u = sun_based_upagrahas(sun)
            assert ((u.upaketu + 30.0) % 360.0) == pytest.approx(
                sun % 360.0, abs=1e-9)

    def test_opposition_pairs(self):
        # Dhuma-Indrachapa and Vyatipata-Parivesha are 180° apart.
        u = sun_based_upagrahas(77.0)
        assert abs((u.dhuma - u.indrachapa) % 360.0) == pytest.approx(180.0)
        assert abs((u.vyatipata - u.parivesha) % 360.0) == pytest.approx(180.0)

    def test_closed_forms(self):
        # Vyatipata = 226°40' − Sun; Parivesha = 46°40' − Sun (mod 360).
        for sun in (10.0, 100.0, 250.0):
            u = sun_based_upagrahas(sun)
            assert u.vyatipata == pytest.approx(
                (226.0 + 40.0 / 60.0 - sun) % 360.0)
            assert u.parivesha == pytest.approx(
                (46.0 + 40.0 / 60.0 - sun) % 360.0)


# ===========================================================================
# 2. Kalavela upagrahas (kernel-backed)
# ===========================================================================

_DELHI = (28.6139, 77.2090)
_JD_SATURDAY_DAY = 2451544.75     # 2000-01-01 06:00 UT — Delhi daytime
_JD_SATURDAY_NIGHT = 2451545.35   # same Vedic Saturday, night


@pytest.mark.requires_ephemeris
class TestKalavelaUpagrahas:

    @pytest.fixture(scope='class')
    def day_result(self, moira_engine):
        from moira.facade import use_reader_override
        with use_reader_override(moira_engine._reader_obj):
            return kalavela_upagrahas(_JD_SATURDAY_DAY, *_DELHI)

    def test_day_birth_detection_and_weekday(self, day_result):
        assert day_result.is_day_birth is True
        assert day_result.weekday_index == 6   # Saturday

    def test_saturday_day_gulika_is_first_part(self, day_result):
        # Saturday day lord = Saturn -> Saturn's portion is part 1, so
        # Gulika (beginning policy) sits at the arc start — matching the
        # classical Saturday Gulika-kalam anchor.
        g = day_result.upagrahas['Gulika']
        assert g.part_index == 1
        assert g.defining_jd == pytest.approx(day_result.arc_start_jd)

    def test_all_five_kalavelas_present_plus_mandi(self, day_result):
        assert set(day_result.upagrahas) == {
            'Gulika', 'Kala', 'Mrityu', 'Ardhaprahara', 'Yamaghantaka',
            'Mandi',
        }

    def test_part_indices_follow_weekday_table(self, day_result):
        # Saturday day: Sat=1, Sun=2, Moon=3, Mars=4, Merc=5, Jup=6.
        ups = day_result.upagrahas
        assert ups['Kala'].part_index == 2          # Sun's portion
        assert ups['Mrityu'].part_index == 4        # Mars's
        assert ups['Ardhaprahara'].part_index == 5  # Mercury's
        assert ups['Yamaghantaka'].part_index == 6  # Jupiter's

    def test_mandi_aliases_gulika_by_default(self, day_result):
        assert (day_result.upagrahas['Mandi'].sidereal_longitude
                == day_result.upagrahas['Gulika'].sidereal_longitude)

    def test_longitudes_in_range(self, day_result):
        for up in day_result.upagrahas.values():
            assert 0.0 <= up.sidereal_longitude < 360.0
            assert 0.0 <= up.tropical_longitude < 360.0

    def test_night_birth_uses_fifth_weekday_lord(self, moira_engine):
        from moira.facade import use_reader_override
        with use_reader_override(moira_engine._reader_obj):
            res = kalavela_upagrahas(_JD_SATURDAY_NIGHT, *_DELHI)
        assert res.is_day_birth is False
        # Saturday night start lord = 5th from Saturday = Wednesday's
        # Mercury; cycle Merc, Jup, Ven, Sat -> Gulika part 4.
        assert res.upagrahas['Gulika'].part_index == 4

    def test_portion_point_policy_moves_the_instant(self, moira_engine):
        from moira.facade import use_reader_override
        with use_reader_override(moira_engine._reader_obj):
            beg = kalavela_upagrahas(_JD_SATURDAY_DAY, *_DELHI)
            end = kalavela_upagrahas(
                _JD_SATURDAY_DAY, *_DELHI,
                policy=UpagrahaPolicy(portion_point='end'))
        part = (beg.arc_end_jd - beg.arc_start_jd) / 8.0
        assert end.upagrahas['Gulika'].defining_jd == pytest.approx(
            beg.upagrahas['Gulika'].defining_jd + part)

    def test_lordless_after_saturn_shifts_kala(self, moira_engine):
        from moira.facade import use_reader_override
        with use_reader_override(moira_engine._reader_obj):
            res = kalavela_upagrahas(
                _JD_SATURDAY_DAY, *_DELHI,
                policy=UpagrahaPolicy(lord_sequence='lordless_after_saturn'))
        # Saturday: Sat part 1, lordless part 2, Sun part 3.
        assert res.upagrahas['Gulika'].part_index == 1
        assert res.upagrahas['Kala'].part_index == 3

    def test_kalidasa_mandi_is_distinct(self, moira_engine):
        from moira.facade import use_reader_override
        with use_reader_override(moira_engine._reader_obj):
            res = kalavela_upagrahas(
                _JD_SATURDAY_DAY, *_DELHI,
                policy=UpagrahaPolicy(mandi_mode='distinct_kalidasa_table'))
        mandi = res.upagrahas['Mandi']
        assert mandi.part_index is None
        # Saturday day table: 2 ghatis of 30 -> arc_start + D/15.
        duration = res.arc_end_jd - res.arc_start_jd
        assert mandi.defining_jd == pytest.approx(
            res.arc_start_jd + duration * (2.0 / 30.0))


# ===========================================================================
# 3. Policy validation
# ===========================================================================

class TestUpagrahaPolicy:

    def test_invalid_portion_point_raises(self):
        with pytest.raises(ValueError, match="portion_point"):
            UpagrahaPolicy(portion_point='quarter')

    def test_invalid_mandi_mode_raises(self):
        with pytest.raises(ValueError, match="mandi_mode"):
            UpagrahaPolicy(mandi_mode='same')

    def test_invalid_lord_sequence_raises(self):
        with pytest.raises(ValueError, match="lord_sequence"):
            UpagrahaPolicy(lord_sequence='reversed')

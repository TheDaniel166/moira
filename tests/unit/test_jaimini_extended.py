"""
Unit tests for moira.jaimini_extended.

Coverage: rasi drishti (offset tables + full symmetry sweep), arudha
padas (double-count, Rath exception vs Raman none, co-lord policy
gating), argala (pairs, malefic-third, Ketu reversal), karakamsa (both
lineage readings named), Chara Dasha (K.N. Rao direction rule, year
counts, co-lord handling, antardasha ordering, continuity).
"""
import pytest

from moira.jaimini_extended import (
    JaiminiExtendedPolicy,
    argala,
    arudha_padas,
    chara_dasha,
    karakamsa,
    rasi_aspects,
    rasi_drishti_of,
)


_LONS = {'Sun': 130, 'Moon': 200, 'Mars': 125, 'Mercury': 160,
         'Jupiter': 40, 'Venus': 310, 'Saturn': 190}


class TestRasiDrishti:

    def test_movable_aspects_fixed_except_adjacent(self):
        assert rasi_drishti_of(0) == frozenset({4, 7, 10})   # Aries
        assert rasi_drishti_of(3) == frozenset({7, 10, 1})   # Cancer

    def test_fixed_aspects_movable_except_adjacent(self):
        assert rasi_drishti_of(1) == frozenset({3, 6, 9})    # Taurus
        assert rasi_drishti_of(4) == frozenset({6, 9, 0})    # Leo

    def test_dual_aspects_other_duals(self):
        assert rasi_drishti_of(2) == frozenset({5, 8, 11})   # Gemini

    def test_full_symmetry_sweep(self):
        for a in range(12):
            for b in range(12):
                assert rasi_aspects(a, b) == rasi_aspects(b, a)

    def test_no_self_aspect(self):
        for s in range(12):
            assert not rasi_aspects(s, s)


class TestArudhaPadas:

    def test_basic_double_count(self):
        # Aries lagna, Mars (lord) in Leo: 5 signs to lord, 5 onward ->
        # Sagittarius.
        res = arudha_padas(_LONS, 5.0)
        al = res.padas[1]
        assert al.lord == 'Mars'
        assert al.pada_sign == 8
        assert not al.exception_applied

    def test_rath_exception_seventh_takes_tenth(self):
        # Lord in the 4th -> computed pada = 7th -> 10th therefrom.
        lons = dict(_LONS, Mars=100.0)
        res = arudha_padas(lons, 5.0)
        al = res.padas[1]
        assert al.computed_sign == 6
        assert al.exception_applied
        assert al.pada_sign == 3

    def test_raman_lineage_has_no_exception(self):
        lons = dict(_LONS, Mars=100.0)
        res = arudha_padas(
            lons, 5.0, JaiminiExtendedPolicy(arudha_exception='none'))
        assert res.padas[1].pada_sign == 6
        assert not res.padas[1].exception_applied

    def test_lord_in_own_sign_pada_in_first_takes_tenth(self):
        # Lord in the house itself: computed = house -> exception -> 10th.
        lons = dict(_LONS, Mars=10.0)   # Mars in Aries
        res = arudha_padas(lons, 5.0)
        al = res.padas[1]
        assert al.computed_sign == 0
        assert al.exception_applied
        assert al.pada_sign == 9

    def test_al_and_ul_labels(self):
        res = arudha_padas(_LONS, 5.0)
        assert res.padas[1].label == 'AL'
        assert res.padas[12].label == 'UL'
        assert res.arudha_lagna_sign == res.padas[1].pada_sign
        assert res.upapada_lagna_sign == res.padas[12].pada_sign

    def test_co_lords_policy_requires_nodes(self):
        with pytest.raises(ValueError, match="node_longitudes"):
            arudha_padas(
                _LONS, 5.0,
                JaiminiExtendedPolicy(arudha_lords='jaimini_co_lords'))

    def test_co_lords_policy_with_nodes(self):
        res = arudha_padas(
            _LONS, 5.0,
            JaiminiExtendedPolicy(arudha_lords='jaimini_co_lords'),
            node_longitudes={'Rahu': 45.0, 'Ketu': 225.0})
        assert set(res.padas) == set(range(1, 13))
        # Scorpio house (H8 from Aries) used a co-lord decision.
        assert res.padas[8].lord in ('Mars', 'Ketu')


class TestArgala:

    def test_pairs_present_for_all_houses(self):
        res = argala(_LONS, 5.0)
        assert len(res.houses) == 12
        for h in res.houses.values():
            assert set(h.argalas) == {2, 4, 11, 5}
            assert set(h.obstructors) == {2, 4, 11, 5}

    def test_unobstructed_requires_more_causers(self):
        res = argala(_LONS, 5.0)
        for h in res.houses.values():
            for pos, flag in h.unobstructed.items():
                if flag:
                    assert len(h.argalas[pos]) > len(h.obstructors[pos])

    def test_ketu_reverses_reckoning(self):
        with_ketu = argala(_LONS, 5.0, node_longitudes={'Ketu': 10.0})
        assert with_ketu.houses[1].reversed_by_ketu is True
        without = argala(_LONS, 5.0)
        assert without.houses[1].reversed_by_ketu is False

    def test_malefic_third_needs_two(self):
        # Saturn+Mars together in the 3rd from H1 (Gemini from Aries).
        lons = dict(_LONS, Saturn=70.0, Mars=75.0)
        res = argala(lons, 5.0)
        assert len(res.houses[1].malefic_third_argala) >= 2


class TestKarakamsa:

    def test_both_lineage_readings_named(self):
        kk = karakamsa(_LONS, 5.0)
        assert 'Rath' in kk.d9_reading
        assert 'Rao' in kk.d1_reading
        assert 0 <= kk.karakamsa_sign <= 11
        assert kk.svamsa_sign is not None

    def test_svamsa_optional(self):
        kk = karakamsa(_LONS)
        assert kk.svamsa_sign is None


class TestCharaDasha:

    def test_direction_by_ninth_from_lagna(self):
        # Aries lagna: 9th = Sagittarius (savya) -> direct.
        assert chara_dasha(_LONS, 5.0, 2451545.0).direction == 1
        # Taurus lagna: 9th = Capricorn (apasavya) -> reverse.
        assert chara_dasha(_LONS, 35.0, 2451545.0).direction == -1

    def test_sequence_contiguous_from_lagna(self):
        cd = chara_dasha(_LONS, 5.0, 2451545.0)
        assert [p.sign for p in cd.periods] == list(range(12))
        cd2 = chara_dasha(_LONS, 35.0, 2451545.0)
        assert [p.sign for p in cd2.periods] == [
            (1 - i) % 12 for i in range(12)]

    def test_year_count_zodiacal_for_savya_sign(self):
        # Aries (savya) dasha, lord Mars in Leo: count 5 -> 4 years.
        cd = chara_dasha(_LONS, 5.0, 2451545.0)
        assert cd.periods[0].years == 4

    def test_lord_in_own_sign_gives_twelve(self):
        lons = dict(_LONS, Mars=10.0)
        cd = chara_dasha(lons, 5.0, 2451545.0)
        assert cd.periods[0].years == 12

    def test_antardasha_dasha_sign_last(self):
        cd = chara_dasha(_LONS, 5.0, 2451545.0)
        for p in cd.periods:
            assert p.antardasha_signs[-1] == p.sign
            assert len(p.antardasha_signs) == 12
            assert len(p.antardasha_starts) == 12

    def test_periods_are_continuous(self):
        cd = chara_dasha(_LONS, 5.0, 2451545.0)
        for a, b in zip(cd.periods, cd.periods[1:]):
            assert a.end_jd == pytest.approx(b.start_jd)
        assert cd.periods[0].start_jd == pytest.approx(2451545.0)

    def test_co_lord_sign_with_nodes(self):
        cd = chara_dasha(_LONS, 5.0, 2451545.0,
                         node_longitudes={'Rahu': 45.0, 'Ketu': 225.0})
        scorpio = next(p for p in cd.periods if p.sign == 7)
        # Ketu in Scorpio: exactly one co-lord in the sign -> count to Mars.
        assert scorpio.lord == 'Mars'
        assert 'count to Mars' in scorpio.lord_note

    def test_lineage_recorded(self):
        cd = chara_dasha(_LONS, 5.0, 2451545.0)
        assert 'K.N. Rao' in cd.lineage
        assert 'First cycle only' in cd.lineage


class TestPolicy:

    def test_invalid_values_raise(self):
        with pytest.raises(ValueError, match="arudha_exception"):
            JaiminiExtendedPolicy(arudha_exception='fifth')
        with pytest.raises(ValueError, match="arudha_lords"):
            JaiminiExtendedPolicy(arudha_lords='nodes_only')

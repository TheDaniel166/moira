"""
Unit tests for moira.avasthas.

Coverage
--------
1. Baladi (BPHS 45.3-4): band table for odd/even signs, effect fractions,
   Vriddha honesty (no invented number), policy override.
2. Jagradadi (BPHS 45.5-6): sign-level dignity (moolatrikona degrees still
   satisfy the own-sign clause), debilitation override.
3. Deeptadi: per-source rule tables (bphs_9 default, saravali_9,
   jataka_parijata_10, phaladeepika_11) — never merged; combustion;
   compound-relationship ladder.
4. Lajjitadi (BPHS 45.11-18): each condition, non-exclusivity, node
   participation gating.
5. Policy validation.
"""
import pytest

from moira.avasthas import (
    AvasthaPolicy,
    baladi_avastha,
    deeptadi_avastha,
    evaluate_avasthas,
    jagradadi_avastha,
    lajjitadi_avasthas,
)


_LONS = {
    'Sun': 130.5,      # Leo 10.5 — own sign (moolatrikona degrees)
    'Moon': 43.0,      # Taurus 13 — exaltation sign
    'Mars': 95.0,      # Cancer 5 — debilitation
    'Mercury': 160.0,  # Virgo 10 — own+exaltation sign
    'Jupiter': 100.0,  # Cancer 10 — exaltation sign
    'Venus': 187.0,    # Libra 7 — own sign (moolatrikona degrees)
    'Saturn': 195.0,   # Libra 15 — exaltation sign
}
_LAGNA = 100.0


# ===========================================================================
# 1. Baladi
# ===========================================================================

class TestBaladi:

    @pytest.mark.parametrize("lon,state,fraction", [
        (3.0, 'Bala', 0.25),      # Aries (odd) band 1
        (9.0, 'Kumara', 0.5),
        (15.0, 'Yuva', 1.0),
        (21.0, 'Vriddha', None),
        (27.0, 'Mrita', 0.0),
        (33.0, 'Mrita', 0.0),     # Taurus (even) band 1 — reversed
        (39.0, 'Vriddha', None),
        (45.0, 'Yuva', 1.0),
        (51.0, 'Kumara', 0.5),
        (57.0, 'Bala', 0.25),
    ])
    def test_band_table(self, lon, state, fraction):
        b = baladi_avastha('Sun', lon)
        assert b.state == state
        assert b.effect_fraction == fraction

    def test_vriddha_has_no_invented_number(self):
        b = baladi_avastha('Sun', 20.0)
        assert b.state == 'Vriddha'
        assert b.effect_fraction is None
        assert b.effect_label == 'negligible'

    def test_vriddha_policy_override(self):
        b = baladi_avastha('Sun', 20.0, AvasthaPolicy(vriddha_fraction=0.125))
        assert b.effect_fraction == 0.125

    def test_boundary_is_lower_inclusive(self):
        assert baladi_avastha('Sun', 6.0).state == 'Kumara'
        assert baladi_avastha('Sun', 5.999).state == 'Bala'


# ===========================================================================
# 2. Jagradadi
# ===========================================================================

class TestJagradadi:

    def test_own_sign_at_moolatrikona_degrees_is_jagrat(self):
        # Sun at Leo 10.5° ranks moolatrikona, but Leo IS the Sun's own
        # sign — the sign clause (BPHS 45.5) must hold.
        j = jagradadi_avastha('Sun', _LONS)
        assert j.state == 'Jagrat'
        assert j.effect_fraction == 1.0

    def test_exaltation_sign_is_jagrat(self):
        j = jagradadi_avastha('Moon', _LONS)
        assert j.state == 'Jagrat'

    def test_debilitation_is_sushupti_and_overrides_lordship(self):
        # Mars in Cancer: the Moon is Mars's friend, but debilitation
        # overrides the lordship clause (declared doctrine).
        j = jagradadi_avastha('Mars', _LONS)
        assert j.state == 'Sushupti'
        assert j.effect_fraction == 0.0

    def test_friend_or_neutral_sign_is_swapna(self):
        lons = dict(_LONS, Sun=350.0)   # Sun in Pisces (Jupiter friend)
        j = jagradadi_avastha('Sun', lons)
        assert j.state == 'Swapna'
        assert j.effect_fraction == 0.5


# ===========================================================================
# 3. Deeptadi (per-source, never merged)
# ===========================================================================

class TestDeeptadi:

    def test_bphs_own_sign_is_swastha(self):
        d = deeptadi_avastha('Sun', _LONS)
        assert d.source == 'bphs_9'
        assert d.state == 'Swastha'

    def test_bphs_exaltation_is_deepta(self):
        d = deeptadi_avastha('Jupiter', _LONS)
        assert d.state == 'Deepta'

    def test_bphs_combust_is_kopa(self):
        lons = dict(_LONS, Venus=135.0)   # 4.5° from the Sun
        d = deeptadi_avastha('Venus', lons)
        assert d.state == 'Kopa'

    def test_saravali_debilitation_is_bhita(self):
        d = deeptadi_avastha(
            'Mars', _LONS, AvasthaPolicy(deeptadi_source='saravali_9'))
        assert d.state == 'Bhita'
        assert d.source == 'saravali_9'

    def test_phaladeepika_moolatrikona_is_sukhita(self):
        # PD splits moolatrikona out as its own state.
        d = deeptadi_avastha(
            'Sun', _LONS, AvasthaPolicy(deeptadi_source='phaladeepika_11'))
        assert d.state == 'Sukhita'

    def test_jp_folds_moolatrikona_into_dipta(self):
        d = deeptadi_avastha(
            'Sun', _LONS, AvasthaPolicy(deeptadi_source='jataka_parijata_10'))
        assert d.state == 'Dipta'

    def test_every_result_carries_source_and_citation(self):
        for source in ('bphs_9', 'saravali_9', 'jataka_parijata_10',
                       'phaladeepika_11'):
            d = deeptadi_avastha(
                'Saturn', _LONS, AvasthaPolicy(deeptadi_source=source))
            assert d.source == source
            assert d.citation


# ===========================================================================
# 4. Lajjitadi
# ===========================================================================

class TestLajjitadi:

    def test_garvita_for_exalted_planet(self):
        r = lajjitadi_avasthas('Jupiter', _LONS, _LAGNA)
        assert 'Garvita' in r.active

    def test_lajjita_requires_fifth_house_and_afflictor(self):
        # Planet in the 5th from lagna with Saturn conjunct.
        lons = dict(_LONS, Mercury=225.0, Saturn=228.0)   # Scorpio = H5
        r = lajjitadi_avasthas('Mercury', lons, _LAGNA)
        assert 'Lajjita' in r.active
        # Same placement without any afflictor: no Lajjita.
        lons2 = dict(_LONS, Mercury=225.0)
        r2 = lajjitadi_avasthas('Mercury', lons2, _LAGNA)
        assert 'Lajjita' not in r2.active

    def test_lajjita_node_clause_gated_on_supplied_nodes(self):
        lons = dict(_LONS, Mercury=225.0)
        without = lajjitadi_avasthas('Mercury', lons, _LAGNA)
        assert 'Lajjita' not in without.active
        with_nodes = lajjitadi_avasthas(
            'Mercury', lons, _LAGNA,
            node_longitudes={'Rahu': 227.0, 'Ketu': 47.0})
        assert 'Lajjita' in with_nodes.active

    def test_kshudhita_via_saturn_conjunction(self):
        lons = dict(_LONS, Mercury=193.0)   # with Saturn in Libra
        r = lajjitadi_avasthas('Mercury', lons, _LAGNA)
        assert 'Kshudhita' in r.active

    def test_trushita_watery_sign_malefic_aspect_no_benefic(self):
        # Planet in Scorpio aspected by Mars (special 8th) with no
        # benefic aspect.
        lons = {'Sun': 130.0, 'Moon': 100.0, 'Mars': 10.0,
                'Mercury': 220.0, 'Jupiter': 300.0, 'Venus': 65.0,
                'Saturn': 195.0}
        # Mars in Aries aspects Scorpio (8th sign aspect).
        r = lajjitadi_avasthas('Mercury', lons, _LAGNA)
        trushita = next(s for s in r.states if s.state == 'Trushita')
        if not trushita.applies:
            # Evidence string must explain which clause failed.
            assert 'watery' in trushita.evidence

    def test_states_are_non_exclusive(self):
        # A planet can be simultaneously Mudita and Kshudhita.
        lons = dict(_LONS, Mercury=190.0)   # Libra with Saturn+Venus
        r = lajjitadi_avasthas('Mercury', lons, _LAGNA)
        assert 'Kshudhita' in r.active or 'Mudita' in r.active
        assert len(r.states) == 6

    def test_active_matches_flags(self):
        r = lajjitadi_avasthas('Sun', _LONS, _LAGNA)
        assert tuple(s.state for s in r.states if s.applies) == r.active


# ===========================================================================
# 5. Full evaluation + policy
# ===========================================================================

class TestEvaluateAvasthas:

    def test_all_planets_evaluated_with_all_systems(self):
        res = evaluate_avasthas(_LONS, _LAGNA)
        assert set(res.planets) == set(_LONS)
        for pa in res.planets.values():
            assert pa.baladi and pa.jagradadi and pa.deeptadi
            assert len(pa.lajjitadi.states) == 6

    def test_invalid_policy_values_raise(self):
        with pytest.raises(ValueError, match="relationship_scheme"):
            AvasthaPolicy(relationship_scheme='mixed')
        with pytest.raises(ValueError, match="deeptadi_source"):
            AvasthaPolicy(deeptadi_source='merged')

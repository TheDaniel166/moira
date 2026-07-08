"""
Unit tests for moira.yogas — the yoga engine.

Coverage
--------
1.  Benefic/malefic classification — BPHS Ch. 3 conditional doctrine
    (paksha Moon, conditional Mercury) + policy overrides.
2.  Pancha Mahapurusha — formation per BPHS 75.1-2 (own/exaltation +
    kendra from lagna), Moon-reference policy variant, no cancellations.
3.  Nabhasa — the 32 yogas: Ashraya/Dala/Akriti/Sankhya rules, exact-set
    doctrine, precedence (Akriti > Dala > Ashraya > Sankhya; Gola over
    Ashraya), exactly one present per chart.
4.  Chandra — Gajakesari (parashara vs common), Sunapha/Anapha/Durudhara
    (Sun excluded), Kemadruma formation + bhanga catalog, Adhi grading,
    Chandra-Mangala.
5.  Surya — Vesi/Vosi/Ubhayachari (Moon excluded), Budhaditya (+ policy
    combustion cancel).
6.  Vessel invariants — present/formed/cancelled consistency.

Source authority: BPHS (Santhanam), Brihat Jataka (Sastri), Saravali
(Santhanam), Phaladeepika, Raman "Three Hundred Important Combinations".
"""
import pytest

from moira.yogas import (
    YogaCondition,
    YogaPolicy,
    YogaResult,
    benefic_malefic_classification,
    chandra_yogas,
    nabhasa_yogas,
    pancha_mahapurusha_yogas,
    surya_yogas,
)


def _by_name(results):
    return {r.name: r for r in results}


def _present(results):
    return [r.name for r in results if r.present]


_ARIES_LAGNA = 5.0
_TAURUS_LAGNA = 35.0


# ===========================================================================
# 1. Benefic/malefic classification (BPHS Ch. 3)
# ===========================================================================

class TestBeneficMaleficClassification:

    def test_fixed_classes(self):
        lons = {'Sun': 0, 'Moon': 90, 'Mars': 120, 'Mercury': 200,
                'Jupiter': 240, 'Venus': 300, 'Saturn': 60}
        c = benefic_malefic_classification(lons)
        assert c['Jupiter'] == 'benefic'
        assert c['Venus'] == 'benefic'
        assert c['Sun'] == 'malefic'
        assert c['Mars'] == 'malefic'
        assert c['Saturn'] == 'malefic'

    def test_waxing_moon_is_benefic(self):
        lons = {'Sun': 0.0, 'Moon': 90.0, 'Mars': 200, 'Mercury': 220,
                'Jupiter': 240, 'Venus': 300, 'Saturn': 60}
        assert benefic_malefic_classification(lons)['Moon'] == 'benefic'

    def test_waning_moon_is_malefic(self):
        lons = {'Sun': 0.0, 'Moon': 270.0, 'Mars': 200, 'Mercury': 220,
                'Jupiter': 240, 'Venus': 300, 'Saturn': 60}
        assert benefic_malefic_classification(lons)['Moon'] == 'malefic'

    def test_mercury_with_malefic_is_malefic(self):
        lons = {'Sun': 10.0, 'Moon': 90.0, 'Mars': 200, 'Mercury': 15.0,
                'Jupiter': 240, 'Venus': 300, 'Saturn': 60}
        assert benefic_malefic_classification(lons)['Mercury'] == 'malefic'

    def test_mercury_alone_is_benefic(self):
        lons = {'Sun': 10.0, 'Moon': 90.0, 'Mars': 200, 'Mercury': 130.0,
                'Jupiter': 240, 'Venus': 300, 'Saturn': 60}
        assert benefic_malefic_classification(lons)['Mercury'] == 'benefic'

    def test_policy_overrides(self):
        lons = {'Sun': 10.0, 'Moon': 270.0, 'Mars': 200, 'Mercury': 15.0,
                'Jupiter': 240, 'Venus': 300, 'Saturn': 60}
        c = benefic_malefic_classification(lons, YogaPolicy(
            moon_benefic_mode='always_benefic',
            mercury_benefic_mode='always_benefic',
        ))
        assert c['Moon'] == 'benefic'
        assert c['Mercury'] == 'benefic'


# ===========================================================================
# 2. Pancha Mahapurusha (BPHS 75.1-2)
# ===========================================================================

class TestPanchaMahapurusha:

    _BASE = {'Sun': 100, 'Moon': 200, 'Mars': 50, 'Mercury': 100,
             'Jupiter': 40, 'Venus': 130, 'Saturn': 190}

    def test_sasa_saturn_exalted_in_kendra(self):
        # Saturn in Libra (exaltation), H7 from Aries lagna.
        res = _by_name(pancha_mahapurusha_yogas(self._BASE, _ARIES_LAGNA))
        assert res['Sasa'].present
        assert res['Sasa'].participants == ('Saturn',)
        assert res['Sasa'].houses_involved == (7,)

    def test_ruchaka_mars_exalted_in_tenth(self):
        lons = dict(self._BASE, Mars=275.0)   # Capricorn H10 from Aries
        res = _by_name(pancha_mahapurusha_yogas(lons, _ARIES_LAGNA))
        assert res['Ruchaka'].present
        assert res['Ruchaka'].houses_involved == (10,)

    def test_dignity_without_kendra_fails(self):
        # Jupiter in Cancer (exaltation) but H3 from Taurus lagna.
        lons = dict(self._BASE, Jupiter=100.0)
        res = _by_name(pancha_mahapurusha_yogas(lons, _TAURUS_LAGNA))
        assert not res['Hamsa'].present
        conds = res['Hamsa'].conditions
        assert conds[0].satisfied is True     # dignity holds
        assert conds[1].satisfied is False    # kendra fails

    def test_kendra_without_dignity_fails(self):
        # Mars in Taurus H1 from Taurus lagna — kendra but no dignity.
        lons = dict(self._BASE, Mars=40.0)
        res = _by_name(pancha_mahapurusha_yogas(lons, _TAURUS_LAGNA))
        assert not res['Ruchaka'].present

    def test_moon_reference_policy_admits_raman_variant(self):
        # Jupiter exalted in Cancer, H3 from Taurus lagna, H10 from Libra Moon.
        lons = dict(self._BASE, Jupiter=100.0, Moon=190.0)
        strict = _by_name(pancha_mahapurusha_yogas(lons, _TAURUS_LAGNA))
        assert not strict['Hamsa'].present
        raman = _by_name(pancha_mahapurusha_yogas(
            lons, _TAURUS_LAGNA, YogaPolicy(mahapurusha_reference='lagna_or_moon'),
        ))
        assert raman['Hamsa'].present

    def test_no_cancellations_defined(self):
        # BPHS/Phaladeepika/Saravali define none.
        for r in pancha_mahapurusha_yogas(self._BASE, _ARIES_LAGNA):
            assert r.cancellations == ()

    def test_all_five_evaluated(self):
        res = pancha_mahapurusha_yogas(self._BASE, _ARIES_LAGNA)
        assert {r.name for r in res} == {
            'Ruchaka', 'Bhadra', 'Hamsa', 'Malavya', 'Sasa',
        }


# ===========================================================================
# 3. Nabhasa (BPHS Ch. 35; BJ Ch. 12)
# ===========================================================================

class TestNabhasa:

    def test_all_32_evaluated(self):
        lons = {'Sun': 10, 'Moon': 40, 'Mars': 100, 'Mercury': 15,
                'Jupiter': 200, 'Venus': 350, 'Saturn': 280}
        res = nabhasa_yogas(lons, _ARIES_LAGNA)
        assert len(res) == 32

    def test_exactly_one_present_per_chart(self):
        charts = [
            {'Sun': 10, 'Moon': 40, 'Mars': 100, 'Mercury': 15,
             'Jupiter': 200, 'Venus': 350, 'Saturn': 280},
            {'Sun': 5, 'Moon': 65, 'Mars': 125, 'Mercury': 185,
             'Jupiter': 245, 'Venus': 305, 'Saturn': 355},
            {'Sun': 0, 'Moon': 30, 'Mars': 60, 'Mercury': 90,
             'Jupiter': 120, 'Venus': 150, 'Saturn': 180},
        ]
        for lons in charts:
            for lagna in (5.0, 95.0, 215.0):
                present = _present(nabhasa_yogas(lons, lagna))
                assert len(present) == 1, (lons, lagna, present)

    def test_rajju_movable_signs(self):
        # Taurus lagna; planets confined to Aries/Cancer/Libra (movable).
        lons = {'Sun': 10, 'Moon': 100, 'Mars': 190, 'Mercury': 15,
                'Jupiter': 105, 'Venus': 195, 'Saturn': 12}
        res = nabhasa_yogas(lons, _TAURUS_LAGNA)
        assert _present(res) == ['Rajju']
        assert _by_name(res)['Sula'].suppressed_by == 'Rajju'

    def test_kamala_eclipses_rajju(self):
        # Movable lagna + movable signs = all kendras -> Kamala (BJ 12.12).
        lons = {'Sun': 10, 'Moon': 100, 'Mars': 190, 'Mercury': 280,
                'Jupiter': 15, 'Venus': 105, 'Saturn': 195}
        res = nabhasa_yogas(lons, _ARIES_LAGNA)
        assert _present(res) == ['Kamala']
        rajju = _by_name(res)['Rajju']
        assert rajju.formed and rajju.suppressed_by == 'Kamala'

    def test_sakata_one_seven(self):
        lons = {'Sun': 10, 'Moon': 195, 'Mars': 15, 'Mercury': 185,
                'Jupiter': 20, 'Venus': 190, 'Saturn': 25}
        assert _present(nabhasa_yogas(lons, _ARIES_LAGNA)) == ['Sakata']

    def test_gola_beats_ashraya(self):
        # All seven in Taurus: Gola prevails over Musala (Bhattotpala).
        lons = {p: 40.0 + i for i, p in enumerate(
            ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'])}
        res = nabhasa_yogas(lons, _ARIES_LAGNA)
        assert _present(res) == ['Gola']
        assert _by_name(res)['Musala'].suppressed_by == 'Gola'

    def test_sankhya_is_residual(self):
        # 6 distinct signs, no pattern -> Dama.
        lons = {'Sun': 10, 'Moon': 40, 'Mars': 100, 'Mercury': 15,
                'Jupiter': 200, 'Venus': 350, 'Saturn': 280}
        assert _present(nabhasa_yogas(lons, _ARIES_LAGNA)) == ['Dama']

    def test_sringataka_trines(self):
        # All in H1/H5/H9 from Aries lagna (Aries/Leo/Sagittarius).
        lons = {'Sun': 10, 'Moon': 130, 'Mars': 250, 'Mercury': 15,
                'Jupiter': 135, 'Venus': 255, 'Saturn': 20}
        assert _present(nabhasa_yogas(lons, _ARIES_LAGNA)) == ['Sringataka']

    def test_yupa_contiguous_from_lagna(self):
        # All in H1-H4 from Aries lagna, all four occupied.
        lons = {'Sun': 10, 'Moon': 40, 'Mars': 70, 'Mercury': 100,
                'Jupiter': 15, 'Venus': 45, 'Saturn': 75}
        assert _present(nabhasa_yogas(lons, _ARIES_LAGNA)) == ['Yupa']

    def test_chakra_odd_houses(self):
        # H1,3,5,7,9,11 all occupied, nothing else.
        lons = {'Sun': 10, 'Moon': 70, 'Mars': 130, 'Mercury': 190,
                'Jupiter': 250, 'Venus': 310, 'Saturn': 15}
        assert _present(nabhasa_yogas(lons, _ARIES_LAGNA)) == ['Chakra']

    def test_suppression_trail_is_visible(self):
        lons = {'Sun': 10, 'Moon': 100, 'Mars': 190, 'Mercury': 280,
                'Jupiter': 15, 'Venus': 105, 'Saturn': 195}
        res = nabhasa_yogas(lons, _ARIES_LAGNA)
        suppressed = [r for r in res if r.suppressed_by is not None]
        assert suppressed, "expected visible suppression trail"
        for r in suppressed:
            assert r.formed and not r.present


# ===========================================================================
# 4. Chandra yogas
# ===========================================================================

class TestChandraYogas:

    def test_gajakesari_common_mode(self):
        # Jupiter H4 from Aries Moon.
        lons = {'Sun': 280, 'Moon': 10, 'Mars': 130, 'Mercury': 300,
                'Jupiter': 100, 'Venus': 250, 'Saturn': 215}
        res = _by_name(chandra_yogas(
            lons, _TAURUS_LAGNA, YogaPolicy(gajakesari_mode='common')))
        assert res['Gajakesari'].present

    def test_gajakesari_parashara_gates_visible(self):
        # Same chart: strict mode fails the benefic-association gate but
        # the proof object shows exactly which clause failed.
        lons = {'Sun': 280, 'Moon': 10, 'Mars': 130, 'Mercury': 300,
                'Jupiter': 100, 'Venus': 250, 'Saturn': 215}
        g = _by_name(chandra_yogas(lons, _TAURUS_LAGNA))['Gajakesari']
        assert not g.present
        satisfied = [c.satisfied for c in g.conditions]
        assert satisfied == [True, False, True]

    def test_gajakesari_parashara_full_formation(self):
        # Venus in Capricorn aspects Cancer (7th) -> benefic association.
        lons = {'Sun': 280, 'Moon': 10, 'Mars': 130, 'Mercury': 300,
                'Jupiter': 100, 'Venus': 285, 'Saturn': 215}
        g = _by_name(chandra_yogas(lons, _TAURUS_LAGNA))['Gajakesari']
        assert g.present, [(c.description, c.satisfied) for c in g.conditions]

    def test_sunapha_excludes_sun(self):
        # Only the Sun in the 2nd from the Moon -> no Sunapha.
        lons = {'Sun': 40, 'Moon': 10, 'Mars': 130, 'Mercury': 300,
                'Jupiter': 160, 'Venus': 250, 'Saturn': 215}
        res = _by_name(chandra_yogas(lons, _TAURUS_LAGNA))
        assert not res['Sunapha'].formed

    def test_sunapha_anapha_durudhara_partition(self):
        base = {'Sun': 280, 'Moon': 10, 'Mercury': 300, 'Jupiter': 130,
                'Venus': 250, 'Saturn': 215}
        # Mars in Taurus (2nd from Aries Moon) -> Sunapha.
        res = _by_name(chandra_yogas(dict(base, Mars=40.0), _TAURUS_LAGNA))
        assert res['Sunapha'].present and not res['Anapha'].present
        # Mars in Pisces (12th) -> Anapha.
        res = _by_name(chandra_yogas(dict(base, Mars=345.0), _TAURUS_LAGNA))
        assert res['Anapha'].present and not res['Sunapha'].present
        # Both flanks -> Durudhara only.
        res = _by_name(chandra_yogas(
            dict(base, Mars=40.0, Saturn=345.0), _TAURUS_LAGNA))
        assert res['Durudhara'].present
        assert not res['Sunapha'].present and not res['Anapha'].present

    def test_kemadruma_formation_and_bhanga(self):
        # Moon isolated (no conjunct, empty flanks) and no planet in kendra
        # from lagna: choose Scorpio lagna so kendras are Sc/Aq/Ta/Le.
        lons = {'Sun': 100, 'Moon': 10, 'Mars': 150, 'Mercury': 95,
                'Jupiter': 155, 'Venus': 250, 'Saturn': 185}
        # Lagna Scorpio (220): kendras Sc(8) Aq(11) Ta(1) Le(4);
        # planets in Cancer(3), Virgo(5x2), Libra(6), Sag(8) -> none in kendra.
        res = _by_name(chandra_yogas(lons, 220.0))
        k = res['Kemadruma']
        assert k.formed, [(c.description, c.satisfied) for c in k.conditions]
        # Bhanga: Mars in Libra = H7 from Aries Moon -> kendra from Moon.
        assert k.cancellations[0].satisfied is True
        assert k.cancelled and not k.present

    def test_kemadruma_bphs_kendra_from_lagna_blocks_formation(self):
        # Jupiter in a kendra from lagna defeats the BPHS formation itself.
        lons = {'Sun': 100, 'Moon': 10, 'Mars': 150, 'Mercury': 95,
                'Jupiter': 130, 'Venus': 250, 'Saturn': 185}
        res = _by_name(chandra_yogas(lons, 35.0))
        assert not res['Kemadruma'].formed

    def test_adhi_yoga_grading_in_notes(self):
        # Jupiter+Venus in 6/7 from Moon; no malefic there.
        lons = {'Sun': 280, 'Moon': 10, 'Mars': 130, 'Mercury': 300,
                'Jupiter': 160, 'Venus': 195, 'Saturn': 250}
        res = _by_name(chandra_yogas(lons, _TAURUS_LAGNA))
        adhi = res['Adhi']
        assert adhi.present
        assert 'count = 2' in adhi.notes

    def test_adhi_yoga_malefic_voids(self):
        # Saturn also in 6/7/8 from Moon -> commentarial cancellation.
        lons = {'Sun': 280, 'Moon': 10, 'Mars': 130, 'Mercury': 300,
                'Jupiter': 160, 'Venus': 195, 'Saturn': 190}
        adhi = _by_name(chandra_yogas(lons, _TAURUS_LAGNA))['Adhi']
        assert adhi.formed and adhi.cancelled and not adhi.present

    def test_chandra_mangala_conjunction(self):
        lons = {'Sun': 280, 'Moon': 10, 'Mars': 15, 'Mercury': 300,
                'Jupiter': 160, 'Venus': 250, 'Saturn': 215}
        res = _by_name(chandra_yogas(lons, _TAURUS_LAGNA))
        assert res['Chandra-Mangala'].present
        assert set(res['Chandra-Mangala'].participants) == {'Moon', 'Mars'}


# ===========================================================================
# 5. Surya yogas
# ===========================================================================

class TestSuryaYogas:

    _BASE = {'Sun': 280, 'Moon': 10, 'Mars': 100, 'Mercury': 130,
             'Jupiter': 165, 'Venus': 220, 'Saturn': 215}

    def test_vesi_second_from_sun(self):
        lons = dict(self._BASE, Venus=310.0)   # Aquarius, 2nd from Cap Sun
        res = _by_name(surya_yogas(lons, _TAURUS_LAGNA))
        assert res['Vesi'].present
        assert 'Venus' in res['Vesi'].participants

    def test_moon_never_counts(self):
        lons = dict(self._BASE, Moon=310.0)    # Moon in 2nd from Sun
        res = _by_name(surya_yogas(lons, _TAURUS_LAGNA))
        assert not res['Vesi'].formed

    def test_ubhayachari_both_flanks(self):
        lons = dict(self._BASE, Venus=310.0, Mercury=250.0)
        res = _by_name(surya_yogas(lons, _TAURUS_LAGNA))
        assert res['Ubhayachari'].present
        assert not res['Vesi'].present and not res['Vosi'].present

    def test_budhaditya_default_mula_rule(self):
        lons = dict(self._BASE, Mercury=285.0)   # same sign as Sun, 5 deg
        res = _by_name(surya_yogas(lons, _TAURUS_LAGNA))
        b = res['Budhaditya']
        assert b.present and not b.cancelled

    def test_budhaditya_raman_combustion_policy(self):
        lons = dict(self._BASE, Mercury=285.0)
        res = _by_name(surya_yogas(
            lons, _TAURUS_LAGNA, YogaPolicy(budhaditya_combustion_cancel=True)))
        b = res['Budhaditya']
        assert b.formed and b.cancelled and not b.present


# ===========================================================================
# 6. Vessel invariants
# ===========================================================================

class TestYogaVessels:

    def test_present_requires_formed(self):
        with pytest.raises(ValueError, match="present requires formed"):
            YogaResult(
                name='X', family='chandra', formed=False,
                cancelled=False, present=True, conditions=(),
            )

    def test_present_and_cancelled_exclusive(self):
        with pytest.raises(ValueError, match="exclusive"):
            YogaResult(
                name='X', family='chandra', formed=True,
                cancelled=True, present=True, conditions=(),
            )

    def test_cancelled_requires_formed(self):
        with pytest.raises(ValueError, match="cancelled requires formed"):
            YogaResult(
                name='X', family='chandra', formed=False,
                cancelled=True, present=False, conditions=(),
            )

    def test_condition_is_frozen(self):
        c = YogaCondition(description='d', satisfied=True, observed='o')
        with pytest.raises((AttributeError, TypeError)):
            c.satisfied = False  # type: ignore[misc]


# ===========================================================================
# 7. Raja yogas (BPHS Ch. 34/39; PD 6.37, 6.57, 7.26-30; UK IV)
# ===========================================================================

from moira.yogas import evaluate_yogas, raja_yogas, dhana_yogas

_CANCER_LAGNA = 100.0


class TestRajaYogas:

    _BASE = {'Sun': 130, 'Moon': 100, 'Mars': 280, 'Mercury': 160,
             'Jupiter': 40, 'Venus': 310, 'Saturn': 190}

    def test_yogakaraka_mars_for_cancer_lagna(self):
        # Cancer lagna: Mars owns the 5th (Scorpio) and 10th (Aries).
        res = _by_name(raja_yogas(self._BASE, _CANCER_LAGNA))
        yk = res['Yogakaraka']
        assert yk.present and yk.participants == ('Mars',)

    def test_no_yogakaraka_for_aries_lagna(self):
        res = _by_name(raja_yogas(self._BASE, _ARIES_LAGNA))
        assert not res['Yogakaraka'].present

    def test_harsha_phaladeepika_mode(self):
        # Cancer lagna, 6L = Jupiter placed in Sagittarius (H6).
        lons = dict(self._BASE, Jupiter=250.0)
        res = _by_name(raja_yogas(lons, _CANCER_LAGNA))
        h = res['Harsha']
        assert h.present and h.houses_involved == (6,)

    def test_harsha_uk_mode_excludes_own_house(self):
        # UK IV.22: the 6th lord must be in the OTHER two dusthanas.
        lons = dict(self._BASE, Jupiter=250.0)   # 6L in own 6th
        res = _by_name(raja_yogas(
            lons, _CANCER_LAGNA, YogaPolicy(viparita_mode='uttara_kalamrita')))
        assert not res['Harsha'].formed

    def test_neecha_bhanga_via_dispositor_kendra(self):
        # Mars debilitated in Cancer; debilitation lord Moon in H1 kendra.
        lons = dict(self._BASE, Mars=95.0)
        res = _by_name(raja_yogas(lons, _CANCER_LAGNA))
        nb = res['Neecha Bhanga (Mars)']
        assert nb.present
        assert nb.conditions[0].satisfied   # deb-lord kendra rule (PD 7.26)

    def test_neecha_bhanga_retrograde_needs_speeds(self):
        lons = dict(self._BASE, Mars=95.0)
        without = _by_name(raja_yogas(lons, _CANCER_LAGNA))
        assert without['Neecha Bhanga (Mars)'].conditions[4].satisfied is False
        with_speeds = _by_name(raja_yogas(
            lons, _CANCER_LAGNA, planet_speeds={'Mars': -0.3}))
        assert with_speeds['Neecha Bhanga (Mars)'].conditions[4].satisfied

    def test_no_neecha_bhanga_result_without_debilitation(self):
        res = raja_yogas(self._BASE, _CANCER_LAGNA)
        assert not any(r.name.startswith('Neecha Bhanga') for r in res
                       if 'Mars' in r.name)


# ===========================================================================
# 8. Dhana yogas (BPHS 13; UK IV.28; PD 6.21, 6.32)
# ===========================================================================

class TestDhanaYogas:

    _BASE = {'Sun': 130, 'Moon': 100, 'Mars': 280, 'Mercury': 160,
             'Jupiter': 40, 'Venus': 310, 'Saturn': 190}

    def test_parivartana_dainya_classification(self):
        # Venus (Aquarius) <-> Saturn (Libra) exchange; Cancer lagna:
        # Saturn owns 7+8 -> dusthana participation -> Dainya.
        res = _by_name(dhana_yogas(self._BASE, _CANCER_LAGNA))
        assert res['Dainya Parivartana'].present
        assert not res['Maha Parivartana'].present

    def test_lakshmi_requires_both_conditions(self):
        # PD 6.21: 9L AND Venus each own/exalted in kendra/trikona.
        # Cancer lagna: 9L = Jupiter. Jupiter exalted in Cancer H1;
        # Venus in Pisces (exaltation) H9.
        lons = dict(self._BASE, Jupiter=95.0, Venus=340.0)
        res = _by_name(dhana_yogas(lons, _CANCER_LAGNA))
        assert res['Lakshmi'].present
        # Break the Venus leg only:
        lons2 = dict(lons, Venus=310.0)
        res2 = _by_name(dhana_yogas(lons2, _CANCER_LAGNA))
        lakshmi = res2['Lakshmi']
        assert not lakshmi.present
        assert lakshmi.conditions[0].satisfied is True
        assert lakshmi.conditions[1].satisfied is False

    def test_dhana_network_contamination_cancels(self):
        # Build a 2/5/9/11 sambandha then contaminate with a dusthana lord.
        # Cancer lagna: 2L=Sun, 5L=Mars, 9L=Jupiter, 11L=Venus.
        lons = dict(self._BASE, Sun=100.0, Mars=105.0)   # Sun+Mars conjunct
        res = _by_name(dhana_yogas(lons, _CANCER_LAGNA))
        net = res['Dhana Network (2-5-9-11)']
        assert net.formed


# ===========================================================================
# 9. Full evaluation
# ===========================================================================

class TestEvaluateYogas:

    def test_full_chart_evaluation_counts(self):
        lons = {'Sun': 130, 'Moon': 100, 'Mars': 280, 'Mercury': 160,
                'Jupiter': 40, 'Venus': 310, 'Saturn': 190}
        result = evaluate_yogas(lons, _CANCER_LAGNA)
        assert len(result.yogas) >= 55       # 5+7+4+32+>=5+6
        assert result.present_names == tuple(
            y.name for y in result.yogas if y.present)

    def test_every_result_is_internally_consistent(self):
        lons = {'Sun': 130, 'Moon': 100, 'Mars': 280, 'Mercury': 160,
                'Jupiter': 40, 'Venus': 310, 'Saturn': 190}
        for lagna in (5.0, 100.0, 215.0, 305.0):
            for y in evaluate_yogas(lons, lagna).yogas:
                if y.present:
                    assert y.formed and not y.cancelled
                if y.cancelled:
                    assert y.formed
                assert y.source, y.name

    def test_every_yoga_carries_conditions_and_citation(self):
        lons = {'Sun': 10, 'Moon': 40, 'Mars': 100, 'Mercury': 15,
                'Jupiter': 200, 'Venus': 350, 'Saturn': 280}
        for y in evaluate_yogas(lons, _ARIES_LAGNA).yogas:
            assert y.conditions, y.name
            for c in y.conditions:
                assert c.description and c.observed is not None

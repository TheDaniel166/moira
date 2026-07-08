"""
Unit tests for the Ashtakavarga kakshya + shodhya pinda extension.

Oracles: BPHS Ch. 69's own worked example (Sun Yoga Pinda 148, Moon 158)
and Patel & Aiyar's Standard Horoscope (Moon Shodhya Pinda 94) — both
reproduced exactly.  Kakshya doctrine per Jataka Parijata II.71 + Patel
1957 (absent from Santhanam's BPHS — recorded honestly on the results).
"""
import pytest

from moira.ashtakavarga import (
    GRAHAMANA,
    KAKSHYA_LORDS,
    RASIMANA,
    REKHA_TABLES,
    KakshyaTransit,
    ShodhyaPinda,
    kakshya_transit,
    shodhya_pinda,
)


_BPHS_POS = {'Sun': 9, 'Moon': 2, 'Mars': 1, 'Mercury': 10,
             'Jupiter': 10, 'Venus': 10, 'Saturn': 7, 'Lagna': 10}


class TestKakshya:

    def test_lord_order_is_jp_saturn_first(self):
        assert KAKSHYA_LORDS == (
            'Saturn', 'Jupiter', 'Mars', 'Sun', 'Venus', 'Mercury',
            'Moon', 'Lagna',
        )

    @pytest.mark.parametrize("deg,index,lord", [
        (0.0, 0, 'Saturn'),
        (3.74, 0, 'Saturn'),
        (3.75, 1, 'Jupiter'),
        (7.5, 2, 'Mars'),
        (11.25, 3, 'Sun'),
        (15.0, 4, 'Venus'),
        (18.75, 5, 'Mercury'),
        (22.5, 6, 'Moon'),
        (26.25, 7, 'Lagna'),
        (29.99, 7, 'Lagna'),
    ])
    def test_kakshya_boundaries(self, deg, index, lord):
        kt = kakshya_transit('Sun', deg, _BPHS_POS)
        assert kt.kakshya_index == index
        assert kt.kakshya_lord == lord

    def test_contribution_checks_the_specific_lord(self):
        # Saturn kakshya of Aries: Saturn natal in Scorpio -> distance 6.
        kt = kakshya_transit('Sun', 0.0, _BPHS_POS)
        assert kt.lord_contributed == (6 in REKHA_TABLES['Sun']['Saturn'])
        assert kt.favorable == kt.lord_contributed

    def test_lagna_kakshya_counts_via_lagna_contribution(self):
        kt = kakshya_transit('Sun', 26.5, _BPHS_POS)   # Aries, Lagna kakshya
        distance = (0 - _BPHS_POS['Lagna']) % 12 + 1
        assert kt.lord_contributed == (
            distance in REKHA_TABLES['Sun']['Lagna'])

    def test_sign_rekhas_matches_bhinnashtakavarga(self):
        from moira.ashtakavarga import bhinnashtakavarga
        kt = kakshya_transit('Jupiter', 95.0, _BPHS_POS)  # Cancer
        assert kt.sign_rekhas == bhinnashtakavarga(
            'Jupiter', _BPHS_POS).rekhas[3]

    def test_source_records_bphs_absence(self):
        kt = kakshya_transit('Sun', 0.0, _BPHS_POS)
        assert 'absent' in kt.source

    def test_unknown_planet_raises(self):
        with pytest.raises(ValueError, match="planet"):
            kakshya_transit('Rahu', 0.0, _BPHS_POS)

    def test_vessel_rejects_mismatched_lord(self):
        with pytest.raises(ValueError, match="does not match"):
            KakshyaTransit(
                planet='Sun', transit_sign_index=0, degrees_in_sign=0.0,
                kakshya_index=0, kakshya_lord='Jupiter',
                lord_contributed=True, sign_rekhas=4, favorable=True,
                source='x',
            )


class TestShodhyaPinda:

    def test_multiplier_tables(self):
        assert RASIMANA == (7, 10, 8, 4, 10, 5, 7, 8, 9, 5, 11, 12)
        assert GRAHAMANA == {
            'Sun': 5, 'Moon': 5, 'Mars': 8, 'Mercury': 5,
            'Jupiter': 10, 'Venus': 7, 'Saturn': 5,
        }
        assert sum(RASIMANA) == 96

    def test_bphs_worked_example_sun(self):
        # BPHS Ch. 69 illustration: Rasi Pinda 100, Graha Pinda 48 -> 148.
        sun_reduced = (0, 1, 1, 4, 1, 0, 0, 4, 1, 3, 0, 0)
        sp = shodhya_pinda('Sun', sun_reduced, _BPHS_POS)
        assert sp.rasi_pinda == 100
        assert sp.graha_pinda == 48
        assert sp.shodhya_pinda == 148

    def test_bphs_worked_example_moon(self):
        moon_reduced = (0, 2, 2, 0, 0, 0, 0, 3, 0, 0, 1, 2)
        sp = shodhya_pinda('Moon', moon_reduced, _BPHS_POS)
        assert sp.rasi_pinda == 95
        assert sp.graha_pinda == 63
        assert sp.shodhya_pinda == 158

    def test_patel_standard_horoscope_moon(self):
        # Patel & Aiyar: Rasi Pinda 62 + Graha Pinda 32 = 94.
        pos = {'Sun': 4, 'Moon': 6, 'Mars': 4, 'Mercury': 4,
               'Jupiter': 6, 'Venus': 6, 'Saturn': 9, 'Lagna': 1}
        moon_reduced = (3, 0, 3, 0, 0, 0, 1, 0, 0, 2, 0, 0)
        sp = shodhya_pinda('Moon', moon_reduced, pos)
        assert sp.rasi_pinda == 62
        assert sp.graha_pinda == 32
        assert sp.shodhya_pinda == 94

    def test_co_occupants_each_multiply_same_sign(self):
        # Mercury/Jupiter/Venus all in Aquarius: each multiplies Aq's
        # figure by its own grahamana (5 + 10 + 7 = 22 per rekha).
        reduced = tuple(1 if i == 10 else 0 for i in range(12))
        sp = shodhya_pinda('Sun', reduced, _BPHS_POS)
        assert sp.graha_pinda == 22
        assert sp.rasi_pinda == 11

    def test_nodes_never_participate(self):
        # Graha Pinda sums exactly the seven grahamana planets.
        reduced = tuple(1 for _ in range(12))
        sp = shodhya_pinda('Sun', reduced, _BPHS_POS)
        assert sp.graha_pinda == sum(GRAHAMANA.values())

    def test_vessel_consistency_enforced(self):
        with pytest.raises(ValueError, match="rasi_pinda"):
            ShodhyaPinda(
                planet='Sun', reduced_rekhas=tuple(0 for _ in range(12)),
                rasi_pinda=10, graha_pinda=5, shodhya_pinda=99, source='x',
            )

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="12 entries"):
            shodhya_pinda('Sun', (1, 2, 3), _BPHS_POS)

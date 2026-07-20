from __future__ import annotations

import math

import pytest

from moira.muhurta import classify_muhurta, score_muhurta
from moira.panchanga import PanchangaElement, PanchangaResult
from moira.sidereal import NakshatraPosition


def _element(name: str, index: int, span: float = 12.0) -> PanchangaElement:
    return PanchangaElement(
        name=name,
        index=index,
        number=index + 1,
        degrees_elapsed=span / 2.0,
        degrees_remaining=span / 2.0,
    )


def _panchanga_with_nakshatra(name: str, index: int) -> PanchangaResult:
    return PanchangaResult(
        jd=2451545.0,
        tithi=_element("Pratipada", 0),
        vara=_element("Somavara", 1, span=0.0),
        vara_lord="Moon",
        nakshatra=NakshatraPosition(
            nakshatra=name,
            nakshatra_index=index,
            nakshatra_lord="Moon",
            pada=1,
            degrees_in=1.0,
            sidereal_lon=float(index) * (360.0 / 27.0) + 1.0,
        ),
        yoga=_element("Priti", 1, span=360.0 / 27.0),
        karana=_element("Bava", 1, span=6.0),
        ayanamsa_system="Lahiri",
    )


def test_muhurta_classification_reads_live_nakshatra_field_for_uttama_nakshatra() -> None:
    result = classify_muhurta(_panchanga_with_nakshatra("Rohini", 3))

    assert result.nakshatra == "auspicious"
    assert result.overall == "auspicious"


def test_muhurta_classification_reads_live_nakshatra_field_for_gandanta_nakshatra() -> None:
    result = classify_muhurta(_panchanga_with_nakshatra("Mula", 18))

    assert result.nakshatra == "inauspicious"
    assert result.overall == "neutral"


def test_muhurta_score_breakdown_reflects_nakshatra_classification() -> None:
    auspicious = score_muhurta(_panchanga_with_nakshatra("Rohini", 3))
    inauspicious = score_muhurta(_panchanga_with_nakshatra("Mula", 18))

    assert auspicious.breakdown["nakshatra"] == pytest.approx(1.0)
    assert inauspicious.breakdown["nakshatra"] == pytest.approx(-0.5)
    assert auspicious.total > inauspicious.total


# ===========================================================================
# Tara Bala + Chandra Bala (natal-personalized muhurta)
# ===========================================================================

from moira.muhurta import (
    TARA_NAMES,
    TaraBala,
    tara_bala,
    ChandraBala,
    chandra_bala,
    personal_muhurta_score,
    MuhurtaPolicy,
)


class TestTaraBala:

    def test_nine_tara_names(self) -> None:
        assert TARA_NAMES == (
            "Janma", "Sampat", "Vipat", "Kshema", "Pratyari",
            "Sadhaka", "Vadha", "Mitra", "Parama Mitra",
        )

    def test_janma_tara_is_caution(self) -> None:
        t = tara_bala(0, 0)
        assert t.count == 1
        assert t.tara_name == "Janma"
        assert t.polarity == "caution"
        assert t.favorable is False

    @pytest.mark.parametrize("offset,name,polarity", [
        (1, "Sampat", "favorable"),
        (2, "Vipat", "unfavorable"),
        (3, "Kshema", "favorable"),
        (4, "Pratyari", "unfavorable"),
        (5, "Sadhaka", "favorable"),
        (6, "Vadha", "unfavorable"),
        (7, "Mitra", "favorable"),
        (8, "Parama Mitra", "favorable"),
    ])
    def test_tara_cycle_polarity(self, offset, name, polarity) -> None:
        t = tara_bala(0, offset)
        assert t.tara_name == name
        assert t.polarity == polarity

    def test_cycle_repeats_after_nine(self) -> None:
        # 10th nakshatra from janma restarts the cycle at Janma.
        t = tara_bala(0, 9)
        assert t.tara_number == 1
        assert t.tara_name == "Janma"

    def test_wraparound_across_revati(self) -> None:
        # Janma Revati (26), target Ashwini (0) -> count 2 -> Sampat.
        t = tara_bala(26, 0)
        assert t.count == 2
        assert t.tara_name == "Sampat"

    def test_invalid_index_raises(self) -> None:
        with pytest.raises(ValueError, match="janma_nakshatra_index"):
            tara_bala(27, 0)


class TestChandraBala:

    def test_same_sign_is_house_one_favorable(self) -> None:
        c = chandra_bala(35.0, 40.0)
        assert c.house_from_moon == 1
        assert c.favorable is True

    def test_eighth_is_chandrashtama(self) -> None:
        c = chandra_bala(15.0, 15.0 + 210.0)
        assert c.house_from_moon == 8
        assert c.is_chandrashtama is True
        assert c.polarity == "unfavorable"

    @pytest.mark.parametrize("house,polarity", [
        (1, "favorable"), (2, "neutral"), (3, "favorable"),
        (4, "unfavorable"), (5, "neutral"), (6, "favorable"),
        (7, "favorable"), (8, "unfavorable"), (9, "unfavorable"),
        (10, "favorable"), (11, "favorable"), (12, "unfavorable"),
    ])
    def test_full_house_polarity_table(self, house, polarity) -> None:
        c = chandra_bala(15.0, 15.0 + (house - 1) * 30.0)
        assert c.house_from_moon == house
        assert c.polarity == polarity

    def test_only_eighth_flags_chandrashtama(self) -> None:
        for house in range(1, 13):
            c = chandra_bala(15.0, 15.0 + (house - 1) * 30.0)
            assert c.is_chandrashtama is (house == 8)


class TestPersonalMuhurtaScore:

    def _panchanga(self):
        return _panchanga_with_nakshatra("Rohini", 3)

    def test_breakdown_carries_tara_and_chandra(self) -> None:
        ps = personal_muhurta_score(self._panchanga(), 100.0, 11.0)
        assert "tara" in ps.breakdown
        assert "chandra" in ps.breakdown

    def test_total_is_base_plus_overlays(self) -> None:
        from moira.muhurta import score_muhurta
        pg = self._panchanga()
        base = score_muhurta(pg)
        ps = personal_muhurta_score(pg, 100.0, 11.0)
        assert ps.total == pytest.approx(
            base.total + ps.breakdown["tara"] + ps.breakdown["chandra"]
        )

    def test_chandrashtama_doubles_the_penalty(self) -> None:
        pg = self._panchanga()
        janma = 15.0
        # 8th from natal Moon (Chandrashtama) vs plain unfavorable 4th.
        ps8 = personal_muhurta_score(pg, janma, janma + 210.0)
        ps4 = personal_muhurta_score(pg, janma, janma + 90.0)
        assert ps8.breakdown["chandra"] == pytest.approx(-2.0)
        assert ps4.breakdown["chandra"] == pytest.approx(-1.0)

    def test_weights_scale_the_overlays(self) -> None:
        pg = self._panchanga()
        policy = MuhurtaPolicy(weight_tara=2.0, weight_chandra=3.0)
        janma = 15.0
        # Transit Moon 1 nakshatra ahead (Sampat, favorable), same sign (H1 favorable).
        transit = janma + 360.0 / 27
        ps = personal_muhurta_score(pg, janma, transit, policy)
        assert ps.breakdown["tara"] == pytest.approx(2.0)
        assert ps.breakdown["chandra"] == pytest.approx(3.0)

    def test_janma_tara_contributes_zero(self) -> None:
        pg = self._panchanga()
        ps = personal_muhurta_score(pg, 15.0, 15.0)
        assert ps.tara.tara_name == "Janma"
        assert ps.breakdown["tara"] == pytest.approx(0.0)

    def test_tara_indices_share_one_ulp_boundary_recovery(self) -> None:
        pg = self._panchanga()
        janma = math.nextafter(40.0 / 3.0, -math.inf)
        transit = math.nextafter(80.0 / 3.0, -math.inf)

        ps = personal_muhurta_score(pg, janma, transit)

        assert ps.tara.janma_nakshatra_index == 1
        assert ps.tara.target_nakshatra_index == 2
        assert ps.tara.tara_name == "Sampat"

from __future__ import annotations

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

"""Moira.longevity() uses Lilly's sourced hyleg/alcocoden and fails closed.

Authority: Lilly, Christian Astrology (1647) III ch. CIV, as implemented by
``find_alcocoden_lilly_1647``. The facade must forward exactly the chart's
geometry to that function (dual-path equivalence) and refuse inputs Lilly's
procedure cannot use, instead of the legacy unsourced rule and its silent
0-degree defaults.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from moira.constants import HouseSystem
from moira.longevity import AlcocodenDetermination, find_alcocoden_lilly_1647

NATAL_DT = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
LAT, LON = 51.5085, -0.1257


def test_longevity_matches_the_sourced_lilly_determination(moira_engine) -> None:
    chart = moira_engine.chart(NATAL_DT)
    houses = moira_engine.houses(NATAL_DT, LAT, LON, HouseSystem.REGIOMONTANUS)

    result = moira_engine.longevity(chart, houses, observer_latitude=LAT)
    direct = find_alcocoden_lilly_1647(
        chart.longitudes(include_nodes=False),
        list(houses.cusps),
        True,  # Sun near culmination at London noon: a day chart
        armc=houses.armc,
        obliquity=chart.obliquity,
        geographic_latitude=LAT,
    )

    assert isinstance(result, AlcocodenDetermination)
    assert result == direct
    assert result.hyleg.is_day_chart is True


def test_longevity_refuses_cusps_whose_first_is_not_the_ascendant(moira_engine) -> None:
    chart = moira_engine.chart(NATAL_DT)
    whole_sign = moira_engine.houses(NATAL_DT, LAT, LON, HouseSystem.WHOLE_SIGN)

    with pytest.raises(ValueError, match="first cusp is the Ascendant"):
        moira_engine.longevity(chart, whole_sign)


def test_longevity_refuses_a_chart_without_all_seven_planets(moira_engine) -> None:
    chart = moira_engine.chart(NATAL_DT)
    houses = moira_engine.houses(NATAL_DT, LAT, LON, HouseSystem.REGIOMONTANUS)
    longitudes = chart.longitudes(include_nodes=False)
    longitudes.pop("Saturn")
    partial = SimpleNamespace(
        longitudes=lambda *, include_nodes=False: dict(longitudes),
        planets=chart.planets,
        obliquity=chart.obliquity,
    )

    with pytest.raises(ValueError, match="missing Saturn"):
        moira_engine.longevity(partial, houses)

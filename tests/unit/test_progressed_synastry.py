from __future__ import annotations

from datetime import datetime, timezone
import pytest

from moira import Body, HouseSystem
from moira.progressions import secondary_progression, solar_arc, daily_house_frame
from moira.synastry import (
    synastry_aspects,
    synastry_contacts,
    house_overlay,
    mutual_house_overlays,
)


@pytest.mark.requires_ephemeris
def test_natal_to_progressed_synastry_aspects(moira_engine) -> None:
    engine = moira_engine
    dt_natal = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_progressed = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)

    chart_natal = engine.chart(dt_natal)
    chart_prog = secondary_progression(chart_natal.jd_ut, dt_progressed)

    # 1. Run aspects using facade
    aspects = engine.synastry_aspects(chart_natal, chart_prog, tier=2, include_nodes=True)
    assert len(aspects) > 0

    # 2. Run aspects using raw synastry function
    aspects_direct = synastry_aspects(chart_natal, chart_prog, tier=2, include_nodes=True)
    assert len(aspects_direct) == len(aspects)

    # 3. Check that bodies from natal and progressed are mapped correctly
    for aspect in aspects:
        assert aspect.body1 in chart_natal.longitudes()
        assert aspect.body2 in chart_prog.longitudes()


@pytest.mark.requires_ephemeris
def test_progressed_to_natal_synastry_aspects(moira_engine) -> None:
    engine = moira_engine
    dt_natal = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_progressed = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)

    chart_natal = engine.chart(dt_natal)
    chart_prog = secondary_progression(chart_natal.jd_ut, dt_progressed)

    aspects = engine.synastry_aspects(chart_prog, chart_natal, tier=2, include_nodes=True)
    assert len(aspects) > 0

    for aspect in aspects:
        assert aspect.body1 in chart_prog.longitudes()
        assert aspect.body2 in chart_natal.longitudes()


@pytest.mark.requires_ephemeris
def test_progressed_to_progressed_synastry_aspects(moira_engine) -> None:
    engine = moira_engine
    dt_natal_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_natal_b = datetime(1995, 5, 10, 12, 0, tzinfo=timezone.utc)
    dt_progressed = datetime(2025, 6, 4, 12, 0, tzinfo=timezone.utc)

    chart_natal_a = engine.chart(dt_natal_a)
    chart_natal_b = engine.chart(dt_natal_b)

    chart_prog_a = secondary_progression(chart_natal_a.jd_ut, dt_progressed)
    chart_prog_b = solar_arc(chart_natal_b.jd_ut, dt_progressed)

    aspects = engine.synastry_aspects(chart_prog_a, chart_prog_b, tier=2, include_nodes=True)
    assert len(aspects) > 0

    for aspect in aspects:
        assert aspect.body1 in chart_prog_a.longitudes()
        assert aspect.body2 in chart_prog_b.longitudes()


@pytest.mark.requires_ephemeris
def test_progressed_house_overlay(moira_engine) -> None:
    engine = moira_engine
    dt_natal_a = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt_natal_b = datetime(1995, 5, 10, 12, 0, tzinfo=timezone.utc)
    dt_progressed = datetime(2025, 6, 4, 12, 0, tzinfo=timezone.utc)
    lat = 40.7128
    lon = -74.0060

    chart_natal_a = engine.chart(dt_natal_a)
    chart_natal_b = engine.chart(dt_natal_b)

    chart_prog_a = secondary_progression(chart_natal_a.jd_ut, dt_progressed)
    houses_prog_b = daily_house_frame(chart_natal_b.jd_ut, dt_progressed, lat, lon, system=HouseSystem.PLACIDUS)

    # 1. Perform overlay direct
    overlay = house_overlay(chart_prog_a, houses_prog_b)
    assert overlay.source_label == "A"
    assert overlay.target_label == "B"
    assert len(overlay.placements) > 0

    # 2. Perform overlay via facade
    overlay_facade = engine.house_overlay(chart_prog_a, houses_prog_b)
    assert overlay_facade.source_label == "A"
    assert overlay_facade.target_label == "B"
    assert len(overlay_facade.placements) == len(overlay.placements)

    # 3. Perform mutual overlays via facade
    houses_prog_a = daily_house_frame(chart_natal_a.jd_ut, dt_progressed, lat, lon, system=HouseSystem.PLACIDUS)
    mutual = engine.mutual_house_overlays(chart_prog_a, houses_prog_a, chart_natal_b, houses_prog_b)

    assert len(mutual.first_in_second.placements) > 0
    assert len(mutual.second_in_first.placements) > 0


def test_synastry_input_validation_hardening(moira_engine) -> None:
    engine = moira_engine
    dt_natal = datetime(1990, 1, 1, 12, 0, tzinfo=timezone.utc)
    chart_natal = engine.chart(dt_natal)

    # 1. Invalid chart arguments to synastry_aspects / synastry_contacts
    with pytest.raises(TypeError, match="chart_a must be a Chart or ProgressedChart instance"):
        synastry_aspects("not_a_chart", chart_natal)
    with pytest.raises(TypeError, match="chart_b must be a Chart or ProgressedChart instance"):
        synastry_aspects(chart_natal, "not_a_chart")

    with pytest.raises(TypeError, match="chart_a must be a Chart or ProgressedChart instance"):
        synastry_contacts("not_a_chart", chart_natal)
    with pytest.raises(TypeError, match="chart_b must be a Chart or ProgressedChart instance"):
        synastry_contacts(chart_natal, "not_a_chart")

    # 2. Invalid arguments to house_overlay
    with pytest.raises(TypeError, match="chart_source must be a Chart or ProgressedChart instance"):
        house_overlay("not_a_chart", chart_natal)

    with pytest.raises(TypeError, match="target_houses must be HouseCusps or ProgressedHouseFrame wrapping HouseCusps"):
        house_overlay(chart_natal, "not_houses")


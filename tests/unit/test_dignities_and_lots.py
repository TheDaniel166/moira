from __future__ import annotations

import pytest

from moira import Moira
from moira.dignities import (
    calculate_dignities,
    is_in_hayz,
    is_in_sect,
    mutual_receptions,
    sect_light,
)
from moira.lots import ArabicPartsService, calculate_lots, list_parts


def _equal_houses(start: float = 0.0) -> list[dict]:
    return [{"number": i + 1, "degree": (start + i * 30.0) % 360.0} for i in range(12)]


def _part_by_name(parts, name: str):
    for part in parts:
        if part.name == name:
            return part
    raise AssertionError(f"Part not found: {name}")


def test_dignities_identify_essential_dignity_mutual_reception_and_hayz() -> None:
    house_positions = _equal_houses(300.0)
    planet_positions = [
        {"name": "Sun", "degree": 130.0, "is_retrograde": False},      # Leo, H7, day, hayz
        {"name": "Moon", "degree": 15.0, "is_retrograde": False},      # Aries
        {"name": "Mercury", "degree": 165.0, "is_retrograde": False},  # Virgo exaltation/domicile
        {"name": "Venus", "degree": 10.0, "is_retrograde": False},     # Aries
        {"name": "Mars", "degree": 35.0, "is_retrograde": False},      # Taurus
        {"name": "Jupiter", "degree": 95.0, "is_retrograde": False},   # Cancer exaltation
        {"name": "Saturn", "degree": 200.0, "is_retrograde": True},    # Libra exaltation, retrograde
    ]

    dignities = calculate_dignities(planet_positions, house_positions)
    by_name = {d.planet: d for d in dignities}

    assert [d.planet for d in dignities] == ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

    assert by_name["Sun"].essential_dignity == "Domicile"
    assert "Angular (H7)" in by_name["Sun"].accidental_dignities
    assert "Direct" in by_name["Sun"].accidental_dignities
    assert "In Hayz" in by_name["Sun"].accidental_dignities

    assert by_name["Jupiter"].essential_dignity == "Exaltation"
    assert by_name["Saturn"].essential_dignity == "Exaltation"
    assert "Retrograde" in by_name["Saturn"].accidental_dignities

    assert "Mutual Reception (Mars)" in by_name["Venus"].accidental_dignities
    assert "Mutual Reception (Venus)" in by_name["Mars"].accidental_dignities


@pytest.mark.parametrize(
    ("mercury_lon", "expected_marker"),
    [
        (100.2, "Cazimi"),
        (105.0, "Combust"),
        (112.0, "Under Sunbeams"),
    ],
)
def test_dignities_solar_proximity_bands_are_classified_correctly(
    mercury_lon: float,
    expected_marker: str,
) -> None:
    house_positions = _equal_houses(0.0)
    planet_positions = [
        {"name": "Sun", "degree": 100.0, "is_retrograde": False},
        {"name": "Moon", "degree": 220.0, "is_retrograde": False},
        {"name": "Mercury", "degree": mercury_lon, "is_retrograde": False},
        {"name": "Venus", "degree": 40.0, "is_retrograde": False},
        {"name": "Mars", "degree": 150.0, "is_retrograde": False},
        {"name": "Jupiter", "degree": 250.0, "is_retrograde": False},
        {"name": "Saturn", "degree": 310.0, "is_retrograde": False},
    ]

    mercury = {d.planet: d for d in calculate_dignities(planet_positions, house_positions)}["Mercury"]
    assert expected_marker in mercury.accidental_dignities


def test_dignity_helpers_cover_sect_and_mutual_reception_logic() -> None:
    assert sect_light(130.0, 300.0) == "Sun"
    assert sect_light(20.0, 300.0) == "Moon"

    assert is_in_sect("Jupiter", is_day_chart=True)
    assert not is_in_sect("Jupiter", is_day_chart=False)
    assert is_in_hayz("Sun", "Leo", 7, is_day_chart=True)
    assert not is_in_hayz("Moon", "Leo", 7, is_day_chart=True)

    receptions = mutual_receptions({"Venus": 10.0, "Mars": 35.0, "Sun": 130.0})
    assert ("Venus", "Mars", "Domicile") in receptions or ("Mars", "Venus", "Domicile") in receptions


def test_lots_day_and_night_formulas_resolve_core_references_correctly() -> None:
    positions = {
        "Sun": 100.0,
        "Moon": 220.0,
        "Mercury": 80.0,
        "Venus": 10.0,
        "Mars": 35.0,
        "Jupiter": 250.0,
        "Saturn": 310.0,
    }
    house_cusps = {i + 1: i * 30.0 for i in range(12)}

    day_parts = calculate_lots(positions, house_cusps, True)
    night_parts = calculate_lots(positions, house_cusps, False)

    day_fortune = _part_by_name(day_parts, "Fortune")
    night_fortune = _part_by_name(night_parts, "Fortune")
    day_spirit = _part_by_name(day_parts, "Spirit")
    night_spirit = _part_by_name(night_parts, "Spirit")
    day_eros = _part_by_name(day_parts, "Eros (Valens)")
    night_eros = _part_by_name(night_parts, "Eros (Valens)")

    assert day_fortune.longitude == pytest.approx((0.0 + 220.0 - 100.0) % 360.0, abs=1e-12)
    assert night_fortune.longitude == pytest.approx((0.0 + 100.0 - 220.0) % 360.0, abs=1e-12)
    assert day_spirit.longitude == pytest.approx((0.0 + 100.0 - 220.0) % 360.0, abs=1e-12)
    assert night_spirit.longitude == pytest.approx((0.0 + 220.0 - 100.0) % 360.0, abs=1e-12)
    assert day_eros.longitude == pytest.approx((0.0 + day_spirit.longitude - day_fortune.longitude) % 360.0, abs=1e-12)
    assert night_eros.longitude == pytest.approx((0.0 + night_fortune.longitude - night_spirit.longitude) % 360.0, abs=1e-12)


def test_lots_reference_builder_resolves_rulers_fixed_degrees_and_optional_inputs() -> None:
    service = ArabicPartsService()
    refs = service._build_refs(
        {
            "Sun": 100.0,
            "Moon": 220.0,
            "Mercury": 80.0,
            "Venus": 10.0,
            "Mars": 35.0,
            "Jupiter": 250.0,
            "Saturn": 310.0,
        },
        {i + 1: i * 30.0 for i in range(12)},
        True,
        syzygy=15.0,
        prenatal_nm=25.0,
        prenatal_fm=205.0,
        lord_of_hour=77.0,
    )

    assert refs["Asc"] == pytest.approx(0.0, abs=1e-12)
    assert refs["MC"] == pytest.approx(270.0, abs=1e-12)
    assert refs["Dsc"] == pytest.approx(180.0, abs=1e-12)
    assert refs["IC"] == pytest.approx(90.0, abs=1e-12)
    assert refs["18 Aries"] == pytest.approx(18.0, abs=1e-12)
    assert refs["Vindemiatrix"] == pytest.approx(193.0, abs=1e-12)
    assert refs["Ruler H1"] == pytest.approx(35.0, abs=1e-12)   # Aries -> Mars
    assert refs["Ruler MC"] == pytest.approx(310.0, abs=1e-12)
    assert refs["Ruler Sun"] == pytest.approx(220.0, abs=1e-12)  # Sun in Cancer -> Moon
    assert refs["Ruler Syzygy"] == pytest.approx(35.0, abs=1e-12)  # 15 Aries -> Mars
    assert refs["New Moon"] == pytest.approx(25.0, abs=1e-12)
    assert refs["Prenatal Full Moon"] == pytest.approx(205.0, abs=1e-12)
    assert refs["Lord of Hour"] == pytest.approx(77.0, abs=1e-12)


@pytest.mark.requires_ephemeris
def test_moira_wrappers_for_dignities_and_lots_match_module_level_calculations(
    moira_engine: Moira,
    natal_chart,
    natal_houses,
) -> None:
    lons = natal_chart.longitudes(include_nodes=False)
    cusps_map = {i + 1: c for i, c in enumerate(natal_houses.cusps)}
    day = sect_light(lons.get("Sun", 0.0), natal_houses.asc) == "Sun"

    expected_lots = calculate_lots(lons, cusps_map, day)
    actual_lots = moira_engine.lots(natal_chart, natal_houses)

    planet_dicts = [
        {
            "name": name,
            "degree": data.longitude,
            "is_retrograde": data.speed < 0,
        }
        for name, data in natal_chart.planets.items()
    ]
    house_dicts = [{"number": i + 1, "degree": cusp} for i, cusp in enumerate(natal_houses.cusps)]
    expected_dignities = calculate_dignities(planet_dicts, house_dicts)
    actual_dignities = moira_engine.dignities(natal_chart, natal_houses)

    assert [(p.name, round(p.longitude, 8)) for p in actual_lots[:20]] == [
        (p.name, round(p.longitude, 8)) for p in expected_lots[:20]
    ]
    assert [
        (d.planet, d.essential_dignity, d.total_score, tuple(d.accidental_dignities))
        for d in actual_dignities
    ] == [
        (d.planet, d.essential_dignity, d.total_score, tuple(d.accidental_dignities))
        for d in expected_dignities
    ]


def test_list_parts_is_sorted_and_contains_core_named_lots() -> None:
    names = list_parts()
    assert names == sorted(names)
    for required in ("Fortune", "Spirit", "Eros (Valens)", "Victory"):
        assert required in names

from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira.varshaphal as varshaphal_module
from moira.constants import HouseSystem
from moira.houses import calculate_houses
from moira.varshaphal import (
    build_varshaphal_chart,
    muntha,
    muntha_condition_profile,
    tajika_aspects,
    tajika_yogas,
    varshaphal_sahams,
)


def test_muntha_advances_one_sign_per_completed_year() -> None:
    assert muntha(312.0, 0) == pytest.approx(312.0)
    assert muntha(312.0, 23) == pytest.approx((312.0 + 23 * 30.0) % 360.0)


def test_muntha_rejects_negative_years() -> None:
    with pytest.raises(ValueError, match="years_elapsed"):
        muntha(120.0, -1)


def test_varshaphal_sahams_apply_30_degree_correction_when_asc_not_between() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    planets = {
        "Sun": 40.0,
        "Moon": 200.0,
        "Mars": 10.0,
        "Mercury": 80.0,
        "Jupiter": 150.0,
        "Venus": 120.0,
        "Saturn": 300.0,
    }

    sahams = {s.name: s for s in varshaphal_sahams(20.0, planets, houses, is_day=True)}
    punya = sahams["Punya"]

    assert punya.correction_applied is True
    assert punya.longitude == pytest.approx((200.0 - 40.0 + 20.0 + 30.0) % 360.0)


def test_varshaphal_sahams_reverse_default_formulas_at_night() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    planets = {
        "Sun": 40.0,
        "Moon": 80.0,
        "Mars": 10.0,
        "Mercury": 50.0,
        "Jupiter": 150.0,
        "Venus": 120.0,
        "Saturn": 300.0,
    }

    sahams = {s.name: s for s in varshaphal_sahams(60.0, planets, houses, is_day=False)}

    assert sahams["Punya"].reversed_for_night is True
    assert sahams["Bhratru"].reversed_for_night is False


def test_varshaphal_sahams_support_derived_dependencies() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    planets = {
        "Sun": 40.0,
        "Moon": 80.0,
        "Mars": 10.0,
        "Mercury": 50.0,
        "Jupiter": 150.0,
        "Venus": 120.0,
        "Saturn": 300.0,
    }

    sahams = {s.name: s for s in varshaphal_sahams(60.0, planets, houses, is_day=True)}
    yasa = sahams["Yasa"]
    punya = sahams["Punya"]
    expected = (planets["Jupiter"] - punya.longitude + 60.0) % 360.0
    if yasa.correction_applied:
        expected = (expected + 30.0) % 360.0

    assert yasa.longitude == pytest.approx(expected)


def test_muntha_condition_profile_tracks_lord_house_geometry() -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    sidereal_planets = {
        "Sun": 10.0,
        "Moon": 20.0,
        "Mars": 65.0,
        "Mercury": 80.0,
        "Jupiter": 140.0,
        "Venus": 200.0,
        "Saturn": 260.0,
    }

    profile = muntha_condition_profile(
        muntha_longitude=5.0,
        muntha_house=1,
        muntha_lord="Sun",
        sidereal_planets=sidereal_planets,
        sidereal_houses=houses,
    )

    assert profile.muntha_sign == "Aries"
    assert profile.muntha_lord_sign == "Aries"
    assert profile.muntha_lord_house == 1
    assert profile.muntha_lord_house_from_muntha == 1
    assert profile.muntha_lord_dignity.dignity_rank == "exaltation"
    assert profile.muntha_lord_dignity_profile.tier == "strong"
    assert profile.lord_in_kendra is True
    assert profile.lord_in_dusthana is False
    assert profile.lord_is_strong is True
    assert profile.lord_is_weak is False


def test_tajika_aspects_classify_benefic_and_inimical_relations() -> None:
    aspects = tajika_aspects(
        {
            "Sun": 10.0,
            "Moon": 130.0,
            "Mars": 100.0,
            "Mercury": 70.0,
            "Jupiter": 250.0,
            "Venus": 190.0,
            "Saturn": 310.0,
        },
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )

    by_pair = {(a.body1, a.body2): a for a in aspects}
    trine = by_pair[("Sun", "Moon")]
    square = by_pair[("Sun", "Mars")]

    assert trine.relation == "open_friend"
    assert trine.is_benefic_relation is True
    assert trine.relation_strength == pytest.approx(0.75)
    assert square.relation == "secret_enemy"
    assert square.is_benefic_relation is False
    assert square.relation_strength == pytest.approx(0.5)


def test_tajika_yogas_distinguish_ithasala_from_isarpha() -> None:
    aspects = tajika_aspects(
        {
            "Sun": 10.0,
            "Moon": 130.0,
            "Mars": 100.0,
            "Mercury": 70.0,
            "Jupiter": 250.0,
            "Venus": 190.0,
            "Saturn": 310.0,
        },
        planet_speeds={
            "Sun": 1.0,
            "Moon": 13.0,
            "Mars": 0.6,
            "Mercury": 1.2,
            "Jupiter": 0.08,
            "Venus": 1.1,
            "Saturn": 0.03,
        },
    )
    yogas = {(y.body1, y.body2): y for y in tajika_yogas(aspects)}

    assert yogas[("Sun", "Moon")].name == "Isarpha"
    assert yogas[("Sun", "Moon")].favorable is False
    assert yogas[("Sun", "Mars")].name == "Ithasala"
    assert yogas[("Sun", "Mars")].favorable is True


def test_build_varshaphal_chart_collects_muntha_and_sahams(monkeypatch: pytest.MonkeyPatch) -> None:
    houses = calculate_houses(2451545.0, 0.0, 0.0, HouseSystem.WHOLE_SIGN, ayanamsa_offset=0.0)
    fake_chart = SimpleNamespace(
        planets={
            "Sun": SimpleNamespace(longitude=100.0, speed=1.0),
            "Moon": SimpleNamespace(longitude=130.0, speed=12.0),
            "Mars": SimpleNamespace(longitude=160.0, speed=0.5),
            "Mercury": SimpleNamespace(longitude=190.0, speed=1.2),
            "Jupiter": SimpleNamespace(longitude=220.0, speed=0.1),
            "Venus": SimpleNamespace(longitude=250.0, speed=1.1),
            "Saturn": SimpleNamespace(longitude=280.0, speed=0.05),
        },
        is_day=True,
    )

    monkeypatch.setattr(varshaphal_module, "_varshaphal_jd", lambda *args, **kwargs: 2460123.25)
    monkeypatch.setattr(varshaphal_module, "_varshaphal_chart", lambda *args, **kwargs: fake_chart)
    monkeypatch.setattr(varshaphal_module, "ayanamsa", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(varshaphal_module, "calculate_houses", lambda *args, **kwargs: houses)
    monkeypatch.setattr(varshaphal_module, "tropical_to_sidereal", lambda lon, jd, system=None: lon % 360.0)

    result = build_varshaphal_chart(
        birth_jd=2451545.0,
        natal_latitude=12.0,
        natal_longitude=77.0,
        year=2001,
        latitude=28.6,
        longitude=77.2,
        house_system=HouseSystem.WHOLE_SIGN,
    )

    assert result.return_year == 2001
    assert result.years_elapsed == 1
    assert result.muntha_longitude == pytest.approx((houses.asc + 30.0) % 360.0)
    assert result.muntha_profile.muntha_lord == result.muntha_lord
    assert result.muntha_profile.muntha_house == result.muntha_house
    assert any(aspect.relation == "open_friend" for aspect in result.tajika_aspects)
    assert any(yoga.name in {"Ithasala", "Isarpha"} for yoga in result.tajika_yogas)
    assert result.saham("Punya").name == "Punya"
    assert result.muntha_house in range(1, 13)

from __future__ import annotations

import importlib

import moira.facade as facade
from moira.harmonic_transits import (
    HarmonicTransitSample,
    MixedOriginHarmonicTransitForecastPolicy,
)
from moira.houses import HouseCusps

huber = importlib.import_module("moira.huber")
nine_parts = importlib.import_module("moira.nine_parts")


class _HarmonicChart:
    def longitudes(self, *, include_nodes: bool) -> dict[str, float]:
        assert include_nodes is False
        return {"Sun": 0.0, "Moon": 72.0}


def _house_cusps() -> HouseCusps:
    return HouseCusps(
        system="direct",
        cusps=tuple(float(index * 30) for index in range(12)),
        asc=0.0,
        mc=90.0,
        armc=90.0,
    )


def _nine_parts_planets() -> dict[str, float]:
    return {
        "Sun": 20.0,
        "Moon": 55.0,
        "Mars": 130.0,
        "Jupiter": 210.0,
        "Saturn": 285.0,
        "North Node": 100.0,
    }


def test_classical_facade_preserves_fractional_harmonic() -> None:
    positions = facade.Moira().harmonic(_HarmonicChart(), 5.5)

    by_body = {position.planet: position for position in positions}
    assert by_body["Moon"].harmonic == 5.5
    assert by_body["Moon"].harmonic_longitude == 36.0


def test_classical_facade_exposes_sampled_harmonic_transit_forecast() -> None:
    policy = MixedOriginHarmonicTransitForecastPolicy(harmonics=(5,))
    samples = (HarmonicTransitSample(2451545.0, {"Mars": 144.0}),)

    result = facade.Moira().harmonic_transit_forecast(
        {"Sun": 0.0, "Moon": 72.0},
        samples,
        policy,
    )

    assert result.window_count == 1
    assert result.windows[0].harmonic == 5


def test_classical_facade_huber_wrappers_delegate_to_engine() -> None:
    engine = facade.Moira()
    houses = _house_cusps()
    points = {"Sun": 20.0, "Moon": 55.0}

    assert engine.huber_house_zones(houses) == huber.house_zones(houses)
    assert engine.huber_age_point(12.5, houses) == huber.age_point(12.5, houses)
    assert engine.huber_dynamic_intensity(3, 0.5) == huber.dynamic_intensity(3, 0.5)
    assert engine.huber_intensity_at(45.0, houses) == huber.intensity_at(45.0, houses)
    assert engine.huber_chart_intensity_profile(points, houses) == huber.chart_intensity_profile(
        points,
        houses,
    )
    assert engine.huber_age_point_contacts(
        houses,
        points,
        orb=2.0,
        start_age=0.0,
        end_age=6.0,
        step_years=0.5,
    ) == huber.age_point_contacts(
        houses,
        points,
        orb=2.0,
        start_age=0.0,
        end_age=6.0,
        step_years=0.5,
    )


def test_classical_facade_nine_parts_delegates_to_engine() -> None:
    engine = facade.Moira()
    planets = _nine_parts_planets()

    via_facade = engine.nine_parts(15.0, planets, False)
    direct = nine_parts.nine_parts_abu_mashar(15.0, planets, False)

    assert via_facade == direct
    assert nine_parts.validate_nine_parts_output(via_facade) == []


def test_classical_facade_nine_parts_accepts_policy() -> None:
    engine = facade.Moira()
    planets = _nine_parts_planets()
    policy = nine_parts.NinePartsPolicy()

    assert engine.nine_parts(15.0, planets, True, policy=policy) == nine_parts.nine_parts_abu_mashar(
        15.0,
        planets,
        True,
        policy=policy,
    )

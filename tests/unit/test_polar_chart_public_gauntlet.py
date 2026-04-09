from __future__ import annotations

from datetime import timezone

import pytest

from moira import Moira
from moira.chart import create_chart
from moira.constants import Body, HouseSystem
from moira.houses import assign_house, describe_angularity
from moira.julian import datetime_from_jd

_EPOCHS_UT = {
    "j2000": 2451545.0,
    "jupiter_saturn_2020": 2459205.25,
}
_POLAR_OBSERVERS = {
    "north_80": (80.0, 15.0),
    "south_80": (-80.0, 140.0),
}
_POLAR_LIMITED_SYSTEMS = (
    HouseSystem.PLACIDUS,
    HouseSystem.KOCH,
    HouseSystem.PULLEN_SD,
)
_SUPPORTED_PUBLIC_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MARS,
    Body.JUPITER,
)
_LOT_TOLERANCE_DEG = 1e-9


def _body_list() -> list[str]:
    return list(_SUPPORTED_PUBLIC_BODIES)


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


def _assert_same_house_figure(left, right) -> None:
    assert left.asc == pytest.approx(right.asc, abs=1e-8)
    assert left.mc == pytest.approx(right.mc, abs=1e-8)

    for left_cusp, right_cusp in zip(left.cusps, right.cusps, strict=True):
        assert left_cusp == pytest.approx(right_cusp, abs=1e-8)


@pytest.mark.requires_ephemeris
def test_public_chart_context_preserves_polar_fallback_truth_across_matrix() -> None:
    for epoch_name, jd_ut in _EPOCHS_UT.items():
        for observer_name, (latitude_deg, longitude_deg) in _POLAR_OBSERVERS.items():
            porphyry_ctx = create_chart(
                jd_ut,
                latitude_deg,
                longitude_deg,
                house_system=HouseSystem.PORPHYRY,
                bodies=_body_list(),
            )
            assert porphyry_ctx.houses is not None

            for system in _POLAR_LIMITED_SYSTEMS:
                fallback_ctx = create_chart(
                    jd_ut,
                    latitude_deg,
                    longitude_deg,
                    house_system=system,
                    bodies=_body_list(),
                )

                assert fallback_ctx.houses is not None, (epoch_name, observer_name, system)
                assert fallback_ctx.houses.system == system, (epoch_name, observer_name, system)
                assert fallback_ctx.houses.effective_system == HouseSystem.PORPHYRY, (
                    epoch_name,
                    observer_name,
                    system,
                )
                assert fallback_ctx.houses.fallback is True, (epoch_name, observer_name, system)
                assert fallback_ctx.is_day == porphyry_ctx.is_day, (epoch_name, observer_name, system)
                _assert_same_house_figure(fallback_ctx.houses, porphyry_ctx.houses)


@pytest.mark.requires_ephemeris
def test_public_chart_body_placements_and_angularity_match_porphyry_under_fallback() -> None:
    for epoch_name, jd_ut in _EPOCHS_UT.items():
        for observer_name, (latitude_deg, longitude_deg) in _POLAR_OBSERVERS.items():
            porphyry_ctx = create_chart(
                jd_ut,
                latitude_deg,
                longitude_deg,
                house_system=HouseSystem.PORPHYRY,
                bodies=_body_list(),
            )
            assert porphyry_ctx.houses is not None

            for system in _POLAR_LIMITED_SYSTEMS:
                fallback_ctx = create_chart(
                    jd_ut,
                    latitude_deg,
                    longitude_deg,
                    house_system=system,
                    bodies=_body_list(),
                )
                assert fallback_ctx.houses is not None

                for body in _SUPPORTED_PUBLIC_BODIES:
                    fallback_placement = assign_house(fallback_ctx.planets[body].longitude, fallback_ctx.houses)
                    porphyry_placement = assign_house(porphyry_ctx.planets[body].longitude, porphyry_ctx.houses)

                    assert fallback_placement.house == porphyry_placement.house, (
                        epoch_name,
                        observer_name,
                        system,
                        body,
                    )
                    assert fallback_placement.exact_on_cusp is porphyry_placement.exact_on_cusp, (
                        epoch_name,
                        observer_name,
                        system,
                        body,
                    )

                    fallback_angularity = describe_angularity(fallback_placement)
                    porphyry_angularity = describe_angularity(porphyry_placement)
                    assert fallback_angularity.category == porphyry_angularity.category, (
                        epoch_name,
                        observer_name,
                        system,
                        body,
                    )


@pytest.mark.requires_ephemeris
def test_public_chart_lots_match_porphyry_under_polar_fallback() -> None:
    engine = Moira()

    for epoch_name, jd_ut in _EPOCHS_UT.items():
        dt = datetime_from_jd(jd_ut).astimezone(timezone.utc)
        chart = engine.chart(dt, bodies=_body_list())

        for observer_name, (latitude_deg, longitude_deg) in _POLAR_OBSERVERS.items():
            porphyry_houses = engine.houses(dt, latitude_deg, longitude_deg, HouseSystem.PORPHYRY)
            porphyry_lots = {part.name: part.longitude for part in engine.lots(chart, porphyry_houses)}

            for system in _POLAR_LIMITED_SYSTEMS:
                fallback_houses = engine.houses(dt, latitude_deg, longitude_deg, system)
                fallback_lots = {part.name: part.longitude for part in engine.lots(chart, fallback_houses)}

                assert fallback_lots.keys() == porphyry_lots.keys(), (epoch_name, observer_name, system)

                for name, lot_longitude_deg in fallback_lots.items():
                    assert abs(_signed_angle_delta(lot_longitude_deg, porphyry_lots[name])) < _LOT_TOLERANCE_DEG, (
                        epoch_name,
                        observer_name,
                        system,
                        name,
                    )

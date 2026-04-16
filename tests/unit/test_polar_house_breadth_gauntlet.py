from __future__ import annotations

import pytest

from moira.constants import Body, HouseSystem
from moira.houses import HousePolicy, assign_house, calculate_houses
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity
from moira.planets import planet_at

_EPOCHS_UT = {
    "1000_bce": 1355818.0,
    "j2000": 2451545.0,
    "jupiter_saturn_2020": 2459205.25,
    "3000_ad": 2816788.0,
}
_POLAR_LIMITED_SYSTEMS = (
    HouseSystem.PLACIDUS,
    HouseSystem.KOCH,
    )
_POLAR_OBSERVERS = {
    "north_67": (67.0, 18.0),
    "north_80": (80.0, 15.0),
    "south_67": (-67.0, -68.0),
    "south_80": (-80.0, 140.0),
}
_HOUSE_SENSITIVE_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MARS,
    Body.JUPITER,
)


def _critical_latitude_deg(jd_ut: float) -> float:
    return 90.0 - true_obliquity(ut_to_tt(jd_ut))


def _assert_same_house_figure(left, right) -> None:
    assert left.asc == pytest.approx(right.asc, abs=1e-8)
    assert left.mc == pytest.approx(right.mc, abs=1e-8)

    for left_cusp, right_cusp in zip(left.cusps, right.cusps, strict=True):
        assert left_cusp == pytest.approx(right_cusp, abs=1e-8)


def test_dynamic_critical_latitude_fallback_holds_across_epoch_matrix() -> None:
    for epoch_name, jd_ut in _EPOCHS_UT.items():
        critical_latitude_deg = _critical_latitude_deg(jd_ut)
        below_latitude_deg = critical_latitude_deg - 0.5
        above_latitude_deg = critical_latitude_deg + 0.5

        for system in _POLAR_LIMITED_SYSTEMS:
            below = calculate_houses(jd_ut, below_latitude_deg, 0.0, system)
            above = calculate_houses(jd_ut, above_latitude_deg, 0.0, system)
            porphyry = calculate_houses(jd_ut, above_latitude_deg, 0.0, HouseSystem.PORPHYRY)

            assert below.system == system, (epoch_name, system)
            assert below.effective_system == system, (epoch_name, system)
            assert below.fallback is False, (epoch_name, system)

            assert above.system == system, (epoch_name, system)
            assert above.effective_system == HouseSystem.PORPHYRY, (epoch_name, system)
            assert above.fallback is True, (epoch_name, system)
            assert "critical latitude" in (above.fallback_reason or "").lower(), (epoch_name, system)
            _assert_same_house_figure(above, porphyry)


def test_strict_polar_policy_raises_across_dynamic_critical_latitude_matrix() -> None:
    for epoch_name, jd_ut in _EPOCHS_UT.items():
        above_latitude_deg = _critical_latitude_deg(jd_ut) + 0.5

        for system in _POLAR_LIMITED_SYSTEMS:
            with pytest.raises(ValueError, match="critical latitude"):
                calculate_houses(
                    jd_ut,
                    above_latitude_deg,
                    0.0,
                    system,
                    policy=HousePolicy.strict(),
                )


@pytest.mark.requires_ephemeris
def test_fallback_house_assignments_match_direct_porphyry_across_polar_matrix() -> None:
    for epoch_name, jd_ut in _EPOCHS_UT.items():
        for observer_name, (latitude_deg, longitude_deg) in _POLAR_OBSERVERS.items():
            for system in _POLAR_LIMITED_SYSTEMS:
                fallback = calculate_houses(jd_ut, latitude_deg, longitude_deg, system)
                porphyry = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.PORPHYRY)

                assert fallback.effective_system == HouseSystem.PORPHYRY, (
                    epoch_name,
                    observer_name,
                    system,
                )
                _assert_same_house_figure(fallback, porphyry)

                for body in _HOUSE_SENSITIVE_BODIES:
                    body_longitude_deg = planet_at(body, jd_ut).longitude
                    fallback_placement = assign_house(body_longitude_deg, fallback)
                    porphyry_placement = assign_house(body_longitude_deg, porphyry)

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


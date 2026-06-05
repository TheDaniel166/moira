from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira import Moira
from moira.asteroids import asteroid_at
from moira.chart import create_chart
from moira.constants import Body
from moira.planets import all_planets_at, planet_at


@pytest.mark.requires_ephemeris
def test_planet_at_chiron_matches_asteroid_oracle() -> None:
    jd_ut = 2451545.0

    bridged = planet_at(Body.CHIRON, jd_ut)
    reference = asteroid_at(Body.CHIRON, jd_ut)

    assert bridged.name == reference.name
    assert bridged.longitude == pytest.approx(reference.longitude, abs=1e-12)
    assert bridged.latitude == pytest.approx(reference.latitude, abs=1e-12)
    assert bridged.distance == pytest.approx(reference.distance, abs=1e-6)
    assert bridged.speed == pytest.approx(reference.speed, abs=1e-9)
    assert bridged.retrograde is reference.retrograde


@pytest.mark.requires_ephemeris
def test_all_planets_at_includes_chiron_when_explicitly_requested() -> None:
    jd_ut = 2451545.0

    result = all_planets_at(jd_ut, bodies=[Body.SUN, Body.CHIRON])

    assert set(result) == {Body.SUN, Body.CHIRON}
    assert result[Body.CHIRON].name == Body.CHIRON


@pytest.mark.requires_ephemeris
def test_create_chart_default_body_set_excludes_chiron() -> None:
    chart = create_chart(2451545.0, 51.5, -0.1)

    assert Body.CHIRON not in chart.planets


@pytest.mark.requires_ephemeris
def test_create_chart_accepts_explicit_chiron_body_request() -> None:
    chart = create_chart(2451545.0, 51.5, -0.1, bodies=[Body.SUN, Body.CHIRON])

    assert set(chart.planets) == {Body.SUN, Body.CHIRON}
    assert chart.planets[Body.CHIRON].name == Body.CHIRON


@pytest.mark.requires_ephemeris
def test_moira_chart_accepts_explicit_chiron_body_request(moira_engine) -> None:
    chart = moira_engine.chart(
        datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        bodies=[Body.SUN, Body.CHIRON],
    )

    assert set(chart.planets) == {Body.SUN, Body.CHIRON}
    assert chart.planets[Body.CHIRON].name == Body.CHIRON



@pytest.mark.requires_ephemeris
def test_planet_at_chiron_supports_partial_correction_modes() -> None:
    # apparent=False (geometric) is now routed through _asteroid_at_with_flags
    result = planet_at(Body.CHIRON, 2451545.0, apparent=False)
    assert result.name == Body.CHIRON
    assert 0.0 <= result.longitude < 360.0

    # aberration=False is also supported
    result_no_aber = planet_at(Body.CHIRON, 2451545.0, aberration=False)
    assert result_no_aber.name == Body.CHIRON
    assert 0.0 <= result_no_aber.longitude < 360.0


def test_planet_at_chiron_still_rejects_unsupported_modes() -> None:
    # Observer coordinates are not supported for small bodies
    with pytest.raises(ValueError):
        planet_at(Body.CHIRON, 2451545.0, observer_lat=51.5, observer_lon=-0.1, lst_deg=0.0)

    # Barycentric center is not supported for small bodies
    with pytest.raises(ValueError):
        planet_at(Body.CHIRON, 2451545.0, center="barycentric")

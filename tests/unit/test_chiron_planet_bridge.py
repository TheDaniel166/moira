from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira import Moira
from moira.asteroids import asteroid_at
from moira.chart import create_chart
from moira.constants import Body
from moira.planets import all_planets_at, planet_at


@pytest.fixture
def borrowed_small_body_moira_engine(
    monkeypatch: pytest.MonkeyPatch,
    small_body_reader_pool,
):
    """Bind a facade to the admitted pool without discovering or owning it."""

    with monkeypatch.context() as constructor_patch:
        constructor_patch.setattr(
            Moira,
            "_try_initialize_reader",
            lambda self: None,
        )
        engine = Moira()
    engine._reader_obj = small_body_reader_pool
    try:
        yield engine
    finally:
        # The session fixture owns and closes the pool.
        engine._reader_obj = None


@pytest.mark.requires_ephemeris
def test_planet_at_chiron_matches_asteroid_oracle(
    small_body_reader_pool,
) -> None:
    jd_ut = 2451545.0

    bridged = planet_at(
        Body.CHIRON,
        jd_ut,
        reader=small_body_reader_pool,
    )
    reference = asteroid_at(
        Body.CHIRON,
        jd_ut,
        reader=small_body_reader_pool,
    )

    assert bridged.name == reference.name
    assert bridged.longitude == pytest.approx(reference.longitude, abs=1e-12)
    assert bridged.latitude == pytest.approx(reference.latitude, abs=1e-12)
    assert bridged.distance == pytest.approx(reference.distance, abs=1e-6)
    assert bridged.speed == pytest.approx(reference.speed, abs=1e-9)
    assert bridged.retrograde is reference.retrograde


@pytest.mark.requires_ephemeris
def test_all_planets_at_includes_chiron_when_explicitly_requested(
    small_body_reader_pool,
) -> None:
    jd_ut = 2451545.0

    result = all_planets_at(
        jd_ut,
        bodies=[Body.SUN, Body.CHIRON],
        reader=small_body_reader_pool,
    )

    assert set(result) == {Body.SUN, Body.CHIRON}
    assert result[Body.CHIRON].name == Body.CHIRON


@pytest.mark.requires_ephemeris
def test_create_chart_default_body_set_excludes_chiron(
    planetary_reader,
) -> None:
    chart = create_chart(
        2451545.0,
        51.5,
        -0.1,
        reader=planetary_reader,
    )

    assert Body.CHIRON not in chart.planets


@pytest.mark.requires_ephemeris
def test_create_chart_accepts_explicit_chiron_body_request(
    small_body_reader_pool,
) -> None:
    chart = create_chart(
        2451545.0,
        51.5,
        -0.1,
        bodies=[Body.SUN, Body.CHIRON],
        reader=small_body_reader_pool,
    )

    assert set(chart.planets) == {Body.SUN, Body.CHIRON}
    assert chart.planets[Body.CHIRON].name == Body.CHIRON


@pytest.mark.requires_ephemeris
def test_moira_chart_accepts_explicit_chiron_body_request(
    borrowed_small_body_moira_engine,
) -> None:
    chart = borrowed_small_body_moira_engine.chart(
        datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        bodies=[Body.SUN, Body.CHIRON],
    )

    assert set(chart.planets) == {Body.SUN, Body.CHIRON}
    assert chart.planets[Body.CHIRON].name == Body.CHIRON



@pytest.mark.requires_ephemeris
def test_planet_at_chiron_supports_partial_correction_modes(
    small_body_reader_pool,
) -> None:
    # apparent=False (geometric) is now routed through _asteroid_at_with_flags
    result = planet_at(
        Body.CHIRON,
        2451545.0,
        reader=small_body_reader_pool,
        apparent=False,
    )
    assert result.name == Body.CHIRON
    assert 0.0 <= result.longitude < 360.0

    # aberration=False is also supported
    result_no_aber = planet_at(
        Body.CHIRON,
        2451545.0,
        reader=small_body_reader_pool,
        aberration=False,
    )
    assert result_no_aber.name == Body.CHIRON
    assert 0.0 <= result_no_aber.longitude < 360.0


def test_planet_at_chiron_still_rejects_unsupported_modes() -> None:
    reader = object()
    # The admitted topocentric path is apparent, geocentric, and ecliptic only.
    with pytest.raises(ValueError):
        planet_at(
            Body.CHIRON,
            2451545.0,
            reader=reader,
            apparent=False,
            observer_lat=51.5,
            observer_lon=-0.1,
            lst_deg=0.0,
        )

    # Barycentric center is not supported for small bodies
    with pytest.raises(ValueError):
        planet_at(
            Body.CHIRON,
            2451545.0,
            reader=reader,
            center="barycentric",
        )

    with pytest.raises(ValueError):
        planet_at(
            Body.CHIRON,
            2451545.0,
            reader=reader,
            frame="cartesian",
            observer_lat=51.5,
            observer_lon=-0.1,
            lst_deg=0.0,
        )

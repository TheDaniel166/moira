from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import moira.local_space as ls
import moira_server.services.local_space as local_space_service
from moira_server.models.local_space import LocalSpaceChartPositionsRequest


@dataclass
class _FakeSky:
    right_ascension: float
    declination: float


@dataclass
class _FakeChart:
    jd_ut: float
    planets: dict[str, object]

    @property
    def jd_tt(self) -> float:
        return self.jd_ut + 0.1


def _by_body(rows: list[ls.LocalSpacePosition]) -> dict[str, ls.LocalSpacePosition]:
    return {row.body: row for row in rows}


def test_local_space_cardinal_horizon_positions_at_equator() -> None:
    rows = _by_body(
        ls.local_space_positions(
                {
                    "Meridian": (0.0, 0.0),
                    "East": (90.0, 0.0),
                    "West": (270.0, 0.0),
                    "Nadir": (180.0, 0.0),
                },
            latitude=0.0,
            lst_deg=0.0,
        )
    )

    assert rows["Meridian"].altitude == pytest.approx(90.0)
    assert rows["Meridian"].azimuth == pytest.approx(180.0)
    assert rows["Meridian"].is_above is True

    assert rows["East"].altitude == pytest.approx(0.0)
    assert rows["East"].azimuth == pytest.approx(90.0)
    assert rows["East"].is_above is True

    assert rows["West"].altitude == pytest.approx(0.0)
    assert rows["West"].azimuth == pytest.approx(270.0)
    assert rows["West"].is_above is True

    assert rows["Nadir"].altitude == pytest.approx(-90.0)
    assert rows["Nadir"].is_above is False


def test_local_space_north_and_south_horizon_directions() -> None:
    rows = _by_body(
        ls.local_space_positions(
            {
                "North": (0.0, 0.0),
                "South": (180.0, 0.0),
            },
            latitude=45.0,
            lst_deg=0.0,
        )
    )

    assert rows["North"].altitude == pytest.approx(45.0)
    assert rows["North"].azimuth == pytest.approx(180.0)
    assert rows["South"].altitude == pytest.approx(-45.0)
    assert rows["South"].azimuth == pytest.approx(0.0)


def test_local_space_sorts_by_azimuth() -> None:
    rows = ls.local_space_positions(
        {
            "C": (90.0, 0.0),
            "A": (0.0, 0.0),
            "B": (270.0, 0.0),
        },
        latitude=0.0,
        lst_deg=0.0,
    )
    assert [row.azimuth for row in rows] == sorted(row.azimuth for row in rows)


@pytest.mark.parametrize(
    ("planet_ra_dec", "latitude", "lst_deg", "message"),
    [
        ({"Sun": (0.0, 0.0)}, float("nan"), 0.0, "latitude"),
        ({"Sun": (0.0, 0.0)}, 91.0, 0.0, "latitude"),
        ({"Sun": (0.0, 0.0)}, 0.0, float("nan"), "lst_deg"),
        ({"Sun": (float("nan"), 0.0)}, 0.0, 0.0, "RA/Dec"),
        ({"Sun": (0.0, 91.0)}, 0.0, 0.0, "declination"),
        ({"": (0.0, 0.0)}, 0.0, 0.0, "body names"),
    ],
)
def test_local_space_rejects_invalid_inputs(
    planet_ra_dec: dict[str, tuple[float, float]],
    latitude: float,
    lst_deg: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ls.local_space_positions(planet_ra_dec, latitude=latitude, lst_deg=lst_deg)


def test_compass_direction_octants_and_repr() -> None:
    labels = {
        0.0: "N",
        45.0: "NE",
        90.0: "E",
        135.0: "SE",
        180.0: "S",
        225.0: "SW",
        270.0: "W",
        315.0: "NW",
    }
    for az, label in labels.items():
        row = ls.LocalSpacePosition("X", azimuth=az, altitude=1.0, is_above=True)
        assert row.compass_direction() == label

    assert "above horizon" in repr(ls.LocalSpacePosition("Sun", azimuth=90.0, altitude=10.0, is_above=True))
    assert "below horizon" in repr(ls.LocalSpacePosition("Sun", azimuth=270.0, altitude=-10.0, is_above=False))


def test_local_space_from_chart_uses_local_sidereal_and_chart_radec(monkeypatch: pytest.MonkeyPatch) -> None:
    chart = _FakeChart(jd_ut=2460389.75, planets={"Sun": object(), "Moon": object()})
    calls: dict[str, object] = {}

    monkeypatch.setattr("moira.obliquity.nutation", lambda jd_tt: (0.2, 0.0))
    monkeypatch.setattr("moira.obliquity.true_obliquity", lambda jd_tt: 23.4)
    monkeypatch.setattr("moira.julian.local_sidereal_time", lambda jd_ut, lon, dpsi, obliq: 211.0)

    def fake_sky_position_at(body: str, jd_ut: float, observer_lat: float, observer_lon: float):
        calls.setdefault("sky", []).append((body, jd_ut, observer_lat, observer_lon))
        return _FakeSky(
            right_ascension={"Sun": 10.0, "Moon": 20.0}[body],
            declination={"Sun": 1.0, "Moon": -2.0}[body],
        )

    def fake_local_space_positions(planet_ra_dec: dict[str, tuple[float, float]], latitude: float, lst_deg: float):
        calls["planet_ra_dec"] = planet_ra_dec
        calls["latitude"] = latitude
        calls["lst_deg"] = lst_deg
        return ["sentinel"]

    monkeypatch.setattr("moira.planets.sky_position_at", fake_sky_position_at)
    monkeypatch.setattr(ls, "local_space_positions", fake_local_space_positions)

    result = ls.local_space_from_chart(chart, observer_lat=40.7128, observer_lon=-74.006, bodies=["Sun", "Moon"])

    assert result == ["sentinel"]
    assert calls["sky"] == [
        ("Sun", chart.jd_ut, 40.7128, -74.006),
        ("Moon", chart.jd_ut, 40.7128, -74.006),
    ]
    assert calls["planet_ra_dec"] == {"Sun": (10.0, 1.0), "Moon": (20.0, -2.0)}
    assert calls["latitude"] == pytest.approx(40.7128)
    assert calls["lst_deg"] == pytest.approx(211.0)


def test_local_space_chart_service_resolves_utc_tt_and_ut1_for_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_dt = datetime(2024, 3, 20, 12, tzinfo=timezone.utc)
    chart = SimpleNamespace(
        jd_ut=100.0,
        datetime_utc=requested_dt,
        planets={"Sun": object()},
    )
    calls: dict[str, object] = {"tt": [], "ut1": [], "sky": []}

    monkeypatch.setattr(local_space_service, "_build_chart", lambda engine, request: chart)

    def fake_utc_to_tt(jd_utc: float) -> float:
        calls["tt"].append(jd_utc)
        return 200.0

    def fake_utc_to_ut1(jd_utc: float) -> float:
        calls["ut1"].append(jd_utc)
        return 99.0

    monkeypatch.setattr(local_space_service, "utc_to_tt", fake_utc_to_tt)
    monkeypatch.setattr(local_space_service, "utc_to_ut1", fake_utc_to_ut1)
    monkeypatch.setattr(local_space_service, "nutation", lambda jd_tt: (0.2, 0.0))
    monkeypatch.setattr(local_space_service, "true_obliquity", lambda jd_tt: 23.5)

    def fake_local_sidereal_time(
        jd_ut1: float,
        longitude: float,
        delta_psi: float,
        obliquity: float,
    ) -> float:
        calls["sidereal"] = (jd_ut1, longitude, delta_psi, obliquity)
        return 123.0

    def fake_sky_position_at(body: str, jd_ut1: float, **kwargs: object) -> SimpleNamespace:
        calls["sky"].append((body, jd_ut1, kwargs))
        return SimpleNamespace(right_ascension=10.0, declination=2.0)

    def fake_local_space_positions(
        planet_ra_dec: dict[str, tuple[float, float]],
        *,
        latitude: float,
        lst_deg: float,
    ) -> list[SimpleNamespace]:
        calls["positions"] = (planet_ra_dec, latitude, lst_deg)
        return [SimpleNamespace(body="Sun")]

    monkeypatch.setattr(local_space_service, "local_sidereal_time", fake_local_sidereal_time)
    monkeypatch.setattr(local_space_service, "sky_position_at", fake_sky_position_at)
    monkeypatch.setattr(local_space_service, "local_space_positions", fake_local_space_positions)

    request = LocalSpaceChartPositionsRequest(
        dt=requested_dt,
        bodies=["Sun"],
        observer_lat=40.0,
        observer_lon=-74.0,
        observer_elev_m=10.0,
    )
    result = local_space_service.compute_local_space_chart_positions(
        SimpleNamespace(_reader="reader"),
        request,
    )

    assert calls["tt"] == [100.0]
    assert calls["ut1"] == [100.0]
    assert calls["sidereal"] == (99.0, -74.0, 0.2, 23.5)
    assert calls["sky"] == [
        (
            "Sun",
            99.0,
            {
                "observer_lat": 40.0,
                "observer_lon": -74.0,
                "observer_elev_m": 10.0,
                "reader": "reader",
            },
        )
    ]
    assert calls["positions"] == ({"Sun": (10.0, 2.0)}, 40.0, 123.0)
    assert result.provenance.jd_ut == 99.0
    assert result.provenance.jd_tt == 200.0

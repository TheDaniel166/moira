from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

import moira.astrocartography as acg


def _wrap_diff(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0) - 180.0


def _wrap_midpoint(a: float, b: float) -> float:
    return (a + _wrap_diff(b, a) / 2.0) % 360.0


def _lat_grid(lat_step: float) -> list[float]:
    return [
        -89.0 + i * lat_step
        for i in range(int(178.0 / lat_step) + 1)
        if -89.0 + i * lat_step <= 89.0
    ]


def _lines_by_type(lines: list[acg.ACGLine]) -> dict[tuple[str, str], acg.ACGLine]:
    return {(line.planet, line.line_type): line for line in lines}


def _points_by_type(
    points: list[acg.SubPlanetaryPoint],
) -> dict[tuple[str, str], acg.SubPlanetaryPoint]:
    return {(point.planet, point.point_type): point for point in points}


def test_acg_lines_returns_four_lines_per_body_in_expected_shape() -> None:
    lines = acg.acg_lines({"Sun": (100.0, 10.0), "Moon": (250.0, -5.0)}, gmst_deg=20.0, lat_step=30.0)

    assert len(lines) == 8
    by_key = _lines_by_type(lines)
    for body in ("Sun", "Moon"):
        assert by_key[(body, "MC")].longitude is not None
        assert by_key[(body, "MC")].points == []
        assert by_key[(body, "IC")].longitude is not None
        assert by_key[(body, "IC")].points == []
        assert by_key[(body, "ASC")].longitude is None
        assert by_key[(body, "ASC")].points
        assert by_key[(body, "DSC")].longitude is None
        assert by_key[(body, "DSC")].points


def test_mc_and_ic_are_antipodal_meridians() -> None:
    line_map = _lines_by_type(acg.acg_lines({"Sun": (100.0, 15.0)}, gmst_deg=20.0))
    mc = line_map[("Sun", "MC")]
    ic = line_map[("Sun", "IC")]

    assert mc.longitude == pytest.approx(80.0)
    assert ic.longitude == pytest.approx(260.0)
    assert _wrap_diff(ic.longitude, mc.longitude) == pytest.approx(-180.0)


def test_zero_declination_body_has_constant_asc_dsc_meridians() -> None:
    gmst = 20.0
    ra = 100.0
    lines = _lines_by_type(acg.acg_lines({"Sun": (ra, 0.0)}, gmst_deg=gmst, lat_step=30.0))
    asc = lines[("Sun", "ASC")]
    dsc = lines[("Sun", "DSC")]
    lon_mc = (ra - gmst) % 360.0

    expected_asc = (lon_mc - 90.0) % 360.0
    expected_dsc = (lon_mc + 90.0) % 360.0
    assert [lat for lat, _ in asc.points] == _lat_grid(30.0)
    assert [lat for lat, _ in dsc.points] == _lat_grid(30.0)
    assert all(lon == pytest.approx(expected_asc) for _, lon in asc.points)
    assert all(lon == pytest.approx(expected_dsc) for _, lon in dsc.points)


def test_high_declination_body_skips_circumpolar_latitudes() -> None:
    lines = _lines_by_type(acg.acg_lines({"Sun": (0.0, 80.0)}, gmst_deg=0.0, lat_step=1.0))
    asc = lines[("Sun", "ASC")]
    dsc = lines[("Sun", "DSC")]

    assert asc.points
    assert dsc.points
    assert len(asc.points) < len(_lat_grid(1.0))
    assert max(abs(lat) for lat, _ in asc.points) <= 10.0
    assert max(abs(lat) for lat, _ in dsc.points) <= 10.0


@pytest.mark.parametrize("lat_step", [0.0, -1.0, math.inf, math.nan, 179.0])
def test_acg_lines_rejects_invalid_lat_step(lat_step: float) -> None:
    with pytest.raises(ValueError, match="lat_step"):
        acg.acg_lines({"Sun": (100.0, 10.0)}, gmst_deg=20.0, lat_step=lat_step)


@pytest.mark.parametrize(
    "planet_ra_dec",
    [
        {"Sun": (math.nan, 10.0)},
        {"Sun": (100.0, math.inf)},
        {"Sun": (100.0, 91.0)},
    ],
)
def test_acg_lines_rejects_invalid_ra_dec(
    planet_ra_dec: dict[str, tuple[float, float]],
) -> None:
    with pytest.raises(ValueError):
        acg.acg_lines(planet_ra_dec, gmst_deg=20.0)


def test_acg_lines_rejects_non_finite_gmst() -> None:
    with pytest.raises(ValueError, match="gmst_deg"):
        acg.acg_lines({"Sun": (100.0, 10.0)}, gmst_deg=math.inf)


def test_asc_and_dsc_are_symmetric_about_mc_meridian() -> None:
    ra = 123.4
    dec = 23.5
    gmst = 45.6
    lon_mc = (ra - gmst) % 360.0
    lines = _lines_by_type(acg.acg_lines({"Sun": (ra, dec)}, gmst_deg=gmst, lat_step=10.0))
    asc = lines[("Sun", "ASC")]
    dsc = lines[("Sun", "DSC")]

    assert [lat for lat, _ in asc.points] == [lat for lat, _ in dsc.points]
    for (lat_a, lon_a), (lat_d, lon_d) in zip(asc.points, dsc.points):
        assert lat_a == pytest.approx(lat_d)
        assert _wrap_diff(lon_a, lon_mc) == pytest.approx(-_wrap_diff(lon_d, lon_mc))


def test_acgline_repr_reports_meridian_or_sample_count() -> None:
    mc = acg.ACGLine(planet="Sun", line_type="MC", longitude=12.3456)
    asc = acg.ACGLine(planet="Sun", line_type="ASC", points=[(-10.0, 20.0), (10.0, 30.0)])

    assert "lon=12.3456" in repr(mc)
    assert "2 points" in repr(asc)


def test_subplanetary_points_return_zenith_and_nadir_per_body() -> None:
    points = acg.subplanetary_points({"Sun": (100.0, 10.0), "Moon": (250.0, -5.0)}, gmst_deg=20.0)

    assert len(points) == 4
    by_key = _points_by_type(points)
    for body in ("Sun", "Moon"):
        assert by_key[(body, "Zenith")]
        assert by_key[(body, "Nadir")]


def test_subplanetary_points_use_hour_angle_longitude_and_antipode() -> None:
    point_map = _points_by_type(acg.subplanetary_points({"Sun": (100.0, 15.0)}, gmst_deg=20.0))
    zenith = point_map[("Sun", "Zenith")]
    nadir = point_map[("Sun", "Nadir")]

    assert zenith.longitude == pytest.approx(80.0)
    assert nadir.longitude == pytest.approx(-100.0)
    assert nadir.latitude == pytest.approx(-zenith.latitude)
    assert _wrap_diff(nadir.longitude, zenith.longitude) == pytest.approx(-180.0)


def test_subplanetary_points_convert_declination_to_geodetic_latitude() -> None:
    point_map = _points_by_type(acg.subplanetary_points({"Sun": (0.0, 45.0)}, gmst_deg=0.0))
    zenith = point_map[("Sun", "Zenith")]
    expected = math.degrees(math.atan(math.tan(math.radians(45.0)) / (1.0 - acg._WGS84_E2)))

    assert zenith.latitude == pytest.approx(expected)
    assert zenith.latitude > 45.0


def test_subplanetary_points_rejects_non_finite_gmst() -> None:
    with pytest.raises(ValueError, match="gmst_deg"):
        acg.subplanetary_points({"Sun": (100.0, 10.0)}, gmst_deg=math.nan)


def test_subplanetary_points_rejects_non_finite_ra_dec() -> None:
    with pytest.raises(ValueError, match="RA/Dec"):
        acg.subplanetary_points({"Sun": (100.0, math.inf)}, gmst_deg=20.0)


def test_subplanetary_point_repr_reports_coordinates() -> None:
    point = acg.SubPlanetaryPoint("Sun", "Zenith", 12.3456, -78.9)

    assert "lat=12.3456deg" in repr(point)
    assert "lon=-78.9000deg" in repr(point)


@dataclass
class _FakePlanet:
    right_ascension: float
    declination: float


@dataclass
class _FakeChart:
    jd_ut: float
    latitude: float
    longitude: float
    planets: dict[str, object]

    @property
    def jd_tt(self) -> float:
        return self.jd_ut + 0.1


def test_acg_from_chart_uses_apparent_sidereal_and_chart_planet_radec(monkeypatch: pytest.MonkeyPatch) -> None:
    chart = _FakeChart(
        jd_ut=2460389.75,
        latitude=40.7128,
        longitude=-74.006,
        planets={"Sun": object(), "Moon": object()},
    )
    calls: dict[str, object] = {}

    monkeypatch.setattr("moira.obliquity.nutation", lambda jd_tt: (0.2, 0.0))
    monkeypatch.setattr("moira.obliquity.true_obliquity", lambda jd_tt: 23.4)
    monkeypatch.setattr("moira.julian.apparent_sidereal_time", lambda jd_ut, dpsi, obliq: 111.0)

    def fake_sky_position_at(body: str, jd_ut: float, observer_lat: float, observer_lon: float):
        calls.setdefault("sky", []).append((body, jd_ut, observer_lat, observer_lon))
        return _FakePlanet(
            right_ascension={"Sun": 10.0, "Moon": 20.0}[body],
            declination={"Sun": 1.0, "Moon": -2.0}[body],
        )

    def fake_acg_lines(planet_ra_dec: dict[str, tuple[float, float]], gmst_deg: float, lat_step: float = 2.0):
        calls["planet_ra_dec"] = planet_ra_dec
        calls["gmst_deg"] = gmst_deg
        calls["lat_step"] = lat_step
        return ["sentinel"]

    monkeypatch.setattr("moira.planets.sky_position_at", fake_sky_position_at)
    monkeypatch.setattr(acg, "acg_lines", fake_acg_lines)

    result = acg.acg_from_chart(chart, bodies=["Sun", "Moon"], lat_step=5.0)

    assert result == ["sentinel"]
    assert calls["sky"] == [
        ("Sun", chart.jd_ut, chart.latitude, chart.longitude),
        ("Moon", chart.jd_ut, chart.latitude, chart.longitude),
    ]
    assert calls["planet_ra_dec"] == {"Sun": (10.0, 1.0), "Moon": (20.0, -2.0)}
    assert calls["gmst_deg"] == pytest.approx(111.0)
    assert calls["lat_step"] == pytest.approx(5.0)


def test_subplanetary_from_chart_uses_geocentric_ecliptic_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    chart = _FakeChart(
        jd_ut=2460389.75,
        latitude=40.7128,
        longitude=-74.006,
        planets={"Sun": object(), "Moon": object()},
    )
    calls: dict[str, object] = {}

    @dataclass
    class _FakePlanetData:
        longitude: float
        latitude: float

    monkeypatch.setattr("moira.julian.utc_to_ut1", lambda jd: jd + 0.01)
    monkeypatch.setattr("moira.julian.utc_to_tt", lambda jd: jd + 0.1)
    monkeypatch.setattr("moira.obliquity.nutation", lambda jd_tt: (0.2, 0.0))
    monkeypatch.setattr("moira.obliquity.true_obliquity", lambda jd_tt: 23.4)
    monkeypatch.setattr("moira.julian.apparent_sidereal_time", lambda jd_ut, dpsi, obliq: 111.0)

    def fake_planet_at(body: str, jd_ut: float, *, jd_tt: float):
        calls.setdefault("planet_at", []).append((body, jd_ut, jd_tt))
        if body == "Sun":
            return _FakePlanetData(longitude=0.0, latitude=0.0)
        return _FakePlanetData(longitude=90.0, latitude=45.0 - 23.4)

    def fake_subplanetary_points(
        planet_ra_dec: dict[str, tuple[float, float]],
        gmst_deg: float,
    ):
        calls["planet_ra_dec"] = planet_ra_dec
        calls["gmst_deg"] = gmst_deg
        return ["sentinel"]

    monkeypatch.setattr("moira.planets.planet_at", fake_planet_at)
    monkeypatch.setattr(acg, "subplanetary_points", fake_subplanetary_points)

    result = acg.subplanetary_from_chart(chart, bodies=["Sun", "Moon"])

    assert result == ["sentinel"]
    assert calls["planet_at"] == [
        ("Sun", chart.jd_ut, chart.jd_tt),
        ("Moon", chart.jd_ut, chart.jd_tt),
    ]
    assert calls["planet_ra_dec"]["Sun"] == pytest.approx((0.0, 0.0))
    assert calls["planet_ra_dec"]["Moon"][0] == pytest.approx(90.0)
    assert calls["gmst_deg"] == pytest.approx(111.0)


def test_subplanetary_from_chart_admits_small_body_through_planet_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chart = _FakeChart(
        jd_ut=2451545.0,
        latitude=0.0,
        longitude=0.0,
        planets={"Ceres": object()},
    )
    calls: list[tuple[str, float, float]] = []

    @dataclass
    class _FakePlanetData:
        longitude: float
        latitude: float

    monkeypatch.setattr("moira.julian.utc_to_ut1", lambda jd: jd + 0.01)
    monkeypatch.setattr("moira.julian.utc_to_tt", lambda jd: jd + 0.1)
    monkeypatch.setattr("moira.obliquity.nutation", lambda jd_tt: (0.0, 0.0))
    monkeypatch.setattr("moira.obliquity.true_obliquity", lambda jd_tt: 23.4392911)
    monkeypatch.setattr("moira.julian.apparent_sidereal_time", lambda jd_ut, dpsi, obliq: 0.0)

    def fake_planet_at(body: str, jd_ut: float, *, jd_tt: float):
        calls.append((body, jd_ut, jd_tt))
        return _FakePlanetData(longitude=15.0, latitude=2.0)

    monkeypatch.setattr("moira.planets.planet_at", fake_planet_at)

    points = acg.subplanetary_from_chart(chart, bodies=["Ceres"])

    assert calls == [("Ceres", chart.jd_ut, chart.jd_tt)]
    point_map = _points_by_type(points)
    assert ("Ceres", "Zenith") in point_map
    assert ("Ceres", "Nadir") in point_map

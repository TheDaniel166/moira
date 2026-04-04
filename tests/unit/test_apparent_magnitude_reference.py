from __future__ import annotations

import math

import pytest

import moira.phase as phase
from moira.constants import Body
from moira.julian import julian_day


class _ZeroSunReader:
    def position(self, center: int, target: int, jd: float):
        assert (center, target) == (0, 10)
        return (0.0, 0.0, 0.0)


def _install_sample_geometry(
    monkeypatch: pytest.MonkeyPatch,
    body_name: str,
    *,
    r_au: float,
    delta_au: float,
    beta_deg: float,
) -> None:
    r_km = r_au * phase.KM_PER_AU
    delta_km = delta_au * phase.KM_PER_AU
    beta_rad = math.radians(beta_deg)

    p_bary = (r_km, 0.0, 0.0)
    geocentric = (
        delta_km * math.cos(beta_rad),
        delta_km * math.sin(beta_rad),
        0.0,
    )
    e_bary = (
        p_bary[0] - geocentric[0],
        p_bary[1] - geocentric[1],
        0.0,
    )

    monkeypatch.setattr(phase, "get_reader", lambda: _ZeroSunReader())
    monkeypatch.setattr(phase, "_barycentric", lambda name, jd, reader: p_bary)
    monkeypatch.setattr(phase, "_earth_barycentric", lambda jd, reader: e_bary)


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _unit(a: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    return (a[0] / n, a[1] / n, a[2] / n)


def _install_saturn_ring_sample_geometry(
    monkeypatch: pytest.MonkeyPatch,
    *,
    jd_ut: float,
    r_au: float,
    delta_au: float,
    beta_deg: float,
    sub_lat_geoc_deg: float,
) -> None:
    pole = phase._saturn_pole_unit(jd_ut)
    ref = (0.0, 0.0, 1.0) if abs(pole[2]) < 0.9 else (0.0, 1.0, 0.0)
    ex = _unit(_cross(ref, pole))
    ey = _cross(pole, ex)

    beta_rad = math.radians(beta_deg)
    sub_lat_rad = math.radians(sub_lat_geoc_deg)
    sin_lat = math.sin(sub_lat_rad)
    cos_lat = math.cos(sub_lat_rad)
    cos_dlon = (math.cos(beta_rad) - sin_lat * sin_lat) / (cos_lat * cos_lat)
    cos_dlon = max(-1.0, min(1.0, cos_dlon))
    dlon = math.acos(cos_dlon)

    def _dir(lon_rad: float) -> tuple[float, float, float]:
        x = cos_lat * math.cos(lon_rad)
        y = cos_lat * math.sin(lon_rad)
        z = sin_lat
        return (
            ex[0] * x + ey[0] * y + pole[0] * z,
            ex[1] * x + ey[1] * y + pole[1] * z,
            ex[2] * x + ey[2] * y + pole[2] * z,
        )

    earth_dir = _dir(-0.5 * dlon)
    sun_dir = _dir(0.5 * dlon)
    p_bary = (0.0, 0.0, 0.0)
    s_bary = tuple(component * r_au * phase.KM_PER_AU for component in sun_dir)
    e_bary = tuple(component * delta_au * phase.KM_PER_AU for component in earth_dir)

    monkeypatch.setattr(phase, "get_reader", lambda: _ZeroSunReader())
    monkeypatch.setattr(phase, "_barycentric", lambda name, jd, reader: p_bary)
    monkeypatch.setattr(phase, "_earth_barycentric", lambda jd, reader: e_bary)
    monkeypatch.setattr(_ZeroSunReader, "position", lambda self, center, target, jd: s_bary)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("body_name", "jd_ut", "r_au", "delta_au", "beta_deg", "expected_mag"),
    [
        (Body.MERCURY, julian_day(2006, 5, 19), 0.310295423552, 1.32182643625754, 1.1677, -2.477),
        (Body.MERCURY, julian_day(2006, 6, 15), 0.413629222334, 0.92644808718613, 90.1662, 0.181),
        (Body.MERCURY, julian_day(2003, 5, 7), 0.448947624811, 0.56004973217883, 178.7284, 7.167),
        (Body.VENUS, julian_day(2006, 10, 28), 0.722722540169, 1.71607489554051, 1.3232, -3.917),
        (Body.VENUS, julian_day(2005, 12, 14), 0.721480714554, 0.37762511206278, 124.1348, -4.916),
        (Body.VENUS, julian_day(2004, 6, 8), 0.726166592736, 0.28889582420642, 179.1845, -3.090),
        (Body.JUPITER, julian_day(2004, 9, 21), 5.446231815414, 6.44985867459088, 0.2446, -1.667),
        (Body.JUPITER, julian_day(2010, 9, 21), 4.957681473205, 3.95393078136013, 0.3431, -2.934),
        (Body.NEPTUNE, julian_day(1970, 11, 23), 30.322109867761, 31.3091610098214, 0.0549, 7.997),
        (Body.NEPTUNE, julian_day(1990, 4, 27), 30.207767693725, 29.8172370857530, 1.7741, 7.827),
        (Body.NEPTUNE, julian_day(2009, 8, 17), 30.028181709541, 29.0158521665744, 0.0381, 7.701),
    ],
)
def test_apparent_magnitude_matches_published_samples(
    monkeypatch: pytest.MonkeyPatch,
    body_name: str,
    jd_ut: float,
    r_au: float,
    delta_au: float,
    beta_deg: float,
    expected_mag: float,
) -> None:
    _install_sample_geometry(
        monkeypatch,
        body_name,
        r_au=r_au,
        delta_au=delta_au,
        beta_deg=beta_deg,
    )

    mag = phase.apparent_magnitude(body_name, jd_ut)

    assert mag == pytest.approx(expected_mag, abs=1e-3)


@pytest.mark.unit
def test_apparent_magnitude_matches_published_saturn_ring_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jd_ut = julian_day(2032, 12, 25)
    _install_saturn_ring_sample_geometry(
        monkeypatch,
        jd_ut=jd_ut,
        r_au=9.014989659493,
        delta_au=8.03160470546889,
        beta_deg=0.1055,
        sub_lat_geoc_deg=26.279,
    )

    mag = phase.apparent_magnitude(Body.SATURN, jd_ut)

    assert mag == pytest.approx(-0.552, abs=1e-3)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("beta_deg", "sub_earth_long", "sub_sun_long", "h_ecl_long", "r_au", "delta_au", "expected_mag"),
    [
        (4.8948, 329.27, 330.76, 334.4996, 1.381191244505, 0.37274381097911, -2.862),
        (11.5877, 76.84, 64.66, 147.3485, 1.664150453905, 2.58995164518460, 1.788),
        (167.9000, 29.50, 221.11, 212.8886, 1.591952180003, 3.85882552272013, 8.977),
    ],
)
def test_mars_reference_formula_matches_published_samples(
    beta_deg: float,
    sub_earth_long: float,
    sub_sun_long: float,
    h_ecl_long: float,
    r_au: float,
    delta_au: float,
    expected_mag: float,
) -> None:
    eff_cm = (sub_earth_long + sub_sun_long) / 2.0
    if abs(sub_earth_long - sub_sun_long) > 180.0:
        eff_cm += 180.0
    if eff_cm > 360.0:
        eff_cm -= 360.0
    mars_ls = (h_ecl_long - 85.0) % 360.0

    mag = phase._mag_mars(
        r_au,
        delta_au,
        beta_deg,
        mars_eff_cm=eff_cm,
        mars_ls=mars_ls,
    )

    assert mag == pytest.approx(expected_mag, abs=1e-3)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("jd_ut", "expected_mag"),
    [
        (julian_day(2003, 8, 28), -2.862),
        (julian_day(2004, 7, 19), 1.788),
    ],
)
def test_mars_apparent_magnitude_matches_published_kernel_samples(
    jd_ut: float,
    expected_mag: float,
) -> None:
    mag = phase.apparent_magnitude(Body.MARS, jd_ut)

    assert mag == pytest.approx(expected_mag, abs=5e-3)


@pytest.mark.unit
def test_uranus_reference_formula_matches_published_large_phase_sample() -> None:
    sub_lat_planetog = (abs(-71.16) + abs(55.11)) / 2.0

    mag = phase._mag_uranus(
        19.38003071775,
        11.1884243801383,
        161.7728,
        uranus_sub_lat_planetog=sub_lat_planetog,
    )

    assert mag == pytest.approx(8.318, abs=1e-3)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("jd_ut", "r_au", "delta_au", "beta_deg", "expected_mag"),
    [
        (julian_day(2018, 2, 21), 29.94386311956, 0.00940968942251, 88.4363, -8.296),
        (julian_day(2018, 3, 6), 29.94363797622, 0.01582757185680, 176.9965, -4.203),
    ],
)
def test_neptune_reference_formula_matches_published_large_phase_samples(
    jd_ut: float,
    r_au: float,
    delta_au: float,
    beta_deg: float,
    expected_mag: float,
) -> None:
    mag = phase._mag_neptune(r_au, delta_au, beta_deg, jd_ut)

    assert mag == pytest.approx(expected_mag, abs=1e-3)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("body_name", "jd_ut", "r_au", "delta_au", "beta_deg", "expected_mag"),
    [
        (Body.URANUS, julian_day(1970, 3, 28), 18.321003215845, 17.3229728525108, 0.0410, 5.381),
        (Body.URANUS, julian_day(2008, 3, 8), 20.096361095266, 21.0888470145276, 0.0568, 6.025),
    ],
)
def test_apparent_magnitude_documented_fallbacks_are_stable(
    body_name: str,
    jd_ut: float,
    r_au: float,
    delta_au: float,
    beta_deg: float,
    expected_mag: float,
) -> None:
    mag = phase.apparent_magnitude(body_name, jd_ut)

    assert mag == pytest.approx(expected_mag, abs=1e-3)


@pytest.mark.unit
def test_moon_apparent_magnitude_matches_admitted_schaefer_formula(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delta_au = 384400.0 / phase.KM_PER_AU
    _install_sample_geometry(
        monkeypatch,
        Body.MOON,
        r_au=1.0,
        delta_au=delta_au,
        beta_deg=0.0,
    )

    mag = phase.apparent_magnitude(Body.MOON, julian_day(2000, 1, 1))

    assert mag == pytest.approx(-12.73, abs=1e-6)

from __future__ import annotations

import pytest

import moira.galactic as gal


JD_J2000 = 2451545.0
OBLIQUITY_J2000 = 23.4392911


class TestGalacticInputValidation:
    @pytest.mark.parametrize(
        ("ra", "dec", "message"),
        [
            (float("nan"), 0.0, "ra"),
            (0.0, float("nan"), "dec"),
            (0.0, 91.0, "dec"),
            (0.0, -91.0, "dec"),
        ],
    )
    def test_equatorial_to_galactic_rejects_invalid_inputs(
        self,
        ra: float,
        dec: float,
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            gal.equatorial_to_galactic(ra, dec)

    @pytest.mark.parametrize(
        ("longitude", "latitude", "message"),
        [
            (float("nan"), 0.0, "l"),
            (0.0, float("nan"), "b"),
            (0.0, 91.0, "b"),
            (0.0, -91.0, "b"),
        ],
    )
    def test_galactic_to_equatorial_rejects_invalid_inputs(
        self,
        longitude: float,
        latitude: float,
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            gal.galactic_to_equatorial(longitude, latitude)

    @pytest.mark.parametrize(
        ("longitude", "latitude", "obliquity", "jd_tt", "message"),
        [
            (float("nan"), 0.0, OBLIQUITY_J2000, JD_J2000, "lon"),
            (0.0, float("nan"), OBLIQUITY_J2000, JD_J2000, "lat"),
            (0.0, 91.0, OBLIQUITY_J2000, JD_J2000, "lat"),
            (0.0, 0.0, float("nan"), JD_J2000, "obliquity"),
            (0.0, 0.0, OBLIQUITY_J2000, float("nan"), "jd_tt"),
        ],
    )
    def test_ecliptic_to_galactic_rejects_invalid_inputs(
        self,
        longitude: float,
        latitude: float,
        obliquity: float,
        jd_tt: float,
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            gal.ecliptic_to_galactic(longitude, latitude, obliquity, jd_tt)

    @pytest.mark.parametrize(
        ("longitude", "latitude", "obliquity", "jd_tt", "message"),
        [
            (float("nan"), 0.0, OBLIQUITY_J2000, JD_J2000, "l"),
            (0.0, float("nan"), OBLIQUITY_J2000, JD_J2000, "b"),
            (0.0, 91.0, OBLIQUITY_J2000, JD_J2000, "b"),
            (0.0, 0.0, float("nan"), JD_J2000, "obliquity"),
            (0.0, 0.0, OBLIQUITY_J2000, float("nan"), "jd_tt"),
        ],
    )
    def test_galactic_to_ecliptic_rejects_invalid_inputs(
        self,
        longitude: float,
        latitude: float,
        obliquity: float,
        jd_tt: float,
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            gal.galactic_to_ecliptic(longitude, latitude, obliquity, jd_tt)

    def test_galactic_reference_points_rejects_non_finite_inputs(self) -> None:
        with pytest.raises(ValueError, match="obliquity"):
            gal.galactic_reference_points(float("nan"), JD_J2000)

        with pytest.raises(ValueError, match="jd_tt"):
            gal.galactic_reference_points(OBLIQUITY_J2000, float("nan"))

    def test_galactic_position_of_rejects_empty_body_name(self) -> None:
        with pytest.raises(ValueError, match="body"):
            gal.galactic_position_of("", 0.0, 0.0, OBLIQUITY_J2000, JD_J2000)

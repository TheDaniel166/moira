from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira.sidereal as sidereal
from moira.precession import general_precession_in_longitude
from moira.obliquity import nutation


def test_public_ayanamsa_path_ignores_private_star_anchor_helper(monkeypatch, jd_j2000) -> None:
    monkeypatch.setattr("moira.planets._approx_year", lambda jd: (2000, 1, 1))
    monkeypatch.setattr("moira.julian.ut_to_tt", lambda jd, year=None: jd + 0.1)
    monkeypatch.setattr(
        "moira.fixed_stars.fixed_star_at",
        lambda star_name, jd_tt: SimpleNamespace(longitude=205.25),
    )

    expected = (
        sidereal._AYANAMSA_AT_J2000[sidereal.Ayanamsa.TRUE_CHITRAPAKSHA]
        + general_precession_in_longitude(jd_j2000)
        + nutation(jd_j2000)[0]
    )
    result = sidereal.ayanamsa(jd_j2000, sidereal.Ayanamsa.TRUE_CHITRAPAKSHA, mode="true")

    assert result == pytest.approx(expected)


def test_private_star_anchor_helper_uses_live_star_position(monkeypatch) -> None:
    monkeypatch.setattr("moira.planets._approx_year", lambda jd: (2000, 1, 1))
    monkeypatch.setattr("moira.julian.ut_to_tt", lambda jd, year=None: jd + 0.1)
    monkeypatch.setattr(
        "moira.fixed_stars.fixed_star_at",
        lambda star_name, jd_tt: SimpleNamespace(longitude=205.25),
    )

    result = sidereal._star_anchored_ayanamsa(
        sidereal.Ayanamsa.TRUE_CHITRAPAKSHA,
        2451545.0,
    )

    assert result == pytest.approx(25.25)


def test_private_star_anchor_helper_fallback_keeps_true_mode_nutation(monkeypatch, jd_j2000) -> None:
    monkeypatch.setattr("moira.planets._approx_year", lambda jd: (2000, 1, 1))
    monkeypatch.setattr("moira.julian.ut_to_tt", lambda jd, year=None: jd)

    def _boom(*_args, **_kwargs):
        raise KeyError("Spica")

    monkeypatch.setattr("moira.fixed_stars.fixed_star_at", _boom)

    expected = (
        sidereal._AYANAMSA_AT_J2000[sidereal.Ayanamsa.TRUE_CHITRAPAKSHA]
        + general_precession_in_longitude(jd_j2000)
        + sidereal.nutation(jd_j2000)[0]
    )

    result = sidereal._star_anchored_ayanamsa(
        sidereal.Ayanamsa.TRUE_CHITRAPAKSHA,
        jd_j2000,
    )

    assert result == pytest.approx(expected)


def test_list_ayanamsa_systems_returns_copy() -> None:
    systems = sidereal.list_ayanamsa_systems()
    systems[sidereal.Ayanamsa.LAHIRI] = -999.0

    fresh = sidereal.list_ayanamsa_systems()
    assert fresh[sidereal.Ayanamsa.LAHIRI] != -999.0


def test_nakshatra_of_exact_boundaries_and_pada_clamp(monkeypatch, jd_j2000) -> None:
    monkeypatch.setattr(
        sidereal,
        "ayanamsa",
        lambda jd, system=sidereal.Ayanamsa.LAHIRI, mode="true": 0.0,
    )

    start = sidereal.nakshatra_of(0.0, jd_j2000)
    next_nak = sidereal.nakshatra_of(sidereal.NAKSHATRA_SPAN, jd_j2000)
    end_of_first = sidereal.nakshatra_of(
        sidereal.NAKSHATRA_SPAN - 1e-12,
        jd_j2000,
    )

    assert start.nakshatra == "Ashwini"
    assert start.nakshatra_index == 0
    assert start.pada == 1

    assert next_nak.nakshatra == "Bharani"
    assert next_nak.nakshatra_index == 1
    assert next_nak.pada == 1

    assert end_of_first.nakshatra == "Ashwini"
    assert end_of_first.nakshatra_index == 0
    assert end_of_first.pada == 4


def test_all_nakshatras_at_maps_each_body(monkeypatch, jd_j2000) -> None:
    monkeypatch.setattr(
        sidereal,
        "ayanamsa",
        lambda jd, system=sidereal.Ayanamsa.LAHIRI, mode="true": 0.0,
    )

    results = sidereal.all_nakshatras_at(
        {
            "Sun": 0.0,
            "Moon": sidereal.NAKSHATRA_SPAN,
        },
        jd_j2000,
    )

    assert set(results) == {"Sun", "Moon"}
    assert results["Sun"].nakshatra == "Ashwini"
    assert results["Moon"].nakshatra == "Bharani"


def test_galactic_5_sag_is_defined_as_galactic_0_sag_plus_five_degrees(jd_j2000) -> None:
    gal0_mean = sidereal.ayanamsa(jd_j2000, sidereal.Ayanamsa.GALACTIC_0_SAG, mode="mean")
    gal5_mean = sidereal.ayanamsa(jd_j2000, sidereal.Ayanamsa.GALACTIC_5_SAG, mode="mean")
    gal0_true = sidereal.ayanamsa(jd_j2000, sidereal.Ayanamsa.GALACTIC_0_SAG, mode="true")
    gal5_true = sidereal.ayanamsa(jd_j2000, sidereal.Ayanamsa.GALACTIC_5_SAG, mode="true")

    assert gal5_mean == pytest.approx((gal0_mean + 5.0) % 360.0)
    assert gal5_true == pytest.approx((gal0_true + 5.0) % 360.0)

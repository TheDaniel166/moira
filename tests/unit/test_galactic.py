from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import moira.galactic as gal
import moira_server.services.galactic as galactic_service
from moira_server.models.galactic import GalacticChartPositionsRequest


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


def test_galactic_chart_service_derives_tt_from_utc_coded_facade_chart(monkeypatch) -> None:
    requested_dt = datetime(2026, 7, 17, tzinfo=timezone.utc)
    jd_utc = 100.0
    jd_tt = 200.0
    chart = SimpleNamespace(
        jd_ut=jd_utc,
        datetime_utc=requested_dt,
        planets={"Sun": SimpleNamespace(longitude=10.0, latitude=2.0)},
    )
    calls: dict[str, object] = {"utc_to_tt": []}

    monkeypatch.setattr(galactic_service, "_build_chart", lambda _engine, _request: chart)

    def fake_utc_to_tt(jd: float) -> float:
        calls["utc_to_tt"].append(jd)
        return jd_tt

    def fake_all_galactic_positions(body_data, obliquity, received_jd_tt):
        calls["galactic"] = (body_data, obliquity, received_jd_tt)
        return [SimpleNamespace(body="Sun")]

    monkeypatch.setattr(galactic_service, "utc_to_tt", fake_utc_to_tt)
    monkeypatch.setattr(galactic_service, "true_obliquity", lambda received_jd_tt: 23.5)
    monkeypatch.setattr(galactic_service, "all_galactic_positions", fake_all_galactic_positions)

    result = galactic_service.compute_galactic_chart_positions(
        SimpleNamespace(),
        GalacticChartPositionsRequest(dt=requested_dt, bodies=["Sun"]),
    )

    assert calls["utc_to_tt"] == [jd_utc]
    assert calls["galactic"] == ({"Sun": (10.0, 2.0)}, 23.5, jd_tt)
    assert result.provenance.jd_ut == jd_utc
    assert result.provenance.jd_tt == jd_tt

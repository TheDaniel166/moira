from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import moira_server.services.gauquelin as gauquelin_service
from moira.gauquelin import (
    GauquelinHorizonStatus,
    all_gauquelin_sectors,
    gauquelin_sector,
)
from moira_server.models.gauquelin import GauquelinChartSectorsRequest


def test_canonical_result_preserves_plus_zone_metadata() -> None:
    position = gauquelin_sector(
        body_ra=0.0,
        body_dec=0.0,
        lat=0.0,
        lst=299.0,
        horizon_altitude=0.0,
        body="Mars",
    )

    assert position.body == "Mars"
    assert position.sector == 3
    assert position.zone == "Plus Zone"
    assert position.is_plus_zone
    assert position.degree_in_sector == pytest.approx(9.0)
    assert position.horizon_status is GauquelinHorizonStatus.NORMAL


def test_custom_sector_resolution_is_engine_supported_but_unzoned() -> None:
    position = gauquelin_sector(100.0, 15.0, 48.0, 90.0, sectors=72)

    assert 1 <= position.sector <= 72
    assert position.sectors == 72
    assert position.zone is None
    assert not position.is_plus_zone


def test_circumpolar_and_never_rises_statuses_are_explicit() -> None:
    circumpolar = gauquelin_sector(0.0, 85.0, 80.0, 0.0)
    never_rises = gauquelin_sector(0.0, -85.0, 80.0, 0.0)

    assert circumpolar.horizon_status is GauquelinHorizonStatus.CIRCUMPOLAR
    assert never_rises.horizon_status is GauquelinHorizonStatus.NEVER_RISES
    for position in (circumpolar, never_rises):
        assert position.sector is None
        assert position.zone is None
        assert position.diurnal_position is None
        assert position.degree_in_sector is None
        assert not position.is_plus_zone


def test_exact_pole_classification_respects_horizon_altitude() -> None:
    above_custom_horizon = gauquelin_sector(
        0.0, -0.2, 90.0, 0.0, horizon_altitude=-0.5667
    )
    below_custom_horizon = gauquelin_sector(
        0.0, 0.0, 90.0, 0.0, horizon_altitude=1.0
    )
    coincident = gauquelin_sector(
        0.0, 0.0, 90.0, 0.0, horizon_altitude=0.0
    )

    assert above_custom_horizon.horizon_status is GauquelinHorizonStatus.CIRCUMPOLAR
    assert below_custom_horizon.horizon_status is GauquelinHorizonStatus.NEVER_RISES
    assert coincident.horizon_status is GauquelinHorizonStatus.HORIZON_COINCIDENT
    assert coincident.sector is None


def test_near_pole_with_real_crossings_is_not_collapsed_to_exact_pole() -> None:
    position = gauquelin_sector(
        0.0,
        0.0,
        89.9999999999,
        0.0,
        horizon_altitude=0.0,
    )

    assert position.horizon_status is GauquelinHorizonStatus.NORMAL
    assert position.sector is not None


def test_default_horizon_is_geometric() -> None:
    kwargs = dict(body_ra=100.0, body_dec=20.0, lat=50.0, lst=80.0)
    assert gauquelin_sector(**kwargs) == gauquelin_sector(
        **kwargs, horizon_altitude=0.0
    )


@pytest.mark.parametrize(
    ("lst", "expected_sector"),
    [(270.0, 1), (280.0, 2), (0.0, 10), (10.0, 11)],
)
def test_exact_sector_boundaries_belong_to_following_sector(
    lst: float,
    expected_sector: int,
) -> None:
    position = gauquelin_sector(
        body_ra=0.0,
        body_dec=0.0,
        lat=0.0,
        lst=lst,
        horizon_altitude=0.0,
    )

    assert position.sector == expected_sector
    assert position.degree_in_sector == pytest.approx(0.0, abs=1.0e-12)


def test_result_vessel_is_immutable() -> None:
    position = gauquelin_sector(0.0, 0.0, 0.0, 0.0)

    with pytest.raises(FrozenInstanceError):
        position.sector = 7  # type: ignore[misc]


def test_batch_preserves_input_order_and_body_names() -> None:
    positions = all_gauquelin_sectors(
        {"Sun": (100.0, 10.0), "Mars": (220.0, -5.0)},
        lat=40.0,
        lst=100.0,
    )

    assert [position.body for position in positions] == ["Sun", "Mars"]
    assert all(1 <= position.sector <= 36 for position in positions)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"body_ra": float("nan")}, "body_ra must be finite"),
        ({"body_dec": float("inf")}, "body_dec must be finite"),
        ({"body_dec": 91.0}, r"body_dec must be in \[-90, 90\]"),
        ({"lat": float("nan")}, "lat must be finite"),
        ({"lat": -91.0}, r"lat must be in \[-90, 90\]"),
        ({"lst": float("inf")}, "lst must be finite"),
        ({"horizon_altitude": float("nan")}, "horizon_altitude must be finite"),
        ({"horizon_altitude": -90.0001}, r"horizon_altitude must be in \[-90, 90\]"),
        ({"horizon_altitude": 90.0001}, r"horizon_altitude must be in \[-90, 90\]"),
        ({"sectors": 0}, "sectors must be a positive integer"),
        ({"sectors": 36.0}, "sectors must be a positive integer"),
        ({"sectors": True}, "sectors must be a positive integer"),
    ],
)
def test_invalid_inputs_are_rejected(kwargs: dict[str, float], message: str) -> None:
    params = {
        "body_ra": 0.0,
        "body_dec": 0.0,
        "lat": 0.0,
        "lst": 0.0,
        "horizon_altitude": 0.0,
        "sectors": 36,
    }
    params.update(kwargs)

    with pytest.raises(ValueError, match=message):
        gauquelin_sector(**params)


def test_gauquelin_chart_service_resolves_utc_tt_and_ut1_for_dependencies(monkeypatch) -> None:
    requested_dt = datetime(2026, 7, 17, tzinfo=timezone.utc)
    jd_utc = 100.0
    jd_tt = 200.0
    jd_ut1 = 99.0
    chart = SimpleNamespace(
        jd_ut=jd_utc,
        datetime_utc=requested_dt,
        planets={"Sun": object()},
    )
    calls: dict[str, object] = {"utc_to_tt": [], "utc_to_ut1": [], "sky": []}

    monkeypatch.setattr(gauquelin_service, "_build_chart", lambda _engine, _request: chart)
    monkeypatch.setattr(
        gauquelin_service,
        "utc_to_tt",
        lambda jd: calls["utc_to_tt"].append(jd) or jd_tt,
    )
    monkeypatch.setattr(
        gauquelin_service,
        "utc_to_ut1",
        lambda jd: calls["utc_to_ut1"].append(jd) or jd_ut1,
    )
    monkeypatch.setattr(gauquelin_service, "nutation", lambda received_jd_tt: (0.2, 0.0))
    monkeypatch.setattr(gauquelin_service, "true_obliquity", lambda received_jd_tt: 23.5)

    def fake_local_sidereal_time(received_jd_ut1, longitude, dpsi, obliquity):
        calls["sidereal"] = (received_jd_ut1, longitude, dpsi, obliquity)
        return 123.0

    def fake_sky_position_at(body, received_jd_ut1, **kwargs):
        calls["sky"].append((body, received_jd_ut1, kwargs))
        return SimpleNamespace(right_ascension=10.0, declination=2.0)

    monkeypatch.setattr(gauquelin_service, "local_sidereal_time", fake_local_sidereal_time)
    monkeypatch.setattr(gauquelin_service, "sky_position_at", fake_sky_position_at)
    monkeypatch.setattr(
        gauquelin_service,
        "gauquelin_sector",
        lambda *_args, body, **_kwargs: SimpleNamespace(body=body),
    )

    result = gauquelin_service.compute_gauquelin_chart_sectors(
        SimpleNamespace(_reader="reader"),
        GauquelinChartSectorsRequest(
            dt=requested_dt,
            latitude=40.0,
            longitude=-74.0,
            bodies=["Sun"],
        ),
    )

    assert calls["utc_to_tt"] == [jd_utc]
    assert calls["utc_to_ut1"] == [jd_utc]
    assert calls["sidereal"] == (jd_ut1, -74.0, 0.2, 23.5)
    assert calls["sky"] == [
        (
            "Sun",
            jd_ut1,
            {
                "observer_lat": 40.0,
                "observer_lon": -74.0,
                "observer_elev_m": 0.0,
                "reader": "reader",
            },
        )
    ]
    assert result.provenance.jd_ut == jd_ut1
    assert result.provenance.jd_tt == jd_tt

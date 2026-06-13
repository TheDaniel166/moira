from __future__ import annotations

import math

import pytest

from moira.gauquelin import (
    GauquelinHorizonStatus,
    all_gauquelin_sectors,
    gauquelin_sector,
)


def test_canonical_result_preserves_plus_zone_metadata() -> None:
    position = gauquelin_sector(
        body_ra=0.0,
        body_dec=0.0,
        lat=0.0,
        lst=300.0,
        horizon_altitude=0.0,
        body="Mars",
    )

    assert position.body == "Mars"
    assert position.sector == 3
    assert position.zone == "Plus Zone"
    assert position.is_plus_zone
    assert position.degree_in_sector == pytest.approx(10.0)
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
    assert 1 <= circumpolar.sector <= 36
    assert 1 <= never_rises.sector <= 36
    assert math.isfinite(circumpolar.diurnal_position)
    assert math.isfinite(never_rises.diurnal_position)


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
        "horizon_altitude": -0.5667,
        "sectors": 36,
    }
    params.update(kwargs)

    with pytest.raises(ValueError, match=message):
        gauquelin_sector(**params)

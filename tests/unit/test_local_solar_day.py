from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import moira._local_solar_day as local_solar_day


def _identity_refinement(
    jd_guess: float,
    latitude: float,
    longitude: float,
    reader: object,
    is_rise: bool,
) -> float:
    del latitude, longitude, reader, is_rise
    return jd_guess


@pytest.mark.parametrize(
    ("jd", "expected_sunrise", "expected_sunset", "expected_next_sunrise"),
    [
        (2451545.10, 2451544.20, 2451544.70, 2451545.20),
        (2451545.50, 2451545.20, 2451545.70, 2451546.20),
    ],
)
def test_resolver_selects_the_enclosing_sunrise_window(
    monkeypatch: pytest.MonkeyPatch,
    jd: float,
    expected_sunrise: float,
    expected_sunset: float,
    expected_next_sunrise: float,
) -> None:
    events_by_noon = {
        2451545.0: (2451544.20, 2451544.70),
        2451546.0: (2451545.20, 2451545.70),
        2451547.0: (2451546.20, 2451546.70),
    }
    monkeypatch.setattr(
        local_solar_day,
        "_sunrise_sunset",
        lambda noon, latitude, longitude, reader: events_by_noon[noon],
    )
    monkeypatch.setattr(local_solar_day, "_refine_sunrise", _identity_refinement)

    result = local_solar_day._local_solar_day_from_ut1(
        jd,
        12.5,
        77.5,
        reader=object(),
    )

    assert result.sunrise_jd == pytest.approx(expected_sunrise)
    assert result.sunset_jd == pytest.approx(expected_sunset)
    assert result.next_sunrise_jd == pytest.approx(expected_next_sunrise)
    assert result.sunrise_jd <= result.jd < result.next_sunrise_jd
    assert result.is_daytime is (result.jd < result.sunset_jd)


def test_local_solar_day_is_immutable_and_weekday_is_longitude_aware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        local_solar_day,
        "_sunrise_sunset",
        lambda noon, latitude, longitude, reader: (noon - 0.72, noon - 0.22),
    )
    monkeypatch.setattr(local_solar_day, "_refine_sunrise", _identity_refinement)

    result = local_solar_day._local_solar_day_from_ut1(
        2460310.5416666665,
        -33.8688,
        151.2093,
        reader=object(),
    )

    assert result.weekday == local_solar_day._local_weekday_at_sunrise(
        result.sunrise_jd,
        result.longitude,
    )
    with pytest.raises(FrozenInstanceError):
        result.sunrise_jd = 0.0  # type: ignore[misc]


def test_utc_adapter_selects_civil_noons_before_ut1_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    noon_calls: list[float] = []

    def fake_sunrise_sunset(
        noon: float,
        latitude: float,
        longitude: float,
        reader: object,
    ) -> tuple[float, float]:
        del latitude, longitude, reader
        noon_calls.append(noon)
        return noon - 0.25, noon + 0.25

    monkeypatch.setattr(local_solar_day, "_sunrise_sunset", fake_sunrise_sunset)
    monkeypatch.setattr(local_solar_day, "_refine_sunrise", _identity_refinement)
    monkeypatch.setattr(local_solar_day, "utc_to_ut1", lambda jd: jd + 0.6)

    result = local_solar_day._local_solar_day_from_utc(
        2451545.49,
        0.0,
        0.0,
        reader=object(),
    )

    assert result.jd == pytest.approx(2451546.09)
    assert noon_calls == pytest.approx([2451545.6, 2451546.6])


def test_resolver_preserves_consumer_specific_bounds_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        local_solar_day,
        "_sunrise_sunset",
        lambda noon, latitude, longitude, reader: (noon - 0.25, noon - 0.25),
    )
    monkeypatch.setattr(local_solar_day, "_refine_sunrise", _identity_refinement)

    with pytest.raises(
        ValueError,
        match="planetary-hours solar bounds must satisfy sunrise < sunset < next sunrise",
    ):
        local_solar_day._resolve_local_solar_day(
            2451545.0,
            0.0,
            0.0,
            object(),  # type: ignore[arg-type]
            previous_noon_ut1=2451544.0,
            current_noon_ut1=2451545.0,
            next_noon_ut1=2451546.0,
            bounds_owner="planetary-hours",
        )


@pytest.mark.parametrize(
    ("jd", "latitude", "longitude", "exception", "message"),
    [
        (True, 0.0, 0.0, TypeError, "jd must be a real number"),
        (float("inf"), 0.0, 0.0, ValueError, "jd must be finite"),
        (2451545.0, -90.1, 0.0, ValueError, "latitude must be within"),
        (2451545.0, 0.0, 180.1, ValueError, "longitude must be within"),
    ],
)
def test_shared_input_contract_rejects_invalid_values(
    jd: float,
    latitude: float,
    longitude: float,
    exception: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception, match=message):
        local_solar_day._local_solar_day_from_ut1(
            jd,
            latitude,
            longitude,
            reader=object(),
        )


@pytest.mark.parametrize("refined", [float("nan"), float("inf")])
def test_refinement_rejects_non_finite_events(
    monkeypatch: pytest.MonkeyPatch,
    refined: float,
) -> None:
    monkeypatch.setattr(
        local_solar_day,
        "_refine_sunrise",
        lambda *args, **kwargs: refined,
    )

    with pytest.raises(ValueError, match="solar event refinement returned a non-finite JD"):
        local_solar_day._refine_solar_event_near(
            2451545.0,
            0.0,
            0.0,
            object(),  # type: ignore[arg-type]
            is_rise=True,
        )

"""Stage 2A Pancha Pakshi local-solar context contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path

import pytest

import moira._local_solar_day as local_solar_day
import moira._pancha_pakshi as internal
import moira.facade as facade
import moira.pancha_pakshi as pancha_pakshi
from moira._local_solar_day import LocalSolarDay
from moira.pancha_pakshi import (
    PanchaPakshiAdmissionStatus,
    PanchaPakshiCapability,
    PanchaPakshiDataError,
    PanchaPakshiHalf,
    PanchaPakshiLocalSolarContextPolicy,
    PanchaPakshiPaksha,
    PanchaPakshiWeekday,
    pancha_pakshi_local_solar_context_at,
    pancha_pakshi_schedule,
)


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_JD = 2_460_000.25
_SUNRISE = 2_460_000.0
_SUNSET = 2_460_000.5
_NEXT_SUNRISE = 2_460_001.0
_HORIZONS_RISE_SET_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "horizons_rise_set_reference.json"
)


def _solar_day(*, jd: float = _JD, weekday: object = 3) -> LocalSolarDay:
    return LocalSolarDay(
        jd=jd,
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd=_SUNRISE,
        sunset_jd=_SUNSET,
        next_sunrise_jd=_NEXT_SUNRISE,
        weekday=weekday,  # type: ignore[arg-type]
    )


def test_local_solar_context_derives_only_half_and_weekday_and_forwards_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = object()
    calls: list[tuple[object, ...]] = []

    def resolve(jd, latitude, longitude, supplied_reader, *, bounds_owner):
        calls.append(
            (jd, latitude, longitude, supplied_reader, bounds_owner)
        )
        return _solar_day()

    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        resolve,
    )

    context = pancha_pakshi_local_solar_context_at(
        _PROFILE_ID,
        _JD,
        13.0827,
        80.2707,
        paksha=PanchaPakshiPaksha.PURVA,
        reader=reader,  # type: ignore[arg-type]
    )

    assert calls == [
        (
            _JD,
            13.0827,
            80.2707,
            reader,
            "pancha-pakshi-local-solar-context",
        )
    ]
    assert context.profile_id == _PROFILE_ID
    assert context.requested_jd_ut1 == _JD
    assert context.latitude == 13.0827
    assert context.longitude == 80.2707
    assert context.sunrise_jd_ut1 == _SUNRISE
    assert context.sunset_jd_ut1 == _SUNSET
    assert context.next_sunrise_jd_ut1 == _NEXT_SUNRISE
    assert context.paksha is PanchaPakshiPaksha.PURVA
    assert context.half is PanchaPakshiHalf.DAY
    assert context.weekday is PanchaPakshiWeekday.WEDNESDAY
    assert context.nominal_schedule == pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.WEDNESDAY,
    )
    assert context.nominal_schedule.provenance.astronomical_routing_status == (
        "not_performed"
    )
    assert context.provenance.astronomical_routing_status == (
        "local_solar_half_and_weekday_performed_paksha_caller_supplied"
    )
    assert context.policy == PanchaPakshiLocalSolarContextPolicy()
    assert context.policy.offset_materialization_status == "not_performed"
    assert not hasattr(context, "current_cell")


def test_exact_sunset_belongs_to_night_and_preserves_caller_paksha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: _solar_day(jd=_SUNSET, weekday=0),
    )

    context = pancha_pakshi_local_solar_context_at(
        _PROFILE_ID,
        _SUNSET,
        13.0827,
        80.2707,
        paksha=PanchaPakshiPaksha.AMARA,
        reader=object(),  # type: ignore[arg-type]
    )

    assert context.paksha is PanchaPakshiPaksha.AMARA
    assert context.half is PanchaPakshiHalf.NIGHT
    assert context.weekday is PanchaPakshiWeekday.SUNDAY
    assert context.nominal_schedule.paksha is PanchaPakshiPaksha.AMARA
    assert context.nominal_schedule.half is PanchaPakshiHalf.NIGHT
    assert context.nominal_schedule.weekday is PanchaPakshiWeekday.SUNDAY


def test_configured_kernel_context_preserves_the_bounded_nominal_contract() -> None:
    from moira._kernel_paths import find_planetary_kernel
    from moira.spk_reader import SpkReader

    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        pytest.skip("no planetary kernel found")

    with SpkReader(kernel_path) as reader:
        context = pancha_pakshi_local_solar_context_at(
            _PROFILE_ID,
            2_461_242.0,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )

    assert (
        context.sunrise_jd_ut1
        <= context.requested_jd_ut1
        < context.next_sunrise_jd_ut1
    )
    assert (
        context.sunrise_jd_ut1
        < context.sunset_jd_ut1
        < context.next_sunrise_jd_ut1
    )
    assert context.half is (
        PanchaPakshiHalf.DAY
        if context.requested_jd_ut1 < context.sunset_jd_ut1
        else PanchaPakshiHalf.NIGHT
    )
    assert context.nominal_schedule == pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=context.paksha,
        half=context.half,
        weekday=context.weekday,
    )


@pytest.mark.requires_ephemeris
def test_context_solar_boundaries_match_offline_horizons_authority() -> None:
    """Validate only the astronomical boundary, not Pancha Pakshi doctrine."""

    from moira._kernel_paths import find_planetary_kernel
    from moira.spk_reader import SpkReader

    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        pytest.skip("no planetary kernel found")
    fixture = json.loads(
        _HORIZONS_RISE_SET_FIXTURE.read_text(encoding="utf-8")
    )
    case = next(
        item for item in fixture["cases"] if item["id"] == "sun-new-york-equinox"
    )
    expected = case["expected_events"]
    location = case["location"]
    threshold_seconds = float(case["threshold_seconds"])
    assert case["body"] == "Sun"
    assert case["source"]["oracle"] == "JPL Horizons"
    assert float(case["altitude_deg"]) == -0.8333

    with SpkReader(kernel_path) as reader:
        context = pancha_pakshi_local_solar_context_at(
            _PROFILE_ID,
            2_460_390.0,
            float(location["latitude_deg"]),
            float(location["longitude_deg"]),
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )

    sunrise_error_seconds = abs(
        context.sunrise_jd_ut1 - float(expected["Rise"])
    ) * 86_400.0
    sunset_error_seconds = abs(
        context.sunset_jd_ut1 - float(expected["Set"])
    ) * 86_400.0
    assert sunrise_error_seconds <= threshold_seconds
    assert sunset_error_seconds <= threshold_seconds


@pytest.mark.parametrize("weekday", [-1, True, 7])
def test_invalid_local_solar_weekday_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    weekday: object,
) -> None:
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: _solar_day(weekday=weekday),
    )

    with pytest.raises(
        PanchaPakshiDataError,
        match="invalid Sunday-zero weekday",
    ):
        pancha_pakshi_local_solar_context_at(
            _PROFILE_ID,
            _JD,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=object(),  # type: ignore[arg-type]
        )


def test_context_gate_rejects_unadmitted_capability_before_solar_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    without_context = replace(
        profile,
        capabilities=tuple(
            capability
            for capability in profile.capabilities
            if capability is not PanchaPakshiCapability.ASTRONOMICAL_CONTEXT
        ),
    )
    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: without_context,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: pytest.fail(
            "solar resolution must not run before the capability gate"
        ),
    )

    with pytest.raises(ValueError, match="does not admit 'astronomical_context'"):
        pancha_pakshi_local_solar_context_at(
            _PROFILE_ID,
            _JD,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=object(),  # type: ignore[arg-type]
        )


def test_context_gate_rejects_research_profile_before_solar_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    research_only = replace(
        profile,
        admission_status=PanchaPakshiAdmissionStatus.RESEARCH_ONLY,
    )
    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: research_only,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: pytest.fail(
            "solar resolution must not run before the admission gate"
        ),
    )

    with pytest.raises(ValueError, match="is not publicly admitted"):
        pancha_pakshi_local_solar_context_at(
            _PROFILE_ID,
            _JD,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=object(),  # type: ignore[arg-type]
        )


def test_context_requires_an_explicit_paksha_enum_before_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: pytest.fail(
            "solar resolution must not infer or coerce Paksha"
        ),
    )

    with pytest.raises(TypeError, match="astronomical paksha inference is not admitted"):
        pancha_pakshi_local_solar_context_at(
            _PROFILE_ID,
            _JD,
            13.0827,
            80.2707,
            paksha="purva",  # type: ignore[arg-type]
            reader=object(),  # type: ignore[arg-type]
        )


def test_local_solar_policy_is_fixed_and_immutable() -> None:
    policy = PanchaPakshiLocalSolarContextPolicy()
    assert policy.policy_id == "local_solar_day_explicit_paksha_v1"
    assert policy.paksha_basis == "caller_supplied_source_label"
    assert policy.solar_day_basis == "topocentric_sunrise_to_next_sunrise"
    assert policy.solar_event_altitude_deg == -0.833
    assert policy.observer_elevation_m == 0.0
    assert policy.solar_altitude_refraction_mode == (
        "unrefracted_signal_standard_refraction_and_semidiameter_in_threshold"
    )
    assert policy.half_basis == "topocentric_sunrise_sunset"
    assert policy.weekday_basis == (
        "local_mean_solar_time_at_governing_sunrise"
    )

    with pytest.raises(TypeError):
        PanchaPakshiLocalSolarContextPolicy(policy_id="ambient")  # type: ignore[call-arg]
    with pytest.raises(FrozenInstanceError):
        policy.policy_id = "ambient"  # type: ignore[misc]


def test_facade_uses_aware_utc_adapter_and_forwards_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    reader = object()
    engine._reader_obj = reader
    expected = object()
    calls: list[tuple[object, ...]] = []
    dt = datetime(2026, 7, 20, 15, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(facade, "jd_from_datetime", lambda value: 2_461_000.75)

    def context_from_utc(
        profile_id,
        jd_utc,
        latitude,
        longitude,
        *,
        paksha,
        reader,
    ):
        calls.append(
            (profile_id, jd_utc, latitude, longitude, paksha, reader)
        )
        return expected

    monkeypatch.setattr(
        pancha_pakshi,
        "_pancha_pakshi_local_solar_context_from_utc",
        context_from_utc,
    )

    assert engine.pancha_pakshi_local_solar_context(
        _PROFILE_ID,
        dt,
        13.0827,
        80.2707,
        paksha=PanchaPakshiPaksha.PURVA,
    ) is expected
    assert calls == [
        (
            _PROFILE_ID,
            2_461_000.75,
            13.0827,
            80.2707,
            PanchaPakshiPaksha.PURVA,
            reader,
        )
    ]

    parameters = inspect.signature(
        facade.Moira.pancha_pakshi_local_solar_context
    ).parameters
    assert parameters["profile_id"].default is inspect.Parameter.empty
    assert parameters["paksha"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["paksha"].default is inspect.Parameter.empty


def test_facade_rejects_naive_datetime_before_context_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = object()
    monkeypatch.setattr(
        pancha_pakshi,
        "_pancha_pakshi_local_solar_context_from_utc",
        lambda *args, **kwargs: pytest.fail(
            "naive datetime must fail before context routing"
        ),
    )

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        engine.pancha_pakshi_local_solar_context(
            _PROFILE_ID,
            datetime(2026, 7, 20, 15, 30),
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
        )

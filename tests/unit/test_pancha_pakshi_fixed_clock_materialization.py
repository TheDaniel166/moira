"""Bounded Phase 2B Pancha Pakshi fixed-clock materialization contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
from fractions import Fraction
import inspect

import pytest

import moira._ephemeris_time as ephemeris_time
import moira._local_solar_day as local_solar_day
import moira._pancha_pakshi as internal
import moira.facade as facade
import moira.pancha_pakshi as pancha_pakshi
from moira._local_solar_day import LocalSolarDay
from moira.pancha_pakshi import (
    PanchaPakshiActivity,
    PanchaPakshiAdmissionStatus,
    PanchaPakshiCapability,
    PanchaPakshiFixedClockMaterializationPolicy,
    PanchaPakshiHalf,
    PanchaPakshiMaterializedCellRelation,
    PanchaPakshiPaksha,
    PanchaPakshiSolarBoundaryRelation,
    pancha_pakshi_fixed_clock_materialization_at,
)


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_SUNRISE = 2_460_000.0
_TT_MINUS_UT1_SECONDS = 100.0


def _bind_linear_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    def to_tt(jd_ut1, reader):
        assert reader is _READER
        return jd_ut1 + _TT_MINUS_UT1_SECONDS / 86_400.0

    def to_ut1(jd_tt, reader):
        assert reader is _READER
        return jd_tt - _TT_MINUS_UT1_SECONDS / 86_400.0

    monkeypatch.setattr(ephemeris_time, "_ut1_to_ephemeris_tt", to_tt)
    monkeypatch.setattr(ephemeris_time, "_ephemeris_tt_to_ut1", to_ut1)


_READER = object()


def _resolved_solar_day(
    *,
    half: PanchaPakshiHalf,
    solar_half_hours: float,
) -> LocalSolarDay:
    if half is PanchaPakshiHalf.DAY:
        sunrise = _SUNRISE
        sunset = sunrise + solar_half_hours / 24.0
        next_sunrise = sunset + 13.0 / 24.0
        requested = sunrise + 0.1
    else:
        sunrise = _SUNRISE
        sunset = sunrise + 11.0 / 24.0
        next_sunrise = sunset + solar_half_hours / 24.0
        requested = sunset + 0.1
    return LocalSolarDay(
        jd=requested,
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd=sunrise,
        sunset_jd=sunset,
        next_sunrise_jd=next_sunrise,
        weekday=3,
    )


def _materialize(
    monkeypatch: pytest.MonkeyPatch,
    *,
    half: PanchaPakshiHalf = PanchaPakshiHalf.DAY,
    solar_half_hours: float = 11.0,
    paksha: PanchaPakshiPaksha = PanchaPakshiPaksha.PURVA,
):
    _bind_linear_clock(monkeypatch)
    solar_day = _resolved_solar_day(
        half=half,
        solar_half_hours=solar_half_hours,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: solar_day,
    )
    return pancha_pakshi_fixed_clock_materialization_at(
        _PROFILE_ID,
        solar_day.jd,
        solar_day.latitude,
        solar_day.longitude,
        paksha=paksha,
        reader=_READER,  # type: ignore[arg-type]
    )


def test_fixed_clock_policy_is_exact_exhaustive_and_immutable() -> None:
    policy = PanchaPakshiFixedClockMaterializationPolicy()
    assert tuple(item.name for item in fields(policy)) == (
        "policy_id",
        "paksha_basis",
        "solar_context_basis",
        "day_anchor",
        "night_anchor",
        "nazhigai_seconds",
        "half_span_nazhigai",
        "half_span_seconds",
        "offset_arithmetic_time_scale",
        "published_endpoint_time_scale",
        "interval_ownership",
        "solar_end_clipping",
        "topology_metric",
        "topology_coalescence_seconds",
        "current_cell_status",
        "solar_proportional_scaling_status",
    )
    assert policy.policy_id == (
        "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
    )
    assert policy.paksha_basis == "caller_supplied_source_label"
    assert policy.solar_context_basis == "topocentric_sunrise_to_next_sunrise"
    assert policy.day_anchor == "governing_topocentric_sunrise"
    assert policy.night_anchor == "governing_topocentric_sunset"
    assert policy.nazhigai_seconds == 1440
    assert policy.half_span_nazhigai == 30
    assert policy.half_span_seconds == 43_200
    assert policy.offset_arithmetic_time_scale == "reader_bound_tt"
    assert policy.published_endpoint_time_scale == "ut1"
    assert policy.interval_ownership == "half_open"
    assert policy.solar_end_clipping == "none"
    assert policy.topology_metric == (
        "fixed_end_jd_tt_minus_solar_end_jd_tt"
    )
    assert policy.topology_coalescence_seconds == 0.0001
    assert policy.current_cell_status == "not_performed"
    assert policy.solar_proportional_scaling_status == "not_performed"

    with pytest.raises(TypeError):
        PanchaPakshiFixedClockMaterializationPolicy(  # type: ignore[call-arg]
            nazhigai_seconds=1
        )
    with pytest.raises(FrozenInstanceError):
        policy.nazhigai_seconds = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    ("activity", "expected_seconds"),
    [
        (PanchaPakshiActivity.EAT, Fraction(1800)),
        (PanchaPakshiActivity.WALK, Fraction(2160)),
        (PanchaPakshiActivity.RULE, Fraction(2880)),
        (PanchaPakshiActivity.SLEEP, Fraction(1080)),
        (PanchaPakshiActivity.DIE, Fraction(720)),
    ],
)
def test_fixed_clock_uses_exact_source_offsets_and_durations(
    monkeypatch: pytest.MonkeyPatch,
    activity: PanchaPakshiActivity,
    expected_seconds: Fraction,
) -> None:
    result = _materialize(monkeypatch)
    matching = [
        cell.duration_seconds
        for cell in result.cells
        if cell.nominal_cell.activity is activity
    ]
    assert matching == [expected_seconds] * 5

    assert len(result.cells) == 25
    assert tuple(cell.schedule_cell_index for cell in result.cells) == tuple(
        range(25)
    )
    assert result.cells[0].start_jd_tt == result.anchor_jd_tt
    assert result.cells[0].start_jd_ut1 == result.anchor_jd_ut1
    assert result.cells[-1].end_jd_tt == result.fixed_end_jd_tt
    assert result.cells[-1].end_jd_ut1 == result.fixed_end_jd_ut1
    assert result.fixed_end_jd_tt - result.anchor_jd_tt == 0.5
    assert sum((cell.duration_seconds for cell in result.cells), Fraction()) == (
        Fraction(43_200)
    )
    for nominal, materialized in zip(
        result.context.nominal_schedule.cells,
        result.cells,
        strict=True,
    ):
        assert materialized.nominal_cell is nominal
    for left, right in zip(result.cells, result.cells[1:]):
        assert left.end_jd_tt == right.start_jd_tt
        assert left.end_jd_ut1 == right.start_jd_ut1
    assert not hasattr(result, "current_cell")


@pytest.mark.parametrize(
    ("half", "solar_half_hours", "expected_relation", "expected_seconds"),
    [
        (
            PanchaPakshiHalf.DAY,
            11.0,
            PanchaPakshiSolarBoundaryRelation.ENDS_AFTER_SOLAR_BOUNDARY,
            3600.0,
        ),
        (
            PanchaPakshiHalf.DAY,
            12.0,
            PanchaPakshiSolarBoundaryRelation.ENDS_AT_SOLAR_BOUNDARY,
            0.0,
        ),
        (
            PanchaPakshiHalf.NIGHT,
            13.0,
            PanchaPakshiSolarBoundaryRelation.ENDS_BEFORE_SOLAR_BOUNDARY,
            -3600.0,
        ),
    ],
)
def test_materialization_reports_solar_topology_without_scaling_or_clipping(
    monkeypatch: pytest.MonkeyPatch,
    half: PanchaPakshiHalf,
    solar_half_hours: float,
    expected_relation: PanchaPakshiSolarBoundaryRelation,
    expected_seconds: float,
) -> None:
    result = _materialize(
        monkeypatch,
        half=half,
        solar_half_hours=solar_half_hours,
        paksha=PanchaPakshiPaksha.AMARA,
    )
    assert result.context.half is half
    assert result.context.paksha is PanchaPakshiPaksha.AMARA
    assert result.anchor_jd_ut1 == (
        result.context.sunrise_jd_ut1
        if half is PanchaPakshiHalf.DAY
        else result.context.sunset_jd_ut1
    )
    assert result.governing_solar_half_end_jd_ut1 == (
        result.context.sunset_jd_ut1
        if half is PanchaPakshiHalf.DAY
        else result.context.next_sunrise_jd_ut1
    )
    assert result.solar_boundary_relation is expected_relation
    assert result.signed_fixed_end_minus_solar_end_seconds_tt == pytest.approx(
        expected_seconds,
        abs=0.0001,
    )
    assert result.fixed_end_jd_tt - result.anchor_jd_tt == 0.5
    assert result.provenance.astronomical_routing_status == (
        "fixed_clock_materialization_performed_paksha_caller_supplied_no_current_cell"
    )


def test_cell_topology_and_boundary_coalescence_are_explicit() -> None:
    tolerance = 0.0001
    assert pancha_pakshi._fixed_clock_cell_relation(
        100.0,
        100.02,
        100.01,
    ) is PanchaPakshiMaterializedCellRelation.CROSSES_GOVERNING_SOLAR_HALF_END
    assert pancha_pakshi._fixed_clock_cell_relation(
        100.0,
        100.01,
        100.01,
    ) is PanchaPakshiMaterializedCellRelation.WITHIN_GOVERNING_SOLAR_HALF
    assert pancha_pakshi._fixed_clock_cell_relation(
        100.01,
        100.02,
        100.01,
    ) is PanchaPakshiMaterializedCellRelation.AFTER_GOVERNING_SOLAR_HALF

    near_boundary_days = 0.00005 / 86_400.0
    assert pancha_pakshi._fixed_clock_cell_relation(
        100.01 - near_boundary_days,
        100.02,
        100.01,
    ) is PanchaPakshiMaterializedCellRelation.CROSSES_GOVERNING_SOLAR_HALF_END
    assert pancha_pakshi._fixed_clock_cell_relation(
        100.0,
        100.01 + near_boundary_days,
        100.01,
    ) is PanchaPakshiMaterializedCellRelation.CROSSES_GOVERNING_SOLAR_HALF_END

    assert pancha_pakshi._fixed_clock_solar_boundary_relation(
        0.00005,
        tolerance,
    ) is PanchaPakshiSolarBoundaryRelation.ENDS_AT_SOLAR_BOUNDARY


@pytest.mark.requires_ephemeris
def test_configured_kernel_materialization_uses_reader_bound_tt_and_ut1() -> None:
    """Exercise the admitted clock composition without treating it as an oracle."""

    from moira._kernel_paths import find_planetary_kernel
    from moira.spk_reader import SpkReader

    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        pytest.skip("no planetary kernel found")

    with SpkReader(kernel_path) as reader:
        result = pancha_pakshi_fixed_clock_materialization_at(
            _PROFILE_ID,
            2_461_242.0,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )

    assert len(result.cells) == 25
    assert result.fixed_end_jd_tt - result.anchor_jd_tt == 0.5
    assert result.cells[0].start_jd_ut1 == result.anchor_jd_ut1
    assert result.cells[-1].end_jd_ut1 == result.fixed_end_jd_ut1
    assert result.governing_solar_half_end_jd_tt > result.anchor_jd_tt
    tolerance = result.policy.topology_coalescence_seconds
    residual = result.signed_fixed_end_minus_solar_end_seconds_tt
    if abs(residual) <= tolerance:
        expected = PanchaPakshiSolarBoundaryRelation.ENDS_AT_SOLAR_BOUNDARY
    elif residual < 0.0:
        expected = PanchaPakshiSolarBoundaryRelation.ENDS_BEFORE_SOLAR_BOUNDARY
    else:
        expected = PanchaPakshiSolarBoundaryRelation.ENDS_AFTER_SOLAR_BOUNDARY
    assert result.solar_boundary_relation is expected
    assert not hasattr(result, "current_cell")


def test_fixed_clock_capability_gate_precedes_solar_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    without_materialization = replace(
        profile,
        capabilities=tuple(
            capability
            for capability in profile.capabilities
            if capability is not PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION
        ),
    )
    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: without_materialization,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: pytest.fail(
            "solar resolution must not run before the fixed-clock capability gate"
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not admit 'fixed_clock_materialization'",
    ):
        pancha_pakshi_fixed_clock_materialization_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=_READER,  # type: ignore[arg-type]
        )


def test_fixed_clock_gate_rejects_research_profile_before_solar_resolution(
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
        pancha_pakshi_fixed_clock_materialization_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=_READER,  # type: ignore[arg-type]
        )


def test_fixed_clock_facade_uses_utc_adapter_and_forwards_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = _READER
    expected = object()
    calls: list[tuple[object, ...]] = []
    dt = datetime(2026, 7, 20, 15, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(facade, "jd_from_datetime", lambda value: 2_461_000.75)

    def materialize_from_utc(
        profile_id,
        jd_utc,
        latitude,
        longitude,
        *,
        paksha,
        reader,
    ):
        calls.append((profile_id, jd_utc, latitude, longitude, paksha, reader))
        return expected

    monkeypatch.setattr(
        pancha_pakshi,
        "_pancha_pakshi_fixed_clock_materialization_from_utc",
        materialize_from_utc,
    )
    assert engine.pancha_pakshi_fixed_clock_materialization(
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
            _READER,
        )
    ]

    parameters = inspect.signature(
        facade.Moira.pancha_pakshi_fixed_clock_materialization
    ).parameters
    assert parameters["profile_id"].default is inspect.Parameter.empty
    assert parameters["paksha"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["paksha"].default is inspect.Parameter.empty


def test_fixed_clock_facade_rejects_naive_datetime_before_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = _READER
    monkeypatch.setattr(
        pancha_pakshi,
        "_pancha_pakshi_fixed_clock_materialization_from_utc",
        lambda *args, **kwargs: pytest.fail(
            "naive datetime must fail before fixed-clock routing"
        ),
    )

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        engine.pancha_pakshi_fixed_clock_materialization(
            _PROFILE_ID,
            datetime(2026, 7, 20, 15, 30),
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
        )

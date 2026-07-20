"""Bounded Stage 2C Pancha Pakshi fixed-clock current-cell contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
import inspect
import math

import pytest

import moira._ephemeris_time as ephemeris_time
import moira._local_solar_day as local_solar_day
import moira._pancha_pakshi as internal
import moira.facade as facade
import moira.pancha_pakshi as pancha_pakshi
from moira._local_solar_day import LocalSolarDay
from moira.pancha_pakshi import (
    PanchaPakshiAdmissionStatus,
    PanchaPakshiCapability,
    PanchaPakshiCurrentCellSelectionStatus,
    PanchaPakshiFixedClockCurrentCellSelectionPolicy,
    PanchaPakshiHalf,
    PanchaPakshiPaksha,
    PanchaPakshiSolarBoundaryRelation,
    pancha_pakshi_fixed_clock_current_cell_at,
    pancha_pakshi_fixed_clock_materialization_at,
)


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_SUNRISE = 2_460_000.0
_TT_MINUS_UT1_SECONDS = 100.0
_READER = object()


def _bind_linear_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    def to_tt(jd_ut1, reader):
        assert reader is _READER
        return jd_ut1 + _TT_MINUS_UT1_SECONDS / 86_400.0

    def to_ut1(jd_tt, reader):
        assert reader is _READER
        return jd_tt - _TT_MINUS_UT1_SECONDS / 86_400.0

    monkeypatch.setattr(ephemeris_time, "_ut1_to_ephemeris_tt", to_tt)
    monkeypatch.setattr(ephemeris_time, "_ephemeris_tt_to_ut1", to_ut1)


def _solar_day(
    *,
    requested_jd_ut1: float,
    half: PanchaPakshiHalf = PanchaPakshiHalf.DAY,
    solar_half_hours: float = 14.0,
) -> LocalSolarDay:
    if half is PanchaPakshiHalf.DAY:
        sunrise = _SUNRISE
        sunset = sunrise + solar_half_hours / 24.0
        next_sunrise = sunset + 10.0 / 24.0
    else:
        sunrise = _SUNRISE
        sunset = sunrise + 10.0 / 24.0
        next_sunrise = sunset + solar_half_hours / 24.0
    return LocalSolarDay(
        jd=requested_jd_ut1,
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd=sunrise,
        sunset_jd=sunset,
        next_sunrise_jd=next_sunrise,
        weekday=0,
    )


def _select(
    monkeypatch: pytest.MonkeyPatch,
    solar_day: LocalSolarDay,
    *,
    paksha: PanchaPakshiPaksha = PanchaPakshiPaksha.PURVA,
):
    _bind_linear_clock(monkeypatch)
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: solar_day,
    )
    return pancha_pakshi_fixed_clock_current_cell_at(
        _PROFILE_ID,
        solar_day.jd,
        solar_day.latitude,
        solar_day.longitude,
        paksha=paksha,
        reader=_READER,  # type: ignore[arg-type]
    )


def test_current_cell_policy_is_explicit_exhaustive_and_immutable() -> None:
    policy = PanchaPakshiFixedClockCurrentCellSelectionPolicy()
    assert tuple(item.name for item in fields(policy)) == (
        "policy_id",
        "materialization_policy_id",
        "paksha_basis",
        "selection_time_scale",
        "interval_ownership",
        "solar_half_precedence",
        "membership_tolerance_seconds",
        "unmaterialized_solar_half_tail",
        "solar_end_clipping",
        "fixed_span_wrap",
        "fixed_span_repeat",
        "solar_proportional_scaling_status",
        "astronomical_paksha_inference_status",
    )
    assert policy.policy_id == (
        "fixed_clock_current_cell_half_open_solar_precedence_v1"
    )
    assert policy.materialization_policy_id == (
        "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
    )
    assert policy.paksha_basis == "caller_supplied_source_label"
    assert policy.selection_time_scale == "reader_bound_tt"
    assert policy.interval_ownership == "half_open"
    assert policy.solar_half_precedence == (
        "resolve_governing_solar_half_before_selection"
    )
    assert policy.membership_tolerance_seconds == 0.0
    assert policy.unmaterialized_solar_half_tail == "explicit_no_current_cell"
    assert policy.solar_end_clipping == "none"
    assert policy.fixed_span_wrap == "none"
    assert policy.fixed_span_repeat == "none"
    assert policy.solar_proportional_scaling_status == "not_performed"
    assert policy.astronomical_paksha_inference_status == "not_performed"

    with pytest.raises(TypeError):
        PanchaPakshiFixedClockCurrentCellSelectionPolicy(  # type: ignore[call-arg]
            membership_tolerance_seconds=1.0
        )
    with pytest.raises(FrozenInstanceError):
        policy.membership_tolerance_seconds = 1.0  # type: ignore[misc]


def test_anchor_and_all_shared_boundaries_use_exact_half_open_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_linear_clock(monkeypatch)
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    base_day = _solar_day(requested_jd_ut1=_SUNRISE)
    anchor = pancha_pakshi._pancha_pakshi_fixed_clock_current_cell_for_solar_day(
        profile,
        base_day,
        paksha=PanchaPakshiPaksha.PURVA,
        reader=_READER,  # type: ignore[arg-type]
    )
    assert anchor.selection_status is PanchaPakshiCurrentCellSelectionStatus.SELECTED
    assert anchor.current_cell is not None
    assert anchor.current_cell.schedule_cell_index == 0

    for expected_index, cell in enumerate(anchor.materialization.cells):
        midpoint = (
            pancha_pakshi._pancha_pakshi_fixed_clock_current_cell_for_solar_day(
                profile,
                replace(
                    base_day,
                    jd=(cell.start_jd_ut1 + cell.end_jd_ut1) / 2.0,
                ),
                paksha=PanchaPakshiPaksha.PURVA,
                reader=_READER,  # type: ignore[arg-type]
            )
        )
        assert midpoint.current_cell is not None
        assert midpoint.current_cell.schedule_cell_index == expected_index

    for expected_index, boundary_jd_ut1 in enumerate(
        (
            cell.end_jd_ut1
            for cell in anchor.materialization.cells[:-1]
        ),
        start=1,
    ):
        at_boundary = (
            pancha_pakshi._pancha_pakshi_fixed_clock_current_cell_for_solar_day(
                profile,
                replace(base_day, jd=boundary_jd_ut1),
                paksha=PanchaPakshiPaksha.PURVA,
                reader=_READER,  # type: ignore[arg-type]
            )
        )
        assert at_boundary.current_cell is not None
        assert at_boundary.current_cell.schedule_cell_index == expected_index

        immediately_before = (
            pancha_pakshi._pancha_pakshi_fixed_clock_current_cell_for_solar_day(
                profile,
                replace(
                    base_day,
                    jd=math.nextafter(boundary_jd_ut1, -math.inf),
                ),
                paksha=PanchaPakshiPaksha.PURVA,
                reader=_READER,  # type: ignore[arg-type]
            )
        )
        assert immediately_before.current_cell is not None
        assert immediately_before.current_cell.schedule_cell_index == (
            expected_index - 1
        )


def test_long_solar_half_tail_is_explicit_and_does_not_reuse_topology_tolerance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_end_ut1 = _SUNRISE + 0.5
    solar_end_ut1 = math.nextafter(fixed_end_ut1, math.inf)
    solar_day = LocalSolarDay(
        jd=fixed_end_ut1,
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd=_SUNRISE,
        sunset_jd=solar_end_ut1,
        next_sunrise_jd=solar_end_ut1 + 0.5,
        weekday=0,
    )
    result = _select(monkeypatch, solar_day)

    assert result.materialization.solar_boundary_relation is (
        PanchaPakshiSolarBoundaryRelation.ENDS_AT_SOLAR_BOUNDARY
    )
    assert result.selection_status is (
        PanchaPakshiCurrentCellSelectionStatus.UNMATERIALIZED_SOLAR_HALF_TAIL
    )
    assert result.current_cell is None
    assert result.requested_jd_tt == result.materialization.fixed_end_jd_tt
    assert result.provenance.astronomical_routing_status == (
        "fixed_clock_current_cell_selection_performed_paksha_caller_supplied_"
        "no_scaling_or_inference"
    )


def test_result_vessel_rejects_incoherent_status_cell_and_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _select(
        monkeypatch,
        _solar_day(requested_jd_ut1=_SUNRISE + 1.0 / 24.0),
    )
    assert selected.current_cell is not None

    with pytest.raises(ValueError, match="requires a current cell"):
        replace(selected, current_cell=None)
    with pytest.raises(ValueError, match="unique half-open TT match"):
        replace(selected, current_cell=replace(selected.current_cell))
    with pytest.raises(ValueError, match="requires current_cell=None"):
        replace(
            selected,
            selection_status=(
                PanchaPakshiCurrentCellSelectionStatus.UNMATERIALIZED_SOLAR_HALF_TAIL
            ),
        )
    with pytest.raises(ValueError, match="must be finite"):
        replace(selected, requested_jd_tt=math.nan)
    without_capability = replace(
        selected.provenance,
        capabilities=tuple(
            capability
            for capability in selected.provenance.capabilities
            if capability
            is not PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION
        ),
    )
    with pytest.raises(ValueError, match="does not admit"):
        replace(selected, provenance=without_capability)


def test_current_cell_capability_gate_precedes_solar_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    without_selection = replace(
        profile,
        capabilities=tuple(
            capability
            for capability in profile.capabilities
            if capability
            is not PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION
        ),
    )
    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: without_selection,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: pytest.fail(
            "solar resolution must not run before the current-cell capability gate"
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not admit 'fixed_clock_current_cell_selection'",
    ):
        pancha_pakshi_fixed_clock_current_cell_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=_READER,  # type: ignore[arg-type]
        )


def test_current_cell_requires_explicit_paksha_and_exposes_no_repair_knobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parameters = inspect.signature(
        pancha_pakshi_fixed_clock_current_cell_at
    ).parameters
    assert tuple(parameters) == (
        "profile_id",
        "jd_ut1",
        "latitude",
        "longitude",
        "paksha",
        "reader",
    )
    assert parameters["paksha"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["paksha"].default is inspect.Parameter.empty
    assert not {
        "tolerance_seconds",
        "clip",
        "wrap",
        "repeat",
        "scale",
        "infer_paksha",
    } & set(parameters)

    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: pytest.fail(
            "invalid paksha must fail before solar resolution"
        ),
    )
    with pytest.raises(TypeError, match="explicit PanchaPakshiPaksha"):
        pancha_pakshi_fixed_clock_current_cell_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha="purva",  # type: ignore[arg-type]
            reader=_READER,  # type: ignore[arg-type]
        )


def test_current_cell_public_gate_rejects_research_profile_before_solar_resolution(
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
            "solar resolution must not run before the public admission gate"
        ),
    )

    with pytest.raises(ValueError, match="is not publicly admitted"):
        pancha_pakshi_fixed_clock_current_cell_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=_READER,  # type: ignore[arg-type]
        )


def test_current_cell_facade_uses_utc_adapter_and_forwards_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = _READER
    expected = object()
    calls: list[tuple[object, ...]] = []
    dt = datetime(2026, 7, 20, 15, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(facade, "jd_from_datetime", lambda value: 2_461_000.75)

    def current_cell_from_utc(
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
        "_pancha_pakshi_fixed_clock_current_cell_from_utc",
        current_cell_from_utc,
    )
    assert engine.pancha_pakshi_fixed_clock_current_cell(
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
        facade.Moira.pancha_pakshi_fixed_clock_current_cell
    ).parameters
    assert parameters["profile_id"].default is inspect.Parameter.empty
    assert parameters["paksha"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["paksha"].default is inspect.Parameter.empty


def test_current_cell_facade_rejects_naive_datetime_before_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = _READER
    monkeypatch.setattr(
        pancha_pakshi,
        "_pancha_pakshi_fixed_clock_current_cell_from_utc",
        lambda *args, **kwargs: pytest.fail(
            "naive datetime must fail before current-cell routing"
        ),
    )

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        engine.pancha_pakshi_fixed_clock_current_cell(
            _PROFILE_ID,
            datetime(2026, 7, 20, 15, 30),
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
        )


@pytest.mark.requires_ephemeris
def test_de441_exact_boundary_long_tail_and_short_half_solar_precedence() -> None:
    """Exercise composition invariants without claiming a Pancha Pakshi oracle."""

    from moira._kernel_paths import find_planetary_kernel
    from moira.spk_reader import SpkReader

    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        pytest.skip("no planetary kernel found")

    with SpkReader(kernel_path) as reader:
        summer = pancha_pakshi_fixed_clock_materialization_at(
            _PROFILE_ID,
            2_461_212.75,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )
        assert summer.fixed_end_jd_tt < summer.governing_solar_half_end_jd_tt
        boundary_jd_ut1 = summer.cells[10].end_jd_ut1
        immediately_before = pancha_pakshi_fixed_clock_current_cell_at(
            _PROFILE_ID,
            math.nextafter(boundary_jd_ut1, -math.inf),
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )
        at_boundary = pancha_pakshi_fixed_clock_current_cell_at(
            _PROFILE_ID,
            boundary_jd_ut1,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )
        tail = pancha_pakshi_fixed_clock_current_cell_at(
            _PROFILE_ID,
            (summer.fixed_end_jd_ut1 + summer.context.sunset_jd_ut1) / 2.0,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )

        winter = pancha_pakshi_fixed_clock_materialization_at(
            _PROFILE_ID,
            2_461_395.75,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )
        assert winter.fixed_end_jd_tt > winter.governing_solar_half_end_jd_tt
        at_sunset = pancha_pakshi_fixed_clock_current_cell_at(
            _PROFILE_ID,
            winter.context.sunset_jd_ut1,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )

    assert immediately_before.current_cell is not None
    assert immediately_before.current_cell.schedule_cell_index == 10
    assert at_boundary.current_cell is not None
    assert at_boundary.current_cell.schedule_cell_index == 11
    assert tail.selection_status is (
        PanchaPakshiCurrentCellSelectionStatus.UNMATERIALIZED_SOLAR_HALF_TAIL
    )
    assert tail.current_cell is None
    assert at_sunset.materialization.context.half is PanchaPakshiHalf.NIGHT
    assert at_sunset.current_cell is not None
    assert at_sunset.current_cell.schedule_cell_index == 0

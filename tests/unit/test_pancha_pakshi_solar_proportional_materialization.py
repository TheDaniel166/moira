"""Stage 2D solar-proportional Pancha Pakshi engine contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
from fractions import Fraction
import inspect

import pytest

import moira
import moira._ephemeris_time as ephemeris_time
import moira._local_solar_day as local_solar_day
import moira._pancha_pakshi as internal
import moira.facade as facade
import moira.pancha_pakshi as pancha_pakshi
import moira.vedic as vedic
from moira._local_solar_day import LocalSolarDay
from moira.pancha_pakshi import (
    PanchaPakshiAdmissionStatus,
    PanchaPakshiCapability,
    PanchaPakshiHalf,
    PanchaPakshiPaksha,
    PanchaPakshiSolarProportionalCell,
    PanchaPakshiSolarProportionalMaterialization,
    PanchaPakshiSolarProportionalMaterializationPolicy,
    pancha_pakshi_solar_proportional_materialization_at,
)


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_SUNRISE = 2_460_000.0
_TT_MINUS_UT1_SECONDS = 100.0
_READER = object()


def _resolved_solar_day(
    *,
    half: PanchaPakshiHalf,
    solar_half_hours: float,
) -> LocalSolarDay:
    if half is PanchaPakshiHalf.DAY:
        sunrise = _SUNRISE
        sunset = sunrise + solar_half_hours / 24.0
        next_sunrise = sunrise + 1.0
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


def _bind_linear_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[float], list[float]]:
    to_tt_calls: list[float] = []
    to_ut1_calls: list[float] = []

    def to_tt(jd_ut1, reader):
        assert reader is _READER
        to_tt_calls.append(jd_ut1)
        return jd_ut1 + _TT_MINUS_UT1_SECONDS / 86_400.0

    def to_ut1(jd_tt, reader):
        assert reader is _READER
        to_ut1_calls.append(jd_tt)
        return jd_tt - _TT_MINUS_UT1_SECONDS / 86_400.0

    monkeypatch.setattr(ephemeris_time, "_ut1_to_ephemeris_tt", to_tt)
    monkeypatch.setattr(ephemeris_time, "_ephemeris_tt_to_ut1", to_ut1)
    return to_tt_calls, to_ut1_calls


def _materialize(
    monkeypatch: pytest.MonkeyPatch,
    *,
    half: PanchaPakshiHalf = PanchaPakshiHalf.DAY,
    solar_half_hours: float = 10.0,
    paksha: PanchaPakshiPaksha = PanchaPakshiPaksha.PURVA,
):
    clock_calls = _bind_linear_clock(monkeypatch)
    solar_day = _resolved_solar_day(
        half=half,
        solar_half_hours=solar_half_hours,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: solar_day,
    )
    result = pancha_pakshi_solar_proportional_materialization_at(
        _PROFILE_ID,
        solar_day.jd,
        solar_day.latitude,
        solar_day.longitude,
        paksha=paksha,
        reader=_READER,  # type: ignore[arg-type]
    )
    return result, solar_day, clock_calls


def test_policy_and_vessel_shapes_are_fixed_explicit_and_immutable() -> None:
    policy = PanchaPakshiSolarProportionalMaterializationPolicy()
    assert tuple(item.name for item in fields(policy)) == (
        "policy_id",
        "paksha_basis",
        "solar_context_basis",
        "day_anchor",
        "night_anchor",
        "nominal_offset_basis",
        "mapping_time_scale",
        "published_endpoint_time_scale",
        "endpoint_mapping",
        "endpoint_closure",
        "interval_ownership",
        "solar_end_clipping",
        "solar_half_wrap",
        "solar_half_repeat",
        "fixed_nazhigai_seconds_status",
        "current_cell_status",
        "astronomical_paksha_inference_status",
    )
    assert policy.policy_id == (
        "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
    )
    assert policy.paksha_basis == "caller_supplied_source_label"
    assert policy.solar_context_basis == "topocentric_sunrise_to_next_sunrise"
    assert policy.day_anchor == "governing_topocentric_sunrise"
    assert policy.night_anchor == "governing_topocentric_sunset"
    assert policy.nominal_offset_basis == (
        "exact_fraction_of_nominal_schedule_span"
    )
    assert policy.mapping_time_scale == "reader_bound_tt"
    assert policy.published_endpoint_time_scale == "ut1"
    assert policy.endpoint_mapping == (
        "independent_anchor_plus_fraction_of_governing_solar_half"
    )
    assert policy.endpoint_closure == (
        "exact_anchor_and_governing_solar_half_end"
    )
    assert policy.interval_ownership == "half_open"
    assert policy.solar_end_clipping == "none"
    assert policy.solar_half_wrap == "none"
    assert policy.solar_half_repeat == "none"
    assert policy.fixed_nazhigai_seconds_status == "not_used"
    assert policy.current_cell_status == "not_performed"
    assert policy.astronomical_paksha_inference_status == "not_performed"

    assert tuple(item.name for item in fields(PanchaPakshiSolarProportionalCell)) == (
        "schedule_cell_index",
        "nominal_cell",
        "start_offset_fraction",
        "end_offset_fraction",
        "span_fraction",
        "start_jd_tt",
        "end_jd_tt",
        "start_jd_ut1",
        "end_jd_ut1",
        "duration_seconds_tt",
    )
    assert tuple(
        item.name
        for item in fields(PanchaPakshiSolarProportionalMaterialization)
    ) == (
        "context",
        "policy",
        "anchor_jd_tt",
        "anchor_jd_ut1",
        "governing_solar_half_end_jd_tt",
        "governing_solar_half_end_jd_ut1",
        "solar_half_duration_seconds_tt",
        "cells",
        "provenance",
    )

    with pytest.raises(TypeError):
        PanchaPakshiSolarProportionalMaterializationPolicy(  # type: ignore[call-arg]
            mapping_time_scale="ut1"
        )
    with pytest.raises(FrozenInstanceError):
        policy.mapping_time_scale = "ut1"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("half", "solar_half_hours"),
    [
        (PanchaPakshiHalf.DAY, 10.0),
        (PanchaPakshiHalf.DAY, 14.0),
        (PanchaPakshiHalf.NIGHT, 10.0),
        (PanchaPakshiHalf.NIGHT, 14.0),
    ],
)
def test_exact_nominal_fractions_map_independently_with_outer_closure(
    monkeypatch: pytest.MonkeyPatch,
    half: PanchaPakshiHalf,
    solar_half_hours: float,
) -> None:
    result, solar_day, (to_tt_calls, to_ut1_calls) = _materialize(
        monkeypatch,
        half=half,
        solar_half_hours=solar_half_hours,
        paksha=PanchaPakshiPaksha.AMARA,
    )
    schedule = result.context.nominal_schedule
    expected_anchor_ut1 = (
        solar_day.sunrise_jd
        if half is PanchaPakshiHalf.DAY
        else solar_day.sunset_jd
    )
    expected_end_ut1 = (
        solar_day.sunset_jd
        if half is PanchaPakshiHalf.DAY
        else solar_day.next_sunrise_jd
    )

    assert to_tt_calls == [expected_anchor_ut1, expected_end_ut1]
    assert result.anchor_jd_ut1 == expected_anchor_ut1
    assert result.governing_solar_half_end_jd_ut1 == expected_end_ut1
    assert result.cells[0].start_jd_tt == result.anchor_jd_tt
    assert result.cells[0].start_jd_ut1 == result.anchor_jd_ut1
    assert result.cells[-1].end_jd_tt == result.governing_solar_half_end_jd_tt
    assert (
        result.cells[-1].end_jd_ut1
        == result.governing_solar_half_end_jd_ut1
    )
    assert len(result.cells) == 25
    assert tuple(cell.schedule_cell_index for cell in result.cells) == tuple(
        range(25)
    )

    unique_offsets = {
        offset
        for nominal_cell in schedule.cells
        for offset in (
            nominal_cell.start_nazhigai,
            nominal_cell.end_nazhigai,
        )
    }
    assert len(to_ut1_calls) == len(unique_offsets) - 2
    assert result.anchor_jd_tt not in to_ut1_calls
    assert result.governing_solar_half_end_jd_tt not in to_ut1_calls

    tt_span = (
        result.governing_solar_half_end_jd_tt - result.anchor_jd_tt
    )
    expected_interior_tt = [
        result.anchor_jd_tt
        + float(offset / schedule.span_nazhigai) * tt_span
        for offset in sorted(unique_offsets)
        if offset not in (Fraction(0), schedule.span_nazhigai)
    ]
    assert to_ut1_calls == expected_interior_tt
    for nominal_cell, cell in zip(schedule.cells, result.cells, strict=True):
        assert cell.nominal_cell is nominal_cell
        assert cell.start_offset_fraction == (
            nominal_cell.start_nazhigai / schedule.span_nazhigai
        )
        assert cell.end_offset_fraction == (
            nominal_cell.end_nazhigai / schedule.span_nazhigai
        )
        assert cell.span_fraction == (
            nominal_cell.duration_nazhigai / schedule.span_nazhigai
        )
        assert cell.span_fraction == (
            cell.end_offset_fraction - cell.start_offset_fraction
        )
        expected_start_tt = result.anchor_jd_tt + (
            float(cell.start_offset_fraction) * tt_span
        )
        expected_end_tt = result.anchor_jd_tt + (
            float(cell.end_offset_fraction) * tt_span
        )
        if cell.start_offset_fraction == 0:
            expected_start_tt = result.anchor_jd_tt
        if cell.end_offset_fraction == 1:
            expected_end_tt = result.governing_solar_half_end_jd_tt
        assert cell.start_jd_tt == expected_start_tt
        assert cell.end_jd_tt == expected_end_tt
        expected_start_ut1 = (
            result.anchor_jd_ut1
            if cell.start_offset_fraction == 0
            else expected_start_tt - _TT_MINUS_UT1_SECONDS / 86_400.0
        )
        expected_end_ut1 = (
            result.governing_solar_half_end_jd_ut1
            if cell.end_offset_fraction == 1
            else expected_end_tt - _TT_MINUS_UT1_SECONDS / 86_400.0
        )
        assert cell.start_jd_ut1 == expected_start_ut1
        assert cell.end_jd_ut1 == expected_end_ut1

    for left, right in zip(result.cells, result.cells[1:]):
        assert left.end_offset_fraction == right.start_offset_fraction
        assert left.end_jd_tt == right.start_jd_tt
        assert left.end_jd_ut1 == right.start_jd_ut1

    assert result.solar_half_duration_seconds_tt == (
        result.governing_solar_half_end_jd_tt - result.anchor_jd_tt
    ) * 86_400.0
    assert sum(cell.duration_seconds_tt for cell in result.cells) == pytest.approx(
        result.solar_half_duration_seconds_tt,
        abs=0.0001,
    )
    assert not hasattr(result, "current_cell")
    assert not hasattr(result, "fixed_end_jd_tt")
    assert not hasattr(result, "solar_boundary_relation")


def test_stage2d_does_not_use_fixed_1440_second_nazhigai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    short, _, _ = _materialize(monkeypatch, solar_half_hours=10.0)
    long, _, _ = _materialize(monkeypatch, solar_half_hours=14.0)
    short_first = short.cells[0]
    long_first = long.cells[0]

    assert short_first.span_fraction == long_first.span_fraction
    assert short_first.duration_seconds_tt != pytest.approx(1800.0)
    assert long_first.duration_seconds_tt != pytest.approx(1800.0)
    assert long_first.duration_seconds_tt / short_first.duration_seconds_tt == (
        pytest.approx(14.0 / 10.0, abs=1e-7)
    )
    assert short.policy.fixed_nazhigai_seconds_status == "not_used"


def test_stage2d_provenance_separates_source_nonattestation_from_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _, _ = _materialize(monkeypatch)
    omissions = {
        omission.feature: omission for omission in result.provenance.declared_omissions
    }

    assert result.provenance.astronomical_routing_status == (
        "solar_proportional_materialization_performed_paksha_caller_supplied_"
        "no_current_cell_or_inference"
    )
    assert "seasonal_scaling" not in omissions
    assert "source_attested_solar_proportional_materialization" in omissions
    source_nonattestation = omissions[
        "source_attested_solar_proportional_materialization"
    ]
    assert source_nonattestation.status == "omitted"
    assert "1879 witness does not attest" in source_nonattestation.reason
    assert "separately admitted modern proportional composition" in (
        source_nonattestation.reason
    )
    assert PanchaPakshiCapability.SOLAR_PROPORTIONAL_MATERIALIZATION in (
        result.provenance.capabilities
    )
    assert result.context.paksha is PanchaPakshiPaksha.PURVA


def test_stage2d_result_rejects_fraction_endpoint_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _, _ = _materialize(monkeypatch)
    cells = list(result.cells)
    shifted_boundary_jd_tt = cells[0].end_jd_tt + 10.0 / 86_400.0
    cells[0] = replace(
        cells[0],
        end_jd_tt=shifted_boundary_jd_tt,
        duration_seconds_tt=(
            shifted_boundary_jd_tt - cells[0].start_jd_tt
        )
        * 86_400.0,
    )
    cells[1] = replace(
        cells[1],
        start_jd_tt=shifted_boundary_jd_tt,
        duration_seconds_tt=(
            cells[1].end_jd_tt - shifted_boundary_jd_tt
        )
        * 86_400.0,
    )

    with pytest.raises(
        ValueError,
        match="does not match its exact nominal fraction",
    ):
        replace(result, cells=tuple(cells))


@pytest.mark.parametrize(
    "provenance",
    [
        "wrong_routing_status",
        "missing_source_nonattestation",
    ],
)
def test_stage2d_result_rejects_contradictory_provenance(
    monkeypatch: pytest.MonkeyPatch,
    provenance: str,
) -> None:
    result, _, _ = _materialize(monkeypatch)
    if provenance == "wrong_routing_status":
        forged = replace(
            result.provenance,
            astronomical_routing_status="not_performed",
        )
    else:
        forged = replace(
            result.provenance,
            declared_omissions=tuple(
                omission
                for omission in result.provenance.declared_omissions
                if omission.feature
                != "source_attested_solar_proportional_materialization"
            ),
        )

    with pytest.raises(
        ValueError,
        match="must equal the exact Stage 2D transformation",
    ):
        replace(result, provenance=forged)


def test_stage2d_capability_gate_precedes_solar_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    without_capability = replace(
        profile,
        capabilities=tuple(
            capability
            for capability in profile.capabilities
            if capability
            is not PanchaPakshiCapability.SOLAR_PROPORTIONAL_MATERIALIZATION
        ),
    )
    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: without_capability,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: pytest.fail(
            "solar resolution must not precede the Stage 2D capability gate"
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not admit 'solar_proportional_materialization'",
    ):
        pancha_pakshi_solar_proportional_materialization_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=_READER,  # type: ignore[arg-type]
        )


def test_stage2d_admission_gate_precedes_solar_resolution(
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
            "solar resolution must not precede the public-admission gate"
        ),
    )

    with pytest.raises(ValueError, match="is not publicly admitted"):
        pancha_pakshi_solar_proportional_materialization_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=_READER,  # type: ignore[arg-type]
        )


def test_stage2d_public_signature_has_no_scaling_or_inference_knob() -> None:
    parameters = inspect.signature(
        pancha_pakshi_solar_proportional_materialization_at
    ).parameters
    assert tuple(parameters) == (
        "profile_id",
        "jd_ut1",
        "latitude",
        "longitude",
        "paksha",
        "reader",
    )
    assert parameters["profile_id"].default is inspect.Parameter.empty
    assert parameters["paksha"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["paksha"].default is inspect.Parameter.empty
    assert parameters["reader"].default is None


def test_stage2d_facade_uses_utc_adapter_and_forwards_reader(
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
        "_pancha_pakshi_solar_proportional_materialization_from_utc",
        materialize_from_utc,
    )
    assert engine.pancha_pakshi_solar_proportional_materialization(
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
        facade.Moira.pancha_pakshi_solar_proportional_materialization
    ).parameters
    assert parameters["profile_id"].default is inspect.Parameter.empty
    assert parameters["paksha"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["paksha"].default is inspect.Parameter.empty


def test_stage2d_facade_rejects_naive_datetime_before_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = _READER
    monkeypatch.setattr(
        pancha_pakshi,
        "_pancha_pakshi_solar_proportional_materialization_from_utc",
        lambda *args, **kwargs: pytest.fail(
            "naive datetime must fail before Stage 2D routing"
        ),
    )

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        engine.pancha_pakshi_solar_proportional_materialization(
            _PROFILE_ID,
            datetime(2026, 7, 20, 15, 30),
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
        )


def test_stage2d_exports_are_identical_across_public_modules() -> None:
    names = (
        "PanchaPakshiSolarProportionalCell",
        "PanchaPakshiSolarProportionalMaterialization",
        "PanchaPakshiSolarProportionalMaterializationPolicy",
        "pancha_pakshi_solar_proportional_materialization_at",
    )
    for name in names:
        expected = getattr(pancha_pakshi, name)
        assert getattr(moira, name) is expected
        assert getattr(facade, name) is expected
        assert getattr(vedic, name) is expected


@pytest.mark.requires_ephemeris
def test_configured_kernel_stage2d_preserves_structural_invariants() -> None:
    """Exercise DE441 clock composition without treating it as an oracle."""

    from moira._kernel_paths import find_planetary_kernel
    from moira.spk_reader import SpkReader

    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        pytest.skip("no planetary kernel found")

    with SpkReader(kernel_path) as reader:
        result = pancha_pakshi_solar_proportional_materialization_at(
            _PROFILE_ID,
            2_461_242.0,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=reader,
        )

    assert len(result.cells) == 25
    assert result.cells[0].start_jd_tt == result.anchor_jd_tt
    assert result.cells[-1].end_jd_tt == result.governing_solar_half_end_jd_tt
    assert result.cells[0].start_jd_ut1 == result.anchor_jd_ut1
    assert (
        result.cells[-1].end_jd_ut1
        == result.governing_solar_half_end_jd_ut1
    )
    assert result.cells[0].start_offset_fraction == Fraction(0)
    assert result.cells[-1].end_offset_fraction == Fraction(1)
    assert sum((cell.span_fraction for cell in result.cells), Fraction()) == 1
    assert result.solar_half_duration_seconds_tt > 0.0
    assert not hasattr(result, "current_cell")

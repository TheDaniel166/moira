"""Stage 2E solar-proportional Pancha Pakshi current-cell contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
import inspect
import math
from types import SimpleNamespace

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
    PanchaPakshiCurrentCellSelectionStatus,
    PanchaPakshiHalf,
    PanchaPakshiPaksha,
    PanchaPakshiSolarProportionalCurrentCellSelectionPolicy,
    pancha_pakshi_solar_proportional_current_cell_at,
)


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_SUNRISE = 2_460_000.0
_TT_MINUS_UT1_SECONDS = 100.0
_READER = object()
_ROUTING_STATUS = (
    "solar_proportional_current_cell_selection_performed_paksha_caller_"
    "supplied_no_fixed_clock_mixing_or_inference"
)


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
    half: PanchaPakshiHalf = PanchaPakshiHalf.DAY,
    solar_half_hours: float = 12.0,
    requested_jd_ut1: float | None = None,
) -> LocalSolarDay:
    if half is PanchaPakshiHalf.DAY:
        sunrise = _SUNRISE
        sunset = sunrise + solar_half_hours / 24.0
        next_sunrise = sunrise + 1.0
        default_requested = (sunrise + sunset) / 2.0
    else:
        sunrise = _SUNRISE
        sunset = sunrise + (24.0 - solar_half_hours) / 24.0
        next_sunrise = sunrise + 1.0
        default_requested = (sunset + next_sunrise) / 2.0
    return LocalSolarDay(
        jd=(default_requested if requested_jd_ut1 is None else requested_jd_ut1),
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd=sunrise,
        sunset_jd=sunset,
        next_sunrise_jd=next_sunrise,
        weekday=0,
    )


def _select_for_solar_day(
    solar_day: LocalSolarDay,
    *,
    paksha: PanchaPakshiPaksha = PanchaPakshiPaksha.PURVA,
):
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    return (
        pancha_pakshi._pancha_pakshi_solar_proportional_current_cell_for_solar_day(
            profile,
            solar_day,
            paksha=paksha,
            reader=_READER,  # type: ignore[arg-type]
        )
    )


def test_stage2e_policy_is_explicit_exhaustive_and_immutable() -> None:
    policy = PanchaPakshiSolarProportionalCurrentCellSelectionPolicy()

    assert tuple(item.name for item in fields(policy)) == (
        "policy_id",
        "materialization_policy_id",
        "paksha_basis",
        "selection_time_scale",
        "interval_ownership",
        "solar_half_precedence",
        "membership_tolerance_seconds",
        "coverage_requirement",
        "required_match_count",
        "unmaterialized_solar_half_tail_status",
        "invalid_match_policy",
        "fixed_clock_mixing_status",
        "astronomical_paksha_inference_status",
    )
    assert policy.policy_id == (
        "solar_proportional_current_cell_half_open_solar_precedence_v1"
    )
    assert policy.materialization_policy_id == (
        "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
    )
    assert policy.paksha_basis == "caller_supplied_source_label"
    assert policy.selection_time_scale == "reader_bound_tt"
    assert policy.interval_ownership == "half_open"
    assert policy.solar_half_precedence == (
        "resolve_governing_solar_half_before_selection"
    )
    assert policy.membership_tolerance_seconds == 0.0
    assert policy.coverage_requirement == "complete_governing_solar_half"
    assert policy.required_match_count == 1
    assert policy.unmaterialized_solar_half_tail_status == "not_applicable"
    assert policy.invalid_match_policy == "fail_closed"
    assert policy.fixed_clock_mixing_status == "not_performed"
    assert policy.astronomical_paksha_inference_status == "not_performed"

    with pytest.raises(TypeError):
        PanchaPakshiSolarProportionalCurrentCellSelectionPolicy(  # type: ignore[call-arg]
            membership_tolerance_seconds=1.0
        )
    with pytest.raises(FrozenInstanceError):
        policy.membership_tolerance_seconds = 1.0  # type: ignore[misc]


def test_anchor_midpoints_and_shared_boundaries_have_exact_half_open_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_linear_clock(monkeypatch)
    base_day = _solar_day(requested_jd_ut1=_SUNRISE)
    anchor = _select_for_solar_day(base_day)

    assert anchor.selection_status is PanchaPakshiCurrentCellSelectionStatus.SELECTED
    assert anchor.current_cell.schedule_cell_index == 0

    for expected_index, cell in enumerate(anchor.materialization.cells):
        midpoint = _select_for_solar_day(
            replace(
                base_day,
                jd=(cell.start_jd_ut1 + cell.end_jd_ut1) / 2.0,
            )
        )
        assert midpoint.current_cell.schedule_cell_index == expected_index

    for expected_index, boundary_jd_ut1 in enumerate(
        (cell.end_jd_ut1 for cell in anchor.materialization.cells[:-1]),
        start=1,
    ):
        at_boundary = _select_for_solar_day(
            replace(base_day, jd=boundary_jd_ut1)
        )
        immediately_before = _select_for_solar_day(
            replace(
                base_day,
                jd=math.nextafter(boundary_jd_ut1, -math.inf),
            )
        )
        assert at_boundary.current_cell.schedule_cell_index == expected_index
        assert immediately_before.current_cell.schedule_cell_index == (
            expected_index - 1
        )


@pytest.mark.parametrize(
    ("half", "solar_half_hours"),
    [
        (PanchaPakshiHalf.DAY, 10.0),
        (PanchaPakshiHalf.DAY, 14.0),
        (PanchaPakshiHalf.NIGHT, 10.0),
        (PanchaPakshiHalf.NIGHT, 14.0),
    ],
)
def test_complete_proportional_partition_has_no_tail_state(
    monkeypatch: pytest.MonkeyPatch,
    half: PanchaPakshiHalf,
    solar_half_hours: float,
) -> None:
    _bind_linear_clock(monkeypatch)
    solar_day = _solar_day(half=half, solar_half_hours=solar_half_hours)
    baseline = _select_for_solar_day(solar_day)
    final_instant = math.nextafter(
        baseline.materialization.governing_solar_half_end_jd_ut1,
        -math.inf,
    )
    selected = _select_for_solar_day(replace(solar_day, jd=final_instant))

    assert selected.selection_status is PanchaPakshiCurrentCellSelectionStatus.SELECTED
    assert selected.current_cell.schedule_cell_index == 24
    assert selected.current_cell.end_jd_tt == (
        selected.materialization.governing_solar_half_end_jd_tt
    )
    assert selected.policy.unmaterialized_solar_half_tail_status == (
        "not_applicable"
    )


def test_exact_sunset_routes_to_first_cell_of_new_night_half(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_linear_clock(monkeypatch)
    day = _solar_day(half=PanchaPakshiHalf.DAY, solar_half_hours=10.0)
    at_sunset = _select_for_solar_day(replace(day, jd=day.sunset_jd))

    assert at_sunset.materialization.context.half is PanchaPakshiHalf.NIGHT
    assert at_sunset.current_cell.schedule_cell_index == 0
    assert at_sunset.requested_jd_tt == at_sunset.materialization.anchor_jd_tt


def test_stage2e_provenance_preserves_stage2d_source_policy_separation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_linear_clock(monkeypatch)
    result = _select_for_solar_day(_solar_day())
    materialization_provenance = result.materialization.provenance
    omissions = {
        omission.feature: omission
        for omission in result.provenance.declared_omissions
    }

    assert result.provenance == replace(
        materialization_provenance,
        astronomical_routing_status=_ROUTING_STATUS,
    )
    assert result.provenance.astronomical_routing_status == _ROUTING_STATUS
    assert "seasonal_scaling" not in omissions
    assert "source_attested_solar_proportional_materialization" in omissions
    assert result.materialization.policy.current_cell_status == "not_performed"
    assert not hasattr(result.materialization, "current_cell")


def test_stage2e_result_rejects_incoherent_status_cell_and_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_linear_clock(monkeypatch)
    selected = _select_for_solar_day(_solar_day())

    with pytest.raises(TypeError, match="PanchaPakshiSolarProportionalCell"):
        replace(selected, current_cell=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="requires selected status"):
        replace(
            selected,
            selection_status=(
                PanchaPakshiCurrentCellSelectionStatus.UNMATERIALIZED_SOLAR_HALF_TAIL
            ),
        )
    with pytest.raises(ValueError, match="unique materialization tuple member"):
        replace(selected, current_cell=replace(selected.current_cell))
    with pytest.raises(ValueError, match="must be finite"):
        replace(selected, requested_jd_tt=math.nan)
    with pytest.raises(ValueError, match="governing half-open solar half"):
        replace(
            selected,
            requested_jd_tt=(
                selected.materialization.governing_solar_half_end_jd_tt
            ),
        )

    wrong_status = replace(
        selected.provenance,
        astronomical_routing_status="not_performed",
    )
    with pytest.raises(ValueError, match="exact Stage 2E transformation"):
        replace(selected, provenance=wrong_status)

    without_capability = replace(
        selected.provenance,
        capabilities=tuple(
            capability
            for capability in selected.provenance.capabilities
            if capability
            is not (
                PanchaPakshiCapability.SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION
            )
        ),
    )
    with pytest.raises(ValueError, match="does not admit"):
        replace(selected, provenance=without_capability)


@pytest.mark.parametrize("match_count", [0, 2])
def test_stage2e_factory_fails_closed_on_invalid_match_count(
    monkeypatch: pytest.MonkeyPatch,
    match_count: int,
) -> None:
    _bind_linear_clock(monkeypatch)
    solar_day = _solar_day()
    baseline = _select_for_solar_day(solar_day).materialization
    matching_cell = baseline.cells[0]
    fake = SimpleNamespace(
        anchor_jd_tt=baseline.anchor_jd_tt,
        governing_solar_half_end_jd_tt=(
            baseline.governing_solar_half_end_jd_tt
        ),
        cells=(() if match_count == 0 else (matching_cell, matching_cell)),
    )
    monkeypatch.setattr(
        pancha_pakshi,
        "_pancha_pakshi_solar_proportional_for_solar_day",
        lambda *args, **kwargs: fake,
    )

    with pytest.raises(
        pancha_pakshi.PanchaPakshiDataError,
        match="requires exactly one",
    ):
        _select_for_solar_day(
            replace(solar_day, jd=baseline.anchor_jd_ut1)
        )


def test_stage2e_capability_gate_precedes_solar_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    without_capability = replace(
        profile,
        capabilities=tuple(
            capability
            for capability in profile.capabilities
            if capability
            is not (
                PanchaPakshiCapability.SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION
            )
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
            "solar resolution must not precede the Stage 2E capability gate"
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not admit 'solar_proportional_current_cell_selection'",
    ):
        pancha_pakshi_solar_proportional_current_cell_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=_READER,  # type: ignore[arg-type]
        )


def test_stage2e_admission_and_paksha_fail_before_solar_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    research_only = replace(
        profile,
        admission_status=PanchaPakshiAdmissionStatus.RESEARCH_ONLY,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: pytest.fail(
            "invalid admission or paksha must fail before solar resolution"
        ),
    )
    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: research_only,
    )
    with pytest.raises(ValueError, match="is not publicly admitted"):
        pancha_pakshi_solar_proportional_current_cell_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
            reader=_READER,  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="explicit PanchaPakshiPaksha"):
        pancha_pakshi_solar_proportional_current_cell_at(
            _PROFILE_ID,
            _SUNRISE,
            13.0827,
            80.2707,
            paksha="purva",  # type: ignore[arg-type]
            reader=_READER,  # type: ignore[arg-type]
        )


def test_stage2e_signature_has_no_repair_or_inference_knobs() -> None:
    parameters = inspect.signature(
        pancha_pakshi_solar_proportional_current_cell_at
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
    assert not {
        "tolerance_seconds",
        "clip",
        "wrap",
        "repeat",
        "fixed_clock",
        "infer_paksha",
    } & set(parameters)


def test_stage2e_facade_uses_utc_adapter_and_forwards_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = _READER
    expected = object()
    calls: list[tuple[object, ...]] = []
    dt = datetime(2026, 7, 20, 15, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(facade, "jd_from_datetime", lambda value: 2_461_000.75)

    def select_from_utc(
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
        "_pancha_pakshi_solar_proportional_current_cell_from_utc",
        select_from_utc,
    )
    assert engine.pancha_pakshi_solar_proportional_current_cell(
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
        facade.Moira.pancha_pakshi_solar_proportional_current_cell
    ).parameters
    assert parameters["profile_id"].default is inspect.Parameter.empty
    assert parameters["paksha"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["paksha"].default is inspect.Parameter.empty


def test_stage2e_facade_rejects_naive_datetime_before_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object.__new__(facade.Moira)
    engine._reader_obj = _READER
    monkeypatch.setattr(
        pancha_pakshi,
        "_pancha_pakshi_solar_proportional_current_cell_from_utc",
        lambda *args, **kwargs: pytest.fail(
            "naive datetime must fail before Stage 2E routing"
        ),
    )

    with pytest.raises(ValueError, match="timezone-aware datetime"):
        engine.pancha_pakshi_solar_proportional_current_cell(
            _PROFILE_ID,
            datetime(2026, 7, 20, 15, 30),
            13.0827,
            80.2707,
            paksha=PanchaPakshiPaksha.PURVA,
        )


def test_stage2e_exports_are_identical_across_public_modules() -> None:
    names = (
        "PanchaPakshiSolarProportionalCurrentCellSelection",
        "PanchaPakshiSolarProportionalCurrentCellSelectionPolicy",
        "pancha_pakshi_solar_proportional_current_cell_at",
    )
    for name in names:
        expected = getattr(pancha_pakshi, name)
        assert getattr(moira, name) is expected
        assert getattr(facade, name) is expected
        assert getattr(vedic, name) is expected


@pytest.mark.requires_ephemeris
def test_de441_every_published_interior_boundary_roundtrips_to_following_cell() -> None:
    """Validate numerical ownership; this is not a Pancha Pakshi oracle."""

    from moira._kernel_paths import find_planetary_kernel
    from moira._local_solar_day import _local_solar_day_from_ut1
    from moira.spk_reader import SpkReader

    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        pytest.skip("no planetary kernel found")

    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    with SpkReader(kernel_path) as reader:
        for seed_jd_ut1 in (2_461_212.75, 2_461_395.75):
            resolved = _local_solar_day_from_ut1(
                seed_jd_ut1,
                13.0827,
                80.2707,
                reader,
                bounds_owner="pancha-pakshi-stage2e-boundary-validation",
            )
            representative_halves = (
                replace(
                    resolved,
                    jd=(resolved.sunrise_jd + resolved.sunset_jd) / 2.0,
                ),
                replace(
                    resolved,
                    jd=(resolved.sunset_jd + resolved.next_sunrise_jd) / 2.0,
                ),
            )
            for solar_day in representative_halves:
                materialization = (
                    pancha_pakshi._pancha_pakshi_solar_proportional_for_solar_day(
                        profile,
                        solar_day,
                        paksha=PanchaPakshiPaksha.PURVA,
                        reader=reader,
                    )
                )
                for expected_index, boundary_jd_ut1 in enumerate(
                    (
                        cell.end_jd_ut1
                        for cell in materialization.cells[:-1]
                    ),
                    start=1,
                ):
                    selected = (
                        pancha_pakshi._pancha_pakshi_solar_proportional_current_cell_for_solar_day(
                            profile,
                            replace(solar_day, jd=boundary_jd_ut1),
                            paksha=PanchaPakshiPaksha.PURVA,
                            reader=reader,
                        )
                    )
                    assert selected.current_cell.schedule_cell_index == (
                        expected_index
                    )

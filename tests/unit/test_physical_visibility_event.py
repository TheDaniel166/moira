"""Public-contract tests for the Phase 3 physical visibility-event path."""

from __future__ import annotations

import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

import moira.heliacal as heliacal
from moira._visibility_lut import (
    VisibilityDataPackConfig,
    VisibilityDataPackReceipt,
)
from moira.constants import Body
from moira.heliacal import (
    PhysicalBackgroundScope,
    PhysicalAtmosphereInput,
    PhysicalDirectionalBackground,
    PhysicalEventTimeSemantics,
    PhysicalVisibilityAssessment,
    PhysicalVisibilityBoundarySource,
    PhysicalVisibilityCrossingDirection,
    PhysicalVisibilityEvidenceState,
    PhysicalVisibilityErrorBudgetReceipt,
    PhysicalVisibilityPhase,
    PhysicalVisibilityPolicy,
    PhysicalVisibilitySearchPolicy,
    PhysicalVisibilityStatus,
    VisibilityComponentReceipt,
    physical_visibility_event,
)


_SHA = (
    "cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c"
)
_PACK_RECEIPT = VisibilityDataPackReceipt(
    pack_id="moira-physical-heliacal-visibility",
    version="1.2.0",
    compatibility_id=(
        "moira-physical-heliacal-visibility-data-pack-v1.2"
    ),
    composite_model_id="clear_sky_naked_eye_point_source_v1",
    table_format_id="test-format",
    engine_contract_id="moira-physical-visibility-engine-contract-v1",
    engine_contract_version=1,
    manifest_sha256=_SHA,
    generation_fingerprint="test-generation",
    payload_sha256=(("payload.bin", _SHA),),
    source_artifact_spec_id="test-source-artifact",
    source_artifact_manifest_sha256=_SHA,
    source_dataset_ids=("test-source",),
    license="test-only",
    notice_sha256=_SHA,
)


def _policy() -> PhysicalVisibilityPolicy:
    return PhysicalVisibilityPolicy(
        background=PhysicalDirectionalBackground(
            photopic_luminance_cd_m2=1.0e-4,
            scotopic_luminance_cd_m2=1.5e-4,
            scope=PhysicalBackgroundScope.DARK_SKY_ANCHOR,
            component_ids=("test_dark_sky",),
            source_id="test-background",
            source_receipt_sha256=_SHA,
            method_id="test-method",
        )
    )


def _search_policy() -> PhysicalVisibilitySearchPolicy:
    return PhysicalVisibilitySearchPolicy(
        search_window_days=1,
        scan_step_days=0.01,
        adaptive_minimum_step_days=1.0e-4,
        root_time_tolerance_days=1.0e-8,
        root_margin_tolerance_magnitude=1.0e-8,
        near_zero_tolerance_magnitude=1.0e-3,
        curvature_tolerance_magnitude=1.0e-4,
    )


def test_physical_policy_rejects_an_untyped_atmosphere() -> None:
    with pytest.raises(
        TypeError,
        match="atmosphere must be a PhysicalAtmosphereInput",
    ):
        PhysicalVisibilityPolicy(atmosphere="us_standard")  # type: ignore[arg-type]


def _day_and_fraction(jd_ut: float) -> tuple[int, float]:
    day_key = math.floor(jd_ut + 0.5)
    return day_key, jd_ut - (day_key - 0.5)


def _morning_geometry(
    target: str,
    jd_ut: float,
    _lat: float,
    _lon: float,
) -> tuple[float, float]:
    _day_key, fraction = _day_and_fraction(jd_ut)
    if target == Body.SUN:
        altitude = -20.0 * math.cos(2.0 * math.pi * fraction)
    else:
        altitude = 30.0 * math.sin(
            2.0 * math.pi * (fraction - 0.15)
        )
    return 180.0, altitude


def _evening_geometry(
    target: str,
    jd_ut: float,
    _lat: float,
    _lon: float,
) -> tuple[float, float]:
    _day_key, fraction = _day_and_fraction(jd_ut)
    if target == Body.SUN:
        altitude = -20.0 * math.cos(2.0 * math.pi * fraction)
    else:
        altitude = 30.0 * math.sin(
            2.0 * math.pi * (fraction - 0.35)
        )
    return 180.0, altitude


def _morning_setting_geometry(
    target: str,
    jd_ut: float,
    _lat: float,
    _lon: float,
) -> tuple[float, float]:
    _day_key, fraction = _day_and_fraction(jd_ut)
    if target == Body.SUN:
        altitude = -20.0 * math.cos(2.0 * math.pi * fraction)
    else:
        altitude = 20.0 * (0.20 - fraction)
    return 180.0, altitude


def _evening_rising_geometry(
    target: str,
    jd_ut: float,
    _lat: float,
    _lon: float,
) -> tuple[float, float]:
    _day_key, fraction = _day_and_fraction(jd_ut)
    if target == Body.SUN:
        altitude = -20.0 * math.cos(2.0 * math.pi * fraction)
    else:
        altitude = 20.0 * (fraction - 0.80)
    return 180.0, altitude


def _assessment(
    body: str,
    jd_ut: float,
    lat: float,
    lon: float,
    policy: PhysicalVisibilityPolicy,
    margin: float,
) -> PhysicalVisibilityAssessment:
    numerical_half_width = 0.01
    error_budget = PhysicalVisibilityErrorBudgetReceipt(
        method_id="test-pack-numerical-envelope",
        background_error_authority="test",
        solver_relative_standard_error_multiplier=1.0,
        background_mesopic_luminance_envelope_lower_cd_m2=1.0e-4,
        background_mesopic_luminance_envelope_upper_cd_m2=2.0e-4,
        limiting_magnitude_envelope_lower=5.0,
        limiting_magnitude_envelope_upper=5.1,
        conditioned_target_magnitude_maximum_pack_error=(
            numerical_half_width
        ),
        visibility_margin_envelope_lower_magnitude=(
            margin - numerical_half_width
        ),
        visibility_margin_envelope_upper_magnitude=(
            margin + numerical_half_width
        ),
        visibility_margin_envelope_maximum_deviation_magnitude=(
            numerical_half_width
        ),
        visibility_classification_within_data_pack_envelope=(
            "indeterminate"
        ),
        included_error_sources=("test-pack-numerical",),
        unquantified_error_sources=("test-scientific",),
    )
    return PhysicalVisibilityAssessment(
        body=body,
        jd_ut=jd_ut,
        latitude_deg=lat,
        longitude_deg=lon,
        status=PhysicalVisibilityStatus.EVALUATED,
        evidence_state=(
            PhysicalVisibilityEvidenceState.EVALUATED_CLEAR_SKY
        ),
        reason=None,
        true_target_altitude_deg=5.0,
        apparent_target_altitude_deg=5.0,
        true_solar_center_altitude_deg=-8.0,
        relative_solar_azimuth_deg=20.0,
        geometrically_visible=True,
        visible=margin >= 0.0,
        observable=margin >= 0.0,
        visibility_margin_magnitude=margin,
        data_pack_receipt=_PACK_RECEIPT,
        atmosphere_receipt=heliacal._physical_atmosphere_receipt(
            policy.atmosphere,
            within_data_pack_domain=True,
        ),
        validity_domain_receipt=None,
        observer_protocol_receipt=(
            heliacal._physical_observer_receipt(policy)
        ),
        background_receipt=None,
        target_receipt=None,
        threshold_receipt=None,
        error_budget_receipt=error_budget,
        components=(
            VisibilityComponentReceipt(
                role="test",
                component_id="test-component",
                source_ids=("test-source",),
            ),
        ),
    )


def _install_synthetic_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    geometry,
    margin_for,
    margin_for_policy=None,
    solar_domain: tuple[float, float] = (-18.0, 0.0),
    target_domain: tuple[float, float] = (-1.0, 45.0),
) -> list[VisibilityDataPackConfig]:
    load_calls: list[VisibilityDataPackConfig] = []
    pack = SimpleNamespace(
        receipt=_PACK_RECEIPT,
        domain=SimpleNamespace(
            solar_center_altitude_deg=solar_domain,
            target_true_altitude_deg=target_domain,
        ),
    )

    def load(config: VisibilityDataPackConfig):
        load_calls.append(config)
        return pack

    def assess(
        body: str,
        jd_ut: float,
        lat: float,
        lon: float,
        *,
        data_pack_config: VisibilityDataPackConfig,
        policy: PhysicalVisibilityPolicy,
        loaded_data_pack,
    ) -> PhysicalVisibilityAssessment:
        assert loaded_data_pack is pack
        assert isinstance(data_pack_config, VisibilityDataPackConfig)
        return _assessment(
            body,
            jd_ut,
            lat,
            lon,
            policy,
            (
                margin_for_policy(jd_ut, policy)
                if margin_for_policy is not None
                else margin_for(jd_ut)
            ),
        )

    monkeypatch.setattr(heliacal, "load_visibility_data_pack", load)
    monkeypatch.setattr(
        heliacal,
        "_physical_atmosphere_matches",
        lambda _atmosphere, _domain: True,
    )
    monkeypatch.setattr(heliacal, "_true_horizontal", geometry)
    monkeypatch.setattr(
        heliacal,
        "apply_refraction",
        lambda altitude, **_kwargs: altitude,
    )
    monkeypatch.setattr(
        heliacal,
        "_physical_visibility_assessment_impl",
        assess,
    )
    monkeypatch.setattr(
        heliacal,
        "_PHYSICAL_EVENT_GEOMETRY_CERTIFICATE",
        heliacal._ScalarLipschitzCertificate(
            certificate_id="synthetic-test:geometry",
            maximum_absolute_rate_per_day=256.0,
            source_receipt_sha256=_SHA,
        ),
    )
    monkeypatch.setattr(
        heliacal,
        "_PHYSICAL_EVENT_MARGIN_CERTIFICATE",
        heliacal._ScalarLipschitzCertificate(
            certificate_id="synthetic-test:margin",
            maximum_absolute_rate_per_day=2.0,
            source_receipt_sha256=_SHA,
        ),
    )
    return load_calls


def test_morning_first_rising_returns_refined_margin_root_and_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def margin_for(jd_ut: float) -> float:
        day_key, fraction = _day_and_fraction(jd_ut)
        if day_key < 100:
            return -1.0
        return fraction - 0.20

    load_calls = _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=margin_for,
    )
    result = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.reason is None
    assert result.observation_day_key == 100
    assert result.comparison_observation_day_key == 99
    assert result.comparison_day_status == "does_not_qualify"
    assert result.event_jd_ut == pytest.approx(99.7, abs=2.0e-6)
    assert (
        result.event_time_semantics
        is PhysicalEventTimeSemantics.VISIBILITY_MARGIN_ZERO
    )
    assert (
        result.boundary_source
        is PhysicalVisibilityBoundarySource.VISIBILITY_MARGIN
    )
    assert (
        result.crossing_direction
        is PhysicalVisibilityCrossingDirection.NOT_VISIBLE_TO_VISIBLE
    )
    assert result.visibility_margin_residual_magnitude is not None
    assert result.visibility_margin_residual_magnitude <= 1.0e-8
    assert result.visibility_margin_bracket_jd_ut is not None
    assert (
        result.visibility_margin_bracket_jd_ut[0]
        <= result.event_jd_ut
        <= result.visibility_margin_bracket_jd_ut[1]
    )
    assert result.root_iterations is not None
    assert result.assessment_jd_ut == result.event_jd_ut
    assert result.observation_window is not None
    assert result.event_assessment is not None
    assert result.data_pack_receipt is _PACK_RECEIPT
    assert result.ephemeris_receipt is not None
    assert result.components[0].component_id == "test-component"
    assert result.solver_receipt.classified_day_count == 2
    assert result.solver_receipt.guard_day_count == 1
    assert tuple(
        (day_key, status)
        for day_key, status, _reason, _geometry
        in result.solver_receipt.classified_day_states
    ) == (
        (99, "does_not_qualify"),
        (100, "qualifies"),
    )
    assert (
        result.solver_receipt.crossing_completeness_state
        == "certified_lipschitz_zero_enclosure"
    )
    assert (
        result.sensitivity_receipt
        .data_pack_numerical_event_interval_jd_ut
        == pytest.approx((99.69, 99.71), abs=3.0e-6)
    )
    assert result.sensitivity_receipt.data_pack_numerical_reason is None
    assert not (
        result.sensitivity_receipt.probabilistic_confidence_claimed
    )
    assert len(load_calls) == 1


def test_visible_at_boundary_assigns_event_to_pack_altitude_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=(
            lambda jd_ut: (
                1.0 if _day_and_fraction(jd_ut)[0] == 100 else -1.0
            )
        ),
        target_domain=(0.25, 45.0),
    )
    result = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.event_jd_ut == pytest.approx(
        99.651326,
        abs=2.0e-6,
    )
    assert (
        result.event_time_semantics
        is PhysicalEventTimeSemantics.DATA_PACK_TARGET_ALTITUDE_FLOOR
    )
    assert (
        result.boundary_source
        is PhysicalVisibilityBoundarySource
        .TARGET_DATA_PACK_ALTITUDE_FLOOR
    )
    assert result.visibility_margin_residual_magnitude is None
    assert result.visibility_margin_bracket_jd_ut is None
    assert result.root_iterations is None
    assert result.assessment_jd_ut is not None
    assert result.assessment_jd_ut > result.event_jd_ut


def test_evening_last_setting_requires_following_nonqualifying_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_runtime(
        monkeypatch,
        geometry=_evening_geometry,
        margin_for=(
            lambda jd_ut: (
                1.0 if _day_and_fraction(jd_ut)[0] == 100 else -1.0
            )
        ),
    )
    result = physical_visibility_event(
        Body.SATURN,
        PhysicalVisibilityPhase.EVENING_LAST_SETTING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.observation_day_key == 100
    assert result.comparison_observation_day_key == 101
    assert result.event_jd_ut == pytest.approx(100.35, abs=2.0e-6)
    assert (
        result.crossing_direction
        is PhysicalVisibilityCrossingDirection.VISIBLE_TO_NOT_VISIBLE
    )
    assert result.solver_receipt.guard_day_count == 1


def test_morning_first_setting_selects_closing_margin_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def margin_for(jd_ut: float) -> float:
        day_key, fraction = _day_and_fraction(jd_ut)
        if day_key < 100:
            return -1.0
        return 0.18 - fraction

    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_setting_geometry,
        margin_for=margin_for,
    )
    result = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_SETTING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.observation_day_key == 100
    assert result.comparison_observation_day_key == 99
    assert result.event_jd_ut == pytest.approx(99.68, abs=2.0e-6)
    assert (
        result.crossing_direction
        is PhysicalVisibilityCrossingDirection.VISIBLE_TO_NOT_VISIBLE
    )
    assert result.boundary_role == "setting"


def test_evening_last_rising_selects_opening_margin_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def margin_for(jd_ut: float) -> float:
        day_key, fraction = _day_and_fraction(jd_ut)
        if day_key > 100:
            return -1.0
        return fraction - 0.82

    _install_synthetic_runtime(
        monkeypatch,
        geometry=_evening_rising_geometry,
        margin_for=margin_for,
    )
    result = physical_visibility_event(
        Body.JUPITER,
        PhysicalVisibilityPhase.EVENING_LAST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.observation_day_key == 100
    assert result.comparison_observation_day_key == 101
    assert result.event_jd_ut == pytest.approx(100.32, abs=2.0e-6)
    assert (
        result.crossing_direction
        is PhysicalVisibilityCrossingDirection.NOT_VISIBLE_TO_VISIBLE
    )
    assert result.boundary_role == "rising"


def test_evaluable_search_without_transition_returns_typed_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=lambda _jd_ut: -1.0,
    )
    result = physical_visibility_event(
        Body.JUPITER,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.NOT_FOUND
    assert (
        result.evidence_state
        is PhysicalVisibilityEvidenceState.EVALUATED_NO_EVENT
    )
    assert result.reason == "no_phase_transition_in_search_window"
    assert result.event_jd_ut is None


def test_repeated_public_event_search_is_structurally_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def margin_for(jd_ut: float) -> float:
        day_key, fraction = _day_and_fraction(jd_ut)
        return fraction - 0.20 if day_key == 100 else -1.0

    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=margin_for,
    )
    arguments = (
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
    )
    keywords = {
        "data_pack_config": VisibilityDataPackConfig("unused"),
        "policy": _policy(),
        "search_policy": _search_policy(),
    }

    first = physical_visibility_event(*arguments, **keywords)
    second = physical_visibility_event(*arguments, **keywords)

    assert first == second


def test_atmospheric_policy_change_shifts_event_without_confidence_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def margin_for_policy(
        jd_ut: float,
        policy: PhysicalVisibilityPolicy,
    ) -> float:
        day_key, fraction = _day_and_fraction(jd_ut)
        if day_key < 100:
            return -1.0
        return fraction - (0.19 + 0.1 * policy.atmosphere.aod550)

    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=lambda _jd_ut: 0.0,
        margin_for_policy=margin_for_policy,
    )
    low_aod_policy = replace(
        _policy(),
        atmosphere=PhysicalAtmosphereInput(aod550=0.1),
    )
    high_aod_policy = replace(
        _policy(),
        atmosphere=PhysicalAtmosphereInput(aod550=0.2),
    )

    low_aod = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=low_aod_policy,
        search_policy=_search_policy(),
    )
    high_aod = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=high_aod_policy,
        search_policy=_search_policy(),
    )

    assert low_aod.status is PhysicalVisibilityStatus.EVALUATED
    assert high_aod.status is PhysicalVisibilityStatus.EVALUATED
    assert high_aod.event_jd_ut - low_aod.event_jd_ut == pytest.approx(
        0.01,
        abs=3.0e-6,
    )
    assert not (
        high_aod.sensitivity_receipt.probabilistic_confidence_claimed
    )
    assert (
        high_aod.sensitivity_receipt.atmospheric_scenario_reason
        == "explicit_admitted_atmospheric_scenario_bounds_required"
    )


def test_missing_guard_day_geometry_blocks_first_day_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def geometry(
        target: str,
        jd_ut: float,
        lat: float,
        lon: float,
    ) -> tuple[float, float]:
        day_key, _fraction = _day_and_fraction(jd_ut)
        if target == Body.SUN and day_key == 99:
            return 180.0, -20.0
        return _morning_geometry(target, jd_ut, lat, lon)

    _install_synthetic_runtime(
        monkeypatch,
        geometry=geometry,
        margin_for=(
            lambda jd_ut: (
                1.0 if _day_and_fraction(jd_ut)[0] == 100 else -1.0
            )
        ),
    )
    result = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE
    assert result.reason == "phase_ownership_not_evaluable"
    assert result.event_jd_ut is None


def test_unadmitted_fixed_star_fails_before_pack_or_native_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        heliacal,
        "load_visibility_data_pack",
        lambda _config: pytest.fail("pack must not load"),
    )
    monkeypatch.setattr(
        heliacal,
        "visibility_event",
        lambda *_args, **_kwargs: pytest.fail(
            "legacy dispatcher must not run"
        ),
    )
    result = physical_visibility_event(
        "Betelgeuse",
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE
    assert result.reason == "target_not_admitted"
    assert result.data_pack_receipt is None
    assert result.ephemeris_receipt is None


@pytest.mark.parametrize("body", (Body.MERCURY, Body.VENUS))
def test_inner_planet_event_is_not_admitted_before_pack_load(
    monkeypatch: pytest.MonkeyPatch,
    body: str,
) -> None:
    monkeypatch.setattr(
        heliacal,
        "load_visibility_data_pack",
        lambda _config: pytest.fail("pack must not load"),
    )

    result = physical_visibility_event(
        body,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE
    assert result.reason == "body_phase_not_admitted"
    assert result.data_pack_receipt is None
    assert result.ephemeris_receipt is None


def test_sirius_event_uses_physical_path_without_legacy_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        heliacal,
        "visibility_event",
        lambda *_args, **_kwargs: pytest.fail(
            "legacy dispatcher must not run"
        ),
    )
    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=(
            lambda jd_ut: (
                1.0 if _day_and_fraction(jd_ut)[0] == 100 else -1.0
            )
        ),
        target_domain=(0.25, 45.0),
    )

    result = physical_visibility_event(
        "Sirius",
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.ephemeris_receipt is not None
    assert (
        result.ephemeris_receipt.provider_id
        == "moira_active_reader_and_sovereign_star_registry_v1"
    )


def test_missing_ephemeris_is_preserved_as_the_public_failure_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from moira.spk_reader import MissingKernelError

    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=lambda _jd_ut: -1.0,
    )

    def missing_geometry(*_args, **_kwargs):
        raise MissingKernelError("test kernel missing")

    monkeypatch.setattr(heliacal, "_true_horizontal", missing_geometry)
    result = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE
    assert result.reason == "ephemeris_dependency_missing"
    assert result.event_jd_ut is None
    assert result.ephemeris_receipt is not None
    assert result.solver_receipt.non_evaluable_day_states


def test_v1_2_manifest_domain_is_used_instead_of_phase0_outer_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def margin_for(jd_ut: float) -> float:
        day_key, fraction = _day_and_fraction(jd_ut)
        if day_key < 100:
            return -1.0
        return fraction - 0.20

    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=margin_for,
        solar_domain=(-9.0, 0.0),
        target_domain=(0.25, 45.0),
    )
    result = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.event_jd_ut == pytest.approx(99.7, abs=2.0e-6)
    assert result.observation_window is not None
    assert (
        result.observation_window.start_jd_ut
        > result.target_horizon_jd_ut
    )
    assert (
        result.observation_window.start_jd_ut
        == pytest.approx(99.675712, abs=2.0e-5)
    )


def test_pack_floor_replaces_unsupported_visual_horizon_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_runtime(
        monkeypatch,
        geometry=_morning_geometry,
        margin_for=(
            lambda jd_ut: (
                1.0 if _day_and_fraction(jd_ut)[0] == 100 else -1.0
            )
        ),
        solar_domain=(-18.0, 0.0),
        target_domain=(0.25, 45.0),
    )
    result = physical_visibility_event(
        Body.MARS,
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        99.5,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig("unused"),
        policy=_policy(),
        search_policy=_search_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.reason is None
    assert (
        result.boundary_source
        is PhysicalVisibilityBoundarySource
        .TARGET_DATA_PACK_ALTITUDE_FLOOR
    )
    assert result.horizon_receipt.target_boundary_narrowing_applied
    assert (
        result.horizon_receipt
        .data_pack_target_true_altitude_floor_deg
        == 0.25
    )

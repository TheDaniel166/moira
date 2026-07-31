from __future__ import annotations

import json
import math
import pickle
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from moira.constants import Body
from moira._visibility_lut import (
    VisibilityDataPack,
    VisibilityDataPackConfig,
    VisibilityDataPackDomain,
    VisibilityDataPackLoadError,
    VisibilityDataPackReceipt,
)
from moira._visibility_spectral import (
    DirectionalLuminance,
    ModeledDirectionalBackgroundComponent,
    PhysicalVisibilityCompositionError,
    TargetSpectralProfile,
    blackwell_crumey_full_range_threshold,
    cie_mes2_adaptation,
    compose_directional_background,
    condition_target,
    spectral_single_epoch_truth,
    sqm_directional_luminance,
)
from moira._visibility_targets import (
    parse_visibility_target_profiles,
)
from moira.heliacal import (
    PhysicalAtmosphereInput,
    PhysicalBackgroundComponentKind,
    PhysicalBackgroundScope,
    PhysicalBortleBackground,
    PhysicalDirectionalBackground,
    PhysicalModeledBackgroundComponent,
    PhysicalVisibilityEvidenceState,
    PhysicalVisibilityPolicy,
    PhysicalVisibilityStatus,
    physical_visibility_assessment,
)


_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "physical_visibility_phase2_equations_v1.json"
)
_SOURCE_SHA256 = "c" * 64
_UNIFORM_WEIGHTS = (1.0 / 400.0,) * 400


def _fixture() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _pack_target_profiles() -> tuple[Any, ...]:
    profiles: list[dict[str, Any]] = []
    for target_id in (
        Body.MERCURY,
        Body.VENUS,
        Body.MARS,
        Body.JUPITER,
        Body.SATURN,
    ):
        if target_id == Body.MERCURY:
            color_model: dict[str, Any] = {
                "model_id": "mallama_2017_gray_phase_shape_v1",
                "kind": "constant_color",
                "phase_angle_domain_deg": [2.0, 170.0],
                "limitations": [],
            }
        elif target_id == Body.SATURN:
            color_model = {
                "model_id": "mallama_2017_ubvri_ring_phase_color_v1",
                "kind": "saturn_ring_phase",
                "phase_angle_domain_deg": [0.0, 6.0],
                "ring_sub_latitude_domain_deg": [0.0, 27.0],
                "coefficients_by_band": [[0.0, 0.0, 0.0, 0.0]] * 5,
                "limitations": ["synthetic_test_profile"],
            }
        else:
            coefficient_count = (
                4 if target_id == Body.VENUS else 2
            )
            model_id, phase_domain = {
                Body.VENUS: (
                    "mallama_2017_ubvri_phase_color_v1",
                    [2.0, 165.0],
                ),
                Body.MARS: (
                    "mallama_2017_ubvri_illumination_color_v1",
                    [0.0, 50.0],
                ),
                Body.JUPITER: (
                    "mallama_2017_ubvri_geocentric_phase_color_v1",
                    [0.0, 12.0],
                ),
            }[target_id]
            color_model = {
                "model_id": model_id,
                "kind": "phase_polynomial",
                "phase_angle_domain_deg": phase_domain,
                "coefficients_by_band": (
                    [[0.0] * coefficient_count] * 5
                ),
                "limitations": [],
            }
        profiles.append(
            {
                "target_id": target_id,
                "spectral_profile_id": (
                    "source-owned-response-weights-v1"
                ),
                "spectral_source_ids": (
                    ["source-owned-spectrum-source-v1"]
                ),
                "spectral_source_receipt_sha256": _SOURCE_SHA256,
                "base_scotopic_to_photopic_ratio": 1.5,
                "base_photopic_extinction_weights": list(
                    _UNIFORM_WEIGHTS
                ),
                "base_scotopic_extinction_weights": list(
                    _UNIFORM_WEIGHTS
                ),
                "color_model": color_model,
            }
        )
    return parse_visibility_target_profiles(
        {
            "schema": (
                "moira.physical-heliacal-visibility-target-profiles/v1"
            ),
            "status": "complete_immutable_target_profiles",
            "catalog_id": (
                "payne_2026_mallama_2017_cie_target_profiles_v1"
            ),
            "color_warp_method": (
                "johnson_cousins_piecewise_linear_"
                "differential_magnitude_v1"
            ),
            "spectral_bins": {
                "coordinate": "bin_start_vacuum_nm",
                "start_nm": 380.0,
                "width_nm": 1.0,
                "count": 400,
            },
            "profiles": profiles,
        }
    )


def _pack(
    *,
    include_target_profiles: bool = True,
) -> VisibilityDataPack:
    return VisibilityDataPack(
        receipt=VisibilityDataPackReceipt(
            pack_id="moira-physical-heliacal-visibility",
            version="1.1.0",
            compatibility_id=(
                "moira-physical-heliacal-visibility-data-pack-v1.1"
            ),
            composite_model_id=(
                "clear_sky_naked_eye_point_source_v1"
            ),
            table_format_id=(
                "regular-grid-ieee754-binary32-le-v1"
            ),
            engine_contract_id=(
                "moira-physical-visibility-engine-contract-v1"
            ),
            engine_contract_version=1,
            manifest_sha256="a" * 64,
            generation_fingerprint="b" * 64,
            payload_sha256=(),
            source_artifact_spec_id="synthetic-test-pack",
            source_artifact_manifest_sha256="d" * 64,
            source_dataset_ids=(
                "CIE_photopic:10.25039/CIE.DS.dktna2s3",
                "CIE_scotopic:10.25039/CIE.DS.gr6w4b5g",
                "libRadtran:2.0.6",
                "REPTRAN:libradtran_reptran_2024_all",
            ),
            license="CC-BY-SA-4.0",
            notice_sha256="e" * 64,
        ),
        domain=VisibilityDataPackDomain(
            atmosphere_profile="us_standard",
            aerosol_profile="rural_summer",
            observer_altitude_m=0.0,
            surface_pressure_hpa=1013.25,
            aod550=0.1,
            angstrom_exponent=1.3,
            ozone_du=300.0,
            ground_albedo=0.2,
            solar_center_altitude_deg=(-9.0, 0.0),
            target_true_altitude_deg=(0.25, 45.0),
            relative_solar_azimuth_deg=(0.0, 180.0),
            refraction="disabled_true_geometric_line_of_sight",
            outside_domain="typed_not_evaluable",
            no_extrapolation=True,
        ),
        _solar_axis=(-9.0, 0.0),
        _target_radiance_axis=(0.25, 45.0),
        _azimuth_axis=(0.0, 180.0),
        _photopic_luminance=(0.3,) * 8,
        _scotopic_luminance=(0.54,) * 8,
        _photopic_rse=(0.01,) * 8,
        _scotopic_rse=(0.02,) * 8,
        _direct_target_axis=(0.25, 45.0),
        _spectral_bin_start_nm=tuple(
            float(value) for value in range(380, 780)
        ),
        _direct_extinction=(1.0,) * 400 + (3.0,) * 400,
        _photopic_error_max_mag=0.35,
        _photopic_error_p95_mag=0.28,
        _scotopic_error_max_mag=0.25,
        _scotopic_error_p95_mag=0.24,
        _direct_error_max_mag=0.02,
        _direct_error_p95_mag=0.003,
        _storage_error_max_mag=0.000001,
        _target_profiles=(
            _pack_target_profiles()
            if include_target_profiles
            else ()
        ),
    )


def _profile(
    *,
    magnitude: float = 2.0,
    sp_ratio: float = 1.5,
) -> TargetSpectralProfile:
    return TargetSpectralProfile(
        target_id="source-owned-test-target",
        top_of_atmosphere_visual_magnitude=magnitude,
        scotopic_to_photopic_ratio=sp_ratio,
        photopic_extinction_weights=_UNIFORM_WEIGHTS,
        scotopic_extinction_weights=_UNIFORM_WEIGHTS,
        photometry_model_id="source-owned-v-magnitude-v1",
        photometry_source_ids=("source-owned-photometry-source-v1",),
        spectral_profile_id="source-owned-response-weights-v1",
        spectral_source_ids=("source-owned-spectrum-source-v1",),
        spectral_source_receipt_sha256=_SOURCE_SHA256,
    )


def _photometry_context(
    *,
    magnitude: float = 2.0,
    phase_angle_deg: float = 20.0,
    saturn_ring_latitude_deg: float | None = 5.0,
    geometry_valid: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        apparent_magnitude=magnitude,
        phase_angle_deg=phase_angle_deg,
        saturn_effective_ring_sub_latitude_deg=(
            saturn_ring_latitude_deg
        ),
        geometry_valid=geometry_valid,
    )


def _public_dark_anchor() -> PhysicalDirectionalBackground:
    return PhysicalDirectionalBackground(
        photopic_luminance_cd_m2=0.0002,
        scotopic_luminance_cd_m2=0.00036,
        scope=PhysicalBackgroundScope.DARK_SKY_ANCHOR,
        component_ids=(
            "airglow",
            "zodiacal_light",
            "integrated_starlight",
        ),
        source_id="measured-dark-sky-anchor-v1",
        source_receipt_sha256=_SOURCE_SHA256,
        method_id="measured-directional-luminance-v1",
    )


def _public_measured_total() -> PhysicalDirectionalBackground:
    return PhysicalDirectionalBackground(
        photopic_luminance_cd_m2=0.3,
        scotopic_luminance_cd_m2=0.54,
        scope=PhysicalBackgroundScope.TOTAL_BACKGROUND,
        component_ids=("measured_total_background",),
        source_id="measured-total-v1",
        source_receipt_sha256=_SOURCE_SHA256,
        method_id="measured-directional-luminance-v1",
    )


def _patch_public_assessment_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    target_altitude_deg: float = 5.0,
    solar_altitude_deg: float = -6.0,
) -> None:
    monkeypatch.setattr(
        "moira.heliacal.load_visibility_data_pack",
        lambda _config: _pack(),
    )

    def horizontal(
        body: str,
        _jd_ut: float,
        _lat: float,
        _lon: float,
    ) -> tuple[float, float]:
        if body == Body.SUN:
            return (40.0, solar_altitude_deg)
        return (100.0, target_altitude_deg)

    monkeypatch.setattr("moira.heliacal._true_horizontal", horizontal)
    monkeypatch.setattr(
        "moira.heliacal.apply_refraction",
        lambda altitude, **_kwargs: altitude,
    )
    monkeypatch.setattr(
        "moira.heliacal._physical_target_photometry_context",
        lambda _body, _jd_ut: _photometry_context(),
    )


def _physical_policy(
    *,
    background: (
        PhysicalDirectionalBackground
        | PhysicalBortleBackground
        | None
    ) = None,
    atmosphere: PhysicalAtmosphereInput | None = None,
) -> PhysicalVisibilityPolicy:
    return PhysicalVisibilityPolicy(
        background=(
            _public_dark_anchor()
            if background is None
            else background
        ),
        atmosphere=(
            PhysicalAtmosphereInput()
            if atmosphere is None
            else atmosphere
        ),
    )


def _dark_anchor(
    *,
    component_ids: tuple[str, ...] = (
        "airglow",
        "zodiacal_light",
        "integrated_starlight",
    ),
) -> DirectionalLuminance:
    return DirectionalLuminance(
        photopic_luminance_cd_m2=0.0002,
        scotopic_luminance_cd_m2=0.00036,
        scope="dark_sky_anchor",
        component_ids=component_ids,
        source_id="measured-dark-sky-anchor-v1",
        source_receipt_sha256=_SOURCE_SHA256,
        method_id="measured-directional-luminance-v1",
    )


def _measured_total() -> DirectionalLuminance:
    return DirectionalLuminance(
        photopic_luminance_cd_m2=0.3,
        scotopic_luminance_cd_m2=0.54,
        scope="total_background",
        component_ids=("measured_total_background",),
        source_id="measured-total-v1",
        source_receipt_sha256=_SOURCE_SHA256,
        method_id="measured-directional-luminance-v1",
    )


def _modeled_component(
    component_id: str = "airglow",
) -> ModeledDirectionalBackgroundComponent:
    return ModeledDirectionalBackgroundComponent(
        component_id=component_id,
        photopic_luminance_cd_m2=1.0e-5,
        scotopic_luminance_cd_m2=1.8e-5,
        model_id=f"test-{component_id}-model-v1",
        source_ids=(f"test-{component_id}-source",),
        source_receipt_sha256=_SOURCE_SHA256,
        spatial_applicability_id="test-site",
        temporal_applicability_id="test-epoch",
        direction_receipt_id="test-direction",
        validity_domain_id=f"test-{component_id}-domain-v1",
        uncertainty_authority_id="test-uncertainty-not-propagated",
    )


def _public_modeled_component(
    kind: PhysicalBackgroundComponentKind = (
        PhysicalBackgroundComponentKind.AIRGLOW
    ),
) -> PhysicalModeledBackgroundComponent:
    return PhysicalModeledBackgroundComponent(
        component_kind=kind,
        photopic_luminance_cd_m2=1.0e-5,
        scotopic_luminance_cd_m2=1.8e-5,
        model_id=f"test-{kind.value}-model-v1",
        source_ids=(f"test-{kind.value}-source",),
        source_receipt_sha256=_SOURCE_SHA256,
        spatial_applicability_id="test-site",
        temporal_applicability_id="test-epoch",
        direction_receipt_id="test-direction",
        validity_domain_id=f"test-{kind.value}-domain-v1",
        uncertainty_authority_id="test-uncertainty-not-propagated",
    )


def test_equation_fixture_binds_protocol_and_exact_sources() -> None:
    fixture = _fixture()

    assert fixture["status"] == "source_owned_phase2_admission_fixture"
    assert (
        fixture["observer_protocol"]["id"]
        == "known_location_directed_averted_observation_v1"
    )
    assert (
        fixture["sources"]["crumey_2014"]["sha256"]
        == "fa6ef183f9402be4d321bff5fa2c112510f89ca683b534e33c63fdb6538e50a4"
    )
    assert fixture["sources"]["crumey_2014"]["equations"] == [28, 34]
    assert (
        fixture["sources"]["cie_tn_007_2017"]["sections"]
        == ["5.1", "6"]
    )


@pytest.mark.parametrize("case_index", (0, 1))
def test_cie_mes2_matches_official_tn007_examples(
    case_index: int,
) -> None:
    case = _fixture()["cie_mes2"]["official_tn_007_examples"][
        case_index
    ]
    photopic = case["photopic_luminance_cd_m2"]

    state = cie_mes2_adaptation(
        photopic,
        photopic * case["scotopic_to_photopic_ratio"],
    )

    assert round(state.adaptation_coefficient, 3) == (
        case["expected_adaptation_coefficient_3dp"]
    )
    assert round(state.mesopic_luminance_cd_m2, 3) == (
        case["expected_mesopic_luminance_cd_m2_3dp"]
    )
    assert state.fixed_point_residual <= 1.0e-12
    assert state.weighting_state == "mesopic"


def test_cie_mes2_closes_at_scotopic_and_photopic_limits() -> None:
    scotopic = cie_mes2_adaptation(0.003, 0.004)
    photopic = cie_mes2_adaptation(6.0, 7.0)

    assert scotopic.adaptation_coefficient == 0.0
    assert scotopic.mesopic_luminance_cd_m2 == 0.004
    assert scotopic.weighting_state == "scotopic"
    assert photopic.adaptation_coefficient == 1.0
    assert photopic.mesopic_luminance_cd_m2 == 6.0
    assert photopic.weighting_state == "photopic"


@pytest.mark.parametrize(
    "luminance",
    (
        math.nextafter(0.005, math.inf),
        math.nextafter(5.0, -math.inf),
    ),
)
def test_cie_mes2_contains_published_coefficient_rounding_at_limits(
    luminance: float,
) -> None:
    state = cie_mes2_adaptation(luminance, luminance)

    assert 0.0 <= state.adaptation_coefficient <= 1.0
    assert state.mesopic_luminance_cd_m2 == pytest.approx(luminance)


def test_full_range_threshold_matches_tousey_koomen_table_i() -> None:
    truth = _fixture()["blackwell_crumey_full_range"][
        "tousey_koomen_table_i"
    ]
    conversion = truth["si_conversion_factor"]
    residuals = []

    for case in truth["cases"]:
        background = (
            10.0 ** case["log10_background_source_unit"]
            * conversion
        )
        threshold = blackwell_crumey_full_range_threshold(background)
        predicted_log_foot_candle = math.log10(
            threshold.threshold_illuminance_lux / conversion
        )
        residuals.append(
            abs(
                predicted_log_foot_candle
                - case["log10_threshold_source_unit"]
            )
        )

    assert max(residuals) <= (
        truth["maximum_accepted_absolute_log10_threshold_residual"]
    )


def test_full_range_threshold_is_monotonic_across_fixture_cases() -> None:
    truth = _fixture()["blackwell_crumey_full_range"][
        "tousey_koomen_table_i"
    ]
    conversion = truth["si_conversion_factor"]
    backgrounds = sorted(
        10.0 ** case["log10_background_source_unit"]
        * conversion
        for case in truth["cases"]
    )

    thresholds = [
        blackwell_crumey_full_range_threshold(background)
        for background in backgrounds
    ]

    assert all(
        right.threshold_illuminance_lux
        > left.threshold_illuminance_lux
        for left, right in zip(thresholds, thresholds[1:])
    )
    assert all(
        right.limiting_magnitude < left.limiting_magnitude
        for left, right in zip(thresholds, thresholds[1:])
    )


@pytest.mark.parametrize("background", (3.425e-5, 3426.1))
def test_full_range_threshold_fails_closed_outside_source_domain(
    background: float,
) -> None:
    with pytest.raises(PhysicalVisibilityCompositionError) as exc_info:
        blackwell_crumey_full_range_threshold(background)

    assert exc_info.value.reason == "criterion_out_of_domain"


def test_qualified_sqm_transform_discloses_every_required_receipt() -> None:
    result = sqm_directional_luminance(
        21.83,
        scotopic_to_photopic_ratio=1.8,
        scope="dark_sky_anchor",
        component_ids=("measured_dark_sky",),
        measurement_source_id="sqm-observation-1",
        measurement_receipt_sha256=_SOURCE_SHA256,
        device_bandpass_id="unihedron-sqm-l-v1",
        pointing_receipt_id="az180-alt90",
        temporal_applicability_id="jd2460000.5",
        spectral_ratio_source_id="measured-sp-ratio-1",
    )

    expected_photopic = 10.0 ** ((12.58 - 21.83) / 2.5)
    assert result.photopic_luminance_cd_m2 == pytest.approx(
        expected_photopic
    )
    assert result.scotopic_luminance_cd_m2 == pytest.approx(
        expected_photopic * 1.8
    )
    assert "unihedron-sqm-l-v1" in result.method_id
    assert "measured-sp-ratio-1" in result.method_id


def test_unqualified_sqm_scalar_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires bandpass"):
        sqm_directional_luminance(
            21.83,
            scotopic_to_photopic_ratio=1.8,
            scope="dark_sky_anchor",
            component_ids=("measured_dark_sky",),
            measurement_source_id="sqm-observation-1",
            measurement_receipt_sha256=_SOURCE_SHA256,
            device_bandpass_id="",
            pointing_receipt_id="az180-alt90",
            temporal_applicability_id="jd2460000.5",
            spectral_ratio_source_id="measured-sp-ratio-1",
        )


def test_measured_total_background_has_absolute_precedence() -> None:
    measured = _measured_total()

    composition = compose_directional_background(
        measured_total=measured
    )

    assert (
        composition.authority_id
        == "measured_directional_photopic_scotopic_v1"
    )
    assert composition.modeled_twilight is None
    assert composition.component_ids == ("measured_total_background",)


def test_measured_total_cannot_be_combined_with_modeled_components() -> None:
    twilight = _pack().interpolate_twilight_luminance(
        solar_center_altitude_deg=-6.0,
        target_true_altitude_deg=5.0,
        relative_solar_azimuth_deg=90.0,
    )

    with pytest.raises(PhysicalVisibilityCompositionError) as exc_info:
        compose_directional_background(
            measured_total=_measured_total(),
            modeled_twilight=twilight,
            dark_sky_anchor=_dark_anchor(),
        )

    assert exc_info.value.reason == "background_components_conflict"


def test_modeled_twilight_requires_nonoverlapping_dark_sky_anchor() -> None:
    twilight = _pack().interpolate_twilight_luminance(
        solar_center_altitude_deg=-6.0,
        target_true_altitude_deg=5.0,
        relative_solar_azimuth_deg=90.0,
    )

    with pytest.raises(PhysicalVisibilityCompositionError) as missing:
        compose_directional_background(modeled_twilight=twilight)
    with pytest.raises(PhysicalVisibilityCompositionError) as overlap:
        compose_directional_background(
            modeled_twilight=twilight,
            dark_sky_anchor=_dark_anchor(
                component_ids=("solar_twilight", "airglow")
            ),
        )

    assert missing.value.reason == "background_input_incomplete"
    assert overlap.value.reason == "background_components_conflict"


def test_modeled_twilight_and_dark_anchor_compose_once() -> None:
    twilight = _pack().interpolate_twilight_luminance(
        solar_center_altitude_deg=-6.0,
        target_true_altitude_deg=5.0,
        relative_solar_azimuth_deg=90.0,
    )

    composition = compose_directional_background(
        modeled_twilight=twilight,
        dark_sky_anchor=_dark_anchor(),
    )

    assert composition.photopic_luminance_cd_m2 == pytest.approx(
        0.3002
    )
    assert composition.scotopic_luminance_cd_m2 == pytest.approx(
        0.54036
    )
    assert composition.component_ids.count("solar_twilight") == 1
    assert (
        composition.photopic_solver_relative_standard_error_bound
        == 0.01
    )


def test_separate_modeled_background_components_require_complete_inventory(
) -> None:
    twilight = _pack().interpolate_twilight_luminance(
        solar_center_altitude_deg=-6.0,
        target_true_altitude_deg=5.0,
        relative_solar_azimuth_deg=90.0,
    )
    anchor = _dark_anchor(
        component_ids=("zodiacal_light", "integrated_starlight")
    )

    with pytest.raises(PhysicalVisibilityCompositionError) as exc_info:
        compose_directional_background(
            modeled_twilight=twilight,
            dark_sky_anchor=anchor,
            modeled_components=(_modeled_component(),),
        )

    assert (
        exc_info.value.reason
        == "background_component_inventory_incomplete"
    )


def test_separate_modeled_background_component_cannot_overlap_anchor(
) -> None:
    twilight = _pack().interpolate_twilight_luminance(
        solar_center_altitude_deg=-6.0,
        target_true_altitude_deg=5.0,
        relative_solar_azimuth_deg=90.0,
    )
    anchor = replace(
        _dark_anchor(),
        component_inventory_complete=True,
    )

    with pytest.raises(PhysicalVisibilityCompositionError) as exc_info:
        compose_directional_background(
            modeled_twilight=twilight,
            dark_sky_anchor=anchor,
            modeled_components=(_modeled_component(),),
        )

    assert exc_info.value.reason == "background_components_conflict"


def test_separate_modeled_background_component_kind_cannot_repeat() -> None:
    twilight = _pack().interpolate_twilight_luminance(
        solar_center_altitude_deg=-6.0,
        target_true_altitude_deg=5.0,
        relative_solar_azimuth_deg=90.0,
    )
    anchor = replace(
        _dark_anchor(component_ids=("residual_dark_sky",)),
        component_inventory_complete=True,
    )

    with pytest.raises(PhysicalVisibilityCompositionError) as exc_info:
        compose_directional_background(
            modeled_twilight=twilight,
            dark_sky_anchor=anchor,
            modeled_components=(
                _modeled_component(),
                _modeled_component(),
            ),
        )

    assert exc_info.value.reason == "background_components_conflict"


def test_separate_modeled_components_are_sorted_summed_and_receipted(
) -> None:
    twilight = _pack().interpolate_twilight_luminance(
        solar_center_altitude_deg=-6.0,
        target_true_altitude_deg=5.0,
        relative_solar_azimuth_deg=90.0,
    )
    anchor = replace(
        _dark_anchor(component_ids=("residual_dark_sky",)),
        component_inventory_complete=True,
    )
    airglow = _modeled_component("airglow")
    zodiacal = _modeled_component("zodiacal_light")

    composition = compose_directional_background(
        modeled_twilight=twilight,
        dark_sky_anchor=anchor,
        modeled_components=(zodiacal, airglow),
    )

    assert composition.authority_id == (
        "modeled_twilight_plus_declared_background_components_v1"
    )
    assert composition.photopic_luminance_cd_m2 == pytest.approx(
        0.30022
    )
    assert composition.scotopic_luminance_cd_m2 == pytest.approx(
        0.540396
    )
    assert composition.component_ids == (
        "solar_twilight",
        "residual_dark_sky",
        "airglow",
        "zodiacal_light",
    )
    assert tuple(
        component.component_id
        for component in composition.modeled_components
    ) == ("airglow", "zodiacal_light")


def test_measured_total_rejects_separate_modeled_background_component(
) -> None:
    with pytest.raises(PhysicalVisibilityCompositionError) as exc_info:
        compose_directional_background(
            measured_total=_measured_total(),
            modeled_components=(_modeled_component(),),
        )

    assert exc_info.value.reason == "background_components_conflict"


def test_target_profile_rejects_silent_weight_normalization() -> None:
    with pytest.raises(ValueError, match="sum to exactly one"):
        TargetSpectralProfile(
            target_id="bad-target",
            top_of_atmosphere_visual_magnitude=2.0,
            scotopic_to_photopic_ratio=1.5,
            photopic_extinction_weights=(0.0,) * 400,
            scotopic_extinction_weights=_UNIFORM_WEIGHTS,
            photometry_model_id="source-owned-v-magnitude-v1",
            photometry_source_ids=("source-owned-photometry-source-v1",),
            spectral_profile_id="bad-weights-v1",
            spectral_source_ids=("source-owned-spectrum-source-v1",),
            spectral_source_receipt_sha256=_SOURCE_SHA256,
        )


def test_target_conditioning_uses_both_response_weighted_paths() -> None:
    direct = _pack().interpolate_direct_extinction_spectrum(
        target_true_altitude_deg=0.25
    )
    adaptation = cie_mes2_adaptation(0.3, 0.54)

    target = condition_target(
        _profile(),
        direct,
        adaptation.adaptation_coefficient,
    )

    expected_transmission = 10.0 ** (-0.4)
    assert target.photopic_transmission == pytest.approx(
        expected_transmission
    )
    assert target.scotopic_transmission == pytest.approx(
        expected_transmission
    )
    assert target.conditioned_mesopic_illuminance_lux > 0.0
    assert target.direct_interpolation_maximum_error_mag == 0.02


def test_single_epoch_modeled_truth_returns_complete_component_receipts() -> None:
    result = spectral_single_epoch_truth(
        _pack(),
        _profile(magnitude=2.0),
        target_true_altitude_deg=0.25,
        solar_center_altitude_deg=-6.0,
        relative_solar_azimuth_deg=90.0,
        dark_sky_anchor=_dark_anchor(),
    )

    component_ids = {
        receipt.component_id for receipt in result.components
    }
    assert result.composite_model_id == (
        "clear_sky_naked_eye_point_source_v1"
    )
    assert result.observer_protocol_id == (
        "known_location_directed_averted_observation_v1"
    )
    assert result.data_pack_receipt.manifest_sha256 == "a" * 64
    assert "libradtran_2_0_6_mystic_spherical_v1" in component_ids
    assert "cie_mes2_2010_v1" in component_ids
    assert (
        "blackwell_crumey_full_range_point_source_v1"
        in component_ids
    )
    assert result.visible == (
        result.visibility_margin_magnitude >= 0.0
    )


def test_modeled_truth_propagates_pack_maximum_errors_to_margin() -> None:
    result = spectral_single_epoch_truth(
        _pack(),
        _profile(magnitude=2.0),
        target_true_altitude_deg=0.25,
        solar_center_altitude_deg=-6.0,
        relative_solar_azimuth_deg=90.0,
        dark_sky_anchor=_dark_anchor(),
    )
    budget = result.error_budget

    assert (
        budget.visibility_margin_envelope_lower_magnitude
        <= result.visibility_margin_magnitude
        <= budget.visibility_margin_envelope_upper_magnitude
    )
    assert (
        budget.background_mesopic_luminance_envelope_lower_cd_m2
        < result.adaptation.mesopic_luminance_cd_m2
        < budget.background_mesopic_luminance_envelope_upper_cd_m2
    )
    assert (
        budget.conditioned_target_magnitude_maximum_pack_error
        == pytest.approx(0.020001)
    )
    assert budget.solver_relative_standard_error_multiplier == 1.0
    assert (
        "pack_twilight_solver_relative_standard_error"
        in budget.included_error_sources
    )
    assert (
        "dark_sky_anchor_input_uncertainty"
        in budget.unquantified_error_sources
    )


def test_zero_pack_errors_collapse_and_larger_errors_widen_margin() -> None:
    zero_error_pack = replace(
        _pack(),
        _photopic_rse=(0.0,) * 8,
        _scotopic_rse=(0.0,) * 8,
        _photopic_error_max_mag=0.0,
        _scotopic_error_max_mag=0.0,
        _direct_error_max_mag=0.0,
        _storage_error_max_mag=0.0,
    )
    zero = spectral_single_epoch_truth(
        zero_error_pack,
        _profile(),
        target_true_altitude_deg=0.25,
        solar_center_altitude_deg=-6.0,
        relative_solar_azimuth_deg=90.0,
        dark_sky_anchor=_dark_anchor(),
    )
    bounded = spectral_single_epoch_truth(
        _pack(),
        _profile(),
        target_true_altitude_deg=0.25,
        solar_center_altitude_deg=-6.0,
        relative_solar_azimuth_deg=90.0,
        dark_sky_anchor=_dark_anchor(),
    )

    assert zero.error_budget.visibility_margin_envelope_lower_magnitude == (
        pytest.approx(zero.visibility_margin_magnitude)
    )
    assert zero.error_budget.visibility_margin_envelope_upper_magnitude == (
        pytest.approx(zero.visibility_margin_magnitude)
    )
    assert (
        zero.error_budget
        .visibility_margin_envelope_maximum_deviation_magnitude
        == pytest.approx(0.0)
    )
    zero_width = (
        zero.error_budget.visibility_margin_envelope_upper_magnitude
        - zero.error_budget.visibility_margin_envelope_lower_magnitude
    )
    bounded_width = (
        bounded.error_budget.visibility_margin_envelope_upper_magnitude
        - bounded.error_budget.visibility_margin_envelope_lower_magnitude
    )
    assert bounded_width > zero_width


def test_measured_total_error_budget_does_not_invent_measurement_error() -> None:
    result = spectral_single_epoch_truth(
        _pack(),
        _profile(),
        target_true_altitude_deg=0.25,
        measured_total_background=_measured_total(),
    )
    budget = result.error_budget

    assert budget.background_error_authority == (
        "caller_measured_total_background_no_pack_error_envelope"
    )
    assert (
        budget.background_mesopic_luminance_envelope_lower_cd_m2
        == pytest.approx(result.adaptation.mesopic_luminance_cd_m2)
    )
    assert (
        budget.background_mesopic_luminance_envelope_upper_cd_m2
        == pytest.approx(result.adaptation.mesopic_luminance_cd_m2)
    )
    assert budget.solver_relative_standard_error_multiplier is None
    assert (
        "pack_twilight_interpolation_maximum_error"
        not in budget.included_error_sources
    )
    assert (
        "measured_total_background_input_uncertainty"
        in budget.unquantified_error_sources
    )
    assert (
        budget.visibility_margin_envelope_upper_magnitude
        - budget.visibility_margin_envelope_lower_magnitude
        == pytest.approx(
            2.0 * budget.conditioned_target_magnitude_maximum_pack_error
        )
    )


def test_margin_crossing_pack_error_is_typed_indeterminate() -> None:
    baseline = spectral_single_epoch_truth(
        _pack(),
        _profile(magnitude=2.0),
        target_true_altitude_deg=0.25,
        solar_center_altitude_deg=-6.0,
        relative_solar_azimuth_deg=90.0,
        dark_sky_anchor=_dark_anchor(),
    )
    boundary = spectral_single_epoch_truth(
        _pack(),
        _profile(
            magnitude=2.0 + baseline.visibility_margin_magnitude
        ),
        target_true_altitude_deg=0.25,
        solar_center_altitude_deg=-6.0,
        relative_solar_azimuth_deg=90.0,
        dark_sky_anchor=_dark_anchor(),
    )

    assert (
        boundary.error_budget
        .visibility_classification_within_data_pack_envelope
        == "indeterminate"
    )
    assert (
        boundary.error_budget.visibility_margin_envelope_lower_magnitude
        < 0.0
        < boundary.error_budget.visibility_margin_envelope_upper_magnitude
    )


def test_measured_total_route_does_not_require_twilight_geometry() -> None:
    result = spectral_single_epoch_truth(
        _pack(),
        _profile(),
        target_true_altitude_deg=0.25,
        measured_total_background=_measured_total(),
    )

    assert (
        result.background.authority_id
        == "measured_directional_photopic_scotopic_v1"
    )
    assert result.background.modeled_twilight is None


def test_measured_total_route_rejects_latent_modeled_inputs() -> None:
    with pytest.raises(PhysicalVisibilityCompositionError) as exc_info:
        spectral_single_epoch_truth(
            _pack(),
            _profile(),
            target_true_altitude_deg=0.25,
            measured_total_background=_measured_total(),
            solar_center_altitude_deg=-20.0,
        )

    assert exc_info.value.reason == "background_components_conflict"


def test_public_assessment_returns_evaluated_truth_and_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert (
        result.evidence_state
        is PhysicalVisibilityEvidenceState.EVALUATED_CLEAR_SKY
    )
    assert result.reason is None
    assert result.data_pack_receipt is not None
    assert result.data_pack_receipt.manifest_sha256 == "a" * 64
    assert result.atmosphere_receipt.within_data_pack_domain
    assert result.validity_domain_receipt is not None
    assert result.validity_domain_receipt.within_domain
    assert result.background_receipt is not None
    assert (
        result.background_receipt
        .photopic_interpolation_p95_error_mag
        == 0.28
    )
    assert result.background_receipt.storage_maximum_error_mag == (
        0.000001
    )
    assert result.target_receipt is not None
    assert result.target_receipt.photometry_source_ids == (
        "Mallama_Hilton:2018",
        "Astronomical_Almanac:planetary_magnitude_models",
    )
    assert result.target_receipt.spectral_source_ids == (
        "source-owned-spectrum-source-v1",
    )
    assert dict(
        result.target_receipt.spectral_model_details
    )["color_model_id"] == "mallama_2017_ubvri_phase_color_v1"
    assert result.threshold_receipt is not None
    assert result.error_budget_receipt is not None
    assert (
        result.error_budget_receipt
        .visibility_margin_envelope_lower_magnitude
        <= result.visibility_margin_magnitude
        <= result.error_budget_receipt
        .visibility_margin_envelope_upper_magnitude
    )
    assert result.visible == (
        result.visibility_margin_magnitude is not None
        and result.visibility_margin_magnitude >= 0.0
    )
    assert result.observable == result.visible
    assert {
        receipt.role for receipt in result.components
    } == {
        "directional_atmosphere",
        "spectral_response",
        "point_source_detection",
        "observer_protocol",
        "background_authority",
        "target_photometry",
        "target_spectral_profile",
        "numerical_error_propagation",
    }
    target_photometry = next(
        receipt
        for receipt in result.components
        if receipt.role == "target_photometry"
    )
    assert _SOURCE_SHA256 not in target_photometry.source_ids


def test_public_assessment_measured_total_ignores_twilight_grid_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(
        monkeypatch,
        solar_altitude_deg=-20.0,
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(
            background=_public_measured_total(),
        ),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.background_receipt is not None
    assert result.background_receipt.authority_id == (
        "measured_directional_photopic_scotopic_v1"
    )
    assert result.validity_domain_receipt is not None
    assert (
        result.validity_domain_receipt
        .queried_solar_center_altitude_deg
        is None
    )
    assert result.validity_domain_receipt.within_domain


def test_public_assessment_missing_pack_owned_profile_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    monkeypatch.setattr(
        "moira.heliacal.load_visibility_data_pack",
        lambda _config: _pack(include_target_profiles=False),
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE
    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY
    )
    assert result.reason == "target_spectral_profile_missing"
    assert result.data_pack_receipt is not None
    assert result.visible is None


def test_public_assessment_has_no_caller_profile_trust_surface() -> None:
    with pytest.raises(TypeError, match="target_profile"):
        physical_visibility_assessment(
            Body.VENUS,
            2451545.0,
            0.0,
            0.0,
            data_pack_config=VisibilityDataPackConfig(
                directory="unused"
            ),
            target_profile=object(),  # type: ignore[call-arg]
            policy=_physical_policy(),
        )


@pytest.mark.parametrize(
    ("body", "reason"),
    (
        (Body.MOON, "target_not_admitted"),
        (Body.URANUS, "target_not_admitted"),
    ),
)
def test_public_assessment_rejects_unadmitted_targets_without_pack_load(
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    reason: str,
) -> None:
    monkeypatch.setattr(
        "moira.heliacal.load_visibility_data_pack",
        lambda _config: pytest.fail("unadmitted target loaded the pack"),
    )

    result = physical_visibility_assessment(
        body,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE
    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.NOT_APPLICABLE
    )
    assert result.reason == reason


def test_public_assessment_reports_pack_load_failure_without_path_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_load(
        _config: VisibilityDataPackConfig,
    ) -> VisibilityDataPack:
        raise VisibilityDataPackLoadError(
            "visibility_data_pack_missing",
            r"C:\secret\deployment\pack is missing",
        )

    monkeypatch.setattr(
        "moira.heliacal.load_visibility_data_pack",
        fail_load,
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.reason == "visibility_data_pack_missing"
    assert result.data_pack_receipt is None
    assert "secret" not in repr(result)


def test_public_assessment_rejects_atmosphere_outside_exact_pack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(
            atmosphere=PhysicalAtmosphereInput(aod550=0.2),
        ),
    )

    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN
    )
    assert result.reason == "atmosphere_input_out_of_domain"
    assert not result.atmosphere_receipt.within_data_pack_domain


def test_public_assessment_rejects_target_outside_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(
        monkeypatch,
        target_altitude_deg=50.0,
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN
    )
    assert result.reason == "target_altitude_out_of_domain"
    assert result.validity_domain_receipt is not None
    assert not result.validity_domain_receipt.within_domain


def test_public_assessment_rejects_modeled_twilight_below_pack_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(
        monkeypatch,
        solar_altitude_deg=-10.0,
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN
    )
    assert result.reason == (
        "solar_twilight_below_data_pack_domain"
    )
    assert result.validity_domain_receipt is not None
    assert not result.validity_domain_receipt.within_domain


def test_public_assessment_below_local_horizon_is_not_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(
        monkeypatch,
        target_altitude_deg=-1.0,
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.NOT_APPLICABLE
    )
    assert result.reason == "target_below_local_horizon"
    assert result.geometrically_visible is False
    assert result.observable is False
    assert result.visible is None


def test_public_assessment_requires_one_background_authority() -> None:
    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=PhysicalVisibilityPolicy(),
    )

    assert result.reason == "background_input_incomplete"
    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY
    )


def test_public_assessment_rejects_policy_config_identity_conflict() -> None:
    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(
            directory="unused",
            expected_manifest_sha256="a" * 64,
        ),
        policy=PhysicalVisibilityPolicy(
            background=_public_dark_anchor(),
            expected_manifest_sha256="b" * 64,
        ),
    )

    assert result.reason == "visibility_data_pack_incompatible"
    assert result.data_pack_receipt is None


def test_public_assessment_enforces_policy_manifest_after_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=PhysicalVisibilityPolicy(
            background=_public_dark_anchor(),
            expected_manifest_sha256="b" * 64,
        ),
    )

    assert result.reason == "visibility_data_pack_checksum_mismatch"
    assert result.data_pack_receipt is not None
    assert result.data_pack_receipt.manifest_sha256 == "a" * 64


def test_public_assessment_rejects_dark_anchor_twilight_double_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    duplicate_twilight = PhysicalDirectionalBackground(
        photopic_luminance_cd_m2=0.1,
        scotopic_luminance_cd_m2=0.18,
        scope=PhysicalBackgroundScope.DARK_SKY_ANCHOR,
        component_ids=("solar_twilight",),
        source_id="invalid-duplicate-twilight",
        source_receipt_sha256=_SOURCE_SHA256,
        method_id="invalid-test-input",
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=PhysicalVisibilityPolicy(
            background=duplicate_twilight,
        ),
    )

    assert result.reason == "background_components_conflict"
    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE


def test_public_assessment_rejects_modeled_component_with_measured_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=PhysicalVisibilityPolicy(
            background=_public_measured_total(),
            modeled_background_components=(
                _public_modeled_component(),
            ),
        ),
    )

    assert result.reason == "background_components_conflict"
    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE
    assert any(
        receipt.role == "modeled_background_component"
        for receipt in result.components
    )


def test_public_assessment_requires_complete_anchor_inventory_for_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    anchor = replace(
        _public_dark_anchor(),
        component_ids=("zodiacal_light", "integrated_starlight"),
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=PhysicalVisibilityPolicy(
            background=anchor,
            modeled_background_components=(
                _public_modeled_component(),
            ),
        ),
    )

    assert result.reason == "background_component_inventory_incomplete"
    assert result.status is PhysicalVisibilityStatus.NOT_EVALUABLE


def test_public_assessment_receipts_separate_modeled_component(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    anchor = replace(
        _public_dark_anchor(),
        component_ids=("zodiacal_light", "integrated_starlight"),
        component_inventory_complete=True,
    )
    airglow = _public_modeled_component()

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=PhysicalVisibilityPolicy(
            background=anchor,
            modeled_background_components=(airglow,),
        ),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.background_receipt is not None
    assert result.background_receipt.authority_id == (
        "modeled_twilight_plus_declared_background_components_v1"
    )
    assert result.background_receipt.component_inventory_complete
    assert result.background_receipt.modeled_component_count == 1
    component_receipt = next(
        receipt
        for receipt in result.components
        if receipt.role == "modeled_background_component"
    )
    details = dict(component_receipt.details)
    assert component_receipt.component_id == airglow.model_id
    assert details["background_component_id"] == "airglow"
    assert details["spatial_applicability_id"] == "test-site"
    assert (
        details["uncertainty_authority_id"]
        == "test-uncertainty-not-propagated"
    )
    assert (
        "modeled_background_component:airglow:input_uncertainty"
        in result.error_budget_receipt.unquantified_error_sources
    )


def test_physical_observer_field_factor_is_fixed_and_receipted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    observer = result.observer_protocol_receipt
    assert observer.detection_field_factor_value == 2.0
    assert not observer.detection_field_factor_mutable
    assert not observer.probabilistic_detection_claimed
    assert observer.detection_field_factor_source_ids == (
        "Crumey:2014:equation_53",
        "Crumey:2014:notional_field_factor_F_2",
    )
    assert result.threshold_receipt is not None
    assert result.threshold_receipt.field_factor == 2.0
    observer_component = next(
        receipt
        for receipt in result.components
        if receipt.role == "observer_protocol"
    )
    assert dict(observer_component.details) == {
        "task": "known_target_directed_averted_detection",
        "optical_aid": "none",
        "detection_field_factor_model_id": (
            "crumey_2014_equation_53_fixed_notional_f2_v1"
        ),
        "detection_field_factor_value": "2",
        "detection_field_factor_mutable": "false",
        "probabilistic_detection_claimed": "false",
    }
    assert "detection_field_factor" not in {
        field.name for field in fields(PhysicalVisibilityPolicy)
    }


def test_public_assessment_rejects_nonfinite_engine_photometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    monkeypatch.setattr(
        "moira.heliacal._physical_target_photometry_context",
        lambda _body, _jd_ut: _photometry_context(
            magnitude=float("nan")
        ),
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.reason == "target_photometry_missing"
    assert result.target_receipt is None


def test_public_assessment_rejects_profile_phase_extrapolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    monkeypatch.setattr(
        "moira.heliacal._physical_target_photometry_context",
        lambda _body, _jd_ut: _photometry_context(
            phase_angle_deg=165.001
        ),
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN
    )
    assert result.reason == "target_spectral_profile_out_of_domain"
    assert result.target_receipt is None


def test_public_assessment_requires_saturn_ring_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    monkeypatch.setattr(
        "moira.heliacal._physical_target_photometry_context",
        lambda _body, _jd_ut: _photometry_context(
            phase_angle_deg=3.0,
            saturn_ring_latitude_deg=None
        ),
    )

    result = physical_visibility_assessment(
        Body.SATURN,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert result.evidence_state is (
        PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY
    )
    assert result.reason == "target_spectral_profile_context_missing"
    assert result.target_receipt is None


def test_public_assessment_bortle_fallback_is_explicit_and_coarse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    policy = PhysicalVisibilityPolicy(
        background=PhysicalBortleBackground(
            light_pollution_class=3,
            scotopic_to_photopic_ratio=1.8,
            spectral_ratio_source_id="explicit-sp-ratio-v1",
            source_receipt_sha256=_SOURCE_SHA256,
        )
    )

    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=policy,
    )

    assert result.status is PhysicalVisibilityStatus.EVALUATED
    assert result.background_receipt is not None
    assert "coarse_night_sky_background" in (
        result.background_receipt.component_ids
    )
    assert "Bortle:2001:class_3" in (
        result.background_receipt.source_ids
    )


def test_public_assessment_pickle_round_trip_preserves_typed_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )

    assert pickle.loads(pickle.dumps(result)) == result


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite JSON number")
        return value
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _json_safe(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        return {
            key: _json_safe(item)
            for key, item in value.items()
        }
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def test_public_assessment_is_json_safe_without_rest_activation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_public_assessment_dependencies(monkeypatch)
    result = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=_physical_policy(),
    )
    not_evaluable = physical_visibility_assessment(
        Body.VENUS,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=VisibilityDataPackConfig(directory="unused"),
        policy=PhysicalVisibilityPolicy(),
    )
    payload, failure_payload = (
        json.loads(
            json.dumps(
                _json_safe(value),
                allow_nan=False,
                sort_keys=True,
            )
        )
        for value in (result, not_evaluable)
    )

    assert payload["status"] == "evaluated"
    assert payload["evidence_state"] == "evaluated_clear_sky"
    assert payload["data_pack_receipt"]["version"] == "1.1.0"
    assert payload["error_budget_receipt"]["method_id"] == (
        "phase2_data_pack_declared_numerical_error_envelope_v1"
    )
    assert (
        payload["error_budget_receipt"][
            "visibility_classification_within_data_pack_envelope"
        ]
        in {"visible", "not_visible", "indeterminate"}
    )
    assert (
        payload["target_receipt"]["spectral_model_details"][1]
        == [
            "color_model_id",
            "mallama_2017_ubvri_phase_color_v1",
        ]
    )
    assert failure_payload["status"] == "not_evaluable"
    assert failure_payload["reason"] == "background_input_incomplete"
    assert failure_payload["target_receipt"] is None
    assert failure_payload["error_budget_receipt"] is None

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pytest

from moira._visibility_targets import (
    VisibilityTargetContext,
    VisibilityTargetProfileError,
    parse_visibility_target_profiles,
    target_profile_by_id,
)
from moira.constants import Body


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = (
    _REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase2_planetary_target_profile_pack_spec.json"
)
_CHECKPOINT_PATH = (
    _REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase2_planetary_target_profiles_checkpoint_2026-07-30.json"
)
_UNIFORM_WEIGHTS = [1.0 / 400.0] * 400
_SCOTOPIC_TEST_WEIGHTS = [
    float(value) / math.fsum(range(1, 401))
    for value in range(400, 0, -1)
]
_SOURCE_RECEIPT = "a" * 64


def _spec() -> dict[str, Any]:
    return json.loads(_SPEC_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _payload() -> dict[str, Any]:
    spec = _spec()
    profiles = []
    for target_id in (
        Body.MERCURY,
        Body.VENUS,
        Body.MARS,
        Body.JUPITER,
        Body.SATURN,
    ):
        color_model = copy.deepcopy(
            spec["color_models"][target_id]
        )
        color_model.pop("source_note", None)
        color_model.setdefault("limitations", [])
        profiles.append(
            {
                "target_id": target_id,
                "spectral_profile_id": (
                    f"synthetic-{target_id.lower()}-profile-v1"
                ),
                "spectral_source_ids": (
                    ["source-owned-synthetic-spectrum-v1"]
                ),
                "spectral_source_receipt_sha256": _SOURCE_RECEIPT,
                "base_scotopic_to_photopic_ratio": 1.5,
                "base_photopic_extinction_weights": (
                    list(_UNIFORM_WEIGHTS)
                ),
                "base_scotopic_extinction_weights": (
                    list(_SCOTOPIC_TEST_WEIGHTS)
                ),
                "color_model": color_model,
            }
        )
    return {
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


def test_phase2_spec_binds_exact_planetary_source_artifacts() -> None:
    sources = _spec()["source_inputs"]

    assert (
        sources["payne_planetary_spectra"]["record_doi"]
        == "10.5281/zenodo.17470005"
    )
    assert (
        sources["payne_planetary_spectra"]["publication_doi"]
        == "10.3847/PSJ/ae2feb"
    )
    assert (
        sources["mallama_planetary_photometry"]["sha256"]
        == "7feb8edb372502cee5dc9c6a7656205e3279353bb38f9a98cbecbe8e8d733f91"
    )
    assert (
        sources["solar_spectrum"]["sha256"]
        == "432600ef415706c401a4c0e17c6b733a631f1556a78c3da32e936830288b414b"
    )
    assert {
        name: receipt["sha256"]
        for name, receipt in (
            sources["payne_planetary_spectra"]["files"].items()
        )
    } == {
        "Jupiter": (
            "839484ad8a416fd8ffe4fba293309a8f7943408e086d38d973fc619e64a1822b"
        ),
        "Mars": (
            "4bfdf7e77c94c0ed5f1f0cf20a6a62c3225436f20376c7f65828e31ed64c5fc4"
        ),
        "Mercury": (
            "ff7b907ac58088b4fecaf0cc8514d039bedc82e9911239f1552c01313d008a0c"
        ),
        "Saturn": (
            "4a8b3fe964db0e2442e1e602e57ad605b319d7b16be94c694e48fd08aacc6e37"
        ),
        "Venus": (
            "408e7bc644657f9479ac97ae1a13cdffefb3d060c14fd0e3902d2d13e8e85246"
        ),
    }


def test_phase2_checkpoint_binds_current_offline_tooling() -> None:
    checkpoint = json.loads(
        _CHECKPOINT_PATH.read_text(encoding="utf-8")
    )

    assert checkpoint["status"] == (
        "phase2_planetary_profiles_accepted"
    )
    assert checkpoint["pack"]["manifest_sha256"] == (
        "f594fd12058cc7f5c7bc9de7f2b06652"
        "bef3c0604ef7b0a05a069e54e4026c87"
    )
    assert checkpoint["validation"] == {
        "independent_validator_imports_builder": False,
        "independent_validator_imports_engine": False,
        "independent_source_rederivation_passed": True,
        "deterministic_repeat_file_count": 13,
        "deterministic_repeat_difference_count": 0,
        "windows_validation_passed": True,
        "network_used": False,
        "source_files_redistributed": False,
        "base_pack_mutated": False,
    }
    for receipt in checkpoint["tooling"]:
        path = _REPO_ROOT / receipt["path"]
        assert path.stat().st_size == receipt["bytes"]
        assert _sha256(path) == receipt["sha256"]
    validator_path = (
        _REPO_ROOT
        / "scripts"
        / "validate_visibility_phase2_data_pack.py"
    )
    tree = ast.parse(validator_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
    )
    assert "moira" not in imported_roots
    assert "build_visibility_phase2_data_pack" not in imported_roots


def test_target_catalog_parses_exact_inventory_and_source_domains() -> None:
    profiles = parse_visibility_target_profiles(_payload())

    assert tuple(profile.target_id for profile in profiles) == (
        Body.MERCURY,
        Body.VENUS,
        Body.MARS,
        Body.JUPITER,
        Body.SATURN,
    )
    assert tuple(
        profile.color_model.phase_angle_domain_deg
        for profile in profiles
    ) == (
        (2.0, 170.0),
        (2.0, 165.0),
        (0.0, 50.0),
        (0.0, 12.0),
        (0.0, 6.0),
    )


def test_mercury_gray_profile_is_constant_within_source_domain() -> None:
    profile = target_profile_by_id(
        parse_visibility_target_profiles(_payload()),
        Body.MERCURY,
    )

    low = profile.resolve(VisibilityTargetContext(phase_angle_deg=2.0))
    high = profile.resolve(
        VisibilityTargetContext(phase_angle_deg=170.0)
    )

    assert low.scotopic_to_photopic_ratio == (
        high.scotopic_to_photopic_ratio
    )
    assert low.photopic_extinction_weights == (
        high.photopic_extinction_weights
    )
    assert low.scotopic_extinction_weights == (
        high.scotopic_extinction_weights
    )
    assert math.fsum(low.photopic_extinction_weights) == pytest.approx(
        1.0,
        abs=2.0e-12,
    )
    assert math.fsum(low.scotopic_extinction_weights) == pytest.approx(
        1.0,
        abs=2.0e-12,
    )


def test_venus_phase_color_changes_both_response_paths_consistently() -> None:
    profile = target_profile_by_id(
        parse_visibility_target_profiles(_payload()),
        Body.VENUS,
    )

    low = profile.resolve(VisibilityTargetContext(phase_angle_deg=2.0))
    high = profile.resolve(
        VisibilityTargetContext(phase_angle_deg=165.0)
    )

    assert high.photopic_extinction_weights != (
        low.photopic_extinction_weights
    )
    assert high.scotopic_extinction_weights != (
        low.scotopic_extinction_weights
    )
    assert high.scotopic_to_photopic_ratio != pytest.approx(
        low.scotopic_to_photopic_ratio
    )
    assert math.fsum(high.photopic_extinction_weights) == pytest.approx(
        1.0,
        abs=2.0e-12,
    )
    assert math.fsum(high.scotopic_extinction_weights) == pytest.approx(
        1.0,
        abs=2.0e-12,
    )


@pytest.mark.parametrize("phase_angle_deg", (1.999, 165.001))
def test_venus_profile_prohibits_phase_extrapolation(
    phase_angle_deg: float,
) -> None:
    profile = target_profile_by_id(
        parse_visibility_target_profiles(_payload()),
        Body.VENUS,
    )

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        profile.resolve(
            VisibilityTargetContext(
                phase_angle_deg=phase_angle_deg
            )
        )

    assert (
        exc_info.value.reason
        == "target_spectral_profile_out_of_domain"
    )


def test_saturn_profile_requires_in_domain_ring_geometry() -> None:
    profile = target_profile_by_id(
        parse_visibility_target_profiles(_payload()),
        Body.SATURN,
    )

    with pytest.raises(VisibilityTargetProfileError) as missing:
        profile.resolve(VisibilityTargetContext(phase_angle_deg=3.0))
    with pytest.raises(VisibilityTargetProfileError) as outside:
        profile.resolve(
            VisibilityTargetContext(
                phase_angle_deg=3.0,
                saturn_effective_ring_sub_latitude_deg=27.001,
            )
        )

    assert (
        missing.value.reason
        == "target_spectral_profile_context_missing"
    )
    assert (
        outside.value.reason
        == "target_spectral_profile_out_of_domain"
    )


def test_target_payload_rejects_unknown_root_fields() -> None:
    payload = _payload()
    payload["undeclared_extension"] = True

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        parse_visibility_target_profiles(payload)

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_target_payload_rejects_changed_coefficient_shape() -> None:
    payload = _payload()
    payload["profiles"][1]["color_model"][
        "coefficients_by_band"
    ][0].append(0.0)

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        parse_visibility_target_profiles(payload)

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_target_payload_rejects_broadened_source_domain() -> None:
    payload = _payload()
    payload["profiles"][1]["color_model"][
        "phase_angle_domain_deg"
    ] = [0.0, 180.0]

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        parse_visibility_target_profiles(payload)

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_target_payload_rejects_relabelled_color_model() -> None:
    payload = _payload()
    payload["profiles"][1]["color_model"][
        "model_id"
    ] = "unreviewed_venus_model"

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        parse_visibility_target_profiles(payload)

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_target_resolution_fails_closed_on_numeric_overflow() -> None:
    payload = _payload()
    payload["profiles"][1]["color_model"][
        "coefficients_by_band"
    ][0][3] = 1.0e308
    profile = target_profile_by_id(
        parse_visibility_target_profiles(payload),
        Body.VENUS,
    )

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        profile.resolve(
            VisibilityTargetContext(phase_angle_deg=165.0)
        )

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_target_payload_rejects_silent_weight_normalization() -> None:
    payload = _payload()
    payload["profiles"][0][
        "base_photopic_extinction_weights"
    ] = [0.0] * 400

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        parse_visibility_target_profiles(payload)

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_missing_target_identity_is_typed() -> None:
    profiles = parse_visibility_target_profiles(_payload())

    with pytest.raises(VisibilityTargetProfileError) as exc_info:
        target_profile_by_id(profiles, Body.NEPTUNE)

    assert exc_info.value.reason == "target_spectral_profile_missing"

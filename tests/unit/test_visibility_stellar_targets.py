"""Strict tests for the Phase 3 source-bound Sirius profile."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from moira._visibility_stellar_targets import (
    VisibilityStellarTargetProfileError,
    parse_visibility_stellar_target_profiles,
    stellar_target_profile_by_id,
)


_SHA = "a" * 64


def _payload() -> dict[str, Any]:
    weights = [1.0 / 400.0] * 400
    return {
        "schema": (
            "moira.physical-heliacal-visibility-stellar-target-profiles/v1"
        ),
        "status": "complete_immutable_stellar_target_profiles",
        "catalog_id": "calspec_bsc5_cie_stellar_profiles_v1",
        "spectral_bins": {
            "coordinate": "bin_start_vacuum_nm",
            "start_nm": 380.0,
            "width_nm": 1.0,
            "count": 400,
        },
        "profiles": [
            {
                "target_id": "Sirius",
                "catalog_identity": {
                    "traditional_name": "Sirius",
                    "nomenclature": "alf CMa",
                    "hipparcos_id": 32349,
                    "hr_id": 2491,
                    "hd_id": 48915,
                },
                "visual_photometry": {
                    "system_id": "johnson_v",
                    "magnitude": -1.46,
                    "model_id": "bsc5_johnson_v_catalog_photometry_v1",
                    "source_ids": [
                        "BSC5:V/50:HR2491",
                        "Hoffleit_Warren:1991",
                    ],
                    "source_receipt_sha256": _SHA,
                },
                "spectral_profile_id": (
                    "calspec_sirius_stis_005_cie_response_v1"
                ),
                "spectral_source_ids": [
                    "STScI:CALSPEC:sirius_stis_005",
                    "CIE:10.25039/CIE.DS.dktna2s3",
                    "CIE:10.25039/CIE.DS.gr6w4b5g",
                ],
                "spectral_source_receipt_sha256": _SHA,
                "base_scotopic_to_photopic_ratio": 1.2,
                "base_photopic_extinction_weights": weights,
                "base_scotopic_extinction_weights": weights,
                "limitations": [
                    "sirius_only_first_stellar_admission",
                    "no_generic_catalog_color_index",
                ],
            }
        ],
    }


def test_sirius_profile_resolves_only_the_source_bound_catalog_identity() -> None:
    profiles = parse_visibility_stellar_target_profiles(_payload())
    profile = stellar_target_profile_by_id(profiles, "Sirius")

    resolved = profile.resolve(
        catalog_name="Sirius",
        catalog_nomenclature="alf CMa",
        catalog_visual_magnitude=-1.46,
    )

    assert resolved.target_id == "Sirius"
    assert resolved.visual_magnitude == -1.46
    assert (
        resolved.photometry_model_id
        == "bsc5_johnson_v_catalog_photometry_v1"
    )
    assert sum(resolved.photopic_extinction_weights) == pytest.approx(1.0)
    assert sum(resolved.scotopic_extinction_weights) == pytest.approx(1.0)
    assert ("hipparcos_id", "32349") in resolved.spectral_model_details
    assert ("hr_id", "2491") in resolved.spectral_model_details
    assert ("hd_id", "48915") in resolved.spectral_model_details


@pytest.mark.parametrize(
    ("catalog_name", "catalog_nomenclature", "magnitude", "reason"),
    (
        (
            "Dog Star",
            "alf CMa",
            -1.46,
            "stellar_target_identity_mismatch",
        ),
        (
            "Sirius",
            "alf CMa",
            -1.45,
            "stellar_target_photometry_mismatch",
        ),
    ),
)
def test_sirius_profile_fails_closed_on_runtime_catalog_drift(
    catalog_name: str,
    catalog_nomenclature: str,
    magnitude: float,
    reason: str,
) -> None:
    profile = parse_visibility_stellar_target_profiles(_payload())[0]

    with pytest.raises(VisibilityStellarTargetProfileError) as exc_info:
        profile.resolve(
            catalog_name=catalog_name,
            catalog_nomenclature=catalog_nomenclature,
            catalog_visual_magnitude=magnitude,
        )

    assert exc_info.value.reason == reason


def test_generic_color_index_cannot_enter_the_stellar_profile_contract() -> None:
    payload = deepcopy(_payload())
    payload["profiles"][0]["color_index"] = 0.0

    with pytest.raises(VisibilityStellarTargetProfileError) as exc_info:
        parse_visibility_stellar_target_profiles(payload)

    assert exc_info.value.reason == "visibility_data_pack_incompatible"


def test_unadmitted_stellar_profile_is_a_typed_dependency_gap() -> None:
    profiles = parse_visibility_stellar_target_profiles(_payload())

    with pytest.raises(VisibilityStellarTargetProfileError) as exc_info:
        stellar_target_profile_by_id(profiles, "Betelgeuse")

    assert exc_info.value.reason == "target_spectral_profile_missing"

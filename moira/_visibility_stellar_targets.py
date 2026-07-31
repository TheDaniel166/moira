"""Immutable stellar spectral-profile truth for physical visibility.

This internal module validates the separately distributed stellar-profile
payload used by the physical visibility model.  It does not query a catalog,
choose a public policy, download a spectrum, or use the legacy fixed-star
heliacal accelerator.

The first admitted inventory is deliberately narrow: Sirius only.  Its
spectral response is derived offline from the pinned STScI CALSPEC spectrum,
while Johnson-system visual photometry and catalog identity are independently
bound to the Bright Star Catalogue record.  Runtime resolution checks the
sovereign star record against those immutable identifiers and fails closed on
drift.  The generic registry ``color_index`` field is never consumed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


_SCHEMA = (
    "moira.physical-heliacal-visibility-stellar-target-profiles/v1"
)
_CATALOG_ID = "calspec_bsc5_cie_stellar_profiles_v1"
_TARGET_IDS = ("Sirius",)
_SPECTRAL_BIN_START_NM = tuple(float(value) for value in range(380, 780))
_HEX_DIGITS = frozenset("0123456789abcdef")
_SIRIUS_IDENTITY = {
    "traditional_name": "Sirius",
    "nomenclature": "alf CMa",
    "hipparcos_id": 32349,
    "hr_id": 2491,
    "hd_id": 48915,
}
_VISUAL_SYSTEM_ID = "johnson_v"
_VISUAL_MAGNITUDE = -1.46
_VISUAL_MAGNITUDE_RUNTIME_TOLERANCE = 1.0e-5


class VisibilityStellarTargetProfileError(ValueError):
    """Typed stellar-profile failure consumed by physical orchestration."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ResolvedVisibilityStellarTargetProfile:
    """One source-bound stellar spectrum matched to the sovereign catalog."""

    target_id: str
    visual_magnitude: float
    photometry_model_id: str
    photometry_source_ids: tuple[str, ...]
    scotopic_to_photopic_ratio: float
    photopic_extinction_weights: tuple[float, ...]
    scotopic_extinction_weights: tuple[float, ...]
    spectral_profile_id: str
    spectral_source_ids: tuple[str, ...]
    spectral_source_receipt_sha256: str
    spectral_model_details: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class VisibilityPackStellarTargetProfile:
    """Validated response integrands and identity law for one fixed star."""

    target_id: str
    traditional_name: str
    nomenclature: str
    hipparcos_id: int
    hr_id: int
    hd_id: int
    visual_system_id: str
    visual_magnitude: float
    photometry_model_id: str
    photometry_source_ids: tuple[str, ...]
    photometry_source_receipt_sha256: str
    spectral_profile_id: str
    spectral_source_ids: tuple[str, ...]
    spectral_source_receipt_sha256: str
    scotopic_to_photopic_ratio: float
    photopic_extinction_weights: tuple[float, ...]
    scotopic_extinction_weights: tuple[float, ...]
    limitations: tuple[str, ...]

    def resolve(
        self,
        *,
        catalog_name: str,
        catalog_nomenclature: str,
        catalog_visual_magnitude: float,
    ) -> ResolvedVisibilityStellarTargetProfile:
        """Bind one runtime star only when its exact catalog identity agrees."""

        if (
            catalog_name != self.traditional_name
            or catalog_nomenclature != self.nomenclature
        ):
            raise VisibilityStellarTargetProfileError(
                "stellar_target_identity_mismatch",
                (
                    f"{self.target_id} resolved as "
                    f"{catalog_name!r}/{catalog_nomenclature!r}"
                ),
            )
        if (
            isinstance(catalog_visual_magnitude, bool)
            or not isinstance(catalog_visual_magnitude, (int, float))
            or not math.isfinite(catalog_visual_magnitude)
            or not math.isclose(
                catalog_visual_magnitude,
                self.visual_magnitude,
                rel_tol=0.0,
                abs_tol=_VISUAL_MAGNITUDE_RUNTIME_TOLERANCE,
            )
        ):
            raise VisibilityStellarTargetProfileError(
                "stellar_target_photometry_mismatch",
                (
                    f"{self.target_id} catalog V={catalog_visual_magnitude!r} "
                    f"differs from source-bound V={self.visual_magnitude}"
                ),
            )
        details = (
            ("catalog_id", _CATALOG_ID),
            ("traditional_name", self.traditional_name),
            ("nomenclature", self.nomenclature),
            ("hipparcos_id", str(self.hipparcos_id)),
            ("hr_id", str(self.hr_id)),
            ("hd_id", str(self.hd_id)),
            ("visual_system_id", self.visual_system_id),
            ("visual_magnitude", format(self.visual_magnitude, ".17g")),
            (
                "visual_photometry_source_receipt_sha256",
                self.photometry_source_receipt_sha256,
            ),
            (
                "runtime_visual_magnitude_tolerance",
                format(_VISUAL_MAGNITUDE_RUNTIME_TOLERANCE, ".17g"),
            ),
            ("limitations", ",".join(self.limitations)),
        )
        return ResolvedVisibilityStellarTargetProfile(
            target_id=self.target_id,
            visual_magnitude=self.visual_magnitude,
            photometry_model_id=self.photometry_model_id,
            photometry_source_ids=self.photometry_source_ids,
            scotopic_to_photopic_ratio=self.scotopic_to_photopic_ratio,
            photopic_extinction_weights=self.photopic_extinction_weights,
            scotopic_extinction_weights=self.scotopic_extinction_weights,
            spectral_profile_id=self.spectral_profile_id,
            spectral_source_ids=self.spectral_source_ids,
            spectral_source_receipt_sha256=(
                self.spectral_source_receipt_sha256
            ),
            spectral_model_details=details,
        )


def parse_visibility_stellar_target_profiles(
    raw: Any,
) -> tuple[VisibilityPackStellarTargetProfile, ...]:
    """Validate an exact stellar-profile payload from a checked pack."""

    value = _require_dict(raw, "stellar target-profile payload")
    bins = _require_dict(value.get("spectral_bins"), "spectral bins")
    if (
        value.get("schema") != _SCHEMA
        or value.get("status")
        != "complete_immutable_stellar_target_profiles"
        or value.get("catalog_id") != _CATALOG_ID
        or bins
        != {
            "coordinate": "bin_start_vacuum_nm",
            "start_nm": 380.0,
            "width_nm": 1.0,
            "count": 400,
        }
    ):
        _incompatible("stellar target-profile contract differs")
    if set(value) != {
        "schema",
        "status",
        "catalog_id",
        "spectral_bins",
        "profiles",
    }:
        _incompatible("stellar target-profile payload fields differ")
    profiles = value.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != len(_TARGET_IDS):
        _incompatible("stellar target-profile inventory differs")
    result = tuple(_parse_profile(profile) for profile in profiles)
    if tuple(profile.target_id for profile in result) != _TARGET_IDS:
        _incompatible("stellar target-profile identities or order differ")
    return result


def stellar_target_profile_by_id(
    profiles: tuple[VisibilityPackStellarTargetProfile, ...],
    target_id: str,
) -> VisibilityPackStellarTargetProfile:
    """Return one exact admitted stellar profile or a typed dependency gap."""

    for profile in profiles:
        if profile.target_id == target_id:
            return profile
    raise VisibilityStellarTargetProfileError(
        "target_spectral_profile_missing",
        f"no pack-owned stellar spectral profile exists for {target_id}",
    )


def _parse_profile(raw: Any) -> VisibilityPackStellarTargetProfile:
    value = _require_dict(raw, "stellar target profile")
    if set(value) != {
        "target_id",
        "catalog_identity",
        "visual_photometry",
        "spectral_profile_id",
        "spectral_source_ids",
        "spectral_source_receipt_sha256",
        "base_scotopic_to_photopic_ratio",
        "base_photopic_extinction_weights",
        "base_scotopic_extinction_weights",
        "limitations",
    }:
        _incompatible("stellar target-profile fields differ")
    target_id = value.get("target_id")
    if target_id != "Sirius":
        _incompatible("unsupported stellar target identity")

    identity = _require_dict(value.get("catalog_identity"), "catalog identity")
    if identity != _SIRIUS_IDENTITY:
        _incompatible("Sirius catalog identity differs")

    photometry = _require_dict(
        value.get("visual_photometry"),
        "visual photometry",
    )
    if set(photometry) != {
        "system_id",
        "magnitude",
        "model_id",
        "source_ids",
        "source_receipt_sha256",
    }:
        _incompatible("stellar visual-photometry fields differ")
    if (
        photometry.get("system_id") != _VISUAL_SYSTEM_ID
        or photometry.get("magnitude") != _VISUAL_MAGNITUDE
        or photometry.get("model_id")
        != "bsc5_johnson_v_catalog_photometry_v1"
    ):
        _incompatible("Sirius visual photometry differs")
    photometry_sources = _source_ids(
        photometry.get("source_ids"),
        "visual-photometry source IDs",
    )
    photometry_receipt = _sha256(
        photometry.get("source_receipt_sha256"),
        "visual-photometry source receipt",
    )

    spectral_profile_id = value.get("spectral_profile_id")
    if spectral_profile_id != "calspec_sirius_stis_005_cie_response_v1":
        _incompatible("Sirius spectral-profile identity differs")
    spectral_sources = _source_ids(
        value.get("spectral_source_ids"),
        "spectral source IDs",
    )
    spectral_receipt = _sha256(
        value.get("spectral_source_receipt_sha256"),
        "spectral source receipt",
    )
    ratio = _positive_finite(
        value.get("base_scotopic_to_photopic_ratio"),
        "base S/P ratio",
    )
    photopic = _weights(
        value.get("base_photopic_extinction_weights"),
        "photopic extinction weights",
    )
    scotopic = _weights(
        value.get("base_scotopic_extinction_weights"),
        "scotopic extinction weights",
    )
    limitations_raw = value.get("limitations")
    if (
        not isinstance(limitations_raw, list)
        or not limitations_raw
        or any(
            not isinstance(item, str) or not item
            for item in limitations_raw
        )
        or len(limitations_raw) != len(set(limitations_raw))
    ):
        _incompatible("stellar-profile limitations differ")
    return VisibilityPackStellarTargetProfile(
        target_id=target_id,
        traditional_name=identity["traditional_name"],
        nomenclature=identity["nomenclature"],
        hipparcos_id=identity["hipparcos_id"],
        hr_id=identity["hr_id"],
        hd_id=identity["hd_id"],
        visual_system_id=photometry["system_id"],
        visual_magnitude=photometry["magnitude"],
        photometry_model_id=photometry["model_id"],
        photometry_source_ids=photometry_sources,
        photometry_source_receipt_sha256=photometry_receipt,
        spectral_profile_id=spectral_profile_id,
        spectral_source_ids=spectral_sources,
        spectral_source_receipt_sha256=spectral_receipt,
        scotopic_to_photopic_ratio=ratio,
        photopic_extinction_weights=photopic,
        scotopic_extinction_weights=scotopic,
        limitations=tuple(limitations_raw),
    )


def _weights(raw: Any, label: str) -> tuple[float, ...]:
    if not isinstance(raw, list) or len(raw) != len(_SPECTRAL_BIN_START_NM):
        _incompatible(f"{label} length differs")
    values = tuple(_positive_finite(value, label) for value in raw)
    if not math.isclose(
        math.fsum(values),
        1.0,
        rel_tol=0.0,
        abs_tol=2.0e-12,
    ):
        _incompatible(f"{label} are not normalized")
    return values


def _source_ids(raw: Any, label: str) -> tuple[str, ...]:
    if (
        not isinstance(raw, list)
        or not raw
        or any(not isinstance(value, str) or not value for value in raw)
        or len(raw) != len(set(raw))
    ):
        _incompatible(f"{label} differ")
    return tuple(raw)


def _sha256(raw: Any, label: str) -> str:
    if (
        not isinstance(raw, str)
        or len(raw) != 64
        or any(character not in _HEX_DIGITS for character in raw)
    ):
        _incompatible(f"{label} is not a lowercase SHA-256")
    return raw


def _positive_finite(raw: Any, label: str) -> float:
    if (
        isinstance(raw, bool)
        or not isinstance(raw, (int, float))
        or not math.isfinite(raw)
        or raw <= 0.0
    ):
        _incompatible(f"{label} must be positive and finite")
    return float(raw)


def _require_dict(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        _incompatible(f"{label} must be an object")
    return raw


def _incompatible(detail: str) -> None:
    raise VisibilityStellarTargetProfileError(
        "visibility_data_pack_incompatible",
        detail,
    )

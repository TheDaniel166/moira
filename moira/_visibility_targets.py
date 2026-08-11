"""Immutable planetary spectral-profile truth for physical visibility.

This internal module validates and resolves the target-profile payload shipped
by physical-visibility data packs.  It does not search for data, perform
ephemeris calculations, choose a public policy, or invent a target spectrum.

The pack owns the full-phase response integrands.  Source-derived
Johnson-Cousins phase laws supply differential color corrections relative to
the V band.  Those corrections are interpolated linearly in magnitude between
the published effective wavelengths, then applied consistently to the
photopic and scotopic response integrands.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from typing import Any


_SCHEMA = "moira.physical-heliacal-visibility-target-profiles/v1"
_CATALOG_ID = "payne_2026_mallama_2017_cie_target_profiles_v1"
_COLOR_WARP_METHOD = (
    "johnson_cousins_piecewise_linear_differential_magnitude_v1"
)
_TARGET_IDS = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")
_SPECTRAL_BIN_START_NM = tuple(float(value) for value in range(380, 780))
_BAND_WAVELENGTH_NM = (360.0, 436.0, 549.0, 700.0, 900.0)
_VISUAL_BAND_INDEX = 2
_MAGNITUDE_TO_NATURAL_LOG = -0.4 * math.log(10.0)
_HEX_DIGITS = frozenset("0123456789abcdef")
_COLOR_MODEL_CONTRACTS = {
    "Mercury": (
        "mallama_2017_gray_phase_shape_v1",
        "constant_color",
        (2.0, 170.0),
        None,
    ),
    "Venus": (
        "mallama_2017_ubvri_phase_color_v1",
        "phase_polynomial",
        (2.0, 165.0),
        None,
    ),
    "Mars": (
        "mallama_2017_ubvri_illumination_color_v1",
        "phase_polynomial",
        (0.0, 50.0),
        None,
    ),
    "Jupiter": (
        "mallama_2017_ubvri_geocentric_phase_color_v1",
        "phase_polynomial",
        (0.0, 12.0),
        None,
    ),
    "Saturn": (
        "mallama_2017_ubvri_ring_phase_color_v1",
        "saturn_ring_phase",
        (0.0, 6.0),
        (0.0, 27.0),
    ),
}


class VisibilityTargetProfileError(ValueError):
    """Typed target-profile failure consumed by physical orchestration."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, slots=True)
class VisibilityTargetContext:
    """Ephemeris-owned color context for one admitted planet."""

    phase_angle_deg: float
    saturn_effective_ring_sub_latitude_deg: float | None = None

    def __post_init__(self) -> None:
        _finite(self.phase_angle_deg, "phase_angle_deg")
        if self.saturn_effective_ring_sub_latitude_deg is not None:
            _finite(
                self.saturn_effective_ring_sub_latitude_deg,
                "saturn_effective_ring_sub_latitude_deg",
            )


@dataclass(frozen=True, slots=True)
class ResolvedVisibilityTargetProfile:
    """One pack-owned target profile resolved for an observing geometry."""

    target_id: str
    scotopic_to_photopic_ratio: float
    photopic_extinction_weights: tuple[float, ...]
    scotopic_extinction_weights: tuple[float, ...]
    spectral_profile_id: str
    spectral_source_ids: tuple[str, ...]
    spectral_source_receipt_sha256: str
    spectral_model_details: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class _TargetColorModel:
    """Pack-owned color model used to resolve a visibility target profile."""

    model_id: str
    kind: str
    phase_angle_domain_deg: tuple[float, float]
    coefficients_by_band: tuple[tuple[float, ...], ...]
    ring_sub_latitude_domain_deg: tuple[float, float] | None
    limitations: tuple[str, ...]

    def band_differential_magnitudes(
        self,
        context: VisibilityTargetContext,
    ) -> tuple[float, ...]:
        phase = context.phase_angle_deg
        lower, upper = self.phase_angle_domain_deg
        if not lower <= phase <= upper:
            raise VisibilityTargetProfileError(
                "target_spectral_profile_out_of_domain",
                (
                    f"phase_angle_deg={phase} is outside the "
                    f"source-owned [{lower}, {upper}] domain"
                ),
            )

        if self.kind == "constant_color":
            values = (0.0,) * len(_BAND_WAVELENGTH_NM)
        elif self.kind == "phase_polynomial":
            values = tuple(
                math.fsum(
                    coefficient * phase**power
                    for power, coefficient in enumerate(
                        coefficients,
                        start=1,
                    )
                )
                for coefficients in self.coefficients_by_band
            )
        else:
            ring_latitude = (
                context.saturn_effective_ring_sub_latitude_deg
            )
            if ring_latitude is None:
                raise VisibilityTargetProfileError(
                    "target_spectral_profile_context_missing",
                    "Saturn ring sub-latitude is required",
                )
            assert self.ring_sub_latitude_domain_deg is not None
            ring_lower, ring_upper = self.ring_sub_latitude_domain_deg
            if not ring_lower <= ring_latitude <= ring_upper:
                raise VisibilityTargetProfileError(
                    "target_spectral_profile_out_of_domain",
                    (
                        "saturn_effective_ring_sub_latitude_deg="
                        f"{ring_latitude} is outside the source-owned "
                        f"[{ring_lower}, {ring_upper}] domain"
                    ),
                )
            sin_ring = math.sin(math.radians(ring_latitude))
            values = tuple(
                (
                    c1 * sin_ring
                    + c2 * phase
                    - c3 * sin_ring * math.exp(c4 * phase)
                )
                for c1, c2, c3, c4 in self.coefficients_by_band
            )

        if any(not math.isfinite(value) for value in values):
            raise VisibilityTargetProfileError(
                "visibility_data_pack_incompatible",
                f"{self.model_id} produced a nonfinite color value",
            )
        visual_value = values[_VISUAL_BAND_INDEX]
        return tuple(value - visual_value for value in values)


@dataclass(frozen=True, slots=True)
class VisibilityPackTargetProfile:
    """Validated response integrands and color law for one planet."""

    target_id: str
    spectral_profile_id: str
    spectral_source_ids: tuple[str, ...]
    spectral_source_receipt_sha256: str
    base_scotopic_to_photopic_ratio: float
    base_photopic_extinction_weights: tuple[float, ...]
    base_scotopic_extinction_weights: tuple[float, ...]
    color_model: _TargetColorModel

    def resolve(
        self,
        context: VisibilityTargetContext,
    ) -> ResolvedVisibilityTargetProfile:
        """Resolve response weights without changing V-band photometry."""

        band_deltas = self.color_model.band_differential_magnitudes(
            context
        )
        ratio, photopic, scotopic = _resolve_response_weights_native(
            base_scotopic_to_photopic_ratio=(
                self.base_scotopic_to_photopic_ratio
            ),
            base_photopic=self.base_photopic_extinction_weights,
            base_scotopic=self.base_scotopic_extinction_weights,
            band_deltas=band_deltas,
        )
        details = [
            ("catalog_id", _CATALOG_ID),
            ("color_model_id", self.color_model.model_id),
            ("color_warp_method", _COLOR_WARP_METHOD),
            (
                "phase_angle_deg",
                format(context.phase_angle_deg, ".17g"),
            ),
            (
                "phase_angle_domain_deg",
                (
                    f"{self.color_model.phase_angle_domain_deg[0]:g}.."
                    f"{self.color_model.phase_angle_domain_deg[1]:g}"
                ),
            ),
        ]
        if (
            context.saturn_effective_ring_sub_latitude_deg
            is not None
        ):
            details.append(
                (
                    "saturn_effective_ring_sub_latitude_deg",
                    format(
                        context.saturn_effective_ring_sub_latitude_deg,
                        ".17g",
                    ),
                )
            )
        if self.color_model.limitations:
            details.append(
                ("limitations", ",".join(self.color_model.limitations))
            )
        return ResolvedVisibilityTargetProfile(
            target_id=self.target_id,
            scotopic_to_photopic_ratio=ratio,
            photopic_extinction_weights=photopic,
            scotopic_extinction_weights=scotopic,
            spectral_profile_id=self.spectral_profile_id,
            spectral_source_ids=self.spectral_source_ids,
            spectral_source_receipt_sha256=(
                self.spectral_source_receipt_sha256
            ),
            spectral_model_details=tuple(details),
        )


def parse_visibility_target_profiles(
    raw: Any,
) -> tuple[VisibilityPackTargetProfile, ...]:
    """Validate an exact target-profile payload from a checked pack."""

    value = _require_dict(raw, "target-profile payload")
    bins = _require_dict(value.get("spectral_bins"), "spectral bins")
    if (
        value.get("schema") != _SCHEMA
        or value.get("status") != "complete_immutable_target_profiles"
        or value.get("catalog_id") != _CATALOG_ID
        or value.get("color_warp_method") != _COLOR_WARP_METHOD
        or bins
        != {
            "coordinate": "bin_start_vacuum_nm",
            "start_nm": 380.0,
            "width_nm": 1.0,
            "count": 400,
        }
    ):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            "target-profile contract differs",
        )
    if set(value) != {
        "schema",
        "status",
        "catalog_id",
        "color_warp_method",
        "spectral_bins",
        "profiles",
    }:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            "target-profile payload fields differ",
        )
    profiles = value.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != len(
        _TARGET_IDS
    ):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            "target-profile inventory differs",
        )
    result = tuple(_parse_profile(profile) for profile in profiles)
    if tuple(profile.target_id for profile in result) != _TARGET_IDS:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            "target-profile identities or order differ",
        )
    return result


def target_profile_by_id(
    profiles: tuple[VisibilityPackTargetProfile, ...],
    target_id: str,
) -> VisibilityPackTargetProfile:
    """Return one exact admitted profile or a typed missing dependency."""

    for profile in profiles:
        if profile.target_id == target_id:
            return profile
    raise VisibilityTargetProfileError(
        "target_spectral_profile_missing",
        f"no pack-owned spectral profile exists for {target_id}",
    )


def _parse_profile(raw: Any) -> VisibilityPackTargetProfile:
    value = _require_dict(raw, "target profile")
    target_id = _nonempty_string(value.get("target_id"), "target_id")
    spectral_profile_id = _nonempty_string(
        value.get("spectral_profile_id"),
        "spectral_profile_id",
    )
    source_ids = _source_ids(
        value.get("spectral_source_ids"),
        "spectral_source_ids",
    )
    receipt = _sha256(
        value.get("spectral_source_receipt_sha256"),
        "spectral_source_receipt_sha256",
    )
    ratio = _positive_finite(
        value.get("base_scotopic_to_photopic_ratio"),
        "base_scotopic_to_photopic_ratio",
    )
    photopic = _weights(
        value.get("base_photopic_extinction_weights"),
        "base_photopic_extinction_weights",
    )
    scotopic = _weights(
        value.get("base_scotopic_extinction_weights"),
        "base_scotopic_extinction_weights",
    )
    color_model = _parse_color_model(
        target_id,
        value.get("color_model"),
    )
    if set(value) != {
        "target_id",
        "spectral_profile_id",
        "spectral_source_ids",
        "spectral_source_receipt_sha256",
        "base_scotopic_to_photopic_ratio",
        "base_photopic_extinction_weights",
        "base_scotopic_extinction_weights",
        "color_model",
    }:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"target-profile fields differ for {target_id}",
        )
    return VisibilityPackTargetProfile(
        target_id=target_id,
        spectral_profile_id=spectral_profile_id,
        spectral_source_ids=source_ids,
        spectral_source_receipt_sha256=receipt,
        base_scotopic_to_photopic_ratio=ratio,
        base_photopic_extinction_weights=photopic,
        base_scotopic_extinction_weights=scotopic,
        color_model=color_model,
    )


def _parse_color_model(
    target_id: str,
    raw: Any,
) -> _TargetColorModel:
    value = _require_dict(raw, f"{target_id} color model")
    model_id = _nonempty_string(value.get("model_id"), "model_id")
    kind = value.get("kind")
    (
        expected_model_id,
        expected_kind,
        expected_phase_domain,
        expected_ring_domain,
    ) = _COLOR_MODEL_CONTRACTS[target_id]
    if kind != expected_kind or model_id != expected_model_id:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"unsupported color model for {target_id}",
        )
    phase_domain = _interval(
        value.get("phase_angle_domain_deg"),
        "phase_angle_domain_deg",
    )
    if phase_domain != expected_phase_domain:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"phase-angle source domain differs for {target_id}",
        )
    limitations = _string_tuple(
        value.get("limitations", []),
        "limitations",
        allow_empty=True,
    )
    if len(limitations) != len(set(limitations)):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"limitations must be unique for {target_id}",
        )
    coefficients: tuple[tuple[float, ...], ...] = ()
    ring_domain: tuple[float, float] | None = None
    allowed = {
        "model_id",
        "kind",
        "phase_angle_domain_deg",
        "limitations",
    }
    if kind != "constant_color":
        coefficient_count = {
            "Venus": 4,
            "Mars": 2,
            "Jupiter": 2,
            "Saturn": 4,
        }[target_id]
        coefficients = _coefficient_matrix(
            value.get("coefficients_by_band"),
            coefficient_count=coefficient_count,
        )
        allowed.add("coefficients_by_band")
    if kind == "saturn_ring_phase":
        ring_domain = _interval(
            value.get("ring_sub_latitude_domain_deg"),
            "ring_sub_latitude_domain_deg",
        )
        if ring_domain != expected_ring_domain:
            raise VisibilityTargetProfileError(
                "visibility_data_pack_incompatible",
                "Saturn ring source domain differs",
            )
        allowed.add("ring_sub_latitude_domain_deg")
    if set(value) != allowed:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"color-model fields differ for {target_id}",
        )
    return _TargetColorModel(
        model_id=model_id,
        kind=kind,
        phase_angle_domain_deg=phase_domain,
        coefficients_by_band=coefficients,
        ring_sub_latitude_domain_deg=ring_domain,
        limitations=limitations,
    )


def _coefficient_matrix(
    raw: Any,
    *,
    coefficient_count: int | None,
) -> tuple[tuple[float, ...], ...]:
    if not isinstance(raw, list) or len(raw) != len(
        _BAND_WAVELENGTH_NM
    ):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            "color coefficient matrix differs",
        )
    rows: list[tuple[float, ...]] = []
    row_length: int | None = coefficient_count
    for row in raw:
        if not isinstance(row, list) or not row:
            raise VisibilityTargetProfileError(
                "visibility_data_pack_incompatible",
                "color coefficient row differs",
            )
        values = tuple(_finite(value, "color coefficient") for value in row)
        if row_length is None:
            row_length = len(values)
        if len(values) != row_length:
            raise VisibilityTargetProfileError(
                "visibility_data_pack_incompatible",
                "color coefficient row lengths differ",
            )
        rows.append(values)
    return tuple(rows)


def _weights(raw: Any, label: str) -> tuple[float, ...]:
    if not isinstance(raw, list) or len(raw) != len(
        _SPECTRAL_BIN_START_NM
    ):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} length differs",
        )
    values = tuple(_nonnegative_finite(value, label) for value in raw)
    if not math.isclose(
        math.fsum(values),
        1.0,
        rel_tol=0.0,
        abs_tol=2.0e-12,
    ):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} is not normalized",
        )
    return values


def _piecewise_linear(
    x_values: tuple[float, ...],
    y_values: tuple[float, ...],
    x: float,
) -> float:
    high = bisect.bisect_right(x_values, x)
    if high == 0 or high == len(x_values):
        raise VisibilityTargetProfileError(
            "target_spectral_profile_out_of_domain",
            f"wavelength {x} is outside the color-warp domain",
        )
    low = high - 1
    fraction = (x - x_values[low]) / (
        x_values[high] - x_values[low]
    )
    return y_values[low] + fraction * (
        y_values[high] - y_values[low]
    )


def _resolve_response_weights_python(
    *,
    base_scotopic_to_photopic_ratio: float,
    base_photopic: tuple[float, ...],
    base_scotopic: tuple[float, ...],
    band_deltas: tuple[float, ...],
) -> tuple[float, tuple[float, ...], tuple[float, ...]]:
    """Python differential oracle for the admitted dense native kernel."""

    log_correction = tuple(
        _MAGNITUDE_TO_NATURAL_LOG
        * _piecewise_linear(
            _BAND_WAVELENGTH_NM,
            band_deltas,
            wavelength_nm,
        )
        for wavelength_nm in _SPECTRAL_BIN_START_NM
    )
    if any(not math.isfinite(value) for value in log_correction):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            "color warp produced a nonfinite logarithmic correction",
        )
    maximum_log_correction = max(log_correction)
    correction = tuple(
        math.exp(value - maximum_log_correction)
        for value in log_correction
    )
    photopic_scale = math.fsum(
        weight * factor
        for weight, factor in zip(base_photopic, correction)
    )
    scotopic_scale = math.fsum(
        weight * factor
        for weight, factor in zip(base_scotopic, correction)
    )
    if photopic_scale <= 0.0 or scotopic_scale <= 0.0:
        raise VisibilityTargetProfileError(
            "target_spectral_profile_missing",
            "resolved response integral is nonpositive",
        )
    photopic = tuple(
        weight * factor / photopic_scale
        for weight, factor in zip(base_photopic, correction)
    )
    scotopic = tuple(
        weight * factor / scotopic_scale
        for weight, factor in zip(base_scotopic, correction)
    )
    ratio = (
        base_scotopic_to_photopic_ratio
        * scotopic_scale
        / photopic_scale
    )
    if not math.isfinite(ratio) or ratio <= 0.0:
        raise VisibilityTargetProfileError(
            "target_spectral_profile_missing",
            "resolved S/P ratio is not positive and finite",
        )
    return ratio, photopic, scotopic


def _resolve_response_weights_native(
    *,
    base_scotopic_to_photopic_ratio: float,
    base_photopic: tuple[float, ...],
    base_scotopic: tuple[float, ...],
    band_deltas: tuple[float, ...],
) -> tuple[float, tuple[float, ...], tuple[float, ...]]:
    """Run the admitted doctrine-free kernel with Python-owned inputs."""

    from . import moira_native

    ratio, photopic, scotopic = (
        moira_native._physical_visibility_resolve_response_weights(
            _BAND_WAVELENGTH_NM,
            band_deltas,
            _SPECTRAL_BIN_START_NM,
            base_scotopic_to_photopic_ratio,
            base_photopic,
            base_scotopic,
        )
    )
    return float(ratio), tuple(photopic), tuple(scotopic)


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must be an object",
        )
    return value


def _finite(value: Any, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must be finite",
        )
    return float(value)


def _positive_finite(value: Any, label: str) -> float:
    number = _finite(value, label)
    if number <= 0.0:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must be positive",
        )
    return number


def _nonnegative_finite(value: Any, label: str) -> float:
    number = _finite(value, label)
    if number < 0.0:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must be nonnegative",
        )
    return number


def _interval(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must contain two values",
        )
    lower = _finite(value[0], f"{label} lower")
    upper = _finite(value[1], f"{label} upper")
    if lower < 0.0 or upper < lower or upper > 180.0:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} is invalid",
        )
    return lower, upper


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must be nonempty",
        )
    return value


def _source_ids(value: Any, label: str) -> tuple[str, ...]:
    result = _string_tuple(value, label, allow_empty=False)
    if len(set(result)) != len(result):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must be unique",
        )
    return result


def _string_tuple(
    value: Any,
    label: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must contain nonempty strings",
        )
    return tuple(value)


def _sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX_DIGITS for character in value)
    ):
        raise VisibilityTargetProfileError(
            "visibility_data_pack_incompatible",
            f"{label} must be lowercase SHA-256",
        )
    return value

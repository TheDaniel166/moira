"""Independently validate the Phase 3 event crossing certificate.

This read-only validator imports neither Moira nor the event solver.  It
recomputes the exact data-pack interpolant slopes, the astronomical coordinate
ceilings, and the visibility-margin bound recorded by the source-controlled
certificate.  It never uses a network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CERTIFICATE = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase3_event_crossing_certificate.json"
)
MANIFEST_NAME = "manifest.json"
EXPECTED_CERTIFICATE_SHA256 = (
    "eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e"
)
EXPECTED_PACK_MANIFEST_SHA256 = (
    "cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c"
)


class ValidationError(ValueError):
    """Raised when any crossing-certificate admission check fails."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    return value


def _f32(path: Path, expected_count: int) -> tuple[float, ...]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read {path.name}") from exc
    if len(payload) != expected_count * 4:
        raise ValidationError(f"{path.name} value count differs")
    values = struct.unpack(f"<{expected_count}f", payload)
    if any(not math.isfinite(value) or value <= 0.0 for value in values):
        raise ValidationError(f"{path.name} contains invalid values")
    return values


def _close(actual: float, expected: Any, label: str) -> None:
    if (
        isinstance(expected, bool)
        or not isinstance(expected, (int, float))
        or not math.isfinite(float(expected))
        or not math.isclose(
            actual,
            float(expected),
            rel_tol=2.0e-15,
            abs_tol=2.0e-15,
        )
    ):
        raise ValidationError(
            f"{label} differs: derived {actual!r}, recorded {expected!r}"
        )


def _strict_axis(raw: Any, label: str) -> tuple[float, ...]:
    if (
        not isinstance(raw, list)
        or len(raw) < 2
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in raw
        )
    ):
        raise ValidationError(f"{label} axis differs")
    values = tuple(float(value) for value in raw)
    if any(right <= left for left, right in zip(values, values[1:])):
        raise ValidationError(f"{label} axis is not strictly increasing")
    return values


def _direct_extinction_derivative_ceiling(
    *,
    altitudes: tuple[float, ...],
    values: tuple[float, ...],
    spectral_bin_count: int,
) -> float:
    """Maximum derivative of the runtime log10(altitude + 0.25) interpolant."""

    maximum = 0.0
    for row in range(len(altitudes) - 1):
        low_altitude = altitudes[row]
        high_altitude = altitudes[row + 1]
        low_coordinate = math.log10(low_altitude + 0.25)
        high_coordinate = math.log10(high_altitude + 0.25)
        coordinate_width = high_coordinate - low_coordinate
        coordinate_derivative_ceiling = 1.0 / (
            math.log(10.0) * (low_altitude + 0.25)
        )
        for spectral_bin in range(spectral_bin_count):
            low_value = values[row * spectral_bin_count + spectral_bin]
            high_value = values[
                (row + 1) * spectral_bin_count + spectral_bin
            ]
            derivative = (
                abs(high_value - low_value)
                / coordinate_width
                * coordinate_derivative_ceiling
            )
            maximum = max(maximum, derivative)
    return maximum


def _surface_brightness_slopes(
    *,
    values: tuple[float, ...],
    axes: tuple[
        tuple[float, ...],
        tuple[float, ...],
        tuple[float, ...],
    ],
) -> tuple[float, float, float]:
    """Maximum magnitude-coordinate slope of the trilinear log10 surface."""

    shape = tuple(len(axis) for axis in axes)
    maximums = [0.0, 0.0, 0.0]
    for first in range(shape[0]):
        for second in range(shape[1]):
            for third in range(shape[2]):
                coordinate = (first, second, third)
                index = (first * shape[1] + second) * shape[2] + third
                for dimension in range(3):
                    if coordinate[dimension] + 1 >= shape[dimension]:
                        continue
                    neighbor = list(coordinate)
                    neighbor[dimension] += 1
                    neighbor_index = (
                        (neighbor[0] * shape[1] + neighbor[1])
                        * shape[2]
                        + neighbor[2]
                    )
                    width = (
                        axes[dimension][neighbor[dimension]]
                        - axes[dimension][coordinate[dimension]]
                    )
                    slope = (
                        2.5
                        * abs(
                            math.log10(values[neighbor_index])
                            - math.log10(values[index])
                        )
                        / width
                    )
                    maximums[dimension] = max(
                        maximums[dimension],
                        slope,
                    )
    return tuple(maximums)  # type: ignore[return-value]


def validate(
    *,
    certificate_path: Path,
    pack: Path,
) -> dict[str, Any]:
    if (
        not certificate_path.is_file()
        or certificate_path.is_symlink()
        or _sha256(certificate_path) != EXPECTED_CERTIFICATE_SHA256
    ):
        raise ValidationError("crossing-certificate identity differs")
    certificate = _json(certificate_path, "crossing certificate")
    if (
        certificate.get("schema")
        != "moira.physical-heliacal-visibility-event-crossing-certificate/v1"
        or certificate.get("certificate_id")
        != "physical-heliacal-event-lipschitz-v1"
        or certificate.get("status")
        != "admitted_exact_pack_crossing_certificate"
    ):
        raise ValidationError("crossing-certificate contract differs")
    admission = certificate.get("event_admission")
    if admission != {
        "planetary_targets": ["Mars", "Jupiter", "Saturn"],
        "stellar_targets": ["Sirius"],
        "phases": [
            "morning_first_rising",
            "morning_first_setting",
            "evening_last_rising",
            "evening_last_setting",
        ],
        "explicitly_not_admitted": {
            "Mercury": (
                "event guards can leave the source-owned "
                "2-to-170-degree phase domain"
            ),
            "Venus": (
                "event guards can leave the source-owned "
                "2-to-165-degree phase domain"
            ),
        },
    }:
        raise ValidationError("event admission matrix differs")
    solver_law = certificate.get("solver_law")
    if (
        not isinstance(solver_law, dict)
        or solver_law.get("unresolved_result")
        != "crossing_completeness_not_certified"
        or solver_law.get("dense_sampling_alone_is_a_certificate")
        is not False
    ):
        raise ValidationError("solver fail-closed law differs")

    if not pack.is_dir() or pack.is_symlink():
        raise ValidationError("pack must be an explicit regular directory")
    manifest_path = pack / MANIFEST_NAME
    if (
        not manifest_path.is_file()
        or manifest_path.is_symlink()
        or _sha256(manifest_path) != EXPECTED_PACK_MANIFEST_SHA256
    ):
        raise ValidationError("exact data-pack identity differs")
    manifest = _json(manifest_path, "data-pack manifest")
    exact_pack = certificate.get("exact_data_pack")
    if (
        exact_pack
        != {
            "pack_id": "moira-physical-heliacal-visibility",
            "version": "1.2.0",
            "manifest_sha256": EXPECTED_PACK_MANIFEST_SHA256,
        }
        or manifest.get("pack_id") != exact_pack["pack_id"]
        or manifest.get("version") != exact_pack["version"]
    ):
        raise ValidationError("certificate pack binding differs")
    roles = manifest.get("file_roles")
    if not isinstance(roles, dict):
        raise ValidationError("data-pack roles are malformed")
    axes = _json(pack / roles["axes"], "data-pack axes")

    direct = axes.get("direct_extinction")
    radiance = axes.get("radiance")
    if not isinstance(direct, dict) or not isinstance(radiance, dict):
        raise ValidationError("data-pack axes contract differs")
    direct_altitudes = _strict_axis(
        direct.get("target_true_altitude_deg"),
        "direct target altitude",
    )
    spectral = direct.get("spectral_bins")
    if (
        not isinstance(spectral, dict)
        or spectral.get("count") != 400
        or direct.get("value_count") != len(direct_altitudes) * 400
    ):
        raise ValidationError("direct-extinction shape differs")
    direct_values = _f32(
        pack / roles["direct_extinction"],
        direct["value_count"],
    )
    direct_slope = _direct_extinction_derivative_ceiling(
        altitudes=direct_altitudes,
        values=direct_values,
        spectral_bin_count=400,
    )

    radiance_axes_raw = radiance.get("axes")
    coordinate_order = radiance.get("coordinate_order")
    if (
        not isinstance(radiance_axes_raw, dict)
        or coordinate_order
        != [
            "solar_center_altitude_deg",
            "target_true_altitude_deg",
            "relative_solar_azimuth_deg",
        ]
    ):
        raise ValidationError("radiance axis order differs")
    radiance_axes = tuple(
        _strict_axis(radiance_axes_raw[name], name)
        for name in coordinate_order
    )
    radiance_count = math.prod(len(axis) for axis in radiance_axes)
    if radiance.get("value_count") != radiance_count:
        raise ValidationError("radiance shape differs")
    photopic_slopes = _surface_brightness_slopes(
        values=_f32(
            pack / roles["photopic_luminance"],
            radiance_count,
        ),
        axes=radiance_axes,  # type: ignore[arg-type]
    )
    scotopic_slopes = _surface_brightness_slopes(
        values=_f32(
            pack / roles["scotopic_luminance"],
            radiance_count,
        ),
        axes=radiance_axes,  # type: ignore[arg-type]
    )
    slopes = certificate.get("exact_pack_maximum_piecewise_slopes")
    if not isinstance(slopes, dict):
        raise ValidationError("pack-slope receipt is malformed")
    _close(
        direct_slope,
        slopes.get(
            "direct_extinction_magnitude_per_target_altitude_deg"
        ),
        "direct-extinction interpolant derivative",
    )
    for prefix, derived in (
        ("photopic", photopic_slopes),
        ("scotopic", scotopic_slopes),
    ):
        for coordinate, value in zip(
            ("solar_altitude", "target_altitude", "relative_azimuth"),
            derived,
        ):
            _close(
                value,
                slopes.get(
                    f"{prefix}_surface_brightness_magnitude_per_"
                    f"{coordinate}_deg"
                ),
                f"{prefix} {coordinate} slope",
            )

    astronomy = certificate.get("astronomical_rate_bound_derivation")
    admitted_rates = certificate.get(
        "astronomical_absolute_rate_bounds_per_day"
    )
    if not isinstance(astronomy, dict) or not isinstance(
        admitted_rates,
        dict,
    ):
        raise ValidationError("astronomical rate receipt is malformed")
    sidereal = float(astronomy["sidereal_rotation_ceiling_deg_per_day"])
    sun_motion = float(
        astronomy["solar_apparent_motion_allowance_deg_per_day"]
    )
    target_motion = float(
        astronomy[
            "admitted_target_apparent_motion_allowance_deg_per_day"
        ]
    )
    target_altitude_limit = float(
        astronomy["pack_maximum_target_true_altitude_deg"]
    )
    solar_altitude_limit = float(
        astronomy["pack_maximum_absolute_solar_altitude_deg"]
    )
    refraction_factor = float(
        astronomy["refraction_derivative_amplification_ceiling"]
    )
    solar_rate = sidereal + sun_motion
    target_rate = sidereal + target_motion
    relative_azimuth_rate = (
        target_rate
        / math.cos(math.radians(target_altitude_limit))
        + solar_rate
        / math.cos(math.radians(solar_altitude_limit))
    )
    refracted_rate = target_rate * refraction_factor
    for key, derived in (
        (
            "derived_solar_true_altitude_rate_ceiling_deg_per_day",
            solar_rate,
        ),
        (
            "derived_target_true_altitude_rate_ceiling_deg_per_day",
            target_rate,
        ),
        (
            "derived_relative_solar_azimuth_rate_ceiling_deg_per_day",
            relative_azimuth_rate,
        ),
        (
            "derived_refracted_apparent_horizon_rate_ceiling_deg_per_day",
            refracted_rate,
        ),
    ):
        _close(derived, astronomy.get(key), key)
    if (
        astronomy.get(
            "coordinate_singularity_excluded_by_pack_target_altitude_ceiling"
        )
        is not True
        or target_altitude_limit != radiance_axes[1][-1]
        or solar_altitude_limit
        != max(abs(value) for value in radiance_axes[0])
    ):
        raise ValidationError("coordinate-domain derivation differs")
    for key, derived in (
        ("solar_true_altitude_deg", solar_rate),
        ("target_true_altitude_deg", target_rate),
        ("relative_solar_azimuth_deg", relative_azimuth_rate),
        ("refracted_apparent_horizon_signal_deg", refracted_rate),
    ):
        admitted = admitted_rates.get(key)
        if (
            isinstance(admitted, bool)
            or not isinstance(admitted, (int, float))
            or float(admitted) < derived
        ):
            raise ValidationError(f"{key} admitted rate is insufficient")

    margin = certificate.get(
        "visibility_margin_rate_derivation_magnitude_per_day"
    )
    if not isinstance(margin, dict):
        raise ValidationError("visibility-margin derivation is malformed")
    direct_ceiling = (
        direct_slope * float(admitted_rates["target_true_altitude_deg"])
    )
    solar_slope = max(photopic_slopes[0], scotopic_slopes[0])
    target_slope = max(photopic_slopes[1], scotopic_slopes[1])
    azimuth_slope = max(photopic_slopes[2], scotopic_slopes[2])
    twilight_ceiling = (
        solar_slope * float(admitted_rates["solar_true_altitude_deg"])
        + target_slope
        * float(admitted_rates["target_true_altitude_deg"])
        + azimuth_slope
        * float(admitted_rates["relative_solar_azimuth_deg"])
    )
    amplification = float(
        margin["cie_mes2_and_crumey_amplification_factor"]
    )
    photometry = float(
        margin["outer_planet_photometry_and_profile_allowance"]
    )
    rounding = float(margin["rounding_and_boundary_allowance"])
    total = (
        direct_ceiling
        + twilight_ceiling * amplification
        + photometry
        + rounding
    )
    _close(
        direct_ceiling,
        margin.get("direct_extinction_interpolant_ceiling"),
        "direct-extinction rate ceiling",
    )
    _close(
        twilight_ceiling,
        margin.get("twilight_surface_brightness_coordinate_ceiling"),
        "twilight rate ceiling",
    )
    _close(
        total,
        margin.get("derived_total_before_binary_ceiling"),
        "visibility-margin total",
    )
    binary_ceiling = margin.get("admitted_binary_ceiling")
    if (
        isinstance(binary_ceiling, bool)
        or not isinstance(binary_ceiling, (int, float))
        or float(binary_ceiling) < total
        or not float(binary_ceiling).is_integer()
        or int(binary_ceiling) & (int(binary_ceiling) - 1)
    ):
        raise ValidationError(
            "visibility-margin binary ceiling is insufficient"
        )

    return {
        "status": "accepted",
        "certificate_id": certificate["certificate_id"],
        "certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
        "pack_manifest_sha256": EXPECTED_PACK_MANIFEST_SHA256,
        "direct_extinction_derivative_ceiling": direct_slope,
        "photopic_surface_brightness_slopes": list(photopic_slopes),
        "scotopic_surface_brightness_slopes": list(scotopic_slopes),
        "derived_relative_azimuth_rate_ceiling": relative_azimuth_rate,
        "derived_visibility_margin_rate_ceiling": total,
        "admitted_visibility_margin_rate_ceiling": float(binary_ceiling),
        "network_used": False,
        "builder_or_runtime_imported": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--certificate",
        type=Path,
        default=DEFAULT_CERTIFICATE,
    )
    parser.add_argument("--pack", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = validate(
            certificate_path=arguments.certificate.resolve(),
            pack=arguments.pack.resolve(),
        )
    except (OSError, ValidationError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

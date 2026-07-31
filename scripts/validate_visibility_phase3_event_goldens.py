"""Validate Phase 3 event goldens against independent external geometry.

The validator imports neither Moira nor its event solver.  Jupiter geometry,
phase, and apparent magnitude come from checksum-locked JPL Horizons observer
tables.  Sirius astrometry comes from checksum-locked Hipparcos I/239 data and
is transformed by a pinned offline Astropy/ERFA/IERS toolchain; its solar
geometry comes from Horizons.  The exact external visibility pack is then
evaluated through a separate implementation of its published interpolation,
CIE MES2, and Crumey equations.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import importlib.metadata
import json
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN = (
    REPO_ROOT
    / "tests"
    / "golden"
    / "physical_visibility_phase3_events.json"
)
MANIFEST_NAME = "manifest.json"
SPECTRAL_WAVELENGTHS_NM = tuple(float(value) for value in range(380, 780))
BAND_WAVELENGTHS_NM = (360.0, 436.0, 549.0, 700.0, 900.0)
CRUMEY_ZERO_POINT_LUX = 2.54e-6
CIE_V_PRIME_555 = 683.0 / 1700.0


class ValidationError(ValueError):
    """Raised when an independent Phase 3 event check fails."""


@dataclass(frozen=True, slots=True)
class ObserverRow:
    """One source-owned airless topocentric observer row."""

    jd_ut: float
    azimuth_deg: float
    altitude_deg: float
    apparent_magnitude: float | None = None
    phase_angle_deg: float | None = None


@dataclass(frozen=True, slots=True)
class MarginRow:
    """One independently evaluated in-domain visibility margin."""

    jd_ut: float
    margin_magnitude: float


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


def _verify_file(
    path: Path,
    receipt: dict[str, Any],
    label: str,
) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != receipt.get("bytes")
        or _sha256(path) != receipt.get("sha256")
    ):
        raise ValidationError(f"{label} identity differs")


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


def _bracket(
    axis: tuple[float, ...],
    value: float,
) -> tuple[int, int, float]:
    if not axis[0] <= value <= axis[-1]:
        raise ValidationError(
            f"coordinate {value} is outside [{axis[0]}, {axis[-1]}]"
        )
    high = bisect.bisect_left(axis, value)
    if high < len(axis) and value == axis[high]:
        return high, high, 0.0
    low = high - 1
    fraction = (value - axis[low]) / (axis[high] - axis[low])
    return low, high, fraction


def _bracket_weights(
    bracket: tuple[int, int, float],
) -> tuple[tuple[int, float], ...]:
    low, high, fraction = bracket
    if low == high:
        return ((low, 1.0),)
    return ((low, 1.0 - fraction), (high, fraction))


def _piecewise_linear(
    x_values: tuple[float, ...],
    y_values: tuple[float, ...],
    x_value: float,
) -> float:
    high = bisect.bisect_right(x_values, x_value)
    if high == 0 or high == len(x_values):
        raise ValidationError("color-warp wavelength is out of domain")
    low = high - 1
    fraction = (
        (x_value - x_values[low])
        / (x_values[high] - x_values[low])
    )
    return y_values[low] + fraction * (
        y_values[high] - y_values[low]
    )


class IndependentVisibilityPack:
    """Separate exact-pack evaluator used only by the external oracle."""

    def __init__(self, directory: Path, expected_manifest_sha256: str) -> None:
        manifest_path = directory / MANIFEST_NAME
        if (
            not directory.is_dir()
            or directory.is_symlink()
            or not manifest_path.is_file()
            or _sha256(manifest_path) != expected_manifest_sha256
        ):
            raise ValidationError("exact visibility-pack identity differs")
        manifest = _json(manifest_path, "visibility-pack manifest")
        if (
            manifest.get("pack_id")
            != "moira-physical-heliacal-visibility"
            or manifest.get("version") != "1.2.0"
            or manifest.get("status") != "complete_immutable_data_pack"
        ):
            raise ValidationError("visibility-pack contract differs")
        roles = manifest.get("file_roles")
        if not isinstance(roles, dict):
            raise ValidationError("visibility-pack roles differ")
        axes = _json(directory / roles["axes"], "visibility-pack axes")
        radiance = axes.get("radiance")
        direct = axes.get("direct_extinction")
        if not isinstance(radiance, dict) or not isinstance(direct, dict):
            raise ValidationError("visibility-pack axis contract differs")
        raw_radiance_axes = radiance.get("axes")
        if (
            not isinstance(raw_radiance_axes, dict)
            or radiance.get("coordinate_order")
            != [
                "solar_center_altitude_deg",
                "target_true_altitude_deg",
                "relative_solar_azimuth_deg",
            ]
        ):
            raise ValidationError("radiance coordinate order differs")
        self.solar_axis = _strict_axis(
            raw_radiance_axes["solar_center_altitude_deg"],
            "solar altitude",
        )
        self.target_radiance_axis = _strict_axis(
            raw_radiance_axes["target_true_altitude_deg"],
            "target radiance altitude",
        )
        self.azimuth_axis = _strict_axis(
            raw_radiance_axes["relative_solar_azimuth_deg"],
            "relative solar azimuth",
        )
        self.direct_target_axis = _strict_axis(
            direct["target_true_altitude_deg"],
            "direct target altitude",
        )
        radiance_count = (
            len(self.solar_axis)
            * len(self.target_radiance_axis)
            * len(self.azimuth_axis)
        )
        if (
            radiance.get("value_count") != radiance_count
            or direct.get("value_count")
            != len(self.direct_target_axis) * 400
        ):
            raise ValidationError("visibility-pack table shape differs")
        self.photopic_luminance = _f32(
            directory / roles["photopic_luminance"],
            radiance_count,
        )
        self.scotopic_luminance = _f32(
            directory / roles["scotopic_luminance"],
            radiance_count,
        )
        self.direct_extinction = _f32(
            directory / roles["direct_extinction"],
            direct["value_count"],
        )
        planetary = _json(
            directory / roles["target_profiles"],
            "planetary target profiles",
        )
        stellar = _json(
            directory / roles["stellar_target_profiles"],
            "stellar target profiles",
        )
        self.planetary_profiles = {
            profile["target_id"]: profile
            for profile in planetary["profiles"]
        }
        self.stellar_profiles = {
            profile["target_id"]: profile
            for profile in stellar["profiles"]
        }

    def _trilinear_log10(
        self,
        values: tuple[float, ...],
        *,
        solar_altitude_deg: float,
        target_altitude_deg: float,
        relative_azimuth_deg: float,
    ) -> float:
        brackets = (
            _bracket(self.solar_axis, solar_altitude_deg),
            _bracket(self.target_radiance_axis, target_altitude_deg),
            _bracket(self.azimuth_axis, relative_azimuth_deg),
        )
        shape = (
            len(self.solar_axis),
            len(self.target_radiance_axis),
            len(self.azimuth_axis),
        )
        weighted_log10 = 0.0
        weight_sum = 0.0
        for solar_index, solar_weight in _bracket_weights(brackets[0]):
            for target_index, target_weight in _bracket_weights(
                brackets[1]
            ):
                for azimuth_index, azimuth_weight in _bracket_weights(
                    brackets[2]
                ):
                    weight = (
                        solar_weight * target_weight * azimuth_weight
                    )
                    index = (
                        (solar_index * shape[1] + target_index)
                        * shape[2]
                        + azimuth_index
                    )
                    weighted_log10 += weight * math.log10(values[index])
                    weight_sum += weight
        if not math.isclose(
            weight_sum,
            1.0,
            rel_tol=0.0,
            abs_tol=1.0e-15,
        ):
            raise ValidationError("trilinear weights do not sum to one")
        return 10.0**weighted_log10

    def _direct_transmission(
        self,
        target_altitude_deg: float,
    ) -> tuple[float, ...]:
        transformed_axis = tuple(
            math.log10(value + 0.25)
            for value in self.direct_target_axis
        )
        if target_altitude_deg <= -0.25:
            raise ValidationError("direct target altitude is out of domain")
        low, high, fraction = _bracket(
            transformed_axis,
            math.log10(target_altitude_deg + 0.25),
        )
        bin_count = len(SPECTRAL_WAVELENGTHS_NM)
        result: list[float] = []
        for spectral_bin in range(bin_count):
            low_value = self.direct_extinction[
                low * bin_count + spectral_bin
            ]
            extinction = (
                low_value
                if low == high
                else low_value
                + fraction
                * (
                    self.direct_extinction[
                        high * bin_count + spectral_bin
                    ]
                    - low_value
                )
            )
            result.append(10.0 ** (-0.4 * extinction))
        return tuple(result)

    def _target_profile(
        self,
        target: str,
        phase_angle_deg: float | None,
    ) -> tuple[float, tuple[float, ...], tuple[float, ...]]:
        if target == "Sirius":
            profile = self.stellar_profiles[target]
            return (
                float(profile["base_scotopic_to_photopic_ratio"]),
                tuple(profile["base_photopic_extinction_weights"]),
                tuple(profile["base_scotopic_extinction_weights"]),
            )
        if target != "Jupiter" or phase_angle_deg is None:
            raise ValidationError("unsupported independent target profile")
        profile = self.planetary_profiles[target]
        color = profile["color_model"]
        lower, upper = color["phase_angle_domain_deg"]
        if not lower <= phase_angle_deg <= upper:
            raise ValidationError("Jupiter phase angle is out of domain")
        band_values = tuple(
            math.fsum(
                coefficient * phase_angle_deg**power
                for power, coefficient in enumerate(coefficients, start=1)
            )
            for coefficients in color["coefficients_by_band"]
        )
        visual_value = band_values[2]
        differential = tuple(
            value - visual_value for value in band_values
        )
        logarithmic = tuple(
            -0.4
            * math.log(10.0)
            * _piecewise_linear(
                BAND_WAVELENGTHS_NM,
                differential,
                wavelength,
            )
            for wavelength in SPECTRAL_WAVELENGTHS_NM
        )
        maximum = max(logarithmic)
        correction = tuple(
            math.exp(value - maximum) for value in logarithmic
        )
        base_photopic = tuple(
            profile["base_photopic_extinction_weights"]
        )
        base_scotopic = tuple(
            profile["base_scotopic_extinction_weights"]
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
            raise ValidationError("Jupiter response integral is nonpositive")
        return (
            float(profile["base_scotopic_to_photopic_ratio"])
            * scotopic_scale
            / photopic_scale,
            tuple(
                weight * factor / photopic_scale
                for weight, factor in zip(base_photopic, correction)
            ),
            tuple(
                weight * factor / scotopic_scale
                for weight, factor in zip(base_scotopic, correction)
            ),
        )

    def margin(
        self,
        *,
        target: str,
        target_azimuth_deg: float,
        target_altitude_deg: float,
        solar_azimuth_deg: float,
        solar_altitude_deg: float,
        apparent_magnitude: float,
        phase_angle_deg: float | None,
        dark_sky_photopic_cd_m2: float,
        dark_sky_scotopic_cd_m2: float,
    ) -> float:
        relative_azimuth = abs(
            (
                target_azimuth_deg
                - solar_azimuth_deg
                + 180.0
            )
            % 360.0
            - 180.0
        )
        photopic_background = (
            self._trilinear_log10(
                self.photopic_luminance,
                solar_altitude_deg=solar_altitude_deg,
                target_altitude_deg=target_altitude_deg,
                relative_azimuth_deg=relative_azimuth,
            )
            + dark_sky_photopic_cd_m2
        )
        scotopic_background = (
            self._trilinear_log10(
                self.scotopic_luminance,
                solar_altitude_deg=solar_altitude_deg,
                target_altitude_deg=target_altitude_deg,
                relative_azimuth_deg=relative_azimuth,
            )
            + dark_sky_scotopic_cd_m2
        )
        adaptation, mesopic_background = _cie_mes2(
            photopic_background,
            scotopic_background,
        )
        limiting_magnitude = _crumey_limiting_magnitude(
            mesopic_background
        )
        ratio, photopic_weights, scotopic_weights = self._target_profile(
            target,
            phase_angle_deg,
        )
        transmission = self._direct_transmission(target_altitude_deg)
        photopic_transmission = math.fsum(
            weight * value
            for weight, value in zip(photopic_weights, transmission)
        )
        scotopic_transmission = math.fsum(
            weight * value
            for weight, value in zip(scotopic_weights, transmission)
        )
        top_photopic = CRUMEY_ZERO_POINT_LUX * 10.0 ** (
            -0.4 * apparent_magnitude
        )
        conditioned_mesopic = _mesopic_quantity(
            top_photopic * photopic_transmission,
            (
                top_photopic
                * ratio
                * scotopic_transmission
            ),
            adaptation,
        )
        conditioned_magnitude = -2.5 * math.log10(
            conditioned_mesopic / CRUMEY_ZERO_POINT_LUX
        )
        return limiting_magnitude - conditioned_magnitude


def _mesopic_quantity(
    photopic: float,
    scotopic: float,
    coefficient: float,
) -> float:
    return (
        coefficient * photopic
        + (1.0 - coefficient) * scotopic * CIE_V_PRIME_555
    ) / (
        coefficient + (1.0 - coefficient) * CIE_V_PRIME_555
    )


def _mes2_coefficient(mesopic: float) -> float:
    if mesopic <= 0.005:
        return 0.0
    if mesopic >= 5.0:
        return 1.0
    return min(
        1.0,
        max(0.0, 0.7670 + 0.3334 * math.log10(mesopic)),
    )


def _cie_mes2(
    photopic: float,
    scotopic: float,
) -> tuple[float, float]:
    coefficient = 0.5
    for _iteration in range(1, 101):
        mesopic = _mesopic_quantity(
            photopic,
            scotopic,
            coefficient,
        )
        updated = _mes2_coefficient(mesopic)
        if abs(updated - coefficient) <= 1.0e-12:
            return (
                updated,
                _mesopic_quantity(
                    photopic,
                    scotopic,
                    updated,
                ),
            )
        coefficient = updated
    raise ValidationError("independent CIE MES2 solver did not converge")


def _crumey_limiting_magnitude(background: float) -> float:
    if not 3.426e-5 <= background <= 3426.0:
        raise ValidationError("Crumey background is out of domain")
    radicand = (
        5.949e-8 * background**0.5
        - 2.389e-7 * background**0.75
        + 2.459e-7 * background
    )
    if radicand < 0.0:
        raise ValidationError("Crumey radicand is negative")
    base_threshold = (
        math.sqrt(radicand)
        + 4.120e-4 * background**0.25
        - 4.225e-4 * background**0.5
    ) ** 2
    threshold = 2.0 * base_threshold
    if threshold <= 0.0 or not math.isfinite(threshold):
        raise ValidationError("Crumey threshold is invalid")
    return -2.5 * math.log10(
        threshold / CRUMEY_ZERO_POINT_LUX
    )


def _horizons_rows(
    path: Path,
    *,
    target_fields: bool,
) -> tuple[ObserverRow, ...]:
    response = _json(path, "JPL Horizons response")
    result = response.get("result")
    signature = response.get("signature")
    if (
        not isinstance(result, str)
        or not isinstance(signature, dict)
        or "$$SOE" not in result
        or "$$EOE" not in result
    ):
        raise ValidationError("JPL Horizons response contract differs")
    lines = result.splitlines()
    start = lines.index("$$SOE") + 1
    stop = lines.index("$$EOE")
    rows: list[ObserverRow] = []
    for fields in csv.reader(lines[start:stop]):
        try:
            rows.append(
                ObserverRow(
                    jd_ut=float(fields[1]),
                    azimuth_deg=float(fields[4]),
                    altitude_deg=float(fields[5]),
                    apparent_magnitude=(
                        float(fields[6]) if target_fields else None
                    ),
                    phase_angle_deg=(
                        float(fields[8]) if target_fields else None
                    ),
                )
            )
        except (IndexError, ValueError) as exc:
            raise ValidationError(
                f"JPL Horizons row differs in {path.name}"
            ) from exc
    if len(rows) < 2 or any(
        right.jd_ut <= left.jd_ut
        for left, right in zip(rows, rows[1:])
    ):
        raise ValidationError(
            f"JPL Horizons time grid differs in {path.name}"
        )
    return tuple(rows)


def _paired_rows(
    target_rows: tuple[ObserverRow, ...],
    solar_rows: tuple[ObserverRow, ...],
) -> tuple[tuple[ObserverRow, ObserverRow], ...]:
    if (
        len(target_rows) != len(solar_rows)
        or any(
            target.jd_ut != solar.jd_ut
            for target, solar in zip(target_rows, solar_rows)
        )
    ):
        raise ValidationError("target and solar Horizons grids differ")
    return tuple(zip(target_rows, solar_rows))


def _hipparcos_sirius(path: Path) -> dict[str, Any]:
    try:
        rows = tuple(
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith(" 32349\t")
        )
    except (OSError, UnicodeError) as exc:
        raise ValidationError("invalid Hipparcos Sirius query") from exc
    if len(rows) != 1:
        raise ValidationError("Hipparcos Sirius row count differs")
    fields = rows[0].split("\t")
    if len(fields) != 7:
        raise ValidationError("Hipparcos Sirius columns differ")
    try:
        result = {
            "hipparcos_id": int(fields[0].strip()),
            "ra_icrs_j1991_25": fields[1].strip(),
            "dec_icrs_j1991_25": fields[2].strip(),
            "parallax_mas": float(fields[3].strip()),
            "pm_ra_cos_dec_mas_per_year": float(fields[4].strip()),
            "pm_dec_mas_per_year": float(fields[5].strip()),
            "catalog_v_magnitude": float(fields[6].strip()),
        }
    except ValueError as exc:
        raise ValidationError("Hipparcos Sirius values differ") from exc
    return result


def _sirius_rows(
    solar_rows: tuple[ObserverRow, ...],
    *,
    astrometry: dict[str, Any],
    latitude_deg: float,
    longitude_deg: float,
) -> tuple[ObserverRow, ...]:
    try:
        import astropy.units as units
        from astropy.coordinates import (
            AltAz,
            Distance,
            EarthLocation,
            SkyCoord,
        )
        from astropy.time import Time
        from astropy.utils import iers
    except ImportError as exc:
        raise ValidationError(
            "independent Sirius validation requires dev Astropy"
        ) from exc
    iers.conf.auto_download = False
    iers.conf.auto_max_age = None
    star = SkyCoord(
        ra=astrometry["ra_icrs_j1991_25"].replace(" ", "h", 1).replace(
            " ",
            "m",
            1,
        )
        + "s",
        dec=(
            astrometry["dec_icrs_j1991_25"]
            .replace(" ", "d", 1)
            .replace(" ", "m", 1)
            + "s"
        ),
        distance=Distance(
            parallax=astrometry["parallax_mas"] * units.mas
        ),
        pm_ra_cosdec=(
            astrometry["pm_ra_cos_dec_mas_per_year"]
            * units.mas
            / units.yr
        ),
        pm_dec=(
            astrometry["pm_dec_mas_per_year"]
            * units.mas
            / units.yr
        ),
        radial_velocity=0.0 * units.km / units.s,
        frame="icrs",
        obstime=Time("J1991.25"),
    )
    location = EarthLocation.from_geodetic(
        lon=longitude_deg * units.deg,
        lat=latitude_deg * units.deg,
        height=0.0 * units.m,
    )
    result: list[ObserverRow] = []
    for solar in solar_rows:
        time = Time(solar.jd_ut, format="jd", scale="utc")
        horizontal = star.apply_space_motion(
            new_obstime=time
        ).transform_to(
            AltAz(
                obstime=time,
                location=location,
                pressure=0.0 * units.hPa,
            )
        )
        result.append(
            ObserverRow(
                jd_ut=solar.jd_ut,
                azimuth_deg=float(horizontal.az.deg),
                altitude_deg=float(horizontal.alt.deg),
                apparent_magnitude=-1.46,
                phase_angle_deg=None,
            )
        )
    return tuple(result)


def _in_domain_margins(
    pack: IndependentVisibilityPack,
    *,
    target: str,
    pairs: tuple[tuple[ObserverRow, ObserverRow], ...],
    background: dict[str, Any],
) -> tuple[MarginRow, ...]:
    result: list[MarginRow] = []
    for target_row, solar_row in pairs:
        if not (
            pack.target_radiance_axis[0]
            <= target_row.altitude_deg
            <= pack.target_radiance_axis[-1]
            and pack.solar_axis[0]
            <= solar_row.altitude_deg
            <= pack.solar_axis[-1]
        ):
            continue
        if target_row.apparent_magnitude is None:
            raise ValidationError("target magnitude is missing")
        result.append(
            MarginRow(
                jd_ut=target_row.jd_ut,
                margin_magnitude=pack.margin(
                    target=target,
                    target_azimuth_deg=target_row.azimuth_deg,
                    target_altitude_deg=target_row.altitude_deg,
                    solar_azimuth_deg=solar_row.azimuth_deg,
                    solar_altitude_deg=solar_row.altitude_deg,
                    apparent_magnitude=target_row.apparent_magnitude,
                    phase_angle_deg=target_row.phase_angle_deg,
                    dark_sky_photopic_cd_m2=background[
                        "photopic_luminance_cd_m2"
                    ],
                    dark_sky_scotopic_cd_m2=background[
                        "scotopic_luminance_cd_m2"
                    ],
                ),
            )
        )
    if len(result) < 2:
        raise ValidationError("external oracle has too few in-domain rows")
    return tuple(result)


def _opening_crossing(
    rows: tuple[MarginRow, ...],
) -> tuple[MarginRow, MarginRow, float]:
    for left, right in zip(rows, rows[1:]):
        if left.margin_magnitude < 0.0 <= right.margin_magnitude:
            fraction = (
                -left.margin_magnitude
                / (right.margin_magnitude - left.margin_magnitude)
            )
            root = left.jd_ut + fraction * (
                right.jd_ut - left.jd_ut
            )
            return left, right, root
    raise ValidationError("independent opening crossing is missing")


def _assert_seconds(
    actual_jd: float,
    expected_jd: float,
    tolerance_seconds: float,
    label: str,
) -> None:
    difference = abs(actual_jd - expected_jd) * 86400.0
    if difference > tolerance_seconds:
        raise ValidationError(
            f"{label} differs by {difference} seconds"
        )


def _validate_toolchain(
    declaration: dict[str, Any],
) -> None:
    try:
        import astropy
        import erfa
        from astropy.utils import iers
    except ImportError as exc:
        raise ValidationError("Astropy/ERFA toolchain is missing") from exc
    if (
        astropy.__version__ != declaration["astropy_version"]
        or erfa.__version__ != declaration["pyerfa_version"]
        or importlib.metadata.version("astropy-iers-data")
        != declaration["astropy_iers_data_version"]
    ):
        raise ValidationError("Astropy/ERFA version receipt differs")
    iers.conf.auto_download = False
    table = iers.earth_orientation_table.get()
    for role, metadata_key in (
        ("iers_finals2000a", "data_path"),
        ("iers_readme", "readme_path"),
    ):
        path = Path(table.meta[metadata_key])
        _verify_file(path, declaration[role], role)


def validate(
    *,
    golden_path: Path,
    pack_path: Path,
    jpl_root: Path,
    hipparcos_query: Path,
    hipparcos_readme: Path,
) -> dict[str, Any]:
    golden = _json(golden_path, "Phase 3 event golden")
    if (
        golden.get("schema")
        != "moira.physical-heliacal-visibility-phase3-event-goldens/v1"
        or golden.get("status")
        != "independent_planetary_and_stellar_event_validation"
    ):
        raise ValidationError("Phase 3 event golden contract differs")
    exact_pack = golden["exact_data_pack"]
    pack = IndependentVisibilityPack(
        pack_path,
        exact_pack["manifest_sha256"],
    )
    background = golden["policy"]["background"]
    if (
        background.get("scope") != "dark_sky_anchor"
        or golden["policy"]["atmosphere"]
        != "exact_data_pack_fixed_domain"
    ):
        raise ValidationError("event-golden policy differs")

    external = golden["external_sources"]
    horizons_files = external["jpl_horizons"]["files"]
    source_paths: dict[str, Path] = {}
    for source_id, receipt in horizons_files.items():
        path = jpl_root / receipt["filename"]
        _verify_file(path, receipt, source_id)
        source_paths[source_id] = path
    hipparcos = external["hipparcos"]
    _verify_file(
        hipparcos_query,
        hipparcos["query"],
        "Hipparcos Sirius query",
    )
    _verify_file(
        hipparcos_readme,
        hipparcos["readme"],
        "Hipparcos ReadMe",
    )
    astrometry = _hipparcos_sirius(hipparcos_query)
    admitted_astrometry = dict(hipparcos["admitted_astrometry"])
    catalog_v_not_used = admitted_astrometry.pop(
        "catalog_v_magnitude_not_used"
    )
    radial_velocity = admitted_astrometry.pop(
        "radial_velocity_assumption_km_per_s"
    )
    source_astrometry = dict(astrometry)
    catalog_v_magnitude = source_astrometry.pop("catalog_v_magnitude")
    if (
        source_astrometry != admitted_astrometry
        or radial_velocity != 0.0
        or catalog_v_not_used is not True
        or catalog_v_magnitude != -1.44
    ):
        raise ValidationError("Hipparcos astrometry receipt differs")
    _validate_toolchain(external["astropy_erfa"])

    results: list[dict[str, Any]] = []
    for case in golden["cases"]:
        target = case["target"]
        if target == "Jupiter":
            candidate_pairs = _paired_rows(
                _horizons_rows(
                    source_paths[case["candidate_sources"][0]],
                    target_fields=True,
                ),
                _horizons_rows(
                    source_paths[case["candidate_sources"][1]],
                    target_fields=False,
                ),
            )
            guard_pairs = _paired_rows(
                _horizons_rows(
                    source_paths[case["guard_sources"][0]],
                    target_fields=True,
                ),
                _horizons_rows(
                    source_paths[case["guard_sources"][1]],
                    target_fields=False,
                ),
            )
        elif target == "Sirius":
            candidate_sun = _horizons_rows(
                source_paths[case["candidate_sources"][0]],
                target_fields=False,
            )
            guard_sun = _horizons_rows(
                source_paths[case["guard_sources"][0]],
                target_fields=False,
            )
            candidate_pairs = _paired_rows(
                _sirius_rows(
                    candidate_sun,
                    astrometry=astrometry,
                    latitude_deg=case["latitude_deg"],
                    longitude_deg=case["longitude_deg"],
                ),
                candidate_sun,
            )
            guard_pairs = _paired_rows(
                _sirius_rows(
                    guard_sun,
                    astrometry=astrometry,
                    latitude_deg=case["latitude_deg"],
                    longitude_deg=case["longitude_deg"],
                ),
                guard_sun,
            )
        else:
            raise ValidationError("unsupported event-golden target")

        candidate_margins = _in_domain_margins(
            pack,
            target=target,
            pairs=candidate_pairs,
            background=background,
        )
        guard_margins = _in_domain_margins(
            pack,
            target=target,
            pairs=guard_pairs,
            background=background,
        )
        guard_maximum = max(
            row.margin_magnitude for row in guard_margins
        )
        oracle = case["independent_oracle"]
        if (
            guard_maximum >= 0.0
            or oracle["guard_day_status"] != "does_not_qualify"
        ):
            raise ValidationError(
                f"{case['case_id']} guard day qualifies"
            )
        left, right, root = _opening_crossing(candidate_margins)
        bracket_jd = oracle["crossing_bracket_jd_ut"]
        bracket_margin = oracle["crossing_bracket_margin_magnitude"]
        reproduction_seconds = oracle[
            "oracle_reproduction_tolerance_seconds"
        ]
        _assert_seconds(
            left.jd_ut,
            bracket_jd[0],
            reproduction_seconds,
            f"{case['case_id']} left bracket",
        )
        _assert_seconds(
            right.jd_ut,
            bracket_jd[1],
            reproduction_seconds,
            f"{case['case_id']} right bracket",
        )
        for actual, expected, side in (
            (left.margin_magnitude, bracket_margin[0], "left"),
            (right.margin_magnitude, bracket_margin[1], "right"),
        ):
            if not math.isclose(
                actual,
                expected,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise ValidationError(
                    f"{case['case_id']} {side} margin differs"
                )
        _assert_seconds(
            root,
            oracle["event_jd_ut"],
            reproduction_seconds,
            f"{case['case_id']} independent root",
        )
        engine = case["engine_result"]
        if (
            engine.get("status") != "evaluated"
            or engine.get("comparison_day_status")
            != "does_not_qualify"
            or engine.get("event_time_semantics")
            != "visibility_margin_zero"
            or engine.get("boundary_source") != "visibility_margin"
            or engine.get("crossing_completeness_state")
            != "certified_lipschitz_zero_enclosure"
            or engine.get("crossing_certificate_source_sha256")
            != (
                "eacf8c373606c1628cebdd4caa611ece5"
                "33d368c32c7f86674a13e04a4c13d3e"
            )
            or engine.get("unresolved_certificate_interval_count") != 0
        ):
            raise ValidationError(
                f"{case['case_id']} engine receipt differs"
            )
        _assert_seconds(
            engine["event_jd_ut"],
            root,
            case["maximum_engine_oracle_difference_seconds"],
            f"{case['case_id']} engine/oracle comparison",
        )
        results.append(
            {
                "case_id": case["case_id"],
                "target": target,
                "guard_maximum_margin_magnitude": guard_maximum,
                "independent_event_jd_ut": root,
                "engine_event_jd_ut": engine["event_jd_ut"],
                "absolute_difference_seconds": (
                    abs(engine["event_jd_ut"] - root) * 86400.0
                ),
                "maximum_difference_seconds": case[
                    "maximum_engine_oracle_difference_seconds"
                ],
                "status": "accepted",
            }
        )

    if {result["target"] for result in results} != {
        "Jupiter",
        "Sirius",
    }:
        raise ValidationError(
            "planetary and stellar validation coverage differs"
        )
    return {
        "status": "accepted",
        "golden_sha256": _sha256(golden_path),
        "pack_manifest_sha256": exact_pack["manifest_sha256"],
        "cases": results,
        "network_used": False,
        "moira_or_event_solver_imported": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--jpl-root", type=Path, required=True)
    parser.add_argument("--hipparcos-query", type=Path, required=True)
    parser.add_argument("--hipparcos-readme", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = validate(
            golden_path=arguments.golden.resolve(),
            pack_path=arguments.pack.resolve(),
            jpl_root=arguments.jpl_root.resolve(),
            hipparcos_query=arguments.hipparcos_query.resolve(),
            hipparcos_readme=arguments.hipparcos_readme.resolve(),
        )
    except (
        OSError,
        ValidationError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

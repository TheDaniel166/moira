"""Pinned, fail-closed resources for sovereign lunar orientation."""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Sequence

from . import moira_native
from ._kernel_paths import find_kernel


class LunarOrientationResourceError(RuntimeError):
    """Base error for absent, drifted, or unsupported orientation assets."""


class LunarOrientationResourceMissingError(LunarOrientationResourceError):
    """Raised when an admitted orientation asset is not installed."""


class LunarOrientationResourceIdentityError(LunarOrientationResourceError):
    """Raised when an installed asset does not match its pinned identity."""


class LunarOrientationCoverageError(LunarOrientationResourceError):
    """Raised when the requested epoch is outside admitted PCK coverage."""


@dataclass(frozen=True, slots=True)
class LunarOrientationResources:
    """Validated PCK resources and frame metadata for lunar orientation."""

    handle: object
    pck_path: Path
    frame_kernel_path: Path
    pck_sha256: str
    frame_kernel_sha256: str
    orientation_model: str
    pa_frame_name: str
    pa_frame_id: int
    target_frame_name: str
    target_frame_id: int
    pa_to_me_matrix: tuple[tuple[float, float, float], ...]
    coverage_start_jd_tdb: float
    coverage_end_jd_tdb: float


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LunarOrientationResourceIdentityError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise LunarOrientationResourceIdentityError(f"{name} must be finite")
    return result


@lru_cache(maxsize=1)
def _manifest() -> dict[str, object]:
    try:
        payload = json.loads(
            files("moira.data")
            .joinpath("lunar_orientation_de440.json")
            .read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise LunarOrientationResourceIdentityError(
            "packaged lunar-orientation manifest is unreadable"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise LunarOrientationResourceIdentityError(
            "unsupported lunar-orientation manifest schema"
        )
    for key in ("pck", "frame_kernel", "target_frame", "orientation_model"):
        if key not in payload:
            raise LunarOrientationResourceIdentityError(
                f"lunar-orientation manifest is missing {key!r}"
            )
    return payload


def _legacy_lunar_limb_path(filename: str) -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Moira" / "lunar_limb" / "kernels" / filename
    return Path.home() / ".cache" / "moira" / "lunar_limb" / "kernels" / filename


def _resolve_resource(filename: str) -> Path:
    primary = find_kernel(filename)
    if primary.is_file():
        return primary
    legacy = _legacy_lunar_limb_path(filename)
    if legacy.is_file():
        return legacy
    raise LunarOrientationResourceMissingError(
        f"required lunar-orientation resource is not installed: {filename}; "
        "run moira-download-kernels --lunar-orientation"
    )


@lru_cache(maxsize=8)
def _verified_identity(path_text: str, expected_bytes: int, expected_sha256: str) -> str:
    path = Path(path_text)
    try:
        byte_length = path.stat().st_size
    except OSError as exc:
        raise LunarOrientationResourceMissingError(
            f"required lunar-orientation resource is unavailable: {path.name}"
        ) from exc
    if byte_length != expected_bytes:
        raise LunarOrientationResourceIdentityError(
            f"lunar-orientation resource byte length mismatch: {path.name}"
        )
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise LunarOrientationResourceIdentityError(
            f"lunar-orientation resource could not be hashed: {path.name}"
        ) from exc
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise LunarOrientationResourceIdentityError(
            f"lunar-orientation resource SHA-256 mismatch: {path.name}"
        )
    return actual


def _matrix(value: object) -> tuple[tuple[float, float, float], ...]:
    if not isinstance(value, list) or len(value) != 3:
        raise LunarOrientationResourceIdentityError("PA-to-ME matrix must be 3x3")
    rows = tuple(
        tuple(_finite_number("PA-to-ME matrix value", item) for item in row)
        for row in value
        if isinstance(row, list) and len(row) == 3
    )
    if len(rows) != 3:
        raise LunarOrientationResourceIdentityError("PA-to-ME matrix must be 3x3")
    for left in range(3):
        for right in range(3):
            dot = sum(rows[left][axis] * rows[right][axis] for axis in range(3))
            expected = 1.0 if left == right else 0.0
            if not math.isclose(dot, expected, rel_tol=0.0, abs_tol=2.0e-15):
                raise LunarOrientationResourceIdentityError(
                    "PA-to-ME matrix is not orthonormal"
                )
    return rows


@lru_cache(maxsize=1)
def lunar_orientation_resources() -> LunarOrientationResources:
    manifest = _manifest()
    pck = manifest["pck"]
    frame_kernel = manifest["frame_kernel"]
    target = manifest["target_frame"]
    if not isinstance(pck, dict) or not isinstance(frame_kernel, dict) or not isinstance(target, dict):
        raise LunarOrientationResourceIdentityError(
            "lunar-orientation manifest resource entries must be objects"
        )
    if (
        pck.get("frame_class_id") != 31008
        or pck.get("inertial_frame_id") != 1
        or pck.get("data_type") != 2
        or pck.get("frame_name") != "MOON_PA_DE440"
        or target.get("frame_id") != 31009
        or target.get("frame_name") != "MOON_ME_DE440_ME421"
        or target.get("relative_frame") != "MOON_PA_DE440"
        or target.get("axes") != [3, 2, 1]
        or target.get("direction") != "relative_frame_to_target_frame"
    ):
        raise LunarOrientationResourceIdentityError(
            "lunar-orientation manifest frame contract is not admitted"
        )
    pck_path = _resolve_resource(str(pck["filename"]))
    frame_path = _resolve_resource(str(frame_kernel["filename"]))
    pck_digest = _verified_identity(
        str(pck_path.resolve()), int(pck["byte_length"]), str(pck["sha256"])
    )
    frame_digest = _verified_identity(
        str(frame_path.resolve()),
        int(frame_kernel["byte_length"]),
        str(frame_kernel["sha256"]),
    )
    try:
        handle = moira_native.open_pck_kernel(str(pck_path))
        catalog = handle.catalog()
        coverage = tuple(float(value) for value in handle.coverage(31008))
    except Exception as exc:
        raise LunarOrientationResourceIdentityError(
            "admitted lunar binary PCK could not be opened"
        ) from exc
    summaries = catalog.get("summaries", [])
    if not summaries or any(
        tuple(item.get("descriptor", ()))[2:5] != (31008, 1, 2)
        for item in summaries
    ):
        handle.close()
        raise LunarOrientationResourceIdentityError(
            "admitted lunar binary PCK descriptor contract is not satisfied"
        )
    return LunarOrientationResources(
        handle=handle,
        pck_path=pck_path,
        frame_kernel_path=frame_path,
        pck_sha256=pck_digest,
        frame_kernel_sha256=frame_digest,
        orientation_model=str(manifest["orientation_model"]),
        pa_frame_name=str(pck["frame_name"]),
        pa_frame_id=int(pck["frame_class_id"]),
        target_frame_name=str(target["frame_name"]),
        target_frame_id=int(target["frame_id"]),
        pa_to_me_matrix=_matrix(target["matrix"]),
        coverage_start_jd_tdb=coverage[0],
        coverage_end_jd_tdb=coverage[1],
    )


def _multiply(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        tuple(sum(left[row][axis] * right[axis][column] for axis in range(3)) for column in range(3))
        for row in range(3)
    )


def lunar_me_rotation(jd_tdb: float) -> tuple[tuple[float, float, float], ...]:
    epoch = _finite_number("jd_tdb", jd_tdb)
    resources = lunar_orientation_resources()
    if not resources.coverage_start_jd_tdb <= epoch <= resources.coverage_end_jd_tdb:
        raise LunarOrientationCoverageError(
            "lunar orientation epoch is outside moon_pa_de440_200625.bpc coverage"
        )
    try:
        j2000_to_pa = resources.handle.rotation_matrix(epoch, resources.pa_frame_id)
    except (IndexError, ValueError, OverflowError) as exc:
        raise LunarOrientationCoverageError(
            "lunar orientation epoch is outside binary PCK coverage"
        ) from exc
    return _multiply(resources.pa_to_me_matrix, j2000_to_pa)


__all__ = [
    "LunarOrientationCoverageError",
    "LunarOrientationResourceError",
    "LunarOrientationResourceIdentityError",
    "LunarOrientationResourceMissingError",
]

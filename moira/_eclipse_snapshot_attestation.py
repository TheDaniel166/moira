"""Verify a caller-pinned build receipt and immutable SPK snapshot.

The manifest is a trust input, not something the extension generates about
itself. Hashing an imported module's current backing path cannot establish the
bytes already loaded into memory after a file replacement. This verifier
therefore does not certify the loaded image or any live memory-mapped file.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from ._eclipse_native_spk_bounds import ConditionalNativeType2Bounds, _snapshot_hash
from ._eclipse_spk_bounds import EclipseSpkBoundsUnavailable

_REQUIRED_SOURCES = frozenset({
    "CMakeLists.txt",
    "src/native/bindings/moira_native.cpp",
    "src/native/include/eclipse_strict_snapshot.hpp",
    "src/native/src/eclipse_strict_snapshot.cpp",
})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_ARTIFACT_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class TrustedSnapshotManifest:
    """Externally pinned receipt; callers must establish its trust separately."""

    binary_sha256: str
    snapshot_sha256: str
    build_log_sha256: str
    compile_command: str
    source_sha256: tuple[tuple[str, str], ...]
    compiler_profile: str = "msvc-strict-v1"


@dataclass(frozen=True, slots=True)
class SnapshotManifestVerification:
    """Verified disk and record identities, with explicit proof limitations."""

    binary_path: str
    binary_sha256: str
    snapshot_sha256: str
    current_disk_binary_verified: bool = True
    pinned_build_evidence_verified: bool = True
    build_provenance_verified: bool = False
    source_at_compile_verified: bool = False
    loaded_image_verified: bool = False
    live_mapped_source_verified: bool = False
    legacy_evaluator_certified: bool = False
    trusted_manifest_required: bool = True


def _read_bounded(path: Path) -> bytes:
    try:
        with path.open("rb") as stream:
            data = stream.read(_MAX_ARTIFACT_BYTES + 1)
    except OSError as exc:
        raise EclipseSpkBoundsUnavailable(f"receipt artifact unavailable: {path}") from exc
    if len(data) > _MAX_ARTIFACT_BYTES:
        raise EclipseSpkBoundsUnavailable("receipt artifact exceeds verification budget")
    return data


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_msvc_command(command: str) -> None:
    # Inspect visible switches only. Environment CL/_CL_, forced includes,
    # compiler execution and linkage are not established by this transcript.
    if "\n" in command or "\r" in command:
        raise EclipseSpkBoundsUnavailable("compile command must be one line")
    tokens = re.findall(r'"[^"]*"|\S+', command)
    lower = [token.strip('"').lower() for token in tokens]
    if any(token.startswith('@') or '%' in token or '$' in token for token in lower):
        raise EclipseSpkBoundsUnavailable("opaque or expanded compile arguments are unsupported")
    if not lower or not re.search(r"(?:^|[\\/])cl(?:\.exe)?$", lower[0]):
        raise EclipseSpkBoundsUnavailable("unrecognized strict compiler command")
    lower[1:] = ["/" + token[1:] if token.startswith("-") else token for token in lower[1:]]
    fp = [token for token in lower if token.startswith("/fp:")]
    gl = [token for token in lower if token in ("/gl", "/gl-")]
    macro = "moira_eclipse_strict_snapshot_build=1"
    defined = any(token == "/d" + macro or (token == macro and index > 0 and lower[index - 1] == "/d")
                  for index, token in enumerate(lower))
    if (not fp or fp[-1] != "/fp:strict" or not gl or gl[-1] != "/gl-"
            or not defined
            or not any(token.endswith("eclipse_strict_snapshot.cpp") for token in lower)):
        raise EclipseSpkBoundsUnavailable("strict compile command lacks required visible flags")


def verify_snapshot_manifest(
    manifest: TrustedSnapshotManifest,
    bounds: ConditionalNativeType2Bounds,
    *, source_root: str | Path, build_log: str | Path,
) -> SnapshotManifestVerification:
    """Verify trusted pins against disk artifacts and the exact copied record.

    The caller must pin the manifest outside the build or runtime being
    checked. Only MSVC evidence is currently admitted; other profiles fail
    closed. Verification is observational, not a race-free file lock or an
    endorsement of compiler, libm, Python routing, or image integrity.
    """
    from ._eclipse_variable_spk_bounds import (
        ConditionalVariableAnchorBounds, StrictScalarVariableAnchorBounds, variable_snapshot_hash,
    )

    if not isinstance(manifest, TrustedSnapshotManifest) or not isinstance(
        bounds, (ConditionalNativeType2Bounds, ConditionalVariableAnchorBounds, StrictScalarVariableAnchorBounds),
    ):
        raise TypeError("trusted manifest and conditional native bounds required")
    if manifest.compiler_profile != "msvc-strict-v1":
        raise EclipseSpkBoundsUnavailable("unsupported build evidence profile")
    pins = (manifest.binary_sha256, manifest.snapshot_sha256, manifest.build_log_sha256)
    if any(not isinstance(pin, str) or not _SHA256.fullmatch(pin) for pin in pins):
        raise EclipseSpkBoundsUnavailable("receipt requires lowercase SHA-256 pins")
    _validate_msvc_command(manifest.compile_command)
    source_pins = dict(manifest.source_sha256)
    if (len(source_pins) != len(manifest.source_sha256) or set(source_pins) != _REQUIRED_SOURCES
            or any(not isinstance(pin, str) or not _SHA256.fullmatch(pin) for pin in source_pins.values())):
        raise EclipseSpkBoundsUnavailable("receipt source pin set is incomplete or malformed")
    root = Path(source_root).resolve()
    for relative, expected in source_pins.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or _digest(_read_bounded(path)) != expected:
            raise EclipseSpkBoundsUnavailable("receipt source hash mismatch")
    evidence = _read_bounded(Path(build_log))
    if _digest(evidence) != manifest.build_log_sha256:
        raise EclipseSpkBoundsUnavailable("receipt build log hash mismatch")
    try:
        lines = evidence.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise EclipseSpkBoundsUnavailable("unsupported build log encoding") from exc
    if lines.count(manifest.compile_command) != 1:
        raise EclipseSpkBoundsUnavailable("receipt compile line absent or ambiguous")
    if isinstance(bounds, (ConditionalVariableAnchorBounds, StrictScalarVariableAnchorBounds)):
        actual_snapshot = variable_snapshot_hash(bounds)
    else:
        actual_snapshot = _snapshot_hash(
            bounds.source, bounds.record_snapshot, bounds.jd_tdb, bounds.offset_days, bounds.record_init,
            bounds.record_length, bounds.record_count, bounds.record_index,
            bounds.descriptor_start, bounds.descriptor_end,
        )
    if actual_snapshot != bounds.record_snapshot_sha256 or actual_snapshot != manifest.snapshot_sha256:
        raise EclipseSpkBoundsUnavailable("receipt snapshot hash mismatch")
    from . import _moira_native

    path = Path(_moira_native.__file__).resolve()
    if _digest(_read_bounded(path)) != manifest.binary_sha256:
        raise EclipseSpkBoundsUnavailable("receipt binary hash mismatch")
    return SnapshotManifestVerification(str(path), manifest.binary_sha256, actual_snapshot)

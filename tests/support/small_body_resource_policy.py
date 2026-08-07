"""Typed, release-bound admission for supplemental small-body test kernels.

Discovery supplies only candidate manifest paths.  Admission requires a
release-finalized manifest whose complete checksum receipt has been verified,
then derives runtime capability from every opened shard reader.  A filename,
build manifest, or legacy manifest is never sufficient evidence.

This module is tests-only and deliberately accepts the release verifier and
reader factory as arguments.  The production loader remains outside the
policy, while the test harness can own every reader it opens and close partial
acquisitions deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
from typing import Callable, Iterable, Mapping, Sequence


SMALL_BODY_MANIFEST_SCHEMA = "moira.small-body-catalog/v1"
SMALL_BODY_RECEIPT_NAME = "SHA256SUMS"
_MAX_MANIFEST_BYTES = 32 * 1024 * 1024
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class SmallBodyResourceDisposition(str, Enum):
    """Terminal decision for the supplemental resource boundary."""

    RUN = "run"
    SKIP = "skip"
    FAILURE = "failure"


class SmallBodyResourceContractError(ValueError):
    """Raised when policy inputs or opened capability are malformed."""


class SmallBodyCapabilityMismatch(SmallBodyResourceContractError):
    """Raised when opened shard truth disagrees with its release manifest."""


@dataclass(frozen=True, slots=True)
class SmallBodyManifestRequirement:
    """Explicit capability required from every ambient small-body manifest."""

    manifest_schema: str = SMALL_BODY_MANIFEST_SCHEMA
    require_release_integrity: bool = True
    allowed_segment_types: frozenset[int] = frozenset({2, 3, 13})
    require_native_catalog: bool = True
    require_native_segments: bool = True

    def __post_init__(self) -> None:
        _require_identity("manifest_schema", self.manifest_schema, slash=True)
        for name, value in (
            ("require_release_integrity", self.require_release_integrity),
            ("require_native_catalog", self.require_native_catalog),
            ("require_native_segments", self.require_native_segments),
        ):
            if type(value) is not bool:
                raise SmallBodyResourceContractError(
                    f"{name} must be a bool"
                )
        segment_types = _normalize_int_set(
            "allowed_segment_types",
            self.allowed_segment_types,
            minimum=1,
        )
        if not segment_types:
            raise SmallBodyResourceContractError(
                "allowed_segment_types must not be empty"
            )
        object.__setattr__(
            self,
            "allowed_segment_types",
            frozenset(segment_types),
        )

    def render(self) -> str:
        segment_types = ",".join(
            str(value) for value in sorted(self.allowed_segment_types)
        )
        return (
            f"schema={self.manifest_schema};"
            f"release_integrity={self.require_release_integrity};"
            f"segment_types={segment_types};"
            f"native_catalog={self.require_native_catalog};"
            f"native_segments={self.require_native_segments}"
        )


@dataclass(frozen=True, slots=True, order=True)
class SmallBodySegmentCapability:
    """One descriptor-derived supplemental SPK segment."""

    target_naif_id: int
    center_naif_id: int
    frame: int
    segment_type: int
    start_jd: float
    end_jd: float

    def __post_init__(self) -> None:
        _require_int("target_naif_id", self.target_naif_id, minimum=1)
        _require_int("center_naif_id", self.center_naif_id)
        _require_int("frame", self.frame, minimum=1)
        _require_int("segment_type", self.segment_type, minimum=1)
        start_jd = _require_finite_real("start_jd", self.start_jd)
        end_jd = _require_finite_real("end_jd", self.end_jd)
        if end_jd < start_jd:
            raise SmallBodyResourceContractError(
                "segment end_jd precedes start_jd"
            )
        object.__setattr__(self, "start_jd", start_jd)
        object.__setattr__(self, "end_jd", end_jd)


@dataclass(frozen=True, slots=True)
class SmallBodyManifestCapability:
    """Immutable release identity plus opened shard capability."""

    manifest_path: Path
    manifest_sha256: str
    manifest_schema: str
    catalog_id: str
    catalog_version: str
    released_utc: str
    source_manifest_sha256: str
    source_revision: str
    integrity_algorithm: str
    integrity_receipt: str
    integrity_scope: str
    shard_count: int
    declared_body_count: int
    bodies: tuple[int, ...]
    segments: tuple[SmallBodySegmentCapability, ...]
    native_catalog: bool
    native_segment_types: frozenset[int]

    def __post_init__(self) -> None:
        path = Path(self.manifest_path)
        if not path.is_absolute():
            raise SmallBodyResourceContractError(
                "manifest_path must be absolute"
            )
        _require_digest("manifest_sha256", self.manifest_sha256)
        _require_identity("manifest_schema", self.manifest_schema, slash=True)
        _require_identity("catalog_id", self.catalog_id)
        _require_identity("catalog_version", self.catalog_version)
        _require_nonempty_text("released_utc", self.released_utc)
        _require_digest(
            "source_manifest_sha256",
            self.source_manifest_sha256,
        )
        _require_nonempty_text("source_revision", self.source_revision)
        if self.integrity_algorithm != "sha256":
            raise SmallBodyResourceContractError(
                "integrity_algorithm must be 'sha256'"
            )
        if self.integrity_receipt != SMALL_BODY_RECEIPT_NAME:
            raise SmallBodyResourceContractError(
                f"integrity_receipt must be {SMALL_BODY_RECEIPT_NAME!r}"
            )
        _require_nonempty_text("integrity_scope", self.integrity_scope)
        _require_int("shard_count", self.shard_count, minimum=1)
        _require_int(
            "declared_body_count",
            self.declared_body_count,
            minimum=1,
        )
        bodies = tuple(self.bodies)
        for body in bodies:
            _require_int("body", body, minimum=1)
        if tuple(sorted(set(bodies))) != bodies:
            raise SmallBodyResourceContractError(
                "bodies must be sorted and unique"
            )
        if len(bodies) != self.declared_body_count:
            raise SmallBodyResourceContractError(
                "opened bodies disagree with declared_body_count"
            )
        segments = tuple(self.segments)
        if not segments or any(
            type(segment) is not SmallBodySegmentCapability
            for segment in segments
        ):
            raise SmallBodyResourceContractError(
                "segments must contain opened segment capability"
            )
        if {segment.target_naif_id for segment in segments} != set(bodies):
            raise SmallBodyResourceContractError(
                "segment targets disagree with admitted bodies"
            )
        if type(self.native_catalog) is not bool:
            raise SmallBodyResourceContractError(
                "native_catalog must be a bool"
            )
        native_types = _normalize_int_set(
            "native_segment_types",
            self.native_segment_types,
            minimum=1,
        )
        object.__setattr__(self, "manifest_path", path)
        object.__setattr__(self, "bodies", bodies)
        object.__setattr__(self, "segments", segments)
        object.__setattr__(
            self,
            "native_segment_types",
            frozenset(native_types),
        )

    @property
    def identity(self) -> str:
        return (
            f"{self.catalog_id}@{self.catalog_version}:"
            f"{self.manifest_sha256}"
        )

    @property
    def segment_types(self) -> frozenset[int]:
        return frozenset(segment.segment_type for segment in self.segments)

    @property
    def frames(self) -> frozenset[int]:
        return frozenset(segment.frame for segment in self.segments)

    @property
    def coverage(self) -> tuple[tuple[int, int, float, float], ...]:
        """Return exact descriptor intervals as center/target coverage."""

        return tuple(
            (
                segment.center_naif_id,
                segment.target_naif_id,
                segment.start_jd,
                segment.end_jd,
            )
            for segment in self.segments
        )


@dataclass(frozen=True, slots=True)
class SmallBodyResourceReceipt:
    """Run, skip, or failure evidence for the supplemental reader pool."""

    name: str
    disposition: SmallBodyResourceDisposition
    requirement: SmallBodyManifestRequirement
    capabilities: tuple[SmallBodyManifestCapability, ...]
    reason: str
    failure_type: str | None = None
    terminal: bool = True

    def __post_init__(self) -> None:
        _require_nonempty_text("receipt name", self.name)
        if type(self.disposition) is not SmallBodyResourceDisposition:
            raise SmallBodyResourceContractError(
                "receipt disposition is invalid"
            )
        if type(self.requirement) is not SmallBodyManifestRequirement:
            raise SmallBodyResourceContractError(
                "receipt requirement is invalid"
            )
        capabilities = tuple(self.capabilities)
        if any(
            type(capability) is not SmallBodyManifestCapability
            for capability in capabilities
        ):
            raise SmallBodyResourceContractError(
                "receipt capabilities are invalid"
            )
        _require_nonempty_text("receipt reason", self.reason)
        if self.failure_type is not None:
            _require_nonempty_text("failure_type", self.failure_type)
        if type(self.terminal) is not bool:
            raise SmallBodyResourceContractError(
                "receipt terminal must be a bool"
            )
        if self.disposition is SmallBodyResourceDisposition.RUN:
            if not capabilities:
                raise SmallBodyResourceContractError(
                    "run receipt requires capability"
                )
            if self.failure_type is not None:
                raise SmallBodyResourceContractError(
                    "run receipt cannot carry failure_type"
                )
        elif self.disposition is SmallBodyResourceDisposition.SKIP:
            if capabilities or self.failure_type is not None:
                raise SmallBodyResourceContractError(
                    "skip receipt cannot carry capability or failure_type"
                )
            if not self.terminal:
                raise SmallBodyResourceContractError(
                    "skip receipt must be terminal"
                )
        else:
            if self.failure_type is None or not self.terminal:
                raise SmallBodyResourceContractError(
                    "failure receipt must be terminal with failure_type"
                )
        object.__setattr__(self, "capabilities", capabilities)

    @property
    def identities(self) -> tuple[str, ...]:
        return tuple(capability.identity for capability in self.capabilities)

    def render(self) -> str:
        identities = (
            ",".join(self.identities)
            if self.identities
            else "<none>"
        )
        failure = (
            ""
            if self.failure_type is None
            else f";failure_type={self.failure_type}"
        )
        return (
            f"{self.name}: disposition={self.disposition.value};"
            f"terminal={self.terminal};identities={identities};"
            f"requirement=({self.requirement.render()});"
            f"reason={self.reason}{failure}"
        )


@dataclass(frozen=True, slots=True)
class SmallBodyReaderAdmission:
    """Receipt and explicitly caller-owned readers from one admission."""

    receipt: SmallBodyResourceReceipt
    readers: tuple[object, ...]

    def __post_init__(self) -> None:
        if type(self.receipt) is not SmallBodyResourceReceipt:
            raise SmallBodyResourceContractError(
                "admission receipt is invalid"
            )
        readers = tuple(self.readers)
        if self.receipt.disposition is SmallBodyResourceDisposition.RUN:
            expected = sum(
                capability.shard_count
                for capability in self.receipt.capabilities
            )
            if len(readers) != expected:
                raise SmallBodyResourceContractError(
                    "admission reader count disagrees with shard capability"
                )
        elif readers:
            raise SmallBodyResourceContractError(
                "non-run admission cannot retain readers"
            )
        object.__setattr__(self, "readers", readers)


@dataclass(frozen=True, slots=True)
class _ManifestShard:
    index: int
    resolved_path: Path
    bodies: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _ManifestIdentity:
    path: Path
    sha256: str
    schema: str
    catalog_id: str
    catalog_version: str
    released_utc: str
    source_manifest_sha256: str
    source_revision: str
    integrity_algorithm: str
    integrity_receipt: str
    integrity_scope: str
    shard_count: int
    body_count: int
    shards: tuple[_ManifestShard, ...]


def admit_small_body_manifests(
    manifest_paths: Iterable[str | Path],
    *,
    verify_release: Callable[[Path], object],
    reader_factory: Callable[[Path], object],
    native_catalog_available: bool,
    native_segment_types: Iterable[int],
    requirement: SmallBodyManifestRequirement | None = None,
) -> SmallBodyReaderAdmission:
    """Verify releases, open all shards, and return caller-owned readers.

    Every reader opened before a failure is closed in reverse order.  Ordinary
    discovery, manifest, integrity, opener, and capability failures become a
    terminal failure receipt rather than leaking a partial pool.
    """

    requirement = requirement or SmallBodyManifestRequirement()
    if type(requirement) is not SmallBodyManifestRequirement:
        raise SmallBodyResourceContractError(
            "requirement must be SmallBodyManifestRequirement"
        )
    if not callable(verify_release):
        raise SmallBodyResourceContractError(
            "verify_release must be callable"
        )
    if not callable(reader_factory):
        raise SmallBodyResourceContractError(
            "reader_factory must be callable"
        )
    if type(native_catalog_available) is not bool:
        raise SmallBodyResourceContractError(
            "native_catalog_available must be a bool"
        )
    native_types = frozenset(
        _normalize_int_set(
            "native_segment_types",
            native_segment_types,
            minimum=1,
        )
    )

    paths: list[Path] = []
    seen_paths: set[Path] = set()
    try:
        for raw_path in manifest_paths:
            path = Path(raw_path).resolve(strict=False)
            if path in seen_paths:
                raise SmallBodyResourceContractError(
                    f"duplicate ambient manifest path: {path}"
                )
            seen_paths.add(path)
            paths.append(path)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return _failure_admission(
            requirement,
            stage="manifest discovery normalization",
            exc=exc,
        )

    if not paths:
        return SmallBodyReaderAdmission(
            receipt=SmallBodyResourceReceipt(
                name="supplemental-small-body-pool",
                disposition=SmallBodyResourceDisposition.SKIP,
                requirement=requirement,
                capabilities=(),
                reason=(
                    "no released sovereign small-body manifest is installed"
                ),
            ),
            readers=(),
        )

    readers: list[object] = []
    capabilities: list[SmallBodyManifestCapability] = []
    stage = "manifest admission"
    try:
        if requirement.require_native_catalog and not native_catalog_available:
            raise SmallBodyCapabilityMismatch(
                "native DAF catalog capability is unavailable"
            )
        for path in paths:
            stage = f"release verification for {path}"
            identity = _load_and_verify_manifest(
                path,
                requirement=requirement,
                verify_release=verify_release,
            )
            stage = f"shard acquisition for {path}"
            capability, opened = _open_manifest_readers(
                identity,
                requirement=requirement,
                reader_factory=reader_factory,
                native_catalog_available=native_catalog_available,
                native_segment_types=native_types,
            )
            readers.extend(opened)
            capabilities.append(capability)
        _validate_cross_manifest_capability(capabilities)
    except Exception as exc:
        close_failures = _close_readers(readers)
        reason = f"{stage} failed: {exc}"
        if close_failures:
            reason += "; partial-reader close failures: " + "; ".join(
                close_failures
            )
        return _failure_admission(
            requirement,
            stage=reason,
            exc=exc,
        )

    receipt = SmallBodyResourceReceipt(
        name="supplemental-small-body-pool",
        disposition=SmallBodyResourceDisposition.RUN,
        requirement=requirement,
        capabilities=tuple(capabilities),
        reason=(
            f"admitted {len(capabilities)} released manifest(s), "
            f"{len(readers)} shard reader(s), and "
            f"{sum(len(item.bodies) for item in capabilities)} body ID(s)"
        ),
        terminal=False,
    )
    return SmallBodyReaderAdmission(
        receipt=receipt,
        readers=tuple(readers),
    )


def terminalize_small_body_receipt(
    receipt: SmallBodyResourceReceipt,
    *,
    close_failures: Sequence[str] = (),
) -> SmallBodyResourceReceipt:
    """Return the terminal run/failure receipt after owned-reader teardown."""

    if (
        type(receipt) is not SmallBodyResourceReceipt
        or receipt.disposition is not SmallBodyResourceDisposition.RUN
        or receipt.terminal
    ):
        raise SmallBodyResourceContractError(
            "only a non-terminal run receipt can be terminalized"
        )
    failures = tuple(close_failures)
    for failure in failures:
        _require_nonempty_text("close failure", failure)
    if failures:
        return SmallBodyResourceReceipt(
            name=receipt.name,
            disposition=SmallBodyResourceDisposition.FAILURE,
            requirement=receipt.requirement,
            capabilities=receipt.capabilities,
            reason="owned-reader teardown failed: " + "; ".join(failures),
            failure_type="ReaderTeardownError",
            terminal=True,
        )
    return replace(
        receipt,
        reason=receipt.reason + "; all owned supplemental readers closed",
        terminal=True,
    )


def fail_small_body_live_receipt(
    receipt: SmallBodyResourceReceipt,
    *,
    stage: str,
    exc: Exception,
    close_failures: Sequence[str] = (),
) -> SmallBodyResourceReceipt:
    """Convert an admitted live pool failure into terminal failure evidence."""

    if (
        type(receipt) is not SmallBodyResourceReceipt
        or receipt.disposition is not SmallBodyResourceDisposition.RUN
        or receipt.terminal
    ):
        raise SmallBodyResourceContractError(
            "only a non-terminal run receipt can record a live failure"
        )
    stage = _require_nonempty_text("live failure stage", stage)
    failures = tuple(close_failures)
    for failure in failures:
        _require_nonempty_text("close failure", failure)
    reason = f"{stage} failed after supplemental admission: {exc}"
    if failures:
        reason += "; owned-reader close failures: " + "; ".join(failures)
    return SmallBodyResourceReceipt(
        name=receipt.name,
        disposition=SmallBodyResourceDisposition.FAILURE,
        requirement=receipt.requirement,
        capabilities=receipt.capabilities,
        reason=reason,
        failure_type=type(exc).__name__,
        terminal=True,
    )


def close_small_body_readers(readers: Iterable[object]) -> tuple[str, ...]:
    """Close readers in reverse order and return every visible failure."""

    return tuple(_close_readers(list(readers)))


def small_body_report_from_receipts(
    receipts: Mapping[str, SmallBodyResourceReceipt],
) -> dict[str, object]:
    """Serialize full receipt evidence into xdist-safe primitives."""

    details: dict[str, object] = {}
    for nodeid, receipt in sorted(receipts.items()):
        if type(nodeid) is not str:
            raise SmallBodyResourceContractError(
                "small-body receipt nodeid must be text"
            )
        if type(receipt) is not SmallBodyResourceReceipt:
            raise SmallBodyResourceContractError(
                "small-body receipt stash contains an invalid value"
            )
        details[nodeid] = _receipt_detail(receipt)
    return {
        "version": 1,
        "summary": _report_summary(details),
        "details": details,
    }


def empty_small_body_report() -> dict[str, object]:
    details: dict[str, object] = {}
    return {
        "version": 1,
        "summary": _report_summary(details),
        "details": details,
    }


def merge_small_body_report(
    target: dict[str, object],
    incoming: object,
    *,
    source: str,
) -> dict[str, object]:
    """Validate and merge one controller/worker report without detail loss."""

    _require_nonempty_text("report source", source)
    normalized = _normalize_report(incoming, source=source)
    target_normalized = _normalize_report(target, source="merge target")
    target_details = target_normalized["details"]
    assert isinstance(target_details, dict)
    incoming_details = normalized["details"]
    assert isinstance(incoming_details, dict)
    for nodeid, detail in incoming_details.items():
        qualified = nodeid
        suffix = 1
        while qualified in target_details:
            suffix += 1
            qualified = f"{nodeid} [{source}#{suffix}]"
        target_details[qualified] = detail
    target_normalized["summary"] = _report_summary(target_details)
    target.clear()
    target.update(target_normalized)
    return target


def _load_and_verify_manifest(
    path: Path,
    *,
    requirement: SmallBodyManifestRequirement,
    verify_release: Callable[[Path], object],
) -> _ManifestIdentity:
    try:
        resolved = path.resolve(strict=True)
        if resolved.is_symlink() or not resolved.is_file():
            raise SmallBodyResourceContractError(
                f"ambient manifest is not a regular non-symlink file: {resolved}"
            )
        size = resolved.stat().st_size
        if size <= 0 or size > _MAX_MANIFEST_BYTES:
            raise SmallBodyResourceContractError(
                f"ambient manifest byte size is outside policy: {size}"
            )
        raw = resolved.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except SmallBodyResourceContractError:
        raise
    except Exception as exc:
        raise SmallBodyResourceContractError(
            f"cannot read ambient manifest {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SmallBodyResourceContractError(
            "small-body manifest root must be an object"
        )
    if not isinstance(payload.get("release"), dict):
        raise SmallBodyResourceContractError(
            "ambient small-body manifest is build/legacy data without "
            "release identity and integrity"
        )
    if payload.get("manifest_schema") != requirement.manifest_schema:
        raise SmallBodyResourceContractError(
            "small-body manifest schema mismatch: "
            f"expected {requirement.manifest_schema!r}, "
            f"found {payload.get('manifest_schema')!r}"
        )

    verification = verify_release(resolved.parent)
    manifest_digest = hashlib.sha256(raw).hexdigest()
    catalog_id = _require_identity("catalog_id", payload.get("catalog_id"))
    catalog_version = _require_identity(
        "catalog_version",
        payload.get("catalog_version"),
    )
    shard_count = _require_int(
        "shard_count",
        payload.get("shard_count"),
        minimum=1,
    )
    body_count = _require_int(
        "body_count",
        payload.get("body_count"),
        minimum=1,
    )
    for field, expected in (
        ("root", resolved.parent),
        ("catalog_id", catalog_id),
        ("catalog_version", catalog_version),
        ("shard_count", shard_count),
        ("body_count", body_count),
        ("manifest_sha256", manifest_digest),
    ):
        actual = getattr(verification, field, None)
        if field == "root":
            try:
                actual = Path(actual).resolve(strict=False)
            except (TypeError, ValueError):
                pass
        if actual != expected:
            raise SmallBodyCapabilityMismatch(
                f"release verifier {field} mismatch: "
                f"expected {expected!r}, found {actual!r}"
            )

    release = payload["release"]
    released_utc = _require_nonempty_text(
        "release.released_utc",
        release.get("released_utc"),
    )
    source_manifest_sha256 = _require_digest(
        "release.source_manifest_sha256",
        release.get("source_manifest_sha256"),
    )
    source_revision = _require_nonempty_text(
        "release.source_revision",
        release.get("source_revision"),
    )
    integrity = release.get("integrity")
    if not isinstance(integrity, dict):
        raise SmallBodyResourceContractError(
            "release.integrity must be an object"
        )
    integrity_algorithm = integrity.get("algorithm")
    if integrity_algorithm != "sha256":
        raise SmallBodyResourceContractError(
            "release integrity algorithm must be 'sha256'"
        )
    integrity_receipt = integrity.get("receipt")
    if integrity_receipt != SMALL_BODY_RECEIPT_NAME:
        raise SmallBodyResourceContractError(
            f"release integrity receipt must be {SMALL_BODY_RECEIPT_NAME!r}"
        )
    integrity_scope = _require_nonempty_text(
        "release.integrity.receipt_scope",
        integrity.get("receipt_scope"),
    )
    raw_shards = payload.get("shards")
    if not isinstance(raw_shards, list) or len(raw_shards) != shard_count:
        raise SmallBodyResourceContractError(
            "manifest shard_count disagrees with shard records"
        )
    shards: list[_ManifestShard] = []
    seen_indices: set[int] = set()
    seen_paths: set[Path] = set()
    seen_bodies: set[int] = set()
    root = resolved.parent
    for position, raw_shard in enumerate(raw_shards):
        if not isinstance(raw_shard, dict):
            raise SmallBodyResourceContractError(
                f"manifest shard {position} must be an object"
            )
        index = _require_int(f"shards[{position}].index", raw_shard.get("index"))
        if index in seen_indices:
            raise SmallBodyResourceContractError(
                f"duplicate shard index {index}"
            )
        seen_indices.add(index)
        relative = _safe_relative_path(
            f"shards[{position}].path",
            raw_shard.get("path"),
        )
        shard_path = (root / relative).resolve(strict=False)
        if not shard_path.is_relative_to(root):
            raise SmallBodyResourceContractError(
                f"shards[{position}].path escapes the release root"
            )
        if (
            not shard_path.is_file()
            or shard_path.is_symlink()
        ):
            raise SmallBodyResourceContractError(
                f"shards[{position}].path is not a regular "
                "non-symlink file"
            )
        if shard_path in seen_paths:
            raise SmallBodyResourceContractError(
                f"duplicate shard path {relative}"
            )
        seen_paths.add(shard_path)
        raw_bodies = raw_shard.get("bodies")
        if not isinstance(raw_bodies, list) or not raw_bodies:
            raise SmallBodyResourceContractError(
                f"shards[{position}].bodies must be non-empty"
            )
        bodies = tuple(
            _require_int(
                f"shards[{position}].bodies",
                body,
                minimum=1,
            )
            for body in raw_bodies
        )
        if len(set(bodies)) != len(bodies):
            raise SmallBodyResourceContractError(
                f"shard {index} contains duplicate body IDs"
            )
        overlap = seen_bodies.intersection(bodies)
        if overlap:
            raise SmallBodyResourceContractError(
                "body IDs occur in multiple shards: "
                f"{sorted(overlap)[:5]}"
            )
        seen_bodies.update(bodies)
        declared = _require_int(
            f"shards[{position}].body_count",
            raw_shard.get("body_count"),
            minimum=1,
        )
        if declared != len(bodies):
            raise SmallBodyResourceContractError(
                f"shard {index} body_count disagrees with bodies"
            )
        shards.append(
            _ManifestShard(
                index=index,
                resolved_path=shard_path,
                bodies=bodies,
            )
        )
    if len(seen_bodies) != body_count:
        raise SmallBodyResourceContractError(
            "manifest body_count disagrees with shard bodies"
        )
    return _ManifestIdentity(
        path=resolved,
        sha256=manifest_digest,
        schema=requirement.manifest_schema,
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        released_utc=released_utc,
        source_manifest_sha256=source_manifest_sha256,
        source_revision=source_revision,
        integrity_algorithm=integrity_algorithm,
        integrity_receipt=integrity_receipt,
        integrity_scope=integrity_scope,
        shard_count=shard_count,
        body_count=body_count,
        shards=tuple(shards),
    )


def _open_manifest_readers(
    identity: _ManifestIdentity,
    *,
    requirement: SmallBodyManifestRequirement,
    reader_factory: Callable[[Path], object],
    native_catalog_available: bool,
    native_segment_types: frozenset[int],
) -> tuple[SmallBodyManifestCapability, list[object]]:
    readers: list[object] = []
    segments: list[SmallBodySegmentCapability] = []
    try:
        for shard in identity.shards:
            reader = reader_factory(shard.resolved_path)
            readers.append(reader)
            reader_path = getattr(
                reader,
                "_path",
                getattr(reader, "path", None),
            )
            try:
                actual_path = Path(reader_path).resolve(strict=False)
            except (TypeError, ValueError) as exc:
                raise SmallBodyCapabilityMismatch(
                    f"opened shard {shard.index} exposes no usable path"
                ) from exc
            if actual_path != shard.resolved_path:
                raise SmallBodyCapabilityMismatch(
                    f"opened shard {shard.index} path mismatch: "
                    f"expected {shard.resolved_path}, found {actual_path}"
                )
            catalog = getattr(reader, "_catalog", None)
            if requirement.require_native_catalog and not isinstance(
                catalog,
                Mapping,
            ):
                raise SmallBodyCapabilityMismatch(
                    f"opened shard {shard.index} has no native catalog evidence"
                )
            kernel = getattr(reader, "_kernel", None)
            raw_segments = getattr(kernel, "segments", None)
            if not isinstance(raw_segments, (list, tuple)) or not raw_segments:
                raise SmallBodyCapabilityMismatch(
                    f"opened shard {shard.index} has no segment descriptors"
                )
            shard_segments = tuple(
                _segment_from_reader(value)
                for value in raw_segments
            )
            actual_bodies = {
                segment.target_naif_id for segment in shard_segments
            }
            if actual_bodies != set(shard.bodies):
                missing = sorted(set(shard.bodies) - actual_bodies)
                unexpected = sorted(actual_bodies - set(shard.bodies))
                raise SmallBodyCapabilityMismatch(
                    f"opened shard {shard.index} body mismatch: "
                    f"missing={missing[:5]}, unexpected={unexpected[:5]}"
                )
            actual_types = {
                segment.segment_type for segment in shard_segments
            }
            unsupported = actual_types - requirement.allowed_segment_types
            if unsupported:
                raise SmallBodyCapabilityMismatch(
                    f"opened shard {shard.index} has disallowed segment "
                    f"types {sorted(unsupported)}"
                )
            if requirement.require_native_segments:
                non_native = actual_types - native_segment_types
                if non_native:
                    raise SmallBodyCapabilityMismatch(
                        f"opened shard {shard.index} lacks native evaluator "
                        f"capability for segment types {sorted(non_native)}"
                    )
            segments.extend(shard_segments)
        capability = SmallBodyManifestCapability(
            manifest_path=identity.path,
            manifest_sha256=identity.sha256,
            manifest_schema=identity.schema,
            catalog_id=identity.catalog_id,
            catalog_version=identity.catalog_version,
            released_utc=identity.released_utc,
            source_manifest_sha256=identity.source_manifest_sha256,
            source_revision=identity.source_revision,
            integrity_algorithm=identity.integrity_algorithm,
            integrity_receipt=identity.integrity_receipt,
            integrity_scope=identity.integrity_scope,
            shard_count=identity.shard_count,
            declared_body_count=identity.body_count,
            bodies=tuple(
                sorted({item.target_naif_id for item in segments})
            ),
            segments=tuple(segments),
            native_catalog=native_catalog_available,
            native_segment_types=native_segment_types,
        )
    except Exception as exc:
        close_failures = _close_readers(readers)
        if close_failures:
            raise SmallBodyCapabilityMismatch(
                f"{exc}; partial-reader close failures: "
                + "; ".join(close_failures)
            ) from exc
        raise

    return capability, readers


def _segment_from_reader(raw: object) -> SmallBodySegmentCapability:
    try:
        return SmallBodySegmentCapability(
            target_naif_id=getattr(raw, "target"),
            center_naif_id=getattr(raw, "center"),
            frame=getattr(raw, "frame"),
            segment_type=getattr(raw, "data_type"),
            start_jd=getattr(raw, "start_jd"),
            end_jd=getattr(raw, "end_jd"),
        )
    except AttributeError as exc:
        raise SmallBodyCapabilityMismatch(
            "opened small-body segment has an incomplete descriptor"
        ) from exc


def _validate_cross_manifest_capability(
    capabilities: Sequence[SmallBodyManifestCapability],
) -> None:
    seen_catalogs: set[tuple[str, str]] = set()
    seen_bodies: set[int] = set()
    for capability in capabilities:
        identity = (capability.catalog_id, capability.catalog_version)
        if identity in seen_catalogs:
            raise SmallBodyCapabilityMismatch(
                f"duplicate catalog release identity {identity!r}"
            )
        seen_catalogs.add(identity)
        overlap = seen_bodies.intersection(capability.bodies)
        if overlap:
            raise SmallBodyCapabilityMismatch(
                "body IDs overlap across admitted manifests: "
                f"{sorted(overlap)[:5]}"
            )
        seen_bodies.update(capability.bodies)


def _failure_admission(
    requirement: SmallBodyManifestRequirement,
    *,
    stage: str,
    exc: Exception,
) -> SmallBodyReaderAdmission:
    reason = stage
    if str(exc) and str(exc) not in reason:
        reason = f"{reason}: {exc}"
    return SmallBodyReaderAdmission(
        receipt=SmallBodyResourceReceipt(
            name="supplemental-small-body-pool",
            disposition=SmallBodyResourceDisposition.FAILURE,
            requirement=requirement,
            capabilities=(),
            reason=reason,
            failure_type=type(exc).__name__,
            terminal=True,
        ),
        readers=(),
    )


def _close_readers(readers: Sequence[object]) -> list[str]:
    failures: list[str] = []
    for position, reader in reversed(tuple(enumerate(readers))):
        try:
            close = getattr(reader, "close")
            close()
        except Exception as exc:
            failures.append(
                f"reader[{position}] {type(exc).__name__}: {exc}"
            )
    return failures


def _receipt_detail(receipt: SmallBodyResourceReceipt) -> dict[str, object]:
    capabilities = []
    for capability in receipt.capabilities:
        capabilities.append(
            {
                "manifest_path": str(capability.manifest_path),
                "manifest_sha256": capability.manifest_sha256,
                "manifest_schema": capability.manifest_schema,
                "catalog_id": capability.catalog_id,
                "catalog_version": capability.catalog_version,
                "released_utc": capability.released_utc,
                "source_manifest_sha256": (
                    capability.source_manifest_sha256
                ),
                "source_revision": capability.source_revision,
                "integrity_algorithm": capability.integrity_algorithm,
                "integrity_receipt": capability.integrity_receipt,
                "integrity_scope": capability.integrity_scope,
                "shard_count": capability.shard_count,
                "declared_body_count": capability.declared_body_count,
                "bodies": list(capability.bodies),
                "coverage": [
                    [center, target, start_jd, end_jd]
                    for center, target, start_jd, end_jd
                    in capability.coverage
                ],
                "segment_types": sorted(capability.segment_types),
                "frames": sorted(capability.frames),
                "native_catalog": capability.native_catalog,
                "native_segment_types": sorted(
                    capability.native_segment_types
                ),
                "identity": capability.identity,
            }
        )
    return {
        "disposition": receipt.disposition.value,
        "terminal": receipt.terminal,
        "failure_type": receipt.failure_type,
        "requirement": {
            "manifest_schema": receipt.requirement.manifest_schema,
            "require_release_integrity": (
                receipt.requirement.require_release_integrity
            ),
            "allowed_segment_types": sorted(
                receipt.requirement.allowed_segment_types
            ),
            "require_native_catalog": (
                receipt.requirement.require_native_catalog
            ),
            "require_native_segments": (
                receipt.requirement.require_native_segments
            ),
        },
        "identities": list(receipt.identities),
        "capabilities": capabilities,
        "rendered": receipt.render(),
    }


def _report_summary(details: Mapping[str, object]) -> dict[str, object]:
    counts = {"run": 0, "skip": 0, "failure": 0}
    terminal = 0
    identities: set[str] = set()
    manifests: set[str] = set()
    shards = 0
    bodies: set[int] = set()
    for raw_detail in details.values():
        detail = raw_detail
        assert isinstance(detail, dict)
        disposition = detail["disposition"]
        assert isinstance(disposition, str)
        counts[disposition] += 1
        if detail["terminal"]:
            terminal += 1
        identities.update(detail["identities"])
        for capability in detail["capabilities"]:
            manifests.add(capability["manifest_path"])
            shards += capability["shard_count"]
            bodies.update(capability["bodies"])
    return {
        "receipts": len(details),
        **counts,
        "terminal": terminal,
        "identities": sorted(identities),
        "manifests": len(manifests),
        "shards": shards,
        "bodies": len(bodies),
    }


def _normalize_report(
    report: object,
    *,
    source: str,
) -> dict[str, object]:
    if (
        not isinstance(report, dict)
        or report.get("version") != 1
        or not isinstance(report.get("details"), dict)
        or not isinstance(report.get("summary"), dict)
    ):
        raise SmallBodyResourceContractError(
            f"{source} returned an invalid small-body resource report"
        )
    normalized_details: dict[str, object] = {}
    for nodeid, raw_detail in report["details"].items():
        if type(nodeid) is not str:
            raise SmallBodyResourceContractError(
                f"{source} returned a non-text small-body nodeid"
            )
        normalized_details[nodeid] = _normalize_detail(
            raw_detail,
            source=source,
        )
    expected = _report_summary(normalized_details)
    if report["summary"] != expected:
        raise SmallBodyResourceContractError(
            f"{source} returned a contradictory small-body resource summary"
        )
    return {
        "version": 1,
        "summary": expected,
        "details": normalized_details,
    }


def _normalize_detail(detail: object, *, source: str) -> dict[str, object]:
    if (
        not isinstance(detail, dict)
        or set(detail)
        != {
            "disposition",
            "terminal",
            "failure_type",
            "requirement",
            "identities",
            "capabilities",
            "rendered",
        }
    ):
        raise SmallBodyResourceContractError(
            f"{source} returned an invalid small-body resource detail"
        )
    disposition = detail.get("disposition")
    terminal = detail.get("terminal")
    failure_type = detail.get("failure_type")
    requirement = detail.get("requirement")
    identities = detail.get("identities")
    capabilities = detail.get("capabilities")
    rendered = detail.get("rendered")
    if (
        disposition not in {"run", "skip", "failure"}
        or type(terminal) is not bool
        or (
            failure_type is not None
            and type(failure_type) is not str
        )
        or not isinstance(identities, list)
        or any(type(value) is not str for value in identities)
        or not isinstance(capabilities, list)
        or type(rendered) is not str
    ):
        raise SmallBodyResourceContractError(
            f"{source} returned an invalid small-body resource detail"
        )
    normalized_requirement = _normalize_requirement(
        requirement,
        source=source,
    )
    normalized_capabilities = [
        _normalize_capability(value, source=source)
        for value in capabilities
    ]
    computed_identities = [
        capability["identity"]
        for capability in normalized_capabilities
    ]
    if identities != computed_identities:
        raise SmallBodyResourceContractError(
            f"{source} returned contradictory small-body identities"
        )
    if disposition == "run" and not normalized_capabilities:
        raise SmallBodyResourceContractError(
            f"{source} returned a capability-free run detail"
        )
    if disposition == "skip" and (
        normalized_capabilities or failure_type is not None or not terminal
    ):
        raise SmallBodyResourceContractError(
            f"{source} returned an invalid skip detail"
        )
    if disposition == "failure" and (
        failure_type is None or not terminal
    ):
        raise SmallBodyResourceContractError(
            f"{source} returned an invalid failure detail"
        )
    return {
        "disposition": disposition,
        "terminal": terminal,
        "failure_type": failure_type,
        "requirement": normalized_requirement,
        "identities": list(identities),
        "capabilities": normalized_capabilities,
        "rendered": rendered,
    }


def _normalize_requirement(
    requirement: object,
    *,
    source: str,
) -> dict[str, object]:
    fields = {
        "manifest_schema",
        "require_release_integrity",
        "allowed_segment_types",
        "require_native_catalog",
        "require_native_segments",
    }
    if not isinstance(requirement, dict) or set(requirement) != fields:
        raise SmallBodyResourceContractError(
            f"{source} returned an invalid small-body requirement"
        )
    manifest_schema = requirement["manifest_schema"]
    allowed_segment_types = requirement["allowed_segment_types"]
    if (
        type(manifest_schema) is not str
        or not manifest_schema
        or not isinstance(allowed_segment_types, list)
        or any(
            type(segment_type) is not int or segment_type < 1
            for segment_type in allowed_segment_types
        )
        or allowed_segment_types
        != sorted(set(allowed_segment_types))
        or any(
            type(requirement[name]) is not bool
            for name in (
                "require_release_integrity",
                "require_native_catalog",
                "require_native_segments",
            )
        )
    ):
        raise SmallBodyResourceContractError(
            f"{source} returned an invalid small-body requirement"
        )
    return {
        "manifest_schema": manifest_schema,
        "require_release_integrity": requirement[
            "require_release_integrity"
        ],
        "allowed_segment_types": list(allowed_segment_types),
        "require_native_catalog": requirement[
            "require_native_catalog"
        ],
        "require_native_segments": requirement[
            "require_native_segments"
        ],
    }


def _normalize_capability(
    capability: object,
    *,
    source: str,
) -> dict[str, object]:
    if not isinstance(capability, dict):
        raise SmallBodyResourceContractError(
            f"{source} returned invalid small-body capability"
        )
    text_fields = (
        "manifest_path",
        "manifest_sha256",
        "manifest_schema",
        "catalog_id",
        "catalog_version",
        "released_utc",
        "source_manifest_sha256",
        "source_revision",
        "integrity_algorithm",
        "integrity_receipt",
        "integrity_scope",
        "identity",
    )
    if any(type(capability.get(field)) is not str for field in text_fields):
        raise SmallBodyResourceContractError(
            f"{source} returned invalid small-body capability text"
        )
    for field in ("shard_count", "declared_body_count"):
        if type(capability.get(field)) is not int or capability[field] < 1:
            raise SmallBodyResourceContractError(
                f"{source} returned invalid small-body {field}"
            )
    for field in (
        "bodies",
        "coverage",
        "segment_types",
        "frames",
        "native_segment_types",
    ):
        if not isinstance(capability.get(field), list):
            raise SmallBodyResourceContractError(
                f"{source} returned invalid small-body {field}"
            )
    if type(capability.get("native_catalog")) is not bool:
        raise SmallBodyResourceContractError(
            f"{source} returned invalid native_catalog"
        )
    bodies = capability["bodies"]
    if any(type(value) is not int or value < 1 for value in bodies):
        raise SmallBodyResourceContractError(
            f"{source} returned invalid body IDs"
        )
    coverage = capability["coverage"]
    for interval in coverage:
        if (
            not isinstance(interval, list)
            or len(interval) != 4
            or type(interval[0]) is not int
            or type(interval[1]) is not int
            or not _is_finite_number(interval[2])
            or not _is_finite_number(interval[3])
            or interval[3] < interval[2]
        ):
            raise SmallBodyResourceContractError(
                f"{source} returned invalid coverage"
            )
    return {
        field: (
            list(capability[field])
            if isinstance(capability[field], list)
            else capability[field]
        )
        for field in (
            *text_fields,
            "shard_count",
            "declared_body_count",
            "bodies",
            "coverage",
            "segment_types",
            "frames",
            "native_catalog",
            "native_segment_types",
        )
    }


def _safe_relative_path(name: str, value: object) -> PurePosixPath:
    if type(value) is not str or not value:
        raise SmallBodyResourceContractError(
            f"{name} must be a non-empty relative POSIX path"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or "\\" in value
        or ":" in value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise SmallBodyResourceContractError(
            f"{name} must stay beneath the release root"
        )
    return path


def _normalize_int_set(
    name: str,
    values: Iterable[int],
    *,
    minimum: int | None = None,
) -> set[int]:
    if isinstance(values, (str, bytes)):
        raise SmallBodyResourceContractError(
            f"{name} must be an iterable of integers"
        )
    try:
        normalized = {
            _require_int(name, value, minimum=minimum)
            for value in values
        }
    except TypeError as exc:
        raise SmallBodyResourceContractError(
            f"{name} must be an iterable of integers"
        ) from exc
    return normalized


def _require_int(
    name: str,
    value: object,
    *,
    minimum: int | None = None,
) -> int:
    if type(value) is not int:
        raise SmallBodyResourceContractError(
            f"{name} must be an integer"
        )
    if minimum is not None and value < minimum:
        raise SmallBodyResourceContractError(
            f"{name} must be at least {minimum}"
        )
    return value


def _require_finite_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SmallBodyResourceContractError(
            f"{name} must be a finite real number"
        )
    normalized = float(value)
    if not math.isfinite(normalized):
        raise SmallBodyResourceContractError(
            f"{name} must be a finite real number"
        )
    return normalized


def _require_nonempty_text(name: str, value: object) -> str:
    if type(value) is not str or not value.strip():
        raise SmallBodyResourceContractError(
            f"{name} must be non-empty text"
        )
    return value


def _require_identity(
    name: str,
    value: object,
    *,
    slash: bool = False,
) -> str:
    value = _require_nonempty_text(name, value)
    if slash:
        if any(character.isspace() for character in value):
            raise SmallBodyResourceContractError(
                f"{name} must not contain whitespace"
            )
    elif _IDENTITY_RE.fullmatch(value) is None:
        raise SmallBodyResourceContractError(
            f"{name} must be a stable ASCII identity"
        )
    return value


def _require_digest(name: str, value: object) -> str:
    if type(value) is not str or _DIGEST_RE.fullmatch(value) is None:
        raise SmallBodyResourceContractError(
            f"{name} must be a lowercase SHA-256 digest"
        )
    return value


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


__all__ = [
    "SMALL_BODY_MANIFEST_SCHEMA",
    "SmallBodyCapabilityMismatch",
    "SmallBodyManifestCapability",
    "SmallBodyManifestRequirement",
    "SmallBodyReaderAdmission",
    "SmallBodyResourceContractError",
    "SmallBodyResourceDisposition",
    "SmallBodyResourceReceipt",
    "SmallBodySegmentCapability",
    "admit_small_body_manifests",
    "close_small_body_readers",
    "empty_small_body_report",
    "fail_small_body_live_receipt",
    "merge_small_body_report",
    "small_body_report_from_receipts",
    "terminalize_small_body_receipt",
]

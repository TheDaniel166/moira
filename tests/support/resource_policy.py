"""Typed, content-derived planetary-kernel contracts for the test harness.

Discovery answers only where a candidate file might be.  Admission requires
opening that candidate through Moira's planetary reader and deriving every
capability from the opened DAF/SPK catalog and segment descriptors.

The resolver deliberately caches only immutable capability facts.  It never
caches or returns the probe reader that produced them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from numbers import Real
import os
from pathlib import Path
import stat
from threading import Lock
from typing import Callable, Iterable, Mapping


_PRODUCT = "planetary-spk"
_HISTORICAL_DEFAULT_IDENTITY = "DE441"
_KERNEL_PATH_ENV = "MOIRA_KERNEL_PATH"


class ResourceDisposition(str, Enum):
    """What the harness must do with one selected resource requirement."""

    RUN = "run"
    SKIP = "skip"
    FAILURE = "failure"


class ResourceContractError(ValueError):
    """Raised when a requirement or opened capability is malformed."""


@dataclass(frozen=True, slots=True)
class PlanetaryKernelFingerprint:
    """Immutable filesystem identity for one probed kernel resource."""

    resolved_path: Path
    size: int
    mtime_ns: int
    device_id: int | None
    file_id: int | None

    def __post_init__(self) -> None:
        try:
            resolved_path = Path(self.resolved_path)
        except (TypeError, ValueError) as exc:
            raise ResourceContractError(
                "fingerprint resolved_path must be path-like"
            ) from exc
        if not resolved_path.is_absolute():
            raise ResourceContractError(
                "fingerprint resolved_path must be absolute"
            )
        _require_int("fingerprint size", self.size)
        if self.size < 0:
            raise ResourceContractError(
                "fingerprint size must not be negative"
            )
        _require_int("fingerprint mtime_ns", self.mtime_ns)
        for name, value in (
            ("fingerprint device_id", self.device_id),
            ("fingerprint file_id", self.file_id),
        ):
            if value is not None:
                _require_int(name, value)
                if value < 0:
                    raise ResourceContractError(
                        f"{name} must not be negative"
                    )
        if (self.device_id is None) != (self.file_id is None):
            raise ResourceContractError(
                "fingerprint device_id and file_id must be present together"
            )
        object.__setattr__(self, "resolved_path", resolved_path)

    @classmethod
    def from_path(
        cls,
        path: str | os.PathLike[str],
    ) -> "PlanetaryKernelFingerprint":
        try:
            resolved_path = Path(path).resolve(strict=True)
            metadata = resolved_path.stat()
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ResourceContractError(
                f"cannot fingerprint planetary-kernel candidate {path}: {exc}"
            ) from exc
        if not stat.S_ISREG(metadata.st_mode):
            raise ResourceContractError(
                "planetary-kernel candidate is not a regular file: "
                f"{resolved_path}"
            )

        raw_file_id = getattr(metadata, "st_ino", None)
        raw_device_id = getattr(metadata, "st_dev", None)
        if (
            type(raw_file_id) is int
            and raw_file_id > 0
            and type(raw_device_id) is int
            and raw_device_id >= 0
        ):
            file_id = raw_file_id
            device_id = raw_device_id
        else:
            file_id = None
            device_id = None

        return cls(
            resolved_path=resolved_path,
            size=metadata.st_size,
            mtime_ns=metadata.st_mtime_ns,
            device_id=device_id,
            file_id=file_id,
        )

    def render(self) -> str:
        file_identity = (
            "<unavailable>"
            if self.file_id is None
            else f"{self.device_id}:{self.file_id}"
        )
        return (
            f"path={self.resolved_path};size={self.size};"
            f"mtime_ns={self.mtime_ns};file_id={file_identity}"
        )


@dataclass(frozen=True, slots=True, order=True)
class KernelRoute:
    """One SPK route, named to prevent center/target order reversal."""

    target_naif_id: int
    center_naif_id: int

    def __post_init__(self) -> None:
        _require_int("target_naif_id", self.target_naif_id)
        _require_int("center_naif_id", self.center_naif_id)

    @classmethod
    def from_target_center_pair(
        cls,
        pair: "KernelRoute | tuple[int, int] | list[int]",
    ) -> "KernelRoute":
        if type(pair) is cls:
            return pair
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ResourceContractError(
                "target_center_pairs entries must be (target, center) pairs"
            )
        return cls(target_naif_id=pair[0], center_naif_id=pair[1])

    def render(self) -> str:
        return f"target={self.target_naif_id}/center={self.center_naif_id}"


@dataclass(frozen=True, slots=True, order=True)
class KernelSegmentCapability:
    """Content-derived descriptor truth for one admitted SPK segment."""

    route: KernelRoute
    frame: int
    segment_type: int
    start_jd: float
    end_jd: float

    def __post_init__(self) -> None:
        if type(self.route) is not KernelRoute:
            raise ResourceContractError(
                "segment route must be a KernelRoute"
            )
        _require_int("frame", self.frame)
        _require_int("segment_type", self.segment_type)
        if self.segment_type <= 0:
            raise ResourceContractError(
                "segment_type must be a positive integer"
            )
        start = _require_finite_float("start_jd", self.start_jd)
        end = _require_finite_float("end_jd", self.end_jd)
        if start > end:
            raise ResourceContractError("segment start_jd must not exceed end_jd")
        object.__setattr__(self, "start_jd", start)
        object.__setattr__(self, "end_jd", end)


@dataclass(frozen=True, slots=True)
class PlanetaryKernelRequirement:
    """A typed planetary-resource requirement.

    ``target_center_pairs`` uses the plan's target/center wording.  Each entry
    is a :class:`KernelRoute`, so callers never depend on positional ambiguity.
    ``segment_types`` is an allowed set for the segments serving the requested
    body, route, and interval.  Marker mappings preserve the suite's historical
    plain-marker meaning (DE441); identity-independent admission must be
    requested explicitly with ``generic=True``.
    """

    product: str | None = _PRODUCT
    content_identity: str | None = None
    interval: tuple[float, float] | None = None
    bodies: frozenset[int] = frozenset()
    target_center_pairs: frozenset[KernelRoute] = frozenset()
    frame: int | None = None
    segment_types: frozenset[int] = frozenset()
    native_capability: bool | None = None

    def __post_init__(self) -> None:
        if self.product is not None:
            object.__setattr__(
                self,
                "product",
                _require_identifier("product", self.product),
            )
        if self.content_identity is not None:
            object.__setattr__(
                self,
                "content_identity",
                _require_identifier(
                    "content_identity",
                    self.content_identity,
                ),
            )
        if self.interval is not None:
            if not isinstance(self.interval, (tuple, list)) or len(self.interval) != 2:
                raise ResourceContractError(
                    "interval must be a two-value (start_jd, end_jd) pair"
                )
            start = _require_finite_float("interval start", self.interval[0])
            end = _require_finite_float("interval end", self.interval[1])
            if start > end:
                raise ResourceContractError(
                    "interval start must not exceed interval end"
                )
            object.__setattr__(self, "interval", (start, end))

        try:
            bodies = frozenset(self.bodies)
        except (TypeError, ValueError) as exc:
            raise ResourceContractError(
                "bodies must be an iterable of integers"
            ) from exc
        for body in bodies:
            _require_int("body", body)
        object.__setattr__(self, "bodies", bodies)

        try:
            routes = frozenset(
                KernelRoute.from_target_center_pair(pair)
                for pair in self.target_center_pairs
            )
        except ResourceContractError:
            raise
        except (TypeError, ValueError) as exc:
            raise ResourceContractError(
                "target_center_pairs must be an iterable of "
                "(target, center) pairs"
            ) from exc
        object.__setattr__(self, "target_center_pairs", routes)

        if self.frame is not None:
            _require_int("frame", self.frame)

        try:
            segment_types = frozenset(self.segment_types)
        except (TypeError, ValueError) as exc:
            raise ResourceContractError(
                "segment_types must be an iterable of positive integers"
            ) from exc
        for segment_type in segment_types:
            _require_int("segment type", segment_type)
            if segment_type <= 0:
                raise ResourceContractError(
                    "segment types must be positive integers"
                )
        object.__setattr__(self, "segment_types", segment_types)

        if self.native_capability is not None and not isinstance(
            self.native_capability,
            bool,
        ):
            raise ResourceContractError(
                "native_capability must be true, false, or omitted"
            )

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, object],
    ) -> "PlanetaryKernelRequirement":
        if not isinstance(values, Mapping):
            raise ResourceContractError(
                "planetary-kernel requirement must be a mapping"
            )
        allowed = {
            "product",
            "content_identity",
            "interval",
            "bodies",
            "target_center_pairs",
            "frame",
            "segment_types",
            "native_capability",
            "generic",
        }
        if not all(isinstance(name, str) for name in values):
            raise ResourceContractError(
                "planetary-kernel requirement field names must be strings"
            )
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ResourceContractError(
                "unknown planetary-kernel requirement field(s): "
                + ", ".join(unknown)
            )

        payload = dict(values)
        generic = payload.pop("generic", False)
        if not isinstance(generic, bool):
            raise ResourceContractError("generic must be true or omitted")
        if generic and payload:
            raise ResourceContractError(
                "generic planetary-kernel requirements cannot also declare "
                "capability constraints"
            )
        if generic:
            return cls()
        if not payload:
            return cls(
                content_identity=_HISTORICAL_DEFAULT_IDENTITY,
            )
        requirement = cls(**payload)
        if requirement.is_generic:
            raise ResourceContractError(
                "generic planetary-kernel admission must be declared "
                "explicitly with generic=True"
            )
        return requirement

    @property
    def is_generic(self) -> bool:
        return (
            self.product in (None, _PRODUCT)
            and self.content_identity is None
            and self.interval is None
            and not self.bodies
            and not self.target_center_pairs
            and self.frame is None
            and not self.segment_types
            and self.native_capability is None
        )

    def render(self) -> str:
        fields: list[str] = []
        if self.product is not None:
            fields.append(f"product={self.product}")
        if self.content_identity is not None:
            fields.append(f"identity={self.content_identity}")
        if self.interval is not None:
            fields.append(f"interval={self.interval[0]}..{self.interval[1]}")
        if self.bodies:
            fields.append(
                "bodies=" + ",".join(str(body) for body in sorted(self.bodies))
            )
        if self.target_center_pairs:
            fields.append(
                "routes="
                + ",".join(
                    route.render()
                    for route in sorted(self.target_center_pairs)
                )
            )
        if self.frame is not None:
            fields.append(f"frame={self.frame}")
        if self.segment_types:
            fields.append(
                "segment_types="
                + ",".join(
                    str(segment_type)
                    for segment_type in sorted(self.segment_types)
                )
            )
        if self.native_capability is not None:
            fields.append(
                f"native_capability={str(self.native_capability).lower()}"
            )
        return "planetary-kernel[" + ";".join(fields) + "]"


@dataclass(frozen=True, slots=True)
class PlanetaryKernelCapability:
    """Immutable facts derived from one successfully opened kernel."""

    product: str
    content_identity: str
    summary_label: str
    planetary_ephemeris: str | None
    lunar_ephemeris: str | None
    segments: tuple[KernelSegmentCapability, ...]
    bodies: frozenset[int]
    target_center_pairs: frozenset[KernelRoute]
    frames: frozenset[int]
    segment_types: frozenset[int]
    native_capability: bool

    def __post_init__(self) -> None:
        product = _require_identifier("product", self.product)
        content_identity = _require_identifier(
            "content_identity",
            self.content_identity,
        )
        summary_label = _require_identifier(
            "summary_label",
            self.summary_label,
        )
        planetary_ephemeris = self.planetary_ephemeris
        if planetary_ephemeris is not None:
            planetary_ephemeris = _require_identifier(
                "planetary_ephemeris",
                planetary_ephemeris,
            )
        lunar_ephemeris = self.lunar_ephemeris
        if lunar_ephemeris is not None:
            lunar_ephemeris = _require_identifier(
                "lunar_ephemeris",
                lunar_ephemeris,
            )
        expected_content_identity = planetary_ephemeris or summary_label
        if content_identity != expected_content_identity:
            raise ResourceContractError(
                "content_identity must equal planetary_ephemeris when "
                "present, otherwise summary_label"
            )

        if not isinstance(self.segments, (tuple, list)):
            raise ResourceContractError(
                "capability segments must be a tuple or list of "
                "KernelSegmentCapability values"
            )
        segments = tuple(self.segments)
        if not segments:
            raise ResourceContractError(
                "planetary-kernel capability must contain at least one segment"
            )
        if not all(
            type(segment) is KernelSegmentCapability
            for segment in segments
        ):
            raise ResourceContractError(
                "capability segments must contain only "
                "KernelSegmentCapability values"
            )

        bodies = _canonical_int_set("capability bodies", self.bodies)
        routes = _canonical_route_set(
            "capability target_center_pairs",
            self.target_center_pairs,
        )
        frames = _canonical_int_set("capability frames", self.frames)
        segment_types = _canonical_int_set(
            "capability segment_types",
            self.segment_types,
            positive=True,
        )
        derived_bodies = frozenset(
            segment.route.target_naif_id
            for segment in segments
        )
        derived_routes = frozenset(segment.route for segment in segments)
        derived_frames = frozenset(segment.frame for segment in segments)
        derived_segment_types = frozenset(
            segment.segment_type
            for segment in segments
        )
        if bodies != derived_bodies:
            raise ResourceContractError(
                "capability bodies do not match its segment descriptors"
            )
        if routes != derived_routes:
            raise ResourceContractError(
                "capability target_center_pairs do not match its "
                "segment descriptors"
            )
        if frames != derived_frames:
            raise ResourceContractError(
                "capability frames do not match its segment descriptors"
            )
        if segment_types != derived_segment_types:
            raise ResourceContractError(
                "capability segment_types do not match its segment descriptors"
            )
        if not isinstance(self.native_capability, bool):
            raise ResourceContractError(
                "capability native_capability must be true or false"
            )

        object.__setattr__(self, "product", product)
        object.__setattr__(self, "content_identity", content_identity)
        object.__setattr__(self, "summary_label", summary_label)
        object.__setattr__(
            self,
            "planetary_ephemeris",
            planetary_ephemeris,
        )
        object.__setattr__(self, "lunar_ephemeris", lunar_ephemeris)
        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "bodies", bodies)
        object.__setattr__(self, "target_center_pairs", routes)
        object.__setattr__(self, "frames", frames)
        object.__setattr__(self, "segment_types", segment_types)


@dataclass(frozen=True, slots=True)
class PlanetaryKernelCandidate:
    """A location candidate plus the policy that selected it."""

    path: Path
    explicit: bool
    source: str
    fingerprint: PlanetaryKernelFingerprint | None = None

    def __post_init__(self) -> None:
        try:
            path = Path(self.path)
        except (TypeError, ValueError) as exc:
            raise ResourceContractError(
                "candidate path must be path-like"
            ) from exc
        if not isinstance(self.explicit, bool):
            raise ResourceContractError(
                "candidate explicit must be true or false"
            )
        if self.fingerprint is not None and type(
            self.fingerprint
        ) is not PlanetaryKernelFingerprint:
            raise ResourceContractError(
                "candidate fingerprint must be a "
                "PlanetaryKernelFingerprint or None"
            )
        object.__setattr__(self, "path", path)
        object.__setattr__(
            self,
            "source",
            _require_identifier("candidate source", self.source),
        )

    def with_fingerprint(
        self,
        fingerprint: PlanetaryKernelFingerprint,
    ) -> "PlanetaryKernelCandidate":
        if type(fingerprint) is not PlanetaryKernelFingerprint:
            raise ResourceContractError(
                "candidate fingerprint must be a "
                "PlanetaryKernelFingerprint"
            )
        return PlanetaryKernelCandidate(
            path=self.path,
            explicit=self.explicit,
            source=self.source,
            fingerprint=fingerprint,
        )


@dataclass(frozen=True, slots=True)
class PlanetaryKernelReceipt:
    """Stable run/skip/failure evidence for one requirement."""

    name: str
    disposition: ResourceDisposition
    requirement: PlanetaryKernelRequirement
    candidate: PlanetaryKernelCandidate | None
    capability: PlanetaryKernelCapability | None
    reason: str
    failure_type: str | None = None

    def __post_init__(self) -> None:
        _require_identifier("receipt name", self.name)
        if not isinstance(self.disposition, ResourceDisposition):
            raise ResourceContractError(
                "receipt disposition must be a ResourceDisposition"
            )
        if not isinstance(self.requirement, PlanetaryKernelRequirement):
            raise ResourceContractError(
                "receipt requirement must be a PlanetaryKernelRequirement"
            )
        if self.candidate is not None and not isinstance(
            self.candidate,
            PlanetaryKernelCandidate,
        ):
            raise ResourceContractError(
                "receipt candidate must be a PlanetaryKernelCandidate or None"
            )
        if self.capability is not None and type(
            self.capability
        ) is not PlanetaryKernelCapability:
            raise ResourceContractError(
                "receipt capability must be a PlanetaryKernelCapability or None"
            )
        if not isinstance(self.reason, str) or not self.reason:
            raise ResourceContractError(
                "receipt reason must be a nonempty string"
            )
        if self.failure_type is not None:
            _require_identifier("receipt failure_type", self.failure_type)

        if self.disposition is ResourceDisposition.RUN:
            if self.candidate is None or self.capability is None:
                raise ResourceContractError(
                    "RUN receipt requires both a candidate and a capability"
                )
            if self.candidate.fingerprint is None:
                raise ResourceContractError(
                    "RUN receipt requires a probed candidate fingerprint"
                )
            if self.failure_type is not None:
                raise ResourceContractError(
                    "RUN receipt must not declare a failure_type"
                )
            mismatches = capability_mismatches(
                self.requirement,
                self.capability,
            )
            if mismatches:
                raise ResourceContractError(
                    "RUN receipt capability does not satisfy its requirement: "
                    + "; ".join(mismatches)
                )
        elif self.disposition is ResourceDisposition.SKIP:
            if self.failure_type is not None:
                raise ResourceContractError(
                    "SKIP receipt must not declare a failure_type"
                )
        elif self.failure_type is None:
            raise ResourceContractError(
                "FAILURE receipt requires a failure_type"
            )

    @property
    def admitted(self) -> bool:
        return self.disposition is ResourceDisposition.RUN

    def render(self) -> str:
        candidate = (
            "<none>"
            if self.candidate is None
            else (
                f"{self.candidate.path} ({self.candidate.source}; "
                "fingerprint="
                + (
                    "<unavailable>"
                    if self.candidate.fingerprint is None
                    else self.candidate.fingerprint.render()
                )
                + ")"
            )
        )
        actual = (
            "<unavailable>"
            if self.capability is None
            else self.capability.content_identity
        )
        failure = (
            ""
            if self.failure_type is None
            else f"; failure_type={self.failure_type}"
        )
        return (
            f"{self.name}: disposition={self.disposition.value}; "
            f"requirement={self.requirement.render()}; "
            f"candidate={candidate}; actual_identity={actual}; "
            f"reason={self.reason}{failure}"
        )


@dataclass(frozen=True, slots=True)
class _ProbeResult:
    capability: PlanetaryKernelCapability | None
    failure_type: str | None
    reason: str


def _require_identifier(name: str, value: object) -> str:
    if type(value) is not str or not value or len(value) > 256:
        raise ResourceContractError(
            f"{name} must be a nonempty string of at most 256 characters"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ResourceContractError(f"{name} must not contain control characters")
    return value


def _require_int(name: str, value: object) -> int:
    if type(value) is not int:
        raise ResourceContractError(f"{name} must be an integer")
    return value


def _canonical_int_set(
    name: str,
    values: object,
    *,
    positive: bool = False,
) -> frozenset[int]:
    try:
        items = frozenset(values)
    except (TypeError, ValueError) as exc:
        raise ResourceContractError(
            f"{name} must be an iterable of integers"
        ) from exc
    for item in items:
        _require_int(name, item)
        if positive and item <= 0:
            raise ResourceContractError(
                f"{name} must contain only positive integers"
            )
    return items


def _canonical_route_set(
    name: str,
    values: object,
) -> frozenset[KernelRoute]:
    try:
        routes = frozenset(values)
    except (TypeError, ValueError) as exc:
        raise ResourceContractError(
            f"{name} must be an iterable of KernelRoute values"
        ) from exc
    if not all(type(route) is KernelRoute for route in routes):
        raise ResourceContractError(
            f"{name} must contain only KernelRoute values"
        )
    return routes


def _require_finite_float(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ResourceContractError(f"{name} must be a finite number")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ResourceContractError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ResourceContractError(f"{name} must be a finite number")
    return parsed


def discover_planetary_kernel_candidate(
    *,
    environ: Mapping[str, str] | None = None,
    finder: Callable[[], Path | None] | None = None,
) -> PlanetaryKernelCandidate | None:
    """Discover a location without claiming that it is a usable resource."""

    selected_environment = os.environ if environ is None else environ
    explicit_path = selected_environment.get(_KERNEL_PATH_ENV)
    if explicit_path:
        return PlanetaryKernelCandidate(
            Path(explicit_path),
            explicit=True,
            source=_KERNEL_PATH_ENV,
        )

    if finder is None:
        from moira._kernel_paths import find_planetary_kernel

        finder = find_planetary_kernel
    discovered = finder()
    if discovered is None:
        return None
    return PlanetaryKernelCandidate(
        Path(discovered),
        explicit=False,
        source="deterministic search",
    )


def capability_from_reader(
    reader: object,
    *,
    native_detector: Callable[[dict], bool] | None = None,
) -> PlanetaryKernelCapability:
    """Build immutable capability facts from an already opened reader."""

    identity = getattr(reader, "_kernel_identity", None)
    kernel = getattr(reader, "_kernel", None)
    if identity is None or kernel is None:
        raise ResourceContractError(
            "opened planetary reader does not expose admitted catalog identity"
        )

    summary_label = _require_identifier(
        "summary label",
        getattr(identity, "summary_label", None),
    )
    planetary_ephemeris = getattr(identity, "planetary_ephemeris", None)
    lunar_ephemeris = getattr(identity, "lunar_ephemeris", None)
    if planetary_ephemeris is not None:
        planetary_ephemeris = _require_identifier(
            "planetary ephemeris identity",
            planetary_ephemeris,
        )
    if lunar_ephemeris is not None:
        lunar_ephemeris = _require_identifier(
            "lunar ephemeris identity",
            lunar_ephemeris,
        )
    content_identity = planetary_ephemeris or summary_label

    raw_segments = getattr(kernel, "segments", None)
    if not isinstance(raw_segments, (tuple, list)) or not raw_segments:
        raise ResourceContractError(
            "opened planetary reader has no admitted SPK segments"
        )

    segments: list[KernelSegmentCapability] = []
    for index, segment in enumerate(raw_segments):
        try:
            route = KernelRoute(
                target_naif_id=getattr(segment, "target"),
                center_naif_id=getattr(segment, "center"),
            )
            capability = KernelSegmentCapability(
                route=route,
                frame=getattr(segment, "frame"),
                segment_type=getattr(segment, "data_type"),
                start_jd=getattr(segment, "start_jd"),
                end_jd=getattr(segment, "end_jd"),
            )
        except (AttributeError, ResourceContractError) as exc:
            raise ResourceContractError(
                f"opened planetary reader segment {index} is malformed: {exc}"
            ) from exc
        segments.append(capability)

    ordered_segments = tuple(sorted(segments))
    catalog = getattr(kernel, "catalog", None)
    if not isinstance(catalog, dict):
        raise ResourceContractError(
            "opened planetary reader does not expose a DAF/SPK catalog"
        )
    if native_detector is None:
        from moira.spk_reader import _planetary_kernel_native_supported

        native_detector = _planetary_kernel_native_supported
    native_capability = bool(native_detector(catalog))

    return PlanetaryKernelCapability(
        product=_PRODUCT,
        content_identity=content_identity,
        summary_label=summary_label,
        planetary_ephemeris=planetary_ephemeris,
        lunar_ephemeris=lunar_ephemeris,
        segments=ordered_segments,
        bodies=frozenset(
            segment.route.target_naif_id
            for segment in ordered_segments
        ),
        target_center_pairs=frozenset(
            segment.route
            for segment in ordered_segments
        ),
        frames=frozenset(segment.frame for segment in ordered_segments),
        segment_types=frozenset(
            segment.segment_type
            for segment in ordered_segments
        ),
        native_capability=native_capability,
    )


def capability_mismatches(
    requirement: PlanetaryKernelRequirement,
    capability: PlanetaryKernelCapability,
) -> tuple[str, ...]:
    """Return every independently visible mismatch for one capability."""

    mismatches: list[str] = []
    if requirement.product is not None and requirement.product != capability.product:
        mismatches.append(
            f"product expected {requirement.product}, got {capability.product}"
        )

    if requirement.content_identity is not None:
        if requirement.content_identity != capability.content_identity:
            mismatches.append(
                "content_identity expected "
                f"{requirement.content_identity}, got "
                f"{capability.content_identity} "
                f"(summary {capability.summary_label})"
            )

    if (
        requirement.native_capability is not None
        and requirement.native_capability != capability.native_capability
    ):
        mismatches.append(
            "native_capability expected "
            f"{requirement.native_capability}, got "
            f"{capability.native_capability}"
        )

    serving_segments = tuple(
        segment
        for segment in capability.segments
        if (
            requirement.frame is None
            or segment.frame == requirement.frame
        )
        and (
            not requirement.segment_types
            or segment.segment_type in requirement.segment_types
        )
    )

    if requirement.frame is not None and not any(
        segment.frame == requirement.frame
        for segment in capability.segments
    ):
        mismatches.append(
            f"frame {requirement.frame} is not present"
        )
    if requirement.segment_types and not serving_segments:
        mismatches.append(
            "no segment satisfies allowed segment_types "
            + ",".join(
                str(value)
                for value in sorted(requirement.segment_types)
            )
        )

    for route in sorted(requirement.target_center_pairs):
        route_segments = tuple(
            segment
            for segment in serving_segments
            if segment.route == route
        )
        if not route_segments:
            mismatches.append(f"route {route.render()} is not present")
            continue
        if requirement.interval is not None and not _segments_cover_interval(
            route_segments,
            requirement.interval,
        ):
            mismatches.append(
                f"route {route.render()} does not continuously cover "
                f"{requirement.interval[0]}..{requirement.interval[1]}"
            )

    for body in sorted(requirement.bodies):
        body_segments = tuple(
            segment
            for segment in serving_segments
            if segment.route.target_naif_id == body
        )
        if not body_segments:
            mismatches.append(f"body target={body} is not present")
            continue
        if requirement.interval is not None:
            routes = {
                segment.route
                for segment in body_segments
            }
            if not any(
                _segments_cover_interval(
                    (
                        segment
                        for segment in body_segments
                        if segment.route == route
                    ),
                    requirement.interval,
                )
                for route in routes
            ):
                mismatches.append(
                    f"body target={body} has no single route continuously "
                    f"covering {requirement.interval[0]}.."
                    f"{requirement.interval[1]}"
                )

    if (
        requirement.interval is not None
        and not requirement.target_center_pairs
        and not requirement.bodies
    ):
        routes = {segment.route for segment in serving_segments}
        if not any(
            _segments_cover_interval(
                (
                    segment
                    for segment in serving_segments
                    if segment.route == route
                ),
                requirement.interval,
            )
            for route in routes
        ):
            mismatches.append(
                "no single route continuously covers "
                f"{requirement.interval[0]}..{requirement.interval[1]}"
            )

    return tuple(mismatches)


def _segments_cover_interval(
    segments: Iterable[KernelSegmentCapability],
    interval: tuple[float, float],
) -> bool:
    start, end = interval
    cursor = start
    for segment in sorted(
        segments,
        key=lambda item: (item.start_jd, item.end_jd),
    ):
        if segment.end_jd < cursor:
            continue
        if segment.start_jd > cursor:
            return False
        cursor = max(cursor, segment.end_jd)
        if cursor >= end:
            return True
    return False


class PlanetaryResourceResolver:
    """Lazily probe one candidate and reuse only its immutable capability."""

    def __init__(
        self,
        candidate: PlanetaryKernelCandidate | None,
        *,
        reader_factory: Callable[[Path], object] | None = None,
        capability_builder: Callable[[object], PlanetaryKernelCapability] | None = None,
        discovery_failure: tuple[str, str] | None = None,
    ) -> None:
        if discovery_failure is not None:
            if candidate is not None:
                raise ResourceContractError(
                    "a discovery failure cannot also provide a candidate"
                )
            if (
                not isinstance(discovery_failure, tuple)
                or len(discovery_failure) != 2
            ):
                raise ResourceContractError(
                    "discovery_failure must be a (failure_type, reason) pair"
                )
            failure_type = _require_identifier(
                "discovery failure_type",
                discovery_failure[0],
            )
            reason = discovery_failure[1]
            if not isinstance(reason, str) or not reason:
                raise ResourceContractError(
                    "discovery failure reason must be a nonempty string"
                )
            discovery_failure = (failure_type, reason)
        self._candidate = candidate
        self._reader_factory = reader_factory
        self._capability_builder = capability_builder
        self._discovery_failure = discovery_failure
        self._probe_result: _ProbeResult | None = None
        self._probe_count = 0
        self._probe_lock = Lock()

    @property
    def probe_count(self) -> int:
        return self._probe_count

    @property
    def cached_capability(self) -> PlanetaryKernelCapability | None:
        if self._probe_result is None:
            return None
        return self._probe_result.capability

    def resolve(
        self,
        requirement: PlanetaryKernelRequirement,
    ) -> PlanetaryKernelReceipt:
        if self._discovery_failure is not None:
            failure_type, reason = self._discovery_failure
            return PlanetaryKernelReceipt(
                name="planetary-kernel",
                disposition=ResourceDisposition.FAILURE,
                requirement=requirement,
                candidate=None,
                capability=None,
                reason=reason,
                failure_type=failure_type,
            )
        if self._candidate is None:
            return PlanetaryKernelReceipt(
                name="planetary-kernel",
                disposition=ResourceDisposition.SKIP,
                requirement=requirement,
                candidate=None,
                capability=None,
                reason="no planetary-kernel candidate was discovered",
            )

        probe = self._probe()
        if probe.capability is None:
            return PlanetaryKernelReceipt(
                name="planetary-kernel",
                disposition=ResourceDisposition.FAILURE,
                requirement=requirement,
                candidate=self._candidate,
                capability=None,
                reason=probe.reason,
                failure_type=probe.failure_type,
            )

        mismatches = capability_mismatches(requirement, probe.capability)
        if not mismatches:
            return PlanetaryKernelReceipt(
                name="planetary-kernel",
                disposition=ResourceDisposition.RUN,
                requirement=requirement,
                candidate=self._candidate,
                capability=probe.capability,
                reason="opened content satisfies the declared capability",
            )

        return PlanetaryKernelReceipt(
            name="planetary-kernel",
            disposition=(
                ResourceDisposition.FAILURE
                if self._candidate.explicit
                else ResourceDisposition.SKIP
            ),
            requirement=requirement,
            candidate=self._candidate,
            capability=probe.capability,
            reason="; ".join(mismatches),
            failure_type=(
                "CapabilityMismatch"
                if self._candidate.explicit
                else None
            ),
        )

    def _probe(self) -> _ProbeResult:
        if self._probe_result is not None:
            return self._probe_result
        with self._probe_lock:
            if self._probe_result is not None:
                return self._probe_result
            return self._probe_once()

    def _probe_once(self) -> _ProbeResult:
        self._probe_count += 1

        factory = self._reader_factory
        if factory is None:
            from moira.spk_reader import SpkReader

            factory = SpkReader
        builder = self._capability_builder
        if builder is None:
            builder = capability_from_reader

        reader: object | None = None
        close_attempted = False
        try:
            fingerprint_before = PlanetaryKernelFingerprint.from_path(
                self._candidate.path
            )
            self._candidate = self._candidate.with_fingerprint(
                fingerprint_before
            )
            reader = factory(self._candidate.path)
            capability = builder(reader)
            if type(capability) is not PlanetaryKernelCapability:
                raise ResourceContractError(
                    "capability builder must return a "
                    "PlanetaryKernelCapability"
                )
            close = getattr(reader, "close", None)
            if not callable(close):
                raise ResourceContractError(
                    "opened planetary reader has no close() lifecycle"
                )
            close_attempted = True
            close()
            reader = None
            fingerprint_after = PlanetaryKernelFingerprint.from_path(
                self._candidate.path
            )
            if fingerprint_after != fingerprint_before:
                raise ResourceContractError(
                    "planetary-kernel candidate changed while its "
                    "capability was probed"
                )
            self._candidate = self._candidate.with_fingerprint(
                fingerprint_after
            )
        except Exception as exc:
            if reader is not None and not close_attempted:
                close = getattr(reader, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception as close_exc:
                        exc = ResourceContractError(
                            f"{exc}; probe reader close failed: {close_exc}"
                        )
            self._probe_result = _ProbeResult(
                capability=None,
                failure_type=type(exc).__name__,
                reason=f"planetary-kernel probe failed: {exc}",
            )
            return self._probe_result

        self._probe_result = _ProbeResult(
            capability=capability,
            failure_type=None,
            reason="opened content admitted",
        )
        return self._probe_result


def verify_reader_matches_receipt(
    reader: object,
    receipt: PlanetaryKernelReceipt,
) -> PlanetaryKernelCapability:
    """Revalidate a live fixture reader against the immutable probe receipt."""

    if not receipt.admitted or receipt.capability is None:
        raise ResourceContractError(
            "cannot acquire a live reader from a non-admitted receipt"
        )
    recorded_mismatches = capability_mismatches(
        receipt.requirement,
        receipt.capability,
    )
    if recorded_mismatches:
        raise ResourceContractError(
            "admitted planetary-kernel receipt does not satisfy its "
            "requirement: "
            + "; ".join(recorded_mismatches)
        )
    if receipt.candidate is None or receipt.candidate.fingerprint is None:
        raise ResourceContractError(
            "admitted planetary-kernel receipt has no resource fingerprint"
        )
    expected_fingerprint = receipt.candidate.fingerprint
    fingerprint_before = PlanetaryKernelFingerprint.from_path(
        receipt.candidate.path
    )
    if fingerprint_before != expected_fingerprint:
        raise ResourceContractError(
            "planetary-kernel resource fingerprint changed after its "
            "receipt was recorded"
        )

    reader_path = getattr(
        reader,
        "path",
        getattr(reader, "_path", None),
    )
    if reader_path is not None:
        try:
            resolved_reader_path = Path(reader_path).resolve(strict=True)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ResourceContractError(
                f"live planetary reader path cannot be resolved: {exc}"
            ) from exc
        if resolved_reader_path != expected_fingerprint.resolved_path:
            raise ResourceContractError(
                "live planetary reader path does not match the probed "
                "resource fingerprint"
            )

    capability = capability_from_reader(reader)
    fingerprint_after = PlanetaryKernelFingerprint.from_path(
        receipt.candidate.path
    )
    if (
        fingerprint_after != fingerprint_before
        or fingerprint_after != expected_fingerprint
    ):
        raise ResourceContractError(
            "planetary-kernel resource fingerprint changed during live "
            "reader verification"
        )
    if capability != receipt.capability:
        mismatches = capability_mismatches(receipt.requirement, capability)
        detail = "; ".join(mismatches) or "opened capability changed after probe"
        raise ResourceContractError(
            "planetary-kernel changed after its receipt was recorded: "
            + detail
        )
    return capability

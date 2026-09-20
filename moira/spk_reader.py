"""
Moira — spk_reader.py
Governs all binary SPK file access for the Moira ephemeris engine.

Boundary: owns the sole point of contact between Moira and planetary SPK
kernel access in Moira. All planetary kernel I/O is funnelled through this
module. No other module may hold a reference to the active kernel reader or
open the planetary kernel file directly.

Public surface:
    KernelReader (Protocol), SpkReader, KernelPool,
    use_reader_override, get_active_reader, set_kernel_path,
    add_to_global_pool, swap_reader, reset_singleton, MissingKernelError

Import-time side effects: None (kernel is opened lazily on first
    SpkReader instantiation, not at import time).

External dependency assumptions:
    - A compatible JPL SPK planetary kernel must be provided to the
      SpkReader at construction. No default kernel is assumed.
    - The planetary reader is native-only at runtime. jplephem is NOT a runtime
      dependency; it appears solely as an optional dev-time parity oracle in the
      tests. Kernels with segment types the native reader does not support
      (anything other than Type 2/3 Chebyshev) raise plainly rather than falling
      back to any third-party reader.
"""

from __future__ import annotations

import math
import hashlib
import re
import threading
from collections import deque, OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Protocol, runtime_checkable

T0 = 2451545.0
S_PER_DAY = 86400.0


def _jd(seconds: float) -> float:
    return T0 + seconds / S_PER_DAY


def compute_calendar_date(jd_integer: float, julian_before=None):
    jd_integer = int(jd_integer)
    use_gregorian = (julian_before is None) or (jd_integer >= julian_before)
    f = jd_integer + 1401
    f += use_gregorian * ((4 * jd_integer + 274277) // 146097 * 3 // 4 - 38)
    e = 4 * f + 3
    g = e % 1461 // 4
    h = 5 * g + 2
    day = h % 153 // 5 + 1
    month = (h // 153 + 2) % 12 + 1
    year = e // 1461 - 4716 + (12 + 2 - month) // 12
    return year, month, day


class OutOfRangeError(ValueError):
    """Vessel: Signals that an SPK segment was queried outside its admitted coverage span."""
    def __init__(self, message, out_of_range_times):
        self.args = (message,)
        self.out_of_range_times = out_of_range_times


try:
    from jplephem.spk import SPK as _SPK
except ImportError:  # pragma: no cover
    _SPK = None

try:
    from . import moira_native as _moira_native
except ImportError:  # pragma: no cover
    _moira_native = None

from .coordinates import vec_add

Vec3 = tuple[float, float, float]
_HAS_JPLEPHEM = _SPK is not None
_HAS_NATIVE_DAF = _moira_native is not None and hasattr(_moira_native, "read_daf_catalog")
_HAS_NATIVE_SEGMENTS = (
    _moira_native is not None
    and hasattr(_moira_native, "read_spk_chebyshev_segment_payload")
)
_HAS_NATIVE_SPK = _HAS_JPLEPHEM or _HAS_NATIVE_SEGMENTS
_HAS_NATIVE_SEGMENT_EVALUATOR = (
    _moira_native is not None
    and hasattr(_moira_native, "load_spk_segment_evaluator")
)
_HAS_NATIVE_KERNEL_HANDLE = (
    _moira_native is not None
    and hasattr(_moira_native, "open_spk_kernel")
)


@dataclass(frozen=True, slots=True)
class _EphemerisKernelIdentity:
    """Immutable ephemeris identity derived from SPK summary-label content.

    ``lunar_tidal_acceleration_arcsec_per_cy2`` is populated only for a
    source-backed DE/LE pair admitted below.  A coherent but unmapped label is
    still represented explicitly; later correction-sensitive composition owns
    the decision to accept or reject an unknown tidal basis.
    """

    summary_label: str
    planetary_ephemeris: str | None
    lunar_ephemeris: str | None
    lunar_tidal_acceleration_arcsec_per_cy2: float | None


@dataclass(frozen=True, slots=True)
class _KernelSourceIdentity:
    """Path-free immutable identity for one opened SPK source."""

    label: str
    sha256: str
    byte_length: int
    catalog_id: str | None = None
    catalog_version: str | None = None
    manifest_sha256: str | None = None
    released_utc: str | None = None
    planetary_ephemeris: str | None = None
    coverage_restricted_to_observed_arc: bool | None = None


@dataclass(frozen=True, slots=True)
class _SpkSegmentReceipt:
    """The exact SPK descriptor and source that served one state leg."""

    center: int
    target: int
    data_type: int
    coverage_start_tdb: float
    coverage_end_tdb: float
    source: _KernelSourceIdentity
    pool_index: int
    traversal_sign: int = 1


@dataclass(frozen=True, slots=True)
class _RoutedState:
    """One ICRF state together with its ordered, atomic route receipt."""

    position_km: Vec3
    velocity_km_per_day: Vec3
    epoch_tdb: float
    legs: tuple[_SpkSegmentReceipt, ...]
    covered_intervals_tdb: tuple[tuple[float, float], ...]
    pool_generation: int | None = None


@dataclass(frozen=True, slots=True)
class _PoolSnapshot:
    """One immutable view of pool order."""

    readers: tuple[object, ...]
    generation: int
    pair_readers: dict[tuple[int, int], tuple[tuple[int, object], ...]] = field(
        default_factory=dict
    )
    target_readers: dict[int, tuple[tuple[int, object], ...]] = field(
        default_factory=dict
    )
    hub_indices: tuple[int, ...] = ()
    planetary_readers: tuple[tuple[int, object], ...] = ()
    integration_identities: tuple[_EphemerisKernelIdentity, ...] = ()


@dataclass(frozen=True, slots=True)
class _RouteEdge:
    """One directed view of a source SPK segment pair."""

    start: int
    end: int
    source_center: int
    source_target: int
    sign: int
    reader: object
    pool_index: int


_SOURCE_HASH_CACHE_LOCK = threading.Lock()
_SOURCE_HASH_CACHE: dict[tuple[str, int, int], str] = {}


def _source_sha256(path: Path) -> tuple[str, int]:
    """Hash an opened source once per immutable path/stat identity."""

    resolved = path.resolve()
    stat = resolved.stat()
    key = (str(resolved), int(stat.st_size), int(stat.st_mtime_ns))
    with _SOURCE_HASH_CACHE_LOCK:
        cached = _SOURCE_HASH_CACHE.get(key)
    if cached is None:
        digest = hashlib.sha256()
        with resolved.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        cached = digest.hexdigest()
        with _SOURCE_HASH_CACHE_LOCK:
            _SOURCE_HASH_CACHE[key] = cached
    return cached, int(stat.st_size)


def _merge_closed_intervals(
    intervals: tuple[tuple[float, float], ...] | list[tuple[float, float]],
) -> tuple[tuple[float, float], ...]:
    """Merge overlapping or endpoint-touching closed intervals, not gaps."""

    ordered = sorted((float(start), float(end)) for start, end in intervals)
    merged: list[tuple[float, float]] = []
    for start, end in ordered:
        if not math.isfinite(start) or not math.isfinite(end) or start > end:
            raise ValueError("SPK coverage interval must be finite and ordered")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def _intersect_closed_intervals(
    left: tuple[tuple[float, float], ...],
    right: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    """Return exact closed intersections of two disjoint interval sets."""

    intersections: list[tuple[float, float]] = []
    i = j = 0
    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0])
        end = min(left[i][1], right[j][1])
        if start <= end:
            intersections.append((start, end))
        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1
    return _merge_closed_intervals(intersections)


_DE_LE_SUMMARY_LABEL = re.compile(r"^DE-(\d{4})LE-(\d{4})$")

# Product-specific authority mappings only.  HPIERS declares its Delta-T table
# for DE430/LE430 at -25.85 arcsec/cy^2.  JPL's DE440/DE441 release record and
# Horizons historical-Delta-T policy establish -25.936 arcsec/cy^2 for the
# DE440-generation lunar solution.  DE440 and DE441 are admitted separately;
# do not infer any other adjacent DE/LE release from numerical or naming
# similarity.
_ADMITTED_LUNAR_TIDAL_ACCELERATIONS: dict[tuple[str, str], float] = {
    ("DE430", "LE430"): -25.85,
    ("DE440", "LE440"): -25.936,
    ("DE441", "LE441"): -25.936,
}

_PLANETARY_CLOCK_ROUTES: tuple[tuple[int, int], ...] = (
    (0, 3),
    (3, 399),
    (3, 301),
    (0, 10),
)


def _coeff_tensor_shape(coefficients) -> tuple[int, int, int]:
    """Return ``(record_count, component_count, coefficient_count)`` for coefficient tensors."""
    record_count = len(coefficients)
    component_count = len(coefficients[0]) if record_count else 0
    coefficient_count = len(coefficients[0][0]) if component_count else 0
    return record_count, component_count, coefficient_count


def _coeff_record(coefficients, index: int):
    """Return one ``(component, coefficient)`` coefficient record."""
    return coefficients[index]


def _eval_chebyshev_record_scalar(coeff_record, s: float) -> tuple[float, ...]:
    """Evaluate one native-loaded SPK record with scalar Clenshaw recurrence."""
    component_count = len(coeff_record)
    coefficient_count = len(coeff_record[0]) if component_count else 0
    values: list[float] = []

    for component in range(component_count):
        coeffs = coeff_record[component]
        if coefficient_count == 0:
            values.append(0.0)
            continue
        if coefficient_count == 1:
            values.append(float(coeffs[0]))
            continue

        s2 = 2.0 * s
        w1 = 0.0
        w2 = 0.0
        for coeff_index in range(coefficient_count - 1):
            c = float(coeffs[coeff_index])
            old_w1 = w1
            w1 = c + s2 * w1 - w2
            w2 = old_w1
        values.append(float(coeffs[coefficient_count - 1]) + s * w1 - w2)

    return tuple(values)


def _eval_chebyshev_record_with_derivative_scalar(
    coeff_record,
    s: float,
    derivative_scale: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Evaluate one native-loaded SPK record and derivative with scalar Clenshaw recurrence."""
    component_count = len(coeff_record)
    coefficient_count = len(coeff_record[0]) if component_count else 0
    values: list[float] = []
    rates: list[float] = []

    for component in range(component_count):
        coeffs = coeff_record[component]
        if coefficient_count == 0:
            values.append(0.0)
            rates.append(0.0)
            continue
        if coefficient_count == 1:
            values.append(float(coeffs[0]))
            rates.append(0.0)
            continue

        s2 = 2.0 * s
        w1 = 0.0
        w2 = 0.0
        dw1 = 0.0
        dw2 = 0.0

        for coeff_index in range(coefficient_count - 1):
            c = float(coeffs[coeff_index])

            old_dw1 = dw1
            dw1 = (2.0 * w1) + (s2 * dw1 - dw2)
            dw2 = old_dw1

            old_w1 = w1
            w1 = c + s2 * w1 - w2
            w2 = old_w1

        values.append(float(coeffs[coefficient_count - 1]) + s * w1 - w2)
        rates.append((w1 + s * dw1 - dw2) * derivative_scale)

    return tuple(values), tuple(rates)


def _native_spk_record_inputs(segment, jd: float):
    """Return native-evaluable type-2 record inputs or ``None``."""
    if not _HAS_NATIVE_SPK or getattr(segment, "data_type", None) != 2:
        return None

    if hasattr(segment, "_load_data"):
        init, intlen, coefficients = segment._load_data()
        record_count, component_count, coefficient_count = _coeff_tensor_shape(coefficients)
        coeff_record_getter = lambda idx: _coeff_record(coefficients, idx)
    else:
        init, intlen, coefficients = segment._data
        coefficient_count = len(coefficients)
        component_count = len(coefficients[0]) if coefficient_count else 0
        record_count = len(coefficients[0][0]) if component_count else 0

        def coeff_record_getter(idx: int):
            return tuple(
                tuple(float(coefficients[k][component][idx]) for k in range(coefficient_count))
                for component in range(component_count)
            )

    if component_count != 3 or coefficient_count == 0 or record_count == 0:
        return None

    index, offset = divmod((jd - T0) * S_PER_DAY - init, intlen)
    index = int(index)
    if index < 0 or index > record_count:
        return None
    if index == record_count:
        index -= 1
        offset += intlen

    s = 2.0 * offset / intlen - 1.0
    derivative_scale = 2.0 * S_PER_DAY / intlen
    return coeff_record_getter(index), s, derivative_scale


def _native_position(segment, jd: float) -> Vec3 | None:
    inputs = _native_spk_record_inputs(segment, jd)
    if inputs is None:
        return None

    coeff_record, s, _derivative_scale = inputs
    values = _eval_chebyshev_record_scalar(coeff_record, s)
    return (float(values[0]), float(values[1]), float(values[2]))


def _native_position_and_velocity(
    segment, jd: float
) -> tuple[Vec3, Vec3] | None:
    inputs = _native_spk_record_inputs(segment, jd)
    if inputs is None:
        return None

    coeff_record, s, derivative_scale = inputs
    values, rates = _eval_chebyshev_record_with_derivative_scalar(
        coeff_record, s, derivative_scale
    )
    return (
        (float(values[0]), float(values[1]), float(values[2])),
        (float(rates[0]), float(rates[1]), float(rates[2])),
    )


class _NativeSpkKernel:
    """
    RITE: The Native SPK Kernel Holder.

    THEOREM: Holds a native-scanned planetary SPK catalog and materializes
    segment wrappers that preserve the reader-facing kernel surface.

    RITE OF PURPOSE:
        _NativeSpkKernel bridges native DAF catalog discovery to the Python
        reader layer. It packages the kernel path, catalog metadata, optional
        native handle, and wrapped segments into one inspectable object so the
        rest of ``spk_reader.py`` can operate through a stable kernel surface.

    LAW OF OPERATION:
        Responsibilities:
            - Store native-discovered kernel metadata and segment wrappers.
            - Expose a segment list compatible with existing reader flows.
            - Release cached segment payloads and close native handles on teardown.
        Non-responsibilities:
            - Does not parse DAF catalogs itself.
            - Does not evaluate positions directly.
            - Does not own kernel-path resolution policy.
        Dependencies:
            - ``_NativeChebyshevSegment`` for per-segment wrappers.
        Structural invariants:
            - ``segments`` mirrors the summaries present in ``catalog``.
            - ``path`` always identifies the kernel file represented by this holder.
        Failure behavior:
            - Handle close errors are swallowed during cleanup to preserve teardown safety.

    Canon: JPL SPK/DAF kernel organization as mediated by Moira-native scanning.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.spk_reader._NativeSpkKernel",
      "risk": "high",
      "api": {
        "frozen": ["close"],
        "internal": ["path", "catalog", "_handle", "segments"]
      },
      "state": {
        "mutable": true,
        "owners": ["_NativeSpkKernel"]
      },
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only"
      },
      "failures": {
        "policy": "raise"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": ["api_change"]
      }
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, path: Path, catalog: dict, handle=None) -> None:
        self.path = path
        self.catalog = catalog
        self._handle = handle
        self.segments = [
            _NativeChebyshevSegment(
                path, item["name"], item["descriptor"], catalog["little_endian"], handle=handle
            )
            for item in catalog["summaries"]
        ]

    def close(self) -> None:
        for segment in self.segments:
            if "_data" in segment.__dict__:
                del segment._data
        if self._handle is not None:
            try:
                self._handle.close()
            except Exception:
                pass


def _open_kernel(path: Path):
    """Open the planetary kernel through the strongest available reader path."""
    if _moira_native is not None and hasattr(_moira_native, "open_spk_kernel"):
        handle = _moira_native.open_spk_kernel(str(path))
        catalog = handle.catalog()
        if _planetary_kernel_native_supported(catalog):
            return _NativeSpkKernel(path, catalog, handle=handle)
        try:
            handle.close()
        except Exception:
            pass
    elif _moira_native is not None and hasattr(_moira_native, "read_daf_catalog"):
        catalog = _moira_native.read_daf_catalog(str(path))
        if _planetary_kernel_native_supported(catalog):
            return _NativeSpkKernel(path, catalog)
    # Sovereign runtime: the planetary reader is native-only. Unsupported segment
    # types raise plainly; there is no jplephem fallback (jplephem is not a runtime
    # dependency, only an optional dev-time parity oracle in the tests).
    raise RuntimeError(
        f"Kernel '{path}' contains segment types not supported by Moira's native "
        "reader and cannot be opened. This kernel is not part of Moira's standard "
        "supported set. If you are using a custom or third-party SPK kernel, ensure "
        "it uses Type 2 or Type 3 Chebyshev segments."
    )


class _NativeChebyshevSegment:
    """
    RITE: The Native Chebyshev Segment Wrapper.

    THEOREM: Governs access to one native-backed SPK type-2/type-3 segment
    while preserving the jplephem-compatible compute surface expected by Moira.

    RITE OF PURPOSE:
        _NativeChebyshevSegment keeps the reader layer sovereign over native
        segment evaluation. It stores descriptor truth, lazily loads either a
        native evaluator or coefficient payload, and exposes the existing
        position / position-plus-velocity interface without changing callers.

    LAW OF OPERATION:
        Responsibilities:
            - Preserve descriptor truth for a single SPK segment.
            - Lazily load native evaluators or coefficient payloads.
            - Evaluate position and velocity through the strongest available path.
        Non-responsibilities:
            - Does not discover kernels or catalog summaries.
            - Does not own higher-level body routing.
            - Does not mutate upstream kernel metadata.
        Dependencies:
            - native SPK payload readers or evaluator loaders when available.
            - local scalar Chebyshev evaluators as fallback.
        Structural invariants:
            - descriptor-derived fields remain aligned to the source segment.
            - ``start_jd`` and ``end_jd`` derive directly from stored seconds.
        Failure behavior:
            - Out-of-range requests raise ``OutOfRangeError`` through the evaluation path.

    Canon: JPL SPK type-2/type-3 Chebyshev segment semantics.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.spk_reader._NativeChebyshevSegment",
      "risk": "high",
      "api": {
        "frozen": ["compute", "compute_and_differentiate"],
        "internal": ["_load_native_evaluator", "_load_data", "_evaluate"]
      },
      "state": {
        "mutable": true,
        "owners": ["_NativeChebyshevSegment"]
      },
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only"
      },
      "failures": {
        "policy": "raise"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": ["api_change"]
      }
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, path: Path, source: bytes, descriptor, little_endian: bool, handle=None) -> None:
        self.path = path
        self.source = source
        self._little_endian = bool(little_endian)
        self._handle = handle
        (
            self.start_second,
            self.end_second,
            self.target,
            self.center,
            self.frame,
            self.data_type,
            self.start_i,
            self.end_i,
        ) = descriptor
        self.start_jd = _jd(self.start_second)
        self.end_jd = _jd(self.end_second)
        self._data = None
        self._native_evaluator = None

    def compute(self, tdb, tdb2=0.0):
        values, _rates = self._evaluate(float(tdb), float(tdb2), need_rates=False)
        return values

    def compute_and_differentiate(self, tdb, tdb2=0.0):
        return self._evaluate(float(tdb), float(tdb2), need_rates=True)

    def _load_native_evaluator(self):
        if self._native_evaluator is None:
            if self._handle is not None and hasattr(self._handle, "load_segment_evaluator"):
                self._native_evaluator = self._handle.load_segment_evaluator(
                    int(self.start_i),
                    int(self.end_i),
                    int(self.data_type),
                )
            elif _moira_native is not None and hasattr(_moira_native, "load_spk_segment_evaluator"):
                self._native_evaluator = _moira_native.load_spk_segment_evaluator(
                    str(self.path),
                    int(self.start_i),
                    int(self.end_i),
                    self._little_endian,
                    int(self.data_type),
                )
        return self._native_evaluator

    def _load_data(self):
        self._load_native_evaluator()
        if self._data is None:
            payload = _moira_native.read_spk_chebyshev_segment_payload(
                str(self.path),
                int(self.start_i),
                int(self.end_i),
                self._little_endian,
                int(self.data_type),
            )
            self._data = (
                float(payload["init"]),
                float(payload["intlen"]),
                payload["coefficients"],
            )
        return self._data

    def _evaluate(self, tdb: float, tdb2: float, need_rates: bool):
        epoch = float(tdb) + float(tdb2)
        if not self.start_jd <= epoch <= self.end_jd:
            raise OutOfRangeError(
                "segment only covers dates %d-%02d-%02d through %d-%02d-%02d"
                % (
                    compute_calendar_date(self.start_jd + 0.5)
                    + compute_calendar_date(self.end_jd + 0.5)
                ),
                out_of_range_times=True,
            )
        if self._handle is not None:
            if need_rates and hasattr(self._handle, "segment_position_and_velocity"):
                return self._handle.segment_position_and_velocity(
                    int(self.start_i),
                    int(self.end_i),
                    int(self.data_type),
                    tdb,
                    tdb2,
                )
            if not need_rates and hasattr(self._handle, "segment_position"):
                return self._handle.segment_position(
                    int(self.start_i),
                    int(self.end_i),
                    int(self.data_type),
                    tdb,
                    tdb2,
                ), None

        self._load_native_evaluator()
        if self._native_evaluator is not None:
            if need_rates:
                return self._native_evaluator.position_and_velocity(tdb, tdb2)
            return self._native_evaluator.position(tdb, tdb2), None

        init, intlen, coefficients = self._load_data()
        record_count, component_count, coefficient_count = _coeff_tensor_shape(coefficients)

        index1, offset1 = divmod((tdb - T0) * S_PER_DAY - init, intlen)
        index2, offset2 = divmod(tdb2 * S_PER_DAY, intlen)
        index3, offset = divmod(offset1 + offset2, intlen)
        index = int(index1 + index2 + index3)
        if index < 0 or index > record_count:
            raise OutOfRangeError(
                'segment only covers dates %d-%02d-%02d through %d-%02d-%02d'
                % (compute_calendar_date(self.start_jd + 0.5) +
                   compute_calendar_date(self.end_jd + 0.5)),
                out_of_range_times=True,
            )
        if index == record_count:
            index -= 1
            offset += intlen

        s = 2.0 * offset / intlen - 1.0
        derivative_scale = 2.0 * S_PER_DAY / intlen

        coeff_record = _coeff_record(coefficients, index)
        if need_rates:
            values, rates = _eval_chebyshev_record_with_derivative_scalar(
                coeff_record, s, derivative_scale
            )
            return values, rates

        values = _eval_chebyshev_record_scalar(coeff_record, s)
        return values, None


def _summary_label_text(value: object) -> str:
    """Return one native DAF summary label as strict ASCII text."""

    if isinstance(value, bytes):
        try:
            return value.decode("ascii").strip(" \x00")
        except UnicodeDecodeError as exc:
            raise ValueError("SPK summary labels must be ASCII") from exc
    if isinstance(value, str):
        return value.strip(" \x00")
    raise ValueError("SPK summary labels must be bytes or text")


def _validated_planetary_summaries(catalog: dict) -> tuple[dict, ...]:
    """Validate the native catalog facts required by the planetary reader.

    Native runtime catalogs always include the DAF header fields.  Their
    absence remains tolerated for older in-process catalog adapters, but an
    explicit non-SPK marker is never admitted.  Descriptor validation is kept
    here in Python so format facts remain separate from ephemeris policy.
    """

    if not isinstance(catalog, dict):
        raise ValueError("planetary kernel catalog must be a mapping")

    locidw = catalog.get("locidw")
    if locidw is not None and locidw != "DAF/SPK":
        raise ValueError("planetary kernel catalog must identify a DAF/SPK file")
    nd = catalog.get("nd")
    if nd is not None and nd != 2:
        raise ValueError("planetary SPK catalog must declare ND=2")
    ni = catalog.get("ni")
    if ni is not None and ni != 6:
        raise ValueError("planetary SPK catalog must declare NI=6")

    summaries = catalog.get("summaries")
    if not isinstance(summaries, (list, tuple)) or not summaries:
        raise ValueError("planetary SPK catalog must contain at least one summary")

    validated: list[dict] = []
    for index, item in enumerate(summaries):
        if not isinstance(item, dict):
            raise ValueError(f"SPK summary {index} must be a mapping")
        _summary_label_text(item.get("name"))
        descriptor = item.get("descriptor")
        if not isinstance(descriptor, (list, tuple)) or len(descriptor) != 8:
            raise ValueError(f"SPK summary {index} must have an 8-field descriptor")

        start_second, end_second = descriptor[0], descriptor[1]
        if isinstance(start_second, bool) or isinstance(end_second, bool):
            raise ValueError(f"SPK summary {index} coverage must be numeric")
        try:
            start_value = float(start_second)
            end_value = float(end_second)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"SPK summary {index} coverage must be numeric") from exc
        if (
            not math.isfinite(start_value)
            or not math.isfinite(end_value)
            or start_value > end_value
        ):
            raise ValueError(f"SPK summary {index} coverage is invalid")

        for field_name, field_index in (
            ("target", 2),
            ("center", 3),
            ("frame", 4),
            ("data type", 5),
            ("start address", 6),
            ("end address", 7),
        ):
            value = descriptor[field_index]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(
                    f"SPK summary {index} {field_name} must be an integer"
                )
        if descriptor[5] not in (2, 3):
            raise ValueError(
                f"SPK summary {index} data type {descriptor[5]} is unsupported"
            )
        if descriptor[6] <= 0 or descriptor[7] < descriptor[6]:
            raise ValueError(f"SPK summary {index} address range is invalid")
        validated.append(item)

    return tuple(validated)


def _ephemeris_kernel_identity_from_catalog(
    catalog: dict,
) -> _EphemerisKernelIdentity:
    """Derive one coherent DE/LE identity from native SPK summary labels."""

    summaries = _validated_planetary_summaries(catalog)
    labels = {_summary_label_text(item["name"]) for item in summaries}
    if len(labels) != 1:
        raise ValueError(
            "planetary SPK summaries contain mixed ephemeris identity labels"
        )

    label = labels.pop()
    match = _DE_LE_SUMMARY_LABEL.fullmatch(label)
    if match is None:
        return _EphemerisKernelIdentity(label, None, None, None)

    planetary = f"DE{int(match.group(1))}"
    lunar = f"LE{int(match.group(2))}"
    tidal_acceleration = _ADMITTED_LUNAR_TIDAL_ACCELERATIONS.get(
        (planetary, lunar)
    )
    return _EphemerisKernelIdentity(
        summary_label=label,
        planetary_ephemeris=planetary,
        lunar_ephemeris=lunar,
        lunar_tidal_acceleration_arcsec_per_cy2=tidal_acceleration,
    )


def _planetary_kernel_native_supported(catalog: dict) -> bool:
    if not (_HAS_NATIVE_DAF and _HAS_NATIVE_SEGMENTS):
        return False
    try:
        _validated_planetary_summaries(catalog)
    except (TypeError, ValueError):
        return False
    return True


class MissingKernelError(RuntimeError):
    """Raised when get_reader() is called with no planetary kernel configured."""


class MissingEphemerisKernelError(RuntimeError):
    """Raised when a facade operation requires an unavailable planetary kernel."""


@runtime_checkable
class KernelReader(Protocol):
    """
    RITE: The Ephemeris Reader Interface

    THEOREM: KernelReader defines the structural protocol for all ephemeris 
        accessors, ensuring that single-kernel readers and multi-kernel 
        pools remain interchangeable at the architectural boundary.

    RITE OF PURPOSE:
        This protocol exists to enforce a stable, common surface for all 
        computational pillars (Planets, Nodes, Stars). By programming to 
        this interface rather than a concrete implementation, the engine 
        preserves its ability to swap between DE440, DE431, or Small Body 
        Kernels without re-validating the calling logic.

    LAW OF OPERATION:
        Responsibilities:
            - Define the mandatory state-vector query surface.
            - Ensure epoch-aware coverage introspection.
            - Enforce resource lifecycle management (close).
        Non-responsibilities:
            - Implementation of file I/O or polynomial math.
        Structural invariants:
            - Any satisfying class must be thread-safe for concurrent reads.
        
    Canon: NAIF SPICE SPK Specification.

    [MACHINE_CONTRACT v1]
    {
      "scope": "protocol",
      "id": "moira.spk_reader.KernelReader",
      "risk": "critical",
      "api": {
        "frozen": ["position", "position_and_velocity", "has_segment",
                   "has_segment_at", "coverage", "covered_bodies", "close"]
      },
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": ["read (impl dependent)"]},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def position(self, center: int, target: int, jd: float) -> Vec3: ...
    def position_and_velocity(
        self, center: int, target: int, jd: float
    ) -> tuple[Vec3, Vec3]: ...
    def has_segment(self, center: int, target: int) -> bool: ...
    def has_segment_at(self, center: int, target: int, jd: float) -> bool: ...
    def coverage(self) -> dict[tuple[int, int], tuple[float, float]]: ...
    def covered_bodies(self) -> frozenset[int]: ...
    def close(self) -> None: ...


class SpkReader:
    """
    RITE: The Gate to the Planetary Kernel

    THEOREM: SpkReader governs read access to a JPL binary SPK
        kernel file, serving raw barycentric state vectors to all computation
        pillars.

    RITE OF PURPOSE:
        SpkReader is the single authorised gateway between Moira's pure-Python
        astronomy layer and a binary JPL SPK ephemeris file. Without it, no
        planetary position can be computed. It exists to keep one reader-owned
        kernel handle for each live SpkReader instance and to ensure that all
        segment-selection logic (including split multi-epoch layouts) is
        encapsulated in one place rather than scattered across callers.

    LAW OF OPERATION:
        Responsibilities:
            - Open and hold the SPK kernel file handle for the lifetime
              of the instance.
            - Select the correct kernel segment for a given (center, target, jd)
              triple, correctly handling split multi-epoch kernel layouts.
            - Serve barycentric rectangular position vectors (km, ICRF) to
              planets.py and nodes.py.
            - Serve position-and-velocity pairs (km, km/day) when requested.
            - Support context-manager usage for deterministic resource cleanup.
        Non-responsibilities:
            - Does not perform coordinate transforms (ecliptic, equatorial,
              topocentric). That is the responsibility of coordinates.py.
            - Does not convert time systems (TT → UTC, JD → calendar). That
              is the responsibility of julian.py.
            - Its position methods do not cache computed positions. Higher
              calculation layers may attach namespaced memoization state to a
              mutable reader; those callers own its lifecycle and concurrency.
            - Does not validate that NAIF body IDs are astronomically
              meaningful.
        Dependencies:
            - The kernel file at the given path must exist before __init__
              is called.
            - Moira's sovereign runtime requires its native planetary reader.
              jplephem is an optional development-time parity oracle only.
        Structural invariants:
            - self._kernel is always a valid open kernel reader object while
              the instance is alive and close() has not been called.
            - self._path always reflects the path from which the kernel was
              opened.
        Behavioral invariants:
            - position() and position_and_velocity() are pure reads; they
              never modify kernel state.
        Concurrency contract:
            - Concurrent reads through an already-open SpkReader are admitted.
            - Module-level singleton replacement is serialized by the reader
              RLock, but that serialization does not make live hot-swapping
              safe for in-flight request traffic.
            - close() must not race with active reads on the same reader.
        Side effects:
            - Opens a file handle to the kernel on construction.
            - Closes that file handle on close() or __exit__.
        Failure behavior:
            - Raises FileNotFoundError if the kernel path does not exist at
              construction time.
            - Raises KeyError if no segment exists for the requested
              (center, target) pair.
            - close() silently swallows all exceptions to allow safe use in
              finally blocks.
        Performance envelope:
            - Each position() call performs one binary segment lookup and one
              Chebyshev polynomial evaluation. Typical latency is < 1 ms.

    LAW OF THE DATA PATH:
        State ownership: Owns the open SPK kernel file handle and the active
            kernel reader object. No other module may hold a reference to the
            kernel object.
        Mutation rules: The kernel is opened lazily on first call to get_state().
            Once open, the file handle is never closed during normal operation.
        Persistence: Kernel state persists for the lifetime of the SpkReader
            instance. There is no cache invalidation mechanism.
        Cross-pillar boundaries: Serves raw barycentric state vectors to
            planets.py and nodes.py. No other pillar accesses the kernel directly.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.spk_reader.SpkReader",
      "risk": "high",
      "api": {
        "frozen": ["position", "position_and_velocity", "has_segment",
                   "has_segment_at", "close", "path", "__enter__", "__exit__"],
        "internal": ["_segment_for", "_kernel", "_path"]
      },
      "state": {"mutable": true, "owners": ["SpkReader"]},
      "effects": {
        "signals_emitted": [],
        "io": ["SPK kernel file (read)"]
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only",
        "singleton_lifecycle": "serialized_by_module_rlock",
        "notes": [
          "concurrent reads through an open SpkReader are safe"
        ]
      },
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, kernel_path: str | Path) -> None:
        path = Path(kernel_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Planetary kernel not found at {path}. "
                "Ensure a compatible JPL SPK file is accessible."
            )
        self._path = path
        kernel = _open_kernel(path)
        try:
            kernel_identity = _ephemeris_kernel_identity_from_catalog(kernel.catalog)
        except Exception:
            try:
                kernel.close()
            finally:
                raise
        self._kernel = kernel
        self._kernel_identity = kernel_identity
        source_hash, source_bytes = _source_sha256(path)
        self._source_identity = _KernelSourceIdentity(
            label=kernel_identity.summary_label,
            sha256=source_hash,
            byte_length=source_bytes,
            planetary_ephemeris=kernel_identity.planetary_ephemeris,
        )
        self._closed = False
        self._segments_by_pair: dict[tuple[int, int], tuple[object, ...]] = {}
        for segment in self._kernel.segments:
            key = (segment.center, segment.target)
            self._segments_by_pair.setdefault(key, []).append(segment)
        self._segments_by_pair = {
            key: tuple(segments) for key, segments in self._segments_by_pair.items()
        }

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "SpkReader":
        """Return self to support use as a context manager."""
        return self

    def __exit__(self, *_) -> None:
        """Close the kernel file handle on context exit."""
        self.close()

    def close(self) -> None:
        """Release the kernel file handle."""
        if self._closed:
            return
        try:
            self._kernel.close()
        except Exception:
            pass
        finally:
            self._closed = True
            self._kernel = None

    def _ensure_open(self) -> None:
        """Raise if the reader has been closed."""
        if self._closed:
            raise RuntimeError("SpkReader is closed")

    # ------------------------------------------------------------------
    # Core read method
    # ------------------------------------------------------------------

    def _segments_for_pair(self, center: int, target: int) -> tuple[object, ...]:
        """Return all kernel segments for ``(center, target)``."""
        self._ensure_open()
        matches = self._segments_by_pair.get((center, target), ())
        if not matches:
            raise KeyError(f"No segment found for center={center}, target={target}")
        return matches

    def _segment_for_tdb(self, center: int, target: int, epoch_tdb: float):
        """Return the segment covering one explicit TDB Julian day."""

        for segment in self._segments_for_pair(center, target):
            if segment.start_jd <= epoch_tdb <= segment.end_jd:
                return segment
        raise ValueError(
            f"Segments exist for center={center}, target={target} but none "
            f"covers JD(TDB) {epoch_tdb:.9f}. Kernel coverage may not extend "
            "to this epoch."
        )

    def _segment_for(self, center: int, target: int, jd: float):
        """
        Return the kernel segment covering *jd* for the given (center, target) pair.

        SPK kernels may store each body across multiple non-overlapping epochs.
        jplephem's kernel[c, t] returns the last matching segment, which may be
        incorrect for historical dates. This method iterates all segments and
        returns the one whose date range covers *jd*.

        Args:
            center: NAIF body ID of the reference body.
            target: NAIF body ID of the body whose segment is needed.
            jd: Julian Day in Terrestrial Time (TT).

        Returns:
            The jplephem segment object whose start_jd ≤ jd ≤ end_jd.

        Raises:
            KeyError: If no segment is registered for the (center, target)
                identity pair.
            ValueError: If segments exist for the pair but none covers ``jd``
                (temporal coverage failure — the JD is outside the kernel's
                epoch range for that body).

        Side effects:
            None.
        """
        from .julian import tt_to_tdb

        return self._segment_for_tdb(center, target, tt_to_tdb(jd))

    def _receipt_for_segment(
        self,
        segment,
        *,
        pool_index: int = 0,
    ) -> _SpkSegmentReceipt:
        """Build a path-free receipt from the exact serving descriptor."""

        return _SpkSegmentReceipt(
            center=int(segment.center),
            target=int(segment.target),
            data_type=int(segment.data_type),
            coverage_start_tdb=float(segment.start_jd),
            coverage_end_tdb=float(segment.end_jd),
            source=self._source_identity,
            pool_index=int(pool_index),
        )

    def position_tdb(self, center: int, target: int, epoch_tdb: float) -> Vec3:
        """Return an ICRF position at an explicit TDB Julian day."""

        self._ensure_open()
        segment = self._segment_for_tdb(center, target, epoch_tdb)
        native = (
            None
            if hasattr(segment, "_load_native_evaluator")
            else _native_position(segment, epoch_tdb)
        )
        if native is not None:
            return native
        pos = segment.compute(epoch_tdb)
        return (float(pos[0]), float(pos[1]), float(pos[2]))

    def position_and_velocity_tdb(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
    ) -> tuple[Vec3, Vec3]:
        """Return an ICRF state at an explicit TDB Julian day."""

        self._ensure_open()
        segment = self._segment_for_tdb(center, target, epoch_tdb)
        native = (
            None
            if hasattr(segment, "_load_native_evaluator")
            else _native_position_and_velocity(segment, epoch_tdb)
        )
        if native is not None:
            return native
        pos, vel = segment.compute_and_differentiate(epoch_tdb)
        return (
            (float(pos[0]), float(pos[1]), float(pos[2])),
            (float(vel[0]), float(vel[1]), float(vel[2])),
        )

    def position_and_velocity_tdb_with_receipt(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
        *,
        pool_index: int = 0,
    ) -> _RoutedState:
        """Evaluate one direct or reverse state and bind its descriptor."""

        sign = 1.0
        try:
            segment = self._segment_for_tdb(center, target, epoch_tdb)
        except (KeyError, ValueError):
            segment = self._segment_for_tdb(target, center, epoch_tdb)
            sign = -1.0
        pos, vel = self.position_and_velocity_tdb(
            int(segment.center), int(segment.target), epoch_tdb
        )
        if sign < 0.0:
            pos = (-pos[0], -pos[1], -pos[2])
            vel = (-vel[0], -vel[1], -vel[2])
        receipt = replace(
            self._receipt_for_segment(segment, pool_index=pool_index),
            traversal_sign=int(sign),
        )
        return _RoutedState(
            position_km=pos,
            velocity_km_per_day=vel,
            epoch_tdb=float(epoch_tdb),
            legs=(receipt,),
            covered_intervals_tdb=((receipt.coverage_start_tdb, receipt.coverage_end_tdb),),
        )

    def position(self, center: int, target: int, jd: float) -> Vec3:
        """
        Return the position of *target* relative to *center* at *jd* (TT).

        Parameters
        ----------
        center : NAIF body ID of the reference body
        target : NAIF body ID of the body whose position is desired
        jd     : Julian Day in Terrestrial Time (TT)

        Returns
        -------
        (x, y, z) in kilometres, ICRF frame

        Raises:
            KeyError: If no kernel segment covers the requested body pair.

        Side effects:
            None.
        """
        from .julian import tt_to_tdb

        return self.position_tdb(center, target, tt_to_tdb(jd))

    def position_and_velocity(
        self, center: int, target: int, jd: float
    ) -> tuple[Vec3, Vec3]:
        """
        Return position and velocity of *target* relative to *center* at *jd* (TT).

        Args:
            center: NAIF body ID of the reference body.
            target: NAIF body ID of the body whose state is desired.
            jd: Julian Day in Terrestrial Time (TT).

        Returns:
            A two-tuple ``((x, y, z), (vx, vy, vz))`` where positions are in
            kilometres (ICRF) and velocities are in kilometres per day.

        Raises:
            KeyError: If no kernel segment covers the requested body pair.

        Side effects:
            None.
        """
        from .julian import tt_to_tdb

        return self.position_and_velocity_tdb(center, target, tt_to_tdb(jd))

    def has_segment(self, center: int, target: int) -> bool:
        """
        Return True if the kernel contains any segment for ``(center, target)``.

        This is intentionally a pair-existence check, not an epoch-validity
        check. Use :meth:`has_segment_at` when the caller needs to know whether
        a segment exists that is applicable at a specific Julian day.
        """
        self._ensure_open()
        return (center, target) in self._segments_by_pair

    def has_segment_at(self, center: int, target: int, jd: float) -> bool:
        """
        Return True if a segment for ``(center, target)`` covers ``jd``.

        Unlike :meth:`has_segment`, this is epoch-aware and therefore follows
        the same two-epoch selection semantics as :meth:`position` and
        :meth:`position_and_velocity`.
        """
        from .julian import tt_to_tdb

        return self.has_segment_at_tdb(center, target, tt_to_tdb(jd))

    def has_segment_at_tdb(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
    ) -> bool:
        """Return whether a descriptor covers one explicit TDB epoch."""

        try:
            for segment in self._segments_for_pair(center, target):
                if segment.start_jd <= epoch_tdb <= segment.end_jd:
                    return True
        except KeyError:
            return False
        return False

    def coverage_intervals_tdb(
        self,
        center: int,
        target: int,
    ) -> tuple[tuple[float, float], ...]:
        """Return every disjoint closed descriptor interval in TDB."""

        self._ensure_open()
        segments = self._segments_by_pair.get((center, target), ())
        return _merge_closed_intervals(
            [(float(segment.start_jd), float(segment.end_jd)) for segment in segments]
        )

    def _coverage_pairs_tdb(self) -> tuple[tuple[int, int], ...]:
        """Return deterministic pair keys for private route planning."""

        self._ensure_open()
        return tuple(sorted(self._segments_by_pair))

    def _ephemeris_kernel_identity_at_tdb(
        self,
        epoch_tdb: float,
    ) -> _EphemerisKernelIdentity | None:
        """Return this planetary identity only where all clock legs exist."""

        if all(
            self.has_segment_at_tdb(center, target, epoch_tdb)
            for center, target in _PLANETARY_CLOCK_ROUTES
        ):
            return self._kernel_identity
        return None

    def _ephemeris_kernel_identity_at(
        self,
        jd_tt: float,
    ) -> _EphemerisKernelIdentity | None:
        """TT compatibility adapter for private identity selection."""

        from .julian import tt_to_tdb

        return self._ephemeris_kernel_identity_at_tdb(tt_to_tdb(jd_tt))

    def coverage(self) -> dict[tuple[int, int], tuple[float, float]]:
        """
        Return the epoch range covered by each (center, target) pair.

        Returns
        -------
        dict mapping (center_naif_id, target_naif_id) to (start_jd, end_jd).
        For pairs whose data is split across multiple segments, start_jd is
        the earliest segment start and end_jd is the latest segment end.
        """
        from .julian import tdb_to_tt

        self._ensure_open()
        result: dict[tuple[int, int], tuple[float, float]] = {}
        for pair in self._segments_by_pair:
            intervals = self.coverage_intervals_tdb(*pair)
            result[pair] = (
                tdb_to_tt(intervals[0][0]),
                tdb_to_tt(intervals[-1][1]),
            )
        return result

    def covered_bodies(self) -> frozenset[int]:
        """Return the set of target NAIF IDs present in this kernel."""
        self._ensure_open()
        return frozenset(target for _, target in self._segments_by_pair)

    def epoch_range(
        self, center: int, target: int
    ) -> tuple[float, float] | None:
        """
        Return the (start_jd, end_jd) range for a specific (center, target) pair,
        or None if the pair is not present in this kernel.

        For split multi-epoch kernels the range spans from the earliest segment
        start to the latest segment end, which may include a gap if the kernel
        stores non-contiguous epochs for that pair.
        """
        self._ensure_open()
        segs = self._segments_by_pair.get((center, target))
        if not segs:
            return None
        from .julian import tdb_to_tt

        return (
            tdb_to_tt(min(s.start_jd for s in segs)),
            tdb_to_tt(max(s.end_jd for s in segs)),
        )

    @property
    def path(self) -> Path:
        """Path to the open SPK kernel file."""
        return self._path

    def __repr__(self) -> str:
        """Return a concise string representation showing the kernel filename."""
        return f"SpkReader('{self._path.name}')"

    def evaluator(
        self,
        target: int,
        center: int = 0,
        jd_tt: float = 2451545.0,
        *,
        jd_end_tt: float | None = None,
    ) -> object:
        """
        Return a native IEvaluator for *target* relative to *center* at *jd_tt*.

        This method allows other modules to obtain a high-performance C++ evaluator
        for a specific body pair. If ``jd_end_tt`` is supplied, one segment must
        cover the complete inclusive interval; evaluators cannot silently cross
        from one SPK descriptor into another. Otherwise only ``jd_tt`` is tested.

        Returns ``None`` when no single native segment covers the request.
        """
        from .julian import tt_to_tdb

        self._ensure_open()
        if jd_end_tt is not None and jd_end_tt < jd_tt:
            raise ValueError("jd_end_tt must be greater than or equal to jd_tt")
        epoch_tdb = tt_to_tdb(jd_tt)
        epoch_end_tdb = None if jd_end_tt is None else tt_to_tdb(jd_end_tt)
        raw = self.evaluator_tdb(
            target,
            center,
            epoch_tdb=epoch_tdb,
            epoch_end_tdb=epoch_end_tdb,
        )
        if raw is None:
            return None
        if _moira_native is None or not hasattr(_moira_native, "TtToTdbEvaluator"):
            raise RuntimeError(
                "native TT-to-TDB evaluator adapter is unavailable; rebuild Moira"
            )
        return _moira_native.TtToTdbEvaluator(raw)

    def evaluator_tdb(
        self,
        target: int,
        center: int = 0,
        *,
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ) -> object:
        """Return one raw native evaluator selected on explicit TDB coverage."""

        self._ensure_open()
        if epoch_end_tdb is not None and epoch_end_tdb < epoch_tdb:
            raise ValueError(
                "epoch_end_tdb must be greater than or equal to epoch_tdb"
            )
        try:
            if epoch_end_tdb is None:
                segment = self._segment_for_tdb(center, target, epoch_tdb)
            else:
                segment = next(
                    (
                        candidate
                        for candidate in self._segments_for_pair(center, target)
                        if candidate.start_jd <= epoch_tdb
                        and epoch_end_tdb <= candidate.end_jd
                    ),
                    None,
                )
                if segment is None:
                    return None
        except (KeyError, ValueError):
            return None
        if hasattr(segment, '_load_native_evaluator'):
            return segment._load_native_evaluator()
        return None


# Capture original class for type-safe checks in shims (prevents 
# auto-discovery regressions in unit tests that monkeypatch SpkReader).
_OriginalSpkReader = SpkReader


# ---------------------------------------------------------------------------
# KernelPool — ordered multi-kernel reader with fallback
# ---------------------------------------------------------------------------

class KernelPool:
    """
    RITE: The Unified Ephemeris Reservoir

    THEOREM: KernelPool governs a fallback-ordered chain of ephemeris
        readers, synthesizing multiple discrete kernels into a single 
        coherent astronomical truth-source.

    RITE OF PURPOSE:
        Moira's planetary truth is often fragmented across multiple 
        files (e.g., DE441 for the planets + a separate BSP for a 
        specific asteroid). KernelPool exists to hide this fragmentation 
        from the rest of the engine. It ensures that the caller receives 
        the highest-priority data available for any given epoch without 
        knowing which specific kernel served the request.

    LAW OF OPERATION:
        Responsibilities:
            - Manage an ordered fallback chain of KernelReaders.
            - Dispatch queries to the first reader covering the epoch.
            - Attempt resource cleanup for every reader in the pool.
        Non-responsibilities:
            - Does not own the files directly (delegates to managed readers).
            - Does not merge overlapping segment data (first-match-wins).
        Dependencies:
            - All managed readers must satisfy the KernelReader protocol.
        Side effects:
            - Calling close() propagates to all managed readers.
        
    Canon: None (Implementation-specific aggregation).

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.spk_reader.KernelPool",
      "risk": "high",
      "api": {
        "frozen": ["position", "position_and_velocity", "has_segment",
                   "has_segment_at", "coverage", "covered_bodies", "close", "add"]
      },
      "state": {"mutable": true, "owners": ["KernelPool"]},
      "effects": {"signals_emitted": [], "io": ["managed reader delegation"]},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, readers=()) -> None:
        self._readers: tuple[object, ...] = tuple(readers)
        self._condition = threading.Condition(threading.RLock())
        self._generation = 0
        self._active_leases = 0
        self._closing = False
        self._closed = False
        self._route_cache_lock = threading.Lock()
        self._route_cache: OrderedDict[
            tuple[int, int],
            tuple[float, float, tuple[_RouteEdge, ...]],
        ] = OrderedDict()
        self._pair_readers: dict[tuple[int, int], tuple[tuple[int, object], ...]] = {}
        self._target_readers: dict[int, tuple[tuple[int, object], ...]] = {}
        self._hub_indices: tuple[int, ...] = ()
        self._planetary_readers: tuple[tuple[int, object], ...] = ()
        self._integration_identities: tuple[_EphemerisKernelIdentity, ...] = ()
        self._rebuild_indices_locked()

    def _rebuild_indices_locked(self) -> None:
        """Construct deterministic lookup indices across the current reader chain."""
        pair_readers: dict[tuple[int, int], list[tuple[int, object]]] = {}
        target_readers: dict[int, list[tuple[int, object]]] = {}
        hub_indices: list[int] = []
        planetary_readers: list[tuple[int, object]] = []
        integration_identities_set: set[_EphemerisKernelIdentity] = set()

        for pool_index, reader in enumerate(self._readers):
            pairs = self._reader_pairs_tdb(reader)
            if not pairs:
                cov = getattr(reader, "coverage", None)
                if callable(cov):
                    try:
                        pairs = tuple(sorted(cov().keys()))
                    except Exception:
                        pairs = ()
            if pairs:
                for center, target in pairs:
                    pair_readers.setdefault((center, target), []).append((pool_index, reader))
                    target_readers.setdefault(target, []).append((pool_index, reader))
                    target_readers.setdefault(center, []).append((pool_index, reader))
            identity = getattr(reader, "_kernel_identity", None)
            is_primary = (
                isinstance(identity, _EphemerisKernelIdentity)
                and identity.planetary_ephemeris is not None
                and identity.lunar_ephemeris is not None
            )
            if isinstance(identity, _EphemerisKernelIdentity):
                planetary_readers.append((pool_index, reader))
            integration_identity = getattr(reader, "_integration_kernel_identity", None)
            if isinstance(integration_identity, _EphemerisKernelIdentity):
                integration_identities_set.add(integration_identity)

            is_spine = any(
                pair in pairs
                for pair in ((0, 3), (3, 399), (0, 10), (3, 301))
            )
            if is_primary or is_spine or pool_index == 0:
                hub_indices.append(pool_index)

        self._pair_readers = {k: tuple(v) for k, v in pair_readers.items()}
        self._target_readers = {k: tuple(v) for k, v in target_readers.items()}
        self._hub_indices = tuple(hub_indices)
        self._planetary_readers = tuple(planetary_readers)
        self._integration_identities = tuple(
            sorted(integration_identities_set, key=lambda idn: idn.summary_label)
        )

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------

    def add(self, reader) -> None:
        """Append *reader* to the fallback chain (lowest priority)."""
        with self._condition:
            if self._closing or self._closed:
                raise RuntimeError("KernelPool is closing or closed")
            self._readers = (*self._readers, reader)
            self._generation += 1
            self._rebuild_indices_locked()
            with self._route_cache_lock:
                self._route_cache.clear()

    @contextmanager
    def _read_lease(self):
        """Yield one immutable reader-order generation for a computation."""

        with self._condition:
            if self._closing or self._closed:
                raise RuntimeError("KernelPool is closing or closed")
            self._active_leases += 1
            snapshot = _PoolSnapshot(
                self._readers,
                self._generation,
                self._pair_readers,
                self._target_readers,
                self._hub_indices,
                self._planetary_readers,
                self._integration_identities,
            )
        try:
            yield snapshot
        finally:
            with self._condition:
                self._active_leases -= 1
                if self._active_leases == 0:
                    self._condition.notify_all()

    def _primary_planetary_reader(
        self,
        snapshot: _PoolSnapshot | None = None,
    ):
        """Return the first content-identified planetary reader, if present.

        Pool order is already the explicit priority doctrine.  A pathname is
        never inspected: supplemental readers without a content-derived
        ``_EphemerisKernelIdentity`` are ignored.
        """

        readers = self._readers if snapshot is None else snapshot.readers
        for reader in readers:
            identity = getattr(reader, "_kernel_identity", None)
            if (
                isinstance(identity, _EphemerisKernelIdentity)
                and identity.planetary_ephemeris is not None
                and identity.lunar_ephemeris is not None
            ):
                return reader
        return None

    @property
    def _kernel_identity(self) -> _EphemerisKernelIdentity | None:
        """Return the primary planetary reader's private identity vessel."""

        reader = self._primary_planetary_reader()
        if reader is None:
            return None
        return reader._kernel_identity

    def _ephemeris_kernel_identity_at_tdb(
        self,
        epoch_tdb: float,
        *,
        snapshot: _PoolSnapshot | None = None,
    ) -> _EphemerisKernelIdentity | None:
        """Resolve one coherent planetary identity at a TDB epoch."""

        if snapshot is None:
            with self._read_lease() as leased:
                return self._ephemeris_kernel_identity_at_tdb(
                    epoch_tdb, snapshot=leased
                )

        identities: list[_EphemerisKernelIdentity] = []
        planetary_readers = (
            getattr(snapshot, "planetary_readers", None) or self._planetary_readers
        )
        if planetary_readers:
            for pool_index, reader in planetary_readers:
                identity = getattr(reader, "_kernel_identity", None)
                if isinstance(identity, _EphemerisKernelIdentity):
                    checker = getattr(reader, "has_segment_at_tdb", None)
                    if callable(checker):
                        try:
                            owns_clock_routes = all(
                                checker(center, target, epoch_tdb)
                                for center, target in _PLANETARY_CLOCK_ROUTES
                            )
                        except (KeyError, ValueError, OutOfRangeError):
                            owns_clock_routes = False
                        if owns_clock_routes:
                            identities.append(identity)
        else:
            for reader in snapshot.readers:
                identity = getattr(reader, "_kernel_identity", None)
                if isinstance(identity, _EphemerisKernelIdentity):
                    checker = getattr(reader, "has_segment_at_tdb", None)
                    if callable(checker):
                        try:
                            owns_clock_routes = all(
                                checker(center, target, epoch_tdb)
                                for center, target in _PLANETARY_CLOCK_ROUTES
                            )
                        except (KeyError, ValueError, OutOfRangeError):
                            owns_clock_routes = False
                        if owns_clock_routes:
                            identities.append(identity)

        integration_identities = (
            getattr(snapshot, "integration_identities", None)
            or self._integration_identities
        )
        if not integration_identities:
            gathered_integration: list[_EphemerisKernelIdentity] = []
            for reader in snapshot.readers:
                integration_identity = getattr(
                    reader, "_integration_kernel_identity", None
                )
                if isinstance(integration_identity, _EphemerisKernelIdentity):
                    gathered_integration.append(integration_identity)
            integration_identities = tuple(gathered_integration)

        selected = identities or list(integration_identities)
        if not selected:
            return None
        first = selected[0]
        all_declared = (*identities, *integration_identities)
        if any(identity != first for identity in all_declared[1:]):
            labels = tuple(
                sorted({identity.summary_label for identity in all_declared})
            )
            raise ValueError(
                "KernelPool has conflicting planetary ephemeris identities "
                f"at JD(TDB) {epoch_tdb}: {labels!r}"
            )
        return first

    def _ephemeris_kernel_identity_at(
        self,
        jd_tt: float,
    ) -> _EphemerisKernelIdentity | None:
        """Resolve one coherent planetary/lunar identity at ``jd_tt``.

        Supplemental small-body readers do not own the Earth/Moon/Sun clock
        basis.  A planetary reader is eligible only when it serves the
        canonical SSB, EMB, Earth, Moon, and Sun routes at the requested
        ephemeris epoch.  Overlapping readers with conflicting identities fail
        instead of inheriting ordinary first-match pool dispatch silently.
        """

        from .julian import tt_to_tdb

        epoch_tdb = tt_to_tdb(jd_tt)
        with self._read_lease() as snapshot:
            exact = self._ephemeris_kernel_identity_at_tdb(
                epoch_tdb, snapshot=snapshot
            )
            if exact is not None:
                return exact

            identities: list[_EphemerisKernelIdentity] = []
            for reader in snapshot.readers:
                identity = getattr(reader, "_kernel_identity", None)
                if not isinstance(identity, _EphemerisKernelIdentity):
                    continue
                try:
                    owns_clock_routes = all(
                        reader.has_segment_at(center, target, jd_tt)
                        for center, target in _PLANETARY_CLOCK_ROUTES
                    )
                except (AttributeError, KeyError, ValueError, OutOfRangeError):
                    owns_clock_routes = False
                if owns_clock_routes:
                    identities.append(identity)
            if not identities:
                return None
            first = identities[0]
            if any(identity != first for identity in identities[1:]):
                labels = tuple(
                    sorted({identity.summary_label for identity in identities})
                )
                raise ValueError(
                    "KernelPool has conflicting planetary ephemeris identities "
                    f"at JD(TT) {jd_tt}: {labels!r}"
                )
            return first

    # ------------------------------------------------------------------
    # Core read interface (mirrors SpkReader)
    # ------------------------------------------------------------------

    @staticmethod
    def _reader_pairs_tdb(reader: object) -> tuple[tuple[int, int], ...]:
        getter = getattr(reader, "_coverage_pairs_tdb", None)
        if not callable(getter):
            return ()
        return tuple(getter())

    @staticmethod
    def _interval_covers(
        intervals: tuple[tuple[float, float], ...],
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ) -> bool:
        end = epoch_tdb if epoch_end_tdb is None else epoch_end_tdb
        return any(start <= epoch_tdb and end <= stop for start, stop in intervals)

    def _route_edges_tdb(
        self,
        snapshot: _PoolSnapshot,
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ) -> tuple[_RouteEdge, ...]:
        edges: list[_RouteEdge] = []
        for pool_index, reader in enumerate(snapshot.readers):
            interval_getter = getattr(reader, "coverage_intervals_tdb", None)
            checker = getattr(reader, "has_segment_at_tdb", None)
            if not callable(interval_getter) or not callable(checker):
                continue
            for source_center, source_target in self._reader_pairs_tdb(reader):
                intervals = tuple(interval_getter(source_center, source_target))
                if not self._interval_covers(
                    intervals, epoch_tdb, epoch_end_tdb
                ):
                    continue
                edges.append(
                    _RouteEdge(
                        start=source_center,
                        end=source_target,
                        source_center=source_center,
                        source_target=source_target,
                        sign=1,
                        reader=reader,
                        pool_index=pool_index,
                    )
                )
                edges.append(
                    _RouteEdge(
                        start=source_target,
                        end=source_center,
                        source_center=source_center,
                        source_target=source_target,
                        sign=-1,
                        reader=reader,
                        pool_index=pool_index,
                    )
                )
        return tuple(edges)

    @staticmethod
    def _bfs_route(
        edges: tuple[_RouteEdge, ...] | list[_RouteEdge],
        center: int,
        target: int,
    ) -> tuple[_RouteEdge, ...] | None:
        by_start: dict[int, list[_RouteEdge]] = {}
        for edge in edges:
            by_start.setdefault(edge.start, []).append(edge)

        queue: deque[tuple[int, tuple[_RouteEdge, ...]]] = deque([(center, ())])
        visited = {center}
        while queue:
            node, route = queue.popleft()
            for edge in by_start.get(node, ()):
                next_route = (*route, edge)
                if edge.end == target:
                    return next_route
                if edge.end not in visited:
                    visited.add(edge.end)
                    queue.append((edge.end, next_route))
        return None

    def _find_direct_edge_tdb(
        self,
        snapshot: _PoolSnapshot,
        center: int,
        target: int,
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ) -> tuple[_RouteEdge, ...] | None:
        pair_readers = getattr(snapshot, "pair_readers", None) or self._pair_readers
        if not pair_readers:
            return None

        # Direct (center, target)
        for pool_index, reader in pair_readers.get((center, target), ()):
            if pool_index >= len(snapshot.readers) or snapshot.readers[pool_index] is not reader:
                continue
            interval_getter = getattr(reader, "coverage_intervals_tdb", None)
            checker = getattr(reader, "has_segment_at_tdb", None)
            if not callable(interval_getter) or not callable(checker):
                continue
            intervals = tuple(interval_getter(center, target))
            if self._interval_covers(intervals, epoch_tdb, epoch_end_tdb):
                return (
                    _RouteEdge(
                        start=center,
                        end=target,
                        source_center=center,
                        source_target=target,
                        sign=1,
                        reader=reader,
                        pool_index=pool_index,
                    ),
                )

        # Reverse (target, center)
        for pool_index, reader in pair_readers.get((target, center), ()):
            if pool_index >= len(snapshot.readers) or snapshot.readers[pool_index] is not reader:
                continue
            interval_getter = getattr(reader, "coverage_intervals_tdb", None)
            checker = getattr(reader, "has_segment_at_tdb", None)
            if not callable(interval_getter) or not callable(checker):
                continue
            intervals = tuple(interval_getter(target, center))
            if self._interval_covers(intervals, epoch_tdb, epoch_end_tdb):
                return (
                    _RouteEdge(
                        start=center,
                        end=target,
                        source_center=target,
                        source_target=center,
                        sign=-1,
                        reader=reader,
                        pool_index=pool_index,
                    ),
                )
        return None

    def _find_candidate_route_tdb(
        self,
        snapshot: _PoolSnapshot,
        center: int,
        target: int,
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ) -> tuple[_RouteEdge, ...] | None:
        target_readers = getattr(snapshot, "target_readers", None) or self._target_readers
        if not target_readers:
            return None

        hub_indices = getattr(snapshot, "hub_indices", None) or self._hub_indices
        candidate_indices: set[int] = set(hub_indices)
        for p_idx, _ in target_readers.get(center, ()):
            candidate_indices.add(p_idx)
        for p_idx, _ in target_readers.get(target, ()):
            candidate_indices.add(p_idx)

        if len(candidate_indices) >= len(snapshot.readers):
            return None

        ordered_indices = sorted(
            p_idx for p_idx in candidate_indices if p_idx < len(snapshot.readers)
        )
        edges: list[_RouteEdge] = []
        for pool_index in ordered_indices:
            reader = snapshot.readers[pool_index]
            interval_getter = getattr(reader, "coverage_intervals_tdb", None)
            checker = getattr(reader, "has_segment_at_tdb", None)
            if not callable(interval_getter) or not callable(checker):
                continue
            for source_center, source_target in self._reader_pairs_tdb(reader):
                intervals = tuple(interval_getter(source_center, source_target))
                if not self._interval_covers(intervals, epoch_tdb, epoch_end_tdb):
                    continue
                edges.append(
                    _RouteEdge(
                        start=source_center,
                        end=source_target,
                        source_center=source_center,
                        source_target=source_target,
                        sign=1,
                        reader=reader,
                        pool_index=pool_index,
                    )
                )
                edges.append(
                    _RouteEdge(
                        start=source_target,
                        end=source_center,
                        source_center=source_center,
                        source_target=source_target,
                        sign=-1,
                        reader=reader,
                        pool_index=pool_index,
                    )
                )

        return self._bfs_route(edges, center, target)

    def _find_fallback_route_tdb(
        self,
        snapshot: _PoolSnapshot,
        center: int,
        target: int,
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ) -> tuple[_RouteEdge, ...] | None:
        edges = self._route_edges_tdb(snapshot, epoch_tdb, epoch_end_tdb)
        return self._bfs_route(edges, center, target)

    def _cache_route_locked(
        self,
        cache_key: tuple[int, int],
        route: tuple[_RouteEdge, ...],
        epoch_tdb: float,
        epoch_end_tdb: float | None,
    ) -> None:
        if not route:
            return
        min_valid = -math.inf
        max_valid = math.inf
        for edge in route:
            candidates = self._pair_readers.get(
                (edge.source_center, edge.source_target), ()
            )
            if candidates and candidates[0][0] < edge.pool_index:
                return
            interval_getter = getattr(edge.reader, "coverage_intervals_tdb", None)
            if not callable(interval_getter):
                return
            intervals = interval_getter(edge.source_center, edge.source_target)
            covering = [
                (start, stop)
                for start, stop in intervals
                if start <= epoch_tdb and (epoch_end_tdb is None or epoch_end_tdb <= stop)
            ]
            if not covering:
                return
            min_valid = max(min_valid, covering[0][0])
            max_valid = min(max_valid, covering[0][1])

        if min_valid >= max_valid:
            return

        with self._route_cache_lock:
            self._route_cache[cache_key] = (min_valid, max_valid, route)
            while len(self._route_cache) > 512:
                self._route_cache.popitem(last=False)

    def _find_route_tdb(
        self,
        snapshot: _PoolSnapshot,
        center: int,
        target: int,
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ) -> tuple[_RouteEdge, ...] | None:
        if center == target:
            return ()

        cache_key = (center, target)
        with self._route_cache_lock:
            cached = self._route_cache.get(cache_key)
            if cached is not None:
                start_valid, end_valid, cached_route = cached
                req_end = epoch_tdb if epoch_end_tdb is None else epoch_end_tdb
                if start_valid <= epoch_tdb and req_end <= end_valid:
                    self._route_cache.move_to_end(cache_key)
                    return cached_route

        direct_route = self._find_direct_edge_tdb(
            snapshot, center, target, epoch_tdb, epoch_end_tdb
        )
        if direct_route is not None:
            self._cache_route_locked(cache_key, direct_route, epoch_tdb, epoch_end_tdb)
            return direct_route

        candidate_route = self._find_candidate_route_tdb(
            snapshot, center, target, epoch_tdb, epoch_end_tdb
        )
        if candidate_route is not None:
            self._cache_route_locked(cache_key, candidate_route, epoch_tdb, epoch_end_tdb)
            return candidate_route

        fallback_route = self._find_fallback_route_tdb(
            snapshot, center, target, epoch_tdb, epoch_end_tdb
        )
        if fallback_route is not None:
            self._cache_route_locked(cache_key, fallback_route, epoch_tdb, epoch_end_tdb)
            return fallback_route

        return None

    @staticmethod
    def _route_is_receiptable(route: tuple[_RouteEdge, ...]) -> bool:
        """Return whether every route leg can bind state to an exact source.

        Runtime ``SpkReader`` and ``SmallBodyKernel`` instances always carry a
        ``_KernelSourceIdentity``.  Historical third-party readers (and older
        protocol test doubles) may expose the newer TDB-shaped methods without
        carrying that identity.  Those readers must remain on the public TT
        compatibility path rather than producing an incomplete receipt.
        """

        return all(
            isinstance(getattr(edge.reader, "_source_identity", None), _KernelSourceIdentity)
            and callable(
                getattr(edge.reader, "position_and_velocity_tdb_with_receipt", None)
            )
            for edge in route
        )

    def position_and_velocity_tdb_with_receipt(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
        *,
        snapshot: _PoolSnapshot | None = None,
    ) -> _RoutedState:
        """Evaluate a deterministic TDB route and bind every serving leg."""

        if snapshot is None:
            with self._read_lease() as leased:
                return self.position_and_velocity_tdb_with_receipt(
                    center, target, epoch_tdb, snapshot=leased
                )
        route = self._find_route_tdb(snapshot, center, target, epoch_tdb)
        if route is None:
            raise OutOfRangeError(
                f"No kernel covers center={center}, target={target} at "
                f"JD(TDB) {epoch_tdb:.9f}",
                out_of_range_times=True,
            )
        return self._evaluate_route_tdb(route, epoch_tdb, snapshot=snapshot)

    def _evaluate_route_tdb(
        self,
        route: tuple[_RouteEdge, ...],
        epoch_tdb: float,
        *,
        snapshot: _PoolSnapshot,
    ) -> _RoutedState:
        """Evaluate one already-selected route against its leased snapshot.

        Stage 2 passage searches use this boundary to prevent ordinary
        epoch-by-epoch pool dispatch from changing the route after a search
        begins.  Callers must retain the lease that produced ``snapshot`` and
        must prove that ``epoch_tdb`` lies in the route's exact common
        coverage before calling.
        """

        if not route:
            return _RoutedState(
                position_km=(0.0, 0.0, 0.0),
                velocity_km_per_day=(0.0, 0.0, 0.0),
                epoch_tdb=float(epoch_tdb),
                legs=(),
                covered_intervals_tdb=((-math.inf, math.inf),),
                pool_generation=snapshot.generation,
            )

        position = (0.0, 0.0, 0.0)
        velocity = (0.0, 0.0, 0.0)
        receipts: list[_SpkSegmentReceipt] = []
        common: tuple[tuple[float, float], ...] | None = None
        for edge in route:
            evaluator = getattr(
                edge.reader, "position_and_velocity_tdb_with_receipt", None
            )
            if not callable(evaluator):
                raise RuntimeError(
                    "selected reader lacks atomic TDB state/source receipt capability"
                )
            state = evaluator(
                edge.source_center,
                edge.source_target,
                epoch_tdb,
                pool_index=edge.pool_index,
            )
            leg_position = state.position_km
            leg_velocity = state.velocity_km_per_day
            if edge.sign < 0:
                leg_position = tuple(-value for value in leg_position)
                leg_velocity = tuple(-value for value in leg_velocity)
            position = tuple(a + b for a, b in zip(position, leg_position))
            velocity = tuple(a + b for a, b in zip(velocity, leg_velocity))
            receipts.extend(
                replace(
                    receipt,
                    traversal_sign=receipt.traversal_sign * edge.sign,
                )
                for receipt in state.legs
            )
            common = (
                state.covered_intervals_tdb
                if common is None
                else _intersect_closed_intervals(
                    common, state.covered_intervals_tdb
                )
            )

        return _RoutedState(
            position_km=position,
            velocity_km_per_day=velocity,
            epoch_tdb=float(epoch_tdb),
            legs=tuple(receipts),
            covered_intervals_tdb=() if common is None else common,
            pool_generation=snapshot.generation,
        )

    def position_tdb(self, center: int, target: int, epoch_tdb: float) -> Vec3:
        """Return a routed ICRF position at an explicit TDB Julian day."""

        return self.position_and_velocity_tdb_with_receipt(
            center, target, epoch_tdb
        ).position_km

    def position_and_velocity_tdb(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
    ) -> tuple[Vec3, Vec3]:
        """Return a routed ICRF state at an explicit TDB Julian day."""

        state = self.position_and_velocity_tdb_with_receipt(
            center, target, epoch_tdb
        )
        return state.position_km, state.velocity_km_per_day

    def position(self, center: int, target: int, jd: float) -> Vec3:
        """
        Return position of *target* relative to *center* at *jd* (TT).

        Phase 1 — direct match: return from the first reader that serves
        (center, target) at jd.

        Phase 2 — center chain: if a reader serves (X, target) where X != center,
        compose: position(X, target) + position(center, X) via recursive pool call.
        First match wins, consistent with phase-1 ordering.

        Raises
        ------
        OutOfRangeError
            If no reader in the pool covers the requested triple by either phase.
        """
        from .julian import tt_to_tdb

        with self._read_lease() as snapshot:
            epoch_tdb = tt_to_tdb(jd)
            route = self._find_route_tdb(snapshot, center, target, epoch_tdb)
            if route is not None and self._route_is_receiptable(route):
                return self.position_and_velocity_tdb_with_receipt(
                    center, target, epoch_tdb, snapshot=snapshot
                ).position_km
            return self._legacy_position(snapshot, center, target, jd, frozenset())

    def _legacy_position(
        self,
        snapshot: _PoolSnapshot,
        center: int,
        target: int,
        jd_tt: float,
        visited: frozenset[tuple[int, int]],
    ) -> Vec3:
        """Preserve the historical protocol for third-party TT readers."""

        key = (center, target)
        if key in visited:
            raise OutOfRangeError(
                f"No acyclic kernel route covers center={center}, target={target}",
                out_of_range_times=True,
            )
        visited = visited | {key}
        for reader in snapshot.readers:
            if reader.has_segment_at(center, target, jd_tt):
                return reader.position(center, target, jd_tt)
            if reader.has_segment_at(target, center, jd_tt):
                value = reader.position(target, center, jd_tt)
                return (-value[0], -value[1], -value[2])
        for reader in snapshot.readers:
            for (source_center, source_target), (start, end) in reader.coverage().items():
                if (
                    source_target == target
                    and source_center != center
                    and start <= jd_tt <= end
                    and reader.has_segment_at(source_center, target, jd_tt)
                ):
                    raw = reader.position(source_center, target, jd_tt)
                    bridge = self._legacy_position(
                        snapshot, center, source_center, jd_tt, visited
                    )
                    return vec_add(raw, bridge)
        raise OutOfRangeError(
            f"No kernel covers center={center}, target={target} at JD(TT) {jd_tt:.9f}",
            out_of_range_times=True,
        )

    def evaluator(
        self,
        target: int,
        center: int = 0,
        jd_tt: float = 2451545.0,
        *,
        jd_end_tt: float | None = None,
    ) -> object:
        """
        Return a native IEvaluator for *target* relative to *center* at *jd_tt*.

        Searches readers in fallback order and returns the first evaluator whose
        one descriptor covers the requested point or inclusive interval.
        """
        from .julian import tt_to_tdb

        if jd_end_tt is not None and jd_end_tt < jd_tt:
            raise ValueError("jd_end_tt must be greater than or equal to jd_tt")
        epoch_tdb = tt_to_tdb(jd_tt)
        epoch_end_tdb = None if jd_end_tt is None else tt_to_tdb(jd_end_tt)
        with self._read_lease() as snapshot:
            route = self._find_route_tdb(
                snapshot, center, target, epoch_tdb, epoch_end_tdb
            )
            if route is not None and self._route_is_receiptable(route):
                raw = self._evaluator_tdb_from_route(
                    route, epoch_tdb, epoch_end_tdb
                )
                if raw is None:
                    return None
                if _moira_native is None or not hasattr(
                    _moira_native, "TtToTdbEvaluator"
                ):
                    raise RuntimeError(
                        "native TT-to-TDB evaluator adapter is unavailable; rebuild Moira"
                    )
                return _moira_native.TtToTdbEvaluator(raw)

            # Historical third-party protocol: preserve its TT-facing evaluator
            # without claiming the strict TDB/source capability.
            for reader in snapshot.readers:
                try:
                    if (
                        reader.has_segment_at(center, target, jd_tt)
                        and (
                            jd_end_tt is None
                            or reader.has_segment_at(center, target, jd_end_tt)
                        )
                    ):
                        evaluator = getattr(reader, "evaluator", None)
                        if callable(evaluator):
                            result = evaluator(
                                target,
                                center,
                                jd_tt,
                                jd_end_tt=jd_end_tt,
                            )
                            if result is not None:
                                return result
                except (KeyError, AttributeError):
                    continue
        return None

    def _evaluator_tdb_from_route(
        self,
        route: tuple[_RouteEdge, ...],
        epoch_tdb: float,
        epoch_end_tdb: float | None,
    ) -> object | None:
        if _moira_native is None:
            return None
        composite = None
        for edge in route:
            getter = getattr(edge.reader, "evaluator_tdb", None)
            if not callable(getter):
                return None
            evaluator = getter(
                edge.source_target,
                edge.source_center,
                epoch_tdb=epoch_tdb,
                epoch_end_tdb=epoch_end_tdb,
            )
            if evaluator is None:
                return None
            if edge.sign < 0:
                evaluator = _moira_native.NegateEvaluator(evaluator)
            composite = (
                evaluator
                if composite is None
                else _moira_native.SumEvaluator(composite, evaluator)
            )
        return composite

    def evaluator_tdb(
        self,
        target: int,
        center: int = 0,
        *,
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ) -> object | None:
        """Return a raw native composite selected on explicit TDB coverage."""

        if epoch_end_tdb is not None and epoch_end_tdb < epoch_tdb:
            raise ValueError(
                "epoch_end_tdb must be greater than or equal to epoch_tdb"
            )
        with self._read_lease() as snapshot:
            route = self._find_route_tdb(
                snapshot, center, target, epoch_tdb, epoch_end_tdb
            )
            if route is None:
                return None
            return self._evaluator_tdb_from_route(
                route, epoch_tdb, epoch_end_tdb
            )

    def position_and_velocity(
        self, center: int, target: int, jd: float
    ) -> tuple[Vec3, Vec3]:
        """
        Return position and velocity of *target* relative to *center* at *jd*.

        SmallBodyKernel readers raise NotImplementedError from their own
        position_and_velocity — no special dispatch needed here.

        Raises
        ------
        OutOfRangeError
            If no reader in the pool covers the requested triple.
        NotImplementedError
            If the covering reader is a SmallBodyKernel.
        """
        from .julian import tt_to_tdb

        with self._read_lease() as snapshot:
            epoch_tdb = tt_to_tdb(jd)
            route = self._find_route_tdb(snapshot, center, target, epoch_tdb)
            if route is not None and self._route_is_receiptable(route):
                state = self.position_and_velocity_tdb_with_receipt(
                    center, target, epoch_tdb, snapshot=snapshot
                )
                return state.position_km, state.velocity_km_per_day
            return self._legacy_position_and_velocity(
                snapshot, center, target, jd, frozenset()
            )

    def _legacy_position_and_velocity(
        self,
        snapshot: _PoolSnapshot,
        center: int,
        target: int,
        jd_tt: float,
        visited: frozenset[tuple[int, int]],
    ) -> tuple[Vec3, Vec3]:
        """Velocity-capable center chaining for historical TT readers."""

        key = (center, target)
        if key in visited:
            raise OutOfRangeError(
                f"No acyclic kernel route covers center={center}, target={target}",
                out_of_range_times=True,
            )
        visited = visited | {key}
        for reader in snapshot.readers:
            if reader.has_segment_at(center, target, jd_tt):
                return reader.position_and_velocity(center, target, jd_tt)
            if reader.has_segment_at(target, center, jd_tt):
                position, velocity = reader.position_and_velocity(
                    target, center, jd_tt
                )
                return (
                    tuple(-value for value in position),
                    tuple(-value for value in velocity),
                )
        for reader in snapshot.readers:
            for (source_center, source_target), (start, end) in reader.coverage().items():
                if (
                    source_target == target
                    and source_center != center
                    and start <= jd_tt <= end
                    and reader.has_segment_at(source_center, target, jd_tt)
                ):
                    raw_position, raw_velocity = reader.position_and_velocity(
                        source_center, target, jd_tt
                    )
                    bridge_position, bridge_velocity = (
                        self._legacy_position_and_velocity(
                            snapshot,
                            center,
                            source_center,
                            jd_tt,
                            visited,
                        )
                    )
                    return (
                        tuple(
                            a + b
                            for a, b in zip(raw_position, bridge_position)
                        ),
                        tuple(
                            a + b
                            for a, b in zip(raw_velocity, bridge_velocity)
                        ),
                    )
        raise OutOfRangeError(
            f"No kernel covers center={center}, target={target} at JD(TT) {jd_tt:.9f}",
            out_of_range_times=True,
        )

    # ------------------------------------------------------------------
    # Segment presence checks
    # ------------------------------------------------------------------

    def has_segment(self, center: int, target: int) -> bool:
        """Return True if any reader in the pool covers (center, target)."""
        with self._read_lease() as snapshot:
            for reader in snapshot.readers:
                if reader.has_segment(center, target):
                    return True
        return False

    def has_segment_at(self, center: int, target: int, jd: float) -> bool:
        """Return True if any reader covers (center, target) at *jd*."""
        from .julian import tt_to_tdb

        epoch_tdb = tt_to_tdb(jd)
        with self._read_lease() as snapshot:
            for reader in snapshot.readers:
                pairs = self._reader_pairs_tdb(reader)
                if (center, target) in pairs:
                    if reader.has_segment_at_tdb(center, target, epoch_tdb):
                        return True
                elif reader.has_segment_at(center, target, jd):
                    return True
        return False

    def has_segment_at_tdb(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
    ) -> bool:
        """Return whether any private-capability reader serves a TDB epoch."""

        with self._read_lease() as snapshot:
            return self._find_route_tdb(
                snapshot, center, target, epoch_tdb
            ) is not None

    # ------------------------------------------------------------------
    # Coverage introspection
    # ------------------------------------------------------------------

    def coverage(self) -> dict[tuple[int, int], tuple[float, float]]:
        """
        Return merged epoch ranges across all readers.

        For pairs present in multiple readers, start_jd is the minimum across
        all readers and end_jd is the maximum — representing the full span of
        available coverage regardless of which reader serves each sub-range.
        """
        merged: dict[tuple[int, int], tuple[float, float]] = {}
        with self._read_lease() as snapshot:
            for reader in snapshot.readers:
                for pair, (start, end) in reader.coverage().items():
                    if pair in merged:
                        previous = merged[pair]
                        merged[pair] = (
                            min(previous[0], start),
                            max(previous[1], end),
                        )
                    else:
                        merged[pair] = (start, end)
        return merged

    def _coverage_pairs_tdb(self) -> tuple[tuple[int, int], ...]:
        """Return every exact-capability pair in deterministic order."""

        with self._read_lease() as snapshot:
            pairs: set[tuple[int, int]] = set()
            for reader in snapshot.readers:
                pairs.update(self._reader_pairs_tdb(reader))
            return tuple(sorted(pairs))

    def coverage_intervals_tdb(
        self,
        center: int,
        target: int,
    ) -> tuple[tuple[float, float], ...]:
        """Return the union of exact TDB intervals across pool readers."""

        intervals: list[tuple[float, float]] = []
        with self._read_lease() as snapshot:
            for reader in snapshot.readers:
                if (center, target) not in self._reader_pairs_tdb(reader):
                    continue
                intervals.extend(reader.coverage_intervals_tdb(center, target))
        return _merge_closed_intervals(intervals)

    def covered_bodies(self) -> frozenset[int]:
        """Return the union of target NAIF IDs across all readers."""
        bodies: set[int] = set()
        with self._read_lease() as snapshot:
            for reader in snapshot.readers:
                bodies.update(reader.covered_bodies())
        return frozenset(bodies)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close all managed readers."""
        with self._condition:
            if self._closed:
                return
            self._closing = True
            while self._active_leases:
                self._condition.wait()
            readers = self._readers
            self._closed = True
        for reader in readers:
            try:
                reader.close()
            except Exception:
                pass

    def __enter__(self) -> "KernelPool":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"KernelPool({len(self._readers)} reader(s))"


# ---------------------------------------------------------------------------
# Reader Override Context
# ---------------------------------------------------------------------------

_reader_override: ContextVar[SpkReader | None] = ContextVar("moira_reader_override", default=None)
_reader: SpkReader | None = None
_reader_path: Path | None = None
_reader_lock = threading.RLock()


def reset_singleton() -> None:
    """
    RITE: The Erasure
    
    THEOREM: reset_singleton ensures that all global state in the reader 
        layer is purged and all file handles are released.

    RITE OF PURPOSE:
        Used primarily in tests and clean shutdowns to ensure that 
        subsequent calls start from a clean, unconfigured state.
    """
    global _reader, _reader_path
    with _reader_lock:
        if _reader is not None:
            _reader.close()
        _reader = None
        _reader_path = None


def swap_reader(new_reader: SpkReader | str | Path | None) -> None:
    """
    RITE: The Substitution
    
    THEOREM: swap_reader allows atomic replacement of the global default 
        reader with a new instance or a new file path.

    Args:
        new_reader: A SpkReader instance, a path to a kernel, or None.
    """
    global _reader, _reader_path
    with _reader_lock:
        if _reader is not None:
            _reader.close()

        if new_reader is None:
            _reader = None
            _reader_path = None
            return None
        elif isinstance(new_reader, (str, Path)):
            _reader = SpkReader(new_reader)
            _reader_path = Path(new_reader)
        else:
            _reader = new_reader
            _reader_path = Path(new_reader.path) if hasattr(new_reader, "path") else None
        return _reader


def set_kernel_path(path: str | Path) -> None:
    """
    RITE: The Legacy Configuration Gate
    
    THEOREM: set_kernel_path allows legacy callers and test bootstraps to 
        establish a global default planetary kernel without using the 
        modern context-aware override.

    RITE OF PURPOSE:
        This function preserves backward compatibility for session-wide 
        kernel configuration (e.g. in test_conftest.py or early engine 
        initialization). It populates a module-level singleton that acts 
        as the ultimate fallback for get_active_reader().

    Args:
        path: Absolute path to a compatible JPL SPK kernel file.
    """
    global _reader, _reader_path
    with _reader_lock:
        if _reader is not None and Path(path) != _reader_path:
            raise RuntimeError(
                f"Cannot change kernel path; SpkReader singleton is already initialized with {_reader_path}. "
                f"Call swap_reader() or reset_singleton() if you must replace it."
            )
        if _reader is not None:
            return
        
        primary_reader = SpkReader(path)
        
        # Discover and add supplemental asteroid/comet kernels 
        # (mirrors Moira facade auto-discovery for the legacy global context)
        found_supplemental = []
        if type(primary_reader) is _OriginalSpkReader:
            try:
                from ._kernel_paths import find_all_small_body_manifests
                from ._spk_body_kernel import small_body_readers_from_manifest

                # Every small body — asteroids (incl. centaurs and TNOs) and the
                # numbered periodic comets — loads from its sovereign shard
                # manifest, discovered under each kernel search root.
                for manifest_path in find_all_small_body_manifests():
                    found_supplemental.extend(small_body_readers_from_manifest(manifest_path))
            except Exception:
                # Supplemental kernel discovery is best-effort: missing shards,
                # unsupported segment types, or import failures must not prevent
                # the primary planetary kernel from initialising.
                pass

        if found_supplemental:
            pool = KernelPool()
            pool.add(primary_reader)
            for s_reader in found_supplemental:
                pool.add(s_reader)
            _reader = pool
        else:
            _reader = primary_reader

        _reader_path = Path(path)


def add_to_global_pool(path: str | Path) -> None:
    """
    RITE: The Cumulative Accord
    
    THEOREM: add_to_global_pool ensures that the provided kernel is added 
        to the active global fallback reader, upgrading it to a 
        KernelPool if necessary.

    Args:
        path: Absolute path to a compatible JPL SPK kernel file.
    """
    global _reader, _reader_path
    with _reader_lock:
        new_reader = SpkReader(path)
        if _reader is None:
            _reader = KernelPool([new_reader])
        elif isinstance(_reader, KernelPool):
            _reader.add(new_reader)
        else:
            # Upgrade SpkReader to KernelPool
            _reader = KernelPool([_reader, new_reader])
        
        # Note: _reader_path for a pool is less meaningful, 
        # but we preserve it as the 'primary' or latest added path.
        _reader_path = Path(path)


@contextmanager
def use_reader_override(reader: SpkReader | None):
    """Temporarily route computational pillars to a caller-owned reader.

    This is safe for per-call reader routing during pure read computation.
    It does not make reader lifecycle mutation safe across threads.
    """
    token = _reader_override.set(reader)
    try:
        yield
    finally:
        _reader_override.reset(token)


def get_active_reader() -> KernelReader | None:
    """
    Return the reader currently active in the ContextVar override, if any.

    This is used by computational pillars to find the reader injected by the
    Moira facade or a manual use_reader_override() context.
    """
    return _reader_override.get() or _reader


def get_reader(path: str | Path | None = None) -> KernelReader:
    """
    Shim for legacy code to retrieve the active contextual reader.

    RITE OF PASSAGE:
        This function bridges the legacy singleton pattern to the modern 
        de-singletonized architecture. It does NOT return a global variable; 
        instead, it retrieves the reader from the active context (ContextVar).
        If no context is active (e.g. outside a Moira facade call), it 
        falls back to the global _reader.

    Args:
        path: Optional path to initialize the global reader if not already set.

    Returns:
        The active KernelReader (SpkReader or KernelPool).

    Raises:
        MissingKernelError: if no reader is found in the current context or global state.
    """
    active = get_active_reader()
    
    # If a path is provided, we must ensure it doesn't conflict with the 
    # already-initialized singleton, UNLESS an override is currently active.
    if path is not None:
        with _reader_lock:
            # If an override is active, we prioritize it and ignore the path 
            # (matches legacy behavior where override 'wins' without checking global path).
            if active is not None and active is _reader_override.get():
                return active

            if _reader is None:
                set_kernel_path(path)
                return get_active_reader()
            elif Path(path) != _reader_path:
                raise RuntimeError(
                    f"Cannot replace the active SpkReader singleton (already initialized with {_reader_path}). "
                    f"Requested {path} would be a silent replacement."
                )

    active = get_active_reader()
    if active is None:
        raise MissingKernelError(
            "Legacy get_reader() called outside an active reader context. "
            "Ensure you are using the Moira facade or use_reader_override()."
        )
    return active

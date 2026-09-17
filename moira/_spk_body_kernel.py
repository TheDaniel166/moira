"""
Native-owned small-body SPK reader infrastructure.

This module provides:
    - _Type13Segment: SPK type 13 (Hermite) segment reader with *preferred* native
      SpkSegmentEvaluator; falls back to the pure-Python reference implementation
      (`_hermite_eval_3d` / `_hermite_eval_3d_with_derivative`) when native is unavailable.
    - _NativeChebyshevSegment: SPK type 2/3 Chebyshev segment reader with preferred native evaluator.
    - SmallBodyKernel: thin wrapper around a native DAF/SPK segment catalog.

The Python Hermite functions are intentionally retained as the permanent guarded
fallback (and as the reference implementation for parity/diagnostic tooling).
The public surface preserves the exact shape used by ``moira.asteroids`` and
``moira.comets`` while removing mandatory runtime dependence on ``jplephem``.
"""

from __future__ import annotations

from bisect import bisect_left
import hashlib
import json
import math
from pathlib import Path

from .coordinates import Vec3
from .spk_reader import (
    _EphemerisKernelIdentity,
    _KernelSourceIdentity,
    _RoutedState,
    _SpkSegmentReceipt,
    _coeff_record,
    _coeff_tensor_shape,
    _eval_chebyshev_record_scalar,
    _eval_chebyshev_record_with_derivative_scalar,
    _merge_closed_intervals,
    _source_sha256,
)

try:
    from . import moira_native as _moira_native
except ImportError:  # pragma: no cover
    _moira_native = None

T0 = 2451545.0
S_PER_DAY = 86400.0
ROOT = Path(__file__).resolve().parents[1]


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
    """Vessel: Signals that a small-body SPK segment was queried outside its admitted coverage span."""
    def __init__(self, message, out_of_range_times):
        self.args = (message,)
        self.out_of_range_times = out_of_range_times


def _validate_segment_epoch(
    tdb: float,
    tdb2: float,
    start_jd: float,
    end_jd: float,
) -> float:
    """Return the combined epoch after enforcing inclusive descriptor truth."""

    epoch = float(tdb) + float(tdb2)
    if not math.isfinite(epoch) or not start_jd <= epoch <= end_jd:
        raise OutOfRangeError(
            "segment only covers dates %d-%02d-%02d through %d-%02d-%02d"
            % (
                compute_calendar_date(start_jd + 0.5)
                + compute_calendar_date(end_jd + 0.5)
            ),
            out_of_range_times=True,
        )
    return epoch


_HAS_NATIVE_DAF = _moira_native is not None and hasattr(_moira_native, "read_daf_catalog")
_HAS_NATIVE_SEGMENTS = (
    _moira_native is not None
    and hasattr(_moira_native, "read_spk_chebyshev_segment_payload")
)
_HAS_NATIVE_TYPE13 = _moira_native is not None and hasattr(
    _moira_native, "read_spk_type13_segment_payload"
)

# Private hooks for benchmarking and differential testing.
# Type 13 (Hermite)
import os as _os
_FORCE_PYTHON_TYPE13_FALLBACK = (
    _os.environ.get("MOIRA_FORCE_PYTHON_TYPE13", "").lower() in ("1", "true", "yes")
)

# Chebyshev (Type 2/3) — added during the 2026-05-30 fine-tooth-comb for consistency
_FORCE_PYTHON_CHEBYSHEV_FALLBACK = (
    _os.environ.get("MOIRA_FORCE_PYTHON_CHEBYSHEV", "").lower() in ("1", "true", "yes")
)


def _hermite_eval_3d(
    t: float,
    ti: list[float],
    pos: list[list[float]],
    vel: list[list[float]],
) -> tuple[float, float, float]:
    """
    Hermite divided-difference interpolation in R^3 (pure Python reference/fallback).

    ROLE (post-Phase 1 native Type 13 wiring):
        This is the **official guarded fallback** implementation of SPK Type 13
        Hermite interpolation. It is used only when the native SpkSegmentEvaluator
        (data_type=13) cannot be loaded or is unavailable.

        It is also the canonical Python reference implementation used by
        adversarial parity tests and diagnostic scripts (e.g. trace_hermite.py)
        to validate the C++ `spk_type13_record_inplace` / Type13SegmentEvaluator
        behavior on both synthetic and real sovereign sb441_type13 shards.

    Numerical contract:
        Must produce results identical (to machine precision on real orbital data)
        with the native C++ path for all admitted window sizes and boundary cases.
        Proven via `test_type13_window_adversarial.py` on real Type 13 data.
    """
    n = len(pos[0])
    m = 2 * n

    z = [0.0] * m
    for i, value in enumerate(ti):
        z[2 * i] = value
        z[2 * i + 1] = value

    prev = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        for i in range(n):
            prev[axis][2 * i] = pos[axis][i]
            prev[axis][2 * i + 1] = pos[axis][i]

    coeffs = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        coeffs[axis][0] = prev[axis][0]

    curr = [[0.0] * (m - 1) for _ in range(3)]
    for i in range(m - 1):
        if i % 2 == 0:
            for axis in range(3):
                curr[axis][i] = vel[axis][i // 2]
        else:
            denom = z[i + 1] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
    for axis in range(3):
        coeffs[axis][1] = curr[axis][0]
    prev = curr

    for j in range(2, m):
        curr = [[0.0] * (m - j) for _ in range(3)]
        for i in range(m - j):
            denom = z[i + j] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
        for axis in range(3):
            coeffs[axis][j] = curr[axis][0]
        prev = curr

    result = [coeffs[axis][m - 1] for axis in range(3)]
    for j in range(m - 2, -1, -1):
        delta = t - z[j]
        for axis in range(3):
            result[axis] = coeffs[axis][j] + delta * result[axis]

    return (result[0], result[1], result[2])


def _hermite_eval_3d_with_derivative(
    t: float,
    ti: list[float],
    pos: list[list[float]],
    vel: list[list[float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """
    Evaluate the Type 13 Hermite interpolant and its exact derivative in one pass
    (pure Python reference/fallback).

    ROLE (post-Phase 1 native Type 13 wiring):
        Companion to `_hermite_eval_3d`. This is the **official guarded fallback**
        for position + velocity (derivative) when the native evaluator is unavailable.

        The caller in `_Type13Segment._evaluate` is responsible for scaling the
        returned rate tuple by S_PER_DAY (the native path already returns velocities
        in km/day units).

        Used by the same adversarial parity tests and diagnostic tooling as the
        non-derivative variant.
    """
    n = len(pos[0])
    m = 2 * n

    z = [0.0] * m
    for i, value in enumerate(ti):
        z[2 * i] = value
        z[2 * i + 1] = value

    prev = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        for i in range(n):
            prev[axis][2 * i] = pos[axis][i]
            prev[axis][2 * i + 1] = pos[axis][i]

    coeffs = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        coeffs[axis][0] = prev[axis][0]

    curr = [[0.0] * (m - 1) for _ in range(3)]
    for i in range(m - 1):
        if i % 2 == 0:
            for axis in range(3):
                curr[axis][i] = vel[axis][i // 2]
        else:
            denom = z[i + 1] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
    for axis in range(3):
        coeffs[axis][1] = curr[axis][0]
    prev = curr

    for j in range(2, m):
        curr = [[0.0] * (m - j) for _ in range(3)]
        for i in range(m - j):
            denom = z[i + j] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
        for axis in range(3):
            coeffs[axis][j] = curr[axis][0]
        prev = curr

    values = [coeffs[axis][m - 1] for axis in range(3)]
    derivatives = [0.0, 0.0, 0.0]
    for j in range(m - 2, -1, -1):
        delta = t - z[j]
        for axis in range(3):
            derivatives[axis] = values[axis] + delta * derivatives[axis]
            values[axis] = coeffs[axis][j] + delta * values[axis]

    return (
        (values[0], values[1], values[2]),
        (derivatives[0], derivatives[1], derivatives[2]),
    )


class _NativeKernelHandle:
    """
    RITE: The Native Small-Body Kernel Handle.

    THEOREM: Governs shared lifetime management for native-owned small-body
    segment wrappers loaded from a single kernel.

    RITE OF PURPOSE:
        _NativeKernelHandle groups the segment wrappers created for one
        native-owned small-body kernel so they can be released together.
        It gives the higher-level kernel wrapper a single teardown surface
        without conflating lifetime management with segment evaluation logic.

    LAW OF OPERATION:
        Responsibilities:
            - Store the live segment wrapper set for one kernel.
            - Release segment-local native caches during teardown.
        Non-responsibilities:
            - Does not evaluate ephemeris values.
            - Does not parse DAF catalogs.
            - Does not own file-path discovery.
        Dependencies:
            - segment wrappers exposing ``_release()`` when needed.
        Structural invariants:
            - ``segments`` is always a concrete list.
        Failure behavior:
            - Teardown is best-effort and skips segments without ``_release``.

    Canon: None (repository lifetime-management helper).

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._spk_body_kernel._NativeKernelHandle",
      "risk": "medium",
      "api": {
        "frozen": ["close"],
        "internal": ["segments"]
      },
      "state": {
        "mutable": true,
        "owners": ["_NativeKernelHandle"]
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
    def __init__(self, segments) -> None:
        self.segments = list(segments)

    def close(self) -> None:
        for segment in self.segments:
            if hasattr(segment, "_release"):
                segment._release()


class _NativeChebyshevSegment:
    """
    RITE: The Native Small-Body Chebyshev Segment.

    THEOREM: Governs one native-backed small-body SPK type-2/type-3 segment
    and preserves the compute surface needed by the small-body kernel layer.

    RITE OF PURPOSE:
        _NativeChebyshevSegment stores descriptor truth for one small-body
        segment, lazily acquires payloads or evaluators, and exposes the
        same position and velocity surface expected by the asteroid/comet
        callers above it.

    LAW OF OPERATION:
        Responsibilities:
            - Preserve one segment descriptor and its time bounds.
            - Load native payloads or evaluators lazily.
            - Evaluate positions and velocities for admitted epochs.
        Non-responsibilities:
            - Does not discover kernels or bodies.
            - Does not own higher-level routing or identity policy.
        Dependencies:
            - native SPK payload/evaluator support when available.
            - local scalar Chebyshev evaluators as fallback.
        Structural invariants:
            - descriptor-derived fields remain aligned with the source segment.
            - ``start_jd`` and ``end_jd`` derive directly from stored seconds.
        Failure behavior:
            - Out-of-range requests raise ``OutOfRangeError``.

    Canon: JPL SPK type-2/type-3 Chebyshev segment semantics.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._spk_body_kernel._NativeChebyshevSegment",
      "risk": "high",
      "api": {
        "frozen": ["compute", "compute_and_differentiate"],
        "internal": ["_release", "_load_data", "_load_native_evaluator", "_evaluate"]
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

    def __init__(self, path: Path, source: bytes, descriptor, little_endian: bool) -> None:
        self.path = path
        self.source = source
        self._little_endian = bool(little_endian)
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

    def _release(self) -> None:
        self._data = None

    def _load_data(self):
        if self._data is None:
            # We pass reverse_coefficients=False to get standard file order [C0, C1, ... Cn]
            # which our Python evaluator now expects.
            payload = _moira_native.read_spk_chebyshev_segment_payload(
                str(self.path),
                int(self.start_i),
                int(self.end_i),
                self._little_endian,
                int(self.data_type),
                False # reverse_coefficients = False
            )
            self._data = (
                float(payload["init"]),
                float(payload["intlen"]),
                payload["coefficients"],
            )
        return self._data

    def _load_native_evaluator(self):
        # Robust to runtime toggling (parallel to Type 13).
        current_force = _FORCE_PYTHON_CHEBYSHEV_FALLBACK
        if getattr(self, "_native_evaluator_force_mode", None) != current_force:
            self._native_evaluator = None
            self._native_evaluator_force_mode = current_force

            if (
                not current_force
                and _HAS_NATIVE_SEGMENTS
                and hasattr(_moira_native, "load_spk_segment_evaluator")
            ):
                self._native_evaluator = _moira_native.load_spk_segment_evaluator(
                    str(self.path),
                    int(self.start_i),
                    int(self.end_i),
                    self._little_endian,
                    int(self.data_type),
                )
        return self._native_evaluator

    def _evaluate(self, tdb: float, tdb2: float, need_rates: bool):
        _validate_segment_epoch(tdb, tdb2, self.start_jd, self.end_jd)
        evaluator = self._load_native_evaluator()
        if evaluator is not None:
            if need_rates:
                return evaluator.position_and_velocity(tdb, tdb2)
            return evaluator.position(tdb, tdb2), None

        init, intlen, coefficients = self._load_data()
        record_count, component_count, coefficient_count = _coeff_tensor_shape(coefficients)

        index1, offset1 = divmod((tdb - T0) * S_PER_DAY - init, intlen)
        index2, offset2 = divmod(tdb2 * S_PER_DAY, intlen)
        index3, offset = divmod(offset1 + offset2, intlen)
        index = int(index1 + index2 + index3)
        if index < 0 or index >= record_count:
            # Boundary handling for exact end matches
            if index == record_count and offset <= 1e-7:
                 index -= 1
                 offset += intlen
            else:
                raise OutOfRangeError(
                    "segment only covers dates %d-%02d-%02d through %d-%02d-%02d"
                    % (
                        compute_calendar_date(self.start_jd + 0.5)
                        + compute_calendar_date(self.end_jd + 0.5)
                    ),
                    out_of_range_times=True,
                )

        coeff_record = _coeff_record(coefficients, index)
        s = 2.0 * offset / intlen - 1.0
        derivative_scale = 2.0 * S_PER_DAY / intlen

        if need_rates:
            values, rates = _eval_chebyshev_record_with_derivative_scalar(
                coeff_record, s, derivative_scale
            )
            return values, rates

        values = _eval_chebyshev_record_scalar(coeff_record, s)
        return values, None

    def compute(self, tdb, tdb2=0.0):
        values, _rates = self._evaluate(float(tdb), float(tdb2), need_rates=False)
        return (float(values[0]), float(values[1]), float(values[2]))

    def compute_and_differentiate(self, tdb, tdb2=0.0):
        values, rates = self._evaluate(float(tdb), float(tdb2), need_rates=True)
        return (
            (float(values[0]), float(values[1]), float(values[2])),
            (float(rates[0]), float(rates[1]), float(rates[2])),
        )


class _Type13Segment:
    """
    RITE: The Native Type-13 Segment Wrapper.

    THEOREM: Governs one SPK type-13 Hermite segment in native-owned small-body
    kernels and exposes a compatible compute interface to callers.

    RITE OF PURPOSE:
        _Type13Segment preserves the descriptor and state truth for one type-13
        segment, lazily loads its payload, and evaluates positions through the
        Hermite interpolation path required by the source segment family.

    LAW OF OPERATION:
        Responsibilities:
            - Store one type-13 descriptor and its derived time bounds.
            - Lazily materialize states, epochs, and window size (for fallback).
            - Prefer native SpkSegmentEvaluator (data_type=13) for Hermite evaluation when available.
            - Fall back to Python divided-difference implementation using loaded state vectors.
            - Evaluate positions and exact Hermite velocities for callers.
        Non-responsibilities:
            - Does not discover kernels or body availability.
            - Does not own the higher-level kernel wrapper.
        Dependencies:
            - native type-13 payload + evaluator support when available.
            - local Hermite interpolation helper as fallback.
        Structural invariants:
            - cached payload remains aligned to the descriptor that produced it.
            - ``start_jd`` and ``end_jd`` derive directly from stored seconds.
            - Native evaluator (when acquired) owns its own copy of the Hermite table.
        Failure behavior:
            - Native payload/evaluator failures fall back to Python path; hard failures propagate.

    Canon: JPL SPK type-13 Hermite segment semantics.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._spk_body_kernel._Type13Segment",
      "risk": "high",
      "api": {
        "frozen": ["compute", "compute_and_differentiate"],
        "internal": ["_release", "_data", "_load_native_evaluator", "_evaluate"]
      },
      "state": {
        "mutable": true,
        "owners": ["_Type13Segment"]
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

    def __init__(self, path: Path, source: bytes, descriptor, little_endian: bool) -> None:
        self.path = path
        self.source = source
        self._little_endian = bool(little_endian)
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
        self.__data = None
        self._native_evaluator = None

    def _release(self) -> None:
        self.__data = None
        self._native_evaluator = None

    @property
    def _data(self):
        if self.__data is None:
            payload = _moira_native.read_spk_type13_segment_payload(
                str(self.path),
                int(self.start_i),
                int(self.end_i),
                self._little_endian,
            )
            states = [list(axis) for axis in payload["states"]]
            epochs_jd = list(payload["epochs_jd"])
            self.__data = (states, epochs_jd, int(payload["window_size"]))
        return self.__data

    def _load_native_evaluator(self):
        # Robust to runtime toggling of _FORCE_PYTHON_TYPE13_FALLBACK (used by benchmarks and differential tests).
        # We track which "force mode" the cached evaluator belongs to.
        current_force = _FORCE_PYTHON_TYPE13_FALLBACK
        if getattr(self, "_native_evaluator_force_mode", None) != current_force:
            self._native_evaluator = None
            self._native_evaluator_force_mode = current_force

            if (
                not current_force
                and _HAS_NATIVE_TYPE13
                and hasattr(_moira_native, "load_spk_segment_evaluator")
            ):
                self._native_evaluator = _moira_native.load_spk_segment_evaluator(
                    str(self.path),
                    int(self.start_i),
                    int(self.end_i),
                    self._little_endian,
                    int(self.data_type),
                )
        return self._native_evaluator

    def _evaluate(self, tdb: float, tdb2: float, need_rates: bool):
        t = _validate_segment_epoch(tdb, tdb2, self.start_jd, self.end_jd)
        evaluator = self._load_native_evaluator()
        if evaluator is not None:
            if need_rates:
                return evaluator.position_and_velocity(tdb, tdb2)
            return evaluator.position(tdb, tdb2), None

        # Fallback path: pure-Python reference Hermite implementation.
        # Only reached when native SpkSegmentEvaluator (data_type=13) is unavailable.
        # This path is intentionally kept as the permanent, no-native-dependency fallback.
        states, epochs_jd, ws = self._data
        idx = bisect_left(epochs_jd, t)
        half = ws // 2
        start = max(0, min(idx - half, len(epochs_jd) - ws))

        win_jd = epochs_jd[start:start + ws]
        win_t = [(jd - T0) * S_PER_DAY for jd in win_jd]
        t_sec = (t - T0) * S_PER_DAY

        pos = [axis[start:start + ws] for axis in states[:3]]
        vel = [axis[start:start + ws] for axis in states[3:]]

        if need_rates:
            position, rate = _hermite_eval_3d_with_derivative(t_sec, win_t, pos, vel)
            return position, tuple(v * S_PER_DAY for v in rate)

        return _hermite_eval_3d(t_sec, win_t, pos, vel), None

    def compute(self, tdb, tdb2=0.0):
        values, _rates = self._evaluate(float(tdb), float(tdb2), need_rates=False)
        return (float(values[0]), float(values[1]), float(values[2]))

    def compute_and_differentiate(self, tdb, tdb2=0.0):
        values, rates = self._evaluate(float(tdb), float(tdb2), need_rates=True)
        return (
            (float(values[0]), float(values[1]), float(values[2])),
            (float(rates[0]), float(rates[1]), float(rates[2])),
        )


def _small_body_kernel_native_supported(catalog: dict) -> bool:
    if not _HAS_NATIVE_DAF:
        return False
    for item in catalog["summaries"]:
        data_type = int(item["descriptor"][5])
        if data_type == 13:
            if not _HAS_NATIVE_TYPE13:
                return False
        elif data_type in (2, 3):
            if not _HAS_NATIVE_SEGMENTS:
                return False
        else:
            return False
    return True


def _native_segment_for(path: Path, descriptor, source: bytes, little_endian: bool):
    data_type = int(descriptor[5])
    if data_type == 13:
        return _Type13Segment(path, source, descriptor, little_endian)
    if data_type in (2, 3):
        return _NativeChebyshevSegment(path, source, descriptor, little_endian)
    raise RuntimeError(f"unsupported small-body SPK segment type {data_type}")


class SmallBodyKernel:
    """
    RITE: The Small-Body Kernel Wrapper.

    THEOREM: Governs native-owned small-body SPK kernels and exposes the
    body-availability and segment-access surface consumed by higher layers.

    RITE OF PURPOSE:
        SmallBodyKernel is the repository-owned wrapper around a supported
        native small-body SPK kernel. It validates kernel support, builds the
        segment handle set, and records available targets and centers so
        asteroid and comet code can consume the kernel without direct DAF logic.

    LAW OF OPERATION:
        Responsibilities:
            - Validate that the requested kernel exists and is supported.
            - Build and retain the native segment-handle graph.
            - Record available target bodies and centers.
        Non-responsibilities:
            - Does not resolve kernel paths globally.
            - Does not perform catalog parsing outside native helpers.
            - Does not own asteroid/comet domain semantics.
        Dependencies:
            - native DAF catalog support.
            - segment wrappers for supported data types.
        Structural invariants:
            - ``_available`` matches the targets exposed by the loaded segments.
            - ``_center`` stores one center mapping per discovered target.
        Failure behavior:
            - Missing files and unsupported kernels raise explicit exceptions.

    Canon: Native-supported SPK small-body kernel semantics within Moira.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._spk_body_kernel.SmallBodyKernel",
      "risk": "high",
      "api": {
        "frozen": ["has_body"],
        "internal": ["_path", "_catalog", "_kernel", "_available", "_center"]
      },
      "state": {
        "mutable": true,
        "owners": ["SmallBodyKernel"]
      },
      "effects": {
        "signals_emitted": [],
        "io": ["filesystem_read"]
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

    def __init__(
        self,
        path: Path,
        *,
        source_identity: _KernelSourceIdentity | None = None,
    ) -> None:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"SPK kernel not found at {path}")
        if not _HAS_NATIVE_DAF:
            raise ImportError(
                "Moira small-body kernels require the native extension module."
            )

        catalog = _moira_native.read_daf_catalog(str(path))
        if not _small_body_kernel_native_supported(catalog):
            unsupported = sorted(
                {int(item["descriptor"][5]) for item in catalog["summaries"]}
                - {2, 3, 13}
            )
            raise RuntimeError(
                "SmallBodyKernel only supports native SPK segment types 2, 3, and 13; "
                f"found unsupported types {unsupported!r} in {path.name}"
            )

        self._path = path
        if source_identity is None:
            source_hash, source_bytes = _source_sha256(path)
            source_identity = _KernelSourceIdentity(
                label=path.name,
                sha256=source_hash,
                byte_length=source_bytes,
            )
        self._source_identity = source_identity
        integration = source_identity.planetary_ephemeris
        if integration in {"DE440", "DE441"}:
            release_number = integration.removeprefix("DE")
            self._integration_kernel_identity = _EphemerisKernelIdentity(
                summary_label=f"DE-{release_number.zfill(4)}LE-{release_number.zfill(4)}",
                planetary_ephemeris=integration,
                lunar_ephemeris=f"LE{release_number}",
                lunar_tidal_acceleration_arcsec_per_cy2=-25.936,
            )
        else:
            self._integration_kernel_identity = None
        self._catalog = catalog
        self._kernel = _NativeKernelHandle(
            [
                _native_segment_for(path, item["descriptor"], item["name"], catalog["little_endian"])
                for item in catalog["summaries"]
            ]
        )

        self._available: set[int] = set()
        self._center: dict[int, int] = {}
        for seg in self._kernel.segments:
            self._available.add(seg.target)
            self._center.setdefault(seg.target, seg.center)

    def has_body(self, naif_id: int) -> bool:
        return naif_id in self._available

    def segment_center(self, naif_id: int) -> int:
        return self._center.get(naif_id, 0)

    def _segment_for_tdb(self, center: int, target: int, epoch_tdb: float):
        """Select one exact small-body descriptor in its native TDB clock."""

        if not self.has_body(target):
            raise KeyError(
                f"NAIF ID {target} not found in kernel {self._path.name}"
            )
        seg_center = self._center[target]
        if center != seg_center:
            raise ValueError(
                f"SmallBodyKernel serves NAIF {target} from center "
                f"{seg_center}, not center {center}"
            )
        for seg in self._kernel.segments:
            if seg.target == target and seg.start_jd <= epoch_tdb <= seg.end_jd:
                return seg
        raise KeyError(
            f"No segment covers NAIF {target} at JD(TDB) {epoch_tdb:.9f}. "
            "The date may be outside the kernel's coverage."
        )

    def position_tdb(self, center: int, target: int, epoch_tdb: float) -> Vec3:
        """Return an ICRF position at an explicit TDB Julian day."""

        segment = self._segment_for_tdb(center, target, epoch_tdb)
        pos = segment.compute(epoch_tdb)
        return (float(pos[0]), float(pos[1]), float(pos[2]))

    def position(self, center: int, target: int, jd_tt: float) -> Vec3:
        from .julian import tt_to_tdb

        return self.position_tdb(center, target, tt_to_tdb(jd_tt))

    def position_and_velocity(
        self, center: int, target: int, jd_tt: float
    ) -> tuple[Vec3, Vec3]:
        from .julian import tt_to_tdb

        return self.position_and_velocity_tdb(center, target, tt_to_tdb(jd_tt))

    def position_and_velocity_tdb(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
    ) -> tuple[Vec3, Vec3]:
        """Return an ICRF state at an explicit TDB Julian day."""

        segment = self._segment_for_tdb(center, target, epoch_tdb)
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
        """Return a state with its exact descriptor and release receipt."""

        segment = self._segment_for_tdb(center, target, epoch_tdb)
        position, velocity = self.position_and_velocity_tdb(
            center, target, epoch_tdb
        )
        receipt = _SpkSegmentReceipt(
            center=int(segment.center),
            target=int(segment.target),
            data_type=int(segment.data_type),
            coverage_start_tdb=float(segment.start_jd),
            coverage_end_tdb=float(segment.end_jd),
            source=self._source_identity,
            pool_index=int(pool_index),
        )
        return _RoutedState(
            position_km=position,
            velocity_km_per_day=velocity,
            epoch_tdb=float(epoch_tdb),
            legs=(receipt,),
            covered_intervals_tdb=(
                (receipt.coverage_start_tdb, receipt.coverage_end_tdb),
            ),
        )

    def has_segment(self, center: int, target: int) -> bool:
        for seg in self._kernel.segments:
            if seg.target == target and seg.center == center:
                return True
        return False

    def covered_bodies(self) -> frozenset:
        return frozenset(self._available)

    def list_naif_ids(self) -> list[int]:
        return sorted(self._available)

    def has_segment_at(self, center: int, target: int, jd: float) -> bool:
        from .julian import tt_to_tdb

        return self.has_segment_at_tdb(center, target, tt_to_tdb(jd))

    def has_segment_at_tdb(
        self,
        center: int,
        target: int,
        epoch_tdb: float,
    ) -> bool:
        for seg in self._kernel.segments:
            if (
                seg.target == target
                and seg.center == center
                and seg.start_jd <= epoch_tdb <= seg.end_jd
            ):
                return True
        return False

    def coverage_intervals_tdb(
        self,
        center: int,
        target: int,
    ) -> tuple[tuple[float, float], ...]:
        """Return exact disjoint descriptor coverage in TDB."""

        return _merge_closed_intervals(
            [
                (float(seg.start_jd), float(seg.end_jd))
                for seg in self._kernel.segments
                if seg.center == center and seg.target == target
            ]
        )

    def _coverage_pairs_tdb(self) -> tuple[tuple[int, int], ...]:
        """Return deterministic pair keys for private route planning."""

        return tuple(
            sorted(
                {
                    (int(seg.center), int(seg.target))
                    for seg in self._kernel.segments
                }
            )
        )

    def coverage(self) -> dict[tuple[int, int], tuple[float, float]]:
        from .julian import tdb_to_tt

        pairs: set[tuple[int, int]] = set()
        for seg in self._kernel.segments:
            pairs.add((int(seg.center), int(seg.target)))
        result: dict[tuple[int, int], tuple[float, float]] = {}
        for pair in pairs:
            intervals = self.coverage_intervals_tdb(*pair)
            result[pair] = (
                tdb_to_tt(intervals[0][0]),
                tdb_to_tt(intervals[-1][1]),
            )
        return result

    def evaluator_tdb(
        self,
        target: int,
        center: int = 0,
        *,
        epoch_tdb: float,
        epoch_end_tdb: float | None = None,
    ):
        """Return a raw native evaluator selected in TDB."""

        segment = self._segment_for_tdb(center, target, epoch_tdb)
        if epoch_end_tdb is not None and not (
            segment.start_jd <= epoch_end_tdb <= segment.end_jd
        ):
            return None
        return segment._load_native_evaluator()

    def evaluator(
        self,
        target: int,
        center: int = 0,
        jd_tt: float = 2451545.0,
        *,
        jd_end_tt: float | None = None,
    ):
        """Return one TT-facing native evaluator."""

        from . import moira_native
        from .julian import tt_to_tdb

        epoch_tdb = tt_to_tdb(jd_tt)
        epoch_end_tdb = None if jd_end_tt is None else tt_to_tdb(jd_end_tt)
        raw = self.evaluator_tdb(
            target,
            center,
            epoch_tdb=epoch_tdb,
            epoch_end_tdb=epoch_end_tdb,
        )
        return None if raw is None else moira_native.TtToTdbEvaluator(raw)

    def close(self) -> None:
        try:
            self._kernel.close()
        except Exception:
            pass


def _resolve_manifest_shard_path(manifest_path: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate

    manifest_relative = (manifest_path.parent / candidate).resolve()
    if manifest_relative.exists():
        return manifest_relative

    root_relative = (ROOT / candidate).resolve()
    if root_relative.exists():
        return root_relative

    return manifest_relative


def small_body_readers_from_manifest(manifest_path: str | Path) -> list[SmallBodyKernel]:
    """
    Build ordered ``SmallBodyKernel`` readers from a sovereign shard manifest.

    A release-finalized manifest is verified against its complete SHA-256
    receipt before any kernel is opened. Build-time and legacy manifests do not
    carry a ``release`` identity and retain their existing loading behavior.
    """
    manifest = Path(manifest_path)
    manifest_bytes = manifest.read_bytes()
    payload = json.loads(manifest_bytes.decode("utf-8"))
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if "release" in payload:
        from .small_body_catalog_release import verify_release

        verify_release(manifest.parent)
    readers: list[SmallBodyKernel] = []
    seen: set[Path] = set()
    for shard in payload.get("shards", []):
        shard_path = _resolve_manifest_shard_path(manifest, str(shard["path"]))
        if not shard_path.exists():
            raise FileNotFoundError(
                f"Sovereign shard listed in {manifest} was not found: {shard_path}"
            )
        resolved = shard_path.resolve()
        if resolved in seen:
            continue
        shard_hash = str(shard.get("sha256") or "")
        shard_bytes = int(shard.get("bytes") or resolved.stat().st_size)
        if not shard_hash:
            shard_hash, shard_bytes = _source_sha256(resolved)
        release = payload.get("release") or {}
        provenance = payload.get("provenance") or {}
        planetary_ephemeris = (
            provenance.get("planetary_ephemeris")
            or payload.get("planetary_ephemeris")
        )
        coverage_note = str((payload.get("coverage") or {}).get("note") or "")
        source_identity = _KernelSourceIdentity(
            label=(
                f"{payload.get('catalog_id', 'small-body-catalog')}:"
                f"{shard.get('index', 0)}"
            ),
            sha256=shard_hash,
            byte_length=shard_bytes,
            catalog_id=payload.get("catalog_id"),
            catalog_version=payload.get("catalog_version"),
            manifest_sha256=manifest_sha256,
            released_utc=release.get("released_utc"),
            planetary_ephemeris=planetary_ephemeris,
            coverage_restricted_to_observed_arc=(
                "clamp" in coverage_note.casefold()
                or "observed arc" in coverage_note.casefold()
            ),
        )
        readers.append(
            SmallBodyKernel(resolved, source_identity=source_identity)
        )
        seen.add(resolved)
    return readers

"""
Moira — spk_reader.py
Governs all binary SPK file access for the Moira ephemeris engine.

Boundary: owns the sole point of contact between Moira and the jplephem
library. All kernel I/O is funnelled through this module. No other module
may hold a reference to the jplephem SPK object or open the kernel file
directly.

Public surface:
    KernelReader (Protocol), SpkReader, KernelPool,
    use_reader_override, get_active_reader, set_kernel_path,
    add_to_global_pool, swap_reader, reset_singleton, MissingKernelError

Import-time side effects: None (kernel is opened lazily on first
    SpkReader instantiation, not at import time).

External dependency assumptions:
    - jplephem must be importable (pip install jplephem).
    - A compatible JPL SPK planetary kernel must be provided to the 
      SpkReader at construction. No default kernel is assumed.
"""

import threading
from contextlib import contextmanager
from contextvars import ContextVar
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

from ._kernel_paths import find_kernel, find_planetary_kernel

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
    """Evaluate one Chebyshev coefficient record with scalar recurrence."""
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

        t_k_minus_2 = 1.0
        t_k_minus_1 = s
        total = float(coeffs[0]) + float(coeffs[1]) * s
        for k in range(2, coefficient_count):
            t_k = 2.0 * s * t_k_minus_1 - t_k_minus_2
            total += float(coeffs[k]) * t_k
            t_k_minus_2 = t_k_minus_1
            t_k_minus_1 = t_k
        values.append(total)

    return tuple(values)


def _eval_chebyshev_record_with_derivative_scalar(
    coeff_record,
    s: float,
    derivative_scale: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Evaluate one record and its derivative with scalar Chebyshev recurrences."""
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

        t_k_minus_2 = 1.0
        t_k_minus_1 = s
        u_k_minus_2 = 1.0
        u_k_minus_1 = 2.0 * s
        value = float(coeffs[0]) + float(coeffs[1]) * s
        derivative = float(coeffs[1])

        for k in range(2, coefficient_count):
            t_k = 2.0 * s * t_k_minus_1 - t_k_minus_2
            u_k_minus_1_current = u_k_minus_1 if k > 1 else 1.0
            value += float(coeffs[k]) * t_k
            derivative += float(k) * float(coeffs[k]) * u_k_minus_1_current
            u_k = 2.0 * s * u_k_minus_1 - u_k_minus_2
            t_k_minus_2 = t_k_minus_1
            t_k_minus_1 = t_k
            u_k_minus_2 = u_k_minus_1
            u_k_minus_1 = u_k

        values.append(value)
        rates.append(derivative * derivative_scale)

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
    """Thin kernel holder built from Moira-native DAF summary scanning."""

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
        if _native_catalog_is_fully_supported(catalog):
            return _NativeSpkKernel(path, catalog, handle=handle)
        try:
            handle.close()
        except Exception:
            pass
    elif _moira_native is not None and hasattr(_moira_native, "read_daf_catalog"):
        catalog = _moira_native.read_daf_catalog(str(path))
        if _native_catalog_is_fully_supported(catalog):
            return _NativeSpkKernel(path, catalog)
    if not _HAS_JPLEPHEM:
        raise RuntimeError(
            "This kernel path still requires jplephem because it contains unsupported "
            "segment types for the current native reader."
        )
    return _SPK.open(str(path))


class _NativeChebyshevSegment:
    """Moira-native type-2/type-3 SPK segment with jplephem-compatible surface."""

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
        if self._handle is not None and tdb2 == 0.0:
            if need_rates and hasattr(self._handle, "segment_position_and_velocity"):
                return self._handle.segment_position_and_velocity(
                    int(self.start_i),
                    int(self.end_i),
                    int(self.data_type),
                    tdb,
                )
            if not need_rates and hasattr(self._handle, "segment_position"):
                return self._handle.segment_position(
                    int(self.start_i),
                    int(self.end_i),
                    int(self.data_type),
                    tdb,
                ), None

        self._load_native_evaluator()
        if self._native_evaluator is not None and tdb2 == 0.0:
            if need_rates:
                return self._native_evaluator.position_and_velocity(tdb)
            return self._native_evaluator.position(tdb), None

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


def _native_catalog_is_fully_supported(catalog: dict) -> bool:
    if not (_HAS_NATIVE_DAF and _HAS_NATIVE_SEGMENTS):
        return False
    return all(item["descriptor"][5] in (2, 3) for item in catalog["summaries"])


class MissingKernelError(RuntimeError):
    """Raised when get_reader() is called with no planetary kernel configured."""


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

    THEOREM: SpkReader governs exclusive read access to a JPL binary SPK
        kernel file, serving raw barycentric state vectors to all computation
        pillars.

    RITE OF PURPOSE:
        SpkReader is the single authorised gateway between Moira's pure-Python
        astronomy layer and a binary JPL SPK ephemeris file. Without it, no
        planetary position can be computed. It exists to enforce the invariant
        that exactly one file handle to the kernel is open at any time, and
        that all segment-selection logic (including split multi-epoch layouts)
        is encapsulated in one place rather than scattered across callers.

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
            - Does not cache computed positions. Callers own their own caches.
            - Does not validate that NAIF body IDs are astronomically
              meaningful.
        Dependencies:
            - jplephem must be importable at module load time.
            - The kernel file at the given path must exist before __init__
              is called.
        Structural invariants:
            - self._kernel is always a valid open jplephem SPK object while
              the instance is alive and close() has not been called.
            - self._path always reflects the path from which the kernel was
              opened.
        Behavioral invariants:
            - position() and position_and_velocity() are pure reads; they
              never modify kernel state.
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
        State ownership: Owns the open SPK kernel file handle and the jplephem
            SPK object. No other module may hold a reference to the kernel object.
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
        self._kernel = _open_kernel(path)
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
        for seg in self._segments_for_pair(center, target):
            if seg.start_jd <= jd <= seg.end_jd:
                return seg
        raise ValueError(
            f"Segments exist for center={center}, target={target} but none "
            f"covers JD {jd:.2f}.  Kernel coverage may not extend to this epoch."
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
        self._ensure_open()
        segment = self._segment_for(center, target, jd)
        native = None if hasattr(segment, "_load_native_evaluator") else _native_position(segment, jd)
        if native is not None:
            return native
        pos = segment.compute(jd)
        return (float(pos[0]), float(pos[1]), float(pos[2]))

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
        self._ensure_open()
        segment = self._segment_for(center, target, jd)
        native = (
            None
            if hasattr(segment, "_load_native_evaluator")
            else _native_position_and_velocity(segment, jd)
        )
        if native is not None:
            return native
        pos, vel = segment.compute_and_differentiate(jd)
        return (
            (float(pos[0]), float(pos[1]), float(pos[2])),
            (float(vel[0]), float(vel[1]), float(vel[2])),
        )

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
        try:
            for segment in self._segments_for_pair(center, target):
                if segment.start_jd <= jd <= segment.end_jd:
                    return True
        except KeyError:
            return False
        return False

    def coverage(self) -> dict[tuple[int, int], tuple[float, float]]:
        """
        Return the epoch range covered by each (center, target) pair.

        Returns
        -------
        dict mapping (center_naif_id, target_naif_id) to (start_jd, end_jd).
        For pairs whose data is split across multiple segments, start_jd is
        the earliest segment start and end_jd is the latest segment end.
        """
        self._ensure_open()
        return {
            pair: (
                min(s.start_jd for s in segs),
                max(s.end_jd   for s in segs),
            )
            for pair, segs in self._segments_by_pair.items()
        }

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
        return (min(s.start_jd for s in segs), max(s.end_jd for s in segs))

    @property
    def path(self) -> Path:
        """Path to the open SPK kernel file."""
        return self._path

    def __repr__(self) -> str:
        """Return a concise string representation showing the kernel filename."""
        return f"SpkReader('{self._path.name}')"


# Capture original class for type-safe checks in shims (prevents 
# auto-discovery regressions in unit tests that monkeypatch SpkReader).
_OriginalSpkReader = SpkReader


# ---------------------------------------------------------------------------
# KernelPool — ordered multi-kernel reader with fallback
# ---------------------------------------------------------------------------

class KernelPool:
    """
    RITE: The Unified Ephemeris Reservoir

    THEOREM: KernelPool governs afallback-ordered chain of ephemeris 
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
            - Ensure atomic resource cleanup for the entire pool.
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
        from ._spk_body_kernel import SmallBodyKernel as _SmallBodyKernel
        self._SmallBodyKernel = _SmallBodyKernel
        self._readers: list = list(readers)

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------

    def add(self, reader) -> None:
        """Append *reader* to the fallback chain (lowest priority)."""
        self._readers.append(reader)

    # ------------------------------------------------------------------
    # Core read interface (mirrors SpkReader)
    # ------------------------------------------------------------------

    def position(self, center: int, target: int, jd: float) -> Vec3:
        """
        Return position of *target* relative to *center* at *jd* (TT).

        Tries each registered reader in order and returns the result from
        the first one that covers the (center, target, jd) triple.

        Raises
        ------
        KeyError
            If no reader in the pool covers the requested triple.
        """
        for reader in self._readers:
            if isinstance(reader, self._SmallBodyKernel):
                if reader.has_segment_at(center, target, jd):
                    return reader.position(target, jd)
            elif reader.has_segment_at(center, target, jd):
                return reader.position(center, target, jd)
        raise KeyError(
            f"No kernel in pool covers center={center}, target={target} "
            f"at JD {jd:.2f}"
        )

    def position_and_velocity(
        self, center: int, target: int, jd: float
    ) -> tuple[Vec3, Vec3]:
        """
        Return position and velocity of *target* relative to *center* at *jd*.

        Only dispatches to SpkReader instances; SmallBodyKernel readers are
        skipped for this method.

        Raises
        ------
        KeyError
            If no SpkReader in the pool covers the requested triple.
        NotImplementedError
            If the only covering reader is a SmallBodyKernel.
        """
        small_body_covered = False
        for reader in self._readers:
            if isinstance(reader, self._SmallBodyKernel):
                if reader.has_segment_at(center, target, jd):
                    small_body_covered = True
            elif reader.has_segment_at(center, target, jd):
                return reader.position_and_velocity(center, target, jd)
        if small_body_covered:
            raise NotImplementedError(
                f"SmallBodyKernel does not support position_and_velocity "
                f"(center={center}, target={target})"
            )
        raise KeyError(
            f"No kernel in pool covers center={center}, target={target} "
            f"at JD {jd:.2f}"
        )

    # ------------------------------------------------------------------
    # Segment presence checks
    # ------------------------------------------------------------------

    def has_segment(self, center: int, target: int) -> bool:
        """Return True if any reader in the pool covers (center, target)."""
        for reader in self._readers:
            if isinstance(reader, self._SmallBodyKernel):
                if reader.has_body(target) and reader.segment_center(target) == center:
                    return True
            elif reader.has_segment(center, target):
                return True
        return False

    def has_segment_at(self, center: int, target: int, jd: float) -> bool:
        """Return True if any reader covers (center, target) at *jd*."""
        for reader in self._readers:
            if reader.has_segment_at(center, target, jd):
                return True
        return False

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
        for reader in self._readers:
            for pair, (start, end) in reader.coverage().items():
                if pair in merged:
                    prev = merged[pair]
                    merged[pair] = (min(prev[0], start), max(prev[1], end))
                else:
                    merged[pair] = (start, end)
        return merged

    def covered_bodies(self) -> frozenset[int]:
        """Return the union of target NAIF IDs across all readers."""
        bodies: set[int] = set()
        for reader in self._readers:
            if isinstance(reader, self._SmallBodyKernel):
                bodies.update(reader.list_naif_ids())
            else:
                bodies.update(reader.covered_bodies())
        return frozenset(bodies)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close all managed readers."""
        for reader in self._readers:
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
                from ._kernel_paths import find_kernel
                from ._spk_body_kernel import SmallBodyKernel
                
                supplemental = [
                    "sb441-n373s.bsp",   # Preferred secondary asteroid kernel
                    "asteroids.bsp",     # Primary asteroid kernel
                    "centaurs.bsp",      # Horizons centaurs
                    "minor_bodies.bsp",  # Horizons minor bodies
                    "comets.bsp",        # Comets
                ]
                for s_name in supplemental:
                    s_path = find_kernel(s_name)
                    if s_path.exists():
                        found_supplemental.append(SmallBodyKernel(s_path))
            except (ImportError, AttributeError):
                # Handle cases where paths or small body logic aren't yet available
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
    """Temporarily route computational pillars to a caller-owned reader."""
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

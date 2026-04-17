"""
Moira — spk_reader.py
Governs all binary SPK file access for the Moira ephemeris engine.

Boundary: owns the sole point of contact between Moira and the jplephem
library. All kernel I/O is funnelled through this module. No other module
may hold a reference to the jplephem SPK object or open the kernel file
directly.

Public surface:
    KernelReader (Protocol), SpkReader, KernelPool,
    get_reader(), set_kernel_path(), swap_reader(), reset_singleton(),
    use_reader_override(), MissingKernelError

Import-time side effects: None (kernel is opened lazily on first
    SpkReader instantiation, not at import time).

External dependency assumptions:
    - jplephem must be importable (pip install jplephem).
    - A compatible JPL SPK planetary kernel must be configured via
      set_kernel_path() or Moira(kernel_path=...) before SpkReader is
      instantiated. No default kernel is assumed.
"""

import threading
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Protocol, runtime_checkable

# jplephem is used solely as a binary SPK file reader
try:
    from jplephem.spk import SPK as _SPK
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Moira requires jplephem to read SPK kernel files. "
        "Install it with: pip install jplephem"
    ) from exc

from ._kernel_paths import find_kernel, find_planetary_kernel

Vec3 = tuple[float, float, float]


class MissingKernelError(RuntimeError):
    """Raised when get_reader() is called with no planetary kernel configured."""


@runtime_checkable
class KernelReader(Protocol):
    """
    Structural protocol for SPK kernel readers.

    Both ``SpkReader`` and ``KernelPool`` satisfy this protocol.  Use this
    type in function signatures wherever a caller should be able to supply
    either a single-kernel reader or a multi-kernel pool.

    Methods
    -------
    position(center, target, jd)
        Barycentric position of *target* relative to *center* at *jd* (TT),
        returned as (x, y, z) in km (ICRF).
    position_and_velocity(center, target, jd)
        Position and velocity as ((x,y,z), (vx,vy,vz)), km and km/day.
    has_segment(center, target)
        True if any data exists for this body pair (epoch-agnostic).
    has_segment_at(center, target, jd)
        True if data for this body pair covers *jd*.
    coverage()
        Dict mapping (center, target) pairs to (start_jd, end_jd) ranges.
    covered_bodies()
        Frozenset of all target NAIF IDs present in this reader.
    close()
        Release all held file handles.
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
          "get_reader() and set_kernel_path() are serialized by a module-level RLock",
          "concurrent reads through an open SpkReader are safe",
          "kernel-path reconfiguration is forbidden after singleton acquisition"
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
        self._kernel = _SPK.open(str(path))
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


# ---------------------------------------------------------------------------
# KernelPool — ordered multi-kernel reader with fallback
# ---------------------------------------------------------------------------

class KernelPool:
    """
    Ordered multi-kernel reader with transparent fallback.

    Dispatches position queries to the first registered reader whose coverage
    includes the requested (center, target, jd) triple.  Accepts any mix of
    SpkReader and SmallBodyKernel instances, in caller-defined priority order.

    Typical use cases
    -----------------
    - Planetary kernel + asteroid extension kernel, unified behind one interface.
    - Primary DE series + auxiliary body kernel for trans-Neptunian objects.
    - Per-request reader pools in multi-tenant servers via use_reader_override().

    Example
    -------
    >>> pool = KernelPool([planetary_reader, asteroid_kernel])
    >>> pos = pool.position(0, 2000433, jd)   # 0=SSB center, 2000433=Eros

    Notes
    -----
    - Readers are tried in insertion order; the first covering match wins.
    - close() closes all managed readers; after close() the pool must not be used.
    - position_and_velocity() is only dispatched to SpkReader instances; calling
      it when only a SmallBodyKernel covers the pair raises NotImplementedError.
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
# Module-level singleton (lazy-initialised)
# ---------------------------------------------------------------------------

_reader: SpkReader | None = None
_reader_path: Path | None = None
_reader_lock = threading.RLock()
_reader_override: ContextVar[SpkReader | None] = ContextVar("moira_reader_override", default=None)


@contextmanager
def use_reader_override(reader: SpkReader | None):
    """Temporarily route ``get_reader()`` to a caller-owned reader."""
    token = _reader_override.set(reader)
    try:
        yield
    finally:
        _reader_override.reset(token)


def get_reader(kernel_path: str | Path | None = None) -> SpkReader:
    """
    Return the module-level SpkReader singleton, initialising it on first call.

    Subsequent calls return the cached instance. Requesting a different kernel
    path while a live singleton exists is forbidden, because closing and
    replacing the active reader would invalidate any handles already shared
    across callers or threads.

    Args:
        kernel_path: Explicit path to a compatible JPL SPK kernel file. If
            omitted, the module checks for any pre-configured path (set via
            set_kernel_path()) and then auto-discovers the first installed
            planetary kernel via find_planetary_kernel(). No specific DE series
            is assumed.

    Returns:
        The active SpkReader singleton.

    Raises:
        MissingKernelError: If no kernel path has been configured and none is
            provided.
        FileNotFoundError: If the kernel file does not exist at the given path.

    Side effects:
        - May open a new file handle to the kernel file on first call.
    """
    override = _reader_override.get()
    if override is not None:
        if kernel_path is not None and override.path != Path(kernel_path):
            raise RuntimeError(
                "Active reader override is bound to a different kernel path."
            )
        return override

    global _reader, _reader_path
    with _reader_lock:
        if _reader is not None:
            if kernel_path is not None and _reader_path != Path(kernel_path):
                raise RuntimeError(
                    "Cannot replace the active SpkReader singleton with a different "
                    "kernel path. Call set_kernel_path() before first access."
                )
            return _reader
        if kernel_path is not None:
            path = Path(kernel_path)
        elif _reader_path is not None:
            path = _reader_path
        else:
            discovered = find_planetary_kernel()
            if discovered is None:
                raise MissingKernelError(
                    "No planetary kernel is configured and none was found on disk. "
                    "Call set_kernel_path() before first use, "
                    "or pass kernel_path= to Moira()."
                )
            path = discovered
        if _reader_path is not None and _reader_path != path:
            raise RuntimeError(
                "Kernel path has already been configured for the next reader. "
                "Use the configured path or restart configuration before first access."
            )
        _reader = SpkReader(path)
        _reader_path = path
        return _reader


def set_kernel_path(path: str | Path) -> None:
    """
    Point Moira at a different SPK kernel file.

    This must be called before the singleton reader is first acquired. Changing
    the path after a live reader exists would invalidate outstanding handles
    and is therefore rejected.  Use :func:`swap_reader` for intentional
    runtime reconfiguration.

    Args:
        path: Filesystem path to the replacement SPK kernel file.

    Side effects:
        - Updates the configured path used by the next singleton creation.
    """
    global _reader, _reader_path
    with _reader_lock:
        if _reader is not None:
            raise RuntimeError(
                "Cannot change kernel path after the singleton reader has been opened. "
                "Use swap_reader() for intentional runtime reconfiguration."
            )
        _reader_path = Path(path)


def swap_reader(reader_or_path: "SpkReader | KernelPool | str | Path") -> "SpkReader | KernelPool":
    """
    Replace the module-level singleton with a new reader, closing the old one.

    Unlike :func:`set_kernel_path`, this may be called at any time — even after
    the singleton has already been acquired.  The existing reader is closed
    under the module lock before the new one is installed, so outstanding
    references held by other threads become stale after this call returns.

    Intended for intentional runtime reconfiguration (kernel upgrade, kernel
    swap between test cases, graceful hot-reload).  For per-request isolation
    without touching the singleton, use :func:`use_reader_override` instead.

    Args:
        reader_or_path: Either a pre-opened ``SpkReader`` or ``KernelPool``
            instance, or a filesystem path string / ``Path`` to a ``.bsp``
            kernel file (in which case a new ``SpkReader`` is opened).

    Returns:
        The newly installed singleton (the same object passed in, or the
        freshly-opened ``SpkReader`` when a path was supplied).

    Raises:
        FileNotFoundError: If a path was supplied and the file does not exist.

    Side effects:
        - Closes the existing singleton reader (if any).
        - Opens a new file handle if a path was supplied.
        - Updates both the module-level ``_reader`` and ``_reader_path``.
    """
    global _reader, _reader_path
    with _reader_lock:
        old = _reader
        if isinstance(reader_or_path, (str, Path)):
            new_reader: SpkReader | KernelPool = SpkReader(Path(reader_or_path))
            new_path = Path(reader_or_path)
        else:
            new_reader = reader_or_path
            new_path = getattr(reader_or_path, "path", _reader_path)
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        _reader = new_reader
        _reader_path = new_path
        return new_reader


def reset_singleton() -> None:
    """
    Close and clear the module-level singleton reader.

    After this call :func:`get_reader` will re-initialise the singleton on its
    next invocation, exactly as it would on a fresh import.  ``_reader_path``
    is also cleared so a different kernel can be configured via
    :func:`set_kernel_path` before the next acquisition.

    Intended for:
    - Test teardown (isolate kernel state between test cases).
    - Graceful shutdown hooks (ensure file handles are released).
    - Re-initialisation after a failed startup attempt.

    Thread safety: serialised by the module-level RLock.

    Side effects:
        - Closes the existing reader (if any); exceptions are suppressed.
        - Clears ``_reader`` and ``_reader_path``.
    """
    global _reader, _reader_path
    with _reader_lock:
        if _reader is not None:
            try:
                _reader.close()
            except Exception:
                pass
            _reader = None
        _reader_path = None

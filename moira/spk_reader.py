"""
Moira — spk_reader.py
Governs all binary SPK file access for the Moira ephemeris engine.

Boundary: owns the sole point of contact between Moira and the jplephem
library. All kernel I/O is funnelled through this module. No other module
may hold a reference to the jplephem SPK object or open the kernel file
directly.

Public surface:
    SpkReader, get_reader(), set_kernel_path(), MissingKernelError

Import-time side effects: None (kernel is opened lazily on first
    SpkReader instantiation, not at import time).

External dependency assumptions:
    - jplephem must be importable (pip install jplephem).
    - A compatible JPL SPK planetary kernel must be configured via
      set_kernel_path() or Moira(kernel_path=...) before SpkReader is
      instantiated. No default kernel is assumed.
"""

import threading
from pathlib import Path

# jplephem is used solely as a binary SPK file reader
try:
    from jplephem.spk import SPK as _SPK
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Moira requires jplephem to read SPK kernel files. "
        "Install it with: pip install jplephem"
    ) from exc

from ._kernel_paths import find_kernel

Vec3 = tuple[float, float, float]


class MissingKernelError(RuntimeError):
    """Raised when get_reader() is called with no planetary kernel configured."""


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
            KeyError: If no segment exists for the (center, target) pair, or if
                no segment for that pair covers ``jd``.

        Side effects:
            None.
        """
        for seg in self._segments_for_pair(center, target):
            if seg.start_jd <= jd <= seg.end_jd:
                return seg
        raise KeyError(
            f"No segment covers center={center}, target={target} at JD {jd}"
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

    @property
    def path(self) -> Path:
        """Path to the open SPK kernel file."""
        return self._path

    def __repr__(self) -> str:
        """Return a concise string representation showing the kernel filename."""
        return f"SpkReader('{self._path.name}')"


# ---------------------------------------------------------------------------
# Module-level singleton (lazy-initialised)
# ---------------------------------------------------------------------------

_reader: SpkReader | None = None
_reader_path: Path | None = None
_reader_lock = threading.RLock()


def get_reader(kernel_path: str | Path | None = None) -> SpkReader:
    """
    Return the module-level SpkReader singleton, initialising it on first call.

    Subsequent calls return the cached instance. Requesting a different kernel
    path while a live singleton exists is forbidden, because closing and
    replacing the active reader would invalidate any handles already shared
    across callers or threads.

    Args:
        kernel_path: Path to a compatible JPL SPK kernel file. Must be provided
            explicitly or pre-configured via set_kernel_path(). No default kernel
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
            raise MissingKernelError(
                "No planetary kernel is configured. "
                "Call set_kernel_path() before first use, "
                "or pass kernel_path= to Moira()."
            )
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
    and is therefore rejected.

    Args:
        path: Filesystem path to the replacement SPK kernel file.

    Side effects:
        - Updates the configured path used by the next singleton creation.
    """
    global _reader, _reader_path
    with _reader_lock:
        if _reader is not None:
            raise RuntimeError(
                "Cannot change kernel path after the singleton reader has been opened."
            )
        _reader_path = Path(path)

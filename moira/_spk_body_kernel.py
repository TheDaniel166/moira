"""
moira/_spk_body_kernel.py — Shared SPK Small-Body Reader

Archetype: Internal shared infrastructure

Purpose
-------
Provides the SPK type 13 segment reader and the ``SmallBodyKernel`` wrapper
used by both ``moira.asteroids`` and ``moira.comets`` (and any future small-body
module).  Factored out to eliminate duplication between those modules.

Boundary declaration
--------------------
Owns:
    - _hermite_eval_3d          — Hermite divided-difference interpolation in R³
    - _Type13Segment            — jplephem BaseSegment extension for SPK type 13
    - SmallBodyKernel           — thin wrapper around a jplephem SPK file
    - SPK type 13 registration  — _segment_classes[13] = _Type13Segment

Delegates: nothing — all logic is self-contained or delegates to jplephem.

Import-time side effects:
    Registers _Type13Segment in jplephem's _segment_classes dict at import
    time (_segment_classes[13] = _Type13Segment).  This is a one-time, idempotent
    mutation of a jplephem global; re-importing is safe.

External dependency assumptions:
    jplephem must be installed.

Public surface
--------------
    SmallBodyKernel    — open an SPK file and query body positions
    _Type13Segment     — re-exported for callers that need the class directly
                         (e.g. test_daf_writer round-trip tests)
"""

from __future__ import annotations

from bisect import bisect_left
from pathlib import Path

from .coordinates import Vec3

try:
    from jplephem.spk import (
        SPK as _SPK,
        BaseSegment,
        _segment_classes,
        S_PER_DAY,
        T0,
        reify,
    )
except ImportError as exc:
    raise ImportError(
        "Moira requires jplephem.  Install: pip install jplephem"
    ) from exc


# ---------------------------------------------------------------------------
# SPK Type 13: Hermite Interpolation — Unequal Time Steps
# ---------------------------------------------------------------------------

def _hermite_eval_3d(
    t: float,
    ti: list[float],
    pos: list[list[float]],
    vel: list[list[float]],
) -> tuple[float, float, float]:
    """
    Hermite divided-difference interpolation in R³.

    Parameters
    ----------
    t   : scalar query time (seconds from J2000)
    ti  : (n,) node times (seconds from J2000)
    pos : (3, n) positions in km
    vel : (3, n) velocities in km/s  [d(km)/d(second)]

    Returns
    -------
    (3,) interpolated position in km
    """
    n = len(pos[0])
    m = 2 * n

    # Extended nodes: [t0,t0, t1,t1, ..., t_{n-1},t_{n-1}]
    z = [0.0] * m
    for i, value in enumerate(ti):
        z[2 * i]     = value
        z[2 * i + 1] = value

    # Divided-differences table, working column-by-column.
    prev = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        for i in range(n):
            prev[axis][2 * i]     = pos[axis][i]
            prev[axis][2 * i + 1] = pos[axis][i]

    coeffs = [[0.0] * m for _ in range(3)]
    for axis in range(3):
        coeffs[axis][0] = prev[axis][0]

    # j = 1: equal adjacent nodes → use known derivative
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

    # j ≥ 2: standard divided differences
    for j in range(2, m):
        curr = [[0.0] * (m - j) for _ in range(3)]
        for i in range(m - j):
            denom = z[i + j] - z[i]
            for axis in range(3):
                curr[axis][i] = (prev[axis][i + 1] - prev[axis][i]) / denom
        for axis in range(3):
            coeffs[axis][j] = curr[axis][0]
        prev = curr

    # Evaluate Newton form via Horner's method
    result = [coeffs[axis][m - 1] for axis in range(3)]
    for j in range(m - 2, -1, -1):
        delta = t - z[j]
        for axis in range(3):
            result[axis] = coeffs[axis][j] + delta * result[axis]

    return (result[0], result[1], result[2])


class _Type13Segment(BaseSegment):
    """RITE: The Hermite Reader — the low-level segment handler that decodes
    unequal-step Hermite-interpolated SPK type 13 state data directly
    from a jplephem DAF into cartesian position vectors.

THEOREM: jplephem BaseSegment extension for SPK type 13 (Hermite
         interpolation, unequal time steps), registered in the jplephem
         segment class registry at import time.

RITE OF PURPOSE:
    _Type13Segment allows jplephem to transparently open and query SPK
    files whose segments use type 13 encoding (the format used by NAIF
    for most small-body kernels).  Without this class, jplephem's
    ``SPK.open()`` cannot read type 13 data and raises on import.

LAW OF OPERATION:
    Responsibilities:
        - Decode the type 13 DAF segment layout (state vectors, epoch
          array, epoch directory, window parameters).
        - Delegate Hermite interpolation to ``_hermite_eval_3d``.
        - Provide ``compute()`` and ``compute_and_differentiate()``.
    Non-responsibilities:
        - Does not own kernel file I/O; that is jplephem SPK.
        - Does not validate NAIF body ID or epoch coverage; the caller
          (``SmallBodyKernel.position``) does that.
    Dependencies:
        - jplephem.spk.BaseSegment, reify, S_PER_DAY, T0.
        - moira._spk_body_kernel._hermite_eval_3d.
    Structural invariants:
        - Registered as _segment_classes[13] at module import time.

Canon: NAIF SPK Required Reading §2.3.13

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._spk_body_kernel._Type13Segment",
    "risk": "high",
    "api": {"frozen": ["compute", "compute_and_differentiate"], "internal": ["_data"]},
    "state": {"mutable": false, "owners": ["_data"]},
    "effects": {"signals_emitted": [], "io": ["kernel_mmap_read"], "mutation": "cached_property"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "terminal", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change", "kernel_policy"]}
}
[/MACHINE_CONTRACT]
    """

    @reify
    def _data(self):
        ws_f, n_f = self.daf.read_array(self.end_i - 1, self.end_i)
        n  = int(n_f)
        ws = int(ws_f)

        i = self.start_i
        raw_states = self.daf.map_array(i, i + 6 * n - 1)
        states = [[0.0] * n for _ in range(6)]
        for row in range(n):
            base = row * 6
            for axis in range(6):
                states[axis][row] = float(raw_states[base + axis])

        raw_epochs = self.daf.map_array(i + 6 * n, i + 7 * n - 1)
        epochs_jd = [float(v) / S_PER_DAY + T0 for v in raw_epochs]

        return states, epochs_jd, ws

    def compute(self, tdb, tdb2=0.0):
        """Return (x, y, z) in km at time *tdb* (JD TDB)."""
        states, epochs_jd, ws = self._data
        t = float(tdb) + float(tdb2)

        idx   = bisect_left(epochs_jd, t)
        half  = ws // 2
        start = max(0, min(idx - half, len(epochs_jd) - ws))

        win_jd = epochs_jd[start:start + ws]
        win_t  = [(jd - T0) * S_PER_DAY for jd in win_jd]
        t_sec  = (t - T0) * S_PER_DAY

        pos = [axis[start:start + ws] for axis in states[:3]]
        vel = [axis[start:start + ws] for axis in states[3:]]

        return _hermite_eval_3d(t_sec, win_t, pos, vel)

    def compute_and_differentiate(self, tdb, tdb2=0.0):
        """Return ((x,y,z), (vx,vy,vz)) — velocity via finite difference (km, km/day)."""
        dt  = 1.0
        p0  = self.compute(tdb - dt * 0.5, tdb2)
        p1  = self.compute(tdb + dt * 0.5, tdb2)
        pos = self.compute(tdb, tdb2)
        vel = tuple((b - a) / dt for a, b in zip(p0, p1))
        return pos, vel


# Register with jplephem so SPK.open() picks up type 13 segments automatically.
_segment_classes[13] = _Type13Segment


# ---------------------------------------------------------------------------
# SmallBodyKernel — thin SPK file wrapper
# ---------------------------------------------------------------------------

class SmallBodyKernel:
    """RITE: The Small-Body Gate — the thin wrapper that opens one JPL SPK
    kernel file and answers body-position queries without duplicating
    the open/index/query logic across the asteroid and comet modules.

THEOREM: Thin wrapper around a jplephem SPK file that indexes available
         NAIF body IDs, reference centers, and epoch coverage, and
         returns ICRF position vectors for a body at a given JD.

RITE OF PURPOSE:
    SmallBodyKernel factors out the SPK open-and-query pattern shared
    by ``moira.asteroids`` and ``moira.comets``.  Without it, both
    modules would duplicate the segment iteration, coverage mapping,
    and FileNotFoundError guard.

LAW OF OPERATION:
    Responsibilities:
        - Open and hold a jplephem SPK kernel file.
        - Index available NAIF IDs and their reference centers.
        - Answer ``position()``, ``has_body()``, and ``coverage()``
          queries.
    Non-responsibilities:
        - Does not own epoch-validity checking beyond segment bounds.
        - Does not convert from ICRF to ecliptic; callers do that.
    Dependencies:
        - jplephem.spk.SPK.
        - moira._spk_body_kernel._Type13Segment (registered at import).
    Structural invariants:
        - ``_path`` is an existing file at construction time.
        - ``_available`` and ``_center`` are consistent with the kernel.

Canon: NAIF SPK Required Reading; moira.asteroids and moira.comets
       small-body kernel policy.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._spk_body_kernel.SmallBodyKernel",
    "risk": "high",
    "api": {"frozen": ["has_body", "segment_center", "position", "list_naif_ids", "has_segment_at", "coverage"], "internal": ["_path", "_kernel", "_available", "_center"]},
    "state": {"mutable": false, "owners": ["_kernel"]},
    "effects": {"signals_emitted": [], "io": ["kernel_file_open"], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "raise"},
    "succession": {"stance": "terminal", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change", "kernel_policy"]}
}
[/MACHINE_CONTRACT]
    """

    def __init__(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"SPK kernel not found at {path}")
        self._path   = path
        self._kernel = _SPK.open(str(path))

        self._available: set[int]       = set()
        self._center:    dict[int, int] = {}
        for seg in self._kernel.segments:
            self._available.add(seg.target)
            if seg.target not in self._center:
                self._center[seg.target] = seg.center

    def has_body(self, naif_id: int) -> bool:
        return naif_id in self._available

    def segment_center(self, naif_id: int) -> int:
        """Return the reference center NAIF ID for this body (10 = Sun for heliocentric kernels)."""
        return self._center.get(naif_id, 0)

    def position(self, naif_id: int, jd_tt: float) -> Vec3:
        """
        Return position of *naif_id* relative to its segment center (km, ICRF).
        """
        for seg in self._kernel.segments:
            if seg.target == naif_id and seg.start_jd <= jd_tt <= seg.end_jd:
                pos = seg.compute(jd_tt)
                return (float(pos[0]), float(pos[1]), float(pos[2]))
        raise KeyError(
            f"No segment covers NAIF {naif_id} at JD {jd_tt:.2f}. "
            "The date may be outside the kernel's coverage."
        )

    def list_naif_ids(self) -> list[int]:
        return sorted(self._available)

    def has_segment_at(self, center: int, target: int, jd: float) -> bool:
        """Return True if a segment for (center, target) covers jd."""
        for seg in self._kernel.segments:
            if (seg.target == target and seg.center == center
                    and seg.start_jd <= jd <= seg.end_jd):
                return True
        return False

    def coverage(self) -> dict[tuple[int, int], tuple[float, float]]:
        """
        Return the epoch range covered by each (center, target) pair.

        Returns
        -------
        dict mapping (center_naif_id, target_naif_id) to (start_jd, end_jd).
        """
        result: dict[tuple[int, int], tuple[float, float]] = {}
        for seg in self._kernel.segments:
            key = (seg.center, seg.target)
            if key in result:
                result[key] = (
                    min(result[key][0], seg.start_jd),
                    max(result[key][1], seg.end_jd),
                )
            else:
                result[key] = (seg.start_jd, seg.end_jd)
        return result

    def close(self) -> None:
        try:
            self._kernel.close()
        except Exception:
            pass

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
    """
    jplephem BaseSegment extension for SPK type 13 (Hermite interpolation,
    unequal time steps).

    Registered in jplephem's segment class registry at module import time so
    SPK.open() handles type 13 files transparently.

    Segment layout (1-indexed DAF words from start_i to end_i):
      [start_i,          start_i + 6N − 1] : N state vectors (x,y,z,vx,vy,vz)
      [start_i + 6N,     start_i + 7N − 1] : N epochs (seconds from J2000)
      [start_i + 7N,     end_i − 2        ] : epoch directory (every 100th)
      [end_i − 1,        end_i            ] : [window_size, N]

    Canon: NAIF SPK Required Reading §2.3.13
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
    """
    Thin wrapper around a jplephem SPK file for small-body position queries.

    Opens a single JPL SPK kernel file, indexes its available NAIF body IDs
    and reference centers, and provides a position() method returning the ICRF
    position of a body at a given JD.

    Used by both moira.asteroids and moira.comets; factored here to avoid
    duplication between those modules.

    Parameters
    ----------
    path : Path to a .bsp SPK kernel file.

    Raises
    ------
    FileNotFoundError : if the kernel file does not exist.
    KeyError          : from position() if no segment covers the body/JD.
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

    def close(self) -> None:
        try:
            self._kernel.close()
        except Exception:
            pass

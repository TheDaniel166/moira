"""
Moira - polar_motion.py

Lazy loading and interpolation of IERS polar motion coordinates for
topocentric observer corrections.
"""

import bisect
import logging
import math
from pathlib import Path

from .constants import ARCSEC2RAD

logger = logging.getLogger(__name__)

_MJD_OFFSET = 2400000.5
_MAX_POLAR_MOTION_ARCSEC = 1.0


class PolarMotionRegistry:
    """
    RITE: The Polar Motion Registry.

    THEOREM: Governs lazy loading and interpolation of bundled polar-motion
    coordinates for topocentric correction workflows.

    RITE OF PURPOSE:
        PolarMotionRegistry provides a single inspectable holder for the
        repository's bundled IERS polar-motion table. It delays file access
        until first use, clamps clearly invalid input rows, and offers a
        deterministic interpolation surface for observer-frame corrections.

    LAW OF OPERATION:
        Responsibilities:
            - Load the bundled polar-motion file on first demand.
            - Cache parsed MJD, x_p, and y_p values.
            - Interpolate polar motion linearly between neighboring rows.
            - Clamp out-of-bounds arcsecond values to the admitted range.
        Non-responsibilities:
            - Does not fetch live IERS products.
            - Does not own refraction, precession, or topocentric transforms.
            - Does not model sub-daily polar-motion structure beyond linear interpolation.
        Dependencies:
            - stdlib ``pathlib``, ``bisect``, and ``logging``.
        Structural invariants:
            - ``_data`` is either ``None`` or a tuple of sorted ``(mjd, x_p, y_p)`` rows.
            - ``_mjds`` is either ``None`` or aligned with ``_data`` row order.
            - ``_path`` always points to the bundled polar-motion file location.
        Failure behavior:
            - Missing files or malformed rows degrade to logged fallbacks, not hard failure.

    Canon: IERS polar-motion tabulation as bundled repository data.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.polar_motion.PolarMotionRegistry",
      "risk": "medium",
      "api": {
        "frozen": ["polar_motion_at"],
        "internal": ["_load", "_data", "_mjds", "_load_attempted", "_path"]
      },
      "state": {
        "mutable": true,
        "owners": ["PolarMotionRegistry"]
      },
      "effects": {
        "signals_emitted": [],
        "io": ["bundled_file_read", "logging"]
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

    _data: tuple[tuple[float, float, float], ...] | None = None
    _mjds: tuple[float, ...] | None = None
    _load_attempted = False
    _path = Path(__file__).resolve().parent / "data" / "iers_polar_motion.txt"

    @classmethod
    def polar_motion_at(cls, jd_ut: float) -> tuple[float, float]:
        """Return interpolated (x_p, y_p) in arcseconds for a UT1-like JD."""
        if cls._data is None:
            cls._load()

        if not cls._data:
            return (0.0, 0.0)

        mjd = float(jd_ut) - _MJD_OFFSET
        first_mjd, first_x, first_y = cls._data[0]
        last_mjd, last_x, last_y = cls._data[-1]

        if mjd <= first_mjd:
            return (first_x, first_y)
        if mjd >= last_mjd:
            return (last_x, last_y)

        idx = bisect.bisect_right(cls._mjds, mjd)
        left_mjd, left_x, left_y = cls._data[idx - 1]
        right_mjd, right_x, right_y = cls._data[idx]

        if mjd == left_mjd:
            return (left_x, left_y)
        if mjd == right_mjd:
            return (right_x, right_y)

        span = right_mjd - left_mjd
        if span <= 0.0:
            return (left_x, left_y)

        t = (mjd - left_mjd) / span
        x_p = left_x + t * (right_x - left_x)
        y_p = left_y + t * (right_y - left_y)
        return (x_p, y_p)

    @classmethod
    def _load(cls) -> None:
        cls._load_attempted = True
        rows: list[tuple[float, float, float]] = []

        if not cls._path.exists():
            logger.warning(
                "Polar motion data file is missing: %s; using zero polar motion.",
                cls._path,
            )
            cls._data = ()
            cls._mjds = ()
            return

        with cls._path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 3:
                    logger.warning(
                        "Skipping malformed polar motion line %d in %s.",
                        line_number,
                        cls._path.name,
                    )
                    continue
                try:
                    mjd = float(parts[0])
                    x_p = float(parts[1])
                    y_p = float(parts[2])
                except ValueError:
                    logger.warning(
                        "Skipping malformed polar motion line %d in %s.",
                        line_number,
                        cls._path.name,
                    )
                    continue
                clamped_x = max(-_MAX_POLAR_MOTION_ARCSEC, min(_MAX_POLAR_MOTION_ARCSEC, x_p))
                clamped_y = max(-_MAX_POLAR_MOTION_ARCSEC, min(_MAX_POLAR_MOTION_ARCSEC, y_p))
                if clamped_x != x_p or clamped_y != y_p:
                    logger.warning(
                        "Clamping out-of-bounds polar motion at MJD %.1f in %s.",
                        mjd,
                        cls._path.name,
                    )
                rows.append((mjd, clamped_x, clamped_y))

        rows.sort(key=lambda row: row[0])
        cls._data = tuple(rows)
        cls._mjds = tuple(row[0] for row in rows)


def polar_motion_matrix(x_p_arcsec: float, y_p_arcsec: float) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]:
    """
    Return the SOFA-compatible polar motion matrix for x_p and y_p.

    This matches the ``pom00`` zero-s' branch:
        R = R_y(-x_p) * R_x(-y_p)
    using the SOFA axis/sign convention.
    """
    if x_p_arcsec == 0.0 and y_p_arcsec == 0.0:
        return (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        )

    x_r = x_p_arcsec * ARCSEC2RAD
    y_r = y_p_arcsec * ARCSEC2RAD

    sx = math.sin(x_r)
    cx = math.cos(x_r)
    sy = math.sin(y_r)
    cy = math.cos(y_r)

    return (
        (cx, 0.0, sx),
        (sx * sy, cy, -cx * sy),
        (-sx * cy, sy, cx * cy),
    )

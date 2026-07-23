"""Shared, scale-explicit result vessels for global eclipse products.

This module owns only semantics that are identical for solar and lunar
eclipses.  Product-specific shadow, contact, surface, and cartography doctrine
belongs in the corresponding solar or lunar module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "EclipseEpoch",
    "EclipseGeocentricBodyState",
]


def _require_nonempty_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_finite(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class EclipseEpoch:
    """One eclipse instant expressed explicitly in TT and UT1."""

    jd_tt: float
    jd_ut1: float
    delta_t_seconds: float
    time_policy: str

    def __post_init__(self) -> None:
        for name in ("jd_tt", "jd_ut1", "delta_t_seconds"):
            _require_finite(name, getattr(self, name))
        _require_nonempty_text("time_policy", self.time_policy)
        recovered_delta_t = (float(self.jd_tt) - float(self.jd_ut1)) * 86400.0
        tolerance_seconds = max(
            5.0e-5,
            8.0 * math.ulp(max(abs(float(self.jd_tt)), abs(float(self.jd_ut1))))
            * 86400.0,
        )
        if abs(recovered_delta_t - float(self.delta_t_seconds)) > tolerance_seconds:
            raise ValueError(
                "delta_t_seconds must equal (jd_tt - jd_ut1) * 86400"
            )


@dataclass(frozen=True, slots=True)
class EclipseGeocentricBodyState:
    """Apparent geocentric body state at one named eclipse epoch."""

    body: str
    right_ascension_deg: float
    declination_deg: float
    distance_km: float
    semidiameter_deg: float
    horizontal_parallax_deg: float
    origin: str
    frame: str
    correction_policy: str

    def __post_init__(self) -> None:
        _require_nonempty_text("body", self.body)
        _require_nonempty_text("origin", self.origin)
        _require_nonempty_text("frame", self.frame)
        _require_nonempty_text("correction_policy", self.correction_policy)
        for name in (
            "right_ascension_deg",
            "declination_deg",
            "distance_km",
            "semidiameter_deg",
            "horizontal_parallax_deg",
        ):
            _require_finite(name, getattr(self, name))
        if not 0.0 <= float(self.right_ascension_deg) < 360.0:
            raise ValueError("right_ascension_deg must be in [0, 360)")
        if not -90.0 <= float(self.declination_deg) <= 90.0:
            raise ValueError("declination_deg must be in [-90, 90]")
        if float(self.distance_km) <= 0.0:
            raise ValueError("distance_km must be positive")
        if not 0.0 < float(self.semidiameter_deg) < 90.0:
            raise ValueError("semidiameter_deg must be in (0, 90)")
        if not 0.0 < float(self.horizontal_parallax_deg) < 90.0:
            raise ValueError("horizontal_parallax_deg must be in (0, 90)")

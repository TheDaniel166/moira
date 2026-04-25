"""
Internal astronomy-method mixin for the public Moira facade.

These methods preserve the legacy ``Moira`` convenience surface while delegating
astronomical truth to the owning engine modules.
"""

import sys
from datetime import datetime
from typing import Any


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class AstronomyFacadeMixin:
    """RITE: The Sky-Reader — the layer that bridges the public Moira surface
    to heliocentric positions, fixed-star lookups, visibility conditions,
    nakshatra placements, and antiscia geometry.

THEOREM: Mixin that aggregates astronomy-facing convenience wrappers for
         the public ``moira.facade.Moira`` class: heliocentric, star_at,
         heliacal_rising, nakshatra, antiscia, and related methods.

RITE OF PURPOSE:
    AstronomyFacadeMixin extracts all astronomy-oriented public methods
    from the monolithic facade.py into a coherent composable unit.
    It preserves the legacy Moira surface while ensuring each
    delegation routes to the authoritative engine module.

LAW OF OPERATION:
    Responsibilities:
        - Delegate heliocentric position calls to ``all_heliocentric_at``.
        - Delegate star lookup, heliacal, nakshatra, and antiscia calls
          to their owning modules via the facade module reference.
    Non-responsibilities:
        - Does not perform any astronomical computation itself.
        - Does not own kernel lifecycle.
    Dependencies:
        - moira.facade (resolved at runtime via sys.modules)
    Structural invariants:
        - All methods delegate to facade-module callables.

Canon: Moira Sovereign Facade Architecture; moira.facade astronomy policy.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_astronomy.AstronomyFacadeMixin",
    "risk": "medium",
    "api": {"frozen": ["heliocentric", "star_at", "heliacal_rising", "nakshatra", "antiscia"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    def heliocentric(self, dt: datetime, bodies: list[str] | None = None):
        """Return heliocentric ecliptic positions for all or specified planets."""
        facade = _facade_module()
        return facade.all_heliocentric_at(
            facade.jd_from_datetime(dt), bodies=bodies, reader=self._reader
        )

    def planetocentric(
        self,
        observer: str,
        dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Return positions as seen from the center of ``observer``."""
        facade = _facade_module()
        return facade.all_planetocentric_at(
            observer,
            facade.jd_from_datetime(dt),
            bodies=bodies,
            reader=self._reader,
        )

    def ssb_chart(self, dt: datetime, bodies: list[str] | None = None):
        """Return ecliptic positions relative to the Solar System Barycenter."""
        facade = _facade_module()
        return facade.all_ssb_positions_at(
            facade.jd_from_datetime(dt), bodies=bodies, reader=self._reader
        )

    def received_light(self, dt: datetime, bodies: list[str] | None = None):
        """Return received-light positions for the given bodies."""
        facade = _facade_module()
        return facade.all_received_light_at(
            facade.jd_from_datetime(dt), bodies=bodies, reader=self._reader
        )

    def twilight(self, dt: datetime, latitude: float, longitude: float):
        """Calculate civil, nautical, and astronomical twilight times."""
        facade = _facade_module()
        return facade.twilight_times(
            facade.jd_from_datetime(dt), latitude, longitude
        )

    def phase(self, body: str, dt: datetime) -> dict[str, float]:
        """Return phase metrics for a body at a given time."""
        facade = _facade_module()
        from .phase import (
            apparent_magnitude as _mag,
            illuminated_fraction as _ill,
            phase_angle as _pa,
        )

        jd = facade.jd_from_datetime(dt)
        pa = _pa(body, jd)
        return {
            "phase_angle": pa,
            "illumination": _ill(pa),
            "angular_diameter_arcsec": facade.angular_diameter(body, jd),
            "apparent_magnitude": _mag(body, jd),
        }

    def synodic_phase(self, body1: str, body2: str, dt: datetime) -> dict[str, float | str]:
        """Return synodic phase metrics for an arbitrary body pair."""
        _ = self._reader
        facade = _facade_module()
        from .phase import synodic_phase_angle as _spa, synodic_phase_state as _sps

        jd = facade.jd_from_datetime(dt)
        ang = _spa(body1, body2, jd)
        return {
            "phase_angle": ang,
            "phase_fraction": ang / 360.0,
            "phase_state": _sps(ang),
        }

    def fixed_star(self, name: str, dt: datetime):
        """Return the tropical ecliptic position of a fixed star."""
        facade = _facade_module()
        from .julian import ut_to_tt as _utt
        from .stars import star_at as _star_at

        jd = facade.jd_from_datetime(dt)
        return _star_at(name, _utt(jd))

    def heliacal_rising(
        self,
        star_name: str,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> float | None:
        """Find the JD of the heliacal rising of a fixed star."""
        facade = _facade_module()
        from .stars import heliacal_rising as _hr

        return _hr(star_name, facade.jd_from_datetime(dt), latitude, longitude)

    def heliacal_setting(
        self,
        star_name: str,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> float | None:
        """Find the JD of the heliacal setting of a fixed star."""
        facade = _facade_module()
        from .stars import heliacal_setting as _hs

        return _hs(star_name, facade.jd_from_datetime(dt), latitude, longitude)

    def heliacal_rising_event(
        self,
        star_name: str,
        dt: datetime,
        latitude: float,
        longitude: float,
    ):
        """Find the next heliacal rising of a fixed star with metadata."""
        facade = _facade_module()
        from .stars import heliacal_rising_event as _hre

        return _hre(star_name, facade.jd_from_datetime(dt), latitude, longitude)

    def heliacal_setting_event(
        self,
        star_name: str,
        dt: datetime,
        latitude: float,
        longitude: float,
    ):
        """Find the next heliacal setting of a fixed star with metadata."""
        facade = _facade_module()
        from .stars import heliacal_setting_event as _hse

        return _hse(star_name, facade.jd_from_datetime(dt), latitude, longitude)

    def nakshatras(self, chart, ayanamsa_system: str | None = None):
        """Compute nakshatra positions for all planets in a chart."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        return facade.all_nakshatras_at(
            chart.longitudes(include_nodes=False), chart.jd_ut, system
        )

    def antiscia(self, chart, orb: float = 1.0):
        """Find antiscia and contra-antiscia aspects in a chart."""
        return _facade_module().find_antiscia(chart.longitudes(), orb=orb)

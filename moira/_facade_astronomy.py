"""
Internal astronomy-method mixin for the public Moira facade.

These methods preserve the legacy ``Moira`` convenience surface while delegating
astronomical truth to the owning engine modules.
"""

from __future__ import annotations

import math
import sys
from datetime import datetime
from typing import Any


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


def _convention_epoch(dt: datetime, timescale: str) -> float:
    """Convert UTC once into the explicitly selected source realization clock."""
    facade = _facade_module()
    clock = facade.ConventionClock(timescale)
    jd_utc = facade.jd_from_datetime(dt)
    return (facade.utc_to_tt(jd_utc) if clock is facade.ConventionClock.TT
            else facade.utc_to_ut1(jd_utc))


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
    "api": {"frozen": ["heliocentric", "star_at", "heliacal_rising", "nakshatra", "antiscia", "baker_vulcan", "mean_priapus", "osculating_priapus", "orbital_second_focus", "arta_osculating_set", "selena", "abramov_proserpina", "hypothetical_orbit"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    def baker_vulcan(self, dt: datetime):
        """Return Baker's symbolic longitude from ordinary planetary inputs."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.baker_vulcan_at(jd_ut1, reader=self._reader)

    def arta_osculating_set(self, dt: datetime, *, frame: str):
        """Return the fourfold Arta construction using owned geometric inputs."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.arta_osculating_set_at(jd_ut1, frame=frame, reader=self._reader)

    def selena(
        self, dt: datetime, *, anchor_jd: float, anchor_longitude: float,
        year_days: float, timescale: str, frame: str,
    ):
        """Return seven-year Selena with the caller's complete anchor policy."""
        facade = _facade_module()
        return facade.selena_seven_year_at(
            _convention_epoch(dt, timescale), anchor_jd=anchor_jd,
            anchor_longitude=anchor_longitude, year_days=year_days,
            timescale=timescale, frame=frame,
        )

    def abramov_proserpina(self, dt: datetime, *, rule: str, timescale: str, frame: str):
        """Return the selected source approximation with explicit clock/frame."""
        facade = _facade_module()
        return facade.abramov_proserpina_at(
            _convention_epoch(dt, timescale), rule=rule, timescale=timescale, frame=frame,
        )

    def hypothetical_orbit(self, orbit, dt: datetime, *, frame: str):
        """Return geometric prescribed-orbit coordinates using its selected clock."""
        facade = _facade_module()
        return facade.hypothetical_orbit_at(
            orbit, _convention_epoch(dt, orbit.timescale), frame=frame,
        )

    def mean_priapus(self, dt: datetime, *, nutation: bool = True):
        """Return the explicitly selected mean lunar perigee model."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.mean_priapus(jd_ut1, nutation=nutation)

    def osculating_priapus(self, dt: datetime):
        """Return lunar perigee with the parent osculating-apogee receipt."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.osculating_priapus(jd_ut1, reader=self._reader)

    def orbital_second_focus(
        self, body: str | int, dt: datetime, *, center: str, frame: str,
    ):
        """Return central-focus-relative geometry in an explicit orbital frame."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.orbital_second_focus(
            body, jd_ut1, center=center, frame=frame, reader=self._reader,
        )

    def heliocentric(self, dt: datetime, bodies: list[str] | None = None):
        """Return heliocentric ecliptic positions for all or specified planets."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.all_heliocentric_at(
            jd_ut1, bodies=bodies, reader=self._reader
        )

    def planetocentric(
        self,
        observer: str,
        dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Return positions as seen from the center of ``observer``."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.all_planetocentric_at(
            observer,
            jd_ut1,
            bodies=bodies,
            reader=self._reader,
        )

    def ssb_chart(self, dt: datetime, bodies: list[str] | None = None):
        """Return ecliptic positions relative to the Solar System Barycenter."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.all_ssb_positions_at(
            jd_ut1, bodies=bodies, reader=self._reader
        )

    def received_light(self, dt: datetime, bodies: list[str] | None = None):
        """Return received-light positions for the given bodies."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.all_received_light_at(
            jd_ut1, bodies=bodies, reader=self._reader
        )

    def twilight(self, dt: datetime, latitude: float, longitude: float):
        """Calculate civil, nautical, and astronomical twilight times."""
        facade = _facade_module()
        jd_utc = facade.jd_from_datetime(dt)
        # Twilight is a civil-date product whose reductions are UT1-based.
        # Select 00:00 on the requested UTC date before crossing the clock
        # boundary so DUT1 cannot move a near-midnight request to another day.
        jd_day_utc = math.floor(jd_utc - 0.5) + 0.5
        jd_day_ut1 = facade.utc_to_ut1(jd_day_utc)
        return facade.twilight_times(
            jd_day_ut1, latitude, longitude
        )

    def phase(self, body: str, dt: datetime) -> dict[str, float]:
        """Return phase metrics for a body at a given time."""
        facade = _facade_module()
        from .phase import (
            apparent_magnitude as _mag,
            illuminated_fraction as _ill,
            phase_angle as _pa,
        )

        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        pa = _pa(body, jd_ut1)
        return {
            "phase_angle": pa,
            "illumination": _ill(pa),
            "angular_diameter_arcsec": facade.angular_diameter(body, jd_ut1),
            "apparent_magnitude": _mag(body, jd_ut1),
        }

    def lunar_orientation(self, dt: datetime, observer=None):
        """Return lunar libration and visible-disc orientation at ``dt``."""

        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.lunar_orientation_at(
            jd_ut1,
            observer=observer,
            reader=self._reader,
        )

    def synodic_phase(self, body1: str, body2: str, dt: datetime) -> dict[str, float | str]:
        """Return synodic phase metrics for an arbitrary body pair."""
        _ = self._reader
        facade = _facade_module()
        from .phase import synodic_phase_angle as _spa, synodic_phase_state as _sps

        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        ang = _spa(body1, body2, jd_ut1)
        return {
            "phase_angle": ang,
            "phase_fraction": ang / 360.0,
            "phase_state": _sps(ang),
        }

    def fixed_star(self, name: str, dt: datetime, product: str | None = None):
        """Return the tropical ecliptic position of a fixed star.

        ``product`` is ``"apparent"`` (the default: as seen from Earth, using
        this facade's kernel), ``"astrometric"``, or ``"geometric"``; see
        ``moira.stars.star_at``.
        """
        facade = _facade_module()
        from .stars import DEFAULT_STAR_PRODUCT, star_at as _star_at

        product = DEFAULT_STAR_PRODUCT if product is None else product

        jd = facade.jd_from_datetime(dt)
        jd_tt = facade.utc_to_tt(jd)
        return _star_at(name, jd_tt, product=product, reader=self._reader)

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

        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return _hr(star_name, jd_ut1, latitude, longitude)

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

        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return _hs(star_name, jd_ut1, latitude, longitude)

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

        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return _hre(star_name, jd_ut1, latitude, longitude)

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

        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return _hse(star_name, jd_ut1, latitude, longitude)

    def nakshatras(self, chart, ayanamsa_system: str | None = None):
        """Compute nakshatra positions for all planets in a chart."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        jd_ut1 = facade.utc_to_ut1(chart.jd_ut)
        return facade.all_nakshatras_at(
            chart.longitudes(include_nodes=False), jd_ut1, system
        )

    def antiscia(self, chart, orb: float = 1.0):
        """Find antiscia and contra-antiscia aspects in a chart."""
        return _facade_module().find_antiscia(chart.longitudes(), orb=orb)

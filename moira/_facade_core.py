"""
Internal core-method mixin for the public Moira facade.

This module keeps chart, house, sky-position, aspect, Julian-day, and sidereal
facade wrappers outside the large public export module. The computations remain
owned by their original engine modules.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class CoreFacadeMixin:
    """RITE: The Chart-Maker — the layer that assembles a complete snapshot
    of the heavens for an instant of time and returns it as a sovereign
    Chart vessel ready for all downstream astrological use.

THEOREM: Mixin that provides chart assembly, house calculation, sky-position
         lookup, aspect finding, Julian-day conversion, and sidereal
         time helpers for the public ``moira.facade.Moira`` class.

RITE OF PURPOSE:
    CoreFacadeMixin consolidates the most frequently called Moira
    convenience methods — chart, houses, sky_position, aspects,
    jd_from_datetime, and sidereal_time — into a single composable
    unit.  Without this mixin, every delegation of these calls would
    live in the monolithic facade.py and resist separation.

LAW OF OPERATION:
    Responsibilities:
        - Assemble Chart vessels from ``all_planets_at``, node
          functions, obliquity, and delta-T.
        - Delegate house calculation to ``calculate_houses``.
        - Delegate sky-position, aspect, and Julian-day helpers to
          their owning modules via the facade module reference.
    Non-responsibilities:
        - Does not own any astronomical math.
        - Does not manage kernel lifecycle; that is KernelFacadeMixin.
    Dependencies:
        - moira.facade (resolved at runtime via sys.modules)
        - moira.nodes.true_lilith, moira.nodes.true_node, etc.
    Structural invariants:
        - chart() always returns a Chart vessel or raises.

Canon: Moira Sovereign Facade Architecture; moira.facade core method policy.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_core.CoreFacadeMixin",
    "risk": "high",
    "api": {"frozen": ["chart", "houses", "sky_position", "aspects", "aspect_motion_witness", "aspects_from_longitudes", "jd_from_datetime", "sidereal_time"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    def chart(
        self,
        dt: datetime,
        bodies: list[str] | None = None,
        include_nodes: bool = True,
        observer_lat: float | None = None,
        observer_lon: float | None = None,
        observer_elev_m: float = 0.0,
    ):
        """
        Compute a complete set of planetary positions for a datetime.

        Parameters
        ----------
        dt              : timezone-aware datetime (UTC used as UT1 proxy)
        bodies          : list of Body.* constants (defaults to ALL_PLANETS)
        include_nodes   : include True Node, Mean Node, Lilith
        observer_lat    : geographic latitude for topocentric Moon (degrees)
        observer_lon    : geographic east longitude for topocentric Moon (degrees)
        observer_elev_m : observer elevation above sea level (metres)
        """
        facade = _facade_module()
        jd = facade.jd_from_datetime(dt)
        jd_tt = facade.utc_to_tt(jd)
        jd_ut1 = facade.utc_to_ut1(jd)

        lst_deg: float | None = None
        if observer_lat is not None and observer_lon is not None:
            dpsi_deg, _ = facade.nutation(jd_tt)
            lst_deg = facade.local_sidereal_time(
                jd_ut1,
                observer_lon,
                dpsi_deg,
                facade.true_obliquity(jd_tt),
            )

        planets = facade.all_planets_at(
            jd_ut1,
            bodies=bodies,
            reader=self._reader,
            observer_lat=observer_lat,
            observer_lon=observer_lon,
            observer_elev_m=observer_elev_m,
            lst_deg=lst_deg,
        )

        nodes: dict[str, Any] = {}
        if include_nodes:
            nodes[facade.Body.TRUE_NODE] = facade.true_node(jd, reader=self._reader)
            nodes[facade.Body.MEAN_NODE] = facade.mean_node(jd)
            nodes[facade.Body.LILITH] = facade.mean_lilith(jd)
            nodes[facade.Body.TRUE_LILITH] = facade.true_lilith(jd, reader=self._reader)

        obl = facade.true_obliquity(jd_tt)
        dt_s = facade.delta_t_from_jd(jd)

        return facade.Chart(
            jd_ut=jd,
            planets=planets,
            nodes=nodes,
            obliquity=obl,
            delta_t=dt_s,
        )

    def houses(
        self,
        dt: datetime,
        latitude: float,
        longitude: float,
        system: str | None = None,
        policy: Any | None = None,
    ):
        """Calculate house cusps for a time and geographic location."""
        facade = _facade_module()
        jd = facade.jd_from_datetime(dt)
        jd_ut1 = facade.utc_to_ut1(jd)
        house_system = facade.HouseSystem.PLACIDUS if system is None else system
        return facade.calculate_houses(
            jd_ut1, latitude, longitude, house_system, policy=policy
        )

    def sky_position(
        self,
        dt: datetime,
        body: str,
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
    ):
        """Calculate apparent topocentric RA/Dec and horizontal coordinates."""
        facade = _facade_module()
        jd = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.sky_position_at(
            body,
            jd,
            observer_lat=latitude,
            observer_lon=longitude,
            observer_elev_m=elevation_m,
            reader=self._reader,
        )

    def aspects(
        self,
        chart,
        orbs: dict[float, float] | None = None,
        include_minor: bool = True,
    ):
        """Find all aspects in a chart."""
        facade = _facade_module()
        speed_getter = getattr(chart, "speeds", None)
        speeds = speed_getter() if callable(speed_getter) else None
        return facade.find_aspects(
            chart.longitudes(),
            orbs=orbs,
            include_minor=include_minor,
            speeds=speeds,
        )

    def aspects_from_longitudes(
        self,
        longitudes,
        *,
        tier: int = 1,
        orb_factor: float = 1.0,
        include_nodes: bool = True,
    ):
        """Analyze a derived chart's supplied ecliptic longitudes."""

        return _facade_module().aspects_from_longitudes(
            longitudes,
            tier=tier,
            orb_factor=orb_factor,
            include_nodes=include_nodes,
        )

    def declination_aspects_from_declinations(
        self,
        declinations,
        *,
        reference_frame: str,
        timescale: str,
        orb: float = 1.0,
    ):
        """Analyze caller-supplied equatorial declinations for parallels."""

        return _facade_module().declination_aspects_from_declinations(
            declinations,
            reference_frame=reference_frame,
            timescale=timescale,
            orb=orb,
        )

    def aspect_motion_witness(
        self,
        body1: str,
        longitude1_deg: float,
        body2: str,
        longitude2_deg: float,
        aspect: str,
        *,
        speed1_deg_per_day: float | None = None,
        speed2_deg_per_day: float | None = None,
        orb_factor: float = 1.0,
        exact_tolerance_deg: float = 1e-9,
        rate_tolerance_deg_per_day: float = 1e-12,
        reference_frame: str,
        timescale: str,
    ):
        """Analyze signed instantaneous motion on one longitude-aspect branch."""

        return _facade_module().aspect_motion_witness(
            body1,
            longitude1_deg,
            body2,
            longitude2_deg,
            aspect,
            speed1_deg_per_day=speed1_deg_per_day,
            speed2_deg_per_day=speed2_deg_per_day,
            orb_factor=orb_factor,
            exact_tolerance_deg=exact_tolerance_deg,
            rate_tolerance_deg_per_day=rate_tolerance_deg_per_day,
            reference_frame=reference_frame,
            timescale=timescale,
        )

    def jd(self, year: int, month: int, day: int, hour: float = 0.0) -> float:
        """Compute Julian Day Number from a calendar date and decimal UT hour."""
        return _facade_module().julian_day(year, month, day, hour)

    def from_jd(self, jd: float) -> datetime:
        """Convert Julian Day to UTC datetime."""
        return _facade_module().datetime_from_jd(jd)

    def calendar_from_jd(self, jd: float):
        """Convert Julian Day to a BCE-safe UTC calendar date-time."""
        return _facade_module().calendar_datetime_from_jd(jd)

    def sidereal_chart(
        self,
        dt: datetime,
        ayanamsa_system: str | None = None,
        bodies: list[str] | None = None,
    ) -> dict[str, float]:
        """Return sidereal longitudes for all bodies."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        jd = facade.jd_from_datetime(dt)
        chart = self.chart(dt, bodies=bodies)
        ayan = facade.ayanamsa(jd, system)
        return {
            name: (p.longitude - ayan) % 360.0
            for name, p in chart.planets.items()
        }

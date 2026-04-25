"""
Internal spatial-method mixin for the public Moira facade.

These wrappers preserve the legacy ``Moira`` spatial surface while delegating
the actual computations to their owning modules.
"""

import sys
from datetime import datetime
from typing import Any


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class SpatialFacadeMixin:
    """RITE: The Earth-Mapper — the layer that routes the public Moira surface
    to geographically and spatially grounded techniques: astrocartography
    lines, geodetic equivalents, local-space azimuths, parans, and
    galactic house placements.

THEOREM: Mixin that provides spatial and geographic astrological method
         wrappers for the public ``moira.facade.Moira`` class, delegating
         each computation to its authoritative owning module.

RITE OF PURPOSE:
    SpatialFacadeMixin extracts all spatial-technique-facing public
    methods from the monolithic facade.py into a composable unit,
    preserving the legacy Moira surface while routing to the correct
    engine module without duplicating logic.

LAW OF OPERATION:
    Responsibilities:
        - Delegate astrocartography, geodetic, local-space, paran, and
          galactic-house computations to their owning modules.
    Non-responsibilities:
        - Does not implement any geographic or spatial math itself.
        - Does not own kernel lifecycle or reader management.
    Dependencies:
        - moira.facade (resolved at runtime via sys.modules)
    Structural invariants:
        - All methods delegate to facade-module callables.

Canon: Moira Sovereign Facade Architecture; moira.astrocartography,
       moira.parans, moira.galactic_houses spatial engine modules.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_spatial.SpatialFacadeMixin",
    "risk": "medium",
    "api": {"frozen": ["astrocartography", "geodetic", "local_space", "parans", "galactic_houses"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    def astrocartography(
        self,
        chart,
        observer_lat: float = 0.0,
        observer_lon: float = 0.0,
        bodies: list[str] | None = None,
        lat_step: float = 2.0,
    ):
        """Compute Astro*Carto*Graphy lines for a chart."""
        facade = _facade_module()
        from .julian import apparent_sidereal_time as _gast, ut_to_tt as _utt
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_tt = _utt(chart.jd_ut)
        dpsi, _ = _nut(jd_tt)
        gmst_deg = _gast(chart.jd_ut, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = facade.sky_position_at(
                body,
                chart.jd_ut,
                observer_lat=observer_lat,
                observer_lon=observer_lon,
                reader=self._reader,
            )
            planet_ra_dec[body] = (sky.right_ascension, sky.declination)

        return facade.acg_lines(planet_ra_dec, gmst_deg, lat_step=lat_step)

    def geodetic(
        self,
        chart,
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
    ):
        """Compute the Geodetic chart for the chart's birth location."""
        return _facade_module().geodetic_chart_from_chart(
            chart,
            zodiac=zodiac,
            ayanamsa_system=ayanamsa_system,
        )

    def geodetic_planet_equivalents(
        self,
        chart,
        bodies: list[str] | None = None,
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
    ) -> dict[str, float]:
        """Return geographic longitudes where natal planets are Geodetic MC."""
        return _facade_module().geodetic_equivalents_from_chart(
            chart,
            bodies=bodies,
            zodiac=zodiac,
            ayanamsa_system=ayanamsa_system,
        )

    def local_space(
        self,
        chart,
        latitude: float,
        longitude: float,
        bodies: list[str] | None = None,
    ):
        """Compute a Local Space chart."""
        facade = _facade_module()
        from .julian import local_sidereal_time as _lst, ut_to_tt as _utt
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_tt = _utt(chart.jd_ut)
        dpsi, _ = _nut(jd_tt)
        lst_deg = _lst(chart.jd_ut, longitude, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = facade.sky_position_at(
                body,
                chart.jd_ut,
                observer_lat=latitude,
                observer_lon=longitude,
                reader=self._reader,
            )
            planet_ra_dec[body] = (sky.right_ascension, sky.declination)

        return facade.local_space_positions(planet_ra_dec, latitude, lst_deg)

    def parans(
        self,
        natal_dt: datetime,
        latitude: float,
        longitude: float,
        bodies: list[str] | None = None,
        orb_minutes: float = 4.0,
    ):
        """Find natal parans on the birth day."""
        facade = _facade_module()
        if bodies is None:
            bodies = list(facade.Body.ALL_PLANETS)
        return facade.natal_parans(
            bodies,
            facade.jd_from_datetime(natal_dt),
            latitude,
            longitude,
            orb_minutes=orb_minutes,
        )

    def gauquelin_sectors(
        self,
        chart,
        latitude: float,
        longitude: float,
        bodies: list[str] | None = None,
    ):
        """Compute Gauquelin sectors for chart planets."""
        facade = _facade_module()
        from .julian import local_sidereal_time as _lst, ut_to_tt as _utt
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_tt = _utt(chart.jd_ut)
        dpsi, _ = _nut(jd_tt)
        lst_deg = _lst(chart.jd_ut, longitude, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = facade.sky_position_at(
                body,
                chart.jd_ut,
                observer_lat=latitude,
                observer_lon=longitude,
                reader=self._reader,
            )
            planet_ra_dec[body] = (sky.right_ascension, sky.declination)

        return facade.all_gauquelin_sectors(planet_ra_dec, latitude, lst_deg)

    def galactic_chart(self, chart, bodies: list[str] | None = None):
        """Compute galactic coordinates for chart bodies."""
        facade = _facade_module()
        obliquity = chart.obliquity
        if bodies is None:
            planet_data = {
                name: (p.longitude, p.latitude)
                for name, p in chart.planets.items()
            }
            planet_data.update({
                name: (n.longitude, 0.0)
                for name, n in chart.nodes.items()
            })
        else:
            planet_data = {}
            for name in bodies:
                if name in chart.planets:
                    p = chart.planets[name]
                    planet_data[name] = (p.longitude, p.latitude)
                elif name in chart.nodes:
                    planet_data[name] = (chart.nodes[name].longitude, 0.0)
        from .julian import ut_to_tt as _utt

        return facade.all_galactic_positions(planet_data, obliquity, _utt(chart.jd_ut))

    def galactic_angles(self, chart) -> dict[str, tuple[float, float]]:
        """Return ecliptic positions of principal galactic reference points."""
        from .julian import ut_to_tt as _utt

        return _facade_module().galactic_reference_points(
            chart.obliquity, _utt(chart.jd_ut)
        )

    def galactic_houses(
        self,
        dt: datetime,
        latitude: float,
        longitude: float,
    ):
        """Compute Galactic Porphyry house cusps."""
        facade = _facade_module()
        return facade.calculate_galactic_houses(
            facade.jd_from_datetime(dt), latitude, longitude
        )

    def uranian(self, dt: datetime):
        """Compute positions for all Uranian hypothetical planets."""
        facade = _facade_module()
        return facade.all_uranian_at(facade.jd_from_datetime(dt))

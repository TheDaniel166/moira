"""
Internal spatial-method mixin for the public Moira facade.

These wrappers preserve the legacy ``Moira`` spatial surface while delegating
the actual computations to their owning modules.
"""

from __future__ import annotations

import math
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
    "api": {"frozen": ["astrocartography", "subplanetary_points", "geodetic", "local_space", "parans", "galactic_houses", "relocated_chart"], "internal": []},
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
        from .julian import apparent_sidereal_time as _gast
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_utc = chart.jd_ut
        jd_ut1 = facade.utc_to_ut1(jd_utc)
        jd_tt = facade.utc_to_tt(jd_utc)
        dpsi, _ = _nut(jd_tt)
        gmst_deg = _gast(jd_ut1, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = facade.sky_position_at(
                body,
                jd_ut1,
                observer_lat=observer_lat,
                observer_lon=observer_lon,
                reader=self._reader,
            )
            planet_ra_dec[body] = (sky.right_ascension, sky.declination)

        return facade.acg_lines(planet_ra_dec, gmst_deg, lat_step=lat_step)

    def fixed_star_astrocartography(
        self,
        star_names,
        jd_ut: float,
        jd_tt: float,
        *,
        lat_step: float = 2.0,
        refraction: bool = False,
    ):
        """Compute source-resolved fixed-star ACG lines and zenith/nadir points."""
        return _facade_module().fixed_star_astrocartography(
            star_names,
            jd_ut,
            jd_tt,
            lat_step=lat_step,
            refraction=refraction,
        )

    def transiting_astrocartography(
        self,
        epochs_jd_ut,
        bodies,
        **kwargs,
    ):
        """Build an explicit-epoch transiting ACG series with line shifts."""
        return _facade_module().transiting_astrocartography(
            epochs_jd_ut,
            bodies,
            reader=self._reader,
            **kwargs,
        )

    def subplanetary_points(
        self,
        chart,
        bodies: list[str] | None = None,
    ):
        """Compute zenith/nadir geographic points for chart bodies."""
        return _facade_module().subplanetary_from_chart(
            chart,
            bodies=bodies,
        )

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

    # -- Geodetic analysis (moira.geodetic_analysis/_curves/_timing/_uncertainty)
    #
    # Each method composes the owning modules on one epoch. The natal snapshot
    # comes first; a place's house figure then reuses the snapshot's UT1/TT
    # epochs and zodiac offset, which overlays and comparisons require.

    def _geodetic_epoch(self, dt: datetime) -> tuple[float, float]:
        """Return (JD UT1, JD TT) for a civil datetime on this engine's clock."""
        from ._ephemeris_time import _ut1_to_ephemeris_tt

        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return jd_ut1, _ut1_to_ephemeris_tt(jd_ut1, self._reader)

    @staticmethod
    def _geodetic_offset(
        zodiac: str,
        ayanamsa_system: str | None,
        jd_ut1: float,
    ) -> float | None:
        """Sidereal offset for one epoch; the tropical lane refuses a system."""
        if zodiac == "sidereal":
            if ayanamsa_system is None:
                raise ValueError(
                    "ayanamsa_system is required when zodiac='sidereal'. "
                    "Pass a system name from moira.sidereal.Ayanamsa."
                )
            from .sidereal import ayanamsa

            # moira.sidereal.ayanamsa is contracted for UT.
            return ayanamsa(jd_ut1, ayanamsa_system)
        if ayanamsa_system is not None:
            raise ValueError("zodiac='tropical' does not take an ayanamsa_system")
        return None

    def _geodetic_snapshot(
        self,
        dt: datetime,
        bodies: list[str] | None,
        zodiac: str,
        ayanamsa_system: str | None,
        error_policy: str,
    ):
        from .geodetic_inputs import geodetic_snapshot_at

        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return geodetic_snapshot_at(
            jd_ut1,
            list(facade.Body.ALL_PLANETS) if bodies is None else list(bodies),
            reader=self._reader,
            zodiac=zodiac,
            ayanamsa_deg=self._geodetic_offset(zodiac, ayanamsa_system, jd_ut1),
            ayanamsa_system=ayanamsa_system,
            error_policy=error_policy,
        )

    @staticmethod
    def _geodetic_figure_for(snapshot, location, system, house_policy, sun_longitude):
        """House figure for one place on the snapshot's epoch and offset."""
        from .geodetic_analysis import geodetic_house_chart
        from .obliquity import true_obliquity

        return geodetic_house_chart(
            location,
            obliquity=true_obliquity(snapshot.jd_tt),
            system=system,
            zodiac=snapshot.zodiac,
            ayanamsa_deg=snapshot.ayanamsa_deg if snapshot.zodiac == "sidereal" else None,
            ayanamsa_system=snapshot.ayanamsa_system,
            house_policy=house_policy,
            sun_longitude=sun_longitude,
            source_frame=snapshot.source_frame,
            jd_ut1=snapshot.jd_ut1,
            jd_tt=snapshot.jd_tt,
        )

    def geodetic_houses(
        self,
        location,
        dt: datetime,
        system: str,
        *,
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
        house_policy=None,
        sun_longitude: float | None = None,
    ):
        """Twelve-house Geodetic figure for a place, with obliquity at ``dt``.

        ``location`` is a ``moira.geodetic.GeodeticLocation``. Solar-dependent
        house systems need an explicit tropical ``sun_longitude``.
        """
        from .geodetic_analysis import geodetic_house_chart
        from .obliquity import true_obliquity

        jd_ut1, jd_tt = self._geodetic_epoch(dt)
        return geodetic_house_chart(
            location,
            obliquity=true_obliquity(jd_tt),
            system=system,
            zodiac=zodiac,
            ayanamsa_deg=self._geodetic_offset(zodiac, ayanamsa_system, jd_ut1),
            ayanamsa_system=ayanamsa_system,
            house_policy=house_policy,
            sun_longitude=sun_longitude,
            jd_ut1=jd_ut1,
            jd_tt=jd_tt,
        )

    def geodetic_overlay(
        self,
        natal_dt: datetime,
        location,
        system: str,
        *,
        aspect_policy,
        bodies: list[str] | None = None,
        angles: tuple[str, ...] = ("MC", "IC", "ASC", "DSC"),
        include_cusps: bool = False,
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
        house_policy=None,
        sun_longitude: float | None = None,
        error_policy: str = "raise",
    ):
        """Place natal bodies in, and aspect them to, a place's Geodetic figure.

        Bodies default to the ten planets. ``aspect_policy`` is a required
        ``moira.aspects.AspectPolicy``; contacts are static.
        """
        from .geodetic_analysis import geodetic_natal_overlay

        snapshot = self._geodetic_snapshot(natal_dt, bodies, zodiac, ayanamsa_system, error_policy)
        figure = self._geodetic_figure_for(snapshot, location, system, house_policy, sun_longitude)
        return geodetic_natal_overlay(
            figure,
            snapshot,
            aspect_policy=aspect_policy,
            angles=angles,
            include_cusps=include_cusps,
        )

    def geodetic_compare(
        self,
        natal_dt: datetime,
        locations,
        system: str,
        *,
        aspect_policy,
        bodies: list[str] | None = None,
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
        house_policy=None,
        sun_longitude: float | None = None,
        error_policy: str = "raise",
        order_by: str = "input",
    ):
        """Compare one natal snapshot across named places.

        ``locations`` are ``moira.geodetic_analysis.GeodeticNamedLocation``.
        ``order_by="minimum_contact_orb"`` is geometric ordering, not a score.
        """
        from .geodetic_analysis import compare_geodetic_locations
        from .obliquity import true_obliquity

        snapshot = self._geodetic_snapshot(natal_dt, bodies, zodiac, ayanamsa_system, error_policy)
        return compare_geodetic_locations(
            locations,
            snapshot,
            obliquity=true_obliquity(snapshot.jd_tt),
            system=system,
            aspect_policy=aspect_policy,
            house_policy=house_policy,
            sun_longitude=sun_longitude,
            error_policy=error_policy,
            order_by=order_by,
        )

    def geodetic_loci(
        self,
        natal_dt: datetime,
        *,
        bodies: list[str] | None = None,
        angles: tuple[str, ...] = ("MC", "IC", "ASC", "DSC"),
        curve_policy=None,
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
        error_policy: str = "raise",
    ):
        """Geographic curves where natal degrees fall on the Geodetic angles.

        These are loci of zodiacal longitudes at ecliptic latitude zero, not
        physical rising/setting tracks of off-ecliptic bodies.
        """
        from .geodetic_curves import geodetic_angular_loci
        from .obliquity import true_obliquity

        snapshot = self._geodetic_snapshot(natal_dt, bodies, zodiac, ayanamsa_system, error_policy)
        return geodetic_angular_loci(
            snapshot,
            obliquity=true_obliquity(snapshot.jd_tt),
            angles=angles,
            policy=curve_policy,
        )

    def geodetic_transits(
        self,
        location,
        reference_dt: datetime,
        mover: str,
        start_dt: datetime,
        end_dt: datetime,
        *,
        aspects,
        policy,
        angles: tuple[str, ...] = ("MC", "IC", "ASC", "DSC"),
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
    ):
        """When a mover aspects a place's Geodetic angles, frozen at ``reference_dt``.

        ``aspects`` are explicit ``(aspect_angle_deg, orb_deg)`` pairs and
        ``policy`` is a ``moira.geodetic_timing.GeodeticTimingPolicy``. Event
        epochs in the result are JD UT1, not civil UTC.
        """
        from .geodetic import geodetic_chart_at_location
        from .geodetic_timing import GeodeticFixedReference, find_geodetic_transits
        from .obliquity import true_obliquity

        facade = _facade_module()
        jd_ut1, jd_tt = self._geodetic_epoch(reference_dt)
        chart = geodetic_chart_at_location(
            location,
            true_obliquity(jd_tt),
            ayanamsa_deg=self._geodetic_offset(zodiac, ayanamsa_system, jd_ut1),
            zodiac=zodiac,
        )
        reference = GeodeticFixedReference(chart, jd_ut1, jd_tt, tuple(angles))
        return find_geodetic_transits(
            reference,
            mover,
            facade.utc_to_ut1(facade.jd_from_datetime(start_dt)),
            facade.utc_to_ut1(facade.jd_from_datetime(end_dt)),
            aspects=aspects,
            policy=policy,
            reader=self._reader,
        )

    def geodetic_uncertainty(self, chart, uncertainty, *, policy):
        """Diagnose how input uncertainty moves a Geodetic chart's angles.

        Includes the first-order sensitivity when it is representable. Sampled
        maxima are diagnostics, not confidence intervals or error bounds.
        """
        from .geodetic_uncertainty import diagnose_geodetic_uncertainty

        return diagnose_geodetic_uncertainty(chart, uncertainty, policy=policy)

    def relocated_chart(
        self,
        natal_dt: datetime,
        latitude: float,
        longitude: float,
        system: str | None = None,
        bodies: list[str] | None = None,
        policy: Any | None = None,
    ):
        """Compute a full relocated chart snapshot for a new geographic site."""
        facade = _facade_module()
        from .chart import create_chart

        jd = facade.jd_from_datetime(natal_dt)
        jd_ut1 = facade.utc_to_ut1(jd)
        house_system = facade.HouseSystem.PLACIDUS if system is None else system
        return create_chart(
            jd_ut1,
            latitude,
            longitude,
            house_system=house_system,
            bodies=bodies,
            reader=self._reader,
            policy=policy,
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
        from .julian import local_sidereal_time as _lst
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_utc = chart.jd_ut
        jd_ut1 = facade.utc_to_ut1(jd_utc)
        jd_tt = facade.utc_to_tt(jd_utc)
        dpsi, _ = _nut(jd_tt)
        lst_deg = _lst(jd_ut1, longitude, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = facade.sky_position_at(
                body,
                jd_ut1,
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
        jd_utc = facade.jd_from_datetime(natal_dt)
        # Preserve the requested UTC birth date, then convert that date's
        # midnight to the UT1 epoch required by the event solvers.  Flooring
        # an already-converted UT1 value would select the wrong civil day for
        # negative DUT1 in the first fraction of a second after midnight.
        jd_day_utc = math.floor(jd_utc - 0.5) + 0.5
        jd_day_ut1 = facade.utc_to_ut1(jd_day_utc)
        return facade.find_parans(
            bodies,
            jd_day_ut1,
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
        from .julian import local_sidereal_time as _lst
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_utc = chart.jd_ut
        jd_ut1 = facade.utc_to_ut1(jd_utc)
        jd_tt = facade.utc_to_tt(jd_utc)
        dpsi, _ = _nut(jd_tt)
        lst_deg = _lst(jd_ut1, longitude, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = facade.sky_position_at(
                body,
                jd_ut1,
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
        jd_tt = facade.utc_to_tt(chart.jd_ut)
        return facade.all_galactic_positions(planet_data, obliquity, jd_tt)

    def galactic_angles(self, chart) -> dict[str, tuple[float, float]]:
        """Return ecliptic positions of principal galactic reference points."""
        facade = _facade_module()
        return facade.galactic_reference_points(
            chart.obliquity, facade.utc_to_tt(chart.jd_ut)
        )

    def galactic_houses(
        self,
        dt: datetime,
        latitude: float,
        longitude: float,
    ):
        """Compute Galactic Porphyry house cusps."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.calculate_galactic_houses(
            jd_ut1, latitude, longitude
        )

    def uranian(self, dt: datetime):
        """Compute positions for all Uranian hypothetical planets."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.all_uranian_at(jd_ut1, reader=self._reader)

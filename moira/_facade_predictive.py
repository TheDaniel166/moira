"""
Internal predictive-method mixin for the public Moira facade.

The methods here are compatibility wrappers. Progression, transit, station,
return, syzygy, and planetary-hour computation remains owned by the underlying
engine modules.
"""

import sys
from datetime import datetime
from typing import Any

from .constants import HouseSystem


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class PredictiveFacadeMixin:
    """RITE: The Time-Mapper — the layer that routes the public Moira surface
    to predictive techniques: secondary progressions, transit search, solar
    and lunar returns, station detection, syzygy, and planetary hours.

THEOREM: Mixin that provides predictive astrological technique wrappers
         for the public ``moira.facade.Moira`` class, delegating each
         time-directed technique to the authoritative owning module.

RITE OF PURPOSE:
    PredictiveFacadeMixin extracts all predictive-technique-facing public
    methods from the monolithic facade.py into a composable unit,
    preserving the legacy Moira surface while cleanly routing to the
    correct engine module without duplicating logic.

LAW OF OPERATION:
    Responsibilities:
        - Delegate progression, transit, return, station, syzygy, and
          planetary-hour computations to their owning modules.
    Non-responsibilities:
        - Does not implement any predictive calculation itself.
        - Does not own kernel lifecycle or reader management.
    Dependencies:
        - moira.facade (resolved at runtime via sys.modules)
        - moira.constants.HouseSystem
    Structural invariants:
        - All methods delegate to facade-module callables.

Canon: Moira Sovereign Facade Architecture; moira.predictive and related
       time-direction engine modules.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_predictive.PredictiveFacadeMixin",
    "risk": "medium",
    "api": {"frozen": ["progression", "transits", "solar_return", "lunar_return", "station", "planetary_hours"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    def progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Secondary Progressed chart."""
        facade = _facade_module()
        return facade.secondary_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def solar_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Solar Arc directed chart."""
        facade = _facade_module()
        return facade.solar_arc(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def solar_arc_directions_ra(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Solar Arc directed chart measured in right ascension."""
        facade = _facade_module()
        return facade.solar_arc_right_ascension(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def naibod_in_longitude(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Naibod directions in ecliptic longitude."""
        facade = _facade_module()
        return facade.naibod_longitude(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def naibod_in_right_ascension(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Naibod directions in right ascension."""
        facade = _facade_module()
        return facade.naibod_right_ascension(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def tertiary_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Tertiary Progressed chart."""
        facade = _facade_module()
        return facade.tertiary_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def tertiary_ii_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Tertiary II / Klaus Wessel progression."""
        facade = _facade_module()
        return facade.tertiary_ii_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Secondary Progressed chart."""
        facade = _facade_module()
        return facade.converse_secondary_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_solar_arc(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Solar Arc directed chart."""
        facade = _facade_module()
        return facade.converse_solar_arc(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_solar_arc_ra(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Solar Arc directed chart measured in right ascension."""
        facade = _facade_module()
        return facade.converse_solar_arc_right_ascension(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_tertiary_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Tertiary Progressed chart."""
        facade = _facade_module()
        return facade.converse_tertiary_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_tertiary_ii_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Tertiary II / Klaus Wessel progression."""
        facade = _facade_module()
        return facade.converse_tertiary_ii_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def minor_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Minor Progressed chart."""
        facade = _facade_module()
        return facade.minor_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_naibod_in_longitude(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Naibod directions in ecliptic longitude."""
        facade = _facade_module()
        return facade.converse_naibod_longitude(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_naibod_in_right_ascension(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Naibod directions in right ascension."""
        facade = _facade_module()
        return facade.converse_naibod_right_ascension(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_minor_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Minor Progressed chart."""
        facade = _facade_module()
        return facade.converse_minor_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def duodenary_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Duodenary progression."""
        facade = _facade_module()
        return facade.duodenary_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_duodenary_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Duodenary progression."""
        facade = _facade_module()
        return facade.converse_duodenary_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def quotidian_solar_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Quotidian solar progression."""
        facade = _facade_module()
        return facade.quotidian_solar_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_quotidian_solar_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Quotidian solar progression."""
        facade = _facade_module()
        return facade.converse_quotidian_solar_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def quotidian_lunar_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Quotidian lunar progression."""
        facade = _facade_module()
        return facade.quotidian_lunar_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_quotidian_lunar_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ):
        """Converse Quotidian lunar progression."""
        facade = _facade_module()
        return facade.converse_quotidian_lunar_progression(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def planetary_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        arc_body: str,
        bodies: list[str] | None = None,
    ):
        """Planetary Arc directed chart."""
        facade = _facade_module()
        return facade.planetary_arc(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            arc_body=arc_body,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_planetary_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        arc_body: str,
        bodies: list[str] | None = None,
    ):
        """Converse Planetary Arc directed chart."""
        facade = _facade_module()
        return facade.converse_planetary_arc(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            arc_body=arc_body,
            bodies=bodies,
            reader=self._reader,
        )

    def ascendant_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        latitude: float,
        longitude: float,
        bodies: list[str] | None = None,
    ):
        """Ascendant Arc directed chart."""
        facade = _facade_module()
        return facade.ascendant_arc(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            latitude,
            longitude,
            bodies=bodies,
            reader=self._reader,
        )

    def daily_house_frame(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        latitude: float,
        longitude: float,
        system: str = HouseSystem.PLACIDUS,
    ):
        """Daily Houses progressed house frame."""
        facade = _facade_module()
        return facade.daily_houses(
            facade.jd_from_datetime(natal_dt),
            target_dt,
            latitude,
            longitude,
            system=system,
        )

    def transits(
        self,
        body: str,
        target_lon: float,
        jd_start: float,
        jd_end: float,
    ):
        """Find all transits of a body to a given longitude."""
        return _facade_module().find_transits(
            body, target_lon, jd_start, jd_end, reader=self._reader
        )

    def ingresses(self, body: str, jd_start: float, jd_end: float):
        """Find all sign ingresses for a body in a date range."""
        return _facade_module().find_ingresses(
            body, jd_start, jd_end, reader=self._reader
        )

    def next_ingress(
        self, body: str, jd_start: float, max_days: float | None = None
    ):
        """Find the next sign ingress of *body* after jd_start."""
        return _facade_module().next_ingress(
            body, jd_start, reader=self._reader, max_days=max_days
        )

    def next_ingress_into(
        self, body: str, sign: str, jd_start: float, max_days: float | None = None
    ):
        """Find the next time *body* enters a specific zodiac *sign*."""
        return _facade_module().next_ingress_into(
            body, sign, jd_start, reader=self._reader, max_days=max_days
        )

    def solar_return(self, natal_sun_lon: float, year: int) -> float:
        """Find the exact Julian Day of the Solar Return for a given year."""
        return _facade_module().solar_return(
            natal_sun_lon, year, reader=self._reader
        )

    def lunar_return(self, natal_moon_lon: float, jd_start: float) -> float:
        """Find the next Lunar Return after jd_start."""
        return _facade_module().lunar_return(
            natal_moon_lon, jd_start, reader=self._reader
        )

    def planet_return(
        self,
        body: str,
        natal_lon: float,
        jd_start: float,
        direction: str = "direct",
    ) -> float:
        """Find the next return of any planet to its natal longitude."""
        return _facade_module().planet_return(
            body, natal_lon, jd_start, direction=direction, reader=self._reader
        )

    def syzygy(self, jd: float) -> tuple[float, str]:
        """Find the prenatal syzygy."""
        return _facade_module().prenatal_syzygy(jd, reader=self._reader)

    def stations(self, body: str, jd_start: float, jd_end: float):
        """Find all retrograde and direct stations for a body in a date range."""
        return _facade_module().find_stations(
            body, jd_start, jd_end, reader=self._reader
        )

    def retrograde_periods(self, body: str, jd_start: float, jd_end: float):
        """Return retrograde intervals for a body."""
        return _facade_module().retrograde_periods(
            body, jd_start, jd_end, reader=self._reader
        )

    def planetary_hours(
        self,
        dt: datetime,
        latitude: float,
        longitude: float,
    ):
        """Calculate planetary hours for a date and location."""
        facade = _facade_module()
        return facade.planetary_hours(
            facade.jd_from_datetime(dt),
            latitude,
            longitude,
            reader=self._reader,
        )

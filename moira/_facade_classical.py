"""
Internal classical-method mixin for the public Moira facade.

These are compatibility wrappers for classical astrology surfaces. The
underlying computations remain owned by their domain modules.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class ClassicalFacadeMixin:
    """Lots, dignities, midpoints, harmonics, profections, and time-lords."""

    def lots(self, chart, houses):
        """Compute Arabic Parts / Hermetic Lots for a chart."""
        facade = _facade_module()
        lons = chart.longitudes(include_nodes=False)
        cusps_map = {i + 1: c for i, c in enumerate(houses.cusps)}
        day = facade.is_day_chart(lons.get("Sun", 0.0), houses.asc)
        return facade.calculate_lots(lons, cusps_map, day)

    def dignities(self, chart, houses):
        """Compute essential and accidental dignities for chart planets."""
        facade = _facade_module()
        planet_dicts = [
            {
                "name": name,
                "degree": data.longitude,
                "is_retrograde": data.speed < 0,
            }
            for name, data in chart.planets.items()
        ]
        house_dicts = [
            {"number": i + 1, "degree": cusp}
            for i, cusp in enumerate(houses.cusps)
        ]
        return facade.calculate_dignities(planet_dicts, house_dicts)

    def mutual_receptions(self, chart, by_exaltation: bool = False):
        """Find mutual receptions between planets."""
        return _facade_module().mutual_receptions(
            chart.longitudes(include_nodes=False),
            by_exaltation=by_exaltation,
        )

    def midpoints(self, chart, planet_set: str = "classic"):
        """Calculate all planetary midpoints."""
        return _facade_module().calculate_midpoints(chart.longitudes(), planet_set)

    def midpoints_to_point(
        self,
        chart,
        longitude: float,
        orb: float = 1.5,
    ):
        """Find midpoints that fall at or oppose a given longitude."""
        return _facade_module().midpoints_to_point(
            longitude, chart.longitudes(), orb=orb
        )

    def harmonic(self, chart, number: int):
        """Compute a harmonic chart."""
        return _facade_module().calculate_harmonic(
            chart.longitudes(include_nodes=False), number
        )

    def profection(
        self,
        natal_asc: float,
        natal_dt: datetime,
        current_dt: datetime,
        natal_positions: dict[str, float] | None = None,
    ):
        """Compute the current annual profection."""
        facade = _facade_module()
        return facade.profection_schedule(
            natal_asc,
            facade.jd_from_datetime(natal_dt),
            facade.jd_from_datetime(current_dt),
            natal_positions,
        )

    def firdaria(self, natal_dt: datetime, natal_chart, natal_houses=None):
        """Compute the Firdaria from birth."""
        facade = _facade_module()
        sun = natal_chart.planets.get("Sun")
        asc = natal_houses.asc if natal_houses is not None else 0.0
        day = facade.is_day_chart(sun.longitude if sun else 0.0, asc)
        return facade.firdaria(facade.jd_from_datetime(natal_dt), day)

    def zodiacal_releasing(
        self,
        lot_longitude: float,
        natal_dt: datetime,
        levels: int = 4,
    ):
        """Generate Zodiacal Releasing periods from a Lot."""
        facade = _facade_module()
        return facade.zodiacal_releasing(
            lot_longitude,
            facade.jd_from_datetime(natal_dt),
            levels=levels,
        )

    def vimshottari_dasha(
        self,
        natal_chart,
        natal_dt: datetime,
        levels: int = 2,
        ayanamsa_system: str | None = None,
    ):
        """Compute the Vimshottari Dasha sequence from birth."""
        facade = _facade_module()
        system = facade.Ayanamsa.LAHIRI if ayanamsa_system is None else ayanamsa_system
        moon = natal_chart.planets.get("Moon")
        if moon is None:
            raise ValueError("Moon not found in natal chart - include it when calling chart()")
        return facade.vimshottari(
            moon.longitude,
            facade.jd_from_datetime(natal_dt),
            levels=levels,
            ayanamsa_system=system,
        )

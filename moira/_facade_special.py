"""
Internal special-topic mixin for the public Moira facade.

This is the final compatibility wrapper layer for the legacy ``Moira`` facade:
eclipses, primary directions, longevity, phenomena, occultations, Sothic and
Egyptian calendar helpers, variable and multiple stars, void-of-course Moon,
electional windows, and representation.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class SpecialTopicsFacadeMixin:
    """RITE: The Final Witness — the layer that routes the public Moira surface
    to all remaining specialised domains: eclipse geometry, primary
    directions, longevity, phenomena, occultations, Sothic and Egyptian
    calendar helpers, variable and multiple stars, void-of-course Moon,
    electional windows, and representation.

THEOREM: Mixin that aggregates the remaining public ``moira.facade.Moira``
         compatibility wrappers not covered by the other facade mixins,
         delegating each call to its authoritative owning module.

RITE OF PURPOSE:
    SpecialTopicsFacadeMixin extracts the last cluster of specialised
    public methods from the monolithic facade.py, ensuring the Moira
    class remains a clean composed facade rather than a method-body
    gravity well.  Without this mixin, these methods would resist
    isolation and accumulate silently in facade.py.

LAW OF OPERATION:
    Responsibilities:
        - Delegate eclipse, primary-direction, longevity, phenomena,
          occultation, Sothic, variable-star, multiple-star,
          void-of-course, electional, and repr calls to their
          owning modules.
    Non-responsibilities:
        - Does not implement any astronomical or astrological math.
        - Does not own kernel lifecycle or reader management.
    Dependencies:
        - moira.facade (resolved at runtime via sys.modules)
    Structural invariants:
        - All methods delegate to facade-module callables.

Canon: Moira Sovereign Facade Architecture; moira.eclipse, moira.sothic,
       moira.occultations, moira.electional, and related domain modules.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_special.SpecialTopicsFacadeMixin",
    "risk": "medium",
    "api": {"frozen": ["eclipse", "primary_directions", "longevity", "phenomena", "occultations", "void_of_course", "electional"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

    def eclipse(self, dt: datetime):
        """Compute eclipse geometry and classification for a datetime."""
        facade = _facade_module()
        return facade.EclipseCalculator(reader=self._reader).calculate(dt)

    def speculum(self, chart, houses, geo_lat: float):
        """Compute the Placidus mundane speculum for a natal chart."""
        return _facade_module().speculum(chart, houses, geo_lat)

    def primary_directions(
        self,
        chart,
        houses,
        geo_lat: float,
        max_arc: float = 90.0,
        include_converse: bool = True,
        significators: list[str] | None = None,
        promissors: list[str] | None = None,
    ):
        """Find Placidus mundane primary direction arcs."""
        return _facade_module().find_primary_arcs(
            chart,
            houses,
            geo_lat,
            max_arc=max_arc,
            include_converse=include_converse,
            significators=significators,
            promissors=promissors,
        )

    def longevity(self, chart, houses):
        """Calculate the Hyleg and Alcocoden."""
        facade = _facade_module()
        lons = chart.longitudes(include_nodes=False)
        day = facade.is_day_chart(lons.get("Sun", 0.0), houses.asc)
        return facade.calculate_longevity(lons, houses.cusps, day)

    def planetary_nodes(self, dt: datetime):
        """Return heliocentric orbital nodes and apsides for all planets."""
        facade = _facade_module()
        return facade.all_planetary_nodes(facade.jd_from_datetime(dt))

    def patterns(self, chart, orb_factor: float = 1.0):
        """Find all aspect patterns in a chart."""
        facade = _facade_module()
        positions = chart.longitudes()
        asps = facade.find_aspects(positions, speeds=chart.speeds())
        return facade.find_all_patterns(positions, aspects=asps, orb_factor=orb_factor)

    def phenomena(self, body: str, jd_start: float, jd_end: float):
        """Find greatest elongations, perihelion, and aphelion for a body."""
        facade = _facade_module()
        events: list[Any] = []
        if body in (facade.Body.MERCURY, facade.Body.VENUS):
            east = facade.greatest_elongation(
                body,
                jd_start,
                direction="east",
                reader=self._reader,
                max_days=jd_end - jd_start,
            )
            west = facade.greatest_elongation(
                body,
                jd_start,
                direction="west",
                reader=self._reader,
                max_days=jd_end - jd_start,
            )
            for event in (east, west):
                if event is not None and jd_start <= event.jd_ut <= jd_end:
                    events.append(event)
        peri = facade.perihelion(
            body, jd_start, reader=self._reader, max_days=jd_end - jd_start
        )
        aphe = facade.aphelion(
            body, jd_start, reader=self._reader, max_days=jd_end - jd_start
        )
        for event in (peri, aphe):
            if event is not None and jd_start <= event.jd_ut <= jd_end:
                events.append(event)
        events.sort(key=lambda e: e.jd_ut)
        return events

    def moon_phases(self, jd_start: float, jd_end: float):
        """Return all Moon phases in a date range."""
        return _facade_module().moon_phases_in_range(
            jd_start, jd_end, reader=self._reader
        )

    def next_conjunction(
        self, body1: str, body2: str, jd_start: float, max_days: float = 1200.0
    ):
        """Find the next conjunction between two bodies."""
        return _facade_module().next_conjunction(
            body1, body2, jd_start, reader=self._reader, max_days=max_days
        )

    def conjunctions(self, body1: str, body2: str, jd_start: float, jd_end: float):
        """Find conjunctions between two bodies in a date range."""
        return _facade_module().conjunctions_in_range(
            body1, body2, jd_start, jd_end, reader=self._reader
        )

    def resonance(self, body1: str, body2: str):
        """Compute orbital resonance for two bodies."""
        return _facade_module().resonance(body1, body2)

    def lunar_mansions(self, chart):
        """Compute Arabic lunar mansions for chart planets."""
        return _facade_module().all_mansions_at(chart.longitudes(include_nodes=False))

    def occultations(
        self,
        jd_start: float,
        jd_end: float,
        targets: list[str] | None = None,
    ):
        """Find lunar occultations of planets in a date range."""
        return _facade_module().all_lunar_occultations(
            jd_start, jd_end, planets=targets, reader=self._reader
        )

    def close_approaches(
        self,
        body1: str,
        body2: str,
        jd_start: float,
        jd_end: float,
        max_sep_deg: float = 1.0,
    ):
        """Find close approaches between two bodies."""
        return _facade_module().close_approaches(
            body1,
            body2,
            jd_start,
            jd_end,
            max_sep_deg=max_sep_deg,
            reader=self._reader,
        )

    def sothic_cycle(
        self,
        latitude: float,
        longitude: float,
        year_start: int,
        year_end: int,
        arcus_visionis: float = 10.0,
    ):
        """Compute Sirius heliacal rising entries for a year range."""
        return _facade_module().sothic_rising(
            latitude,
            longitude,
            year_start,
            year_end,
            arcus_visionis=arcus_visionis,
        )

    def sothic_epoch_finder(
        self,
        latitude: float,
        longitude: float,
        year_start: int,
        year_end: int,
        tolerance_days: float = 1.0,
    ):
        """Find Sothic epochs in a year range."""
        return _facade_module().sothic_epochs(
            latitude,
            longitude,
            year_start,
            year_end,
            tolerance_days=tolerance_days,
        )

    def egyptian_date(self, dt: datetime, epoch_jd: float | None = None):
        """Convert a datetime to an Egyptian civil calendar date."""
        facade = _facade_module()
        from .sothic import _SOTHIC_EPOCH_139_JD

        return facade.egyptian_civil_date(
            facade.jd_from_datetime(dt), epoch_jd or _SOTHIC_EPOCH_139_JD
        )

    def variable_star_phase(self, name: str, dt: datetime) -> float:
        """Return the phase of a variable star at a given time."""
        facade = _facade_module()
        return facade.phase_at(
            facade.variable_star(name), facade.jd_from_datetime(dt)
        )

    def variable_star_magnitude(self, name: str, dt: datetime) -> float:
        """Estimate the V magnitude of a variable star at a given time."""
        facade = _facade_module()
        return facade.magnitude_at(
            facade.variable_star(name), facade.jd_from_datetime(dt)
        )

    def variable_star_next_minimum(self, name: str, dt: datetime) -> float | None:
        """Return the JD of the next primary minimum after dt."""
        facade = _facade_module()
        return facade.next_minimum(
            facade.variable_star(name), facade.jd_from_datetime(dt)
        )

    def variable_star_next_maximum(self, name: str, dt: datetime) -> float | None:
        """Return the JD of the next maximum after dt."""
        facade = _facade_module()
        return facade.next_maximum(
            facade.variable_star(name), facade.jd_from_datetime(dt)
        )

    def variable_star_minima(self, name: str, jd_start: float, jd_end: float):
        """Return primary minima JDs in a range."""
        facade = _facade_module()
        return facade.minima_in_range(facade.variable_star(name), jd_start, jd_end)

    def variable_star_maxima(self, name: str, jd_start: float, jd_end: float):
        """Return maxima JDs in a range."""
        facade = _facade_module()
        return facade.maxima_in_range(facade.variable_star(name), jd_start, jd_end)

    def variable_star_quality(self, name: str, dt: datetime) -> dict[str, float]:
        """Return variable-star quality scores at dt."""
        facade = _facade_module()
        star = facade.variable_star(name)
        jd = facade.jd_from_datetime(dt)
        return {
            "phase": facade.phase_at(star, jd),
            "magnitude": facade.magnitude_at(star, jd),
            "malefic_intensity": facade.malefic_intensity(star, jd),
            "benefic_strength": facade.benefic_strength(star, jd),
            "is_eclipsed": facade.is_in_eclipse(star, jd),
        }

    def multiple_star_separation(
        self, name: str, dt: datetime, aperture_mm: float = 100.0
    ) -> dict:
        """Return the orbital state of a multiple star system."""
        facade = _facade_module()
        system = facade.multiple_star(name)
        jd = facade.jd_from_datetime(dt)
        return {
            "separation_arcsec": facade.angular_separation_at(system, jd),
            "position_angle_deg": facade.position_angle_at(system, jd),
            "is_resolvable": facade.is_resolvable(system, jd, aperture_mm),
            "dominant_component": facade.dominant_component(system).label,
            "combined_magnitude": facade.combined_magnitude(system),
            "system_type": system.system_type,
        }

    def multiple_star_components(self, name: str, dt: datetime) -> dict:
        """Return the full component snapshot of a multiple star system."""
        facade = _facade_module()
        return facade.components_at(
            facade.multiple_star(name), facade.jd_from_datetime(dt)
        )

    def moon_void_of_course(self, dt: datetime, modern: bool = False):
        """Return the Moon void-of-course window for dt."""
        facade = _facade_module()
        return facade.void_of_course_window(
            facade.jd_from_datetime(dt), reader=self._reader, modern=modern
        )

    def is_moon_void_of_course(self, dt: datetime, modern: bool = False) -> bool:
        """Return True if the Moon is void of course at dt."""
        facade = _facade_module()
        return facade.is_void_of_course(
            facade.jd_from_datetime(dt), reader=self._reader, modern=modern
        )

    def electional_windows(
        self,
        dt_start: datetime,
        dt_end: datetime,
        latitude: float,
        longitude: float,
        predicate,
        policy=None,
    ):
        """Find time windows where the caller-supplied predicate is satisfied."""
        facade = _facade_module()
        return facade.find_electional_windows(
            jd_start=facade.jd_from_datetime(dt_start),
            jd_end=facade.jd_from_datetime(dt_end),
            latitude=latitude,
            longitude=longitude,
            predicate=predicate,
            policy=policy,
            reader=self._reader,
        )

    def __repr__(self) -> str:
        facade = _facade_module()
        if self._reader_obj is not None:
            kernel_name = self._reader_obj.path.name
        else:
            kernel_name = "unavailable"
        return f"Moira(kernel='{kernel_name}', v{facade.__version__})"

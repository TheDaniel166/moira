"""
Internal special-topic mixin for the public Moira facade.

This is the final compatibility wrapper layer for the legacy ``Moira`` facade:
eclipses, primary directions, longevity, phenomena, occultations, Sothic and
Egyptian calendar helpers, variable and multiple stars, void-of-course Moon,
electional windows, bounded Western electional doctrine, and representation.
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
    electional windows, Western electional profiles, and representation.

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
          void-of-course, electional search, Western electional, and repr calls to their
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
        "api": {"frozen": ["eclipse", "solar_eclipse_footprint", "lunar_eclipse_visibility_map", "speculum", "primary_directions", "primary_directions_policy_preset", "primary_direction_relations", "primary_direction_condition", "primary_directions_profile", "primary_directions_network", "longevity", "phenomena", "occultations", "lunar_occultation_path_topology", "lunar_occultation_path_topology_at", "lunar_star_occultation_path_topology", "lunar_star_occultation_path_topology_at", "void_of_course", "electional", "moon_connection_flow_at", "ramesey_moon_condition_at", "sahl_moon_condition_at", "sahl_matter_profile_at", "lilly_perfection_at", "dorotheus_moon_condition_at", "dorotheus_rooted_context_at", "dorotheus_construction_at", "dorotheus_matter_profile_at", "western_electional_profile_windows"], "internal": []},
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

    def solar_eclipse_footprint(
        self,
        jd_start: float,
        *,
        kind: str = "any",
        backward: bool = False,
        sample_count: int = 181,
    ):
        """Return the complete mean-limb solar-eclipse visibility footprint."""
        facade = _facade_module()
        return facade.EclipseCalculator(reader=self._reader).solar_eclipse_footprint(
            jd_start,
            kind=kind,
            backward=backward,
            sample_count=sample_count,
        )

    def lunar_eclipse_visibility_map(
        self,
        jd_start: float,
        *,
        kind: str = "any",
        backward: bool = False,
        mode: str = "native",
        sample_count: int = 181,
    ):
        """Return global contact-horizon limits for one lunar eclipse."""
        facade = _facade_module()
        return facade.EclipseCalculator(reader=self._reader).lunar_eclipse_visibility_map(
            jd_start,
            kind=kind,
            backward=backward,
            mode=mode,
            sample_count=sample_count,
        )

    def eclipse_hits_in_range(
        self,
        jd_start: float,
        jd_end: float,
        natal_positions: dict,
        orb: float = 1.0,
    ):
        """Return eclipses in [jd_start, jd_end] that hit natal positions within *orb* degrees."""
        facade = _facade_module()
        return facade.EclipseCalculator(reader=self._reader).eclipse_hits_in_range(
            jd_start, jd_end, natal_positions, orb=orb
        )

    def speculum(
        self,
        chart,
        houses,
        geo_lat: float,
        *,
        obliquity: float | None = None,
        bodies: list[str] | None = None,
    ):
        """Compute the Placidus mundane speculum for a natal chart."""
        return _facade_module().speculum(
            chart,
            houses,
            geo_lat,
            obliquity=obliquity,
            bodies=bodies,
        )

    def primary_directions(
        self,
        chart,
        houses,
        geo_lat: float,
        max_arc: float = 90.0,
        include_converse: bool = True,
        significators: list[str] | None = None,
        promissors: list[str] | None = None,
        *,
        solar_speed: float | None = None,
        obliquity: float | None = None,
        policy=None,
    ):
        """Find primary-direction arcs under an explicit optional policy."""
        return _facade_module().find_primary_arcs(
            chart,
            houses,
            geo_lat,
            max_arc=max_arc,
            include_converse=include_converse,
            significators=significators,
            promissors=promissors,
            solar_speed=solar_speed,
            obliquity=obliquity,
            policy=policy,
        )

    def primary_directions_policy_preset(self, preset, **kwargs):
        """Build one canonical primary-directions policy preset."""
        return _facade_module().primary_directions_policy_preset(preset, **kwargs)

    def primary_direction_relations(self, arc, *, policy=None):
        """Evaluate the admitted relation profile for one primary arc."""
        return _facade_module().evaluate_primary_direction_relations(arc, policy=policy)

    def primary_direction_condition(self, arcs, *, policy=None):
        """Evaluate one significator's directed condition profile."""
        return _facade_module().evaluate_primary_direction_condition(arcs, policy=policy)

    def primary_directions_profile(self, arcs, *, policy=None):
        """Evaluate an aggregate primary-directions profile."""
        return _facade_module().evaluate_primary_directions_aggregate(arcs, policy=policy)

    def primary_directions_network(self, arcs, *, policy=None):
        """Evaluate the directed promissor-to-significator network."""
        return _facade_module().evaluate_primary_directions_network(arcs, policy=policy)

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

    def planetary_node(self, planet: str, dt: datetime):
        """Return the heliocentric orbital node and apsides for one planet."""
        facade = _facade_module()
        return facade.planetary_node(planet, facade.jd_from_datetime(dt))

    def patterns(
        self,
        chart,
        orb_factor: float = 1.0,
        dominant_only: bool = False,
    ):
        """Find chart aspect patterns, optionally retaining only maximal structures."""
        facade = _facade_module()
        positions = chart.longitudes()
        asps = facade.find_aspects(
            positions,
            speeds=chart.speeds(),
            orb_factor=orb_factor,
        )
        return facade.find_all_patterns(
            positions,
            aspects=asps,
            orb_factor=orb_factor,
            dominant_only=dominant_only,
        )

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

    def visibility_tonight(self, body: str, jd_ut: float, lat: float, lon: float, *, policy=None):
        """Return the practitioner-facing visibility assessment alias for one epoch."""
        return _facade_module().visibility_tonight(
            body, jd_ut, lat, lon, policy=policy
        )

    def is_visible_tonight(self, body: str, jd_ut: float, lat: float, lon: float, *, policy=None) -> bool:
        """Return only the boolean visibility verdict for one epoch."""
        return _facade_module().is_visible_tonight(
            body, jd_ut, lat, lon, policy=policy
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

    def proximity_events(
        self, body1: str, body2: str, jd_start: float, jd_end: float, threshold_deg: float
    ):
        """Find all threshold-crossing events between two bodies in a range."""
        return _facade_module().proximity_events_in_range(
            body1, body2, jd_start, jd_end, threshold_deg=threshold_deg, reader=self._reader
        )

    def solar_condition_events(
        self, body: str, jd_start: float, jd_end: float, condition: str = "cazimi"
    ):
        """Find solar condition events (cazimi, combust, etc.) for a body."""
        return _facade_module().solar_condition_events_in_range(
            body, jd_start, jd_end, condition=condition, reader=self._reader
        )

    def solar_condition_at(self, body: str, jd_ut: float):
        """Return the solar proximity condition for *body* at *jd_ut*.

        Returns a SolarConditionTruth with ``present``, ``condition``
        (``"cazimi"`` / ``"combust"`` / ``"under_sunbeams"`` / ``None``),
        ``label``, ``score``, and ``distance_from_sun``.
        """
        return _facade_module().solar_condition_at(body, jd_ut, reader=self._reader)

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

    def lunar_occultation_path_topology(
        self,
        target: str,
        jd_start: float,
        jd_end: float,
        step_days: float = 0.25,
        sample_count: int = 65,
        observer_elev_m: float = 0.0,
    ):
        """Return detailed, polar-safe path topology for planetary events."""

        return _facade_module().lunar_occultation_path_topology(
            target,
            jd_start,
            jd_end,
            step_days=step_days,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            reader=self._reader,
        )

    def lunar_occultation_path_topology_at(
        self,
        target: str,
        jd_mid: float,
        *,
        sample_count: int = 65,
        observer_elev_m: float = 0.0,
    ):
        """Return detailed planetary path topology at one greatest epoch."""

        return _facade_module().lunar_occultation_path_topology_at(
            target,
            jd_mid,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            reader=self._reader,
        )

    def lunar_star_occultation_path_topology(
        self,
        star_lon: float,
        star_lat: float,
        star_name: str,
        jd_start: float,
        jd_end: float,
        step_days: float = 0.25,
        sample_count: int = 65,
        observer_elev_m: float = 0.0,
    ):
        """Return detailed, polar-safe path topology for stellar events."""

        return _facade_module().lunar_star_occultation_path_topology(
            star_lon,
            star_lat,
            star_name,
            jd_start,
            jd_end,
            step_days=step_days,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            reader=self._reader,
        )

    def lunar_star_occultation_path_topology_at(
        self,
        star_lon: float,
        star_lat: float,
        star_name: str,
        jd_mid: float,
        *,
        sample_count: int = 65,
        observer_elev_m: float = 0.0,
    ):
        """Return detailed stellar path topology at one greatest epoch."""

        return _facade_module().lunar_star_occultation_path_topology_at(
            star_lon,
            star_lat,
            star_name,
            jd_mid,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            reader=self._reader,
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
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.void_of_course_window(
            jd_ut1, reader=self._reader, modern=modern
        )

    def is_moon_void_of_course(self, dt: datetime, modern: bool = False) -> bool:
        """Return True if the Moon is void of course at dt."""
        facade = _facade_module()
        jd_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt))
        return facade.is_void_of_course(
            jd_ut1, reader=self._reader, modern=modern
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
        jd_start_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt_start))
        jd_end_ut1 = facade.utc_to_ut1(facade.jd_from_datetime(dt_end))
        return facade.find_electional_windows(
            jd_start=jd_start_ut1,
            jd_end=jd_end_ut1,
            latitude=latitude,
            longitude=longitude,
            predicate=predicate,
            policy=policy,
            reader=self._reader,
        )

    def ramesey_moon_condition_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        unavoidable_time_urgency: bool | None = None,
        house_policy=None,
        policy=None,
    ):
        """Evaluate Ramesey's bounded Moon-condition profile at one instant."""
        facade = _facade_module()
        resolved_policy = (
            facade.RAMESEY_MOON_CONDITION_V1 if policy is None else policy
        )
        return facade.ramesey_moon_condition_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            reader=self._reader,
            house_policy=house_policy,
            policy=resolved_policy,
        )

    def lunar_ecliptic_direction_at(self, jd_ut: float, *, policy=None):
        """Return the neutral lunar latitude-direction and node-crossing witness."""

        facade = _facade_module()
        resolved_policy = (
            facade.LUNAR_ECLIPTIC_DIRECTION_V1 if policy is None else policy
        )
        return facade.lunar_ecliptic_direction_at(
            jd_ut,
            reader=self._reader,
            policy=resolved_policy,
        )

    def sahl_moon_condition_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        burnt_path_variant,
        eighth_rule_variant=None,
        house_policy=None,
        policy=None,
    ):
        """Evaluate Sahl's bounded Moon-condition profile at one instant."""
        facade = _facade_module()
        resolved_policy = facade.SAHL_MOON_CONDITION_V1 if policy is None else policy
        return facade.sahl_moon_condition_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            burnt_path_variant=burnt_path_variant,
            eighth_rule_variant=eighth_rule_variant,
            reader=self._reader,
            house_policy=house_policy,
            policy=resolved_policy,
        )

    def sahl_matter_profile_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        profile_id,
        burnt_path_variant,
        eighth_rule_variant=None,
        house_policy=None,
        policy=None,
        moon_policy=None,
    ):
        """Evaluate one named source-bounded Sahl matter profile at one instant."""

        facade = _facade_module()
        return facade.sahl_matter_profile_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            profile_id=profile_id,
            burnt_path_variant=burnt_path_variant,
            eighth_rule_variant=eighth_rule_variant,
            reader=self._reader,
            house_policy=house_policy,
            policy=policy,
            moon_policy=moon_policy,
        )

    def lilly_perfection_at(
        self,
        jd_start: float,
        jd_end: float,
        significator_a: str,
        significator_b: str,
        *,
        is_day_chart: bool,
        policy=None,
    ):
        """Return a bounded Lilly 1647 perfection trace for two significators."""

        facade = _facade_module()
        resolved_policy = facade.LILLY_1647_PERFECTION_V1 if policy is None else policy
        return facade.lilly_perfection_at(
            jd_start,
            jd_end,
            significator_a,
            significator_b,
            is_day_chart=is_day_chart,
            reader=self._reader,
            policy=resolved_policy,
        )

    def western_electional_judgement_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        matter_profile_id,
        perfection_significator_a: str,
        perfection_significator_b: str,
        perfection_interval_days: float,
        election_class=None,
        natal_jd_ut: float | None = None,
        natal_latitude: float | None = None,
        natal_longitude: float | None = None,
        natal_house_system: str | None = None,
        unavoidable_time_urgency: bool | None = None,
        moon_flow_policy=None,
        dorotheus_sign_nature_variant=None,
        sahl_burnt_path_variant=None,
        sahl_eighth_rule_variant=None,
        house_policy=None,
        policy=None,
    ):
        """Compose one admitted matter profile and Lilly perfection trace."""

        facade = _facade_module()
        resolved_class = (
            facade.WesternElectionClass.EPHEMERAL
            if election_class is None
            else election_class
        )
        resolved_policy = (
            facade.WESTERN_ELECTIONAL_JUDGEMENT_V1
            if policy is None
            else policy
        )
        return facade.western_electional_judgement_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            matter_profile_id=matter_profile_id,
            perfection_significator_a=perfection_significator_a,
            perfection_significator_b=perfection_significator_b,
            perfection_interval_days=perfection_interval_days,
            election_class=resolved_class,
            natal_jd_ut=natal_jd_ut,
            natal_latitude=natal_latitude,
            natal_longitude=natal_longitude,
            natal_house_system=natal_house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            moon_flow_policy=moon_flow_policy,
            dorotheus_sign_nature_variant=dorotheus_sign_nature_variant,
            sahl_burnt_path_variant=sahl_burnt_path_variant,
            sahl_eighth_rule_variant=sahl_eighth_rule_variant,
            reader=self._reader,
            house_policy=house_policy,
            policy=resolved_policy,
        )

    def western_electional_ranking_at(
        self,
        candidate_jds,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        matter_profile_id,
        perfection_significator_a: str,
        perfection_significator_b: str,
        perfection_interval_days: float,
        weights,
        election_class=None,
        natal_jd_ut: float | None = None,
        natal_latitude: float | None = None,
        natal_longitude: float | None = None,
        natal_house_system: str | None = None,
        unavoidable_time_urgency: bool | None = None,
        moon_flow_policy=None,
        dorotheus_sign_nature_variant=None,
        sahl_burnt_path_variant=None,
        sahl_eighth_rule_variant=None,
        house_policy=None,
        judgement_policy=None,
        ranking_policy=None,
    ):
        """Rank explicit candidate instants under one complete judgement selection."""

        facade = _facade_module()
        resolved_class = (
            facade.WesternElectionClass.EPHEMERAL
            if election_class is None
            else election_class
        )
        resolved_judgement_policy = (
            facade.WESTERN_ELECTIONAL_JUDGEMENT_V1
            if judgement_policy is None
            else judgement_policy
        )
        resolved_ranking_policy = (
            facade.WESTERN_ELECTIONAL_RANKING_V1
            if ranking_policy is None
            else ranking_policy
        )
        return facade.western_electional_ranking_at(
            candidate_jds,
            latitude,
            longitude,
            house_system=house_system,
            matter_profile_id=matter_profile_id,
            perfection_significator_a=perfection_significator_a,
            perfection_significator_b=perfection_significator_b,
            perfection_interval_days=perfection_interval_days,
            weights=weights,
            election_class=resolved_class,
            natal_jd_ut=natal_jd_ut,
            natal_latitude=natal_latitude,
            natal_longitude=natal_longitude,
            natal_house_system=natal_house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            moon_flow_policy=moon_flow_policy,
            dorotheus_sign_nature_variant=dorotheus_sign_nature_variant,
            sahl_burnt_path_variant=sahl_burnt_path_variant,
            sahl_eighth_rule_variant=sahl_eighth_rule_variant,
            reader=self._reader,
            house_policy=house_policy,
            judgement_policy=resolved_judgement_policy,
            ranking_policy=resolved_ranking_policy,
        )

    def western_electional_judgement_windows(
        self,
        jd_start: float,
        jd_end: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        matter_profile_id,
        perfection_significator_a: str,
        perfection_significator_b: str,
        perfection_interval_days: float,
        election_class=None,
        natal_jd_ut: float | None = None,
        natal_latitude: float | None = None,
        natal_longitude: float | None = None,
        natal_house_system: str | None = None,
        unavoidable_time_urgency: bool | None = None,
        moon_flow_policy=None,
        dorotheus_sign_nature_variant=None,
        sahl_burnt_path_variant=None,
        sahl_eighth_rule_variant=None,
        house_policy=None,
        judgement_policy=None,
        scan_policy=None,
    ):
        """Return bounded observed complete-judgement windows."""

        facade = _facade_module()
        resolved_class = (
            facade.WesternElectionClass.EPHEMERAL
            if election_class is None
            else election_class
        )
        resolved_judgement_policy = (
            facade.WESTERN_ELECTIONAL_JUDGEMENT_V1
            if judgement_policy is None
            else judgement_policy
        )
        resolved_scan_policy = (
            facade.WESTERN_ELECTIONAL_JUDGEMENT_WINDOWS_V1
            if scan_policy is None
            else scan_policy
        )
        return facade.scan_western_electional_judgement_windows(
            jd_start,
            jd_end,
            latitude,
            longitude,
            house_system=house_system,
            matter_profile_id=matter_profile_id,
            perfection_significator_a=perfection_significator_a,
            perfection_significator_b=perfection_significator_b,
            perfection_interval_days=perfection_interval_days,
            election_class=resolved_class,
            natal_jd_ut=natal_jd_ut,
            natal_latitude=natal_latitude,
            natal_longitude=natal_longitude,
            natal_house_system=natal_house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            moon_flow_policy=moon_flow_policy,
            dorotheus_sign_nature_variant=dorotheus_sign_nature_variant,
            sahl_burnt_path_variant=sahl_burnt_path_variant,
            sahl_eighth_rule_variant=sahl_eighth_rule_variant,
            reader=self._reader,
            house_policy=house_policy,
            judgement_policy=resolved_judgement_policy,
            scan_policy=resolved_scan_policy,
        )

    def dorotheus_moon_condition_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        unavoidable_time_urgency: bool | None = None,
        house_policy=None,
        policy=None,
    ):
        """Evaluate Dorotheus's bounded Book V.6 profile at one instant."""
        facade = _facade_module()
        resolved_policy = (
            facade.DOROTHEUS_MOON_CONDITION_V1 if policy is None else policy
        )
        return facade.dorotheus_moon_condition_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            reader=self._reader,
            house_policy=house_policy,
            policy=resolved_policy,
        )

    def dorotheus_rooted_context_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        matter,
        election_class=None,
        natal_jd_ut: float | None = None,
        natal_latitude: float | None = None,
        natal_longitude: float | None = None,
        natal_house_system: str | None = None,
        house_policy=None,
        policy=None,
    ):
        """Evaluate Dorotheus's rooted V.6/V.31 context at one instant."""

        facade = _facade_module()
        resolved_class = (
            facade.WesternElectionClass.EPHEMERAL
            if election_class is None
            else election_class
        )
        resolved_policy = (
            facade.DOROTHEUS_ROOTED_CONTEXT_V1 if policy is None else policy
        )
        return facade.dorotheus_rooted_context_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            matter=matter,
            election_class=resolved_class,
            natal_jd_ut=natal_jd_ut,
            natal_latitude=natal_latitude,
            natal_longitude=natal_longitude,
            natal_house_system=natal_house_system,
            reader=self._reader,
            house_policy=house_policy,
            policy=resolved_policy,
        )

    def dorotheus_construction_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        election_class=None,
        natal_jd_ut: float | None = None,
        natal_latitude: float | None = None,
        natal_longitude: float | None = None,
        natal_house_system: str | None = None,
        unavoidable_time_urgency: bool | None = None,
        house_policy=None,
        policy=None,
    ):
        """Evaluate the complete source-layered Dorotheus V.7 profile."""

        facade = _facade_module()
        resolved_class = (
            facade.WesternElectionClass.EPHEMERAL
            if election_class is None
            else election_class
        )
        resolved_policy = (
            facade.DOROTHEUS_CONSTRUCTION_V1 if policy is None else policy
        )
        return facade.dorotheus_construction_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            election_class=resolved_class,
            natal_jd_ut=natal_jd_ut,
            natal_latitude=natal_latitude,
            natal_longitude=natal_longitude,
            natal_house_system=natal_house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            reader=self._reader,
            house_policy=house_policy,
            policy=resolved_policy,
        )

    def dorotheus_matter_profile_at(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        profile_id,
        election_class=None,
        natal_jd_ut: float | None = None,
        natal_latitude: float | None = None,
        natal_longitude: float | None = None,
        natal_house_system: str | None = None,
        unavoidable_time_urgency: bool | None = None,
        house_policy=None,
        policy=None,
        moon_flow_policy=None,
        sign_nature_variant=None,
    ):
        """Evaluate one admitted named Dorothean Book V matter profile."""

        facade = _facade_module()
        resolved_class = (
            facade.WesternElectionClass.EPHEMERAL
            if election_class is None
            else election_class
        )
        return facade.dorotheus_matter_profile_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            profile_id=profile_id,
            election_class=resolved_class,
            natal_jd_ut=natal_jd_ut,
            natal_latitude=natal_latitude,
            natal_longitude=natal_longitude,
            natal_house_system=natal_house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            reader=self._reader,
            house_policy=house_policy,
            policy=policy,
            moon_flow_policy=moon_flow_policy,
            sign_nature_variant=sign_nature_variant,
        )

    def moon_connection_flow_at(self, jd_ut: float, *, policy):
        """Return a neutral exact lunar separation/connection flow."""

        facade = _facade_module()
        return facade.moon_connection_flow_at(
            jd_ut,
            policy=policy,
            reader=self._reader,
        )

    def western_electional_profile_windows(
        self,
        jd_start: float,
        jd_end: float,
        latitude: float,
        longitude: float,
        *,
        house_system: str,
        profile_id,
        scan_policy,
        unavoidable_time_urgency: bool | None = None,
        sahl_burnt_path_variant=None,
        sahl_eighth_rule_variant=None,
        house_policy=None,
    ):
        """Scan one admitted Western Moon profile by exact summary status."""

        facade = _facade_module()
        return facade.scan_western_electional_profile(
            jd_start,
            jd_end,
            latitude,
            longitude,
            house_system=house_system,
            profile_id=profile_id,
            scan_policy=scan_policy,
            unavoidable_time_urgency=unavoidable_time_urgency,
            sahl_burnt_path_variant=sahl_burnt_path_variant,
            sahl_eighth_rule_variant=sahl_eighth_rule_variant,
            reader=self._reader,
            house_policy=house_policy,
        )

    def __repr__(self) -> str:
        facade = _facade_module()
        if self._reader_obj is not None:
            kernel_name = self._reader_obj.path.name
        else:
            kernel_name = "unavailable"
        return f"Moira(kernel='{kernel_name}', v{facade.__version__})"

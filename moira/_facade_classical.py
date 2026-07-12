"""
Internal classical-method mixin for the public Moira facade.

These are compatibility wrappers for classical and Hermetic astrology surfaces. The
underlying computations remain owned by their domain modules.
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from typing import Any

_nine_parts = importlib.import_module("moira.nine_parts")


def _facade_module() -> Any:
    """Return the loaded public facade module for compatibility globals."""

    return sys.modules[f"{__package__}.facade"]


class ClassicalFacadeMixin:
    """RITE: The Tradition-Keeper — the layer that routes the public Moira
    surface to classical and Hermetic astrological techniques: Hermetic Lots,
    essential dignities, Church of Light Astrodynes, midpoints, harmonics,
    profections, and time-lord systems.

THEOREM: Mixin that provides classical astrological technique wrappers
         for the public ``moira.facade.Moira`` class, delegating each
         computation to the authoritative owning module.

RITE OF PURPOSE:
    ClassicalFacadeMixin extracts all classical-technique-facing public
    methods from the monolithic facade.py into a coherent composable
    unit, preserving the legacy Moira surface while routing to the
    correct engine module without duplicating logic.

LAW OF OPERATION:
    Responsibilities:
        - Delegate lots, dignities, Astrodynes, midpoints, harmonics, profections,
          and time-lord computations to their owning modules.
    Non-responsibilities:
        - Does not implement any astrological calculation itself.
        - Does not own kernel lifecycle or reader management.
    Dependencies:
        - moira.facade (resolved at runtime via sys.modules)
    Structural invariants:
        - All methods delegate to facade-module callables.

Canon: Moira Sovereign Facade Architecture; Hellenistic and medieval
       classical technique modules.

[MACHINE_CONTRACT v1]
{
    "scope": "class",
    "id": "moira._facade_classical.ClassicalFacadeMixin",
    "risk": "medium",
    "api": {"frozen": ["lots", "dignities", "mutual_receptions", "astrodynes", "astrodynes_from_geometry", "normal_progressed_astrodynes", "practical_progressed_astrodynes", "progressed_astrodynes_geometry", "progressed_astrodynes_chart", "progressed_astrodyne_dated_aspect", "progressed_astrodyne_major_relation", "progressed_astrodyne_accessory_relation", "progressed_astrodyne_reenforcement", "progressed_astrodyne_total_influence", "progressed_astrodyne_compound_total_influence", "midpoints", "midpoints_to_point", "harmonic", "profection", "firdaria", "decennials", "current_decennials", "zodiacal_releasing", "vimshottari_dasha", "almuten_of_degree", "almuten_figuris", "huber_house_zones", "huber_age_point", "huber_age_point_contacts", "huber_dynamic_intensity", "huber_intensity_at", "huber_chart_intensity_profile", "nine_parts"], "internal": []},
    "state": {"mutable": false, "owners": []},
    "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
    "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
    "failures": {"policy": "propagate"},
    "succession": {"stance": "mixin", "override_points": []},
    "agent": {"autofix": "disallowed", "requires_human_for": ["api_change"]}
}
[/MACHINE_CONTRACT]
    """

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

    def astrodynes(
        self,
        body_inputs,
        cusp_signs,
        *,
        intercepted_signs_by_house=None,
        policy=None,
    ):
        """Compute the kernel-free Church of Light natal Astrodyne result."""

        return _facade_module().natal_astrodynes(
            body_inputs,
            cusp_signs,
            intercepted_signs_by_house=intercepted_signs_by_house,
            policy=policy,
        )

    def astrodynes_from_geometry(
        self,
        planet_longitudes,
        declinations,
        cusp_longitudes,
        mc_longitude,
        asc_longitude,
        *,
        policy=None,
    ):
        """Compute Church of Light natal Astrodynes from explicit geometry."""

        return _facade_module().natal_astrodynes_from_geometry(
            planet_longitudes,
            declinations,
            cusp_longitudes,
            mc_longitude,
            asc_longitude,
            policy=policy,
        )

    def normal_progressed_astrodynes(
        self,
        birth_body_values,
        birth_sign_values,
        birth_house_values,
        placements,
        *,
        policy=None,
    ):
        """Build the Church of Light normal progressed horoscope."""

        return _facade_module().normal_progressed_horoscope(
            birth_body_values,
            birth_sign_values,
            birth_house_values,
            placements,
            policy=policy,
        )

    def practical_progressed_astrodynes(
        self,
        normal,
        aspects,
        terminal_locations,
        house_cusp_signs,
        intercepted_signs=None,
        mutual_receptions=(),
    ):
        """Distribute dated progressed influence through signs and houses."""

        return _facade_module().practical_progressed_horoscope(
            normal,
            aspects,
            terminal_locations,
            house_cusp_signs,
            intercepted_signs,
            mutual_receptions,
        )

    def progressed_astrodynes_geometry(
        self,
        natal_dt,
        target_dt,
        observer_lat,
        observer_lon,
        **kwargs,
    ):
        """Build chart-backed Church of Light progression terminal geometry."""

        return _facade_module().church_of_light_progression_geometry(
            natal_dt,
            target_dt,
            observer_lat,
            observer_lon,
            reader=self._reader,
            **kwargs,
        )

    def progressed_astrodynes_chart(
        self,
        natal_dt,
        target_dt,
        observer_lat,
        observer_lon,
        **kwargs,
    ):
        """Compute the full chart-backed Church of Light Astrodyne product."""

        return _facade_module().church_of_light_progressed_astrodynes_chart(
            natal_dt,
            target_dt,
            observer_lat,
            observer_lon,
            reader=self._reader,
            **kwargs,
        )

    def search_progressed_astrodyne_contacts(
        self,
        natal_dt,
        start_dt,
        end_dt,
        observer_lat,
        observer_lon,
        query,
        **kwargs,
    ):
        """Search a bounded Church of Light one-degree contact chronology."""

        return _facade_module().search_progressed_contacts(
            natal_dt,
            start_dt,
            end_dt,
            observer_lat,
            observer_lon,
            query,
            reader=self._reader,
            **kwargs,
        )

    def integrate_progressed_astrodyne_influence(
        self,
        natal_dt,
        start_dt,
        end_dt,
        observer_lat,
        observer_lon,
        query,
        **kwargs,
    ):
        """Integrate the source curve over actual ephemeris-varying motion."""

        return _facade_module().integrate_progressed_influence(
            natal_dt,
            start_dt,
            end_dt,
            observer_lat,
            observer_lon,
            query,
            reader=self._reader,
            **kwargs,
        )

    def progressed_astrodyne_dated_aspect(self, *args, **kwargs):
        """Evaluate one progressed aspect from peak power and dated distance."""

        return _facade_module().progressed_dated_aspect(*args, **kwargs)

    def progressed_astrodyne_major_relation(self, *args, **kwargs):
        """Evaluate one explicit major-progressed terminal relation."""

        return _facade_module().evaluate_major_progressed_relation(*args, **kwargs)

    def progressed_astrodyne_accessory_relation(self, *args, **kwargs):
        """Evaluate one independent minor or transit relation."""

        return _facade_module().evaluate_accessory_progressed_relation(
            *args, **kwargs
        )

    def progressed_astrodyne_reenforcement(self, *args, **kwargs):
        """Apply a minor progressed power-only reenforcement."""

        return _facade_module().reenforce_major_progressed_relation(
            *args, **kwargs
        )

    def progressed_astrodyne_total_influence(self, *args, **kwargs):
        """Compute constant-rate total progressed influence."""

        return _facade_module().progressed_total_influence(*args, **kwargs)

    def progressed_astrodyne_compound_total_influence(self, *args, **kwargs):
        """Compute the manual's compound year/month/day influence product."""

        return _facade_module().progressed_compound_total_influence(
            *args, **kwargs
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

    def decennials(self, natal_dt: datetime, natal_chart, natal_houses=None, *, policy=None):
        """Compute the Decennials sequence from birth."""
        facade = _facade_module()
        sun = natal_chart.planets.get("Sun")
        asc = natal_houses.asc if natal_houses is not None else 0.0
        day = facade.is_day_chart(sun.longitude if sun else 0.0, asc)
        longitudes = natal_chart.longitudes(include_nodes=False)
        positions = {
            planet: longitudes[planet]
            for planet in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
        }
        return facade.decennials(
            facade.jd_from_datetime(natal_dt),
            positions,
            day,
            policy=policy,
        )

    def current_decennials(self, natal_dt: datetime, current_dt: datetime, natal_chart, natal_houses=None, *, policy=None):
        """Compute the active Decennials major and sub-period at a target date."""
        facade = _facade_module()
        sun = natal_chart.planets.get("Sun")
        asc = natal_houses.asc if natal_houses is not None else 0.0
        day = facade.is_day_chart(sun.longitude if sun else 0.0, asc)
        longitudes = natal_chart.longitudes(include_nodes=False)
        positions = {
            planet: longitudes[planet]
            for planet in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
        }
        return facade.current_decennials(
            facade.jd_from_datetime(natal_dt),
            positions,
            day,
            facade.jd_from_datetime(current_dt),
            policy=policy,
        )

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

    def almuten_of_degree(self, longitude: float, is_day: bool) -> str:
        """Compute the essential almuten of a zodiacal degree."""
        return _facade_module().almuten_of_degree(longitude, is_day)

    def almuten_figuris(
        self,
        chart,
        houses,
        prenatal_syzygy_lon: float | None = None,
        day_ruler: str | None = None,
        hour_ruler: str | None = None,
        strict: bool = False,
    ) -> str:
        """
        Compute the traditional Almuten Figuris for a natal chart.
        If prenatal_syzygy_lon, day_ruler, or hour_ruler are not passed,
        they are resolved automatically from the chart and house coordinates.
        If strict is True, any auto-resolution errors will bubble up.
        """
        facade = _facade_module()
        lons = chart.longitudes(include_nodes=False)
        day = facade.is_day_chart(lons.get("Sun", 0.0), houses.asc)

        # 1. Resolve prenatal syzygy degree if not provided
        if prenatal_syzygy_lon is None:
            try:
                from .transits import prenatal_syzygy
                from .planets import planet_at
                reader = getattr(chart, "_reader", None)
                jd_syzygy, phase = prenatal_syzygy(chart.jd_ut, reader=reader)
                if phase == "New Moon":
                    prenatal_syzygy_lon = planet_at("Sun", jd_syzygy, reader=reader).longitude
                else:
                    prenatal_syzygy_lon = planet_at("Moon", jd_syzygy, reader=reader).longitude
            except Exception as e:
                if strict:
                    raise e

        # 2. Resolve day and hour rulers if not provided
        if day_ruler is None or hour_ruler is None:
            lat = getattr(houses, "geo_lat", getattr(chart, "latitude", None))
            lon = getattr(houses, "geo_lon", getattr(chart, "longitude", None))
            reader = getattr(chart, "_reader", None)
            if lat is not None and lon is not None:
                try:
                    from .planetary_hours import planetary_hours
                    ph_day = planetary_hours(chart.jd_ut, lat, lon, reader=reader)
                    found_hour = None
                    for h in ph_day.day_hours:
                        if h.start_jd <= chart.jd_ut <= h.end_jd:
                            found_hour = h
                            break
                    if found_hour is None:
                        for h in ph_day.night_hours:
                            if h.start_jd <= chart.jd_ut <= h.end_jd:
                                found_hour = h
                                break
                    if found_hour is not None:
                        hour_ruler = found_hour.ruler
                    if ph_day.day_hours:
                        day_ruler = ph_day.day_hours[0].ruler
                except Exception as e:
                    if strict:
                        raise e

        return facade.almuten_figuris(
            lons,
            houses.cusps,
            day,
            prenatal_syzygy_lon=prenatal_syzygy_lon,
            day_ruler=day_ruler,
            hour_ruler=hour_ruler,
        )

    def huber_house_zones(self, house_cusps):
        """Compute Huber golden-section zone boundaries for a house frame."""
        return _facade_module().house_zones(house_cusps)

    def huber_age_point(self, age_years: float, house_cusps):
        """Compute the Huber Age Point for a caller-supplied house frame."""
        return _facade_module().age_point(age_years, house_cusps)

    def huber_age_point_contacts(
        self,
        house_cusps,
        planet_longitudes: dict[str, float],
        orb: float = 2.0,
        start_age: float = 0.0,
        end_age: float = 72.0,
        step_years: float = 1.0 / 12.0,
    ):
        """Scan bounded Huber Age Point contacts against named chart points."""
        return _facade_module().age_point_contacts(
            house_cusps,
            planet_longitudes,
            orb=orb,
            start_age=start_age,
            end_age=end_age,
            step_years=step_years,
        )

    def huber_dynamic_intensity(self, house: int, fraction: float):
        """Evaluate the Huber Dynamic Intensity Curve by house fraction."""
        return _facade_module().dynamic_intensity(house, fraction)

    def huber_intensity_at(self, longitude: float, house_cusps):
        """Evaluate Huber dynamic intensity at an ecliptic longitude."""
        return _facade_module().intensity_at(longitude, house_cusps)

    def huber_chart_intensity_profile(
        self,
        points: dict[str, float],
        house_cusps,
    ):
        """Score named chart points against the Huber Dynamic Intensity Curve."""
        return _facade_module().chart_intensity_profile(points, house_cusps)

    def nine_parts(
        self,
        asc: float,
        planets: dict[str, float],
        is_night_chart: bool,
        policy=None,
    ):
        """Compute Abu Ma'shar's Nine Parts from caller-supplied chart truth."""
        if policy is None:
            policy = _nine_parts.DEFAULT_NINE_PARTS_POLICY
        return _nine_parts.nine_parts_abu_mashar(
            asc,
            planets,
            is_night_chart,
            policy=policy,
        )

"""
moira.essentials — Beginner-friendly Moira surface.

This is the simplest entry point for new users.  It exposes just enough
to cast a natal chart, inspect planetary positions, compute houses and
aspects, and handle basic time conversions.

Usage
-----
    from moira.essentials import Moira, Chart, Body, HouseSystem

    m = Moira()
    chart = m.chart(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))
    for body, data in chart.planets.items():
        print(body, data.longitude)

    houses = m.houses(chart.jd, latitude=51.5, longitude=-0.1)
    print(houses.asc, houses.mc)

    aspects = m.aspects(chart)
    for a in aspects:
        print(a)

Next step
---------
When you're ready for dignities, lots, fixed stars, profections, and
classical time-lord systems, move to ``moira.classical``.

When you need transits, progressions, synastry, eclipses, and returns,
move to ``moira.predictive``.

For the complete surface (heliacal visibility, parans, astrocartography,
galactic coordinates, uranian points, occultations, variable stars, and
every other subsystem), import from ``moira.facade``.
"""

# ── Core facade ──────────────────────────────────────────────────────────
from .facade import Moira, Chart, MissingEphemerisKernelError

# ── Identity enums ───────────────────────────────────────────────────────
from .constants import Body, HouseSystem

# ── Result vessels ───────────────────────────────────────────────────────
from .planets import PlanetData, SkyPosition, CartesianPosition
from .nodes import NodeData
from .houses import HouseCusps
from .aspects import AspectData

# ── Time ─────────────────────────────────────────────────────────────────
from .julian import (
    CalendarDateTime,
    DeltaTPolicy,
    julian_day,
    calendar_from_jd,
    calendar_datetime_from_jd,
    jd_from_datetime,
    datetime_from_jd,
    format_jd_utc,
    safe_datetime_from_jd,
    delta_t,
)
from .delta_t_physical import DeltaTBreakdown, delta_t_breakdown

# ── Houses (basic) ───────────────────────────────────────────────────────
from .houses import calculate_houses, assign_house

# ── Aspects (basic) ──────────────────────────────────────────────────────
from .aspects import find_aspects, AspectPolicy, DEFAULT_POLICY

# ── Sidereal (basic) ────────────────────────────────────────────────────
from .sidereal import (
    Ayanamsa,
    ayanamsa,
    tropical_to_sidereal,
    sidereal_to_tropical,
    list_ayanamsa_systems,
)

# ── Decanates ────────────────────────────────────────────────────────────
from .decanates import DecanatePosition, chaldean_face, triplicity_decan, vedic_drekkana


__all__ = [
    # Core
    "Moira", "Chart", "MissingEphemerisKernelError",
    # Identity
    "Body", "HouseSystem",
    # Result vessels
    "PlanetData", "SkyPosition", "CartesianPosition",
    "NodeData", "HouseCusps", "AspectData",
    # Time
    "CalendarDateTime", "DeltaTPolicy",
    "julian_day", "calendar_from_jd", "calendar_datetime_from_jd",
    "jd_from_datetime", "datetime_from_jd", "format_jd_utc",
    "safe_datetime_from_jd", "delta_t",
    "DeltaTBreakdown", "delta_t_breakdown",
    # Houses
    "calculate_houses", "assign_house",
    # Aspects
    "find_aspects", "AspectPolicy", "DEFAULT_POLICY",
    # Sidereal
    "Ayanamsa", "ayanamsa",
    "tropical_to_sidereal", "sidereal_to_tropical", "list_ayanamsa_systems",
    # Decanates
    "DecanatePosition", "chaldean_face", "triplicity_decan", "vedic_drekkana",
]

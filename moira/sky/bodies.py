"""
moira.sky.bodies — Celestial Body Positions
============================================
Strict astronomy API for solar system body positions in geocentric,
heliocentric, topocentric, barycentric, and planetocentric frames.

All computations use Moira's DE441 ephemeris via a lazy-loaded kernel.
The kernel is accessed on first call; no import-time side effects.

Geocentric positions  (moira.planets)
--------------------------------------
planet_at(body, jd_ut)
    Geocentric ecliptic position of a solar system body at a given JD_UT.
    Returns PlanetData with ecliptic longitude, latitude, distance, speed,
    and true obliquity at the epoch.

sky_position_at(body, jd_ut, lat, lon)
    Topocentric apparent position for an observer at lat/lon.
    Returns SkyPosition with right ascension, declination, altitude,
    azimuth, and parallax-corrected distance.

all_planets_at(jd_ut)
    Geocentric PlanetData for all supported major bodies simultaneously.

sun_longitude(jd_ut)
    Solar ecliptic longitude in degrees (geocentric, true-of-date).

planet_relative_to(body, jd_ut, reference)
    Ecliptic position of ``body`` as measured from ``reference`` body.

next_heliocentric_transit(body, jd_start, longitude)
    Next epoch at which the body's heliocentric longitude equals
    ``longitude`` (useful for ingress / egress computations).

Heliocentric positions
-----------------------
heliocentric_planet_at(body, jd_ut)
    Heliocentric ecliptic position.  Returns HeliocentricData with
    longitude, latitude, distance, and speed.

all_heliocentric_at(jd_ut)
    HeliocentricData for all supported bodies simultaneously.

Barycentric / SSB positions  (moira.ssb)
-----------------------------------------
ssb_position_at(body, jd_ut)
    Position of a body measured from the Solar System Barycentre.
    Returns SSBPosition with BCRS ecliptic longitude, latitude, distance.
    The Sun itself is non-zero here.

all_ssb_positions_at(jd_ut)
    SSBPosition for all SSB_BODIES simultaneously.

SSB_BODIES
    frozenset of body names with well-defined SSB states in DE441.

Planetocentric positions  (moira.planetocentric)
-------------------------------------------------
planetocentric_at(observer_body, target_body, jd_ut)
    Apparent ecliptic position of ``target_body`` as seen from the center
    of ``observer_body``.  Returns PlanetocentricData.

all_planetocentric_at(observer_body, jd_ut)
    PlanetocentricData for all targets as seen from ``observer_body``.

VALID_OBSERVER_BODIES
    frozenset of bodies that may serve as observer or target.

Lunar nodes and apsides  (moira.nodes)
----------------------------------------
mean_node(jd_ut)    NodeData for the mean ascending node.
true_node(jd_ut)    NodeData for the true (osculating) ascending node.
mean_lilith(jd_ut)  NodeData for mean Lilith (mean apogee).
true_lilith(jd_ut)  NodeData for true Lilith (osculating apogee).

next_moon_node_crossing(jd_start)
    Next JD_UT at which the Moon crosses the ecliptic.

nodes_and_apsides_at(jd_ut)
    NodesAndApsides vessel — mean/true node, mean/true Lilith, perigee,
    and apogee, all at a single epoch.

Result vessels
--------------
PlanetData          geocentric ecliptic: lon, lat, dist, speed, obliquity
SkyPosition         topocentric RA/Dec + alt/az
HeliocentricData    heliocentric ecliptic: lon, lat, dist, speed
CartesianPosition   ICRF Cartesian (x, y, z in AU)
SSBPosition         barycentric ecliptic: lon, lat, dist
PlanetocentricData  observer-relative ecliptic: lon, lat, dist
NodeData            lunar node or Lilith: lon, speed
NodesAndApsides     combined node/apsis bundle
"""

from __future__ import annotations

from moira.nodes import (
    NodeData,
    NodesAndApsides,
    mean_lilith,
    mean_node,
    next_moon_node_crossing,
    nodes_and_apsides_at,
    true_lilith,
    true_node,
)
from moira.planetocentric import (
    VALID_OBSERVER_BODIES,
    PlanetocentricData,
    all_planetocentric_at,
    planetocentric_at,
)
from moira.planets import (
    CartesianPosition,
    HeliocentricData,
    PlanetData,
    SkyPosition,
    all_heliocentric_at,
    all_planets_at,
    heliocentric_planet_at,
    next_heliocentric_transit,
    planet_at,
    planet_relative_to,
    sky_position_at,
    sun_longitude,
)
from moira.ssb import (
    SSB_BODIES,
    SSBPosition,
    all_ssb_positions_at,
    ssb_position_at,
)

__all__ = [
    # Geocentric result vessels
    "PlanetData",
    "SkyPosition",
    "HeliocentricData",
    "CartesianPosition",
    # Geocentric functions
    "planet_at",
    "sky_position_at",
    "all_planets_at",
    "sun_longitude",
    "planet_relative_to",
    "next_heliocentric_transit",
    # Heliocentric functions
    "heliocentric_planet_at",
    "all_heliocentric_at",
    # SSB / barycentric
    "SSBPosition",
    "SSB_BODIES",
    "ssb_position_at",
    "all_ssb_positions_at",
    # Planetocentric
    "PlanetocentricData",
    "VALID_OBSERVER_BODIES",
    "planetocentric_at",
    "all_planetocentric_at",
    # Lunar nodes and apsides
    "NodeData",
    "NodesAndApsides",
    "mean_node",
    "true_node",
    "mean_lilith",
    "true_lilith",
    "next_moon_node_crossing",
    "nodes_and_apsides_at",
]

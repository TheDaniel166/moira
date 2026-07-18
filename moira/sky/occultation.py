"""
moira.sky.occultation — Occultations, Grazes, and Close Approaches
===================================================================
Strict astronomy API for lunar occultations of planets and stars, close
approaches between solar system bodies, and graze path geometry.

All computation uses Moira's DE441 ephemeris for planetary positions and
a fixed-star catalog for stellar targets.

Close approaches
----------------
CloseApproach
    Result vessel for a minimum-separation event between any two bodies.
    Carries JD_UT epoch, angular separation in degrees, and both body names.

close_approaches(body1, body2, jd_start, jd_end)
    Scan a date range for all close approach minima between two named bodies.

Lunar occultations — planets
-----------------------------
LunarOccultation
    Result vessel for a Moon occultation of a planet.
    Carries ingress and egress epochs (JD_UT), body name, and contact postion
    angles.

lunar_occultation(body, jd_start, jd_end)
    Search for Moon occultations of a named planet in a date range.

all_lunar_occultations(jd_start, jd_end)
    Search for Moon occultations of all visible planets simultaneously.

lunar_occultation_path_at(target, jd_mid)
    Compute the compatibility OccultationPathGeometry summary for a planetary
    occultation at a supplied greatest epoch.

lunar_occultation_path(target, jd_start, jd_end)
    Search for planetary occultations and return their compatibility summaries.

lunar_occultation_path_topology_at(target, jd_mid)
    Compute the detailed, polar-safe band topology at one greatest epoch.

lunar_occultation_path_topology(target, jd_start, jd_end)
    Search for planetary occultations and return their detailed topologies.

Lunar occultations — stars
--------------------------
lunar_star_occultation(star, jd_start, jd_end)
    Search for Moon occultations of a named fixed star in a date range.

lunar_star_occultation_path_at(star_lon, star_lat, star_name, jd_mid)
    Compatibility OccultationPathGeometry summary for a stellar occultation.

lunar_star_occultation_path(star_lon, star_lat, star_name, jd_start, jd_end)
    Search for stellar occultations and return their compatibility summaries.

lunar_star_occultation_path_topology_at(star_lon, star_lat, star_name, jd_mid)
    Compute the detailed, polar-safe stellar band topology at one epoch.

lunar_star_occultation_path_topology(star_lon, star_lat, star_name, jd_start, jd_end)
    Search for stellar occultations and return their detailed topologies.

Graze geometry
--------------
Grazes occur when an observer near the northern or southern limit of the
occultation path sees the body skim the lunar limb.  The graze path is
computed using Moira's lunar geometry and the observer's topocentric
parallax.

GrazeCircumstances
    Contact events along the limb during a graze: multiple disappear /
    reappear epochs as the body crosses limb features.

GrazeTableRow
    One row in a latitude-keyed graze table: latitude, longitude, contact
    type, position angle.

GrazeProductGeometry
    The resolved graze geometry at a specific observer lat/lon.

GrazeProductTrack
    The graze track across a band of latitudes.

OccultationPathGeometry
    Compatibility summary vessel containing sampled center locations plus the
    greatest path width and greatest-site duration. It does not contain limit
    tracks or begin/end contact vessels.

OccultationPathTopology
    Detailed nominal mean-limb path-band vessel containing the shared UT1 center lattice,
    intrinsic left/right limit tracks, greatest half-width witnesses, and
    explicit exact-pole ingress/egress contacts. Left/right follows increasing
    UT1 along the track and must not be relabeled geographic north/south. The
    requested observer elevation is retained as result provenance.

Functions
---------
lunar_star_graze_circumstances(star, event, lat, lon)
lunar_star_graze_latitude(star, event)
lunar_star_practical_graze_latitude(star, event)
lunar_star_graze_line(star, event)
lunar_star_graze_table(star, event)
lunar_star_graze_product_at(star, event, lat)
lunar_star_graze_product_track(star, event)
"""

from __future__ import annotations

from moira.occultations import (
    CloseApproach,
    GrazeCircumstances,
    GrazeProductGeometry,
    GrazeProductTrack,
    GrazeTableRow,
    LunarOccultation,
    OccultationGeographicPole,
    OccultationPathBoundaryPoint,
    OccultationPathBoundarySide,
    OccultationPathBoundaryTrack,
    OccultationPathGeometry,
    OccultationPathPoint,
    OccultationPathTopology,
    OccultationPathTopologyKind,
    OccultationPoleCrossing,
    OccultationPoleCrossingPhase,
    all_lunar_occultations,
    close_approaches,
    lunar_occultation,
    lunar_occultation_path,
    lunar_occultation_path_at,
    lunar_occultation_path_topology,
    lunar_occultation_path_topology_at,
    lunar_star_graze_circumstances,
    lunar_star_graze_latitude,
    lunar_star_graze_line,
    lunar_star_graze_product_at,
    lunar_star_graze_product_track,
    lunar_star_graze_table,
    lunar_star_occultation,
    lunar_star_occultation_path,
    lunar_star_occultation_path_at,
    lunar_star_occultation_path_topology,
    lunar_star_occultation_path_topology_at,
    lunar_star_practical_graze_latitude,
)

__all__ = [
    # Result vessels
    "CloseApproach",
    "LunarOccultation",
    "OccultationGeographicPole",
    "OccultationPathBoundaryPoint",
    "OccultationPathBoundarySide",
    "OccultationPathBoundaryTrack",
    "OccultationPathGeometry",
    "OccultationPathPoint",
    "OccultationPathTopology",
    "OccultationPathTopologyKind",
    "OccultationPoleCrossing",
    "OccultationPoleCrossingPhase",
    # Graze vessels
    "GrazeCircumstances",
    "GrazeTableRow",
    "GrazeProductGeometry",
    "GrazeProductTrack",
    # Close approach
    "close_approaches",
    # Planetary occultations
    "lunar_occultation",
    "lunar_occultation_path_at",
    "lunar_occultation_path",
    "lunar_occultation_path_topology_at",
    "lunar_occultation_path_topology",
    "all_lunar_occultations",
    # Stellar occultations
    "lunar_star_occultation",
    "lunar_star_occultation_path_at",
    "lunar_star_occultation_path",
    "lunar_star_occultation_path_topology_at",
    "lunar_star_occultation_path_topology",
    # Graze functions
    "lunar_star_graze_circumstances",
    "lunar_star_graze_latitude",
    "lunar_star_practical_graze_latitude",
    "lunar_star_graze_line",
    "lunar_star_graze_table",
    "lunar_star_graze_product_at",
    "lunar_star_graze_product_track",
]

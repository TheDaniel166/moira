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

lunar_occultation_path_at(event, jd_ut)
    Compute OccultationPathGeometry for a planetary occultation at a moment.

lunar_occultation_path(event)
    Full geographic path of a planetary lunar occultation.

Lunar occultations — stars
--------------------------
lunar_star_occultation(star, jd_start, jd_end)
    Search for Moon occultations of a named fixed star in a date range.

lunar_star_occultation_path_at(event, jd_ut)
    OccultationPathGeometry for a stellar occultation at a moment.

lunar_star_occultation_path(event)
    Full geographic path of a stellar lunar occultation.

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
    General path geometry vessel: northern and southern limit lines,
    central line (if applicable), begin and end points.

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

from moira.occultations import (
    CloseApproach,
    GrazeCircumstances,
    GrazeProductGeometry,
    GrazeProductTrack,
    GrazeTableRow,
    LunarOccultation,
    OccultationPathGeometry,
    all_lunar_occultations,
    close_approaches,
    lunar_occultation,
    lunar_occultation_path,
    lunar_occultation_path_at,
    lunar_star_graze_circumstances,
    lunar_star_graze_latitude,
    lunar_star_graze_line,
    lunar_star_graze_product_at,
    lunar_star_graze_product_track,
    lunar_star_graze_table,
    lunar_star_occultation,
    lunar_star_occultation_path,
    lunar_star_occultation_path_at,
    lunar_star_practical_graze_latitude,
)

__all__ = [
    # Result vessels
    "CloseApproach",
    "LunarOccultation",
    "OccultationPathGeometry",
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
    "all_lunar_occultations",
    # Stellar occultations
    "lunar_star_occultation",
    "lunar_star_occultation_path_at",
    "lunar_star_occultation_path",
    # Graze functions
    "lunar_star_graze_circumstances",
    "lunar_star_graze_latitude",
    "lunar_star_practical_graze_latitude",
    "lunar_star_graze_line",
    "lunar_star_graze_table",
    "lunar_star_graze_product_at",
    "lunar_star_graze_product_track",
]

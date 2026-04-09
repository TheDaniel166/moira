"""
moira.sky.visibility — Observational Visibility Doctrine
=========================================================
Strict astronomy API for heliacal visibility, lunar crescent prediction,
atmospheric extinction, moonlight modeling, and arcus visionis.

This subsystem implements Moira's full visibility doctrine.  All models
are explicitly named and policy-controlled; there are no hidden defaults.

Visibility framework
--------------------
VisibilityPolicy
    Observer environment: sky darkness, extinction, twilight model,
    light pollution class, observer aids (naked eye / binocular / telescope).

HeliacalPolicy
    Combines VisibilityPolicy with the target body, search direction, and
    criterion family (arcus visionis vs Yallop crescent vs general).

VisibilitySearchPolicy
    Search window, time step, and convergence tolerance parameters.

VisibilityModel
    Resolved values: effective limiting magnitude, extinction coefficient,
    sky darkness in nanolamberts.  Read-only output of policy resolution.

ExtinctionCoefficient
    Explicit extinction model: Rayleigh + aerosol + ozone components.

Observer environment
--------------------
ObserverVisibilityEnvironment  sky darkness, elevation, horizon
LightPollutionClass            Bortle-derived classification
ObserverAid                    NakedEye / Binocular / Telescope

Moonlight model
---------------
MoonlightPolicy   KS1991 (Khalid-Sultana) vs simplified approximation

Lunar crescent (Yallop 1997)
----------------------------
LunarCrescentDetails
    Full crescent geometry: q-value, arc of light, ARCV, DAZ, crescent
    width, best time, Yallop visibility class.

LunarCrescentVisibilityClass
    A — Easily visible
    B — Visible under perfect conditions
    C — May need optical aid
    D — Only with optical aid
    E — Not visible with optical aid
    F — Below the horizon

Heliacal events
---------------
visibility_assessment       single-epoch check — body visible at this moment?
visual_limiting_magnitude   effective limiting magnitude at epoch
visibility_event            search for next first/last heliacal event
planet_heliacal_rising      morning first visibility (planet)
planet_heliacal_setting     evening last visibility (planet)
planet_acronychal_rising    evening first visibility (planet)
planet_acronychal_setting   morning last visibility (planet)

Result vessels
--------------
VisibilityAssessment    single-epoch result with altitude, elongation, verdict
GeneralVisibilityEvent  body + date + kind + assessment for any body
PlanetHeliacalEvent     planet-specific event with elongation and phase data

Enumerations
------------
HeliacalEventKind         MorningFirst / EveningLast / EveningFirst / MorningLast
VisibilityTargetKind      Star / Planet / Moon
VisibilityCriterionFamily ArucusVisionis / YallopCrescent / General
VisibilityExtinctionModel Schaefer / Fixed / Custom
VisibilityTwilightModel   Civil / Nautical / Astronomical / SolarDepression
"""

from __future__ import annotations

from moira.heliacal import (
    ExtinctionCoefficient,
    GeneralVisibilityEvent,
    HeliacalEventKind,
    HeliacalPolicy,
    LightPollutionClass,
    LightPollutionDerivationMode,
    LunarCrescentDetails,
    LunarCrescentVisibilityClass,
    MoonlightPolicy,
    ObserverAid,
    ObserverVisibilityEnvironment,
    PlanetHeliacalEvent,
    VisibilityAssessment,
    VisibilityCriterionFamily,
    VisibilityExtinctionModel,
    VisibilityModel,
    VisibilityPolicy,
    VisibilitySearchPolicy,
    VisibilityTargetKind,
    VisibilityTwilightModel,
    planet_acronychal_rising,
    planet_acronychal_setting,
    planet_heliacal_rising,
    planet_heliacal_setting,
    visibility_assessment,
    visibility_event,
    visual_limiting_magnitude,
)

__all__ = [
    # Enumerations
    "HeliacalEventKind",
    "VisibilityTargetKind",
    "LightPollutionClass",
    "LightPollutionDerivationMode",
    "ObserverAid",
    "VisibilityCriterionFamily",
    "LunarCrescentVisibilityClass",
    "VisibilityExtinctionModel",
    "VisibilityTwilightModel",
    "MoonlightPolicy",
    # Policy objects
    "ExtinctionCoefficient",
    "ObserverVisibilityEnvironment",
    "VisibilityPolicy",
    "VisibilitySearchPolicy",
    "VisibilityModel",
    "HeliacalPolicy",
    # Result vessels
    "LunarCrescentDetails",
    "VisibilityAssessment",
    "GeneralVisibilityEvent",
    "PlanetHeliacalEvent",
    # Functions
    "visibility_assessment",
    "visual_limiting_magnitude",
    "visibility_event",
    "planet_heliacal_rising",
    "planet_heliacal_setting",
    "planet_acronychal_rising",
    "planet_acronychal_setting",
]

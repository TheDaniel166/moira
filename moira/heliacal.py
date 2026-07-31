"""
Moira — Heliacal and Visibility Doctrine
=========================================

Archetype: Substrate Anchor (Phenomena Engine)

Purpose
-------
Provides Moira's public heliacal and admitted generalized visibility doctrine.
This includes typed doctrine surfaces for heliacal phenomena, explicit
visibility policy, direct atmospheric extinction, directional cloudless-sky
twilight brightness, point-source thresholds, and moonlight sky brightness.

Boundary
--------
Owns:
    - HeliacalEventKind exhaustive event-kind enum.
    - Generalized visibility event surface for planets, fixed stars, and the Moon.
    - Observer-environment policy and Bortle-class light-pollution derivation.
    - Direct-beam extinction and directional sky-brightness models.
    - Naked-eye point-source threshold and moonlight models.
Delegates:
    - moira.stars      — fixed-star heliacal event search.
    - moira.planets    — planetary apparent positions and magnitudes.
    - moira.rise_set   — altitude, twilight, and rise/set phenomena.

Data source
-----------
Krisciunas, K. & Schaefer, B.E. (1991), PASP 103, 1033–1039 (Moonlight).
Kasten, F. & Young, A.T. (1989), Applied Optics 28, 4735–4738 (Air mass).
Schaefer, B.E. (1993), Vistas in Astronomy 36, 311–361 (Visibility).
Crumey, A. (2014), MNRAS 442, 2600–2619 (Point-source threshold).
Bortle, J.E. (2001), Sky & Telescope 101(2), 126–129 (Light Pollution).
Yallop, B.D. (1997), NAO Technical Note No. 69 (Lunar Crescent).

Import-time side effects
------------------------
None.

External dependency assumptions
--------------------------------
- DE441 kernel accessible via moira.planets.
- moira.constants.Body constants available for body identity.

Public surface
--------------
See ``__all__`` below for the stable public surface.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, IntEnum

from ._visibility_lut import (
    VisibilityDataPack,
    VisibilityDataPackConfig,
    VisibilityDataPackDomain,
    VisibilityDataPackDomainError,
    VisibilityDataPackLoadError,
    VisibilityDataPackReceipt,
    load_visibility_data_pack,
)
from ._visibility_event_solver import (
    ObservationDaySolution as _ObservationDaySolution,
    ObservationPhaseRule as _ObservationPhaseRule,
    ObservationWindowConstruction as _ObservationWindowConstruction,
    PhaseTransitionSelection as _PhaseTransitionSelection,
    ScalarEvaluation as _ScalarEvaluation,
    ScalarIntervalScan as _ScalarIntervalScan,
    ScalarLipschitzCertificate as _ScalarLipschitzCertificate,
    ScalarSearchPolicy as _ScalarSearchPolicy,
    classify_observation_day as _classify_observation_day,
    construct_observation_windows as _construct_observation_windows,
    select_owned_phase_transition as _select_owned_phase_transition,
)
from ._visibility_spectral import (
    ConditionedTarget,
    DirectionalLuminance as _DirectionalLuminance,
    FullRangePointSourceThreshold as _FullRangePointSourceThreshold,
    ModeledDirectionalBackgroundComponent,
    PhysicalVisibilityCompositionError,
    SpectralComponentReceipt,
    SpectralSingleEpochTruth,
    TargetSpectralProfile as _TargetSpectralProfile,
    VisibilityMarginErrorBudget as _VisibilityMarginErrorBudget,
    spectral_single_epoch_truth,
    sqm_directional_luminance,
)
from ._visibility_stellar_targets import (
    VisibilityStellarTargetProfileError,
)
from ._visibility_targets import (
    VisibilityTargetContext,
    VisibilityTargetProfileError,
)
from .constants import Body
from .corrections import apply_refraction


__all__ = [
    "HeliacalEventKind",
    "VisibilityTargetKind",
    "LightPollutionClass",
    "ObserverAid",
    "LightPollutionDerivationMode",
    "VisibilityExtinctionModel",
    "VisibilityTwilightModel",
    "ExtinctionCoefficient",
    "MoonlightPolicy",
    "VisibilityCriterionFamily",
    "PhysicalVisibilityStatus",
    "PhysicalVisibilityEvidenceState",
    "PhysicalVisibilityPhase",
    "PhysicalVisibilityCrossingDirection",
    "PhysicalVisibilityBoundarySource",
    "PhysicalEventTimeSemantics",
    "PhysicalBackgroundScope",
    "PhysicalBackgroundComponentKind",
    "AtmosphericExtinctionAssessment",
    "TwilightSkyBrightnessAssessment",
    "PointSourceVisibilityThreshold",
    "PhysicalAtmosphereInput",
    "PhysicalDirectionalBackground",
    "PhysicalModeledBackgroundComponent",
    "PhysicalSqmBackground",
    "PhysicalBortleBackground",
    "PhysicalHorizonSample",
    "PhysicalHorizonProfile",
    "PhysicalVisibilityPolicy",
    "VisibilityComponentReceipt",
    "PhysicalAtmosphereReceipt",
    "PhysicalValidityDomainReceipt",
    "PhysicalObserverProtocolReceipt",
    "PhysicalBackgroundReceipt",
    "PhysicalTargetReceipt",
    "PhysicalThresholdReceipt",
    "PhysicalVisibilityErrorBudgetReceipt",
    "PhysicalVisibilityAssessment",
    "PhysicalVisibilitySearchPolicy",
    "PhysicalObservationWindowReceipt",
    "PhysicalEventSolverReceipt",
    "PhysicalEventSensitivityReceipt",
    "PhysicalHorizonReceipt",
    "PhysicalEphemerisReceipt",
    "PhysicalVisibilityEventResult",
    "VisibilityDataPackConfig",
    "VisibilityDataPackReceipt",
    "LunarCrescentVisibilityClass",
    "LunarCrescentDetails",
    "ObserverVisibilityEnvironment",
    "VisibilityPolicy",
    "VisibilitySearchPolicy",
    "VisibilityAssessment",
    "VisibilityModel",
    "HeliacalPolicy",
    "GeneralVisibilityEvent",
    "PlanetHeliacalEvent",
    "relative_optical_airmass",
    "atmospheric_extinction",
    "directional_twilight_sky_brightness",
    "point_source_visibility_threshold",
    "physical_visibility_assessment",
    "physical_visibility_event",
    "visibility_assessment",
    "visual_limiting_magnitude",
    "visibility_event",
    "visibility_tonight",
    "is_visible_tonight",
    "planet_heliacal_rising",
    "planet_heliacal_setting",
    "planet_acronychal_rising",
    "planet_acronychal_setting",
]


# ---------------------------------------------------------------------------
# HeliacalEventKind
# ---------------------------------------------------------------------------

class HeliacalEventKind(str, Enum):
    """
    RITE: The Six Gates — the canonical astronomical visibility threshold crossings.

    THEOREM: Exhaustive str-enum of the six classical heliacal phenomena that
    govern event-kind dispatch throughout the visibility doctrine.

    RITE OF PURPOSE:
        Encodes the six canonical visibility boundary crossings as a typed enum
        so callers cannot accidentally pass an out-of-range integer or an
        ambiguous string.  Without this gate, event-kind dispatch collapses into
        brittle integer comparisons carried wholesale from legacy integer
        flag constants.  This enum is the doctrinal identity layer for heliacal
        event taxonomy.

    LAW OF OPERATION:
        Responsibilities:
            - Provide exhaustive named coverage of the six classical phenomena.
            - Serve as the dispatch key for visibility_event() routing.
            - Enforce that event-kind values are valid at the type level.
        Non-responsibilities:
            - Does not compute any event.
            - Does not express a runtime dependency on legacy integer flags.
            - Does not distinguish planetary vs. stellar applicability.
        Dependencies:
            - None.  Pure enum; no runtime imports required.
        Structural invariants:
            - Six members exactly.  New kinds require explicit doctrinal
              justification and a change to the event-search dispatch table.

    Canon: Ptolemy via Schoch nomenclature; modern heliacal event nomenclature
           family (mapping provenance only, not runtime dependency).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.HeliacalEventKind",
        "risk": "low",
        "api": {
            "members": ["HELIACAL_RISING", "HELIACAL_SETTING",
                        "ACRONYCHAL_RISING", "ACRONYCHAL_SETTING",
                        "COSMIC_RISING", "COSMIC_SETTING"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]

    Heliacal phenomena (eastern sky near sunrise):
        HELIACAL_RISING      — body first visible in the east before sunrise
                                after a period of solar invisibility (the
                                classical *first appearance*).
        HELIACAL_SETTING     — body last visible in the east before sunrise
                                before solar invisibility begins (*last
                                appearance*, eastern sky).

    Acronychal phenomena (western sky near sunset):
        ACRONYCHAL_RISING    — body first visible in the west after sunset.
        ACRONYCHAL_SETTING   — body last visible in the west after sunset.

    Cosmic phenomena (astronomical twilight boundary):
        COSMIC_RISING        — body rises exactly at true astronomical dawn.
        COSMIC_SETTING       — body sets exactly at true astronomical dusk.
    """
    HELIACAL_RISING   = "heliacal_rising"
    HELIACAL_SETTING  = "heliacal_setting"
    ACRONYCHAL_RISING = "acronychal_rising"
    ACRONYCHAL_SETTING = "acronychal_setting"
    COSMIC_RISING     = "cosmic_rising"
    COSMIC_SETTING    = "cosmic_setting"


class VisibilityTargetKind(str, Enum):
    """
    RITE: The Three Families — planet, star, and Moon as distinct visibility populations.

    THEOREM: Str-enum classifying the target body family for generalized
    visibility-event dispatch and result labelling.

    RITE OF PURPOSE:
        Distinguishes planets, fixed stars, and the Moon so the visibility_event()
        Engine can route to the correct algorithm and oracle for each family.
        Without this classifier, the generalized surface would require callers to
        infer target-kind semantics from body name strings, collapsing distinct
        computational paths into one ambiguous channel.

    LAW OF OPERATION:
        Responsibilities:
            - Classify any admitted body into one of three target families.
            - Serve as a routing discriminant inside visibility_event().
            - Label result vessels so downstream callers can inspect target kind
              without re-inferring it from body name.
        Non-responsibilities:
            - Does not infer body kind from a body name string (that is
              done by _target_kind()).
            - Does not define the algorithm for any family.
        Dependencies:
            - None.  Pure enum.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.VisibilityTargetKind",
        "risk": "low",
        "api": {
            "members": ["PLANET", "STAR", "MOON"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    PLANET = "planet"
    STAR = "star"
    MOON = "moon"


class LightPollutionClass(IntEnum):
    """
    RITE: The Bortle Scale — the canonical darkness-class registry for observing sites.

    THEOREM: Typed int-enum encoding the Bortle sky darkness scale from class 1
    (exceptional dark site) to class 9 (inner-city sky).

    RITE OF PURPOSE:
        Encodes the Bortle scale as a typed int-enum so site darkness can be
        expressed as a policy field without passing raw floats or magic integers.
        Drives both limiting-magnitude derivation and K&S 1991 dark-sky
        nanolambert derivation.  Without this typed scale, observers would need
        to supply ad-hoc sky-brightness values whose provenance is invisible.

    LAW OF OPERATION:
        Responsibilities:
            - Provide nine named Bortle tiers as a closed typed scale.
            - Serve as policy input to _policy_limiting_magnitude() and
              _ks1991_dark_sky_nanolamberts().
        Non-responsibilities:
            - Does not define the numeric sky-brightness associated with each
              class (held in _BORTLE_LIMITING_MAG_TABLE and _BORTLE_SKY_SQM_TABLE).
            - Does not validate geographic site characteristics.
        Dependencies:
            - None.  Pure enum.
        Structural invariants:
            - Nine members, integer values 1–9 matching the Bortle paper.

    Canon: Bortle, J.E. (2001), Sky & Telescope 101(2), 126–129.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.LightPollutionClass",
        "risk": "low",
        "api": {
            "members": ["BORTLE_1", "BORTLE_2", "BORTLE_3", "BORTLE_4", "BORTLE_5",
                        "BORTLE_6", "BORTLE_7", "BORTLE_8", "BORTLE_9"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid integer construction"],
            "policy": "int-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    BORTLE_1 = 1
    BORTLE_2 = 2
    BORTLE_3 = 3
    BORTLE_4 = 4
    BORTLE_5 = 5
    BORTLE_6 = 6
    BORTLE_7 = 7
    BORTLE_8 = 8
    BORTLE_9 = 9


class ObserverAid(str, Enum):
    """
    RITE: The Instrument Witness — the declared optical instrument of the observer.

    THEOREM: Str-enum of the three admitted observing instruments for the
    visibility criterion family.

    RITE OF PURPOSE:
        Declares whether the observer uses naked eye, binoculars, or a telescope,
        so the criterion family can adjust the effective visibility threshold.
        The Yallop lunar crescent criterion uses observing aid to classify B/C/D
        events as instrument-dependent.  Without this typed declaration,
        instrument sensitivity would require separate raw flags.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the three admitted observing instruments.
            - Serve as an input to _yallop_class_observable() and
              ObserverVisibilityEnvironment.observing_aid.
        Non-responsibilities:
            - Does not define the magnitude correction for each instrument.
            - Does not apply to planetary position computation.
        Dependencies:
            - None.  Pure enum.

    Canon: Yallop (1997), NAO Technical Note No. 69 (three-way instrument
           classification for lunar crescent visibility).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.ObserverAid",
        "risk": "low",
        "api": {
            "members": ["NAKED_EYE", "BINOCULARS", "TELESCOPE"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    NAKED_EYE = "naked_eye"
    BINOCULARS = "binoculars"
    TELESCOPE = "telescope"


class LightPollutionDerivationMode(str, Enum):
    """
    RITE: The Derivation Mode — the admitted selection between two Bortle derivation paths.

    THEOREM: Str-enum selecting whether limiting magnitude is derived from the
    Bortle class via a lookup table or a linear formula.

    RITE OF PURPOSE:
        Controls how _policy_limiting_magnitude() converts a Bortle class integer
        into a floating-point limiting magnitude.  The two modes produce slightly
        different values and the explicit selection ensures the derivation path
        is visible in policy rather than hidden behind a single function.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the two admitted derivation modes.
            - Serve as the mode selector in _policy_limiting_magnitude().
        Non-responsibilities:
            - Does not hold the table or formula itself.
            - Does not affect K&S 1991 moonlight computation directly.
        Dependencies:
            - None.  Pure enum.

    Canon: Bortle (2001), Sky & Telescope 101(2), 126–129 (table source);
           linear formula is a Moira internal approximation.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.LightPollutionDerivationMode",
        "risk": "low",
        "api": {
            "members": ["BORTLE_LINEAR", "BORTLE_TABLE"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    BORTLE_LINEAR = "bortle_linear"
    BORTLE_TABLE = "bortle_table"


class VisibilityCriterionFamily(str, Enum):
    """
    RITE: The Criterion Gate — the doctrinal selection between admitted visibility
    criterion families.

    THEOREM: Str-enum naming the currently admitted visibility criterion
    families that govern observability decisions.

    RITE OF PURPOSE:
        Separates the legacy limiting-magnitude threshold, the physical Crumey
        point-source threshold, and the Yallop lunar crescent family so each
        dispatch path applies the criterion that the caller declared.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the admitted criterion families.
            - Serve as the routing key in visibility_assessment() and
              visibility_event().
        Non-responsibilities:
            - Does not implement either criterion.
            - Does not validate that a body is appropriate for the selected family
              (that is enforced at call sites).
        Dependencies:
            - None.  Pure enum.
        Behavioral invariants:
            - YALLOP_LUNAR_CRESCENT is only valid when body == Body.MOON.

    Canon: Yallop (1997), NAO Technical Note No. 69 (Yallop crescent criterion);
           Schaefer (1990), PASP 102, 212–229 (limiting-magnitude family).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.VisibilityCriterionFamily",
        "risk": "low",
        "api": {
            "members": [
                "LIMITING_MAGNITUDE_THRESHOLD",
                "CRUMEY_2014_POINT_SOURCE",
                "YALLOP_LUNAR_CRESCENT"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    LIMITING_MAGNITUDE_THRESHOLD = "limiting_magnitude_threshold"
    CRUMEY_2014_POINT_SOURCE = "crumey_2014_point_source"
    YALLOP_LUNAR_CRESCENT = "yallop_lunar_crescent"


class PhysicalVisibilityStatus(str, Enum):
    """Evaluation status for additive physical assessment and event truth."""

    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"
    NOT_FOUND = "not_found"


class PhysicalVisibilityEvidenceState(str, Enum):
    """Why a physical assessment or event did or did not produce truth."""

    EVALUATED_CLEAR_SKY = "evaluated_clear_sky"
    EVALUATED_NO_EVENT = "evaluated_no_event"
    NOT_APPLICABLE = "not_applicable"
    MISSING_DEPENDENCY = "missing_dependency"
    OUT_OF_DOMAIN = "out_of_domain"


class PhysicalVisibilityPhase(str, Enum):
    """Exact within-day and across-day physical event semantics."""

    MORNING_FIRST_RISING = "morning_first_rising"
    MORNING_FIRST_SETTING = "morning_first_setting"
    EVENING_LAST_RISING = "evening_last_rising"
    EVENING_LAST_SETTING = "evening_last_setting"


class PhysicalVisibilityCrossingDirection(str, Enum):
    """Direction of the physical visibility-state transition."""

    NOT_VISIBLE_TO_VISIBLE = "not_visible_to_visible"
    VISIBLE_TO_NOT_VISIBLE = "visible_to_not_visible"


class PhysicalVisibilityBoundarySource(str, Enum):
    """Astronomical boundary that owns the reported event instant."""

    VISIBILITY_MARGIN = "visibility_margin"
    TARGET_HORIZON = "target_horizon"
    TARGET_DATA_PACK_ALTITUDE_FLOOR = (
        "target_data_pack_altitude_floor"
    )


class PhysicalEventTimeSemantics(str, Enum):
    """Typed meaning of the primary event Julian date."""

    VISIBILITY_MARGIN_ZERO = "visibility_margin_zero"
    APPARENT_TARGET_HORIZON = "apparent_target_horizon"
    DATA_PACK_TARGET_ALTITUDE_FLOOR = (
        "data_pack_target_altitude_floor"
    )


class PhysicalBackgroundScope(str, Enum):
    """Whether a background input is total or one dark-sky component."""

    TOTAL_BACKGROUND = "total_background"
    DARK_SKY_ANCHOR = "dark_sky_anchor"


class PhysicalBackgroundComponentKind(str, Enum):
    """Separately modeled directional background component identity."""

    AIRGLOW = "airglow"
    ZODIACAL_LIGHT = "zodiacal_light"
    INTEGRATED_STARLIGHT = "integrated_starlight"
    ARTIFICIAL_LIGHT = "artificial_light"


class LunarCrescentVisibilityClass(str, Enum):
    """
    RITE: The Yallop Classes — the six canonical lunar crescent visibility grades.

    THEOREM: Str-enum reproducing the six A–F observability grades defined by
    Yallop (1997) for lunar new crescent first-sighting.

    RITE OF PURPOSE:
        Encodes the Yallop q-value classification scheme so that crescent
        observability verdicts carry a typed, self-documenting grade rather than
        a raw float or an opaque integer.  Classes A and B indicate naked-eye
        visibility; C and D instrument-aided; E and F not visible.  Without
        this enum, the q-value boundary table would need to be reproduced
        at every call site.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the six Yallop visibility grades.
            - Serve as the typed verdict in LunarCrescentDetails.visibility_class
              and VisibilityAssessment.
        Non-responsibilities:
            - Does not compute the q-value.
            - Does not encode the numeric q-value boundaries (held in
              _yallop_visibility_class()).
        Dependencies:
            - None.  Pure enum.
        Structural invariants:
            - Six members A–F, matching the Yallop paper classification table.

    Canon: Yallop, B.D. (1997), "A Method for Predicting the First Sighting of
           the New Crescent Moon," NAO Technical Note No. 69.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.LunarCrescentVisibilityClass",
        "risk": "low",
        "api": {
            "members": ["A", "B", "C", "D", "E", "F"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


@dataclass(frozen=True, slots=True)
class LunarCrescentDetails:
    """
    RITE: The Yallop Vessel — the canonical crescent-assessment data carrier.

    THEOREM: Immutable frozen dataclass carrying all Yallop (1997) derived
    quantities produced for a single lunar crescent assessment instant.

    RITE OF PURPOSE:
        Collects the intermediate geometric and photometric quantities that the
        Yallop q-value formula requires and produces, so that a crescent
        assessment result is fully inspectable and reproducible.  Without this
        vessel, callers receiving only a visibility boolean would have no way to
        audit the arcv/arcl/width values that drove the decision.

    LAW OF OPERATION:
        Responsibilities:
            - Store all Yallop (1997) intermediate and derived quantities for
              one assessment instant.
            - Carry the final q-value and A–F visibility class.
            - Serve as the inner vessel within VisibilityAssessment and
              GeneralVisibilityEvent when criterion_family is
              YALLOP_LUNAR_CRESCENT.
        Non-responsibilities:
            - Does not compute any of its fields (populated by
              _lunar_crescent_details_at()).
            - Does not define q-value boundaries or class transitions.
        Dependencies:
            - Populated exclusively by _lunar_crescent_details_at() or
              _lunar_crescent_details_for_evening/morning().
        Structural invariants:
            - All float fields are finite upon construction (enforced by the
              computing functions, not by __post_init__).
            - visibility_class matches the q-value per the Yallop boundary table.

    Canon: Yallop, B.D. (1997), "A Method for Predicting the First Sighting of
           the New Crescent Moon," NAO Technical Note No. 69.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.LunarCrescentDetails",
        "risk": "low",
        "api": {
            "public_attributes": [
                "best_time_jd_ut", "sunset_jd_ut", "moonset_jd_ut",
                "lag_minutes", "arcl_deg", "arcv_deg", "daz_deg",
                "moon_altitude_deg", "sun_altitude_deg",
                "lunar_parallax_arcmin", "topocentric_crescent_width_arcmin",
                "q", "visibility_class"
            ]
        },
        "state": {
            "mutable": false,
            "fields": "all float except visibility_class (LunarCrescentVisibilityClass)"
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller-populated; field validity is the computing function's responsibility"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    best_time_jd_ut: float
    sunset_jd_ut: float
    moonset_jd_ut: float
    lag_minutes: float
    arcl_deg: float
    arcv_deg: float
    daz_deg: float
    moon_altitude_deg: float
    sun_altitude_deg: float
    lunar_parallax_arcmin: float
    topocentric_crescent_width_arcmin: float
    q: float
    visibility_class: LunarCrescentVisibilityClass


class VisibilityExtinctionModel(str, Enum):
    """
    RITE: The Extinction Slot — the admitted extinction treatment declaration.

    THEOREM: Str-enum naming the admitted legacy or physical extinction
    treatment declared by a visibility policy.

    RITE OF PURPOSE:
        Holds the named extinction treatment so policy objects distinguish the
        legacy arcus-visionis convention, a measured broadband coefficient
        evaluated with Kasten--Young (1989) air mass, and Schaefer's (1993)
        component estimate.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the admitted extinction treatments.
            - Serve as the extinction_model field of VisibilityPolicy.
        Non-responsibilities:
            - Does not implement extinction computation (handled by
              atmospheric_extinction() or the legacy _arcus_visionis()).
            - Does not govern K&S 1991 moonlight extinction (controlled by
              VisibilityPolicy.extinction_coefficient_k).
        Dependencies:
            - None.  Pure enum.

    Canon: Schaefer, B.E. (1990), PASP 102, 212–229 (arcus visionis and
           extinction foundation used in LEGACY_ARCUS_VISIONIS).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.VisibilityExtinctionModel",
        "risk": "low",
        "api": {
            "members": [
                "LEGACY_ARCUS_VISIONIS",
                "KASTEN_YOUNG_1989_BROADBAND",
                "SCHAEFER_1993_COMPONENTS"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    LEGACY_ARCUS_VISIONIS = "legacy_arcus_visionis"
    KASTEN_YOUNG_1989_BROADBAND = "kasten_young_1989_broadband"
    SCHAEFER_1993_COMPONENTS = "schaefer_1993_components"


class VisibilityTwilightModel(str, Enum):
    """
    RITE: The Twilight Slot — the admitted twilight treatment declaration.

    THEOREM: Str-enum naming either the legacy solar-depression event
    convention or the admitted directional twilight-brightness model.

    RITE OF PURPOSE:
        Holds the named twilight treatment so that policy objects can declare
        which twilight model governs the calculation: the legacy
        solar-depression threshold or Schaefer's (1993) directional
        cloudless-sky brightness model.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the admitted twilight treatments.
            - Serve as the twilight_model field of VisibilityPolicy.
        Non-responsibilities:
            - Does not implement twilight computation (handled by
              directional_twilight_sky_brightness() or legacy event search).
            - Does not govern astronomical or civil twilight separately.
        Dependencies:
            - None.  Pure enum.

    Canon: Ptolemy / Schoch arcus visionis tradition; Schaefer (1990),
           PASP 102, 212–229 (solar-depression as visibility threshold).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.VisibilityTwilightModel",
        "risk": "low",
        "api": {
            "members": [
                "ARCUS_VISIONIS_SOLAR_DEPRESSION",
                "SCHAEFER_1993_DIRECTIONAL"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    ARCUS_VISIONIS_SOLAR_DEPRESSION = "arcus_visionis_solar_depression"
    SCHAEFER_1993_DIRECTIONAL = "schaefer_1993_directional"


class ExtinctionCoefficient:
    """
    RITE: The Extinction Oracle — the canonical broadband extinction coefficient registry.

    THEOREM: Class-level namespace holding four named reference extinction
    coefficients (mag/airmass) drawn from Schaefer (1990) and Krisciunas &
    Schaefer (1991).

    RITE OF PURPOSE:
        Provides named float holders for the four admitted site-class extinction
        values so callers can reference well-documented reference points rather
        than supplying raw floats to VisibilityPolicy.extinction_coefficient_k.
        Without this registry, users would need to memorise or look up the
        K&S 1991 paper values before constructing a policy.

    LAW OF OPERATION:
        Responsibilities:
            - Expose four named float class attributes covering the practical
              range of broadband extinction from exceptional to hazy sites.
            - Serve as documentation-adjacent holders for
              VisibilityPolicy.extinction_coefficient_k.
        Non-responsibilities:
            - Does not instantiate; all attributes are class-level floats.
            - Does not enforce that the policy field is restricted to these
              four values.
            - Does not govern wavelength-dependent or narrow-band extinction.
        Dependencies:
            - None.  No runtime imports required.
        Structural invariants:
            - MAUNA_KEA (0.172) ≤ GOOD_DARK_SITE (0.20) ≤ TYPICAL (0.25)
              ≤ HAZY (0.30).

    Canon: Schaefer, B.E. (1990), PASP 102, 212–229;
           Krisciunas, K. & Schaefer, B.E. (1991), PASP 103, 1033–1039.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.ExtinctionCoefficient",
        "risk": "low",
        "api": {
            "public_attributes": ["MAUNA_KEA", "GOOD_DARK_SITE", "TYPICAL", "HAZY"]
        },
        "state": {
            "mutable": false,
            "fields": "class-level float constants"
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "no instance construction expected"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    MAUNA_KEA: float = 0.172
    """Exceptional high-altitude site (Mauna Kea, Hawaii)."""

    GOOD_DARK_SITE: float = 0.20
    """Good mid-latitude dark site.  Recommended default for most observers."""

    TYPICAL: float = 0.25
    """Typical clear mid-latitude site."""

    HAZY: float = 0.30
    """Hazy or coastal conditions."""


class MoonlightPolicy(str, Enum):
    """
    RITE: The Moonlight Gate — the admitted selection between moonlight treatment regimes.

    THEOREM: Str-enum declaring whether the Krisciunas & Schaefer (1991)
    moonlight sky-brightness penalty is applied or suppressed.

    RITE OF PURPOSE:
        Controls whether and how the Moon's contribution to sky brightness
        reduces the effective limiting magnitude during a visibility assessment.
        An explicit named gate prevents silent activation of the K&S 1991 model
        when the caller has not declared a moonlight policy, and keeps the
        computational regime visible in policy rather than hidden behind a boolean.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the two admitted moonlight treatment regimes.
            - Serve as the moonlight_policy field of VisibilityPolicy.
        Non-responsibilities:
            - Does not implement the K&S 1991 computation (handled by
              _ks1991_limiting_magnitude_penalty()).
            - Does not control the extinction coefficient used by K&S 1991
              (that is VisibilityPolicy.extinction_coefficient_k).
        Dependencies:
            - None.  Pure enum.

    Canon: Krisciunas, K. & Schaefer, B.E. (1991), PASP 103, 1033–1039
           (for the KRISCIUNAS_SCHAEFER_1991 member).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.MoonlightPolicy",
        "risk": "low",
        "api": {
            "members": ["IGNORE", "KRISCIUNAS_SCHAEFER_1991"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid string construction"],
            "policy": "str-enum construction validates implicitly"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    IGNORE = "ignore"
    KRISCIUNAS_SCHAEFER_1991 = "krisciunas_schaefer_1991"


@dataclass(frozen=True, slots=True)
class AtmosphericExtinctionAssessment:
    """Auditable direct-beam extinction for one apparent line of sight.

    Component fields are populated only for
    :attr:`VisibilityExtinctionModel.SCHAEFER_1993_COMPONENTS`.  The
    Kasten--Young broadband path instead populates ``broadband_airmass`` and
    applies the caller-declared measured coefficient without inventing a
    spectral decomposition.  For Schaefer's component path,
    ``total_zenith_extinction_coefficient`` is the scotopic coefficient used
    for direct target extinction, while
    ``sky_brightness_extinction_coefficient`` retains the visual-band
    coefficient required by the paper's nanolambert sky-brightness equations.
    """

    model: VisibilityExtinctionModel
    apparent_altitude_deg: float
    zenith_distance_deg: float
    broadband_airmass: float | None
    rayleigh_airmass: float | None
    aerosol_airmass: float | None
    ozone_airmass: float | None
    rayleigh_coefficient_mag_per_airmass: float | None
    aerosol_coefficient_mag_per_airmass: float | None
    ozone_coefficient_mag_per_airmass: float | None
    total_zenith_extinction_coefficient: float
    sky_brightness_extinction_coefficient: float
    extinction_magnitude: float
    transmission_fraction: float


@dataclass(frozen=True, slots=True)
class TwilightSkyBrightnessAssessment:
    """Directional cloudless-sky twilight contribution from Schaefer (1993).

    ``formula_applied`` is false after astronomical twilight, where the
    contribution is explicitly zero, and while the Sun is above the horizon,
    where the admitted twilight formula is not valid and ``sky_nanolamberts``
    is ``None``.
    """

    model: VisibilityTwilightModel
    target_altitude_deg: float
    sun_altitude_deg: float
    sun_target_separation_deg: float
    sky_airmass: float
    extinction_coefficient: float
    formula_applied: bool
    valid: bool
    reason: str | None
    sky_nanolamberts: float | None


@dataclass(frozen=True, slots=True)
class PointSourceVisibilityThreshold:
    """Crumey (2014) scotopic naked-eye point-source threshold.

    A result outside Crumey's published background-luminance interval remains
    inspectable but is marked invalid and carries no limiting magnitude.  Moira
    does not silently extrapolate that fit.  ``field_factor`` is Crumey's
    overall ``F``: it may include target spectrum, observing medium,
    laboratory scaling, detection practice, and observer physiology.
    """

    criterion_family: VisibilityCriterionFamily
    background_nanolamberts: float
    background_luminance_cd_m2: float
    field_factor: float
    valid_background_min_cd_m2: float
    valid_background_max_cd_m2: float
    valid: bool
    reason: str | None
    limiting_magnitude: float | None


@dataclass(frozen=True, slots=True)
class PhysicalAtmosphereInput:
    """Complete named atmosphere requested from the first physical pack."""

    atmosphere_profile: str = "us_standard"
    aerosol_profile: str = "rural_summer"
    observer_altitude_m: float = 0.0
    surface_pressure_hpa: float = 1013.25
    aod550: float = 0.1
    angstrom_exponent: float = 1.3
    ozone_du: float = 300.0
    ground_albedo: float = 0.2

    def __post_init__(self) -> None:
        if not self.atmosphere_profile or not self.aerosol_profile:
            raise ValueError(
                "atmosphere_profile and aerosol_profile must not be empty"
            )
        for name in (
            "observer_altitude_m",
            "surface_pressure_hpa",
            "aod550",
            "angstrom_exponent",
            "ozone_du",
            "ground_albedo",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class PhysicalDirectionalBackground:
    """Source-identified response-integrated directional luminance."""

    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    scope: PhysicalBackgroundScope
    component_ids: tuple[str, ...]
    source_id: str
    source_receipt_sha256: str
    method_id: str
    component_inventory_complete: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.scope, PhysicalBackgroundScope):
            object.__setattr__(
                self,
                "scope",
                PhysicalBackgroundScope(self.scope),
            )
        _DirectionalLuminance(
            photopic_luminance_cd_m2=self.photopic_luminance_cd_m2,
            scotopic_luminance_cd_m2=self.scotopic_luminance_cd_m2,
            scope=self.scope.value,
            component_ids=self.component_ids,
            source_id=self.source_id,
            source_receipt_sha256=self.source_receipt_sha256,
            method_id=self.method_id,
            component_inventory_complete=(
                self.component_inventory_complete
            ),
        )


@dataclass(frozen=True, slots=True)
class PhysicalModeledBackgroundComponent:
    """One caller-supplied directional output from a named sky model."""

    component_kind: PhysicalBackgroundComponentKind
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    model_id: str
    source_ids: tuple[str, ...]
    source_receipt_sha256: str
    spatial_applicability_id: str
    temporal_applicability_id: str
    direction_receipt_id: str
    validity_domain_id: str
    uncertainty_authority_id: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.component_kind,
            PhysicalBackgroundComponentKind,
        ):
            object.__setattr__(
                self,
                "component_kind",
                PhysicalBackgroundComponentKind(self.component_kind),
            )
        try:
            source_ids = tuple(self.source_ids)
        except TypeError as exc:
            raise TypeError(
                "source_ids must be an iterable of strings"
            ) from exc
        object.__setattr__(self, "source_ids", source_ids)
        ModeledDirectionalBackgroundComponent(
            component_id=self.component_kind.value,
            photopic_luminance_cd_m2=(
                self.photopic_luminance_cd_m2
            ),
            scotopic_luminance_cd_m2=(
                self.scotopic_luminance_cd_m2
            ),
            model_id=self.model_id,
            source_ids=source_ids,
            source_receipt_sha256=self.source_receipt_sha256,
            spatial_applicability_id=self.spatial_applicability_id,
            temporal_applicability_id=self.temporal_applicability_id,
            direction_receipt_id=self.direction_receipt_id,
            validity_domain_id=self.validity_domain_id,
            uncertainty_authority_id=self.uncertainty_authority_id,
        )


@dataclass(frozen=True, slots=True)
class PhysicalSqmBackground:
    """Fully qualified SQM/V-equivalent directional background input."""

    sqm_mag_arcsec2: float
    scotopic_to_photopic_ratio: float
    scope: PhysicalBackgroundScope
    component_ids: tuple[str, ...]
    measurement_source_id: str
    measurement_receipt_sha256: str
    device_bandpass_id: str
    pointing_receipt_id: str
    temporal_applicability_id: str
    spectral_ratio_source_id: str
    component_inventory_complete: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.scope, PhysicalBackgroundScope):
            object.__setattr__(
                self,
                "scope",
                PhysicalBackgroundScope(self.scope),
            )
        sqm_directional_luminance(
            self.sqm_mag_arcsec2,
            scotopic_to_photopic_ratio=(
                self.scotopic_to_photopic_ratio
            ),
            scope=self.scope.value,
            component_ids=self.component_ids,
            measurement_source_id=self.measurement_source_id,
            measurement_receipt_sha256=(
                self.measurement_receipt_sha256
            ),
            device_bandpass_id=self.device_bandpass_id,
            pointing_receipt_id=self.pointing_receipt_id,
            temporal_applicability_id=self.temporal_applicability_id,
            spectral_ratio_source_id=self.spectral_ratio_source_id,
            component_inventory_complete=(
                self.component_inventory_complete
            ),
        )


@dataclass(frozen=True, slots=True)
class PhysicalBortleBackground:
    """Explicit coarse Bortle dark-sky anchor with an S/P assumption."""

    light_pollution_class: LightPollutionClass
    scotopic_to_photopic_ratio: float
    spectral_ratio_source_id: str
    source_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.light_pollution_class,
            LightPollutionClass,
        ):
            object.__setattr__(
                self,
                "light_pollution_class",
                LightPollutionClass(self.light_pollution_class),
            )
        if (
            not math.isfinite(self.scotopic_to_photopic_ratio)
            or self.scotopic_to_photopic_ratio <= 0.0
        ):
            raise ValueError(
                "scotopic_to_photopic_ratio must be finite and > 0"
            )
        if not self.spectral_ratio_source_id:
            raise ValueError(
                "spectral_ratio_source_id must not be empty"
            )
        _validate_physical_sha256(
            self.source_receipt_sha256,
            "source_receipt_sha256",
        )


@dataclass(frozen=True, slots=True)
class PhysicalHorizonSample:
    """One apparent-altitude obstruction sample on the local horizon."""

    azimuth_deg: float
    apparent_altitude_deg: float

    def __post_init__(self) -> None:
        for name in ("azimuth_deg", "apparent_altitude_deg"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{name} must be finite")
        normalized = float(self.azimuth_deg) % 360.0
        if normalized >= 360.0:
            normalized = 0.0
        if normalized == 0.0:
            normalized = 0.0
        altitude = float(self.apparent_altitude_deg)
        if not -5.0 <= altitude < 90.0:
            raise ValueError(
                "apparent_altitude_deg must be in [-5, 90)"
            )
        object.__setattr__(self, "azimuth_deg", normalized)
        object.__setattr__(self, "apparent_altitude_deg", altitude)


def _physical_horizon_cone_factor(
    samples: tuple[PhysicalHorizonSample, ...],
    maximum_absolute_slope_deg_per_deg: float,
    *,
    additional_constant_altitude_deg: float | None = None,
) -> float:
    altitudes = [
        sample.apparent_altitude_deg for sample in samples
    ]
    if additional_constant_altitude_deg is not None:
        altitudes.append(additional_constant_altitude_deg)
    maximum_absolute_tangent = max(
        abs(math.tan(math.radians(altitude)))
        for altitude in altitudes
    )
    maximum_secant_squared = max(
        1.0
        / (math.cos(math.radians(altitude)) ** 2)
        for altitude in altitudes
    )
    return math.hypot(
        maximum_absolute_tangent,
        maximum_secant_squared
        * maximum_absolute_slope_deg_per_deg,
    )


@dataclass(frozen=True, slots=True)
class PhysicalHorizonProfile:
    """Source-identified circular linear terrain-horizon profile."""

    samples: tuple[PhysicalHorizonSample, ...]
    profile_id: str
    source_id: str
    source_receipt_sha256: str
    interpolation_method_id: str = field(
        init=False,
        default="circular_linear_azimuth_v1",
    )
    admitted_maximum_gap_deg: float = field(
        init=False,
        default=10.0,
    )
    actual_maximum_gap_deg: float = field(init=False)
    maximum_absolute_slope_deg_per_deg: float = field(init=False)
    cone_signal_lipschitz_factor: float = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ValueError("profile_id must not be empty")
        if not isinstance(self.source_id, str) or not self.source_id:
            raise ValueError("source_id must not be empty")
        _validate_physical_sha256(
            self.source_receipt_sha256,
            "source_receipt_sha256",
        )
        try:
            samples = tuple(self.samples)
        except TypeError as exc:
            raise TypeError(
                "samples must be an iterable of PhysicalHorizonSample"
            ) from exc
        if any(
            not isinstance(sample, PhysicalHorizonSample)
            for sample in samples
        ):
            raise TypeError(
                "samples must contain only PhysicalHorizonSample values"
            )
        samples = tuple(
            sorted(samples, key=lambda sample: sample.azimuth_deg)
        )
        if len(samples) < 2:
            raise ValueError("horizon profile requires at least two samples")
        azimuths = tuple(sample.azimuth_deg for sample in samples)
        if len(set(azimuths)) != len(azimuths):
            raise ValueError(
                "horizon profile contains duplicate normalized azimuths"
            )

        gaps: list[float] = []
        slopes: list[float] = []
        for index, sample in enumerate(samples):
            next_sample = samples[(index + 1) % len(samples)]
            next_azimuth = next_sample.azimuth_deg
            if index == len(samples) - 1:
                next_azimuth += 360.0
            gap = next_azimuth - sample.azimuth_deg
            if gap <= 0.0:
                raise ValueError(
                    "horizon profile azimuths must advance circularly"
                )
            gaps.append(gap)
            slope = abs(
                (
                    next_sample.apparent_altitude_deg
                    - sample.apparent_altitude_deg
                )
                / gap
            )
            if not math.isfinite(slope):
                raise ValueError(
                    "horizon profile interpolation slope must be finite"
                )
            slopes.append(slope)

        actual_maximum_gap = max(gaps)
        if (
            actual_maximum_gap
            > self.admitted_maximum_gap_deg + 1.0e-12
        ):
            raise ValueError(
                "horizon profile has an azimuth gap larger than "
                f"{self.admitted_maximum_gap_deg:g} degrees"
            )
        object.__setattr__(self, "samples", samples)
        object.__setattr__(
            self,
            "actual_maximum_gap_deg",
            actual_maximum_gap,
        )
        object.__setattr__(
            self,
            "maximum_absolute_slope_deg_per_deg",
            max(slopes),
        )
        cone_signal_lipschitz_factor = _physical_horizon_cone_factor(
            samples,
            max(slopes),
        )
        if not math.isfinite(cone_signal_lipschitz_factor):
            raise ValueError(
                "horizon profile cone-signal bound must be finite"
            )
        object.__setattr__(
            self,
            "cone_signal_lipschitz_factor",
            cone_signal_lipschitz_factor,
        )

    def apparent_altitude_at(self, azimuth_deg: float) -> float:
        """Interpolate the circular profile at one normalized azimuth."""

        if (
            isinstance(azimuth_deg, bool)
            or not isinstance(azimuth_deg, (int, float))
            or not math.isfinite(azimuth_deg)
        ):
            raise ValueError("azimuth_deg must be finite")
        query = float(azimuth_deg) % 360.0
        if query >= 360.0:
            query = 0.0
        azimuths = tuple(
            sample.azimuth_deg for sample in self.samples
        )
        lower_index = bisect_right(azimuths, query) - 1
        if lower_index < 0:
            lower_index = len(self.samples) - 1
        upper_index = (lower_index + 1) % len(self.samples)
        lower = self.samples[lower_index]
        upper = self.samples[upper_index]
        lower_azimuth = lower.azimuth_deg
        upper_azimuth = upper.azimuth_deg
        adjusted_query = query
        if upper_index == 0:
            upper_azimuth += 360.0
            if adjusted_query < lower_azimuth:
                adjusted_query += 360.0
        fraction = (
            (adjusted_query - lower_azimuth)
            / (upper_azimuth - lower_azimuth)
        )
        return lower.apparent_altitude_deg + fraction * (
            upper.apparent_altitude_deg
            - lower.apparent_altitude_deg
        )


PhysicalBackgroundInput = (
    PhysicalDirectionalBackground
    | PhysicalSqmBackground
    | PhysicalBortleBackground
)


@dataclass(frozen=True, slots=True)
class PhysicalVisibilityPolicy:
    """Versioned additive policy for physical single-epoch truth."""

    background: PhysicalBackgroundInput | None = None
    atmosphere: PhysicalAtmosphereInput = field(
        default_factory=PhysicalAtmosphereInput
    )
    composite_model_id: str = (
        "clear_sky_naked_eye_point_source_v1"
    )
    expected_data_pack_id: str = (
        "moira-physical-heliacal-visibility"
    )
    expected_manifest_sha256: str | None = None
    observer_protocol_id: str = (
        "known_location_directed_averted_observation_v1"
    )
    local_horizon_altitude_deg: float = 0.0
    refraction_model_id: str = "bennett_extended_v1"
    refraction_pressure_hpa: float = 1013.25
    refraction_temperature_c: float = 15.0
    refraction_relative_humidity: float = 0.0
    directional_horizon: PhysicalHorizonProfile | None = None
    modeled_background_components: tuple[
        PhysicalModeledBackgroundComponent,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.atmosphere, PhysicalAtmosphereInput):
            raise TypeError(
                "atmosphere must be a PhysicalAtmosphereInput"
            )
        if self.background is not None and not isinstance(
            self.background,
            (
                PhysicalDirectionalBackground,
                PhysicalSqmBackground,
                PhysicalBortleBackground,
            ),
        ):
            raise TypeError("unsupported physical background input")
        if (
            self.composite_model_id
            != "clear_sky_naked_eye_point_source_v1"
        ):
            raise ValueError("unsupported physical composite_model_id")
        if (
            self.expected_data_pack_id
            != "moira-physical-heliacal-visibility"
        ):
            raise ValueError("unsupported expected_data_pack_id")
        if (
            self.observer_protocol_id
            != "known_location_directed_averted_observation_v1"
        ):
            raise ValueError("unsupported observer_protocol_id")
        if self.refraction_model_id != "bennett_extended_v1":
            raise ValueError("unsupported refraction_model_id")
        try:
            modeled_components = tuple(
                self.modeled_background_components
            )
        except TypeError as exc:
            raise TypeError(
                "modeled_background_components must be an iterable of "
                "PhysicalModeledBackgroundComponent values"
            ) from exc
        if any(
            not isinstance(
                component,
                PhysicalModeledBackgroundComponent,
            )
            for component in modeled_components
        ):
            raise TypeError(
                "modeled_background_components must contain only "
                "PhysicalModeledBackgroundComponent values"
            )
        object.__setattr__(
            self,
            "modeled_background_components",
            modeled_components,
        )
        if (
            self.directional_horizon is not None
            and not isinstance(
                self.directional_horizon,
                PhysicalHorizonProfile,
            )
        ):
            raise TypeError(
                "directional_horizon must be a PhysicalHorizonProfile"
            )
        if self.expected_manifest_sha256 is not None:
            _validate_physical_sha256(
                self.expected_manifest_sha256,
                "expected_manifest_sha256",
            )
        if (
            not math.isfinite(self.local_horizon_altitude_deg)
            or not -5.0 <= self.local_horizon_altitude_deg <= 90.0
        ):
            raise ValueError(
                "local_horizon_altitude_deg must be in [-5, 90]"
            )
        if (
            self.directional_horizon is not None
            and self.local_horizon_altitude_deg != 0.0
        ):
            raise ValueError(
                "directional_horizon cannot be combined with a nonzero "
                "scalar local_horizon_altitude_deg"
            )
        if (
            not math.isfinite(self.refraction_pressure_hpa)
            or self.refraction_pressure_hpa <= 0.0
        ):
            raise ValueError(
                "refraction_pressure_hpa must be finite and > 0"
            )
        if not math.isfinite(self.refraction_temperature_c):
            raise ValueError(
                "refraction_temperature_c must be finite"
            )
        if (
            not math.isfinite(self.refraction_relative_humidity)
            or not 0.0 <= self.refraction_relative_humidity <= 1.0
        ):
            raise ValueError(
                "refraction_relative_humidity must be in [0, 1]"
            )


@dataclass(frozen=True, slots=True)
class PhysicalVisibilitySearchPolicy:
    """Deterministic search and refinement policy for physical events."""

    search_window_days: int = 400
    scan_step_days: float = 5.0 / 1440.0
    adaptive_minimum_step_days: float = 30.0 / 86400.0
    root_time_tolerance_days: float = 0.25 / 86400.0
    root_margin_tolerance_magnitude: float = 1.0e-5
    near_zero_tolerance_magnitude: float = 2.5e-3
    curvature_tolerance_magnitude: float = 5.0e-3
    maximum_adaptive_depth: int = 12
    maximum_root_iterations: int = 96

    def __post_init__(self) -> None:
        if (
            isinstance(self.search_window_days, bool)
            or not isinstance(self.search_window_days, int)
            or self.search_window_days <= 0
        ):
            raise ValueError(
                "search_window_days must be a positive integer"
            )
        self._scalar_policy()

    def _scalar_policy(self) -> _ScalarSearchPolicy:
        return _ScalarSearchPolicy(
            scan_step_days=self.scan_step_days,
            adaptive_minimum_step_days=(
                self.adaptive_minimum_step_days
            ),
            root_time_tolerance_days=self.root_time_tolerance_days,
            root_value_tolerance=(
                self.root_margin_tolerance_magnitude
            ),
            near_zero_tolerance=(
                self.near_zero_tolerance_magnitude
            ),
            curvature_tolerance=(
                self.curvature_tolerance_magnitude
            ),
            maximum_adaptive_depth=self.maximum_adaptive_depth,
            maximum_root_iterations=self.maximum_root_iterations,
        )


@dataclass(frozen=True, slots=True)
class VisibilityComponentReceipt:
    """Public receipt for one effective physical-model component."""

    role: str
    component_id: str
    source_ids: tuple[str, ...]
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class PhysicalAtmosphereReceipt:
    """Resolved atmosphere completeness and pack-domain truth."""

    complete: bool
    within_data_pack_domain: bool | None
    atmosphere_profile: str
    aerosol_profile: str
    observer_altitude_m: float
    surface_pressure_hpa: float
    aod550: float
    angstrom_exponent: float
    ozone_du: float
    ground_albedo: float


@dataclass(frozen=True, slots=True)
class PhysicalValidityDomainReceipt:
    """Exact data-pack axes and queried geometry."""

    no_extrapolation: bool
    solar_center_altitude_domain_deg: tuple[float, float]
    target_true_altitude_domain_deg: tuple[float, float]
    relative_solar_azimuth_domain_deg: tuple[float, float]
    queried_solar_center_altitude_deg: float | None
    queried_target_true_altitude_deg: float | None
    queried_relative_solar_azimuth_deg: float | None
    within_domain: bool | None


@dataclass(frozen=True, slots=True)
class PhysicalObserverProtocolReceipt:
    """Fixed task, adaptation-field, horizon, and refraction receipt."""

    protocol_id: str
    task: str
    optical_aid: str
    adaptation_field: str
    local_horizon_altitude_deg: float
    refraction_model_id: str
    refraction_pressure_hpa: float
    refraction_temperature_c: float
    refraction_relative_humidity: float
    horizon_model_id: str = "scalar_apparent_horizon_v1"
    directional_profile_applied: bool = False
    directional_profile_id: str | None = None
    directional_profile_source_id: str | None = None
    directional_profile_source_receipt_sha256: str | None = None
    detection_field_factor_model_id: str = (
        "crumey_2014_equation_53_fixed_notional_f2_v1"
    )
    detection_field_factor_value: float = 2.0
    detection_field_factor_mutable: bool = False
    detection_field_factor_source_ids: tuple[str, ...] = (
        "Crumey:2014:equation_53",
        "Crumey:2014:notional_field_factor_F_2",
    )
    probabilistic_detection_claimed: bool = False


@dataclass(frozen=True, slots=True)
class PhysicalBackgroundReceipt:
    """Effective background and CIE adaptation receipt."""

    authority_id: str
    component_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    mesopic_luminance_cd_m2: float
    scotopic_to_photopic_ratio: float
    adaptation_coefficient: float
    weighting_state: str
    adaptation_solver_method: str
    photopic_solver_relative_standard_error_bound: float | None
    scotopic_solver_relative_standard_error_bound: float | None
    solver_uncertainty_bound_method: str | None
    photopic_interpolation_maximum_error_mag: float | None
    photopic_interpolation_p95_error_mag: float | None
    scotopic_interpolation_maximum_error_mag: float | None
    scotopic_interpolation_p95_error_mag: float | None
    storage_maximum_error_mag: float | None
    component_inventory_complete: bool = False
    modeled_component_count: int = 0


@dataclass(frozen=True, slots=True)
class PhysicalTargetReceipt:
    """Dynamic photometry, spectrum, and atmospheric conditioning receipt."""

    target_id: str
    photometry_model_id: str
    photometry_source_ids: tuple[str, ...]
    spectral_profile_id: str
    spectral_source_ids: tuple[str, ...]
    spectral_source_receipt_sha256: str
    spectral_model_details: tuple[tuple[str, str], ...]
    top_of_atmosphere_visual_magnitude: float
    scotopic_to_photopic_ratio: float
    photopic_transmission: float
    scotopic_transmission: float
    conditioned_target_magnitude: float
    direct_interpolation_maximum_error_mag: float
    direct_interpolation_p95_error_mag: float
    storage_maximum_error_mag: float


@dataclass(frozen=True, slots=True)
class PhysicalThresholdReceipt:
    """Full-range point-source threshold and its fixed field factor."""

    model_id: str
    background_luminance_cd_m2: float
    field_factor: float
    threshold_illuminance_lux: float
    limiting_magnitude: float
    valid_background_min_cd_m2: float
    valid_background_max_cd_m2: float
    equation_receipt: str


@dataclass(frozen=True, slots=True)
class PhysicalVisibilityErrorBudgetReceipt:
    """Declared pack-numerical envelope, not scientific confidence."""

    method_id: str
    background_error_authority: str
    solver_relative_standard_error_multiplier: float | None
    background_mesopic_luminance_envelope_lower_cd_m2: float
    background_mesopic_luminance_envelope_upper_cd_m2: float
    limiting_magnitude_envelope_lower: float
    limiting_magnitude_envelope_upper: float
    conditioned_target_magnitude_maximum_pack_error: float
    visibility_margin_envelope_lower_magnitude: float
    visibility_margin_envelope_upper_magnitude: float
    visibility_margin_envelope_maximum_deviation_magnitude: float
    visibility_classification_within_data_pack_envelope: str
    included_error_sources: tuple[str, ...]
    unquantified_error_sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PhysicalVisibilityAssessment:
    """Additive typed result for one physical single-epoch assessment."""

    body: str
    jd_ut: float
    latitude_deg: float
    longitude_deg: float
    status: PhysicalVisibilityStatus
    evidence_state: PhysicalVisibilityEvidenceState
    reason: str | None
    true_target_altitude_deg: float | None
    apparent_target_altitude_deg: float | None
    true_solar_center_altitude_deg: float | None
    relative_solar_azimuth_deg: float | None
    geometrically_visible: bool | None
    visible: bool | None
    observable: bool | None
    visibility_margin_magnitude: float | None
    data_pack_receipt: VisibilityDataPackReceipt | None
    atmosphere_receipt: PhysicalAtmosphereReceipt
    validity_domain_receipt: PhysicalValidityDomainReceipt | None
    observer_protocol_receipt: PhysicalObserverProtocolReceipt
    background_receipt: PhysicalBackgroundReceipt | None
    target_receipt: PhysicalTargetReceipt | None
    threshold_receipt: PhysicalThresholdReceipt | None
    error_budget_receipt: PhysicalVisibilityErrorBudgetReceipt | None
    components: tuple[VisibilityComponentReceipt, ...]
    horizon_receipt: PhysicalHorizonReceipt | None = None


@dataclass(frozen=True, slots=True)
class PhysicalObservationWindowReceipt:
    """Exact target-horizon-connected interval used by an event search."""

    observation_day_key: int
    start_jd_ut: float
    end_jd_ut: float
    target_boundary_jd_ut: float
    target_boundary_role: str
    solar_side: str


@dataclass(frozen=True, slots=True)
class PhysicalEventSolverReceipt:
    """Numerical search receipt, separate from scientific sensitivity."""

    search_window_days: int
    scan_step_days: float
    bracket_tolerance_days: float
    adaptive_minimum_step_days: float
    root_time_tolerance_days: float
    root_margin_tolerance_magnitude: float
    near_zero_tolerance_magnitude: float
    curvature_tolerance_magnitude: float
    candidate_day_count: int
    guard_day_count: int
    classified_day_count: int
    evaluable_day_count: int
    observation_window_count: int
    scalar_evaluation_count: int
    sign_changing_root_count: int
    tangent_root_count: int
    near_zero_interval_count: int
    non_evaluable_gap_count: int
    maximum_sample_gap_days: float | None
    classified_day_states: tuple[
        tuple[int, str, str | None, str | None],
        ...,
    ]
    non_evaluable_day_states: tuple[
        tuple[int, str, str | None],
        ...,
    ]
    crossing_completeness_state: str
    crossing_completeness_reason: str | None
    crossing_certificate_ids: tuple[str, ...] = ()
    crossing_certificate_source_sha256: str | None = None
    root_enclosure_count: int = 0
    unresolved_certificate_interval_count: int = 0


@dataclass(frozen=True, slots=True)
class PhysicalEventSensitivityReceipt:
    """Deterministic sensitivity state, never probabilistic confidence."""

    data_pack_numerical_event_interval_jd_ut: (
        tuple[float, float] | None
    )
    data_pack_numerical_reason: str | None
    atmospheric_scenario_event_interval_jd_ut: (
        tuple[float, float] | None
    )
    atmospheric_scenario_reason: str | None
    probabilistic_confidence_claimed: bool


@dataclass(frozen=True, slots=True)
class PhysicalHorizonReceipt:
    """Apparent terrain-horizon and refraction boundary identity."""

    horizon_model_id: str
    apparent_horizon_altitude_deg: float | None
    directional_profile_applied: bool
    refraction_model_id: str
    refraction_pressure_hpa: float
    refraction_temperature_c: float
    refraction_relative_humidity: float
    applied_to: tuple[str, ...]
    target_apparent_boundary_altitude_deg: float | None = None
    solar_apparent_horizon_altitude_deg: float | None = None
    data_pack_target_true_altitude_floor_deg: float | None = None
    target_boundary_narrowing_applied: bool = False
    directional_profile_id: str | None = None
    directional_profile_source_id: str | None = None
    directional_profile_source_receipt_sha256: str | None = None
    interpolation_method_id: str | None = None
    profile_sample_count: int | None = None
    admitted_maximum_gap_deg: float | None = None
    actual_maximum_gap_deg: float | None = None
    maximum_absolute_slope_deg_per_deg: float | None = None
    cone_signal_lipschitz_factor: float | None = None
    queried_target_azimuth_deg: float | None = None
    queried_solar_azimuth_deg: float | None = None
    target_local_horizon_altitude_deg: float | None = None
    solar_local_horizon_altitude_deg: float | None = None
    event_certificate_id: str | None = None
    event_certificate_source_sha256: str | None = None
    event_certificate_maximum_absolute_rate_per_day: float | None = None


@dataclass(frozen=True, slots=True)
class PhysicalEphemerisReceipt:
    """Ephemeris and horizontal-frame identity used by the event solver."""

    provider_id: str
    input_timescale: str
    ephemeris_timescale: str
    direction_frame: str
    horizontal_frame: str
    refraction_applied_separately: bool


@dataclass(frozen=True, slots=True)
class PhysicalVisibilityEventResult:
    """Additive typed result for one four-phase physical event search."""

    body: str
    phase: PhysicalVisibilityPhase
    latitude_deg: float
    longitude_deg: float
    status: PhysicalVisibilityStatus
    evidence_state: PhysicalVisibilityEvidenceState
    reason: str | None
    observation_day_key: int | None
    comparison_observation_day_key: int | None
    comparison_day_status: str | None
    event_jd_ut: float | None
    event_time_semantics: PhysicalEventTimeSemantics | None
    target_horizon_jd_ut: float | None
    peak_margin_jd_ut: float | None
    peak_margin_magnitude: float | None
    boundary_role: str | None
    crossing_direction: PhysicalVisibilityCrossingDirection | None
    boundary_source: PhysicalVisibilityBoundarySource | None
    visibility_margin_residual_magnitude: float | None
    visibility_margin_bracket_jd_ut: tuple[float, float] | None
    root_iterations: int | None
    derived_arcus_deg: float | None
    assessment_jd_ut: float | None
    observation_window: PhysicalObservationWindowReceipt | None
    event_assessment: PhysicalVisibilityAssessment | None
    data_pack_receipt: VisibilityDataPackReceipt | None
    atmosphere_receipt: PhysicalAtmosphereReceipt
    observer_protocol_receipt: PhysicalObserverProtocolReceipt
    horizon_receipt: PhysicalHorizonReceipt
    ephemeris_receipt: PhysicalEphemerisReceipt | None
    solver_receipt: PhysicalEventSolverReceipt
    sensitivity_receipt: PhysicalEventSensitivityReceipt
    components: tuple[VisibilityComponentReceipt, ...]


@dataclass(frozen=True, slots=True)
class ObserverVisibilityEnvironment:
    """
    RITE: The Observer Environment Vessel — the complete typed environment declaration
    for one observing site and sky condition.

    THEOREM: Immutable frozen dataclass carrying the observer's physical site
    environment parameters required by the generalized visibility criterion family.

    RITE OF PURPOSE:
        Separates the observer's physical environment (site darkness, horizon,
        atmosphere, instrument) from the computational visibility policy so that
        each layer can be constructed and inspected independently.  Without this
        vessel, environment state would be embedded alongside computational policy
        choices, making it impossible to reuse a site environment across multiple
        criterion families.

    LAW OF OPERATION:
        Responsibilities:
            - Carry site darkness class, an explicit limiting magnitude or
              measured sky-surface brightness, local horizon altitude,
              atmospheric parameters, and observing aid.
            - Validate relative_humidity, pressure_mbar, and
              observer_altitude_m on construction.
            - Serve as the environment field of VisibilityPolicy.
        Non-responsibilities:
            - Does not compute limiting magnitude (delegated to
              _effective_limiting_magnitude()).
            - Does not decide whether atmospheric refraction is applied
              (VisibilityPolicy.use_refraction governs that assessment step).
            - Does not carry geographic coordinates (those are function arguments).
        Dependencies:
            - LightPollutionClass, ObserverAid (enum dependencies only).
        Behavioral invariants:
            - limiting_magnitude, when provided, must be finite.
            - relative_humidity ∈ [0, 1].
            - pressure_mbar ≥ 0.
            - observer_altitude_m ≥ −1000 m.

    Canon: None (No applicable canon; synthesis of standard atmospheric and
           observational parameters).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.ObserverVisibilityEnvironment",
        "risk": "low",
        "api": {
            "public_attributes": [
                "light_pollution_class", "limiting_magnitude",
                "sky_surface_brightness_mag_arcsec2",
                "local_horizon_altitude_deg", "temperature_c",
                "pressure_mbar", "relative_humidity",
                "observer_altitude_m", "observing_aid"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError on invalid humidity, pressure, or altitude"],
            "policy": "__post_init__ enforces physical plausibility bounds"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    light_pollution_class: LightPollutionClass | None = LightPollutionClass.BORTLE_3
    limiting_magnitude: float | None = None
    sky_surface_brightness_mag_arcsec2: float | None = None
    local_horizon_altitude_deg: float = 0.0
    temperature_c: float = 10.0
    pressure_mbar: float = 1013.25
    relative_humidity: float = 0.5
    observer_altitude_m: float = 0.0
    observing_aid: ObserverAid = ObserverAid.NAKED_EYE

    def __post_init__(self) -> None:
        if self.limiting_magnitude is not None and not math.isfinite(self.limiting_magnitude):
            raise ValueError("limiting_magnitude must be finite when provided")
        if (
            self.sky_surface_brightness_mag_arcsec2 is not None
            and (
                not math.isfinite(self.sky_surface_brightness_mag_arcsec2)
                or self.sky_surface_brightness_mag_arcsec2 <= 0.0
            )
        ):
            raise ValueError(
                "sky_surface_brightness_mag_arcsec2 must be finite and > 0 when provided"
            )
        if (
            not math.isfinite(self.local_horizon_altitude_deg)
            or not -90.0 <= self.local_horizon_altitude_deg <= 90.0
        ):
            raise ValueError(
                "local_horizon_altitude_deg must be finite and in [-90, 90]"
            )
        if not math.isfinite(self.temperature_c):
            raise ValueError("temperature_c must be finite")
        if (
            not math.isfinite(self.relative_humidity)
            or not 0.0 <= self.relative_humidity <= 1.0
        ):
            raise ValueError("relative_humidity must be finite and in [0, 1]")
        if not math.isfinite(self.pressure_mbar) or self.pressure_mbar < 0.0:
            raise ValueError("pressure_mbar must be finite and >= 0")
        if (
            not math.isfinite(self.observer_altitude_m)
            or self.observer_altitude_m < -1000.0
        ):
            raise ValueError(
                "observer_altitude_m must be finite and >= -1000"
            )


@dataclass(frozen=True, slots=True)
class VisibilityPolicy:
    """
    RITE: The Visibility Doctrine — the unified policy vessel for generalized
    observability decisions.

    THEOREM: Immutable frozen dataclass carrying the complete set of doctrinal
    choices governing how a body's observability is assessed or searched.

    RITE OF PURPOSE:
        Gathers criterion family, observer environment, sky model choices,
        extinction treatment, twilight model, and moonlight policy into a single
        typed, immutable policy object so that every visibility assessment is
        driven by an explicit, inspectable, reproducible doctrine.  Without this
        unification, the same parameters would need to be threaded as individual
        keyword arguments across every call site, obscuring the operational
        doctrine and making policy changes non-atomic.

    LAW OF OPERATION:
        Responsibilities:
            - Carry all doctrinal choices for an observability assessment or event
              search in one immutable vessel.
            - Default environment to ObserverVisibilityEnvironment() when None.
            - Enforce that YALLOP_LUNAR_CRESCENT requires the standard twilight
              model slot.
        Non-responsibilities:
            - Does not compute sky brightness, limiting magnitude, or
              observability.
            - Does not carry geographic coordinates (those are function arguments).
            - Does not govern stellar heliacal event search (that uses
              FixedStarComputationPolicy in star_types.py).
        Dependencies:
            - VisibilityCriterionFamily, ObserverVisibilityEnvironment,
              LightPollutionDerivationMode, VisibilityExtinctionModel,
              VisibilityTwilightModel, MoonlightPolicy.
        Behavioral invariants:
            - environment is never None after construction.
            - YALLOP_LUNAR_CRESCENT + non-standard twilight_model raises
              ValueError on construction.

    Canon: None (No applicable canon; unified design synthesis).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.VisibilityPolicy",
        "risk": "medium",
        "api": {
            "public_attributes": [
                "criterion_family", "environment",
                "light_pollution_derivation_mode", "extinction_model",
                "twilight_model", "use_refraction", "moonlight_policy",
                "extinction_coefficient_k", "crumey_field_factor",
                "crumey_field_factor_includes_atmosphere"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError for incompatible criterion/model/environment combinations"],
            "policy": "__post_init__ enforces coherent declared model combinations"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    criterion_family: VisibilityCriterionFamily = VisibilityCriterionFamily.LIMITING_MAGNITUDE_THRESHOLD
    environment: ObserverVisibilityEnvironment | None = None
    light_pollution_derivation_mode: LightPollutionDerivationMode = LightPollutionDerivationMode.BORTLE_LINEAR
    extinction_model: VisibilityExtinctionModel = VisibilityExtinctionModel.LEGACY_ARCUS_VISIONIS
    twilight_model: VisibilityTwilightModel = VisibilityTwilightModel.ARCUS_VISIONIS_SOLAR_DEPRESSION
    use_refraction: bool = True
    moonlight_policy: MoonlightPolicy = MoonlightPolicy.IGNORE
    extinction_coefficient_k: float = 0.20
    """Broadband extinction coefficient (mag/airmass).

    This is used by the Kasten--Young direct-extinction path, Schaefer
    directional twilight path, and Krisciunas & Schaefer moonlight path.
    The Schaefer component-extinction path derives its own coefficient.
    Use the :class:`ExtinctionCoefficient` named holders for the four
    admitted reference site classes:

    - ``ExtinctionCoefficient.MAUNA_KEA``       = 0.172  (exceptional high-altitude site)
    - ``ExtinctionCoefficient.GOOD_DARK_SITE``  = 0.20   (recommended default)
    - ``ExtinctionCoefficient.TYPICAL``         = 0.25   (typical clear site)
    - ``ExtinctionCoefficient.HAZY``            = 0.30   (hazy or coastal conditions)

    The declared model combination determines whether this field is consumed.
    """
    crumey_field_factor: float = 2.0
    """Observer/field factor ``F`` in Crumey (2014), Eq. 53.

    ``2.0`` reproduces Crumey's representative naked-eye example.  The
    physical point-source criterion requires naked-eye observing and applies
    this factor exactly as declared; it is never inferred from an aid class.
    By Crumey's definition it is an overall factor that may include target
    spectrum, medium, laboratory scaling, detection practice, and observer.
    """
    crumey_field_factor_includes_atmosphere: bool = True
    """Whether Crumey's field factor already contains atmospheric target loss.

    Crumey defines ``F`` as including target, medium, laboratory-scaling, and
    observer factors, so ``True`` is the source-faithful default.  Set this to
    ``False`` only when ``crumey_field_factor`` was calibrated without
    atmospheric transmission; Moira will then apply the separately calculated
    direct extinction to the target magnitude used by the criterion.
    """

    def __post_init__(self) -> None:
        if self.environment is None:
            object.__setattr__(self, "environment", ObserverVisibilityEnvironment())
        if not isinstance(self.crumey_field_factor_includes_atmosphere, bool):
            raise ValueError(
                "crumey_field_factor_includes_atmosphere must be bool"
            )
        if not math.isfinite(self.extinction_coefficient_k) or self.extinction_coefficient_k < 0.0:
            raise ValueError("extinction_coefficient_k must be finite and >= 0")
        if not math.isfinite(self.crumey_field_factor) or self.crumey_field_factor <= 0.0:
            raise ValueError("crumey_field_factor must be finite and > 0")
        if (
            self.criterion_family is VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT
            and (
                self.extinction_model is not VisibilityExtinctionModel.LEGACY_ARCUS_VISIONIS
                or self.twilight_model
                is not VisibilityTwilightModel.ARCUS_VISIONIS_SOLAR_DEPRESSION
            )
        ):
            raise ValueError(
                "YALLOP_LUNAR_CRESCENT requires the legacy extinction and twilight slots"
            )
        if self.criterion_family is VisibilityCriterionFamily.LIMITING_MAGNITUDE_THRESHOLD:
            if (
                self.extinction_model is not VisibilityExtinctionModel.LEGACY_ARCUS_VISIONIS
                or self.twilight_model
                is not VisibilityTwilightModel.ARCUS_VISIONIS_SOLAR_DEPRESSION
            ):
                raise ValueError(
                    "LIMITING_MAGNITUDE_THRESHOLD requires the legacy extinction "
                    "and twilight slots; use CRUMEY_2014_POINT_SOURCE for the "
                    "physical atmospheric path"
                )
        if self.criterion_family is VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE:
            if self.extinction_model not in {
                VisibilityExtinctionModel.KASTEN_YOUNG_1989_BROADBAND,
                VisibilityExtinctionModel.SCHAEFER_1993_COMPONENTS,
            }:
                raise ValueError(
                    "CRUMEY_2014_POINT_SOURCE requires an admitted physical "
                    "extinction model"
                )
            if self.twilight_model is not VisibilityTwilightModel.SCHAEFER_1993_DIRECTIONAL:
                raise ValueError(
                    "CRUMEY_2014_POINT_SOURCE requires SCHAEFER_1993_DIRECTIONAL twilight"
                )
            environment = self.environment
            assert environment is not None
            if environment.limiting_magnitude is not None:
                raise ValueError(
                    "CRUMEY_2014_POINT_SOURCE derives its own limiting magnitude; "
                    "use sky_surface_brightness_mag_arcsec2, not limiting_magnitude"
                )
            if (
                environment.sky_surface_brightness_mag_arcsec2 is None
                and environment.light_pollution_class is None
            ):
                raise ValueError(
                    "CRUMEY_2014_POINT_SOURCE requires measured sky surface "
                    "brightness or a declared Bortle class"
                )
            if (
                environment.sky_surface_brightness_mag_arcsec2 is None
                and self.light_pollution_derivation_mode
                is not LightPollutionDerivationMode.BORTLE_TABLE
            ):
                raise ValueError(
                    "CRUMEY_2014_POINT_SOURCE Bortle fallback requires "
                    "light_pollution_derivation_mode=BORTLE_TABLE"
                )
            if environment.observing_aid is not ObserverAid.NAKED_EYE:
                raise ValueError(
                    "CRUMEY_2014_POINT_SOURCE is admitted only for naked-eye observation"
                )
            if not self.use_refraction:
                raise ValueError(
                    "CRUMEY_2014_POINT_SOURCE requires apparent altitude "
                    "(use_refraction=True)"
                )
            if (
                self.extinction_model is VisibilityExtinctionModel.SCHAEFER_1993_COMPONENTS
                and environment.relative_humidity >= 1.0
            ):
                raise ValueError(
                    "SCHAEFER_1993_COMPONENTS requires relative_humidity < 1 "
                    "for the clear-air aerosol model"
                )


@dataclass(frozen=True, slots=True)
class VisibilitySearchPolicy:
    """
    RITE: The Search Warden — the policy vessel governing event-search extent
    and step resolution.

    THEOREM: Immutable frozen dataclass carrying the search-window, step-size,
    and refinement-tolerance parameters for generalized visibility-event search.

    RITE OF PURPOSE:
        Separates search configuration from visibility doctrine so that callers
        can tune search performance (window size, step resolution) independently
        from the criterion family and observer environment.  Without this
        vessel, search parameters would need to be threaded as raw int/float
        keyword arguments alongside doctrinal choices, making the search
        configuration invisible at the API surface.

    LAW OF OPERATION:
        Responsibilities:
            - Carry search_window_days, coarse_step_days, refine_tolerance_days,
              and long_search flag as a typed, validated policy.
            - Validate on construction that window and steps are positive and
              finite.
        Non-responsibilities:
            - Does not execute any search.
            - Does not define the visibility criterion used during search.
        Dependencies:
            - None (pure data vessel).
        Behavioral invariants:
            - search_window_days must be a positive integer.
            - coarse_step_days and refine_tolerance_days must be positive finite
              floats.

    Canon: None (No applicable canon).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.VisibilitySearchPolicy",
        "risk": "low",
        "api": {
            "public_attributes": [
                "search_window_days", "coarse_step_days",
                "refine_tolerance_days", "long_search"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError for non-positive window or non-finite steps"],
            "policy": "__post_init__ enforces physical plausibility bounds"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    search_window_days: int = 400
    coarse_step_days: float = 1.0
    refine_tolerance_days: float = 1.0 / 86400.0
    long_search: bool = False

    def __post_init__(self) -> None:
        if not (isinstance(self.search_window_days, int) and self.search_window_days > 0):
            raise ValueError("search_window_days must be a positive integer")
        if not (math.isfinite(self.coarse_step_days) and self.coarse_step_days > 0.0):
            raise ValueError("coarse_step_days must be positive and finite")
        if not (math.isfinite(self.refine_tolerance_days) and self.refine_tolerance_days > 0.0):
            raise ValueError("refine_tolerance_days must be positive and finite")


# ---------------------------------------------------------------------------
# VisibilityModel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VisibilityModel:
    """
    RITE: The V0 Observer Vessel — the legacy narrow observer-and-atmosphere carrier
    for admitted planetary heliacal events.

    THEOREM: Immutable frozen dataclass compressing observer physiology,
    atmospheric extinction, and horizon threshold into a single typed vessel for
    the V0 planetary event helpers.

    RITE OF PURPOSE:
        Replaces legacy integer-indexed AtmosphericConditions arrays
        with a typed, self-documenting vessel so that planetary heliacal event
        callers can express observing conditions without raw array indexing.
        Retained for V0 backwards compatibility; new callers should use
        ObserverVisibilityEnvironment and VisibilityPolicy for the full
        generalized surface.

    LAW OF OPERATION:
        Responsibilities:
            - Carry limiting magnitude, extinction coefficient, horizon altitude,
              and atmospheric parameters as typed, validated fields.
            - Serve as the visibility_model field of HeliacalPolicy.
            - Provide to_observer_environment() for bridging into the full
              generalized surface.
        Non-responsibilities:
            - Does not separate site darkness from observer physiology (by design;
              that separation belongs to ObserverVisibilityEnvironment).
            - Does not carry light-pollution class (use ObserverVisibilityEnvironment
              for that).
            - Does not apply refraction itself.
        Dependencies:
            - LightPollutionClass, ObserverAid (optional; passed through
              to_observer_environment() only).
        Behavioral invariants:
            - relative_humidity \u2208 [0, 1].
            - extinction_coefficient \u2265 0.

    Canon: Schaefer, B.E. (1990), PASP 102, 212\u2013229 (physical model basis).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.VisibilityModel",
        "risk": "low",
        "api": {
            "public_attributes": [
                "limiting_magnitude", "extinction_coefficient",
                "horizon_altitude_deg", "temperature_c",
                "pressure_mbar", "relative_humidity"
            ],
            "public_methods": ["to_observer_environment"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError for invalid humidity or extinction_coefficient"],
            "policy": "__post_init__ enforces physical plausibility bounds"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]

    All fields have documented physical units.  Callers must not pass raw
    legacy integer-array indices to any Moira heliacal function.

    Args:
        limiting_magnitude: Faintest magnitude visible to the naked eye
            under these conditions (dimensionless, positive).
            Default 6.5 (ideal dark sky).
        extinction_coefficient: Atmospheric extinction per airmass
            (magnitudes/airmass).  Default 0.25 (average site).
        horizon_altitude_deg: Legacy alias for the local visibility cutoff
            above the geometric horizon (degrees).  This is a terrain or
            site-obstruction threshold, not the rise/set effective geometric
            horizon used by RiseSetPolicy.  Default 0.0.
        temperature_c: Ambient temperature (\u00b0C) for refraction.  Default 10.
        pressure_mbar: Atmospheric pressure (mbar) for refraction.
            Default 1013.25 (sea level ISA).
        relative_humidity: Relative humidity [0.0, 1.0] for extended
            refraction model.  Default 0.5.
    """
    limiting_magnitude:     float = 6.5
    extinction_coefficient: float = 0.25
    horizon_altitude_deg:   float = 0.0
    temperature_c:          float = 10.0
    pressure_mbar:          float = 1013.25
    relative_humidity:      float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.relative_humidity <= 1.0:
            raise ValueError(
                f"VisibilityModel.relative_humidity must be in [0, 1], "
                f"got {self.relative_humidity}"
            )
        if self.extinction_coefficient < 0.0:
            raise ValueError(
                f"VisibilityModel.extinction_coefficient must be >= 0, "
                f"got {self.extinction_coefficient}"
            )

    def to_observer_environment(
        self,
        *,
        light_pollution_class: LightPollutionClass | None = None,
        observing_aid: ObserverAid = ObserverAid.NAKED_EYE,
    ) -> ObserverVisibilityEnvironment:
        """Adapt the legacy narrow vessel into the fuller environment layer."""
        return ObserverVisibilityEnvironment(
            light_pollution_class=light_pollution_class,
            limiting_magnitude=self.limiting_magnitude,
            local_horizon_altitude_deg=self.horizon_altitude_deg,
            temperature_c=self.temperature_c,
            pressure_mbar=self.pressure_mbar,
            relative_humidity=self.relative_humidity,
            observing_aid=observing_aid,
        )


# ---------------------------------------------------------------------------
# HeliacalPolicy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HeliacalPolicy:
    """
    RITE: The V0 Doctrine Layer — the legacy narrow planetary heliacal event policy
    carrier.

    THEOREM: Immutable frozen dataclass governing three narrow doctrinal choices
    for the V0 admitted planetary heliacal event helpers.

    RITE OF PURPOSE:
        Replaces legacy heliacal integer flag bitfields with
        a typed, self-documenting policy so that planetary heliacal event callers
        can declare observing configuration without raw SE_HELFLAG_ constants.
        Retained for V0 compatibility; bridges into VisibilityPolicy through
        __post_init__ construction.  New callers using visibility_event() may
        pass VisibilityPolicy directly and leave this vessel at default.

    LAW OF OPERATION:
        Responsibilities:
            - Carry optical_aid, use_extended_atmosphere, visibility_model, and
              visibility_policy as a typed, validated policy.
            - Construct a default visibility_policy from visibility_model when
              none is supplied.
            - Serve as the heliacal_policy argument to visibility_event() and
              the narrow V0 planet_heliacal_* helpers.
        Non-responsibilities:
            - Does not govern fixed-star heliacal search (that is
              FixedStarComputationPolicy in star_types.py).
            - Does not carry geographic coordinates.
            - Does not infer body_type from body name (that is done at call time).
        Dependencies:
            - ObserverAid, VisibilityModel, VisibilityPolicy,
              ObserverVisibilityEnvironment.
        Behavioral invariants:
            - optical_aid is normalised to an ObserverAid enum member.
            - visibility_model is never None after construction.
            - visibility_policy is never None after construction.

    Canon: Schaefer (1990), PASP 102, 212\u2013229 (physical doctrine basis).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.HeliacalPolicy",
        "risk": "medium",
        "api": {
            "public_attributes": [
                "optical_aid", "use_extended_atmosphere",
                "visibility_model", "visibility_policy"
            ],
            "public_methods": ["default"]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": ["ValueError for invalid optical_aid value"],
            "policy": "__post_init__ normalises optical_aid and populates defaults"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]

    Args:
        optical_aid: One of ``'naked_eye'``, ``'binoculars'``, or
            ``'telescope'``.  Default ``'naked_eye'``.
        use_extended_atmosphere: If ``True``, apply the extended refraction
            model (requires humidity/wavelength in VisibilityModel).
            Default ``False``.
        visibility_model: :class:`VisibilityModel` instance governing
            observer and atmospheric parameters.  Default is standard
            dark-sky conditions.
    """
    optical_aid:               str            = 'naked_eye'
    use_extended_atmosphere:   bool           = False
    visibility_model:          VisibilityModel = None  # type: ignore[assignment]
    visibility_policy:         VisibilityPolicy | None = None

    def __post_init__(self) -> None:
        valid = tuple(aid.value for aid in ObserverAid)
        optical_aid_value = self.optical_aid.value if isinstance(self.optical_aid, ObserverAid) else self.optical_aid
        if optical_aid_value not in valid:
            raise ValueError(
                f"HeliacalPolicy.optical_aid must be one of {valid}, "
                f"got {optical_aid_value!r}"
            )
        if not isinstance(self.optical_aid, ObserverAid):
            object.__setattr__(self, 'optical_aid', ObserverAid(optical_aid_value))
        # Replace None sentinel with the default VisibilityModel
        if self.visibility_model is None:
            object.__setattr__(self, 'visibility_model', VisibilityModel())
        if self.visibility_policy is None:
            object.__setattr__(
                self,
                'visibility_policy',
                VisibilityPolicy(
                    environment=self.visibility_model.to_observer_environment(
                        observing_aid=self.optical_aid,
                    ),
                    use_refraction=True,
                ),
            )

    @classmethod
    def default(cls) -> 'HeliacalPolicy':
        """Return the standard naked-eye dark-sky policy."""
        return cls()


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_HELIACAL_PLANETS: frozenset[str] = frozenset({
    Body.MERCURY, Body.VENUS, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
})
_PHYSICAL_VISIBILITY_PLANETS: frozenset[str] = frozenset({
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
})
_PHYSICAL_VISIBILITY_STARS: frozenset[str] = frozenset({
    "Sirius",
})
_PHYSICAL_VISIBILITY_TARGETS: frozenset[str] = (
    _PHYSICAL_VISIBILITY_PLANETS | _PHYSICAL_VISIBILITY_STARS
)
_PHYSICAL_EVENT_PLANETS: frozenset[str] = frozenset({
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
})
_PHYSICAL_EVENT_TARGETS: frozenset[str] = (
    _PHYSICAL_EVENT_PLANETS | _PHYSICAL_VISIBILITY_STARS
)
_PHYSICAL_EVENT_PACK_VERSION = "1.2.0"
_PHYSICAL_EVENT_PACK_MANIFEST_SHA256 = (
    "cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c"
)
_PHYSICAL_EVENT_CROSSING_CERTIFICATE_SHA256 = (
    "eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e"
)
_PHYSICAL_DIRECTIONAL_HORIZON_CERTIFICATE_SHA256 = (
    "3baf162ffd5f3e659b1489d60502e409f76c3b20cf6e90ef004eabb06fa029d6"
)
_PHYSICAL_DIRECTIONAL_HORIZON_BASE_RATE_PER_DAY = 1024.0
_PHYSICAL_EVENT_GEOMETRY_CERTIFICATE = _ScalarLipschitzCertificate(
    certificate_id=(
        "physical-heliacal-event-lipschitz-v1:geometry"
    ),
    maximum_absolute_rate_per_day=1024.0,
    source_receipt_sha256=(
        _PHYSICAL_EVENT_CROSSING_CERTIFICATE_SHA256
    ),
)
_PHYSICAL_EVENT_MARGIN_CERTIFICATE = _ScalarLipschitzCertificate(
    certificate_id=(
        "physical-heliacal-event-lipschitz-v1:visibility-margin"
    ),
    maximum_absolute_rate_per_day=16384.0,
    source_receipt_sha256=(
        _PHYSICAL_EVENT_CROSSING_CERTIFICATE_SHA256
    ),
)
_PHYSICAL_PLANET_PHOTOMETRY_MODEL_ID = (
    "mallama_hilton_2018_moira_planetary_v1"
)
_PHYSICAL_PLANET_PHOTOMETRY_SOURCE_IDS = (
    "Mallama_Hilton:2018",
    "Astronomical_Almanac:planetary_magnitude_models",
)

# Minimum elongation (°) from the Sun before bothering to test visibility.
# Below this the planet is lost in the solar glare regardless of magnitude.
_ELONG_MIN: float = 5.0
_COSMIC_SOLAR_ALTITUDE_DEG: float = -18.0


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _signed_elongation(body: str, jd: float) -> float:
    """
    Signed ecliptic elongation of *body* from the Sun (degrees).

    Positive = east of Sun (evening star).
    Negative = west of Sun (morning star).
    Range: (−180, +180].
    """
    from .planets import planet_at
    p = planet_at(body, jd)
    s = planet_at(Body.SUN, jd)
    return (p.longitude - s.longitude + 180.0) % 360.0 - 180.0


def _planet_alt(
    body: str,
    jd: float,
    lat: float,
    lon: float,
    *,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
    relative_humidity: float = 0.0,
) -> float:
    """Apparent altitude of *body* above the observer's horizon (degrees)."""
    from .rise_set import _altitude

    geometric_altitude = _altitude(
        jd,
        lat,
        lon,
        body,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
    )
    return apply_refraction(
        geometric_altitude,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
        relative_humidity=relative_humidity,
    )


def _sun_alt(jd: float, lat: float, lon: float) -> float:
    """Altitude of the Sun above the observer's horizon (degrees)."""
    from .rise_set import _altitude
    return _altitude(jd, lat, lon, Body.SUN)


def _arcus_visionis(mag: float, model: VisibilityModel) -> float:
    """
    Solar depression (degrees) required for a body of apparent magnitude *mag*
    to be visible under the given atmospheric conditions.

    Based on the classical stepped table (Ptolemy / Schoch), scaled for
    non-standard limiting magnitude and extinction coefficient.
    """
    if mag <= -4.0:
        base = 5.0
    elif mag <= -2.0:
        base = 6.5
    elif mag <= -1.0:
        base = 7.5
    elif mag <= 0.0:
        base = 9.0
    elif mag <= 1.0:
        base = 10.0
    elif mag <= 2.0:
        base = 11.0
    elif mag <= 3.0:
        base = 12.0
    elif mag <= 4.0:
        base = 13.0
    else:
        base = 14.5
    # Adjust for limiting magnitude (observer acuity) and extinction
    base += (6.5 - model.limiting_magnitude) * 0.8
    base += (model.extinction_coefficient - 0.25) * 4.0
    return max(3.0, base)


_BORTLE_LIMITING_MAG_TABLE: dict[LightPollutionClass, float] = {
    LightPollutionClass.BORTLE_1: 7.6,
    LightPollutionClass.BORTLE_2: 7.1,
    LightPollutionClass.BORTLE_3: 6.6,
    LightPollutionClass.BORTLE_4: 6.1,
    LightPollutionClass.BORTLE_5: 5.6,
    LightPollutionClass.BORTLE_6: 5.1,
    LightPollutionClass.BORTLE_7: 4.6,
    LightPollutionClass.BORTLE_8: 4.1,
    LightPollutionClass.BORTLE_9: 3.6,
}


def _policy_limiting_magnitude(
    light_pollution_class: LightPollutionClass | None,
    mode: LightPollutionDerivationMode,
) -> float:
    """
    Derive limiting magnitude from Bortle class under the selected derivation mode.

    Returns 6.5 when ``light_pollution_class`` is None.

    Raises:
        KeyError: If ``mode`` is ``BORTLE_TABLE`` and the Bortle class is not
            present in the lookup table.

    Side effects: None.
    """
    if light_pollution_class is None:
        return 6.5
    if mode is LightPollutionDerivationMode.BORTLE_TABLE:
        return _BORTLE_LIMITING_MAG_TABLE[light_pollution_class]
    return 8.1 - 0.5 * float(light_pollution_class)


def _effective_limiting_magnitude(policy: VisibilityPolicy) -> float:
    """
    Resolve the effective limiting magnitude from policy environment state.

    Uses explicit ``environment.limiting_magnitude`` when provided; otherwise
    derives a value from Bortle class and derivation mode.

    Raises:
        AssertionError: If ``policy.environment`` is unexpectedly None.

    Side effects: None.
    """
    environment = policy.environment
    assert environment is not None
    if environment.limiting_magnitude is not None:
        return environment.limiting_magnitude
    return _policy_limiting_magnitude(
        environment.light_pollution_class,
        policy.light_pollution_derivation_mode,
    )


# ---------------------------------------------------------------------------
# Physical atmospheric visibility models
# ---------------------------------------------------------------------------

_CRUMEY_BACKGROUND_MIN_CD_M2 = 1.0e-5
_CRUMEY_BACKGROUND_MAX_CD_M2 = 3.426e-2
_NANOLAMBERT_TO_CD_M2 = 1.0e-5 / math.pi


def _validate_apparent_altitude(altitude_deg: float) -> None:
    if not math.isfinite(altitude_deg) or not 0.0 <= altitude_deg <= 90.0:
        raise ValueError("apparent altitude must be finite and in [0, 90] degrees")


def relative_optical_airmass(apparent_altitude_deg: float) -> float:
    """Return Kasten--Young (1989) relative optical air mass.

    The input is apparent altitude in degrees.  The approximation is admitted
    from the horizon through the zenith; below-horizon sight lines are rejected
    rather than clamped into a fictitious atmospheric path.
    """

    _validate_apparent_altitude(apparent_altitude_deg)
    h = apparent_altitude_deg
    return 1.0 / (
        math.sin(math.radians(h))
        + 0.50572 * (h + 6.07995) ** -1.6364
    )


def _rozenberg_airmass(apparent_altitude_deg: float) -> float:
    """Whole-atmosphere air mass from Rozenberg (1966), Schaefer Eq. 2b."""

    _validate_apparent_altitude(apparent_altitude_deg)
    cos_z = math.sin(math.radians(apparent_altitude_deg))
    return 1.0 / (cos_z + 0.025 * math.exp(-11.0 * cos_z))


def _schaefer_exponential_airmass(
    apparent_altitude_deg: float,
    scale_height_km: float,
) -> float:
    """Schaefer (1993), Eq. 3a, for an exponential atmospheric component."""

    _validate_apparent_altitude(apparent_altitude_deg)
    cos_z = math.sin(math.radians(apparent_altitude_deg))
    root_height = math.sqrt(scale_height_km)
    return 1.0 / (
        cos_z
        + 0.01
        * root_height
        * math.exp(-30.0 * cos_z / root_height)
    )


def _schaefer_layer_airmass(
    apparent_altitude_deg: float,
    layer_height_km: float,
) -> float:
    """Schaefer (1993), Eq. 3b, for a thin layer above the observer."""

    _validate_apparent_altitude(apparent_altitude_deg)
    sin_z = math.cos(math.radians(apparent_altitude_deg))
    earth_equatorial_radius_km = 6378.0
    denominator = 1.0 + layer_height_km / earth_equatorial_radius_km
    return (1.0 - (sin_z / denominator) ** 2) ** -0.5


def atmospheric_extinction(
    apparent_altitude_deg: float,
    *,
    model: VisibilityExtinctionModel,
    extinction_coefficient_k: float = ExtinctionCoefficient.GOOD_DARK_SITE,
    observer_altitude_m: float = 0.0,
    relative_humidity: float = 0.5,
    observer_latitude_deg: float = 0.0,
    sun_right_ascension_deg: float = 0.0,
) -> AtmosphericExtinctionAssessment:
    """Compute direct-beam extinction for one sight line.

    ``KASTEN_YOUNG_1989_BROADBAND`` applies a caller-declared, preferably
    measured, broadband coefficient to the Kasten--Young relative optical air
    mass.  ``SCHAEFER_1993_COMPONENTS`` estimates Rayleigh, aerosol, and ozone
    terms using Schaefer's Eqs. 3--6 and his stated night-vision multipliers
    for the direct target.  It also returns the unmodified visual-band sum
    separately for Schaefer/Krisciunas sky-brightness equations.
    The legacy arcus-visionis slot is intentionally not accepted here because
    it is an event-threshold convention, not a direct extinction model.
    """

    _validate_apparent_altitude(apparent_altitude_deg)
    if not math.isfinite(extinction_coefficient_k) or extinction_coefficient_k < 0.0:
        raise ValueError("extinction_coefficient_k must be finite and >= 0")
    if not math.isfinite(observer_altitude_m) or observer_altitude_m < -1000.0:
        raise ValueError("observer_altitude_m must be finite and >= -1000")
    if not math.isfinite(relative_humidity) or not 0.0 <= relative_humidity <= 1.0:
        raise ValueError("relative_humidity must be finite and in [0, 1]")
    if not math.isfinite(observer_latitude_deg) or not -90.0 <= observer_latitude_deg <= 90.0:
        raise ValueError("observer_latitude_deg must be finite and in [-90, 90]")
    if not math.isfinite(sun_right_ascension_deg):
        raise ValueError("sun_right_ascension_deg must be finite")

    zenith_distance = 90.0 - apparent_altitude_deg
    if model is VisibilityExtinctionModel.KASTEN_YOUNG_1989_BROADBAND:
        broadband_airmass = relative_optical_airmass(apparent_altitude_deg)
        extinction_magnitude = extinction_coefficient_k * broadband_airmass
        return AtmosphericExtinctionAssessment(
            model=model,
            apparent_altitude_deg=apparent_altitude_deg,
            zenith_distance_deg=zenith_distance,
            broadband_airmass=broadband_airmass,
            rayleigh_airmass=None,
            aerosol_airmass=None,
            ozone_airmass=None,
            rayleigh_coefficient_mag_per_airmass=None,
            aerosol_coefficient_mag_per_airmass=None,
            ozone_coefficient_mag_per_airmass=None,
            total_zenith_extinction_coefficient=extinction_coefficient_k,
            sky_brightness_extinction_coefficient=extinction_coefficient_k,
            extinction_magnitude=extinction_magnitude,
            transmission_fraction=10.0 ** (-0.4 * extinction_magnitude),
        )
    if model is not VisibilityExtinctionModel.SCHAEFER_1993_COMPONENTS:
        raise ValueError(
            "atmospheric_extinction requires KASTEN_YOUNG_1989_BROADBAND "
            "or SCHAEFER_1993_COMPONENTS"
        )
    if relative_humidity >= 1.0:
        raise ValueError(
            "SCHAEFER_1993_COMPONENTS requires relative_humidity < 1 "
            "for the clear-air aerosol model"
        )

    height_km = observer_altitude_m / 1000.0
    rayleigh_airmass = _schaefer_exponential_airmass(apparent_altitude_deg, 8.2)
    aerosol_airmass = _schaefer_exponential_airmass(apparent_altitude_deg, 1.5)
    ozone_airmass = _schaefer_layer_airmass(apparent_altitude_deg, 20.0)

    # Schaefer (1993), Eqs. 4b, 5, and 6 first define visual-band
    # coefficients.  The paper later gives separate night-vision factors for
    # direct faint-target extinction: Rayleigh 1.35, ozone 0.30, aerosol 1.10.
    rayleigh_visual_k = 0.1066 * math.exp(-height_km / 8.2)
    latitude_rad = math.radians(observer_latitude_deg)
    sun_ra_rad = math.radians(sun_right_ascension_deg % 360.0)
    ozone_column_mm = 3.0 + 0.4 * (
        latitude_rad * math.cos(sun_ra_rad) - math.cos(3.0 * latitude_rad)
    )
    ozone_visual_k = 0.031 * ozone_column_mm / 3.0

    if relative_humidity == 0.0:
        humidity_factor = 1.0
    else:
        humidity_factor = (
            1.0 - 0.32 / math.log(relative_humidity)
        ) ** (4.0 / 3.0)
    aerosol_visual_k = (
        0.12
        * math.exp(-height_km / 1.5)
        * humidity_factor
        * (1.0 + 0.33 * math.sin(sun_ra_rad))
    )
    rayleigh_k = 1.35 * rayleigh_visual_k
    ozone_k = 0.30 * ozone_visual_k
    aerosol_k = 1.10 * aerosol_visual_k
    extinction_magnitude = (
        rayleigh_k * rayleigh_airmass
        + aerosol_k * aerosol_airmass
        + ozone_k * ozone_airmass
    )
    total_k = rayleigh_k + aerosol_k + ozone_k
    sky_brightness_k = (
        rayleigh_visual_k + aerosol_visual_k + ozone_visual_k
    )
    return AtmosphericExtinctionAssessment(
        model=model,
        apparent_altitude_deg=apparent_altitude_deg,
        zenith_distance_deg=zenith_distance,
        broadband_airmass=None,
        rayleigh_airmass=rayleigh_airmass,
        aerosol_airmass=aerosol_airmass,
        ozone_airmass=ozone_airmass,
        rayleigh_coefficient_mag_per_airmass=rayleigh_k,
        aerosol_coefficient_mag_per_airmass=aerosol_k,
        ozone_coefficient_mag_per_airmass=ozone_k,
        total_zenith_extinction_coefficient=total_k,
        sky_brightness_extinction_coefficient=sky_brightness_k,
        extinction_magnitude=extinction_magnitude,
        transmission_fraction=10.0 ** (-0.4 * extinction_magnitude),
    )


def directional_twilight_sky_brightness(
    target_altitude_deg: float,
    sun_altitude_deg: float,
    sun_target_separation_deg: float,
    *,
    extinction_coefficient_k: float,
) -> TwilightSkyBrightnessAssessment:
    """Return Schaefer's directional cloudless-sky twilight contribution.

    Schaefer (1993), Eq. 15c, is evaluated only for solar altitudes from
    -18 through 0 degrees.  Below -18 degrees the admitted twilight
    contribution is zero.  Above the horizon the result is explicitly invalid
    because this is not a daylight-sky model.
    """

    _validate_apparent_altitude(target_altitude_deg)
    if not math.isfinite(sun_altitude_deg):
        raise ValueError("sun_altitude_deg must be finite")
    if (
        not math.isfinite(sun_target_separation_deg)
        or not 0.0 <= sun_target_separation_deg <= 180.0
    ):
        raise ValueError("sun_target_separation_deg must be finite and in [0, 180]")
    if not math.isfinite(extinction_coefficient_k) or extinction_coefficient_k < 0.0:
        raise ValueError("extinction_coefficient_k must be finite and >= 0")

    sky_airmass = _rozenberg_airmass(target_altitude_deg)
    if sun_altitude_deg < -18.0:
        return TwilightSkyBrightnessAssessment(
            model=VisibilityTwilightModel.SCHAEFER_1993_DIRECTIONAL,
            target_altitude_deg=target_altitude_deg,
            sun_altitude_deg=sun_altitude_deg,
            sun_target_separation_deg=sun_target_separation_deg,
            sky_airmass=sky_airmass,
            extinction_coefficient=extinction_coefficient_k,
            formula_applied=False,
            valid=True,
            reason="sun_below_astronomical_twilight",
            sky_nanolamberts=0.0,
        )
    if sun_altitude_deg > 0.0:
        return TwilightSkyBrightnessAssessment(
            model=VisibilityTwilightModel.SCHAEFER_1993_DIRECTIONAL,
            target_altitude_deg=target_altitude_deg,
            sun_altitude_deg=sun_altitude_deg,
            sun_target_separation_deg=sun_target_separation_deg,
            sky_airmass=sky_airmass,
            extinction_coefficient=extinction_coefficient_k,
            formula_applied=False,
            valid=False,
            reason="sun_above_twilight_model_range",
            sky_nanolamberts=None,
        )

    directional_factor = max(
        1.0,
        10.0 ** (sun_target_separation_deg / 90.0 - 1.1),
    )
    brightness = (
        directional_factor
        * 10.0 ** (8.45 + 0.4 * sun_altitude_deg)
        * (1.0 - 10.0 ** (-0.4 * extinction_coefficient_k * sky_airmass))
    )
    return TwilightSkyBrightnessAssessment(
        model=VisibilityTwilightModel.SCHAEFER_1993_DIRECTIONAL,
        target_altitude_deg=target_altitude_deg,
        sun_altitude_deg=sun_altitude_deg,
        sun_target_separation_deg=sun_target_separation_deg,
        sky_airmass=sky_airmass,
        extinction_coefficient=extinction_coefficient_k,
        formula_applied=True,
        valid=True,
        reason=None,
        sky_nanolamberts=max(0.0, brightness),
    )


def point_source_visibility_threshold(
    background_nanolamberts: float,
    *,
    field_factor: float = 2.0,
) -> PointSourceVisibilityThreshold:
    """Return Crumey's scotopic naked-eye point-source limiting magnitude.

    Implements Crumey (2014), Eq. 53, with the paper's V-band illuminance zero
    point.  ``field_factor`` retains the paper's overall target/medium/
    laboratory/observer semantics.  Values outside the published background
    interval are returned as invalid rather than extrapolated.
    """

    if not math.isfinite(background_nanolamberts) or background_nanolamberts <= 0.0:
        raise ValueError("background_nanolamberts must be finite and > 0")
    if not math.isfinite(field_factor) or field_factor <= 0.0:
        raise ValueError("field_factor must be finite and > 0")

    background_cd_m2 = background_nanolamberts * _NANOLAMBERT_TO_CD_M2
    if not _CRUMEY_BACKGROUND_MIN_CD_M2 <= background_cd_m2 <= _CRUMEY_BACKGROUND_MAX_CD_M2:
        return PointSourceVisibilityThreshold(
            criterion_family=VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE,
            background_nanolamberts=background_nanolamberts,
            background_luminance_cd_m2=background_cd_m2,
            field_factor=field_factor,
            valid_background_min_cd_m2=_CRUMEY_BACKGROUND_MIN_CD_M2,
            valid_background_max_cd_m2=_CRUMEY_BACKGROUND_MAX_CD_M2,
            valid=False,
            reason="background_outside_crumey_2014_range",
            limiting_magnitude=None,
        )

    threshold_illuminance_lux = field_factor * (
        6.505e-4 * background_cd_m2 ** 0.25
        - 8.461e-4 * background_cd_m2 ** 0.5
    ) ** 2
    limiting_magnitude = -2.5 * math.log10(
        threshold_illuminance_lux / 2.54e-6
    )
    return PointSourceVisibilityThreshold(
        criterion_family=VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE,
        background_nanolamberts=background_nanolamberts,
        background_luminance_cd_m2=background_cd_m2,
        field_factor=field_factor,
        valid_background_min_cd_m2=_CRUMEY_BACKGROUND_MIN_CD_M2,
        valid_background_max_cd_m2=_CRUMEY_BACKGROUND_MAX_CD_M2,
        valid=True,
        reason=None,
        limiting_magnitude=limiting_magnitude,
    )


# ---------------------------------------------------------------------------
# Krisciunas & Schaefer (1991) moonlight sky-brightness model
# ---------------------------------------------------------------------------
# Authority: Krisciunas, K. & Schaefer, B.E. (1991), PASP 103, 1033-1039.
# "A model for the brightness of moonlight."
# The formulas below implement the paper's admitted derivation chain:
#   Eq. 9      - lunar apparent magnitude as a function of phase angle
#   Eqs. 17-19 - Rayleigh and piecewise Mie scattering functions
#   Eq. 20     - top-of-atmosphere lunar illuminance I*(alpha)
#   Eq. 15     - moonlight sky brightness B_moon in nanolamberts
# The limiting-magnitude penalty uses the linear sky-brightness / limiting-magnitude
# relation derived from the Bortle SQM column, under the approximation that
# mL varies as -2.5 * log10(B_sky) (sky background as the dominant noise source).

# Bortle class → sky surface brightness (mag/arcsec²)
# Values from Bortle (2001, Sky & Telescope) and subsequent SQM calibration work.
_BORTLE_SKY_SQM_TABLE: dict[LightPollutionClass, float] = {
    LightPollutionClass.BORTLE_1: 21.75,
    LightPollutionClass.BORTLE_2: 21.50,
    LightPollutionClass.BORTLE_3: 21.25,
    LightPollutionClass.BORTLE_4: 20.75,
    LightPollutionClass.BORTLE_5: 20.25,
    LightPollutionClass.BORTLE_6: 19.50,
    LightPollutionClass.BORTLE_7: 18.75,
    LightPollutionClass.BORTLE_8: 18.00,
    LightPollutionClass.BORTLE_9: 17.50,
}


def _ks1991_moon_magnitude(phase_angle_deg: float) -> float:
    """
    Apparent V-band magnitude of the Moon as a function of phase angle.

    Krisciunas & Schaefer (1991), Eq. 9.
    phase_angle_deg: 0 = full moon, 180 = new moon.
    """
    alpha = abs(phase_angle_deg)
    return -12.73 + 0.026 * alpha + 4.0e-9 * alpha**4


def _ks1991_scattering_function(rho_deg: float) -> float:
    """
    Atmospheric scattering function f(rho) for moonlit sky brightness.

    Krisciunas & Schaefer (1991), Eqs. 17-19 and 21.
    rho_deg: angular separation (degrees) between Moon and target sky point.
    The empirical Mie term follows Eq. 18 from 10 through 180 degrees and
    switches to the Eq. 19 aureole law below 10 degrees. The point-source
    model is singular at zero separation, so zero is rejected rather than
    silently clamped.
    """
    if not math.isfinite(rho_deg) or not 0.0 < rho_deg <= 180.0:
        raise ValueError("rho_deg must be finite and in (0, 180]")

    rho = rho_deg
    rho_r = math.radians(rho)
    rayleigh = 10.0**5.36 * (1.06 + math.cos(rho_r) ** 2)
    mie = (
        6.2e7 * rho**-2.0
        if rho < 10.0
        else 10.0 ** (6.15 - rho / 40.0)
    )
    return rayleigh + mie


def _ks1991_moonlight_nanolamberts(
    rho_deg: float,
    alt_moon_deg: float,
    phase_angle_deg: float,
    extinction_k: float,
    alt_target_deg: float,
) -> float:
    """
    Moonlight contribution to sky brightness at target direction, in nanolamberts.

    Krisciunas & Schaefer (1991), Eqs. 20-21.
    Returns 0.0 if the Moon or the target is below the horizon.

    Parameters
    ----------
    rho_deg:
        Angular separation between Moon and target in ``(0, 180]`` degrees.
        Separations below 10 degrees use the source-defined aureole law.
    alt_moon_deg:
        Altitude of the Moon above the horizon (degrees).
    phase_angle_deg:
        Moon's phase angle (0 = full, 180 = new).
    extinction_k:
        Extinction coefficient (magnitudes per airmass). Use 0.172 for a
        photometric-standard clear sky (Schaefer 1990).
    alt_target_deg:
        Altitude of the target sky point above the horizon (degrees).
    """
    if alt_moon_deg <= 0.0 or alt_target_deg <= 0.0:
        return 0.0

    # Eq. 9 + Eq. 20: top-of-atmosphere lunar illuminance
    v_moon = _ks1991_moon_magnitude(phase_angle_deg)
    i_star = 10.0**(-0.4 * (v_moon + 16.57))

    # Eqs. 17-19 and 21: Rayleigh plus piecewise Mie scattering.
    f_rho = _ks1991_scattering_function(rho_deg)

    # The attenuated lunar beam and the scattering path toward the sky point
    # are distinct geometrical objects in K&S 1991.
    x_moon = _rozenberg_airmass(alt_moon_deg)
    x_target = (
        1.0 - 0.96 * math.cos(math.radians(alt_target_deg)) ** 2
    ) ** -0.5

    # Eq. 15: moonlight sky brightness in nanolamberts.
    b_moon = (
        f_rho
        * i_star
        * 10.0**(-0.4 * extinction_k * x_moon)
        * (1.0 - 10.0**(-0.4 * extinction_k * x_target))
    )
    return max(0.0, b_moon)


def _ks1991_dark_sky_nanolamberts(policy: VisibilityPolicy) -> float:
    """
    Dark-sky surface brightness in nanolamberts derived from the Bortle light-pollution
    policy or an explicit measured V/SQM surface brightness.

    Krisciunas & Schaefer (1991), Eq. 1:
    ``B_nL = 34.08 exp(20.7233 - 0.92104 V)``.
    """
    environment = policy.environment
    assert environment is not None
    if environment.sky_surface_brightness_mag_arcsec2 is not None:
        sqm = environment.sky_surface_brightness_mag_arcsec2
    else:
        lpc = environment.light_pollution_class
        sqm = _BORTLE_SKY_SQM_TABLE.get(
            lpc,
            _BORTLE_SKY_SQM_TABLE[LightPollutionClass.BORTLE_3],
        )
    return 34.08 * math.exp(20.7233 - 0.92104 * sqm)


def _directional_dark_sky_nanolamberts(
    zenith_sky_nanolamberts: float,
    apparent_altitude_deg: float,
    extinction_k: float,
) -> float:
    """Project an observed zenith sky brightness to one direction.

    This is the zenith-normalized form of Krisciunas & Schaefer (1991),
    Eq. 2.  The supplied observed zenith value is recovered at 90 degrees.
    """

    _validate_apparent_altitude(apparent_altitude_deg)
    x_direct = _rozenberg_airmass(apparent_altitude_deg)
    scattering = (
        0.4
        + 0.6
        / math.sqrt(
            1.0 - 0.96 * math.cos(math.radians(apparent_altitude_deg)) ** 2
        )
    )
    return (
        zenith_sky_nanolamberts
        * scattering
        * 10.0 ** (-0.4 * extinction_k * (x_direct - 1.0))
    )


def _ks1991_moonlight_for_target(
    policy: VisibilityPolicy,
    jd_ut: float,
    lat: float,
    lon: float,
    body: str,
    *,
    extinction_k: float | None = None,
) -> float:
    """Return the K&S moonlight contribution for the target direction."""

    target_azimuth_deg, target_altitude_deg = _true_horizontal(
        body,
        jd_ut,
        lat,
        lon,
    )
    return _ks1991_moonlight_for_horizontal_direction(
        policy,
        jd_ut,
        lat,
        lon,
        target_azimuth_deg,
        target_altitude_deg,
        extinction_k=extinction_k,
    )


def _ks1991_moonlight_for_horizontal_direction(
    policy: VisibilityPolicy,
    jd_ut: float,
    lat: float,
    lon: float,
    target_azimuth_deg: float,
    target_true_altitude_deg: float,
    *,
    extinction_k: float | None = None,
) -> float:
    """Return K&S moonlight for one declared true horizontal direction."""

    from .phase import phase_angle as _phase_angle

    moon_az, moon_alt = _true_horizontal(Body.MOON, jd_ut, lat, lon)
    environment = policy.environment
    assert environment is not None
    if policy.use_refraction:
        moon_alt = apply_refraction(
            moon_alt,
            pressure_mbar=environment.pressure_mbar,
            temperature_c=environment.temperature_c,
            relative_humidity=environment.relative_humidity,
        )
    if moon_alt <= 0.0:
        return 0.0

    tgt_az = target_azimuth_deg
    tgt_alt = target_true_altitude_deg
    if policy.use_refraction:
        tgt_alt = apply_refraction(
            tgt_alt,
            pressure_mbar=environment.pressure_mbar,
            temperature_c=environment.temperature_c,
            relative_humidity=environment.relative_humidity,
        )
    if tgt_alt <= 0.0:
        return 0.0

    moon_phase = _phase_angle(Body.MOON, jd_ut)
    cos_rho = (
        math.sin(math.radians(moon_alt)) * math.sin(math.radians(tgt_alt))
        + math.cos(math.radians(moon_alt))
        * math.cos(math.radians(tgt_alt))
        * math.cos(math.radians(moon_az - tgt_az))
    )
    rho_deg = math.degrees(math.acos(max(-1.0, min(1.0, cos_rho))))
    k = policy.extinction_coefficient_k if extinction_k is None else extinction_k
    return _ks1991_moonlight_nanolamberts(
        rho_deg,
        moon_alt,
        moon_phase,
        k,
        tgt_alt,
    )


def _ks1991_zenith_limiting_magnitude_penalty(
    policy: VisibilityPolicy,
    jd_ut: float,
    lat: float,
    lon: float,
) -> float:
    """Return the K&S moonlight penalty for the zenith reference direction."""

    b_moon = _ks1991_moonlight_for_horizontal_direction(
        policy,
        jd_ut,
        lat,
        lon,
        0.0,
        90.0,
    )
    if b_moon <= 0.0:
        return 0.0
    b_dark = _ks1991_dark_sky_nanolamberts(policy)
    return -2.5 * math.log10(1.0 + b_moon / b_dark)


def _ks1991_limiting_magnitude_penalty(
    policy: VisibilityPolicy,
    jd_ut: float,
    lat: float,
    lon: float,
    body: str,
) -> float:
    """
    Reduction in effective limiting magnitude (magnitudes, negative) due to
    moonlight, computed via the Krisciunas & Schaefer (1991) model.

    Returns 0.0 when the Moon is below the horizon or the body is below
    the horizon, since moonlight adds no sky glow under those conditions.

    The extinction coefficient is read from ``policy.extinction_coefficient_k``.
    The K&S 1991 paper's own examples use 0.172 (Mauna Kea); the policy default
    is 0.20, which is more representative of a typical clear dark-sky site.
    """
    b_moon = _ks1991_moonlight_for_target(
        policy,
        jd_ut,
        lat,
        lon,
        body,
    )

    if b_moon <= 0.0:
        return 0.0

    environment = policy.environment
    assert environment is not None
    _, target_altitude = _true_horizontal(body, jd_ut, lat, lon)
    if policy.use_refraction:
        target_altitude = apply_refraction(
            target_altitude,
            pressure_mbar=environment.pressure_mbar,
            temperature_c=environment.temperature_c,
            relative_humidity=environment.relative_humidity,
        )
    b_dark = _directional_dark_sky_nanolamberts(
        _ks1991_dark_sky_nanolamberts(policy),
        target_altitude,
        policy.extinction_coefficient_k,
    )
    return -2.5 * math.log10(1.0 + b_moon / b_dark)


def _effective_visibility_model(policy: HeliacalPolicy) -> VisibilityModel:
    """
    Build the effective V0 visibility model from heliacal and visibility policy.

    When a full ``VisibilityPolicy`` is present, this helper projects its
    environment and limiting-magnitude state into a legacy ``VisibilityModel``
    instance for V0 helper compatibility.

    Raises:
        AssertionError: If ``policy.visibility_policy.environment`` is
            unexpectedly None.

    Side effects: None.
    """
    visibility_policy = policy.visibility_policy
    if visibility_policy is None:
        return policy.visibility_model
    environment = visibility_policy.environment
    assert environment is not None
    return VisibilityModel(
        limiting_magnitude=_effective_limiting_magnitude(visibility_policy),
        extinction_coefficient=policy.visibility_model.extinction_coefficient,
        horizon_altitude_deg=environment.local_horizon_altitude_deg,
        temperature_c=environment.temperature_c,
        pressure_mbar=environment.pressure_mbar,
        relative_humidity=environment.relative_humidity,
    )


def _true_altitude(body: str, jd_ut: float, lat: float, lon: float) -> float:
    """
    Compute geometric (unrefracted) altitude from RA/Dec and local sidereal time.

    This helper intentionally bypasses atmospheric refraction and returns the
    pure geometric altitude in degrees.

    Raises:
        ValueError: Propagated from trig operations if inputs are non-finite.

    Side effects: None.
    """
    from .rise_set import _body_ra_dec, _lst

    ra, dec = _body_ra_dec(jd_ut, body)
    H = math.radians((_lst(jd_ut, lon) - ra) % 360.0)
    lat_r = math.radians(lat)
    dec_r = math.radians(dec)
    alt = math.asin(
        math.sin(lat_r) * math.sin(dec_r)
        + math.cos(lat_r) * math.cos(dec_r) * math.cos(H)
    )
    return math.degrees(alt)


def _true_horizontal(body: str, jd_ut: float, lat: float, lon: float) -> tuple[float, float]:
    """
    Return geometric azimuth/altitude for a body at the given instant.

    Returns ``(azimuth_deg, altitude_deg)`` using equatorial-to-horizontal
    conversion with no atmospheric refraction.

    Raises:
        ValueError: Propagated by underlying coordinate transforms for invalid
            numeric inputs.

    Side effects: None.
    """
    from .coordinates import equatorial_to_horizontal
    from .rise_set import _body_ra_dec, _lst

    ra, dec = _body_ra_dec(jd_ut, body)
    lst = _lst(jd_ut, lon)
    return equatorial_to_horizontal(ra, dec, lst, lat)


def _horizontal_separation_deg(
    azimuth_a_deg: float,
    altitude_a_deg: float,
    azimuth_b_deg: float,
    altitude_b_deg: float,
) -> float:
    """Angular separation of two horizontal directions on the celestial sphere."""

    cos_separation = (
        math.sin(math.radians(altitude_a_deg))
        * math.sin(math.radians(altitude_b_deg))
        + math.cos(math.radians(altitude_a_deg))
        * math.cos(math.radians(altitude_b_deg))
        * math.cos(math.radians(azimuth_a_deg - azimuth_b_deg))
    )
    return math.degrees(
        math.acos(max(-1.0, min(1.0, cos_separation)))
    )


@dataclass(frozen=True, slots=True)
class _PhysicalTargetPhotometryContext:
    """Engine-owned photometry and spectral-profile geometry."""

    apparent_magnitude: float
    phase_angle_deg: float | None
    saturn_effective_ring_sub_latitude_deg: float | None
    geometry_valid: bool
    catalog_name: str | None = None
    catalog_nomenclature: str | None = None


def _physical_target_photometry_context(
    body: str,
    jd_ut: float,
) -> _PhysicalTargetPhotometryContext:
    """Resolve one internally consistent planetary or stellar context."""

    if body in _PHYSICAL_VISIBILITY_PLANETS:
        from .phase import _apparent_magnitude_context

        context = _apparent_magnitude_context(body, jd_ut)
        return _PhysicalTargetPhotometryContext(
            apparent_magnitude=context.apparent_magnitude,
            phase_angle_deg=context.phase_angle_deg,
            saturn_effective_ring_sub_latitude_deg=(
                context.saturn_effective_ring_sub_latitude_deg
            ),
            geometry_valid=context.geometry_valid,
        )

    from ._ephemeris_time import _ut1_to_ephemeris_tt
    from .julian import ut_to_tt
    from .spk_reader import get_active_reader
    from .stars import star_at

    reader = get_active_reader()
    jd_tt = (
        ut_to_tt(jd_ut)
        if reader is None
        else _ut1_to_ephemeris_tt(jd_ut, reader)
    )
    star = star_at(body, jd_tt)
    return _PhysicalTargetPhotometryContext(
        apparent_magnitude=star.magnitude,
        phase_angle_deg=None,
        saturn_effective_ring_sub_latitude_deg=None,
        geometry_valid=True,
        catalog_name=star.name,
        catalog_nomenclature=star.nomenclature,
    )


def _target_apparent_magnitude(body: str, jd_ut: float) -> float:
    """
    Return the admitted apparent-magnitude surrogate for a visibility target.

    Planets and the Moon are routed to ``phase.apparent_magnitude``; fixed
    stars are routed to ``stars.star_magnitude``.

    Raises:
        ValueError: Propagated by downstream magnitude providers for unsupported
            body identities.

    Side effects: None.
    """
    if body == Body.MOON or body in _HELIACAL_PLANETS:
        from .phase import apparent_magnitude

        return apparent_magnitude(body, jd_ut)
    from .stars import star_magnitude

    return star_magnitude(body)


def _target_signed_elongation(body: str, jd_ut: float) -> float:
    """
    Return signed solar elongation for planets, Moon, or fixed stars.

    Planetary and lunar elongation uses direct planetary longitudes; stellar
    elongation uses star coordinates at TT against the Sun at UT/TT.

    Raises:
        ValueError: Propagated by downstream ephemeris/stellar providers for
            unsupported body identities.

    Side effects: None.
    """
    if body in _HELIACAL_PLANETS or body == Body.MOON:
        return _signed_elongation(body, jd_ut)
    from .constants import Body as _Body
    from ._ephemeris_time import _ut1_to_ephemeris_tt
    from .julian import ut_to_tt
    from .planets import planet_at
    from .spk_reader import get_active_reader
    from .stars import star_at

    reader = get_active_reader()
    jd_tt = (
        ut_to_tt(jd_ut)
        if reader is None
        else _ut1_to_ephemeris_tt(jd_ut, reader)
    )
    star = star_at(body, jd_tt)
    sun = planet_at(_Body.SUN, jd_ut, jd_tt=jd_tt)
    return ((star.longitude - sun.longitude + 180.0) % 360.0) - 180.0


def _target_altitude(
    body: str,
    jd_ut: float,
    lat: float,
    lon: float,
    *,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
    relative_humidity: float = 0.0,
) -> float:
    """
    Return apparent altitude for a planet, Moon, or fixed star.

    Computes geometric altitude through ``moira.rise_set`` and then applies
    Moira's explicit atmospheric refraction correction.

    Raises:
        ValueError: Propagated by downstream altitude solver for invalid body
            identities or numeric inputs.

    Side effects: None.
    """
    return _planet_alt(
        body,
        jd_ut,
        lat,
        lon,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
        relative_humidity=relative_humidity,
    )


def _moon_horizontal_parallax_arcmin(jd_ut: float) -> float:
    """
    Compute lunar horizontal parallax in arcminutes at a UT1 instant.

    Returns 0.0 when the Moon distance is non-positive.

    Raises:
        ValueError: Propagated if ephemeris provider returns invalid numeric
            values.

    Side effects: None.
    """
    from .constants import EARTH_RADIUS_KM
    from .planets import planet_at

    moon = planet_at(Body.MOON, jd_ut)
    if moon.distance <= 0.0:
        return 0.0
    parallax_deg = math.degrees(math.asin(min(1.0, EARTH_RADIUS_KM / moon.distance)))
    return parallax_deg * 60.0


def _yallop_visibility_class(q: float) -> LunarCrescentVisibilityClass:
    """
    Classify a Yallop q-value into A-F lunar crescent visibility class.

    Thresholds follow the admitted Yallop boundary table.

    Side effects: None.
    """
    if q > 0.216:
        return LunarCrescentVisibilityClass.A
    if q > -0.014:
        return LunarCrescentVisibilityClass.B
    if q > -0.160:
        return LunarCrescentVisibilityClass.C
    if q > -0.232:
        return LunarCrescentVisibilityClass.D
    if q > -0.293:
        return LunarCrescentVisibilityClass.E
    return LunarCrescentVisibilityClass.F


def _yallop_class_observable(
    visibility_class: LunarCrescentVisibilityClass,
    observer_aid: ObserverAid,
) -> bool:
    """
    Resolve whether a Yallop class is observable for the given observing aid.

    A and B are naked-eye observable; C and D require binoculars or telescope;
    E and F are not observable.

    Side effects: None.
    """
    if visibility_class in (LunarCrescentVisibilityClass.A, LunarCrescentVisibilityClass.B):
        return True
    if visibility_class in (LunarCrescentVisibilityClass.C, LunarCrescentVisibilityClass.D):
        return observer_aid in (ObserverAid.BINOCULARS, ObserverAid.TELESCOPE)
    return False


def _lunar_crescent_details_at(
    jd_ut: float,
    lat: float,
    lon: float,
) -> LunarCrescentDetails:
    """
    Compute Yallop lunar crescent detail fields at a single instant.

    Produces the full ``LunarCrescentDetails`` vessel, including ARCL/ARCV,
    parallax-adjusted crescent width, q-value, and A-F class.

    Raises:
        ValueError: Propagated from coordinate/phase providers for invalid
            inputs.

    Side effects: None.
    """
    from .phase import elongation

    arcl_deg = elongation(Body.MOON, jd_ut)
    moon_azimuth_deg, moon_altitude_deg = _true_horizontal(Body.MOON, jd_ut, lat, lon)
    sun_azimuth_deg, sun_altitude_deg = _true_horizontal(Body.SUN, jd_ut, lat, lon)
    arcv_deg = moon_altitude_deg - sun_altitude_deg
    daz_deg = ((sun_azimuth_deg - moon_azimuth_deg + 180.0) % 360.0) - 180.0
    lunar_parallax_arcmin = _moon_horizontal_parallax_arcmin(jd_ut)
    parallax_deg = lunar_parallax_arcmin / 60.0
    semi_diameter_arcmin = 0.27245 * lunar_parallax_arcmin
    topocentric_crescent_width_arcmin = semi_diameter_arcmin * (
        1.0
        + math.sin(math.radians(moon_altitude_deg)) * math.sin(math.radians(parallax_deg))
    ) * (1.0 - math.cos(math.radians(arcl_deg)))
    q = (
        arcv_deg
        - (
            11.8371
            - 6.3226 * topocentric_crescent_width_arcmin
            + 0.7319 * topocentric_crescent_width_arcmin**2
            - 0.1018 * topocentric_crescent_width_arcmin**3
        )
    ) / 10.0
    return LunarCrescentDetails(
        best_time_jd_ut=jd_ut,
        sunset_jd_ut=jd_ut,
        moonset_jd_ut=jd_ut,
        lag_minutes=0.0,
        arcl_deg=arcl_deg,
        arcv_deg=arcv_deg,
        daz_deg=daz_deg,
        moon_altitude_deg=moon_altitude_deg,
        sun_altitude_deg=sun_altitude_deg,
        lunar_parallax_arcmin=lunar_parallax_arcmin,
        topocentric_crescent_width_arcmin=topocentric_crescent_width_arcmin,
        q=q,
        visibility_class=_yallop_visibility_class(q),
    )


def _lunar_crescent_details_for_evening(
    jd_midnight: float,
    lat: float,
    lon: float,
) -> LunarCrescentDetails | None:
    """
    Compute evening crescent details using sunset-to-moonset best-time rule.

    Returns None if sunset is absent, moonset is absent, or moonset does not
    occur after sunset on the same evening window.

    Side effects: None.
    """
    from .rise_set import find_phenomena, twilight_times

    twilight = twilight_times(jd_midnight, lat, lon)
    sunset_jd = twilight.sunset
    if sunset_jd is None:
        return None
    moon_events = find_phenomena(Body.MOON, sunset_jd - 0.25, lat, lon)
    moonset_jd = moon_events.get("Set")
    if moonset_jd is None or moonset_jd <= sunset_jd:
        return None
    best_time_jd = sunset_jd + (4.0 / 9.0) * (moonset_jd - sunset_jd)
    details = _lunar_crescent_details_at(best_time_jd, lat, lon)
    return LunarCrescentDetails(
        best_time_jd_ut=best_time_jd,
        sunset_jd_ut=sunset_jd,
        moonset_jd_ut=moonset_jd,
        lag_minutes=(moonset_jd - sunset_jd) * 24.0 * 60.0,
        arcl_deg=details.arcl_deg,
        arcv_deg=details.arcv_deg,
        daz_deg=details.daz_deg,
        moon_altitude_deg=details.moon_altitude_deg,
        sun_altitude_deg=details.sun_altitude_deg,
        lunar_parallax_arcmin=details.lunar_parallax_arcmin,
        topocentric_crescent_width_arcmin=details.topocentric_crescent_width_arcmin,
        q=details.q,
        visibility_class=details.visibility_class,
    )


def _lunar_crescent_details_for_morning(
    jd_midnight: float,
    lat: float,
    lon: float,
) -> LunarCrescentDetails | None:
    """
    Compute morning crescent details using moonrise-to-sunrise best-time rule.

    Returns None if sunrise is absent, moonrise is absent, or moonrise occurs
    after sunrise in the morning window.

    Side effects: None.
    """
    from .rise_set import find_phenomena, twilight_times

    twilight = twilight_times(jd_midnight, lat, lon)
    sunrise_jd = twilight.sunrise
    if sunrise_jd is None:
        return None
    moon_events = find_phenomena(Body.MOON, sunrise_jd - 0.75, lat, lon)
    moonrise_jd = moon_events.get("Rise")
    if moonrise_jd is None or moonrise_jd >= sunrise_jd:
        return None
    best_time_jd = sunrise_jd - (4.0 / 9.0) * (sunrise_jd - moonrise_jd)
    details = _lunar_crescent_details_at(best_time_jd, lat, lon)
    return LunarCrescentDetails(
        best_time_jd_ut=best_time_jd,
        sunset_jd_ut=sunrise_jd,
        moonset_jd_ut=moonrise_jd,
        lag_minutes=(sunrise_jd - moonrise_jd) * 24.0 * 60.0,
        arcl_deg=details.arcl_deg,
        arcv_deg=details.arcv_deg,
        daz_deg=details.daz_deg,
        moon_altitude_deg=details.moon_altitude_deg,
        sun_altitude_deg=details.sun_altitude_deg,
        lunar_parallax_arcmin=details.lunar_parallax_arcmin,
        topocentric_crescent_width_arcmin=details.topocentric_crescent_width_arcmin,
        q=details.q,
        visibility_class=details.visibility_class,
    )


def _find_sun_at_alt(
    jd_midnight: float,
    lat: float,
    lon: float,
    target_alt: float,
    morning: bool,
) -> float | None:
    """
    Find the JD when the Sun's altitude equals *target_alt* within one
    half-day window.

    Parameters
    ----------
    jd_midnight : JD of the midnight that begins the civil day being searched.
    morning     : True  → search the morning half [midnight, noon].
                  False → search the evening half [noon, next-midnight].
    target_alt  : Target solar altitude (negative for twilight, e.g. −12.0).

    Returns None if no crossing exists (polar day/night, or wrong half-day).

    Raises:
        ValueError: Propagated from solar-altitude computation for invalid
            numeric inputs.

    Side effects: None.
    """
    t0 = jd_midnight if morning else jd_midnight + 0.5
    t1 = t0 + 0.5
    a0 = _sun_alt(t0, lat, lon)
    a1 = _sun_alt(t1, lat, lon)

    if morning:
        # Sun should be rising through target: a0 â‰¤ target â‰¤ a1
        if not (a0 <= target_alt <= a1):
            return None
    else:
        # Sun should be descending through target: a1 â‰¤ target â‰¤ a0
        if not (a1 <= target_alt <= a0):
            return None

    for _ in range(22):
        tm = (t0 + t1) * 0.5
        am = _sun_alt(tm, lat, lon)
        if (a0 - target_alt) * (am - target_alt) <= 0.0:
            t1, a1 = tm, am
        else:
            t0, a0 = tm, am
    return (t0 + t1) * 0.5


def _check_visibility(
    body: str,
    jd_midnight: float,
    lat: float,
    lon: float,
    morning: bool,
    model: VisibilityModel,
    use_refraction: bool = True,
) -> tuple[float, float, float, float] | None:
    """
    Check whether *body* is visible at the arcus-visionis twilight moment on
    the given day.

    Returns ``(twilight_jd, planet_alt_deg, sun_alt_deg, magnitude)`` if
    visible, else ``None``.

    ``use_refraction`` governs the altitude used for the horizon test.  It must
    match the public ``VisibilityPolicy`` used to assess the returned event.

    Raises:
        ValueError: Propagated by downstream magnitude/altitude helpers for
            invalid inputs.

    Side effects: None.
    """
    mag = _target_apparent_magnitude(body, jd_midnight + 0.5)
    av = _arcus_visionis(mag, model)
    twilight_jd = _find_sun_at_alt(jd_midnight, lat, lon, -av, morning)
    if twilight_jd is None:
        return None
    planet_alt = (
        _target_altitude(
            body,
            twilight_jd,
            lat,
            lon,
            pressure_mbar=model.pressure_mbar,
            temperature_c=model.temperature_c,
            relative_humidity=model.relative_humidity,
        )
        if use_refraction
        else _true_altitude(body, twilight_jd, lat, lon)
    )
    if planet_alt <= model.horizon_altitude_deg:
        return None
    return twilight_jd, planet_alt, -av, mag


def _validate_args(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    search_days: int,
) -> None:
    """
    Validate core planetary heliacal search arguments.

    Raises:
        ValueError: If body is not an admitted heliacal planet, jd_start is
            non-finite, lat/lon are out of range, or search_days is not a
            positive integer.

    Side effects: None.
    """
    if body not in _HELIACAL_PLANETS:
        raise ValueError(
            f"body must be a planet (not SUN, MOON, or EARTH); got {body!r}"
        )
    if not math.isfinite(jd_start):
        raise ValueError(f"jd_start must be finite, got {jd_start}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon}")
    if not (isinstance(search_days, int) and search_days > 0):
        raise ValueError(f"search_days must be a positive integer, got {search_days!r}")


def _target_kind(body: str) -> VisibilityTargetKind:
    """
    Classify a body identifier into PLANET, MOON, or STAR target kind.

    Side effects: None.
    """
    if body in _HELIACAL_PLANETS:
        return VisibilityTargetKind.PLANET
    if body == Body.MOON:
        return VisibilityTargetKind.MOON
    return VisibilityTargetKind.STAR


def _check_visibility_with_target_alt(
    body: str,
    jd_midnight: float,
    lat: float,
    lon: float,
    morning: bool,
    target_solar_altitude_deg: float,
    model: VisibilityModel,
    use_refraction: bool = True,
) -> tuple[float, float, float, float] | None:
    """
    Evaluate visibility on a day at an explicit solar-altitude threshold.

    Returns ``(twilight_jd, target_alt_deg, sun_alt_deg, magnitude)`` when the
    target is above local horizon and bright enough at the threshold moment.

    ``use_refraction`` governs the altitude used for the horizon test.

    Side effects: None.
    """
    mag = _target_apparent_magnitude(body, jd_midnight + 0.5)

    twilight_jd = _find_sun_at_alt(jd_midnight, lat, lon, target_solar_altitude_deg, morning)
    if twilight_jd is None:
        return None
    planet_alt = (
        _target_altitude(
            body,
            twilight_jd,
            lat,
            lon,
            pressure_mbar=model.pressure_mbar,
            temperature_c=model.temperature_c,
            relative_humidity=model.relative_humidity,
        )
        if use_refraction
        else _true_altitude(body, twilight_jd, lat, lon)
    )
    if planet_alt <= model.horizon_altitude_deg:
        return None
    if mag > model.limiting_magnitude:
        return None
    return twilight_jd, planet_alt, target_solar_altitude_deg, mag


def _general_event_from_tuple(
    body: str,
    kind: HeliacalEventKind,
    event_tuple: tuple[float, float, float, float, float],
    lat: float,
    lon: float,
    *,
    visibility_policy: VisibilityPolicy | None,
) -> GeneralVisibilityEvent:
    """
    Build ``GeneralVisibilityEvent`` from tuple payload plus assessment.

    This helper normalizes tuple-based search output into the public event
    vessel and injects the computed ``VisibilityAssessment``.

    Side effects: None.
    """
    jd_ev, target_alt, sun_alt, mag, elong = event_tuple
    assessment = visibility_assessment(
        body,
        jd_ev,
        lat,
        lon,
        policy=visibility_policy,
    )
    return GeneralVisibilityEvent(
        body=body,
        target_kind=_target_kind(body),
        kind=kind,
        jd_ut=jd_ev,
        elongation_deg=elong,
        target_altitude_deg=target_alt,
        sun_altitude_deg=sun_alt,
        apparent_magnitude=mag,
        assessment=assessment,
    )


def _general_event_from_jd(
    body: str,
    kind: HeliacalEventKind,
    jd_ev: float,
    lat: float,
    lon: float,
    *,
    sun_altitude_deg: float,
    visibility_policy: VisibilityPolicy | None,
) -> GeneralVisibilityEvent:
    """
    Build ``GeneralVisibilityEvent`` from a resolved event JD.

    Recomputes signed elongation and assessment at ``jd_ev`` and stores the
    supplied solar altitude from the upstream event source.

    Side effects: None.
    """
    assessment = visibility_assessment(
        body,
        jd_ev,
        lat,
        lon,
        policy=visibility_policy,
    )
    return GeneralVisibilityEvent(
        body=body,
        target_kind=_target_kind(body),
        kind=kind,
        jd_ut=jd_ev,
        elongation_deg=_target_signed_elongation(body, jd_ev),
        target_altitude_deg=assessment.apparent_altitude_deg,
        sun_altitude_deg=sun_altitude_deg,
        apparent_magnitude=assessment.apparent_magnitude,
        assessment=assessment,
        lunar_crescent_details=assessment.lunar_crescent_details,
    )


def _general_event_from_lunar_crescent_details(
    kind: HeliacalEventKind,
    details: LunarCrescentDetails,
    lat: float,
    lon: float,
    *,
    visibility_policy: VisibilityPolicy,
) -> GeneralVisibilityEvent:
    """
    Build ``GeneralVisibilityEvent`` from a lunar crescent details vessel.

    Used for Yallop-governed Moon events where crescent details are first-class
    output and must be preserved in the outer event vessel.

    Side effects: None.
    """
    assessment = visibility_assessment(
        Body.MOON,
        details.best_time_jd_ut,
        lat,
        lon,
        policy=visibility_policy,
    )
    return GeneralVisibilityEvent(
        body=Body.MOON,
        target_kind=VisibilityTargetKind.MOON,
        kind=kind,
        jd_ut=details.best_time_jd_ut,
        elongation_deg=_target_signed_elongation(Body.MOON, details.best_time_jd_ut),
        target_altitude_deg=assessment.apparent_altitude_deg,
        sun_altitude_deg=details.sun_altitude_deg,
        apparent_magnitude=assessment.apparent_magnitude,
        assessment=assessment,
        lunar_crescent_details=details,
    )


def _search_visibility_event(
    body: str,
    kind: HeliacalEventKind,
    jd_mid0: float,
    lat: float,
    lon: float,
    *,
    model: VisibilityModel,
    search_days: int,
    target_solar_altitude_deg: float | None = None,
    use_refraction: bool = True,
) -> tuple[float, float, float, float, float] | None:
    """
    Execute the core forward visibility-event search state machine.

    Returns the first qualifying event tuple for rising kinds, or the last
    qualifying visible tuple for setting kinds prior to loss conditions.

    The return payload is ``(jd_ut, target_alt_deg, sun_alt_deg,
    apparent_mag, signed_elongation_deg)``.

    ``use_refraction`` is forwarded to every daily visibility check so that
    search doctrine cannot diverge from the public assessment doctrine.

    Side effects: None.
    """
    morning = kind in (
        HeliacalEventKind.HELIACAL_RISING,
        HeliacalEventKind.HELIACAL_SETTING,
        HeliacalEventKind.COSMIC_RISING,
    )
    require_min_elongation = kind not in (
        HeliacalEventKind.COSMIC_RISING,
        HeliacalEventKind.COSMIC_SETTING,
    )
    check = (
        (
            lambda jd_midnight: _check_visibility(
                body,
                jd_midnight,
                lat,
                lon,
                morning=morning,
                model=model,
                use_refraction=use_refraction,
            )
        )
        if target_solar_altitude_deg is None
        else (
            lambda jd_midnight: _check_visibility_with_target_alt(
                body,
                jd_midnight,
                lat,
                lon,
                morning=morning,
                target_solar_altitude_deg=target_solar_altitude_deg,
                model=model,
                use_refraction=use_refraction,
            )
        )
    )

    if kind in (
        HeliacalEventKind.HELIACAL_RISING,
        HeliacalEventKind.ACRONYCHAL_RISING,
        HeliacalEventKind.COSMIC_RISING,
    ):
        for d in range(search_days):
            jd_midnight = jd_mid0 + d
            se = _target_signed_elongation(body, jd_midnight + 0.5)
            if morning and se >= 0.0:
                continue
            if not morning and se <= 0.0:
                continue
            if require_min_elongation and abs(se) < _ELONG_MIN:
                continue
            vis = check(jd_midnight)
            if vis is not None:
                jd_ev, target_alt, sun_alt, mag = vis
                return jd_ev, target_alt, sun_alt, mag, se
        return None

    last: tuple[float, float, float, float, float] | None = None
    for d in range(search_days):
        jd_midnight = jd_mid0 + d
        se = _target_signed_elongation(body, jd_midnight + 0.5)
        abs_se = abs(se)
        signed_side_ok = (morning and se < 0.0) or ((not morning) and se > 0.0)
        elong_ok = (not require_min_elongation) or abs_se >= _ELONG_MIN
        if signed_side_ok and elong_ok:
            vis = check(jd_midnight)
            if vis is not None:
                jd_ev, target_alt, sun_alt, mag = vis
                last = (jd_ev, target_alt, sun_alt, mag, se)
            elif last is not None and not require_min_elongation:
                return last
        elif last is not None:
            if not require_min_elongation or abs_se < _ELONG_MIN:
                return last
    return None


# ---------------------------------------------------------------------------
# VisibilityAssessment
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VisibilityAssessment:
    """
    RITE: The Visibility Verdict — the complete observability result for one instant.

    THEOREM: Immutable frozen dataclass carrying the single-instant observability
    assessment for a body under the currently admitted criterion families.

    RITE OF PURPOSE:
        Provides a fully auditable visibility result: geometry, raw and
        extinction-adjusted target magnitude, directional sky contributions,
        criterion validity, limiting threshold, margin, and final verdict.

    LAW OF OPERATION:
        Responsibilities:
            - Carry all intermediate and final values from a single call to
              visibility_assessment(), including physical-model validity and
              the named component result vessels.
            - Include lunar_crescent_details when criterion_family is
              YALLOP_LUNAR_CRESCENT.
            - Include moonlight_sky_nanolamberts when K&S 1991 moonlight model
              is active.
        Non-responsibilities:
            - Does not compute any of its fields (populated by
              visibility_assessment()).
            - Does not define the criterion family semantics.
        Dependencies:
            - VisibilityCriterionFamily, LunarCrescentDetails (optional).
        Structural invariants:
            - lunar_crescent_details is non-None iff criterion_family is
              YALLOP_LUNAR_CRESCENT.
            - criterion_applicable is false whenever an admitted physical
              formula refuses an out-of-domain evaluation.

    Canon: None (No applicable canon; aggregation result vessel).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.VisibilityAssessment",
        "risk": "low",
        "api": {
            "public_attributes": [
                "body", "jd_ut", "criterion_family",
                "effective_limiting_magnitude", "apparent_magnitude",
                "true_altitude_deg", "apparent_altitude_deg",
                "local_horizon_altitude_deg", "solar_elongation_deg",
                "is_geometrically_visible", "is_bright_enough", "observable",
                "lunar_crescent_details", "moonlight_sky_nanolamberts",
                "extinction_adjusted_magnitude", "visibility_margin_magnitude",
                "criterion_target_magnitude",
                "target_extinction_applied_separately",
                "criterion_applicable", "criterion_reason",
                "atmospheric_extinction", "twilight_sky_brightness",
                "point_source_threshold", "dark_sky_nanolamberts",
                "total_sky_nanolamberts"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller-populated via visibility_assessment()"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    body: str
    jd_ut: float
    criterion_family: VisibilityCriterionFamily
    effective_limiting_magnitude: float | None
    apparent_magnitude: float
    true_altitude_deg: float
    apparent_altitude_deg: float
    local_horizon_altitude_deg: float
    solar_elongation_deg: float
    is_geometrically_visible: bool
    is_bright_enough: bool
    observable: bool
    lunar_crescent_details: LunarCrescentDetails | None = None
    moonlight_sky_nanolamberts: float | None = None
    extinction_adjusted_magnitude: float | None = None
    visibility_margin_magnitude: float | None = None
    criterion_target_magnitude: float | None = None
    target_extinction_applied_separately: bool = False
    criterion_applicable: bool = True
    criterion_reason: str | None = None
    atmospheric_extinction: AtmosphericExtinctionAssessment | None = None
    twilight_sky_brightness: TwilightSkyBrightnessAssessment | None = None
    point_source_threshold: PointSourceVisibilityThreshold | None = None
    dark_sky_nanolamberts: float | None = None
    total_sky_nanolamberts: float | None = None


@dataclass(frozen=True, slots=True)
class GeneralVisibilityEvent:
    """
    RITE: The Event Vessel — the canonical result carrier for generalized
    visibility-event search.

    THEOREM: Immutable frozen dataclass carrying the primary result of a
    generalized visibility-event search across all admitted target families.

    RITE OF PURPOSE:
        Provides a unified result vessel for heliacal, acronychal, and cosmic
        visibility events across planets, fixed stars, and the Moon, carrying
        the event geometry (elongation, target altitude, sun altitude, magnitude)
        alongside the full VisibilityAssessment so that callers have both the
        event identification and its observability audit in one immutable record.

    LAW OF OPERATION:
        Responsibilities:
            - Carry body identity, target kind, event kind, event JD, and the
              key geometric quantities at the event moment.
            - Embed the full VisibilityAssessment for the event instant.
            - Include lunar_crescent_details at the outer vessel level for easy
              access when target_kind is MOON.
        Non-responsibilities:
            - Does not compute any of its fields (populated by
              _general_event_from_tuple(), _general_event_from_jd(), or
              _general_event_from_lunar_crescent_details()).
            - Does not define event-search algorithm.
        Dependencies:
            - VisibilityTargetKind, HeliacalEventKind, VisibilityAssessment,
              LunarCrescentDetails (optional).
        Structural invariants:
            - jd_ut is the UT1 Julian Day of the first visibility crossing.
            - assessment.body == body.

    Canon: None (No applicable canon; aggregation result vessel).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.GeneralVisibilityEvent",
        "risk": "low",
        "api": {
            "public_attributes": [
                "body", "target_kind", "kind", "jd_ut",
                "elongation_deg", "target_altitude_deg", "sun_altitude_deg",
                "apparent_magnitude", "assessment", "lunar_crescent_details"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller-populated via visibility_event()"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    body: str
    target_kind: VisibilityTargetKind
    kind: HeliacalEventKind
    jd_ut: float
    elongation_deg: float
    target_altitude_deg: float
    sun_altitude_deg: float
    apparent_magnitude: float
    assessment: VisibilityAssessment
    lunar_crescent_details: LunarCrescentDetails | None = None


# ---------------------------------------------------------------------------
# PlanetHeliacalEvent
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PlanetHeliacalEvent:
    """
    RITE: The Planetary Heliacal Record — the narrow result vessel for planetary
    visibility events.

    THEOREM: Immutable frozen dataclass carrying the narrow identification and
    geometry for a single planetary heliacal or acronychal visibility event.

    RITE OF PURPOSE:
        Provides a concise, backward-compatible result type for the V0 planetary
        event helpers (planet_heliacal_rising, planet_heliacal_setting,
        planet_acronychal_rising, planet_acronychal_setting), carrying only the
        event-geometry fields that planetary event callers need without the full
        VisibilityAssessment inner vessel.  Produced by
        _planet_event_from_general_event() from a GeneralVisibilityEvent.

    LAW OF OPERATION:
        Responsibilities:
            - Carry body name, event kind, Julian Day, elongation, planet altitude,
              sun altitude, and apparent magnitude for a planetary event.
            - Serve as the return type of the V0 planet_heliacal_* helpers.
        Non-responsibilities:
            - Does not carry the full VisibilityAssessment (use
              GeneralVisibilityEvent for that).
            - Does not store search policy or observer environment.
            - Cannot represent fixed-star or lunar events.
        Dependencies:
            - HeliacalEventKind (event-kind typing only).
        Structural invariants:
            - jd_ut is the UT1 Julian Day of the visibility threshold crossing.
            - sun_altitude_deg ≈ −arcus_visionis at jd_ut by construction.

    Canon: None (No applicable canon; narrow result vessel).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.heliacal.PlanetHeliacalEvent",
        "risk": "low",
        "api": {
            "public_attributes": [
                "body", "kind", "jd_ut", "elongation_deg",
                "planet_altitude_deg", "sun_altitude_deg", "apparent_magnitude"
            ]
        },
        "state": {
            "mutable": false
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller-populated via _planet_event_from_general_event()"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]

    Fields
    ------
    body : str
        Planet name (one of the ``Body.*`` constants).
    kind : HeliacalEventKind
        The event type.
    jd_ut : float
        Julian Day (UT1) of the event — the moment when the Sun's altitude
        equals ``−arcus_visionis`` (the visibility threshold crossing).
    elongation_deg : float
        Signed elongation from the Sun at the event day.
        Negative = west of Sun (morning sky).
        Positive = east of Sun (evening sky).
    planet_altitude_deg : float
        Planet's altitude above the observer's horizon at ``jd_ut``.
    sun_altitude_deg : float
        Sun's altitude at ``jd_ut`` (equals ``−arcus_visionis`` by construction).
    apparent_magnitude : float
        Planet's apparent V magnitude on the event date.
    """
    body:                  str
    kind:                  HeliacalEventKind
    jd_ut:                 float
    elongation_deg:        float
    planet_altitude_deg:   float
    sun_altitude_deg:      float
    apparent_magnitude:    float


# ---------------------------------------------------------------------------
# Public computation layer
# ---------------------------------------------------------------------------

# The public layer below preserves the legacy event path while admitting an
# opt-in, validity-bounded physical point-source assessment.  The physical
# criterion is intentionally not used by legacy event search until event-level
# doctrine and validation are admitted separately.

def physical_visibility_assessment(
    body: str,
    jd_ut: float,
    lat: float,
    lon: float,
    *,
    data_pack_config: VisibilityDataPackConfig,
    policy: PhysicalVisibilityPolicy | None = None,
) -> PhysicalVisibilityAssessment:
    """Evaluate the additive physical point-source criterion at one instant.

    The calculation uses only an explicit caller-supplied data-pack path.  It
    never searches for, downloads, or generates a data pack.  The legacy
    :func:`visibility_assessment` path is not consulted or changed.
    """

    return _physical_visibility_assessment_impl(
        body,
        jd_ut,
        lat,
        lon,
        data_pack_config=data_pack_config,
        policy=policy,
        loaded_data_pack=None,
    )


def _physical_visibility_assessment_impl(
    body: str,
    jd_ut: float,
    lat: float,
    lon: float,
    *,
    data_pack_config: VisibilityDataPackConfig,
    policy: PhysicalVisibilityPolicy | None,
    loaded_data_pack: VisibilityDataPack | None,
) -> PhysicalVisibilityAssessment:
    """Evaluate one instant, optionally reusing one validated immutable pack."""

    if not isinstance(body, str) or not body:
        raise ValueError("body must be a nonempty string")
    _validate_physical_request_coordinate(jd_ut, "jd_ut")
    _validate_physical_request_coordinate(lat, "lat")
    _validate_physical_request_coordinate(lon, "lon")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon}")
    if not isinstance(data_pack_config, VisibilityDataPackConfig):
        raise TypeError(
            "data_pack_config must be a VisibilityDataPackConfig"
        )

    resolved_policy = (
        policy if policy is not None else PhysicalVisibilityPolicy()
    )
    if not isinstance(resolved_policy, PhysicalVisibilityPolicy):
        raise TypeError("policy must be a PhysicalVisibilityPolicy")

    atmosphere_receipt = _physical_atmosphere_receipt(
        resolved_policy.atmosphere,
        within_data_pack_domain=None,
    )
    observer_receipt = _physical_observer_receipt(resolved_policy)

    if body not in _PHYSICAL_VISIBILITY_TARGETS:
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.NOT_APPLICABLE,
            "target_not_admitted",
            atmosphere_receipt=atmosphere_receipt,
            observer_receipt=observer_receipt,
        )
    if resolved_policy.background is None:
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY,
            "background_input_incomplete",
            atmosphere_receipt=atmosphere_receipt,
            observer_receipt=observer_receipt,
        )
    if (
        data_pack_config.expected_pack_id
        != resolved_policy.expected_data_pack_id
        or data_pack_config.expected_composite_model_id
        != resolved_policy.composite_model_id
        or (
            data_pack_config.expected_manifest_sha256 is not None
            and resolved_policy.expected_manifest_sha256 is not None
            and data_pack_config.expected_manifest_sha256
            != resolved_policy.expected_manifest_sha256
        )
    ):
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY,
            "visibility_data_pack_incompatible",
            atmosphere_receipt=atmosphere_receipt,
            observer_receipt=observer_receipt,
        )

    if loaded_data_pack is None:
        try:
            pack = load_visibility_data_pack(data_pack_config)
        except VisibilityDataPackLoadError as exc:
            return _physical_not_evaluable(
                body,
                jd_ut,
                lat,
                lon,
                resolved_policy,
                PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY,
                exc.reason,
                atmosphere_receipt=atmosphere_receipt,
                observer_receipt=observer_receipt,
            )
    else:
        if not isinstance(loaded_data_pack, VisibilityDataPack):
            raise TypeError(
                "loaded_data_pack must be a VisibilityDataPack"
            )
        pack = loaded_data_pack
        if (
            pack.receipt.pack_id
            != data_pack_config.expected_pack_id
            or pack.receipt.composite_model_id
            != data_pack_config.expected_composite_model_id
            or (
                data_pack_config.expected_manifest_sha256 is not None
                and pack.receipt.manifest_sha256
                != data_pack_config.expected_manifest_sha256
            )
        ):
            return _physical_not_evaluable(
                body,
                jd_ut,
                lat,
                lon,
                resolved_policy,
                PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY,
                "visibility_data_pack_incompatible",
                data_pack_receipt=pack.receipt,
                atmosphere_receipt=atmosphere_receipt,
                observer_receipt=observer_receipt,
            )

    if (
        resolved_policy.expected_manifest_sha256 is not None
        and pack.receipt.manifest_sha256
        != resolved_policy.expected_manifest_sha256
    ):
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY,
            "visibility_data_pack_checksum_mismatch",
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            observer_receipt=observer_receipt,
        )

    atmosphere_matches = _physical_atmosphere_matches(
        resolved_policy.atmosphere,
        pack.domain,
    )
    atmosphere_receipt = _physical_atmosphere_receipt(
        resolved_policy.atmosphere,
        within_data_pack_domain=atmosphere_matches,
    )
    if not atmosphere_matches:
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN,
            "atmosphere_input_out_of_domain",
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            validity_domain_receipt=_physical_domain_receipt(pack.domain),
            observer_receipt=observer_receipt,
        )

    from .spk_reader import MissingKernelError

    try:
        target_azimuth_deg, target_true_altitude_deg = (
            _true_horizontal(body, jd_ut, lat, lon)
        )
        solar_azimuth_deg, solar_true_altitude_deg = _true_horizontal(
            Body.SUN,
            jd_ut,
            lat,
            lon,
        )
    except MissingKernelError:
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY,
            "ephemeris_dependency_missing",
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            validity_domain_receipt=_physical_domain_receipt(pack.domain),
            observer_receipt=observer_receipt,
        )

    relative_solar_azimuth_deg = abs(
        (
            target_azimuth_deg
            - solar_azimuth_deg
            + 180.0
        )
        % 360.0
        - 180.0
    )
    apparent_target_altitude_deg = apply_refraction(
        target_true_altitude_deg,
        pressure_mbar=resolved_policy.refraction_pressure_hpa,
        temperature_c=resolved_policy.refraction_temperature_c,
        relative_humidity=(
            resolved_policy.refraction_relative_humidity
        ),
    )
    horizon_receipt = _physical_event_horizon_receipt(
        resolved_policy,
        pack.domain,
        target_azimuth_deg=target_azimuth_deg,
        solar_azimuth_deg=solar_azimuth_deg,
    )
    target_local_horizon_altitude_deg = (
        horizon_receipt.target_local_horizon_altitude_deg
    )
    assert target_local_horizon_altitude_deg is not None
    geometrically_visible = (
        apparent_target_altitude_deg
        >= target_local_horizon_altitude_deg
    )

    if not geometrically_visible:
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.NOT_APPLICABLE,
            "target_below_local_horizon",
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            validity_domain_receipt=_physical_domain_receipt(
                pack.domain,
                target_true_altitude_deg=target_true_altitude_deg,
            ),
            observer_receipt=observer_receipt,
            true_target_altitude_deg=target_true_altitude_deg,
            apparent_target_altitude_deg=(
                apparent_target_altitude_deg
            ),
            true_solar_center_altitude_deg=solar_true_altitude_deg,
            relative_solar_azimuth_deg=(
                relative_solar_azimuth_deg
            ),
            geometrically_visible=False,
            observable=False,
            horizon_receipt=horizon_receipt,
        )

    try:
        photometry_context = _physical_target_photometry_context(
            body,
            jd_ut,
        )
    except (KeyError, MissingKernelError, ValueError):
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY,
            "target_photometry_missing",
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            validity_domain_receipt=_physical_domain_receipt(
                pack.domain,
                target_true_altitude_deg=target_true_altitude_deg,
            ),
            observer_receipt=observer_receipt,
            true_target_altitude_deg=target_true_altitude_deg,
            apparent_target_altitude_deg=(
                apparent_target_altitude_deg
            ),
            true_solar_center_altitude_deg=solar_true_altitude_deg,
            relative_solar_azimuth_deg=(
                relative_solar_azimuth_deg
            ),
            geometrically_visible=True,
            horizon_receipt=horizon_receipt,
        )
    target_magnitude = photometry_context.apparent_magnitude
    phase_angle_deg = photometry_context.phase_angle_deg
    saturn_ring_latitude_deg = (
        photometry_context.saturn_effective_ring_sub_latitude_deg
    )
    if (
        photometry_context.geometry_valid is not True
        or isinstance(target_magnitude, bool)
        or not isinstance(target_magnitude, (int, float))
        or not math.isfinite(target_magnitude)
        or (
            body in _PHYSICAL_VISIBILITY_PLANETS
            and (
                isinstance(phase_angle_deg, bool)
                or not isinstance(phase_angle_deg, (int, float))
                or not math.isfinite(phase_angle_deg)
            )
        )
        or (
            body in _PHYSICAL_VISIBILITY_STARS
            and (
                not isinstance(
                    photometry_context.catalog_name,
                    str,
                )
                or not photometry_context.catalog_name
                or not isinstance(
                    photometry_context.catalog_nomenclature,
                    str,
                )
                or not photometry_context.catalog_nomenclature
            )
        )
        or (
            saturn_ring_latitude_deg is not None
            and (
                isinstance(saturn_ring_latitude_deg, bool)
                or not isinstance(
                    saturn_ring_latitude_deg,
                    (int, float),
                )
                or not math.isfinite(saturn_ring_latitude_deg)
            )
        )
    ):
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY,
            "target_photometry_missing",
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            validity_domain_receipt=_physical_domain_receipt(
                pack.domain,
                target_true_altitude_deg=target_true_altitude_deg,
            ),
            observer_receipt=observer_receipt,
            true_target_altitude_deg=target_true_altitude_deg,
            apparent_target_altitude_deg=(
                apparent_target_altitude_deg
            ),
            true_solar_center_altitude_deg=solar_true_altitude_deg,
            relative_solar_azimuth_deg=(
                relative_solar_azimuth_deg
            ),
            geometrically_visible=True,
            horizon_receipt=horizon_receipt,
        )

    try:
        if body in _PHYSICAL_VISIBILITY_PLANETS:
            assert isinstance(phase_angle_deg, (int, float))
            target_profile = pack.resolve_target_profile(
                body,
                VisibilityTargetContext(
                    phase_angle_deg=float(phase_angle_deg),
                    saturn_effective_ring_sub_latitude_deg=(
                        saturn_ring_latitude_deg
                    ),
                ),
            )
            photometry_model_id = (
                _PHYSICAL_PLANET_PHOTOMETRY_MODEL_ID
            )
            photometry_source_ids = (
                _PHYSICAL_PLANET_PHOTOMETRY_SOURCE_IDS
            )
        else:
            assert photometry_context.catalog_name is not None
            assert (
                photometry_context.catalog_nomenclature is not None
            )
            target_profile = pack.resolve_stellar_target_profile(
                body,
                catalog_name=photometry_context.catalog_name,
                catalog_nomenclature=(
                    photometry_context.catalog_nomenclature
                ),
                catalog_visual_magnitude=target_magnitude,
            )
            target_magnitude = target_profile.visual_magnitude
            photometry_model_id = target_profile.photometry_model_id
            photometry_source_ids = (
                target_profile.photometry_source_ids
            )
    except (
        VisibilityStellarTargetProfileError,
        VisibilityTargetProfileError,
    ) as exc:
        evidence_state = (
            PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN
            if exc.reason == "target_spectral_profile_out_of_domain"
            else PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY
        )
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            evidence_state,
            exc.reason,
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            validity_domain_receipt=_physical_domain_receipt(
                pack.domain,
                target_true_altitude_deg=target_true_altitude_deg,
            ),
            observer_receipt=observer_receipt,
            true_target_altitude_deg=target_true_altitude_deg,
            apparent_target_altitude_deg=(
                apparent_target_altitude_deg
            ),
            true_solar_center_altitude_deg=solar_true_altitude_deg,
            relative_solar_azimuth_deg=(
                relative_solar_azimuth_deg
            ),
            geometrically_visible=True,
            horizon_receipt=horizon_receipt,
        )

    internal_profile = _TargetSpectralProfile(
        target_id=target_profile.target_id,
        top_of_atmosphere_visual_magnitude=target_magnitude,
        scotopic_to_photopic_ratio=(
            target_profile.scotopic_to_photopic_ratio
        ),
        photopic_extinction_weights=(
            target_profile.photopic_extinction_weights
        ),
        scotopic_extinction_weights=(
            target_profile.scotopic_extinction_weights
        ),
        photometry_model_id=photometry_model_id,
        photometry_source_ids=photometry_source_ids,
        spectral_profile_id=target_profile.spectral_profile_id,
        spectral_source_ids=target_profile.spectral_source_ids,
        spectral_source_receipt_sha256=(
            target_profile.spectral_source_receipt_sha256
        ),
        spectral_model_details=(
            target_profile.spectral_model_details
        ),
    )
    internal_background = _resolve_physical_background(
        resolved_policy.background
    )
    internal_modeled_background_components = (
        _resolve_modeled_background_components(
            resolved_policy.modeled_background_components
        )
    )
    modeled_twilight = (
        internal_background.scope == "dark_sky_anchor"
    )
    domain_receipt = _physical_domain_receipt(
        pack.domain,
        solar_center_altitude_deg=(
            solar_true_altitude_deg if modeled_twilight else None
        ),
        target_true_altitude_deg=target_true_altitude_deg,
        relative_solar_azimuth_deg=(
            relative_solar_azimuth_deg if modeled_twilight else None
        ),
    )

    try:
        if modeled_twilight:
            truth = spectral_single_epoch_truth(
                pack,
                internal_profile,
                target_true_altitude_deg=target_true_altitude_deg,
                solar_center_altitude_deg=solar_true_altitude_deg,
                relative_solar_azimuth_deg=(
                    relative_solar_azimuth_deg
                ),
                dark_sky_anchor=internal_background,
                modeled_background_components=(
                    internal_modeled_background_components
                ),
            )
        else:
            truth = spectral_single_epoch_truth(
                pack,
                internal_profile,
                target_true_altitude_deg=target_true_altitude_deg,
                measured_total_background=internal_background,
                modeled_background_components=(
                    internal_modeled_background_components
                ),
            )
    except VisibilityDataPackDomainError as exc:
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN,
            exc.reason,
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            validity_domain_receipt=domain_receipt,
            observer_receipt=observer_receipt,
            true_target_altitude_deg=target_true_altitude_deg,
            apparent_target_altitude_deg=(
                apparent_target_altitude_deg
            ),
            true_solar_center_altitude_deg=solar_true_altitude_deg,
            relative_solar_azimuth_deg=(
                relative_solar_azimuth_deg
            ),
            geometrically_visible=True,
            horizon_receipt=horizon_receipt,
        )
    except PhysicalVisibilityCompositionError as exc:
        evidence_state = (
            PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN
            if exc.reason == "criterion_out_of_domain"
            else PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY
        )
        return _physical_not_evaluable(
            body,
            jd_ut,
            lat,
            lon,
            resolved_policy,
            evidence_state,
            exc.reason,
            data_pack_receipt=pack.receipt,
            atmosphere_receipt=atmosphere_receipt,
            validity_domain_receipt=domain_receipt,
            observer_receipt=observer_receipt,
            true_target_altitude_deg=target_true_altitude_deg,
            apparent_target_altitude_deg=(
                apparent_target_altitude_deg
            ),
            true_solar_center_altitude_deg=solar_true_altitude_deg,
            relative_solar_azimuth_deg=(
                relative_solar_azimuth_deg
            ),
            geometrically_visible=True,
            horizon_receipt=horizon_receipt,
        )

    return PhysicalVisibilityAssessment(
        body=body,
        jd_ut=jd_ut,
        latitude_deg=lat,
        longitude_deg=lon,
        status=PhysicalVisibilityStatus.EVALUATED,
        evidence_state=(
            PhysicalVisibilityEvidenceState.EVALUATED_CLEAR_SKY
        ),
        reason=None,
        true_target_altitude_deg=target_true_altitude_deg,
        apparent_target_altitude_deg=apparent_target_altitude_deg,
        true_solar_center_altitude_deg=solar_true_altitude_deg,
        relative_solar_azimuth_deg=relative_solar_azimuth_deg,
        geometrically_visible=True,
        visible=truth.visible,
        observable=truth.visible,
        visibility_margin_magnitude=(
            truth.visibility_margin_magnitude
        ),
        data_pack_receipt=truth.data_pack_receipt,
        atmosphere_receipt=atmosphere_receipt,
        validity_domain_receipt=domain_receipt,
        observer_protocol_receipt=observer_receipt,
        background_receipt=_physical_background_receipt(truth),
        target_receipt=_physical_target_receipt(
            truth.target,
            internal_profile,
        ),
        threshold_receipt=_physical_threshold_receipt(
            truth.threshold
        ),
        error_budget_receipt=_physical_error_budget_receipt(
            truth.error_budget
        ),
        components=(
            *_physical_component_receipts(truth.components),
            *_physical_horizon_component_receipts(resolved_policy),
        ),
        horizon_receipt=horizon_receipt,
    )


def _physical_phase_rule(
    phase: PhysicalVisibilityPhase,
) -> _ObservationPhaseRule:
    rising = phase in {
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        PhysicalVisibilityPhase.EVENING_LAST_RISING,
    }
    morning = phase in {
        PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        PhysicalVisibilityPhase.MORNING_FIRST_SETTING,
    }
    return _ObservationPhaseRule(
        solar_side="morning" if morning else "evening",
        target_boundary_role="rising" if rising else "setting",
        crossing_direction=(
            "negative_to_positive"
            if rising
            else "positive_to_negative"
        ),
        day_ownership="first" if morning else "last",
    )


def _physical_event_horizon_receipt(
    policy: PhysicalVisibilityPolicy,
    data_pack_domain: VisibilityDataPackDomain | None = None,
    *,
    target_azimuth_deg: float | None = None,
    solar_azimuth_deg: float | None = None,
) -> PhysicalHorizonReceipt:
    profile = policy.directional_horizon
    target_local_horizon = (
        _physical_local_horizon_altitude(
            policy,
            target_azimuth_deg,
        )
        if profile is None or target_azimuth_deg is not None
        else None
    )
    solar_local_horizon = (
        _physical_local_horizon_altitude(
            policy,
            solar_azimuth_deg,
        )
        if profile is None or solar_azimuth_deg is not None
        else None
    )
    target_boundary = target_local_horizon
    target_true_floor: float | None = None
    pack_floor_apparent: float | None = None
    narrowing_applied = False
    if data_pack_domain is not None:
        target_true_floor = (
            data_pack_domain.target_true_altitude_deg[0]
        )
        pack_floor_apparent = apply_refraction(
            target_true_floor,
            pressure_mbar=policy.refraction_pressure_hpa,
            temperature_c=policy.refraction_temperature_c,
            relative_humidity=(
                policy.refraction_relative_humidity
            ),
        )
        if (
            target_boundary is not None
            and pack_floor_apparent > target_boundary
        ):
            target_boundary = pack_floor_apparent
            narrowing_applied = True
    event_certificate = (
        _physical_horizon_signal_certificate(
            policy,
            role="target" if data_pack_domain is not None else "profile",
            additional_constant_altitude_deg=pack_floor_apparent,
        )
        if profile is not None
        else None
    )
    if profile is not None:
        horizon_model_id = (
            "directional_circular_linear_apparent_horizon_"
            "with_pack_floor_v1"
            if data_pack_domain is not None
            else "directional_circular_linear_apparent_horizon_v1"
        )
    else:
        horizon_model_id = (
            "scalar_apparent_horizon_with_pack_floor_v2"
            if data_pack_domain is not None
            else "scalar_apparent_horizon_v1"
        )
    return PhysicalHorizonReceipt(
        horizon_model_id=horizon_model_id,
        apparent_horizon_altitude_deg=(
            None
            if profile is not None
            else policy.local_horizon_altitude_deg
        ),
        directional_profile_applied=profile is not None,
        refraction_model_id=policy.refraction_model_id,
        refraction_pressure_hpa=policy.refraction_pressure_hpa,
        refraction_temperature_c=policy.refraction_temperature_c,
        refraction_relative_humidity=(
            policy.refraction_relative_humidity
        ),
        applied_to=("target", "Sun"),
        target_apparent_boundary_altitude_deg=target_boundary,
        solar_apparent_horizon_altitude_deg=solar_local_horizon,
        data_pack_target_true_altitude_floor_deg=target_true_floor,
        target_boundary_narrowing_applied=narrowing_applied,
        directional_profile_id=(
            profile.profile_id if profile is not None else None
        ),
        directional_profile_source_id=(
            profile.source_id if profile is not None else None
        ),
        directional_profile_source_receipt_sha256=(
            profile.source_receipt_sha256
            if profile is not None
            else None
        ),
        interpolation_method_id=(
            profile.interpolation_method_id
            if profile is not None
            else None
        ),
        profile_sample_count=(
            len(profile.samples) if profile is not None else None
        ),
        admitted_maximum_gap_deg=(
            profile.admitted_maximum_gap_deg
            if profile is not None
            else None
        ),
        actual_maximum_gap_deg=(
            profile.actual_maximum_gap_deg
            if profile is not None
            else None
        ),
        maximum_absolute_slope_deg_per_deg=(
            profile.maximum_absolute_slope_deg_per_deg
            if profile is not None
            else None
        ),
        cone_signal_lipschitz_factor=(
            _physical_horizon_cone_factor(
                profile.samples,
                profile.maximum_absolute_slope_deg_per_deg,
                additional_constant_altitude_deg=(
                    pack_floor_apparent
                ),
            )
            if profile is not None
            else None
        ),
        queried_target_azimuth_deg=target_azimuth_deg,
        queried_solar_azimuth_deg=solar_azimuth_deg,
        target_local_horizon_altitude_deg=target_local_horizon,
        solar_local_horizon_altitude_deg=solar_local_horizon,
        event_certificate_id=(
            event_certificate.certificate_id
            if event_certificate is not None
            else _PHYSICAL_EVENT_GEOMETRY_CERTIFICATE.certificate_id
        ),
        event_certificate_source_sha256=(
            event_certificate.source_receipt_sha256
            if event_certificate is not None
            else (
                _PHYSICAL_EVENT_GEOMETRY_CERTIFICATE
                .source_receipt_sha256
            )
        ),
        event_certificate_maximum_absolute_rate_per_day=(
            event_certificate.maximum_absolute_rate_per_day
            if event_certificate is not None
            else (
                _PHYSICAL_EVENT_GEOMETRY_CERTIFICATE
                .maximum_absolute_rate_per_day
            )
        ),
    )


def _physical_local_horizon_altitude(
    policy: PhysicalVisibilityPolicy,
    azimuth_deg: float | None,
) -> float:
    profile = policy.directional_horizon
    if profile is None:
        return policy.local_horizon_altitude_deg
    if azimuth_deg is None:
        raise ValueError(
            "directional horizon evaluation requires an azimuth"
        )
    return profile.apparent_altitude_at(azimuth_deg)


def _physical_directional_horizon_signal(
    apparent_altitude_deg: float,
    boundary_altitude_deg: float,
) -> float:
    """Return a zenith-safe signal with the sign of altitude minus terrain."""

    apparent_altitude_rad = math.radians(apparent_altitude_deg)
    boundary_altitude_rad = math.radians(boundary_altitude_deg)
    horizontal_projection = max(
        0.0,
        math.cos(apparent_altitude_rad),
    )
    return (
        math.sin(apparent_altitude_rad)
        - horizontal_projection * math.tan(boundary_altitude_rad)
    )


def _physical_horizon_signal_certificate(
    policy: PhysicalVisibilityPolicy,
    *,
    role: str,
    additional_constant_altitude_deg: float | None = None,
) -> _ScalarLipschitzCertificate:
    profile = policy.directional_horizon
    if profile is None:
        return _PHYSICAL_EVENT_GEOMETRY_CERTIFICATE
    cone_factor = _physical_horizon_cone_factor(
        profile.samples,
        profile.maximum_absolute_slope_deg_per_deg,
        additional_constant_altitude_deg=(
            additional_constant_altitude_deg
        ),
    )
    maximum_rate = (
        math.radians(
            _PHYSICAL_DIRECTIONAL_HORIZON_BASE_RATE_PER_DAY
        )
        * (
            1.0
            + cone_factor
        )
    )
    return _ScalarLipschitzCertificate(
        certificate_id=(
            "physical-heliacal-event-lipschitz-v1:"
            f"directional-horizon:{role}:"
            f"{profile.source_receipt_sha256}"
        ),
        maximum_absolute_rate_per_day=maximum_rate,
        source_receipt_sha256=(
            _PHYSICAL_DIRECTIONAL_HORIZON_CERTIFICATE_SHA256
        ),
        maximum_subdivision_depth=(
            _PHYSICAL_EVENT_GEOMETRY_CERTIFICATE
            .maximum_subdivision_depth
        ),
    )


def _physical_event_ephemeris_receipt(
    body: str,
) -> PhysicalEphemerisReceipt:
    return PhysicalEphemerisReceipt(
        provider_id=(
            "moira_active_reader_and_sovereign_star_registry_v1"
            if body in _PHYSICAL_VISIBILITY_STARS
            else "moira_active_planetary_reader_v1"
        ),
        input_timescale="UT1 Julian day",
        ephemeris_timescale="reader_resolved_TT",
        direction_frame="apparent_geocentric_equatorial",
        horizontal_frame="local_apparent_sidereal_horizon",
        refraction_applied_separately=True,
    )


def _physical_event_scans(
    selection: _PhaseTransitionSelection | None,
) -> tuple[_ScalarIntervalScan, ...]:
    if selection is None:
        return ()
    scans: list[_ScalarIntervalScan] = []
    for day in selection.classified_days:
        construction = day.construction
        scans.append(construction.solar_horizon_scan)
        if construction.solar_domain_scan is not None:
            scans.append(construction.solar_domain_scan)
        if construction.target_horizon_scan is not None:
            scans.append(construction.target_horizon_scan)
        if construction.target_domain_scan is not None:
            scans.append(construction.target_domain_scan)
        for window in day.window_solutions:
            if window.margin_scan is not None:
                scans.append(window.margin_scan)
    return tuple(scans)


def _physical_event_solver_receipt(
    search_policy: PhysicalVisibilitySearchPolicy,
    candidate_day_keys: tuple[int, ...],
    selection: _PhaseTransitionSelection | None,
    policy: PhysicalVisibilityPolicy,
) -> PhysicalEventSolverReceipt:
    scans = _physical_event_scans(selection)
    classified = (
        selection.classified_days if selection is not None else ()
    )
    roots = tuple(root for scan in scans for root in scan.roots)
    gaps = tuple(gap for scan in scans for gap in scan.gaps)
    near_zero = tuple(
        interval
        for scan in scans
        for interval in scan.near_zero_intervals
    )
    sample_gaps = tuple(
        scan.maximum_sample_gap_days for scan in scans
    )
    candidate_set = set(candidate_day_keys)
    guard_count = sum(
        day.observation_day_key not in candidate_set
        for day in classified
    )
    unresolved_certificate_intervals = tuple(
        interval
        for scan in scans
        for interval in scan.unresolved_intervals
    )
    certificate_ids = tuple(
        sorted(
            {
                scan.certificate_id
                for scan in scans
                if scan.certificate_id is not None
            }
        )
    )
    completeness_state = (
        "not_evaluated"
        if not scans
        else "certified_lipschitz_zero_enclosure"
        if all(
            scan.crossing_completeness_state
            == "certified_lipschitz_zero_enclosure"
            for scan in scans
        )
        else "not_certified"
    )
    completeness_reason = (
        "event_not_evaluated"
        if not scans
        else None
        if completeness_state
        == "certified_lipschitz_zero_enclosure"
        else "certificate_left_unresolved_intervals"
    )
    return PhysicalEventSolverReceipt(
        search_window_days=search_policy.search_window_days,
        scan_step_days=search_policy.scan_step_days,
        bracket_tolerance_days=(
            search_policy.adaptive_minimum_step_days
        ),
        adaptive_minimum_step_days=(
            search_policy.adaptive_minimum_step_days
        ),
        root_time_tolerance_days=(
            search_policy.root_time_tolerance_days
        ),
        root_margin_tolerance_magnitude=(
            search_policy.root_margin_tolerance_magnitude
        ),
        near_zero_tolerance_magnitude=(
            search_policy.near_zero_tolerance_magnitude
        ),
        curvature_tolerance_magnitude=(
            search_policy.curvature_tolerance_magnitude
        ),
        candidate_day_count=len(candidate_day_keys),
        guard_day_count=guard_count,
        classified_day_count=len(classified),
        evaluable_day_count=sum(
            day.status != "not_evaluable" for day in classified
        ),
        observation_window_count=sum(
            len(day.construction.windows) for day in classified
        ),
        scalar_evaluation_count=sum(
            scan.evaluation_count for scan in scans
        ),
        sign_changing_root_count=sum(
            root.kind == "crossing" for root in roots
        ),
        tangent_root_count=sum(
            root.kind == "tangent" for root in roots
        ),
        near_zero_interval_count=len(near_zero),
        non_evaluable_gap_count=len(gaps),
        maximum_sample_gap_days=(
            max(sample_gaps) if sample_gaps else None
        ),
        classified_day_states=tuple(
            (
                day.observation_day_key,
                day.status,
                day.reason,
                day.construction.geometry_state,
            )
            for day in classified
        ),
        non_evaluable_day_states=tuple(
            (
                day.observation_day_key,
                day.reason or "solver_domain_disconnected",
                day.construction.geometry_state,
            )
            for day in classified
            if day.status == "not_evaluable"
        ),
        crossing_completeness_state=completeness_state,
        crossing_completeness_reason=completeness_reason,
        crossing_certificate_ids=certificate_ids,
        crossing_certificate_source_sha256=(
            (
                _PHYSICAL_DIRECTIONAL_HORIZON_CERTIFICATE_SHA256
                if policy.directional_horizon is not None
                else _PHYSICAL_EVENT_CROSSING_CERTIFICATE_SHA256
            )
            if certificate_ids
            else None
        ),
        root_enclosure_count=sum(
            len(scan.root_enclosures) for scan in scans
        ),
        unresolved_certificate_interval_count=len(
            unresolved_certificate_intervals
        ),
    )


def _physical_event_sensitivity_receipt(
    *,
    data_pack_numerical_event_interval_jd_ut: (
        tuple[float, float] | None
    ),
    data_pack_numerical_reason: str | None,
) -> PhysicalEventSensitivityReceipt:
    return PhysicalEventSensitivityReceipt(
        data_pack_numerical_event_interval_jd_ut=(
            data_pack_numerical_event_interval_jd_ut
        ),
        data_pack_numerical_reason=data_pack_numerical_reason,
        atmospheric_scenario_event_interval_jd_ut=None,
        atmospheric_scenario_reason=(
            "explicit_admitted_atmospheric_scenario_bounds_required"
        ),
        probabilistic_confidence_claimed=False,
    )


def _physical_event_evidence_state(
    status: PhysicalVisibilityStatus,
    reason: str | None,
) -> PhysicalVisibilityEvidenceState:
    if status is PhysicalVisibilityStatus.EVALUATED:
        return PhysicalVisibilityEvidenceState.EVALUATED_CLEAR_SKY
    if status is PhysicalVisibilityStatus.NOT_FOUND:
        return PhysicalVisibilityEvidenceState.EVALUATED_NO_EVENT
    if reason in {
        "target_not_admitted",
        "body_phase_not_admitted",
        "target_rise_missing",
        "target_set_missing",
        "solar_rise_missing",
        "solar_set_missing",
        "no_valid_observation_window",
    }:
        return PhysicalVisibilityEvidenceState.NOT_APPLICABLE
    if reason in {
        "solar_twilight_below_data_pack_domain",
        "solar_altitude_out_of_domain",
        "target_altitude_out_of_domain",
        "atmosphere_input_out_of_domain",
        "target_spectral_profile_out_of_domain",
        "criterion_out_of_domain",
    }:
        return PhysicalVisibilityEvidenceState.OUT_OF_DOMAIN
    return PhysicalVisibilityEvidenceState.MISSING_DEPENDENCY


def _physical_event_result(
    *,
    body: str,
    phase: PhysicalVisibilityPhase,
    lat: float,
    lon: float,
    status: PhysicalVisibilityStatus,
    reason: str | None,
    policy: PhysicalVisibilityPolicy,
    search_policy: PhysicalVisibilitySearchPolicy,
    candidate_day_keys: tuple[int, ...],
    selection: _PhaseTransitionSelection | None,
    data_pack_receipt: VisibilityDataPackReceipt | None,
    assessment_cache: dict[float, PhysicalVisibilityAssessment],
    solar_true_altitude: Callable[[float], _ScalarEvaluation] | None,
    ephemeris_attempted: bool,
    data_pack_numerical_event_interval_jd_ut: (
        tuple[float, float] | None
    ),
    data_pack_numerical_reason: str | None,
    data_pack_domain: VisibilityDataPackDomain | None = None,
) -> PhysicalVisibilityEventResult:
    selected_day = (
        selection.selected_day
        if (
            selection is not None
            and selection.status == "evaluated"
        )
        else None
    )
    comparison_day = (
        selection.comparison_day if selection is not None else None
    )
    selected_window = (
        selected_day.selected_window
        if selected_day is not None
        else None
    )
    horizon_receipt = _physical_event_horizon_receipt(
        policy,
        data_pack_domain,
    )
    event_assessment: PhysicalVisibilityAssessment | None = None
    event_jd_ut: float | None = None
    assessment_jd_ut: float | None = None
    if selected_window is not None:
        event_jd_ut = selected_window.event_jd_ut
        assessment_jd_ut = selected_window.assessment_jd_ut
        if assessment_jd_ut is not None:
            event_assessment = assessment_cache.get(
                assessment_jd_ut
            )
            if (
                event_assessment is not None
                and event_assessment.horizon_receipt is not None
            ):
                horizon_receipt = event_assessment.horizon_receipt

    derived_arcus_deg: float | None = None
    if event_jd_ut is not None and solar_true_altitude is not None:
        solar_sample = solar_true_altitude(event_jd_ut)
        if solar_sample.evaluable:
            assert solar_sample.value is not None
            derived_arcus_deg = -solar_sample.value

    boundary_source: PhysicalVisibilityBoundarySource | None = None
    event_semantics: PhysicalEventTimeSemantics | None = None
    crossing_direction: (
        PhysicalVisibilityCrossingDirection | None
    ) = None
    if selected_window is not None:
        if selected_window.boundary_source == "target_horizon":
            if horizon_receipt.target_boundary_narrowing_applied:
                boundary_source = (
                    PhysicalVisibilityBoundarySource
                    .TARGET_DATA_PACK_ALTITUDE_FLOOR
                )
                event_semantics = (
                    PhysicalEventTimeSemantics
                    .DATA_PACK_TARGET_ALTITUDE_FLOOR
                )
            else:
                boundary_source = (
                    PhysicalVisibilityBoundarySource.TARGET_HORIZON
                )
                event_semantics = (
                    PhysicalEventTimeSemantics.APPARENT_TARGET_HORIZON
                )
        elif selected_window.boundary_source == "visibility_margin":
            boundary_source = (
                PhysicalVisibilityBoundarySource.VISIBILITY_MARGIN
            )
            event_semantics = (
                PhysicalEventTimeSemantics.VISIBILITY_MARGIN_ZERO
            )
        crossing_direction = (
            PhysicalVisibilityCrossingDirection.NOT_VISIBLE_TO_VISIBLE
            if (
                selected_window.crossing_direction
                == "negative_to_positive"
            )
            else PhysicalVisibilityCrossingDirection.VISIBLE_TO_NOT_VISIBLE
        )

    window_receipt = None
    if selected_window is not None:
        window = selected_window.window
        window_receipt = PhysicalObservationWindowReceipt(
            observation_day_key=window.observation_day_key,
            start_jd_ut=window.start_jd_ut,
            end_jd_ut=window.end_jd_ut,
            target_boundary_jd_ut=window.target_boundary_jd_ut,
            target_boundary_role=window.target_boundary_role,
            solar_side=window.solar_side,
        )

    atmosphere_receipt = _physical_atmosphere_receipt(
        policy.atmosphere,
        within_data_pack_domain=(
            event_assessment.atmosphere_receipt.within_data_pack_domain
            if event_assessment is not None
            else None
        ),
    )
    observer_receipt = _physical_observer_receipt(policy)
    return PhysicalVisibilityEventResult(
        body=body,
        phase=phase,
        latitude_deg=lat,
        longitude_deg=lon,
        status=status,
        evidence_state=_physical_event_evidence_state(
            status,
            reason,
        ),
        reason=reason,
        observation_day_key=(
            selected_day.observation_day_key
            if selected_day is not None
            else None
        ),
        comparison_observation_day_key=(
            comparison_day.observation_day_key
            if comparison_day is not None
            else None
        ),
        comparison_day_status=(
            comparison_day.status
            if comparison_day is not None
            else None
        ),
        event_jd_ut=event_jd_ut,
        event_time_semantics=event_semantics,
        target_horizon_jd_ut=(
            selected_window.window.target_boundary_jd_ut
            if selected_window is not None
            else None
        ),
        peak_margin_jd_ut=(
            selected_window.peak_margin_jd_ut
            if selected_window is not None
            else None
        ),
        peak_margin_magnitude=(
            selected_window.peak_margin
            if selected_window is not None
            else None
        ),
        boundary_role=(
            selected_window.window.target_boundary_role
            if selected_window is not None
            else None
        ),
        crossing_direction=crossing_direction,
        boundary_source=boundary_source,
        visibility_margin_residual_magnitude=(
            selected_window.root_residual
            if selected_window is not None
            else None
        ),
        visibility_margin_bracket_jd_ut=(
            (
                selected_window.root_bracket_start_jd_ut,
                selected_window.root_bracket_end_jd_ut,
            )
            if (
                selected_window is not None
                and selected_window.root_bracket_start_jd_ut
                is not None
                and selected_window.root_bracket_end_jd_ut is not None
            )
            else None
        ),
        root_iterations=(
            selected_window.root_iterations
            if selected_window is not None
            else None
        ),
        derived_arcus_deg=derived_arcus_deg,
        assessment_jd_ut=assessment_jd_ut,
        observation_window=window_receipt,
        event_assessment=event_assessment,
        data_pack_receipt=data_pack_receipt,
        atmosphere_receipt=atmosphere_receipt,
        observer_protocol_receipt=observer_receipt,
        horizon_receipt=horizon_receipt,
        ephemeris_receipt=(
            _physical_event_ephemeris_receipt(body)
            if ephemeris_attempted
            else None
        ),
        solver_receipt=_physical_event_solver_receipt(
            search_policy,
            candidate_day_keys,
            selection,
            policy,
        ),
        sensitivity_receipt=_physical_event_sensitivity_receipt(
            data_pack_numerical_event_interval_jd_ut=(
                data_pack_numerical_event_interval_jd_ut
            ),
            data_pack_numerical_reason=(
                data_pack_numerical_reason
            ),
        ),
        components=(
            event_assessment.components
            if event_assessment is not None
            else ()
        ),
    )


def physical_visibility_event(
    body: str,
    phase: PhysicalVisibilityPhase,
    jd_start: float,
    lat: float,
    lon: float,
    *,
    data_pack_config: VisibilityDataPackConfig,
    policy: PhysicalVisibilityPolicy | None = None,
    search_policy: PhysicalVisibilitySearchPolicy | None = None,
) -> PhysicalVisibilityEventResult:
    """Search the opt-in four-phase physical point-source event contract.

    ``jd_start`` selects the first local-mean-solar observation-day key.  The
    complete selected day is classified, and one adjacent guard day is used
    only to prove Phase 0 first-day or last-day ownership.
    """

    if not isinstance(body, str) or not body:
        raise ValueError("body must be a nonempty string")
    if not isinstance(phase, PhysicalVisibilityPhase):
        try:
            phase = PhysicalVisibilityPhase(phase)
        except (TypeError, ValueError) as exc:
            raise ValueError("unsupported physical visibility phase") from exc
    _validate_physical_request_coordinate(jd_start, "jd_start")
    _validate_physical_request_coordinate(lat, "lat")
    _validate_physical_request_coordinate(lon, "lon")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon}")
    if not isinstance(data_pack_config, VisibilityDataPackConfig):
        raise TypeError(
            "data_pack_config must be a VisibilityDataPackConfig"
        )
    resolved_policy = (
        policy if policy is not None else PhysicalVisibilityPolicy()
    )
    if not isinstance(resolved_policy, PhysicalVisibilityPolicy):
        raise TypeError("policy must be a PhysicalVisibilityPolicy")
    resolved_search = (
        search_policy
        if search_policy is not None
        else PhysicalVisibilitySearchPolicy()
    )
    if not isinstance(
        resolved_search,
        PhysicalVisibilitySearchPolicy,
    ):
        raise TypeError(
            "search_policy must be a PhysicalVisibilitySearchPolicy"
        )
    scalar_policy = resolved_search._scalar_policy()
    start_day_key = math.floor(
        jd_start + 0.5 + lon / 360.0
    )
    candidate_day_keys = tuple(
        range(
            start_day_key,
            start_day_key + resolved_search.search_window_days,
        )
    )

    def early_failure(reason: str) -> PhysicalVisibilityEventResult:
        return _physical_event_result(
            body=body,
            phase=phase,
            lat=lat,
            lon=lon,
            status=PhysicalVisibilityStatus.NOT_EVALUABLE,
            reason=reason,
            policy=resolved_policy,
            search_policy=resolved_search,
            candidate_day_keys=candidate_day_keys,
            selection=None,
            data_pack_receipt=None,
            assessment_cache={},
            solar_true_altitude=None,
            ephemeris_attempted=False,
            data_pack_numerical_event_interval_jd_ut=None,
            data_pack_numerical_reason="event_not_evaluated",
        )

    if body not in _PHYSICAL_VISIBILITY_TARGETS:
        return early_failure("target_not_admitted")
    if body not in _PHYSICAL_EVENT_TARGETS:
        return early_failure("body_phase_not_admitted")
    if resolved_policy.background is None:
        return early_failure("background_input_incomplete")
    if (
        data_pack_config.expected_pack_id
        != resolved_policy.expected_data_pack_id
        or data_pack_config.expected_composite_model_id
        != resolved_policy.composite_model_id
        or (
            data_pack_config.expected_manifest_sha256 is not None
            and resolved_policy.expected_manifest_sha256 is not None
            and data_pack_config.expected_manifest_sha256
            != resolved_policy.expected_manifest_sha256
        )
    ):
        return early_failure("visibility_data_pack_incompatible")

    try:
        pack = load_visibility_data_pack(data_pack_config)
    except VisibilityDataPackLoadError as exc:
        return early_failure(exc.reason)
    if (
        pack.receipt.version != _PHYSICAL_EVENT_PACK_VERSION
        or pack.receipt.manifest_sha256
        != _PHYSICAL_EVENT_PACK_MANIFEST_SHA256
    ):
        return _physical_event_result(
            body=body,
            phase=phase,
            lat=lat,
            lon=lon,
            status=PhysicalVisibilityStatus.NOT_EVALUABLE,
            reason="visibility_event_data_pack_not_admitted",
            policy=resolved_policy,
            search_policy=resolved_search,
            candidate_day_keys=candidate_day_keys,
            selection=None,
            data_pack_receipt=pack.receipt,
            assessment_cache={},
            solar_true_altitude=None,
            ephemeris_attempted=False,
            data_pack_numerical_event_interval_jd_ut=None,
            data_pack_numerical_reason="event_not_evaluated",
            data_pack_domain=pack.domain,
        )
    if (
        resolved_policy.expected_manifest_sha256 is not None
        and pack.receipt.manifest_sha256
        != resolved_policy.expected_manifest_sha256
    ):
        return _physical_event_result(
            body=body,
            phase=phase,
            lat=lat,
            lon=lon,
            status=PhysicalVisibilityStatus.NOT_EVALUABLE,
            reason="visibility_data_pack_checksum_mismatch",
            policy=resolved_policy,
            search_policy=resolved_search,
            candidate_day_keys=candidate_day_keys,
            selection=None,
            data_pack_receipt=pack.receipt,
            assessment_cache={},
            solar_true_altitude=None,
            ephemeris_attempted=False,
            data_pack_numerical_event_interval_jd_ut=None,
            data_pack_numerical_reason="event_not_evaluated",
        )
    if not _physical_atmosphere_matches(
        resolved_policy.atmosphere,
        pack.domain,
    ):
        return _physical_event_result(
            body=body,
            phase=phase,
            lat=lat,
            lon=lon,
            status=PhysicalVisibilityStatus.NOT_EVALUABLE,
            reason="atmosphere_input_out_of_domain",
            policy=resolved_policy,
            search_policy=resolved_search,
            candidate_day_keys=candidate_day_keys,
            selection=None,
            data_pack_receipt=pack.receipt,
            assessment_cache={},
            solar_true_altitude=None,
            ephemeris_attempted=False,
            data_pack_numerical_event_interval_jd_ut=None,
            data_pack_numerical_reason="event_not_evaluated",
            data_pack_domain=pack.domain,
        )

    from .spk_reader import MissingKernelError

    target_pack_floor_apparent = apply_refraction(
        pack.domain.target_true_altitude_deg[0],
        pressure_mbar=resolved_policy.refraction_pressure_hpa,
        temperature_c=resolved_policy.refraction_temperature_c,
        relative_humidity=(
            resolved_policy.refraction_relative_humidity
        ),
    )

    horizontal_cache: dict[
        tuple[str, float],
        tuple[float, float] | str,
    ] = {}

    def horizontal(
        target: str,
        jd_ut: float,
    ) -> tuple[float, float] | str:
        key = (target, jd_ut)
        cached = horizontal_cache.get(key)
        if cached is not None:
            return cached
        try:
            result: tuple[float, float] | str = _true_horizontal(
                target,
                jd_ut,
                lat,
                lon,
            )
        except MissingKernelError:
            result = "ephemeris_dependency_missing"
        horizontal_cache[key] = result
        return result

    def true_altitude(
        target: str,
        jd_ut: float,
    ) -> _ScalarEvaluation:
        result = horizontal(target, jd_ut)
        if isinstance(result, str):
            return _ScalarEvaluation(
                jd_ut=jd_ut,
                value=None,
                reason=result,
            )
        return _ScalarEvaluation(jd_ut=jd_ut, value=result[1])

    def apparent_horizon_signal(
        target: str,
        jd_ut: float,
        *,
        apply_target_pack_floor: bool,
    ) -> _ScalarEvaluation:
        result = horizontal(target, jd_ut)
        if isinstance(result, str):
            return _ScalarEvaluation(
                jd_ut=jd_ut,
                value=None,
                reason=result,
            )
        apparent_altitude = apply_refraction(
            result[1],
            pressure_mbar=(
                resolved_policy.refraction_pressure_hpa
            ),
            temperature_c=(
                resolved_policy.refraction_temperature_c
            ),
            relative_humidity=(
                resolved_policy.refraction_relative_humidity
            ),
        )
        boundary_altitude_deg = _physical_local_horizon_altitude(
            resolved_policy,
            result[0],
        )
        if apply_target_pack_floor:
            boundary_altitude_deg = max(
                boundary_altitude_deg,
                target_pack_floor_apparent,
            )
        if resolved_policy.directional_horizon is not None:
            signal = _physical_directional_horizon_signal(
                apparent_altitude,
                boundary_altitude_deg,
            )
        else:
            signal = apparent_altitude - boundary_altitude_deg
        return _ScalarEvaluation(
            jd_ut=jd_ut,
            value=signal,
        )

    assessment_cache: dict[
        float,
        PhysicalVisibilityAssessment,
    ] = {}

    def assessment_at(
        jd_ut: float,
    ) -> PhysicalVisibilityAssessment:
        assessment = assessment_cache.get(jd_ut)
        if assessment is None:
            assessment = _physical_visibility_assessment_impl(
                body,
                jd_ut,
                lat,
                lon,
                data_pack_config=data_pack_config,
                policy=resolved_policy,
                loaded_data_pack=pack,
            )
            assessment_cache[jd_ut] = assessment
        return assessment

    def margin(
        jd_ut: float,
        *,
        envelope: str | None = None,
    ) -> _ScalarEvaluation:
        assessment = assessment_at(jd_ut)
        if (
            assessment.status is not PhysicalVisibilityStatus.EVALUATED
            or assessment.visibility_margin_magnitude is None
        ):
            return _ScalarEvaluation(
                jd_ut=jd_ut,
                value=None,
                reason=(
                    assessment.reason
                    or "solver_domain_disconnected"
                ),
            )
        if envelope is not None:
            error_budget = assessment.error_budget_receipt
            if error_budget is None:
                return _ScalarEvaluation(
                    jd_ut=jd_ut,
                    value=None,
                    reason=(
                        "data_pack_numerical_error_envelope_missing"
                    ),
                )
            if envelope == "lower":
                value = (
                    error_budget
                    .visibility_margin_envelope_lower_magnitude
                )
            elif envelope == "upper":
                value = (
                    error_budget
                    .visibility_margin_envelope_upper_magnitude
                )
            else:
                raise ValueError("unsupported numerical envelope")
            return _ScalarEvaluation(jd_ut=jd_ut, value=value)
        return _ScalarEvaluation(
            jd_ut=jd_ut,
            value=assessment.visibility_margin_magnitude,
        )

    phase_rule = _physical_phase_rule(phase)
    construction_cache: dict[
        int,
        _ObservationWindowConstruction,
    ] = {}

    def construction_for(
        day_key: int,
    ) -> _ObservationWindowConstruction:
        construction = construction_cache.get(day_key)
        if construction is None:
            construction = _construct_observation_windows(
                day_key,
                lon,
                phase_rule,
                target_apparent_horizon_signal=(
                    lambda jd_ut: apparent_horizon_signal(
                        body,
                        jd_ut,
                        apply_target_pack_floor=True,
                    )
                ),
                target_true_altitude=(
                    lambda jd_ut: true_altitude(body, jd_ut)
                ),
                solar_apparent_horizon_signal=(
                    lambda jd_ut: apparent_horizon_signal(
                        Body.SUN,
                        jd_ut,
                        apply_target_pack_floor=False,
                    )
                ),
                solar_true_altitude=(
                    lambda jd_ut: true_altitude(Body.SUN, jd_ut)
                ),
                solar_true_altitude_domain_deg=(
                    pack.domain.solar_center_altitude_deg
                ),
                target_true_altitude_domain_deg=(
                    pack.domain.target_true_altitude_deg
                ),
                policy=scalar_policy,
                target_horizon_certificate=(
                    _physical_horizon_signal_certificate(
                        resolved_policy,
                        role="target",
                        additional_constant_altitude_deg=(
                            target_pack_floor_apparent
                        ),
                    )
                ),
                target_altitude_certificate=(
                    _PHYSICAL_EVENT_GEOMETRY_CERTIFICATE
                ),
                solar_horizon_certificate=(
                    _physical_horizon_signal_certificate(
                        resolved_policy,
                        role="Sun",
                    )
                ),
                solar_altitude_certificate=(
                    _PHYSICAL_EVENT_GEOMETRY_CERTIFICATE
                ),
            )
            construction_cache[day_key] = construction
        return construction

    def classify(
        day_key: int,
        *,
        envelope: str | None = None,
    ) -> _ObservationDaySolution:
        return _classify_observation_day(
            construction_for(day_key),
            phase_rule,
            (
                lambda jd_ut: margin(
                    jd_ut,
                    envelope=envelope,
                )
            ),
            policy=scalar_policy,
            margin_certificate=(
                _PHYSICAL_EVENT_MARGIN_CERTIFICATE
            ),
        )

    selection = _select_owned_phase_transition(
        candidate_day_keys,
        phase_rule,
        lambda day_key: classify(day_key),
    )
    data_pack_interval: tuple[float, float] | None = None
    data_pack_reason: str | None = "event_not_evaluated"
    if selection.status == "evaluated":
        lower_selection = _select_owned_phase_transition(
            candidate_day_keys,
            phase_rule,
            lambda day_key: classify(
                day_key,
                envelope="lower",
            ),
        )
        upper_selection = _select_owned_phase_transition(
            candidate_day_keys,
            phase_rule,
            lambda day_key: classify(
                day_key,
                envelope="upper",
            ),
        )

        def selected_event_jd_ut(
            candidate: _PhaseTransitionSelection,
        ) -> float | None:
            if (
                candidate.status != "evaluated"
                or candidate.selected_day is None
                or candidate.selected_day.selected_window is None
            ):
                return None
            return candidate.selected_day.selected_window.event_jd_ut

        nominal_jd = selected_event_jd_ut(selection)
        lower_jd = selected_event_jd_ut(lower_selection)
        upper_jd = selected_event_jd_ut(upper_selection)
        if (
            nominal_jd is not None
            and lower_jd is not None
            and upper_jd is not None
        ):
            data_pack_interval = (
                min(nominal_jd, lower_jd, upper_jd),
                max(nominal_jd, lower_jd, upper_jd),
            )
            data_pack_reason = None
        elif (
            lower_selection.reason
            == "data_pack_numerical_error_envelope_missing"
            or upper_selection.reason
            == "data_pack_numerical_error_envelope_missing"
        ):
            data_pack_reason = (
                "data_pack_numerical_error_envelope_missing"
            )
        else:
            data_pack_reason = (
                "data_pack_numerical_event_interval_not_bounded"
            )
    result_status = {
        "evaluated": PhysicalVisibilityStatus.EVALUATED,
        "not_evaluable": PhysicalVisibilityStatus.NOT_EVALUABLE,
        "not_found": PhysicalVisibilityStatus.NOT_FOUND,
    }[selection.status]
    return _physical_event_result(
        body=body,
        phase=phase,
        lat=lat,
        lon=lon,
        status=result_status,
        reason=selection.reason,
        policy=resolved_policy,
        search_policy=resolved_search,
        candidate_day_keys=candidate_day_keys,
        selection=selection,
        data_pack_receipt=pack.receipt,
        assessment_cache=assessment_cache,
        solar_true_altitude=(
            lambda jd_ut: true_altitude(Body.SUN, jd_ut)
        ),
        ephemeris_attempted=bool(horizontal_cache),
        data_pack_numerical_event_interval_jd_ut=(
            data_pack_interval
        ),
        data_pack_numerical_reason=data_pack_reason,
        data_pack_domain=pack.domain,
    )


def _resolve_physical_background(
    background: PhysicalBackgroundInput,
) -> _DirectionalLuminance:
    """Convert one validated public background vessel to the compositor."""

    if isinstance(background, PhysicalDirectionalBackground):
        return _DirectionalLuminance(
            photopic_luminance_cd_m2=(
                background.photopic_luminance_cd_m2
            ),
            scotopic_luminance_cd_m2=(
                background.scotopic_luminance_cd_m2
            ),
            scope=background.scope.value,
            component_ids=background.component_ids,
            source_id=background.source_id,
            source_receipt_sha256=(
                background.source_receipt_sha256
            ),
            method_id=background.method_id,
            component_inventory_complete=(
                background.component_inventory_complete
            ),
        )
    if isinstance(background, PhysicalSqmBackground):
        return sqm_directional_luminance(
            background.sqm_mag_arcsec2,
            scotopic_to_photopic_ratio=(
                background.scotopic_to_photopic_ratio
            ),
            scope=background.scope.value,
            component_ids=background.component_ids,
            measurement_source_id=background.measurement_source_id,
            measurement_receipt_sha256=(
                background.measurement_receipt_sha256
            ),
            device_bandpass_id=background.device_bandpass_id,
            pointing_receipt_id=background.pointing_receipt_id,
            temporal_applicability_id=(
                background.temporal_applicability_id
            ),
            spectral_ratio_source_id=(
                background.spectral_ratio_source_id
            ),
            component_inventory_complete=(
                background.component_inventory_complete
            ),
        )
    if isinstance(background, PhysicalBortleBackground):
        sqm = _BORTLE_SKY_SQM_TABLE[
            background.light_pollution_class
        ]
        return sqm_directional_luminance(
            sqm,
            scotopic_to_photopic_ratio=(
                background.scotopic_to_photopic_ratio
            ),
            scope=PhysicalBackgroundScope.DARK_SKY_ANCHOR.value,
            component_ids=("coarse_night_sky_background",),
            measurement_source_id=(
                f"Bortle:2001:class_"
                f"{background.light_pollution_class.value}"
            ),
            measurement_receipt_sha256=(
                background.source_receipt_sha256
            ),
            device_bandpass_id=(
                "bortle_visual_sky_brightness_mapping_v1"
            ),
            pointing_receipt_id="coarse_zenith_reference",
            temporal_applicability_id="coarse_reference_not_time_bound",
            spectral_ratio_source_id=(
                background.spectral_ratio_source_id
            ),
            component_inventory_complete=False,
        )
    raise TypeError("unsupported physical background input")


def _resolve_modeled_background_components(
    components: tuple[PhysicalModeledBackgroundComponent, ...],
) -> tuple[ModeledDirectionalBackgroundComponent, ...]:
    """Convert declared public model outputs to the internal compositor."""

    return tuple(
        ModeledDirectionalBackgroundComponent(
            component_id=component.component_kind.value,
            photopic_luminance_cd_m2=(
                component.photopic_luminance_cd_m2
            ),
            scotopic_luminance_cd_m2=(
                component.scotopic_luminance_cd_m2
            ),
            model_id=component.model_id,
            source_ids=component.source_ids,
            source_receipt_sha256=component.source_receipt_sha256,
            spatial_applicability_id=(
                component.spatial_applicability_id
            ),
            temporal_applicability_id=(
                component.temporal_applicability_id
            ),
            direction_receipt_id=component.direction_receipt_id,
            validity_domain_id=component.validity_domain_id,
            uncertainty_authority_id=(
                component.uncertainty_authority_id
            ),
        )
        for component in components
    )


def _physical_not_evaluable(
    body: str,
    jd_ut: float,
    lat: float,
    lon: float,
    policy: PhysicalVisibilityPolicy,
    evidence_state: PhysicalVisibilityEvidenceState,
    reason: str,
    *,
    atmosphere_receipt: PhysicalAtmosphereReceipt,
    observer_receipt: PhysicalObserverProtocolReceipt,
    data_pack_receipt: VisibilityDataPackReceipt | None = None,
    validity_domain_receipt: (
        PhysicalValidityDomainReceipt | None
    ) = None,
    true_target_altitude_deg: float | None = None,
    apparent_target_altitude_deg: float | None = None,
    true_solar_center_altitude_deg: float | None = None,
    relative_solar_azimuth_deg: float | None = None,
    geometrically_visible: bool | None = None,
    observable: bool | None = None,
    horizon_receipt: PhysicalHorizonReceipt | None = None,
) -> PhysicalVisibilityAssessment:
    """Build one typed fail-closed assessment without fabricated truth."""

    return PhysicalVisibilityAssessment(
        body=body,
        jd_ut=jd_ut,
        latitude_deg=lat,
        longitude_deg=lon,
        status=PhysicalVisibilityStatus.NOT_EVALUABLE,
        evidence_state=evidence_state,
        reason=reason,
        true_target_altitude_deg=true_target_altitude_deg,
        apparent_target_altitude_deg=apparent_target_altitude_deg,
        true_solar_center_altitude_deg=(
            true_solar_center_altitude_deg
        ),
        relative_solar_azimuth_deg=relative_solar_azimuth_deg,
        geometrically_visible=geometrically_visible,
        visible=None,
        observable=observable,
        visibility_margin_magnitude=None,
        data_pack_receipt=data_pack_receipt,
        atmosphere_receipt=atmosphere_receipt,
        validity_domain_receipt=validity_domain_receipt,
        observer_protocol_receipt=observer_receipt,
        background_receipt=None,
        target_receipt=None,
        threshold_receipt=None,
        error_budget_receipt=None,
        components=_physical_partial_components(
            policy,
            data_pack_receipt,
        ),
        horizon_receipt=(
            horizon_receipt
            if horizon_receipt is not None
            else _physical_event_horizon_receipt(policy)
        ),
    )


def _physical_partial_components(
    policy: PhysicalVisibilityPolicy,
    data_pack_receipt: VisibilityDataPackReceipt | None,
) -> tuple[VisibilityComponentReceipt, ...]:
    components = [
        VisibilityComponentReceipt(
            role="observer_protocol",
            component_id=policy.observer_protocol_id,
            source_ids=("CIE:TN007:2017:clause_6", "Blackwell:1946"),
            details=(
                ("task", "known_target_directed_averted_detection"),
                ("optical_aid", "none"),
                (
                    "detection_field_factor_model_id",
                    "crumey_2014_equation_53_fixed_notional_f2_v1",
                ),
                ("detection_field_factor_value", "2"),
                ("detection_field_factor_mutable", "false"),
                ("probabilistic_detection_claimed", "false"),
            ),
        ),
        VisibilityComponentReceipt(
            role="atmosphere_request",
            component_id=(
                f"{policy.atmosphere.atmosphere_profile}:"
                f"{policy.atmosphere.aerosol_profile}"
            ),
            source_ids=(),
        ),
        *_physical_modeled_background_component_receipts(policy),
        *_physical_horizon_component_receipts(policy),
    ]
    if data_pack_receipt is not None:
        components.append(
            VisibilityComponentReceipt(
                role="visibility_data_pack",
                component_id=(
                    f"{data_pack_receipt.pack_id}:"
                    f"{data_pack_receipt.version}"
                ),
                source_ids=data_pack_receipt.source_dataset_ids,
                details=(
                    (
                        "manifest_sha256",
                        data_pack_receipt.manifest_sha256,
                    ),
                ),
            )
        )
    return tuple(components)


def _physical_modeled_background_component_receipts(
    policy: PhysicalVisibilityPolicy,
) -> tuple[VisibilityComponentReceipt, ...]:
    return tuple(
        VisibilityComponentReceipt(
            role="modeled_background_component",
            component_id=component.model_id,
            source_ids=component.source_ids,
            details=(
                (
                    "background_component_id",
                    component.component_kind.value,
                ),
                (
                    "photopic_luminance_cd_m2",
                    format(
                        component.photopic_luminance_cd_m2,
                        ".17g",
                    ),
                ),
                (
                    "scotopic_luminance_cd_m2",
                    format(
                        component.scotopic_luminance_cd_m2,
                        ".17g",
                    ),
                ),
                (
                    "source_receipt_sha256",
                    component.source_receipt_sha256,
                ),
                (
                    "spatial_applicability_id",
                    component.spatial_applicability_id,
                ),
                (
                    "temporal_applicability_id",
                    component.temporal_applicability_id,
                ),
                (
                    "direction_receipt_id",
                    component.direction_receipt_id,
                ),
                (
                    "validity_domain_id",
                    component.validity_domain_id,
                ),
                (
                    "uncertainty_authority_id",
                    component.uncertainty_authority_id,
                ),
            ),
        )
        for component in sorted(
            policy.modeled_background_components,
            key=lambda value: value.component_kind.value,
        )
    )


def _physical_horizon_component_receipts(
    policy: PhysicalVisibilityPolicy,
) -> tuple[VisibilityComponentReceipt, ...]:
    profile = policy.directional_horizon
    if profile is None:
        return ()
    return (
        VisibilityComponentReceipt(
            role="local_horizon",
            component_id=profile.profile_id,
            source_ids=(profile.source_id,),
            details=(
                (
                    "interpolation_method_id",
                    profile.interpolation_method_id,
                ),
                ("source_receipt_sha256", profile.source_receipt_sha256),
                ("sample_count", str(len(profile.samples))),
                (
                    "admitted_maximum_gap_deg",
                    f"{profile.admitted_maximum_gap_deg:.17g}",
                ),
                (
                    "actual_maximum_gap_deg",
                    f"{profile.actual_maximum_gap_deg:.17g}",
                ),
                (
                    "maximum_absolute_slope_deg_per_deg",
                    (
                        f"{profile.maximum_absolute_slope_deg_per_deg:.17g}"
                    ),
                ),
                (
                    "cone_signal_lipschitz_factor",
                    f"{profile.cone_signal_lipschitz_factor:.17g}",
                ),
            ),
        ),
    )


def _physical_atmosphere_matches(
    atmosphere: PhysicalAtmosphereInput,
    domain: VisibilityDataPackDomain,
) -> bool:
    return (
        atmosphere.atmosphere_profile == domain.atmosphere_profile
        and atmosphere.aerosol_profile == domain.aerosol_profile
        and atmosphere.observer_altitude_m == domain.observer_altitude_m
        and atmosphere.surface_pressure_hpa == domain.surface_pressure_hpa
        and atmosphere.aod550 == domain.aod550
        and atmosphere.angstrom_exponent == domain.angstrom_exponent
        and atmosphere.ozone_du == domain.ozone_du
        and atmosphere.ground_albedo == domain.ground_albedo
    )


def _physical_atmosphere_receipt(
    atmosphere: PhysicalAtmosphereInput,
    *,
    within_data_pack_domain: bool | None,
) -> PhysicalAtmosphereReceipt:
    return PhysicalAtmosphereReceipt(
        complete=True,
        within_data_pack_domain=within_data_pack_domain,
        atmosphere_profile=atmosphere.atmosphere_profile,
        aerosol_profile=atmosphere.aerosol_profile,
        observer_altitude_m=atmosphere.observer_altitude_m,
        surface_pressure_hpa=atmosphere.surface_pressure_hpa,
        aod550=atmosphere.aod550,
        angstrom_exponent=atmosphere.angstrom_exponent,
        ozone_du=atmosphere.ozone_du,
        ground_albedo=atmosphere.ground_albedo,
    )


def _physical_observer_receipt(
    policy: PhysicalVisibilityPolicy,
) -> PhysicalObserverProtocolReceipt:
    profile = policy.directional_horizon
    return PhysicalObserverProtocolReceipt(
        protocol_id=policy.observer_protocol_id,
        task="known_target_directed_averted_detection",
        optical_aid="none",
        adaptation_field="immediate_directional_peripheral_field",
        local_horizon_altitude_deg=(
            policy.local_horizon_altitude_deg
        ),
        refraction_model_id=policy.refraction_model_id,
        refraction_pressure_hpa=policy.refraction_pressure_hpa,
        refraction_temperature_c=policy.refraction_temperature_c,
        refraction_relative_humidity=(
            policy.refraction_relative_humidity
        ),
        horizon_model_id=(
            "directional_circular_linear_apparent_horizon_v1"
            if profile is not None
            else "scalar_apparent_horizon_v1"
        ),
        directional_profile_applied=profile is not None,
        directional_profile_id=(
            profile.profile_id if profile is not None else None
        ),
        directional_profile_source_id=(
            profile.source_id if profile is not None else None
        ),
        directional_profile_source_receipt_sha256=(
            profile.source_receipt_sha256
            if profile is not None
            else None
        ),
        detection_field_factor_model_id=(
            "crumey_2014_equation_53_fixed_notional_f2_v1"
        ),
        detection_field_factor_value=2.0,
        detection_field_factor_mutable=False,
        detection_field_factor_source_ids=(
            "Crumey:2014:equation_53",
            "Crumey:2014:notional_field_factor_F_2",
        ),
        probabilistic_detection_claimed=False,
    )


def _physical_domain_receipt(
    domain: VisibilityDataPackDomain,
    *,
    solar_center_altitude_deg: float | None = None,
    target_true_altitude_deg: float | None = None,
    relative_solar_azimuth_deg: float | None = None,
) -> PhysicalValidityDomainReceipt:
    queries = (
        solar_center_altitude_deg,
        target_true_altitude_deg,
        relative_solar_azimuth_deg,
    )
    within_domain: bool | None
    if all(value is None for value in queries):
        within_domain = None
    else:
        within_domain = True
        if solar_center_altitude_deg is not None:
            within_domain = within_domain and _within_closed_interval(
                solar_center_altitude_deg,
                domain.solar_center_altitude_deg,
            )
        if target_true_altitude_deg is not None:
            within_domain = within_domain and _within_closed_interval(
                target_true_altitude_deg,
                domain.target_true_altitude_deg,
            )
        if relative_solar_azimuth_deg is not None:
            within_domain = within_domain and _within_closed_interval(
                relative_solar_azimuth_deg,
                domain.relative_solar_azimuth_deg,
            )
    return PhysicalValidityDomainReceipt(
        no_extrapolation=domain.no_extrapolation,
        solar_center_altitude_domain_deg=(
            domain.solar_center_altitude_deg
        ),
        target_true_altitude_domain_deg=(
            domain.target_true_altitude_deg
        ),
        relative_solar_azimuth_domain_deg=(
            domain.relative_solar_azimuth_deg
        ),
        queried_solar_center_altitude_deg=(
            solar_center_altitude_deg
        ),
        queried_target_true_altitude_deg=target_true_altitude_deg,
        queried_relative_solar_azimuth_deg=(
            relative_solar_azimuth_deg
        ),
        within_domain=within_domain,
    )


def _within_closed_interval(
    value: float,
    interval: tuple[float, float],
) -> bool:
    return interval[0] <= value <= interval[1]


def _physical_background_receipt(
    truth: SpectralSingleEpochTruth,
) -> PhysicalBackgroundReceipt:
    background = truth.background
    adaptation = truth.adaptation
    return PhysicalBackgroundReceipt(
        authority_id=background.authority_id,
        component_ids=background.component_ids,
        source_ids=background.source_ids,
        photopic_luminance_cd_m2=(
            background.photopic_luminance_cd_m2
        ),
        scotopic_luminance_cd_m2=(
            background.scotopic_luminance_cd_m2
        ),
        mesopic_luminance_cd_m2=adaptation.mesopic_luminance_cd_m2,
        scotopic_to_photopic_ratio=(
            adaptation.scotopic_to_photopic_ratio
        ),
        adaptation_coefficient=adaptation.adaptation_coefficient,
        weighting_state=adaptation.weighting_state,
        adaptation_solver_method=adaptation.solver_method,
        photopic_solver_relative_standard_error_bound=(
            background.photopic_solver_relative_standard_error_bound
        ),
        scotopic_solver_relative_standard_error_bound=(
            background.scotopic_solver_relative_standard_error_bound
        ),
        solver_uncertainty_bound_method=(
            background.solver_uncertainty_bound_method
        ),
        photopic_interpolation_maximum_error_mag=(
            background.photopic_interpolation_maximum_error_mag
        ),
        photopic_interpolation_p95_error_mag=(
            background.photopic_interpolation_p95_error_mag
        ),
        scotopic_interpolation_maximum_error_mag=(
            background.scotopic_interpolation_maximum_error_mag
        ),
        scotopic_interpolation_p95_error_mag=(
            background.scotopic_interpolation_p95_error_mag
        ),
        storage_maximum_error_mag=(
            background.storage_maximum_error_mag
        ),
        component_inventory_complete=(
            background.component_inventory_complete
        ),
        modeled_component_count=len(background.modeled_components),
    )


def _physical_target_receipt(
    target: ConditionedTarget,
    profile: _TargetSpectralProfile,
) -> PhysicalTargetReceipt:
    return PhysicalTargetReceipt(
        target_id=target.target_id,
        photometry_model_id=profile.photometry_model_id,
        photometry_source_ids=profile.photometry_source_ids,
        spectral_profile_id=profile.spectral_profile_id,
        spectral_source_ids=profile.spectral_source_ids,
        spectral_source_receipt_sha256=(
            profile.spectral_source_receipt_sha256
        ),
        spectral_model_details=profile.spectral_model_details,
        top_of_atmosphere_visual_magnitude=(
            target.top_of_atmosphere_visual_magnitude
        ),
        scotopic_to_photopic_ratio=(
            profile.scotopic_to_photopic_ratio
        ),
        photopic_transmission=target.photopic_transmission,
        scotopic_transmission=target.scotopic_transmission,
        conditioned_target_magnitude=(
            target.conditioned_target_magnitude
        ),
        direct_interpolation_maximum_error_mag=(
            target.direct_interpolation_maximum_error_mag
        ),
        direct_interpolation_p95_error_mag=(
            target.direct_interpolation_p95_error_mag
        ),
        storage_maximum_error_mag=target.storage_maximum_error_mag,
    )


def _physical_threshold_receipt(
    threshold: _FullRangePointSourceThreshold,
) -> PhysicalThresholdReceipt:
    return PhysicalThresholdReceipt(
        model_id=threshold.model_id,
        background_luminance_cd_m2=(
            threshold.background_luminance_cd_m2
        ),
        field_factor=threshold.field_factor,
        threshold_illuminance_lux=threshold.threshold_illuminance_lux,
        limiting_magnitude=threshold.limiting_magnitude,
        valid_background_min_cd_m2=(
            threshold.valid_background_min_cd_m2
        ),
        valid_background_max_cd_m2=(
            threshold.valid_background_max_cd_m2
        ),
        equation_receipt=threshold.equation_receipt,
    )


def _physical_error_budget_receipt(
    budget: _VisibilityMarginErrorBudget,
) -> PhysicalVisibilityErrorBudgetReceipt:
    return PhysicalVisibilityErrorBudgetReceipt(
        method_id=budget.method_id,
        background_error_authority=budget.background_error_authority,
        solver_relative_standard_error_multiplier=(
            budget.solver_relative_standard_error_multiplier
        ),
        background_mesopic_luminance_envelope_lower_cd_m2=(
            budget.background_mesopic_luminance_envelope_lower_cd_m2
        ),
        background_mesopic_luminance_envelope_upper_cd_m2=(
            budget.background_mesopic_luminance_envelope_upper_cd_m2
        ),
        limiting_magnitude_envelope_lower=(
            budget.limiting_magnitude_envelope_lower
        ),
        limiting_magnitude_envelope_upper=(
            budget.limiting_magnitude_envelope_upper
        ),
        conditioned_target_magnitude_maximum_pack_error=(
            budget.conditioned_target_magnitude_maximum_pack_error
        ),
        visibility_margin_envelope_lower_magnitude=(
            budget.visibility_margin_envelope_lower_magnitude
        ),
        visibility_margin_envelope_upper_magnitude=(
            budget.visibility_margin_envelope_upper_magnitude
        ),
        visibility_margin_envelope_maximum_deviation_magnitude=(
            budget.visibility_margin_envelope_maximum_deviation_magnitude
        ),
        visibility_classification_within_data_pack_envelope=(
            budget.visibility_classification_within_data_pack_envelope
        ),
        included_error_sources=budget.included_error_sources,
        unquantified_error_sources=budget.unquantified_error_sources,
    )


def _physical_component_receipts(
    components: tuple[SpectralComponentReceipt, ...],
) -> tuple[VisibilityComponentReceipt, ...]:
    return tuple(
        VisibilityComponentReceipt(
            role=component.role,
            component_id=component.component_id,
            source_ids=component.source_ids,
            details=component.details,
        )
        for component in components
    )


def _validate_physical_request_coordinate(
    value: float,
    name: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be finite")


def _validate_physical_sha256(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(
            f"{name} must be a lowercase 64-character SHA-256"
        )


def visibility_assessment(
    body: str,
    jd_ut: float,
    lat: float,
    lon: float,
    *,
    policy: VisibilityPolicy | None = None,
) -> VisibilityAssessment:
    """
    Assess direct observability of a body at a single instant.

    This is the standalone public surface for the legacy limiting-magnitude
    criterion, the opt-in CRUMEY_2014_POINT_SOURCE physical path for unresolved
    planets and stars, and YALLOP_LUNAR_CRESCENT for the Moon.

    Parameters
    ----------
    body:
        Body name constant (``Body.*``) or a fixed-star name string.
    jd_ut:
        Julian Day in UT1.
    lat:
        Observer geodetic latitude in degrees (−90 to +90).
    lon:
        Observer longitude in degrees (−180 to +180).
    policy:
        :class:`VisibilityPolicy` governing criterion family, observer
        environment, and moonlight model.  Defaults to
        ``VisibilityPolicy()`` (LIMITING_MAGNITUDE_THRESHOLD, Bortle 3,
        no moonlight penalty).

    Returns
    -------
    :class:`VisibilityAssessment`
        The complete single-instant observability assessment with all
        intermediate values.

    Raises
    ------
    ValueError
        If ``jd_ut`` is not finite, ``lat`` or ``lon`` are out of range,
        or YALLOP_LUNAR_CRESCENT is requested for a body other than the Moon.

    Side effects: None.
    """
    if not math.isfinite(jd_ut):
        raise ValueError(f"jd_ut must be finite, got {jd_ut}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon}")

    resolved_policy = policy if policy is not None else VisibilityPolicy()
    environment = resolved_policy.environment
    assert environment is not None

    if (
        resolved_policy.criterion_family is VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT
        and body != Body.MOON
    ):
        raise ValueError("YALLOP_LUNAR_CRESCENT is currently defined only for the Moon")

    true_altitude_deg = _true_altitude(body, jd_ut, lat, lon)
    if resolved_policy.use_refraction:
        apparent_altitude_deg = _planet_alt(
            body,
            jd_ut,
            lat,
            lon,
            pressure_mbar=environment.pressure_mbar,
            temperature_c=environment.temperature_c,
            relative_humidity=environment.relative_humidity,
        )
    else:
        apparent_altitude_deg = true_altitude_deg

    apparent_mag = _target_apparent_magnitude(body, jd_ut)
    is_geometrically_visible = apparent_altitude_deg >= environment.local_horizon_altitude_deg
    solar_elongation_deg = _target_signed_elongation(body, jd_ut)

    effective_limiting_magnitude: float | None = _effective_limiting_magnitude(
        resolved_policy
    )
    moonlight_sky_nl: float | None = None
    lunar_crescent_details = None
    extinction_adjusted_magnitude: float | None = None
    visibility_margin_magnitude: float | None = None
    criterion_target_magnitude: float | None = None
    target_extinction_applied_separately = False
    criterion_applicable = True
    criterion_reason: str | None = None
    extinction_details: AtmosphericExtinctionAssessment | None = None
    twilight_details: TwilightSkyBrightnessAssessment | None = None
    point_threshold: PointSourceVisibilityThreshold | None = None
    dark_sky_nl: float | None = None
    total_sky_nl: float | None = None

    if (
        body == Body.MOON
        and resolved_policy.criterion_family is VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT
    ):
        lunar_crescent_details = _lunar_crescent_details_at(jd_ut, lat, lon)
        is_bright_enough = _yallop_class_observable(
            lunar_crescent_details.visibility_class,
            environment.observing_aid,
        )
    elif (
        resolved_policy.criterion_family
        is VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE
    ):
        if body in {Body.SUN, Body.MOON}:
            raise ValueError(
                "CRUMEY_2014_POINT_SOURCE is admitted for unresolved point "
                "sources, not the Sun or Moon"
            )
        effective_limiting_magnitude = None
        is_bright_enough = False
        if apparent_altitude_deg < 0.0:
            criterion_applicable = False
            criterion_reason = "target_below_atmospheric_horizon"
        else:
            atmospheric_altitude = min(90.0, apparent_altitude_deg)
            from .rise_set import _body_ra_dec

            sun_right_ascension_deg, _ = _body_ra_dec(jd_ut, Body.SUN)
            extinction_details = atmospheric_extinction(
                atmospheric_altitude,
                model=resolved_policy.extinction_model,
                extinction_coefficient_k=resolved_policy.extinction_coefficient_k,
                observer_altitude_m=environment.observer_altitude_m,
                relative_humidity=environment.relative_humidity,
                observer_latitude_deg=lat,
                sun_right_ascension_deg=sun_right_ascension_deg,
            )
            extinction_adjusted_magnitude = (
                apparent_mag + extinction_details.extinction_magnitude
            )
            extinction_k = (
                extinction_details.sky_brightness_extinction_coefficient
            )

            target_azimuth_deg, target_true_altitude_deg = _true_horizontal(
                body,
                jd_ut,
                lat,
                lon,
            )
            sun_azimuth_deg, sun_true_altitude_deg = _true_horizontal(
                Body.SUN,
                jd_ut,
                lat,
                lon,
            )
            sun_target_separation_deg = _horizontal_separation_deg(
                target_azimuth_deg,
                target_true_altitude_deg,
                sun_azimuth_deg,
                sun_true_altitude_deg,
            )
            twilight_details = directional_twilight_sky_brightness(
                atmospheric_altitude,
                sun_true_altitude_deg,
                sun_target_separation_deg,
                extinction_coefficient_k=extinction_k,
            )
            if not twilight_details.valid:
                criterion_applicable = False
                criterion_reason = twilight_details.reason
            else:
                zenith_sky_nl = _ks1991_dark_sky_nanolamberts(
                    resolved_policy
                )
                dark_sky_nl = _directional_dark_sky_nanolamberts(
                    zenith_sky_nl,
                    atmospheric_altitude,
                    extinction_k,
                )
                if (
                    resolved_policy.moonlight_policy
                    is MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991
                ):
                    moonlight_sky_nl = _ks1991_moonlight_for_target(
                        resolved_policy,
                        jd_ut,
                        lat,
                        lon,
                        body,
                        extinction_k=extinction_k,
                    )
                twilight_nl = twilight_details.sky_nanolamberts
                assert twilight_nl is not None
                total_sky_nl = (
                    dark_sky_nl
                    + twilight_nl
                    + (moonlight_sky_nl or 0.0)
                )
                point_threshold = point_source_visibility_threshold(
                    total_sky_nl,
                    field_factor=resolved_policy.crumey_field_factor,
                )
                criterion_applicable = point_threshold.valid
                criterion_reason = point_threshold.reason
                effective_limiting_magnitude = (
                    point_threshold.limiting_magnitude
                )
                if point_threshold.valid:
                    assert effective_limiting_magnitude is not None
                    assert extinction_adjusted_magnitude is not None
                    target_extinction_applied_separately = (
                        not resolved_policy.crumey_field_factor_includes_atmosphere
                    )
                    criterion_target_magnitude = (
                        extinction_adjusted_magnitude
                        if target_extinction_applied_separately
                        else apparent_mag
                    )
                    visibility_margin_magnitude = (
                        effective_limiting_magnitude
                        - criterion_target_magnitude
                    )
                    is_bright_enough = visibility_margin_magnitude >= 0.0
    else:
        if (
            resolved_policy.moonlight_policy
            is MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991
        ):
            computed_moonlight_sky_nl = _ks1991_moonlight_for_target(
                resolved_policy,
                jd_ut,
                lat,
                lon,
                body,
            )
            moonlight_sky_nl = (
                computed_moonlight_sky_nl
                if computed_moonlight_sky_nl > 0.0
                else None
            )
            delta = _ks1991_limiting_magnitude_penalty(
                resolved_policy,
                jd_ut,
                lat,
                lon,
                body,
            )
            if delta < 0.0:
                assert effective_limiting_magnitude is not None
                effective_limiting_magnitude += delta
        assert effective_limiting_magnitude is not None
        criterion_target_magnitude = apparent_mag
        is_bright_enough = apparent_mag <= effective_limiting_magnitude

    return VisibilityAssessment(
        body=body,
        jd_ut=jd_ut,
        criterion_family=resolved_policy.criterion_family,
        effective_limiting_magnitude=effective_limiting_magnitude,
        apparent_magnitude=apparent_mag,
        true_altitude_deg=true_altitude_deg,
        apparent_altitude_deg=apparent_altitude_deg,
        local_horizon_altitude_deg=environment.local_horizon_altitude_deg,
        solar_elongation_deg=solar_elongation_deg,
        is_geometrically_visible=is_geometrically_visible,
        is_bright_enough=is_bright_enough,
        observable=(
            criterion_applicable
            and is_geometrically_visible
            and is_bright_enough
        ),
        lunar_crescent_details=lunar_crescent_details,
        moonlight_sky_nanolamberts=moonlight_sky_nl,
        extinction_adjusted_magnitude=extinction_adjusted_magnitude,
        visibility_margin_magnitude=visibility_margin_magnitude,
        criterion_target_magnitude=criterion_target_magnitude,
        target_extinction_applied_separately=(
            target_extinction_applied_separately
        ),
        criterion_applicable=criterion_applicable,
        criterion_reason=criterion_reason,
        atmospheric_extinction=extinction_details,
        twilight_sky_brightness=twilight_details,
        point_source_threshold=point_threshold,
        dark_sky_nanolamberts=dark_sky_nl,
        total_sky_nanolamberts=total_sky_nl,
    )


def visual_limiting_magnitude(
    jd_ut: float,
    lat: float,
    lon: float,
    *,
    policy: VisibilityPolicy | None = None,
) -> float:
    """
    Return the effective visual limiting magnitude at a given instant.

    This is the same scalar that ``visibility_assessment`` places in
    ``VisibilityAssessment.effective_limiting_magnitude``.  It combines:

    1. the Bortle-class sky limit from the observer's
       ``LightPollutionClass`` (or an explicit ``limiting_magnitude``
       override if supplied on the policy);
    2. a K&S 1991 moonlight penalty when
       ``policy.moonlight_policy == MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991``
       and the Moon is above the horizon.

    The result is the faintest V-magnitude object that Moira considers
    detectable under the given conditions.

    Parameters
    ----------
    jd_ut:
        Julian Day in UT1.
    lat:
        Observer geodetic latitude in degrees (-90 to +90).
    lon:
        Observer longitude in degrees (-180 to +180).
    policy:
        ``VisibilityPolicy`` that governs sky brightness, Bortle class,
        and moonlight model.  Defaults to ``VisibilityPolicy()``.

    Returns
    -------
    float
        Effective limiting V-magnitude.
    """
    if not math.isfinite(jd_ut):
        raise ValueError(f"jd_ut must be finite, got {jd_ut}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"lon must be in [-180, 180], got {lon}")

    resolved_policy = policy if policy is not None else VisibilityPolicy()
    if (
        resolved_policy.criterion_family
        is VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE
    ):
        raise ValueError(
            "CRUMEY_2014_POINT_SOURCE is directional; use "
            "visibility_assessment(body, ...) to obtain its limiting magnitude"
        )
    magnitude = _effective_limiting_magnitude(resolved_policy)
    if resolved_policy.moonlight_policy is MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991:
        delta = _ks1991_zenith_limiting_magnitude_penalty(
            resolved_policy,
            jd_ut,
            lat,
            lon,
        )
        if delta < 0.0:
            magnitude += delta
    return magnitude


def visibility_tonight(
    body: str,
    jd_ut: float,
    lat: float,
    lon: float,
    *,
    policy: VisibilityPolicy | None = None,
) -> VisibilityAssessment:
    """
    Convenience alias for a practitioner-facing single-night visibility check.

    This wrapper introduces no new visibility doctrine. It delegates directly
    to ``visibility_assessment()`` at the supplied Julian Day.
    """

    return visibility_assessment(body, jd_ut, lat, lon, policy=policy)


def is_visible_tonight(
    body: str,
    jd_ut: float,
    lat: float,
    lon: float,
    *,
    policy: VisibilityPolicy | None = None,
) -> bool:
    """
    Return only the boolean verdict from ``visibility_tonight()``.

    This is the minimal discoverability alias for callers who want a simple
    yes/no answer without inspecting the full assessment vessel.
    """

    return visibility_tonight(body, jd_ut, lat, lon, policy=policy).observable


def visibility_event(
    body: str,
    event_kind: HeliacalEventKind,
    jd_start: float,
    lat: float,
    lon: float,
    *,
    heliacal_policy: HeliacalPolicy | None = None,
    visibility_policy: VisibilityPolicy | None = None,
    search_policy: VisibilitySearchPolicy | None = None,
) -> GeneralVisibilityEvent | None:
    """
    Generalized visibility-event search surface for all admitted target families.

    Searches forward from ``jd_start`` for the next occurrence of the requested
    ``event_kind`` for the given body, using the declared visibility and search
    policies.  Returns ``None`` if no event is found within the search window.

    Admitted target families:
        - Planets (all non-Sun, non-Earth, non-Moon Body constants)
        - Fixed stars (named star strings routed to moira.stars)
        - Moon (with YALLOP_LUNAR_CRESCENT criterion for crescent events)

    Admitted event kinds:
        - HELIACAL_RISING, HELIACAL_SETTING
        - ACRONYCHAL_RISING, ACRONYCHAL_SETTING
        - COSMIC_RISING, COSMIC_SETTING (planets only)

    Parameters
    ----------
    body:
        Body name constant or fixed-star name string.
    event_kind:
        :class:`HeliacalEventKind` specifying which visibility crossing to find.
    jd_start:
        Julian Day (UT1) to begin the forward search.
    lat:
        Observer geodetic latitude in degrees (−90 to +90).
    lon:
        Observer longitude in degrees (−180 to +180).
    heliacal_policy:
        :class:`HeliacalPolicy` governing observer model.  Defaults to
        ``HeliacalPolicy.default()``.
    visibility_policy:
        :class:`VisibilityPolicy` governing criterion family and observer
        environment.  When supplied, overrides the policy embedded in
        ``heliacal_policy``.
    search_policy:
        :class:`VisibilitySearchPolicy` governing search extent and step.
        Defaults to ``VisibilitySearchPolicy()``.

    Returns
    -------
    :class:`GeneralVisibilityEvent` or ``None`` if no event is found.

    Raises
    ------
    ValueError
        For invalid ``body`` (SUN, EARTH), invalid argument ranges, or
        invalid search_window_days.
    NotImplementedError
        For YALLOP_LUNAR_CRESCENT with non-crescent event kinds, or
        unsupported event kinds.

    Side effects: None.
    """
    if body in {Body.SUN, Body.EARTH}:
        raise ValueError(f"visibility_event does not support body {body!r}")
    target_kind = _target_kind(body)
    resolved_heliacal_policy = heliacal_policy if heliacal_policy is not None else HeliacalPolicy.default()
    resolved_visibility_policy = (
        visibility_policy
        if visibility_policy is not None
        else resolved_heliacal_policy.visibility_policy
    )
    if (
        resolved_visibility_policy is not None
        and resolved_visibility_policy.criterion_family
        is VisibilityCriterionFamily.CRUMEY_2014_POINT_SOURCE
    ):
        raise ValueError(
            "CRUMEY_2014_POINT_SOURCE is admitted for single-epoch "
            "visibility_assessment only; physical event-search doctrine "
            "has not been admitted"
        )
    resolved_search_policy = search_policy if search_policy is not None else VisibilitySearchPolicy()
    search_uses_refraction = (
        resolved_visibility_policy.use_refraction
        if resolved_visibility_policy is not None
        else True
    )

    model = _effective_visibility_model(
        HeliacalPolicy(
            optical_aid=resolved_heliacal_policy.optical_aid,
            use_extended_atmosphere=resolved_heliacal_policy.use_extended_atmosphere,
            visibility_model=resolved_heliacal_policy.visibility_model,
            visibility_policy=resolved_visibility_policy,
        )
    )
    if target_kind is VisibilityTargetKind.PLANET:
        _validate_args(body, jd_start, lat, lon, resolved_search_policy.search_window_days)
    else:
        if not math.isfinite(jd_start):
            raise ValueError(f"jd_start must be finite, got {jd_start}")
        if not -90.0 <= lat <= 90.0:
            raise ValueError(f"lat must be in [-90, 90], got {lat}")
        if not -180.0 <= lon <= 180.0:
            raise ValueError(f"lon must be in [-180, 180], got {lon}")
        if not (
            isinstance(resolved_search_policy.search_window_days, int)
            and resolved_search_policy.search_window_days > 0
        ):
            raise ValueError(
                "search_window_days must be a positive integer, "
                f"got {resolved_search_policy.search_window_days!r}"
            )
    jd_mid0 = math.floor(jd_start + 0.5) - 0.5
    search_days = resolved_search_policy.search_window_days

    if (
        target_kind is VisibilityTargetKind.MOON
        and resolved_visibility_policy is not None
        and resolved_visibility_policy.criterion_family
        is VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT
    ):
        if event_kind not in (
            HeliacalEventKind.ACRONYCHAL_RISING,
            HeliacalEventKind.ACRONYCHAL_SETTING,
        ):
            raise NotImplementedError(
                "YALLOP_LUNAR_CRESCENT currently governs evening first-sighting "
                "and last-evening lunar crescent events only"
            )
        environment = resolved_visibility_policy.environment
        assert environment is not None
        if event_kind is HeliacalEventKind.ACRONYCHAL_RISING:
            for d in range(search_days):
                details = _lunar_crescent_details_for_evening(jd_mid0 + d, lat, lon)
                if details is None:
                    continue
                if _yallop_class_observable(details.visibility_class, environment.observing_aid):
                    return _general_event_from_lunar_crescent_details(
                        event_kind,
                        details,
                        lat,
                        lon,
                        visibility_policy=resolved_visibility_policy,
                    )
            return None

        last_visible: LunarCrescentDetails | None = None
        for d in range(search_days):
            details = _lunar_crescent_details_for_evening(jd_mid0 + d, lat, lon)
            if details is None:
                if last_visible is not None:
                    return _general_event_from_lunar_crescent_details(
                        event_kind,
                        last_visible,
                        lat,
                        lon,
                        visibility_policy=resolved_visibility_policy,
                    )
                continue
            if _yallop_class_observable(details.visibility_class, environment.observing_aid):
                last_visible = details
            elif last_visible is not None:
                return _general_event_from_lunar_crescent_details(
                    event_kind,
                    last_visible,
                    lat,
                    lon,
                    visibility_policy=resolved_visibility_policy,
                )
        return None

    if target_kind is VisibilityTargetKind.STAR:
        from .stars import heliacal_rising_event, heliacal_setting_event

        if event_kind is HeliacalEventKind.HELIACAL_RISING:
            event = heliacal_rising_event(
                body,
                jd_start,
                lat,
                lon,
                search_days=search_days,
            )
            if not event.is_found or event.jd_ut is None:
                return None
            sun_altitude_deg = event.computation_truth.qualifying_sun_altitude
            assert sun_altitude_deg is not None
            return _general_event_from_jd(
                body,
                event_kind,
                event.jd_ut,
                lat,
                lon,
                sun_altitude_deg=sun_altitude_deg,
                visibility_policy=resolved_visibility_policy,
            )

        if event_kind is HeliacalEventKind.HELIACAL_SETTING:
            event = heliacal_setting_event(
                body,
                jd_start,
                lat,
                lon,
                search_days=search_days,
            )
            if not event.is_found or event.jd_ut is None:
                return None
            sun_altitude_deg = event.computation_truth.qualifying_sun_altitude
            assert sun_altitude_deg is not None
            return _general_event_from_jd(
                body,
                event_kind,
                event.jd_ut,
                lat,
                lon,
                sun_altitude_deg=sun_altitude_deg,
                visibility_policy=resolved_visibility_policy,
            )

        result = _search_visibility_event(
            body,
            event_kind,
            jd_mid0,
            lat,
            lon,
            model=model,
            search_days=search_days,
            target_solar_altitude_deg=(
                _COSMIC_SOLAR_ALTITUDE_DEG
                if event_kind in (HeliacalEventKind.COSMIC_RISING, HeliacalEventKind.COSMIC_SETTING)
                else None
            ),
            use_refraction=search_uses_refraction,
        )
        if result is None:
            return None
        return _general_event_from_tuple(
            body,
            event_kind,
            result,
            lat,
            lon,
            visibility_policy=resolved_visibility_policy,
        )

    if event_kind is HeliacalEventKind.HELIACAL_RISING:
        for d in range(search_days):
            jd_midnight = jd_mid0 + d
            se = _signed_elongation(body, jd_midnight + 0.5)
            if se >= 0.0 or abs(se) < _ELONG_MIN:
                continue
            vis = _check_visibility(
                body,
                jd_midnight,
                lat,
                lon,
                morning=True,
                model=model,
                use_refraction=search_uses_refraction,
            )
            if vis is not None:
                jd_ev, p_alt, s_alt, mag = vis
                return _general_event_from_tuple(
                    body,
                    event_kind,
                    (jd_ev, p_alt, s_alt, mag, se),
                    lat,
                    lon,
                    visibility_policy=resolved_visibility_policy,
                )
        return None

    if event_kind is HeliacalEventKind.HELIACAL_SETTING:
        last: tuple[float, float, float, float, float] | None = None
        for d in range(search_days):
            jd_midnight = jd_mid0 + d
            se = _signed_elongation(body, jd_midnight + 0.5)
            abs_se = abs(se)
            if se < 0.0 and abs_se >= _ELONG_MIN:
                vis = _check_visibility(
                    body,
                    jd_midnight,
                    lat,
                    lon,
                    morning=True,
                    model=model,
                    use_refraction=search_uses_refraction,
                )
                if vis is not None:
                    jd_ev, p_alt, s_alt, mag = vis
                    last = (jd_ev, p_alt, s_alt, mag, se)
            elif last is not None and abs_se < _ELONG_MIN:
                return _general_event_from_tuple(
                    body,
                    event_kind,
                    last,
                    lat,
                    lon,
                    visibility_policy=resolved_visibility_policy,
                )
        return None

    if event_kind is HeliacalEventKind.ACRONYCHAL_RISING:
        for d in range(search_days):
            jd_midnight = jd_mid0 + d
            se = _signed_elongation(body, jd_midnight + 0.5)
            if se <= 0.0 or abs(se) < _ELONG_MIN:
                continue
            vis = _check_visibility(
                body,
                jd_midnight,
                lat,
                lon,
                morning=False,
                model=model,
                use_refraction=search_uses_refraction,
            )
            if vis is not None:
                jd_ev, p_alt, s_alt, mag = vis
                return _general_event_from_tuple(
                    body,
                    event_kind,
                    (jd_ev, p_alt, s_alt, mag, se),
                    lat,
                    lon,
                    visibility_policy=resolved_visibility_policy,
                )
        return None

    if event_kind is HeliacalEventKind.ACRONYCHAL_SETTING:
        last = None
        for d in range(search_days):
            jd_midnight = jd_mid0 + d
            se = _signed_elongation(body, jd_midnight + 0.5)
            abs_se = abs(se)
            if se > 0.0 and abs_se >= _ELONG_MIN:
                vis = _check_visibility(
                    body,
                    jd_midnight,
                    lat,
                    lon,
                    morning=False,
                    model=model,
                    use_refraction=search_uses_refraction,
                )
                if vis is not None:
                    jd_ev, p_alt, s_alt, mag = vis
                    last = (jd_ev, p_alt, s_alt, mag, se)
            elif last is not None and abs_se < _ELONG_MIN:
                return _general_event_from_tuple(
                    body,
                    event_kind,
                    last,
                    lat,
                    lon,
                    visibility_policy=resolved_visibility_policy,
                )
        return None

    if event_kind in (HeliacalEventKind.COSMIC_RISING, HeliacalEventKind.COSMIC_SETTING):
        result = _search_visibility_event(
            body,
            event_kind,
            jd_mid0,
            lat,
            lon,
            model=model,
            search_days=search_days,
            target_solar_altitude_deg=_COSMIC_SOLAR_ALTITUDE_DEG,
            use_refraction=search_uses_refraction,
        )
        if result is None:
            return None
        return _general_event_from_tuple(
            body,
            event_kind,
            result,
            lat,
            lon,
            visibility_policy=resolved_visibility_policy,
        )

    raise NotImplementedError(f"unsupported event kind {event_kind!r}")


def _planet_event_from_general_event(
    event: GeneralVisibilityEvent | None,
) -> PlanetHeliacalEvent | None:
    """
    Convert a generalized event vessel into the legacy planetary event vessel.

    Returns None when input is None.

    Raises:
        ValueError: If ``event`` is non-planetary and therefore not valid for
            legacy planetary helper surfaces.

    Side effects: None.
    """
    if event is None:
        return None
    if event.target_kind is not VisibilityTargetKind.PLANET:
        raise ValueError(
            "planetary heliacal helpers can only wrap planetary generalized events"
        )
    return PlanetHeliacalEvent(
        body=event.body,
        kind=event.kind,
        jd_ut=event.jd_ut,
        elongation_deg=event.elongation_deg,
        planet_altitude_deg=event.target_altitude_deg,
        sun_altitude_deg=event.sun_altitude_deg,
        apparent_magnitude=event.apparent_magnitude,
    )

def planet_heliacal_rising(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    policy: HeliacalPolicy | None = None,
    search_days: int = 400,
) -> PlanetHeliacalEvent | None:
    """
    Find the next heliacal rising of a planet from ``jd_start``.

    The heliacal rising is the first morning when the planet is visible in
    the eastern sky before sunrise, after a period of solar invisibility.
    This is the classical *first appearance* — Venus rising as the morning
    star (Lucifer / Phosphoros), or Mars/Jupiter/Saturn emerging from the
    Sun's rays.

    Parameters
    ----------
    body        : Planet body constant (``Body.VENUS``, ``Body.MARS``, etc.).
                  ``Body.SUN``, ``Body.MOON``, and ``Body.EARTH`` raise
                  ``ValueError``.
    jd_start    : Julian Day (UT1) to begin the forward search.
                  Start near or just before the expected solar conjunction
                  for best results.
    lat         : Observer latitude (degrees, north positive).
    lon         : Observer longitude (degrees, east positive).
    policy      : :class:`HeliacalPolicy` governing visibility conditions.
                  Defaults to standard naked-eye dark-sky conditions.
    search_days : Maximum number of days to scan forward.  Increase for
                  slow outer planets.  Default 400.

    Returns
    -------
    :class:`PlanetHeliacalEvent` or ``None`` if no event is found within
    ``search_days``.

    Algorithm
    ---------
    For each day in the search window:

    1. Compute signed elongation.  Skip if ≥ 0° (planet not in morning sky)
       or |elongation| < 5° (too close to Sun).
    2. Compute the planet's apparent magnitude → arcus visionis.
    3. Find the moment when the Sun's altitude = −arcus_visionis before
    sunrise (bisection on solar altitude).
    4. Compute planet altitude at that moment.  If planet is above the
    visibility horizon → heliacal rising.
    """
    _validate_args(body, jd_start, lat, lon, search_days)
    return _planet_event_from_general_event(
        visibility_event(
            body,
            HeliacalEventKind.HELIACAL_RISING,
            jd_start,
            lat,
            lon,
            heliacal_policy=policy,
            search_policy=VisibilitySearchPolicy(search_window_days=search_days),
        )
    )


def planet_heliacal_setting(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    policy: HeliacalPolicy | None = None,
    search_days: int = 400,
) -> PlanetHeliacalEvent | None:
    """
    Find the next heliacal setting of a planet from ``jd_start``.

    The heliacal setting is the last morning when the planet is visible
    before it disappears into the Sun's light ahead of solar conjunction.

    The search scans forward, tracking the last visible morning.  When the
    planet's elongation drops below the minimum threshold (planet re-enters
    the Sun's glare), the last recorded visible morning is returned.

    Parameters
    ----------
    body, jd_start, lat, lon, policy, search_days : see
        :func:`planet_heliacal_rising`.

    Notes
    -----
    Start ``jd_start`` when the planet is already in the morning sky for
    best results.  If no visible morning is found before the search ends,
    returns ``None``.
    """
    _validate_args(body, jd_start, lat, lon, search_days)
    return _planet_event_from_general_event(
        visibility_event(
            body,
            HeliacalEventKind.HELIACAL_SETTING,
            jd_start,
            lat,
            lon,
            heliacal_policy=policy,
            search_policy=VisibilitySearchPolicy(search_window_days=search_days),
        )
    )


def planet_acronychal_rising(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    policy: HeliacalPolicy | None = None,
    search_days: int = 400,
) -> PlanetHeliacalEvent | None:
    """
    Find the next acronychal rising of a planet from ``jd_start``.

    The acronychal rising is the first evening when the planet is visible
    in the western sky after sunset — the first appearance as an evening
    star.  For Venus this is the Hesperus / evening-star phase; for outer
    planets it corresponds to the first evening visibility after the planet
    has passed through the morning sky and now re-enters evening apparition.

    Parameters
    ----------
    body, jd_start, lat, lon, policy, search_days : see
        :func:`planet_heliacal_rising`.
    """
    _validate_args(body, jd_start, lat, lon, search_days)
    return _planet_event_from_general_event(
        visibility_event(
            body,
            HeliacalEventKind.ACRONYCHAL_RISING,
            jd_start,
            lat,
            lon,
            heliacal_policy=policy,
            search_policy=VisibilitySearchPolicy(search_window_days=search_days),
        )
    )


def planet_acronychal_setting(
    body: str,
    jd_start: float,
    lat: float,
    lon: float,
    policy: HeliacalPolicy | None = None,
    search_days: int = 400,
) -> PlanetHeliacalEvent | None:
    """
    Find the next acronychal setting of a planet from ``jd_start``.

    The acronychal setting is the last evening when the planet is visible
    after sunset before it disappears into the Sun's light ahead of solar
    conjunction.

    Parameters
    ----------
    body, jd_start, lat, lon, policy, search_days : see
        :func:`planet_heliacal_rising`.
    """
    _validate_args(body, jd_start, lat, lon, search_days)
    return _planet_event_from_general_event(
        visibility_event(
            body,
            HeliacalEventKind.ACRONYCHAL_SETTING,
            jd_start,
            lat,
            lon,
            heliacal_policy=policy,
            search_policy=VisibilitySearchPolicy(search_window_days=search_days),
        )
    )

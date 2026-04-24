"""
Moira — heliacal.py
Heliacal and Visibility Doctrine Pillar

Purpose
-------
Provides the complete heliacal and generalized visibility doctrine surface for Moira:
- typed doctrine surfaces for heliacal phenomena and generalized visibility policy
- concrete planetary heliacal/acronychal event helpers
- the generalized visibility event surface for planets, fixed stars, and the Moon
- observer-environment policy with Bortle-class light-pollution derivation
- moonlight-aware limiting-magnitude penalty via Krisciunas & Schaefer (1991)

Implemented surfaces:
- ``HeliacalEventKind``                    — exhaustive event-kind enum
- ``VisibilityTargetKind``                 — planet / star / moon classifier
- ``LightPollutionClass``                  — Bortle 1–9 typed scale
- ``LightPollutionDerivationMode``         — Bortle table or linear derivation
- ``ObserverAid``                          — naked eye / binoculars / telescope
- ``ObserverVisibilityEnvironment``        — full observer environment vessel
- ``VisibilityCriterionFamily``            — limiting-magnitude threshold and
                                             Yallop lunar crescent
- ``VisibilityExtinctionModel``            — named extinction treatment slot
- ``VisibilityTwilightModel``              — named twilight treatment slot
- ``ExtinctionCoefficient``               — named reference values (K&S 1991)
- ``MoonlightPolicy``                      — IGNORE or KRISCIUNAS_SCHAEFER_1991
- ``VisibilityPolicy``                     — unified admitted visibility policy;
                                             includes ``extinction_coefficient_k``
- ``VisibilitySearchPolicy``               — search-window and step-size policy
- ``LunarCrescentVisibilityClass``         — Yallop A–F class
- ``LunarCrescentDetails``                 — Yallop derived quantities vessel
- ``VisibilityAssessment``                 — direct visibility result at one instant
- ``GeneralVisibilityEvent``               — generalized event search result
- ``PlanetHeliacalEvent``                  — narrow planetary event result
- ``VisibilityModel``                      — legacy narrow observer vessel (V0 compat)
- ``HeliacalPolicy``                       — legacy narrow policy vessel (V0 compat)
- ``visibility_assessment``               — single-instant observability check
- ``visual_limiting_magnitude``           — effective limiting magnitude at an instant
- ``visibility_event``                     — generalized event search surface
- ``planet_heliacal_rising``
- ``planet_heliacal_setting``
- ``planet_acronychal_rising``
- ``planet_acronychal_setting``

Boundary
--------
Owns:
    All heliacal and visibility doctrine surfaces listed above.

Delegates to:
    moira.stars      — fixed-star heliacal event search (heliacal_rising_event,
                       heliacal_setting_event)
    moira.planets    — planetary apparent positions and magnitudes
    moira.phase      — phase angle and apparent magnitude
    moira.rise_set   — altitude, twilight, and rise/set phenomena
    moira.coordinates — equatorial-to-horizontal transforms

Import-time side effects: None

External dependency assumptions
---------------------------------
- DE441 kernel accessible via moira.planets (required for planetary positions).
- moira.constants.Body constants available for body identity.
- No OS-level features, threads, or network access required.

Public surface / exports
------------------------
See ``__all__`` below.  All 27 names are stable public API.

K&S 1991 moonlight model (V6 partial)
--------------------------------------
Authority: Krisciunas, K. & Schaefer, B.E. (1991), PASP 103, 1033–1039.
Implemented equations:
- Eq. 9  — lunar apparent magnitude as a function of phase angle
- Eq. 3  — atmospheric scattering function f(ρ)
- Eq. 20 — top-of-atmosphere lunar illuminance I*(α)
- Eq. 21 — moonlight sky brightness in nanolamberts
The penalty is applied as Δm_L = −2.5 log₁₀(1 + B_moon / B_dark), where
B_dark is derived from the Bortle SQM table.  The extinction coefficient
defaults to 0.20 mag/airmass (good mid-latitude dark site); ``ExtinctionCoefficient``
holds named reference values.

Validation status
-----------------
- Yallop lunar crescent corpus: 295/295 within ±0.05 q-value (2026-04-05).
  Mean residual 0.0077, max 0.0315.  See wiki/03_validation/VALIDATION_ASTRONOMY.md.
- K&S 1991 moonlight: unit-tested against paper formulas; no live-ephemeris
  integration corpus yet.

Deferred
--------
- Stellar heliacal event batch validation corpus beyond the Sothic/Sirius anchor.
- Integration test for moonlight under real ephemeris conditions.
- Summit-grade generalized visibility corpus across criterion families.
- Terrain/horizon profile integration.

Constitution entry
------------------
    Pillar:       Heliacal / Visibility
    SCP entry:    moira/stars.py, STARS_BACKEND_STANDARD.md
    Current state:
        - planetary heliacal/acronychal helpers implemented (V0)
        - observer-environment and light-pollution policy implemented (V1)
        - visibility criterion family and limiting-magnitude doctrine (V2)
        - generalized event surface for planets, stars, Moon (V3)
        - Yallop corpus validation passing 295/295 (V4)
        - public surface widened, 18 names promoted (V5)
        - K&S 1991 moonlight model admitted (V6 partial)

    Design invariants (must hold in all future changes):
    - No legacy integer bitfields.
    - Narrow planetary helpers remain distinguishable from the generalized surface.
    - Visibility doctrine, observer environment, and search policy stay separate.
    - HeliacalEventKind is exhaustive; new kinds require doctrinal justification.
    - Results are in Julian Day (UT1), never formatted strings.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, IntEnum

from .constants import Body


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
    "visibility_assessment",
    "visual_limiting_magnitude",
    "visibility_event",
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

    THEOREM: Str-enum naming the two currently admitted visibility criterion
    families that govern observability decisions.

    RITE OF PURPOSE:
        Separates the limiting-magnitude threshold family (used for planets and
        fixed stars) from the Yallop lunar crescent family (used for the Moon),
        ensuring that each dispatch path within visibility_assessment() and
        visibility_event() applies the correct observability test.  Explicit
        family selection prevents silent application of a planetary threshold
        to a crescent-moon event.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the two admitted criterion families.
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
            "members": ["LIMITING_MAGNITUDE_THRESHOLD", "YALLOP_LUNAR_CRESCENT"]
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
    YALLOP_LUNAR_CRESCENT = "yallop_lunar_crescent"


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

    THEOREM: Str-enum naming the admitted extinction treatment applied when
    computing visibility under the LIMITING_MAGNITUDE_THRESHOLD criterion.

    RITE OF PURPOSE:
        Holds the named extinction treatment slot so that policy objects can
        declare which extinction model governs their arcus-visionis derivation.
        Currently a single member (LEGACY_ARCUS_VISIONIS), preserving the slot
        for future admission of more rigorous airmass-based extinction models
        without requiring a breaking policy-field change.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the admitted extinction treatments.
            - Serve as the extinction_model field of VisibilityPolicy.
        Non-responsibilities:
            - Does not implement extinction computation (handled by
              _arcus_visionis()).
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
            "members": ["LEGACY_ARCUS_VISIONIS"]
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


class VisibilityTwilightModel(str, Enum):
    """
    RITE: The Twilight Slot — the admitted twilight treatment declaration.

    THEOREM: Str-enum naming the admitted twilight treatment used to determine
    the visibility-threshold solar depression moment.

    RITE OF PURPOSE:
        Holds the named twilight treatment so that policy objects can declare
        which solar-depression model governs when the visibility-threshold
        twilight moment is found.  Currently a single member
        (ARCUS_VISIONIS_SOLAR_DEPRESSION), preserving the slot for future
        admission of alternative twilight definitions without a breaking
        policy-field change.

    LAW OF OPERATION:
        Responsibilities:
            - Enumerate the admitted twilight treatments.
            - Serve as the twilight_model field of VisibilityPolicy.
        Non-responsibilities:
            - Does not implement the twilight search (handled by
              _find_sun_at_alt()).
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
            "members": ["ARCUS_VISIONIS_SOLAR_DEPRESSION"]
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
            - Carry site darkness class, explicit limiting magnitude override,
              local horizon altitude, atmospheric parameters, and observing aid.
            - Validate relative_humidity, pressure_mbar, and
              observer_altitude_m on construction.
            - Serve as the environment field of VisibilityPolicy.
        Non-responsibilities:
            - Does not compute limiting magnitude (delegated to
              _effective_limiting_magnitude()).
            - Does not apply atmospheric refraction (delegated to
              moira.rise_set._altitude()).
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
    local_horizon_altitude_deg: float = 0.0
    temperature_c: float = 10.0
    pressure_mbar: float = 1013.25
    relative_humidity: float = 0.5
    observer_altitude_m: float = 0.0
    observing_aid: ObserverAid = ObserverAid.NAKED_EYE

    def __post_init__(self) -> None:
        if self.limiting_magnitude is not None and not math.isfinite(self.limiting_magnitude):
            raise ValueError("limiting_magnitude must be finite when provided")
        if not math.isfinite(self.local_horizon_altitude_deg):
            raise ValueError("local_horizon_altitude_deg must be finite")
        if not 0.0 <= self.relative_humidity <= 1.0:
            raise ValueError("relative_humidity must be in [0, 1]")
        if self.pressure_mbar < 0.0:
            raise ValueError("pressure_mbar must be >= 0")
        if self.observer_altitude_m < -1000.0:
            raise ValueError("observer_altitude_m is implausibly low")


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
                "extinction_coefficient_k"
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
            "raises": ["ValueError for YALLOP_LUNAR_CRESCENT with incompatible twilight_model"],
            "policy": "__post_init__ enforces criterion/twilight compatibility"
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
    """Broadband extinction coefficient (mag/airmass) used by the
    Krisciunas & Schaefer (1991) moonlight model.

    Use the :class:`ExtinctionCoefficient` named holders for the
    four admitted reference site classes:

    - ``ExtinctionCoefficient.MAUNA_KEA``       = 0.172  (exceptional high-altitude site)
    - ``ExtinctionCoefficient.GOOD_DARK_SITE``  = 0.20   (recommended default)
    - ``ExtinctionCoefficient.TYPICAL``         = 0.25   (typical clear site)
    - ``ExtinctionCoefficient.HAZY``            = 0.30   (hazy or coastal conditions)

    This field has no effect when ``moonlight_policy`` is ``IGNORE``.
    """

    def __post_init__(self) -> None:
        if self.environment is None:
            object.__setattr__(self, "environment", ObserverVisibilityEnvironment())
        if (
            self.criterion_family is VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT
            and self.twilight_model is not VisibilityTwilightModel.ARCUS_VISIONIS_SOLAR_DEPRESSION
        ):
            raise ValueError(
                "YALLOP_LUNAR_CRESCENT currently requires the standard twilight model slot"
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
        horizon_altitude_deg: Effective visibility horizon altitude above
            the geometric horizon (degrees).  Default 0.0.
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
) -> float:
    """Altitude of *body* above the observer's horizon (degrees)."""
    from .rise_set import _altitude
    return _altitude(
        jd,
        lat,
        lon,
        body,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
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
# Krisciunas & Schaefer (1991) moonlight sky-brightness model
# ---------------------------------------------------------------------------
# Authority: Krisciunas, K. & Schaefer, B.E. (1991), PASP 103, 1033-1039.
# "A model for the brightness of moonlight."
# The formulas below implement the paper's admitted derivation chain:
#   Eq. 9  → lunar apparent magnitude as function of phase angle
#   Eq. 3  → scattering function f(rho)
#   Eq. 20 → top-of-atmosphere lunar illuminance I*(alpha)
#   Eq. 21 → moonlight sky brightness B_moon in nanolamberts
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

    Krisciunas & Schaefer (1991), Eq. 3.
    rho_deg: angular separation (degrees) between Moon and target sky point.
    Clamped to >= 10 degrees: the model is not valid for very small separations.
    """
    rho = max(rho_deg, 10.0)
    rho_r = math.radians(rho)
    return (
        10.0**5.36 * (1.06 + math.cos(rho_r)**2)
        + 10.0**(6.15 - rho / 40.0)
    )


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
        Angular separation between Moon and target (degrees). Clamped to >= 10 deg.
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

    # Eq. 3: scattering function
    f_rho = _ks1991_scattering_function(rho_deg)

    # Plane-parallel airmass (clamped to avoid divergence at horizon)
    x_moon = min(1.0 / math.sin(math.radians(alt_moon_deg)), 40.0)
    x_target = min(1.0 / math.sin(math.radians(alt_target_deg)), 40.0)

    # Eq. 21: moonlight sky brightness in nanolamberts
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
    policy. Conversion: B_nL = 34.08 * 10^((21.572 - mu_SQM) / 2.5).
    """
    environment = policy.environment
    assert environment is not None
    lpc = environment.light_pollution_class
    sqm = _BORTLE_SKY_SQM_TABLE.get(lpc, _BORTLE_SKY_SQM_TABLE[LightPollutionClass.BORTLE_3])
    return 34.08 * 10.0**((21.572 - sqm) / 2.5)


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
    from .phase import phase_angle as _phase_angle

    moon_az, moon_alt = _true_horizontal(Body.MOON, jd_ut, lat, lon)
    if moon_alt <= 0.0:
        return 0.0

    tgt_az, tgt_alt = _true_horizontal(body, jd_ut, lat, lon)
    if tgt_alt <= 0.0:
        return 0.0

    moon_phase = _phase_angle(Body.MOON, jd_ut)

    # Angular separation Moon–target via spherical dot product
    cos_rho = (
        math.sin(math.radians(moon_alt)) * math.sin(math.radians(tgt_alt))
        + math.cos(math.radians(moon_alt)) * math.cos(math.radians(tgt_alt))
        * math.cos(math.radians(moon_az - tgt_az))
    )
    rho_deg = math.degrees(math.acos(max(-1.0, min(1.0, cos_rho))))

    _EXTINCTION_K = policy.extinction_coefficient_k
    b_moon = _ks1991_moonlight_nanolamberts(rho_deg, moon_alt, moon_phase, _EXTINCTION_K, tgt_alt)
    if b_moon <= 0.0:
        return 0.0

    b_dark = _ks1991_dark_sky_nanolamberts(policy)
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
    from .julian import ut_to_tt
    from .planets import planet_at
    from .stars import star_at

    jd_tt = ut_to_tt(jd_ut)
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
) -> float:
    """
    Return apparent altitude for a planet, Moon, or fixed star.

    Uses the refraction-aware altitude engine in ``moira.rise_set``.

    Raises:
        ValueError: Propagated by downstream altitude solver for invalid body
            identities or numeric inputs.

    Side effects: None.
    """
    from .rise_set import _altitude

    return _altitude(
        jd_ut,
        lat,
        lon,
        body,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
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
) -> tuple[float, float, float, float] | None:
    """
    Check whether *body* is visible at the arcus-visionis twilight moment on
    the given day.

    Returns ``(twilight_jd, planet_alt_deg, sun_alt_deg, magnitude)`` if
    visible, else ``None``.

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
    planet_alt = _target_altitude(body, twilight_jd, lat, lon)
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
) -> tuple[float, float, float, float] | None:
    """
    Evaluate visibility on a day at an explicit solar-altitude threshold.

    Returns ``(twilight_jd, target_alt_deg, sun_alt_deg, magnitude)`` when the
    target is above local horizon and bright enough at the threshold moment.

    Side effects: None.
    """
    mag = _target_apparent_magnitude(body, jd_midnight + 0.5)

    twilight_jd = _find_sun_at_alt(jd_midnight, lat, lon, target_solar_altitude_deg, morning)
    if twilight_jd is None:
        return None
    planet_alt = _target_altitude(
        body,
        twilight_jd,
        lat,
        lon,
        pressure_mbar=model.pressure_mbar,
        temperature_c=model.temperature_c,
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
) -> tuple[float, float, float, float, float] | None:
    """
    Execute the core forward visibility-event search state machine.

    Returns the first qualifying event tuple for rising kinds, or the last
    qualifying visible tuple for setting kinds prior to loss conditions.

    The return payload is ``(jd_ut, target_alt_deg, sun_alt_deg,
    apparent_mag, signed_elongation_deg)``.

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
        (lambda jd_midnight: _check_visibility(body, jd_midnight, lat, lon, morning=morning, model=model))
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
        Provides a fully auditable visibility result: the raw intermediate values
        (true and apparent altitude, effective limiting magnitude, solar
        elongation, moonlight contribution) alongside the final observable boolean,
        so that callers can inspect every step of the observability decision rather
        than receiving only a boolean answer.  Without this vessel, diagnosing
        threshold boundary cases would require re-running subcomputations manually.

    LAW OF OPERATION:
        Responsibilities:
            - Carry all intermediate and final values from a single call to
              visibility_assessment().
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
            - moonlight_sky_nanolamberts is non-None iff K&S 1991 moonlight
              penalty was applied.

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
                "lunar_crescent_details", "moonlight_sky_nanolamberts"
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
    effective_limiting_magnitude: float
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

# V0 note:
# The functions below are real, admitted planetary event surfaces. They are
# not the full generalized visibility subsystem, which remains deferred until
# observer-environment policy and a broader validation corpus are
# constitutionalized across more doctrine families.

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

    This is the standalone public surface for the currently admitted criterion
    families: LIMITING_MAGNITUDE_THRESHOLD for planets and fixed stars, and
    YALLOP_LUNAR_CRESCENT for the Moon.

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

    effective_limiting_magnitude = _effective_limiting_magnitude(resolved_policy)
    moonlight_sky_nl: float | None = None
    if resolved_policy.moonlight_policy is MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991:
        delta = _ks1991_limiting_magnitude_penalty(resolved_policy, jd_ut, lat, lon, body)
        if delta < 0.0:
            moonlight_sky_nl = _ks1991_dark_sky_nanolamberts(resolved_policy)
            effective_limiting_magnitude += delta
    true_altitude_deg = _true_altitude(body, jd_ut, lat, lon)
    if resolved_policy.use_refraction:
        apparent_altitude_deg = _planet_alt(
            body,
            jd_ut,
            lat,
            lon,
            pressure_mbar=environment.pressure_mbar,
            temperature_c=environment.temperature_c,
        )
    else:
        apparent_altitude_deg = true_altitude_deg

    apparent_mag = _target_apparent_magnitude(body, jd_ut)
    is_geometrically_visible = apparent_altitude_deg >= environment.local_horizon_altitude_deg
    solar_elongation_deg = _target_signed_elongation(body, jd_ut)

    lunar_crescent_details = None
    if (
        body == Body.MOON
        and resolved_policy.criterion_family is VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT
    ):
        lunar_crescent_details = _lunar_crescent_details_at(jd_ut, lat, lon)
        is_bright_enough = _yallop_class_observable(
            lunar_crescent_details.visibility_class,
            environment.observing_aid,
        )
    else:
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
        observable=is_geometrically_visible and is_bright_enough,
        lunar_crescent_details=lunar_crescent_details,
        moonlight_sky_nanolamberts=moonlight_sky_nl,
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
    magnitude = _effective_limiting_magnitude(resolved_policy)
    if resolved_policy.moonlight_policy is MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991:
        delta = _ks1991_limiting_magnitude_penalty(
            resolved_policy, jd_ut, lat, lon, Body.MOON
        )
        if delta < 0.0:
            magnitude += delta
    return magnitude


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
    resolved_search_policy = search_policy if search_policy is not None else VisibilitySearchPolicy()

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
            vis = _check_visibility(body, jd_midnight, lat, lon, morning=True, model=model)
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
                vis = _check_visibility(body, jd_midnight, lat, lon, morning=True, model=model)
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
            vis = _check_visibility(body, jd_midnight, lat, lon, morning=False, model=model)
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
                vis = _check_visibility(body, jd_midnight, lat, lon, morning=False, model=model)
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

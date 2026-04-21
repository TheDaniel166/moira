from __future__ import annotations

"""
Lots Engine — moira/lots.py

Archetype: Engine
Purpose: Computes Arabic Parts (Hermetic Lots) for ~430 named lots drawn from
         Hellenistic, medieval, and modern sources, using the formula
         Lot = ASC + Add − Subtract (mod 360°) with automatic day/night
         reversal where the tradition requires it.

Boundary declaration:
    Owns: the comprehensive lots catalogue (PARTS_DEFINITIONS), the reference-
          key resolver (planets, angles, house cusps, rulers, fixed degrees,
          pre-computed lots), the day/night reversal logic, and the ArabicPart
          and PartDefinition result types.
    Delegates: chart data access to moira.chart.ChartContext; sign arithmetic
               to moira.constants.sign_of and SIGNS.

Import-time side effects: None

External dependency assumptions:
    - moira.chart.ChartContext exposes planet longitudes, house cusps, and
      Ascendant/MC as named attributes.
    - moira.constants.SIGNS is an ordered list of 12 sign name strings.

Public surface / exports:
    PartDefinition        — catalogue entry for a single lot
    ArabicPart            — computed result for a single lot
    ArabicPartsService    — service class for computing lots from a chart
    PARTS_DEFINITIONS     — list of all ~430 PartDefinition entries
    calculate_arabic_parts() — module-level convenience wrapper
"""

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite

from .constants import sign_of, SIGNS
from .chart import ChartContext


__all__ = [
    # Enumerations
    "LotReferenceKind", "LotReversalKind", "LotDependencyRole",
    "LotConditionState", "LotConditionNetworkEdgeMode", "LotsReferenceFailureMode",
    # Policy
    "LotsDerivedReferencePolicy", "LotsExternalReferencePolicy", "LotsComputationPolicy",
    # Truth / Classification
    "LotReferenceTruth", "ArabicPartComputationTruth",
    "LotReferenceClassification", "ArabicPartClassification",
    # Condition vessels
    "LotDependency",
    "LotConditionProfile", "LotChartConditionProfile",
    "LotConditionNetworkNode", "LotConditionNetworkEdge", "LotConditionNetworkProfile",
    # Core vessels
    "ArabicPart",
    # Functions
    "calculate_lots",
    "calculate_lot_dependencies", "calculate_all_lot_dependencies",
    "calculate_lot_condition_profiles", "calculate_lot_chart_condition_profile",
    "calculate_lot_condition_network_profile",
    "ArabicPartsService", "list_parts",
]


# ---------------------------------------------------------------------------
# Traditional sign rulers (used for house-ruler lookups)
# ---------------------------------------------------------------------------

_SIGN_RULER: dict[str, str] = {
    "Aries":       "Mars",
    "Taurus":      "Venus",
    "Gemini":      "Mercury",
    "Cancer":      "Moon",
    "Leo":         "Sun",
    "Virgo":       "Mercury",
    "Libra":       "Venus",
    "Scorpio":     "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn":   "Saturn",
    "Aquarius":    "Saturn",
    "Pisces":      "Jupiter",
}

# Fixed-degree constants (tropical ecliptic longitude, degrees)
_FIXED_DEG: dict[str, float] = {
    "18 Aries":   18.0,
    "2 Taurus":   32.0,
    "0 Gemini":   60.0,
    "15 Cancer": 105.0,
    "29 Cancer": 119.0,
    "0 Leo":     120.0,
    "15 Leo":    135.0,
    "0 Virgo":   150.0,
    "Leo":       120.0,    # start of Leo (used in The King)
    "Cancer":     90.0,    # start of Cancer (used in The Month)
    "Vindemiatrix": 193.0, # ε Vir fixed star, approx 13° Libra (J2000)
}


# ---------------------------------------------------------------------------
# Part definition
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PartDefinition:
    """
    RITE: The Sacred Formula — the immutable recipe for a single Arabic Part,
          encoding its name, day and night ingredients, reversal rule, and
          traditional category.

    THEOREM: Immutable catalogue entry for one Arabic Part, storing the
             day-formula operands, the night-reversal flag, the tradition
             category, and an optional description.

    RITE OF PURPOSE:
        PartDefinition is the atomic unit of the lots catalogue.  It separates
        the definition of a lot from its computation, allowing the catalogue to
        be inspected, filtered, and extended without touching the calculation
        engine.  Without this vessel, the ~430 lot formulas would be embedded
        as raw tuples with no semantic labels.

    LAW OF OPERATION:
        Responsibilities:
            - Store name, day_add, day_sub, reverse_at_night, category,
              and optional description.
        Non-responsibilities:
            - Does not compute the lot longitude; that is ArabicPartsService's role.
            - Does not validate that day_add and day_sub are resolvable keys.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - None beyond Python builtins.
        Structural invariants:
            - name is a non-empty string uniquely identifying the lot.
            - reverse_at_night is True only for lots that swap Add/Sub in night charts.

    Canon: Paulus Alexandrinus, Introductory Matters (Hellenistic lots);
           Bonatti, Liber Astronomiae (medieval lots)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.lots.PartDefinition",
        "risk": "low",
        "api": {"frozen": ["name", "day_add", "day_sub", "reverse_at_night", "category", "description"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:             str
    day_add:          str
    day_sub:          str
    reverse_at_night: bool
    category:         str
    description:      str = ""


# ---------------------------------------------------------------------------
# Comprehensive parts catalogue  (~430 entries)
# ---------------------------------------------------------------------------

PARTS_DEFINITIONS: list[PartDefinition] = [
    # --- A ---
    PartDefinition("Accomplishment",                    "Sun",           "Jupiter",        False, "modern"),
    PartDefinition("Accusation (Firmicus)",             "Saturn",        "Mars",           False, "hellenistic"),
    PartDefinition("Accusation (Valens)",               "Mars",          "Saturn",         True,  "hellenistic"),
    PartDefinition("Activity (Olympiodorus 1)",         "Venus",         "Jupiter",        True,  "hellenistic"),
    PartDefinition("Activity (Olympiodorus 2)",         "Jupiter",       "Sun",            True,  "hellenistic"),
    PartDefinition("Activity (Rhetorius)",              "Mars",          "Mercury",        True,  "hellenistic,medieval"),
    PartDefinition("Adultery 1",                        "Mars",          "Venus",          True,  "hellenistic"),
    PartDefinition("Adultery 2",                        "Venus",         "Mars",           True,  "hellenistic"),
    PartDefinition("Advancement",                       "Sun",           "Saturn",         False, "modern"),
    PartDefinition("Agriculture",                       "Saturn",        "Venus",          False, "medieval"),
    PartDefinition("Air and Wind",                      "Ruler Mercury", "Mercury",        False, "medieval,weather"),
    PartDefinition("Air and Wind (Mercury in Virgo)",   "Mercury",       "0 Virgo",        False, "medieval,weather"),
    PartDefinition("Air and Wind (Mercury in Gemini)",  "Mercury",       "0 Gemini",       False, "medieval,weather"),
    PartDefinition("Allegiance",                        "Saturn",        "Sun",            False, "modern"),
    PartDefinition("Animals",                           "H12",           "Ruler H12",      False, "medieval"),
    PartDefinition("Appreciation",                      "Venus",         "Sun",            False, "modern"),
    PartDefinition("Apricots",                          "Mars",          "Saturn",         True,  "medieval,commodity"),
    PartDefinition("Aptness, Aloofness",                "Mercury",       "Saturn",         True,  "modern"),
    PartDefinition("Art",                               "Mercury",       "Venus",          True,  "modern"),
    PartDefinition("Assassination",                     "Neptune",       "Uranus",         False, "modern"),
    PartDefinition("Assassination (IGJ)",               "Ruler H12",     "Neptune",        False, "modern"),
    PartDefinition("Association 1",                     "Venus",         "Mercury",        True,  "hellenistic"),
    PartDefinition("Association 2",                     "Venus",         "Jupiter",        False, "hellenistic"),
    PartDefinition("Association 3",                     "Jupiter",       "Mercury",        False, "hellenistic"),
    PartDefinition("Astrology",                         "Mercury",       "Uranus",         False, "modern"),
    PartDefinition("Authority",                         "Sun",           "Mars",           True,  "hellenistic"),
    PartDefinition("Authority & Work",                  "Moon",          "Saturn",         True,  "medieval"),
    PartDefinition("Authority, Aid & Conquering",       "Saturn",        "Sun",            True,  "medieval,mundane"),
    PartDefinition("Authority, Aid & Conquering (Alt)", "Jupiter",       "Sun",            False, "medieval"),

    # --- B ---
    PartDefinition("Barley",                            "Jupiter",       "Moon",           True,  "medieval,commodity"),
    PartDefinition("Basis (Firmicus)",                  "Fortune",       "Spirit",         True,  "hellenistic"),
    PartDefinition("Basis (Valens)",                    "Spirit",        "Fortune",        True,  "hellenistic,medieval"),
    PartDefinition("Basis 2",                           "Mercury",       "Venus",          True,  "hellenistic"),
    PartDefinition("Battle",                            "Moon",          "Mars",           False, "medieval,mundane"),
    PartDefinition("Beans",                             "Mars",          "Saturn",         True,  "medieval,commodity"),
    PartDefinition("Beauty",                            "Venus",         "Sun",            False, "modern"),
    PartDefinition("Behest",                            "Jupiter",       "Neptune",        False, "modern"),
    PartDefinition("Being in a Foreign Land",           "Mars",          "Saturn",         False, "hellenistic"),
    PartDefinition("Being Known Among People",          "Sun",           "Fortune",        True,  "medieval"),
    PartDefinition("Benevolence, Assurance",            "Jupiter",       "Mercury",        False, "modern"),
    PartDefinition("Bequest",                           "Jupiter",       "Uranus",         True,  "modern"),
    PartDefinition("Bereavement",                       "Ruler H12",     "Neptune",        False, "modern"),
    PartDefinition("Bigotry",                           "Uranus",        "Sun",            True,  "modern"),
    PartDefinition("Birth/Pregnancy",                   "Ruler H5",      "H5",             False, "medieval,horary"),
    PartDefinition("Bitter Foods",                      "Saturn",        "Mercury",        True,  "medieval,commodity"),
    PartDefinition("Bitter Purgatives (al-Biruni)",     "Mars",          "Saturn",         True,  "medieval,commodity"),
    PartDefinition("Boy-Lover of a Man",                "Jupiter",       "Venus",          True,  "hellenistic"),
    PartDefinition("Burial",                            "Saturn",        "Moon",           True,  "hellenistic"),
    PartDefinition("Business A",                        "Mars",          "Jupiter",        True,  "hellenistic"),
    PartDefinition("Business B",                        "Saturn",        "Jupiter",        True,  "hellenistic"),
    PartDefinition("Business Partnerships",             "Dsc",           "Ruler H10",      False, "modern"),
    PartDefinition("Business, Buying & Selling",        "Fortune",       "Spirit",         True,  "medieval"),
    PartDefinition("Butter",                            "Venus",         "Sun",            False, "medieval,commodity"),

    # --- C ---
    PartDefinition("Cancer (Disease)",                  "Neptune",       "Jupiter",        False, "modern"),
    PartDefinition("Catastrophe",                       "Uranus",        "Sun",            False, "modern"),
    PartDefinition("Catastrophe (Goldstein-Jacobson)",  "Uranus",        "Saturn",         False, "modern"),
    PartDefinition("Caution",                           "Neptune",       "Saturn",         False, "modern"),
    PartDefinition("Change",                            "Uranus",        "Pluto",          False, "modern"),
    PartDefinition("Charm, Personality",                "Uranus",        "Neptune",        False, "modern"),
    PartDefinition("Chick-peas",                        "Sun",           "Venus",          True,  "medieval,commodity"),
    PartDefinition("Children",                          "Saturn",        "Jupiter",        True,  "hellenistic,medieval"),
    PartDefinition("Children (Firmicus)",               "Venus",         "Mercury",        False, "hellenistic"),
    PartDefinition("Children (Firmicus)(Alt)",          "Mercury",       "Jupiter",        True,  "hellenistic"),
    PartDefinition("Children (Sahl/Hermes)",            "Saturn",        "Mercury",        False, "medieval"),
    PartDefinition("Civil Office",                      "Mercury",       "Jupiter",        False, "medieval"),
    PartDefinition("Clouds",                            "Saturn",        "Mars",           True,  "medieval,weather"),
    PartDefinition("Coincidence",                       "Mars",          "Uranus",         False, "modern"),
    PartDefinition("Cold",                              "Saturn",        "Mercury",        True,  "medieval,weather"),
    PartDefinition("Comfort",                           "Venus",         "Moon",           False, "modern"),
    PartDefinition("Commerce",                          "Mercury",       "Sun",            False, "modern"),
    PartDefinition("Commerce (Jacobson)",               "Mars",          "Sun",            False, "modern"),
    PartDefinition("Communication",                     "Mercury",       "Sun",            False, "modern"),
    PartDefinition("Compulsion",                        "Mercury",       "Spirit",         False, "medieval"),
    PartDefinition("Confidence",                        "Uranus",        "Saturn",         False, "modern"),
    PartDefinition("Conquest",                          "Mars",          "Sun",            False, "medieval,mundane"),
    PartDefinition("Contentions and Contenders",        "Jupiter",       "Mars",           True,  "medieval"),
    PartDefinition("Contentment & Peace",               "Venus",         "Sun",            True,  "modern"),
    PartDefinition("Contract 1",                        "Jupiter",       "Mercury",        True,  "hellenistic"),
    PartDefinition("Contract 2",                        "Jupiter",       "Saturn",         False, "hellenistic"),
    PartDefinition("Controversy",                       "Jupiter",       "Mars",           False, "modern"),
    PartDefinition("Cooperation (Jones)",               "Moon",          "Mercury",        False, "modern"),
    PartDefinition("Cooperation (Louis)",               "Moon",          "Sun",            False, "modern"),
    PartDefinition("Corruptness",                       "Neptune",       "Venus",          True,  "modern"),
    PartDefinition("Cotton",                            "Venus",         "Mercury",        True,  "medieval,commodity"),
    PartDefinition("Courage",                           "Fortune",       "Mars",           True,  "hellenistic,medieval,hermetic"),
    PartDefinition("Courage, Violence & Combat",        "Moon",          "Ruler Asc",      True,  "medieval"),
    PartDefinition("Craft",                             "Moon",          "Mars",           True,  "hellenistic"),
    PartDefinition("Critical Year",                     "Ruler Syzygy",  "Saturn",         False, "hellenistic,medieval"),
    PartDefinition("Cunning, Deception & Stratagems",   "Spirit",        "Mercury",        True,  "medieval"),
    PartDefinition("Curiosity",                         "Moon",          "Mercury",        True,  "modern"),

    # --- D ---
    PartDefinition("Daily Rains",                       "Saturn",        "Sun",            False, "medieval,weather"),
    PartDefinition("Damage",                            "Saturn",        "Mars",           True,  "hellenistic"),
    PartDefinition("Damage (Modern)",                   "Neptune",       "Mars",           False, "modern"),
    PartDefinition("Dates",                             "Venus",         "Sun",            False, "medieval,commodity"),
    PartDefinition("Death",                             "H8",            "Moon",           False, "hellenistic,medieval"),
    PartDefinition("Death (al-Tabari 1)",               "Ruler Asc",     "Ruler H8",       False, "medieval,horary"),
    PartDefinition("Death (al-Tabari 2)",               "Ruler H8",      "H8",             False, "medieval,horary"),
    PartDefinition("Death (Laurentianus)",              "Saturn",        "Moon",           True,  "hellenistic"),
    PartDefinition("Death (Olympiodorus)",              "Moon",          "Saturn",         True,  "hellenistic"),
    PartDefinition("Death (Persian)",                   "Saturn",        "Mars",           True,  "medieval"),
    PartDefinition("Death (Rhetorius)",                 "H8",            "Moon",           False, "hellenistic,medieval"),
    PartDefinition("Death of Brothers",                 "MC",            "Sun",            True,  "medieval"),
    PartDefinition("Death of the Father",               "Jupiter",       "Saturn",         False, "medieval"),
    PartDefinition("Death Point (Emerson)",             "Saturn",        "MC",             False, "modern"),
    PartDefinition("Debt",                              "Saturn",        "Mercury",        False, "hellenistic,medieval"),
    PartDefinition("Debtor",                            "Mercury",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Deceit",                            "Mars",          "Sun",            True,  "hellenistic"),
    PartDefinition("Deceit (Modern)",                   "Venus",         "Neptune",        False, "modern"),
    PartDefinition("Delusion",                          "Neptune",       "Moon",           False, "modern"),
    PartDefinition("Dependence",                        "Jupiter",       "Moon",           False, "modern"),
    PartDefinition("Desire",                            "Venus",         "Jupiter",        True,  "hellenistic"),
    PartDefinition("Desire & Sexual Attraction",        "H5",            "Ruler H5",       False, "modern"),
    PartDefinition("Destiny",                           "Sun",           "Moon",           False, "modern"),
    PartDefinition("Destroyer",                         "Moon",          "Ruler Asc",      True,  "hellenistic,medieval"),
    PartDefinition("Destruction",                       "Mercury",       "Mars",           True,  "hellenistic"),
    PartDefinition("Destruction (Jones)",               "Mars",          "Sun",            False, "modern"),
    PartDefinition("Dignity",                           "Sun",           "Jupiter",        True,  "hellenistic"),
    PartDefinition("Dignity B",                         "Mars",          "Sun",            True,  "hellenistic"),
    PartDefinition("Disappointment",                    "Mars",          "Neptune",        False, "modern"),
    PartDefinition("Discernment & Education",           "Moon",          "Mercury",        True,  "modern"),
    PartDefinition("Discord",                           "Dsc",           "Mars",           False, "medieval"),
    PartDefinition("Disinterest/Boredom",               "Sun",           "Venus",          False, "modern"),
    PartDefinition("Dismissal or Resignation",          "Jupiter",       "Sun",            False, "medieval,horary"),
    PartDefinition("Disputes",                          "Mercury",       "Mars",           False, "modern"),
    PartDefinition("Dissappointment, Endings",          "Mars",          "Venus",          False, "modern"),
    PartDefinition("Dissociation",                      "Moon",          "Mars",           False, "modern"),
    PartDefinition("Distress, Upset",                   "Mars",          "Saturn",         True,  "modern"),
    PartDefinition("Divination",                        "Neptune",       "Mercury",        False, "modern"),
    PartDefinition("Divorce",                           "Venus",         "Dsc",            False, "modern"),
    PartDefinition("Divorce 2",                         "Dsc",           "Saturn",         False, "modern"),
    PartDefinition("Dramatization",                     "Moon",          "Uranus",         False, "modern"),
    PartDefinition("Dreams A",                          "Mercury",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Dreams B",                          "Venus",         "Saturn",         True,  "hellenistic"),
    PartDefinition("Dwelling",                          "Moon",          "Saturn",         True,  "hellenistic"),

    # --- E ---
    PartDefinition("Earth",                             "Jupiter",       "Saturn",         False, "medieval,weather"),
    PartDefinition("Eccentricity",                      "Mercury",       "Uranus",         False, "modern"),
    PartDefinition("Enemies (Ancients/Olympiodorus A)", "Mars",          "Saturn",         True,  "hellenistic,medieval"),
    PartDefinition("Enemies (Firmicus)",                "Mercury",       "Mars",           True,  "hellenistic"),
    PartDefinition("Enemies (Hermes)",                  "H12",           "Ruler H12",      False, "medieval"),
    PartDefinition("Enemies (Laurentianus)",            "Mercury",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Enemies (Olympiodorus B)",          "Mars",          "Sun",            True,  "hellenistic"),
    PartDefinition("Enemies (Olympiodorus C)",          "Mercury",       "Venus",          True,  "hellenistic"),
    PartDefinition("Energy, Sex Drive & Stimulation",   "Pluto",         "Venus",          False, "modern"),
    PartDefinition("Entanglement and Hardship",         "Mercury",       "Saturn",         True,  "medieval"),
    PartDefinition("Entertainment",                     "Uranus",        "Jupiter",        False, "modern"),
    PartDefinition("Eros (Firmicus)",                   "Fortune",       "Spirit",         True,  "hellenistic"),
    PartDefinition("Eros (Hermetic)",                   "Venus",         "Spirit",         True,  "hellenistic,medieval"),
    PartDefinition("Eros (Olympiodorus) A",             "Jupiter",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Eros (Olympiodorus) B",             "Mars",          "Saturn",         True,  "hellenistic"),
    PartDefinition("Eros (Paulus)",                     "Venus",         "Spirit",         False, "hellenistic"),
    PartDefinition("Eros (Valens)",                     "Spirit",        "Fortune",        True,  "hellenistic,medieval"),
    PartDefinition("Estates",                           "Mercury",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Exaltation (Day)",                  "18 Aries",      "Sun",            False, "hellenistic,medieval"),
    PartDefinition("Exaltation (Night)",                "2 Taurus",      "Moon",           False, "hellenistic,medieval"),
    PartDefinition("Exhaustion of Bodies",              "Mars",          "Fortune",        True,  "medieval"),
    PartDefinition("Exile A",                           "Moon",          "Mars",           True,  "hellenistic"),
    PartDefinition("Exile B",                           "Mars",          "Saturn",         False, "hellenistic"),
    PartDefinition("Expected Birth 2",                  "Venus",         "Moon",           False, "modern"),

    # --- F ---
    PartDefinition("Faithfulness",                      "Saturn",        "Mercury",        True,  "modern"),
    PartDefinition("False Love",                        "Neptune",       "Venus",          False, "modern"),
    PartDefinition("Fame",                              "Venus",         "Jupiter",        True,  "hellenistic"),
    PartDefinition("Fame and Reputation",               "Venus",         "Jupiter",        False, "hellenistic"),
    PartDefinition("Fame, Wisdom",                      "Jupiter",       "Sun",            False, "modern"),
    PartDefinition("Family",                            "Jupiter",       "Saturn",         False, "modern"),
    PartDefinition("Farming A",                         "Venus",         "Saturn",         True,  "hellenistic"),
    PartDefinition("Farming B",                         "Venus",         "Jupiter",        True,  "hellenistic"),
    PartDefinition("Fascination",                       "Venus",         "Uranus",         False, "modern"),
    PartDefinition("Fatality",                          "Saturn",        "Sun",            False, "modern"),
    PartDefinition("Father",                            "Saturn",        "Sun",            True,  "hellenistic,medieval"),
    PartDefinition("Father (Alt 1)",                    "Jupiter",       "Mars",           True,  "hellenistic,medieval"),
    PartDefinition("Father (Alt 2)",                    "Jupiter",       "Sun",            True,  "hellenistic,medieval"),
    PartDefinition("Faults and Lusts",                  "Saturn",        "Moon",           False, "hellenistic"),
    PartDefinition("Female Children (Dorotheus)",       "Venus",         "Moon",           True,  "hellenistic,medieval"),
    PartDefinition("Female Children (Valens)",          "Venus",         "Jupiter",        False, "hellenistic"),
    PartDefinition("Finding Lost Objects",              "H4",            "Ruler Asc",      False, "modern"),
    PartDefinition("Fire",                              "Mars",          "Sun",            False, "medieval,weather"),
    PartDefinition("Flax",                              "Venus",         "Mars",           True,  "medieval,commodity"),
    PartDefinition("Foolhardiness",                     "Saturn",        "Uranus",         False, "modern"),
    PartDefinition("Fortune",                           "Moon",          "Sun",            True,  "hellenistic,medieval"),
    PartDefinition("Found Wealth",                      "Venus",         "Mercury",        True,  "medieval"),
    PartDefinition("Fraud",                             "Neptune",       "Mercury",        False, "modern"),
    PartDefinition("Freedmen and Servants",             "Saturn",        "Jupiter",        False, "medieval,horary"),
    PartDefinition("Freedom",                           "Sun",           "Mercury",        True,  "hellenistic"),
    PartDefinition("Friends",                           "Mercury",       "Moon",           True,  "hellenistic,medieval"),
    PartDefinition("Friends (Firmicus)",                "Mercury",       "Jupiter",        True,  "hellenistic"),
    PartDefinition("Friends (Modern 2)",                "Moon",          "Venus",          False, "modern"),
    PartDefinition("Friends (Modern)",                  "Moon",          "Uranus",         True,  "modern"),
    PartDefinition("Friends (Olympiodorus 1) A",        "Venus",         "Mercury",        True,  "hellenistic"),
    PartDefinition("Friends (Olympiodorus 1) B",        "Saturn",        "Jupiter",        True,  "hellenistic"),
    PartDefinition("Friends (Olympiodorus 2)",          "Venus",         "Jupiter",        False, "hellenistic"),

    # --- G ---
    PartDefinition("Gender (of unknown/unborn)",        "Asc",           "Moon",           False, "modern"),
    PartDefinition("Genius",                            "Sun",           "Neptune",        True,  "modern"),
    PartDefinition("Gossip",                            "Mercury",       "Neptune",        False, "modern"),
    PartDefinition("Grandfathers",                      "Saturn",        "Ruler Sun",      True,  "medieval"),
    PartDefinition("Grandfathers (Alt 1)",              "Saturn",        "Sun",            True,  "medieval"),
    PartDefinition("Grandfathers (Alt 2)",              "Saturn",        "0 Leo",          True,  "medieval"),
    PartDefinition("Grapes",                            "Venus",         "Saturn",         True,  "medieval,commodity"),
    PartDefinition("Grief 1A",                          "Mars",          "Saturn",         True,  "hellenistic"),
    PartDefinition("Grief 1B",                          "Sun",           "Saturn",         True,  "hellenistic"),
    PartDefinition("Guidance",                          "Neptune",       "Uranus",         False, "modern"),

    # --- H ---
    PartDefinition("Happiness",                         "Uranus",        "Jupiter",        False, "modern"),
    PartDefinition("Happiness and Wedding",             "Dsc",           "Venus",          False, "hellenistic,medieval"),
    PartDefinition("Heaviness",                         "Saturn",        "Sun",            False, "modern"),
    PartDefinition("Higher Education",                  "H9",            "Mercury",        False, "modern"),
    PartDefinition("Homeland A",                        "Mercury",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Homeland B",                        "Jupiter",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Homeland C",                        "Mars",          "Sun",            True,  "hellenistic"),
    PartDefinition("Homosexuality",                     "Mars",          "Uranus",         False, "modern"),
    PartDefinition("Honey",                             "Sun",           "Moon",           True,  "medieval,commodity"),
    PartDefinition("Hope",                              "Venus",         "Saturn",         True,  "medieval"),

    # --- I ---
    PartDefinition("Identity",                          "Saturn",        "Moon",           False, "modern"),
    PartDefinition("If an Event Will Come About",       "Asc",           "Ruler Dsc",      False, "horary"),
    PartDefinition("If an Outcome Will be Useful",      "Lord of Hour",  "Ruler Asc",      False, "horary"),
    PartDefinition("Illness (Ancients)",                "Mars",          "Mercury",        False, "medieval"),
    PartDefinition("Illness (Dorotheus - Chinese)",     "H6",            "Sun",            False, "medieval"),
    PartDefinition("Illness (Dorotheus)",               "Mars",          "Saturn",         True,  "hellenistic,medieval"),
    PartDefinition("Illness (Laurentianus)",            "Mercury",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Impression",                        "Jupiter",       "Sun",            False, "modern"),
    PartDefinition("Imprisonment (Modern)",             "Neptune",       "Sun",            False, "modern"),
    PartDefinition("Imprisonment A",                    "Sun",           "Saturn",         True,  "hellenistic"),
    PartDefinition("Imprisonment B",                    "Mars",          "Saturn",         True,  "hellenistic"),
    PartDefinition("Imprisonment, Sorrow & Captivity",  "Fortune",       "Neptune",        False, "modern"),
    PartDefinition("Increase",                          "Jupiter",       "Sun",            False, "modern"),
    PartDefinition("Indecency and Lust",                "Venus",         "Moon",           False, "hellenistic"),
    PartDefinition("Indian Peas",                       "Mars",          "Saturn",         False, "medieval,commodity"),
    PartDefinition("Individuality",                     "Sun",           "Uranus",         False, "modern"),
    PartDefinition("Influence",                         "Saturn",        "Moon",           False, "modern"),
    PartDefinition("Inheritance",                       "Jupiter",       "Venus",          False, "modern"),
    PartDefinition("Inheritance 1",                     "Venus",         "Saturn",         True,  "hellenistic"),
    PartDefinition("Inheritance 2",                     "Mercury",       "Jupiter",        True,  "hellenistic"),
    PartDefinition("Initiative",                        "Sun",           "Mars",           True,  "modern"),
    PartDefinition("Injury 1",                          "Saturn",        "Mars",           True,  "hellenistic"),
    PartDefinition("Injury 2",                          "Mars",          "Saturn",         False, "hellenistic"),
    PartDefinition("Injury 3",                          "Mars",          "Saturn",         True,  "hellenistic"),
    PartDefinition("Injury to Business",                "Fortune",       "Ruler Asc",      False, "medieval,horary"),
    PartDefinition("Insincerity",                       "Moon",          "Neptune",        False, "modern"),
    PartDefinition("Inspiration",                       "Neptune",       "Uranus",         False, "modern"),
    PartDefinition("Integrity",                         "Mercury",       "Jupiter",        False, "modern"),
    PartDefinition("Intellectuality",                   "Sun",           "Uranus",         False, "modern"),
    PartDefinition("Intrusion",                         "Mercury",       "Neptune",        False, "modern"),
    PartDefinition("Iron",                              "Saturn",        "Mars",           True,  "medieval,commodity"),

    # --- J ---
    PartDefinition("Job & Authority",                   "MC",            "Sun",            False, "medieval"),
    PartDefinition("Judgment 1A",                       "Jupiter",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Judgment 1B",                       "Mars",          "Saturn",         True,  "hellenistic"),
    PartDefinition("Judgment 1C",                       "Mercury",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Judgment 2",                        "Jupiter",       "Mars",           True,  "hellenistic"),

    # --- K ---
    PartDefinition("Killing",                           "Mars",          "Moon",           False, "medieval,horary"),
    PartDefinition("Kings, Rulers",                     "Moon",          "Mercury",        False, "modern"),
    PartDefinition("Kinship",                           "Jupiter",       "Mercury",        True,  "hellenistic"),
    PartDefinition("Knowledge",                         "Jupiter",       "Moon",           True,  "medieval,mundane"),
    PartDefinition("Knowledge & Meditation",            "Jupiter",       "Saturn",         True,  "medieval"),
    PartDefinition("Knowledge & Meditation (al-Qabisi)","Jupiter",       "Saturn",         False, "medieval"),

    # --- L ---
    PartDefinition("Labor",                             "Saturn",        "Venus",          False, "modern"),
    PartDefinition("Lawsuit",                           "Mercury",       "Mars",           False, "medieval,horary"),
    PartDefinition("Legalizing Contracts/Marriage",     "H3",            "Venus",          False, "modern"),
    PartDefinition("Lentils",                           "Saturn",        "Mars",           True,  "medieval,commodity"),
    PartDefinition("Life (Female)",                     "Moon",          "Prenatal Full Moon", False, "modern"),
    PartDefinition("Life (Male)",                       "Moon",          "Prenatal New Moon",  False, "modern"),
    PartDefinition("Life 1",                            "Saturn",        "Jupiter",        True,  "hellenistic,medieval"),
    PartDefinition("Life 2a",                           "Venus",         "Moon",           True,  "hellenistic"),
    PartDefinition("Life 2b",                           "Venus",         "Saturn",         False, "hellenistic"),
    PartDefinition("Life 2c",                           "Saturn",        "Venus",          False, "hellenistic"),
    PartDefinition("Life 2d",                           "Venus",         "Fortune",        False, "hellenistic"),
    PartDefinition("Life or Death of Absent",           "Mars",          "Moon",           False, "medieval,horary"),
    PartDefinition("Lineage",                           "Mars",          "Saturn",         True,  "medieval"),
    PartDefinition("Livelihood (Dorotheus)",            "H2",            "Ruler H2",       False, "hellenistic,medieval"),
    PartDefinition("Livelihood 2",                      "Saturn",        "Venus",          True,  "hellenistic"),
    PartDefinition("Livelihood 3",                      "Asc",           "Sun",            False, "hellenistic"),
    PartDefinition("Livelihood 4",                      "Moon",          "Venus",          True,  "hellenistic"),
    PartDefinition("Loans",                             "Saturn",        "Mercury",        True,  "hellenistic"),
    PartDefinition("Logic & Reason",                    "Mars",          "Mercury",        True,  "medieval"),
    PartDefinition("Loneliness",                        "Jupiter",       "Venus",          False, "modern"),
    PartDefinition("Longevity",                         "Moon",          "Jupiter",        True,  "medieval"),
    PartDefinition("Lords and Masters",                 "Saturn",        "Jupiter",        False, "medieval,horary"),
    PartDefinition("Lost Animal",                       "Mars",          "Sun",            False, "medieval,horary"),
    PartDefinition("Love (Modern)",                     "Venus",         "Sun",            False, "modern"),
    PartDefinition("Love & Entertainment",              "Venus",         "Sun",            True,  "modern"),
    PartDefinition("Love & Marriage (Louis)",           "Jupiter",       "Venus",          True,  "modern"),
    PartDefinition("Love & Marriage (Modern)",          "Venus",         "Jupiter",        False, "modern"),
    PartDefinition("Lover of a Woman",                  "Moon",          "Jupiter",        True,  "hellenistic"),
    PartDefinition("Lovers",                            "Venus",         "Jupiter",        False, "medieval"),
    PartDefinition("Lovers (Modern)",                   "Venus",         "H5",             False, "modern"),
    PartDefinition("Luck",                              "Moon",          "Jupiter",        False, "modern"),

    # --- M ---
    PartDefinition("Madness",                           "Neptune",       "Sun",            False, "modern"),
    PartDefinition("Male Children (Dorotheus - Chinese)","Jupiter",      "Sun",            False, "medieval"),
    PartDefinition("Male Children (Dorotheus)",         "Sun",           "Jupiter",        False, "hellenistic"),
    PartDefinition("Male Children (Hermes)",            "Jupiter",       "Moon",           True,  "hellenistic,medieval"),
    PartDefinition("Male Children (Persian/Theophilus)","Saturn",        "Moon",           True,  "medieval"),
    PartDefinition("Male Children (Valens)",            "Mercury",       "Jupiter",        False, "hellenistic"),
    PartDefinition("Manual Workers & Commercial Activities","Venus",     "Mercury",        True,  "medieval"),
    PartDefinition("Marriage (Firmicus)",               "Moon",          "Sun",            False, "hellenistic,medieval"),
    PartDefinition("Marriage (Horary)",                 "Ruler Dsc",     "Dsc",            False, "medieval,horary"),
    PartDefinition("Marriage (Men, Dorotheus)",         "Venus",         "Saturn",         True,  "hellenistic,medieval"),
    PartDefinition("Marriage (Men, Valens)",            "Venus",         "Sun",            False, "hellenistic,medieval"),
    PartDefinition("Marriage (Valens)",                 "Venus",         "Jupiter",        True,  "hellenistic,medieval"),
    PartDefinition("Marriage (Women, Dorotheus)",       "Saturn",        "Venus",          True,  "hellenistic,medieval"),
    PartDefinition("Marriage (Women, Valens)",          "Mars",          "Moon",           False, "hellenistic,medieval"),
    PartDefinition("Meat",                              "Jupiter",       "Moon",           True,  "medieval,commodity"),
    PartDefinition("Melons",                            "Saturn",        "Mercury",        False, "medieval,commodity"),
    PartDefinition("Memory",                            "Mars",          "Moon",           False, "modern"),
    PartDefinition("Military Expedition",               "Moon",          "Saturn",         True,  "hellenistic,medieval,mundane"),
    PartDefinition("Military Service (Firmicus)",       "Sun",           "Mars",           True,  "hellenistic"),
    PartDefinition("Military Service (Laurentianus)",   "Mars",          "Mercury",        True,  "hellenistic"),
    PartDefinition("Military Service (Olympiodorus 1)", "Jupiter",       "Mars",           True,  "hellenistic"),
    PartDefinition("Mind, Captivity",                   "H3",            "Mercury",        False, "modern"),
    PartDefinition("Mind, Understanding (Female)",      "Moon",          "Venus",          True,  "modern"),
    PartDefinition("Mind, Understanding (Male)",        "Mars",          "Mercury",        False, "modern"),
    PartDefinition("Miracles",                          "Sun",           "Pluto",          False, "modern"),
    PartDefinition("Misinterpretation",                 "Uranus",        "Moon",           False, "modern"),
    PartDefinition("Mistress of a Man",                 "Jupiter",       "Moon",           True,  "hellenistic"),
    PartDefinition("Mistress of a Woman",               "Moon",          "Venus",          True,  "hellenistic"),
    PartDefinition("Misunderstanding",                  "Neptune",       "Mars",           False, "modern"),
    PartDefinition("Mother",                            "Moon",          "Venus",          True,  "hellenistic,medieval"),
    PartDefinition("Mother (Modern)",                   "Moon",          "Saturn",         False, "modern"),
    PartDefinition("Mother & Family",                   "Jupiter",       "Venus",          False, "modern"),

    # --- N ---
    PartDefinition("Nature of the Planets (Moon)",      "15 Cancer",     "Moon",           False, "medieval,mundane"),
    PartDefinition("Nature of the Planets (Sun)",       "15 Leo",        "Sun",            False, "medieval,mundane"),
    PartDefinition("Navigation (Hellenistic)",          "15 Cancer",     "Saturn",         True,  "hellenistic"),
    PartDefinition("Navigation (Medieval)",             "29 Cancer",     "Saturn",         True,  "medieval"),
    PartDefinition("Necessity (Firmicus)",              "Spirit",        "Fortune",        True,  "hellenistic"),
    PartDefinition("Necessity (Hermetic)",              "Fortune",       "Mercury",        True,  "hellenistic,medieval"),
    PartDefinition("Necessity (Paulus)",                "Mercury",       "Fortune",        False, "hellenistic"),
    PartDefinition("Necessity (Persian)",               "Mercury",       "Eros (Valens)",  True,  "medieval"),
    PartDefinition("Necessity (Valens)",                "Fortune",       "Spirit",         True,  "hellenistic,medieval"),
    PartDefinition("Necessity & Hindering of Needs",    "H3",            "Mars",           False, "medieval"),
    PartDefinition("Need & Desire",                     "Mars",          "Saturn",         False, "medieval"),
    PartDefinition("Negotiation",                       "Mars",          "Jupiter",        False, "modern"),
    PartDefinition("Nemesis",                           "Fortune",       "Saturn",         True,  "hellenistic,medieval,hermetic"),
    PartDefinition("Nemesis (Firmicus)",                "Fortune",       "Moon",           True,  "hellenistic"),
    PartDefinition("Noxious Place",                     "Mars",          "Saturn",         True,  "hellenistic,medieval"),
    PartDefinition("Noxious Place (Alt)",               "Mars",          "Saturn",         True,  "hellenistic,medieval"),
    PartDefinition("Number of Siblings",                "Saturn",        "Mercury",        False, "medieval"),
    PartDefinition("Nuts (al-Biruni)",                  "Venus",         "Mars",           True,  "medieval,commodity"),
    PartDefinition("Nuts (al-Qabisi Latin)",            "Mars",          "Mercury",        False, "medieval,commodity"),

    # --- O ---
    PartDefinition("Occultism",                         "Neptune",       "Uranus",         False, "modern"),
    PartDefinition("Office",                            "H10",           "Ruler H10",      False, "medieval"),
    PartDefinition("Office & Carrying Out Orders",      "Saturn",        "Sun",            False, "medieval"),
    PartDefinition("Office & King",                     "MC",            "Jupiter",        False, "medieval,horary"),
    PartDefinition("Offspring",                         "Moon",          "Venus",          False, "modern"),
    PartDefinition("Oil",                               "Moon",          "Mars",           True,  "medieval,commodity"),
    PartDefinition("Olives",                            "Moon",          "Mercury",        True,  "medieval,commodity"),
    PartDefinition("Onions",                            "Mars",          "Saturn",         True,  "medieval,commodity"),
    PartDefinition("Opportunity",                       "Sun",           "Saturn",         True,  "hellenistic"),
    PartDefinition("Organization",                      "Pluto",         "Sun",            False, "modern"),
    PartDefinition("Originality",                       "Uranus",        "Mercury",        False, "modern"),
    PartDefinition("Ostracism & Loss",                  "Uranus",        "Sun",            True,  "modern"),
    PartDefinition("Outcomes",                          "Ruler Asc",     "Lord of Hour",   False, "medieval,horary"),
    PartDefinition("Outcomes of Affairs",               "Ruler Syzygy",  "Saturn",         False, "medieval"),

    # --- P ---
    PartDefinition("Parents",                           "Moon",          "Sun",            True,  "hellenistic"),
    PartDefinition("Passion",                           "Mars",          "Sun",            False, "modern"),
    PartDefinition("Passion, Emotion & Affection",      "Mars",          "Venus",          False, "modern"),
    PartDefinition("Peace Among Soldiers",              "Mercury",       "Moon",           False, "medieval,horary,mundane"),
    PartDefinition("Perversion",                        "Venus",         "Uranus",         False, "modern"),
    PartDefinition("Play, Activity, Rapid Change",      "Venus",         "Mars",           True,  "modern"),
    PartDefinition("Plenty & Abundance of Good",        "Mercury",       "Moon",           False, "medieval"),
    PartDefinition("Poisons",                           "Neptune",       "North Node",     False, "medieval,commodity"),
    PartDefinition("Popularity (Jones)",                "Mars",          "Neptune",        False, "modern"),
    PartDefinition("Popularity (Louis)",                "Venus",         "Pluto",          False, "modern"),
    PartDefinition("Power",                             "Saturn",        "Sun",            True,  "hellenistic"),
    PartDefinition("Prejudice",                         "Mercury",       "Moon",           False, "modern"),
    PartDefinition("Prisoners (Day)",                   "Sun",           "Ruler Sun",      False, "medieval"),
    PartDefinition("Prisoners (Night)",                 "Moon",          "Ruler Moon",     False, "medieval"),
    PartDefinition("Property Management",               "Venus",         "Sun",            False, "modern"),
    PartDefinition("Prosperity",                        "Dsc",           "Sun",            False, "medieval,mundane"),
    PartDefinition("Pulse",                             "Mercury",       "Venus",          True,  "medieval,commodity"),
    PartDefinition("Pungent/Spicy Foods",               "Saturn",        "Mars",           True,  "medieval,commodity"),
    PartDefinition("Punishment (Hellenistic)",          "Saturn",        "Mercury",        True,  "hellenistic"),
    PartDefinition("Punishment (Medieval)",             "Sun",           "Mars",           True,  "medieval"),
    PartDefinition("Purchase 1A",                       "Mercury",       "Venus",          True,  "hellenistic"),
    PartDefinition("Purchase 1B",                       "Venus",         "Mercury",        True,  "hellenistic"),
    PartDefinition("Purchase 2A",                       "Venus",         "Mars",           True,  "hellenistic"),
    PartDefinition("Purchase 2B",                       "Mars",          "Venus",          True,  "hellenistic"),
    PartDefinition("Purgative & Salty Medicines",       "Moon",          "Mars",           False, "medieval,commodity"),
    PartDefinition("Purgative & Sour Medicines",        "Jupiter",       "Saturn",         True,  "medieval,commodity"),
    PartDefinition("Purgative & Sweet Medicines",       "Moon",          "Sun",            False, "medieval,commodity"),
    PartDefinition("Purgatives (al-Biruni)",            "Saturn",        "Mercury",        True,  "medieval,commodity"),

    # --- R ---
    PartDefinition("Race & Race Consciousness",         "Moon",          "Pluto",          False, "modern"),
    PartDefinition("Radical Change",                    "Pluto",         "Uranus",         False, "modern"),
    PartDefinition("Rain (Annual)",                     "Venus",         "Moon",           True,  "medieval,weather"),
    PartDefinition("Rain (Ibn Ezra)",                   "Moon",          "New Moon",       True,  "medieval,weather"),
    PartDefinition("Real Estate (al-Tabari)",           "Saturn",        "Ruler H4",       True,  "medieval,horary"),
    PartDefinition("Real Estate (Hermes)",              "Moon",          "Saturn",         False, "medieval"),
    PartDefinition("Real Estate (Persian)",             "Jupiter",       "Mercury",        True,  "medieval"),
    PartDefinition("Reason & Depth of Thought",         "Moon",          "Saturn",         True,  "medieval"),
    PartDefinition("Reincarnation",                     "Saturn",        "Jupiter",        False, "modern"),
    PartDefinition("Release, Luck",                     "Mercury",       "Mars",           False, "modern"),
    PartDefinition("Releaser",                          "Moon",          "Syzygy",         False, "hellenistic,medieval"),
    PartDefinition("Religion/Piety",                    "Mercury",       "Moon",           True,  "medieval"),
    PartDefinition("Repression",                        "Saturn",        "Pluto",          False, "modern"),
    PartDefinition("Revelation",                        "Moon",          "Neptune",        True,  "modern"),
    PartDefinition("Reward 1",                          "Jupiter",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Reward 2A",                         "Venus",         "Mercury",        True,  "hellenistic"),
    PartDefinition("Reward 2B",                         "Mercury",       "Venus",          True,  "hellenistic"),
    PartDefinition("Reward 3",                          "IC",            "Ruler IC",       False, "hellenistic"),
    PartDefinition("Rice",                              "Saturn",        "Jupiter",        True,  "medieval,commodity"),
    PartDefinition("Rice & Millet",                     "Venus",         "Jupiter",        True,  "medieval,commodity"),
    PartDefinition("Royal Lot (al-Tabari)",             "Jupiter",       "Sun",            True,  "medieval,horary"),
    PartDefinition("Royal Lot (Theophilus)",            "Moon",          "Sun",            False, "medieval,mundane"),
    PartDefinition("Rulership & Authority 1",           "Moon",          "Mars",           True,  "hellenistic,medieval"),
    PartDefinition("Rulership 1",                       "Venus",         "Jupiter",        True,  "hellenistic"),
    PartDefinition("Rulership 2",                       "Venus",         "Saturn",         True,  "hellenistic"),
    PartDefinition("Rumors",                            "Ruler Asc",     "Lord of Hour",   False, "medieval,horary"),
    PartDefinition("Rumors, True or False",             "Moon",          "Mercury",        True,  "medieval,horary"),

    # --- S ---
    PartDefinition("Sale 1",                            "Moon",          "Mercury",        True,  "hellenistic"),
    PartDefinition("Sale 2",                            "Mars",          "Venus",          True,  "hellenistic"),
    PartDefinition("Salt",                              "Mars",          "Moon",           True,  "medieval,commodity"),
    PartDefinition("Salty Things",                      "Moon",          "Mars",           False, "medieval,commodity"),
    PartDefinition("Secret Enemies",                    "Moon",          "Saturn",         False, "modern"),
    PartDefinition("Secrets",                           "H10",           "Ruler Asc",      False, "medieval,horary"),
    PartDefinition("Security",                          "Venus",         "Mercury",        False, "modern"),
    PartDefinition("Self-Undoing",                      "H12",           "Neptune",        False, "modern"),
    PartDefinition("Sensitivity",                       "Mercury",       "Jupiter",        False, "modern"),
    PartDefinition("Sentiment",                         "Venus",         "Jupiter",        False, "modern"),
    PartDefinition("Sesame 1",                          "Jupiter",       "Saturn",         False, "medieval,commodity"),
    PartDefinition("Sesame 2",                          "Venus",         "Saturn",         False, "medieval,commodity"),
    PartDefinition("Ship-Owning",                       "Mercury",       "Saturn",         True,  "hellenistic"),
    PartDefinition("Short Journeys",                    "H3",            "Ruler H3",       False, "modern"),
    PartDefinition("Siblings",                          "Jupiter",       "Saturn",         True,  "hellenistic,medieval"),
    PartDefinition("Siblings (Firmicus)",               "Sun",           "Mercury",        False, "hellenistic"),
    PartDefinition("Siblings (Persian)",                "Mars",          "Ruler Asc",      False, "medieval"),
    PartDefinition("Silk",                              "Venus",         "Mercury",        True,  "medieval,commodity"),
    PartDefinition("Sisters",                           "Saturn",        "Venus",          False, "medieval"),
    PartDefinition("Slander",                           "Saturn",        "Neptune",        False, "modern"),
    PartDefinition("Slaves (Dorotheus)",                "Moon",          "Mercury",        True,  "hellenistic,medieval"),
    PartDefinition("Slaves (Hephaistio)",               "Fortune",       "Mercury",        True,  "hellenistic,medieval"),
    PartDefinition("Slaves 3",                          "Moon",          "Mars",           True,  "hellenistic"),
    PartDefinition("Slaves 4A",                         "Mercury",       "Mars",           True,  "hellenistic"),
    PartDefinition("Slaves 4B",                         "Mercury",       "Sun",            False, "hellenistic"),
    PartDefinition("Siblings (Number)",                 "Jupiter",       "Mercury",        False, "hellenistic,medieval"),
    PartDefinition("Slyness",                           "Neptune",       "Pluto",          False, "modern"),
    PartDefinition("Soldiers & Policemen",              "Saturn",        "Mars",           True,  "medieval"),
    PartDefinition("Sons",                              "Moon",          "Sun",            False, "modern"),
    PartDefinition("Sons-in-Law",                       "Venus",         "Saturn",         False, "medieval"),
    PartDefinition("Soul's Freedom",                    "Sun",           "Mercury",        True,  "medieval"),
    PartDefinition("Sour Foods",                        "Mars",          "Saturn",         False, "medieval,commodity"),
    PartDefinition("Sowing",                            "Mars",          "Sun",            True,  "hellenistic"),
    PartDefinition("Speculation 1",                     "H5",            "Jupiter",        True,  "modern"),
    PartDefinition("Speculation 2",                     "Jupiter",       "Neptune",        False, "modern"),
    PartDefinition("Spirit",                            "Sun",           "Moon",           True,  "hellenistic,medieval"),
    PartDefinition("Stability",                         "Saturn",        "Mercury",        True,  "modern"),
    PartDefinition("Strength",                          "MC",            "Sun",            True,  "hellenistic"),
    PartDefinition("Strength of the Body",              "Jupiter",       "Moon",           False, "hellenistic"),
    PartDefinition("Substance and Possessions",         "Jupiter",       "Mercury",        False, "hellenistic"),
    PartDefinition("Success",                           "Jupiter",       "Fortune",        True,  "medieval,mundane"),
    PartDefinition("Success in Investment",             "Venus",         "Saturn",         False, "modern"),
    PartDefinition("Successful Issue",                  "Jupiter",       "Sun",            False, "medieval,horary"),
    PartDefinition("Sudden Luck",                       "Jupiter",       "Uranus",         False, "modern"),
    PartDefinition("Sudden Parting",                    "Saturn",        "Uranus",         False, "modern"),
    PartDefinition("Suffering",                         "Fortune",       "Spirit",         False, "medieval"),
    PartDefinition("Sugar (al-Biruni)",                 "Mercury",       "Venus",          True,  "medieval,commodity"),
    PartDefinition("Sugar (al-Qabisi Latin)",           "Venus",         "Mercury",        False, "medieval,commodity"),
    PartDefinition("Suicide 1",                         "H8",            "Neptune",        False, "modern"),
    PartDefinition("Suicide 2",                         "Jupiter",       "H12",            False, "modern"),
    PartDefinition("Suicide 3",                         "Jupiter",       "Neptune",        False, "modern"),
    PartDefinition("Surgery & Accident",                "Saturn",        "Mars",           True,  "modern"),
    PartDefinition("Surprise",                          "Mars",          "Uranus",         False, "modern"),
    PartDefinition("Sweet Foods",                       "Venus",         "Sun",            True,  "medieval,commodity"),

    # --- T ---
    PartDefinition("Tales, Knowledge of Rumors",        "Jupiter",       "Sun",            True,  "medieval"),
    PartDefinition("Temperament",                       "Sun",           "Mercury",        False, "modern"),
    PartDefinition("The Creditor",                      "Mercury",       "Saturn",         False, "hellenistic"),
    PartDefinition("The Fugitive",                      "Mars",          "Mercury",        True,  "hellenistic"),
    PartDefinition("The Husband",                       "Venus",         "Mars",           True,  "hellenistic"),
    PartDefinition("The King (Theophilus)",             "Leo",           "Moon",           False, "medieval,mundane"),
    PartDefinition("The Master",                        "Sun",           "Venus",          True,  "hellenistic"),
    PartDefinition("The Month",                         "Cancer",        "Sun",            False, "medieval,mundane"),
    PartDefinition("The Praised & Commended",           "Venus",         "Jupiter",        True,  "medieval"),
    PartDefinition("Theft (Olympiodorus)",              "Mars",          "Mercury",        True,  "hellenistic"),
    PartDefinition("Theft (Valens)",                    "Mars",          "Mercury",        True,  "hellenistic"),
    PartDefinition("Those Honored & Known Among People","Sun",           "Mercury",        False, "medieval"),
    PartDefinition("Those Suddenly Elevated",           "Fortune",       "Saturn",         True,  "medieval"),
    PartDefinition("Time for Action",                   "Jupiter",       "Sun",            False, "medieval,horary"),
    PartDefinition("Time Occupied by Action",           "Saturn",        "Sun",            False, "medieval,horary"),
    PartDefinition("Time of Attainment",                "Ruler H10",     "Lord of Hour",   True,  "medieval,horary"),
    PartDefinition("Time of Children",                  "Jupiter",       "Mars",           False, "hellenistic,medieval"),
    PartDefinition("Timidity",                          "Saturn",        "Neptune",        False, "modern"),
    PartDefinition("Torture",                           "Saturn",        "Moon",           False, "medieval,horary"),
    PartDefinition("Transformation",                    "Ruler H4",      "Dsc",            False, "modern"),
    PartDefinition("Travel",                            "H9",            "Ruler H9",       False, "hellenistic,medieval"),
    PartDefinition("Travel (Firmicus)",                 "Mars",          "Sun",            False, "hellenistic,medieval"),
    PartDefinition("Travel (Modern)",                   "Mercury",       "Moon",           False, "modern"),
    PartDefinition("Travel by Air (Louis)",             "H9",            "Uranus",         False, "modern"),
    PartDefinition("Treachery",                         "Neptune",       "Sun",            False, "modern"),

    # --- U ---
    PartDefinition("Underground Things A",              "Saturn",        "Venus",          True,  "hellenistic"),
    PartDefinition("Underground Things B",              "Mars",          "Venus",          False, "hellenistic"),
    PartDefinition("Underground Things C",              "Venus",         "Mars",           True,  "hellenistic"),
    PartDefinition("Undertaking Some Effort",           "Moon",          "Saturn",         False, "general"),
    PartDefinition("Unpreparedness",                    "Uranus",        "Mars",           False, "modern"),
    PartDefinition("Unusual Events",                    "Uranus",        "Moon",           False, "modern"),

    # --- V ---
    PartDefinition("Vanity",                            "Venus",         "Neptune",        False, "modern"),
    PartDefinition("Venture",                           "Mercury",       "Venus",          False, "modern"),
    PartDefinition("Victory",                           "Jupiter",       "Spirit",         True,  "hellenistic,medieval,hermetic,mundane"),
    PartDefinition("Victory (Olympiodorus)",            "Mars",          "Venus",          True,  "hellenistic"),
    PartDefinition("Visitation",                        "Neptune",       "Jupiter",        False, "modern"),
    PartDefinition("Vitality",                          "Mercury",       "Sun",            False, "modern"),
    PartDefinition("Vocation & Status",                 "Moon",          "Sun",            False, "modern"),

    # --- W ---
    PartDefinition("War (al-Tabari)",                   "Moon",          "Mars",           False, "medieval,horary"),
    PartDefinition("Waste & Extravagance",              "Jupiter",       "Mars",           False, "modern"),
    PartDefinition("Wastefulness",                      "Uranus",        "Venus",          False, "modern"),
    PartDefinition("Water (Commodity)",                 "Venus",         "Moon",           True,  "medieval,commodity"),
    PartDefinition("Water (Element)",                   "Venus",         "Moon",           False, "medieval,weather"),
    PartDefinition("Watermelons (al-Biruni)",           "Mercury",       "Jupiter",        True,  "medieval,commodity"),
    PartDefinition("Waters",                            "Saturn",        "Venus",          False, "hellenistic"),
    PartDefinition("Wealth A",                          "Sun",           "Jupiter",        True,  "hellenistic"),
    PartDefinition("Wealth B",                          "Sun",           "Saturn",         True,  "hellenistic"),
    PartDefinition("Wedding",                           "Moon",          "Sun",            False, "hellenistic,medieval"),
    PartDefinition("Wheat",                             "Mars",          "Sun",            False, "medieval,commodity"),
    PartDefinition("Wheat (al-Biruni)",                 "Jupiter",       "Sun",            True,  "medieval,commodity"),
    PartDefinition("Whether Someone's Rule Will Come to Pass","MC",      "Sun",            False, "medieval,mundane"),
    PartDefinition("Widowhood",                         "Vindemiatrix",  "Neptune",        False, "modern"),
    PartDefinition("Woman's Abstinence",                "Venus",         "Moon",           False, "medieval"),
    PartDefinition("Work of Truth",                     "Mars",          "Mercury",        True,  "medieval"),
    PartDefinition("Work Which Must be Done",           "Jupiter",       "Sun",            True,  "medieval"),
]

_CATEGORY_ORDER = {
    "hellenistic": 0, "medieval": 1, "hermetic": 2,
    "traditional": 3, "modern": 4, "horary": 5, "mundane": 6,
    "commodity": 7, "weather": 8, "general": 9,
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

class LotReferenceKind(StrEnum):
    """Typed classification of how a lot ingredient reference was resolved."""

    PLANET = "planet"
    PLANET_ALIAS = "planet_alias"
    ANGLE = "angle"
    HOUSE_CUSP = "house_cusp"
    FIXED_DEGREE = "fixed_degree"
    EXTERNAL = "external"
    DERIVED_LOT = "derived_lot"
    HOUSE_RULER = "house_ruler"
    ANGLE_RULER_ALIAS = "angle_ruler_alias"
    PLANET_RULER = "planet_ruler"
    SYZYGY_RULER = "syzygy_ruler"


class LotReversalKind(StrEnum):
    """Typed classification of day/night reversal state for a computed lot."""

    DIRECT = "direct"
    NIGHT_REVERSIBLE = "night_reversible"
    NIGHT_REVERSED = "night_reversed"


class LotsReferenceFailureMode(StrEnum):
    """Policy for unresolved lot ingredient references."""

    SKIP = "skip"
    RAISE = "raise"


class LotDependencyRole(StrEnum):
    """Typed role of a dependency within a lot formula."""

    ADD_OPERAND = "add_operand"
    SUB_OPERAND = "sub_operand"


class LotConditionState(StrEnum):
    """Structural condition state for one computed lot."""

    DIRECT = "direct"
    MIXED = "mixed"
    INDIRECT = "indirect"


class LotConditionNetworkEdgeMode(StrEnum):
    """Visibility mode for one directed inter-lot dependency edge."""

    UNILATERAL = "unilateral"
    RECIPROCAL = "reciprocal"


@dataclass(slots=True)
class LotChartConditionProfile:
    """
    Chart-wide condition profile derived from per-part lot condition profiles.

    This is a backend aggregation layer only. It consumes existing
    LotConditionProfile results and does not recompute lot doctrine.
    """

    profiles: list[LotConditionProfile] = field(default_factory=list)
    direct_count: int = 0
    mixed_count: int = 0
    indirect_count: int = 0
    direct_dependency_total: int = 0
    indirect_dependency_total: int = 0
    inter_lot_dependency_total: int = 0
    external_dependency_total: int = 0
    strongest_parts: list[str] = field(default_factory=list)
    weakest_parts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        direct = sum(1 for profile in self.profiles if profile.state is LotConditionState.DIRECT)
        mixed = sum(1 for profile in self.profiles if profile.state is LotConditionState.MIXED)
        indirect = sum(1 for profile in self.profiles if profile.state is LotConditionState.INDIRECT)
        if (self.direct_count, self.mixed_count, self.indirect_count) != (direct, mixed, indirect):
            raise ValueError("LotChartConditionProfile invariant failed: state counts must match profile states")

        direct_total = sum(profile.direct_dependency_count for profile in self.profiles)
        indirect_total = sum(profile.indirect_dependency_count for profile in self.profiles)
        inter_lot_total = sum(profile.inter_lot_dependency_count for profile in self.profiles)
        external_total = sum(profile.external_dependency_count for profile in self.profiles)
        if (self.direct_dependency_total, self.indirect_dependency_total) != (direct_total, indirect_total):
            raise ValueError("LotChartConditionProfile invariant failed: direct/indirect totals must match profile totals")
        if self.inter_lot_dependency_total != inter_lot_total:
            raise ValueError("LotChartConditionProfile invariant failed: inter_lot total must match profile totals")
        if self.external_dependency_total != external_total:
            raise ValueError("LotChartConditionProfile invariant failed: external total must match profile totals")

        ordered_names = [profile.part_name for profile in sorted(self.profiles, key=lambda profile: (profile.primary_category, profile.part_name))]
        if [profile.part_name for profile in self.profiles] != ordered_names:
            raise ValueError("LotChartConditionProfile invariant failed: profiles must be in deterministic order")
        def strongest_key(profile: LotConditionProfile) -> tuple[int, int, int, str]:
            return (
                {
                    LotConditionState.DIRECT: 0,
                    LotConditionState.MIXED: 1,
                    LotConditionState.INDIRECT: 2,
                }[profile.state],
                -profile.direct_dependency_count,
                profile.indirect_dependency_count,
                profile.part_name,
            )

        def weakest_key(profile: LotConditionProfile) -> tuple[int, int, int, str]:
            return (
                {
                    LotConditionState.INDIRECT: 0,
                    LotConditionState.MIXED: 1,
                    LotConditionState.DIRECT: 2,
                }[profile.state],
                -profile.indirect_dependency_count,
                profile.direct_dependency_count,
                profile.part_name,
            )

        if self.profiles:
            strongest_rank = min(strongest_key(profile) for profile in self.profiles)
            expected_strongest = sorted(
                profile.part_name for profile in self.profiles if strongest_key(profile) == strongest_rank
            )
            weakest_profile = min(self.profiles, key=weakest_key)
            expected_weakest = sorted(
                profile.part_name
                for profile in self.profiles
                if (
                    profile.state is weakest_profile.state
                    and profile.indirect_dependency_count == weakest_profile.indirect_dependency_count
                    and profile.direct_dependency_count == weakest_profile.direct_dependency_count
                )
            )
        else:
            expected_strongest = []
            expected_weakest = []
        if self.strongest_parts != expected_strongest:
            raise ValueError("LotChartConditionProfile invariant failed: strongest_parts must match derived ranking")
        if self.weakest_parts != expected_weakest:
            raise ValueError("LotChartConditionProfile invariant failed: weakest_parts must match derived ranking")

    @property
    def profile_count(self) -> int:
        """Return the number of condition profiles aggregated."""

        return len(self.profiles)

    @property
    def strongest_count(self) -> int:
        """Return the number of structurally strongest lots in the profile."""

        return len(self.strongest_parts)

    @property
    def weakest_count(self) -> int:
        """Return the number of structurally weakest lots in the profile."""

        return len(self.weakest_parts)


@dataclass(slots=True)
class LotConditionNetworkNode:
    """
    Node in the derived lot dependency/condition network.

    This is a backend inspectability layer only. It consumes existing
    LotConditionProfile truth and admitted inter-lot dependencies.
    """

    part_name: str
    condition_state: LotConditionState
    outgoing_count: int = 0
    incoming_count: int = 0
    reciprocal_count: int = 0

    def __post_init__(self) -> None:
        if self.reciprocal_count > min(self.outgoing_count, self.incoming_count):
            raise ValueError("LotConditionNetworkNode invariant failed: reciprocal_count cannot exceed incoming/outgoing counts")

    @property
    def degree_count(self) -> int:
        """Return the direct degree count for this node."""

        return self.outgoing_count + self.incoming_count

    @property
    def is_isolated(self) -> bool:
        """Return True when the node has no admitted inter-lot links."""

        return self.degree_count == 0


@dataclass(slots=True)
class LotConditionNetworkEdge:
    """
    Directed edge in the derived lot dependency/condition network.

    Each edge corresponds to one admitted inter-lot dependency relation and
    does not recompute lot doctrine independently.
    """

    source_part: str
    target_part: str
    role: LotDependencyRole
    mode: LotConditionNetworkEdgeMode

    def __post_init__(self) -> None:
        if self.source_part == self.target_part:
            raise ValueError("LotConditionNetworkEdge invariant failed: source_part and target_part must differ")


@dataclass(slots=True)
class LotConditionNetworkProfile:
    """
    Network profile derived from per-part condition profiles and lot links.

    This is a backend aggregation layer only. It consumes existing condition
    profiles and their admitted inter-lot dependencies.
    """

    nodes: list[LotConditionNetworkNode] = field(default_factory=list)
    edges: list[LotConditionNetworkEdge] = field(default_factory=list)
    isolated_parts: list[str] = field(default_factory=list)
    most_connected_parts: list[str] = field(default_factory=list)
    reciprocal_edge_count: int = 0
    unilateral_edge_count: int = 0

    def __post_init__(self) -> None:
        ordered_names = sorted(node.part_name for node in self.nodes)
        if [node.part_name for node in self.nodes] != ordered_names:
            raise ValueError("LotConditionNetworkProfile invariant failed: nodes must be in deterministic order")

        ordered_edges = sorted(self.edges, key=lambda edge: (edge.source_part, edge.target_part, edge.role.value))
        if self.edges != ordered_edges:
            raise ValueError("LotConditionNetworkProfile invariant failed: edges must be in deterministic order")

        reciprocal = sum(1 for edge in self.edges if edge.mode is LotConditionNetworkEdgeMode.RECIPROCAL)
        unilateral = sum(1 for edge in self.edges if edge.mode is LotConditionNetworkEdgeMode.UNILATERAL)
        if self.reciprocal_edge_count != reciprocal:
            raise ValueError("LotConditionNetworkProfile invariant failed: reciprocal_edge_count must match edges")
        if self.unilateral_edge_count != unilateral:
            raise ValueError("LotConditionNetworkProfile invariant failed: unilateral_edge_count must match edges")
        edge_pairs = {(edge.source_part, edge.target_part) for edge in self.edges}
        for edge in self.edges:
            reverse_present = (edge.target_part, edge.source_part) in edge_pairs
            if edge.mode is LotConditionNetworkEdgeMode.RECIPROCAL and not reverse_present:
                raise ValueError("LotConditionNetworkProfile invariant failed: reciprocal edges must have a reverse edge")
            if edge.mode is LotConditionNetworkEdgeMode.UNILATERAL and reverse_present:
                raise ValueError("LotConditionNetworkProfile invariant failed: unilateral edges must not have a reverse edge")

        node_map = {node.part_name: node for node in self.nodes}
        outgoing = {name: 0 for name in node_map}
        incoming = {name: 0 for name in node_map}
        reciprocal_counts = {name: 0 for name in node_map}
        for edge in self.edges:
            if edge.source_part not in node_map or edge.target_part not in node_map:
                raise ValueError("LotConditionNetworkProfile invariant failed: edges must reference known nodes")
            outgoing[edge.source_part] += 1
            incoming[edge.target_part] += 1
            if edge.mode is LotConditionNetworkEdgeMode.RECIPROCAL:
                reciprocal_counts[edge.source_part] += 1
        for node in self.nodes:
            if node.outgoing_count != outgoing[node.part_name] or node.incoming_count != incoming[node.part_name]:
                raise ValueError("LotConditionNetworkProfile invariant failed: node incoming/outgoing counts must match edges")
            if node.reciprocal_count != reciprocal_counts[node.part_name]:
                raise ValueError("LotConditionNetworkProfile invariant failed: node reciprocal_count must match reciprocal edges")

        expected_isolated = sorted(node.part_name for node in self.nodes if node.is_isolated)
        if self.isolated_parts != expected_isolated:
            raise ValueError("LotConditionNetworkProfile invariant failed: isolated_parts must match nodes")

        if self.nodes:
            max_degree = max(node.degree_count for node in self.nodes)
            expected_most_connected = sorted(
                node.part_name for node in self.nodes if node.degree_count == max_degree and max_degree > 0
            )
        else:
            expected_most_connected = []
        if self.most_connected_parts != expected_most_connected:
            raise ValueError("LotConditionNetworkProfile invariant failed: most_connected_parts must match node degrees")

    @property
    def node_count(self) -> int:
        """Return the number of network nodes."""

        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Return the number of directed network edges."""

        return len(self.edges)


@dataclass(frozen=True, slots=True)
class LotsDerivedReferencePolicy:
    """Policy governing inclusion of the currently supported derived references."""

    include_fortune: bool = True
    include_spirit: bool = True
    include_eros_valens: bool = True


@dataclass(frozen=True, slots=True)
class LotsExternalReferencePolicy:
    """Policy governing admissibility of optional external reference keys."""

    include_syzygy: bool = True
    include_prenatal_new_moon: bool = True
    include_prenatal_full_moon: bool = True
    include_lord_of_hour: bool = True


@dataclass(frozen=True, slots=True)
class LotsComputationPolicy:
    """
    Lean backend policy surface for the lots engine.

    The default policy is intentionally identical to the current engine
    behavior.
    """

    unresolved_reference_mode: LotsReferenceFailureMode = LotsReferenceFailureMode.SKIP
    derived: LotsDerivedReferencePolicy = field(default_factory=LotsDerivedReferencePolicy)
    external: LotsExternalReferencePolicy = field(default_factory=LotsExternalReferencePolicy)

    @property
    def is_default(self) -> bool:
        """Return True when this policy matches current default behavior."""

        return self == LotsComputationPolicy()


@dataclass(slots=True)
class LotReferenceClassification:
    """Typed classification for one preserved lot ingredient reference."""

    kind: LotReferenceKind
    key: str
    detail: str = ""

    @property
    def is_derived(self) -> bool:
        """Return True when the reference was derived rather than directly supplied."""

        return self.kind in {
            LotReferenceKind.DERIVED_LOT,
            LotReferenceKind.HOUSE_RULER,
            LotReferenceKind.ANGLE_RULER_ALIAS,
            LotReferenceKind.PLANET_RULER,
            LotReferenceKind.SYZYGY_RULER,
        }


@dataclass(slots=True)
class ArabicPartClassification:
    """
    Lean typed classification of an already-computed lot.

    This classifies preserved computation truth. It does not alter lot
    longitude, formula semantics, or catalogue doctrine.
    """

    primary_category: str
    category_tags: tuple[str, ...]
    reversal: LotReversalKind
    add_reference: LotReferenceClassification
    sub_reference: LotReferenceClassification

    def __post_init__(self) -> None:
        if not self.category_tags:
            raise ValueError("ArabicPartClassification invariant failed: category_tags must not be empty")
        if self.primary_category not in self.category_tags:
            raise ValueError("ArabicPartClassification invariant failed: primary_category must be included in category_tags")

    @property
    def is_reversed(self) -> bool:
        """Return True when the lot actually reversed for the chart."""

        return self.reversal is LotReversalKind.NIGHT_REVERSED


@dataclass(slots=True)
class LotDependency:
    """
    Formal dependency relation for one lot operand.

    This is a backend-only relational layer. It is derived from preserved lot
    computation truth and does not independently recompute lot doctrine.
    """

    part_name: str
    role: LotDependencyRole
    requested_key: str
    effective_key: str
    reference_kind: LotReferenceKind
    reference_longitude: float
    detail: str = ""

    def __post_init__(self) -> None:
        if self.role is LotDependencyRole.ADD_OPERAND and not self.effective_key:
            raise ValueError("LotDependency invariant failed: add dependency must have an effective_key")
        if self.role is LotDependencyRole.SUB_OPERAND and not self.effective_key:
            raise ValueError("LotDependency invariant failed: sub dependency must have an effective_key")

    @property
    def is_inter_lot(self) -> bool:
        """Return True when the dependency points to another derived lot."""

        return self.reference_kind is LotReferenceKind.DERIVED_LOT

    @property
    def is_external(self) -> bool:
        """Return True when the dependency points to an optional external reference."""

        return self.reference_kind is LotReferenceKind.EXTERNAL

    @property
    def is_indirect(self) -> bool:
        """Return True when the dependency is not a direct supplied reference."""

        return self.is_inter_lot or self.is_external


@dataclass(slots=True)
class LotConditionProfile:
    """
    Integrated per-part condition profile derived from existing lot truth.

    This is a backend synthesis layer only. It consumes preserved lot truth,
    classification, and dependency relations and does not independently
    recompute lot doctrine.
    """

    part_name: str
    category_tags: tuple[str, ...]
    primary_category: str
    reversal: LotReversalKind
    all_dependencies: list[LotDependency] = field(default_factory=list)
    dependencies: list[LotDependency] = field(default_factory=list)
    direct_dependency_count: int = 0
    indirect_dependency_count: int = 0
    inter_lot_dependency_count: int = 0
    external_dependency_count: int = 0
    state: LotConditionState = LotConditionState.DIRECT

    def __post_init__(self) -> None:
        if self.primary_category not in self.category_tags:
            raise ValueError("LotConditionProfile invariant failed: primary_category must be included in category_tags")
        if any(dependency not in self.all_dependencies for dependency in self.dependencies):
            raise ValueError("LotConditionProfile invariant failed: dependencies must be a subset of all_dependencies")
        direct = sum(1 for dependency in self.dependencies if not dependency.is_indirect)
        indirect = sum(1 for dependency in self.dependencies if dependency.is_indirect)
        inter_lot = sum(1 for dependency in self.dependencies if dependency.is_inter_lot)
        external = sum(1 for dependency in self.dependencies if dependency.is_external)
        if (self.direct_dependency_count, self.indirect_dependency_count) != (direct, indirect):
            raise ValueError("LotConditionProfile invariant failed: direct/indirect counts must match dependencies")
        if self.inter_lot_dependency_count != inter_lot:
            raise ValueError("LotConditionProfile invariant failed: inter_lot_dependency_count must match dependencies")
        if self.external_dependency_count != external:
            raise ValueError("LotConditionProfile invariant failed: external_dependency_count must match dependencies")
        expected_state = ArabicPartsService._derive_condition_state(direct, indirect)
        if self.state is not expected_state:
            raise ValueError("LotConditionProfile invariant failed: state must match derived dependency polarity")

    @property
    def has_inter_lot_dependency(self) -> bool:
        """Return True when the lot depends on another derived lot."""

        return self.inter_lot_dependency_count > 0

    @property
    def has_external_dependency(self) -> bool:
        """Return True when the lot depends on an external optional reference."""

        return self.external_dependency_count > 0

@dataclass(slots=True)
class LotReferenceTruth:
    """
    Structured truth for one resolved lot ingredient reference.

    This preserves how an ingredient key such as `Sun`, `H8`, `Ruler H10`, or
    `Fortune` was resolved for computation without changing calculation
    semantics.
    """

    key:         str
    longitude:   float
    source_kind: str
    detail:      str = ""

    def __post_init__(self) -> None:
        LotReferenceKind(self.source_kind)


@dataclass(slots=True)
class ArabicPartComputationTruth:
    """
    Structured doctrinal/computational path for one computed lot.

    This is Phase 1 truth preservation only. It records the operands actually
    used to compute the returned longitude so later classification and policy
    layers do not need to reconstruct hidden logic from the flattened `formula`
    string.
    """

    asc_longitude:      float
    requested_add_key:  str
    requested_sub_key:  str
    effective_add_key:  str
    effective_sub_key:  str
    reversed_at_night:  bool
    reversed_for_chart: bool
    add_reference:      LotReferenceTruth
    sub_reference:      LotReferenceTruth
    formula:            str

    def __post_init__(self) -> None:
        if self.formula != f"Asc + {self.effective_add_key} - {self.effective_sub_key}":
            raise ValueError("ArabicPartComputationTruth invariant failed: formula must match effective operand keys")
        if self.reversed_for_chart and not self.reversed_at_night:
            raise ValueError("ArabicPartComputationTruth invariant failed: reversed_for_chart requires reversed_at_night")
        if self.add_reference.key != self.effective_add_key:
            raise ValueError("ArabicPartComputationTruth invariant failed: add_reference.key must match effective_add_key")
        if self.sub_reference.key != self.effective_sub_key:
            raise ValueError("ArabicPartComputationTruth invariant failed: sub_reference.key must match effective_sub_key")


@dataclass(slots=True)
class ArabicPart:
    """
    RITE: The Hermetic Point — the computed longitude where the sacred formula
          of a lot lands in the zodiac, carrying its name, formula string,
          and sign position.

    THEOREM: Immutable result of computing a single Arabic Part, storing the
             lot name, ecliptic longitude, formula string, category, and
             derived sign/degree fields.

    RITE OF PURPOSE:
        ArabicPart is the result vessel of ArabicPartsService.  It gives
        callers a fully labelled, sign-resolved lot position without requiring
        them to perform the modular arithmetic or sign lookup themselves.
        Without this vessel, callers would receive bare floats with no
        association to the lot's name, tradition, or formula.

    LAW OF OPERATION:
        Responsibilities:
            - Store name, longitude, formula, category, and description.
            - Preserve the resolved computational path in computation_truth.
            - Preserve a typed classification view in classification.
            - Derive sign, sign_symbol, and sign_degree via __post_init__.
            - Provide longitude_dms property for degree/minute/second breakdown.
            - Render a compact human-readable repr.
        Non-responsibilities:
            - Does not compute the lot longitude; that is ArabicPartsService's role.
            - Does not validate that longitude is in [0, 360).
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.constants.sign_of for sign derivation.
        Structural invariants:
            - longitude is in [0, 360).
            - sign, sign_symbol, sign_degree are set by __post_init__ and are
              consistent with longitude.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.lots.ArabicPart",
        "risk": "low",
        "api": {"frozen": ["name", "longitude", "formula", "category", "description"], "internal": ["sign", "sign_symbol", "sign_degree"]},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:        str
    longitude:   float
    formula:     str
    category:    str
    description: str     = ""
    computation_truth: ArabicPartComputationTruth | None = None
    classification: ArabicPartClassification | None = None
    all_dependencies: list[LotDependency] = field(default_factory=list)
    dependencies: list[LotDependency] = field(default_factory=list)
    condition_profile: LotConditionProfile | None = None
    sign:        str     = field(init=False)
    sign_symbol: str     = field(init=False)
    sign_degree: float   = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)
        if not (0.0 <= self.longitude < 360.0):
            raise ValueError("ArabicPart invariant failed: longitude must be in [0, 360)")
        if self.computation_truth is not None:
            if self.formula != self.computation_truth.formula:
                raise ValueError("ArabicPart invariant failed: formula must match computation_truth.formula")
            if self.all_dependencies and len(self.all_dependencies) != 2:
                raise ValueError("ArabicPart invariant failed: all_dependencies must contain exactly two operand relations when present")
            if len(self.dependencies) not in (0, 2):
                raise ValueError("ArabicPart invariant failed: dependencies must be empty or contain exactly two operand relations")
        if self.classification is not None:
            expected_tags = ArabicPartsService._parse_category_tags(self.category)
            if self.classification.category_tags != expected_tags:
                raise ValueError("ArabicPart invariant failed: classification category_tags must match category")
            expected_primary = min(
                expected_tags,
                key=lambda tag: (_CATEGORY_ORDER.get(tag, 99), tag),
                default="general",
            )
            if self.classification.primary_category != expected_primary:
                raise ValueError("ArabicPart invariant failed: classification primary_category must match category ordering")
        if self.computation_truth is not None and self.classification is not None:
            expected_reversal = (
                LotReversalKind.NIGHT_REVERSED
                if self.computation_truth.reversed_for_chart
                else LotReversalKind.NIGHT_REVERSIBLE
                if self.computation_truth.reversed_at_night
                else LotReversalKind.DIRECT
            )
            if self.classification.reversal is not expected_reversal:
                raise ValueError("ArabicPart invariant failed: classification reversal must match computation truth")
            if self.classification.add_reference.kind.value != self.computation_truth.add_reference.source_kind:
                raise ValueError("ArabicPart invariant failed: add-reference classification must match computation truth")
            if self.classification.sub_reference.kind.value != self.computation_truth.sub_reference.source_kind:
                raise ValueError("ArabicPart invariant failed: sub-reference classification must match computation truth")
        if self.computation_truth is not None and self.dependencies:
            add_dependencies = [dep for dep in self.dependencies if dep.role is LotDependencyRole.ADD_OPERAND]
            sub_dependencies = [dep for dep in self.dependencies if dep.role is LotDependencyRole.SUB_OPERAND]
            if len(add_dependencies) != 1 or len(sub_dependencies) != 1:
                raise ValueError("ArabicPart invariant failed: dependencies must contain one add and one sub relation")
            add_dependency = add_dependencies[0]
            sub_dependency = sub_dependencies[0]
            if add_dependency.effective_key != self.computation_truth.effective_add_key:
                raise ValueError("ArabicPart invariant failed: add dependency must match computation truth")
            if sub_dependency.effective_key != self.computation_truth.effective_sub_key:
                raise ValueError("ArabicPart invariant failed: sub dependency must match computation truth")
            if add_dependency.reference_kind.value != self.computation_truth.add_reference.source_kind:
                raise ValueError("ArabicPart invariant failed: add dependency kind must match computation truth")
            if sub_dependency.reference_kind.value != self.computation_truth.sub_reference.source_kind:
                raise ValueError("ArabicPart invariant failed: sub dependency kind must match computation truth")
        if self.all_dependencies:
            for dependency in self.dependencies:
                if dependency not in self.all_dependencies:
                    raise ValueError("ArabicPart invariant failed: dependencies must be a subset of all_dependencies")
        if self.condition_profile is not None:
            if self.condition_profile.part_name != self.name:
                raise ValueError("ArabicPart invariant failed: condition_profile.part_name must match lot name")
            if tuple(self.condition_profile.category_tags) != self.category_tags:
                raise ValueError("ArabicPart invariant failed: condition_profile category_tags must match lot classification")
            if self.condition_profile.primary_category != self.primary_category:
                raise ValueError("ArabicPart invariant failed: condition_profile primary_category must match lot classification")
            if self.condition_profile.reversal is not self.reversal_kind:
                raise ValueError("ArabicPart invariant failed: condition_profile reversal must match lot classification")
            if self.condition_profile.dependencies != self.dependencies:
                raise ValueError("ArabicPart invariant failed: condition_profile dependencies must match lot dependencies")
            if self.condition_profile.all_dependencies != self.all_dependencies:
                raise ValueError("ArabicPart invariant failed: condition_profile all_dependencies must match lot all_dependencies")

    @property
    def longitude_dms(self) -> tuple[int, int, float]:
        d = self.sign_degree
        deg = int(d)
        m   = int((d - deg) * 60)
        s   = ((d - deg) * 60 - m) * 60
        return deg, m, s

    @property
    def category_tags(self) -> tuple[str, ...]:
        """Return the deterministic parsed category tags for this lot."""

        if self.classification is not None:
            return self.classification.category_tags
        return ArabicPartsService._parse_category_tags(self.category)

    @property
    def primary_category(self) -> str:
        """Return the deterministic primary category for this lot."""

        if self.classification is not None:
            return self.classification.primary_category
        return min(
            self.category_tags,
            key=lambda tag: (_CATEGORY_ORDER.get(tag, 99), tag),
            default="general",
        )

    @property
    def reversal_kind(self) -> LotReversalKind:
        """Return the classified reversal state for this lot."""

        if self.classification is not None:
            return self.classification.reversal
        if self.computation_truth is None:
            return LotReversalKind.DIRECT
        if self.computation_truth.reversed_for_chart:
            return LotReversalKind.NIGHT_REVERSED
        if self.computation_truth.reversed_at_night:
            return LotReversalKind.NIGHT_REVERSIBLE
        return LotReversalKind.DIRECT

    @property
    def is_reversed(self) -> bool:
        """Return True when the lot reversed for the current chart."""

        return self.reversal_kind is LotReversalKind.NIGHT_REVERSED

    @property
    def add_reference_kind(self) -> LotReferenceKind | None:
        """Return the classified add-reference kind when available."""

        if self.classification is not None:
            return self.classification.add_reference.kind
        if self.computation_truth is not None:
            return LotReferenceKind(self.computation_truth.add_reference.source_kind)
        return None

    @property
    def sub_reference_kind(self) -> LotReferenceKind | None:
        """Return the classified sub-reference kind when available."""

        if self.classification is not None:
            return self.classification.sub_reference.kind
        if self.computation_truth is not None:
            return LotReferenceKind(self.computation_truth.sub_reference.source_kind)
        return None

    @property
    def dependency_count(self) -> int:
        """Return the number of policy-admitted dependencies on this part."""

        return len(self.dependencies)

    @property
    def all_dependency_count(self) -> int:
        """Return the number of total doctrinal dependencies on this part."""

        return len(self.all_dependencies)

    @property
    def inter_lot_dependencies(self) -> list[LotDependency]:
        """Return admitted dependencies that point to other derived lots."""

        return [dependency for dependency in self.dependencies if dependency.is_inter_lot]

    @property
    def external_dependencies(self) -> list[LotDependency]:
        """Return admitted dependencies that point to external optional references."""

        return [dependency for dependency in self.dependencies if dependency.is_external]

    @property
    def condition_state(self) -> LotConditionState:
        """Return the integrated structural condition state for this lot."""

        if self.condition_profile is not None:
            return self.condition_profile.state
        return ArabicPartsService._derive_condition_state(
            sum(1 for dependency in self.dependencies if not dependency.is_indirect),
            sum(1 for dependency in self.dependencies if dependency.is_indirect),
        )

    def __repr__(self) -> str:
        deg, m, s = self.longitude_dms
        return (f"{self.name} [{self.category}]: {deg:2d}d{m:02d}m "
                f"{self.sign}  ({self.longitude:.4f})  {self.formula}")


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

class ArabicPartsService:
    """
    RITE: The Alchemist of Angles — the Engine that resolves ingredient keys,
          applies day/night reversal, and computes the longitude of every lot
          in the catalogue for a given chart.

    THEOREM: Governs the computation of all Arabic Parts for a ChartContext
             by resolving named ingredient keys to ecliptic longitudes and
             applying the formula Lot = ASC + Add − Subtract (mod 360°).

    RITE OF PURPOSE:
        ArabicPartsService is the computational heart of the Lots Engine.
        It bridges the abstract catalogue of PartDefinition entries and the
        concrete ChartContext, resolving every reference key — planets, angles,
        house cusps, rulers, fixed degrees, and pre-computed lots — into a
        numeric longitude before applying the lot formula.  Without this
        Engine, the catalogue would be inert data with no path to a result.

    LAW OF OPERATION:
        Responsibilities:
            - Resolve ingredient keys (planets, angles, house cusps, rulers,
              fixed degrees, pre-computed lots) to ecliptic longitudes.
            - Apply day/night reversal for lots that require it.
            - Compute Lot = ASC + Add − Subtract (mod 360°) for every entry
              in PARTS_DEFINITIONS.
            - Return a list of ArabicPart results.
        Non-responsibilities:
            - Does not own the catalogue; PARTS_DEFINITIONS is module-level.
            - Does not validate chart completeness before computation.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.chart.ChartContext for planet longitudes, house cusps,
              Ascendant, and MC.
            - moira.constants.sign_of for sign derivation in ArabicPart.
        Failure behavior:
            - Unresolvable ingredient keys return 0.0 silently; the lot is
              still computed and included in the result list.
        Truth preservation:
            - Returned ArabicPart results preserve the resolved doctrinal path
              through computation_truth, including operand reversal and
              ingredient source kinds.
        Future layers:
            - Classification, inspectability, policy, and constitutional
              hardening should consume preserved truth rather than parse
              formula strings or rebuild ingredient logic ad hoc.
        Classification:
            - ArabicPart results carry a lean typed classification describing
              category tags, reversal state, and operand reference kinds.
        Policy:
            - LotsComputationPolicy makes current doctrine explicit without
              changing default computation behavior.
        Relational formalization:
            - ArabicPart results preserve operand dependencies as first-class
              LotDependency relations, and the service can flatten them into a
              dependency surface without recomputing lot logic.
        Dependency hardening:
            - ArabicPart distinguishes doctrinal all_dependencies from the
              currently admitted dependency subset exposed in dependencies.
        Condition integration:
            - ArabicPart results carry a derived LotConditionProfile that
              summarizes dependency structure without changing lot semantics.

    Canon: Abu Ma'shar, The Abbreviation of the Introduction to Astrology;
           al-Biruni, The Book of Instruction in the Elements of the Art of Astrology

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.lots.ArabicPartsService",
        "risk": "medium",
        "api": {"frozen": ["calculate_for_chart"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "silent_default"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def calculate_for_chart(self, chart: ChartContext) -> list[ArabicPart]:
        """
        Calculate all Arabic Parts for a unified ChartContext.
        """
        # Convert planet data to simple longitudes for the ingredient builder
        planet_lons = {name: data.longitude for name, data in chart.planets.items()}
        # Add nodes
        for name, data in chart.nodes.items():
            planet_lons[name] = data.longitude
            
        return self.calculate_parts(
            planet_longitudes=planet_lons,
            house_cusps=chart.houses.cusps if chart.houses else [],
            is_day_chart=chart.is_day,
        )
            
    def calculate_parts(
        self,
        planet_longitudes: dict[str, float],
        house_cusps: dict[int, float] | list[float],
        is_day_chart: bool,
        policy: LotsComputationPolicy | None = None,
        *,
        syzygy: float | None = None,
        prenatal_new_moon: float | None = None,
        prenatal_full_moon: float | None = None,
        lord_of_hour: float | None = None,
    ) -> list[ArabicPart]:
        """
        Calculate all Arabic Parts for raw longitude data.
        """
        policy = self._validate_policy(policy)
        planet_longitudes = self._validate_planet_longitudes(planet_longitudes)
        house_cusps = self._validate_house_cusps(house_cusps)
        refs, ref_truths = self._build_refs(
            planet_longitudes, house_cusps, is_day_chart,
            syzygy, prenatal_new_moon, prenatal_full_moon, lord_of_hour,
            policy=policy,
        )

        results: list[ArabicPart] = []
        for pdef in PARTS_DEFINITIONS:
            requested_add_key = pdef.day_add
            requested_sub_key = pdef.day_sub
            add_key = requested_add_key
            sub_key = requested_sub_key
            reversed_for_chart = pdef.reverse_at_night and not is_day_chart
            if reversed_for_chart:
                add_key, sub_key = sub_key, add_key

            add_val = refs.get(add_key)
            sub_val = refs.get(sub_key)
            if add_val is None or sub_val is None:
                if policy.unresolved_reference_mode is LotsReferenceFailureMode.RAISE:
                    missing = add_key if add_val is None else sub_key
                    raise ValueError(f"Unresolved lot ingredient reference: {missing}")
                continue   # ingredient unavailable — skip silently

            lon     = (refs["Asc"] + add_val - sub_val) % 360.0
            formula = f"Asc + {add_key} - {sub_key}"
            computation_truth = ArabicPartComputationTruth(
                asc_longitude=refs["Asc"],
                requested_add_key=requested_add_key,
                requested_sub_key=requested_sub_key,
                effective_add_key=add_key,
                effective_sub_key=sub_key,
                reversed_at_night=pdef.reverse_at_night,
                reversed_for_chart=reversed_for_chart,
                add_reference=ref_truths[add_key],
                sub_reference=ref_truths[sub_key],
                formula=formula,
            )
            all_dependencies = self._build_part_dependencies(
                part_name=pdef.name,
                computation_truth=computation_truth,
            )

            results.append(ArabicPart(
                name=pdef.name,
                longitude=lon,
                formula=formula,
                category=pdef.category,
                description=pdef.description,
                computation_truth=computation_truth,
                classification=self._classify_part(
                    category=pdef.category,
                    reversed_at_night=pdef.reverse_at_night,
                    reversed_for_chart=reversed_for_chart,
                    add_reference=ref_truths[add_key],
                    sub_reference=ref_truths[sub_key],
                ),
                all_dependencies=all_dependencies,
                dependencies=list(all_dependencies),
                condition_profile=self._build_condition_profile(
                    part_name=pdef.name,
                    classification=self._classify_part(
                        category=pdef.category,
                        reversed_at_night=pdef.reverse_at_night,
                        reversed_for_chart=reversed_for_chart,
                        add_reference=ref_truths[add_key],
                        sub_reference=ref_truths[sub_key],
                    ),
                    all_dependencies=all_dependencies,
                    dependencies=list(all_dependencies),
                ),
            ))

        first_cat = lambda c: min(
            (_CATEGORY_ORDER.get(x.strip(), 99) for x in c.split(",")), default=99
        )
        results.sort(key=lambda p: (first_cat(p.category), p.name))
        return results

    def calculate_dependencies(
        self,
        planet_longitudes: dict[str, float],
        house_cusps: dict[int, float] | list[float],
        is_day_chart: bool,
        policy: LotsComputationPolicy | None = None,
        *,
        syzygy: float | None = None,
        prenatal_new_moon: float | None = None,
        prenatal_full_moon: float | None = None,
        lord_of_hour: float | None = None,
    ) -> list[LotDependency]:
        """Return all formal lot dependencies for the currently computable lots."""

        parts = self.calculate_parts(
            planet_longitudes,
            house_cusps,
            is_day_chart,
            policy=policy,
            syzygy=syzygy,
            prenatal_new_moon=prenatal_new_moon,
            prenatal_full_moon=prenatal_full_moon,
            lord_of_hour=lord_of_hour,
        )
        dependencies = [dependency for part in parts for dependency in part.dependencies]
        dependencies.sort(key=lambda dep: (dep.part_name, dep.role.value, dep.effective_key))
        return dependencies

    def calculate_all_dependencies(
        self,
        planet_longitudes: dict[str, float],
        house_cusps: dict[int, float] | list[float],
        is_day_chart: bool,
        *,
        syzygy: float | None = None,
        prenatal_new_moon: float | None = None,
        prenatal_full_moon: float | None = None,
        lord_of_hour: float | None = None,
    ) -> list[LotDependency]:
        """Return all doctrinally computable dependencies under default admission."""

        parts = self.calculate_parts(
            planet_longitudes,
            house_cusps,
            is_day_chart,
            policy=LotsComputationPolicy(),
            syzygy=syzygy,
            prenatal_new_moon=prenatal_new_moon,
            prenatal_full_moon=prenatal_full_moon,
            lord_of_hour=lord_of_hour,
        )
        dependencies = [dependency for part in parts for dependency in part.all_dependencies]
        dependencies.sort(key=lambda dep: (dep.part_name, dep.role.value, dep.effective_key))
        return dependencies

    def calculate_condition_profiles(
        self,
        planet_longitudes: dict[str, float],
        house_cusps: dict[int, float] | list[float],
        is_day_chart: bool,
        policy: LotsComputationPolicy | None = None,
        *,
        syzygy: float | None = None,
        prenatal_new_moon: float | None = None,
        prenatal_full_moon: float | None = None,
        lord_of_hour: float | None = None,
    ) -> list[LotConditionProfile]:
        """Return integrated condition profiles for the currently computable lots."""

        parts = self.calculate_parts(
            planet_longitudes,
            house_cusps,
            is_day_chart,
            policy=policy,
            syzygy=syzygy,
            prenatal_new_moon=prenatal_new_moon,
            prenatal_full_moon=prenatal_full_moon,
            lord_of_hour=lord_of_hour,
        )
        profiles = [part.condition_profile for part in parts if part.condition_profile is not None]
        profiles.sort(key=lambda profile: (profile.primary_category, profile.part_name))
        return profiles

    def calculate_chart_condition_profile(
        self,
        planet_longitudes: dict[str, float],
        house_cusps: dict[int, float] | list[float],
        is_day_chart: bool,
        policy: LotsComputationPolicy | None = None,
        *,
        syzygy: float | None = None,
        prenatal_new_moon: float | None = None,
        prenatal_full_moon: float | None = None,
        lord_of_hour: float | None = None,
    ) -> LotChartConditionProfile:
        """Return the chart-wide lot condition profile."""

        profiles = self.calculate_condition_profiles(
            planet_longitudes,
            house_cusps,
            is_day_chart,
            policy=policy,
            syzygy=syzygy,
            prenatal_new_moon=prenatal_new_moon,
            prenatal_full_moon=prenatal_full_moon,
            lord_of_hour=lord_of_hour,
        )

        def ranking_key(profile: LotConditionProfile) -> tuple[int, int, int, str]:
            state_rank = {
                LotConditionState.DIRECT: 0,
                LotConditionState.MIXED: 1,
                LotConditionState.INDIRECT: 2,
            }[profile.state]
            return (
                state_rank,
                -profile.direct_dependency_count,
                profile.indirect_dependency_count,
                profile.part_name,
            )

        strongest_sorted = sorted(profiles, key=ranking_key)
        weakest_sorted = sorted(
            profiles,
            key=lambda profile: (
                {
                    LotConditionState.INDIRECT: 0,
                    LotConditionState.MIXED: 1,
                    LotConditionState.DIRECT: 2,
                }[profile.state],
                -profile.indirect_dependency_count,
                profile.direct_dependency_count,
                profile.part_name,
            ),
        )
        strongest_score = ranking_key(strongest_sorted[0]) if strongest_sorted else None
        weakest_score = weakest_sorted[0] if weakest_sorted else None
        strongest_parts = [
            profile.part_name for profile in strongest_sorted
            if ranking_key(profile) == strongest_score
        ] if strongest_sorted else []
        weakest_parts = [
            profile.part_name for profile in weakest_sorted
            if (
                profile.state is weakest_score.state
                and profile.indirect_dependency_count == weakest_score.indirect_dependency_count
                and profile.direct_dependency_count == weakest_score.direct_dependency_count
            )
        ] if weakest_sorted else []

        return LotChartConditionProfile(
            profiles=profiles,
            direct_count=sum(1 for profile in profiles if profile.state is LotConditionState.DIRECT),
            mixed_count=sum(1 for profile in profiles if profile.state is LotConditionState.MIXED),
            indirect_count=sum(1 for profile in profiles if profile.state is LotConditionState.INDIRECT),
            direct_dependency_total=sum(profile.direct_dependency_count for profile in profiles),
            indirect_dependency_total=sum(profile.indirect_dependency_count for profile in profiles),
            inter_lot_dependency_total=sum(profile.inter_lot_dependency_count for profile in profiles),
            external_dependency_total=sum(profile.external_dependency_count for profile in profiles),
            strongest_parts=strongest_parts,
            weakest_parts=weakest_parts,
        )

    def calculate_condition_network_profile(
        self,
        planet_longitudes: dict[str, float],
        house_cusps: dict[int, float] | list[float],
        is_day_chart: bool,
        policy: LotsComputationPolicy | None = None,
        *,
        syzygy: float | None = None,
        prenatal_new_moon: float | None = None,
        prenatal_full_moon: float | None = None,
        lord_of_hour: float | None = None,
    ) -> LotConditionNetworkProfile:
        """Return the derived inter-lot dependency/condition network profile."""

        profiles = self.calculate_condition_profiles(
            planet_longitudes,
            house_cusps,
            is_day_chart,
            policy=policy,
            syzygy=syzygy,
            prenatal_new_moon=prenatal_new_moon,
            prenatal_full_moon=prenatal_full_moon,
            lord_of_hour=lord_of_hour,
        )
        profile_map = {profile.part_name: profile for profile in profiles}

        edge_pairs: set[tuple[str, str]] = set()
        edge_triples: list[tuple[str, str, LotDependencyRole]] = []
        for profile in profiles:
            for dependency in profile.dependencies:
                if not dependency.is_inter_lot or dependency.effective_key not in profile_map:
                    continue
                edge_pairs.add((profile.part_name, dependency.effective_key))
                edge_triples.append((profile.part_name, dependency.effective_key, dependency.role))

        edges = [
            LotConditionNetworkEdge(
                source_part=source_part,
                target_part=target_part,
                role=role,
                mode=(
                    LotConditionNetworkEdgeMode.RECIPROCAL
                    if (target_part, source_part) in edge_pairs
                    else LotConditionNetworkEdgeMode.UNILATERAL
                ),
            )
            for source_part, target_part, role in sorted(edge_triples, key=lambda item: (item[0], item[1], item[2].value))
        ]

        outgoing_counts = {name: 0 for name in profile_map}
        incoming_counts = {name: 0 for name in profile_map}
        reciprocal_counts = {name: 0 for name in profile_map}
        for edge in edges:
            outgoing_counts[edge.source_part] += 1
            incoming_counts[edge.target_part] += 1
            if edge.mode is LotConditionNetworkEdgeMode.RECIPROCAL:
                reciprocal_counts[edge.source_part] += 1

        nodes = [
            LotConditionNetworkNode(
                part_name=profile.part_name,
                condition_state=profile.state,
                outgoing_count=outgoing_counts[profile.part_name],
                incoming_count=incoming_counts[profile.part_name],
                reciprocal_count=reciprocal_counts[profile.part_name],
            )
            for profile in sorted(profiles, key=lambda profile: profile.part_name)
        ]

        max_degree = max((node.degree_count for node in nodes), default=0)
        return LotConditionNetworkProfile(
            nodes=nodes,
            edges=edges,
            isolated_parts=sorted(node.part_name for node in nodes if node.is_isolated),
            most_connected_parts=sorted(
                node.part_name for node in nodes if node.degree_count == max_degree and max_degree > 0
            ),
            reciprocal_edge_count=sum(1 for edge in edges if edge.mode is LotConditionNetworkEdgeMode.RECIPROCAL),
            unilateral_edge_count=sum(1 for edge in edges if edge.mode is LotConditionNetworkEdgeMode.UNILATERAL),
        )

    # ------------------------------------------------------------------

    def _build_refs(
        self,
        planet_lons: dict[str, float],
        house_cusps: dict[int, float] | list[float],
        is_day: bool,
        syzygy: float | None,
        prenatal_nm: float | None,
        prenatal_fm: float | None,
        lord_of_hour: float | None,
        *,
        policy: LotsComputationPolicy,
    ) -> tuple[dict[str, float], dict[str, LotReferenceTruth]]:
        # Normalise planet names to title case
        norm: dict[str, float] = {}
        ref_truths: dict[str, LotReferenceTruth] = {}

        def store_ref(key: str, longitude: float, source_kind: str, detail: str = "") -> None:
            ref_truths[key] = LotReferenceTruth(
                key=key,
                longitude=longitude,
                source_kind=source_kind,
                detail=detail,
            )

        for name, lon in planet_lons.items():
            n = name.strip().title()
            norm[n] = lon
            store_ref(n, lon, "planet", name.strip())
            if n.lower() in ("true node", "north node", "mean node"):
                norm["North Node"] = lon
                store_ref("North Node", lon, "planet_alias", n)

        # Accept both list (0-indexed, from HouseCusps.cusps) and dict (1-indexed)
        if isinstance(house_cusps, list):
            house_cusps = {i + 1: v for i, v in enumerate(house_cusps)}

        asc = house_cusps.get(1, 0.0)
        mc  = house_cusps.get(10, 0.0)
        dsc = (asc + 180.0) % 360.0
        ic  = (mc  + 180.0) % 360.0

        refs: dict[str, float] = {
            **norm,
            "Asc": asc, "Dsc": dsc, "MC": mc, "IC": ic,
        }
        store_ref("Asc", asc, "angle", "house_cusp_1")
        store_ref("Dsc", dsc, "angle", "derived_from_asc")
        store_ref("MC", mc, "angle", "house_cusp_10")
        store_ref("IC", ic, "angle", "derived_from_mc")

        # House cusps H1–H12
        for i in range(1, 13):
            refs[f"H{i}"] = house_cusps.get(i, 0.0)
            store_ref(f"H{i}", refs[f"H{i}"], "house_cusp", f"house_{i}")

        # Fixed-degree constants
        refs.update(_FIXED_DEG)
        for key, lon in _FIXED_DEG.items():
            store_ref(key, lon, "fixed_degree")

        # Optional externals
        if syzygy is not None and policy.external.include_syzygy:
            refs["Syzygy"] = syzygy
            store_ref("Syzygy", syzygy, "external", "syzygy")
        if prenatal_nm is not None and policy.external.include_prenatal_new_moon:
            refs["New Moon"]           = prenatal_nm
            refs["Prenatal New Moon"]  = prenatal_nm
            store_ref("New Moon", prenatal_nm, "external", "prenatal_new_moon")
            store_ref("Prenatal New Moon", prenatal_nm, "external", "prenatal_new_moon")
        if prenatal_fm is not None and policy.external.include_prenatal_full_moon:
            refs["Prenatal Full Moon"] = prenatal_fm
            store_ref("Prenatal Full Moon", prenatal_fm, "external", "prenatal_full_moon")
        if lord_of_hour is not None and policy.external.include_lord_of_hour:
            refs["Lord of Hour"] = lord_of_hour
            store_ref("Lord of Hour", lord_of_hour, "external", "lord_of_hour")

        # Pre-compute Fortune and Spirit
        if is_day:
            fortune_lon = (asc + norm.get("Moon", 0) - norm.get("Sun", 0)) % 360.0
            spirit_lon  = (asc + norm.get("Sun",  0) - norm.get("Moon", 0)) % 360.0
        else:
            fortune_lon = (asc + norm.get("Sun",  0) - norm.get("Moon", 0)) % 360.0
            spirit_lon  = (asc + norm.get("Moon", 0) - norm.get("Sun",  0)) % 360.0
        if policy.derived.include_fortune:
            refs["Fortune"] = fortune_lon
            store_ref("Fortune", fortune_lon, "derived_lot", "part_of_fortune")
        if policy.derived.include_spirit:
            refs["Spirit"] = spirit_lon
            store_ref("Spirit", spirit_lon, "derived_lot", "part_of_spirit")

        # Eros (Valens) = Asc + Spirit - Fortune  (reversible)
        if (
            policy.derived.include_eros_valens
            and policy.derived.include_fortune
            and policy.derived.include_spirit
        ):
            if is_day:
                refs["Eros (Valens)"] = (asc + spirit_lon  - fortune_lon) % 360.0
            else:
                refs["Eros (Valens)"] = (asc + fortune_lon - spirit_lon)  % 360.0
            store_ref("Eros (Valens)", refs["Eros (Valens)"], "derived_lot", "eros_valens")

        # House rulers H1–H12
        for i in range(1, 13):
            cusp_lon  = house_cusps.get(i, 0.0)
            sign_name = SIGNS[int(cusp_lon // 30) % 12]
            ruler_key = _SIGN_RULER[sign_name]
            ruler_lon = norm.get(ruler_key)
            if ruler_lon is not None:
                refs[f"Ruler H{i}"] = ruler_lon
                store_ref(f"Ruler H{i}", ruler_lon, "house_ruler", f"H{i}->{ruler_key}")

        # Named-house ruler aliases: "Ruler Asc" = "Ruler H1", etc.
        for src, dst in [("Ruler Asc","Ruler H1"), ("Ruler Dsc","Ruler H7"),
                         ("Ruler MC", "Ruler H10"), ("Ruler IC","Ruler H4")]:
            if dst in refs:
                refs[src] = refs[dst]
                store_ref(src, refs[src], "angle_ruler_alias", dst)

        # Ruler of a planet's own sign ("Ruler Sun", "Ruler Moon", …)
        for body in ("Sun","Moon","Mercury","Venus","Mars",
                     "Jupiter","Saturn","Uranus","Neptune","Pluto"):
            if body in norm:
                sign_name = SIGNS[int(norm[body] // 30) % 12]
                ruler_key = _SIGN_RULER[sign_name]
                if ruler_key in norm:
                    refs[f"Ruler {body}"] = norm[ruler_key]
                    store_ref(f"Ruler {body}", norm[ruler_key], "planet_ruler", f"{body}->{ruler_key}")

        # Ruler of the Syzygy sign
        if "Syzygy" in refs:
            sign_name = SIGNS[int(refs["Syzygy"] // 30) % 12]
            ruler_key = _SIGN_RULER[sign_name]
            if ruler_key in norm:
                refs["Ruler Syzygy"] = norm[ruler_key]
                store_ref("Ruler Syzygy", norm[ruler_key], "syzygy_ruler", ruler_key)

        return refs, ref_truths

    # ------------------------------------------------------------------

    @staticmethod
    def is_day_chart(sun_longitude: float, asc_longitude: float) -> bool:
        """True when Sun is above horizon (houses 7–12)."""
        diff = (sun_longitude - asc_longitude) % 360.0
        return diff >= 180.0 or diff == 0.0

    @staticmethod
    def _classify_reference_truth(reference: LotReferenceTruth) -> LotReferenceClassification:
        """Classify one preserved reference truth without changing its meaning."""

        return LotReferenceClassification(
            kind=LotReferenceKind(reference.source_kind),
            key=reference.key,
            detail=reference.detail,
        )

    @staticmethod
    def _parse_category_tags(category: str) -> tuple[str, ...]:
        """Return deterministic category tags from the stored category string."""

        return tuple(tag.strip() for tag in category.split(",") if tag.strip())

    @staticmethod
    def _classify_part(
        *,
        category: str,
        reversed_at_night: bool,
        reversed_for_chart: bool,
        add_reference: LotReferenceTruth,
        sub_reference: LotReferenceTruth,
    ) -> ArabicPartClassification:
        """Build a lean classification from already-preserved computation truth."""

        category_tags = ArabicPartsService._parse_category_tags(category)
        primary_category = min(
            category_tags,
            key=lambda tag: (_CATEGORY_ORDER.get(tag, 99), tag),
            default="general",
        )
        if reversed_for_chart:
            reversal = LotReversalKind.NIGHT_REVERSED
        elif reversed_at_night:
            reversal = LotReversalKind.NIGHT_REVERSIBLE
        else:
            reversal = LotReversalKind.DIRECT
        return ArabicPartClassification(
            primary_category=primary_category,
            category_tags=category_tags,
            reversal=reversal,
            add_reference=ArabicPartsService._classify_reference_truth(add_reference),
            sub_reference=ArabicPartsService._classify_reference_truth(sub_reference),
        )

    @staticmethod
    def _build_part_dependencies(
        *,
        part_name: str,
        computation_truth: ArabicPartComputationTruth,
    ) -> list[LotDependency]:
        """Build the two formal operand dependencies for one computed lot."""

        return [
            LotDependency(
                part_name=part_name,
                role=LotDependencyRole.ADD_OPERAND,
                requested_key=computation_truth.requested_add_key,
                effective_key=computation_truth.effective_add_key,
                reference_kind=LotReferenceKind(computation_truth.add_reference.source_kind),
                reference_longitude=computation_truth.add_reference.longitude,
                detail=computation_truth.add_reference.detail,
            ),
            LotDependency(
                part_name=part_name,
                role=LotDependencyRole.SUB_OPERAND,
                requested_key=computation_truth.requested_sub_key,
                effective_key=computation_truth.effective_sub_key,
                reference_kind=LotReferenceKind(computation_truth.sub_reference.source_kind),
                reference_longitude=computation_truth.sub_reference.longitude,
                detail=computation_truth.sub_reference.detail,
            ),
        ]

    @staticmethod
    def _derive_condition_state(direct_dependency_count: int, indirect_dependency_count: int) -> LotConditionState:
        """Derive the structural condition state from dependency composition."""

        if indirect_dependency_count == 0:
            return LotConditionState.DIRECT
        if direct_dependency_count == 0:
            return LotConditionState.INDIRECT
        return LotConditionState.MIXED

    @staticmethod
    def _build_condition_profile(
        *,
        part_name: str,
        classification: ArabicPartClassification,
        all_dependencies: list[LotDependency],
        dependencies: list[LotDependency],
    ) -> LotConditionProfile:
        """Build the integrated per-part condition profile."""

        direct = sum(1 for dependency in dependencies if not dependency.is_indirect)
        indirect = sum(1 for dependency in dependencies if dependency.is_indirect)
        inter_lot = sum(1 for dependency in dependencies if dependency.is_inter_lot)
        external = sum(1 for dependency in dependencies if dependency.is_external)
        return LotConditionProfile(
            part_name=part_name,
            category_tags=classification.category_tags,
            primary_category=classification.primary_category,
            reversal=classification.reversal,
            all_dependencies=list(all_dependencies),
            dependencies=list(dependencies),
            direct_dependency_count=direct,
            indirect_dependency_count=indirect,
            inter_lot_dependency_count=inter_lot,
            external_dependency_count=external,
            state=ArabicPartsService._derive_condition_state(direct, indirect),
        )

    @staticmethod
    def _validate_policy(policy: LotsComputationPolicy | None) -> LotsComputationPolicy:
        """Return a valid lots policy or raise clearly on unsupported values."""

        if policy is None:
            policy = LotsComputationPolicy()
        if not isinstance(policy.unresolved_reference_mode, LotsReferenceFailureMode):
            raise ValueError("Unsupported lots unresolved-reference mode")
        if not isinstance(policy.derived, LotsDerivedReferencePolicy):
            raise ValueError("Unsupported lots derived-reference policy")
        if not isinstance(policy.external, LotsExternalReferencePolicy):
            raise ValueError("Unsupported lots external-reference policy")
        for attr in ("include_fortune", "include_spirit", "include_eros_valens"):
            if not isinstance(getattr(policy.derived, attr), bool):
                raise ValueError(f"Lots derived-reference policy field {attr} must be a bool")
        for attr in ("include_syzygy", "include_prenatal_new_moon", "include_prenatal_full_moon", "include_lord_of_hour"):
            if not isinstance(getattr(policy.external, attr), bool):
                raise ValueError(f"Lots external-reference policy field {attr} must be a bool")
        return policy

    @staticmethod
    def _validate_planet_longitudes(planet_longitudes: dict[str, float]) -> dict[str, float]:
        """Validate and normalize raw lot longitudes."""

        normalized: dict[str, float] = {}
        for name, longitude in planet_longitudes.items():
            normalized_name = name.strip().title()
            if not normalized_name:
                raise ValueError("Lot planet name must not be empty")
            if normalized_name in normalized:
                raise ValueError(f"Duplicate lot planet entry after normalization: {normalized_name}")
            if not isfinite(longitude):
                raise ValueError(f"Lot longitude for {normalized_name} must be finite")
            normalized[normalized_name] = longitude % 360.0
        return normalized

    @staticmethod
    def _validate_house_cusps(house_cusps: dict[int, float] | list[float]) -> dict[int, float]:
        """Validate and normalize house cusps for lot computation."""

        if isinstance(house_cusps, list):
            if len(house_cusps) != 12:
                raise ValueError("Lot house_cusps list must contain exactly 12 entries")
            normalized = {i + 1: cusp for i, cusp in enumerate(house_cusps)}
        else:
            normalized: dict[int, float] = {}
            for number, cusp in house_cusps.items():
                if not isinstance(number, int):
                    raise ValueError("Lot house cusp numbers must be integers")
                if number < 1 or number > 12:
                    raise ValueError(f"Lot house cusp number must be in the range 1..12: {number}")
                if number in normalized:
                    raise ValueError(f"Duplicate lot house cusp number: {number}")
                normalized[number] = cusp
        missing = [number for number in range(1, 13) if number not in normalized]
        if missing:
            raise ValueError(f"Lot house cusps missing {missing}")
        for number, cusp in normalized.items():
            if not isfinite(cusp):
                raise ValueError(f"Lot house cusp {number} must be finite")
            normalized[number] = cusp % 360.0
        return normalized


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_service = ArabicPartsService()


def calculate_lots(
    positions: dict[str, float],
    house_cusps: dict[int, float],
    is_day_chart: bool,
    policy: LotsComputationPolicy | None = None,
    *,
    syzygy: float | None = None,
    prenatal_new_moon: float | None = None,
    prenatal_full_moon: float | None = None,
    lord_of_hour: float | None = None,
    ) -> list[ArabicPart]:
    """Compute all Arabic Parts."""
    return _service.calculate_parts(
        positions, house_cusps, is_day_chart, policy=policy,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )


def calculate_lot_dependencies(
    positions: dict[str, float],
    house_cusps: dict[int, float],
    is_day_chart: bool,
    policy: LotsComputationPolicy | None = None,
    *,
    syzygy: float | None = None,
    prenatal_new_moon: float | None = None,
    prenatal_full_moon: float | None = None,
    lord_of_hour: float | None = None,
) -> list[LotDependency]:
    """Compute all formal lot dependencies for the currently computable lots."""

    return _service.calculate_dependencies(
        positions,
        house_cusps,
        is_day_chart,
        policy=policy,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )


def calculate_all_lot_dependencies(
    positions: dict[str, float],
    house_cusps: dict[int, float],
    is_day_chart: bool,
    *,
    syzygy: float | None = None,
    prenatal_new_moon: float | None = None,
    prenatal_full_moon: float | None = None,
    lord_of_hour: float | None = None,
) -> list[LotDependency]:
    """Compute the doctrinal dependency set under default admission behavior."""

    return _service.calculate_all_dependencies(
        positions,
        house_cusps,
        is_day_chart,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )


def calculate_lot_condition_profiles(
    positions: dict[str, float],
    house_cusps: dict[int, float],
    is_day_chart: bool,
    policy: LotsComputationPolicy | None = None,
    *,
    syzygy: float | None = None,
    prenatal_new_moon: float | None = None,
    prenatal_full_moon: float | None = None,
    lord_of_hour: float | None = None,
) -> list[LotConditionProfile]:
    """Compute integrated condition profiles for the currently computable lots."""

    return _service.calculate_condition_profiles(
        positions,
        house_cusps,
        is_day_chart,
        policy=policy,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )


def calculate_lot_chart_condition_profile(
    positions: dict[str, float],
    house_cusps: dict[int, float],
    is_day_chart: bool,
    policy: LotsComputationPolicy | None = None,
    *,
    syzygy: float | None = None,
    prenatal_new_moon: float | None = None,
    prenatal_full_moon: float | None = None,
    lord_of_hour: float | None = None,
) -> LotChartConditionProfile:
    """Compute the chart-wide lot condition profile."""

    return _service.calculate_chart_condition_profile(
        positions,
        house_cusps,
        is_day_chart,
        policy=policy,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )


def calculate_lot_condition_network_profile(
    positions: dict[str, float],
    house_cusps: dict[int, float],
    is_day_chart: bool,
    policy: LotsComputationPolicy | None = None,
    *,
    syzygy: float | None = None,
    prenatal_new_moon: float | None = None,
    prenatal_full_moon: float | None = None,
    lord_of_hour: float | None = None,
) -> LotConditionNetworkProfile:
    """Compute the derived inter-lot dependency/condition network profile."""

    return _service.calculate_condition_network_profile(
        positions,
        house_cusps,
        is_day_chart,
        policy=policy,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )


def list_parts() -> list[str]:
    """Return sorted list of part names."""
    return sorted(p.name for p in PARTS_DEFINITIONS)

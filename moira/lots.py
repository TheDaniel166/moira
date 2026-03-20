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

from .constants import sign_of, SIGNS
from .chart import ChartContext


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
    PartDefinition("Debt",                              "Mercury",       "Saturn",         False, "hellenistic,medieval"),
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
    PartDefinition("Friends (Firmicus)",                "Mercury",       "Jupiter",        False, "hellenistic"),
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
    PartDefinition("Travel (Firmicus)",                 "Mars",          "Sun",            True,  "hellenistic,medieval"),
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
    sign:        str     = field(init=False)
    sign_symbol: str     = field(init=False)
    sign_degree: float   = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    @property
    def longitude_dms(self) -> tuple[int, int, float]:
        d = self.sign_degree
        deg = int(d)
        m   = int((d - deg) * 60)
        s   = ((d - deg) * 60 - m) * 60
        return deg, m, s

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
            is_day_chart=chart.is_day
        )
            
    def calculate_parts(
        self,
        planet_longitudes: dict[str, float],
        house_cusps: dict[int, float] | list[float],
        is_day_chart: bool,
        *,
        syzygy: float | None = None,
        prenatal_new_moon: float | None = None,
        prenatal_full_moon: float | None = None,
        lord_of_hour: float | None = None,
    ) -> list[ArabicPart]:
        """
        Calculate all Arabic Parts for raw longitude data.
        """
        refs = self._build_refs(
            planet_longitudes, house_cusps, is_day_chart,
            syzygy, prenatal_new_moon, prenatal_full_moon, lord_of_hour,
        )

        results: list[ArabicPart] = []
        for pdef in PARTS_DEFINITIONS:
            add_key = pdef.day_add
            sub_key = pdef.day_sub
            if pdef.reverse_at_night and not is_day_chart:
                add_key, sub_key = sub_key, add_key

            add_val = refs.get(add_key)
            sub_val = refs.get(sub_key)
            if add_val is None or sub_val is None:
                continue   # ingredient unavailable — skip silently

            lon     = (refs["Asc"] + add_val - sub_val) % 360.0
            formula = f"Asc + {add_key} - {sub_key}"

            results.append(ArabicPart(
                name=pdef.name,
                longitude=lon,
                formula=formula,
                category=pdef.category,
                description=pdef.description,
            ))

        first_cat = lambda c: min(
            (_CATEGORY_ORDER.get(x.strip(), 99) for x in c.split(",")), default=99
        )
        results.sort(key=lambda p: (first_cat(p.category), p.name))
        return results

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
    ) -> dict[str, float]:
        # Normalise planet names to title case
        norm: dict[str, float] = {}
        for name, lon in planet_lons.items():
            n = name.strip().title()
            norm[n] = lon
            if n.lower() in ("true node", "north node", "mean node"):
                norm["North Node"] = lon

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

        # House cusps H1–H12
        for i in range(1, 13):
            refs[f"H{i}"] = house_cusps.get(i, 0.0)

        # Fixed-degree constants
        refs.update(_FIXED_DEG)

        # Optional externals
        if syzygy is not None:
            refs["Syzygy"] = syzygy
        if prenatal_nm is not None:
            refs["New Moon"]           = prenatal_nm
            refs["Prenatal New Moon"]  = prenatal_nm
        if prenatal_fm is not None:
            refs["Prenatal Full Moon"] = prenatal_fm
        if lord_of_hour is not None:
            refs["Lord of Hour"] = lord_of_hour

        # Pre-compute Fortune and Spirit
        if is_day:
            fortune_lon = (asc + norm.get("Moon", 0) - norm.get("Sun", 0)) % 360.0
            spirit_lon  = (asc + norm.get("Sun",  0) - norm.get("Moon", 0)) % 360.0
        else:
            fortune_lon = (asc + norm.get("Sun",  0) - norm.get("Moon", 0)) % 360.0
            spirit_lon  = (asc + norm.get("Moon", 0) - norm.get("Sun",  0)) % 360.0
        refs["Fortune"] = fortune_lon
        refs["Spirit"]  = spirit_lon

        # Eros (Valens) = Asc + Spirit - Fortune  (reversible)
        if is_day:
            refs["Eros (Valens)"] = (asc + spirit_lon  - fortune_lon) % 360.0
        else:
            refs["Eros (Valens)"] = (asc + fortune_lon - spirit_lon)  % 360.0

        # House rulers H1–H12
        for i in range(1, 13):
            cusp_lon  = house_cusps.get(i, 0.0)
            sign_name = SIGNS[int(cusp_lon // 30) % 12]
            ruler_key = _SIGN_RULER[sign_name]
            ruler_lon = norm.get(ruler_key)
            if ruler_lon is not None:
                refs[f"Ruler H{i}"] = ruler_lon

        # Named-house ruler aliases: "Ruler Asc" = "Ruler H1", etc.
        for src, dst in [("Ruler Asc","Ruler H1"), ("Ruler Dsc","Ruler H7"),
                         ("Ruler MC", "Ruler H10"), ("Ruler IC","Ruler H4")]:
            if dst in refs:
                refs[src] = refs[dst]

        # Ruler of a planet's own sign ("Ruler Sun", "Ruler Moon", …)
        for body in ("Sun","Moon","Mercury","Venus","Mars",
                     "Jupiter","Saturn","Uranus","Neptune","Pluto"):
            if body in norm:
                sign_name = SIGNS[int(norm[body] // 30) % 12]
                ruler_key = _SIGN_RULER[sign_name]
                if ruler_key in norm:
                    refs[f"Ruler {body}"] = norm[ruler_key]

        # Ruler of the Syzygy sign
        if "Syzygy" in refs:
            sign_name = SIGNS[int(refs["Syzygy"] // 30) % 12]
            ruler_key = _SIGN_RULER[sign_name]
            if ruler_key in norm:
                refs["Ruler Syzygy"] = norm[ruler_key]

        return refs

    # ------------------------------------------------------------------

    @staticmethod
    def is_day_chart(sun_longitude: float, asc_longitude: float) -> bool:
        """True when Sun is above horizon (houses 7–12)."""
        diff = (sun_longitude - asc_longitude) % 360.0
        return diff >= 180.0 or diff == 0.0


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_service = ArabicPartsService()


def calculate_lots(
    positions: dict[str, float],
    house_cusps: dict[int, float],
    is_day_chart: bool,
    *,
    syzygy: float | None = None,
    prenatal_new_moon: float | None = None,
    prenatal_full_moon: float | None = None,
    lord_of_hour: float | None = None,
) -> list[ArabicPart]:
    """Compute all Arabic Parts."""
    return _service.calculate_parts(
        positions, house_cusps, is_day_chart,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )


def list_parts() -> list[str]:
    """Return sorted list of part names."""
    return sorted(p.name for p in PARTS_DEFINITIONS)

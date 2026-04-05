"""
Moira — Manazil Engine
=======================

Archetype: Engine

Purpose
-------
Governs computation of Arabic Lunar Mansion (Manazil al-Qamar) positions,
mapping any ecliptic longitude to one of the 28 equal stations of the Moon
together with their traditional significations.

Supports tropical and sidereal computation, and multiple textual
traditions for mansion attributions (al-Biruni default, plus Abenragel,
Ibn al-Arabi, Agrippa, and Picatrix variant tables).

Boundary declaration
--------------------
Owns: the 28-mansion table, mansion span arithmetic, ``MansionInfo`` and
      ``MansionPosition`` result vessels, variant attribution tables.
Delegates: sidereal conversion to ``moira.sidereal``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure arithmetic over
ecliptic longitudes (sidereal mode requires a Julian Day for ayanamsa).

Public surface
--------------
``MansionInfo``          — immutable record for one of the 28 mansion definitions.
``MansionPosition``      — vessel for a body's mansion position result.
``MansionTradition``     — enum selecting which textual tradition to use.
``MANSIONS``             — ordered list of all 28 ``MansionInfo`` records (al-Biruni).
``MANSION_SPAN``         — degrees per mansion (360/28).
``mansion_of``           — compute mansion for a single ecliptic longitude.
``mansion_of_sidereal``  — compute mansion using sidereal longitude (via ayanamsa).
``all_mansions_at``      — compute mansions for a dict of body positions.
``all_mansions_at_sidereal`` — sidereal batch computation.
``moon_mansion``         — convenience wrapper for the Moon's mansion.
``variant_nature``       — look up a mansion's nature in a specific tradition.
``variant_signification``— look up a mansion's signification in a specific tradition.
"""

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "MansionInfo",
    "MansionPosition",
    "MansionTradition",
    "MANSIONS",
    "MANSION_SPAN",
    "mansion_of",
    "mansion_of_sidereal",
    "all_mansions_at",
    "all_mansions_at_sidereal",
    "moon_mansion",
    "variant_nature",
    "variant_signification",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MANSION_SPAN: float = 360.0 / 28   # 12.857142...°


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MansionInfo:
    """
    RITE: The Mansion Record — the immutable definition of one lunar station.

    THEOREM: Holds the index, Arabic name, Latin name, ruling star, nature,
    and traditional signification for one of the 28 Arabic lunar mansions.

    RITE OF PURPOSE:
        Serves the Manazil Engine as the static definition record for each
        mansion in the ``MANSIONS`` table. Without this vessel, the mansion
        table would be an untyped list of tuples, making field access fragile
        and signification lookup impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store all six definitional fields for one mansion.
        Non-responsibilities:
            - Does not compute positions or perform any arithmetic.
            - Does not validate that ``index`` is in [1, 28].
        Dependencies:
            - Instantiated at module load time to populate ``MANSIONS``.
        Structural invariants:
            - ``index`` is always in [1, 28].
            - ``nature`` is always "Fortunate", "Unfortunate", or "Mixed".
        Succession stance: terminal — not designed for subclassing.

    Canon: al-Biruni, "Book of Instruction in the Elements of the Art of
           Astrology" (1029 CE); Agrippa, "Three Books of Occult Philosophy"
           (1531); Ibn Ezra, "The Book of the World" (12th c.).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.manazil.MansionInfo",
        "risk": "low",
        "api": {
            "public_methods": [],
            "public_attributes": [
                "index", "arabic_name", "latin_name",
                "ruling_star", "nature", "signification"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "index", "arabic_name", "latin_name",
                "ruling_star", "nature", "signification"
            ]
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
            "policy": "no runtime failures — static definition record"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    index: int
    arabic_name: str
    latin_name: str
    ruling_star: str
    nature: str
    signification: str


# ---------------------------------------------------------------------------
# The 28-mansion table
# ---------------------------------------------------------------------------

MANSIONS: list[MansionInfo] = [
    MansionInfo(1,  "Al-Sharatain",      "Alnath",       "Beta Arietis",          "Mixed",       "Journeys, harvests, new beginnings"),
    MansionInfo(2,  "Al-Butain",         "Albotain",     "Epsilon Arietis",       "Fortunate",   "Finding lost things, treasure"),
    MansionInfo(3,  "Al-Thurayya",       "Alcyone",      "Pleiades",              "Fortunate",   "Safe travel by sea"),
    MansionInfo(4,  "Al-Dabaran",        "Aldebaran",    "Aldebaran",             "Unfortunate", "Strife, discord, contention"),
    MansionInfo(5,  "Al-Haq'a",          "Albucca",      "Lambda Orionis",        "Fortunate",   "Favor of kings, swift travel"),
    MansionInfo(6,  "Al-Han'a",          "Athena",       "Mu Geminorum",          "Unfortunate", "Hunting, enmity, captivity"),
    MansionInfo(7,  "Al-Dhira",          "Aldirah",      "Alpha Geminorum",       "Fortunate",   "Gain, friendship, health"),
    MansionInfo(8,  "Al-Nathra",         "Alnaza",       "Praesepe (Beehive)",    "Mixed",       "Love, healing, liberation"),
    MansionInfo(9,  "Al-Tarf",           "Atarf",        "Kappa Cancri",          "Unfortunate", "Ruin of harvests, hindrances"),
    MansionInfo(10, "Al-Jabhah",         "Algebha",      "Zeta Leonis",           "Fortunate",   "Strongholds, victory, love"),
    MansionInfo(11, "Al-Zubra",          "Azobra",       "Delta Leonis",          "Fortunate",   "Gain, kindness, abundance"),
    MansionInfo(12, "Al-Sarfah",         "Assarfah",     "Beta Leonis (Denebola)", "Mixed",      "Journey, travel, changes"),
    MansionInfo(13, "Al-'Awwa",          "Alhaire",      "Beta Virginis",         "Fortunate",   "Traders, harvests, gain"),
    MansionInfo(14, "Al-Simak",          "Azimech",      "Spica",                 "Fortunate",   "Abundance, harvests, honor"),
    MansionInfo(15, "Al-Ghafr",          "Aigebha",      "Iota Virginis",         "Fortunate",   "Digging, finding treasure"),
    MansionInfo(16, "Al-Zubana",         "Azubene",      "Alpha Librae",          "Unfortunate", "Trade loss, hindrances"),
    MansionInfo(17, "Al-Iklil",          "Aclil",        "Beta Scorpii",          "Fortunate",   "Good fortune, blessing"),
    MansionInfo(18, "Al-Qalb",           "Alcab",        "Antares",               "Unfortunate", "Illness, evil, captivity"),
    MansionInfo(19, "Al-Shawla",         "Axaulah",      "Lambda Scorpii",        "Mixed",       "Swift travel, reconciliation"),
    MansionInfo(20, "Al-Na'am",          "Nahaym",       "Sigma Sagittarii",      "Fortunate",   "Taming, domestication, hunting"),
    MansionInfo(21, "Al-Baldah",         "Albeldah",     "Pi Sagittarii",         "Mixed",       "Ruin, loneliness"),
    MansionInfo(22, "Sa'd al-Dhabih",    "Caadaldeba",   "Alpha Capricorni",      "Fortunate",   "Captives freed, cures illness"),
    MansionInfo(23, "Sa'd Bula",         "Caad Abola",   "Mu Aquarii",            "Fortunate",   "Sickness cured, healing"),
    MansionInfo(24, "Sa'd al-Su'ud",     "Caad Acohot",  "Beta Aquarii",          "Fortunate",   "Marriage, favor, honor"),
    MansionInfo(25, "Sa'd al-Akhbiya",   "Caad Angue",   "Gamma Aquarii",         "Mixed",       "Agriculture, building, gain"),
    MansionInfo(26, "Al-Fargh al-Awwal", "Alpharg",      "Alpha Pegasi",          "Mixed",       "Travel, union, fortune"),
    MansionInfo(27, "Al-Fargh al-Thani", "Alcharya",     "Gamma Pegasi",          "Fortunate",   "Good news, union, peace"),
    MansionInfo(28, "Batn al-Hut",       "Arrexhe",      "Beta Andromedae",       "Fortunate",   "Fish, travel by sea, marriage"),
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MansionPosition:
    """
    RITE: The Station Vessel — a body's place in the lunar mansion cycle.

    THEOREM: Holds the ``MansionInfo`` record, degrees elapsed within the
    mansion, and the original ecliptic longitude for a single body's mansion
    position result.

    RITE OF PURPOSE:
        Serves the Manazil Engine as the canonical result vessel for mansion
        position computations. Without this vessel, ``mansion_of`` would
        return a bare ``MansionInfo`` with no degree-within-mansion context,
        making electional timing and degree-precise analysis impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store the ``MansionInfo`` for the matched mansion.
            - Store the degrees elapsed within the mansion (0 to MANSION_SPAN).
            - Store the original ecliptic longitude for traceability.
        Non-responsibilities:
            - Does not compute the mansion (delegated to ``mansion_of``).
            - Does not validate that ``degrees_in`` is within [0, MANSION_SPAN).
        Dependencies:
            - Populated exclusively by ``mansion_of()``.
        Structural invariants:
            - ``degrees_in`` is always in [0, MANSION_SPAN).
            - ``mansion`` always references a valid entry from ``MANSIONS``.
        Succession stance: terminal — not designed for subclassing.

    Canon: al-Biruni, "Book of Instruction in the Elements of the Art of
           Astrology" (1029 CE).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.manazil.MansionPosition",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": ["mansion", "degrees_in", "longitude"]
        },
        "state": {
            "mutable": false,
            "fields": ["mansion", "degrees_in", "longitude"]
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
            "policy": "no runtime failures — result vessel only"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    mansion:    MansionInfo
    degrees_in: float    # degrees elapsed within the mansion (0–12.857°)
    longitude:  float    # original ecliptic longitude

    def __repr__(self) -> str:
        return (
            f"Mansion {self.mansion.index:>2} — {self.mansion.arabic_name} "
            f"({self.mansion.latin_name})  "
            f"{self.degrees_in:.4f}° in  "
            f"[{self.mansion.nature}]  {self.mansion.signification}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def mansion_of(longitude: float) -> MansionPosition:
    """
    Return the Arabic mansion for a given ecliptic longitude.

    Parameters
    ----------
    longitude : ecliptic longitude in degrees (0–360, tropical)

    Returns
    -------
    MansionPosition with mansion details and degrees elapsed within it
    """
    lon = longitude % 360.0
    index_0 = int(lon / MANSION_SPAN)          # 0-based, 0–27
    index_0 = min(index_0, 27)                 # clamp for exactly 360.0
    degrees_in = lon - index_0 * MANSION_SPAN
    return MansionPosition(
        mansion=MANSIONS[index_0],
        degrees_in=degrees_in,
        longitude=longitude,
    )


def all_mansions_at(positions: dict[str, float]) -> dict[str, MansionPosition]:
    """
    Compute Arabic mansion positions for all bodies.

    Parameters
    ----------
    positions : dict mapping body name → ecliptic longitude (degrees)

    Returns
    -------
    dict mapping body name → MansionPosition
    """
    return {body: mansion_of(lon) for body, lon in positions.items()}


def moon_mansion(moon_longitude: float) -> MansionPosition:
    """
    Convenience: return the mansion of the Moon.

    Parameters
    ----------
    moon_longitude : Moon's ecliptic longitude (degrees)

    Returns
    -------
    MansionPosition for the Moon
    """
    return mansion_of(moon_longitude)


# ---------------------------------------------------------------------------
# Sidereal mansion computation
# ---------------------------------------------------------------------------

def mansion_of_sidereal(
    tropical_longitude: float,
    jd: float,
    ayanamsa_system: str = "Lahiri",
    ayanamsa_mode: str = "true",
) -> MansionPosition:
    """
    Return the Arabic mansion for a tropical longitude, converted to sidereal.

    Parameters
    ----------
    tropical_longitude : ecliptic longitude in degrees (tropical)
    jd                 : Julian Day (UT) for ayanamsa computation
    ayanamsa_system    : ayanamsa system name (default "Lahiri")
    ayanamsa_mode      : "true" or "mean" (default "true")

    Returns
    -------
    MansionPosition computed from the sidereal longitude.
    The ``longitude`` field carries the original tropical value for traceability.
    """
    from .sidereal import tropical_to_sidereal

    sid_lon = tropical_to_sidereal(tropical_longitude, jd, ayanamsa_system, ayanamsa_mode)
    lon = sid_lon % 360.0
    index_0 = int(lon / MANSION_SPAN)
    index_0 = min(index_0, 27)
    degrees_in = lon - index_0 * MANSION_SPAN
    return MansionPosition(
        mansion=MANSIONS[index_0],
        degrees_in=degrees_in,
        longitude=tropical_longitude,
    )


def all_mansions_at_sidereal(
    positions: dict[str, float],
    jd: float,
    ayanamsa_system: str = "Lahiri",
    ayanamsa_mode: str = "true",
) -> dict[str, MansionPosition]:
    """
    Compute sidereal Arabic mansion positions for all bodies.

    Parameters
    ----------
    positions       : dict mapping body name to tropical ecliptic longitude
    jd              : Julian Day (UT) for ayanamsa computation
    ayanamsa_system : ayanamsa system name (default "Lahiri")
    ayanamsa_mode   : "true" or "mean" (default "true")

    Returns
    -------
    dict mapping body name to MansionPosition (sidereal).
    """
    return {
        body: mansion_of_sidereal(lon, jd, ayanamsa_system, ayanamsa_mode)
        for body, lon in positions.items()
    }


# ---------------------------------------------------------------------------
# Textual tradition variants
# ---------------------------------------------------------------------------
#
# The 28-mansion equal division is shared across all Arabic traditions.
# What differs is the attribution: the nature (Fortunate / Unfortunate /
# Mixed), the signification, and the talismanic or angelic associations.
#
# The default MANSIONS table follows al-Biruni / Ibn Ezra.  The variant
# tables below record natures and significations from four additional
# major authorities.  Computational boundaries are unchanged.
#
# Authority:
#   Abenragel    — Haly Abenragel, *Liber de Judiciis Stellarum* (11th c.)
#   Ibn al-Arabi — Muhyiddin Ibn al-Arabi, *al-Futuhat al-Makkiyya* (13th c.)
#   Agrippa      — Heinrich Cornelius Agrippa, *Three Books of Occult
#                  Philosophy* (1531)
#   Picatrix     — *Ghayat al-Hakim* / *Picatrix* (10th–11th c.)
# ---------------------------------------------------------------------------

class MansionTradition(str, Enum):
    """Selectable textual tradition for mansion attributions."""

    AL_BIRUNI   = "al_biruni"     # default (the MANSIONS table)
    ABENRAGEL   = "abenragel"
    IBN_ALARABI = "ibn_alarabi"
    AGRIPPA     = "agrippa"
    PICATRIX    = "picatrix"


# Each variant table is a dict mapping mansion index (1–28) to
# (nature, signification).  Only entries that differ materially from the
# al-Biruni default are listed; missing entries fall back to al-Biruni.

_ABENRAGEL_VARIANTS: dict[int, tuple[str, str]] = {
    1:  ("Fortunate",   "Opening works, journeys, taking medicine"),
    2:  ("Fortunate",   "Finding treasure, sowing, reconciliation"),
    3:  ("Fortunate",   "Good for alchemy, hunting, sailing"),
    4:  ("Unfortunate", "Destruction, discord, separation"),
    5:  ("Fortunate",   "Return of the absent, favor of the powerful"),
    6:  ("Unfortunate", "Siege, war, obstruction of works"),
    7:  ("Fortunate",   "Commerce, friendship, planting"),
    8:  ("Fortunate",   "Love, brotherhood, travel"),
    9:  ("Unfortunate", "Harm, illness, obstruction"),
    10: ("Fortunate",   "Strength, fortification, love"),
    11: ("Fortunate",   "Commerce, gain, favor of the powerful"),
    12: ("Mixed",       "Separation, change of condition"),
    13: ("Fortunate",   "Commerce, harvest, planting"),
    14: ("Fortunate",   "Marriage, healing, profit"),
    15: ("Fortunate",   "Wells, digging, treasure"),
    16: ("Unfortunate", "Hindering journeys, loss in trade"),
    17: ("Fortunate",   "Building, planting, good fortune"),
    18: ("Unfortunate", "War, captivity, discord"),
    19: ("Mixed",       "Taming beasts, reconciliation, swift travel"),
    20: ("Fortunate",   "Taming, hunting, domestication"),
    21: ("Unfortunate", "Destruction, desolation, separation"),
    22: ("Fortunate",   "Healing, freedom, escape from captivity"),
    23: ("Fortunate",   "Healing, medicine, cures"),
    24: ("Fortunate",   "Love, marriage, favor"),
    25: ("Mixed",       "Building, gain, agriculture"),
    26: ("Mixed",       "Union, love, travel"),
    27: ("Fortunate",   "Commerce, gain, peace"),
    28: ("Fortunate",   "Sea travel, fishing, marriage"),
}

_IBN_ALARABI_VARIANTS: dict[int, tuple[str, str]] = {
    1:  ("Mixed",       "Divine Name: al-Rabb; beginning of creation, divine initiative"),
    2:  ("Fortunate",   "Divine Name: al-Badi'; revelation of hidden things"),
    3:  ("Fortunate",   "Divine Name: al-Musawwir; divine beauty and form"),
    4:  ("Unfortunate", "Divine Name: al-Qahhar; severity and breaking"),
    5:  ("Fortunate",   "Divine Name: al-Nur; illumination and guidance"),
    6:  ("Unfortunate", "Divine Name: al-Mumit; death and constriction"),
    7:  ("Fortunate",   "Divine Name: al-Muhyi; life and restoration"),
    8:  ("Mixed",       "Divine Name: al-Rauf; tenderness and compassion"),
    9:  ("Unfortunate", "Divine Name: al-Darr; affliction and harm"),
    10: ("Fortunate",   "Divine Name: al-Aziz; power and dignity"),
    11: ("Fortunate",   "Divine Name: al-Ghani; self-sufficiency and abundance"),
    12: ("Mixed",       "Divine Name: al-Muqit; transformation and nourishment"),
    13: ("Fortunate",   "Divine Name: al-Razzaq; provision and sustenance"),
    14: ("Fortunate",   "Divine Name: al-Shakur; gratitude and increase"),
    15: ("Fortunate",   "Divine Name: al-Hafiz; protection and preservation"),
    16: ("Unfortunate", "Divine Name: al-Mudhill; abasement and testing"),
    17: ("Fortunate",   "Divine Name: al-Wahhab; bestowal and grace"),
    18: ("Unfortunate", "Divine Name: al-Muntaqim; retribution and justice"),
    19: ("Mixed",       "Divine Name: al-Sari'; swiftness and movement"),
    20: ("Fortunate",   "Divine Name: al-Latif; subtlety and gentleness"),
    21: ("Unfortunate", "Divine Name: al-Khafid; lowering and humbling"),
    22: ("Fortunate",   "Divine Name: al-Jabbar; mending and restoration"),
    23: ("Fortunate",   "Divine Name: al-Shafi; healing and remedy"),
    24: ("Fortunate",   "Divine Name: al-Wadud; divine love and intimacy"),
    25: ("Mixed",       "Divine Name: al-Bani; construction and building"),
    26: ("Mixed",       "Divine Name: al-Jami'; union and gathering"),
    27: ("Fortunate",   "Divine Name: al-Salam; peace and completion"),
    28: ("Fortunate",   "Divine Name: al-Wasi'; comprehension and expanse"),
}

_AGRIPPA_VARIANTS: dict[int, tuple[str, str]] = {
    1:  ("Mixed",       "Destruction of one, profit of another; journeys"),
    2:  ("Fortunate",   "Finding treasure, retaining captives"),
    3:  ("Fortunate",   "Profitable to sailors, hunters, alchemists"),
    4:  ("Unfortunate", "Revenge, enmity, discord, sedition"),
    5:  ("Fortunate",   "Favor of kings, return of travelers"),
    6:  ("Unfortunate", "Hunting, besieging cities, revenge of princes"),
    7:  ("Fortunate",   "Gain, friendship, love, profitable to lovers"),
    8:  ("Fortunate",   "Love, friendship; profitable for travel"),
    9:  ("Unfortunate", "Hindering harvest, travelers, destroying ships"),
    10: ("Fortunate",   "Strengthening buildings, promoting love"),
    11: ("Fortunate",   "Voyages, gain by merchandise, redemption of captives"),
    12: ("Mixed",       "Separation of lovers; destroying houses, enemies"),
    13: ("Fortunate",   "Benevolent for harvest, trade, and journeys"),
    14: ("Fortunate",   "Favor of married people, curing the sick"),
    15: ("Fortunate",   "Profitable for extracting treasure, digging wells"),
    16: ("Unfortunate", "Hindering journeys and weddings"),
    17: ("Fortunate",   "Improving fortune, safe buildings"),
    18: ("Unfortunate", "Causing discord, infirmity, plotting against enemies"),
    19: ("Mixed",       "Facilitating escape and deliveries"),
    20: ("Fortunate",   "Taming beasts, strengthening prisons"),
    21: ("Unfortunate", "Destruction and waste"),
    22: ("Fortunate",   "Curing infirmity, freeing captives"),
    23: ("Fortunate",   "Curing ailments, profitable for benevolence"),
    24: ("Fortunate",   "Conjugal goodwill, victory of soldiers"),
    25: ("Mixed",       "Protecting trees and harvests"),
    26: ("Mixed",       "Uniting lovers, destroying enemies' wealth"),
    27: ("Fortunate",   "Increasing commerce, gain"),
    28: ("Fortunate",   "Increasing harvests, multiplying goods"),
}

_PICATRIX_VARIANTS: dict[int, tuple[str, str]] = {
    1:  ("Mixed",       "Talisman for safe travel; image of a black man with a lance"),
    2:  ("Fortunate",   "Talisman against wrath; image of a crowned king"),
    3:  ("Fortunate",   "Talisman for safe voyages; image of a woman with right hand raised"),
    4:  ("Unfortunate", "Talisman for destruction; image of a soldier on horseback"),
    5:  ("Fortunate",   "Talisman for favor; image of a head with no body"),
    6:  ("Unfortunate", "Talisman for destruction; image of a man sitting on a chair"),
    7:  ("Fortunate",   "Talisman for gain; image of a man clothed in robes"),
    8:  ("Fortunate",   "Talisman for love; image of an eagle with a man's face"),
    9:  ("Unfortunate", "Talisman for harm and sickness; image of a man with no right hand"),
    10: ("Fortunate",   "Talisman for love and strength; image of a lion's head"),
    11: ("Fortunate",   "Talisman for commerce; image of a man on a horse"),
    12: ("Mixed",       "Talisman for separation; image of a dragon biting its tail"),
    13: ("Fortunate",   "Talisman for trade and harvest; image of a man with hands raised"),
    14: ("Fortunate",   "Talisman for love between married; image of a dog biting its paw"),
    15: ("Fortunate",   "Talisman for treasure; image of a man sitting with hands at heart"),
    16: ("Unfortunate", "Talisman for hindrance; image of a man sitting on a chair, holding scales"),
    17: ("Fortunate",   "Talisman for fortune; image of an ape"),
    18: ("Unfortunate", "Talisman for discord; image of a snake with its tail above its head"),
    19: ("Mixed",       "Talisman for safe escape; image of a woman holding her hands to her face"),
    20: ("Fortunate",   "Talisman for taming; image of a man with hands cut off"),
    21: ("Unfortunate", "Talisman for destruction; image of a man with two faces"),
    22: ("Fortunate",   "Talisman for healing; image of a man with head in his hands"),
    23: ("Fortunate",   "Talisman for curing; image of a cat with a dog's head"),
    24: ("Fortunate",   "Talisman for love; image of a woman nursing a child"),
    25: ("Mixed",       "Talisman for protection of trees; image of a man planting"),
    26: ("Mixed",       "Talisman for love and union; image of a woman combing hair"),
    27: ("Fortunate",   "Talisman for gain; image of a man with wings, holding a vessel"),
    28: ("Fortunate",   "Talisman for increase; image of a fish"),
}

_VARIANT_TABLES: dict[MansionTradition, dict[int, tuple[str, str]]] = {
    MansionTradition.ABENRAGEL:   _ABENRAGEL_VARIANTS,
    MansionTradition.IBN_ALARABI: _IBN_ALARABI_VARIANTS,
    MansionTradition.AGRIPPA:     _AGRIPPA_VARIANTS,
    MansionTradition.PICATRIX:    _PICATRIX_VARIANTS,
}


def variant_nature(mansion_index: int, tradition: MansionTradition) -> str:
    """
    Return the nature of a mansion according to a specific tradition.

    Parameters
    ----------
    mansion_index : mansion number (1--28)
    tradition     : which textual tradition to consult

    Returns
    -------
    "Fortunate", "Unfortunate", or "Mixed".
    Falls back to al-Biruni default if the tradition has no override.
    """
    if mansion_index < 1 or mansion_index > 28:
        raise ValueError(f"mansion_index must be 1--28, got {mansion_index}")

    if tradition is MansionTradition.AL_BIRUNI:
        return MANSIONS[mansion_index - 1].nature

    table = _VARIANT_TABLES.get(tradition)
    if table and mansion_index in table:
        return table[mansion_index][0]
    return MANSIONS[mansion_index - 1].nature


def variant_signification(mansion_index: int, tradition: MansionTradition) -> str:
    """
    Return the signification of a mansion according to a specific tradition.

    Parameters
    ----------
    mansion_index : mansion number (1--28)
    tradition     : which textual tradition to consult

    Returns
    -------
    Signification string.
    Falls back to al-Biruni default if the tradition has no override.
    """
    if mansion_index < 1 or mansion_index > 28:
        raise ValueError(f"mansion_index must be 1--28, got {mansion_index}")

    if tradition is MansionTradition.AL_BIRUNI:
        return MANSIONS[mansion_index - 1].signification

    table = _VARIANT_TABLES.get(tradition)
    if table and mansion_index in table:
        return table[mansion_index][1]
    return MANSIONS[mansion_index - 1].signification

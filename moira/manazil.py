"""
Moira — Manazil Engine
=======================

Archetype: Engine

Purpose
-------
Governs computation of Arabic Lunar Mansion (Manazil al-Qamar) positions,
mapping any ecliptic longitude to one of the 28 equal stations of the Moon
together with their traditional significations.

Boundary declaration
--------------------
Owns: the 28-mansion table, mansion span arithmetic, ``MansionInfo`` and
      ``MansionPosition`` result vessels.
Delegates: nothing — all computation is self-contained.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure arithmetic over
ecliptic longitudes.

Public surface
--------------
``MansionInfo``       — immutable record for one of the 28 mansion definitions.
``MansionPosition``   — vessel for a body's mansion position result.
``MANSIONS``          — ordered list of all 28 ``MansionInfo`` records.
``MANSION_SPAN``      — degrees per mansion (360/28).
``mansion_of``        — compute mansion for a single ecliptic longitude.
``all_mansions_at``   — compute mansions for a dict of body positions.
``moon_mansion``      — convenience wrapper for the Moon's mansion.
"""

from dataclasses import dataclass

__all__ = [
    "MansionInfo",
    "MansionPosition",
    "MANSIONS",
    "MANSION_SPAN",
    "mansion_of",
    "all_mansions_at",
    "moon_mansion",
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

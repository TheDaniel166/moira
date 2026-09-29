"""
Moira — Manazil Engine
=======================

Archetype: Engine

Purpose
-------
Governs computation of Arabic Lunar Mansion (Manazil al-Qamar) positions.
Supports equal division traditions (Agrippa, Picatrix) and catalogues the
unequal star-based tradition (al-Biruni).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "AstronomicalMansion",
    "ElectionalMansion",
    "MansionPosition",
    "MansionTradition",
    "AL_BIRUNI_MANSIONS",
    "AGRIPPA_MANSIONS",
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
class AstronomicalMansion:
    """One mansion of the star-based (al-Biruni) tradition: its number, Arabic name and marker stars."""

    index: int
    arabic_name: str
    marker_stars: tuple[str, ...]

@dataclass(slots=True)
class ElectionalMansion:
    """One mansion of an electional tradition: its number, Latin name, nature and signification."""

    index: int
    latin_name: str
    nature: str
    signification: str

AL_BIRUNI_MANSIONS: list[AstronomicalMansion] = [
    AstronomicalMansion(1,  "Al-Sharatain",      ("bet Ari", "gam Ari")),
    AstronomicalMansion(2,  "Al-Butain",         ("del Ari", "rho Ari")),
    AstronomicalMansion(3,  "Al-Thurayya",       ("eta Tau",)), 
    AstronomicalMansion(4,  "Al-Dabaran",        ("alf Tau",)),
    AstronomicalMansion(5,  "Al-Haq'a",          ("lam Ori",)),
    AstronomicalMansion(6,  "Al-Han'a",          ("gam Gem", "xi Gem")),
    AstronomicalMansion(7,  "Al-Dhira",          ("alf Gem", "bet Gem")),
    AstronomicalMansion(8,  "Al-Nathra",         ("del Cnc", "gam Cnc")),
    AstronomicalMansion(9,  "Al-Tarf",           ("lam Leo", "kap Cnc")),
    AstronomicalMansion(10, "Al-Jabhah",         ("zet Leo", "gam Leo", "eta Leo", "alf Leo")),
    AstronomicalMansion(11, "Al-Zubra",          ("del Leo", "thet Leo")),
    AstronomicalMansion(12, "Al-Sarfah",         ("bet Leo",)),
    AstronomicalMansion(13, "Al-'Awwa",          ("bet Vir", "eta Vir", "gam Vir", "del Vir", "eps Vir")),
    AstronomicalMansion(14, "Al-Simak",          ("alf Vir",)),
    AstronomicalMansion(15, "Al-Ghafr",          ("iot Vir", "kap Vir", "lam Vir")),
    AstronomicalMansion(16, "Al-Zubana",         ("alf02 Lib", "bet Lib")),
    AstronomicalMansion(17, "Al-Iklil",          ("bet01 Sco", "del Sco", "pi. Sco")),
    AstronomicalMansion(18, "Al-Qalb",           ("alf Sco",)),
    AstronomicalMansion(19, "Al-Shawla",         ("lam Sco", "ups Sco")),
    AstronomicalMansion(20, "al-Naʿāʾim",        ("gam02 Sgr", "del Sgr", "eps Sgr", "eta Sgr", "sig Sgr", "phi Sgr", "tau Sgr", "zet Sgr")),
    AstronomicalMansion(21, "Al-Baldah",         ("pi. Sgr",)),
    AstronomicalMansion(22, "Sa'd al-Dhabih",    ("alf02 Cap", "bet01 Cap")),
    AstronomicalMansion(23, "Sa'd Bula",         ("mu. Aqr", "eps Aqr", "nu Aqr")),
    AstronomicalMansion(24, "Sa'd al-Su'ud",     ("bet Aqr", "xi Aqr")),
    AstronomicalMansion(25, "Sa'd al-Akhbiya",   ("gam Aqr", "pi. Aqr", "zet Aqr", "eta Aqr")),
    AstronomicalMansion(26, "Al-Fargh al-Awwal", ("alf Peg", "bet Peg")),
    AstronomicalMansion(27, "Al-Fargh al-Thani", ("gam Peg", "alf And")),
    AstronomicalMansion(28, "Batn al-Hut",       ("bet And",)),
]

AGRIPPA_MANSIONS: list[ElectionalMansion] = [
    ElectionalMansion(1,  "Alnath",       "Mixed",       "Destruction of one, profit of another; journeys"),
    ElectionalMansion(2,  "Albotain",     "Fortunate",   "Finding treasure, retaining captives"),
    ElectionalMansion(3,  "Athoray",      "Fortunate",   "Profitable to sailors, hunters, alchemists"),
    ElectionalMansion(4,  "Aldebaran",    "Unfortunate", "Revenge, enmity, discord, sedition"),
    ElectionalMansion(5,  "Albothayn",    "Fortunate",   "Favor of kings, return of travelers"),
    ElectionalMansion(6,  "Athaya",       "Unfortunate", "Hunting, besieging cities, revenge of princes"),
    ElectionalMansion(7,  "Aldirah",      "Fortunate",   "Gain, friendship, love, profitable to lovers"),
    ElectionalMansion(8,  "Alnaza",       "Fortunate",   "Love, friendship; profitable for travel"),
    ElectionalMansion(9,  "Atarf",        "Unfortunate", "Hindering harvest, travelers, destroying ships"),
    ElectionalMansion(10, "Algebha",      "Fortunate",   "Strengthening buildings, promoting love"),
    ElectionalMansion(11, "Azobra",       "Fortunate",   "Voyages, gain by merchandise, redemption of captives"),
    ElectionalMansion(12, "Assarfah",     "Mixed",       "Separation of lovers; destroying houses, enemies"),
    ElectionalMansion(13, "Alhaire",      "Fortunate",   "Benevolent for harvest, trade, and journeys"),
    ElectionalMansion(14, "Azimech",      "Fortunate",   "Favor of married people, curing the sick"),
    ElectionalMansion(15, "Algafra",      "Fortunate",   "Profitable for extracting treasure, digging wells"),
    ElectionalMansion(16, "Azubene",      "Unfortunate", "Hindering journeys and weddings"),
    ElectionalMansion(17, "Aclil",        "Fortunate",   "Improving fortune, safe buildings"),
    ElectionalMansion(18, "Alcab",        "Unfortunate", "Causing discord, infirmity, plotting against enemies"),
    ElectionalMansion(19, "Axaulah",      "Mixed",       "Facilitating escape and deliveries"),
    ElectionalMansion(20, "Nahaym",       "Fortunate",   "Taming beasts, strengthening prisons"),
    ElectionalMansion(21, "Albeldah",     "Unfortunate", "Destruction and waste"),
    ElectionalMansion(22, "Caadaldeba",   "Fortunate",   "Curing infirmity, freeing captives"),
    ElectionalMansion(23, "Caad Abola",   "Fortunate",   "Curing ailments, profitable for benevolence"),
    ElectionalMansion(24, "Caad Acohot",  "Fortunate",   "Conjugal goodwill, victory of soldiers"),
    ElectionalMansion(25, "Sadalachbia",  "Mixed",       "Protecting trees and harvests"),
    ElectionalMansion(26, "Alpharg",      "Mixed",       "Uniting lovers, destroying enemies' wealth"),
    ElectionalMansion(27, "Alcharya",     "Fortunate",   "Increasing commerce, gain"),
    ElectionalMansion(28, "Arrexhe",      "Fortunate",   "Increasing harvests, multiplying goods"),
]

@dataclass(slots=True)
class MansionPosition:
    """The mansion a longitude falls in, with the degrees already travelled into it."""

    mansion:    ElectionalMansion
    degrees_in: float
    longitude:  float

    def __repr__(self) -> str:
        return (
            f"Mansion {self.mansion.index:>2} — {self.mansion.latin_name} "
            f"{self.degrees_in:.4f}° in  "
            f"[{self.mansion.nature}]  {self.mansion.signification}"
        )


class MansionTradition(str, Enum):
    """Which mansion tradition to use: the star-based al-Biruni scheme or an electional one."""

    AL_BIRUNI   = "al_biruni"     
    ABENRAGEL   = "abenragel"
    IBN_ALARABI = "ibn_alarabi"
    AGRIPPA     = "agrippa"
    PICATRIX    = "picatrix"

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

_PICATRIX_VARIANTS: dict[int, tuple[str, str]] = {
    1:  ("Mixed",       "Talisman for safe travel; image of a black man with a lance"),
    2:  ("Unfortunate", "Talisman for destruction and removal of anger; image of a crowned king"),
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
    15: ("Unfortunate", "Talisman for hindrance of travel and marriage; image of a man sitting with hands at heart"),
    16: ("Unfortunate", "Talisman for hindrance; image of a man sitting on a chair, holding scales"),
    17: ("Fortunate",   "Talisman for fortune; image of an ape"),
    18: ("Fortunate",   "Talisman for protecting houses and healing fevers; image of a snake with its tail above its head"),
    19: ("Mixed",       "Talisman for safe escape; image of a woman holding her hands to her face"),
    20: ("Fortunate",   "Talisman for taming; image of a man with hands cut off"),
    21: ("Unfortunate", "Talisman for destruction; image of a man with two faces"),
    22: ("Fortunate",   "Talisman for healing; image of a man with head in his hands"),
    23: ("Fortunate",   "Talisman for curing; image of a cat with a dog's head"),
    24: ("Fortunate",   "Talisman for love; image of a woman nursing a child"),
    25: ("Mixed",       "Talisman for protection of trees; image of a man planting"),
    26: ("Mixed",       "Talisman for love and union; image of a woman combing hair"),
    27: ("Unfortunate", "Talisman for the destruction of springs and wells; image of a man with wings, holding a vessel"),
    28: ("Fortunate",   "Talisman for increase; image of a fish"),
}

_VARIANT_TABLES: dict[MansionTradition, dict[int, tuple[str, str]]] = {
    MansionTradition.ABENRAGEL:   _ABENRAGEL_VARIANTS,
    MansionTradition.IBN_ALARABI: _IBN_ALARABI_VARIANTS,
    MansionTradition.AGRIPPA:     {},
    MansionTradition.PICATRIX:    _PICATRIX_VARIANTS,
}

def variant_nature(mansion_index: int, tradition: MansionTradition) -> str:
    if mansion_index < 1 or mansion_index > 28:
        raise ValueError(f"mansion_index must be 1--28, got {mansion_index}")
    if tradition is MansionTradition.AL_BIRUNI:
        raise ValueError("al-Biruni star-based tradition does not support electional natures.")
    table = _VARIANT_TABLES.get(tradition)
    if table and mansion_index in table:
        return table[mansion_index][0]
    return AGRIPPA_MANSIONS[mansion_index - 1].nature

from functools import lru_cache

@lru_cache(maxsize=16)
def _al_biruni_boundaries(jd: float) -> tuple[float, ...]:
    from .stars import star_at
    from .julian import utc_to_tt
    jd_tt = utc_to_tt(jd)
    boundaries = []
    for m in AL_BIRUNI_MANSIONS:
        primary_star_name = m.marker_stars[0]
        s = star_at(primary_star_name, jd_tt)
        boundaries.append(s.longitude % 360.0)
    return tuple(boundaries)

def variant_signification(mansion_index: int, tradition: MansionTradition) -> str:
    if mansion_index < 1 or mansion_index > 28:
        raise ValueError(f"mansion_index must be 1--28, got {mansion_index}")
    if tradition is MansionTradition.AL_BIRUNI:
        raise ValueError("al-Biruni star-based tradition does not support electional significations.")
    table = _VARIANT_TABLES.get(tradition)
    if table and mansion_index in table:
        return table[mansion_index][1]
    return AGRIPPA_MANSIONS[mansion_index - 1].signification

def mansion_of(longitude: float, tradition: MansionTradition = MansionTradition.AGRIPPA, jd: float | None = None) -> MansionPosition:
    lon = longitude % 360.0

    if tradition == MansionTradition.AL_BIRUNI:
        if jd is None:
            raise ValueError("al-Biruni star-based tradition requires jd to calculate stellar boundaries")
        boundaries = _al_biruni_boundaries(jd)
        index_0 = 27
        degrees_in = 0.0
        for i in range(28):
            start = boundaries[i]
            end = boundaries[(i + 1) % 28]
            span = (end - start) % 360.0
            dist = (lon - start) % 360.0
            if dist < span:
                index_0 = i
                degrees_in = dist
                break
        mansion = AL_BIRUNI_MANSIONS[index_0]
    else:
        index_0 = int(lon / MANSION_SPAN)          
        index_0 = min(index_0, 27)                 
        degrees_in = lon - index_0 * MANSION_SPAN
        mansion = ElectionalMansion(
            index=index_0 + 1,
            latin_name=AGRIPPA_MANSIONS[index_0].latin_name,
            nature=variant_nature(index_0 + 1, tradition),
            signification=variant_signification(index_0 + 1, tradition),
        )

    return MansionPosition(
        mansion=mansion,
        degrees_in=degrees_in,
        longitude=longitude,
    )

def all_mansions_at(positions: dict[str, float], tradition: MansionTradition = MansionTradition.AGRIPPA, jd: float | None = None) -> dict[str, MansionPosition]:
    return {body: mansion_of(lon, tradition, jd=jd) for body, lon in positions.items()}

def moon_mansion(moon_longitude: float, tradition: MansionTradition = MansionTradition.AGRIPPA, jd: float | None = None) -> MansionPosition:
    return mansion_of(moon_longitude, tradition, jd=jd)

def mansion_of_sidereal(
    tropical_longitude: float,
    jd: float,
    ayanamsa_system: str = "Lahiri",
    ayanamsa_mode: str = "true",
    tradition: MansionTradition = MansionTradition.AGRIPPA
) -> MansionPosition:
    from .sidereal import tropical_to_sidereal
    sid_lon = tropical_to_sidereal(tropical_longitude, jd, ayanamsa_system, ayanamsa_mode)
    lon = sid_lon % 360.0

    if tradition == MansionTradition.AL_BIRUNI:
        boundaries = _al_biruni_boundaries(jd)
        sid_boundaries = [tropical_to_sidereal(b, jd, ayanamsa_system, ayanamsa_mode) % 360.0 for b in boundaries]
        
        index_0 = 27
        degrees_in = 0.0
        for i in range(28):
            start = sid_boundaries[i]
            end = sid_boundaries[(i + 1) % 28]
            span = (end - start) % 360.0
            dist = (lon - start) % 360.0
            if dist < span:
                index_0 = i
                degrees_in = dist
                break
        mansion = AL_BIRUNI_MANSIONS[index_0]
    else:
        index_0 = int(lon / MANSION_SPAN)
        index_0 = min(index_0, 27)
        degrees_in = lon - index_0 * MANSION_SPAN
        mansion = ElectionalMansion(
            index=index_0 + 1,
            latin_name=AGRIPPA_MANSIONS[index_0].latin_name,
            nature=variant_nature(index_0 + 1, tradition),
            signification=variant_signification(index_0 + 1, tradition),
        )
    return MansionPosition(
        mansion=mansion,
        degrees_in=degrees_in,
        longitude=tropical_longitude,
    )

def all_mansions_at_sidereal(
    positions: dict[str, float],
    jd: float,
    ayanamsa_system: str = "Lahiri",
    ayanamsa_mode: str = "true",
    tradition: MansionTradition = MansionTradition.AGRIPPA
) -> dict[str, MansionPosition]:
    return {
        body: mansion_of_sidereal(lon, jd, ayanamsa_system, ayanamsa_mode, tradition)
        for body, lon in positions.items()
    }

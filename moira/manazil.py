"""
Moira — Manazil Engine
=======================

Archetype: Engine

Purpose
-------
Governs computation of Arabic Lunar Mansion (Manazil al-Qamar) positions.

Every tradition here divides the zodiac into 28 equal mansions of
360/28 = 12°51′25.7″, counted from 0° of the zodiac in use (tropical, or
sidereal through ``mansion_of_sidereal``). The traditions differ only in the
names and meanings they attach to each mansion.

Sources
-------
- al-Bīrūnī, *Book of Instruction in the Elements of the Art of Astrology*
  (Wright 1934), §164 (begins p. 81). The Moon's path among the fixed stars is divided into
  daily stations, as the zodiac is divided into twelve equal signs, and the
  stations "begin as in the case of the Sun at the Vernal Equinox". The stars
  he describes for each station *mark* it and give it its name. §164 gives no
  boundaries set by stars. ``AL_BIRUNI_MANSIONS`` therefore carries his names
  and marker stars as descriptive data, and positions use the equal division.
  (Checked against the Wright 1934 text, archive.org item
  ``ilmetauqeet_gmail_635``, and the transcription of §164 in C. Warnock,
  *The Mansions of the Moon*, 2019, Appendix D.) §§165–166 (from p. 85)
  locate the mansions by stepping from the Pleiades and give about thirteen
  days between the risings of successive mansions; neither they nor §164
  state a mansion length in degrees. The equal 12 6/7° span therefore comes
  from the equal division itself (and from Agrippa below), not from an
  explicit statement by al-Bīrūnī.
- Agrippa, *De occulta philosophia* II.33 (English 1651, J. H. Peterson
  ed., esotericarchives.com): each mansion "containth [sic] twelve degrees, and one
  and fifty minutes, and almost twenty six seconds". Latin names are Agrippa's
  first-named form. His alternatives are in ``latin_aliases``. Agrippa
  places the mansions "in the Zodiack of the eight sphere", the sphere of the
  fixed stars. ``mansion_of`` counts them from tropical 0° Aries.
  ``mansion_of_sidereal`` counts them from a sidereal 0° Aries set by a named
  ayanamsa.
- Picatrix I.4 (Latin, ed. Pingree 1986): Latin names as listed by I. Freer,
  *The Picatrix: Lunar Mansions in Western Astrology*, who worked from
  Pingree's text.

The Bayer designations of the marker stars are the conventional modern
identifications of al-Bīrūnī's descriptions. He describes the stars but does
not use Bayer letters. Only stars that the Moira star catalogue resolves
(``moira.stars.star_name_resolves``) are listed. A mansion's ``note`` names any
star that the catalogue lacks.

In 6.9.8 each ``al_biruni`` mansion started at its first marker star. That
rule had no source, and 6.9.9 removed it.
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
    "PICATRIX_LATIN_NAMES",
    "MANSION_SPAN",
    "electional_mansion",
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

MANSION_SPAN: float = 360.0 / 28   # 12.857142...° = 12°51′25.7″

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AstronomicalMansion:
    """One mansion as al-Bīrūnī lists it: number, Arabic name, other names and marker stars.

    ``marker_stars`` describe the mansion. They mark it in the sky and do not
    set its boundaries. ``note`` qualifies the star list where needed.
    """

    index: int
    arabic_name: str
    marker_stars: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    note: str | None = None

@dataclass(slots=True)
class ElectionalMansion:
    """One mansion of an electional tradition: its number, Latin name, nature and signification."""

    index: int
    latin_name: str
    nature: str
    signification: str
    latin_aliases: tuple[str, ...] = ()

# al-Bīrūnī, Book of Instruction §164 (Wright 1934). The comments paraphrase
# his description of each station. The Bayer designations are modern
# identifications of those descriptions.
AL_BIRUNI_MANSIONS: list[AstronomicalMansion] = [
    # two bright stars on the horns of Aries, in a north-south line
    AstronomicalMansion(1,  "Al-Sharatain",      ("bet Ari", "gam Ari")),
    # three stars from the tail of Aries, in a triangle
    AstronomicalMansion(2,  "Al-Butain",         ("del Ari", "eps Ari A"),
                        note="The third star of the triangle, rho Ari, is not in the Moira star catalogue."),
    # six stars from the shoulder of Taurus (the Pleiades)
    AstronomicalMansion(3,  "Al-Thurayya",       ("eta Tau", "17 Tau", "Taygeta", "20 Tau", "23 Tau", "27 Tau")),
    # the large red star in the eye of Taurus
    AstronomicalMansion(4,  "Al-Dabaran",        ("alf Tau",)),
    # three small stars from the head of Orion, like a trivet
    AstronomicalMansion(5,  "Al-Haq'a",          ("lam Ori", "phi01 Ori", "phi02 Ori")),
    # two small stars from the feet of Gemini
    AstronomicalMansion(6,  "Al-Han'a",          ("gam Gem", "ksi Gem")),
    # two bright stars from the heads of Gemini
    AstronomicalMansion(7,  "Al-Dhira",          ("alf Gem", "bet Gem")),
    # two small stars of Cancer, with the Praesepe between them
    AstronomicalMansion(8,  "Al-Nathra",         ("gam Cnc", "del Cnc")),
    # two stars, one from Leo and one from outside it
    AstronomicalMansion(9,  "Al-Tarf",           ("lam Leo",),
                        note="The second star, kap Cnc, is not in the Moira star catalogue."),
    # four bright stars; the largest and most southerly is Regulus
    AstronomicalMansion(10, "Al-Jabhah",         ("zet Leo", "gam Leo", "eta Leo", "alf Leo")),
    # two stars from the hindquarters of Leo
    AstronomicalMansion(11, "Al-Zubra",          ("del Leo", "tet Leo")),
    # a bright star at the tip of the tail of Leo
    AstronomicalMansion(12, "Al-Sarfah",         ("bet Leo",)),
    # four stars from the breast and wings of Virgo, running north to south
    # and curving at the end like the letter lam
    AstronomicalMansion(13, "Al-'Awwa",          ("bet Vir", "eta Vir", "gam Vir", "del Vir", "eps Vir"),
                        note="al-Biruni counts four stars. The fifth, eps Vir, follows the common modern five-star identification."),
    # Spica
    AstronomicalMansion(14, "Al-Simak",          ("alf Vir",)),
    # two small, inconspicuous stars on the train of Virgo
    AstronomicalMansion(15, "Al-Ghafr",          ("iot Vir", "kap Vir", "lam Vir"),
                        note="al-Biruni counts two stars. The third, lam Vir, follows the common modern three-star identification."),
    # two stars from the scales of Libra
    AstronomicalMansion(16, "Al-Zubana",         ("alf02 Lib", "bet Lib")),
    # three bright stars from the forehead of Scorpius, north-south
    AstronomicalMansion(17, "Al-Iklil",          ("bet01 Sco", "del Sco", "pi. Sco")),
    # Antares, with one star before it and one behind
    AstronomicalMansion(18, "Al-Qalb",           ("alf Sco", "sig Sco", "tau Sco")),
    # the sting of Scorpius: two stars about a span apart
    AstronomicalMansion(19, "Al-Shawla",         ("lam Sco", "ups Sco")),
    # four ostriches going to the river and four returning from it
    AstronomicalMansion(20, "al-Naʿāʾim",        ("gam02 Sgr", "del Sgr", "eps Sgr", "eta Sgr", "sig Sgr", "phi Sgr", "tau Sgr", "zet Sgr")),
    # an area of the sky behind Sagittarius, without stars
    AstronomicalMansion(21, "Al-Baldah",         ("pi. Sgr",),
                        note="Al-Baldah is a region without stars. pi Sgr, one of the stars bordering it on the west, is only a conventional marker."),
    # two stars on the horn of Capricorn, and a third, the sheep
    AstronomicalMansion(22, "Sa'd al-Dhabih",    ("alf02 Cap", "bet01 Cap", "nu. Cap")),
    # two stars on the left hand of Aquarius, with a third between them
    AstronomicalMansion(23, "Sa'd Bula",         ("eps Aqr", "mu. Aqr", "nu. Aqr")),
    # three stars in a row, from the tail of Capricorn and the shoulder of Aquarius
    AstronomicalMansion(24, "Sa'd al-Su'ud",     ("bet Aqr", "ksi Aqr"),
                        note="The third star, 46 Cap (c1 Cap), is not in the Moira star catalogue."),
    # four stars on the right hand of Aquarius, three around a fourth
    AstronomicalMansion(25, "Sa'd al-Akhbiya",   ("gam Aqr", "zet01 Aqr", "pi. Aqr", "eta Aqr")),
    # two stars of Pegasus
    AstronomicalMansion(26, "Al-Fargh al-Muqaddam",   ("alf Peg", "bet Peg"),
                        aliases=("Al-Fargh al-Awwal",)),
    # two stars of Pegasus
    AstronomicalMansion(27, "Al-Fargh al-Muʾakhkhar", ("gam Peg", "alf And"),
                        aliases=("Al-Fargh al-Thani",)),
    # two bright stars from the head of Andromeda, near a curved line of
    # small stars that the Arabs make into a fish; others call it al-Rishāʾ
    AstronomicalMansion(28, "Batn al-Hut",       ("bet And",),
                        aliases=("Al-Rishāʾ",),
                        note="al-Biruni names two bright stars from the head of Andromeda. Only beta And, the conventional modern marker, is listed; his second star is not identified here."),
]

# Agrippa, De occulta philosophia II.33 (English 1651, esotericarchives.com
# agripp2c). Latin name: Agrippa's first-named form; latin_aliases: the other
# names he gives ("... or ..."). ``signification`` is a short paraphrase of
# the effects Agrippa lists, in his order. Agrippa gives no nature label:
# ``nature`` is Moira's editorial summary of the listed effects (Fortunate:
# the effects are aids; Unfortunate: they are hindrances or destruction;
# Mixed: substantial effects of both kinds).
AGRIPPA_MANSIONS: list[ElectionalMansion] = [
    ElectionalMansion(1,  "Alnath",     "Mixed",       "Causes discords and journeys"),
    ElectionalMansion(2,  "Allothaim",  "Fortunate",   "Finding treasure, retaining captives", ("Albochan",)),
    ElectionalMansion(3,  "Achaomazon", "Fortunate",   "Profitable to sailors, hunters, alchemists", ("Athoray",)),
    ElectionalMansion(4,  "Aldebaram",  "Unfortunate", "Destroys and hinders buildings, fountains, wells and gold-mines; drives off creeping things; begets discord", ("Aldelamen",)),
    ElectionalMansion(5,  "Alchatay",   "Fortunate",   "Return from a journey, instruction of scholars; confirms buildings; gives health and good will", ("Albachay",)),
    ElectionalMansion(6,  "Alhanna",    "Mixed",       "Hunting, besieging towns, revenge of princes; destroys harvests and fruits; hinders the physician", ("Alchaya",)),
    ElectionalMansion(7,  "Aldimiach",  "Fortunate",   "Gain and friendship; profitable to lovers; scares flies; destroys magisteries", ("Alarzach",)),
    ElectionalMansion(8,  "Alnaza",     "Fortunate",   "Love, friendship, fellowship of travellers; drives away mice; afflicts captives, confirming their imprisonment", ("Anatrachya",)),
    ElectionalMansion(9,  "Archaam",    "Unfortunate", "Hinders harvests and travellers; puts discord between men", ("Arcaph",)),
    ElectionalMansion(10, "Algelioche", "Fortunate",   "Strengthens buildings; gives love, benevolence and help against enemies", ("Albgebh",)),
    ElectionalMansion(11, "Azobra",     "Fortunate",   "Voyages, gain by merchandise, redemption of captives", ("Ardaf",)),
    ElectionalMansion(12, "Alzarpha",   "Mixed",       "Prosperity to harvests and plantations; hinders seamen; betters servants, captives and companions", ("Azarpha",)),
    ElectionalMansion(13, "Alhaire",    "Fortunate",   "Benevolence, gain, voyages, harvests, freedom of captives"),
    ElectionalMansion(14, "Achureth",   "Fortunate",   "Love of married folk (1651: 'martyred folk'); cures the sick; profitable to sailors; hinders journeys by land", ("Arimet", "Azimeth", "Alhumech", "Alcheymech")),
    ElectionalMansion(15, "Agrapha",    "Mixed",       "Extracting treasures, digging wells; furthers divorce, discord, destruction of houses and enemies; hinders travellers", ("Algarpha",)),
    ElectionalMansion(16, "Azubene",    "Unfortunate", "Hinders journeys, wedlock, harvests and merchandise; prevails for redemption of captives", ("Ahubene",)),
    ElectionalMansion(17, "Alchil",     "Fortunate",   "Betters bad fortune; makes love durable; strengthens buildings; helps seamen"),
    ElectionalMansion(18, "Alchas",     "Mixed",       "Discord, sedition, conspiracy against princes, revenge on enemies; frees captives; helps buildings", ("Altob",)),
    ElectionalMansion(19, "Allatha",    "Unfortunate", "Besieging and taking towns, driving men from their places; destruction of seamen, perdition of captives", ("Achala", "Hycula", "Axala")),
    ElectionalMansion(20, "Abnahaya",   "Mixed",       "Tames wild beasts, strengthens prisons; destroys the wealth of societies; compels a man to come to a place"),
    ElectionalMansion(21, "Abeda",      "Mixed",       "Good for harvests, gain, buildings and travellers; causes divorce", ("Albeldach",)),
    ElectionalMansion(22, "Sadahacha",  "Fortunate",   "Flight of servants and captives, that they may escape; helps cure diseases", ("Zodeboluch", "Zandeldena")),
    ElectionalMansion(23, "Zabadola",   "Mixed",       "Divorce, liberty of captives, health of the sick", ("Zobrach",)),
    ElectionalMansion(24, "Sadabath",   "Mixed",       "Goodwill of married folk, victory of soldiers; hurts and hinders the exercise of government", ("Chadezoad",)),
    ElectionalMansion(25, "Sadalabra",  "Unfortunate", "Besieging, revenge, destroying enemies, divorce; confirms prisons and buildings; hastens messengers; binding spells against copulation", ("Sadalachia",)),
    ElectionalMansion(26, "Alpharg",    "Mixed",       "Union and love of men, health of captives; destroys prisons and buildings", ("Phragal Mocaden",)),
    ElectionalMansion(27, "Alcharya",   "Mixed",       "Increases harvests, revenues and gain; heals infirmities; hinders buildings, prolongs prisons, endangers seamen; helps work mischief on others", ("Alhalgalmoad",)),
    ElectionalMansion(28, "Albotham",   "Mixed",       "Increases harvests and merchandise; secures travellers in danger; joy of married couples; strengthens prisons, causes loss of treasures", ("Alchalcy",)),
]

# Picatrix I.4, Latin (ed. Pingree 1986), as listed by I. Freer, "The Picatrix:
# Lunar Mansions in Western Astrology". Index 0 is mansion 1.
PICATRIX_LATIN_NAMES: tuple[str, ...] = (
    "Alnath", "Albotain", "Azoraya", "Aldebaran", "Almices", "Athaya", "Aldirah",
    "Annathra", "Atarf", "Algebha", "Azobra", "Acarfa", "Alahue", "Azimech",
    "Argafra", "Azubene", "Alichil", "Alcalb", "Exaula", "Nahaym", "Elbelda",
    "Caadaldeba", "Caadebolach", "Caadacohot", "Caadalhacbia", "Almiquedam",
    "Algarf Almuehar", "Arrexhe",
)

@dataclass(slots=True)
class MansionPosition:
    """The mansion a longitude falls in, with the degrees already travelled into it."""

    mansion:    ElectionalMansion | AstronomicalMansion
    degrees_in: float
    longitude:  float

    def __repr__(self) -> str:
        m = self.mansion
        if isinstance(m, AstronomicalMansion):
            return (
                f"Mansion {m.index:>2} — {m.arabic_name} "
                f"{self.degrees_in:.4f}° in  "
                f"[{', '.join(m.marker_stars)}]"
            )
        return (
            f"Mansion {m.index:>2} — {m.latin_name} "
            f"{self.degrees_in:.4f}° in  "
            f"[{m.nature}]  {m.signification}"
        )


class MansionTradition(str, Enum):
    """Which tradition names and interprets the 28 equal mansions.

    ``AL_BIRUNI`` gives al-Bīrūnī's Arabic names and marker stars, without
    interpretations. The others are electional traditions.
    """

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
        raise ValueError("The al-Biruni tradition does not support electional natures: it gives names and marker stars only.")
    table = _VARIANT_TABLES.get(tradition)
    if table and mansion_index in table:
        return table[mansion_index][0]
    return AGRIPPA_MANSIONS[mansion_index - 1].nature

def variant_signification(mansion_index: int, tradition: MansionTradition) -> str:
    if mansion_index < 1 or mansion_index > 28:
        raise ValueError(f"mansion_index must be 1--28, got {mansion_index}")
    if tradition is MansionTradition.AL_BIRUNI:
        raise ValueError("The al-Biruni tradition does not support electional significations: it gives names and marker stars only.")
    table = _VARIANT_TABLES.get(tradition)
    if table and mansion_index in table:
        return table[mansion_index][1]
    return AGRIPPA_MANSIONS[mansion_index - 1].signification

def electional_mansion(mansion_index: int, tradition: MansionTradition) -> ElectionalMansion:
    """The mansion as an electional tradition names and interprets it.

    Picatrix uses its own Latin names (``PICATRIX_LATIN_NAMES``). Agrippa,
    Abenragel and Ibn al-Arabi use Agrippa's Latin names. Moira holds no
    separate Latin list for Abenragel or Ibn al-Arabi.
    """
    if mansion_index < 1 or mansion_index > 28:
        raise ValueError(f"mansion_index must be 1--28, got {mansion_index}")
    if tradition is MansionTradition.AL_BIRUNI:
        raise ValueError(
            "The al-Biruni tradition gives Arabic names and marker stars, not electional mansions; "
            "use AL_BIRUNI_MANSIONS."
        )
    agrippa = AGRIPPA_MANSIONS[mansion_index - 1]
    if tradition is MansionTradition.PICATRIX:
        latin_name, latin_aliases = PICATRIX_LATIN_NAMES[mansion_index - 1], ()
    else:
        latin_name, latin_aliases = agrippa.latin_name, agrippa.latin_aliases
    return ElectionalMansion(
        index=mansion_index,
        latin_name=latin_name,
        nature=variant_nature(mansion_index, tradition),
        signification=variant_signification(mansion_index, tradition),
        latin_aliases=latin_aliases,
    )


def _equal_mansion(
    lon: float, tradition: MansionTradition
) -> tuple[ElectionalMansion | AstronomicalMansion, float]:
    """Assign a normalized longitude to one of 28 equal mansions of 360/28 degrees from 0°."""
    index_0 = min(int(lon / MANSION_SPAN), 27)
    degrees_in = lon - index_0 * MANSION_SPAN
    if tradition is MansionTradition.AL_BIRUNI:
        return AL_BIRUNI_MANSIONS[index_0], degrees_in
    return electional_mansion(index_0 + 1, tradition), degrees_in


def mansion_of(longitude: float, tradition: MansionTradition = MansionTradition.AGRIPPA, jd: float | None = None) -> MansionPosition:
    """The equal mansion (360/28 degrees each, from 0° Aries) that a tropical longitude falls in.

    ``jd`` is accepted for compatibility with 6.9.8, where the al-Biruni
    tradition needed it for star-based boundaries. No tradition uses it now.
    """
    lon = longitude % 360.0
    mansion, degrees_in = _equal_mansion(lon, tradition)
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
    """The equal mansion counted from sidereal 0° Aries, for every tradition.

    ``longitude`` in the result stays the tropical input.
    """
    from .sidereal import tropical_to_sidereal
    lon = tropical_to_sidereal(tropical_longitude, jd, ayanamsa_system, ayanamsa_mode) % 360.0
    mansion, degrees_in = _equal_mansion(lon, tradition)
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

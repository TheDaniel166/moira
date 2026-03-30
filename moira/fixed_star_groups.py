"""
Oracle of Star Groups — moira/fixed_star_groups.py

Archetype: Oracle
Purpose: Provides named constants, group tuples, and per-star position
         functions for ~50 astrologically significant fixed stars, including
         the Pleiades, Hyades, and Ptolemy's 15 stars.

Boundary declaration
--------------------
Owns:
    - Named string constants for ~50 individual fixed stars.
    - Group tuples: PLEIADES, HYADES, PTOLEMY_STARS.
    - FIXED_STAR_NAMES master mapping (constant → canonical name).
    - Per-star convenience functions (algol_at, sirius_at, vega_at, â€¦).
    - fixed_star_group_at() dispatcher.
    - list_fixed_stars(), available_fixed_stars() and per-group introspection
      (list_pleiades, list_hyades, list_ptolemy_stars, available_* variants).
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    PLEIADES, HYADES, PTOLEMY_STARS  (group tuples)
    ALGOL, MIRFAK, ALCYONE, MAIA, ELECTRA, TAYGETA, MEROPE, CELAENO,
    STEROPE, ALDEBARAN, AIN, HYADUM_I, HYADUM_II, RIGEL, BETELGEUSE,
    CAPELLA, CASTOR, POLLUX, SIRIUS, PROCYON, CANOPUS, ACHERNAR,
    REGULUS, DENEBOLA, ZOSMA, SPICA, VINDEMIATRIX, ARCTURUS, ALPHECCA,
    ZUBENELGENUBI, ZUBENESHAMALI, ANTARES, GRAFFIAS, DSCHUBBA, ACRAB,
    LESATH, RASALHAGUE, RAS_ALGETHI, FACIES, SADALSUUD, SADALMELIK,
    ALGEDI, FOMALHAUT, SCHEAT, MARKAB, ALPHERATZ, MIRACH, ALMACH,
    ANKAA, DENEB, VEGA, ALPHARD, ALKES, ALGORAB, ACRUX, MIMOSA,
    HAMAL, MENKAR  (individual star constants)
    FIXED_STAR_NAMES
    fixed_star_group_at() and all per-star _at() functions
    list_fixed_stars(), available_fixed_stars()
    list_pleiades(), list_hyades(), list_ptolemy_stars()
    available_pleiades(), available_hyades(), available_ptolemy_stars()

Stars sourced from moira/data/star_registry.csv via moira.stars.
"""

from .stars import star_at as star_at, list_named_stars as list_stars, FixedStar as StarPosition

# ---------------------------------------------------------------------------
# Group tuples
# ---------------------------------------------------------------------------

PLEIADES = (
    "Alcyone", "Maia", "Electra", "Taygeta", "Merope", "Celaeno", "Sterope I",
)

HYADES = (
    "Ain", "Hyadum I", "Hyadum II",
)

PTOLEMY_STARS = (
    "Algol", "Alcyone", "Aldebaran", "Capella", "Sirius", "Regulus", "Spica",
    "Arcturus", "Alphecca", "Antares", "Vega", "Deneb", "Fomalhaut",
    "Canopus", "Achernar",
)

# ---------------------------------------------------------------------------
# Individual star constants
# ---------------------------------------------------------------------------

# Perseus
ALGOL  = "Algol"
MIRFAK = "Mirfak"

# Taurus / Pleiades / Hyades
ALCYONE   = "Alcyone"
MAIA      = "Maia"
ELECTRA   = "Electra"
TAYGETA   = "Taygeta"
MEROPE    = "Merope"
CELAENO   = "Celaeno"
STEROPE   = "Sterope I"
ALDEBARAN = "Aldebaran"
AIN       = "Ain"
HYADUM_I  = "Hyadum I"
HYADUM_II = "Hyadum II"

# Orion
RIGEL      = "Rigel"
BETELGEUSE = "Betelgeuse"

# Auriga
CAPELLA = "Capella"

# Gemini
CASTOR = "Castor"
POLLUX = "Pollux"

# Canis Major / Minor
SIRIUS  = "Sirius"
PROCYON = "Procyon"

# Carina / Eridanus
CANOPUS  = "Canopus"
ACHERNAR = "Achernar"

# Leo
REGULUS  = "Regulus"
DENEBOLA = "Denebola"
ZOSMA    = "Zosma"

# Virgo
SPICA        = "Spica"
VINDEMIATRIX = "Vindemiatrix"

# Bootes
ARCTURUS = "Arcturus"

# Corona Borealis
ALPHECCA = "Alphecca"

# Libra
ZUBENELGENUBI = "Zubenelgenubi"
ZUBENESHAMALI = "Zubeneshamali"

# Scorpius
ANTARES  = "Antares"
GRAFFIAS = "Graffias"
DSCHUBBA = "Dschubba"
ACRAB    = "Acrab"
LESATH   = "Lesath"

# Ophiuchus / Hercules
RASALHAGUE  = "Rasalhague"
RAS_ALGETHI = "Ras Algethi"

# Sagittarius
FACIES = "Facies"

# Aquarius
SADALSUUD  = "Sadalsuud"
SADALMELIK = "Sadalmelik"

# Capricornus
ALGEDI = "Algedi"

# Pisces / Pegasus
FOMALHAUT = "Fomalhaut"
SCHEAT    = "Scheat"
MARKAB    = "Markab"

# Andromeda
ALPHERATZ = "Alpheratz"
MIRACH    = "Mirach"
ALMACH    = "Almach"

# Phoenix
ANKAA = "Ankaa"

# Cygnus
DENEB = "Deneb"

# Lyra
VEGA = "Vega"

# Hydra / Crater
ALPHARD = "Alphard"
ALKES   = "Alkes"

# Corvus
ALGORAB = "Algorab"

# Crux
ACRUX  = "Acrux"
MIMOSA = "Mimosa"

# Aries / Cetus
HAMAL  = "Hamal"
MENKAR = "Menkar"

# ---------------------------------------------------------------------------
# Master names dict
# ---------------------------------------------------------------------------

FIXED_STAR_NAMES = {
    ALGOL:         "Algol",
    MIRFAK:        "Mirfak",
    ALCYONE:       "Alcyone",
    MAIA:          "Maia",
    ELECTRA:       "Electra",
    TAYGETA:       "Taygeta",
    MEROPE:        "Merope",
    CELAENO:       "Celaeno",
    STEROPE:       "Sterope I",
    ALDEBARAN:     "Aldebaran",
    AIN:           "Ain",
    HYADUM_I:      "Hyadum I",
    HYADUM_II:     "Hyadum II",
    RIGEL:         "Rigel",
    BETELGEUSE:    "Betelgeuse",
    CAPELLA:       "Capella",
    CASTOR:        "Castor",
    POLLUX:        "Pollux",
    SIRIUS:        "Sirius",
    PROCYON:       "Procyon",
    CANOPUS:       "Canopus",
    ACHERNAR:      "Achernar",
    REGULUS:       "Regulus",
    DENEBOLA:      "Denebola",
    ZOSMA:         "Zosma",
    SPICA:         "Spica",
    VINDEMIATRIX:  "Vindemiatrix",
    ARCTURUS:      "Arcturus",
    ALPHECCA:      "Alphecca",
    ZUBENELGENUBI: "Zubenelgenubi",
    ZUBENESHAMALI: "Zubeneshamali",
    ANTARES:       "Antares",
    GRAFFIAS:      "Graffias",
    DSCHUBBA:      "Dschubba",
    ACRAB:         "Acrab",
    LESATH:        "Lesath",
    RASALHAGUE:    "Rasalhague",
    RAS_ALGETHI:   "Ras Algethi",
    FACIES:        "Facies",
    SADALSUUD:     "Sadalsuud",
    SADALMELIK:    "Sadalmelik",
    ALGEDI:        "Algedi",
    FOMALHAUT:     "Fomalhaut",
    SCHEAT:        "Scheat",
    MARKAB:        "Markab",
    ALPHERATZ:     "Alpheratz",
    MIRACH:        "Mirach",
    ALMACH:        "Almach",
    ANKAA:         "Ankaa",
    DENEB:         "Deneb",
    VEGA:          "Vega",
    ALPHARD:       "Alphard",
    ALKES:         "Alkes",
    ALGORAB:       "Algorab",
    ACRUX:         "Acrux",
    MIMOSA:        "Mimosa",
    HAMAL:         "Hamal",
    MENKAR:        "Menkar",
}


# ---------------------------------------------------------------------------
# Dispatcher and per-body functions
# ---------------------------------------------------------------------------

def fixed_star_group_at(name: str, jd_tt: float) -> StarPosition:
    """Return the position of a named fixed star at jd_tt."""
    return star_at(name, jd_tt)


def algol_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALGOL, jd_tt)

def mirfak_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(MIRFAK, jd_tt)

def alcyone_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALCYONE, jd_tt)

def maia_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(MAIA, jd_tt)

def electra_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ELECTRA, jd_tt)

def taygeta_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(TAYGETA, jd_tt)

def merope_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(MEROPE, jd_tt)

def celaeno_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(CELAENO, jd_tt)

def sterope_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(STEROPE, jd_tt)

def aldebaran_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALDEBARAN, jd_tt)

def ain_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(AIN, jd_tt)

def hyadum_i_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(HYADUM_I, jd_tt)

def hyadum_ii_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(HYADUM_II, jd_tt)

def rigel_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(RIGEL, jd_tt)

def betelgeuse_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(BETELGEUSE, jd_tt)

def capella_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(CAPELLA, jd_tt)

def castor_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(CASTOR, jd_tt)

def pollux_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(POLLUX, jd_tt)

def sirius_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(SIRIUS, jd_tt)

def procyon_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(PROCYON, jd_tt)

def canopus_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(CANOPUS, jd_tt)

def achernar_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ACHERNAR, jd_tt)

def regulus_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(REGULUS, jd_tt)

def denebola_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(DENEBOLA, jd_tt)

def zosma_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ZOSMA, jd_tt)

def spica_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(SPICA, jd_tt)

def vindemiatrix_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(VINDEMIATRIX, jd_tt)

def arcturus_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ARCTURUS, jd_tt)

def alphecca_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALPHECCA, jd_tt)

def zubenelgenubi_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ZUBENELGENUBI, jd_tt)

def zubeneshamali_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ZUBENESHAMALI, jd_tt)

def antares_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ANTARES, jd_tt)

def graffias_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(GRAFFIAS, jd_tt)

def dschubba_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(DSCHUBBA, jd_tt)

def acrab_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ACRAB, jd_tt)

def lesath_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(LESATH, jd_tt)

def rasalhague_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(RASALHAGUE, jd_tt)

def ras_algethi_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(RAS_ALGETHI, jd_tt)

def facies_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(FACIES, jd_tt)

def sadalsuud_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(SADALSUUD, jd_tt)

def sadalmelik_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(SADALMELIK, jd_tt)

def algedi_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALGEDI, jd_tt)

def fomalhaut_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(FOMALHAUT, jd_tt)

def scheat_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(SCHEAT, jd_tt)

def markab_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(MARKAB, jd_tt)

def alpheratz_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALPHERATZ, jd_tt)

def mirach_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(MIRACH, jd_tt)

def almach_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALMACH, jd_tt)

def ankaa_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ANKAA, jd_tt)

def deneb_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(DENEB, jd_tt)

def vega_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(VEGA, jd_tt)

def alphard_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALPHARD, jd_tt)

def alkes_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALKES, jd_tt)

def algorab_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ALGORAB, jd_tt)

def acrux_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(ACRUX, jd_tt)

def mimosa_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(MIMOSA, jd_tt)

def hamal_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(HAMAL, jd_tt)

def menkar_at(jd_tt: float) -> StarPosition:
    return fixed_star_group_at(MENKAR, jd_tt)


# ---------------------------------------------------------------------------
# List / availability helpers
# ---------------------------------------------------------------------------

def list_fixed_stars() -> list[str]:
    """Return all fixed star names known to this module."""
    return list(FIXED_STAR_NAMES.values())


def available_fixed_stars() -> list[str]:
    """Return fixed star names available in the loaded catalog."""
    catalog = set(list_stars())
    return [name for name in FIXED_STAR_NAMES.values() if name in catalog]


def list_pleiades() -> list[str]:
    """Return the Pleiades star names."""
    return list(PLEIADES)


def list_hyades() -> list[str]:
    """Return the Hyades star names."""
    return list(HYADES)


def list_ptolemy_stars() -> list[str]:
    """Return Ptolemy's 15 star names."""
    return list(PTOLEMY_STARS)


def available_pleiades() -> list[str]:
    """Return Pleiades names available in the loaded catalog."""
    catalog = set(list_stars())
    return [name for name in PLEIADES if name in catalog]


def available_hyades() -> list[str]:
    """Return Hyades names available in the loaded catalog."""
    catalog = set(list_stars())
    return [name for name in HYADES if name in catalog]


def available_ptolemy_stars() -> list[str]:
    """Return Ptolemy star names available in the loaded catalog."""
    catalog = set(list_stars())
    return [name for name in PTOLEMY_STARS if name in catalog]


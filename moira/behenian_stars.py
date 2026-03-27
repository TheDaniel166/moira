"""
Oracle of the Behenian Stars — moira/behenian_stars.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for the
         15 Behenian stars of medieval magical tradition.

Boundary declaration
--------------------
Owns:
    - Named string constants for each of the 15 Behenian stars.
    - BEHENIAN_STAR_NAMES mapping (constant → canonical name).
    - Per-star convenience functions (algol_at, sirius_at, …).
    - behenian_star_at() dispatcher.
    - list_behenian_stars() / available_behenian_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALGOL, ALCYONE, ALDEBARAN, CAPELLA, SIRIUS, PROCYON, REGULUS,
    ALGORAB, SPICA, ARCTURUS, ALPHECCA, ANTARES, VEGA, ALGEDI, FOMALHAUT
    BEHENIAN_STAR_NAMES
    behenian_star_at(), algol_at(), alcyone_at(), aldebaran_at(),
    capella_at(), sirius_at(), procyon_at(), regulus_at(), algorab_at(),
    spica_at(), arcturus_at(), alphecca_at(), antares_at(), vega_at(),
    algedi_at(), fomalhaut_at()
    list_behenian_stars(), available_behenian_stars()

The Behenian stars are a selection of fifteen stars considered especially
useful for magical applications in medieval European and Arabic astrology
(Cornelius Agrippa, Picatrix).
Stars sourced from sefstars.txt via moira.fixed_stars.
"""

from .stars import star_at, StarPosition, list_stars

ALGOL     = "Algol"
ALCYONE   = "Alcyone"
ALDEBARAN = "Aldebaran"
CAPELLA   = "Capella"
SIRIUS    = "Sirius"
PROCYON   = "Procyon"
REGULUS   = "Regulus"
ALGORAB   = "Algorab"
SPICA     = "Spica"
ARCTURUS  = "Arcturus"
ALPHECCA  = "Alphecca"
ANTARES   = "Antares"
VEGA      = "Vega"
ALGEDI    = "Algedi"
FOMALHAUT = "Fomalhaut"

BEHENIAN_STAR_NAMES = {
    ALGOL:     "Algol",
    ALCYONE:   "Alcyone",
    ALDEBARAN: "Aldebaran",
    CAPELLA:   "Capella",
    SIRIUS:    "Sirius",
    PROCYON:   "Procyon",
    REGULUS:   "Regulus",
    ALGORAB:   "Algorab",
    SPICA:     "Spica",
    ARCTURUS:  "Arcturus",
    ALPHECCA:  "Alphecca",
    ANTARES:   "Antares",
    VEGA:      "Vega",
    ALGEDI:    "Algedi",
    FOMALHAUT: "Fomalhaut",
}


def behenian_star_at(name: str, jd_tt: float) -> StarPosition:
    """Return the position of a Behenian star at jd_tt."""
    return star_at(name, jd_tt)


def algol_at(jd_tt: float) -> StarPosition:
    """Return the position of Algol at jd_tt."""
    return behenian_star_at(ALGOL, jd_tt)


def alcyone_at(jd_tt: float) -> StarPosition:
    """Return the position of Alcyone at jd_tt."""
    return behenian_star_at(ALCYONE, jd_tt)


def aldebaran_at(jd_tt: float) -> StarPosition:
    """Return the position of Aldebaran at jd_tt."""
    return behenian_star_at(ALDEBARAN, jd_tt)


def capella_at(jd_tt: float) -> StarPosition:
    """Return the position of Capella at jd_tt."""
    return behenian_star_at(CAPELLA, jd_tt)


def sirius_at(jd_tt: float) -> StarPosition:
    """Return the position of Sirius at jd_tt."""
    return behenian_star_at(SIRIUS, jd_tt)


def procyon_at(jd_tt: float) -> StarPosition:
    """Return the position of Procyon at jd_tt."""
    return behenian_star_at(PROCYON, jd_tt)


def regulus_at(jd_tt: float) -> StarPosition:
    """Return the position of Regulus at jd_tt."""
    return behenian_star_at(REGULUS, jd_tt)


def algorab_at(jd_tt: float) -> StarPosition:
    """Return the position of Algorab at jd_tt."""
    return behenian_star_at(ALGORAB, jd_tt)


def spica_at(jd_tt: float) -> StarPosition:
    """Return the position of Spica at jd_tt."""
    return behenian_star_at(SPICA, jd_tt)


def arcturus_at(jd_tt: float) -> StarPosition:
    """Return the position of Arcturus at jd_tt."""
    return behenian_star_at(ARCTURUS, jd_tt)


def alphecca_at(jd_tt: float) -> StarPosition:
    """Return the position of Alphecca at jd_tt."""
    return behenian_star_at(ALPHECCA, jd_tt)


def antares_at(jd_tt: float) -> StarPosition:
    """Return the position of Antares at jd_tt."""
    return behenian_star_at(ANTARES, jd_tt)


def vega_at(jd_tt: float) -> StarPosition:
    """Return the position of Vega at jd_tt."""
    return behenian_star_at(VEGA, jd_tt)


def algedi_at(jd_tt: float) -> StarPosition:
    """Return the position of Algedi at jd_tt."""
    return behenian_star_at(ALGEDI, jd_tt)


def fomalhaut_at(jd_tt: float) -> StarPosition:
    """Return the position of Fomalhaut at jd_tt."""
    return behenian_star_at(FOMALHAUT, jd_tt)


def list_behenian_stars() -> list[str]:
    """Return names of Behenian stars known to this API."""
    return list(BEHENIAN_STAR_NAMES.values())


def available_behenian_stars() -> list[str]:
    """Return names of Behenian stars available in the loaded catalog."""
    catalog = set(list_stars())
    return [name for name in BEHENIAN_STAR_NAMES.values() if name in catalog]

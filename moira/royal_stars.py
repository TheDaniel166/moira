"""
Oracle of the Royal Stars — moira/royal_stars.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for the
         four Royal Stars (Watchers of the Heavens) of Persian astronomy.

Boundary declaration
--------------------
Owns:
    - Named string constants for each of the four Royal Stars.
    - ROYAL_STAR_NAMES mapping (constant → canonical name).
    - Per-star convenience functions (aldebaran_at, regulus_at, â€¦).
    - royal_star_at() dispatcher.
    - list_royal_stars() / available_royal_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALDEBARAN, REGULUS, ANTARES, FOMALHAUT
    ROYAL_STAR_NAMES
    royal_star_at(), aldebaran_at(), regulus_at(), antares_at(), fomalhaut_at()
    list_royal_stars(), available_royal_stars()

The Royal Stars are the four brightest stars historically associated with
the four cardinal directions and the four archangels in Persian astronomy.
Stars sourced from moira/data/star_registry.csv via moira.stars.
"""

from .stars import star_at, StarPosition, list_stars

ALDEBARAN = "Aldebaran"
REGULUS   = "Regulus"
ANTARES   = "Antares"
FOMALHAUT = "Fomalhaut"

ROYAL_STAR_NAMES = {
    ALDEBARAN: "Aldebaran",
    REGULUS:   "Regulus",
    ANTARES:   "Antares",
    FOMALHAUT: "Fomalhaut",
}


def royal_star_at(name: str, jd_tt: float) -> StarPosition:
    """Return the position of a Royal Star at jd_tt."""
    return star_at(name, jd_tt)


def aldebaran_at(jd_tt: float) -> StarPosition:
    """Return the position of Aldebaran at jd_tt."""
    return royal_star_at(ALDEBARAN, jd_tt)


def regulus_at(jd_tt: float) -> StarPosition:
    """Return the position of Regulus at jd_tt."""
    return royal_star_at(REGULUS, jd_tt)


def antares_at(jd_tt: float) -> StarPosition:
    """Return the position of Antares at jd_tt."""
    return royal_star_at(ANTARES, jd_tt)


def fomalhaut_at(jd_tt: float) -> StarPosition:
    """Return the position of Fomalhaut at jd_tt."""
    return royal_star_at(FOMALHAUT, jd_tt)


def list_royal_stars() -> list[str]:
    """Return names of Royal Stars known to this API."""
    return list(ROYAL_STAR_NAMES.values())


def available_royal_stars() -> list[str]:
    """Return names of Royal Stars available in the loaded catalog."""
    catalog = set(list_stars())
    return [name for name in ROYAL_STAR_NAMES.values() if name in catalog]


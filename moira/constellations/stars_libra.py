"""
Libra Constellation Oracle â€” moira/constellations/stars_libra.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Libra (IAU: Lib).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Libra.
    - LIBRA_STAR_NAMES mapping (constant â†’ canonical name).
    - libra_star_at() dispatcher.
    - Per-star convenience functions (zubenelgenubi_at, zubeneshamali_at, â€¦).
    - list_libra_stars() / available_libra_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ZUBENELGENUBI, ZUBENESHAMALI, ZUBENELAKRAB, ZUBENELAKRIBI,
    VISHAKHA, ZUBENHAKRABI, BRACHIUM
    LIBRA_STAR_NAMES
    libra_star_at() and all per-star _at() functions
    list_libra_stars(), available_libra_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

ZUBENELGENUBI  = "Zubenelgenubi"
ZUBENESHAMALI  = "Zubeneschamali"
ZUBENELAKRAB   = "Zubenelhakrabi"
ZUBENELAKRIBI  = "Zubenelhakrabi"
VISHAKHA       = "Vishakha"
ZUBENHAKRABI   = "Zubenelhakrabi"
BRACHIUM       = "Brachium"

LIBRA_STAR_NAMES = {
    ZUBENELGENUBI: "Zubenelgenubi",
    ZUBENESHAMALI: "Zubeneschamali",
    ZUBENELAKRAB:  "Zubenelhakrabi",
    ZUBENELAKRIBI: "Zubenelhakrabi",
    VISHAKHA:      "Vishakha",
    ZUBENHAKRABI:  "Zubenelhakrabi",
    BRACHIUM:      "Brachium",
}


def libra_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def zubenelgenubi_at(jd_tt: float) -> StarPosition:
    return libra_star_at(ZUBENELGENUBI, jd_tt)

def zubeneshamali_at(jd_tt: float) -> StarPosition:
    return libra_star_at(ZUBENESHAMALI, jd_tt)

def zubenelakrab_at(jd_tt: float) -> StarPosition:
    return libra_star_at(ZUBENELAKRAB, jd_tt)

def zubenelakribi_at(jd_tt: float) -> StarPosition:
    return libra_star_at(ZUBENELAKRIBI, jd_tt)

def vishakha_at(jd_tt: float) -> StarPosition:
    return libra_star_at(VISHAKHA, jd_tt)

def zubenhakrabi_at(jd_tt: float) -> StarPosition:
    return libra_star_at(ZUBENHAKRABI, jd_tt)

def brachium_at(jd_tt: float) -> StarPosition:
    return libra_star_at(BRACHIUM, jd_tt)


def list_libra_stars() -> list[str]:
    return list(LIBRA_STAR_NAMES.values())


def available_libra_stars() -> list[str]:
    return [name for name in LIBRA_STAR_NAMES.values() if _star_name_is_resolvable(name)]






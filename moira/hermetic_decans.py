"""
Moira — Hermetic Decan Engine
==============================

Archetype: Engine

Status
------
**Research quarantine.** The 36 names and planetary faces have been
reconstructed from Gundel's 1936 edition of British Library Harley MS 3731,
ff. 1r-50r. The complete edited text explicitly assigns ten degrees to each
decan beginning from Aries, but the catalog and modern tropical/rising
projection have not yet passed the later public-admission gates. The module
remains excluded from the package root, facade, and REST application.

Purpose
-------
Preserves the source-identified catalog, equal 10-degree lookup, and
rising-decan composition for source comparison. Each catalog entry's name,
sign order, planetary face, and edition page are source-reconstructed here.

Tradition and frame of reference
---------------------------------
The edited Harley text orders three decans under each of the twelve signs and
assigns each a planetary face. It also begins from Aries and counts 10° for
each decan. Moira's modern equinox-fixed tropical realization and
Ascendant-based composition remain explicit research projection policies
rather than silently claimed manuscript doctrine.

Night-hour non-admission
------------------------
The removed ``decan_hours`` experiment divided sunset-to-sunrise into twelve
equal intervals beginning with the zodiacal decan on the Midheaven at sunset.
No identified passage in the Gundel/Harley edition establishes that algorithm.
Ancient Egyptian stellar decanal tables are a separate, source- and
epoch-dependent astronomical product; executable night-hour code must not be
reintroduced without its own admitted authority and validation contract.

Fixed-star non-admission
------------------------
The former one-fixed-star-per-decan table has no support in the identified
edition. ``DECAN_RULING_STARS`` is therefore empty, and fixed-star accessors
fail closed. Planetary faces are stored separately in
``DECAN_PLANETARY_FACES``.

Boundary declaration
--------------------
Owns: the 36-decan source catalog, planetary-face table, decan-order list,
      decan-for-longitude mapping, and rising-decan composition.
Delegates: true obliquity to ``moira.obliquity``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access or planetary kernel required.

Research surface
----------------
``DECAN_NAMES``        — dict of decan constant to name string (36 entries).
``DECAN_PLANETARY_FACES`` — source-reconstructed planetary faces.
``HERMETIC_DECAN_CATALOG`` — typed records with source pages.
``DECAN_RULING_STARS`` — empty compatibility marker; no admitted assignments.
``list_decans``        — return all 36 decan names in ecliptic order.
``available_decans``   — return no star-backed decans (fail-closed).
``decan_for_longitude``— map a longitude to its decan name.
``decan_at``           — return the decan containing the Ascendant at a given JD and location.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .julian import ut_to_tt
from .obliquity import true_obliquity

# ---------------------------------------------------------------------------
# Source-reconstructed Harley MS 3731 catalog
#
# Authority: Wilhelm Gundel, Dekane und Dekansternbilder (1936), pp. 379-383,
# section "Die lateinische Dekanliste des Hermes Trismegistos", transcribing
# British Library Harley MS 3731, ff. 1r-50r. The opening edited text (p. 33)
# supplies Aries-starting 10-degree segmentation; pp. 379-383 supply the names
# and planetary faces used below. The edition does not supply the fixed-star
# assignments previously stored here; those assignments are removed and fail
# closed.
# ---------------------------------------------------------------------------

HERMETIC_CATALOG_SOURCE_ID = "gundel_1936_harley_ms_3731"
HERMETIC_CATALOG_WITNESS = "British Library Harley MS 3731, ff. 1r-50r"
HERMETIC_CATALOG_EDITION = (
    "Wilhelm Gundel, Dekane und Dekansternbilder (1936), pp. 379-383"
)

AULATHAMAS     = "Aulathamas"
SABAOTH        = "Sabaoth"
DISORNAFAIS    = "Disornafais"
JAUS           = "Jaus"
SARNATAS       = "Sarnatas"
ERCHUMBRIS     = "Erchumbris"
MANUCHOS       = "Manuchos"
SAMUROIS       = "Samurois"
ASUEL          = "Asuel"
SENEPTOIS      = "Seneptois"
SOMATHALMAIS   = "Somathalmais"
CHARMINE       = "Charmine"
ZALOIAS        = "Zaloias"
ZACHOR         = "Zachor"
FRICH          = "Frich"
ZAMENDRES      = "Zamendres"
MAGOIS         = "Magois"
MICHULAIS      = "Michulais"
PSINEUS        = "Psineus"
CHUSTHISIS     = "Chusthisis"
PSANNATOIS     = "Psannatois"
NEBENOS        = "Nebenos"
CHURMANTIS     = "Churmantis"
PSERMES        = "Psermes"
CLINOTHOIS     = "Clinothois"
THURSOIS       = "Thursois"
RENETHIS       = "Renethis"
RENPSOIS       = "Renpsois"
MANETHOIS      = "Manethois"
MARXOIS        = "Marxois"
ULARIS         = "Ularis"
LUXOIS         = "Luxois"
CRAUXES        = "Crauxes"
FAMBRAIS       = "Fambrais"
FLUGMOIS_MARS  = "Flugmois Mars"
PIATHRIS       = "Piathris"

_CATALOG_SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
_FACE_PLANETS = frozenset(
    {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
)


@dataclass(slots=True, frozen=True)
class HermeticDecanCatalogEntry:
    """One name and planetary face transcribed from Gundel's Harley edition."""

    index: int
    sign: str
    decan_number: int
    name: str
    planetary_face: str
    edition_page: int
    source_id: str = HERMETIC_CATALOG_SOURCE_ID

    def __post_init__(self) -> None:
        if self.sign not in _CATALOG_SIGNS:
            raise ValueError(f"Unsupported catalog sign: {self.sign!r}")
        if not 1 <= self.decan_number <= 3:
            raise ValueError("decan_number must be in [1, 3]")
        expected_index = _CATALOG_SIGNS.index(self.sign) * 3 + self.decan_number - 1
        if self.index != expected_index:
            raise ValueError("catalog index must match sign and decan_number")
        if not self.name:
            raise ValueError("catalog name must be non-empty")
        if self.planetary_face not in _FACE_PLANETS:
            raise ValueError(f"Unsupported planetary face: {self.planetary_face!r}")
        if self.edition_page not in {379, 380, 381, 382, 383}:
            raise ValueError("edition_page must be within Gundel's Harley catalog")
        if self.source_id != HERMETIC_CATALOG_SOURCE_ID:
            raise ValueError("source_id must identify the reconstruction source")


HERMETIC_DECAN_CATALOG: tuple[HermeticDecanCatalogEntry, ...] = (
    HermeticDecanCatalogEntry(0, "Aries", 1, AULATHAMAS, "Mars", 379),
    HermeticDecanCatalogEntry(1, "Aries", 2, SABAOTH, "Sun", 379),
    HermeticDecanCatalogEntry(2, "Aries", 3, DISORNAFAIS, "Venus", 379),
    HermeticDecanCatalogEntry(3, "Taurus", 1, JAUS, "Mercury", 379),
    HermeticDecanCatalogEntry(4, "Taurus", 2, SARNATAS, "Moon", 380),
    HermeticDecanCatalogEntry(5, "Taurus", 3, ERCHUMBRIS, "Saturn", 380),
    HermeticDecanCatalogEntry(6, "Gemini", 1, MANUCHOS, "Jupiter", 380),
    HermeticDecanCatalogEntry(7, "Gemini", 2, SAMUROIS, "Mars", 380),
    HermeticDecanCatalogEntry(8, "Gemini", 3, ASUEL, "Sun", 380),
    HermeticDecanCatalogEntry(9, "Cancer", 1, SENEPTOIS, "Venus", 380),
    HermeticDecanCatalogEntry(10, "Cancer", 2, SOMATHALMAIS, "Mercury", 380),
    HermeticDecanCatalogEntry(11, "Cancer", 3, CHARMINE, "Moon", 380),
    HermeticDecanCatalogEntry(12, "Leo", 1, ZALOIAS, "Saturn", 381),
    HermeticDecanCatalogEntry(13, "Leo", 2, ZACHOR, "Jupiter", 381),
    HermeticDecanCatalogEntry(14, "Leo", 3, FRICH, "Mars", 381),
    HermeticDecanCatalogEntry(15, "Virgo", 1, ZAMENDRES, "Sun", 381),
    HermeticDecanCatalogEntry(16, "Virgo", 2, MAGOIS, "Venus", 381),
    HermeticDecanCatalogEntry(17, "Virgo", 3, MICHULAIS, "Mercury", 381),
    HermeticDecanCatalogEntry(18, "Libra", 1, PSINEUS, "Moon", 381),
    HermeticDecanCatalogEntry(19, "Libra", 2, CHUSTHISIS, "Saturn", 381),
    HermeticDecanCatalogEntry(20, "Libra", 3, PSANNATOIS, "Jupiter", 381),
    HermeticDecanCatalogEntry(21, "Scorpio", 1, NEBENOS, "Mars", 382),
    HermeticDecanCatalogEntry(22, "Scorpio", 2, CHURMANTIS, "Sun", 382),
    HermeticDecanCatalogEntry(23, "Scorpio", 3, PSERMES, "Venus", 382),
    HermeticDecanCatalogEntry(24, "Sagittarius", 1, CLINOTHOIS, "Mercury", 382),
    HermeticDecanCatalogEntry(25, "Sagittarius", 2, THURSOIS, "Moon", 382),
    HermeticDecanCatalogEntry(26, "Sagittarius", 3, RENETHIS, "Saturn", 382),
    HermeticDecanCatalogEntry(27, "Capricorn", 1, RENPSOIS, "Jupiter", 382),
    HermeticDecanCatalogEntry(28, "Capricorn", 2, MANETHOIS, "Mars", 382),
    HermeticDecanCatalogEntry(29, "Capricorn", 3, MARXOIS, "Sun", 382),
    HermeticDecanCatalogEntry(30, "Aquarius", 1, ULARIS, "Venus", 382),
    HermeticDecanCatalogEntry(31, "Aquarius", 2, LUXOIS, "Mercury", 382),
    HermeticDecanCatalogEntry(32, "Aquarius", 3, CRAUXES, "Moon", 383),
    HermeticDecanCatalogEntry(33, "Pisces", 1, FAMBRAIS, "Saturn", 383),
    HermeticDecanCatalogEntry(34, "Pisces", 2, FLUGMOIS_MARS, "Jupiter", 383),
    HermeticDecanCatalogEntry(35, "Pisces", 3, PIATHRIS, "Mars", 383),
)

_CATALOG_BY_NAME = {entry.name: entry for entry in HERMETIC_DECAN_CATALOG}
DECAN_NAMES: dict[str, str] = {
    entry.name: entry.name for entry in HERMETIC_DECAN_CATALOG
}
DECAN_PLANETARY_FACES: dict[str, str] = {
    entry.name: entry.planetary_face for entry in HERMETIC_DECAN_CATALOG
}
DECAN_SOURCE_PAGES: dict[str, int] = {
    entry.name: entry.edition_page for entry in HERMETIC_DECAN_CATALOG
}

# Compatibility marker only. The identified edition supplies no fixed-star
# rulership table, so valid assignments are intentionally empty.
DECAN_RULING_STARS: dict[str, str] = {}

_DECAN_ORDER: list[str] = [
    entry.name for entry in HERMETIC_DECAN_CATALOG
]


# ---------------------------------------------------------------------------
# Catalog and ordering functions
# ---------------------------------------------------------------------------

def list_decans() -> list[str]:
    """Return all 36 decan names in tropical ecliptic order (0°→360°)."""
    return list(_DECAN_ORDER)


def list_decan_catalog() -> list[HermeticDecanCatalogEntry]:
    """Return the source-reconstructed Harley catalog in zodiacal order."""

    return list(HERMETIC_DECAN_CATALOG)


def decan_catalog_entry(name: str) -> HermeticDecanCatalogEntry:
    """Return the source record for one decan name."""

    return _CATALOG_BY_NAME[name]


def decan_planetary_face(name: str) -> str:
    """Return the planetary face printed for one decan in Gundel's edition."""

    return DECAN_PLANETARY_FACES[name]


def available_decans() -> list[str]:
    """Return decans with source-admitted fixed-star rulers.

    Gundel's Harley catalog supplies no such table, so this compatibility
    query fails closed with an empty result.
    """

    return []


def decan_for_longitude(lon: float) -> str:
    """Map a tropical ecliptic longitude to its Hermetic decan name.

    Applies the source-supported equal 10° segmentation beginning at Aries
    through Moira's explicit tropical-frame research projection. Source
    support for the segmentation does not by itself admit that modern frame
    projection as public doctrine.

    Normalizes the longitude modulo 360 before computing the decan.
    Raises ValueError for NaN or infinite inputs.
    """
    if not math.isfinite(lon):
        raise ValueError(f"longitude must be finite, got {lon!r}")
    idx = int(lon % 360) // 10
    # Guard against float edge case where lon % 360 == 360.0 exactly
    return _DECAN_ORDER[idx % 36]


def decan_index(name: str) -> int:
    """Return the 0-based ecliptic index of a decan name.

    Raises ValueError if the name is not a valid decan.
    """
    return _DECAN_ORDER.index(name)


# ---------------------------------------------------------------------------
# Fixed-star compatibility functions
# ---------------------------------------------------------------------------

def decan_ruling_star(name: str) -> str:
    """Fail closed because the identified edition supplies no star ruler."""

    if name not in _CATALOG_BY_NAME:
        raise KeyError(name)
    raise LookupError(
        "The Gundel/Harley 3731 catalog does not provide fixed-star rulerships"
    )


def decan_star_at(name: str, jd: float) -> None:
    """Fail closed because no source-admitted decan star can be positioned."""

    if name not in _CATALOG_BY_NAME:
        raise KeyError(name)
    if not math.isfinite(jd):
        raise ValueError("jd must be finite")
    raise LookupError(
        "The Gundel/Harley 3731 catalog does not provide fixed-star rulerships"
    )


# ---------------------------------------------------------------------------
# Local Sidereal Time → RAMC
# ---------------------------------------------------------------------------

def _lst_to_ramc(jd: float, geo_lon: float) -> float:
    """Return the Right Ascension of the Midheaven Culminating (RAMC) in degrees.

    Parameters
    ----------
    jd      : Julian Day (UT)
    geo_lon : geographic longitude in degrees (positive east)
    """
    T = (jd - 2451545.0) / 36525.0
    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * T * T
        - T * T * T / 38710000.0
    ) % 360.0
    lst = (gmst_deg + geo_lon) % 360.0
    return lst  # RAMC == LST


# ---------------------------------------------------------------------------
# Rising decan (Ascendant-based)
# ---------------------------------------------------------------------------

def decan_at(
    jd: float,
    lat: float,
    lon: float,
) -> str:
    """Return the decan whose 10° zodiacal span contains the Ascendant at jd.

    The Ascendant ecliptic longitude is computed from RAMC, true obliquity,
    and geographic latitude using the standard Placidus formula.  The result
    is then mapped to a decan via ``decan_for_longitude``.

    Parameters
    ----------
    jd     : Julian Day (UT)
    lat    : geographic latitude in degrees (positive north)
    lon    : geographic longitude in degrees (positive east)
    Returns
    -------
    Decan name (member of list_decans())
    """
    ramc = _lst_to_ramc(jd, lon)
    ramc_r = math.radians(ramc)
    obl_r  = math.radians(true_obliquity(ut_to_tt(jd)))
    lat_r  = math.radians(lat)

    asc_lon = math.degrees(math.atan2(
        math.cos(ramc_r),
        -(math.sin(ramc_r) * math.cos(obl_r) + math.tan(lat_r) * math.sin(obl_r)),
    )) % 360.0

    return decan_for_longitude(asc_lon)

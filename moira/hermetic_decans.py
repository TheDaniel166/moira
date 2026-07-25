"""
Moira — Hermetic Decan Engine
==============================

Archetype: Engine

Status
------
**Research quarantine.** The 36 names and planetary faces have been
reconstructed from Gundel's 1936 edition of British Library Harley MS 3731,
ff. 1r-50r. The catalog has not yet passed the later public-admission gates,
and the lookup/night geometry has not been established by this reconstruction.
The module remains excluded from the package root, facade, and REST application.

Purpose
-------
Preserves the source-identified catalog, quarantined tropical lookup geometry,
rising-decan calculation, and 12-part night division for source comparison.
Only each catalog entry's name, sign order, planetary face, and edition page
are source-reconstructed here.

Tradition and frame of reference
---------------------------------
The edited Harley text orders three decans under each of the twelve signs and
assigns each a planetary face. Moira's equal tropical 10° lookup is retained
only as quarantined research geometry; this source pass does not claim that a
modern equinox-fixed longitude realizes the manuscript's complete doctrine.

Fixed-star non-admission
------------------------
The former one-fixed-star-per-decan table has no support in the identified
edition. ``DECAN_RULING_STARS`` is therefore empty, and fixed-star accessors
fail closed. Planetary faces are stored separately in
``DECAN_PLANETARY_FACES``.

Boundary declaration
--------------------
Owns: the 36-decan source catalog, planetary-face table, decan-order list,
      decan-for-longitude mapping, rising-decan computation, night-hour
      division, and the ``DecanHour`` / ``DecanHoursNight`` result vessels.
Delegates: true obliquity to ``moira.obliquity``,
           SpkReader access to ``moira.spk_reader``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Rising-decan and night-hour
computations require a valid ``SpkReader`` (or the module singleton).

Research surface
----------------
``DecanHour``          — vessel for a single decan night hour.
``DecanHoursNight``    — vessel for all 12 decan hours of a night.
``DECAN_NAMES``        — dict of decan constant to name string (36 entries).
``DECAN_PLANETARY_FACES`` — source-reconstructed planetary faces.
``HERMETIC_DECAN_CATALOG`` — typed records with source pages.
``DECAN_RULING_STARS`` — empty compatibility marker; no admitted assignments.
``list_decans``        — return all 36 decan names in ecliptic order.
``available_decans``   — return no star-backed decans (fail-closed).
``decan_for_longitude``— map a longitude to its decan name.
``decan_at``           — return the decan containing the Ascendant at a given JD and location.
``decan_hours``        — compute the 12 decan night hours for a given night.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .julian import ut_to_tt
from ._ephemeris_time import _ut1_to_ephemeris_tt
from .obliquity import true_obliquity
from .spk_reader import get_reader, SpkReader
from ._solar import _sunrise_sunset, _refine_sunrise

# ---------------------------------------------------------------------------
# Source-reconstructed Harley MS 3731 catalog
#
# Authority: Wilhelm Gundel, Dekane und Dekansternbilder (1936), pp. 379-383,
# section "Die lateinische Dekanliste des Hermes Trismegistos", transcribing
# British Library Harley MS 3731, ff. 1r-50r. The edition supplies names and
# planetary faces. It does not supply the fixed-star assignments previously
# stored here; those assignments are therefore removed and fail closed.
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

    Applies Moira's quarantined equal 10° tropical lookup geometry. The
    source reconstruction establishes name order within the twelve signs;
    it does not by itself admit this modern lookup frame as public doctrine.

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


def _refine_solar_event_near(
    jd_guess: float,
    lat: float,
    lon: float,
    reader: SpkReader,
    *,
    is_rise: bool,
) -> float:
    """Refine a sunrise/sunset approximation while preserving day locality."""
    jd_event = _refine_sunrise(jd_guess, lat, lon, reader, is_rise=is_rise)
    if not math.isfinite(jd_event):
        raise ValueError("solar event refinement returned a non-finite JD")
    day_shift = round(jd_guess - jd_event)
    if abs(jd_guess - jd_event) > 0.75:
        jd_event += day_shift
    return jd_event


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


# ---------------------------------------------------------------------------
# Decan night hours
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class DecanHour:
    """
    RITE: The Hour Vessel — a single decan night hour and its planetary face.

    THEOREM: Holds the hour number, decan name, planetary face, and start/end
    Julian Days for one of the 12 decan night hours.

    RITE OF PURPOSE:
        Serves the Hermetic Decan Engine as the atomic unit of night-hour
        division. Without this vessel, ``DecanHoursNight`` would have no
        structured per-hour representation, making hour-at-JD lookup and
        decan-of-hour queries impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store hour number (1-12), decan name, planetary face, and
              the JD boundaries of the hour.
        Non-responsibilities:
            - Does not compute hour boundaries (delegated to ``decan_hours``).
            - Does not validate that ``hour_number`` is in [1, 12].
        Dependencies:
            - Populated exclusively by ``decan_hours()``.
        Structural invariants:
            - ``jd_start < jd_end`` always holds.
            - ``hour_number`` is always in [1, 12].
        Succession stance: terminal — not designed for subclassing.

    Canon: Liber Hermetis (~200 AD); Firmicus Maternus, "Mathesis" (~334 AD).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.hermetic_decans.DecanHour",
        "risk": "low",
        "api": {
            "public_methods": [],
            "public_attributes": [
                "hour_number", "decan", "planetary_face", "jd_start", "jd_end"
            ]
        },
        "state": {
            "mutable": false,
            "fields": ["hour_number", "decan", "planetary_face", "jd_start", "jd_end"]
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
            "policy": "caller ensures valid JD boundaries before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    hour_number:    int    # 1–12
    decan:          str
    planetary_face: str
    jd_start:       float
    jd_end:         float

    def __post_init__(self) -> None:
        if not (1 <= self.hour_number <= 12):
            raise ValueError(
                f"DecanHour.hour_number must be in [1, 12], got {self.hour_number}"
            )
        if self.decan not in DECAN_PLANETARY_FACES:
            raise ValueError(f"DecanHour.decan must be a valid decan name, got {self.decan!r}")
        if self.planetary_face != DECAN_PLANETARY_FACES[self.decan]:
            raise ValueError(
                "DecanHour.planetary_face must match the catalog face: "
                f"{self.decan!r} -> {DECAN_PLANETARY_FACES[self.decan]!r}, "
                f"got {self.planetary_face!r}"
            )
        if not math.isfinite(self.jd_start) or not math.isfinite(self.jd_end):
            raise ValueError("DecanHour.jd_start and .jd_end must be finite")
        if not self.jd_start < self.jd_end:
            raise ValueError(
                f"DecanHour must satisfy jd_start < jd_end, got {self.jd_start} >= {self.jd_end}"
            )


@dataclass(slots=True, frozen=True)
class DecanHoursNight:
    """
    RITE: The Night Vessel — all 12 decan hours of a single night.

    THEOREM: Holds the sunset and next-sunrise Julian Days, observer location,
    and the ordered list of 12 ``DecanHour`` instances dividing the night.

    RITE OF PURPOSE:
        Serves the Hermetic Decan Engine as the top-level result vessel for
        nightly decan hour computation. Without this vessel, callers would
        receive a bare list of hours with no night-boundary context, making
        ``hour_at`` and ``decan_of_hour`` queries structurally impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store the reference JD, observer latitude/longitude, sunset JD,
              next-sunrise JD, and the 12 ``DecanHour`` instances.
            - Expose ``hour_at(jd)`` to return the hour containing a given JD.
            - Expose ``decan_of_hour(jd)`` to return the decan name for a JD.
        Non-responsibilities:
            - Does not compute night boundaries (delegated to ``decan_hours``).
            - Does not validate that ``hours`` contains exactly 12 entries.
        Dependencies:
            - Populated exclusively by ``decan_hours()``.
            - ``hours`` contains ``DecanHour`` instances from this module.
        Structural invariants:
            - ``sunset_jd < next_sunrise_jd`` always holds.
            - ``hours`` always contains exactly 12 entries.
        Succession stance: terminal — not designed for subclassing.

    Canon: Liber Hermetis (~200 AD); Firmicus Maternus, "Mathesis" (~334 AD).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.hermetic_decans.DecanHoursNight",
        "risk": "medium",
        "api": {
            "public_methods": ["hour_at", "decan_of_hour"],
            "public_attributes": [
                "date_jd", "latitude", "longitude",
                "sunset_jd", "next_sunrise_jd", "hours"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "date_jd", "latitude", "longitude",
                "sunset_jd", "next_sunrise_jd", "hours"
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
            "policy": "caller ensures valid night boundaries before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    date_jd:         float
    latitude:        float
    longitude:       float
    sunset_jd:       float
    next_sunrise_jd: float
    hours:           tuple[DecanHour, ...]

    def __post_init__(self) -> None:
        tol = 1e-12
        object.__setattr__(self, "hours", tuple(self.hours))
        if not math.isfinite(self.date_jd):
            raise ValueError(f"DecanHoursNight.date_jd must be finite, got {self.date_jd!r}")
        if not math.isfinite(self.latitude) or not math.isfinite(self.longitude):
            raise ValueError("DecanHoursNight.latitude and .longitude must be finite")
        if not math.isfinite(self.sunset_jd) or not math.isfinite(self.next_sunrise_jd):
            raise ValueError("DecanHoursNight.sunset_jd and .next_sunrise_jd must be finite")
        if not self.sunset_jd < self.next_sunrise_jd:
            raise ValueError(
                "DecanHoursNight must satisfy sunset_jd < next_sunrise_jd, "
                f"got {self.sunset_jd} >= {self.next_sunrise_jd}"
            )
        if len(self.hours) != 12:
            raise ValueError(
                f"DecanHoursNight.hours must contain exactly 12 entries, got {len(self.hours)}"
            )
        for idx, hour in enumerate(self.hours, start=1):
            if not isinstance(hour, DecanHour):
                raise TypeError(
                    f"DecanHoursNight.hours[{idx - 1}] must be a DecanHour, got {type(hour).__name__}"
                )
            if hour.hour_number != idx:
                raise ValueError(
                    "DecanHoursNight.hours must be sequentially numbered from 1 to 12, "
                    f"got hour_number={hour.hour_number} at position {idx}"
                )
        if not math.isclose(self.hours[0].jd_start, self.sunset_jd, abs_tol=tol):
            raise ValueError("DecanHoursNight first hour must begin at sunset_jd")
        if not math.isclose(self.hours[-1].jd_end, self.next_sunrise_jd, abs_tol=tol):
            raise ValueError("DecanHoursNight last hour must end at next_sunrise_jd")
        for earlier, later in zip(self.hours, self.hours[1:]):
            if not math.isclose(earlier.jd_end, later.jd_start, abs_tol=tol):
                raise ValueError("DecanHoursNight.hours must form a gap-free partition of the night")

    def hour_at(self, jd: float) -> DecanHour | None:
        """Return the DecanHour containing the given JD, or None if outside the night."""
        for h in self.hours:
            if h.jd_start <= jd < h.jd_end:
                return h
        return None

    def decan_of_hour(self, jd: float) -> str | None:
        """Return the decan name for the hour containing jd, or None if outside the night."""
        h = self.hour_at(jd)
        return h.decan if h else None


def decan_hours(
    jd: float,
    lat: float,
    lon: float,
    reader: SpkReader | None = None,
) -> DecanHoursNight:
    """Compute the 12 decan night hours for the night containing jd.

    Parameters
    ----------
    jd     : Julian Day (UT) — any time during the target day/night
    lat    : geographic latitude in degrees (positive north)
    lon    : geographic longitude in degrees (positive east)
    reader : SpkReader instance (falls back to get_reader() if None)

    Returns
    -------
    DecanHoursNight with 12 DecanHour instances covering sunset to next sunrise.
    """
    if reader is None:
        reader = get_reader()

    # Approximate local-civil day anchors from the UT date containing jd.
    jd_noon = math.floor(jd - 0.5) + 1.0

    # Current day's sunrise and sunset.
    jd_sr_approx, jd_ss_approx = _sunrise_sunset(jd_noon, lat, lon, reader)
    jd_sunrise_today = _refine_solar_event_near(
        jd_sr_approx, lat, lon, reader, is_rise=True
    )
    jd_sunset_today = _refine_solar_event_near(
        jd_ss_approx, lat, lon, reader, is_rise=False
    )

    if jd < jd_sunrise_today:
        jd_prev_noon = jd_noon - 1.0
        _, jd_prev_ss_approx = _sunrise_sunset(jd_prev_noon, lat, lon, reader)
        jd_sunset = _refine_solar_event_near(
            jd_prev_ss_approx, lat, lon, reader, is_rise=False
        )
        jd_next_sunrise = jd_sunrise_today
    else:
        jd_next_noon = jd_noon + 1.0
        jd_nr_approx, _ = _sunrise_sunset(jd_next_noon, lat, lon, reader)
        jd_sunset = jd_sunset_today
        jd_next_sunrise = _refine_solar_event_near(
            jd_nr_approx, lat, lon, reader, is_rise=True
        )

    if not math.isfinite(jd_sunset) or not math.isfinite(jd_next_sunrise):
        raise ValueError("decan_hours could not determine a finite sunset/sunrise boundary")
    if not jd_sunset < jd_next_sunrise:
        raise ValueError(
            "decan_hours requires a valid night with sunset before next sunrise; "
            f"got sunset={jd_sunset}, next_sunrise={jd_next_sunrise}"
        )

    # Decan culminating on the MC at sunset → starting index
    # (Liber Hermetis: the first hour of the night is ruled by the decan
    # on the Midheaven at sunset, not the decan rising on the Ascendant.)
    ramc_sunset = _lst_to_ramc(jd_sunset, lon)
    obl_sunset = true_obliquity(
        _ut1_to_ephemeris_tt(jd_sunset, reader)
    )
    mc_lon = math.degrees(math.atan2(
        math.sin(math.radians(ramc_sunset)),
        math.cos(math.radians(ramc_sunset)) * math.cos(math.radians(obl_sunset)),
    )) % 360.0
    start_decan_name = decan_for_longitude(mc_lon)
    start_decan_idx = decan_index(start_decan_name)

    # Divide night into 12 equal hours
    night_duration = jd_next_sunrise - jd_sunset
    hour_len = night_duration / 12.0

    hours: list[DecanHour] = []
    for i in range(12):
        idx = (start_decan_idx + i) % 36
        decan_name = _DECAN_ORDER[idx]
        jd_start = jd_sunset + i * hour_len
        jd_end   = jd_start + hour_len
        hours.append(DecanHour(
            hour_number=i + 1,
            decan=decan_name,
            planetary_face=DECAN_PLANETARY_FACES[decan_name],
            jd_start=jd_start,
            jd_end=jd_end,
        ))

    return DecanHoursNight(
        date_jd=jd,
        latitude=lat,
        longitude=lon,
        sunset_jd=jd_sunset,
        next_sunrise_jd=jd_next_sunrise,
        hours=hours,
    )

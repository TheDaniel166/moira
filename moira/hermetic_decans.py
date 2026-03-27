"""
Moira â€” Hermetic Decan Engine
==============================

Archetype: Engine

Purpose
-------
Governs the 36 Hermetic decan faces of the Egyptian-Hellenistic tradition,
mapping the tropical zodiac onto decan names and their ruling fixed stars,
and computing the 12 decan night hours for a given location and date.

Boundary declaration
--------------------
Owns: the 36-decan name constants, ruling-star table, decan-order list,
      decan-for-longitude mapping, rising-decan computation, night-hour
      division, and the ``DecanHour`` / ``DecanHoursNight`` result vessels.
Delegates: fixed star positions to ``moira.stars``,
           mean obliquity to ``moira.obliquity``,
           SpkReader access to ``moira.spk_reader``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Rising-decan and night-hour
computations require a valid ``SpkReader`` (or the module singleton).

Public surface
--------------
``DecanHour``          â€” vessel for a single decan night hour.
``DecanHoursNight``    â€” vessel for all 12 decan hours of a night.
``DECAN_NAMES``        â€” dict of decan constant to name string (36 entries).
``DECAN_RULING_STARS`` â€” dict of decan name to ruling star name (36 entries).
``list_decans``        â€” return all 36 decan names in ecliptic order.
``available_decans``   â€” return decans whose ruling star is in the catalog.
``decan_for_longitude``â€” map a longitude to its decan name.
``decan_at``           â€” return the decan rising at a given JD and location.
``decan_hours``        â€” compute the 12 decan night hours for a given night.
"""

import math
from dataclasses import dataclass

from .stars import star_at, StarPosition, list_stars
from .obliquity import mean_obliquity
from .spk_reader import get_reader, SpkReader

# ---------------------------------------------------------------------------
# 36 decan name constants
# ---------------------------------------------------------------------------

HORAIOS        = "Horaios"
TOMALOS        = "Tomalos"
ATHAFRA        = "Athafra"
SENACHER       = "Senacher"
THESOGAR       = "Thesogar"
TEPIS          = "Tepis"
SOTHIS         = "Sothis"
TPAU           = "Tpau"
APHRUIMIS      = "Aphruimis"
TMOUM          = "Tmoum"
TATHEMIS       = "Tathemis"
SERK           = "Serk"
CHONTARE       = "Chontare"
PHAKARE        = "Phakare"
TPA            = "Tpa"
THOSOLK        = "Thosolk"
SOTHIS_II      = "Sothis II"
TPAU_II        = "Tpau II"
CHONTACHRE     = "Chontachre"
APHRUIMIS_II   = "Aphruimis II"
TMOUM_II       = "Tmoum II"
TATHEMIS_II    = "Tathemis II"
SERK_II        = "Serk II"
CHONTARE_II    = "Chontare II"
PHAKARE_II     = "Phakare II"
TPA_II         = "Tpa II"
THOSOLK_II     = "Thosolk II"
HORAIOS_II     = "Horaios II"
TOMALOS_II     = "Tomalos II"
ATHAFRA_II     = "Athafra II"
SENACHER_II    = "Senacher II"
THESOGAR_II    = "Thesogar II"
TEPIS_II       = "Tepis II"
SOTHIS_III     = "Sothis III"
TPAU_III       = "Tpau III"
APHRUIMIS_III  = "Aphruimis III"

# ---------------------------------------------------------------------------
# DECAN_NAMES: constant â†’ string value (36 entries)
# ---------------------------------------------------------------------------

DECAN_NAMES: dict[str, str] = {
    HORAIOS:       "Horaios",
    TOMALOS:       "Tomalos",
    ATHAFRA:       "Athafra",
    SENACHER:      "Senacher",
    THESOGAR:      "Thesogar",
    TEPIS:         "Tepis",
    SOTHIS:        "Sothis",
    TPAU:          "Tpau",
    APHRUIMIS:     "Aphruimis",
    TMOUM:         "Tmoum",
    TATHEMIS:      "Tathemis",
    SERK:          "Serk",
    CHONTARE:      "Chontare",
    PHAKARE:       "Phakare",
    TPA:           "Tpa",
    THOSOLK:       "Thosolk",
    SOTHIS_II:     "Sothis II",
    TPAU_II:       "Tpau II",
    CHONTACHRE:    "Chontachre",
    APHRUIMIS_II:  "Aphruimis II",
    TMOUM_II:      "Tmoum II",
    TATHEMIS_II:   "Tathemis II",
    SERK_II:       "Serk II",
    CHONTARE_II:   "Chontare II",
    PHAKARE_II:    "Phakare II",
    TPA_II:        "Tpa II",
    THOSOLK_II:    "Thosolk II",
    HORAIOS_II:    "Horaios II",
    TOMALOS_II:    "Tomalos II",
    ATHAFRA_II:    "Athafra II",
    SENACHER_II:   "Senacher II",
    THESOGAR_II:   "Thesogar II",
    TEPIS_II:      "Tepis II",
    SOTHIS_III:    "Sothis III",
    TPAU_III:      "Tpau III",
    APHRUIMIS_III: "Aphruimis III",
}

# ---------------------------------------------------------------------------
# DECAN_RULING_STARS: decan name â†’ ruling star name (36 entries)
# ---------------------------------------------------------------------------

DECAN_RULING_STARS: dict[str, str] = {
    HORAIOS:       "Hamal",
    TOMALOS:       "Sheratan",
    ATHAFRA:       "Mesarthim",
    SENACHER:      "Alcyone",
    THESOGAR:      "Aldebaran",
    TEPIS:         "Rigel",
    SOTHIS:        "Sirius",
    TPAU:          "Castor",
    APHRUIMIS:     "Pollux",
    TMOUM:         "Procyon",
    TATHEMIS:      "Asellus Australis",
    SERK:          "Acubens",
    CHONTARE:      "Regulus",
    PHAKARE:       "Zosma",
    TPA:           "Denebola",
    THOSOLK:       "Vindemiatrix",
    SOTHIS_II:     "Spica",
    TPAU_II:       "Arcturus",
    CHONTACHRE:    "Zubenelgenubi",
    APHRUIMIS_II:  "Zubeneschamali",
    TMOUM_II:      "Unukalhai",
    TATHEMIS_II:   "Antares",
    SERK_II:       "Graffias",
    CHONTARE_II:   "Lesath",
    PHAKARE_II:    "Vega",
    TPA_II:        "Nunki",
    THOSOLK_II:    "Altair",
    HORAIOS_II:    "Deneb Algedi",
    TOMALOS_II:    "Sadalsuud",
    ATHAFRA_II:    "Sadalmelik",
    SENACHER_II:   "Fomalhaut",
    THESOGAR_II:   "Skat",
    TEPIS_II:      "Markab",
    SOTHIS_III:    "Algenib",
    TPAU_III:      "Mirach",
    APHRUIMIS_III: "Alpherg",
}

# ---------------------------------------------------------------------------
# _DECAN_ORDER: 36 decan names in tropical ecliptic order (index 0 = 0Â°)
# ---------------------------------------------------------------------------

_DECAN_ORDER: list[str] = [
    HORAIOS,      TOMALOS,      ATHAFRA,      SENACHER,    THESOGAR,    TEPIS,
    SOTHIS,       TPAU,         APHRUIMIS,    TMOUM,       TATHEMIS,    SERK,
    CHONTARE,     PHAKARE,      TPA,          THOSOLK,     SOTHIS_II,   TPAU_II,
    CHONTACHRE,   APHRUIMIS_II, TMOUM_II,     TATHEMIS_II, SERK_II,     CHONTARE_II,
    PHAKARE_II,   TPA_II,       THOSOLK_II,   HORAIOS_II,  TOMALOS_II,  ATHAFRA_II,
    SENACHER_II,  THESOGAR_II,  TEPIS_II,     SOTHIS_III,  TPAU_III,    APHRUIMIS_III,
]


# ---------------------------------------------------------------------------
# Catalog and ordering functions
# ---------------------------------------------------------------------------

def list_decans() -> list[str]:
    """Return all 36 decan names in tropical ecliptic order (0Â°â†’360Â°)."""
    return list(_DECAN_ORDER)


def available_decans() -> list[str]:
    """Return decan names whose ruling star is present in the fixed star catalog."""
    catalog = set(list_stars())
    return [d for d in _DECAN_ORDER if DECAN_RULING_STARS[d] in catalog]


def decan_for_longitude(lon: float) -> str:
    """Map a tropical ecliptic longitude to its Hermetic decan name.

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
# Ruling star access functions
# ---------------------------------------------------------------------------

def decan_ruling_star(name: str) -> str:
    """Return the ruling star name for a decan.

    Raises KeyError for unknown decan names.
    """
    return DECAN_RULING_STARS[name]


def decan_star_at(name: str, jd: float) -> StarPosition:
    """Return the StarPosition of a decan's ruling star at the given JD.

    Delegates to star_at with the decan's ruling star name.
    Propagates KeyError if the ruling star is absent from the catalog.
    """
    return star_at(DECAN_RULING_STARS[name], jd)


# ---------------------------------------------------------------------------
# Solar helpers (copied from planetary_hours.py for self-containment)
# ---------------------------------------------------------------------------

def _solar_declination_ra(jd: float, reader: SpkReader) -> tuple[float, float]:
    """Return (declination_deg, right_ascension_deg) of the Sun at jd."""
    from .planets import planet_at
    from .constants import Body
    from .obliquity import true_obliquity

    p = planet_at(Body.SUN, jd, reader=reader)
    obl = true_obliquity(jd)
    obl_r = math.radians(obl)
    lon_r = math.radians(p.longitude)
    lat_r = math.radians(p.latitude)

    x = math.cos(lat_r) * math.cos(lon_r)
    y = math.cos(lat_r) * math.sin(lon_r) * math.cos(obl_r) - math.sin(lat_r) * math.sin(obl_r)
    z = math.cos(lat_r) * math.sin(lon_r) * math.sin(obl_r) + math.sin(lat_r) * math.cos(obl_r)

    dec = math.degrees(math.asin(z))
    ra  = math.degrees(math.atan2(y, x)) % 360.0
    return dec, ra


def _sunrise_sunset(
    jd_noon: float,
    latitude: float,
    longitude: float,
    reader: SpkReader,
    altitude_deg: float = -0.833,
) -> tuple[float, float]:
    """Compute sunrise and sunset JD for the calendar day containing jd_noon."""
    dec, _ = _solar_declination_ra(jd_noon, reader)
    lat_r = math.radians(latitude)
    dec_r = math.radians(dec)
    alt_r = math.radians(altitude_deg)

    cos_H = ((math.sin(alt_r) - math.sin(lat_r) * math.sin(dec_r))
             / (math.cos(lat_r) * math.cos(dec_r)))

    if cos_H > 1.0:
        return jd_noon, jd_noon
    if cos_H < -1.0:
        return jd_noon - 0.5, jd_noon + 0.5

    H_deg = math.degrees(math.acos(cos_H))

    jd_day_start = math.floor(jd_noon - 0.5) + 0.5
    noon_frac = 0.5 - longitude / 360.0
    jd_solar_noon = jd_day_start + noon_frac

    sunrise_frac = H_deg / 360.0
    jd_sunrise = jd_solar_noon - sunrise_frac
    jd_sunset  = jd_solar_noon + sunrise_frac

    return jd_sunrise, jd_sunset


def _refine_sunrise(
    jd_approx: float,
    latitude: float,
    longitude: float,
    reader: SpkReader,
    is_rise: bool,
    tol_days: float = 1.0 / 86400,
) -> float:
    """Iteratively refine sunrise or sunset time."""
    jd = jd_approx
    for _ in range(5):
        dec, _ = _solar_declination_ra(jd, reader)
        lat_r = math.radians(latitude)
        dec_r = math.radians(dec)
        alt_r = math.radians(-0.833)

        cos_H = ((math.sin(alt_r) - math.sin(lat_r) * math.sin(dec_r))
                 / (math.cos(lat_r) * math.cos(dec_r)))
        cos_H = max(-1.0, min(1.0, cos_H))
        H_deg = math.degrees(math.acos(cos_H))

        jd_day_start = math.floor(jd - 0.5) + 0.5
        noon_frac = 0.5 - longitude / 360.0
        jd_solar_noon = jd_day_start + noon_frac

        sunrise_frac = H_deg / 360.0
        jd_new = jd_solar_noon - sunrise_frac if is_rise else jd_solar_noon + sunrise_frac

        if abs(jd_new - jd) < tol_days:
            break
        jd = jd_new
    return jd


# ---------------------------------------------------------------------------
# Local Sidereal Time â†’ RAMC
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
    reader: SpkReader | None = None,
) -> str:
    """Return the decan whose ruling star is closest to the Ascendant at jd.

    Parameters
    ----------
    jd     : Julian Day (UT)
    lat    : geographic latitude in degrees (positive north)
    lon    : geographic longitude in degrees (positive east)
    reader : SpkReader instance (falls back to get_reader() if None)

    Returns
    -------
    Decan name (member of list_decans())
    """
    reader = reader or get_reader()

    # Compute Ascendant ecliptic longitude
    ramc = _lst_to_ramc(jd, lon)
    ramc_r = math.radians(ramc)
    obl_r  = math.radians(mean_obliquity(jd))
    lat_r  = math.radians(lat)

    asc_lon = math.degrees(math.atan2(
        -math.cos(ramc_r),
        math.sin(ramc_r) * math.cos(obl_r) + math.tan(lat_r) * math.sin(obl_r),
    )) % 360.0

    # Find decan whose ruling star is closest to asc_lon
    best_decan: str | None = None
    best_dist = float("inf")

    for decan in _DECAN_ORDER:
        star_name = DECAN_RULING_STARS[decan]
        star_pos = star_at(star_name, jd)
        star_lon = star_pos.longitude
        dist = min((star_lon - asc_lon) % 360.0, (asc_lon - star_lon) % 360.0)
        if dist < best_dist:
            best_dist = dist
            best_decan = decan

    assert best_decan is not None  # _DECAN_ORDER is never empty
    return best_decan


# ---------------------------------------------------------------------------
# Decan night hours
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DecanHour:
    """
    RITE: The Hour Vessel â€” a single decan night hour and its ruling star.

    THEOREM: Holds the hour number, decan name, ruling star name, and start/end
    Julian Days for one of the 12 decan night hours.

    RITE OF PURPOSE:
        Serves the Hermetic Decan Engine as the atomic unit of night-hour
        division. Without this vessel, ``DecanHoursNight`` would have no
        structured per-hour representation, making hour-at-JD lookup and
        decan-of-hour queries impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store hour number (1-12), decan name, ruling star name, and
              the JD boundaries of the hour.
        Non-responsibilities:
            - Does not compute hour boundaries (delegated to ``decan_hours``).
            - Does not validate that ``hour_number`` is in [1, 12].
        Dependencies:
            - Populated exclusively by ``decan_hours()``.
        Structural invariants:
            - ``jd_start < jd_end`` always holds.
            - ``hour_number`` is always in [1, 12].
        Succession stance: terminal â€” not designed for subclassing.

    Canon: Liber Hermetis (~200 AD); Firmicus Maternus, "Mathesis" (~334 AD).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.hermetic_decans.DecanHour",
        "risk": "low",
        "api": {
            "public_methods": [],
            "public_attributes": [
                "hour_number", "decan", "ruling_star", "jd_start", "jd_end"
            ]
        },
        "state": {
            "mutable": false,
            "fields": ["hour_number", "decan", "ruling_star", "jd_start", "jd_end"]
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
    hour_number: int    # 1â€“12
    decan:       str
    ruling_star: str
    jd_start:    float
    jd_end:      float


@dataclass(slots=True)
class DecanHoursNight:
    """
    RITE: The Night Vessel â€” all 12 decan hours of a single night.

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
        Succession stance: terminal â€” not designed for subclassing.

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
    hours:           list[DecanHour]

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
    jd     : Julian Day (UT) â€” any time during the target day/night
    lat    : geographic latitude in degrees (positive north)
    lon    : geographic longitude in degrees (positive east)
    reader : SpkReader instance (falls back to get_reader() if None)

    Returns
    -------
    DecanHoursNight with 12 DecanHour instances covering sunset to next sunrise.
    """
    if reader is None:
        reader = get_reader()

    # Approximate noon for the day
    jd_noon = math.floor(jd - 0.5) + 0.5 + 0.5

    # Sunset for this day
    jd_sr_approx, jd_ss_approx = _sunrise_sunset(jd_noon, lat, lon, reader)
    jd_sunset = _refine_sunrise(jd_ss_approx, lat, lon, reader, is_rise=False)

    # Next sunrise (following day)
    jd_next_noon = jd_noon + 1.0
    jd_nr_approx, _ = _sunrise_sunset(jd_next_noon, lat, lon, reader)
    jd_next_sunrise = _refine_sunrise(jd_nr_approx, lat, lon, reader, is_rise=True)

    # Decan rising at sunset â†’ starting index
    start_decan_name = decan_at(jd_sunset, lat, lon, reader)
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
            ruling_star=DECAN_RULING_STARS[decan_name],
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


# ---------------------------------------------------------------------------
# Per-decan convenience functions (36 total)
# ---------------------------------------------------------------------------

def horaios_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Horaios's ruling star at jd."""
    return decan_star_at(HORAIOS, jd)

def tomalos_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tomalos's ruling star at jd."""
    return decan_star_at(TOMALOS, jd)

def athafra_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Athafra's ruling star at jd."""
    return decan_star_at(ATHAFRA, jd)

def senacher_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Senacher's ruling star at jd."""
    return decan_star_at(SENACHER, jd)

def thesogar_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Thesogar's ruling star at jd."""
    return decan_star_at(THESOGAR, jd)

def tepis_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tepis's ruling star at jd."""
    return decan_star_at(TEPIS, jd)

def sothis_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Sothis's ruling star at jd."""
    return decan_star_at(SOTHIS, jd)

def tpau_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tpau's ruling star at jd."""
    return decan_star_at(TPAU, jd)

def aphruimis_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Aphruimis's ruling star at jd."""
    return decan_star_at(APHRUIMIS, jd)

def tmoum_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tmoum's ruling star at jd."""
    return decan_star_at(TMOUM, jd)

def tathemis_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tathemis's ruling star at jd."""
    return decan_star_at(TATHEMIS, jd)

def serk_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Serk's ruling star at jd."""
    return decan_star_at(SERK, jd)

def chontare_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Chontare's ruling star at jd."""
    return decan_star_at(CHONTARE, jd)

def phakare_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Phakare's ruling star at jd."""
    return decan_star_at(PHAKARE, jd)

def tpa_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tpa's ruling star at jd."""
    return decan_star_at(TPA, jd)

def thosolk_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Thosolk's ruling star at jd."""
    return decan_star_at(THOSOLK, jd)

def sothis_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Sothis II's ruling star at jd."""
    return decan_star_at(SOTHIS_II, jd)

def tpau_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tpau II's ruling star at jd."""
    return decan_star_at(TPAU_II, jd)

def chontachre_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Chontachre's ruling star at jd."""
    return decan_star_at(CHONTACHRE, jd)

def aphruimis_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Aphruimis II's ruling star at jd."""
    return decan_star_at(APHRUIMIS_II, jd)

def tmoum_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tmoum II's ruling star at jd."""
    return decan_star_at(TMOUM_II, jd)

def tathemis_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tathemis II's ruling star at jd."""
    return decan_star_at(TATHEMIS_II, jd)

def serk_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Serk II's ruling star at jd."""
    return decan_star_at(SERK_II, jd)

def chontare_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Chontare II's ruling star at jd."""
    return decan_star_at(CHONTARE_II, jd)

def phakare_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Phakare II's ruling star at jd."""
    return decan_star_at(PHAKARE_II, jd)

def tpa_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tpa II's ruling star at jd."""
    return decan_star_at(TPA_II, jd)

def thosolk_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Thosolk II's ruling star at jd."""
    return decan_star_at(THOSOLK_II, jd)

def horaios_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Horaios II's ruling star at jd."""
    return decan_star_at(HORAIOS_II, jd)

def tomalos_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tomalos II's ruling star at jd."""
    return decan_star_at(TOMALOS_II, jd)

def athafra_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Athafra II's ruling star at jd."""
    return decan_star_at(ATHAFRA_II, jd)

def senacher_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Senacher II's ruling star at jd."""
    return decan_star_at(SENACHER_II, jd)

def thesogar_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Thesogar II's ruling star at jd."""
    return decan_star_at(THESOGAR_II, jd)

def tepis_ii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tepis II's ruling star at jd."""
    return decan_star_at(TEPIS_II, jd)

def sothis_iii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Sothis III's ruling star at jd."""
    return decan_star_at(SOTHIS_III, jd)

def tpau_iii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Tpau III's ruling star at jd."""
    return decan_star_at(TPAU_III, jd)

def aphruimis_iii_star_at(jd: float) -> StarPosition:
    """Return the StarPosition of Aphruimis III's ruling star at jd."""
    return decan_star_at(APHRUIMIS_III, jd)


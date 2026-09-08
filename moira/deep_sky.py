"""Curated deep-sky coordinate anchors with explicit source boundaries.

This module owns identity lookup and true-ecliptic-of-date projection for a
small, release-bound catalog of galaxies, nebulae, clusters, compact systems,
stellar remnants, and confirmed exoplanet host stars.  Extended objects are
represented by catalog centers; Solar-System bodies are deliberately absent.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

from .constants import J2000, sign_of
from .coordinates import icrf_to_true_ecliptic
from .stars import star_at, star_name_resolves


__all__ = [
    "DeepSkyClass",
    "DeepSkyObject",
    "DeepSkyPosition",
    "deep_sky_object",
    "deep_sky_at",
    "all_deep_sky_at",
    "list_deep_sky_objects",
    "find_deep_sky_objects",
]


_DATA_DIR = Path(__file__).resolve().parent / "data"
_CATALOG_PATH = _DATA_DIR / "deep_sky_catalog.json"
_METADATA_PATH = _DATA_DIR / "deep_sky_catalog.metadata.json"
_MAS_TO_RAD = math.radians(1.0 / 3_600_000.0)


class DeepSkyClass(str, Enum):
    """Vessel: Stable object classes admitted by the deep-sky catalog."""

    GALAXY = "galaxy"
    NEBULA = "nebula"
    STAR_CLUSTER = "star_cluster"
    COMPACT_OBJECT = "compact_object"
    STELLAR_REMNANT = "stellar_remnant"
    HOST_STAR = "host_star"


@dataclass(frozen=True, slots=True)
class DeepSkyObject:
    """Vessel: One source-bound object identity and J2000 coordinate anchor."""

    canonical_name: str
    designation: str
    aliases: tuple[str, ...]
    object_class: DeepSkyClass
    is_extended: bool
    position_semantics: str
    simbad_main_id: str
    simbad_otype: str
    ra_deg: float
    dec_deg: float
    pmra_mas_yr: float | None
    pmdec_mas_yr: float | None
    proper_motion_admitted: bool
    coordinate_bibcode: str
    coordinate_quality: str
    star_registry_name: str | None
    nasa_exoplanet_archive_hostname: str | None
    confirmed_planet_count: int | None
    catalog_version: str


@dataclass(frozen=True, slots=True)
class DeepSkyPosition:
    """Vessel: True ecliptic-of-date direction for one deep-sky anchor."""

    name: str
    designation: str
    object_class: DeepSkyClass
    longitude: float
    latitude: float
    sign: str
    sign_symbol: str
    sign_degree: float
    jd_tt: float
    source_ra_deg: float
    source_dec_deg: float
    source_frame: str
    source_epoch_jd_tt: float
    position_semantics: str
    position_source: str
    proper_motion_applied: bool
    simbad_main_id: str
    coordinate_bibcode: str
    coordinate_quality: str
    catalog_version: str


def _sha256_bytes(payload: bytes) -> str:
    """Return the lowercase SHA-256 digest for catalog verification."""

    return hashlib.sha256(payload).hexdigest()


def _normalized_label(value: str) -> str:
    """Normalize one user-visible identity label for exact lookup."""

    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _optional_float(value: object) -> float | None:
    """Coerce one optional finite catalog number."""

    if value is None:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("deep-sky catalog contains a non-finite number")
    return result


@lru_cache(maxsize=1)
def _load_catalog() -> tuple[tuple[DeepSkyObject, ...], dict[str, object]]:
    """Load and verify the release-bound data artifact and provenance receipt."""

    try:
        catalog_bytes = _CATALOG_PATH.read_bytes()
        payload = json.loads(catalog_bytes.decode("utf-8"))
        metadata = json.loads(_METADATA_PATH.read_text(encoding="utf-8"))
        artifact = metadata["artifact"]
        if artifact["path"] != "moira/data/deep_sky_catalog.json":
            raise ValueError("catalog receipt path is invalid")
        if _sha256_bytes(catalog_bytes) != artifact["sha256"]:
            raise ValueError("catalog SHA-256 does not match its receipt")
        if payload["schema_version"] != 1 or metadata["schema_version"] != 1:
            raise ValueError("unsupported deep-sky catalog schema")
        if payload["catalog_id"] != "moira-deep-sky" or metadata["catalog_id"] != "moira-deep-sky":
            raise ValueError("unexpected deep-sky catalog identity")
        if payload["catalog_version"] != metadata["catalog_version"]:
            raise ValueError("catalog and metadata versions disagree")
        raw_records = payload["records"]
        if not isinstance(raw_records, list) or len(raw_records) != int(artifact["record_count"]):
            raise ValueError("catalog record count does not match its receipt")

        records: list[DeepSkyObject] = []
        class_counts: dict[str, int] = {}
        labels: dict[str, str] = {}
        for raw in raw_records:
            object_class = DeepSkyClass(str(raw["object_class"]))
            ra_deg = float(raw["ra_deg"])
            dec_deg = float(raw["dec_deg"])
            if not (math.isfinite(ra_deg) and 0.0 <= ra_deg < 360.0):
                raise ValueError(f"invalid right ascension for {raw['canonical_name']!r}")
            if not (math.isfinite(dec_deg) and -90.0 <= dec_deg <= 90.0):
                raise ValueError(f"invalid declination for {raw['canonical_name']!r}")
            pmra = _optional_float(raw.get("pmra_mas_yr"))
            pmdec = _optional_float(raw.get("pmdec_mas_yr"))
            proper_motion_admitted = bool(raw["proper_motion_admitted"])
            if proper_motion_admitted and (pmra is None or pmdec is None):
                raise ValueError(f"admitted proper motion is incomplete for {raw['canonical_name']!r}")
            confirmed_count = raw.get("confirmed_planet_count")
            confirmed_planet_count = None if confirmed_count is None else int(confirmed_count)
            star_registry_name = raw.get("star_registry_name")
            nasa_hostname = raw.get("nasa_exoplanet_archive_hostname")
            if object_class is DeepSkyClass.HOST_STAR:
                if not isinstance(star_registry_name, str) or not star_name_resolves(star_registry_name):
                    raise ValueError(f"host star {raw['canonical_name']!r} has no sovereign-star identity")
                if not isinstance(nasa_hostname, str) or not confirmed_planet_count or confirmed_planet_count < 1:
                    raise ValueError(f"host star {raw['canonical_name']!r} has no confirmed NASA identity")
            elif star_registry_name is not None or nasa_hostname is not None or confirmed_planet_count is not None:
                raise ValueError(f"non-host {raw['canonical_name']!r} carries host-star fields")

            record = DeepSkyObject(
                canonical_name=str(raw["canonical_name"]),
                designation=str(raw["designation"]),
                aliases=tuple(str(alias) for alias in raw["aliases"]),
                object_class=object_class,
                is_extended=bool(raw["is_extended"]),
                position_semantics=str(raw["position_semantics"]),
                simbad_main_id=str(raw["simbad_main_id"]),
                simbad_otype=str(raw["simbad_otype"]),
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                pmra_mas_yr=pmra,
                pmdec_mas_yr=pmdec,
                proper_motion_admitted=proper_motion_admitted,
                coordinate_bibcode=str(raw["coordinate_bibcode"]),
                coordinate_quality=str(raw["coordinate_quality"]),
                star_registry_name=star_registry_name,
                nasa_exoplanet_archive_hostname=nasa_hostname,
                confirmed_planet_count=confirmed_planet_count,
                catalog_version=str(payload["catalog_version"]),
            )
            class_counts[object_class.value] = class_counts.get(object_class.value, 0) + 1
            for label in (record.canonical_name, record.designation, *record.aliases, record.simbad_main_id):
                key = _normalized_label(label)
                owner = labels.get(key)
                if owner is not None and owner != record.canonical_name:
                    raise ValueError(f"deep-sky label {label!r} is ambiguous")
                labels[key] = record.canonical_name
            records.append(record)

        expected_counts = {str(key): int(value) for key, value in artifact["class_counts"].items()}
        if class_counts != expected_counts:
            raise ValueError("catalog class counts do not match their receipt")
        return tuple(records), metadata
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid packaged deep-sky catalog: {exc}") from exc


@lru_cache(maxsize=1)
def _lookup_index() -> dict[str, DeepSkyObject]:
    """Build the exact normalized identity index for all admitted labels."""

    records, _ = _load_catalog()
    result: dict[str, DeepSkyObject] = {}
    for record in records:
        for label in (record.canonical_name, record.designation, *record.aliases, record.simbad_main_id):
            result[_normalized_label(label)] = record
    return result


def _coerce_class(value: DeepSkyClass | str | None) -> DeepSkyClass | None:
    """Normalize an optional public object-class filter."""

    if value is None or isinstance(value, DeepSkyClass):
        return value
    try:
        return DeepSkyClass(value.strip().casefold())
    except (AttributeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in DeepSkyClass)
        raise ValueError(f"object_class must be one of: {allowed}") from exc


def deep_sky_object(name: str) -> DeepSkyObject:
    """Return one catalog record by canonical name, designation, or alias."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("deep-sky object name must be a non-empty string")
    record = _lookup_index().get(_normalized_label(name))
    if record is None:
        raise KeyError(f"Deep-sky object {name!r} is not in the released catalog")
    return record


def list_deep_sky_objects(object_class: DeepSkyClass | str | None = None) -> list[str]:
    """Return sorted canonical names, optionally restricted to one class."""

    selected_class = _coerce_class(object_class)
    records, _ = _load_catalog()
    return sorted(
        record.canonical_name
        for record in records
        if selected_class is None or record.object_class is selected_class
    )


def find_deep_sky_objects(
    fragment: str,
    object_class: DeepSkyClass | str | None = None,
) -> list[str]:
    """Search canonical names, designations, aliases, and SIMBAD identities."""

    if not isinstance(fragment, str):
        raise ValueError("fragment must be a string")
    selected_class = _coerce_class(object_class)
    needle = _normalized_label(fragment)
    records, _ = _load_catalog()
    matches = []
    for record in records:
        if selected_class is not None and record.object_class is not selected_class:
            continue
        labels = (record.canonical_name, record.designation, *record.aliases, record.simbad_main_id)
        if any(needle in _normalized_label(label) for label in labels):
            matches.append(record.canonical_name)
    return sorted(matches)


def _icrs_unit_vector(record: DeepSkyObject, jd_tt: float) -> tuple[tuple[float, float, float], bool]:
    """Return a J2000-basis direction with only explicitly admitted PM applied."""

    ra = math.radians(record.ra_deg)
    dec = math.radians(record.dec_deg)
    cos_dec = math.cos(dec)
    base = (cos_dec * math.cos(ra), cos_dec * math.sin(ra), math.sin(dec))
    if not record.proper_motion_admitted or jd_tt == J2000:
        return base, False
    assert record.pmra_mas_yr is not None and record.pmdec_mas_yr is not None
    dt_years = (jd_tt - J2000) / 365.25
    east = (-math.sin(ra), math.cos(ra), 0.0)
    north = (-math.sin(dec) * math.cos(ra), -math.sin(dec) * math.sin(ra), cos_dec)
    dra_cosdec = record.pmra_mas_yr * _MAS_TO_RAD
    ddec = record.pmdec_mas_yr * _MAS_TO_RAD
    propagated = (
        base[0] + (dra_cosdec * east[0] + ddec * north[0]) * dt_years,
        base[1] + (dra_cosdec * east[1] + ddec * north[1]) * dt_years,
        base[2] + (dra_cosdec * east[2] + ddec * north[2]) * dt_years,
    )
    norm = math.sqrt(sum(component * component for component in propagated))
    if norm == 0.0:
        raise ValueError(f"proper-motion propagation collapsed for {record.canonical_name!r}")
    return tuple(component / norm for component in propagated), True


def deep_sky_at(name: str, jd_tt: float) -> DeepSkyPosition:
    """Project one released coordinate anchor to true ecliptic-of-date at TT."""

    if isinstance(jd_tt, bool) or not math.isfinite(jd_tt):
        raise ValueError("jd_tt must be finite")
    record = deep_sky_object(name)
    if record.object_class is DeepSkyClass.HOST_STAR:
        assert record.star_registry_name is not None
        star = star_at(record.star_registry_name, jd_tt)
        longitude = star.longitude
        latitude = star.latitude
        position_source = "sovereign_star_registry"
        proper_motion_applied = jd_tt != J2000
    else:
        vector, proper_motion_applied = _icrs_unit_vector(record, jd_tt)
        longitude, latitude, _ = icrf_to_true_ecliptic(jd_tt, vector)
        position_source = "simbad_catalog_anchor"
    sign_name, sign_symbol, sign_degree = sign_of(longitude)
    return DeepSkyPosition(
        name=record.canonical_name,
        designation=record.designation,
        object_class=record.object_class,
        longitude=longitude,
        latitude=latitude,
        sign=sign_name,
        sign_symbol=sign_symbol,
        sign_degree=sign_degree,
        jd_tt=float(jd_tt),
        source_ra_deg=record.ra_deg,
        source_dec_deg=record.dec_deg,
        source_frame="ICRS",
        source_epoch_jd_tt=J2000,
        position_semantics=record.position_semantics,
        position_source=position_source,
        proper_motion_applied=proper_motion_applied,
        simbad_main_id=record.simbad_main_id,
        coordinate_bibcode=record.coordinate_bibcode,
        coordinate_quality=record.coordinate_quality,
        catalog_version=record.catalog_version,
    )


def all_deep_sky_at(
    jd_tt: float,
    object_class: DeepSkyClass | str | None = None,
) -> dict[str, DeepSkyPosition]:
    """Return positions for every released anchor in deterministic name order."""

    return {
        name: deep_sky_at(name, jd_tt)
        for name in list_deep_sky_objects(object_class)
    }

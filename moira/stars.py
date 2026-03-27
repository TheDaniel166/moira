"""
Star Catalogue Oracle - moira/stars.py

Archetype: Oracle
Purpose: Unified sovereign star surface backed by the local registry CSV and
         companion JSON metadata files.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .coordinates import icrf_to_true_ecliptic
from .star_types import (
    FixedStarLookupPolicy,
    HeliacalSearchPolicy,
    FixedStarComputationPolicy,
    DEFAULT_FIXED_STAR_POLICY,
    UnifiedStarMergePolicy,
    UnifiedStarComputationPolicy,
    StarPositionTruth,
    StarPositionClassification,
    StarRelation,
    StarConditionState,
    StarConditionProfile,
    StarPosition,
    FixedStarTruth,
    FixedStarClassification,
    UnifiedStarRelation,
    StarChartConditionProfile,
    StarConditionNetworkNode,
    StarConditionNetworkEdge,
    StarConditionNetworkProfile,
    HeliacalEventTruth,
    HeliacalEventClassification,
    HeliacalEvent,
)

__all__ = [
    "StarPositionTruth",
    "StarPositionClassification",
    "StarRelation",
    "StarConditionState",
    "StarConditionProfile",
    "StarChartConditionProfile",
    "StarConditionNetworkNode",
    "StarConditionNetworkEdge",
    "StarConditionNetworkProfile",
    "HeliacalEventTruth",
    "HeliacalEventClassification",
    "HeliacalEvent",
    "FixedStarLookupPolicy",
    "HeliacalSearchPolicy",
    "FixedStarComputationPolicy",
    "DEFAULT_FIXED_STAR_POLICY",
    "StarPosition",
    "star_at",
    "all_stars_at",
    "list_stars",
    "find_stars",
    "star_magnitude",
    "load_catalog",
    "heliacal_rising",
    "heliacal_setting",
    "heliacal_rising_event",
    "heliacal_setting_event",
    "star_chart_condition_profile",
    "star_condition_network_profile",
    "UnifiedStarMergePolicy",
    "UnifiedStarComputationPolicy",
    "FixedStarTruth",
    "FixedStarClassification",
    "UnifiedStarRelation",
    "FixedStar",
    "stars_near",
    "stars_by_magnitude",
    "list_named_stars",
    "find_named_stars",
]

_J2000 = 2451545.0
_AS2DEG = 1.0 / 3600.0
_DATA_DIR = Path(__file__).resolve().parent / "data"
_REGISTRY_PATH = _DATA_DIR / "star_registry.csv"
_LORE_PATH = _DATA_DIR / "star_lore.json"
_PROVENANCE_PATH = _DATA_DIR / "star_provenance.json"


@dataclass(frozen=True, slots=True)
class StellarQuality:
    element: str
    planet: str
    hot: bool
    dry: bool


@dataclass(frozen=True, slots=True)
class _SovereignStarRecord:
    name: str
    nomenclature: str
    gaia_dr3_id: int | None
    ra_deg: float
    dec_deg: float
    pmra_mas_yr: float
    pmdec_mas_yr: float
    parallax_mas: float
    magnitude_v: float
    color_index: float
    ecl_lon_deg: float
    ecl_lat_deg: float
    arc_vis_deg: float
    lat_limit_deg: float
    lore: dict[str, object]
    provenance: dict[str, object]


@dataclass(slots=True)
class FixedStar:
    """Unified sovereign star result."""

    name: str
    nomenclature: str
    longitude: float
    latitude: float
    magnitude: float
    bp_rp: float = math.nan
    teff_k: float = math.nan
    parallax_mas: float = math.nan
    distance_ly: float = math.nan
    quality: StellarQuality | None = None
    source: str = "sovereign"
    is_topocentric: bool = False
    computation_truth: FixedStarTruth | None = None
    classification: FixedStarClassification | None = None
    relation: UnifiedStarRelation | None = None
    condition_profile: StarConditionProfile | None = None

    def __post_init__(self) -> None:
        self.longitude = self.longitude % 360.0

    @property
    def sign(self) -> str:
        from .constants import SIGNS

        return SIGNS[int(self.longitude // 30)]


def _coerce_float(value: str | None, *, default: float = math.nan) -> float:
    if value is None:
        return default
    text = value.strip()
    if not text:
        return default
    return float(text)


def _coerce_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    number = int(text)
    return None if number == 0 else number


@lru_cache(maxsize=1)
def _load_lore() -> dict[str, dict[str, object]]:
    with _LORE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {str(name): payload for name, payload in data.items()}


@lru_cache(maxsize=1)
def _load_provenance() -> dict[str, dict[str, object]]:
    with _PROVENANCE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {str(name): payload for name, payload in data.items()}


@lru_cache(maxsize=1)
def _load_registry_records() -> tuple[_SovereignStarRecord, ...]:
    lore = _load_lore()
    provenance = _load_provenance()
    records: list[_SovereignStarRecord] = []

    with _REGISTRY_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = row["name"].strip()
            if not name:
                continue
            records.append(
                _SovereignStarRecord(
                    name=name,
                    nomenclature=row["nomenclature"].strip(),
                    gaia_dr3_id=_coerce_int(row.get("gaia_dr3_id")),
                    ra_deg=_coerce_float(row.get("ra_deg")),
                    dec_deg=_coerce_float(row.get("dec_deg")),
                    pmra_mas_yr=_coerce_float(row.get("pmra_mas_yr"), default=0.0),
                    pmdec_mas_yr=_coerce_float(row.get("pmdec_mas_yr"), default=0.0),
                    parallax_mas=_coerce_float(row.get("parallax_mas"), default=math.nan),
                    magnitude_v=_coerce_float(row.get("magnitude_v")),
                    color_index=_coerce_float(row.get("color_index")),
                    ecl_lon_deg=_coerce_float(row.get("ecl_lon_deg")),
                    ecl_lat_deg=_coerce_float(row.get("ecl_lat_deg")),
                    arc_vis_deg=_coerce_float(row.get("arc_vis_deg")),
                    lat_limit_deg=_coerce_float(row.get("lat_limit_deg")),
                    lore=lore.get(name, {}),
                    provenance=provenance.get(name, {}),
                )
            )

    return tuple(records)


@lru_cache(maxsize=1)
def _build_indexes() -> tuple[
    dict[str, _SovereignStarRecord],
    dict[str, tuple[_SovereignStarRecord, ...]],
    dict[str, tuple[_SovereignStarRecord, ...]],
    dict[str, tuple[_SovereignStarRecord, ...]],
]:
    by_name_exact: dict[str, _SovereignStarRecord] = {}
    by_name_folded: dict[str, list[_SovereignStarRecord]] = {}
    by_nomenclature_exact: dict[str, list[_SovereignStarRecord]] = {}
    by_nomenclature_folded: dict[str, list[_SovereignStarRecord]] = {}
    for record in _load_registry_records():
        by_name_exact[record.name] = record
        by_name_folded.setdefault(record.name.lower(), []).append(record)
        if record.nomenclature:
            by_nomenclature_exact.setdefault(record.nomenclature, []).append(record)
            by_nomenclature_folded.setdefault(record.nomenclature.lower(), []).append(record)
    return (
        by_name_exact,
        {key: tuple(records) for key, records in by_name_folded.items()},
        {key: tuple(records) for key, records in by_nomenclature_exact.items()},
        {key: tuple(records) for key, records in by_nomenclature_folded.items()},
    )


def _resolve_star_record(
    name: str,
    policy: FixedStarLookupPolicy,
) -> tuple[_SovereignStarRecord, str]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("star name must be a non-empty string")

    query = name.strip()
    key = query.lower()
    by_name_exact, by_name_folded, by_nomenclature_exact, by_nomenclature_folded = _build_indexes()

    record = by_name_exact.get(query)
    if record is not None:
        return record, "traditional_name"

    exact_nomenclature_matches = by_nomenclature_exact.get(query, ())
    if len(exact_nomenclature_matches) == 1:
        return exact_nomenclature_matches[0], "nomenclature"
    if len(exact_nomenclature_matches) > 1:
        return min(exact_nomenclature_matches, key=lambda candidate: (len(candidate.name), candidate.name)), "nomenclature_duplicate"

    folded_name_matches = by_name_folded.get(key, ())
    if len(folded_name_matches) == 1:
        return folded_name_matches[0], "traditional_name_casefold"
    if len(folded_name_matches) > 1:
        raise KeyError(
            f"Star {name!r} is ambiguous under case-insensitive lookup. "
            f"Use the exact catalog casing or nomenclature."
        )

    folded_nomenclature_matches = by_nomenclature_folded.get(key, ())
    if len(folded_nomenclature_matches) == 1:
        return folded_nomenclature_matches[0], "nomenclature_casefold"
    if len(folded_nomenclature_matches) > 1:
        raise KeyError(
            f"Star {name!r} is ambiguous under case-insensitive nomenclature lookup. "
            f"Use the exact catalog casing."
        )

    if policy.allow_prefix_lookup:
        matches = [candidate for candidate in _load_registry_records() if candidate.name.lower().startswith(key)]
        if len(matches) == 1:
            return matches[0], "prefix_unique"
        if matches:
            return min(matches, key=lambda candidate: len(candidate.name)), "prefix_shortest"

    raise KeyError(f"Star {name!r} not in sovereign registry. Use list_stars() to inspect available names.")


def _apply_proper_motion(record: _SovereignStarRecord, jd_tt: float) -> tuple[float, float]:
    dt_years = (jd_tt - _J2000) / 365.25
    dec_rad = math.radians(record.dec_deg)
    cos_dec = math.cos(dec_rad)

    ra_deg = record.ra_deg
    if abs(cos_dec) > 1e-10:
        ra_deg += ((record.pmra_mas_yr / 1000.0) * _AS2DEG / cos_dec) * dt_years

    dec_deg = record.dec_deg + ((record.pmdec_mas_yr / 1000.0) * _AS2DEG) * dt_years
    dec_deg = max(-90.0, min(90.0, dec_deg))
    return ra_deg % 360.0, dec_deg


def _distance_ly_from_parallax(parallax_mas: float) -> float:
    if not math.isfinite(parallax_mas) or parallax_mas <= 0.0:
        return math.nan
    return 3261.56 / parallax_mas


def _native_position(record: _SovereignStarRecord, jd_tt: float) -> tuple[float, float]:
    ra_deg, dec_deg = _apply_proper_motion(record, jd_tt)
    ra_rad = math.radians(ra_deg)
    dec_rad = math.radians(dec_deg)
    xyz = (
        math.cos(dec_rad) * math.cos(ra_rad),
        math.cos(dec_rad) * math.sin(ra_rad),
        math.sin(dec_rad),
    )
    lon, lat, _ = icrf_to_true_ecliptic(jd_tt, xyz)
    return lon, lat


def _build_fixed_star(
    record: _SovereignStarRecord,
    query_name: str,
    lookup_kind: str,
    jd_tt: float,
) -> FixedStar:
    longitude, latitude = _native_position(record, jd_tt)
    return FixedStar(
        name=record.name,
        nomenclature=record.nomenclature,
        longitude=longitude,
        latitude=latitude,
        magnitude=record.magnitude_v,
        bp_rp=record.color_index,
        parallax_mas=record.parallax_mas,
        distance_ly=_distance_ly_from_parallax(record.parallax_mas),
        source="sovereign",
        is_topocentric=False,
        computation_truth=FixedStarTruth(
            lookup_kind=lookup_kind,
            hipparcos_name=record.name,
            source_mode="sovereign_registry",
            gaia_match_status="native_registry",
            gaia_source_index=None,
            is_topocentric=False,
            true_position=True,
            dedup_applied=False,
        ),
        classification=FixedStarClassification(
            lookup_kind=lookup_kind,
            source_kind="sovereign",
            merge_state="native_registry",
            observer_mode="geocentric",
        ),
        relation=UnifiedStarRelation(
            kind="catalog_merge",
            basis="sovereign_registry",
            star_name=query_name,
            source_kind="sovereign",
            gaia_source_index=None,
        ),
    )


def load_catalog() -> None:
    _load_registry_records()
    _build_indexes()


def star_at(
    name: str,
    jd_tt: float,
    policy: UnifiedStarComputationPolicy | FixedStarComputationPolicy | None = None,
    **_: object,
) -> FixedStar:
    if not math.isfinite(jd_tt):
        raise ValueError("jd_tt must be finite")

    lookup_policy = policy.lookup if policy is not None else DEFAULT_FIXED_STAR_POLICY.lookup
    record, lookup_kind = _resolve_star_record(name, lookup_policy)
    return _build_fixed_star(record, name, lookup_kind, jd_tt)


def all_stars_at(jd_tt: float) -> dict[str, FixedStar]:
    return {record.name: _build_fixed_star(record, record.name, "traditional_name", jd_tt) for record in _load_registry_records()}


def list_named_stars() -> list[str]:
    return sorted(record.name for record in _load_registry_records())


list_stars = list_named_stars


def find_named_stars(fragment: str, **_: object) -> list[str]:
    needle = fragment.strip().lower()
    return sorted(
        record.name
        for record in _load_registry_records()
        if needle in record.name.lower() or needle in record.nomenclature.lower()
    )


find_stars = find_named_stars


def star_magnitude(name: str) -> float:
    record, _ = _resolve_star_record(name, DEFAULT_FIXED_STAR_POLICY.lookup)
    return record.magnitude_v


def _longitude_delta(a: float, b: float) -> float:
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def stars_near(longitude_deg: float, jd_tt: float, orb: float = 1.0, **_: object) -> list[FixedStar]:
    matches: list[FixedStar] = []
    for record in _load_registry_records():
        star = _build_fixed_star(record, record.name, "traditional_name", jd_tt)
        if _longitude_delta(star.longitude, longitude_deg) <= orb:
            matches.append(star)
    matches.sort(key=lambda star: (_longitude_delta(star.longitude, longitude_deg), star.magnitude, star.name))
    return matches


def stars_by_magnitude(max_magnitude: float, jd_tt: float, **_: object) -> list[FixedStar]:
    matches = [
        _build_fixed_star(record, record.name, "traditional_name", jd_tt)
        for record in _load_registry_records()
        if record.magnitude_v <= max_magnitude
    ]
    matches.sort(key=lambda star: (star.magnitude, star.name))
    return matches


heliacal_rising = lambda *a, **k: None
heliacal_setting = lambda *a, **k: None
heliacal_rising_event = lambda *a, **k: None
heliacal_setting_event = lambda *a, **k: None
star_chart_condition_profile = lambda *a, **k: None
star_condition_network_profile = lambda *a, **k: None

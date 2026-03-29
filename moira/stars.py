"""
Star Catalogue Oracle - moira/stars.py

Archetype: Oracle
Purpose: Unified sovereign star surface backed by the local registry CSV and
         companion JSON metadata files.
"""

from __future__ import annotations

import csv
import importlib
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
    "star_name_resolves",
]

_J2000 = 2451545.0
_MAS2RAD = math.radians(1.0 / (1000.0 * 3600.0))
_DATA_DIR = Path(__file__).resolve().parent / "data"
_REGISTRY_PATH = _DATA_DIR / "star_registry.csv"
_LORE_PATH = _DATA_DIR / "star_lore.json"
_PROVENANCE_PATH = _DATA_DIR / "star_provenance.json"
_HISTORICAL_STAR_ALIASES = {
    "Adhab": "Titawin",
    "Hydria": "eta Aqr",
    "Ekkhysis": "Shatabhisha",
    "Albulaan": "nu. Aqr",
    "Delta Aquilae": "del Aql",
    "Deneb el Okab Borealis": "eps Aql",
    "Deneb el Okab Australis": "Okab",
    "Bazak": "eta Aql",
    "Tseen Foo": "Antinous",
    "Al Thalimaim Posterior": "iot Aql",
    "Al Thalimaim Anterior": "lam Aql",
    "Bered": "i Aql",
    "Princeps": "del Boo",
    "Asellus Primus": "tet Boo",
    "Asellus Secundus": "iot Boo",
    "Asellus Tertius": "kap02 Boo",
    "Hemelein Prima": "rho Boo",
    "Hemelein Secunda": "sig Boo",
    "Decapoda": "Yuyu",
    "Castra": "eps Cap",
    "Marakk": "zet Cap",
    "Baten Algiedi": "ome Cap",
    "Vathorz Posterior": "tet Car",
    "Vathorz Prior": "ups Car",
    "Tsih": "Tiansi",
    "Marfak": "tet Cas",
    "Muhlifain": "gam Cen",
    "Birdun": "eps Cen",
    "Alhakim": "Kulou",
    "Ke Kwan": "kap Cen",
    "Ma Ti": "lam Cen",
    "Kabkent Secunda": "Heng",
    "Kabkent Tertia": "phi Cen",
    "Minkar": "eps Crv",
    "Avis Satyra": "eta Crv",
    "Alsharasif": "bet Crt",
    "Labrum": "del Crt",
    "Decrux": "Imai",
    "Juxta Crucem": "Ginan",
    "Alwaid": "Rastaban",
    "Nodus II": "Altais",
    "Tyl": "eps Dra",
    "Nodus I": "Aldhibah",
    "Ketu": "kap Dra",
    "Giansar": "Giausar",
    "Arrakis": "Alrakis",
    "Kuma": "nu.01 Dra",
    "Batentaban Borealis": "chi Dra",
    "Aldhibain": "Athebyne",
    "Batentaban Australis": "phi Dra",
    "Rutilicus": "zet Her",
    "Sofian": "eta Her",
    "Rukbalgethi Genubi": "tet Her",
    "Al Jathiyah": "iot Her",
    "Melkarth": "mu.01 Her",
    "Fudail": "pi. Her",
    "Rukbalgethi Shemali": "tau Her",
    "Cauda Hydrae": "Naga",
    "Mautinah": "del Hya",
    "Hydrobius": "zet Hya",
    "Pleura": "nu. Hya",
    "Sataghni": "pi. Hya",
    "Al Minliar al Shuja": "Minchir",
    "Ras Elased Australis": "eps Leo",
    "Al Jabhah": "eta Leo",
    "Tse Tseng": "iot Leo",
    "Alminhar": "kap Leo",
    "Ras Elased Borealis": "Rasalas",
    "Coxa": "Chertan",
    "Shir": "Shaomin",
    "Vishakha": "iot Lib",
    "Al Durajah": "Bake-eo",
    "Ensis": "eta Ori",
    "Simmah": "gam Psc",
    "Linteum": "del Psc",
    "Kaht": "eps Psc",
    "Torcularis Septentrionalis": "Torcular",
    "Sephdar": "eta Sgr",
    "Manubrium": "omi Sgr",
    "Hecatebolus": "tau Sgr",
    "Nanto": "phi Sgr",
    "Graffias": "Acrab",
    "Wei": "Larawag",
    "Girtab": "kap Sco",
    "Al Hecka": "Tianguan",
    "Phaeo": "tet01 Tau",
    "Phaesula": "Chamukuy",
    "Althaur": "lam Tau",
    "Furibundus": "nu. Tau",
    "Ushakaron": "ksi Tau",
    "Atirsagne": "omi Tau",
    "Sterope I": "Asterope",
    "Sterope II": "Asterope",
    "Mizar": "zet01 UMa",
    "Al Haud": "tet UMa",
    "Talitha Australis": "Alkaphrah",
    "El Kophrah": "Taiyangshou",
    "Urodelus": "eps UMi",
    "Alifa Al Farkadain": "zet UMi",
    "Auva": "Minelauva",
    "Rijl al Awwa": "mu. Vir",
}


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
    constellation: str | None
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


@lru_cache(maxsize=1)
def _build_alias_indexes() -> tuple[
    dict[str, str],
    dict[str, tuple[str, ...]],
]:
    by_alias_exact = dict(_HISTORICAL_STAR_ALIASES)
    by_alias_folded: dict[str, list[str]] = {}
    for alias in _HISTORICAL_STAR_ALIASES:
        by_alias_folded.setdefault(alias.lower(), []).append(alias)
    return by_alias_exact, {key: tuple(values) for key, values in by_alias_folded.items()}


def _resolve_catalog_star_record(
    query: str,
    key: str,
    policy: FixedStarLookupPolicy,
) -> tuple[_SovereignStarRecord, str]:
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
            f"Star {query!r} is ambiguous under case-insensitive lookup. "
            f"Use the exact catalog casing or nomenclature."
        )

    folded_nomenclature_matches = by_nomenclature_folded.get(key, ())
    if len(folded_nomenclature_matches) == 1:
        return folded_nomenclature_matches[0], "nomenclature_casefold"
    if len(folded_nomenclature_matches) > 1:
        raise KeyError(
            f"Star {query!r} is ambiguous under case-insensitive nomenclature lookup. "
            f"Use the exact catalog casing."
        )

    if policy.allow_prefix_lookup:
        matches = [candidate for candidate in _load_registry_records() if candidate.name.lower().startswith(key)]
        if len(matches) == 1:
            return matches[0], "prefix_unique"
        if matches:
            return min(matches, key=lambda candidate: len(candidate.name)), "prefix_shortest"

    raise KeyError(f"Star {query!r} not in sovereign registry. Use list_stars() to inspect available names.")


def _resolve_star_record(
    name: str,
    policy: FixedStarLookupPolicy,
) -> tuple[_SovereignStarRecord, str]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("star name must be a non-empty string")

    query = name.strip()
    key = query.lower()
    try:
        return _resolve_catalog_star_record(query, key, policy)
    except KeyError as missing:
        by_alias_exact, by_alias_folded = _build_alias_indexes()
        alias_target = by_alias_exact.get(query)
        if alias_target is not None:
            record, _ = _resolve_catalog_star_record(alias_target, alias_target.lower(), policy)
            return record, "historical_alias"

        folded_alias_matches = by_alias_folded.get(key, ())
        if len(folded_alias_matches) == 1:
            alias_target = by_alias_exact[folded_alias_matches[0]]
            record, _ = _resolve_catalog_star_record(alias_target, alias_target.lower(), policy)
            return record, "historical_alias_casefold"
        if len(folded_alias_matches) > 1:
            raise KeyError(
                f"Star {name!r} is ambiguous under case-insensitive historical alias lookup. "
                f"Use the exact alias casing."
            )
        raise missing


def _icrs_unit_vector(ra_deg: float, dec_deg: float) -> tuple[float, float, float]:
    ra_rad = math.radians(ra_deg)
    dec_rad = math.radians(dec_deg)
    cos_dec = math.cos(dec_rad)
    return (
        cos_dec * math.cos(ra_rad),
        cos_dec * math.sin(ra_rad),
        math.sin(dec_rad),
    )


def _propagate_icrs_vector(record: _SovereignStarRecord, jd_tt: float) -> tuple[float, float, float]:
    dt_years = (jd_tt - _J2000) / 365.25
    if dt_years == 0.0:
        return _icrs_unit_vector(record.ra_deg, record.dec_deg)

    ra_rad = math.radians(record.ra_deg)
    dec_rad = math.radians(record.dec_deg)
    cos_dec = math.cos(dec_rad)
    sin_dec = math.sin(dec_rad)
    cos_ra = math.cos(ra_rad)
    sin_ra = math.sin(ra_rad)

    # Gaia/HIP-style pmRA is mu_alpha* = d(alpha)/dt * cos(delta).
    dra_dt = 0.0
    if abs(cos_dec) > 1e-12:
        dra_dt = record.pmra_mas_yr * _MAS2RAD / cos_dec
    ddec_dt = record.pmdec_mas_yr * _MAS2RAD

    p_hat = (
        cos_dec * cos_ra,
        cos_dec * sin_ra,
        sin_dec,
    )
    east_hat = (-sin_ra, cos_ra, 0.0)
    north_hat = (-sin_dec * cos_ra, -sin_dec * sin_ra, cos_dec)

    tangential_velocity = (
        dra_dt * cos_dec * east_hat[0] + ddec_dt * north_hat[0],
        dra_dt * cos_dec * east_hat[1] + ddec_dt * north_hat[1],
        dra_dt * cos_dec * east_hat[2] + ddec_dt * north_hat[2],
    )

    if math.isfinite(record.parallax_mas) and record.parallax_mas > 0.0:
        distance_pc = 1000.0 / record.parallax_mas
        propagated = (
            distance_pc * p_hat[0] + tangential_velocity[0] * distance_pc * dt_years,
            distance_pc * p_hat[1] + tangential_velocity[1] * distance_pc * dt_years,
            distance_pc * p_hat[2] + tangential_velocity[2] * distance_pc * dt_years,
        )
    else:
        propagated = (
            p_hat[0] + tangential_velocity[0] * dt_years,
            p_hat[1] + tangential_velocity[1] * dt_years,
            p_hat[2] + tangential_velocity[2] * dt_years,
        )

    norm = math.sqrt(
        propagated[0] * propagated[0]
        + propagated[1] * propagated[1]
        + propagated[2] * propagated[2]
    )
    if norm == 0.0:
        return p_hat
    return (
        propagated[0] / norm,
        propagated[1] / norm,
        propagated[2] / norm,
    )


def _distance_ly_from_parallax(parallax_mas: float) -> float:
    if not math.isfinite(parallax_mas) or parallax_mas <= 0.0:
        return math.nan
    return 3261.56 / parallax_mas


def _native_position(record: _SovereignStarRecord, jd_tt: float) -> tuple[float, float]:
    xyz = _propagate_icrs_vector(record, jd_tt)
    lon, lat, _ = icrf_to_true_ecliptic(jd_tt, xyz)
    return lon, lat


def _build_fixed_star(
    record: _SovereignStarRecord,
    query_name: str,
    lookup_kind: str,
    jd_tt: float,
) -> FixedStar:
    longitude, latitude = _native_position(record, jd_tt)
    constellation = _constellation_for_star(record.name)
    return FixedStar(
        name=record.name,
        nomenclature=record.nomenclature,
        constellation=constellation,
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
            constellation=constellation,
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


def _constellation_label_from_module_stem(stem: str) -> str:
    return stem.removeprefix("stars_").replace("_", " ").title()


@lru_cache(maxsize=1)
def _constellation_index() -> dict[str, str]:
    package_dir = Path(__file__).resolve().parent / "constellations"
    memberships: dict[str, set[str]] = {}
    for module_path in sorted(package_dir.glob("stars_*.py")):
        module = importlib.import_module(f"{__package__}.constellations.{module_path.stem}")
        constellation = _constellation_label_from_module_stem(module_path.stem)
        for attr_name, star_map in module.__dict__.items():
            if not attr_name.endswith("_STAR_NAMES") or not isinstance(star_map, dict):
                continue
            for advertised_name in star_map.values():
                if not isinstance(advertised_name, str):
                    continue
                try:
                    record, _ = _resolve_star_record(advertised_name, DEFAULT_FIXED_STAR_POLICY.lookup)
                except (KeyError, ValueError):
                    continue
                memberships.setdefault(record.name, set()).add(constellation)

    return {
        star_name: sorted(constellations)[0]
        for star_name, constellations in memberships.items()
        if constellations
    }


def _constellation_for_star(name: str) -> str | None:
    return _constellation_index().get(name)


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


def star_name_resolves(name: str) -> bool:
    try:
        _resolve_star_record(name, DEFAULT_FIXED_STAR_POLICY.lookup)
    except (KeyError, ValueError):
        return False
    return True


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

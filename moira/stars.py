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
    HeliacalBatchResult,
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
    "HeliacalBatchResult",
    "FixedStarLookupPolicy",
    "HeliacalSearchPolicy",
    "FixedStarComputationPolicy",
    "DEFAULT_FIXED_STAR_POLICY",
    "StarPosition",
    "star_at",
    "star_light_time_split",
    "all_stars_at",
    "list_stars",
    "find_stars",
    "star_magnitude",
    "load_catalog",
    "heliacal_rising",
    "heliacal_setting",
    "heliacal_rising_event",
    "heliacal_setting_event",
    "heliacal_catalog_batch",
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


_DAYS_PER_YEAR = 365.25


def _emission_jd(record: _SovereignStarRecord, jd_tt: float) -> float:
    """Return the JD at which the light we receive at jd_tt was emitted by this star.

    For a star at distance d light-years, the light travel time is d years.
    The emission epoch is therefore jd_tt - d * 365.25 days.

    Returns jd_tt unchanged when parallax is absent or non-positive (star treated
    as at infinite distance; the light-time distinction is undefined).
    """
    dist_ly = _distance_ly_from_parallax(record.parallax_mas)
    if not math.isfinite(dist_ly):
        return jd_tt
    return jd_tt - dist_ly * _DAYS_PER_YEAR


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
    classification = FixedStarClassification(
        lookup_kind=lookup_kind,
        source_kind="sovereign",
        merge_state="native_registry",
        observer_mode="geocentric",
    )
    relation = UnifiedStarRelation(
        kind="catalog_merge",
        basis="sovereign_registry",
        star_name=query_name,
        source_kind="sovereign",
        gaia_source_index=None,
    )
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
        classification=classification,
        relation=relation,
        condition_profile=StarConditionProfile(
            result_kind="fixed_star",
            condition_state=StarConditionState("unified_merge"),
            relation_kind=relation.kind,
            relation_basis=relation.basis,
            source_kind=classification.source_kind,
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


def star_light_time_split(
    name: str,
    jd_tt: float,
) -> tuple[FixedStar, FixedStar]:
    """Return (observed_position, true_position) for a fixed star.

    observed_position — where the star appears to be: its position at the epoch
        when the light we are currently receiving was emitted, i.e. at
        ``jd_tt - distance_ly * 365.25``.  This is what a telescope shows.

    true_position — where the star physically is at ``jd_tt``, accounting for
        proper motion from J2000 to now.  The light carrying this information
        has not yet reached Earth.

    The longitude difference between the two positions is the proper-motion
    drift accumulated over the light travel time.  For Arcturus (37 ly) this
    is approximately 37 years of proper motion; for Sirius (8.6 ly) about
    8.6 years.

    For stars without a valid parallax measurement the light-travel-time is
    undefined (star treated as at infinite distance); both returned positions
    are identical and carry ``true_position=True``.

    Parameters
    ----------
    name   : star name as accepted by ``star_at``
    jd_tt  : Julian Date in TT

    Returns
    -------
    (observed, true) — a pair of FixedStar vessels.
    ``observed.computation_truth.true_position`` is False.
    ``true.computation_truth.true_position`` is True.
    """
    if not math.isfinite(jd_tt):
        raise ValueError("jd_tt must be finite")

    record, lookup_kind = _resolve_star_record(name, DEFAULT_FIXED_STAR_POLICY.lookup)
    constellation = _constellation_for_star(record.name)
    dist_ly = _distance_ly_from_parallax(record.parallax_mas)

    # True position: propagate to jd_tt
    true = _build_fixed_star(record, name, lookup_kind, jd_tt)

    # Observed position: propagate to emission epoch
    obs_jd = _emission_jd(record, jd_tt)
    obs_lon, obs_lat = _native_position(record, obs_jd)
    classification = FixedStarClassification(
        lookup_kind=lookup_kind,
        source_kind="sovereign",
        merge_state="native_registry",
        observer_mode="geocentric",
    )
    relation = UnifiedStarRelation(
        kind="catalog_merge",
        basis="sovereign_registry",
        star_name=name,
        source_kind="sovereign",
        gaia_source_index=None,
    )
    observed = FixedStar(
        name=record.name,
        nomenclature=record.nomenclature,
        constellation=constellation,
        longitude=obs_lon,
        latitude=obs_lat,
        magnitude=record.magnitude_v,
        bp_rp=record.color_index,
        parallax_mas=record.parallax_mas,
        distance_ly=dist_ly,
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
            true_position=False,
            dedup_applied=False,
        ),
        classification=classification,
        relation=relation,
        condition_profile=StarConditionProfile(
            result_kind="fixed_star",
            condition_state=StarConditionState("unified_merge"),
            relation_kind=relation.kind,
            relation_basis=relation.basis,
            source_kind=classification.source_kind,
        ),
    )

    return observed, true


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


def _heliacal_signed_elongation(name: str, jd_ut: float) -> float:
    """Signed ecliptic elongation of a fixed star from the Sun in degrees."""
    from .constants import Body
    from .julian import ut_to_tt
    from .planets import planet_at

    jd_tt = ut_to_tt(jd_ut)
    star = star_at(name, jd_tt)
    sun = planet_at(Body.SUN, jd_tt)
    return ((star.longitude - sun.longitude + 180.0) % 360.0) - 180.0


def _star_altitude(
    name: str,
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
) -> float:
    from .rise_set import _altitude

    return _altitude(
        jd_ut,
        latitude,
        longitude,
        name,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
    )


def _default_arcus_for_star(name: str) -> float:
    from .heliacal import VisibilityModel, _arcus_visionis

    return _arcus_visionis(star_magnitude(name), VisibilityModel())


def _build_heliacal_event(
    event_kind: str,
    name: str,
    jd_start: float,
    search_days: int,
    arcus_visionis: float,
    elongation_threshold: float,
    qualifying_day_offset: int | None,
    qualifying_elongation: float | None,
    qualifying_sun_altitude: float | None,
    event_jd_ut: float | None,
) -> HeliacalEvent:
    is_found = event_jd_ut is not None
    visibility_state = "found" if is_found else "not_found"
    relation = StarRelation(
        kind="heliacal_event",
        basis="arcus_visionis_threshold",
        star_name=name,
        event_kind=event_kind,
    )
    condition_profile = StarConditionProfile(
        result_kind="heliacal_event",
        condition_state=StarConditionState(visibility_state),
        relation_kind=relation.kind,
        relation_basis=relation.basis,
        event_kind=event_kind,
    )
    return HeliacalEvent(
        event_kind=event_kind,
        star_name=name,
        jd_ut=event_jd_ut,
        is_found=is_found,
        computation_truth=HeliacalEventTruth(
            event_kind=event_kind,
            star_name=name,
            jd_start=jd_start,
            search_days=search_days,
            arcus_visionis=arcus_visionis,
            elongation_threshold=elongation_threshold,
            conjunction_offset=None,
            qualifying_day_offset=qualifying_day_offset,
            qualifying_elongation=qualifying_elongation,
            qualifying_sun_altitude=qualifying_sun_altitude,
            event_jd_ut=event_jd_ut,
        ),
        classification=HeliacalEventClassification(
            event_kind=event_kind,
            search_kind="forward_visibility_scan",
            visibility_state=visibility_state,
        ),
        relation=relation,
        condition_profile=condition_profile,
    )


def heliacal_rising(
    name: str,
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    arcus_visionis: float | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> float | None:
    return heliacal_rising_event(
        name,
        jd_ut,
        latitude,
        longitude,
        arcus_visionis=arcus_visionis,
        search_days=search_days,
        policy=policy,
    ).jd_ut


def heliacal_setting(
    name: str,
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    arcus_visionis: float | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> float | None:
    return heliacal_setting_event(
        name,
        jd_ut,
        latitude,
        longitude,
        arcus_visionis=arcus_visionis,
        search_days=search_days,
        policy=policy,
    ).jd_ut


def heliacal_rising_event(
    name: str,
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    arcus_visionis: float | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> HeliacalEvent:
    from .heliacal import _find_sun_at_alt

    resolved_policy = DEFAULT_FIXED_STAR_POLICY if policy is None else policy
    if not isinstance(resolved_policy, FixedStarComputationPolicy):
        raise ValueError("policy must be a FixedStarComputationPolicy")
    if not math.isfinite(jd_ut):
        raise ValueError("jd_ut must be finite")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be in [-90, 90]")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be in [-180, 180]")
    if not isinstance(search_days, int) or search_days <= 0:
        raise ValueError("search_days must be a positive integer")

    star_name_resolves(name) or _resolve_star_record(name, DEFAULT_FIXED_STAR_POLICY.lookup)
    resolved_arcus = _default_arcus_for_star(name) if arcus_visionis is None else arcus_visionis
    if not math.isfinite(resolved_arcus) or resolved_arcus <= 0.0:
        raise ValueError("arcus_visionis must be a positive finite value")

    jd_mid0 = math.floor(jd_ut + 0.5) - 0.5
    elongation_threshold = resolved_policy.heliacal.elongation_threshold

    for day_offset in range(search_days):
        jd_midnight = jd_mid0 + day_offset
        se = _heliacal_signed_elongation(name, jd_midnight + 0.5)
        if se >= 0.0 or abs(se) < elongation_threshold:
            continue
        twilight_jd = _find_sun_at_alt(jd_midnight, latitude, longitude, -resolved_arcus, True)
        if twilight_jd is None:
            continue
        star_alt = _star_altitude(name, twilight_jd, latitude, longitude)
        if star_alt <= 0.0:
            continue
        return _build_heliacal_event(
            "heliacal_rising",
            name,
            jd_ut,
            search_days,
            resolved_arcus,
            elongation_threshold,
            day_offset,
            se,
            -resolved_arcus,
            twilight_jd,
        )

    return _build_heliacal_event(
        "heliacal_rising",
        name,
        jd_ut,
        search_days,
        resolved_arcus,
        elongation_threshold,
        None,
        None,
        None,
        None,
    )


def heliacal_setting_event(
    name: str,
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    arcus_visionis: float | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> HeliacalEvent:
    from .heliacal import _find_sun_at_alt

    resolved_policy = DEFAULT_FIXED_STAR_POLICY if policy is None else policy
    if not isinstance(resolved_policy, FixedStarComputationPolicy):
        raise ValueError("policy must be a FixedStarComputationPolicy")
    if not math.isfinite(jd_ut):
        raise ValueError("jd_ut must be finite")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be in [-90, 90]")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be in [-180, 180]")
    if not isinstance(search_days, int) or search_days <= 0:
        raise ValueError("search_days must be a positive integer")

    star_name_resolves(name) or _resolve_star_record(name, DEFAULT_FIXED_STAR_POLICY.lookup)
    resolved_arcus = _default_arcus_for_star(name) if arcus_visionis is None else arcus_visionis
    if not math.isfinite(resolved_arcus) or resolved_arcus <= 0.0:
        raise ValueError("arcus_visionis must be a positive finite value")

    jd_mid0 = math.floor(jd_ut + 0.5) - 0.5
    elongation_threshold = resolved_policy.heliacal.elongation_threshold
    disappearance_threshold = elongation_threshold * resolved_policy.heliacal.setting_visibility_factor
    last_visible: tuple[int, float, float] | None = None

    for day_offset in range(search_days):
        jd_midnight = jd_mid0 + day_offset
        se = _heliacal_signed_elongation(name, jd_midnight + 0.5)
        abs_se = abs(se)

        if se < 0.0 and abs_se >= elongation_threshold:
            twilight_jd = _find_sun_at_alt(jd_midnight, latitude, longitude, -resolved_arcus, True)
            if twilight_jd is None:
                continue
            star_alt = _star_altitude(name, twilight_jd, latitude, longitude)
            if star_alt > 0.0:
                last_visible = (day_offset, se, twilight_jd)
        elif last_visible is not None and abs_se < disappearance_threshold:
            last_day_offset, last_elongation, last_jd = last_visible
            return _build_heliacal_event(
                "heliacal_setting",
                name,
                jd_ut,
                search_days,
                resolved_arcus,
                elongation_threshold,
                last_day_offset,
                last_elongation,
                -resolved_arcus,
                last_jd,
            )

    return _build_heliacal_event(
        "heliacal_setting",
        name,
        jd_ut,
        search_days,
        resolved_arcus,
        elongation_threshold,
        last_visible[0] if last_visible is not None else None,
        last_visible[1] if last_visible is not None else None,
        -resolved_arcus if last_visible is not None else None,
        last_visible[2] if last_visible is not None else None,
    )


# ---------------------------------------------------------------------------
# Catalog-wide heliacal batch search
# ---------------------------------------------------------------------------

_HELIACAL_BATCH_EVENT_KINDS: frozenset[str] = frozenset({"heliacal_rising", "heliacal_setting"})


def heliacal_catalog_batch(
    event_kind: str,
    jd_start: float,
    latitude: float,
    longitude: float,
    *,
    max_magnitude: float = 6.5,
    names: list[str] | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> HeliacalBatchResult:
    """
    Run a heliacal rising or setting search across the sovereign star catalog.

    Two pre-filters are applied before any ephemeris computation, using
    data already stored in the registry:

    1. **Magnitude filter** — stars whose V magnitude exceeds ``max_magnitude``
       are placed in ``result.skipped_magnitude`` without touching the
       ephemeris.  Default 6.5 (naked-eye limit).

    2. **Latitude-limit filter** — each registry record carries a
       ``lat_limit_deg`` value equal to ``90° − |dec|``.  If
       ``abs(latitude) > lat_limit_deg``, the star is either circumpolar
       (high-declination northern star seen from a high northern latitude)
       or permanently below the horizon (southern star at a high northern
       latitude).  Either way heliacal events are geometrically impossible,
       so the star is placed in ``result.skipped_latitude``.

    Stars that pass both filters are searched with ``heliacal_rising_event``
    or ``heliacal_setting_event``, using the ``arc_vis_deg`` stored in the
    registry record as the arcus visionis threshold (falling back to the
    Ptolemaic-table derivation only when the registry value is absent or
    non-positive).

    The ``found`` list in the result is sorted ascending by ``jd_ut``.

    Parameters
    ----------
    event_kind : ``"heliacal_rising"`` or ``"heliacal_setting"``.
    jd_start : Julian Day (UT1) to begin the forward search.
    latitude, longitude : Observer geodetic coordinates (degrees).
    max_magnitude : Faintest V magnitude to include. Default 6.5.
    names : If given, restrict the search to this explicit subset of
        sovereign registry names.  Names absent from the registry raise
        ``ValueError``.
    search_days : Forward search window per star (days). Default 400.
    policy : Fixed-star computation policy. Defaults to
        ``DEFAULT_FIXED_STAR_POLICY``.
    """
    if event_kind not in _HELIACAL_BATCH_EVENT_KINDS:
        raise ValueError(
            f"event_kind must be 'heliacal_rising' or 'heliacal_setting', got {event_kind!r}"
        )
    if not math.isfinite(jd_start):
        raise ValueError("jd_start must be finite")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude must be in [-90, 90], got {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude must be in [-180, 180], got {longitude}")
    if not math.isfinite(max_magnitude):
        raise ValueError("max_magnitude must be finite")
    if not isinstance(search_days, int) or search_days <= 0:
        raise ValueError("search_days must be a positive integer")

    resolved_policy = DEFAULT_FIXED_STAR_POLICY if policy is None else policy

    all_records = _load_registry_records()
    if names is not None:
        by_name = {r.name: r for r in all_records}
        unknown = set(names) - by_name.keys()
        if unknown:
            raise ValueError(f"Unknown star names: {sorted(unknown)}")
        records: tuple[_SovereignStarRecord, ...] = tuple(by_name[n] for n in names if n in by_name)
    else:
        records = all_records

    abs_lat = abs(latitude)
    search_fn = heliacal_rising_event if event_kind == "heliacal_rising" else heliacal_setting_event

    found: list[HeliacalEvent] = []
    not_found: list[str] = []
    skipped_latitude: list[str] = []
    skipped_magnitude: list[str] = []

    for record in records:
        # Pre-filter 1: magnitude
        if record.magnitude_v > max_magnitude:
            skipped_magnitude.append(record.name)
            continue
        # Pre-filter 2: latitude limit — circumpolar or never-visible
        if math.isfinite(record.lat_limit_deg) and abs_lat > record.lat_limit_deg:
            skipped_latitude.append(record.name)
            continue
        # Use the catalog's per-star arcus visionis where available
        arcus: float | None = (
            record.arc_vis_deg
            if math.isfinite(record.arc_vis_deg) and record.arc_vis_deg > 0.0
            else None
        )
        event = search_fn(
            record.name,
            jd_start,
            latitude,
            longitude,
            arcus_visionis=arcus,
            search_days=search_days,
            policy=resolved_policy,
        )
        if event.is_found:
            found.append(event)
        else:
            not_found.append(record.name)

    found.sort(key=lambda e: e.jd_ut if e.jd_ut is not None else math.inf)

    return HeliacalBatchResult(
        event_kind=event_kind,
        jd_start=jd_start,
        latitude=latitude,
        longitude=longitude,
        max_magnitude=max_magnitude,
        search_days=search_days,
        found=tuple(found),
        not_found=tuple(not_found),
        skipped_latitude=tuple(skipped_latitude),
        skipped_magnitude=tuple(skipped_magnitude),
    )


def _derive_star_position_condition_profile(position: StarPosition) -> StarConditionProfile | None:
    if position.condition_profile is not None:
        return position.condition_profile
    if position.relation is None:
        return None
    lookup_kind = None if position.classification is None else position.classification.lookup_kind
    return StarConditionProfile(
        result_kind="catalog_position",
        condition_state=StarConditionState("catalog_position"),
        relation_kind=position.relation.kind,
        relation_basis=position.relation.basis,
        lookup_kind=lookup_kind,
        source_kind="catalog",
    )


def _derive_heliacal_condition_profile(event: HeliacalEvent) -> StarConditionProfile | None:
    if event.condition_profile is not None:
        return event.condition_profile
    if event.relation is None:
        return None
    return StarConditionProfile(
        result_kind="heliacal_event",
        condition_state=StarConditionState("found" if event.is_found else "not_found"),
        relation_kind=event.relation.kind,
        relation_basis=event.relation.basis,
        event_kind=event.event_kind,
    )


def _derive_fixed_star_condition_profile(star: FixedStar) -> StarConditionProfile | None:
    if star.condition_profile is not None:
        return star.condition_profile
    if star.relation is None:
        return None
    source_kind = None
    if star.classification is not None:
        source_kind = star.classification.source_kind
    elif star.relation.source_kind:
        source_kind = star.relation.source_kind
    else:
        source_kind = star.source
    return StarConditionProfile(
        result_kind="fixed_star",
        condition_state=StarConditionState("unified_merge"),
        relation_kind=star.relation.kind,
        relation_basis=star.relation.basis,
        source_kind=source_kind,
    )


def _star_condition_strength(profile: StarConditionProfile) -> int:
    if profile.result_kind == "heliacal_event":
        return 3 if profile.condition_state.name == "found" else 1
    if profile.condition_state.name == "unified_merge":
        return 2
    return 0


def _star_condition_sort_key(profile: StarConditionProfile) -> tuple[object, ...]:
    return (
        profile.condition_state.name,
        profile.result_kind,
        profile.relation_kind,
        profile.relation_basis,
        profile.lookup_kind or "",
        profile.source_kind or "",
        profile.event_kind or "",
    )


def _star_network_node_sort_key(node: StarConditionNetworkNode) -> tuple[str, str]:
    return (node.kind, node.node_id)


def _star_network_edge_sort_key(edge: StarConditionNetworkEdge) -> tuple[str, str, str, str, str]:
    return (
        edge.source_id,
        edge.target_id,
        edge.relation_kind,
        edge.relation_basis,
        edge.condition_state,
    )


def _catalog_position_source_node_id(position: StarPosition) -> str:
    relation = position.relation
    assert relation is not None
    reference = relation.reference or position.name
    return f"source:catalog_lookup:{relation.basis}:{reference}"


def _heliacal_event_node_id(event: HeliacalEvent) -> str:
    anchor_jd = event.jd_ut
    if anchor_jd is None and event.computation_truth is not None:
        anchor_jd = event.computation_truth.jd_start
    if anchor_jd is None or not math.isfinite(anchor_jd):
        suffix = "unknown"
    else:
        suffix = f"{anchor_jd:.6f}"
    return f"event:{event.event_kind}:{event.star_name}:{suffix}"


def _fixed_star_source_node_id(star: FixedStar) -> str:
    relation = star.relation
    assert relation is not None
    return f"source:catalog_merge:{relation.basis}:{relation.source_kind}:{star.name}"


def star_chart_condition_profile(
    *,
    catalog_positions: list[StarPosition] | None = None,
    heliacal_events: list[HeliacalEvent] | None = None,
    fixed_stars: list[FixedStar] | None = None,
) -> StarChartConditionProfile:
    """Aggregate current star condition profiles into one chart-wide vessel."""

    profiles: list[StarConditionProfile] = []
    if catalog_positions is not None:
        profiles.extend(
            profile
            for position in catalog_positions
            if (profile := _derive_star_position_condition_profile(position)) is not None
        )
    if heliacal_events is not None:
        profiles.extend(
            profile
            for event in heliacal_events
            if (profile := _derive_heliacal_condition_profile(event)) is not None
        )
    if fixed_stars is not None:
        profiles.extend(
            profile
            for star in fixed_stars
            if (profile := _derive_fixed_star_condition_profile(star)) is not None
        )

    ordered_profiles = tuple(sorted(profiles, key=_star_condition_sort_key))
    if ordered_profiles:
        strongest_rank = max(_star_condition_strength(profile) for profile in ordered_profiles)
        weakest_rank = min(_star_condition_strength(profile) for profile in ordered_profiles)
        strongest_profiles = tuple(
            profile
            for profile in ordered_profiles
            if _star_condition_strength(profile) == strongest_rank
        )
        weakest_profiles = tuple(
            profile
            for profile in ordered_profiles
            if _star_condition_strength(profile) == weakest_rank
        )
    else:
        strongest_profiles = ()
        weakest_profiles = ()

    return StarChartConditionProfile(
        profiles=ordered_profiles,
        catalog_position_count=sum(1 for profile in ordered_profiles if profile.condition_state.name == "catalog_position"),
        heliacal_event_count=sum(1 for profile in ordered_profiles if profile.result_kind == "heliacal_event"),
        unified_merge_count=sum(1 for profile in ordered_profiles if profile.condition_state.name == "unified_merge"),
        strongest_profiles=strongest_profiles,
        weakest_profiles=weakest_profiles,
    )


def star_condition_network_profile(
    *,
    catalog_positions: list[StarPosition] | None = None,
    heliacal_events: list[HeliacalEvent] | None = None,
    fixed_stars: list[FixedStar] | None = None,
) -> StarConditionNetworkProfile:
    """Build a deterministic network from current star relation and condition truth."""

    node_kinds: dict[str, str] = {}
    edge_rows: set[tuple[str, str, str, str, str]] = set()

    def ensure_node(node_id: str, kind: str) -> None:
        existing = node_kinds.get(node_id)
        if existing is None:
            node_kinds[node_id] = kind
        elif existing != kind:
            raise ValueError("star network node ids must not change kind")

    if catalog_positions is not None:
        for position in catalog_positions:
            profile = _derive_star_position_condition_profile(position)
            if position.relation is None or profile is None:
                continue
            source_id = _catalog_position_source_node_id(position)
            target_id = f"star:{position.name}"
            ensure_node(source_id, "source")
            ensure_node(target_id, "star")
            edge_rows.add((
                source_id,
                target_id,
                position.relation.kind,
                position.relation.basis,
                profile.condition_state.name,
            ))

    if heliacal_events is not None:
        for event in heliacal_events:
            profile = _derive_heliacal_condition_profile(event)
            if event.relation is None or profile is None:
                continue
            source_id = _heliacal_event_node_id(event)
            target_id = f"star:{event.star_name}"
            ensure_node(source_id, "event")
            ensure_node(target_id, "star")
            edge_rows.add((
                source_id,
                target_id,
                event.relation.kind,
                event.relation.basis,
                profile.condition_state.name,
            ))

    if fixed_stars is not None:
        for star in fixed_stars:
            profile = _derive_fixed_star_condition_profile(star)
            if star.relation is None or profile is None:
                continue
            source_id = _fixed_star_source_node_id(star)
            target_id = f"star:{star.name}"
            ensure_node(source_id, "source")
            ensure_node(target_id, "star")
            edge_rows.add((
                source_id,
                target_id,
                star.relation.kind,
                star.relation.basis,
                profile.condition_state.name,
            ))

    ordered_edges = tuple(sorted(
        (
            StarConditionNetworkEdge(
                source_id=source_id,
                target_id=target_id,
                relation_kind=relation_kind,
                relation_basis=relation_basis,
                condition_state=condition_state,
            )
            for source_id, target_id, relation_kind, relation_basis, condition_state in edge_rows
        ),
        key=_star_network_edge_sort_key,
    ))

    incoming_counts = {node_id: 0 for node_id in node_kinds}
    outgoing_counts = {node_id: 0 for node_id in node_kinds}
    for edge in ordered_edges:
        outgoing_counts[edge.source_id] += 1
        incoming_counts[edge.target_id] += 1

    ordered_nodes = tuple(sorted(
        (
            StarConditionNetworkNode(
                node_id=node_id,
                kind=kind,
                incoming_count=incoming_counts[node_id],
                outgoing_count=outgoing_counts[node_id],
            )
            for node_id, kind in node_kinds.items()
        ),
        key=_star_network_node_sort_key,
    ))

    if ordered_nodes:
        max_degree = max(node.incoming_count + node.outgoing_count for node in ordered_nodes)
        most_connected_nodes = tuple(
            node
            for node in ordered_nodes
            if node.incoming_count + node.outgoing_count == max_degree
        )
    else:
        most_connected_nodes = ()

    return StarConditionNetworkProfile(
        nodes=ordered_nodes,
        edges=ordered_edges,
        isolated_nodes=tuple(
            node
            for node in ordered_nodes
            if node.incoming_count + node.outgoing_count == 0
        ),
        most_connected_nodes=most_connected_nodes,
    )

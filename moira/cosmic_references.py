"""Typed cosmic reference points with explicit astronomical semantics.

This registry keeps three different objects visibly separate: physical catalog
objects, coordinate-frame landmarks, and declared proxy references for broad
or model-dependent regions.  Every released direction is an ICRS/J2000 anchor
that Moira projects into the true ecliptic of date at runtime.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Literal

from .constants import J2000, sign_of
from .coordinates import icrf_to_true_ecliptic
from .deep_sky import deep_sky_object


__all__ = [
    "COSMIC_REFERENCE_CATALOG_VERSION",
    "CosmicReferenceKind",
    "CosmicReferenceDefinition",
    "CosmicReferencePosition",
    "cosmic_reference_definition",
    "cosmic_reference_at",
    "all_cosmic_references_at",
    "list_cosmic_references",
]


COSMIC_REFERENCE_CATALOG_VERSION = "2026.09.08.1"

_GALACTIC_AUTHORITY_URL = (
    "https://www.aanda.org/articles/aa/abs/2011/02/aa14961-10/aa14961-10.html"
)
_SUPERGALACTIC_AUTHORITY_URL = (
    "https://cxc.cfa.harvard.edu/ciao/ahelp/prop-coords.html"
)
_VIRGO_STRUCTURE_URL = "https://ned.ipac.caltech.edu/level5/Binggeli/Bin2.html"
_GREAT_ATTRACTOR_URL = "https://arxiv.org/abs/astro-ph/0006126"
_SHAPLEY_CORE_URL = "https://arxiv.org/abs/astro-ph/0310802"


class CosmicReferenceKind(str, Enum):
    """Vessel: The three semantic classes admitted by the registry."""

    PHYSICAL_OBJECT = "physical_object"
    COORDINATE_LANDMARK = "coordinate_landmark"
    PROXY_REFERENCE = "proxy_reference"


@dataclass(frozen=True, slots=True)
class CosmicReferenceDefinition:
    """Vessel: One immutable reference identity and its source declaration."""

    reference_id: str
    name: str
    aliases: tuple[str, ...]
    kind: CosmicReferenceKind
    anchor: str
    icrs_ra_deg: float
    icrs_dec_deg: float
    source_frame: Literal["ICRS"]
    source_epoch_jd_tt: float
    position_semantics: str
    coordinate_authority: str
    semantic_authority: str
    source_version: str
    citation_urls: tuple[str, ...]
    catalog_version: str


@dataclass(frozen=True, slots=True)
class CosmicReferencePosition:
    """Vessel: One typed reference projected to the true ecliptic of date."""

    definition: CosmicReferenceDefinition
    longitude: float
    latitude: float
    sign: str
    sign_symbol: str
    sign_degree: float
    jd_tt: float


def _definition(
    reference_id: str,
    name: str,
    aliases: tuple[str, ...],
    kind: CosmicReferenceKind,
    anchor: str,
    ra_deg: float,
    dec_deg: float,
    position_semantics: str,
    coordinate_authority: str,
    semantic_authority: str,
    source_version: str,
    citation_urls: tuple[str, ...],
) -> CosmicReferenceDefinition:
    """Build one definition in the registry's common ICRS/J2000 frame."""

    return CosmicReferenceDefinition(
        reference_id=reference_id,
        name=name,
        aliases=aliases,
        kind=kind,
        anchor=anchor,
        icrs_ra_deg=ra_deg,
        icrs_dec_deg=dec_deg,
        source_frame="ICRS",
        source_epoch_jd_tt=J2000,
        position_semantics=position_semantics,
        coordinate_authority=coordinate_authority,
        semantic_authority=semantic_authority,
        source_version=source_version,
        citation_urls=citation_urls,
        catalog_version=COSMIC_REFERENCE_CATALOG_VERSION,
    )


@lru_cache(maxsize=1)
def _catalog() -> tuple[CosmicReferenceDefinition, ...]:
    """Build and validate the complete release-bound reference registry."""

    sgr_a = deep_sky_object("Sagittarius A*")
    m87 = deep_sky_object("M87 Galaxy")
    galactic_authority = "Liu, Zhu & Zhang (2011), A&A 526 A16"
    supergalactic_authority = (
        "de Vaucouleurs supergalactic frame as tabulated by Chandra CIAO"
    )
    records = (
        _definition(
            "galactic_frame_origin",
            "Galactic Center Frame Origin",
            ("Galactic Center", "GC"),
            CosmicReferenceKind.COORDINATE_LANDMARK,
            "IAU galactic longitude 0 degrees, latitude 0 degrees",
            266.405100,
            -28.936175,
            "coordinate_frame_origin_not_physical_source",
            galactic_authority,
            galactic_authority,
            "IAU 1958 system in ICRS/J2000 realization",
            (_GALACTIC_AUTHORITY_URL,),
        ),
        _definition(
            "galactic_anticenter",
            "Galactic Anti-Center",
            ("GAC",),
            CosmicReferenceKind.COORDINATE_LANDMARK,
            "antipode of the IAU galactic frame origin",
            86.405100,
            28.936175,
            "derived_coordinate_antipode",
            galactic_authority,
            galactic_authority,
            "IAU 1958 system in ICRS/J2000 realization",
            (_GALACTIC_AUTHORITY_URL,),
        ),
        _definition(
            "north_galactic_pole",
            "North Galactic Pole",
            ("NGP",),
            CosmicReferenceKind.COORDINATE_LANDMARK,
            "positive pole of the IAU galactic frame",
            192.859508,
            27.128336,
            "coordinate_frame_pole",
            galactic_authority,
            galactic_authority,
            "IAU 1958 system in ICRS/J2000 realization",
            (_GALACTIC_AUTHORITY_URL,),
        ),
        _definition(
            "south_galactic_pole",
            "South Galactic Pole",
            ("SGP",),
            CosmicReferenceKind.COORDINATE_LANDMARK,
            "antipode of the north galactic pole",
            12.859508,
            -27.128336,
            "derived_coordinate_antipode",
            galactic_authority,
            galactic_authority,
            "IAU 1958 system in ICRS/J2000 realization",
            (_GALACTIC_AUTHORITY_URL,),
        ),
        _definition(
            "supergalactic_longitude_origin",
            "Supergalactic Longitude Origin",
            ("Formal Supergalactic Origin", "SGL 0"),
            CosmicReferenceKind.COORDINATE_LANDMARK,
            "supergalactic longitude 0 degrees, latitude 0 degrees",
            42.310125,
            59.52834722222222,
            "coordinate_frame_longitude_origin_not_virgo_center",
            supergalactic_authority,
            supergalactic_authority,
            "CIAO 4.18 institutional coordinate table",
            (_SUPERGALACTIC_AUTHORITY_URL,),
        ),
        _definition(
            "north_supergalactic_pole",
            "North Supergalactic Pole",
            ("NSGP",),
            CosmicReferenceKind.COORDINATE_LANDMARK,
            "positive pole of the de Vaucouleurs supergalactic frame",
            283.7540833333333,
            15.708936111111111,
            "coordinate_frame_pole",
            supergalactic_authority,
            supergalactic_authority,
            "CIAO 4.18 institutional coordinate table",
            (_SUPERGALACTIC_AUTHORITY_URL,),
        ),
        _definition(
            "south_supergalactic_pole",
            "South Supergalactic Pole",
            ("SSGP",),
            CosmicReferenceKind.COORDINATE_LANDMARK,
            "antipode of the north supergalactic pole",
            103.7540833333333,
            -15.708936111111111,
            "derived_coordinate_antipode",
            supergalactic_authority,
            supergalactic_authority,
            "derived from CIAO 4.18 institutional coordinate table",
            (_SUPERGALACTIC_AUTHORITY_URL,),
        ),
        _definition(
            "sagittarius_a_star",
            "Sagittarius A*",
            ("Sgr A*",),
            CosmicReferenceKind.PHYSICAL_OBJECT,
            "SIMBAD compact source NAME Sgr A*",
            sgr_a.ra_deg,
            sgr_a.dec_deg,
            "physical_compact_source_catalog_direction",
            f"SIMBAD coordinate record {sgr_a.coordinate_bibcode}",
            "SIMBAD physical-object identity",
            f"moira-deep-sky {sgr_a.catalog_version}",
            (
                "https://simbad.cds.unistra.fr/simbad/sim-id?Ident=NAME+Sgr+A%2A",
            ),
        ),
        _definition(
            "m87_galaxy",
            "M87 Galaxy",
            ("M87", "M 87", "Virgo A", "NGC 4486"),
            CosmicReferenceKind.PHYSICAL_OBJECT,
            "SIMBAD galaxy catalog center M 87",
            m87.ra_deg,
            m87.dec_deg,
            "physical_galaxy_catalog_center",
            f"SIMBAD coordinate record {m87.coordinate_bibcode}",
            "SIMBAD physical-object identity",
            f"moira-deep-sky {m87.catalog_version}",
            ("https://simbad.cds.unistra.fr/simbad/sim-id?Ident=M+87",),
        ),
        _definition(
            "virgo_m87_astrological_sgc",
            "Virgo/M87 Astrological SGC",
            ("Super-Galactic Center", "Super Galactic Center", "Astrological SGC"),
            CosmicReferenceKind.PROXY_REFERENCE,
            "M87 Galaxy catalog center",
            m87.ra_deg,
            m87.dec_deg,
            "legacy_astrological_convention_not_formal_supergalactic_origin",
            f"SIMBAD M87 coordinate record {m87.coordinate_bibcode}",
            "Moira legacy astrological convention, qualified by NED Virgo structure review",
            f"moira-deep-sky {m87.catalog_version}",
            (
                "https://simbad.cds.unistra.fr/simbad/sim-id?Ident=M+87",
                _VIRGO_STRUCTURE_URL,
            ),
        ),
        _definition(
            "great_attractor_norma_proxy",
            "Great Attractor / Norma Cluster Proxy",
            ("Great Attractor", "Norma Cluster Proxy", "ACO 3627"),
            CosmicReferenceKind.PROXY_REFERENCE,
            "Norma Cluster (ACO 3627) catalog center",
            243.59375,
            -60.86861111111111,
            "observational_proxy_not_unique_point_center",
            "SIMBAD ACO 3627 coordinate record 2002ApJ...580..774E",
            "Woudt & Kraan-Korteweg (2000) potential-well proxy assessment",
            "SIMBAD snapshot 2026-09-08",
            (
                "https://simbad.cds.unistra.fr/simbad/sim-id?Ident=ACO+3627",
                _GREAT_ATTRACTOR_URL,
            ),
        ),
        _definition(
            "shapley_a3558_proxy",
            "Shapley Concentration / ACO 3558 Proxy",
            ("Shapley Concentration", "Shapley Attractor", "ACO 3558"),
            CosmicReferenceKind.PROXY_REFERENCE,
            "ACO 3558 catalog center within the multicluster Shapley core",
            202.0135,
            -31.5265,
            "central_cluster_proxy_not_unique_supercluster_center",
            "SIMBAD ACO 3558 coordinate record 2022A&A...661A..38P",
            "Akimoto et al. (2003) multicluster-core assessment",
            "SIMBAD snapshot 2026-09-08",
            (
                "https://simbad.cds.unistra.fr/simbad/sim-id?Ident=ACO+3558",
                _SHAPLEY_CORE_URL,
            ),
        ),
    )
    _validate_catalog(records)
    return records


def _normalized_label(value: str) -> str:
    """Normalize one public identity label for exact lookup."""

    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _validate_catalog(records: tuple[CosmicReferenceDefinition, ...]) -> None:
    """Reject semantic, identity, or coordinate drift in the static registry."""

    expected_counts = {
        CosmicReferenceKind.PHYSICAL_OBJECT: 2,
        CosmicReferenceKind.COORDINATE_LANDMARK: 7,
        CosmicReferenceKind.PROXY_REFERENCE: 3,
    }
    actual_counts = {
        kind: sum(record.kind is kind for record in records)
        for kind in CosmicReferenceKind
    }
    if actual_counts != expected_counts:
        raise RuntimeError(
            f"cosmic reference class counts {actual_counts!r} != {expected_counts!r}"
        )
    reference_ids: set[str] = set()
    labels: dict[str, str] = {}
    for record in records:
        if record.reference_id in reference_ids:
            raise RuntimeError(f"duplicate cosmic reference id {record.reference_id!r}")
        reference_ids.add(record.reference_id)
        if not (math.isfinite(record.icrs_ra_deg) and 0.0 <= record.icrs_ra_deg < 360.0):
            raise RuntimeError(f"invalid ICRS right ascension for {record.name!r}")
        if not (math.isfinite(record.icrs_dec_deg) and -90.0 <= record.icrs_dec_deg <= 90.0):
            raise RuntimeError(f"invalid ICRS declination for {record.name!r}")
        if record.source_frame != "ICRS" or record.source_epoch_jd_tt != J2000:
            raise RuntimeError(f"unexpected source frame or epoch for {record.name!r}")
        required_text = (
            record.reference_id,
            record.name,
            record.anchor,
            record.position_semantics,
            record.coordinate_authority,
            record.semantic_authority,
            record.source_version,
        )
        if any(not value.strip() for value in required_text):
            raise RuntimeError(f"incomplete semantic receipt for {record.name!r}")
        if record.catalog_version != COSMIC_REFERENCE_CATALOG_VERSION:
            raise RuntimeError(f"unexpected catalog version for {record.name!r}")
        if not record.citation_urls or any(
            not url.startswith("https://") for url in record.citation_urls
        ):
            raise RuntimeError(f"invalid citation receipt for {record.name!r}")
        for label in (record.reference_id, record.name, *record.aliases):
            key = _normalized_label(label)
            owner = labels.get(key)
            if owner is not None and owner != record.reference_id:
                raise RuntimeError(f"cosmic reference label {label!r} is ambiguous")
            labels[key] = record.reference_id


@lru_cache(maxsize=1)
def _lookup_index() -> dict[str, CosmicReferenceDefinition]:
    """Return the normalized exact-identity index."""

    result: dict[str, CosmicReferenceDefinition] = {}
    for record in _catalog():
        for label in (record.reference_id, record.name, *record.aliases):
            result[_normalized_label(label)] = record
    return result


def _coerce_kind(
    kind: CosmicReferenceKind | str | None,
) -> CosmicReferenceKind | None:
    """Normalize one optional registry-kind filter."""

    if kind is None or isinstance(kind, CosmicReferenceKind):
        return kind
    try:
        return CosmicReferenceKind(kind.strip().casefold())
    except (AttributeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in CosmicReferenceKind)
        raise ValueError(f"kind must be one of: {allowed}") from exc


def cosmic_reference_definition(name: str) -> CosmicReferenceDefinition:
    """Return one definition by stable id, canonical name, or exact alias."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("cosmic reference name must be a non-empty string")
    record = _lookup_index().get(_normalized_label(name))
    if record is None:
        raise KeyError(f"Cosmic reference {name!r} is not in the released registry")
    return record


def list_cosmic_references(
    kind: CosmicReferenceKind | str | None = None,
) -> list[str]:
    """Return canonical reference names, optionally filtered by semantic kind."""

    selected_kind = _coerce_kind(kind)
    return sorted(
        record.name
        for record in _catalog()
        if selected_kind is None or record.kind is selected_kind
    )


def cosmic_reference_at(name: str, jd_tt: float) -> CosmicReferencePosition:
    """Project one fixed ICRS/J2000 reference direction to true ecliptic of date."""

    if isinstance(jd_tt, bool) or not math.isfinite(jd_tt):
        raise ValueError("jd_tt must be finite")
    definition = cosmic_reference_definition(name)
    ra = math.radians(definition.icrs_ra_deg)
    dec = math.radians(definition.icrs_dec_deg)
    cos_dec = math.cos(dec)
    vector = (cos_dec * math.cos(ra), cos_dec * math.sin(ra), math.sin(dec))
    longitude, latitude, _ = icrf_to_true_ecliptic(jd_tt, vector)
    sign, sign_symbol, sign_degree = sign_of(longitude)
    return CosmicReferencePosition(
        definition=definition,
        longitude=longitude,
        latitude=latitude,
        sign=sign,
        sign_symbol=sign_symbol,
        sign_degree=sign_degree,
        jd_tt=float(jd_tt),
    )


def all_cosmic_references_at(
    jd_tt: float,
    kind: CosmicReferenceKind | str | None = None,
) -> dict[str, CosmicReferencePosition]:
    """Return all selected reference positions in deterministic name order."""

    return {
        name: cosmic_reference_at(name, jd_tt)
        for name in list_cosmic_references(kind)
    }

"""Services for asteroid (and later comet) surfaces.

Designed for "fast API" use on websites:
- Automatically uses sovereign small-body Type 13 + native evaluator when loaded at startup.
- Falls back gracefully.
"""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from datetime import timezone
from typing import Any

from moira import Moira
from moira.asteroids import ASTEROID_NAIF, AsteroidData, asteroid_at
from moira.asteroid_families import (
    asteroid_family,
    families_in_chart,
    family_members,
)
from moira.centaurs import CENTAUR_NAMES
from moira.classical_asteroids import CLASSICAL_NAMES
from moira.julian import jd_from_datetime
from moira.main_belt import MAIN_BELT_NAMES
from moira.tno import TNO_NAMES

from ..models.asteroids import (
    AsteroidFamiliesInChartProvenanceResponse,
    AsteroidFamiliesInChartRequest,
    AsteroidFamiliesInChartResponse,
    AsteroidFamilyLookupProvenanceResponse,
    AsteroidFamilyLookupResponse,
    AsteroidFamilyMembersProvenanceResponse,
    AsteroidFamilyMembersResponse,
    AsteroidListItem,
    AsteroidListProvenanceResponse,
    AsteroidListResponse,
    AsteroidPositionRequest,
    AsteroidPositionResponse,
    AsteroidSubsetCatalogItem,
    AsteroidSubsetListProvenanceResponse,
    AsteroidSubsetListResponse,
    AsteroidSubsetPositionsProvenanceResponse,
    AsteroidSubsetPositionsRequest,
    AsteroidSubsetPositionsResponse,
    AsteroidSubsetSlug,
    AsteroidSubsetSummaryResponse,
    AsteroidSubsetsResponse,
    AsteroidsBulkRequest,
    AsteroidsBulkResponse,
)
from ..serializers.asteroids import (
    serialize_asteroid,
    serialize_asteroid_bulk_provenance,
    serialize_asteroid_position_provenance,
)


def _get_small_body_reader(engine: Moira) -> Any | None:
    """
    Return the active reader (which now includes sovereign small-body kernels
    loaded via the proper Moira engine API).
    """
    try:
        return engine._reader  # The facade maintains the full pool (planetary + small bodies)
    except Exception:
        return None


def _covered_bodies(reader: Any | None) -> frozenset[int]:
    if reader is None or not hasattr(reader, "covered_bodies"):
        return frozenset()
    return frozenset(reader.covered_bodies())


_KNOWN_ASTEROID_NAMES = frozenset(name.casefold() for name in ASTEROID_NAIF)
_KNOWN_ASTEROID_IDS = frozenset(ASTEROID_NAIF.values())
_ASTEROID_NAME_BY_ID = {naif_id: name for name, naif_id in ASTEROID_NAIF.items()}
_ASTEROID_NAME_BY_CASEFOLD = {name.casefold(): name for name in ASTEROID_NAIF}


@dataclass(frozen=True, slots=True)
class _AsteroidSubset:
    slug: AsteroidSubsetSlug
    label: str
    source_module: str
    catalog_source: str
    names_by_id: dict[int, str]

    @property
    def names(self) -> list[str]:
        return list(self.names_by_id.values())

    @property
    def ids(self) -> frozenset[int]:
        return frozenset(self.names_by_id)

    @property
    def names_casefold(self) -> dict[str, str]:
        return {name.casefold(): name for name in self.names}


_ASTEROID_SUBSETS: dict[AsteroidSubsetSlug, _AsteroidSubset] = {
    AsteroidSubsetSlug.classical: _AsteroidSubset(
        slug=AsteroidSubsetSlug.classical,
        label="Classical asteroids",
        source_module="moira.classical_asteroids",
        catalog_source="CLASSICAL_NAMES",
        names_by_id=CLASSICAL_NAMES,
    ),
    AsteroidSubsetSlug.main_belt: _AsteroidSubset(
        slug=AsteroidSubsetSlug.main_belt,
        label="Main-belt asteroid subset",
        source_module="moira.main_belt",
        catalog_source="MAIN_BELT_NAMES",
        names_by_id=MAIN_BELT_NAMES,
    ),
    AsteroidSubsetSlug.centaurs: _AsteroidSubset(
        slug=AsteroidSubsetSlug.centaurs,
        label="Centaur subset",
        source_module="moira.centaurs",
        catalog_source="CENTAUR_NAMES",
        names_by_id=CENTAUR_NAMES,
    ),
    AsteroidSubsetSlug.tnos: _AsteroidSubset(
        slug=AsteroidSubsetSlug.tnos,
        label="Trans-Neptunian object subset",
        source_module="moira.tno",
        catalog_source="TNO_NAMES",
        names_by_id=TNO_NAMES,
    ),
}


def _known_asteroid_entry(body: str | int) -> bool:
    if isinstance(body, int):
        return body in _KNOWN_ASTEROID_IDS
    if body.isdecimal():
        return int(body) in _KNOWN_ASTEROID_IDS
    return body.casefold() in _KNOWN_ASTEROID_NAMES


def _resolve_asteroid_name(body: str | int) -> str:
    if isinstance(body, int):
        return _ASTEROID_NAME_BY_ID[body]
    if body.isdecimal():
        return _ASTEROID_NAME_BY_ID[int(body)]
    return _ASTEROID_NAME_BY_CASEFOLD[body.casefold()]


def _kernel_source(reader: Any | None) -> str:
    return "loaded_small_body_reader" if reader is not None else "active_reader_or_default_kernel_path"


def compute_asteroid_position(
    engine: Moira, request: AsteroidPositionRequest
) -> AsteroidPositionResponse:
    """High-performance asteroid position using native Type 13 path when available."""
    reader = _get_small_body_reader(engine)
    jd_ut = jd_from_datetime(request.dt)
    data: AsteroidData = asteroid_at(
        request.body,
        jd_ut,
        reader=reader,   # This is the key: passes sovereign fast kernels if present
    )

    covered = _covered_bodies(reader)
    loaded_kernel_available = data.naif_id in covered

    return serialize_asteroid(
        data,
        is_sovereign=loaded_kernel_available,
        provenance=serialize_asteroid_position_provenance(
            request=request,
            data=data,
            jd_ut=jd_ut,
            kernel_source=_kernel_source(reader),
            known_catalog_entry=_known_asteroid_entry(request.body),
            loaded_kernel_available=loaded_kernel_available,
        ),
    )


def compute_asteroids_bulk(
    engine: Moira, request: AsteroidsBulkRequest
) -> AsteroidsBulkResponse:
    """Bulk asteroid positions — the fast path for websites loading many bodies at once."""
    reader = _get_small_body_reader(engine)
    covered = _covered_bodies(reader)

    results = {}
    missing: list[str] = []

    jd_ut = jd_from_datetime(request.dt)
    for body in request.bodies:
        try:
            data = asteroid_at(body, jd_ut, reader=reader)
            loaded_kernel_available = data.naif_id in covered
            results[str(body)] = serialize_asteroid(
                data,
                is_sovereign=loaded_kernel_available,
                provenance=serialize_asteroid_position_provenance(
                    request=AsteroidPositionRequest(dt=request.dt, body=body),
                    data=data,
                    jd_ut=jd_ut,
                    kernel_source=_kernel_source(reader),
                    known_catalog_entry=_known_asteroid_entry(body),
                    loaded_kernel_available=loaded_kernel_available,
                ),
            )
        except Exception:
            if not request.skip_missing:
                raise
            missing.append(str(body))

    return AsteroidsBulkResponse(
        dt=request.dt,
        results=results,
        missing=missing,
        sovereign_used=any(result.is_sovereign for result in results.values()),
        provenance=serialize_asteroid_bulk_provenance(
            request=request,
            jd_ut=jd_ut,
            kernel_source=_kernel_source(reader),
            returned_bodies=[result.name for result in results.values()],
            missing_bodies=missing,
            loaded_kernel_available=bool(covered),
        ),
    )


def list_sovereign_asteroids(
    engine: Moira,
    name_filter: str | None = None,
    limit: int = 500,
) -> AsteroidListResponse:
    """
    Return bodies available in the loaded sovereign small-body kernels.
    Supports basic name/NAIF filtering for website search.
    """
    reader = _get_small_body_reader(engine)
    if reader is None:
        return AsteroidListResponse(
            bodies=[],
            total=0,
            provenance=AsteroidListProvenanceResponse(
                availability_source="no_loaded_reader",
                loaded_kernel_available=False,
                requested_query=name_filter,
                limit=limit,
                returned_count=0,
                stage_sequence=["reader_availability_check", "loaded_kernel_list_serialization"],
            ),
        )

    covered_ids = _covered_bodies(reader)
    result = [
        AsteroidListItem(name=name, naif_id=naif_id)
        for name, naif_id in ASTEROID_NAIF.items()
        if naif_id in covered_ids
    ]
    if name_filter:
        nf = name_filter.lower()
        result = [
            body for body in result
            if nf in body.name.lower() or nf in str(body.naif_id)
        ]
    result.sort(key=lambda body: body.name)
    limited = result[:limit]
    return AsteroidListResponse(
        bodies=limited,
        total=len(limited),
        provenance=AsteroidListProvenanceResponse(
            availability_source="loaded_reader_covered_bodies",
            loaded_kernel_available=True,
            requested_query=name_filter,
            limit=limit,
            returned_count=len(limited),
            stage_sequence=["reader_coverage_intersection", "loaded_kernel_list_serialization"],
        ),
    )


def list_asteroid_subsets() -> AsteroidSubsetsResponse:
    return AsteroidSubsetsResponse(
        subsets=[
            AsteroidSubsetSummaryResponse(
                subset=subset.slug,
                label=subset.label,
                catalog_source=subset.catalog_source,
                member_count=len(subset.names_by_id),
            )
            for subset in _ASTEROID_SUBSETS.values()
        ],
        total=len(_ASTEROID_SUBSETS),
        stage_sequence=["subset_registry_serialization"],
    )


def list_asteroid_subset(
    engine: Moira,
    subset_slug: AsteroidSubsetSlug,
    name_filter: str | None = None,
    limit: int = 500,
) -> AsteroidSubsetListResponse:
    subset = _ASTEROID_SUBSETS[subset_slug]
    reader = _get_small_body_reader(engine)
    covered_ids = _covered_bodies(reader)

    bodies = [
        AsteroidSubsetCatalogItem(
            name=name,
            naif_id=naif_id,
            loaded_kernel_available=naif_id in covered_ids,
        )
        for naif_id, name in subset.names_by_id.items()
    ]
    if name_filter:
        nf = name_filter.casefold()
        bodies = [
            body for body in bodies
            if nf in body.name.casefold() or nf in str(body.naif_id)
        ]
    bodies.sort(key=lambda body: body.name)
    limited = bodies[:limit]
    return AsteroidSubsetListResponse(
        subset=subset.slug,
        label=subset.label,
        bodies=limited,
        total=len(limited),
        provenance=AsteroidSubsetListProvenanceResponse(
            catalog_source=subset.catalog_source,
            subset_source_module=subset.source_module,
            availability_source="loaded_reader_covered_bodies",
            loaded_kernel_available=bool(covered_ids),
            requested_query=name_filter,
            limit=limit,
            returned_count=len(limited),
            stage_sequence=["subset_catalog_selection", "reader_coverage_intersection"],
        ),
    )


def _resolve_subset_request_bodies(
    subset: _AsteroidSubset,
    bodies: list[str | int] | None,
    *,
    skip_missing: bool,
) -> tuple[list[str], list[str]]:
    if bodies is None:
        return subset.names, []

    resolved: list[str] = []
    missing: list[str] = []
    for body in bodies:
        try:
            name = _resolve_asteroid_name(body)
            if ASTEROID_NAIF[name] not in subset.ids:
                raise KeyError(body)
            resolved.append(name)
        except Exception:
            if not skip_missing:
                raise
            missing.append(str(body))
    return resolved, missing


def compute_asteroid_subset_positions(
    engine: Moira,
    subset_slug: AsteroidSubsetSlug,
    request: AsteroidSubsetPositionsRequest,
) -> AsteroidSubsetPositionsResponse:
    subset = _ASTEROID_SUBSETS[subset_slug]
    resolved_bodies, missing = _resolve_subset_request_bodies(
        subset,
        request.bodies,
        skip_missing=request.skip_missing,
    )
    if not resolved_bodies:
        reader = _get_small_body_reader(engine)
        return AsteroidSubsetPositionsResponse(
            subset=subset.slug,
            label=subset.label,
            dt=request.dt,
            results={},
            missing=missing,
            sovereign_used=False,
            provenance=AsteroidSubsetPositionsProvenanceResponse(
                subset=subset.slug,
                subset_source_module=subset.source_module,
                requested_datetime=request.dt.isoformat(),
                normalized_datetime_utc=request.dt.astimezone(timezone.utc).isoformat(),
                requested_bodies=[str(body) for body in request.bodies] if request.bodies else [],
                resolved_subset_bodies=[],
                returned_bodies=[],
                missing_bodies=missing,
                loaded_kernel_available=bool(_covered_bodies(reader)),
                stage_sequence=[
                    "subset_catalog_selection",
                    "datetime_validation",
                    "empty_subset_position_response_serialization",
                ],
            ),
        )
    bulk = compute_asteroids_bulk(
        engine,
        AsteroidsBulkRequest(
            dt=request.dt,
            bodies=resolved_bodies,
            skip_missing=request.skip_missing,
        ),
    )
    combined_missing = [*missing, *bulk.missing]
    return AsteroidSubsetPositionsResponse(
        subset=subset.slug,
        label=subset.label,
        dt=request.dt,
        results=bulk.results,
        missing=combined_missing,
        sovereign_used=bulk.sovereign_used,
        provenance=AsteroidSubsetPositionsProvenanceResponse(
            subset=subset.slug,
            subset_source_module=subset.source_module,
            requested_datetime=request.dt.isoformat(),
            normalized_datetime_utc=request.dt.astimezone(timezone.utc).isoformat(),
            requested_bodies=[str(body) for body in request.bodies] if request.bodies else subset.names,
            resolved_subset_bodies=resolved_bodies,
            returned_bodies=[result.name for result in bulk.results.values()],
            missing_bodies=combined_missing,
            loaded_kernel_available=bulk.provenance.loaded_kernel_available,
            stage_sequence=[
                "subset_catalog_selection",
                "datetime_validation",
                "julian_day_conversion",
                "asteroid_bulk_position_transport",
                "subset_position_response_serialization",
            ],
        ),
    )


def lookup_asteroid_family(number: int) -> AsteroidFamilyLookupResponse:
    family = asteroid_family(number)
    return AsteroidFamilyLookupResponse(
        number=number,
        family_name=family,
        provenance=AsteroidFamilyLookupProvenanceResponse(
            requested_number=number,
            stage_sequence=["mpc_number_validation", "nesvorny_family_lookup"],
        ),
    )


def list_asteroid_family_members(
    family_name: str,
    *,
    offset: int = 0,
    limit: int = 500,
) -> AsteroidFamilyMembersResponse:
    members = family_members(family_name)
    limited = members[offset:offset + limit]
    return AsteroidFamilyMembersResponse(
        family_name=family_name,
        members=limited,
        total_available=len(members),
        returned_count=len(limited),
        provenance=AsteroidFamilyMembersProvenanceResponse(
            requested_family_name=family_name,
            offset=offset,
            limit=limit,
            total_available=len(members),
            returned_count=len(limited),
            stage_sequence=[
                "family_name_lookup",
                "mpc_member_catalog_selection",
                "bounded_member_serialization",
            ],
        ),
    )


def group_asteroid_families_in_chart(
    request: AsteroidFamiliesInChartRequest,
) -> AsteroidFamiliesInChartResponse:
    groups = families_in_chart(request.numbers)
    grouped_numbers = {number for members in groups.values() for number in members}
    ungrouped = [number for number in request.numbers if number not in grouped_numbers]
    return AsteroidFamiliesInChartResponse(
        groups=groups,
        ungrouped_numbers=ungrouped,
        provenance=AsteroidFamiliesInChartProvenanceResponse(
            requested_count=len(request.numbers),
            grouped_count=len(grouped_numbers),
            ungrouped_count=len(ungrouped),
            stage_sequence=[
                "mpc_number_list_validation",
                "nesvorny_family_grouping",
                "family_group_response_serialization",
            ],
        ),
    )

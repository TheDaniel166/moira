"""Serializers for deep-sky catalog records and ecliptic positions."""

from __future__ import annotations

from datetime import datetime, timezone

from moira.deep_sky import DeepSkyObject, DeepSkyPosition

from ..models.deep_sky import (
    DeepSkyCatalogItemResponse,
    DeepSkyPositionProvenanceResponse,
    DeepSkyPositionResponse,
)


def serialize_deep_sky_catalog_item(record: DeepSkyObject) -> DeepSkyCatalogItemResponse:
    """Serialize one immutable catalog identity and source receipt."""

    return DeepSkyCatalogItemResponse(
        name=record.canonical_name,
        designation=record.designation,
        aliases=list(record.aliases),
        object_class=record.object_class,
        is_extended=record.is_extended,
        position_semantics=record.position_semantics,
        simbad_main_id=record.simbad_main_id,
        simbad_otype=record.simbad_otype,
        source_ra_deg=record.ra_deg,
        source_dec_deg=record.dec_deg,
        coordinate_bibcode=record.coordinate_bibcode,
        coordinate_quality=record.coordinate_quality,
        proper_motion_admitted=record.proper_motion_admitted,
        star_registry_name=record.star_registry_name,
        nasa_exoplanet_archive_hostname=record.nasa_exoplanet_archive_hostname,
        confirmed_planet_count=record.confirmed_planet_count,
        catalog_version=record.catalog_version,
    )


def serialize_deep_sky_position(
    position: DeepSkyPosition,
    requested_datetime: datetime,
) -> DeepSkyPositionResponse:
    """Serialize one position with its complete catalog/frame provenance."""

    return DeepSkyPositionResponse(
        name=position.name,
        designation=position.designation,
        object_class=position.object_class,
        longitude=position.longitude,
        latitude=position.latitude,
        sign=position.sign,
        sign_symbol=position.sign_symbol,
        sign_degree=position.sign_degree,
        provenance=DeepSkyPositionProvenanceResponse(
            requested_datetime=requested_datetime.isoformat(),
            normalized_datetime_utc=requested_datetime.astimezone(timezone.utc).isoformat(),
            jd_tt=position.jd_tt,
            source_ra_deg=position.source_ra_deg,
            source_dec_deg=position.source_dec_deg,
            source_frame=position.source_frame,
            source_epoch_jd_tt=position.source_epoch_jd_tt,
            position_semantics=position.position_semantics,
            position_source=position.position_source,
            proper_motion_applied=position.proper_motion_applied,
            simbad_main_id=position.simbad_main_id,
            coordinate_bibcode=position.coordinate_bibcode,
            coordinate_quality=position.coordinate_quality,
            catalog_version=position.catalog_version,
            stage_sequence=[
                "datetime_validation",
                "utc_to_tt",
                "deep_sky_identity_resolution",
                "proper_motion_policy",
                "true_ecliptic_of_date_projection",
                "response_serialization",
            ],
        ),
    )

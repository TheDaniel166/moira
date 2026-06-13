"""Serializers for stars surfaces."""

from __future__ import annotations

from datetime import datetime, timezone

from moira.multiple_stars import (
    MultipleStarSystem,
    StarComponent,
    OrbitalElements,
    combined_magnitude,
)
from moira.stars import FixedStar, StarPosition
from moira.variable_stars import (
    CatalogProfile,
    StarStatePair,
    VariableStar,
    VarStarConditionProfile,
)
from moira.constants import sign_of

from ..models.stars import (
    MultipleStarComponentResponse,
    MultipleStarCatalogProvenanceResponse,
    MultipleStarListProvenanceResponse,
    MultipleStarOrbitResponse,
    MultipleStarStateResponse,
    MultipleStarStateProvenanceResponse,
    MultipleStarSystemResponse,
    StarPositionProvenanceResponse,
    StarPositionResponse,
    StarsBulkResponse,
    VariableStarCatalogProvenanceResponse,
    VariableStarComputationProvenanceResponse,
    VariableStarCatalogProfileResponse,
    VariableStarCatalogResponse,
    VariableStarConditionResponse,
    VariableStarPairResponse,
    VariableStarStateResponse,
)
from moira.variable_stars import DEFAULT_VAR_STAR_POLICY


def _condition_state_name(data) -> str | None:
    condition_profile = getattr(data, "condition_profile", None)
    state = getattr(condition_profile, "condition_state", None)
    return getattr(state, "name", None)


def serialize_star_provenance(
    data: StarPosition | FixedStar | dict,
    *,
    requested_datetime: datetime | None = None,
    jd_tt: float | None = None,
) -> StarPositionProvenanceResponse:
    truth = getattr(data, "computation_truth", None)
    classification = getattr(data, "classification", None)
    relation = getattr(data, "relation", None)
    condition_profile = getattr(data, "condition_profile", None)

    return StarPositionProvenanceResponse(
        requested_datetime=requested_datetime.isoformat() if requested_datetime is not None else None,
        normalized_datetime_utc=(
            requested_datetime.astimezone(timezone.utc).isoformat() if requested_datetime is not None else None
        ),
        jd_tt=jd_tt,
        source=getattr(data, "source", None),
        source_mode=getattr(truth, "source_mode", None),
        lookup_kind=getattr(truth, "lookup_kind", getattr(classification, "lookup_kind", None)),
        hipparcos_name=getattr(truth, "hipparcos_name", None),
        constellation=getattr(truth, "constellation", getattr(data, "constellation", None)),
        gaia_match_status=getattr(truth, "gaia_match_status", None),
        gaia_source_index=getattr(truth, "gaia_source_index", getattr(relation, "gaia_source_index", None)),
        source_kind=getattr(classification, "source_kind", getattr(relation, "source_kind", None)),
        merge_state=getattr(classification, "merge_state", None),
        observer_mode=getattr(classification, "observer_mode", None),
        is_topocentric=getattr(truth, "is_topocentric", getattr(data, "is_topocentric", None)),
        true_position=getattr(truth, "true_position", None),
        dedup_applied=getattr(truth, "dedup_applied", None),
        relation_kind=getattr(relation, "kind", None),
        relation_basis=getattr(relation, "basis", None),
        relation_star_name=getattr(relation, "star_name", None),
        condition_result_kind=getattr(condition_profile, "result_kind", None),
        condition_state=_condition_state_name(data),
        stage_sequence=[
            "datetime_validation",
            "ut_to_tt",
            "star_catalog_resolution",
            "sovereign_registry_position",
            "fixed_star_response_serialization",
        ],
    )


def serialize_star(
    data: StarPosition | FixedStar | dict,
    is_variable: bool = False,
    *,
    requested_datetime: datetime | None = None,
    jd_tt: float | None = None,
) -> StarPositionResponse:
    """Normalize star position result."""
    if isinstance(data, dict):
        lon = data.get("longitude", data.get("ecliptic_longitude", 0.0))
        lat = data.get("latitude", data.get("ecliptic_latitude", 0.0))
        name = data.get("name", data.get("designation", "Unknown"))
        designation = data.get("designation")
        mag = data.get("magnitude")
    else:
        lon = getattr(data, "longitude", 0.0)
        lat = getattr(data, "latitude", 0.0)
        name = getattr(data, "name", "Unknown")
        designation = getattr(data, "designation", None)
        mag = getattr(data, "magnitude", None)

    sign, sign_symbol, sign_degree = sign_of(lon)

    return StarPositionResponse(
        name=name,
        designation=designation,
        longitude=lon,
        latitude=lat,
        distance=None,
        magnitude=mag,
        sign=sign,
        sign_symbol=sign_symbol,
        sign_degree=sign_degree,
        is_variable=is_variable,
        provenance=serialize_star_provenance(data, requested_datetime=requested_datetime, jd_tt=jd_tt),
    )


def serialize_stars_bulk(results: dict, missing: list[str]) -> StarsBulkResponse:
    serialized = {}
    for key, data in results.items():
        serialized[key] = serialize_star(data)

    return StarsBulkResponse(
        dt=results.get("dt") if isinstance(results, dict) else None,  # placeholder
        results=serialized,
        missing=missing,
    )


def serialize_variable_star(star: VariableStar) -> VariableStarCatalogResponse:
    return VariableStarCatalogResponse(
        name=star.name,
        designation=star.designation,
        var_type=star.var_type,
        epoch_jd=star.epoch_jd,
        epoch_is_minimum=star.epoch_is_minimum,
        period_days=star.period_days,
        mag_max=star.mag_max,
        mag_min=star.mag_min,
        mag_min2=star.mag_min2,
        eclipse_width=star.eclipse_width,
        classical_quality=star.classical_quality,
        amplitude=star.amplitude,
        type_class=star.type_class,
        is_eclipsing=star.is_eclipsing,
        is_pulsating=star.is_pulsating,
        is_long_period=star.is_long_period,
        is_irregular=star.is_irregular,
        note=star.note,
        provenance=serialize_variable_catalog_provenance(star),
    )


def _variable_catalog_sources() -> list[str]:
    return [
        "GCVS",
        "AAVSO VSX",
        "published_linear_ephemerides",
    ]


def _variable_phase_convention(star: VariableStar | None = None) -> str:
    if star is None:
        return "phase_zero_is_primary_minimum_for_eclipsing_types_and_maximum_light_for_pulsating_or_long_period_types"
    if star.epoch_is_minimum:
        return "phase_zero_is_primary_minimum"
    return "phase_zero_is_maximum_light"


def serialize_variable_catalog_provenance(star: VariableStar) -> VariableStarCatalogProvenanceResponse:
    return VariableStarCatalogProvenanceResponse(
        catalog_source=_variable_catalog_sources(),
        phase_convention=_variable_phase_convention(star),
        var_type=star.var_type,
        epoch_jd=star.epoch_jd,
        epoch_is_minimum=star.epoch_is_minimum,
        period_days=star.period_days,
        stage_sequence=[
            "variable_star_catalog_resolution",
            "catalog_record_serialization",
        ],
    )


def serialize_variable_computation_provenance(
    *,
    requested_datetime: datetime | None = None,
    jd: float | None = None,
    requested_stars: list[str],
    returned_stars: list[str],
    eclipse_threshold: float | None = None,
    stage_sequence: list[str],
) -> VariableStarComputationProvenanceResponse:
    return VariableStarComputationProvenanceResponse(
        requested_datetime=requested_datetime.isoformat() if requested_datetime is not None else None,
        normalized_datetime_utc=(
            requested_datetime.astimezone(timezone.utc).isoformat() if requested_datetime is not None else None
        ),
        jd=jd,
        catalog_source=_variable_catalog_sources(),
        requested_stars=list(requested_stars),
        returned_stars=list(returned_stars),
        eclipse_threshold=(
            DEFAULT_VAR_STAR_POLICY.eclipse_threshold if eclipse_threshold is None else eclipse_threshold
        ),
        phase_convention=_variable_phase_convention(),
        stage_sequence=list(stage_sequence),
    )


def serialize_variable_range_provenance(
    star: VariableStar,
    jd_start: float,
    jd_end: float,
) -> VariableStarComputationProvenanceResponse:
    return VariableStarComputationProvenanceResponse(
        requested_datetime=None,
        normalized_datetime_utc=None,
        jd=None,
        catalog_source=_variable_catalog_sources(),
        requested_stars=[star.name],
        returned_stars=[star.name],
        eclipse_threshold=DEFAULT_VAR_STAR_POLICY.eclipse_threshold,
        phase_convention=_variable_phase_convention(star),
        stage_sequence=[
            "jd_range_validation",
            "variable_star_catalog_resolution",
            "extrema_range_computation",
            f"range_start_jd:{jd_start}",
            f"range_end_jd:{jd_end}",
            "variable_star_response_serialization",
        ],
    )


def serialize_variable_condition(profile: VarStarConditionProfile) -> VariableStarConditionResponse:
    return VariableStarConditionResponse(
        name=profile.name,
        designation=profile.designation,
        var_type=profile.var_type,
        type_class=profile.type_class,
        classical_quality=profile.classical_quality,
        is_malefic=profile.is_malefic,
        is_benefic=profile.is_benefic,
        amplitude=profile.amplitude,
        period_days=profile.period_days,
        is_irregular=profile.is_irregular,
        phase=profile.phase,
        magnitude=profile.magnitude,
        malefic_score=profile.malefic_score,
        benefic_score=profile.benefic_score,
        in_eclipse=profile.in_eclipse,
    )


def serialize_variable_state(
    star: VariableStar,
    profile: VarStarConditionProfile,
    next_minimum_jd: float | None,
    next_maximum_jd: float | None,
    *,
    provenance: VariableStarComputationProvenanceResponse,
) -> VariableStarStateResponse:
    return VariableStarStateResponse(
        star=serialize_variable_star(star),
        condition=serialize_variable_condition(profile),
        next_minimum_jd=next_minimum_jd,
        next_maximum_jd=next_maximum_jd,
        provenance=provenance,
    )


def serialize_variable_catalog_profile(
    profile: CatalogProfile,
    *,
    provenance: VariableStarComputationProvenanceResponse,
) -> VariableStarCatalogProfileResponse:
    return VariableStarCatalogProfileResponse(
        profiles=[serialize_variable_condition(item) for item in profile.profiles],
        star_count=profile.star_count,
        eclipsing_count=profile.eclipsing_count,
        pulsating_count=profile.pulsating_count,
        long_period_count=profile.long_period_count,
        malefic_count=profile.malefic_count,
        benefic_count=profile.benefic_count,
        neutral_count=profile.neutral_count,
        mixed_count=profile.mixed_count,
        eclipse_active_count=profile.eclipse_active_count,
        has_active_eclipses=profile.has_active_eclipses,
        provenance=provenance,
    )


def serialize_variable_pair(
    pair: StarStatePair,
    *,
    provenance: VariableStarComputationProvenanceResponse,
) -> VariableStarPairResponse:
    return VariableStarPairResponse(
        primary=serialize_variable_condition(pair.primary),
        secondary=serialize_variable_condition(pair.secondary),
        is_same_type_class=pair.is_same_type_class,
        is_same_quality=pair.is_same_quality,
        both_malefic=pair.both_malefic,
        both_in_eclipse=pair.both_in_eclipse,
        quality_conflict=pair.quality_conflict,
        provenance=provenance,
    )


def serialize_multiple_component(component: StarComponent | dict) -> MultipleStarComponentResponse:
    if isinstance(component, dict):
        return MultipleStarComponentResponse(
            label=str(component.get("label", "")),
            spectral_type=str(component.get("spectral_type", "")),
            magnitude=float(component.get("magnitude", 0.0)),
            mass_solar=float(component.get("mass_solar", 0.0)),
            note=str(component.get("note", "")),
        )
    return MultipleStarComponentResponse(
        label=component.label,
        spectral_type=component.spectral_type,
        magnitude=component.magnitude,
        mass_solar=component.mass_solar,
        note=component.note,
    )


def serialize_multiple_orbit(orbit: OrbitalElements) -> MultipleStarOrbitResponse:
    return MultipleStarOrbitResponse(
        label=orbit.label,
        period_yr=orbit.period_yr,
        epoch_jd=orbit.epoch_jd,
        ecc=orbit.ecc,
        semi_major_arcsec=orbit.semi_major_arcsec,
        incl_deg=orbit.incl_deg,
        node_deg=orbit.node_deg,
        arg_peri_deg=orbit.arg_peri_deg,
        ref_pa_deg=orbit.ref_pa_deg,
        period_uncertain=orbit.period_uncertain,
    )


def _multiple_catalog_sources() -> list[str]:
    return [
        "WDS",
        "INT4",
        "6OC",
        "Pourbaix et al. 2002",
        "Bond et al. 2017",
        "Torres et al. 2009",
        "Herbison-Evans et al. 1971",
    ]


def _multiple_orbit_model(system: MultipleStarSystem) -> str:
    if system.system_type == "visual":
        return "kepler_thiele_innes_visual_binary"
    if system.system_type in {"wide", "optical"}:
        return "fixed_reference_separation_position_angle"
    if system.system_type == "spectroscopic":
        return "spectroscopic_unresolvable"
    return "multiple_star_oracle"


def _multiple_orbital_doctrine(system: MultipleStarSystem) -> str:
    if system.system_type == "visual":
        return "Campbell elements projected with Kepler solver and Thiele-Innes constants"
    if system.system_type == "wide":
        return "reference separation and position angle for long-period visual pair"
    if system.system_type == "optical":
        return "reference separation and position angle for line-of-sight optical pair"
    if system.system_type == "spectroscopic":
        return "spectroscopic binary treated as visually unresolvable"
    return "multiple-star catalog doctrine"


def serialize_multiple_catalog_provenance(system: MultipleStarSystem) -> MultipleStarCatalogProvenanceResponse:
    primary_orbit = system.orbits[0] if system.orbits else None
    return MultipleStarCatalogProvenanceResponse(
        catalog_source=_multiple_catalog_sources(),
        system_type=system.system_type,
        orbit_model=_multiple_orbit_model(system),
        orbital_doctrine=_multiple_orbital_doctrine(system),
        primary_orbit_label=primary_orbit.label if primary_orbit is not None else None,
        primary_orbit_period_uncertain=primary_orbit.period_uncertain if primary_orbit is not None else None,
        stage_sequence=[
            "multiple_star_catalog_resolution",
            "catalog_record_serialization",
        ],
    )


def serialize_multiple_list_provenance(
    *,
    q: str | None,
    system_type: str | None,
    limit: int,
    returned_count: int,
) -> MultipleStarListProvenanceResponse:
    return MultipleStarListProvenanceResponse(
        catalog_source=_multiple_catalog_sources(),
        requested_query=q,
        requested_system_type=system_type,
        limit=limit,
        returned_count=returned_count,
        stage_sequence=[
            "multiple_star_catalog_filtering",
            "bounded_list_serialization",
        ],
    )


def serialize_multiple_state_provenance(
    system: MultipleStarSystem,
    *,
    requested_datetime: datetime,
    jd: float,
    requested_system: str,
    aperture_mm: float,
) -> MultipleStarStateProvenanceResponse:
    primary_orbit = system.orbits[0] if system.orbits else None
    return MultipleStarStateProvenanceResponse(
        requested_datetime=requested_datetime.isoformat(),
        normalized_datetime_utc=requested_datetime.astimezone(timezone.utc).isoformat(),
        jd=jd,
        catalog_source=_multiple_catalog_sources(),
        requested_system=requested_system,
        returned_system=system.name,
        system_type=system.system_type,
        orbit_model=_multiple_orbit_model(system),
        aperture_mm=aperture_mm,
        dawes_limit_arcsec=116.0 / aperture_mm,
        primary_orbit_label=primary_orbit.label if primary_orbit is not None else None,
        primary_orbit_period_uncertain=primary_orbit.period_uncertain if primary_orbit is not None else None,
        stage_sequence=[
            "datetime_validation",
            "julian_day_conversion",
            "multiple_star_catalog_resolution",
            "components_snapshot_computation",
            "dawes_resolvability_evaluation",
            "multiple_star_response_serialization",
        ],
    )


def serialize_multiple_system(system: MultipleStarSystem) -> MultipleStarSystemResponse:
    return MultipleStarSystemResponse(
        name=system.name,
        designation=system.designation,
        also_known_as=list(system.also_known_as),
        system_type=system.system_type,
        components=[serialize_multiple_component(component) for component in system.components],
        orbits=[serialize_multiple_orbit(orbit) for orbit in system.orbits],
        combined_mag=system.combined_mag,
        computed_combined_magnitude=combined_magnitude(system),
        classical_quality=system.classical_quality,
        note=system.note,
        provenance=serialize_multiple_catalog_provenance(system),
    )


def serialize_multiple_state(
    system: MultipleStarSystem,
    snapshot: dict,
    is_resolvable_at_aperture: bool,
    *,
    provenance: MultipleStarStateProvenanceResponse,
) -> MultipleStarStateResponse:
    return MultipleStarStateResponse(
        system=serialize_multiple_system(system),
        separation_arcsec=snapshot["separation_arcsec"],
        position_angle_deg=snapshot["position_angle_deg"],
        is_resolvable=is_resolvable_at_aperture,
        is_resolvable_100mm=snapshot["is_resolvable_100mm"],
        is_resolvable_200mm=snapshot["is_resolvable_200mm"],
        dominant_component=snapshot["dominant_component"],
        components={
            label: serialize_multiple_component({"label": label, **component})
            for label, component in snapshot["components"].items()
        },
        provenance=provenance,
    )

"""Serializers for stars surfaces."""

from __future__ import annotations

from moira.multiple_stars import (
    MultipleStarSystem,
    StarComponent,
    OrbitalElements,
    combined_magnitude,
)
from moira.stars import StarPosition
from moira.variable_stars import (
    CatalogProfile,
    StarStatePair,
    VariableStar,
    VarStarConditionProfile,
)
from moira.constants import sign_of

from ..models.stars import (
    MultipleStarComponentResponse,
    MultipleStarOrbitResponse,
    MultipleStarStateResponse,
    MultipleStarSystemResponse,
    StarPositionResponse,
    StarsBulkResponse,
    VariableStarCatalogProfileResponse,
    VariableStarCatalogResponse,
    VariableStarConditionResponse,
    VariableStarPairResponse,
    VariableStarStateResponse,
)


def serialize_star(data: StarPosition | dict, is_variable: bool = False) -> StarPositionResponse:
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
) -> VariableStarStateResponse:
    return VariableStarStateResponse(
        star=serialize_variable_star(star),
        condition=serialize_variable_condition(profile),
        next_minimum_jd=next_minimum_jd,
        next_maximum_jd=next_maximum_jd,
    )


def serialize_variable_catalog_profile(profile: CatalogProfile) -> VariableStarCatalogProfileResponse:
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
    )


def serialize_variable_pair(pair: StarStatePair) -> VariableStarPairResponse:
    return VariableStarPairResponse(
        primary=serialize_variable_condition(pair.primary),
        secondary=serialize_variable_condition(pair.secondary),
        is_same_type_class=pair.is_same_type_class,
        is_same_quality=pair.is_same_quality,
        both_malefic=pair.both_malefic,
        both_in_eclipse=pair.both_in_eclipse,
        quality_conflict=pair.quality_conflict,
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
    )


def serialize_multiple_state(
    system: MultipleStarSystem,
    snapshot: dict,
    is_resolvable_at_aperture: bool,
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
    )

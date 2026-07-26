"""Lossless serializers for the unified Hellenistic profile."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from moira.hellenistic import (
    HellenisticAspectProfile,
    HellenisticChartProfile,
    HellenisticDecennialSnapshot,
    HellenisticLotProfile,
    HellenisticPlanetProfile,
    HellenisticProfilePolicy,
    HellenisticZodiacalReleasingSnapshot,
)
from moira.timelords import DecennialPeriod

from ..models.dignities import (
    DignityComputationPolicyRequest,
)
from ..models.egyptian_bounds import EgyptianBoundsPolicyRequest
from ..models.hellenistic_aspects import (
    HellenisticAspectClassificationResponse,
    HellenisticDirectionTruthResponse,
    HellenisticOvercomingTruthResponse,
    HellenisticSuperiorityTruthResponse,
)
from ..models.hellenistic_profile import (
    HellenisticAspectProfileResponse,
    HellenisticChartProfileResponse,
    HellenisticDecennialPolicyRequest,
    HellenisticDecennialPeriodResponse,
    HellenisticDecennialSnapshotResponse,
    HellenisticLotProfileResponse,
    HellenisticObserverContextResponse,
    HellenisticPlanetProfileResponse,
    HellenisticPlanetaryJoyTruthResponse,
    HellenisticProfileNotEvaluableResponse,
    HellenisticProfilePolicyRequest,
    HellenisticProfileProvenanceResponse,
    HellenisticZRYearPolicyRequest,
    HellenisticZodiacalReleasingSnapshotResponse,
)
from ..models.lots import LotsComputationPolicyRequest
from .decans import serialize_decanate_position
from .dignities import (
    serialize_besieging_truth,
    serialize_essential_dignity_component_truth,
    serialize_planetary_reception,
    serialize_planetary_solar_phase_truth,
    serialize_sect_truth,
    serialize_solar_proximity_truth,
)
from .egyptian_bounds import serialize_egyptian_bound_truth
from .lots import (
    serialize_arabic_part_computation_truth,
    serialize_lot_astrological_condition_truth,
    serialize_lot_dependency_completeness,
    serialize_lot_not_evaluable,
)
from .timelords import (
    serialize_decennial_sequence_truth,
    serialize_profection_result,
    serialize_releasing_period,
)
from .triplicity import serialize_triplicity_assignment


def _transport_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            item.name: _transport_value(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            _transport_value(key): _transport_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_transport_value(item) for item in value]
    return value


def _serialize_policy(
    policy: HellenisticProfilePolicy,
) -> HellenisticProfilePolicyRequest:
    return HellenisticProfilePolicyRequest(
        dignity=DignityComputationPolicyRequest.model_validate(
            _transport_value(policy.dignity)
        ),
        lots=LotsComputationPolicyRequest.model_validate(
            _transport_value(policy.lots)
        ),
        triplicity_doctrine=policy.triplicity_doctrine,
        bounds=EgyptianBoundsPolicyRequest.model_validate(
            _transport_value(policy.bounds)
        ),
        decennials=HellenisticDecennialPolicyRequest(
            start_lord_basis=policy.decennials.start_lord_basis,
            sequence_mode=policy.decennials.sequence_mode,
            subperiod_mode=policy.decennials.subperiod_mode,
            major_months=policy.decennials.major_months,
            month_basis_days=policy.decennials.month_basis_days,
            time_basis=policy.decennials.time_basis,
            calendar_projection_basis=(
                policy.decennials.calendar_projection_basis
            ),
        ),
        zr_year=HellenisticZRYearPolicyRequest.model_validate(
            _transport_value(policy.zr_year)
        ),
        activation_orb_deg=policy.activation_orb_deg,
        leap_day_policy=policy.leap_day_policy,
        zr_lot_name=policy.zr_lot_name,
        zr_levels=policy.zr_levels,
        use_loosing_of_bond=policy.use_loosing_of_bond,
    )


def _serialize_superiority_truth(
    truth,
) -> HellenisticSuperiorityTruthResponse:
    return HellenisticSuperiorityTruthResponse(
        body1=truth.body1,
        body2=truth.body2,
        longitude1=truth.longitude1,
        longitude2=truth.longitude2,
        direction_truth=HellenisticDirectionTruthResponse(
            status=truth.direction_truth.status,
            aspect_angle_deg=truth.direction_truth.aspect_angle_deg,
            forward_arc_body1_to_body2_deg=(
                truth.direction_truth.forward_arc_body1_to_body2_deg
            ),
            direction=truth.direction_truth.direction,
            reason=truth.direction_truth.reason,
        ),
        overcoming_truth=HellenisticOvercomingTruthResponse(
            status=truth.overcoming_truth.status,
            body1_sign_index=truth.overcoming_truth.body1_sign_index,
            body2_sign_index=truth.overcoming_truth.body2_sign_index,
            body1_place_from_body2=truth.overcoming_truth.body1_place_from_body2,
            body2_place_from_body1=truth.overcoming_truth.body2_place_from_body1,
            relation=truth.overcoming_truth.relation,
            reason=truth.overcoming_truth.reason,
        ),
    )


def _serialize_planet(
    profile: HellenisticPlanetProfile,
) -> HellenisticPlanetProfileResponse:
    return HellenisticPlanetProfileResponse(
        planet=profile.planet,
        longitude=profile.longitude,
        sign=profile.sign,
        house=profile.house,
        is_retrograde=profile.is_retrograde,
        essential_components=tuple(
            serialize_essential_dignity_component_truth(component)
            for component in profile.essential_components
        ),
        sect_truth=serialize_sect_truth(profile.sect_truth),
        joy_truth=HellenisticPlanetaryJoyTruthResponse(
            status=profile.joy_truth.status,
            planet=profile.joy_truth.planet,
            actual_house=profile.joy_truth.actual_house,
            joy_house=profile.joy_truth.joy_house,
            matched=profile.joy_truth.matched,
            reason=profile.joy_truth.reason,
        ),
        solar_proximity_truth=serialize_solar_proximity_truth(
            profile.solar_proximity_truth
        ),
        planetary_solar_phase_truth=serialize_planetary_solar_phase_truth(
            profile.planetary_solar_phase_truth
        ),
        besieging_truth=serialize_besieging_truth(profile.besieging_truth),
        receptions=tuple(
            serialize_planetary_reception(reception)
            for reception in profile.receptions
        ),
        triplicity_assignment=serialize_triplicity_assignment(
            profile.triplicity_assignment
        ),
        bound_truth=serialize_egyptian_bound_truth(profile.bound_truth),
        face=serialize_decanate_position(profile.face),
    )


def _serialize_aspect(
    profile: HellenisticAspectProfile,
) -> HellenisticAspectProfileResponse:
    classification = profile.classification
    return HellenisticAspectProfileResponse(
        body1=profile.body1,
        body2=profile.body2,
        aspect=profile.aspect,
        symbol=profile.symbol,
        angle=profile.angle,
        separation=profile.separation,
        sign_degree1=profile.sign_degree1,
        sign_degree2=profile.sign_degree2,
        classification=HellenisticAspectClassificationResponse(
            domain=classification.domain.value,
            tier=classification.tier.value,
            family=classification.family.value,
        ),
        superiority_truth=_serialize_superiority_truth(
            profile.superiority_truth
        ),
    )


def _serialize_lot(
    profile: HellenisticLotProfile,
) -> HellenisticLotProfileResponse:
    return HellenisticLotProfileResponse(
        name=profile.name,
        longitude=profile.longitude,
        formula=profile.formula,
        category=profile.category,
        description=profile.description,
        computation_truth=serialize_arabic_part_computation_truth(
            profile.computation_truth
        ),
        dependency_completeness=serialize_lot_dependency_completeness(
            profile.dependency_completeness
        ),
        astrological_condition_truth=(
            serialize_lot_astrological_condition_truth(
                profile.astrological_condition_truth
            )
        ),
    )


def _serialize_decennials(
    snapshot: HellenisticDecennialSnapshot,
) -> HellenisticDecennialSnapshotResponse:
    return HellenisticDecennialSnapshotResponse(
        status=snapshot.status,
        sequence_truth=serialize_decennial_sequence_truth(
            snapshot.sequence_truth
        ),
        active_periods=tuple(
            _serialize_decennial_period(period)
            for period in snapshot.active_periods
        ),
        reason=snapshot.reason,
    )


def _serialize_decennial_period(
    period: DecennialPeriod,
) -> HellenisticDecennialPeriodResponse:
    truth = period.sequence_truth
    if truth is None:
        raise ValueError("Decennial profile period must preserve sequence truth")
    return HellenisticDecennialPeriodResponse(
        level=period.level,
        level_name=period.level_name,
        planet=period.planet,
        start_jd=period.start_jd,
        end_jd=period.end_jd,
        years=period.years,
        months=period.months,
        days=period.days,
        time_basis=period.time_basis,
        calendar_projection_basis=period.calendar_projection_basis,
        sequence_origin_jd=period.sequence_origin_jd,
        start_distribution_day=period.start_distribution_day,
        end_distribution_day=period.end_distribution_day,
        distribution_years=period.distribution_years,
        start_date=period.start_dt.isoformat(),
        end_date=period.end_dt.isoformat(),
        major_planet=period.major_planet,
        parent_planet=period.parent_planet,
        parent_level=period.parent_level,
        is_day_chart=period.is_day_chart,
        sect_light=period.sect_light,
        sequence_kind=period.sequence_kind,
        major_index=period.major_index,
        sub_index=period.sub_index,
        ancestor_planets=list(period.ancestor_planets),
        sequence_position=period.sequence_position,
        sequence_truth=serialize_decennial_sequence_truth(truth),
    )


def _serialize_zr(
    snapshot: HellenisticZodiacalReleasingSnapshot,
) -> HellenisticZodiacalReleasingSnapshotResponse:
    return HellenisticZodiacalReleasingSnapshotResponse(
        status=snapshot.status,
        lot_name=snapshot.lot_name,
        source_lot_name=snapshot.source_lot_name,
        lot_longitude=snapshot.lot_longitude,
        fortune_longitude=snapshot.fortune_longitude,
        levels=snapshot.levels,
        use_loosing_of_bond=snapshot.use_loosing_of_bond,
        active_periods=tuple(
            serialize_releasing_period(period)
            for period in snapshot.active_periods
        ),
        reason=snapshot.reason,
    )


def serialize_hellenistic_chart_profile(
    profile: HellenisticChartProfile,
) -> HellenisticChartProfileResponse:
    """Serialize every admitted receipt without adding interpretation."""

    return HellenisticChartProfileResponse(
        natal_dt=profile.natal_dt,
        current_dt=profile.current_dt,
        natal_jd=profile.natal_jd,
        current_jd=profile.current_jd,
        house_system=profile.house_system,
        asc_longitude=profile.asc_longitude,
        mc_longitude=profile.mc_longitude,
        observer=HellenisticObserverContextResponse(
            latitude=profile.observer.latitude,
            longitude=profile.observer.longitude,
            elevation_m=profile.observer.elevation_m,
            source=profile.observer.source,
        ),
        is_day_chart=profile.is_day_chart,
        sect_light=profile.sect_light,
        policy=_serialize_policy(profile.policy),
        planets=tuple(_serialize_planet(planet) for planet in profile.planets),
        aspects=tuple(_serialize_aspect(aspect) for aspect in profile.aspects),
        lots=tuple(_serialize_lot(lot) for lot in profile.lots),
        lots_not_evaluable=tuple(
            serialize_lot_not_evaluable(item)
            for item in profile.lots_not_evaluable
        ),
        profection=serialize_profection_result(profile.profection),
        decennials=_serialize_decennials(profile.decennials),
        zodiacal_releasing=_serialize_zr(profile.zodiacal_releasing),
        included_components=profile.included_components,
        excluded_components=profile.excluded_components,
        provenance=HellenisticProfileProvenanceResponse(
            method_id=profile.provenance.method_id,
            lineage=profile.provenance.lineage,
            source_refs=profile.provenance.source_refs,
            input_semantics=profile.provenance.input_semantics,
            position_frame=profile.provenance.position_frame,
            calendar_and_timescale=profile.provenance.calendar_and_timescale,
            engine_version=profile.provenance.engine_version,
            kernel_id=profile.provenance.kernel_id,
            kernel_coverage=profile.provenance.kernel_coverage,
            derivation_or_evidence=(
                profile.provenance.derivation_or_evidence
            ),
            warnings=profile.provenance.warnings,
            not_evaluable=tuple(
                HellenisticProfileNotEvaluableResponse(
                    component=item.component,
                    subject=item.subject,
                    reason=item.reason,
                )
                for item in profile.provenance.not_evaluable
            ),
        ),
    )


__all__ = ["serialize_hellenistic_chart_profile"]

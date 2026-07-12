"""Serializers for progressed Astrodynes transport vessels."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from moira.astrodynes import ASTRODYNE_PLANETS, ASTRODYNE_SIGNS
from moira.progressed_astrodynes import (
    PROGRESSED_ASTRODYNE_SOURCE_ANOMALIES,
    ProgressedDatedAspectTruth,
    ProgressedAccessoryAspectRelation,
    ProgressedCompoundInfluenceTruth,
    ProgressedMajorAspectRelation,
    ProgressedNormalHoroscope,
    ProgressedPracticalHoroscope,
    ProgressedReenforcementTruth,
    ProgressedTotalInfluenceTruth,
)
from moira.progressed_astrodynes_chart import (
    ChurchOfLightProgressedAstrodynesChart,
    ChurchOfLightProgressionGeometry,
)
from moira.obliquity import true_obliquity

from ..models.progressed_astrodynes import (
    ProgressedAstrodynesDoctrineResponse,
    ProgressedAstrodynesChartResponse,
    ProgressedChartGeometryResponse,
    ProgressedCompoundInfluenceResponse,
    ProgressedContactSearchResponse,
    ProgressedDatedAspectResponse,
    ProgressedNormalResponse,
    ProgressedPracticalResponse,
    ProgressedReenforcementResponse,
    ProgressedRelationResponse,
    ProgressedTotalInfluenceResponse,
    ProgressedVariableInfluenceResponse,
)
from ..serializers.astrodynes import serialize_astrodynes_calculation
from ..services.astrodynes import AstrodynesCalculationTruth


def _value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _value(asdict(value))
    if isinstance(value, dict):
        return {key: _value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_value(item) for item in value]
    return value


def _round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def serialize_progressed_doctrine(
    truth: dict[str, object],
) -> ProgressedAstrodynesDoctrineResponse:
    return ProgressedAstrodynesDoctrineResponse.model_validate(_value(truth))


def _terminal_house(longitude: float, cusps: tuple[float, ...]) -> int:
    for index, opening in enumerate(cusps):
        closing = cusps[(index + 1) % 12]
        distance = (longitude - opening) % 360.0
        size = (closing - opening) % 360.0
        if distance < size or distance <= 1e-12:
            return index + 1
    raise ValueError("terminal longitude does not fall in natal house figure")


def serialize_progressed_geometry(
    truth: ChurchOfLightProgressionGeometry,
) -> ProgressedChartGeometryResponse:
    def terminals(values):
        return tuple(
            {
                "terminal_id": item.terminal_id,
                "body": item.body,
                "kind": item.kind.value,
                "longitude_deg": item.longitude_deg,
                "declination_deg": item.declination_deg,
                "sign": ASTRODYNE_SIGNS[int(item.longitude_deg // 30.0)],
                "house": _terminal_house(item.longitude_deg, truth.natal_cusps),
                "house_class": item.house_class,
            }
            for item in values
        )

    time = truth.time_truth
    time_truth = {
        **asdict(time),
        "major_ephemeris_datetime": time.major_ephemeris_datetime,
        "minor_ephemeris_datetime": time.minor_ephemeris_datetime,
    }
    return ProgressedChartGeometryResponse(
        natal_dt=truth.natal_dt,
        target_dt=truth.target_dt,
        observer_lat=truth.observer_lat,
        observer_lon=truth.observer_lon,
        requested_house_system=truth.requested_house_system,
        effective_house_system=truth.effective_house_system,
        house_fallback=truth.house_fallback,
        house_fallback_reason=truth.house_fallback_reason,
        natal_cusps=truth.natal_cusps,
        time_truth=time_truth,
        natal_terminals=terminals(truth.natal_terminals),
        major_terminals=terminals(truth.major_terminals),
        minor_terminals=terminals(truth.minor_terminals),
        transit_terminals=terminals(truth.transit_terminals),
    )


def serialize_progressed_normal(
    truth: ProgressedNormalHoroscope,
) -> ProgressedNormalResponse:
    profiles = []
    for profile in truth.profiles:
        carry = profile.carry
        profiles.append(
            {
                "body": profile.body,
                "longitude_deg": profile.placement.longitude_deg,
                "sign": profile.placement.sign,
                "sign_degree": profile.placement.sign_degree,
                "house": profile.placement.house,
                "natal": {
                    "power": profile.natal.power,
                    "harmony": profile.natal.harmony,
                    "discord": profile.natal.discord,
                },
                "dignity_delta": profile.dignity_delta,
                "carry": {
                    "tier": carry.tier.value,
                    "carry_factor": carry.carry_factor,
                    "carried_power": carry.carried_power,
                    "carried_harmony": carry.carried_harmony,
                    "carried_discord": carry.carried_discord,
                    "dignity_harmony": carry.dignity_harmony,
                    "dignity_discord": carry.dignity_discord,
                    "manual_carried_power": carry.manual_carried_power,
                    "manual_total_harmony": carry.manual_total_harmony,
                    "manual_total_discord": carry.manual_total_discord,
                },
            }
        )

    def aggregate(entry):
        return {
            "name": entry.name,
            "baseline": asdict(entry.baseline),
            "occupants": entry.occupants,
            "added_power": entry.manual_added_power,
            "added_harmony": entry.manual_added_harmony,
            "added_discord": entry.manual_added_discord,
            "total_power": entry.manual_total_power,
            "total_harmony": entry.manual_total_harmony,
            "total_discord": entry.manual_total_discord,
            "net_harmony": entry.manual_net_harmony,
        }

    return ProgressedNormalResponse(
        profiles=tuple(profiles),
        signs=tuple(aggregate(item) for item in truth.signs),
        houses=tuple(aggregate(item) for item in truth.houses),
        total_sign_power=truth.total_sign_power,
        total_house_power=truth.total_house_power,
        total_sign_harmony=truth.total_sign_harmony,
        total_house_harmony=truth.total_house_harmony,
        checksums_pass=truth.checksums_pass,
    )


def serialize_progressed_dated_aspect(
    truth: ProgressedDatedAspectTruth,
) -> ProgressedDatedAspectResponse:
    return ProgressedDatedAspectResponse(
        **asdict(truth),
        net_harmony=truth.net_harmony,
    )


def serialize_progressed_relation(
    truth: ProgressedMajorAspectRelation | ProgressedAccessoryAspectRelation,
) -> ProgressedRelationResponse:
    if isinstance(truth, ProgressedMajorAspectRelation):
        direct = tuple(item.terminal_id for item in truth.direct_terminals)
        indirect = tuple(item.terminal_id for item in truth.indirect_terminals)
        harmony_truth = truth.manual_moment_harmony_truth
    else:
        direct = (
            truth.moving_terminal.terminal_id,
            truth.target_terminal.terminal_id,
        )
        indirect = (truth.indirect_target_terminal.terminal_id,)
        harmony_truth = truth.manual_moment_harmony_truth
    harmony = _manual_net = _round2(
        harmony_truth.total_harmony - harmony_truth.total_discord,
    )
    return ProgressedRelationResponse(
        relation_id=truth.relation_id,
        aspect=truth.aspect,
        tier=truth.tier.value,
        direct_terminal_ids=direct,
        indirect_terminal_ids=indirect,
        distance_arcmin=truth.distance_arcmin,
        progressed_percentage=truth.percentage_truth.progressed_percentage,
        peak_power=truth.peak_truth.peak_power,
        manual_peak_power=truth.peak_truth.manual_peak_power,
        power=truth.moment_truth.power,
        manual_power=truth.moment_truth.manual_power,
        harmony=max(harmony, 0.0),
        discord=max(-_manual_net, 0.0),
        net_harmony=harmony,
        detected=truth.detected,
        admitted=truth.admitted,
        scored=truth.scored,
    )


def serialize_progressed_reenforcement(
    truth: ProgressedReenforcementTruth,
) -> ProgressedReenforcementResponse:
    return ProgressedReenforcementResponse(
        major_relation_id=truth.major_relation_id,
        minor_relation_id=truth.minor_relation_id,
        target_terminal_id=truth.target_terminal_id,
        target_is_direct=truth.target_is_direct,
        terminal_factor=truth.terminal_factor,
        progressed_percentage=truth.progressed_percentage,
        peak_power=truth.peak_power,
        manual_peak_power=truth.manual_peak_power,
        reenforcement_power=truth.moment_truth.power,
        manual_reenforcement_power=truth.moment_truth.manual_power,
        unreenforced_power=truth.unreenforced_power,
        reenforced_power=truth.reenforced_power,
        manual_unreenforced_power=truth.manual_unreenforced_power,
        manual_reenforced_power=truth.manual_reenforced_power,
        harmony_unchanged=truth.harmony_unchanged,
        discord_unchanged=truth.discord_unchanged,
    )


def serialize_progressed_practical(
    truth: ProgressedPracticalHoroscope,
) -> ProgressedPracticalResponse:
    def aggregate(entry):
        contributions = tuple(
            {**asdict(item), "net_harmony": item.net_harmony}
            for item in entry.contributions
        )
        return {
            **{
                key: value
                for key, value in asdict(entry).items()
                if key != "contributions"
            },
            "contributions": contributions,
            "net_harmony": entry.net_harmony,
        }

    return ProgressedPracticalResponse(
        signs=tuple(aggregate(item) for item in truth.signs),
        houses=tuple(aggregate(item) for item in truth.houses),
        doctrine="church_of_light_progressed_astrodynes",
        parity_status="doctrinal_parity_with_published_anomalies",
        source_anomalies=PROGRESSED_ASTRODYNE_SOURCE_ANOMALIES,
    )


def serialize_progressed_total_influence(
    truth: ProgressedTotalInfluenceTruth,
) -> ProgressedTotalInfluenceResponse:
    return ProgressedTotalInfluenceResponse.model_validate(_value(asdict(truth)))


def serialize_progressed_compound_influence(
    truth: ProgressedCompoundInfluenceTruth,
) -> ProgressedCompoundInfluenceResponse:
    return ProgressedCompoundInfluenceResponse.model_validate(_value(asdict(truth)))


def serialize_progressed_chart(
    truth: ChurchOfLightProgressedAstrodynesChart,
) -> ProgressedAstrodynesChartResponse:
    geometry = truth.geometry
    radical = {item.body: item for item in geometry.natal_terminals}
    natal_truth = AstrodynesCalculationTruth(
        result=truth.natal,
        source_mode="chart_backed",
        dt=geometry.natal_dt,
        observer_lat=geometry.observer_lat,
        observer_lon=geometry.observer_lon,
        jd_ut=geometry.time_truth.natal_jd_ut,
        obliquity_deg=true_obliquity(geometry.time_truth.natal_jd_ut),
        planet_longitudes={
            body: radical[body].longitude_deg for body in ASTRODYNE_PLANETS
        },
        declinations={
            body: radical[body].declination_deg for body in radical
        },
        cusp_longitudes=geometry.natal_cusps,
        mc_longitude=radical["M.C."].longitude_deg,
        asc_longitude=radical["Asc."].longitude_deg,
        requested_house_system=geometry.requested_house_system,
        effective_house_system=geometry.effective_house_system,
        house_fallback=geometry.house_fallback,
        house_fallback_reason=geometry.house_fallback_reason,
        engine_entrypoint="Moira.progressed_astrodynes_chart:natal",
        planetary_frame="geocentric_apparent",
        kernel_required=True,
    )
    return ProgressedAstrodynesChartResponse(
        geometry=serialize_progressed_geometry(geometry),
        natal=serialize_astrodynes_calculation(natal_truth),
        normal=serialize_progressed_normal(truth.normal),
        major_relations=tuple(
            serialize_progressed_relation(item) for item in truth.major_relations
        ),
        minor_relations=tuple(
            serialize_progressed_relation(item) for item in truth.minor_relations
        ),
        transit_relations=tuple(
            serialize_progressed_relation(item) for item in truth.transit_relations
        ),
        reenforcements=tuple(
            serialize_progressed_reenforcement(item) for item in truth.reenforcements
        ),
        practical=serialize_progressed_practical(truth.practical),
        provenance={
            "doctrine": "church_of_light_progressed_astrodynes",
            "engine_entrypoint": "Moira.progressed_astrodynes_chart",
            "kernel_required": True,
            "planetary_frame": "geocentric_apparent",
            "major_time_key": "limiting_date_day_for_year",
            "minor_time_key": "solar_constant_27.3_day_lunar_return",
            "angle_method": "sun_mc_constant_and_natal_latitude_horizon",
            "natal_house_frame": "progressed_terminals_assigned_to_natal_houses",
        },
    )


def serialize_progressed_contact_search(truth) -> ProgressedContactSearchResponse:
    return ProgressedContactSearchResponse.model_validate(_value(asdict(truth)))


def serialize_progressed_variable_influence(
    truth,
) -> ProgressedVariableInfluenceResponse:
    return ProgressedVariableInfluenceResponse.model_validate(_value(asdict(truth)))


__all__ = [
    "serialize_progressed_compound_influence",
    "serialize_progressed_chart",
    "serialize_progressed_dated_aspect",
    "serialize_progressed_doctrine",
    "serialize_progressed_geometry",
    "serialize_progressed_normal",
    "serialize_progressed_practical",
    "serialize_progressed_reenforcement",
    "serialize_progressed_relation",
    "serialize_progressed_total_influence",
    "serialize_progressed_contact_search",
    "serialize_progressed_variable_influence",
]

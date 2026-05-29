"""Serializers for phase-8 Varshaphal vessels (P8-11, P8-13)."""

from __future__ import annotations

from moira.julian import datetime_from_jd
from moira.varshaphal import (
    MuddaDasha,
    MuddaDashaActivation,
    MuddaDashaPeriod,
    MuddaPeriodJudgement,
    MuddaPeriodResultProfile,
    MunthaConditionProfile,
    TajikaAspect,
    TajikaYoga,
    TasiraDasha,
    TasiraPeriod,
    VarshaphalChart,
    VarshaphalSaham,
    VarsheshaResult,
)

from ..models.varshaphal import (
    MuddaDashaActivationResponse,
    MuddaDashaPeriodResponse,
    MuddaDashaResponse,
    MuddaPeriodJudgementResponse,
    MuddaPeriodResultProfileResponse,
    MunthaConditionProfileResponse,
    TajikaAspectResponse,
    TajikaYogaResponse,
    TasiraDashaResponse,
    TasiraPeriodResponse,
    VarshaphalChartResponse,
    VarshaphalHouseCuspsResponse,
    VarshaphalSahamResponse,
    VarsheshaResultResponse,
)


def _iso(jd: float) -> str:
    return datetime_from_jd(jd).isoformat()


def _serialize_saham(s: VarshaphalSaham) -> VarshaphalSahamResponse:
    return VarshaphalSahamResponse(
        name=s.name, longitude=s.longitude, house=s.house, ruler=s.ruler
    )


def _serialize_muntha_profile(mp: MunthaConditionProfile) -> MunthaConditionProfileResponse:
    return MunthaConditionProfileResponse(
        muntha_longitude=mp.muntha_longitude,
        muntha_house=mp.muntha_house,
        muntha_sign=mp.muntha_sign,
        muntha_lord=mp.muntha_lord,
        muntha_lord_longitude=mp.muntha_lord_longitude,
        muntha_lord_house=mp.muntha_lord_house,
        muntha_lord_sign=mp.muntha_lord_sign,
        lord_in_kendra=mp.lord_in_kendra,
        lord_in_trikona=mp.lord_in_trikona,
        lord_in_dusthana=mp.lord_in_dusthana,
        lord_is_strong=mp.lord_is_strong,
        lord_is_weak=mp.lord_is_weak,
    )


def _serialize_varshesha(v: VarsheshaResult) -> VarsheshaResultResponse:
    return VarsheshaResultResponse(
        planet=v.planet,
        roles=list(v.roles),
        selection_basis=v.selection_basis,
        triplicity_contenders=list(v.triplicity_contenders),
    )


def _serialize_tajika_aspect(ta: TajikaAspect) -> TajikaAspectResponse:
    return TajikaAspectResponse(
        body1=ta.body1,
        body2=ta.body2,
        angle=ta.aspect.angle,
        orb=ta.aspect.orb,
        relation=ta.relation,
        relation_strength=ta.relation_strength,
        effect=ta.effect,
        is_benefic_relation=ta.is_benefic_relation,
        within_effective_orb=ta.within_effective_orb,
    )


def _serialize_tajika_yoga(ty: TajikaYoga) -> TajikaYogaResponse:
    return TajikaYogaResponse(
        name=ty.name,
        body1=ty.body1,
        body2=ty.body2,
        favorable=ty.favorable,
        doctrine=ty.doctrine,
        mediator=ty.mediator,
    )


def _serialize_mudda_period(p: MuddaDashaPeriod) -> MuddaDashaPeriodResponse:
    return MuddaDashaPeriodResponse(
        level=p.level,
        lord=p.lord,
        start_day=p.start_day,
        end_day=p.end_day,
        duration_days=p.duration_days,
        start_date=_iso(p.start_jd),
        end_date=_iso(p.end_jd),
        source_fraction=p.source_fraction,
        sub=[_serialize_mudda_period(s) for s in p.sub],
    )


def _serialize_mudda_dasha(md: MuddaDasha) -> MuddaDashaResponse:
    return MuddaDashaResponse(
        school=md.school,
        natal_nakshatra=md.natal_nakshatra,
        natal_nakshatra_index=md.natal_nakshatra_index,
        natal_nakshatra_lord=md.natal_nakshatra_lord,
        birth_elapsed_ghatis=md.birth_elapsed_ghatis,
        birth_remaining_ghatis=md.birth_remaining_ghatis,
        year_ruler=md.year_ruler,
        year_start_date=_iso(md.year_start_jd),
        year_end_date=_iso(md.year_end_jd),
        periods=[_serialize_mudda_period(p) for p in md.periods],
    )


def _serialize_tasira_period(tp: TasiraPeriod) -> TasiraPeriodResponse:
    return TasiraPeriodResponse(
        lord=tp.lord,
        aspect_angle=tp.aspect_angle,
        aspect_points=tp.aspect_points,
        nominal_days=tp.nominal_days,
        start_date=_iso(tp.start_jd),
        end_date=_iso(tp.end_jd),
    )


def _serialize_tasira_dasha(td: TasiraDasha) -> TasiraDashaResponse:
    return TasiraDashaResponse(
        year_start_date=_iso(td.year_start_jd),
        year_end_date=_iso(td.year_end_jd),
        periods=[_serialize_tasira_period(p) for p in td.periods],
    )


def serialize_varshaphal_chart(chart: VarshaphalChart) -> VarshaphalChartResponse:
    houses = chart.sidereal_houses
    ayanamsa_str = (
        chart.ayanamsa_system
        if isinstance(chart.ayanamsa_system, str)
        else "custom"
    )
    verdict = ""
    if chart.year_judgement is not None:
        verdict = chart.year_judgement.final_verdict
    return VarshaphalChartResponse(
        birth_jd=chart.birth_jd,
        return_year=chart.return_year,
        years_elapsed=chart.years_elapsed,
        jd_ut=chart.jd_ut,
        return_date=_iso(chart.jd_ut),
        ayanamsa_system=ayanamsa_str,
        sidereal_planets=dict(chart.sidereal_planets),
        sidereal_houses=VarshaphalHouseCuspsResponse(
            system=houses.system,
            cusps=list(houses.cusps),
            asc=houses.asc,
            mc=houses.mc,
            vertex=houses.vertex,
        ),
        natal_sidereal_asc=chart.natal_sidereal_asc,
        natal_sidereal_planets=dict(chart.natal_sidereal_planets),
        muntha_longitude=chart.muntha_longitude,
        muntha_house=chart.muntha_house,
        muntha_lord=chart.muntha_lord,
        muntha_sign=chart.muntha_sign,
        muntha_profile=_serialize_muntha_profile(chart.muntha_profile),
        varshesha=_serialize_varshesha(chart.varshesha),
        tajika_aspects=[_serialize_tajika_aspect(a) for a in chart.tajika_aspects],
        tajika_yogas=[_serialize_tajika_yoga(y) for y in chart.tajika_yogas],
        sahams=[_serialize_saham(s) for s in chart.sahams],
        natal_sahams=[_serialize_saham(s) for s in chart.natal_sahams],
        mudda_dasha=_serialize_mudda_dasha(chart.mudda_dasha),
        tasira_dasha=_serialize_tasira_dasha(chart.tasira_dasha),
        year_judgement_verdict=verdict,
    )


def serialize_mudda_activation(activation: MuddaDashaActivation) -> MuddaDashaActivationResponse:
    return MuddaDashaActivationResponse(
        query_date=_iso(activation.jd_ut),
        major_lord=activation.major_period.lord,
        major_start_date=_iso(activation.major_period.start_jd),
        major_end_date=_iso(activation.major_period.end_jd),
        sub_lord=activation.sub_period.lord,
        sub_start_date=_iso(activation.sub_period.start_jd),
        sub_end_date=_iso(activation.sub_period.end_jd),
    )


def serialize_tasira_active(period: TasiraPeriod) -> TasiraPeriodResponse:
    return _serialize_tasira_period(period)


def _serialize_result_profile(rp: MuddaPeriodResultProfile) -> MuddaPeriodResultProfileResponse:
    return MuddaPeriodResultProfileResponse(
        period_lord=rp.period_lord,
        governing_year_lord=rp.governing_year_lord,
        relation_to_varshesha=rp.relation_to_varshesha,
        relation_to_year_lagna_lord=rp.relation_to_year_lagna_lord,
        strength_quality=rp.strength_quality,
        manifestation=rp.manifestation,
        result_fullness=rp.result_fullness,
        doctrine=rp.doctrine,
    )


def serialize_mudda_judgement(judgement: MuddaPeriodJudgement) -> MuddaPeriodJudgementResponse:
    return MuddaPeriodJudgementResponse(
        activation=serialize_mudda_activation(judgement.activation),
        major_lord=judgement.activation.major_period.lord,
        sub_lord=judgement.activation.sub_period.lord,
        major_house=judgement.major_house,
        sub_house=judgement.sub_house,
        major_authority=judgement.major_authority,
        sub_authority=judgement.sub_authority,
        major_supportive_yoga_count=judgement.major_supportive_yoga_count,
        major_obstructive_yoga_count=judgement.major_obstructive_yoga_count,
        sub_supportive_yoga_count=judgement.sub_supportive_yoga_count,
        sub_obstructive_yoga_count=judgement.sub_obstructive_yoga_count,
        major_result=_serialize_result_profile(judgement.major_result),
        sub_result=_serialize_result_profile(judgement.sub_result),
    )


__all__ = [
    "serialize_mudda_activation",
    "serialize_mudda_judgement",
    "serialize_tasira_active",
    "serialize_varshaphal_chart",
]

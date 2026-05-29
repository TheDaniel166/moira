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
    TajikaChestaBala,
    TajikaDrigBala,
    TajikaKalaBala,
    TajikaPanchavargiStrength,
    TajikaShadbalaProfile,
    TajikaYoga,
    TasiraDasha,
    TasiraPeriod,
    VarshaphalActorJudgement,
    VarshaphalChart,
    VarshaphalJudgementProfile,
    VarshaphalSaham,
    VarshaphalSahamJudgement,
    VarshaphalSahamPriority,
    VarshaphalTopicJudgement,
    VarshaphalTopicWindow,
    VarshaphalYearJudgement,
    VarshaphalYearSummary,
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
    TajikaChestaBalaResponse,
    TajikaDrigBalaResponse,
    TajikaKalaBalaResponse,
    TajikaPanchavargiStrengthResponse,
    TajikaShadbalaProfileResponse,
    TajikaYogaResponse,
    TasiraDashaResponse,
    TasiraPeriodResponse,
    VarshaphalActorJudgementResponse,
    VarshaphalChartResponse,
    VarshaphalHouseCuspsResponse,
    VarshaphalJudgementProfileResponse,
    VarshaphalSahamJudgementResponse,
    VarshaphalSahamPriorityResponse,
    VarshaphalSahamResponse,
    VarshaphalTopicJudgementResponse,
    VarshaphalTopicWindowResponse,
    VarshaphalYearJudgementResponse,
    VarshaphalYearSummaryResponse,
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


# ---------------------------------------------------------------------------
# P8-12 serializers — thin declarative mappings only
# ---------------------------------------------------------------------------

def _serialize_panchavargi_strength(p: TajikaPanchavargiStrength) -> TajikaPanchavargiStrengthResponse:
    return TajikaPanchavargiStrengthResponse(
        planet=p.planet,
        longitude=p.longitude,
        sign=p.sign,
        domicile_lord=p.domicile_lord,
        domicile_relationship=p.domicile_relationship,
        domicile_score=p.domicile_score,
        exaltation_basis_planet=p.exaltation_basis_planet,
        exaltation_relationship=p.exaltation_relationship,
        exaltation_score=p.exaltation_score,
        hadda_lord=p.hadda_lord,
        hadda_relationship=p.hadda_relationship,
        hadda_score=p.hadda_score,
        decan_lord=p.decan_lord,
        decan_relationship=p.decan_relationship,
        decan_score=p.decan_score,
        musallaha_lord=p.musallaha_lord,
        musallaha_relationship=p.musallaha_relationship,
        musallaha_score=p.musallaha_score,
        total_score=p.total_score,
    )


def _serialize_kala_bala(k: TajikaKalaBala) -> TajikaKalaBalaResponse:
    return TajikaKalaBalaResponse(
        planet=k.planet,
        sect_strength=k.sect_strength,
        luminary_elongation_strength=k.luminary_elongation_strength,
        venus_elongation_strength=k.venus_elongation_strength,
        night_watch_strength=k.night_watch_strength,
        total_score=k.total_score,
    )


def _serialize_chesta_bala(c: TajikaChestaBala) -> TajikaChestaBalaResponse:
    return TajikaChestaBalaResponse(
        planet=c.planet,
        motion_mode_strength=c.motion_mode_strength,
        benefic_contact_strength=c.benefic_contact_strength,
        solar_synodic_strength=c.solar_synodic_strength,
        blocked_by_malefic_contact=c.blocked_by_malefic_contact,
        total_score=c.total_score,
    )


def _serialize_drig_bala(d: TajikaDrigBala) -> TajikaDrigBalaResponse:
    return TajikaDrigBalaResponse(
        planet=d.planet,
        ascendant_aspect_strength=d.ascendant_aspect_strength,
        benefic_support_strength=d.benefic_support_strength,
        blocked_by_malefic_square=d.blocked_by_malefic_square,
        total_score=d.total_score,
    )


def _serialize_shadbala_profile(s: TajikaShadbalaProfile) -> TajikaShadbalaProfileResponse:
    return TajikaShadbalaProfileResponse(
        planet=s.planet,
        panchavargi_strength=_serialize_panchavargi_strength(s.panchavargi_strength),
        directional_strength=s.directional_strength,
        temporal_strength=_serialize_kala_bala(s.temporal_strength),
        natural_strength=s.natural_strength,
        motion_strength=_serialize_chesta_bala(s.motion_strength),
        aspect_strength=_serialize_drig_bala(s.aspect_strength),
        total_score=s.total_score,
    )


def _serialize_actor_judgement(a: VarshaphalActorJudgement) -> VarshaphalActorJudgementResponse:
    return VarshaphalActorJudgementResponse(
        actor=a.actor,
        planet=a.planet,
        house=a.house,
        supportive_yoga_count=a.supportive_yoga_count,
        obstructive_yoga_count=a.obstructive_yoga_count,
        panchavargi_strength=_serialize_panchavargi_strength(a.panchavargi_strength),
        shadbala=_serialize_shadbala_profile(a.shadbala),
        authority_score=a.authority_score,
        authority=a.authority,
    )


def _serialize_saham_judgement(sj: VarshaphalSahamJudgement) -> VarshaphalSahamJudgementResponse:
    return VarshaphalSahamJudgementResponse(
        saham_name=sj.saham_name,
        house=sj.house,
        ruler=sj.ruler,
        ruler_house=sj.ruler_house,
        ruler_strength=_serialize_shadbala_profile(sj.ruler_strength),
        relevance_score=sj.relevance_score,
        authority=sj.authority,
    )


def _serialize_saham_priority(sp: VarshaphalSahamPriority) -> VarshaphalSahamPriorityResponse:
    return VarshaphalSahamPriorityResponse(
        saham_name=sp.saham_name,
        annual_judgement=_serialize_saham_judgement(sp.annual_judgement),
        natal_judgement=_serialize_saham_judgement(sp.natal_judgement),
        priority=sp.priority,
        is_considered=sp.is_considered,
        doctrine=sp.doctrine,
    )


def serialize_varshaphal_judgement_profile(profile: VarshaphalJudgementProfile) -> VarshaphalJudgementProfileResponse:
    """Serialize the core annual judgement scaffold (P8-12)."""
    return VarshaphalJudgementProfileResponse(
        varshesha=_serialize_varshesha(profile.varshesha),
        supportive_yogas=list(profile.supportive_yogas),
        obstructive_yogas=list(profile.obstructive_yogas),
        varshesha_house=profile.varshesha_house,
        varshesha_dignity=profile.varshesha_dignity.name if hasattr(profile.varshesha_dignity, "name") else str(profile.varshesha_dignity),
        varshesha_strength=_serialize_panchavargi_strength(profile.varshesha_strength),
        varshesha_shadbala=_serialize_shadbala_profile(profile.varshesha_shadbala),
        muntha_lord_shadbala=_serialize_shadbala_profile(profile.muntha_lord_shadbala),
        year_lagna_lord=profile.year_lagna_lord,
        year_lagna_lord_strong=profile.year_lagna_lord_strong,
        actor_rankings=[_serialize_actor_judgement(a) for a in profile.actor_rankings],
        key_saham_rankings=[_serialize_saham_judgement(sj) for sj in profile.key_saham_rankings],
        strongest_testimonies=list(profile.strongest_testimonies),
        yearly_strength_balance=profile.yearly_strength_balance,
        ascendant_authority_indication=profile.ascendant_authority_indication,
    )


def serialize_varshaphal_year_judgement(judgement: VarshaphalYearJudgement) -> VarshaphalYearJudgementResponse:
    """Serialize the full consolidated annual verdict (P8-12)."""
    return VarshaphalYearJudgementResponse(
        profile=serialize_varshaphal_judgement_profile(judgement.profile),
        dominant_governor=_serialize_actor_judgement(judgement.dominant_governor) if judgement.dominant_governor else None,
        supporting_governors=[_serialize_actor_judgement(g) for g in judgement.supporting_governors],
        strained_governors=[_serialize_actor_judgement(g) for g in judgement.strained_governors],
        topics=[_serialize_topic_judgement(t) for t in judgement.topics],
        foreground_topics=[_serialize_topic_judgement(t) for t in judgement.foreground_topics],
        obstructed_topics=[_serialize_topic_judgement(t) for t in judgement.obstructed_topics],
        background_topics=[_serialize_topic_judgement(t) for t in judgement.background_topics],
        prioritized_sahams=[_serialize_saham_priority(p) for p in judgement.prioritized_sahams],
        disregarded_sahams=[_serialize_saham_priority(p) for p in judgement.disregarded_sahams],
        key_sahams=[_serialize_saham_judgement(sj) for sj in judgement.key_sahams],
        supportive_yogas=list(judgement.supportive_yogas),
        obstructive_yogas=list(judgement.obstructive_yogas),
        decisive_testimonies=list(judgement.decisive_testimonies),
        final_verdict=judgement.final_verdict,
        conflict_resolution=judgement.conflict_resolution,
        verdict_basis=list(judgement.verdict_basis),
    )


def _serialize_topic_judgement(tj: VarshaphalTopicJudgement) -> VarshaphalTopicJudgementResponse:
    return VarshaphalTopicJudgementResponse(
        topic=tj.topic,
        saham_name=tj.saham_name,
        polarity=tj.polarity,
        house_numbers=list(tj.house_numbers),
        house_rulers=list(tj.house_rulers),
        supportive_relation_to_varshesha=tj.supportive_relation_to_varshesha,
        obstructive_relation_to_varshesha=tj.obstructive_relation_to_varshesha,
        timed_activation=tj.timed_activation,
        emphasis_score=tj.emphasis_score,
        judgement=tj.judgement,
        basis=list(tj.basis),
    )


def serialize_varshaphal_topic_judgements(topics: tuple[VarshaphalTopicJudgement, ...] | list[VarshaphalTopicJudgement]) -> list[VarshaphalTopicJudgementResponse]:
    """Serialize topic judgement list (P8-12)."""
    return [_serialize_topic_judgement(t) for t in topics]


def serialize_varshaphal_topic_windows(windows: tuple[VarshaphalTopicWindow, ...] | list[VarshaphalTopicWindow]) -> list[VarshaphalTopicWindowResponse]:
    """Serialize timed topic activation windows (P8-12)."""
    return [
        VarshaphalTopicWindowResponse(
            topic=w.topic,
            start_jd=w.start_jd,
            end_jd=w.end_jd,
            source=w.source,
            major_lord=w.major_lord,
            sub_lord=w.sub_lord,
            activation_kind=w.activation_kind,
            basis=list(w.basis),
        )
        for w in windows
    ]


def serialize_varshaphal_year_summary(summary: VarshaphalYearSummary) -> VarshaphalYearSummaryResponse:
    """Serialize the structured annual summary (P8-12)."""
    return VarshaphalYearSummaryResponse(
        yearly_tone=summary.yearly_tone,
        dominant_governor=summary.dominant_governor,
        foreground_topics=list(summary.foreground_topics),
        obstructed_topics=list(summary.obstructed_topics),
        background_topics=list(summary.background_topics),
        timed_highlights=list(summary.timed_highlights),
        strongest_testimonies=list(summary.strongest_testimonies),
        narrative_basis=list(summary.narrative_basis),
    )


__all__ = [
    "serialize_mudda_activation",
    "serialize_mudda_judgement",
    "serialize_tasira_active",
    "serialize_varshaphal_chart",
    # P8-12
    "serialize_varshaphal_judgement_profile",
    "serialize_varshaphal_topic_judgements",
    "serialize_varshaphal_topic_windows",
    "serialize_varshaphal_year_judgement",
    "serialize_varshaphal_year_summary",
]

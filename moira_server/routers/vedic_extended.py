"""Vedic Phase-2 deepening routes: upagrahas, avasthas, Jaimini extended."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira
from moira.julian import jd_from_datetime, utc_to_ut1

from ..dependencies import get_engine
from ..models.sayanadi import AvasthaBirthRequest, SayanadiRequest, SayanadiResponse
from ..serializers.avasthas import serialize_avastha_birth, serialize_avastha_chart
from ..services.avasthas import compute_avastha_birth
from ..models.vedic_extended import (
    ArgalaHouseResponse,
    ArgalaRequest,
    ArgalaResponse,
    ArudhaPadaResponse,
    ArudhaRequest,
    ArudhaResponse,
    AvasthaChartResponse,
    AvasthaBirthResponse,
    AvasthaRequest,
    CharaDashaPeriodResponse,
    CharaDashaRequest,
    CharaDashaResponse,
    CharaDashaComputationResponse,
    KalavelaRequest,
    KalavelaResponse,
    KalavelaUpagrahaResponse,
    KarakamsaRequest,
    KarakamsaResponse,
    SunBasedUpagrahasRequest,
    SunBasedUpagrahasResponse,
)


upagrahas_router = APIRouter(prefix="/v1/upagrahas", tags=["upagrahas"])
avasthas_router = APIRouter(prefix="/v1/avasthas", tags=["avasthas"])
jaimini_extended_router = APIRouter(
    prefix="/v1/jaimini/extended", tags=["jaimini"],
)


@upagrahas_router.post("/sun-based", response_model=SunBasedUpagrahasResponse)
def sun_based_upagrahas_route(
    request: SunBasedUpagrahasRequest,
) -> SunBasedUpagrahasResponse:
    """The five Sun-derived upagrahas (BPHS 3.61-64), with the verse's own
    self-check (Upaketu + 30 deg = Sun) enforced as an invariant."""
    from moira.upagrahas import sun_based_upagrahas

    u = sun_based_upagrahas(request.sun_sidereal_lon)
    return SunBasedUpagrahasResponse(
        sun_longitude=u.sun_longitude,
        dhuma=u.dhuma,
        vyatipata=u.vyatipata,
        parivesha=u.parivesha,
        indrachapa=u.indrachapa,
        upaketu=u.upaketu,
    )


@upagrahas_router.post("/kalavelas", response_model=KalavelaResponse)
def kalavelas_route(
    request: KalavelaRequest,
    engine: Moira = Depends(get_engine),
) -> KalavelaResponse:
    """Gulika, Kala, Mrityu, Ardhaprahara, Yamaghantaka, and Mandi
    (BPHS 3.66-70): eight-fold day/night division, weekday lord tables,
    ascendant materialization; portion-point / Mandi / lord-sequence
    lineage variants as explicit policy."""
    from moira.facade import use_reader_override
    from moira.upagrahas import UpagrahaPolicy, kalavela_upagrahas

    # rise_set.find_phenomena resolves the reader from the active context,
    # so the engine's reader is installed for the duration of the call.
    # The engine currently accepts one JD for both astronomical reduction and
    # its civil weekday/day-arc selection.  UT1 is required for the former;
    # the returned civil fields remain engine-owned and are not rewritten here.
    # A strict UTC-civil/UT1-astronomy split requires an engine policy surface.
    jd_ut = utc_to_ut1(jd_from_datetime(request.dt))
    with use_reader_override(engine._reader_obj):
        result = kalavela_upagrahas(
            jd_ut,
            request.latitude,
            request.longitude,
            ayanamsa_system=request.ayanamsa_system,
            policy=UpagrahaPolicy(
                portion_point=request.portion_point,
                mandi_mode=request.mandi_mode,
                lord_sequence=request.lord_sequence,
            ),
            reader=engine._reader_obj,
        )
    return KalavelaResponse(
        is_day_birth=result.is_day_birth,
        weekday_index=result.weekday_index,
        arc_start_jd=result.arc_start_jd,
        arc_end_jd=result.arc_end_jd,
        ayanamsa_system=result.ayanamsa_system,
        upagrahas={
            name: KalavelaUpagrahaResponse(
                name=up.name,
                portion_planet=up.portion_planet,
                part_index=up.part_index,
                defining_jd=up.defining_jd,
                sidereal_longitude=up.sidereal_longitude,
                tropical_longitude=up.tropical_longitude,
            )
            for name, up in result.upagrahas.items()
        },
    )


@avasthas_router.post("/evaluate", response_model=AvasthaChartResponse)
def avasthas_route(request: AvasthaRequest) -> AvasthaChartResponse:
    """Four classical avastha families and optional complete Sayanadi context."""
    from moira.avasthas import AvasthaPolicy, evaluate_avasthas

    result = evaluate_avasthas(
        request.sidereal_longitudes, request.lagna_sidereal_lon,
        AvasthaPolicy(deeptadi_source=request.deeptadi_source,
                      relationship_scheme=request.relationship_scheme,
                      vriddha_fraction=request.vriddha_fraction),
        node_longitudes=request.node_longitudes,
        sayanadi_context=request.sayanadi_context.to_engine() if request.sayanadi_context is not None else None,
    )
    return serialize_avastha_chart(result)


@avasthas_router.post("/sayanadi", response_model=SayanadiResponse)
def sayanadi_route(request: SayanadiRequest) -> SayanadiResponse:
    """One of nine source-defined subjects, supplied positions and explicit clock/name."""
    from moira.avasthas import sayanadi_avastha
    result = sayanadi_avastha(request.planet, request.sidereal_longitudes,
                              request.lagna_sidereal_lon, context=request.context.to_engine())
    return SayanadiResponse.model_validate(result)


@avasthas_router.post("/from-datetime", response_model=AvasthaBirthResponse)
def avastha_birth_route(request: AvasthaBirthRequest, engine: Moira = Depends(get_engine)) -> AvasthaBirthResponse:
    """Reader-bound birth chart, previous-sunrise brackets and ghati availability."""
    return serialize_avastha_birth(compute_avastha_birth(engine, request))


@jaimini_extended_router.post("/arudhas", response_model=ArudhaResponse)
def arudhas_route(request: ArudhaRequest) -> ArudhaResponse:
    """Arudha padas A1-A12 (AL/UL) per JUS 1.1.30-32, with the
    Rath/JHora exception and lordship lineages as explicit policy."""
    from moira.jaimini_extended import JaiminiExtendedPolicy, arudha_padas

    result = arudha_padas(
        request.sidereal_longitudes,
        request.lagna_sidereal_lon,
        JaiminiExtendedPolicy(
            arudha_exception=request.arudha_exception,
            arudha_lords=request.arudha_lords,
        ),
        node_longitudes=request.node_longitudes,
    )
    return ArudhaResponse(
        lagna_sign=result.lagna_sign,
        padas={
            h: ArudhaPadaResponse(
                house=p.house, label=p.label, house_sign=p.house_sign,
                lord=p.lord, lord_sign=p.lord_sign,
                computed_sign=p.computed_sign, pada_sign=p.pada_sign,
                exception_applied=p.exception_applied,
            )
            for h, p in result.padas.items()
        },
        arudha_lagna_sign=result.arudha_lagna_sign,
        upapada_lagna_sign=result.upapada_lagna_sign,
        lineage=result.lineage,
    )


@jaimini_extended_router.post("/argala", response_model=ArgalaResponse)
def argala_route(request: ArgalaRequest) -> ArgalaResponse:
    """Argala/virodha for all twelve houses (JUS 1.1.5-10, Rath/PVR
    reading), including the Ketu reversal and the malefic-third rule."""
    from moira.jaimini_extended import argala

    result = argala(
        request.sidereal_longitudes,
        request.lagna_sidereal_lon,
        node_longitudes=request.node_longitudes,
    )
    return ArgalaResponse(
        lagna_sign=result.lagna_sign,
        houses={
            h: ArgalaHouseResponse(
                reference_sign=a.reference_sign,
                reversed_by_ketu=a.reversed_by_ketu,
                argalas=a.argalas,
                obstructors=a.obstructors,
                unobstructed=a.unobstructed,
                malefic_third_argala=a.malefic_third_argala,
            )
            for h, a in result.houses.items()
        },
        lineage=result.lineage,
    )


@jaimini_extended_router.post("/karakamsa", response_model=KarakamsaResponse)
def karakamsa_route(request: KarakamsaRequest) -> KarakamsaResponse:
    """The Atmakaraka's navamsa sign with BOTH lineage readings named
    (Rath/PVR D9 svamsa school vs K.N. Rao D1 projection) — never
    collapsed."""
    from moira.jaimini_extended import karakamsa

    result = karakamsa(
        request.sidereal_longitudes,
        request.lagna_sidereal_lon,
        scheme=request.scheme,
    )
    return KarakamsaResponse(
        atmakaraka=result.atmakaraka,
        karakamsa_sign=result.karakamsa_sign,
        d9_reading=result.d9_reading,
        d1_reading=result.d1_reading,
        svamsa_sign=result.svamsa_sign,
    )


@jaimini_extended_router.post("/chara-dasha", response_model=CharaDashaResponse)
def chara_dasha_route(request: CharaDashaRequest) -> CharaDashaResponse:
    """Bounded one/two-cycle Chara Dasha in the existing Moira formulation,
    with ninth-from-lagna direction, count-to-lord years with no
    exaltation adjustment, antardashas with the dasha sign last."""
    from moira.jaimini_extended import chara_dasha

    result = chara_dasha(
        request.sidereal_longitudes,
        request.lagna_sidereal_lon,
        request.birth_jd,
        node_longitudes=request.node_longitudes,
        cycles=request.cycles,
    )
    return CharaDashaResponse(
        lagna_sign=result.lagna_sign,
        direction=result.direction,
        birth_jd=result.birth_jd,
        periods=tuple(
            CharaDashaPeriodResponse(
                sign=p.sign, years=p.years,
                start_jd=p.start_jd, end_jd=p.end_jd,
                lord=p.lord, lord_note=p.lord_note,
                antardasha_signs=p.antardasha_signs,
                antardasha_starts=p.antardasha_starts,
            )
            for p in result.periods
        ),
        lineage=result.lineage,
        period_count=result.period_count,
        computation=CharaDashaComputationResponse(
            **{name: getattr(result.computation, name)
               for name in CharaDashaComputationResponse.model_fields}
        ),
    )


__all__ = [
    "avasthas_router",
    "jaimini_extended_router",
    "upagrahas_router",
]

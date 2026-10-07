"""Service helpers for Phase-9 Varga routes (P9-11)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from moira import Moira
from moira.varga import (
    D60Method,
    VargaPoint,
    akshavedamsha,
    ashtamsha,
    calculate_varga,
    d60_sign,
    chaturthamsha,
    chaturvimshamsha,
    dashamansa,
    dwadashamsa,
    hora,
    khavedamsha,
    navamsa,
    saptamsa,
    saptavimshamsha,
    shashthamsha,
    shashtiamsha,
    shodashamsha,
    trimshamsa,
    vimshamsha,
)

from ..models.varga import (
    VargaChartNamedRequest,
    VargaChartShodashvargaBatchRequest,
    VargaChartShodashvargaRequest,
    VargaGenericRequest,
    VargaNamedBatchRequest,
    VargaNamedRequest,
    VargaShodashvargaBatchRequest,
    VargaShodashvargaRequest,
)
from .sidereal_context import (
    SiderealChartContext,
    SiderealChartRequirements,
    derive_sidereal_chart_context,
)


VARGA_FUNCTIONS: dict[str, Callable[[float], VargaPoint]] = {
    "hora": hora,
    "chaturthamsha": chaturthamsha,
    "shashthamsha": shashthamsha,
    "saptamsa": saptamsa,
    "ashtamsha": ashtamsha,
    "navamsa": navamsa,
    "dashamansa": dashamansa,
    "dwadashamsa": dwadashamsa,
    "shodashamsha": shodashamsha,
    "vimshamsha": vimshamsha,
    "chaturvimshamsha": chaturvimshamsha,
    "saptavimshamsha": saptavimshamsha,
    "trimshamsa": trimshamsa,
    "khavedamsha": khavedamsha,
    "akshavedamsha": akshavedamsha,
    "shashtiamsha": shashtiamsha,
}


@dataclass(frozen=True, slots=True)
class VargaChartNamedResult:
    context: SiderealChartContext
    body: str
    varga: str
    result: VargaPoint


@dataclass(frozen=True, slots=True)
class VargaChartShodashvargaResult:
    context: SiderealChartContext
    body: str
    results: dict[str, VargaPoint]


@dataclass(frozen=True, slots=True)
class VargaChartShodashvargaBatchResult:
    context: SiderealChartContext
    results: dict[str, dict[str, VargaPoint]]


def compute_varga_generic(request: VargaGenericRequest) -> VargaPoint:
    return calculate_varga(
        request.sidereal_longitude,
        request.divisor,
        request.name or "",
    )


def compute_varga_named(request: VargaNamedRequest) -> VargaPoint:
    return _named_point(request.varga, request.sidereal_longitude, request.d60_method)


def _named_point(selector: str, longitude: float, method: D60Method) -> VargaPoint:
    function = VARGA_FUNCTIONS[selector]
    if method is not D60Method.HARMONIC:
        # Compose source-profile groups from one normalization convention;
        # otherwise another division can round a tiny negative input to 360.
        longitude = d60_sign(longitude, method=method).longitude
    if selector == "shashtiamsha":
        return function(longitude, d60_method=method)
    return function(longitude)


def compute_varga_shodashvarga(
    request: VargaShodashvargaRequest,
) -> dict[str, VargaPoint]:
    return {
        selector: _named_point(selector, request.sidereal_longitude, request.d60_method)
        for selector in VARGA_FUNCTIONS
    }


def compute_varga_named_batch(
    request: VargaNamedBatchRequest,
) -> dict[str, VargaPoint]:
    return {
        key: _named_point(request.varga, longitude, request.d60_method)
        for key, longitude in request.longitudes.items()
    }


def compute_varga_shodashvarga_batch(
    request: VargaShodashvargaBatchRequest,
) -> dict[str, dict[str, VargaPoint]]:
    return {
        key: {
            selector: _named_point(selector, longitude, request.d60_method)
            for selector in VARGA_FUNCTIONS
        }
        for key, longitude in request.longitudes.items()
    }


def compute_varga_chart_named(
    engine: Moira,
    request: VargaChartNamedRequest,
) -> VargaChartNamedResult:
    context = _derive_varga_context(engine, request, (request.body,))
    return VargaChartNamedResult(
        context=context,
        body=request.body,
        varga=request.varga,
        result=_named_point(request.varga, context.sidereal_longitudes[request.body], request.d60_method),
    )


def compute_varga_chart_shodashvarga(
    engine: Moira,
    request: VargaChartShodashvargaRequest,
) -> VargaChartShodashvargaResult:
    context = _derive_varga_context(engine, request, (request.body,))
    return VargaChartShodashvargaResult(
        context=context,
        body=request.body,
        results={
            selector: _named_point(selector, context.sidereal_longitudes[request.body], request.d60_method)
            for selector in VARGA_FUNCTIONS
        },
    )


def compute_varga_chart_shodashvarga_batch(
    engine: Moira,
    request: VargaChartShodashvargaBatchRequest,
) -> VargaChartShodashvargaBatchResult:
    bodies = tuple(request.bodies)
    context = _derive_varga_context(engine, request, bodies)
    return VargaChartShodashvargaBatchResult(
        context=context,
        results={
            body: {
                selector: _named_point(selector, context.sidereal_longitudes[body], request.d60_method)
                for selector in VARGA_FUNCTIONS
            }
            for body in bodies
        },
    )


def _derive_varga_context(
    engine: Moira,
    request,
    required_bodies: tuple[str, ...],
) -> SiderealChartContext:
    return derive_sidereal_chart_context(
        engine,
        request,
        SiderealChartRequirements(required_bodies=required_bodies),
    )


def compute_vimshopaka(request):
    """Vimshopaka Bala for all seven planets + vargottama flags."""
    from moira.varga import vimshopaka_all, vargottama_planets

    from ..models.varga import (
        VimshopakaBalaResponse,
        VimshopakaChartResponse,
        VimshopakaVargaEntryResponse,
    )

    longitudes = request.sidereal_longitudes
    if request.d60_method is not D60Method.HARMONIC:
        longitudes = {body: d60_sign(lon, method=request.d60_method).longitude
                      for body, lon in longitudes.items()}
    results = vimshopaka_all(longitudes, request.group, d60_method=request.d60_method)
    return VimshopakaChartResponse(
        group=request.group,
        planets={
            planet: VimshopakaBalaResponse(
                planet=vb.planet,
                group=vb.group,
                entries=tuple(
                    VimshopakaVargaEntryResponse(
                        division=e.division,
                        varga_sign_index=e.varga_sign_index,
                        lord=e.lord,
                        dignity=e.dignity,
                        vishva=e.vishva,
                        weight=e.weight,
                        points=e.points,
                    )
                    for e in vb.entries
                ),
                total=vb.total,
                d60_method=vb.d60_method,
                d60_source_references=vb.d60_source_references,
            )
            for planet, vb in results.items()
        },
        vargottama=tuple(sorted(vargottama_planets(longitudes))),
    )


__all__ = [
    "VARGA_FUNCTIONS",
    "VargaChartNamedResult",
    "VargaChartShodashvargaBatchResult",
    "VargaChartShodashvargaResult",
    "compute_varga_chart_named",
    "compute_varga_chart_shodashvarga",
    "compute_varga_chart_shodashvarga_batch",
    "compute_varga_generic",
    "compute_varga_named",
    "compute_varga_named_batch",
    "compute_varga_shodashvarga",
    "compute_varga_shodashvarga_batch",
    "compute_vimshopaka",
]

"""Service helpers for Phase-9 Varga routes (P9-11)."""

from __future__ import annotations

from collections.abc import Callable

from moira.varga import (
    VargaPoint,
    akshavedamsha,
    ashtamsha,
    calculate_varga,
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
    VargaGenericRequest,
    VargaNamedBatchRequest,
    VargaNamedRequest,
    VargaShodashvargaBatchRequest,
    VargaShodashvargaRequest,
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


def compute_varga_generic(request: VargaGenericRequest) -> VargaPoint:
    return calculate_varga(
        request.sidereal_longitude,
        request.divisor,
        request.name or "",
    )


def compute_varga_named(request: VargaNamedRequest) -> VargaPoint:
    return VARGA_FUNCTIONS[request.varga](request.sidereal_longitude)


def compute_varga_shodashvarga(
    request: VargaShodashvargaRequest,
) -> dict[str, VargaPoint]:
    return {
        selector: function(request.sidereal_longitude)
        for selector, function in VARGA_FUNCTIONS.items()
    }


def compute_varga_named_batch(
    request: VargaNamedBatchRequest,
) -> dict[str, VargaPoint]:
    function = VARGA_FUNCTIONS[request.varga]
    return {
        key: function(longitude)
        for key, longitude in request.longitudes.items()
    }


def compute_varga_shodashvarga_batch(
    request: VargaShodashvargaBatchRequest,
) -> dict[str, dict[str, VargaPoint]]:
    return {
        key: {
            selector: function(longitude)
            for selector, function in VARGA_FUNCTIONS.items()
        }
        for key, longitude in request.longitudes.items()
    }


__all__ = [
    "VARGA_FUNCTIONS",
    "compute_varga_generic",
    "compute_varga_named",
    "compute_varga_named_batch",
    "compute_varga_shodashvarga",
    "compute_varga_shodashvarga_batch",
]

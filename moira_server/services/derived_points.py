"""Transport-only delegation to the owning derived-point engine module."""

from __future__ import annotations

from moira import Moira
from moira.derived_points import (
    baker_vulcan_at, baker_vulcan_from_longitudes, derived_point_catalog,
    mean_priapus, orbital_second_focus, osculating_priapus,
)
from moira.spk_reader import KernelReader, MissingEphemerisKernelError

from ..models.derived_points import (
    BakerLongitudesRequest, BakerVulcanResponse, DerivedPointCatalogResponse,
    DerivedPointEpochRequest, MeanPriapusRequest, PriapusResponse,
    SecondFocusRequest, SecondFocusResponse,
)


def list_derived_points() -> DerivedPointCatalogResponse:
    points = derived_point_catalog()
    return DerivedPointCatalogResponse(points=list(points), count=len(points))


def _engine_reader(engine: Moira) -> KernelReader:
    """Require instance ownership; never turn an absent reader into a global fallback."""
    reader = engine._reader
    if reader is None:
        raise MissingEphemerisKernelError("No planetary kernel is available on this engine instance.")
    return reader


def compute_baker_longitudes(request: BakerLongitudesRequest) -> BakerVulcanResponse:
    return BakerVulcanResponse.model_validate(baker_vulcan_from_longitudes(
        request.sun_longitude, request.mercury_longitude,
    ))


def compute_baker_vulcan(
    engine: Moira, request: DerivedPointEpochRequest,
) -> BakerVulcanResponse:
    return BakerVulcanResponse.model_validate(baker_vulcan_at(
        request.jd_ut, reader=_engine_reader(engine),
    ))


def compute_mean_priapus(request: MeanPriapusRequest) -> PriapusResponse:
    return PriapusResponse.model_validate(mean_priapus(
        request.jd_ut, nutation=request.nutation,
    ))


def compute_osculating_priapus(
    engine: Moira, request: DerivedPointEpochRequest,
) -> PriapusResponse:
    return PriapusResponse.model_validate(osculating_priapus(
        request.jd_ut, reader=_engine_reader(engine),
    ))


def compute_second_focus(
    engine: Moira, request: SecondFocusRequest,
) -> SecondFocusResponse:
    return SecondFocusResponse.model_validate(orbital_second_focus(
        request.body, request.jd_ut, center=request.center, frame=request.frame,
        reader=_engine_reader(engine),
    ))

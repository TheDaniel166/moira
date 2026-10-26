"""Transport-only assembly of named source-policy hypothetical requests."""

from __future__ import annotations

from moira import Moira
from moira.hypothetical import (
    ArtaFourPoints, ArtaOsculatingSet, HistoricalRealization, HypotheticalGeometry,
    LongitudeConvention, abramov_proserpina_at, adams_1846_orbit, arta_four_points,
    arta_osculating_set_at, harrington_1988_orbit, hypothetical_orbit_at,
    koch_waldemath_orbit, leverrier_1846_orbit, selena_seven_year_at,
    weston_stahl_vulcan_orbit,
    PlanetNineScenario, fienga_2016_planet_nine_scenario,
)

from ..models.hypothetical import (
    AdamsRequest, ArtaInputsRequest, ArtaOsculatingRequest, HarringtonRequest,
    HypotheticalOrbitRequest, ProserpinaRequest, SelenaRequest, WaldemathRequest,
    WestonRequest, LeverrierRequest,
    PlanetNineScenarioRequest,
)
from .derived_points import _engine_reader


def compute_arta_inputs(request: ArtaInputsRequest) -> ArtaFourPoints:
    return arta_four_points(**request.model_dump())


def compute_arta_osculating(engine: Moira, request: ArtaOsculatingRequest) -> ArtaOsculatingSet:
    return arta_osculating_set_at(request.jd_ut, frame=request.frame, reader=_engine_reader(engine))


def compute_selena(request: SelenaRequest) -> LongitudeConvention:
    return selena_seven_year_at(**request.model_dump())


def compute_proserpina(request: ProserpinaRequest) -> LongitudeConvention:
    return abramov_proserpina_at(**request.model_dump())


def compute_planet_nine_scenario(request: PlanetNineScenarioRequest) -> PlanetNineScenario:
    return fienga_2016_planet_nine_scenario(**request.model_dump())


def compute_hypothetical_orbit(request: HypotheticalOrbitRequest) -> HypotheticalGeometry:
    if isinstance(request, WaldemathRequest):
        orbit = koch_waldemath_orbit(
            source_equinox_jd_tt=request.source_equinox_jd_tt,
            berlin_local_minus_ut1_hours=request.berlin_local_minus_ut1_hours,
        )
    elif isinstance(request, WestonRequest):
        orbit = weston_stahl_vulcan_orbit(
            source_equinox_jd_tt=request.source_equinox_jd_tt, year_days=request.year_days,
        )
    else:
        policy = HistoricalRealization(**request.policy.model_dump())
        if isinstance(request, HarringtonRequest):
            orbit = harrington_1988_orbit(policy)
        elif isinstance(request, AdamsRequest):
            orbit = adams_1846_orbit(policy, uranus_semimajor_axis_au=request.uranus_semimajor_axis_au,
                                    uranus_sidereal_period_days=request.uranus_sidereal_period_days)
        elif isinstance(request, LeverrierRequest):
            orbit = leverrier_1846_orbit(policy)
        else:
            raise ValueError("Unsupported hypothetical orbit model")
    return hypothetical_orbit_at(orbit, request.epoch_jd, frame=request.frame)

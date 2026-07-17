"""Service helpers for the Sade Sati route family."""

from __future__ import annotations

from moira import Moira
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.sade_sati import sade_sati_status, sade_sati_windows

from ..models.sade_sati import (
    SadeSatiStatusRequest,
    SadeSatiStatusResponse,
    SadeSatiWindowResponse,
    SadeSatiWindowsRequest,
    SadeSatiWindowsResponse,
)


def compute_sade_sati_status(request: SadeSatiStatusRequest) -> SadeSatiStatusResponse:
    status = sade_sati_status(
        request.natal_moon_sidereal_lon,
        request.saturn_sidereal_lon,
    )
    return SadeSatiStatusResponse(
        janma_rashi_index=status.janma_rashi_index,
        saturn_rashi_index=status.saturn_rashi_index,
        house_from_moon=status.house_from_moon,
        in_sade_sati=status.in_sade_sati,
        phase=status.phase,
        is_ashtama_shani=status.is_ashtama_shani,
        is_kantaka_shani=status.is_kantaka_shani,
    )


def compute_sade_sati_windows(
    engine: Moira,
    request: SadeSatiWindowsRequest,
) -> SadeSatiWindowsResponse:
    start_jd = utc_to_ut1(jd_from_datetime(request.start_dt))
    end_jd = utc_to_ut1(jd_from_datetime(request.end_dt))
    # The engine's reader context wraps public method calls; here we pass the
    # reader explicitly since sade_sati_windows is module-level.
    result = sade_sati_windows(
        request.natal_moon_sidereal_lon,
        start_jd,
        end_jd,
        ayanamsa_system=request.ayanamsa_system,
        reader=engine._reader_obj,
    )
    return SadeSatiWindowsResponse(
        janma_rashi_index=result.janma_rashi_index,
        start_jd=result.start_jd,
        end_jd=result.end_jd,
        ayanamsa_system=result.ayanamsa_system,
        windows=tuple(
            SadeSatiWindowResponse(
                phase=w.phase,
                sign_index=w.sign_index,
                start_jd=w.start_jd,
                end_jd=w.end_jd,
                start_is_ingress=w.start_is_ingress,
                end_is_egress=w.end_is_egress,
            )
            for w in result.windows
        ),
    )


__all__ = [
    "compute_sade_sati_status",
    "compute_sade_sati_windows",
]

from __future__ import annotations

import pytest

from moira.planets import sky_position_at
from tests.tools.benchmark_matrix import STRICT_SKY_PLANET_CASES, SkyCase
from tests.tools.horizons import observer_sky_position


def _signed_arcsec(a_deg: float, b_deg: float) -> float:
    return ((a_deg - b_deg + 180.0) % 360.0 - 180.0) * 3600.0


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("body", "case"),
    [(body, case) for body, cases in STRICT_SKY_PLANET_CASES.items() for case in cases],
    ids=[f"{body}-{case.label}" for body, cases in STRICT_SKY_PLANET_CASES.items() for case in cases],
)
def test_planet_sky_positions_match_horizons(body: str, case: SkyCase) -> None:
    moira = sky_position_at(
        body,
        case.jd_ut,
        observer_lat=case.latitude_deg,
        observer_lon=case.longitude_deg,
        observer_elev_m=case.elevation_km * 1000.0,
    )
    ref = observer_sky_position(
        case.command,
        case.jd_ut,
        longitude_deg=case.longitude_deg,
        latitude_deg=case.latitude_deg,
        elevation_km=case.elevation_km,
    )

    ra_error = _signed_arcsec(moira.right_ascension, ref.right_ascension)
    dec_error = (moira.declination - ref.declination) * 3600.0

    assert abs(ra_error) <= case.ra_tolerance_arcsec, (
        f"{body} {case.label}: RA error {ra_error:+.3f} arcsec "
        f"exceeds {case.ra_tolerance_arcsec:.3f}"
    )
    assert abs(dec_error) <= case.dec_tolerance_arcsec, (
        f"{body} {case.label}: Dec error {dec_error:+.3f} arcsec "
        f"exceeds {case.dec_tolerance_arcsec:.3f}"
    )

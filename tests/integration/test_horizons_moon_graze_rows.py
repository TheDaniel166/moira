from __future__ import annotations

import pytest

from moira.constants import Body
from moira.planets import sky_position_at
from tools.horizons import observer_sky_position
from tests.integration.test_eclipse_occultation_where_reference import (
    _parse_iota_annual_graze_section,
    _parse_iota_graze_rows_for_date,
)


def _signed_arcsec(a_deg: float, b_deg: float) -> float:
    return ((a_deg - b_deg + 180.0) % 360.0 - 180.0) * 3600.0


def _first(rows: list[dict[str, float]]) -> dict[str, float]:
    return rows[0]


def _last(rows: list[dict[str, float]]) -> dict[str, float]:
    return rows[-1]


_AS_BOREALIS_ROWS = _parse_iota_annual_graze_section(
    "https://occultations.org/publications/rasc/2025/nam25grz.txt",
    "Asellus Borealis",
)

CASES = [
    pytest.param(
        "El Nath worst row",
        _last(_parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2025/20250307ElNath.txt", 2025, 3, 7
        )),
        id="elnath-worst",
    ),
    pytest.param(
        "Spica north worst row",
        _last(_parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt", 2024, 11, 27
        )),
        id="spica-north-worst",
    ),
    pytest.param(
        "Spica south worst row",
        _last(_parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2024/20241127SpicaSlimit.txt", 2024, 11, 27
        )),
        id="spica-south-worst",
    ),
    pytest.param(
        "Alcyone leading row",
        _first(_parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt", "Alcyone"
        )),
        id="alcyone-leading",
    ),
    pytest.param(
        "Merope leading row",
        _first(_parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt", "Merope"
        )),
        id="merope-leading",
    ),
    pytest.param(
        "Asellus Borealis control row",
        _AS_BOREALIS_ROWS[(2 * len(_AS_BOREALIS_ROWS)) // 3],
        id="asellus-control",
    ),
    pytest.param(
        "Regulus control row",
        _last(_parse_iota_annual_graze_section(
            "https://occultations.org/publications/rasc/2025/nam25grz.txt", "Regulus"
        )),
        id="regulus-control",
    ),
]


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(("label", "row"), CASES)
def test_moon_topocentric_apparent_position_matches_horizons_on_occultation_rows(
    label: str,
    row: dict[str, float],
) -> None:
    moira = sky_position_at(
        Body.MOON,
        row["jd"],
        observer_lat=row["lat"],
        observer_lon=row["lon"],
        observer_elev_m=row["observer_elev_m"],
    )
    ref = observer_sky_position(
        "301",
        row["jd"],
        longitude_deg=row["lon"],
        latitude_deg=row["lat"],
        elevation_km=row["observer_elev_m"] / 1000.0,
    )

    ra_error = _signed_arcsec(moira.right_ascension, ref.right_ascension)
    dec_error = (moira.declination - ref.declination) * 3600.0

    assert abs(ra_error) <= 0.5, (
        f"{label}: Moon RA error {ra_error:+.3f} arcsec exceeds 0.5 arcsec"
    )
    assert abs(dec_error) <= 0.5, (
        f"{label}: Moon Dec error {dec_error:+.3f} arcsec exceeds 0.5 arcsec"
    )

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


CASES = [
    pytest.param("elnath-worst", id="elnath-worst"),
    pytest.param("spica-north-worst", id="spica-north-worst"),
    pytest.param("spica-south-worst", id="spica-south-worst"),
    pytest.param("alcyone-leading", id="alcyone-leading"),
    pytest.param("merope-leading", id="merope-leading"),
    pytest.param("asellus-control", id="asellus-control"),
    pytest.param("regulus-control", id="regulus-control"),
]


def _load_case(case_key: str) -> tuple[str, dict[str, float]]:
    """Acquire one live IOTA row only after pytest admits the network test."""
    if case_key == "elnath-worst":
        rows = _parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2025/20250307ElNath.txt",
            2025,
            3,
            7,
        )
        return "El Nath worst row", _last(rows)
    if case_key == "spica-north-worst":
        rows = _parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2024/20241127SpicaNlimit.txt",
            2024,
            11,
            27,
        )
        return "Spica north worst row", _last(rows)
    if case_key == "spica-south-worst":
        rows = _parse_iota_graze_rows_for_date(
            "https://occultations.org/publications/rasc/2024/20241127SpicaSlimit.txt",
            2024,
            11,
            27,
        )
        return "Spica south worst row", _last(rows)

    annual_url = "https://occultations.org/publications/rasc/2025/nam25grz.txt"
    if case_key == "alcyone-leading":
        return "Alcyone leading row", _first(
            _parse_iota_annual_graze_section(annual_url, "Alcyone")
        )
    if case_key == "merope-leading":
        return "Merope leading row", _first(
            _parse_iota_annual_graze_section(annual_url, "Merope")
        )
    if case_key == "asellus-control":
        rows = _parse_iota_annual_graze_section(annual_url, "Asellus Borealis")
        return "Asellus Borealis control row", rows[(2 * len(rows)) // 3]
    if case_key == "regulus-control":
        return "Regulus control row", _last(
            _parse_iota_annual_graze_section(annual_url, "Regulus")
        )
    raise AssertionError(f"unknown IOTA/Horizons case {case_key!r}")


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize("case_key", CASES)
def test_moon_topocentric_apparent_position_matches_horizons_on_occultation_rows(
    case_key: str,
) -> None:
    label, row = _load_case(case_key)
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

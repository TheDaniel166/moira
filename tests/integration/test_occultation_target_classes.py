from __future__ import annotations

import pytest

from moira.julian import ut_to_tt
from moira.lunar_limb import official_lunar_limb_profile_adjustment
from moira.occultations import (
    lunar_star_graze_line,
)
from moira.stars import star_at
from tests.integration.test_eclipse_occultation_where_reference import (
    _parse_iota_annual_graze_section,
    _parse_iota_graze_rows_for_date,
)


@pytest.mark.network
def test_target_class_nominal_elnath_worst_row() -> None:
    row = _parse_iota_graze_rows_for_date(
        "https://occultations.org/publications/rasc/2025/20250307ElNath.txt",
        2025,
        3,
        7,
    )[-1]
    star = star_at("Elnath", ut_to_tt(float(row["jd"])))
    graze_lat = lunar_star_graze_line(
        star.longitude,
        star.latitude,
        float(row["jd"]),
        float(row["lon"]),
        float(row["lat"]),
        semantics="nominal",
        observer_elev_m=float(row["observer_elev_m"]),
        refraction_adjusted=True,
    )
    assert abs(graze_lat - float(row["lat"])) <= 0.003


@pytest.mark.network
def test_target_class_nominal_spica_south_worst_row() -> None:
    row = _parse_iota_graze_rows_for_date(
        "https://occultations.org/publications/rasc/2024/20241127SpicaSlimit.txt",
        2024,
        11,
        27,
    )[-1]
    star = star_at("Spica", ut_to_tt(float(row["jd"])))
    graze_lat = lunar_star_graze_line(
        star.longitude,
        star.latitude,
        float(row["jd"]),
        float(row["lon"]),
        float(row["lat"]),
        semantics="nominal",
        observer_elev_m=float(row["observer_elev_m"]),
        refraction_adjusted=True,
    )
    assert abs(graze_lat - float(row["lat"])) <= 0.0015


@pytest.mark.network
@pytest.mark.slow
def test_target_class_profile_alcyone_leading_row() -> None:
    row = _parse_iota_annual_graze_section(
        "https://occultations.org/publications/rasc/2025/nam25grz.txt",
        "Alcyone",
    )[0]
    star = star_at("Alcyone", ut_to_tt(float(row["jd"])))
    practical_lat = lunar_star_graze_line(
        star.longitude,
        star.latitude,
        float(row["jd"]),
        float(row["lon"]),
        float(row["lat"]),
        semantics="practical",
        observer_elev_m=float(row["observer_elev_m"]),
        limb_profile_provider=official_lunar_limb_profile_adjustment,
    )
    assert abs(practical_lat - float(row["lat"])) <= 0.003


@pytest.mark.network
@pytest.mark.slow
def test_target_class_profile_merope_leading_row() -> None:
    row = _parse_iota_annual_graze_section(
        "https://occultations.org/publications/rasc/2025/nam25grz.txt",
        "Merope",
    )[0]
    star = star_at("Merope", ut_to_tt(float(row["jd"])))
    practical_lat = lunar_star_graze_line(
        star.longitude,
        star.latitude,
        float(row["jd"]),
        float(row["lon"]),
        float(row["lat"]),
        semantics="practical",
        observer_elev_m=float(row["observer_elev_m"]),
        limb_profile_provider=official_lunar_limb_profile_adjustment,
    )
    assert abs(practical_lat - float(row["lat"])) <= 0.002

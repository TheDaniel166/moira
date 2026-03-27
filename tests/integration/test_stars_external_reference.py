from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.stars import star_at


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "stars_swetest_reference.json"
EXPECTED_STARS = {"Sirius", "Algol", "Spica", "Aldebaran"}
MAX_LONGITUDE_ERROR_DEG = 0.01
MAX_LATITUDE_ERROR_DEG = 0.0025
MAX_TT_UT_RESIDUAL_DELTA_DEG = 1e-5


def _angular_diff(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


@pytest.fixture(scope="module")
def star_reference_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.integration
def test_star_fixture_covers_expected_anchor_set(star_reference_data: dict) -> None:
    assert set(star_reference_data["_stars"]) == EXPECTED_STARS
    assert star_reference_data["_case_count"] == len(star_reference_data["cases"])
    assert len(star_reference_data["cases"]) >= 7


def _cases(data: dict) -> list[pytest.ParamSpec]:
    params = []
    for case in data["cases"]:
        for star_name, ref in case["stars"].items():
            params.append(
                pytest.param(
                    case["id"],
                    star_name,
                    ref["jd_tt"],
                    ref["longitude_deg"],
                    ref["latitude_deg"],
                    id=f"{case['id']}::{star_name}",
                )
            )
    return params


REFERENCE_DATA = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.integration
@pytest.mark.parametrize(
    ("case_id", "star_name", "jd_tt", "expected_longitude", "expected_latitude"),
    _cases(REFERENCE_DATA),
)
def test_stars_match_offline_swiss_reference_at_jd_tt(
    case_id: str,
    star_name: str,
    jd_tt: float,
    expected_longitude: float,
    expected_latitude: float,
) -> None:
    actual = star_at(star_name, jd_tt)
    lon_err = _angular_diff(actual.longitude, expected_longitude)
    lat_err = abs(actual.latitude - expected_latitude)

    assert lon_err <= MAX_LONGITUDE_ERROR_DEG, (
        f"{case_id} {star_name}: expected lon {expected_longitude:.10f}, "
        f"got {actual.longitude:.10f}, delta={lon_err:.10f} deg "
        f"({lon_err * 3600.0:.3f} arcsec)"
    )
    assert lat_err <= MAX_LATITUDE_ERROR_DEG, (
        f"{case_id} {star_name}: expected lat {expected_latitude:.10f}, "
        f"got {actual.latitude:.10f}, delta={lat_err:.10f} deg "
        f"({lat_err * 3600.0:.3f} arcsec)"
    )


@pytest.mark.integration
def test_fixed_star_external_residual_is_not_driven_by_delta_t(star_reference_data: dict) -> None:
    failures: list[str] = []

    for case in star_reference_data["cases"]:
        for star_name, ref in case["stars"].items():
            tt_star = star_at(star_name, ref["jd_tt"])
            ut_star = star_at(star_name, ref["jd_ut"])

            tt_total = max(
                _angular_diff(tt_star.longitude, ref["longitude_deg"]),
                abs(tt_star.latitude - ref["latitude_deg"]),
            )
            ut_total = max(
                _angular_diff(ut_star.longitude, ref["longitude_deg"]),
                abs(ut_star.latitude - ref["latitude_deg"]),
            )
            alignment_delta = abs(tt_total - ut_total)

            if alignment_delta > MAX_TT_UT_RESIDUAL_DELTA_DEG:
                failures.append(
                    f"{case['id']} {star_name}: TT residual={tt_total:.10f} deg, "
                    f"UT residual={ut_total:.10f} deg, "
                    f"alignment delta={alignment_delta:.10f} deg"
                )

    assert not failures, "TT-vs-UT alignment changed the residual too much:\n" + "\n".join(failures)

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.sidereal import Ayanamsa, ayanamsa


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "sidereal_swetest_reference.json"
PASS_THRESHOLD_DEG = 1e-3  # 3.6 arcseconds


def _angular_diff(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


@pytest.fixture(scope="module")
def sidereal_reference_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _cases(data: dict, mode: str) -> list[pytest.ParamSpec]:
    params = []
    for case in data["cases"]:
        for system, system_data in case["systems"].items():
            ref = system_data[mode]
            params.append(
                pytest.param(
                    system,
                    ref["jd_tt"],
                    ref["ayanamsa_deg"],
                    system_data["sid_mode"],
                    case["id"],
                    id=f"{case['id']}::{system}::{mode}",
                )
            )
    return params


REFERENCE_DATA = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
MEAN_CASES = _cases(REFERENCE_DATA, "mean")
TRUE_CASES = _cases(REFERENCE_DATA, "true")


@pytest.mark.integration
def test_fixture_covers_all_supported_moira_systems() -> None:
    covered = {system for case in REFERENCE_DATA["cases"] for system in case["systems"]}
    expected = set(Ayanamsa.ALL) - {Ayanamsa.GALACTIC_5_SAG}

    assert covered == expected


@pytest.mark.integration
@pytest.mark.parametrize("case_id", [case["id"] for case in REFERENCE_DATA["cases"]])
@pytest.mark.parametrize("mode", ["mean", "true"])
def test_galactic_5_sag_tracks_galactic_0_sag_plus_five_degrees(case_id: str, mode: str) -> None:
    case = next(case for case in REFERENCE_DATA["cases"] if case["id"] == case_id)
    jd_tt = case["systems"][Ayanamsa.GALACTIC_0_SAG][mode]["jd_tt"]

    gal0 = ayanamsa(jd_tt, Ayanamsa.GALACTIC_0_SAG, mode=mode)
    gal5 = ayanamsa(jd_tt, Ayanamsa.GALACTIC_5_SAG, mode=mode)
    expected = (gal0 + 5.0) % 360.0
    diff = _angular_diff(gal5, expected)

    assert diff <= PASS_THRESHOLD_DEG, (
        f"{case_id} {mode} Galactic Center (5 Sag): "
        f"expected {expected:.12f}, got {gal5:.12f}, "
        f"delta={diff:.12f} deg ({diff * 3600:.3f} arcsec)"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("system", "jd_tt", "expected", "sid_mode", "case_id"),
    MEAN_CASES,
)
def test_mean_ayanamsa_matches_offline_swetest_references(
    system: str,
    jd_tt: float,
    expected: float,
    sid_mode: int,
    case_id: str,
) -> None:
    actual = ayanamsa(jd_tt, system, mode="mean")
    diff = _angular_diff(actual, expected)

    assert diff <= PASS_THRESHOLD_DEG, (
        f"{case_id} sid_mode={sid_mode} mean {system}: "
        f"expected {expected:.12f}, got {actual:.12f}, "
        f"delta={diff:.12f} deg ({diff * 3600:.3f} arcsec)"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("system", "jd_tt", "expected", "sid_mode", "case_id"),
    TRUE_CASES,
)
def test_true_ayanamsa_matches_offline_swetest_references(
    system: str,
    jd_tt: float,
    expected: float,
    sid_mode: int,
    case_id: str,
) -> None:
    actual = ayanamsa(jd_tt, system, mode="true")
    diff = _angular_diff(actual, expected)

    assert diff <= PASS_THRESHOLD_DEG, (
        f"{case_id} sid_mode={sid_mode} true {system}: "
        f"expected {expected:.12f}, got {actual:.12f}, "
        f"delta={diff:.12f} deg ({diff * 3600:.3f} arcsec)"
    )

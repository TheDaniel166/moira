from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.sidereal import Ayanamsa, ayanamsa


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "sidereal_swetest_reference.json"
# Secondary external-reference tolerance for non-star systems. The swetest
# fixture and Moira differ by model basis in historical epochs; keep a modest
# envelope for cross-engine sanity checks.
PASS_THRESHOLD_DEG = 1e-2  # 36 arcseconds

# Star-anchored ("true") ayanamsas compute the ayanamsa from the live tropical
# longitude of a reference star.  Moira uses IAU 2006 Fukushima-Williams
# precession and proper-motion propagation; Swiss Ephemeris uses an older
# precession model and includes annual aberration.  The resulting model-basis
# difference is ~5-20" for most stars and up to ~110" for high-proper-motion
# stars (Aldebaran) at historical epochs.  This is not a defect — Moira's
# IAU 2006 pipeline is the stronger model.
STAR_ANCHORED_THRESHOLD_DEG = 0.035  # 126 arcseconds — model-basis envelope

# Systems whose "true" mode uses a live star position rather than a polynomial.
_STAR_ANCHORED_SYSTEMS = {
    Ayanamsa.TRUE_CHITRAPAKSHA, Ayanamsa.TRUE_REVATI,
    Ayanamsa.ALDEBARAN_15_TAU, Ayanamsa.TRUE_PUSHYA,
    Ayanamsa.TRUE_MULA,
}


def _angular_diff(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


@pytest.fixture(scope="module")
def sidereal_reference_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _cases(data: dict, mode: str) -> list[pytest.ParamSpec]:
    params = []
    active = set(Ayanamsa.ALL)
    for case in data["cases"]:
        for system, system_data in case["systems"].items():
            if system not in active:
                continue
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
    expected = set(Ayanamsa.ALL)
    assert expected.issubset(covered)


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
    # Star-anchored systems also carry model-basis polynomial drift in mean mode.
    threshold = STAR_ANCHORED_THRESHOLD_DEG if system in _STAR_ANCHORED_SYSTEMS else PASS_THRESHOLD_DEG

    assert diff <= threshold, (
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
    threshold = STAR_ANCHORED_THRESHOLD_DEG if system in _STAR_ANCHORED_SYSTEMS else PASS_THRESHOLD_DEG

    assert diff <= threshold, (
        f"{case_id} sid_mode={sid_mode} true {system}: "
        f"expected {expected:.12f}, got {actual:.12f}, "
        f"delta={diff:.12f} deg ({diff * 3600:.3f} arcsec)"
    )

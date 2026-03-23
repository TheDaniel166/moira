from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from moira.constants import Body
from moira.dasha import vimshottari
from moira.julian import jd_from_datetime
from moira.planets import planet_at


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "vimshottari_reference.json"
PASS_THRESHOLD_DAYS = 1.0


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


REFERENCE_CASES = _load_fixture().get("cases", []) if FIXTURE_PATH.exists() else []


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _find_period(periods: list, planet: str, start_jd: float, end_jd: float, parent: str | None = None):
    for period in periods:
        if period.planet != planet:
            continue
        if parent is not None and period.parent_planet != parent:
            continue
        if abs(period.start_jd - start_jd) <= PASS_THRESHOLD_DAYS and abs(period.end_jd - end_jd) <= PASS_THRESHOLD_DAYS:
            return period
    return None


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.skipif(
    not FIXTURE_PATH.exists(),
    reason="vimshottari_reference.json not found - run scripts/build_vimshottari_manual_fixture.py first",
)
def test_vimshottari_fixture_has_real_cases() -> None:
    fixture = _load_fixture()
    cases = fixture.get("cases", [])
    assert cases, "No Vimshottari oracle cases present in fixture"
    assert all(case["mahadasha"] for case in cases), "Fixture contains placeholder cases without Mahadasha data"


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.skipif(
    not FIXTURE_PATH.exists(),
    reason="vimshottari_reference.json not found - run scripts/build_vimshottari_manual_fixture.py first",
)
@pytest.mark.parametrize("case", REFERENCE_CASES, ids=lambda case: case["id"])
def test_vimshottari_matches_manual_external_reference(case: dict) -> None:
    if not case["mahadasha"]:
        pytest.skip(f"{case['id']}: placeholder case without oracle values")

    natal_dt = _dt(case["natal_dt_utc"])
    natal_jd = jd_from_datetime(natal_dt)
    moon_lon = planet_at(Body.MOON, natal_jd).longitude

    levels = 2 if case.get("antardasha") else 1
    periods = vimshottari(
        moon_lon,
        natal_jd,
        levels=levels,
        year_basis=case["year_basis"],
        ayanamsa_system=case["ayanamsa"],
    )

    for expected in case["mahadasha"]:
        start_jd = jd_from_datetime(_dt(expected["start_utc"]))
        end_jd = jd_from_datetime(_dt(expected["end_utc"]))
        match = _find_period(periods, expected["planet"], start_jd, end_jd)
        assert match is not None, (
            f"{case['id']} Mahadasha {expected['planet']} not found within {PASS_THRESHOLD_DAYS} day(s) "
            f"of {expected['start_utc']} -> {expected['end_utc']}"
        )

    for expected in case.get("antardasha", []):
        start_jd = jd_from_datetime(_dt(expected["start_utc"]))
        end_jd = jd_from_datetime(_dt(expected["end_utc"]))
        match = _find_period(periods, expected["planet"], start_jd, end_jd, parent=expected["parent"])
        assert match is not None, (
            f"{case['id']} Antardasha {expected['parent']} / {expected['planet']} not found within "
            f"{PASS_THRESHOLD_DAYS} day(s) of {expected['start_utc']} -> {expected['end_utc']}"
        )

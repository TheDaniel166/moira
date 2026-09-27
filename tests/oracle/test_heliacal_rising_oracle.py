"""Primary-source and independent-oracle checks for heliacal risings.

Schaefer (1987, DOI 10.1177/002182868701801103) defines heliacal rising as
first morning visibility after conjunction and solar invisibility. NASA/JPL
Horizons owns apparition identity and Sun-relative geometry in the planetary
matrix. Exact visibility dates are policy-dependent, so the strict timed
anchors use independently evaluated one-minute JPL/Hipparcos geometry and the
checksum-locked physical visibility data pack without importing Moira's event
solver. Captured legacy results are regression receipts, never oracle truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import moira.heliacal as heliacal_module
from moira.heliacal import (
    HeliacalEventKind,
    _local_mean_solar_midnight,
    planet_heliacal_rising,
)
from moira.spk_reader import use_reader_override
from moira.star_types import FixedStarComputationPolicy
from moira.stars import heliacal_rising_event


_ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "oracle"
_ORACLE_PATH = _ARTIFACTS / "heliacal_rising_oracle_matrix.json"
_PHYSICAL_GOLDEN_PATH = (
    Path(__file__).resolve().parents[1]
    / "golden"
    / "physical_visibility_phase3_events.json"
)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_ORACLE = _json(_ORACLE_PATH)
_PLANETARY_CASES = tuple(_ORACLE["planetary_cases"])


def _physical_case(case_id: str) -> dict[str, Any]:
    golden = _json(_PHYSICAL_GOLDEN_PATH)
    return next(case for case in golden["cases"] if case["case_id"] == case_id)


def test_oracle_matrix_covers_every_admitted_heliacal_planet_once() -> None:
    bodies = [str(case["body"]) for case in _PLANETARY_CASES]

    assert len(bodies) == _ORACLE["selection_policy"]["required_planet_count"]
    assert len(bodies) == len(set(bodies))
    assert set(bodies) == set(heliacal_module._HELIACAL_PLANETS)


@pytest.mark.parametrize(
    "case",
    _PLANETARY_CASES,
    ids=lambda case: str(case["case_id"]),
)
@pytest.mark.requires_ephemeris
def test_every_planet_opens_only_after_its_jpl_morning_side_transition(
    case: dict[str, Any],
    planetary_reader,
) -> None:
    selection = _ORACLE["selection_policy"]
    site = case["site"]
    transition = case["conjunction_side_transition"]
    captured = case["captured_legacy_result"]
    horizons_event = case["legacy_event_horizons_sample"]

    assert transition["trailing_sample"]["relative_position_code"] == "/T"
    assert transition["leading_sample"]["relative_position_code"] == "/L"
    assert horizons_event["relative_position_code"] == "/L"

    with use_reader_override(planetary_reader):
        event = planet_heliacal_rising(
            str(case["body"]),
            float(selection["search_start_jd_ut"]),
            float(site["latitude_deg"]),
            float(site["longitude_deg"]),
            search_days=int(selection["search_days"]),
        )

    assert event is not None
    assert event.kind is HeliacalEventKind.HELIACAL_RISING
    assert event.jd_ut > transition["leading_sample"]["jd_ut"]
    assert event.jd_ut <= (
        transition["leading_sample"]["jd_ut"]
        + float(case["maximum_days_after_leading_transition"])
    )
    assert event.jd_ut == pytest.approx(captured["jd_ut"], abs=0.5 / 86400.0)
    assert event.jd_ut == pytest.approx(horizons_event["jd_ut"], abs=0.5 / 86400.0)
    assert event.elongation_deg < 0.0
    assert abs(abs(event.elongation_deg) - horizons_event["solar_elongation_deg"]) <= (
        float(selection["maximum_jpl_engine_elongation_difference_deg"])
    )
    assert event.planet_altitude_deg > 0.0
    assert event.sun_altitude_deg < 0.0


@pytest.mark.parametrize(
    "case",
    _PLANETARY_CASES,
    ids=lambda case: str(case["case_id"]),
)
@pytest.mark.requires_ephemeris
def test_every_planet_skips_an_already_open_apparition(
    case: dict[str, Any],
    planetary_reader,
) -> None:
    site = case["site"]
    first_rising = float(case["captured_legacy_result"]["jd_ut"])

    with use_reader_override(planetary_reader):
        next_rising = planet_heliacal_rising(
            str(case["body"]),
            first_rising + 1.0,
            float(site["latitude_deg"]),
            float(site["longitude_deg"]),
            search_days=900,
        )

    assert next_rising is not None
    assert next_rising.jd_ut - first_rising > float(
        case["minimum_next_rising_separation_days"]
    )


@pytest.mark.requires_ephemeris
def test_reported_jupiter_open_apparition_returns_the_2027_rising(
    planetary_reader,
) -> None:
    regression = _ORACLE["reported_jupiter_regression"]
    site = regression["site"]

    assert regression["already_visible_apparition"]["solar_elongation_deg"] == (
        pytest.approx(49.8625)
    )
    assert regression["already_visible_apparition"]["relative_position_code"] == "/L"

    with use_reader_override(planetary_reader):
        event = planet_heliacal_rising(
            "Jupiter",
            float(regression["search_start_jd_ut"]),
            float(site["latitude_deg"]),
            float(site["longitude_deg"]),
            search_days=400,
        )

    assert event is not None
    assert event.jd_ut > regression["next_conjunction_leading_sample"]["jd_ut"]
    assert event.jd_ut == pytest.approx(
        regression["independent_visibility_event_jd_ut"],
        abs=float(regression["maximum_legacy_difference_days"]),
    )
    assert abs(event.elongation_deg) < regression["maximum_event_solar_elongation_deg"]


@pytest.mark.requires_ephemeris
def test_legacy_jupiter_is_bounded_by_independent_physical_oracle(
    planetary_reader,
) -> None:
    anchor = _ORACLE["independent_visibility_anchors"][0]
    physical = _physical_case(str(anchor["case_id"]))

    with use_reader_override(planetary_reader):
        event = planet_heliacal_rising(
            str(physical["target"]),
            float(physical["jd_start"]),
            float(physical["latitude_deg"]),
            float(physical["longitude_deg"]),
            search_days=int(physical["search_window_days"]),
        )

    assert event is not None
    assert event.jd_ut == pytest.approx(
        physical["independent_oracle"]["event_jd_ut"],
        abs=float(anchor["maximum_legacy_difference_days"]),
    )


@pytest.mark.requires_ephemeris
def test_legacy_sirius_is_bounded_and_skips_its_open_apparition(
    planetary_reader,
) -> None:
    anchor = _ORACLE["independent_visibility_anchors"][1]
    physical = _physical_case(str(anchor["case_id"]))
    python_policy = FixedStarComputationPolicy(use_native_heliacal=False)

    with use_reader_override(planetary_reader):
        event = heliacal_rising_event(
            str(physical["target"]),
            float(physical["jd_start"]),
            float(physical["latitude_deg"]),
            float(physical["longitude_deg"]),
            search_days=int(physical["search_window_days"]),
            policy=python_policy,
        )
        assert event.jd_ut is not None
        next_event = heliacal_rising_event(
            str(physical["target"]),
            event.jd_ut + 30.0,
            float(physical["latitude_deg"]),
            float(physical["longitude_deg"]),
            search_days=400,
            policy=python_policy,
        )

    assert event.jd_ut == pytest.approx(
        physical["independent_oracle"]["event_jd_ut"],
        abs=float(anchor["maximum_legacy_difference_days"]),
    )
    assert next_event.jd_ut is not None
    assert next_event.jd_ut - event.jd_ut > 300.0


@pytest.mark.parametrize(
    ("longitude_deg", "expected_midnight_jd_ut"),
    [
        (0.0, 2461041.5),
        (151.21, 2461041.0799722224),
        (-90.0, 2461040.75),
    ],
)
def test_legacy_daily_scan_is_anchored_to_local_mean_solar_midnight(
    longitude_deg: float,
    expected_midnight_jd_ut: float,
) -> None:
    assert _local_mean_solar_midnight(2461041.5, longitude_deg) == (
        pytest.approx(expected_midnight_jd_ut)
    )

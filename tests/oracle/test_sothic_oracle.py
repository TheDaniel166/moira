"""Authority checks for the Sothic component's bounded public truth.

The Censorinus case validates a calendar relation, not an observed timestamp.
The historical civil-day cases compare Moira with the published IMCCE/
Observatoire de Paris Sirius calculator under identical site, year, arcus, and
calendar semantics. Strict modern event-time validation remains owned by the
independent physical heliacal oracle named in the artifact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from moira.sothic import (
    CENSORINUS_139_ANCHOR,
    SOTHIC_EPOCH_REFERENCES,
    SothicYearStatus,
    sothic_rising_series,
)
from moira.spk_reader import use_reader_override


_ORACLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "oracle"
    / "sothic_reference_matrix.json"
)


def _oracle() -> dict[str, Any]:
    return json.loads(_ORACLE_PATH.read_text(encoding="utf-8"))


def test_censorinus_anchor_preserves_calendar_and_evidence_semantics() -> None:
    oracle = _oracle()
    expected = oracle["calendar_anchor"]
    source = oracle["sources"]["censorinus"]

    assert CENSORINUS_139_ANCHOR.anchor_id == expected["anchor_id"]
    assert CENSORINUS_139_ANCHOR.jd == pytest.approx(expected["jd"], abs=1e-12)
    assert CENSORINUS_139_ANCHOR.astronomical_year == expected["astronomical_year"]
    assert CENSORINUS_139_ANCHOR.julian_calendar_date == expected["julian_calendar_date"]
    assert (
        CENSORINUS_139_ANCHOR.proleptic_gregorian_date
        == expected["proleptic_gregorian_date"]
    )
    assert CENSORINUS_139_ANCHOR.evidence_kind == "primary_text_calendar_anchor"
    assert CENSORINUS_139_ANCHOR.source_title == source["title"]
    assert CENSORINUS_139_ANCHOR.source_locator == source["locator"]
    assert CENSORINUS_139_ANCHOR.source_url == source["url"]


def test_cycle_reference_table_does_not_promote_projections_to_observations() -> None:
    references = {reference.cycle_offset_from_139: reference for reference in SOTHIC_EPOCH_REFERENCES}

    assert references[0].evidence_kind == "primary_text_calendar_anchor"
    assert references[0].astronomical_year == 139
    for offset in (-2, -1, 1):
        assert references[offset].evidence_kind == "schematic_projection"
        assert references[offset].astronomical_year == 139 + offset * 1460


def test_oracle_matrix_names_independent_modern_timing_owner() -> None:
    source = _oracle()["sources"]["modern_physical_oracle"]

    assert source["case_id"] == "phase3-sirius-2026-morning-first-rising"
    assert source["artifact"] == "tests/golden/physical_visibility_phase3_events.json"
    assert source["test_owner"] == "tests/oracle/test_heliacal_rising_oracle.py"


@pytest.mark.parametrize(
    "case",
    _oracle()["imcce_civil_day_cases"],
    ids=lambda case: str(case["case_id"]),
)
@pytest.mark.requires_ephemeris
def test_sothic_civil_day_matches_published_imcce_sirius_model(
    case: dict[str, Any],
    planetary_reader,
) -> None:
    """Authority validation at civil-day resolution, the shared product level."""

    with use_reader_override(planetary_reader):
        result = sothic_rising_series(
            float(case["latitude_deg"]),
            float(case["longitude_deg"]),
            int(case["astronomical_year"]),
            int(case["astronomical_year"]),
            arcus_visionis=float(case["arcus_visionis_deg"]),
        )

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert outcome.status is SothicYearStatus.FOUND
    assert outcome.entry is not None
    assert (
        outcome.entry.calendar_year,
        outcome.entry.calendar_month,
        outcome.entry.calendar_day,
    ) == tuple(case["expected_proleptic_gregorian"])
    assert outcome.entry.heliacal_event is outcome.heliacal_event
    assert outcome.heliacal_event.computation_truth is not None
    assert outcome.heliacal_event.computation_truth.arcus_visionis == pytest.approx(
        case["arcus_visionis_deg"],
        abs=1e-12,
    )

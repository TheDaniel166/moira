from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.eclipse_contacts import find_lunar_contacts


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"


def _contact_cases() -> tuple[dict[str, float | str], ...]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return tuple(payload["lunar_contact_products"])


def _duration_minutes(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return (end - start) * 1440.0


def test_lunar_contact_fixture_names_its_catalog_semantics_and_sources() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert "Danjon" in payload["source"]["lunar_contact_validation_note"]
    rows = payload["lunar_contact_products"]
    assert len(rows) == 4
    assert {str(row["kind"]) for row in rows} == {"penumbral", "partial", "total"}
    assert all(
        row["source_url"]
        == "https://eclipse.gsfc.nasa.gov/LEcat5/LE2001-2100.html"
        for row in rows
    )
    for row in rows:
        derived_ut_jd = float(row["greatest_td_jd"]) - (
            float(row["delta_t_s"]) / 86400.0
        )
        assert float(row["greatest_ut_jd"]) == pytest.approx(
            derived_ut_jd,
            abs=1.0e-9,
        )


@pytest.mark.slow
@pytest.mark.parametrize(
    "row",
    _contact_cases(),
    ids=lambda row: str(row["label"]),
)
def test_native_lunar_contact_durations_match_named_nasa_catalog_products(
    eclipse_calculator,
    row: dict[str, float | str],
) -> None:
    """Compare native mean-limb phase durations with named NASA rows.

    NASA's century catalog uses VSOP87/ELP2000-82, Danjon enlargement, and
    catalog Delta-T; Moira uses DE441 with its native TT/UT policy.  The
    fixture therefore owns explicit cross-model duration envelopes.  The
    limiting 2027 penumbral row is evidence that the short P1/P4 pair remains
    resolved, not a sub-minute parity claim.
    """

    greatest_ut = float(row["greatest_ut_jd"])
    contacts = find_lunar_contacts(eclipse_calculator, greatest_ut)
    data = eclipse_calculator.calculate_jd(contacts.greatest)

    assert str(data.eclipse_type).lower() == str(row["kind"])
    assert abs(contacts.greatest - greatest_ut) * 86400.0 <= float(
        row["greatest_tolerance_s"]
    )

    phase_pairs = {
        "penumbral_duration_min": (contacts.p1, contacts.p4),
        "partial_duration_min": (contacts.u1, contacts.u4),
        "total_duration_min": (contacts.u2, contacts.u3),
    }
    duration_tolerance = float(row["duration_tolerance_min"])
    for field, (start, end) in phase_pairs.items():
        actual_duration = _duration_minutes(start, end)
        if field not in row:
            assert actual_duration is None
            continue
        assert actual_duration is not None
        assert actual_duration == pytest.approx(
            float(row[field]),
            abs=duration_tolerance,
        )

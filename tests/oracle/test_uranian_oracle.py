"""Cross-engine corroboration for all admitted hypothetical bodies.

The fixed artifact was captured from Astrodienst's official swetest 2.10.03
service. It is secondary cross-engine evidence, not the authority for Moira's
standard Keplerian derivation and not a runtime dependency.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.uranian import UranianBody, all_uranian_at


_ARTIFACT_PATH = (
    Path(__file__).parents[1]
    / "artifacts"
    / "oracle"
    / "uranian_reference_matrix.json"
)
_ARTIFACT = json.loads(_ARTIFACT_PATH.read_text(encoding="utf-8"))


def _circular_error(actual: float, expected: float) -> float:
    return abs((actual - expected + 180.0) % 360.0 - 180.0)


@pytest.mark.parametrize(
    "snapshot",
    _ARTIFACT["snapshots"],
    ids=lambda row: row["datetime_utc"],
)
def test_all_uranian_positions_match_frozen_swetest_matrix(
    snapshot: dict,
    moira_engine,
) -> None:
    tolerances = _ARTIFACT["tolerances"]
    actual = all_uranian_at(snapshot["jd_ut"], reader=moira_engine._reader)

    assert list(snapshot["positions"]) == list(UranianBody.ALL)
    assert list(actual) == list(UranianBody.ALL)
    for name, expected in snapshot["positions"].items():
        longitude, latitude, distance_au, speed = expected
        position = actual[name]
        assert _circular_error(position.longitude, longitude) <= tolerances["longitude_deg"]
        assert position.latitude == pytest.approx(
            latitude,
            abs=tolerances["latitude_deg"],
        )
        assert position.distance_au == pytest.approx(
            distance_au,
            abs=tolerances["distance_au"],
        )
        assert position.speed == pytest.approx(
            speed,
            abs=tolerances["speed_deg_per_day"],
        )
        assert position.retrograde is (speed < 0.0)


def test_oracle_matrix_names_its_semantics_and_evidence_class() -> None:
    assert _ARTIFACT["evidence_class"] == "cross_engine_corroboration"
    comparator = _ARTIFACT["comparator"]
    assert comparator["provider"] == "Astrodienst"
    assert comparator["version"] == "2.10.03"
    assert comparator["body_codes"] == "JKLMNOPQR"
    assert "apparent geocentric" in comparator["semantics"]

"""Byte-bound primary-source review; no runtime accuracy/admission bypass."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "fixtures/horizons_asteroid_apsidal_anchored_2026_10_03"


def _load(name):
    return json.loads((ROOT / name).read_bytes())


def _hash(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def test_review_binds_primary_inputs_and_keeps_original_gates():
    review = _load("source_review.json")
    report = _load("report.json")
    assert review["status"] == "reviewed_for_validation_only_integration"
    assert review["release_admitted"] is False
    assert _hash("report.json") == review["report_sha256"]
    assert _hash("unanchored-controls.json") == review["controls_sha256"]
    assert _hash("historical-reference-input.json") == report["historical_fixture_sha256"]
    assert report["candidate_manifest_sha256"] == review["validated_view_manifest_sha256"]
    assert review["acceptance_gates"] == report["acceptance_gates"] == {
        "event_time_absolute_days": 0.0001, "distance_absolute_au": 1e-9,
    }
    for name, digest in review["generator_captures"].items():
        assert _hash(name) == digest


def test_every_authority_event_retains_anchors_solutions_and_two_sided_witnesses():
    report = _load("report.json")
    review = _load("source_review.json")
    assert len(report["events"]) == review["event_count"] == 6
    assert {event["body"] for event in report["events"]} == {"Eros", "Chiron", "Sedna", "Eris"}
    checked = set()
    for event in report["events"]:
        assert event["coverage_anchor_epochs_jd_tdb"] == [2305447.5, 2634157.5]
        assert event["target_solution"] == event["historical_target_solution"]
        assert abs(event["candidate_distance_delta_km"]) <= 0.1495978707
        before, after = event["two_sided_radial_velocity_km_s"]
        if event["kind"] == "PERICENTER":
            assert before < 0 < after
        else:
            assert event["kind"] == "APOCENTER" and before > 0 > after
        for request in event["requests"]:
            tags = request["epochs_jd_tdb"]
            assert tags[0] == 2305447.5 and tags[-1] == 2634157.5
            assert request["authority"]["target_solution"] == event["target_solution"]
            assert "Sun (10)" in request["authority"]["center_body_line"]
            assert "DE441" in request["authority"]["center_body_line"]
            assert _hash(request["raw_response"]) == request["sha256"]
            assert (ROOT / request["raw_response"]).stat().st_size == request["bytes"]
            checked.add(request["raw_response"])
    assert checked == {path.name for path in ROOT.glob("*.horizons.txt")
                       if "unanchored-control" not in path.name}


def test_live_unanchored_controls_reproduce_the_historical_reference_product():
    controls = _load("unanchored-controls.json")
    events = _load("report.json")["events"]
    assert len(controls) == 4
    for control in controls:
        reference = next(e for e in events if e["body"] == control["body"])
        assert len(control["query_epochs_jd_tdb"]) == 1
        assert control["authority"]["target_solution"] == reference["target_solution"]
        assert abs(control["historical_distance_delta_km"]) <= 1e-6
        assert _hash(control["raw_response"]) == control["response_sha256"]

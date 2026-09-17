"""Governance checks for the reviewed Orbital Core Stage 1 receipts."""

from __future__ import annotations

import json
import re
from pathlib import Path


ARTIFACT_ROOT = Path(__file__).parents[1] / "artifacts" / "release"
ARTIFACTS = {
    "clock": ARTIFACT_ROOT
    / "orbital_core_stage1_reader_clock_shift_2026-09-15.json",
    "frame": ARTIFACT_ROOT
    / "orbital_core_stage1_frame_shift_2026-09-15.json",
    "validation": ARTIFACT_ROOT
    / "orbital_core_stage1_validation_2026-09-15.json",
}
EXPECTED_SCHEMAS = {
    "clock": "moira.orbital-core-stage1.reader-clock-shift/v1",
    "frame": "moira.orbital-core-stage1.frame-shift/v1",
    "validation": "moira.orbital-core-stage1.validation/v1",
}
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?:[a-z]:[\\/])")


def _load(name: str) -> dict:
    return json.loads(ARTIFACTS[name].read_text(encoding="utf-8"))


def test_stage1_receipts_are_path_free_and_bind_identical_resources() -> None:
    for name, path in ARTIFACTS.items():
        rendered = path.read_text(encoding="utf-8")
        receipt = json.loads(rendered)
        assert receipt["schema"] == EXPECTED_SCHEMAS[name]
        assert not WINDOWS_ABSOLUTE_PATH.search(rendered)
        assert receipt["baseline_identity"]["resources"] == receipt[
            "candidate_identity"
        ]["resources"]
        assert receipt["baseline_identity"]["network_boundary"] == {
            "external_network_used": False,
            "moira_no_download": True,
        }
        assert receipt["candidate_identity"]["network_boundary"] == {
            "external_network_used": False,
            "moira_no_download": True,
        }
        revision = receipt["candidate_identity"]["source"]["revision"]
        assert revision not in {"unknown", "dfad306-worktree"}
        assert len(revision) >= 12


def test_reader_clock_receipt_proves_exactly_one_conversion() -> None:
    receipt = _load("clock")
    witness = receipt["clock_witness"]
    assert receipt["status"] == "review_ready"
    assert witness["all_legacy_replays_exact_to_1e_12"] is True
    assert witness["all_tt_adapters_exactly_once_to_1e_12"] is True
    assert witness["second_conversion_is_observably_distinct"] is True
    assert receipt["candidate_native_python_parity"]["within_1e_9"] is True
    assert len(receipt["probe_status"]["baseline"]) == 19
    assert set(receipt["probe_status"]["baseline"].values()) == {"ok"}
    assert set(receipt["probe_status"]["candidate"].values()) == {"ok"}


def test_frame_receipt_separates_matrix_and_combined_consumer_evidence() -> None:
    receipt = _load("frame")
    isolation = receipt["component_isolation"]
    assert receipt["status"] == "review_ready"
    assert "frame-only" in isolation["authority_matrix_comparison"]
    assert "combined" in isolation["consumer_comparison"]
    assert isolation["reader_clock_receipt_status"] == "review_ready"
    assert receipt["authority"] == "IAU SOFA Issue 2023-10-11 frozen fixture"


def test_validation_receipt_does_not_overstate_release_readiness() -> None:
    receipt = _load("validation")
    gates = receipt["test_gates"]
    counts = receipt["test_gate_counts"]
    assert receipt["status"] == "implementation_review_ready_release_blocked"
    assert receipt["required_probe_count"] == 19
    assert receipt["required_probes_green"] is True
    assert gates["targeted_stage1"] == "passed"
    assert gates["live_jpl_horizons"] == "passed"
    assert gates["documentation"] == "passed"
    assert gates["consumer_inventory"] == "passed"
    assert gates["git_diff_check"] == "passed"
    assert gates["native"] == "passed"
    assert gates["kernel_and_extraction"] == "passed"
    assert gates["full_catalog"].startswith("NOT RUN - full moira-asteroids")
    assert "pre-existing" in gates["non_external_network"]
    assert "baseline also reports 66 findings" in gates["changed_file_ruff"]
    assert gates["full_catalog"] in receipt["skips"]
    assert gates["full_catalog"] in receipt["blockers"]
    assert gates["non_external_network"] in receipt["blockers"]
    assert gates["changed_file_ruff"] in receipt["blockers"]
    assert receipt["no_download"] is True
    assert receipt["release_or_deployment_performed"] is False
    assert counts["compatibility_probes"] == {
        "baseline_green": 19,
        "candidate_green": 19,
    }
    assert counts["targeted_stage1"]["collected"] == 694
    assert counts["targeted_stage1"]["passed"] == 692
    assert counts["targeted_stage1"]["skipped"] == 2
    assert len(counts["targeted_stage1"]["skip_reasons"]) == 2
    assert counts["native"]["passed"] == 30
    assert counts["kernel_and_extraction"]["passed"] == 108
    assert counts["live_jpl_horizons"]["passed"] == 52
    assert counts["full_catalog"]["skipped"] == 1

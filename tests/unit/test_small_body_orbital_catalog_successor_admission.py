"""Governance for the October 29 successor small-body orbital admission.

The successor admits the sealed `moira-asteroids@2026.10.10.1` release against
the same frozen September 28 Horizons authority fixture, for the four asteroid
records only. The September receipt stays immutable; this test fails if its
content changes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ORACLE = ROOT / "tests" / "artifacts" / "oracle"
SUCCESSOR_PATH = ORACLE / "small_body_orbital_catalog_admission_2026-10-29.json"
PREDECESSOR_PATH = ORACLE / "small_body_orbital_catalog_admission_2026-09-28.json"
MANIFEST_PATH = (
    ROOT / "tests" / "fixtures" / "small_body_release_manifests"
    / "asteroids-2026.10.10.1.json"
)
# Canonical (sorted-key, compact) JSON hash, independent of line endings.
PREDECESSOR_CONTENT_SHA256 = (
    "537eac32fca5f738886a3afcd2d9a93efef4fa2bb8ae771071b2924e216ec04f"
)
ASTEROID_BODIES = ["Ceres", "Hektor", "Atira", "Apophis"]
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?<!http)(?<!htt)(?:[a-z]:[\\/])")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _content_sha256(payload: dict) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def test_predecessor_receipt_is_not_relabelled() -> None:
    predecessor = _load(PREDECESSOR_PATH)
    assert _content_sha256(predecessor) == PREDECESSOR_CONTENT_SHA256
    assert {
        (item["catalog_id"], item["catalog_version"])
        for item in predecessor["catalog_release_identity"]
    } == {("moira-asteroids", "2026.09.18.1"), ("moira-comets", "2026.07.28.1")}


def test_successor_binds_the_same_authority_and_unchanged_gates() -> None:
    rendered = SUCCESSOR_PATH.read_text(encoding="utf-8")
    successor = json.loads(rendered)
    predecessor = _load(PREDECESSOR_PATH)
    authority = successor["authority_fixture"]
    fixture_bytes = (ROOT / authority["path"]).read_bytes()

    assert successor["schema"] == "moira.small-body-orbital-catalog-admission/v1"
    assert successor["status"] == "admitted"
    assert not WINDOWS_ABSOLUTE_PATH.search(rendered)
    assert successor["predecessor"] == PREDECESSOR_PATH.relative_to(ROOT).as_posix()
    assert authority == predecessor["authority_fixture"]
    assert authority["sha256"] == hashlib.sha256(fixture_bytes).hexdigest()
    assert authority["bytes"] == len(fixture_bytes)
    assert successor["acceptance_gates"] == predecessor["acceptance_gates"]
    assert successor["gate_origin"] == predecessor["gate_origin"]
    assert set(successor["measured_maxima"]) == set(successor["acceptance_gates"])
    assert all(
        successor["measured_maxima"][field] < limit
        for field, limit in successor["acceptance_gates"].items()
    )


def test_successor_binds_the_archived_release_manifest_and_its_bodies() -> None:
    successor = _load(SUCCESSOR_PATH)
    manifest_bytes = MANIFEST_PATH.read_bytes()
    manifest = json.loads(manifest_bytes)
    fixture = json.loads(
        (ROOT / successor["authority_fixture"]["path"]).read_bytes()
    )
    records = {record["body"]: record for record in fixture["records"]}

    (release,) = successor["catalog_release_identity"]
    assert (release["catalog_id"], release["catalog_version"]) == (
        "moira-asteroids", "2026.10.10.1",
    )
    assert release["manifest_sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    assert release["body_count"] == manifest["body_count"]
    assert release["shard_count"] == manifest["shard_count"]
    assert release["sampling_base_step_days"] == manifest["sampling"]["base_step_days"]
    assert release["sampling_policy_version"] == manifest["sampling"]["policy_version"]
    assert release["authority_bodies"] == ASTEROID_BODIES
    assert release["authority_records"] == len(ASTEROID_BODIES)

    shard_of = {
        body_id: shard["path"]
        for shard in manifest["shards"]
        for body_id in shard["bodies"]
    }
    for body in ASTEROID_BODIES:
        assert successor["authority_shards"][body]["shard"] == shard_of[
            records[body]["body_naif_id"]
        ]
    assert set(successor["excluded_records"]) == set(records) - set(ASTEROID_BODIES)


def test_successor_records_its_scope_without_overstating_it() -> None:
    successor = _load(SUCCESSOR_PATH)
    assert successor["full_catalog_gate"]["status"] == "passed"
    assert successor["full_catalog_gate"]["bodies_passed"] == 11720
    assert successor["network_boundary"]["external_network_used"] is True
    assert successor["network_boundary"]["live_drift_audit_cases_total"] == 17
    assert successor["release_or_deployment_performed"] is False
    assert any(
        "not 11223 independent Horizons queries" in limitation
        for limitation in successor["limitations"]
    )
    assert any("not admitted" in limitation for limitation in successor["limitations"])

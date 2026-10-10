"""Adaptive Type-13 sampling policy for numbered periodic comets."""

from __future__ import annotations

import io
import hashlib
import json
from pathlib import Path
import urllib.error

import pytest

from scripts import build_comet_catalog


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_PROBE_PATH = (
    _REPOSITORY_ROOT
    / "tests"
    / "artifacts"
    / "oracle"
    / "comet_apsidal_sampling_probe_2026-09-28.json"
)
_ADMISSION_PATH = (
    _REPOSITORY_ROOT
    / "tests"
    / "artifacts"
    / "oracle"
    / "comet_type13_catalog_candidate_admission_2026-10-01.json"
)


def _states_with_radial_velocities(values: list[float]) -> list[list[float]]:
    count = len(values)
    return [
        [1.0] * count,
        [0.0] * count,
        [0.0] * count,
        values,
        [0.0] * count,
        [0.0] * count,
    ]


def test_adaptive_sampling_refines_both_radial_extrema() -> None:
    epochs = [0.0, 30.0, 60.0, 90.0]
    states = _states_with_radial_velocities([-1.0, 1.0, 1.0, -1.0])

    refinement, bracket_count = build_comet_catalog._extremum_refinement_epochs(
        epochs,
        states,
    )

    assert bracket_count == 2
    assert refinement[:3] == [0.0, 1.0, 2.0]
    assert refinement[-3:] == [88.0, 89.0, 90.0]
    assert refinement[34:37] == [34.0, 56.0, 57.0]
    assert len(refinement) == 70


def test_vector_merge_orders_nodes_and_replaces_duplicate_epochs() -> None:
    base_epochs = [0.0, 30.0, 60.0]
    base_states = [[axis + epoch for epoch in base_epochs] for axis in range(6)]
    extra_epochs = [29.0, 30.0, 31.0]
    extra_states = [
        [100.0 * axis + epoch for epoch in extra_epochs]
        for axis in range(6)
    ]

    epochs, states = build_comet_catalog._merge_vectors(
        base_epochs,
        base_states,
        [(extra_epochs, extra_states)],
    )

    assert epochs == [0.0, 29.0, 30.0, 31.0, 60.0]
    duplicate_index = epochs.index(30.0)
    assert [axis[duplicate_index] for axis in states] == [
        30.0,
        130.0,
        230.0,
        330.0,
        430.0,
        530.0,
    ]


def test_cached_shard_must_match_sampling_policy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    kernel_path = tmp_path / "comet_shard_000.bsp"
    metadata_path = tmp_path / "comet_shard_000.metadata.json"
    kernel_path.write_bytes(b"kernel")
    metadata = {
        "sampling_policy": build_comet_catalog._sampling_policy(),
        "records": [{"naif_id": 1_000_001}],
        "naif_map": {"1P/Halley": 1_000_001},
        "failures": [],
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    class FakeKernel:
        def __init__(self, path: Path) -> None:
            assert path == kernel_path

        def covered_bodies(self) -> tuple[int, ...]:
            return (1_000_001,)

        def close(self) -> None:
            pass

    monkeypatch.setattr(build_comet_catalog, "SmallBodyKernel", FakeKernel)
    assert build_comet_catalog._shard_cached(
        kernel_path,
        metadata_path,
        expected_naif_ids={1_000_001},
    ) == metadata
    assert (
        build_comet_catalog._shard_cached(
            kernel_path,
            metadata_path,
            expected_naif_ids={1_000_001, 1_000_002},
        )
        is None
    )

    metadata["sampling_policy"] = build_comet_catalog._sampling_policy()
    metadata["failures"] = [{"number": 2, "error": "synthetic failure"}]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert (
        build_comet_catalog._shard_cached(
            kernel_path,
            metadata_path,
            expected_naif_ids={1_000_001},
        )
        is None
    )

    metadata.pop("sampling_policy")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert (
        build_comet_catalog._shard_cached(
            kernel_path,
            metadata_path,
            expected_naif_ids={1_000_001},
        )
        is None
    )


def test_sampling_policy_declares_nonuniform_extremum_refinement() -> None:
    policy = build_comet_catalog._sampling_policy()

    assert policy == {
        "policy_version": "moira-comet-type13-apsidal-adaptive-v5",
        "mode": "certified_adaptive_radial_extrema",
        "base_step_days": 10,
        "initial_refinement_step_days": 1.0,
        "minimum_refinement_step_days": 0.0078125,
        "refinement_padding_days": 4.0,
        "refinement_request_max_span_days": 11688.0,
        "refined_extrema": ["PERICENTER", "APOCENTER"],
        "time_tags": "nonuniform",
        "integration_coherence": "every_exact_request_includes_coverage_endpoints",
        "window_size": 7,
        "horizons_tlist_limit": 10_000,
        "reserved_integration_anchor_epochs": 2,
        "certification": {
            "witness_step_ratio": 0.5,
            "distance_absolute_km": 0.1495978707,
            "event_time_absolute_seconds": 8.64,
            "failure_action": "halve_refinement_step_or_reject_body",
        },
    }


def test_comet_fetch_uses_the_comet_specific_refinement_floor(monkeypatch) -> None:
    epochs = [2451545.0, 2451555.0]
    states = _states_with_radial_velocities([1.0, 1.0])
    seen: dict[str, object] = {}

    monkeypatch.setattr(build_comet_catalog, "_fetch_raw", lambda *_args: "raw")
    monkeypatch.setattr(
        build_comet_catalog,
        "_parse_solution",
        lambda _raw: "JPL#TEST",
    )
    monkeypatch.setattr(
        build_comet_catalog,
        "_parse_vectors",
        lambda _raw: (epochs, states),
    )

    def fake_build(base_epochs, base_states, fetch_exact, **kwargs):
        seen.update(kwargs)
        return (
            base_epochs,
            base_states,
            {
                "status": "no_radial_extrema_in_coverage",
                "base_extremum_brackets": 0,
                "accepted_refinement_step_days": None,
                "levels": [],
                "passed": True,
            },
            [],
        )

    monkeypatch.setattr(
        build_comet_catalog.adaptive,
        "build_certified_adaptive_series",
        fake_build,
    )

    result = build_comet_catalog._fetch_comet(1)

    assert seen["minimum_refinement_step_days"] == 1.0 / 128.0
    assert result["sampling_policy"]["policy_version"] == (
        "moira-comet-type13-apsidal-adaptive-v5"
    )


def test_response_cache_directory_can_be_reused_across_policy_rebuilds(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "shared-cache"

    args = build_comet_catalog._parse_args(
        ["targets.json", "0", "497", str(tmp_path / "candidate"),
         "--response-cache-dir", str(cache_dir)]
    )

    assert args.response_cache_dir == cache_dir


def test_refinement_requests_are_bounded_by_count_and_time_span(
    monkeypatch,
) -> None:
    monkeypatch.setattr(build_comet_catalog, "HORIZONS_TLIST_LIMIT", 5)
    monkeypatch.setattr(
        build_comet_catalog,
        "REFINEMENT_REQUEST_MAX_SPAN_DAYS",
        10.0,
    )

    chunks = build_comet_catalog._refinement_request_chunks(
        [0.0, 1.0, 2.0, 9.0, 11.0, 12.0]
    )

    assert chunks == [[0.0, 1.0, 2.0], [9.0, 11.0, 12.0]]


def test_refinement_vectors_reserve_full_coverage_integration_anchors(
    monkeypatch,
) -> None:
    requested = [10.0, 11.0]
    seen: list[float] = []

    def fake_fetch(command: str, epochs: list[float]) -> str:
        assert command == "'DES=1P;NOFRAG;CAP'"
        seen.extend(epochs)
        return "raw"

    def fake_parse(raw: str) -> tuple[list[float], list[list[float]]]:
        assert raw == "raw"
        return seen, [[axis * 100.0 + epoch for epoch in seen] for axis in range(6)]

    monkeypatch.setattr(build_comet_catalog, "_fetch_tlist_raw", fake_fetch)
    monkeypatch.setattr(build_comet_catalog, "_parse_vectors", fake_parse)
    monkeypatch.setattr(
        build_comet_catalog,
        "_parse_solution",
        lambda raw: "JPL#TEST",
    )

    epochs, states, receipts = build_comet_catalog._fetch_refinement_vectors(
        "'DES=1P;NOFRAG;CAP'",
        requested,
        query_kind="test",
        coverage_anchor_epochs=(0.0, 100.0),
        expected_target_solution="JPL#TEST",
    )

    assert seen == [0.0, 10.0, 11.0, 100.0]
    assert epochs == requested
    assert states[0] == requested
    assert states[5] == [510.0, 511.0]
    assert receipts[0]["integration_anchor_epochs_jd_tdb"] == [0.0, 100.0]


def test_refinement_rejects_target_solution_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        build_comet_catalog,
        "_fetch_tlist_raw",
        lambda _command, _epochs: (
            "Target body name: 2P/Encke {source: JPL#NEW}"
        ),
    )

    with pytest.raises(RuntimeError, match="changed within one comet build"):
        build_comet_catalog._fetch_refinement_vectors(
            "'DES=2P;NOFRAG;CAP'",
            [10.0],
            coverage_anchor_epochs=(0.0, 100.0),
            expected_target_solution="JPL#OLD",
        )


def test_apsidal_sampling_probe_is_bound_to_current_authority_fixture() -> None:
    probe = json.loads(_PROBE_PATH.read_text(encoding="utf-8"))
    fixture_path = _REPOSITORY_ROOT / probe["authority"]["event_fixture"]

    assert hashlib.sha256(fixture_path.read_bytes()).hexdigest() == (
        probe["authority"]["event_fixture_sha256"]
    )
    assert probe["authority"]["target_solutions"] == {
        "1P/Halley": "JPL#75",
        "2P/Encke": "JPL#K273/17",
    }


def test_candidate_policy_passes_without_widening_stage2_gates() -> None:
    probe = json.loads(_PROBE_PATH.read_text(encoding="utf-8"))
    gates = probe["acceptance_gates"]

    assert not any(
        measurement["passed"]
        for measurement in probe["installed_release_baseline"]["measurements"]
    )
    for measurement in probe["candidate_policy"]["measurements"]:
        assert measurement["passed"] is True
        assert abs(measurement["event_time_delta_seconds"]) <= (
            gates["event_time_absolute_seconds"]
        )
        assert abs(measurement["distance_delta_au"]) <= (
            gates["distance_absolute_au"]
        )
    assert probe["diagnosis"]["fixture_gate_widened"] is False


def test_final_candidate_admission_keeps_strict_anchored_oracle_gates() -> None:
    receipt = json.loads(_ADMISSION_PATH.read_text(encoding="utf-8"))

    assert receipt["status"] == "candidate_validated_not_release_admitted"
    assert receipt["catalog"]["body_count"] == 497
    assert receipt["catalog"]["shard_count"] == 20
    assert receipt["catalog"]["sampling_policy_version"] == (
        "moira-comet-type13-apsidal-adaptive-v5"
    )
    assert receipt["acceptance_gates"] == {
        "event_time_absolute_seconds": 8.64,
        "distance_absolute_au": 1.0e-9,
        "origin": "pre-existing Stage 2 gates; not widened",
    }
    assert all(
        measurement["passed"] is True
        for measurement in receipt["anchored_apsidal_oracle"]["measurements"]
    )
    assert receipt["refresh_integrity"] == {
        "first_generation": {
            "replaced_bodies": 23,
            "preserved_raw_node_tables_exact": 474,
        },
        "second_generation": {
            "replaced_bodies": 1,
            "preserved_raw_node_tables_exact": 496,
        },
        "all_manifest_kernel_and_metadata_hashes_verified": True,
        "all_certificates_passed": True,
        "exact_roster_verified": True,
    }


def test_transient_horizons_response_is_retried(monkeypatch) -> None:
    attempts = 0

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def read(self) -> bytes:
            return b"ok"

    def _urlopen(request, timeout: int):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise urllib.error.HTTPError(
                str(request), 503, "Service Unavailable", {}, io.BytesIO()
            )
        return _Response()

    monkeypatch.setattr(build_comet_catalog.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(build_comet_catalog.time, "sleep", lambda delay: None)

    assert build_comet_catalog._read_request("https://example.invalid", timeout=1) == "ok"
    assert attempts == 2


def test_installed_master_can_supply_rebuild_targets(tmp_path: Path) -> None:
    master = tmp_path / "comet_master.json"
    master.write_text(
        json.dumps(
            {
                "records": [
                    {"number": 1, "name": "1P/Halley", "naif_id": 1_000_001},
                    {"number": 2, "full_name": "2P/Encke", "naif_id": 1_000_002},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert build_comet_catalog._load_targets(master) == [
        {"number": 1, "full_name": "1P/Halley"},
        {"number": 2, "full_name": "2P/Encke"},
    ]

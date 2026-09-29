import io
import hashlib
import json
from pathlib import Path
import sys
import urllib.error

from scripts import build_unified_asteroid_catalog as catalog_builder


def _stub_parsed_vectors(_raw: str) -> tuple[list[float], list[list[float]]]:
    return [2451545.0], [[float(axis)] for axis in range(6)]


def test_observation_arc_limited_body_uses_jpl_sbdb_bounds(monkeypatch) -> None:
    fetched: list[tuple[str, str, str]] = []
    provenance = {
        "start": "1930-12-13",
        "stop": "2026-04-15",
        "authority": "JPL SBDB",
        "orbit_id": "578",
        "solution_date": "2026-04-16 05:49:08",
    }

    monkeypatch.setattr(catalog_builder, "_fetch_observation_arc", lambda number: provenance)
    monkeypatch.setattr(
        catalog_builder,
        "_fetch_raw",
        lambda command, start, stop: fetched.append((command, start, stop)) or "raw",
    )
    monkeypatch.setattr(catalog_builder, "_parse_vectors", _stub_parsed_vectors)
    monkeypatch.setattr(catalog_builder, "_parse_name", lambda raw, number: "Apollo")

    body = catalog_builder._fetch_body(1862)

    assert fetched == [("1862;", "1930-12-13", "2026-04-15")]
    assert body["clamped"] is True
    assert body["coverage_policy"] == "jpl_sbdb_observation_arc"
    assert body["coverage_provenance"] == provenance


def test_regular_body_keeps_uniform_catalog_window(monkeypatch) -> None:
    fetched: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        catalog_builder,
        "_fetch_raw",
        lambda command, start, stop: fetched.append((command, start, stop)) or "raw",
    )
    monkeypatch.setattr(catalog_builder, "_parse_vectors", _stub_parsed_vectors)
    monkeypatch.setattr(catalog_builder, "_parse_name", lambda raw, number: "Ceres")
    monkeypatch.setattr(
        catalog_builder,
        "_fetch_observation_arc",
        lambda number: (_ for _ in ()).throw(AssertionError("SBDB must not be queried")),
    )

    body = catalog_builder._fetch_body(1)

    assert fetched == [("1;", *catalog_builder.WINDOW)]
    assert body["clamped"] is False
    assert "coverage_policy" not in body


def test_adaptive_roster_body_uses_shared_certifier(monkeypatch) -> None:
    number = next(iter(catalog_builder.ADAPTIVE_BODY_NUMBERS))
    called = False

    monkeypatch.setattr(catalog_builder, "_fetch_raw", lambda *args: "raw")
    monkeypatch.setattr(catalog_builder, "_parse_vectors", _stub_parsed_vectors)
    monkeypatch.setattr(catalog_builder, "_parse_name", lambda raw, value: "adaptive")

    def fake_certifier(base_epochs, base_states, fetch_exact, **kwargs):
        nonlocal called
        called = True
        assert kwargs["window_size"] == catalog_builder.WINDOW_SIZE
        return base_epochs, base_states, {"passed": True}, []

    monkeypatch.setattr(
        catalog_builder.adaptive,
        "build_certified_adaptive_series",
        fake_certifier,
    )

    body = catalog_builder._fetch_body(number)

    assert called is True
    assert body["apsidal_sampling_certificate"] == {"passed": True}


def test_exact_vectors_reserve_full_coverage_integration_anchors(monkeypatch) -> None:
    requested = [10.0, 11.0]
    seen: list[float] = []

    def fake_fetch(command: str, epochs: list[float]) -> str:
        assert command == "2340;"
        seen.extend(epochs)
        return "raw"

    def fake_parse(raw: str) -> tuple[list[float], list[list[float]]]:
        assert raw == "raw"
        return seen, [[axis * 100.0 + epoch for epoch in seen] for axis in range(6)]

    monkeypatch.setattr(catalog_builder, "_fetch_tlist_raw", fake_fetch)
    monkeypatch.setattr(catalog_builder, "_parse_vectors", fake_parse)

    epochs, states, receipts = catalog_builder._fetch_exact_vectors(
        "2340;",
        requested,
        query_kind="test",
        coverage_anchor_epochs=(0.0, 100.0),
    )

    assert seen == [0.0, 10.0, 11.0, 100.0]
    assert epochs == requested
    assert states[0] == requested
    assert states[5] == [510.0, 511.0]
    assert receipts[0]["integration_anchor_epochs_jd_tdb"] == [0.0, 100.0]


def test_adaptive_roster_exactly_matches_bound_audit_repair_scope() -> None:
    roster_path = catalog_builder.ADAPTIVE_ROSTER_PATH
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    audit_path = catalog_builder.ROOT / roster["source_audit"]
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    repair_scope = audit["repair_scope"]

    assert hashlib.sha256(audit_path.read_bytes()).hexdigest() == (
        roster["source_audit_sha256"]
    )
    assert set(roster["body_numbers"]) == {
        body["number"] for body in repair_scope["bodies"]
    }
    assert set(roster["shard_indices"]) == set(repair_scope["shard_indices"])
    assert roster["body_count"] == repair_scope["body_count"] == 59
    assert roster["shard_count"] == repair_scope["shard_count"] == 40


def test_unaffected_seed_is_audited_migrated_and_resumable(tmp_path: Path) -> None:
    source = tmp_path / "source"
    candidate = tmp_path / "candidate"
    source.mkdir()
    candidate.mkdir()
    targets = [
        {"number": number, "family": None, "families": []}
        for number in range(1, 26)
    ]
    kernel = source / "asteroid_shard_000.bsp"
    metadata = source / "asteroid_shard_000.metadata.json"
    kernel.write_bytes(b"kernel")
    metadata_payload = {
        "shard": 0,
        "kernel": kernel.name,
        "kernel_bytes": kernel.stat().st_size,
        "window": list(catalog_builder.WINDOW),
        "step_days": catalog_builder.STEP_DAYS,
        "window_size": catalog_builder.WINDOW_SIZE,
        "records": [
            {
                "number": number,
                "naif_id": 2_000_000 + number,
                "name": f"Body {number}",
                "nodes": 100,
            }
            for number in range(1, 26)
        ],
        "failures": [],
        "naif_map": {
            f"Body {number}": 2_000_000 + number for number in range(1, 26)
        },
    }
    metadata.write_text(json.dumps(metadata_payload), encoding="utf-8")
    manifest = {
        "body_count": 25,
        "shards": [
            {
                "index": 0,
                "path": kernel.name,
                "body_count": 25,
                "bodies": [2_000_000 + number for number in range(1, 26)],
                "sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
                "metadata": {
                    "path": metadata.name,
                    "sha256": hashlib.sha256(metadata.read_bytes()).hexdigest(),
                },
            }
        ],
    }
    (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    first = catalog_builder._seed_unaffected_catalog(source, candidate, targets)
    second = catalog_builder._seed_unaffected_catalog(source, candidate, targets)

    migrated = json.loads(
        (candidate / metadata.name).read_text(encoding="utf-8")
    )
    assert first["unaffected_shards_seeded"] == 1
    assert second["unaffected_shards_resumed"] == 1
    assert (candidate / kernel.name).read_bytes() == b"kernel"
    assert migrated["sampling_policy"] == catalog_builder._sampling_policy()
    assert all(record["adaptive_nodes"] == 0 for record in migrated["records"])
    assert all(
        record["apsidal_sampling_certificate"]["passed"] is True
        for record in migrated["records"]
    )


def test_regular_body_accumulates_sequential_horizons_range_limits(monkeypatch) -> None:
    fetched: list[tuple[str, str, str]] = []
    responses = {
        catalog_builder.WINDOW: (
            'No ephemeris for target "101955 Bennu (1999 RQ36)" '
            "prior to A.D. 1900-JAN-02 00:00:00.0000 TDB"
        ),
        ("1901-01-01", "2500-01-01"): (
            'No ephemeris for target "101955 Bennu (1999 RQ36)" '
            "after A.D. 2135-SEP-30 00:00:00.0000 TDB"
        ),
        ("1901-01-01", "2134-01-01"): "vectors",
    }

    def _fetch_raw(command: str, start: str, stop: str) -> str:
        fetched.append((command, start, stop))
        return responses[(start, stop)]

    def _parse_vectors(raw: str) -> tuple[list[float], list[list[float]]]:
        if raw != "vectors":
            raise RuntimeError("no $$SOE/$$EOE")
        return _stub_parsed_vectors(raw)

    monkeypatch.setattr(catalog_builder, "_fetch_raw", _fetch_raw)
    monkeypatch.setattr(catalog_builder, "_parse_vectors", _parse_vectors)
    monkeypatch.setattr(catalog_builder, "_parse_name", lambda raw, number: "Bennu")

    body = catalog_builder._fetch_body(101955)

    assert fetched == [
        ("101955;", *catalog_builder.WINDOW),
        ("101955;", "1901-01-01", "2500-01-01"),
        ("101955;", "1901-01-01", "2134-01-01"),
    ]
    assert body["clamped"] is True
    assert body["start"] == "1901-01-01"
    assert body["stop"] == "2134-01-01"


def test_tighter_catalog_sampling_policy_is_the_default() -> None:
    assert catalog_builder.STEP_DAYS == 10
    assert catalog_builder.WINDOW_SIZE == 7


def test_cached_metadata_requires_exact_build_policy_and_membership() -> None:
    meta = {
        "window": list(catalog_builder.WINDOW),
        "step_days": 10,
        "window_size": 7,
        "sampling_policy": catalog_builder._sampling_policy(),
        "records": [{"number": 1}, {"number": 33}],
        "failures": [],
    }

    assert catalog_builder._metadata_matches_build(meta, {1, 33}) is True

    meta["step_days"] = 30
    assert catalog_builder._metadata_matches_build(meta, {1, 33}) is False
    meta["step_days"] = 10

    assert catalog_builder._metadata_matches_build(meta, {1}) is False
    meta["failures"] = [{"number": 33, "error": "transient failure"}]
    assert catalog_builder._metadata_matches_build(meta, {1, 33}) is False


def test_four_hour_runtime_limit_is_admitted(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_unified_asteroid_catalog.py",
            "targets.json",
            "0",
            "1",
            "--max-runtime-hours",
            "4",
        ],
    )

    args = catalog_builder._parse_args()

    assert args.max_runtime_hours == 4.0


def test_transient_jpl_response_is_retried(monkeypatch) -> None:
    attempts = 0

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def read(self) -> bytes:
            return b"ok"

    def _urlopen(url: str, timeout: int):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise urllib.error.HTTPError(url, 502, "Bad Gateway", {}, io.BytesIO())
        return _Response()

    monkeypatch.setattr(catalog_builder.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(catalog_builder.time, "sleep", lambda delay: None)

    assert catalog_builder._read_url("https://example.invalid", timeout=1) == "ok"
    assert attempts == 2


def test_limited_cached_record_must_match_current_sbdb_solution(monkeypatch) -> None:
    current = {
        "start": "1930-12-13",
        "stop": "2026-04-15",
        "authority": "JPL SBDB",
        "orbit_id": "578",
        "solution_date": "2026-04-16 05:49:08",
    }
    monkeypatch.setattr(catalog_builder, "_fetch_observation_arc", lambda number: current)
    record = {
        "number": 1862,
        "start": current["start"],
        "stop": current["stop"],
        "coverage_policy": "jpl_sbdb_observation_arc",
        "coverage_provenance": current,
    }

    assert catalog_builder._limited_record_is_current(record) is True
    record["coverage_provenance"] = {**current, "orbit_id": "577"}
    assert catalog_builder._limited_record_is_current(record) is False

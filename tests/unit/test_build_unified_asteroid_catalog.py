import io
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

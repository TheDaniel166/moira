"""REST contract and installed-kernel tests for the planetary moon routes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest

from moira._kernel_paths import find_kernel
from moira.constants import J2000
from moira.julian import tdb_to_tt, tt_to_tdb
from moira.planetary_moon_events import find_planetary_moon_events
from moira.planetary_moons import PlanetaryMoons
from moira.spk_reader import S_PER_DAY
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback
SNAPSHOT = "/v1/planetary-moons/snapshot"
COVERAGE = "/v1/planetary-moons/coverage"
EVENTS = "/v1/planetary-moons/events"


@pytest.fixture
def client():
    with TestClient(create_app(ServerConfig())) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def manifest_path():
    path = os.getenv("MOIRA_TEST_PLANETARY_MOONS_MANIFEST")
    if path is None:
        pytest.skip("Set MOIRA_TEST_PLANETARY_MOONS_MANIFEST for the installed kernel tests")
    return Path(path)


@pytest.fixture(scope="module")
def installed_client(manifest_path):
    config = ServerConfig(planetary_moons_manifest=str(manifest_path))
    with TestClient(create_app(config)) as test_client:
        yield test_client


def _assert_error(response, status, code):
    assert response.status_code == status, response.text
    payload = response.json()
    assert payload["error_code"] == code
    assert payload["request_id"] == response.headers["X-Request-ID"]


def test_openapi_and_manifest_configuration(client, monkeypatch):
    monkeypatch.setenv("MOIRA_SERVER_PLANETARY_MOONS_MANIFEST", "local-manifest.json")
    assert ServerConfig.from_env().planetary_moons_manifest == "local-manifest.json"
    schema = client.get("/openapi.json").json()
    post = schema["paths"][SNAPSHOT]["post"]
    get = schema["paths"][COVERAGE]["get"]
    assert post["tags"] == get["tags"] == ["planetary-moons"]
    assert {"200", "422", "503"} <= post["responses"].keys()
    assert {"200", "503"} <= get["responses"].keys()
    assert post["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/PlanetaryMoonsSnapshotRequest"
    )
    assert get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/PlanetaryMoonsCoverageResponse"
    )


@pytest.mark.parametrize("body", [
    {},
    {"jd_tt": True},
    {"jd_tt": "2451545.0"},
    {"jd_tt": 2451545.0, "planet": "Mars"},
    {"jd_tt": 2451545.0, "manifest_path": "local-manifest.json"},
])
def test_snapshot_input_validation(client, body):
    _assert_error(client.post(SNAPSHOT, json=body), 422, "validation_error")


def test_nonfinite_epoch(client):
    response = client.post(
        SNAPSHOT, content='{"jd_tt": 1e999}', headers={"Content-Type": "application/json"},
    )
    _assert_error(response, 422, "validation_error")


def test_routes_require_configuration(client, jd_j2000):
    _assert_error(client.get(COVERAGE), 503, "server_not_configured")
    _assert_error(client.post(SNAPSHOT, json={"jd_tt": jd_j2000}), 503, "server_not_configured")
    _assert_error(client.post(EVENTS, json={"jd_start_tt": jd_j2000, "jd_end_tt": jd_j2000 + 1}),
                  503, "server_not_configured")


def test_event_windows_and_next_use_admitted_context(installed_client, manifest_path):
    seed = tdb_to_tt(J2000 + 848908869.1829523 / S_PER_DAY)
    request = {
        "jd_start_tt": seed - 0.25, "jd_end_tt": seed + 0.25,
        "planet": "Jupiter", "moon_ids": [503], "kinds": ["transit"],
    }
    with PlanetaryMoons.open(de441_path=find_kernel("de441.bsp"), manifest_path=manifest_path) as context:
        expected = find_planetary_moon_events(
            context, request["jd_start_tt"], request["jd_end_tt"], planet="Jupiter",
            moon_ids=(503,), kinds=("transit",),
        )
    assert expected.status == "complete" and len(expected.events) == 1
    for mode in ("window", "next"):
        response = installed_client.post(EVENTS, json={**request, "mode": mode})
        assert response.status_code == 200, response.text
        result = response.json()["result"]
        assert result["status"] == "complete"
        event, = result["events"]
        assert event["naif_id"] == 503
        assert event["start_jd_tt"] == expected.events[0].start_jd_tt < seed
        assert event["end_jd_tt"] == expected.events[0].end_jd_tt > seed
        assert event["contacts"][0]["kind"] == "ingress"
        assert event["contacts"][-1]["kind"] == "egress"


def test_event_window_failure_contracts(installed_client, manifest_path, jd_j2000):
    response = installed_client.post(EVENTS, json={"jd_start_tt": jd_j2000, "jd_end_tt": jd_j2000 - 1})
    _assert_error(response, 422, "validation_error")
    budget = installed_client.post(EVENTS, json={
        "jd_start_tt": jd_j2000, "jd_end_tt": jd_j2000 + 1, "moon_ids": [501],
        "mode": "next", "max_evaluations": 1,
    })
    assert budget.status_code == 200, budget.text
    assert budget.json()["result"]["status"] == "evaluation_budget"
    assert budget.json()["result"]["events"] == []
    limited = installed_client.post(EVENTS, json={
        "jd_start_tt": jd_j2000, "jd_end_tt": jd_j2000 + 4,
        "planet": "Jupiter", "moon_ids": [501], "max_results": 1,
    })
    assert limited.status_code == 200, limited.text
    assert limited.json()["result"]["status"] == "result_limit"
    assert len(limited.json()["result"]["events"]) == 1
    with PlanetaryMoons.open(de441_path=find_kernel("de441.bsp"), manifest_path=manifest_path) as context:
        earliest = context.coverage_tdb()["Saturn"][0][0]
    response = installed_client.post(EVENTS, json={
        "jd_start_tt": tdb_to_tt(earliest - 0.02), "jd_end_tt": tdb_to_tt(earliest + 0.02),
        "planet": "Saturn",
    })
    _assert_error(response, 422, "planetary_moons_epoch_out_of_coverage")


def test_event_window_requires_contiguous_coverage(installed_client, jd_j2000, monkeypatch):
    epoch = tt_to_tdb(jd_j2000)
    monkeypatch.setattr(PlanetaryMoons, "coverage_tdb", lambda self: {
        "Jupiter": ((epoch - 1, epoch + 0.25), (epoch + 0.75, epoch + 2)),
    })
    response = installed_client.post(EVENTS, json={
        "jd_start_tt": jd_j2000, "jd_end_tt": jd_j2000 + 1, "planet": "Jupiter",
    })
    _assert_error(response, 422, "planetary_moons_epoch_out_of_coverage")


@pytest.mark.parametrize("contents", [None, "not JSON", "{}"])
def test_unavailable_manifest_does_not_leak_path(tmp_path, contents, jd_j2000):
    manifest = tmp_path / "operator-manifest.json"
    if contents is not None:
        manifest.write_text(contents, encoding="utf-8")
    config = ServerConfig(planetary_moons_manifest=str(manifest))
    with TestClient(create_app(config)) as test_client:
        for response in (
            test_client.get(COVERAGE),
            test_client.post(SNAPSHOT, json={"jd_tt": jd_j2000}),
        ):
            _assert_error(response, 503, "kernel_not_ready")
            assert manifest.name not in response.text


def test_installed_snapshot_and_coverage(installed_client, manifest_path, jd_j2000):
    expected_kernel = find_kernel("de441.bsp")
    with PlanetaryMoons.open(de441_path=expected_kernel, manifest_path=manifest_path) as moons:
        expected_coverage = moons.coverage_tdb()
        expected = moons.at(jd_j2000)

    response = installed_client.get(COVERAGE)
    assert response.status_code == 200, response.text
    coverage = response.json()["systems"]
    assert [(item["planet"], [
        (span["start_jd_tdb"], span["end_jd_tdb"]) for span in item["intervals_tdb"]
    ]) for item in coverage] == [(planet, list(spans)) for planet, spans in expected_coverage.items()]

    response = installed_client.post(SNAPSHOT, json={"jd_tt": jd_j2000})
    assert response.status_code == 200, response.text
    snapshot = response.json()
    assert (snapshot["jd_tt"], snapshot["jd_tdb"]) == (expected.jd_tt, expected.jd_tdb)
    assert (snapshot["de441_sha256"], snapshot["figure_pck_sha256"]) == (
        expected.de441_sha256, expected.figure_pck_sha256,
    )
    assert [source["planet"] for source in snapshot["sources"]] == ["Jupiter", "Saturn"]
    for source, receipt in zip(snapshot["sources"], expected.sources, strict=True):
        assert source["source_url"] == receipt.source_url
        assert source["source_sha256"] == receipt.source_sha256
        assert source["extract_sha256"] == receipt.extract_sha256
    assert len(snapshot["moons"]) == 12
    for row, moon in zip(snapshot["moons"], expected.moons, strict=True):
        assert row["naif_id"] == moon.naif_id
        assert row["position_km"] == list(moon.position_km)
        assert row["velocity_km_per_day"] == list(moon.velocity_km_per_day)
        assert row["earth_view"]["side"] == moon.earth_view.side
        assert row["earth_view"]["event"] == moon.earth_view.event
        assert row["phase"]["illuminated_fraction"] == moon.phase.illuminated_fraction
        assert row["eclipse"] == moon.eclipse

    saturn_start = expected_coverage["Saturn"][0][0]
    response = installed_client.post(SNAPSHOT, json={
        "jd_tt": tdb_to_tt(saturn_start + 1.0 / S_PER_DAY), "planet": "Saturn",
    })
    _assert_error(response, 422, "planetary_moons_epoch_out_of_coverage")


@pytest.mark.parametrize("seconds_tdb,planet,transits,occulted", [
    (288757566.1853102, "Saturn", {601, 602, 604, 606}, None),
    (848908869.1829523, "Jupiter", {503}, None),
    (849214869.1830335, "Jupiter", set(), 503),
    (849214869.1830335, "Saturn", set(), 601),
])
def test_observed_and_reference_events(installed_client, seconds_tdb, planet, transits, occulted):
    # These reception epochs match the independently checked CSPICE cases.
    response = installed_client.post(SNAPSHOT, json={
        "jd_tt": tdb_to_tt(J2000 + seconds_tdb / S_PER_DAY), "planet": planet,
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert [receipt["planet"] for receipt in payload["sources"]] == [planet]
    moons = {moon["naif_id"]: moon for moon in payload["moons"]}
    assert len(moons) == (4 if planet == "Jupiter" else 8)
    assert {body for body, moon in moons.items() if moon["earth_view"]["event"] == "transit"} == transits
    if occulted is not None:
        assert moons[occulted]["earth_view"]["event"] == "occultation"
    if occulted == 601:
        assert moons[601]["eclipse"] == "total"


def test_single_system_installation(manifest_path, tmp_path, jd_j2000):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    jupiter = manifest["systems"]["Jupiter"]
    manifest["systems"] = {"Jupiter": jupiter}
    single_manifest = tmp_path / "manifest.json"
    single_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    source = manifest_path.parent / jupiter["filename"]
    extract = tmp_path / source.name
    try:
        os.link(source, extract)
    except OSError:
        shutil.copyfile(source, extract)

    config = ServerConfig(planetary_moons_manifest=str(single_manifest))
    with TestClient(create_app(config)) as test_client:
        coverage = test_client.get(COVERAGE)
        assert coverage.status_code == 200, coverage.text
        assert [item["planet"] for item in coverage.json()["systems"]] == ["Jupiter"]
        snapshot = test_client.post(SNAPSHOT, json={"jd_tt": jd_j2000, "planet": "Jupiter"})
        assert snapshot.status_code == 200, snapshot.text
        assert len(snapshot.json()["moons"]) == 4
        _assert_error(test_client.post(SNAPSHOT, json={"jd_tt": jd_j2000}), 503, "kernel_not_ready")
        _assert_error(
            test_client.post(SNAPSHOT, json={"jd_tt": jd_j2000, "planet": "Saturn"}),
            503, "kernel_not_ready",
        )
        window = {"jd_start_tt": jd_j2000, "jd_end_tt": jd_j2000 + 0.1}
        jupiter_events = test_client.post(EVENTS, json={**window, "planet": "Jupiter"})
        assert jupiter_events.status_code == 200, jupiter_events.text
        assert jupiter_events.json()["result"]["status"] == "complete"
        _assert_error(
            test_client.post(EVENTS, json={**window, "planet": "Saturn"}),
            503, "kernel_not_ready",
        )

"""FastAPI transport checks for the native multi-epoch SPK reader."""

from __future__ import annotations

from hashlib import sha256
import math
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira import spk_reader
from moira.constants import C_KM_PER_DAY
from moira.spk_reader import KernelPool, SpkReader
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.dependencies import get_engine
from tests.unit.test_planets_architecture_invariants import _write_planetary_seam_kernel


pytestmark = pytest.mark.loopback

_J2000_TDB = 2_451_545.0
_EARTH = [[0, 3], [3, 399]]
_MARS = [[0, 4]]
_SUN = [[0, 10]]
_STATES = "/v1/batch/spk/states"
_LIGHT = "/v1/batch/spk/received-light"


@pytest.fixture(scope="module")
def spk_client(tmp_path_factory):
    """Start the actual server on a configured kernel with a sub-JD-tick emission seam."""
    kernel = tmp_path_factory.mktemp("server-spk") / "configured-seam.bsp"
    delay_days = math.hypot(40e6, 80e6) / C_KM_PER_DAY
    seam_et = -delay_days * 86_400 - 5e-6
    _write_planetary_seam_kernel(
        kernel,
        mars_override_interval=(seam_et, 86_400.0),
        distant_mars=True,
        moving_earth=True,
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira._kernel_paths.find_planetary_kernel", lambda: None)
        patch.setattr("moira._kernel_paths.find_all_small_body_manifests", lambda: ())
        patch.setattr(spk_reader, "_reader", None)
        patch.setattr(spk_reader, "_reader_path", None)
        app = create_app(ServerConfig(kernel_path=str(kernel)))
        try:
            with TestClient(app) as client:
                reader = app.state.engine._reader
                assert reader.path == kernel
                yield client, reader
        finally:
            engine = getattr(app.state, "engine", None)
            if engine is not None and engine._reader_obj is not None:
                engine._reader_obj.close()
            spk_reader.reset_singleton()


def test_spk_states_match_the_native_grid_and_type3_velocity(spk_client):
    client, reader = spk_client
    epochs = [_J2000_TDB + 0.125, _J2000_TDB - 0.5, _J2000_TDB, _J2000_TDB + 0.125]
    routes = [_MARS, _EARTH]
    response = client.post(_STATES, json={"routes": routes, "epochs_tdb": epochs})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kernel_sha256"] == sha256(reader.path.read_bytes()).hexdigest()
    assert body["kernel_label"] == reader._source_identity.label
    assert (body["frame"], body["time_scale"]) == ("ICRF", "TDB")
    assert body["states"] == reader.states_tdb_batch(routes, epochs).tolist()
    assert [row[1] for row in body["states"][0]] == [180e6, 182e6, 180e6, 180e6]
    assert body["states"][1][2] == [50e6, 100e6, 0.0, 21_600.0, 0.0, 0.0]


def test_spk_received_light_matches_the_native_grid_across_emission_seam(spk_client):
    client, reader = spk_client
    before = math.nextafter(_J2000_TDB, -math.inf)
    epochs = [_J2000_TDB, before, _J2000_TDB + 0.125, _J2000_TDB]
    targets = [_MARS, _SUN]
    response = client.post(
        _LIGHT,
        json={"observer_route": _EARTH, "target_routes": targets, "epochs_tdb": epochs},
    )

    assert response.status_code == 200, response.text
    rows = response.json()["received_light"]
    assert rows == reader.received_light_tdb_batch(_EARTH, targets, epochs).tolist()
    assert [row[1] for row in rows[0]] == [80e6, 82e6, 80e6, 80e6]
    assert rows[0][0][3] == pytest.approx(math.hypot(40e6, 80e6) / C_KM_PER_DAY, abs=1e-17, rel=0)


def test_spk_gaps_fail_the_whole_batch_on_the_primary_reader(spk_client, tmp_path, monkeypatch):
    client, source = spk_client
    gap_kernel = tmp_path / "gapped-primary.bsp"
    _write_planetary_seam_kernel(
        gap_kernel,
        mars_override_interval=(-100.0, 86_400.0),
        distant_mars=True,
        mars_base_interval=(-86_400.0, -400.0),
    )
    with KernelPool([SpkReader(gap_kernel), SpkReader(source.path)]) as pool:
        monkeypatch.setitem(client.app.dependency_overrides, get_engine, lambda: SimpleNamespace(_reader=pool))
        valid_epoch = _J2000_TDB + 0.5
        reception = client.post(_STATES, json={"routes": [_MARS], "epochs_tdb": [valid_epoch, _J2000_TDB]})
        assert reception.status_code == 200, reception.text
        assert reception.json()["kernel_sha256"] == sha256(gap_kernel.read_bytes()).hexdigest()

        states = client.post(
            _STATES,
            json={"routes": [_MARS], "epochs_tdb": [valid_epoch, _J2000_TDB - 256.0 / 86_400]},
        )
        light = client.post(
            _LIGHT,
            json={"observer_route": _EARTH, "target_routes": [_MARS], "epochs_tdb": [valid_epoch, _J2000_TDB]},
        )

    for response in (states, light):
        assert response.status_code == 422, response.text
        body = response.json()
        assert body["error_code"] == "validation_error"
        assert body["request_id"] == response.headers["X-Request-ID"]
        assert "No SPK segment covers center=0, target=4" in body["message"]
    assert "offset -" in light.json()["message"]


@pytest.mark.parametrize(
    ("endpoint", "payload", "message_fragment"),
    [
        (_STATES, {"routes": [_MARS], "epochs_tdb": []}, "at least 1"),
        (_STATES, {"routes": [_MARS], "epochs_tdb": ["2451545.0"]}, "valid number"),
        (_STATES, {"routes": [[[0, True]]], "epochs_tdb": [_J2000_TDB]}, "valid integer"),
        (_STATES, {"routes": [[[0, 2**31]]], "epochs_tdb": [_J2000_TDB]}, "2147483647"),
        (_STATES, {"routes": [[[0, 3], [0, 4]]], "epochs_tdb": [_J2000_TDB]}, "contiguous"),
        (_STATES, {"routes": [_MARS], "epochs_tdb": [_J2000_TDB] * 16_385}, "16384"),
        (_STATES, {"routes": [_MARS] * 11, "epochs_tdb": [_J2000_TDB] * 16_384}, "163840"),
        (
            _LIGHT,
            {"observer_route": [[3, 399]], "target_routes": [_MARS], "epochs_tdb": [_J2000_TDB]},
            "barycenter",
        ),
    ],
)
def test_spk_rejects_invalid_or_oversized_requests(spk_client, endpoint, payload, message_fragment):
    client, _ = spk_client
    response = client.post(endpoint, json=payload)
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "validation_error"
    assert message_fragment in response.json()["message"]


def test_spk_rejects_nonfinite_epoch(spk_client):
    client, _ = spk_client
    response = client.post(
        _STATES,
        content='{"routes": [[[0, 4]]], "epochs_tdb": [1e309]}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422, response.text
    assert "finite" in response.json()["message"]


def test_spk_reports_missing_primary_kernel(monkeypatch):
    monkeypatch.setattr("moira._kernel_paths.find_planetary_kernel", lambda: None)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        response = client.post(_STATES, json={"routes": [_MARS], "epochs_tdb": [_J2000_TDB]})
    assert response.status_code == 503, response.text
    assert response.json()["error_code"] == "kernel_not_ready"


def test_spk_batches_are_discoverable_in_openapi(spk_client):
    client, _ = spk_client
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    paths = response.json()["paths"]
    for endpoint in (_STATES, _LIGHT):
        operation = paths[endpoint]["post"]
        assert operation["tags"] == ["batch"]
        for status in ("422", "503"):
            error = operation["responses"][status]["content"]["application/json"]["schema"]
            assert error["$ref"] == "#/components/schemas/ErrorEnvelope"

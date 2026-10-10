"""Real HTTP adversarial repair acceptance, separate from source arithmetic."""

import math
import pytest
from fastapi.testclient import TestClient
from moira.constants import SIGNS
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]


@pytest.fixture(scope="module")
def client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
        with TestClient(
            create_app(ServerConfig(prewarm_enabled=False)),
            raise_server_exceptions=False,
        ) as c:
            yield c


def post(c, path, payload):
    r = c.post(path, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("dt", ["2000-05-18T00:00:00Z", "2020-12-21T12:00:00Z"])
def test_real_war_full_lagna_and_supplied_roundtrip(client, dt):
    payload = {
        "dt": dt,
        "observer_lat": 28.6,
        "observer_lon": 77.2,
        "house_system": "O",
    }
    full = post(client, "/v1/shadbala/chart/full", payload)
    chart = full["chart"]
    ledger = chart["war_resolution"]
    assert ledger["pairs"] and ledger["pairs"] == full["network"]["active_wars"]
    assert abs(math.fsum(v for _, v in ledger["adjustments"])) < 1e-9
    for p, delta in ledger["adjustments"]:
        ps = chart["planets"][p]
        assert ps["kala_bala"]["yuddha"] == delta
        assert ps["chesta_bala"] == dict(ledger["raw_chesta"])[p]
        assert ps["total_shashtiamsas"] == pytest.approx(
            dict(ledger["raw_totals"])[p] + delta, abs=1e-9
        )
    for enabled in (False, True):
        lagna = post(
            client,
            "/v1/muhurta/lagna/datetime",
            {
                "dt": dt,
                "latitude": 28.6,
                "longitude": 77.2,
                "include_shadbala": enabled,
            },
        )
        if enabled:
            assert len(lagna["assessment"]["shadbala"]) == 7
            witness = lagna["assessment"]["shadbala_result"]
            assert witness["context"]["provenance"] == "serving_reader_derived"
            assert len(witness["war_resolution"]["pairs"]) == len(ledger["pairs"])
            direct = {
                "sidereal_longitudes": dict(witness["context"]["sidereal_longitudes"]),
                "jd_ut1": witness["jd"],
                "lagna_sidereal_longitude": lagna["assessment"][
                    "lagna_sidereal_longitude"
                ],
                "shadbala_result": witness,
            }
            post(client, "/v1/muhurta/lagna/direct", direct)
            direct["sidereal_longitudes"]["Sun"] += 1
            assert (
                client.post("/v1/muhurta/lagna/direct", json=direct).status_code == 422
            )
            direct["sidereal_longitudes"]["Sun"] -= 1
            witness["war_resolution"]["credits"][0][1] += 1
            assert (
                client.post("/v1/muhurta/lagna/direct", json=direct).status_code == 422
            )


def test_dasha_birth_current_full_axis(client):
    natal = {"dt": "2000-01-01T12:00:00Z", "year_basis": "savana_360"}
    seq = post(client, "/v1/dasha/vimshottari/sequence", {"natal": natal, "levels": 2})
    current = post(
        client,
        "/v1/dasha/vimshottari/current",
        {"natal": natal, "current_dt": natal["dt"], "levels": 2},
    )
    first = seq["mahadashas"][0]
    assert first["planet"] == "Rahu" and first["sub"][0]["planet"] == "Mars"
    assert first["full_start_jd"] < first["start_jd"]
    assert first["full_end_jd"] - first["full_start_jd"] == pytest.approx(
        18 * 360, abs=1e-9
    )
    assert "Mars" in str(current)


def test_all_eight_varga_http_surfaces(client):
    lon = -1e-300
    dt = "2000-01-01T12:00:00Z"
    cases = [
        ("generic", {"sidereal_longitude": 30.0, "divisor": 27}),
        ("named", {"sidereal_longitude": lon, "varga": "hora"}),
        ("shodashvarga", {"sidereal_longitude": lon}),
        ("named/batch", {"longitudes": {"Sun": lon}, "varga": "hora"}),
        ("shodashvarga/batch", {"longitudes": {"Sun": lon}}),
        ("chart/named", {"dt": dt, "body": "Sun", "varga": "navamsa"}),
        ("chart/shodashvarga", {"dt": dt, "body": "Moon"}),
        ("chart/shodashvarga/batch", {"dt": dt, "bodies": ["Sun", "Moon"]}),
    ]
    count = 0

    def check(value):
        nonlocal count
        if isinstance(value, dict):
            if "varga_longitude" in value:
                count += 1
                assert value["sign"] == SIGNS[int(value["varga_longitude"] // 30)]
                assert 0 <= value["sign_degree"] < 30
            for v in value.values():
                check(v)
        elif isinstance(value, list):
            for v in value:
                check(v)

    for path, payload in cases:
        result = post(client, "/v1/varga/" + path, payload)
        check(result)
        if path == "generic":
            assert result["sign"] == "Cancer" and result["sign_degree"] == 0
    assert count >= 80


def test_sade_budget_and_context_policy_http(client):
    payload = {
        "natal_moon_sidereal_lon": 0.0,
        "start_dt": "2000-01-01T00:00:00Z",
        "end_dt": "2001-01-01T00:00:00Z",
        "max_evaluations": 2,
    }
    r = client.post("/v1/sade-sati/windows", json=payload)
    assert r.status_code == 422, r.text
    assert r.json()["category"] == "search_budget"
    payload["max_evaluations"] = True
    assert client.post("/v1/sade-sati/windows", json=payload).status_code == 422
    payload["max_evaluations"] = 10000
    result = post(client, "/v1/sade-sati/windows", payload)
    assert 1 < result["evaluations"] < 10000
    p = {"dt": "2000-01-01T12:00:00Z", "observer_lat": 28.6, "observer_lon": 77.2}
    b = post(
        client,
        "/v1/shadbala/chart",
        p | {"policy": {"saptavargaja_profile": "bphs_santhanam_27"}},
    )
    assert b["saptavargaja_profile"] == "bphs_santhanam_27"
    assert (
        b["policy_receipt"]["threshold_convention"] == "moira_retained_required_rupas"
    )
    assert (
        client.post(
            "/v1/shadbala/chart",
            json=p | {"policy": {"saptavargaja_profile": "universal"}},
        ).status_code
        == 422
    )


def test_timezone_polar_and_internal_error_http(client, monkeypatch):
    p = {
        "dt": "2000-01-01T12:00:00Z",
        "observer_lat": 28.6,
        "observer_lon": 77.2,
        "house_system": "O",
    }
    a = post(client, "/v1/shadbala/chart", p)
    b = post(client, "/v1/shadbala/chart", p | {"dt": "2000-01-01T17:30:00+05:30"})
    assert a == b
    polar = client.post(
        "/v1/shadbala/chart",
        json=p | {"dt": "2000-06-21T12:00:00Z", "observer_lat": 89.0},
    )
    assert (
        polar.status_code == 422
        and polar.json()["error_code"] == "shadbala_context_unavailable"
    )

    def broken(result):
        raise ValueError("injected internal invariant failure")

    monkeypatch.setattr(
        "moira_server.services.shadbala.validate_shadbala_output", broken
    )
    failure = client.post("/v1/shadbala/chart", json=p)
    assert failure.status_code == 500

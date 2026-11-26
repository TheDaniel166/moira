"""REST admission of ayanamsa provenance and the doctrinal families.

Governing record: wiki/02_standards/AYANAMSA_DOCTRINE_STANDARD.md.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.galactic_ayanamsa import GalacticAyanamsa, _PRESETS
from moira.sidereal import (
    Ayanamsa,
    GrahalaghavaAyanamsa,
    PolarStarAyanamsa,
    SuryaSiddhantaLibrationAyanamsa,
    ayanamsa,
    ayanamsa_with_truth,
    tropical_to_sidereal,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback

JD = 2461000.5


class _FakeEngine:
    pass


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_systems_list_carries_each_record(client: TestClient) -> None:
    body = client.get("/v1/sidereal/ayanamsa-systems").json()
    by_name = {item["system"]: item["doctrine"] for item in body["systems"]}
    assert set(by_name) == set(Ayanamsa.ALL)
    chitra = by_name[Ayanamsa.TRUE_CHITRAPAKSHA]
    assert chitra["family"] == "star_anchored_ecliptic"
    assert chitra["layer"] == "modern_convention"
    assert chitra["identification_certainty"] == "in_doubt"
    assert any(a["value_deg"] == 183.0 for a in chitra["attestations"])
    assert by_name[Ayanamsa.LAHIRI]["family"] == "epoch_polynomial"


def test_named_ayanamsa_reports_its_doctrine(client: TestClient) -> None:
    body = client.post("/v1/sidereal/ayanamsa", json={"jd_ut": JD, "ayanamsa_system": "True Pushya"}).json()
    assert body["doctrine"]["anchor_target_deg"] == 106.0
    assert body["computation_truth"]["doctrine_family"] == "star_anchored_ecliptic"
    assert body["computation_truth"]["doctrine_terms"] == {}


def test_galactic_preset_catalog_matches_engine_and_openapi(client: TestClient) -> None:
    response = client.get("/v1/sidereal/galactic-ayanamsa-presets")
    assert response.status_code == 200, response.text
    presets = response.json()["presets"]
    assert tuple(row["selection"]["preset"] for row in presets) == tuple(_PRESETS)
    for row in presets:
        assert row["selection"]["family"] == "galactic_anchor"
        assert row["supported_modes"] == ["true", "mean"]
        assert row["doctrine"]["sources"]
        assert row["doctrine"]["system"] == GalacticAyanamsa(row["selection"]["preset"]).name
    schema = client.app.openapi()
    assert "/v1/sidereal/galactic-ayanamsa-presets" in schema["paths"]
    models = schema["components"]["schemas"]
    assert models["GalacticAyanamsaSelection"]["properties"]["preset"]["enum"] == list(_PRESETS)
    doctrine = models["SiderealAyanamsaRequest"]["properties"]["ayanamsa_doctrine"]
    assert "galactic_anchor" in doctrine["anyOf"][0]["discriminator"]["mapping"]


@pytest.mark.parametrize("preset", tuple(_PRESETS))
@pytest.mark.parametrize("mode", ["mean", "true"])
def test_galactic_ayanamsa_matches_engine(client: TestClient, preset: str, mode: str) -> None:
    response = client.post("/v1/sidereal/ayanamsa", json={
        "jd_ut": JD, "mode": mode,
        "ayanamsa_doctrine": {"family": "galactic_anchor", "preset": preset},
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    truth = ayanamsa_with_truth(JD, GalacticAyanamsa(preset), mode)
    assert payload["ayanamsa_deg"] == truth.ayanamsa_deg
    assert payload["computation_truth"]["ayanamsa_unwrapped_deg"] == truth.ayanamsa_unwrapped_deg
    assert payload["computation_truth"]["doctrine_terms"] == dict(truth.doctrine_terms)
    assert payload["doctrine"]["family"] == "galactic_anchor"


def test_galactic_selection_reaches_conversion_and_nakshatras(client: TestClient) -> None:
    preset = "equator_allwise_2024"
    shared = {"jd_ut": JD, "ayanamsa_doctrine": {"family": "galactic_anchor", "preset": preset}}
    conversion = client.post("/v1/sidereal/convert", json={
        **shared, "longitude_deg": 100.0, "direction": "tropical_to_sidereal",
    })
    position = client.post("/v1/nakshatra/position", json={
        **shared, "tropical_longitude_deg": 100.0,
    })
    bulk = client.post("/v1/nakshatra/bulk", json={**shared, "positions": {"Moon": 100.0}})
    for response in (conversion, position, bulk):
        assert response.status_code == 200, response.text
    expected = tropical_to_sidereal(100.0, JD, GalacticAyanamsa(preset))
    assert conversion.json()["output_longitude_deg"] == expected
    assert position.json()["position"]["sidereal_longitude_deg"] == expected
    assert bulk.json()["positions"][0]["sidereal_longitude_deg"] == expected


def test_galactic_ayanamsa_enforces_engine_epoch_bound(client: TestClient) -> None:
    response = client.post("/v1/sidereal/ayanamsa", json={
        "jd_ut": 5_000_000.0,
        "ayanamsa_doctrine": {"family": "galactic_anchor", "preset": "centre_cochrane"},
    })
    assert response.status_code == 422
    assert "50 Julian centuries" in response.json()["message"]


@pytest.mark.parametrize(("selection", "system"), [
    ({"family": "grahalaghava"}, GrahalaghavaAyanamsa()),
    ({"family": "grahalaghava", "year_convention": "elapsed", "stepping": "continuous"},
     GrahalaghavaAyanamsa("elapsed", "continuous")),
    ({"family": "polar_star", "source": "surya_siddhanta", "nakshatra": "chitra"},
     PolarStarAyanamsa("surya_siddhanta", "chitra")),
    ({"family": "surya_siddhanta_libration"}, SuryaSiddhantaLibrationAyanamsa()),
])
def test_doctrinal_ayanamsa_matches_the_engine(client: TestClient, selection: dict, system) -> None:
    response = client.post("/v1/sidereal/ayanamsa", json={"jd_ut": JD, "ayanamsa_doctrine": selection})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ayanamsa_system"] == system.name
    assert body["ayanamsa_deg"] == pytest.approx(ayanamsa(JD, system) % 360.0, abs=1e-12)
    assert body["doctrine"]["system"] == system.name
    assert body["computation_truth"]["doctrine_terms"]


def test_doctrinal_conversion_and_nakshatra(client: TestClient) -> None:
    selection = {"family": "suryadeva_trepidation"}
    from moira.sidereal import SuryadevaTrepidationAyanamsa

    system = SuryadevaTrepidationAyanamsa()
    conversion = client.post("/v1/sidereal/convert", json={
        "jd_ut": JD, "longitude_deg": 100.0, "direction": "tropical_to_sidereal",
        "ayanamsa_doctrine": selection,
    })
    assert conversion.status_code == 200, conversion.text
    assert conversion.json()["output_longitude_deg"] == pytest.approx(
        tropical_to_sidereal(100.0, JD, system), abs=1e-12)
    position = client.post("/v1/nakshatra/position", json={
        "jd_ut": JD, "tropical_longitude_deg": 100.0, "ayanamsa_doctrine": selection,
    })
    assert position.status_code == 200, position.text
    assert position.json()["position"]["ayanamsa_system"] == system.name


@pytest.mark.parametrize("payload", [
    {"jd_ut": JD, "ayanamsa_system": "Lahiri", "ayanamsa_doctrine": {"family": "grahalaghava"}},
    {"jd_ut": JD, "ayanamsa_doctrine": {"family": "grahalaghava", "stepping": "daily"}},
    {"jd_ut": JD, "ayanamsa_doctrine": {"family": "polar_star", "source": "lalla", "nakshatra": "chitra"}},
    {"jd_ut": JD, "ayanamsa_doctrine": {"family": "surya_siddhanta_libration", "cycles_per_mahayuga": 60}},
    {"jd_ut": JD, "ayanamsa_doctrine": {"family": "unknown"}},
    {"jd_ut": JD, "ayanamsa_doctrine": {"family": "galactic_anchor"}},
    {"jd_ut": JD, "ayanamsa_doctrine": {"family": "galactic_anchor", "preset": "unknown"}},
    {"jd_ut": JD, "ayanamsa_system": "Lahiri",
     "ayanamsa_doctrine": {"family": "galactic_anchor", "preset": "centre_cochrane"}},
])
def test_invalid_doctrinal_requests_are_rejected(client: TestClient, payload: dict) -> None:
    assert client.post("/v1/sidereal/ayanamsa", json=payload).status_code == 422

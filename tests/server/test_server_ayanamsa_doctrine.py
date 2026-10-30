"""REST admission of ayanamsa provenance and the doctrinal families.

Governing record: wiki/02_standards/AYANAMSA_DOCTRINE_STANDARD.md.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.sidereal import (
    Ayanamsa,
    GrahalaghavaAyanamsa,
    PolarStarAyanamsa,
    SuryaSiddhantaLibrationAyanamsa,
    ayanamsa,
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
])
def test_invalid_doctrinal_requests_are_rejected(client: TestClient, payload: dict) -> None:
    assert client.post("/v1/sidereal/ayanamsa", json=payload).status_code == 422

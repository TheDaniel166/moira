"""Noncentral geometry survives REST transport without invented central data."""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira.julian import julian_day
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.phenomena import SolarEclipseUmbralContactsResponse
from moira_server.serializers.phenomena import (
    serialize_solar_eclipse_global_circumstances,
    serialize_solar_eclipse_path,
)


@pytest.mark.loopback
@pytest.mark.parametrize("date,kind", [((2014, 4, 29), "annular"), ((2043, 4, 9), "total")])
def test_noncentral_path_and_global_routes_preserve_nullable_geometry(
    eclipse_calculator, monkeypatch, date, kind,
):
    seed = julian_day(*date) - 1.0
    path = eclipse_calculator.solar_eclipse_path(seed, kind=kind, sample_count=3)
    result = eclipse_calculator.solar_global_circumstances(seed, kind=kind)
    engine = SimpleNamespace(
        _reader=eclipse_calculator._reader,
        solar_global_circumstances=lambda *args, **kwargs: result,
    )
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        global_response = client.post(
            "/v1/eclipses/solar/global-circumstances", json={"jd_start": seed, "kind": kind},
        )
        path_response = client.post(
            "/v1/eclipses/solar/path", json={"jd_start": seed, "kind": kind, "sample_count": 3},
        )
    assert global_response.status_code == 200, global_response.text
    assert path_response.status_code == 200, path_response.text
    global_body, path_body = global_response.json(), path_response.json()
    assert global_body == serialize_solar_eclipse_global_circumstances(result).model_dump(mode="json")
    assert path_body == serialize_solar_eclipse_path(path).model_dump(mode="json")
    assert path_body["central_line_lats"] == path_body["central_line_lons"] == []
    assert path_body["umbral_width_km"] is None
    assert global_body["greatest"]["path_width_km"] is None
    assert global_body["greatest_duration"]["path_width_km"] is None
    assert global_body["first_central_line_limit"] is None
    assert global_body["last_central_line_limit"] is None
    contacts = global_body["umbral_contacts"]
    assert contacts["u1"]["kind"] == "u1"
    assert contacts["u4"]["kind"] == "u4"
    assert contacts["u2"] is contacts["u3"] is None
    for snapshot in path_body["noncentral_footprints"]:
        assert snapshot["boundary"][0] == snapshot["boundary"][-1]
        assert snapshot["horizon_policy"] == "UNCLIPPED_PHYSICAL_CONE"
    malformed = {**contacts, "u2": {**contacts["u1"], "kind": "u2"}}
    with pytest.raises(ValidationError, match="paired"):
        SolarEclipseUmbralContactsResponse.model_validate(malformed)

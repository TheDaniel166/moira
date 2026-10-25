"""Optional rational aspect selection, discovery, receipts, and bounded searches."""

from fractions import Fraction
from types import SimpleNamespace

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira import Moira, Chart
from moira.planets import PlanetData
from moira.optional_aspects import OPTIONAL_ASPECT_FRACTIONS
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.forecasting import CompositeTransitRequest, DavisonTransitRequest
from moira_server.models.relationship import SynastryPairRequest
from moira_server.services import forecasting, relationship, chart_wheel


pytestmark = pytest.mark.loopback

_NUMERATORS = {13: (1, 2, 3, 4, 5, 6), 32: (1, 3, 5, 7, 9, 11, 13, 15),
               36: (1, 5, 7, 11, 13, 17), 40: (1, 3, 7, 9, 11, 13, 17, 19)}
_PARTY = {"dt": "2000-01-01T12:00:00Z", "latitude": 0, "longitude": 0}


@pytest.fixture
def engine():
    # Exercise the actual facade on supplied geometry; these methods need no SPK.
    value = Moira.__new__(Moira)
    value._reader_obj = None
    return value


@pytest.fixture
def client(monkeypatch, engine):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    with TestClient(app) as value:
        yield value


def test_discovery_returns_all_exact_fractions_aliases_orbs_and_no_default_selection(client):
    response = client.get("/v1/aspects/optional-sets")
    assert response.status_code == 200
    body = response.json()
    assert body["standard_aspect_count"] == 46
    assert body["optional_aspect_count"] == 28
    assert body["default_selection"] == []
    assert body["orb_policy"] == "12_degrees_divided_by_harmonic"
    assert [group["key"] for group in body["sets"]] == ["H13", "H32", "H36", "H40"]
    for group in body["sets"]:
        q = group["harmonic"]
        assert [member["numerator"] for member in group["members"]] == list(_NUMERATORS[q])
        for member in group["members"]:
            p = member["numerator"]
            assert member["name"] == f"H{q} {p}/{q}"
            assert member["denominator"] == q
            assert member["angle_deg"] == pytest.approx(float(360 * Fraction(p, q)), abs=1e-12)
            assert member["default_orb_deg"] == 12/q
            assert f"{p}/{q}" in member["aliases"]


@pytest.mark.parametrize("q", _NUMERATORS)
def test_every_optional_fraction_is_detected_and_serialized_only_after_opt_in(client, q):
    for p in _NUMERATORS[q]:
        name = f"H{q} {p}/{q}"
        payload = {"longitudes": {"Sun": 355, "Moon": (355 + float(360 * Fraction(p, q))) % 360}, "tier": 0}
        default = client.post("/v1/aspects/from-longitudes", json=payload)
        assert default.status_code == 200
        assert default.json()["computation_truth"]["optional_sets"] == []
        assert all(event["aspect"] not in OPTIONAL_ASPECT_FRACTIONS for event in default.json()["events"])
        response = client.post("/v1/aspects/from-longitudes", json={**payload, "optional_sets": [f"h{q}"]})
        assert response.status_code == 200
        body = response.json()
        assert body["computation_truth"]["optional_sets"] == [f"H{q}"]
        assert body["computation_truth"]["aspect_policy_authority"] == "moira.aspect_registry.ASPECT_DEFINITIONS"
        hit = next(event for event in body["events"] if event["aspect"] == name)
        assert hit["angle"] == pytest.approx(float(360 * Fraction(p, q)), abs=1e-12)
        assert hit["orb"] == pytest.approx(0, abs=1e-12)
        assert hit["allowed_orb"] == 12/q
        assert hit["classification"] == {"domain": "zodiacal", "tier": "extended_minor", "family": f"harmonic_{q}"}


@pytest.mark.parametrize("value", ["H13", None, [13], [True], ["H99"], ["H13", "h13"], [" H13"]])
def test_invalid_sets_reject_before_geometry_dispatch(client, monkeypatch, value):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid optional selection reached computation")

    monkeypatch.setattr(relationship, "compute_aspects_from_longitudes", unexpected)
    response = client.post("/v1/aspects/from-longitudes", json={
        "longitudes": {"Sun": 0, "Moon": 9}, "optional_sets": value,
    })
    assert response.status_code == 422


@pytest.mark.parametrize("route", ["aspects", "contacts"])
def test_synastry_selection_survives_service_and_contact_receipts(client, monkeypatch, route):
    a = SimpleNamespace(longitudes=lambda **_: {"Sun": 0}, speeds=lambda: {})
    b = SimpleNamespace(longitudes=lambda **_: {"Moon": 9}, speeds=lambda: {})
    monkeypatch.setattr(relationship, "_pair_charts", lambda *args: (a, b))
    response = client.post(f"/v1/synastry/{route}", json={
        "first": _PARTY, "second": _PARTY, "tier": 0, "optional_sets": ["h40"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["computation_truth"]["optional_sets"] == ["H40"]
    if route == "aspects":
        assert any(event["aspect"] == "H40 1/40" for event in body["events"])
    else:
        hit = next(event for event in body["events"] if event["aspect"]["aspect"] == "H40 1/40")
        assert hit["truth"]["optional_sets"] == ["H40"]


def test_derived_chart_analysis_forwards_optional_selection(engine):
    request = SynastryPairRequest(first=_PARTY, second=_PARTY, optional_sets=["H36"])
    analysis = relationship._compute_derived_chart_aspects(engine, {"Sun": 0, "Moon": 10}, request)
    assert analysis.optional_sets == ("H36",)
    assert any(aspect.aspect == "H36 1/36" for aspect in analysis.aspects)


def test_chart_wheel_exposes_optional_geometry_and_policy_receipt(client, monkeypatch):
    chart = Chart(
        2_451_545.0,
        {name: PlanetData(name, longitude, 0, 1, 1, False) for name, longitude in (("Sun", 0), ("Moon", 9))},
        {}, 23.4, 64,
    )
    monkeypatch.setattr(chart_wheel, "compute_chart", lambda *args: chart)
    payload = {"chart": {"dt": _PARTY["dt"]}, "config": {"aspect_tier": 0, "optional_sets": ["h40"]}}
    response = client.post("/v1/website/chart-wheel/packet", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["config"]["optional_sets"] == ["H40"]
    assert body["computation_truth"]["aspects"]["optional_sets"] == ["H40"]
    hit = next(aspect for aspect in body["aspects"] if aspect["aspect"] == "H40 1/40")
    assert hit["angle"] == 9
    assert hit["allowed_orb"] == 0.3
    assert hit["family"] == "harmonic_40"


@pytest.mark.parametrize(("model", "service_name", "builder", "finder"), [
    (CompositeTransitRequest, "compute_composite_transits", "compute_composite_chart", "find_composite_transits"),
    (DavisonTransitRequest, "compute_davison_transits", "compute_davison_chart", "find_davison_transits"),
])
def test_forecasting_services_forward_sets_and_preserve_work_budgets(monkeypatch, model, service_name, builder, finder):
    chart, sentinel = object(), object()
    captured = {}
    request = model.model_validate({
        "chart": {"first": _PARTY, "second": _PARTY}, "moving_bodies": ["Mars"],
        "jd_start": 2_460_000, "jd_end": 2_460_001, "tier": 0,
        "target_names": ["Sun"], "optional_sets": ["H13"], "aspect_names": ["1/13"],
    })
    monkeypatch.setattr(forecasting, builder, lambda *args: chart)
    monkeypatch.setattr(forecasting, "relationship_chart_targets", lambda *args, **kwargs: SimpleNamespace(target_count=1))

    def fake_find(*args, **kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(forecasting, finder, fake_find)
    assert getattr(forecasting, service_name)(SimpleNamespace(_reader=object()), request) is sentinel
    assert captured["optional_sets"] == ("H13",)
    assert captured["aspect_names"] == ["H13 1/13"]
    assert forecasting._directional_branch_count(2, None) == 90
    assert forecasting._directional_branch_count(2, None, tuple(f"H{q}" for q in _NUMERATORS)) == 146
    monkeypatch.setattr(forecasting, "_MAX_RELATIONSHIP_SEARCH_CALLS", 100)
    with pytest.raises(ValueError, match="146 canonical searches"):
        forecasting._guard_relationship_search(
            target_count=1, moving_body_count=1, tier=2, aspect_names=None,
            optional_sets=tuple(f"H{q}" for q in _NUMERATORS), moving_bodies=["Mars"],
            jd_start=2_460_000, jd_end=2_460_001, step_days=1,
        )
    with pytest.raises(ValidationError, match="unique after alias"):
        model.model_validate({**request.model_dump(), "aspect_names": ["1/13", "H13 1/13"]})


def test_four_presets_appear_in_catalog_and_computed_chart_payloads(client):
    catalog = client.get("/v1/harmonics/presets").json()
    by_harmonic = {preset["harmonic"]: preset["name"] for preset in catalog["presets"]}
    for q in _NUMERATORS:
        assert by_harmonic[q] == f"H{q} 1/{q}"
        response = client.post("/v1/harmonics/chart", json={"longitudes": {"Sun": 0, "Moon": 360/q}, "harmonic": q})
        assert response.status_code == 200
        assert response.json()["provenance"]["preset_name"] == f"H{q} 1/{q}"

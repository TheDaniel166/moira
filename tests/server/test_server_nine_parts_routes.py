"""P12-05 Abu Ma'shar Nine Parts route admission tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.nine_parts import NinePartName, nine_parts_abu_mashar
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeEngine:
    pass


DIURNAL_ASC = 15.0
DIURNAL_PLANETS = {
    "Sun": 20.0,
    "Moon": 55.0,
    "Mars": 130.0,
    "Jupiter": 210.0,
    "Saturn": 285.0,
    "North Node": 100.0,
}
NOCTURNAL_PLANETS = {
    "Sun": 195.0,
    "Moon": 55.0,
    "Mars": 130.0,
    "Jupiter": 210.0,
    "Saturn": 285.0,
    "North Node": 100.0,
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert message_fragment in body["message"]


def _post_abu_mashar(
    client: TestClient,
    *,
    planets: dict[str, float] | None = None,
    is_night_chart: bool = False,
    include_validation: bool = True,
):
    return client.post(
        "/v1/nine-parts/abu-mashar",
        json={
            "asc": DIURNAL_ASC,
            "planets": DIURNAL_PLANETS if planets is None else planets,
            "is_night_chart": is_night_chart,
            "include_validation": include_validation,
        },
    )


def test_abu_mashar_route_preserves_day_chart_engine_truth(client: TestClient) -> None:
    direct = nine_parts_abu_mashar(DIURNAL_ASC, DIURNAL_PLANETS, False)

    response = _post_abu_mashar(client)

    assert response.status_code == 200
    body = response.json()
    assert [part["name"] for part in body["parts"]] == [name.value for name in NinePartName]
    assert len(body["parts"]) == 9
    assert body["aggregate"]["is_night_chart"] is False
    assert body["aggregate"]["part_count"] == 9
    assert body["aggregate"]["direct_part_count"] == 6
    assert body["aggregate"]["derived_part_count"] == 3
    assert body["aggregate"]["planetary_part_count"] == 7
    assert body["aggregate"]["admitted_extension_part_count"] == 2
    assert body["aggregate"]["nocturnal_formula_count"] == 0
    assert body["policy"] == {
        "reversal_rule": "full_reversal",
        "historical_scope": "evidenced_core_plus_admitted_extension",
    }
    assert body["validation"] == {
        "passed": True,
        "failures": [],
        "entrypoint": "validate_nine_parts_output",
    }

    for response_part, direct_part in zip(body["parts"], direct.parts_set.parts, strict=True):
        assert response_part["name"] == direct_part.name.value
        assert response_part["planet_association"] == direct_part.planet_association
        assert response_part["historical_status"] == direct_part.historical_status.value
        assert response_part["meaning"] == direct_part.meaning
        assert response_part["longitude"] == pytest.approx(direct_part.longitude)
        assert response_part["sign"] == direct_part.sign
        assert response_part["sign_degree"] == pytest.approx(direct_part.sign_degree)
        assert response_part["sign_symbol"] == direct_part.sign_symbol
        assert response_part["dependency_kind"] == direct_part.dependency_kind.value
        assert response_part["computation"]["formula_variant"] == "day"
        assert response_part["computation"]["formula_reversed"] is False
        assert response_part["computation"]["formula"] == direct_part.computation.formula

    provenance = body["provenance"]
    assert provenance["source_module"] == "moira.nine_parts"
    assert provenance["engine_entrypoint"] == "nine_parts_abu_mashar"
    assert provenance["validation_entrypoint"] == "validate_nine_parts_output"
    assert provenance["doctrine"] == "Abu_Mashar_Nine_Parts"
    assert provenance["night_determination_owner"] == "caller_supplied"
    assert provenance["ascendant_derivation_owner"] == "caller_supplied"
    assert provenance["chart_construction"] == "not_computed"
    assert provenance["house_placement"] == "not_computed"
    assert provenance["sect_determination"] == "not_computed"


def test_abu_mashar_route_preserves_night_full_reversal(client: TestClient) -> None:
    direct = nine_parts_abu_mashar(DIURNAL_ASC, NOCTURNAL_PLANETS, True)

    response = _post_abu_mashar(
        client,
        planets=NOCTURNAL_PLANETS,
        is_night_chart=True,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["aggregate"]["is_night_chart"] is True
    assert body["aggregate"]["nocturnal_formula_count"] == 9
    assert all(part["computation"]["formula_reversed"] for part in body["parts"])
    assert {part["computation"]["formula_variant"] for part in body["parts"]} == {"night"}
    assert [part["longitude"] for part in body["parts"]] == pytest.approx(
        [part.longitude for part in direct.parts_set.parts]
    )


def test_abu_mashar_route_preserves_derived_dependencies_and_extensions(
    client: TestClient,
) -> None:
    response = _post_abu_mashar(client)

    assert response.status_code == 200
    body = response.json()
    dependencies = {relation["part"]: relation for relation in body["dependency_relations"]}
    assert dependencies["Love"]["lot_dependencies"] == ["Spirit", "Fortune"]
    assert dependencies["Love"]["is_direct"] is False
    assert dependencies["Love"]["dependency_count"] == 2
    assert dependencies["Necessity"]["lot_dependencies"] == ["Fortune", "Spirit"]
    assert dependencies["Victory"]["lot_dependencies"] == ["Spirit"]

    by_name = {part["name"]: part for part in body["parts"]}
    assert by_name["Sword"]["historical_status"] == "admitted_extension"
    assert by_name["Sword"]["planet_association"] is None
    assert by_name["Node"]["historical_status"] == "admitted_extension"
    assert by_name["Node"]["planet_association"] is None
    for name in ["Fortune", "Spirit", "Love", "Necessity", "Courage", "Victory", "Nemesis"]:
        assert by_name[name]["historical_status"] == "core_seven"


def test_abu_mashar_route_preserves_condition_profiles(client: TestClient) -> None:
    response = _post_abu_mashar(client)

    assert response.status_code == 200
    body = response.json()
    assert [profile["part"] for profile in body["condition_profiles"]] == [
        name.value for name in NinePartName
    ]
    assert len(body["condition_profiles"]) == 9
    for profile, part in zip(body["condition_profiles"], body["parts"], strict=True):
        assert profile["part"] == part["name"]
        assert profile["dependency_kind"] == part["dependency_kind"]
        assert profile["historical_status"] == part["historical_status"]
        assert isinstance(profile["lord"], str)
        assert isinstance(profile["lord_is_part_planet"], bool)
        assert isinstance(profile["is_in_own_sign"], bool)


def test_abu_mashar_route_can_omit_validation_block(client: TestClient) -> None:
    response = _post_abu_mashar(client, include_validation=False)

    assert response.status_code == 200
    assert response.json()["validation"] is None


def test_abu_mashar_route_accepts_explicit_admitted_policy(client: TestClient) -> None:
    response = client.post(
        "/v1/nine-parts/abu-mashar",
        json={
            "asc": DIURNAL_ASC,
            "planets": DIURNAL_PLANETS,
            "is_night_chart": False,
            "policy": {
                "reversal_rule": "full_reversal",
                "historical_scope": "evidenced_core_plus_admitted_extension",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["policy"] == {
        "reversal_rule": "full_reversal",
        "historical_scope": "evidenced_core_plus_admitted_extension",
    }


@pytest.mark.parametrize("missing_key", ["Sun", "Moon", "North Node"])
def test_abu_mashar_route_rejects_missing_required_planets(
    client: TestClient,
    missing_key: str,
) -> None:
    planets = dict(DIURNAL_PLANETS)
    del planets[missing_key]

    response = _post_abu_mashar(client, planets=planets)

    _assert_validation_envelope(response, message_fragment=f"planets missing required keys: {missing_key}")


def test_abu_mashar_route_rejects_non_finite_inputs(client: TestClient) -> None:
    non_finite_asc = client.post(
        "/v1/nine-parts/abu-mashar",
        json={"asc": "NaN", "planets": DIURNAL_PLANETS, "is_night_chart": False},
    )
    planets = dict(DIURNAL_PLANETS)
    planets["Moon"] = "NaN"
    non_finite_planet = _post_abu_mashar(client, planets=planets)

    _assert_validation_envelope(non_finite_asc, message_fragment="asc must be finite")
    _assert_validation_envelope(non_finite_planet, message_fragment="planet longitudes must be finite")


def test_abu_mashar_route_rejects_non_boolean_flags(client: TestClient) -> None:
    non_bool_night = client.post(
        "/v1/nine-parts/abu-mashar",
        json={"asc": DIURNAL_ASC, "planets": DIURNAL_PLANETS, "is_night_chart": 1},
    )
    non_bool_validation = client.post(
        "/v1/nine-parts/abu-mashar",
        json={
            "asc": DIURNAL_ASC,
            "planets": DIURNAL_PLANETS,
            "is_night_chart": False,
            "include_validation": "yes",
        },
    )

    _assert_validation_envelope(non_bool_night, message_fragment="is_night_chart must be a boolean")
    _assert_validation_envelope(
        non_bool_validation,
        message_fragment="include_validation must be a boolean",
    )


def test_abu_mashar_route_rejects_malformed_planet_maps(client: TestClient) -> None:
    non_object = client.post(
        "/v1/nine-parts/abu-mashar",
        json={"asc": DIURNAL_ASC, "planets": [], "is_night_chart": False},
    )
    empty_name = client.post(
        "/v1/nine-parts/abu-mashar",
        json={
            "asc": DIURNAL_ASC,
            "planets": {**DIURNAL_PLANETS, " ": 10.0},
            "is_night_chart": False,
        },
    )
    duplicate_after_trim = client.post(
        "/v1/nine-parts/abu-mashar",
        json={
            "asc": DIURNAL_ASC,
            "planets": {**DIURNAL_PLANETS, " Sun ": 10.0},
            "is_night_chart": False,
        },
    )

    _assert_validation_envelope(non_object, message_fragment="Input should be a valid dictionary")
    _assert_validation_envelope(empty_name, message_fragment="planet keys must be non-empty")
    _assert_validation_envelope(duplicate_after_trim, message_fragment="unique after trimming")


def test_abu_mashar_route_rejects_unsupported_policy_values(client: TestClient) -> None:
    unsupported_reversal = client.post(
        "/v1/nine-parts/abu-mashar",
        json={
            "asc": DIURNAL_ASC,
            "planets": DIURNAL_PLANETS,
            "is_night_chart": False,
            "policy": {"reversal_rule": "partial_reversal"},
        },
    )
    unsupported_scope = client.post(
        "/v1/nine-parts/abu-mashar",
        json={
            "asc": DIURNAL_ASC,
            "planets": DIURNAL_PLANETS,
            "is_night_chart": False,
            "policy": {"historical_scope": "core_seven_only"},
        },
    )
    non_object_policy = client.post(
        "/v1/nine-parts/abu-mashar",
        json={
            "asc": DIURNAL_ASC,
            "planets": DIURNAL_PLANETS,
            "is_night_chart": False,
            "policy": "full_reversal",
        },
    )

    _assert_validation_envelope(unsupported_reversal, message_fragment="Input should be")
    _assert_validation_envelope(unsupported_scope, message_fragment="Input should be")
    _assert_validation_envelope(non_object_policy, message_fragment="Input should be a valid dictionary")


def test_nine_parts_route_is_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/nine-parts/")
    }

    assert paths == {"/v1/nine-parts/abu-mashar"}

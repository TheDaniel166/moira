from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "iota_spica_2024_observed_contacts.json"
)
_EXPECTED_DOCUMENTS = {
    "contact_reduction": {
        "url": "https://occultations.org/publications/rasc/2025/Reducing_A_Graze_With_Pymovie_and_Pyote.pdf",
        "mime_type": "application/pdf",
        "byte_length": 285123,
        "sha256": "424135fe208cbd232907c8eea374f528a56220ca4c8c7bd8bf6c361302b23486",
        "last_modified": "Wed, 01 Jan 2025 05:26:51 GMT",
    },
    "event_page": {
        "url": "https://occultations.org/publications/rasc/2025/20241127Spica.htm",
        "mime_type": "text/html",
        "byte_length": 11069,
        "sha256": "bdeef79e9803b7587e7f0fef5125fb687d0c2374c1d5e33a888dcfbe87fa8e5e",
        "last_modified": "Wed, 01 Jan 2025 05:26:44 GMT",
    },
    "prediction_manual": {
        "url": "https://occultations.org/publications/rasc/2025/GRAZPREP5p0Manual.pdf",
        "mime_type": "application/pdf",
        "byte_length": 4871421,
        "sha256": "7b25742b1fcf02b1a39d9f00cc79bcfe4fe6c908905b1204dcbd21cffc6644c5",
    },
}
_EXPECTED_SITE_SHAPES = {
    "Dunham1": {
        "latitude_deg": 31.49531,
        "longitude_deg": -99.91815,
        "published_height_m": 500.5,
        "instrument_height_m": 500.0,
        "interval_count": 5,
        "labels": ("D1", "R1", "D2", "R2", "D3", "R3", "D4", "R4", "D5", "R5"),
        "contacts": (
            ("D1", "disappearance", "10:54:31.3039", 0.0237),
            ("R1", "reappearance", "10:54:32.8355", 0.0245),
            ("D2", "disappearance", "10:54:34.0220", 0.0196),
            ("R2", "reappearance", "10:54:57.6368", 0.0184),
            ("D3", "disappearance", "10:56:09.5055", 0.0135),
            ("R3", "reappearance", "10:57:00.0714", 0.0192),
            ("D4", "disappearance", "10:57:17.2212", 0.0168),
            ("R4", "reappearance", "10:57:27.2838", 0.0133),
            ("D5", "disappearance", "10:57:27.6316", 0.0196),
            ("R5", "reappearance", "10:57:48.3268", 0.0143),
        ),
    },
    "Dunham2": {
        "latitude_deg": 31.49570,
        "longitude_deg": -99.91792,
        "published_height_m": 499.9,
        "instrument_height_m": 497.0,
        "interval_count": 4,
        "labels": ("D1", "R1", "D2", "R2", "D3", "R3", "D4", "R5"),
        "contacts": (
            ("D1", "disappearance", "10:54:31.1780", 0.0145),
            ("R1", "reappearance", "10:54:33.2681", 0.0101),
            ("D2", "disappearance", "10:54:33.9701", 0.0212),
            ("R2", "reappearance", "10:54:58.0113", 0.0087),
            ("D3", "disappearance", "10:56:09.2413", 0.0142),
            ("R3", "reappearance", "10:57:00.2204", 0.0113),
            ("D4", "disappearance", "10:57:16.7772", 0.0120),
            ("R5", "reappearance", "10:57:48.2962", 0.0110),
        ),
    },
}


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_iota_spica_observed_contact_fixture_preserves_source_semantics() -> None:
    payload = _fixture()
    source = payload["source"]

    assert payload["schema_version"] == 1
    assert payload["evidence_class"] == "authority_validation"
    assert payload["product"] == "observed_lunar_graze_contact_chronology"
    assert source["authority"] == "International Occultation Timing Association (IOTA)"
    assert source["target"] == "Spica"
    assert source["event_date_utc"] == "2024-11-27"
    assert source["time_label_in_contact_table"] == "UT"
    assert source["time_realization"] == "GPS-referenced UTC"
    assert source["table_display_resolution_s"] == 0.0001
    assert source["intended_report_resolution_s"] == 0.01
    assert "UTC to UT1 exactly once" in source["timestamp_interpretation"]
    assert "0.95 containment" in source["uncertainty_semantics"]
    assert source["uncertainty_is_model_tolerance"] is False
    assert "not asserted to exhaust" in source["contact_scope"]
    assert "does not report a tangency" in source["tangency_scope"]

    documents = source["documents"]
    assert set(documents) == set(_EXPECTED_DOCUMENTS)
    assert documents["contact_reduction"]["author"] == "Joan Dunham"
    assert documents["contact_reduction"]["title"] == "Reducing a graze with Pymovie/Pyote"
    assert documents["event_page"]["title"] == "Spectacular Graze of Spica, 2024 November 27"
    assert documents["prediction_manual"]["title"] == "GRAZPREP version 5.0 Manual"
    assert documents["prediction_manual"]["author"] == "Eberhard Riedel"
    for document_id, expected in _EXPECTED_DOCUMENTS.items():
        document = documents[document_id]
        for field, value in expected.items():
            assert document[field] == value
        assert len(document["sha256"]) == 64

    prediction_context = source["prediction_context"]
    assert prediction_context["software"] == "GRAZPREP 5.0"
    assert "recalculated" in prediction_context["topography"]
    assert prediction_context["contact_claim"].startswith("approximate")
    assert "not asserted" in prediction_context["raw_copc_equivalence"]
    assert "observed PyOTE contacts" in prediction_context["validation_role"]

    sites = payload["sites"]
    assert [site["site_id"] for site in sites] == ["Dunham1", "Dunham2"]
    for site in sites:
        expected = _EXPECTED_SITE_SHAPES[site["site_id"]]
        assert site["latitude_deg"] == expected["latitude_deg"]
        assert site["longitude_deg"] == expected["longitude_deg"]
        assert site["coordinate_resolution_deg"] == 0.00001
        assert site["coordinate_resolution_role"] == (
            "published decimal resolution; not asserted as geodetic accuracy"
        )
        assert site["published_height"]["value_m"] == expected["published_height_m"]
        assert site["published_height"]["vertical_reference"] == "mean_sea_level"
        assert site["published_height"]["source_label"] == "above sea level"
        assert site["published_height"]["is_wgs84_ellipsoid_height"] is False
        assert site["instrument_height"]["value_m"] == expected["instrument_height_m"]
        assert "not asserted as WGS84 ellipsoid height" in site["instrument_height"]["vertical_reference"]
        assert site["observed_occultation_interval_count"] == expected["interval_count"]
        validation_height = site["validation_height_approximation"]
        assert validation_height["formula"] == "h = H + N"
        assert validation_height["geoid_model_error_m"] == 0.058
        assert validation_height["geoid_retrieved_on"] == "2026-07-18"
        assert validation_height["source_height_H_m"] == expected["published_height_m"]
        assert validation_height["ellipsoid_height_m"] == pytest.approx(
            expected["published_height_m"] + validation_height["geoid_undulation_N_m"],
            abs=0.0005,
        )
        assert "not asserted identical to WGS84" in validation_height[
            "horizontal_vertical_realization"
        ]

        contacts = site["contacts"]
        assert tuple(contact["label"] for contact in contacts) == expected["labels"]
        assert tuple(
            (
                contact["label"],
                contact["kind"],
                contact["published_ut"],
                contact["uncertainty_95_s"],
            )
            for contact in contacts
        ) == expected["contacts"]
        assert [_utc(contact["timestamp_utc"]) for contact in contacts] == sorted(
            _utc(contact["timestamp_utc"]) for contact in contacts
        )
        assert all(
            contact["timestamp_utc"].endswith(f"T{contact['published_ut']}Z")
            for contact in contacts
        )
        assert all(
            contact["kind"] == (
                "disappearance" if contact["label"].startswith("D") else "reappearance"
            )
            for contact in contacts
        )
        assert all(0.0087 <= contact["uncertainty_95_s"] <= 0.0245 for contact in contacts)

    dunham1 = sites[0]["contacts"]
    r4 = next(contact for contact in dunham1 if contact["label"] == "R4")
    d5 = next(contact for contact in dunham1 if contact["label"] == "D5")
    assert (_utc(d5["timestamp_utc"]) - _utc(r4["timestamp_utc"])).total_seconds() == pytest.approx(
        0.3478,
        abs=1.0e-9,
    )
    policy = payload["comparison_policy"]
    assert policy["model_comparison_status"] == "admitted_in_separate_model_fixture"
    assert policy["model_comparison_fixture"] == (
        "tests/fixtures/iota_spica_2024_moira_lola_model.json"
    )
    assert policy["model_contact_gate_s"] is None
    assert policy["source_supplies_model_tolerance"] is False
    assert policy["critical_resolved_visible_interval_s"] == 0.3478
    assert policy["critical_interval_role"] == (
        "observed morphology witness; not a model tolerance"
    )


@pytest.mark.external_network
@pytest.mark.slow
def test_iota_spica_authority_documents_still_match_frozen_bytes() -> None:
    requests = pytest.importorskip("requests")
    documents = _fixture()["source"]["documents"]

    for document_id, expected in _EXPECTED_DOCUMENTS.items():
        response = requests.get(
            expected["url"],
            timeout=(10, 60),
            headers={"User-Agent": "Moira authority-fixture verifier/1"},
        )
        response.raise_for_status()

        raw = response.content
        received_mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        assert received_mime == expected["mime_type"], (
            f"{document_id} MIME drifted from the frozen authority fixture"
        )
        assert len(raw) == expected["byte_length"], (
            f"{document_id} byte length drifted; inspect the authority document manually"
        )
        assert hashlib.sha256(raw).hexdigest() == expected["sha256"], (
            f"{document_id} SHA-256 drifted; inspect the authority document manually"
        )

        frozen = documents[document_id]
        assert frozen["url"] == expected["url"]
        assert frozen["mime_type"] == expected["mime_type"]
        assert frozen["byte_length"] == expected["byte_length"]
        assert frozen["sha256"] == expected["sha256"]


@pytest.mark.external_network
def test_iota_spica_height_approximations_still_match_noaa_geoid18() -> None:
    """Refresh the geoid term without promoting Google Earth H to WGS84."""

    requests = pytest.importorskip("requests")
    for site in _fixture()["sites"]:
        approximation = site["validation_height_approximation"]
        response = requests.get(approximation["geoid_query_url"], timeout=(10, 30))
        response.raise_for_status()
        payload = response.json()

        assert payload["geoidModel"] == "GEOID18"
        assert payload["units"] == "m"
        assert payload["lat"] == pytest.approx(site["latitude_deg"], abs=5.0e-8)
        assert payload["lon"] == pytest.approx(site["longitude_deg"], abs=5.0e-8)
        assert payload["geoidHeight"] == pytest.approx(
            approximation["geoid_undulation_N_m"],
            abs=0.0005,
        )
        assert payload["error"] == pytest.approx(
            approximation["geoid_model_error_m"],
            abs=0.0005,
        )

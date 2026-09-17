"""Offline governance for the reviewed Stage 1 primary-source corpus."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any

import pytest


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TIME_PATH = FIXTURES / "orbital_time_naif0012_reference.json"
FRAME_PATH = FIXTURES / "orbital_frames_sofa_20231011_reference.json"
CALIBRATION_PATH = FIXTURES / "horizons_orbital_elements_calibration.json"
HOLDOUT_PATH = FIXTURES / "horizons_orbital_elements_holdout.json"
CATALOG_HOLDOUT_PATH = (
    FIXTURES / "horizons_orbital_elements_catalog_holdout.json"
)
APSIDAL_PATH = FIXTURES / "horizons_apsidal_passages_reference.json"

EXPECTED_SOURCES = {
    "naif_lsk": (
        5_257,
        "678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b",
        "https://naif.jpl.nasa.gov/",
    ),
    "horizons_gm": (
        15_428,
        "169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c",
        "https://ssd.jpl.nasa.gov/",
    ),
    "iau_sofa": (
        3_686_708,
        "375729d8c0a254fd27c55484de5c8b83cccef351e1ef19d9cf7f26f5485e5538",
        "https://www.iausofa.org/",
    ),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LOCAL_PATH = re.compile(
    r"(?i)(?:^|[\s\"'(])(?:[a-z]:[\\/]|/home/|/users/|/tmp/)"
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


@pytest.mark.parametrize(
    "path",
    (
        TIME_PATH,
        FRAME_PATH,
        CALIBRATION_PATH,
        HOLDOUT_PATH,
        CATALOG_HOLDOUT_PATH,
        APSIDAL_PATH,
    ),
)
def test_orbital_fixtures_have_reviewed_schemas_and_no_local_paths(
    path: Path,
) -> None:
    payload = _load(path)
    assert payload["schema_version"] in {
        "moira.orbital-time-authority.v1",
        "moira.orbital-frame-authority.v1",
        "moira.horizons-orbital-elements.v1",
        "moira.horizons-apsidal-passages.v1",
    }
    assert payload["generator_version"] in {
        "moira-orbital-authority-builder-v1",
        "moira-horizons-orbital-elements-builder-v1",
        "moira-horizons-apsidal-passages-builder-v1",
    }
    assert not [text for text in _strings(payload) if _LOCAL_PATH.search(text)]


def test_pinned_authority_source_receipts_are_exact() -> None:
    time = _load(TIME_PATH)
    frame = _load(FRAME_PATH)
    receipts = {
        **time["sources"],
        "iau_sofa": frame["source"],
    }

    assert set(receipts) == set(EXPECTED_SOURCES)
    for key, (byte_count, sha256, url_prefix) in EXPECTED_SOURCES.items():
        receipt = receipts[key]
        assert receipt["byte_count"] == byte_count
        assert receipt["source_sha256"] == sha256
        assert receipt["source_url"].startswith(url_prefix)
        assert receipt["retrieved_utc"].endswith("Z")
        assert receipt["owner"]


def test_time_and_gravity_authority_is_complete() -> None:
    payload = _load(TIME_PATH)
    model = payload["time_model"]
    assert model == {
        "delta_t_a_seconds": 32.184,
        "eb": 0.01671,
        "equation": "TDB-TT = K*sin(M + EB*sin(M)); M evaluated at TDB",
        "fixed_point_max_iterations": 8,
        "fixed_point_residual_seconds": 1.0e-15,
        "k_seconds": 0.001657,
        "m": [6.239996, 1.99096871e-07],
    }
    assert len(payload["time_cases"]) == 5
    for case in payload["time_cases"]:
        assert all(
            math.isfinite(case[key])
            for key in ("jd_tt", "jd_tdb", "tdb_minus_tt_seconds")
        )
        assert 2 <= case["iterations"] <= model["fixed_point_max_iterations"]

    gravity = payload["gravity_model"]
    assert gravity["units"] == "km^3/s^2"
    assert gravity["assignment_rule"] == "last textual PCK assignment wins"
    assert set(gravity["values_by_naif_id"]) == {
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "199",
        "299",
        "301",
        "399",
    }
    assert all(value > 0.0 for value in gravity["values_by_naif_id"].values())


def test_frame_fixture_is_from_official_sofa_c_and_has_each_branch() -> None:
    payload = _load(FRAME_PATH)
    assert payload["compiler_oracle"] == "official IAU SOFA C 2023-10-11"
    cases = payload["cases"]
    assert len(cases) == 12
    assert {(case["frame"], case["routine"]) for case in cases} == {
        ("MEAN_ECLIPTIC_OF_DATE", "ECM06"),
        ("MEAN_ECLIPTIC_OF_DATE", "LTECM"),
        ("TRUE_ECLIPTIC_OF_DATE", "OBL06_NUT06A_PNM06A_RX"),
    }
    for case in cases:
        assert math.isfinite(case["epoch_tt"])
        assert len(case["matrix"]) == 3
        assert all(len(row) == 3 for row in case["matrix"])
        assert all(math.isfinite(value) for row in case["matrix"] for value in row)


def _horizons_payloads() -> tuple[dict[str, Any], ...]:
    return tuple(
        _load(path)
        for path in (CALIBRATION_PATH, HOLDOUT_PATH, CATALOG_HOLDOUT_PATH)
    )


def test_horizons_calibration_and_holdout_keys_are_disjoint() -> None:
    payloads = _horizons_payloads()
    key_sets = [
        {record["case_key"] for record in payload["records"]}
        for payload in payloads
    ]
    assert key_sets[0].isdisjoint(key_sets[1])
    assert key_sets[0].isdisjoint(key_sets[2])
    assert key_sets[1].isdisjoint(key_sets[2])
    assert [payload["fixture_role"] for payload in payloads] == [
        "calibration",
        "planet_holdout",
        "catalog_holdout",
    ]


@pytest.mark.parametrize(
    "path",
    (CALIBRATION_PATH, HOLDOUT_PATH, CATALOG_HOLDOUT_PATH),
)
def test_horizons_records_have_exact_tdb_request_and_response_receipts(
    path: Path,
) -> None:
    payload = _load(path)
    assert payload["source_url"] == "https://ssd.jpl.nasa.gov/api/horizons.api"
    assert payload["records"]
    for record in payload["records"]:
        vectors = record["requests"]["vectors"]
        elements = record["requests"]["elements"]
        for request in (vectors, elements):
            assert request["TIME_TYPE"].strip("'") == "TDB"
            assert request["TLIST_TYPE"].strip("'") == "JD"
            assert request["CENTER"] == elements["CENTER"]
            assert request["TLIST"] == elements["TLIST"]
            assert request["MAKE_EPHEM"] == "YES"
        assert vectors["EPHEM_TYPE"] == "VECTORS"
        assert vectors["REF_SYSTEM"] == "ICRF"
        assert vectors["REF_PLANE"] == "FRAME"
        assert vectors["VEC_CORR"] == "NONE"
        assert elements["EPHEM_TYPE"] == "ELEMENTS"
        assert elements["REF_SYSTEM"] == "J2000"
        assert elements["REF_PLANE"] == "ECLIPTIC"
        assert elements["OUT_UNITS"] == "AU-D"

        responses = record["responses"]
        for prefix in ("vectors", "elements"):
            assert _SHA256.fullmatch(responses[f"{prefix}_sha256"])
            assert responses[f"{prefix}_byte_count"] > 100
        authority = record["authority"]
        assert authority["api_version"] == "1.2"
        assert authority["api_source"] == "NASA/JPL Horizons API"
        assert authority["target_body_line"].startswith("Target body name:")
        assert authority["center_body_line"].startswith("Center body name:")
        assert authority["target_solution"]
        assert authority["keplerian_gm_au3_day2"] > 0.0
        assert authority["output_type"] == "GEOMETRIC osculating elements"
        assert authority["reference_frame"] == "Ecliptic of J2000.0"
        assert record["source"]["generator_version"] == payload["generator_version"]
        assert record["source"]["retrieved_utc"].endswith("Z")

        assert all(
            math.isfinite(value)
            for value in record["vector_icrf_km_km_s"].values()
        )
        assert all(
            math.isfinite(value)
            for value in record["elements_j2000_ecliptic_au_day"].values()
        )


def test_apsidal_fixture_is_disjoint_exact_tdb_primary_evidence() -> None:
    payload = _load(APSIDAL_PATH)
    assert payload["source_url"] == "https://ssd.jpl.nasa.gov/api/horizons.api"
    assert payload["fixture_role"] == "disjoint_calibration_and_holdout"
    assert payload["acceptance_gates"] == {
        "distance_absolute_au": 1.0e-9,
        "event_time_absolute_days": 1.0e-4,
    }
    records = payload["records"]
    assert {record["body"] for record in records} == {
        "Mercury",
        "Venus",
        "Earth",
        "Earth-Moon Barycenter",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
        "Eros",
        "Chiron",
        "1P/Halley",
        "2P/Encke",
        "Sedna",
        "Eris",
    }
    role_keys = {
        role: {
            record["case_key"]
            for record in records
            if record["fixture_role"] == role
        }
        for role in ("calibration", "holdout")
    }
    assert role_keys["calibration"]
    assert role_keys["holdout"]
    assert role_keys["calibration"].isdisjoint(role_keys["holdout"])

    for record in records:
        assert record["coordinate_contract"] == {
            "distance_unit": "AU",
            "reference_plane": "FRAME",
            "reference_system": "ICRF",
            "time_scale": "TDB",
            "vector_correction": "NONE",
            "velocity_unit": "km/s",
        }
        coarse = record["coarse_search"]
        request = coarse["request"]
        assert request["TIME_TYPE"].strip("'") == "TDB"
        assert request["EPHEM_TYPE"] == "VECTORS"
        assert request["REF_SYSTEM"] == "ICRF"
        assert request["REF_PLANE"] == "FRAME"
        assert request["VEC_CORR"] == "NONE"
        assert _SHA256.fullmatch(coarse["response"]["sha256"])
        assert coarse["response"]["byte_count"] > 100

        assert record["events"]
        for event in record["events"]:
            assert event["kind"] in {"PERICENTER", "APOCENTER"}
            assert math.isfinite(event["epoch_tdb"])
            assert event["distance_au"] > 0.0
            assert (
                event["final_bracket_tdb"][1]
                - event["final_bracket_tdb"][0]
                <= payload["refinement_policy"]["root_tolerance_days"]
            )
            event_request = event["event_state"]["request"]
            assert event_request["TIME_TYPE"].strip("'") == "TDB"
            assert event_request["TLIST_TYPE"].strip("'") == "JD"
            assert event_request["VEC_CORR"] == "NONE"
            assert _SHA256.fullmatch(
                event["event_state"]["response"]["sha256"]
            )
            authority = event["authority"]
            assert authority["api_version"] == "1.2"
            assert authority["api_source"] == "NASA/JPL Horizons API"
            assert authority["target_body_line"].startswith(
                "Target body name:"
            )
            assert authority["center_body_line"].startswith(
                "Center body name:"
            )
            witness = event["two_sided_witness"]
            before = witness["before"]
            after = witness["after"]
            if event["kind"] == "PERICENTER":
                assert before["radial_velocity_km_s"] < 0.0
                assert after["radial_velocity_km_s"] > 0.0
                assert event["distance_au"] <= min(
                    before["distance_au"], after["distance_au"]
                )
            else:
                assert before["radial_velocity_km_s"] > 0.0
                assert after["radial_velocity_km_s"] < 0.0
                assert event["distance_au"] >= max(
                    before["distance_au"], after["distance_au"]
                )

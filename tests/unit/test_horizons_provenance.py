"""Horizons system-release provenance (invariant tests; offline).

Evidence classes in play: the release string is read from the Horizons manual (a primary
source, here replaced by fixed text); ``inferred`` and ``unrecorded`` are Moira
classifications of existing artifacts, checked against the artifacts themselves.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from moira.tools.horizons_provenance import (
    MANUAL_URL,
    HorizonsProvenanceError,
    HorizonsSystemRelease,
    classify_artifact,
    collect_retrieval_dates,
    fetch_system_release,
    manifest_release_block,
    parse_system_release,
    release_block,
)

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "tests" / "fixtures" / "horizons_system_provenance.json"
MANUAL_TEXT = (
    "Introduction\n\nVersion 4.98e (August 25, 2026)\n\nHorizons is ...\n"
    "Version 4.98d (November 21, 2025)"
)
RELEASE = HorizonsSystemRelease("4.98e", "2026-08-25", MANUAL_URL, "2026-10-31", "test")


def test_parse_takes_the_first_release_statement() -> None:
    assert parse_system_release(MANUAL_TEXT) == ("4.98e", "2026-08-25")


@pytest.mark.parametrize(
    "text",
    ["no release here", "Version 4.98e (Februar 30, 2026)", "Version 4.98e (February 30, 2026)"],
)
def test_parse_refuses_to_guess(text: str) -> None:
    with pytest.raises(HorizonsProvenanceError):
        parse_system_release(text)


def test_fetch_records_when_and_where_and_that_the_response_carries_no_release() -> None:
    seen: list[str] = []
    now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    release = fetch_system_release(fetch=lambda url: seen.append(url) or MANUAL_TEXT, now=now)
    assert seen == [MANUAL_URL]
    assert (release.version, release.release_date, release.observed_utc) == (
        "4.98e",
        "2026-08-25",
        "2026-10-31T12:00:00Z",
    )
    assert "carries no system release" in release.evidence
    assert release_block(release)["source_url"] == MANUAL_URL


def test_fetch_failure_raises_instead_of_producing_a_guess() -> None:
    def broken(_url: str) -> str:
        raise OSError("offline")

    with pytest.raises(HorizonsProvenanceError, match="offline"):
        fetch_system_release(fetch=broken)


def _payload(*dates: str) -> dict:
    return {"records": [{"source": {"retrieved_utc": f"{d}T00:00:00Z"}} for d in dates]}


def test_collect_retrieval_dates_finds_every_known_key() -> None:
    payload = {
        "a": {"retrieved_utc": "2026-09-15T20:06:43Z"},
        "b": [{"fetched_at_utc": "2026-09-26T19:08:36Z"}],
        "release": {"released_utc": "2026-10-10T12:33:17Z"},
        "c": {"retrieved_utc_date": "2026-07-18"},
    }
    assert collect_retrieval_dates(payload) == [
        "2026-07-18",
        "2026-09-15",
        "2026-09-26",
        "2026-10-10",
    ]


@pytest.mark.parametrize(
    ("payload", "expected_class", "expected_version"),
    [
        ({"horizons_system_release": {"version": "4.98e"}}, "recorded", "4.98e"),
        (_payload("2026-08-25", "2026-10-29"), "inferred", "4.98e"),
        (_payload("2026-08-24"), "unrecorded", None),
        ({"nothing": 1}, "unrecorded", None),
        (_payload("2026-08-20", "2026-09-01"), "partial", None),
        ({"horizons_system_release": {"version": None}, **_payload("2026-09-01")}, "inferred", "4.98e"),
    ],
)
def test_classification(payload: dict, expected_class: str, expected_version: str | None) -> None:
    evidence_class, version, basis = classify_artifact(payload, RELEASE)
    assert (evidence_class, version) == (expected_class, expected_version)
    assert basis


def _horizons_artifacts() -> list[str]:
    paths = sorted(
        p
        for p in glob.glob(str(ROOT / "tests/fixtures/*horizons*.json"))
        if os.path.isfile(p) and os.path.basename(p) != SIDECAR.name
    )
    paths += sorted(glob.glob(str(ROOT / "tests/fixtures/small_body_release_manifests/*.json")))
    paths += [
        str(ROOT / "moira/kernels/asteroids/manifest.json"),
        str(ROOT / "moira/kernels/comets/manifest.json"),
    ]
    return [os.path.relpath(p, ROOT).replace("\\", "/") for p in paths]


def test_every_horizons_artifact_is_classified_in_the_sidecar() -> None:
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    listed = {row["path"] for row in sidecar["artifacts"]}
    expected = set(_horizons_artifacts())
    assert expected - listed == set(), "unclassified Horizons artifact: add it to the sidecar"
    assert listed - expected == set(), "sidecar lists an artifact that is gone"


def test_sidecar_rows_match_a_fresh_classification_of_the_artifacts() -> None:
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    observed = sidecar["observed_release"]
    release = HorizonsSystemRelease(
        observed["version"],
        observed["release_date"],
        observed["source_url"],
        observed["observed_utc"],
        observed["evidence"],
    )
    assert release.source_url == MANUAL_URL
    for row in sidecar["artifacts"]:
        payload = json.loads((ROOT / row["path"]).read_text(encoding="utf-8"))
        evidence_class, version, _basis = classify_artifact(payload, release)
        assert (row["evidence_class"], row["system_release"]) == (evidence_class, version), row["path"]
        if row["evidence_class"] == "inferred":
            assert min(collect_retrieval_dates(payload)) >= release.release_date


def test_new_style_blocks_are_well_formed_wherever_they_appear() -> None:
    for relative in _horizons_artifacts():
        payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        block = payload.get("horizons_system_release") if isinstance(payload, dict) else None
        if block is not None and block.get("version"):
            required = {"version", "release_date", "source_url", "observed_utc", "evidence"}
            assert required <= set(block), relative


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_script_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(module)
    return module


def test_orbital_elements_builder_embeds_the_release_block() -> None:
    builder = _load_script("build_orbital_elements_fixtures")
    payload = builder._payload("calibration", (), "2026-10-31T00:00:00Z", RELEASE)
    assert payload["horizons_system_release"] == release_block(RELEASE)


def test_apsidal_builder_keeps_a_merged_release_only_when_candidates_agree() -> None:
    builder = _load_script("build_apsidal_passages_fixture")
    block = release_block(RELEASE)
    other = release_block(
        HorizonsSystemRelease("4.99a", "2026-12-01", MANUAL_URL, "2026-12-02", "x")
    )
    agreed = builder._merged_release_block([{"horizons_system_release": block}] * 2)
    assert agreed["version"] == "4.98e"
    for mixed in (
        [{"horizons_system_release": block}, {"horizons_system_release": other}],
        [{"horizons_system_release": block}, {}],
        [],
    ):
        merged = builder._merged_release_block(mixed)
        assert merged["version"] is None and "no single recorded" in merged["note"]


def test_comet_catalog_builder_records_the_release_in_manifest_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = _load_script("build_comet_catalog")
    monkeypatch.setattr(builder, "fetch_system_release", lambda: RELEASE)
    block = builder._catalog_provenance()["horizons_system_release_at_manifest"]
    assert block == manifest_release_block(RELEASE)
    assert "shards may have been retrieved earlier" in block["scope"]


def test_unified_asteroid_builder_records_the_release_in_manifest_provenance() -> None:
    source = (ROOT / "scripts" / "build_unified_asteroid_catalog.py").read_text(encoding="utf-8")
    assert (
        '"horizons_system_release_at_manifest": manifest_release_block(fetch_system_release())'
        in source
    )

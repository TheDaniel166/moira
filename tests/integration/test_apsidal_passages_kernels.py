"""Offline DE441/catalog checks against frozen official Horizons passages."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from moira._ephemeris_time import _ephemeris_tt_to_ut1
from moira._orbital_errors import (
    OrbitalBodyNotLoadedError,
    OrbitalCoverageError,
    OrbitalKernelMissingError,
)
from moira.julian import tdb_to_tt
from moira.orbits import (
    ApsidalDirection,
    ApsidalPassageStatus,
    OrbitalCenter,
    apsidal_passages,
)


_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "horizons_apsidal_passages_reference.json"
)
_FIXTURE_BYTES = _FIXTURE_PATH.read_bytes()
_FIXTURE_SHA256 = hashlib.sha256(_FIXTURE_BYTES).hexdigest()
_FIXTURE = json.loads(_FIXTURE_BYTES)
_PLANETARY_RECORDS = tuple(
    record
    for record in _FIXTURE["records"]
    if record["body_naif_id"] < 1_000_000
)
_CATALOG_RECORDS = tuple(
    record
    for record in _FIXTURE["records"]
    if record["body_naif_id"] >= 1_000_000
)


def _catalog_passage_admission(record) -> dict | None:
    """Return a governed release's Stage 2 accuracy admission, if present."""

    from moira._kernel_paths import find_all_small_body_manifests

    target = record["body_naif_id"]
    for manifest_path in find_all_small_body_manifests():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        body_ids = {
            body_id
            for shard in manifest.get("shards", ())
            for body_id in shard.get("bodies", ())
        }
        if target not in body_ids:
            continue
        validation = manifest.get("validation", {})
        admission = validation.get("apsidal_passages")
        return admission if isinstance(admission, dict) else None
    return None


def _assert_matches_frozen_horizons(record, reader) -> None:
    start_ut1 = _ephemeris_tt_to_ut1(
        tdb_to_tt(record["start_jd_tdb"]),
        reader,
    )
    result = apsidal_passages(
        record["body"],
        start_ut1,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        reader=reader,
    )
    gates = _FIXTURE["acceptance_gates"]
    for event in record["events"]:
        outcome = (
            result.pericenter
            if event["kind"] == "PERICENTER"
            else result.apocenter
        )
        assert outcome.status is ApsidalPassageStatus.FOUND
        assert outcome.epoch_tdb is not None
        assert outcome.distance_au is not None
        assert outcome.epoch_tdb == pytest.approx(
            event["epoch_tdb"],
            abs=gates["event_time_absolute_days"],
        )
        assert outcome.distance_au == pytest.approx(
            event["distance_au"],
            abs=gates["distance_absolute_au"],
        )


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "record",
    _PLANETARY_RECORDS,
    ids=[record["body"] for record in _PLANETARY_RECORDS],
)
def test_planetary_apsidal_passages_match_frozen_horizons(
    record,
    planetary_reader,
) -> None:
    _assert_matches_frozen_horizons(record, planetary_reader)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "record",
    _CATALOG_RECORDS,
    ids=[record["body"] for record in _CATALOG_RECORDS],
)
def test_catalog_apsidal_passages_match_frozen_horizons_when_loaded(
    record,
    receipted_small_body_reader_pool,
) -> None:
    admission = _catalog_passage_admission(record)
    if admission is None:
        pytest.skip(
            f"the governed catalog containing {record['body']} has no "
            "reviewed Stage 2 apsidal-passage accuracy admission"
        )
    assert admission["reference_fixture_sha256"] == _FIXTURE_SHA256
    assert admission["acceptance_gates"] == _FIXTURE["acceptance_gates"]
    try:
        _assert_matches_frozen_horizons(
            record,
            receipted_small_body_reader_pool,
        )
    except (
        OrbitalBodyNotLoadedError,
        OrbitalCoverageError,
        OrbitalKernelMissingError,
    ) as exc:
        pytest.skip(
            f"governed runtime prerequisite unavailable for "
            f"{record['body']}: {type(exc).__name__}"
        )


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_loaded_eros_passage_search_is_runnable_without_claiming_authority_parity(
    receipted_small_body_reader_pool,
) -> None:
    record = next(record for record in _CATALOG_RECORDS if record["body"] == "Eros")
    start_ut1 = _ephemeris_tt_to_ut1(
        tdb_to_tt(record["start_jd_tdb"]),
        receipted_small_body_reader_pool,
    )
    result = apsidal_passages(
        "Eros",
        start_ut1,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        reader=receipted_small_body_reader_pool,
    )
    assert result.pericenter.status is ApsidalPassageStatus.FOUND
    assert result.apocenter.status is ApsidalPassageStatus.FOUND
    assert any(
        leg.catalog_id in {"moira-asteroids", "moira-asteroids-wheel"}
        for leg in result.provenance.state_source.legs
    )

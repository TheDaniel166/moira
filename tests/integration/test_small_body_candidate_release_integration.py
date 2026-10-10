"""Explicit, fail-closed integration of unpublished adaptive catalog views.

Set MOIRA_TEST_ASTEROID_CANDIDATE_RELEASE and MOIRA_TEST_COMET_CANDIDATE_RELEASE
to separately sealed validation directories. No ambient/installed catalog can
silently supply a body in this suite. Frozen authority gates remain unchanged.
"""

from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path

import pytest

from moira._ephemeris_time import _bind_ephemeris_time
from moira._spk_body_kernel import small_body_readers_from_manifest
from moira.julian import tdb_to_tt
from moira.orbits import (
    ApsidalDirection, ApsidalPassageStatus, OrbitalCenter, OrbitalFrame,
    apsidal_passages, osculating_elements,
)
from moira.planetary_nodes import _geometric_node_computation
from moira.small_body_catalog_release import verify_release
from moira.spk_reader import KernelPool, SpkReader
from support.orbital_catalog_admission import ACCEPTANCE_GATES, CATALOG_RECORDS


ROOT = Path(__file__).resolve().parents[2]
ENV = {
    "moira-asteroids": "MOIRA_TEST_ASTEROID_CANDIDATE_RELEASE",
    "moira-comets": "MOIRA_TEST_COMET_CANDIDATE_RELEASE",
}
EXPECTED = {"moira-asteroids": (11223, 449), "moira-comets": (497, 20)}
COMET_RECEIPT = json.loads((ROOT / "tests/artifacts/oracle/"
    "comet_type13_catalog_candidate_admission_2026-10-01.json").read_text())
ANCHORED_ROOT = ROOT / "tests/fixtures/horizons_asteroid_apsidal_anchored_2026_10_03"
ANCHORED_REVIEW = json.loads((ANCHORED_ROOT / "source_review.json").read_bytes())
ANCHORED_REPORT = json.loads((ANCHORED_ROOT / "report.json").read_bytes())
ASTEROID_PASSAGES = tuple(
    {**record, "events": [event for event in ANCHORED_REPORT["events"]
                          if event["body_naif_id"] == record["body_naif_id"]]}
    for record in ANCHORED_REVIEW["records"]
)

pytestmark = [pytest.mark.integration, pytest.mark.requires_ephemeris]


@pytest.fixture(scope="module")
def candidate_catalogs():
    configured = {key: os.environ.get(name) for key, name in ENV.items()}
    if not any(configured.values()):
        pytest.skip("explicit sealed adaptive candidate views not configured")
    assert all(configured.values()), "both explicit candidate views are required"
    assert ANCHORED_REVIEW["status"] == "reviewed_for_validation_only_integration"
    assert hashlib.sha256((ANCHORED_ROOT / "report.json").read_bytes()).hexdigest() == (
        ANCHORED_REVIEW["report_sha256"]
    )
    assert ANCHORED_REPORT["acceptance_gates"] == ANCHORED_REVIEW["acceptance_gates"] == {
        "event_time_absolute_days": 0.0001, "distance_absolute_au": 1e-9,
    }
    catalogs = {}
    for catalog_id, root in configured.items():
        path = Path(root)
        verification = verify_release(path)
        manifest = json.loads((path / "manifest.json").read_bytes())
        assert verification.catalog_id == catalog_id
        assert ".validation" in verification.catalog_version
        assert (verification.body_count, verification.shard_count) == EXPECTED[catalog_id]
        assert manifest["sampling"]["mode"] == "certified_adaptive_radial_extrema"
        catalogs[catalog_id] = (path, manifest, verification)
    assert catalogs["moira-comets"][1]["release"]["source_manifest_sha256"] == (
        COMET_RECEIPT["catalog"]["manifest_sha256"]
    )
    assert catalogs["moira-asteroids"][1]["release"]["source_manifest_sha256"] == (
        ANCHORED_REVIEW["source_catalog_manifest_sha256"]
    )
    return catalogs


@pytest.fixture(scope="module")
def candidate_pool(candidate_catalogs, planetary_kernel_path):
    # Production receipt loader and native readers; exact explicit manifests,
    # no discovery patch or admission/accuracy bypass.
    with ExitStack() as resources:
        primary = SpkReader(planetary_kernel_path)
        resources.callback(primary.close)
        readers = [primary]
        for path, manifest, _ in candidate_catalogs.values():
            supplemental = small_body_readers_from_manifest(path / "manifest.json")
            for reader in supplemental:
                resources.callback(reader.close)
                readers.append(reader)
            assert len(supplemental) == manifest["shard_count"]
            for reader, shard in zip(supplemental, manifest["shards"]):
                assert isinstance(reader._catalog, dict)
                segments = reader._kernel.segments
                assert {segment.target for segment in segments} == set(shard["bodies"])
                assert all(segment.center == 10 and segment.frame == 1
                           and segment.data_type == 13 for segment in segments)
        yield KernelPool(tuple(readers))


def _ut1(epoch_tdb, reader):
    jd = tdb_to_tt(epoch_tdb)
    for _ in range(8):
        residual = epoch_tdb - _bind_ephemeris_time(jd, reader).epoch_tdb
        if abs(residual) <= math.ulp(epoch_tdb):
            return jd
        jd += residual
    raise AssertionError(f"could not bind exact JD(TDB) {epoch_tdb}")


def _epoch(intervals):
    admitted = [(max(start, 2415021.0), min(end, 2488069.0))
                for start, end in intervals
                if max(start, 2415021.0) <= min(end, 2488069.0)]
    assert admitted, "body has no coverage inside the true-date frame interval"
    for start, end in admitted:
        if start <= 2460676.5 <= end:
            return 2460676.5
    start, end = max(admitted, key=lambda pair: pair[1] - pair[0])
    return (start + end) / 2


def _source(result, catalog, body_id):
    _, manifest, verified = catalog
    expected_shard = next(s for s in manifest["shards"] if body_id in s["bodies"])
    legs = result.provenance.state_source.legs
    matches = [leg for leg in legs if leg.catalog_id == verified.catalog_id]
    assert matches
    assert all(leg.catalog_version == verified.catalog_version
               and leg.manifest_sha256 == verified.manifest_sha256
               and leg.kernel_sha256 == expected_shard["sha256"]
               and leg.kernel_bytes == expected_shard["bytes"] for leg in matches)


@pytest.mark.slow
@pytest.mark.parametrize("catalog_id", tuple(EXPECTED))
def test_every_candidate_body_has_exact_release_bound_elements_and_nodes(
    catalog_id, candidate_catalogs, candidate_pool, record_property,
):
    catalog = candidate_catalogs[catalog_id]
    _, manifest, verified = catalog
    seen = set()
    ut_cache = {}
    for shard in manifest["shards"]:
        for body_id in shard["bodies"]:
            assert body_id not in seen
            seen.add(body_id)
            intervals = candidate_pool.coverage_intervals_tdb(10, body_id)
            assert intervals
            epoch = _epoch(intervals)
            if epoch not in ut_cache:
                ut_cache[epoch] = _ut1(epoch, candidate_pool)
            jd = ut_cache[epoch]
            elements = osculating_elements(body_id, jd, center=OrbitalCenter.SUN,
                frame=OrbitalFrame.J2000_ECLIPTIC, reader=candidate_pool)
            assert elements.epoch_tdb == epoch
            assert all(math.isfinite(v) for v in (
                elements.eccentricity, elements.pericenter_distance_au,
                elements.inclination_deg, elements.lon_ascending_node_deg,
            ))
            _source(elements, catalog, body_id)
            computation = _geometric_node_computation(body_id, jd, candidate_pool)
            node = computation.node
            assert computation.elements.epoch_tdb == epoch
            assert computation.elements.provenance.frame_construction.router_branch == "modern_true"
            assert node.ascending_node == computation.elements.lon_ascending_node_deg
            assert node.perihelion == computation.elements.pericenter_ecliptic_lon_deg
            assert all(math.isfinite(v) for v in (
                node.ascending_node, node.perihelion, node.aphelion,
                node.inclination, node.eccentricity, node.semi_major_axis,
            ))
            _source(computation.elements, catalog, body_id)
    assert len(seen) == verified.body_count
    record_property("bodies_checked", len(seen))
    record_property("catalog_id", verified.catalog_id)
    record_property("catalog_version", verified.catalog_version)
    record_property("manifest_sha256", verified.manifest_sha256)


@pytest.mark.parametrize("record", tuple(r for r in CATALOG_RECORDS
    if r["body_naif_id"] >= 2000000), ids=lambda r: r["body"])
def test_candidate_asteroid_elements_match_frozen_primary_holdouts(
    record, candidate_catalogs, candidate_pool,
):
    result = osculating_elements(record["body_naif_id"],
        _ut1(record["jd_tdb"], candidate_pool), center=OrbitalCenter.SUN,
        frame=OrbitalFrame.J2000_ECLIPTIC, reader=candidate_pool)
    expected = record["elements_j2000_ecliptic_au_day"]
    scalar = {"semi_major_axis_au": "semi_major_axis_au",
              "eccentricity": "eccentricity",
              "pericenter_distance_au": "perihelion_distance_au",
              "apocenter_distance_au": "aphelion_distance_au"}
    for field, source in scalar.items():
        gate = {"semi_major_axis_au": "semi_major_axis_absolute_au",
                "eccentricity": "eccentricity_absolute",
                "pericenter_distance_au": "pericenter_distance_absolute_au",
                "apocenter_distance_au": "apocenter_distance_absolute_au"}[field]
        assert abs(getattr(result, field) - expected[source]) <= ACCEPTANCE_GATES[gate]
    for field, source, gate in (
        ("inclination_deg", "inclination_deg", "inclination_absolute_deg"),
        ("lon_ascending_node_deg", "lon_ascending_node_deg", "node_angular_absolute_deg"),
        ("arg_pericenter_deg", "arg_perihelion_deg", "arg_pericenter_angular_absolute_deg"),
        ("mean_anomaly_deg", "mean_anomaly_deg", "mean_anomaly_angular_absolute_deg"),
    ):
        error = abs((getattr(result, field) - expected[source] + 180) % 360 - 180)
        assert error <= ACCEPTANCE_GATES[gate]
    _source(result, candidate_catalogs["moira-asteroids"], record["body_naif_id"])


@pytest.mark.parametrize("record", ASTEROID_PASSAGES, ids=lambda r: r["body"])
def test_candidate_asteroid_passages_match_anchored_primary_events(
    record, candidate_catalogs, candidate_pool,
):
    result = apsidal_passages(record["body_naif_id"],
        _ut1(record["start_jd_tdb"], candidate_pool), center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT, reader=candidate_pool)
    for expected in record["events"]:
        event = result.pericenter if expected["kind"] == "PERICENTER" else result.apocenter
        assert event.status is ApsidalPassageStatus.FOUND
        assert abs(event.epoch_tdb - expected["authority_epoch_tdb"]) <= 0.0001
        assert abs(event.distance_au - expected["authority_distance_au"]) <= 1e-9
    _source(result, candidate_catalogs["moira-asteroids"], record["body_naif_id"])


@pytest.mark.parametrize("body_id,body", ((1000001, "1P/Halley"), (1000002, "2P/Encke")))
def test_candidate_comet_passages_match_endpoint_anchored_primary_oracle(
    body_id, body, candidate_catalogs, candidate_pool,
):
    result = apsidal_passages(body_id, _ut1(2460676.5, candidate_pool),
        center=OrbitalCenter.SUN, direction=ApsidalDirection.NEXT, reader=candidate_pool)
    measurements = [m for m in COMET_RECEIPT["anchored_apsidal_oracle"]["measurements"]
                    if m["body"] == body]
    assert measurements
    gates = COMET_RECEIPT["acceptance_gates"]
    assert gates["event_time_absolute_seconds"] == 8.64
    assert gates["distance_absolute_au"] == 1e-9
    for expected in measurements:
        event = result.pericenter if expected["kind"] == "PERICENTER" else result.apocenter
        assert event.status is ApsidalPassageStatus.FOUND
        assert abs(event.epoch_tdb - expected["authority_epoch_tdb"]) * 86400 <= 8.64
        assert abs(event.distance_au - expected["authority_distance_au"]) <= 1e-9
    _source(result, candidate_catalogs["moira-comets"], body_id)

"""Release-host Stage 3 validation for every sovereign catalog member."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import _bind_ephemeris_time
from moira._kernel_paths import find_all_small_body_manifests
from moira._orbital_frames import MODERN_FRAME_INTERVAL_TT
from moira._orbital_state import resolve_orbital_body
from moira.julian import tdb_to_tt
from moira.planetary_nodes import _geometric_node_computation
from moira.small_body_catalog_release import verify_release


FULL_ASTEROID_ID = ("moira-asteroids", "2026.08.12.1")
FULL_COMET_ID = ("moira-comets", "2026.07.28.1")
REQUIRED_RELEASES = (FULL_ASTEROID_ID, FULL_COMET_ID)


def _installed_release_manifests() -> dict[tuple[str, str], Path]:
    result: dict[tuple[str, str], Path] = {}
    for path in find_all_small_body_manifests():
        payload = json.loads(path.read_text(encoding="utf-8"))
        key = (payload.get("catalog_id"), payload.get("catalog_version"))
        if all(isinstance(value, str) for value in key):
            result[key] = path
    return result


INSTALLED = _installed_release_manifests()


def _release_parameter(key: tuple[str, str]):
    catalog_id, catalog_version = key
    return pytest.param(
        key,
        id=f"{catalog_id}@{catalog_version}",
        marks=pytest.mark.skipif(
            key not in INSTALLED,
            reason=f"NOT RUN - full {catalog_id}@{catalog_version} release not installed",
        ),
    )


def _manifest_body_ids(manifest: dict) -> tuple[int, ...]:
    return tuple(
        int(body_id)
        for shard in manifest["shards"]
        for body_id in shard["bodies"]
    )


def _representative_true_date_epoch(
    intervals: tuple[tuple[float, float], ...],
) -> float:
    # One day inside the TT model boundary also safely absorbs the millisecond-
    # scale TT/TDB periodic difference when this TDB instant is rebound to UT1.
    lower = MODERN_FRAME_INTERVAL_TT[0] + 1.0
    upper = MODERN_FRAME_INTERVAL_TT[1] - 1.0
    admitted = tuple(
        (max(start, lower), min(end, upper))
        for start, end in intervals
        if max(start, lower) <= min(end, upper)
    )
    assert admitted, "catalog body has no coverage inside the true-date frame model"

    preferred = 2460676.5
    for start, end in admitted:
        if start <= preferred <= end:
            return preferred
    start, end = max(admitted, key=lambda item: item[1] - item[0])
    return start + (end - start) / 2.0


def _ut1_for_exact_tdb(epoch_tdb: float, reader) -> float:
    jd_ut1 = tdb_to_tt(epoch_tdb)
    for _ in range(8):
        bound = _bind_ephemeris_time(jd_ut1, reader)
        residual = epoch_tdb - bound.epoch_tdb
        if abs(residual) <= math.ulp(epoch_tdb):
            return jd_ut1
        jd_ut1 += residual
    raise AssertionError(f"could not bind exact JD(TDB) {epoch_tdb:.12f}")


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    "release_key",
    tuple(_release_parameter(key) for key in REQUIRED_RELEASES),
)
def test_every_full_catalog_body_has_a_receipted_finite_geometric_node(
    release_key,
    receipted_small_body_reader_pool,
) -> None:
    manifest_path = INSTALLED[release_key]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verification = verify_release(manifest_path.parent)
    body_ids = _manifest_body_ids(manifest)
    assert len(body_ids) == manifest["body_count"]
    assert len(body_ids) == len(set(body_ids))

    pool = receipted_small_body_reader_pool
    ut_cache: dict[float, float] = {}
    seen: set[int] = set()
    for body_id in body_ids:
        assert body_id not in seen
        seen.add(body_id)
        resolved = resolve_orbital_body(body_id)
        intervals = pool.coverage_intervals_tdb(10, body_id)
        assert intervals
        epoch_tdb = _representative_true_date_epoch(intervals)
        if epoch_tdb not in ut_cache:
            ut_cache[epoch_tdb] = _ut1_for_exact_tdb(epoch_tdb, pool)

        computation = _geometric_node_computation(
            body_id,
            ut_cache[epoch_tdb],
            pool,
        )
        node = computation.node
        elements = computation.elements
        assert node.planet == resolved.name
        assert node.ascending_node == elements.lon_ascending_node_deg
        assert node.perihelion == elements.pericenter_ecliptic_lon_deg
        assert node.inclination == elements.inclination_deg
        assert node.eccentricity == elements.eccentricity
        assert node.semi_major_axis == elements.semi_major_axis_au
        assert all(
            math.isfinite(value)
            for value in (
                node.ascending_node,
                node.perihelion,
                node.aphelion,
                node.inclination,
                node.eccentricity,
                node.semi_major_axis,
            )
        )
        assert 0.0 <= node.ascending_node < 360.0
        assert 0.0 <= node.perihelion < 360.0
        assert 0.0 <= node.aphelion < 360.0
        assert elements.epoch_tdb == epoch_tdb
        assert elements.provenance.frame_construction.router_branch == "modern_true"

        catalog_legs = [
            leg
            for leg in elements.provenance.state_source.legs
            if (leg.catalog_id, leg.catalog_version) == release_key
        ]
        assert catalog_legs
        assert all(
            leg.manifest_sha256 == verification.manifest_sha256
            and leg.kernel_sha256
            and leg.kernel_bytes > 0
            for leg in catalog_legs
        )

    assert len(seen) == manifest["body_count"]

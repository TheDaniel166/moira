"""Release-host validation for every sovereign small-body catalog member."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import _bind_ephemeris_time
from moira._kernel_paths import find_all_small_body_manifests
from moira._orbital_state import resolve_orbital_body
from moira.julian import tdb_to_tt
from moira.orbits import OrbitalCenter, OrbitalFrame, osculating_elements
from moira.small_body_catalog_release import verify_release


FULL_ASTEROID_ID = ("moira-asteroids", "2026.08.12.1")
FULL_COMET_ID = ("moira-comets", "2026.07.28.1")


def _installed_release_manifests() -> dict[tuple[str, str], Path]:
    result: dict[tuple[str, str], Path] = {}
    for path in find_all_small_body_manifests():
        payload = json.loads(path.read_text(encoding="utf-8"))
        key = (payload.get("catalog_id"), payload.get("catalog_version"))
        if all(isinstance(value, str) for value in key):
            result[key] = path
    return result


INSTALLED = _installed_release_manifests()
MISSING_FULL_ASTEROID = FULL_ASTEROID_ID not in INSTALLED
MISSING_FULL_COMET = FULL_COMET_ID not in INSTALLED

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_ephemeris,
    pytest.mark.slow,
    pytest.mark.skipif(
        MISSING_FULL_ASTEROID,
        reason=(
            "NOT RUN - full moira-asteroids@2026.08.12.1 release not installed"
        ),
    ),
    pytest.mark.skipif(
        MISSING_FULL_COMET,
        reason="NOT RUN - full moira-comets@2026.07.28.1 release not installed",
    ),
]


def _manifest_body_ids(manifest: dict) -> tuple[int, ...]:
    return tuple(
        int(body_id)
        for shard in manifest["shards"]
        for body_id in shard["bodies"]
    )


def _representative_epoch(intervals: tuple[tuple[float, float], ...]) -> float:
    preferred = 2460676.5
    for start, end in intervals:
        if start <= preferred <= end:
            return preferred
    start, end = max(intervals, key=lambda item: item[1] - item[0])
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


def test_every_full_catalog_body_has_receipted_finite_elements(
    receipted_small_body_reader_pool,
) -> None:
    small_body_reader_pool = receipted_small_body_reader_pool
    manifests = {
        key: json.loads(path.read_text(encoding="utf-8"))
        for key, path in INSTALLED.items()
        if key in {FULL_ASTEROID_ID, FULL_COMET_ID}
    }
    verifications = {
        key: verify_release(path.parent) for key, path in INSTALLED.items()
        if key in manifests
    }
    seen: set[int] = set()
    ut_cache: dict[float, float] = {}

    for key, manifest in manifests.items():
        body_ids = _manifest_body_ids(manifest)
        assert len(body_ids) == manifest["body_count"]
        assert len(body_ids) == len(set(body_ids))
        for body_id in body_ids:
            assert body_id not in seen
            seen.add(body_id)
            assert resolve_orbital_body(body_id) == resolve_orbital_body(body_id)

            intervals = small_body_reader_pool.coverage_intervals_tdb(10, body_id)
            assert intervals
            epoch_tdb = _representative_epoch(intervals)
            state = small_body_reader_pool.position_and_velocity_tdb_with_receipt(
                10, body_id, epoch_tdb
            )
            assert all(math.isfinite(value) for value in state.position_km)
            assert all(math.isfinite(value) for value in state.velocity_km_per_day)
            assert state.covered_intervals_tdb

            if epoch_tdb not in ut_cache:
                ut_cache[epoch_tdb] = _ut1_for_exact_tdb(
                    epoch_tdb, small_body_reader_pool
                )
            jd_ut1 = ut_cache[epoch_tdb]
            result = osculating_elements(
                body_id,
                jd_ut1,
                center=OrbitalCenter.SUN,
                frame=OrbitalFrame.J2000_ECLIPTIC,
                reader=small_body_reader_pool,
            )
            assert result.epoch_tdb == epoch_tdb
            assert math.isfinite(result.eccentricity)
            assert math.isfinite(result.pericenter_distance_au)

            catalog_legs = [
                leg
                for leg in result.provenance.state_source.legs
                if (leg.catalog_id, leg.catalog_version) == key
            ]
            assert catalog_legs
            assert all(
                leg.manifest_sha256 == verifications[key].manifest_sha256
                and leg.kernel_sha256
                and leg.kernel_bytes > 0
                for leg in catalog_legs
            )

    expected = sum(manifest["body_count"] for manifest in manifests.values())
    assert len(seen) == expected

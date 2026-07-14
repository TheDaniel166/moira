import json
import math
from pathlib import Path

import pytest

from moira._kernel_paths import find_all_small_body_manifests, find_planetary_kernel
from moira._spk_body_kernel import small_body_readers_from_manifest
from moira.asteroids import asteroid_at
from moira.comets import COMET_NAIF, comet_at
from moira.spk_reader import KernelPool, OutOfRangeError, SpkReader, use_reader_override

_ONE_SECOND_JD = 1.0 / 86400.0
_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "horizons_asteroid_reference.json"
_THRESHOLD_OBSERVER_ARCSEC = 5.0
_SMOOTH_STEP_LIMIT_DEG = 1e-3
_SMOOTH_STEP_MISMATCH_DEG = 1e-4
def _load_cases() -> list[dict]:
    if not _FIXTURE.exists():
        return []
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return [c for c in data.get("cases", []) if "error" not in c]


def _threshold_for(case: dict) -> float:
    return _THRESHOLD_OBSERVER_ARCSEC


def _angle_diff_arcsec(a: float, b: float) -> float:
    delta_deg = ((a - b + 180.0) % 360.0) - 180.0
    return delta_deg * 3600.0


def _signed_angle_delta(start_deg: float, end_deg: float) -> float:
    return ((end_deg - start_deg + 180.0) % 360.0) - 180.0


@pytest.fixture(scope="module")
def native_small_body_reader_pool() -> KernelPool:
    planetary_path = find_planetary_kernel()
    if planetary_path is None:
        pytest.skip("No planetary kernel is installed")

    readers = [SpkReader(planetary_path)]
    try:
        manifests = find_all_small_body_manifests()
        if not manifests:
            pytest.skip("No small-body shard manifest is installed")

        for manifest_path in manifests:
            readers.extend(small_body_readers_from_manifest(manifest_path))
        if len(readers) == 1:
            pytest.skip("Installed small-body manifests contain no shards")

        pool = KernelPool(readers)
        yield pool
    finally:
        for reader in reversed(readers):
            try:
                reader.close()
            except Exception:
                pass


_CASES = _load_cases()
_CASE_IDS = [f"{case['body']}-{case['label']}" for case in _CASES]


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.skipif(
    not _FIXTURE.exists(),
    reason="tracked horizons_asteroid_reference.json fixture is missing",
)
@pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
def test_asteroid_fixture_cases_match_under_native_reader_pool(
    case: dict,
    native_small_body_reader_pool: KernelPool,
) -> None:
    with use_reader_override(native_small_body_reader_pool):
        reader = native_small_body_reader_pool
        result = asteroid_at(case["body"], case["jd_ut"], reader=reader)
        lon_err_arcsec = _angle_diff_arcsec(result.longitude, case["ecl_lon_deg"])
        lat_err_arcsec = (result.latitude - case["ecl_lat_deg"]) * 3600.0
        threshold = _threshold_for(case)
        src = case.get("ref_source", "observer")

        assert abs(lon_err_arcsec) <= threshold, (
            f"{case['body']} @ {case['label']} [{src}]: longitude error {lon_err_arcsec:+.3f}\" "
            f"exceeds {threshold}\" threshold"
        )
        assert abs(lat_err_arcsec) <= threshold, (
            f"{case['body']} @ {case['label']} [{src}]: latitude error {lat_err_arcsec:+.3f}\" "
            f"exceeds {threshold}\" threshold"
        )


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("body_name", "jd_ut"),
    (
        ("Ceres", 2451545.0),
        ("Chiron", 2451545.0),
        ("Pandora", 2451545.0),
        ("Eros", 2451545.0),
        ("Halley", 2451545.0),
    ),
)
def test_small_body_public_positions_remain_smooth_over_one_second(
    body_name: str,
    jd_ut: float,
    native_small_body_reader_pool: KernelPool,
) -> None:
    with use_reader_override(native_small_body_reader_pool):
        reader = native_small_body_reader_pool
        if body_name in COMET_NAIF:
            before = comet_at(body_name, jd_ut - _ONE_SECOND_JD, reader=reader)
            current = comet_at(body_name, jd_ut, reader=reader)
            after = comet_at(body_name, jd_ut + _ONE_SECOND_JD, reader=reader)
        else:
            before = asteroid_at(body_name, jd_ut - _ONE_SECOND_JD, reader=reader)
            current = asteroid_at(body_name, jd_ut, reader=reader)
            after = asteroid_at(body_name, jd_ut + _ONE_SECOND_JD, reader=reader)

        before_step_deg = _signed_angle_delta(before.longitude, current.longitude)
        after_step_deg = _signed_angle_delta(current.longitude, after.longitude)
        step_mismatch_deg = after_step_deg - before_step_deg

        assert math.isfinite(before.longitude)
        assert math.isfinite(current.longitude)
        assert math.isfinite(after.longitude)
        assert abs(before_step_deg) < _SMOOTH_STEP_LIMIT_DEG, (body_name, before_step_deg)
        assert abs(after_step_deg) < _SMOOTH_STEP_LIMIT_DEG, (body_name, after_step_deg)
        assert abs(step_mismatch_deg) < _SMOOTH_STEP_MISMATCH_DEG, (body_name, step_mismatch_deg)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_small_body_kernels_fail_cleanly_outside_body_coverage(
    native_small_body_reader_pool: KernelPool,
) -> None:
    representative_targets = (
        2000433,
        2000001,
        2002060,
        2000055,
        1000001,
    )
    coverage = native_small_body_reader_pool.coverage()

    for naif_id in representative_targets:
        key = next((pair for pair in coverage if pair[1] == naif_id), None)
        assert key is not None, f"Manifest-backed pool does not contain NAIF {naif_id}"
        center = key[0]
        start_jd, end_jd = coverage[key]
        with pytest.raises(OutOfRangeError, match="No kernel covers"):
            native_small_body_reader_pool.position(center, naif_id, start_jd - 1.0)
        with pytest.raises(OutOfRangeError, match="No kernel covers"):
            native_small_body_reader_pool.position(center, naif_id, end_jd + 1.0)

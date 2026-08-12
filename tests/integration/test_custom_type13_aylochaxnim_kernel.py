from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira._spk_body_kernel import SmallBodyKernel
from moira.asteroids import asteroid_at
from moira.julian import julian_day
from moira.spk_reader import KernelPool, SpkReader, use_reader_override
from support.horizons_observer import angle_diff_arcsec, observer_ecliptic_horizons

_ROOT = Path(__file__).resolve().parents[2]
_META = _ROOT / "tests" / "artifacts" / "kernels" / "aylochaxnim_type13_test.metadata.json"


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_custom_aylochaxnim_type13_kernel_round_trips_through_public_asteroid_api() -> None:
    if not _META.exists():
        pytest.skip("aylochaxnim type13 metadata artifact is missing")

    payload = json.loads(_META.read_text(encoding="utf-8"))
    kernel_path = _ROOT / payload["output_bsp"]
    if not kernel_path.exists():
        pytest.skip("aylochaxnim type13 BSP artifact is missing")

    planetary_path = find_planetary_kernel()
    if planetary_path is None:
        pytest.skip("no planetary kernel is installed")

    # Deliberately not registered in ASTEROID_NAIF / the packaged catalog —
    # that file is release-bound (see test_asteroid_identity_catalog.py) and
    # this PR does not touch it. Look the target up by raw NAIF ID instead;
    # see the PR description for why the name isn't admitted here.
    naif_id = payload["target"]["naif_id"]

    readers = [SpkReader(planetary_path), SmallBodyKernel(kernel_path)]
    try:
        pool = KernelPool(readers)
        with use_reader_override(pool):
            coverage = payload["coverage"]
            start_jd = float(coverage["start_jd"])
            end_jd = float(coverage["end_jd"])
            midpoint_jd = float(payload["verification"]["midpoint_jd"])
            sample_jds = (start_jd + 120.0, midpoint_jd, end_jd - 120.0)

            longitudes: list[float] = []
            for jd_ut in sample_jds:
                result = asteroid_at(naif_id, jd_ut, reader=pool)
                assert result.naif_id == 2594913
                assert math.isfinite(result.longitude)
                assert math.isfinite(result.latitude)
                assert math.isfinite(result.distance)
                assert math.isfinite(result.speed)
                longitudes.append(result.longitude)

            for earlier, later in zip(longitudes, longitudes[1:]):
                delta = ((later - earlier + 180.0) % 360.0) - 180.0
                assert abs(delta) < 180.0
    finally:
        for reader in reversed(readers):
            reader.close()


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.external_network
def test_custom_aylochaxnim_type13_kernel_matches_live_horizons_observer_product() -> None:
    if not _META.exists():
        pytest.skip("aylochaxnim type13 metadata artifact is missing")

    payload = json.loads(_META.read_text(encoding="utf-8"))
    kernel_path = _ROOT / payload["output_bsp"]
    if not kernel_path.exists():
        pytest.skip("aylochaxnim type13 BSP artifact is missing")

    planetary_path = find_planetary_kernel()
    if planetary_path is None:
        pytest.skip("no planetary kernel is installed")

    readers = [SpkReader(planetary_path), SmallBodyKernel(kernel_path)]
    try:
        pool = KernelPool(readers)
        # 'Aylo'chaxnim's orbital period is only ~151 days — check three
        # dates spread across the kernel's coverage (not just one) since its
        # angular motion is much faster than Toutatis's and interpolation
        # error would show up first at a small number of sample points.
        for jd_ut in (
            julian_day(2021, 3, 15, 0.0),
            julian_day(2025, 9, 1, 0.0),
            julian_day(2029, 6, 20, 0.0),
        ):
            ref_lon, ref_lat = observer_ecliptic_horizons(payload["target"]["command"], jd_ut)
            with use_reader_override(pool):
                result = asteroid_at(payload["target"]["naif_id"], jd_ut, reader=pool)

            lon_err_arcsec = angle_diff_arcsec(result.longitude, ref_lon)
            lat_err_arcsec = (result.latitude - ref_lat) * 3600.0

            assert abs(lon_err_arcsec) < 0.1, (jd_ut, lon_err_arcsec)
            assert abs(lat_err_arcsec) < 0.1, (jd_ut, lat_err_arcsec)
    finally:
        for reader in reversed(readers):
            reader.close()

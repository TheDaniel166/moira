from __future__ import annotations

import datetime as dt

import pytest

from moira.asteroids import asteroid_at
from moira._kernel_paths import find_planetary_kernel
from moira.spk_reader import KernelPool, SpkReader
from moira._spk_body_kernel import small_body_readers_from_manifest
from moira._wheel_asteroid_catalog import CATALOG_DIR
from moira.julian import jd_from_datetime


pytestmark = pytest.mark.skipif(
    find_planetary_kernel() is None,
    reason="planetary kernel required",
)


def test_wheel_catalog_computes_chiron_ceres_eris_amor() -> None:
    planetary = find_planetary_kernel()
    assert planetary is not None
    pool = KernelPool()
    pool.add(SpkReader(planetary))
    for reader in small_body_readers_from_manifest(CATALOG_DIR / "manifest.json"):
        pool.add(reader)
    when = dt.datetime(1990, 6, 15, 12, 0, tzinfo=dt.timezone.utc)
    jd_ut = jd_from_datetime(when)
    for name in ("Chiron", "Ceres", "Eris", "Amor"):
        pos = asteroid_at(name, jd_ut, reader=pool)
        assert pos.name == name
        assert 0.0 <= pos.longitude < 360.0

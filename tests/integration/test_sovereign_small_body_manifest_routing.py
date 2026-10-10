from pathlib import Path
import shutil

import pytest

from moira._kernel_paths import SOVEREIGN_SMALL_BODY_MANIFEST_ENV
from moira._spk_body_kernel import small_body_readers_from_manifest
from moira.asteroids import asteroid_at
from moira.julian import julian_day
from moira.spk_reader import (
    KernelPool,
    MissingKernelError,
    SpkReader,
    get_reader,
    reset_singleton,
    set_kernel_path,
)


_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "moira"
    / "kernels"
    / "asteroids_wheel"
    / "manifest.json"
)


def _angle_diff_arcsec(a: float, b: float) -> float:
    return (((a - b + 180.0) % 360.0) - 180.0) * 3600.0


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_public_asteroid_route_prefers_sovereign_manifest_when_configured(
    monkeypatch: pytest.MonkeyPatch,
    configured_global_reader,
    planetary_kernel_path,
    tmp_path: Path,
) -> None:
    # Routing equivalence needs a complete native catalog, not the unavailable
    # historical research export. Copy the sealed packaged wheel to a distinct
    # location, so ignoring the configured path cannot masquerade as success.
    manifest = tmp_path / "configured-catalog" / "manifest.json"
    shutil.copytree(_MANIFEST.parent, manifest.parent)

    assert get_reader() is configured_global_reader
    monkeypatch.setenv(SOVEREIGN_SMALL_BODY_MANIFEST_ENV, str(manifest))
    reset_singleton()

    explicit_readers = [SpkReader(planetary_kernel_path)]
    explicit_readers.extend(small_body_readers_from_manifest(manifest))
    explicit_pool = KernelPool(explicit_readers)
    try:
        set_kernel_path(planetary_kernel_path)
        routed_reader = get_reader()
        assert any(
            getattr(child, "_path", None) == manifest.parent / "asteroid_shard_000.bsp"
            for child in routed_reader._readers
        )

        jd_ut = julian_day(2026, 5, 9, 0.0)
        routed = asteroid_at("Ceres", jd_ut, reader=routed_reader)
        explicit = asteroid_at("Ceres", jd_ut, reader=explicit_pool)

        assert abs(_angle_diff_arcsec(routed.longitude, explicit.longitude)) < 1e-6
        assert abs((routed.latitude - explicit.latitude) * 3600.0) < 1e-6
        assert abs(routed.distance - explicit.distance) < 1e-3
    finally:
        explicit_pool.close()
        reset_singleton()

    with pytest.raises(MissingKernelError, match="outside an active reader context"):
        get_reader()

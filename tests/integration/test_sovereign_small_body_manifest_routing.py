from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel, SOVEREIGN_SMALL_BODY_MANIFEST_ENV
from moira._spk_body_kernel import small_body_readers_from_manifest
from moira.asteroids import asteroid_at
from moira.julian import julian_day
from moira.spk_reader import KernelPool, SpkReader, get_reader, reset_singleton, set_kernel_path


_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "kernels"
    / "sb441_type13_full_2020_2030"
    / "manifest.json"
)


def _angle_diff_arcsec(a: float, b: float) -> float:
    return (((a - b + 180.0) % 360.0) - 180.0) * 3600.0


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_public_asteroid_route_prefers_sovereign_manifest_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    if not _MANIFEST.exists():
        pytest.skip("Sovereign small-body manifest artifact is not present")

    planetary_path = find_planetary_kernel()
    if planetary_path is None:
        pytest.skip("No planetary kernel is installed")

    monkeypatch.setenv(SOVEREIGN_SMALL_BODY_MANIFEST_ENV, str(_MANIFEST))
    reset_singleton()

    explicit_readers = [SpkReader(planetary_path)]
    explicit_readers.extend(small_body_readers_from_manifest(_MANIFEST))
    explicit_pool = KernelPool(explicit_readers)
    try:
        set_kernel_path(planetary_path)
        routed_reader = get_reader()

        jd_ut = julian_day(2026, 5, 9, 0.0)
        routed = asteroid_at("Adeona", jd_ut, reader=routed_reader)
        explicit = asteroid_at("Adeona", jd_ut, reader=explicit_pool)

        assert abs(_angle_diff_arcsec(routed.longitude, explicit.longitude)) < 1e-6
        assert abs((routed.latitude - explicit.latitude) * 3600.0) < 1e-6
        assert abs(routed.distance - explicit.distance) < 1e-3
    finally:
        explicit_pool.close()
        reset_singleton()

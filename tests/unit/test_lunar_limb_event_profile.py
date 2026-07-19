"""Focused doctrine checks for immutable finite-resolution lunar profiles."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import gc
import hashlib
import math
import multiprocessing
import os
from pathlib import Path
import time
from types import SimpleNamespace
import weakref

import pytest

import moira.lunar_limb as lunar_limb
from moira.lunar_limb import (
    LunarLimbAssetIdentity,
    LunarLimbEventProfile,
    LunarLimbProfileCoverageError,
    LunarLimbProfileSlice,
    LunarLimbProfileSource,
    LunarLimbResourceError,
)


pytestmark = pytest.mark.unit


class _DelayedDownloadResponse:
    def __init__(self, payload: bytes, delay_seconds: float) -> None:
        self._payload = payload
        self._delay_seconds = delay_seconds

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        time.sleep(self._delay_seconds)
        for offset in range(0, len(self._payload), chunk_size):
            yield self._payload[offset : offset + chunk_size]


class _DelayedDownloadRequests:
    def __init__(
        self,
        payload: bytes,
        delay_seconds: float,
        entered_event,
        call_count,
    ) -> None:
        self._payload = payload
        self._delay_seconds = delay_seconds
        self._entered_event = entered_event
        self._call_count = call_count

    def get(self, _url: str, **_kwargs) -> _DelayedDownloadResponse:
        with self._call_count.get_lock():
            self._call_count.value += 1
        self._entered_event.set()
        return _DelayedDownloadResponse(self._payload, self._delay_seconds)


def _download_collision_worker(
    destination: str,
    payload: bytes,
    delay_seconds: float,
    entered_event,
    ready_event,
    start_event,
    call_count,
    result_queue,
) -> None:
    """Spawn-safe worker for the real OS-lock/cache publication test."""

    import moira.lunar_limb as worker_lunar_limb

    os.environ["MOIRA_NO_DOWNLOAD"] = "0"
    worker_lunar_limb._HAS_REQUESTS = True
    worker_lunar_limb.requests = _DelayedDownloadRequests(
        payload,
        delay_seconds,
        entered_event,
        call_count,
    )
    ready_event.set()
    start_event.wait(10.0)
    digest = hashlib.sha256(payload).hexdigest()
    try:
        result = worker_lunar_limb._download_file(
            "https://example.invalid/authoritative.copc.laz",
            Path(destination),
            expected_identity=(len(payload), digest),
        )
        result_queue.put(("ok", str(result), result.read_bytes() == payload))
    except Exception as exc:  # pragma: no cover - failure detail crosses process
        result_queue.put(("error", type(exc).__name__, str(exc)))


def _cache_lock_holder(lock_path: str, entered_event, release_event) -> None:
    import moira.lunar_limb as worker_lunar_limb

    with worker_lunar_limb._interprocess_cache_lock(Path(lock_path)):
        entered_event.set()
        release_event.wait(10.0)


def _source() -> LunarLimbProfileSource:
    return LunarLimbProfileSource(
        authority="fixture authority",
        collection="fixture collection",
        coordinate_frame="fixture Moon XYZ",
        translation_model="fixture DE441/LE441",
        orientation_model="fixture orientation",
        surface_frame_model="fixture DE421 ME",
        orientation_alignment_max_m=0.5,
        orientation_alignment_interval="fixture interval",
        reference_radius_km=1737.4,
        spatial_query_half_width_km=10.0,
        spatial_query_bounds_moon_xyz_km=(
            (-10.0, -10.0, -10.0),
            (10.0, 10.0, 10.0),
        ),
        relief_observation_sources=("fixture://relief-observation",),
        relief_observed_highest_km=9.0,
        relief_observed_approximate_absolute_km=10.0,
        relief_acquisition_policy="fixture +/-12 km policy",
        max_absolute_relief_km=12.0,
        assets=(
            LunarLimbAssetIdentity(
                "fixture://lola-profile",
                1,
                "0" * 64,
            ),
        ),
    )


def _slice(
    jd_ut1: float,
    radii_km: tuple[float, float, float],
) -> LunarLimbProfileSlice:
    return LunarLimbProfileSlice(
        jd_ut1=jd_ut1,
        position_angles_unwrapped_deg=(359.0, 360.0, 361.0),
        radii_km=radii_km,
        bin_width_deg=1.0,
        max_interpolation_gap_deg=1.1,
        source_point_count=3,
        asset_urls=("fixture://lola-profile",),
    )


def test_profile_slice_reconstructs_bin_center_extrema_and_pa_wrap() -> None:
    profile_slice = _slice(100.0, (1738.0, 1737.0, 1738.0))

    assert profile_slice.radius_km_at(359.0) == 1738.0
    assert profile_slice.radius_km_at(0.0) == 1737.0
    assert profile_slice.radius_km_at(360.5) == 1737.5
    assert profile_slice.radius_km_at(1.0) == 1738.0


def test_profile_slice_makes_no_exact_sub_bin_topography_claim() -> None:
    profile_slice = _slice(100.0, (1740.0, 1737.4, 1737.4))

    # The admitted values are half-open-bin maxima assigned to bin centres.
    # Between centres the declared product is linear; it is not an assertion
    # that the maximum source point occurred at either queried sub-bin PA.
    assert profile_slice.radius_km_at(359.25) == pytest.approx(1739.35)
    assert "CENTER_SAMPLE_LINEAR_RECONSTRUCTION" in _source().silhouette_model


def test_finite_distance_limb_point_uses_the_spherical_tangent_circle() -> None:
    distance_km = 384_400.0
    context = lunar_limb._ObserverLimbContext(
        subobserver_lon_deg=0.0,
        subobserver_lat_deg=0.0,
        observer_distance_km=distance_km,
        los_j2000=(-1.0, 0.0, 0.0),
        observer_dir_moon=(1.0, 0.0, 0.0),
        sky_north_moon=(0.0, 0.0, 1.0),
        sky_east_moon=(0.0, 1.0, 0.0),
    )

    lon_deg, lat_deg = lunar_limb._limb_point_lon_lat_from_context(context, 0.0)

    tangent_cosine = lunar_limb.MOON_RADIUS_KM / distance_km
    assert lon_deg == pytest.approx(0.0, abs=1.0e-12)
    assert lat_deg == pytest.approx(
        math.degrees(math.acos(tangent_cosine)),
        abs=1.0e-12,
    )
    assert lat_deg < 90.0


def _synthetic_cap(
    longitude_deg: float,
    latitude_deg: float,
    angular_radius_deg: float,
) -> lunar_limb._LolaSphericalCap:
    lon = math.radians(longitude_deg)
    lat = math.radians(latitude_deg)
    return lunar_limb._LolaSphericalCap(
        center_unit=(
            math.cos(lat) * math.cos(lon),
            math.cos(lat) * math.sin(lon),
            math.sin(lat),
        ),
        center_lon_deg=longitude_deg,
        center_lat_deg=latitude_deg,
        angular_radius_rad=math.radians(angular_radius_deg),
    )


def test_relief_shell_guard_is_source_distinct_and_finite_distance_complete() -> None:
    radius = lunar_limb.MOON_RADIUS_KM
    inner = radius - lunar_limb._LOLA_MAX_ABSOLUTE_RELIEF_KM
    outer = radius + lunar_limb._LOLA_MAX_ABSOLUTE_RELIEF_KM
    distance = 403_604.0

    assert lunar_limb._NASA_LRO_HIGHEST_POINT_KM == 10.786
    assert lunar_limb._NASA_LOLA_APPROXIMATE_ABSOLUTE_RELIEF_KM == 10.0
    assert lunar_limb._LOLA_MAX_ABSOLUTE_RELIEF_KM == 12.0
    assert math.degrees(lunar_limb._LOLA_MEAN_LIMB_CENTRAL_GUARD_RAD) == (
        pytest.approx(6.714787268986791, abs=1.0e-12)
    )
    assert lunar_limb._LOLA_MEAN_LIMB_CHORD_MARGIN_KM == pytest.approx(
        204.55219382837254,
        abs=1.0e-12,
    )

    guard = lunar_limb._lola_relief_competition_guard_rad(distance)
    infinite_distance_guard = math.acos(inner / outer)
    assert math.degrees(guard) == pytest.approx(9.503297126727372, abs=1.0e-12)
    assert guard > infinite_distance_guard

    tangent_angle = math.acos(radius / distance)

    def projected_equivalent_radius(angle: float) -> float:
        return (
            distance
            * outer
            * math.sin(angle)
            / math.sqrt(
                distance**2
                + outer**2
                - 2.0 * distance * outer * math.cos(angle)
            )
        )

    assert projected_equivalent_radius(tangent_angle + guard) == pytest.approx(
        inner,
        abs=1.0e-9,
    )
    assert projected_equivalent_radius(tangent_angle + guard + 1.0e-7) < inner


def test_cartesian_cap_union_contains_the_outer_shell_limiting_point() -> None:
    radius = lunar_limb.MOON_RADIUS_KM
    outer = radius + lunar_limb._LOLA_MAX_ABSOLUTE_RELIEF_KM
    distance = 403_604.0
    tangent_angle = math.acos(radius / distance)
    guard = lunar_limb._lola_relief_competition_guard_rad(distance)
    cap = lunar_limb._LolaSphericalCap(
        center_unit=(math.cos(tangent_angle), math.sin(tangent_angle), 0.0),
        center_lon_deg=math.degrees(tangent_angle),
        center_lat_deg=0.0,
        angular_radius_rad=guard,
    )

    bounds = lunar_limb._lola_cartesian_query_bounds((cap,))
    limiting_point = (
        outer * math.cos(tangent_angle + guard),
        outer * math.sin(tangent_angle + guard),
        0.0,
    )

    assert all(
        lower - 1.0e-12 <= value <= upper + 1.0e-12
        for value, lower, upper in zip(
            limiting_point,
            bounds.minimum_km,
            bounds.maximum_km,
        )
    )


def test_tile_discovery_crosses_cell_boundary_dateline_and_pole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lunar_limb,
        "_lola_acquisition_caps",
        lambda *_args, **_kwargs: (_synthetic_cap(14.9, 1.0, 1.0),),
    )
    boundary_cells = set(
        lunar_limb._lola_envelope_tile_cells(object(), 0.0, 1.0)
    )
    assert (0, 0) in boundary_cells
    assert (15, 0) in boundary_cells

    monkeypatch.setattr(
        lunar_limb,
        "_lola_acquisition_caps",
        lambda *_args, **_kwargs: (_synthetic_cap(179.8, 1.0, 1.0),),
    )
    dateline_cells = set(
        lunar_limb._lola_envelope_tile_cells(object(), 0.0, 1.0)
    )
    assert (165, 0) in dateline_cells
    assert (-180, 0) in dateline_cells

    monkeypatch.setattr(
        lunar_limb,
        "_lola_acquisition_caps",
        lambda *_args, **_kwargs: (_synthetic_cap(40.0, -89.0, 2.0),),
    )
    polar_cells = lunar_limb._lola_envelope_tile_cells(object(), 0.0, 1.0)
    assert {
        lon_bin
        for lon_bin, lat_bin in polar_cells
        if lat_bin == -90
    } == set(range(-180, 180, 15))
    monkeypatch.setattr(lunar_limb, "_MAX_CONTACT_LOLA_TILES", 23)
    with pytest.raises(LunarLimbResourceError, match="admitted tile bound 23"):
        lunar_limb._lola_envelope_tile_cells(object(), 0.0, 1.0)


def test_lola_envelope_tile_urls_fails_if_any_intersecting_cell_is_unmapped(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cells = ((60, -90), (75, -90))
    monkeypatch.setattr(
        lunar_limb,
        "_lola_envelope_tile_cells",
        lambda *_args, **_kwargs: cells,
    )

    def resolve(lon_bin: int, lat_bin: int, _cache_root: str) -> str:
        if (lon_bin, lat_bin) == cells[1]:
            raise lunar_limb._NoLolaTileError("official STAC cell is absent")
        return "https://example.invalid/first.copc.laz"

    monkeypatch.setattr(lunar_limb, "_lola_tile_asset_url", resolve)

    with pytest.raises(
        lunar_limb._NoLolaTileError,
        match="official STAC cell is absent",
    ):
        lunar_limb._lola_envelope_tile_urls(
            object(),
            0.0,
            1.0,
            tmp_path,
        )


def test_lunar_surface_chord_is_wrap_safe_and_symmetric() -> None:
    expected = 2.0 * lunar_limb.MOON_RADIUS_KM * math.sin(math.radians(1.0))

    forward = lunar_limb._lunar_surface_chord_km(179.0, 0.0, -179.0, 0.0)
    reverse = lunar_limb._lunar_surface_chord_km(-179.0, 0.0, 179.0, 0.0)

    assert forward == pytest.approx(expected, abs=1.0e-12)
    assert reverse == pytest.approx(forward, abs=1.0e-12)


def test_event_profile_interpolates_pa_then_time_without_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = LunarLimbEventProfile(
        source=_source(),
        slices=(
            _slice(100.0, (1738.0, 1737.0, 1738.0)),
            _slice(102.0, (1740.0, 1739.0, 1740.0)),
        ),
        max_time_interpolation_gap_days=2.0,
        observer_latitude_deg=31.5,
        observer_longitude_deg=-99.9,
        observer_elevation_m=475.0,
    )

    def unexpected_io(*args, **kwargs):
        raise AssertionError("profile evaluation attempted I/O or SPICE work")

    monkeypatch.setattr(
        lunar_limb,
        "requests",
        SimpleNamespace(get=unexpected_io, post=unexpected_io),
    )
    monkeypatch.setattr(lunar_limb, "sp", SimpleNamespace(spkcpo=unexpected_io))

    assert profile.radius_km_at(101.0, 0.0) == 1738.0
    assert profile.radius_km_at(101.0, 0.5) == 1738.5
    assert profile.elevation_m_at(101.0, 0.0) == pytest.approx(600.0)


def test_event_profile_rejects_noncanonical_reference_radius() -> None:
    with pytest.raises(ValueError, match="canonical 1737.4 km"):
        LunarLimbEventProfile(
            source=replace(_source(), reference_radius_km=1737.5),
            slices=(_slice(100.0, (1738.0, 1737.0, 1738.0)),),
            max_time_interpolation_gap_days=0.0,
            observer_latitude_deg=31.5,
            observer_longitude_deg=-99.9,
            observer_elevation_m=475.0,
        )


@pytest.mark.parametrize("radius_km", [1725.399, 1749.401])
def test_event_profile_rejects_radius_outside_declared_relief_shell(
    radius_km: float,
) -> None:
    with pytest.raises(ValueError, match="source-declared absolute-relief shell"):
        LunarLimbEventProfile(
            source=_source(),
            slices=(_slice(100.0, (1738.0, radius_km, 1738.0)),),
            max_time_interpolation_gap_days=0.0,
            observer_latitude_deg=31.5,
            observer_longitude_deg=-99.9,
            observer_elevation_m=475.0,
        )


def test_profile_rejects_pa_gap_and_out_of_window_epoch() -> None:
    gapped = LunarLimbProfileSlice(
        jd_ut1=100.0,
        position_angles_unwrapped_deg=(359.0, 361.0),
        radii_km=(1738.0, 1738.0),
        bin_width_deg=0.1,
        max_interpolation_gap_deg=0.25,
        source_point_count=2,
        asset_urls=("fixture://lola-profile",),
    )
    profile = LunarLimbEventProfile(
        source=_source(),
        slices=(gapped,),
        max_time_interpolation_gap_days=0.0,
        observer_latitude_deg=31.5,
        observer_longitude_deg=-99.9,
        observer_elevation_m=475.0,
    )

    with pytest.raises(LunarLimbProfileCoverageError, match="sample gap"):
        profile.radius_km_at(100.0, 0.0)
    with pytest.raises(LunarLimbProfileCoverageError, match="outside profile coverage"):
        profile.radius_km_at(99.0, 359.0)
    with pytest.raises(LunarLimbProfileCoverageError, match="outside profile coverage"):
        profile.radius_km_at(100.0, 20.0)


def test_event_profile_rejects_time_interpolation_across_declared_gap() -> None:
    profile = LunarLimbEventProfile(
        source=_source(),
        slices=(
            _slice(100.0, (1738.0, 1737.0, 1738.0)),
            _slice(102.0, (1740.0, 1739.0, 1740.0)),
        ),
        max_time_interpolation_gap_days=1.0,
        observer_latitude_deg=31.5,
        observer_longitude_deg=-99.9,
        observer_elevation_m=475.0,
    )

    with pytest.raises(LunarLimbProfileCoverageError, match="time sample gap"):
        profile.radius_km_at(101.0, 0.0)


def test_multi_slice_builder_requires_an_independent_time_gap_policy() -> None:
    with pytest.raises(
        ValueError,
        match="max_time_interpolation_gap_days is required",
    ):
        lunar_limb.build_lola_rdr_lunar_limb_event_profile(
            (2_460_000.0, 2_460_000.001),
            0.0,
            0.0,
            0.0,
            0.0,
            reader=object(),
        )


def test_event_profile_builder_rejects_excessive_sequence_before_iteration() -> None:
    class OversizedEpochs:
        def __len__(self) -> int:
            return lunar_limb.MAX_LUNAR_LIMB_EVENT_PROFILE_SLICES + 1

        def __iter__(self):
            raise AssertionError("oversized epochs must not be iterated")

    with pytest.raises(ValueError, match="exceeding the admitted bound"):
        lunar_limb.build_lola_rdr_lunar_limb_event_profile(
            OversizedEpochs(),  # type: ignore[arg-type]
            0.0,
            0.0,
            0.0,
            0.0,
            reader=object(),
        )


def test_profile_vessels_defensively_freeze_input_sequences() -> None:
    angles = [359.0, 360.0, 361.0]
    radii = [1738.0, 1737.0, 1738.0]
    urls = ["fixture://lola-profile"]
    profile_slice = LunarLimbProfileSlice(
        jd_ut1=100.0,
        position_angles_unwrapped_deg=angles,  # type: ignore[arg-type]
        radii_km=radii,  # type: ignore[arg-type]
        bin_width_deg=1.0,
        max_interpolation_gap_deg=1.1,
        source_point_count=3,
        asset_urls=urls,  # type: ignore[arg-type]
    )
    angles[1] = 999.0
    radii[1] = 999.0
    urls[0] = "fixture://changed"

    assert profile_slice.position_angles_unwrapped_deg == (359.0, 360.0, 361.0)
    assert profile_slice.radii_km == (1738.0, 1737.0, 1738.0)
    assert profile_slice.asset_urls == ("fixture://lola-profile",)
    with pytest.raises(FrozenInstanceError):
        profile_slice.jd_ut1 = 101.0  # type: ignore[misc]


def test_half_open_bin_builder_selects_maxima_without_filling_valley() -> None:
    result = lunar_limb._profile_slice_from_projected_radii(
        jd_ut1=100.0,
        projected_position_angles_deg=(358.0, 359.1, 359.9, 0.0, 1.2, 2.0),
        projected_radii_km=(1737.0, 1737.1, 1738.0, 1736.0, 1739.0, 1900.0),
        position_angle_center_deg=0.0,
        position_angle_half_width_deg=2.0,
        bin_width_deg=1.0,
        max_interpolation_gap_deg=1.1,
        source_point_count=6,
        asset_urls=("fixture://lola-profile",),
    )

    assert result.position_angles_unwrapped_deg == (-1.5, -0.5, 0.5, 1.5)
    assert result.radii_km == (1737.0, 1738.0, 1736.0, 1739.0)
    assert 1900.0 not in result.radii_km  # exact upper edge belongs to no bin
    assert result.radius_km_at(0.0) == 1737.0


def test_profile_relief_floor_preserves_admitted_valleys_and_fails_below_bound() -> None:
    inner = (
        lunar_limb.MOON_RADIUS_KM
        - lunar_limb._LOLA_MAX_ABSOLUTE_RELIEF_KM
    )
    retained = lunar_limb._profile_slice_from_projected_radii(
        jd_ut1=100.0,
        projected_position_angles_deg=(-1.5, -0.5, 0.5, 1.5),
        projected_radii_km=(
            lunar_limb.MOON_RADIUS_KM - 5.0,
            lunar_limb.MOON_RADIUS_KM - 11.0,
            lunar_limb.MOON_RADIUS_KM - 5.0,
            lunar_limb.MOON_RADIUS_KM - 11.0,
        ),
        position_angle_center_deg=0.0,
        position_angle_half_width_deg=2.0,
        bin_width_deg=1.0,
        max_interpolation_gap_deg=1.1,
        source_point_count=4,
        asset_urls=("fixture://lola-profile",),
    )
    assert retained.radii_km[1] == lunar_limb.MOON_RADIUS_KM - 11.0

    with pytest.raises(LunarLimbProfileCoverageError, match="R-H"):
        lunar_limb._profile_slice_from_projected_radii(
            jd_ut1=100.0,
            projected_position_angles_deg=(-1.5, -0.5, 0.5, 1.5),
            projected_radii_km=(inner - 0.001,) * 4,
            position_angle_center_deg=0.0,
            position_angle_half_width_deg=2.0,
            bin_width_deg=1.0,
            max_interpolation_gap_deg=1.1,
            source_point_count=4,
            asset_urls=("fixture://lola-profile",),
        )


def test_loaded_tile_reducer_merges_sparse_native_bin_maxima() -> None:
    class Cloud:
        def __init__(self, radii: tuple[float, ...], admitted_count: int) -> None:
            self._radii = radii
            self._admitted_count = admitted_count

        def size(self) -> int:
            return self._admitted_count

        def project_max_radius_per_pa_bin(self, *args):
            assert args[3:6] == (-2.0, 2.0, 1.0)
            assert args[7] == lunar_limb._LOLA_INNER_RELIEF_RADIUS_KM
            assert args[8] == lunar_limb._LOLA_OUTER_RELIEF_RADIUS_KM
            return SimpleNamespace(
                bin_count=4,
                bin_indices=(0, 1, 2, 3),
                bin_centers_unwrapped_deg=(-1.5, -0.5, 0.5, 1.5),
                radii_km=self._radii,
                admitted_source_point_count=self._admitted_count,
            )

    urls = ("fixture://one", "fixture://two")
    loaded = {
        urls[0]: lunar_limb._LolaTile(
            Cloud((1737.0, 1736.0, 1737.5, 1737.0), 8)
        ),
        urls[1]: lunar_limb._LolaTile(
            Cloud((1736.5, 1737.0, 1737.1, 1738.0), 6)
        ),
    }
    context = SimpleNamespace(
        observer_distance_km=403_604.0,
        observer_dir_moon=(1.0, 0.0, 0.0),
        sky_east_moon=(0.0, 1.0, 0.0),
        sky_north_moon=(0.0, 0.0, 1.0),
    )

    profile_slice = lunar_limb._profile_slice_from_loaded_lola_tiles(
        jd_ut1=100.0,
        observer_context=context,
        position_angle_center_deg=0.0,
        position_angle_half_width_deg=2.0,
        bin_width_deg=1.0,
        max_interpolation_gap_deg=1.1,
        tile_urls=urls,
        loaded_tiles=loaded,
        expected_lola_assets=None,
    )

    assert profile_slice.radii_km == (1737.0, 1737.0, 1737.5, 1738.0)
    assert profile_slice.source_point_count == 14


def test_profile_slice_builder_fails_closed_when_projected_points_are_missing() -> None:
    with pytest.raises(LunarLimbProfileCoverageError, match="at least two"):
        lunar_limb._profile_slice_from_projected_radii(
            jd_ut1=100.0,
            projected_position_angles_deg=(),
            projected_radii_km=(),
            position_angle_center_deg=0.0,
            position_angle_half_width_deg=2.0,
            bin_width_deg=1.0,
            max_interpolation_gap_deg=1.1,
            source_point_count=0,
            asset_urls=("fixture://lola-profile",),
        )


def test_profile_slice_builder_requires_both_pa_boundaries() -> None:
    with pytest.raises(LunarLimbProfileCoverageError, match="both requested PA boundaries"):
        lunar_limb._profile_slice_from_projected_radii(
            jd_ut1=100.0,
            projected_position_angles_deg=(-0.4, 0.4),
            projected_radii_km=(1737.4, 1737.5),
            position_angle_center_deg=0.0,
            position_angle_half_width_deg=2.0,
            bin_width_deg=1.0,
            max_interpolation_gap_deg=1.1,
            source_point_count=2,
            asset_urls=("fixture://lola-profile",),
        )


def test_no_download_policy_blocks_uncached_file_and_stac_access(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_network(*args, **kwargs):
        raise AssertionError("network access must not occur")

    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setattr(
        lunar_limb,
        "requests",
        SimpleNamespace(get=unexpected_network, post=unexpected_network),
    )
    lunar_limb._lola_tile_asset_url.cache_clear()

    with pytest.raises(LunarLimbResourceError, match="MOIRA_NO_DOWNLOAD"):
        lunar_limb._download_file(
            "https://example.invalid/resource",
            tmp_path / "missing.bin",
        )
    with pytest.raises(LunarLimbResourceError, match="MOIRA_NO_DOWNLOAD"):
        lunar_limb._lola_tile_asset_url(0, 0, str(tmp_path))


def test_cached_resource_admission_does_not_require_requests(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = tmp_path / "cached.bin"
    cached.write_bytes(b"authoritative bytes")
    monkeypatch.setattr(lunar_limb, "_HAS_REQUESTS", False)
    monkeypatch.setattr(lunar_limb, "requests", None)

    assert lunar_limb._download_file("https://example.invalid/cached.bin", cached) == cached


def test_pinned_cached_resource_hash_mismatch_fails_before_use(tmp_path) -> None:
    cached = tmp_path / "pinned.bin"
    cached.write_bytes(b"wrong bytes")

    with pytest.raises(LunarLimbResourceError, match="byte length mismatch"):
        lunar_limb._download_file(
            "https://example.invalid/pinned.bin",
            cached,
            expected_identity=(99, "0" * 64),
        )


@pytest.mark.slow
@pytest.mark.serial
def test_long_download_collision_publishes_one_atomic_cache_file(tmp_path) -> None:
    """A second Windows worker must outwait the historical ten-second limit."""

    context = multiprocessing.get_context("spawn")
    payload = (b"authoritative LOLA bytes\0" * 8192) + b"complete"
    destination = tmp_path / "authoritative.copc.laz"
    entered_event = context.Event()
    first_ready_event = context.Event()
    second_ready_event = context.Event()
    first_start_event = context.Event()
    second_start_event = context.Event()
    call_count = context.Value("i", 0)
    result_queue = context.Queue()
    first = context.Process(
        target=_download_collision_worker,
        args=(
            str(destination),
            payload,
            11.0,
            entered_event,
            first_ready_event,
            first_start_event,
            call_count,
            result_queue,
        ),
    )
    second = context.Process(
        target=_download_collision_worker,
        args=(
            str(destination),
            payload,
            0.0,
            entered_event,
            second_ready_event,
            second_start_event,
            call_count,
            result_queue,
        ),
    )

    first.start()
    second.start()
    assert first_ready_event.wait(5.0), "first worker did not initialize"
    assert second_ready_event.wait(5.0), "second worker did not initialize"
    first_start_event.set()
    assert entered_event.wait(5.0), "first worker did not enter the download"
    second_start_event.set()
    first.join(25.0)
    second.join(25.0)
    if first.is_alive():
        first.terminate()
        first.join()
    if second.is_alive():
        second.terminate()
        second.join()

    assert first.exitcode == 0
    assert second.exitcode == 0
    results = sorted((result_queue.get(timeout=2.0), result_queue.get(timeout=2.0)))
    assert results == [
        ("ok", str(destination), True),
        ("ok", str(destination), True),
    ]
    assert call_count.value == 1
    assert destination.read_bytes() == payload
    assert tuple(tmp_path.glob("*.part")) == ()


@pytest.mark.serial
def test_interprocess_cache_lock_timeout_is_explicit(tmp_path) -> None:
    context = multiprocessing.get_context("spawn")
    lock_path = tmp_path / "held.lock"
    entered_event = context.Event()
    release_event = context.Event()
    holder = context.Process(
        target=_cache_lock_holder,
        args=(str(lock_path), entered_event, release_event),
    )
    holder.start()
    assert entered_event.wait(5.0), "lock holder did not acquire the cache lock"
    try:
        with pytest.raises(LunarLimbResourceError, match="timed out after 0.1 seconds"):
            with lunar_limb._interprocess_cache_lock(
                lock_path,
                timeout_seconds=0.1,
                poll_interval_seconds=0.01,
            ):
                raise AssertionError("contended lock must not be admitted")
    finally:
        release_event.set()
        holder.join(10.0)
        if holder.is_alive():
            holder.terminate()
            holder.join()
    assert holder.exitcode == 0


def test_external_fixture_tile_urls_must_match_before_decode() -> None:
    expected = LunarLimbAssetIdentity(
        "https://example.invalid/expected.copc.laz",
        123,
        "a" * 64,
    )
    admitted = lunar_limb._expected_lola_asset_map((expected,))

    lunar_limb._admit_expected_lola_tile_urls((expected.url,), admitted)
    with pytest.raises(LunarLimbResourceError, match="unexpected=.*other"):
        lunar_limb._admit_expected_lola_tile_urls(
            ("https://example.invalid/other.copc.laz",),
            admitted,
        )


def test_profile_builder_rejects_external_tile_url_drift_before_collection(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = LunarLimbAssetIdentity(
        "https://example.invalid/expected.copc.laz",
        123,
        "a" * 64,
    )
    context = SimpleNamespace()
    monkeypatch.setattr(lunar_limb, "_default_cache_root", lambda: tmp_path)
    monkeypatch.setattr(
        lunar_limb,
        "_ensure_contact_orientation_kernels_loaded",
        lambda _cache_root: (),
    )
    monkeypatch.setattr(
        lunar_limb,
        "_reader_bound_observer_limb_context",
        lambda *_args: (context, "fixture DE441", 0.0),
    )
    monkeypatch.setattr(
        lunar_limb,
        "_limb_point_lon_lat_from_context",
        lambda *_args: (0.0, 0.0),
    )
    monkeypatch.setattr(
        lunar_limb,
        "_lola_envelope_tile_urls",
        lambda *_args: ("https://example.invalid/drifted.copc.laz",),
    )
    monkeypatch.setattr(
        lunar_limb,
        "_collect_lola_projected_points",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("tile collection/decode must not begin")
        ),
    )

    with pytest.raises(LunarLimbResourceError, match="resolved LOLA tile URL set"):
        lunar_limb.build_lola_rdr_lunar_limb_event_profile(
            (2_460_000.0,),
            0.0,
            0.0,
            0.0,
            0.0,
            reader=object(),
            expected_lola_assets=(expected,),
        )


def test_profile_builder_reuses_union_tiles_and_releases_native_clouds(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tile_urls = (
        "https://example.invalid/one.copc.laz",
        "https://example.invalid/two.copc.laz",
    )
    tile_root = tmp_path / "lola_tiles"
    tile_root.mkdir()
    for url in tile_urls:
        (tile_root / Path(url).name).write_bytes(url.encode("ascii"))
    orientation_paths = []
    for index in range(2):
        path = tmp_path / f"orientation-{index}.kernel"
        path.write_bytes(f"orientation-{index}".encode("ascii"))
        orientation_paths.append(path)

    context = SimpleNamespace(
        observer_distance_km=403_604.0,
        observer_dir_moon=(1.0, 0.0, 0.0),
        sky_east_moon=(0.0, 1.0, 0.0),
        sky_north_moon=(0.0, 0.0, 1.0),
    )
    bounds = lunar_limb._LolaCartesianBounds(
        (-20.0, -10.0, -5.0),
        (20.0, 10.0, 5.0),
    )
    cloud_references: list[weakref.ReferenceType[object]] = []
    loaded_urls: list[str] = []
    reduced_urls: list[str] = []

    class Cloud:
        def size(self) -> int:
            return 1

    def load_tile(url, *_args, **_kwargs):
        if cloud_references:
            gc.collect()
            assert cloud_references[-1]() is None
        loaded_urls.append(url)
        cloud = Cloud()
        cloud_references.append(weakref.ref(cloud))
        return lunar_limb._LolaTile(
            cloud,
            decompression_point_upper_bound=4,
        )

    def merge_tile(maxima, *, url, bin_count, **_kwargs):
        reduced_urls.append(url)
        for index in range(bin_count):
            maxima[index] = max(maxima.get(index, 0.0), 1737.4)
        return bin_count

    monkeypatch.setattr(lunar_limb, "_default_cache_root", lambda: tmp_path)
    monkeypatch.setattr(
        lunar_limb,
        "_ensure_contact_orientation_kernels_loaded",
        lambda _cache_root: tuple(orientation_paths),
    )
    monkeypatch.setattr(
        lunar_limb,
        "_reader_bound_observer_limb_context",
        lambda *_args: (context, "fixture DE441", 0.0),
    )
    monkeypatch.setattr(
        lunar_limb,
        "_lola_envelope_tile_urls",
        lambda *_args, **_kwargs: tile_urls,
    )
    monkeypatch.setattr(
        lunar_limb,
        "_lola_common_cartesian_query_bounds",
        lambda *_args, **_kwargs: bounds,
    )
    monkeypatch.setattr(
        lunar_limb,
        "_load_lola_tile_cartesian_region",
        load_tile,
    )
    monkeypatch.setattr(
        lunar_limb,
        "_merge_loaded_lola_tile_profile_maxima",
        merge_tile,
    )

    profile = lunar_limb.build_lola_rdr_lunar_limb_event_profile(
        (2_460_000.0, 2_460_000.001),
        0.0,
        0.0,
        0.0,
        0.0,
        reader=object(),
        max_time_interpolation_gap_days=0.01,
    )
    gc.collect()

    assert loaded_urls == list(tile_urls)
    assert reduced_urls == [tile_urls[0], tile_urls[0], tile_urls[1], tile_urls[1]]
    assert all(reference() is None for reference in cloud_references)
    assert profile.source.spatial_query_bounds_moon_xyz_km == (
        bounds.minimum_km,
        bounds.maximum_km,
    )
    assert profile.source.spatial_query_half_width_km == 20.0
    assert profile.source.max_absolute_relief_km == 12.0
    assert profile.source.relief_observed_highest_km == 10.786


def test_expected_lola_identity_fails_before_copc_decode(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://example.invalid/pinned.copc.laz"
    tile_path = tmp_path / "lola_tiles" / "pinned.copc.laz"
    tile_path.parent.mkdir(parents=True)
    payload = b"same length but wrong content"
    tile_path.write_bytes(payload)
    decode_called = False

    class RejectDecode:
        @staticmethod
        def open(_path):
            nonlocal decode_called
            decode_called = True
            raise AssertionError("COPC decode must follow byte admission")

    monkeypatch.setattr(lunar_limb, "_require_laspy", lambda: None)
    monkeypatch.setattr(lunar_limb, "CopcReader", RejectDecode)

    with pytest.raises(LunarLimbResourceError, match="SHA-256 mismatch"):
        lunar_limb._load_lola_tile_region(
            url,
            str(tmp_path),
            0.0,
            0.0,
            10.0,
            len(payload),
            "0" * 64,
        )
    assert decode_called is False


def test_copc_node_point_bound_fails_before_query_decompression(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query_called = False

    class Reader:
        header = SimpleNamespace(
            mins=(-2_000_000.0, -2_000_000.0, -2_000_000.0),
            maxs=(2_000_000.0, 2_000_000.0, 2_000_000.0),
        )
        source = object()
        copc_info = object()
        root_page = object()

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def query(self, **_kwargs):
            nonlocal query_called
            query_called = True
            raise AssertionError("point budget must fail before COPC query")

    tile_path = tmp_path / "bounded.copc.laz"
    monkeypatch.setattr(lunar_limb, "_require_laspy", lambda: None)
    monkeypatch.setattr(
        lunar_limb,
        "_download_file",
        lambda *_args, **_kwargs: tile_path,
    )
    monkeypatch.setattr(
        lunar_limb,
        "CopcReader",
        SimpleNamespace(open=lambda _path: Reader()),
    )
    monkeypatch.setattr(
        lunar_limb,
        "_validate_lola_coordinate_header",
        lambda _header: None,
    )
    monkeypatch.setattr(
        lunar_limb,
        "load_octree_for_query",
        lambda *_args, **_kwargs: (
            SimpleNamespace(point_count=4),
            SimpleNamespace(point_count=3),
        ),
    )

    with pytest.raises(LunarLimbResourceError, match="decompress up to 7"):
        lunar_limb._load_lola_tile_cartesian_region(
            "https://example.invalid/bounded.copc.laz",
            str(tmp_path),
            lunar_limb._LolaCartesianBounds(
                (-10.0, -10.0, -10.0),
                (10.0, 10.0, 10.0),
            ),
            max_points=5,
            max_decompression_points=5,
        )
    assert query_called is False


def test_predecode_budget_uses_remaining_node_and_projection_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lunar_limb, "_MAX_CONTACT_LOLA_POINTS_PER_TILE", 10)
    monkeypatch.setattr(lunar_limb, "_MAX_CONTACT_LOLA_NODE_POINTS_TOTAL", 7)
    monkeypatch.setattr(
        lunar_limb,
        "_MAX_CONTACT_LOLA_POINT_PROJECTION_WORK",
        12,
    )

    assert lunar_limb._lola_predecode_node_limit(4, 8, 2) == 2
    with pytest.raises(LunarLimbResourceError, match="exhausted"):
        lunar_limb._lola_predecode_node_limit(7, 8, 2)


def test_stac_lookup_queries_cell_interior_and_admits_unique_containing_tile(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "features": [
                    {
                        "bbox": [0.0, 0.0, 15.0, 15.0],
                        "assets": {"data": {"href": "https://example.invalid/cell.laz"}},
                    }
                ]
            }

    def post(_url: str, **kwargs: object) -> Response:
        calls.append(kwargs)
        return Response()

    monkeypatch.delenv("MOIRA_NO_DOWNLOAD", raising=False)
    monkeypatch.setattr(lunar_limb, "_HAS_REQUESTS", True)
    monkeypatch.setattr(lunar_limb, "requests", SimpleNamespace(post=post))
    lunar_limb._lola_tile_asset_url.cache_clear()

    assert lunar_limb._lola_tile_asset_url(0, 0, str(tmp_path)) == (
        "https://example.invalid/cell.laz"
    )
    assert calls[0]["json"]["bbox"] == pytest.approx([7.49, 7.49, 7.51, 7.51])


def test_lola_wkt_admission_requires_the_iau_2015_moon_xyz_sphere() -> None:
    admitted_wkt = (
        'GEODCRS["IAU_2015MoonXYZ",DATUM["Moon(2015)-Sphere",'
        'ELLIPSOID["Moon(2015)-Sphere",1737400,0,LENGTHUNIT["metre",1,'
        'ID["EPSG",9001]]]],CS[Cartesian,3],'
        'AXIS["(X)",geocentricX,ORDER[1],LENGTHUNIT["metre",1]],'
        'AXIS["(Y)",geocentricY,ORDER[2],LENGTHUNIT["metre",1]],'
        'AXIS["(Z)",geocentricZ,ORDER[3],LENGTHUNIT["metre",1]],'
        'ID["IAU",30000,2015]]'
    )
    admitted_header = SimpleNamespace(
        vlrs=(
            SimpleNamespace(
                user_id="LASF_Projection",
                record_id=2112,
                string=admitted_wkt,
            ),
        )
    )
    lunar_limb._validate_lola_coordinate_header(admitted_header)

    terrestrial_header = SimpleNamespace(
        vlrs=(
            SimpleNamespace(
                user_id="LASF_Projection",
                record_id=2112,
                string='GEODCRS["WGS 84",CS[Cartesian,3]]',
            ),
        )
    )
    with pytest.raises(LunarLimbResourceError, match="IAU 2015 Moon XYZ"):
        lunar_limb._validate_lola_coordinate_header(terrestrial_header)

    swapped_axes = admitted_wkt.replace(
        'AXIS["(X)",geocentricX,ORDER[1]',
        'AXIS["(X)",geocentricX,ORDER[2]',
    )
    with pytest.raises(LunarLimbResourceError, match="IAU 2015 Moon XYZ"):
        lunar_limb._validate_lola_coordinate_header(
            SimpleNamespace(
                vlrs=(
                    SimpleNamespace(
                        user_id="LASF_Projection",
                        record_id=2112,
                        string=swapped_axes,
                    ),
                )
            )
        )


def test_ut1_epoch_is_inverted_to_utc_before_et_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float]] = []

    def fake_ut1_to_utc(value: float) -> float:
        calls.append(("ut1_to_utc", value))
        return value - 0.25

    def fake_utc_to_et(value: float) -> float:
        calls.append(("utc_to_et", value))
        return value + 1000.0

    monkeypatch.setattr(lunar_limb, "_ut1_to_utc", fake_ut1_to_utc)
    monkeypatch.setattr(lunar_limb, "_jd_utc_to_et", fake_utc_to_et)

    assert lunar_limb._jd_ut_to_et(100.0) == 1099.75
    assert calls == [("ut1_to_utc", 100.0), ("utc_to_et", 99.75)]


def test_reader_bound_light_cone_uses_physical_de441_translation_without_aberration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira.corrections as corrections
    import moira.julian as julian
    import moira.obliquity as obliquity
    import moira.planets as planets

    identity = SimpleNamespace(
        planetary_ephemeris="DE441",
        lunar_ephemeris="LE441",
        summary_label="DE-0441LE-0441",
    )

    class Reader:
        def position(self, center: int, target: int, _jd: float):
            if (center, target) == (3, 301):
                return (300_000.0, 0.0, 0.0)
            if (center, target) in ((0, 3), (3, 399)):
                return (0.0, 0.0, 0.0)
            raise AssertionError((center, target))

    identity_matrix = (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    monkeypatch.setattr(lunar_limb, "_ut1_to_ephemeris_tt", lambda *_args: 100.0)
    monkeypatch.setattr(lunar_limb, "_reader_identity_at", lambda *_args: identity)
    monkeypatch.setattr(lunar_limb, "tt_to_tdb", lambda value: value)
    monkeypatch.setattr(corrections, "apply_frame_bias", lambda vector: vector)
    monkeypatch.setattr(
        corrections,
        "_observer_position_icrf",
        lambda *_args, **_kwargs: (0.0, 0.0, 0.0),
    )
    monkeypatch.setattr(planets, "_compose_rotation_matrix", lambda *_args, **_kwargs: identity_matrix)
    monkeypatch.setattr(planets, "_apply_rotation_matrix", lambda _matrix, vector: vector)
    monkeypatch.setattr(julian, "local_sidereal_time", lambda *_args: 0.0)
    monkeypatch.setattr(obliquity, "nutation", lambda *_args: (0.0, 0.0))
    monkeypatch.setattr(obliquity, "true_obliquity", lambda *_args: 23.4)

    result = lunar_limb._reader_bound_moon_light_cone(
        99.0,
        31.5,
        -99.9,
        500.0,
        Reader(),
    )

    light_time_days = 300_000.0 / (299_792.458 * 86_400.0)
    assert result.distance_km == pytest.approx(300_000.0)
    assert result.observer_to_moon_icrf == pytest.approx((1.0, 0.0, 0.0))
    assert result.jd_tt_emission == pytest.approx(100.0 - light_time_days)
    assert result.translation_label == "DE-0441LE-0441"

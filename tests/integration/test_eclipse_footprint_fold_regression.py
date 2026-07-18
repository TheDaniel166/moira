from __future__ import annotations

import math

import pytest

from moira.constants import EARTH_RADIUS_KM
from moira.eclipse import (
    _SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM,
    _WGS84_POLAR_RADIUS_KM,
    SolarEclipseFootprintBoundaryKind,
    _earth_fixed_solar_shadow,
    _penumbral_clearance_km,
    _wgs84_surface_xyz_km,
)
from moira.julian import julian_day


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]

_FOLD_SEED_JD = julian_day(1991, 1, 1)
_OUTPUT_SAMPLE_COUNTS = (9, 99, 181, 257, 721)
_INCIDENCE_TIME_TOLERANCE_S = 0.05
_INCIDENCE_POSITION_TOLERANCE_KM = 0.02
_DENSE_COMPONENT_STEP_CEILING_KM = 1_000.0
_SURFACE_EQUATION_TOLERANCE = 1.0e-12
_CONTINUOUS_SCAN_INTERVALS = 4096
_CONTINUOUS_TIME_TOLERANCE_DAYS = 1.0e-10
_PENUMBRAL_KINDS = (
    SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
    SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
)
_SOUTH_SHORT_ARM_DURATION_BOUNDS_S = (3.0, 4.0)


@pytest.fixture(scope="module")
def fold_footprints(eclipse_calculator):
    footprints = {
        sample_count: eclipse_calculator.solar_eclipse_footprint(
            _FOLD_SEED_JD,
            kind="annular",
            sample_count=sample_count,
        )
        for sample_count in _OUTPUT_SAMPLE_COUNTS
    }
    assert all(
        footprint.ephemeris == "DE-0441LE-0441"
        for footprint in footprints.values()
    )
    return footprints


def _track_structure(
    footprint,
) -> dict[SolarEclipseFootprintBoundaryKind, tuple[tuple[int, int], ...]]:
    result: dict[SolarEclipseFootprintBoundaryKind, list[tuple[int, int]]] = {}
    for track in footprint.tracks:
        result.setdefault(track.kind, []).append(
            (track.component_id, track.segment_id)
        )
    return {
        kind: tuple(sorted(identities))
        for kind, identities in result.items()
    }


def _point_xyz(point) -> tuple[float, float, float]:
    return _wgs84_surface_xyz_km(
        point.latitude_deg,
        point.longitude_deg,
    )


def _points_coincide(left, right) -> bool:
    return (
        abs(left.jd_ut - right.jd_ut) * 86400.0
        <= _INCIDENCE_TIME_TOLERANCE_S
        and math.dist(_point_xyz(left), _point_xyz(right))
        <= _INCIDENCE_POSITION_TOLERANCE_KM
    )


def _surface_equation_residual(point) -> float:
    x_km, y_km, z_km = _point_xyz(point)
    return abs(
        math.fsum(
            (
                (x_km * x_km + y_km * y_km)
                / (EARTH_RADIUS_KM * EARTH_RADIUS_KM),
                z_km * z_km
                / (_WGS84_POLAR_RADIUS_KM * _WGS84_POLAR_RADIUS_KM),
                -1.0,
            )
        )
    )


def _golden_section_maximum(objective, left: float, right: float) -> tuple[float, float]:
    golden = (math.sqrt(5.0) - 1.0) / 2.0
    x1 = right - golden * (right - left)
    x2 = left + golden * (right - left)
    f1 = objective(x1)
    f2 = objective(x2)
    for _ in range(80):
        if right - left <= _CONTINUOUS_TIME_TOLERANCE_DAYS:
            break
        if f1 >= f2:
            right = x2
            x2 = x1
            f2 = f1
            x1 = right - golden * (right - left)
            f1 = objective(x1)
        else:
            left = x1
            x1 = x2
            f1 = f2
            x2 = left + golden * (right - left)
            f2 = objective(x2)
    epoch = (left + right) / 2.0
    return epoch, objective(epoch)


def _continuous_fixed_site_maximum(
    *,
    shadow_at,
    xyz_km: tuple[float, float, float],
    left: float,
    right: float,
    witness_jd: float,
) -> tuple[float, float]:
    """Refine every resolved fixed-site maximum, not only grid samples."""

    step = (right - left) / _CONTINUOUS_SCAN_INTERVALS
    epochs = {
        left + index * step
        for index in range(_CONTINUOUS_SCAN_INTERVALS + 1)
    }
    epochs.add(witness_jd)
    for offset_s in (
        0.25,
        0.5,
        1.0,
        2.0,
        4.0,
        8.0,
        16.0,
        32.0,
        64.0,
        128.0,
    ):
        for direction in (-1.0, 1.0):
            epoch = witness_jd + direction * offset_s / 86400.0
            if left < epoch < right:
                epochs.add(epoch)
    ordered_epochs = tuple(sorted(epochs))

    def objective(epoch: float) -> float:
        return _penumbral_clearance_km(shadow_at(epoch), xyz_km)

    values = tuple(objective(epoch) for epoch in ordered_epochs)
    candidates = [
        (ordered_epochs[0], values[0]),
        (ordered_epochs[-1], values[-1]),
        (witness_jd, objective(witness_jd)),
    ]
    for index in range(1, len(ordered_epochs) - 1):
        if values[index] < values[index - 1] or values[index] < values[index + 1]:
            continue
        candidates.append(
            _golden_section_maximum(
                objective,
                ordered_epochs[index - 1],
                ordered_epochs[index + 1],
            )
        )
    return max(candidates, key=lambda item: item[1])


def _fold_cusp_and_neighbors(footprint, kind):
    tracks = tuple(
        sorted(
            (track for track in footprint.tracks if track.kind is kind),
            key=lambda track: (track.component_id, track.segment_id),
        )
    )
    assert len(tracks) == 2, (
        f"the 1991 multi-valued {kind.value} envelope requires two public segments"
    )
    shared_endpoint_pairs = tuple(
        (left_index, right_index)
        for left_index, left in enumerate(
            (tracks[0].points[0], tracks[0].points[-1])
        )
        for right_index, right in enumerate(
            (tracks[1].points[0], tracks[1].points[-1])
        )
        if _points_coincide(left, right)
    )
    assert len(shared_endpoint_pairs) == 1, (
        f"the two {kind.value} segments must share exactly one fold endpoint"
    )
    left_cusp_index, right_cusp_index = shared_endpoint_pairs[0]
    cusp = (tracks[0].points[0], tracks[0].points[-1])[
        left_cusp_index
    ]
    neighbors = []
    for track, cusp_index in (
        (tracks[0], left_cusp_index),
        (tracks[1], right_cusp_index),
    ):
        neighbor_index = 1 if cusp_index == 0 else -2
        neighbors.append(track.points[neighbor_index])
    return tracks, cusp, tuple(neighbors), shared_endpoint_pairs[0]


def _track_duration_s(track) -> float:
    return (track.points[-1].jd_ut - track.points[0].jd_ut) * 86400.0


def test_1991_fold_graph_is_independent_of_public_output_density(
    fold_footprints,
) -> None:
    structures = {
        sample_count: _track_structure(footprint)
        for sample_count, footprint in fold_footprints.items()
    }
    assert all(
        structure == structures[721]
        for structure in structures.values()
    )

    structure = structures[721]
    assert structure[SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH] == (
        (0, 0),
        (0, 1),
    )
    assert structure[SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH] == (
        (0, 0),
        (0, 1),
    )
    assert SolarEclipseFootprintBoundaryKind.SUNRISE in structure
    assert SolarEclipseFootprintBoundaryKind.SUNSET in structure
    for identities in structure.values():
        components = sorted({component_id for component_id, _ in identities})
        assert components == list(range(len(components)))
        for component_id in components:
            segments = sorted(
                segment_id
                for candidate_component, segment_id in identities
                if candidate_component == component_id
            )
            assert segments == list(range(len(segments)))

    reference = fold_footprints[721]
    for sample_count in _OUTPUT_SAMPLE_COUNTS[:-1]:
        candidate = fold_footprints[sample_count]
        assert candidate.event.jd_ut == pytest.approx(
            reference.event.jd_ut,
            abs=1.0e-12,
        )
        assert candidate.topology is reference.topology
        assert _points_coincide(candidate.greatest, reference.greatest)
        for contact_name in ("p1", "p2", "p3", "p4"):
            actual_contact = getattr(candidate.contacts, contact_name)
            expected_contact = getattr(reference.contacts, contact_name)
            assert (actual_contact is None) is (expected_contact is None)
            if actual_contact is not None and expected_contact is not None:
                assert actual_contact.kind is expected_contact.kind
                assert _points_coincide(
                    actual_contact.point,
                    expected_contact.point,
                )
        reference_tracks = {
            (track.kind, track.component_id, track.segment_id): track
            for track in reference.tracks
        }
        for track in candidate.tracks:
            expected = reference_tracks[
                (track.kind, track.component_id, track.segment_id)
            ]
            assert _points_coincide(track.points[0], expected.points[0])
            assert _points_coincide(track.points[-1], expected.points[-1])

    point_counts = tuple(
        sum(len(track.points) for track in fold_footprints[sample_count].tracks)
        for sample_count in _OUTPUT_SAMPLE_COUNTS
    )
    assert point_counts == tuple(sorted(point_counts))
    assert point_counts[0] < point_counts[-1]


def test_1991_south_fold_retains_its_short_three_second_arm(
    fold_footprints,
) -> None:
    """Pin a DE441 fold regression, not a NASA-published duration."""

    lower_s, upper_s = _SOUTH_SHORT_ARM_DURATION_BOUNDS_S
    for sample_count, footprint in fold_footprints.items():
        tracks, _cusp, _neighbors, _cusp_indices = _fold_cusp_and_neighbors(
            footprint,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
        )
        short_track = min(tracks, key=_track_duration_s)
        duration_s = _track_duration_s(short_track)
        assert lower_s < duration_s < upper_s, (
            f"sample_count={sample_count} returned a {duration_s:.6f}s "
            "south fold arm; the dated DE441 witness is about 3.523s"
        )


def test_1991_fold_segments_have_only_horizon_or_fold_incidence(
    fold_footprints,
) -> None:
    footprint = fold_footprints[721]
    horizon_points = tuple(
        point
        for track in footprint.tracks
        if track.kind
        in {
            SolarEclipseFootprintBoundaryKind.SUNRISE,
            SolarEclipseFootprintBoundaryKind.SUNSET,
        }
        for point in track.points
    )
    for kind in _PENUMBRAL_KINDS:
        tracks, cusp, _neighbors, cusp_indices = _fold_cusp_and_neighbors(
            footprint,
            kind,
        )
        assert not any(
            _points_coincide(cusp, point) for point in horizon_points
        )

        for track, cusp_index in zip(tracks, cusp_indices):
            non_cusp_endpoint = track.points[-1 if cusp_index == 0 else 0]
            assert any(
                _points_coincide(non_cusp_endpoint, point)
                for point in horizon_points
            )

    penumbral_tracks = tuple(
        track
        for track in footprint.tracks
        if track.kind
        in {
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
        }
    )
    for track in penumbral_tracks:
        component_peers = tuple(
            candidate
            for candidate in penumbral_tracks
            if candidate.kind is track.kind
            and candidate.component_id == track.component_id
            and candidate.segment_id != track.segment_id
        )
        for endpoint in (track.points[0], track.points[-1]):
            on_horizon = any(
                _points_coincide(endpoint, point) for point in horizon_points
            )
            at_shared_fold = any(
                _points_coincide(endpoint, peer_endpoint)
                for peer in component_peers
                for peer_endpoint in (peer.points[0], peer.points[-1])
            )
            assert on_horizon != at_shared_fold


def test_1991_dense_fold_components_do_not_contain_a_spatial_splice(
    fold_footprints,
) -> None:
    footprint = fold_footprints[721]
    failures = []
    for track in footprint.tracks:
        if track.kind not in {
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
        }:
            continue
        for index, (left, right) in enumerate(zip(track.points, track.points[1:])):
            distance_km = math.dist(_point_xyz(left), _point_xyz(right))
            if distance_km > _DENSE_COMPONENT_STEP_CEILING_KM:
                failures.append(
                    f"{track.kind.value}[{track.component_id}:{track.segment_id}] "
                    f"point-pair {index} "
                    f"spans {distance_km:.3f} km in "
                    f"{(right.jd_ut - left.jd_ut) * 86400.0:.3f} s"
                )
    assert not failures, "spliced dense footprint components:\n" + "\n".join(
        failures
    )


def test_1991_fold_points_are_on_wgs84_and_the_instantaneous_cone(
    eclipse_calculator,
    fold_footprints,
) -> None:
    footprint = fold_footprints[721]
    contacts = tuple(
        contact
        for contact in (
            footprint.contacts.p1,
            footprint.contacts.p2,
            footprint.contacts.p3,
            footprint.contacts.p4,
        )
        if contact is not None
    )
    points = tuple(
        point for track in footprint.tracks for point in track.points
    ) + tuple(contact.point for contact in contacts)
    shadow_cache = {}
    max_surface_residual = 0.0
    max_clearance_km = 0.0
    for point in points:
        max_surface_residual = max(
            max_surface_residual,
            _surface_equation_residual(point),
        )
        cache_key = round(point.jd_ut, 14)
        shadow = shadow_cache.get(cache_key)
        if shadow is None:
            shadow = _earth_fixed_solar_shadow(eclipse_calculator, point.jd_ut)
            assert shadow is not None
            shadow_cache[cache_key] = shadow
        max_clearance_km = max(
            max_clearance_km,
            abs(_penumbral_clearance_km(shadow, _point_xyz(point))),
        )

    assert max_surface_residual <= _SURFACE_EQUATION_TOLERANCE
    assert max_clearance_km <= _SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM


def test_1991_fold_sites_are_continuous_fixed_site_path_limits(
    eclipse_calculator,
    fold_footprints,
) -> None:
    footprint = fold_footprints[721]
    north_tracks, north_cusp, north_neighbors, _north_cusp_indices = (
        _fold_cusp_and_neighbors(
            footprint,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
        )
    )
    south_tracks, south_cusp, south_neighbors, _south_cusp_indices = (
        _fold_cusp_and_neighbors(
            footprint,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
        )
    )
    left = footprint.contacts.p1.point.jd_ut
    right = footprint.contacts.p4.point.jd_ut
    shadow_cache = {}

    def shadow_at(epoch: float):
        key = round(epoch, 14)
        shadow = shadow_cache.get(key)
        if shadow is None:
            shadow = _earth_fixed_solar_shadow(eclipse_calculator, epoch)
            assert shadow is not None
            shadow_cache[key] = shadow
        return shadow

    north_short_index = min(
        range(len(north_tracks)),
        key=lambda index: _track_duration_s(north_tracks[index]),
    )
    north_long_index = 1 - north_short_index
    south_short_index = min(
        range(len(south_tracks)),
        key=lambda index: _track_duration_s(south_tracks[index]),
    )
    witnesses = (
        ("north-cusp", north_cusp),
        ("north-long-arm-neighbor", north_neighbors[north_long_index]),
        ("north-short-arm-neighbor", north_neighbors[north_short_index]),
        ("south-cusp", south_cusp),
        ("south-short-arm-neighbor", south_neighbors[south_short_index]),
    )

    failures = []
    for label, point in witnesses:
        xyz_km = _point_xyz(point)
        instantaneous = _penumbral_clearance_km(
            shadow_at(point.jd_ut),
            xyz_km,
        )
        maximum_epoch, maximum_clearance = _continuous_fixed_site_maximum(
            shadow_at=shadow_at,
            xyz_km=xyz_km,
            left=left,
            right=right,
            witness_jd=point.jd_ut,
        )
        if abs(instantaneous) > _SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM:
            failures.append(
                f"{label} instantaneous clearance={instantaneous:.9f} km"
            )
        if maximum_clearance > _SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM:
            failures.append(
                f"{label} continuous maximum={maximum_clearance:.9f} km "
                f"at {maximum_epoch:.12f} UT1"
            )
    assert not failures, "non-limiting fold sites:\n" + "\n".join(failures)

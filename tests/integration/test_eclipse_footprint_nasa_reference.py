from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.constants import EARTH_RADIUS_KM
from moira.eclipse import (
    _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS,
    SolarEclipseFootprintBoundaryKind,
    SolarEclipseFootprintTopology,
    _WGS84_POLAR_RADIUS_KM,
    _earth_fixed_solar_shadow,
    _offset_geographic_km,
    _penumbral_clearance_km,
    _solar_altitude_derivative_sign,
    _solar_axis_surface_point,
    _topocentric_solar_altitude_proxy,
    _wgs84_surface_xyz_km,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "nasa_solar_penumbral_footprint_reference.json"
)

_ADMITTED_TOLERANCES = {
    "anchor_time_s": 5.0,
    "surface_position_km": 40.0,
    "penumbral_clearance_km": 0.001,
    "wgs84_surface_equation_residual": 1.0e-12,
}

# DE441 regression identity, distinct from the sparse NASA authority rows.
# NASA's map topology corroborates each connected component, not Moira's
# internal time-monotone segment identifiers.
_DE441_PENUMBRAL_SEGMENT_STRUCTURE = {
    "2003-11-23-one-limit-penumbral-footprint": {
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH: ((0, 0), (0, 1)),
    },
    "2006-03-29-two-limit-penumbral-footprint": {
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH: ((0, 0), (0, 1)),
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH: ((0, 0), (0, 1)),
    },
}


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _surface_distance_km(
    actual: tuple[float, float],
    expected: tuple[float, float],
) -> float:
    actual_latitude, actual_longitude = map(math.radians, actual)
    expected_latitude, expected_longitude = map(math.radians, expected)
    actual_unit = (
        math.cos(actual_latitude) * math.cos(actual_longitude),
        math.cos(actual_latitude) * math.sin(actual_longitude),
        math.sin(actual_latitude),
    )
    expected_unit = (
        math.cos(expected_latitude) * math.cos(expected_longitude),
        math.cos(expected_latitude) * math.sin(expected_longitude),
        math.sin(expected_latitude),
    )
    cross = (
        actual_unit[1] * expected_unit[2]
        - actual_unit[2] * expected_unit[1],
        actual_unit[2] * expected_unit[0]
        - actual_unit[0] * expected_unit[2],
        actual_unit[0] * expected_unit[1]
        - actual_unit[1] * expected_unit[0],
    )
    cross_norm = math.sqrt(math.fsum(component * component for component in cross))
    dot = math.fsum(
        left * right for left, right in zip(actual_unit, expected_unit)
    )
    return EARTH_RADIUS_KM * math.atan2(cross_norm, dot)


def _row_coordinates(row: dict) -> tuple[float, float]:
    return float(row["latitude_deg"]), float(row["longitude_deg"])


def _surface_equation_residual(xyz_km: tuple[float, float, float]) -> float:
    x_km, y_km, z_km = xyz_km
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


def test_nasa_footprint_fixture_preserves_authority_and_topology_semantics() -> None:
    fixture = _load_fixture()
    source = fixture["source"]
    receipt = fixture["de441_runtime_receipt"]

    assert fixture["schema_version"] == 1
    assert fixture["tolerances"] == _ADMITTED_TOLERANCES
    assert source["authority"] == (
        "NASA Goddard Space Flight Center Eclipse Web Site"
    )
    assert source["topology_url"] == (
        "https://eclipse.gsfc.nasa.gov/SEmono/reference/map.html"
    )
    assert source["published_product"] == (
        "Shadow Contacts and Circumstances: penumbral P contacts and "
        "extreme north/south limits"
    )
    assert source["time_scale"] == "TDT/TT"
    assert "True Longitude" in source["coordinate_semantics"]
    assert "P1/P4" in source["topology_semantics"]
    assert "P2/P3" in source["topology_semantics"]
    assert "do not publish a dense coordinate oracle" in source["comparison_scope"]
    assert "cross-model" in source["reference_model_note"]
    assert "not NASA uncertainty" in fixture["tolerance_note"]

    assert receipt["ephemeris"] == "DE-0441LE-0441"
    assert receipt["sample_count"] == 181
    assert "only its explicitly named Moira penumbral boundary family" in receipt[
        "matching_rule"
    ]
    assert "distinct from NASA" in receipt["matching_rule"]
    assert receipt["max_anchor_time_residual_s"] <= _ADMITTED_TOLERANCES[
        "anchor_time_s"
    ]
    assert receipt["max_surface_position_residual_km"] <= _ADMITTED_TOLERANCES[
        "surface_position_km"
    ]
    assert "regression receipt" in receipt["evidence_class"]

    events = fixture["events"]
    assert [row["expected_topology"] for row in events] == [
        "one_limit_connected",
        "two_limit_two_loop",
    ]
    assert [contact["kind"] for contact in events[0]["contacts"]] == ["p1", "p4"]
    assert [contact["kind"] for contact in events[1]["contacts"]] == [
        "p1",
        "p2",
        "p3",
        "p4",
    ]
    assert [row["label"] for row in events[0]["extrema"]] == ["N1", "S1"]
    assert [row["boundary_kind"] for row in events[0]["extrema"]] == [
        "penumbral_north",
        "penumbral_north",
    ]
    assert [row["label"] for row in events[1]["extrema"]] == [
        "N1",
        "S1",
        "N2",
        "S2",
    ]
    assert [row["boundary_kind"] for row in events[1]["extrema"]] == [
        "penumbral_north",
        "penumbral_south",
        "penumbral_north",
        "penumbral_south",
    ]

    for event in events:
        event_source = event["source"]
        assert event["kind"] == "total"
        assert event_source["table_1_url"].startswith(
            "https://eclipse.gsfc.nasa.gov/SEmono/"
        )
        assert event_source["table_2_url"].startswith(
            "https://eclipse.gsfc.nasa.gov/SEmono/"
        )
        assert event_source["map_url"].startswith(
            "https://eclipse.gsfc.nasa.gov/SEmono/"
        )
        assert event_source["reference_ephemeris"] == "DE200/LE200"
        assert event_source["lunar_radius_constants"] == {
            "k1_penumbral": 0.2725076,
            "k2_umbral": 0.272281,
        }
        contact_times = [float(row["tt_jd"]) for row in event["contacts"]]
        assert all(
            earlier < later for earlier, later in zip(contact_times, contact_times[1:])
        )
        for row in (*event["contacts"], *event["extrema"]):
            latitude_deg, longitude_deg = _row_coordinates(row)
            assert -90.0 <= latitude_deg <= 90.0
            assert -180.0 <= longitude_deg <= 180.0
            assert row["published_tdt"].endswith(" TDT/TT")


@pytest.mark.slow
def test_de441_footprints_reach_nasa_sparse_contacts_and_extrema(
    eclipse_calculator,
) -> None:
    """Validate sparse authority anchors without claiming dense-track parity."""

    fixture = _load_fixture()
    tolerances = fixture["tolerances"]
    receipt = fixture["de441_runtime_receipt"]
    measured: list[tuple[str, float, float]] = []
    failures: list[str] = []

    for event_row in fixture["events"]:
        footprint = eclipse_calculator.solar_eclipse_footprint(
            float(event_row["seed_jd"]),
            kind=str(event_row["kind"]),
            sample_count=int(receipt["sample_count"]),
        )
        assert footprint.ephemeris == receipt["ephemeris"]
        assert footprint.event.data.eclipse_type.is_total
        assert footprint.surface_model == "WGS84_ZERO_ELEVATION"
        assert footprint.limb_model == "SPHERICAL_MEAN_LIMB"
        assert footprint.time_scale == "UT1"
        assert footprint.atmospheric_refraction is False
        assert footprint.topology is SolarEclipseFootprintTopology(
            event_row["expected_topology"]
        )
        actual_penumbral_structure = {
            kind: tuple(
                sorted(
                    (track.component_id, track.segment_id)
                    for track in footprint.tracks
                    if track.kind is kind
                )
            )
            for kind in {
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
            }
            if any(track.kind is kind for track in footprint.tracks)
        }
        assert actual_penumbral_structure == _DE441_PENUMBRAL_SEGMENT_STRUCTURE[
            str(event_row["id"])
        ]

        contacts = {
            kind: getattr(footprint.contacts, kind)
            for kind in ("p1", "p2", "p3", "p4")
        }
        expected_contact_kinds = {
            row["kind"] for row in event_row["contacts"]
        }
        assert {
            kind for kind, contact in contacts.items() if contact is not None
        } == expected_contact_kinds

        for row in event_row["contacts"]:
            contact = contacts[str(row["kind"])]
            assert contact is not None
            point = contact.point
            time_residual_s = abs(
                _ut1_to_ephemeris_tt(point.jd_ut, eclipse_calculator._reader)
                - float(row["tt_jd"])
            ) * 86400.0
            distance_residual_km = _surface_distance_km(
                (point.latitude_deg, point.longitude_deg),
                _row_coordinates(row),
            )
            anchor_id = f"{event_row['id']}:{str(row['kind']).upper()}"
            measured.append((anchor_id, time_residual_s, distance_residual_km))
            if (
                time_residual_s > float(tolerances["anchor_time_s"])
                or distance_residual_km > float(tolerances["surface_position_km"])
            ):
                failures.append(
                    f"{anchor_id} time={time_residual_s:.6f}s "
                    f"surface={distance_residual_km:.6f}km"
                )

        penumbral_boundary_points = tuple(
            (
                track.kind,
                track.component_id,
                track.segment_id,
                point,
                _ut1_to_ephemeris_tt(point.jd_ut, eclipse_calculator._reader),
            )
            for track in footprint.tracks
            if track.kind
            in {
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
            }
            for point in track.points
        )
        for row in event_row["extrema"]:
            expected_tt = float(row["tt_jd"])
            expected_kind = SolarEclipseFootprintBoundaryKind(
                str(row["boundary_kind"])
            )
            assert expected_kind.value in event_row[
                "expected_penumbral_track_kinds"
            ]
            candidates: list[
                tuple[
                    float,
                    float,
                    SolarEclipseFootprintBoundaryKind,
                    int,
                    int,
                ]
            ] = []
            for (
                track_kind,
                component_id,
                segment_id,
                point,
                point_tt,
            ) in penumbral_boundary_points:
                if track_kind is not expected_kind:
                    continue
                time_residual_s = abs(point_tt - expected_tt) * 86400.0
                if time_residual_s > float(tolerances["anchor_time_s"]):
                    continue
                distance_residual_km = _surface_distance_km(
                    (point.latitude_deg, point.longitude_deg),
                    _row_coordinates(row),
                )
                candidates.append(
                    (
                        distance_residual_km,
                        time_residual_s,
                        track_kind,
                        component_id,
                        segment_id,
                    )
                )
            anchor_id = f"{event_row['id']}:{row['label']}"
            if not candidates:
                failures.append(
                    f"{anchor_id} has no returned boundary point within "
                    f"{tolerances['anchor_time_s']}s"
                )
                continue
            (
                distance_residual_km,
                time_residual_s,
                track_kind,
                component_id,
                segment_id,
            ) = min(candidates)
            assert track_kind is expected_kind
            measured.append((anchor_id, time_residual_s, distance_residual_km))
            if distance_residual_km > float(tolerances["surface_position_km"]):
                failures.append(
                    f"{anchor_id} time={time_residual_s:.6f}s "
                    f"surface={distance_residual_km:.6f}km "
                    f"track={track_kind.value}[{component_id}:{segment_id}]"
                )

    assert not failures, "NASA sparse footprint-anchor mismatches:\n" + "\n".join(
        failures
    )
    max_time = max(measured, key=lambda item: item[1])
    max_distance = max(measured, key=lambda item: item[2])
    # These are one-sided dated regression receipts. A smaller residual is an
    # improvement; a larger one requires deliberate review even if it remains
    # beneath the rounded external-comparison ceiling.
    assert max_time[1] <= float(receipt["max_anchor_time_residual_s"]) + 0.01
    assert max_distance[2] <= (
        float(receipt["max_surface_position_residual_km"]) + 0.01
    )


@pytest.mark.slow
def test_de441_footprint_tracks_obey_wgs84_and_penumbral_clearance_invariants(
    eclipse_calculator,
) -> None:
    fixture = _load_fixture()
    tolerances = fixture["tolerances"]

    for event_row in fixture["events"]:
        footprint = eclipse_calculator.solar_eclipse_footprint(
            float(event_row["seed_jd"]),
            kind=str(event_row["kind"]),
            sample_count=int(fixture["de441_runtime_receipt"]["sample_count"]),
        )
        track_kinds = {track.kind for track in footprint.tracks}
        assert {
            SolarEclipseFootprintBoundaryKind.SUNRISE,
            SolarEclipseFootprintBoundaryKind.SUNSET,
        }.issubset(track_kinds)
        assert {
            kind.value
            for kind in track_kinds
            if kind
            in {
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
            }
        } == set(event_row["expected_penumbral_track_kinds"])

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
        assert all(
            left.point.jd_ut < right.point.jd_ut
            for left, right in zip(contacts, contacts[1:])
        )
        all_points = tuple(
            point for track in footprint.tracks for point in track.points
        ) + tuple(contact.point for contact in contacts)
        shadow_cache = {}
        max_surface_residual = 0.0
        max_clearance_km = 0.0
        for point in all_points:
            xyz_km = _wgs84_surface_xyz_km(
                point.latitude_deg,
                point.longitude_deg,
            )
            max_surface_residual = max(
                max_surface_residual,
                _surface_equation_residual(xyz_km),
            )
            cache_key = round(point.jd_ut, 14)
            shadow = shadow_cache.get(cache_key)
            if shadow is None:
                shadow = _earth_fixed_solar_shadow(
                    eclipse_calculator,
                    point.jd_ut,
                )
                assert shadow is not None
                shadow_cache[cache_key] = shadow
            max_clearance_km = max(
                max_clearance_km,
                abs(_penumbral_clearance_km(shadow, xyz_km)),
            )

        assert max_surface_residual <= float(
            tolerances["wgs84_surface_equation_residual"]
        )
        assert max_clearance_km <= float(tolerances["penumbral_clearance_km"])


@pytest.mark.slow
def test_boundary_graph_is_independent_of_requested_output_density(
    eclipse_calculator,
) -> None:
    """Lock a sub-minute polar reversal that a presentation grid once hid."""

    seed_jd = 2_448_622.5  # 1992-01-01; next eclipse is 1992-01-04.
    sample_counts = (9, 99, 257, 721)
    footprints = {
        sample_count: eclipse_calculator.solar_eclipse_footprint(
            seed_jd,
            sample_count=sample_count,
        )
        for sample_count in sample_counts
    }
    dense = footprints[721]
    dense_structure = tuple(
        (track.kind, track.component_id, track.segment_id)
        for track in dense.tracks
    )
    transitions = []
    for sample_count, footprint in footprints.items():
        structure = tuple(
            (track.kind, track.component_id, track.segment_id)
            for track in footprint.tracks
        )
        assert footprint.event.jd_ut == pytest.approx(
            dense.event.jd_ut,
            abs=1.0e-12,
        )
        assert footprint.topology is dense.topology
        assert structure == dense_structure, sample_count
        assert {
            track.component_id
            for track in footprint.tracks
            if track.kind is SolarEclipseFootprintBoundaryKind.SUNSET
        } == {0, 1, 2}

        short_component = next(
            track
            for track in footprint.tracks
            if track.kind is SolarEclipseFootprintBoundaryKind.SUNSET
            and track.component_id == 1
        )
        assert 0.0 < (
            short_component.points[-1].jd_ut
            - short_component.points[0].jd_ut
        ) * 86400.0 < 60.0
        transition = short_component.points[-1]
        sunrise_successor = next(
            track
            for track in footprint.tracks
            if track.kind is SolarEclipseFootprintBoundaryKind.SUNRISE
            and track.component_id == 2
        )
        assert transition == sunrise_successor.points[0]
        shared_incidence = tuple(
            (track.kind, track.component_id, track.segment_id, endpoint_index)
            for track in footprint.tracks
            if track is not short_component
            for endpoint_index, endpoint in enumerate(
                (track.points[0], track.points[-1])
            )
            if endpoint == transition
        )
        assert shared_incidence == (
            (SolarEclipseFootprintBoundaryKind.SUNRISE, 2, 0, 0),
        )
        transitions.append(transition)

    assert all(transition == transitions[-1] for transition in transitions)
    transition = transitions[-1]
    transition_xyz = _wgs84_surface_xyz_km(
        transition.latitude_deg,
        transition.longitude_deg,
    )
    before = _earth_fixed_solar_shadow(
        eclipse_calculator,
        transition.jd_ut - _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS,
    )
    after = _earth_fixed_solar_shadow(
        eclipse_calculator,
        transition.jd_ut + _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS,
    )
    assert before is not None
    assert after is not None
    assert abs(
        _solar_altitude_derivative_sign(before, after, transition_xyz)
    ) <= 1.0e-9


@pytest.mark.slow
def test_partial_greatest_uses_the_same_sunlit_physical_cone(
    eclipse_calculator,
) -> None:
    footprint = eclipse_calculator.solar_eclipse_footprint(
        2_451_579.5,
        kind="partial",
        sample_count=9,
    )
    greatest = footprint.greatest
    assert _solar_axis_surface_point(
        eclipse_calculator,
        footprint.event.jd_ut,
    ) is None
    shadow = _earth_fixed_solar_shadow(eclipse_calculator, greatest.jd_ut)
    assert shadow is not None
    greatest_xyz = _wgs84_surface_xyz_km(
        greatest.latitude_deg,
        greatest.longitude_deg,
    )
    greatest_clearance = _penumbral_clearance_km(shadow, greatest_xyz)
    assert greatest_clearance > 0.0
    assert _topocentric_solar_altitude_proxy(shadow, greatest_xyz) >= 0.0

    for north_km, east_km in (
        (-1.0, 0.0),
        (1.0, 0.0),
        (0.0, -1.0),
        (0.0, 1.0),
    ):
        latitude_deg, longitude_deg = _offset_geographic_km(
            greatest.latitude_deg,
            greatest.longitude_deg,
            north_km,
            east_km,
        )
        neighbor_xyz = _wgs84_surface_xyz_km(latitude_deg, longitude_deg)
        if _topocentric_solar_altitude_proxy(shadow, neighbor_xyz) >= 0.0:
            assert _penumbral_clearance_km(shadow, neighbor_xyz) <= (
                greatest_clearance + 1.0e-6
            )

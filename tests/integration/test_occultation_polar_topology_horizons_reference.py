from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira.constants import Body, EARTH_RADIUS_KM
from moira.occultations import (
    OccultationGeographicPole,
    OccultationPathBoundarySide,
    OccultationPathTopologyKind,
    OccultationPoleCrossingPhase,
    lunar_occultation_path_topology,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "jpl_horizons_polar_occultation_reference.json"
)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _angular_separation_deg(
    left_ra_deg: float,
    left_dec_deg: float,
    right_ra_deg: float,
    right_dec_deg: float,
) -> float:
    left_ra, left_dec, right_ra, right_dec = map(
        math.radians,
        (left_ra_deg, left_dec_deg, right_ra_deg, right_dec_deg),
    )
    delta_ra = right_ra - left_ra
    numerator = math.hypot(
        math.cos(right_dec) * math.sin(delta_ra),
        math.cos(left_dec) * math.sin(right_dec)
        - math.sin(left_dec) * math.cos(right_dec) * math.cos(delta_ra),
    )
    denominator = (
        math.sin(left_dec) * math.sin(right_dec)
        + math.cos(left_dec) * math.cos(right_dec) * math.cos(delta_ra)
    )
    return math.degrees(math.atan2(numerator, denominator))


def _surface_distance_km(
    left_latitude_deg: float,
    left_longitude_deg: float,
    right_latitude_deg: float,
    right_longitude_deg: float,
) -> float:
    def unit(latitude_deg: float, longitude_deg: float) -> tuple[float, float, float]:
        latitude = math.radians(latitude_deg)
        longitude = math.radians(longitude_deg)
        cos_latitude = math.cos(latitude)
        return (
            cos_latitude * math.cos(longitude),
            cos_latitude * math.sin(longitude),
            math.sin(latitude),
        )

    left = unit(left_latitude_deg, left_longitude_deg)
    right = unit(right_latitude_deg, right_longitude_deg)
    cross = (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))
    return EARTH_RADIUS_KM * math.atan2(
        math.sqrt(sum(component * component for component in cross)),
        dot,
    )


def _distance_from_bracket_s(value: float, lower: float, upper: float) -> float:
    if value < lower:
        return (lower - value) * 86400.0
    if value > upper:
        return (value - upper) * 86400.0
    return 0.0


def test_horizons_fixture_preserves_airless_polar_contact_semantics() -> None:
    fixture = _load_fixture()
    source = fixture["primary_authority"]
    query = fixture["query"]
    observer = fixture["observer"]

    assert fixture["schema_version"] == 1
    assert fixture["evidence_class"] == "authority_validation"
    assert source["institution"] == (
        "NASA Jet Propulsion Laboratory Solar System Dynamics Group"
    )
    assert source["api_signature_version"] == "1.2"
    assert source["credit"] == (
        "NASA/JPL-Caltech, Solar System Dynamics Group"
    )
    assert query["common_parameters"]["APPARENT"] == "AIRLESS"
    assert query["common_parameters"]["QUANTITIES"] == "2,13,49"
    assert query["reported_kernel_sources"] == {
        "moon": "DE441",
        "earth": "DE441",
        "mars": "mar099",
    }
    assert observer == {
        "surface_model": "WGS84_GEODETIC",
        "horizons_center_frame": "ITRF93",
        "latitude_deg": 90.0,
        "longitude_deg": 0.0,
        "elevation_m": 0.0,
        "longitude_at_exact_pole": "canonical_only",
    }
    assert fixture["event"]["eop_status_at_retrieval"] == "PREDICTIVE"

    observed_signs: list[str] = []
    for contact in fixture["contacts"]:
        assert float(contact["bracket_width_s"]) == 0.5
        for row in contact["rows"]:
            moon = row["moon"]
            mars = row["mars"]
            separation = _angular_separation_deg(
                moon["ra_deg"],
                moon["dec_deg"],
                mars["ra_deg"],
                mars["dec_deg"],
            )
            radii_sum = (
                moon["angular_diameter_arcsec"]
                + mars["angular_diameter_arcsec"]
            ) / 7200.0
            clearance = radii_sum - separation
            assert separation == pytest.approx(row["separation_deg"], abs=1.0e-15)
            assert radii_sum == pytest.approx(row["radii_sum_deg"], abs=1.0e-15)
            assert clearance == pytest.approx(row["clearance_deg"], abs=1.0e-15)
            assert row["jd_ut1"] == pytest.approx(
                row["jd_utc"] + row["dut1_s"] / 86400.0,
                abs=5.0e-10,
            )
            observed_signs.append("inside" if clearance > 0.0 else "outside")

    assert observed_signs == fixture["validation_policy"]["required_sign_sequence"]
    assert "does not independently" in fixture["validation_policy"]["scope"]


@pytest.mark.requires_ephemeris
def test_de441_topology_recovers_horizons_north_pole_containment(reader) -> None:
    fixture = _load_fixture()
    policy = fixture["validation_policy"]
    jd_start, jd_end = map(float, policy["engine_search_window_jd_ut1"])

    events = lunar_occultation_path_topology(
        Body.MARS,
        jd_start,
        jd_end,
        step_days=float(policy["engine_search_step_days"]),
        sample_count=int(policy["engine_topology_sample_count"]),
        observer_elev_m=0.0,
        reader=reader,
    )

    assert len(events) == 1
    topology = events[0]
    assert topology.topology is OccultationPathTopologyKind.TWO_SIDED_BAND
    assert topology.summary.occulting_body == Body.MOON
    assert topology.summary.occulted_body == Body.MARS
    assert topology.summary.path_width_km > 0.0
    assert topology.summary.duration_at_greatest_s > 0.0
    assert topology.observer_elevation_m == 0.0
    assert topology.lunar_limb_model == "SPHERICAL_MEAN_LIMB"
    assert topology.target_model == "JPL_EQUATORIAL_SOLID_BODY"
    assert topology.time_scale == "UT1"
    assert topology.atmospheric_refraction is False
    assert topology.saturn_rings_included is False

    assert len(topology.centers) == int(policy["engine_topology_sample_count"])
    assert topology.summary.central_line_lats == tuple(
        point.latitude_deg for point in topology.centers
    )
    assert topology.summary.central_line_lons == tuple(
        point.longitude_deg for point in topology.centers
    )
    assert tuple(track.side for track in topology.boundaries) == (
        OccultationPathBoundarySide.LEFT,
        OccultationPathBoundarySide.RIGHT,
    )

    center_by_epoch = {point.jd_ut: point for point in topology.centers}
    for track in topology.boundaries:
        for boundary in track.points:
            center = center_by_epoch[boundary.point.jd_ut]
            measured_distance = _surface_distance_km(
                center.latitude_deg,
                center.longitude_deg,
                boundary.point.latitude_deg,
                boundary.point.longitude_deg,
            )
            assert boundary.cross_track_distance_km == pytest.approx(
                measured_distance,
                abs=1.0e-5,
            )
            assert abs(boundary.point.clearance_deg) <= 1.0e-7

    greatest_center = center_by_epoch[topology.summary.jd_greatest_ut]
    measured_width = _surface_distance_km(
        greatest_center.latitude_deg,
        greatest_center.longitude_deg,
        topology.greatest_left.point.latitude_deg,
        topology.greatest_left.point.longitude_deg,
    ) + _surface_distance_km(
        greatest_center.latitude_deg,
        greatest_center.longitude_deg,
        topology.greatest_right.point.latitude_deg,
        topology.greatest_right.point.longitude_deg,
    )
    assert topology.summary.path_width_km == pytest.approx(
        measured_width,
        abs=2.0e-5,
    )

    north_crossings = [
        crossing
        for crossing in topology.pole_crossings
        if crossing.pole is OccultationGeographicPole.NORTH
    ]
    assert tuple(crossing.phase for crossing in north_crossings) == (
        OccultationPoleCrossingPhase.INGRESS,
        OccultationPoleCrossingPhase.EGRESS,
    )
    assert all(crossing.boundary_side is not None for crossing in north_crossings)

    tolerance_s = float(policy["moira_contact_time_tolerance_s"])
    for actual, expected in zip(north_crossings, fixture["contacts"]):
        lower, upper = (float(row["jd_ut1"]) for row in expected["rows"])
        assert _distance_from_bracket_s(
            actual.point.jd_ut,
            lower,
            upper,
        ) <= tolerance_s
        assert actual.point.latitude_deg == 90.0
        assert actual.point.longitude_deg == 0.0
        assert abs(actual.point.clearance_deg) <= 1.0e-7

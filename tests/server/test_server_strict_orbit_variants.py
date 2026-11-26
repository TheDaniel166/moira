"""Verify strict orbit transport against the request-bound planetary kernel."""

import math

import pytest
from fastapi.testclient import TestClient

from moira.constants import KM_PER_AU
from moira.orbits import (
    ApsidalDirection,
    OrbitalCenter,
    OrbitalFrame,
    apsidal_passages,
    osculating_elements,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


@pytest.fixture
def kernel_client(moira_engine, monkeypatch):
    """Serve orbit requests with the same reader used for direct verification."""
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        yield client


@pytest.mark.parametrize(
    ("body", "center", "frame", "jd_ut", "orientation", "router_branch"),
    [
        ("Moon", OrbitalCenter.EARTH, OrbitalFrame.J2000_ECLIPTIC,
         2451545.0, "fixed_J2000_ecliptic", "fixed_j2000"),
        ("Mars", OrbitalCenter.SUN, OrbitalFrame.MEAN_ECLIPTIC_OF_DATE,
         2451545.0, "mean_ecliptic_of_date", "modern_mean"),
        ("Moon", OrbitalCenter.EARTH, OrbitalFrame.MEAN_ECLIPTIC_OF_DATE,
         2400000.0, "mean_ecliptic_of_date", "long_term_mean"),
        ("Moon", OrbitalCenter.EARTH, OrbitalFrame.TRUE_ECLIPTIC_OF_DATE,
         2451545.0, "true_ecliptic_of_date", "modern_true"),
    ],
)
def test_elements_select_center_and_frame(
    kernel_client, moira_engine, body, center, frame, jd_ut, orientation, router_branch
):
    """Return engine elements in the requested axes with center-specific names."""
    response = kernel_client.post(
        "/v1/orbits/elements",
        json={"body": body, "jd_ut": jd_ut, "center": center.value, "frame": frame.value},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    expected = osculating_elements(
        body, jd_ut, center=center, frame=frame, reader=moira_engine._reader
    )
    provenance = payload["provenance"]
    assert (provenance["center"], provenance["frame"]) == (center.value, frame.value)
    assert provenance["orientation"] == orientation
    assert provenance["frame_construction"]["router_branch"] == router_branch
    assert provenance["shape"] == expected.shape.value
    assert provenance["undefined"] == []
    assert provenance["gravity"]["component_naif_ids"] == list(
        expected.provenance.gravity.component_naif_ids
    )
    assert [
        [leg["center_naif_id"], leg["target_naif_id"], leg["traversal_sign"]]
        for leg in provenance["state_source"]["legs"]
    ] == [
        [leg.center_naif_id, leg.target_naif_id, leg.traversal_sign]
        for leg in expected.provenance.state_source.legs
    ]
    assert payload["time"]["jd_ut"] == jd_ut
    assert payload["time"]["epoch_tdb"] == expected.epoch_tdb
    elements = payload["elements"]
    assert elements["epoch_jd"] == expected.epoch_tt
    assert elements["eccentricity"] == expected.eccentricity
    assert elements["inclination_deg"] == expected.inclination_deg
    assert elements["lon_ascending_node_deg"] == expected.lon_ascending_node_deg
    if center is OrbitalCenter.EARTH:
        assert elements["arg_perigee_deg"] == expected.arg_pericenter_deg
        assert elements["perigee_distance_au"] == expected.pericenter_distance_au
        assert elements["apogee_distance_au"] == expected.apocenter_distance_au
        assert "arg_perihelion_deg" not in elements
    else:
        assert elements["arg_perihelion_deg"] == expected.arg_pericenter_deg
        assert elements["perihelion_distance_au"] == expected.pericenter_distance_au
        assert elements["aphelion_distance_au"] == expected.apocenter_distance_au


def _lunar_range_and_radial_product(reader, jd_tdb):
    """Measure Moon relative to Earth by differencing the two DE441 states."""
    moon_pos, moon_vel = reader.position_and_velocity_tdb(3, 301, jd_tdb)
    earth_pos, earth_vel = reader.position_and_velocity_tdb(3, 399, jd_tdb)
    offset = tuple(moon - earth for moon, earth in zip(moon_pos, earth_pos, strict=True))
    velocity = tuple(moon - earth for moon, earth in zip(moon_vel, earth_vel, strict=True))
    return math.hypot(*offset) / KM_PER_AU, math.fsum(
        position * rate for position, rate in zip(offset, velocity, strict=True)
    )


@pytest.mark.parametrize("direction", list(ApsidalDirection))
def test_bounded_lunar_passages_follow_direction(kernel_client, moira_engine, direction):
    """Match both engine outcomes and verify each radial sign change in DE441."""
    jd_ut = 2451545.0
    max_days = 35.0
    response = kernel_client.post(
        "/v1/orbits/distance-extremes",
        json={
            "body": "Moon", "jd_ut": jd_ut, "center": "EARTH",
            "direction": direction.value, "max_days": max_days,
        },
    )
    assert response.status_code == 200, response.text
    reader = moira_engine._reader
    expected = apsidal_passages(
        "Moon", jd_ut, center=OrbitalCenter.EARTH, direction=direction,
        max_days=max_days, reader=reader,
    )
    payload = response.json()
    provenance = payload["provenance"]
    assert (provenance["center"], provenance["direction"]) == ("EARTH", direction.value)
    assert provenance["search"]["search_window_source"] == "EXPLICIT_MAX_DAYS"
    assert provenance["search"]["searched_interval_tdb"] == list(
        expected.provenance.searched_interval_tdb
    )
    assert payload["time"]["jd_ut"] == jd_ut
    assert payload["time"]["epoch_tt"] == expected.start_epoch_tt
    assert payload["time"]["epoch_tdb"] == expected.start_epoch_tdb
    sign = 1 if direction is ApsidalDirection.NEXT else -1
    for kind, lunar_name, sign_after in (
        ("pericenter", "perigee", 1),
        ("apocenter", "apogee", -1),
    ):
        passage = provenance[kind]
        direct = getattr(expected, kind)
        assert passage["status"] == "FOUND"
        assert passage["jd_ut"] == direct.jd_ut
        assert passage["epoch_tt"] == direct.epoch_tt
        assert passage["epoch_tdb"] == direct.epoch_tdb
        assert passage["distance_au"] == direct.distance_au
        assert payload["distance_extremes"][f"{lunar_name}_jd"] == direct.epoch_tt
        assert payload["distance_extremes"][f"{lunar_name}_distance_au"] == direct.distance_au
        epoch_tdb = passage["epoch_tdb"]
        assert 0 < sign * (epoch_tdb - expected.start_epoch_tdb) <= max_days
        distance, _ = _lunar_range_and_radial_product(reader, epoch_tdb)
        assert distance == pytest.approx(direct.distance_au, abs=1e-15, rel=0)
        _, radial_before = _lunar_range_and_radial_product(reader, epoch_tdb - 0.01)
        _, radial_after = _lunar_range_and_radial_product(reader, epoch_tdb + 0.01)
        assert radial_before * sign_after < 0 < radial_after * sign_after


def test_explicit_lunar_window_can_omit_both_passages(kernel_client):
    """Return both typed misses with null convenience values for a short search."""
    response = kernel_client.post(
        "/v1/orbits/distance-extremes",
        json={"body": "Moon", "jd_ut": 2451545.0, "center": "EARTH", "max_days": 0.01},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["distance_extremes"] == {
        "name": "Moon",
        "perigee_jd": None,
        "perigee_distance_au": None,
        "apogee_jd": None,
        "apogee_distance_au": None,
    }
    provenance = payload["provenance"]
    assert provenance["direction"] == "NEXT"
    assert provenance["pericenter"]["status"] == "NOT_IN_WINDOW"
    assert provenance["apocenter"]["status"] == "NOT_IN_WINDOW"
    start, end = provenance["search"]["searched_interval_tdb"]
    epoch_tdb = payload["time"]["epoch_tdb"]
    assert start < epoch_tdb  # The inclusive start uses a two-sided probe.
    assert end == epoch_tdb + 0.01


@pytest.mark.parametrize(
    ("route", "payload", "error_code"),
    [
        ("elements", {"body": "Mars", "center": "EARTH"}, "center_not_allowed"),
        ("distance-extremes", {"body": "Moon", "center": "SUN"}, "center_not_allowed"),
        ("elements", {"body": "Moon", "center": "EARTH", "jd_ut": 2400000.0,
                      "frame": "TRUE_ECLIPTIC_OF_DATE"}, "frame_outside_model_range"),
    ],
)
def test_strict_orbit_variants_keep_engine_admission(kernel_client, route, payload, error_code):
    """Translate unsupported centers and frame epochs using the strict engine errors."""
    response = kernel_client.post(
        f"/v1/orbits/{route}", json={"jd_ut": 2451545.0, **payload}
    )
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == error_code

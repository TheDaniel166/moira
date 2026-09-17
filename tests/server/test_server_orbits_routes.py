from __future__ import annotations

from unittest.mock import ANY

from fastapi.testclient import TestClient
import pytest

from moira._orbital_state import OrbitalStateLeg
from moira.orbits import (
    ApsidalDirection,
    ApsidalPassageOutcome,
    ApsidalPassageStatus,
    ApsidalPassages,
    ApsidalPassagesProvenance,
    ApsidalRouteScheduleEntry,
    ApsidalSegmentUsage,
    OrbitShape,
    OrbitalBodyIdentity,
    OrbitalBodyKind,
    OrbitalCenter,
    OrbitalFrame,
    OrbitalFrameConstruction,
    OrbitalGravity,
    OrbitalSingularityThresholds,
    OrbitalStateSource,
    OrbitalTimeConversion,
    OsculatingElements,
    OsculatingElementsProvenance,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeReader:
    pass


class _FakeEngine:
    def __init__(self) -> None:
        self._reader = _FakeReader()


def _strict_elements(
    body: str,
    jd_ut: float,
    *,
    semi_major_axis_au: float = 1.000001,
    eccentricity: float = 0.0167,
    inclination_deg: float = 0.0001,
    lon_ascending_node_deg: float = 174.9,
    arg_pericenter_deg: float = 288.1,
    mean_anomaly_deg: float = 357.5,
    mean_motion_deg_per_day: float = 0.9856,
    orbital_period_days: float = 365.25,
) -> OsculatingElements:
    epoch_tt = jd_ut + 64.184 / 86400.0
    epoch_tdb = epoch_tt - 8.0e-10
    state_source = OrbitalStateSource(
        legs=(
            OrbitalStateLeg(
                center_naif_id=0,
                target_naif_id=10,
                traversal_sign=-1,
                segment_type=2,
                coverage_start_tdb=2287184.5,
                coverage_end_tdb=2688976.5,
                kernel_label="de441_part-2.bsp",
                kernel_sha256="a" * 64,
                kernel_bytes=123456,
                pool_index=0,
                catalog_id=None,
                catalog_version=None,
                manifest_sha256=None,
                released_utc=None,
                planetary_ephemeris="DE441",
                coverage_restricted_to_observed_arc=None,
            ),
            OrbitalStateLeg(
                center_naif_id=0,
                target_naif_id=399,
                traversal_sign=1,
                segment_type=2,
                coverage_start_tdb=2287184.5,
                coverage_end_tdb=2688976.5,
                kernel_label="de441_part-2.bsp",
                kernel_sha256="a" * 64,
                kernel_bytes=123456,
                pool_index=0,
                catalog_id=None,
                catalog_version=None,
                manifest_sha256=None,
                released_utc=None,
                planetary_ephemeris="DE441",
                coverage_restricted_to_observed_arc=None,
            ),
        ),
        covered_intervals_tdb=((2287184.5, 2688976.5),),
        pool_generation=7,
    )
    provenance = OsculatingElementsProvenance(
        state_source=state_source,
        gravity=OrbitalGravity(
            rule="SUN_PLUS_PLANET_BODY",
            gm_km3_s2=132712838641.71492,
            component_naif_ids=(10, 399),
            component_gm_km3_s2=(132712440041.27942, 398600.43550702266),
            policy="HORIZONS_GM_2026_09_15",
            source_url="https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/gm_Horizons.pck",
            retrieved_date="2026-09-15",
            source_sha256="b" * 64,
            source_bytes=15428,
            planetary_ephemeris="DE441",
        ),
        frame_construction=OrbitalFrameConstruction(
            frame=OrbitalFrame.J2000_ECLIPTIC,
            routine="fixed J2000 x rotation",
            router_branch="fixed_j2000",
            precession_model=None,
            obliquity_model="IAU J2000 mean obliquity",
            nutation_model=None,
        ),
        frame_model_interval_tt=None,
        time_conversion=OrbitalTimeConversion(
            delta_t_policy="MOIRA_SOURCE_OWNED_DELTA_T_V1",
            delta_t_source_product="IERS_EOP",
            delta_t_retarget_mode="none",
            delta_t_correction_seconds=0.0,
            identity_iterations=2,
            tt_tdb_policy="NAIF_LSK_TT_TDB",
            tt_tdb_version="naif0012",
            tt_tdb_source_url="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
            tt_tdb_source_sha256="c" * 64,
            tt_tdb_source_bytes=5257,
            tt_tdb_iterations=2,
        ),
        singularity_thresholds=OrbitalSingularityThresholds(
            circular_e_tolerance=1.0e-10,
            equatorial_sin_i_tolerance=1.0e-10,
            parabolic_e_tolerance=1.0e-10,
            rectilinear_normalized_h_tolerance=1.0e-10,
            policy="MOIRA_OSCULATING_ELEMENTS_STAGE1_V1",
        ),
    )
    return OsculatingElements(
        body=OrbitalBodyIdentity(body, OrbitalBodyKind.PLANET_BODY, 399),
        center=OrbitalCenter.SUN,
        frame=OrbitalFrame.J2000_ECLIPTIC,
        jd_ut=jd_ut,
        epoch_tt=epoch_tt,
        epoch_tdb=epoch_tdb,
        delta_t_seconds=64.184,
        tdb_minus_tt_seconds=(epoch_tdb - epoch_tt) * 86400.0,
        shape=OrbitShape.ELLIPTIC,
        semi_major_axis_au=semi_major_axis_au,
        eccentricity=eccentricity,
        pericenter_distance_au=semi_major_axis_au * (1.0 - eccentricity),
        apocenter_distance_au=semi_major_axis_au * (1.0 + eccentricity),
        inclination_deg=inclination_deg,
        lon_ascending_node_deg=lon_ascending_node_deg,
        arg_pericenter_deg=arg_pericenter_deg,
        true_anomaly_deg=0.0,
        mean_anomaly_deg=mean_anomaly_deg,
        mean_motion_deg_per_day=mean_motion_deg_per_day,
        orbital_period_days=orbital_period_days,
        time_of_pericenter_tdb=epoch_tdb,
        time_of_pericenter_tt=epoch_tt,
        lon_pericenter_deg=103.0,
        arg_latitude_deg=288.1,
        true_longitude_deg=100.0,
        mean_longitude_deg=100.0,
        pericenter_ecliptic_lon_deg=103.0,
        pericenter_ecliptic_lat_deg=0.0,
        undefined=(),
        provenance=provenance,
    )


def _strict_passages(body: str, jd_ut: float) -> ApsidalPassages:
    elements = _strict_elements(body, jd_ut)
    source = elements.provenance.state_source
    peri_tt = 2451600.25
    aphe_tt = 2451782.75
    peri_tdb = peri_tt - 8.0e-10
    aphe_tdb = aphe_tt - 8.0e-10
    return ApsidalPassages(
        body=elements.body,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        jd_ut=jd_ut,
        start_epoch_tt=elements.epoch_tt,
        start_epoch_tdb=elements.epoch_tdb,
        pericenter=ApsidalPassageOutcome(
            status=ApsidalPassageStatus.FOUND,
            epoch_tdb=peri_tdb,
            epoch_tt=peri_tt,
            jd_ut=peri_tt - 64.184 / 86400.0,
            distance_au=0.98329,
            coverage_edge_tdb=None,
            detail="TWO_SIDED_RADIAL_VELOCITY_ROOT",
        ),
        apocenter=ApsidalPassageOutcome(
            status=ApsidalPassageStatus.FOUND,
            epoch_tdb=aphe_tdb,
            epoch_tt=aphe_tt,
            jd_ut=aphe_tt - 64.184 / 86400.0,
            distance_au=1.01671,
            coverage_edge_tdb=None,
            detail="TWO_SIDED_RADIAL_VELOCITY_ROOT",
        ),
        provenance=ApsidalPassagesProvenance(
            algorithm_version="MOIRA_APSIDAL_PASSAGES_V1",
            gravity=elements.provenance.gravity,
            time_conversion=elements.provenance.time_conversion,
            state_source=source,
            initial_period_fraction=1.0 / 256.0,
            radial_timescale_fraction=1.0 / 20.0,
            minimum_step_days=0.05,
            maximum_step_days=32.0,
            witness_root_tolerance_factor=8.0,
            witness_minimum_step_fraction=0.1,
            witness_motion_timescale_fraction=1.0e-4,
            witness_maximum_offset_days=1.0,
            refinement_tolerance_days=1.0e-8,
            maximum_root_iterations=96,
            evaluation_budget=20_000,
            extremum_semantics="two-sided local extremum",
            search_window_source="AUTO_PERIOD",
            route_plan_identity="d" * 64,
            route_schedule=(
                ApsidalRouteScheduleEntry(
                    start_tdb=source.covered_intervals_tdb[0][0],
                    end_tdb=source.covered_intervals_tdb[0][1],
                    route_identity="e" * 64,
                    legs=source.legs,
                ),
            ),
            segment_usage=tuple(
                ApsidalSegmentUsage(leg=leg, evaluations=42)
                for leg in source.legs
            ),
            seam_continuity=(),
            searched_interval_tdb=(elements.epoch_tdb, aphe_tdb),
            total_evaluations=42,
        ),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_orbital_elements_route_returns_engine_elements_and_provenance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float, object, object, object | None]] = []

    def fake_osculating_elements(
        body: str,
        jd_ut: float,
        *,
        center: object,
        frame: object,
        reader: object | None,
    ) -> OsculatingElements:
        calls.append((body, jd_ut, center, frame, reader))
        return _strict_elements(body, jd_ut)

    monkeypatch.setattr(
        "moira_server.services.orbits.osculating_elements",
        fake_osculating_elements,
    )

    response = client.post(
        "/v1/orbits/elements",
        json={"body": " Earth ", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request"] == {"body": "Earth", "jd_ut": 2451545.0}
    assert body["time"] == {
        "input_time_scale": "UT1_JD",
        "state_evaluation_scale": "TDB_JD",
        "output_time_scale": "TT_JD",
        "jd_ut": 2451545.0,
        "epoch_tt": pytest.approx(2451545.0 + 64.184 / 86400.0),
        "epoch_tdb": pytest.approx(2451545.0 + 64.184 / 86400.0 - 8.0e-10),
        "delta_t_seconds": 64.184,
        "tdb_minus_tt_seconds": pytest.approx(-8.046627044677734e-05),
        "conversion": {
            "delta_t_policy": "MOIRA_SOURCE_OWNED_DELTA_T_V1",
            "delta_t_source_product": "IERS_EOP",
            "delta_t_retarget_mode": "none",
            "delta_t_correction_seconds": 0.0,
            "identity_iterations": 2,
            "tt_tdb_policy": "NAIF_LSK_TT_TDB",
            "tt_tdb_version": "naif0012",
            "tt_tdb_source_url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
            "tt_tdb_source_sha256": "c" * 64,
            "tt_tdb_source_bytes": 5257,
            "tt_tdb_iterations": 2,
        },
    }
    assert body["elements"] == {
        "name": "Earth",
        "epoch_jd": pytest.approx(2451545.0 + 64.184 / 86400.0),
        "semi_major_axis_au": 1.000001,
        "eccentricity": 0.0167,
        "inclination_deg": 0.0001,
        "lon_ascending_node_deg": 174.9,
        "arg_perihelion_deg": 288.1,
        "mean_anomaly_deg": 357.5,
        "mean_motion_deg_per_day": 0.9856,
        "orbital_period_days": 365.25,
        "perihelion_distance_au": pytest.approx(0.9833009833),
        "aphelion_distance_au": pytest.approx(1.0167010167),
    }
    provenance = body["provenance"]
    assert provenance["source_module"] == "moira.orbits"
    assert provenance["engine_entrypoint"] == "osculating_elements"
    assert provenance["reader_owner"] == "Moira engine instance"
    assert provenance["center"] == "SUN"
    assert provenance["frame"] == "J2000_ECLIPTIC"
    assert provenance["element_type"] == "osculating"
    assert provenance["state_source"]["legs"][0]["kernel_label"] == "de441_part-2.bsp"
    assert provenance["state_source"]["legs"][0]["traversal_sign"] == -1
    assert provenance["state_source"]["covered_intervals_tdb"] == [
        [2287184.5, 2688976.5]
    ]
    assert provenance["gravity"]["rule"] == "SUN_PLUS_PLANET_BODY"
    assert provenance["gravity"]["units"] == "km^3/s^2"
    assert provenance["gravity"]["planetary_ephemeris"] == "DE441"
    assert provenance["frame_construction"]["router_branch"] == "fixed_j2000"
    assert provenance["apparent_corrections"] == "not_applied"
    assert provenance["light_time_correction"] == "not_applied"
    assert provenance["mean_element_table"] == "not_used"
    assert provenance["stage_sequence"] == [
        "input_validation",
        "reader_binding",
        "ut1_tt_tdb_binding",
        "source_and_gravity_binding",
        "state_evaluation",
        "frame_rotation",
        "element_extraction",
        "transport_serialization",
    ]
    assert calls == [
        (
            "Earth",
            2451545.0,
            OrbitalCenter.SUN,
            OrbitalFrame.J2000_ECLIPTIC,
            ANY,
        )
    ]
    assert calls[0][4] is not None
    assert "C:\\" not in response.text


def test_orbital_elements_route_handles_outer_planet(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_osculating_elements(
        body: str,
        jd_ut: float,
        *,
        center: object,
        frame: object,
        reader: object | None,
    ) -> OsculatingElements:
        return _strict_elements(
            body,
            jd_ut,
            semi_major_axis_au=5.2,
            eccentricity=0.049,
            inclination_deg=1.3,
            lon_ascending_node_deg=100.5,
            arg_pericenter_deg=273.8,
            mean_anomaly_deg=20.0,
            mean_motion_deg_per_day=0.083,
            orbital_period_days=4332.6,
        )

    monkeypatch.setattr(
        "moira_server.services.orbits.osculating_elements",
        fake_osculating_elements,
    )

    response = client.post(
        "/v1/orbits/elements",
        json={"body": "Jupiter", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["elements"]["name"] == "Jupiter"
    assert body["elements"]["semi_major_axis_au"] == 5.2
    assert body["elements"]["perihelion_distance_au"] == pytest.approx(4.9452)
    assert body["elements"]["aphelion_distance_au"] == pytest.approx(5.4548)


def test_distance_extremes_route_returns_tt_extremes_and_search_provenance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float, object | None]] = []

    def fake_apsidal_passages(
        body: str,
        jd_ut: float,
        *,
        center: object,
        direction: object,
        reader: object | None,
    ) -> ApsidalPassages:
        calls.append((body, jd_ut, reader))
        assert center is OrbitalCenter.SUN
        assert direction is ApsidalDirection.NEXT
        return _strict_passages(body, jd_ut)

    monkeypatch.setattr(
        "moira_server.services.orbits.apsidal_passages",
        fake_apsidal_passages,
    )

    response = client.post(
        "/v1/orbits/distance-extremes",
        json={"body": "Venus", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request"] == {"body": "Venus", "jd_ut": 2451545.0}
    assert body["distance_extremes"] == {
        "name": "Venus",
        "perihelion_jd": 2451600.25,
        "perihelion_distance_au": 0.98329,
        "aphelion_jd": 2451782.75,
        "aphelion_distance_au": 1.01671,
    }
    assert body["time"]["input_time_scale"] == "UT1_JD"
    assert body["time"]["state_evaluation_scale"] == "TDB_JD"
    assert body["time"]["output_time_scale"] == "TT_JD"
    assert body["time"]["epoch_tdb"] != body["time"]["epoch_tt"]
    provenance = body["provenance"]
    assert provenance["engine_entrypoint"] == "apsidal_passages"
    assert provenance["center"] == "SUN"
    assert provenance["direction"] == "NEXT"
    assert provenance["pericenter"]["status"] == "FOUND"
    assert provenance["apocenter"]["status"] == "FOUND"
    assert provenance["search"]["algorithm_version"] == "MOIRA_APSIDAL_PASSAGES_V1"
    assert provenance["search"]["gravity"]["units"] == "km^3/s^2"
    assert provenance["search"]["state_source"]["legs"]
    assert provenance["search"]["route_plan_identity"] == "d" * 64
    assert provenance["stage_sequence"] == [
        "input_validation",
        "reader_binding",
        "ut1_tt_tdb_binding",
        "frozen_route_plan",
        "radial_velocity_search",
        "two_sided_extremum_witness",
        "tdb_tt_ut1_event_inversion",
        "distance_extrema_serialization",
        "provenance_serialization",
    ]
    assert calls == [("Venus", 2451545.0, ANY)]
    assert calls[0][2] is not None


@pytest.mark.parametrize(
    ("payload", "message_fragment"),
    [
        ({"body": "Sun", "jd_ut": 2451545.0}, "body must be one of"),
        ({"body": "Moon", "jd_ut": 2451545.0}, "body must be one of"),
        ({"body": "Ceres", "jd_ut": 2451545.0}, "body must be one of"),
        ({"body": " ", "jd_ut": 2451545.0}, "body must be non-empty"),
        ({"body": "Earth", "jd_ut": "NaN"}, "jd_ut must be finite"),
    ],
)
def test_orbits_routes_reject_invalid_inputs(
    client: TestClient,
    payload: dict[str, object],
    message_fragment: str,
) -> None:
    elements = client.post("/v1/orbits/elements", json=payload)
    extremes = client.post("/v1/orbits/distance-extremes", json=payload)

    assert elements.status_code == 422
    assert extremes.status_code == 422
    assert message_fragment in elements.json()["message"]
    assert message_fragment in extremes.json()["message"]


def test_orbits_routes_reject_extra_fields(client: TestClient) -> None:
    elements = client.post(
        "/v1/orbits/elements",
        json={"body": "Earth", "jd_ut": 2451545.0, "frame": "mean"},
    )
    extremes = client.post(
        "/v1/orbits/distance-extremes",
        json={"body": "Earth", "jd_ut": 2451545.0, "frame": "mean"},
    )

    assert elements.status_code == 422
    assert extremes.status_code == 422


def test_orbits_get_is_not_admitted(client: TestClient) -> None:
    assert client.get("/v1/orbits/elements").status_code == 405
    assert client.get("/v1/orbits/distance-extremes").status_code == 405

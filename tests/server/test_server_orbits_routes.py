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
    OrbitClassBatchItem,
    OrbitClassBatchResult,
    OrbitClassBoundaryMargin,
    OrbitClassCode,
    OrbitClassPredicate,
    OrbitClassResult,
    OrbitalBodyIdentity,
    OrbitalBodyKind,
    OrbitalBodyNotSupportedError,
    OrbitalCenter,
    OrbitalErrorReceipt,
    OrbitalFrame,
    OrbitalFrameConstruction,
    OrbitalGravity,
    OrbitalSingularityThresholds,
    OrbitalStateSource,
    OrbitalTimeConversion,
    OrbitShape,
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
    semi_major_axis_au: float | None = 1.000001,
    eccentricity: float = 0.0167,
    inclination_deg: float = 0.0001,
    lon_ascending_node_deg: float = 174.9,
    arg_pericenter_deg: float = 288.1,
    mean_anomaly_deg: float | None = 357.5,
    mean_motion_deg_per_day: float | None = 0.9856,
    orbital_period_days: float | None = 365.25,
    pericenter_distance_au: float | None = None,
    apocenter_distance_au: float | None = None,
    shape: OrbitShape = OrbitShape.ELLIPTIC,
    body_kind: OrbitalBodyKind = OrbitalBodyKind.PLANET_BODY,
    naif_id: int = 399,
) -> OsculatingElements:
    if pericenter_distance_au is None:
        if semi_major_axis_au is not None:
            pericenter_distance_au = semi_major_axis_au * (1.0 - eccentricity)
        else:
            pericenter_distance_au = 0.9833009833
    if apocenter_distance_au is None:
        if shape == OrbitShape.ELLIPTIC and semi_major_axis_au is not None:
            apocenter_distance_au = semi_major_axis_au * (1.0 + eccentricity)
        else:
            apocenter_distance_au = None
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
        body=OrbitalBodyIdentity(body, body_kind, naif_id),
        center=OrbitalCenter.SUN,
        frame=OrbitalFrame.J2000_ECLIPTIC,
        jd_ut=jd_ut,
        epoch_tt=epoch_tt,
        epoch_tdb=epoch_tdb,
        delta_t_seconds=64.184,
        tdb_minus_tt_seconds=(epoch_tdb - epoch_tt) * 86400.0,
        shape=shape,
        semi_major_axis_au=semi_major_axis_au,
        eccentricity=eccentricity,
        pericenter_distance_au=pericenter_distance_au,
        apocenter_distance_au=apocenter_distance_au,
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


def _strict_orbit_class(
    body: str,
    jd_ut: float,
    *,
    code: OrbitClassCode = OrbitClassCode.MBA,
    title: str = "Main-belt Asteroid",
) -> OrbitClassResult:
    elements = _strict_elements(
        body,
        jd_ut,
        semi_major_axis_au=2.77,
        eccentricity=0.08,
        pericenter_distance_au=2.5484,
        apocenter_distance_au=2.9916,
        body_kind=OrbitalBodyKind.ASTEROID,
        naif_id=2000001,
    )
    return OrbitClassResult(
        body=OrbitalBodyIdentity(name=body, kind=OrbitalBodyKind.ASTEROID, naif_id=2000001),
        epoch_tdb=elements.epoch_tdb,
        elements=elements,
        code=code,
        title=title,
        classification_policy="jpl_sbdb_osculating_v1",
        predicates=(
            OrbitClassPredicate(
                code=code,
                conditions=(
                    OrbitClassBoundaryMargin("a", 2.77, ">", 2.0, 0.77, "AU"),
                    OrbitClassBoundaryMargin("a", 2.77, "<", 3.2, -0.43, "AU"),
                    OrbitClassBoundaryMargin("q", 2.55, ">", 1.666, 0.884, "AU"),
                ),
                matched=True,
            ),
        ),
        boundary_margins=(
            OrbitClassBoundaryMargin("a", 2.77, ">", 2.0, 0.77, "AU"),
            OrbitClassBoundaryMargin("a", 2.77, "<", 3.2, -0.43, "AU"),
            OrbitClassBoundaryMargin("q", 2.55, ">", 1.666, 0.884, "AU"),
        ),
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
        ({"body": "Sun", "jd_ut": 2451545.0}, "not an orbital target"),
        ({"body": "Moon", "jd_ut": 2451545.0}, "center 'SUN' is not allowed for 'Moon'"),
        ({"body": " ", "jd_ut": 2451545.0}, "body must be non-empty"),
        ({"body": "Earth", "jd_ut": "NaN"}, "jd_ut must be finite"),
        ({"body": "Earth", "jd_ut": True}, "jd_ut must be a real number"),
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
    orbit_class_res = client.post(
        "/v1/orbits/class",
        json={"body": "Ceres", "jd_ut": 2451545.0, "extra": "invalid"},
    )
    orbit_class_batch_res = client.post(
        "/v1/orbits/class/batch",
        json={"bodies": ["Ceres"], "jd_ut": 2451545.0, "extra": "invalid"},
    )

    assert elements.status_code == 422
    assert extremes.status_code == 422
    assert orbit_class_res.status_code == 422
    assert orbit_class_batch_res.status_code == 422


def test_orbits_get_is_not_admitted(client: TestClient) -> None:
    assert client.get("/v1/orbits/elements").status_code == 405
    assert client.get("/v1/orbits/distance-extremes").status_code == 405
    assert client.get("/v1/orbits/class").status_code == 405
    assert client.get("/v1/orbits/class/batch").status_code == 405


def test_orbital_elements_route_admits_small_bodies(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float]] = []

    def fake_osculating_elements(
        body: str,
        jd_ut: float,
        *,
        center: object,
        frame: object,
        reader: object | None,
    ) -> OsculatingElements:
        calls.append((body, jd_ut))
        if body == "Ceres":
            return _strict_elements(
                body,
                jd_ut,
                semi_major_axis_au=2.767,
                eccentricity=0.078,
                inclination_deg=10.59,
                lon_ascending_node_deg=80.3,
                arg_pericenter_deg=73.5,
                mean_anomaly_deg=95.4,
                mean_motion_deg_per_day=0.214,
                orbital_period_days=1682.0,
                pericenter_distance_au=2.551,
                apocenter_distance_au=2.983,
                body_kind=OrbitalBodyKind.ASTEROID,
                naif_id=2000001,
            )
        # Hyperbolic trajectory (e.g. 1I/'Oumuamua)
        return _strict_elements(
            body,
            jd_ut,
            semi_major_axis_au=None,
            eccentricity=1.20,
            inclination_deg=122.6,
            lon_ascending_node_deg=24.6,
            arg_pericenter_deg=241.7,
            mean_anomaly_deg=None,
            mean_motion_deg_per_day=None,
            orbital_period_days=None,
            pericenter_distance_au=0.255,
            apocenter_distance_au=None,
            shape=OrbitShape.HYPERBOLIC,
            body_kind=OrbitalBodyKind.COMET,
            naif_id=1003507,
        )

    monkeypatch.setattr(
        "moira_server.services.orbits.osculating_elements",
        fake_osculating_elements,
    )

    # 1. Closed elliptic asteroid: Ceres
    res_ceres = client.post("/v1/orbits/elements", json={"body": "Ceres", "jd_ut": 2451545.0})
    assert res_ceres.status_code == 200
    body_ceres = res_ceres.json()
    assert body_ceres["request"] == {"body": "Ceres", "jd_ut": 2451545.0}
    assert body_ceres["elements"]["name"] == "Ceres"
    assert body_ceres["elements"]["semi_major_axis_au"] == 2.767
    assert body_ceres["elements"]["eccentricity"] == 0.078
    assert body_ceres["elements"]["aphelion_distance_au"] == 2.983

    # 2. Hyperbolic small body: open conic with nullable fields
    res_hyper = client.post("/v1/orbits/elements", json={"body": "'Oumuamua", "jd_ut": 2451545.0})
    assert res_hyper.status_code == 200
    body_hyper = res_hyper.json()
    assert body_hyper["elements"]["semi_major_axis_au"] is None
    assert body_hyper["elements"]["aphelion_distance_au"] is None
    assert body_hyper["elements"]["orbital_period_days"] is None
    assert body_hyper["elements"]["mean_anomaly_deg"] is None
    assert body_hyper["elements"]["mean_motion_deg_per_day"] is None
    assert body_hyper["elements"]["eccentricity"] == 1.20


def test_distance_extremes_route_admits_small_bodies(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_apsidal_passages(
        body: str,
        jd_ut: float,
        *,
        center: object,
        direction: object,
        reader: object | None,
    ) -> ApsidalPassages:
        if body == "Ceres":
            return _strict_passages(body, jd_ut)
        # Simulate open conic or unavailable passage
        passages = _strict_passages(body, jd_ut)
        unavailable_apocenter = ApsidalPassageOutcome(
            status=ApsidalPassageStatus.NOT_IN_WINDOW,
            epoch_tdb=None,
            epoch_tt=None,
            jd_ut=None,
            distance_au=None,
            coverage_edge_tdb=None,
            detail="OPEN_CONIC_HAS_NO_APOCENTER",
        )
        object.__setattr__(passages, "apocenter", unavailable_apocenter)
        return passages

    monkeypatch.setattr(
        "moira_server.services.orbits.apsidal_passages",
        fake_apsidal_passages,
    )

    # 1. Closed asteroid returns 200 with extrema
    res_ceres = client.post("/v1/orbits/distance-extremes", json={"body": "Ceres", "jd_ut": 2451545.0})
    assert res_ceres.status_code == 200
    data_ceres = res_ceres.json()
    assert data_ceres["distance_extremes"]["name"] == "Ceres"
    assert data_ceres["distance_extremes"]["perihelion_distance_au"] == 0.98329
    assert data_ceres["distance_extremes"]["aphelion_distance_au"] == 1.01671

    # 2. Unavailable passage raises OrbitalPassageUnavailableError mapped to 422
    res_comet = client.post("/v1/orbits/distance-extremes", json={"body": "HyperbolicComet", "jd_ut": 2451545.0})
    assert res_comet.status_code == 422
    err = res_comet.json()
    assert err["category"] == "orbital_event_availability"


def test_orbit_class_route_returns_sbdb_classification(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float]] = []

    def fake_orbit_class(
        body: str,
        jd_ut: float,
        *,
        reader: object | None = None,
    ) -> OrbitClassResult:
        calls.append((body, jd_ut))
        if body == "Ceres":
            return _strict_orbit_class(body, jd_ut, code=OrbitClassCode.MBA, title="Main-belt Asteroid")
        if body == "Chiron":
            return _strict_orbit_class(body, jd_ut, code=OrbitClassCode.CEN, title="Centaur")
        if body == "Eros":
            return _strict_orbit_class(body, jd_ut, code=OrbitClassCode.AMO, title="Amor")
        raise OrbitalBodyNotSupportedError(body, "planet", "orbit_class admits small bodies only")

    monkeypatch.setattr("moira_server.services.orbits.orbit_class", fake_orbit_class)

    # 1. Ceres (MBA)
    res_ceres = client.post("/v1/orbits/class", json={"body": "Ceres", "jd_ut": 2451545.0})
    assert res_ceres.status_code == 200
    data_ceres = res_ceres.json()
    assert data_ceres["request"] == {"body": "Ceres", "jd_ut": 2451545.0}
    assert data_ceres["orbit_class"]["name"] == "Ceres"
    assert data_ceres["orbit_class"]["code"] == "MBA"
    assert data_ceres["orbit_class"]["title"] == "Main-belt Asteroid"
    assert "Main-belt asteroid" in data_ceres["orbit_class"]["description"]
    assert data_ceres["orbit_class"]["is_near_earth_asteroid"] is False
    assert len(data_ceres["orbit_class"]["predicates"]) == 3
    assert data_ceres["orbit_class"]["predicates"][0]["parameter"] == "a"
    assert data_ceres["orbit_class"]["predicates"][0]["operator"] == ">"
    assert data_ceres["orbit_class"]["predicates"][0]["boundary"] == 2.0
    assert data_ceres["orbit_class"]["predicates"][0]["satisfied"] is True
    assert data_ceres["provenance"]["classification_policy"] == "jpl_sbdb_osculating_v1"

    # 2. Chiron (CEN)
    res_chiron = client.post("/v1/orbits/class", json={"body": "Chiron", "jd_ut": 2451545.0})
    assert res_chiron.status_code == 200
    assert res_chiron.json()["orbit_class"]["code"] == "CEN"

    # 3. Eros (AMO - Near Earth Asteroid)
    res_eros = client.post("/v1/orbits/class", json={"body": "Eros", "jd_ut": 2451545.0})
    assert res_eros.status_code == 200
    data_eros = res_eros.json()
    assert data_eros["orbit_class"]["code"] == "AMO"
    assert data_eros["orbit_class"]["is_near_earth_asteroid"] is True

    # 4. Non-small-body (e.g. Jupiter)
    res_jup = client.post("/v1/orbits/class", json={"body": "Jupiter", "jd_ut": 2451545.0})
    assert res_jup.status_code == 422


def test_orbit_class_batch_route_evaluates_and_isolates_errors(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_orbit_classes_at(
        bodies: list[str],
        jd_ut: float,
        *,
        reader: object | None = None,
    ) -> OrbitClassBatchResult:
        items = []
        for i, body in enumerate(bodies):
            if body == "Ceres":
                items.append(
                    OrbitClassBatchItem(
                        input_index=i,
                        input_body=body,
                        result=_strict_orbit_class(body, jd_ut, code=OrbitClassCode.MBA, title="Main-belt Asteroid"),
                        error=None,
                    )
                )
            elif body == "Chiron":
                items.append(
                    OrbitClassBatchItem(
                        input_index=i,
                        input_body=body,
                        result=_strict_orbit_class(body, jd_ut, code=OrbitClassCode.CEN, title="Centaur"),
                        error=None,
                    )
                )
            else:
                items.append(
                    OrbitClassBatchItem(
                        input_index=i,
                        input_body=body,
                        result=None,
                        error=OrbitalErrorReceipt(
                            error_code="ORBITAL_BODY_NOT_FOUND",
                            message=f"unknown small body: {body}",
                            details=(("body", body),),
                        ),
                    )
                )
        return OrbitClassBatchResult(epoch_tdb=2451545.0, items=tuple(items))

    monkeypatch.setattr("moira_server.services.orbits.orbit_classes_at", fake_orbit_classes_at)

    response = client.post(
        "/v1/orbits/class/batch",
        json={"bodies": ["Ceres", "Chiron", "UnknownBody123"], "jd_ut": 2451545.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request"] == {"bodies_count": 3, "jd_ut": 2451545.0}
    assert data["total_requested"] == 3
    assert data["total_succeeded"] == 2
    assert data["total_failed"] == 1
    assert "Ceres" in data["results"]
    assert data["results"]["Ceres"]["code"] == "MBA"
    assert "Chiron" in data["results"]
    assert data["results"]["Chiron"]["code"] == "CEN"
    assert "UnknownBody123" in data["errors"]
    assert data["errors"]["UnknownBody123"]["error_code"] == "ORBITAL_BODY_NOT_FOUND"
    assert data["provenance"]["classification_policy"] == "jpl_sbdb_osculating_v1"

    # Batch request with empty bodies list is rejected
    res_empty = client.post("/v1/orbits/class/batch", json={"bodies": [], "jd_ut": 2451545.0})
    assert res_empty.status_code == 422


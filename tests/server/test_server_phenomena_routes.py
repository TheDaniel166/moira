from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.eclipse import EclipseCalculator, next_solar_eclipse_at_location
from moira.heliacal import HeliacalEventKind, visibility_event
from moira.occultations import (
    all_lunar_occultations,
    close_approaches,
    lunar_occultation_path_at,
    lunar_star_occultation,
    lunar_star_occultation_path_at,
)
from moira.parans import (
    analyze_paran_field,
    analyze_paran_field_structure,
    consolidate_paran_contours,
    evaluate_paran_site,
    extract_paran_field_contours,
    find_parans,
    natal_parans,
    sample_paran_field,
)
from moira.rise_set import RiseSetPolicy, find_phenomena, get_transit, twilight_times
from moira.spk_reader import use_reader_override
from moira.stations import is_retrograde, next_station
from moira.void_of_course import next_void_of_course, void_of_course_window, void_periods_in_range
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


@pytest.mark.requires_ephemeris
def test_station_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct_stations = moira_engine.stations("Mercury", 2451545.0, 2451545.0 + 365.25)
    direct_next = next_station("Mercury", 2451545.0, reader=getattr(moira_engine, "_reader", None))
    direct_periods = moira_engine.retrograde_periods("Mercury", 2451545.0, 2451545.0 + 365.25)
    midpoint = (direct_periods[0][0] + direct_periods[0][1]) / 2.0
    direct_state = is_retrograde(
        "Mercury",
        midpoint,
        reader=getattr(moira_engine, "_reader", None),
    )

    search_response = client_with_engine.post(
        "/v1/stations/search",
        json={"body": "Mercury", "jd_start": 2451545.0, "jd_end": 2451545.0 + 365.25},
    )
    next_response = client_with_engine.post(
        "/v1/stations/next",
        json={"body": "Mercury", "jd_start": 2451545.0},
    )
    periods_response = client_with_engine.post(
        "/v1/stations/retrograde-periods",
        json={"body": "Mercury", "jd_start": 2451545.0, "jd_end": 2451545.0 + 365.25},
    )
    state_response = client_with_engine.post(
        "/v1/stations/is-retrograde",
        json={"body": "Mercury", "jd_ut": midpoint},
    )

    assert search_response.status_code == 200
    search_body = search_response.json()
    assert len(search_body["events"]) == len(direct_stations)
    assert search_body["events"][0]["station_type"] == direct_stations[0].station_type
    assert search_body["events"][0]["jd_ut"] == pytest.approx(direct_stations[0].jd_ut)

    assert next_response.status_code == 200
    next_body = next_response.json()
    assert next_body["body"] == direct_next.body
    assert next_body["jd_ut"] == pytest.approx(direct_next.jd_ut)

    assert periods_response.status_code == 200
    periods_body = periods_response.json()
    assert len(periods_body["periods"]) == len(direct_periods)
    assert periods_body["periods"][0]["start"]["jd_ut"] == pytest.approx(direct_periods[0][0])
    assert periods_body["periods"][0]["end"]["jd_ut"] == pytest.approx(direct_periods[0][1])

    assert state_response.status_code == 200
    assert state_response.json()["is_retrograde"] is direct_state


@pytest.mark.requires_ephemeris
def test_void_of_course_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct_window = void_of_course_window(2451545.0, reader=getattr(moira_engine, "_reader", None))
    direct_next = next_void_of_course(2451545.0, reader=getattr(moira_engine, "_reader", None))
    direct_range = void_periods_in_range(
        2451545.0,
        2451545.0 + 20.0,
        reader=getattr(moira_engine, "_reader", None),
    )

    window_response = client_with_engine.post(
        "/v1/void-of-course/window",
        json={"jd_ut": 2451545.0},
    )
    next_response = client_with_engine.post(
        "/v1/void-of-course/next",
        json={"jd_ut": 2451545.0},
    )
    range_response = client_with_engine.post(
        "/v1/void-of-course/range",
        json={"jd_start": 2451545.0, "jd_end": 2451545.0 + 20.0},
    )
    state_response = client_with_engine.post(
        "/v1/void-of-course/is-active",
        json={"jd_ut": 2451545.0},
    )

    assert window_response.status_code == 200
    window_body = window_response.json()
    assert window_body["moon_sign"] == direct_window.moon_sign
    assert window_body["jd_voc_start"] == pytest.approx(direct_window.jd_voc_start)
    assert window_body["jd_voc_end"] == pytest.approx(direct_window.jd_voc_end)

    assert next_response.status_code == 200
    next_body = next_response.json()
    assert next_body["jd_voc_start"] == pytest.approx(direct_next.jd_voc_start)
    assert next_body["moon_sign_next"] == direct_next.moon_sign_next

    assert range_response.status_code == 200
    range_body = range_response.json()
    assert len(range_body["windows"]) == len(direct_range)
    assert range_body["windows"][0]["jd_voc_start"] == pytest.approx(direct_range[0].jd_voc_start)

    assert state_response.status_code == 200
    assert state_response.json()["is_void_of_course"] is (
        direct_window.jd_voc_start <= 2451545.0 <= direct_window.jd_voc_end
    )


@pytest.mark.requires_ephemeris
def test_rise_set_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    reader = getattr(moira_engine, "_reader", None)
    policy = RiseSetPolicy(disc_reference="center", refraction=False)
    jd_day = 2451544.5
    with use_reader_override(reader):
        direct_events = find_phenomena("Sun", jd_day, 0.0, 0.0, policy=policy)
        direct_transit = get_transit("Sun", jd_day, 0.0, 0.0, upper=True)
        direct_twilight = twilight_times(jd_day, 0.0, 0.0)

    phenomena_response = client_with_engine.post(
        "/v1/rise-set/phenomena",
        json={
            "body": "Sun",
            "jd_start": jd_day,
            "lat": 0.0,
            "lon": 0.0,
            "policy": {"disc_reference": "center", "refraction": False},
        },
    )
    transit_response = client_with_engine.post(
        "/v1/rise-set/transit",
        json={"body": "Sun", "jd_day": jd_day, "lat": 0.0, "lon": 0.0, "upper": True},
    )
    twilight_response = client_with_engine.post(
        "/v1/rise-set/twilight",
        json={"jd_day": jd_day, "lat": 0.0, "lon": 0.0},
    )

    assert phenomena_response.status_code == 200
    phenomena_body = phenomena_response.json()
    assert phenomena_body["rise"]["jd_ut"] == pytest.approx(direct_events["Rise"])
    assert phenomena_body["set"]["jd_ut"] == pytest.approx(direct_events["Set"])
    assert phenomena_body["transit"]["jd_ut"] == pytest.approx(direct_events["Transit"])

    assert transit_response.status_code == 200
    assert transit_response.json()["jd_ut"] == pytest.approx(direct_transit)

    assert twilight_response.status_code == 200
    twilight_body = twilight_response.json()
    assert twilight_body["sunrise"]["jd_ut"] == pytest.approx(direct_twilight.sunrise)
    assert twilight_body["sunset"]["jd_ut"] == pytest.approx(direct_twilight.sunset)
    assert twilight_body["astronomical_dawn"]["jd_ut"] == pytest.approx(
        direct_twilight.astronomical_dawn
    )


def test_phase_six_routes_reject_invalid_windows_bodies_and_coordinates(
    client_with_engine: TestClient,
) -> None:
    invalid_body = client_with_engine.post(
        "/v1/stations/search",
        json={"body": "NotAPlanet", "jd_start": 2451545.0, "jd_end": 2451545.0 + 10.0},
    )
    reversed_window = client_with_engine.post(
        "/v1/void-of-course/range",
        json={"jd_start": 2451545.0 + 10.0, "jd_end": 2451545.0},
    )
    invalid_lat = client_with_engine.post(
        "/v1/rise-set/phenomena",
        json={"body": "Sun", "jd_start": 2451545.0, "lat": 95.0, "lon": 0.0},
    )

    assert invalid_body.status_code == 422
    assert invalid_body.json()["error_code"] == "validation_error"
    assert "NotAPlanet" in invalid_body.json()["message"]

    assert reversed_window.status_code == 422
    assert reversed_window.json()["error_code"] == "validation_error"
    assert "jd_end" in reversed_window.json()["message"]

    assert invalid_lat.status_code == 422
    assert invalid_lat.json()["error_code"] == "validation_error"
    assert "lat" in invalid_lat.json()["message"]


@pytest.mark.requires_ephemeris
def test_eclipse_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    reader = getattr(moira_engine, "_reader", None)
    calc = EclipseCalculator(reader=reader)
    direct_solar = calc.next_solar_eclipse(2451545.0)
    direct_lunar = calc.next_lunar_eclipse(2451545.0)
    direct_solar_local = next_solar_eclipse_at_location(
        2451545.0,
        0.0,
        0.0,
        reader=reader,
    )
    direct_lunar_local = calc.lunar_local_circumstances(2451545.0, 0.0, 0.0)

    solar_response = client_with_engine.post(
        "/v1/eclipses/solar/next",
        json={"jd_start": 2451545.0},
    )
    lunar_response = client_with_engine.post(
        "/v1/eclipses/lunar/next",
        json={"jd_start": 2451545.0},
    )
    solar_local_response = client_with_engine.post(
        "/v1/eclipses/solar/local-visible",
        json={"jd_start": 2451545.0, "latitude": 0.0, "longitude": 0.0},
    )
    lunar_local_response = client_with_engine.post(
        "/v1/eclipses/lunar/local",
        json={"jd_start": 2451545.0, "latitude": 0.0, "longitude": 0.0},
    )

    assert solar_response.status_code == 200
    solar_body = solar_response.json()
    assert solar_body["jd_ut"] == pytest.approx(direct_solar.jd_ut)
    assert solar_body["data"]["eclipse_type"] == str(direct_solar.data.eclipse_type)

    assert lunar_response.status_code == 200
    lunar_body = lunar_response.json()
    assert lunar_body["jd_ut"] == pytest.approx(direct_lunar.jd_ut)
    assert lunar_body["data"]["is_lunar_eclipse"] is direct_lunar.data.is_lunar_eclipse

    assert solar_local_response.status_code == 200
    solar_local_body = solar_local_response.json()
    assert solar_local_body["event"]["jd_ut"] == pytest.approx(direct_solar_local.event.jd_ut)
    assert solar_local_body["topocentric_overlap"] is direct_solar_local.topocentric_overlap

    assert lunar_local_response.status_code == 200
    lunar_local_body = lunar_local_response.json()
    assert lunar_local_body["event"]["jd_ut"] == pytest.approx(direct_lunar_local.analysis.event.jd_ut)
    assert lunar_local_body["greatest"]["visible"] is direct_lunar_local.greatest.visible


@pytest.mark.requires_ephemeris
def test_occultation_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    reader = getattr(moira_engine, "_reader", None)
    direct_close = close_approaches("Venus", "Jupiter", 2451545.0, 2451545.0 + 120.0, reader=reader)
    direct_all = all_lunar_occultations(2451545.0, 2451545.0 + 120.0, reader=reader)
    direct_star = lunar_star_occultation(
        203.835,
        -2.397,
        "Spica",
        2451545.0,
        2451545.0 + 120.0,
        reader=reader,
    )

    close_response = client_with_engine.post(
        "/v1/occultations/close-approaches",
        json={
            "body1": "Venus",
            "body2": "Jupiter",
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 120.0,
        },
    )
    all_response = client_with_engine.post(
        "/v1/occultations/all-lunar",
        json={"jd_start": 2451545.0, "jd_end": 2451545.0 + 120.0},
    )
    star_response = client_with_engine.post(
        "/v1/occultations/lunar-star",
        json={
            "star_lon": 203.835,
            "star_lat": -2.397,
            "star_name": "Spica",
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 120.0,
        },
    )

    assert close_response.status_code == 200
    close_body = close_response.json()
    assert len(close_body["events"]) == len(direct_close)
    if direct_close:
        assert close_body["events"][0]["jd_ut"] == pytest.approx(direct_close[0].jd_ut)
        assert close_body["events"][0]["is_occultation"] is direct_close[0].is_occultation

    assert all_response.status_code == 200
    all_body = all_response.json()
    assert len(all_body["events"]) == len(direct_all)
    if direct_all:
        assert all_body["events"][0]["jd_ingress"] == pytest.approx(direct_all[0].jd_ingress)

    assert star_response.status_code == 200
    star_body = star_response.json()
    assert len(star_body["events"]) == len(direct_star)


@pytest.mark.requires_ephemeris
def test_heliacal_and_paran_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    reader = getattr(moira_engine, "_reader", None)
    with use_reader_override(reader):
        direct_visibility = visibility_event(
            "Venus",
            HeliacalEventKind.HELIACAL_RISING,
            2451545.0,
            0.0,
            0.0,
        )
        direct_parans = find_parans(["Sun", "Moon", "Mars"], 2451544.5, 51.5, 0.0, orb_minutes=10.0)
        direct_natal_parans = natal_parans(["Sun", "Moon", "Mars"], 2451545.0, 51.5, 0.0, orb_minutes=10.0)

    planet_response = client_with_engine.post(
        "/v1/heliacal/planet",
        json={
            "body": "Venus",
            "kind": "heliacal_rising",
            "jd_start": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
        },
    )
    general_response = client_with_engine.post(
        "/v1/heliacal/visibility-event",
        json={
            "body": "Venus",
            "kind": "heliacal_rising",
            "jd_start": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
        },
    )
    paran_response = client_with_engine.post(
        "/v1/parans/search",
        json={
            "bodies": ["Sun", "Moon", "Mars"],
            "jd_day": 2451544.5,
            "lat": 51.5,
            "lon": 0.0,
            "orb_minutes": 10.0,
        },
    )
    natal_paran_response = client_with_engine.post(
        "/v1/parans/natal",
        json={
            "bodies": ["Sun", "Moon", "Mars"],
            "natal_jd": 2451545.0,
            "lat": 51.5,
            "lon": 0.0,
            "orb_minutes": 10.0,
        },
    )

    assert planet_response.status_code == 200
    if direct_visibility is not None:
        planet_body = planet_response.json()
        assert planet_body["jd_ut"] == pytest.approx(direct_visibility.jd_ut)
        assert planet_body["body"] == direct_visibility.body
    else:
        assert planet_response.json() is None

    assert general_response.status_code == 200
    if direct_visibility is not None:
        general_body = general_response.json()
        assert general_body["jd_ut"] == pytest.approx(direct_visibility.jd_ut)
        assert general_body["target_kind"] == direct_visibility.target_kind.value
    else:
        assert general_response.json() is None

    assert paran_response.status_code == 200
    paran_body = paran_response.json()
    assert len(paran_body["events"]) == len(direct_parans)

    assert natal_paran_response.status_code == 200
    natal_paran_body = natal_paran_response.json()
    assert len(natal_paran_body["events"]) == len(direct_natal_parans)


@pytest.mark.requires_ephemeris
def test_phase_six_path_and_field_routes_match_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    reader = getattr(moira_engine, "_reader", None)
    calc = EclipseCalculator(reader=reader)
    direct_solar_path = calc.solar_eclipse_path(2451545.0)
    direct_all_occultations = all_lunar_occultations(2451545.0, 2451545.0 + 120.0, reader=reader)
    assert direct_all_occultations
    direct_occultation_path = lunar_occultation_path_at(
        direct_all_occultations[0].target,
        direct_all_occultations[0].jd_mid,
        reader=reader,
    )
    direct_star_events = lunar_star_occultation(
        203.835,
        -2.397,
        "Spica",
        2451545.0,
        2451545.0 + 120.0,
        reader=reader,
    )
    direct_star_path = (
        lunar_star_occultation_path_at(
            203.835,
            -2.397,
            "Spica",
            direct_star_events[0].jd_mid,
            reader=reader,
        )
        if direct_star_events
        else None
    )

    with use_reader_override(reader):
        direct_parans = find_parans(["Sun", "Moon", "Mars"], 2451544.5, 51.5, 0.0, orb_minutes=10.0)
        assert direct_parans
        target = direct_parans[0]
        direct_site = evaluate_paran_site(target, 2451544.5, 51.5, 0.0, orb_minutes=10.0)
        direct_samples = sample_paran_field(
            target,
            2451544.5,
            [51.0, 51.5],
            [0.0, 0.5],
            orb_minutes=10.0,
        )
        direct_analysis = analyze_paran_field(direct_samples, metric="match_presence", threshold=1.0)
        direct_extraction = extract_paran_field_contours(
            direct_samples,
            metric="match_presence",
            threshold=1.0,
        )
        direct_path_set = consolidate_paran_contours(direct_extraction)
        direct_structure = analyze_paran_field_structure(direct_analysis, direct_path_set)

    target_payload = {
        "body1": target.body1,
        "body2": target.body2,
        "circle1": target.circle1,
        "circle2": target.circle2,
        "jd1": target.jd1,
        "jd2": target.jd2,
        "orb_min": target.orb_min,
    }

    solar_path_response = client_with_engine.post(
        "/v1/eclipses/solar/path",
        json={"jd_start": 2451545.0},
    )
    lunar_path_response = client_with_engine.post(
        "/v1/occultations/lunar-path-at",
        json={
            "target": direct_all_occultations[0].target,
            "jd_mid": direct_all_occultations[0].jd_mid,
        },
    )
    star_path_response = (
        client_with_engine.post(
            "/v1/occultations/lunar-star-path-at",
            json={
                "star_lon": 203.835,
                "star_lat": -2.397,
                "star_name": "Spica",
                "jd_mid": direct_star_events[0].jd_mid,
            },
        )
        if direct_star_events
        else None
    )
    site_response = client_with_engine.post(
        "/v1/parans/site",
        json={
            "target": target_payload,
            "jd_day": 2451544.5,
            "lat": 51.5,
            "lon": 0.0,
            "orb_minutes": 10.0,
        },
    )
    samples_response = client_with_engine.post(
        "/v1/parans/field/samples",
        json={
            "target": target_payload,
            "jd_day": 2451544.5,
            "latitudes": [51.0, 51.5],
            "longitudes": [0.0, 0.5],
            "orb_minutes": 10.0,
        },
    )
    analysis_response = client_with_engine.post(
        "/v1/parans/field/analysis",
        json={
            "target": target_payload,
            "jd_day": 2451544.5,
            "latitudes": [51.0, 51.5],
            "longitudes": [0.0, 0.5],
            "metric": "match_presence",
            "threshold": 1.0,
            "orb_minutes": 10.0,
        },
    )
    contours_response = client_with_engine.post(
        "/v1/parans/field/contours",
        json={
            "target": target_payload,
            "jd_day": 2451544.5,
            "latitudes": [51.0, 51.5],
            "longitudes": [0.0, 0.5],
            "metric": "match_presence",
            "threshold": 1.0,
            "orb_minutes": 10.0,
        },
    )
    paths_response = client_with_engine.post(
        "/v1/parans/field/paths",
        json={
            "target": target_payload,
            "jd_day": 2451544.5,
            "latitudes": [51.0, 51.5],
            "longitudes": [0.0, 0.5],
            "metric": "match_presence",
            "threshold": 1.0,
            "orb_minutes": 10.0,
        },
    )
    structure_response = client_with_engine.post(
        "/v1/parans/field/structure",
        json={
            "target": target_payload,
            "jd_day": 2451544.5,
            "latitudes": [51.0, 51.5],
            "longitudes": [0.0, 0.5],
            "metric": "match_presence",
            "threshold": 1.0,
            "orb_minutes": 10.0,
        },
    )

    assert solar_path_response.status_code == 200
    solar_path_body = solar_path_response.json()
    assert solar_path_body["max_eclipse_lat"] == pytest.approx(direct_solar_path.max_eclipse_lat)
    assert solar_path_body["umbral_width_km"] == pytest.approx(direct_solar_path.umbral_width_km)

    assert lunar_path_response.status_code == 200
    lunar_path_body = lunar_path_response.json()
    assert lunar_path_body["jd_greatest_ut"] == pytest.approx(direct_occultation_path.jd_greatest_ut)
    assert lunar_path_body["path_width_km"] == pytest.approx(direct_occultation_path.path_width_km)

    if direct_star_events:
        assert star_path_response is not None
        assert direct_star_path is not None
        assert star_path_response.status_code == 200
        star_path_body = star_path_response.json()
        assert star_path_body["jd_greatest_ut"] == pytest.approx(direct_star_path.jd_greatest_ut)
        assert star_path_body["occulted_body"] == direct_star_path.occulted_body

    assert site_response.status_code == 200
    site_body = site_response.json()
    assert site_body["matched"] is direct_site.matched

    assert samples_response.status_code == 200
    assert len(samples_response.json()["samples"]) == len(direct_samples)

    assert analysis_response.status_code == 200
    analysis_body = analysis_response.json()
    assert analysis_body["active_sample_count"] == direct_analysis.active_sample_count
    assert len(analysis_body["regions"]) == len(direct_analysis.regions)

    assert contours_response.status_code == 200
    contours_body = contours_response.json()
    assert len(contours_body["segments"]) == len(direct_extraction.segments)

    assert paths_response.status_code == 200
    paths_body = paths_response.json()
    assert len(paths_body["paths"]) == len(direct_path_set.paths)

    assert structure_response.status_code == 200
    structure_body = structure_response.json()
    assert structure_body["dominant_path_index"] == direct_structure.dominant_path_index
    assert len(structure_body["hierarchy"]) == len(direct_structure.hierarchy)


def test_remaining_phase_six_routes_reject_invalid_kinds_and_pairings(
    client_with_engine: TestClient,
) -> None:
    invalid_eclipse_kind = client_with_engine.post(
        "/v1/eclipses/solar/next",
        json={"jd_start": 2451545.0, "kind": "sideways"},
    )
    invalid_heliacal_kind = client_with_engine.post(
        "/v1/heliacal/planet",
        json={
            "body": "Venus",
            "kind": "cosmic_rising",
            "jd_start": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
        },
    )
    invalid_occultation_observer = client_with_engine.post(
        "/v1/occultations/lunar",
        json={
            "target": "Venus",
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 20.0,
            "observer_lat": 10.0,
        },
    )
    invalid_paran_circle = client_with_engine.post(
        "/v1/parans/site",
        json={
            "target": {
                "body1": "Sun",
                "body2": "Moon",
                "circle1": "Diagonal",
                "circle2": "Rising",
                "jd1": 2451545.0,
                "jd2": 2451545.0,
                "orb_min": 0.0,
            },
            "jd_day": 2451544.5,
            "lat": 51.5,
            "lon": 0.0,
        },
    )
    invalid_paran_metric = client_with_engine.post(
        "/v1/parans/field/analysis",
        json={
            "target": {
                "body1": "Sun",
                "body2": "Moon",
                "circle1": "Rising",
                "circle2": "Setting",
                "jd1": 2451545.0,
                "jd2": 2451545.1,
                "orb_min": 2.0,
            },
            "jd_day": 2451544.5,
            "latitudes": [51.0],
            "longitudes": [0.0],
            "metric": "mystery",
            "threshold": 1.0,
        },
    )

    assert invalid_eclipse_kind.status_code == 422
    assert invalid_eclipse_kind.json()["error_code"] == "validation_error"
    assert "sideways" in invalid_eclipse_kind.json()["message"]

    assert invalid_heliacal_kind.status_code == 422
    assert invalid_heliacal_kind.json()["error_code"] == "validation_error"
    assert "planet heliacal endpoint supports only" in invalid_heliacal_kind.json()["message"]

    assert invalid_occultation_observer.status_code == 422
    assert invalid_occultation_observer.json()["error_code"] == "validation_error"
    assert "observer_lat and observer_lon" in invalid_occultation_observer.json()["message"]

    assert invalid_paran_circle.status_code == 422
    assert invalid_paran_circle.json()["error_code"] == "validation_error"

    assert invalid_paran_metric.status_code == 422
    assert invalid_paran_metric.json()["error_code"] == "validation_error"

"""Transport the admitted width state independently at each eclipse site."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from moira.julian import julian_day
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.phenomena import (
    serialize_solar_eclipse_global_availability,
    serialize_solar_eclipse_global_circumstances,
    serialize_solar_eclipse_path,
    serialize_solar_eclipse_path_availability,
)
from moira_server.models.phenomena import (
    SolarEclipsePathAvailabilityResponse, SolarEclipseGlobalAvailabilityResponse,
    SolarEclipsePathRequest, SolarEclipseGlobalCircumstancesRequest,
)
from moira_server.routers.phenomena import (
    solar_eclipse_path_route, solar_eclipse_path_availability_route,
    solar_eclipse_global_availability_route,
)


@pytest.mark.slow
@pytest.mark.parametrize("date", [(2003, 5, 31), (2044, 2, 28)])
def test_open_width_routes_return_explicit_unavailability(
    eclipse_calculator, monkeypatch, date,
):
    seed = julian_day(*date) - 1.0
    path = eclipse_calculator.solar_eclipse_path(seed, kind="annular", sample_count=3)
    result = eclipse_calculator.solar_global_circumstances(seed, kind="annular")
    engine = SimpleNamespace(
        _reader=eclipse_calculator._reader,
        solar_global_circumstances=lambda *args, **kwargs: result,
    )
    monkeypatch.setattr("moira_server.routers.phenomena.compute_solar_eclipse_path", lambda engine, request: path)
    p = solar_eclipse_path_availability_route(
        SolarEclipsePathRequest(jd_start=seed, kind="annular", sample_count=3), engine
    ).model_dump(mode="json")
    g = solar_eclipse_global_availability_route(
        SolarEclipseGlobalCircumstancesRequest(jd_start=seed, kind="annular"), engine
    ).model_dump(mode="json")
    assert p == serialize_solar_eclipse_path_availability(path).model_dump(mode="json")
    assert g == serialize_solar_eclipse_global_availability(result).model_dump(mode="json")
    # Existing strict clients continue to receive exactly the legacy field set.
    legacy_path = serialize_solar_eclipse_path(path).model_dump(mode="json")
    legacy_global = serialize_solar_eclipse_global_circumstances(result).model_dump(mode="json")
    assert "umbral_width_status" not in legacy_path
    assert "umbral_width_reason" not in legacy_path
    for site in (legacy_global["greatest"], legacy_global["greatest_duration"]):
        if site is not None:
            assert "path_width_status" not in site
            assert "path_width_reason" not in site
    assert p["umbral_width_km"] is None
    assert p["umbral_width_status"] == "closed_width_not_admitted"
    assert p["umbral_width_reason"] == "incomplete_generator_intersections"
    assert g["greatest"]["path_width_km"] is None
    assert g["greatest"]["path_width_status"] == "closed_width_not_admitted"
    assert g["greatest"]["path_width_reason"] == "incomplete_generator_intersections"
    bad_path = {**p, "umbral_width_km": 0.0}
    with pytest.raises(ValidationError, match="unadmitted closed width"):
        SolarEclipsePathAvailabilityResponse.model_validate(bad_path)
    bad_global = {**g, "greatest": {**g["greatest"], "path_width_reason": None}}
    with pytest.raises(ValidationError, match="unadmitted closed width"):
        SolarEclipseGlobalAvailabilityResponse.model_validate(bad_global)
    assert g["umbral_contacts"]["u1"] is not None
    assert g["umbral_contacts"]["u4"] is not None
    assert g["first_central_line_limit"] is not None
    assert g["last_central_line_limit"] is not None
    # This site has a separately evaluated epoch and width policy; it must not
    # be filled by copying the greatest-eclipse site's availability.
    duration = g["greatest_duration"]
    assert duration is not None
    if date == (2044, 2, 28):
        assert duration["path_width_km"] is None
        assert duration["path_width_status"] == "width_not_computed"
        assert duration["path_width_reason"] == "central_axis_boundary"
    if duration["path_width_status"] == "closed_width_not_admitted":
        assert duration["path_width_km"] is None
        assert duration["path_width_reason"] == "incomplete_generator_intersections"
    elif duration["path_width_status"] == "width_not_computed":
        assert duration["path_width_km"] is None
        assert duration["path_width_reason"] == "central_axis_boundary"
    else:
        assert duration["path_width_status"] == "available"
        assert duration["path_width_km"] is not None
        assert duration["path_width_reason"] is None


@pytest.mark.slow
def test_width_availability_invariant_rejects_fabricated_or_unexplained_states(
    eclipse_calculator,
):
    result = eclipse_calculator.solar_global_circumstances(julian_day(2003, 5, 30), kind="annular")
    site = result.greatest
    with pytest.raises(ValueError, match="unadmitted closed width"):
        replace(site, path_width_km=0.0)
    with pytest.raises(ValueError, match="unadmitted closed width"):
        replace(site, path_width_reason=None)
    with pytest.raises(ValueError, match="available width"):
        replace(site, path_width_status="available", path_width_reason=None)
    with pytest.raises(ValueError, match="absent width requires"):
        replace(result, greatest=replace(site, path_width_status="not_applicable", path_width_reason=None))
    # Legacy callers could construct a central duration site with no width
    # before availability metadata existed.  It remains unspecified, not
    # automatically reclassified as an admitted or unavailable measurement.
    legacy_duration = replace(
        result.greatest_duration, path_width_km=None,
        path_width_status="unspecified", path_width_reason=None,
    )
    legacy_greatest = replace(
        site, path_width_km=1.0, path_width_status="unspecified", path_width_reason=None,
    )
    legacy_result = replace(result, greatest=legacy_greatest, greatest_duration=legacy_duration)
    assert legacy_result.greatest_duration.path_width_status == "unspecified"
    assert legacy_result.greatest_duration.path_width_km is None


def test_legacy_direct_constructors_do_not_claim_width_availability():
    from dataclasses import fields
    from moira.eclipse import SolarEclipsePath
    from moira.solar_eclipse_global import SolarEclipseGreatestSite
    # Constructor defaults preserve old callers that supply neither new field.
    for cls, field_name in ((SolarEclipsePath, "umbral_width_status"),
                            (SolarEclipseGreatestSite, "path_width_status")):
        field = next(field for field in fields(cls) if field.name == field_name)
        assert field.default == "unspecified"

    from moira.eclipse_global import EclipseEpoch
    legacy_path = SolarEclipsePath(
        central_line_lats=(), central_line_lons=(),
        northern_limit_lats=(), northern_limit_lons=(),
        southern_limit_lats=(), southern_limit_lons=(),
        umbral_width_km=None, duration_at_max_s=0.0,
        max_eclipse_lat=0.0, max_eclipse_lon=0.0, eclipse_data=None,
    )
    legacy_site = SolarEclipseGreatestSite(
        epoch=EclipseEpoch(1.0, 1.0, 0.0, "legacy"), latitude_deg=0.0,
        longitude_deg=0.0, path_width_km=None, central_duration_seconds=0.0,
        sun_altitude_deg=0.0, sun_azimuth_deg=0.0, moon_altitude_deg=0.0,
        moon_azimuth_deg=0.0, separation_deg=0.0, sun_semidiameter_deg=0.25,
        moon_semidiameter_deg=0.25, magnitude=0.0, obscuration=0.0,
        local_class="none",
    )
    assert legacy_path.umbral_width_status == "unspecified"
    assert legacy_site.path_width_status == "unspecified"

    boundary = replace(legacy_site, path_width_status="width_not_computed", path_width_reason="central_axis_boundary")
    assert boundary.path_width_km is None
    with pytest.raises(ValueError, match="uncomputed boundary width"):
        replace(boundary, path_width_km=0.0)
    with pytest.raises(ValueError, match="uncomputed boundary width"):
        replace(boundary, path_width_reason=None)


def test_opt_in_openapi_preserves_legacy_response_properties():
    app = create_app(ServerConfig(docs_enabled=False))
    schema = app.openapi()
    paths = schema["paths"]
    assert "/v1/eclipses/solar/path/availability" in paths
    assert "/v1/eclipses/solar/global-circumstances/availability" in paths
    models = schema["components"]["schemas"]
    assert "umbral_width_status" not in models["SolarEclipsePathResponse"]["properties"]
    assert "path_width_status" not in models["SolarEclipseGreatestSiteResponse"]["properties"]
    assert "umbral_width_status" in models["SolarEclipsePathAvailabilityResponse"]["properties"]
    assert "path_width_status" in models["SolarEclipseGreatestSiteAvailabilityResponse"]["properties"]


def test_path_route_round_trip_preserves_legacy_shape(monkeypatch):
    from moira.eclipse import SolarEclipsePath
    data = SimpleNamespace(
        eclipse_type="annular", is_eclipse_season=True, is_solar_eclipse=True,
        is_lunar_eclipse=False, eclipse_magnitude=0.9, sun_longitude=0.0,
        moon_longitude=0.0, node_longitude=0.0, moon_latitude=0.0,
        sun_node_distance=0.0, angular_separation_3d=0.0, saros_index=None,
        saros_series=None, saros_lunation_number=None, saros_cycle_position=0.0,
        metonic_year=0.0, metonic_is_reset=False,
    )
    path = SolarEclipsePath(
        central_line_lats=(0.0,), central_line_lons=(0.0,),
        northern_limit_lats=(), northern_limit_lons=(), southern_limit_lats=(),
        southern_limit_lons=(), umbral_width_km=None, duration_at_max_s=0.0,
        max_eclipse_lat=0.0, max_eclipse_lon=0.0, eclipse_data=data,
        umbral_width_status="closed_width_not_admitted",
        umbral_width_reason="incomplete_generator_intersections",
    )
    monkeypatch.setattr("moira_server.routers.phenomena.compute_solar_eclipse_path", lambda engine, request: path)
    payload = SolarEclipsePathRequest(jd_start=2450000.0, kind="annular", sample_count=3)
    legacy = solar_eclipse_path_route(payload, object()).model_dump(mode="json")
    body = solar_eclipse_path_availability_route(payload, object()).model_dump(mode="json")
    assert body.pop("umbral_width_status") == "closed_width_not_admitted"
    assert body.pop("umbral_width_reason") == "incomplete_generator_intersections"
    assert body == legacy

"""Installed DE441 composition evidence; independent substrate reconstruction.

This verifies the compositor, not an additional external astrology authority.
Existing source-collated Gochar fixtures and BAV table tests own those layers.
"""
import importlib
import pytest

from moira import GocharaDatePolicy, GocharaNatalBavMode, GocharaBirthLocation
from moira.gochara import GOCHARA_PLANETS, gochara_from_positions
from moira.ashtakavarga import REKHA_TABLES
from moira._ephemeris_time import _bind_ephemeris_time
from moira.planets import planet_at
from moira.sidereal import _ayanamsa_at_tt
from moira.spk_reader import use_reader_override

dated = importlib.import_module("moira.gochara_dated")


@pytest.mark.parametrize("natal,transit,system", [
    (2447892.5, 2461319.5, "Lahiri"),
    (2316412.5, 2461319.5, "Raman"),
    (2451545.0, 2451545.0, "True Chitrapaksha"),
])
def test_real_reader_clocks_positions_and_raw_bav(moira_engine, natal, transit, system):
    engine = moira_engine
    policy = GocharaDatePolicy(ayanamsa_system=system, natal_bav_mode=GocharaNatalBavMode.COMPUTE_RAW)
    result = engine.gochara_at(natal, transit, policy=policy,
                               birth_location=GocharaBirthLocation(28.6139, 77.209))
    for epoch in (result.natal, result.transit):
        clock = _bind_ephemeris_time(epoch.jd_ut1, engine._reader)
        assert epoch.jd_tt == clock.epoch_tt and epoch.jd_tdb == clock.epoch_tdb
        assert epoch.kernel_label == clock.identity.summary_label
        with use_reader_override(engine._reader):
            offset = _ayanamsa_at_tt(clock.epoch_tt, system, "true")
            for position in epoch.positions:
                tropical = planet_at(position.planet, epoch.jd_ut1, reader=engine._reader,
                                      jd_tt=clock.epoch_tt).longitude
                assert position.tropical_longitude == tropical
                assert position.position.sidereal_longitude == pytest.approx((tropical-offset) % 360, abs=1e-12)
    if natal == 2316412.5:
        assert result.natal.delta_t_correction_seconds != 0
    indices = dict(result.natal_sign_indices)
    assert len(indices) == 8
    for bav in result.profile.snapshot.bhinna:
        expected = tuple(sum((sign-indices[ref]) % 12+1 in distances
                             for ref, distances in REKHA_TABLES[bav.planet].items()) for sign in range(12))
        assert bav.rekhas == expected
    independent = gochara_from_positions(result.natal.positions[1].position.sidereal_longitude,
        {p.planet: p.position.sidereal_longitude for p in result.transit.positions},
        bhinna={b.planet: b for b in result.profile.snapshot.bhinna}, policy=policy.gochara_policy)
    assert independent == result.profile.snapshot
    assert len(independent.planets) == 7 and independent.missing_planets == ()


@pytest.mark.parametrize("system", dated.Ayanamsa.ALL)
def test_all_named_ayanamsas_resolve_with_installed_resources(moira_engine, system):
    result = moira_engine.gochara_at(2451545, 2461319.5, policy=GocharaDatePolicy(ayanamsa_system=system))
    assert result.natal.ayanamsa_system == result.transit.ayanamsa_system == system
    assert len(result.profile.snapshot.planets) == 7


@pytest.mark.loopback
def test_real_engine_rest_result_and_actual_uncovered_epoch(moira_engine, monkeypatch):
    from fastapi.testclient import TestClient
    from moira_server.app import create_app
    from moira_server.config import ServerConfig
    from moira_server.serializers.gochara import serialize_gochara_date
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=True, prewarm_enabled=False))
    with TestClient(app) as client:
        body = {"natal_jd_ut1": 2447892.5, "transit_jd_ut1": 2461319.5}
        response = client.post("/v1/gochara/from-epochs", json=body)
        assert response.status_code == 200, response.text
        expected = moira_engine.gochara_at(**body)
        assert response.json() == serialize_gochara_date(expected).model_dump(mode="json")
        body["transit_jd_ut1"] = 10_000_000
        outside = client.post("/v1/gochara/from-epochs", json=body)
        assert outside.status_code == 422, outside.text
        assert outside.json()["error_code"] == "gochara_date_outside_coverage"

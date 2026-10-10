"""Real-reader clock/frame/lifecycle evidence; no predictive-validation claim."""
from contextvars import Context
from datetime import datetime, timedelta, timezone
from fractions import Fraction

from fastapi.testclient import TestClient
import pytest

from moira import (
    SayanadiBirthPolicy, SayanadiName, PanchangaSunriseDefinition,
    avasthas_for_datetime, sayanadi_avastha,
)
from moira.nodes import true_node
from moira.spk_reader import SpkReader, get_active_reader
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.avasthas import serialize_avastha_birth

pytestmark = [pytest.mark.integration, pytest.mark.requires_ephemeris, pytest.mark.loopback]
IST = timezone(timedelta(hours=5, minutes=30))


@pytest.mark.parametrize("birth,lat,lon,zone,system,sunrise,nodes", [
    (datetime(2026, 9, 22, 8, 31, 17, tzinfo=IST), 23+11/60, 82.5, "UTC+05:30", "Lahiri", "rashtriya_upper_limb", False),
    (datetime(2026, 10, 8, 12, 3, tzinfo=timezone.utc), 28.6139, 77.209, "Asia/Kolkata", "Raman", "usno_upper_limb", True),
    (datetime(2026, 3, 8, 12, 3, tzinfo=timezone.utc), 40.73, -73.92, "America/New_York", "Lahiri", "geometric_center", False),
    (datetime(2026, 11, 1, 12, 3, tzinfo=timezone.utc), 40.73, -73.92, "America/New_York", "Lahiri", "rashtriya_upper_limb", True),
])
def test_real_birth_clock_frame_and_direct_calculation_parity(moira_engine, birth, lat, lon, zone, system, sunrise, nodes):
    active_before = get_active_reader()
    policy = SayanadiBirthPolicy(ayanamsa_system=system,
                                 sunrise_definition=PanchangaSunriseDefinition(sunrise), evaluate_nodes=nodes)
    r = moira_engine.avasthas_for_datetime(birth, lat, lon, timezone_name=zone, name=SayanadiName(sound="स"), policy=policy)
    assert get_active_reader() is active_before
    assert r.status == "evaluated", r.unavailable_reasons
    assert r.sunrise.upper_jd_ut1 <= r.birth_jd_ut1 < r.next_sunrise.lower_jd_ut1
    assert r.sunrise.bracket_width_seconds <= policy.solver_tolerance_seconds
    assert r.epoch.ayanamsa_system == system and r.epoch.kernel_label
    assert r.epoch.jd_tt != r.epoch.jd_ut1
    low = (Fraction.from_float(r.birth_jd_ut1) - Fraction.from_float(r.sunrise.upper_jd_ut1)) * 60
    high = (Fraction.from_float(r.birth_jd_ut1) - Fraction.from_float(r.sunrise.lower_jd_ut1)) * 60
    assert max(1, -(-low.numerator // low.denominator)) == r.ghati_candidates[0]
    assert max(1, -(-high.numerator // high.denominator)) == r.ghati_candidates[0]
    inputs = {p.planet: p.position.sidereal_longitude for p in r.epoch.positions}
    for body, pa in r.chart.planets.items():
        assert pa.sayanadi == sayanadi_avastha(body, inputs, r.lagna_sidereal, context=r.chart.sayanadi_context)
    if nodes:
        raw = true_node(r.birth_jd_ut1, reader=moira_engine._reader, jd_tt=r.epoch.jd_tt).longitude
        assert r.node_longitudes["Rahu"] == (raw - r.epoch.ayanamsa_degrees) % 360
        for body in ("Rahu", "Ketu"):
            assert r.chart.sayanadi_nodes[body] == sayanadi_avastha(body, inputs | r.node_longitudes,
                                                                  r.lagna_sidereal, context=r.chart.sayanadi_context)
    if birth.month == 9:
        # Reuse VED-015's PAC 2026-27/31 Bhadra published minute sunrise;
        # unchanged 60-second institutional component gate. This is not a
        # published full Sayanadi chart or an observational birth-time oracle.
        assert abs((r.sunrise.moment.local - datetime(2026, 9, 22, 5, 49, tzinfo=IST)).total_seconds()) <= 60
        assert r.ghati_candidates == (7,)


def test_real_polar_sunrise_absence_is_unavailable(moira_engine):
    r = moira_engine.avasthas_for_datetime(datetime(2026, 6, 21, 12, 3, tzinfo=timezone.utc),
                                          69.6492, 18.9553, timezone_name="Europe/Oslo",
                                          name=SayanadiName(value=4))
    assert r.status == "unavailable" and r.chart is None and r.epoch is None
    assert r.unavailable_reasons == ("previous_or_next_sunrise_absent_in_three_civil_dates",)


def test_explicit_borrowed_reader_is_open_until_its_owner_closes(planetary_kernel_path):
    with SpkReader(planetary_kernel_path) as reader:
        r = avasthas_for_datetime(datetime(2000, 1, 2, 12, 3, tzinfo=timezone.utc), 0, 0,
                                  name=SayanadiName(value=4), reader=reader)
        assert r.status == "evaluated" and reader._closed is False
        assert r.reader_binding == "caller_owned_reader"
    assert reader._closed is True


@pytest.mark.parametrize("configured", [False, True])
def test_real_server_startup_reader_and_http_parity(planetary_kernel_path, monkeypatch, configured):
    payload = {"birth": "2026-10-08T12:03:00Z", "latitude": 28.6139, "longitude": 77.209,
               "timezone_name": "Asia/Kolkata", "name": {"sound": "स"},
               "policy": {"evaluate_nodes": True}}
    config = ServerConfig(kernel_path=str(planetary_kernel_path) if configured else None,
                           prewarm_enabled=False, require_kernel_ready=True)
    def run():
        with TestClient(create_app(config)) as client:
            engine = client.app.state.engine
            try:
                response = client.post("/v1/avasthas/from-datetime", json=payload)
                assert response.status_code == 200, response.text
                expected = engine.avasthas_for_datetime(datetime.fromisoformat(payload["birth"].replace("Z", "+00:00")),
                    payload["latitude"], payload["longitude"], name=SayanadiName(sound="स"),
                    timezone_name=payload["timezone_name"], policy=SayanadiBirthPolicy(evaluate_nodes=True))
                assert response.json() == serialize_avastha_birth(expected).model_dump(mode="json")
                assert expected.status == "evaluated" and expected.reader_binding == "caller_owned_reader"
                assert engine._reader_obj._closed is False
            finally:
                # This test owns the startup engine; composition borrows it.
                engine._reader_obj.close()
        assert engine._reader_obj._closed is True
    Context().run(run)


def test_curated_exports_have_owning_object_identity():
    import moira
    import moira.vedic as vedic
    import moira.facade as facade
    import moira.avasthas as core
    import importlib
    dated = importlib.import_module("moira.sayanadi_dated")
    for owner, names in ((core, ["SayanadiAvastha", "SayanadiPolicy", "SayanadiName", "SayanadiGhati",
                               "SayanadiContext", "SayanadiTrace", "SayanadiEffectProvenance",
                               "sayanadi_avastha", "sayanadi_ghati_from_elapsed"]),
                         (dated, dated.__all__)):
        for name in names:
            assert getattr(moira, name) is getattr(vedic, name) is getattr(facade, name) is getattr(owner, name)

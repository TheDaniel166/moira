"""Real DE441 composition and transport; published PAC gate is sunrise only."""
from contextvars import Context
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
import importlib

from fastapi.testclient import TestClient
import pytest

from moira import NamedMuhurtaPolicy, PanchangaSunriseDefinition, named_muhurta_for_date
from moira.spk_reader import SpkReader, get_active_reader
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.named_muhurta import serialize_named_muhurta_day

pytestmark = [pytest.mark.integration, pytest.mark.requires_ephemeris, pytest.mark.loopback]
IST = timezone(timedelta(hours=5, minutes=30))


@pytest.mark.parametrize("day,lat,lon,zone,sunrise,basis", [
    (date(2026, 9, 22), 23+11/60, 82.5, "UTC+05:30", "rashtriya_upper_limb", "arunadatta_fixed_ghati"),
    (date(2026, 6, 21), 28.6139, 77.209, "Asia/Kolkata", "usno_upper_limb", "legacy_proportional_night_14"),
    (date(2026, 3, 8), 40.73, -73.92, "America/New_York", "geometric_center", "arunadatta_fixed_ghati"),
    (date(2026, 11, 1), 40.73, -73.92, "America/New_York", "rashtriya_upper_limb", "legacy_proportional_night_14"),
])
def test_real_solar_interval_bounds_and_rational_composition(moira_engine, day, lat, lon, zone, sunrise, basis):
    active = get_active_reader()
    policy = NamedMuhurtaPolicy(sunrise_definition=PanchangaSunriseDefinition(sunrise), brahma_basis=basis)
    r = moira_engine.named_muhurta_for_date(day, lat, lon, timezone=zone, policy=policy)
    assert get_active_reader() is active
    assert r.result.status == "available" and r.reader_binding == "caller_owned_reader"
    assert r.kernel_label == "DE-0441LE-0441" and r.clock_jd_tt != r.clock_jd_ut1
    assert r.result.sunrise.moment.local.date() == day
    rise, setting, previous = (Fraction.from_float(x.jd_ut1) for x in
        (r.result.sunrise, r.result.sunset, r.result.previous_sunset))
    expected = [((8*rise+7*setting)/15, (7*rise+8*setting)/15)]
    expected.append((rise-Fraction(4, 60), rise-Fraction(2, 60)) if basis == "arunadatta_fixed_ghati"
                    else ((2*previous+13*rise)/15, (previous+14*rise)/15))
    for window, pair in zip(r.result.intervals, expected):
        assert (window.start_jd_ut1, window.end_jd_ut1) == tuple(map(float, pair))
        assert window.start.local.tzinfo == window.end.local.tzinfo
        assert window.contains((window.start_jd_ut1+window.end_jd_ut1)/2) is True
    for anchor in (r.result.sunrise, r.result.sunset, r.result.previous_sunset):
        assert (anchor.upper_jd_ut1-anchor.lower_jd_ut1)*86400 <= .1
    if day.month == 9:
        # PAC 2026-27, 31 Bhadra, original VED-015 published-minute component
        # threshold. This supplies no published paired Abhijit/Brahma oracle.
        expected_sunrise = datetime(2026, 9, 22, 5, 49, tzinfo=IST)
        assert abs((r.result.sunrise.moment.local-expected_sunrise).total_seconds()) <= 60


@pytest.mark.parametrize("day", [date(2026, 6, 21), date(2026, 12, 21)])
def test_real_polar_dates_do_not_fabricate_windows(moira_engine, day):
    r = moira_engine.named_muhurta_for_date(day, 69.6492, 18.9553, timezone="Europe/Oslo")
    assert r.result.status == "unavailable"
    assert all(w.unavailable_reasons == ("sunrise_absent",) for w in r.result.intervals)


def test_explicit_reader_lifecycle_and_active_context_entrypoint(planetary_kernel_path):
    from moira.spk_reader import use_reader_override
    with SpkReader(planetary_kernel_path) as reader:
        explicit = named_muhurta_for_date(date(2000, 1, 2), 0, 0, timezone="UTC", reader=reader)
        with use_reader_override(reader):
            implicit = named_muhurta_for_date(date(2000, 1, 2), 0, 0, timezone="UTC")
            assert get_active_reader() is reader
        assert explicit.result == implicit.result
        assert implicit.reader_binding == "active_context_reader"
        assert reader._closed is False
    assert reader._closed is True


@pytest.mark.parametrize("configured", [False, True])
def test_real_startup_reader_and_http_parity(planetary_kernel_path, configured):
    config = ServerConfig(kernel_path=str(planetary_kernel_path) if configured else None,
                           prewarm_enabled=False, require_kernel_ready=True)
    def run():
        with TestClient(create_app(config)) as client:
            engine = client.app.state.engine
            try:
                payload = {"local_date": "2026-10-08", "latitude": 28.6139, "longitude": 77.209,
                           "timezone": "Asia/Kolkata"}
                response = client.post("/v1/muhurta/named/day", json=payload)
                assert response.status_code == 200, response.text
                expected = engine.named_muhurta_for_date(date(2026, 10, 8), 28.6139, 77.209, timezone="Asia/Kolkata")
                assert response.json() == serialize_named_muhurta_day(expected).model_dump(mode="json")
                assert expected.result.status == "available" and engine._reader_obj._closed is False
            finally:
                engine._reader_obj.close()
        assert engine._reader_obj._closed is True
    Context().run(run)


def test_all_public_exports_have_owning_identity():
    import moira
    import moira.facade as facade
    import moira.vedic as vedic
    owner = importlib.import_module("moira.named_muhurta")
    for name in owner.__all__:
        assert getattr(moira, name) is getattr(facade, name) is getattr(vedic, name) is getattr(owner, name)

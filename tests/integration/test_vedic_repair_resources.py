"""Real reader lifecycle, frame/time and polar repair acceptance."""

from datetime import datetime, timezone, timedelta
import pytest
from moira.shadbala_context import derive_shadbala_context
from moira.spk_reader import SpkReader, get_active_reader, use_reader_override
from moira._kernel_paths import find_planetary_kernel
from moira.upagrahas import kalavela_upagrahas
from moira.julian import jd_from_datetime, utc_to_ut1

pytestmark = pytest.mark.requires_ephemeris


def test_real_borrowed_kalavela_lifecycle(moira_engine, monkeypatch):
    import moira.spk_reader as readers

    original = get_active_reader()
    with SpkReader(find_planetary_kernel()) as borrowed:
        calls = []
        close = borrowed.close
        monkeypatch.setattr(borrowed, "close", lambda: calls.append("close"))
        try:
            # Explicit reader with no ambient reader, then a distinct active reader.
            monkeypatch.setattr(readers, "_reader", None)
            with use_reader_override(None):
                first = kalavela_upagrahas(2451545.0, 28.6, 77.2, reader=borrowed)
                assert get_active_reader() is None
            with use_reader_override(moira_engine._reader_obj):
                second = kalavela_upagrahas(2451545.0, 28.6, 77.2, reader=borrowed)
                assert get_active_reader() is moira_engine._reader_obj
            assert first == second and not calls
        finally:
            monkeypatch.setattr(borrowed, "close", close)
    monkeypatch.undo()
    assert get_active_reader() is original


def test_actual_solar_longitude_season_timezone_and_polar_context(moira_engine):
    dt = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    local = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
    jd = utc_to_ut1(jd_from_datetime(dt))
    assert utc_to_ut1(jd_from_datetime(local)) == jd
    r = moira_engine._reader_obj
    a = derive_shadbala_context(jd, 28.6, 77.2, reader=r)
    b = derive_shadbala_context(jd, 28.6, -74.0, reader=r)
    assert dict(a.sidereal_longitudes) == dict(b.sidereal_longitudes)
    assert (
        (a.local_apparent_day_fraction - b.local_apparent_day_fraction) % 1
    ) == pytest.approx(151.2 / 360, abs=1e-12)
    summer = derive_shadbala_context(2451717.0, 28.6, 77.2, reader=r)
    assert summer.sunset_jd - summer.sunrise_jd > a.sunset_jd - a.sunrise_jd
    polar = derive_shadbala_context(2451717.0, 89.0, 0.0, reader=r)
    assert polar.missing_components == ("tribhaga",)
    assert len(polar.declinations) == 7

"""Analytic solar crossings for transport and boundary invariants, not oracles."""
from datetime import datetime, time
import importlib
from types import SimpleNamespace

from moira.julian import jd_from_datetime
from moira.spk_reader import get_active_reader


def install_analytic_solar(monkeypatch, *, sunrise_hour=6, sunset_hour=18):
    owner = importlib.import_module("moira.named_muhurta")
    daily = importlib.import_module("moira.daily_panchanga")
    reader, calls, roots = object(), [], []
    state = SimpleNamespace(omit_rises=False, omit_sets=False, multiple=False, fail_signal=False)
    monkeypatch.setattr(daily, "utc_to_ut1", lambda jd: jd)
    monkeypatch.setattr(daily, "_ut1_to_utc", lambda jd: jd)
    monkeypatch.setattr(owner, "get_reader", lambda: reader)

    def solar(day, zone, lat, lon, altitude):
        assert get_active_reader() is reader
        calls.append(("solar", day))
        start, end = daily._civil_bounds(day, zone)
        rise = jd_from_datetime(datetime.combine(day, time(sunrise_hour), zone))
        setting = jd_from_datetime(datetime.combine(day, time(sunset_hour), zone))
        roots.extend(((rise, altitude, 1), (setting, altitude, -1)))
        # Coarse witnesses are deliberately off the true root by 0.2 seconds.
        rises = () if state.omit_rises else (daily._moment(rise + .2/86400, zone),)
        if state.multiple:
            rises += (daily._moment(rise + .01, zone),)
        sets = () if state.omit_sets else (daily._moment(setting + .2/86400, zone),)
        return daily.PanchangaSolarDate(day, daily._moment(start, zone), daily._moment(end, zone), rises, sets)

    def signal(jd, *args):
        assert get_active_reader() is reader
        if state.fail_signal:
            return float("nan")
        root, altitude, direction = min(roots, key=lambda root: abs(jd-root[0]))
        return direction * (jd-root) * 86400 + altitude

    def clock(jd, bound):
        assert bound is reader and get_active_reader() is reader
        calls.append(("clock", jd))
        return SimpleNamespace(jd_ut1=jd, epoch_tt=jd+70/86400, epoch_tdb=jd+70/86400,
            delta_t_seconds=70, delta_t_correction_seconds=0, tdb_minus_tt_seconds=0,
            identity=SimpleNamespace(summary_label="analytic solar fixture"),
            raw_delta_t=SimpleNamespace(source_product="analytic clock"))

    monkeypatch.setattr(owner, "_solar_date", solar)
    monkeypatch.setattr(owner, "_altitude", signal)
    monkeypatch.setattr(owner, "_bind_ephemeris_time", clock)
    return owner, reader, calls, state

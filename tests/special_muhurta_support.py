"""Analytic altitude and moving-longitude fixtures, not external oracles."""
import importlib
import math
from types import SimpleNamespace

from moira.spk_reader import get_active_reader
from tests.named_muhurta_support import install_analytic_solar


def install_special_sky(monkeypatch):
    named, reader, calls, state = install_analytic_solar(monkeypatch)
    owner = importlib.import_module("moira.special_muhurta")
    daily = importlib.import_module("moira.daily_panchanga")
    origin = 2451544.5

    def altitude(jd, *args):
        assert get_active_reader() is reader
        return float("nan") if state.fail_signal else 30 * math.sin(2*math.pi*(jd-origin-.25))

    def solar(day, zone, lat, lon, height):
        assert get_active_reader() is reader
        calls.append(("solar", day, height))
        start, end = daily._civil_bounds(day, zone)
        offset = math.asin(height/30)/(2*math.pi)
        rises, sets = [], []
        for n in range(math.floor(start-origin)-1, math.ceil(end-origin)+1):
            rise, setting = origin+n+.25+offset, origin+n+.75-offset
            if start <= rise < end and not state.omit_rises:
                rises.append(daily._moment(rise+.2/86400, zone))
                if state.multiple:
                    rises.append(daily._moment(rise+.01, zone))
            if start <= setting < end and not state.omit_sets:
                sets.append(daily._moment(setting+.2/86400, zone))
        return daily.PanchangaSolarDate(day, daily._moment(start, zone), daily._moment(end, zone), tuple(rises), tuple(sets))

    def planet(body, jd, *, reader):
        assert reader is get_active_reader()
        calls.append(("position", body))
        return SimpleNamespace(longitude=((jd-origin)*(1 if body == "Sun" else 13.5)+10) % 360)

    for module in (owner, named):
        monkeypatch.setattr(module, "_solar_date", solar)
        monkeypatch.setattr(module, "_altitude", altitude)
    monkeypatch.setattr(owner, "get_reader", lambda: reader)
    monkeypatch.setattr(owner, "planet_at", planet)
    monkeypatch.setattr(owner, "tropical_to_sidereal", lambda lon, jd, system: lon)
    return owner, reader, calls, state

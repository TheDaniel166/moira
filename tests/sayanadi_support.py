"""Controlled sunrise/position trajectories; never classical/astronomy oracles."""
from datetime import datetime, time
import importlib
from types import SimpleNamespace

from moira.gochara_dated import GocharaEpoch
from moira.julian import jd_from_datetime
from moira.spk_reader import get_active_reader


def install_analytic_birth(monkeypatch):
    dated = importlib.import_module("moira.sayanadi_dated")
    daily = importlib.import_module("moira.daily_panchanga")
    reader, calls, roots = object(), [], []
    monkeypatch.setattr(dated, "utc_to_ut1", lambda jd: jd)
    monkeypatch.setattr(daily, "_ut1_to_utc", lambda jd: jd)
    monkeypatch.setattr(dated, "get_reader", lambda: reader)

    def solar_date(day, zone, lat, lon, altitude):
        assert get_active_reader() is reader
        jd = jd_from_datetime(datetime.combine(day, time(6), zone))
        roots.append((jd, altitude))
        calls.append(("solar_date", day))
        return SimpleNamespace(sunrises=(SimpleNamespace(jd_ut1=jd),))

    def signal(jd, *args):
        assert get_active_reader() is reader
        root, altitude = min(roots, key=lambda root: abs(jd-root[0]))
        return (jd - root) * 86400 + altitude

    def epoch(jd, bound, policy):
        assert bound is reader and get_active_reader() is reader
        calls.append(("epoch", jd))
        return GocharaEpoch(jd, jd+70/86400, jd+70/86400, 70, 0, 0,
                            "analytic_clock", "DE-0441LE-0441", "DE441", "LE441",
                            -25.936, policy.ayanamsa_system, 25, (10, 37.2, 90, 150, 190, 220, 270))

    def node(jd, *, reader: object, jd_tt):
        assert get_active_reader() is reader
        calls.append(("true_node", jd_tt))
        return SimpleNamespace(longitude=44)

    monkeypatch.setattr(dated, "_solar_date", solar_date)
    monkeypatch.setattr(dated, "_altitude", signal)
    monkeypatch.setattr(dated, "_epoch", epoch)
    monkeypatch.setattr(dated, "_lagna", lambda epoch, lat, lon: (250, 225))
    monkeypatch.setattr(dated, "true_node", node)
    return dated, reader, calls

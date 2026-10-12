"""Analytic window astronomy; exact polynomial expectations live in tests."""
from importlib import import_module
from moira.gochara import GOCHARA_PLANETS
from moira.gochara_dated import GocharaEpoch
from moira._event_search.frames import Differential as D, _jet_polynomial
from moira._event_search.intervals import Interval as I
from moira._event_search.isolation import Signal

START = 2460000.
NATAL = 2451545.


def install(monkeypatch, curves=None, natal_sign=0):
    search = import_module("moira._gochara_window_search")
    curves = {p: (15.+30*i,) for i,p in enumerate(GOCHARA_PLANETS)} | (curves or {})
    calls = []
    def epoch(jd, reader, policy):
        calls.append(jd)
        if jd == NATAL:
            values = tuple((natal_sign*30+15 if p == "Moon" else 15+30*i)%360
                           for i,p in enumerate(GOCHARA_PLANETS))
        else:
            x = jd-START
            values = tuple(sum(c*x**i for i,c in enumerate(curves[p]))%360 for p in GOCHARA_PLANETS)
        return GocharaEpoch(jd,jd,jd,0.,0.,0.,"analytic", "analytic", "DE441", "LE441",
                            -25.936,policy.ayanamsa_system,0.,values)
    class Astronomy:
        def __init__(self, reader, meter, policy, start, end):
            self.meter = meter
        def signal(self, planet, a, b, coarse=False):
            x = D(I(a-START,b-START), I.point(1.),I.point((a+b)/2-START),(b-a)/2)
            y = _jet_polynomial(curves[planet],x)
            return Signal(y.value,y.rate,y.center)
        def receipts(self):
            return (("source", "independently specified analytic polynomial"),)
    monkeypatch.setattr(search,"_epoch",epoch)
    monkeypatch.setattr(search,"GocharaWindowAstronomy",Astronomy)
    return calls

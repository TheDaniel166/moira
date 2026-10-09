"""Linear independent sky and analytic solar anchors; no oracle claim."""
from types import SimpleNamespace
import importlib
from moira.spk_reader import get_active_reader
from tests.special_muhurta_support import install_special_sky


def install_shuddhi_sky(monkeypatch):
    _, reader, calls, state = install_special_sky(monkeypatch)
    owner = importlib.import_module('moira._panchanga_shuddhi_day')
    origin=2451544.5
    def planet(body, jd, *, reader):
        assert reader is get_active_reader()
        calls.append(('position',body,jd))
        return SimpleNamespace(longitude=((jd-origin)*(1 if body=='Sun' else 13.5)+10)%360)
    def angles(jd,lat,lon):
        assert get_active_reader() is reader
        return SimpleNamespace(asc=((jd-origin)*360+lon)%360,obliquity=23.44)
    monkeypatch.setattr(owner,'get_reader',lambda: reader)
    monkeypatch.setattr(owner,'planet_at',planet)
    monkeypatch.setattr(owner,'_local_angles_at',angles)
    monkeypatch.setattr(owner,'tropical_to_sidereal',lambda lon,jd,system:lon)
    return owner,reader,calls,state

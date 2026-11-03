"""Native longitude adoption without changing the bounded transit product.

Analytic curves independently define exact hits, motion and orb boundaries.
Ephemeris comparisons use the existing default apparent geocentric longitude
and the native planetary route's existing 1e-12 degree parity threshold.
"""
from collections import Counter
from dataclasses import replace
import math
from types import SimpleNamespace

import pytest

from moira import planets, transits, transits_aspects as aspects
from moira.constants import Body
from moira.nodes import true_node

JD = 2451545.0


def test_compiled_transit_path_without_external_ephemeris():
    from scripts.check_transit_native_wheel import check_native_transit_path

    check_native_transit_path()


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('body', Body.ALL_PLANETS)
@pytest.mark.parametrize('offset', [-40000., -12.25, 0., 40000.])
def test_transit_longitude_uses_existing_native_apparent_product(planetary_reader, monkeypatch, body, offset):
    jd = JD + offset
    expected = planets.planet_at(body, jd, reader=planetary_reader).longitude
    native = planets._native_default_apparent_longitude(body, jd, planetary_reader)
    assert native is not None, 'real native planetary reader must admit the fast path'
    assert abs((native-expected+180.) % 360.-180.) < 1e-12

    def unused_full_planet(*args, **kwargs):
        raise AssertionError('transit longitude must not calculate unused PlanetData speed')

    monkeypatch.setattr(transits, 'planet_at', unused_full_planet)
    truth = transits._resolve_longitude_truth(body, jd, planetary_reader)
    assert truth.longitude == native
    assert (truth.resolved_kind, truth.resolved_name, truth.jd_ut) == ('planet', body, jd)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('offset', [-40000., -12.25, 0., 40000.])
def test_node_longitude_omits_only_unused_rate(planetary_reader, offset):
    jd = JD+offset
    expected = true_node(jd, reader=planetary_reader).longitude
    truth = transits._resolve_longitude_truth(Body.TRUE_NODE, jd, planetary_reader)
    assert truth.longitude == expected
    assert truth.resolved_kind == 'node'


def test_unadmitted_native_reader_keeps_scalar_provider_and_truth(monkeypatch):
    reader = object()
    assert planets._native_default_apparent_longitude(Body.MARS, JD, reader) is None
    monkeypatch.setattr(transits, 'planet_at', lambda body, jd, reader: SimpleNamespace(longitude=123.25))
    truth = transits._resolve_longitude_truth(' mars ', JD, reader)
    assert truth.requested_spec == ' mars '
    assert (truth.resolved_kind, truth.resolved_name, truth.longitude) == ('planet', Body.MARS, 123.25)


def install_curve(monkeypatch, curve):
    calls = Counter()

    def canonical(body, jd, reader):
        calls[jd] += 1
        return curve(jd-JD) % 360.

    def discarded_geometric(*args, **kwargs):
        raise AssertionError('bounded canonical scanner must not compute a discarded geometric prepass')

    monkeypatch.setattr(aspects, '_resolve_longitude', canonical)
    monkeypatch.setattr(aspects, '_native_ecliptic_longitude_series', discarded_geometric)
    monkeypatch.setattr(aspects, '_native_small_body_series', discarded_geometric)
    return calls


def grid(specs, end=20., **kwargs):
    return aspects.find_aspect_transits_to_longitudes(
        Body.MERCURY, specs, JD, JD+end, step_days=1., reader=object(), **kwargs)


def test_canonical_samples_are_reused_across_targets(monkeypatch):
    calls = install_curve(monkeypatch, lambda t: 10*t)
    events = grid([(50., 0., 1.), (100., 0., 1.), (150., 0., 1.)])
    assert [event.jd_exact-JD for event in events] == pytest.approx([5., 10., 15.], abs=1e-6)
    assert max(calls.values()) == 1


def test_narrow_orb_entry_and_exit_survive_native_adoption(monkeypatch):
    install_curve(monkeypatch, lambda t: 13*(t-4.27))
    event, = grid([(0., 0., 1.)], end=9.)
    assert event.jd_exact-JD == pytest.approx(4.27, abs=1e-6)
    assert event.jd_entering-JD == pytest.approx(4.27-1/13, abs=1e-6)
    assert event.jd_leaving-JD == pytest.approx(4.27+1/13, abs=1e-6)


def test_retrograde_passes_and_clipped_connected_window_survive(monkeypatch):
    install_curve(monkeypatch, lambda t: 10*math.sin((t-15)*math.pi/10))
    events = grid([(0., 0., 15.)], end=30.)
    assert [event.jd_exact-JD for event in events] == pytest.approx([5., 15., 25.], abs=1e-6)
    assert [event.is_retrograde_hit for event in events] == [True, False, True]
    assert all(event.jd_entering is None and event.jd_leaving is None for event in events)
    backward = grid([(0., 0., 15.)], end=30., search_motion='backward')
    assert [event.jd_exact for event in backward] == [event.jd_exact for event in reversed(events)]
    assert all(event.search_motion == 'backward' for event in backward)


def test_stationary_touch_and_inclusive_range_endpoints_survive(monkeypatch):
    install_curve(monkeypatch, lambda t: .01*(t-10.3)**2)
    touch, = grid([(0., 0., .1)])
    assert touch.jd_exact-JD == pytest.approx(10.3, abs=2e-6)
    install_curve(monkeypatch, lambda t: 18*t)
    endpoints = grid([(0., 0., 1.)])
    assert [event.jd_exact-JD for event in endpoints] == [0., 20.]
    assert endpoints[0].jd_entering is None
    assert endpoints[-1].jd_leaving is None


def test_exhausted_search_stays_explicitly_incomplete(monkeypatch):
    import moira._fixed_aspect_search as fixed

    install_curve(monkeypatch, lambda t: t-10)
    policy = fixed._FixedScanPolicy
    monkeypatch.setattr(fixed, '_FixedScanPolicy', lambda *a, **kw: replace(policy(*a, **kw), max_evaluations=3))
    with pytest.raises(RuntimeError, match='incomplete: search_budget_exhausted'):
        grid([(0., 0., 1.)])

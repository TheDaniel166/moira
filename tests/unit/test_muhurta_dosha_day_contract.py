"""Analytic transition ownership, reader failure cleanup and public contracts."""
from dataclasses import asdict, replace
from datetime import date
import importlib
import math

import pytest

from moira import Moira, MuhurtaDoshaPolicy, muhurta_doshas_for_date, detect_muhurta_doshas
from moira.muhurta_dosha import MC_NECESSARY, MC_ABHIJIT
from moira.muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from moira.spk_reader import get_active_reader, use_reader_override, MissingKernelError, OutOfRangeError
from tests.muhurta_dosha_support import install_dosha_sky
from tests.unit.test_muhurta_dosha import point, event, finding


def test_all_cells_hold_away_from_midpoints_and_root_bands(monkeypatch):
    _, reader, _, _ = install_dosha_sky(monkeypatch)
    policy = MuhurtaDoshaPolicy(parihara_profiles=(MC_NECESSARY, MC_ABHIJIT))
    day = muhurta_doshas_for_date(date(2026, 10, 9), 20, 80, timezone='Asia/Kolkata',
                                reader=reader, policy=policy, necessary_activity=True)
    def truth(assessment):
        return tuple((f.rule_id, f.detected, f.neutralized) for f in assessment.findings)
    for cell in day.cells:
        lo, hi = cell.interval.start.upper_jd_ut1, cell.interval.end.lower_jd_ut1
        for fraction in (.0001, .1, .9, .9999):
            jd = lo + fraction*(hi-lo)
            values = asdict(cell.assessment.inputs)
            values.update(sun_sidereal_longitude=((jd-2451544.5)+10) % 360,
                          moon_sidereal_longitude=((jd-2451544.5)*13.5+10) % 360,
                          lagna_sidereal_longitude=((jd-2451544.5)*360+80) % 360,
                          jd_ut1=jd, phase_spans=cell.assessment.inputs.phase_spans,
                          sunrise_day=cell.assessment.inputs.sunrise_day,
                          sunset=cell.assessment.inputs.sunset)
            assert truth(detect_muhurta_doshas(**values, policy=policy)) == truth(day.at(jd))
    for b in day.transition_bands:
        if b.lower_jd_ut1 < b.upper_jd_ut1:
            assert all(day.at(jd) is None for jd in (b.lower_jd_ut1, b.jd_ut1, b.upper_jd_ut1))
    # The weekday belongs to the sunrise date on both sides of local midnight.
    assert {c.assessment.inputs.weekday for c in day.cells} == {5}
    assert day.at(day.sunrise.lower_jd_ut1-1) is None
    assert day.at(day.next_sunrise.upper_jd_ut1+1) is None


@pytest.mark.parametrize('error,expected', [
    (OutOfRangeError('outside coverage', [2451545.]), MuhurtaCoverageError),
    (MissingKernelError('missing kernel'), MuhurtaResourceError),
    (RuntimeError('unexpected signal failure'), RuntimeError),
])
def test_exception_restores_foreign_active_reader_without_closing_caller(monkeypatch, error, expected):
    owner, reader, _, _ = install_dosha_sky(monkeypatch)
    def fail(*args, **kwargs):
        assert get_active_reader() is reader
        raise error
    monkeypatch.setattr(owner, 'planet_at', fail)
    foreign = object()
    with use_reader_override(foreign):
        with pytest.raises(expected):
            muhurta_doshas_for_date(date(2026, 10, 9), 20, 80, timezone='Asia/Kolkata', reader=reader)
        assert get_active_reader() is foreign
    assert not getattr(reader, '_closed', False)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1., 360.])
def test_bad_circular_signal_fails_before_publishing_cells(monkeypatch, value):
    owner, reader, calls, _ = install_dosha_sky(monkeypatch)
    monkeypatch.setattr(owner, 'tropical_to_sidereal', lambda *args: value)
    with pytest.raises(ValueError, match='invalid circular phase'):
        muhurta_doshas_for_date(date(2026, 10, 9), 20, 80, timezone='Asia/Kolkata', reader=reader)
    assert len(calls) < 30


def test_retrograde_signal_is_rejected_with_bounded_work(monkeypatch):
    owner, reader, calls, _ = install_dosha_sky(monkeypatch)
    monkeypatch.setattr(owner, 'tropical_to_sidereal', lambda lon, *args: (-lon) % 360)
    with pytest.raises(ValueError, match='nonmonotonic or unresolved phase'):
        muhurta_doshas_for_date(date(2026, 10, 9), 20, 80, timezone='Asia/Kolkata', reader=reader)
    assert len(calls) < 200


@pytest.mark.parametrize('change', [
    {'local_date': date(1, 1, 1)}, {'local_date': date(9999, 1, 1)},
    {'local_date': '2026-10-09'}, {'latitude': True}, {'longitude': float('nan')},
    {'timezone': 'Mars/Unknown'}, {'necessary_activity': 'yes'},
    {'local_date': date(2011, 12, 30), 'timezone': 'Pacific/Apia'},
])
def test_direct_day_preflight_never_discovers_reader(monkeypatch, change):
    owner = importlib.import_module('moira._muhurta_dosha_day')
    def unexpected():
        pytest.fail('reader discovery before input validation')
    monkeypatch.setattr(owner, 'get_reader', unexpected)
    values = dict(local_date=date(2026, 10, 9), latitude=20, longitude=80, timezone='Asia/Kolkata')
    with pytest.raises(ValueError):
        muhurta_doshas_for_date(**(values | change))


def test_exact_phase_edges_and_uncertain_yamaghanta_pair():
    # Friday's Rohini pair, with both neighbouring full events explicitly given.
    spans = (event('nakshatra', 3, 0, 1, 1e-5), event('nakshatra', 4, 1, 2, 1e-5))
    for star in (3, 4):
        result = detect_muhurta_doshas(0, (star+.5)*360/27, jd_ut1=1,
                                     weekday=5, phase_spans=spans)
        assert finding(result, 'yamaghanta_yoga').detected is None
    exact = tuple(replace(s, interval=replace(s.interval, start=point(s.interval.start.jd_ut1),
                                             end=point(s.interval.end.jd_ut1))) for s in spans)
    for jd, star, expected in ((math.nextafter(1., 0.), 3, True), (1., 4, False)):
        result = detect_muhurta_doshas(0, (star+.5)*360/27, jd_ut1=jd,
                                     weekday=5, phase_spans=exact)
        assert finding(result, 'yamaghanta_yoga').detected is expected


def test_rejects_unresolved_events_and_foreign_uncertain_parent():
    with pytest.raises(ValueError, match='separated endpoint'):
        event('lagna', 0, 0, .001, .001)
    with pytest.raises(ValueError, match='possible parent'):
        detect_muhurta_doshas(0, 45, jd_ut1=1, phase_spans=(event('nakshatra', 20, 0, 1, 1e-5),))


def test_public_curation_and_facade_identity():
    owner = importlib.import_module('moira.muhurta_dosha')
    root = importlib.import_module('moira')
    vedic = importlib.import_module('moira.vedic')
    facade = importlib.import_module('moira.facade')
    names = ('MuhurtaDoshaPolicy', 'DoshaPhaseSpan', 'MuhurtaDoshaInputs', 'DoshaWitness',
             'DoshaPredicate', 'PariharaEvidence', 'MuhurtaDoshaFinding', 'MuhurtaDoshaAssessment',
             'DoshaCatalogueEntry', 'MuhurtaDoshaCatalogue', 'MuhurtaDoshaCell', 'MuhurtaDoshaDay',
             'muhurta_dosha_catalogue', 'detect_muhurta_doshas', 'muhurta_doshas_for_date')
    for name in names:
        for public in (root, vedic, facade):
            assert getattr(public, name) is getattr(owner, name)
            assert name in public.__all__
    engine = object.__new__(Moira)
    engine._reader_obj = None
    assert engine.muhurta_dosha_catalogue() == owner.muhurta_dosha_catalogue()
    assert engine.detect_muhurta_doshas(0, 45, jd_ut1=.5) == detect_muhurta_doshas(0, 45, jd_ut1=.5)


def test_derived_band_overlapping_sunrise_is_retained_even_if_estimate_is_outside(monkeypatch):
    from moira.muhurta_dosha import DoshaWitness, _finding
    from moira.panchanga_shuddhi import ShuddhiBoundary, ShuddhiInterval
    owner, reader, _, _ = install_dosha_sky(monkeypatch)
    original = owner.detect_muhurta_doshas
    def boundary_case(*args, **kwargs):
        result = original(*args, **kwargs)
        rise = result.inputs.sunrise_day.start.jd_ut1
        # An uncertain restriction edge whose estimate precedes sunrise while
        # its bracket extends into the owned day. The composer must retain it.
        edge = ShuddhiBoundary('overlapping_test_edge', rise-1/86400, rise-3/86400, rise+2/86400)
        window = ShuddhiInterval(edge, point(rise+.1))
        witness = DoshaWitness('edge_fixture', None, window, window, window.contains(kwargs['jd_ut1']))
        first = _finding('vishanadi', result.policy.vishanadi_profile, (witness,), result.inputs, result.policy)
        return replace(result, findings=(first, *result.findings[1:]))
    monkeypatch.setattr(owner, 'detect_muhurta_doshas', boundary_case)
    day = muhurta_doshas_for_date(date(2026, 10, 9), 20, 80, timezone='Asia/Kolkata', reader=reader)
    assert day.at(day.sunrise.jd_ut1+1/86400) is None
    assert 'overlapping_test_edge' in day.transition_bands[0].kind
    assert day.transition_bands[0].upper_jd_ut1 >= day.sunrise.jd_ut1+2/86400

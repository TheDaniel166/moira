"""Independent analytic trajectories and calendar assembly invariants."""
from dataclasses import replace
import importlib
from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade
import moira.vedic as vedic
from moira.spk_reader import get_active_reader

calendar = importlib.import_module("moira.lunar_month")


@pytest.fixture
def analytic_calendar(monkeypatch):
    reader = object()
    monkeypatch.setattr(calendar, "get_reader", lambda: reader)
    monkeypatch.setattr(calendar, "tropical_to_sidereal", lambda lon, jd, system: lon % 360)

    def set_positions(solar_rate=1.0, opening_solar=10.0, elongation=6.0):
        def position(body, jd, *, reader):
            assert get_active_reader() is reader
            sun = opening_solar + solar_rate * (jd - 999.5)
            return SimpleNamespace(longitude=(sun + (elongation + 12*(jd-1000) if body == "Moon" else 0)) % 360)
        monkeypatch.setattr(calendar, "planet_at", position)
    set_positions()
    return reader, set_positions


def test_ordinary_amanta_geometry_and_half_open_conjunction(analytic_calendar):
    reader, _ = analytic_calendar
    r = calendar.lunar_month_at(1000, reader=reader)
    assert r.status == "available"
    assert r.label == calendar.LunarMonthLabel(1, "Vaisakha", "ordinary")
    assert r.month_start.jd_ut1 == pytest.approx(999.5, abs=0.1/86400)
    assert r.month_end.jd_ut1 == pytest.approx(1029.5, abs=0.1/86400)
    assert r.paksha == "Shukla" and r.tithi_number == 1
    ingress, = r.amanta_lunation.ingresses
    assert ingress.target_degrees == 30
    assert ingress.lower_jd_ut1 <= 1019.5 <= ingress.jd_ut1
    at = calendar.lunar_month_at(999.5, reader=reader)
    assert at.amanta_lunation.start.jd_ut1 == 999.5
    before = calendar.lunar_month_at(999.5 - 1/86400, reader=reader)
    assert before.amanta_lunation.end.jd_ut1 == pytest.approx(999.5, abs=0.1/86400)


@pytest.mark.parametrize("jd,month,start,end,paksha,tithi", [
    (1000, "Vaisakha", 984.5, 1014.5, "Shukla", 1),
    (1014.5, "Jyaishtha", 1014.5, 1044.5, "Krishna", 1),
    (1015, "Jyaishtha", 1014.5, 1044.5, "Krishna", 1),
])
def test_purnimanta_ordinary_mapping(analytic_calendar, jd, month, start, end, paksha, tithi):
    reader, _ = analytic_calendar
    r = calendar.lunar_month_at(jd, reader=reader,
        policy=calendar.LunarMonthPolicy(system=calendar.LunarMonthSystem.PURNIMANTA))
    assert r.status == "available"
    assert r.label.name == month and r.paksha == paksha and r.tithi_number == tithi
    assert r.month_start.jd_ut1 == pytest.approx(start, abs=0.1/86400)
    assert r.month_end.jd_ut1 == pytest.approx(end, abs=0.1/86400)


def test_adhika_lunation_and_explicit_purnimanta_deferral(analytic_calendar):
    reader, set_positions = analytic_calendar
    set_positions(solar_rate=0.95, opening_solar=0.1)
    amanta = calendar.lunar_month_at(1000, reader=reader)
    assert amanta.label.qualifier == "adhika" and amanta.label.name == "Vaisakha"
    assert amanta.amanta_lunation.ingresses == ()
    assert amanta.next_lunation.label.name == "Vaisakha"
    purnimanta = calendar.lunar_month_at(1000, reader=reader,
        policy=calendar.LunarMonthPolicy(system=calendar.LunarMonthSystem.PURNIMANTA))
    assert purnimanta.status == "unsupported_intercalation"
    assert purnimanta.label is None and purnimanta.month_start is None
    assert purnimanta.amanta_lunation == amanta.amanta_lunation


def test_two_ingresses_retain_omitted_name_without_remapping(analytic_calendar):
    reader, set_positions = analytic_calendar
    set_positions(solar_rate=1.05, opening_solar=29.9)
    r = calendar.lunar_month_at(1000, reader=reader)
    assert r.label.qualifier == "ksaya_context"
    assert r.amanta_lunation.omitted_months == ("Jyaishtha",)
    assert [e.target_degrees for e in r.amanta_lunation.ingresses] == [30, 60]


def test_near_conjunction_ingress_is_ambiguous_not_repaired(analytic_calendar):
    reader, set_positions = analytic_calendar
    set_positions(opening_solar=30.0)
    r = calendar.lunar_month_at(1000, reader=reader)
    assert r.status == "boundary_ambiguous" and r.label is None
    assert r.amanta_lunation.uncertain_ingresses
    assert r.amanta_lunation.label is None


@pytest.mark.parametrize("jd,kind", [(999.5, "new_moon"), (1014.5, "full_moon")])
def test_requested_instant_inside_phase_bracket_retains_the_actual_evidence(analytic_calendar, jd, kind):
    reader, _ = analytic_calendar
    requested = jd - 0.02/86400
    r = calendar.lunar_month_at(requested, reader=reader)
    assert r.status == "boundary_ambiguous"
    assert r.label is None and r.month_start is None and r.month_end is None
    event, = r.uncertain_phase_boundaries
    assert event.kind == kind
    assert event.lower_jd_ut1 <= requested < event.jd_ut1
    assert event.lower_jd_ut1 <= jd <= event.jd_ut1


@pytest.mark.parametrize("rate", [10.5, 12.0, 13.9])
@pytest.mark.parametrize("target", [0.0, 180.0])
def test_nonlinear_phase_roots_have_independent_quadratic_witness(rate, target):
    # Positive acceleration, with roots at a known target on the continuous arc.
    angle = target - 5
    def fn(jd):
        return (angle + rate*jd + 0.1*jd*jd) % 360
    roots = calendar._angular_boundaries(0, 2, fn, 180, 0.01, True)
    expected = (-rate + (rate*rate + 2.0)**0.5)/0.2
    event, = roots
    assert event.target_degrees == target
    assert event.lower_jd_ut1 <= expected <= event.jd_ut1
    assert (event.jd_ut1 - event.lower_jd_ut1)*86400 <= 0.01


@pytest.mark.parametrize("trajectory", [lambda jd: 1, lambda jd: (-jd) % 360,
                                        lambda jd: (100*jd) % 360])
def test_invalid_forward_trajectory_fails(trajectory):
    with pytest.raises(RuntimeError, match="angular bound"):
        calendar._angular_boundaries(0, 2, trajectory, 180, 0.1, True)


@pytest.mark.parametrize("bad", [True, "2451545", float("nan"), float("inf"), 10_000_001, -10_000_001])
def test_invalid_jd_fails_before_acquiring_reader(monkeypatch, bad):
    monkeypatch.setattr(calendar, "get_reader", lambda: pytest.fail("must validate first"))
    with pytest.raises((ValueError, TypeError)):
        calendar.lunar_month_at(bad)


@pytest.mark.parametrize("kwargs", [dict(system="amanta"), dict(system=True),
    dict(ayanamsa_system="fictional"), dict(ayanamsa_system=True),
    dict(solver_tolerance_seconds=True), dict(solver_tolerance_seconds="0.1"),
    dict(solver_tolerance_seconds=float("nan")), dict(solver_tolerance_seconds=0),
    dict(solver_tolerance_seconds=2)])
def test_invalid_policy_is_rejected(kwargs):
    with pytest.raises((TypeError, ValueError)):
        calendar.LunarMonthPolicy(**kwargs)


def test_policy_normalizes_existing_ayanamsa_and_rejects_wrong_vessel(monkeypatch):
    assert calendar.LunarMonthPolicy(ayanamsa_system="LAHIRI").ayanamsa_system == "Lahiri"
    monkeypatch.setattr(calendar, "get_reader", lambda: pytest.fail("must validate first"))
    with pytest.raises(TypeError, match="policy"):
        calendar.lunar_month_at(1000, policy={})


def test_reader_restored_on_success_and_failure(analytic_calendar, monkeypatch):
    reader, _ = analytic_calendar
    before = get_active_reader()
    calendar.lunar_month_at(1000, reader=reader)
    assert get_active_reader() is before
    def fail(*args, **kwargs):
        assert get_active_reader() is reader
        raise RuntimeError("resource failure")
    monkeypatch.setattr(calendar, "planet_at", fail)
    with pytest.raises(RuntimeError, match="resource failure"):
        calendar.lunar_month_at(1000, reader=reader)
    assert get_active_reader() is before


def test_public_identity_and_facade_reader_binding(analytic_calendar):
    reader, _ = analytic_calendar
    for name in calendar.__all__:
        assert getattr(moira, name) is getattr(calendar, name)
        assert getattr(facade, name) is getattr(calendar, name)
        assert getattr(vedic, name) is getattr(calendar, name)
        assert name in moira.__all__ and name in facade.__all__ and name in vedic.__all__
    engine = SimpleNamespace(_reader=reader)
    assert moira.Moira.lunar_month_at(engine, 1000) == calendar.lunar_month_at(1000, reader=reader)


def test_vessels_reject_inconsistent_claims(analytic_calendar):
    reader, _ = analytic_calendar
    r = calendar.lunar_month_at(1000, reader=reader)
    for changes in (dict(label=None), dict(unavailable_reasons=("false",)),
                    dict(status="other"), dict(tithi_number=True),
                    dict(month_end=r.month_start), dict(next_lunation=r.amanta_lunation),
                    dict(status="boundary_ambiguous", label=None, month_start=None,
                         month_end=None, unavailable_reasons=("phase_or_ingress_brackets_overlap",))):
        with pytest.raises(ValueError):
            replace(r, **changes)
    for changes in (dict(omitted_months=("Jyaishtha",)), dict(label=None),
                    dict(solar_rashi_at_start=True), dict(ingresses=())):
        with pytest.raises(ValueError):
            replace(r.amanta_lunation, **changes)
    for args in ((True, "Vaisakha", "ordinary"), (1, "wrong", "ordinary"),
                 (1, "Vaisakha", "wrong")):
        with pytest.raises(ValueError):
            calendar.LunarMonthLabel(*args)


def test_boundary_vessel_guards():
    for args in (("new_moon", 180, 0, 1), ("full_moon", 0, 0, 1),
                 ("solar_ingress", 31, 0, 1), ("other", 0, 0, 1),
                 ("new_moon", 0, 1, 0), ("new_moon", 0, float("nan"), 1),
                 ("new_moon", 0, 0, 2/86400)):
        with pytest.raises(ValueError):
            calendar.CalendarBoundary(*args)

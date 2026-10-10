"""Daily coverage invariants and analytic boundary witnesses, no kernels.

Synthetic positions are controlled angular trajectories, not astronomy oracles.
Real resources and institutional timing checks live in the integration slice.
"""
from datetime import date, datetime, timedelta, timezone
from dataclasses import replace
from types import SimpleNamespace
import importlib

import pytest

import moira
import moira.facade as facade
import moira.vedic as vedic
from moira.julian import jd_from_datetime
from moira.spk_reader import get_active_reader

daily = importlib.import_module("moira.daily_panchanga")
sidereal = importlib.import_module("moira.sidereal")


@pytest.fixture
def analytic_day(monkeypatch):
    anchor = jd_from_datetime(datetime(2000, 1, 2, 6, tzinfo=timezone.utc))
    reader = object()
    monkeypatch.setattr(daily, "utc_to_ut1", lambda jd: jd)
    monkeypatch.setattr(daily, "_ut1_to_utc", lambda jd: jd)
    monkeypatch.setattr(daily, "get_reader", lambda: reader)
    monkeypatch.setattr(daily, "tropical_to_sidereal", lambda lon, jd, system: lon % 360)
    monkeypatch.setattr(sidereal, "tropical_to_sidereal", lambda lon, jd, system: lon % 360)

    def positions(*, elongation=348.0, lunar_rate=14.0, solar_rate=1.0):
        def lookup(body, jd, *, reader):
            assert get_active_reader() is reader
            elapsed = jd - anchor
            lon = (lunar_rate * elapsed + elongation) if body == "Moon" else solar_rate * elapsed
            return SimpleNamespace(longitude=lon % 360)
        monkeypatch.setattr(daily, "planet_at", lookup)

    def events(body, start, lat, lon, *, altitude):
        assert get_active_reader() is reader
        day_start = int(start - 0.5) + 0.5
        candidates = {"Rise": day_start + 0.25, "Set": day_start + 0.75}
        return {key: value if value >= start else value + 1 for key, value in candidates.items()}

    monkeypatch.setattr(daily, "find_phenomena", events)
    positions()
    return anchor, reader, positions


def test_wrap_boundaries_are_solved_and_all_coverage_is_contiguous(analytic_day):
    anchor, reader, _ = analytic_day
    previous = get_active_reader()
    result = daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC", reader=reader)
    assert get_active_reader() is previous
    assert result.at_sunrise.vara_lord == "Sun"
    limbs = {limb.limb: limb for limb in result.limbs}
    tithi = limbs["tithi"]
    assert [part.index for part in tithi.intervals] == [29, 0]
    assert tithi.intervals[0].ending.jd_ut1 == pytest.approx(anchor + 12 / 13, abs=0.1 / 86400)
    assert tithi.intervals[1].ending.jd_ut1 > result.next_sunrise.jd_ut1
    assert limbs["karana"].skipped_at_sunrise_indices == (59,)
    for limb in result.limbs:
        assert limb.intervals[0].coverage_start == result.sunrise
        assert limb.intervals[-1].coverage_end == result.next_sunrise
        for left, right in zip(limb.intervals, limb.intervals[1:]):
            assert left.coverage_end == right.coverage_start
        for part in limb.intervals:
            assert part.coverage_start.jd_ut1 < part.coverage_end.jd_ut1 <= part.ending.jd_ut1


def test_repeated_limb_preserves_actual_ending_outside_the_day(analytic_day):
    _, _, positions = analytic_day
    positions(elongation=0.0, lunar_rate=11.0, solar_rate=1.0)
    result = daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")
    tithi = result.limbs[0]
    assert tithi.repeated_at_next_sunrise
    assert len(tithi.intervals) == 1
    assert tithi.intervals[0].ending.jd_ut1 > result.next_sunrise.jd_ut1
    assert tithi.skipped_at_sunrise_indices == ()


def test_exact_sunrise_boundaries_belong_to_entered_limb(analytic_day):
    anchor, _, positions = analytic_day
    positions(elongation=0.0, lunar_rate=13.0, solar_rate=1.0)
    result = daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")
    tithi = result.limbs[0]
    assert tithi.index_at_sunrise == 0
    assert tithi.index_at_next_sunrise == 1
    assert len(tithi.intervals) == 1
    assert tithi.intervals[0].ending.jd_ut1 == pytest.approx(anchor + 1, abs=0.1 / 86400)
    assert not tithi.repeated_at_next_sunrise
    assert not tithi.skipped_at_sunrise_indices


def test_daily_vessels_reject_inconsistent_coverage_and_claims(analytic_day):
    r = daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")
    with pytest.raises(ValueError, match="nonempty"):
        replace(r.limbs[0].intervals[0], coverage_end=r.sunrise)
    with pytest.raises(ValueError, match="repeated/skipped"):
        replace(r.limbs[0], repeated_at_next_sunrise=True)
    with pytest.raises(ValueError, match="all four"):
        replace(r, limbs=r.limbs[:1])
    with pytest.raises(ValueError, match="fabricate"):
        replace(r, status="unavailable", unavailable_reasons=("sunrise_absent",))


def test_missing_sunrise_is_unavailable_without_fabricated_limbs(analytic_day, monkeypatch):
    monkeypatch.setattr(daily, "find_phenomena", lambda *args, **kwargs: {})
    result = daily.daily_panchanga(date(2000, 1, 2), 90, 0, timezone="UTC")
    assert result.status == "unavailable"
    assert result.unavailable_reasons == ("sunrise_absent", "next_sunrise_absent")
    assert result.at_sunrise is None and result.limbs == ()
    assert result.sunrise is None and result.next_sunrise is None


def test_only_next_sunrise_absent_retains_opening_solar_evidence(analytic_day, monkeypatch):
    anchor, _, _ = analytic_day
    monkeypatch.setattr(daily, "find_phenomena", lambda *args, **kwargs: {"Rise": anchor})
    r = daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")
    assert r.status == "unavailable" and r.unavailable_reasons == ("next_sunrise_absent",)
    assert r.sunrise is not None and r.next_sunrise is None
    assert r.at_sunrise is None and not r.limbs


def test_multiple_civil_date_sunrises_are_preserved_as_ambiguous(analytic_day, monkeypatch):
    anchor, _, _ = analytic_day
    def events(body, start, lat, lon, *, altitude):
        return {"Rise": anchor if start < anchor else anchor + 0.4}
    monkeypatch.setattr(daily, "find_phenomena", events)
    r = daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")
    assert len(r.solar_date.sunrises) == 2
    assert r.status == "unavailable" and "sunrise_ambiguous" in r.unavailable_reasons
    assert r.at_sunrise is None and r.sunrise is None


def test_solar_search_and_phase_failures_restore_reader(analytic_day, monkeypatch):
    _, reader, _ = analytic_day
    previous = get_active_reader()
    def fail(*args, **kwargs):
        assert get_active_reader() is reader
        raise RuntimeError("resource failure")
    monkeypatch.setattr(daily, "find_phenomena", fail)
    with pytest.raises(RuntimeError, match="resource failure"):
        daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC", reader=reader)
    assert get_active_reader() is previous


def test_non_monotonic_trajectory_is_a_search_failure(analytic_day):
    _, _, positions = analytic_day
    positions(lunar_rate=-10.0)
    with pytest.raises(RuntimeError, match="forward phase"):
        daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")


def test_root_uses_moving_phase_instead_of_constant_speed(analytic_day, monkeypatch):
    anchor, _, _ = analytic_day
    def lookup(body, jd, *, reader):
        t = jd - anchor
        return SimpleNamespace(longitude=(t if body == "Sun" else t + 8 * t * t) % 360)
    monkeypatch.setattr(daily, "planet_at", lookup)
    r = daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")
    # Elongation=8*t^2, so the first 12-degree boundary is sqrt(12/8) days.
    assert r.limbs[0].intervals[0].ending.jd_ut1 == pytest.approx(anchor + (12 / 8) ** 0.5, abs=0.1 / 86400)


@pytest.mark.parametrize("elongation", [0.0, 11.999, 12.0, 179.999, 180.0, 359.999, 360.0])
@pytest.mark.parametrize("rate", [10.0, 13.0, 16.0])
def test_analytic_trajectory_sweep_keeps_each_boundary_and_day_cover(analytic_day, elongation, rate):
    anchor, _, positions = analytic_day
    positions(elongation=elongation, lunar_rate=rate)
    r = daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")
    for limb, (_, _, count) in zip(r.limbs, daily._LIMBS):
        assert limb.intervals[0].coverage_start.jd_ut1 == anchor
        assert limb.intervals[-1].coverage_end.jd_ut1 == anchor + 1
        for part in limb.intervals:
            root = part.ending.jd_ut1
            for offset, index in ((-1, part.index), (1, (part.index + 1) % count)):
                jd = root + offset / 86400
                snapshot = daily.panchanga_at((jd - anchor) % 360,
                    (elongation + rate * (jd - anchor)) % 360, jd)
                assert daily._limb_identity(snapshot, limb.limb)[0] == index


def test_search_cap_fails_without_a_fake_limb_ending(analytic_day):
    _, _, positions = analytic_day
    positions(lunar_rate=1.01, solar_rate=1.0)
    with pytest.raises(RuntimeError, match="72-hour"):
        daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone="UTC")


@pytest.mark.parametrize("day", ["2000-01-02", datetime(2000, 1, 2), date(1, 1, 1), date(9999, 12, 31)])
def test_invalid_date_rejected_before_reader(monkeypatch, day):
    monkeypatch.setattr(daily, "get_reader", lambda: pytest.fail("reader acquired"))
    with pytest.raises((ValueError, TypeError)):
        daily.daily_panchanga(day, 0, 0, timezone="UTC")


@pytest.mark.parametrize("value", [True, "10", float("nan"), float("inf"), -91, 91])
def test_invalid_latitude_fails_before_resource_acquisition(monkeypatch, value):
    monkeypatch.setattr(daily, "get_reader", lambda: pytest.fail("reader acquired"))
    with pytest.raises((ValueError, TypeError)):
        daily.daily_panchanga(date(2000, 1, 2), value, 0, timezone="UTC")


@pytest.mark.parametrize("value", [True, "0.1", 0, 2, float("nan")])
def test_policy_rejects_invalid_solver_tolerances(value):
    with pytest.raises((ValueError, TypeError)):
        daily.DailyPanchangaPolicy(solver_tolerance_seconds=value)


@pytest.mark.parametrize("zone", ["", "Missing/Zone", "UTC+25:00", "UTC+00:61"])
def test_invalid_timezone_rejected_before_reader(monkeypatch, zone):
    monkeypatch.setattr(daily, "get_reader", lambda: pytest.fail("reader acquired"))
    with pytest.raises(ValueError):
        daily.daily_panchanga(date(2000, 1, 2), 0, 0, timezone=zone)


@pytest.mark.parametrize("day,hours", [(date(2026, 3, 8), 23), (date(2026, 11, 1), 25)])
def test_dst_bounds_are_local_civil_dates(day, hours, monkeypatch):
    zone = daily._resolve_timezone("America/New_York")
    start, end = daily._civil_bounds(day, zone)
    assert (end - start) * 24 == pytest.approx(hours, abs=1e-5)
    monkeypatch.setattr(daily, "find_phenomena", lambda *args, **kwargs: {})
    solar = daily._solar_date(day, zone, 0, 0, 0)
    assert solar.civil_start.local.date() == day
    assert solar.civil_end.local.date() == day + timedelta(days=1)
    assert solar.civil_start.local.hour == solar.civil_end.local.hour == 0


def test_midnight_gap_is_normalized_and_skipped_date_rejected(monkeypatch):
    zone = daily._resolve_timezone("America/Santiago")
    monkeypatch.setattr(daily, "find_phenomena", lambda *args, **kwargs: {})
    solar = daily._solar_date(date(2026, 9, 6), zone, 0, 0, 0)
    assert solar.civil_start.local.hour == 1
    with pytest.raises(ValueError, match="skipped"):
        daily._civil_bounds(date(2011, 12, 30), daily._resolve_timezone("Pacific/Apia"))


def test_public_exports_share_canonical_identity():
    for name in daily.__all__:
        for surface in (moira, facade, vedic):
            assert name in surface.__all__
            assert getattr(surface, name) is getattr(daily, name)


def test_facade_passes_its_own_reader(monkeypatch):
    engine = SimpleNamespace(_reader=object())
    sentinel = object()
    def compute(day, lat, lon, *, timezone, policy, reader):
        assert reader is engine._reader
        assert (day, lat, lon, timezone, policy) == (date(2026, 9, 22), 23, 82, "UTC", None)
        return sentinel
    monkeypatch.setattr(daily, "daily_panchanga", compute)
    assert facade.Moira.daily_panchanga(engine, date(2026, 9, 22), 23, 82, timezone="UTC") is sentinel

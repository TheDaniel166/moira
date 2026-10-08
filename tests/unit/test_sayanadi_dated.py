"""Clock ownership, uncertainty and serving-reader composition."""
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from moira.avasthas import SayanadiName
from moira.spk_reader import get_active_reader, use_reader_override
from sayanadi_support import install_analytic_birth


@pytest.fixture
def analytic_birth(monkeypatch):
    return install_analytic_birth(monkeypatch)


@pytest.mark.parametrize("hour,ordinal,day", [(5, 58, 1), (6, 1, 2), (12, 15, 2), (23, 43, 2)])
def test_previous_sunrise_source_clock_and_zero_boundary(analytic_birth, hour, ordinal, day):
    dated, reader, calls = analytic_birth
    previous_reader = get_active_reader()
    result = dated.avasthas_for_datetime(datetime(2000, 1, 2, hour, tzinfo=timezone.utc), 0, 0,
                                        name=SayanadiName(sound="स"), reader=reader)
    assert get_active_reader() is previous_reader
    assert result.status == "evaluated" and result.ghati_candidates == (ordinal,)
    assert result.sunrise.moment.utc.day == day
    assert result.sunrise.lower_jd_ut1 == result.sunrise.upper_jd_ut1
    assert result.sunrise.moment.jd_ut1 <= result.birth_jd_ut1 < result.next_sunrise.moment.jd_ut1
    assert result.chart.sayanadi_context.ghati.basis == "sunrise_derived_ut1"
    assert len([call for call in calls if call[0] == "epoch"]) == 1


def test_uncertain_ghati_and_sunrise_ownership_do_not_claim_a_chart(analytic_birth, monkeypatch):
    dated, reader, calls = analytic_birth
    original = dated._refine_sunrise

    def wide(estimate, *args):
        result = original(estimate, *args)
        return replace(result, lower_jd_ut1=estimate-0.2/86400, upper_jd_ut1=estimate+0.2/86400)

    monkeypatch.setattr(dated, "_refine_sunrise", wide)
    name = SayanadiName(value=4)
    result = dated.avasthas_for_datetime(datetime(2000, 1, 2, 6, 24, tzinfo=timezone.utc), 0, 0, name=name, reader=reader)
    assert result.status == "unavailable" and result.ghati_candidates == (1, 2)
    assert result.unavailable_reasons == ("ghati_ordinal_uncertain_inside_sunrise_bracket",)
    assert result.chart is None and result.epoch is None
    result = dated.avasthas_for_datetime(datetime(2000, 1, 2, 6, tzinfo=timezone.utc), 0, 0, name=name, reader=reader)
    assert result.unavailable_reasons == ("sunrise_ownership_uncertain",)
    assert not any(c[0] == "epoch" for c in calls)


def test_missing_sunrise_and_reader_override_restoration(analytic_birth, monkeypatch):
    dated, reader, _ = analytic_birth
    monkeypatch.setattr(dated, "_solar_date", lambda *args: SimpleNamespace(sunrises=()))
    outer = object()
    with use_reader_override(outer):
        result = dated.avasthas_for_datetime(datetime(2000, 1, 2, 12, tzinfo=timezone.utc), 80, 0,
                                            name=SayanadiName(value=4), reader=reader)
        assert get_active_reader() is outer
    assert result.status == "unavailable" and result.chart is None


@pytest.mark.parametrize("nodes,afflictors", [(False, False), (True, False), (False, True), (True, True)])
def test_node_evaluation_is_independent_from_lajjitadi(analytic_birth, nodes, afflictors):
    dated, reader, calls = analytic_birth
    r = dated.avasthas_for_datetime(datetime(2000, 1, 2, 12, tzinfo=timezone.utc), 0, 0,
                                   name=SayanadiName(value=4), reader=reader,
                                   policy=dated.SayanadiBirthPolicy(evaluate_nodes=nodes, lajjitadi_nodes=afflictors))
    assert set(r.chart.sayanadi_nodes) == ({"Rahu", "Ketu"} if nodes else set())
    assert set(r.node_longitudes) == ({"Rahu", "Ketu"} if nodes or afflictors else set())
    assert bool([c for c in calls if c[0] == "true_node"]) == (nodes or afflictors)
    assert r.chart.sayanadi_context.evaluate_nodes is nodes
    for pa in r.chart.planets.values():
        assert pa.sayanadi.trace.context is r.chart.sayanadi_context


def test_offsets_and_named_zone_identify_same_instant(analytic_birth):
    dated, reader, _ = analytic_birth
    kwargs = dict(name=SayanadiName(value=4), reader=reader, timezone_name="America/New_York")
    a = dated.avasthas_for_datetime(datetime.fromisoformat("2026-03-08T12:00:00+00:00"), 40.73, -73.92, **kwargs)
    b = dated.avasthas_for_datetime(datetime.fromisoformat("2026-03-08T08:00:00-04:00"), 40.73, -73.92, **kwargs)
    assert a.birth_jd_ut1 == b.birth_jd_ut1 and a.ghati_candidates == b.ghati_candidates
    assert a.chart == b.chart and a.sunrise == b.sunrise


def test_nonexistent_zoneinfo_birth_fails_before_resources(analytic_birth):
    dated, _, calls = analytic_birth
    with pytest.raises(ValueError, match="nonexistent"):
        dated.avasthas_for_datetime(datetime(2026, 3, 8, 2, 30, tzinfo=ZoneInfo("America/New_York")),
                                    40.73, -73.92, name=SayanadiName(value=4))
    assert calls == []


@pytest.mark.parametrize("dt,lat,lon", [
    (datetime(2000, 1, 2), 0, 0), (True, 0, 0),
    (datetime(2000, 1, 2, tzinfo=timezone.utc), True, 0),
    (datetime(2000, 1, 2, tzinfo=timezone.utc), 90, 0),
    (datetime(2000, 1, 2, tzinfo=timezone.utc), 0, 181),
])
def test_invalid_birth_inputs_fail_before_resources(analytic_birth, dt, lat, lon):
    dated, _, calls = analytic_birth
    with pytest.raises((ValueError, TypeError)):
        dated.avasthas_for_datetime(dt, lat, lon, name=SayanadiName(value=4))
    assert calls == []

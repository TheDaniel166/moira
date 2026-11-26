"""Synthetic crossing and interruption witnesses for the bounded return scan."""

from types import SimpleNamespace

import pytest

from moira import stations, transits
from moira.cycles import bounded_return_series
from moira.spk_reader import OutOfRangeError


def test_station_split_detects_both_crossings_inside_one_cell(monkeypatch):
    monkeypatch.setattr(stations, "find_stations", lambda *args, **kwargs: [SimpleNamespace(jd_ut=1000.25)])
    monkeypatch.setattr(
        transits, "_lon",
        lambda body, jd, reader: body if isinstance(body, float) else 31 - 16 * (jd - 1000.25) ** 2,
    )
    result = bounded_return_series("Mercury", 30.99, 1000, 1000.5, reader=object())
    assert result.station_count == 1
    assert [event.direction for event in result.events] == ["direct", "retrograde"]
    assert [event.jd_ut1 for event in result.events] == pytest.approx([1000.225, 1000.275], abs=1e-6)


def test_endpoint_ownership_and_coverage_failure(monkeypatch):
    monkeypatch.setattr(stations, "find_stations", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        transits, "_lon", lambda body, jd, reader: body if isinstance(body, float) else jd - 970,
    )
    initial = bounded_return_series("Sun", 30.5, 1000, 1000.5, reader=object())
    following = bounded_return_series("Sun", 30.5, 1000.5, 1001, reader=object())
    assert [event.jd_ut1 for event in initial.events] == [1000.5]
    assert following.events == ()

    def failed_position(body, jd, reader):
        raise OutOfRangeError("fixture coverage", out_of_range_times=True)

    monkeypatch.setattr(transits, "_lon", failed_position)
    with pytest.raises(OutOfRangeError, match="fixture coverage"):
        bounded_return_series("Sun", 30, 1000, 1001, reader=object())


def test_station_on_ending_longitude_is_a_touch(monkeypatch):
    monkeypatch.setattr(stations, "find_stations", lambda *args, **kwargs: [])
    monkeypatch.setattr(stations, "_speed", lambda body, jd, reader: -32 * (jd - 1000.5))
    monkeypatch.setattr(transits, "_lon", lambda body, jd, reader: 31 - 16 * (jd - 1000.5) ** 2)
    result = bounded_return_series("Mercury", 31, 1000, 1000.5, reader=object())
    assert result.events == ()

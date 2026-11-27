"""Printed Special Lagna results and sunrise ownership."""

from datetime import date, datetime, timezone
import importlib
from types import SimpleNamespace

import pytest

from moira.daily_panchanga import PanchangaMoment
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.special_lagnas import special_lagnas, special_lagnas_for_datetime
from moira.spk_reader import get_reader

module = importlib.import_module("moira.special_lagnas")


@pytest.mark.parametrize(
    "sun,seconds,expected",
    [
        # BPHS 5.2–8, Santhanam's example, pp. 62–64.
        (132, 18_000, (207, 282, 147)),
        # Rao examples 7–9. Bhava is independently corrected at 15°/hour.
        (294 + 17 / 60, 766 * 60, (125 + 47 / 60, 317 + 17 / 60, 171 + 47 / 60)),
        # Rao exercise 8 and its printed Hora/Ghati answer. Bhava is derived.
        (42 + 11 / 60, 75_150, (355 + 18.5 / 60, 308 + 26 / 60, 167 + 48.5 / 60)),
        (359.5, 120, (0, 0.5, 2)),
        (132, 0, (132, 132, 132)),
    ],
)
def test_worked_lagna_arithmetic(sun, seconds, expected):
    result = special_lagnas(sun, seconds)
    actual = (result.bhava_longitude, result.hora_longitude, result.ghati_longitude)
    assert actual == pytest.approx(expected, abs=1e-12, rel=0)


@pytest.mark.parametrize("sun,elapsed", [(True, 1), (360, 1), (-1, 1), (0, True), (0, -1),
                                        (0, float("inf")), (0, 10**400), (float("nan"), 0)])
def test_direct_inputs_are_finite_and_strict(sun, elapsed):
    with pytest.raises((TypeError, ValueError)):
        special_lagnas(sun, elapsed)


@pytest.mark.parametrize("hour,anchor", [(5, date(2026, 9, 21)), (6, date(2026, 9, 22)),
                                         (18, date(2026, 9, 22))])
def test_birth_owns_the_preceding_or_equal_sunrise(monkeypatch, hour, anchor):
    reader = object()
    searched = []
    seeds = []

    def solar(day, zone, lat, lng, altitude):
        assert get_reader() is reader
        searched.append(day)
        utc = datetime.combine(day, datetime.min.time(), timezone.utc).replace(hour=6)
        jd = utc_to_ut1(jd_from_datetime(utc))
        return SimpleNamespace(sunrises=(PanchangaMoment(jd, utc, utc),))

    def planet_at(body, jd, *, reader):
        seeds.append(jd)
        assert body == "Sun" and reader is get_reader()
        return SimpleNamespace(longitude=132.0)

    monkeypatch.setattr(module, "_solar_date", solar)
    monkeypatch.setattr(module, "planet_at", planet_at)
    monkeypatch.setattr(module, "tropical_to_sidereal", lambda sun, jd, system: sun)
    birth = datetime(2026, 9, 22, hour, tzinfo=timezone.utc)
    result = special_lagnas_for_datetime(birth, 20, 0, timezone="UTC", reader=reader)
    assert result.status == "available"
    assert result.sunrise.utc.date() == anchor
    assert seeds == [result.sunrise.jd_ut1]
    assert len(searched) == (2 if hour < 6 else 1)
    if hour == 6:
        assert result.result.elapsed_seconds == 0
        assert result.result.bhava_longitude == 132.0


@pytest.mark.parametrize("count,reason", [(0, "sunrise_absent"), (2, "sunrise_ambiguous")])
def test_solar_absence_and_ambiguity_remain_explicit(monkeypatch, count, reason):
    birth = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
    moment = PanchangaMoment(2461306.0, birth, birth)
    monkeypatch.setattr(module, "_solar_date", lambda *_: SimpleNamespace(sunrises=(moment,) * count))
    result = special_lagnas_for_datetime(birth, 30, 0, timezone="UTC", reader=object())
    assert result.status == "unavailable" and result.unavailable_reason == reason
    assert result.sunrise is None and result.result is None
    assert len(result.candidate_sunrises) == count


def test_birth_instant_underflow_is_a_validation_error():
    birth = datetime.fromisoformat("0001-01-01T00:00:00+05:30")
    with pytest.raises(ValueError, match="outside the representable civil calendar"):
        special_lagnas_for_datetime(birth, 20, 82.5, timezone="UTC+05:30", reader=object())

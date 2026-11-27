"""Independent print-derived fixtures for the second Vedic expansion wave."""
from datetime import datetime, timedelta
from math import inf, nextafter

import pytest

from moira import choghadiya_from_solar_times, khara_divisions, prashna_sphutas
from moira.julian import jd_from_datetime
from moira.upagrahas import _mandi_defining_jd


def test_charak_chart_and_raman_moon_example():
    # Charak's Jatakalankara Chart V-1, pp. 133–134. Virgo Lagna and Leo Moon.
    result = khara_divisions(120 + 24 + 31 / 60, 150 + 27 + 31 / 60)
    navamsa = result.navamsa_64
    assert navamsa.seed.varga_sign == "Scorpio"
    assert navamsa.target.zodiac_sign == "Pisces"
    assert navamsa.target.sign_ordinal == 8
    assert (navamsa.target.varga_sign, navamsa.target.varga_lord) == ("Aquarius", "Saturn")
    drekkana = result.drekkana_22
    assert (drekkana.target.zodiac_sign, drekkana.target.sign_ordinal) == ("Aries", 3)
    assert (drekkana.target.arc_start_arcseconds, drekkana.target.arc_end_arcseconds) == (72000, 108000)
    assert (drekkana.target.varga_sign, drekkana.target.varga_lord) == ("Sagittarius", "Jupiter")
    # Raman p. 286 starts from the projected Leo D9. Aries 15° is one witness.
    lunar = khara_divisions(15, 0).navamsa_64
    assert (lunar.seed.varga_sign, lunar.target.varga_sign, lunar.target.varga_lord) == ("Leo", "Scorpio", "Mars")


@pytest.mark.parametrize("division,count,field", [(3, 22, "drekkana_22"), (9, 64, "navamsa_64")])
def test_every_numbered_cell_matches_an_inclusive_count(division, count, field):
    # Independent ring walk, explicit trinal D3 and modality-based D9 projection.
    ring = [(sign, ordinal) for sign in range(12) for ordinal in range(division)]
    signs = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
             "Sagittarius", "Capricorn", "Aquarius", "Pisces")
    for index, (sign, ordinal) in enumerate(ring):
        value = 30 * sign + 30 * (ordinal + 0.5) / division
        result = getattr(khara_divisions(value, value), field)
        target = (ring[index:] + ring[:index])[count - 1]
        target_index = ring.index(target)
        target_sign, target_ordinal = target
        projection = (target_sign + 4 * target_ordinal if division == 3
                      else target_sign + (0, 8, 4)[target_sign % 3] + target_ordinal) % 12
        assert result.target.zodiac_ordinal == target_index + 1
        assert result.target.sign_ordinal == ordinal + 1
        assert result.target.varga_sign == signs[projection]
        assert result.target.arc_start_arcseconds * division == target_index * 108000


def test_numbered_cell_edges_use_exact_partition_and_wrap():
    assert khara_divisions(nextafter(10.0, -inf), nextafter(10.0, -inf)).navamsa_64.seed.sign_ordinal == 3
    exact = khara_divisions(10.0, 10.0)
    assert exact.navamsa_64.seed.sign_ordinal == 4
    assert exact.drekkana_22.seed.sign_ordinal == 2
    assert khara_divisions(360.0, 360.0) == khara_divisions(0.0, 0.0)


def test_raman_printed_sphuta_example_and_exact_wrap():
    result = prashna_sphutas(lagna=43 + 9 / 60, moon=18 + 29 / 60, gulika=64 + 26 / 60,
                             sun=301 + 12 / 60, rahu=6 + 9 / 60)
    assert (result.tri, result.chatus, result.pancha) == pytest.approx((126 + 4 / 60, 67 + 16 / 60, 73 + 25 / 60))
    result = prashna_sphutas(lagna=150, moon=150, gulika=60, sun=nextafter(360, 0), rahu=2**-45)
    assert result.tri == 0
    assert result.chatus == result.pancha == nextafter(360, 0)


def test_raman_printed_day_and_night_mandi_clocks():
    # Friday 6 ghatis of a 30-ghati day and Saturday 14 of a 34-ghati night.
    assert _mandi_defining_jd(5, True, 0, 30) == 6
    assert _mandi_defining_jd(6, False, 0, 34) == pytest.approx(15.8666666667)


# Sirohi 1916, pp. 232–233. Each literal row is one slot, Sun through Sat.
_DAY = (
    "U A R L S C K", "C K U A R L S", "L S C K U A R", "A R L S C K U",
    "K U A R L S C", "S C K U A R L", "R L S C K U A", "U A R L S C K",
)
_NIGHT = (
    "S C K U A R L", "A R L S C K U", "C K U A R L S", "R L S C K U A",
    "K U A R L S C", "L S C K U A R", "U A R L S C K", "S C K U A R L",
)
_NAMES = dict(U="Udvega", A="Amrita", R="Roga", L="Labha", S="Shubha", C="Chala", K="Kala")


@pytest.mark.parametrize("weekday", range(7))
def test_all_112_printed_choghadiya_names(weekday):
    result = choghadiya_from_solar_times(weekday=weekday, sunrise_jd_ut1=0, sunset_jd_ut1=8, next_sunrise_jd_ut1=24)
    column = (weekday + 1) % 7
    for intervals, printed, origin, step in ((result.day, _DAY, 0, 1), (result.night, _NIGHT, 8, 2)):
        for i, (interval, row) in enumerate(zip(intervals, printed, strict=True)):
            assert interval.name == _NAMES[row.split()[column]]
            assert interval.ordinal == i + 1
            assert (interval.start_jd_ut1, interval.end_jd_ut1) == (origin + i * step, origin + (i + 1) * step)


def test_durban_published_choghadiya_starts_and_midnight():
    # Durban Panchang, 3–4 February 2026, pp. 14–15, clocks as printed.
    times = ("05:27:39", "07:08:12", "08:48:44", "10:29:17", "12:09:49", "13:50:21", "15:30:54", "17:11:26",
             "18:51:58", "20:11:32", "21:31:06", "22:50:41", "00:10:15", "01:29:49", "02:49:23", "04:08:57",
             "05:28:31")
    civil = tuple(datetime.fromisoformat(f"2026-02-03T{t}+02:00") + timedelta(days=i >= 12)
                  for i, t in enumerate(times))
    # Constant-offset published clocks serve as test anchors, independent of the solar solver.
    jds = tuple(jd_from_datetime(t) for t in civil)
    result = choghadiya_from_solar_times(weekday=1, sunrise_jd_ut1=jds[0], sunset_jd_ut1=jds[8],
                                        next_sunrise_jd_ut1=jds[-1])
    intervals = result.day + result.night
    assert max(abs(x.start_jd_ut1 - expected) * 86400 for x, expected in zip(intervals, jds[:-1], strict=True)) < 1
    assert intervals[12].name == "Amrita"
    assert intervals[-1].end_jd_ut1 == jds[-1]


@pytest.mark.parametrize("values", [(0, 0, 1), (0, 2, 1), (0, inf, 1), (1, nextafter(1.0, inf), 2)])
def test_choghadiya_rejects_unusable_anchors(values):
    with pytest.raises(ValueError):
        choghadiya_from_solar_times(weekday=0, sunrise_jd_ut1=values[0], sunset_jd_ut1=values[1],
                                    next_sunrise_jd_ut1=values[2])

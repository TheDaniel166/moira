"""Rath's Tables 10–14, 20 and 25 as independent timing and direction witnesses."""
import pytest

from moira import active_narayana, narayana_dasha
from moira.narayana import _duration, _major_order

# Rath, printed p. 95, Chart 17. Signs and degrees are transcribed from the chart.
WADIYAR = {
    "Sun": 30 + 21 + 41/60, "Moon": 180 + 1 + 29/60, "Mars": 120 + 7 + 26/60,
    "Mercury": 30 + 1 + 15/60, "Jupiter": 100, "Venus": 90 + 1 + 26/60,
    "Saturn": 30 + 21 + 24/60, "Rahu": 150 + 28 + 9/60, "Ketu": 330 + 28 + 9/60,
}


@pytest.mark.parametrize("seed,exception,numbers", [
    (0, "ordinary", [1,2,3,4,5,6,7,8,9,10,11,12]),
    (1, "ordinary", [2,9,4,11,6,1,8,3,10,5,12,7]),
    (11, "ordinary", [12,4,8,9,1,5,6,10,2,3,7,11]),
    (7, "saturn", [8,9,10,11,12,1,2,3,4,5,6,7]),
    (0, "ketu", [1,12,11,10,9,8,7,6,5,4,3,2]),
    (1, "ketu", [2,7,12,5,10,3,8,1,6,11,4,9]),
    (7, "ketu", [8,1,6,11,4,9,2,7,12,5,10,3]),
    (11, "ketu", [12,8,4,3,11,7,6,2,10,9,5,1]),
])
def test_printed_major_orders(seed, exception, numbers):
    actual, _ = _major_order(seed, exception)
    assert actual == tuple(x - 1 for x in numbers)


def test_wadiyar_major_and_antardasha_obey_printed_table_25():
    result = narayana_dasha(116 + 5/60, WADIYAR, resolved_co_lords={7: "Ketu"},
                           birth_jd_ut1=2451545, year_basis="savana_360")
    assert result.starting_sign_index == 3
    assert result.starting_decision.rule == "occupant_count"
    cancer, gemini, taurus = result.periods[:3]
    assert [p.sign_index for p in (cancer, gemini, taurus)] == [3, 2, 1]
    assert [p.source_years_numerator for p in (cancer, gemini, taurus)] == [9, 11, 2]
    # Cancer MD is even. Table 25 begins from Libra and advances forward.
    assert [x.sign_index for x in cancer.antardashas] == [6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4, 5]
    assert (cancer.antardashas[0].source_years_numerator, cancer.antardashas[0].source_years_denominator) == (3, 4)
    # Taurus's Saturn makes the Cancer-seeded subperiod order forward.
    assert [x.sign_index for x in taurus.antardashas[:3]] == [3, 4, 5]
    assert result.major_order == tuple(p.sign_index for p in result.periods[12:])
    for first, second in zip(result.periods[:12], result.periods[12:], strict=True):
        assert first.source_years_numerator + second.source_years_numerator == 12
    assert result.periods[-1].source_end_years == 144
    assert active_narayana(result, cancer.antardashas[0].end_jd_ut1) == (cancer, cancer.antardashas[1])
    assert active_narayana(result, cancer.end_jd_ut1)[0] == gemini
    assert active_narayana(result, 2451545 - 1) == ()


def test_advani_joint_exception_and_book_durations():
    # Page 71 compares actual in-sign Saturn and reverse Ketu degrees.
    # Other positions are sign interiors reconstructed from Table 20's
    # worked lords and duration counts, with the exact Saturn/Ketu tie inputs.
    values = {"Sun": 185, "Moon": 5, "Mars": 185, "Mercury": 185, "Jupiter": 335, "Venus": 155,
              "Saturn": 210 + 14 + 23/60, "Ketu": 210 + 27 + 39/60, "Rahu": 30 + 27 + 39/60}
    result = narayana_dasha(218, values)
    assert tuple(p.source_years_numerator for p in result.periods[:12]) == (11, 3, 2, 3, 12, 6, 3, 4, 3, 9, 11, 10)
    assert tuple(p.source_years_numerator for p in result.periods[12:15]) == (1, 9, 10)
    assert result.exception == "saturn"
    assert result.direction == "forward"
    assert result.major_order[:4] == (7, 8, 9, 10)
    assert _duration(4, 0, "Sun") == 5
    assert _duration(5, 5, "Mercury") == 12
    assert _duration(6, 5, "Venus") == 10
    assert _duration(10, 2, "Rahu") == 9


def test_unresolved_co_lord_and_half_open_zero_handling():
    unresolved = narayana_dasha(116, WADIYAR)
    assert "co_lord_7_unresolved" in unresolved.unresolved
    assert len(unresolved.major_order) == 12
    assert unresolved.periods == ()
    result = narayana_dasha(116, WADIYAR | {"Jupiter": 340}, resolved_co_lords={7: "Ketu"},
                           birth_jd_ut1=2451545, year_basis="julian_365.25")
    assert any(p.source_years_numerator == 0 for p in result.periods)
    for p in result.periods:
        if not p.source_years_numerator:
            assert p.start_jd_ut1 is p.end_jd_ut1 is None
            assert p.antardashas == ()

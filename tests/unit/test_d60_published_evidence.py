"""Edition-owned sign witnesses and a conditional rounded modern point pair.

Sharma BPHS I, 1999 reprint, ch.7.33-41, printed pp.131-136/PDF pp.139-144.
The row literals below are published SIGNS; their sample interior longitudes
are selected test inputs. No full D60 degrees are published by those tables.
Rao 2010 Padamsas v2, PDF p.12, publishes an arudha point's D1/D60 pair.
Its minute-rounding policy is unknown: nearest-minute interval compatibility
is conditional evidence, not an exact planetary oracle or a new tolerance.
"""
from fractions import Fraction

import pytest

from moira.varga import D60Method, d60_sign, shashtiamsha


# Transcribed one-based sign numbers across ARI ... PIS, not engine-derived.
# The source's degree column is a natal partition's upper edge, not its
# mapped D60 degree. Interior samples avoid assuming its boundary convention.
SHARMA_ROWS = (
    (0.25, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)),  # row 1, printed p.132
    (12.75, (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1)),  # row 26, p.134
    (29.75, (12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)),  # row 60, p.136
)


@pytest.mark.parametrize("method", [D60Method.SANTHANAM_SIGN, D60Method.PVR_TEXTBOOK_LINEAR])
@pytest.mark.parametrize("natal_sign", range(12))
@pytest.mark.parametrize("sample,published_signs", SHARMA_ROWS)
def test_independent_published_sign_table_rows(method, natal_sign, sample, published_signs):
    result = d60_sign(30 * natal_sign + sample, method=method)
    assert result.sign_index + 1 == published_signs[natal_sign]


@pytest.mark.parametrize("method", [D60Method.SANTHANAM_SIGN, D60Method.PVR_TEXTBOOK_LINEAR])
def test_sharma_published_gemini_sun_example(method):
    # Published Gemini 26d31m54s -> Scorpio, printed p.131/PDF p.139.
    longitude = float(Fraction(86) + Fraction(31, 60) + Fraction(54, 3600))
    result = d60_sign(longitude, method=method)
    assert result.sign == "Scorpio"


def test_published_arudha_pair_is_only_conditionally_rounding_compatible():
    # Published point (not planet): 16Cn17 in D1 -> 16Pi37 in D60.
    # Exact evaluation of the printed central input gives 17Pi00, not 16Pi37.
    central_input = Fraction(106) + Fraction(17, 60)
    printed_output = Fraction(346) + Fraction(37, 60)
    method = D60Method.PVR_TEXTBOOK_LINEAR
    central = shashtiamsha(float(central_input), d60_method=method)
    assert central.sign == "Pisces"
    assert central.varga_longitude == pytest.approx(347, abs=1e-12)
    assert Fraction(347) - printed_output == Fraction(23, 60)

    # If BOTH numerals were rounded to the nearest arcminute, their exact
    # intervals overlap after mapping. These are precision-derived intervals,
    # not fitted errors. Here neither interval crosses a partition boundary.
    half_minute = Fraction(1, 120)
    low = shashtiamsha(float(central_input - half_minute), d60_method=method)
    high = shashtiamsha(float(central_input + half_minute), d60_method=method)
    assert low.sign == high.sign == "Pisces"
    assert low.varga_longitude == pytest.approx(346.5, abs=1e-12)
    assert high.varga_longitude == pytest.approx(347.5, abs=1e-12)
    output_low = printed_output - half_minute
    output_high = printed_output + half_minute
    assert low.varga_longitude < float(output_low) < float(output_high) < high.varga_longitude

    # A truncate-to-minute assumption would FAIL: D1 [16Cn17,16Cn18)
    # maps to [17Pi00,18Pi00), beyond the printed D60 [16Pi37,16Pi38).
    assert Fraction(347) > printed_output + Fraction(1, 60)

from __future__ import annotations

import pytest

import moira.varga as varga


def test_d1_identity_matches_rashi_longitude() -> None:
    result = varga.calculate_varga(45.5, 1, "Rashi")
    assert result.varga_name == "Rashi"
    assert result.varga_number == 1
    assert result.varga_longitude == pytest.approx(45.5)
    assert result.sign == "Taurus"
    assert result.sign_degree == pytest.approx(15.5)


def test_navamsa_first_three_segments_cycle_through_aries_taurus_gemini() -> None:
    first = varga.navamsa(0.0)
    second = varga.navamsa(30.0 / 9.0)
    third = varga.navamsa(2.0 * 30.0 / 9.0)

    assert first.sign == "Aries"
    assert second.sign == "Taurus"
    assert third.sign == "Gemini"


def test_varga_boundary_advances_sign_and_resets_degree() -> None:
    n = 9
    segment = 30.0 / n
    left = varga.calculate_varga(segment - 1e-9, n, "D9")
    right = varga.calculate_varga(segment, n, "D9")

    assert left.sign == "Aries"
    assert left.sign_degree == pytest.approx(30.0 - n * 1e-9, abs=1e-6)
    assert right.sign == "Taurus"
    assert right.sign_degree == pytest.approx(0.0)


def test_varga_wraps_cleanly_at_360_degrees() -> None:
    zero = varga.navamsa(0.0)
    wrapped = varga.navamsa(360.0)

    assert wrapped.sign == zero.sign
    assert wrapped.sign_degree == pytest.approx(zero.sign_degree)
    assert wrapped.varga_longitude == pytest.approx(zero.varga_longitude)


def test_varga_is_periodic_every_360_degrees() -> None:
    base = varga.calculate_varga(123.456, 12, "D12")
    shifted = varga.calculate_varga(123.456 + 360.0, 12, "D12")

    assert shifted.sign == base.sign
    assert shifted.sign_symbol == base.sign_symbol
    assert shifted.sign_degree == pytest.approx(base.sign_degree)
    assert shifted.varga_longitude == pytest.approx(base.varga_longitude)


def test_varga_sign_degree_is_scaled_segment_remainder() -> None:
    result = varga.calculate_varga(17.25, 4, "D4")
    segment = 30.0 / 4.0
    segment_idx = int((17.25 % 360.0) // segment)
    sign_idx = segment_idx % 12
    expected_degree = (17.25 % segment) * 4.0

    assert result.sign_degree == pytest.approx(expected_degree)
    assert result.varga_longitude == pytest.approx((sign_idx * 30.0) + expected_degree)


def test_varga_repr_contains_name_number_sign_and_minutes() -> None:
    result = varga.navamsa(10.5)
    text = repr(result)
    assert "Navamsa" in text
    assert "(D9)" in text
    assert result.sign in text
    assert result.sign_symbol in text


@pytest.mark.parametrize(
    ("fn", "name", "number"),
    [
        (varga.navamsa, "Navamsa", 9),
        (varga.saptamsa, "Saptamsa", 7),
        (varga.dashamansa, "Dashamansa", 10),
        (varga.dwadashamsa, "Dwadashamsa", 12),
        (varga.trimshamsa, "Trimshamsa", 30),
    ],
)
def test_varga_convenience_functions_preserve_declared_name_and_number(fn, name: str, number: int) -> None:
    result = fn(95.0)
    assert result.varga_name == name
    assert result.varga_number == number


def test_varga_output_ranges_hold_across_sample_longitudes() -> None:
    for n in (1, 2, 3, 7, 9, 10, 12, 30, 60):
        for lon in (0.0, 0.1, 29.999999, 30.0, 123.456, 359.999999):
            result = varga.calculate_varga(lon, n, f"D{n}")
            assert 0.0 <= result.varga_longitude < 360.0
            assert 0.0 <= result.sign_degree < 30.0

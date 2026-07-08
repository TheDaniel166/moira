from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

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


def test_vargapoint_machine_contract_is_immutable() -> None:
    result = varga.navamsa(10.5)

    with pytest.raises((AttributeError, FrozenInstanceError)):
        result.sign = "Taurus"


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


# ===========================================================================
# Vimshopaka Bala + vargottama (BPHS Shodashavarga Adhyaya)
# ===========================================================================

_VIM_LONS = {
    'Sun': 10.0, 'Moon': 35.0, 'Mars': 190.0, 'Mercury': 160.0,
    'Jupiter': 100.0, 'Venus': 185.0, 'Saturn': 280.0,
}


class TestVimshopakaBala:

    def test_group_weights_each_sum_to_twenty(self) -> None:
        for group, weights in varga.VIMSHOPAKA_GROUPS.items():
            assert sum(weights.values()) == pytest.approx(20.0), group

    def test_group_division_counts(self) -> None:
        assert len(varga.VIMSHOPAKA_GROUPS['shadvarga']) == 6
        assert len(varga.VIMSHOPAKA_GROUPS['saptavarga']) == 7
        assert len(varga.VIMSHOPAKA_GROUPS['dashavarga']) == 10
        assert len(varga.VIMSHOPAKA_GROUPS['shodashavarga']) == 16

    def test_total_equals_sum_of_entry_points(self) -> None:
        for group in varga.VIMSHOPAKA_GROUPS:
            vb = varga.vimshopaka_bala('Sun', _VIM_LONS, group)
            assert vb.total == pytest.approx(sum(e.points for e in vb.entries))

    def test_total_bounded_between_5_and_20(self) -> None:
        # Worst case adhi shatru everywhere -> 5; best own sign -> 20.
        for planet in _VIM_LONS:
            vb = varga.vimshopaka_bala(planet, _VIM_LONS)
            assert 5.0 <= vb.total <= 20.0

    def test_entry_points_are_weight_times_vishva_over_twenty(self) -> None:
        vb = varga.vimshopaka_bala('Jupiter', _VIM_LONS, 'shadvarga')
        for e in vb.entries:
            assert e.points == pytest.approx(e.weight * e.vishva / 20.0)
            assert e.vishva in varga.VARGA_VISHVA.values()

    def test_own_sign_scores_full_vishva(self) -> None:
        # Sun at 10° Leo sidereal: D1 = Leo = own sign -> D1 vishva 20.
        lons = dict(_VIM_LONS)
        lons['Sun'] = 130.0
        vb = varga.vimshopaka_bala('Sun', lons, 'shadvarga')
        d1 = next(e for e in vb.entries if e.division == 1)
        assert d1.dignity == 'own_sign'
        assert d1.vishva == pytest.approx(20.0)
        assert d1.points == pytest.approx(d1.weight)

    def test_unknown_group_raises(self) -> None:
        with pytest.raises(ValueError, match="group"):
            varga.vimshopaka_bala('Sun', _VIM_LONS, 'panchavarga')

    def test_missing_planet_raises(self) -> None:
        with pytest.raises(KeyError):
            varga.vimshopaka_bala('Sun', {'Moon': 10.0})

    def test_vimshopaka_all_covers_every_planet(self) -> None:
        results = varga.vimshopaka_all(_VIM_LONS)
        assert set(results) == set(_VIM_LONS)
        for planet, vb in results.items():
            assert vb.planet == planet
            assert vb.group == 'shodashavarga'

    def test_varga_sign_index_matches_wrappers(self) -> None:
        # Dual-path: dispatcher must agree with the Parashari wrappers.
        from moira.constants import SIGNS
        for lon in (2.0, 17.5, 95.0, 200.0, 340.0):
            assert varga.varga_sign_index(lon, 2) == SIGNS.index(varga.hora(lon).sign)
            assert varga.varga_sign_index(lon, 4) == SIGNS.index(varga.chaturthamsha(lon).sign)
            assert varga.varga_sign_index(lon, 9) == SIGNS.index(varga.navamsa(lon).sign)
            assert varga.varga_sign_index(lon, 27) == SIGNS.index(varga.saptavimshamsha(lon).sign)
            assert varga.varga_sign_index(lon, 40) == SIGNS.index(varga.khavedamsha(lon).sign)
            assert varga.varga_sign_index(lon, 45) == SIGNS.index(varga.akshavedamsha(lon).sign)

    def test_d3_uses_parashari_trine_rule(self) -> None:
        # Aries 15° (2nd decan) -> 5th from Aries = Leo (index 4), not Taurus.
        assert varga.varga_sign_index(15.0, 3) == 4
        # Aries 25° (3rd decan) -> 9th from Aries = Sagittarius (index 8).
        assert varga.varga_sign_index(25.0, 3) == 8


class TestVargottama:

    def test_first_navamsa_of_sign_is_vargottama(self) -> None:
        # 0°-3°20' Aries: D9 starts at Aries for fire signs.
        assert varga.is_vargottama(2.0) is True

    def test_mid_sign_not_vargottama(self) -> None:
        assert varga.is_vargottama(15.0) is False

    def test_classical_vargottama_anchors_by_sign_mode(self) -> None:
        # Movable sign -> 1st navamsa; fixed -> 5th; dual -> 9th.
        assert varga.is_vargottama(91.0) is True    # Cancer 1 deg (movable, 1st)
        assert varga.is_vargottama(45.0) is True    # Taurus 15 deg (fixed, 5th)
        assert varga.is_vargottama(88.0) is True    # Gemini 28 deg (dual, 9th)
        assert varga.is_vargottama(118.0) is False  # Cancer 28 deg (movable, 9th)

    def test_vargottama_planets_filters_correctly(self) -> None:
        lons = {'Sun': 2.0, 'Moon': 15.0, 'Mars': 91.0}
        assert varga.vargottama_planets(lons) == frozenset({'Sun', 'Mars'})

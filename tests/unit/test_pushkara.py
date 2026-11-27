"""Primary-source tables and exact partition witnesses for Pushkara."""

from fractions import Fraction
from math import inf, nextafter

import pytest

from moira.pushkara import PushkaraBhagaProfile, pushkara

JP = PushkaraBhagaProfile.JATAKA_PARIJATA_SASTRI
VM = PushkaraBhagaProfile.VIDYAMADHAVIYAM_1923
# Each group is independently transcribed from Vishnusarma, printed p. 31.
NAVAMSAS = ((7, 9), (3, 5), (6, 8), (1, 3), (7, 9), (3, 5),
            (6, 8), (1, 3), (7, 9), (3, 5), (6, 8), (1, 3))


@pytest.mark.parametrize("sign", range(12))
def test_all_108_navamsas_use_the_printed_rule(sign):
    for ordinal in range(1, 10):
        midpoint = Fraction(30 * sign) + Fraction(5 * (2 * ordinal - 1), 3)
        result = pushkara(float(midpoint), bhaga_profile=JP)
        assert result.navamsa_ordinal == ordinal
        assert result.pushkara_navamsa_ordinals == NAVAMSAS[sign]
        assert result.in_pushkara_navamsa == (ordinal in NAVAMSAS[sign])


def test_exact_navamsa_boundary_neighbors_and_wrap():
    for segment in range(1, 108):
        boundary = float(Fraction(10 * segment, 3))
        for longitude in (nextafter(boundary, -inf), boundary, nextafter(boundary, inf)):
            exact_segment = (Fraction.from_float(longitude) * 3) // 10
            found = pushkara(longitude, bhaga_profile=VM)
            assert found.navamsa_ordinal == exact_segment % 9 + 1
            assert found.in_pushkara_navamsa == (found.navamsa_ordinal in NAVAMSAS[exact_segment // 9])

    assert pushkara(360, bhaga_profile=VM) == pushkara(0, bhaga_profile=VM)
    assert pushkara(nextafter(0.0, -inf), bhaga_profile=VM).navamsa_ordinal == 9


@pytest.mark.parametrize(
    "profile,degree_table,subject",
    [
        (JP, (21, 14, 18, 8, 19, 9, 24, 11, 23, 14, 19, 9), "moon"),
        (VM, (21, 14, 24, 7, 21, 14, 24, 7, 21, 14, 24, 7), "sign_degree"),
    ],
)
def test_printed_bhaga_degrees_with_half_open_interval_policy(profile, degree_table, subject):
    for sign, degree in enumerate(degree_table):
        left = float(30 * sign + degree - 1)
        right = left + 1.0
        for longitude, expected in ((nextafter(left, -inf), False), (left, True),
                                    (nextafter(right, -inf), True), (right, False)):
            found = pushkara(longitude, bhaga_profile=profile)
            assert found.bhaga_degree_ordinal == degree
            assert found.bhaga_degree_interval == (degree - 1, degree)
            assert found.bhaga_source_subject == subject
            assert found.in_pushkara_bhaga is expected


@pytest.mark.parametrize("longitude", ["20", True, float("nan"), float("inf"), 10**400])
def test_invalid_longitudes_are_rejected(longitude):
    with pytest.raises((TypeError, ValueError)):
        pushkara(longitude, bhaga_profile=JP)


def test_worked_source_witnesses_keep_the_two_techniques_independent():
    # 21° Aries is the seventh division, which maps to Libra.
    fire = pushkara(20.5, bhaga_profile=JP)
    assert fire.navamsa_sign == "Libra"
    assert fire.in_pushkara_navamsa and fire.in_pushkara_bhaga

    # Gemini 17°30′ is in the sixth division, which maps to Pisces. JP puts
    # its Bhaga here, while the Vidyamadhaviyam puts it in the 24th degree.
    jp = pushkara(77.5, bhaga_profile=JP)
    vm = pushkara(77.5, bhaga_profile=VM)
    assert jp.navamsa_sign == vm.navamsa_sign == "Pisces"
    assert jp.in_pushkara_navamsa and vm.in_pushkara_navamsa
    assert jp.in_pushkara_bhaga and not vm.in_pushkara_bhaga
    assert pushkara(83.5, bhaga_profile=VM).in_pushkara_bhaga


def test_profile_requires_explicit_enum():
    with pytest.raises(TypeError):
        pushkara(20, bhaga_profile="jataka_parijata_sastri")

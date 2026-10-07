"""Classical-derived D60: source scope and independently derived coordinates.

BPHS Santhanam 6.33 prints the Capricorn 13d25m -> Pisces SIGN.
The 25d coordinate below is a Moira derivation, not a published D60 degree.
Raman's Prasna Marga V.27-28 notes print the two D9 full-position examples.
No astronomical oracle or predictive validity is claimed by these checks.
"""
from fractions import Fraction
from math import inf, nextafter

import pytest

from moira import Moira
from moira.varga import (
    D60Method, SHASHTIAMSHA_DEITIES, VargaPoint, d60_sign, navamsa,
    shashtiamsha, vimshopaka_bala,
)

PROFILE = D60Method.CLASSICAL_DERIVED_LINEAR
SOURCES = (
    "BPHS-Santhanam-Vol1:6.33:printed83:commentary",
    "Saravali:3.18:subdivision-coordinate",
    "Jataka-Parijata-Sastri:3.43:printed139:fractional-correspondence",
    "Prasna-Marga-Raman:5.27-28:printed171-173:notes:navamsa-degrees",
    "Moira:D60:classical-derived-proportional:v1",
)


@pytest.mark.parametrize("natal_sign", range(12))
def test_all_subdivisions_and_adjacent_boundaries_with_rational_progress(natal_sign):
    # Binary-rational oracle preserves the actual float input. Natal sign,
    # subdivision ordinal and fractional progress are evaluated separately.
    for part in range(60):
        start = natal_sign * 30 + part / 2
        end = start + 0.5
        for longitude in (start, nextafter(start, inf), start + 0.25,
                          nextafter(end, -inf), end % 360):
            angle = Fraction.from_float(longitude)
            natal = angle // 30
            within = angle - 30 * natal
            ordinal = within // Fraction(1, 2)
            progress = (within - Fraction(ordinal, 2)) / Fraction(1, 2)
            sign = int((natal + ordinal) % 12)
            point = shashtiamsha(longitude, d60_method=PROFILE)
            assert int(point.varga_longitude // 30) == sign
            assert point.sign_degree == float(30 * progress)
            assert 0 <= point.sign_degree < 30
            assert sign * 30 <= point.varga_longitude < (sign + 1) * 30
            deity = ordinal if natal % 2 == 0 else 59 - ordinal
            assert point.deity == SHASHTIAMSHA_DEITIES[int(deity)]
            assert point.d60_source_references == SOURCES
            assert point.d60_degree_attribution == "classical_derived"


def test_published_classical_sign_with_separately_derived_degree():
    source_angle = Fraction(283) + Fraction(25, 60)
    longitude = float(source_angle)
    point = shashtiamsha(longitude, d60_method=PROFILE)
    assert point.sign == "Pisces"  # Published Santhanam commentary witness.
    # Exact decimal input gives 25 degrees by derivation. The binary input's
    # conversion residual is amplified by 60, evaluated exactly here without
    # inventing a published coordinate or enlarging an oracle tolerance.
    assert (source_angle - 283) * 60 == 25
    converted_degree = 25 + 60 * (Fraction.from_float(longitude) - source_angle)
    assert point.sign_degree == float(converted_degree)
    assert point.d60_source_references == SOURCES


@pytest.mark.parametrize("natal,minutes,sign,degree", [
    (3, 24 * 60 + 25, "Aquarius", Fraction(39, 4)),
    (1, 25 * 60 + 11, "Leo", Fraction(333, 20)),
])
def test_raman_published_navamsa_examples(natal, minutes, sign, degree):
    # Printed pp.171-173 / PDF pp.200-202; commentary, not a D60 verse.
    within = Fraction(minutes, 60)
    assert (within * 9) % 30 == degree
    point = navamsa(float(natal * 30 + within))
    assert point.sign == sign
    assert point.sign_degree == pytest.approx(float(degree), abs=1e-12, rel=0)


@pytest.mark.parametrize("longitude", [-720.25, -360.25, -0.25, 0.25, 360.25, 720.25, 10**100, -1e-300])
def test_normalization_sign_projection_and_facade(longitude):
    point = shashtiamsha(longitude, d60_method=PROFILE)
    sign = d60_sign(longitude, method=PROFILE)
    assert (point.longitude, point.sign) == (sign.longitude, sign.sign)
    assert sign.source_reference == SOURCES[0]
    engine = Moira.__new__(Moira)
    engine._reader_obj = None
    assert engine.varga_named(longitude, "shashtiamsha", d60_method=PROFILE) == point
    assert engine.shodashvarga(longitude, d60_method=PROFILE)["shashtiamsha"] == point


@pytest.mark.parametrize("bad", [True, False, "12", None, float("nan"), float("inf"), -float("inf"), 10**400])
def test_derived_profile_rejects_nonfinite_or_coerced_input(bad):
    with pytest.raises(ValueError):
        shashtiamsha(bad, d60_method=PROFILE)


def test_equal_coordinates_preserve_distinct_degree_attribution():
    modern = shashtiamsha(31.125, d60_method=D60Method.PVR_TEXTBOOK_LINEAR)
    derived = shashtiamsha(31.125, d60_method=PROFILE)
    assert (modern.sign, modern.sign_degree, modern.varga_longitude) == (
        derived.sign, derived.sign_degree, derived.varga_longitude,
    )
    assert modern.d60_degree_attribution == "modern_composed"
    assert modern.d60_source_references != derived.d60_source_references
    assert shashtiamsha(31.125).d60_degree_attribution == "generic_harmonic"
    manual = VargaPoint("Manual", 60, 0, 0, "Aries", "♈", 0)
    assert manual.d60_degree_attribution is None and manual.d60_source_references == ()


@pytest.mark.parametrize("group", ["dashavarga", "shodashavarga"])
def test_strength_uses_classical_sign_without_requiring_degrees(group):
    lons = {"Sun": 130, "Moon": 200, "Mars": 125, "Mercury": 315,
            "Jupiter": 105, "Venus": 283 + 25 / 60, "Saturn": 190}
    strength = vimshopaka_bala("Venus", lons, group, d60_method=PROFILE)
    sign_only = vimshopaka_bala("Venus", lons, group, d60_method=D60Method.SANTHANAM_SIGN)
    assert (strength.entries, strength.total) == (sign_only.entries, sign_only.total)
    assert strength.d60_source_references == SOURCES
    with pytest.raises(ValueError, match="containing D60"):
        vimshopaka_bala("Venus", lons, "shadvarga", d60_method=PROFILE)


@pytest.mark.parametrize("method", [D60Method.PVR_TEXTBOOK_LINEAR, PROFILE])
def test_composed_strength_normalizes_all_divisions_and_relationships(method):
    lons = {"Sun": -1e-300, "Moon": 200, "Mars": 125, "Mercury": 315,
            "Jupiter": 105, "Venus": 283 + 25 / 60, "Saturn": 190}
    normalized = {body: d60_sign(lon, method=method).longitude for body, lon in lons.items()}
    for body in lons:
        actual = vimshopaka_bala(body, lons, d60_method=method)
        expected = vimshopaka_bala(body, normalized, d60_method=method)
        assert actual == expected

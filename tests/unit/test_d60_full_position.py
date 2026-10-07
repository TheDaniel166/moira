"""Modern source profile: published sign witness, derived degrees, boundaries.

Rao 2000 section 6.2.20 publishes 222d58m -> Sagittarius (sign only).
Rao 2013 version 1 PDF page 2 supplies the general divisional-degree law.
28 degrees below is derived from that law, NOT a published D60 coordinate.
The Fraction oracle is independent of engine sign/segment helpers.
"""
from fractions import Fraction
from math import floor, inf, nextafter

import pytest

from moira import Moira
from moira.varga import (
    D60Method, SHASHTIAMSHA_DEITIES, calculate_varga, d60_sign,
    navamsa, shashtiamsha, varga_sign_index, vimshopaka_bala,
)

PROFILE = D60Method.PVR_TEXTBOOK_LINEAR
LONS = {"Sun": 130, "Moon": 200, "Mars": 125, "Mercury": 315,
        "Jupiter": 105, "Venus": 283 + 25 / 60, "Saturn": 190}


def rational_position(longitude):
    angle = Fraction.from_float(longitude)
    natal = angle // 30
    within = angle - natal * 30
    segment = within // Fraction(1, 2)
    return int((natal + segment) % 12), float((within - Fraction(segment, 2)) * 60), int(natal), int(segment)


@pytest.mark.parametrize("segment", range(720))
def test_every_half_degree_segment_with_exact_rational_oracle(segment):
    start = segment / 2
    end = start + 0.5
    for longitude in (start, nextafter(start, inf), start + 0.25, nextafter(end, -inf)):
        sign, degree, natal, part = rational_position(longitude)
        result = shashtiamsha(longitude, d60_method=PROFILE)
        assert result.sign == d60_sign(longitude, method=PROFILE).sign
        assert floor(result.varga_longitude / 30) == sign
        assert result.sign_degree == degree
        assert 0 <= result.sign_degree < 30
        assert sign * 30 <= result.varga_longitude < (sign + 1) * 30
        assert result.deity == SHASHTIAMSHA_DEITIES[part if natal % 2 == 0 else 59 - part]
        assert result.d60_method is PROFILE
        assert len(result.d60_source_references) == 2
        assert varga_sign_index(longitude, 60, d60_method=PROFILE) == sign
    # Endpoints belong to the next segment, including natal/zodiac wraps.
    sign, degree, _, _ = rational_position(end % 360)
    point = shashtiamsha(end, d60_method=PROFILE)
    assert (floor(point.varga_longitude / 30), point.sign_degree) == (sign, degree)


def test_source_published_sign_and_independently_derived_degree():
    # Published sign: Rao textbook example 26. Fraction derives 28Sg00.
    lon = float(Fraction(222) + Fraction(58, 60))
    point = shashtiamsha(lon, d60_method=PROFILE)
    assert point.sign == "Sagittarius"
    assert point.sign_degree == pytest.approx(28.0, abs=1e-12)
    assert point.varga_longitude == pytest.approx(268.0, abs=1e-12)
    assert "2000:6.2.20" in point.d60_source_references[0]
    assert "2013-12-31:v1" in point.d60_source_references[1]
    # The source's stated multiplication has an arithmetic discrepancy:
    # (8d05m - 6d40m) * 9 = 12d45m, not its printed 13d45m.
    # Test the explicit LAW, preserve the defective printed coordinate in
    # the source record, and do not bend engine arithmetic to match it.
    witness = navamsa(300 + 8 + 5 / 60)
    assert witness.sign == "Sagittarius"
    assert witness.sign_degree == pytest.approx(12.75, abs=1e-12)
    assert (Fraction(8) + Fraction(5, 60) - Fraction(20, 3)) * 9 == Fraction(51, 4)
    # Its reverse-reckoning D24 example independently agrees with the law.
    assert 30 - (Fraction(8) - Fraction(15, 2)) * 24 == 18


@pytest.mark.parametrize("lon,sign,degree", [
    (0.25, "Aries", 15), (30.25, "Taurus", 15),
    (31.125, "Cancer", 7.5), (330.25, "Pisces", 15),
    (359.75, "Aquarius", 15), (13.25, "Gemini", 15),
    (43.25, "Cancer", 15),
])
def test_hand_derived_forward_parity_and_zodiac_examples(lon, sign, degree):
    point = shashtiamsha(lon, d60_method=PROFILE)
    assert (point.sign, point.sign_degree) == (sign, degree)


@pytest.mark.parametrize("longitude", [-720.25, -360.25, -0.25, 0.25, 360.25, 720.25, 10**100, -1e-300])
def test_full_profile_normalization_is_shared_with_sign_receipt(longitude):
    sign = d60_sign(longitude, method=PROFILE)
    point = shashtiamsha(longitude, d60_method=PROFILE)
    assert point.longitude == sign.longitude
    assert point.sign == sign.sign
    assert 0 <= point.varga_longitude < 360 and 0 <= point.sign_degree < 30


@pytest.mark.parametrize("bad", [True, False, "12", None, float("nan"), float("inf"), -float("inf"), 10**400])
def test_source_full_profile_is_strict_finite(bad):
    with pytest.raises(ValueError):
        shashtiamsha(bad, d60_method=PROFILE)


@pytest.mark.parametrize("bad", ["pvr_textbook_linear", "unknown", None, 1])
def test_full_method_cannot_coerce_or_fall_back(bad):
    with pytest.raises(TypeError):
        shashtiamsha(10, d60_method=bad)


def test_facade_method_application_and_preflight(monkeypatch):
    engine = Moira.__new__(Moira)
    engine._reader_obj = None
    expected = shashtiamsha(31.125, d60_method=PROFILE)
    assert engine.varga_named(31.125, "shashtiamsha", d60_method=PROFILE) == expected
    mapped = engine.shodashvarga(31.125, d60_method=PROFILE)
    default = engine.shodashvarga(31.125)
    assert mapped["shashtiamsha"] == expected
    assert {k:v for k,v in mapped.items() if k != "shashtiamsha"} == {k:v for k,v in default.items() if k != "shashtiamsha"}
    monkeypatch.setattr(Moira, "_sidereal_longitudes_from_chart", lambda *a, **kw: {"Sun": 31.125})
    assert engine.varga_for_chart(None, "Sun", "shashtiamsha", d60_method=PROFILE) == expected
    assert engine.shodashvarga_for_chart(None, "Sun", d60_method=PROFILE)["shashtiamsha"] == expected
    monkeypatch.setattr(Moira, "_sidereal_longitudes_from_chart", lambda *a, **kw: pytest.fail("invalid profile must fail before chart work"))
    with pytest.raises(ValueError, match="only to shashtiamsha"):
        engine.varga_for_chart(None, "Sun", "navamsa", d60_method=PROFILE)


@pytest.mark.parametrize("group,weight", [("dashavarga", 5), ("shodashavarga", 4)])
def test_strength_matches_sign_profile_with_separate_applied_authority(group, weight):
    default = vimshopaka_bala("Venus", LONS, group)
    result = vimshopaka_bala("Venus", LONS, group, d60_method=PROFILE)
    sign_only = vimshopaka_bala("Venus", LONS, group, d60_method=D60Method.SANTHANAM_SIGN)
    assert result.entries == sign_only.entries and result.total == sign_only.total
    assert result.entries[:-1] == default.entries[:-1]
    assert result.entries[-1].points == weight * 7 / 20
    assert result.total - default.total == pytest.approx(-11 * weight / 20, abs=1e-12)
    assert result.d60_method is PROFILE
    assert result.d60_source_references == shashtiamsha(LONS["Venus"], d60_method=PROFILE).d60_source_references
    with pytest.raises(ValueError, match="containing D60"):
        vimshopaka_bala("Venus", LONS, "shadvarga", d60_method=PROFILE)


def test_default_harmonic_and_generic_semantics_are_retained():
    for segment in range(720):
        lon = segment / 2 + 0.25
        generic = calculate_varga(lon, 60)
        named = shashtiamsha(lon)
        assert named.varga_longitude == generic.varga_longitude
        assert named.sign_degree == generic.sign_degree
        assert named.d60_method is generic.d60_method is D60Method.HARMONIC
        assert generic.deity is None
        assert named.d60_source_references == ("moira_generic_harmonic",)
    assert calculate_varga(10, 9).d60_source_references == ()

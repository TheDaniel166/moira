"""Ayanamsa doctrine: provenance records and the doctrinal families.

Governing record: wiki/02_standards/AYANAMSA_DOCTRINE_STANDARD.md.
"""

from __future__ import annotations

import math

import pytest

from moira.ayanamsa_doctrine import (
    FAMILY_EPOCH_POLYNOMIAL,
    FAMILY_POLAR_STAR,
    FAMILY_STAR_ANCHORED_ECLIPTIC,
    FAMILY_TEXTUAL_FORMULA,
    FAMILY_TREPIDATION,
    POLAR_STAR_CATALOGUE,
    _KALI_EPOCH_JD,
    _MEAN_SUN_L0_DEG,
    _MEAN_SUN_RATE_DEG_PER_DAY,
    _grahalaghava_year_boundary,
    grahalaghava_ayanamsa_for_saka_year,
    polar_longitude,
    siddhantic_polar_to_ecliptic,
)
from moira.obliquity import nutation
from moira.sidereal import (
    Ayanamsa,
    GrahalaghavaAyanamsa,
    PolarStarAyanamsa,
    SuryaSiddhantaLibrationAyanamsa,
    SuryadevaTrepidationAyanamsa,
    UserDefinedAyanamsa,
    _AYANAMSA_AT_J2000,
    _STAR_ANCHORED,
    _anchor_product,
    _ayanamsa_truth_at_tt,
    ayanamsa_doctrine,
    tropical_to_sidereal,
)

ARCSEC = 1.0 / 3600.0
JD = 2461000.5  # 2025-11-20


def _dm(degrees: int, minutes: float) -> float:
    return degrees + minutes / 60.0


# --------------------------------------------------------------- Phase A

@pytest.mark.parametrize("system", Ayanamsa.ALL)
def test_every_named_system_has_a_record_that_agrees_with_the_tables(system: str) -> None:
    doctrine = ayanamsa_doctrine(system)
    assert doctrine.system == system
    assert doctrine.definition and doctrine.sources
    if system in _STAR_ANCHORED:
        star, target = _STAR_ANCHORED[system]
        assert doctrine.family == FAMILY_STAR_ANCHORED_ECLIPTIC
        assert doctrine.layer == "modern_convention"
        assert doctrine.anchor_star == star
        assert doctrine.anchor_target_deg == target
        assert doctrine.anchor_coordinate == "ecliptic"
        assert doctrine.anchor_product == _anchor_product(system)
    else:
        assert doctrine.family == FAMILY_EPOCH_POLYNOMIAL
        assert doctrine.anchor_star is None


@pytest.mark.parametrize("system", Ayanamsa.ALL)
def test_every_named_truth_carries_its_family_and_layer(system: str) -> None:
    truth = _ayanamsa_truth_at_tt(2451545.0, system, "mean")
    doctrine = ayanamsa_doctrine(system)
    assert (truth.doctrine_family, truth.doctrine_layer) == (doctrine.family, doctrine.layer)
    assert truth.doctrine_terms == ()


def test_star_records_state_which_texts_give_their_value() -> None:
    chitra = ayanamsa_doctrine(Ayanamsa.TRUE_CHITRAPAKSHA)
    polar = {a.source: a.value_deg for a in chitra.attestations if a.coordinate == "polar"}
    assert polar["Sūrya Siddhānta"] == 180.0
    assert sorted(v for s, v in polar.items() if s != "Sūrya Siddhānta") == [183.0] * 4
    assert chitra.identification_certainty == "in_doubt"
    pushya = ayanamsa_doctrine(Ayanamsa.TRUE_PUSHYA)
    assert {a.value_deg for a in pushya.attestations} == {106.0}
    assert pushya.identification_certainty == "beyond_doubt"
    mula = ayanamsa_doctrine(Ayanamsa.TRUE_MULA)
    assert 240.0 not in {a.value_deg for a in mula.attestations}


def test_user_defined_and_unknown_systems() -> None:
    assert ayanamsa_doctrine(UserDefinedAyanamsa(23.0)).family == "user_defined"
    with pytest.raises(ValueError):
        ayanamsa_doctrine("Not A System")
    with pytest.raises(ValueError):
        ayanamsa_doctrine(42)


def test_named_values_are_unchanged_by_the_doctrine_layer() -> None:
    # The doctrine fields are additive; the computed value is the same path.
    truth = _ayanamsa_truth_at_tt(2451545.0, Ayanamsa.LAHIRI, "mean")
    assert truth.ayanamsa_unwrapped_deg == pytest.approx(
        _AYANAMSA_AT_J2000[Ayanamsa.LAHIRI], abs=1e-12)


# --------------------------------------------------------------- Phase B

@pytest.mark.parametrize(("saka", "expected"), [
    (1534, _dm(18, 10)),   # Viśvanātha's worked example (Jośī ed. p. 65)
    (1809, _dm(22, 45)),   # Dikshit, Bhāratīya Jyotiṣa Śāstra p. 291
    (1920, _dm(24, 36)),   # Rao & Uma p. S123
    (444, 0.0),            # the zero year, 522 CE
])
def test_grahalaghava_published_values(saka: int, expected: float) -> None:
    assert grahalaghava_ayanamsa_for_saka_year(saka) == pytest.approx(expected, abs=1e-12)


def test_grahalaghava_rejects_a_non_integer_year() -> None:
    with pytest.raises(ValueError):
        grahalaghava_ayanamsa_for_saka_year(1534.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        GrahalaghavaAyanamsa(year_convention="kali")
    with pytest.raises(ValueError):
        GrahalaghavaAyanamsa(stepping="daily")


@pytest.mark.parametrize("convention", ["current", "elapsed"])
def test_grahalaghava_boundary_is_the_mean_sun_reaching_the_year_value(convention: str) -> None:
    for year in (-500, 522, 1520, 2026, 3000):
        boundary = _grahalaghava_year_boundary(year, convention)
        saka = year - 77 if convention == "current" else year - 78
        mean_sun = (_MEAN_SUN_L0_DEG + _MEAN_SUN_RATE_DEG_PER_DAY * (boundary - 2451545.0)) % 360.0
        assert ((mean_sun - grahalaghava_ayanamsa_for_saka_year(saka) + 180.0) % 360.0) - 180.0 == pytest.approx(
            0.0, abs=1e-7)
        # The boundary falls in the spring of that year.
        assert 0.0 < _grahalaghava_year_boundary(year + 1, convention) - boundary < 366.0


def test_grahalaghava_annual_steps_one_arcminute_at_the_boundary() -> None:
    system = GrahalaghavaAyanamsa()
    boundary = _grahalaghava_year_boundary(2026, "current")
    before = _ayanamsa_truth_at_tt(boundary - 1e-6, system, "mean")
    after = _ayanamsa_truth_at_tt(boundary + 1e-6, system, "mean")
    assert dict(before.doctrine_terms)["saka_year"] == 1948
    assert dict(after.doctrine_terms)["saka_year"] == 1949
    assert after.ayanamsa_unwrapped_deg - before.ayanamsa_unwrapped_deg == pytest.approx(1.0 / 60.0, abs=1e-12)
    mid = _ayanamsa_truth_at_tt(boundary + 100.0, system, "mean")
    assert mid.ayanamsa_unwrapped_deg == after.ayanamsa_unwrapped_deg


def test_grahalaghava_continuous_is_continuous_and_matches_at_year_start() -> None:
    annual = GrahalaghavaAyanamsa(stepping="continuous")
    boundary = _grahalaghava_year_boundary(2026, "current")
    before = _ayanamsa_truth_at_tt(boundary - 1e-6, annual, "mean").ayanamsa_unwrapped_deg
    after = _ayanamsa_truth_at_tt(boundary + 1e-6, annual, "mean").ayanamsa_unwrapped_deg
    assert after - before == pytest.approx(0.0, abs=1e-9)
    assert after == pytest.approx(grahalaghava_ayanamsa_for_saka_year(1949), abs=1e-9)


def test_grahalaghava_conventions_differ_by_one_year_and_true_adds_nutation() -> None:
    current = _ayanamsa_truth_at_tt(JD, GrahalaghavaAyanamsa("current"), "mean").ayanamsa_unwrapped_deg
    elapsed = _ayanamsa_truth_at_tt(JD, GrahalaghavaAyanamsa("elapsed"), "mean").ayanamsa_unwrapped_deg
    assert current - elapsed == pytest.approx(1.0 / 60.0, abs=1e-12)
    true = _ayanamsa_truth_at_tt(JD, GrahalaghavaAyanamsa(), "true")
    assert true.ayanamsa_unwrapped_deg - current == pytest.approx(nutation(JD)[0], abs=1e-12)
    assert true.doctrine_family == FAMILY_TEXTUAL_FORMULA
    assert true.doctrine_layer == "verse"
    assert true.ayanamsa_system == "Grahalaghava (current year, annual)"


# --------------------------------------------------------------- Phase C

@pytest.mark.parametrize(("dhruvaka", "vikshepa", "lon", "lat"), [
    # The research table (AYANAMSA_ANCHORS_IN_ORIGINAL_TEXTS.md), 24° obliquity.
    (180.0, -2.0, _dm(180, 49), -_dm(1, 50)),
    (241.0, -9.0, _dm(242, 55), -_dm(8, 48)),
    (8.0, 10.0, _dm(12, 4), _dm(9, 9)),
    (106.0, 0.0, 106.0, 0.0),
])
def test_siddhantic_polar_reduction_matches_the_table(dhruvaka, vikshepa, lon, lat) -> None:
    got_lon, got_lat = siddhantic_polar_to_ecliptic(dhruvaka, vikshepa)
    assert got_lon == pytest.approx(lon, abs=0.6 / 60.0)
    assert got_lat == pytest.approx(lat, abs=0.6 / 60.0)


@pytest.mark.parametrize("source", sorted(POLAR_STAR_CATALOGUE))
def test_polar_reduction_round_trips(source: str) -> None:
    for dhruvaka, vikshepa in POLAR_STAR_CATALOGUE[source].values():
        lon, lat = siddhantic_polar_to_ecliptic(dhruvaka, vikshepa, 24.0)
        back = polar_longitude(lon, lat, 24.0)
        assert ((back - dhruvaka + 180.0) % 360.0) - 180.0 == pytest.approx(0.0, abs=1e-9)


def test_polar_longitude_is_ecliptic_longitude_on_the_ecliptic() -> None:
    for lon in (0.0, 45.0, 106.0, 180.0, 271.3, 359.8):
        assert polar_longitude(lon, 0.0, 23.44) == pytest.approx(lon % 360.0, abs=1e-9)
    with pytest.raises(ValueError):
        polar_longitude(10.0, 90.0, 23.44)


@pytest.mark.parametrize("source", sorted(POLAR_STAR_CATALOGUE))
@pytest.mark.parametrize("nakshatra", ["ashvini", "pushya", "chitra", "mula", "revati"])
def test_polar_mode_puts_the_star_polar_point_at_its_target(source: str, nakshatra: str) -> None:
    system = PolarStarAyanamsa(source, nakshatra)
    truth = _ayanamsa_truth_at_tt(JD, system, "true")
    terms = dict(truth.doctrine_terms)
    assert truth.doctrine_family == FAMILY_POLAR_STAR
    assert truth.anchor_product == "astrometric"
    sidereal_polar = (terms["star_polar_longitude_deg"] - truth.ayanamsa_unwrapped_deg) % 360.0
    target = POLAR_STAR_CATALOGUE[source][nakshatra][0]
    assert ((sidereal_polar - target + 180.0) % 360.0) - 180.0 == pytest.approx(0.0, abs=1e-9)


def test_polar_chitra_differs_from_true_chitrapaksha_by_the_latitude_effect() -> None:
    # Spica's polar longitude is about 49′ below its ecliptic longitude.
    polar = _ayanamsa_truth_at_tt(JD, PolarStarAyanamsa("surya_siddhanta", "chitra"), "true")
    ecliptic = _ayanamsa_truth_at_tt(JD, Ayanamsa.TRUE_CHITRAPAKSHA, "true")
    assert ecliptic.ayanamsa_deg - polar.ayanamsa_deg == pytest.approx(0.82, abs=0.05)


def test_polar_mean_mode_uses_the_mean_equinox() -> None:
    system = PolarStarAyanamsa("grahalaghava", "pushya")
    true = dict(_ayanamsa_truth_at_tt(JD, system, "true").doctrine_terms)
    mean = dict(_ayanamsa_truth_at_tt(JD, system, "mean").doctrine_terms)
    assert true["star_ecliptic_longitude_deg"] - mean["star_ecliptic_longitude_deg"] == pytest.approx(
        nutation(JD)[0], abs=1e-12)
    assert mean["obliquity_model"] == "mean_of_date"


def test_polar_star_validation() -> None:
    with pytest.raises(ValueError):
        PolarStarAyanamsa("lalla", "chitra")
    with pytest.raises(ValueError):
        PolarStarAyanamsa("surya_siddhanta", "rohini")
    with pytest.raises(ValueError):
        PolarStarAyanamsa("surya_siddhanta", "chitra", star_product="geometric")


# --------------------------------------------------------------- Phase D

def test_surya_siddhanta_libration_reproduces_burgess() -> None:
    # Burgess, Sūrya Siddhānta (1860) p. 245: 20°24′38.67″ for 1 January 1860.
    truth = _ayanamsa_truth_at_tt(2400410.5, SuryaSiddhantaLibrationAyanamsa(), "mean")
    assert truth.ayanamsa_unwrapped_deg == pytest.approx(_dm(20, 24 + 38.67 / 60.0), abs=0.01 * ARCSEC)
    assert truth.doctrine_layer == "reconstruction"


def test_surya_siddhanta_libration_shape() -> None:
    system = SuryaSiddhantaLibrationAyanamsa()
    cycle = 1_577_917_828 / 600.0
    values = {
        frac: _ayanamsa_truth_at_tt(_KALI_EPOCH_JD + frac * cycle, system, "mean").ayanamsa_unwrapped_deg
        for frac in (0.0, 0.25, 0.5, 0.75)
    }
    assert values[0.0] == pytest.approx(0.0, abs=1e-9)
    assert values[0.25] == pytest.approx(-27.0, abs=1e-9)
    assert values[0.5] == pytest.approx(0.0, abs=1e-9)   # Kali 3600, 499 CE
    assert values[0.75] == pytest.approx(27.0, abs=1e-9)
    slow = _ayanamsa_truth_at_tt(2400410.5, SuryaSiddhantaLibrationAyanamsa(30), "mean")
    assert abs(slow.ayanamsa_unwrapped_deg) < 27.0
    with pytest.raises(ValueError):
        SuryaSiddhantaLibrationAyanamsa(60)


def test_suryadeva_rule_shape() -> None:
    system = SuryadevaTrepidationAyanamsa()
    year = 1_577_917_500 / 4_320_000

    def at(kali_years: float) -> float:
        return _ayanamsa_truth_at_tt(_KALI_EPOCH_JD + kali_years * year, system, "mean").ayanamsa_unwrapped_deg

    assert at(3600.0) == pytest.approx(0.0, abs=1e-9)
    assert at(3600.0 + 1452.0) == pytest.approx(24.0, abs=1e-9)
    assert at(3600.0 + 2904.0) == pytest.approx(0.0, abs=1e-9)
    assert at(3600.0 + 4356.0) == pytest.approx(-24.0, abs=1e-9)
    assert at(5000.0) == pytest.approx(at(5000.0 + 5808.0), abs=1e-9)
    assert at(3601.0) == pytest.approx(2.0 / 121.0, abs=1e-9)  # about 59.5″ a year
    doctrine = ayanamsa_doctrine(system)
    assert doctrine.family == FAMILY_TREPIDATION
    assert "Āryabhaṭa" in " ".join(doctrine.caveats)


# --------------------------------------------------------------- conversions and consumers

@pytest.mark.parametrize("system", [
    GrahalaghavaAyanamsa(),
    PolarStarAyanamsa("surya_siddhanta", "revati"),
    SuryaSiddhantaLibrationAyanamsa(),
    SuryadevaTrepidationAyanamsa(),
])
def test_doctrinal_values_convert_longitudes(system) -> None:
    from moira.sidereal import ayanamsa, sidereal_to_tropical

    value = ayanamsa(JD, system)
    assert tropical_to_sidereal(100.0, JD, system) == pytest.approx((100.0 - value) % 360.0, abs=1e-12)
    assert sidereal_to_tropical(tropical_to_sidereal(100.0, JD, system), JD, system) == pytest.approx(100.0, abs=1e-9)


def test_named_only_consumers_refuse_doctrinal_values() -> None:
    from moira._kalachakra_types import named_ayanamsa
    from moira.daily_panchanga import DailyPanchangaPolicy
    from moira._kalachakra_types import KalachakraInputError
    from moira.gochara_dated import GocharaDatePolicy

    system = GrahalaghavaAyanamsa()
    with pytest.raises(KalachakraInputError):
        named_ayanamsa(system)
    with pytest.raises((TypeError, ValueError)):
        DailyPanchangaPolicy(ayanamsa_system=system)
    with pytest.raises((TypeError, ValueError)):
        GocharaDatePolicy(ayanamsa_system=system)


def test_doctrine_terms_keep_finite_numbers() -> None:
    for system in (GrahalaghavaAyanamsa(stepping="continuous"), SuryadevaTrepidationAyanamsa()):
        for _, value in _ayanamsa_truth_at_tt(JD, system, "true").doctrine_terms:
            if isinstance(value, float):
                assert math.isfinite(value)

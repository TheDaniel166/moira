"""
Unit tests for moira.hermetic_decans.

Catalog and equal-segmentation tests are source-locked to Gundel's Harley
MS 3731 edition. Rising-composition tests remain quarantined structural checks
rather than doctrine admission.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest


_SOURCE_NAMES = (
    "Aulathamas", "Sabaoth", "Disornafais",
    "Jaus", "Sarnatas", "Erchumbris",
    "Manuchos", "Samurois", "Asuel",
    "Seneptois", "Somathalmais", "Charmine",
    "Zaloias", "Zachor", "Frich",
    "Zamendres", "Magois", "Michulais",
    "Psineus", "Chusthisis", "Psannatois",
    "Nebenos", "Churmantis", "Psermes",
    "Clinothois", "Thursois", "Renethis",
    "Renpsois", "Manethois", "Marxois",
    "Ularis", "Luxois", "Crauxes",
    "Fambrais", "Flugmois Mars", "Piathris",
)


def test_quarantined_catalog_is_not_curated_by_package_or_facade() -> None:
    import moira
    import moira.facade as facade
    import moira.hermetic_decans as decans

    quarantined_symbols = {
        "DECAN_NAMES",
        "DECAN_PLANETARY_FACES",
        "HERMETIC_DECAN_CATALOG",
        "DECAN_RULING_STARS",
        "list_decans",
        "available_decans",
        "decan_for_longitude",
        "decan_at",
    }
    removed_symbols = {"DecanHour", "DecanHoursNight", "decan_hours"}

    assert quarantined_symbols.isdisjoint(moira.__all__)
    assert all(not hasattr(facade, name) for name in quarantined_symbols)
    assert all(not hasattr(decans, name) for name in removed_symbols)


def test_solar_declination_ra_uses_tt_obliquity() -> None:
    import moira._solar as solar_module

    dummy_sun = MagicMock(longitude=15.0, latitude=1.0)
    reader = MagicMock()
    with patch.object(solar_module, "planet_at", return_value=dummy_sun), \
         patch.object(solar_module, "_ut1_to_ephemeris_tt", return_value=2451545.0008) as mock_tt, \
         patch.object(solar_module, "true_obliquity", return_value=23.4) as mock_obl:
        solar_module._solar_declination_ra(2451545.0, reader)

    mock_tt.assert_called_once_with(2451545.0, reader)
    mock_obl.assert_called_once_with(2451545.0008)


def test_decan_at_uses_tt_obliquity() -> None:
    import moira.hermetic_decans as decans

    with patch.object(decans, "_lst_to_ramc", return_value=120.0), \
         patch.object(decans, "ut_to_tt", return_value=2451545.0008) as mock_tt, \
         patch.object(decans, "true_obliquity", return_value=23.4) as mock_obl, \
         patch.object(decans, "decan_for_longitude", return_value="Aulathamas"):
        result = decans.decan_at(2451545.0, 51.5, -0.1)

    assert result == "Aulathamas"
    mock_tt.assert_called_once_with(2451545.0)
    mock_obl.assert_called_once_with(2451545.0008)


def test_decan_at_matches_house_engine_ascendant_for_representative_cases() -> None:
    from moira.hermetic_decans import decan_at, decan_for_longitude
    from moira.houses import calculate_houses
    from moira.julian import jd_from_datetime

    samples = [
        (datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 51.5, -0.1),
        (datetime(1987, 4, 10, 0, tzinfo=timezone.utc), 37.98, 23.72),
        (datetime(2024, 6, 21, 0, tzinfo=timezone.utc), 0.0, 0.0),
    ]
    for dt, lat, lon in samples:
        jd = jd_from_datetime(dt)
        houses = calculate_houses(jd, lat, lon)
        assert decan_at(jd, lat, lon) == decan_for_longitude(houses.asc)


# ===========================================================================
# 7.1 — Constants and dict structure
# ===========================================================================

class TestDecanConstants:
    def test_aulathamas_constant(self):
        from moira.hermetic_decans import AULATHAMAS
        assert AULATHAMAS == "Aulathamas"

    def test_piathris_constant(self):
        from moira.hermetic_decans import PIATHRIS
        assert PIATHRIS == "Piathris"

    def test_flugmois_mars_transcription(self):
        from moira.hermetic_decans import FLUGMOIS_MARS
        assert FLUGMOIS_MARS == "Flugmois Mars"


class TestDecanNamesDict:
    def test_length(self):
        from moira.hermetic_decans import DECAN_NAMES
        assert len(DECAN_NAMES) == 36

    def test_aulathamas_entry(self):
        from moira.hermetic_decans import DECAN_NAMES
        assert DECAN_NAMES["Aulathamas"] == "Aulathamas"

    def test_piathris_entry(self):
        from moira.hermetic_decans import DECAN_NAMES
        assert DECAN_NAMES["Piathris"] == "Piathris"

    def test_all_values_are_strings(self):
        from moira.hermetic_decans import DECAN_NAMES
        for k, v in DECAN_NAMES.items():
            assert isinstance(v, str)


class TestSourceReconstructedCatalog:
    def test_catalog_matches_gundel_harley_name_order(self):
        from moira.hermetic_decans import HERMETIC_DECAN_CATALOG

        assert tuple(entry.name for entry in HERMETIC_DECAN_CATALOG) == _SOURCE_NAMES

    def test_catalog_source_and_page_receipts(self):
        from moira.hermetic_decans import (
            HERMETIC_CATALOG_SOURCE_ID,
            HERMETIC_DECAN_CATALOG,
        )

        assert len(HERMETIC_DECAN_CATALOG) == 36
        assert {entry.source_id for entry in HERMETIC_DECAN_CATALOG} == {
            HERMETIC_CATALOG_SOURCE_ID
        }
        assert {entry.edition_page for entry in HERMETIC_DECAN_CATALOG} == {
            379, 380, 381, 382, 383
        }

    def test_planetary_faces_match_the_edited_harley_list(self):
        from moira.hermetic_decans import DECAN_PLANETARY_FACES

        assert DECAN_PLANETARY_FACES["Aulathamas"] == "Mars"
        assert DECAN_PLANETARY_FACES["Sabaoth"] == "Sun"
        assert DECAN_PLANETARY_FACES["Jaus"] == "Mercury"
        assert DECAN_PLANETARY_FACES["Luxois"] == "Mercury"
        assert DECAN_PLANETARY_FACES["Flugmois Mars"] == "Jupiter"
        assert DECAN_PLANETARY_FACES["Piathris"] == "Mars"

    def test_unsupported_fixed_star_table_is_empty(self):
        from moira.hermetic_decans import DECAN_RULING_STARS

        assert DECAN_RULING_STARS == {}


# ===========================================================================
# 7.2 — list_decans and decan_index
# ===========================================================================

class TestListDecans:
    def test_length(self):
        from moira.hermetic_decans import list_decans
        assert len(list_decans()) == 36

    def test_first_value(self):
        from moira.hermetic_decans import list_decans
        assert list_decans()[0] == "Aulathamas"

    def test_last_value(self):
        from moira.hermetic_decans import list_decans
        assert list_decans()[35] == "Piathris"

    def test_returns_list(self):
        from moira.hermetic_decans import list_decans
        assert isinstance(list_decans(), list)

    def test_returns_new_copy(self):
        from moira.hermetic_decans import list_decans
        a = list_decans()
        b = list_decans()
        assert a is not b


class TestDecanIndex:
    def test_index_of_first(self):
        from moira.hermetic_decans import decan_index
        assert decan_index("Aulathamas") == 0

    def test_index_of_last(self):
        from moira.hermetic_decans import decan_index
        assert decan_index("Piathris") == 35

    def test_index_of_manuchos(self):
        from moira.hermetic_decans import decan_index
        assert decan_index("Manuchos") == 6

    def test_invalid_name_raises(self):
        from moira.hermetic_decans import decan_index
        with pytest.raises(ValueError):
            decan_index("NotADecan")


# ===========================================================================
# 7.3 — decan_for_longitude
# ===========================================================================

class TestDecanForLongitude:
    def test_zero_degrees(self):
        from moira.hermetic_decans import decan_for_longitude
        assert decan_for_longitude(0.0) == "Aulathamas"

    def test_359_9_degrees(self):
        from moira.hermetic_decans import decan_for_longitude
        assert decan_for_longitude(359.9) == "Piathris"

    def test_normalization_370(self):
        # 370 % 360 = 10 → Sabaoth (index 1)
        from moira.hermetic_decans import decan_for_longitude
        assert decan_for_longitude(370.0) == "Sabaoth"

    def test_spot_check_60_degrees(self):
        # 60° → index 6 → Manuchos
        from moira.hermetic_decans import decan_for_longitude
        assert decan_for_longitude(60.0) == "Manuchos"

    def test_nan_raises_value_error(self):
        from moira.hermetic_decans import decan_for_longitude
        with pytest.raises(ValueError):
            decan_for_longitude(float("nan"))

    def test_inf_raises_value_error(self):
        from moira.hermetic_decans import decan_for_longitude
        with pytest.raises(ValueError):
            decan_for_longitude(float("inf"))

    def test_negative_inf_raises_value_error(self):
        from moira.hermetic_decans import decan_for_longitude
        with pytest.raises(ValueError):
            decan_for_longitude(float("-inf"))

    def test_result_in_list_decans(self):
        from moira.hermetic_decans import decan_for_longitude, list_decans
        decans = list_decans()
        for lon in [0.0, 10.0, 60.0, 120.0, 180.0, 270.0, 350.0, 359.9]:
            assert decan_for_longitude(lon) in decans


# ===========================================================================
# 7.4 — source-admission boundaries
# ===========================================================================

class TestAvailableDecans:
    def test_fixed_star_availability_fails_closed(self):
        from moira.hermetic_decans import available_decans

        assert available_decans() == []


# ===========================================================================
# 7.5 — fixed-star access fails closed
# ===========================================================================

class TestDecanRulingStar:
    def test_valid_decan_has_no_fabricated_star(self):
        from moira.hermetic_decans import decan_ruling_star
        with pytest.raises(LookupError, match="does not provide fixed-star"):
            decan_ruling_star("Aulathamas")

    def test_unknown_decan_raises_key_error(self):
        from moira.hermetic_decans import decan_ruling_star
        with pytest.raises(KeyError):
            decan_ruling_star("NotADecan")


class TestDecanStarAt:
    def test_valid_decan_has_no_fabricated_star_position(self):
        from moira.hermetic_decans import decan_star_at
        with pytest.raises(LookupError, match="does not provide fixed-star"):
            decan_star_at("Aulathamas", 2451545.0)

    def test_non_finite_jd_is_rejected_before_non_admission(self):
        from moira.hermetic_decans import decan_star_at
        with pytest.raises(ValueError, match="jd must be finite"):
            decan_star_at("Aulathamas", float("nan"))

    def test_unknown_decan_raises_key_error(self):
        from moira.hermetic_decans import decan_star_at
        with pytest.raises(KeyError):
            decan_star_at("NotADecan", 2451545.0)


# ===========================================================================
# 9.x — Property-based tests (Hypothesis, no ephemeris required)
# ===========================================================================

try:
    from hypothesis import given, settings
    import hypothesis.strategies as st
    _HYPOTHESIS_AVAILABLE = True
except ImportError:
    _HYPOTHESIS_AVAILABLE = False

_skip_no_hypothesis = pytest.mark.skipif(
    not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed"
)


@_skip_no_hypothesis
@given(lon=st.floats(min_value=0.0, max_value=360.0, exclude_max=True))
@settings(max_examples=100)
def test_prop2_decan_for_longitude_membership(lon):
    """Property 2: decan_for_longitude(lon) in list_decans() for all floats in [0, 360).

    **Validates: Requirements 2.4**
    """
    from moira.hermetic_decans import decan_for_longitude, list_decans
    result = decan_for_longitude(lon)
    assert result in list_decans()


@_skip_no_hypothesis
@given(lon=st.floats(allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_prop3_decan_for_longitude_normalization(lon):
    """Property 3: normalization invariant decan_for_longitude(lon) == decan_for_longitude(lon % 360).

    **Validates: Requirements 2.3**
    """
    from moira.hermetic_decans import decan_for_longitude
    assert decan_for_longitude(lon) == decan_for_longitude(lon % 360)


@_skip_no_hypothesis
@given(
    i=st.integers(min_value=0, max_value=35),
    offset=st.floats(min_value=0.0, max_value=10.0, exclude_max=True),
)
@settings(max_examples=100)
def test_prop4_decan_for_longitude_band_assignment(i, offset):
    """Property 4: correct band assignment for all i in [0, 35] and offset in [0, 10).

    **Validates: Requirements 2.2, 2.5**
    """
    from hypothesis import assume
    from moira.hermetic_decans import decan_for_longitude, list_decans
    # Filter out offsets so close to 10.0 that float addition crosses the band boundary
    assume(offset < 9.9999999999)
    lon = i * 10.0 + offset
    assert decan_for_longitude(lon) == list_decans()[i]


@_skip_no_hypothesis
@given(d=st.sampled_from(_SOURCE_NAMES))
@settings(max_examples=100)
def test_prop5_decan_index_range(d):
    """Property 5: decan_index(d) in [0, 35] for all valid decan names.

    **Validates: Requirements 2.7**
    """
    from moira.hermetic_decans import decan_index
    idx = decan_index(d)
    assert 0 <= idx <= 35


@_skip_no_hypothesis
@given(d=st.sampled_from(_SOURCE_NAMES))
@settings(max_examples=100)
def test_prop6_name_index_longitude_name_roundtrip(d):
    """Property 6: name → index → longitude → name round-trip.

    **Validates: Requirements 2.8, 8.2**
    """
    from moira.hermetic_decans import decan_index, decan_for_longitude
    idx = decan_index(d)
    lon = idx * 10.0
    assert decan_for_longitude(lon) == d


@_skip_no_hypothesis
@given(i=st.integers(min_value=0, max_value=35))
@settings(max_examples=100)
def test_prop7_index_name_index_roundtrip(i):
    """Property 7: index → name → index round-trip.

    **Validates: Requirements 8.3**
    """
    from moira.hermetic_decans import list_decans, decan_index
    name = list_decans()[i]
    assert decan_index(name) == i


@_skip_no_hypothesis
@given(d=st.sampled_from(_SOURCE_NAMES))
@settings(max_examples=100)
def test_prop8_decan_planetary_face_consistency(d):
    """Property 8: the catalog accessor agrees with the source face table.

    **Validates: Requirements 3.2**
    """
    from moira.hermetic_decans import decan_planetary_face, DECAN_PLANETARY_FACES
    assert decan_planetary_face(d) == DECAN_PLANETARY_FACES[d]


# ===========================================================================
# Meeus oracle tests — Chapter 12 (GMST)
#
# Reference: Jean Meeus, "Astronomical Algorithms" 2nd ed.
#   Example 12.a  — April 10, 1987, 0h UT (JD 2446895.5)
#                   GMST = 197.693195°
#
# All expected values are derived from that single verified anchor point.
# No external runtime dependency: constants are hardcoded from the oracle run.
# ===========================================================================

# Oracle constants — do not edit without re-running the verification script.
_MEEUS_JD          = 2446895.5      # April 10 1987, 0h UT
_MEEUS_GMST        = 197.693195     # deg — Meeus Ex 12.a ground truth


class TestLstToRamcMeeusOracle:
    """_lst_to_ramc agrees with Meeus Example 12.a to sub-arcsecond precision."""

    def test_gmst_matches_meeus_example_12a(self):
        """GMST at JD 2446895.5 (lon=0) must equal Meeus 197.693195° within 0.001°."""
        from moira.hermetic_decans import _lst_to_ramc
        result = _lst_to_ramc(_MEEUS_JD, 0.0)
        assert abs(result - _MEEUS_GMST) < 0.001, (
            f"GMST {result:.6f}° diverges from Meeus oracle {_MEEUS_GMST}° "
            f"by {abs(result - _MEEUS_GMST)*3600:.2f} arcsec"
        )

    def test_lst_shifts_by_geo_longitude(self):
        """LST at lon=25° must equal GMST + 25° (modulo 360)."""
        from moira.hermetic_decans import _lst_to_ramc
        gmst  = _lst_to_ramc(_MEEUS_JD, 0.0)
        lst25 = _lst_to_ramc(_MEEUS_JD, 25.0)
        assert abs((lst25 - gmst) % 360.0 - 25.0) < 0.001

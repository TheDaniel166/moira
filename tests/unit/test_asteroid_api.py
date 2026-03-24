"""
Unit tests for the three new asteroid API modules:
  - moira.classical_asteroids
  - moira.tno
  - moira.main_belt

No kernel is required for any of these tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from moira.asteroids import ASTEROID_NAIF, AsteroidData
from moira.classical_asteroids import (
    CERES, PALLAS, JUNO, VESTA,
    CLASSICAL_NAMES,
    list_classical_asteroids,
    available_classical_asteroids,
)
from moira.tno import (
    IXION, QUAOAR, VARUNA, ORCUS,
    TNO_NAMES,
    list_tnos,
    available_tnos,
)
from moira.main_belt import (
    MAIN_BELT_NAMES,
    list_main_belt,
    available_main_belt,
    main_belt_at,
)


# ---------------------------------------------------------------------------
# 4.1  Constant values
# ---------------------------------------------------------------------------

class TestClassicalConstants:
    def test_ceres(self):
        assert CERES == 2000001

    def test_pallas(self):
        assert PALLAS == 2000002

    def test_juno(self):
        assert JUNO == 2000003

    def test_vesta(self):
        assert VESTA == 2000004

    def test_ceres_matches_asteroid_naif(self):
        assert CERES == ASTEROID_NAIF["Ceres"]

    def test_pallas_matches_asteroid_naif(self):
        assert PALLAS == ASTEROID_NAIF["Pallas"]

    def test_juno_matches_asteroid_naif(self):
        assert JUNO == ASTEROID_NAIF["Juno"]

    def test_vesta_matches_asteroid_naif(self):
        assert VESTA == ASTEROID_NAIF["Vesta"]


class TestTNOConstants:
    def test_ixion(self):
        assert IXION == 2028978

    def test_quaoar(self):
        assert QUAOAR == 2050000

    def test_varuna(self):
        assert VARUNA == 2020000

    def test_orcus(self):
        assert ORCUS == 2090482

    def test_ixion_matches_asteroid_naif(self):
        assert IXION == ASTEROID_NAIF["Ixion"]

    def test_quaoar_matches_asteroid_naif(self):
        assert QUAOAR == ASTEROID_NAIF["Quaoar"]

    def test_varuna_matches_asteroid_naif(self):
        assert VARUNA == ASTEROID_NAIF["Varuna"]

    def test_orcus_matches_asteroid_naif(self):
        assert ORCUS == ASTEROID_NAIF["Orcus"]


# ---------------------------------------------------------------------------
# 4.2  *_NAMES dict structure
# ---------------------------------------------------------------------------

class TestClassicalNames:
    def test_has_exactly_4_entries(self):
        assert len(CLASSICAL_NAMES) == 4

    def test_ceres_entry(self):
        assert CLASSICAL_NAMES[CERES] == "Ceres"

    def test_pallas_entry(self):
        assert CLASSICAL_NAMES[PALLAS] == "Pallas"

    def test_juno_entry(self):
        assert CLASSICAL_NAMES[JUNO] == "Juno"

    def test_vesta_entry(self):
        assert CLASSICAL_NAMES[VESTA] == "Vesta"


class TestTNONames:
    def test_has_exactly_4_entries(self):
        assert len(TNO_NAMES) == 4

    def test_ixion_entry(self):
        assert TNO_NAMES[IXION] == "Ixion"

    def test_quaoar_entry(self):
        assert TNO_NAMES[QUAOAR] == "Quaoar"

    def test_varuna_entry(self):
        assert TNO_NAMES[VARUNA] == "Varuna"

    def test_orcus_entry(self):
        assert TNO_NAMES[ORCUS] == "Orcus"


class TestMainBeltNames:
    # Centaur, classical, and TNO NAIF IDs that must NOT appear in MAIN_BELT_NAMES
    _CENTAUR_IDS  = {2002060, 2005145, 2007066, 2008405, 2010199, 2010370}
    _CLASSICAL_IDS = {2000001, 2000002, 2000003, 2000004}
    _TNO_IDS       = {2028978, 2050000, 2020000, 2090482}

    def test_has_exactly_36_entries(self):
        assert len(MAIN_BELT_NAMES) == 36

    def test_no_overlap_with_classical(self):
        assert not (set(MAIN_BELT_NAMES.keys()) & self._CLASSICAL_IDS)

    def test_no_overlap_with_centaurs(self):
        assert not (set(MAIN_BELT_NAMES.keys()) & self._CENTAUR_IDS)

    def test_no_overlap_with_tnos(self):
        assert not (set(MAIN_BELT_NAMES.keys()) & self._TNO_IDS)

    def test_astraea_present(self):
        assert 2000005 in MAIN_BELT_NAMES
        assert MAIN_BELT_NAMES[2000005] == "Astraea"

    def test_virginia_present(self):
        assert 2000050 in MAIN_BELT_NAMES
        assert MAIN_BELT_NAMES[2000050] == "Virginia"


# ---------------------------------------------------------------------------
# 4.3  list_*() return types and contents (no kernel needed)
# ---------------------------------------------------------------------------

class TestListFunctions:
    def test_list_classical_asteroids_returns_correct_list(self):
        result = list_classical_asteroids()
        assert result == ["Ceres", "Pallas", "Juno", "Vesta"]

    def test_list_tnos_returns_correct_list(self):
        result = list_tnos()
        assert result == ["Ixion", "Quaoar", "Varuna", "Orcus"]

    def test_list_main_belt_returns_list(self):
        result = list_main_belt()
        assert isinstance(result, list)

    def test_list_main_belt_has_36_entries(self):
        result = list_main_belt()
        assert len(result) == 36

    def test_list_main_belt_contains_astraea(self):
        assert "Astraea" in list_main_belt()

    def test_list_main_belt_does_not_contain_eros(self):
        # Eros is NOT in the 36 main-belt bodies (Astraea through Virginia)
        assert "Eros" not in list_main_belt()

    def test_list_main_belt_all_strings(self):
        for name in list_main_belt():
            assert isinstance(name, str)


# ---------------------------------------------------------------------------
# 4.4  available_*() does not raise when no kernel is loaded
# ---------------------------------------------------------------------------

class TestAvailableNoKernel:
    def test_available_classical_returns_empty_when_no_kernel(self):
        with patch("moira.classical_asteroids.available_in_kernel", return_value=[]):
            result = available_classical_asteroids()
        assert result == []

    def test_available_tnos_returns_empty_when_no_kernel(self):
        with patch("moira.tno.available_in_kernel", return_value=[]):
            result = available_tnos()
        assert result == []

    def test_available_main_belt_returns_empty_when_no_kernel(self):
        with patch("moira.main_belt.available_in_kernel", return_value=[]):
            result = available_main_belt()
        assert result == []


# ---------------------------------------------------------------------------
# 4.5  available_*() subset invariant with a mocked kernel
# ---------------------------------------------------------------------------

class TestAvailableSubsetInvariant:
    def test_available_classical_is_subset_of_list(self):
        mocked = ["Ceres", "Ixion", "Astraea"]  # mixed — only Ceres is classical
        with patch("moira.classical_asteroids.available_in_kernel", return_value=mocked):
            result = available_classical_asteroids()
        assert set(result).issubset(set(list_classical_asteroids()))

    def test_available_tnos_is_subset_of_list(self):
        mocked = ["Ceres", "Ixion", "Astraea"]  # only Ixion is a TNO
        with patch("moira.tno.available_in_kernel", return_value=mocked):
            result = available_tnos()
        assert set(result).issubset(set(list_tnos()))

    def test_available_main_belt_is_subset_of_list(self):
        mocked = ["Ceres", "Ixion", "Astraea"]  # only Astraea is main-belt
        with patch("moira.main_belt.available_in_kernel", return_value=mocked):
            result = available_main_belt()
        assert set(result).issubset(set(list_main_belt()))

    def test_available_classical_only_returns_matching_names(self):
        mocked = ["Ceres", "Vesta", "Astraea", "Ixion"]
        with patch("moira.classical_asteroids.available_in_kernel", return_value=mocked):
            result = available_classical_asteroids()
        assert set(result) == {"Ceres", "Vesta"}

    def test_available_tnos_only_returns_matching_names(self):
        mocked = ["Ixion", "Quaoar", "Ceres", "Astraea"]
        with patch("moira.tno.available_in_kernel", return_value=mocked):
            result = available_tnos()
        assert set(result) == {"Ixion", "Quaoar"}


# ---------------------------------------------------------------------------
# 4.6  Cross-group delegation does not raise (structural, no kernel)
# ---------------------------------------------------------------------------

def _make_dummy_asteroid_data(name: str = "Chiron", naif_id: int = 2002060) -> AsteroidData:
    """Create a minimal AsteroidData for use in mocks."""
    return AsteroidData(
        name=name,
        naif_id=naif_id,
        longitude=45.0,
        latitude=1.5,
        distance=1_500_000.0,
        speed=0.5,
        retrograde=False,
    )


class TestCrossGroupDelegation:
    def test_main_belt_at_with_chiron_does_not_raise(self):
        dummy = _make_dummy_asteroid_data("Chiron", 2002060)
        with patch("moira.main_belt.asteroid_at", return_value=dummy):
            result = main_belt_at("Chiron", 2451545.0)
        assert result is dummy

    def test_main_belt_at_returns_asteroid_data_instance(self):
        dummy = _make_dummy_asteroid_data("Chiron", 2002060)
        with patch("moira.main_belt.asteroid_at", return_value=dummy):
            result = main_belt_at("Chiron", 2451545.0)
        assert isinstance(result, AsteroidData)

    def test_main_belt_at_passes_name_and_jd_to_asteroid_at(self):
        dummy = _make_dummy_asteroid_data("Chiron", 2002060)
        with patch("moira.main_belt.asteroid_at", return_value=dummy) as mock_fn:
            main_belt_at("Chiron", 2451545.0)
        mock_fn.assert_called_once_with("Chiron", 2451545.0)


# ---------------------------------------------------------------------------
# Property-based tests (Hypothesis) — require ephemeris kernels
# ---------------------------------------------------------------------------

from hypothesis import given, settings
from hypothesis import strategies as st

from moira.classical_asteroids import classical_asteroid_at, ceres_at, pallas_at, juno_at, vesta_at
from moira.tno import tno_at, ixion_at, quaoar_at, varuna_at, orcus_at
from moira.asteroids import asteroid_at


# ---------------------------------------------------------------------------
# 6.1  Property 1 — Delegation round-trip for classical asteroids
# Validates: Requirements 1.3, 1.8
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_classical_asteroid_at_delegation_round_trip(jd):
    """**Validates: Requirements 1.3, 1.8**"""
    for name in list_classical_asteroids():
        r1 = classical_asteroid_at(name, jd)
        r2 = asteroid_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.distance  == r2.distance
        assert r1.speed     == r2.speed


# ---------------------------------------------------------------------------
# 6.2  Property 1 — Delegation round-trip for main-belt bodies
# Validates: Requirements 2.3, 2.7
# ---------------------------------------------------------------------------

_MAIN_BELT_SAMPLE = ["Astraea", "Hebe", "Psyche", "Fortuna", "Lutetia"]

@pytest.mark.requires_ephemeris
@settings(deadline=None)
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_main_belt_at_delegation_round_trip(jd):
    """**Validates: Requirements 2.3, 2.7**"""
    from moira.main_belt import main_belt_at
    for name in _MAIN_BELT_SAMPLE:
        r1 = main_belt_at(name, jd)
        r2 = asteroid_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.distance  == r2.distance
        assert r1.speed     == r2.speed


# ---------------------------------------------------------------------------
# 6.3  Property 1 — Delegation round-trip for TNOs
# Validates: Requirements 3.3, 3.8
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@settings(deadline=None)
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_tno_at_delegation_round_trip(jd):
    """**Validates: Requirements 3.3, 3.8**"""
    for name in list_tnos():
        r1 = tno_at(name, jd)
        r2 = asteroid_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.distance  == r2.distance
        assert r1.speed     == r2.speed


# ---------------------------------------------------------------------------
# 6.4  Property 2 — Per-body function identity for classical asteroids
# Validates: Requirements 1.4, 1.7
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_ceres_at_identity(jd):
    """**Validates: Requirements 1.4, 1.7**"""
    result = ceres_at(jd)
    direct = asteroid_at(CERES, jd)
    assert result.name      == "Ceres"
    assert result.naif_id   == CERES
    assert result.longitude == direct.longitude
    assert result.latitude  == direct.latitude
    assert result.distance  == direct.distance
    assert result.speed     == direct.speed


@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_pallas_at_identity(jd):
    """**Validates: Requirements 1.4, 1.7**"""
    result = pallas_at(jd)
    direct = asteroid_at(PALLAS, jd)
    assert result.name      == "Pallas"
    assert result.naif_id   == PALLAS
    assert result.longitude == direct.longitude
    assert result.latitude  == direct.latitude
    assert result.distance  == direct.distance
    assert result.speed     == direct.speed


@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_juno_at_identity(jd):
    """**Validates: Requirements 1.4, 1.7**"""
    result = juno_at(jd)
    direct = asteroid_at(JUNO, jd)
    assert result.name      == "Juno"
    assert result.naif_id   == JUNO
    assert result.longitude == direct.longitude
    assert result.latitude  == direct.latitude
    assert result.distance  == direct.distance
    assert result.speed     == direct.speed


@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_vesta_at_identity(jd):
    """**Validates: Requirements 1.4, 1.7**"""
    result = vesta_at(jd)
    direct = asteroid_at(VESTA, jd)
    assert result.name      == "Vesta"
    assert result.naif_id   == VESTA
    assert result.longitude == direct.longitude
    assert result.latitude  == direct.latitude
    assert result.distance  == direct.distance
    assert result.speed     == direct.speed


# ---------------------------------------------------------------------------
# 6.5  Property 2 — Per-body function identity for TNOs
# Validates: Requirements 3.4, 3.7
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_ixion_at_identity(jd):
    """**Validates: Requirements 3.4, 3.7**"""
    result = ixion_at(jd)
    direct = asteroid_at(IXION, jd)
    assert result.name      == "Ixion"
    assert result.naif_id   == IXION
    assert result.longitude == direct.longitude
    assert result.latitude  == direct.latitude
    assert result.distance  == direct.distance
    assert result.speed     == direct.speed


@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_quaoar_at_identity(jd):
    """**Validates: Requirements 3.4, 3.7**"""
    result = quaoar_at(jd)
    direct = asteroid_at(QUAOAR, jd)
    assert result.name      == "Quaoar"
    assert result.naif_id   == QUAOAR
    assert result.longitude == direct.longitude
    assert result.latitude  == direct.latitude
    assert result.distance  == direct.distance
    assert result.speed     == direct.speed


@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_varuna_at_identity(jd):
    """**Validates: Requirements 3.4, 3.7**"""
    result = varuna_at(jd)
    direct = asteroid_at(VARUNA, jd)
    assert result.name      == "Varuna"
    assert result.naif_id   == VARUNA
    assert result.longitude == direct.longitude
    assert result.latitude  == direct.latitude
    assert result.distance  == direct.distance
    assert result.speed     == direct.speed


@pytest.mark.requires_ephemeris
@given(jd=st.floats(min_value=2415020.5, max_value=2488069.5, allow_nan=False, allow_infinity=False))
def test_orcus_at_identity(jd):
    """**Validates: Requirements 3.4, 3.7**"""
    result = orcus_at(jd)
    direct = asteroid_at(ORCUS, jd)
    assert result.name      == "Orcus"
    assert result.naif_id   == ORCUS
    assert result.longitude == direct.longitude
    assert result.latitude  == direct.latitude
    assert result.distance  == direct.distance
    assert result.speed     == direct.speed


# ---------------------------------------------------------------------------
# 6.6  Property 3 — Availability subset invariant
# Validates: Requirements 1.6, 2.6, 3.6, 4.5
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_available_classical_is_subset_of_list():
    """**Validates: Requirements 1.6, 4.5**"""
    assert set(available_classical_asteroids()) <= set(list_classical_asteroids())


@pytest.mark.requires_ephemeris
def test_available_main_belt_is_subset_of_list():
    """**Validates: Requirements 2.6, 4.5**"""
    from moira.main_belt import available_main_belt, list_main_belt
    assert set(available_main_belt()) <= set(list_main_belt())


@pytest.mark.requires_ephemeris
def test_available_tnos_is_subset_of_list():
    """**Validates: Requirements 3.6, 4.5**"""
    assert set(available_tnos()) <= set(list_tnos())

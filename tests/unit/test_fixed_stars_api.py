"""
Unit and property-based tests for the Fixed Stars API modules.

Unit tests (6.x): use mocking — no catalog file needed.
Property tests (8.x): marked @pytest.mark.requires_ephemeris — require sefstars.txt.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dummy_star(name: str = "Aldebaran"):
    """Return a minimal StarPosition-like mock."""
    from moira.fixed_stars import StarPosition
    return StarPosition(
        name=name,
        nomenclature="alTau",
        longitude=69.5,
        latitude=-5.5,
        magnitude=0.87,
    )


# ===========================================================================
# 6.1 — String constant values: tradition-based modules
# ===========================================================================

class TestRoyalStarConstants:
    def test_aldebaran(self):
        from moira.royal_stars import ALDEBARAN
        assert ALDEBARAN == "Aldebaran"

    def test_regulus(self):
        from moira.royal_stars import REGULUS
        assert REGULUS == "Regulus"

    def test_antares(self):
        from moira.royal_stars import ANTARES
        assert ANTARES == "Antares"

    def test_fomalhaut(self):
        from moira.royal_stars import FOMALHAUT
        assert FOMALHAUT == "Fomalhaut"


class TestBehenianStarConstants:
    def test_algol(self):
        from moira.behenian_stars import ALGOL
        assert ALGOL == "Algol"

    def test_alcyone(self):
        from moira.behenian_stars import ALCYONE
        assert ALCYONE == "Alcyone"

    def test_aldebaran(self):
        from moira.behenian_stars import ALDEBARAN
        assert ALDEBARAN == "Aldebaran"

    def test_capella(self):
        from moira.behenian_stars import CAPELLA
        assert CAPELLA == "Capella"

    def test_sirius(self):
        from moira.behenian_stars import SIRIUS
        assert SIRIUS == "Sirius"

    def test_procyon(self):
        from moira.behenian_stars import PROCYON
        assert PROCYON == "Procyon"

    def test_regulus(self):
        from moira.behenian_stars import REGULUS
        assert REGULUS == "Regulus"

    def test_algorab(self):
        from moira.behenian_stars import ALGORAB
        assert ALGORAB == "Algorab"

    def test_spica(self):
        from moira.behenian_stars import SPICA
        assert SPICA == "Spica"

    def test_arcturus(self):
        from moira.behenian_stars import ARCTURUS
        assert ARCTURUS == "Arcturus"

    def test_alphecca(self):
        from moira.behenian_stars import ALPHECCA
        assert ALPHECCA == "Alphecca"

    def test_antares(self):
        from moira.behenian_stars import ANTARES
        assert ANTARES == "Antares"

    def test_vega(self):
        from moira.behenian_stars import VEGA
        assert VEGA == "Vega"

    def test_algedi(self):
        from moira.behenian_stars import ALGEDI
        assert ALGEDI == "Algedi"

    def test_fomalhaut(self):
        from moira.behenian_stars import FOMALHAUT
        assert FOMALHAUT == "Fomalhaut"


class TestFixedStarGroupsConstants:
    def test_algol(self):
        from moira.fixed_star_groups import ALGOL
        assert ALGOL == "Algol"

    def test_vega(self):
        from moira.fixed_star_groups import VEGA
        assert VEGA == "Vega"

    def test_sirius(self):
        from moira.fixed_star_groups import SIRIUS
        assert SIRIUS == "Sirius"

    def test_ras_algethi(self):
        from moira.fixed_star_groups import RAS_ALGETHI
        assert RAS_ALGETHI == "Ras Algethi"

    def test_hyadum_i(self):
        from moira.fixed_star_groups import HYADUM_I
        assert HYADUM_I == "Hyadum I"

    def test_sterope(self):
        from moira.fixed_star_groups import STEROPE
        assert STEROPE == "Sterope I"


# ===========================================================================
# 6.2 — *_NAMES dict structure: tradition-based modules
# ===========================================================================

class TestRoyalStarNamesDict:
    def test_length(self):
        from moira.royal_stars import ROYAL_STAR_NAMES
        assert len(ROYAL_STAR_NAMES) == 4

    def test_keys_and_values(self):
        from moira.royal_stars import ROYAL_STAR_NAMES
        assert ROYAL_STAR_NAMES["Aldebaran"] == "Aldebaran"
        assert ROYAL_STAR_NAMES["Regulus"]   == "Regulus"
        assert ROYAL_STAR_NAMES["Antares"]   == "Antares"
        assert ROYAL_STAR_NAMES["Fomalhaut"] == "Fomalhaut"


class TestBehenianStarNamesDict:
    def test_length(self):
        from moira.behenian_stars import BEHENIAN_STAR_NAMES
        assert len(BEHENIAN_STAR_NAMES) == 15

    def test_contains_algol(self):
        from moira.behenian_stars import BEHENIAN_STAR_NAMES
        assert "Algol" in BEHENIAN_STAR_NAMES.values()

    def test_contains_spica(self):
        from moira.behenian_stars import BEHENIAN_STAR_NAMES
        assert "Spica" in BEHENIAN_STAR_NAMES.values()


class TestFixedStarGroupsNamesDict:
    def test_contains_algol(self):
        from moira.fixed_star_groups import FIXED_STAR_NAMES
        assert "Algol" in FIXED_STAR_NAMES.values()

    def test_contains_vega(self):
        from moira.fixed_star_groups import FIXED_STAR_NAMES
        assert "Vega" in FIXED_STAR_NAMES.values()

    def test_contains_ras_algethi(self):
        from moira.fixed_star_groups import FIXED_STAR_NAMES
        assert "Ras Algethi" in FIXED_STAR_NAMES.values()

    def test_contains_hyadum_i(self):
        from moira.fixed_star_groups import FIXED_STAR_NAMES
        assert "Hyadum I" in FIXED_STAR_NAMES.values()


# ===========================================================================
# 6.3 — Group tuples in fixed_star_groups
# ===========================================================================

class TestGroupTuples:
    def test_pleiades(self):
        from moira.fixed_star_groups import PLEIADES
        assert PLEIADES == (
            "Alcyone", "Maia", "Electra", "Taygeta", "Merope", "Celaeno", "Sterope I",
        )

    def test_hyades(self):
        from moira.fixed_star_groups import HYADES
        assert HYADES == ("Ain", "Hyadum I", "Hyadum II")

    def test_ptolemy_stars_length(self):
        from moira.fixed_star_groups import PTOLEMY_STARS
        assert len(PTOLEMY_STARS) == 15

    def test_ptolemy_stars_contains_algol(self):
        from moira.fixed_star_groups import PTOLEMY_STARS
        assert "Algol" in PTOLEMY_STARS

    def test_ptolemy_stars_contains_fomalhaut(self):
        from moira.fixed_star_groups import PTOLEMY_STARS
        assert "Fomalhaut" in PTOLEMY_STARS


# ===========================================================================
# 6.4 — list_*() return types and contents
# ===========================================================================

class TestListFunctions:
    def test_list_royal_stars(self):
        from moira.royal_stars import list_royal_stars
        result = list_royal_stars()
        assert result == ["Aldebaran", "Regulus", "Antares", "Fomalhaut"]

    def test_list_behenian_stars_type_and_length(self):
        from moira.behenian_stars import list_behenian_stars
        result = list_behenian_stars()
        assert isinstance(result, list)
        assert len(result) == 15

    def test_list_behenian_stars_contains_algol(self):
        from moira.behenian_stars import list_behenian_stars
        assert "Algol" in list_behenian_stars()

    def test_list_behenian_stars_contains_spica(self):
        from moira.behenian_stars import list_behenian_stars
        assert "Spica" in list_behenian_stars()

    def test_list_pleiades(self):
        from moira.fixed_star_groups import list_pleiades, PLEIADES
        assert list_pleiades() == list(PLEIADES)

    def test_list_hyades(self):
        from moira.fixed_star_groups import list_hyades, HYADES
        assert list_hyades() == list(HYADES)

    def test_list_ptolemy_stars(self):
        from moira.fixed_star_groups import list_ptolemy_stars, PTOLEMY_STARS
        assert list_ptolemy_stars() == list(PTOLEMY_STARS)

    def test_list_taurus_stars_length(self):
        from moira.constellations.stars_taurus import list_taurus_stars
        result = list_taurus_stars()
        assert isinstance(result, list)
        assert len(result) == 25

    def test_list_taurus_stars_contains_aldebaran(self):
        from moira.constellations.stars_taurus import list_taurus_stars
        assert "Aldebaran" in list_taurus_stars()

    def test_list_taurus_stars_contains_alcyone(self):
        from moira.constellations.stars_taurus import list_taurus_stars
        assert "Alcyone" in list_taurus_stars()

    def test_list_scorpius_stars_length(self):
        from moira.constellations.stars_scorpius import list_scorpius_stars
        result = list_scorpius_stars()
        assert isinstance(result, list)
        assert len(result) == 16

    def test_list_scorpius_stars_contains_antares(self):
        from moira.constellations.stars_scorpius import list_scorpius_stars
        assert "Antares" in list_scorpius_stars()


# ===========================================================================
# 6.5 — available_*() does not raise when catalog is empty
# ===========================================================================

class TestAvailableEmptyCatalog:
    def _patch_list_stars(self, module_path: str):
        return patch(f"{module_path}.list_stars", return_value=[])

    def test_available_royal_stars_empty(self):
        with patch("moira.royal_stars.list_stars", return_value=[]):
            from moira.royal_stars import available_royal_stars
            assert available_royal_stars() == []

    def test_available_behenian_stars_empty(self):
        with patch("moira.behenian_stars.list_stars", return_value=[]):
            from moira.behenian_stars import available_behenian_stars
            assert available_behenian_stars() == []

    def test_available_fixed_stars_empty(self):
        with patch("moira.fixed_star_groups.list_stars", return_value=[]):
            from moira.fixed_star_groups import available_fixed_stars
            assert available_fixed_stars() == []

    def test_available_taurus_stars_empty(self):
        with patch("moira.constellations.stars_taurus.list_stars", return_value=[]):
            from moira.constellations.stars_taurus import available_taurus_stars
            assert available_taurus_stars() == []

    def test_available_scorpius_stars_empty(self):
        with patch("moira.constellations.stars_scorpius.list_stars", return_value=[]):
            from moira.constellations.stars_scorpius import available_scorpius_stars
            assert available_scorpius_stars() == []

    def test_available_orion_stars_empty(self):
        with patch("moira.constellations.stars_orion.list_stars", return_value=[]):
            from moira.constellations.stars_orion import available_orion_stars
            assert available_orion_stars() == []


# ===========================================================================
# 6.6 — available_*() subset invariant with mocked catalog
# ===========================================================================

class TestAvailableSubsetInvariant:
    def test_royal_subset(self):
        partial = ["Aldebaran", "Vega", "Sirius"]
        with patch("moira.royal_stars.list_stars", return_value=partial):
            from moira.royal_stars import available_royal_stars, list_royal_stars
            avail = available_royal_stars()
            full  = list_royal_stars()
            assert set(avail) <= set(full)
            assert "Aldebaran" in avail
            assert "Vega" not in avail  # not in royal stars

    def test_behenian_subset(self):
        partial = ["Algol", "Spica", "Vega", "Sirius"]
        with patch("moira.behenian_stars.list_stars", return_value=partial):
            from moira.behenian_stars import available_behenian_stars, list_behenian_stars
            avail = available_behenian_stars()
            full  = list_behenian_stars()
            assert set(avail) <= set(full)

    def test_taurus_subset(self):
        partial = ["Aldebaran", "Alcyone", "Rigel"]
        with patch("moira.constellations.stars_taurus.list_stars", return_value=partial):
            from moira.constellations.stars_taurus import available_taurus_stars, list_taurus_stars
            avail = available_taurus_stars()
            full  = list_taurus_stars()
            assert set(avail) <= set(full)
            assert "Rigel" not in avail  # not a Taurus star

    def test_scorpius_subset(self):
        partial = ["Antares", "Shaula", "Vega"]
        with patch("moira.constellations.stars_scorpius.list_stars", return_value=partial):
            from moira.constellations.stars_scorpius import available_scorpius_stars, list_scorpius_stars
            avail = available_scorpius_stars()
            full  = list_scorpius_stars()
            assert set(avail) <= set(full)


# ===========================================================================
# 6.7 — Per-body function delegation (structural, no catalog)
# ===========================================================================

class TestPerBodyDelegation:
    def test_regulus_at_royal(self):
        dummy = _dummy_star("Regulus")
        with patch("moira.royal_stars.fixed_star_at", return_value=dummy):
            from moira.royal_stars import regulus_at
            result = regulus_at(2451545.0)
            assert result is dummy

    def test_algol_at_behenian(self):
        dummy = _dummy_star("Algol")
        with patch("moira.behenian_stars.fixed_star_at", return_value=dummy):
            from moira.behenian_stars import algol_at
            result = algol_at(2451545.0)
            assert result is dummy

    def test_aldebaran_at_taurus(self):
        dummy = _dummy_star("Aldebaran")
        with patch("moira.constellations.stars_taurus.fixed_star_at", return_value=dummy):
            from moira.constellations.stars_taurus import aldebaran_at
            result = aldebaran_at(2451545.0)
            assert result is dummy


# ===========================================================================
# 6.8 — String constant values: representative constellation modules
# ===========================================================================

class TestConstellationConstants:
    def test_taurus_aldebaran(self):
        from moira.constellations.stars_taurus import ALDEBARAN
        assert ALDEBARAN == "Aldebaran"

    def test_taurus_sterope_i(self):
        from moira.constellations.stars_taurus import STEROPE_I
        assert STEROPE_I == "Sterope I"

    def test_taurus_hyadum_i(self):
        from moira.constellations.stars_taurus import HYADUM_I
        assert HYADUM_I == "Hyadum I"

    def test_scorpius_antares(self):
        from moira.constellations.stars_scorpius import ANTARES
        assert ANTARES == "Antares"

    def test_orion_rigel(self):
        from moira.constellations.stars_orion import RIGEL
        assert RIGEL == "Rigel"

    def test_ursa_major_dubhe(self):
        from moira.constellations.stars_ursa_major import DUBHE
        assert DUBHE == "Dubhe"

    def test_draco_nodus_ii(self):
        from moira.constellations.stars_draco import NODUS_II
        assert NODUS_II == "Nodus II"

    def test_aquila_deneb_el_okab_borealis(self):
        from moira.constellations.stars_aquila import DENEB_EL_OKAB_BOREALIS
        assert DENEB_EL_OKAB_BOREALIS == "Deneb el Okab Borealis"


# ===========================================================================
# 6.9 — *_NAMES dict structure: representative constellation modules
# ===========================================================================

class TestConstellationNamesDicts:
    def test_taurus_length(self):
        from moira.constellations.stars_taurus import TAURUS_STAR_NAMES
        assert len(TAURUS_STAR_NAMES) == 25

    def test_scorpius_length(self):
        from moira.constellations.stars_scorpius import SCORPIUS_STAR_NAMES
        assert len(SCORPIUS_STAR_NAMES) == 16

    def test_orion_length(self):
        from moira.constellations.stars_orion import ORION_STAR_NAMES
        assert len(ORION_STAR_NAMES) == 12

    def test_ursa_major_length(self):
        from moira.constellations.stars_ursa_major import URSA_MAJOR_STAR_NAMES
        assert len(URSA_MAJOR_STAR_NAMES) == 17


# ===========================================================================
# 8.x — Property-based tests (require sefstars.txt)
# ===========================================================================

try:
    from hypothesis import given, settings
    import hypothesis.strategies as st
    _HYPOTHESIS_AVAILABLE = True
except ImportError:
    given = settings = st = None
    _HYPOTHESIS_AVAILABLE = False

_JD_STRATEGY = (
    st.floats(min_value=2415020.5, max_value=2488069.5)
    if _HYPOTHESIS_AVAILABLE else None
)


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_royal_star_at_delegation_roundtrip(jd):
    """Property 1: royal_star_at delegates correctly to fixed_star_at."""
    from moira.royal_stars import royal_star_at, list_royal_stars
    from moira.fixed_stars import fixed_star_at
    for name in list_royal_stars():
        r1 = royal_star_at(name, jd)
        r2 = fixed_star_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.magnitude == r2.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_behenian_star_at_delegation_roundtrip(jd):
    """Property 1: behenian_star_at delegates correctly to fixed_star_at."""
    from moira.behenian_stars import behenian_star_at, list_behenian_stars
    from moira.fixed_stars import fixed_star_at
    for name in list_behenian_stars():
        r1 = behenian_star_at(name, jd)
        r2 = fixed_star_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.magnitude == r2.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_fixed_star_group_at_delegation_roundtrip(jd):
    """Property 1: fixed_star_group_at delegates correctly to fixed_star_at."""
    from moira.fixed_star_groups import fixed_star_group_at, list_fixed_stars
    from moira.fixed_stars import fixed_star_at
    # Sample a representative subset to keep test fast
    sample = ["Algol", "Aldebaran", "Sirius", "Vega", "Antares", "Fomalhaut"]
    for name in sample:
        r1 = fixed_star_group_at(name, jd)
        r2 = fixed_star_at(name, jd)
        assert r1.longitude == r2.longitude
        assert r1.latitude  == r2.latitude
        assert r1.magnitude == r2.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_constellation_dispatcher_delegation_roundtrip(jd):
    """Property 1: constellation dispatchers delegate correctly to fixed_star_at."""
    from moira.fixed_stars import fixed_star_at
    from moira.constellations.stars_taurus import taurus_star_at, list_taurus_stars
    from moira.constellations.stars_scorpius import scorpius_star_at, list_scorpius_stars
    from moira.constellations.stars_orion import orion_star_at, list_orion_stars
    from moira.constellations.stars_ursa_major import ursa_major_star_at, list_ursa_major_stars

    for dispatcher, names in [
        (taurus_star_at,     list_taurus_stars()),
        (scorpius_star_at,   list_scorpius_stars()),
        (orion_star_at,      list_orion_stars()),
        (ursa_major_star_at, list_ursa_major_stars()),
    ]:
        for name in names:
            r1 = dispatcher(name, jd)
            r2 = fixed_star_at(name, jd)
            assert r1.longitude == r2.longitude
            assert r1.latitude  == r2.latitude
            assert r1.magnitude == r2.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_royal_per_body_identity(jd):
    """Property 2: per-body functions return correct name and match fixed_star_at."""
    from moira.fixed_stars import fixed_star_at
    from moira.royal_stars import (
        aldebaran_at, regulus_at, antares_at, fomalhaut_at,
        ALDEBARAN, REGULUS, ANTARES, FOMALHAUT,
    )
    for fn, const in [
        (aldebaran_at, ALDEBARAN),
        (regulus_at,   REGULUS),
        (antares_at,   ANTARES),
        (fomalhaut_at, FOMALHAUT),
    ]:
        result = fn(jd)
        direct = fixed_star_at(const, jd)
        assert result.name      == const
        assert result.longitude == direct.longitude
        assert result.latitude  == direct.latitude
        assert result.magnitude == direct.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_behenian_per_body_identity(jd):
    """Property 2: behenian per-body functions match fixed_star_at."""
    from moira.fixed_stars import fixed_star_at
    from moira.behenian_stars import algol_at, spica_at, vega_at, ALGOL, SPICA, VEGA
    for fn, const in [(algol_at, ALGOL), (spica_at, SPICA), (vega_at, VEGA)]:
        result = fn(jd)
        direct = fixed_star_at(const, jd)
        assert result.name      == const
        assert result.longitude == direct.longitude
        assert result.latitude  == direct.latitude
        assert result.magnitude == direct.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@settings(deadline=None)
@given(jd=_JD_STRATEGY)
def test_constellation_per_body_identity(jd):
    """Property 2: constellation per-body functions match fixed_star_at."""
    from moira.fixed_stars import fixed_star_at
    from moira.constellations.stars_taurus import aldebaran_at as tau_aldebaran_at, ALDEBARAN as TAU_ALDEBARAN
    from moira.constellations.stars_scorpius import antares_at as sco_antares_at, ANTARES as SCO_ANTARES
    from moira.constellations.stars_orion import rigel_at, RIGEL

    for fn, const in [
        (tau_aldebaran_at, TAU_ALDEBARAN),
        (sco_antares_at,   SCO_ANTARES),
        (rigel_at,         RIGEL),
    ]:
        result = fn(jd)
        direct = fixed_star_at(const, jd)
        assert result.name      == const
        assert result.longitude == direct.longitude
        assert result.latitude  == direct.latitude
        assert result.magnitude == direct.magnitude


@pytest.mark.requires_ephemeris
@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
def test_availability_subset_invariant():
    """Property 3: available_*() is always a subset of list_*()."""
    from moira.royal_stars import available_royal_stars, list_royal_stars
    from moira.behenian_stars import available_behenian_stars, list_behenian_stars
    from moira.fixed_star_groups import (
        available_fixed_stars, list_fixed_stars,
        available_pleiades, list_pleiades,
    )
    from moira.constellations.stars_taurus import available_taurus_stars, list_taurus_stars
    from moira.constellations.stars_scorpius import available_scorpius_stars, list_scorpius_stars

    assert set(available_royal_stars())    <= set(list_royal_stars())
    assert set(available_behenian_stars()) <= set(list_behenian_stars())
    assert set(available_fixed_stars())    <= set(list_fixed_stars())
    assert set(available_pleiades())       <= set(list_pleiades())
    assert set(available_taurus_stars())   <= set(list_taurus_stars())
    assert set(available_scorpius_stars()) <= set(list_scorpius_stars())

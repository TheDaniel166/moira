"""
Public-surface wiring tests for the three previously-missing API gaps.

Coverage:
  1. fixed_stars   — heliacal_rising, heliacal_setting importable via moira.*
  2. dignities     — is_in_hayz, is_in_sect, SectStateKind, SectTruth,
                     SectClassification importable via moira.*
  3. varga         — VargaPoint, calculate_varga, navamsa, saptamsa,
                     dashamansa, dwadashamsa, trimshamsa importable via moira.*

Each group tests:
  - Same-object identity between moira.X and moira.<module>.X
  - Presence in moira.__all__
  - Basic smoke: callable / instantiable, returns correct type
"""

import moira
import moira.stars as _fs
import moira.dignities as _dig
import moira.varga as _varga
import pytest


# ---------------------------------------------------------------------------
# 1. fixed_stars public surface
# ---------------------------------------------------------------------------

class TestFixedStarsPublicSurface:

    def test_heliacal_rising_in_all(self):
        assert "heliacal_rising" in moira.__all__

    def test_heliacal_setting_in_all(self):
        assert "heliacal_setting" in moira.__all__

    def test_heliacal_rising_same_object(self):
        assert moira.heliacal_rising is _fs.heliacal_rising

    def test_heliacal_setting_same_object(self):
        assert moira.heliacal_setting is _fs.heliacal_setting

    def test_heliacal_rising_callable(self):
        assert callable(moira.heliacal_rising)

    def test_heliacal_setting_callable(self):
        assert callable(moira.heliacal_setting)

    def test_star_position_in_all(self):
        assert "StarPosition" in moira.__all__

    def test_load_catalog_in_all(self):
        assert "load_catalog" in moira.__all__

    def test_fixed_stars_module_all_present(self):
        for name in _fs.__all__:
            assert hasattr(moira, name), f"moira.{name} missing"


# ---------------------------------------------------------------------------
# 2. dignities public surface
# ---------------------------------------------------------------------------

class TestDignitiesPublicSurface:

    def test_is_in_hayz_in_all(self):
        assert "is_in_hayz" in moira.__all__

    def test_is_in_sect_in_all(self):
        assert "is_in_sect" in moira.__all__

    def test_sect_state_kind_in_all(self):
        assert "SectStateKind" in moira.__all__

    def test_sect_truth_in_all(self):
        assert "SectTruth" in moira.__all__

    def test_sect_classification_in_all(self):
        assert "SectClassification" in moira.__all__

    def test_is_in_hayz_same_object(self):
        assert moira.is_in_hayz is _dig.is_in_hayz

    def test_is_in_sect_same_object(self):
        assert moira.is_in_sect is _dig.is_in_sect

    def test_sect_state_kind_same_object(self):
        assert moira.SectStateKind is _dig.SectStateKind

    def test_sect_truth_same_object(self):
        assert moira.SectTruth is _dig.SectTruth

    def test_sect_classification_same_object(self):
        assert moira.SectClassification is _dig.SectClassification

    def test_is_in_sect_diurnal_day(self):
        assert moira.is_in_sect("Sun", is_day_chart=True) is True

    def test_is_in_sect_diurnal_night(self):
        assert moira.is_in_sect("Sun", is_day_chart=False) is False

    def test_is_in_sect_nocturnal_night(self):
        assert moira.is_in_sect("Moon", is_day_chart=False) is True

    def test_is_in_hayz_sun_day_above_masculine(self):
        assert moira.is_in_hayz("Sun", "Leo", 10, is_day_chart=True) is True

    def test_is_in_hayz_sun_night(self):
        assert moira.is_in_hayz("Sun", "Leo", 10, is_day_chart=False) is False

    def test_is_in_hayz_unknown_planet(self):
        assert moira.is_in_hayz("Pluto", "Aries", 1, is_day_chart=True) is False

    def test_sect_state_kind_values(self):
        assert moira.SectStateKind.IN_HAYZ == "in_hayz"
        assert moira.SectStateKind.IN_SECT == "in_sect"
        assert moira.SectStateKind.OUT_OF_SECT == "out_of_sect"


# ---------------------------------------------------------------------------
# 3. varga public surface
# ---------------------------------------------------------------------------

class TestVargaPublicSurface:

    def test_varga_point_in_all(self):
        assert "VargaPoint" in moira.__all__

    def test_calculate_varga_in_all(self):
        assert "calculate_varga" in moira.__all__

    def test_navamsa_in_all(self):
        assert "navamsa" in moira.__all__

    def test_saptamsa_in_all(self):
        assert "saptamsa" in moira.__all__

    def test_dashamansa_in_all(self):
        assert "dashamansa" in moira.__all__

    def test_dwadashamsa_in_all(self):
        assert "dwadashamsa" in moira.__all__

    def test_trimshamsa_in_all(self):
        assert "trimshamsa" in moira.__all__

    def test_varga_point_same_object(self):
        assert moira.VargaPoint is _varga.VargaPoint

    def test_calculate_varga_same_object(self):
        assert moira.calculate_varga is _varga.calculate_varga

    def test_navamsa_same_object(self):
        assert moira.navamsa is _varga.navamsa

    def test_varga_module_all_present(self):
        for name in _varga.__all__:
            assert hasattr(moira, name), f"moira.{name} missing"

    def test_navamsa_returns_varga_point(self):
        result = moira.navamsa(95.0)
        assert isinstance(result, moira.VargaPoint)

    def test_navamsa_name(self):
        result = moira.navamsa(0.0)
        assert result.varga_name == "Navamsa"
        assert result.varga_number == 9

    def test_saptamsa_returns_varga_point(self):
        result = moira.saptamsa(60.0)
        assert isinstance(result, moira.VargaPoint)

    def test_dashamansa_returns_varga_point(self):
        result = moira.dashamansa(180.0)
        assert isinstance(result, moira.VargaPoint)

    def test_dwadashamsa_returns_varga_point(self):
        result = moira.dwadashamsa(270.0)
        assert isinstance(result, moira.VargaPoint)

    def test_trimshamsa_returns_varga_point(self):
        result = moira.trimshamsa(15.0)
        assert isinstance(result, moira.VargaPoint)

    def test_calculate_varga_arbitrary_division(self):
        result = moira.calculate_varga(45.0, 4, "D4")
        assert isinstance(result, moira.VargaPoint)
        assert result.varga_number == 4
        assert result.varga_name == "D4"

    def test_varga_longitude_in_range(self):
        for lon in [0.0, 45.0, 90.0, 180.0, 270.0, 359.9]:
            result = moira.navamsa(lon)
            assert 0.0 <= result.varga_longitude < 360.0

    def test_sign_degree_in_range(self):
        for lon in [0.0, 45.0, 90.0, 180.0, 270.0, 359.9]:
            result = moira.navamsa(lon)
            assert 0.0 <= result.sign_degree < 30.0

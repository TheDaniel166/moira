"""
tests/unit/test_timelords_public_api.py

Validates that the curated timelords public API is correctly exposed from the
owning module and forwarded through the classical and facade surfaces.

Scope: moira.timelords.__all__ contract and Decennials-era export freeze.
No computation is performed; all assertions are import-resolution checks.
"""

import moira
import moira.classical as _classical_module
import moira.facade as _facade_module
import moira.timelords as _timelords_module

_CURATED_PUBLIC_NAMES = [
    "FIRDARIA_DIURNAL",
    "FIRDARIA_NOCTURNAL",
    "FIRDARIA_NOCTURNAL_BONATTI",
    "CHALDEAN_ORDER",
    "MINOR_YEARS",
    "FirdarSequenceKind",
    "DecennialSequenceKind",
    "ZRAngularityClass",
    "FirdarYearPolicy",
    "DecennialPolicy",
    "ZRYearPolicy",
    "TimelordComputationPolicy",
    "DEFAULT_TIMELORD_POLICY",
    "FirdarPeriod",
    "DecennialPeriod",
    "ReleasingPeriod",
    "FirdarMajorGroup",
    "DecennialMajorGroup",
    "DecennialPeriodGroup",
    "ZRPeriodGroup",
    "FirdarConditionProfile",
    "DecennialConditionProfile",
    "ZRConditionProfile",
    "FirdarSequenceProfile",
    "DecennialSequenceProfile",
    "ZRSequenceProfile",
    "FirdarActivePair",
    "DecennialActivePair",
    "DecennialActivePath",
    "ZRLevelPair",
    "firdaria",
    "current_firdaria",
    "decennials",
    "current_decennials",
    "zodiacal_releasing",
    "current_releasing",
    "group_firdaria",
    "group_decennials",
    "group_releasing",
    "firdar_condition_profile",
    "decennial_condition_profile",
    "zr_condition_profile",
    "firdar_sequence_profile",
    "decennial_sequence_profile",
    "zr_sequence_profile",
    "firdar_active_pair",
    "decennial_active_pair",
    "decennial_active_path",
    "zr_level_pair",
    "validate_firdaria_output",
    "validate_decennials_output",
    "validate_releasing_output",
]

_INTERNAL_NAMES = [
    "_firdar_sequence_kind",
    "_decennial_sequence_kind",
    "_zr_angularity_class",
    "_validate_timelord_policy",
    "_DECENNIAL_MONTHS",
    "_TOTAL_MINOR_YEARS",
]

_DECAENNIAL_FORWARD_NAMES = [
    "DecennialSequenceKind",
    "DecennialPolicy",
    "DecennialPeriod",
    "DecennialMajorGroup",
    "DecennialPeriodGroup",
    "DecennialConditionProfile",
    "DecennialSequenceProfile",
    "DecennialActivePair",
    "DecennialActivePath",
    "decennials",
    "current_decennials",
    "group_decennials",
    "decennial_condition_profile",
    "decennial_sequence_profile",
    "decennial_active_pair",
    "decennial_active_path",
    "validate_decennials_output",
]


class TestTimelordsModuleLevelResolution:
    def test_all_curated_names_resolve_from_moira_timelords(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_timelords_module, name), f"moira.timelords.{name} not found"

    def test_timelords_all_exists(self):
        assert hasattr(_timelords_module, "__all__"), "moira.timelords.__all__ not defined"

    def test_timelords_all_contains_exactly_curated_names(self):
        assert set(_timelords_module.__all__) == set(_CURATED_PUBLIC_NAMES), (
            f"moira.timelords.__all__ mismatch.\n"
            f"  Extra:   {set(_timelords_module.__all__) - set(_CURATED_PUBLIC_NAMES)}\n"
            f"  Missing: {set(_CURATED_PUBLIC_NAMES) - set(_timelords_module.__all__)}"
        )

    def test_no_internal_names_in_timelords_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in _timelords_module.__all__, (
                f"{name!r} leaked into moira.timelords.__all__"
            )


class TestTimelordsCounts:
    def test_curated_count_is_52(self):
        assert len(_CURATED_PUBLIC_NAMES) == 52

    def test_timelords_all_count_is_52(self):
        assert len(_timelords_module.__all__) == 52


class TestTimelordsInternalsRemainInternal:
    def test_internal_names_are_accessible_on_module_but_not_in_all(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_timelords_module, name), (
                f"moira.timelords.{name} disappeared — internal name should still be accessible"
            )
            assert name not in _timelords_module.__all__, (
                f"{name!r} leaked into moira.timelords.__all__"
            )


class TestDecennialsForwardedSurfaces:
    def test_decennials_names_are_forwarded_through_classical(self):
        for name in _DECAENNIAL_FORWARD_NAMES:
            assert hasattr(_classical_module, name), f"moira.classical.{name} not found"
            assert name in _classical_module.__all__, f"{name!r} missing from moira.classical.__all__"

    def test_decennials_names_are_forwarded_through_facade(self):
        for name in _DECAENNIAL_FORWARD_NAMES:
            assert hasattr(_facade_module, name), f"moira.facade.{name} not found"
            assert name in _facade_module.__all__, f"{name!r} missing from moira.facade.__all__"

    def test_decennials_names_do_not_leak_into_root_package(self):
        for name in _DECAENNIAL_FORWARD_NAMES:
            assert not hasattr(moira, name), f"moira.{name} should remain absent from the thin root package"
            assert name not in moira.__all__, f"{name!r} should remain absent from moira.__all__"

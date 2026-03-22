"""
tests/unit/test_sothic_public_api.py

Validates that the curated Sothic backend public API is exposed at the moira
package root while helper machinery remains internal.

Scope: moira.__init__ Sothic exports only. No computation is performed.
"""

import moira
import moira.sothic as _sothic_module


_CURATED_PUBLIC_NAMES = [
    # Policy
    "SothicCalendarPolicy",
    "SothicHeliacalPolicy",
    "SothicEpochPolicy",
    "SothicPredictionPolicy",
    "SothicComputationPolicy",
    # Truth / classification
    "EgyptianCalendarTruth",
    "SothicComputationTruth",
    "EgyptianCalendarClassification",
    "SothicComputationClassification",
    # Relation / condition / aggregate vessels
    "SothicRelation",
    "SothicConditionState",
    "SothicConditionProfile",
    "SothicChartConditionProfile",
    "SothicConditionNetworkNode",
    "SothicConditionNetworkEdge",
    "SothicConditionNetworkProfile",
    # Result vessels / constants / entry points
    "EgyptianDate",
    "SothicEntry",
    "SothicEpoch",
    "EGYPTIAN_MONTHS",
    "EGYPTIAN_SEASONS",
    "EPAGOMENAL_BIRTHS",
    "HISTORICAL_SOTHIC_EPOCHS",
    "egyptian_civil_date",
    "days_from_1_thoth",
    "sothic_rising",
    "sothic_epochs",
    "sothic_drift_rate",
    "predicted_sothic_epoch_year",
    "sothic_chart_condition_profile",
    "sothic_condition_network_profile",
]

_INTERNAL_NAMES = [
    "_resolve_sothic_policy",
    "_validate_sothic_policy",
    "_classify_egyptian_calendar_truth",
    "_classify_sothic_computation_truth",
    "_build_egyptian_date_relation",
    "_build_sothic_entry_relation",
    "_build_sothic_epoch_relation",
    "_build_egyptian_date_condition_profile",
    "_build_sothic_entry_condition_profile",
    "_build_sothic_epoch_condition_profile",
    "_sothic_condition_strength",
    "_sothic_condition_sort_key",
    "_sothic_network_node_sort_key",
    "_sothic_network_edge_sort_key",
]


class TestPackageLevelResolution:
    def test_all_curated_names_resolve_from_moira(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(moira, name), f"moira.{name} not found"

    def test_all_curated_names_in_moira_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in moira.__all__, f"{name!r} missing from moira.__all__"

    def test_no_internal_names_in_moira_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in moira.__all__, f"{name!r} leaked into moira.__all__"

    def test_internal_names_not_in_package_namespace(self):
        for name in _INTERNAL_NAMES:
            assert not hasattr(moira, name), f"Internal {name!r} leaked into moira"


class TestModuleAgreement:
    def test_all_curated_names_resolve_from_moira_sothic(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_sothic_module, name), f"moira.sothic.{name} not found"

    def test_curated_package_exports_are_module_objects(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert getattr(moira, name) is getattr(_sothic_module, name), (
                f"moira.{name} and moira.sothic.{name} are different objects"
            )

    def test_internal_names_remain_accessible_on_module(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_sothic_module, name), (
                f"moira.sothic.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_31(self):
        assert len(_CURATED_PUBLIC_NAMES) == 31

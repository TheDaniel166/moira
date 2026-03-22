"""
tests/unit/test_synastry_public_api.py

Validates that the curated synastry backend public API is exposed at the moira
package root while helper machinery remains internal.

Scope: moira.__init__ synastry exports only. No computation is performed.
"""

import moira
import moira.synastry as _synastry_module


_CURATED_PUBLIC_NAMES = [
    # Truth / classification
    "SynastryAspectTruth",
    "SynastryAspectContact",
    "SynastryOverlayTruth",
    "CompositeComputationTruth",
    "DavisonComputationTruth",
    "SynastryAspectClassification",
    "SynastryOverlayClassification",
    "CompositeClassification",
    "DavisonClassification",
    # Relation / condition / aggregate vessels
    "SynastryRelation",
    "SynastryConditionState",
    "SynastryConditionProfile",
    "SynastryChartConditionProfile",
    "SynastryConditionNetworkNode",
    "SynastryConditionNetworkEdge",
    "SynastryConditionNetworkProfile",
    # Policy
    "SynastryAspectPolicy",
    "SynastryOverlayPolicy",
    "SynastryCompositePolicy",
    "SynastryDavisonPolicy",
    "SynastryComputationPolicy",
    # Result vessels
    "SynastryHouseOverlay",
    "MutualHouseOverlay",
    "CompositeChart",
    "DavisonInfo",
    "DavisonChart",
    # Core techniques / entry points
    "synastry_aspects",
    "synastry_contacts",
    "house_overlay",
    "mutual_house_overlays",
    "composite_chart",
    "composite_chart_reference_place",
    "davison_chart",
    "davison_chart_uncorrected",
    "davison_chart_reference_place",
    "davison_chart_spherical_midpoint",
    "davison_chart_corrected",
    # Layered entry points
    "synastry_contact_relations",
    "mutual_overlay_relations",
    "synastry_condition_profiles",
    "synastry_chart_condition_profile",
    "synastry_condition_network_profile",
]

_INTERNAL_NAMES = [
    "_classify_synastry_aspect_truth",
    "_classify_overlay_truth",
    "_classify_composite_truth",
    "_classify_davison_truth",
    "_relation_basis_for_composite_method",
    "_relation_basis_for_davison_method",
    "_build_contact_condition_profile",
    "_build_overlay_condition_profile",
    "_build_composite_condition_profile",
    "_build_davison_condition_profile",
    "_resolve_synastry_policy",
    "_validate_label_pair",
    "_validate_finite_coordinate",
    "_validate_house_system_code",
    "_validate_synastry_aspect_inputs",
    "_synastry_condition_sort_key",
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
    def test_all_curated_names_resolve_from_moira_synastry(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_synastry_module, name), f"moira.synastry.{name} not found"

    def test_curated_package_exports_are_module_objects(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert getattr(moira, name) is getattr(_synastry_module, name), (
                f"moira.{name} and moira.synastry.{name} are different objects"
            )

    def test_internal_names_remain_accessible_on_module(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_synastry_module, name), (
                f"moira.synastry.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_42(self):
        assert len(_CURATED_PUBLIC_NAMES) == 42

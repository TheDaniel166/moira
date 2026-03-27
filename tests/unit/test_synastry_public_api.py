"""
tests/unit/test_synastry_public_api.py

Validates that the curated synastry backend public API is exposed from the
owning module while helper machinery remains internal.

Scope: moira.synastry exports only. No computation is performed.
"""

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


class TestModuleAgreement:
    def test_all_curated_names_resolve_from_moira_synastry(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_synastry_module, name), f"moira.synastry.{name} not found"

    def test_all_curated_names_in_module_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in _synastry_module.__all__, f"{name!r} missing from moira.synastry.__all__"

    def test_no_internal_names_in_module_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in _synastry_module.__all__, f"{name!r} leaked into moira.synastry.__all__"

    def test_internal_names_remain_accessible_on_module(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_synastry_module, name), (
                f"moira.synastry.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_42(self):
        assert len(_CURATED_PUBLIC_NAMES) == 42

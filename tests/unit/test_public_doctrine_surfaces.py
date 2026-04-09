"""
Public doctrine surface audit.

Verifies that:
- every publicly exposed doctrine or policy vessel remains reachable from its
  declared public module
- doctrine surfaces stay listed in module __all__ whenever the module declares
  one
- public doctrine enums remain non-empty enums
- public policy vessels remain frozen, zero-argument constructible dataclasses
  with stable equality and hash behavior

Scope: public doctrine surfaces only. No computational truth or oracle parity
checks are performed here.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import EnumMeta
import importlib

import pytest


_PUBLIC_DOCTRINE_SURFACES = {
    "moira.julian": ["DeltaTPolicy"],
    "moira.houses": ["HousePolicy", "UnknownSystemPolicy", "PolarFallbackPolicy"],
    "moira.aspects": ["AspectPolicy"],
    "moira.dignities": [
        "EssentialDignityDoctrine",
        "EssentialDignityPolicy",
        "SolarConditionPolicy",
        "MutualReceptionPolicy",
        "SectHayzPolicy",
        "AccidentalDignityPolicy",
        "DignityComputationPolicy",
        "DispositorshipSubjectPolicy",
        "DispositorshipRulershipPolicy",
        "DispositorshipTerminationPolicy",
        "DispositorshipUnsupportedSubjectPolicy",
        "DispositorshipOrderingPolicy",
        "DispositorshipComputationPolicy",
    ],
    "moira.dasha_systems": ["AshtottariPolicy", "YoginiPolicy"],
    "moira.dasha": [
        "VimshottariYearPolicy",
        "VimshottariAyanamsaPolicy",
        "VimshottariComputationPolicy",
    ],
    "moira.ashtakavarga": ["AshtakavargaPolicy"],
    "moira.shadbala": ["ShadbalaPolicy"],
    "moira.heliacal": [
        "MoonlightPolicy",
        "VisibilityPolicy",
        "VisibilitySearchPolicy",
        "HeliacalPolicy",
    ],
    "moira.rise_set": ["RiseSetPolicy"],
    "moira.egyptian_bounds": ["EgyptianBoundsDoctrine", "EgyptianBoundsPolicy"],
    "moira.electional": ["ElectionalPolicy"],
    "moira.patterns": [
        "PatternSelectionPolicy",
        "StelliumPolicy",
        "PatternComputationPolicy",
    ],
    "moira.nine_parts": ["NinePartsPolicy"],
    "moira.panchanga": ["PanchangaPolicy"],
    "moira.lord_of_the_orb": ["LordOfOrbPolicy"],
    "moira.lord_of_the_turn": ["LordOfTurnPolicy"],
    "moira.lots": [
        "LotsDerivedReferencePolicy",
        "LotsExternalReferencePolicy",
        "LotsComputationPolicy",
    ],
    "moira.parans": ["ParanPolicy"],
    "moira.sothic": [
        "SothicCalendarPolicy",
        "SothicHeliacalPolicy",
        "SothicEpochPolicy",
        "SothicPredictionPolicy",
        "SothicComputationPolicy",
    ],
    "moira.progressions": ["ProgressionTimeKeyPolicy"],
    "moira.harmograms": [
        "HarmogramPolicy",
        "HarmogramIntensityPolicy",
        "PointSetHarmonicVectorPolicy",
    ],
    "moira.vedic_dignities": ["VedicDignityPolicy"],
    "moira.jaimini": ["JaiminiPolicy"],
}

_MODULES_WITHOUT_ALL = {"moira.julian"}
_PUBLIC_DOCTRINE_SURFACE_COUNT = 55
_PUBLIC_DOCTRINE_DATACLASS_COUNT = 50
_PUBLIC_DOCTRINE_ENUM_COUNT = 5


def _iter_surface_records() -> list[tuple[str, str]]:
    return [
        (module_name, name)
        for module_name, names in _PUBLIC_DOCTRINE_SURFACES.items()
        for name in names
    ]


def _surface_object(module_name: str, name: str) -> object:
    module = importlib.import_module(module_name)
    return getattr(module, name)


class TestPublicDoctrineSurfaceAgreement:
    def test_surface_count_is_stable(self) -> None:
        assert len(_iter_surface_records()) == _PUBLIC_DOCTRINE_SURFACE_COUNT

    def test_only_julian_lacks_module_all(self) -> None:
        actual = {
            module_name
            for module_name in _PUBLIC_DOCTRINE_SURFACES
            if not hasattr(importlib.import_module(module_name), "__all__")
        }
        assert actual == _MODULES_WITHOUT_ALL

    def test_each_surface_resolves_from_its_declared_public_module(self) -> None:
        for module_name, name in _iter_surface_records():
            module = importlib.import_module(module_name)
            assert hasattr(module, name), f"{module_name}.{name} not found"

    def test_each_surface_stays_in_module_all_when_defined(self) -> None:
        for module_name, name in _iter_surface_records():
            module = importlib.import_module(module_name)
            exported = getattr(module, "__all__", None)
            if exported is None:
                continue
            assert name in exported, f"{name!r} missing from {module_name}.__all__"


class TestPublicDoctrineKinds:
    def test_all_public_doctrine_surfaces_are_frozen_dataclasses_or_enums(self) -> None:
        counts = {"dataclass": 0, "enum": 0}
        for module_name, name in _iter_surface_records():
            obj = _surface_object(module_name, name)
            if isinstance(obj, EnumMeta):
                counts["enum"] += 1
                continue
            if is_dataclass(obj):
                counts["dataclass"] += 1
                assert obj.__dataclass_params__.frozen, f"{module_name}.{name} is not frozen"
                continue
            pytest.fail(f"{module_name}.{name} is neither an enum nor a dataclass")

        assert counts["dataclass"] == _PUBLIC_DOCTRINE_DATACLASS_COUNT
        assert counts["enum"] == _PUBLIC_DOCTRINE_ENUM_COUNT

    def test_public_doctrine_enums_have_non_empty_member_sets(self) -> None:
        for module_name, name in _iter_surface_records():
            obj = _surface_object(module_name, name)
            if not isinstance(obj, EnumMeta):
                continue

            members = list(obj)
            assert members, f"{module_name}.{name} has no members"
            assert all(isinstance(member, obj) for member in members), (
                f"{module_name}.{name} yielded non-member enum values"
            )
            assert len({member.value for member in members}) == len(members), (
                f"{module_name}.{name} has duplicate enum values"
            )


class TestPublicDoctrineDataclasses:
    def test_default_dataclass_policies_construct_hash_and_compare_cleanly(self) -> None:
        for module_name, name in _iter_surface_records():
            obj = _surface_object(module_name, name)
            if not is_dataclass(obj):
                continue

            left = obj()
            right = obj()

            assert left == right, f"{module_name}.{name} default equality drifted"
            assert hash(left) == hash(right), f"{module_name}.{name} default hash drifted"

    def test_default_dataclass_policies_reject_attribute_reassignment(self) -> None:
        for module_name, name in _iter_surface_records():
            obj = _surface_object(module_name, name)
            if not is_dataclass(obj):
                continue

            instance = obj()
            policy_fields = fields(instance)
            assert policy_fields, f"{module_name}.{name} unexpectedly has no fields"

            field_name = policy_fields[0].name
            original = getattr(instance, field_name)
            with pytest.raises((AttributeError, TypeError)):
                setattr(instance, field_name, original)
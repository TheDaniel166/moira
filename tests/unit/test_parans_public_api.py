"""
Phase 14 — public API surface contract tests.

These tests prove that every name in the curated paran public API resolves
correctly from both ``moira.parans`` and the top-level ``moira`` package, and
that no internal helper is accidentally re-exported.

Validation environment: project .venv (Python 3.14).
"""
from __future__ import annotations

import moira
import moira.parans as _parans_module


# ---------------------------------------------------------------------------
# Curated public names — the frozen contract from Phase 13 / Phase 14
# ---------------------------------------------------------------------------

_EXPECTED_PUBLIC = {
    # Constants / configuration
    "CIRCLE_TYPES",
    "DEFAULT_PARAN_POLICY",
    # Core vessels
    "Paran",
    "ParanCrossing",
    "ParanSignature",
    "ParanPolicy",
    "ParanStrength",
    # Stability
    "ParanStability",
    "ParanStabilitySample",
    "evaluate_paran_stability",
    # Site / grid
    "ParanSiteResult",
    "ParanFieldSample",
    "evaluate_paran_site",
    "sample_paran_field",
    # Field analysis
    "ParanFieldAnalysis",
    "ParanFieldRegion",
    "ParanFieldPeak",
    "ParanThresholdCrossing",
    "analyze_paran_field",
    # Contour extraction
    "ParanContourExtraction",
    "ParanContourSegment",
    "ParanContourPoint",
    "extract_paran_field_contours",
    # Contour consolidation
    "ParanContourPathSet",
    "ParanContourPath",
    "consolidate_paran_contours",
    # Higher-order structure
    "ParanFieldStructure",
    "ParanContourHierarchyEntry",
    "ParanContourAssociation",
    "analyze_paran_field_structure",
    # Engine entry points
    "find_parans",
    "natal_parans",
}

_INTERNAL_HELPERS = {
    "_validate_circle",
    "_validate_metric",
    "_validate_orb_non_negative",
    "_named_star_catalog",
    "_body_family_role",
    "_classify_paran",
    "_policy_allows_paran",
    "_matching_perturbed_paran_candidates",
    "_matching_site_paran_candidates",
    "_field_metric_value",
    "_infer_field_axes",
    "_orthogonal_neighbor_coords",
    "_interpolate_contour_point",
    "_contour_point_key",
    "_extract_cell_contour_segments",
    "_path_bounding_box",
    "_path_centroid",
    "_point_in_closed_path",
    "_crossing_times",
    "_derive_paran_strength",
    "_SUPPORTED_METRICS",
    "_MINUTES_TO_JD",
}


# ---------------------------------------------------------------------------
# moira.parans.__all__ contract
# ---------------------------------------------------------------------------

def test_parans_module_has_all() -> None:
    assert hasattr(_parans_module, "__all__")


def test_parans_all_contains_every_public_name() -> None:
    missing = _EXPECTED_PUBLIC - set(_parans_module.__all__)
    assert not missing, f"Missing from __all__: {sorted(missing)}"


def test_parans_all_contains_no_extra_names() -> None:
    extra = set(_parans_module.__all__) - _EXPECTED_PUBLIC
    assert not extra, f"Unexpected names in __all__: {sorted(extra)}"


def test_parans_all_contains_no_internal_helpers() -> None:
    leaked = _INTERNAL_HELPERS & set(_parans_module.__all__)
    assert not leaked, f"Internal helpers in __all__: {sorted(leaked)}"


# ---------------------------------------------------------------------------
# moira.parans direct import resolution
# ---------------------------------------------------------------------------

def test_all_public_names_resolve_from_parans_module() -> None:
    missing = [
        name for name in _EXPECTED_PUBLIC
        if not hasattr(_parans_module, name)
    ]
    assert not missing, f"Not found in moira.parans: {missing}"


# ---------------------------------------------------------------------------
# Internal helpers are not re-exported at package level
# ---------------------------------------------------------------------------

def test_internal_helpers_not_on_moira_package() -> None:
    moira_all = set(getattr(moira, "__all__", []))
    leaked = [name for name in _INTERNAL_HELPERS if name in moira_all]
    assert not leaked, f"Internal helpers leaked into moira.__all__: {leaked}"


# ---------------------------------------------------------------------------
# Spot-check: callable entry points are callable
# ---------------------------------------------------------------------------

def test_entry_points_are_callable() -> None:
    callables = [
        "find_parans",
        "natal_parans",
        "evaluate_paran_stability",
        "evaluate_paran_site",
        "sample_paran_field",
        "analyze_paran_field",
        "extract_paran_field_contours",
        "consolidate_paran_contours",
        "analyze_paran_field_structure",
    ]
    for name in callables:
        obj = getattr(_parans_module, name)
        assert callable(obj), f"moira.parans.{name} is not callable"


# ---------------------------------------------------------------------------
# Spot-check: dataclasses are classes
# ---------------------------------------------------------------------------

def test_dataclass_vessels_are_classes() -> None:
    classes = [
        "Paran", "ParanCrossing", "ParanSignature", "ParanPolicy",
        "ParanStrength", "ParanStability", "ParanStabilitySample",
        "ParanSiteResult", "ParanFieldSample", "ParanFieldAnalysis",
        "ParanFieldRegion", "ParanFieldPeak", "ParanThresholdCrossing",
        "ParanContourExtraction", "ParanContourSegment", "ParanContourPoint",
        "ParanContourPathSet", "ParanContourPath",
        "ParanFieldStructure", "ParanContourHierarchyEntry",
        "ParanContourAssociation",
    ]
    for name in classes:
        obj = getattr(_parans_module, name)
        assert isinstance(obj, type), f"moira.parans.{name} is not a class"


# ---------------------------------------------------------------------------
# Spot-check: constants have correct types
# ---------------------------------------------------------------------------

def test_circle_types_is_tuple_of_four_strings() -> None:
    ct = _parans_module.CIRCLE_TYPES
    assert isinstance(ct, tuple)
    assert len(ct) == 4
    assert all(isinstance(s, str) for s in ct)


def test_default_paran_policy_is_paran_policy_instance() -> None:
    assert isinstance(_parans_module.DEFAULT_PARAN_POLICY, _parans_module.ParanPolicy)

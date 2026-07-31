"""Source-control governance for the Phase 3 physical event admission."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import ModuleType

import pytest

import moira.heliacal as heliacal


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = (
    _REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase3_stellar_target_profile_pack_spec.json"
)
_CERTIFICATE_PATH = (
    _REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase3_event_crossing_certificate.json"
)
_BUILDER_PATH = (
    _REPO_ROOT / "scripts" / "build_visibility_phase3_data_pack.py"
)
_PACK_VALIDATOR_PATH = (
    _REPO_ROOT / "scripts" / "validate_visibility_phase3_data_pack.py"
)
_CERTIFICATE_VALIDATOR_PATH = (
    _REPO_ROOT
    / "scripts"
    / "validate_visibility_phase3_event_certificate.py"
)
_EVENT_GOLDEN_VALIDATOR_PATH = (
    _REPO_ROOT
    / "scripts"
    / "validate_visibility_phase3_event_goldens.py"
)
_EVENT_GOLDEN_PATH = (
    _REPO_ROOT
    / "tests"
    / "golden"
    / "physical_visibility_phase3_events.json"
)
_COMPATIBILITY_PATHS = (
    _REPO_ROOT
    / "moira"
    / "data"
    / "physical_heliacal_visibility_data_pack_compatibility_v1_2.json",
    _REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_heliacal_visibility_data_pack_compatibility_v1_2.json",
)
_CERTIFICATE_SHA256 = (
    "eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e"
)
_COMPATIBILITY_SHA256 = (
    "aaa44f99cfdb85277a44778167abd5c0c721e4a580dfb6e000ef74957cdb9e37"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = {
        alias.name.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    result.update(
        node.module.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
    )
    return result


def test_phase3_compatibility_contract_is_identical_at_both_owners() -> None:
    assert tuple(_sha256(path) for path in _COMPATIBILITY_PATHS) == (
        _COMPATIBILITY_SHA256,
        _COMPATIBILITY_SHA256,
    )
    assert (
        _COMPATIBILITY_PATHS[0].read_bytes()
        == _COMPATIBILITY_PATHS[1].read_bytes()
    )


def test_phase3_source_spec_pins_the_exact_sirius_inputs() -> None:
    spec = json.loads(_SPEC_PATH.read_text(encoding="utf-8"))
    sources = spec["source_inputs"]

    assert sources["calspec_sirius"]["sha256"] == (
        "1349da7b8b59ad035aefea8d7948f552"
        "b41b3897d07e5ad82ca162a53af97271"
    )
    assert sources["bsc5_sirius_photometry"]["sha256"] == (
        "09556d03431f70c65b75a4a555742812"
        "dd542d2e0a4ee40df4c11a876b5fcc3d"
    )
    assert sources["bsc5_sirius_photometry"]["readme_sha256"] == (
        "44fd9c73e2eecad0beb47bdfa3f01c60"
        "fd43f93d6964198e31fcd48732de5b33"
    )
    assert spec["target"]["catalog_identity"] == {
        "traditional_name": "Sirius",
        "nomenclature": "alf CMa",
        "hipparcos_id": 32349,
        "hr_id": 2491,
        "hd_id": 48915,
    }
    assert not sources["bsc5_sirius_photometry"]["color_index_used"]
    assert not spec["runtime_boundary"][
        "legacy_native_arcus_dispatch_allowed"
    ]


def test_phase3_offline_tools_import_no_runtime_builder_or_network() -> None:
    builder_imports = _imported_roots(_BUILDER_PATH)
    pack_validator_imports = _imported_roots(_PACK_VALIDATOR_PATH)
    certificate_validator_imports = _imported_roots(
        _CERTIFICATE_VALIDATOR_PATH
    )
    event_golden_validator_imports = _imported_roots(
        _EVENT_GOLDEN_VALIDATOR_PATH
    )
    network_clients = {
        "http",
        "requests",
        "socket",
        "urllib",
    }

    assert "moira" not in pack_validator_imports
    assert "moira" not in certificate_validator_imports
    assert "moira" not in event_golden_validator_imports
    assert "build_visibility_phase3_data_pack" not in (
        pack_validator_imports
        | certificate_validator_imports
        | event_golden_validator_imports
    )
    assert not (
        network_clients
        & (
            builder_imports
            | pack_validator_imports
            | certificate_validator_imports
            | event_golden_validator_imports
        )
    )


def test_phase3_event_golden_covers_one_planet_and_one_fixed_star() -> None:
    golden = json.loads(_EVENT_GOLDEN_PATH.read_text(encoding="utf-8"))

    assert _sha256(_EVENT_GOLDEN_PATH) == (
        "8111d662df77b1a8b3f53258fef02a1f"
        "cf5f3c21a980e3a48df9a7c5d5838518"
    )
    assert golden["exact_data_pack"]["manifest_sha256"] == (
        "cf93433a9f66a5ea92832271ce3c4b02"
        "3fcc8693164803539a9f1be85b17468c"
    )
    assert tuple(case["target"] for case in golden["cases"]) == (
        "Jupiter",
        "Sirius",
    )
    for case in golden["cases"]:
        assert (
            case["engine_result"]["crossing_certificate_source_sha256"]
            == _CERTIFICATE_SHA256
        )
        assert (
            case["engine_result"]["crossing_completeness_state"]
            == "certified_lipschitz_zero_enclosure"
        )
        assert (
            case["engine_result"][
                "unresolved_certificate_interval_count"
            ]
            == 0
        )
        assert case["independent_oracle"]["guard_day_status"] == (
            "does_not_qualify"
        )


def test_engine_is_bound_to_the_exact_independently_validated_certificate() -> None:
    assert _sha256(_CERTIFICATE_PATH) == _CERTIFICATE_SHA256
    assert (
        heliacal._PHYSICAL_EVENT_CROSSING_CERTIFICATE_SHA256
        == _CERTIFICATE_SHA256
    )
    assert (
        heliacal._PHYSICAL_EVENT_MARGIN_CERTIFICATE
        .maximum_absolute_rate_per_day
        == 16384.0
    )
    certificate = json.loads(
        _CERTIFICATE_PATH.read_text(encoding="utf-8")
    )
    assert certificate["visibility_margin_rate_derivation_magnitude_per_day"][
        "derived_total_before_binary_ceiling"
    ] < 16384.0


def test_certificate_validator_uses_the_runtime_interpolant_derivative() -> None:
    validator = _load_module(
        _CERTIFICATE_VALIDATOR_PATH,
        "phase3_certificate_validator_for_test",
    )
    altitudes = (0.25, 0.375)
    values = (10.0, 8.0)

    derived = validator._direct_extinction_derivative_ceiling(
        altitudes=altitudes,
        values=values,
        spectral_bin_count=1,
    )
    coordinate_width = math.log10(0.625) - math.log10(0.5)
    expected = (
        2.0
        / coordinate_width
        / (math.log(10.0) * 0.5)
    )

    assert derived == pytest.approx(expected, rel=1.0e-15)
    assert derived > 2.0 / (0.375 - 0.25)

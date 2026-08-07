"""Phase 7 evidence, inventory, and external-pack release gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import moira.heliacal as heliacal
from scripts import generate_physical_visibility_inventory as inventory
from scripts import package_physical_visibility_data_pack as packager
from scripts import validate_physical_visibility_phase7_release as release_validator


REPO_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_PATH = (
    REPO_ROOT
    / "moira"
    / "data"
    / "physical_heliacal_visibility_release_identity.json"
)
NOTICE_PATH = (
    REPO_ROOT
    / "moira"
    / "data"
    / "physical_heliacal_visibility_NOTICE.txt"
)
GOLDEN_PATH = (
    REPO_ROOT
    / "tests"
    / "golden"
    / "physical_visibility_phase3_events.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _minimal_pack(
    directory: Path,
    *,
    schema: str = (
        "moira.physical-heliacal-visibility-data-pack-manifest/v1"
    ),
    pack_id: str = "moira-physical-heliacal-visibility-test",
) -> None:
    payload = directory / "payload.bin"
    payload.write_bytes(b"phase7-pack-payload\n")
    _write_json(
        directory / "manifest.json",
        {
            "schema": schema,
            "pack_id": pack_id,
            "version": "1.0.0",
            "license": "CC-BY-SA-4.0",
            "source_artifact": {"manifest": {"sha256": "a" * 64}},
            "payload_files": [
                {
                    "path": payload.name,
                    "bytes": payload.stat().st_size,
                    "sha256": _sha256(payload),
                }
            ],
        },
    )


def test_generated_phase7_inventories_match_runtime_truth() -> None:
    rendered = inventory.render_documents()
    assert rendered
    for path, expected in rendered.items():
        assert path.read_text(encoding="utf-8") == expected

    runtime = inventory.collect_inventory()
    assert len(runtime.public_surfaces) == 36
    assert len(runtime.operations) == 2
    assert len(runtime.legacy_operations) == 3
    assert len(runtime.native_kernels) == 2
    assert all(all(row[1:]) for row in runtime.public_surfaces)


def test_every_phase7_evidence_class_binds_existing_current_bytes() -> None:
    runtime = inventory.collect_inventory()
    identifiers = {row.identifier for row in runtime.evidence}
    assert {
        "primary_source_equation_validation",
        "independent_libradtran_holdouts",
        "modern_era_observational_comparison",
        "historical_event_corroboration",
        "property_and_invariant_testing",
        "legacy_regression_fixtures",
        "public_contract_and_openapi_parity",
        "external_ephemeris_event_goldens",
        "separated_numerical_tolerances",
        "native_python_differential",
        "release_artifact_and_offline_install",
        "experimental_site_specific_moonlight_quarantine",
    } == identifiers
    for row in runtime.evidence:
        assert len(row.fingerprint) == 64
        assert all((REPO_ROOT / path).is_file() for path in row.paths)


def test_packaged_release_identity_binds_event_golden_and_contracts() -> None:
    identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    pack = identity["external_data_pack"]

    assert identity["schema"] == (
        "moira.physical-heliacal-visibility-release-identity/v1"
    )
    assert identity["composite_model_id"] == (
        "clear_sky_naked_eye_point_source_v1"
    )
    assert pack["manifest_sha256"] == golden["exact_data_pack"][
        "manifest_sha256"
    ]
    assert pack["manifest_sha256"] == (
        heliacal._PHYSICAL_EVENT_PACK_MANIFEST_SHA256
    )
    assert pack["version"] == golden["exact_data_pack"]["version"] == "1.2.0"
    assert pack["license"] == "CC-BY-SA-4.0"
    assert "jones_moonlight_component_pack" not in identity
    assert "paranal_scenario_data_pack" not in identity

    for contract in identity["packaged_compatibility_contracts"]:
        path = REPO_ROOT / contract["path"]
        assert _sha256(path) == contract["sha256"]

    assert identity["release_boundary"] == {
        "legacy_visibility_default_changed": False,
        "physical_policy_opt_in": True,
        "experimental_site_specific_moonlight_in_release": False,
        "quarantine_receipt": (
            "wiki/05_research/heliacal_visibility/"
            "PHYSICAL_HELIACAL_VISIBILITY_JONES_PARANAL_QUARANTINE_2026-08-07.md"
        ),
    }


def test_packaged_notice_preserves_resource_and_license_boundary() -> None:
    notice = NOTICE_PATH.read_text(encoding="utf-8")
    normalized = " ".join(notice.split())
    assert "does not contain the external" in normalized
    assert "CC BY-SA 4.0" in normalized
    assert "never downloads" in normalized
    assert "Jones/Paranal" in normalized
    assert "not composed" in normalized


def test_release_resource_resolver_contains_only_the_core_pack(
    tmp_path: Path,
) -> None:
    identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    baseline = tmp_path / "baseline"

    resources = release_validator._external_resources(
        identity,
        baseline_data_pack=baseline,
    )

    assert tuple(resource.label for resource in resources) == (
        "baseline_visibility",
    )
    assert tuple(resource.loader_kind for resource in resources) == (
        "visibility",
    )


def test_release_receipt_never_certifies_itself() -> None:
    assert release_validator._is_generated_release_receipt(
        "tests/artifacts/release/"
        "physical_visibility_phase7_release_validation_2026-08-07.json"
    )
    assert not release_validator._is_generated_release_receipt(
        "tests/fixtures/physical_visibility_phase7_evidence_registry.json"
    )


def test_external_pack_release_archive_is_byte_reproducible(
    tmp_path: Path,
) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    _minimal_pack(pack)
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"

    first_receipt = packager.build_release_archive(pack, first)
    second_receipt = packager.build_release_archive(pack, second)

    assert first.read_bytes() == second.read_bytes()
    assert first_receipt["archive"]["sha256"] == second_receipt["archive"][
        "sha256"
    ]
    assert first_receipt["archive"]["file_count"] == 2
    assert first_receipt["runtime_boundary"] == {
        "embedded_in_python_distribution": False,
        "automatic_download_allowed": False,
        "caller_or_server_supplied_directory_required": True,
    }


def test_external_pack_release_rejects_an_experimental_manifest_schema(
    tmp_path: Path,
) -> None:
    pack = tmp_path / "experimental-pack"
    pack.mkdir()
    _minimal_pack(
        pack,
        schema=(
            "moira.jones-paranal-moonlight-component-pack-manifest/v1"
        ),
        pack_id="moira-jones-paranal-moonlight-component",
    )

    with pytest.raises(
        packager.PhysicalVisibilityPackReleaseError,
        match="manifest schema is not admitted",
    ):
        packager.build_release_archive(
            pack,
            tmp_path / "experimental.tar.gz",
        )


def test_external_pack_release_rejects_an_unmanifested_file(
    tmp_path: Path,
) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    _minimal_pack(pack)
    (pack / "unexpected.bin").write_bytes(b"not declared")

    with pytest.raises(
        packager.PhysicalVisibilityPackReleaseError,
        match="inventory differs",
    ):
        packager.build_release_archive(pack, tmp_path / "invalid.tar.gz")

"""Strict receipt and coverage-context evaluation for assurance cells."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Mapping

from _pytest_plugins.artifacts import _run_context
from _pytest_plugins.evidence import _validate_receipt_payload
from _pytest_plugins.evidence_schema import (
    EvidenceContract,
    contract_payload,
    contract_sha256,
)


_MAX_JSON_BYTES = 16 * 1024 * 1024
_ALLOWED_CONTEXT_PHASES = frozenset({"setup", "run", "teardown"})


class AssuranceReceiptError(ValueError):
    """Raised when runtime evidence cannot lawfully fill an assurance cell."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> object:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise AssuranceReceiptError(f"required receipt file is missing: {path}") from exc
    if size > _MAX_JSON_BYTES:
        raise AssuranceReceiptError(f"receipt JSON exceeds the size limit: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceReceiptError(f"receipt JSON is invalid: {path}") from exc


def _require_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssuranceReceiptError(f"{label} must be a JSON object")
    return value


def _safe_relative_path(value: object, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise AssuranceReceiptError(f"{label} must be an exact POSIX path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise AssuranceReceiptError(f"{label} escapes the repository")
    return path


def load_assurance_requirements(path: Path) -> dict[str, object]:
    """Load and structurally validate the independent required-cell policy."""

    payload = _require_dict(_read_json(path), "assurance requirements")
    if set(payload) != {"schema_version", "policy", "cells"}:
        raise AssuranceReceiptError("assurance requirement fields are not exact")
    if payload["schema_version"] != 1:
        raise AssuranceReceiptError("assurance requirement schema is unsupported")
    policy = _require_dict(payload["policy"], "assurance policy")
    required_policy = {
        "admission_scope",
        "coverage_branch",
        "coverage_config",
        "coverage_context",
        "coverage_core",
        "coverage_is_scientific_gate",
        "coverage_phase_default",
        "coverage_runtime",
        "coverage_source",
        "global_percentage_gate",
        "required_cell_rule",
        "run_requirements",
        "runtime_versions",
        "security_boundary",
    }
    if set(policy) != required_policy:
        raise AssuranceReceiptError("assurance policy fields are not exact")
    if policy["coverage_context"] != "pytest-cov --cov-context=test":
        raise AssuranceReceiptError("coverage context policy is not admitted")
    if policy["coverage_core"] != "ctrace":
        raise AssuranceReceiptError("coverage core policy must require ctrace")
    if policy["coverage_branch"] is not None:
        raise AssuranceReceiptError("coverage branch policy is not admitted")
    if policy["coverage_config"] != "pyproject.toml":
        raise AssuranceReceiptError("coverage config policy is not admitted")
    if policy["coverage_source"] != ["moira"]:
        raise AssuranceReceiptError("coverage source policy is not admitted")
    coverage_runtime = _require_dict(
        policy["coverage_runtime"],
        "coverage runtime policy",
    )
    if set(coverage_runtime) != {
        "actual_core",
        "config_files",
        "effective_config",
    }:
        raise AssuranceReceiptError("coverage runtime policy fields are not exact")
    if coverage_runtime["actual_core"] != "CTracer":
        raise AssuranceReceiptError("coverage runtime must require CTracer")
    if coverage_runtime["config_files"] != ["pyproject.toml"]:
        raise AssuranceReceiptError("coverage config provenance is not admitted")
    effective_coverage = _require_dict(
        coverage_runtime["effective_config"],
        "effective coverage policy",
    )
    if effective_coverage != {
        "branch": False,
        "concurrency": [],
        "core": "ctrace",
        "dynamic_context": None,
        "parallel": True,
        "plugins": [],
        "relative_files": False,
        "source": ["moira"],
        "static_context": None,
        "timid": False,
    }:
        raise AssuranceReceiptError(
            "effective coverage runtime policy is not admitted"
        )
    if policy["admission_scope"] != "phase9_and_phase10_reviewed_claims":
        raise AssuranceReceiptError("assurance admission scope is not explicit")
    if policy["coverage_is_scientific_gate"] is not False:
        raise AssuranceReceiptError("coverage must not claim scientific proof")
    if policy["global_percentage_gate"] is not None:
        raise AssuranceReceiptError("global coverage percentage is not an admitted gate")
    run_requirements = _require_dict(
        policy["run_requirements"],
        "assurance run requirements",
    )
    if set(run_requirements) != {
        "external_network_enabled",
        "git_identity",
        "native_backend_under_repository",
        "no_download",
        "project_venv",
        "strict_known_issues",
        "test_mode",
    } or any(type(value) is not bool for value in run_requirements.values()):
        raise AssuranceReceiptError("assurance run requirements are not exact")
    runtime_versions = _require_dict(
        policy["runtime_versions"],
        "assurance runtime versions",
    )
    if set(runtime_versions) != {"python", "toolchain_versions"}:
        raise AssuranceReceiptError("assurance runtime version fields are not exact")
    python_versions = _require_dict(
        runtime_versions["python"],
        "assurance Python versions",
    )
    if set(python_versions) != {"cache_tag", "implementation", "version"}:
        raise AssuranceReceiptError("assurance Python version fields are not exact")
    toolchain_versions = _require_dict(
        runtime_versions["toolchain_versions"],
        "assurance toolchain versions",
    )
    if set(toolchain_versions) != {"coverage", "pytest", "pytest_cov", "xdist"}:
        raise AssuranceReceiptError("assurance toolchain fields are not exact")
    if not all(
        isinstance(value, str) and value
        for value in (*python_versions.values(), *toolchain_versions.values())
    ):
        raise AssuranceReceiptError("assurance runtime versions are invalid")
    cells = payload["cells"]
    if not isinstance(cells, list) or not cells:
        raise AssuranceReceiptError("assurance cells must be a non-empty list")
    cell_ids: set[str] = set()
    claim_ids: set[str] = set()
    for index, cell in enumerate(cells):
        cell = _require_dict(cell, f"cells[{index}]")
        if set(cell) != {
            "cell_id",
            "expected_contract_sha256",
            "product_surface",
            "evidence_class",
            "required_claim_id",
            "expected_bindings",
            "targets",
        }:
            raise AssuranceReceiptError(f"cells[{index}] fields are not exact")
        for field in (
            "cell_id",
            "product_surface",
            "evidence_class",
            "required_claim_id",
        ):
            if not isinstance(cell[field], str) or not cell[field]:
                raise AssuranceReceiptError(f"cells[{index}].{field} is invalid")
        expected_contract_sha256 = cell["expected_contract_sha256"]
        if (
            not isinstance(expected_contract_sha256, str)
            or len(expected_contract_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in expected_contract_sha256
            )
        ):
            raise AssuranceReceiptError(
                f"cells[{index}].expected_contract_sha256 is invalid"
            )
        if cell["cell_id"] in cell_ids:
            raise AssuranceReceiptError("assurance cell IDs must be unique")
        if cell["required_claim_id"] in claim_ids:
            raise AssuranceReceiptError(
                "one claim cannot silently fill multiple required cells"
            )
        cell_ids.add(str(cell["cell_id"]))
        claim_ids.add(str(cell["required_claim_id"]))
        expected_bindings = cell["expected_bindings"]
        if not isinstance(expected_bindings, list) or not expected_bindings:
            raise AssuranceReceiptError(
                f"cells[{index}].expected_bindings must be non-empty"
            )
        bases: set[str] = set()
        exact_nodeids: set[str] = set()
        for binding_index, binding in enumerate(expected_bindings):
            binding = _require_dict(
                binding,
                f"cells[{index}].expected_bindings[{binding_index}]",
            )
            if set(binding) != {"base_nodeid", "nodeids"}:
                raise AssuranceReceiptError("expected binding fields are not exact")
            base = binding["base_nodeid"]
            nodeids = binding["nodeids"]
            if (
                not isinstance(base, str)
                or "::" not in base
                or "[" in base
                or base in bases
                or not isinstance(nodeids, list)
                or not nodeids
                or not all(isinstance(nodeid, str) for nodeid in nodeids)
                or nodeids != sorted(set(nodeids))
                or any(
                    "\\" in nodeid
                    or not _base_matches(nodeid, base)
                    for nodeid in nodeids
                )
                or bool(exact_nodeids.intersection(nodeids))
            ):
                raise AssuranceReceiptError("expected binding is invalid")
            bases.add(base)
            exact_nodeids.update(nodeids)
        targets = cell["targets"]
        if not isinstance(targets, list) or not targets:
            raise AssuranceReceiptError(f"cells[{index}].targets must be non-empty")
        target_ids: set[tuple[str, str, tuple[str, ...]]] = set()
        for target_index, target in enumerate(targets):
            target = _require_dict(
                target,
                f"cells[{index}].targets[{target_index}]",
            )
            if set(target) != {"path", "qualname", "phases", "protected"}:
                raise AssuranceReceiptError("coverage target fields are not exact")
            path_value = _safe_relative_path(target["path"], "coverage target path")
            if path_value.suffix != ".py":
                raise AssuranceReceiptError("coverage target must be a Python file")
            qualname = target["qualname"]
            phases = target["phases"]
            if (
                not isinstance(qualname, str)
                or not qualname
                or not isinstance(phases, list)
                or not phases
                or not set(phases) <= _ALLOWED_CONTEXT_PHASES
                or len(set(phases)) != len(phases)
                or type(target["protected"]) is not bool
            ):
                raise AssuranceReceiptError("coverage target semantics are invalid")
            identity = (str(path_value), qualname, tuple(phases))
            if identity in target_ids:
                raise AssuranceReceiptError("coverage target is duplicated")
            target_ids.add(identity)
    return payload


def validate_requirements_against_contracts(
    requirements: Mapping[str, object],
    contracts: Mapping[str, EvidenceContract],
) -> None:
    """Ensure required cells cannot disappear when a contract is deleted."""

    cells = requirements["cells"]
    assert isinstance(cells, list)
    required_claims = {str(cell["required_claim_id"]) for cell in cells}
    extra_claims = set(contracts) - required_claims
    missing_claims = required_claims - set(contracts)
    if missing_claims:
        raise AssuranceReceiptError(
            "required assurance claims are missing: "
            + ", ".join(sorted(missing_claims))
        )
    if extra_claims:
        raise AssuranceReceiptError(
            "reviewed contracts lack independent assurance requirements: "
            + ", ".join(sorted(extra_claims))
        )
    for cell in cells:
        assert isinstance(cell, dict)
        claim_id = str(cell["required_claim_id"])
        contract = contracts[claim_id]
        if cell["product_surface"] != contract.product_surface:
            raise AssuranceReceiptError(
                f"{cell['cell_id']}: product surface contradicts its contract"
            )
        if cell["evidence_class"] != contract.evidence_class.value:
            raise AssuranceReceiptError(
                f"{cell['cell_id']}: evidence class contradicts its contract"
            )
        if cell["expected_contract_sha256"] != contract_sha256(contract):
            raise AssuranceReceiptError(
                f"{cell['cell_id']}: reviewed contract digest drifted"
            )
        expected_bases = {
            str(binding["base_nodeid"])
            for binding in cell["expected_bindings"]
        }
        if expected_bases != set(contract.nodeids):
            raise AssuranceReceiptError(
                f"{cell['cell_id']}: expected bindings do not cover the exact contract nodeids"
            )
        if cell["targets"] != contract_payload(contract)["coverage_targets"]:
            raise AssuranceReceiptError(
                f"{cell['cell_id']}: coverage targets contradict the contract"
            )


def load_complete_receipt(receipt_dir: Path) -> dict[str, object]:
    """Verify a complete controller receipt and return its bound sidecars."""

    receipt_dir = receipt_dir.resolve()
    complete = _require_dict(
        _read_json(receipt_dir / "COMPLETE"),
        "COMPLETE marker",
    )
    if complete.get("status") != "complete":
        raise AssuranceReceiptError("receipt is not complete")
    run_path = receipt_dir / "run.json"
    run_identity = _require_dict(complete.get("run_json"), "COMPLETE run_json")
    if run_identity.get("bytes") != run_path.stat().st_size:
        raise AssuranceReceiptError("run.json byte count contradicts COMPLETE")
    if run_identity.get("sha256") != _sha256(run_path):
        raise AssuranceReceiptError("run.json hash contradicts COMPLETE")
    run = _require_dict(_read_json(run_path), "run.json")
    if run.get("run_id") != complete.get("run_id"):
        raise AssuranceReceiptError("run identity contradicts COMPLETE")
    exitstatus = _require_dict(
        _require_dict(run.get("pytest"), "run pytest").get("exitstatus"),
        "run exitstatus",
    )
    if exitstatus.get("code") != 0 or exitstatus.get("name") != "OK":
        raise AssuranceReceiptError("assurance receipt did not finish green")
    artifacts = _require_dict(run.get("artifacts"), "run artifacts")
    sidecars: dict[str, object] = {}
    for name, identity in artifacts.items():
        if not isinstance(name, str):
            raise AssuranceReceiptError("artifact filename is invalid")
        identity = _require_dict(identity, f"artifact {name}")
        path = receipt_dir / name
        if identity.get("bytes") != path.stat().st_size:
            raise AssuranceReceiptError(f"artifact byte count mismatch: {name}")
        if identity.get("sha256") != _sha256(path):
            raise AssuranceReceiptError(f"artifact SHA-256 mismatch: {name}")
        if name.endswith(".json"):
            sidecars[name] = _read_json(path)
    required = {
        "collection.json",
        "resources.json",
        "reports.jsonl",
        "failures.json",
        "durations.json",
        "rerun-nodeids.json",
    }
    if set(artifacts) != required:
        raise AssuranceReceiptError("artifact manifest file set is not exact")
    reports: list[dict[str, object]] = []
    reports_path = receipt_dir / "reports.jsonl"
    if reports_path.stat().st_size > _MAX_JSON_BYTES:
        raise AssuranceReceiptError("reports.jsonl exceeds the size limit")
    try:
        for line_number, line in enumerate(
            reports_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            report = json.loads(line)
            reports.append(_require_dict(report, f"report line {line_number}"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceReceiptError("reports.jsonl is invalid") from exc
    collection = _require_dict(sidecars["collection.json"], "collection.json")
    if collection.get("classification_errors") != []:
        raise AssuranceReceiptError("classification receipt contains errors")
    if collection.get("evidence_errors") != []:
        raise AssuranceReceiptError("evidence receipt contains reconciliation errors")
    if collection.get("collection_error_report_sequences") != []:
        raise AssuranceReceiptError("collection receipt contains errors")
    failures = _require_dict(sidecars["failures.json"], "failures.json")
    for field in (
        "failure_report_sequences",
        "failed_cases",
        "collection_failure_report_sequences",
        "worker_crash_report_sequences",
        "budget_violations",
        "flakes",
    ):
        if failures.get(field) != []:
            raise AssuranceReceiptError(f"failure receipt is nonempty: {field}")
    return {
        "receipt_dir": receipt_dir,
        "run": run,
        "collection": collection,
        "durations": _require_dict(sidecars["durations.json"], "durations.json"),
        "reports": reports,
    }


def _base_matches(nodeid: str, base_nodeid: str) -> bool:
    return nodeid == base_nodeid or nodeid.startswith(base_nodeid + "[")


def _validate_native_build_provenance(
    *,
    root: Path,
    native: Mapping[str, object],
) -> None:
    """Bind the loaded extension to every current native/build input byte."""

    if set(native) != {
        "available",
        "backend_loader",
        "backend_loader_path",
        "backend_module",
        "backend_path",
        "backend_sha256",
        "backend_size",
        "backend_under_repository",
        "build_provenance",
        "moira_version",
        "package_path",
        "package_under_repository",
    }:
        raise AssuranceReceiptError("run native identity fields are not exact")
    if native.get("available") is not True:
        raise AssuranceReceiptError("run native backend is unavailable")
    if native.get("backend_module") != "moira._moira_native":
        raise AssuranceReceiptError("run native module identity is not admitted")
    backend_loader = native.get("backend_loader")
    if not isinstance(backend_loader, str) or not backend_loader.endswith(
        ".ExtensionFileLoader"
    ):
        raise AssuranceReceiptError("run native backend loader is not admitted")
    if (
        not isinstance(native.get("backend_loader_path"), str)
        or native.get("backend_loader_path") != native.get("backend_path")
    ):
        raise AssuranceReceiptError(
            "run native backend path is not owned by its extension loader"
        )
    if native.get("package_under_repository") is not True:
        raise AssuranceReceiptError("run Moira package is outside the checkout")
    if (
        not isinstance(native.get("backend_size"), int)
        or int(native["backend_size"]) <= 0
        or not isinstance(native.get("backend_sha256"), str)
        or len(str(native["backend_sha256"])) != 64
        or any(
            character not in "0123456789abcdef"
            for character in str(native["backend_sha256"])
        )
    ):
        raise AssuranceReceiptError("run native backend artifact is malformed")

    provenance = _require_dict(
        native.get("build_provenance"),
        "native build provenance",
    )
    if set(provenance) != {
        "current_input_manifest",
        "embedded_input_sha256",
        "error",
        "matches_current_inputs",
        "schema_version",
    }:
        raise AssuranceReceiptError("native build-provenance fields are not exact")
    if provenance.get("schema_version") != 2:
        raise AssuranceReceiptError("native build-provenance schema is unsupported")
    if provenance.get("error") is not None:
        raise AssuranceReceiptError(
            f"native build provenance is unavailable: {provenance['error']}"
        )
    embedded = provenance.get("embedded_input_sha256")
    if (
        not isinstance(embedded, str)
        or len(embedded) != 64
        or any(character not in "0123456789abcdef" for character in embedded)
    ):
        raise AssuranceReceiptError("native embedded build digest is malformed")
    manifest = _require_dict(
        provenance.get("current_input_manifest"),
        "native current input manifest",
    )
    if set(manifest) != {"inputs", "schema_version", "sha256"}:
        raise AssuranceReceiptError("native input-manifest fields are not exact")
    if manifest.get("schema_version") != 2 or manifest.get("sha256") != embedded:
        raise AssuranceReceiptError(
            "native extension is not bound to the current input manifest"
        )
    raw_inputs = manifest.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise AssuranceReceiptError("native input manifest is empty or malformed")
    paths: list[str] = []
    for index, raw_input in enumerate(raw_inputs):
        input_identity = _require_dict(
            raw_input,
            f"native build input {index}",
        )
        if set(input_identity) != {"bytes", "hash_mode", "path", "sha256"}:
            raise AssuranceReceiptError("native build-input fields are not exact")
        relative_path = input_identity.get("path")
        if not isinstance(relative_path, str):
            raise AssuranceReceiptError("native build-input path is malformed")
        _safe_relative_path(relative_path, "native build-input path")
        paths.append(relative_path)
        hash_mode = input_identity.get("hash_mode")
        expected_hash_mode = (
            "toml_build_sections_v1"
            if relative_path == "pyproject.toml"
            else "raw_bytes"
        )
        if hash_mode != expected_hash_mode:
            raise AssuranceReceiptError("native build-input hash mode changed")
        size = input_identity.get("bytes")
        digest = input_identity.get("sha256")
        if (
            not isinstance(size, int)
            or size < 0
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise AssuranceReceiptError("native build-input identity is malformed")
    if paths != sorted(set(paths)):
        raise AssuranceReceiptError("native build-input paths are not unique and sorted")
    if provenance.get("matches_current_inputs") is not True:
        raise AssuranceReceiptError(
            "native extension was not built from the current checkout inputs"
        )

    from moira._native_build_provenance import native_build_input_manifest

    try:
        current_manifest = native_build_input_manifest(root)
    except Exception as exc:
        raise AssuranceReceiptError(
            "current native build inputs cannot be recomputed"
        ) from exc
    if manifest != current_manifest:
        raise AssuranceReceiptError(
            "sealed native build inputs differ from the current checkout"
        )


def _validate_run_identity(
    *,
    root: Path,
    requirements: Mapping[str, object],
    run: Mapping[str, object],
) -> None:
    """Bind a receipt to the admitted runtime and the current checkout."""

    policy = _require_dict(requirements.get("policy"), "assurance policy")
    required = _require_dict(
        policy.get("run_requirements"),
        "assurance run requirements",
    )
    run_policy = _require_dict(run.get("policy"), "run policy")
    for field in (
        "test_mode",
        "no_download",
        "strict_known_issues",
        "external_network_enabled",
    ):
        if run_policy.get(field) is not required.get(field):
            raise AssuranceReceiptError(
                f"run policy does not satisfy assurance requirement: {field}"
            )

    interpreter = _require_dict(run.get("interpreter"), "run interpreter")
    if interpreter.get("is_project_venv") is not required.get("project_venv"):
        raise AssuranceReceiptError(
            "run interpreter does not satisfy the project .venv requirement"
        )
    native = _require_dict(run.get("native"), "run native identity")
    expected_native_under_root = required.get("native_backend_under_repository")
    if native.get("backend_under_repository") is not expected_native_under_root:
        raise AssuranceReceiptError(
            "run native backend does not satisfy repository binding policy"
        )
    if expected_native_under_root and (
        native.get("available") is not True
        or not isinstance(native.get("backend_sha256"), str)
        or len(str(native.get("backend_sha256"))) != 64
    ):
        raise AssuranceReceiptError("run native backend identity is incomplete")
    if expected_native_under_root:
        _validate_native_build_provenance(root=root, native=native)
    repository = _require_dict(run.get("repository"), "run repository identity")
    git_identity = _require_dict(
        repository.get("git"),
        "run git identity",
    )
    if git_identity.get("available") is not required.get("git_identity"):
        raise AssuranceReceiptError(
            "run repository does not satisfy the git identity requirement"
        )

    assurance_runtime = _require_dict(
        run.get("assurance_runtime"),
        "run assurance runtime",
    )
    if set(assurance_runtime) != {"python", "toolchain_versions"}:
        raise AssuranceReceiptError("run assurance runtime fields are not exact")
    python_runtime = _require_dict(
        assurance_runtime["python"],
        "run assurance Python identity",
    )
    if set(python_runtime) != {
        "build",
        "cache_tag",
        "compiler",
        "executable",
        "executable_bytes",
        "executable_sha256",
        "hexversion",
        "implementation",
        "version",
    }:
        raise AssuranceReceiptError("run assurance Python fields are not exact")
    if (
        not isinstance(python_runtime.get("executable_bytes"), int)
        or python_runtime["executable_bytes"] <= 0
        or not isinstance(python_runtime.get("executable_sha256"), str)
        or len(python_runtime["executable_sha256"]) != 64
    ):
        raise AssuranceReceiptError("run interpreter artifact identity is invalid")
    required_versions = _require_dict(
        policy.get("runtime_versions"),
        "assurance runtime versions",
    )
    required_python = _require_dict(
        required_versions["python"],
        "required Python versions",
    )
    for field in ("cache_tag", "implementation", "version"):
        if python_runtime.get(field) != required_python.get(field):
            raise AssuranceReceiptError(
                f"run Python {field} differs from the admitted version"
            )
    if assurance_runtime.get("toolchain_versions") != required_versions.get(
        "toolchain_versions"
    ):
        raise AssuranceReceiptError("run assurance toolchain versions changed")

    current = _run_context(root)
    final_context = _require_dict(run.get("final_context"), "run final context")
    for field in (
        "assurance_runtime",
        "repository",
        "interpreter",
        "native",
        "execution_switches",
    ):
        if run.get(field) != final_context.get(field):
            raise AssuranceReceiptError(
                f"run {field} identity changed before receipt sealing"
            )
        if run.get(field) != current.get(field):
            raise AssuranceReceiptError(
                f"sealed run {field} identity differs from the current checkout"
            )


def _validate_coverage_identity(
    *,
    root: Path,
    requirements: Mapping[str, object],
    run: Mapping[str, object],
    coverage_file: Path,
    started_dt: datetime,
    finished_dt: datetime,
) -> None:
    """Require the exact CTracer data file sealed by this pytest run."""

    coverage = _require_dict(run.get("coverage"), "run coverage identity")
    if set(coverage) != {"core", "data_file", "pytest_cov", "runtime"}:
        raise AssuranceReceiptError("run coverage identity fields are not exact")
    core = _require_dict(coverage["core"], "run coverage core")
    if set(core) != {"environment", "is_ctrace", "policy"}:
        raise AssuranceReceiptError("run coverage core fields are not exact")
    policy = _require_dict(requirements.get("policy"), "assurance policy")
    required_core = policy.get("coverage_core")
    if (
        core.get("environment") != required_core
        or core.get("policy") != "explicit_environment"
        or core.get("is_ctrace") is not True
    ):
        raise AssuranceReceiptError(
            "run coverage core is not the required explicit CTracer core"
        )
    pytest_cov = _require_dict(
        coverage["pytest_cov"],
        "effective pytest-cov options",
    )
    if set(pytest_cov) != {
        "append",
        "branch",
        "config",
        "context",
        "no_cov",
        "source",
    }:
        raise AssuranceReceiptError("effective pytest-cov fields are not exact")
    if pytest_cov.get("append") is not False:
        raise AssuranceReceiptError("effective --cov-append is forbidden")
    if pytest_cov.get("no_cov") is not False:
        raise AssuranceReceiptError("effective --no-cov is forbidden")
    if pytest_cov.get("context") != "test":
        raise AssuranceReceiptError("effective pytest-cov context is not test")
    if pytest_cov.get("source") != policy.get("coverage_source"):
        raise AssuranceReceiptError("effective pytest-cov source changed")
    if pytest_cov.get("config") != policy.get("coverage_config"):
        raise AssuranceReceiptError("effective pytest-cov config changed")
    if pytest_cov.get("branch") is not policy.get("coverage_branch"):
        raise AssuranceReceiptError("effective pytest-cov branch policy changed")

    runtime = _require_dict(coverage["runtime"], "coverage runtime attestation")
    if set(runtime) != {"controller", "workers"}:
        raise AssuranceReceiptError("coverage runtime fields are not exact")
    workers = _require_dict(runtime["workers"], "coverage worker attestations")
    xdist = _require_dict(run.get("xdist"), "run xdist identity")
    if set(xdist) != {"mode", "worker_shutdown"}:
        raise AssuranceReceiptError("run xdist identity fields are not exact")
    xdist_mode = xdist.get("mode")
    if xdist_mode not in {
        "no",
        "load",
        "loadfile",
        "loadgroup",
        "loadscope",
        "worksteal",
    }:
        raise AssuranceReceiptError("run xdist scheduler mode is not admitted")
    raw_shutdown = xdist.get("worker_shutdown")
    if not isinstance(raw_shutdown, list):
        raise AssuranceReceiptError("run xdist worker shutdown roster is malformed")
    shutdown_workers: set[str] = set()
    for index, raw_status in enumerate(raw_shutdown):
        status = _require_dict(
            raw_status,
            f"xdist worker shutdown status {index}",
        )
        if set(status) != {"error", "exitstatus", "finalized", "worker_id"}:
            raise AssuranceReceiptError(
                "xdist worker shutdown status fields are not exact"
            )
        worker_id = status.get("worker_id")
        if not isinstance(worker_id, str) or not worker_id:
            raise AssuranceReceiptError("xdist worker shutdown identity is malformed")
        if worker_id in shutdown_workers:
            raise AssuranceReceiptError(
                f"xdist worker shutdown identity is duplicated: {worker_id}"
            )
        shutdown_workers.add(worker_id)
        if (
            status.get("error") is not None
            or status.get("exitstatus") != 0
            or status.get("finalized") is not True
        ):
            raise AssuranceReceiptError(
                f"xdist worker did not finalize successfully: {worker_id}"
            )
    if xdist_mode == "no":
        if workers or shutdown_workers:
            raise AssuranceReceiptError("serial run contains xdist workers")
    elif not shutdown_workers:
        raise AssuranceReceiptError("xdist run lacks finalized workers")
    if set(workers) != shutdown_workers:
        raise AssuranceReceiptError(
            "coverage worker set differs from the finalized xdist worker set"
        )

    runtime_policy = _require_dict(
        policy.get("coverage_runtime"),
        "coverage runtime policy",
    )
    expected_effective = _require_dict(
        runtime_policy.get("effective_config"),
        "coverage effective-config policy",
    )
    expected_config_files = runtime_policy.get("config_files")
    if not isinstance(expected_config_files, list) or not all(
        isinstance(path, str) for path in expected_config_files
    ):
        raise AssuranceReceiptError("coverage config-file policy is invalid")

    contributors = {"controller": runtime["controller"], **workers}
    for contributor, raw_identity in contributors.items():
        identity = _require_dict(
            raw_identity,
            f"{contributor} coverage runtime",
        )
        if set(identity) != {
            "active",
            "actual_core",
            "assurance_runtime",
            "config_files",
            "controller",
            "coverage_data_file",
            "effective_config",
            "environment",
            "final_run_context",
            "run_context",
        }:
            raise AssuranceReceiptError(
                f"{contributor} coverage runtime fields are not exact"
            )
        if identity.get("active") is not True:
            raise AssuranceReceiptError(
                f"{contributor} pytest-cov Coverage was not active"
            )
        if identity.get("actual_core") != runtime_policy.get("actual_core"):
            raise AssuranceReceiptError(
                f"{contributor} actual coverage tracer is not admitted"
            )
        if identity.get("assurance_runtime") != run.get("assurance_runtime"):
            raise AssuranceReceiptError(
                f"{contributor} assurance runtime differs from the controller"
            )
        contributor_context = _require_dict(
            identity.get("run_context"),
            f"{contributor} run context",
        )
        expected_context = {
            field: run.get(field)
            for field in (
                "assurance_runtime",
                "repository",
                "interpreter",
                "native",
                "execution_switches",
            )
        }
        if contributor_context != expected_context:
            raise AssuranceReceiptError(
                f"{contributor} run context differs from the controller"
            )
        final_contributor_context = _require_dict(
            identity.get("final_run_context"),
            f"{contributor} final run context",
        )
        if final_contributor_context != expected_context:
            raise AssuranceReceiptError(
                f"{contributor} final run context differs from the controller"
            )
        if identity.get("coverage_data_file") != str(coverage_file.resolve()):
            raise AssuranceReceiptError(
                f"{contributor} coverage data path changed"
            )
        effective = _require_dict(
            identity["effective_config"],
            f"{contributor} effective coverage config",
        )
        if effective != expected_effective:
            raise AssuranceReceiptError(
                f"{contributor} effective coverage configuration changed"
            )
        environment = _require_dict(
            identity["environment"],
            f"{contributor} coverage environment",
        )
        if set(environment) != {
            "COVERAGE_CORE",
            "COVERAGE_FILE",
            "COVERAGE_FORCE_CONFIG",
            "COVERAGE_PROCESS_CONFIG",
            "COVERAGE_PROCESS_START",
            "COVERAGE_RCFILE",
        }:
            raise AssuranceReceiptError(
                f"{contributor} coverage environment fields are not exact"
            )
        if environment.get("COVERAGE_CORE") != required_core:
            raise AssuranceReceiptError(
                f"{contributor} did not request the admitted coverage core"
            )
        if environment.get("COVERAGE_FILE") != str(coverage_file.resolve()):
            raise AssuranceReceiptError(
                f"{contributor} coverage data environment changed"
            )
        for forbidden in (
            "COVERAGE_FORCE_CONFIG",
            "COVERAGE_PROCESS_CONFIG",
            "COVERAGE_PROCESS_START",
            "COVERAGE_RCFILE",
        ):
            if environment.get(forbidden) is not None:
                raise AssuranceReceiptError(
                    f"{contributor} used forbidden ambient {forbidden}"
                )
        config_files = identity.get("config_files")
        if not isinstance(config_files, list):
            raise AssuranceReceiptError(
                f"{contributor} coverage config files are malformed"
            )
        config_paths: list[str] = []
        for sealed in config_files:
            config_identity = _require_dict(
                sealed,
                f"{contributor} coverage config file",
            )
            if set(config_identity) != {
                "bytes",
                "path",
                "path_policy",
                "resolved_path",
                "sha256",
            }:
                raise AssuranceReceiptError(
                    f"{contributor} coverage config-file fields are not exact"
                )
            if config_identity.get("path_policy") != "repository_relative":
                raise AssuranceReceiptError(
                    f"{contributor} coverage config is outside the checkout"
                )
            relative_path = config_identity.get("path")
            if not isinstance(relative_path, str):
                raise AssuranceReceiptError(
                    f"{contributor} coverage config path is malformed"
                )
            config_paths.append(relative_path)
            current_path = root / relative_path
            if (
                not current_path.is_file()
                or config_identity.get("resolved_path")
                != str(current_path.resolve())
                or config_identity.get("bytes") != current_path.stat().st_size
                or config_identity.get("sha256") != _sha256(current_path)
            ):
                raise AssuranceReceiptError(
                    f"{contributor} coverage config identity changed"
                )
        if config_paths != expected_config_files:
            raise AssuranceReceiptError(
                f"{contributor} coverage config provenance changed"
            )

        controller_name = identity.get("controller")
        expected_suffix = (
            ".DistWorker"
            if contributor != "controller"
            else ".Central" if xdist_mode == "no" else ".DistMaster"
        )
        if not isinstance(controller_name, str) or not controller_name.endswith(
            expected_suffix
        ):
            raise AssuranceReceiptError(
                f"{contributor} pytest-cov controller is not admitted"
            )

    data_file = _require_dict(coverage["data_file"], "run coverage data file")
    if set(data_file) != {
        "bytes",
        "mtime_ns",
        "path",
        "path_policy",
        "resolved_path",
        "sha256",
    }:
        raise AssuranceReceiptError("run coverage data identity fields are not exact")
    resolved = coverage_file.resolve()
    if data_file.get("resolved_path") != str(resolved):
        raise AssuranceReceiptError("coverage file path differs from sealed run identity")
    path_policy = data_file.get("path_policy")
    if path_policy == "repository_relative":
        try:
            expected_path = resolved.relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise AssuranceReceiptError(
                "repository-relative coverage path is outside the checkout"
            ) from exc
        if data_file.get("path") != expected_path:
            raise AssuranceReceiptError("coverage repository-relative path is invalid")
    elif path_policy == "absolute":
        if data_file.get("path") != str(resolved):
            raise AssuranceReceiptError("coverage absolute path is invalid")
    else:
        raise AssuranceReceiptError("coverage path policy is invalid")

    stat_result = coverage_file.stat()
    if data_file.get("bytes") != stat_result.st_size:
        raise AssuranceReceiptError("coverage byte count differs from sealed identity")
    if data_file.get("mtime_ns") != stat_result.st_mtime_ns:
        raise AssuranceReceiptError("coverage mtime differs from sealed identity")
    if data_file.get("sha256") != _sha256(coverage_file):
        raise AssuranceReceiptError("coverage SHA-256 differs from sealed identity")
    mtime = datetime.fromtimestamp(
        stat_result.st_mtime_ns / 1_000_000_000,
        tz=timezone.utc,
    )
    if mtime < started_dt.astimezone(timezone.utc):
        raise AssuranceReceiptError("coverage data predates the admitted run")
    if mtime > finished_dt.astimezone(timezone.utc):
        raise AssuranceReceiptError("coverage data postdates receipt sealing")


def _passing_nodeids(bundle: Mapping[str, object]) -> set[str]:
    durations = bundle["durations"]
    assert isinstance(durations, dict)
    cases = durations.get("cases")
    if not isinstance(cases, list):
        raise AssuranceReceiptError("duration cases are invalid")
    attempts: dict[str, list[dict[str, object]]] = {}
    for case in cases:
        case = _require_dict(case, "duration case")
        nodeid = case.get("nodeid")
        if not isinstance(nodeid, str):
            raise AssuranceReceiptError("duration case nodeid is invalid")
        attempts.setdefault(nodeid, []).append(case)
    wasxfail = {
        str(report.get("nodeid"))
        for report in bundle["reports"]
        if report.get("wasxfail") is not None
    }
    passing: set[str] = set()
    for nodeid, node_attempts in attempts.items():
        if len(node_attempts) != 1:
            continue
        case = node_attempts[0]
        if (
            case.get("attempt") == 1
            and case.get("complete") is True
            and case.get("passed") is True
            and case.get("failed") is False
            and case.get("case_budget_exceeded") is False
            and nodeid not in wasxfail
        ):
            passing.add(nodeid)
    return passing


def _receipt_claim_bindings(
    bundle: Mapping[str, object],
    contracts: Mapping[str, EvidenceContract],
) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    collection = bundle["collection"]
    assert isinstance(collection, dict)
    evidence = _require_dict(collection.get("evidence"), "collection evidence")
    try:
        _validate_receipt_payload(evidence)
    except (TypeError, ValueError) as exc:
        raise AssuranceReceiptError(
            f"sealed evidence manifest is invalid: {exc}"
        ) from exc
    receipt_contracts = evidence.get("contracts")
    bindings = evidence.get("bindings")
    if not isinstance(receipt_contracts, list) or not isinstance(bindings, list):
        raise AssuranceReceiptError("evidence contracts or bindings are invalid")
    by_claim: dict[str, dict[str, object]] = {}
    for entry in receipt_contracts:
        entry = _require_dict(entry, "receipt contract")
        claim_id = entry.get("claim_id")
        if not isinstance(claim_id, str) or claim_id not in contracts:
            raise AssuranceReceiptError("receipt contains an unknown claim")
        expected_contract = contracts[claim_id]
        if entry.get("contract") != contract_payload(expected_contract):
            raise AssuranceReceiptError(f"receipt contract changed: {claim_id}")
        if entry.get("contract_sha256") != contract_sha256(expected_contract):
            raise AssuranceReceiptError(f"receipt contract digest changed: {claim_id}")
        if claim_id in by_claim:
            raise AssuranceReceiptError(f"receipt repeats contract: {claim_id}")
        by_claim[claim_id] = entry
    node_claims: dict[str, str] = {}
    for binding in bindings:
        binding = _require_dict(binding, "evidence binding")
        nodeid = binding.get("nodeid")
        claim_id = binding.get("claim_id")
        if (
            not isinstance(nodeid, str)
            or not isinstance(claim_id, str)
            or claim_id not in by_claim
            or nodeid in node_claims
            or binding.get("contract_sha256")
            != by_claim[claim_id].get("contract_sha256")
        ):
            raise AssuranceReceiptError("receipt evidence binding is invalid")
        contract = contracts[claim_id]
        if not any(
            _base_matches(nodeid, base_nodeid)
            for base_nodeid in contract.nodeids
        ):
            raise AssuranceReceiptError(
                f"receipt binding is not admitted by {claim_id}: {nodeid}"
            )
        node_claims[nodeid] = claim_id
    if evidence.get("selected_items") != len(node_claims):
        raise AssuranceReceiptError("selected evidence item count is inconsistent")
    if evidence.get("selected_contracts") != len(by_claim):
        raise AssuranceReceiptError("selected evidence contract count is inconsistent")
    reported_bound_nodeids: set[str] = set()
    for report in bundle["reports"]:
        if report.get("kind") != "test":
            continue
        nodeid = report.get("nodeid")
        if not isinstance(nodeid, str):
            raise AssuranceReceiptError("test report nodeid is invalid")
        properties = _require_dict(
            report.get("user_properties"),
            "test report user properties",
        )
        actual = (
            properties.get("moira_validation_claim_id"),
            properties.get("moira_validation_contract_sha256"),
        )
        claim_id = node_claims.get(nodeid)
        if claim_id is None:
            if actual != (None, None):
                raise AssuranceReceiptError(
                    f"unbound report emitted validation identity: {nodeid}"
                )
            continue
        expected = (
            claim_id,
            contract_sha256(contracts[claim_id]),
        )
        if actual != expected:
            raise AssuranceReceiptError(
                f"report validation identity contradicts receipt: {nodeid}"
            )
        reported_bound_nodeids.add(nodeid)
    if reported_bound_nodeids != set(node_claims):
        raise AssuranceReceiptError(
            "one or more selected validation bindings produced no durable report"
        )
    return node_claims, by_claim


def _callable_body_lines(path: Path, qualname: str) -> set[int]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise AssuranceReceiptError(f"coverage target cannot be parsed: {path}") from exc
    matches: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            current = ".".join((*self.stack, node.name))
            if current == qualname:
                matches.append(node)
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        visit_FunctionDef = _visit_function
        visit_AsyncFunctionDef = _visit_function

    Visitor().visit(tree)
    if len(matches) != 1:
        raise AssuranceReceiptError(
            f"coverage target qualname is missing or ambiguous: {path}::{qualname}"
        )
    node = matches[0]
    lines: set[int] = set()
    for statement in node.body:
        end = getattr(statement, "end_lineno", statement.lineno)
        lines.update(range(statement.lineno, int(end) + 1))
    if not lines:
        raise AssuranceReceiptError(
            f"coverage target has no executable body: {path}::{qualname}"
        )
    return lines


def _coverage_context(context: object) -> tuple[str, str] | None:
    if not isinstance(context, str) or "|" not in context:
        return None
    nodeid, phase = context.rsplit("|", 1)
    if not nodeid or phase not in _ALLOWED_CONTEXT_PHASES:
        return None
    return nodeid, phase


def _measured_filename(coverage_data, target: Path) -> str:
    target_key = os.path.normcase(str(target.resolve()))
    matches = [
        filename
        for filename in coverage_data.measured_files()
        if os.path.normcase(str(Path(filename).resolve())) == target_key
    ]
    if len(matches) != 1:
        raise AssuranceReceiptError(
            f"coverage data does not identify exactly one target file: {target}"
        )
    return matches[0]


def _is_regression_only_protected_target(
    *,
    protected: object,
    evidence_classes: set[str],
) -> bool:
    """Classify only reviewed protected targets, never repository-wide code."""

    return protected is True and evidence_classes == {"regression"}


def evaluate_runtime_assurance(
    *,
    root: Path,
    requirements: Mapping[str, object],
    contracts: Mapping[str, EvidenceContract],
    receipt_dir: Path,
    coverage_file: Path,
) -> dict[str, object]:
    """Join a sealed green run with exact pytest-cov test contexts."""

    validate_requirements_against_contracts(requirements, contracts)
    try:
        from coverage import CoverageData
    except ImportError as exc:
        raise AssuranceReceiptError(
            "coverage is required only for the development assurance gate"
        ) from exc
    bundle = load_complete_receipt(receipt_dir)
    run = bundle["run"]
    assert isinstance(run, dict)
    invocation = _require_dict(run.get("invocation"), "run invocation")
    arguments = invocation.get("arguments")
    if not isinstance(arguments, list) or not all(
        isinstance(argument, str) for argument in arguments
    ):
        raise AssuranceReceiptError("run invocation arguments are invalid")
    if "--cov-context=test" not in arguments:
        raise AssuranceReceiptError("run did not use --cov-context=test")
    if not any(argument.startswith("--cov=") for argument in arguments):
        raise AssuranceReceiptError("run did not enable pytest-cov")
    if "--cov-append" in arguments:
        raise AssuranceReceiptError("appended coverage cannot fill assurance cells")
    coverage_file = coverage_file.resolve()
    if not coverage_file.is_file():
        raise AssuranceReceiptError("explicit coverage data file is missing")
    timing = _require_dict(run.get("timing"), "run timing")
    started = timing.get("started_utc")
    finished = timing.get("finished_utc")
    if not isinstance(started, str) or not isinstance(finished, str):
        raise AssuranceReceiptError("run timing identity is invalid")
    try:
        started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        finished_dt = datetime.fromisoformat(finished.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssuranceReceiptError("run timing is not ISO-8601") from exc
    if finished_dt < started_dt:
        raise AssuranceReceiptError("run timing is reversed")
    _validate_run_identity(
        root=root,
        requirements=requirements,
        run=run,
    )
    _validate_coverage_identity(
        root=root,
        requirements=requirements,
        run=run,
        coverage_file=coverage_file,
        started_dt=started_dt,
        finished_dt=finished_dt,
    )
    coverage_data = CoverageData(basename=str(coverage_file))
    try:
        coverage_data.read()
    except Exception as exc:
        raise AssuranceReceiptError("coverage data cannot be read") from exc
    if not coverage_data.has_arcs() and not coverage_data.measured_files():
        raise AssuranceReceiptError("coverage data is empty")
    node_claims, receipt_contracts = _receipt_claim_bindings(bundle, contracts)
    passing = _passing_nodeids(bundle)
    cells = requirements["cells"]
    assert isinstance(cells, list)
    results: list[dict[str, object]] = []
    regression_only: list[str] = []
    all_known_contexts: set[str] = set()
    for filename in coverage_data.measured_files():
        for contexts in coverage_data.contexts_by_lineno(filename).values():
            all_known_contexts.update(contexts)
    attributable_contexts = {
        context
        for context in all_known_contexts
        if (
            (parsed := _coverage_context(context)) is not None
            and parsed[0] in node_claims
            and parsed[0] in passing
        )
    }
    for cell in sorted(cells, key=lambda value: str(value["cell_id"])):
        claim_id = str(cell["required_claim_id"])
        if claim_id not in receipt_contracts:
            raise AssuranceReceiptError(
                f"{cell['cell_id']}: required claim was not selected"
            )
        selected_for_claim = sorted(
            nodeid
            for nodeid, bound_claim in node_claims.items()
            if bound_claim == claim_id
        )
        expected_nodeids: set[str] = set()
        for expected in cell["expected_bindings"]:
            base = str(expected["base_nodeid"])
            reviewed_nodeids = set(expected["nodeids"])
            actual = {
                nodeid for nodeid in selected_for_claim if _base_matches(nodeid, base)
            }
            if actual != reviewed_nodeids:
                raise AssuranceReceiptError(
                    f"{cell['cell_id']}: exact reviewed cases changed for {base}"
                )
            expected_nodeids.update(reviewed_nodeids)
        if set(selected_for_claim) != expected_nodeids:
            raise AssuranceReceiptError(
                f"{cell['cell_id']}: claim has unexpected selected bindings"
            )
        incomplete = sorted(set(selected_for_claim) - passing)
        if incomplete:
            raise AssuranceReceiptError(
                f"{cell['cell_id']}: required bindings did not pass completely: "
                + ", ".join(incomplete)
            )
        target_results: list[dict[str, object]] = []
        for target in cell["targets"]:
            relative = _safe_relative_path(target["path"], "coverage target")
            source_path = root.joinpath(*relative.parts)
            measured = _measured_filename(coverage_data, source_path)
            body_lines = _callable_body_lines(source_path, str(target["qualname"]))
            contexts_by_line = coverage_data.contexts_by_lineno(measured)
            accepted_nodeids: set[str] = set()
            evidence_classes: set[str] = set()
            for line_number in body_lines:
                for context in contexts_by_line.get(line_number, ()):
                    parsed = _coverage_context(context)
                    if parsed is None:
                        continue
                    nodeid, phase = parsed
                    bound_claim = node_claims.get(nodeid)
                    if (
                        phase not in target["phases"]
                        or nodeid not in passing
                        or bound_claim is None
                    ):
                        continue
                    evidence_classes.add(contracts[bound_claim].evidence_class.value)
                    if bound_claim == claim_id:
                        accepted_nodeids.add(nodeid)
            required_nodeids = set(selected_for_claim)
            if accepted_nodeids != required_nodeids:
                missing_contexts = sorted(required_nodeids - accepted_nodeids)
                raise AssuranceReceiptError(
                    f"{cell['cell_id']}: target lacks every passed {claim_id} "
                    f"coverage context for {target['path']}::{target['qualname']}: "
                    + ", ".join(missing_contexts)
                )
            if _is_regression_only_protected_target(
                protected=target["protected"],
                evidence_classes=evidence_classes,
            ):
                regression_only.append(
                    f"{target['path']}::{target['qualname']}"
                )
            target_results.append(
                {
                    "path": target["path"],
                    "qualname": target["qualname"],
                    "phases": list(target["phases"]),
                    "passed_context_nodeids": sorted(accepted_nodeids),
                }
            )
        results.append(
            {
                "cell_id": cell["cell_id"],
                "claim_id": claim_id,
                "evidence_class": cell["evidence_class"],
                "status": "filled",
                "selected_items": len(selected_for_claim),
                "targets": target_results,
            }
        )
    return {
        "schema_version": 1,
        "status": "complete",
        "coverage_file": str(coverage_file),
        "coverage_sha256": _sha256(coverage_file),
        "cells": results,
        "regression_only_protected_targets": sorted(regression_only),
        "regression_only_scope": "declared_protected_assurance_targets",
        "unattributed_contexts": sorted(all_known_contexts - attributable_contexts),
        "global_percentage_gate": None,
        "security_boundary": (
            "coverage contexts are cooperative attribution, not a security sandbox"
        ),
    }


__all__ = [
    "AssuranceReceiptError",
    "evaluate_runtime_assurance",
    "load_assurance_requirements",
    "load_complete_receipt",
    "validate_requirements_against_contracts",
]

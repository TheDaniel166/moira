"""Adversarial contracts for machine-checkable validation evidence."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
from textwrap import dedent

import pytest

from evidence.contracts import (
    CONTRACTS,
    Comparison,
    CoverageTarget,
    DeclaredField,
    EvidenceClass,
    EvidenceContract,
    EvidenceSource,
    SourceSet,
    contract_payload,
    contract_sha256,
    validate_contract,
    validate_registry,
)
from evidence.receipts import (
    AssuranceReceiptError,
    _validate_native_build_provenance,
    evaluate_runtime_assurance,
)
from _pytest_plugins.artifacts import _native_identity
from _pytest_plugins.evidence import (
    _validate_receipt_against_registry,
    _validate_receipt_payload,
)
from _pytest_plugins.evidence_schema import (
    EVIDENCE_SCHEMA_VERSION,
    canonical_python_ast_sha256,
    freeze_registry,
    synthetic_registry,
)


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_ROOT = Path(__file__).resolve().parents[2]
_SOURCE_TESTS = _ROOT / "tests"
_HARNESS_SOURCE = (_SOURCE_TESTS / "conftest.py").read_text(
    encoding="utf-8"
)
_POLICY_ENVIRONMENT = (
    "MOIRA_TEST_MODE",
    "MOIRA_NO_DOWNLOAD",
    "MOIRA_STRICT_KNOWN_ISSUES",
    "MOIRA_TEST_ARTIFACTS",
    "MOIRA_TEST_RUN_ID",
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "COVERAGE_FILE",
    "COVERAGE_CORE",
    "COVERAGE_FORCE_CONFIG",
    "COVERAGE_PROCESS_CONFIG",
    "COVERAGE_PROCESS_START",
    "COVERAGE_RCFILE",
)


def _field(value: str = "declared") -> DeclaredField:
    return DeclaredField.declared(value)


def _minimal_contract(**overrides: object) -> EvidenceContract:
    values: dict[str, object] = {
        "claim_id": "MOIRA-TEST-CLAIM-V1",
        "product_surface": "synthetic product surface",
        "evidence_class": EvidenceClass.INVARIANT,
        "governing_object": "synthetic independently derived invariant",
        "nodeids": ("tests/unit/test_probe.py::test_probe",),
        "proves": ("the synthetic relation holds for the admitted case",),
        "does_not_prove": ("external astronomical truth",),
        "authorities": SourceSet.not_applicable(
            "an invariant does not use an external authority"
        ),
        "fixtures": SourceSet.not_applicable(
            "the synthetic relation creates no fixture"
        ),
        "corpora": SourceSet.not_applicable(
            "the synthetic relation uses no corpus"
        ),
        "frame": _field("synthetic Cartesian frame"),
        "origin": _field("synthetic origin"),
        "timescale": DeclaredField.not_applicable(
            "the relation has no time coordinate"
        ),
        "correction_policy": DeclaredField.not_applicable(
            "the relation applies no corrections"
        ),
        "comparisons": (
            Comparison(
                metric="synthetic residual",
                unit="dimensionless",
                rule="absolute",
                absolute=1e-12,
                basis="binary64 round-off bound for the synthetic relation",
            ),
        ),
        "bodies": DeclaredField.not_applicable(
            "the relation contains no astronomical body"
        ),
        "interval": DeclaredField.not_applicable(
            "the relation contains no independent coordinate interval"
        ),
        "resource_capability": DeclaredField.not_applicable(
            "the relation is resource-free"
        ),
        "execution_paths": ("python:synthetic.probe",),
        "exclusions": ("hostile mutation of the test process",),
        "expected_refusal": (
            "collection fails when the claim contract is malformed",
        ),
        "coverage_targets": (
            CoverageTarget(
                path="moira/julian.py",
                qualname="julian_day",
                phases=("run",),
                protected=True,
            ),
        ),
    }
    values.update(overrides)
    return EvidenceContract(**values)


def test_committed_contract_registry_is_exact_valid_and_deterministic() -> None:
    validate_registry(CONTRACTS, root=_ROOT, verify_assets=True)

    assert tuple(CONTRACTS) == tuple(sorted(CONTRACTS))
    payloads = [contract_payload(contract) for contract in CONTRACTS.values()]
    assert [payload["claim_id"] for payload in payloads] == list(CONTRACTS)
    for contract in CONTRACTS.values():
        digest = contract_sha256(contract)
        assert len(digest) == 64
        assert digest == contract_sha256(contract)
        assert json.loads(
            json.dumps(contract_payload(contract), sort_keys=True)
        ) == contract_payload(contract)


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        ({"claim_id": "not stable"}, "claim_id"),
        ({"product_surface": ""}, "product_surface"),
        ({"proves": ()}, "proves"),
        ({"does_not_prove": ()}, "does_not_prove"),
        ({"nodeids": ("../escape.py::test_probe",)}, "nodeid"),
        ({"execution_paths": ()}, "execution_paths"),
        ({"expected_refusal": ()}, "expected_refusal"),
        ({"coverage_targets": ()}, "coverage_targets"),
    ),
)
def test_contract_rejects_missing_or_ambiguous_required_cells(
    mutation: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        validate_contract(
            replace(_minimal_contract(), **mutation),
            root=_ROOT,
            verify_assets=False,
        )


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -1.0])
def test_contract_rejects_nonfinite_or_negative_tolerance(
    threshold: float,
) -> None:
    comparison = replace(
        _minimal_contract().comparisons[0],
        absolute=threshold,
    )
    with pytest.raises(ValueError, match="absolute"):
        validate_contract(
            replace(_minimal_contract(), comparisons=(comparison,)),
            root=_ROOT,
            verify_assets=False,
        )


def test_authority_claim_requires_a_named_primary_authority() -> None:
    contract = replace(
        _minimal_contract(),
        evidence_class=EvidenceClass.AUTHORITY,
    )
    with pytest.raises(ValueError, match="authority"):
        validate_contract(contract, root=_ROOT, verify_assets=False)


def test_native_parity_requires_python_and_native_execution_paths() -> None:
    contract = replace(
        _minimal_contract(),
        evidence_class=EvidenceClass.NATIVE_PARITY,
        execution_paths=("python:synthetic.reference",),
    )
    with pytest.raises(ValueError, match="python.*native"):
        validate_contract(contract, root=_ROOT, verify_assets=False)


def test_local_evidence_hash_is_verified_against_content(tmp_path: Path) -> None:
    test_path = tmp_path / "tests" / "unit" / "test_probe.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text("def test_probe():\n    pass\n", encoding="utf-8")
    source_path = tmp_path / "moira" / "julian.py"
    source_path.parent.mkdir()
    source_path.write_text("def julian_day():\n    pass\n", encoding="utf-8")
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text("{}\n", encoding="utf-8")
    source = EvidenceSource(
        name="synthetic fixture",
        locator="fixture.json",
        version="v1",
        sha256="0" * 64,
        local=True,
    )
    contract = replace(
        _minimal_contract(),
        fixtures=SourceSet.declared(source),
    )
    with pytest.raises(ValueError, match="SHA-256"):
        validate_contract(contract, root=tmp_path, verify_assets=True)


def test_python_protocol_digest_is_scoped_dependency_closed_and_eol_stable(
    tmp_path: Path,
) -> None:
    source = """
import pytest

CASES = (1, 2)

def helper(value):
    '''Return the admitted value.'''
    return value

@pytest.mark.parametrize("value", CASES)
def test_probe(value):
    '''Exercise the admitted helper.'''
    assert helper(value) == value

def unrelated():
    return 1
""".lstrip()
    path = tmp_path / "test_protocol.py"
    path.write_bytes(source.encode("utf-8"))
    baseline = canonical_python_ast_sha256(path, ("test_probe",))

    path.write_bytes(source.replace("\n", "\r\n").encode("utf-8"))
    assert canonical_python_ast_sha256(path, ("test_probe",)) == baseline

    path.write_text(
        source.replace(
            "Return the admitted value.",
            "Changed helper documentation only.",
        ).replace(
            "Exercise the admitted helper.",
            "Changed test documentation only.",
        ),
        encoding="utf-8",
    )
    assert canonical_python_ast_sha256(path, ("test_probe",)) == baseline

    path.write_text(source.replace("return 1\n", "return 99\n"), encoding="utf-8")
    assert canonical_python_ast_sha256(path, ("test_probe",)) == baseline

    path.write_text(
        source + "\ndef unrelated():\n    return 2\n",
        encoding="utf-8",
    )
    assert canonical_python_ast_sha256(path, ("test_probe",)) == baseline

    path.write_text(
        source.replace("return value\n", "return value + 1\n"),
        encoding="utf-8",
    )
    assert canonical_python_ast_sha256(path, ("test_probe",)) != baseline

    path.write_text(
        source.replace("CASES = (1, 2)", "CASES = (1, 3)"),
        encoding="utf-8",
    )
    assert canonical_python_ast_sha256(path, ("test_probe",)) != baseline

    path.write_text(
        source + "\ndef helper(value):\n    return value\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="selected Python protocol symbol is rebound"):
        canonical_python_ast_sha256(path, ("test_probe",))


def test_python_protocol_preserves_semantic_none_and_rejects_doc_introspection(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test_protocol.py"
    path.write_text(
        "FLAG = None\n\ndef test_probe():\n    assert FLAG is None\n",
        encoding="utf-8",
    )
    protocol = canonical_python_ast_sha256(path, ("test_probe",))
    assert len(protocol) == 64
    from _pytest_plugins.evidence_schema import canonical_python_ast_bytes

    assert b'"scalar_type":"none"' in canonical_python_ast_bytes(
        path,
        ("test_probe",),
    )

    path.write_text(
        'def helper():\n    """visible"""\n    return helper.__doc__\n\n'
        "def test_probe():\n    assert helper()\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="cannot exclude an introspected docstring"):
        canonical_python_ast_sha256(path, ("test_probe",))


def test_native_build_manifest_changes_with_every_admitted_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os
    import stat
    from types import SimpleNamespace

    from moira._native_build_provenance import (
        native_build_input_manifest,
        stage_native_build_snapshot,
    )

    for relative_path in (
        "CMakeLists.txt",
        "moira/_native_build_provenance.py",
        "setup.py",
        "src/native/bindings.cpp",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"admitted input: {relative_path}\n", encoding="utf-8")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[build-system]\n"
        'requires = ["setuptools"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        "[tool.setuptools]\n"
        "include-package-data = false\n\n"
        "[tool.setuptools.package-data]\n"
        'moira = ["data/*.txt"]\n\n'
        "[tool.pytest.ini_options]\n"
        'markers = ["one"]\n',
        encoding="utf-8",
    )

    baseline = native_build_input_manifest(tmp_path)
    assert [item["path"] for item in baseline["inputs"]] == sorted(
        [
            "CMakeLists.txt",
            "moira/_native_build_provenance.py",
            "pyproject.toml",
            "setup.py",
            "src/native/bindings.cpp",
        ]
    )

    native_source = tmp_path / "src" / "native" / "bindings.cpp"
    native_source.write_text("changed native source\n", encoding="utf-8")
    changed_source = native_build_input_manifest(tmp_path)
    assert changed_source["sha256"] != baseline["sha256"]

    readme = tmp_path / "src" / "native" / "README.md"
    readme.write_text("not a native build input\n", encoding="utf-8")
    assert native_build_input_manifest(tmp_path) == changed_source

    new_header = tmp_path / "src" / "native" / "new_header.hpp"
    new_header.write_text("new native input\n", encoding="utf-8")
    changed_file_set = native_build_input_manifest(tmp_path)
    assert changed_file_set["sha256"] != changed_source["sha256"]
    assert changed_file_set["inputs"][-1]["path"] == (
        "src/native/new_header.hpp"
    )

    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            'markers = ["one"]',
            'markers = ["two"]',
        ),
        encoding="utf-8",
    )
    assert native_build_input_manifest(tmp_path) == changed_file_set

    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            'requires = ["setuptools"]',
            'requires = ["setuptools", "wheel"]',
        ),
        encoding="utf-8",
    )
    build_config_manifest = native_build_input_manifest(tmp_path)
    assert build_config_manifest["sha256"] != (
        changed_file_set["sha256"]
    )

    snapshot_root = tmp_path / "build" / "native_source_snapshot"
    stage_native_build_snapshot(
        tmp_path,
        snapshot_root,
        build_config_manifest,
    )
    assert native_build_input_manifest(snapshot_root) == build_config_manifest
    new_header.write_text("post-staging checkout edit\n", encoding="utf-8")
    assert native_build_input_manifest(snapshot_root) == build_config_manifest

    native_root = tmp_path / "src" / "native"
    real_scandir = os.scandir

    class _FakeReparseEntry:
        name = "linked-native-tree"
        path = str(native_root / name)

        @staticmethod
        def stat(*, follow_symlinks: bool) -> object:
            assert follow_symlinks is False
            return SimpleNamespace(
                st_mode=stat.S_IFDIR,
                st_file_attributes=0x400,
            )

    class _FakeScandir:
        def __enter__(self) -> list[object]:
            return [_FakeReparseEntry()]

        def __exit__(self, *_args: object) -> None:
            return None

    def _scandir(path: object):
        if Path(path) == native_root:
            return _FakeScandir()
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", _scandir)
    with pytest.raises(ValueError, match="link or reparse point"):
        native_build_input_manifest(tmp_path)


def test_native_build_provenance_rejects_stale_extension_identity() -> None:
    native = _native_identity(_ROOT)
    _validate_native_build_provenance(root=_ROOT, native=native)

    stale = json.loads(json.dumps(native))
    stale["build_provenance"]["matches_current_inputs"] = False
    stale["build_provenance"]["error"] = (
        "native extension build inputs differ from the current checkout"
    )
    with pytest.raises(
        AssuranceReceiptError,
        match="native build provenance is unavailable",
    ):
        _validate_native_build_provenance(root=_ROOT, native=stale)


def test_native_identity_ignores_mutable_python_shim_copies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from moira import moira_native
    from importlib import import_module

    expected = _native_identity(_ROOT)
    monkeypatch.setattr(moira_native, "__backend_file__", __file__)
    monkeypatch.setattr(
        moira_native,
        "_build_input_manifest_sha256",
        lambda: "0" * 64,
    )
    assert _native_identity(_ROOT) == expected

    raw_backend = import_module("moira._moira_native")
    forged_backend = tmp_path / Path(str(expected["backend_path"])).name
    shutil.copyfile(str(expected["backend_path"]), forged_backend)
    monkeypatch.setattr(raw_backend, "__file__", str(forged_backend))
    monkeypatch.setattr(raw_backend.__spec__, "origin", str(forged_backend))
    forged_identity = _native_identity(_ROOT)
    assert forged_identity["available"] is False
    assert "loader filename contradicts" in str(forged_identity["error"])


def test_native_identity_rejects_mutable_loaded_marker_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from importlib import import_module

    raw_backend = import_module("moira._moira_native")
    monkeypatch.setattr(
        raw_backend,
        "_build_provenance_marker",
        lambda: "MOIRA_NATIVE_BUILD_INPUT_MANIFEST_SHA256=" + "0" * 64,
    )
    identity = _native_identity(_ROOT)
    assert identity["available"] is False
    assert "built-in build-provenance marker" in str(identity["error"])


def test_contract_nodeid_must_name_an_existing_ast_callable(
    tmp_path: Path,
) -> None:
    test_path = tmp_path / "tests" / "unit" / "test_probe.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text(
        "def test_probe():\n    pass\n",
        encoding="utf-8",
    )
    source_path = tmp_path / "moira" / "julian.py"
    source_path.parent.mkdir()
    source_path.write_text(
        "def julian_day():\n    pass\n",
        encoding="utf-8",
    )

    validate_contract(_minimal_contract(), root=tmp_path, verify_assets=True)
    with pytest.raises(ValueError, match="test callable does not exist"):
        validate_contract(
            replace(
                _minimal_contract(),
                nodeids=("tests/unit/test_probe.py::test_missing",),
            ),
            root=tmp_path,
            verify_assets=True,
        )


def test_freeze_registry_rejects_duplicate_claim_ids() -> None:
    contract = _minimal_contract()

    with pytest.raises(ValueError, match="duplicate claim_id"):
        freeze_registry((contract, replace(contract, product_surface="other")))


def test_coverage_target_rejects_path_escape_and_unbounded_phase() -> None:
    for target in (
        CoverageTarget("../moira.py", "probe", ("run",), True),
        CoverageTarget("moira/probe.py", "probe", ("foreign",), True),
    ):
        with pytest.raises(ValueError, match="coverage"):
            validate_contract(
                replace(
                    _minimal_contract(),
                    coverage_targets=(target,),
                ),
                root=_ROOT,
                verify_assets=False,
            )


def _make_project(
    pytester: pytest.Pytester,
    *,
    test_source: str,
    registry_source: str,
) -> tuple[Path, Path]:
    root = pytester.path
    tests_dir = root / "tests"
    tests_dir.mkdir()
    shutil.copytree(_SOURCE_TESTS / "support", tests_dir / "support")
    shutil.copytree(
        _SOURCE_TESTS / "_pytest_plugins",
        tests_dir / "_pytest_plugins",
    )
    evidence_dir = tests_dir / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "__init__.py").write_text("", encoding="utf-8")
    (evidence_dir / "contracts.py").write_text(
        dedent(registry_source),
        encoding="utf-8",
    )
    (tests_dir / "conftest.py").write_text(
        _HARNESS_SOURCE,
        encoding="utf-8",
    )
    (tests_dir / "KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    (tests_dir / "unit").mkdir()
    (tests_dir / "unit" / "test_probe.py").write_text(
        dedent(test_source),
        encoding="utf-8",
    )
    config = root / "pytest.ini"
    config.write_text(
        "[pytest]\n"
        "pythonpath = . tests\n"
        "strict_config = true\n"
        "strict_markers = true\n",
        encoding="utf-8",
    )
    return root, config


def _run_project(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    config: Path,
    *arguments: str,
    run_id: str | None = None,
    coverage_file: Path | None = None,
    pytest_addopts: str | None = None,
    coverage_environment: dict[str, str] | None = None,
) -> pytest.RunResult:
    for name in _POLICY_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1")
    if run_id is not None:
        monkeypatch.setenv("MOIRA_TEST_ARTIFACTS", "1")
        monkeypatch.setenv("MOIRA_TEST_RUN_ID", run_id)
    if coverage_file is not None:
        monkeypatch.setenv("COVERAGE_FILE", str(coverage_file))
        monkeypatch.setenv("COVERAGE_CORE", "ctrace")
    if pytest_addopts is not None:
        monkeypatch.setenv("PYTEST_ADDOPTS", pytest_addopts)
    for name, value in (coverage_environment or {}).items():
        monkeypatch.setenv(name, value)
    effective_arguments = list(arguments)
    if (
        coverage_file is not None
        and not any(
            argument.startswith("--cov-config")
            for argument in effective_arguments
        )
        and "--cov-config" not in (pytest_addopts or "")
    ):
        effective_arguments.append("--cov-config=pytest.ini")
    return pytester.runpytest_subprocess(
        "-c",
        str(config),
        "--rootdir",
        str(root),
        *effective_arguments,
    )


_SYNTHETIC_REGISTRY = """
from _pytest_plugins.evidence_schema import synthetic_registry
CONTRACTS = synthetic_registry()
"""


def test_collection_rejects_unknown_contract_id(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-UNKNOWN-V1")
            def test_probe():
                assert True
        """,
    )
    result = _run_project(pytester, monkeypatch, root, config, "tests/unit")
    assert result.ret != pytest.ExitCode.OK
    result.stderr.fnmatch_lines(["*unknown validation contract*"])


def test_collection_rejects_local_hypothesis_settings_on_contracted_test(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest
            from hypothesis import given, settings, strategies as st

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            @settings(max_examples=1)
            @given(st.integers())
            def test_probe(value):
                assert isinstance(value, int)
        """,
    )
    result = _run_project(pytester, monkeypatch, root, config, "tests/unit")
    assert result.ret != pytest.ExitCode.OK
    result.stderr.fnmatch_lines(
        ["*contract-bound Hypothesis tests*explicit @settings*forbidden*"]
    )


def test_collection_rejects_missing_marker_on_reviewed_surface(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            def test_probe():
                assert True
        """,
    )
    result = _run_project(pytester, monkeypatch, root, config, "tests/unit")
    assert result.ret != pytest.ExitCode.OK
    result.stderr.fnmatch_lines(
        ["*reviewed validation surface requires validation_contract*"]
    )


def test_runtime_rejects_marker_mutation_during_test_call(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe(request):
                request.node.own_markers = [
                    marker
                    for marker in request.node.own_markers
                    if marker.name != "validation_contract"
                ]
        """,
    )
    result = _run_project(pytester, monkeypatch, root, config, "tests/unit")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        ["*validation evidence binding changed after collection*"]
    )


def test_runtime_rejects_duplicate_evidence_properties(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe(record_property):
                record_property(
                    "moira_validation_claim_id",
                    "MOIRA-TEST-CLAIM-V1",
                )
        """,
    )
    result = _run_project(pytester, monkeypatch, root, config, "tests/unit")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        ["*validation evidence user properties changed after collection*"]
    )


def test_selected_binding_without_any_report_fails_session_policy(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe():
                assert True
        """,
    )
    (root / "suppress_execution.py").write_text(
        dedent(
            """
            import pytest

            @pytest.hookimpl(tryfirst=True)
            def pytest_runtestloop(session):
                return True
            """
        ),
        encoding="utf-8",
    )
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "-p",
        "suppress_execution",
        "tests/unit",
        run_id="missing-evidence-report",
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(
        ["*selected validation binding produced no test report*"]
    )
    collection = json.loads(
        (
            _receipt_dir(root, "missing-evidence-report")
            / "collection.json"
        ).read_text(encoding="utf-8")
    )
    assert collection["evidence_errors"] == [
        "tests/unit/test_probe.py::test_probe: selected validation binding "
        "produced no test report"
    ]


def test_controller_rejects_self_signed_ghost_worker_binding() -> None:
    import hashlib

    from _pytest_plugins.evidence_schema import canonical_json_bytes

    claim_id, contract = next(iter(CONTRACTS.items()))
    digest = contract_sha256(contract)
    payload = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "contracts": [
            {
                "claim_id": claim_id,
                "contract_sha256": digest,
                "contract": contract_payload(contract),
            }
        ],
        "bindings": [
            {
                "nodeid": "tests/unit/does_not_exist.py::test_ghost",
                "claim_id": claim_id,
                "contract_sha256": digest,
            }
        ],
        "class_counts": [[contract.evidence_class.value, 1]],
        "selected_contracts": 1,
        "selected_items": 1,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        canonical_json_bytes(payload)
    ).hexdigest()
    validated = _validate_receipt_payload(payload)
    with pytest.raises(ValueError, match="not admitted"):
        _validate_receipt_against_registry(validated)


def test_report_redaction_cannot_mutate_reserved_evidence_identity(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe():
                assert True
        """,
    )
    monkeypatch.setenv(
        "MOIRA_PHASE9_EVIDENCE_SECRET",
        "moira_validation",
    )
    run_id = "evidence-report-redaction-refusal"
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "tests/unit",
        run_id=run_id,
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    receipt_dir = _receipt_dir(root, run_id)
    assert not (receipt_dir / "COMPLETE").exists()
    incomplete = json.loads(
        (receipt_dir / "INCOMPLETE").read_text(encoding="utf-8")
    )
    assert any(
        "reserved validation report identity" in error
        for error in incomplete["finalization_errors"]
    )


@pytest.mark.parametrize(
    "marker",
    (
        "@pytest.mark.validation_contract",
        "@pytest.mark.validation_contract()",
        "@pytest.mark.validation_contract('MOIRA-TEST-CLAIM-V1', 'extra')",
        "@pytest.mark.validation_contract(claim_id='MOIRA-TEST-CLAIM-V1')",
    ),
)
def test_collection_rejects_malformed_contract_marker(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    marker: str,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source=f"""
            import pytest

            {marker}
            def test_probe():
                assert True
        """,
    )
    result = _run_project(pytester, monkeypatch, root, config, "tests/unit")
    assert result.ret != pytest.ExitCode.OK
    result.stderr.fnmatch_lines(["*validation_contract*exactly one*"])


def _receipt_dir(root: Path, run_id: str) -> Path:
    return root / ".pytest_cache" / "moira-artifacts" / run_id


def _rewrite_run_and_reseal(
    receipt_dir: Path,
    run: dict[str, object],
) -> None:
    run_bytes = (
        json.dumps(
            run,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    (receipt_dir / "run.json").write_bytes(run_bytes)
    complete = json.loads(
        (receipt_dir / "COMPLETE").read_text(encoding="utf-8")
    )
    complete["run_json"] = {
        "bytes": len(run_bytes),
        "sha256": hashlib.sha256(run_bytes).hexdigest(),
    }
    complete_bytes = (
        json.dumps(
            complete,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    (receipt_dir / "COMPLETE").write_bytes(complete_bytes)


def _synthetic_requirements(
    *,
    nodeids: list[str] | None = None,
) -> dict[str, object]:
    contract = synthetic_registry()["MOIRA-TEST-CLAIM-V1"]
    reviewed_nodeids = nodeids or [contract.nodeids[0]]
    return {
        "schema_version": 1,
        "policy": {
            "admission_scope": "phase9_and_phase10_reviewed_claims",
            "coverage_branch": None,
            "coverage_config": "pytest.ini",
            "coverage_context": "pytest-cov --cov-context=test",
            "coverage_core": "ctrace",
            "coverage_is_scientific_gate": False,
            "coverage_phase_default": "run",
            "coverage_source": ["tests"],
            "coverage_runtime": {
                "actual_core": "CTracer",
                "config_files": ["pytest.ini"],
                "effective_config": {
                    "branch": False,
                    "concurrency": [],
                    "core": "ctrace",
                    "dynamic_context": None,
                    "parallel": True,
                    "plugins": [],
                    "relative_files": False,
                    "source": ["tests"],
                    "static_context": None,
                    "timid": False,
                },
            },
            "global_percentage_gate": None,
            "required_cell_rule": "exact synthetic cell",
            "run_requirements": {
                "external_network_enabled": False,
                "git_identity": False,
                "native_backend_under_repository": False,
                "no_download": True,
                "project_venv": False,
                "strict_known_issues": True,
                "test_mode": True,
            },
            "runtime_versions": {
                "python": {
                    "cache_tag": "cpython-314",
                    "implementation": "CPython",
                    "version": "3.14.3",
                },
                "toolchain_versions": {
                    "coverage": "7.13.5",
                    "pytest": "9.0.2",
                    "pytest_cov": "7.0.0",
                    "xdist": "3.8.0",
                },
            },
            "security_boundary": "cooperative attribution only",
        },
        "cells": [
            {
                "cell_id": "synthetic-invariant",
                "expected_contract_sha256": contract_sha256(contract),
                "product_surface": contract.product_surface,
                "evidence_class": contract.evidence_class.value,
                "required_claim_id": contract.claim_id,
                "expected_bindings": [
                    {
                        "base_nodeid": contract.nodeids[0],
                        "nodeids": reviewed_nodeids,
                    }
                ],
                "targets": contract_payload(contract)["coverage_targets"],
            }
        ],
    }


def test_selected_contract_is_emitted_once_with_exact_item_binding(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe():
                assert True
        """,
    )
    run_id = "evidence-serial-receipt"
    coverage_file = root / ".coverage-evidence-serial"
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "--cov=tests",
        "--cov-context=test",
        "--cov-report=",
        "tests/unit",
        run_id=run_id,
        coverage_file=coverage_file,
    )
    result.assert_outcomes(passed=1)

    receipt_dir = _receipt_dir(root, run_id)
    assert (receipt_dir / "COMPLETE").is_file()
    collection = json.loads(
        (receipt_dir / "collection.json").read_text(encoding="utf-8")
    )
    evidence = collection["evidence"]
    assert collection["evidence_errors"] == []
    assert evidence["selected_contracts"] == 1
    assert evidence["selected_items"] == 1
    assert evidence["class_counts"] == [["invariant", 1]]
    assert evidence["bindings"] == [
        {
            "nodeid": "tests/unit/test_probe.py::test_probe",
            "claim_id": "MOIRA-TEST-CLAIM-V1",
            "contract_sha256": evidence["contracts"][0][
                "contract_sha256"
            ],
        }
    ]
    reports = [
        json.loads(line)
        for line in (receipt_dir / "reports.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    phase_reports = [
        report
        for report in reports
        if report["nodeid"] == "tests/unit/test_probe.py::test_probe"
    ]
    assert {report["phase"] for report in phase_reports} == {
        "setup",
        "call",
        "teardown",
    }
    for report in phase_reports:
        assert report["user_properties"]["moira_validation_claim_id"] == (
            "MOIRA-TEST-CLAIM-V1"
        )
        assert report["user_properties"][
            "moira_validation_contract_sha256"
        ] == evidence["contracts"][0]["contract_sha256"]
    runtime = evaluate_runtime_assurance(
        root=root,
        requirements=_synthetic_requirements(),
        contracts=synthetic_registry(),
        receipt_dir=receipt_dir,
        coverage_file=coverage_file,
    )
    assert runtime["cells"][0]["status"] == "filled"

    stale_coverage = root / ".coverage-evidence-stale"
    shutil.copyfile(coverage_file, stale_coverage)
    os.utime(stale_coverage, (1, 1))
    with pytest.raises(
        AssuranceReceiptError,
        match="(?:path differs|data path changed)",
    ):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=receipt_dir,
            coverage_file=stale_coverage,
        )

    from coverage import CoverageData

    original_bytes = coverage_file.read_bytes()
    original_stat = coverage_file.stat()
    coverage_file.unlink()
    foreign_data = CoverageData(basename=str(coverage_file))
    foreign_data.set_context(
        "tests/unit/test_probe.py::test_probe|run"
    )
    foreign_data.add_lines(
        {str(root / "tests" / "unit" / "test_probe.py"): set(range(1, 20))}
    )
    foreign_data.write()
    with pytest.raises(
        AssuranceReceiptError,
        match="byte count|mtime|SHA-256",
    ):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=receipt_dir,
            coverage_file=coverage_file,
        )

    coverage_file.write_bytes(original_bytes)
    os.utime(
        coverage_file,
        ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
    )
    run_payload = json.loads(
        (receipt_dir / "run.json").read_text(encoding="utf-8")
    )
    drifted_context = {
        field: run_payload[field]
        for field in (
            "assurance_runtime",
            "repository",
            "interpreter",
            "native",
            "execution_switches",
        )
    }
    drifted_context = json.loads(json.dumps(drifted_context))
    drifted_context["repository"]["git"]["error"] = (
        "simulated post-run source drift"
    )
    monkeypatch.setattr(
        "evidence.receipts._run_context",
        lambda _root: drifted_context,
    )
    with pytest.raises(AssuranceReceiptError, match="repository identity"):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=receipt_dir,
            coverage_file=coverage_file,
        )

    runtime_drift = {
        field: run_payload[field]
        for field in (
            "assurance_runtime",
            "repository",
            "interpreter",
            "native",
            "execution_switches",
        )
    }
    runtime_drift = json.loads(json.dumps(runtime_drift))
    runtime_drift["assurance_runtime"]["python"][
        "executable_sha256"
    ] = "0" * 64
    monkeypatch.setattr(
        "evidence.receipts._run_context",
        lambda _root: runtime_drift,
    )
    with pytest.raises(AssuranceReceiptError, match="assurance_runtime identity"):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=receipt_dir,
            coverage_file=coverage_file,
        )


def test_xdist_workers_reconcile_one_identical_selected_manifest(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("xdist")
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            @pytest.mark.parallel(reason="isolated_resources")
            def test_probe():
                assert True
        """,
    )
    run_id = "evidence-xdist-receipt"
    coverage_file = root / ".coverage-evidence-xdist"
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "-n",
        "2",
        "-m",
        "parallel",
        "--cov=tests",
        "--cov-context=test",
        "--cov-report=",
        "tests/unit",
        run_id=run_id,
        coverage_file=coverage_file,
    )
    result.assert_outcomes(passed=1)
    collection = json.loads(
        (_receipt_dir(root, run_id) / "collection.json").read_text(
            encoding="utf-8"
        )
    )
    assert collection["evidence"]["selected_contracts"] == 1
    assert collection["evidence"]["selected_items"] == 1
    assert collection["evidence_errors"] == []
    run = json.loads(
        (_receipt_dir(root, run_id) / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(run["xdist"]["worker_shutdown"]) == 2
    coverage_runtime = run["coverage"]["runtime"]
    assert set(coverage_runtime["workers"]) == {"gw0", "gw1"}
    assert coverage_runtime["controller"]["actual_core"] == "CTracer"
    assert all(
        worker["actual_core"] == "CTracer"
        for worker in coverage_runtime["workers"].values()
    )
    assert all(
        worker["assurance_runtime"] == run["assurance_runtime"]
        for worker in coverage_runtime["workers"].values()
    )
    runtime = evaluate_runtime_assurance(
        root=root,
        requirements=_synthetic_requirements(),
        contracts=synthetic_registry(),
        receipt_dir=_receipt_dir(root, run_id),
        coverage_file=coverage_file,
    )
    assert runtime["cells"][0]["status"] == "filled"

    unmodified_run = json.loads(json.dumps(run))
    run["coverage"]["runtime"]["workers"]["gw0"][
        "assurance_runtime"
    ]["toolchain_versions"]["coverage"] = "0.0"
    _rewrite_run_and_reseal(_receipt_dir(root, run_id), run)
    with pytest.raises(
        AssuranceReceiptError,
        match="gw0 assurance runtime differs from the controller",
    ):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=_receipt_dir(root, run_id),
            coverage_file=coverage_file,
        )

    missing_worker_run = json.loads(json.dumps(unmodified_run))
    del missing_worker_run["coverage"]["runtime"]["workers"]["gw0"]
    _rewrite_run_and_reseal(
        _receipt_dir(root, run_id),
        missing_worker_run,
    )
    with pytest.raises(
        AssuranceReceiptError,
        match="coverage worker set differs from the finalized xdist worker set",
    ):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=_receipt_dir(root, run_id),
            coverage_file=coverage_file,
        )

    foreign_native_run = json.loads(json.dumps(unmodified_run))
    foreign_native_run["coverage"]["runtime"]["workers"]["gw0"][
        "final_run_context"
    ]["native"]["backend_sha256"] = "0" * 64
    _rewrite_run_and_reseal(
        _receipt_dir(root, run_id),
        foreign_native_run,
    )
    with pytest.raises(
        AssuranceReceiptError,
        match="gw0 final run context differs from the controller",
    ):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=_receipt_dir(root, run_id),
            coverage_file=coverage_file,
        )


def test_same_count_parameter_substitution_cannot_fill_reviewed_cell(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.parametrize("case", ["alpha", "beta"])
            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe(case):
                assert case in {"alpha", "beta"}
        """,
    )
    run_id = "evidence-exact-parameter-cases"
    coverage_file = root / ".coverage-evidence-exact-cases"
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "--cov=tests",
        "--cov-context=test",
        "--cov-report=",
        "tests/unit",
        run_id=run_id,
        coverage_file=coverage_file,
    )
    result.assert_outcomes(passed=2)

    exact_nodeids = [
        "tests/unit/test_probe.py::test_probe[alpha]",
        "tests/unit/test_probe.py::test_probe[beta]",
    ]
    runtime = evaluate_runtime_assurance(
        root=root,
        requirements=_synthetic_requirements(nodeids=exact_nodeids),
        contracts=synthetic_registry(),
        receipt_dir=_receipt_dir(root, run_id),
        coverage_file=coverage_file,
    )
    assert runtime["cells"][0]["targets"][0][
        "passed_context_nodeids"
    ] == exact_nodeids

    substituted = list(exact_nodeids)
    substituted[1] = "tests/unit/test_probe.py::test_probe[gamma]"
    with pytest.raises(AssuranceReceiptError, match="exact reviewed cases changed"):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(nodeids=substituted),
            contracts=synthetic_registry(),
            receipt_dir=_receipt_dir(root, run_id),
            coverage_file=coverage_file,
        )


def test_ambient_cov_append_cannot_fill_assurance_cell(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe():
                assert True
        """,
    )
    run_id = "evidence-ambient-cov-append"
    coverage_file = root / ".coverage-evidence-ambient-append"
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "--cov=tests",
        "--cov-context=test",
        "--cov-report=",
        "tests/unit",
        run_id=run_id,
        coverage_file=coverage_file,
        pytest_addopts="--cov-append",
    )
    result.assert_outcomes(passed=1)
    with pytest.raises(AssuranceReceiptError, match="effective --cov-append"):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=_receipt_dir(root, run_id),
            coverage_file=coverage_file,
        )


def test_requested_ctrace_cannot_hide_an_actual_pytracer(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe():
                assert True
        """,
    )
    timid_config = root / "timid.ini"
    timid_config.write_text("[run]\ntimid = true\n", encoding="utf-8")
    run_id = "evidence-actual-pytracer"
    coverage_file = root / ".coverage-evidence-actual-pytracer"
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "--cov=tests",
        "--cov-config=timid.ini",
        "--cov-context=test",
        "--cov-report=",
        "tests/unit",
        run_id=run_id,
        coverage_file=coverage_file,
    )
    result.assert_outcomes(passed=1)
    receipt_dir = _receipt_dir(root, run_id)
    run = json.loads((receipt_dir / "run.json").read_text(encoding="utf-8"))
    assert run["coverage"]["runtime"]["controller"]["actual_core"] == (
        "PyTracer"
    )
    requirements = _synthetic_requirements()
    requirements["policy"]["coverage_config"] = "timid.ini"
    requirements["policy"]["coverage_runtime"]["config_files"] = [
        "timid.ini"
    ]
    with pytest.raises(AssuranceReceiptError, match="actual coverage tracer"):
        evaluate_runtime_assurance(
            root=root,
            requirements=requirements,
            contracts=synthetic_registry(),
            receipt_dir=receipt_dir,
            coverage_file=coverage_file,
        )


def test_ambient_coverage_rcfile_cannot_fill_assurance_cell(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe():
                assert True
        """,
    )
    ambient = root / "ambient-coverage.ini"
    ambient.write_text("[run]\ntimid = false\n", encoding="utf-8")
    run_id = "evidence-ambient-coverage-rcfile"
    coverage_file = root / ".coverage-evidence-ambient-coverage-rcfile"
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "--cov=tests",
        "--cov-context=test",
        "--cov-report=",
        "tests/unit",
        run_id=run_id,
        coverage_file=coverage_file,
        coverage_environment={"COVERAGE_RCFILE": str(ambient)},
    )
    result.assert_outcomes(passed=1)
    with pytest.raises(
        AssuranceReceiptError,
        match="forbidden ambient COVERAGE_RCFILE",
    ):
        evaluate_runtime_assurance(
            root=root,
            requirements=_synthetic_requirements(),
            contracts=synthetic_registry(),
            receipt_dir=_receipt_dir(root, run_id),
            coverage_file=coverage_file,
        )


def test_deselected_contract_does_not_masquerade_as_executed_evidence(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, config = _make_project(
        pytester,
        registry_source=_SYNTHETIC_REGISTRY,
        test_source="""
            import pytest

            @pytest.mark.validation_contract("MOIRA-TEST-CLAIM-V1")
            def test_probe():
                assert True

            def test_other():
                assert True
        """,
    )
    run_id = "evidence-deselected-receipt"
    result = _run_project(
        pytester,
        monkeypatch,
        root,
        config,
        "-k",
        "other",
        "tests/unit",
        run_id=run_id,
    )
    result.assert_outcomes(passed=1, deselected=1)
    collection = json.loads(
        (_receipt_dir(root, run_id) / "collection.json").read_text(
            encoding="utf-8"
        )
    )
    assert collection["evidence"]["selected_contracts"] == 0
    assert collection["evidence"]["selected_items"] == 0

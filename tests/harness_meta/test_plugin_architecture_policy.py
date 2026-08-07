"""Fail-closed contracts for the extracted pytest-plugin architecture."""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
import shutil
import sys
from textwrap import dedent

import pytest


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_SOURCE_TESTS = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = _SOURCE_TESTS.parent
_PLUGIN_DIR = _SOURCE_TESTS / "_pytest_plugins"
_TESTS_CONFTEST = _SOURCE_TESTS / "conftest.py"
_HARNESS_SOURCE = (_SOURCE_TESTS / "conftest.py").read_text(encoding="utf-8")
_TARGET_PLUGIN_MODULES = (
    "_pytest_plugins.classification",
    "_pytest_plugins.configuration",
    "_pytest_plugins.determinism",
    "_pytest_plugins.network_policy",
    "_pytest_plugins.known_issues",
    "_pytest_plugins.xdist_coordination",
    "_pytest_plugins.resources",
    "_pytest_plugins.lifecycle",
    "_pytest_plugins.artifacts",
    "_pytest_plugins.evidence",
)
_POLICY_ENVIRONMENT = (
    "MOIRA_TEST_MODE",
    "MOIRA_NO_DOWNLOAD",
    "MOIRA_TEST_SEED",
    "MOIRA_TEST_BUDGET_TOTAL_S",
    "MOIRA_TEST_BUDGET_CASE_S",
    "MOIRA_STRICT_KNOWN_ISSUES",
    "MOIRA_SNAPSHOT_UPDATE",
    "MOIRA_GOLDEN_UPDATE",
    "MOIRA_TEST_NETWORK_POLICY",
    "MOIRA_TEST_ARTIFACTS",
    "MOIRA_TEST_RUN_ID",
    "MOIRA_REGRESSION_PCT",
    "PYTEST_XDIST_WORKER",
    "PYTEST_XDIST_WORKER_COUNT",
    "MOIRA_WORKER_ID",
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "_MOIRA_ROOT_HARNESS_BOOTSTRAP",
)
_TESTS_SCOPED_FIXTURES = (
    "snapshot",
    "golden",
    "ritual",
    "moira_approx",
    "assert_longitude",
    "eclipse_calculator",
)
_FIXTURE_SCOPES = {
    "snapshot": "function",
    "golden": "function",
    "ritual": "function",
    "moira_approx": "function",
    "assert_longitude": "function",
    "eclipse_calculator": "session",
}
_HOOK_CONTRACTS = (
    (
        "_pytest_plugins.classification",
        "pytest_configure",
        "pytest_configure",
        False,
        False,
        False,
        False,
        False,
    ),
    (
        "_pytest_plugins.classification",
        "pytest_collection_modifyitems",
        "pytest_collection_modifyitems",
        True,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.classification",
        "pytest_collection_finish",
        "pytest_collection_finish",
        True,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.classification",
        "pytest_runtest_setup",
        "pytest_runtest_setup_execution_classification",
        False,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.configuration",
        "pytest_configure",
        "pytest_configure",
        False,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.determinism",
        "pytest_configure",
        "pytest_configure",
        False,
        False,
        False,
        False,
        False,
    ),
    (
        "_pytest_plugins.determinism",
        "pytest_sessionstart",
        "pytest_sessionstart",
        False,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.network_policy",
        "pytest_configure",
        "pytest_configure",
        False,
        False,
        False,
        False,
        False,
    ),
    (
        "_pytest_plugins.network_policy",
        "pytest_collection_modifyitems",
        "pytest_collection_modifyitems_external_network_isolation",
        False,
        False,
        False,
        True,
        False,
    ),
    (
        "_pytest_plugins.network_policy",
        "pytest_runtest_protocol",
        "pytest_runtest_protocol",
        False,
        True,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.known_issues",
        "pytest_configure",
        "pytest_configure",
        False,
        False,
        False,
        False,
        False,
    ),
    (
        "_pytest_plugins.xdist_coordination",
        "pytest_configure",
        "pytest_configure",
        False,
        False,
        False,
        True,
        False,
    ),
    (
        "_pytest_plugins.xdist_coordination",
        "pytest_sessionfinish",
        "pytest_sessionfinish",
        True,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.xdist_coordination",
        "pytest_sessionfinish",
        "pytest_sessionfinish_worker_receipt_seal",
        True,
        False,
        False,
        True,
        False,
    ),
    (
        "_pytest_plugins.xdist_coordination",
        "pytest_xdist_make_scheduler",
        "pytest_xdist_make_scheduler",
        True,
        False,
        True,
        False,
        True,
    ),
    (
        "_pytest_plugins.xdist_coordination",
        "pytest_configure_node",
        "pytest_configure_node",
        False,
        False,
        False,
        False,
        True,
    ),
    (
        "_pytest_plugins.xdist_coordination",
        "pytest_testnodedown",
        "pytest_testnodedown",
        False,
        False,
        False,
        False,
        True,
    ),
    (
        "_pytest_plugins.resources",
        "pytest_runtest_setup",
        "pytest_runtest_setup",
        False,
        False,
        False,
        False,
        False,
    ),
    (
        "_pytest_plugins.lifecycle",
        "pytest_sessionstart",
        "pytest_sessionstart",
        False,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.lifecycle",
        "pytest_runtest_makereport",
        "pytest_runtest_makereport",
        True,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.artifacts",
        "pytest_configure",
        "pytest_configure",
        False,
        False,
        False,
        False,
        False,
    ),
    (
        "_pytest_plugins.artifacts",
        "pytest_runtest_makereport",
        "pytest_runtest_makereport",
        True,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.artifacts",
        "pytest_sessionstart",
        "pytest_sessionstart",
        False,
        False,
        False,
        True,
        False,
    ),
    (
        "_pytest_plugins.evidence",
        "pytest_collection_modifyitems",
        "pytest_collection_modifyitems",
        True,
        False,
        False,
        True,
        False,
    ),
    (
        "_pytest_plugins.evidence",
        "pytest_runtest_setup",
        "pytest_runtest_setup",
        True,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.evidence",
        "pytest_runtest_call",
        "pytest_runtest_call",
        True,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.evidence",
        "pytest_runtest_teardown",
        "pytest_runtest_teardown",
        True,
        False,
        True,
        False,
        False,
    ),
    (
        "_pytest_plugins.evidence",
        "pytest_terminal_summary",
        "pytest_terminal_summary",
        False,
        False,
        False,
        False,
        False,
    ),
)
_AUXILIARY_HOOK_CONTRACTS = (
    (
        "_pytest_plugins.artifacts",
        "_ControllerReceiptCollector",
        "pytest_runtest_logreport",
        "pytest_runtest_logreport",
        False,
        False,
        False,
        False,
        False,
    ),
    (
        "_pytest_plugins.artifacts",
        "_ControllerReceiptCollector",
        "pytest_collectreport",
        "pytest_collectreport",
        False,
        False,
        False,
        False,
        False,
    ),
    (
        "_pytest_plugins.artifacts",
        "_ControllerReceiptCollector",
        "pytest_collection_finish",
        "pytest_collection_finish",
        False,
        False,
        False,
        False,
        False,
    ),
)
_SHARED_STASH_KEYS = (
    "_ARTIFACT_DIR_KEY",
    "_ARTIFACT_FINALIZATION_ERRORS_KEY",
    "_ARTIFACT_ITEM_SECRET_VALUES_KEY",
    "_ARTIFACT_START_CONTEXT_KEY",
    "_CASE_LIFECYCLE_KEY",
    "_CLASSIFICATION_RECEIPT_KEY",
    "_COVERAGE_RUNTIME_IDENTITY_KEY",
    "_COLLECTED_EXECUTION_ITEMS_KEY",
    "_CONTROLLER_EVIDENCE_ERRORS_KEY",
    "_EVIDENCE_ITEM_BINDING_KEY",
    "_EVIDENCE_ITEM_VIOLATION_KEY",
    "_EVIDENCE_PAYLOAD_KEY",
    "_EVIDENCE_SELECTED_RECEIPT_KEY",
    "_EXECUTION_CLASSIFICATION_FROZEN_KEY",
    "_EXECUTION_CLASSIFICATION_IDENTITY_ITEM_KEY",
    "_EXTERNAL_NETWORK_SELECTED_KEY",
    "_HARNESS_CONFIG_KEY",
    "_KNOWN_ISSUES_KEY",
    "_LIFECYCLE_PAYLOAD_KEY",
    "_PRIMARY_CLASS_ITEM_KEY",
    "_RECEIPT_COLLECTOR_KEY",
    "_RESOURCE_ITEM_RECEIPT_KEY",
    "_RESOURCE_ITEM_REQUIREMENT_KEY",
    "_RESOURCE_RECEIPTS_KEY",
    "_RESOURCE_RESOLVER_KEY",
    "_SESSION_PERF_START_KEY",
    "_SESSION_TOTAL_BUDGET_KEY",
    "_SESSION_UTC_START_KEY",
    "_SMALL_BODY_RESOURCE_RECEIPTS_KEY",
    "_XDIST_CLASSIFICATION_ERRORS_STATE_KEY",
    "_XDIST_CLASSIFICATION_EXPECTED_STATE_KEY",
    "_XDIST_CLASSIFICATION_REPORTED_STATE_KEY",
    "_XDIST_CLASSIFICATION_REPORT_STATE_KEY",
    "_XDIST_COVERAGE_RUNTIME_ERRORS_STATE_KEY",
    "_XDIST_COVERAGE_RUNTIME_REPORT_STATE_KEY",
    "_XDIST_EVIDENCE_ERRORS_STATE_KEY",
    "_XDIST_EVIDENCE_EXPECTED_STATE_KEY",
    "_XDIST_EVIDENCE_REPORTED_STATE_KEY",
    "_XDIST_EVIDENCE_REPORT_STATE_KEY",
    "_XDIST_MODE_KEY",
    "_XDIST_PLANETARY_RESOURCE_REPORT_STATE_KEY",
    "_XDIST_SMALL_BODY_RESOURCE_REPORT_STATE_KEY",
    "_XDIST_WORKER_ACTIVE_KEY",
    "_XDIST_WORKER_CLASSIFICATION_VIOLATION_COUNT_STATE_KEY",
    "_XDIST_WORKER_CLASSIFICATION_VIOLATIONS_STATE_KEY",
)


def test_required_plugin_manifest_is_exact_complete_and_local(
    pytestconfig: pytest.Config,
) -> None:
    bootstrap = importlib.import_module("_pytest_plugins")

    assert bootstrap.REQUIRED_PLUGIN_MODULES == _TARGET_PLUGIN_MODULES
    for module_name in _TARGET_PLUGIN_MODULES:
        module = importlib.import_module(module_name)
        assert pytestconfig.pluginmanager.get_plugin(module_name) is module
        assert Path(module.__file__).resolve().is_relative_to(
            _PLUGIN_DIR.resolve()
        )
        assert f"tests.{module_name}" not in sys.modules


@pytest.mark.parametrize(
    (
        "module_name",
        "hook_name",
        "function_name",
        "wrapper",
        "hookwrapper",
        "tryfirst",
        "trylast",
        "optionalhook",
    ),
    _HOOK_CONTRACTS,
    ids=[
        f"{module_name.rsplit('.', 1)[-1]}:"
        f"{hook_name}:{function_name}"
        for module_name, hook_name, function_name, *_flags
        in _HOOK_CONTRACTS
    ],
)
def test_required_plugin_hook_contract_is_exact(
    pytestconfig: pytest.Config,
    module_name: str,
    hook_name: str,
    function_name: str,
    wrapper: bool,
    hookwrapper: bool,
    tryfirst: bool,
    trylast: bool,
    optionalhook: bool,
) -> None:
    module = importlib.import_module(module_name)
    hook = getattr(pytestconfig.pluginmanager.hook, hook_name)
    implementations = [
        implementation
        for implementation in hook.get_hookimpls()
        if (
            implementation.plugin is module
            and implementation.function.__name__ == function_name
        )
    ]

    assert len(implementations) == 1
    implementation = implementations[0]
    assert (
        implementation.wrapper,
        implementation.hookwrapper,
        implementation.tryfirst,
        implementation.trylast,
        implementation.optionalhook,
    ) == (
        wrapper,
        hookwrapper,
        tryfirst,
        trylast,
        optionalhook,
    )


@pytest.mark.parametrize("module_name", _TARGET_PLUGIN_MODULES)
def test_required_plugin_has_no_uncontracted_hooks(
    pytestconfig: pytest.Config,
    module_name: str,
) -> None:
    module = importlib.import_module(module_name)
    callers = pytestconfig.pluginmanager.get_hookcallers(module) or ()
    actual = {caller.name for caller in callers}
    expected = {
        hook_name
        for contract_module, hook_name, *_rest in _HOOK_CONTRACTS
        if contract_module == module_name
    }
    assert actual == expected


def test_controller_collector_hook_contract_is_exact(
    pytestconfig: pytest.Config,
) -> None:
    artifacts = importlib.import_module("_pytest_plugins.artifacts")
    collector = artifacts._controller_collector(pytestconfig)
    expected = {
        (
            hook_name,
            function_name,
            wrapper,
            hookwrapper,
            tryfirst,
            trylast,
            optionalhook,
        )
        for (
            _module_name,
            _owner_name,
            hook_name,
            function_name,
            wrapper,
            hookwrapper,
            tryfirst,
            trylast,
            optionalhook,
        ) in _AUXILIARY_HOOK_CONTRACTS
    }

    if collector is None:
        assert getattr(pytestconfig, "workerinput", None) is not None
        actual = set()
        collector_type = artifacts._ControllerReceiptCollector
        for (
            _module_name,
            _owner_name,
            hook_name,
            function_name,
            *_flags,
        ) in _AUXILIARY_HOOK_CONTRACTS:
            options = getattr(
                getattr(collector_type, function_name),
                "pytest_impl",
            )
            actual.add(
                (
                    options["specname"] or hook_name,
                    function_name,
                    options["wrapper"],
                    options["hookwrapper"],
                    options["tryfirst"],
                    options["trylast"],
                    options["optionalhook"],
                )
            )
        assert actual == expected
        return

    actual = set()
    for caller in pytestconfig.pluginmanager.get_hookcallers(collector) or ():
        for implementation in caller.get_hookimpls():
            if implementation.plugin is not collector:
                continue
            actual.add(
                (
                    caller.name,
                    implementation.function.__name__,
                    implementation.wrapper,
                    implementation.hookwrapper,
                    implementation.tryfirst,
                    implementation.trylast,
                    implementation.optionalhook,
                )
            )
    assert actual == expected


def test_wrapper_order_preserves_lifecycle_and_worker_evidence(
    pytestconfig: pytest.Config,
) -> None:
    plugin_manager = pytestconfig.pluginmanager

    collection_plugins = [
        implementation.plugin_name
        for implementation
        in plugin_manager.hook.pytest_collection_modifyitems.get_hookimpls()
    ]
    assert collection_plugins.index("_pytest_plugins.network_policy") < (
        collection_plugins.index("_pytest_plugins.classification")
    )

    report_plugins = [
        implementation.plugin_name
        for implementation
        in plugin_manager.hook.pytest_runtest_makereport.get_hookimpls()
    ]
    assert report_plugins.index("_pytest_plugins.lifecycle") < (
        report_plugins.index("_pytest_plugins.artifacts")
    )

    finish_plugins = [
        (
            implementation.plugin_name,
            implementation.function.__name__,
        )
        for implementation
        in plugin_manager.hook.pytest_sessionfinish.get_hookimpls()
    ]
    assert finish_plugins.index(
        (
            "_pytest_plugins.xdist_coordination",
            "pytest_sessionfinish_worker_receipt_seal",
        )
    ) < finish_plugins.index(
        (
            "_pytest_plugins.xdist_coordination",
            "pytest_sessionfinish",
        )
    )


def _pytest_function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("pytest_")
        )
    }


def _hookimpl_declarations(
    path: Path,
) -> list[tuple[str, str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    declarations: list[tuple[str, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        ancestor = parents.get(node)
        owner_parts: list[str] = []
        while ancestor is not None and not isinstance(ancestor, ast.Module):
            if isinstance(
                ancestor,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                owner_parts.append(ancestor.name)
            ancestor = parents.get(ancestor)
        owner_name = ".".join(reversed(owner_parts)) or "<module>"

        for decorator in node.decorator_list:
            decorator_call = (
                decorator
                if isinstance(decorator, ast.Call)
                else None
            )
            target = (
                decorator_call.func
                if decorator_call is not None
                else decorator
            )
            if not (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "pytest"
                and target.attr == "hookimpl"
            ):
                continue
            hook_name = node.name
            if decorator_call is not None:
                for keyword in decorator_call.keywords:
                    if (
                        keyword.arg == "specname"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        hook_name = keyword.value.value
            declarations.append((owner_name, hook_name, node.name))
    return declarations


@pytest.mark.parametrize("module_name", _TARGET_PLUGIN_MODULES)
def test_required_plugin_source_has_only_contracted_hookimpls(
    module_name: str,
) -> None:
    source_path = (
        _PLUGIN_DIR / f"{module_name.rsplit('.', 1)[-1]}.py"
    )
    actual = sorted(_hookimpl_declarations(source_path))
    expected = sorted(
        ("<module>", hook_name, function_name)
        for (
            contract_module,
            hook_name,
            function_name,
            *_flags,
        ) in _HOOK_CONTRACTS
        if contract_module == module_name
    )
    expected.extend(
        sorted(
            (owner_name, hook_name, function_name)
            for (
                contract_module,
                owner_name,
                hook_name,
                function_name,
                *_flags,
            ) in _AUXILIARY_HOOK_CONTRACTS
            if contract_module == module_name
        )
    )
    expected.sort()
    assert actual == expected


def test_conftest_hook_surfaces_are_only_registration_guards() -> None:
    assert _pytest_function_names(_TESTS_CONFTEST) == {
        "pytest_addoption",
        "pytest_collection_finish_required_plugin_guard",
        "pytest_configure_required_plugins",
    }
    assert _pytest_function_names(_SOURCE_ROOT / "conftest.py") == {
        "pytest_addoption",
        "pytest_collection_finish",
        "pytest_configure",
    }


def test_loaded_tests_conftest_owns_only_runtime_registration_guards(
    pytestconfig: pytest.Config,
) -> None:
    plugin_manager = pytestconfig.pluginmanager
    owners = [
        plugin
        for _name, plugin in plugin_manager.list_name_plugin()
        if (
            getattr(plugin, "__file__", None)
            and Path(plugin.__file__).resolve() == _TESTS_CONFTEST.resolve()
        )
    ]
    assert len(owners) == 1

    owner = owners[0]
    actual = set()
    for caller in plugin_manager.get_hookcallers(owner) or ():
        for implementation in caller.get_hookimpls():
            if implementation.plugin is not owner:
                continue
            actual.add(
                (
                    caller.name,
                    implementation.function.__name__,
                    implementation.wrapper,
                    implementation.hookwrapper,
                    implementation.tryfirst,
                    implementation.trylast,
                )
            )
    assert actual == {
        (
            "pytest_configure",
            "pytest_configure_required_plugins",
            False,
            False,
            True,
            False,
        ),
        (
            "pytest_collection_finish",
            "pytest_collection_finish_required_plugin_guard",
            False,
            False,
            False,
            True,
        ),
    }


def test_shared_stash_keys_have_one_canonical_identity() -> None:
    state = importlib.import_module("_pytest_plugins._state")
    actual = {
        name: value
        for name, value in vars(state).items()
        if isinstance(value, pytest.StashKey)
    }
    assert set(actual) == set(_SHARED_STASH_KEYS)
    assert len({id(key) for key in actual.values()}) == len(actual)

    for module_name in _TARGET_PLUGIN_MODULES:
        module = importlib.import_module(module_name)
        for key_name, canonical_key in actual.items():
            imported_key = vars(module).get(key_name)
            if imported_key is not None:
                assert imported_key is canonical_key

    state_path = _PLUGIN_DIR / "_state.py"
    for source_path in (
        _SOURCE_ROOT / "conftest.py",
        _TESTS_CONFTEST,
        *sorted(_PLUGIN_DIR.glob("*.py")),
    ):
        tree = ast.parse(
            source_path.read_text(encoding="utf-8"),
            filename=str(source_path),
        )
        stash_key_calls = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and (
                    (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "StashKey"
                    )
                    or (
                        isinstance(node.func, ast.Name)
                        and node.func.id == "StashKey"
                    )
                )
            )
        ]
        if source_path == state_path:
            assert len(stash_key_calls) == len(_SHARED_STASH_KEYS)
        else:
            assert not stash_key_calls, source_path


@pytest.mark.parametrize("fixture_name", _TESTS_SCOPED_FIXTURES)
def test_shared_fixture_has_one_tests_scoped_owner(
    request: pytest.FixtureRequest,
    fixture_name: str,
) -> None:
    """Fixture extraction must not widen these exports into a root plugin."""

    fixture_manager = request._fixturemanager
    definitions = fixture_manager.getfixturedefs(fixture_name, request.node)
    assert definitions is not None
    assert len(definitions) == 1, [
        {
            "baseid": definition.baseid,
            "source": inspect.getsourcefile(definition.func),
        }
        for definition in definitions
    ]

    definition = definitions[0]
    assert definition.argname == fixture_name
    assert definition.baseid == "tests"
    assert definition.scope == _FIXTURE_SCOPES[fixture_name]
    assert definition.func.__module__ == "tests.conftest"
    assert Path(inspect.getsourcefile(definition.func)).resolve() == (
        _TESTS_CONFTEST.resolve()
    )


def _make_project(pytester: pytest.Pytester) -> tuple[Path, Path]:
    root = pytester.path
    tests_dir = root / "tests"
    tests_dir.mkdir()
    shutil.copytree(_SOURCE_TESTS / "support", tests_dir / "support")
    shutil.copytree(_PLUGIN_DIR, tests_dir / "_pytest_plugins")
    (tests_dir / "conftest.py").write_text(
        _HARNESS_SOURCE,
        encoding="utf-8",
    )
    (tests_dir / "KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    (tests_dir / "test_probe.py").write_text(
        "def test_probe():\n    assert True\n",
        encoding="utf-8",
    )
    config = root / "pytest.ini"
    config.write_text(
        dedent(
            """
            [pytest]
            pythonpath = . tests
            strict_config = true
            strict_markers = true
            """
        ),
        encoding="utf-8",
    )
    return root, config


def test_evidence_terminal_receipt_is_emitted_once(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in _POLICY_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1")
    root, config = _make_project(pytester)

    result = pytester.runpytest_subprocess(
        "-c",
        str(config),
        str(root / "tests"),
        "-q",
        "--color=no",
        timeout=60,
    )

    result.assert_outcomes(passed=1)
    output = f"{result.stdout.str()}\n{result.stderr.str()}"
    assert output.count("Moira: harness policy receipt") == 1
    assert output.count("Execution classification:") == 1
    assert output.count("Moira: slowest tests") == 1


@pytest.mark.parametrize("blocked_module", _TARGET_PLUGIN_MODULES)
def test_required_plugin_cannot_be_silently_blocked(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    blocked_module: str,
) -> None:
    for name in _POLICY_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1")
    root, config = _make_project(pytester)

    result = pytester.runpytest_subprocess(
        "-c",
        str(config),
        "-p",
        f"no:{blocked_module}",
        str(root / "tests"),
        "-q",
        "--color=no",
        timeout=60,
    )

    output = f"{result.stdout.str()}\n{result.stderr.str()}"
    assert result.ret == pytest.ExitCode.USAGE_ERROR, output
    assert "Required Moira pytest plugin was blocked" in output
    assert blocked_module in output

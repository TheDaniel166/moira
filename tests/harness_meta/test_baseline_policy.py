"""Adversarial contracts for immutable snapshot and golden baselines."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from types import ModuleType
from typing import Callable

import pytest

from tools import golden as golden_module
from tools import snapshots as snapshot_module


@dataclass(frozen=True, slots=True)
class _BaselineChannel:
    name: str
    module: ModuleType
    directory_attribute: str
    update_environment: str
    assertion: Callable[[str, object], None]


_CHANNELS = (
    _BaselineChannel(
        name="snapshot",
        module=snapshot_module,
        directory_attribute="SNAPSHOT_DIR",
        update_environment="MOIRA_SNAPSHOT_UPDATE",
        assertion=snapshot_module.assert_snapshot,
    ),
    _BaselineChannel(
        name="golden",
        module=golden_module,
        directory_attribute="GOLDEN_DIR",
        update_environment="MOIRA_GOLDEN_UPDATE",
        assertion=golden_module.assert_golden,
    ),
)

_TESTS_DIR = Path(__file__).resolve().parents[1]
_HARNESS_SOURCE = (_TESTS_DIR / "conftest.py").read_text(encoding="utf-8")
_NETWORK_POLICY_SOURCE = (
    _TESTS_DIR / "support" / "network_policy.py"
).read_text(encoding="utf-8")
_NETWORK_BOOTSTRAP_SOURCE = (
    _TESTS_DIR / "support" / "network_bootstrap" / "sitecustomize.py"
).read_text(encoding="utf-8")
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
)
_PYTEST_CONFIG = """\
[pytest]
markers =
    loopback: local IPC only
    external_network: explicitly permitted external access
    network: forbidden legacy marker
    parallel: tests admitted for parallel execution
    property: property-based tests
"""
_NO_KERNEL_BOOTSTRAP = """

@pytest.fixture(scope="session", autouse=True)
def _bootstrap_kernel_singleton():
    \"\"\"Keep baseline-policy mini-projects independent of local kernels.\"\"\"
    yield
"""


@pytest.fixture(params=_CHANNELS, ids=lambda channel: channel.name)
def baseline_channel(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[_BaselineChannel, Path]:
    channel: _BaselineChannel = request.param
    root = tmp_path / channel.name
    root.mkdir()
    monkeypatch.setattr(channel.module, channel.directory_attribute, root)
    monkeypatch.delenv(channel.update_environment, raising=False)
    return channel, root


def _write_baseline(root: Path, name: str, value: object) -> Path:
    path = root / f"{name}.json"
    path.write_text(
        json.dumps({"value": value}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_existing_baseline_read_preserves_bytes_and_directory_entries(
    baseline_channel: tuple[_BaselineChannel, Path],
) -> None:
    channel, root = baseline_channel
    path = _write_baseline(root, "score_H12", {"angles": [0.0, 359.9]})
    before_digest = _digest(path)
    before_entries = tuple(sorted(entry.name for entry in root.iterdir()))

    channel.assertion("score_H12", {"angles": [0.0, 359.9]})

    assert _digest(path) == before_digest
    assert tuple(sorted(entry.name for entry in root.iterdir())) == before_entries


def test_mismatch_never_modifies_approved_baseline(
    baseline_channel: tuple[_BaselineChannel, Path],
) -> None:
    channel, root = baseline_channel
    path = _write_baseline(root, "approved_value", {"status": "approved"})
    before = path.read_bytes()

    with pytest.raises(AssertionError, match="mismatch"):
        channel.assertion("approved_value", {"status": "candidate"})

    assert path.read_bytes() == before


def test_missing_directory_is_not_created(
    baseline_channel: tuple[_BaselineChannel, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel, root = baseline_channel
    missing = root / "does_not_exist"
    monkeypatch.setattr(channel.module, channel.directory_attribute, missing)

    with pytest.raises(AssertionError, match="read-only"):
        channel.assertion("new_candidate", 1)

    assert not missing.exists()


def test_missing_file_is_not_created(
    baseline_channel: tuple[_BaselineChannel, Path],
) -> None:
    channel, root = baseline_channel

    with pytest.raises(AssertionError, match="read-only"):
        channel.assertion("new_candidate", 1)

    assert tuple(root.iterdir()) == ()


def test_removed_update_keyword_cannot_bypass_review(
    baseline_channel: tuple[_BaselineChannel, Path],
) -> None:
    channel, root = baseline_channel
    path = _write_baseline(root, "approved_value", 1)
    before = path.read_bytes()

    with pytest.raises(TypeError, match="update"):
        channel.assertion("approved_value", 2, update=True)  # type: ignore[call-arg]

    assert path.read_bytes() == before


def test_legacy_update_environment_is_rejected_without_writing(
    baseline_channel: tuple[_BaselineChannel, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel, root = baseline_channel
    path = _write_baseline(root, "approved_value", 1)
    before = path.read_bytes()
    monkeypatch.setenv(channel.update_environment, "1")

    with pytest.raises(AssertionError, match="read-only"):
        channel.assertion("approved_value", 2)

    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "invalid_name",
    (
        "",
        ".",
        "..",
        "../escape",
        r"..\escape",
        "nested/name",
        r"nested\name",
        "/absolute",
        r"C:\absolute",
        r"\\server\share",
        "white space",
        "trailing.",
        "nul\x00byte",
        "a" * 129,
        "CON",
        "con",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM9",
        "LPT1",
        "LPT9",
    ),
)
def test_invalid_baseline_names_fail_before_filesystem_access(
    baseline_channel: tuple[_BaselineChannel, Path],
    invalid_name: str,
) -> None:
    channel, root = baseline_channel

    with pytest.raises(ValueError, match="safe slug"):
        channel.assertion(invalid_name, 1)

    assert tuple(root.iterdir()) == ()


@pytest.mark.parametrize("invalid_name", (None, 1, True, Path("name")))
def test_non_string_baseline_names_are_rejected(
    baseline_channel: tuple[_BaselineChannel, Path],
    invalid_name: object,
) -> None:
    channel, root = baseline_channel

    with pytest.raises(TypeError, match="string"):
        channel.assertion(invalid_name, 1)  # type: ignore[arg-type]

    assert tuple(root.iterdir()) == ()


def test_symbolic_link_cannot_alias_external_evidence(
    baseline_channel: tuple[_BaselineChannel, Path],
    tmp_path: Path,
) -> None:
    channel, root = baseline_channel
    outside = _write_baseline(tmp_path, "outside", 1)
    alias = root / "approved_value.json"
    try:
        alias.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symbolic links unavailable in this environment: {exc}")

    with pytest.raises(AssertionError, match="symbolic link"):
        channel.assertion("approved_value", 1)


def test_baseline_root_cannot_be_a_symbolic_link(
    baseline_channel: tuple[_BaselineChannel, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel, _root = baseline_channel
    external_root = tmp_path / f"{channel.name}_external"
    external_root.mkdir()
    _write_baseline(external_root, "approved_value", 1)
    alias_root = tmp_path / f"{channel.name}_alias"
    try:
        alias_root.symlink_to(external_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symbolic links unavailable: {exc}")
    monkeypatch.setattr(channel.module, channel.directory_attribute, alias_root)

    with pytest.raises(AssertionError, match="symbolic link|reparse|approved"):
        channel.assertion("approved_value", 1)


def test_file_replacement_between_validation_and_open_is_rejected(
    baseline_channel: tuple[_BaselineChannel, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel, root = baseline_channel
    path = _write_baseline(root, "approved_value", 1)
    replacement = _write_baseline(root, "replacement", 2)
    original_open = Path.open
    swapped = False

    def swapping_open(self: Path, *args, **kwargs):
        nonlocal swapped
        if self == path and not swapped:
            swapped = True
            os.replace(replacement, path)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", swapping_open)

    with pytest.raises(AssertionError, match="changed during secure open"):
        channel.assertion("approved_value", 1)


def test_root_replacement_during_validation_is_rejected(
    baseline_channel: tuple[_BaselineChannel, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel, root = baseline_channel
    displaced_root = root.with_name(f"{root.name}_displaced")
    replacement_root = root.with_name(f"{root.name}_replacement")
    replacement_root.mkdir()
    _write_baseline(replacement_root, "approved_value", 1)
    original_resolve = Path.resolve
    swapped = False

    def swapping_resolve(self: Path, *args, **kwargs):
        nonlocal swapped
        if self == root and not swapped:
            swapped = True
            root.rename(displaced_root)
            replacement_root.rename(root)
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", swapping_resolve)

    with pytest.raises(AssertionError, match="root changed during validation"):
        channel.assertion("approved_value", 1)


def test_json_booleans_never_compare_equal_to_numbers(
    baseline_channel: tuple[_BaselineChannel, Path],
) -> None:
    channel, root = baseline_channel

    for index, (approved, observed) in enumerate(
        ((True, 1), (False, 0), (1, True), (0, False))
    ):
        path = _write_baseline(root, f"typed_value_{index}", approved)
        before = path.read_bytes()

        with pytest.raises(AssertionError, match="mismatch"):
            channel.assertion(f"typed_value_{index}", observed)

        assert path.read_bytes() == before


@pytest.mark.parametrize(
    "document",
    (
        "{not-json",
        '{"value": 1, "value": 2}',
        '{"value": NaN}',
        '{"value": Infinity}',
        "[]",
        "{}",
        '{"value": 1, "extra": 2}',
    ),
    ids=(
        "malformed",
        "duplicate-key",
        "nan",
        "infinity",
        "non-object",
        "missing-value",
        "extra-key",
    ),
)
def test_malformed_or_ambiguous_json_is_rejected(
    baseline_channel: tuple[_BaselineChannel, Path],
    document: str,
) -> None:
    channel, root = baseline_channel
    path = root / "approved_value.json"
    path.write_text(document, encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(AssertionError, match="baseline"):
        channel.assertion("approved_value", 1)

    assert path.read_bytes() == before


def test_invalid_utf8_is_rejected_without_mutation(
    baseline_channel: tuple[_BaselineChannel, Path],
) -> None:
    channel, root = baseline_channel
    path = root / "approved_value.json"
    path.write_bytes(b'{"value": "' + bytes([0xFF]) + b'"}')
    before = path.read_bytes()

    with pytest.raises(AssertionError, match="UTF-8"):
        channel.assertion("approved_value", 1)

    assert path.read_bytes() == before


def test_directory_cannot_masquerade_as_baseline_file(
    baseline_channel: tuple[_BaselineChannel, Path],
) -> None:
    channel, root = baseline_channel
    (root / "approved_value.json").mkdir()

    with pytest.raises(AssertionError, match="regular file"):
        channel.assertion("approved_value", 1)


def _make_policy_project(pytester: pytest.Pytester) -> None:
    mini_tests = pytester.path / "tests"
    mini_tests.mkdir()
    mini_support = mini_tests / "support"
    mini_support.mkdir()
    mini_support.joinpath("__init__.py").write_text("", encoding="utf-8")
    mini_support.joinpath("network_policy.py").write_text(
        _NETWORK_POLICY_SOURCE,
        encoding="utf-8",
    )
    mini_bootstrap = mini_support / "network_bootstrap"
    mini_bootstrap.mkdir()
    mini_bootstrap.joinpath("sitecustomize.py").write_text(
        _NETWORK_BOOTSTRAP_SOURCE,
        encoding="utf-8",
    )
    mini_tests.joinpath("conftest.py").write_text(
        _HARNESS_SOURCE + _NO_KERNEL_BOOTSTRAP,
        encoding="utf-8",
    )
    mini_tests.joinpath("KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    mini_tests.joinpath("test_probe.py").write_text(
        dedent(
            """
            def test_probe():
                pass
            """
        ),
        encoding="utf-8",
    )
    pytester.path.joinpath("pytest.ini").write_text(
        _PYTEST_CONFIG,
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "update_environment",
    ("MOIRA_SNAPSHOT_UPDATE", "MOIRA_GOLDEN_UPDATE"),
)
@pytest.mark.parametrize(
    "extra_arguments",
    ((), ("-n", "2")),
    ids=("local", "xdist"),
)
def test_pytest_configuration_rejects_legacy_update_mode(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    update_environment: str,
    extra_arguments: tuple[str, ...],
) -> None:
    for name in _POLICY_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(update_environment, "1")
    _make_policy_project(pytester)

    result = pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--tb=short",
        *extra_arguments,
        timeout=30,
    )
    output = f"{result.stdout.str()}\n{result.stderr.str()}"

    assert result.ret == pytest.ExitCode.USAGE_ERROR, output
    assert update_environment in output
    assert "read-only" in output

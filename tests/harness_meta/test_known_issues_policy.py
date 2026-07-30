"""Black-box contracts for the ``KNOWN_ISSUES.yml`` pytest policy.

These tests deliberately execute Moira's test harness in isolated subprocesses.
They specify the fail-closed schema and path policy without importing private
loader helpers into the meta-test process.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest


_SOURCE_TESTS = Path(__file__).resolve().parents[1]
_MISSING = object()

_VALID_FIELDS = {
    "id": json.dumps("KI-META-001"),
    "path": json.dumps("test_probe.py"),
    "reason": json.dumps("A bounded pre-existing test defect."),
    "owner": json.dumps("validation"),
    "expires": json.dumps("2099-12-31"),
}

_PYTEST_CONFIG = """\
[pytest]
markers =
    experimental: experimental tests
    integration: integration tests
    loopback: local IPC only
    external_network: explicitly permitted external access
    network: forbidden legacy marker
    parallel: tests safe for parallel execution
    property: property-based tests
    requires_ephemeris: tests that require a planetary kernel
    serial: tests that require serial execution
    slow: slow tests
    template: template tests
    ui: UI tests
    unit: unit tests
"""


def _issue_entry(
    *,
    omit: str | None = None,
    overrides: dict[str, str] | None = None,
) -> str:
    fields = dict(_VALID_FIELDS)
    fields.update(overrides or {})
    lines: list[str] = []
    for name, value in fields.items():
        if name == omit:
            continue
        prefix = "  - " if not lines else "    "
        lines.append(f"{prefix}{name}: {value}")
    return "\n".join(lines)


def _issue_document(
    *,
    omit: str | None = None,
    overrides: dict[str, str] | None = None,
    extra_entries: tuple[str, ...] = (),
) -> str:
    entries = [_issue_entry(omit=omit, overrides=overrides), *extra_entries]
    return "known_issues:\n" + "\n".join(entries) + "\n"


def _copy_harness(test_dir: Path) -> None:
    """Copy the harness surface needed by the isolated subprocess."""

    shutil.copy2(_SOURCE_TESTS / "conftest.py", test_dir / "conftest.py")
    shutil.copytree(_SOURCE_TESTS / "support", test_dir / "support")

    # Keep the contract valid after conftest is decomposed into local plugins.
    plugin_dir = _SOURCE_TESTS / "_pytest_plugins"
    if plugin_dir.is_dir():
        shutil.copytree(plugin_dir, test_dir / "_pytest_plugins")


def _make_project(
    pytester: pytest.Pytester,
    document: str | object = _issue_document(),
) -> Path:
    test_dir = pytester.path / "tests"
    test_dir.mkdir()
    _copy_harness(test_dir)

    (pytester.path / "pytest.ini").write_text(_PYTEST_CONFIG, encoding="utf-8")
    (test_dir / "test_probe.py").write_text(
        "def test_probe():\n    assert True\n",
        encoding="utf-8",
    )
    if document is not _MISSING:
        (test_dir / "KNOWN_ISSUES.yml").write_text(
            str(document),
            encoding="utf-8",
        )
    return test_dir


def _run_policy(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    document: str | object = _issue_document(),
    *,
    strict: bool = True,
) -> tuple[Any, Path]:
    test_dir = _make_project(pytester, document)
    _set_policy_env(monkeypatch, strict=strict)
    return _invoke_policy(pytester), test_dir


def _set_policy_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    strict: bool = True,
) -> None:
    for name in (
        "MOIRA_TEST_MODE",
        "MOIRA_NO_DOWNLOAD",
        "MOIRA_STRICT_KNOWN_ISSUES",
        "MOIRA_TEST_SEED",
        "MOIRA_TEST_BUDGET_TOTAL_S",
        "MOIRA_TEST_BUDGET_CASE_S",
        "MOIRA_TEST_ARTIFACTS",
        "MOIRA_TEST_RUN_ID",
        "MOIRA_SNAPSHOT_UPDATE",
        "MOIRA_GOLDEN_UPDATE",
        "MOIRA_TEST_NETWORK_POLICY",
        "HYPOTHESIS_PROFILE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1" if strict else "0")


def _invoke_policy(pytester: pytest.Pytester) -> Any:
    return pytester.runpytest_subprocess(
        "--collect-only",
        "tests/test_probe.py",
        "-q",
        "--color=no",
        timeout=30,
    )


def _combined_output(result: Any) -> str:
    return "\n".join([*result.stdout.lines, *result.stderr.lines])


def _assert_accepted(result: Any) -> None:
    output = _combined_output(result)
    assert result.ret == pytest.ExitCode.OK, output
    assert "test_probe" in output


def _assert_usage_error(result: Any, *patterns: str) -> None:
    output = _combined_output(result)
    assert result.ret == pytest.ExitCode.USAGE_ERROR, output
    for pattern in patterns:
        assert re.search(pattern, output, re.IGNORECASE | re.DOTALL), (
            f"diagnostic did not match {pattern!r}\n{output}"
        )


@pytest.mark.parametrize(
    "document",
    (
        "known_issues: []\n",
        _issue_document(),
    ),
    ids=("empty-list", "mapping-with-list-entry"),
)
def test_canonical_root_mapping_and_list_are_accepted(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    document: str,
) -> None:
    result, _ = _run_policy(pytester, monkeypatch, document)
    _assert_accepted(result)


def test_missing_known_issues_file_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run_policy(pytester, monkeypatch, _MISSING)
    _assert_usage_error(result, r"KNOWN_ISSUES\.yml", r"missing|does not exist")


@pytest.mark.parametrize(
    ("document", "diagnostic"),
    (
        ("{}\n", r"known_issues"),
        ("misspelled_known_issues: []\n", r"known_issues"),
        ("known_issues: []\nunexpected: true\n", r"unexpected|top.level"),
        ("[]\n", r"top.level.*mapping|root.*mapping"),
        ("- id: KI-META-001\n", r"top.level.*mapping|root.*mapping"),
        ("null\n", r"top.level.*mapping|root.*mapping"),
        ("known_issues\n", r"top.level.*mapping|root.*mapping"),
        ("known_issues: {}\n", r"known_issues.*list|list.*known_issues"),
        ("known_issues: false\n", r"known_issues.*list|list.*known_issues"),
        ("known_issues: null\n", r"known_issues.*list|list.*known_issues"),
    ),
    ids=(
        "missing-key",
        "misspelled-key",
        "extra-key",
        "bare-empty-list",
        "bare-entry-list",
        "null-root",
        "scalar-root",
        "mapping-instead-of-list",
        "boolean-instead-of-list",
        "null-instead-of-list",
    ),
)
def test_noncanonical_document_shapes_are_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    document: str,
    diagnostic: str,
) -> None:
    result, _ = _run_policy(pytester, monkeypatch, document)
    _assert_usage_error(result, r"KNOWN_ISSUES\.yml", diagnostic)


@pytest.mark.parametrize(
    "entry",
    (
        "  - not-a-mapping",
        "  - 42",
        "  - true",
        "  - null",
        "  - [id, path]",
    ),
    ids=("string", "integer", "boolean", "null", "sequence"),
)
def test_every_known_issue_entry_must_be_a_mapping(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    entry: str,
) -> None:
    result, _ = _run_policy(pytester, monkeypatch, f"known_issues:\n{entry}\n")
    _assert_usage_error(
        result,
        r"KNOWN_ISSUES\.yml",
        r"entry|issue",
        r"mapping",
    )


def test_known_issue_mapping_rejects_unexpected_fields(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={"unexpected": json.dumps("not admitted")}),
    )
    _assert_usage_error(result, r"unexpected", r"field|key")


@pytest.mark.parametrize(
    ("document", "duplicate_key"),
    (
        (
            "known_issues: []\nknown_issues: []\n",
            "known_issues",
        ),
        (
            """\
known_issues:
  - id: "KI-META-FIRST"
    id: "KI-META-SECOND"
    path: "test_probe.py"
    reason: "A bounded pre-existing test defect."
    owner: "validation"
    expires: "2099-12-31"
""",
            "id",
        ),
        (
            """\
known_issues:
  - id: "KI-META-001"
    path: "other_probe.py"
    path: "test_probe.py"
    reason: "A bounded pre-existing test defect."
    owner: "validation"
    expires: "2099-12-31"
""",
            "path",
        ),
    ),
    ids=("root-key", "entry-id", "entry-path"),
)
def test_duplicate_yaml_mapping_keys_are_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    document: str,
    duplicate_key: str,
) -> None:
    result, _ = _run_policy(pytester, monkeypatch, document)
    _assert_usage_error(
        result,
        r"KNOWN_ISSUES\.yml",
        r"duplicate",
        rf"\b{re.escape(duplicate_key)}\b",
    )


@pytest.mark.parametrize(
    ("document", "diagnostic"),
    (
        (
            "known_issues: []\n#" + ("x" * (300 * 1024)) + "\n",
            r"limit|exceed|bytes",
        ),
        (
            "known_issues: " + ("[" * 600) + ("]" * 600) + "\n",
            r"depth|nest|invalid YAML",
        ),
        (
            "known_issues:\n" + ("  - x\n" * 10_050),
            r"node|limit|exceed",
        ),
        (
            "known_issues:\n"
            + _issue_entry().replace("  - id:", "  - &shared id:", 1)
            + "\n  - *shared\n",
            r"alias|permit|policy",
        ),
    ),
    ids=("byte-limit", "depth-limit", "node-limit", "alias-limit"),
)
def test_yaml_resource_limits_fail_as_usage_errors(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    document: str,
    diagnostic: str,
) -> None:
    result, _ = _run_policy(pytester, monkeypatch, document)
    _assert_usage_error(
        result,
        r"KNOWN_ISSUES\.yml",
        diagnostic,
    )


@pytest.mark.parametrize("field", tuple(_VALID_FIELDS))
def test_every_required_field_must_be_present(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(omit=field),
    )
    _assert_usage_error(result, r"KNOWN_ISSUES\.yml", re.escape(field))


@pytest.mark.parametrize("field", tuple(_VALID_FIELDS))
@pytest.mark.parametrize("blank", (json.dumps(""), json.dumps("   ")))
def test_required_string_fields_must_not_be_blank(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    blank: str,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={field: blank}),
    )
    _assert_usage_error(
        result,
        r"KNOWN_ISSUES\.yml",
        re.escape(field),
        r"blank|empty|nonempty",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("id", "42"),
        ("path", "true"),
        ("reason", "[]"),
        ("owner", "{}"),
        ("expires", "20991231"),
    ),
)
def test_required_fields_reject_non_string_scalars_and_containers(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={field: value}),
    )
    _assert_usage_error(
        result,
        r"KNOWN_ISSUES\.yml",
        re.escape(field),
        r"string|date",
    )


def test_known_issue_ids_must_be_unique(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = _issue_entry(
        overrides={
            "path": json.dumps("other_probe.py"),
            "reason": json.dumps("A second bounded defect."),
        }
    )
    document = _issue_document(extra_entries=(duplicate,))
    test_dir = _make_project(pytester, document)
    (test_dir / "other_probe.py").write_text("# target\n", encoding="utf-8")
    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_usage_error(result, r"duplicate", r"KI-META-001")


@pytest.mark.parametrize(
    "issue_id",
    (
        json.dumps("KI\nFORGED"),
        json.dumps("KI-\u001b[31mFORGED"),
        json.dumps("../KI-META-001"),
        json.dumps("K" * 65),
    ),
    ids=("newline", "ansi-control", "unsafe-punctuation", "overlong"),
)
def test_known_issue_ids_must_be_bounded_safe_slugs(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    issue_id: str,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={"id": issue_id}),
    )
    _assert_usage_error(result, r"id", r"safe|slug|control|length")


def test_policy_file_replacement_between_validation_and_open_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = pytester.path / "tests"
    test_dir.mkdir()
    _copy_harness(test_dir)
    harness_source = (test_dir / "conftest.py").read_text(encoding="utf-8")
    race_injection = """

_moira_original_path_open = Path.open
_moira_policy_swap_done = False


def _moira_swapping_path_open(self, *args, **kwargs):
    global _moira_policy_swap_done
    mode = args[0] if args else kwargs.get("mode", "r")
    if (
        self.name == "KNOWN_ISSUES.yml"
        and "b" in mode
        and not _moira_policy_swap_done
    ):
        _moira_policy_swap_done = True
        os.replace(
            self.with_name("KNOWN_ISSUES_REPLACEMENT.yml"),
            self,
        )
    return _moira_original_path_open(self, *args, **kwargs)


Path.open = _moira_swapping_path_open
"""
    (test_dir / "conftest.py").write_text(
        harness_source + race_injection,
        encoding="utf-8",
    )
    (test_dir / "KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    (test_dir / "KNOWN_ISSUES_REPLACEMENT.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    (test_dir / "test_probe.py").write_text(
        "def test_probe():\n    assert True\n",
        encoding="utf-8",
    )
    (pytester.path / "pytest.ini").write_text(_PYTEST_CONFIG, encoding="utf-8")
    _set_policy_env(monkeypatch)

    result = _invoke_policy(pytester)

    _assert_usage_error(result, r"changed during secure open")


@pytest.mark.parametrize(
    "expires",
    (
        json.dumps("2099-12-31"),
        "2099-12-31",
    ),
    ids=("quoted-string", "yaml-date"),
)
def test_exact_string_and_yaml_date_expiries_are_accepted(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    expires: str,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={"expires": expires}),
    )
    _assert_accepted(result)


@pytest.mark.parametrize(
    "expires",
    (
        json.dumps("2099-02-30"),
        json.dumps("20991231"),
        json.dumps("2099-1-1"),
        json.dumps("2099-01-01T00:00:00"),
        "2099-01-01T00:00:00",
    ),
    ids=(
        "invalid-calendar-date",
        "basic-date",
        "non-padded-date",
        "timestamp-string",
        "yaml-datetime",
    ),
)
def test_invalid_or_noncanonical_expiries_are_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    expires: str,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={"expires": expires}),
    )
    _assert_usage_error(
        result,
        r"KNOWN_ISSUES\.yml",
        r"expires",
        r"YYYY-MM-DD|date|timestamp",
    )


def test_expired_issue_is_reported_but_not_failed_without_strict_mode(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={"expires": json.dumps("2000-01-01")}),
        strict=False,
    )
    _assert_accepted(result)
    output = _combined_output(result)
    assert re.search(r"expired", output, re.IGNORECASE)
    assert "KI-META-001" in output


def test_expired_issue_fails_in_strict_mode(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={"expires": json.dumps("2000-01-01")}),
        strict=True,
    )
    _assert_usage_error(result, r"expired", r"KI-META-001")


def test_nested_contained_regular_file_is_accepted(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = _make_project(
        pytester,
        _issue_document(
            overrides={"path": json.dumps("unit/test_present.py")},
        ),
    )
    target = test_dir / "unit" / "test_present.py"
    target.parent.mkdir()
    target.write_text("# known issue target\n", encoding="utf-8")
    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_accepted(result)


@pytest.mark.parametrize(
    "path_value",
    (
        "../outside.py",
        "nested/../test_probe.py",
    ),
    ids=("escape", "contained-after-normalization"),
)
def test_parent_traversal_is_rejected_before_resolution(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    path_value: str,
) -> None:
    test_dir = _make_project(
        pytester,
        _issue_document(overrides={"path": json.dumps(path_value)}),
    )
    (pytester.path / "outside.py").write_text("# outside tests\n", encoding="utf-8")
    (test_dir / "nested").mkdir()
    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_usage_error(result, r"path", r"parent|traversal|\.\.")


def test_drive_relative_path_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = _make_project(
        pytester,
        _issue_document(overrides={"path": json.dumps("C:relative.py")}),
    )
    (test_dir / "relative.py").write_text("# drive-relative target\n", encoding="utf-8")
    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_usage_error(result, r"path", r"drive.relative|drive|relative")


def test_rooted_path_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_project(
        pytester,
        _issue_document(
            overrides={
                "path": json.dumps(
                    r"\Windows\System32\drivers\etc\hosts"
                )
            }
        ),
    )
    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_usage_error(result, r"path", r"rooted|relative|absolute")


def test_unc_path_is_rejected_without_filesystem_access(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unc_path = r"\\moira-invalid\known-issues\probe.py"
    _make_project(
        pytester,
        _issue_document(overrides={"path": json.dumps(unc_path)}),
    )
    (pytester.path / "conftest.py").write_text(
        """\
from pathlib import Path

_original_is_file = Path.is_file
_original_lstat = Path.lstat
_original_resolve = Path.resolve
_original_stat = Path.stat


def _guard(path):
    if str(path).startswith(r"\\\\moira-invalid\\known-issues"):
        raise RuntimeError("UNC filesystem access attempted")


def _guarded_is_file(path):
    _guard(path)
    return _original_is_file(path)


def _guarded_lstat(path):
    _guard(path)
    return _original_lstat(path)


def _guarded_resolve(path, *args, **kwargs):
    _guard(path)
    return _original_resolve(path, *args, **kwargs)


def _guarded_stat(path, *args, **kwargs):
    _guard(path)
    return _original_stat(path, *args, **kwargs)


Path.is_file = _guarded_is_file
Path.lstat = _guarded_lstat
Path.resolve = _guarded_resolve
Path.stat = _guarded_stat
""",
        encoding="utf-8",
    )
    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    output = _combined_output(result)
    assert "UNC filesystem access attempted" not in output, output
    _assert_usage_error(result, r"path", r"UNC|rooted|relative")


def test_nul_containing_path_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={"path": json.dumps("bad\x00path.py")}),
    )
    _assert_usage_error(result, r"path", r"NUL|null")


def test_absolute_path_is_rejected_even_when_it_names_a_contained_file(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = _make_project(pytester)
    absolute_target = test_dir / "test_probe.py"
    (test_dir / "KNOWN_ISSUES.yml").write_text(
        _issue_document(
            overrides={"path": json.dumps(str(absolute_target))},
        ),
        encoding="utf-8",
    )
    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_usage_error(result, r"path", r"relative|absolute|rooted")


def test_directory_path_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = _make_project(
        pytester,
        _issue_document(overrides={"path": json.dumps("known_issue_dir")}),
    )
    (test_dir / "known_issue_dir").mkdir()
    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_usage_error(result, r"path", r"regular file|file")


def test_symlink_escape_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = _make_project(
        pytester,
        _issue_document(overrides={"path": json.dumps("linked_probe.py")}),
    )
    outside = pytester.path / "outside_probe.py"
    outside.write_text("# outside tests\n", encoding="utf-8")
    link = test_dir / "linked_probe.py"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"file symlink creation unavailable: {exc}")

    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_usage_error(
        result,
        r"path",
        r"outside|contain|symlink|symbolic link|escape",
    )


def test_contained_symlink_is_rejected_before_resolution(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = _make_project(
        pytester,
        _issue_document(overrides={"path": json.dumps("linked_inside.py")}),
    )
    link = test_dir / "linked_inside.py"
    try:
        link.symlink_to(test_dir / "test_probe.py")
    except OSError as exc:
        pytest.skip(f"file symlink creation unavailable: {exc}")

    _set_policy_env(monkeypatch)
    result = _invoke_policy(pytester)
    _assert_usage_error(result, r"path", r"symbolic link|symlink|reparse")


def test_reparse_component_is_rejected_before_descent(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = _make_project(
        pytester,
        _issue_document(overrides={"path": json.dumps("junction/probe.py")}),
    )
    (test_dir / "junction").mkdir()
    (pytester.path / "conftest.py").write_text(
        """\
import stat
from pathlib import Path
from types import SimpleNamespace

_original_lstat = Path.lstat


def _guarded_lstat(path):
    if path.name == "junction":
        return SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=getattr(
                stat,
                "FILE_ATTRIBUTE_REPARSE_POINT",
                0x400,
            ),
            st_reparse_tag=getattr(
                stat,
                "IO_REPARSE_TAG_MOUNT_POINT",
                0xA0000003,
            ),
        )
    if path.name == "probe.py" and path.parent.name == "junction":
        raise RuntimeError("reparse point traversal attempted")
    return _original_lstat(path)


Path.lstat = _guarded_lstat
""",
        encoding="utf-8",
    )
    _set_policy_env(monkeypatch)

    result = _invoke_policy(pytester)

    output = _combined_output(result)
    assert "reparse point traversal attempted" not in output, output
    _assert_usage_error(result, r"path", r"reparse|symbolic link")


def test_non_name_surrogate_cloud_reparse_tag_is_admitted(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = _make_project(
        pytester,
        _issue_document(overrides={"path": json.dumps("cloud_file.py")}),
    )
    (test_dir / "cloud_file.py").write_text("# hydrated cloud file\n", encoding="utf-8")
    (pytester.path / "conftest.py").write_text(
        """\
import stat
from pathlib import Path
from types import SimpleNamespace

_original_lstat = Path.lstat


def _guarded_lstat(path):
    if path.name == "cloud_file.py":
        return SimpleNamespace(
            st_mode=stat.S_IFREG,
            st_file_attributes=getattr(
                stat,
                "FILE_ATTRIBUTE_REPARSE_POINT",
                0x400,
            ),
            st_reparse_tag=0x9000001A,
        )
    return _original_lstat(path)


Path.lstat = _guarded_lstat
""",
        encoding="utf-8",
    )
    _set_policy_env(monkeypatch)

    result = _invoke_policy(pytester)

    _assert_accepted(result)


def test_missing_target_path_is_rejected(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = _run_policy(
        pytester,
        monkeypatch,
        _issue_document(overrides={"path": json.dumps("missing.py")}),
    )
    _assert_usage_error(result, r"path", r"missing|does not exist|regular file")

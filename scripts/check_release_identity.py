"""Verify that Moira's release identity is internally coherent.

This is a release-engineering guard, not a runtime dependency.  It checks the
static package version, public runtime version, changelog boundary, and the two
release-facing documents before a release tag is allowed to build artifacts.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _project_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        value = tomllib.load(stream)["project"]["version"]
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ValueError(f"project.version is not a stable semantic version: {value!r}")
    return value


def _facade_version() -> str:
    source = (REPO_ROOT / "moira" / "facade.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="moira/facade.py")
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if isinstance(target, ast.Name) and target.id == "__version__":
            if isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str):
                return statement.value.value
    raise ValueError("moira/facade.py does not contain a static __version__ assignment")


def _check_release_documents(
    version: str,
    *,
    require_empty_unreleased: bool,
) -> list[str]:
    failures: list[str] = []
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if not re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.MULTILINE):
        failures.append(f"CHANGELOG.md has no dated [{version}] release heading")

    unreleased_match = re.search(
        r"^## \[Unreleased\]\s*(.*?)^## \[",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    if unreleased_match is None:
        failures.append("CHANGELOG.md does not contain an Unreleased section before a release")
    elif require_empty_unreleased and unreleased_match.group(1).strip():
        failures.append("CHANGELOG.md Unreleased section is not empty at release time")

    expected_documents = (
        REPO_ROOT / "wiki" / "03_release" / f"RELEASE_NOTES_{version}.md",
        REPO_ROOT / "wiki" / "03_release" / f"COMPATIBILITY_NOTES_{version}.md",
    )
    for path in expected_documents:
        if not path.is_file():
            failures.append(f"missing release document: {path.relative_to(REPO_ROOT)}")
            continue
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        if version not in first_line:
            failures.append(
                f"{path.relative_to(REPO_ROOT)} heading does not identify version {version}"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tag",
        help="Release tag to compare with project.version, for example v5.0.0",
    )
    args = parser.parse_args(argv)

    failures: list[str] = []
    try:
        project_version = _project_version()
        facade_version = _facade_version()
    except (KeyError, OSError, SyntaxError, ValueError) as exc:
        print(f"Release identity check failed: {exc}", file=sys.stderr)
        return 1

    if facade_version != project_version:
        failures.append(
            f"moira.__version__ source {facade_version!r} does not match "
            f"project.version {project_version!r}"
        )
    if args.tag is not None and args.tag != f"v{project_version}":
        failures.append(
            f"release tag {args.tag!r} does not match project.version "
            f"{project_version!r}"
        )
    failures.extend(
        _check_release_documents(
            project_version,
            require_empty_unreleased=args.tag is not None,
        )
    )

    if failures:
        print("Release identity check failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    tag_note = f", tag {args.tag}" if args.tag is not None else ""
    print(f"Release identity check passed for {project_version}{tag_note}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

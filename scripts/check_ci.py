"""Run the checked-in CI verification steps locally, without installing or publishing.

The workflow YAML is the command authority, so local test selections cannot drift
from CI. Uses the active project interpreter and expands test globs on Windows as
well as Linux. Jobs for other Python versions remain CI-only and are reported.
Requires the project's dev and server extras to be installed beforehand.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
from string import Template
import subprocess
import sys
import tempfile
from typing import Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ("release-hardening.yml", "release-acceptance.yml")
METADATA_ACTIONS = {"actions/checkout@v4", "actions/setup-python@v5", "actions/upload-artifact@v4"}


@dataclass(frozen=True)
class Check:
    """One workflow verification step and its literal environment."""

    label: str
    commands: tuple[tuple[str, ...], ...]
    environment: dict[str, str]


def commands_for_run(source: str, root: Path, environment: dict[str, str]) -> tuple[tuple[str, ...], ...]:
    """Translate the workflows' simple command syntax; reject unsupported shell work."""
    commands = []
    for line in source.replace("\\\n", " ").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        tokens = shlex.split(line)
        if any(token in {"&&", "||", "|", ";", ">", ">>", "<"} for token in tokens):
            raise ValueError(f"Unsupported shell syntax: {line}")
        if tokens[0] == "python":
            tokens[0] = sys.executable
        elif tokens[0] == "ruff":
            tokens[:1] = [sys.executable, "-m", "ruff"]
        else:
            raise ValueError(f"Unsupported verification command: {line}")
        expanded = []
        for token in tokens:
            token = Template(token).substitute(environment)
            if any(char in token for char in "*?["):
                matches = sorted(path.relative_to(root).as_posix() for path in root.glob(token))
                if not matches:
                    raise ValueError(f"Verification glob matched no files: {token}")
                expanded.extend(matches)
            else:
                expanded.append(token)
        commands.append(tuple(expanded))
    if not commands:
        raise ValueError("Empty verification step")
    return tuple(commands)


def load_plan(root: Path, environment: dict[str, str]) -> tuple[list[Check], list[str]]:
    """Read every verification step for this Python version from both CI workflows."""
    checks = []
    ci_only = []
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    for filename in WORKFLOWS:
        workflow = yaml.safe_load((root / ".github" / "workflows" / filename).read_text(encoding="utf-8"))
        completed = set()
        for job_id, job in workflow["jobs"].items():
            steps = job["steps"]
            versions = [str(step["with"]["python-version"]) for step in steps
                        if step.get("uses") == "actions/setup-python@v5"]
            if len(versions) != 1:
                raise ValueError(f"Expected one explicit Python version: {filename}/{job_id}")
            if versions[0] != version:
                ci_only.append(f"{filename}/{job_id} (Python {versions[0]}; active Python {version})")
                continue
            dependencies = job.get("needs", [])
            if isinstance(dependencies, str):
                dependencies = [dependencies]
            if not set(dependencies) <= completed:
                raise ValueError(f"Unverified or out-of-order dependencies: {filename}/{job_id}")
            if "if" in job or job.get("continue-on-error") or "strategy" in job:
                raise ValueError(f"Unsupported conditional/matrix job: {filename}/{job_id}")
            job_env = {**environment, **job.get("env", {})}
            for step in steps:
                if "if" in step or step.get("continue-on-error"):
                    raise ValueError(f"Unsupported conditional/optional step: {step['name']}")
                if "uses" in step:
                    if step["uses"] not in METADATA_ACTIONS:
                        raise ValueError(f"Unsupported CI action: {step['uses']}")
                    continue
                source = step["run"]
                # Environment provisioning belongs to setup, not verification.
                if source.strip() in {
                    'python -m pip install -e ".[dev,server]"',
                    'python -m pip install -e ".[dev]"',
                }:
                    continue
                step_env = {**job_env, **step.get("env", {})}
                checks.append(Check(
                    f"{filename}/{job_id}: {step['name']}",
                    commands_for_run(source, root, step_env),
                    step_env,
                ))
            completed.add(job_id)
    if not checks:
        raise ValueError(f"No verification jobs match active Python {version}")
    return checks, ci_only


def run_plan(checks: Sequence[Check], root: Path, *, list_only: bool = False) -> int:
    """Run in workflow order and propagate the first failing verification status."""
    for check in checks:
        print(f"\n{check.label}", flush=True)
        for command in check.commands:
            print(f"  {shlex.join(command)}", flush=True)
            if not list_only:
                result = subprocess.run(command, cwd=root, env=check.environment, check=False)
                if result.returncode:
                    print(f"CI verification stopped: {check.label} (exit {result.returncode}).", file=sys.stderr)
                    return result.returncode
    return 0


def check_timezone_data() -> None:
    """Fail before the long gates if this host lacks CI's IANA data resource."""
    try:
        ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            "IANA timezone data is unavailable. Install the project's dev extra "
            "(includes tzdata on Windows) before running CI verification."
        ) from exc


def main(argv: Sequence[str] | None = None) -> int:
    """Use the project environment; keep temporary candidate artifacts outside source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Show the complete plan without executing it.")
    args = parser.parse_args(argv)
    environment = os.environ.copy()
    environment.update(MOIRA_NO_DOWNLOAD="1", MOIRA_TEST_MODE="1", MOIRA_STRICT_KNOWN_ISSUES="1", PYTHONUTF8="1")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, (str(ROOT), environment.get("PYTHONPATH", ""))))
    try:
        with tempfile.TemporaryDirectory(prefix="moira-ci-") as temporary:
            environment["RUNNER_TEMP"] = temporary
            checks, ci_only = load_plan(ROOT, environment)
            for job in ci_only:
                print(f"CI-only runtime gate: {job}", flush=True)
            print("Using preinstalled project dev/server dependencies; no checkout, installation, upload, or publication.", flush=True)
            if not args.list:
                check_timezone_data()
            status = run_plan(checks, ROOT, list_only=args.list)
            if not status:
                print(f"\n{'Planned' if args.list else 'Passed'} {len(checks)} local CI verification steps.", flush=True)
                for job in ci_only:
                    print(f"Still requires CI: {job}", flush=True)
            return status
    except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
        print(f"Cannot run CI verification: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

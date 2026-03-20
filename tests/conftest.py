"""
Pytest configuration and shared fixtures for Moira tests.

Automatically loaded by pytest before running tests. Provides:
  - Moira-specific session fixtures (engine, test charts)
  - Network safety (default-deny, opt-in via @pytest.mark.network)
  - KNOWN_ISSUES.yml validation with expiry checking
  - Per-test and total runtime budgets
  - Snapshot / golden-value assertion fixtures
  - Hypothesis configuration
  - pytest-xdist parallel support
  - Optional artifact recording (ISOPGEM_TEST_ARTIFACTS=1)
  - PySide6 / Qt fixtures for UI tests
"""
from __future__ import annotations

import json
import io
import importlib
import os
import random
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest


# ---------------------------------------------------------------------------
# Directory constants
# ---------------------------------------------------------------------------

ROOT_DIR  = Path(__file__).resolve().parents[1]   # project root
TEST_DIR  = ROOT_DIR / "tests"
MOIRA_DIR = ROOT_DIR / "moira"


# ---------------------------------------------------------------------------
# KNOWN_ISSUES loader (YAML with pure-Python fallback)
# ---------------------------------------------------------------------------

def _load_known_issues(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw_text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        yaml = None  # type: ignore[assignment]

    if yaml is not None:
        data = yaml.safe_load(raw_text)
        if data is None:
            return []
        if isinstance(data, dict):
            data = data.get("known_issues", [])
        if not isinstance(data, list):
            raise RuntimeError("KNOWN_ISSUES.yml must be a list of issue dicts.")
        return [i for i in data if isinstance(i, dict)]

    # Pure-Python YAML-lite fallback
    issues: list[dict] = []
    current: dict | None = None
    for raw in raw_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            current = {}
            issues.append(current)
            line = line[2:].strip()
        if ":" in line and current is not None:
            key, value = line.split(":", 1)
            current[key.strip()] = value.strip().strip("'").strip('"')
    return issues


# ---------------------------------------------------------------------------
# Ephemeris detection
# ---------------------------------------------------------------------------

def _has_ephemeris() -> bool:
    return any([
        (ROOT_DIR  / "de441.bsp").exists(),
        (ROOT_DIR  / "kernels" / "de441.bsp").exists(),
        (ROOT_DIR  / "data"    / "de441.bsp").exists(),
    ])


# ---------------------------------------------------------------------------
# Optional coverage integration
# ---------------------------------------------------------------------------

def pytest_addoption(parser) -> None:
    group = parser.getgroup("isopgem-coverage")
    group.addoption(
        "--isopgem-cover-source",
        action="append",
        default=[],
        help="Coverage source package/path. Repeatable.",
    )
    group.addoption(
        "--isopgem-cover-include",
        action="append",
        default=[],
        help="Coverage report include pattern. Repeatable.",
    )
    group.addoption(
        "--isopgem-cover-preimport",
        action="append",
        default=[],
        help="Module to import before starting coverage. Repeatable.",
    )


def _finalize_session_coverage(config) -> None:
    cov = getattr(config, "_isop_coverage", None)
    if cov is None or getattr(config, "_isop_coverage_finalized", False):
        return
    cov.stop()
    cov.save()
    config._isop_coverage_finalized = True


# ---------------------------------------------------------------------------
# pytest_configure
# ---------------------------------------------------------------------------

def pytest_configure(config) -> None:
    # Global test-mode defaults (no network, no downloads, deterministic seed)
    if os.getenv("ISOPGEM_TEST_MODE", "0") == "1":
        os.environ.setdefault("ISOPGEM_NO_DOWNLOAD",    "1")
        os.environ.setdefault("ISOPGEM_TEST_SEED",      "1337")

    # Validate KNOWN_ISSUES.yml
    issues   = _load_known_issues(TEST_DIR / "KNOWN_ISSUES.yml")
    required = {"id", "path", "reason", "owner", "expires"}
    missing  = [i for i in issues if not required.issubset(i.keys())]
    today    = datetime.now().date()
    expired  = []
    for issue in issues:
        if issue in missing:
            continue
        try:
            exp = datetime.fromisoformat(issue["expires"]).date()
            if exp < today:
                expired.append(issue)
        except ValueError:
            missing.append(issue)

    if missing:
        raise RuntimeError(
            "KNOWN_ISSUES.yml has invalid entries; each must include "
            "id, path, reason, owner, expires (YYYY-MM-DD)."
        )
    if expired:
        if os.getenv("ISOPGEM_STRICT_KNOWN_ISSUES", "0") == "1":
            details = ", ".join(
                f"{i.get('id')} {i.get('path')} (expired {i.get('expires')})"
                for i in expired
            )
            raise RuntimeError(f"KNOWN_ISSUES.yml has expired entries: {details}")
        print("KNOWN_ISSUES.yml: expired entries detected:")
        for i in expired:
            print(f"  - {i.get('id')} {i.get('path')} (expired {i.get('expires')})")

    # Runtime budgets
    config._isop_budget_total = float(os.getenv("ISOPGEM_TEST_BUDGET_TOTAL_S", "0") or 0)
    config._isop_budget_case  = float(os.getenv("ISOPGEM_TEST_BUDGET_CASE_S",  "0") or 0)
    config._isop_run_start    = datetime.now()

    # xdist worker ID
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "")
    if worker_id:
        os.environ["ISOPGEM_WORKER_ID"] = worker_id

    run_id = os.environ.setdefault(
        "ISOPGEM_TEST_RUN_ID",
        config._isop_run_start.strftime("%Y%m%d-%H%M%S"),
    )

    if os.getenv("ISOPGEM_TEST_ARTIFACTS", "0") == "1":
        artifact_base = TEST_DIR / "artifacts" / run_id
        config._isop_artifact_dir = (
            artifact_base / f"worker_{worker_id}" if worker_id else artifact_base
        )

    # Optional coverage integration for targeted module reports.
    cover_sources = list(config.getoption("--isopgem-cover-source") or [])
    cover_includes = list(config.getoption("--isopgem-cover-include") or [])
    cover_preimports = list(config.getoption("--isopgem-cover-preimport") or [])
    if cover_sources or cover_includes or cover_preimports:
        try:
            import coverage
        except ImportError as exc:
            raise RuntimeError(
                "Coverage support requested, but coverage.py is not installed in the active environment."
            ) from exc

        for module_name in cover_preimports:
            importlib.import_module(module_name)

        config._isop_coverage = coverage.Coverage(source=cover_sources or None)
        config._isop_coverage_includes = cover_includes
        config._isop_coverage_finalized = False
        config._isop_coverage.start()


# Ignore legacy/ folder if it ever appears
collect_ignore = ["legacy"]


# ---------------------------------------------------------------------------
# pytest_collection_modifyitems — auto-markers
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(config, items):
    for item in items:
        item_path  = Path(str(item.fspath))
        dir_parts  = {p.lower() for p in item_path.parts}

        if "ui" in dir_parts or item_path.name.startswith("test_ui_") or "qtbot" in item.fixturenames:
            item.add_marker(pytest.mark.ui)
        if "integration" in dir_parts:
            item.add_marker(pytest.mark.integration)
        if "unit" in dir_parts:
            item.add_marker(pytest.mark.unit)

        # requires_ephemeris → skip when de441.bsp is absent and downloads disabled
        if item.get_closest_marker("requires_ephemeris"):
            no_dl = (
                os.getenv("ISOPGEM_NO_DOWNLOAD", "0") == "1"
                or os.getenv("ISOPGEM_TEST_MODE",  "0") == "1"
            )
            if no_dl and not _has_ephemeris():
                item.add_marker(pytest.mark.skip(reason="de441.bsp missing and downloads disabled"))

        # slow → skip when ISOPGEM_SKIP_SLOW=1
        if item.get_closest_marker("slow"):
            if os.getenv("ISOPGEM_SKIP_SLOW", "0") == "1":
                item.add_marker(pytest.mark.skip(reason="slow tests skipped (ISOPGEM_SKIP_SLOW=1)"))

        # template / experimental → opt-in
        if item.get_closest_marker("template"):
            if os.getenv("ISOPGEM_RUN_TEMPLATES", "0") != "1":
                item.add_marker(pytest.mark.skip(reason="template tests are opt-in"))
        if item.get_closest_marker("experimental"):
            if os.getenv("ISOPGEM_RUN_EXPERIMENTAL", "0") != "1":
                item.add_marker(pytest.mark.skip(reason="experimental tests are opt-in"))

        # Hypothesis auto-marker
        if not item.get_closest_marker("property") and hasattr(item, "function"):
            func = item.function
            if hasattr(func, "hypothesis") or hasattr(func, "hypothesis_explicit_examples"):
                item.add_marker(pytest.mark.property)

        # parallel / serial auto-detection
        if not item.get_closest_marker("parallel") and not item.get_closest_marker("serial"):
            serial_dirs = {"database", "singleton", "global_state", "file_lock", "mutex"}
            if dir_parts & serial_dirs:
                item.add_marker(pytest.mark.serial)
            else:
                item.add_marker(pytest.mark.parallel)


# ---------------------------------------------------------------------------
# Safety: default-deny network
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _block_network(request, monkeypatch):
    """Block all network access unless test is marked @pytest.mark.network."""
    if request.node.get_closest_marker("network"):
        yield
        return

    def _blocked(*_args, **_kwargs):
        raise RuntimeError(
            "Network access is disabled by default. "
            "Mark the test with @pytest.mark.network to enable."
        )

    monkeypatch.setattr(socket, "socket",            _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _seed_test_random():
    seed = int(os.getenv("ISOPGEM_TEST_SEED", "1337"))
    random.seed(seed)


@pytest.fixture(scope="session", autouse=True)
def configure_hypothesis():
    try:
        from hypothesis import settings, Verbosity

        test_mode   = os.getenv("ISOPGEM_TEST_MODE", "0") == "1"
        max_examples = 50 if test_mode else 100

        settings.register_profile(
            "isopgem",
            max_examples=max_examples,
            verbosity=Verbosity.quiet if test_mode else Verbosity.normal,
            database=None,
            derandomize=test_mode,
            deadline=1000,
        )
        settings.load_profile("isopgem")
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Environment isolation
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_env_vars() -> Generator[dict, None, None]:
    """Yield a dict to populate; restores the original env after each test."""
    original = dict(os.environ)
    test_vars: dict = {}
    yield test_vars
    os.environ.clear()
    os.environ.update(original)


# ---------------------------------------------------------------------------
# Moira engine fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def moira_engine():
    """Session-scoped Moira engine (loads de441.bsp once for the whole run)."""
    from moira import Moira
    return Moira()


@pytest.fixture(scope="session")
def jd_j2000() -> float:
    """Julian Day of J2000.0 epoch (2000-Jan-1.5 TT ≈ 2000-Jan-1 12:00 UTC)."""
    return 2451545.0


@pytest.fixture(scope="session")
def natal_chart(moira_engine):
    """
    A fixed test chart: 2000-01-01 12:00:00 UTC.

    Used as a stable reference for aspect, dignity, and lot tests.
    """
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    return moira_engine.chart(dt)


@pytest.fixture(scope="session")
def natal_houses(moira_engine):
    """
    House cusps for the test chart: London (51.5°N, 0.1°W), Placidus.
    """
    from moira.constants import HouseSystem
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    return moira_engine.houses(dt, latitude=51.5, longitude=-0.1, system=HouseSystem.PLACIDUS)


# ---------------------------------------------------------------------------
# Snapshot and golden-value fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def snapshot():
    """
    Snapshot assertion — compares a value against a stored JSON baseline.

    Usage::

        def test_output(snapshot):
            snapshot("my_test_name", some_result)

    Set ``ISOPGEM_SNAPSHOT_UPDATE=1`` to write/update baselines.
    """
    from tests.tools.snapshots import assert_snapshot
    return assert_snapshot


@pytest.fixture
def golden():
    """
    Golden-value assertion — compares a value against a stored golden file.

    Usage::

        def test_golden(golden):
            golden("my_golden_name", some_result)

    Set ``ISOPGEM_GOLDEN_UPDATE=1`` to write/update golden files.
    """
    from tests.tools.golden import assert_golden
    return assert_golden


# ---------------------------------------------------------------------------
# PySide6 / Qt fixtures (UI tests only)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def qapp():
    """
    Function-scoped QApplication for Qt widget tests.

    Skips automatically when PySide6 is not installed.
    Closes all top-level widgets after each test.
    """
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PySide6 not available")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    yield app

    for widget in app.topLevelWidgets():
        try:
            widget.close()
            widget.deleteLater()
        except Exception:
            pass
    app.processEvents()


@pytest.fixture(scope="session")
def qapp_session():
    """
    Session-scoped QApplication for tests that need Qt but don't create widgets.

    Use the function-scoped ``qapp`` fixture when creating widgets.
    """
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PySide6 not available")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    yield app


# ---------------------------------------------------------------------------
# Pytest hooks: per-test budget, artifacts, terminal summary
# ---------------------------------------------------------------------------

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()
    if report.when != "call":
        return

    # Per-test budget
    case_budget = float(getattr(item.config, "_isop_budget_case", 0) or 0)
    if case_budget and report.duration > case_budget:
        report.outcome  = "failed"
        report.longrepr = (
            f"Test exceeded per-test budget: {report.duration:.3f}s > {case_budget:.3f}s"
        )

    # Accumulate durations
    durations = getattr(item.config, "_isop_durations", None)
    if durations is None:
        durations = {}
        item.config._isop_durations = durations
    durations[report.nodeid] = report.duration

    # Track flakes
    if report.failed:
        flakes = getattr(item.config, "_isop_flake_counts", None)
        if flakes is None:
            flakes = {}
            item.config._isop_flake_counts = flakes
        flakes[report.nodeid] = flakes.get(report.nodeid, 0) + 1

    # Artifact recording
    artifact_dir = getattr(item.config, "_isop_artifact_dir", None)
    if artifact_dir and report.failed:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        with (artifact_dir / "failures.txt").open("a", encoding="utf-8") as f:
            f.write(f"{report.nodeid}\n{report.longrepr}\n{'-'*60}\n")


def pytest_sessionfinish(session, exitstatus):
    _finalize_session_coverage(session.config)

    # Total budget check
    budget_total = float(getattr(session.config, "_isop_budget_total", 0) or 0)
    if budget_total:
        elapsed = (datetime.now() - session.config._isop_run_start).total_seconds()
        if elapsed > budget_total:
            pytest.exit(
                f"Test session exceeded total budget: {elapsed:.1f}s > {budget_total:.1f}s",
                returncode=1,
            )

    artifact_dir = getattr(session.config, "_isop_artifact_dir", None)
    if not artifact_dir:
        return

    # Flush durations
    durations = getattr(session.config, "_isop_durations", None)
    if durations:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "durations.json").write_text(
            json.dumps(durations, indent=2, sort_keys=True), encoding="utf-8"
        )

    # Flush flakes
    flakes = getattr(session.config, "_isop_flake_counts", None)
    if flakes:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "flake_report.json").write_text(
            json.dumps({"tests": flakes, "run_id": os.getenv("ISOPGEM_TEST_RUN_ID", "")},
                       indent=2, sort_keys=True),
            encoding="utf-8",
        )

    # Merge worker artifacts (main process only)
    if not os.getenv("PYTEST_XDIST_WORKER"):
        try:
            worker_dirs = [
                d for d in artifact_dir.parent.iterdir()
                if d.is_dir() and d.name.startswith("worker_")
            ]
        except FileNotFoundError:
            worker_dirs = []
        if worker_dirs:
            try:
                from tests.tools.merge_worker_artifacts import merge_durations, merge_failures
                md = merge_durations(artifact_dir.parent)
                mf = merge_failures(artifact_dir.parent)
                if md:
                    (artifact_dir / "durations.json").write_text(
                        json.dumps(md, indent=2, sort_keys=True), encoding="utf-8"
                    )
                if mf:
                    (artifact_dir / "failures.txt").write_text(
                        "\n".join(mf) + "\n", encoding="utf-8"
                    )
            except Exception:
                pass

    # Write PowerShell rerun helper for failures
    failures_path = artifact_dir / "failures.txt"
    if not failures_path.exists():
        return
    nodeids = []
    for raw in failures_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("-"):
            continue
        if line.startswith("tests"):
            nodeids.append(line.split()[0])
    seen: set[str] = set()
    unique = [n for n in nodeids if n not in seen and not seen.add(n)]  # type: ignore[func-returns-value]
    if not unique:
        return
    invoked_cmd = "pytest " + " ".join(session.config.invocation_params.args)
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Generated: {timestamp}",
        f"# From: {invoked_cmd}",
        '$ErrorActionPreference = "Stop"',
        '$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..")',
        '$python = "py" "-3.14"',
        "$nodeids = @(",
        *[f'  "{n}"' for n in unique],
        ")",
        "& $python -m pytest @nodeids",
    ]
    (artifact_dir / "rerun.ps1").write_text("\n".join(lines) + "\n", encoding="utf-8")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print slowest tests and performance regressions."""
    _finalize_session_coverage(config)

    durations = getattr(config, "_isop_durations", None)
    if durations:
        n_slow     = 5
        sorted_dur = sorted(durations.items(), key=lambda kv: kv[1], reverse=True)
        if sorted_dur:
            terminalreporter.section("Moira: slowest tests")
            for nodeid, dur in sorted_dur[:n_slow]:
                terminalreporter.write_line(f"  {dur:7.3f}s  {nodeid}")

        baseline_path = TEST_DIR / "artifacts" / "durations_baseline.json"
        if baseline_path.exists():
            try:
                baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
            except Exception:
                baseline = None
            if baseline:
                threshold   = float(os.getenv("ISOPGEM_REGRESSION_PCT", "50")) / 100.0
                regressions = [
                    (nodeid, base, cur)
                    for nodeid, cur in durations.items()
                    if (base := baseline.get(nodeid)) and base > 0 and (cur - base) / base >= threshold
                ]
                if regressions:
                    terminalreporter.section("Moira: performance regressions")
                    for nodeid, base, cur in sorted(regressions, key=lambda r: r[2] - r[1], reverse=True):
                        pct = (cur - base) / base * 100
                        terminalreporter.write_line(f"  {nodeid}:  {base:.3f}s -> {cur:.3f}s  (+{pct:.0f}%)")

    cov = getattr(config, "_isop_coverage", None)
    includes = getattr(config, "_isop_coverage_includes", None)
    if cov is not None:
        buffer = io.StringIO()
        try:
            cov.report(include=includes or None, file=buffer)
        except Exception as exc:
            terminalreporter.section("Moira: coverage")
            terminalreporter.write_line(f"  coverage report failed: {exc}")
        else:
            terminalreporter.section("Moira: coverage")
            for line in buffer.getvalue().splitlines():
                terminalreporter.write_line(f"  {line}")


# ---------------------------------------------------------------------------
# pytest-xdist node configuration (only registered when installed)
# ---------------------------------------------------------------------------

try:
    import xdist  # noqa: F401

    def pytest_configure_node(node):
        worker_seed = os.getenv("ISOPGEM_TEST_SEED", "1337")
        node.workerinput["isopgem_test_seed"] = worker_seed
        node.workerinput["isopgem_test_mode"] = os.getenv("ISOPGEM_TEST_MODE", "0")
        node.workerinput["workerid"] = node.workerinput.get("workerid", "gw0")

except ImportError:
    pass

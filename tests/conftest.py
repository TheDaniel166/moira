"""
Pytest configuration and shared fixtures for Moira tests.

Automatically loaded by pytest before running tests. Provides:
  - Moira-specific session fixtures (engine, test charts)
  - Network safety (default-deny, opt-in via @pytest.mark.network)
  - KNOWN_ISSUES.yml validation with expiry and path checking
  - Per-test and total runtime budgets
  - Snapshot / golden-value assertion fixtures
  - Hypothesis configuration
  - pytest-xdist parallel support
  - Optional artifact recording (MOIRA_TEST_ARTIFACTS=1)
  - PySide6 / Qt fixtures for UI tests
  - Domain fixtures: reference_epoch, moira_approx, any_house_system, assert_longitude
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


def _repo_owns_module(module) -> bool:
    module_file = getattr(module, "__file__", None)
    if not module_file:
        module_path = getattr(module, "__path__", None)
        if not module_path:
            return False
        try:
            return all(Path(p).resolve().is_relative_to(ROOT_DIR) for p in module_path)
        except Exception:
            return False
    try:
        return Path(module_file).resolve().is_relative_to(ROOT_DIR)
    except Exception:
        return False


def _enforce_local_import_roots() -> None:
    root_str = str(ROOT_DIR)
    if sys.path[:1] != [root_str]:
        try:
            sys.path.remove(root_str)
        except ValueError:
            pass
        sys.path.insert(0, root_str)

    for name, module in list(sys.modules.items()):
        if not (name == "tests" or name.startswith("tests.") or name == "moira" or name.startswith("moira.")):
            continue
        if _repo_owns_module(module):
            continue
        sys.modules.pop(name, None)


_enforce_local_import_roots()




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
    group = parser.getgroup("moira-coverage")
    group.addoption(
        "--moira-cover-source",
        action="append",
        default=[],
        help="Coverage source package/path. Repeatable.",
    )
    group.addoption(
        "--moira-cover-include",
        action="append",
        default=[],
        help="Coverage report include pattern. Repeatable.",
    )
    group.addoption(
        "--moira-cover-preimport",
        action="append",
        default=[],
        help="Module to import before starting coverage. Repeatable.",
    )


def _finalize_session_coverage(config) -> None:
    cov = getattr(config, "_moira_coverage", None)
    if cov is None or getattr(config, "_moira_coverage_finalized", False):
        return
    cov.stop()
    cov.save()
    config._moira_coverage_finalized = True


# ---------------------------------------------------------------------------
# pytest_configure
# ---------------------------------------------------------------------------

def pytest_configure(config) -> None:
    # Global test-mode defaults (no network, no downloads, deterministic seed)
    if os.getenv("MOIRA_TEST_MODE", "0") == "1":
        os.environ.setdefault("MOIRA_NO_DOWNLOAD", "1")
        os.environ.setdefault("MOIRA_TEST_SEED",   "1337")

    # Validate KNOWN_ISSUES.yml
    issues   = _load_known_issues(TEST_DIR / "KNOWN_ISSUES.yml")
    required = {"id", "path", "reason", "owner", "expires"}
    missing  = [i for i in issues if not required.issubset(i.keys())]
    today    = datetime.now().date()
    expired  = []
    stale_paths = []

    for issue in issues:
        if issue in missing:
            continue
        # Expiry check
        try:
            exp = datetime.fromisoformat(issue["expires"]).date()
            if exp < today:
                expired.append(issue)
        except ValueError:
            missing.append(issue)
            continue
        # Path existence check — catch entries that reference deleted tests
        issue_path = TEST_DIR / issue["path"]
        if not issue_path.exists():
            stale_paths.append(issue)

    if missing:
        raise RuntimeError(
            "KNOWN_ISSUES.yml has invalid entries; each must include "
            "id, path, reason, owner, expires (YYYY-MM-DD)."
        )
    if stale_paths:
        details = ", ".join(
            f"{i.get('id')} ({i.get('path')})" for i in stale_paths
        )
        raise RuntimeError(
            f"KNOWN_ISSUES.yml references paths that no longer exist: {details}"
        )
    if expired:
        if os.getenv("MOIRA_STRICT_KNOWN_ISSUES", "0") == "1":
            details = ", ".join(
                f"{i.get('id')} {i.get('path')} (expired {i.get('expires')})"
                for i in expired
            )
            raise RuntimeError(f"KNOWN_ISSUES.yml has expired entries: {details}")
        print("KNOWN_ISSUES.yml: expired entries detected:")
        for i in expired:
            print(f"  - {i.get('id')} {i.get('path')} (expired {i.get('expires')})")

    # Runtime budgets
    config._moira_budget_total = float(os.getenv("MOIRA_TEST_BUDGET_TOTAL_S", "0") or 0)
    config._moira_budget_case  = float(os.getenv("MOIRA_TEST_BUDGET_CASE_S",  "0") or 0)
    config._moira_run_start    = datetime.now()

    # xdist worker ID
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "")
    if worker_id:
        os.environ["MOIRA_WORKER_ID"] = worker_id

    run_id = os.environ.setdefault(
        "MOIRA_TEST_RUN_ID",
        config._moira_run_start.strftime("%Y%m%d-%H%M%S"),
    )

    if os.getenv("MOIRA_TEST_ARTIFACTS", "0") == "1":
        artifact_base = TEST_DIR / "artifacts" / run_id
        config._moira_artifact_dir = (
            artifact_base / f"worker_{worker_id}" if worker_id else artifact_base
        )

    # Optional coverage integration for targeted module reports.
    cover_sources   = list(config.getoption("--moira-cover-source")    or [])
    cover_includes  = list(config.getoption("--moira-cover-include")   or [])
    cover_preimports = list(config.getoption("--moira-cover-preimport") or [])
    if cover_sources or cover_includes or cover_preimports:
        try:
            import coverage
        except ImportError as exc:
            raise RuntimeError(
                "Coverage support requested, but coverage.py is not installed in the active environment."
            ) from exc

        for module_name in cover_preimports:
            importlib.import_module(module_name)

        config._moira_coverage = coverage.Coverage(source=cover_sources or None)
        config._moira_coverage_includes = cover_includes
        config._moira_coverage_finalized = False
        config._moira_coverage.start()


# Ignore legacy/ folder if it ever appears
collect_ignore = ["legacy"]


# ---------------------------------------------------------------------------
# pytest_collection_modifyitems — auto-markers
# ---------------------------------------------------------------------------

# Fixtures that imply ephemeris access — auto-apply requires_ephemeris
_EPHEMERIS_FIXTURES = {"moira_engine", "natal_chart", "natal_houses"}


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

        # Auto-apply requires_ephemeris when engine fixtures are used
        if not item.get_closest_marker("requires_ephemeris"):
            if _EPHEMERIS_FIXTURES & set(item.fixturenames):
                item.add_marker(pytest.mark.requires_ephemeris)

        # requires_ephemeris → skip when de441.bsp is absent and downloads disabled
        if item.get_closest_marker("requires_ephemeris"):
            no_dl = (
                os.getenv("MOIRA_NO_DOWNLOAD", "0") == "1"
                or os.getenv("MOIRA_TEST_MODE",  "0") == "1"
            )
            if no_dl and not _has_ephemeris():
                item.add_marker(pytest.mark.skip(reason="de441.bsp missing and downloads disabled"))

        # slow → skip when MOIRA_SKIP_SLOW=1
        if item.get_closest_marker("slow"):
            if os.getenv("MOIRA_SKIP_SLOW", "0") == "1":
                item.add_marker(pytest.mark.skip(reason="slow tests skipped (MOIRA_SKIP_SLOW=1)"))

        # template / experimental → opt-in
        if item.get_closest_marker("template"):
            if os.getenv("MOIRA_RUN_TEMPLATES", "0") != "1":
                item.add_marker(pytest.mark.skip(reason="template tests are opt-in"))
        if item.get_closest_marker("experimental"):
            if os.getenv("MOIRA_RUN_EXPERIMENTAL", "0") != "1":
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
    seed = int(os.getenv("MOIRA_TEST_SEED", "1337"))
    random.seed(seed)


@pytest.fixture(scope="session", autouse=True)
def configure_hypothesis():
    try:
        from hypothesis import settings, Verbosity

        test_mode    = os.getenv("MOIRA_TEST_MODE", "0") == "1"
        max_examples = 50 if test_mode else 100

        settings.register_profile(
            "moira",
            max_examples=max_examples,
            verbosity=Verbosity.quiet if test_mode else Verbosity.normal,
            database=None,
            derandomize=test_mode,
            deadline=1000,
        )
        settings.load_profile("moira")
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
    """
    Session-scoped Moira engine (loads de441.bsp once for the whole run).

    Skips gracefully when de441.bsp is not present rather than crashing.
    Mark tests that use this fixture with @pytest.mark.requires_ephemeris,
    or rely on the auto-marker in pytest_collection_modifyitems.
    """
    if not _has_ephemeris():
        pytest.skip("de441.bsp not found — skipping ephemeris-dependent test")
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

    Set ``MOIRA_SNAPSHOT_UPDATE=1`` to write/update baselines.
    Use for regression baselines of implementation-level output.
    """
    from tools.snapshots import assert_snapshot
    return assert_snapshot


@pytest.fixture
def golden():
    """
    Golden-value assertion — compares a value against a stored golden file.

    Usage::

        def test_golden(golden):
            golden("my_golden_name", some_result)

    Set ``MOIRA_GOLDEN_UPDATE=1`` to write/update golden files.
    Use for externally validated reference values (Horizons, ERFA, SWE).
    """
    from tools.golden import assert_golden
    return assert_golden


@pytest.fixture
def ritual(snapshot, golden, request):
    """
    Generative Ritual fixture — three-phase test object.

    Separates summoning (calling the engine without presupposed output),
    witnessing (recording revealed truth as a snapshot or golden baseline),
    and covenanting (asserting structural and relational invariants on that truth).

    Methods:
        witness(name, value, *, as_golden=False) → value
            Record summoned output as canonical truth. Returns value for chaining.
            Use ``as_golden=True`` for externally validated values (Horizons, ERFA, SWE).

        cross_witness(a, b, *, keys=None, abs_tol=None, label="")
            Assert two independently summoned values agree.
            Use for symmetry checks and dual-path computation agreement.

        temporal_covenant(sequence, predicate, *, label="")
            Assert predicate(a, b) holds for every consecutive pair in a sequence.
            Use for continuity, monotonicity, and bounded-step invariants over time.

    Example — single summon::

        def test_chart_is_self_consistent(moira_engine, jd_j2000, ritual, assert_longitude):
            chart = ritual.witness("chart_j2000", moira_engine.chart(jd_j2000))
            for body, pos in chart.positions.items():
                assert_longitude(pos.longitude, label=body)

    Example — cross-witness::

        def test_aspect_symmetry(moira_engine, jd_j2000, ritual):
            pos = moira_engine.positions(jd_j2000)
            ab = moira_engine.aspect(pos["Sun"], pos["Moon"])
            ba = moira_engine.aspect(pos["Moon"], pos["Sun"])
            ritual.witness("sun_moon_aspect_j2000", ab)
            ritual.cross_witness(ab, ba, keys=["orb", "angle"], label="aspect symmetry")

    Example — temporal covenant::

        def test_sun_moves_forward(moira_engine, ritual):
            jds = [2451545.0 + i for i in range(30)]
            lons = [moira_engine.planet(jd, "Sun").longitude for jd in jds]
            ritual.witness("sun_longitude_30day", lons)
            ritual.temporal_covenant(
                lons,
                lambda a, b: (b - a) % 360 < 2.0,
                label="Sun moves less than 2 degrees per day",
            )
    """
    from tools.ritual import Ritual
    return Ritual(snapshot, golden, request.node.nodeid)


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(
    params=[
        (2451545.0,  "J2000.0"),       # 2000-Jan-1 12:00 TT
        (2415020.0,  "B1900.0"),       # 1900-Jan-0.5 ET
        (2299160.5,  "Julian_reform"), # 1582-Oct-15, first Gregorian day
        (1721425.5,  "Julian_epoch"),  # 0001-Jan-1 proleptic Julian
        (2816787.5,  "J2100.0"),       # 2100-Jan-1 (future)
    ],
    ids=lambda p: p[1],
)
def reference_epoch(request) -> tuple[float, str]:
    """
    Parametrized fixture over well-known Julian Dates.

    Yields ``(jd, label)`` tuples so a single test sweeps multiple epochs
    without repetition. Use for invariant checks (longitude range, cusp count,
    etc.) that must hold across the full supported date range.

    Example::

        def test_cusps_always_twelve(reference_epoch, moira_engine):
            jd, label = reference_epoch
            result = moira_engine.houses(jd, latitude=51.5, longitude=0.0)
            assert len(result.cusps) == 12, f"Failed at epoch {label}"
    """
    return request.param


@pytest.fixture
def moira_approx():
    """
    Domain-aware approximate comparison fixture.

    Returns a callable ``moira_approx(value, kind="longitude")`` that wraps
    ``pytest.approx`` with tolerances appropriate for each computation kind,
    so tests don't scatter magic tolerance numbers.

    Kinds and tolerances:
        longitude  — 1e-6 degrees  (~3.6 mas, sub-arcsecond)
        distance   — 1e-9 AU       (sub-kilometre)
        angle      — 1e-4 degrees  (fine enough for aspects/orbs)
        time       — 1e-8 days     (~1 ms)
        ratio      — 1e-9          (dimensionless fractions)

    Example::

        def test_sun_longitude(moira_engine, jd_j2000, moira_approx):
            pos = moira_engine.planet(jd_j2000, "Sun")
            assert pos.longitude == moira_approx(280.459, kind="longitude")
    """
    _tolerances = {
        "longitude": 1e-6,
        "distance":  1e-9,
        "angle":     1e-4,
        "time":      1e-8,
        "ratio":     1e-9,
    }

    def _approx(value, kind: str = "longitude"):
        tol = _tolerances.get(kind)
        if tol is None:
            raise ValueError(
                f"Unknown moira_approx kind {kind!r}. "
                f"Valid kinds: {list(_tolerances)}"
            )
        return pytest.approx(value, abs=tol)

    return _approx


@pytest.fixture(
    params=None,  # populated lazily from HouseSystem at collection time
    ids=str,
)
def any_house_system(request):
    """
    Parametrized fixture over every valid HouseSystem value.

    Use for invariant sweeps that must hold across all house systems, e.g.
    "always produces exactly 12 cusps" or "cusps are always in [0, 360)".
    Skips automatically if moira.constants.HouseSystem cannot be imported.

    Example::

        def test_cusp_count_all_systems(any_house_system, jd_j2000):
            from moira.houses import calculate_houses
            result = calculate_houses(jd_j2000, 51.5, 0.0, any_house_system)
            assert len(result.cusps) == 12
    """
    return request.param


def pytest_generate_tests(metafunc):
    """Populate any_house_system params lazily so import errors skip cleanly."""
    if "any_house_system" in metafunc.fixturenames:
        try:
            from moira.constants import HouseSystem
            systems = list(HouseSystem)
        except Exception:
            systems = []
        metafunc.parametrize("any_house_system", systems, ids=str)


@pytest.fixture
def assert_longitude():
    """
    Assert that a value is a valid ecliptic longitude: in [0, 360).

    The single most common structural invariant in this codebase. Use instead
    of writing ``assert 0 <= lon < 360`` in every test.

    Example::

        def test_cusp_range(natal_houses, assert_longitude):
            for cusp in natal_houses.cusps:
                assert_longitude(cusp)
    """
    def _check(value: float, label: str = "longitude") -> None:
        assert 0.0 <= value < 360.0, (
            f"{label} {value!r} is outside [0, 360)"
        )
    return _check


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
    case_budget = float(getattr(item.config, "_moira_budget_case", 0) or 0)
    if case_budget and report.duration > case_budget:
        report.outcome  = "failed"
        report.longrepr = (
            f"Test exceeded per-test budget: {report.duration:.3f}s > {case_budget:.3f}s"
        )

    # Accumulate durations
    durations = getattr(item.config, "_moira_durations", None)
    if durations is None:
        durations = {}
        item.config._moira_durations = durations
    durations[report.nodeid] = report.duration

    # Track flakes
    if report.failed:
        flakes = getattr(item.config, "_moira_flake_counts", None)
        if flakes is None:
            flakes = {}
            item.config._moira_flake_counts = flakes
        flakes[report.nodeid] = flakes.get(report.nodeid, 0) + 1

    # Artifact recording
    artifact_dir = getattr(item.config, "_moira_artifact_dir", None)
    if artifact_dir and report.failed:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        with (artifact_dir / "failures.txt").open("a", encoding="utf-8") as f:
            f.write(f"{report.nodeid}\n{report.longrepr}\n{'-'*60}\n")


def pytest_sessionfinish(session, exitstatus):
    _finalize_session_coverage(session.config)

    # Total budget check
    budget_total = float(getattr(session.config, "_moira_budget_total", 0) or 0)
    if budget_total:
        elapsed = (datetime.now() - session.config._moira_run_start).total_seconds()
        if elapsed > budget_total:
            pytest.exit(
                f"Test session exceeded total budget: {elapsed:.1f}s > {budget_total:.1f}s",
                returncode=1,
            )

    artifact_dir = getattr(session.config, "_moira_artifact_dir", None)
    if not artifact_dir:
        return

    # Flush durations
    durations = getattr(session.config, "_moira_durations", None)
    if durations:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "durations.json").write_text(
            json.dumps(durations, indent=2, sort_keys=True), encoding="utf-8"
        )

    # Flush flakes
    flakes = getattr(session.config, "_moira_flake_counts", None)
    if flakes:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "flake_report.json").write_text(
            json.dumps({"tests": flakes, "run_id": os.getenv("MOIRA_TEST_RUN_ID", "")},
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
                from tools.merge_worker_artifacts import merge_durations, merge_failures
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

    durations = getattr(config, "_moira_durations", None)
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
                threshold   = float(os.getenv("MOIRA_REGRESSION_PCT", "50")) / 100.0
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

    cov = getattr(config, "_moira_coverage", None)
    includes = getattr(config, "_moira_coverage_includes", None)
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

    @pytest.hookimpl(optionalhook=True)
    def pytest_configure_node(node):
        worker_seed = os.getenv("MOIRA_TEST_SEED", "1337")
        node.workerinput["moira_test_seed"] = worker_seed
        node.workerinput["moira_test_mode"] = os.getenv("MOIRA_TEST_MODE", "0")
        node.workerinput["workerid"] = node.workerinput.get("workerid", "gw0")

except ImportError:
    pass

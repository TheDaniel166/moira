"""
Pytest configuration and shared fixtures for Moira tests.

Automatically loaded by pytest before running tests. Provides:
  - Moira-specific session fixtures (engine, test charts)
  - Network safety (deny by default; explicit loopback/external capabilities)
  - KNOWN_ISSUES.yml validation with expiry and path checking
  - Per-test and total runtime budgets
  - Snapshot / golden-value assertion fixtures
  - Hypothesis configuration
  - pytest-xdist parallel support
  - Optional artifact recording (MOIRA_TEST_ARTIFACTS=1)
  - Domain fixtures: moira_approx and assert_longitude
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import pytest

from _pytest_plugins import (
    register_required_plugins,
    verify_required_plugins,
)
from _pytest_plugins._state import (
    ROOT_DIR,
)
from _pytest_plugins.network_policy import (
    register_options as _register_network_options,
)
from _pytest_plugins.resources import (
    _enforce_planetary_resource_receipt,
    _enforce_small_body_resource_receipt,
    _planetary_receipt_for_item,
    _planetary_requirement_for_item,
    _record_planetary_live_failure,
    _record_small_body_resource_receipt,
    _resource_policy_module,
    _session_planetary_receipt,
    _small_body_resource_policy_module,
)


# ---------------------------------------------------------------------------
# Directory constants
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Typed harness policy
# ---------------------------------------------------------------------------



# Windows IsReparseTagNameSurrogate() tests this bit in a reparse tag.


# ---------------------------------------------------------------------------
# KNOWN_ISSUES loader
# ---------------------------------------------------------------------------


if (
    os.environ.get("_MOIRA_ROOT_HARNESS_BOOTSTRAP")
    != str(ROOT_DIR)
):

    def pytest_addoption(parser) -> None:
        """Standalone pytester projects have no repository-root bridge."""

        _register_network_options(parser)


# ---------------------------------------------------------------------------
# Planetary-resource policy
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# pytest_configure
# ---------------------------------------------------------------------------


@pytest.hookimpl(
    tryfirst=True,
    specname="pytest_configure",
)
def pytest_configure_required_plugins(config) -> None:
    register_required_plugins(config)
    verify_required_plugins(config)


# Ignore legacy/ folder if it ever appears
collect_ignore = ["legacy"]


# ---------------------------------------------------------------------------
# pytest_collection_modifyitems — auto-markers
# ---------------------------------------------------------------------------

# Fixtures that imply planetary-resource access auto-apply the historical
# content-derived DE441 contract unless the test declares a narrower one.


@pytest.hookimpl(
    trylast=True,
    specname="pytest_collection_finish",
)
def pytest_collection_finish_required_plugin_guard(session):
    verify_required_plugins(session.config)


# ---------------------------------------------------------------------------
# Explicit planetary-resource fixtures
# ---------------------------------------------------------------------------



@pytest.fixture(autouse=True)
def _activate_declared_planetary_resource(request):
    """Admit and context-route only explicitly resource-marked test items."""

    requirement = _planetary_requirement_for_item(request.node)
    if requirement is None:
        yield
        return

    receipt = _planetary_receipt_for_item(request.node)
    _enforce_planetary_resource_receipt(receipt)

    # This fixture is the sole admitted global-state boundary.  Its consumer
    # must observe the real global fallback rather than a ContextVar override.
    if "configured_global_reader" in request.fixturenames:
        yield
        return

    handle = request.getfixturevalue("_planetary_reader_handle")
    from moira.spk_reader import use_reader_override

    with use_reader_override(handle):
        yield


@pytest.fixture
def planetary_kernel_receipt(request):
    """Return the selected item's immutable run receipt."""

    receipt = _planetary_receipt_for_item(request.node)
    _enforce_planetary_resource_receipt(receipt)
    return receipt


@pytest.fixture(scope="session")
def planetary_kernel_path(request) -> Path:
    """Return a path only after its opened content has been admitted."""

    receipt = _session_planetary_receipt(
        request,
        nodeid="<session:planetary-kernel-path>",
    )
    if receipt.candidate is None:
        raise AssertionError("admitted planetary receipt has no candidate")
    return receipt.candidate.path


@pytest.fixture(scope="session")
def _planetary_reader_handle(request, planetary_kernel_path):
    """Own the stable session reader without installing ambient global state."""

    policy = _resource_policy_module()
    receipt = _session_planetary_receipt(
        request,
        nodeid="<session:planetary-reader>",
    )
    from moira.spk_reader import SpkReader

    handle = None
    try:
        handle = SpkReader(planetary_kernel_path)
        policy.verify_reader_matches_receipt(handle, receipt)
    except Exception as exc:
        if handle is not None:
            try:
                handle.close()
            except Exception as close_exc:
                _record_planetary_live_failure(
                    request.config,
                    nodeid="<session:planetary-reader>",
                    stage="failed-acquisition-close",
                    admitted_receipt=receipt,
                    exc=close_exc,
                )
        _record_planetary_live_failure(
            request.config,
            nodeid="<session:planetary-reader>",
            stage="acquisition",
            admitted_receipt=receipt,
            exc=exc,
        )
        raise
    try:
        yield handle
    finally:
        try:
            handle.close()
        except Exception as exc:
            _record_planetary_live_failure(
                request.config,
                nodeid="<session:planetary-reader>",
                stage="teardown",
                admitted_receipt=receipt,
                exc=exc,
            )
            raise


@pytest.fixture(scope="session")
def planetary_reader(_planetary_reader_handle):
    """Session-owned reader for explicit argument passing."""

    return _planetary_reader_handle


@pytest.fixture(scope="session")
def reader(planetary_reader):
    """Compatibility alias for the explicit planetary reader."""

    return planetary_reader


@pytest.fixture(scope="session")
def small_body_reader_pool(request, planetary_kernel_path):
    """Own the explicit planetary-plus-sovereign-small-body reader pool.

    The planetary path has already passed the planetary resource receipt.
    Supplemental manifests are a separate product admission boundary: this
    fixture discovers them in repository-defined order, opens every listed
    reader, and skips when no sovereign small-body reader is installed.  It
    does not widen the planetary receipt into a supplemental-content claim.
    """

    from moira._kernel_paths import find_all_small_body_manifests
    from moira import _spk_body_kernel
    from moira.small_body_catalog_release import verify_release
    from moira.spk_reader import KernelPool, SpkReader

    planetary_policy = _resource_policy_module()
    supplemental_policy = _small_body_resource_policy_module()
    planetary_receipt = _session_planetary_receipt(
        request,
        nodeid="<session:small-body-reader-pool-primary>",
    )
    receipt_nodeid = "<session:small-body-reader-pool>"
    primary_reader = None
    supplemental_admission = None
    supplemental_readers = ()
    pool = None
    primary_close_failure = None
    supplemental_close_failures = ()
    supplemental_pool_failure = None
    try:
        try:
            primary_reader = SpkReader(planetary_kernel_path)
            planetary_policy.verify_reader_matches_receipt(
                primary_reader,
                planetary_receipt,
            )
        except Exception as exc:
            _record_planetary_live_failure(
                request.config,
                nodeid="<session:small-body-reader-pool-primary>",
                stage="acquisition",
                admitted_receipt=planetary_receipt,
                exc=exc,
            )
            raise
        try:
            manifest_paths = find_all_small_body_manifests()
        except Exception as exc:
            failure = supplemental_policy.SmallBodyResourceReceipt(
                name="supplemental-small-body-pool",
                disposition=(
                    supplemental_policy.SmallBodyResourceDisposition.FAILURE
                ),
                requirement=(
                    supplemental_policy.SmallBodyManifestRequirement()
                ),
                capabilities=(),
                reason=f"ambient manifest discovery failed: {exc}",
                failure_type=type(exc).__name__,
                terminal=True,
            )
            _record_small_body_resource_receipt(
                request.config,
                receipt_nodeid,
                failure,
            )
            _enforce_small_body_resource_receipt(failure)

        native_segment_types = set()
        if _spk_body_kernel._HAS_NATIVE_SEGMENTS:
            native_segment_types.update((2, 3))
        if _spk_body_kernel._HAS_NATIVE_TYPE13:
            native_segment_types.add(13)
        supplemental_admission = (
            supplemental_policy.admit_small_body_manifests(
                manifest_paths,
                verify_release=verify_release,
                reader_factory=_spk_body_kernel.SmallBodyKernel,
                native_catalog_available=bool(
                    _spk_body_kernel._HAS_NATIVE_DAF
                ),
                native_segment_types=native_segment_types,
            )
        )
        _record_small_body_resource_receipt(
            request.config,
            receipt_nodeid,
            supplemental_admission.receipt,
        )
        _enforce_small_body_resource_receipt(
            supplemental_admission.receipt
        )
        supplemental_readers = supplemental_admission.readers
        try:
            pool = KernelPool(
                (primary_reader, *supplemental_readers)
            )
        except Exception as exc:
            supplemental_pool_failure = exc
            raise
        yield pool
    finally:
        if supplemental_readers:
            supplemental_close_failures = (
                supplemental_policy.close_small_body_readers(
                    supplemental_readers
                )
            )
        if (
            supplemental_admission is not None
            and supplemental_admission.receipt.disposition
            is supplemental_policy.SmallBodyResourceDisposition.RUN
            and not supplemental_admission.receipt.terminal
        ):
            if supplemental_pool_failure is not None:
                terminal_receipt = (
                    supplemental_policy.fail_small_body_live_receipt(
                        supplemental_admission.receipt,
                        stage="KernelPool construction",
                        exc=supplemental_pool_failure,
                        close_failures=supplemental_close_failures,
                    )
                )
            else:
                terminal_receipt = (
                    supplemental_policy.terminalize_small_body_receipt(
                        supplemental_admission.receipt,
                        close_failures=supplemental_close_failures,
                    )
                )
            _record_small_body_resource_receipt(
                request.config,
                receipt_nodeid,
                terminal_receipt,
            )
        if primary_reader is not None:
            try:
                primary_reader.close()
            except Exception as exc:
                primary_close_failure = (
                    f"{type(exc).__name__}: {exc}"
                )
                _record_planetary_live_failure(
                    request.config,
                    nodeid="<session:small-body-reader-pool-primary>",
                    stage="teardown",
                    admitted_receipt=planetary_receipt,
                    exc=exc,
                )
        teardown_failures = [
            *supplemental_close_failures,
            *(
                [f"primary reader {primary_close_failure}"]
                if primary_close_failure is not None
                else []
            ),
        ]
        if teardown_failures:
            raise RuntimeError(
                "small_body_reader_pool teardown failed: "
                + "; ".join(teardown_failures)
            )


@pytest.fixture
def small_body_reader_context(small_body_reader_pool):
    """Context-route the separately admitted small-body pool for one test."""

    from moira.spk_reader import use_reader_override

    with use_reader_override(small_body_reader_pool):
        yield small_body_reader_pool


@pytest.fixture
def configured_global_reader(request, planetary_kernel_path):
    """Configure and erase the legacy singleton for its explicit consumer."""

    from unittest.mock import patch

    from moira import spk_reader

    policy = _resource_policy_module()
    receipt = _session_planetary_receipt(
        request,
        nodeid="<fixture:configured-global-reader>",
    )
    nodeid = getattr(request.node, "nodeid", "<configured-global-reader>")
    owns_global_reader = False
    try:
        if spk_reader._reader is not None or spk_reader._reader_path is not None:
            raise policy.ResourceContractError(
                "configured_global_reader refuses to hot-swap pre-existing "
                "global reader state"
            )
        # This fixture is deliberately primary-only. Supplemental manifests
        # have their own explicit pool fixture and must never be admitted
        # through set_kernel_path()'s best-effort discovery side channel.
        with patch(
            "moira._kernel_paths.find_all_small_body_manifests",
            return_value=(),
            create=True,
        ):
            spk_reader.set_kernel_path(planetary_kernel_path)
        owns_global_reader = (
            spk_reader._reader is not None
            or spk_reader._reader_path is not None
        )
        if spk_reader._reader is None:
            raise policy.ResourceContractError(
                "configured_global_reader did not establish global state"
            )
        policy.verify_reader_matches_receipt(spk_reader._reader, receipt)
    except Exception as exc:
        _record_planetary_live_failure(
            request.config,
            nodeid=nodeid,
            stage="configured-global-reader-acquisition",
            admitted_receipt=receipt,
            exc=exc,
        )
        if owns_global_reader:
            try:
                spk_reader.reset_singleton()
            except Exception as close_exc:
                _record_planetary_live_failure(
                    request.config,
                    nodeid=nodeid,
                    stage="configured-global-reader-failed-acquisition-close",
                    admitted_receipt=receipt,
                    exc=close_exc,
                )
        raise
    try:
        yield spk_reader._reader
    finally:
        try:
            spk_reader.reset_singleton()
        except Exception as exc:
            _record_planetary_live_failure(
                request.config,
                nodeid=nodeid,
                stage="configured-global-reader-teardown",
                admitted_receipt=receipt,
                exc=exc,
            )
            raise


# ---------------------------------------------------------------------------
# Moira engine fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def moira_engine(request, planetary_kernel_path):
    """Session-owned Moira facade with explicit reader teardown."""

    from unittest.mock import patch

    policy = _resource_policy_module()
    receipt = _session_planetary_receipt(
        request,
        nodeid="<session:moira-engine>",
    )
    from moira import Moira

    engine = None
    try:
        # Keep the ordinary engine fixture primary-only. Supplemental kernels
        # are admitted through small_body_reader_pool, never hidden facade
        # discovery that can silently swallow malformed-manifest failures.
        with patch(
            "moira._kernel_paths.find_all_small_body_manifests",
            return_value=(),
            create=True,
        ):
            engine = Moira(kernel_path=str(planetary_kernel_path))
        if engine._supplemental_kernel_init_error is not None:
            raise engine._supplemental_kernel_init_error
        owned_reader = engine._reader_obj
        if owned_reader is None:
            raise policy.ResourceContractError(
                "moira_engine could not open its admitted planetary resource"
            )
        primary_reader_getter = getattr(
            owned_reader,
            "_primary_planetary_reader",
            None,
        )
        primary_reader = (
            primary_reader_getter()
            if callable(primary_reader_getter)
            else owned_reader
        )
        policy.verify_reader_matches_receipt(primary_reader, receipt)
    except Exception as exc:
        _record_planetary_live_failure(
            request.config,
            nodeid="<session:moira-engine>",
            stage="acquisition",
            admitted_receipt=receipt,
            exc=exc,
        )
        if engine is not None and engine._reader_obj is not None:
            try:
                engine._reader_obj.close()
            except Exception as close_exc:
                _record_planetary_live_failure(
                    request.config,
                    nodeid="<session:moira-engine>",
                    stage="failed-acquisition-close",
                    admitted_receipt=receipt,
                    exc=close_exc,
                )
            finally:
                engine._reader_obj = None
        raise
    try:
        yield engine
    finally:
        if engine._reader_obj is not None:
            try:
                engine._reader_obj.close()
            except Exception as exc:
                _record_planetary_live_failure(
                    request.config,
                    nodeid="<session:moira-engine>",
                    stage="teardown",
                    admitted_receipt=receipt,
                    exc=exc,
                )
                raise
            finally:
                engine._reader_obj = None


@pytest.fixture(scope="session")
def eclipse_calculator(reader):
    """Session-scoped EclipseCalculator with an explicit reader."""

    from moira.eclipse import EclipseCalculator

    return EclipseCalculator(reader=reader)


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
    Read-only comparison against an approved JSON regression witness.

    Usage::

        def test_output(snapshot):
            snapshot("my_test_name", some_result)

    Ordinary pytest cannot create or update snapshots. Candidate generation and
    reviewed promotion are separate protected-evidence operations. A snapshot
    detects implementation drift; it does not establish external truth.
    """
    from tools.snapshots import assert_snapshot
    return assert_snapshot


@pytest.fixture
def golden():
    """
    Read-only comparison against an approved golden storage record.

    Usage::

        def test_golden(golden):
            golden("my_golden_name", some_result)

    Ordinary pytest cannot create or update goldens. A golden file is only a
    storage channel; its authority comes from adjacent provenance, declared
    product semantics, and the producing validation record.
    """
    from tools.golden import assert_golden
    return assert_golden


@pytest.fixture
def ritual(snapshot, golden, request):
    """
    Generative Ritual fixture — three-phase test object.

    Separates summoning (calling the engine), witnessing (comparing a serialized
    observation with approved regression or provenance-governed storage), and
    covenanting (asserting structural and relational invariants). Witnessing
    alone does not establish scientific truth.

    Methods:
        witness(name, value, *, as_golden=False) → value
            Compare summoned output with approved storage. Returns value for
            chaining. ``as_golden=True`` selects the golden storage channel; it
            does not itself confer external authority.

        cross_witness(a, b, *, keys=None, abs_tol=None, label="")
            Assert two independently summoned values agree.
            Use for parity or invariant evidence, not external truth.

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

@pytest.fixture
def moira_approx():
    """
    Legacy approximate comparison fixture pending product-by-product migration.

    This wrapper is not unit-safe and treats longitude linearly. New tests must
    use named contracts from ``support.numeric_assertions``. Existing consumers
    remain until each product's units, semantics, and tolerance basis are
    reviewed; do not mechanically translate them.

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
    from support.numeric_assertions import assert_canonical_longitude_degrees

    def _check(value: float, label: str = "longitude") -> None:
        assert_canonical_longitude_degrees(value, label=label)

    return _check


# This file intentionally ends with tests-scoped fixture exports. Global
# policy hooks live in the required ``_pytest_plugins`` manifest.

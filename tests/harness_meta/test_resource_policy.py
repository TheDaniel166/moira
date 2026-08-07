"""Adversarial contracts for typed planetary-kernel resource admission."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import math
import os
from pathlib import Path
import shutil
from threading import Condition
from textwrap import dedent
from types import SimpleNamespace

import pytest

from support.resource_policy import (
    KernelRoute,
    KernelSegmentCapability,
    PlanetaryKernelCandidate,
    PlanetaryKernelCapability,
    PlanetaryKernelFingerprint,
    PlanetaryKernelReceipt,
    PlanetaryKernelRequirement,
    PlanetaryResourceResolver,
    ResourceContractError,
    ResourceDisposition,
    capability_from_reader,
    capability_mismatches,
    discover_planetary_kernel_candidate,
    verify_reader_matches_receipt,
)


pytestmark = pytest.mark.parallel(reason="isolated_resources")


_TESTS_DIR = Path(__file__).resolve().parents[1]
_HARNESS_SOURCE = (_TESTS_DIR / "conftest.py").read_text(encoding="utf-8")
_RESOURCE_POLICY_SOURCE = (
    _TESTS_DIR / "support" / "resource_policy.py"
).read_text(encoding="utf-8")
_NETWORK_POLICY_SOURCE = (
    _TESTS_DIR / "support" / "network_policy.py"
).read_text(encoding="utf-8")
_NETWORK_BOOTSTRAP_SOURCE = (
    _TESTS_DIR / "support" / "network_bootstrap" / "sitecustomize.py"
).read_text(encoding="utf-8")
_PYTEST_CONFIG = """\
[pytest]
addopts = -ra
strict_config = true
strict_markers = true
markers =
    requires_ephemeris: typed planetary-kernel capability
    loopback: local IPC only
    external_network: live external access
    network: forbidden legacy marker
    serial: isolated global-state test
    parallel: parallel-safe test
    property: property-based test
"""
_FAKE_SPK_READER = """\
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
import os
from pathlib import Path
from types import SimpleNamespace


_reader = None
_reader_path = None
_override = ContextVar("fake_reader_override", default=None)
_open_count = 0


def _append_log(kind):
    log_path = os.environ.get("FAKE_KERNEL_LOG")
    if log_path:
        with Path(log_path).open("a", encoding="utf-8") as stream:
            stream.write(kind + "\\n")


class SpkReader:
    def __init__(self, path):
        global _open_count
        _open_count += 1
        self._path = Path(path)
        self._closed = False
        _append_log("open:" + self._path.name)
        fail_after = os.environ.get("FAKE_LIVE_OPEN_FAIL_AFTER")
        if fail_after is not None and _open_count > int(fail_after):
            raise OSError("synthetic live acquisition failure")
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        if payload.get("corrupt"):
            raise ValueError("synthetic corrupt DAF/SPK")
        identity = payload.get("identity", "DE441")
        summary = payload.get("summary", "DE-0441LE-0441")
        self._kernel_identity = SimpleNamespace(
            summary_label=summary,
            planetary_ephemeris=identity,
            lunar_ephemeris=payload.get("lunar_identity", "LE441"),
        )
        segments = []
        for item in payload.get(
            "segments",
            [{
                "target": 10,
                "center": 0,
                "frame": 1,
                "data_type": 2,
                "start_jd": 1000.0,
                "end_jd": 2000.0,
            }],
        ):
            segments.append(SimpleNamespace(**item))
        self._kernel = SimpleNamespace(
            catalog={"native": payload.get("native", True)},
            segments=segments,
        )

    @property
    def path(self):
        return self._path

    def close(self):
        if not self._closed:
            self._closed = True
            _append_log("close:" + self._path.name)


def _planetary_kernel_native_supported(catalog):
    return bool(catalog.get("native"))


@contextmanager
def use_reader_override(reader):
    token = _override.set(reader)
    try:
        yield
    finally:
        _override.reset(token)


def get_reader(path=None):
    global _reader
    active = _override.get()
    if active is not None:
        return active
    if _reader is None and path is not None:
        set_kernel_path(path)
    if _reader is None:
        raise RuntimeError("no fake reader configured")
    return _reader


def set_kernel_path(path):
    global _reader, _reader_path
    if _reader is not None:
        raise RuntimeError("fake global reader already configured")
    _reader = SpkReader(path)
    _reader_path = Path(path)


def reset_singleton():
    global _reader, _reader_path
    if _reader is not None:
        _reader.close()
    _reader = None
    _reader_path = None
"""
_FAKE_KERNEL_PATHS = """\
import os
from pathlib import Path


def find_planetary_kernel():
    if os.environ.get("FAKE_DISCOVERY_ERROR") == "1":
        raise OSError("synthetic discovery failure")
    value = os.environ.get("FAKE_DISCOVERED_KERNEL")
    return None if value is None else Path(value)
"""


def _make_harness_project(
    pytester: pytest.Pytester,
    source: str,
) -> None:
    mini_tests = pytester.path / "tests"
    mini_tests.mkdir()
    support = mini_tests / "support"
    support.mkdir()
    support.joinpath("__init__.py").write_text("", encoding="utf-8")
    support.joinpath("resource_policy.py").write_text(
        _RESOURCE_POLICY_SOURCE,
        encoding="utf-8",
    )
    support.joinpath("network_policy.py").write_text(
        _NETWORK_POLICY_SOURCE,
        encoding="utf-8",
    )
    bootstrap = support / "network_bootstrap"
    bootstrap.mkdir()
    bootstrap.joinpath("sitecustomize.py").write_text(
        _NETWORK_BOOTSTRAP_SOURCE,
        encoding="utf-8",
    )
    shutil.copytree(
        _TESTS_DIR / "_pytest_plugins",
        mini_tests / "_pytest_plugins",
    )
    mini_tests.joinpath("conftest.py").write_text(
        _HARNESS_SOURCE,
        encoding="utf-8",
    )
    mini_tests.joinpath("KNOWN_ISSUES.yml").write_text(
        "known_issues: []\n",
        encoding="utf-8",
    )
    mini_tests.joinpath("test_probe.py").write_text(
        dedent(source),
        encoding="utf-8",
    )

    fake_moira = pytester.path / "moira"
    fake_moira.mkdir()
    fake_moira.joinpath("__init__.py").write_text("", encoding="utf-8")
    fake_moira.joinpath("spk_reader.py").write_text(
        _FAKE_SPK_READER,
        encoding="utf-8",
    )
    fake_moira.joinpath("_kernel_paths.py").write_text(
        _FAKE_KERNEL_PATHS,
        encoding="utf-8",
    )
    pytester.path.joinpath("pytest.ini").write_text(
        _PYTEST_CONFIG,
        encoding="utf-8",
    )


def _run_harness_project(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    *arguments: str,
    environment: dict[str, str] | None = None,
) -> pytest.RunResult:
    for name in (
        "MOIRA_KERNEL_PATH",
        "MOIRA_KERNELS_DIR",
        "FAKE_DISCOVERED_KERNEL",
        "FAKE_DISCOVERY_ERROR",
        "FAKE_KERNEL_LOG",
        "FAKE_LIVE_OPEN_FAIL_AFTER",
        "MOIRA_TEST_MODE",
        "MOIRA_NO_DOWNLOAD",
        "MOIRA_STRICT_KNOWN_ISSUES",
        "MOIRA_SNAPSHOT_UPDATE",
        "MOIRA_GOLDEN_UPDATE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1")
    for name, value in (environment or {}).items():
        monkeypatch.setenv(name, value)
    invocation = (
        arguments
        if arguments and not arguments[0].startswith("-")
        else ("tests", *arguments)
    )
    return pytester.runpytest_subprocess(
        *invocation,
        "--tb=short",
        timeout=45,
    )


def _combined_output(result: pytest.RunResult) -> str:
    return f"{result.stdout.str()}\n{result.stderr.str()}"


def _placeholder_kernel_path(
    tmp_path: Path,
    name: str = "candidate.bsp",
) -> Path:
    path = tmp_path / name
    path.write_bytes(b"synthetic planetary-kernel placeholder")
    return path


def _segment(
    *,
    target: int = 10,
    center: int = 0,
    frame: int = 1,
    segment_type: int = 2,
    start: float = 1000.0,
    end: float = 2000.0,
) -> KernelSegmentCapability:
    return KernelSegmentCapability(
        route=KernelRoute(
            target_naif_id=target,
            center_naif_id=center,
        ),
        frame=frame,
        segment_type=segment_type,
        start_jd=start,
        end_jd=end,
    )


def _capability(
    *segments: KernelSegmentCapability,
    identity: str = "DE441",
    summary_label: str = "DE-0441LE-0441",
    native: bool = True,
) -> PlanetaryKernelCapability:
    admitted_segments = tuple(
        segments
        or (
            _segment(),
            _segment(
                target=301,
                center=3,
                start=1000.0,
                end=2000.0,
            ),
        )
    )
    routes = frozenset(segment.route for segment in admitted_segments)
    return PlanetaryKernelCapability(
        product="planetary-spk",
        content_identity=identity,
        summary_label=summary_label,
        planetary_ephemeris=(
            identity
            if identity.startswith("DE")
            else None
        ),
        lunar_ephemeris=(
            "LE441"
            if identity == "DE441"
            else None
        ),
        segments=admitted_segments,
        bodies=frozenset(
            segment.route.target_naif_id
            for segment in admitted_segments
        ),
        target_center_pairs=routes,
        frames=frozenset(segment.frame for segment in admitted_segments),
        segment_types=frozenset(
            segment.segment_type
            for segment in admitted_segments
        ),
        native_capability=native,
    )


class _FakeReader:
    def __init__(
        self,
        *,
        identity: str = "DE441",
        summary_label: str = "DE-0441LE-0441",
        segments: tuple[SimpleNamespace, ...] | None = None,
    ) -> None:
        self._kernel_identity = SimpleNamespace(
            summary_label=summary_label,
            planetary_ephemeris=identity,
            lunar_ephemeris="LE441",
        )
        self._kernel = SimpleNamespace(
            catalog={"summaries": [{"descriptor": object()}]},
            segments=list(
                segments
                or (
                    SimpleNamespace(
                        target=10,
                        center=0,
                        frame=1,
                        data_type=2,
                        start_jd=1000.0,
                        end_jd=2000.0,
                    ),
                )
            ),
        )
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


def test_requirement_is_frozen_hashable_and_canonical() -> None:
    requirement = PlanetaryKernelRequirement(
        content_identity="DE441",
        bodies=frozenset({10, 301}),
        target_center_pairs=frozenset(
            {
                KernelRoute(target_naif_id=301, center_naif_id=3),
                KernelRoute(target_naif_id=10, center_naif_id=0),
            }
        ),
        segment_types=frozenset({3, 2}),
    )

    assert hash(requirement)
    assert (
        requirement.render()
        == "planetary-kernel[product=planetary-spk;identity=DE441;"
        "bodies=10,301;routes=target=10/center=0,"
        "target=301/center=3;segment_types=2,3]"
    )
    with pytest.raises(FrozenInstanceError):
        requirement.content_identity = "DE430"


@pytest.mark.parametrize(
    "kwargs",
    (
        {"bodies": frozenset({True})},
        {"bodies": None},
        {"target_center_pairs": frozenset({(10,)})},
        {"target_center_pairs": frozenset({(True, 0)})},
        {"frame": True},
        {"segment_types": frozenset({False})},
        {"segment_types": frozenset({0})},
        {"segment_types": 2},
        {"native_capability": 1},
        {"interval": ("1000.0", "2000.0")},
        {"interval": (math.nan, 2.0)},
        {"interval": (2.0, math.inf)},
        {"interval": (2.0, 1.0)},
        {"content_identity": "DE441\nspoof"},
    ),
)
def test_requirement_rejects_ambiguous_or_nonfinite_values(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ResourceContractError):
        PlanetaryKernelRequirement(**kwargs)


def test_requirement_mapping_rejects_unknown_or_generic_plus_constraints() -> None:
    with pytest.raises(ResourceContractError, match="unknown"):
        PlanetaryKernelRequirement.from_mapping({"filename": "de441.bsp"})
    with pytest.raises(ResourceContractError, match="generic"):
        PlanetaryKernelRequirement.from_mapping(
            {"generic": True, "content_identity": "DE441"}
        )
    historical_default = PlanetaryKernelRequirement.from_mapping({})
    assert historical_default.content_identity == "DE441"
    assert not historical_default.is_generic
    assert PlanetaryKernelRequirement.from_mapping({"generic": True}).is_generic
    with pytest.raises(ResourceContractError, match="generic=True"):
        PlanetaryKernelRequirement.from_mapping({"product": "planetary-spk"})


def test_target_center_pair_order_is_named_and_not_reversible() -> None:
    requirement = PlanetaryKernelRequirement.from_mapping(
        {"target_center_pairs": [(301, 3)]}
    )
    assert requirement.target_center_pairs == frozenset(
        {KernelRoute(target_naif_id=301, center_naif_id=3)}
    )
    mismatch = capability_mismatches(
        PlanetaryKernelRequirement.from_mapping(
            {"target_center_pairs": [(3, 301)]}
        ),
        _capability(_segment(target=301, center=3)),
    )
    assert any("target=3/center=301" in item for item in mismatch)


def test_capability_is_derived_from_opened_content_not_filename() -> None:
    reader = _FakeReader(
        identity="DE430",
        summary_label="DE-0430LE-0430",
    )
    reader._kernel_identity.lunar_ephemeris = "LE430"

    capability = capability_from_reader(
        reader,
        native_detector=lambda _catalog: True,
    )

    assert capability.content_identity == "DE430"
    assert capability.summary_label == "DE-0430LE-0430"
    assert capability.native_capability is True


def test_capability_canonicalizes_mutable_segments_without_aliasing() -> None:
    original = _segment()
    mutable_segments = [original]
    capability = PlanetaryKernelCapability(
        product="planetary-spk",
        content_identity="DE441",
        summary_label="DE-0441LE-0441",
        planetary_ephemeris="DE441",
        lunar_ephemeris="LE441",
        segments=mutable_segments,
        bodies=frozenset({10}),
        target_center_pairs=frozenset({original.route}),
        frames=frozenset({1}),
        segment_types=frozenset({2}),
        native_capability=True,
    )

    mutable_segments.append(_segment(target=399))

    assert capability.segments == (original,)
    assert capability_mismatches(
        PlanetaryKernelRequirement(bodies=frozenset({399})),
        capability,
    )


def test_capability_rejects_reader_retention_in_segment_facts() -> None:
    reader = _FakeReader()

    with pytest.raises(ResourceContractError, match="KernelSegmentCapability"):
        PlanetaryKernelCapability(
            product="planetary-spk",
            content_identity="DE441",
            summary_label="DE-0441LE-0441",
            planetary_ephemeris="DE441",
            lunar_ephemeris="LE441",
            segments=(reader,),
            bodies=frozenset(),
            target_center_pairs=frozenset(),
            frames=frozenset(),
            segment_types=frozenset(),
            native_capability=True,
        )


def test_unknown_coherent_identity_can_only_satisfy_generic_requirement() -> None:
    capability = _capability(
        identity="CUSTOM PLANETARY KERNEL",
        summary_label="CUSTOM PLANETARY KERNEL",
    )

    assert not capability_mismatches(
        PlanetaryKernelRequirement(),
        capability,
    )
    mismatch = capability_mismatches(
        PlanetaryKernelRequirement(content_identity="DE441"),
        capability,
    )
    assert mismatch == (
        "content_identity expected DE441, got CUSTOM PLANETARY KERNEL "
        "(summary CUSTOM PLANETARY KERNEL)",
    )


@pytest.mark.parametrize(
    "alias",
    ("LE441", "DE-0430LE-0441"),
)
def test_content_identity_matches_only_the_canonical_identity(
    alias: str,
) -> None:
    segment = _segment()
    capability = PlanetaryKernelCapability(
        product="planetary-spk",
        content_identity="DE430",
        summary_label="DE-0430LE-0441",
        planetary_ephemeris="DE430",
        lunar_ephemeris="LE441",
        segments=(segment,),
        bodies=frozenset({10}),
        target_center_pairs=frozenset({segment.route}),
        frames=frozenset({1}),
        segment_types=frozenset({2}),
        native_capability=True,
    )

    assert capability_mismatches(
        PlanetaryKernelRequirement(content_identity="DE430"),
        capability,
    ) == ()
    mismatch = capability_mismatches(
        PlanetaryKernelRequirement(content_identity=alias),
        capability,
    )
    assert mismatch
    assert f"content_identity expected {alias}, got DE430" in mismatch[0]


@pytest.mark.parametrize(
    ("requirement", "token"),
    (
        (
            PlanetaryKernelRequirement(product="small-body-spk"),
            "product",
        ),
        (
            PlanetaryKernelRequirement(bodies=frozenset({399})),
            "body target=399",
        ),
        (
            PlanetaryKernelRequirement(frame=17),
            "frame 17",
        ),
        (
            PlanetaryKernelRequirement(
                segment_types=frozenset({13})
            ),
            "segment_types 13",
        ),
        (
            PlanetaryKernelRequirement(native_capability=False),
            "native_capability",
        ),
    ),
)
def test_independent_capability_mismatches_are_named(
    requirement: PlanetaryKernelRequirement,
    token: str,
) -> None:
    mismatches = capability_mismatches(requirement, _capability())
    assert any(token in mismatch for mismatch in mismatches)


def test_interval_uses_contiguous_segments_not_coverage_envelope() -> None:
    capability = _capability(
        _segment(start=1000.0, end=1200.0),
        _segment(start=1300.0, end=2000.0),
    )
    requirement = PlanetaryKernelRequirement(
        interval=(1100.0, 1900.0),
        target_center_pairs=frozenset(
            {KernelRoute(target_naif_id=10, center_naif_id=0)}
        ),
    )

    mismatches = capability_mismatches(requirement, capability)

    assert len(mismatches) == 1
    assert "continuously cover" in mismatches[0]


def test_contiguous_route_segments_admit_the_whole_interval() -> None:
    capability = _capability(
        _segment(start=1000.0, end=1300.0),
        _segment(start=1300.0, end=2000.0),
    )
    requirement = PlanetaryKernelRequirement(
        interval=(1100.0, 1900.0),
        target_center_pairs=frozenset(
            {KernelRoute(target_naif_id=10, center_naif_id=0)}
        ),
    )

    assert capability_mismatches(requirement, capability) == ()


def test_frame_and_type_must_serve_the_required_route() -> None:
    capability = _capability(
        _segment(target=10, center=0, frame=1, segment_type=2),
        _segment(target=301, center=3, frame=17, segment_type=3),
    )
    requirement = PlanetaryKernelRequirement(
        target_center_pairs=frozenset(
            {KernelRoute(target_naif_id=10, center_naif_id=0)}
        ),
        frame=17,
        segment_types=frozenset({3}),
    )

    mismatch = capability_mismatches(requirement, capability)

    assert mismatch == ("route target=10/center=0 is not present",)


def test_missing_candidate_skips_without_opening_any_reader() -> None:
    opened = 0

    def forbidden_factory(_path: Path) -> object:
        nonlocal opened
        opened += 1
        raise AssertionError("reader must remain unopened")

    resolver = PlanetaryResourceResolver(
        None,
        reader_factory=forbidden_factory,
    )

    receipt = resolver.resolve(PlanetaryKernelRequirement())

    assert receipt.disposition is ResourceDisposition.SKIP
    assert resolver.probe_count == 0
    assert opened == 0


def test_corrupt_existing_candidate_is_failure_not_availability(
    tmp_path: Path,
) -> None:
    corrupt = tmp_path / "de441.bsp"
    corrupt.write_bytes(b"not a DAF/SPK file")
    resolver = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            corrupt,
            explicit=False,
            source="test discovery",
        ),
        reader_factory=lambda path: (_ for _ in ()).throw(
            ValueError(f"corrupt resource at {path}")
        ),
    )

    receipt = resolver.resolve(PlanetaryKernelRequirement())

    assert receipt.disposition is ResourceDisposition.FAILURE
    assert receipt.capability is None
    assert receipt.failure_type == "ValueError"
    assert "corrupt resource" in receipt.reason


def test_probe_reader_closes_when_capability_build_fails(
    tmp_path: Path,
) -> None:
    reader = _FakeReader()
    candidate_path = _placeholder_kernel_path(tmp_path)
    resolver = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            candidate_path,
            explicit=False,
            source="test discovery",
        ),
        reader_factory=lambda _path: reader,
        capability_builder=lambda _reader: (_ for _ in ()).throw(
            ResourceContractError("malformed descriptor")
        ),
    )

    receipt = resolver.resolve(PlanetaryKernelRequirement())

    assert receipt.disposition is ResourceDisposition.FAILURE
    assert reader.close_calls == 1


def test_probe_close_failure_is_not_retried_or_hidden(
    tmp_path: Path,
) -> None:
    reader = _FakeReader()
    candidate_path = _placeholder_kernel_path(tmp_path)

    def fail_close() -> None:
        reader.close_calls += 1
        raise OSError("close receipt failed")

    reader.close = fail_close
    resolver = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            candidate_path,
            explicit=False,
            source="test discovery",
        ),
        reader_factory=lambda _path: reader,
        capability_builder=lambda _reader: _capability(),
    )

    receipt = resolver.resolve(PlanetaryKernelRequirement())

    assert receipt.disposition is ResourceDisposition.FAILURE
    assert reader.close_calls == 1
    assert receipt.failure_type == "OSError"
    assert "close receipt failed" in receipt.reason


def test_resolver_probes_once_and_never_caches_the_reader(
    tmp_path: Path,
) -> None:
    readers: list[_FakeReader] = []
    capability = _capability()
    candidate_path = _placeholder_kernel_path(
        tmp_path,
        "renamed.bsp",
    )

    def factory(_path: Path) -> _FakeReader:
        reader = _FakeReader()
        readers.append(reader)
        return reader

    resolver = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            candidate_path,
            explicit=False,
            source="test discovery",
        ),
        reader_factory=factory,
        capability_builder=lambda _reader: capability,
    )

    first = resolver.resolve(PlanetaryKernelRequirement())
    second = resolver.resolve(
        PlanetaryKernelRequirement(content_identity="DE441")
    )

    assert first.disposition is ResourceDisposition.RUN
    assert second.disposition is ResourceDisposition.RUN
    assert resolver.probe_count == 1
    assert len(readers) == 1
    assert readers[0].close_calls == 1
    assert resolver.cached_capability is capability
    assert all(
        not isinstance(value, _FakeReader)
        for value in (
            resolver.cached_capability,
            first.capability,
            second.capability,
        )
    )


def test_resolver_rejects_a_builder_that_returns_the_reader(
    tmp_path: Path,
) -> None:
    reader = _FakeReader()
    candidate_path = _placeholder_kernel_path(tmp_path)
    resolver = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            candidate_path,
            explicit=False,
            source="test discovery",
        ),
        reader_factory=lambda _path: reader,
        capability_builder=lambda opened_reader: opened_reader,
    )

    receipt = resolver.resolve(PlanetaryKernelRequirement())

    assert receipt.disposition is ResourceDisposition.FAILURE
    assert receipt.failure_type == "ResourceContractError"
    assert resolver.cached_capability is None
    assert reader.close_calls == 1


def test_concurrent_resolves_share_exactly_one_probe(
    tmp_path: Path,
) -> None:
    condition = Condition()
    readers: list[_FakeReader] = []
    candidate_path = _placeholder_kernel_path(tmp_path)

    def factory(_path: Path) -> _FakeReader:
        reader = _FakeReader()
        with condition:
            readers.append(reader)
            condition.notify_all()
            if len(readers) == 1:
                condition.wait_for(
                    lambda: len(readers) > 1,
                    timeout=0.25,
                )
        return reader

    resolver = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            candidate_path,
            explicit=False,
            source="test discovery",
        ),
        reader_factory=factory,
        capability_builder=lambda _reader: _capability(),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                resolver.resolve,
                PlanetaryKernelRequirement(),
            )
            for _ in range(2)
        ]
        receipts = [future.result(timeout=2) for future in futures]

    assert all(
        receipt.disposition is ResourceDisposition.RUN
        for receipt in receipts
    )
    assert resolver.probe_count == 1
    assert len(readers) == 1
    assert readers[0].close_calls == 1


def test_mismatch_skips_discovered_but_fails_explicit_candidate(
    tmp_path: Path,
) -> None:
    capability = _capability(identity="DE430", summary_label="DE-0430LE-0430")
    requirement = PlanetaryKernelRequirement(content_identity="DE441")
    discovered_path = _placeholder_kernel_path(
        tmp_path,
        "de441.bsp",
    )
    explicit_path = _placeholder_kernel_path(
        tmp_path,
        "renamed.bsp",
    )

    discovered = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            discovered_path,
            explicit=False,
            source="deterministic search",
        ),
        reader_factory=lambda _path: _FakeReader(),
        capability_builder=lambda _reader: capability,
    ).resolve(requirement)
    explicit = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            explicit_path,
            explicit=True,
            source="MOIRA_KERNEL_PATH",
        ),
        reader_factory=lambda _path: _FakeReader(),
        capability_builder=lambda _reader: capability,
    ).resolve(requirement)

    assert discovered.disposition is ResourceDisposition.SKIP
    assert explicit.disposition is ResourceDisposition.FAILURE
    assert explicit.failure_type == "CapabilityMismatch"


def test_explicit_kernel_path_is_authoritative_even_when_missing(
    tmp_path: Path,
) -> None:
    finder_called = False

    def finder() -> Path:
        nonlocal finder_called
        finder_called = True
        return tmp_path / "fallback.bsp"

    explicit = tmp_path / "missing.bsp"
    candidate = discover_planetary_kernel_candidate(
        environ={"MOIRA_KERNEL_PATH": str(explicit)},
        finder=finder,
    )

    assert candidate == PlanetaryKernelCandidate(
        explicit,
        explicit=True,
        source="MOIRA_KERNEL_PATH",
    )
    assert finder_called is False


def test_empty_explicit_kernel_path_does_not_become_the_working_directory(
    tmp_path: Path,
) -> None:
    discovered = tmp_path / "fallback.bsp"
    finder_called = False

    def finder() -> Path:
        nonlocal finder_called
        finder_called = True
        return discovered

    candidate = discover_planetary_kernel_candidate(
        environ={"MOIRA_KERNEL_PATH": ""},
        finder=finder,
    )

    assert candidate == PlanetaryKernelCandidate(
        discovered,
        explicit=False,
        source="deterministic search",
    )
    assert finder_called is True


def test_discovery_without_override_is_location_evidence_only(
    tmp_path: Path,
) -> None:
    candidate = discover_planetary_kernel_candidate(
        environ={},
        finder=lambda: tmp_path / "de441.bsp",
    )

    assert candidate == PlanetaryKernelCandidate(
        tmp_path / "de441.bsp",
        explicit=False,
        source="deterministic search",
    )


def test_receipt_render_names_expected_actual_and_disposition(
    tmp_path: Path,
) -> None:
    requirement = PlanetaryKernelRequirement(content_identity="DE441")
    capability = _capability(identity="DE430", summary_label="DE-0430LE-0430")
    receipt = PlanetaryKernelReceipt(
        name="planetary-kernel",
        disposition=ResourceDisposition.FAILURE,
        requirement=requirement,
        candidate=PlanetaryKernelCandidate(
            tmp_path / "spoofed-de441.bsp",
            explicit=True,
            source="MOIRA_KERNEL_PATH",
        ),
        capability=capability,
        reason="content_identity expected DE441, got DE430",
        failure_type="CapabilityMismatch",
    )

    rendered = receipt.render()

    assert "disposition=failure" in rendered
    assert "identity=DE441" in rendered
    assert "actual_identity=DE430" in rendered
    assert "failure_type=CapabilityMismatch" in rendered


def test_forged_run_receipt_cannot_bypass_identity_admission(
    tmp_path: Path,
) -> None:
    reader = _FakeReader(
        identity="DE430",
        summary_label="DE-0430LE-0430",
    )
    reader._kernel_identity.lunar_ephemeris = "LE430"
    capability = capability_from_reader(reader)
    candidate_path = _placeholder_kernel_path(
        tmp_path,
        "renamed.bsp",
    )
    candidate = PlanetaryKernelCandidate(
        candidate_path,
        explicit=False,
        source="test discovery",
        fingerprint=PlanetaryKernelFingerprint.from_path(candidate_path),
    )

    with pytest.raises(
        ResourceContractError,
        match="RUN receipt capability does not satisfy",
    ):
        PlanetaryKernelReceipt(
            name="planetary-kernel",
            disposition=ResourceDisposition.RUN,
            requirement=PlanetaryKernelRequirement(
                content_identity="DE441"
            ),
            candidate=candidate,
            capability=capability,
            reason="forged admission",
        )

    admitted = PlanetaryKernelReceipt(
        name="planetary-kernel",
        disposition=ResourceDisposition.RUN,
        requirement=PlanetaryKernelRequirement(
            content_identity="DE430"
        ),
        candidate=candidate,
        capability=capability,
        reason="opened content satisfies the declared capability",
    )
    object.__setattr__(
        admitted,
        "requirement",
        PlanetaryKernelRequirement(content_identity="DE441"),
    )
    with pytest.raises(
        ResourceContractError,
        match="receipt does not satisfy",
    ):
        verify_reader_matches_receipt(reader, admitted)


def test_live_reader_revalidation_rejects_changed_content(
    tmp_path: Path,
) -> None:
    admitted_capability = _capability()
    candidate_path = _placeholder_kernel_path(
        tmp_path,
        "renamed.bsp",
    )
    receipt = PlanetaryKernelReceipt(
        name="planetary-kernel",
        disposition=ResourceDisposition.RUN,
        requirement=PlanetaryKernelRequirement(content_identity="DE441"),
        candidate=PlanetaryKernelCandidate(
            candidate_path,
            explicit=False,
            source="test discovery",
            fingerprint=PlanetaryKernelFingerprint.from_path(candidate_path),
        ),
        capability=admitted_capability,
        reason="opened content satisfies the declared capability",
    )
    changed_reader = _FakeReader(
        identity="DE430",
        summary_label="DE-0430LE-0430",
    )
    changed_reader._kernel_identity.lunar_ephemeris = "LE430"

    with pytest.raises(ResourceContractError, match="changed after"):
        verify_reader_matches_receipt(changed_reader, receipt)


def test_live_reader_revalidation_rejects_same_identity_file_replacement(
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "renamed.bsp"
    candidate_path.write_bytes(b"AAAA")
    resolver = PlanetaryResourceResolver(
        PlanetaryKernelCandidate(
            candidate_path,
            explicit=False,
            source="test discovery",
        ),
        reader_factory=lambda _path: _FakeReader(),
    )
    receipt = resolver.resolve(
        PlanetaryKernelRequirement(content_identity="DE441")
    )

    assert receipt.disposition is ResourceDisposition.RUN
    assert receipt.candidate is not None
    assert receipt.candidate.fingerprint is not None
    original_fingerprint = receipt.candidate.fingerprint

    replacement = tmp_path / "replacement.bsp"
    replacement.write_bytes(b"BBBB")
    if original_fingerprint.file_id is not None:
        os.utime(
            replacement,
            ns=(
                original_fingerprint.mtime_ns,
                original_fingerprint.mtime_ns,
            ),
        )
    else:
        replacement.write_bytes(b"different-size coefficients")
    os.replace(replacement, candidate_path)

    live_reader = _FakeReader()
    assert capability_from_reader(live_reader) == receipt.capability
    with pytest.raises(ResourceContractError, match="fingerprint changed"):
        verify_reader_matches_receipt(live_reader, receipt)


def test_kernel_free_exact_selection_never_opens_corrupt_configured_path(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corrupt = pytester.path / "de441.bsp"
    corrupt.write_text("not-json", encoding="utf-8")
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        import pytest


        def test_kernel_free():
            pass


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_resource_sibling_must_not_be_set_up():
            raise AssertionError("deselected resource sibling executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "tests/test_probe.py::test_kernel_free",
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(corrupt),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(passed=1)
    assert not log.exists()
    assert "Planetary resource:" not in _combined_output(result)


def test_discovered_identity_mismatch_skips_with_named_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "spoofed-de441.bsp"
    candidate.write_text(
        '{"identity":"DE430","summary":"DE-0430LE-0430",'
        '"lunar_identity":"LE430"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        import pytest

        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_requires_de441():
            raise AssertionError("mismatched resource test body executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "FAKE_DISCOVERED_KERNEL": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(skipped=1)
    output = _combined_output(result)
    assert "actual_identity=DE430" in output
    assert "content_identity expected DE441" in output
    assert log.read_text(encoding="utf-8").splitlines() == [
        "open:spoofed-de441.bsp",
        "close:spoofed-de441.bsp",
    ]


def test_mismatch_is_enforced_before_session_reader_fixture_opens(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "spoofed-de441.bsp"
    candidate.write_text(
        '{"identity":"DE430","summary":"DE-0430LE-0430",'
        '"lunar_identity":"LE430"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        import pytest

        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_requires_de441(planetary_reader):
            raise AssertionError("mismatched resource fixture opened")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "FAKE_DISCOVERED_KERNEL": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(skipped=1)
    output = _combined_output(result)
    assert "actual_identity=DE430" in output
    assert "content_identity expected DE441" in output
    assert log.read_text(encoding="utf-8").splitlines() == [
        "open:spoofed-de441.bsp",
        "close:spoofed-de441.bsp",
    ]


def test_pre_skipped_resource_item_never_discovers_or_opens_kernel(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corrupt = pytester.path / "corrupt.bsp"
    corrupt.write_text("not-json", encoding="utf-8")
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        import pytest


        @pytest.mark.skip(reason="precondition unavailable")
        def test_skipped_resource(planetary_reader):
            raise AssertionError("skipped resource body executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(corrupt),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(skipped=1)
    assert not log.exists()
    assert "Planetary resource:" not in _combined_output(result)


def test_stateful_skipif_is_evaluated_once_before_resource_admission(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corrupt = pytester.path / "corrupt.bsp"
    corrupt.write_text("not-json", encoding="utf-8")
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        r"""
        import pytest


        _skip_decisions = iter((True, False))


        def stateful_skip():
            return next(_skip_decisions)


        @pytest.mark.skipif(
            "stateful_skip()",
            reason="first decision skips",
        )
        def test_skipped_resource(planetary_reader):
            raise AssertionError("stateful skipped resource body executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(corrupt),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(skipped=1)
    assert not log.exists()
    assert "Planetary resource:" not in _combined_output(result)


def test_nonrunning_xfail_never_discovers_or_opens_kernel(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corrupt = pytester.path / "corrupt.bsp"
    corrupt.write_text("not-json", encoding="utf-8")
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        import pytest


        @pytest.mark.xfail(run=False, reason="unsafe precondition")
        def test_nonrunning_resource(planetary_reader):
            raise AssertionError("non-running xfail body executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(corrupt),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(xfailed=1)
    assert not log.exists()
    assert "Planetary resource:" not in _combined_output(result)

    run_result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        "--runxfail",
        environment={
            "MOIRA_KERNEL_PATH": str(corrupt),
            "FAKE_KERNEL_LOG": str(log),
        },
    )
    run_result.assert_outcomes(errors=1)
    run_output = _combined_output(run_result)
    assert "disposition=failure" in run_output
    assert "content_probes=1" in run_output


def test_discovery_failure_is_a_named_failure_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_harness_project(
        pytester,
        """
        import pytest


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_resource():
            raise AssertionError("resource body executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={"FAKE_DISCOVERY_ERROR": "1"},
    )

    result.assert_outcomes(errors=1)
    output = _combined_output(result)
    assert "disposition=failure" in output
    assert "failure_type=OSError" in output
    assert "planetary-kernel discovery failed" in output
    assert "failure=1" in output
    assert "content_probes=0" in output


def test_live_acquisition_failure_replaces_false_green_terminal_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "candidate.bsp"
    candidate.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        def test_resource(planetary_reader):
            raise AssertionError("resource body executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
            "FAKE_LIVE_OPEN_FAIL_AFTER": "1",
        },
    )

    result.assert_outcomes(errors=1)
    output = _combined_output(result)
    assert "synthetic live acquisition failure" in output
    assert "planetary-kernel-live" in output
    assert "failure=1" in output
    assert "content_probes=1" in output


def test_moira_engine_missing_reader_is_recorded_as_live_failure(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "de441.bsp"
    candidate.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        def test_engine(moira_engine):
            raise AssertionError("missing-reader engine body executed")
        """,
    )
    pytester.path.joinpath("moira", "__init__.py").write_text(
        dedent(
            """
            class Moira:
                def __init__(self, kernel_path=None):
                    self._reader_obj = None
                    self._supplemental_kernel_init_error = None
            """
        ),
        encoding="utf-8",
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(errors=1)
    output = _combined_output(result)
    assert "could not open its admitted planetary resource" in output
    assert "planetary-kernel-live" in output
    assert "failure=1" in output
    assert "content_probes=1" in output


def test_explicit_identity_mismatch_fails_without_fallback(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "renamed.bsp"
    candidate.write_text(
        '{"identity":"DE430","summary":"DE-0430LE-0430",'
        '"lunar_identity":"LE430"}',
        encoding="utf-8",
    )
    fallback = pytester.path / "fallback.bsp"
    fallback.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        import pytest


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_requires_de441():
            raise AssertionError("mismatched resource test body executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(candidate),
            "FAKE_DISCOVERED_KERNEL": str(fallback),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(errors=1)
    output = _combined_output(result)
    assert "disposition=failure" in output
    assert "failure_type=CapabilityMismatch" in output
    assert "actual_identity=DE430" in output
    assert "fallback.bsp" not in log.read_text(encoding="utf-8")


def test_matching_items_share_one_probe_and_one_owned_live_reader(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "renamed.bsp"
    candidate.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        import pytest


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_first():
            from moira.spk_reader import get_reader
            assert get_reader().path.name == "renamed.bsp"


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_second():
            from moira.spk_reader import get_reader
            assert get_reader().path.name == "renamed.bsp"
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(passed=2)
    assert log.read_text(encoding="utf-8").splitlines() == [
        "open:renamed.bsp",
        "close:renamed.bsp",
        "open:renamed.bsp",
        "close:renamed.bsp",
    ]
    output = _combined_output(result)
    assert "content_probes=1" in output
    assert "identities=DE441" in output


def test_corrupt_explicit_resource_fails_before_test_body(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "corrupt.bsp"
    candidate.write_text('{"corrupt":true}', encoding="utf-8")
    log = pytester.path / "kernel.log"
    body_sentinel = pytester.path / "body-ran"
    _make_harness_project(
        pytester,
        f"""
        from pathlib import Path
        import pytest


        @pytest.mark.requires_ephemeris(generic=True)
        def test_corrupt_resource_never_runs():
            Path({str(body_sentinel)!r}).write_text("ran", encoding="utf-8")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(errors=1)
    assert not body_sentinel.exists()
    output = _combined_output(result)
    assert "synthetic corrupt DAF/SPK" in output
    assert "disposition=failure" in output


def test_planetary_reader_context_never_mutates_global_singleton(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "de441.bsp"
    candidate.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        def test_explicit_reader_is_contextual(planetary_reader):
            from moira import spk_reader
            assert spk_reader._reader is None
            assert spk_reader._reader_path is None
            assert spk_reader.get_reader() is planetary_reader


        def test_kernel_free_successor_sees_no_global_state():
            from moira import spk_reader
            assert spk_reader._reader is None
            assert spk_reader._reader_path is None
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(passed=2)
    assert log.read_text(encoding="utf-8").splitlines() == [
        "open:de441.bsp",
        "close:de441.bsp",
        "open:de441.bsp",
        "close:de441.bsp",
    ]


def test_configured_global_reader_is_erased_before_successor(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "de441.bsp"
    candidate.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        def test_legacy_global_boundary(configured_global_reader):
            from moira import spk_reader
            assert spk_reader._reader is configured_global_reader
            assert spk_reader.get_reader() is configured_global_reader


        def test_successor_sees_erased_global_state():
            from moira import spk_reader
            assert spk_reader._reader is None
            assert spk_reader._reader_path is None
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(passed=2)
    assert log.read_text(encoding="utf-8").splitlines() == [
        "open:de441.bsp",
        "close:de441.bsp",
        "open:de441.bsp",
        "close:de441.bsp",
    ]


def test_configured_global_reader_refuses_foreign_state_with_failure_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "de441.bsp"
    candidate.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    log = pytester.path / "kernel.log"
    _make_harness_project(
        pytester,
        """
        from pathlib import Path

        import pytest


        @pytest.fixture(scope="session", autouse=True)
        def foreign_global_reader():
            from moira import spk_reader

            foreign = object()
            spk_reader._reader = foreign
            spk_reader._reader_path = Path("foreign-reader.bsp")
            yield
            preserved = (
                spk_reader._reader is foreign
                and spk_reader._reader_path == Path("foreign-reader.bsp")
            )
            spk_reader._reader = None
            spk_reader._reader_path = None
            assert preserved, "fixture erased reader state it did not own"


        def test_legacy_global_boundary(configured_global_reader):
            raise AssertionError("foreign state must block fixture setup")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "MOIRA_KERNEL_PATH": str(candidate),
            "FAKE_KERNEL_LOG": str(log),
        },
    )

    result.assert_outcomes(errors=1)
    output = _combined_output(result)
    assert "refuses to hot-swap pre-existing global reader state" in output
    assert "failure=1" in output
    assert "configured-global-reader-acquisition" in output
    assert log.read_text(encoding="utf-8").splitlines() == [
        "open:de441.bsp",
        "close:de441.bsp",
    ]


@pytest.mark.parametrize(
    "source",
    (
        """
        import pytest


        @pytest.mark.requires_ephemeris("DE441")
        def test_invalid_positional_contract():
            pass
        """,
        """
        import pytest


        @pytest.mark.requires_ephemeris(bodies=None)
        def test_invalid_capability_value():
            pass
        """,
        """
        import pytest


        pytestmark = pytest.mark.requires_ephemeris(
            content_identity="DE430"
        )


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_conflicting_contracts():
            pass
        """,
        """
        import pytest


        pytestmark = pytest.mark.requires_ephemeris(
            content_identity="DE441"
        )


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_duplicate_contracts():
            pass
        """,
    ),
)
def test_invalid_or_conflicting_resource_markers_fail_collection(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    _make_harness_project(pytester, source)

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "--collect-only",
        "-q",
    )

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    output = _combined_output(result)
    assert "requires_ephemeris" in output


def _planetary_resource_summary_line(
    result: pytest.RunResult,
) -> str:
    lines = [
        line.strip()
        for line in _combined_output(result).splitlines()
        if line.strip().startswith("Planetary resource:")
    ]
    assert len(lines) == 1, lines
    return lines[0]


def test_xdist_planetary_receipt_summary_matches_serial_semantics(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "renamed.bsp"
    candidate.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    _make_harness_project(
        pytester,
        """
        import pytest

        pytestmark = pytest.mark.parallel(reason="isolated_resources")


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_first():
            pass


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_second():
            pass


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_third():
            pass


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_fourth():
            pass
        """,
    )

    serial = _run_harness_project(
        pytester,
        monkeypatch,
        "-q",
        environment={"MOIRA_KERNEL_PATH": str(candidate)},
    )
    serial.assert_outcomes(passed=4)

    parallel = _run_harness_project(
        pytester,
        monkeypatch,
        "-n",
        "2",
        "--dist=load",
        "-q",
        environment={"MOIRA_KERNEL_PATH": str(candidate)},
    )
    parallel.assert_outcomes(passed=4)

    assert _planetary_resource_summary_line(serial) == (
        "Planetary resource: receipts=6, run=6, skip=0, failure=0, "
        "content_probes=1, identities=DE441"
    )
    assert _planetary_resource_summary_line(parallel) == (
        "Planetary resource: receipts=6, run=6, skip=0, failure=0, "
        "content_probes=2, identities=DE441"
    )


def test_xdist_planetary_receipt_details_survive_worker_shutdown(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = pytester.path / "spoofed-de441.bsp"
    candidate.write_text(
        '{"identity":"DE430","summary":"DE-0430LE-0430",'
        '"lunar_identity":"LE430"}',
        encoding="utf-8",
    )
    _make_harness_project(
        pytester,
        """
        import pytest

        pytestmark = pytest.mark.parallel(reason="isolated_resources")


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_first():
            raise AssertionError("mismatched resource test body executed")


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_second():
            raise AssertionError("mismatched resource test body executed")


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_third():
            raise AssertionError("mismatched resource test body executed")


        @pytest.mark.requires_ephemeris(content_identity="DE441")
        def test_fourth():
            raise AssertionError("mismatched resource test body executed")
        """,
    )

    result = _run_harness_project(
        pytester,
        monkeypatch,
        "-n",
        "2",
        "--dist=load",
        "-q",
        environment={
            "FAKE_DISCOVERED_KERNEL": str(candidate),
        },
    )

    result.assert_outcomes(skipped=4)
    assert _planetary_resource_summary_line(result) == (
        "Planetary resource: receipts=4, run=0, skip=4, failure=0, "
        "content_probes=2, identities=DE430"
    )
    output_lines = {
        line.strip()
        for line in _combined_output(result).splitlines()
    }
    for name in ("first", "second", "third", "fourth"):
        prefix = (
            f"tests/test_probe.py::test_{name}: "
            "planetary-kernel: disposition=skip;"
        )
        assert any(line.startswith(prefix) for line in output_lines)

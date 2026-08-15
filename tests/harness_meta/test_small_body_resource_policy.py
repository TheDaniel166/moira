"""Adversarial contracts for released supplemental small-body resources."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest

import support.small_body_resource_policy as small_body_policy
from support.small_body_resource_policy import (
    SmallBodyManifestRequirement,
    SmallBodyResourceContractError,
    SmallBodyResourceDisposition,
    admit_small_body_manifests,
    close_small_body_readers,
    empty_small_body_report,
    fail_small_body_live_receipt,
    merge_small_body_report,
    small_body_report_from_receipts,
    terminalize_small_body_receipt,
)


_TESTS_DIR = Path(__file__).resolve().parents[1]
_HARNESS_SOURCE = (_TESTS_DIR / "conftest.py").read_text(encoding="utf-8")
_PLANETARY_POLICY_SOURCE = (
    _TESTS_DIR / "support" / "resource_policy.py"
).read_text(encoding="utf-8")
_SMALL_BODY_POLICY_SOURCE = (
    _TESTS_DIR / "support" / "small_body_resource_policy.py"
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
markers =
    requires_ephemeris: typed planetary-kernel capability
    loopback: local IPC only
    external_network: live external access
    network: forbidden legacy marker
    serial: isolated global-state test
    parallel: parallel-safe test
    property: property-based test
"""


def _manifest_payload(
    shard_bodies: tuple[tuple[int, ...], ...] = ((2_000_001,),),
    *,
    released: bool = True,
    catalog_id: str = "test-asteroids",
) -> dict[str, object]:
    shards = [
        {
            "index": index,
            "path": f"shard-{index}.bsp",
            "body_count": len(bodies),
            "bodies": list(bodies),
            "bytes": 1,
            "sha256": "1" * 64,
            "metadata": {
                "path": f"shard-{index}.metadata.json",
                "bytes": 1,
                "sha256": "2" * 64,
            },
        }
        for index, bodies in enumerate(shard_bodies)
    ]
    payload: dict[str, object] = {
        "manifest_schema": "moira.small-body-catalog/v1",
        "catalog_id": catalog_id,
        "catalog_version": "2026.07.30.1",
        "shard_count": len(shards),
        "body_count": sum(len(bodies) for bodies in shard_bodies),
        "shards": shards,
    }
    if released:
        payload["release"] = {
            "released_utc": "2026-07-30T12:00:00Z",
            "source_manifest_sha256": "a" * 64,
            "source_revision": "test-revision",
            "integrity": {
                "algorithm": "sha256",
                "receipt": "SHA256SUMS",
                "receipt_scope": (
                    "manifest, shards, metadata, and provenance files"
                ),
            },
            "files": [],
        }
    return payload


def _write_manifest(
    root: Path,
    shard_bodies: tuple[tuple[int, ...], ...] = ((2_000_001,),),
    *,
    released: bool = True,
    catalog_id: str = "test-asteroids",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    payload = _manifest_payload(
        shard_bodies,
        released=released,
        catalog_id=catalog_id,
    )
    for shard in payload["shards"]:
        root.joinpath(shard["path"]).write_bytes(b"x")
        root.joinpath(shard["metadata"]["path"]).write_text(
            "{}\n",
            encoding="utf-8",
        )
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _verification_for(path: Path) -> SimpleNamespace:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SimpleNamespace(
        root=path.parent.resolve(),
        catalog_id=payload["catalog_id"],
        catalog_version=payload["catalog_version"],
        shard_count=payload["shard_count"],
        body_count=payload["body_count"],
        manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


class _FakeSmallBodyReader:
    def __init__(
        self,
        path: Path,
        bodies: tuple[int, ...],
        *,
        segment_type: int = 13,
        close_log: list[str] | None = None,
        close_failure: bool = False,
    ) -> None:
        self._path = Path(path)
        self._catalog = {"native": True}
        self._kernel = SimpleNamespace(
            segments=[
                SimpleNamespace(
                    target=body,
                    center=10,
                    frame=1,
                    data_type=segment_type,
                    start_jd=2_400_000.5,
                    end_jd=2_500_000.5,
                )
                for body in bodies
            ]
        )
        self._close_log = close_log
        self._close_failure = close_failure

    def close(self) -> None:
        if self._close_log is not None:
            self._close_log.append(self._path.name)
        if self._close_failure:
            raise OSError(f"synthetic close failure for {self._path.name}")


def _reader_factory(
    manifest: Path,
    *,
    close_log: list[str] | None = None,
    fail_name: str | None = None,
    body_override: dict[str, tuple[int, ...]] | None = None,
    close_failure: bool = False,
):
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    by_name = {
        shard["path"]: tuple(shard["bodies"])
        for shard in payload["shards"]
    }

    def _open(path: Path):
        if path.name == fail_name:
            raise OSError(f"synthetic open failure for {path.name}")
        bodies = (
            body_override.get(path.name, by_name[path.name])
            if body_override is not None
            else by_name[path.name]
        )
        return _FakeSmallBodyReader(
            path,
            bodies,
            close_log=close_log,
            close_failure=close_failure,
        )

    return _open


def _admit(
    manifest_paths,
    *,
    verify_release=None,
    reader_factory=None,
    native_catalog_available: bool = True,
    native_segment_types=(2, 3, 13),
):
    manifests = list(manifest_paths)
    first = manifests[0] if manifests else None
    return admit_small_body_manifests(
        manifests,
        verify_release=(
            verify_release
            if verify_release is not None
            else lambda root: _verification_for(root / "manifest.json")
        ),
        reader_factory=(
            reader_factory
            if reader_factory is not None
            else _reader_factory(first)
        ),
        native_catalog_available=native_catalog_available,
        native_segment_types=native_segment_types,
    )


def test_requirement_is_immutable_and_explicit() -> None:
    requirement = SmallBodyManifestRequirement()
    assert requirement.require_release_integrity is True
    assert requirement.require_native_catalog is True
    assert requirement.require_native_segments is True
    assert requirement.allowed_segment_types == frozenset({2, 3, 13})
    with pytest.raises(FrozenInstanceError):
        requirement.require_release_integrity = False


def test_no_manifest_is_a_terminal_named_skip() -> None:
    calls = []
    admission = admit_small_body_manifests(
        (),
        verify_release=lambda root: calls.append(("verify", root)),
        reader_factory=lambda path: calls.append(("open", path)),
        native_catalog_available=True,
        native_segment_types=(2, 3, 13),
    )
    assert admission.readers == ()
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.SKIP
    )
    assert admission.receipt.terminal is True
    assert "no released sovereign" in admission.receipt.reason
    assert calls == []


def test_missing_manifest_is_failure_not_availability(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "absent" / "manifest.json"
    admission = _admit(
        [missing],
        verify_release=lambda root: pytest.fail("verifier called"),
        reader_factory=lambda path: pytest.fail("reader opened"),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert admission.receipt.failure_type == "SmallBodyResourceContractError"
    assert "cannot read ambient manifest" in admission.receipt.reason


def test_malformed_manifest_is_terminal_failure(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{", encoding="utf-8")
    admission = _admit(
        [manifest],
        verify_release=lambda root: pytest.fail("verifier called"),
        reader_factory=lambda path: pytest.fail("reader opened"),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "cannot read ambient manifest" in admission.receipt.reason


def test_build_or_legacy_manifest_is_rejected_before_verifier_and_open(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path, released=False)
    calls = []
    admission = _admit(
        [manifest],
        verify_release=lambda root: calls.append(("verify", root)),
        reader_factory=lambda path: calls.append(("open", path)),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "build/legacy" in admission.receipt.reason
    assert calls == []


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        (("release", "source_revision"), "", "source_revision"),
        (
            ("release", "source_manifest_sha256"),
            "not-a-digest",
            "source_manifest_sha256",
        ),
        (
            ("release", "integrity", "algorithm"),
            "sha1",
            "algorithm",
        ),
        (
            ("release", "integrity", "receipt"),
            "OTHER",
            "SHA256SUMS",
        ),
    ),
)
def test_release_source_and_integrity_identity_are_mandatory(
    tmp_path: Path,
    path: tuple[str, ...],
    value: str,
    message: str,
) -> None:
    manifest = _write_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    admission = _admit([manifest])
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert message in admission.receipt.reason


def test_release_verifier_failure_prevents_open(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    opens = []

    def _fail_verify(root):
        raise ValueError("synthetic checksum mismatch")

    admission = _admit(
        [manifest],
        verify_release=_fail_verify,
        reader_factory=lambda path: opens.append(path),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "synthetic checksum mismatch" in admission.receipt.reason
    assert opens == []


def test_release_verifier_identity_mismatch_prevents_open(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    verification = _verification_for(manifest)
    verification.manifest_sha256 = "f" * 64
    opens = []
    admission = _admit(
        [manifest],
        verify_release=lambda root: verification,
        reader_factory=lambda path: opens.append(path),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "manifest_sha256 mismatch" in admission.receipt.reason
    assert opens == []


def test_success_records_release_and_opened_descriptor_truth(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path,
        ((2_000_001, 2_000_002), (2_000_003,)),
    )
    admission = _admit(
        [manifest],
        reader_factory=_reader_factory(manifest),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.RUN
    )
    assert admission.receipt.terminal is False
    assert len(admission.readers) == 2
    capability = admission.receipt.capabilities[0]
    assert capability.manifest_path == manifest.resolve()
    assert capability.manifest_sha256 == hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    assert capability.manifest_schema == "moira.small-body-catalog/v1"
    assert capability.catalog_id == "test-asteroids"
    assert capability.catalog_version == "2026.07.30.1"
    assert capability.source_manifest_sha256 == "a" * 64
    assert capability.source_revision == "test-revision"
    assert capability.integrity_algorithm == "sha256"
    assert capability.integrity_receipt == "SHA256SUMS"
    assert capability.shard_count == 2
    assert capability.bodies == (2_000_001, 2_000_002, 2_000_003)
    assert capability.segment_types == frozenset({13})
    assert capability.native_segment_types == frozenset({2, 3, 13})
    assert capability.frames == frozenset({1})
    assert len(capability.coverage) == 3
    assert close_small_body_readers(admission.readers) == ()


def _reader_factory_from_each_manifest():
    def _open(path: Path):
        payload = json.loads(
            (path.parent / "manifest.json").read_text(encoding="utf-8")
        )
        by_name = {
            shard["path"]: tuple(shard["bodies"])
            for shard in payload["shards"]
        }
        return _FakeSmallBodyReader(path, by_name[path.name])

    return _open


def test_distinct_catalogs_may_share_body_ids(tmp_path: Path) -> None:
    wheel = _write_manifest(
        tmp_path / "wheel",
        ((2_000_001, 2_000_060),),
        catalog_id="moira-asteroids-wheel",
    )
    full = _write_manifest(
        tmp_path / "full",
        ((2_000_001, 2_000_060, 2_009_377),),
        catalog_id="moira-asteroids",
    )
    admission = _admit(
        [full, wheel],
        reader_factory=_reader_factory_from_each_manifest(),
    )
    assert (
        admission.receipt.disposition is SmallBodyResourceDisposition.RUN
    )
    assert len(admission.receipt.capabilities) == 2
    assert admission.receipt.capabilities[0].catalog_id == "moira-asteroids"
    assert (
        admission.receipt.capabilities[1].catalog_id
        == "moira-asteroids-wheel"
    )
    shared = set(admission.receipt.capabilities[0].bodies).intersection(
        admission.receipt.capabilities[1].bodies
    )
    assert shared == {2_000_001, 2_000_060}
    assert close_small_body_readers(admission.readers) == ()


def test_duplicate_catalog_release_identity_is_still_rejected(
    tmp_path: Path,
) -> None:
    first = _write_manifest(tmp_path / "a", ((2_000_001,),))
    second = _write_manifest(tmp_path / "b", ((2_000_002,),))
    admission = _admit(
        [first, second],
        reader_factory=_reader_factory_from_each_manifest(),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "duplicate catalog release identity" in admission.receipt.reason


def test_opened_body_mismatch_closes_the_reader(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    close_log = []
    admission = _admit(
        [manifest],
        reader_factory=_reader_factory(
            manifest,
            close_log=close_log,
            body_override={"shard-0.bsp": (2_999_999,)},
        ),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "body mismatch" in admission.receipt.reason
    assert admission.readers == ()
    assert close_log == ["shard-0.bsp"]


def test_later_open_failure_closes_every_previously_opened_reader(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path,
        ((2_000_001,), (2_000_002,)),
    )
    close_log = []
    admission = _admit(
        [manifest],
        reader_factory=_reader_factory(
            manifest,
            close_log=close_log,
            fail_name="shard-1.bsp",
        ),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "synthetic open failure" in admission.receipt.reason
    assert admission.readers == ()
    assert close_log == ["shard-0.bsp"]


def test_capability_construction_failure_closes_every_opened_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _write_manifest(
        tmp_path,
        ((2_000_001,), (2_000_002,)),
    )
    close_log = []

    def _fail_capability(**kwargs):
        raise ValueError("synthetic capability construction failure")

    monkeypatch.setattr(
        small_body_policy,
        "SmallBodyManifestCapability",
        _fail_capability,
    )
    admission = _admit(
        [manifest],
        reader_factory=_reader_factory(
            manifest,
            close_log=close_log,
        ),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "synthetic capability construction failure" in (
        admission.receipt.reason
    )
    assert close_log == ["shard-1.bsp", "shard-0.bsp"]


def test_manifest_shard_path_may_not_escape_release_root(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path / "release")
    escaped = tmp_path / "escaped.bsp"
    escaped.write_bytes(b"x")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["shards"][0]["path"] = "../escaped.bsp"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    admission = _admit([manifest])
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "stay beneath the release root" in admission.receipt.reason


def test_partial_close_failure_is_visible_in_failure_receipt(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path,
        ((2_000_001,), (2_000_002,)),
    )
    admission = _admit(
        [manifest],
        reader_factory=_reader_factory(
            manifest,
            fail_name="shard-1.bsp",
            close_failure=True,
        ),
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert "partial-reader close failures" in admission.receipt.reason


@pytest.mark.parametrize(
    ("native_catalog", "native_types", "message"),
    (
        (False, (2, 3, 13), "native DAF catalog"),
        (True, (2, 3), "lacks native evaluator"),
    ),
)
def test_native_capability_is_required(
    tmp_path: Path,
    native_catalog: bool,
    native_types: tuple[int, ...],
    message: str,
) -> None:
    manifest = _write_manifest(tmp_path)
    admission = _admit(
        [manifest],
        native_catalog_available=native_catalog,
        native_segment_types=native_types,
    )
    assert (
        admission.receipt.disposition
        is SmallBodyResourceDisposition.FAILURE
    )
    assert message in admission.receipt.reason


def test_terminal_receipt_records_successful_teardown(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    admission = _admit([manifest])
    terminal = terminalize_small_body_receipt(admission.receipt)
    assert terminal.disposition is SmallBodyResourceDisposition.RUN
    assert terminal.terminal is True
    assert terminal.identities == admission.receipt.identities
    assert "all owned supplemental readers closed" in terminal.reason
    assert close_small_body_readers(admission.readers) == ()


def test_terminal_receipt_promotes_close_failure_to_failure(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    admission = _admit([manifest])
    terminal = terminalize_small_body_receipt(
        admission.receipt,
        close_failures=("reader[0] OSError: synthetic",),
    )
    assert terminal.disposition is SmallBodyResourceDisposition.FAILURE
    assert terminal.failure_type == "ReaderTeardownError"
    assert terminal.terminal is True
    assert terminal.capabilities == admission.receipt.capabilities
    assert close_small_body_readers(admission.readers) == ()


def test_live_pool_failure_preserves_capability_and_close_failures(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    admission = _admit([manifest])
    failure = fail_small_body_live_receipt(
        admission.receipt,
        stage="KernelPool construction",
        exc=RuntimeError("synthetic pool failure"),
        close_failures=("reader[0] OSError: synthetic close",),
    )
    assert failure.disposition is SmallBodyResourceDisposition.FAILURE
    assert failure.failure_type == "RuntimeError"
    assert failure.terminal is True
    assert failure.capabilities == admission.receipt.capabilities
    assert "KernelPool construction" in failure.reason
    assert "synthetic close" in failure.reason
    assert close_small_body_readers(admission.readers) == ()


def test_report_preserves_full_capability_and_rejects_contradiction(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    admission = _admit([manifest])
    terminal = terminalize_small_body_receipt(admission.receipt)
    report = small_body_report_from_receipts({"worker-node": terminal})
    detail = report["details"]["worker-node"]
    capability = detail["capabilities"][0]
    assert capability["manifest_path"] == str(manifest.resolve())
    assert capability["bodies"] == [2_000_001]
    assert capability["coverage"] == [
        [10, 2_000_001, 2_400_000.5, 2_500_000.5]
    ]
    assert report["summary"]["terminal"] == 1
    assert report["summary"]["manifests"] == 1
    assert report["summary"]["shards"] == 1
    assert report["summary"]["bodies"] == 1

    contradictory = dict(report)
    contradictory["summary"] = dict(report["summary"])
    contradictory["summary"]["bodies"] = 0
    with pytest.raises(
        SmallBodyResourceContractError,
        match="contradictory",
    ):
        merge_small_body_report(
            empty_small_body_report(),
            contradictory,
            source="worker",
        )
    assert close_small_body_readers(admission.readers) == ()


def test_xdist_merge_retains_identical_worker_receipt_details(
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path)
    admission = _admit([manifest])
    terminal = terminalize_small_body_receipt(admission.receipt)
    worker = small_body_report_from_receipts(
        {"<session:small-body-reader-pool>": terminal}
    )
    combined = empty_small_body_report()
    merge_small_body_report(combined, worker, source="worker gw0")
    merge_small_body_report(combined, worker, source="worker gw1")
    assert combined["summary"]["receipts"] == 2
    assert combined["summary"]["run"] == 2
    assert combined["summary"]["terminal"] == 2
    assert len(combined["details"]) == 2
    assert any("worker gw1" in key for key in combined["details"])
    assert close_small_body_readers(admission.readers) == ()


_FAKE_SPK_READER = """\
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import json
import os


_open_count = 0


def _log(value):
    path = os.environ.get("FAKE_READER_LOG")
    if path:
        with Path(path).open("a", encoding="utf-8") as stream:
            stream.write(value + "\\n")


class SpkReader:
    def __init__(self, path):
        global _open_count
        _open_count += 1
        fail_after = os.environ.get("FAKE_PRIMARY_FAIL_AFTER")
        if fail_after is not None and _open_count > int(fail_after):
            raise OSError("synthetic live primary acquisition failure")
        self._path = Path(path)
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        self._kernel_identity = SimpleNamespace(
            summary_label=payload.get("summary", "DE-0441LE-0441"),
            planetary_ephemeris=payload.get("identity", "DE441"),
            lunar_ephemeris="LE441",
        )
        self._kernel = SimpleNamespace(
            catalog={"native": True},
            segments=[
                SimpleNamespace(
                    target=10,
                    center=0,
                    frame=1,
                    data_type=2,
                    start_jd=1000.0,
                    end_jd=3000.0,
                )
            ],
        )
        _log("open-primary")

    @property
    def path(self):
        return self._path

    def close(self):
        _log("close-primary")


def _planetary_kernel_native_supported(catalog):
    return bool(catalog.get("native"))


class KernelPool:
    def __init__(self, readers):
        if os.environ.get("FAKE_POOL_CONSTRUCTION_FAILURE") == "1":
            raise OSError("synthetic KernelPool construction failure")
        self._readers = list(readers)


@contextmanager
def use_reader_override(reader):
    yield
"""

_FAKE_SMALL_BODY = """\
from pathlib import Path
from types import SimpleNamespace
import json
import os


_HAS_NATIVE_DAF = True
_HAS_NATIVE_SEGMENTS = True
_HAS_NATIVE_TYPE13 = True


def _log(value):
    path = os.environ.get("FAKE_READER_LOG")
    if path:
        with Path(path).open("a", encoding="utf-8") as stream:
            stream.write(value + "\\n")


class SmallBodyKernel:
    def __init__(self, path):
        self._path = Path(path)
        if os.environ.get("FAKE_SMALL_BODY_OPEN_FAILURE") == self._path.name:
            raise OSError("synthetic small-body open failure")
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        bodies = payload["bodies"]
        self._catalog = {"native": True}
        self._kernel = SimpleNamespace(
            segments=[
                SimpleNamespace(
                    target=body,
                    center=10,
                    frame=1,
                    data_type=13,
                    start_jd=2400000.5,
                    end_jd=2500000.5,
                )
                for body in bodies
            ]
        )
        _log("open-small:" + self._path.name)

    def close(self):
        _log("close-small:" + self._path.name)
        if os.environ.get("FAKE_SMALL_BODY_CLOSE_FAILURE") == self._path.name:
            raise OSError("synthetic small-body close failure")
"""

_FAKE_KERNEL_PATHS = """\
from pathlib import Path
import os


def find_planetary_kernel():
    value = os.environ.get("FAKE_PLANETARY_KERNEL")
    return None if value is None else Path(value)


def find_all_small_body_manifests():
    if os.environ.get("FAKE_MANIFEST_DISCOVERY_FAILURE") == "1":
        raise OSError("synthetic manifest discovery failure")
    value = os.environ.get("FAKE_SMALL_BODY_MANIFESTS", "")
    return [Path(item) for item in value.split(os.pathsep) if item]
"""

_FAKE_RELEASE = """\
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json


def verify_release(root):
    root = Path(root).resolve()
    manifest = root / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("integrity_failure"):
        raise ValueError("synthetic release integrity failure")
    return SimpleNamespace(
        root=root,
        catalog_id=payload["catalog_id"],
        catalog_version=payload["catalog_version"],
        shard_count=payload["shard_count"],
        body_count=payload["body_count"],
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    )
"""


def _make_harness_project(
    pytester: pytest.Pytester,
    source: str,
) -> tuple[Path, Path]:
    mini_tests = pytester.path / "tests"
    mini_tests.mkdir()
    support = mini_tests / "support"
    support.mkdir()
    support.joinpath("__init__.py").write_text("", encoding="utf-8")
    support.joinpath("resource_policy.py").write_text(
        _PLANETARY_POLICY_SOURCE,
        encoding="utf-8",
    )
    support.joinpath("small_body_resource_policy.py").write_text(
        _SMALL_BODY_POLICY_SOURCE,
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
    pytester.path.joinpath("pytest.ini").write_text(
        _PYTEST_CONFIG,
        encoding="utf-8",
    )

    fake_moira = pytester.path / "moira"
    fake_moira.mkdir()
    fake_moira.joinpath("__init__.py").write_text("", encoding="utf-8")
    fake_moira.joinpath("spk_reader.py").write_text(
        _FAKE_SPK_READER,
        encoding="utf-8",
    )
    fake_moira.joinpath("_spk_body_kernel.py").write_text(
        _FAKE_SMALL_BODY,
        encoding="utf-8",
    )
    fake_moira.joinpath("_kernel_paths.py").write_text(
        _FAKE_KERNEL_PATHS,
        encoding="utf-8",
    )
    fake_moira.joinpath("small_body_catalog_release.py").write_text(
        _FAKE_RELEASE,
        encoding="utf-8",
    )
    planetary = pytester.path / "planetary.bsp"
    planetary.write_text(
        '{"identity":"DE441","summary":"DE-0441LE-0441"}',
        encoding="utf-8",
    )
    log = pytester.path / "readers.log"
    return planetary, log


def _write_harness_manifest(
    pytester: pytest.Pytester,
    *,
    released: bool = True,
    two_shards: bool = False,
) -> Path:
    root = pytester.path / "small-body-release"
    shard_bodies = (
        ((2_000_001,), (2_000_002,))
        if two_shards
        else ((2_000_001,),)
    )
    manifest = _write_manifest(
        root,
        shard_bodies,
        released=released,
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for shard in payload["shards"]:
        root.joinpath(shard["path"]).write_text(
            json.dumps({"bodies": shard["bodies"]}),
            encoding="utf-8",
        )
    return manifest


def _run_harness(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    *args: str,
    environment: dict[str, str],
) -> pytest.RunResult:
    for key in (
        "FAKE_PLANETARY_KERNEL",
        "FAKE_READER_LOG",
        "FAKE_SMALL_BODY_MANIFESTS",
        "FAKE_SMALL_BODY_OPEN_FAILURE",
        "FAKE_SMALL_BODY_CLOSE_FAILURE",
        "FAKE_PRIMARY_FAIL_AFTER",
        "FAKE_POOL_CONSTRUCTION_FAILURE",
        "FAKE_MANIFEST_DISCOVERY_FAILURE",
        "MOIRA_KERNEL_PATH",
        "MOIRA_NO_DOWNLOAD",
        "MOIRA_TEST_MODE",
        "MOIRA_STRICT_KNOWN_ISSUES",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("MOIRA_NO_DOWNLOAD", "1")
    monkeypatch.setenv("MOIRA_TEST_MODE", "1")
    monkeypatch.setenv("MOIRA_STRICT_KNOWN_ISSUES", "1")
    return pytester.runpytest_subprocess(*args)


def _combined_output(result: pytest.RunResult) -> str:
    return result.stdout.str() + "\n" + result.stderr.str()


def _summary_line(result: pytest.RunResult) -> str:
    lines = [
        line.strip()
        for line in _combined_output(result).splitlines()
        if line.strip().startswith(
            "Supplemental small-body resource:"
        )
    ]
    assert len(lines) == 1, lines
    return lines[0]


def test_pytester_missing_manifest_is_named_skip_with_terminal_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planetary, log = _make_harness_project(
        pytester,
        """
        def test_needs_small_body(small_body_reader_pool):
            raise AssertionError("body must not execute")
        """,
    )
    result = _run_harness(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "FAKE_PLANETARY_KERNEL": str(planetary),
            "MOIRA_KERNEL_PATH": str(planetary),
            "FAKE_READER_LOG": str(log),
        },
    )
    result.assert_outcomes(skipped=1)
    assert _summary_line(result).startswith(
        "Supplemental small-body resource: receipts=1, run=0, "
        "skip=1, failure=0, terminal=1"
    )
    assert log.read_text(encoding="utf-8").splitlines() == [
        "open-primary",
        "close-primary",
        "open-primary",
        "close-primary",
    ]


def test_pytester_success_receipt_is_terminal_after_owned_teardown(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planetary, log = _make_harness_project(
        pytester,
        """
        def test_pool(small_body_reader_pool):
            assert len(small_body_reader_pool._readers) == 2
        """,
    )
    manifest = _write_harness_manifest(pytester)
    result = _run_harness(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "FAKE_PLANETARY_KERNEL": str(planetary),
            "MOIRA_KERNEL_PATH": str(planetary),
            "FAKE_READER_LOG": str(log),
            "FAKE_SMALL_BODY_MANIFESTS": str(manifest),
        },
    )
    result.assert_outcomes(passed=1)
    line = _summary_line(result)
    assert "receipts=1, run=1, skip=0, failure=0, terminal=1" in line
    assert "manifests=1, shards=1, bodies=1" in line
    assert "test-asteroids@2026.07.30.1:" in line
    assert log.read_text(encoding="utf-8").splitlines() == [
        "open-primary",
        "close-primary",
        "open-primary",
        "open-small:shard-0.bsp",
        "open-primary",
        "close-primary",
        "close-small:shard-0.bsp",
        "close-primary",
    ]


@pytest.mark.parametrize(
    ("released", "open_failure", "expected"),
    (
        (False, None, "build/legacy"),
        (True, "shard-1.bsp", "synthetic small-body open failure"),
    ),
)
def test_pytester_unreleased_and_partial_open_are_terminal_failures(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    released: bool,
    open_failure: str | None,
    expected: str,
) -> None:
    planetary, log = _make_harness_project(
        pytester,
        """
        def test_pool(small_body_reader_pool):
            raise AssertionError("body must not execute")
        """,
    )
    manifest = _write_harness_manifest(
        pytester,
        released=released,
        two_shards=open_failure is not None,
    )
    environment = {
        "FAKE_PLANETARY_KERNEL": str(planetary),
        "MOIRA_KERNEL_PATH": str(planetary),
        "FAKE_READER_LOG": str(log),
        "FAKE_SMALL_BODY_MANIFESTS": str(manifest),
    }
    if open_failure is not None:
        environment["FAKE_SMALL_BODY_OPEN_FAILURE"] = open_failure
    result = _run_harness(
        pytester,
        monkeypatch,
        "-q",
        environment=environment,
    )
    result.assert_outcomes(errors=1)
    output = _combined_output(result)
    assert expected in output
    assert "disposition=failure" in output
    assert "terminal=True" in output
    assert "failure=1, terminal=1" in _summary_line(result)
    if open_failure is not None:
        log_lines = log.read_text(encoding="utf-8").splitlines()
        assert "open-small:shard-0.bsp" in log_lines
        assert "close-small:shard-0.bsp" in log_lines


def test_pytester_teardown_failure_replaces_run_with_terminal_failure(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planetary, log = _make_harness_project(
        pytester,
        """
        def test_pool(small_body_reader_pool):
            assert len(small_body_reader_pool._readers) == 2
        """,
    )
    manifest = _write_harness_manifest(pytester)
    result = _run_harness(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "FAKE_PLANETARY_KERNEL": str(planetary),
            "MOIRA_KERNEL_PATH": str(planetary),
            "FAKE_READER_LOG": str(log),
            "FAKE_SMALL_BODY_MANIFESTS": str(manifest),
            "FAKE_SMALL_BODY_CLOSE_FAILURE": "shard-0.bsp",
        },
    )
    result.assert_outcomes(passed=1, errors=1)
    output = _combined_output(result)
    assert "ReaderTeardownError" in output
    assert "run=0, skip=0, failure=1, terminal=1" in _summary_line(
        result
    )


def test_pytester_primary_live_open_failure_records_planetary_failure(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planetary, log = _make_harness_project(
        pytester,
        """
        def test_pool(small_body_reader_pool):
            raise AssertionError("body must not execute")
        """,
    )
    manifest = _write_harness_manifest(pytester)
    result = _run_harness(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "FAKE_PLANETARY_KERNEL": str(planetary),
            "MOIRA_KERNEL_PATH": str(planetary),
            "FAKE_READER_LOG": str(log),
            "FAKE_SMALL_BODY_MANIFESTS": str(manifest),
            "FAKE_PRIMARY_FAIL_AFTER": "1",
        },
    )
    result.assert_outcomes(errors=1)
    output = _combined_output(result)
    assert "synthetic live primary acquisition failure" in output
    planetary_lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip().startswith("Planetary resource:")
    ]
    assert len(planetary_lines) == 1
    assert "failure=1" in planetary_lines[0]
    assert "planetary-kernel-live: disposition=failure" in output


def test_pytester_pool_construction_failure_records_supplemental_failure(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planetary, log = _make_harness_project(
        pytester,
        """
        def test_pool(small_body_reader_pool):
            raise AssertionError("body must not execute")
        """,
    )
    manifest = _write_harness_manifest(pytester)
    result = _run_harness(
        pytester,
        monkeypatch,
        "-q",
        environment={
            "FAKE_PLANETARY_KERNEL": str(planetary),
            "MOIRA_KERNEL_PATH": str(planetary),
            "FAKE_READER_LOG": str(log),
            "FAKE_SMALL_BODY_MANIFESTS": str(manifest),
            "FAKE_POOL_CONSTRUCTION_FAILURE": "1",
        },
    )
    result.assert_outcomes(errors=1)
    output = _combined_output(result)
    assert "synthetic KernelPool construction failure" in output
    assert "KernelPool construction failed after supplemental admission" in (
        output
    )
    assert "run=0, skip=0, failure=1, terminal=1" in _summary_line(
        result
    )
    assert "close-small:shard-0.bsp" in log.read_text(
        encoding="utf-8"
    ).splitlines()


def test_pytester_xdist_preserves_each_worker_terminal_receipt(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planetary, log = _make_harness_project(
        pytester,
        """
        def test_first(small_body_reader_pool):
            assert len(small_body_reader_pool._readers) == 2


        def test_second(small_body_reader_pool):
            assert len(small_body_reader_pool._readers) == 2
        """,
    )
    manifest = _write_harness_manifest(pytester)
    result = _run_harness(
        pytester,
        monkeypatch,
        "-n",
        "2",
        "--dist=load",
        "-q",
        environment={
            "FAKE_PLANETARY_KERNEL": str(planetary),
            "MOIRA_KERNEL_PATH": str(planetary),
            "FAKE_READER_LOG": str(log),
            "FAKE_SMALL_BODY_MANIFESTS": str(manifest),
        },
    )
    result.assert_outcomes(passed=2)
    line = _summary_line(result)
    assert "receipts=2, run=2, skip=0, failure=0, terminal=2" in line
    assert "manifests=1" in line

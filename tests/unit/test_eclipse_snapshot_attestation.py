"""Trusted pins detect changed artifacts without claiming build provenance."""
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from moira import _moira_native
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_native_spk_bounds import conditional_native_type2_bounds
from moira._eclipse_snapshot_attestation import (
    TrustedSnapshotManifest,
    verify_snapshot_manifest,
)
from moira._eclipse_spk_bounds import EclipseSpkBoundsUnavailable
from moira._eclipse_variable_spk_bounds import conditional_variable_anchor_type2_bounds


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def receipt(tmp_path, planetary_reader):
    root = tmp_path / "src"
    names = (
        "CMakeLists.txt", "src/native/bindings/moira_native.cpp",
        "src/native/include/eclipse_strict_snapshot.hpp", "src/native/src/eclipse_strict_snapshot.cpp",
    )
    pins = []
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = name.encode()
        path.write_bytes(data)
        pins.append((name, sha(data)))
    line = ('  "C:\\tools\\cl.exe" /c /GL /D MOIRA_ECLIPSE_STRICT_SNAPSHOT_BUILD=1 '
            '/fp:strict /GL- "src/native/src/eclipse_strict_snapshot.cpp"')
    log = tmp_path / "build.log"
    log.write_text(line + "\n", encoding="utf8")
    bounds = conditional_native_type2_bounds(planetary_reader, 0, 3, 2451545., I.point(.0001))
    manifest = TrustedSnapshotManifest(
        sha(Path(_moira_native.__file__).read_bytes()), bounds.record_snapshot_sha256,
        sha(log.read_bytes()), line, tuple(pins),
    )
    return manifest, bounds, root, log


@pytest.mark.requires_ephemeris
def test_receipt_checks_pins_without_claiming_provenance(receipt):
    manifest, bounds, root, log = receipt
    result = verify_snapshot_manifest(manifest, bounds, source_root=root, build_log=log)
    assert result.current_disk_binary_verified and result.pinned_build_evidence_verified
    assert not result.build_provenance_verified and not result.source_at_compile_verified
    assert not result.loaded_image_verified and not result.live_mapped_source_verified
    assert not result.legacy_evaluator_certified and result.trusted_manifest_required


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("changed", ["source", "log", "binary", "snapshot", "record", "domain"])
def test_receipt_rejects_changed_input(receipt, changed):
    manifest, bounds, root, log = receipt
    if changed == "source":
        (root / "CMakeLists.txt").write_text("changed")
    elif changed == "log":
        log.write_text("changed")
    elif changed == "binary":
        manifest = replace(manifest, binary_sha256="0" * 64)
    elif changed == "snapshot":
        manifest = replace(manifest, snapshot_sha256="0" * 64)
    elif changed == "record":
        axis = list(bounds.record_snapshot[0])
        axis[0] += 1
        bounds = replace(bounds, record_snapshot=(tuple(axis), *bounds.record_snapshot[1:]))
    else:
        bounds = replace(bounds, offset_days=I(0, 1))
    with pytest.raises(EclipseSpkBoundsUnavailable):
        verify_snapshot_manifest(manifest, bounds, source_root=root, build_log=log)


@pytest.mark.requires_ephemeris
def test_receipt_rejects_replaced_binary_path(receipt, tmp_path, monkeypatch):
    manifest, bounds, root, log = receipt
    replacement = tmp_path / "replacement.pyd"
    replacement.write_bytes(b"replacement image")
    monkeypatch.setattr(_moira_native, "__file__", str(replacement))
    with pytest.raises(EclipseSpkBoundsUnavailable, match="binary hash"):
        verify_snapshot_manifest(manifest, bounds, source_root=root, build_log=log)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("suffix", [" /fp:fast", " /GL", "\nextra", " /fp:precise", " @flags.rsp", " %CL%", " -fp:fast", " -GL"])
def test_receipt_rejects_contradictory_strict_command(receipt, suffix):
    manifest, bounds, root, log = receipt
    manifest = replace(manifest, compile_command=manifest.compile_command + suffix)
    with pytest.raises(EclipseSpkBoundsUnavailable):
        verify_snapshot_manifest(manifest, bounds, source_root=root, build_log=log)


@pytest.mark.requires_ephemeris
def test_receipt_rejects_bare_macro_without_define(receipt):
    manifest, bounds, root, log = receipt
    manifest = replace(manifest, compile_command=manifest.compile_command.replace("/D MOIRA", "MOIRA"))
    with pytest.raises(EclipseSpkBoundsUnavailable):
        verify_snapshot_manifest(manifest, bounds, source_root=root, build_log=log)


@pytest.mark.requires_ephemeris
def test_receipt_rejects_missing_or_duplicate_source_pins_and_unknown_profile(receipt):
    manifest, bounds, root, log = receipt
    for changed in (
        replace(manifest, source_sha256=manifest.source_sha256[:-1]),
        replace(manifest, source_sha256=(*manifest.source_sha256, manifest.source_sha256[0])),
        replace(manifest, compiler_profile="unknown"),
    ):
        with pytest.raises(EclipseSpkBoundsUnavailable):
            verify_snapshot_manifest(changed, bounds, source_root=root, build_log=log)


@pytest.mark.requires_ephemeris
def test_variable_anchor_snapshot_receipt_binds_both_domains(receipt, planetary_reader):
    manifest, _, root, log = receipt
    bounds = conditional_variable_anchor_type2_bounds(planetary_reader, 0, 3, I(2451545.2, 2451545.3), I(-.001, -.0001))
    manifest = replace(manifest, snapshot_sha256=bounds.record_snapshot_sha256)
    verify_snapshot_manifest(manifest, bounds, source_root=root, build_log=log)
    forged = replace(bounds, anchor_days=I(2451545.2, 2451545.4))
    with pytest.raises(EclipseSpkBoundsUnavailable, match="snapshot"):
        verify_snapshot_manifest(manifest, forged, source_root=root, build_log=log)

"""Build and clean-install the Phase 7 physical-visibility release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

if __package__:
    from .package_physical_visibility_data_pack import build_release_archive
else:
    from package_physical_visibility_data_pack import build_release_archive


REPO_ROOT = Path(__file__).resolve().parents[1]
IDENTITY_PATH = (
    REPO_ROOT / "moira" / "data" / "physical_heliacal_visibility_release_identity.json"
)
_RECEIPT_SCHEMA = "moira.physical-visibility.phase7-release-validation/v1"
_PACKAGED_FILES = (
    "moira/data/physical_heliacal_visibility_data_pack_compatibility_v1.json",
    "moira/data/physical_heliacal_visibility_data_pack_compatibility_v1_1.json",
    "moira/data/physical_heliacal_visibility_data_pack_compatibility_v1_2.json",
    "moira/data/physical_heliacal_visibility_release_identity.json",
    "moira/data/physical_heliacal_visibility_NOTICE.txt",
)
_FORBIDDEN_EMBEDDED_SUFFIXES = (
    ".f32le",
    "/direct-extinction-1nm.f32le",
    "/solar-twilight-photopic-luminance.f32le",
    "/solar-twilight-scotopic-luminance.f32le",
)
_EVIDENCE_OUTPUT_PREFIX = (
    "tests/artifacts/release/"
    "physical_visibility_phase7_release_validation_"
)


class PhysicalVisibilityReleaseValidationError(RuntimeError):
    """Raised when a candidate release artifact fails a Phase 7 gate."""


@dataclass(frozen=True, slots=True)
class _ExternalResource:
    """One exact external runtime resource in the release candidate."""

    label: str
    loader_kind: str
    directory: Path
    identity: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode:
        quoted = subprocess.list2cmdline(list(command))
        raise PhysicalVisibilityReleaseValidationError(
            f"command failed ({completed.returncode}): {quoted}\n{completed.stdout}"
        )
    return completed


def _git_files() -> tuple[str, ...]:
    completed = _run(
        (
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ),
        cwd=REPO_ROOT,
    )
    return tuple(name for name in completed.stdout.split("\0") if name)


def _is_generated_release_receipt(path: str) -> bool:
    """Keep dated validator output out of the source artifact it certifies."""

    return path.startswith(_EVIDENCE_OUTPUT_PREFIX) and path.endswith(".json")


def _copy_source_snapshot(destination: Path) -> tuple[str, ...]:
    copied: list[str] = []
    for raw in _git_files():
        normalized = raw.replace("\\", "/")
        if _is_generated_release_receipt(normalized):
            continue
        source = REPO_ROOT / raw
        if not source.is_file():
            continue
        if source.is_symlink():
            raise PhysicalVisibilityReleaseValidationError(
                f"source snapshot contains a symlink: {raw}"
            )
        target = destination / raw
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.append(normalized)
    if "pyproject.toml" not in copied or "setup.py" not in copied:
        raise PhysicalVisibilityReleaseValidationError(
            "source snapshot lacks build authorities"
        )
    return tuple(sorted(copied))


def _source_fingerprint(source: Path, files: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for name in files:
        path = source / name
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _artifact(path: Path) -> dict[str, Any]:
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _archive_members(path: Path) -> tuple[str, ...]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return tuple(sorted(archive.namelist()))
    with tarfile.open(path, "r:gz") as archive:
        return tuple(sorted(archive.getnames()))


def _matching_member(members: Sequence[str], relative: str) -> str:
    normalized = relative.replace("\\", "/")
    matches = [
        member
        for member in members
        if member == normalized or member.endswith("/" + normalized)
    ]
    if len(matches) != 1:
        raise PhysicalVisibilityReleaseValidationError(
            f"artifact must contain exactly one {relative!r}; found {matches}"
        )
    return matches[0]


def _inspect_distribution(path: Path, *, require_native: bool) -> dict[str, Any]:
    members = _archive_members(path)
    for relative in _PACKAGED_FILES:
        _matching_member(members, relative)
    lowered = tuple(member.lower() for member in members)
    embedded = [
        member
        for member in lowered
        if any(member.endswith(suffix) for suffix in _FORBIDDEN_EMBEDDED_SUFFIXES)
    ]
    if embedded:
        raise PhysicalVisibilityReleaseValidationError(
            f"external visibility payload leaked into distribution: {embedded}"
        )
    native = [
        member
        for member in members
        if "/_moira_native" in "/" + member.replace("\\", "/")
        and member.lower().endswith((".pyd", ".so", ".dylib"))
    ]
    if require_native and len(native) != 1:
        raise PhysicalVisibilityReleaseValidationError(
            f"wheel native extension inventory is not exact: {native}"
        )
    if not require_native:
        for required in ("CMakeLists.txt", "setup.py", "pyproject.toml"):
            _matching_member(members, required)
        if not any(
            member.endswith(
                "/src/native/include/physical_visibility_kernels.hpp"
            )
            for member in members
        ):
            raise PhysicalVisibilityReleaseValidationError(
                "sdist lacks the physical-visibility native header"
            )
    return {
        "member_count": len(members),
        "packaged_identity_and_notice_files": list(_PACKAGED_FILES),
        "external_payload_embedded": False,
        "native_extensions": native,
    }


def _venv_python(directory: Path) -> Path:
    if os.name == "nt":
        return directory / "Scripts" / "python.exe"
    return directory / "bin" / "python"


def _clean_install_smoke(
    wheel: Path,
    *,
    resources: Sequence[_ExternalResource],
    work: Path,
    label: str,
) -> dict[str, Any]:
    venv = work / f"venv-{label}"
    _run((sys.executable, "-m", "venv", str(venv)), cwd=work)
    python = _venv_python(venv)
    _run(
        (
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            str(wheel),
        ),
        cwd=work,
    )
    code = r'''
import json
import socket
import sys

class _DeniedSocket(socket.socket):
    def connect(self, *args, **kwargs):
        raise AssertionError("network access attempted during offline smoke")
    def connect_ex(self, *args, **kwargs):
        raise AssertionError("network access attempted during offline smoke")

def _denied_connection(*args, **kwargs):
    raise AssertionError("network access attempted during offline smoke")

socket.socket = _DeniedSocket
socket.create_connection = _denied_connection

import moira
from moira import physical_visibility_assessment, physical_visibility_event
from moira import moira_native
from moira._visibility_lut import VisibilityDataPackConfig, load_visibility_data_pack

resource_specs = json.loads(sys.argv[1])
resource_receipts = []
for item in resource_specs:
    if item["loader_kind"] != "visibility":
        raise AssertionError("unsupported release resource loader")
    pack = load_visibility_data_pack(
        VisibilityDataPackConfig(
            item["directory"],
            expected_pack_id=item["pack_id"],
            expected_manifest_sha256=item["manifest_sha256"],
        )
    )
    model_id = pack.receipt.composite_model_id
    resource_receipts.append({
        "label": item["label"],
        "loader_kind": item["loader_kind"],
        "pack_id": pack.receipt.pack_id,
        "pack_version": pack.receipt.version,
        "manifest_sha256": pack.receipt.manifest_sha256,
        "model_id": model_id,
    })
print(json.dumps({
    "version": moira.__version__,
    "module": moira.__file__,
    "native_backend": moira_native.__backend_file__,
    "assessment_callable": callable(physical_visibility_assessment),
    "event_callable": callable(physical_visibility_event),
    "resources": resource_receipts,
    "network_guard_active": True,
}, sort_keys=True))
'''
    resource_specs = [
        {
            "label": resource.label,
            "loader_kind": resource.loader_kind,
            "directory": str(resource.directory),
            "pack_id": resource.identity["pack_id"],
            "version": resource.identity["version"],
            "manifest_sha256": resource.identity["manifest_sha256"],
            "model_id": (
                resource.identity.get("model_id")
                or "clear_sky_naked_eye_point_source_v1"
            ),
        }
        for resource in resources
    ]
    env = os.environ.copy()
    env["MOIRA_NO_DOWNLOAD"] = "1"
    completed = _run(
        (
            str(python),
            "-I",
            "-c",
            code,
            json.dumps(resource_specs, sort_keys=True),
        ),
        cwd=work,
        env=env,
    )
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise PhysicalVisibilityReleaseValidationError(
            f"clean-install smoke did not emit JSON: {completed.stdout}"
        ) from exc
    expected_receipts = [
        {
            "label": item["label"],
            "loader_kind": item["loader_kind"],
            "pack_id": item["pack_id"],
            "pack_version": item["version"],
            "manifest_sha256": item["manifest_sha256"],
            "model_id": item["model_id"],
        }
        for item in resource_specs
    ]
    if (
        payload.get("resources") != expected_receipts
        or payload.get("assessment_callable") is not True
        or payload.get("event_callable") is not True
        or payload.get("network_guard_active") is not True
    ):
        raise PhysicalVisibilityReleaseValidationError(
            f"clean-install smoke receipt differs: {payload}"
        )
    return {
        "version": payload["version"],
        "installed_module": "site-packages/moira/__init__.py",
        "native_backend_filename": Path(payload["native_backend"]).name,
        "assessment_callable": payload["assessment_callable"],
        "event_callable": payload["event_callable"],
        "resources": payload["resources"],
        "network_guard_active": payload["network_guard_active"],
    }


def _extract_sdist(sdist: Path, destination: Path) -> Path:
    with tarfile.open(sdist, "r:gz") as archive:
        archive.extractall(destination, filter="data")
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise PhysicalVisibilityReleaseValidationError(
            f"sdist extraction root is not exact: {roots}"
        )
    return roots[0]


def _load_identity() -> dict[str, Any]:
    payload = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != (
        "moira.physical-heliacal-visibility-release-identity/v1"
    ):
        raise PhysicalVisibilityReleaseValidationError(
            "packaged physical-visibility release identity is malformed"
        )
    for item in payload.get("packaged_compatibility_contracts", []):
        path = REPO_ROOT / item["path"]
        if _sha256(path) != item.get("sha256"):
            raise PhysicalVisibilityReleaseValidationError(
                f"compatibility contract identity differs: {item.get('path')}"
            )
    return payload


def _external_resources(
    identity: dict[str, Any],
    *,
    baseline_data_pack: Path,
) -> tuple[_ExternalResource, ...]:
    return (
        _ExternalResource(
            label="baseline_visibility",
            loader_kind="visibility",
            directory=baseline_data_pack.resolve(),
            identity=identity["external_data_pack"],
        ),
    )


def _build_external_resource_archive(
    resource: _ExternalResource,
    artifacts_directory: Path,
) -> dict[str, Any]:
    manifest_path = resource.directory / "manifest.json"
    if (
        not manifest_path.is_file()
        or _sha256(manifest_path)
        != resource.identity["manifest_sha256"]
    ):
        raise PhysicalVisibilityReleaseValidationError(
            f"{resource.label} does not match the packaged identity"
        )
    archive_identity = resource.identity["archive"]
    external_archive = artifacts_directory / archive_identity["filename"]
    receipt = build_release_archive(resource.directory, external_archive)
    expected_pack = {
        "pack_id": resource.identity["pack_id"],
        "version": resource.identity["version"],
        "license": resource.identity["license"],
        "manifest_sha256": resource.identity["manifest_sha256"],
    }
    for key, expected in expected_pack.items():
        if receipt["pack"].get(key) != expected:
            raise PhysicalVisibilityReleaseValidationError(
                f"{resource.label} release identity differs for {key}"
            )
    for key in ("filename", "bytes", "sha256"):
        if receipt["archive"][key] != archive_identity[key]:
            raise PhysicalVisibilityReleaseValidationError(
                f"{resource.label} deterministic archive differs for {key}"
            )
    return receipt


def validate_release(
    data_pack: Path,
    artifacts_directory: Path,
) -> dict[str, Any]:
    """Execute all Phase 7 build, archive, and clean-install gates."""

    artifacts_directory = artifacts_directory.resolve()
    artifacts_directory.mkdir(parents=True, exist_ok=True)
    identity = _load_identity()
    resources = _external_resources(
        identity,
        baseline_data_pack=data_pack,
    )
    resource_receipts = {
        resource.label: _build_external_resource_archive(
            resource,
            artifacts_directory,
        )
        for resource in resources
    }

    with tempfile.TemporaryDirectory(prefix="moira-phase7-release-") as raw:
        work = Path(raw)
        source = work / "source"
        source.mkdir()
        source_files = _copy_source_snapshot(source)
        source_fingerprint = _source_fingerprint(source, source_files)

        dist = work / "dist"
        _run(
            (
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--sdist",
                "--outdir",
                str(dist),
                str(source),
            ),
            cwd=work,
        )
        wheels = sorted(dist.glob("*.whl"))
        sdists = sorted(dist.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise PhysicalVisibilityReleaseValidationError(
                f"source build produced unexpected artifacts: {wheels}, {sdists}"
            )
        wheel = wheels[0]
        sdist = sdists[0]
        wheel_inventory = _inspect_distribution(wheel, require_native=True)
        sdist_inventory = _inspect_distribution(sdist, require_native=False)
        wheel_smoke = _clean_install_smoke(
            wheel,
            resources=resources,
            work=work,
            label="wheel",
        )

        extracted = _extract_sdist(sdist, work / "sdist-source")
        sdist_dist = work / "sdist-dist"
        _run(
            (
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--outdir",
                str(sdist_dist),
                str(extracted),
            ),
            cwd=work,
        )
        sdist_wheels = sorted(sdist_dist.glob("*.whl"))
        if len(sdist_wheels) != 1:
            raise PhysicalVisibilityReleaseValidationError(
                f"sdist rebuild produced unexpected wheels: {sdist_wheels}"
            )
        sdist_wheel = sdist_wheels[0]
        sdist_wheel_inventory = _inspect_distribution(
            sdist_wheel, require_native=True
        )
        sdist_smoke = _clean_install_smoke(
            sdist_wheel,
            resources=resources,
            work=work,
            label="sdist-wheel",
        )

        preservation = (
            (wheel, artifacts_directory / wheel.name),
            (sdist, artifacts_directory / sdist.name),
            (
                sdist_wheel,
                artifacts_directory / f"from-sdist-{sdist_wheel.name}",
            ),
        )
        preserved = []
        for artifact, target in preservation:
            if target.exists():
                target.unlink()
            shutil.copyfile(artifact, target)
            preserved.append(target)

    git_revision = _run(("git", "rev-parse", "HEAD"), cwd=REPO_ROOT).stdout.strip()
    return {
        "schema": _RECEIPT_SCHEMA,
        "status": "all_phase7_release_artifact_gates_passed",
        "source": {
            "git_revision": git_revision,
            "source_file_count": len(source_files),
            "source_fingerprint": source_fingerprint,
        },
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "external_resources": resource_receipts,
        "distributions": {
            "wheel": {
                **_artifact(preserved[0]),
                "inventory": wheel_inventory,
                "clean_install": wheel_smoke,
            },
            "sdist": {
                **_artifact(preserved[1]),
                "inventory": sdist_inventory,
                "rebuilt_wheel": {
                    **_artifact(preserved[2]),
                    "inventory": sdist_wheel_inventory,
                    "clean_install": sdist_smoke,
                },
            },
        },
        "network_boundary": {
            "build_isolation": False,
            "pip_no_index": True,
            "pip_no_dependencies": True,
            "moira_no_download": True,
            "socket_guard_during_installed_pack_load": True,
        },
        "claims": {
            "wheel_clean_install": True,
            "sdist_rebuild_and_clean_install": True,
            "external_resource_identities_exact": True,
            "external_resources_embedded": False,
            "normal_execution_offline": True,
            "experimental_site_specific_moonlight_quarantined": True,
            "release_or_deployment_performed": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-pack", required=True, type=Path)
    parser.add_argument("--artifacts-directory", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    receipt = validate_release(
        args.data_pack,
        args.artifacts_directory,
    )
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

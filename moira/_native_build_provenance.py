"""Deterministic source identity for the compiled Moira native backend."""

from __future__ import annotations

import hashlib
from importlib.machinery import EXTENSION_SUFFIXES, ExtensionFileLoader
import json
import os
from pathlib import Path
import re
import shutil
import stat
from types import BuiltinFunctionType


_EXACT_BUILD_INPUTS = (
    "CMakeLists.txt",
    "moira/_native_build_provenance.py",
    "setup.py",
)
_NATIVE_BUILD_SUFFIXES = frozenset(
    {
        ".c",
        ".cc",
        ".cmake",
        ".cpp",
        ".cxx",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".in",
        ".inc",
        ".inl",
        ".ipp",
        ".ixx",
        ".tpp",
    }
)
_PYPROJECT_BUILD_SECTIONS = frozenset(
    {
        "build-system",
        "tool.setuptools",
        "tool.setuptools.package-data",
    }
)
_TOML_TABLE = re.compile(
    r"^\s*\[([A-Za-z0-9_.-]+)\]\s*(?:#.*)?$"
)
_BINARY_PROVENANCE_MARKER = re.compile(
    rb"MOIRA_NATIVE_BUILD_INPUT_MANIFEST_SHA256=([0-9a-f]{64})"
)
_WINDOWS_REPARSE_POINT = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_link_or_reparse(path: Path, status: os.stat_result) -> None:
    attributes = getattr(status, "st_file_attributes", 0)
    if stat.S_ISLNK(status.st_mode) or attributes & _WINDOWS_REPARSE_POINT:
        raise ValueError(f"native build input must not be a link or reparse point: {path}")


def _plain_path(root: Path, relative: str) -> tuple[Path, os.stat_result]:
    current = root
    status: os.stat_result | None = None
    for part in Path(relative).parts:
        current = current / part
        try:
            status = current.lstat()
        except OSError as exc:
            raise ValueError(f"native build input is unavailable: {current}") from exc
        _reject_link_or_reparse(current, status)
    assert status is not None
    return current, status


def _walk_plain_native_files(native_root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    pending = [native_root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError as exc:
            raise ValueError(
                f"native build directory cannot be inspected: {directory}"
            ) from exc
        for entry in children:
            path = Path(entry.path)
            try:
                status = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise ValueError(
                    f"native build input cannot be inspected: {path}"
                ) from exc
            _reject_link_or_reparse(path, status)
            if stat.S_ISDIR(status.st_mode):
                pending.append(path)
            elif stat.S_ISREG(status.st_mode):
                if path.suffix.casefold() in _NATIVE_BUILD_SUFFIXES:
                    files.append(path)
            else:
                raise ValueError(
                    f"native build tree contains an unsupported entry: {path}"
                )
    return tuple(sorted(files, key=lambda path: path.as_posix()))


def _build_input_paths(root: Path) -> tuple[Path, ...]:
    resolved_root = root.resolve(strict=True)
    candidates: list[Path] = []
    for relative in _EXACT_BUILD_INPUTS:
        path, status = _plain_path(resolved_root, relative)
        if not stat.S_ISREG(status.st_mode):
            raise ValueError(f"native build input is not a regular file: {path}")
        candidates.append(path)

    pyproject_path, pyproject_status = _plain_path(
        resolved_root,
        "pyproject.toml",
    )
    if not stat.S_ISREG(pyproject_status.st_mode):
        raise ValueError(
            f"native build input is not a regular file: {pyproject_path}"
        )
    candidates.append(pyproject_path)

    src_path, src_status = _plain_path(resolved_root, "src")
    if not stat.S_ISDIR(src_status.st_mode):
        raise ValueError(f"native source parent is not a directory: {src_path}")
    native_root, native_status = _plain_path(resolved_root, "src/native")
    if not stat.S_ISDIR(native_status.st_mode):
        raise ValueError(f"native source path is not a directory: {native_root}")
    candidates.extend(_walk_plain_native_files(native_root))

    if len(set(candidates)) != len(candidates):
        raise ValueError("native build input paths are not unique")
    return tuple(
        sorted(
            candidates,
            key=lambda path: path.relative_to(resolved_root).as_posix(),
        )
    )


def _pyproject_build_bytes(path: Path) -> bytes:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("pyproject.toml cannot be read as UTF-8") from exc
    sections: dict[str, list[str]] = {
        name: [] for name in _PYPROJECT_BUILD_SECTIONS
    }
    current: str | None = None
    seen: set[str] = set()
    for raw_line in source.splitlines():
        stripped = raw_line.strip()
        table = _TOML_TABLE.fullmatch(raw_line)
        if stripped.startswith("["):
            current = table.group(1) if table is not None else None
            if current in sections:
                if current in seen:
                    raise ValueError(
                        f"pyproject.toml repeats build table [{current}]"
                    )
                seen.add(current)
                sections[current].append(f"[{current}]")
            continue
        if current in sections and stripped and not stripped.startswith("#"):
            sections[current].append(raw_line.rstrip())
    missing = sorted(_PYPROJECT_BUILD_SECTIONS - seen)
    if missing:
        raise ValueError(
            "pyproject.toml omits required native build tables: "
            + ", ".join(missing)
        )
    canonical_lines: list[str] = []
    for section in sorted(sections):
        canonical_lines.extend(sections[section])
    return ("\n".join(canonical_lines) + "\n").encode("utf-8")


def native_build_input_manifest(root: Path) -> dict[str, object]:
    """Return the canonical manifest embedded into the native extension."""

    resolved_root = root.resolve(strict=True)
    inputs: list[dict[str, object]] = []
    for path in _build_input_paths(resolved_root):
        relative = path.relative_to(resolved_root).as_posix()
        if relative == "pyproject.toml":
            payload = _pyproject_build_bytes(path)
            hash_mode = "toml_build_sections_v1"
        else:
            payload = path.read_bytes()
            hash_mode = "raw_bytes"
        inputs.append(
            {
                "bytes": len(payload),
                "hash_mode": hash_mode,
                "path": relative,
                "sha256": _sha256_bytes(payload),
            }
        )
    unsigned = {"schema_version": 2, "inputs": inputs}
    canonical = (
        json.dumps(
            unsigned,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        + b"\n"
    )
    return {**unsigned, "sha256": _sha256_bytes(canonical)}


def stage_native_build_snapshot(
    source_root: Path,
    destination_root: Path,
    expected_manifest: dict[str, object],
) -> None:
    """Copy and verify the exact input snapshot that CMake will consume."""

    resolved_source = source_root.resolve(strict=True)
    if destination_root.exists():
        raise ValueError(
            f"native build snapshot destination already exists: {destination_root}"
        )
    destination_root.mkdir(parents=True)
    raw_inputs = expected_manifest.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ValueError("native build snapshot manifest is malformed")
    for raw_input in raw_inputs:
        if not isinstance(raw_input, dict):
            raise ValueError("native build snapshot input is malformed")
        relative = raw_input.get("path")
        if not isinstance(relative, str) or not relative:
            raise ValueError("native build snapshot path is malformed")
        source, status = _plain_path(resolved_source, relative)
        if not stat.S_ISREG(status.st_mode):
            raise ValueError(f"native build snapshot input is not a file: {source}")
        target = destination_root / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target, follow_symlinks=False)
    staged_manifest = native_build_input_manifest(destination_root)
    if staged_manifest != expected_manifest:
        raise ValueError(
            "native build snapshot differs from the manifest computed before staging"
        )


def native_backend_binary_identity(raw_backend: object) -> dict[str, object]:
    """Read immutable identity and the tagged provenance from the raw binary."""

    spec = getattr(raw_backend, "__spec__", None)
    loader = getattr(spec, "loader", None)
    module_loader = getattr(raw_backend, "__loader__", None)
    origin = getattr(spec, "origin", None)
    module_name = getattr(spec, "name", None)
    runtime_name = getattr(raw_backend, "__name__", None)
    module_file = getattr(raw_backend, "__file__", None)
    if (
        module_name != "moira._moira_native"
        or runtime_name != module_name
    ):
        raise ValueError("raw native backend has an unexpected module identity")
    if not isinstance(loader, ExtensionFileLoader):
        raise ValueError("raw native backend is not extension-loaded")
    if module_loader is not loader:
        raise ValueError("raw native backend loader contradicts its module spec")
    if not isinstance(origin, str) or not isinstance(module_file, str):
        raise ValueError("raw native backend omits its extension origin")
    loader_path_text = getattr(loader, "path", None)
    try:
        loader_filename = loader.get_filename(module_name)
    except (ImportError, OSError, TypeError, ValueError) as exc:
        raise ValueError("raw native backend loader filename is unavailable") from exc
    if not isinstance(loader_filename, str) or not isinstance(
        loader_path_text,
        str,
    ):
        raise ValueError("raw native backend loader omits its extension path")
    try:
        origin_path = Path(origin).resolve(strict=True)
        module_path = Path(module_file).resolve(strict=True)
        loader_filename_path = Path(loader_filename).resolve(strict=True)
        loader_path = Path(loader_path_text).resolve(strict=True)
    except OSError as exc:
        raise ValueError("raw native backend extension path is unavailable") from exc
    if origin_path != module_path:
        raise ValueError("raw native backend file contradicts its module spec")
    if loader_filename_path != origin_path:
        raise ValueError(
            "raw native backend loader filename contradicts its module origin"
        )
    if loader_path != loader_filename_path:
        raise ValueError(
            "raw native backend loader path contradicts its loader filename"
        )
    backend_text = str(loader_path).casefold()
    if not any(
        backend_text.endswith(suffix.casefold()) for suffix in EXTENSION_SUFFIXES
    ):
        raise ValueError("raw native backend origin lacks an extension suffix")

    try:
        with loader_path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("raw native backend is not a regular file")
            payload = stream.read()
            after = os.fstat(stream.fileno())
    except OSError as exc:
        raise ValueError("raw native backend cannot be read") from exc
    if (
        (before.st_size, before.st_mtime_ns)
        != (after.st_size, after.st_mtime_ns)
        or len(payload) != after.st_size
    ):
        raise ValueError("raw native backend changed while being identified")
    marker_digests = {
        match.decode("ascii") for match in _BINARY_PROVENANCE_MARKER.findall(payload)
    }
    if len(marker_digests) != 1:
        raise ValueError(
            "raw native backend must contain one unique build-provenance marker"
        )
    marker_digest = next(iter(marker_digests))
    marker_reader = getattr(raw_backend, "_build_provenance_marker", None)
    if (
        not isinstance(marker_reader, BuiltinFunctionType)
        or getattr(marker_reader, "__module__", None) != module_name
        or getattr(marker_reader, "__name__", None) != "_build_provenance_marker"
    ):
        raise ValueError(
            "raw native backend omits its built-in build-provenance marker"
        )
    loaded_marker = marker_reader()
    if loaded_marker != (
        "MOIRA_NATIVE_BUILD_INPUT_MANIFEST_SHA256=" + marker_digest
    ):
        raise ValueError(
            "loaded native backend provenance contradicts its binary marker"
        )
    return {
        "backend_loader": (
            f"{type(loader).__module__}.{type(loader).__qualname__}"
        ),
        "backend_loader_path": str(loader_path),
        "backend_module": module_name,
        "backend_path": str(loader_path),
        "backend_size": len(payload),
        "backend_sha256": _sha256_bytes(payload),
        "embedded_input_sha256": marker_digest,
    }


def native_build_provenance_identity(
    root: Path,
    embedded_sha256: object,
) -> dict[str, object]:
    """Compare one binary-embedded build digest with current build inputs."""

    embedded = embedded_sha256 if isinstance(embedded_sha256, str) else None
    try:
        current = native_build_input_manifest(root)
        manifest_error = None
    except Exception as exc:
        current = None
        manifest_error = f"{type(exc).__name__}: {exc}"

    embedded_valid = (
        isinstance(embedded, str)
        and len(embedded) == 64
        and all(character in "0123456789abcdef" for character in embedded)
    )
    errors: list[str] = []
    if not embedded_valid:
        errors.append("native extension omitted a valid build-input SHA-256")
    if manifest_error is not None:
        errors.append(manifest_error)
    current_sha256 = current.get("sha256") if current is not None else None
    matches = embedded_valid and embedded == current_sha256
    if embedded_valid and current is not None and not matches:
        errors.append("native extension build inputs differ from the current checkout")
    return {
        "schema_version": 2,
        "embedded_input_sha256": embedded,
        "current_input_manifest": current,
        "matches_current_inputs": matches,
        "error": "; ".join(errors) if errors else None,
    }

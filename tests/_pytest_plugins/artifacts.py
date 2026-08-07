"""Fail-closed artifact receipts and final report redaction."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib import import_module, metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
import uuid

import pytest

from ._common import _is_name_surrogate_reparse
from ._state import (
    ROOT_DIR,
    _ARTIFACT_DIR_KEY,
    _ARTIFACT_ITEM_SECRET_VALUES_KEY,
    _ARTIFACT_START_CONTEXT_KEY,
    _COVERAGE_RUNTIME_IDENTITY_KEY,
    _CONTROLLER_EVIDENCE_ERRORS_KEY,
    _EVIDENCE_PAYLOAD_KEY,
    _HARNESS_CONFIG_KEY,
    _LIFECYCLE_PAYLOAD_KEY,
    _RECEIPT_COLLECTOR_KEY,
    _SESSION_UTC_START_KEY,
    _XDIST_CLASSIFICATION_EXPECTED_STATE_KEY,
    _XDIST_COVERAGE_RUNTIME_ERRORS_STATE_KEY,
    _XDIST_COVERAGE_RUNTIME_REPORT_STATE_KEY,
    _XDIST_EVIDENCE_ERRORS_STATE_KEY,
    _HarnessConfig,
)
from .classification import (
    _classification_errors,
    _classification_receipt_for_summary,
    _is_xdist_worker,
    _serialize_classification_receipt,
    _xdist_mode,
)
from .lifecycle import _CASE_PHASES
from .resources import (
    _bind_planetary_content_digests,
    _combined_planetary_resource_report,
    _combined_small_body_resource_report,
)


_MAX_ARTIFACT_TEXT_CHARS = 64 * 1024


_EVIDENCE_REPORT_PROPERTY_NAMES = frozenset(
    {
        "moira_validation_claim_id",
        "moira_validation_contract_sha256",
    }
)


_XDIST_COVERAGE_RUNTIME_REPORT_KEY = "moira_coverage_runtime_v1"


_COVERAGE_ENVIRONMENT_NAMES = (
    "COVERAGE_CORE",
    "COVERAGE_FILE",
    "COVERAGE_FORCE_CONFIG",
    "COVERAGE_PROCESS_CONFIG",
    "COVERAGE_PROCESS_START",
    "COVERAGE_RCFILE",
)


_SECRET_NAME_RE = re.compile(
    r"(?i)(?:token|secret|password|passwd|api[_-]?key|authorization|"
    r"cookie|private[_-]?key|access[_-]?key|session[_-]?key)"
)


_HEADER_SECRET_RE = re.compile(
    r"(?im)\b(authorization|proxy-authorization|cookie|set-cookie|"
    r"x-api-key|api-key)\s*([:=])\s*([^\r\n,;}]+)"
)


_ASSIGNMENT_SECRET_RE = re.compile(
    r"(?im)\b([A-Za-z0-9_.-]*(?:token|secret|password|passwd|"
    r"api[_-]?key|private[_-]?key|access[_-]?key|session[_-]?key)"
    r"[A-Za-z0-9_.-]*)\s*(=|:(?!:))\s*([^\r\n,;}]+)"
)


_BEARER_SECRET_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


_URL_CREDENTIAL_RE = re.compile(
    r"(?i)\b(https?://)([^/\s:@]+):([^@\s/]+)@"
)


_SECRET_OPTION_RE = re.compile(
    r"(?i)^--?[A-Za-z0-9_.-]*(?:token|secret|password|passwd|"
    r"api[_-]?key|private[_-]?key|access[_-]?key|session[_-]?key)"
    r"[A-Za-z0-9_.-]*$"
)


def _secret_environment_values() -> tuple[str, ...]:
    values = {
        value
        for name, value in os.environ.items()
        if len(value) >= 4 and _SECRET_NAME_RE.search(name)
    }
    return tuple(sorted(values, key=len, reverse=True))


def _redact_text(
    value: object,
    *,
    secret_values: tuple[str, ...],
) -> tuple[str, bool]:
    try:
        text = str(value)
    except Exception as exc:
        text = f"<unprintable {type(value).__name__}: {type(exc).__name__}>"
    original = text
    for secret in secret_values:
        text = text.replace(secret, "[REDACTED]")
    text = _URL_CREDENTIAL_RE.sub(r"\1[REDACTED]@", text)
    text = _HEADER_SECRET_RE.sub(r"\1\2 [REDACTED]", text)
    text = _ASSIGNMENT_SECRET_RE.sub(r"\1\2 [REDACTED]", text)
    text = _BEARER_SECRET_RE.sub("Bearer [REDACTED]", text)
    truncated = False
    if len(text) > _MAX_ARTIFACT_TEXT_CHARS:
        omitted = len(text) - _MAX_ARTIFACT_TEXT_CHARS
        text = (
            text[:_MAX_ARTIFACT_TEXT_CHARS]
            + f"\n...[TRUNCATED {omitted} CHARACTERS]"
        )
        truncated = True
    return text, truncated or text != original


def _attach_artifact_report_shadow(
    report,
    *,
    secret_values: tuple[str, ...] | None = None,
) -> None:
    secret_values = tuple(
        sorted(
            set(secret_values or ())
            | set(_secret_environment_values()),
            key=len,
            reverse=True,
        )
    )
    longrepr, longrepr_changed = _redact_text(
        getattr(report, "longrepr", ""),
        secret_values=secret_values,
    )
    sections: list[tuple[str, str]] = []
    changed = longrepr_changed
    for raw_section in getattr(report, "sections", ()) or ():
        try:
            raw_name, raw_content = raw_section
        except (TypeError, ValueError):
            continue
        name, name_changed = _redact_text(
            raw_name,
            secret_values=secret_values,
        )
        content, content_changed = _redact_text(
            raw_content,
            secret_values=secret_values,
        )
        sections.append((name, content))
        changed = changed or name_changed or content_changed

    user_properties: list[tuple[object, object]] = []
    for raw_property in getattr(report, "user_properties", ()) or ():
        try:
            raw_name, raw_value = raw_property
        except (TypeError, ValueError):
            continue
        if isinstance(raw_value, str):
            safe_value, value_changed = _redact_text(
                raw_value,
                secret_values=secret_values,
            )
            changed = changed or value_changed
        else:
            safe_value = raw_value
        user_properties.append((raw_name, safe_value))

    raw_wasxfail = getattr(report, "wasxfail", None)
    if raw_wasxfail is None:
        wasxfail = None
    else:
        wasxfail, wasxfail_changed = _redact_text(
            raw_wasxfail,
            secret_values=secret_values,
        )
        changed = changed or wasxfail_changed
    report._moira_artifact_longrepr = longrepr
    report._moira_artifact_sections = sections
    report._moira_artifact_user_properties = user_properties
    report._moira_artifact_wasxfail = wasxfail
    report._moira_artifact_redacted = changed


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Attach the final redacted shadow after lifecycle policy has run."""
    report = yield
    artifact_secret_values = tuple(
        sorted(
            set(
                item.stash.get(
                    _ARTIFACT_ITEM_SECRET_VALUES_KEY,
                    (),
                )
            )
            | set(_secret_environment_values()),
            key=len,
            reverse=True,
        )
    )
    item.stash[_ARTIFACT_ITEM_SECRET_VALUES_KEY] = (
        artifact_secret_values
    )
    _attach_artifact_report_shadow(
        report,
        secret_values=artifact_secret_values,
    )
    return report


_ARTIFACT_SCHEMA_VERSION = 1


_ARTIFACT_FILENAMES = (
    "collection.json",
    "resources.json",
    "reports.jsonl",
    "failures.json",
    "durations.json",
    "rerun-nodeids.json",
)


_MAX_ARTIFACT_RECORD_BYTES = 256 * 1024


_MAX_ARTIFACT_RUN_BYTES = 16 * 1024 * 1024


_MAX_REPLAY_NODEID_CHARS = 16 * 1024


_MAX_REPLAY_NODEIDS = 10_000


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as output:
            descriptor = None
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _assert_real_artifact_directory(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise pytest.UsageError(
            f"{label} is unavailable: {path}: {exc}"
        ) from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _is_name_surrogate_reparse(metadata)
    ):
        raise pytest.UsageError(
            f"{label} must be a real directory, not a symlink or "
            f"name-surrogate reparse point: {path}"
        )


def _initialize_artifact_run(config, policy: _HarnessConfig) -> None:
    if not policy.artifacts_enabled or _is_xdist_worker(config):
        return
    cache_dir = ROOT_DIR / ".pytest_cache"
    artifact_base = cache_dir / "moira-artifacts"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        _assert_real_artifact_directory(
            cache_dir,
            label="pytest cache directory",
        )
        artifact_base.mkdir(exist_ok=True)
        _assert_real_artifact_directory(
            artifact_base,
            label="Moira artifact root",
        )
        resolved_root = ROOT_DIR.resolve(strict=True)
        resolved_base = artifact_base.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise pytest.UsageError(
            f"Cannot initialize the Moira artifact root: {exc}"
        ) from exc
    if not resolved_base.is_relative_to(resolved_root):
        raise pytest.UsageError(
            "Moira artifact root escapes the repository: "
            f"{resolved_base}"
        )

    artifact_dir = artifact_base / policy.run_id
    try:
        artifact_dir.mkdir()
        _assert_real_artifact_directory(
            artifact_dir,
            label="Moira artifact run directory",
        )
        _atomic_write_bytes(
            artifact_dir / "INCOMPLETE",
            _json_bytes(
                {
                    "schema_version": _ARTIFACT_SCHEMA_VERSION,
                    "run_id": policy.run_id,
                    "started_utc": _utc_now_iso(),
                    "status": "incomplete",
                }
            ),
        )
    except FileExistsError as exc:
        raise pytest.UsageError(
            "MOIRA_TEST_RUN_ID collides with an existing artifact run; "
            f"refusing to resume or overwrite {artifact_dir}"
        ) from exc
    except OSError as exc:
        raise pytest.UsageError(
            f"Cannot initialize Moira artifact run {artifact_dir}: {exc}"
        ) from exc
    config.stash[_ARTIFACT_DIR_KEY] = artifact_dir


def _git_bytes(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        shell=False,
    )
    if completed.returncode != 0:
        diagnostic = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"git {' '.join(arguments)} failed with "
            f"{completed.returncode}: {diagnostic}"
        )
    return completed.stdout


def _untracked_content_digest(root: Path) -> tuple[str, int]:
    raw_paths = _git_bytes(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )
    relative_paths = sorted(
        path
        for path in raw_paths.decode("utf-8", errors="strict").split("\0")
        if path
    )
    digest = hashlib.sha256()
    for relative in relative_paths:
        posix = PurePosixPath(relative)
        if (
            posix.is_absolute()
            or any(part in {"", ".", ".."} for part in posix.parts)
        ):
            raise RuntimeError(f"git returned unsafe untracked path {relative!r}")
        path = root.joinpath(*posix.parts)
        metadata = path.lstat()
        encoded_path = relative.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        if stat.S_ISLNK(metadata.st_mode):
            target = os.readlink(path).encode("utf-8")
            digest.update(b"symlink\0")
            digest.update(len(target).to_bytes(8, "big"))
            digest.update(target)
            final_metadata = path.lstat()
            if (
                final_metadata.st_size != metadata.st_size
                or final_metadata.st_mtime_ns != metadata.st_mtime_ns
                or final_metadata.st_dev != metadata.st_dev
                or final_metadata.st_ino != metadata.st_ino
            ):
                raise RuntimeError(
                    f"untracked symlink changed while hashing: {relative}"
                )
        elif stat.S_ISREG(metadata.st_mode):
            digest.update(b"file\0")
            digest.update(metadata.st_size.to_bytes(8, "big"))
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                opened_metadata = os.fstat(source.fileno())
            if (
                opened_metadata.st_size != metadata.st_size
                or opened_metadata.st_mtime_ns != metadata.st_mtime_ns
                or opened_metadata.st_dev != metadata.st_dev
                or opened_metadata.st_ino != metadata.st_ino
            ):
                raise RuntimeError(
                    f"untracked file changed while hashing: {relative}"
                )
        else:
            raise RuntimeError(
                f"untracked path is not a regular file or symlink: {relative}"
            )
    return digest.hexdigest(), len(relative_paths)


def _git_identity(root: Path) -> dict[str, object]:
    try:
        git_root = Path(
            _git_bytes(root, "rev-parse", "--show-toplevel")
            .decode("utf-8", errors="strict")
            .strip()
        ).resolve(strict=True)
        head = (
            _git_bytes(root, "rev-parse", "HEAD")
            .decode("ascii", errors="strict")
            .strip()
        )
        tracked_diff = _git_bytes(
            root,
            "diff",
            "--binary",
            "--no-ext-diff",
            "--no-textconv",
            "HEAD",
            "--",
        )
        untracked_digest, untracked_count = _untracked_content_digest(root)
    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "available": True,
        "repository_root": str(git_root),
        "head": head,
        "tracked_diff_sha256": _sha256_bytes(tracked_diff),
        "untracked_content_sha256": untracked_digest,
        "untracked_count": untracked_count,
    }


def _native_identity(root: Path) -> dict[str, object]:
    try:
        import moira
        from moira._native_build_provenance import (
            native_backend_binary_identity,
            native_build_provenance_identity,
        )

        package_path = Path(moira.__file__).resolve(strict=True)
        raw_backend = import_module("moira._moira_native")
        binary_identity = native_backend_binary_identity(raw_backend)
        embedded_sha256 = binary_identity.pop("embedded_input_sha256")
        backend_path = Path(str(binary_identity["backend_path"]))
        resolved_root = root.resolve(strict=True)
        build_provenance = native_build_provenance_identity(
            resolved_root,
            embedded_sha256,
        )
        return {
            "available": True,
            "moira_version": str(moira.__version__),
            "package_path": str(package_path),
            "package_under_repository": package_path.is_relative_to(
                resolved_root
            ),
            **binary_identity,
            "backend_under_repository": backend_path.is_relative_to(
                resolved_root
            ),
            "build_provenance": build_provenance,
        }
    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _interpreter_identity(root: Path) -> dict[str, object]:
    executable = Path(sys.executable).resolve(strict=True)
    prefix = Path(sys.prefix).resolve(strict=True)
    candidates = (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    )
    project_python = next(
        (
            candidate.resolve(strict=True)
            for candidate in candidates
            if candidate.is_file()
        ),
        None,
    )
    return {
        "executable": str(executable),
        "prefix": str(prefix),
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "project_venv_executable": (
            None if project_python is None else str(project_python)
        ),
        "is_project_venv": project_python == executable,
    }


def _execution_switch_identity() -> dict[str, bool]:
    return {
        "MOIRA_ACCELERATE": os.environ.get("MOIRA_ACCELERATE") == "1",
        "MOIRA_FORCE_PYTHON_TYPE13": os.environ.get(
            "MOIRA_FORCE_PYTHON_TYPE13",
            "",
        ).casefold()
        in {"1", "true", "yes"},
        "MOIRA_FORCE_PYTHON_CHEBYSHEV": os.environ.get(
            "MOIRA_FORCE_PYTHON_CHEBYSHEV",
            "",
        ).casefold()
        in {"1", "true", "yes"},
    }


def _assurance_runtime_identity() -> dict[str, object]:
    """Seal interpreter bytes and versions that govern Phase 9 evidence."""

    executable = Path(sys.executable).resolve(strict=True)
    executable_stat = executable.stat()
    distributions = {
        receipt_name: metadata.version(distribution_name)
        for receipt_name, distribution_name in (
            ("coverage", "coverage"),
            ("pytest", "pytest"),
            ("pytest_cov", "pytest-cov"),
            ("xdist", "pytest-xdist"),
        )
    }
    return {
        "python": {
            "build": list(platform.python_build()),
            "cache_tag": sys.implementation.cache_tag,
            "compiler": platform.python_compiler(),
            "executable": str(executable),
            "executable_bytes": executable_stat.st_size,
            "executable_sha256": _sha256_file(executable),
            "hexversion": sys.hexversion,
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "toolchain_versions": distributions,
    }


def _run_context(root: Path) -> dict[str, object]:
    return {
        "assurance_runtime": _assurance_runtime_identity(),
        "repository": {
            "root": str(root.resolve(strict=True)),
            "git": _git_identity(root),
        },
        "interpreter": _interpreter_identity(root),
        "native": _native_identity(root),
        "execution_switches": _execution_switch_identity(),
    }


class _ControllerReceiptCollector:
    def __init__(self, config) -> None:
        self.config = config
        self.records: list[dict[str, object]] = []
        self.errors: list[str] = []
        self.worker_shutdown: list[dict[str, object]] = []
        self._test_attempts: Counter[str] = Counter()
        self._active_test_attempts: dict[tuple[str, str], int] = {}
        self._other_attempts: Counter[tuple[str, str, str]] = Counter()
        self._secret_values = _secret_environment_values()
        self._identity_secret_values: tuple[str, ...] | None = None

    @property
    def secret_values(self) -> tuple[str, ...]:
        return self._secret_values

    def _refresh_secret_values(self) -> None:
        self._secret_values = tuple(
            sorted(
                set(self._secret_values)
                | set(_secret_environment_values()),
                key=len,
                reverse=True,
            )
        )

    def _text(self, value: object) -> tuple[str, bool]:
        return _redact_text(value, secret_values=self._secret_values)

    @pytest.hookimpl
    def pytest_collection_finish(self, session) -> None:
        del session
        self._refresh_secret_values()
        self._identity_secret_values = self._secret_values

    def _bounded_record(
        self,
        record: dict[str, object],
    ) -> dict[str, object]:
        encoded = json.dumps(
            record,
            allow_nan=False,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) <= _MAX_ARTIFACT_RECORD_BYTES:
            return record
        minimal = {
            "schema_version": _ARTIFACT_SCHEMA_VERSION,
            "sequence": record["sequence"],
            "kind": record["kind"],
            "nodeid": record["nodeid"],
            "attempt": record["attempt"],
            "phase": record["phase"],
            "outcome": record["outcome"],
            "duration_s": record["duration_s"],
            "worker_id": record["worker_id"],
            "wasxfail": record["wasxfail"],
            "longrepr": "[TRUNCATED: per-record artifact limit]",
            "sections": [],
            "user_properties": {},
            "truncation": {
                "applied": True,
                "original_bytes": len(encoded),
                "limit_bytes": _MAX_ARTIFACT_RECORD_BYTES,
            },
        }
        minimal_size = len(
            json.dumps(
                minimal,
                allow_nan=False,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        if minimal_size > _MAX_ARTIFACT_RECORD_BYTES:
            self.errors.append(
                f"{record['nodeid']}: exact report identity exceeds the "
                "per-record artifact limit"
            )
        return minimal

    def _attempt(
        self,
        *,
        nodeid: str,
        worker_id: str,
        kind: str,
        phase: str,
    ) -> int:
        if kind != "test":
            key = (kind, nodeid, phase)
            self._other_attempts[key] += 1
            return self._other_attempts[key]

        active_key = (nodeid, worker_id)
        if phase == "setup":
            self._test_attempts[nodeid] += 1
            attempt = self._test_attempts[nodeid]
            self._active_test_attempts[active_key] = attempt
            return attempt

        attempt = self._active_test_attempts.get(active_key)
        if attempt is None:
            self._test_attempts[nodeid] += 1
            attempt = self._test_attempts[nodeid]
            self._active_test_attempts[active_key] = attempt
        if phase not in {"call"}:
            self._active_test_attempts.pop(active_key, None)
        return attempt

    def _record(self, report, *, kind: str, phase: str) -> None:
        if _is_xdist_worker(self.config):
            return
        self._refresh_secret_values()
        raw_nodeid = getattr(report, "nodeid", "<unknown>")
        nodeid, nodeid_changed = _redact_text(
            raw_nodeid,
            secret_values=(
                self._identity_secret_values
                if self._identity_secret_values is not None
                else self._secret_values
            ),
        )
        if nodeid_changed or len(nodeid) > _MAX_REPLAY_NODEID_CHARS:
            self.errors.append(
                "A report node ID required redaction or exceeded the replay "
                f"limit and cannot be receipted exactly: {nodeid[:200]}"
            )
            nodeid = "[NON-REPLAYABLE NODEID]"
        raw_duration = getattr(report, "duration", 0.0)
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError):
            duration = math.nan
        if not math.isfinite(duration) or duration < 0:
            self.errors.append(
                f"{nodeid}: {phase} report has invalid duration "
                f"{raw_duration!r}"
            )
            duration = 0.0

        outcome, outcome_changed = self._text(
            getattr(report, "outcome", "unknown")
        )
        worker_id, worker_changed = self._text(
            getattr(report, "worker_id", "controller")
        )
        if outcome_changed or worker_changed:
            self.errors.append(
                f"{nodeid}: report identity fields required redaction"
            )

        attempt = self._attempt(
            nodeid=nodeid,
            worker_id=worker_id,
            kind=kind,
            phase=phase,
        )
        longrepr, longrepr_changed = self._text(
            getattr(
                report,
                "_moira_artifact_longrepr",
                getattr(report, "longrepr", ""),
            )
        )
        sections: list[dict[str, object]] = []
        detail_truncated = longrepr_changed or bool(
            getattr(report, "_moira_artifact_redacted", False)
        )
        for section_index, section in enumerate(
            getattr(
                report,
                "_moira_artifact_sections",
                getattr(report, "sections", ()),
            )
            or ()
        ):
            if section_index >= 64:
                detail_truncated = True
                break
            try:
                raw_name, raw_content = section
            except (TypeError, ValueError):
                self.errors.append(
                    f"{nodeid}: report section {section_index} is malformed"
                )
                continue
            name, name_changed = self._text(raw_name)
            content, content_changed = self._text(raw_content)
            detail_truncated = (
                detail_truncated or name_changed or content_changed
            )
            sections.append({"name": name, "content": content})

        user_properties: dict[str, object] = {}
        seen_evidence_properties: set[str] = set()
        for property_index, property_pair in enumerate(
            getattr(
                report,
                "_moira_artifact_user_properties",
                getattr(report, "user_properties", ()),
            )
            or ()
        ):
            if property_index >= 256:
                detail_truncated = True
                break
            try:
                raw_name, raw_value = property_pair
            except (TypeError, ValueError):
                self.errors.append(
                    f"{nodeid}: user property {property_index} is malformed"
                )
                continue
            if not isinstance(raw_name, str) or not raw_name.startswith(
                "moira_"
            ):
                continue
            if raw_name in _EVIDENCE_REPORT_PROPERTY_NAMES:
                if raw_name in seen_evidence_properties:
                    self.errors.append(
                        f"{nodeid}: {phase} report repeats the "
                        f"{raw_name} user property"
                    )
                    continue
                seen_evidence_properties.add(raw_name)
            if (
                isinstance(raw_value, (bool, int, float, str))
                or raw_value is None
            ):
                if (
                    isinstance(raw_value, float)
                    and not math.isfinite(raw_value)
                ):
                    self.errors.append(
                        f"{nodeid}: {raw_name} user property is non-finite"
                    )
                    continue
                if isinstance(raw_value, str):
                    safe_value, changed = self._text(raw_value)
                    detail_truncated = detail_truncated or changed
                    user_properties[raw_name] = safe_value
                else:
                    user_properties[raw_name] = raw_value

        record = {
            "schema_version": _ARTIFACT_SCHEMA_VERSION,
            "sequence": len(self.records) + 1,
            "kind": kind,
            "nodeid": nodeid,
            "attempt": attempt,
            "phase": phase,
            "outcome": outcome,
            "duration_s": duration,
            "worker_id": worker_id,
            "wasxfail": (
                None
                if getattr(
                    report,
                    "_moira_artifact_wasxfail",
                    getattr(report, "wasxfail", None),
                )
                is None
                else self._text(
                    getattr(
                        report,
                        "_moira_artifact_wasxfail",
                        getattr(report, "wasxfail", None),
                    )
                )[0]
            ),
            "longrepr": longrepr,
            "sections": sections,
            "user_properties": user_properties,
            "truncation": {
                "applied": detail_truncated,
                "original_bytes": None,
                "limit_bytes": _MAX_ARTIFACT_RECORD_BYTES,
            },
        }
        self.records.append(self._bounded_record(record))

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report) -> None:
        self._record(
            report,
            kind="test",
            phase=str(getattr(report, "when", "unknown")),
        )

    @pytest.hookimpl
    def pytest_collectreport(self, report) -> None:
        self._record(report, kind="collection", phase="collect")

    def record_worker_shutdown(
        self,
        *,
        worker_id: str,
        error: object,
        workeroutput: object,
    ) -> None:
        self._refresh_secret_values()
        safe_worker, changed = self._text(worker_id)
        safe_error, error_changed = self._text(
            "" if error is None else repr(error)
        )
        if changed:
            self.errors.append("xdist worker identity required redaction")
        status = {
            "worker_id": safe_worker,
            "error": None if error is None else safe_error,
            "exitstatus": (
                workeroutput.get("exitstatus")
                if isinstance(workeroutput, dict)
                and isinstance(workeroutput.get("exitstatus"), int)
                else None
            ),
            "finalized": error is None,
        }
        self.worker_shutdown.append(status)
        if error is not None:
            synthetic = type(
                "_MoiraWorkerCrashReport",
                (),
                {
                    "nodeid": f"<xdist-worker:{safe_worker}>",
                    "duration": 0.0,
                    "outcome": "failed",
                    "worker_id": safe_worker,
                    "longrepr": safe_error,
                    "sections": (),
                    "user_properties": (),
                },
            )()
            self._record(synthetic, kind="xdist_crash", phase="crash")
        elif error_changed:
            self.errors.append(
                f"xdist worker {safe_worker} shutdown detail required redaction"
            )


def _exit_status_payload(exitstatus: object) -> dict[str, object]:
    try:
        status = pytest.ExitCode(int(exitstatus))
    except (TypeError, ValueError):
        return {
            "code": None,
            "name": "UNKNOWN",
            "raw": str(exitstatus),
        }
    return {
        "code": int(status),
        "name": status.name,
    }


def _controller_collector(config) -> _ControllerReceiptCollector | None:
    collector = config.stash.get(_RECEIPT_COLLECTOR_KEY, None)
    if collector is None:
        return None
    if not isinstance(collector, _ControllerReceiptCollector):
        raise RuntimeError("controller receipt collector has an invalid type")
    return collector


def _phase_record_payload(
    record: dict[str, object] | None,
) -> dict[str, object]:
    if record is None:
        return {
            "status": "not_run",
            "outcome": None,
            "duration_s": 0.0,
            "report_sequence": None,
        }
    return {
        "status": "reported",
        "outcome": record["outcome"],
        "duration_s": record["duration_s"],
        "report_sequence": record["sequence"],
    }


def _lifecycle_payload(
    collector: _ControllerReceiptCollector,
) -> dict[str, object]:
    grouped: dict[
        tuple[str, int],
        dict[str, dict[str, object]],
    ] = {}
    worker_ids: dict[tuple[str, int], str] = {}
    for record in collector.records:
        if record["kind"] != "test" or record["phase"] not in _CASE_PHASES:
            continue
        key = (str(record["nodeid"]), int(record["attempt"]))
        phases = grouped.setdefault(key, {})
        phase = str(record["phase"])
        if phase in phases:
            collector.errors.append(
                f"{key[0]} attempt {key[1]} emitted duplicate {phase} reports"
            )
            continue
        phases[phase] = record
        worker = str(record["worker_id"])
        existing_worker = worker_ids.setdefault(key, worker)
        if existing_worker != worker:
            collector.errors.append(
                f"{key[0]} attempt {key[1]} crossed worker identities"
            )

    cases: list[dict[str, object]] = []
    for (nodeid, attempt), phase_records in sorted(
        grouped.items(),
        key=lambda item: (
            min(
                int(record["sequence"])
                for record in item[1].values()
            ),
            item[0],
        ),
    ):
        phases = {
            phase: _phase_record_payload(phase_records.get(phase))
            for phase in _CASE_PHASES
        }
        total_s = sum(
            float(detail["duration_s"])
            for detail in phases.values()
        )
        teardown = phase_records.get("teardown")
        properties = (
            teardown.get("user_properties", {})
            if teardown is not None
            else {}
        )
        assert isinstance(properties, dict)
        case_budget_s = collector.config.stash[
            _HARNESS_CONFIG_KEY
        ].budget_case_s
        case_budget_exceeded = bool(
            case_budget_s and total_s > case_budget_s
        )
        reported_total = properties.get("moira_lifecycle_total_s")
        if (
            isinstance(reported_total, (int, float))
            and math.isfinite(float(reported_total))
            and not math.isclose(
                total_s,
                float(reported_total),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            collector.errors.append(
                f"{nodeid} attempt {attempt} lifecycle total contradicts "
                "its phase reports"
            )
        reported_budget = properties.get("moira_case_budget_s")
        if (
            isinstance(reported_budget, (int, float))
            and math.isfinite(float(reported_budget))
            and not math.isclose(
                case_budget_s,
                float(reported_budget),
                rel_tol=0.0,
                abs_tol=0.0,
            )
        ):
            collector.errors.append(
                f"{nodeid} attempt {attempt} case budget contradicts "
                "controller policy"
            )
        reported_exceeded = properties.get(
            "moira_case_budget_exceeded"
        )
        if (
            type(reported_exceeded) is bool
            and reported_exceeded != case_budget_exceeded
        ):
            collector.errors.append(
                f"{nodeid} attempt {attempt} case-budget result "
                "contradicts controller lifecycle evidence"
            )
        failed = any(
            detail["outcome"] == "failed"
            for detail in phases.values()
        )
        if case_budget_exceeded and not failed:
            collector.errors.append(
                f"{nodeid} attempt {attempt} exceeded its case budget "
                "without a failed report"
            )
        cases.append(
            {
                "nodeid": nodeid,
                "attempt": attempt,
                "worker_id": worker_ids[(nodeid, attempt)],
                "complete": (
                    "setup" in phase_records
                    and "teardown" in phase_records
                ),
                "phases": phases,
                "total_duration_s": total_s,
                "case_budget_s": case_budget_s,
                "case_budget_exceeded": case_budget_exceeded,
                "failed": failed,
                "passed": all(
                    phases[phase]["status"] == "reported"
                    and phases[phase]["outcome"] == "passed"
                    for phase in _CASE_PHASES
                ),
            }
        )
    return {
        "schema_version": _ARTIFACT_SCHEMA_VERSION,
        "cases": cases,
    }


def _seal_lifecycle_evidence(
    config,
    collector: _ControllerReceiptCollector | None = None,
) -> tuple[dict[str, object], tuple[str, ...]]:
    """Validate lifecycle records once and retain the exact sealed result."""

    existing_payload = config.stash.get(_LIFECYCLE_PAYLOAD_KEY, None)
    existing_errors = config.stash.get(
        _CONTROLLER_EVIDENCE_ERRORS_KEY,
        None,
    )
    if existing_payload is not None or existing_errors is not None:
        if existing_payload is None or existing_errors is None:
            raise RuntimeError("lifecycle evidence seal is incomplete")
        return existing_payload, existing_errors

    selected_collector = (
        collector
        if collector is not None
        else _controller_collector(config)
    )
    if selected_collector is None:
        payload = {
            "schema_version": _ARTIFACT_SCHEMA_VERSION,
            "cases": [],
        }
        errors = (
            "controller receipt collector is unavailable during "
            "lifecycle sealing",
        )
    else:
        try:
            payload = _lifecycle_payload(selected_collector)
        except Exception as exc:
            error = (
                "lifecycle evidence sealing failed: "
                f"{type(exc).__name__}: {exc}"
            )
            selected_collector.errors.append(error)
            payload = {
                "schema_version": _ARTIFACT_SCHEMA_VERSION,
                "cases": [],
            }
        errors = tuple(selected_collector.errors)

    config.stash[_LIFECYCLE_PAYLOAD_KEY] = payload
    config.stash[_CONTROLLER_EVIDENCE_ERRORS_KEY] = errors
    return payload, errors


def _failure_payload(
    collector: _ControllerReceiptCollector,
    lifecycle: dict[str, object],
) -> tuple[dict[str, object], tuple[str, ...]]:
    cases = lifecycle["cases"]
    assert isinstance(cases, list)
    failed_cases = [
        {
            "nodeid": case["nodeid"],
            "attempt": case["attempt"],
            "failed_phases": [
                phase
                for phase, detail in case["phases"].items()
                if detail["outcome"] == "failed"
            ],
        }
        for case in cases
        if case["failed"]
    ]
    failed_case_keys = {
        (str(case["nodeid"]), int(case["attempt"]))
        for case in failed_cases
    }
    unscoped_test_failures = [
        record
        for record in collector.records
        if record["kind"] == "test"
        and record["outcome"] == "failed"
        and record["phase"] not in _CASE_PHASES
    ]
    for record in unscoped_test_failures:
        key = (str(record["nodeid"]), int(record["attempt"]))
        if key in failed_case_keys:
            continue
        failed_cases.append(
            {
                "nodeid": key[0],
                "attempt": key[1],
                "failed_phases": [str(record["phase"])],
            }
        )
        failed_case_keys.add(key)
    failure_reports = [
        int(record["sequence"])
        for record in collector.records
        if record["outcome"] == "failed"
    ]
    collection_failures = [
        int(record["sequence"])
        for record in collector.records
        if record["kind"] == "collection"
        and record["outcome"] == "failed"
    ]
    worker_crashes = [
        int(record["sequence"])
        for record in collector.records
        if record["kind"] == "xdist_crash"
    ]
    budget_violations = [
        {
            "nodeid": case["nodeid"],
            "attempt": case["attempt"],
            "total_duration_s": case["total_duration_s"],
            "budget_s": case["case_budget_s"],
        }
        for case in cases
        if case["case_budget_exceeded"]
    ]

    attempts_by_nodeid: dict[str, list[dict[str, object]]] = {}
    for case in cases:
        attempts_by_nodeid.setdefault(
            str(case["nodeid"]),
            [],
        ).append(case)
    flakes: list[dict[str, object]] = []
    for nodeid, attempts in sorted(attempts_by_nodeid.items()):
        attempts.sort(key=lambda case: int(case["attempt"]))
        first_failed = next(
            (
                int(case["attempt"])
                for case in attempts
                if case["failed"]
            ),
            None,
        )
        if first_failed is None:
            continue
        later_passed = next(
            (
                int(case["attempt"])
                for case in attempts
                if int(case["attempt"]) > first_failed
                and case["passed"]
            ),
            None,
        )
        if later_passed is not None:
            flakes.append(
                {
                    "nodeid": nodeid,
                    "failed_attempt": first_failed,
                    "passing_attempt": later_passed,
                }
            )

    rerun_nodeids: list[str] = []
    seen: set[str] = set()
    for case in failed_cases:
        nodeid = str(case["nodeid"])
        if nodeid in seen:
            continue
        if _validate_replay_nodeid(nodeid):
            rerun_nodeids.append(nodeid)
            seen.add(nodeid)
        else:
            collector.errors.append(
                f"failed test node ID is not safely replayable: {nodeid[:200]}"
            )
    if len(rerun_nodeids) > _MAX_REPLAY_NODEIDS:
        collector.errors.append(
            "failed test node ID count exceeds the replay receipt limit"
        )

    return (
        {
            "schema_version": _ARTIFACT_SCHEMA_VERSION,
            "failure_report_sequences": failure_reports,
            "failed_cases": failed_cases,
            "collection_failure_report_sequences": collection_failures,
            "worker_crash_report_sequences": worker_crashes,
            "unscoped_test_failure_report_sequences": [
                int(record["sequence"])
                for record in unscoped_test_failures
            ],
            "budget_violations": budget_violations,
            "flakes": flakes,
        },
        tuple(rerun_nodeids[:_MAX_REPLAY_NODEIDS]),
    )


def _validate_replay_nodeid(nodeid: str) -> bool:
    if (
        not nodeid
        or len(nodeid) > _MAX_REPLAY_NODEID_CHARS
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in nodeid)
        or "\\" in nodeid
    ):
        return False
    path_text = nodeid.split("::", 1)[0]
    path = PurePosixPath(path_text)
    return (
        not path.is_absolute()
        and len(path.parts) >= 2
        and path.parts[0] == "tests"
        and path.suffix == ".py"
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _collection_payload(
    config,
    collector: _ControllerReceiptCollector,
) -> dict[str, object]:
    receipt = _classification_receipt_for_summary(config)
    classification = (
        None
        if receipt is None
        else _serialize_classification_receipt(receipt)
    )
    return {
        "schema_version": _ARTIFACT_SCHEMA_VERSION,
        "classification": classification,
        "classification_errors": list(_classification_errors(config)),
        "evidence": config.stash.get(_EVIDENCE_PAYLOAD_KEY, None),
        "evidence_errors": list(
            config.stash.get(_XDIST_EVIDENCE_ERRORS_STATE_KEY, ())
        ),
        "collection_error_report_sequences": [
            int(record["sequence"])
            for record in collector.records
            if record["kind"] == "collection"
            and record["outcome"] == "failed"
        ],
    }


def _sanitize_artifact_value(
    value: object,
    *,
    secret_values: tuple[str, ...],
    depth: int = 0,
) -> object:
    if depth > 64:
        raise ValueError("artifact payload exceeds the maximum nesting depth")
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("artifact payload contains a non-finite number")
        return value
    if isinstance(value, str):
        return _redact_text(value, secret_values=secret_values)[0]
    if isinstance(value, (list, tuple)):
        return [
            _sanitize_artifact_value(
                item,
                secret_values=secret_values,
                depth=depth + 1,
            )
            for item in value
        ]
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("artifact payload contains a non-text key")
            safe_key = _redact_text(
                key,
                secret_values=secret_values,
            )[0]
            if safe_key in sanitized:
                raise ValueError(
                    "artifact redaction created a duplicate object key"
                )
            sanitized[safe_key] = _sanitize_artifact_value(
                item,
                secret_values=secret_values,
                depth=depth + 1,
            )
        return sanitized
    raise ValueError(
        f"artifact payload contains unsupported {type(value).__name__}"
    )


def _reports_jsonl_bytes(
    collector: _ControllerReceiptCollector,
    *,
    secret_values: tuple[str, ...],
) -> bytes:
    lines: list[bytes] = []
    for record in collector.records:
        safe_record = _sanitize_artifact_value(
            record,
            secret_values=secret_values,
        )
        raw_nodeid = record.get("nodeid")
        if not isinstance(raw_nodeid, str):
            raise ValueError("artifact report node ID is malformed")
        safe_record["nodeid"] = raw_nodeid
        raw_properties = record.get("user_properties", {})
        safe_properties = safe_record.get("user_properties", {})
        if not isinstance(raw_properties, dict) or not isinstance(
            safe_properties,
            dict,
        ):
            raise ValueError("artifact report user properties are malformed")
        for reserved_name in (
            "moira_validation_claim_id",
            "moira_validation_contract_sha256",
        ):
            if raw_properties.get(reserved_name) != safe_properties.get(
                reserved_name
            ):
                raise ValueError(
                    "artifact redaction would mutate reserved validation "
                    f"report identity: {reserved_name}"
                )
        lines.append(
            json.dumps(
                safe_record,
                allow_nan=False,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    return b"\n".join(lines) + (b"\n" if lines else b"")


def _redacted_invocation(config, secret_values: tuple[str, ...]) -> dict[str, object]:
    arguments: list[str] = []
    redacted = False
    redact_next = False
    for argument in tuple(config.invocation_params.args):
        if redact_next:
            safe, changed = "[REDACTED]", True
            redact_next = False
        else:
            safe, changed = _redact_text(
                argument,
                secret_values=secret_values,
            )
            if _SECRET_OPTION_RE.fullmatch(argument):
                redact_next = True
                changed = True
        arguments.append(safe)
        redacted = redacted or changed
    return {
        "arguments": arguments,
        "arguments_are_evidence_only": True,
        "redacted": redacted,
    }


def _policy_payload(policy: _HarnessConfig) -> dict[str, object]:
    return {
        "test_mode": policy.test_mode,
        "no_download": policy.no_download,
        "strict_known_issues": policy.strict_known_issues,
        "external_network_enabled": policy.external_network_enabled,
        "seed": policy.seed,
        "budget_total_s": policy.budget_total_s,
        "budget_case_s": policy.budget_case_s,
        "artifacts_enabled": policy.artifacts_enabled,
        "hypothesis": {
            "profile": policy.hypothesis.profile,
            "max_examples": policy.hypothesis.max_examples,
            "database_policy": policy.hypothesis.database_policy,
            "derandomize": policy.hypothesis.derandomize,
        },
    }


def _pytest_cov_option_identity(config) -> dict[str, object]:
    """Capture effective pytest-cov options after all ambient configuration."""

    source = getattr(config.option, "cov_source", None)
    if source is not None:
        if not isinstance(source, (list, tuple)) or not all(
            isinstance(value, str) for value in source
        ):
            raise RuntimeError("effective pytest-cov source option is malformed")
        source = list(source)
    cov_config = getattr(config.option, "cov_config", None)
    if cov_config is not None:
        cov_config = str(cov_config)
    return {
        "append": getattr(config.option, "cov_append", None),
        "branch": getattr(config.option, "cov_branch", None),
        "config": cov_config,
        "context": getattr(config.option, "cov_context", None),
        "no_cov": getattr(config.option, "no_cov", None),
        "source": source,
    }


def _coverage_config_file_identity(root: Path, raw_path: object) -> dict[str, object]:
    candidate = Path(str(raw_path))
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        resolved = candidate.resolve(strict=True)
        payload = resolved.read_bytes()
    except OSError as exc:
        raise RuntimeError(
            f"coverage configuration file is unavailable: {candidate}"
        ) from exc
    if not resolved.is_file():
        raise RuntimeError(
            f"coverage configuration path is not a regular file: {resolved}"
        )
    try:
        receipt_path = resolved.relative_to(root.resolve(strict=True)).as_posix()
        path_policy = "repository_relative"
    except ValueError:
        receipt_path = str(resolved)
        path_policy = "absolute"
    return {
        "bytes": len(payload),
        "path": receipt_path,
        "path_policy": path_policy,
        "resolved_path": str(resolved),
        "sha256": _sha256_bytes(payload),
    }


def _active_coverage_runtime_identity(root: Path, config) -> dict[str, object] | None:
    """Capture pytest-cov's resolved tracer while its Coverage is active."""

    plugin = config.pluginmanager.get_plugin("_cov")
    if plugin is None or bool(getattr(plugin, "_disabled", False)):
        return None
    controller = getattr(plugin, "cov_controller", None)
    cov = getattr(controller, "cov", None)
    if cov is None:
        raise RuntimeError("pytest-cov has no active Coverage controller")
    try:
        from coverage import Coverage

        info = dict(cov.sys_info())
        active = Coverage.current() is cov
        coverage_config = cov.config
    except Exception as exc:
        raise RuntimeError("active pytest-cov runtime cannot be inspected") from exc
    config_files = [
        _coverage_config_file_identity(root, path)
        for path in tuple(coverage_config.config_files_read)
    ]
    config_files.sort(key=lambda item: str(item["resolved_path"]))
    source = coverage_config.source
    concurrency = coverage_config.concurrency
    plugins = coverage_config.plugins
    return {
        "active": active,
        "actual_core": info.get("core"),
        "assurance_runtime": _assurance_runtime_identity(),
        "config_files": config_files,
        "controller": (
            f"{type(controller).__module__}.{type(controller).__qualname__}"
        ),
        "coverage_data_file": str(Path(coverage_config.data_file).resolve()),
        "effective_config": {
            "branch": coverage_config.branch,
            "concurrency": list(concurrency or ()),
            "core": coverage_config.core,
            "dynamic_context": coverage_config.dynamic_context,
            "parallel": coverage_config.parallel,
            "plugins": list(plugins or ()),
            "relative_files": coverage_config.relative_files,
            "source": None if source is None else list(source),
            "static_context": coverage_config.context,
            "timid": coverage_config.timid,
        },
        "environment": {
            name: os.environ.get(name) for name in _COVERAGE_ENVIRONMENT_NAMES
        },
        "run_context": _run_context(root),
    }


@pytest.hookimpl(trylast=True)
def pytest_sessionstart(session) -> None:
    identity = _active_coverage_runtime_identity(ROOT_DIR, session.config)
    if identity is not None:
        session.config.stash[_COVERAGE_RUNTIME_IDENTITY_KEY] = identity


def _coverage_runtime_receipt(config) -> dict[str, object] | None:
    controller = config.stash.get(_COVERAGE_RUNTIME_IDENTITY_KEY, None)
    workers = config.stash.get(
        _XDIST_COVERAGE_RUNTIME_REPORT_STATE_KEY,
        {},
    )
    errors = config.stash.get(
        _XDIST_COVERAGE_RUNTIME_ERRORS_STATE_KEY,
        [],
    )
    if errors:
        raise RuntimeError("; ".join(errors))
    mode = _xdist_mode(config)
    if mode == "no":
        if workers:
            raise RuntimeError("serial coverage receipt contains worker attestations")
    else:
        expected_workers = config.stash.get(
            _XDIST_CLASSIFICATION_EXPECTED_STATE_KEY,
            set(),
        )
        if set(workers) != set(expected_workers):
            raise RuntimeError(
                "xdist coverage runtime attestations are incomplete: "
                f"expected {sorted(expected_workers)}, got {sorted(workers)}"
            )
    if controller is None:
        if workers:
            raise RuntimeError("worker coverage attestations lack a controller")
        return None
    controller = dict(controller)
    controller["final_run_context"] = _run_context(ROOT_DIR)
    for contributor, identity in (
        ("controller", controller),
        *tuple(sorted(workers.items())),
    ):
        config_files = identity.get("config_files")
        if not isinstance(config_files, list):
            raise RuntimeError(
                f"{contributor} coverage config identity is malformed"
            )
        for sealed in config_files:
            if not isinstance(sealed, dict) or not isinstance(
                sealed.get("resolved_path"),
                str,
            ):
                raise RuntimeError(
                    f"{contributor} coverage config identity is malformed"
                )
            current = _coverage_config_file_identity(
                ROOT_DIR,
                sealed["resolved_path"],
            )
            if current != sealed:
                raise RuntimeError(
                    f"{contributor} coverage configuration changed during the run"
                )
    return {
        "controller": controller,
        "workers": {name: workers[name] for name in sorted(workers)},
    }


def _explicit_coverage_identity(root: Path, config) -> dict[str, object] | None:
    """Seal the exact data file named by ``COVERAGE_FILE``, when present."""

    configured = os.environ.get("COVERAGE_FILE")
    if not configured:
        return None

    configured_path = Path(configured)
    candidate = (
        configured_path
        if configured_path.is_absolute()
        else Path.cwd() / configured_path
    )
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(
            "coverage data file requested by COVERAGE_FILE is missing or "
            f"unresolvable: {candidate}"
        ) from exc

    try:
        with resolved.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise RuntimeError(
                    "coverage data file requested by COVERAGE_FILE is not "
                    f"a regular file: {resolved}"
                )
            payload = stream.read()
            after = os.fstat(stream.fileno())
    except RuntimeError:
        raise
    except OSError as exc:
        raise RuntimeError(
            "coverage data file requested by COVERAGE_FILE is unreadable: "
            f"{resolved}"
        ) from exc

    before_identity = (before.st_size, before.st_mtime_ns)
    after_identity = (after.st_size, after.st_mtime_ns)
    if before_identity != after_identity or len(payload) != after.st_size:
        raise RuntimeError(
            "coverage data file requested by COVERAGE_FILE changed while "
            f"its identity was being sealed: {resolved}"
        )

    resolved_root = root.resolve(strict=True)
    try:
        relative_path = resolved.relative_to(resolved_root).as_posix()
    except ValueError:
        receipt_path = str(resolved)
        path_policy = "absolute"
    else:
        receipt_path = relative_path
        path_policy = "repository_relative"

    coverage_core = os.environ.get("COVERAGE_CORE")
    return {
        "data_file": {
            "path": receipt_path,
            "path_policy": path_policy,
            "resolved_path": str(resolved),
            "bytes": len(payload),
            "sha256": _sha256_bytes(payload),
            "mtime_ns": after.st_mtime_ns,
        },
        "core": {
            "environment": coverage_core,
            "policy": (
                "explicit_environment"
                if coverage_core is not None
                else "coverage_default"
            ),
            "is_ctrace": coverage_core == "ctrace",
        },
        "pytest_cov": _pytest_cov_option_identity(config),
        "runtime": _coverage_runtime_receipt(config),
    }


def _artifact_error(
    value: object,
    *,
    secret_values: tuple[str, ...],
) -> str:
    return _redact_text(value, secret_values=secret_values)[0]


def _retain_incomplete_artifact(
    config,
    policy: _HarnessConfig,
    errors: list[str],
    *,
    secret_values: tuple[str, ...],
) -> list[str]:
    safe_errors = [
        _artifact_error(error, secret_values=secret_values)
        for error in errors
    ]
    try:
        artifact_dir = config.stash.get(_ARTIFACT_DIR_KEY, None)
        if artifact_dir is not None:
            _assert_real_artifact_directory(
                artifact_dir,
                label="Moira artifact run directory",
            )
        if artifact_dir is not None and not (
            artifact_dir / "COMPLETE"
        ).exists():
            _atomic_write_bytes(
                artifact_dir / "INCOMPLETE",
                _json_bytes(
                    {
                        "schema_version": _ARTIFACT_SCHEMA_VERSION,
                        "run_id": policy.run_id,
                        "status": "incomplete",
                        "finished_utc": _utc_now_iso(),
                        "finalization_errors": safe_errors[:20],
                        "omitted_error_count": max(
                            0,
                            len(safe_errors) - 20,
                        ),
                    }
                ),
            )
    except Exception as exc:
        safe_errors.append(
            _artifact_error(
                "could not update the INCOMPLETE sentinel: "
                f"{type(exc).__name__}: {exc}",
                secret_values=secret_values,
            )
        )
    return safe_errors


def _finalize_artifact_receipt(
    session,
    *,
    total_budget: dict[str, object],
    prospective_exitstatus: object,
) -> list[str]:
    config = session.config
    policy = config.stash[_HARNESS_CONFIG_KEY]
    collector = _controller_collector(config)
    lifecycle, _evidence_errors = _seal_lifecycle_evidence(
        config,
        collector,
    )
    if not policy.artifacts_enabled:
        return []
    errors: list[str] = []
    secret_values = tuple(
        sorted(
            set(_secret_environment_values())
            | (
                set(collector.secret_values)
                if collector is not None
                else set()
            ),
            key=len,
            reverse=True,
        )
    )
    try:
        artifact_dir = config.stash[_ARTIFACT_DIR_KEY]
        _assert_real_artifact_directory(
            artifact_dir,
            label="Moira artifact run directory",
        )
        if collector is None:
            raise RuntimeError("controller receipt collector is unavailable")
        if collector.errors:
            errors.extend(collector.errors)

        start_context = config.stash[_ARTIFACT_START_CONTEXT_KEY]
        final_context = _run_context(ROOT_DIR)
        for field in (
            "assurance_runtime",
            "repository",
            "interpreter",
            "native",
            "execution_switches",
        ):
            if start_context[field] != final_context[field]:
                errors.append(
                    f"{field} identity changed during the pytest run"
                )
        if errors:
            return _retain_incomplete_artifact(
                config,
                policy,
                errors,
                secret_values=secret_values,
            )

        failures, rerun_nodeids = _failure_payload(
            collector,
            lifecycle,
        )
        if collector.errors:
            return _retain_incomplete_artifact(
                config,
                policy,
                collector.errors,
                secret_values=secret_values,
            )

        collection_payload = _collection_payload(config, collector)
        sanitized_collection = _sanitize_artifact_value(
            collection_payload,
            secret_values=secret_values,
        )
        if (
            sanitized_collection["evidence"]
            != collection_payload["evidence"]
        ):
            raise RuntimeError(
                "artifact redaction would mutate sealed validation evidence"
            )

        sidecar_payloads: dict[str, object] = {
            "collection.json": sanitized_collection,
            "resources.json": {
                "schema_version": _ARTIFACT_SCHEMA_VERSION,
                "planetary": _bind_planetary_content_digests(
                    _combined_planetary_resource_report(config)
                ),
                "small_body": _combined_small_body_resource_report(config),
            },
            "failures.json": failures,
            "durations.json": lifecycle,
            "rerun-nodeids.json": {
                "schema_version": _ARTIFACT_SCHEMA_VERSION,
                "nodeids": list(rerun_nodeids),
            },
        }
        sidecar_bytes = {
            name: _json_bytes(
                _sanitize_artifact_value(
                    payload,
                    secret_values=secret_values,
                )
            )
            for name, payload in sidecar_payloads.items()
        }
        sidecar_bytes["reports.jsonl"] = _reports_jsonl_bytes(
            collector,
            secret_values=secret_values,
        )
        if set(sidecar_bytes) != set(_ARTIFACT_FILENAMES):
            raise RuntimeError("artifact finalizer produced an invalid file set")

        artifact_manifest = {
            name: {
                "bytes": len(data),
                "sha256": _sha256_bytes(data),
            }
            for name, data in sorted(sidecar_bytes.items())
        }
        started_utc = config.stash.get(
            _SESSION_UTC_START_KEY,
            _utc_now_iso(),
        )
        coverage_identity = _explicit_coverage_identity(ROOT_DIR, config)
        run_payload = {
            "schema_version": _ARTIFACT_SCHEMA_VERSION,
            "run_id": policy.run_id,
            "assurance_runtime": start_context["assurance_runtime"],
            "repository": start_context["repository"],
            "interpreter": start_context["interpreter"],
            "native": start_context["native"],
            "execution_switches": start_context["execution_switches"],
            "final_context": final_context,
            "invocation": _redacted_invocation(config, secret_values),
            "policy": _policy_payload(policy),
            "timing": {
                "started_utc": started_utc,
                "finished_utc": _utc_now_iso(),
                "elapsed_monotonic_s": total_budget["elapsed_s"],
                "clock": "time.perf_counter",
            },
            "pytest": {
                "exitstatus": _exit_status_payload(
                    prospective_exitstatus
                ),
                "total_budget": total_budget,
            },
            "xdist": {
                "mode": _xdist_mode(config),
                "worker_shutdown": list(collector.worker_shutdown),
            },
            "coverage": coverage_identity,
            "artifacts": artifact_manifest,
        }
        sanitized_run_payload = _sanitize_artifact_value(
            run_payload,
            secret_values=secret_values,
        )
        if sanitized_run_payload["coverage"] != coverage_identity:
            raise RuntimeError(
                "artifact redaction would mutate the sealed coverage identity"
            )
        run_bytes = _json_bytes(sanitized_run_payload)
        complete_payload = {
            "schema_version": _ARTIFACT_SCHEMA_VERSION,
            "run_id": policy.run_id,
            "status": "complete",
            "run_json": {
                "bytes": len(run_bytes),
                "sha256": _sha256_bytes(run_bytes),
            },
        }
        complete_bytes = _json_bytes(complete_payload)
        total_bytes = (
            sum(len(data) for data in sidecar_bytes.values())
            + len(run_bytes)
            + len(complete_bytes)
        )
        if total_bytes > _MAX_ARTIFACT_RUN_BYTES:
            raise RuntimeError(
                "artifact receipt exceeds the total run limit: "
                f"{total_bytes} > {_MAX_ARTIFACT_RUN_BYTES} bytes"
            )

        for name in _ARTIFACT_FILENAMES:
            _atomic_write_bytes(
                artifact_dir / name,
                sidecar_bytes[name],
            )
        _atomic_write_bytes(artifact_dir / "run.json", run_bytes)
        incomplete = artifact_dir / "INCOMPLETE"
        _atomic_write_bytes(incomplete, complete_bytes)
        os.replace(incomplete, artifact_dir / "COMPLETE")
    except Exception as exc:
        errors.append(
            f"artifact receipt finalization failed: "
            f"{type(exc).__name__}: {exc}"
        )
    if errors:
        return _retain_incomplete_artifact(
            config,
            policy,
            errors,
            secret_values=secret_values,
        )
    return []


def _emit_post_session_diagnostics(
    config,
    *,
    total_budget: dict[str, object],
    evidence_errors: tuple[str, ...],
    artifact_errors: list[str],
) -> None:
    terminalreporter = config.pluginmanager.get_plugin("terminalreporter")
    if terminalreporter is None:
        return
    if total_budget["exceeded"]:
        terminalreporter.section("Moira: total budget")
        terminalreporter.write_line(
            "  Test session exceeded the total budget: "
            f"{float(total_budget['elapsed_s']):.3f}s > "
            f"{float(total_budget['budget_s']):.3f}s"
        )
    if evidence_errors:
        terminalreporter.section("Moira: controller evidence validation")
        terminalreporter.write_line("  FAILED")
        for error in evidence_errors[:10]:
            terminalreporter.write_line(f"    {error}")
    if artifact_errors:
        terminalreporter.section("Moira: artifact finalization")
        terminalreporter.write_line("  FAILED; INCOMPLETE receipt retained")
        for error in artifact_errors[:10]:
            terminalreporter.write_line(f"    {error}")
    else:
        artifact_dir = config.stash.get(_ARTIFACT_DIR_KEY, None)
        if artifact_dir is not None:
            terminalreporter.write_line(
                f"  Artifact receipt: {artifact_dir / 'COMPLETE'}"
            )


@pytest.hookimpl
def pytest_configure(config) -> None:
    """Install the controller-owned receipt collector exactly once."""

    if _is_xdist_worker(config):
        return
    policy = config.stash[_HARNESS_CONFIG_KEY]
    collector = _ControllerReceiptCollector(config)
    config.stash[_RECEIPT_COLLECTOR_KEY] = collector
    config.pluginmanager.register(
        collector,
        name="moira-controller-receipt-collector",
    )
    _initialize_artifact_run(config, policy)
    if policy.artifacts_enabled:
        config.stash[_ARTIFACT_START_CONTEXT_KEY] = _run_context(ROOT_DIR)

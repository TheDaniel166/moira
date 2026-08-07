"""Pure schema and canonical serialization for validation evidence claims."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType
from typing import Mapping


EVIDENCE_SCHEMA_VERSION = 2


_CLAIM_ID_RE = re.compile(r"[A-Z0-9][A-Z0-9_.-]{2,95}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_QUALNAME_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
)
_ALLOWED_COMPARISON_RULES = frozenset(
    {
        "exact",
        "absolute",
        "relative",
        "absolute_or_relative",
        "circular",
        "vector_angle",
        "interval",
    }
)
_ALLOWED_COVERAGE_PHASES = frozenset({"setup", "run", "teardown"})
_ALLOWED_SOURCE_HASH_MODES = frozenset({"bytes", "python_ast_v1"})


class EvidenceClass(str, Enum):
    """Constitutional evidence classes; no class upgrades another."""

    REGRESSION = "regression"
    AUTHORITY = "authority"
    CORROBORATION = "corroboration"
    INVARIANT = "invariant"
    NATIVE_PARITY = "native_parity"
    HARNESS = "harness"
    PERFORMANCE = "performance"


@dataclass(frozen=True, slots=True)
class DeclaredField:
    """A required semantic cell with an explicit applicability decision."""

    status: str
    value: str | None = None
    reason: str | None = None

    @classmethod
    def declared(cls, value: str) -> "DeclaredField":
        return cls(status="declared", value=value)

    @classmethod
    def not_applicable(cls, reason: str) -> "DeclaredField":
        return cls(status="not_applicable", reason=reason)


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """A named authority, fixture, or corpus identity."""

    name: str
    locator: str
    version: str
    sha256: str | None = None
    local: bool = False
    hash_mode: str = "bytes"
    symbols: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceSet:
    """An explicit set of sources or an explicit non-applicability reason."""

    status: str
    sources: tuple[EvidenceSource, ...] = ()
    reason: str | None = None

    @classmethod
    def declared(cls, *sources: EvidenceSource) -> "SourceSet":
        return cls(status="declared", sources=tuple(sources))

    @classmethod
    def not_applicable(cls, reason: str) -> "SourceSet":
        return cls(status="not_applicable", reason=reason)


@dataclass(frozen=True, slots=True)
class Comparison:
    """One exact or tolerance-governed comparison made by a claim."""

    metric: str
    unit: str
    rule: str
    basis: str
    absolute: float | None = None
    relative: float | None = None


@dataclass(frozen=True, slots=True)
class CoverageTarget:
    """One callable whose executed statements must fill an assurance cell."""

    path: str
    qualname: str
    phases: tuple[str, ...] = ("run",)
    protected: bool = True


@dataclass(frozen=True, slots=True)
class EvidenceContract:
    """Complete, immutable semantics for one admitted validation claim."""

    claim_id: str
    product_surface: str
    evidence_class: EvidenceClass
    governing_object: str
    nodeids: tuple[str, ...]
    proves: tuple[str, ...]
    does_not_prove: tuple[str, ...]
    authorities: SourceSet
    fixtures: SourceSet
    corpora: SourceSet
    frame: DeclaredField
    origin: DeclaredField
    timescale: DeclaredField
    correction_policy: DeclaredField
    comparisons: tuple[Comparison, ...]
    bodies: DeclaredField
    interval: DeclaredField
    resource_capability: DeclaredField
    execution_paths: tuple[str, ...]
    exclusions: tuple[str, ...]
    expected_refusal: tuple[str, ...]
    coverage_targets: tuple[CoverageTarget, ...]


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    if "\x00" in value:
        raise ValueError(f"{label} must not contain NUL")
    return value


def _require_text_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not value:
        raise ValueError(f"{label} must be a non-empty tuple")
    normalized = tuple(
        _require_text(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} must not contain duplicates")
    return normalized


def _validate_declared_field(field: DeclaredField, label: str) -> None:
    if not isinstance(field, DeclaredField):
        raise ValueError(f"{label} must be a DeclaredField")
    if field.status == "declared":
        _require_text(field.value, f"{label}.value")
        if field.reason is not None:
            raise ValueError(f"{label} declared values cannot carry a reason")
        return
    if field.status == "not_applicable":
        _require_text(field.reason, f"{label}.reason")
        if field.value is not None:
            raise ValueError(
                f"{label} not_applicable values cannot carry a value"
            )
        return
    raise ValueError(
        f"{label}.status must be declared or not_applicable"
    )


def _safe_relative_path(value: str, label: str) -> PurePosixPath:
    _require_text(value, label)
    if "\\" in value or any(character in value for character in "*?[]"):
        raise ValueError(f"{label} must be an exact POSIX relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"{label} escapes the repository")
    return path


def _assignment_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_assignment_names(element))
        return names
    return set()


def _module_bindings(tree: ast.Module) -> dict[str, tuple[ast.stmt, ...]]:
    candidates: dict[str, list[ast.stmt]] = {}

    def bind(name: str, node: ast.stmt) -> None:
        candidates.setdefault(name, []).append(node)

    for statement in tree.body:
        if isinstance(
            statement,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            bind(statement.name, statement)
        elif isinstance(statement, ast.Assign):
            for target in statement.targets:
                for name in _assignment_names(target):
                    bind(name, statement)
        elif isinstance(statement, ast.AnnAssign):
            for name in _assignment_names(statement.target):
                bind(name, statement)
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                name = alias.asname or alias.name.split(".", 1)[0]
                bind(name, ast.Import(names=[alias]))
        elif isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                name = alias.asname or alias.name
                bind(
                    name,
                    ast.ImportFrom(
                        module=statement.module,
                        names=[alias],
                        level=statement.level,
                    ),
                )
    return {name: tuple(nodes) for name, nodes in candidates.items()}


def _is_leading_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _canonical_ast_scalar(value: object) -> object:
    if isinstance(value, ast.AST):
        return _canonical_ast_node(value)
    if isinstance(value, list):
        return [_canonical_ast_scalar(item) for item in value]
    if isinstance(value, tuple):
        return {
            "scalar_type": "tuple",
            "items": [_canonical_ast_scalar(item) for item in value],
        }
    if value is None:
        return {"scalar_type": "none"}
    if value is Ellipsis:
        return {"scalar_type": "ellipsis"}
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return {"scalar_type": "float", "hex": value.hex()}
    if isinstance(value, complex):
        return {
            "scalar_type": "complex",
            "real_hex": value.real.hex(),
            "imag_hex": value.imag.hex(),
        }
    if isinstance(value, bytes):
        return {"scalar_type": "bytes", "hex": value.hex()}
    if isinstance(value, str):
        return value
    raise ValueError(
        f"Python protocol AST contains unsupported {type(value).__name__}"
    )


def _canonical_ast_node(node: ast.AST) -> dict[str, object]:
    fields: dict[str, object] = {}
    for field_name, raw_value in ast.iter_fields(node):
        if raw_value is None:
            if isinstance(node, ast.Constant) and field_name == "value":
                fields[field_name] = {"scalar_type": "none"}
            continue
        if isinstance(raw_value, (list, tuple)) and not raw_value:
            continue
        if (
            field_name == "body"
            and isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            )
            and isinstance(raw_value, list)
            and raw_value
            and _is_leading_docstring(raw_value[0])
        ):
            raw_value = raw_value[1:]
            if not raw_value:
                continue
        fields[field_name] = _canonical_ast_scalar(raw_value)
    return {"node": type(node).__name__, "fields": fields}


def _reject_docstring_introspection(node: ast.AST, *, symbol: str) -> None:
    for candidate in ast.walk(node):
        if (
            isinstance(candidate, ast.Name)
            and candidate.id in {"__doc__", "getdoc"}
        ) or (
            isinstance(candidate, ast.Attribute)
            and candidate.attr in {"__doc__", "getdoc"}
        ):
            raise ValueError(
                "Python protocol v1 cannot exclude an introspected docstring: "
                f"{symbol}"
            )


def canonical_python_ast_bytes(
    path: Path,
    symbols: tuple[str, ...],
) -> bytes:
    """Serialize the dependency closure of selected module symbols."""

    if not isinstance(symbols, tuple) or not symbols:
        raise ValueError("Python protocol symbols must be a non-empty tuple")
    if len(set(symbols)) != len(symbols):
        raise ValueError("Python protocol symbols must not contain duplicates")
    for symbol in symbols:
        if not isinstance(symbol, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            symbol,
        ):
            raise ValueError(f"invalid Python protocol symbol: {symbol!r}")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise ValueError(f"Python protocol source cannot be parsed: {path}") from exc
    bindings = _module_bindings(tree)
    missing = sorted(set(symbols) - set(bindings))
    if missing:
        raise ValueError(
            "Python protocol symbol is missing: " + ", ".join(missing)
        )

    admitted: dict[str, ast.stmt] = {}
    pending = list(symbols)
    while pending:
        name = pending.pop()
        if name in admitted:
            continue
        candidates = bindings[name]
        if len(candidates) != 1:
            raise ValueError(f"selected Python protocol symbol is rebound: {name}")
        node = candidates[0]
        _reject_docstring_introspection(node, symbol=name)
        admitted[name] = node
        dependencies = {
            reference.id
            for reference in ast.walk(node)
            if isinstance(reference, ast.Name)
            and isinstance(reference.ctx, ast.Load)
            and reference.id in bindings
        }
        pending.extend(sorted(dependencies - set(admitted), reverse=True))

    payload = {
        "hash_mode": "python_ast_v1",
        "roots": list(symbols),
        "bindings": [
            {
                "name": name,
                "ast": _canonical_ast_node(admitted[name]),
            }
            for name in sorted(admitted)
        ],
    }
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        + b"\n"
    )


def canonical_python_ast_sha256(
    path: Path,
    symbols: tuple[str, ...],
) -> str:
    return hashlib.sha256(canonical_python_ast_bytes(path, symbols)).hexdigest()


def _validate_source_set(
    source_set: SourceSet,
    label: str,
    *,
    root: Path,
    verify_assets: bool,
) -> None:
    if not isinstance(source_set, SourceSet):
        raise ValueError(f"{label} must be a SourceSet")
    if source_set.status == "not_applicable":
        if source_set.sources:
            raise ValueError(
                f"{label} not_applicable sets cannot contain sources"
            )
        _require_text(source_set.reason, f"{label}.reason")
        return
    if source_set.status != "declared" or not source_set.sources:
        raise ValueError(
            f"{label} must declare at least one source or be not_applicable"
        )
    if source_set.reason is not None:
        raise ValueError(f"{label} declared sets cannot carry a reason")
    identities: set[tuple[str, str, str]] = set()
    for index, source in enumerate(source_set.sources):
        if not isinstance(source, EvidenceSource):
            raise ValueError(f"{label}[{index}] must be an EvidenceSource")
        name = _require_text(source.name, f"{label}[{index}].name")
        locator = _require_text(
            source.locator,
            f"{label}[{index}].locator",
        )
        version = _require_text(
            source.version,
            f"{label}[{index}].version",
        )
        identity = (name, locator, version)
        if identity in identities:
            raise ValueError(f"{label} contains a duplicate source")
        identities.add(identity)
        if source.hash_mode not in _ALLOWED_SOURCE_HASH_MODES:
            raise ValueError(f"{label}[{index}].hash_mode is not admitted")
        if not isinstance(source.symbols, tuple):
            raise ValueError(f"{label}[{index}].symbols must be a tuple")
        if source.local:
            relative = _safe_relative_path(
                locator,
                f"{label}[{index}].locator",
            )
            if not isinstance(source.sha256, str) or not _SHA256_RE.fullmatch(
                source.sha256
            ):
                raise ValueError(
                    f"{label}[{index}] local source requires lowercase SHA-256"
                )
            if verify_assets:
                path = root.joinpath(*relative.parts)
                try:
                    payload = path.read_bytes()
                except OSError as exc:
                    raise ValueError(
                        f"{label}[{index}] local source is unavailable: {path}"
                    ) from exc
                if source.hash_mode == "bytes":
                    if source.symbols:
                        raise ValueError(
                            f"{label}[{index}] byte source cannot name symbols"
                        )
                    digest = hashlib.sha256(payload).hexdigest()
                else:
                    if relative.suffix != ".py":
                        raise ValueError(
                            f"{label}[{index}] Python AST source must be .py"
                        )
                    digest = canonical_python_ast_sha256(
                        path,
                        source.symbols,
                    )
                if digest != source.sha256:
                    raise ValueError(
                        f"{label}[{index}] SHA-256 mismatch: "
                        f"expected {source.sha256}, got {digest}"
                    )
        elif source.sha256 is not None:
            if not _SHA256_RE.fullmatch(source.sha256):
                raise ValueError(
                    f"{label}[{index}].sha256 must be lowercase SHA-256"
                )
            if source.hash_mode != "bytes" or source.symbols:
                raise ValueError(
                    f"{label}[{index}] non-local source cannot use a local canonicalizer"
                )
        elif source.hash_mode != "bytes" or source.symbols:
            raise ValueError(
                f"{label}[{index}] non-local source cannot use a local canonicalizer"
            )


def _validate_comparison(comparison: Comparison, index: int) -> None:
    label = f"comparisons[{index}]"
    if not isinstance(comparison, Comparison):
        raise ValueError(f"{label} must be a Comparison")
    _require_text(comparison.metric, f"{label}.metric")
    _require_text(comparison.unit, f"{label}.unit")
    _require_text(comparison.basis, f"{label}.basis")
    if comparison.rule not in _ALLOWED_COMPARISON_RULES:
        raise ValueError(f"{label}.rule is not admitted")
    thresholds = {
        "absolute": comparison.absolute,
        "relative": comparison.relative,
    }
    for name, threshold in thresholds.items():
        if threshold is None:
            continue
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(float(threshold))
            or float(threshold) < 0.0
        ):
            raise ValueError(
                f"{label}.{name} must be finite and non-negative"
            )
    if comparison.rule == "exact":
        if any(value is not None for value in thresholds.values()):
            raise ValueError(f"{label} exact comparisons cannot use tolerance")
    elif comparison.rule == "absolute" and comparison.absolute is None:
        raise ValueError(f"{label}.absolute is required")
    elif comparison.rule == "relative" and comparison.relative is None:
        raise ValueError(f"{label}.relative is required")
    elif comparison.rule == "absolute_or_relative" and all(
        value is None for value in thresholds.values()
    ):
        raise ValueError(f"{label} requires an absolute or relative tolerance")
    elif comparison.rule in {"circular", "vector_angle", "interval"} and (
        comparison.absolute is None
    ):
        raise ValueError(f"{label}.absolute is required")


def _callable_qualnames(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            result.add(".".join((*self.stack, node.name)))
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        visit_FunctionDef = _visit_function
        visit_AsyncFunctionDef = _visit_function

    Visitor().visit(tree)
    return result


def _validate_coverage_target(
    target: CoverageTarget,
    index: int,
    *,
    root: Path,
    verify_assets: bool,
) -> None:
    label = f"coverage_targets[{index}]"
    if not isinstance(target, CoverageTarget):
        raise ValueError(f"{label} must be a coverage target")
    relative = _safe_relative_path(target.path, f"{label}.path")
    if relative.suffix != ".py":
        raise ValueError(f"{label}.path must name one Python source file")
    if not _QUALNAME_RE.fullmatch(target.qualname):
        raise ValueError(f"{label}.qualname is not an exact Python qualname")
    if (
        not isinstance(target.phases, tuple)
        or not target.phases
        or not set(target.phases) <= _ALLOWED_COVERAGE_PHASES
        or len(set(target.phases)) != len(target.phases)
    ):
        raise ValueError(f"{label} coverage phases are invalid")
    if type(target.protected) is not bool:
        raise ValueError(f"{label}.protected must be boolean")
    if verify_assets:
        source_path = root.joinpath(*relative.parts)
        if not source_path.is_file():
            raise ValueError(f"{label}.path does not exist: {target.path}")
        try:
            qualnames = _callable_qualnames(source_path)
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise ValueError(f"{label}.path cannot be inspected") from exc
        if target.qualname not in qualnames:
            raise ValueError(
                f"{label}.qualname does not exist in {target.path}: "
                f"{target.qualname}"
            )


def _validate_nodeid(
    nodeid: str,
    index: int,
    *,
    root: Path,
    verify_assets: bool,
) -> None:
    label = f"nodeids[{index}]"
    _require_text(nodeid, label)
    if "[" in nodeid or "\\" in nodeid or "::" not in nodeid:
        raise ValueError(
            f"{label} must be an unparameterized exact base nodeid"
        )
    path_text, *object_parts = nodeid.split("::")
    relative = _safe_relative_path(path_text, f"{label} path")
    if (
        not relative.parts
        or relative.parts[0] != "tests"
        or relative.suffix != ".py"
        or not object_parts
        or any(not part for part in object_parts)
    ):
        raise ValueError(f"{label} is not a repository test nodeid")
    qualname = ".".join(object_parts)
    if not _QUALNAME_RE.fullmatch(qualname):
        raise ValueError(
            f"{label} object path is not an exact Python qualname"
        )
    if verify_assets:
        test_path = root.joinpath(*relative.parts)
        if not test_path.is_file():
            raise ValueError(f"{label} test file does not exist")
        try:
            qualnames = _callable_qualnames(test_path)
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise ValueError(f"{label} test file cannot be inspected") from exc
        if qualname not in qualnames:
            raise ValueError(
                f"{label} test callable does not exist in {path_text}: "
                f"{qualname}"
            )


def validate_contract(
    contract: EvidenceContract,
    *,
    root: Path,
    verify_assets: bool,
) -> None:
    """Reject incomplete, ambiguous, stale, or class-incoherent claims."""

    if not isinstance(contract, EvidenceContract):
        raise ValueError("registry value must be an EvidenceContract")
    if not _CLAIM_ID_RE.fullmatch(contract.claim_id):
        raise ValueError("claim_id must be a stable uppercase ASCII slug")
    _require_text(contract.product_surface, "product_surface")
    if not isinstance(contract.evidence_class, EvidenceClass):
        raise ValueError("evidence_class is not recognized")
    _require_text(contract.governing_object, "governing_object")
    _require_text_tuple(contract.nodeids, "nodeids")
    for index, nodeid in enumerate(contract.nodeids):
        _validate_nodeid(
            nodeid,
            index,
            root=root,
            verify_assets=verify_assets,
        )
    _require_text_tuple(contract.proves, "proves")
    _require_text_tuple(contract.does_not_prove, "does_not_prove")
    _validate_source_set(
        contract.authorities,
        "authorities",
        root=root,
        verify_assets=verify_assets,
    )
    _validate_source_set(
        contract.fixtures,
        "fixtures",
        root=root,
        verify_assets=verify_assets,
    )
    _validate_source_set(
        contract.corpora,
        "corpora",
        root=root,
        verify_assets=verify_assets,
    )
    for label in (
        "frame",
        "origin",
        "timescale",
        "correction_policy",
        "bodies",
        "interval",
        "resource_capability",
    ):
        _validate_declared_field(getattr(contract, label), label)
    if not isinstance(contract.comparisons, tuple) or not contract.comparisons:
        raise ValueError("comparisons must be a non-empty tuple")
    for index, comparison in enumerate(contract.comparisons):
        _validate_comparison(comparison, index)
    execution_paths = _require_text_tuple(
        contract.execution_paths,
        "execution_paths",
    )
    _require_text_tuple(contract.exclusions, "exclusions")
    _require_text_tuple(contract.expected_refusal, "expected_refusal")
    if (
        not isinstance(contract.coverage_targets, tuple)
        or not contract.coverage_targets
    ):
        raise ValueError("coverage_targets must be a non-empty tuple")
    target_identities: set[tuple[str, str, tuple[str, ...]]] = set()
    for index, target in enumerate(contract.coverage_targets):
        _validate_coverage_target(
            target,
            index,
            root=root,
            verify_assets=verify_assets,
        )
        identity = (target.path, target.qualname, target.phases)
        if identity in target_identities:
            raise ValueError("coverage_targets contains a duplicate target")
        target_identities.add(identity)
    if contract.evidence_class is EvidenceClass.AUTHORITY and (
        contract.authorities.status != "declared"
    ):
        raise ValueError("authority evidence requires a named authority")
    if contract.evidence_class is EvidenceClass.CORROBORATION and (
        contract.corpora.status != "declared"
    ):
        raise ValueError("corroboration evidence requires a named comparator corpus")
    if contract.evidence_class is EvidenceClass.REGRESSION and (
        contract.fixtures.status != "declared"
        and contract.corpora.status != "declared"
    ):
        raise ValueError("regression evidence requires a bound fixture or corpus")
    if contract.evidence_class is EvidenceClass.NATIVE_PARITY:
        has_python = any(path.startswith("python:") for path in execution_paths)
        has_native = any(path.startswith("native:") for path in execution_paths)
        if not (has_python and has_native):
            raise ValueError(
                "native_parity evidence requires both python and native paths"
            )


def _field_payload(field: DeclaredField) -> dict[str, object]:
    if field.status == "declared":
        return {"status": "declared", "value": field.value}
    return {"status": "not_applicable", "reason": field.reason}


def _source_set_payload(source_set: SourceSet) -> dict[str, object]:
    if source_set.status == "not_applicable":
        return {
            "status": "not_applicable",
            "reason": source_set.reason,
        }
    return {
        "status": "declared",
        "sources": [
            {
                "name": source.name,
                "locator": source.locator,
                "version": source.version,
                "sha256": source.sha256,
                "local": source.local,
                "hash_mode": source.hash_mode,
                "symbols": list(source.symbols),
            }
            for source in source_set.sources
        ],
    }


def contract_payload(contract: EvidenceContract) -> dict[str, object]:
    """Return the canonical JSON-safe representation of one contract."""

    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "claim_id": contract.claim_id,
        "product_surface": contract.product_surface,
        "evidence_class": contract.evidence_class.value,
        "governing_object": contract.governing_object,
        "nodeids": list(contract.nodeids),
        "proves": list(contract.proves),
        "does_not_prove": list(contract.does_not_prove),
        "authorities": _source_set_payload(contract.authorities),
        "fixtures": _source_set_payload(contract.fixtures),
        "corpora": _source_set_payload(contract.corpora),
        "frame": _field_payload(contract.frame),
        "origin": _field_payload(contract.origin),
        "timescale": _field_payload(contract.timescale),
        "correction_policy": _field_payload(contract.correction_policy),
        "comparisons": [
            {
                "metric": comparison.metric,
                "unit": comparison.unit,
                "rule": comparison.rule,
                "absolute": comparison.absolute,
                "relative": comparison.relative,
                "basis": comparison.basis,
            }
            for comparison in contract.comparisons
        ],
        "bodies": _field_payload(contract.bodies),
        "interval": _field_payload(contract.interval),
        "resource_capability": _field_payload(contract.resource_capability),
        "execution_paths": list(contract.execution_paths),
        "exclusions": list(contract.exclusions),
        "expected_refusal": list(contract.expected_refusal),
        "coverage_targets": [
            {
                "path": target.path,
                "qualname": target.qualname,
                "phases": list(target.phases),
                "protected": target.protected,
            }
            for target in contract.coverage_targets
        ],
    }


def canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        + b"\n"
    )


def contract_sha256(contract: EvidenceContract) -> str:
    return hashlib.sha256(canonical_json_bytes(contract_payload(contract))).hexdigest()


def validate_registry(
    registry: Mapping[str, EvidenceContract],
    *,
    root: Path,
    verify_assets: bool,
) -> None:
    """Validate registry identity, order, bindings, and every contract."""

    if not isinstance(registry, Mapping) or not registry:
        raise ValueError("contract registry must be a non-empty mapping")
    claim_ids = tuple(registry)
    if claim_ids != tuple(sorted(claim_ids)):
        raise ValueError("contract registry must be sorted by claim_id")
    bound_nodeids: dict[str, str] = {}
    for claim_id, contract in registry.items():
        if claim_id != contract.claim_id:
            raise ValueError("contract registry key must equal claim_id")
        validate_contract(
            contract,
            root=root,
            verify_assets=verify_assets,
        )
        for nodeid in contract.nodeids:
            previous = bound_nodeids.setdefault(nodeid, claim_id)
            if previous != claim_id:
                raise ValueError(
                    f"nodeid {nodeid} is bound to multiple validation claims"
                )


def freeze_registry(
    contracts: tuple[EvidenceContract, ...],
) -> Mapping[str, EvidenceContract]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for contract in contracts:
        if contract.claim_id in seen:
            duplicates.add(contract.claim_id)
        seen.add(contract.claim_id)
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate claim_id values: {duplicate_list}")
    registry = {contract.claim_id: contract for contract in contracts}
    return MappingProxyType(dict(sorted(registry.items())))


def synthetic_registry() -> Mapping[str, EvidenceContract]:
    """Return a complete one-claim registry for isolated plugin canaries."""

    contract = EvidenceContract(
        claim_id="MOIRA-TEST-CLAIM-V1",
        product_surface="synthetic product surface",
        evidence_class=EvidenceClass.INVARIANT,
        governing_object="synthetic independently derived invariant",
        nodeids=("tests/unit/test_probe.py::test_probe",),
        proves=("the synthetic relation holds",),
        does_not_prove=("external truth",),
        authorities=SourceSet.not_applicable(
            "the invariant has no external authority"
        ),
        fixtures=SourceSet.not_applicable("the invariant has no fixture"),
        corpora=SourceSet.not_applicable("the invariant has no corpus"),
        frame=DeclaredField.declared("synthetic frame"),
        origin=DeclaredField.declared("synthetic origin"),
        timescale=DeclaredField.not_applicable("time is not an input"),
        correction_policy=DeclaredField.not_applicable(
            "no corrections are applied"
        ),
        comparisons=(
            Comparison(
                metric="synthetic equality",
                unit="dimensionless",
                rule="exact",
                basis="integer identity is exact",
            ),
        ),
        bodies=DeclaredField.not_applicable("no body is present"),
        interval=DeclaredField.not_applicable("no interval is present"),
        resource_capability=DeclaredField.not_applicable(
            "the claim is resource-free"
        ),
        execution_paths=("python:tests.unit.test_probe.test_probe",),
        exclusions=("hostile in-process evidence forgery",),
        expected_refusal=("malformed markers fail collection",),
        coverage_targets=(
            CoverageTarget(
                path="tests/unit/test_probe.py",
                qualname="test_probe",
                phases=("run",),
                protected=False,
            ),
        ),
    )
    return freeze_registry((contract,))

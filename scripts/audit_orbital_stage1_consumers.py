"""Generate and verify the Orbital Core Stage 1 consumer inventory.

The inventory is deliberately source-derived.  Python call sites are found with
the AST; the small native surface is scanned as C++ source because no compiler
database is required for this release gate.  A newly discovered source file has
no policy by default and therefore fails the audit instead of being silently
classified.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]

READER_STARTING_FILES = (
    "moira/_facade_classical.py",
    "moira/_spk_body_kernel.py",
    "moira/asteroids.py",
    "moira/comets.py",
    "moira/daf_writer_ui.py",
    "moira/draconic.py",
    "moira/eclipse.py",
    "moira/lunar_limb.py",
    "moira/mundane.py",
    "moira/nodes.py",
    "moira/orbits.py",
    "moira/phase.py",
    "moira/phenomena.py",
    "moira/planetary_nodes.py",
    "moira/planets.py",
    "moira/shadbala.py",
    "moira/spk_reader.py",
    "moira/stars.py",
    "src/native/bindings/moira_native.cpp",
)

FRAME_STARTING_FILES = (
    "moira/comets.py",
    "moira/coordinates.py",
    "moira/corrections.py",
    "moira/eclipse.py",
    "moira/eclipse_besselian.py",
    "moira/galactic.py",
    "moira/lunar_eclipse_global.py",
    "moira/lunar_limb.py",
    "moira/nodes.py",
    "moira/occultations.py",
    "moira/planetary_nodes.py",
    "moira/planets.py",
    "moira/precession.py",
    "moira/sky/position.py",
)

READER_CALLS = frozenset(
    {
        "position",
        "position_and_velocity",
        "has_segment_at",
        "coverage",
        "evaluator",
        "_segment_for",
        "_segment_for_tdb",
        "_load_native_evaluator",
        "load_segment_evaluator",
        "load_spk_segment_evaluator",
        "NativePlanetaryEvaluator",
        "segment_position",
        "segment_position_and_velocity",
        "batch_segment_position_requests",
        "batch_segment_position_and_velocity",
        "evaluator_tdb",
        "position_and_velocity_tdb_with_receipt",
        "coverage_intervals_tdb",
    }
)
FRAME_CALLS = frozenset(
    {
        "apply_frame_bias",
        "apply_iau2006_frame_bias",
        "precession_matrix",
        "precession_matrix_equatorial",
        "icrf_to_true_ecliptic",
    }
)
RAW_TDB_CALLS = frozenset(
    {
        "_segment_for_tdb",
        "segment_position",
        "segment_position_and_velocity",
        "batch_segment_position_requests",
        "batch_segment_position_and_velocity",
        "evaluator_tdb",
        "position_and_velocity_tdb_with_receipt",
        "coverage_intervals_tdb",
    }
)
READER_RECEIVER_MARKERS = (
    "reader",
    "kernel",
    "segment",
    "seg",
    "handle",
    "evaluator",
)
MANUAL_FRAME_SCOPES = frozenset(
    {
        "_compose_rotation_matrix",
        "_earth_fixed_lunar_reception_vector",
        "_earth_fixed_solar_shadow",
        "_fw2m",
        "_observer_position_icrf",
        "_observer_velocity_icrf",
        "orbital_frame_transform",
    }
)


class OrbitalConsumerAuditError(RuntimeError):
    """Raised when the Stage 1 inventory or a protected boundary drifts."""


@dataclass(frozen=True)
class Site:
    category: str
    path: str
    line: int
    scope: str
    call: str
    source: str
    ordinal: int = 0

    @property
    def key(self) -> str:
        return f"{self.path}::{self.scope}::{self.call}::{self.ordinal}"


@dataclass(frozen=True)
class Decision:
    current: str
    route: str
    moves: str
    owner: str
    disposition: str


PUBLIC_TT_READER_FILES = frozenset(
    {
        "moira/asteroids.py",
        "moira/comets.py",
        "moira/daf_writer_ui.py",
        "moira/eclipse.py",
        "moira/lunar_limb.py",
        "moira/mundane.py",
        "moira/nodes.py",
        "moira/orbits.py",
        "moira/phase.py",
        "moira/phenomena.py",
        "moira/planetary_nodes.py",
        "moira/planets.py",
        "moira/shadbala.py",
        "moira/stars.py",
        "moira/transits_aspects.py",
        "moira/transits_equatorial.py",
    }
)
INTERNAL_READER_FILES = frozenset(
    {
        "moira/_orbital_state.py",
        "moira/_spk_body_kernel.py",
        "moira/spk_reader.py",
        "src/native/bindings/moira_native.cpp",
        "src/native/include/daf.hpp",
        "src/native/include/evaluators.hpp",
        "src/native/include/planetary_evaluator.hpp",
    }
)

DUPLICATE_BIAS_REPAIRED_FILES = frozenset(
    {
        "moira/comets.py",
        "moira/eclipse.py",
        "moira/lunar_limb.py",
        "moira/nodes.py",
        "moira/occultations.py",
        "moira/planetary_nodes.py",
        "moira/planets.py",
        "src/native/include/visibility.hpp",
        "src/native/include/planetary_evaluator.hpp",
    }
)
INHERITED_FRAME_FILES = frozenset(
    {
        "moira/coordinates.py",
        "moira/corrections.py",
        "moira/cosmic_references.py",
        "moira/deep_sky.py",
        "moira/eclipse_besselian.py",
        "moira/galactic.py",
        "moira/lunar_eclipse_global.py",
        "moira/phase.py",
        "moira/stars.py",
        "moira/sky/position.py",
        "src/native/include/visibility.hpp",
    }
)

CLASSIFIED_READER_FILES = (
    set(READER_STARTING_FILES)
    | PUBLIC_TT_READER_FILES
    | INTERNAL_READER_FILES
    | {"moira/_orbital_state.py", "moira/transits_aspects.py"}
)
CLASSIFIED_FRAME_FILES = (
    set(FRAME_STARTING_FILES)
    | DUPLICATE_BIAS_REPAIRED_FILES
    | INHERITED_FRAME_FILES
    | {
        "moira/_orbital_frames.py",
        "src/native/bindings/moira_native.cpp",
        "src/native/include/precession.hpp",
    }
)


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _receiver(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        return ast.unparse(node.func.value)
    return ""


def _scope_for(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
    return "<module>"


def _is_reader_call(path: str, node: ast.Call, name: str) -> bool:
    if name not in READER_CALLS:
        return False
    if path in READER_STARTING_FILES or path in INTERNAL_READER_FILES:
        return True
    if name not in {"position", "position_and_velocity", "coverage", "evaluator"}:
        return True
    receiver = _receiver(node).lower()
    return any(marker in receiver for marker in READER_RECEIVER_MARKERS)


def _manual_frame_call(path: str, scope: str, node: ast.Call, name: str) -> bool:
    if name != "mat_mul" or scope not in MANUAL_FRAME_SCOPES:
        return False
    source = ast.unparse(node).lower()
    return any(token in source for token in ("nut", "prec", "bias", "rnpb"))


def _python_sites(path: Path) -> list[Site]:
    relative = path.relative_to(REPO_ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    sites: list[Site] = []
    calls = sorted(
        (node for node in ast.walk(tree) if isinstance(node, ast.Call)),
        key=lambda node: (node.lineno, node.col_offset),
    )
    for node in calls:
        name = _call_name(node)
        if name is None:
            continue
        scope = _scope_for(node, parents)
        source = ast.unparse(node).replace("\n", " ")
        if _is_reader_call(relative, node, name):
            sites.append(Site("reader", relative, node.lineno, scope, name, source))
        if name in FRAME_CALLS:
            sites.append(Site("frame", relative, node.lineno, scope, name, source))
        elif _manual_frame_call(relative, scope, node, name):
            sites.append(
                Site(
                    "frame",
                    relative,
                    node.lineno,
                    scope,
                    "manual_frame_composition",
                    source,
                )
            )
    return sites


_NATIVE_NAMES = tuple(
    sorted(
        READER_CALLS
        | FRAME_CALLS
        | {
            "batch_segment_position",
            "batch_segment_position_and_velocity",
        },
        key=len,
        reverse=True,
    )
)
_NATIVE_NAME_RE = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in _NATIVE_NAMES) + r")\b"
)


def _native_sites(path: Path) -> list[Site]:
    relative = path.relative_to(REPO_ROOT).as_posix()
    sites: list[Site] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        for match in _NATIVE_NAME_RE.finditer(line):
            name = match.group(1)
            following = line[match.end() :].lstrip()
            is_invocation_or_definition = following.startswith("(")
            is_python_binding = f'.def("{name}"' in line
            is_bound_class = name == "NativePlanetaryEvaluator" and (
                "py::class_" in line or line.startswith("class ")
            )
            if not (
                is_invocation_or_definition or is_python_binding or is_bound_class
            ):
                continue
            category = "frame" if name in FRAME_CALLS else "reader"
            sites.append(
                Site(category, relative, line_number, "<native>", name, line)
            )
        if "Mat3::mul" in line and any(
            token in line.lower() for token in ("nut", "prec", "bias", "rnpb")
        ):
            sites.append(
                Site(
                    "frame",
                    relative,
                    line_number,
                    "<native>",
                    "manual_frame_composition",
                    line,
                )
            )
    return sites


def discover_sites() -> tuple[Site, ...]:
    raw: list[Site] = []
    for path in sorted((REPO_ROOT / "moira").rglob("*.py")):
        raw.extend(_python_sites(path))
    for suffix in ("*.hpp", "*.cpp"):
        for path in sorted((REPO_ROOT / "src" / "native").rglob(suffix)):
            raw.extend(_native_sites(path))

    counters: dict[tuple[str, str, str, str], int] = {}
    result: list[Site] = []
    for site in sorted(raw, key=lambda row: (row.path, row.line, row.category, row.call)):
        base = (site.category, site.path, site.scope, site.call)
        ordinal = counters.get(base, 0) + 1
        counters[base] = ordinal
        result.append(
            Site(
                site.category,
                site.path,
                site.line,
                site.scope,
                site.call,
                site.source,
                ordinal,
            )
        )
    return tuple(result)


def _reader_decision(site: Site) -> Decision:
    if site.path not in CLASSIFIED_READER_FILES:
        raise OrbitalConsumerAuditError(
            f"unclassified reader/evaluator source: {site.path} ({site.key})"
        )
    if site.path == "moira/draconic.py":
        return Decision(
            "derived-chart callback, not an SPK epoch",
            "documented no-change",
            "no",
            "tests/unit/test_draconic.py",
            "non-SPK name collision classified",
        )
    if site.call in {"coverage", "_load_native_evaluator", "load_segment_evaluator", "load_spk_segment_evaluator", "NativePlanetaryEvaluator"}:
        return Decision(
            "date-free kernel capability",
            "date-free capability",
            "no",
            "tests/unit/test_orbital_stage1_consumer_inventory.py",
            "retained; no clock value crosses this call",
        )
    if site.call in RAW_TDB_CALLS or (
        site.path in {"moira/_spk_body_kernel.py", "moira/spk_reader.py"}
        and site.scope in {"_evaluate", "evaluator_tdb"}
    ):
        return Decision(
            "explicit JD(TDB)",
            "private explicit TDB capability",
            "no additional movement",
            "tests/unit/test_spk_reader.py; tests/unit/test_orbital_state_routes.py",
            "migrated; raw SPK epoch is named TDB",
        )
    if site.path == "moira/_orbital_state.py":
        return Decision(
            "bound JD(TDB) from OrbitalTimeReceipt",
            "private atomic TDB state-with-receipt route",
            "new surface",
            "tests/unit/test_orbital_state_routes.py",
            "admitted strict state route",
        )
    if site.path == "moira/spk_reader.py":
        return Decision(
            "JD(TT) compatibility boundary",
            "public TT adapter or preserved third-party TT protocol",
            "built-ins: one TT-to-TDB correction; third-party: no",
            "tests/unit/test_spk_reader.py",
            "retained compatibility boundary",
        )
    if site.path in PUBLIC_TT_READER_FILES:
        return Decision(
            "JD(TT) at public reader boundary",
            "public TT adapter; exactly one internal TT-to-TDB conversion",
            "yes, bounded reader-clock correction",
            "tests/unit/test_orbital_stage1_consumer_inventory.py",
            "migrated or verified TT-facing",
        )
    if site.path in INTERNAL_READER_FILES:
        return Decision(
            "raw JD(TDB) native substrate",
            "private explicit TDB capability",
            "no additional movement",
            "tests/unit/test_adversarial_native_runtime_verification.py",
            "retained internal TDB boundary",
        )
    raise OrbitalConsumerAuditError(f"reader decision missing: {site.key}")


def _frame_decision(site: Site) -> Decision:
    if site.path not in CLASSIFIED_FRAME_FILES:
        raise OrbitalConsumerAuditError(
            f"unclassified frame-transform source: {site.path} ({site.key})"
        )
    if site.path == "moira/_orbital_frames.py":
        return Decision(
            "ICRF state plus JD(TT) frame epoch",
            "private SOFA-derived orbital frame router",
            "new surface",
            "tests/unit/test_orbital_frames.py",
            "admitted frame construction",
        )
    if site.path in {
        "moira/precession.py",
        "src/native/include/precession.hpp",
    }:
        return Decision(
            "ICRS axes plus JD(TT)",
            "bias-inclusive Pmat06/Ltpb-equivalent router",
            "modern: no; long-term: one missing bias restored",
            "tests/unit/test_orbital_frames.py",
            "bias ownership repaired on both branches",
        )
    if site.path in {
        "moira/corrections.py",
        "src/native/bindings/moira_native.cpp",
    } and site.call in {"apply_frame_bias", "apply_iau2006_frame_bias"}:
        return Decision(
            "standalone ICRF vector",
            "low-level explicit bias primitive",
            "no",
            "tests/unit/test_planetary_frame_contracts.py",
            "retained primitive; forbidden before bias-owning route",
        )
    if site.path in DUPLICATE_BIAS_REPAIRED_FILES:
        return Decision(
            "raw ICRF vector plus JD(TT)",
            "single bias-owning precession/nutation route",
            "yes, duplicate modern bias removed",
            "tests/unit/test_orbital_stage1_consumer_inventory.py",
            "explicit predecessor bias removed",
        )
    if site.path in INHERITED_FRAME_FILES:
        return Decision(
            "raw ICRF vector plus JD(TT)",
            "bias-inclusive precession followed by existing nutation",
            "modern: no; long-term: one missing bias restored",
            "tests/unit/test_orbital_stage1_consumer_inventory.py",
            "verified single-owner transform",
        )
    raise OrbitalConsumerAuditError(f"frame decision missing: {site.key}")


def decision_for(site: Site) -> Decision:
    if site.category == "reader":
        return _reader_decision(site)
    return _frame_decision(site)


def validate_source_guards(sites: tuple[Site, ...]) -> None:
    failures: list[str] = []
    for site in sites:
        decision_for(site)
        if site.call == "_segment_for":
            failures.append(f"ambiguous raw segment selection returned: {site.key}")
        if site.call in RAW_TDB_CALLS and re.search(
            r"\b(?:jd|epoch)(?:_\w+)?_tt\b", site.source, re.IGNORECASE
        ):
            failures.append(f"TT value passed to raw TDB call: {site.key}")

    native_visibility = (
        REPO_ROOT / "src" / "native" / "include" / "visibility.hpp"
    ).read_text(encoding="utf-8")
    if "apply_iau2006_frame_bias" in native_visibility:
        failures.append(
            "native visibility retains explicit bias before bias-owning precession"
        )
    native_planets = (
        REPO_ROOT / "src" / "native" / "include" / "planetary_evaluator.hpp"
    ).read_text(encoding="utf-8")
    if "apply_frame_bias" in native_planets:
        failures.append("native all-planets evaluator retains explicit frame bias")
    if "double epoch_tdb" not in native_planets:
        failures.append("native all-planets evaluator lacks an explicit TDB epoch")

    for path in READER_STARTING_FILES + FRAME_STARTING_FILES:
        if not (REPO_ROOT / path).is_file():
            failures.append(f"governing inventory path is missing: {path}")
    if failures:
        raise OrbitalConsumerAuditError("\n".join(failures))


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("`", "'")


def render_inventory() -> str:
    sites = discover_sites()
    validate_source_guards(sites)
    counts: dict[tuple[str, str], int] = {}
    for site in sites:
        key = (site.category, site.path)
        counts[key] = counts.get(key, 0) + 1

    lines = [
        "# Orbital Core Stage 1 Consumer Inventory",
        "",
        "Generated by `scripts/audit_orbital_stage1_consumers.py`. Do not hand-edit.",
        "",
        "This inventory freezes the Stage 1 reader-clock and frame-ownership decisions.",
        "The clock authority is NAIF `naif0012.tls`; frame construction is checked",
        "against official IAU SOFA Issue 2023-10-11 C output. JPL Horizons supplies",
        "the independent state/element comparison corpus.",
        "",
        "## Governing-path coverage",
        "",
        "| Category | File | Discovered sites | Status |",
        "| --- | --- | ---: | --- |",
    ]
    for category, paths in (
        ("reader", READER_STARTING_FILES),
        ("frame", FRAME_STARTING_FILES),
    ):
        for path in paths:
            lines.append(
                f"| {category} | `{path}` | {counts.get((category, path), 0)} | classified |"
            )

    lines.extend(
        [
            "",
            "## Call-site decisions",
            "",
            "| Key | Line | Current scale/frame | Stage 1 route | Numeric movement | Test owner | Final disposition |",
            "| --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for site in sites:
        decision = decision_for(site)
        key = _escape(site.key)
        lines.append(
            "| "
            f"`{key}` | {site.line} | {_escape(decision.current)} | "
            f"{_escape(decision.route)} | {_escape(decision.moves)} | "
            f"{_escape(decision.owner)} | {_escape(decision.disposition)} |"
        )

    reader_count = sum(site.category == "reader" for site in sites)
    frame_count = sum(site.category == "frame" for site in sites)
    lines.extend(
        [
            "",
            "## Guard receipt",
            "",
            f"- Reader/evaluator sites: {reader_count}",
            f"- Frame-transform/composition sites: {frame_count}",
            "- Ambiguous `_segment_for(...)` calls: 0",
            "- TT-named arguments passed to raw TDB calls: 0",
            "- Explicit native visibility bias before bias-owning precession: 0",
            "- Native all-planets epoch contract: `epoch_tdb`",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", type=Path)
    mode.add_argument("--check", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        rendered = render_inventory()
    except (OSError, SyntaxError, OrbitalConsumerAuditError) as exc:
        print(f"orbital consumer audit failed: {exc}", file=sys.stderr)
        return 1

    target = args.write or args.check
    assert target is not None
    if not target.is_absolute():
        target = REPO_ROOT / target
    if args.write is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"wrote {target.relative_to(REPO_ROOT).as_posix()}")
        return 0
    if not target.is_file():
        print(f"inventory is missing: {target}", file=sys.stderr)
        return 1
    actual = target.read_text(encoding="utf-8")
    if actual != rendered:
        print(
            "orbital consumer inventory is stale; rerun with --write",
            file=sys.stderr,
        )
        return 1
    print("orbital consumer inventory is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

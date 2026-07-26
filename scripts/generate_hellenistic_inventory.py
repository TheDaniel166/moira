"""Generate the runtime-backed Hellenistic capability and REST inventories."""

from __future__ import annotations

import argparse
import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "HELLENISTIC_CAPABILITY_MATRIX.generated.md"
)
API_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "HELLENISTIC_API_INVENTORY.generated.md"
)
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "options", "head")


@dataclass(frozen=True, slots=True)
class Capability:
    """One governed Hellenistic or explicitly adjacent engine family."""

    capability_id: str
    capability: str
    status: str
    profile: str
    owner: str
    anchors: tuple[str, ...]
    evidence: str
    source: str
    caveat: str
    route_families: tuple[str, ...] = ()
    require_absent_from_curated: bool = False


CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        "whole_sign_frame",
        "Whole Sign chart frame and exact angles",
        "admitted",
        "included",
        "moira.hellenistic",
        ("HellenisticChartProfile", "hellenistic_chart_profile"),
        "profile hardening and exact-cusp tests",
        "policy and geometry contract",
        "The pure composer consumes validated Whole Sign cusps; the Moira wrapper owns chart computation.",
        ("Unified profile",),
    ),
    Capability(
        "whole_sign_aspects",
        "Whole Sign aspects, direction, and overcoming",
        "admitted",
        "included",
        "moira.aspects",
        ("find_whole_sign_aspects", "hellenistic_superiority_truth"),
        "typed truth, boundary, REST, and OpenAPI tests",
        "source references plus geometric invariants",
        "Tests validate declared geometry and typed non-evaluability, not astrological effects.",
        ("Hellenistic aspects",),
    ),
    Capability(
        "essential_dignity_components",
        "Typed essential dignity components",
        "admitted",
        "included",
        "moira.dignities",
        ("EssentialDignityComponentTruth", "calculate_dignities"),
        "atomic truth and contract-parity tests",
        "named table standards and source fixtures",
        "Legacy labels and scores are projections; the profile carries score-free components.",
        ("Dignities (mixed supporting surface)",),
    ),
    Capability(
        "sect_halb_hayz",
        "Sect, Halb, and Hayz",
        "admitted_qualified",
        "included with named medieval doctrine",
        "moira.dignities",
        ("SectTruth", "is_in_halb", "is_in_hayz"),
        "source-decision, boundary, and typed truth tests",
        "al-Qabisi and Bonatti via Dykes 2007",
        "Halb/Hayz is a medieval admission used by the classical condition layer; it is not relabeled as ancient Hellenistic doctrine.",
        ("Dignities (mixed supporting surface)",),
    ),
    Capability(
        "planetary_solar_phase",
        "Oriental/occidental solar phase",
        "admitted",
        "included",
        "moira.dignities",
        ("PlanetarySolarPhaseTruth", "planetary_solar_phase_truth"),
        "typed conjunction/opposition boundary tests",
        "declared geometric policy",
        "Exact conjunction/opposition is not evaluable; policy suppression cannot erase raw geometry.",
        ("Dignities (mixed supporting surface)",),
    ),
    Capability(
        "solar_proximity",
        "Cazimi, combust, under-sunbeams, and clear bands",
        "admitted_qualified",
        "included",
        "moira.dignities",
        ("SolarProximityTruth", "solar_proximity_truth"),
        "exclusive-band and policy-separation tests",
        "named policy thresholds",
        "Thresholds are explicit computation policy, not a claim of one universal ancient orb table.",
        ("Dignities (mixed supporting surface)",),
    ),
    Capability(
        "besieging",
        "Besieging dependency completeness and enclosure truth",
        "admitted_qualified",
        "included",
        "moira.dignities",
        ("BesiegingTruth", "besieging_truth"),
        "dependency, ambiguity, and fail-closed tests",
        "named enclosure policy",
        "The configured enclosure orb is policy; incomplete or ambiguous geometry cannot score.",
        ("Dignities (mixed supporting surface)",),
    ),
    Capability(
        "planetary_joys",
        "Planetary joy houses",
        "admitted",
        "included",
        "moira.dignities",
        ("PLANETARY_JOYS", "is_in_joy"),
        "independent source-owned golden",
        "Brennan 2013 synthesis with identified ancient locations",
        "The golden locks house assignments only and does not validate interpretive strength.",
        ("Dignities (mixed supporting surface)",),
    ),
    Capability(
        "dorothean_triplicity",
        "Dorothean day, night, and participating triplicity rulers",
        "admitted",
        "included",
        "moira.triplicity",
        ("TriplicityAssignment", "triplicity_assignment_for"),
        "independent full source-owned golden",
        "Dorotheus I.1, Pingree 1976",
        "Only the named Pingree doctrine is admitted; alternate traditions require separate doctrine members.",
        ("Triplicity",),
    ),
    Capability(
        "bounds",
        "Egyptian, Ptolemaic, and sect-explicit Chaldean bounds",
        "admitted",
        "included with selected policy",
        "moira.egyptian_bounds",
        ("EgyptianBoundTruth", "egyptian_bound_of"),
        "independent full/rule source goldens and every-boundary tests",
        "Ptolemy I.20/I.21, Robbins 1940",
        "The unified profile selects one explicit doctrine; the supporting API exposes all four admitted variants.",
        ("Egyptian bounds",),
    ),
    Capability(
        "chaldean_faces",
        "Ordinary Chaldean faces",
        "admitted_qualified",
        "included",
        "moira.decanates",
        ("DecanatePosition", "chaldean_face"),
        "independent 36-face cycle golden",
        "Agrippa II.37, J. F. translation 1651",
        "The identified witness is later; it validates the ordinary cycle without proving a Hellenistic date of origin.",
        ("Decanates (mixed supporting surface)",),
    ),
    Capability(
        "triplicity_decans",
        "Triplicity decan placement",
        "admitted_supporting",
        "not included",
        "moira.decanates",
        ("triplicity_decan",),
        "literal and exhaustive geometry tests",
        "Dorotheus and Valens source references",
        "This admitted supporting decanate is distinct from the profile's Chaldean-face component.",
        ("Decanates (mixed supporting surface)",),
    ),
    Capability(
        "profile_lots",
        "Fortune, Spirit, Valens Eros, and Valens Necessity",
        "admitted",
        "included",
        "moira.lots",
        ("LotsEvaluation", "evaluate_lots"),
        "independent formula/output golden and dependency truth tests",
        "Valens II.3, II.22, and IV.25",
        "The four-lot profile subset is source-locked and fails closed on missing luminaries.",
        ("Lots (mixed supporting surface)",),
    ),
    Capability(
        "broad_lots_catalog",
        "Heterogeneous full lots catalog",
        "admitted_qualified",
        "profile subset only",
        "moira.lots",
        ("PARTS_DEFINITIONS", "evaluate_lots"),
        "typed dependency coverage plus source-verification ledger",
        "multiple Hellenistic, medieval, and modern authorities",
        "The broad catalog is not one Hellenistic authority and is not fully source-goldened.",
        ("Lots (mixed supporting surface)",),
    ),
    Capability(
        "profections",
        "Annual/monthly profections and activation truth",
        "admitted_qualified",
        "annual profile component included",
        "moira.profections",
        ("ProfectionActivationTruth", "profection_schedule"),
        "cycle, dependency, civil-anniversary, and leap-day policy tests",
        "ancient sign-cycle doctrine plus explicit modern civil policy",
        "Completed civil anniversaries are a declared projection policy, not an ancient civil-calendar reconstruction.",
        ("Profections",),
    ),
    Capability(
        "decennials_l1_l2",
        "Decennials L1/L2",
        "admitted",
        "included",
        "moira.timelords",
        ("DecennialSequenceAssemblyTruth", "decennials"),
        "independent minor-period golden plus typed sequence tests",
        "Valens VI.6-8, Riley annotated pages 494-502",
        "Symbolic 30-day months are preserved separately from elapsed-Julian-day projection.",
        ("Decennials",),
    ),
    Capability(
        "zodiacal_releasing",
        "Zodiacal Releasing",
        "admitted_qualified",
        "included",
        "moira.timelords",
        ("ZRFortuneAngularityTruth", "zodiacal_releasing"),
        "Valens source-owned start-shift/circuit goldens plus typed angularity tests",
        "Valens IV.4, Riley annotated pages 329-333",
        "The source prose/editorial arithmetic governs the 211-month cap; interpretation is excluded.",
        ("Zodiacal Releasing",),
    ),
    Capability(
        "unified_profile",
        "Unified score-free Hellenistic chart profile",
        "admitted",
        "product contract",
        "moira.hellenistic",
        (
            "HellenisticChartProfile",
            "HellenisticProfilePolicy",
            "HellenisticProfileProvenance",
            "hellenistic_chart_profile",
        ),
        "engine, facade, serializer, REST, and OpenAPI parity tests",
        "composition of admitted atomic receipts",
        "This is non-interpretive composition and contains no chart-wide score, ranking, recommendation, or narrative.",
        ("Unified profile",),
    ),
    Capability(
        "hermetic_catalog",
        "Hermetic 36-name catalog identity",
        "source_catalog_quarantined",
        "excluded",
        "moira.hermetic_decans",
        ("HERMETIC_DECAN_CATALOG", "HERMETIC_CATALOG_SOURCE_ID"),
        "source-locked literal catalog tests",
        "Gundel 1936, pages 379-383; Harley MS 3731",
        "Names, faces, and edition pages are reconstructed, but the module remains outside curated imports and REST.",
        require_absent_from_curated=True,
    ),
    Capability(
        "hermetic_geometry",
        "Hermetic longitude and rising geometry",
        "quarantined",
        "excluded",
        "moira.hermetic_decans",
        ("decan_for_longitude", "decan_at"),
        "source-locked 10-degree segmentation and internal rising-composition tests",
        "Gundel 1936 supports Aries-starting 10-degree decans; tropical-frame and rising projection remain policy-qualified",
        "The unsupported night-hour experiment and all dormant Hermetic transport were removed; no curated import or REST route is allowed.",
        require_absent_from_curated=True,
    ),
    Capability(
        "decennials_l3_l4",
        "Decennials L3/L4",
        "quarantined",
        "excluded",
        "moira.timelords",
        (),
        "rejection tests",
        "conflicted Valens/Hephaistio deep-subdivision candidates",
        "The admitted engine rejects levels above 2 and exposes no selectable deep method.",
    ),
    Capability(
        "firdaria",
        "Firdaria",
        "admitted_non_hellenistic",
        "excluded",
        "moira.timelords",
        ("firdaria",),
        "separate timelord tests and REST contract",
        "medieval Persian/Arabic tradition",
        "The engine and REST expose Firdaria separately; HellenisticChartProfile excludes it by type.",
        ("Firdaria (outside profile)",),
    ),
    Capability(
        "medieval_almutens",
        "Medieval almutens",
        "admitted_non_hellenistic",
        "excluded",
        "moira.dignities",
        ("almuten_figuris",),
        "separate medieval dignity tests",
        "medieval doctrine",
        "Live elsewhere in the classical engine and structurally excluded from the Hellenistic profile.",
    ),
    Capability(
        "later_electional",
        "Later electional rules",
        "admitted_non_hellenistic",
        "excluded",
        "moira.western_electional",
        ("scan_western_electional_judgement_windows",),
        "separate source-scoped electional validation",
        "Dorothean, Sahl, Lilly, and later bounded profiles",
        "No electional ranking or recommendation is composed into the Hellenistic profile.",
    ),
    Capability(
        "primary_directions",
        "Unscoped primary-direction branches",
        "admitted_non_hellenistic",
        "excluded",
        "moira.primary_directions",
        ("find_primary_arcs",),
        "separate method and external-authority validation",
        "method-specific historical authorities",
        "No primary-direction branch is silently selected by the Hellenistic profile.",
    ),
    Capability(
        "valens_distribution_interpretation",
        "Valens distribution interpretation",
        "excluded_unadmitted",
        "excluded",
        "none",
        (),
        "absence from profile and curated contract",
        "source research remains incomplete/conflicted",
        "No interpretive effect vessel is admitted by the unified profile.",
    ),
    Capability(
        "triacontaeteris",
        "Triacontaeteris",
        "deferred",
        "absent",
        "none",
        (),
        "research deferral record",
        "no sufficient first-principles algorithm recovered",
        "No implementation or public capability claim is made.",
    ),
)


@dataclass(frozen=True, slots=True)
class RouteFamily:
    """One runtime route group and its admission relationship."""

    name: str
    mode: str
    prefixes: tuple[str, ...] = ()
    exact_paths: tuple[str, ...] = ()

    def matches(self, path: str) -> bool:
        return path in self.exact_paths or any(
            path.startswith(prefix) for prefix in self.prefixes
        )


ROUTE_FAMILIES: tuple[RouteFamily, ...] = (
    RouteFamily(
        "Unified profile",
        "dedicated profile",
        exact_paths=("/v1/hellenistic/chart-profile",),
    ),
    RouteFamily(
        "Hellenistic aspects",
        "dedicated atomic",
        prefixes=("/v1/aspects/hellenistic/",),
    ),
    RouteFamily(
        "Dignities (mixed supporting surface)",
        "mixed supporting",
        prefixes=("/v1/dignities/",),
    ),
    RouteFamily(
        "Lots (mixed supporting surface)",
        "mixed supporting",
        prefixes=("/v1/lots/",),
    ),
    RouteFamily(
        "Triplicity",
        "dedicated supporting",
        prefixes=("/v1/triplicity/",),
    ),
    RouteFamily(
        "Egyptian bounds",
        "dedicated supporting",
        prefixes=("/v1/egyptian-bounds/",),
    ),
    RouteFamily(
        "Decanates (mixed supporting surface)",
        "mixed supporting",
        exact_paths=(
            "/v1/decanates/chaldean-face",
            "/v1/decanates/triplicity",
            "/v1/decanates/set",
            "/v1/decanates/chart/set",
        ),
    ),
    RouteFamily(
        "Profections",
        "dedicated supporting",
        prefixes=("/v1/profections/",),
    ),
    RouteFamily(
        "Decennials",
        "dedicated supporting",
        prefixes=("/v1/timelords/decennials/",),
    ),
    RouteFamily(
        "Zodiacal Releasing",
        "dedicated supporting",
        prefixes=("/v1/timelords/zodiacal-releasing/",),
    ),
    RouteFamily(
        "Firdaria (outside profile)",
        "live but excluded",
        prefixes=("/v1/timelords/firdaria/",),
    ),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that committed generated inventories match runtime truth.",
    )
    return parser.parse_args()


def _escape(value: Any) -> str:
    return str(value or "-").replace("|", r"\|").replace("\n", " ").strip()


def _schema_label(schema: Any) -> str:
    if not isinstance(schema, dict):
        return "-"
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return reference.rsplit("/", 1)[-1]
    if isinstance(schema.get("items"), dict):
        return f"array[{_schema_label(schema['items'])}]"
    choices = schema.get("anyOf") or schema.get("oneOf")
    if isinstance(choices, list):
        labels = [_schema_label(choice) for choice in choices]
        return " | ".join(label for label in labels if label != "-") or "inline"
    return schema.get("title") or schema.get("type") or "inline"


def _operations(app: Any) -> list[dict[str, str]]:
    openapi = app.openapi()
    operations: list[dict[str, str]] = []
    family_counts = {family.name: 0 for family in ROUTE_FAMILIES}
    for path, path_item in openapi.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        family = next(
            (candidate for candidate in ROUTE_FAMILIES if candidate.matches(path)),
            None,
        )
        if family is None:
            continue
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            request_schema = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema")
            )
            response_schema = (
                operation.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema")
            )
            operations.append(
                {
                    "family": family.name,
                    "mode": family.mode,
                    "method": method.upper(),
                    "path": path,
                    "tags": ", ".join(operation.get("tags", [])),
                    "operation_id": operation.get("operationId", "-"),
                    "request": _schema_label(request_schema),
                    "response": _schema_label(response_schema),
                }
            )
            family_counts[family.name] += 1

    missing = [name for name, count in family_counts.items() if count == 0]
    if missing:
        raise ValueError(
            "Hellenistic API inventory expected live route families with no "
            f"operations: {missing}"
        )
    paths = openapi.get("paths", {})
    prohibited = [
        path
        for path in paths
        if "hermetic" in path.lower()
        or "triacontaeteris" in path.lower()
        or "/decennials/l3" in path.lower()
        or "/decennials/l4" in path.lower()
    ]
    if prohibited:
        raise ValueError(
            "Quarantined Hellenistic paths appeared in OpenAPI: "
            f"{sorted(prohibited)}"
        )
    return sorted(operations, key=lambda item: (item["family"], item["path"]))


def _anchor_receipt(capability: Capability) -> str:
    if not capability.anchors:
        return "No admitted runtime anchor by design"
    module = importlib.import_module(capability.owner)
    surfaces = {
        "root": importlib.import_module("moira"),
        "classical": importlib.import_module("moira.classical"),
        "facade": importlib.import_module("moira.facade"),
    }
    owned: list[tuple[str, Any]] = []
    for name in capability.anchors:
        if not hasattr(module, name):
            raise ValueError(
                f"{capability.capability_id}: missing {capability.owner}.{name}"
            )
        owned.append((name, getattr(module, name)))

    counts = {
        surface_name: sum(
            getattr(surface, name, None) is value for name, value in owned
        )
        for surface_name, surface in surfaces.items()
    }
    if capability.require_absent_from_curated and any(counts.values()):
        raise ValueError(
            f"{capability.capability_id}: quarantined anchors leaked into "
            f"curated surfaces: {counts}"
        )
    return (
        f"{len(owned)}/{len(owned)} owner anchors; "
        + "; ".join(
            f"{surface_name} {count}/{len(owned)}"
            for surface_name, count in counts.items()
        )
    )


def _verify_profile_exports() -> None:
    module = importlib.import_module("moira.hellenistic")
    surfaces = (
        importlib.import_module("moira"),
        importlib.import_module("moira.classical"),
        importlib.import_module("moira.facade"),
    )
    for name in module.__all__:
        value = getattr(module, name)
        if any(
            name not in surface.__all__ or getattr(surface, name, None) is not value
            for surface in surfaces
        ):
            raise ValueError(
                f"Unified Hellenistic export parity failed for {name}"
            )


def render_capability_matrix(app: Any | None = None) -> str:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    if app is None:
        from moira_server.app import create_app

        app = create_app()

    _verify_profile_exports()
    operations = _operations(app)
    route_counts: dict[str, int] = {}
    for operation in operations:
        route_counts[operation["family"]] = (
            route_counts.get(operation["family"], 0) + 1
        )

    from moira.hellenistic import (
        HELLENISTIC_CLASSICAL_PLANETS,
        HELLENISTIC_PROFILE_LOTS,
        HellenisticProfileComponent,
        HellenisticProfileExclusion,
        HellenisticProfilePolicy,
    )

    policy = HellenisticProfilePolicy()
    rows = [
        "# Generated Hellenistic Capability Matrix",
        "",
        "> Generated from current Python modules, curated import surfaces, and "
        "`moira_server.app.create_app().openapi()` by "
        "`scripts/generate_hellenistic_inventory.py`. Do not edit this file by hand.",
        "",
        "Status is a product/admission label, not a claim that astrology has been "
        "empirically demonstrated. Evidence labels distinguish independent "
        "source data from internal invariants and explicit policy tests.",
        "",
        "| Capability | Status | Profile | Runtime/export receipt | REST operations | Evidence | Source basis | Boundary |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for capability in CAPABILITIES:
        route_count = sum(
            route_counts.get(family, 0) for family in capability.route_families
        )
        rows.append(
            "| "
            f"{_escape(capability.capability)} | "
            f"`{_escape(capability.status)}` | "
            f"{_escape(capability.profile)} | "
            f"{_escape(_anchor_receipt(capability))} | "
            f"{route_count} | "
            f"{_escape(capability.evidence)} | "
            f"{_escape(capability.source)} | "
            f"{_escape(capability.caveat)} |"
        )

    rows.extend(
        [
            "",
            "## Unified profile runtime receipt",
            "",
            f"- Classical planets: {', '.join(HELLENISTIC_CLASSICAL_PLANETS)}",
            f"- Profile lots: {', '.join(HELLENISTIC_PROFILE_LOTS)}",
            "- Included component enum: "
            + ", ".join(item.value for item in HellenisticProfileComponent),
            "- Typed exclusions: "
            + ", ".join(item.value for item in HellenisticProfileExclusion),
            f"- Default triplicity doctrine: `{policy.triplicity_doctrine.value}`",
            f"- Default bounds doctrine: `{policy.bounds.doctrine.value}`",
            f"- Default Zodiacal Releasing depth: `{policy.zr_levels}`",
            "- Decennial deep-subdivision selector: "
            f"`{policy.decennials.deep_subdivision_method}`",
            "",
            "## Evidence boundaries",
            "",
            "- `tests/golden/hellenistic_source_tables.json` owns independent "
            "triplicity, joys, bounds, ordinary-face, profile-lot, and Decennial data.",
            "- `tests/golden/hellenistic_zr_valens_iv4.json` owns the Valens "
            "same-sign start-shift and 211-month circuit cases.",
            "- Hermetic catalog identity remains source-locked in "
            "`tests/unit/test_hermetic_decans.py`; its geometry is still quarantined "
            "and every Hermetic transport layer is absent.",
            "- Mixed supporting routes expose broader classical catalogs or policies. "
            "Only `/v1/hellenistic/chart-profile` freezes the unified profile contract.",
            "- The heterogeneous lots catalog is not promoted to a single Hellenistic "
            "source claim by the four source-goldened profile lots.",
            "",
            "## Regeneration",
            "",
            "```powershell",
            "$env:MOIRA_TEST_MODE = \"1\"",
            "$env:MOIRA_STRICT_KNOWN_ISSUES = \"1\"",
            r".\.venv\Scripts\python.exe scripts\generate_hellenistic_inventory.py",
            r".\.venv\Scripts\python.exe scripts\generate_hellenistic_inventory.py --check",
            "```",
            "",
        ]
    )
    return "\n".join(rows)


def render_api_inventory(app: Any | None = None) -> str:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    if app is None:
        from moira_server.app import create_app

        app = create_app()
    operations = _operations(app)
    openapi = app.openapi()
    all_operation_count = sum(
        1
        for item in openapi.get("paths", {}).values()
        if isinstance(item, dict)
        for method in HTTP_METHODS
        if isinstance(item.get(method), dict)
    )

    family_counts: dict[str, int] = {}
    for operation in operations:
        family_counts[operation["family"]] = (
            family_counts.get(operation["family"], 0) + 1
        )

    rows = [
        "# Generated Hellenistic API Inventory",
        "",
        "> Generated from `moira_server.app.create_app().openapi()` by "
        "`scripts/generate_hellenistic_inventory.py`. Do not edit this file by hand.",
        "",
        f"- Application: `{app.title}` `{app.version}`",
        f"- Complete registered OpenAPI operations: {all_operation_count}",
        f"- Hellenistic, supporting, and explicitly adjacent operations inventoried here: {len(operations)}",
        "- Quarantined Hermetic geometry, Triacontaeteris, and Decennial L3/L4 paths: 0",
        "",
        "## Family counts",
        "",
        "| Family | Relationship | Operations |",
        "|---|---|---:|",
    ]
    for family in ROUTE_FAMILIES:
        rows.append(
            f"| {_escape(family.name)} | {_escape(family.mode)} | "
            f"{family_counts.get(family.name, 0)} |"
        )

    rows.extend(
        [
            "",
            "## Runtime route and schema inventory",
            "",
            "| Family | Mode | Method | Path | Request schema | 200 response schema | Tags | Operation ID |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for operation in operations:
        rows.append(
            "| "
            f"{_escape(operation['family'])} | "
            f"{_escape(operation['mode'])} | "
            f"`{_escape(operation['method'])}` | "
            f"`{_escape(operation['path'])}` | "
            f"`{_escape(operation['request'])}` | "
            f"`{_escape(operation['response'])}` | "
            f"{_escape(operation['tags'])} | "
            f"`{_escape(operation['operation_id'])}` |"
        )

    rows.extend(
        [
            "",
            "## Contract reading rules",
            "",
            "- Dedicated Hellenistic routes are the unified profile and the two "
            "whole-sign aspect routes.",
            "- Triplicity, bounds, profections, Decennials, and Zodiacal Releasing "
            "are dedicated supporting families used by the profile.",
            "- Dignities, lots, and decanate routes are broader mixed classical "
            "surfaces. Their presence does not mean every selectable doctrine or "
            "catalog entry belongs to the Hellenistic profile.",
            "- Firdaria is listed because it is a live adjacent timelord surface "
            "that the profile explicitly excludes.",
            "- Route registration proves transport availability only. Source "
            "admission and validation status are governed by the capability matrix.",
            "",
        ]
    )
    return "\n".join(rows)


def main() -> int:
    args = _parse_args()
    try:
        from moira_server.app import create_app

        app = create_app()
        rendered = {
            CAPABILITY_PATH: render_capability_matrix(app),
            API_PATH: render_api_inventory(app),
        }
    except (ImportError, OSError, ValueError) as exc:
        print(f"Hellenistic inventory generation failed: {exc}", file=sys.stderr)
        return 1

    if args.check:
        stale = [
            path
            for path, content in rendered.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            print(
                "Hellenistic generated inventories are stale: "
                + ", ".join(str(path.relative_to(REPO_ROOT)) for path in stale),
                file=sys.stderr,
            )
            return 1
        print("Hellenistic generated inventories are current.")
        return 0

    for path, content in rendered.items():
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Generated {path.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

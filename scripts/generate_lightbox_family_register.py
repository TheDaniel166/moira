"""Generate the governed Light Box calculation-family register.

LB-WP2 groups every in-scope surface from the authoritative inventory into one
primary review family.  The register is a planning and coverage boundary only:
family membership, priority, and exposure do not confer conformance.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "LIGHT_BOX_CALCULATION_INVENTORY.generated.json"
)
INVENTORY_GENERATOR_PATH = (
    REPO_ROOT / "scripts" / "generate_lightbox_calculation_inventory.py"
)
PRODUCT_USAGE_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_PRODUCT_USAGE_SNAPSHOT.json"
)
REVIEW_POLICY_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_FAMILY_REVIEW_POLICY.json"
)
JSON_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_FAMILY_REGISTER.generated.json"
)
MARKDOWN_PATH = (
    REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_FAMILY_REGISTER.generated.md"
)
GENERATOR_PATH = "scripts/generate_lightbox_family_register.py"
SCHEMA_VERSION = "moira.lightbox-family-register/v2"


class LightBoxFamilyError(RuntimeError):
    """Raised when the inventory cannot form a complete family register."""


FAMILY_ALIASES: Mapping[str, str] = {
    "asteroid-families": "asteroids",
    "asteroids-fast-small-body": "asteroids",
    "comets-fast-small-body": "comets",
    "compat-nasa-eclipse": "eclipses",
    "dasha-systems": "dasha",
    "generic-phenomena": "phenomena",
    "jaimini-extended": "jaimini",
    "locational-forecasting": "astrocartography",
    "muhurta-business": "muhurta",
    "muhurta-travel": "muhurta",
    "muhurta-vastu": "muhurta",
    "multiple-stars": "stars",
    "progressed-astrodynes": "astrodynes",
    "relationship-forecasting": "relationship",
    "special-muhurta": "muhurta",
    "stars-fixed-stars": "stars",
    "synastry": "relationship",
    "transits-aspects": "transits",
    "variable-stars": "stars",
    "vedic-dignities": "vedic-dignities",
    "western-electional": "electional",
    "western-electional-dorotheus": "electional",
    "western-electional-judgement": "electional",
}

PHENOMENA_FAMILIES = {
    "eclipses",
    "heliacal",
    "occultations",
    "phenomena",
    "phase",
    "rise-set",
    "solar-condition",
    "stations",
    "visibility",
    "void-of-course",
}
RELATIONSHIP_FAMILIES = {
    "composite",
    "davison",
    "relationship",
}
PREDICTIVE_FAMILIES = {
    "batch",
    "cycles",
    "harmograms-compute",
    "primary-directions",
    "profections",
    "progressions",
    "returns",
    "timelords",
    "transits",
}
VEDIC_FAMILIES = {
    "alternate-dashas",
    "ashtakavarga",
    "avasthas",
    "dasha",
    "gochara",
    "gochara-windows",
    "jaimini",
    "muhurta",
    "nakshatra",
    "nine-parts",
    "pancha-pakshi",
    "panchanga",
    "panchanga-shuddhi",
    "sade-sati",
    "shadbala",
    "upagrahas",
    "varga",
    "vedic-dignities",
    "vedic-profile",
    "varshaphal",
    "yogas",
}
TRADITIONAL_WESTERN_FAMILIES = {
    "almuten",
    "antiscia",
    "decanates",
    "dignities",
    "egyptian-bounds",
    "electional",
    "hellenistic-aspects",
    "hellenistic-atoms",
    "hellenistic-profile",
    "hellenistic-systems",
    "horary",
    "hyleg",
    "lord-of-the-orb",
    "lord-of-the-turn",
    "lots",
    "manazil",
    "planetary-hours",
    "triplicity",
    "western-profile",
}
LOCATIONAL_FAMILIES = {
    "astrocartography",
    "galactic-houses",
    "gauquelin",
    "geodetic",
    "local-space",
    "parans",
}
REST_PATH_FAMILY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("/v1/positions/frame/", "positions-frame"),
    ("/v1/pipeline/positions/", "positions"),
    ("/v1/positions/", "positions"),
    ("/v1/houses", "houses"),
    ("/v1/pipeline/chart", "chart"),
    ("/v1/chart", "chart"),
)
CORE_FAMILIES = {
    "aspects",
    "chart",
    "coordinates",
    "houses",
    "julian",
    "nodes",
    "obliquity",
    "orbits",
    "pipeline",
    "planets",
    "planetary-nodes",
    "positions",
    "positions-frame",
    "sidereal",
    "website-chart-wheel",
    "website-pipeline",
}


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LightBoxFamilyError(f"cannot load JSON: {_relative(path)}") from exc
    if not isinstance(value, dict):
        raise LightBoxFamilyError(f"JSON root must be an object: {_relative(path)}")
    return value


def _load_inventory_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_lightbox_calculation_inventory_for_families",
        INVENTORY_GENERATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise LightBoxFamilyError("cannot load LB-WP0 inventory generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_current_inventory() -> dict[str, Any]:
    committed = _load_json(INVENTORY_PATH)
    current = _load_inventory_generator().build_inventory()
    if committed != current:
        raise LightBoxFamilyError(
            "calculation inventory is stale; regenerate LB-WP0 first"
        )
    return committed


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    while normalized.startswith("-"):
        normalized = normalized[1:]
    return FAMILY_ALIASES.get(normalized, normalized)


def _python_family(row: Mapping[str, Any]) -> tuple[str, str]:
    module = str(row["owner_module"])
    stem = module.removeprefix("moira.").replace("._", ".")
    family_id = _slug(stem.replace(".", "-"))
    return family_id, f"python owner module {module}"


def _rest_family(row: Mapping[str, Any]) -> tuple[str, str]:
    path = str(row["path"])
    for prefix, family_id in REST_PATH_FAMILY_PREFIXES:
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return family_id, f"governed REST path prefix {prefix!r}"
    tags = [str(tag) for tag in row.get("tags", []) if str(tag).strip()]
    if tags:
        family_id = _slug(tags[0])
        return family_id, f"primary OpenAPI tag {tags[0]!r}"
    first_segment = next(
        (part for part in path.split("/") if part and part != "v1"), "rest"
    )
    return _slug(first_segment), "first stable REST path segment (no OpenAPI tag)"


def _domain_group(family_id: str) -> str:
    if family_id in CORE_FAMILIES:
        return "astronomy-and-chart-core"
    if family_id in PHENOMENA_FAMILIES:
        return "phenomena-and-visibility"
    if family_id in RELATIONSHIP_FAMILIES:
        return "relationship"
    if family_id in PREDICTIVE_FAMILIES:
        return "predictive-and-time"
    if family_id in VEDIC_FAMILIES:
        return "vedic-and-electional"
    if family_id in TRADITIONAL_WESTERN_FAMILIES:
        return "traditional-western"
    if family_id in LOCATIONAL_FAMILIES:
        return "locational"
    return "specialist-and-compositional"


def _label(family_id: str) -> str:
    return " ".join(
        part.upper() if part in {"ssb"} else part.title()
        for part in family_id.split("-")
    )


def _entry(
    row: Mapping[str, Any],
    *,
    transport: str,
    production_canonical_ids: set[str],
    usage_by_canonical_id: Mapping[str, list[Mapping[str, Any]]],
    review_policy: Mapping[str, Any],
) -> dict[str, Any]:
    family_id, rule = (
        _python_family(row) if transport == "python" else _rest_family(row)
    )
    alias = row["alias_of"] is not None
    canonical_id = str(row["canonical_id"])
    product_used = canonical_id in production_canonical_ids
    strong = set(review_policy["strong_exemplar_families"])
    mixed = set(review_policy["mixed_families"])
    major = set(review_policy["major_gap_families"])
    stage_two = set(review_policy["stage_2_families"])
    if family_id in strong:
        assessment_status = "strong_exemplar"
    elif family_id in mixed:
        assessment_status = "mixed"
    elif family_id in major:
        assessment_status = "major_gap"
    else:
        assessment_status = str(review_policy["default_status"])
    if family_id in stage_two:
        review_stage = "stage_2_exemplars"
    elif product_used:
        review_stage = "stage_3_product_use"
    elif _domain_group(family_id) in {"phenomena-and-visibility", "relationship"}:
        review_stage = "stage_4_phenomena_relationships"
    else:
        review_stage = "stage_5_remaining_tail"
    return {
        "surface_id": row["surface_id"],
        "canonical_surface_id": row["canonical_id"],
        "entry_role": "alias" if alias else "canonical",
        "surface_kind": row["surface_kind"],
        "transport": transport,
        "family_id": family_id,
        "family_label": _label(family_id),
        "domain_group": _domain_group(family_id),
        "priority": "P0" if product_used else ("P1" if transport == "rest" else "P2"),
        "exposure": "production_user"
        if product_used
        else ("public_api" if transport == "rest" else "source_only"),
        "review_state": "reviewed",
        "review_stage": review_stage,
        "assessment_status": assessment_status,
        "assignment_basis": rule,
        "product_usage": {
            "snapshot_path": _relative(PRODUCT_USAGE_PATH) if product_used else None,
            "matched_surface_count": len(usage_by_canonical_id.get(canonical_id, [])),
            "products": sorted(
                {
                    callsite["product"]
                    for usage in usage_by_canonical_id.get(canonical_id, [])
                    for callsite in usage.get("callsites", [])
                }
            ),
        },
        "ownership": {
            "source_path": row["source_path"],
            "source_line": row["source_line"],
        },
    }


def _summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    canonical = [row for row in entries if row["entry_role"] == "canonical"]
    families: dict[str, set[str]] = defaultdict(set)
    for row in canonical:
        families[row["family_id"]].add(row["transport"])
    return {
        "entries_total": len(entries),
        "canonical_entries": len(canonical),
        "alias_entries": len(entries) - len(canonical),
        "family_count": len(families),
        "cross_transport_families": sum(
            len(transports) > 1 for transports in families.values()
        ),
        "canonical_by_domain_group": dict(
            sorted(Counter(row["domain_group"] for row in canonical).items())
        ),
        "canonical_by_priority": {
            priority: sum(row["priority"] == priority for row in canonical)
            for priority in ("P0", "P1", "P2")
        },
        "canonical_by_exposure": dict(
            sorted(Counter(row["exposure"] for row in canonical).items())
        ),
        "canonical_by_review_state": {
            state: sum(row["review_state"] == state for row in canonical)
            for state in ("seeded", "reviewed", "blocked")
        },
    }


def load_product_usage(inventory: Mapping[str, Any]) -> dict[str, Any]:
    if not PRODUCT_USAGE_PATH.is_file():
        return {
            "schema_version": "moira.lightbox-product-usage/v2",
            "inventory_fingerprint_sha256": inventory["structural_fingerprint_sha256"],
            "summary": {"production_user_surfaces": 0},
            "entries": [],
        }
    usage = _load_json(PRODUCT_USAGE_PATH)
    if usage.get("schema_version") != "moira.lightbox-product-usage/v2":
        raise LightBoxFamilyError("unsupported product-usage snapshot schema")
    if usage.get("inventory_fingerprint_sha256") != inventory.get(
        "structural_fingerprint_sha256"
    ):
        raise LightBoxFamilyError(
            "product-usage snapshot is stale for the current inventory"
        )
    entries = usage.get("entries")
    if not isinstance(entries, list):
        raise LightBoxFamilyError("product-usage snapshot entries must be an array")
    return usage


def load_review_policy() -> dict[str, Any]:
    policy = _load_json(REVIEW_POLICY_PATH)
    if policy.get("schema_version") != "moira.lightbox-family-review-policy/v1":
        raise LightBoxFamilyError("unsupported family review policy schema")
    statuses = {"strong_exemplar", "partial", "mixed", "major_gap", "unresolved"}
    if policy.get("default_status") not in statuses:
        raise LightBoxFamilyError("invalid default family assessment status")
    named: set[str] = set()
    for key in (
        "stage_2_families",
        "strong_exemplar_families",
        "mixed_families",
        "major_gap_families",
    ):
        values = policy.get(key)
        if not isinstance(values, list) or len(values) != len(set(values)):
            raise LightBoxFamilyError(f"review policy {key} must be a unique array")
        if key != "stage_2_families":
            overlap = named & set(values)
            if overlap:
                raise LightBoxFamilyError(
                    f"family has conflicting assessment statuses: {sorted(overlap)}"
                )
            named.update(values)
    return policy


def build_register(inventory: Mapping[str, Any]) -> dict[str, Any]:
    if inventory.get("schema_version") != "moira.lightbox-calculation-inventory/v2":
        raise LightBoxFamilyError("unsupported inventory schema; regenerate v2 structural bindings")
    usage = load_product_usage(inventory)
    review_policy = load_review_policy()
    usage_by_canonical_id: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in usage["entries"]:
        usage_by_canonical_id[str(row["canonical_surface_id"])].append(row)
    production_canonical_ids = set(usage_by_canonical_id)
    entries = sorted(
        [
            _entry(
                row,
                transport=transport,
                production_canonical_ids=production_canonical_ids,
                usage_by_canonical_id=usage_by_canonical_id,
                review_policy=review_policy,
            )
            for collection, transport in (
                ("python_exports", "python"),
                ("rest_operations", "rest"),
            )
            for row in inventory[collection]
            if row["in_lightbox_calculation_scope"]
        ],
        key=lambda row: row["surface_id"],
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "inventory_schema_version": inventory["schema_version"],
        "engine_version": inventory["engine_version"],
        "inventory_fingerprint_sha256": inventory["structural_fingerprint_sha256"],
        "generated_by": GENERATOR_PATH,
        "product_usage_snapshot": {
            "path": _relative(PRODUCT_USAGE_PATH)
            if PRODUCT_USAGE_PATH.is_file()
            else None,
            "audit_date": usage.get("audit_date"),
            "roots": usage.get("roots", []),
        },
        "review_policy": {
            "path": _relative(REVIEW_POLICY_PATH),
            "review_date": review_policy["review_date"],
            "boundary": review_policy["review_boundary"],
        },
        "scope_rule": "Every in-scope canonical surface is assigned to exactly one primary family. Aliases remain visible and inherit no independent conformance claim.",
        "priority_policy": {
            "P0": "Reserved for confirmed production-user call paths in the Stage 3 usage snapshot.",
            "P1": "Public REST calculation not yet confirmed as a production-user call path.",
            "P2": "Python-facade calculation without an independently confirmed production-user call path.",
        },
        "limitations": [
            "Family membership and reviewed structural disposition are not correctness or conformance evidence.",
            "P0 records exact static callsites in the revision-bound product-usage snapshot; it does not prove runtime reachability or frequency.",
            "A Python and REST surface sharing a family name are related review subjects, not automatically transport-equivalent.",
            "Source-only exposure means the public Python facade; it does not mean a product user can inspect the derivation.",
        ],
        "summary": _summary(entries),
        "entries": entries,
    }


def validate_register(
    register: Mapping[str, Any], inventory: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    expected = {
        row["surface_id"]: row
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    entries = register.get("entries")
    if not isinstance(entries, list):
        return ["$.entries: must be a list"]
    ids = [row.get("surface_id") for row in entries if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        errors.append("$.entries: duplicate surface_id")
    if set(ids) != set(expected):
        errors.append("$.entries: does not exactly cover the LB-WP0 in-scope set")
    for index, entry in enumerate(entries):
        path = f"$.entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{path}: must be an object")
            continue
        surface_id = entry.get("surface_id")
        source = expected.get(surface_id)
        if source is None:
            continue
        expected_role = "alias" if source["alias_of"] is not None else "canonical"
        if entry.get("canonical_surface_id") != source["canonical_id"]:
            errors.append(f"{path}.canonical_surface_id: inventory drift")
        if entry.get("entry_role") != expected_role:
            errors.append(f"{path}.entry_role: inventory drift")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(entry.get("family_id", ""))):
            errors.append(f"{path}.family_id: invalid or empty")
        if entry.get("priority") not in {"P0", "P1", "P2"}:
            errors.append(f"{path}.priority: invalid")
        if entry.get("exposure") not in {
            "production_user",
            "public_api",
            "source_only",
            "unresolved",
        }:
            errors.append(f"{path}.exposure: invalid")
        if entry.get("review_state") not in {"seeded", "reviewed", "blocked"}:
            errors.append(f"{path}.review_state: invalid")
        owner = entry.get("ownership", {})
        if (
            owner.get("source_path") != source["source_path"]
            or owner.get("source_line") != source["source_line"]
        ):
            errors.append(f"{path}.ownership: inventory drift")
    if register.get("summary") != _summary(entries):
        errors.append("$.summary: does not match entry-derived counts")
    return errors


def render_json(register: Mapping[str, Any]) -> str:
    return json.dumps(register, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def render_markdown(register: Mapping[str, Any]) -> str:
    summary = register["summary"]
    family_rows: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in register["entries"]:
        if row["entry_role"] == "canonical":
            family_rows[row["family_id"]].append(row)
    lines = [
        "# Light Box Family Register",
        "",
        f"> Generated by `{GENERATOR_PATH}`. Do not edit by hand.",
        "",
        f"- Engine version: `{register['engine_version']}`",
        f"- Inventory structural fingerprint: `{register['inventory_fingerprint_sha256']}`",
        f"- Canonical surfaces: {summary['canonical_entries']}",
        f"- Explicit aliases: {summary['alias_entries']}",
        f"- Primary families: {summary['family_count']}",
        f"- Cross-transport families: {summary['cross_transport_families']}",
        "",
        "## Boundary",
        "",
        "This register makes the review denominator and sequencing explicit. It does **not** certify any calculation. Stage 1 leaves every family `seeded`; later stages must attach reviewed semantics, evidence, residual, release, and exposure receipts through the conformance contract.",
        "",
        "P0 contains only canonical calculations matched by the revision-bound product-usage snapshot. P1 covers the remaining public REST calculation surface, and P2 covers Python-facade surfaces not independently confirmed as product call paths.",
        "",
        "## Coverage",
        "",
        "| Domain group | Canonical surfaces |",
        "|---|---:|",
    ]
    for domain, count in summary["canonical_by_domain_group"].items():
        lines.append(f"| `{domain}` | {count} |")
    lines.extend(
        [
            "",
            "| Priority | Canonical surfaces |",
            "|---|---:|",
        ]
    )
    for priority, count in summary["canonical_by_priority"].items():
        lines.append(f"| `{priority}` | {count} |")
    lines.extend(
        [
            "",
            "## Family queue",
            "",
            "| Family | Domain | Canonical | Python | REST | Highest priority | Review state |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )
    for family_id in sorted(family_rows):
        rows = family_rows[family_id]
        priorities = {"P0": 0, "P1": 1, "P2": 2}
        highest = min((row["priority"] for row in rows), key=priorities.get)
        states = sorted({row["review_state"] for row in rows})
        lines.append(
            f"| `{family_id}` | `{rows[0]['domain_group']}` | {len(rows)} | "
            f"{sum(row['transport'] == 'python' for row in rows)} | "
            f"{sum(row['transport'] == 'rest' for row in rows)} | `{highest}` | "
            f"`{','.join(states)}` |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "Every canonical inventory ID appears exactly once, every alias resolves to an inventoried canonical ID, and no family assignment changes a conformance disposition. The next stage may admit only evidence that satisfies the canonical schema and names its exact covered surfaces.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_atomic(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail when generated artifacts are stale"
    )
    args = parser.parse_args()
    try:
        inventory = load_current_inventory()
        register = build_register(inventory)
        errors = validate_register(register, inventory)
        if errors:
            raise LightBoxFamilyError(
                "family register validation failed:\n- " + "\n- ".join(errors[:25])
            )
        outputs = (
            (JSON_PATH, render_json(register)),
            (MARKDOWN_PATH, render_markdown(register)),
        )
        if args.check:
            stale = [
                _relative(path)
                for path, expected in outputs
                if not path.is_file() or path.read_text(encoding="utf-8") != expected
            ]
            if stale:
                raise LightBoxFamilyError(
                    "Light Box family register is stale: " + ", ".join(stale)
                )
            print("Light Box family register is current.")
            return 0
        for path, text in outputs:
            _write_atomic(path, text)
            print(f"Generated {_relative(path)}.")
        return 0
    except LightBoxFamilyError as exc:
        print(f"Light Box family generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

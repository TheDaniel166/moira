"""Generate Phase 7 physical-visibility capability and API inventories."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
EVIDENCE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "physical_visibility_phase7_evidence_registry.json"
)
CAPABILITY_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "PHYSICAL_HELIACAL_VISIBILITY_CAPABILITY_MATRIX.generated.md"
)
API_PATH = (
    REPO_ROOT
    / "wiki"
    / "03_validation"
    / "PHYSICAL_HELIACAL_VISIBILITY_API_INVENTORY.generated.md"
)

PUBLIC_NAMES = (
    "PhysicalVisibilityStatus",
    "PhysicalVisibilityEvidenceState",
    "PhysicalVisibilityPhase",
    "PhysicalVisibilityCrossingDirection",
    "PhysicalVisibilityBoundarySource",
    "PhysicalEventTimeSemantics",
    "PhysicalBackgroundScope",
    "PhysicalBackgroundComponentKind",
    "PhysicalAtmosphereInput",
    "PhysicalDirectionalBackground",
    "PhysicalModeledBackgroundComponent",
    "PhysicalSqmBackground",
    "PhysicalBortleBackground",
    "PhysicalHorizonSample",
    "PhysicalHorizonProfile",
    "PhysicalVisibilityPolicy",
    "VisibilityComponentReceipt",
    "PhysicalAtmosphereReceipt",
    "PhysicalValidityDomainReceipt",
    "PhysicalObserverProtocolReceipt",
    "PhysicalBackgroundReceipt",
    "PhysicalTargetReceipt",
    "PhysicalThresholdReceipt",
    "PhysicalVisibilityErrorBudgetReceipt",
    "PhysicalVisibilityAssessment",
    "PhysicalVisibilitySearchPolicy",
    "PhysicalObservationWindowReceipt",
    "PhysicalEventSolverReceipt",
    "PhysicalEventSensitivityReceipt",
    "PhysicalHorizonReceipt",
    "PhysicalEphemerisReceipt",
    "PhysicalVisibilityEventResult",
    "VisibilityDataPackConfig",
    "VisibilityDataPackReceipt",
    "physical_visibility_assessment",
    "physical_visibility_event",
)

PHYSICAL_ROUTES = (
    "/v1/visibility/physical-assessment",
    "/v1/visibility/physical-event",
)
LEGACY_ROUTES = (
    "/v1/visibility/assessment",
    "/v1/visibility/tonight",
    "/v1/heliacal/visibility-event",
)
PRIVATE_NATIVE_KERNELS = (
    "_physical_visibility_resolve_response_weights",
    "_PhysicalVisibilityDirectExtinctionKernel",
)
FORBIDDEN_PUBLIC_TOKENS = (
    "physical_visibility_confidence",
    "mc_spectral_is",
    "libradtran",
    "mystic",
    "universal_rbf",
)


class PhysicalVisibilityInventoryError(RuntimeError):
    """Raised when runtime truth cannot support a generated inventory."""


@dataclass(frozen=True)
class EvidenceClass:
    identifier: str
    role: str
    paths: tuple[str, ...]
    limitation: str
    fingerprint: str


@dataclass(frozen=True)
class RuntimeInventory:
    engine_version: str
    public_surfaces: tuple[tuple[str, bool, bool, bool, bool], ...]
    methods: tuple[str, ...]
    operations: tuple[tuple[str, str, str, str], ...]
    legacy_operations: tuple[tuple[str, str], ...]
    native_kernels: tuple[str, ...]
    evidence: tuple[EvidenceClass, ...]


def _canonical_text_bytes(path: Path) -> bytes:
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PhysicalVisibilityInventoryError(
            f"evidence path is not UTF-8 text: {path}"
        ) from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(_canonical_text_bytes(path)).hexdigest()


def _combined_fingerprint(paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for raw in paths:
        path = REPO_ROOT / raw
        if not path.is_file():
            raise PhysicalVisibilityInventoryError(
                f"evidence path does not exist: {raw}"
            )
        digest.update(raw.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_canonical_text_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _load_evidence() -> tuple[EvidenceClass, ...]:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != (
        "moira.physical-heliacal-visibility-phase7-evidence-registry/v1"
    ):
        raise PhysicalVisibilityInventoryError("evidence registry schema drift")
    rows = payload.get("evidence_classes")
    if not isinstance(rows, list) or not rows:
        raise PhysicalVisibilityInventoryError("evidence registry is empty")

    result: list[EvidenceClass] = []
    identifiers: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise PhysicalVisibilityInventoryError(
                "evidence registry row is not an object"
            )
        identifier = row.get("id")
        role = row.get("role")
        paths = row.get("paths")
        limitation = row.get("limitation")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in identifiers
            or not isinstance(role, str)
            or not role
            or not isinstance(paths, list)
            or not paths
            or not all(isinstance(path, str) and path for path in paths)
            or not isinstance(limitation, str)
            or not limitation
        ):
            raise PhysicalVisibilityInventoryError(
                f"malformed or duplicate evidence class: {identifier!r}"
            )
        identifiers.add(identifier)
        result.append(
            EvidenceClass(
                identifier=identifier,
                role=role,
                paths=tuple(paths),
                limitation=limitation,
                fingerprint=_combined_fingerprint(paths),
            )
        )
    return tuple(result)


def _schema_name(schema: Any) -> str:
    if not isinstance(schema, dict):
        return "none"
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return reference.rsplit("/", 1)[-1]
    one_of = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(one_of, list):
        return " | ".join(_schema_name(item) for item in one_of)
    return str(schema.get("type", "inline"))


def _request_schema(operation: dict[str, Any]) -> str:
    body = operation.get("requestBody", {})
    content = body.get("content", {}) if isinstance(body, dict) else {}
    media = content.get("application/json", {}) if isinstance(content, dict) else {}
    return _schema_name(media.get("schema") if isinstance(media, dict) else None)


def _response_schema(operation: dict[str, Any]) -> str:
    responses = operation.get("responses", {})
    success = responses.get("200", {}) if isinstance(responses, dict) else {}
    content = success.get("content", {}) if isinstance(success, dict) else {}
    media = content.get("application/json", {}) if isinstance(content, dict) else {}
    return _schema_name(media.get("schema") if isinstance(media, dict) else None)


def collect_inventory() -> RuntimeInventory:
    import moira
    import moira.facade as facade
    import moira.heliacal as heliacal
    import moira.sky.visibility as sky_visibility
    from moira import moira_native
    from moira_server.app import create_app
    from moira_server.config import ServerConfig

    surfaces = []
    for name in PUBLIC_NAMES:
        owner = getattr(heliacal, name, None)
        if owner is None:
            raise PhysicalVisibilityInventoryError(
                f"owning heliacal module lacks public symbol: {name}"
            )
        flags = []
        for surface in (moira, facade, sky_visibility):
            flags.append(
                name in getattr(surface, "__all__", ())
                and getattr(surface, name, None) is owner
            )
        surfaces.append((name, True, *flags))
    if not all(all(row[1:]) for row in surfaces):
        raise PhysicalVisibilityInventoryError(
            "physical public symbol identity differs across Python surfaces"
        )

    methods = (
        "Moira.physical_visibility_assessment",
        "Moira.physical_visibility_event",
    )
    for method in ("physical_visibility_assessment", "physical_visibility_event"):
        if not callable(getattr(facade.Moira, method, None)):
            raise PhysicalVisibilityInventoryError(
                f"Moira method is absent: {method}"
            )

    openapi = create_app(ServerConfig(docs_enabled=False)).openapi()
    paths = openapi.get("paths", {})
    operations = []
    for path in PHYSICAL_ROUTES:
        operation = paths.get(path, {}).get("post")
        if not isinstance(operation, dict):
            raise PhysicalVisibilityInventoryError(
                f"physical OpenAPI operation is absent: POST {path}"
            )
        operations.append(
            (
                path,
                str(operation.get("operationId", "missing")),
                _request_schema(operation),
                _response_schema(operation),
            )
        )

    legacy = []
    for path in LEGACY_ROUTES:
        operation = paths.get(path, {}).get("post")
        if not isinstance(operation, dict):
            raise PhysicalVisibilityInventoryError(
                f"legacy OpenAPI operation is absent: POST {path}"
            )
        legacy.append((path, str(operation.get("operationId", "missing"))))

    serialized_openapi = json.dumps(openapi, sort_keys=True).lower()
    serialized_public = "\n".join(PUBLIC_NAMES).lower()
    for token in FORBIDDEN_PUBLIC_TOKENS:
        if token in serialized_openapi or token in serialized_public:
            raise PhysicalVisibilityInventoryError(
                f"closed physical-visibility token became public: {token}"
            )

    native = []
    for name in PRIVATE_NATIVE_KERNELS:
        if not callable(getattr(moira_native, name, None)):
            raise PhysicalVisibilityInventoryError(
                f"admitted private native kernel is absent: {name}"
            )
        native.append(name)

    return RuntimeInventory(
        engine_version=str(moira.__version__),
        public_surfaces=tuple(surfaces),
        methods=methods,
        operations=tuple(operations),
        legacy_operations=tuple(legacy),
        native_kernels=tuple(native),
        evidence=_load_evidence(),
    )


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _evidence_table(inventory: RuntimeInventory) -> list[str]:
    lines = [
        "| Evidence class | Role | Bound files | Fingerprint | Limitation |",
        "|---|---|---:|---|---|",
    ]
    for row in inventory.evidence:
        lines.append(
            f"| `{row.identifier}` | `{row.role}` | {len(row.paths)} | "
            f"`{row.fingerprint[:16]}` | {_escape(row.limitation)} |"
        )
    return lines


def render_capability_matrix(inventory: RuntimeInventory) -> str:
    evidence_ids = {row.identifier for row in inventory.evidence}
    required = {
        "primary_source_equation_validation",
        "independent_libradtran_holdouts",
        "modern_era_observational_comparison",
        "historical_event_corroboration",
        "property_and_invariant_testing",
        "legacy_regression_fixtures",
        "public_contract_and_openapi_parity",
        "external_ephemeris_event_goldens",
        "separated_numerical_tolerances",
        "native_python_differential",
        "release_artifact_and_offline_install",
        "experimental_site_specific_moonlight_quarantine",
    }
    missing = required - evidence_ids
    if missing:
        raise PhysicalVisibilityInventoryError(
            f"capability matrix lacks evidence classes: {sorted(missing)}"
        )

    rows = (
        (
            "Legacy generalized visibility and heliacal search",
            "admitted compatibility contract",
            "default legacy policy",
            "legacy_regression_fixtures, historical_event_corroboration",
            "Not relabelled as the physical model.",
        ),
        (
            "Physical single-epoch point-source assessment",
            "admitted",
            "explicit opt-in plus external pack",
            "primary_source_equation_validation, independent_libradtran_holdouts, modern_era_observational_comparison, property_and_invariant_testing, separated_numerical_tolerances, public_contract_and_openapi_parity",
            "Clear-sky, unresolved steady point sources inside the exact pack domain.",
        ),
        (
            "Physical four-phase first/last event search",
            "admitted",
            "explicit opt-in plus exact pack 1.2.0",
            "external_ephemeris_event_goldens, property_and_invariant_testing, separated_numerical_tolerances, public_contract_and_openapi_parity",
            "Event ownership and geometry are validated; event goldens are not observed visibility dates.",
        ),
        (
            "External physical visibility data pack",
            "admitted immutable resource",
            "caller/server supplied; never downloaded",
            "independent_libradtran_holdouts, release_artifact_and_offline_install",
            "CC BY-SA 4.0 pack remains separate from the MIT Python distribution.",
        ),
        (
            "Two Phase 6 numerical kernels",
            "admitted private optimization",
            "no public API and Python-owned policy",
            "native_python_differential",
            "Differential/performance evidence is not scientific validation.",
        ),
        (
            "Site-specific experimental moonlight extensions",
            "quarantined research",
            "absent from product and release surfaces",
            "experimental_site_specific_moonlight_quarantine",
            "A separately authorized model and evidence program would be required to reopen this work.",
        ),
        (
            "Cloudy sky, live weather, telescopes, extended objects, Sun, Moon crescent, and observer-population confidence",
            "closed exclusion",
            "absent",
            "property_and_invariant_testing",
            "A new model identity and independent evidence are required.",
        ),
    )

    lines = [
        "# Generated Physical Heliacal-Visibility Capability Matrix",
        "",
        "> Generated from current Python exports, the FastAPI OpenAPI registry, "
        "and the Phase 7 evidence registry by "
        "`scripts/generate_physical_visibility_inventory.py`. Do not edit this "
        "file by hand.",
        "",
        f"- Engine package version: `{inventory.engine_version}`",
        "- Composite model: `clear_sky_naked_eye_point_source_v1`",
        "- Admitted external pack: `moira-physical-heliacal-visibility` "
        "`1.2.0`, manifest `cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c`",
        "- Release posture: additive and opt-in; legacy defaults unchanged",
        "",
        "## Capability matrix",
        "",
        "| Capability | Admission | Availability | Named evidence classes | Boundary |",
        "|---|---|---|---|---|",
    ]
    for capability, admission, availability, evidence, boundary in rows:
        lines.append(
            f"| {capability} | `{admission}` | {availability} | "
            f"{', '.join(f'`{value.strip()}`' for value in evidence.split(','))} | "
            f"{boundary} |"
        )
    lines.extend(
        [
            "",
            "## Evidence registry",
            "",
            "Fingerprints bind each class to the canonical LF-normalized UTF-8 "
            "content of every listed source, test, fixture, artifact, or receipt. "
            "They are drift indicators, not accuracy scores.",
            "",
            *_evidence_table(inventory),
            "",
            "## Tolerance law",
            "",
            "Source-solver/Monte Carlo uncertainty, binary storage error, LUT "
            "interpolation error, root-time tolerance, root-margin residual, "
            "limiting-magnitude envelopes, and deterministic event-time "
            "sensitivity are retained as separate receipts. Moira publishes no "
            "single aggregate tolerance or probabilistic confidence score for "
            "this model.",
            "",
        ]
    )
    return "\n".join(lines)


def render_api_inventory(inventory: RuntimeInventory) -> str:
    lines = [
        "# Generated Physical Heliacal-Visibility API Inventory",
        "",
        "> Generated from current object identity and "
        "`moira_server.app.create_app().openapi()` by "
        "`scripts/generate_physical_visibility_inventory.py`. Do not edit this "
        "file by hand.",
        "",
        f"- Engine package version: `{inventory.engine_version}`",
        f"- Curated physical symbols: {len(inventory.public_surfaces)}",
        f"- Dedicated physical REST operations: {len(inventory.operations)}",
        "- Client-supplied filesystem paths: prohibited",
        "",
        "## Python object identity",
        "",
        "| Symbol | `moira.heliacal` owner | `moira` root | `moira.facade` | `moira.sky.visibility` |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, owner, root, facade, sky in inventory.public_surfaces:
        lines.append(
            f"| `{name}` | {'yes' if owner else 'no'} | "
            f"{'yes' if root else 'no'} | {'yes' if facade else 'no'} | "
            f"{'yes' if sky else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Facade methods",
            "",
            *(f"- `{method}`" for method in inventory.methods),
            "",
            "Both methods require `data_pack_config` as a keyword-only input. "
            "The event method also keeps the complete search policy keyword-only.",
            "",
            "## Dedicated REST operations",
            "",
            "| Method | Path | Operation ID | Request schema | Response schema |",
            "|---|---|---|---|---|",
        ]
    )
    for path, operation_id, request, response in inventory.operations:
        lines.append(
            f"| `POST` | `{path}` | `{operation_id}` | `{request}` | `{response}` |"
        )
    lines.extend(
        [
            "",
            "Server-owned pack configuration:",
            "",
            "- `MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_DIRECTORY`",
            "- `MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_MANIFEST_SHA256`",
            "",
            "An unconfigured physical route returns the standard HTTP 503 "
            "`server_not_configured` error envelope. Physical request schemas "
            "contain no directory or data-pack path.",
            "",
            "## Preserved legacy REST operations",
            "",
            "| Method | Path | Operation ID |",
            "|---|---|---|",
        ]
    )
    for path, operation_id in inventory.legacy_operations:
        lines.append(f"| `POST` | `{path}` | `{operation_id}` |")
    lines.extend(
        [
            "",
            "## Private native substrate",
            "",
            *(f"- `{name}`" for name in inventory.native_kernels),
            "",
            "These underscore-prefixed bindings are private implementation "
            "details. They do not own policy, pack admission, typed failures, "
            "event semantics, or result construction.",
            "",
            "## Explicitly absent public surfaces",
            "",
            "No confidence score, client-supplied data-pack path request field, "
            "runtime libRadtran/MYSTIC operation, automatic downloader, "
            "site-specific experimental moonlight surface, or legacy-default "
            "replacement appears in the public inventory.",
            "",
        ]
    )
    return "\n".join(lines)


def render_documents() -> dict[Path, str]:
    inventory = collect_inventory()
    return {
        CAPABILITY_PATH: render_capability_matrix(inventory),
        API_PATH: render_api_inventory(inventory),
    }


def _write_or_check(check: bool) -> int:
    failures = []
    for path, rendered in render_documents().items():
        expected = rendered.encode("utf-8")
        if check:
            if not path.is_file() or _canonical_text_bytes(path) != expected:
                failures.append(path.relative_to(REPO_ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    if failures:
        raise PhysicalVisibilityInventoryError(
            "generated physical-visibility inventory is stale: "
            + ", ".join(failures)
        )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    return parser


def main() -> int:
    return _write_or_check(_parser().parse_args().check)


if __name__ == "__main__":
    raise SystemExit(main())

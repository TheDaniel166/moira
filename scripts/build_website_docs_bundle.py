"""Build the reproducible public-website documentation manifest.

The canonical Markdown remains under ``wiki/``. This script validates the
strict website allowlist, binds each public document to a SHA-256 digest, and
exports release, contract, validation, and catalog facts for downstream
consumers. It intentionally does not publish private research or copy source
documents into a second engine-owned tree.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "website_docs" / "publication_sources.json"
OUTPUT_PATH = REPO_ROOT / "website_docs" / "publication.json"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"

FORBIDDEN_PUBLIC_SOURCE_PREFIXES = (
    "wiki/04_sources/",
    "wiki/05_research/",
    "wiki/07_audit/",
)
ALLOWED_KINDS = {"doc", "validation_report", "validation_case"}
CONTRACT_SOURCES = {
    "python_api_reference": "wiki/02_standards/API_REFERENCE.md",
    "python_root_exports": "moira/__init__.py",
    "python_facade": "moira/facade.py",
    "rest_api_reference": "wiki/02_services/REST_API_REFERENCE.md",
    "rest_router_registration": "moira_server/app.py",
    "planetary_reduction": "wiki/02_standards/PLANETARY_REDUCTION_PIPELINE.md",
}
VALIDATION_METADATA: dict[str, dict[str, Any]] = {
    "astronomy": {
        "status": "partial",
        "oracles": ["IAU SOFA/ERFA", "JPL Horizons", "NASA/GSFC", "USNO", "IOTA"],
        "scope": "Mixed astronomy validation report; each section owns its corpus, semantics, and tolerance.",
    },
    "astrology": {
        "status": "partial",
        "oracles": ["Swiss Ephemeris fixtures", "Astro.com", "canonical doctrine tables", "structural invariants"],
        "scope": "Mixed convention-layer report; external software is used only where a stable matching product exists.",
    },
    "experimental": {
        "status": "partial",
        "oracles": ["SOFA/ERFA", "AAVSO", "GCVS", "published orbit ephemerides", "structural invariants"],
        "scope": "Mixed experimental report with explicit validated and partial subsections.",
    },
    "rose-of-venus": {
        "status": "validated",
        "oracles": ["JPL Horizons"],
        "scope": "Sun-Venus apparent geocentric conjunction sequence from 2026 through 2032.",
    },
    "eclipse-canon-comparison": {
        "status": "partial",
        "oracles": ["NASA eclipse catalogs", "Swiss eclipse fixtures"],
        "scope": "Readable catalog comparison; model-basis differences and unproved products remain explicit.",
    },
    "killer-validation-index": {
        "status": "documented",
        "oracles": ["multiple named authorities", "regression artifacts", "physical and structural invariants"],
        "scope": "Index only; every linked evidence record owns its own authority class and boundary.",
    },
    "polar-house-external-reference": {
        "status": "validated",
        "oracles": ["cached Swiss setest/t.exp fixture"],
        "scope": "Named high-latitude house cases under explicit system and fallback policy.",
    },
    "ancient-occultation-program": {
        "status": "documented",
        "oracles": ["historical and archaeological records"],
        "scope": "Validation program and uncertainty policy; not every candidate event is externally closed.",
    },
    "adversarial-stress-tests": {
        "status": "documented",
        "oracles": ["physical invariants", "structural invariants", "regression fixtures"],
        "scope": "Fail-visible singularity and defect ledger; regression evidence is not external truth.",
    },
    "gauquelin-g5-historical": {
        "status": "validated",
        "oracles": ["Gauquelin g5 historical dataset", "cached Swiss method-0 rows"],
        "scope": "Named historical corpus and plus-zone policy only.",
    },
    "release-evidence-5-1-to-5-2": {
        "status": "documented",
        "oracles": ["release-specific authority corpora", "physical and structural invariants"],
        "scope": "Status-explicit index; each release row states whether its evidence is validated, partial, or documented.",
    },
}


class PublicationError(ValueError):
    """Raised when the publication contract is internally inconsistent."""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed publication manifest without rewriting it.",
    )
    return parser.parse_args()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value: Any, *, pretty: bool) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    else:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return text.encode("utf-8")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_path(relative: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts:
        raise PublicationError(f"unsafe repository path: {relative!r}")
    path = REPO_ROOT.joinpath(*posix.parts)
    if not path.is_file():
        raise PublicationError(f"missing publication source: {relative}")
    return path


def _semver(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise PublicationError(f"not a stable semantic version: {value!r}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _git_output(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PublicationError(f"git {' '.join(args)} failed: {exc}") from exc
    return completed.stdout.strip()


def _project_facts() -> dict[str, Any]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    version = project["version"]
    _semver(version)
    tag = f"v{version}"
    commit = _git_output("rev-list", "-n", "1", tag)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PublicationError(f"{tag} did not resolve to a full commit")

    classifiers = project.get("classifiers", [])
    supported_python = sorted(
        {
            match.group(1)
            for classifier in classifiers
            if (
                match := re.fullmatch(
                    r"Programming Language :: Python :: (\d+\.\d+)",
                    classifier,
                )
            )
        },
        key=lambda item: tuple(int(part) for part in item.split(".")),
    )

    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    release_match = re.search(
        rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$",
        changelog,
        re.MULTILINE,
    )
    if not release_match:
        raise PublicationError(f"CHANGELOG.md has no dated {version} release")

    return {
        "name": project["name"],
        "version": version,
        "tag": tag,
        "commit": commit,
        "release_date": release_match.group(1),
        "requires_python": project["requires-python"],
        "supported_python": supported_python,
        "license": project["license"],
        "kernel_policy": {
            "planetary_readers": ["DE430", "DE440", "DE441"],
            "flagship_full_range_reader": "DE441",
            "small_body_availability": "An installed BSP-backed manifest is required; catalog metadata alone is not an ephemeris.",
        },
    }


def _extract_receipt_header(text: str) -> dict[str, str]:
    head = "\n".join(text.splitlines()[:30])
    version_match = re.search(r"(?:\*\*)?Version:(?:\*\*)?\s*([0-9.]+)", head)
    date_match = re.search(r"(?:\*\*)?Date:(?:\*\*)?\s*(\d{4}-\d{2}-\d{2})", head)
    result: dict[str, str] = {}
    if version_match:
        result["document_version"] = version_match.group(1)
    if date_match:
        result["receipt_date"] = date_match.group(1)
    return result


def _documents(config: dict[str, Any]) -> list[dict[str, Any]]:
    documents = config.get("documents")
    if not isinstance(documents, list) or not documents:
        raise PublicationError("publication config has no documents")

    seen_ids: set[str] = set()
    seen_routes: set[str] = set()
    seen_outputs: set[str] = set()
    rendered: list[dict[str, Any]] = []

    for entry in documents:
        if not isinstance(entry, dict):
            raise PublicationError("document entries must be objects")
        identifier = entry.get("id")
        kind = entry.get("kind")
        route = entry.get("route")
        output = entry.get("output")
        source = entry.get("source")
        if not all(isinstance(value, str) and value for value in (identifier, kind, route, output, source)):
            raise PublicationError(f"document entry has missing string fields: {entry!r}")
        if kind not in ALLOWED_KINDS:
            raise PublicationError(f"{identifier}: unsupported document kind {kind!r}")
        if not route.startswith("/"):
            raise PublicationError(f"{identifier}: route must be absolute")
        if any(source.startswith(prefix) for prefix in FORBIDDEN_PUBLIC_SOURCE_PREFIXES):
            raise PublicationError(f"{identifier}: private/internal source is not publishable: {source}")
        if identifier in seen_ids or route in seen_routes or output in seen_outputs:
            raise PublicationError(f"duplicate document identity, route, or output at {identifier}")
        seen_ids.add(identifier)
        seen_routes.add(route)
        seen_outputs.add(output)

        source_path = _repo_path(source)
        body = source_path.read_text(encoding="utf-8")
        public_entry = {
            **entry,
            "source_sha256": _sha256_path(source_path),
            "source_bytes": source_path.stat().st_size,
            "last_verified": config["last_verified"],
            "prerender": True,
            "markdown": True,
            "sitemap": True,
        }
        if kind.startswith("validation_"):
            metadata = VALIDATION_METADATA.get(identifier)
            if metadata is None:
                raise PublicationError(f"{identifier}: missing validation metadata")
            public_entry["validation"] = {
                **metadata,
                "evidence_paths": [source],
                **_extract_receipt_header(body),
            }
        rendered.append(public_entry)
    return rendered


def _changelog_versions() -> dict[str, str]:
    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    return {
        version: date
        for version, date in re.findall(
            r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$",
            text,
            re.MULTILINE,
        )
    }


def _releases(config: dict[str, Any], current_version: str) -> list[dict[str, Any]]:
    summaries = config.get("release_summaries")
    if not isinstance(summaries, list):
        raise PublicationError("publication config release_summaries must be a list")

    changelog_versions = _changelog_versions()
    floor = _semver(config["release_history_floor"])
    current = _semver(current_version)
    expected = {
        version
        for version in changelog_versions
        if floor < _semver(version) <= current
    }
    supplied = {entry.get("version") for entry in summaries if isinstance(entry, dict)}
    if supplied != expected:
        missing = sorted(expected - supplied, key=_semver)
        extra = sorted(supplied - expected, key=_semver)  # type: ignore[arg-type]
        raise PublicationError(
            f"release summary gap (missing={missing}, extra={extra})"
        )

    rendered: list[dict[str, Any]] = []
    for entry in summaries:
        version = entry["version"]
        if entry["date"] != changelog_versions[version]:
            raise PublicationError(
                f"{version}: configured date {entry['date']} does not match CHANGELOG "
                f"{changelog_versions[version]}"
            )
        for field in ("added", "changed", "fixed", "validation"):
            if not isinstance(entry.get(field), list):
                raise PublicationError(f"{version}: {field} must be a list")
        release_notes = entry["release_notes"]
        compatibility_notes = entry["compatibility_notes"]
        release_path = _repo_path(release_notes)
        compatibility_path = _repo_path(compatibility_notes)
        rendered.append(
            {
                **entry,
                "tag": f"v{version}",
                "release_notes_sha256": _sha256_path(release_path),
                "compatibility_notes_sha256": _sha256_path(compatibility_path),
            }
        )
    return sorted(rendered, key=lambda item: _semver(item["version"]), reverse=True)


def _catalog_metrics() -> dict[str, Any]:
    asteroid_manifest = _load_json(_repo_path("moira/kernels/asteroids/manifest.json"))
    comet_manifest = _load_json(_repo_path("moira/kernels/comets/manifest.json"))
    family_metadata = _load_json(_repo_path("moira/data/asteroid_families.metadata.json"))
    counts = family_metadata["counts"]
    return {
        "position_capable_asteroid_ephemeris": {
            "body_count": asteroid_manifest["body_count"],
            "shard_count": asteroid_manifest["shard_count"],
            "availability": "external_install_required",
            "source": "moira/kernels/asteroids/manifest.json",
        },
        "position_capable_periodic_comet_ephemeris": {
            "body_count": comet_manifest["body_count"],
            "shard_count": comet_manifest["shard_count"],
            "availability": "external_install_required",
            "source": "moira/kernels/comets/manifest.json",
        },
        "asteroid_family_membership_catalog": {
            "family_count": counts["family_count"],
            "unique_numbered_asteroid_count": counts["unique_numbered_asteroid_count"],
            "membership_row_count": counts["membership_row_count"],
            "maximum_memberships_per_asteroid": counts["maximum_memberships_per_asteroid"],
            "semantics": family_metadata["membership_semantics"],
            "source": "moira/data/asteroid_families.metadata.json",
            "catalog_sha256": family_metadata["csv_sha256"],
        },
    }


def _capability_metrics() -> dict[str, Any]:
    """Return current public-registry sizes from the implementation itself."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    from moira.constants import ASPECT_TIERS, HOUSE_SYSTEM_NAMES
    from moira.declination_aspects import DeclinationAspectKind
    from moira.lots import PARTS_DEFINITIONS
    from moira.sidereal import list_ayanamsa_systems

    star_source = "moira/data/star_registry.csv"
    with _repo_path(star_source).open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        fixed_star_count = sum(1 for _row in csv.DictReader(stream))

    constants_source = "moira/constants.py"
    declination_source = "moira/declination_aspects.py"
    lots_source = "moira/lots.py"
    sidereal_source = "moira/sidereal.py"
    return {
        "fixed_star_registry": {
            "entry_count": fixed_star_count,
            "source": star_source,
            "source_sha256": _sha256_path(_repo_path(star_source)),
        },
        "house_system_registry": {
            "entry_count": len(HOUSE_SYSTEM_NAMES),
            "source": constants_source,
            "source_sha256": _sha256_path(_repo_path(constants_source)),
        },
        "ecliptic_aspect_registry": {
            "entry_count": len(ASPECT_TIERS[max(ASPECT_TIERS)]),
            "source": constants_source,
            "source_sha256": _sha256_path(_repo_path(constants_source)),
        },
        "declination_aspect_registry": {
            "entry_count": len(DeclinationAspectKind),
            "source": declination_source,
            "source_sha256": _sha256_path(_repo_path(declination_source)),
        },
        "lot_definition_registry": {
            "entry_count": len(PARTS_DEFINITIONS),
            "source": lots_source,
            "source_sha256": _sha256_path(_repo_path(lots_source)),
        },
        "ayanamsha_registry": {
            "entry_count": len(list_ayanamsa_systems()),
            "source": sidereal_source,
            "source_sha256": _sha256_path(_repo_path(sidereal_source)),
        },
    }


def _python_exports() -> dict[str, Any]:
    """Bind website import examples to the implementation's public surfaces."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    import moira
    from moira import classical, essentials, facade, predictive, vedic

    modules = {
        "root": (moira, "moira/__init__.py"),
        "essentials": (essentials, "moira/essentials.py"),
        "classical": (classical, "moira/classical.py"),
        "predictive": (predictive, "moira/predictive.py"),
        "facade": (facade, "moira/facade.py"),
        "vedic": (vedic, "moira/vedic.py"),
    }
    rendered: dict[str, Any] = {}
    for name, (module, source) in modules.items():
        exports = getattr(module, "__all__", None)
        if not isinstance(exports, list) or not all(
            isinstance(symbol, str) and symbol for symbol in exports
        ):
            raise PublicationError(f"moira.{name} has no valid __all__ export list")
        if len(exports) != len(set(exports)):
            raise PublicationError(f"moira.{name} has duplicate public exports")
        rendered[name] = {
            "source": source,
            "source_sha256": _sha256_path(_repo_path(source)),
            "symbols": sorted(exports),
        }
    return rendered


def _contract_sources() -> list[dict[str, str]]:
    return [
        {"id": identifier, "source": source, "source_sha256": _sha256_path(_repo_path(source))}
        for identifier, source in CONTRACT_SOURCES.items()
    ]


def build_manifest() -> dict[str, Any]:
    config = _load_json(CONFIG_PATH)
    if config.get("schema_version") != 1:
        raise PublicationError("unsupported publication config schema_version")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", config.get("last_verified", "")):
        raise PublicationError("last_verified must be an ISO date")

    engine_release = _project_facts()
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "source_repository": "https://github.com/TheDaniel166/moira",
        "last_verified": config["last_verified"],
        "engine_release": engine_release,
        "contract_sources": _contract_sources(),
        "catalog_metrics": _catalog_metrics(),
        "capability_metrics": _capability_metrics(),
        "python_exports": _python_exports(),
        "documents": _documents(config),
        "releases": _releases(config, engine_release["version"]),
    }
    manifest["manifest_sha256"] = _sha256_bytes(_json_bytes(manifest, pretty=False))
    return manifest


def main() -> int:
    args = _parse_args()
    try:
        manifest = build_manifest()
    except (KeyError, OSError, json.JSONDecodeError, PublicationError, TypeError) as exc:
        print(f"Website documentation bundle failed: {exc}", file=sys.stderr)
        return 1

    rendered = _json_bytes(manifest, pretty=True)
    if args.check:
        if not OUTPUT_PATH.is_file():
            print(f"Missing generated manifest: {OUTPUT_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        existing = OUTPUT_PATH.read_bytes()
        if existing != rendered:
            print(
                "Website documentation manifest is stale; run "
                "python scripts/build_website_docs_bundle.py",
                file=sys.stderr,
            )
            return 1
        print(
            f"Website documentation manifest is current for "
            f"{manifest['engine_release']['tag']} "
            f"({len(manifest['documents'])} documents, {len(manifest['releases'])} releases)."
        )
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(rendered)
    print(
        f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} for "
        f"{manifest['engine_release']['tag']} "
        f"({len(manifest['documents'])} documents, {len(manifest['releases'])} releases)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
